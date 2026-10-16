# ============================================================
# TASSONOMIA WIKIDATA — classificazione botanica da Wikidata (CC0, dominio pubblico)
# Riempie per ogni ingrediente: nome scientifico, famiglia, genere, origine geografica.
# Fonte CC0 = uso commerciale libero, nessuna attribuzione obbligatoria.
# Gira LATO SERVER (la rete Wikidata è aperta lì). DRY-RUN di default; con &esegui=1
# scrive fill-only (mai sovrascrive), taggato stato:"classificato" + fonte "Wikidata CC0 #Q...".
# Due passi: wbsearchentities (nome→QID, solo se è un taxon) → SPARQL (QID→tassonomia).
# I PARSER sono funzioni pure, testate senza rete (tests/test_tassonomia_wikidata.py).
# ============================================================
import os
import json
import time
import urllib.request
import urllib.parse

from flask import Blueprint, request, jsonify

bp_tax = Blueprint("tassonomia_wikidata", __name__)

_UA = "MatterBench/1.0 (https://web-production-79457.up.railway.app; taxonomy ingest)"
_WB_SEARCH = "https://www.wikidata.org/w/api.php"
_SPARQL = "https://query.wikidata.org/sparql"

# ranghi tassonomici Wikidata
_Q_FAMIGLIA = "Q35409"
_Q_GENERE = "Q34740"


def _http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# --- PARSER PURI (testabili senza rete) ---------------------------------------

def _parse_search(d):
    """Da risposta wbsearchentities -> lista di QID candidati (in ordine)."""
    out = []
    for it in (d or {}).get("search", []) or []:
        qid = it.get("id")
        if qid and qid.startswith("Q"):
            out.append(qid)
    return out


def _parse_taxonomia(d):
    """Da risposta SPARQL -> dict {nome_scientifico, famiglia, genere, origine} (solo presenti)."""
    b = (((d or {}).get("results") or {}).get("bindings") or [])
    if not b:
        return {}
    row = b[0]
    def val(k):
        v = (row.get(k) or {}).get("value")
        return v.strip() if isinstance(v, str) and v.strip() else None
    out = {}
    if val("sci"):
        out["nome_scientifico"] = val("sci")
    if val("familyName"):
        out["famiglia"] = val("familyName")
    if val("genusName"):
        out["genere"] = val("genusName")
    if val("originLabel"):
        out["origine"] = val("originLabel")
    return out


def _sparql_query(qid):
    return (
        "SELECT ?sci ?familyName ?genusName ?originLabel WHERE {"
        " OPTIONAL { wd:%s wdt:P225 ?sci. }"
        " OPTIONAL { wd:%s wdt:P171* ?fam. ?fam wdt:P105 wd:%s; wdt:P225 ?familyName. }"
        " OPTIONAL { wd:%s wdt:P171* ?gen. ?gen wdt:P105 wd:%s; wdt:P225 ?genusName. }"
        " OPTIONAL { wd:%s wdt:P495 ?o. ?o rdfs:label ?originLabel. FILTER(LANG(?originLabel)=\"it\") }"
        "} LIMIT 1" % (qid, qid, _Q_FAMIGLIA, qid, _Q_GENERE, qid)
    )


# --- CHIAMATE WIKIDATA (lato server) ------------------------------------------

def _cerca_qid(nome):
    """Cerca il QID per nome italiano; accetta solo un item che è un taxon (ha P225)."""
    url = _WB_SEARCH + "?" + urllib.parse.urlencode({
        "action": "wbsearchentities", "search": nome, "language": "it",
        "type": "item", "format": "json", "limit": 5,
    })
    for qid in _parse_search(_http_json(url))[:5]:
        tax = _tax_per_qid(qid)
        if tax.get("nome_scientifico"):  # è un taxon vero
            return qid, tax
    return None, {}


def _tax_per_qid(qid):
    url = _SPARQL + "?" + urllib.parse.urlencode({"format": "json", "query": _sparql_query(qid)})
    try:
        return _parse_taxonomia(_http_json(url))
    except Exception:
        return {}


@bp_tax.route("/admin/ingerisci-tassonomia-wikidata")
def ingerisci_tassonomia_wikidata():
    """DRY-RUN di default (?s=SECRET). &esegui=1 scrive (fill-only, backup, transazione).
    &offset / &limite per lavorare a blocchi (evita i timeout). Fonte Wikidata CC0."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    try:
        limite = int(request.args.get("limite", "20"))
    except ValueError:
        limite = 20
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    if offset < 0:
        offset = 0
    if limite <= 0 or limite > 50:
        limite = 20  # cap: Wikidata ha rate-limit, blocchi piccoli

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_tassonomia
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        # ingredienti ordinati, a blocchi; solo quelli SENZA tassonomia già scritta
        cur.execute("""SELECT id, name, data FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       ORDER BY name OFFSET %s LIMIT %s""", (offset, limite))
        righe = cur.fetchall()

        campione, scritti, saltati_nomatch, gia_fatti = [], 0, 0, 0
        for nid, nome, data in righe:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            if dd.get("tassonomia"):  # fill-only: non ritoccare chi ce l'ha
                gia_fatti += 1
                continue
            try:
                qid, tax = _cerca_qid(nome)
            except Exception:
                qid, tax = None, {}
            time.sleep(0.4)  # gentile col rate-limit Wikidata
            if not qid or not tax:
                saltati_nomatch += 1
                continue

            riga = {"nodo": nid, "nome": nome, "qid": qid, "tassonomia": tax}
            campione.append(riga)

            if esegui:
                cur.execute("INSERT INTO _backup_tassonomia (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                dd["tassonomia"] = tax
                dd["tassonomia_meta"] = {"stato": "classificato",
                                         "fonte": f"Wikidata CC0 #{qid}"}
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "dry_run": (not esegui),
            "fonte": "Wikidata (CC0)",
            "offset": offset, "limite": limite,
            "esaminati": len(righe),
            "gia_classificati": gia_fatti,
            "senza_match_taxon": saltati_nomatch,
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato scritto. &esegui=1 per scrivere; "
                     "&offset per il blocco successivo." if not esegui else
                     "ESEGUITO: fill-only, backup in _backup_tassonomia, taggato Wikidata CC0."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500


@bp_tax.route("/v1/tassonomia/<path:nome>")
def leggi_tassonomia(nome):
    """Lettura pubblica: la classificazione botanica di un ingrediente, per la scheda."""
    import psycopg2
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"trovato": False})
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute("""SELECT data FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                       ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (nome,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"trovato": False})
        dd = row[0] if isinstance(row[0], dict) else (json.loads(row[0]) if row[0] else {})
        tax = dd.get("tassonomia") or {}
        meta = dd.get("tassonomia_meta") or {}
        return jsonify({"trovato": bool(tax), "tassonomia": tax, "fonte": meta.get("fonte", "")})
    except Exception:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return jsonify({"trovato": False})
