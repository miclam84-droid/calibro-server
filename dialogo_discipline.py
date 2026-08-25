# dialogo_discipline.py
# I PONTI TRA LE DISCIPLINE — il cuore della "Bibbia": le figure dialogano.
# Vino↔cucina è in carta_vini. Qui: birra↔piatto, dolce↔menu, distillato→creatività barman.

# ── BIRRA ↔ PIATTO ──
BIRRA_CATEGORIE = {
    "Lager / Pils": {
        "profilo": "leggera, secca, luppolo delicato, effervescente",
        "abbina": "fritti, pizza, piatti leggeri, aperitivo",
        "perche": "la carbonazione e l'amaro leggero puliscono il palato dal fritto"},
    "Weizen / Bianche": {
        "profilo": "frumento, banana, chiodo di garofano, morbida",
        "abbina": "insalate, pesce, piatti estivi, wurstel",
        "perche": "le note speziate e la morbidezza legano con piatti delicati e speziati"},
    "IPA / Pale Ale": {
        "profilo": "luppolo intenso, amaro, agrumi, resina",
        "abbina": "carni speziate, formaggi saporiti, cucina piccante, hamburger",
        "perche": "l'amaro deciso taglia il grasso e regge il piccante e le carni saporite"},
    "Ambrata / Amber Ale": {
        "profilo": "maltata, caramello, corpo medio",
        "abbina": "carni alla brace, formaggi stagionati, salumi",
        "perche": "le note maltate e caramellate richiamano la crosta Maillard delle grigliate"},
    "Stout / Porter": {
        "profilo": "scura, caffè, cioccolato, tostata, corposa",
        "abbina": "brasati, dolci al cioccolato, ostriche, carni ricche",
        "perche": "le note tostate legano con la carne brasata e col cioccolato per contrasto"},
    "Trappista / Belgian Strong": {
        "profilo": "complessa, frutta secca, alcol alto, speziata",
        "abbina": "formaggi erborinati, selvaggina, dolci ricchi",
        "perche": "corpo e alcol reggono piatti intensi e formaggi potenti"},
}

def birra_per_piatto(piatto):
    p = (piatto or "").lower()
    REGOLE = [
        (["fritto", "frittura", "pizza", "tempura", "aperitivo"], ["Lager / Pils", "Weizen / Bianche"]),
        (["pesce", "insalata", "verdure", "estivo"], ["Weizen / Bianche", "Lager / Pils"]),
        (["piccante", "speziato", "hamburger", "curry", "messican"], ["IPA / Pale Ale"]),
        (["brace", "griglia", "bbq", "salumi", "stagionato"], ["Ambrata / Amber Ale", "Stout / Porter"]),
        (["brasato", "selvaggina", "stufato", "cioccolato", "ostrica"], ["Stout / Porter", "Trappista / Belgian Strong"]),
        (["erborinato", "gorgonzola", "dolce ricco"], ["Trappista / Belgian Strong"]),
    ]
    cat = []
    for chiavi, categorie in REGOLE:
        if any(k in p for k in chiavi):
            for c in categorie:
                if c not in cat: cat.append(c)
    if not cat:
        cat = ["Lager / Pils", "Ambrata / Amber Ale"]
    return [{"categoria": c, **BIRRA_CATEGORIE[c]} for c in cat[:3]]


# ── DOLCE ↔ MENU: che dessert chiude un certo menu ──
def dolce_per_menu(menu_descrizione):
    """Dato il carattere del menu, suggerisce il tipo di dessert che lo chiude bene."""
    m = (menu_descrizione or "").lower()
    if any(k in m for k in ["pesce", "leggero", "mare", "crudo", "estivo"]):
        return {"tipo": "dessert fresco e agrumato",
                "esempi": ["sorbetto al limone", "semifreddo agli agrumi", "panna cotta ai frutti di bosco"],
                "perche": "dopo un menu di mare, un dolce fresco e acidulo pulisce senza appesantire"}
    if any(k in m for k in ["carne", "brasato", "ricco", "selvaggina", "tartufo"]):
        return {"tipo": "dessert strutturato",
                "esempi": ["tortino al cioccolato", "tiramisù", "bonet"],
                "perche": "un menu ricco regge (e chiede) un dolce importante e goloso"}
    if any(k in m for k in ["speziato", "etnico", "asiatico", "piccante"]):
        return {"tipo": "dessert cremoso e lenitivo",
                "esempi": ["panna cotta", "gelato al cocco", "budino"],
                "perche": "dopo il piccante, un dolce cremoso e freddo lenisce il palato"}
    return {"tipo": "dessert classico versatile",
            "esempi": ["tiramisù", "panna cotta", "crostata di frutta"],
            "perche": "chiusura equilibrata che sta bene dopo un menu vario"}


# ── DISTILLATO → CREATIVITÀ BARMAN: spunti per creare, non solo eseguire ──
DISTILLATO_CREATIVITA = {
    "gin": {"carattere": "botaniche, ginepro, agrumi, erbe",
            "spunti": "esalta le botaniche con erbe fresche (basilico, rosmarino), agrumi, cetriolo; "
                      "bilancia con tonica artigianale o vermouth; prova infusioni di camomilla o tè",
            "abbina_bar": "agrumi, cetriolo, erbe aromatiche, sambuco, pepe rosa"},
    "rum": {"carattere": "canna da zucchero, vaniglia, spezie, caramello (se scuro)",
            "spunti": "gioca sulle note tropicali (ananas, cocco, lime, passion fruit); "
                      "lo scuro lega con spezie, caffè, cioccolato; prova falernum o orgeat",
            "abbina_bar": "lime, ananas, cocco, menta, zenzero, caffè"},
    "whisky": {"carattere": "malto, torba, vaniglia, legno, affumicato",
            "spunti": "esalta col miele e limone (penicillin), o note amare (amaro, vermouth); "
                      "l'affumicato lega con torba, tè lapsang; prova sciroppi speziati",
            "abbina_bar": "miele, limone, zenzero, amaro, ciliegia, arancia"},
    "tequila": {"carattere": "agave, vegetale, terroso, agrumato",
            "spunti": "lega con lime e agave (margarita, paloma); il mezcal aggiunge affumicato; "
                      "prova peperoncino, pompelmo, coriandolo, sedano",
            "abbina_bar": "lime, pompelmo, agave, peperoncino, coriandolo, cetriolo"},
    "vodka": {"carattere": "neutro, pulito, versatile",
            "spunti": "tela bianca: costruisci su un ingrediente protagonista (frutto, caffè, pomodoro); "
                      "ottima per infusioni; prova espresso, frutti di bosco, zenzero",
            "abbina_bar": "caffè, frutti di bosco, zenzero, pomodoro, agrumi"},
    "cognac": {"carattere": "uva, frutta secca, vaniglia, legno",
            "spunti": "classe nei classici (sidecar, sazerac); lega con agrumi, miele, spezie dolci; "
                      "prova con champagne o note di frutta secca",
            "abbina_bar": "arancia, limone, miele, spezie dolci, champagne"},
}

def distillato_creativita(spirito):
    s = (spirito or "").lower().strip()
    for chiave, dati in DISTILLATO_CREATIVITA.items():
        if chiave in s:
            return {"distillato": chiave, **dati}
    return None
