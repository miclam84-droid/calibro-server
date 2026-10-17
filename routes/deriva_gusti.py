# ============================================================
# DERIVA-GUSTI-USDA — pipeline del gusto DERIVATO da composizione (USDA FDC)
# Porta dolce/salato/grasso dei comuni da 'stimato' (AI) a 'derivato' (da misura).
# DRY-RUN di default: conta + campione (vecchio stimato vs nuovo derivato), NON scrive.
# Con ?esegui=1: backup + UPDATE in transazione, fill-only, mai sovrascrive corretto/verificato.
# Non tocca gli altri assi, non tocca le varieta' rare/DOP. Curve tarate (van Langeveld), dichiarate.
# Spec: claude/SPEC-PIPELINE-DERIVAZIONE-GUSTO-USDA.md
# ============================================================
import os
import json
import time
import urllib.request
import urllib.parse

from flask import Blueprint, request, jsonify

bp_gusti = Blueprint("deriva_gusti", __name__)

FORMULA_VER = "v1"

# --- Curve di derivazione (misura per 100g -> asse 0-10), ancore tarate su van Langeveld ---
_DOLCE = [(0, 0), (5, 3), (12, 5), (30, 7), (60, 9), (80, 10)]
_SALATO = [(5, 0), (50, 1), (200, 3), (500, 5), (1500, 7), (5000, 9), (15000, 10)]  # sodio mg
_GRASSO = [(0, 0), (3, 2), (10, 4), (20, 6), (35, 8), (60, 10)]

# dolcezza relativa per tipo di zucchero (saccarosio = 1.0)
_SW = {"fruttosio": 1.3, "saccarosio": 1.0, "glucosio": 0.75, "maltosio": 0.45, "lattosio": 0.40}


def _interp(x, pts):
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return round(y0 + (y1 - y0) * (x - x0) / (x1 - x0), 1)
    return 0.0


# --- Match curato ingrediente italiano -> USDA fdc_id (fdc_id gia' verificati, SR Legacy/Foundation) ---
# Solo comuni ad alta confidenza. Le varieta' rare NON entrano qui (si misurano al banco).
_MATCH = {
    "succo di limone": 167747, "succo di lime": 168156, "succo d'arancia": 169098,
    "pomodoro": 170457, "mela": 171688, "fragola": 167762, "lampone": 2346410,
    "mirtillo": 2346411, "pesca": 169928, "albicocca": 171697, "ciliegia": 171719,
    "mango": 169910, "banana": 173944, "uva": 174683,
    "melograno": 169134, "latte": 171265, "panna": 2346386, "burro": 789828,
    "yogurt": 170886, "cheddar": 173414, "albume": 172183,
    "uovo": 171287, "farina": 168944, "farina di segale": 2512375,
    "riso": 169756, "manzo": 174036, "pollo": 171477, "petto di pollo": 171477,
    "salmone": 175167, "maiale": 167903, "agnello": 174404, "tonno": 175159,
    "aglio": 169230, "cipolla": 170000, "carota": 170393,
    "cetriolo": 168409, "peperone": 170108, "spinaci": 168462, "patata": 170026,
    "olio di oliva": 171413, "olio d'oliva": 171413, "zucchero": 169655, "miele": 169640,
    "sciroppo d'acero": 169661, "cioccolato fondente": 170272, "cacao": 169593,
    "caffe": 171890, "aceto balsamico": 172241,
    "champignon": 169251, "mandorla": 170567, "nocciola": 170581, "noce": 170187,
    "zenzero": 169231, "cannella": 171320, "pepe nero": 170931,
    # RE-INSERITI 15/10 — fdc_id ri-verificato live su USDA, descrizione confermata:
    "ananas": 169124,       # Pineapple, raw, all varieties
    "parmigiano": 170848,   # Cheese, parmesan, hard
    "gambero": 175179,      # Crustaceans, shrimp, raw
    "kiwi": 168153,         # Kiwifruit, green, raw   (nessun alias EN -> la ricerca non lo prende)
    "arachidi": 2515376,    # Peanuts, raw            (nessun alias EN -> la ricerca non lo prende)
    # AGGIUNTI 16/10 — fdc_id verificato live, numeri calcolati con formula server e approvati da Michele.
    # Match "ingrediente giusto": scrivono derivato USDA (provvisorio, il banco sovrascrive).
    # NON aggiunti per scelta: pasta di pistacchio (crudo != pasta) e ricotta di pecora (vaccina != pecora) -> al banco.
    "scorza di limone": 167749,   # Lemon peel, raw
    "coriandolo": 169997,         # Coriander (cilantro) leaves, raw
    "zucchine": 168565,           # Squash, zucchini, baby, raw
    "cioccolato bianco": 167571,  # Candies, white chocolate
    "farina di mandorle": 2261420, # Flour, almond
    # ANCORA DA RI-VERIFICARE (rate limit DEMO_KEY il 15/10): pera, tuorlo, salsa di soia.
    # RIMOSSI 14/10 (fdc_id curato sbagliato, verificato live su USDA): ananas->Plums,
    # pera->Persimmons, parmigiano->Feta, tuorlo->Egg omelet, gambero->Cod, salsa di soia->Mustard.
    # Vanno derivati da /admin/deriva-gusti-search (ricerca live + cancello di confidenza).
}

# esclusioni di sicurezza: mai derivare un raro/DOP/presidio da un match generico
_ESCLUDI = ("dop", "igp", "presidio", "bufala", "san marzano", "podolic", "castelpoto",
            "menaica", "maracuoccio", "pertosa", "bagnoles", "conciato", "nocellara")


def _usda_get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Matter/1.0"})
            r = urllib.request.urlopen(req, timeout=30)
            return json.loads(r.read().decode())
        except Exception:
            if i < retries - 1:
                time.sleep(2 * (i + 1))
            else:
                raise


def _nutrienti(detail):
    """Estrae {nome_nutriente: valore} dal dettaglio USDA /food/<fdc_id>."""
    out = {}
    for n in detail.get("foodNutrients", []):
        nome = (n.get("nutrient", {}) or {}).get("name")
        amount = n.get("amount")
        if nome and amount is not None:
            out[nome] = float(amount)
    return out


# Pannello nutrizionale standard (etichetta). Nome USDA -> (chiave, unità).
# L'energia si prende SOLO in kcal (unitName KCAL), mai convertita dai kJ.
_PANNELLO = [
    ("proteine",      ["Protein"],                              "g/100g"),
    ("carboidrati",   ["Carbohydrate, by difference"],          "g/100g"),
    ("fibre",         ["Fiber, total dietary"],                 "g/100g"),
    ("grassi",        ["Total lipid (fat)"],                    "g/100g"),
    ("grassi_saturi", ["Fatty acids, total saturated"],         "g/100g"),
    ("zuccheri",      ["Sugars, total including NLEA", "Total Sugars"], "g/100g"),
    ("sodio",         ["Sodium, Na"],                           "mg/100g"),
]


def _pannello_nutrienti(detail):
    """Funzione PURA: dal dettaglio USDA estrae il pannello nutrizionale standard
    (energia/proteine/carboidrati/fibre/grassi/saturi/zuccheri/sodio). Include SOLO
    i campi realmente presenti con un valore: niente zero inventato, niente conversioni.
    Energia presa solo se c'è in kcal."""
    fn = detail.get("foodNutrients", []) or []
    # indice nome->valore per i campi semplici (ultimo vince, come il resto della pipeline)
    per_nome = {}
    energia_kcal = None
    for n in fn:
        nutr = n.get("nutrient", {}) or {}
        nome = nutr.get("name")
        amount = n.get("amount")
        if not nome or amount is None:
            continue
        if nome == "Energy" and (nutr.get("unitName") or "").upper() == "KCAL":
            energia_kcal = float(amount)
        per_nome[nome] = float(amount)
    out = {}
    if energia_kcal is not None:
        out["energia_kcal"] = {"valore": round(energia_kcal, 1), "unita": "kcal/100g"}
    for chiave, nomi, unita in _PANNELLO:
        for nm in nomi:
            if nm in per_nome:
                out[chiave] = {"valore": round(per_nome[nm], 2), "unita": unita}
                break
    return out


def _deriva(nut):
    """Da nutrienti USDA -> (dolce, salato, grasso) + grezzi + via dolce."""
    # dolce: se c'e' la scomposizione degli zuccheri, equivalente-dolce pesato; altrimenti totali
    zucch_tot = nut.get("Sugars, total including NLEA", nut.get("Total Sugars", 0.0)) or 0.0
    bd = {
        "fruttosio": nut.get("Fructose", 0.0) or 0.0,
        "glucosio": nut.get("Glucose", 0.0) or 0.0,
        "saccarosio": nut.get("Sucrose", 0.0) or 0.0,
        "maltosio": nut.get("Maltose", 0.0) or 0.0,
        "lattosio": nut.get("Lactose", 0.0) or 0.0,
    }
    if sum(bd.values()) > 0:
        eq = sum(g * _SW[k] for k, g in bd.items())
        via = "zuccheri_pesati"
        grezzo_dolce = round(eq, 1)
    else:
        eq = zucch_tot
        via = "zuccheri_totali"
        grezzo_dolce = round(zucch_tot, 1)
    sodio = nut.get("Sodium, Na", 0.0) or 0.0
    grassi = nut.get("Total lipid (fat)", 0.0) or 0.0
    return {
        "dolce": {"val": _interp(eq, _DOLCE), "grezzo": grezzo_dolce, "via": via},
        "salato": {"val": _interp(sodio, _SALATO), "grezzo": round(sodio, 1)},
        "grasso": {"val": _interp(grassi, _GRASSO), "grezzo": round(grassi, 1)},
    }


@bp_gusti.route("/admin/deriva-gusti-usda")
def deriva_gusti_usda():
    """DRY-RUN di default (?s=SECRET). Con &esegui=1 scrive (fill-only, backup+transazione).
    &limite=N per limitare gli ingredienti (default: tutti i match)."""
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
        limite = int(request.args.get("limite", "0"))
    except Exception:
        limite = 0

    try:
        offset = int(request.args.get("offset", "0"))
    except Exception:
        offset = 0
    if offset < 0:
        offset = 0
    coppie = list(_MATCH.items())
    if offset:
        coppie = coppie[offset:]
    if limite > 0:
        coppie = coppie[:limite]

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()

        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_gusti_derivati
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        campione, scritti, saltati_nomatch, saltati_protetti, saltati_usda, cache_usda = [], 0, 0, 0, 0, {}

        for nome_it, fdc_id in coppie:
            # 1) trova il nodo italiano (match esatto sul nome, minuscolo)
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (nome_it,))
            row = cur.fetchone()
            if not row:
                saltati_nomatch += 1
                continue
            nid, nome_nodo, data = row
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})

            # esclusione rari/DOP (a livello di codice)
            testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                saltati_protetti += 1
                continue

            # 2) USDA (con cache per fdc_id). Un intoppo su USDA (es. 429 rate-limit) deve
            #    far SALTARE solo questo ingrediente, non annullare in rollback tutti gli
            #    altri gia' pronti: niente piu' "tutto o niente" sul batch.
            if fdc_id in cache_usda:
                nut, nome_usda, nutri = cache_usda[fdc_id]
            else:
                try:
                    detail = _usda_get(f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key={urllib.parse.quote(key)}")
                except Exception:
                    saltati_usda += 1
                    continue
                nut = _nutrienti(detail)
                nome_usda = detail.get("description", "")
                nutri = _pannello_nutrienti(detail)  # pannello nutrizionale completo (quel che prima si buttava)
                cache_usda[fdc_id] = (nut, nome_usda, nutri)
                time.sleep(0.3)  # rate limit USDA (1000/h)

            der = _deriva(nut)

            prop = dict(dd.get("proprieta", {}) or {})
            meta = dict(dd.get("proprieta_meta", {}) or {})

            riga = {"nodo": nid, "nome": nome_nodo, "fdc_id": fdc_id, "nome_usda": nome_usda, "assi": {}}
            cambi = {}
            for asse in ("dolce", "salato", "grasso"):
                vecchio = prop.get(asse)
                stato_vecchio = (meta.get(asse, {}) or {}).get("stato")
                # fill-only: scrivi solo se manca o era stimato/non-etichettato; mai su corretto/verificato
                scrivibile = stato_vecchio in (None, "stimato")
                nuovo = der[asse]["val"]
                riga["assi"][asse] = {
                    "vecchio": vecchio, "stato_vecchio": stato_vecchio or "stimato/non-taggato",
                    "nuovo_derivato": nuovo, "grezzo": der[asse]["grezzo"],
                    "scrivibile": scrivibile,
                }
                if scrivibile:
                    cambi[asse] = (nuovo, der[asse])

            # pannello nutrizionale: fill-only, mai sopra un blocco corretto a mano
            nutr_meta_vecchio = dd.get("nutrienti_meta", {}) or {}
            nutr_scrivibile = bool(nutri) and (nutr_meta_vecchio.get("stato") in (None, "derivato", "stimato"))
            riga["nutrienti"] = nutri
            riga["nutrienti_scrivibile"] = nutr_scrivibile

            if len(campione) < 40:
                campione.append(riga)

            # 3) scrittura (solo con esegui=1)
            if esegui and (cambi or nutr_scrivibile):
                cur.execute("INSERT INTO _backup_gusti_derivati (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                for asse, (nuovo, info) in cambi.items():
                    prop[asse] = nuovo
                    m = {"stato": "derivato", "fonte": f"USDA FDC {fdc_id}",
                         "formula": FORMULA_VER, "grezzo": info["grezzo"]}
                    if asse == "dolce":
                        m["via"] = info.get("via")
                    meta[asse] = m
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta
                if nutr_scrivibile:
                    dd["nutrienti"] = nutri
                    dd["nutrienti_meta"] = {"stato": "derivato", "fonte": f"USDA FDC {fdc_id}",
                                            "formula": FORMULA_VER}
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "formula": FORMULA_VER,
            "match_tentati": len(coppie),
            "offset": offset,
            "totale_match_curati": len(_MATCH),
            "nodi_non_trovati": saltati_nomatch,
            "saltati_protetti_rari": saltati_protetti,
            "saltati_usda": saltati_usda,
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato modificato. Aggiungi &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_gusti_derivati; "
                     "solo assi dolce/salato/grasso, mai sovrascritto corretto/verificato."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
