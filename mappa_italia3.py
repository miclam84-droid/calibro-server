# mappa_italia3.py
# MAPPA ITALIA — parte 3: ancora piatti canonici regionali. Verso una copertura piena.

REGIONI_3 = {
    "Lazio": [
        {"nome": "Rigatoni con la pajata", "chiave": "pajata", "firma": ["rigatoni", "pajata", "pomodoro", "pecorino"]},
        {"nome": "Spaghetti cacio e uova", "chiave": "uova", "firma": ["spaghetti", "uova", "pecorino", "pepe"]},
        {"nome": "Broccoli e arzilla in brodo", "chiave": "razza", "firma": ["razza", "broccolo romanesco", "pomodoro"]},
        {"nome": "Abbacchio al forno con patate", "chiave": "agnello", "firma": ["agnello", "patate", "rosmarino", "aglio"]},
        {"nome": "Carciofi alla matticella", "chiave": "carciofi", "firma": ["carciofi", "mentuccia", "olio"]},
    ],
    "Campania": [
        {"nome": "Paccheri alla Genovese di mare", "chiave": "polpo", "firma": ["paccheri", "polpo", "cipolla", "vino"]},
        {"nome": "Pasta e fagioli con le cozze", "chiave": "fagioli", "firma": ["pasta", "fagioli", "cozze"]},
        {"nome": "Peperoni imbottiti", "chiave": "peperoni", "firma": ["peperoni", "pane", "capperi", "olive", "acciughe"]},
        {"nome": "Melanzane a funghetto", "chiave": "melanzane", "firma": ["melanzane", "pomodorini", "aglio", "basilico"]},
        {"nome": "Casatiello", "chiave": "farina", "firma": ["pasta pane", "strutto", "salumi", "formaggi", "uova"], "disc": "panificazione"},
        {"nome": "Graffe napoletane", "chiave": "patate", "firma": ["farina", "patate", "uova", "zucchero"], "disc": "pasticceria"},
    ],
    "Sicilia": [
        {"nome": "Pasta con i tenerumi", "chiave": "tenerumi", "firma": ["spaghetti spezzati", "tenerumi", "pomodoro", "aglio"]},
        {"nome": "Stigghiola", "chiave": "budella", "firma": ["budella d'agnello", "prezzemolo", "limone"]},
        {"nome": "Sfincione", "chiave": "farina", "firma": ["pasta pane", "pomodoro", "cipolla", "acciughe", "caciocavallo"], "disc": "panificazione"},
        {"nome": "Braciole messinesi", "chiave": "manzo", "firma": ["manzo", "pangrattato", "caciocavallo", "pomodoro"]},
        {"nome": "Minne di Sant'Agata", "chiave": "ricotta", "firma": ["pan di spagna", "ricotta", "glassa"], "disc": "pasticceria"},
    ],
    "Puglia": [
        {"nome": "Cavatelli e cozze", "chiave": "cozze", "firma": ["cavatelli", "cozze", "pomodorini", "aglio"]},
        {"nome": "Cime di rapa stufate", "chiave": "cime di rapa", "firma": ["cime di rapa", "aglio", "peperoncino", "olio"]},
        {"nome": "Bombette pugliesi", "chiave": "maiale", "firma": ["capocollo di maiale", "formaggio", "pancetta"]},
        {"nome": "Purè di fave e cicoria", "chiave": "fave", "firma": ["fave secche", "cicoria", "olio"]},
    ],
    "Toscana": [
        {"nome": "Tortelli maremmani", "chiave": "ricotta", "firma": ["pasta all'uovo", "ricotta", "spinaci", "ragù"]},
        {"nome": "Scottiglia", "chiave": "carne", "firma": ["carni miste", "pomodoro", "vino", "pane"]},
        {"nome": "Fagioli all'uccelletto", "chiave": "fagioli", "firma": ["fagioli cannellini", "salvia", "pomodoro", "aglio"]},
        {"nome": "Cecina", "chiave": "ceci", "firma": ["farina di ceci", "acqua", "olio"], "disc": "panificazione"},
    ],
    "Piemonte": [
        {"nome": "Plin al sugo d'arrosto", "chiave": "carne", "firma": ["agnolotti del plin", "sugo d'arrosto"]},
        {"nome": "Peperoni con bagna cauda", "chiave": "peperoni", "firma": ["peperoni", "acciughe", "aglio", "olio"]},
        {"nome": "Fritto misto alla piemontese", "chiave": "carne", "firma": ["carni", "verdure", "semolino", "amaretti"]},
        {"nome": "Baci di dama", "chiave": "nocciole", "firma": ["nocciole", "burro", "cioccolato"], "disc": "pasticceria"},
    ],
    "Emilia-Romagna": [
        {"nome": "Strozzapreti alla romagnola", "chiave": "salsiccia", "firma": ["strozzapreti", "salsiccia", "pomodoro", "panna"]},
        {"nome": "Bollito con salsa verde", "chiave": "manzo", "firma": ["manzo", "verdure", "salsa verde"]},
        {"nome": "Crescentine (tigelle)", "chiave": "farina", "firma": ["farina", "strutto", "latte"], "disc": "panificazione"},
        {"nome": "Gnocco fritto", "chiave": "farina", "firma": ["farina", "strutto", "salumi"], "disc": "panificazione"},
    ],
    "Veneto": [
        {"nome": "Pasta e fasioi", "chiave": "fagioli", "firma": ["pasta", "fagioli di lamon", "cotenna"]},
        {"nome": "Seppie in nero con polenta", "chiave": "seppia", "firma": ["seppie", "nero di seppia", "polenta"]},
        {"nome": "Pastissada de caval", "chiave": "cavallo", "firma": ["carne di cavallo", "vino", "spezie"]},
        {"nome": "Fritole", "chiave": "farina", "firma": ["farina", "uvetta", "pinoli", "grappa"], "disc": "pasticceria"},
    ],
    "Lombardia": [
        {"nome": "Tortelli di zucca mantovani", "chiave": "zucca", "firma": ["pasta", "zucca", "amaretti", "mostarda"]},
        {"nome": "Polenta taragna", "chiave": "farina di mais", "firma": ["farina di mais", "grano saraceno", "formaggio", "burro"]},
        {"nome": "Busecca (trippa)", "chiave": "trippa", "firma": ["trippa", "fagioli", "pomodoro"]},
    ],
    "Calabria": [
        {"nome": "Lagane e ceci", "chiave": "ceci", "firma": ["lagane", "ceci", "aglio", "peperoncino"]},
        {"nome": "Stocco alla mammolese", "chiave": "stoccafisso", "firma": ["stoccafisso", "patate", "olive", "peperoni"]},
        {"nome": "Frittole calabresi", "chiave": "maiale", "firma": ["carne di maiale", "grasso", "spezie"]},
    ],
    "Sardegna": [
        {"nome": "Fregola con cozze", "chiave": "cozze", "firma": ["fregola", "cozze", "pomodoro", "aglio"]},
        {"nome": "Porceddu allo spiedo", "chiave": "maiale", "firma": ["maialino da latte", "mirto"]},
        {"nome": "Sa fregula incasada", "chiave": "semola", "firma": ["fregola", "brodo", "pecorino"]},
    ],
}
