"""immagini.py — recupero immagini stock con ROUTING multi-fonte (Pexels -> Unsplash -> Pixabay).
Query migliorate: cerca in INGLESE con contesto di disciplina, per evitare foto sbagliate
(es. "Bee's Knees" da solo dava un secchio; ora cerca "cocktail drink" col nome come rinforzo).
Chiavi (opzionali, in ambiente): PEXELS_API_KEY, UNSPLASH_ACCESS_KEY, PIXABAY_API_KEY.
Se una fonte manca la chiave o non trova, si passa alla successiva.
"""
import os, json, urllib.request, urllib.parse

_PEXELS_URL   = "https://api.pexels.com/v1/search"
_UNSPLASH_URL = "https://api.unsplash.com/search/photos"
_PIXABAY_URL  = "https://pixabay.com/api/"

_CTX_DISCIPLINA = {
    "bar":            "cocktail drink glass",
    "caffetteria":    "coffee cup barista",
    "cucina":         "plated food dish gourmet",
    "pasticceria":    "dessert pastry patisserie",
    "panificazione":  "artisan bread bakery",
    "gelateria":      "ice cream gelato",
    "vino":           "wine glass bottle",
    "birra":          "craft beer glass",
}

_KW_IT_EN = {
    "risotto": "risotto rice", "pasta": "pasta", "pizza": "pizza", "pane": "bread",
    "focaccia": "focaccia bread", "gelato": "ice cream", "sorbetto": "sorbet",
    "espresso": "espresso coffee", "cappuccino": "cappuccino", "cornetto": "croissant",
    "tiramisu": "tiramisu dessert", "crema": "cream dessert", "torta": "cake",
    "brioche": "brioche", "cioccolato": "chocolate", "vino": "wine", "birra": "beer",
    "negroni": "negroni cocktail", "spritz": "aperol spritz", "martini": "martini cocktail",
    "sour": "whiskey sour cocktail", "mojito": "mojito cocktail", "margarita": "margarita cocktail",
}

def _query_intelligente(nome, disciplina):
    ctx = _CTX_DISCIPLINA.get((disciplina or "").lower(), "food")
    nome_l = (nome or "").lower()
    extra = ""
    for it, en in _KW_IT_EN.items():
        if it in nome_l:
            extra = " " + en
            break
    return (ctx + extra).strip()

def _norm(url, autore, fonte, fonte_nome):
    if not url:
        return None
    return {"url": url, "autore": autore or "", "fonte": fonte or "", "fonte_nome": fonte_nome}

def _pexels(query, rank=0):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    try:
        params = urllib.parse.urlencode({"query": query, "per_page": 5, "orientation": "landscape"})
        req = urllib.request.Request(f"{_PEXELS_URL}?{params}",
                                     headers={"Authorization": key, "User-Agent": "MatterLab/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        fotos = data.get("photos", [])
        if not fotos:
            return None
        f = fotos[min(rank, len(fotos)-1)]
        return _norm(f.get("src", {}).get("large") or f.get("src", {}).get("medium"),
                     f.get("photographer", ""), f.get("url", ""), "Pexels")
    except Exception:
        return None

def _unsplash(query, rank=0):
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return None
    try:
        params = urllib.parse.urlencode({"query": query, "per_page": 5, "orientation": "landscape"})
        req = urllib.request.Request(f"{_UNSPLASH_URL}?{params}",
                                     headers={"Authorization": f"Client-ID {key}", "User-Agent": "MatterLab/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        res = data.get("results", [])
        if not res:
            return None
        f = res[min(rank, len(res)-1)]
        autore = (f.get("user", {}) or {}).get("name", "")
        return _norm((f.get("urls", {}) or {}).get("regular"),
                     autore, (f.get("links", {}) or {}).get("html", ""), "Unsplash")
    except Exception:
        return None

def _pixabay(query, rank=0):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    try:
        params = urllib.parse.urlencode({"key": key, "q": query, "image_type": "photo",
                                         "orientation": "horizontal", "per_page": 5, "safesearch": "true"})
        req = urllib.request.Request(f"{_PIXABAY_URL}?{params}", headers={"User-Agent": "MatterLab/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        hits = data.get("hits", [])
        if not hits:
            return None
        f = hits[min(rank, len(hits)-1)]
        return _norm(f.get("largeImageURL") or f.get("webformatURL"),
                     f.get("user", ""), f.get("pageURL", ""), "Pixabay")
    except Exception:
        return None

def cerca_immagine(query, lang="it", disciplina=None, nome=None, rank=0):
    """ROUTING: Pexels -> Unsplash -> Pixabay. Se arriva nome+disciplina costruisce la query intelligente."""
    if nome is not None or disciplina is not None:
        q = _query_intelligente(nome or query, disciplina)
    else:
        q = query
    for fonte in (_pexels, _unsplash, _pixabay):
        res = fonte(q, rank)
        if res:
            return res
    return None

def credito_immagine(autore, fonte_nome="Pexels"):
    if autore:
        return f"Foto: {autore} / {fonte_nome}"
    return f"Foto: {fonte_nome}"
