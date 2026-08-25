# mappa_italia5.py
# MAPPA ITALIA — parte 5: ultimo strato di piatti regionali codificati (primi, secondi, dolci, street food).

REGIONI_5 = {
    "Lazio": [
        {"nome": "Spaghetti alla checca", "chiave": "pomodoro", "firma": ["spaghetti", "pomodorini crudi", "mozzarella", "basilico"]},
        {"nome": "Coda di rospo in guazzetto", "chiave": "rana pescatrice", "firma": ["rana pescatrice", "pomodorini", "vino", "prezzemolo"]},
        {"nome": "Frittata di carciofi", "chiave": "carciofi", "firma": ["carciofi", "uova", "pecorino"]},
        {"nome": "Ciambelline al vino", "chiave": "vino", "firma": ["farina", "vino", "olio", "anice"], "disc": "pasticceria"},
    ],
    "Campania": [
        {"nome": "Genovese di tonno", "chiave": "tonno", "firma": ["cipolle", "tonno fresco", "pasta"]},
        {"nome": "Zuppa di cozze pasquale", "chiave": "cozze", "firma": ["cozze", "polpo", "pomodoro", "peperoncino"]},
        {"nome": "Parmigiana di zucchine", "chiave": "zucchine", "firma": ["zucchine", "pomodoro", "provola", "basilico"]},
        {"nome": "Roccocò", "chiave": "mandorle", "firma": ["farina", "mandorle", "pisto (spezie)", "canditi"], "disc": "pasticceria"},
        {"nome": "Susamielli", "chiave": "miele", "firma": ["farina", "miele", "mandorle", "spezie"], "disc": "pasticceria"},
    ],
    "Sicilia": [
        {"nome": "Spaghetti ai ricci di mare", "chiave": "ricci", "firma": ["spaghetti", "ricci di mare", "aglio", "olio"]},
        {"nome": "Pasta alla trapanese", "chiave": "mandorle", "firma": ["pasta", "pomodoro", "mandorle", "basilico", "aglio"]},
        {"nome": "Coniglio all'agrodolce", "chiave": "coniglio", "firma": ["coniglio", "aceto", "zucchero", "olive", "capperi"]},
        {"nome": "Buccellato", "chiave": "fichi", "firma": ["pasta frolla", "fichi secchi", "mandorle", "canditi"], "disc": "pasticceria"},
    ],
    "Puglia": [
        {"nome": "Spaghetti all'assassina", "chiave": "pomodoro", "firma": ["spaghetti", "pomodoro", "peperoncino", "aglio"]},
        {"nome": "Agnello con lampascioni", "chiave": "agnello", "firma": ["agnello", "lampascioni", "vino"]},
        {"nome": "Rustico leccese", "chiave": "farina", "firma": ["pasta sfoglia", "besciamella", "mozzarella", "pomodoro"], "disc": "panificazione"},
        {"nome": "Spumone pugliese", "chiave": "gelato", "firma": ["gelato", "pan di spagna", "liquore"], "disc": "gelateria"},
    ],
    "Toscana": [
        {"nome": "Garmugia lucchese", "chiave": "verdure", "firma": ["carciofi", "fave", "piselli", "asparagi", "carne"]},
        {"nome": "Cinghiale in umido", "chiave": "cinghiale", "firma": ["cinghiale", "vino rosso", "pomodoro", "olive"]},
        {"nome": "Cacciucco alla livornese", "chiave": "pesce", "firma": ["pesce misto", "molluschi", "vino", "peperoncino"]},
        {"nome": "Panforte di Siena", "chiave": "frutta secca", "firma": ["mandorle", "canditi", "miele", "spezie"], "disc": "pasticceria"},
    ],
    "Piemonte": [
        {"nome": "Agnolotti al plin di coniglio", "chiave": "coniglio", "firma": ["pasta", "coniglio", "verza"]},
        {"nome": "Lepre in civet", "chiave": "lepre", "firma": ["lepre", "vino rosso", "spezie", "sangue"]},
        {"nome": "Bagna cauda con verdure", "chiave": "acciughe", "firma": ["acciughe", "aglio", "olio", "verdure crude"]},
        {"nome": "Krumiri", "chiave": "farina", "firma": ["farina", "burro", "uova", "vaniglia"], "disc": "pasticceria"},
    ],
    "Emilia-Romagna": [
        {"nome": "Tortelli di erbette", "chiave": "bietole", "firma": ["pasta all'uovo", "bietole", "ricotta", "parmigiano"]},
        {"nome": "Anolini in brodo", "chiave": "carne", "firma": ["pasta all'uovo", "stracotto", "brodo"]},
        {"nome": "Culatello con lo gnocco", "chiave": "maiale", "firma": ["culatello", "gnocco fritto"]},
        {"nome": "Pinza bolognese", "chiave": "farina", "firma": ["pasta", "mostarda", "marmellata"], "disc": "pasticceria"},
    ],
    "Veneto": [
        {"nome": "Risi e bisi", "chiave": "riso", "firma": ["riso", "piselli", "pancetta", "brodo"]},
        {"nome": "Anatra col pien", "chiave": "anatra", "firma": ["anatra", "ripieno di pane", "fegatini"]},
        {"nome": "Castradina", "chiave": "montone", "firma": ["montone affumicato", "verza", "vino"]},
        {"nome": "Baicoli", "chiave": "farina", "firma": ["farina", "burro", "lievito"], "disc": "pasticceria"},
    ],
    "Lombardia": [
        {"nome": "Pizzoccheri della Valtellina", "chiave": "grano saraceno", "firma": ["grano saraceno", "verze", "patate", "bitto", "burro"]},
        {"nome": "Risotto ai funghi porcini", "chiave": "funghi", "firma": ["riso", "porcini", "brodo", "parmigiano"]},
        {"nome": "Trippa alla milanese (busecca)", "chiave": "trippa", "firma": ["trippa", "fagioli", "verdure"]},
        {"nome": "Offella di Parona", "chiave": "farina", "firma": ["farina", "burro", "uova"], "disc": "pasticceria"},
    ],
    "Sardegna": [
        {"nome": "Culurgiones ogliastrini", "chiave": "patate", "firma": ["pasta", "patate", "pecorino", "menta"]},
        {"nome": "Sa merca", "chiave": "muggine", "firma": ["muggine", "erba obione", "salamoia"]},
        {"nome": "Zuppa cuata gallurese", "chiave": "pane", "firma": ["pane", "formaggio fresco", "brodo di pecora"]},
        {"nome": "Gueffus", "chiave": "mandorle", "firma": ["mandorle", "zucchero", "acqua di fiori d'arancio"], "disc": "pasticceria"},
    ],
    "Calabria": [
        {"nome": "Maccheroni al ferretto con ragù", "chiave": "carne", "firma": ["maccheroni", "ragù di maiale", "pecorino"]},
        {"nome": "Alici arraganate", "chiave": "acciughe", "firma": ["alici", "pangrattato", "origano", "aglio"]},
        {"nome": "Licurdia", "chiave": "cipolla", "firma": ["cipolle di tropea", "patate", "peperoncino", "pane"]},
    ],
    "Basilicata": [
        {"nome": "Pignata di pecora", "chiave": "pecora", "firma": ["pecora", "patate", "sedano", "pomodoro"]},
        {"nome": "Baccalà con peperoni cruschi", "chiave": "baccalà", "firma": ["baccalà", "peperoni cruschi", "aglio"]},
        {"nome": "Cialledda", "chiave": "pane", "firma": ["pane raffermo", "pomodoro", "cipolla", "olio"]},
    ],
    "Abruzzo": [
        {"nome": "Chitarra con pallottine", "chiave": "carne", "firma": ["pasta alla chitarra", "polpettine", "pomodoro"]},
        {"nome": "Ndocca ndocca", "chiave": "maiale", "firma": ["parti di maiale", "peperoncino", "aceto", "aglio"]},
        {"nome": "Confetti di Sulmona", "chiave": "mandorle", "firma": ["mandorle", "zucchero"], "disc": "pasticceria"},
    ],
}
