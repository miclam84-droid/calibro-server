# knowledge_architecture.py
# LA KNOWLEDGE ARCHITECTURE di Matter: la tassonomia che regge il grafo gastronomico.
# Senza questa, aggiungere migliaia di ingredienti = Wikipedia ingestibile (avviso dei revisori).
# Con questa, il grafo cresce per anni senza collassare: ogni ingrediente ha categoria, famiglia
# aromatica, provenienza del dato, sinonimi. È il fondamento del "grafo professionale verificato".

# ── CATEGORIE MERCEOLOGICHE (il primo livello di ordine) ──
# Ogni ingrediente appartiene a UNA categoria merceologica. Serve per il filtro anti-rumore
# (un abbinamento chimico si mostra solo se le categorie sono gastronomicamente compatibili).
CATEGORIE_MERCEOLOGICHE = {
    "erbe_aromatiche": ["basilico", "prezzemolo", "menta", "timo", "rosmarino", "salvia", "origano", "coriandolo", "aneto", "erba cipollina", "maggiorana", "dragoncello"],
    "spezie": ["pepe", "cannella", "chiodi di garofano", "noce moscata", "cardamomo", "zenzero", "curcuma", "cumino", "coriandolo seme", "paprika", "peperoncino", "zafferano", "vaniglia", "anice stellato"],
    "agrumi": ["limone", "lime", "arancia", "pompelmo", "mandarino", "bergamotto", "cedro", "chinotto", "yuzu"],
    "frutta": ["mela", "pera", "pesca", "albicocca", "ciliegia", "fragola", "lampone", "mirtillo", "fico", "uva", "banana", "ananas", "mango", "frutto della passione"],
    "verdura": ["pomodoro", "zucchina", "melanzana", "peperone", "cipolla", "aglio", "carota", "sedano", "finocchio", "zucca", "patata", "funghi", "carciofo", "asparago"],
    "carne": ["manzo", "vitello", "maiale", "agnello", "pollo", "anatra", "coniglio", "guanciale", "pancetta", "prosciutto"],
    "pesce": ["branzino", "orata", "salmone", "tonno", "baccalà", "acciuga", "gambero", "cozza", "vongola", "polpo", "seppia", "ricci di mare"],
    "latticini": ["mozzarella", "parmigiano", "pecorino", "burro", "panna", "ricotta", "mascarpone", "gorgonzola", "latte"],
    "cereali_farine": ["farina di grano", "farina 00", "semola", "segale", "farro", "orzo", "mais", "riso", "avena", "manitoba"],
    "frutta_secca": ["mandorla", "nocciola", "pistacchio", "noce", "pinolo", "pecan", "anacardo", "arachide"],
    "dolcificanti": ["zucchero", "miele", "sciroppo d'acero", "agave", "melassa"],
    "cioccolato_cacao": ["cioccolato fondente", "cioccolato al latte", "cioccolato bianco", "cacao"],
    "distillati": ["gin", "whisky", "bourbon", "rum", "tequila", "vodka", "cognac", "brandy", "mezcal", "pisco", "cachaça"],
    "liquori_amari": ["campari", "aperol", "vermouth", "chartreuse", "maraschino", "cointreau", "amaro", "fernet", "benedictine"],
    "vino_birra": ["vino rosso", "vino bianco", "prosecco", "champagne", "birra", "sherry"],
    "caffe_te": ["caffè", "tè nero", "tè verde", "matcha", "orzo tostato"],
}

# ── FAMIGLIE AROMATICHE (il secondo livello: perché due ingredienti stanno bene insieme) ──
# Raggruppa gli ingredienti per profilo aromatico dominante. Base per gli abbinamenti "per famiglia".
FAMIGLIE_AROMATICHE = {
    "agrumato": ["limone", "lime", "arancia", "bergamotto", "coriandolo", "citronella"],
    "erbaceo_verde": ["basilico", "prezzemolo", "menta", "timo", "rosmarino", "salvia"],
    "dolce_speziato": ["cannella", "vaniglia", "chiodi di garofano", "noce moscata", "cardamomo"],
    "terroso": ["funghi", "tartufo", "barbabietola", "patata", "cacao"],
    "tostato": ["caffè", "nocciola", "mandorla tostata", "malto", "cacao tostato", "crosta di pane"],
    "floreale": ["rosa", "sambuco", "lavanda", "camomilla", "fiori d'arancio", "violetta"],
    "fruttato_rosso": ["fragola", "lampone", "ciliegia", "ribes", "mora"],
    "affumicato": ["scotch torbato", "mezcal", "paprika affumicata", "tè lapsang"],
    "umami": ["parmigiano", "pomodoro", "funghi", "acciuga", "salsa di soia", "prosciutto"],
    "erbaceo_amaro": ["chartreuse", "fernet", "amaro", "campari", "china"],
}

# ── LIVELLI DI EVIDENZA / PROVENIENZA (il terzo livello: quanto ti fidi del dato) ──
# Ogni abbinamento/parametro ha una provenienza. È la trasparenza scientifica di Matter.
LIVELLI_PROVENIENZA = {
    "A_verificato": "Dato da fonte scientifica primaria (Ahn 2011, IBA, Hamelman, Dave Arnold, FooDB) verificato.",
    "B_ereditato": "Dato ereditato da un ingrediente-archetipo della stessa famiglia (es. peperone crusco eredita da bell_pepper).",
    "C_stima_ai": "Stima generata dall'AI dalla conoscenza professionale, non da fonte primaria. Da verificare.",
    "M_michele": "VERIFICATO DA MICHELE al banco (cocktail bar + bakery reali). Il gold standard Matter.",
}


def categoria_di(ingrediente):
    """Restituisce la categoria merceologica di un ingrediente (o None)."""
    ing = (ingrediente or "").lower().strip()
    for cat, lista in CATEGORIE_MERCEOLOGICHE.items():
        if any(ing == x or ing in x or x in ing for x in lista):
            return cat
    return None


def famiglia_aromatica_di(ingrediente):
    """Restituisce la famiglia aromatica di un ingrediente (o None)."""
    ing = (ingrediente or "").lower().strip()
    for fam, lista in FAMIGLIE_AROMATICHE.items():
        if any(ing == x or ing in x for x in lista):
            return fam
    return None


def categorie_compatibili(cat_a, cat_b):
    """Filtro anti-rumore: due categorie sono gastronomicamente compatibili?
    Impedisce gli abbinamenti chimici assurdi (cioccolato bianco + caviale)."""
    if not cat_a or not cat_b:
        return True  # se non classificato, non filtro (conservativo)
    if cat_a == cat_b:
        return True
    # matrice di compatibilità merceologica (semplificata, estendibile)
    compatibili = {
        "distillati": {"agrumi", "spezie", "frutta", "erbe_aromatiche", "liquori_amari", "dolcificanti", "frutta_secca", "caffe_te", "cioccolato_cacao"},
        "cioccolato_cacao": {"frutta_secca", "frutta", "spezie", "caffe_te", "distillati", "agrumi", "dolcificanti", "latticini"},
        "carne": {"erbe_aromatiche", "spezie", "verdura", "vino_birra", "frutta"},
        "pesce": {"agrumi", "erbe_aromatiche", "verdura", "vino_birra"},
        "cereali_farine": {"dolcificanti", "frutta_secca", "latticini", "spezie", "cioccolato_cacao"},
        "erbe_aromatiche": {"carne", "pesce", "verdura", "distillati", "agrumi", "latticini"},
        "agrumi": {"pesce", "distillati", "frutta", "erbe_aromatiche", "dolcificanti", "cioccolato_cacao"},
    }
    if cat_a in compatibili and cat_b in compatibili[cat_a]:
        return True
    if cat_b in compatibili and cat_a in compatibili[cat_b]:
        return True
    return False
