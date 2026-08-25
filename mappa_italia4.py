# mappa_italia4.py
# MAPPA ITALIA — parte 4: copertura più profonda (antipasti, contorni, piatti minori codificati).

REGIONI_4 = {
    "Lazio": [
        {"nome": "Fiori di zucca fritti", "chiave": "fiori di zucca", "firma": ["fiori di zucca", "mozzarella", "acciughe", "pastella"]},
        {"nome": "Gnocchi alla romana", "chiave": "semolino", "firma": ["semolino", "burro", "parmigiano", "tuorli"]},
        {"nome": "Involtini alla romana", "chiave": "manzo", "firma": ["manzo", "prosciutto", "sedano", "pomodoro"]},
        {"nome": "Zuppa di broccoli e arzilla", "chiave": "razza", "firma": ["razza", "broccoli", "pomodoro", "peperoncino"]},
    ],
    "Campania": [
        {"nome": "Scialatielli ai frutti di mare", "chiave": "frutti di mare", "firma": ["scialatielli", "frutti di mare", "pomodorini", "aglio"]},
        {"nome": "Pasta patate e provola", "chiave": "patate", "firma": ["pasta mista", "patate", "provola", "parmigiano"]},
        {"nome": "Pizza fritta", "chiave": "farina", "firma": ["pasta pizza", "ricotta", "cicoli", "provola"], "disc": "panificazione"},
        {"nome": "Insalata di rinforzo", "chiave": "cavolfiore", "firma": ["cavolfiore", "papaccelle", "olive", "acciughe"]},
        {"nome": "Ragù di polpo", "chiave": "polpo", "firma": ["polpo", "pomodoro", "olive", "capperi"]},
    ],
    "Sicilia": [
        {"nome": "Pasta con broccoli arriminati", "chiave": "cavolfiore", "firma": ["pasta", "cavolfiore", "uvetta", "pinoli", "zafferano"]},
        {"nome": "Macco di fave", "chiave": "fave", "firma": ["fave secche", "finocchietto", "olio"]},
        {"nome": "Caponata di carciofi", "chiave": "carciofi", "firma": ["carciofi", "sedano", "olive", "aceto"]},
        {"nome": "Farsumagru", "chiave": "manzo", "firma": ["manzo", "uova", "salame", "formaggio"]},
    ],
    "Puglia": [
        {"nome": "Fave nette con cicoria", "chiave": "fave", "firma": ["fave", "cicoria", "olio"]},
        {"nome": "Cozze arraganate", "chiave": "cozze", "firma": ["cozze", "pangrattato", "prezzemolo", "pomodoro"]},
        {"nome": "Zuppa di pesce gallipolina", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "peperoncino"]},
        {"nome": "Sagne 'ncannulate", "chiave": "pomodoro", "firma": ["pasta arrotolata", "pomodoro", "ricotta"]},
    ],
    "Toscana": [
        {"nome": "Acquacotta", "chiave": "verdure", "firma": ["verdure", "pane", "uovo", "pomodoro"]},
        {"nome": "Lampredotto", "chiave": "trippa", "firma": ["lampredotto", "pane", "salsa verde"]},
        {"nome": "Baccalà alla livornese", "chiave": "baccalà", "firma": ["baccalà", "pomodoro", "aglio", "prezzemolo"]},
        {"nome": "Zuccotto", "chiave": "ricotta", "firma": ["pan di spagna", "ricotta", "cioccolato", "canditi"], "disc": "pasticceria"},
    ],
    "Piemonte": [
        {"nome": "Insalata russa", "chiave": "patate", "firma": ["patate", "carote", "piselli", "maionese"]},
        {"nome": "Carne cruda all'albese", "chiave": "manzo", "firma": ["manzo crudo", "olio", "limone", "aglio"]},
        {"nome": "Brasato di manzo al vino", "chiave": "manzo", "firma": ["manzo", "vino rosso", "aromi"]},
        {"nome": "Torta di nocciole", "chiave": "nocciole", "firma": ["nocciole", "uova", "zucchero", "burro"], "disc": "pasticceria"},
    ],
    "Emilia-Romagna": [
        {"nome": "Cappellacci di zucca", "chiave": "zucca", "firma": ["pasta all'uovo", "zucca", "parmigiano", "noce moscata"]},
        {"nome": "Balanzoni", "chiave": "ricotta", "firma": ["pasta verde", "ricotta", "mortadella"]},
        {"nome": "Coppa di testa", "chiave": "maiale", "firma": ["testa di maiale", "spezie"]},
        {"nome": "Ciambella romagnola", "chiave": "farina", "firma": ["farina", "uova", "burro", "latte"], "disc": "pasticceria"},
    ],
    "Veneto": [
        {"nome": "Risotto di go", "chiave": "riso", "firma": ["riso", "ghiozzo", "brodo di pesce"]},
        {"nome": "Baccalà alla cappuccina", "chiave": "baccalà", "firma": ["baccalà", "uvetta", "pinoli", "cannella"]},
        {"nome": "Sopa coada", "chiave": "piccione", "firma": ["piccione", "pane", "brodo", "parmigiano"]},
        {"nome": "Pinza veneta", "chiave": "farina di mais", "firma": ["farina di mais", "fichi secchi", "uvetta"], "disc": "pasticceria"},
    ],
    "Lombardia": [
        {"nome": "Nervetti in insalata", "chiave": "manzo", "firma": ["nervetti di manzo", "cipolla", "aceto"]},
        {"nome": "Risotto alla pilota", "chiave": "riso", "firma": ["riso", "salamella", "parmigiano"]},
        {"nome": "Michetta", "chiave": "farina", "firma": ["farina", "acqua", "lievito", "malto"], "disc": "panificazione"},
    ],
    "Sardegna": [
        {"nome": "Impanadas", "chiave": "carne", "firma": ["pasta", "carne", "piselli", "pomodoro"]},
        {"nome": "Sa cassola", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "aglio", "peperoncino"]},
        {"nome": "Amaretti sardi", "chiave": "mandorle", "firma": ["mandorle", "albumi", "zucchero"], "disc": "pasticceria"},
    ],
    "Calabria": [
        {"nome": "Morseddu", "chiave": "frattaglie", "firma": ["frattaglie di maiale", "pomodoro", "peperoncino", "pane"]},
        {"nome": "Pipi e patate", "chiave": "peperoni", "firma": ["peperoni", "patate", "cipolla"]},
        {"nome": "Mostaccioli calabresi", "chiave": "miele", "firma": ["farina", "miele", "spezie"], "disc": "pasticceria"},
    ],
    "Abruzzo": [
        {"nome": "Timballo di scrippelle", "chiave": "uova", "firma": ["crespelle", "ragù", "polpettine", "formaggio"]},
        {"nome": "Brodetto vastese", "chiave": "pesce", "firma": ["pesce misto", "pomodoro", "peperoncino", "aglio"]},
        {"nome": "Fiadoni abruzzesi", "chiave": "formaggio", "firma": ["pasta", "formaggio", "uova"], "disc": "pasticceria"},
    ],
    "Marche": [
        {"nome": "Passatelli asciutti", "chiave": "pane", "firma": ["pangrattato", "parmigiano", "uova", "tartufo"]},
        {"nome": "Moscioli in potacchio", "chiave": "cozze", "firma": ["moscioli", "pomodoro", "aglio", "prezzemolo"]},
        {"nome": "Crema fritta", "chiave": "crema", "firma": ["crema pasticcera", "pangrattato", "olio"], "disc": "pasticceria"},
    ],
    "Umbria": [
        {"nome": "Umbricelli al tartufo", "chiave": "tartufo", "firma": ["umbricelli", "tartufo nero", "olio"]},
        {"nome": "Fagiolina del Trasimeno", "chiave": "fagioli", "firma": ["fagiolina", "aglio", "salvia", "olio"]},
        {"nome": "Torcolo di San Costanzo", "chiave": "farina", "firma": ["farina", "uvetta", "canditi", "pinoli"], "disc": "pasticceria"},
    ],
    "Liguria": [
        {"nome": "Minestrone alla genovese col pesto", "chiave": "verdure", "firma": ["verdure", "fagioli", "pesto", "pasta"]},
        {"nome": "Stoccafisso accomodato", "chiave": "stoccafisso", "firma": ["stoccafisso", "patate", "olive", "pinoli"]},
        {"nome": "Baci di Alassio", "chiave": "nocciole", "firma": ["nocciole", "cacao", "cioccolato"], "disc": "pasticceria"},
    ],
}
