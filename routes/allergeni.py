"""Allergeni — Regolamento UE 1169/2011 (obbligo di legge, sanzioni fino a 24.000€).
Deduzione DETERMINISTICA dagli ingredienti (non AI: su una cosa legale non si può "dimenticare"
un allergene). Vantaggio su One2One: deduciamo dagli ingredienti reali, non da una foto del menu.
I 14 allergeni sono un ENUM FISSO UE, non modificabile."""
from flask import Blueprint, request, jsonify

bp_allergeni = Blueprint("allergeni", __name__)

# I 14 ALLERGENI UE (Allegato II, lista fissa). id, nome IT/EN/ES, icona (chiave frontend).
ALLERGENI_UE = [
    {"id": 1, "it": "Glutine", "en": "Gluten", "es": "Gluten", "icona": "glutine"},
    {"id": 2, "it": "Crostacei", "en": "Crustaceans", "es": "Crustáceos", "icona": "crostacei"},
    {"id": 3, "it": "Uova", "en": "Eggs", "es": "Huevos", "icona": "uova"},
    {"id": 4, "it": "Pesce", "en": "Fish", "es": "Pescado", "icona": "pesce"},
    {"id": 5, "it": "Arachidi", "en": "Peanuts", "es": "Cacahuetes", "icona": "arachidi"},
    {"id": 6, "it": "Soia", "en": "Soy", "es": "Soja", "icona": "soia"},
    {"id": 7, "it": "Latte", "en": "Milk", "es": "Leche", "icona": "latte"},
    {"id": 8, "it": "Frutta a guscio", "en": "Tree nuts", "es": "Frutos de cáscara", "icona": "frutta-guscio"},
    {"id": 9, "it": "Sedano", "en": "Celery", "es": "Apio", "icona": "sedano"},
    {"id": 10, "it": "Senape", "en": "Mustard", "es": "Mostaza", "icona": "senape"},
    {"id": 11, "it": "Sesamo", "en": "Sesame", "es": "Sésamo", "icona": "sesamo"},
    {"id": 12, "it": "Solfiti", "en": "Sulphites", "es": "Sulfitos", "icona": "solfiti"},
    {"id": 13, "it": "Lupini", "en": "Lupin", "es": "Altramuces", "icona": "lupini"},
    {"id": 14, "it": "Molluschi", "en": "Molluscs", "es": "Moluscos", "icona": "molluschi"},
]

# Mappa deterministica: parola chiave nell'ingrediente → id allergene.
# Costruita con cura sulle insidie note (pinoli NON sono frutta a guscio; il vino ha solfiti).
_MAPPA = {
    # 1 glutine (cereali)
    1: ("farina", "grano", "frumento", "pane", "pasta", "spaghetti", "penne", "orzo", "segale",
        "avena", "farro", "kamut", "semola", "pangrattato", "cous cous", "couscous", "bulgur",
        "seitan", "birra", "malto", "biscott", "pizza", "focaccia", "gnocc", "lasagn", "tagliatell",
        "brioche", "cracker", "grissini", "pandoro", "panettone", "besciamella", "roux", "crostini"),
    # 2 crostacei
    2: ("gamber", "scampi", "aragosta", "astice", "granchio", "mazzancoll", "canocchi", "crostace"),
    # 3 uova
    3: ("uovo", "uova", "tuorlo", "albume", "maionese", "frittata", "zabaione", "meringa", "pasta all'uovo",
        "carbonara", "tiramis", "crema pasticcera", "pan di spagna", "savoiardo"),
    # 4 pesce
    4: ("pesce", "acciug", "alici", "salmone", "tonno", "branzino", "orata", "spigola", "merluzzo",
        "baccal", "sgombro", "sardine", "colatura", "bottarga", "nasello", "cernia", "rombo", "sogliola"),
    # 5 arachidi
    5: ("arachid", "burro di arachidi", "peanut"),
    # 6 soia
    6: ("soia", "tofu", "edamame", "tempeh", "salsa di soia", "miso"),
    # 7 latte
    7: ("latte", "burro", "panna", "formagg", "parmigian", "pecorino", "mozzarella", "ricotta",
        "mascarpone", "gorgonzola", "grana", "stracchino", "yogurt", "caciocavallo", "provolone",
        "scamorza", "fontina", "taleggio", "caprino", "burrata", "besciamella", "gelato", "crema di latte"),
    # 8 frutta a guscio (NON i pinoli)
    8: ("mandorl", "nocciol", "noci", "noce", "anacard", "pistacch", "pecan", "macadamia", "castagn",
        "marroni", "pralin", "gianduia", "frutta secca"),
    # 9 sedano
    9: ("sedano", "sedano rapa"),
    # 10 senape
    10: ("senape", "mostarda"),
    # 11 sesamo
    11: ("sesamo", "tahin", "gomasio"),
    # 12 solfiti (VINO/spumanti/aperitivi quasi sempre, frutta secca, aceto)
    12: ("vino", "prosecco", "spumante", "champagne", "franciacorta", "lambrusco", "moscato",
         "aperol", "campari", "bitter", "vermouth", "vermut", "martini", "sherry", "porto", "marsala",
         "aceto balsamico", "aceto di vino", "solfiti", "frutta essiccata", "albicocche secche",
         "uvetta", "prugne secche", "fichi secchi"),
    # 13 lupini
    13: ("lupini", "farina di lupino"),
    # 14 molluschi
    14: ("cozze", "vongole", "ostriche", "calamar", "seppie", "polpo", "moscardini", "lumache",
         "totani", "cannolicchi", "tellin", "mollusch"),
}


def deduci_allergeni(ingredienti):
    """Dato un elenco di ingredienti (stringhe o dict con 'nome'), deduce gli allergeni UE.
    Ritorna (allergeni_ids, warning). Deterministica e conservativa (meglio segnalare in più)."""
    trovati = set()
    testo = ""
    for ing in (ingredienti or []):
        nome = ing.get("nome", "") if isinstance(ing, dict) else str(ing)
        testo += " " + nome.lower()
    for aid, chiavi in _MAPPA.items():
        if any(k in testo for k in chiavi):
            trovati.add(aid)
    warning = None
    if 12 in trovati and any(k in testo for k in ("vino", "prosecco", "spumante", "champagne", "aperol", "campari", "vermouth", "martini", "bitter")):
        warning = "Contiene solfiti (allergene #12), tipico di vino, spumanti e aperitivi."
    return sorted(trovati), warning


@bp_allergeni.route("/v1/allergeni/lista", methods=["GET"])
def lista_allergeni():
    """I 14 allergeni UE con nome nella lingua richiesta e icona. ?lang=it|en|es"""
    lang = (request.args.get("lang") or "it").strip().lower()
    if lang not in ("it", "en", "es"):
        lang = "it"
    return jsonify({"allergeni": [{"id": a["id"], "nome": a[lang], "icona": a["icona"]} for a in ALLERGENI_UE],
                    "fonte": "Regolamento UE 1169/2011 - Allegato II"})


@bp_allergeni.route("/v1/allergeni/deduci", methods=["POST"])
def deduci():
    """Deduce gli allergeni da una lista di ingredienti. Body: {ingredienti:[...], lang?}
    Il vantaggio competitivo: deduzione dagli INGREDIENTI reali, non da una foto del menu."""
    body = request.json or {}
    ingredienti = body.get("ingredienti", [])
    lang = (body.get("lang") or "it").strip().lower()
    if lang not in ("it", "en", "es"):
        lang = "it"
    if not ingredienti:
        return jsonify({"errore": "ingredienti mancanti"}), 400
    ids, warning = deduci_allergeni(ingredienti)
    _map = {a["id"]: a for a in ALLERGENI_UE}
    dettaglio = [{"id": i, "nome": _map[i][lang], "icona": _map[i]["icona"]} for i in ids if i in _map]
    return jsonify({
        "allergeni": ids,
        "dettaglio": dettaglio,
        "warning": warning,
        "disclaimer": "Deduzione automatica dagli ingredienti. Il ristoratore deve verificare e "
                      "confermare: la responsabilità legale della dichiarazione allergeni è sua.",
    })


@bp_allergeni.route("/v1/ricetta/<rid>/allergeni", methods=["GET"])
def allergeni_ricetta(rid):
    """Allergeni dedotti dagli ingredienti di una ricetta. ?lang="""
    from db import carica_grafo
    import json as _j
    lang = (request.args.get("lang") or "it").strip().lower()
    db = carica_grafo()
    try:
        row = db.execute("SELECT ingredienti FROM ricette WHERE id=?", (rid,)).fetchone()
        if not row:
            return jsonify({"errore": "ricetta non trovata"}), 404
        ing_raw = row["ingredienti"] if hasattr(row, "keys") else row[0]
        ings = ing_raw if isinstance(ing_raw, list) else (_j.loads(ing_raw) if ing_raw else [])
        ids, warning = deduci_allergeni(ings)
        _map = {a["id"]: a for a in ALLERGENI_UE}
        if lang not in ("it", "en", "es"): lang = "it"
        dettaglio = [{"id": i, "nome": _map[i][lang], "icona": _map[i]["icona"]} for i in ids if i in _map]
        return jsonify({"ricetta_id": rid, "allergeni": ids, "dettaglio": dettaglio, "warning": warning})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]}), 200
