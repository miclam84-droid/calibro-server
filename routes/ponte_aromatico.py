# -*- coding: utf-8 -*-
# PONTE AROMATICO — 1 endpoint di SOLA LETTURA per gli ingredienti SENZA profilo gusto.
#
# Problema reale: i nuovi ingredienti "scheletro" (e molti gia' presenti) NON hanno i
# valori degli assi del gusto (dolce/salato/.../umami). Senza quei numeri gli endpoint
# che confrontano profili non possono dire niente. Ma un abbinamento ONESTO si puo'
# comunque proporre da due segnali REALI, che non richiedono i gusti:
#   1) COMPOSTI aromatici condivisi (rete Ahn gia' nel grafo) — perche' molecolare;
#   2) FAMIGLIA: stessa categoria dell'ingrediente, e accostamenti tradizionali
#      documentati (famiglie che storicamente si abbinano) — perche' culturale.
# Ogni suggerimento DICHIARA su cosa si basa ("composti" | "famiglia"). Nessun gusto
# viene letto ne' inventato: se mancano sia i composti sia la famiglia, torna lista
# vuota e lo dice. E' la regola costituzionale: Matter mostra PERCHE', non un voto,
# e non inventa un legame che non c'e'.
#
# Riuso (NON reinvento le query sul grafo): gli helper di lettura e il ranking IDF gia'
# provati vengono da routes/criteri.py (_risolvi_nodo, _base_aromatica, _tradizione,
# _nome_composto, _errore, DATABASE_URL) e da routes/laboratorio_sensoriale.py
# (_composti_di, _profilo_gusto). Le connessioni passano dalla porta unica db.connessione().
#
# Le parti PURE (ranking/dedup/formattazione dei suggerimenti, nota onesta) sono funzioni
# senza DB e senza rete, testate in tests/test_ponte_aromatico.py con nodi finti. Le query
# DB si verificano in smoke su prod, come gli altri endpoint del progetto.

from flask import Blueprint, jsonify

from db import connessione
from routes.criteri import (
    _risolvi_nodo,
    _base_aromatica,
    _tradizione,
    _nome_composto,
    _errore,
    DATABASE_URL,
)
from routes.laboratorio_sensoriale import _composti_di, _profilo_gusto

bp_ponte = Blueprint("ponte_aromatico", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# PARTI PURE (nessun DB, nessuna rete) — costruzione, ranking e dedup dei ponti.
# ─────────────────────────────────────────────────────────────────────────────

def ponte_da_composti(voce):
    """Trasforma una voce di _base_aromatica (un dict, in test un 'nodo finto') in un
    suggerimento-ponte dichiarato come base COMPOSTI. Non tocca i gusti: usa solo il
    numero di composti condivisi reali e i piu' caratterizzanti gia' calcolati a monte.
    Ritorna None se la voce non ha almeno un composto condiviso (niente ponte inventato)."""
    ev = (voce or {}).get("evidenza") or {}
    n = int(ev.get("composti_condivisi") or 0)
    nome = (voce or {}).get("ingrediente")
    if not nome or n <= 0:
        return None
    caratt = [c for c in (ev.get("composti_caratterizzanti") or []) if c][:3]
    perche = "condivide " + str(n) + " composti aromatici reali"
    perche += (" — caratterizzanti: " + ", ".join(caratt)) if caratt \
        else " (comuni, poco caratterizzanti)"
    return {
        "ingrediente": nome,
        "composti_condivisi": n,
        "perche": perche,
        "base": "composti",
    }


def ponte_da_famiglia(nome, motivo, famiglia=None):
    """Costruisce un suggerimento-ponte dichiarato come base FAMIGLIA. `motivo` e' uno di
    'stessa_famiglia' (stessa categoria dell'ingrediente) o 'tradizione' (accostamento
    documentato, famiglie che storicamente si abbinano). composti_condivisi resta 0: il
    segnale qui NON e' molecolare e non lo spacciamo per tale. Ritorna None senza nome."""
    if not nome:
        return None
    if motivo == "stessa_famiglia":
        perche = "stessa famiglia" + (" (" + famiglia + ")" if famiglia else "") \
            + ": profilo e ruolo simili, da provare al banco"
    else:
        perche = "accostamento tradizionale documentato (cultura, non chimica)"
    return {
        "ingrediente": nome,
        "composti_condivisi": 0,
        "perche": perche,
        "base": "famiglia",
    }


def ordina_e_dedup(suggeriti, limite=12):
    """Ranking dei ponti, PURO. Ordina prima i ponti su COMPOSTI (per numero di composti
    condivisi decrescente, poi nome), poi quelli su FAMIGLIA (per nome). Deduplica per
    nome ingrediente tenendo il segnale piu' forte: COMPOSTI batte FAMIGLIA; a parita' di
    base, piu' composti condivisi. Non inventa nulla: riordina solo cio' che riceve.
    `suggeriti` e' una lista di dict come da ponte_da_composti/ponte_da_famiglia."""
    rank_base = {"composti": 0, "famiglia": 1}
    migliore = {}
    for s in suggeriti or []:
        if not isinstance(s, dict):
            continue
        nome = s.get("ingrediente")
        if not nome:
            continue
        chiave = nome.strip().lower()
        att = migliore.get(chiave)
        if att is None or _piu_forte(s, att):
            migliore[chiave] = s
    ordinati = sorted(
        migliore.values(),
        key=lambda s: (
            rank_base.get(s.get("base"), 9),
            -int(s.get("composti_condivisi") or 0),
            (s.get("ingrediente") or "").lower(),
        ),
    )
    return ordinati[:limite]


def _piu_forte(a, b):
    """True se il suggerimento a e' piu' forte di b per lo stesso ingrediente: COMPOSTI
    batte FAMIGLIA; a parita' di base, piu' composti condivisi. Puro."""
    rank_base = {"composti": 0, "famiglia": 1}
    ra = rank_base.get(a.get("base"), 9)
    rb = rank_base.get(b.get("base"), 9)
    if ra != rb:
        return ra < rb
    return int(a.get("composti_condivisi") or 0) > int(b.get("composti_condivisi") or 0)


def nota_onesta(ha_gusti, n_suggeriti, ha_composti, ha_famiglia):
    """Nota onesta sui dati, PURA. Dichiara da dove nasce la risposta e cosa manca.
    - nessun segnale (ne' composti ne' famiglia): lo diciamo chiaro, niente ponte finto;
    - altrimenti: spiega su cosa si basa e ricorda che il gusto non e' stato usato ne'
      inventato (va verificato al banco)."""
    if n_suggeriti <= 0:
        if not ha_composti and not ha_famiglia:
            return ("Non abbastanza dati: questo ingrediente non ha composti aromatici "
                    "mappati ne' una famiglia nota nel grafo. Nessun abbinamento onesto "
                    "da proporre — provalo e registra al banco.")
        return ("Ci sono dei segnali ma nessun partner ha superato la soglia: "
                "provalo e registra al banco.")
    fonti = []
    if ha_composti:
        fonti.append("composti aromatici condivisi (rete Ahn)")
    if ha_famiglia:
        fonti.append("stessa famiglia e accostamenti tradizionali documentati")
    base_txt = " e ".join(fonti) if fonti else "segnali reali del grafo"
    coda = (" L'ingrediente non ha un profilo gusto: nessun gusto e' stato usato ne' "
            "inventato, i suggerimenti sono ipotesi da verificare al banco."
            if not ha_gusti else
            " Suggerimenti da verificare al banco.")
    return "Abbinamenti basati su " + base_txt + "." + coda


# ─────────────────────────────────────────────────────────────────────────────
# HELPER DB (riusano i pattern di query gia' provati in criteri.py)
# ─────────────────────────────────────────────────────────────────────────────

def _famiglia_di(cur, node_id):
    """Categoria/famiglia del nodo (data->>'categoria', con fallback data->>'famiglia').
    Ritorna la stringa o None. Non inventa: se il nodo non ha categoria, torna None."""
    cur.execute(
        "SELECT COALESCE(NULLIF(data->>'categoria',''), NULLIF(data->>'famiglia','')) "
        "FROM nodes WHERE id=%s",
        (node_id,))
    r = cur.fetchone()
    return (r[0] if r and r[0] else None)


def _stessa_famiglia(cur, node_id, famiglia, limit=8):
    """Ingredienti/prodotti VISIBILI della stessa categoria (escluso il nodo stesso e le
    varianti-prodotto con nome tecnico underscore). Stesso pattern di admin.py:6780.
    Niente gusti, niente composti: solo appartenenza alla stessa famiglia."""
    if not famiglia:
        return []
    cur.execute(
        r"""SELECT DISTINCT n.name
            FROM nodes n
            WHERE n.type IN ('Ingrediente','Prodotto')
              AND n.id <> %s
              AND lower(COALESCE(n.data->>'categoria', n.data->>'famiglia')) = lower(%s)
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
            ORDER BY n.name
            LIMIT %s""",
        (node_id, famiglia, limit))
    return [r[0] for r in cur.fetchall() if r[0]]


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT — "Ponte aromatico": abbinamenti onesti per ingredienti senza gusti.
# ─────────────────────────────────────────────────────────────────────────────
@bp_ponte.route("/v1/ponte/<ingrediente>", methods=["GET"])
def ponte(ingrediente):
    """PONTE AROMATICO: dato un ingrediente (tipicamente SENZA profilo gusto), propone
    abbinamenti onesti da due segnali reali che non richiedono i gusti — composti
    aromatici condivisi (rete Ahn) e/o stessa famiglia + accostamenti tradizionali
    documentati. Ogni suggerimento dichiara la sua base. Se mancano entrambi i segnali,
    torna lista vuota e una nota onesta. Nessun gusto letto o inventato."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "ha_gusti": False, "suggeriti": [],
                        "nota_onesta": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({
                    "ingrediente": ingrediente,
                    "ha_gusti": False,
                    "non_riconosciuto": True,
                    "suggeriti": [],
                    "nota_onesta": "Ingrediente non trovato nel grafo: niente da proporre "
                                   "onestamente. Controlla il nome o registralo al banco.",
                }), 404
            ing_id, ing_nome = nodo
            ha_gusti = bool(_profilo_gusto(cur, ing_id))
            ha_composti_propri = len(_composti_di(cur, ing_id)) > 0
            # 1) segnale COMPOSTI: riuso del ranking IDF reale (anti-hub, per famiglia).
            vicini = _base_aromatica(cur, ing_id, ing_nome, limit=8) if ha_composti_propri else []
            # 2) segnale FAMIGLIA: stessa categoria + accostamenti tradizionali documentati.
            famiglia = _famiglia_di(cur, ing_id)
            simili = _stessa_famiglia(cur, ing_id, famiglia, limit=8)
            trad = _tradizione(cur, ing_id, limit=8)
            cur.close()

        sugg_composti = [s for s in (ponte_da_composti(v) for v in vicini) if s]
        sugg_famiglia = [s for s in (
            [ponte_da_famiglia(n, "stessa_famiglia", famiglia) for n in simili]
            + [ponte_da_famiglia(t.get("ingrediente"), "tradizione") for t in trad]
        ) if s]

        suggeriti = ordina_e_dedup(sugg_composti + sugg_famiglia, limite=12)
        ha_composti = len(sugg_composti) > 0
        ha_famiglia = bool(famiglia) or len(trad) > 0

        return jsonify({
            "ingrediente": ing_nome,
            "nodo_id": ing_id,
            "ha_gusti": ha_gusti,
            "famiglia": famiglia,
            "suggeriti": suggeriti,
            "conteggio": {"composti": len(sugg_composti), "famiglia": len(sugg_famiglia),
                          "mostrati": len(suggeriti)},
            "nota_onesta": nota_onesta(ha_gusti, len(suggeriti), ha_composti, ha_famiglia),
        })
    except Exception as e:
        return _errore(e)
