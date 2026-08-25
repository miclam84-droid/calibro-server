# risolutore_immagini.py
# SISTEMA IMMAGINI A CASCATA (idea di Michele):
# 1) foto del PIATTO se esiste su Cloudinary (match sicuro per nome)
# 2) foto dell'INGREDIENTE PRINCIPALE come fallback (bagna cauda -> aglio) — onesta, mai "sbagliata"
# 3) niente foto (placeholder pulito) se non c'è nulla di sicuro
#
# REGOLA FERMA: meglio la foto dell'ingrediente giusto che una foto-piatto sbagliata.
# Una foto di aglio per la bagna cauda NON è un errore: è l'ingrediente-firma, ed è onesta.

import re
import unicodedata

CLOUD = "ddciz5th"


def _slug(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _url(nome_file):
    return f"https://res.cloudinary.com/{CLOUD}/image/upload/{nome_file}"


# ── MAPPA INGREDIENTE-CHIAVE → foto ingrediente disponibile su Cloudinary ──
# Sicura: è la foto di quell'ingrediente, non può essere "sbagliata".
FOTO_INGREDIENTE = {
    "aglio": "curious_collectibles-garlic-8214036_1920.jpg",
    "garlic": "curious_collectibles-garlic-8214036_1920.jpg",
    "acciughe": "curious_collectibles-garlic-8214036_1920.jpg",  # bagna cauda: aglio+acciughe, aglio ok
    "zenzero": "webtechexperts-ginger-5108742_1920.jpg",
    "ginger": "webtechexperts-ginger-5108742_1920.jpg",
    "broccoli": "shutterbug26-broccoli-1238250_1920.jpg",
    "cavolo": "shutterbug26-broccoli-1238250_1920.jpg",
    "pepe nero": "couleur-peppercorns-3061240_1920.jpg",
    "pepe": "couleur-peppercorns-3061240_1920.jpg",
    "peperoni": "jacques2017-stuffed-pepper-2255998_1920.jpg",
    "verdure": "stevepb-soup-greens-869075_1920.jpg",
    "erbe": "ka_re-herb-4680551_1920.jpg",
    "anice stellato": "daria-yakovleva-star-anise-1887231_1920.jpg",
}


def risolvi_immagine(nome_piatto, ingrediente_chiave, foto_cloudinary_piatto=None, lista_file_cloudinary=None):
    """Risolve l'immagine di una ricetta a cascata.
    Ritorna {url, tipo, autore} dove tipo = 'piatto' | 'ingrediente' | None.
    - foto_cloudinary_piatto: se il DB ha già una foto-piatto verificata per questo id, ha priorità.
    - lista_file_cloudinary: elenco file su Cloudinary per il match del nome piatto.
    """
    # 1) foto del piatto già assegnata nel DB (curata da Michele, match per id) — massima priorità
    if foto_cloudinary_piatto:
        return {"url": foto_cloudinary_piatto, "tipo": "piatto", "autore": "Michele Lamagna"}

    # 2) match del nome piatto tra i file foodiesfeed su Cloudinary
    if lista_file_cloudinary:
        slug_piatto = _slug(nome_piatto)
        parole = [w for w in slug_piatto.split("-") if len(w) >= 4]
        for f in lista_file_cloudinary:
            fl = f.lower()
            # match forte: una parola distintiva del piatto è nel nome file
            for w in parole:
                if w in fl:
                    return {"url": _url(f), "tipo": "piatto", "autore": "foodiesfeed"}

    # 3) FALLBACK: foto dell'ingrediente principale (mai sbagliata)
    chiave = (ingrediente_chiave or "").lower().strip()
    if chiave in FOTO_INGREDIENTE:
        return {"url": _url(FOTO_INGREDIENTE[chiave]), "tipo": "ingrediente", "autore": "ingrediente principale"}

    # 4) niente foto sicura -> placeholder (il frontend mostra il placeholder pulito)
    return {"url": None, "tipo": None, "autore": None}
