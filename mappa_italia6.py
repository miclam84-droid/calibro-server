# mappa_italia6.py
# MAPPA ITALIA — parte 6: ultimo strato (dolci, street food, piatti di mare, primi minori).

REGIONI_6 = {
    "Campania": [
        {"nome": "Spaghetti a vongole fujute", "chiave": "pomodoro", "firma": ["spaghetti", "pomodorini", "aglio", "prezzemolo"]},
        {"nome": "Baccalà alla napoletana", "chiave": "baccalà", "firma": ["baccalà", "pomodoro", "olive", "capperi", "pinoli"]},
        {"nome": "Polpettone napoletano", "chiave": "carne macinata", "firma": ["carne macinata", "uova sode", "provola", "pane"]},
        {"nome": "Insalata di mare", "chiave": "frutti di mare", "firma": ["polpo", "calamari", "gamberi", "limone", "prezzemolo"]},
        {"nome": "Torta caprese al limone", "chiave": "mandorle", "firma": ["mandorle", "cioccolato bianco", "limone"], "disc": "pasticceria"},
    ],
    "Sicilia": [
        {"nome": "Pasta con le melanzane e ricotta salata", "chiave": "melanzane", "firma": ["pasta", "melanzane", "ricotta salata", "pomodoro"]},
        {"nome": "Sarde a linguata", "chiave": "sarde", "firma": ["sarde", "farina", "aceto", "menta"]},
        {"nome": "Caponata di pesce spada", "chiave": "pesce spada", "firma": ["pesce spada", "sedano", "olive", "capperi"]},
        {"nome": "Cassatelle di ricotta", "chiave": "ricotta", "firma": ["pasta", "ricotta", "cioccolato", "cannella"], "disc": "pasticceria"},
        {"nome": "Torrone di mandorle", "chiave": "mandorle", "firma": ["mandorle", "miele", "albume"], "disc": "pasticceria"},
    ],
    "Lazio": [
        {"nome": "Minestra di broccoli e pasta", "chiave": "broccoli", "firma": ["pasta", "broccolo romanesco", "brodo di prosciutto"]},
        {"nome": "Saltimbocca di pollo", "chiave": "pollo", "firma": ["pollo", "prosciutto", "salvia"]},
        {"nome": "Pangiallo romano", "chiave": "frutta secca", "firma": ["frutta secca", "miele", "canditi"], "disc": "pasticceria"},
    ],
    "Puglia": [
        {"nome": "Orecchiette con braciole", "chiave": "manzo", "firma": ["orecchiette", "braciole di manzo", "pomodoro"]},
        {"nome": "Pancotto pugliese", "chiave": "pane", "firma": ["pane raffermo", "rucola", "patate", "aglio"]},
        {"nome": "Focaccia con cipolle", "chiave": "farina", "firma": ["pasta pane", "cipolle", "olive"], "disc": "panificazione"},
    ],
    "Toscana": [
        {"nome": "Pappardelle alla lepre", "chiave": "lepre", "firma": ["pappardelle", "lepre", "vino rosso", "pomodoro"]},
        {"nome": "Zuppa di farro", "chiave": "farro", "firma": ["farro", "fagioli", "verdure"]},
        {"nome": "Necci con ricotta", "chiave": "farina di castagne", "firma": ["farina di castagne", "ricotta"], "disc": "pasticceria"},
    ],
    "Emilia-Romagna": [
        {"nome": "Garganelli al prosciutto", "chiave": "prosciutto", "firma": ["garganelli", "prosciutto", "panna", "piselli"]},
        {"nome": "Spoja lorda", "chiave": "formaggio", "firma": ["pasta all'uovo", "ricotta", "brodo"]},
        {"nome": "Migliaccio ferrarese", "chiave": "maiale", "firma": ["sangue di maiale", "pane", "spezie"]},
    ],
    "Veneto": [
        {"nome": "Bigoli con l'anatra", "chiave": "anatra", "firma": ["bigoli", "anatra", "brodo"]},
        {"nome": "Moeche fritte", "chiave": "granchio", "firma": ["granchi molle", "farina", "uova", "olio"]},
        {"nome": "Zaeti", "chiave": "farina di mais", "firma": ["farina di mais", "uvetta", "burro"], "disc": "pasticceria"},
    ],
    "Piemonte": [
        {"nome": "Risotto alla piemontese al tartufo", "chiave": "tartufo", "firma": ["riso", "tartufo bianco", "burro", "parmigiano"]},
        {"nome": "Coniglio alla piemontese", "chiave": "coniglio", "firma": ["coniglio", "vino bianco", "rosmarino", "peperoni"]},
        {"nome": "Torta gianduia", "chiave": "cioccolato", "firma": ["cioccolato", "nocciole", "burro"], "disc": "pasticceria"},
    ],
    "Lombardia": [
        {"nome": "Risotto alla monzese", "chiave": "riso", "firma": ["riso", "luganega", "zafferano", "pomodoro"]},
        {"nome": "Stracotto d'asino", "chiave": "asino", "firma": ["asino", "vino rosso", "verdure"]},
        {"nome": "Colomba pasquale", "chiave": "farina", "firma": ["farina", "burro", "uova", "canditi", "mandorle"], "disc": "panificazione"},
    ],
    "Liguria": [
        {"nome": "Trenette al pesto", "chiave": "basilico", "firma": ["trenette", "pesto", "patate", "fagiolini"]},
        {"nome": "Buridda di seppie", "chiave": "seppia", "firma": ["seppie", "piselli", "pomodoro", "vino"]},
        {"nome": "Focaccia di Recco", "chiave": "formaggio", "firma": ["pasta sottile", "crescenza"], "disc": "panificazione"},
    ],
    "Sardegna": [
        {"nome": "Spaghetti alla bottarga", "chiave": "bottarga", "firma": ["spaghetti", "bottarga", "aglio", "olio"]},
        {"nome": "Cordula con piselli", "chiave": "agnello", "firma": ["cordula d'agnello", "piselli"]},
        {"nome": "Sebadas con miele", "chiave": "pecorino", "firma": ["pasta", "pecorino fresco", "miele"], "disc": "pasticceria"},
    ],
    "Trentino-Alto Adige": [
        {"nome": "Canederli allo speck", "chiave": "pane", "firma": ["pane", "speck", "uova", "erba cipollina"]},
        {"nome": "Tortel di patate", "chiave": "patate", "firma": ["patate grattugiate", "farina", "olio"]},
        {"nome": "Buchteln", "chiave": "farina", "firma": ["pasta lievitata", "marmellata"], "disc": "pasticceria"},
    ],
    "Marche": [
        {"nome": "Vincisgrassi marchigiani", "chiave": "carne", "firma": ["sfoglia", "ragù di rigaglie", "besciamella"]},
        {"nome": "Coniglio in potacchio", "chiave": "coniglio", "firma": ["coniglio", "rosmarino", "aglio", "vino"]},
        {"nome": "Ciambelle di mosto", "chiave": "mosto", "firma": ["farina", "mosto d'uva", "olio"], "disc": "pasticceria"},
    ],
    "Umbria": [
        {"nome": "Cardi alla perugina", "chiave": "cardi", "firma": ["cardi", "ragù", "besciamella"]},
        {"nome": "Porchetta di Norcia", "chiave": "maiale", "firma": ["maiale", "finocchietto", "aglio", "pepe"]},
    ],
    "Molise": [
        {"nome": "Zuppa di cardi", "chiave": "cardi", "firma": ["cardi", "brodo", "polpettine", "uova"]},
        {"nome": "Taccozze e fagioli", "chiave": "fagioli", "firma": ["pasta", "fagioli", "cotenna"]},
    ],
}
