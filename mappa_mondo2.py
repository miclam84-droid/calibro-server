# mappa_mondo2.py
# MAPPA MONDO — parte 2: altre cucine nazionali. Stesso schema.

CUCINE2 = {
    "Germania / Austria": [
        {"nome": "Wiener schnitzel", "chiave": "vitello", "firma": ["vitello", "pangrattato", "uova", "limone"]},
        {"nome": "Bratwurst con crauti", "chiave": "salsiccia", "firma": ["salsiccia", "crauti", "senape"]},
        {"nome": "Sauerbraten", "chiave": "manzo", "firma": ["manzo", "aceto", "spezie", "uvetta"]},
        {"nome": "Kartoffelsalat", "chiave": "patate", "firma": ["patate", "aceto", "senape", "cipolla"]},
        {"nome": "Käsespätzle", "chiave": "farina", "firma": ["spätzle", "formaggio", "cipolla fritta"]},
        {"nome": "Sachertorte", "chiave": "cioccolato", "firma": ["cioccolato", "marmellata di albicocche", "uova"], "disc": "pasticceria"},
        {"nome": "Apfelstrudel", "chiave": "mele", "firma": ["pasta", "mele", "uvetta", "cannella"], "disc": "pasticceria"},
        {"nome": "Pretzel", "chiave": "farina", "firma": ["farina", "lievito", "bicarbonato", "sale grosso"], "disc": "panificazione"},
    ],
    "Nord Africa": [
        {"nome": "Couscous marocchino", "chiave": "semola", "firma": ["couscous", "agnello", "verdure", "ceci", "spezie ras el hanout"]},
        {"nome": "Tagine di pollo e limone", "chiave": "pollo", "firma": ["pollo", "limone confit", "olive", "zafferano"]},
        {"nome": "Harira", "chiave": "lenticchie", "firma": ["lenticchie", "ceci", "pomodoro", "coriandolo"]},
        {"nome": "Brik tunisino", "chiave": "uova", "firma": ["pasta malsouka", "uovo", "tonno", "prezzemolo"]},
        {"nome": "Shakshuka", "chiave": "uova", "firma": ["uova", "pomodoro", "peperoni", "cumino"]},
        {"nome": "Merguez", "chiave": "agnello", "firma": ["agnello", "harissa", "spezie"]},
    ],
    "Sud America": [
        {"nome": "Empanadas argentine", "chiave": "carne", "firma": ["pasta", "carne", "cipolla", "olive", "uova"]},
        {"nome": "Asado argentino", "chiave": "manzo", "firma": ["manzo", "sale grosso", "chimichurri"]},
        {"nome": "Ceviche peruviano", "chiave": "pesce", "firma": ["pesce crudo", "lime", "peperoncino ají", "cipolla rossa"]},
        {"nome": "Lomo saltado", "chiave": "manzo", "firma": ["manzo", "cipolla", "pomodoro", "patatine", "salsa di soia"]},
        {"nome": "Feijoada brasiliana", "chiave": "fagioli neri", "firma": ["fagioli neri", "maiale", "salsicce", "riso"]},
        {"nome": "Arepa", "chiave": "mais", "firma": ["farina di mais", "acqua", "ripieno"], "disc": "panificazione"},
        {"nome": "Moqueca", "chiave": "pesce", "firma": ["pesce", "latte di cocco", "olio di palma", "peperoni"]},
        {"nome": "Chimichurri", "chiave": "prezzemolo", "firma": ["prezzemolo", "aglio", "aceto", "origano", "olio"]},
    ],
    "Est Europa / Russia": [
        {"nome": "Borscht", "chiave": "barbabietola", "firma": ["barbabietola", "cavolo", "manzo", "panna acida"]},
        {"nome": "Pierogi", "chiave": "patate", "firma": ["pasta", "patate", "formaggio", "cipolla"]},
        {"nome": "Goulash ungherese", "chiave": "manzo", "firma": ["manzo", "paprika", "cipolla", "patate"]},
        {"nome": "Beef stroganoff", "chiave": "manzo", "firma": ["manzo", "funghi", "panna acida", "senape"]},
        {"nome": "Golabki (involtini di cavolo)", "chiave": "cavolo", "firma": ["cavolo", "carne", "riso", "pomodoro"]},
        {"nome": "Blini", "chiave": "farina", "firma": ["farina", "uova", "latte", "lievito"], "disc": "pasticceria"},
    ],
    "Regno Unito / Irlanda": [
        {"nome": "Fish and chips", "chiave": "pesce", "firma": ["merluzzo", "pastella", "patate", "olio per friggere"]},
        {"nome": "Shepherd's pie", "chiave": "agnello", "firma": ["agnello macinato", "purè di patate", "carote", "piselli"]},
        {"nome": "Beef Wellington", "chiave": "manzo", "firma": ["filetto di manzo", "pasta sfoglia", "funghi", "prosciutto"]},
        {"nome": "Irish stew", "chiave": "agnello", "firma": ["agnello", "patate", "cipolla", "carote"]},
        {"nome": "Scones", "chiave": "farina", "firma": ["farina", "burro", "latte", "lievito"], "disc": "pasticceria"},
        {"nome": "Sticky toffee pudding", "chiave": "datteri", "firma": ["datteri", "farina", "salsa mou"], "disc": "pasticceria"},
    ],
    "Asia (altro)": [
        {"nome": "Nasi lemak", "chiave": "riso", "firma": ["riso al cocco", "sambal", "acciughe", "arachidi", "uovo"]},
        {"nome": "Rendang", "chiave": "manzo", "firma": ["manzo", "latte di cocco", "pasta di spezie", "citronella"]},
        {"nome": "Char kway teow", "chiave": "noodles", "firma": ["noodles piatti", "gamberi", "uova", "germogli", "salsa di soia"]},
        {"nome": "Hainanese chicken rice", "chiave": "pollo", "firma": ["pollo", "riso", "zenzero", "salsa di soia"]},
        {"nome": "Biryani pakistano", "chiave": "riso basmati", "firma": ["riso basmati", "montone", "spezie", "yogurt"]},
        {"nome": "Momos", "chiave": "carne", "firma": ["pasta", "carne", "zenzero", "aglio"]},
        {"nome": "Khao soi", "chiave": "noodles", "firma": ["noodles", "curry", "latte di cocco", "pollo"]},
    ],
    "Etiopia / Africa sub": [
        {"nome": "Injera con wat", "chiave": "teff", "firma": ["farina di teff fermentata", "stufato berbere"]},
        {"nome": "Doro wat", "chiave": "pollo", "firma": ["pollo", "berbere", "cipolla", "uova sode"]},
        {"nome": "Jollof rice", "chiave": "riso", "firma": ["riso", "pomodoro", "peperoni", "spezie"]},
        {"nome": "Bobotie", "chiave": "carne macinata", "firma": ["carne macinata", "curry", "uvetta", "crema all'uovo"]},
    ],
}
