# affiliati_libri.py - link affiliati Amazon ai libri scientifici di riferimento.
# Monetizzazione accessoria: ogni disciplina/fenomeno rimanda al libro autorevole.
# IMPORTANTE: sostituisci AMAZON_TAG col tuo tag Associates reale (es. "matterbench-21").

import os
AMAZON_TAG = os.environ.get("AMAZON_ASSOC_TAG", "matterbench-21")  # da configurare su Railway

def _link(asin):
    """Costruisce il link affiliato Amazon.it da un ASIN."""
    return f"https://www.amazon.it/dp/{asin}?tag={AMAZON_TAG}"

# I libri di riferimento per disciplina (ASIN = codice prodotto Amazon).
# NOTA: gli ASIN vanno verificati/aggiornati con le edizioni italiane reali disponibili.
LIBRI = {
    "panificazione": {
        "titolo": "Il pane. Tecniche e ricette (Hamelman)",
        "autore": "Jeffrey Hamelman",
        "asin": "8858014707",  # placeholder - verificare ASIN reale IT
        "perche": "Il riferimento tecnico per la panificazione professionale.",
    },
    "pasticceria": {
        "titolo": "La scienza della pasticceria",
        "autore": "Dario Bressanini",
        "asin": "8858018745",
        "perche": "La chimica della pasticceria spiegata con rigore.",
    },
    "cucina": {
        "titolo": "Il cibo e la cucina (McGee)",
        "autore": "Harold McGee",
        "asin": "8865207981",
        "perche": "La bibbia della scienza in cucina.",
    },
    "bar": {
        "titolo": "Liquid Intelligence (Dave Arnold)",
        "autore": "Dave Arnold",
        "asin": "0393089037",
        "perche": "La scienza e la tecnica della miscelazione d'avanguardia.",
    },
    "gelateria": {
        "titolo": "La scienza del gelato",
        "autore": "Dario Bressanini",
        "asin": "8858021517",
        "perche": "Bilanciamento e struttura del gelato, spiegati.",
    },
    "caffetteria": {
        "titolo": "The World Atlas of Coffee (Hoffmann)",
        "autore": "James Hoffmann",
        "asin": "1784724297",
        "perche": "Estrazione, tostatura e origine del caffè specialty.",
    },
}

# mappa alcune parole-chiave dei fenomeni alla disciplina (per suggerire il libro giusto)
_KEYWORD_DISC = {
    "lievit": "panificazione", "glutine": "panificazione", "impasto": "panificazione",
    "maillard": "cucina", "coagul": "cucina", "emulsion": "cucina", "brasatura": "cucina",
    "caramell": "pasticceria", "temperagg": "pasticceria", "meringa": "pasticceria",
    "diluizion": "bar", "shakerato": "bar", "distill": "bar",
    "pac": "gelateria", "overrun": "gelateria",
    "estrazion": "caffetteria", "tostatura": "caffetteria",
}

def libro_per_disciplina(disciplina):
    """Ritorna il libro di riferimento per una disciplina, col link affiliato."""
    d = (disciplina or "").lower()
    libro = LIBRI.get(d)
    if not libro:
        return None
    return {
        "titolo": libro["titolo"],
        "autore": libro["autore"],
        "perche": libro["perche"],
        "link": _link(libro["asin"]),
    }

def libro_per_fenomeno(nome_fenomeno, disciplina=None):
    """Suggerisce il libro giusto per un fenomeno (dalla disciplina o dalle keyword)."""
    if disciplina:
        l = libro_per_disciplina(disciplina)
        if l: return l
    nome = (nome_fenomeno or "").lower()
    for kw, disc in _KEYWORD_DISC.items():
        if kw in nome:
            return libro_per_disciplina(disc)
    return libro_per_disciplina("cucina")  # fallback: McGee, il più generale
