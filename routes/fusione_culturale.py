# -*- coding: utf-8 -*-
# ============================================================
# FUSIONE CULTURALE — Ondata 3 (V1 ONESTA, sola lettura)
#
# VISIONE (16 ott): "fusione culturale" = trovare ponti aromatici TRA cucine
# diverse — un ingrediente di una tradizione che si lega a uno di un'altra
# tramite composti condivisi (rete Ahn 2011).
#
# VERDETTO DI FATTIBILITA' (verificato sul grafo, 18 ott):
#   NEL GRAFO NON ESISTE UN DATO DI CUCINA/CULTURA per ingrediente.
#   - nodes.domain sugli ingredienti Ahn = CATEGORIA alimentare (flower, meat,
#     spice, fruit...), NON una cucina.  Vedi grafo/seed-ahn-ingredienti.sql.
#   - data->>'categoria' = la stessa categoria Ahn.  Non e' una cucina.
#   - ricette.disciplina = bar|cucina|bakery (il mestiere), NON una cucina
#     nazionale.  Vedi grafo/schema-ricette.sql.
#   - data->>'regione' esiste SOLO su un sottoinsieme di varieta' italiane
#     (Atlante biodiversita', DOP/IGP: Campania, Sicilia...) e sta su nodi-varieta'
#     che di norma NON portano la chimica aromatica (i composti stanno sul padre
#     Ahn canonico).  E' provenienza intra-italiana, NON una cucina del mondo.
#   - routes/api.py dichiara esplicitamente: "la regione dei piatti non e' un
#     dato verificato nel corpus".
#
# CONSEGUENZA: non si puo' etichettare l'origine culturale di un ingrediente
# senza inventarla.  Quindi questo endpoint NON inventa cucine.  Fa il ponte
# ONESTO: dato un ingrediente, trova ingredienti che condividono composti
# aromatici REALI (archi contiene_composto, rete Ahn), mostrando per ciascuno
# solo dati veri: la CATEGORIA alimentare Ahn e, SE presente, la regione italiana.
#
# Il pezzo "cultura" resta PENDENTE: vedi data/FUSIONE-CULTURALE-cosa-serve.md
# per l'esatto dato di cucina che servirebbe alla V1 vera.
#
# Regola costituzionale (come criteri.py): numero reale -> criterio -> perche'.
# Mai cucina inventata, mai abbinamento non sorretto da composti condivisi reali.
# ============================================================
import os
import math

from flask import Blueprint, request, jsonify

try:
    from db import _get_conn, _release_conn
except Exception:  # pragma: no cover
    _get_conn = _release_conn = None

bp_fusione = Blueprint("fusione_culturale", __name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# varianti "preparate" da evitare (coerente con criteri.py)
_PREP_RX = r"roast|smoke|dried|dry|filter|grill|fried|cured|_oil"


def _nome_composto(cid):
    """comp_pub_1_octanol -> '1 octanol'. Toglie prefissi tecnici, non inventa traduzioni."""
    s = (cid or "").replace("comp_", "")
    if s.startswith("pub_"):
        s = s[4:]
    return s.replace("_", " ").strip()


# ------------------------------------------------------------------
# LOGICA PURA — ponti via composti condivisi, con peso IDF per rarita'.
# Nessun DB, nessuna rete: testabile in isolamento (tests/test_fusione_culturale.py).
# ------------------------------------------------------------------
def ponti_aromatici(base_comps, partner_comps, df, n_tot,
                    min_shared=3, limit=12):
    """Classifica i partner per FORZA del ponte aromatico.

    Input (tutto dato reale estratto dal grafo, qui solo aritmetica):
      base_comps   : set/iterable degli id-composto dell'ingrediente base.
      partner_comps: dict  nome_partner -> set/iterable di id-composto del partner.
      df           : dict  id-composto -> document frequency (in quanti ingredienti
                     compare quel composto in tutto il grafo). Serve all'IDF.
      n_tot        : int   numero totale di ingredienti con composti (per l'IDF).

    Punteggio (identico in spirito a criteri._base_aromatica):
      - ogni composto condiviso pesa ln(n_tot / df)  -> i comuni (df alto) pesano ~0,
        i caratterizzanti (df basso) pesano tanto. Uccide gli hub (te', birra).
      - normalizzazione per sqrt(|base| * |partner|) -> non premia i profili enormi.
      - si tengono solo i partner con almeno `min_shared` composti condivisi.
      - 'composti_condivisi' mostra i piu' RARI (i caratterizzanti) prima.

    Ritorna lista ordinata di dict:
      {ingrediente, n_condivisi, indice_rarita, composti_condivisi:[nomi], perche}
    """
    base = set(base_comps or ())
    if not base:
        return []
    n_tot = max(int(n_tot or 0), 2)
    grezzi = []
    for nome, comps in (partner_comps or {}).items():
        pset = set(comps or ())
        shared = base & pset
        if len(shared) < min_shared:
            continue
        # peso IDF di ogni composto condiviso
        idf = {c: math.log(n_tot / max(float(df.get(c, 1) or 1), 1.0)) for c in shared}
        somma = sum(idf.values())
        score = somma / math.sqrt(max(len(base), 1) * max(len(pset), 1))
        # composti condivisi ordinati dal piu' raro (df piu' basso) al meno
        comps_rari = sorted(shared, key=lambda c: (df.get(c, 1), c))
        grezzi.append({
            "ingrediente": nome,
            "n_condivisi": len(shared),
            "_score": score,
            "_comps": comps_rari,
        })
    if not grezzi:
        return []
    max_score = max(g["_score"] for g in grezzi) or 1.0
    grezzi.sort(key=lambda g: (-g["_score"], -g["n_condivisi"], g["ingrediente"]))
    out = []
    for g in grezzi[:limit]:
        nomi = [_nome_composto(c) for c in g["_comps"][:6]]
        frac = g["_score"] / max_score
        banda = "Alta" if frac >= 0.6 else ("Media" if frac >= 0.33 else "Esplorativa")
        n = g["n_condivisi"]
        perche = ("condivide composti caratterizzanti"
                  + (f" — {', '.join(nomi[:3])}"
                     + (f" (e altri, {n} in tutto)" if n > 3 else "")
                     if nomi else f" — {n} composti"))
        out.append({
            "ingrediente": g["ingrediente"],
            "n_condivisi": n,
            "indice_rarita": round(g["_score"], 3),
            "robustezza": banda,
            "composti_condivisi": nomi,
            "perche": perche,
        })
    return out


# ------------------------------------------------------------------
# ACCESSO DATI (sola lettura) — costruisce gli input della logica pura dal grafo.
# ------------------------------------------------------------------
def _risolvi(cur, ingrediente):
    """Trova il nodo canonico con la chimica. Preferisce: non-preparato, nodo ahn_,
    match esatto, con composti veri. Ritorna (id, nome, categoria) o None.
    Coerente con criteri._risolvi_nodo ma restituisce anche la categoria Ahn."""
    ing = (ingrediente or "").strip().lower()
    if not ing:
        return None
    cur.execute(
        r"""
        SELECT n.id, n.name, n.data->>'categoria' AS categoria,
               (CASE WHEN (n.id ~ %s) THEN 1 ELSE 0 END) AS prep,
               (CASE WHEN n.id LIKE 'ahn_%%' THEN 0 ELSE 1 END) AS noncanon,
               (CASE WHEN LOWER(n.name) = %s THEN 0 ELSE 1 END) AS nonexact,
               COUNT(e.to_id) AS nc
        FROM nodes n
        LEFT JOIN edges e ON e.from_id = n.id AND e.relation = 'contiene_composto'
        WHERE n.type IN ('Ingrediente','Prodotto')
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND (LOWER(n.name) = %s OR LOWER(n.name) LIKE %s OR LOWER(n.id) = %s)
        GROUP BY n.id, n.name, n.data
        HAVING COUNT(e.to_id) > 0
        ORDER BY prep ASC, noncanon ASC, nonexact ASC, nc DESC, LENGTH(n.name) ASC
        LIMIT 1
        """,
        (_PREP_RX, ing, ing, f"%{ing}%", "ahn_" + ing.replace(" ", "_")),
    )
    r = cur.fetchone()
    if not r:
        return None
    return (r[0], r[1], r[2])


def _n_tot_ingredienti(cur):
    cur.execute(
        "SELECT GREATEST(COUNT(DISTINCT from_id), 2) FROM edges WHERE relation='contiene_composto'")
    return int((cur.fetchone() or [2])[0])


def _carica_ponti(cur, ing_id):
    """Estrae dal grafo gli input per ponti_aromatici().
    Ritorna (base_comps, partner_comps, partner_meta, df, n_tot).
      partner_meta: nome -> {categoria, regione}  (solo dati veri, mai cucina).
    Partner ammessi: solo INGREDIENTI canonici (niente nodi 'Prodotto'/varianti che
    copiano la chimica del padre), nome senza underscore, non nascosti, != base."""
    # 1) composti del base
    cur.execute(
        "SELECT DISTINCT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto'",
        (ing_id,))
    base_comps = [r[0] for r in cur.fetchall()]
    if not base_comps:
        return [], {}, {}, {}, 2

    # 2) partner che condividono almeno un composto del base, coi composti condivisi
    cur.execute(
        r"""
        SELECT n.name, n.data->>'categoria' AS categoria, n.data->>'regione' AS regione,
               b.to_id AS comp
        FROM edges a
        JOIN edges b ON a.to_id = b.to_id AND b.relation='contiene_composto'
        JOIN nodes n ON n.id = b.from_id
        WHERE a.from_id = %s AND a.relation='contiene_composto'
          AND b.from_id <> %s
          AND n.type = 'Ingrediente'
          AND n.padre_ahn_id IS NULL
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND n.name NOT LIKE '%%\_%%'
        """,
        (ing_id, ing_id),
    )
    partner_comps = {}
    partner_meta = {}
    comp_coinvolti = set(base_comps)
    for name, categoria, regione, comp in cur.fetchall():
        partner_comps.setdefault(name, set()).add(comp)
        comp_coinvolti.add(comp)
        if name not in partner_meta:
            partner_meta[name] = {"categoria": categoria, "regione": regione}

    # 3) df (document frequency) dei soli composti coinvolti — per l'IDF
    df = {}
    if comp_coinvolti:
        ids = list(comp_coinvolti)
        ph = ",".join(["%s"] * len(ids))
        cur.execute(
            f"""SELECT to_id, COUNT(DISTINCT from_id) FROM edges
                WHERE relation='contiene_composto' AND to_id IN ({ph})
                GROUP BY to_id""",
            ids,
        )
        df = {r[0]: int(r[1]) for r in cur.fetchall()}

    n_tot = _n_tot_ingredienti(cur)
    return base_comps, partner_comps, partner_meta, df, n_tot


_NOTA_ONESTA = (
    "Ponte ONESTO via composti aromatici condivisi (rete Ahn 2011). "
    "L'etichetta di CUCINA/CULTURA non e' un dato presente nel grafo: non e' stata "
    "inventata. Qui si mostra solo la categoria alimentare Ahn (e, se presente, la "
    "regione italiana di provenienza). Per la 'fusione culturale' vera servirebbe un "
    "dato di cucina per ingrediente: vedi data/FUSIONE-CULTURALE-cosa-serve.md."
)


@bp_fusione.route("/v1/fusione/<ingrediente>", methods=["GET"])
def fusione(ingrediente):
    """Ponti aromatici per un ingrediente (sola lettura).

    Query param:
      limite               int, default 12, max 30.
      min_condivisi        int, default 3 (soglia composti condivisi).
      solo_altra_categoria 1/true -> tiene solo partner di CATEGORIA Ahn diversa dal
                           base (il ponte piu' "trasversale" possibile con i dati veri;
                           NON e' una cucina, e' una categoria alimentare).

    Risposta:
      {ingrediente, categoria, cucina_disponibile: false, nota, ponti:[...], avviso}
    ogni ponte: {ingrediente, categoria, regione, composti_condivisi, n_condivisi, perche}
    """
    if _get_conn is None:
        return jsonify({"errore": "database non configurato"}), 500
    try:
        limite = max(1, min(int(request.args.get("limite", 12)), 30))
    except (TypeError, ValueError):
        limite = 12
    try:
        min_shared = max(1, min(int(request.args.get("min_condivisi", 3)), 10))
    except (TypeError, ValueError):
        min_shared = 3
    solo_altra = str(request.args.get("solo_altra_categoria", "")).lower() in ("1", "true", "si", "sì", "yes")

    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        risolto = _risolvi(cur, ingrediente)
        if not risolto:
            cur.close()
            return jsonify({
                "ingrediente": ingrediente,
                "trovato": False,
                "cucina_disponibile": False,
                "ponti": [],
                "nota": "Ingrediente non trovato con un profilo aromatico nel grafo.",
            }), 404
        ing_id, nome, categoria_base = risolto
        base_comps, partner_comps, partner_meta, df, n_tot = _carica_ponti(cur, ing_id)
        cur.close()

        ponti = ponti_aromatici(base_comps, partner_comps, df, n_tot,
                                min_shared=min_shared, limit=(limite * 3 if solo_altra else limite))
        # arricchisci con i dati VERI (categoria/regione) e, se richiesto, filtra per categoria diversa
        arricchiti = []
        for p in ponti:
            meta = partner_meta.get(p["ingrediente"], {})
            cat = meta.get("categoria")
            if solo_altra and categoria_base and cat and cat == categoria_base:
                continue
            p_out = {
                "ingrediente": p["ingrediente"],
                "categoria": cat,              # categoria alimentare Ahn (NON cucina)
                "regione": meta.get("regione"),  # provenienza italiana se presente, altrimenti null
                "composti_condivisi": p["composti_condivisi"],
                "n_condivisi": p["n_condivisi"],
                "robustezza": p["robustezza"],
                "indice_rarita": p["indice_rarita"],
                "perche": p["perche"],
            }
            arricchiti.append(p_out)
            if len(arricchiti) >= limite:
                break

        return jsonify({
            "ingrediente": nome,
            "categoria": categoria_base,       # categoria alimentare Ahn (NON cucina)
            "cucina_disponibile": False,       # verdetto onesto: la cucina non e' nel grafo
            "filtro_solo_altra_categoria": solo_altra,
            "ponti": arricchiti,
            "totale": len(arricchiti),
            "nota": _NOTA_ONESTA,
        })
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({"errore": str(e)[:200], "cucina_disponibile": False}), 500
    finally:
        if conn is not None and _release_conn is not None:
            _release_conn(conn)
