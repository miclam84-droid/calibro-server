# -*- coding: utf-8 -*-
# MOTORE CRITERI (Laboratorio) — modulo pulito, NON tocca api_abbina.
# Decisioni congelate 8 ott 2026 (DECISIONI-LABORATORIO-CONGELATE).
#
# Regola costituzionale di questa sezione:
#   Matter NON assegna un voto alla compatibilita'. Mostra PERCHE' una relazione esiste.
#   Sempre: numero reale -> criterio -> interpretazione. Mai: numero inventato -> percentuale -> verdetto.
#
# Criteri V1 (questo file: 1 e 4; il bridging (2) arriva come pezzo successivo, dopo verifica su dati veri):
#   1 BASE AROMATICA  = composti volatili realmente condivisi (archi contiene_composto). Con i NOMI dei composti.
#   4 TRADIZIONE      = accostamenti documentati (archi abbinamento_tradizionale). Etichettati come CULTURA, non chimica.
#
# Robustezza = forza dell'evidenza molecolare (quanti composti condivisi), NON probabilita' che "piaccia".
# Le soglie qui sotto sono una PRIMA proposta: vanno calibrate guardando l'output sui tuoi ingredienti veri.
#
# NB verifica: questo modulo non e' stato eseguito su DB reale in fase di scrittura (il sandbox non ha DATABASE_URL).
# Primo passo dopo il deploy: aprire /v1/criteri/pomodoro, /fragola, /parmigiano e GUARDARE l'output.

import os
import json
from flask import Blueprint, jsonify, request

bp = Blueprint("criteri", __name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# ── Robustezza: composti condivisi -> banda (dichiarata, non una probabilita') ──
_SOGLIA_ALTA = 8     # >= 8 composti condivisi = base aromatica forte
_SOGLIA_MEDIA = 4    # 4-7 = media ;  < 4 = esplorativa


def _banda(n):
    if n >= _SOGLIA_ALTA:
        return "Alta"
    if n >= _SOGLIA_MEDIA:
        return "Media"
    return "Esplorativa"


def _nome_composto(cid):
    """comp_linalool -> 'linalool'. NON inventa traduzioni italiane: mostra il nome pulito del composto."""
    return (cid or "").replace("comp_", "").replace("_", " ").strip()


def _conn():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def _risolvi_nodo(cur, ingrediente):
    """Trova il nodo che ha DAVVERO i composti.
    Problema reale: 'pomodoro' (nodo italiano) ha 0 composti; i composti stanno sul padre 'ahn_tomato'.
    Strategia: prendo il nodo-match con piu' archi contiene_composto (il 'ricco'); se e' magro e ha
    padre_ahn_id, salto al padre. Coerente con l'Italian Knowledge Layer di api_abbina.
    Ritorna (id, name_display) oppure None.
    """
    ing = (ingrediente or "").strip()
    cur.execute(
        """
        SELECT n.id, n.name, n.padre_ahn_id, COUNT(e.to_id) AS nc
        FROM nodes n
        LEFT JOIN edges e ON e.from_id = n.id AND e.relation = 'contiene_composto'
        WHERE n.type IN ('Ingrediente','Prodotto')
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND (LOWER(n.name) = LOWER(%s)
               OR LOWER(n.name) LIKE LOWER(%s)
               OR LOWER(n.id) = LOWER(%s))
        GROUP BY n.id, n.name, n.padre_ahn_id
        ORDER BY nc DESC, LENGTH(n.name) ASC
        LIMIT 1
        """,
        (ing, f"%{ing}%", "ahn_" + ing.lower().replace(" ", "_")),
    )
    row = cur.fetchone()
    if not row:
        return None
    nid, nname, padre, nc = row[0], row[1], row[2], row[3]
    # se il nodo trovato e' magro di composti ma ha un padre Ahn, uso il padre (che ha la chimica)
    if (nc or 0) < 2 and padre:
        cur.execute("SELECT id, name FROM nodes WHERE id = %s LIMIT 1", (padre,))
        p = cur.fetchone()
        if p:
            return (p[0], nname)  # id del padre (per la chimica), ma mostro il nome italiano cercato
    return (nid, nname)


def _base_aromatica(cur, ing_id, escludi_id, limit=12, min_shared=2):
    """Criterio 1: ingredienti che condividono composti volatili reali.
    Query a specchio del motore 'scoperta' di /v1/possibilita (gia' provato sul DB reale).
    Esclude i nascosti (oli essenziali 95/5) e i nomi-dataset grezzi (con underscore)."""
    cur.execute(
        r"""
        SELECT n.name,
               COUNT(*) AS shared,
               (array_agg(a.to_id ORDER BY a.to_id))[1:5] AS compounds
        FROM edges a
        JOIN edges b ON a.to_id = b.to_id AND b.relation = 'contiene_composto'
        JOIN nodes n ON n.id = b.from_id
        WHERE a.from_id = %s AND a.relation = 'contiene_composto'
          AND b.from_id <> %s
          AND n.type IN ('Ingrediente','Prodotto')
          AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
          AND n.name NOT LIKE '%%\_%%'
        GROUP BY n.name
        HAVING COUNT(*) >= %s
        ORDER BY shared DESC, n.name ASC
        LIMIT %s
        """,
        (ing_id, escludi_id, min_shared, limit),
    )
    out = []
    for name, shared, compounds in cur.fetchall():
        comps = [_nome_composto(c) for c in (compounds or [])]
        out.append({
            "ingrediente": name,
            "criterio": "base_aromatica",
            "evidenza": {"composti_condivisi": int(shared), "composti": comps},
            "robustezza": _banda(int(shared)),
            "perche": "condivide una base aromatica"
                      + (f" — {shared} composti ({', '.join(comps[:3])})" if comps else f" — {shared} composti"),
        })
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
                "robustezza": None,  # la tradizione non ha robustezza molecolare: e' cultura
                "perche": "accostamento tradizionale documentato (cultura, non chimica)",
            })
    except Exception:
        pass  # relazione non presente / tabella vuota
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
                            "nota": "Ingrediente non trovato nel grafo."})
        ing_id, ing_nome = nodo
        base = _base_aromatica(cur, ing_id, ing_id)
        trad = _tradizione(cur, ing_id)
        cur.close(); conn.close()
        # tradizione in coda, de-duplicata rispetto alla base
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
    """Diagnostica: mostra quale nodo e' stato risolto e quanti composti ha. Serve a GUARDARE
    se la risoluzione nodo (italiano -> padre Ahn) funziona davvero, prima di fidarsi dei risultati."""
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
