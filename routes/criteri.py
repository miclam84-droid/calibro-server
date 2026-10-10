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
