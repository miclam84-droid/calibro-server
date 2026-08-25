# mappa_extra7.py
# ULTIMO STRATO — Italia + mondo, per completare oltre 1000 piatti canonici.

ITALIA_7 = {
    "Campania": [
        {"nome": "Pasta e zucca", "chiave": "zucca", "firma": ["pasta", "zucca", "provola", "pancetta"]},
        {"nome": "Zuppa di lenticchie napoletana", "chiave": "lenticchie", "firma": ["lenticchie", "pomodoro", "sedano"]},
        {"nome": "Cianfotta", "chiave": "verdure", "firma": ["melanzane", "peperoni", "patate", "pomodoro"]},
        {"nome": "Ministra maritata", "chiave": "verdure", "firma": ["verdure", "carni di maiale", "brodo"]},
    ],
    "Sicilia": [
        {"nome": "Pasta al forno alla siciliana", "chiave": "pasta", "firma": ["pasta", "ragù", "melanzane", "caciocavallo", "uova"]},
        {"nome": "Scacce ragusane", "chiave": "farina", "firma": ["pasta pane", "pomodoro", "caciocavallo"], "disc": "panificazione"},
        {"nome": "Falso magro al sugo", "chiave": "manzo", "firma": ["manzo", "uova", "formaggio", "pomodoro"]},
    ],
    "Lazio": [
        {"nome": "Stracciatella alla romana", "chiave": "uova", "firma": ["uova", "parmigiano", "brodo", "semolino"]},
        {"nome": "Vignarola", "chiave": "verdure", "firma": ["fave", "piselli", "carciofi", "guanciale"]},
        {"nome": "Pizza bianca romana", "chiave": "farina", "firma": ["pasta pizza", "olio", "sale"], "disc": "panificazione"},
    ],
    "Toscana": [
        {"nome": "Farinata di cavolo nero", "chiave": "cavolo nero", "firma": ["cavolo nero", "fagioli", "farina di mais"]},
        {"nome": "Rosticciana toscana", "chiave": "maiale", "firma": ["costine di maiale", "salvia", "vino"]},
        {"nome": "Brutti ma buoni", "chiave": "nocciole", "firma": ["nocciole", "albumi", "zucchero"], "disc": "pasticceria"},
    ],
    "Puglia": [
        {"nome": "Minestra di fave e bietole", "chiave": "fave", "firma": ["fave", "bietole", "olio"]},
        {"nome": "Calzone di cipolla", "chiave": "cipolla", "firma": ["pasta", "cipolla sponsale", "olive", "acciughe"], "disc": "panificazione"},
    ],
    "Emilia-Romagna": [
        {"nome": "Maccheroni al pettine col ragù", "chiave": "carne macinata", "firma": ["maccheroni", "ragù", "parmigiano"]},
        {"nome": "Salama da sugo", "chiave": "maiale", "firma": ["salame speziato", "vino", "purè"]},
    ],
    "Veneto": [
        {"nome": "Risotto agli asparagi", "chiave": "asparagi", "firma": ["riso", "asparagi", "brodo", "parmigiano"]},
        {"nome": "Fegato alla veneziana con polenta", "chiave": "fegato", "firma": ["fegato", "cipolla", "polenta"]},
    ],
    "Piemonte": [
        {"nome": "Zuppa di castagne e riso", "chiave": "castagne", "firma": ["castagne", "riso", "latte"]},
        {"nome": "Bocconcini di vitello ai funghi", "chiave": "vitello", "firma": ["vitello", "funghi", "vino"]},
    ],
    "Lombardia": [
        {"nome": "Risotto giallo con ossobuco", "chiave": "riso carnaroli", "firma": ["risotto milanese", "ossobuco", "gremolada"]},
        {"nome": "Zuppa pavese", "chiave": "uova", "firma": ["brodo", "uovo", "pane", "parmigiano"]},
    ],
    "Calabria": [
        {"nome": "Pasta china", "chiave": "pasta", "firma": ["pasta", "polpettine", "uova", "provola"]},
        {"nome": "Ciambotta calabrese", "chiave": "verdure", "firma": ["melanzane", "peperoni", "patate", "pomodoro"]},
    ],
    "Liguria": [
        {"nome": "Torta di riso ligure", "chiave": "riso", "firma": ["riso", "uova", "parmigiano", "maggiorana"]},
        {"nome": "Sardenaira", "chiave": "pomodoro", "firma": ["pasta pane", "pomodoro", "acciughe", "olive"], "disc": "panificazione"},
    ],
    "Sardegna": [
        {"nome": "Malloreddus al ragù di salsiccia", "chiave": "salsiccia", "firma": ["malloreddus", "salsiccia", "zafferano", "pecorino"]},
        {"nome": "Panada di anguille", "chiave": "anguilla", "firma": ["pasta", "anguilla", "patate", "pomodoro"]},
    ],
    "Trentino-Alto Adige": [
        {"nome": "Orzotto ai funghi", "chiave": "orzo", "firma": ["orzo", "funghi", "brodo", "formaggio"]},
        {"nome": "Gröstl", "chiave": "patate", "firma": ["patate", "manzo", "cipolla", "uovo"]},
    ],
    "Marche": [
        {"nome": "Brodetto di San Benedetto", "chiave": "pesce", "firma": ["pesce misto", "pomodoro verde", "aceto"]},
        {"nome": "Calcioni marchigiani", "chiave": "formaggio", "firma": ["pasta", "pecorino", "uova"], "disc": "pasticceria"},
    ],
    "Umbria": [
        {"nome": "Gnocchi al sagrantino", "chiave": "patate", "firma": ["gnocchi", "salsiccia", "sagrantino"]},
        {"nome": "Attorta umbra", "chiave": "mele", "firma": ["pasta", "mele", "noci", "uvetta"], "disc": "pasticceria"},
    ],
    "Abruzzo": [
        {"nome": "Zuppa di lenticchie di Santo Stefano", "chiave": "lenticchie", "firma": ["lenticchie", "soffritto", "olio"]},
        {"nome": "Pizza dogana", "chiave": "farina di mais", "firma": ["farina di mais", "verdure", "peperoncino"]},
    ],
    "Basilicata": [
        {"nome": "Lagane e ceci lucane", "chiave": "ceci", "firma": ["lagane", "ceci", "peperoncino", "aglio"]},
        {"nome": "Ciaudedda lucana", "chiave": "verdure", "firma": ["carciofi", "fave", "patate", "cipolla"]},
    ],
    "Molise": [
        {"nome": "Cavatelli alla molisana", "chiave": "carne", "firma": ["cavatelli", "ragù di maiale", "peperoncino"]},
        {"nome": "Calcioni di ricotta rustici", "chiave": "ricotta", "firma": ["pasta", "ricotta", "salumi"], "disc": "pasticceria"},
    ],
    "Friuli-Venezia Giulia": [
        {"nome": "Orzo e fagioli friulano", "chiave": "orzo", "firma": ["orzo", "fagioli", "cotenna"]},
        {"nome": "Toc' in braide", "chiave": "farina di mais", "firma": ["polenta morbida", "formaggio", "burro"]},
    ],
    "Valle d'Aosta": [
        {"nome": "Seupa à la valpelleunentse", "chiave": "cavolo", "firma": ["cavolo", "pane nero", "fontina", "brodo"]},
        {"nome": "Costolette alla valdostana", "chiave": "vitello", "firma": ["vitello", "fontina", "prosciutto", "pangrattato"]},
    ],
}

MONDO_7 = {
    "Giappone": [
        {"nome": "Buta no kakuni", "chiave": "maiale", "firma": ["pancetta di maiale", "salsa di soia", "zenzero", "sakè"]},
        {"nome": "Ebi furai", "chiave": "gamberi", "firma": ["gamberi", "panko", "salsa tonkatsu"]},
    ],
    "Cina": [
        {"nome": "Riso saltato con gamberi", "chiave": "gamberi", "firma": ["riso", "gamberi", "uova", "cipollotto"]},
        {"nome": "Manzo con cipollotto", "chiave": "manzo", "firma": ["manzo", "cipollotto", "salsa di ostriche"]},
    ],
    "India": [
        {"nome": "Egg curry", "chiave": "uova", "firma": ["uova sode", "pomodoro", "cipolla", "spezie"]},
        {"nome": "Bhindi masala", "chiave": "okra", "firma": ["okra", "cipolla", "pomodoro", "spezie"]},
    ],
    "Francia": [
        {"nome": "Poulet basquaise", "chiave": "pollo", "firma": ["pollo", "peperoni", "pomodoro", "prosciutto di baiona"]},
        {"nome": "Clafoutis", "chiave": "ciliegie", "firma": ["ciliegie", "uova", "latte", "farina"], "disc": "pasticceria"},
    ],
    "Messico": [
        {"nome": "Mole verde", "chiave": "pollo", "firma": ["pollo", "tomatillo", "peperoncini verdi", "semi di zucca"]},
        {"nome": "Tacos dorados", "chiave": "tortilla", "firma": ["tortilla", "pollo", "salsa", "panna acida"]},
    ],
    "Medio Oriente": [
        {"nome": "Msabaha", "chiave": "ceci", "firma": ["ceci interi", "tahini", "limone", "cumino"]},
        {"nome": "Sabich", "chiave": "melanzane", "firma": ["pita", "melanzane fritte", "uovo", "tahini"]},
    ],
    "Spagna": [
        {"nome": "Bacalao al pil pil", "chiave": "baccalà", "firma": ["baccalà", "aglio", "peperoncino", "olio"]},
        {"nome": "Migas", "chiave": "pane", "firma": ["pane", "chorizo", "aglio", "peperoni"]},
    ],
    "Grecia": [
        {"nome": "Kleftiko", "chiave": "agnello", "firma": ["agnello", "limone", "origano", "aglio"]},
        {"nome": "Revithada", "chiave": "ceci", "firma": ["ceci", "cipolla", "limone", "olio"]},
    ],
    "USA / BBQ": [
        {"nome": "Philly cheesesteak", "chiave": "manzo", "firma": ["manzo", "cipolla", "formaggio", "pane"]},
        {"nome": "Cobb salad", "chiave": "pollo", "firma": ["pollo", "bacon", "avocado", "uova", "formaggio blu"]},
    ],
    "Corea": [
        {"nome": "Bossam", "chiave": "maiale", "firma": ["pancetta di maiale lessa", "kimchi", "aglio"]},
        {"nome": "Kimbap", "chiave": "riso", "firma": ["riso", "alga", "verdure", "uovo", "manzo"]},
    ],
    "Vietnam / SE Asia": [
        {"nome": "Bun rieu", "chiave": "granchio", "firma": ["noodles", "brodo di granchio", "pomodoro", "tofu"]},
        {"nome": "Ga nuong", "chiave": "pollo", "firma": ["pollo", "citronella", "salsa di pesce", "miele"]},
    ],
    "Thailandia": [
        {"nome": "Gaeng som", "chiave": "pesce", "firma": ["pesce", "curry acido", "verdure", "tamarindo"]},
        {"nome": "Khao niaow ma muang", "chiave": "riso glutinoso", "firma": ["riso glutinoso", "mango", "latte di cocco"], "disc": "pasticceria"},
    ],
    "Portogallo": [
        {"nome": "Arroz de marisco", "chiave": "frutti di mare", "firma": ["riso", "frutti di mare", "pomodoro", "coriandolo"]},
        {"nome": "Francesinha", "chiave": "carne", "firma": ["pane", "carni", "formaggio", "salsa birra"]},
    ],
    "Turchia": [
        {"nome": "Iskender kebab", "chiave": "agnello", "firma": ["agnello", "pane", "yogurt", "salsa di pomodoro", "burro"]},
        {"nome": "Imam bayildi", "chiave": "melanzane", "firma": ["melanzane", "cipolla", "pomodoro", "aglio"]},
    ],
    "Bar / Cocktail": [
        {"nome": "Tom Collins", "chiave": "gin", "firma": ["gin", "limone", "zucchero", "soda"], "disc": "bar"},
        {"nome": "Dark 'n' Stormy", "chiave": "rum", "firma": ["rum scuro", "ginger beer", "lime"], "disc": "bar"},
        {"nome": "Gimlet", "chiave": "gin", "firma": ["gin", "lime cordial"], "disc": "bar"},
        {"nome": "Rob Roy", "chiave": "whiskey", "firma": ["scotch", "vermouth rosso", "angostura"], "disc": "bar"},
        {"nome": "Vesper", "chiave": "gin", "firma": ["gin", "vodka", "lillet blanc"], "disc": "bar"},
        {"nome": "Mint Julep", "chiave": "whiskey", "firma": ["bourbon", "menta", "zucchero"], "disc": "bar"},
        {"nome": "Clover Club", "chiave": "gin", "firma": ["gin", "lampone", "limone", "albume"], "disc": "bar"},
        {"nome": "Corpse Reviver", "chiave": "gin", "firma": ["gin", "cointreau", "lillet", "limone", "assenzio"], "disc": "bar"},
    ],
}
