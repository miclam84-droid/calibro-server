# mappa_mondo6.py
# MAPPA MONDO — parte 6: ultimo completamento verso 1000.

CUCINE6 = {
    "Giappone": [
        {"nome": "Yakisoba", "chiave": "noodles", "firma": ["noodles", "cavolo", "maiale", "salsa yakisoba"]},
        {"nome": "Oyakodon", "chiave": "pollo", "firma": ["pollo", "uova", "cipolla", "riso"]},
        {"nome": "Tamagoyaki", "chiave": "uova", "firma": ["uova", "dashi", "salsa di soia", "zucchero"]},
        {"nome": "Unagi don", "chiave": "anguilla", "firma": ["anguilla", "salsa kabayaki", "riso"]},
    ],
    "Cina": [
        {"nome": "Ma po noodles", "chiave": "noodles", "firma": ["noodles", "maiale", "doubanjiang", "pepe di sichuan"]},
        {"nome": "Pollo croccante al limone", "chiave": "pollo", "firma": ["pollo fritto", "salsa al limone"]},
        {"nome": "Wonton fritti", "chiave": "maiale", "firma": ["pasta wonton", "maiale", "gamberi"]},
    ],
    "India": [
        {"nome": "Tandoori paneer", "chiave": "paneer", "firma": ["paneer", "yogurt", "spezie tandoori"]},
        {"nome": "Prawn masala", "chiave": "gamberi", "firma": ["gamberi", "pomodoro", "cipolla", "spezie"]},
        {"nome": "Jalebi", "chiave": "farina", "firma": ["pastella fermentata", "sciroppo", "zafferano"], "disc": "pasticceria"},
    ],
    "Thailandia": [
        {"nome": "Khao pad", "chiave": "riso", "firma": ["riso", "uova", "gamberi", "salsa di pesce"]},
        {"nome": "Yam nua", "chiave": "manzo", "firma": ["manzo", "lime", "peperoncino", "erbe"]},
    ],
    "Corea": [
        {"nome": "Dakgalbi", "chiave": "pollo", "firma": ["pollo", "gochujang", "cavolo", "tteok"]},
        {"nome": "Gyeranjjim", "chiave": "uova", "firma": ["uova", "brodo", "cipollotto"]},
    ],
    "Messico": [
        {"nome": "Sopes", "chiave": "masa", "firma": ["masa", "fagioli", "carne", "formaggio"]},
        {"nome": "Huevos rancheros", "chiave": "uova", "firma": ["uova", "tortilla", "salsa", "fagioli"]},
        {"nome": "Flan messicano", "chiave": "uova", "firma": ["uova", "latte condensato", "caramello"], "disc": "pasticceria"},
    ],
    "Medio Oriente": [
        {"nome": "Manakish za'atar", "chiave": "farina", "firma": ["pasta", "za'atar", "olio"], "disc": "panificazione"},
        {"nome": "Mujadara", "chiave": "lenticchie", "firma": ["lenticchie", "riso", "cipolla caramellata"]},
        {"nome": "Kanafeh", "chiave": "formaggio", "firma": ["pasta kataifi", "formaggio", "sciroppo"], "disc": "pasticceria"},
        {"nome": "Maqluba", "chiave": "riso", "firma": ["riso", "melanzane", "pollo", "spezie"]},
    ],
    "Grecia": [
        {"nome": "Gemista", "chiave": "verdure", "firma": ["pomodori", "peperoni", "riso", "erbe"]},
        {"nome": "Fasolada", "chiave": "fagioli", "firma": ["fagioli", "pomodoro", "sedano", "carote"]},
        {"nome": "Loukoumades", "chiave": "farina", "firma": ["pasta", "miele", "cannella"], "disc": "pasticceria"},
    ],
    "Spagna": [
        {"nome": "Cocido madrileño", "chiave": "ceci", "firma": ["ceci", "carne", "chorizo", "verdure"]},
        {"nome": "Pulpo a feira", "chiave": "polpo", "firma": ["polpo", "patate", "paprika"]},
        {"nome": "Ensaladilla rusa", "chiave": "patate", "firma": ["patate", "tonno", "piselli", "maionese"]},
    ],
    "Vietnam / SE Asia": [
        {"nome": "Banh xeo", "chiave": "gamberi", "firma": ["crêpe di riso", "gamberi", "germogli", "erbe"]},
        {"nome": "Ca kho to", "chiave": "pesce", "firma": ["pesce", "caramello", "salsa di pesce", "pepe"]},
    ],
    "USA / BBQ": [
        {"nome": "Gumbo", "chiave": "gamberi", "firma": ["roux", "gamberi", "salsiccia", "okra", "riso"]},
        {"nome": "Chili con carne", "chiave": "manzo", "firma": ["manzo", "fagioli", "pomodoro", "peperoncino"]},
        {"nome": "Brownie", "chiave": "cioccolato", "firma": ["cioccolato", "burro", "uova", "farina"], "disc": "pasticceria"},
    ],
    "Argentina / Uruguay": [
        {"nome": "Milanesa napolitana", "chiave": "manzo", "firma": ["manzo impanato", "prosciutto", "formaggio", "pomodoro"]},
        {"nome": "Provoleta", "chiave": "formaggio", "firma": ["provolone", "origano", "peperoncino"]},
        {"nome": "Dulce de leche", "chiave": "latte", "firma": ["latte", "zucchero"], "disc": "pasticceria"},
        {"nome": "Alfajores", "chiave": "farina", "firma": ["biscotti", "dulce de leche", "cocco"], "disc": "pasticceria"},
    ],
    "Germania / Austria": [
        {"nome": "Rouladen", "chiave": "manzo", "firma": ["manzo", "pancetta", "cetriolini", "senape"]},
        {"nome": "Kaiserschmarrn", "chiave": "farina", "firma": ["frittata dolce", "uvetta", "zucchero"], "disc": "pasticceria"},
        {"nome": "Linzer torte", "chiave": "mandorle", "firma": ["mandorle", "marmellata di ribes", "cannella"], "disc": "pasticceria"},
    ],
    "Ungheria / Est": [
        {"nome": "Chicken paprikash", "chiave": "pollo", "firma": ["pollo", "paprika", "panna acida", "cipolla"]},
        {"nome": "Langos", "chiave": "farina", "firma": ["pasta fritta", "aglio", "panna acida", "formaggio"], "disc": "panificazione"},
        {"nome": "Cevapi", "chiave": "carne macinata", "firma": ["carne macinata", "cipolla", "ajvar"]},
    ],
    "Bar / Cocktail": [
        {"nome": "Gin Tonic", "chiave": "gin", "firma": ["gin", "acqua tonica", "lime"], "disc": "bar"},
        {"nome": "Moscow Mule", "chiave": "vodka", "firma": ["vodka", "ginger beer", "lime"], "disc": "bar"},
        {"nome": "Piña Colada", "chiave": "rum", "firma": ["rum", "latte di cocco", "ananas"], "disc": "bar"},
        {"nome": "Caipirinha", "chiave": "cachaça", "firma": ["cachaça", "lime", "zucchero"], "disc": "bar"},
        {"nome": "Bloody Mary", "chiave": "vodka", "firma": ["vodka", "succo di pomodoro", "tabasco", "worcester"], "disc": "bar"},
        {"nome": "Sidecar", "chiave": "cognac", "firma": ["cognac", "triple sec", "limone"], "disc": "bar"},
        {"nome": "Sazerac", "chiave": "whiskey", "firma": ["rye whiskey", "assenzio", "zucchero", "peychaud's"], "disc": "bar"},
        {"nome": "French 75", "chiave": "gin", "firma": ["gin", "champagne", "limone", "zucchero"], "disc": "bar"},
        {"nome": "Mai Tai", "chiave": "rum", "firma": ["rum", "orgeat", "curaçao", "lime"], "disc": "bar"},
        {"nome": "Bellini", "chiave": "prosecco", "firma": ["prosecco", "purea di pesca"], "disc": "bar"},
    ],
}
