# -*- coding: utf-8 -*-
# LABORATORIO SENSORIALE V1 — 3 endpoint di SOLA LETTURA sulla rete aromatica reale.
#
# Scopo: spiegare il PERCHE' scientifico di un accostamento usando SOLO composti e
# relazioni reali presenti nel grafo, con conteggio e robustezza dell'evidenza.
# Niente voti di compatibilita', niente ponti inventati: se due ingredienti non
# condividono nulla di reale, lo diciamo. E' la regola costituzionale del progetto
# ("Matter mostra PERCHE' una relazione esiste, non un voto").
#
# Riuso (NON reinvento le query sul grafo): tutti gli helper di lettura vengono da
# routes/criteri.py — _risolvi_nodo (nodo canonico con chimica), _base_aromatica
# (vicini nella rete aromatica, ranking IDF), _nome_composto (nome leggibile),
# _errore (gestione errori regola d'arte). Le connessioni passano dalla porta
# unica del pool db.connessione().
#
# Le parti PURE (ranking/formattazione: indice di rarita', banda di evidenza,
# selezione dei composti caratterizzanti, partizione condivisi/distinti, confronto
# assi) sono funzioni senza DB, testate in tests/test_laboratorio.py. Le query DB
# si verificano in smoke su prod, come gli altri endpoint del progetto.

import math
from flask import Blueprint, jsonify

from db import connessione
from routes.criteri import (
    _risolvi_nodo,
    _base_aromatica,
    _nome_composto,
    _errore,
)

bp_lab = Blueprint("laboratorio_sensoriale", __name__)

# Assi sensoriali del grafo (stessi di routes/criteri.py, data->'proprieta').
ASSI_GUSTO = ("dolce", "salato", "acido", "amaro", "umami", "grasso", "piccante", "alcolico")


# ─────────────────────────────────────────────────────────────────────────────
# PARTI PURE (nessun DB, nessuna rete) — ranking e formattazione, testabili.
# ─────────────────────────────────────────────────────────────────────────────

def indice_rarita(df_list, n_tot, n_a, n_b):
    """Indice di rarita' dei composti condivisi, STESSA formula di _base_aromatica:
    somma dei pesi IDF ln(Ntot/df) normalizzata per sqrt(profilo_A * profilo_B).
    Condividere composti che stanno in tutto (df alto) vale ~0; condividere composti
    rari (caratterizzanti) vale tanto. df_list = document frequency di ogni composto
    condiviso (in quanti ingredienti compare). Ritorna 0.0 se mancano i dati."""
    if not df_list or n_a <= 0 or n_b <= 0:
        return 0.0
    n = max(float(n_tot), 2.0)
    somma = sum(math.log(n / max(float(d), 1.0)) for d in df_list)
    return round(somma / math.sqrt(float(n_a) * float(n_b)), 3)


def seleziona_caratterizzanti(comp_df, n_tot, soglia_frazione=0.05):
    """Dai composti condivisi tiene solo i CARATTERIZZANTI: quelli che compaiono in
    al piu' `soglia_frazione` degli ingredienti (default 5%). Un volatile verde
    generico (in migliaia di ingredienti) non caratterizza nulla. comp_df = lista di
    (comp_id, df). Ritorna la lista filtrata ordinata dal piu' raro, invariata la forma."""
    soglia = max(float(n_tot) * float(soglia_frazione), 1.0)
    rari = [(c, d) for (c, d) in comp_df if float(d) <= soglia]
    rari.sort(key=lambda x: float(x[1]))
    return rari


def banda_evidenza(n_condivisi, n_caratterizzanti):
    """Banda QUALITATIVA della robustezza dell'EVIDENZA molecolare di un singolo
    accostamento (non e' un voto di compatibilita'). Pesa soprattutto i composti
    caratterizzanti (rari): condividere tanta roba comune conta poco — e' la stessa
    lezione IDF di _base_aromatica, qui applicata a una coppia fissa che non ha
    competitori su cui normalizzare. Soglie dichiarate:
      - nessun composto condiviso        -> None (nessun ponte reale, lo diciamo)
      - >= 3 caratterizzanti             -> 'Alta'
      - >= 1 caratterizzante o >= 8 tot  -> 'Media'
      - almeno 1 condiviso               -> 'Esplorativa'."""
    if n_condivisi <= 0:
        return None
    if n_caratterizzanti >= 3:
        return "Alta"
    if n_caratterizzanti >= 1 or n_condivisi >= 8:
        return "Media"
    return "Esplorativa"


def partiziona_composti(comp_a, comp_b):
    """Partiziona due insiemi di composti in (condivisi, solo_a, solo_b), ordinati.
    Pura: lavora su id, non tocca il DB."""
    sa, sb = set(comp_a or []), set(comp_b or [])
    return sorted(sa & sb), sorted(sa - sb), sorted(sb - sa)


def confronta_assi(assi_a, assi_b):
    """Affianca i profili sensoriali di due ingredienti, asse per asse, con delta.
    Salta gli assi assenti in entrambi. Pura: nessun DB."""
    out = []
    for k in ASSI_GUSTO:
        va = (assi_a or {}).get(k)
        vb = (assi_b or {}).get(k)
        if va is None and vb is None:
            continue
        riga = {"asse": k, "a": va, "b": vb}
        if va is not None and vb is not None:
            riga["delta"] = round(float(va) - float(vb), 1)
        out.append(riga)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# HELPER DB (riusano i pattern di query gia' provati in criteri.py)
# ─────────────────────────────────────────────────────────────────────────────

def _composti_di(cur, node_id):
    """Insieme dei composti volatili reali di un nodo (DISTINCT: il grafo ha archi doppi)."""
    cur.execute(
        "SELECT DISTINCT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto'",
        (node_id,))
    return [r[0] for r in cur.fetchall()]


def _n_ingredienti_con_composti(cur):
    """Ntot per l'IDF: quanti ingredienti hanno almeno un composto (>=2, come _base_aromatica)."""
    cur.execute(
        "SELECT GREATEST(COUNT(DISTINCT from_id), 2) FROM edges WHERE relation='contiene_composto'")
    return int((cur.fetchone() or [2])[0])


def _df_composti(cur, comp_ids):
    """Document frequency reale di ogni composto: in quanti ingredienti distinti compare.
    Stesso conteggio del CTE `df` di _base_aromatica, qui per una lista fissa di composti."""
    if not comp_ids:
        return {}
    cur.execute(
        """SELECT to_id, COUNT(DISTINCT from_id)
           FROM edges WHERE relation='contiene_composto' AND to_id = ANY(%s)
           GROUP BY to_id""",
        (list(comp_ids),))
    return {r[0]: int(r[1]) for r in cur.fetchall()}


def _profilo_gusto(cur, node_id):
    """Profilo sensoriale reale dal nodo (data->'proprieta'), stessi assi di criteri.py.
    Ritorna {} se il nodo non ha ancora un profilo gusto (onesto, niente valori finti)."""
    import json as _json
    cur.execute("SELECT data FROM nodes WHERE id=%s", (node_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return {}
    dd = row[0] if isinstance(row[0], dict) else _json.loads(row[0])
    prop = (dd or {}).get("proprieta") or {}
    return {k: round(float(prop[k]), 1) for k in ASSI_GUSTO
            if isinstance(prop.get(k), (int, float))}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 1 — "Perche' funziona": composti condivisi reali tra due ingredienti.
# ─────────────────────────────────────────────────────────────────────────────
@bp_lab.route("/v1/laboratorio/perche/<ing_a>/<ing_b>", methods=["GET"])
def laboratorio_perche(ing_a, ing_b):
    """PERCHE' FUNZIONA: i composti aromatici realmente CONDIVISI tra due ingredienti,
    con conteggio, composti caratterizzanti (i piu' rari) e banda di robustezza
    dell'evidenza. Se non condividono nulla di reale, lo diciamo: niente ponte inventato."""
    from routes.criteri import DATABASE_URL
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            na = _risolvi_nodo(cur, ing_a)
            nb = _risolvi_nodo(cur, ing_b)
            if not na or not nb:
                mancanti = [x for x, n in ((ing_a, na), (ing_b, nb)) if not n]
                cur.close()
                return jsonify({
                    "a": ing_a, "b": ing_b,
                    "non_riconosciuto": mancanti,
                    "nota": "Ingrediente non trovato nel grafo con un profilo di composti.",
                }), 404
            id_a, nome_a = na
            id_b, nome_b = nb
            comp_a = _composti_di(cur, id_a)
            comp_b = _composti_di(cur, id_b)
            condivisi, _, _ = partiziona_composti(comp_a, comp_b)
            n_tot = _n_ingredienti_con_composti(cur)
            df = _df_composti(cur, condivisi)
            cur.close()

        if id_a == id_b:
            return jsonify({
                "a": nome_a, "b": nome_b,
                "nota": "Stesso nodo nel grafo: confronto non applicabile.",
            }), 400

        comp_df = [(c, df.get(c, 1)) for c in condivisi]
        caratt = seleziona_caratterizzanti(comp_df, n_tot)
        score = indice_rarita([d for _, d in comp_df], n_tot, len(comp_a), len(comp_b))
        banda = banda_evidenza(len(condivisi), len(caratt))
        nomi_caratt = [_nome_composto(c) for c, _ in caratt[:8]]

        if not condivisi:
            return jsonify({
                "a": nome_a, "b": nome_b,
                "nodi": {"a": id_a, "b": id_b},
                "condividono": False,
                "composti_condivisi": 0,
                "robustezza": None,
                "perche": "Nessun composto aromatico condiviso nei dati del grafo: "
                          "non c'e' un ponte molecolare reale tra questi due ingredienti.",
                "nota": "Onesta' dei dati: non inventiamo un legame che non esiste.",
            })

        return jsonify({
            "a": nome_a, "b": nome_b,
            "nodi": {"a": id_a, "b": id_b},
            "condividono": True,
            "composti_condivisi": len(condivisi),
            "profilo": {"composti_a": len(comp_a), "composti_b": len(comp_b)},
            "indice_rarita": score,
            "composti_caratterizzanti": nomi_caratt,
            "robustezza": banda,
            "perche": ("condividono " + str(len(condivisi)) + " composti aromatici reali"
                       + (" — caratterizzanti: " + ", ".join(nomi_caratt[:3])
                          if nomi_caratt else " (tutti comuni, poco caratterizzanti)")),
            "nota": "Robustezza = forza dell'evidenza molecolare (i composti rari pesano), "
                    "non un voto di compatibilita'.",
        })
    except Exception as e:
        return _errore(e)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 2 — "Sostituisci": vicini piu' simili nella rete aromatica.
# ─────────────────────────────────────────────────────────────────────────────
@bp_lab.route("/v1/laboratorio/sostituisci/<ing>", methods=["GET"])
def laboratorio_sostituisci(ing):
    """SOSTITUISCI: gli ingredienti piu' vicini nella rete aromatica (piu' composti
    condivisi, pesati per rarita'), col PERCHE'. Riusa _base_aromatica di criteri.py,
    cioe' lo stesso ranking IDF del motore criteri: niente logica nuova, stessi dati."""
    from routes.criteri import DATABASE_URL
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ing)
            if not nodo:
                cur.close()
                return jsonify({
                    "ingrediente": ing, "non_riconosciuto": True,
                    "sostituti": [],
                    "nota": "Ingrediente non trovato nel grafo con un profilo di composti.",
                }), 404
            ing_id, ing_nome = nodo
            vicini = _base_aromatica(cur, ing_id, ing_nome, limit=8)
            cur.close()

        sostituti = [{
            "ingrediente": v["ingrediente"],
            "composti_condivisi": v["evidenza"]["composti_condivisi"],
            "composti_caratterizzanti": v["evidenza"].get("composti_caratterizzanti", []),
            "indice_rarita": v["evidenza"].get("indice_rarita"),
            "robustezza": v["robustezza"],
            "perche": v["perche"],
        } for v in vicini]

        return jsonify({
            "ingrediente": ing_nome,
            "nodo_id": ing_id,
            "sostituti": sostituti,
            "conteggio": len(sostituti),
            "nota": "Vicinanza = composti aromatici condivisi reali, pesati per rarita'. "
                    "Un sostituto condivide la firma aromatica, non il ruolo in cucina: "
                    "ipotesi da verificare al banco." if sostituti else
                    "Nessun vicino con composti condivisi sufficienti nei dati del grafo.",
        })
    except Exception as e:
        return _errore(e)


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT 3 — "Confronta": profili sensoriali affiancati + condivisi vs distinti.
# ─────────────────────────────────────────────────────────────────────────────
@bp_lab.route("/v1/laboratorio/confronta/<ing_a>/<ing_b>", methods=["GET"])
def laboratorio_confronta(ing_a, ing_b):
    """CONFRONTA: profili sensoriali (assi gusto) affiancati con delta, piu' i composti
    aromatici condivisi e quelli distinti di ciascuno. Tutto dai dati reali del grafo;
    assi assenti restano nulli, non inventati."""
    from routes.criteri import DATABASE_URL
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            na = _risolvi_nodo(cur, ing_a)
            nb = _risolvi_nodo(cur, ing_b)
            if not na or not nb:
                mancanti = [x for x, n in ((ing_a, na), (ing_b, nb)) if not n]
                cur.close()
                return jsonify({
                    "a": ing_a, "b": ing_b,
                    "non_riconosciuto": mancanti,
                    "nota": "Ingrediente non trovato nel grafo con un profilo di composti.",
                }), 404
            id_a, nome_a = na
            id_b, nome_b = nb
            comp_a = _composti_di(cur, id_a)
            comp_b = _composti_di(cur, id_b)
            assi_a = _profilo_gusto(cur, id_a)
            assi_b = _profilo_gusto(cur, id_b)
            condivisi, solo_a, solo_b = partiziona_composti(comp_a, comp_b)
            n_tot = _n_ingredienti_con_composti(cur)
            # df su TUTTI i composti coinvolti, per mostrare i piu' caratterizzanti di ogni gruppo
            df = _df_composti(cur, set(comp_a) | set(comp_b))
            cur.close()

        def _top_caratterizzanti(ids, k=8):
            comp_df = [(c, df.get(c, 1)) for c in ids]
            rari = seleziona_caratterizzanti(comp_df, n_tot)
            scelti = rari if rari else sorted(comp_df, key=lambda x: float(x[1]))
            return [_nome_composto(c) for c, _ in scelti[:k]]

        return jsonify({
            "a": nome_a, "b": nome_b,
            "nodi": {"a": id_a, "b": id_b},
            "profilo_sensoriale": confronta_assi(assi_a, assi_b),
            "assi_assenti": not (assi_a or assi_b),
            "composti": {
                "condivisi": len(condivisi),
                "condivisi_caratterizzanti": _top_caratterizzanti(condivisi),
                "solo_a": len(solo_a),
                "solo_a_caratterizzanti": _top_caratterizzanti(solo_a),
                "solo_b": len(solo_b),
                "solo_b_caratterizzanti": _top_caratterizzanti(solo_b),
            },
            "nota": "Profili e composti dai dati reali del grafo. Gli assi mancanti sono "
                    "nulli (non ancora misurati), non zero: lettura da verificare al banco.",
        })
    except Exception as e:
        return _errore(e)
