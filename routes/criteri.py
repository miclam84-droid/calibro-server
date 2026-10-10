# -*- coding: utf-8 -*-
# MOTORE CRITERI (Laboratorio) — modulo pulito, NON tocca api_abbina.
# Decisioni congelate 8 ott 2026 (DECISIONI-LABORATORIO-CONGELATE).
#
# Regola costituzionale:
#   Matter NON assegna un voto alla compatibilita'. Mostra PERCHE' una relazione esiste.
#   Sempre: numero reale -> criterio -> interpretazione. Mai: numero inventato -> percentuale -> verdetto.
#
# Criteri V1: 1 BASE AROMATICA (composti condivisi reali) + 4 TRADIZIONE (archi documentati).
#
# Fix sistematici dopo test su dati reali (8 ott, giro largo):
#  - RISOLUZIONE NODO: preferiva la variante piu' ricca di dati (manzo->"manzo arrosto", caffe->"caffe filtro"
#    con 0 composti, cipolla->"cipolla arrostita"). Ora preferisce l'ingrediente CANONICO ahn_, scarta le
#    varianti arrosto/affumicato/filtro, e richiede che abbia davvero dei composti.
#  - FLOOD VARIANTI-PRODOTTO: brisket, fiorentina, ossobuco, tomahawk inondavano ogni ingrediente perche'
#    sono nodi 'Prodotto' che copiano la chimica del padre. Ora si abbina solo con INGREDIENTI canonici.
#  - ROBUSTEZZA: la soglia assoluta dava "Alta" a tutto (basilico 10 = manzo 179). Ora e' RELATIVA al
#    miglior risultato di quell'ingrediente.
#  - COUNT(DISTINCT) + filtro firma + padre<>base: restano (archi doppi, varianti dello stesso ingrediente).

import os
from flask import Blueprint, jsonify, request
from db import connessione

bp = Blueprint("criteri", __name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

_log = __import__("logging").getLogger("criteri")


def _errore(e):
    """Gestione errori regola d'arte: logga il traceback (lo cattura Railway + Sentry),
    NON espone i dettagli interni al pubblico (solo messaggio generico), ma li mostra
    all'admin col secret per il debug. Sostituisce i vecchi 'return str(e)'."""
    import traceback
    _log.exception("errore endpoint criteri")
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except Exception:
        pass
    if _admin_ok():
        return jsonify({"errore": str(e)[:300], "trace": traceback.format_exc()[-900:]}), 500
    return jsonify({"errore": "errore interno"}), 500

# IT -> nome Ahn canonico, per i casi che la risoluzione per nome sbagliava.
_ALIAS = {
    "caffe": "coffee", "caffè": "coffee", "cioccolato": "cocoa", "cacao": "cocoa",
    "manzo": "beef", "cipolla": "onion", "melanzana": "eggplant", "melanzane": "eggplant",
    "pomodoro": "tomato", "aglio": "garlic", "limone": "lemon", "lime": "lime",
    "fragola": "strawberry", "basilico": "basil", "gambero": "shrimp", "gamberi": "shrimp",
    "maiale": "pork", "pollo": "chicken", "mela": "apple", "pera": "pear",
    "vino": "wine", "vino bianco": "white_wine", "vino rosso": "red_wine", "birra": "beer",
    "arancia": "orange", "banana": "banana", "ananas": "pineapple", "mango": "mango",
    "zenzero": "ginger", "menta": "mint", "rosmarino": "rosemary", "timo": "thyme",
    "prezzemolo": "parsley", "salvia": "sage", "cannella": "cinnamon", "vaniglia": "vanilla",
    "burro": "butter", "panna": "cream", "latte": "milk", "uovo": "egg", "uova": "egg",
    "salmone": "salmon", "tonno": "tuna", "patata": "potato", "carota": "carrot",
    "funghi": "mushroom", "zucca": "pumpkin", "miele": "honey", "mandorla": "almond",
    "nocciola": "hazelnut", "cocco": "coconut", "peperoncino": "chili",
}

# varianti "preparate" da evitare quando l'utente cerca l'ingrediente base
_PREP_RX = r"roast|smoke|dried|dry|filter|grill|fried|cured|_oil"


def _nome_composto(cid):
    """comp_pub_1_octanol -> '1 octanol'. Toglie prefissi tecnici, non inventa traduzioni."""
    s = (cid or "").replace("comp_", "")
    if s.startswith("pub_"):
        s = s[4:]
    return s.replace("_", " ").strip()


# Le connessioni passano dalla porta unica del pool: db.connessione() (vedi PULIZIA-BACKEND-DIARIO).


def _risolvi_nodo(cur, ingrediente):
    """Trova il nodo CANONICO con la chimica. Preferisce: ingrediente base (non arrosto/filtro),
    nodo ahn_, match esatto di nome, e con composti veri (nc>0). Ritorna (id, nome_mostrato) o None."""
    ing = (ingrediente or "").strip().lower()

    # 1) alias diretto -> ahn_<name>, se esiste e ha composti
    alias = _ALIAS.get(ing)
    if alias:
        cur.execute(
            """SELECT n.id, n.name, COUNT(e.to_id) nc
               FROM nodes n LEFT JOIN edges e ON e.from_id=n.id AND e.relation='contiene_composto'
               WHERE n.id = %s GROUP BY n.id, n.name""",
            ("ahn_" + alias,),
        )
        r = cur.fetchone()
        if r and (r[2] or 0) > 0:
            return (r[0], ingrediente.strip())

    # 2) ricerca per nome/id, preferendo: non-preparato, canonico ahn_, match esatto, piu' ricco.
    cur.execute(
        r"""
        SELECT n.id, n.name,
               (CASE WHEN (n.id ~ %s) THEN 1 ELSE 0 END) AS prep,
               (CASE WHEN n.id LIKE 'ahn_%%' THEN 0 ELSE 1 END) AS noncanon,
               (CASE WHEN LOWER(n.name) = %s THEN 0 ELSE 1 END) AS nonexact,
               COUNT(e.to_id) AS nc
        FROM nodes n
        LEFT JOIN edges e ON e.from_id = n.id AND e.relation = 'contiene_composto'
        WHERE n.type IN ('Ingrediente','Prodotto')
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND (LOWER(n.name) = %s OR LOWER(n.name) LIKE %s OR LOWER(n.id) = %s)
        GROUP BY n.id, n.name
        HAVING COUNT(e.to_id) > 0
        ORDER BY prep ASC, noncanon ASC, nonexact ASC, nc DESC, LENGTH(n.name) ASC
        LIMIT 1
        """,
        (_PREP_RX, ing, ing, f"%{ing}%", "ahn_" + ing.replace(" ", "_")),
    )
    r = cur.fetchone()
    if r:
        return (r[0], ingrediente.strip())

    # 3) fallback: nessun nodo con composti (es. melanzana, pochi volatili). Prendo comunque il
    #    miglior match, così la TRADIZIONE si vede lo stesso. base_aromatica tornerà vuota, onesto.
    cur.execute(
        """SELECT n.id, n.name FROM nodes n
           WHERE n.type IN ('Ingrediente','Prodotto')
             AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
             AND (LOWER(n.name) = %s OR LOWER(n.name) LIKE %s OR LOWER(n.id) = %s)
           ORDER BY (LOWER(n.name) = %s) DESC, LENGTH(n.name) ASC
           LIMIT 1""",
        (ing, f"%{ing}%", "ahn_" + ing.replace(" ", "_"), ing),
    )
    r = cur.fetchone()
    if r:
        return (r[0], ingrediente.strip())
    return None


def _base_aromatica(cur, ing_id, base_nome, limit=12, min_shared=3, pool=200):
    """Criterio 1: ingredienti che condividono composti volatili reali.
    - solo partner INGREDIENTE canonico (niente nodi 'Prodotto' = varianti/tagli che copiano la chimica);
    - COUNT(DISTINCT): il grafo ha archi doppi;
    - RANKING PESATO PER RARITA' (IDF): ogni composto condiviso pesa ln(N/df), dove df = in quanti
      ingredienti compare. Un composto in 1500 ingredienti (volatile verde generico) pesa ~0; uno in
      5 e' caratterizzante e pesa tanto. Il conteggio grezzo e la sola normalizzazione lasciavano gli
      HUB (te', birra) in cima perche' condividono TANTI composti COMUNI. L'IDF li uccide: condividere
      roba che sta in tutto non vale niente. Poi si normalizza per sqrt(profilo_A*profilo_B).
    - 'composti' mostra i condivisi piu' RARI (i caratterizzanti), non i primi per id.
    - filtro firma aromatica: stessa firma di composti rari = stessa famiglia -> max 2."""
    cur.execute(
        "SELECT COUNT(DISTINCT to_id) FROM edges WHERE from_id=%s AND relation='contiene_composto'",
        (ing_id,))
    nA = int((cur.fetchone() or [0])[0]) or 1
    cur.execute(
        r"""
        WITH df AS (
            SELECT to_id AS comp, COUNT(DISTINCT from_id)::float AS d
            FROM edges WHERE relation='contiene_composto' GROUP BY to_id
        ),
        ntot AS (SELECT GREATEST(COUNT(DISTINCT from_id),2)::float AS n
                 FROM edges WHERE relation='contiene_composto'),
        cc AS (
            SELECT from_id, COUNT(DISTINCT to_id) AS n
            FROM edges WHERE relation='contiene_composto' GROUP BY from_id
        ),
        shared AS (
            SELECT DISTINCT n.name AS pname, b.to_id AS comp, cc.n AS nb
            FROM edges a
            JOIN edges b ON a.to_id = b.to_id AND b.relation = 'contiene_composto'
            JOIN nodes n ON n.id = b.from_id
            JOIN cc ON cc.from_id = n.id
            WHERE a.from_id = %s AND a.relation = 'contiene_composto'
              AND b.from_id <> %s
              AND n.type = 'Ingrediente'
              AND n.padre_ahn_id IS NULL
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
              AND LOWER(n.name) NOT LIKE LOWER(%s)
        )
        SELECT s.pname,
               COUNT(*) AS shared,
               MAX(s.nb) AS nb,
               ( SUM( ln( (SELECT n FROM ntot) / GREATEST(df.d,1) ) )
                 / sqrt(%s::float * MAX(s.nb)) ) AS score,
               (array_agg(s.comp ORDER BY df.d ASC))[1:6] AS rare_comps
        FROM shared s JOIN df ON df.comp = s.comp
        GROUP BY s.pname
        HAVING COUNT(*) >= %s
        ORDER BY score DESC, shared DESC, s.pname ASC
        LIMIT %s
        """,
        (ing_id, ing_id, f"%{base_nome}%", nA, min_shared, pool),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    max_score = max(float(r[3]) for r in rows) or 1.0
    out = []
    firma_count = {}
    for name, shared, nb, score, rare_comps in rows:
        ids = list(rare_comps or [])
        firma = tuple(sorted(ids)[:5])
        if firma and firma_count.get(firma, 0) >= 2:
            continue  # stessa firma = stessa famiglia -> max 2
        firma_count[firma] = firma_count.get(firma, 0) + 1
        frac = float(score) / max_score
        banda = "Alta" if frac >= 0.6 else ("Media" if frac >= 0.33 else "Esplorativa")
        comps = [_nome_composto(c) for c in ids]
        out.append({
            "ingrediente": name,
            "criterio": "base_aromatica",
            "evidenza": {"composti_condivisi": int(shared), "profilo_partner": int(nb),
                         "indice_rarita": round(float(score), 3), "composti_caratterizzanti": comps},
            "robustezza": banda,
            "perche": "condivide composti caratterizzanti"
                      + (f" — {', '.join(comps[:3])} (e altri, {shared} in tutto)" if comps
                         else f" — {shared} composti"),
        })
        if len(out) >= limit:
            break
    return out


def _tradizione(cur, ing_id, limit=6):
    """Criterio 4: accostamenti documentati. Etichettati come CULTURA, non come chimica."""
    out = []
    try:
        cur.execute(
            r"""
            SELECT DISTINCT n.name
            FROM edges e
            JOIN nodes n ON n.id = e.to_id
            WHERE e.from_id = %s AND e.relation = 'abbinamento_tradizionale'
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
            LIMIT %s
            """,
            (ing_id, limit),
        )
        for (name,) in cur.fetchall():
            out.append({
                "ingrediente": name,
                "criterio": "tradizione",
                "evidenza": {"tipo": "documentato"},
                "robustezza": None,
                "perche": "accostamento tradizionale documentato (cultura, non chimica)",
            })
    except Exception:
        pass
    return out


def _contrasto(cur, ing_id, limit=6):
    """Criterio: contrasto documentato (archi abbinamento_contrasto, bidirezionali).
    Relazione curata nel grafo, NON l'euristica fisico-chimica (quella richiede dati
    grassi/ph/amaro oggi non popolati — vedi mappa dati)."""
    out = []
    try:
        cur.execute(
            r"""
            SELECT DISTINCT n.name
            FROM edges e
            JOIN nodes n ON n.id = CASE WHEN e.from_id = %s THEN e.to_id ELSE e.from_id END
            WHERE (e.from_id = %s OR e.to_id = %s) AND e.relation = 'abbinamento_contrasto'
              AND n.id <> %s
              AND n.type IN ('Ingrediente', 'Prodotto')
              AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
              AND n.name NOT LIKE '%%\_%%'
            LIMIT %s
            """,
            (ing_id, ing_id, ing_id, ing_id, limit),
        )
        for (name,) in cur.fetchall():
            out.append({
                "ingrediente": name,
                "criterio": "contrasto",
                "evidenza": {"tipo": "documentato"},
                "robustezza": None,
                "perche": "contrasto documentato nel grafo (relazione curata, non euristica)",
            })
    except Exception:
        pass
    return out


# NOTA (3d, dietrofront verificato sui dati): i "sostituti" NON sono calcolabili dai soli composti
# aromatici. Test live: pomodoro -> te nero/patate (senza senso), parmigiano -> vuoto (ahn_parmesan ha
# 6 composti). La sostituibilita' richiede il RUOLO/categoria (acido/grasso/struttura), dato oggi assente.
# sostituti resta nel gruppo bloccato-dai-dati (vedi PULIZIA-BACKEND-DIARIO / mappa dati).


@bp.route("/v1/criteri/<ingrediente>", methods=["GET"])
def criteri(ingrediente):
    """Relazioni di un ingrediente, per criterio, con evidenza reale. NIENTE percentuale di abbinabilita'."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "relazioni": [], "nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"ingrediente": ingrediente, "relazioni": [],
                                "non_riconosciuto": True,
                                "nota": "Ingrediente non trovato nel grafo con un profilo di composti."})
            ing_id, ing_nome = nodo
            base = _base_aromatica(cur, ing_id, ing_nome)
            trad = _tradizione(cur, ing_id)
            contr = _contrasto(cur, ing_id)
            cur.close()
        # declassa gli hub generici (riuso il filtro gia' provato di api.py)
        try:
            from routes.api import _pulisci_abbinamenti
            base = _pulisci_abbinamenti(base, campo="ingrediente", max_famiglia=3, ingrediente_base=ing_nome)
        except Exception:
            pass
        base = base[:12]
        nomi_base = {r["ingrediente"].lower() for r in base}
        trad = [r for r in trad if r["ingrediente"].lower() not in nomi_base]
        gia_visti = nomi_base | {r["ingrediente"].lower() for r in trad}
        contr = [r for r in contr if r["ingrediente"].lower() not in gia_visti]
        return jsonify({
            "ingrediente": ing_nome,
            "nodo_id": ing_id,
            "regola": "Matter mostra perche' una relazione esiste, non un voto di compatibilita'.",
            "relazioni": base + trad + contr,
            "conteggio": {"base_aromatica": len(base), "tradizione": len(trad), "contrasto": len(contr)},
        })
    except Exception as e:
        return _errore(e)


@bp.route("/v1/criteri/diag/<ingrediente>", methods=["GET"])
def criteri_diag(ingrediente):
    """Diagnostica: quale nodo e' stato risolto e quanti composti ha."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"ingrediente": ingrediente, "trovato": False})
            ing_id, ing_nome = nodo
            cur.execute("SELECT COUNT(*) FROM edges WHERE from_id=%s AND relation='contiene_composto'", (ing_id,))
            n_comp = cur.fetchone()[0]
            cur.execute(
                "SELECT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto' LIMIT 8", (ing_id,))
            esempi = [_nome_composto(r[0]) for r in cur.fetchall()]
            cur.close()
        return jsonify({
            "cercato": ingrediente,
            "nodo_risolto": ing_id,
            "nome_mostrato": ing_nome,
            "composti_totali": n_comp,
            "composti_esempio": esempi,
        })
    except Exception as e:
        return _errore(e)


@bp.route("/v1/criteri/grafo-stato", methods=["GET"])
def grafo_stato():
    """Inventario reale del grafo: nodi per tipo, composti, ingredienti visibili/nascosti, archi per relazione."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type ORDER BY COUNT(*) DESC")
            nodi_per_tipo = {(t or "(senza tipo)"): n for t, n in cur.fetchall()}
            cur.execute(r"SELECT COUNT(*) FROM nodes WHERE id LIKE 'comp\_%' OR id LIKE 'pub\_%'")
            composti = cur.fetchone()[0]
            cur.execute(
                """SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
               AND (data->>'visibility') IS DISTINCT FROM 'hidden'""")
            ing_visibili = cur.fetchone()[0]
            cur.execute(
                """SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
               AND (data->>'visibility') = 'hidden'""")
            ing_nascosti = cur.fetchone()[0]
            cur.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC")
            archi_per_relazione = {(r or "(senza relazione)"): n for r, n in cur.fetchall()}
            # COPERTURA DATI (per la mappa-dati / moat): quanti ingredienti+prodotti hanno
            # il profilo organolettico 'proprieta' e quanti hanno almeno un composto.
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
            ip_totali = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'proprieta')")
            con_proprieta = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(DISTINCT from_id) FROM edges
                           WHERE relation = 'contiene_composto'""")
            con_composti = cur.fetchone()[0]
            # RECUPERABILITA' composti: chi eredita da un padre Ahn (padre_ahn_id) e
            # chi e' orfano (ne' composti propri ne' padre) = i candidati-da-collegare / buchi veri.
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND padre_ahn_id IS NOT NULL")
            con_padre_ahn = cur.fetchone()[0]
            cur.execute("""SELECT COUNT(*) FROM nodes n
                           WHERE n.type IN ('Ingrediente','Prodotto')
                             AND n.padre_ahn_id IS NULL
                             AND NOT EXISTS (SELECT 1 FROM edges e
                                             WHERE e.from_id = n.id AND e.relation = 'contiene_composto')""")
            senza_composti_ne_padre = cur.fetchone()[0]
            cur.close()
        return jsonify({
            "nodi_per_tipo": nodi_per_tipo,
            "composti_totali": composti,
            "ingredienti_visibili": ing_visibili,
            "ingredienti_nascosti": ing_nascosti,
            "archi_per_relazione": archi_per_relazione,
            "copertura_dati": {
                "ingredienti_prodotti_totali": ip_totali,
                "con_proprieta_organolettiche": con_proprieta,
                "nodi_con_composti": con_composti,
                "con_padre_ahn_eredita": con_padre_ahn,
                "orfani_senza_composti_ne_padre": senza_composti_ne_padre,
            },
        })
    except Exception as e:
        return _errore(e)


@bp.route("/v1/criteri/orfani", methods=["GET"])
def criteri_orfani():
    """DIAGNOSTICO (strategia Ahn): ingredienti/prodotti senza composti e senza padre_ahn.
    Raggruppa per prefisso id e campiona i nomi, per classificarli (varieta' di Ahn / preparazioni /
    genuinamente nuovi) e capire cosa si recupera gratis col link al padre e cosa no."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                r"""SELECT regexp_replace(id, '[-_].*$', '') AS pref, COUNT(*)
                    FROM nodes n
                    WHERE n.type IN ('Ingrediente','Prodotto')
                      AND n.padre_ahn_id IS NULL
                      AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation = 'contiene_composto')
                    GROUP BY pref ORDER BY COUNT(*) DESC""")
            per_prefisso = {(p or "(vuoto)"): c for p, c in cur.fetchall()}
            cur.execute(
                r"""SELECT id, name FROM nodes n
                    WHERE n.type IN ('Ingrediente','Prodotto')
                      AND n.padre_ahn_id IS NULL
                      AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation = 'contiene_composto')
                    ORDER BY n.name
                    LIMIT 120""")
            campione = [{"id": i, "nome": nm} for i, nm in cur.fetchall()]
            cur.close()
        return jsonify({"per_prefisso_id": per_prefisso, "campione_nomi": campione, "n_campione": len(campione)})
    except Exception as e:
        return _errore(e)


@bp.route("/v1/criteri/orfani-match", methods=["GET"])
def criteri_orfani_match():
    """DRY-RUN (strategia Ahn): per ogni orfano prova ad agganciarlo a un nodo con composti (futuro
    padre_ahn). NON scrive niente. Salta i chimici mis-tipati. Mostra cosa collegherebbe e cosa no,
    coi conteggi per bucket: agganciabili (recupero gratis) / chimici / non-agganciabili (comprare o buco)."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import re as _re
    _qualif = _re.compile(r"\b(dop|igp|docg|doc|pdo|pgi|igt|stg|tradizionale|riserva|extra|biologico|bio)\b|\d+\s*anni|\d{4}", _re.I)
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, lower(name) FROM nodes n
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')""")
            padri = {}
            padri_id = set()
            for pid, pn in cur.fetchall():
                padri_id.add(pid)
                if pn and pn not in padri:
                    padri[pn] = pid
            cur.execute(
                """SELECT id, name FROM nodes n
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND n.padre_ahn_id IS NULL
                     AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')""")
            orfani = cur.fetchall()
            cur.close()
        chimici = 0
        proposte = []
        non_match = []
        for oid, onome in orfani:
            nl = (onome or "").strip().lower()
            # euristica chimici mis-tipati: underscore, 'acido ...', suffisso oil
            if (not nl) or ("_" in nl) or nl.startswith("acido ") or nl == "acetaldeide" or nl.endswith(" oil"):
                chimici += 1
                continue
            base = _re.sub(r"\s+", " ", _qualif.sub(" ", nl)).strip()
            parent = None
            metodo = None
            for it_word, ahn in _ALIAS.items():
                if it_word in base:
                    cand = "ahn_" + ahn
                    if cand in padri_id:
                        parent = cand
                        metodo = f"alias:{it_word}->{ahn}"
                        break
            if not parent:
                for w in base.split():
                    if len(w) >= 4 and w in padri:
                        parent = padri[w]
                        metodo = f"parola:{w}"
                        break
            if parent:
                proposte.append({"orfano": onome, "padre": parent, "metodo": metodo})
            else:
                non_match.append(onome)
        return jsonify({
            "totale_orfani": len(orfani),
            "chimici_mis_tipati": chimici,
            "agganciabili": len(proposte),
            "non_agganciabili": len(non_match),
            "proposte_campione": proposte[:60],
            "non_agganciabili_campione": non_match[:60],
            "nota": "DRY-RUN: nessuna scrittura. Rivedi le proposte prima di applicare i link.",
        })
    except Exception as e:
        return _errore(e)


# --- LINK VERTICALI protocollo->fenomeno (moat): matcher STRETTO ---------------
# Il vecchio matcher prendeva OGNI parola >=5 lettere del nome-fenomeno come radice
# e agganciava su un solo stem: cosi' "La pasta e l'acqua di cottura" catturava
# qualunque "cottura X" (sundae, tiradito, steak...). Meta' falsi.
# Qui invece: una lista CURATA di termini DISTINTIVI. Un termine (o una coppia) deve
# comparire sia nel TESTO del protocollo sia nel NOME del fenomeno, e deve risolvere
# a UN SOLO fenomeno. Le parole generiche (cottura, conservazione, equilibrio,
# montatura, latte, zucchero, affinamento) sono fuori di proposito.
# Principio Matter: un arco falso e' peggio di un testo non collegato. Precisione > copertura.
# (termini_distintivi, id_fenomeno_esplicito_o_None).
# id esplicito = confermato dai dati reali (vince sull'ambiguita' di nome: "emulsion"
# compare sia in "Emulsione" sia in "Ganache (emulsione...)"). id None = risolto per
# nome solo se UNICO (altrimenti la regola non nasce, nessun falso).
_TERMINI_FEN_DISTINTIVI = [
    (("gelatinizz",),     "fen-gelatinizzazione"),
    (("emulsion",),       "fen-emulsione"),
    (("amaro", "bitter"), "fen-amaro-bitter"),
    (("farina", "forza"), "fen-farina-forza"),
    (("shakera",),        "fen-shakerare-mescolare"),
    (("maillard",),       None),   # risolto per nome se esiste ed e' unico
    (("caramellizz",),    None),
]


def _regole_fenomeni(fen):
    """fen: lista (fid, fname). Ritorna [(termini, fid)]. Con id esplicito: usato se il
    nodo esiste. Senza id: risolto per nome solo se UNICO. Ambiguo/assente -> regola non nasce."""
    fen_ids = {fid for fid, _ in fen}
    regole = []
    for termini, esplicito in _TERMINI_FEN_DISTINTIVI:
        if esplicito:
            if esplicito in fen_ids:
                regole.append((termini, esplicito))
        else:
            cand = [fid for fid, fname in fen if all(t in (fname or "").lower() for t in termini)]
            if len(cand) == 1:
                regole.append((termini, cand[0]))
    return regole


def _match_testo_fenomeno(testo, regole):
    """Prima regola i cui termini sono TUTTI nel testo. Altrimenti None."""
    tl = (testo or "").lower()
    for termini, fid in regole:
        if all(t in tl for t in termini):
            return fid
    return None


@bp.route("/v1/criteri/link-fenomeni", methods=["GET"])
def criteri_link_fenomeni():
    """DRY-RUN (moat, collegamenti verticali): legge il testo-fenomeni di ogni Protocollo e propone
    l'arco al nodo Fenomeno giusto, con MATCH STRETTO (termini distintivi, no parole generiche).
    NON scrive. Mostra proposte (complete), gia'-linkati, e i testi non-matchati distinti (coda lunga:
    spesso tecniche o passi di cottura generici, non fenomeni). Param opzionale ?ingrediente=pomodoro."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    from flask import request
    filtro_ing = (request.args.get("ingrediente") or "").strip().lower()
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM nodes WHERE type='Fenomeno'")
            fen = [(r[0], r[1]) for r in cur.fetchall()]
            regole = _regole_fenomeni(fen)
            nomi_fen = {fid: fname for fid, fname in fen}
            if filtro_ing:
                cur.execute("""SELECT DISTINCT n.id, n.name, n.data FROM edges e JOIN nodes n ON n.id=e.from_id
                               JOIN nodes i ON i.id=e.to_id
                               WHERE e.relation='usa_reagente' AND n.type='Protocollo'
                                 AND LOWER(i.name) LIKE %s AND n.data ? 'fenomeni'""", (f"%{filtro_ing}%",))
            else:
                cur.execute("SELECT id, name, data FROM nodes WHERE type='Protocollo' AND data ? 'fenomeni'")
            prot = cur.fetchall()
            cur.close()
        gia_linkati = 0
        testo_totale = 0
        proposte = []
        non_match_conta = {}
        for pid, pname, data in prot:
            dd = data if isinstance(data, dict) else (_json.loads(data) if data else {})
            for f in (dd.get("fenomeni") or []):
                if isinstance(f, dict):
                    if f.get("slug") or f.get("fenomeno_id"):
                        gia_linkati += 1
                        continue
                    txt = str(f.get("nome", ""))
                else:
                    txt = str(f)
                if not txt.strip():
                    continue
                testo_totale += 1
                fid = _match_testo_fenomeno(txt, regole)
                if fid:
                    proposte.append({"protocollo": pname, "testo": txt, "fenomeno": fid, "nome_fen": nomi_fen.get(fid)})
                else:
                    non_match_conta[txt] = non_match_conta.get(txt, 0) + 1
        # proposte per fenomeno (riepilogo che Michele puo' leggere a colpo d'occhio)
        per_fen = {}
        for p in proposte:
            per_fen[p["nome_fen"]] = per_fen.get(p["nome_fen"], 0) + 1
        non_match_distinti = sorted(non_match_conta.items(), key=lambda kv: -kv[1])
        return jsonify({
            "filtro_ingrediente": filtro_ing or "(tutti)",
            "protocolli_con_fenomeni": len(prot),
            "voci_fenomeno_testo": testo_totale,
            "gia_linkati": gia_linkati,
            "regole_attive": [{"termini": list(t), "fenomeno": fid, "nome_fen": nomi_fen.get(fid)} for t, fid in regole],
            "proposte_arco": len(proposte),
            "proposte_per_fenomeno": per_fen,
            "proposte": proposte,
            "non_matchati_distinti": len(non_match_distinti),
            "non_matchati": [{"testo": t, "conta": c} for t, c in non_match_distinti],
            "nota": "DRY-RUN: nessuna scrittura. Match stretto per termini distintivi. "
                    "I non-matchati sono quasi tutti passi di cottura generici o tecniche, non fenomeni.",
        })
    except Exception as e:
        return _errore(e)


def _admin_ok():
    """Auth scritture: stesso standard del resto (admin.py _admin_ok) — hmac a tempo costante,
    secret da header X-Admin-Secret (preferito) o ?s=. Nessun endpoint di scrittura senza questo."""
    import hmac
    atteso = os.environ.get("ADMIN_SECRET") or ""
    dato = request.headers.get("X-Admin-Secret", "") or request.args.get("s", "")
    return bool(atteso) and hmac.compare_digest(str(dato), str(atteso))


@bp.route("/v1/criteri/link-fenomeni/applica", methods=["GET", "POST"])
def criteri_link_fenomeni_applica():
    """APPLICA i link verticali protocollo->fenomeno con le STESSE regole strette del dry-run.
    Scrive slug+fenomeno_id nelle voci-fenomeno sciolte che matchano una regola distintiva.
    Idempotente (salta le gia'-linkate). Protetto: secret admin + ?conferma=applica (intento)."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    if not _admin_ok():
        return jsonify({"errore": "non autorizzato"}), 403
    if (request.args.get("conferma") or "") != "applica":
        return jsonify({"nota": "Sicurezza: aggiungi ?conferma=applica per scrivere gli archi."}), 400
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM nodes WHERE type='Fenomeno'")
            fen = [(r[0], r[1]) for r in cur.fetchall()]
            regole = _regole_fenomeni(fen)
            cur.execute("SELECT id, name, data FROM nodes WHERE type='Protocollo' AND data ? 'fenomeni'")
            prot = cur.fetchall()
            scritti = 0
            protocolli_toccati = 0
            dettaglio = []
            for pid, pname, data in prot:
                dd = data if isinstance(data, dict) else (_json.loads(data) if data else {})
                cambiato = False
                for f in (dd.get("fenomeni") or []):
                    if not isinstance(f, dict):
                        continue
                    if f.get("slug") or f.get("fenomeno_id"):
                        continue
                    fid = _match_testo_fenomeno(str(f.get("nome", "")), regole)
                    if fid:
                        f["slug"] = fid
                        f["fenomeno_id"] = fid
                        cambiato = True
                        scritti += 1
                        dettaglio.append({"protocollo": pname, "testo": f.get("nome"), "fenomeno": fid})
                if cambiato:
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                                (_json.dumps(dd, ensure_ascii=False), pid))
                    protocolli_toccati += 1
            conn.commit()
            cur.close()
        return jsonify({
            "scritti": scritti,
            "protocolli_toccati": protocolli_toccati,
            "dettaglio": dettaglio,
            "nota": "Archi slug materializzati. Rilanciare e' sicuro: idempotente.",
        })
    except Exception as e:
        return _errore(e)


# --- PULIZIA INGREDIENTI (punto 2): classificatore DRY-RUN -----------------------
# Separa i 1740 orfani in tre classi deterministiche, SENZA scrivere:
#   chimici     = nodi mis-tipati (non sono ingredienti: '_', 'acido ...', ' oil', acetaldeide)
#   usda_grezzi = doppioni USDA in inglese tecnico (marker USDA o >=2 virgole) di nodi che
#                 spesso esistono gia' in forma IT/Ahn -> spazzatura da togliere
#   non_mappati = ingredienti VERI senza profilo chimico (ostriche, seppia, oolong, inulina...)
#                 -> la sezione "non mappati" onesta, da dichiarare, non da gonfiare
_MARK_USDA = ["beverage", "distilled", "alcoholic", "raw", "cooked", "prepared", "unprepared",
              "with salt", "without salt", "proof", "nfs", "ns as to", "includes", "commercially",
              "broilers", "drained", "unenriched", "flesh and skin"]


def _classe_orfano(nome):
    nl = (nome or "").strip().lower()
    if (not nl) or ("_" in nl) or nl.startswith("acido ") or nl == "acetaldeide" or nl.endswith(" oil"):
        return "chimico"
    if any(m in nl for m in _MARK_USDA) or (nome or "").count(",") >= 2:
        return "usda_grezzo"
    return "non_mappato"


@bp.route("/v1/criteri/pulizia-ingredienti", methods=["GET"])
def criteri_pulizia_ingredienti():
    """DRY-RUN: classifica gli orfani (nodi Ingrediente/Prodotto senza composti ne' padre) in
    chimici mis-tipati / doppioni USDA grezzi / non-mappati veri. NON scrive. Dai numeri reali
    si decide cosa togliere (doppioni) e cosa dichiarare (non-mappati veri)."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, name FROM nodes n
                   WHERE n.type IN ('Ingrediente','Prodotto')
                     AND n.padre_ahn_id IS NULL
                     AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')""")
            orfani = cur.fetchall()
            cur.close()
        classi = {"chimico": [], "usda_grezzo": [], "non_mappato": []}
        for oid, onome in orfani:
            classi[_classe_orfano(onome)].append({"id": oid, "nome": onome})
        return jsonify({
            "totale_orfani": len(orfani),
            "conteggio": {k: len(v) for k, v in classi.items()},
            "chimici_campione": [x["nome"] for x in classi["chimico"][:40]],
            "usda_grezzi_campione": [x["nome"] for x in classi["usda_grezzo"][:40]],
            "non_mappati_campione": [x["nome"] for x in classi["non_mappato"][:60]],
            "nota": "DRY-RUN: nessuna scrittura. chimico=da ri-tipizzare; usda_grezzo=doppioni da "
                    "togliere; non_mappato=ingredienti veri da dichiarare come sezione onesta.",
        })
    except Exception as e:
        return _errore(e)


# --- CABLAGGIO USDA -> ASSI DEL GUSTO (Fase 2, dati reali) -----------------------
# Rifa' giusto cio' che il vecchio 'flask import-usda' faceva male (creava nodi usda_ a parte
# con acqua/proteine). Qui: prende zuccheri/sodio/grassi da USDA (pubblico dominio) per fdc_id
# verificato, DERIVA dolce/salato/grasso 0-10 e li scrive come `proprieta` SUL NODO CANONICO
# (pomodoro, non usda_tomato), taggati `derivato` con la fonte. Endpoint (no CLI), protetto, dry-run.
# Gli ancoraggi 0-10 sono PROVVISORI (vedi SCALE-SENSORIALI): si tarano al banco.
_USDA_CORE = {
    # italiano (per _risolvi_nodo) -> fdc_id USDA verificato
    "pomodoro": 170457, "limone": 167747, "lime": 168195, "mela": 171688,
    "fragola": 167762, "parmigiano": 173420, "burro": 789828, "latte": 171265,
    "zucchero": 169655, "miele": 169640, "olio di oliva": 171413, "aglio": 169230,
    "cipolla": 170000, "carota": 170393, "patata": 170026, "spinaci": 168462,
}
# agganci FISSI dove _risolvi_nodo sbaglia (verificati col dry-run): nodo canonico corretto
_USDA_NODO_FISSO = {
    "lime": "ing-lime",            # non kaffir
    "zucchero": "prod_zucchero",   # zucchero, non lo sciroppo
    "olio di oliva": "ing-olio-evo",  # l'EVO vero, non il nodo fis_
}
# ancoraggi (valore_grezzo_per_100g -> voto 0..10), PROVVISORI
_ANCORE_DOLCE = [(0, 0), (5, 2), (10, 4), (15, 6), (50, 8), (100, 10)]          # zuccheri g
_ANCORE_SALATO = [(0, 0), (50, 1), (400, 3), (800, 5), (2500, 8), (38000, 10)]  # sodio mg
_ANCORE_GRASSO = [(0, 0), (3, 2), (15, 5), (50, 7), (81, 8), (100, 10)]         # grassi g


def _scala(v, punti):
    """Interpolazione lineare a tratti tra gli ancoraggi, con clamp 0..10."""
    if v is None:
        return None
    if v <= punti[0][0]:
        return 0.0
    for (x0, y0), (x1, y1) in zip(punti, punti[1:]):
        if v <= x1:
            if x1 == x0:
                return round(y1, 1)
            return round(y0 + (y1 - y0) * (v - x0) / (x1 - x0), 1)
    return 10.0


def _usda_nutrienti(fdc_id, key):
    """Prende zuccheri/sodio/grassi (per 100g) da USDA FoodData Central per fdc_id."""
    import urllib.request as _u, json as _j
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key={key}"
    req = _u.Request(url, headers={"User-Agent": "Matter/1.0"})
    with _u.urlopen(req, timeout=30) as r:
        d = _j.loads(r.read().decode())
    zuccheri = sodio = grassi = None
    nome = d.get("description", "")
    for n in d.get("foodNutrients", []):
        nm = (n.get("nutrient", {}) or {}).get("name", "") or ""
        amt = n.get("amount")
        if amt is None:
            continue
        low = nm.lower()
        if "sugars" in low and "added" not in low and zuccheri is None:
            zuccheri = float(amt)
        elif low.startswith("sodium") and sodio is None:
            sodio = float(amt)
        elif "total lipid" in low and grassi is None:
            grassi = float(amt)
    return {"nome_usda": nome, "zuccheri_g": zuccheri, "sodio_mg": sodio, "grassi_g": grassi}


@bp.route("/v1/criteri/usda-gusti", methods=["GET", "POST"])
def criteri_usda_gusti():
    """Caba dolce/salato/grasso da USDA sui nodi canonici del core. DRY-RUN di default
    (mostra cosa scriverebbe). Scrive solo con ?conferma=applica. Protetto dal secret admin."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato (manca il secret admin)"}), 403
    key = os.environ.get("USDA_API_KEY", "")
    if not key:
        return jsonify({"errore": "USDA_API_KEY non impostata su Railway"}), 503
    righe = []
    scritti = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it, fdc in _USDA_CORE.items():
                voce = {"ingrediente": nome_it, "fdc_id": fdc}
                fisso = _USDA_NODO_FISSO.get(nome_it)
                nodo = None
                if fisso:
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (fisso,))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    voce["stato"] = "nodo non trovato"
                    righe.append(voce)
                    continue
                voce["nodo"] = nodo[0]
                try:
                    nutr = _usda_nutrienti(fdc, key)
                except Exception as e:
                    voce["stato"] = "USDA errore: " + str(e)[:80]
                    righe.append(voce)
                    continue
                dolce = _scala(nutr["zuccheri_g"], _ANCORE_DOLCE)
                salato = _scala(nutr["sodio_mg"], _ANCORE_SALATO)
                grasso = _scala(nutr["grassi_g"], _ANCORE_GRASSO)
                voce["grezzo"] = {"zuccheri_g": nutr["zuccheri_g"], "sodio_mg": nutr["sodio_mg"],
                                  "grassi_g": nutr["grassi_g"]}
                voce["derivato"] = {"dolce": dolce, "salato": salato, "grasso": grasso}
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (
                        _json.loads(row[0]) if (row and row[0]) else {})
                    prop = dd.get("proprieta") or {}
                    for asse, val, base in (("dolce", dolce, f"zuccheri {nutr['zuccheri_g']}g/100g"),
                                            ("salato", salato, f"sodio {nutr['sodio_mg']}mg/100g"),
                                            ("grasso", grasso, f"grassi {nutr['grassi_g']}g/100g")):
                        if val is not None:
                            prop[asse] = val
                    dd["proprieta"] = prop
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                                (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                    scritti += 1
                    voce["stato"] = "scritto"
                righe.append(voce)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({
            "modo": "APPLICATO" if applica else "DRY-RUN (aggiungi ?conferma=applica per scrivere)",
            "scritti": scritti,
            "ancoraggi": "PROVVISORI (vedi SCALE-SENSORIALI, si tarano al banco)",
            "righe": righe,
        })
    except Exception as e:
        return _errore(e)


# --- ACIDO (pH) + UMAMI (glutammato) da dati pubblici, sul core -------------------
_PH_CORE = {
    "pomodoro": 4.3, "limone": 2.3, "lime": 2.3, "mela": 3.4, "fragola": 3.4,
    "parmigiano": 5.4, "latte": 6.7, "miele": 3.9, "aglio": 5.8, "cipolla": 5.5,
    "carota": 6.0, "patata": 5.7, "spinaci": 5.6,
}
_GLU_CORE = {
    "pomodoro": 240, "parmigiano": 1200, "latte": 2, "aglio": 100, "cipolla": 50,
    "carota": 40, "spinaci": 50, "patata": 100, "mela": 5, "fragola": 5,
    "miele": 0, "zucchero": 0, "burro": 5, "olio di oliva": 0, "limone": 3, "lime": 3,
}
_ANCORE_ACIDO = [(0, 0), (1.5, 3), (2.5, 5), (3.5, 7), (4.7, 9), (5.2, 10)]
_ANCORE_UMAMI = [(0, 0), (50, 1.5), (150, 3), (400, 5), (800, 7), (1200, 8.5), (1600, 10)]


@bp.route("/v1/criteri/gusti-ph-umami", methods=["GET", "POST"])
def criteri_gusti_ph_umami():
    """Caba ACIDO (da pH) e UMAMI (da glutammato) sui nodi del core. DRY-RUN; scrive con ?conferma=applica."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    scritti = 0
    nomi = set(list(_PH_CORE.keys()) + list(_GLU_CORE.keys()))
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it in sorted(nomi):
                voce = {"ingrediente": nome_it}
                fisso = _USDA_NODO_FISSO.get(nome_it)
                nodo = None
                if fisso:
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (fisso,))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    voce["stato"] = "nodo non trovato"
                    righe.append(voce)
                    continue
                voce["nodo"] = nodo[0]
                ph = _PH_CORE.get(nome_it)
                glu = _GLU_CORE.get(nome_it)
                acido = _scala(7 - ph, _ANCORE_ACIDO) if ph is not None else None
                umami = _scala(glu, _ANCORE_UMAMI) if glu is not None else None
                voce["grezzo"] = {"pH": ph, "glutammato_mg": glu}
                voce["derivato"] = {"acido": acido, "umami": umami}
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                    prop = dd.get("proprieta") or {}
                    fonti = dd.get("proprieta_fonti") or {}
                    if acido is not None and "acido" not in prop:
                        prop["acido"] = acido
                        fonti["acido"] = {"stato": "derivato", "fonte": "pH FDA/extension", "base": f"pH {ph}"}
                    if umami is not None and "umami" not in prop:
                        prop["umami"] = umami
                        fonti["umami"] = {"stato": "derivato", "fonte": "glutammato letteratura", "base": f"glutammato {glu} mg/100g"}
                    dd["proprieta"] = prop
                    dd["proprieta_fonti"] = fonti
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                    scritti += 1
                    voce["stato"] = "scritto"
                righe.append(voce)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "scritti": scritti, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- ESTENSIONE CORE (bar + bakery): aggiorna le mappe gusto senza toccare l'esistente ---
_USDA_CORE.update({
    "farina": 168944, "uovo": 171287, "tuorlo": 172185, "albume": 172183,
    "cacao": 169593, "cioccolato fondente": 170272, "caffe": 171890,
    "aceto balsamico": 172241, "yogurt": 170886, "panna": 2346386,
    "manzo": 174036, "salmone": 175167, "funghi": 169251, "mandorle": 170567,
    "riso": 169756, "banana": 173944, "arancia": 169098, "ananas": 169949,
})
_PH_CORE.update({
    "farina": 6.0, "uovo": 7.6, "albume": 9.0, "tuorlo": 6.3, "cacao": 5.8,
    "cioccolato fondente": 5.5, "caffe": 5.0, "aceto balsamico": 3.0, "yogurt": 4.4,
    "panna": 6.6, "manzo": 5.6, "salmone": 6.2, "funghi": 6.2, "mandorle": 6.5,
    "riso": 6.5, "banana": 4.8, "arancia": 3.7, "ananas": 3.5,
})
_GLU_CORE.update({
    "farina": 30, "uovo": 20, "albume": 20, "tuorlo": 10, "cacao": 100,
    "cioccolato fondente": 50, "caffe": 20, "aceto balsamico": 0, "yogurt": 5,
    "panna": 5, "manzo": 10, "salmone": 20, "funghi": 70, "mandorle": 40,
    "riso": 5, "banana": 15, "arancia": 20, "ananas": 20,
})

# --- agganci fissi aggiuntivi (nodi canonici corretti, verificati col dry-run) ---
_USDA_NODO_FISSO.update({
    "farina": "ing-base-farina",
    "mandorle": "ahn_almond",
})

# --- USDA gusti A BLOCCHI (fill-only): evita il timeout, completa dolce/salato/grasso sui nuovi ---
@bp.route("/v1/criteri/usda-gusti-blocco", methods=["GET", "POST"])
def criteri_usda_gusti_blocco():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    key = os.environ.get("USDA_API_KEY", "")
    if not key:
        return jsonify({"errore": "USDA_API_KEY non impostata"}), 503
    try:
        da = int(request.args.get("da") or 0)
        a = int(request.args.get("a") or 12)
    except ValueError:
        da, a = 0, 12
    voci = sorted(_USDA_CORE.items())[da:a]
    righe = []
    scritti = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it, fdc in voci:
                r = {"ingrediente": nome_it, "fdc_id": fdc}
                fisso = _USDA_NODO_FISSO.get(nome_it)
                nodo = None
                if fisso:
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (fisso,))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    r["stato"] = "nodo non trovato"
                    righe.append(r)
                    continue
                r["nodo"] = nodo[0]
                try:
                    nutr = _usda_nutrienti(fdc, key)
                except Exception as e:
                    r["stato"] = "USDA errore: " + str(e)[:60]
                    righe.append(r)
                    continue
                dolce = _scala(nutr["zuccheri_g"], _ANCORE_DOLCE)
                salato = _scala(nutr["sodio_mg"], _ANCORE_SALATO)
                grasso = _scala(nutr["grassi_g"], _ANCORE_GRASSO)
                r["derivato"] = {"dolce": dolce, "salato": salato, "grasso": grasso}
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                    prop = dd.get("proprieta") or {}
                    fonti = dd.get("proprieta_fonti") or {}
                    for asse, val, base in (("dolce", dolce, f"zuccheri {nutr['zuccheri_g']}g/100g"),
                                            ("salato", salato, f"sodio {nutr['sodio_mg']}mg/100g"),
                                            ("grasso", grasso, f"grassi {nutr['grassi_g']}g/100g")):
                        if val is not None and asse not in prop:
                            prop[asse] = val
                            fonti[asse] = {"stato": "derivato", "fonte": f"USDA FDC {fdc}", "base": base}
                    dd["proprieta"] = prop
                    dd["proprieta_fonti"] = fonti
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                    scritti += 1
                    r["stato"] = "scritto"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "fetta": f"{da}:{a}",
                        "totale_core": len(_USDA_CORE), "scritti": scritti, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- FASE 2: BILANCIAMENTO (lettura degli assi, non verdetto) ---------------------
_BILANCIA = {
    "grasso": ["acido", "amaro"],
    "acido":  ["dolce", "grasso"],
    "dolce":  ["acido", "amaro"],
    "salato": ["acido", "dolce"],
    "amaro":  ["dolce", "grasso"],
    "umami":  ["acido"],
}


def _alti_in_asse(cur, asse, escludi_id, soglia=6.0, limite=6):
    cur.execute(
        """SELECT n.name, (n.data->'proprieta'->>%s)::float AS v
           FROM nodes n
           WHERE n.type IN ('Ingrediente','Prodotto')
             AND n.id <> %s
             AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
             AND (n.data->'proprieta' ? %s)
             AND (n.data->'proprieta'->>%s) ~ '^[0-9.]+$'
             AND (n.data->'proprieta'->>%s)::float >= %s
           ORDER BY v DESC LIMIT %s""",
        (asse, escludi_id, asse, asse, asse, soglia, limite))
    return [{"ingrediente": r[0], "valore": round(float(r[1]), 1)} for r in cur.fetchall()]


@bp.route("/v1/criteri/bilancio/<ingrediente>", methods=["GET"])
def criteri_bilancio(ingrediente):
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"errore": f"ingrediente '{ingrediente}' non trovato"}), 404
            cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
            row = cur.fetchone()
            dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
            prop = dd.get("proprieta") or {}
            assi = {}
            for k in ("dolce", "salato", "acido", "amaro", "umami", "grasso", "piccante", "alcolico"):
                v = prop.get(k)
                if isinstance(v, (int, float)):
                    assi[k] = round(float(v), 1)
            if not assi:
                cur.close()
                return jsonify({"ingrediente": nodo[1], "nodo": nodo[0], "nota": "nessun profilo gusto ancora"})
            dominanti = sorted([a for a, v in assi.items() if v >= 6.0], key=lambda a: -assi[a])
            bilancio = []
            visti = set()
            for asse in dominanti:
                for serve in _BILANCIA.get(asse, []):
                    if serve in visti:
                        continue
                    visti.add(serve)
                    partner = _alti_in_asse(cur, serve, nodo[0])
                    if partner:
                        bilancio.append({"perche": f"{nodo[1]} e' {asse} {assi[asse]} -> {serve} per bilanciare",
                                         "asse_che_serve": serve, "partner": partner})
            cur.close()
        return jsonify({"ingrediente": nodo[1], "nodo": nodo[0], "profilo_gusto": assi,
                        "assi_dominanti": dominanti or ["(nessun asse >= 6)"], "bilanciamento": bilancio,
                        "nota": "Lettura degli assi: ipotesi da verificare al banco, non un verdetto."})
    except Exception as e:
        return _errore(e)

# --- ESTENSIONE CORE 2: altri ingredienti (frutta, latticini, cereali, carni, fermentati) ---
_USDA_CORE.update({
    "pompelmo": 169106, "melograno": 169134, "mango": 169910, "pera": 169943,
    "uva": 174683, "cheddar": 173414, "panna acida": 170862, "farina di segale": 2512375,
    "farina di avena": 173903, "orzo": 169700, "pollo": 171477, "maiale": 167903,
    "tonno": 175159, "gamberi": 175178, "acciughe": 174178, "cetriolo": 168409,
    "peperone": 170108, "sciroppo d'acero": 169661, "aceto di mele": 173468,
    "crauti": 169279, "miso": 172444, "nocciole": 170581, "noci": 170187,
    "zenzero": 169231, "cannella": 171320, "pepe nero": 170931,
})
_PH_CORE.update({
    "pompelmo": 3.3, "melograno": 3.0, "mango": 4.6, "pera": 3.9, "uva": 3.5,
    "cheddar": 5.3, "panna acida": 4.5, "farina di segale": 6.0, "farina di avena": 6.3,
    "orzo": 6.5, "pollo": 6.0, "maiale": 5.9, "tonno": 5.8, "gamberi": 7.0,
    "acciughe": 6.0, "cetriolo": 5.5, "peperone": 5.0, "aceto di mele": 3.0,
    "crauti": 3.5, "miso": 5.0, "nocciole": 6.0, "noci": 5.5, "zenzero": 5.6,
    "cannella": 5.0, "pepe nero": 6.0, "sciroppo d'acero": 5.5,
})
_GLU_CORE.update({
    "pompelmo": 20, "melograno": 10, "mango": 20, "pera": 10, "uva": 20,
    "cheddar": 180, "panna acida": 10, "farina di segale": 30, "farina di avena": 20,
    "orzo": 30, "pollo": 20, "maiale": 10, "tonno": 30, "gamberi": 120,
    "acciughe": 300, "cetriolo": 30, "peperone": 50, "sciroppo d'acero": 0,
    "aceto di mele": 0, "crauti": 50, "miso": 200, "nocciole": 40, "noci": 40,
    "zenzero": 20, "cannella": 0, "pepe nero": 0,
})

# --- aggancio fisso: nocciole (nodo canonico, non la farina) ---
_USDA_NODO_FISSO.update({"nocciole": "ahn_hazelnut"})

# --- FASE 2.1: BILANCIO + AROMA (unisce i due strati) ----------
def _condivisi_con(cur, target_id, partner_nome):
    cur.execute(
        """SELECT COUNT(DISTINCT b.to_id)
           FROM edges a JOIN edges b ON a.to_id=b.to_id AND b.relation='contiene_composto'
           JOIN nodes n ON n.id=b.from_id
           WHERE a.from_id=%s AND a.relation='contiene_composto' AND LOWER(n.name)=LOWER(%s)""",
        (target_id, partner_nome))
    r = cur.fetchone()
    return int(r[0]) if r and r[0] else 0


@bp.route("/v1/criteri/bilancio-aroma/<ingrediente>", methods=["GET"])
def criteri_bilancio_aroma(ingrediente):
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"errore": f"'{ingrediente}' non trovato"}), 404
            cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
            row = cur.fetchone()
            dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
            prop = dd.get("proprieta") or {}
            assi = {k: round(float(prop[k]), 1) for k in ("dolce", "salato", "acido", "amaro", "umami", "grasso", "piccante", "alcolico")
                    if isinstance(prop.get(k), (int, float))}
            if not assi:
                cur.close()
                return jsonify({"ingrediente": nodo[1], "nota": "nessun profilo gusto"})
            dominanti = sorted([a for a, v in assi.items() if v >= 6.0], key=lambda a: -assi[a])
            out = []
            visti = set()
            for asse in dominanti:
                for serve in _BILANCIA.get(asse, []):
                    if serve in visti:
                        continue
                    visti.add(serve)
                    partner = _alti_in_asse(cur, serve, nodo[0], limite=10)
                    for p in partner:
                        p["aroma_condiviso"] = _condivisi_con(cur, nodo[0], p["ingrediente"])
                    partner.sort(key=lambda x: (-x["aroma_condiviso"], -x["valore"]))
                    forti = [p for p in partner if p["aroma_condiviso"] > 0][:5]
                    solo_bil = [p for p in partner if p["aroma_condiviso"] == 0][:4]
                    out.append({
                        "perche": f"{nodo[1]} e' {asse} {assi[asse]} -> {serve} per bilanciare",
                        "bilanciano_e_condividono_aroma": forti,
                        "bilanciano_soltanto": [p["ingrediente"] for p in solo_bil],
                    })
            cur.close()
        return jsonify({
            "ingrediente": nodo[1], "nodo": nodo[0], "profilo_gusto": assi,
            "assi_dominanti": dominanti or ["(nessuno >= 6)"],
            "bilancio_aroma": out,
            "nota": "Chi BILANCIA e CONDIVIDE AROMA e' il piu' forte. Ipotesi da verificare, non verdetto.",
        })
    except Exception as e:
        return _errore(e)

# --- CREAZIONE UNIFICATA: tutto per costruire attorno a un ingrediente ------------
@bp.route("/v1/criteri/costruisci/<ingrediente>", methods=["GET"])
def criteri_costruisci(ingrediente):
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    try:
        with connessione() as conn:
            cur = conn.cursor()
            nodo = _risolvi_nodo(cur, ingrediente)
            if not nodo:
                cur.close()
                return jsonify({"errore": f"'{ingrediente}' non trovato"}), 404
            cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
            row = cur.fetchone()
            dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
            prop = dd.get("proprieta") or {}
            assi = {k: round(float(prop[k]), 1) for k in ("dolce", "salato", "acido", "amaro", "umami", "grasso", "piccante", "alcolico")
                    if isinstance(prop.get(k), (int, float))}
            try:
                aroma = _base_aromatica(cur, nodo[0], nodo[1], limit=6)
            except Exception:
                aroma = []
            aroma_out = [{"ingrediente": a.get("ingrediente"), "perche": a.get("perche")} for a in aroma]
            dominanti = sorted([a for a, v in assi.items() if v >= 6.0], key=lambda a: -assi[a])
            bil = []
            visti = set()
            for asse in dominanti:
                for serve in _BILANCIA.get(asse, []):
                    if serve in visti:
                        continue
                    visti.add(serve)
                    partner = _alti_in_asse(cur, serve, nodo[0], limite=10)
                    for p in partner:
                        p["aroma_condiviso"] = _condivisi_con(cur, nodo[0], p["ingrediente"])
                    partner.sort(key=lambda x: (-x["aroma_condiviso"], -x["valore"]))
                    forti = [p["ingrediente"] for p in partner if p["aroma_condiviso"] > 0][:5]
                    altri = [p["ingrediente"] for p in partner if p["aroma_condiviso"] == 0][:3]
                    bil.append({"serve": serve, "motivo": f"{asse} {assi[asse]}",
                                "aroma_e_bilancio": forti, "solo_bilancio": altri})
            cur.close()
        return jsonify({
            "ingrediente": nodo[1], "nodo": nodo[0],
            "profilo_gusto": assi or "(profilo non ancora mappato)",
            "partner_aroma": aroma_out,
            "bilancio": bil,
            "nota": "Aroma + gusto + bilancio in una vista. Chi torna in entrambi e' il piu' forte. Ipotesi da verificare.",
        })
    except Exception as e:
        return _errore(e)

# --- FASE 2.2: SINERGIA UMAMI (glutammato x nucleotidi) ---
_NUCLEOTIDI = {
    "manzo": "inosinato", "maiale": "inosinato", "pollo": "inosinato", "salmone": "inosinato",
    "tonno": "inosinato", "gamberi": "inosinato", "acciughe": "inosinato", "prosciutto": "inosinato",
    "katsuobushi": "inosinato", "bonito": "inosinato", "sardine": "inosinato",
    "funghi secchi": "guanilato", "shiitake essiccato": "guanilato", "porcini": "guanilato",
    "funghi": "guanilato", "shiitake": "guanilato",
}
_GLUTAMMATO_RICCHI = {
    "pomodoro", "parmigiano", "cheddar", "miso", "salsa di soia", "colatura", "kombu",
    "piselli", "mais", "aglio", "alga",
}


@bp.route("/v1/criteri/umami-sinergia/<ingrediente>", methods=["GET"])
def criteri_umami_sinergia(ingrediente):
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    il = (ingrediente or "").strip().lower()
    glu = _GLU_CORE.get(il, 0)
    e_glutammato = (il in _GLUTAMMATO_RICCHI) or (glu >= 120)
    e_nucleotide = il in _NUCLEOTIDI
    partner = []
    if e_glutammato:
        partner = [{"ingrediente": k, "tipo": v} for k, v in _NUCLEOTIDI.items()]
        ruolo = "glutammato"
        spiega = f"'{ingrediente}' e' ricco di GLUTAMMATO. Abbinalo a una sorgente di NUCLEOTIDI: la sinergia moltiplica l'umami (fino a ~8x)."
    elif e_nucleotide:
        partner = [{"ingrediente": k, "tipo": "glutammato"} for k in sorted(_GLUTAMMATO_RICCHI)]
        ruolo = _NUCLEOTIDI[il]
        spiega = f"'{ingrediente}' e' ricco di {ruolo.upper()} (nucleotide). Abbinalo a una sorgente di GLUTAMMATO: la sinergia moltiplica l'umami."
    else:
        ruolo = "nessuna famiglia forte"
        spiega = f"'{ingrediente}' non e' sorgente forte di glutammato ne' nucleotidi: la sinergia umami non e' la sua leva."
    return jsonify({
        "ingrediente": ingrediente, "famiglia_umami": ruolo, "spiegazione": spiega,
        "partner_sinergia": partner,
        "esempi_classici": ["pomodoro+acciuga", "carne+pomodoro (ragu)", "brodo+funghi secchi", "dashi (kombu+katsuobushi)"],
        "nota": "Sinergia glutammato x nucleotidi: fatto di scienza alimentare. Liste curate da letteratura.",
    })

# --- COPERTURA DATI: la mappa dei buchi (read-only) ---
@bp.route("/v1/criteri/copertura", methods=["GET"])
def criteri_copertura():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    try:
        with connessione() as conn:
            cur = conn.cursor()
            base = ("FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto') "
                    "AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'")
            def c(extra, params=()):
                cur.execute(f"SELECT COUNT(*) {base} {extra}", params)
                return cur.fetchone()[0]
            totale = c("")
            gusto = c("AND n.data ? 'proprieta' AND (n.data->'proprieta') ?| "
                      "array['dolce','salato','acido','amaro','umami','grasso']")
            sci = c("AND n.data ? 'nome_scientifico' AND length(n.data->>'nome_scientifico') > 0")
            foto = c("AND n.data ? 'immagine' AND length(n.data->>'immagine') > 0")
            comp = c("AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')")
            cur.close()
        def pct(x):
            return round(100.0 * x / totale, 1) if totale else 0
        return jsonify({
            "totale_ingredienti": totale,
            "profilo_gusto": {"n": gusto, "pct": pct(gusto)},
            "nome_scientifico": {"n": sci, "pct": pct(sci)},
            "foto": {"n": foto, "pct": pct(foto)},
            "composti": {"n": comp, "pct": pct(comp)},
            "nota": "Mappa di copertura: dove sono i buchi.",
        })
    except Exception as e:
        return _errore(e)

# --- COPERTURA: NOMI SCIENTIFICI (binomi certi) ---
_SCIENTIFICO = {
    "pomodoro": "Solanum lycopersicum", "limone": "Citrus limon", "lime": "Citrus aurantiifolia",
    "mela": "Malus domestica", "fragola": "Fragaria x ananassa", "aglio": "Allium sativum",
    "cipolla": "Allium cepa", "carota": "Daucus carota", "patata": "Solanum tuberosum",
    "spinaci": "Spinacia oleracea", "basilico": "Ocimum basilicum", "menta": "Mentha",
    "timo": "Thymus vulgaris", "rosmarino": "Salvia rosmarinus", "salvia": "Salvia officinalis",
    "origano": "Origanum vulgare", "zafferano": "Crocus sativus", "cardamomo": "Elettaria cardamomum",
    "cumino": "Cuminum cyminum", "coriandolo": "Coriandrum sativum", "pepe nero": "Piper nigrum",
    "zenzero": "Zingiber officinale", "cannella": "Cinnamomum verum", "garofano": "Syzygium aromaticum",
    "noce moscata": "Myristica fragrans", "vaniglia": "Vanilla planifolia", "mandorle": "Prunus dulcis",
    "nocciole": "Corylus avellana", "noci": "Juglans regia", "cacao": "Theobroma cacao",
    "caffe": "Coffea arabica", "mango": "Mangifera indica", "pera": "Pyrus communis",
    "uva": "Vitis vinifera", "banana": "Musa", "arancia": "Citrus sinensis",
    "pompelmo": "Citrus paradisi", "ananas": "Ananas comosus", "melograno": "Punica granatum",
    "champignon": "Agaricus bisporus", "shiitake": "Lentinula edodes", "porcini": "Boletus edulis",
    "finferli": "Cantharellus cibarius", "riso": "Oryza sativa", "orzo": "Hordeum vulgare",
    "farina": "Triticum aestivum", "farina di segale": "Secale cereale", "farina di avena": "Avena sativa",
    "manzo": "Bos taurus", "maiale": "Sus scrofa domesticus", "pollo": "Gallus gallus domesticus",
    "salmone": "Salmo salar", "tonno": "Thunnus", "acciughe": "Engraulis encrasicolus",
    "olio di oliva": "Olea europaea", "friarielli": "Brassica rapa subsp. sylvestris",
    "manioca": "Manihot esculenta", "scarola": "Cichorium endivia", "cicoria": "Cichorium intybus",
    "daikon": "Raphanus sativus", "cetriolo": "Cucumis sativus", "peperone": "Capsicum annuum",
    "melanzana": "Solanum melongena", "zucchero": "Beta vulgaris / Saccharum officinarum",
}


@bp.route("/v1/criteri/nomi-scientifici", methods=["GET", "POST"])
def criteri_nomi_scientifici():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    scritti = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it, binomio in sorted(_SCIENTIFICO.items()):
                r = {"ingrediente": nome_it, "binomio": binomio}
                fisso = _USDA_NODO_FISSO.get(nome_it)
                nodo = None
                if fisso:
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (fisso,))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    r["stato"] = "nodo non trovato"
                    righe.append(r)
                    continue
                r["nodo"] = nodo[0]
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                    if not (dd.get("nome_scientifico") or "").strip():
                        dd["nome_scientifico"] = binomio
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                        scritti += 1
                        r["stato"] = "scritto"
                    else:
                        r["stato"] = "gia presente"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "scritti": scritti, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- FIX: garofano = spezia Syzygium (nodo ahn_clove), non fiore Dianthus ---
_USDA_NODO_FISSO["garofano"] = "ahn_clove"


# --- DIAGNOSTICO (sola lettura): ingredienti USATI senza profilo gusto ---
@bp.route("/v1/criteri/gusto-da-fare", methods=["GET"])
def criteri_gusto_da_fare():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT n.id, n.name, COUNT(e.from_id) AS usi
                FROM nodes n
                JOIN edges e ON e.to_id = n.id AND e.relation = 'usa_reagente'
                WHERE n.type IN ('Ingrediente','Prodotto')
                GROUP BY n.id, n.name
                ORDER BY usi DESC
            """)
            usati = cur.fetchall()
            da_fare = []
            coperti = 0
            for rid, nome, usi in usati:
                cur.execute("SELECT data FROM nodes WHERE id=%s", (rid,))
                row = cur.fetchone()
                dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                prop = dd.get("proprieta") or {}
                assi = [k for k in ("dolce","salato","acido","amaro","umami","grasso","piccante","alcolico") if isinstance(prop.get(k),(int,float))]
                if assi:
                    coperti += 1
                else:
                    da_fare.append({"nodo": rid, "nome": nome, "usato_in": usi})
            cur.close()
        return jsonify({
            "usati_totali": len(usati),
            "con_gusto": coperti,
            "senza_gusto": len(da_fare),
            "da_fare": da_fare[:80],
            "nota": "Ingredienti usati nei protocolli ma senza gusto, ordinati per frequenza d'uso.",
        })
    except Exception as e:
        return _errore(e)

# --- COPERTURA GUSTO: nodi-base piu usati (USDA verificato, pin esatto) ---
_USDA_CORE.update({
    "olio": 171413,
    "latte intero": 171265,
    "zucchero a velo": 169655,
    "destrosio": 169655,
})
_USDA_NODO_FISSO.update({
    "olio": "ing-base-olio",
    "latte intero": "ing-latte-intero",
    "zucchero a velo": "ing-zucchero-a-velo",
    "destrosio": "ing-destrosio",
})

# --- COPERTURA GUSTO 2: nodi usati, riuso valori verificati, pin esatto ---
_USDA_CORE.update({
    "cioccolato": 170272,
    "caffe espresso": 171890,
    "albumi": 172183,
    "panna fresca": 2346386,
    "mandorle intere": 170567,
})
_PH_CORE.update({
    "cioccolato": 5.5, "caffe espresso": 5.0, "albumi": 9.0,
    "panna fresca": 6.6, "mandorle intere": 6.5,
    "succo di limone": 2.3, "succo di lime": 2.4,
})
_GLU_CORE.update({
    "cioccolato": 50, "caffe espresso": 20, "albumi": 20,
    "panna fresca": 5, "mandorle intere": 40,
    "succo di limone": 3, "succo di lime": 3,
})
_USDA_NODO_FISSO.update({
    "cioccolato": "ing-base-cioccolato",
    "caffe espresso": "prod_caffe_espresso",
    "albumi": "ing-albumi",
    "panna fresca": "ing-panna-fresca-35",
    "mandorle intere": "ing-mandorle",
    "succo di limone": "fis_lemon_juice",
    "succo di lime": "fis_lime_juice",
})
_BILANCIA["piccante"] = ["grasso", "dolce", "acido"]


# --- COPERTURA PICCANTE (7o asse): Scoville per i peperoncini, pungenza stimata per le spezie ---
_PICCANTE_CORE = {
    "peperoncino":           {"v": 6.5, "stato": "derivato", "base": "Scoville ~30-50k (medio)",  "nodo": "ai_peperoncino"},
    "peperoncino habanero":  {"v": 9.0, "stato": "derivato", "base": "Scoville ~150-350k",         "nodo": "ing-peperoncino-habanero"},
    "peperoncino calabrese": {"v": 6.0, "stato": "derivato", "base": "Scoville ~25-40k",           "nodo": "ing-peperoncino-calabrese"},
    "pepe nero":             {"v": 3.5, "stato": "stimato",  "base": "piperina, pungenza moderata", "nodo": "ing-pepe-nero-in-pasticceria"},
    "pepe bianco":           {"v": 3.5, "stato": "stimato",  "base": "piperina",                   "nodo": None},
    "zenzero":               {"v": 3.0, "stato": "stimato",  "base": "gingerolo",                  "nodo": None},
    "senape":                {"v": 5.0, "stato": "stimato",  "base": "isotiocianato di allile",    "nodo": None},
    "rafano":                {"v": 7.0, "stato": "stimato",  "base": "isotiocianato, molto pungente", "nodo": None},
    "wasabi":                {"v": 7.5, "stato": "stimato",  "base": "isotiocianato",              "nodo": None},
}

@bp.route("/v1/criteri/piccante", methods=["GET", "POST"])
def criteri_piccante():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    scritti = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it, info in sorted(_PICCANTE_CORE.items()):
                r = {"ingrediente": nome_it, "piccante": info["v"], "stato_dato": info["stato"]}
                nodo = None
                if info.get("nodo"):
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (info["nodo"],))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    r["stato"] = "nodo non trovato"
                    righe.append(r); continue
                r["nodo"] = nodo[0]
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                    prop = dd.get("proprieta") or {}
                    fonti = dd.get("proprieta_fonti") or {}
                    cur_v = prop.get("piccante")
                    if not isinstance(cur_v, (int, float)) or cur_v == 0:
                        prop["piccante"] = info["v"]
                        fonti["piccante"] = {"stato": info["stato"], "fonte": "Scoville/pungenza", "base": info["base"]}
                        dd["proprieta"] = prop
                        dd["proprieta_fonti"] = fonti
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                        scritti += 1
                        r["stato"] = "scritto"
                    else:
                        r["stato"] = "gia presente"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "scritti": scritti, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- FIX senape: non alliaria (garlic mustard) ma senape vera + semi ---
_PICCANTE_CORE["senape"]["nodo"] = "ahn_mustard"
_PICCANTE_CORE["semi di senape nera"]   = {"v": 6.0, "stato": "stimato", "base": "isotiocianato, seme nero", "nodo": "ing-semi-di-senape-nera"}
_PICCANTE_CORE["semi di senape gialla"] = {"v": 4.0, "stato": "stimato", "base": "isotiocianato, seme giallo", "nodo": "ing-semi-di-senape-gialla"}

# --- COPERTURA ALCOLICO (8o asse): ABV reale -> 0..10, derivato ---
_ANCORE_ALCOL = [(0, 0), (5, 2), (12, 4), (20, 6), (40, 8.5), (60, 10)]
_ABV_CORE = {
    "rum bianco":     {"abv": 40, "nodo": "ing-rum-bianco"},
    "rum scuro":      {"abv": 40, "nodo": "ing-rum-scuro"},
    "bourbon":        {"abv": 40, "nodo": "ing-bourbon"},
    "vodka":          {"abv": 40, "nodo": "ing-vodka"},
    "vermouth rosso": {"abv": 16, "nodo": "ing-vermouth-rosso"},
    "prosecco":       {"abv": 11, "nodo": "ing-prosecco-per-sorbetti"},
    "gin":            {"abv": 40, "nodo": None},
    "tequila":        {"abv": 38, "nodo": None},
    "whisky":         {"abv": 40, "nodo": None},
    "brandy":         {"abv": 40, "nodo": None},
    "cognac":         {"abv": 40, "nodo": None},
    "campari":        {"abv": 25, "nodo": None},
    "aperol":         {"abv": 11, "nodo": None},
    "triple sec":     {"abv": 40, "nodo": None},
    "limoncello":     {"abv": 30, "nodo": None},
}
_BILANCIA["alcolico"] = ["dolce", "acido"]

@bp.route("/v1/criteri/alcolico", methods=["GET", "POST"])
def criteri_alcolico():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    scritti = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nome_it, info in sorted(_ABV_CORE.items()):
                val = _scala(info["abv"], _ANCORE_ALCOL)
                r = {"ingrediente": nome_it, "abv": info["abv"], "alcolico": val}
                nodo = None
                if info.get("nodo"):
                    cur.execute("SELECT id, name FROM nodes WHERE id=%s", (info["nodo"],))
                    rr = cur.fetchone()
                    if rr:
                        nodo = (rr[0], rr[1])
                if not nodo:
                    nodo = _risolvi_nodo(cur, nome_it)
                if not nodo:
                    r["stato"] = "nodo non trovato"
                    righe.append(r); continue
                r["nodo"] = nodo[0]
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (nodo[0],))
                    row = cur.fetchone()
                    dd = row[0] if (row and isinstance(row[0], dict)) else (_json.loads(row[0]) if (row and row[0]) else {})
                    prop = dd.get("proprieta") or {}
                    fonti = dd.get("proprieta_fonti") or {}
                    cur_v = prop.get("alcolico")
                    if not isinstance(cur_v, (int, float)) or cur_v == 0:
                        prop["alcolico"] = val
                        fonti["alcolico"] = {"stato": "derivato", "fonte": "ABV", "base": f"{info['abv']}% vol"}
                        dd["proprieta"] = prop
                        dd["proprieta_fonti"] = fonti
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(dd, ensure_ascii=False), nodo[0]))
                        scritti += 1
                        r["stato"] = "scritto"
                    else:
                        r["stato"] = "gia presente"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "scritti": scritti, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- CATENA: PREPARAZIONE -> INGREDIENTE DERIVATO (vertical slice) ---
_PREPARAZIONI = {
    "prep-cordiale-al-lime": {
        "name": "Cordiale al lime (preparazione)",
        "ricetta": "ric-cls-cordiale-al-lime",
        "proprieta": {"acido": 6.0, "dolce": 6.5},
        "fonti": {
            "acido": {"stato": "stimato", "fonte": "calcolo da ricetta",
                      "base": "succo di lime pH~2.4 diluito 1:1 con acqua, bilanciato da 100g zucchero/400ml"},
            "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta",
                      "base": "100 g zucchero in ~400 ml (~25%)"},
        },
        "preparazione": {
            "deriva_da_ricetta": "ric-cls-cordiale-al-lime",
            "resa": "~450 ml",
            "condizioni": "zucchero sciolto a caldo e raffreddato; succo di lime filtrato a crudo",
            "versione_processo": "v1",
            "nota_trasformazione": "profilo bilanciato, NON somma: diluizione + zucchero abbassano l'acido del lime da ~9 a ~6",
        },
    },
}

@bp.route("/v1/criteri/preparazione-derivata", methods=["GET", "POST"])
def criteri_preparazione_derivata():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    creati = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for nid, spec in sorted(_PREPARAZIONI.items()):
                r = {"nodo": nid, "name": spec["name"], "deriva_da": spec["ricetta"], "proprieta": spec["proprieta"]}
                cur.execute("SELECT 1 FROM ricette WHERE id=%s", (spec["ricetta"],))
                if not cur.fetchone():
                    r["stato"] = "ricetta d'origine non trovata"
                    righe.append(r); continue
                data = {
                    "proprieta": spec["proprieta"],
                    "proprieta_fonti": spec["fonti"],
                    "preparazione": spec["preparazione"],
                    "tipo_nodo": "preparazione",
                }
                if applica:
                    cur.execute(
                        "INSERT INTO nodes (id, name, type, data) VALUES (%s,%s,'Prodotto',%s) "
                        "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, data=EXCLUDED.data",
                        (nid, spec["name"], _json.dumps(data, ensure_ascii=False)))
                    creati += 1
                    r["stato"] = "creato/aggiornato"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "creati": creati, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- FIX FENOMENI PREPARAZIONI (passo 1 revisore): oleo saccharum -> osmosi+estrazione ---
_PREP_FENOMENI = {
    "ric-cls-oleo-saccharum-classico":           [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
    "ric-fig-oleo-saccharum-speziato":           [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
    "ric-fig-oleo-saccharum-affumicato":         [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
    "ric-fig-oleo-saccharum-ai-frutti-di-bosco": [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
}

@bp.route("/v1/criteri/prep-fenomeni", methods=["GET", "POST"])
def criteri_prep_fenomeni():
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    import json as _json
    applica = (request.args.get("conferma") or "") == "applica"
    if applica and not _admin_ok():
        return jsonify({"errore": "scrittura: non autorizzato"}), 403
    righe = []
    aggiornati = 0
    try:
        with connessione() as conn:
            cur = conn.cursor()
            for rid, fen in sorted(_PREP_FENOMENI.items()):
                cur.execute("SELECT fenomeni FROM ricette WHERE id=%s", (rid,))
                row = cur.fetchone()
                r = {"ricetta": rid}
                if not row:
                    r["stato"] = "ricetta non trovata"
                    righe.append(r); continue
                r["vecchio"] = row[0]
                r["nuovo"] = [f["nome"] for f in fen]
                if applica:
                    cur.execute("UPDATE ricette SET fenomeni=%s::jsonb WHERE id=%s",
                                (_json.dumps(fen, ensure_ascii=False), rid))
                    aggiornati += 1
                    r["stato"] = "aggiornato"
                righe.append(r)
            if applica:
                conn.commit()
            cur.close()
        return jsonify({"modo": "APPLICATO" if applica else "DRY-RUN", "aggiornati": aggiornati, "righe": righe})
    except Exception as e:
        return _errore(e)

# --- ESTENSIONE CATENA: oleo saccharum come ingrediente derivato ---
_PREPARAZIONI["prep-oleo-saccharum"] = {
    "name": "Oleo Saccharum (preparazione)",
    "ricetta": "ric-cls-oleo-saccharum-classico",
    "proprieta": {"dolce": 8.0, "aroma_fresco": 7.0},
    "fonti": {
        "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta",
                  "base": "sciroppo saturo: lo zucchero scioglie negli oli/acqua estratti dalla scorza"},
        "aroma_fresco": {"stato": "stimato", "fonte": "calcolo da ricetta",
                         "base": "oli essenziali agrumati estratti dalla scorza per osmosi"},
    },
    "preparazione": {
        "deriva_da_ricetta": "ric-cls-oleo-saccharum-classico",
        "resa": "~1 parte sciroppo oleoso per scorza+zucchero",
        "condizioni": "macerazione 4-6 h; OLTRE estrae oli amari dalla parte bianca (punto critico)",
        "versione_processo": "v1",
        "nota_trasformazione": "profilo NON somma: lo zucchero NON e' piu' solo dolce, porta gli oli agrumati estratti",
        "fenomeni": [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
    },
}

# --- resa delle preparazioni (per il costo coerente) ---
_PREPARAZIONI["prep-cordiale-al-lime"]["preparazione"]["resa_ml"] = 450
_PREPARAZIONI["prep-oleo-saccharum"]["preparazione"]["resa_ml"] = 250

# --- ESTENSIONE CATENA 2: shrub (acidulato) + vermouth infuso (alcolico) ---
_PREPARAZIONI["prep-shrub-frutti-rossi"] = {
    "name": "Shrub ai frutti rossi (preparazione)",
    "ricetta": "ric-cls-shrub-ai-frutti-rossi",
    "proprieta": {"acido": 7.0, "dolce": 6.0, "aroma_fresco": 6.0},
    "fonti": {
        "acido": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "aceto di mele (pH~3.5) + acidi dei frutti rossi"},
        "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "250 g zucchero, bilanciato dall'aceto"},
        "aroma_fresco": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "frutti rossi macerati"},
    },
    "preparazione": {
        "deriva_da_ricetta": "ric-cls-shrub-ai-frutti-rossi",
        "resa_ml": 600,
        "condizioni": "macerazione; piu' lunga = piu' estrazione aromi (punto critico)",
        "versione_processo": "v1",
        "nota_trasformazione": "profilo NON somma: l'aceto porta l'acido, la macerazione estrae gli aromi della frutta",
        "fenomeni": [{"nome": "Estrazione", "slug": "fen-estrazione"}, {"nome": "Infusione e macerazione", "slug": "fen-infusione"}],
    },
}
_PREPARAZIONI["prep-vermouth-infuso"] = {
    "name": "Vermouth Infuso (preparazione)",
    "ricetta": "ric-cls-vermouth-infuso-classico",
    "proprieta": {"alcolico": 5.0, "amaro": 5.0, "dolce": 3.0, "aroma_caldo": 4.0},
    "fonti": {
        "alcolico": {"stato": "stimato", "fonte": "vermouth tipico ~16-18% vol", "base": "ATTENZIONE: la ricetta d'origine (750ml vino + 250ml alcol neutro) darebbe ~30%, quantita alcol DA VERIFICARE"},
        "amaro": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "botaniche amare: assenzio, genziana"},
        "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "100 g zucchero"},
        "aroma_caldo": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "erbe aromatiche infuse"},
    },
    "preparazione": {
        "deriva_da_ricetta": "ric-cls-vermouth-infuso-classico",
        "resa_ml": 1100,
        "condizioni": "infusione; tempo cruciale per sviluppare gli aromi (punto critico)",
        "versione_processo": "v1",
        "nota_trasformazione": "profilo NON somma: le botaniche portano amaro e aroma; l'alcol fortifica il vino",
        "fenomeni": [{"nome": "Infusione e macerazione", "slug": "fen-infusione"}],
    },
}

# --- ESTENSIONE CATENA 3: oleo affumicato (aroma caldo) + vermouth speziato ---
_PREPARAZIONI["prep-oleo-saccharum-affumicato"] = {
    "name": "Oleo Saccharum Affumicato (preparazione)",
    "ricetta": "ric-fig-oleo-saccharum-affumicato",
    "proprieta": {"dolce": 8.0, "aroma_caldo": 6.0, "aroma_fresco": 5.0},
    "fonti": {
        "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "150 g zucchero saturo di oli estratti"},
        "aroma_caldo": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "affumicatura (hickory/melo), <60C per non bruciare gli oli (punto critico)"},
        "aroma_fresco": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "oli agrumati di limone e lime"},
    },
    "preparazione": {
        "deriva_da_ricetta": "ric-fig-oleo-saccharum-affumicato",
        "resa_ml": 200,
        "condizioni": "osmosi scorze+zucchero; affumicatura a freddo <60C",
        "versione_processo": "v1",
        "nota_trasformazione": "profilo NON somma: l'affumicatura aggiunge aroma caldo che gli ingredienti crudi non hanno",
        "fenomeni": [{"nome": "Osmosi", "slug": "fen-osmosi"}, {"nome": "Estrazione", "slug": "fen-estrazione"}],
    },
}
_PREPARAZIONI["prep-vermouth-speziato"] = {
    "name": "Vermouth Infuso Speziato (preparazione)",
    "ricetta": "ric-fig-vermouth-infuso-speziato",
    "proprieta": {"alcolico": 4.0, "aroma_caldo": 6.0, "amaro": 4.0, "dolce": 3.0},
    "fonti": {
        "alcolico": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "vermouth rosso ~16% diluito con 200ml acqua -> ~12-13%"},
        "aroma_caldo": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "cannella, chiodi di garofano, cardamomo infusi"},
        "amaro": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "base vermouth (botaniche)"},
        "dolce": {"stato": "stimato", "fonte": "calcolo da ricetta", "base": "50 g zucchero"},
    },
    "preparazione": {
        "deriva_da_ricetta": "ric-fig-vermouth-infuso-speziato",
        "resa_ml": 950,
        "condizioni": "infusione <50-55C per non estrarre amari dalle spezie (punto critico)",
        "versione_processo": "v1",
        "nota_trasformazione": "profilo NON somma: le spezie portano aroma caldo; l'acqua abbassa l'alcol del vermouth base",
        "fenomeni": [{"nome": "Infusione e macerazione", "slug": "fen-infusione"}],
    },
}

# --- COPERTURA GUSTO 3: peperone (pin al nodo usato) + capperi (acido da pH) ---
_USDA_NODO_FISSO.update({
    "peperone": "ing-base-peperone",
    "capperi": "ing-capperi",
})
_PH_CORE.update({
    "capperi": 3.4,
})