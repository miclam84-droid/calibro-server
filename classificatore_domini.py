# classificatore_domini.py
# Assegna la DISCIPLINA (domain) agli ingredienti in base al nome, così ogni disciplina
# (bar, gelateria, pasticceria, panificazione, caffè, cucina) ha la sua materia prima.
# Un ingrediente può appartenere a più domini (il limone è bar E cucina): domini = lista.

# parole-chiave -> disciplina. Ordine: le più specifiche prime.
REGOLE_DOMINIO = {
    "bar": [
        "gin", "rum", "whisky", "whiskey", "vodka", "tequila", "mezcal", "cognac", "brandy",
        "vermouth", "campari", "aperol", "bitter", "maraschino", "curacao", "curaçao", "triple sec",
        "angostura", "chartreuse", "amaretto", "amaro", "grappa", "cachaça", "cachaca", "pisco",
        "liquore", "sciroppo", "soda", "tonica", "tonic", "ginger beer", "ginger ale", "cordial",
        "orgeat", "grenadine", "granatina", "prosecco", "champagne", "spumante", "bitters",
        "lillet", "drambuie", "benedictine", "bénédictine", "galliano", "kahlua", "cointreau",
    ],
    "caffe": [
        "caffè", "caffe", "espresso", "arabica", "robusta", "cold brew", "moka", "chicco",
        "cappuccino", "latte art",
    ],
    "gelateria": [
        "gelato", "sorbetto", "granita", "panna", "latte intero", "destrosio", "saccarosio",
        "neutro", "stabilizzante", "base gelato", "pac", "pod", "glucosio", "latte magro",
        "sciroppo di glucosio", "inulina",
    ],
    "pasticceria": [
        "cioccolato", "cacao", "burro", "zucchero a velo", "gelatina", "vaniglia", "lievito chimico",
        "mascarpone", "ricotta", "mandorle", "nocciole", "pistacchi", "marzapane", "pasta di mandorle",
        "crema", "panna montata", "meringa", "savoiardi", "amaretti", "canditi", "miele", "marmellata",
        "cremor tartaro", "colla di pesce", "fecola", "amido", "albume", "tuorlo", "uova",
    ],
    "panificazione": [
        "farina", "farina 00", "farina 0", "manitoba", "semola", "semola rimacinata", "lievito madre",
        "lievito di birra", "lievito", "grano saraceno", "segale", "malto", "glutine", "crusca",
        "pasta madre", "acqua", "sale", "strutto", "farina integrale", "farina di mais", "farina di riso",
    ],
    "vino": [
        "uva", "mosto", "vino", "tannino", "lieviti", "solforosa", "so2", "acido tartarico", "malico",
        "barrique", "botte",
    ],
    "cucina": [
        # la cucina è il default per la materia prima food: verdure, carni, pesci, spezie
        "pomodoro", "cipolla", "aglio", "carota", "sedano", "peperone", "melanzana", "zucchina",
        "manzo", "vitello", "maiale", "pollo", "agnello", "coniglio", "pesce", "acciughe", "tonno",
        "guanciale", "pancetta", "prosciutto", "salsiccia", "pecorino", "parmigiano", "mozzarella",
        "olio", "basilico", "prezzemolo", "rosmarino", "salvia", "peperoncino", "pepe", "sale grosso",
        "riso", "pasta", "patate", "fagioli", "ceci", "lenticchie", "spinaci", "broccoli", "funghi",
        "brodo", "vino bianco", "aceto", "limone", "arancia", "erbe",
    ],
}


def classifica(nome_ingrediente):
    """Ritorna la lista dei domini a cui appartiene un ingrediente (può essere più di uno).
    Se non matcha nulla, ritorna ['cucina'] come default (è materia prima food generica)."""
    nome = (nome_ingrediente or "").lower()
    domini = []
    for dominio, chiavi in REGOLE_DOMINIO.items():
        for chiave in chiavi:
            if chiave in nome:
                if dominio not in domini:
                    domini.append(dominio)
                break
    if not domini:
        domini = ["cucina"]  # default: materia prima food generica
    return domini
