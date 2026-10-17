# ============================================================
# DERIVA-GUSTI-CIQUAL — pipeline del gusto DERIVATO da composizione (CIQUAL 2025, ANSES)
# Fratello di deriva_gusti.py (USDA). Porta dolce/salato/grasso/ACIDO dei comuni da
# 'stimato' (AI) a 'derivato' (da misura europea). CIQUAL dà anche gli acidi organici,
# quindi aggiunge l'asse ACIDO che USDA non copre — taggato "da acidi organici, non pH".
# DRY-RUN di default; con ?esegui=1 scrive fill-only in transazione con backup.
# Match CURATO a mano (il match automatico su CIQUAL sbaglia ~50%: ciliegia->pomodoro,
# burro->fagiolo, miele->melone). Dati locali: data/ciqual2025_norm.csv (niente rete).
# Fonte obbligatoria da licenza Open Licence ANSES: "Anses. 2025. Ciqual..."
# Oltre agli assi del gusto persiste anche il PANNELLO nutrizionale (dd["nutrienti"]/
# ["nutrienti_meta"], fill-only) con i SOLI campi che la tabella CIQUAL normalizzata
# contiene davvero — vedi _pannello_nutrienti() per quali e perché.
# ============================================================
import os
import csv
import json

from flask import Blueprint, request, jsonify
from routes.deriva_gusti import _interp, _ESCLUDI

bp_gusti_ciqual = Blueprint("deriva_gusti_ciqual", __name__)

FORMULA_VER = "ciqual-v1"
FONTE = "CIQUAL 2025 (ANSES)"

# --- Curve (misura per 100g -> asse 0-10). Le prime tre identiche a USDA (stesse unità);
#     ACIDO: curva su acidi organici g/100g, ancorata alla definizione delle scale
#     (pomodoro~3, yogurt~6, limone~8/9). È un PROXY: gli acidi organici non sono il pH. ---
_DOLCE = [(0, 0), (5, 3), (12, 5), (30, 7), (60, 9), (80, 10)]            # zuccheri g
_SALATO = [(5, 0), (50, 1), (200, 3), (500, 5), (1500, 7), (5000, 9), (15000, 10)]  # sodio mg
_GRASSO = [(0, 0), (3, 2), (10, 4), (20, 6), (35, 8), (60, 10)]            # grasso g
_ACIDO = [(0, 0), (0.15, 1), (0.5, 3), (1.0, 5.5), (2.5, 7), (5.0, 8.5), (8.0, 10)]  # acidi org. g

_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "ciqual2025_norm.csv")
_TBL = None


def _tabella():
    """Carica (una volta) la tabella CIQUAL normalizzata: {alim_code: {misure}}."""
    global _TBL
    if _TBL is not None:
        return _TBL
    _TBL = {}
    try:
        with open(_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    code = int(float(r["alim_code"]))
                except (ValueError, TypeError, KeyError):
                    continue

                def fl(k):
                    v = (r.get(k) or "").strip()
                    if v in ("", "nan", "None"):
                        return None
                    try:
                        return float(v)
                    except ValueError:
                        return None

                _TBL[code] = {
                    "nome": r.get("nome_eng", ""),
                    "zuccheri": fl("zuccheri_g"),
                    "grasso": fl("grasso_g"),
                    "sodio": fl("sodio_mg"),
                    "acidi": fl("acidi_organici_g"),
                }
    except FileNotFoundError:
        _TBL = {}
    return _TBL


# --- Match CURATO ingrediente italiano -> alim_code CIQUAL (forma base cruda, verificata a mano) ---
_MATCH = {
    # agrumi / frutta
    "pomodoro": 20345, "limone": 13009, "succo di limone": 2007, "lime": 13067,
    "arancia": 13034, "mela": 13039, "fragola": 13014, "lampone": 13015,
    "mirtillo": 13028, "pesca": 13043, "albicocca": 13000, "ciliegia": 13008,
    "mango": 13025, "banana": 13005, "uva": 13045,
    # latticini / uova
    "latte": 19010, "panna": 19411, "burro": 16400, "mozzarella": 19590,
    "parmigiano": 12120, "cheddar": 12726, "uovo": 22000,
    # cereali / amidi
    "farina": 9435, "riso": 9100,
    # carni / pesce
    "manzo": 6001, "pollo": 36003, "petto di pollo": 36003, "salmone": 26223,
    "maiale": 28100, "tonno": 26053,
    # ortaggi / aromi
    "aglio": 11000, "cipolla": 20034, "carota": 20009, "cetriolo": 20019,
    "zucchine": 20020, "peperone": 20087, "spinaci": 20059, "patata": 4023,
    "basilico": 11033, "coriandolo": 11026, "champignon": 20056,
    # grassi / dolci / fondi
    "olio di oliva": 17270, "olio d'oliva": 17270, "zucchero": 31016, "miele": 31008,
    "cacao": 18100, "aceto balsamico": 11091,
    # frutta secca / spezie
    "mandorla": 15000, "nocciola": 15004, "noce": 15005,
    "zenzero": 11074, "cannella": 11025, "pepe nero": 11015,
    # ONDATA 2 — erbe/spezie (forma base, verificata a mano sul nome CIQUAL)
    "rosmarino": 11068, "timo": 11070, "salvia": 11069, "menta": 11027,
    "prezzemolo": 11014, "origano": 11035, "alloro": 11053, "noce moscata": 11048,
    "vaniglia": 11057, "curcuma": 11089, "paprika": 11049, "peperoncino": 20151,
    # latticini
    "ricotta": 19585, "mascarpone": 19584, "gorgonzola": 12524, "pecorino": 12122, "feta": 12060,
    # frutta
    "pera": 13037, "kiwi": 13021, "ananas": 13002, "fico": 13012, "dattero": 13011,
    "uvetta": 13046, "pompelmo": 13040, "cocco": 15006, "melone": 13430, "anguria": 13036, "prugna": 13583,
    # frutta secca / semi
    "pinoli": 15025, "sesamo": 15010, "arachidi": 15001, "anacardi": 15054,
    # cereali / farine
    "avena": 9310, "farro": 9001, "segale": 9390, "grano saraceno": 9380, "mais": 9614,
    # ortaggi / legumi
    "zucca": 20044, "sedano": 20023, "porro": 20039, "broccolo": 20057,
    "cavolfiore": 20016, "ceci": 20516, "lenticchie": 20359,
    # dolcificanti
    "sciroppo d'acero": 31034,
}

_ASSI = ("dolce", "salato", "grasso", "acido")


def _deriva(row):
    """Da misure CIQUAL -> fino a 4 assi + grezzo. Solo gli assi con misura presente."""
    out = {}
    if row.get("zuccheri") is not None:
        out["dolce"] = {"val": _interp(row["zuccheri"], _DOLCE), "grezzo": round(row["zuccheri"], 2)}
    if row.get("sodio") is not None:
        out["salato"] = {"val": _interp(row["sodio"], _SALATO), "grezzo": round(row["sodio"], 1)}
    if row.get("grasso") is not None:
        out["grasso"] = {"val": _interp(row["grasso"], _GRASSO), "grezzo": round(row["grasso"], 2)}
    if row.get("acidi") is not None:
        out["acido"] = {"val": _interp(row["acidi"], _ACIDO), "grezzo": round(row["acidi"], 2),
                        "nota": "da acidi organici, non pH"}
    return out


# Pannello nutrizionale standard (etichetta) dai campi CIQUAL realmente presenti.
# ONESTÀ: la tabella CIQUAL normalizzata (data/ciqual2025_norm.csv) espone SOLO le
# colonne nutrizionali zuccheri_g, grasso_g, sodio_mg, sale_g, acidi_organici_g.
# Quindi il pannello può contenere soltanto grassi/zuccheri/sodio: energia (kcal),
# proteine, carboidrati, fibre e grassi saturi NON esistono nella tabella e NON si
# scrivono mai (niente zero inventato, nessuna conversione). Mappatura
# chiave_pannello -> (chiave riga interna = colonna CIQUAL reale, unità).
_PANNELLO = [
    ("grassi",   "grasso",   "g/100g"),    # colonna CIQUAL: grasso_g
    ("zuccheri", "zuccheri", "g/100g"),    # colonna CIQUAL: zuccheri_g
    ("sodio",    "sodio",    "mg/100g"),   # colonna CIQUAL: sodio_mg
]


def _pannello_nutrienti(row):
    """Funzione PURA: da una riga CIQUAL normalizzata estrae il pannello
    nutrizionale standard, includendo SOLO i campi con un valore realmente
    presente (non None). La tabella CIQUAL normalizzata non contiene energia/
    proteine/carboidrati/fibre/grassi saturi: quei campi non vengono mai scritti
    (niente zero inventato). Stessa forma d'uscita del pannello USDA:
    {chiave: {"valore": x, "unita": u}}."""
    out = {}
    for chiave, kriga, unita in _PANNELLO:
        v = (row or {}).get(kriga)
        if v is not None:
            out[chiave] = {"valore": round(float(v), 2), "unita": unita}
    return out


def _nutri_da_scrivere(nutri, nutrienti_vecchio, nutr_meta_vecchio):
    """Decide (PURO) se persistere il pannello CIQUAL `nutri`. Regole:
    - niente da scrivere se il nuovo pannello è vuoto;
    - fill-only: mai sopra un blocco con stato diverso da derivato/stimato/assente;
    - NO-DOWNGRADE: se il nodo ha GIÀ un blocco nutrienti, si scrive solo se il
      nuovo pannello ha PIÙ campi di quello esistente. Così un pannello più ricco
      (es. USDA a 8 campi) non viene mai sostituito da uno più povero (CIQUAL a 3).
    La `fonte` resta UNICA per blocco (nessuna provenienza per-campo)."""
    if not nutri:
        return False
    stato = (nutr_meta_vecchio or {}).get("stato")
    if stato not in (None, "derivato", "stimato"):
        return False
    vecchio = nutrienti_vecchio if isinstance(nutrienti_vecchio, dict) else {}
    if vecchio and len(nutri) <= len(vecchio):
        return False  # no-downgrade: non sostituire un pannello uguale o più ricco
    return True


@bp_gusti_ciqual.route("/admin/deriva-gusti-ciqual")
def deriva_gusti_ciqual():
    """DRY-RUN di default (?s=SECRET). Con &esegui=1 scrive (fill-only, backup+transazione).
    &offset / &limite per lavorare a blocchi. Dati locali CIQUAL: niente rete."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    tbl = _tabella()
    if not tbl:
        return jsonify({"errore": "tabella CIQUAL non trovata (data/ciqual2025_norm.csv)"}), 500

    esegui = request.args.get("esegui") == "1"
    try:
        limite = int(request.args.get("limite", "0"))
    except ValueError:
        limite = 0
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
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

        campione, scritti, saltati_nomatch, saltati_protetti, saltati_dato = [], 0, 0, 0, 0

        for nome_it, code in coppie:
            # 1) nodo italiano (match esatto sul nome, minuscolo)
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (nome_it,))
            row = cur.fetchone()
            if not row:
                saltati_nomatch += 1
                continue
            nid, nome_nodo, data = row
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})

            # esclusione rari/DOP
            testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                saltati_protetti += 1
                continue

            cq = tbl.get(code)
            if not cq:
                saltati_dato += 1
                continue
            der = _deriva(cq)
            if not der:
                saltati_dato += 1
                continue

            prop = dict(dd.get("proprieta", {}) or {})
            meta = dict(dd.get("proprieta_meta", {}) or {})

            riga = {"nodo": nid, "nome": nome_nodo, "fdc_id": code,
                    "nome_usda": cq.get("nome", ""), "assi": {}}
            cambi = {}
            for asse in _ASSI:
                if asse not in der:
                    continue
                vecchio = prop.get(asse)
                stato_vecchio = (meta.get(asse, {}) or {}).get("stato")
                # fill-only: mai su corretto/verificato, mai su un derivato USDA già presente
                scrivibile = stato_vecchio in (None, "stimato")
                riga["assi"][asse] = {
                    "vecchio": vecchio, "stato_vecchio": stato_vecchio or "stimato/non-taggato",
                    "nuovo_derivato": der[asse]["val"], "grezzo": der[asse]["grezzo"],
                    "scrivibile": scrivibile,
                }
                if scrivibile:
                    cambi[asse] = (der[asse]["val"], der[asse])

            # pannello nutrizionale completo (solo campi CIQUAL realmente presenti):
            # fill-only + no-downgrade (mai sostituire un pannello esistente più ricco).
            nutri = _pannello_nutrienti(cq)
            nutr_scrivibile = _nutri_da_scrivere(nutri, dd.get("nutrienti"), dd.get("nutrienti_meta", {}))
            riga["nutrienti"] = nutri
            riga["nutrienti_scrivibile"] = nutr_scrivibile

            if len(campione) < 40:
                campione.append(riga)

            # 2) scrittura (solo con esegui=1)
            if esegui and (cambi or nutr_scrivibile):
                cur.execute("INSERT INTO _backup_gusti_derivati (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                for asse, (nuovo, info) in cambi.items():
                    prop[asse] = nuovo
                    m = {"stato": "derivato", "fonte": f"{FONTE} #{code}",
                         "formula": FORMULA_VER, "grezzo": info["grezzo"]}
                    if asse == "acido":
                        m["nota"] = "da acidi organici, non pH"
                    meta[asse] = m
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta
                if nutr_scrivibile:
                    dd["nutrienti"] = nutri
                    dd["nutrienti_meta"] = {"stato": "derivato", "fonte": f"{FONTE} #{code}",
                                            "formula": FORMULA_VER}
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "fonte": FONTE,
            "formula": FORMULA_VER,
            "match_tentati": len(coppie),
            "offset": offset,
            "totale_match_curati": len(_MATCH),
            "nodi_non_trovati": saltati_nomatch,
            "saltati_protetti_rari": saltati_protetti,
            "saltati_dato": saltati_dato,
            "saltati_usda": 0,  # compat col pannello (CIQUAL è locale, nessun rate-limit)
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato modificato. Aggiungi &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_gusti_derivati; "
                     "assi dolce/salato/grasso/acido + pannello nutrienti (grassi/zuccheri/sodio, "
                     "gli unici campi presenti nella tabella CIQUAL), mai sovrascritto corretto/verificato. "
                     "Fonte: Anses. 2025. Ciqual French food composition table."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
