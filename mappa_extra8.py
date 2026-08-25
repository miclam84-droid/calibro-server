# mappa_extra8.py
# BLOCCO FINALE — supera i 1000 piatti canonici. Italia oltre 500 + completamento cucine mondo magre.

ITALIA_8 = {
    "Campania": [
        {"nome": "Pasta e cavolfiore", "chiave": "cavolfiore", "firma": ["pasta", "cavolfiore", "aglio", "peperoncino"]},
        {"nome": "Braciole di maiale al ragù", "chiave": "maiale", "firma": ["maiale", "pinoli", "uvetta", "pomodoro"]},
        {"nome": "Frittata di maccheroni", "chiave": "pasta", "firma": ["pasta", "uova", "formaggio", "salumi"]},
    ],
    "Sicilia": [
        {"nome": "Pasta col nero di seppia", "chiave": "seppia", "firma": ["pasta", "seppie", "nero di seppia", "pomodoro"]},
        {"nome": "Cuscus di pesce trapanese", "chiave": "pesce", "firma": ["couscous", "pesce", "brodo", "mandorle"]},
    ],
    "Lazio": [
        {"nome": "Pollo alla cacciatora romana", "chiave": "pollo", "firma": ["pollo", "aceto", "acciughe", "rosmarino"]},
        {"nome": "Minestra di arzilla e broccoli", "chiave": "razza", "firma": ["razza", "broccolo romanesco", "pasta"]},
    ],
    "Toscana": [
        {"nome": "Tortelli di patate mugellani", "chiave": "patate", "firma": ["pasta", "patate", "ragù"]},
        {"nome": "Bordatino pisano", "chiave": "cavolo nero", "firma": ["farina di mais", "cavolo nero", "fagioli"]},
    ],
    "Puglia": [
        {"nome": "Riso cozze e patate al forno", "chiave": "cozze", "firma": ["riso", "cozze", "patate", "pecorino"]},
        {"nome": "Verdure gratinate pugliesi", "chiave": "verdure", "firma": ["verdure miste", "pangrattato", "olio"]},
    ],
    "Piemonte": [
        {"nome": "Tofeja piemontese", "chiave": "fagioli", "firma": ["fagioli", "cotenne", "piedini di maiale"]},
        {"nome": "Panissa vercellese", "chiave": "riso", "firma": ["riso", "fagioli", "salame", "vino"]},
    ],
    "Emilia-Romagna": [
        {"nome": "Tortellini panna e prosciutto", "chiave": "prosciutto", "firma": ["tortellini", "panna", "prosciutto"]},
        {"nome": "Friggione bolognese", "chiave": "cipolla", "firma": ["cipolle", "pomodoro", "olio"]},
    ],
    "Lombardia": [
        {"nome": "Risotto alla certosina", "chiave": "gamberi di fiume", "firma": ["riso", "gamberi di fiume", "rane", "verdure"]},
        {"nome": "Polenta e osei", "chiave": "farina di mais", "firma": ["polenta", "uccelletti", "burro"]},
    ],
    "Veneto": [
        {"nome": "Radicchio e fagioli", "chiave": "radicchio", "firma": ["radicchio", "fagioli", "pancetta"]},
        {"nome": "Risi e verze", "chiave": "riso", "firma": ["riso", "verze", "pancetta", "brodo"]},
    ],
    "Calabria": [
        {"nome": "Sagne chine", "chiave": "pasta", "firma": ["lasagne", "polpettine", "uova", "provola"]},
        {"nome": "Baccalà fritto alla calabrese", "chiave": "baccalà", "firma": ["baccalà", "pastella", "peperoncino"]},
    ],
    "Sardegna": [
        {"nome": "Favata sarda", "chiave": "fave", "firma": ["fave secche", "maiale", "finocchietto"]},
        {"nome": "Burrida alla cagliaritana", "chiave": "pesce", "firma": ["gattuccio", "noci", "aceto", "aglio"]},
    ],
    "Marche": [
        {"nome": "Olive ascolane con fritto misto", "chiave": "olive", "firma": ["olive ripiene", "carne", "verdure fritte"]},
        {"nome": "Maccheroncini di Campofilone", "chiave": "carne macinata", "firma": ["maccheroncini", "ragù", "parmigiano"]},
    ],
    "Umbria": [
        {"nome": "Ciriole alla ternana", "chiave": "pomodoro", "firma": ["ciriole", "pomodoro", "aglio", "peperoncino"]},
        {"nome": "Fagiolina con salsicce", "chiave": "fagioli", "firma": ["fagiolina", "salsicce", "pomodoro"]},
    ],
    "Abruzzo": [
        {"nome": "Cazzarielli e fagioli", "chiave": "fagioli", "firma": ["cazzarielli", "fagioli", "peperoncino"]},
        {"nome": "Coratella d'agnello", "chiave": "agnello", "firma": ["coratella", "cipolla", "vino", "peperoncino"]},
    ],
    "Liguria": [
        {"nome": "Cappon magro genovese", "chiave": "pesce", "firma": ["pesce", "verdure", "salsa verde", "gallette"]},
        {"nome": "Ravioli di magro al tocco", "chiave": "carne", "firma": ["ravioli", "sugo di carne"]},
    ],
    "Basilicata": [
        {"nome": "Cutturidde", "chiave": "agnello", "firma": ["agnello", "cipolla", "sedano", "pecorino"]},
    ],
    "Molise": [
        {"nome": "Brodetto di seppie molisano", "chiave": "seppia", "firma": ["seppie", "pomodoro", "peperoncino"]},
    ],
    "Friuli-Venezia Giulia": [
        {"nome": "Muset e brovada", "chiave": "maiale", "firma": ["cotechino", "rape fermentate"]},
    ],
    "Valle d'Aosta": [
        {"nome": "Polenta grassa", "chiave": "farina di mais", "firma": ["polenta", "fontina", "burro"]},
    ],
    "Trentino-Alto Adige": [
        {"nome": "Zuppa d'orzo altoatesina", "chiave": "orzo", "firma": ["orzo", "speck", "verdure"]},
    ],
}

MONDO_8 = {
    "Nord Africa": [
        {"nome": "Chakchouka tunisina", "chiave": "uova", "firma": ["uova", "peperoni", "pomodoro", "harissa"]},
        {"nome": "Tajine di sardine", "chiave": "sarde", "firma": ["sarde", "chermoula", "pomodoro"]},
    ],
    "Sud America": [
        {"nome": "Pabellón criollo", "chiave": "manzo", "firma": ["manzo sfilacciato", "fagioli neri", "riso", "platano"]},
        {"nome": "Anticuchos peruviani", "chiave": "manzo", "firma": ["cuore di manzo", "aji panca", "aceto"]},
        {"nome": "Humita", "chiave": "mais", "firma": ["mais", "cipolla", "formaggio", "foglie di mais"]},
    ],
    "Est Europa / Russia": [
        {"nome": "Bigos polacco", "chiave": "cavolo", "firma": ["crauti", "cavolo", "salsicce", "carne"]},
        {"nome": "Vareniki", "chiave": "patate", "firma": ["pasta", "patate", "formaggio", "cipolla"]},
        {"nome": "Solyanka", "chiave": "carne", "firma": ["carni miste", "cetriolini", "olive", "brodo"]},
    ],
    "Regno Unito / Irlanda": [
        {"nome": "Bangers and mash", "chiave": "salsiccia", "firma": ["salsicce", "purè", "gravy di cipolla"]},
        {"nome": "Cornish pasty", "chiave": "manzo", "firma": ["pasta", "manzo", "patate", "rutabaga"]},
        {"nome": "Full English breakfast", "chiave": "uova", "firma": ["uova", "bacon", "salsicce", "fagioli", "pomodoro"]},
    ],
    "Filippine": [
        {"nome": "Kare kare", "chiave": "manzo", "firma": ["coda di bue", "salsa di arachidi", "verdure", "bagoong"]},
        {"nome": "Tocino", "chiave": "maiale", "firma": ["maiale", "zucchero", "aglio", "annatto"]},
    ],
    "Indonesia / Malesia": [
        {"nome": "Soto ayam", "chiave": "pollo", "firma": ["pollo", "brodo di curcuma", "noodles", "uovo"]},
        {"nome": "Ayam goreng", "chiave": "pollo", "firma": ["pollo", "spezie", "olio per friggere"]},
    ],
    "Caraibi": [
        {"nome": "Mofongo", "chiave": "platano", "firma": ["platano verde", "aglio", "ciccioli"]},
        {"nome": "Callaloo", "chiave": "verdure", "firma": ["foglie di taro", "latte di cocco", "granchio"]},
    ],
    "Perù": [
        {"nome": "Causa limeña", "chiave": "patate", "firma": ["patate", "aji amarillo", "pollo", "avocado"]},
    ],
    "Marocco": [
        {"nome": "Rfissa", "chiave": "pollo", "firma": ["pollo", "lenticchie", "msemen", "fieno greco"]},
    ],
    "Etiopia / Africa sub": [
        {"nome": "Misir wot", "chiave": "lenticchie", "firma": ["lenticchie rosse", "berbere", "cipolla"]},
    ],
    "Libano": [
        {"nome": "Shish taouk", "chiave": "pollo", "firma": ["pollo", "aglio", "limone", "yogurt"]},
        {"nome": "Loubieh bi zeit", "chiave": "fagiolini", "firma": ["fagiolini", "pomodoro", "aglio", "olio"]},
    ],
    "Ungheria / Est": [
        {"nome": "Halászlé", "chiave": "pesce", "firma": ["pesce d'acqua dolce", "paprika", "cipolla"]},
    ],
    "Argentina / Uruguay": [
        {"nome": "Locro", "chiave": "mais", "firma": ["mais", "fagioli", "zucca", "carne"]},
        {"nome": "Chivito uruguaiano", "chiave": "manzo", "firma": ["manzo", "prosciutto", "formaggio", "uovo", "pane"]},
    ],
    "Brasile": [
        {"nome": "Acarajé", "chiave": "fagioli", "firma": ["fagioli neri", "gamberi secchi", "olio di palma"]},
        {"nome": "Vatapá", "chiave": "gamberi", "firma": ["gamberi", "latte di cocco", "pane", "arachidi"]},
    ],
}
