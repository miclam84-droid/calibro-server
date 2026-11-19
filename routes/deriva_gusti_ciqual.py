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
    # ONDATA 3 — frutta/ortaggi curati a mano (alim_code verificato sul nome_eng del CSV
    # CIQUAL; molti portano l'ACIDO, l'asse che USDA non copre).
    "melograno": 13018, "ribes": 13019, "ribes nero": 13007, "mora": 13029,
    "cachi": 13066, "mandarino": 13024, "clementina": 13024, "mela cotogna": 13010,
    "mirtillo rosso": 13113, "uva spina": 13020, "rabarbaro": 13047, "sambuco": 13126,
    "nespola": 13564, "kumquat": 13549, "guava": 13083, "papaya": 13035,
    "maracuja": 13016, "tamarindo": 13080,
    "finocchio": 20028, "carciofo": 20052, "asparago": 20279, "cavolo": 20069,
    "cavoletti di bruxelles": 20058, "bietola": 20004, "rapa": 20064, "barbabietola": 20091,
    "radicchio": 20026, "rucola": 20217, "ravanello": 20045, "lattuga": 20031,
    "fava": 20517, "piselli": 20072, "castagna": 15024, "patata dolce": 4101,
    "melanzana": 20053, "scalogno": 20097, "indivia": 20012, "zucchina": 20020,
    "sedano rapa": 20055, "pastinaca": 20181, "crescione": 20022, "topinambur": 20196,
    "scarola": 20090, "cardo": 20054, "cavolo nero": 20346,
    # ONDATA 4 — pesce/carne/formaggi/cereali/legumi (alim_code verificato sul nome_eng
    # CSV; pesce e carne hanno acido 0 — giusto — ma portano dolce/salato/grasso reali).
    "tacchino": 36311, "coniglio": 34001, "vitello": 6513, "agnello": 21502,
    "merluzzo": 26043, "sogliola": 26135, "sgombro": 26051, "acciuga": 26079,
    "sardina": 26065, "gambero": 10021, "cozza": 10014, "vongola": 10017,
    "ostrica": 10011, "polpo": 10018, "seppia": 10016, "calamaro": 10001,
    "aragosta": 10010, "granchio": 10039, "capesante": 10045,
    "emmental": 12115, "gruviera": 12114, "provola": 12716, "noce pecan": 15026,
    "orzo": 9320, "quinoa": 9340, "miglio": 9330, "bulgur": 9690,
    "fagioli": 20503, "lupini": 20534,
    # coda F&B (9 nov): stragglers rilevanti per bar/forno, codici CIQUAL raw/plain verificati a mano
    "pesca noce": 13399, "frutto della passione": 13016, "kombucha": 18025, "sidro": 5021,
    # ONDATA 5 (11 nov): comuni non ancora mappati, codice CIQUAL raw/plain verificato sul nome_eng.
    # Priorita' agli ingredienti che portano l'ACIDO (acidi_organici in CIQUAL). Scartati per
    # match sporco (solo forme cotte/piatti compositi): soia, senape, crauti, fagiolini, latticello.
    "avocado": 13004,          # Avocado, flesh without skin, pitted, raw (acidi 1.02)
    "yogurt": 19600,           # Yoghurt or fermented milk, plain (average) (acidi 0.95)
    "cicoria": 20026,          # Chicory, raw
    "nettarina": 13399,        # Nectarine, flesh and skin, pitted, raw (average)
    "susina": 13100,           # Plum, flesh and skin, pitted, raw (acidi 1.27)
    "funghi": 20010,           # Mushroom, all types, raw
    "cavolo cappuccio": 20116, # White cabbage, raw (acidi 0.18)
    "tartufo": 20106,          # Black truffle, raw
    "capperi": 11040,          # Capers, pickled in vinegar
    "olive verdi": 13033,      # Olive, green, in brine (acidi 0.31)
    "olive nere": 13032,       # Olive, black, in brine
    # ONDATA 6 (11 nov): dal roster reale (composti_matter.json), codici CIQUAL raw/plain/dried
    # verificati sul nome_eng. Scartati senza match pulito: aceto di vino/riso, bergamotto,
    # cedro, farina di mais/ceci, cime di rapa, anice, concentrato di pomodoro, branzino d'allevamento.
    "aceto": 11018,            # Vinegar (acidi 5.9 — forte)
    "arancia amara": 13432,    # Bitter orange, flesh without skin, raw
    "amarena": 13110,          # Morello cherry, raw
    "acerola": 13055,          # Acerola, flesh and skin, pitted, raw
    "feijoa": 13061,           # Feijoa, flesh without skin, raw
    "fichi secchi": 13013,     # Fig, dried (acidi 0.8)
    "branzino": 26072,         # European bass, raw
    "camembert": 12006,        # Camembert cheese (acidi 0.98)
    "comté": 12110,            # Comté cheese
    "farina di castagne": 9570,# Chestnut flour
    "farina di segale": 9530,  # Rye flour, type 170
    "aneto": 11093,            # Dill, fresh
    "dragoncello": 11092,      # Tarragon, fresh
    "erba cipollina": 11003,   # Chive, fresh
    "cardamomo": 11075,        # Cardamom, powder
    "cumino": 11042,           # Cumin, seed
    "carvi": 11064,            # Caraway, seed
    "chiodi di garofano": 11052, # Cloves
    "fieno greco": 11077,      # Fenugreek, seed
    # ONDATA 7 (11 nov): dal roster, codici CIQUAL raw/plain/no-salt verificati sul nome_eng.
    # NON mappati di proposito (meglio il banco di Michele o CIQUAL non li ha puliti):
    # specialita' DOP/varieta' (pomodori San Marzano/piennolo/datterino, prosciutti DOP,
    # olive taggiasche), tagli di manzo specifici (fiorentina, picanha, ossobuco),
    # botanici/agrumi esotici (bergamotto, yuzu, cedro, chinotto) assenti da CIQUAL.
    "cognac": 1023,            # Brandy, Armagnac or Cognac type
    "whisky": 1005,            # Whisky
    "porcino": 20160,          # Cep or boletus mushroom, raw
    "finferli": 20103,         # Chanterelle or girolle mushroom, raw
    "cardoncelli": 20114,      # Oyster mushroom, raw
    "provolone": 12716,        # Provolone cheese
    "farina di grano duro": 9610, # Durum wheat semolina, raw
    "semola rimacinata": 9610, # Durum wheat semolina, raw (rimacinata)
    "sorgo": 9360,             # Sorghum, wholegrain, raw
    "germe di grano": 9660,    # Wheat germ
    "pistacchio": 15044,       # Pistachio nut, grilled, no added salt
    "anacardo": 15054,         # Cashew nut, grilled, no added salt
    "noci": 15005,             # Walnut, kernel, dried
    # --- NUCLEO: cibi veri usati nei protocolli, codici CIQUAL verificati a mano
    #     dal CSV (non match fuzzy). Chiudono parte dei 120 "da misurare". 2026-11-16.
    "riso arborio": 9100, "riso carnaroli": 9100, "riso per sushi": 9100,  # Rice, white, raw
    "riso basmati": 9119,                 # Rice, basmati, raw
    "farina 0": 9436,                     # Wheat flour, type 55 (for bread)
    "saccarosio": 31016, "destrosio": 31016,   # Sugar, white (dolce ~ puro)
    "cacao amaro in polvere": 18100,      # Cocoa powder, no added sugars
    "cioccolato amaro": 31005,            # Dark chocolate, 50% cocoa
    "miele millefiori": 31008,            # Honey
    "arachide": 15001,                    # Peanut, no added salt
    "uvetta sultanina": 13046,            # Raisin
    "zenzero fresco": 11074,              # Ginger, raw
    "gelatina in fogli": 11007,           # Gelatin, dried
    "amido di mais": 9510,                # Maize/corn starch
    "fecola di patate": 4090,             # Potato starch
    "latte di cocco": 18041,              # Coconut milk
    "semi di lino": 15034,                # Flaxseed, seed
    "succo di lime fresco": 2030,         # Lime juice, fresh
    "succo di limone fresco": 2007,       # Lemon juice, homemade
    "pangrattato": 7500,                  # Breadcrumbs
    "tuorlo": 22002,                      # Egg yolk, raw
    "concentrato di pomodoro": 20068,     # Tomato paste, concentrated
    "cardamomo verde": 11075,             # Cardamom, powder
    "coriandolo fresco": 11094,           # Coriander, fresh
    "cipollotto": 11003,                  # Chive or spring onion, fresh
    "olive taggiasche": 13131,            # Olive, black, in oil
    "pecorino romano": 12122,             # Pecorino cheese, ewe's milk
    "ricotta di pecora": 19585,           # Ricotta (cow) ~ approssimazione di classe
    "prosciutto": 28812,                  # Dry-cured ham
    "orata": 26080,                       # Gilthead seabream, wild, raw
    "fave secche": 20518,                 # Broad bean, dried
    "fagioli borlotti": 20501,            # Haricot bean, dried (~ borlotti)
    "aceto di vino bianco": 11018, "aceto di mele": 11018, "aceto di riso": 11018,  # Vinegar
    # --- NUCLEO lotto 2: altri cibi misurabili (codici CIQUAL verificati). 2026-11-16.
    "latte magro in polvere": 19054, "latte in polvere scremato": 19054,  # Milk powder, skimmed
    "bacca di vaniglia": 11057,            # Vanilla, pod
    "confettura": 31024,                   # Jam, strawberry (rappresentativo generico)
    "arancia candita": 31021,              # Candied orange peel
    "cedro candito": 31027,                # Candied fruit
    "panna fresca 35%": 19411,             # Cream (= mappatura 'panna' esistente)
    # ONDATA 3 — cibi veri scoperti (copertura-gusti, 19/11). Codici CIQUAL
    # verificati a mano su data/ciqual2025_norm.csv (record "raw" dove esiste).
    "acciughe": 26079,            # Anchovy, raw
    "astice": 10010,              # Lobster, raw
    "aragosta": 10015,            # Spiny lobster, raw
    "asparagi verdi": 20279,      # Asparagus, green, raw
    "asparagi crudi": 20279,      # Asparagus, green, raw
    "asparagi bianchi": 20282,    # Asparagus, white or purple, peeled, raw
    "merluzzo": 26043,            # Cod, raw
    "baccalà": 26024,             # Cod, salted (merluzzo salato: salato alto corretto)
    "amarena": 13110,             # Morello cherry, raw
    "melograno": 13018,           # Pomegranate, flesh, raw
    "fico": 13012,                # Fig, raw
    # ONDATA 4 — fix errori trovati nell'audit profili (19/11). Item salati/curati
    # con salato sbagliato o mancante, e aceto senza acido. Codici verificati su CSV.
    "acciuga salata": 26177,      # Anchovy, salted, in oil (sodio 3600 -> salato alto)
    "acciughe sott'olio": 26177,  # idem (prodotto salato)
    "bresaola": 28860,            # Viande des Grisons / dried beef (sodio 1530)
    "speck": 28801,               # Cured ham, smoked (sodio 2050)
    "aceto di vino": 11018,       # Vinegar (acidi 5.9 -> acido alto)
    # ONDATA 5 — altri fuzzy-USDA sbagliati trovati nell'audit allargato (131 regole).
    # Prodotti compositi con record CIQUAL puro verificato; recupero via supera_usda.
    "cioccolato al latte": 31004, # Milk chocolate, bar (zuc 56 -> dolce; gra 31)
    "maionese": 11054,            # Mayonnaise 70% fat (gra 74.5 -> grasso alto)
    "salmone affumicato": 26037,  # Salmon, smoked (sodio 1220 -> salato alto)
    "senape": 11013,              # Mustard (sodio 2300 -> salato)
    # NON aggiunti di proposito: "olio di girasole" (CIQUAL non ha l'olio di semi puro)
    # e "lardo" (ambiguo: lardo stagionato salato vs strutto reso) -> niente aggancio incerto.
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
    # &supera_usda=1: la fonte CIQUAL verificata (ID vero) può RECLAMARE un asse oggi
    # derivato da un "match ricerca" USDA (match fuzzy, a volte sul cibo sbagliato —
    # es. cotogna con grasso/salato da un record non-cotogna). Mai tocca corretto/
    # verificato al banco, né derivati USDA non-fuzzy. Senza il flag: comportamento storico.
    supera_usda = request.args.get("supera_usda") == "1"
    # &correggi_acido=1: sostituisce l'asse ACIDO quando e' un derivato vecchio che diverge
    # (>=0.5) dalla derivazione nuova agganciata all'acidita' grezza CIQUAL. Backup + tag
    # 'corretto'. Mai tocca corretto/verificato/misurato, ne' assi diverse da acido.
    correggi_acido = request.args.get("correggi_acido") == "1"
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
        reclamati_da_match_ricerca = 0  # assi strappati a un match fuzzy USDA (solo con supera_usda=1)
        corretti_acido = 0  # acido-derivato gonfiato sostituito dal nuovo (solo con correggi_acido=1)

        for nome_it, code in coppie:
            # 1) nodo italiano (match esatto sul nome, minuscolo)
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC, id LIMIT 1""", (nome_it,))
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
                meta_asse = meta.get(asse, {}) or {}
                stato_vecchio = meta_asse.get("stato")
                fonte_vecchia = str(meta_asse.get("fonte", ""))
                # un asse derivato da match fuzzy USDA è reclamabile da CIQUAL (ID verificato)
                e_match_fuzzy = "match ricerca" in fonte_vecchia.lower()
                # fill-only: mai su corretto/verificato. Un derivato USDA resta, SALVO
                # (con supera_usda=1) quando è un match fuzzy: lì vince l'ID CIQUAL.
                scrivibile = stato_vecchio in (None, "stimato")
                reclamo = (supera_usda and stato_vecchio == "derivato" and e_match_fuzzy)
                if reclamo:
                    scrivibile = True
                # correzione acido: ciqual-v1 e' agganciata all'acidita' grezza CIQUAL.
                # Dove l'acido e' un derivato vecchio gonfiato (scarto >=0.5 dal nuovo), con
                # correggi_acido=1 lo sostituiamo. Mai su corretto/verificato/misurato.
                e_correzione = False
                if (correggi_acido and asse == "acido" and stato_vecchio == "derivato"
                        and der[asse].get("grezzo") is not None):
                    try:
                        scarto = abs(float(der[asse]["val"]) - float(vecchio)) if vecchio is not None else 999.0
                    except (TypeError, ValueError):
                        scarto = 999.0
                    if scarto >= 0.5:
                        scrivibile = True
                        e_correzione = True
                riga["assi"][asse] = {
                    "vecchio": vecchio, "stato_vecchio": stato_vecchio or "stimato/non-taggato",
                    "fonte_vecchia": fonte_vecchia or None,
                    "nuovo_derivato": der[asse]["val"], "grezzo": der[asse]["grezzo"],
                    "scrivibile": scrivibile, "reclamato_da_match_ricerca": reclamo,
                    "correzione": e_correzione,
                }
                if scrivibile:
                    cambi[asse] = (der[asse]["val"], der[asse], e_correzione)
                    if reclamo:
                        reclamati_da_match_ricerca += 1
                    if e_correzione:
                        corretti_acido += 1

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
                for asse, (nuovo, info, e_corr) in cambi.items():
                    prop[asse] = nuovo
                    if e_corr:
                        m = {"stato": "corretto",
                             "fonte": f"{FONTE} #{code} (acidita' titolabile)",
                             "formula": FORMULA_VER, "grezzo": info["grezzo"],
                             "nota": "acido corretto: agganciato all'acidita' grezza CIQUAL "
                                     "(sostituisce un derivato precedente gonfiato)"}
                    else:
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
            "supera_usda": supera_usda,
            "correggi_acido": correggi_acido,
            "reclamati_da_match_ricerca": reclamati_da_match_ricerca,
            "corretti_acido": corretti_acido,
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato modificato. Aggiungi &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_gusti_derivati; "
                     "assi dolce/salato/grasso/acido + pannello nutrienti (grassi/zuccheri/sodio, "
                     "gli unici campi presenti nella tabella CIQUAL), mai sovrascritto corretto/verificato. "
                     "Con correggi_acido=1 l'acido-derivato gonfiato viene sostituito e taggato 'corretto'. "
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


@bp_gusti_ciqual.route("/admin/audit-nomi-ambigui-ciqual")
def audit_nomi_ambigui_ciqual():
    """READ-ONLY. Per ogni nome nella mappa CIQUAL _MATCH conta i nodi
    Ingrediente/Prodotto che condividono quel nome esatto. I nomi con >1 nodo
    sono ambigui: la mappa 'nome -> codice CIQUAL' applica lo stesso codice a
    specie diverse (es. 4 nodi 'mela cotogna' = cotogna vera + cinese + nana +
    buccia). Mostra gli id e se il meta cita davvero quel codice, così si vede
    dove un codice è stato applicato alla specie sbagliata. Nessuna scrittura."""
    import psycopg2
    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        ambigui, nodi_totali_ambigui = [], 0
        for nome_it, code in _MATCH.items():
            cur.execute("""SELECT id, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC, id""", (nome_it,))
            rows = cur.fetchall()
            if len(rows) <= 1:
                continue
            nodi = []
            for nid, data in rows:
                dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
                meta = dd.get("proprieta_meta", {}) or {}
                # fonti CIQUAL citate adesso sugli assi (per vedere il codice applicato)
                fonti = sorted({str((meta.get(a, {}) or {}).get("fonte", ""))
                                for a in ("dolce", "salato", "grasso", "acido")
                                if (meta.get(a, {}) or {}).get("fonte")})
                nodi.append({"id": nid, "en": ((dd.get("names", {}) or {}).get("en")
                                               or dd.get("nome_en") or ""),
                             "fonti_assi": fonti})
            nodi_totali_ambigui += len(rows)
            ambigui.append({"nome": nome_it, "codice_mappa": code,
                            "n_nodi": len(rows), "nodi": nodi})
        cur.close(); conn.close()
        ambigui.sort(key=lambda x: -x["n_nodi"])
        return jsonify({
            "read_only": True,
            "nomi_mappa_totali": len(_MATCH),
            "nomi_ambigui": len(ambigui),
            "nodi_coinvolti": nodi_totali_ambigui,
            "nota": ("Ogni voce è un nome con più nodi: la mappa CIQUAL applica un solo "
                     "codice a tutte le specie omonime. Dove 'fonti_assi' cita quel codice "
                     "su un nodo che NON è la specie del codice, la provenienza è sbagliata."),
            "dettaglio": ambigui,
        })
    except Exception as e:
        try:
            if conn: conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500


@bp_gusti_ciqual.route("/admin/disambigua-nodo")
def disambigua_nodo():
    """Disambigua UN nodo omonimo: rinomina + toglie una fonte-specie prestata.
    DRY-RUN di default. Parametri:
      id      (obbligatorio) id esatto del nodo
      nome    (opz) nuovo nome reale del nodo (es. 'mela cotogna cinese').
      strip   (opz) sottostringa di fonte: ogni asse dolce/salato/grasso/acido la
              cui 'fonte' la contiene torna a stato='stimato' (tolte fonte/grezzo/
              formula) — niente provenienza falsa di un'altra specie. Il VALORE
              numerico resta come stima, senza più spacciare una fonte.
      esegui=1 scrive (transazione + backup in _backup_disambigua).
    Mai cancella il nodo. Reversibile dal backup."""
    import psycopg2
    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400
    nid = request.args.get("id", "").strip()
    if not nid:
        return jsonify({"errore": "manca id"}), 400
    nuovo_nome = request.args.get("nome", "").strip()
    strip = request.args.get("strip", "").strip()
    esegui = request.args.get("esegui") == "1"
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE id=%s", (nid,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({"errore": "nodo non trovato", "id": nid}), 404
        _id, nome_vecchio, data = row
        dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        meta = dict(dd.get("proprieta_meta", {}) or {})

        assi_strippati = []
        if strip:
            for a in ("dolce", "salato", "grasso", "acido"):
                m = meta.get(a) or {}
                if strip.lower() in str(m.get("fonte", "")).lower():
                    assi_strippati.append({"asse": a, "fonte_tolta": m.get("fonte"),
                                           "grezzo_tolto": m.get("grezzo")})
                    meta[a] = {"stato": "stimato"}

        azione = {
            "id": nid,
            "nome_vecchio": nome_vecchio,
            "nome_nuovo": (nuovo_nome or nome_vecchio),
            "rinomina": bool(nuovo_nome and nuovo_nome != nome_vecchio),
            "assi_riportati_a_stima": assi_strippati,
            "strip": strip or None,
        }

        if esegui and (azione["rinomina"] or assi_strippati):
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_disambigua
                           (id TEXT, name_old TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            cur.execute("INSERT INTO _backup_disambigua (id, name_old, data_old) VALUES (%s,%s,%s)",
                        (nid, nome_vecchio, json.dumps(dd, ensure_ascii=False)))
            if assi_strippati:
                dd["proprieta_meta"] = meta
            if azione["rinomina"]:
                names = dict(dd.get("names", {}) or {})
                if names.get("it"):
                    names["it"] = nuovo_nome
                    dd["names"] = names
                cur.execute("UPDATE nodes SET name=%s, data=%s WHERE id=%s",
                            (nuovo_nome, json.dumps(dd, ensure_ascii=False), nid))
            else:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
            conn.commit()
            azione["scritto"] = True
        else:
            azione["scritto"] = False

        cur.close(); conn.close()
        azione["dry_run"] = (not esegui)
        azione["nota"] = ("DRY RUN: aggiungi &esegui=1 per scrivere."
                          if not esegui else
                          "ESEGUITO: backup in _backup_disambigua; nodo mai cancellato.")
        return jsonify(azione)
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500


@bp_gusti_ciqual.route("/admin/copertura-gusti")
def copertura_gusti():
    """READ-ONLY. Mappa della copertura: per ogni asse di gusto conta quanti nodi
    Ingrediente/Prodotto hanno un valore e quanti NO, e restituisce un campione
    (fino a &limite, default 150) di NOMI scoperti per asse. Serve a curare
    l'estensione del match nome->record (CIQUAL/USDA) su nodi veri, non alla cieca:
    e' la lista-bersaglio del 'Livello A' del piano dati. Nessuna scrittura."""
    import psycopg2
    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400
    try:
        limite = int(request.args.get("limite", "150"))
    except ValueError:
        limite = 150
    limite = max(1, min(limite, 1000))
    assi = ["acido", "umami", "amaro", "dolce", "salato", "grasso"]
    # "comune" = ingrediente generico da banco: nome in minuscolo e senza underscore.
    # Esclude DOP/IGP e nomi propri (Title Case: "Agnello d'Alpago", "Aceite de Madrid")
    # e botaniche/oli essenziali (underscore: abies_alba, achillea_micrantha_oil).
    # Questi ultimi NON devono avere un gusto base: gonfiano solo il denominatore.
    COMUNE = "name ~ '^[[:lower:]]' AND position('_' in name) = 0"
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')""")
        totale = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND " + COMUNE)
        totale_comuni = cur.fetchone()[0]
        out = {}
        for asse in assi:
            # ha valore = proprieta ha la chiave asse e non e' null
            cur.execute("""SELECT COUNT(*) FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto')
                             AND (data->'proprieta'->>%s) IS NOT NULL""", (asse,))
            con = cur.fetchone()[0]
            # copertura VERA: solo sugli ingredienti generici
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND "
                        + COMUNE + " AND (data->'proprieta'->>%s) IS NOT NULL", (asse,))
            con_comuni = cur.fetchone()[0]
            cur.execute("SELECT name FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND "
                        + COMUNE + " AND (data->'proprieta'->>%s) IS NULL ORDER BY name LIMIT %s",
                        (asse, limite))
            scoperti_comuni = [r[0] for r in cur.fetchall()]
            out[asse] = {
                "con_valore": con, "senza_valore": totale - con,
                "copertura_pct_grezza": round(100.0 * con / totale, 1) if totale else 0,
                "comuni_con_valore": con_comuni,
                "comuni_senza_valore": totale_comuni - con_comuni,
                "copertura_pct_comuni": round(100.0 * con_comuni / totale_comuni, 1) if totale_comuni else 0,
                "esempi_comuni_scoperti": scoperti_comuni,
            }
        cur.close(); conn.close()
        return jsonify({"ok": True, "totale_nodi": totale, "totale_comuni": totale_comuni,
                        "limite_esempi": limite, "assi": out,
                        "nota": "Sola lettura. 'copertura_pct_comuni' e' la copertura VERA "
                                "(solo ingredienti generici); la grezza e' gonfiata da oli "
                                "essenziali, botaniche e DOP che non hanno gusto base. "
                                "'esempi_comuni_scoperti' = la lista-bersaglio reale da curare."})
    except Exception as e:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500


@bp_gusti_ciqual.route("/admin/nodi-doppioni")
def nodi_doppioni():
    """READ-ONLY. Nodi Ingrediente/Prodotto con lo STESSO nome (case-insensitive)
    presenti piu' volte: sono i doppioni (es. 'cioccolato al latte' su 2 nodi,
    'assenzio' su 5). Per ciascuno: quante copie e gli id. E' la lista per la
    deduplica (l'endpoint /admin/disambigua lavora un nodo alla volta). Nessuna
    scrittura."""
    import psycopg2
    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400
    try:
        limite = int(request.args.get("limite", "200"))
    except ValueError:
        limite = 200
    limite = max(1, min(limite, 2000))
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute("""SELECT LOWER(name) AS ln, COUNT(*) AS n,
                              array_agg(id ORDER BY id) AS ids
                       FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name)
                       HAVING COUNT(*) > 1
                       ORDER BY COUNT(*) DESC, LOWER(name)
                       LIMIT %s""", (limite,))
        righe = cur.fetchall()
        # totali
        cur.execute("""SELECT COALESCE(SUM(c-1),0), COUNT(*) FROM (
                         SELECT COUNT(*) c FROM nodes
                         WHERE type IN ('Ingrediente','Prodotto')
                         GROUP BY LOWER(name) HAVING COUNT(*)>1) t""")
        copie_extra, nomi_doppi = cur.fetchone()
        cur.close(); conn.close()
        doppioni = [{"nome": r[0], "copie": r[1], "ids": r[2]} for r in righe]
        return jsonify({"ok": True,
                        "nomi_con_doppioni": nomi_doppi,
                        "copie_in_eccesso": copie_extra,
                        "mostrati": len(doppioni),
                        "doppioni": doppioni,
                        "nota": "Sola lettura. 'copie_in_eccesso' = quanti nodi "
                                "sparirebbero deduplicando (tenendone uno per nome). "
                                "La fusione vera va fatta a mano/con disambigua, con backup."})
    except Exception as e:
        try:
            if conn: conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
