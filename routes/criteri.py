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

bp = Blueprint("criteri", __name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

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


def _conn():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


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
    return None


def _base_aromatica(cur, ing_id, base_nome, limit=12, min_shared=3, pool=120):
    """Criterio 1: ingredienti che condividono composti volatili reali.
    - solo partner INGREDIENTE canonico (niente nodi 'Prodotto' = varianti/tagli che copiano la chimica);
    - COUNT(DISTINCT): il grafo ha archi doppi;
    - filtro firma aromatica: stessa firma di composti = di fatto stessa famiglia -> max 2;
    - robustezza RELATIVA al miglior risultato di questo ingrediente (la soglia assoluta non ha senso)."""
    cur.execute(
        r"""
        SELECT n.name,
               COUNT(DISTINCT b.to_id) AS shared,
               (array_agg(DISTINCT b.to_id ORDER BY b.to_id))[1:6] AS compounds
        FROM edges a
        JOIN edges b ON a.to_id = b.to_id AND b.relation = 'contiene_composto'
        JOIN nodes n ON n.id = b.from_id
        WHERE a.from_id = %s AND a.relation = 'contiene_composto'
          AND b.from_id <> %s
          AND n.type = 'Ingrediente'
          AND n.padre_ahn_id IS NULL
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND n.name NOT LIKE '%%\_%%'
          AND LOWER(n.name) NOT LIKE LOWER(%s)
        GROUP BY n.name
        HAVING COUNT(DISTINCT b.to_id) >= %s
        ORDER BY shared DESC, n.name ASC
        LIMIT %s
        """,
        (ing_id, ing_id, f"%{base_nome}%", min_shared, pool),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    max_n = max(int(r[1]) for r in rows) or 1
    out = []
    firma_count = {}
    for name, shared, compounds in rows:
        ids = list(compounds or [])
        firma = tuple(sorted(ids)[:5])
        if firma and firma_count.get(firma, 0) >= 2:
            continue  # stessa firma = stessa famiglia -> max 2
        firma_count[firma] = firma_count.get(firma, 0) + 1
        frac = int(shared) / max_n
        banda = "Alta" if frac >= 0.6 else ("Media" if frac >= 0.33 else "Esplorativa")
        comps = [_nome_composto(c) for c in ids]
        out.append({
            "ingrediente": name,
            "criterio": "base_aromatica",
            "evidenza": {"composti_condivisi": int(shared), "composti": comps},
            "robustezza": banda,
            "perche": "condivide una base aromatica"
                      + (f" — {shared} composti ({', '.join(comps[:3])})" if comps else f" — {shared} composti"),
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


@bp.route("/v1/criteri/<ingrediente>", methods=["GET"])
def criteri(ingrediente):
    """Relazioni di un ingrediente, per criterio, con evidenza reale. NIENTE percentuale di abbinabilita'."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "relazioni": [], "nota": "DB non disponibile"})
    conn = None
    try:
        conn = _conn()
        cur = conn.cursor()
        nodo = _risolvi_nodo(cur, ingrediente)
        if not nodo:
            cur.close(); conn.close()
            return jsonify({"ingrediente": ingrediente, "relazioni": [],
                            "non_riconosciuto": True,
                            "nota": "Ingrediente non trovato nel grafo con un profilo di composti."})
        ing_id, ing_nome = nodo
        base = _base_aromatica(cur, ing_id, ing_nome)
        trad = _tradizione(cur, ing_id)
        cur.close(); conn.close()
        # declassa gli hub generici (riuso il filtro gia' provato di api.py)
        try:
            from routes.api import _pulisci_abbinamenti
            base = _pulisci_abbinamenti(base, campo="ingrediente", max_famiglia=3, ingrediente_base=ing_nome)
        except Exception:
            pass
        base = base[:12]
        nomi_base = {r["ingrediente"].lower() for r in base}
        trad = [r for r in trad if r["ingrediente"].lower() not in nomi_base]
        return jsonify({
            "ingrediente": ing_nome,
            "nodo_id": ing_id,
            "regola": "Matter mostra perche' una relazione esiste, non un voto di compatibilita'.",
            "relazioni": base + trad,
            "conteggio": {"base_aromatica": len(base), "tradizione": len(trad)},
        })
    except Exception as e:
        if conn:
            try: conn.close()
            except Exception: pass
        return jsonify({"ingrediente": ingrediente, "errore": str(e)[:160]}), 500


@bp.route("/v1/criteri/diag/<ingrediente>", methods=["GET"])
def criteri_diag(ingrediente):
    """Diagnostica: quale nodo e' stato risolto e quanti composti ha."""
    if not DATABASE_URL:
        return jsonify({"nota": "DB non disponibile"})
    conn = None
    try:
        conn = _conn()
        cur = conn.cursor()
        nodo = _risolvi_nodo(cur, ingrediente)
        if not nodo:
            cur.close(); conn.close()
            return jsonify({"ingrediente": ingrediente, "trovato": False})
        ing_id, ing_nome = nodo
        cur.execute("SELECT COUNT(*) FROM edges WHERE from_id=%s AND relation='contiene_composto'", (ing_id,))
        n_comp = cur.fetchone()[0]
        cur.execute(
            "SELECT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto' LIMIT 8", (ing_id,))
        esempi = [_nome_composto(r[0]) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({
            "cercato": ingrediente,
            "nodo_risolto": ing_id,
            "nome_mostrato": ing_nome,
            "composti_totali": n_comp,
            "composti_esempio": esempi,
        })
    except Exception as e:
        if conn:
            try: conn.close()
            except Exception: pass
        return jsonify({"errore": str(e)[:160]}), 500
