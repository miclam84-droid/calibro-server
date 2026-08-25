# mappa_mondo4.py
# MAPPA MONDO — parte 4: ancora piatti per raggiungere la copertura piena.

CUCINE4 = {
    "Giappone": [
        {"nome": "Ochazuke", "chiave": "riso", "firma": ["riso", "tè verde", "salmone", "alga"]},
        {"nome": "Gyudon", "chiave": "manzo", "firma": ["manzo", "cipolla", "salsa di soia", "riso"]},
        {"nome": "Agedashi tofu", "chiave": "tofu", "firma": ["tofu", "fecola", "brodo dashi", "cipollotto"]},
        {"nome": "Nikujaga", "chiave": "manzo", "firma": ["manzo", "patate", "carote", "salsa di soia"]},
    ],
    "Cina": [
        {"nome": "Zuppa wonton", "chiave": "gamberi", "firma": ["wonton", "brodo", "gamberi", "cipollotto"]},
        {"nome": "Congee", "chiave": "riso", "firma": ["riso", "brodo", "zenzero", "cipollotto"]},
        {"nome": "Maiale in salsa di fagioli neri", "chiave": "maiale", "firma": ["maiale", "fagioli neri fermentati", "aglio", "peperoni"]},
        {"nome": "Anatra croccante", "chiave": "anatra", "firma": ["anatra", "cinque spezie", "salsa hoisin"]},
    ],
    "India": [
        {"nome": "Malai kofta", "chiave": "paneer", "firma": ["polpette di paneer", "salsa cremosa", "spezie"]},
        {"nome": "Keema", "chiave": "carne macinata", "firma": ["carne macinata", "piselli", "spezie", "cipolla"]},
        {"nome": "Chole bhature", "chiave": "ceci", "firma": ["ceci speziati", "pane fritto"]},
        {"nome": "Masala dosa", "chiave": "riso", "firma": ["dosa", "patate", "curry", "senape"]},
    ],
    "Thailandia": [
        {"nome": "Panang curry", "chiave": "latte di cocco", "firma": ["pasta panang", "latte di cocco", "manzo", "arachidi"]},
        {"nome": "Pad see ew", "chiave": "noodles", "firma": ["noodles piatti", "salsa di soia scura", "cavolo cinese", "uova"]},
        {"nome": "Larb", "chiave": "carne macinata", "firma": ["carne macinata", "riso tostato", "lime", "erbe", "peperoncino"]},
    ],
    "Vietnam / SE Asia": [
        {"nome": "Bun bo Hue", "chiave": "manzo", "firma": ["noodles", "brodo di manzo piccante", "citronella"]},
        {"nome": "Com tam", "chiave": "maiale", "firma": ["riso spezzato", "maiale grigliato", "uovo"]},
        {"nome": "Cao lau", "chiave": "maiale", "firma": ["noodles", "maiale", "erbe", "crackers"]},
    ],
    "Messico": [
        {"nome": "Birria", "chiave": "manzo", "firma": ["manzo o capra", "peperoncini", "spezie", "brodo"]},
        {"nome": "Tinga de pollo", "chiave": "pollo", "firma": ["pollo", "chipotle", "pomodoro", "cipolla"]},
        {"nome": "Menudo", "chiave": "trippa", "firma": ["trippa", "hominy", "peperoncino", "origano"]},
    ],
    "Grecia": [
        {"nome": "Pastitsio", "chiave": "carne macinata", "firma": ["pasta", "carne macinata", "besciamella", "cannella"]},
        {"nome": "Dolmades", "chiave": "riso", "firma": ["foglie di vite", "riso", "erbe", "limone"]},
        {"nome": "Keftedes", "chiave": "carne macinata", "firma": ["carne macinata", "menta", "cipolla", "pane"]},
        {"nome": "Galaktoboureko", "chiave": "semolino", "firma": ["pasta fillo", "crema di semolino", "sciroppo"], "disc": "pasticceria"},
    ],
    "Spagna": [
        {"nome": "Fabada asturiana", "chiave": "fagioli", "firma": ["fagioli fabes", "chorizo", "morcilla", "pancetta"]},
        {"nome": "Pisto manchego", "chiave": "verdure", "firma": ["zucchine", "peperoni", "pomodoro", "cipolla"]},
        {"nome": "Calamares a la romana", "chiave": "calamari", "firma": ["calamari", "farina", "olio per friggere"]},
        {"nome": "Crema catalana", "chiave": "uova", "firma": ["latte", "tuorli", "zucchero", "cannella", "limone"], "disc": "pasticceria"},
    ],
    "USA / BBQ": [
        {"nome": "Buffalo wings", "chiave": "pollo", "firma": ["ali di pollo", "salsa piccante", "burro"]},
        {"nome": "Jambalaya", "chiave": "riso", "firma": ["riso", "salsiccia", "gamberi", "pollo", "spezie cajun"]},
        {"nome": "Cornbread", "chiave": "farina di mais", "firma": ["farina di mais", "burro", "uova", "latticello"], "disc": "panificazione"},
        {"nome": "Pancakes", "chiave": "farina", "firma": ["farina", "uova", "latte", "sciroppo d'acero"], "disc": "pasticceria"},
    ],
    "Filippine": [
        {"nome": "Adobo", "chiave": "pollo", "firma": ["pollo o maiale", "salsa di soia", "aceto", "aglio", "alloro"]},
        {"nome": "Sinigang", "chiave": "maiale", "firma": ["maiale", "tamarindo", "verdure", "brodo acido"]},
        {"nome": "Lumpia", "chiave": "carne", "firma": ["involtini", "carne", "verdure"]},
        {"nome": "Pancit", "chiave": "noodles", "firma": ["noodles", "verdure", "carne", "salsa di soia"]},
    ],
    "Indonesia / Malesia": [
        {"nome": "Satay ayam", "chiave": "pollo", "firma": ["pollo", "spezie", "salsa di arachidi"]},
        {"nome": "Beef rendang", "chiave": "manzo", "firma": ["manzo", "latte di cocco", "spezie", "citronella"]},
        {"nome": "Mie goreng", "chiave": "noodles", "firma": ["noodles", "kecap manis", "verdure", "uovo"]},
        {"nome": "Gado gado", "chiave": "verdure", "firma": ["verdure lesse", "salsa di arachidi", "uovo", "tofu"]},
    ],
    "Caraibi": [
        {"nome": "Jerk chicken", "chiave": "pollo", "firma": ["pollo", "spezie jerk", "peperoncino scotch bonnet"]},
        {"nome": "Ropa vieja", "chiave": "manzo", "firma": ["manzo sfilacciato", "peperoni", "pomodoro", "cumino"]},
        {"nome": "Rice and peas", "chiave": "riso", "firma": ["riso", "fagioli", "latte di cocco", "timo"]},
    ],
}
