# ============================================================
# INGEST SCHELETRO WIKIDATA — amplia il grafo con nodi ingrediente "scheletro".
#
# Tira da Wikidata (CC0, dominio pubblico, uso commerciale libero) le SPECIE di
# una famiglia/categoria botanica e crea NUOVI nodi ingrediente classificati ma
# NON profilati: solo nome + famiglia + QID. Nessun gusto, nessun numero
# sensoriale, niente dati inventati. Ogni nodo nuovo dichiara di essere uno
# scheletro da profilare a mano più tardi.
#
#   data["kind"]  = "scheletro"
#   data["stato"] = "non_profilato"
#   data["famiglia"], data["nome_scientifico"], data["wikidata_qid"]
#   data["fonte"] = "Wikidata CC0"
#
# FILL-ONLY: non duplica mai un nodo che esiste già (confronto per nome e per
# QID Wikidata). DRY-RUN di default (?s=SECRET); con &esegui=1 scrive dentro una
# transazione, registrando gli id inseriti in _ingest_scheletro_log (per poter
# disfare col clic). AMBITO LIMITATO per chiamata: una famiglia/categoria alla
# volta, con &limite/&offset per lavorare a blocchi (Wikidata ha rate-limit).
#
# Gira LATO SERVER (la rete Wikidata è aperta lì). Due servizi Wikidata:
#   - w/api.php  (wbsearchentities / wbgetentities): risolve il nome famiglia -> QID.
#   - query.wikidata.org/sparql: elenca le specie sotto quel QID (P171* + rango specie).
# Il servizio SPARQL (WDQS) ogni tanto è in rate-limit/outage: in quel caso
# l'endpoint lo dice onestamente invece di inventare dati.
#
# I PARSER e la logica fill-only sono funzioni PURE, testate senza rete né DB
# (tests/test_ingest_skeleton.py).
# ============================================================
import os
import re
import json
import time
import hmac
import unicodedata
import urllib.request
import urllib.parse

from flask import Blueprint, request, jsonify

bp_ingest_skeleton = Blueprint("ingest_skeleton", __name__)

_UA = "MatterBench/1.0 (https://web-production-79457.up.railway.app; skeleton ingest)"
_WB_API = "https://www.wikidata.org/w/api.php"
_SPARQL = "https://query.wikidata.org/sparql"

# ranghi tassonomici Wikidata (P105 = rango tassonomico)
_Q_FAMIGLIA = "Q35409"
_Q_GENERE = "Q34740"
_Q_SPECIE = "Q7432"

# Mappa di comodo: nome breve -> nome scientifico della famiglia da risolvere a
# QID runtime (niente QID scritti a mano = niente QID sbagliati). Sono famiglie
# a forte vocazione alimentare: un buon punto di partenza per lo scheletro.
FAMIGLIE_NOTE = {
    "rosacee": "Rosaceae",           # mele, pere, prugne, ciliegie, fragole, mandorle...
    "solanacee": "Solanaceae",       # pomodoro, patata, melanzana, peperone...
    "brassicacee": "Brassicaceae",   # cavoli, rape, senape, rucola...
    "cucurbitacee": "Cucurbitaceae", # zucche, zucchine, cetrioli, meloni...
    "lamiacee": "Lamiaceae",         # basilico, menta, origano, rosmarino, timo...
    "apiacee": "Apiaceae",           # carota, sedano, prezzemolo, finocchio, cumino...
    "fabacee": "Fabaceae",           # fagioli, ceci, lenticchie, piselli, fave...
    "rutacee": "Rutaceae",           # agrumi: limone, arancia, mandarino, lime...
    "liliacee": "Amaryllidaceae",    # aglio, cipolla, porro, scalogno (ex Liliaceae)
    "poacee": "Poaceae",             # cereali: grano, riso, mais, orzo, avena...
}


def _http_json(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# --- FUNZIONI PURE (testabili senza rete né DB) ------------------------------

def _slug(nome):
    """Nome -> slug ascii minuscolo con trattini (max 48 char)."""
    s = unicodedata.normalize("NFKD", (nome or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:48]


def _parse_ricerca(d):
    """Risposta wbsearchentities -> lista di QID candidati, in ordine."""
    out = []
    for it in (d or {}).get("search", []) or []:
        qid = it.get("id")
        if qid and qid.startswith("Q"):
            out.append(qid)
    return out


def _rango_da_entita(d, qid):
    """Risposta wbgetentities -> QID del rango tassonomico (P105) dell'entità, o None.
    Serve a confermare che il QID risolto è davvero una famiglia (o un genere)."""
    ent = (((d or {}).get("entities") or {}).get(qid) or {})
    claims = (ent.get("claims") or {}).get("P105") or []
    for c in claims:
        try:
            return c["mainsnak"]["datavalue"]["value"]["id"]
        except (KeyError, TypeError):
            continue
    return None


def _parse_specie(d):
    """Risposta SPARQL -> lista di specie {qid, nome_scientifico, nome, origine}.
    Dedup per QID, salta righe senza un nome usabile. Nessun dato di gusto."""
    b = (((d or {}).get("results") or {}).get("bindings") or [])
    visti = set()
    out = []
    for row in b:
        def val(k):
            v = (row.get(k) or {}).get("value")
            return v.strip() if isinstance(v, str) and v.strip() else None
        uri = val("item")
        if not uri:
            continue
        qid = uri.rsplit("/", 1)[-1]
        if not qid.startswith("Q") or qid in visti:
            continue
        sci = val("sci")
        nome = val("nome") or sci  # etichetta it/en; in mancanza, il nome scientifico
        if not nome:
            continue
        visti.add(qid)
        rec = {"qid": qid, "nome": nome}
        if sci:
            rec["nome_scientifico"] = sci
        origine = val("origine")
        if origine:
            rec["origine"] = origine
        out.append(rec)
    return out


def _nodo_scheletro(specie, famiglia_nome, famiglia_qid):
    """Costruisce (id, nome, data) di un nodo ingrediente-scheletro. Funzione pura.
    SOLO dati Wikidata: nome, famiglia, QID. Nessun gusto, nessun numero."""
    qid = specie["qid"]
    nome = specie["nome"]
    nid = "scheletro-" + (_slug(nome) or qid.lower()) + "-" + qid.lower()
    data = {
        "kind": "scheletro",
        "stato": "non_profilato",
        "famiglia": famiglia_nome,
        "famiglia_qid": famiglia_qid,
        "wikidata_qid": qid,
        "fonte": "Wikidata CC0",
        "visibility": "public",
    }
    if specie.get("nome_scientifico"):
        data["nome_scientifico"] = specie["nome_scientifico"]
    if specie.get("origine"):
        data["origine"] = specie["origine"]
    return nid, nome, data


def _fill_only(candidati, nomi_esistenti, qid_esistenti):
    """Tiene solo i candidati che NON esistono già nel grafo.
    - nomi_esistenti: set di nomi (già minuscoli) presenti.
    - qid_esistenti:  set di QID Wikidata già collegati a un nodo.
    Dedup anche all'interno del batch (per QID e per nome). Logica pura.
    Ritorna (nuovi, saltati_gia_presenti)."""
    nuovi, saltati = [], 0
    visti_qid, visti_nome = set(), set()
    for c in candidati:
        qid = c.get("qid")
        nome_l = (c.get("nome") or "").strip().lower()
        if qid and (qid in qid_esistenti or qid in visti_qid):
            saltati += 1
            continue
        if nome_l and (nome_l in nomi_esistenti or nome_l in visti_nome):
            saltati += 1
            continue
        if qid:
            visti_qid.add(qid)
        if nome_l:
            visti_nome.add(nome_l)
        nuovi.append(c)
    return nuovi, saltati


def _sparql_specie(qid, limite, offset):
    """Query SPARQL: specie (rango Q7432) sotto il taxon <qid> (catena P171*),
    con nome scientifico e etichetta it/en, origine geografica se c'è.
    ORDER BY ?item -> paginazione stabile con offset/limite."""
    return (
        "SELECT ?item ?sci (COALESCE(?itL,?enL) AS ?nome) ?origine WHERE {"
        " ?item wdt:P171* wd:%s ."
        " ?item wdt:P105 wd:%s ."
        " OPTIONAL { ?item wdt:P225 ?sci. }"
        " OPTIONAL { ?item rdfs:label ?itL. FILTER(LANG(?itL)=\"it\") }"
        " OPTIONAL { ?item rdfs:label ?enL. FILTER(LANG(?enL)=\"en\") }"
        " OPTIONAL { ?item wdt:P495 ?o. ?o rdfs:label ?origine. FILTER(LANG(?origine)=\"it\") }"
        "} ORDER BY ?item OFFSET %d LIMIT %d" % (qid, _Q_SPECIE, offset, limite)
    )


def _sparql_conteggio(qid):
    """Quante specie totali ci sono sotto il taxon (stima d'ambito)."""
    return (
        "SELECT (COUNT(DISTINCT ?item) AS ?n) WHERE {"
        " ?item wdt:P171* wd:%s . ?item wdt:P105 wd:%s ."
        "}" % (qid, _Q_SPECIE)
    )


# --- CHIAMATE WIKIDATA (lato server) -----------------------------------------

def _risolvi_famiglia_qid(nome_scientifico):
    """nome famiglia -> QID, confermando via wbgetentities che il rango è famiglia
    (o genere). Usa solo w/api.php (non il WDQS), quindi funziona anche se SPARQL
    è in outage. Ritorna (qid, rango_qid) o (None, None)."""
    url = _WB_API + "?" + urllib.parse.urlencode({
        "action": "wbsearchentities", "search": nome_scientifico, "language": "en",
        "type": "item", "format": "json", "limit": 5,
    })
    for qid in _parse_ricerca(_http_json(url))[:5]:
        ent_url = _WB_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": qid, "props": "claims", "format": "json",
        })
        try:
            rango = _rango_da_entita(_http_json(ent_url), qid)
        except Exception:
            rango = None
        if rango in (_Q_FAMIGLIA, _Q_GENERE):
            return qid, rango
    return None, None


@bp_ingest_skeleton.route("/admin/ingest-wikidata-skeleton")
def ingest_wikidata_skeleton():
    """Crea nodi ingrediente-scheletro dalle specie di una famiglia Wikidata (CC0).

    Parametri:
      ?s=ADMIN_SECRET          (obbligatorio, gate hmac)
      &famiglia=rosacee        nome famiglia (vedi FAMIGLIE_NOTE) risolto a QID runtime
      &qid=Q46299              in alternativa, il QID della famiglia/genere diretto
      &limite=50               specie per chiamata (cap 300; Wikidata ha rate-limit)
      &offset=0                blocco successivo
      &esegui=1                scrive davvero (default: DRY-RUN, non scrive nulla)

    Fill-only: non duplica nodi già presenti (per nome o per QID). Backup/undo via
    tabella _ingest_scheletro_log. Solo dati Wikidata: nome, famiglia, QID."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET") or ""
    if not hmac.compare_digest(str(request.args.get("s", "")), str(sec)):
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    try:
        limite = int(request.args.get("limite", "50"))
    except ValueError:
        limite = 50
    if limite <= 0 or limite > 300:
        limite = 50  # cap: un blocco sensato, mai 30k nodi in un colpo
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    if offset < 0:
        offset = 0

    # 1) Ambito: risolvi la famiglia/categoria a un QID.
    qid_param = (request.args.get("qid") or "").strip()
    fam_param = (request.args.get("famiglia") or "").strip().lower()
    famiglia_qid = None
    famiglia_nome = None
    if qid_param and re.fullmatch(r"Q\d+", qid_param):
        famiglia_qid = qid_param
        famiglia_nome = request.args.get("nome_famiglia") or qid_param
    elif fam_param:
        nome_sci = FAMIGLIE_NOTE.get(fam_param, request.args.get("famiglia").strip())
        try:
            famiglia_qid, _ = _risolvi_famiglia_qid(nome_sci)
        except Exception as e:
            return jsonify({"errore": f"risoluzione famiglia fallita: {str(e)[:120]}"}), 502
        famiglia_nome = nome_sci
    if not famiglia_qid:
        return jsonify({
            "errore": "ambito mancante: passa &famiglia=<nome> o &qid=Q...",
            "famiglie_note": sorted(FAMIGLIE_NOTE.keys()),
        }), 400

    # 2) Stima d'ambito + elenco specie dal WDQS (può essere in rate-limit/outage).
    stima_specie = None
    try:
        cj = _http_json(_SPARQL + "?" + urllib.parse.urlencode(
            {"format": "json", "query": _sparql_conteggio(famiglia_qid)}))
        b = (((cj or {}).get("results") or {}).get("bindings") or [])
        if b:
            stima_specie = int(b[0]["n"]["value"])
    except Exception:
        stima_specie = None  # best-effort, non blocca

    try:
        dj = _http_json(_SPARQL + "?" + urllib.parse.urlencode(
            {"format": "json", "query": _sparql_specie(famiglia_qid, limite, offset)}), timeout=60)
    except Exception as e:
        return jsonify({
            "errore": "Wikidata SPARQL (WDQS) non raggiungibile adesso",
            "dettaglio": str(e)[:160],
            "nota": ("Il servizio query di Wikidata è a volte in rate-limit/outage. "
                     "La macchina è a posto: riprova più tardi. Il nome famiglia è "
                     "comunque stato risolto."),
            "famiglia": famiglia_nome, "famiglia_qid": famiglia_qid,
            "stima_specie_totali": stima_specie,
        }), 503

    specie = _parse_specie(dj)
    if not specie:
        return jsonify({
            "dry_run": (not esegui), "famiglia": famiglia_nome, "famiglia_qid": famiglia_qid,
            "offset": offset, "limite": limite, "stima_specie_totali": stima_specie,
            "candidati": 0, "nota": "nessuna specie in questo blocco (prova offset più basso?)",
        })

    # 3) Fill-only: carica nomi e QID già presenti, scarta chi esiste.
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        cur.execute("SELECT LOWER(name) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        nomi_esistenti = {r[0] for r in cur.fetchall() if r[0]}
        cur.execute("""SELECT DISTINCT data->>'wikidata_qid' FROM nodes
                       WHERE data ? 'wikidata_qid'""")
        qid_esistenti = {r[0] for r in cur.fetchall() if r[0]}

        nuovi, saltati = _fill_only(specie, nomi_esistenti, qid_esistenti)
        campione = [_anteprima(_nodo_scheletro(s, famiglia_nome, famiglia_qid)) for s in nuovi[:15]]

        scritti = 0
        if esegui and nuovi:
            cur.execute("""CREATE TABLE IF NOT EXISTS _ingest_scheletro_log
                           (id TEXT, famiglia TEXT, qid TEXT, ts TIMESTAMPTZ DEFAULT NOW())""")
            for s in nuovi:
                nid, nome, data = _nodo_scheletro(s, famiglia_nome, famiglia_qid)
                cur.execute(
                    "INSERT INTO nodes (id, name, type, data) VALUES (%s,%s,'Ingrediente',%s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (nid, nome, json.dumps(data, ensure_ascii=False)))
                if cur.rowcount:
                    cur.execute(
                        "INSERT INTO _ingest_scheletro_log (id, famiglia, qid) VALUES (%s,%s,%s)",
                        (nid, famiglia_nome, s["qid"]))
                    scritti += 1
            conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "dry_run": (not esegui),
            "fonte": "Wikidata (CC0)",
            "famiglia": famiglia_nome, "famiglia_qid": famiglia_qid,
            "offset": offset, "limite": limite,
            "stima_specie_totali": stima_specie,
            "candidati_nel_blocco": len(specie),
            "gia_presenti": saltati,
            "nuovi_da_creare": len(nuovi),
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun nodo creato. &esegui=1 per scrivere; &offset per il "
                     "blocco successivo. I nodi sono 'scheletro' non profilati: nome + "
                     "famiglia + QID, nessun gusto." if not esegui else
                     "ESEGUITO: nodi scheletro creati (fill-only), id loggati in "
                     "_ingest_scheletro_log, marcati stato=non_profilato, fonte Wikidata CC0."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500


def _anteprima(nodo_tuple):
    nid, nome, data = nodo_tuple
    return {"id": nid, "nome": nome, "famiglia": data.get("famiglia"),
            "nome_scientifico": data.get("nome_scientifico"), "qid": data.get("wikidata_qid"),
            "stato": data.get("stato")}
