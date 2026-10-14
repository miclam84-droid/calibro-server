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
#   combacia e l'overlap >= soglia. I match deboli sono SOLO proposti, mai scritti.
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
_SOGLIA = 0.5          # overlap minimo per 'alta'
_STOP_IT = {"di", "della", "delle", "del", "dei", "degli", "al", "alla", "con", "e",
            "in", "da", "a", "il", "lo", "la", "i", "gli", "le", "un", "una"}


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


@bp_gusti_search.route("/admin/deriva-gusti-search")
def deriva_gusti_search():
    """DRY-RUN di default (?s=SECRET). &esegui=1 scrive (fill-only, backup+transazione).
    &limite=N limita il numero di ricerche USDA (default 30, per il rate 1000/h)."""
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
        limite = int(request.args.get("limite", "30"))
    except Exception:
        limite = 30
    if limite <= 0:
        limite = 30

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
                       ORDER BY (id LIKE 'ing-%%') DESC, name""")
        righe = cur.fetchall()

        ricerche = 0
        scritti = 0
        senza_en = 0
        gia_derivati = 0
        protetti = 0
        proposte_alta, proposte_bassa = [], []

        for nid, nome_nodo, data in righe:
            if ricerche >= limite:
                break
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})

            # salta varieta'/DOP
            testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                protetti += 1
                continue

            meta = dict(dd.get("proprieta_meta", {}) or {})
            assi_target = [a for a in ("dolce", "salato", "grasso")
                           if (meta.get(a, {}) or {}).get("stato") != "derivato"]
            if not assi_target:
                gia_derivati += 1
                continue

            query_en, fonte_en = _nome_en(nome_nodo, dd)
            if not query_en:
                senza_en += 1
                continue

            # --- ricerca USDA (1 chiamata) ---
            ricerche += 1
            try:
                cand = _cerca_usda(query_en, key)
            except Exception as e:
                proposte_bassa.append({"nodo": nid, "nome": nome_nodo, "query_en": query_en,
                                       "errore_usda": str(e)[:80]})
                time.sleep(0.3)
                continue
            time.sleep(0.3)

            migliore = None
            for f in cand:
                if f.get("dataType") not in _DATATYPE_OK:
                    continue
                sc, testa = _score(query_en, f.get("description", ""))
                if migliore is None or sc > migliore[0]:
                    migliore = (sc, testa, f)
            if not migliore:
                proposte_bassa.append({"nodo": nid, "nome": nome_nodo, "query_en": query_en,
                                       "esito": "nessun candidato SR Legacy/Foundation"})
                continue

            sc, testa, food = migliore
            fdc_id = food.get("fdcId")
            descr = food.get("description", "")
            alta = testa and sc >= _SOGLIA

            voce = {"nodo": nid, "nome": nome_nodo, "query_en": query_en, "fonte_en": fonte_en,
                    "fdc_id": fdc_id, "usda": descr, "dataType": food.get("dataType"),
                    "score": sc, "testa_ok": testa, "assi_target": assi_target}

            if not alta:
                if len(proposte_bassa) < 60:
                    proposte_bassa.append(voce)
                continue

            # --- alta confidenza: dettaglio /food per nutrienti accurati ---
            try:
                detail = _usda_get("https://api.nal.usda.gov/fdc/v1/food/%s?api_key=%s"
                                   % (fdc_id, urllib.parse.quote(key)))
                time.sleep(0.3)
            except Exception as e:
                voce["errore_dettaglio"] = str(e)[:80]
                proposte_bassa.append(voce)
                continue
            der = _deriva(_nutrienti(detail))

            prop = dict(dd.get("proprieta", {}) or {})
            cambi = {}
            voce["derivati"] = {}
            for asse in assi_target:
                nuovo = der[asse]["val"]
                voce["derivati"][asse] = {"vecchio": prop.get(asse), "nuovo": nuovo,
                                          "grezzo": der[asse]["grezzo"]}
                cambi[asse] = (nuovo, der[asse])

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
                scritti += 1
                voce["scritto"] = True

            if len(proposte_alta) < 60:
                proposte_alta.append(voce)

        if esegui:
            conn.commit()
        cur.close(); conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "formula": FORMULA_VER,
            "soglia_alta": _SOGLIA,
            "ricerche_usda": ricerche,
            "limite": limite,
            "accettati_alta": len(proposte_alta),
            "proposti_bassa_NON_scritti": len(proposte_bassa),
            "scritti": scritti if esegui else 0,
            "saltati_senza_nome_en": senza_en,
            "saltati_gia_derivati": gia_derivati,
            "saltati_protetti_rari": protetti,
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
