# mappa_extra9.py
# ULTIMO BLOCCO — supera i 1000 piatti canonici.

ITALIA_9 = {
    "Campania": [
        {"nome": "Pasta e patate senza provola", "chiave": "patate", "firma": ["pasta mista", "patate", "sedano", "pomodoro"]},
        {"nome": "Cozze gratinate", "chiave": "cozze", "firma": ["cozze", "pangrattato", "prezzemolo", "aglio"]},
        {"nome": "Melanzane al cioccolato", "chiave": "melanzane", "firma": ["melanzane", "cioccolato", "canditi"], "disc": "pasticceria"},
    ],
    "Sicilia": [
        {"nome": "Anelletti al forno", "chiave": "pasta", "firma": ["anelletti", "ragù", "melanzane", "caciocavallo"]},
        {"nome": "Sfincia di San Giuseppe", "chiave": "ricotta", "firma": ["pasta", "ricotta", "canditi"], "disc": "pasticceria"},
    ],
    "Lazio": [
        {"nome": "Coda alla vaccinara con cacao", "chiave": "coda di bue", "firma": ["coda di bue", "sedano", "pinoli", "cacao"]},
        {"nome": "Fave e pecorino", "chiave": "fave", "firma": ["fave fresche", "pecorino romano"]},
    ],
    "Toscana": [
        {"nome": "Fagioli al fiasco", "chiave": "fagioli", "firma": ["fagioli", "aglio", "salvia", "olio"]},
        {"nome": "Cieche alla pisana", "chiave": "anguilla", "firma": ["cieche", "aglio", "salvia"]},
    ],
    "Piemonte": [
        {"nome": "Fritto misto dolce e salato", "chiave": "carne", "firma": ["carni", "semolino dolce", "amaretti", "mele"]},
        {"nome": "Bagna cauda light", "chiave": "acciughe", "firma": ["acciughe", "aglio", "latte", "olio"]},
    ],
    "Puglia": [
        {"nome": "Orecchiette con broccoli e salsiccia", "chiave": "salsiccia", "firma": ["orecchiette", "broccoli", "salsiccia"]},
    ],
    "Veneto": [
        {"nome": "Zuppa di pesce chioggiotta", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "aceto"]},
    ],
    "Emilia-Romagna": [
        {"nome": "Zuppa imperiale", "chiave": "uova", "firma": ["semolino", "uova", "parmigiano", "brodo"]},
    ],
    "Lombardia": [
        {"nome": "Casoeula con verze", "chiave": "maiale", "firma": ["maiale", "verze", "cotenne"]},
    ],
    "Calabria": [
        {"nome": "Pesce spada alla calabrese", "chiave": "pesce spada", "firma": ["pesce spada", "pomodoro", "capperi", "olive"]},
    ],
    "Sardegna": [
        {"nome": "Agnello con carciofi sardo", "chiave": "agnello", "firma": ["agnello", "carciofi", "uova", "limone"]},
    ],
    "Marche": [
        {"nome": "Brodetto marchigiano a 13 pesci", "chiave": "pesce", "firma": ["tredici pesci", "pomodoro", "aceto"]},
    ],
}

MONDO_9 = {
    "Giappone": [
        {"nome": "Katsu curry", "chiave": "maiale", "firma": ["tonkatsu", "curry giapponese", "riso"]},
        {"nome": "Soba in brodo caldo", "chiave": "soba", "firma": ["soba", "brodo dashi", "cipollotto"]},
    ],
    "Cina": [
        {"nome": "Involtini primavera", "chiave": "verdure", "firma": ["pasta", "verdure", "germogli", "olio"]},
        {"nome": "Riso alla cantonese classico", "chiave": "riso", "firma": ["riso", "prosciutto", "uova", "piselli"]},
    ],
    "India": [
        {"nome": "Tarka dal", "chiave": "lenticchie", "firma": ["lenticchie", "cumino", "aglio", "burro chiarificato"]},
    ],
    "Francia": [
        {"nome": "Steak frites", "chiave": "manzo", "firma": ["bistecca", "patatine", "burro alle erbe"]},
        {"nome": "Croque monsieur", "chiave": "prosciutto", "firma": ["pane", "prosciutto", "besciamella", "gruyère"]},
    ],
    "Messico": [
        {"nome": "Nachos", "chiave": "tortilla", "firma": ["tortilla chips", "formaggio", "jalapeños", "fagioli"]},
    ],
    "Spagna": [
        {"nome": "Pan con tomate", "chiave": "pomodoro", "firma": ["pane", "pomodoro", "aglio", "olio"], "disc": "panificazione"},
        {"nome": "Albóndigas", "chiave": "carne macinata", "firma": ["polpette", "salsa di pomodoro", "vino"]},
    ],
    "USA / BBQ": [
        {"nome": "Sloppy joe", "chiave": "manzo", "firma": ["manzo macinato", "salsa", "pane"]},
    ],
    "Grecia": [
        {"nome": "Souvlaki di pollo", "chiave": "pollo", "firma": ["pollo", "limone", "origano", "pita"]},
    ],
    "Medio Oriente": [
        {"nome": "Ful medames", "chiave": "fave", "firma": ["fave", "aglio", "limone", "cumino"]},
    ],
    "Corea": [
        {"nome": "Bibim guksu", "chiave": "noodles", "firma": ["noodles", "gochujang", "verdure", "uovo"]},
    ],
    "Thailandia": [
        {"nome": "Khao man gai", "chiave": "pollo", "firma": ["pollo", "riso", "zenzero", "salsa di soia"]},
    ],
    "Portogallo": [
        {"nome": "Sardinhas assadas", "chiave": "sarde", "firma": ["sarde", "sale grosso", "pane"]},
    ],
}


# ultimi piatti per superare 1000
ITALIA_9["Lazio"].extend([
    {"nome": "Spaghetti aglio olio e peperoncino", "chiave": "aglio", "firma": ["spaghetti", "aglio", "peperoncino", "olio", "prezzemolo"]},
    {"nome": "Pasta e broccoli in brodo di arzilla", "chiave": "broccoli", "firma": ["pasta", "broccolo romanesco", "razza"]},
])
ITALIA_9["Campania"].extend([
    {"nome": "Spaghetti con la colatura di alici", "chiave": "acciughe", "firma": ["spaghetti", "colatura di alici", "aglio", "prezzemolo"]},
    {"nome": "Minestra di scarole e fagioli", "chiave": "fagioli", "firma": ["scarola", "fagioli", "aglio"]},
])
MONDO_9["Francia"].extend([
    {"nome": "Ratatouille niçoise", "chiave": "verdure", "firma": ["melanzane", "zucchine", "peperoni", "pomodoro", "timo"]},
    {"nome": "Tarte flambée", "chiave": "farina", "firma": ["pasta sottile", "panna acida", "cipolla", "pancetta"], "disc": "panificazione"},
])
MONDO_9["Cina"].extend([
    {"nome": "Noodles saltati con verdure", "chiave": "noodles", "firma": ["noodles", "verdure", "salsa di soia", "germogli"]},
    {"nome": "Pollo alle mandorle", "chiave": "pollo", "firma": ["pollo", "mandorle", "verdure", "salsa"]},
])
MONDO_9["India"].extend([
    {"nome": "Chicken 65", "chiave": "pollo", "firma": ["pollo", "peperoncino", "curry foglie", "yogurt"]},
    {"nome": "Aloo matar", "chiave": "patate", "firma": ["patate", "piselli", "pomodoro", "spezie"]},
])
MONDO_9["Messico"].extend([
    {"nome": "Burrito", "chiave": "tortilla", "firma": ["tortilla di grano", "fagioli", "riso", "carne", "formaggio"]},
    {"nome": "Salsa guacamole piccante", "chiave": "avocado", "firma": ["avocado", "lime", "peperoncino", "coriandolo"]},
])
MONDO_9["Giappone"].extend([
    {"nome": "Poke bowl giapponese", "chiave": "pesce", "firma": ["riso", "tonno crudo", "avocado", "salsa di soia"]},
])

MONDO_9["Giappone"].append({"nome": "Ramen shio", "chiave": "sale", "firma": ["noodles", "brodo di sale", "chashu", "cipollotto"]})
ITALIA_9["Sicilia"].append({"nome": "Pasta ammuddicata", "chiave": "acciughe", "firma": ["pasta", "acciughe", "mollica tostata", "aglio"]})
