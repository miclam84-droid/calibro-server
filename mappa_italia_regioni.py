# mappa_italia_regioni.py
# MAPPA DEI PIATTI CANONICI ITALIANI PER REGIONE — tutti e 20 i territori.
# Fonte: tradizione regionale codificata (tipo Ada Boni "Italian Regional Cooking" 600 ricette,
# Slow Food Dictionary). Ogni piatto ha: nome, firma (ingredienti che lo DEFINISCONO), ingrediente_chiave.
# Il motore NON inventa: prende un piatto canonico vero + grounding (correttezza) + verificatore (no eresie).
# Verificabile a colpo d'occhio da un professionista italiano.

REGIONI = {
    "Lazio": [
        {"nome": "Carbonara", "chiave": "guanciale", "firma": ["spaghetti", "guanciale", "tuorli", "pecorino romano", "pepe nero"]},
        {"nome": "Amatriciana", "chiave": "guanciale", "firma": ["bucatini", "guanciale", "pomodoro", "pecorino romano", "peperoncino"]},
        {"nome": "Gricia", "chiave": "guanciale", "firma": ["rigatoni", "guanciale", "pecorino romano", "pepe nero"]},
        {"nome": "Cacio e pepe", "chiave": "pecorino romano", "firma": ["tonnarelli", "pecorino romano", "pepe nero"]},
        {"nome": "Saltimbocca alla romana", "chiave": "vitello", "firma": ["vitello", "prosciutto crudo", "salvia", "burro"]},
        {"nome": "Abbacchio alla scottadito", "chiave": "agnello", "firma": ["costolette di agnello", "rosmarino", "aglio", "olio"]},
        {"nome": "Coda alla vaccinara", "chiave": "coda di bue", "firma": ["coda di bue", "sedano", "pomodoro", "vino"]},
        {"nome": "Carciofi alla giudia", "chiave": "carciofi", "firma": ["carciofi romaneschi", "olio per friggere", "sale"]},
        {"nome": "Carciofi alla romana", "chiave": "carciofi", "firma": ["carciofi", "mentuccia", "aglio", "olio"]},
        {"nome": "Trippa alla romana", "chiave": "trippa", "firma": ["trippa", "pomodoro", "pecorino", "mentuccia"]},
        {"nome": "Pollo coi peperoni", "chiave": "pollo", "firma": ["pollo", "peperoni", "pomodoro", "vino"]},
        {"nome": "Maritozzo", "chiave": "farina", "firma": ["farina", "panna montata", "uvetta"], "disc": "pasticceria"},
    ],
    "Campania": [
        {"nome": "Pizza margherita", "chiave": "mozzarella", "firma": ["impasto pizza", "pomodoro", "mozzarella", "basilico", "olio"], "disc": "panificazione"},
        {"nome": "Pizza marinara", "chiave": "pomodoro", "firma": ["impasto pizza", "pomodoro", "aglio", "origano", "olio"], "disc": "panificazione"},
        {"nome": "Spaghetti alle vongole", "chiave": "vongole", "firma": ["spaghetti", "vongole", "aglio", "prezzemolo", "olio", "vino bianco"]},
        {"nome": "Parmigiana di melanzane", "chiave": "melanzane", "firma": ["melanzane", "pomodoro", "mozzarella", "parmigiano", "basilico"]},
        {"nome": "Genovese napoletana", "chiave": "cipolla", "firma": ["cipolle", "manzo", "pasta ziti"]},
        {"nome": "Ragù napoletano", "chiave": "carne", "firma": ["carne mista", "pomodoro", "cipolla", "vino"]},
        {"nome": "Sartù di riso", "chiave": "riso", "firma": ["riso", "ragù", "piselli", "mozzarella", "polpettine"]},
        {"nome": "Gattò di patate", "chiave": "patate", "firma": ["patate", "uova", "provola", "salumi"]},
        {"nome": "Acqua pazza", "chiave": "pesce", "firma": ["pesce", "pomodorini", "aglio", "prezzemolo", "olio"]},
        {"nome": "Pastiera napoletana", "chiave": "ricotta", "firma": ["grano cotto", "ricotta", "uova", "acqua di fiori d'arancio", "canditi"], "disc": "pasticceria"},
        {"nome": "Babà", "chiave": "farina", "firma": ["farina", "uova", "burro", "rum", "zucchero"], "disc": "pasticceria"},
        {"nome": "Sfogliatella", "chiave": "ricotta", "firma": ["pasta sfoglia", "ricotta", "semola", "canditi"], "disc": "pasticceria"},
        {"nome": "Caprese (torta)", "chiave": "cioccolato", "firma": ["mandorle", "cioccolato", "burro", "uova"], "disc": "pasticceria"},
    ],
    "Sicilia": [
        {"nome": "Pasta alla Norma", "chiave": "melanzane", "firma": ["pasta", "melanzane", "pomodoro", "ricotta salata", "basilico"]},
        {"nome": "Pasta con le sarde", "chiave": "sarde", "firma": ["bucatini", "sarde", "finocchietto", "uvetta", "pinoli"]},
        {"nome": "Caponata", "chiave": "melanzane", "firma": ["melanzane", "sedano", "olive", "capperi", "aceto", "zucchero"]},
        {"nome": "Arancini", "chiave": "riso", "firma": ["riso", "ragù", "piselli", "caciocavallo", "pangrattato"]},
        {"nome": "Sarde a beccafico", "chiave": "sarde", "firma": ["sarde", "pangrattato", "uvetta", "pinoli"]},
        {"nome": "Cannoli siciliani", "chiave": "ricotta", "firma": ["cialda fritta", "ricotta", "zucchero", "gocce di cioccolato"], "disc": "pasticceria"},
        {"nome": "Cassata siciliana", "chiave": "ricotta", "firma": ["pan di spagna", "ricotta", "pasta di mandorle", "canditi"], "disc": "pasticceria"},
        {"nome": "Granita", "chiave": "zucchero", "firma": ["acqua", "zucchero", "frutta o caffè"], "disc": "gelateria"},
    ],
    "Lombardia": [
        {"nome": "Risotto alla milanese", "chiave": "riso carnaroli", "firma": ["riso carnaroli", "brodo", "zafferano", "burro", "parmigiano", "cipolla"]},
        {"nome": "Ossobuco alla milanese", "chiave": "vitello", "firma": ["ossobuco di vitello", "brodo", "vino bianco", "gremolada"]},
        {"nome": "Cotoletta alla milanese", "chiave": "vitello", "firma": ["costoletta di vitello", "uova", "pangrattato", "burro"]},
        {"nome": "Cassoeula", "chiave": "maiale", "firma": ["maiale", "verze", "cotenne", "salsicce"]},
        {"nome": "Pizzoccheri", "chiave": "grano saraceno", "firma": ["grano saraceno", "verze", "patate", "formaggio valtellina", "burro"]},
        {"nome": "Panettone", "chiave": "farina", "firma": ["farina", "lievito madre", "burro", "uvetta", "canditi"], "disc": "panificazione"},
    ],
    "Emilia-Romagna": [
        {"nome": "Tagliatelle al ragù", "chiave": "carne macinata", "firma": ["tagliatelle", "carne macinata", "soffritto", "pomodoro", "vino"]},
        {"nome": "Lasagne alla bolognese", "chiave": "carne macinata", "firma": ["sfoglia", "ragù", "besciamella", "parmigiano"]},
        {"nome": "Tortellini in brodo", "chiave": "carne", "firma": ["pasta all'uovo", "ripieno di carne", "parmigiano", "brodo di cappone"]},
        {"nome": "Tagliatelle al tartufo", "chiave": "tartufo", "firma": ["tagliatelle", "tartufo", "burro", "parmigiano"]},
        {"nome": "Piadina", "chiave": "farina", "firma": ["farina", "strutto", "acqua", "sale"], "disc": "panificazione"},
        {"nome": "Tortelli di zucca", "chiave": "zucca", "firma": ["pasta all'uovo", "zucca", "amaretti", "parmigiano"]},
    ],
    "Toscana": [
        {"nome": "Bistecca alla fiorentina", "chiave": "manzo", "firma": ["bistecca di manzo chianina", "sale", "pepe", "olio"]},
        {"nome": "Ribollita", "chiave": "cavolo nero", "firma": ["cavolo nero", "fagioli", "pane", "verdure"]},
        {"nome": "Pappa al pomodoro", "chiave": "pomodoro", "firma": ["pane", "pomodoro", "aglio", "basilico", "olio"]},
        {"nome": "Panzanella", "chiave": "pane", "firma": ["pane", "pomodoro", "cipolla", "basilico", "aceto"]},
        {"nome": "Pappardelle al cinghiale", "chiave": "cinghiale", "firma": ["pappardelle", "cinghiale", "pomodoro", "vino"]},
        {"nome": "Cantucci", "chiave": "mandorle", "firma": ["farina", "mandorle", "uova", "zucchero"], "disc": "pasticceria"},
    ],
    "Piemonte": [
        {"nome": "Brasato al Barolo", "chiave": "manzo", "firma": ["manzo", "vino barolo", "soffritto", "brodo"]},
        {"nome": "Vitello tonnato", "chiave": "vitello", "firma": ["vitello", "tonno", "acciughe", "capperi", "maionese"]},
        {"nome": "Agnolotti del plin", "chiave": "carne", "firma": ["pasta all'uovo", "ripieno di arrosto", "burro"]},
        {"nome": "Bagna cauda", "chiave": "acciughe", "firma": ["acciughe", "aglio", "olio", "verdure"]},
        {"nome": "Bollito misto", "chiave": "manzo", "firma": ["manzo", "verdure", "salse (bagnet)"]},
        {"nome": "Tajarin al tartufo", "chiave": "tartufo", "firma": ["tajarin", "tartufo bianco", "burro"]},
        {"nome": "Zabaione", "chiave": "uova", "firma": ["tuorli", "zucchero", "vino marsala"], "disc": "pasticceria"},
    ],
    "Veneto": [
        {"nome": "Baccalà mantecato", "chiave": "baccalà", "firma": ["baccalà", "olio", "aglio"]},
        {"nome": "Baccalà alla vicentina", "chiave": "baccalà", "firma": ["baccalà", "latte", "cipolla", "acciughe", "polenta"]},
        {"nome": "Risi e bisi", "chiave": "riso", "firma": ["riso", "piselli", "brodo", "pancetta"]},
        {"nome": "Fegato alla veneziana", "chiave": "fegato", "firma": ["fegato di vitello", "cipolla", "vino", "prezzemolo"]},
        {"nome": "Bigoli in salsa", "chiave": "acciughe", "firma": ["bigoli", "acciughe", "cipolla", "olio"]},
        {"nome": "Tiramisù", "chiave": "mascarpone", "firma": ["savoiardi", "mascarpone", "uova", "caffè", "cacao"], "disc": "pasticceria"},
    ],
    "Puglia": [
        {"nome": "Orecchiette con le cime di rapa", "chiave": "cime di rapa", "firma": ["orecchiette", "cime di rapa", "aglio", "acciughe", "peperoncino"]},
        {"nome": "Focaccia barese", "chiave": "farina", "firma": ["farina", "patata", "pomodorini", "olive", "olio"], "disc": "panificazione"},
        {"nome": "Fave e cicoria", "chiave": "fave", "firma": ["fave secche", "cicoria", "olio"]},
        {"nome": "Tiella di riso patate e cozze", "chiave": "cozze", "firma": ["riso", "patate", "cozze", "pomodoro"]},
        {"nome": "Burrata", "chiave": "latte", "firma": ["latte", "panna", "stracciatella"]},
    ],
    "Liguria": [
        {"nome": "Pesto alla genovese", "chiave": "basilico", "firma": ["basilico", "pinoli", "parmigiano", "pecorino", "aglio", "olio"]},
        {"nome": "Trofie al pesto", "chiave": "basilico", "firma": ["trofie", "pesto", "patate", "fagiolini"]},
        {"nome": "Focaccia genovese", "chiave": "farina", "firma": ["farina", "acqua", "lievito", "olio", "sale"], "disc": "panificazione"},
        {"nome": "Farinata", "chiave": "ceci", "firma": ["farina di ceci", "acqua", "olio", "sale"], "disc": "panificazione"},
        {"nome": "Cappon magro", "chiave": "pesce", "firma": ["pesce", "verdure", "salsa verde", "gallette"]},
    ],
    "Sardegna": [
        {"nome": "Culurgiones", "chiave": "patate", "firma": ["pasta", "patate", "pecorino", "menta"]},
        {"nome": "Porceddu", "chiave": "maiale", "firma": ["maialino da latte", "mirto", "sale"]},
        {"nome": "Fregola con arselle", "chiave": "arselle", "firma": ["fregola", "arselle", "pomodoro", "aglio"]},
        {"nome": "Malloreddus alla campidanese", "chiave": "salsiccia", "firma": ["malloreddus", "salsiccia", "pomodoro", "zafferano", "pecorino"]},
        {"nome": "Seadas", "chiave": "pecorino", "firma": ["pasta", "pecorino fresco", "miele"], "disc": "pasticceria"},
    ],
    "Calabria": [
        {"nome": "'Nduja", "chiave": "maiale", "firma": ["carne di maiale", "peperoncino"]},
        {"nome": "Pasta con la 'nduja", "chiave": "nduja", "firma": ["pasta", "nduja", "pomodoro"]},
        {"nome": "Melanzane ripiene", "chiave": "melanzane", "firma": ["melanzane", "pane", "pecorino", "uova"]},
        {"nome": "Fileja con ragù di capra", "chiave": "capra", "firma": ["fileja", "capra", "pomodoro"]},
    ],
    "Abruzzo": [
        {"nome": "Arrosticini", "chiave": "pecora", "firma": ["carne di pecora", "sale"]},
        {"nome": "Maccheroni alla chitarra", "chiave": "carne", "firma": ["pasta alla chitarra", "ragù misto", "pecorino"]},
        {"nome": "Brodetto di pesce", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "peperoncino", "aglio"]},
        {"nome": "Timballo abruzzese", "chiave": "carne", "firma": ["scrippelle", "ragù", "polpettine", "uova"]},
    ],
    "Marche": [
        {"nome": "Vincisgrassi", "chiave": "carne", "firma": ["sfoglia", "ragù", "rigaglie", "besciamella"]},
        {"nome": "Brodetto all'anconetana", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "aceto"]},
        {"nome": "Olive all'ascolana", "chiave": "olive", "firma": ["olive", "carne", "pangrattato", "uova"]},
        {"nome": "Ciauscolo", "chiave": "maiale", "firma": ["carne di maiale", "spezie"]},
    ],
    "Umbria": [
        {"nome": "Strangozzi al tartufo", "chiave": "tartufo", "firma": ["strangozzi", "tartufo nero", "olio", "aglio"]},
        {"nome": "Porchetta", "chiave": "maiale", "firma": ["maiale", "finocchietto", "aglio", "sale"]},
        {"nome": "Torta al testo", "chiave": "farina", "firma": ["farina", "acqua", "bicarbonato"], "disc": "panificazione"},
        {"nome": "Lenticchie di Castelluccio", "chiave": "lenticchie", "firma": ["lenticchie", "soffritto", "olio"]},
    ],
    "Trentino-Alto Adige": [
        {"nome": "Canederli", "chiave": "pane", "firma": ["pane raffermo", "speck", "uova", "latte"]},
        {"nome": "Speck", "chiave": "maiale", "firma": ["coscia di maiale", "affumicatura", "spezie"]},
        {"nome": "Strudel di mele", "chiave": "mele", "firma": ["pasta", "mele", "uvetta", "cannella"], "disc": "pasticceria"},
        {"nome": "Gulasch", "chiave": "manzo", "firma": ["manzo", "cipolla", "paprika"]},
    ],
    "Friuli-Venezia Giulia": [
        {"nome": "Frico", "chiave": "formaggio montasio", "firma": ["formaggio montasio", "patate", "cipolla"]},
        {"nome": "Jota", "chiave": "fagioli", "firma": ["fagioli", "crauti", "patate", "maiale"]},
        {"nome": "Cjarsons", "chiave": "patate", "firma": ["pasta", "patate", "erbe", "ricotta affumicata"]},
        {"nome": "Prosciutto di San Daniele", "chiave": "maiale", "firma": ["coscia di maiale", "sale"]},
    ],
    "Basilicata": [
        {"nome": "Peperoni cruschi", "chiave": "peperoni", "firma": ["peperoni secchi", "olio", "sale"]},
        {"nome": "Pasta con peperoni cruschi", "chiave": "peperoni", "firma": ["pasta", "peperoni cruschi", "mollica", "aglio"]},
        {"nome": "Baccalà alla lucana", "chiave": "baccalà", "firma": ["baccalà", "peperoni cruschi", "aglio"]},
    ],
    "Molise": [
        {"nome": "Cavatelli", "chiave": "farina", "firma": ["semola", "acqua", "ragù"]},
        {"nome": "Pampanella", "chiave": "maiale", "firma": ["maiale", "peperoncino", "aglio", "aceto"]},
        {"nome": "Caciocavallo", "chiave": "latte", "firma": ["latte", "caglio"]},
    ],
    "Valle d'Aosta": [
        {"nome": "Fonduta valdostana", "chiave": "fontina", "firma": ["fontina", "latte", "tuorli", "burro"]},
        {"nome": "Carbonada", "chiave": "manzo", "firma": ["manzo", "vino rosso", "cipolla"]},
        {"nome": "Polenta concia", "chiave": "farina di mais", "firma": ["farina di mais", "fontina", "burro"]},
    ],
}


def tutti_i_piatti_italia():
    piatti = []
    for regione, lista in REGIONI.items():
        for p in lista:
            q = dict(p)
            q["regione"] = regione
            q["area"] = "Italia"
            piatti.append(q)
    return piatti


def conta_italia():
    piatti = tutti_i_piatti_italia()
    regioni = len(REGIONI)
    ingredienti_chiave = len({p["chiave"] for p in piatti})
    return {"regioni": regioni, "piatti": len(piatti), "ingredienti_chiave": ingredienti_chiave}
