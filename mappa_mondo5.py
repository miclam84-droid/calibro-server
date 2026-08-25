# mappa_mondo5.py
# MAPPA MONDO — parte 5: completamento cucine + drink classici (bar).

CUCINE5 = {
    "Francia": [
        {"nome": "Cassolette de fruits de mer", "chiave": "frutti di mare", "firma": ["frutti di mare", "vino bianco", "panna", "erbe"]},
        {"nome": "Choucroute garnie", "chiave": "maiale", "firma": ["crauti", "salsicce", "maiale", "patate"]},
        {"nome": "Aligot", "chiave": "patate", "firma": ["patate", "tomme", "aglio", "burro"]},
        {"nome": "Tartiflette", "chiave": "patate", "firma": ["patate", "reblochon", "pancetta", "cipolla"]},
        {"nome": "Crêpes suzette", "chiave": "farina", "firma": ["crêpes", "burro", "arancia", "grand marnier"], "disc": "pasticceria"},
        {"nome": "Financier", "chiave": "mandorle", "firma": ["farina di mandorle", "burro nocciola", "albumi"], "disc": "pasticceria"},
    ],
    "Cina": [
        {"nome": "Pollo agrodolce cantonese", "chiave": "pollo", "firma": ["pollo", "ananas", "peperoni", "salsa agrodolce"]},
        {"nome": "Chow fun di manzo", "chiave": "manzo", "firma": ["noodles piatti", "manzo", "germogli", "salsa di soia"]},
        {"nome": "Zuppa di mais e granchio", "chiave": "granchio", "firma": ["mais", "granchio", "uovo", "brodo"]},
        {"nome": "Tofu mala", "chiave": "tofu", "firma": ["tofu", "pepe di sichuan", "peperoncino", "olio"]},
    ],
    "India": [
        {"nome": "Fish curry del Kerala", "chiave": "pesce", "firma": ["pesce", "latte di cocco", "curry", "tamarindo"]},
        {"nome": "Aloo paratha", "chiave": "farina", "firma": ["pane", "patate speziate"], "disc": "panificazione"},
        {"nome": "Paneer tikka", "chiave": "paneer", "firma": ["paneer", "yogurt", "spezie", "peperoni"]},
        {"nome": "Kheer", "chiave": "riso", "firma": ["riso", "latte", "cardamomo", "frutta secca"], "disc": "pasticceria"},
    ],
    "Giappone": [
        {"nome": "Hiyashi chuka", "chiave": "noodles", "firma": ["noodles freddi", "verdure", "prosciutto", "uovo"]},
        {"nome": "Zaru soba", "chiave": "soba", "firma": ["soba freddi", "salsa tsuyu", "wasabi"]},
        {"nome": "Motsunabe", "chiave": "frattaglie", "firma": ["frattaglie", "cavolo", "brodo", "aglio"]},
    ],
    "Perù": [
        {"nome": "Aji de gallina", "chiave": "pollo", "firma": ["pollo", "aji amarillo", "pane", "noci"]},
        {"nome": "Papa a la huancaina", "chiave": "patate", "firma": ["patate", "aji amarillo", "formaggio", "latte"]},
        {"nome": "Anticuchos", "chiave": "manzo", "firma": ["cuore di manzo", "aji panca", "aceto", "cumino"]},
    ],
    "Brasile": [
        {"nome": "Feijoada completa", "chiave": "fagioli neri", "firma": ["fagioli neri", "maiale", "salsicce", "arancia"]},
        {"nome": "Coxinha", "chiave": "pollo", "firma": ["pollo", "pasta", "pangrattato"]},
        {"nome": "Pão de queijo", "chiave": "formaggio", "firma": ["tapioca", "formaggio", "uova"], "disc": "panificazione"},
        {"nome": "Brigadeiro", "chiave": "cioccolato", "firma": ["latte condensato", "cacao", "burro"], "disc": "pasticceria"},
    ],
    "Marocco": [
        {"nome": "Pastilla", "chiave": "piccione", "firma": ["pasta warqa", "piccione", "mandorle", "cannella", "zucchero"]},
        {"nome": "Tagine di manzo e prugne", "chiave": "manzo", "firma": ["manzo", "prugne", "mandorle", "spezie"]},
        {"nome": "Zaalouk", "chiave": "melanzane", "firma": ["melanzane", "pomodoro", "aglio", "cumino"]},
    ],
    "Etiopia / Africa sub": [
        {"nome": "Kitfo", "chiave": "manzo", "firma": ["manzo crudo", "burro speziato", "mitmita"]},
        {"nome": "Shiro", "chiave": "ceci", "firma": ["farina di ceci", "berbere", "aglio"]},
        {"nome": "Tibs", "chiave": "manzo", "firma": ["manzo", "cipolla", "peperoni", "rosmarino"]},
    ],
    "Bar / Cocktail": [
        {"nome": "Negroni", "chiave": "gin", "firma": ["gin", "vermouth rosso", "bitter campari"], "disc": "bar"},
        {"nome": "Americano", "chiave": "bitter", "firma": ["bitter campari", "vermouth rosso", "soda"], "disc": "bar"},
        {"nome": "Martini cocktail", "chiave": "gin", "firma": ["gin", "vermouth dry"], "disc": "bar"},
        {"nome": "Manhattan", "chiave": "whiskey", "firma": ["rye whiskey", "vermouth rosso", "angostura"], "disc": "bar"},
        {"nome": "Old Fashioned", "chiave": "whiskey", "firma": ["bourbon", "zucchero", "angostura"], "disc": "bar"},
        {"nome": "Daiquiri", "chiave": "rum", "firma": ["rum bianco", "lime", "zucchero"], "disc": "bar"},
        {"nome": "Margarita", "chiave": "tequila", "firma": ["tequila", "triple sec", "lime"], "disc": "bar"},
        {"nome": "Mojito", "chiave": "rum", "firma": ["rum bianco", "lime", "menta", "zucchero", "soda"], "disc": "bar"},
        {"nome": "Aperol Spritz", "chiave": "aperol", "firma": ["aperol", "prosecco", "soda"], "disc": "bar"},
        {"nome": "Espresso Martini", "chiave": "vodka", "firma": ["vodka", "caffè espresso", "liquore al caffè"], "disc": "bar"},
        {"nome": "Whiskey Sour", "chiave": "whiskey", "firma": ["bourbon", "limone", "zucchero", "albume"], "disc": "bar"},
        {"nome": "Aviation", "chiave": "gin", "firma": ["gin", "maraschino", "crème de violette", "limone"], "disc": "bar"},
        {"nome": "Cosmopolitan", "chiave": "vodka", "firma": ["vodka", "triple sec", "succo di mirtillo", "lime"], "disc": "bar"},
        {"nome": "Boulevardier", "chiave": "whiskey", "firma": ["bourbon", "vermouth rosso", "campari"], "disc": "bar"},
        {"nome": "Paloma", "chiave": "tequila", "firma": ["tequila", "pompelmo", "lime", "soda"], "disc": "bar"},
    ],
}
