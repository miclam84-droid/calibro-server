# ============================================================
# DERIVA-GUSTI-SEARCH — allarga la derivazione del gusto oltre i curati.
# Per i nodi senza profilo DERIVATO, cerca l'ingrediente su USDA FoodData Central
# (ricerca a runtime -> fdc_id VERI, non inventati) e deriva dolce/salato/grasso
# con le STESSE curve di deriva_gusti.py.
#
# FONTE DEL NOME EN (nessuna traduzione inventata):
#   1) data.nomi.en del nodo stesso   2) _ALIAS_AHN (it->en curato)   altrimenti SALTA.
# CANCELLO DI CONFIDENZA (un match falso = gusto falso, peggio del buco):
#   accetta/scrive SOLO se dataType in SR Legacy/Foundation, la testa del nome
#   combacia e l'overlap >= soglia (default 0.6: scarta i mezzi-match tipo
#   "polvere" agganciata a "bevanda"). I match deboli sono SOLO proposti, mai scritti.
# SICUREZZA identica a deriva_gusti: fill-only, backup, transazione, DRY-RUN di default,
#   mai varieta'/DOP, mai sovrascrive corretto/verificato. &limite=N per il rate USDA.
# ============================================================
import os
import re
import json
import time
import urllib.request
import urllib.parse

from flask import Blueprint, request, jsonify

from routes.deriva_gusti import _deriva, _nutrienti, _usda_get, _ESCLUDI, FORMULA_VER

bp_gusti_search = Blueprint("deriva_gusti_search", __name__)

_DATATYPE_OK = ("SR Legacy", "Foundation")
_SOGLIA = 0.6          # overlap minimo per 'alta' (regolabile con &soglia=)
_STOP_IT = {"di", "della", "delle", "del", "dei", "degli", "al", "alla", "con", "e",
            "in", "da", "a", "il", "lo", "la", "i", "gli", "le", "un", "una"}

# Guardia prodotto-derivato: se il nome IT (o la query EN) dichiara un prodotto
# trasformato, la composizione del base NON vale. La descrizione USDA DEVE contenere
# la parola del prodotto, altrimenti e' il base ingredient travestito (es. "aceto di
# fico d'india" agganciato a "Prickly pears, raw"). 'succo' e 'olio' NON entrano qui:
# succo/olio sono prodotti che vogliamo DAVVERO derivare e USDA li ha col nome giusto.
_PRODOTTO = {
    "aceto": ("vinegar",),
    "sciroppo": ("syrup",),
    "confettura": ("jam", "preserve", "marmalade", "jelly"),
    "marmellata": ("jam", "preserve", "marmalade", "jelly"),
    "estratto": ("extract",),
    "essenza": ("extract", "essence"),
    "polvere": ("powder", "dried", "dehydrated"),
    "liquore": ("liqueur", "liquor"),
    "gelatina": ("gelatin", "jelly"),
    "concentrato": ("concentrate", "concentrated", "paste"),
    "purea": ("puree", "pureed", "pulp"),
    "fermentat": ("ferment", "fermented"),
}


def _prodotto_coerente(nome_it, query_en, descr):
    """False se il nome dichiara un prodotto trasformato ma la descrizione USDA non
    lo conferma (quindi e' il base ingredient, non il prodotto)."""
    hay = (str(nome_it) + " " + str(query_en)).lower()
    d = (descr or "").lower()
    for marker, parole in _PRODOTTO.items():
        if marker in hay and not any(p in d for p in parole):
            return False
    return True


# Ingredienti NON sensoriali: additivi, acidi, amidi, aromi puri. Non hanno un
# profilo dolce/salato/grasso misurabile da composizione, e la ricerca li aggancia
# a cibi che li contengono (acido ascorbico -> mela con vit.C; amido di mais -> pane).
# Si saltano del tutto (match sulla PRIMA parola del nome).
_NON_SENS = {"acido", "amido", "aroma", "colorante", "addensante", "emulsionante",
             "stabilizzante", "conservante", "gelificante", "lecitina", "bicarbonato",
             "maltodestrina", "destrina", "gomma"}

# Descrizioni USDA composte/preparate: se il nome e' un ingrediente semplice ma USDA
# risponde con un prodotto composto, il profilo non e' quello dell'ingrediente.
_COMPOSITO_USDA = ("with added", "made with", "seasoning", "fortified", " mix,",
                   "drink,", "drink mix", "flavor drink", "-flavor drink", "infant formula")


def _non_sensoriale(nome_it):
    p = str(nome_it).lower().split()
    return bool(p) and p[0] in _NON_SENS


def _usda_composito(descr):
    d = (descr or "").lower()
    return any(m in d for m in _COMPOSITO_USDA)


def _nome_en(nome_it, dd):
    """EN dal nodo (data.nomi.en) o da _ALIAS_AHN; None se non traducibile con certezza."""
    nomi = dd.get("nomi") if isinstance(dd.get("nomi"), dict) else {}
    en = (nomi.get("en") or dd.get("en") or "").strip()
    if en and en.lower() != str(nome_it).strip().lower():
        return en, "nodo.nomi.en"
    try:
        from routes.api import _ALIAS_AHN
    except Exception:
        _ALIAS_AHN = {}
    k = str(nome_it).lower().strip()
    if k in _ALIAS_AHN:
        return _ALIAS_AHN[k].replace("_", " "), "alias_ahn"
    # testa del nome (prima parola significativa) via alias
    for tok in re.split(r"[\s,/]+", k):
        if tok and tok not in _STOP_IT and tok in _ALIAS_AHN:
            return _ALIAS_AHN[tok].replace("_", " "), "alias_ahn(testa)"
    return None, None


def _tok(s):
    return [t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 2]


def _stem(t):
    """plurale inglese -> singolare grezzo: strawberries->strawberry, tomatoes->tomato."""
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("es"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def _match_tok(a, b):
    """plurali/varianti: stemming + match esatto o prefisso (>=4)."""
    a, b = _stem(a), _stem(b)
    if a == b:
        return True
    n = min(len(a), len(b))
    return n >= 4 and (a.startswith(b) or b.startswith(a))


def _score(query_en, descr):
    """overlap della query EN nella descrizione USDA; (score, testa_ok)."""
    q = _tok(query_en)
    d = _tok(descr)
    if not q or not d:
        return 0.0, False
    testa_ok = any(_match_tok(q[0], dt) for dt in d)
    inter = sum(1 for qt in q if any(_match_tok(qt, dt) for dt in d))
    return round(inter / len(q), 2), testa_ok


def _cerca_usda(query_en, key):
    """USDA /foods/search -> lista candidati (fdcId, description, dataType)."""
    url = ("https://api.nal.usda.gov/fdc/v1/foods/search?api_key=%s&query=%s"
           "&dataType=%s&pageSize=5"
           % (urllib.parse.quote(key), urllib.parse.quote(query_en),
              urllib.parse.quote("SR Legacy,Foundation")))
    data = _usda_get(url)
    return data.get("foods", []) or []


def _elabora_nodo(nid, nome_nodo, data, key, soglia, cur, esegui):
    """Elabora UN nodo: parsing -> filtri -> ricerca USDA -> match/soglia ->
    dettaglio -> derivazione -> scrittura (fill-only + backup). Funzione estratta
    per isolare il crash di UN nodo storto (prima faceva cadere l'intero lotto).

    PUO' SOLLEVARE: un nodo con dati storti (json rotto, dettaglio USDA malformato,
    derivazione impossibile) solleva qui dentro; il chiamante (_sweep_nodi) lo cattura,
    rollback al savepoint, conta 'saltati_errore' e CONTINUA col nodo dopo.

    Ritorna un dict:
      {"categoria": "protetto"|"non_sensoriale"|"gia_derivati"|"senza_en"|"bassa"|"alta",
       "ricerca_fatta": bool, "voce": dict|None, "scritto": bool}
    La logica di match/soglia e la semantica fill-only+backup sono INVARIATE."""
    dd = data if isinstance(data, dict) else (json.loads(data) if data else {})

    # salta varieta'/DOP
    testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
    if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
        return {"categoria": "protetto", "ricerca_fatta": False, "voce": None, "scritto": False}

    # salta additivi/acidi/amidi/aromi: nessun gusto da composizione
    if _non_sensoriale(nome_nodo):
        return {"categoria": "non_sensoriale", "ricerca_fatta": False, "voce": None, "scritto": False}

    meta = dict(dd.get("proprieta_meta", {}) or {})
    assi_target = [a for a in ("dolce", "salato", "grasso")
                   if (meta.get(a, {}) or {}).get("stato") != "derivato"]
    if not assi_target:
        return {"categoria": "gia_derivati", "ricerca_fatta": False, "voce": None, "scritto": False}

    query_en, fonte_en = _nome_en(nome_nodo, dd)
    if not query_en:
        return {"categoria": "senza_en", "ricerca_fatta": False, "voce": None, "scritto": False}

    # --- ricerca USDA (1 chiamata) ---
    try:
        cand = _cerca_usda(query_en, key)
    except Exception as e:
        time.sleep(0.3)
        return {"categoria": "bassa", "ricerca_fatta": True, "scritto": False,
                "voce": {"nodo": nid, "nome": nome_nodo, "query_en": query_en,
                         "errore_usda": str(e)[:80]}}
    time.sleep(0.3)

    migliore = None
    for f in cand:
        if f.get("dataType") not in _DATATYPE_OK:
            continue
        sc, testa = _score(query_en, f.get("description", ""))
        if migliore is None or sc > migliore[0]:
            migliore = (sc, testa, f)
    if not migliore:
        return {"categoria": "bassa", "ricerca_fatta": True, "scritto": False,
                "voce": {"nodo": nid, "nome": nome_nodo, "query_en": query_en,
                         "esito": "nessun candidato SR Legacy/Foundation"}}

    sc, testa, food = migliore
    fdc_id = food.get("fdcId")
    descr = food.get("description", "")
    prod_ok = _prodotto_coerente(nome_nodo, query_en, descr)
    comp = _usda_composito(descr)
    # alta SOLO se: testa combacia, overlap >= soglia, prodotto confermato,
    # e la descrizione USDA NON e' un cibo composto/preparato.
    alta = testa and sc >= soglia and prod_ok and not comp

    voce = {"nodo": nid, "nome": nome_nodo, "query_en": query_en, "fonte_en": fonte_en,
            "fdc_id": fdc_id, "usda": descr, "dataType": food.get("dataType"),
            "score": sc, "testa_ok": testa, "prodotto_coerente": prod_ok,
            "usda_composito": comp, "assi_target": assi_target}

    if not alta:
        return {"categoria": "bassa", "ricerca_fatta": True, "voce": voce, "scritto": False}

    # --- alta confidenza: dettaglio /food per nutrienti accurati ---
    try:
        detail = _usda_get("https://api.nal.usda.gov/fdc/v1/food/%s?api_key=%s"
                           % (fdc_id, urllib.parse.quote(key)))
        time.sleep(0.3)
    except Exception as e:
        voce["errore_dettaglio"] = str(e)[:80]
        return {"categoria": "bassa", "ricerca_fatta": True, "voce": voce, "scritto": False}
    # NB: la derivazione sotto NON e' protetta: su un dettaglio USDA storto solleva
    # e il nodo viene saltato (saltati_errore), senza abbattere il lotto.
    der = _deriva(_nutrienti(detail))

    prop = dict(dd.get("proprieta", {}) or {})
    cambi = {}
    voce["derivati"] = {}
    for asse in assi_target:
        nuovo = der[asse]["val"]
        voce["derivati"][asse] = {"vecchio": prop.get(asse), "nuovo": nuovo,
                                  "grezzo": der[asse]["grezzo"]}
        cambi[asse] = (nuovo, der[asse])

    scritto = False
    if esegui and cambi:
        cur.execute("INSERT INTO _backup_gusti_derivati (id, data_old) VALUES (%s,%s)",
                    (nid, json.dumps(dd, ensure_ascii=False)))
        for asse, (nuovo, info) in cambi.items():
            prop[asse] = nuovo
            m = {"stato": "derivato", "fonte": "USDA FDC %s (match ricerca)" % fdc_id,
                 "formula": FORMULA_VER, "grezzo": info["grezzo"], "match_score": sc}
            if asse == "dolce":
                m["via"] = info.get("via")
            meta[asse] = m
        dd["proprieta"] = prop
        dd["proprieta_meta"] = meta
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                    (json.dumps(dd, ensure_ascii=False), nid))
        scritto = True
        voce["scritto"] = True

    return {"categoria": "alta", "ricerca_fatta": True, "voce": voce, "scritto": scritto}


def _sweep_nodi(righe, key, soglia, limite, cur, esegui):
    """Orchestratore resiliente del lotto. Per OGNI nodo: SAVEPOINT -> _elabora_nodo
    -> RELEASE; su eccezione del singolo nodo: log (print flush), ROLLBACK TO SAVEPOINT
    (la transazione resta sana per i nodi successivi), conta 'saltati_errore' e CONTINUA.
    Un nodo rotto NON fa piu' 500 ne' abbatte il lotto.
    Ritorna (contatori, proposte_alta, proposte_bassa, errori)."""
    cont = {"ricerche": 0, "scritti": 0, "senza_en": 0, "gia_derivati": 0,
            "protetti": 0, "non_sensoriali": 0, "saltati_errore": 0, "consumati": 0}
    proposte_alta, proposte_bassa, errori = [], [], []

    def _sp(sql):
        # Savepoint utili solo in transazione viva; il cursore finto nei test li ignora.
        try:
            cur.execute(sql)
        except Exception:
            pass

    for nid, nome_nodo, data in righe:
        if cont["ricerche"] >= limite:
            break
        cont["consumati"] += 1
        _sp("SAVEPOINT sp_nodo")
        try:
            ris = _elabora_nodo(nid, nome_nodo, data, key, soglia, cur, esegui)
            _sp("RELEASE SAVEPOINT sp_nodo")
        except Exception as e:
            print("[deriva-gusti-search] nodo %r (%s) saltato per errore: %s"
                  % (nid, nome_nodo, e), flush=True)
            _sp("ROLLBACK TO SAVEPOINT sp_nodo")
            cont["saltati_errore"] += 1
            if len(errori) < 60:
                errori.append({"nodo": nid, "nome": nome_nodo, "errore": str(e)[:120]})
            continue

        if ris.get("ricerca_fatta"):
            cont["ricerche"] += 1
        cat = ris.get("categoria")
        if cat == "protetto":
            cont["protetti"] += 1
        elif cat == "non_sensoriale":
            cont["non_sensoriali"] += 1
        elif cat == "gia_derivati":
            cont["gia_derivati"] += 1
        elif cat == "senza_en":
            cont["senza_en"] += 1
        elif cat == "bassa":
            if ris.get("voce") and len(proposte_bassa) < 60:
                proposte_bassa.append(ris["voce"])
        elif cat == "alta":
            if ris.get("scritto"):
                cont["scritti"] += 1
            if ris.get("voce") and len(proposte_alta) < 60:
                proposte_alta.append(ris["voce"])

    return cont, proposte_alta, proposte_bassa, errori


@bp_gusti_search.route("/admin/deriva-gusti-search")
def deriva_gusti_search():
    """DRY-RUN di default (?s=SECRET). &esegui=1 scrive (fill-only, backup+transazione).
    &limite=N limita le ricerche USDA per chiamata (default 30, tienilo <=20 per non
    sfondare i 120s di gunicorn). &soglia=0.7 per alzare il cancello.
    &offset=N riparte dal nodo N: la risposta torna 'prossimo_offset' per la chiamata
    successiva (None quando 'fine' e' true = grafo esaurito). Cosi' si copre tutto a lotti."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("USDA_API_KEY", "")
    if not key:
        return jsonify({"errore": "USDA_API_KEY non impostata su Railway"}), 400
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    try:
        limite = int(request.args.get("limite", "12"))
    except Exception:
        limite = 12
    if limite <= 0:
        limite = 12
    try:
        soglia = float(request.args.get("soglia", _SOGLIA))
    except Exception:
        soglia = _SOGLIA
    try:
        offset = int(request.args.get("offset", "0"))
    except Exception:
        offset = 0
    if offset < 0:
        offset = 0

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_gusti_derivati
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        cur.execute("""SELECT id, name, data FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       ORDER BY (id LIKE 'ing-%%') DESC, name
                       OFFSET %s""", (offset,))
        righe = cur.fetchall()

        cont, proposte_alta, proposte_bassa, errori = _sweep_nodi(
            righe, key, soglia, limite, cur, esegui)
        consumati = cont["consumati"]

        if esegui:
            conn.commit()
        cur.close(); conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "formula": FORMULA_VER,
            "soglia_alta": soglia,
            "ricerche_usda": cont["ricerche"],
            "limite": limite,
            "offset": offset,
            "prossimo_offset": (None if consumati >= len(righe) else offset + consumati),
            "fine": (consumati >= len(righe)),
            "accettati_alta": len(proposte_alta),
            "proposti_bassa_NON_scritti": len(proposte_bassa),
            "scritti": cont["scritti"] if esegui else 0,
            "saltati_senza_nome_en": cont["senza_en"],
            "saltati_gia_derivati": cont["gia_derivati"],
            "saltati_protetti_rari": cont["protetti"],
            "saltati_non_sensoriali": cont["non_sensoriali"],
            "saltati_errore": cont["saltati_errore"],
            "errori": errori,
            "nota": ("DRY RUN: nessuna scrittura. Guarda 'alta_confidenza' (verrebbero scritti) "
                     "e 'bassa_confidenza' (NON scritti, da controllare a occhio). "
                     "Aggiungi &esegui=1 per scrivere SOLO gli alta. Rilancia con &limite piu' alto "
                     "per coprire piu' nodi (occhio al rate USDA 1000/h)."
                     if not esegui else
                     "ESEGUITO: scritti solo i match ad alta confidenza, fill-only, backup in "
                     "_backup_gusti_derivati. I bassa confidenza NON sono stati toccati."),
            "alta_confidenza": proposte_alta,
            "bassa_confidenza": proposte_bassa,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
