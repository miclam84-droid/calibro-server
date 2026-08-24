"""immagini.py — recupero immagini stock con ROUTING multi-fonte (Pexels -> Unsplash -> Pixabay).
Query migliorate: cerca in INGLESE con contesto di disciplina, per evitare foto sbagliate
(es. "Bee's Knees" da solo dava un secchio; ora cerca "cocktail drink" col nome come rinforzo).
Chiavi (opzionali, in ambiente): PEXELS_API_KEY, UNSPLASH_ACCESS_KEY, PIXABAY_API_KEY.
Se una fonte manca la chiave o non trova, si passa alla successiva.
"""
import os, json, urllib.request, urllib.parse
import base64

# ── CLOUDINARY: l'archivio foto di Michele (fonte PRIORITARIA, prima dello stock) ──
# Elenca le foto caricate e ne pesca una a rotazione. Serve CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET.
_CLOUD_CACHE = {"urls": [], "ts": 0}

def _cloudinary_lista():
    """Elenca (con cache 10 min) gli URL delle foto nell'archivio Cloudinary di Michele."""
    import time
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME")
    key = os.environ.get("CLOUDINARY_API_KEY")
    secret = os.environ.get("CLOUDINARY_API_SECRET")
    if not (cloud and key and secret):
        return []
    # cache: non richiamare l'API a ogni foto
    if _CLOUD_CACHE["urls"] and (time.time() - _CLOUD_CACHE["ts"] < 600):
        return _CLOUD_CACHE["urls"]
    try:
        # Admin API: lista risorse immagini (max 500)
        url = f"https://api.cloudinary.com/v1_1/{cloud}/resources/image?max_results=500"
        auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        # SAMPLE di Cloudinary da IGNORARE (immagini demo che l'account ha di default)
        _SAMPLE = ("sample", "shoes", "ecommerce", "accessories-bag", "leather-bag-gray",
                   "logo", "cld-sample", "couple", "balloons", "coffee_cup", "dog", "cat")
        urls = []
        for res in data.get("resources", []):
            u = res.get("secure_url")
            pid = (res.get("public_id") or "").lower()
            if not u:
                continue
            # scarta i sample di sistema; tieni le foto vere (foodiesfeed e altre caricate da Michele)
            if any(s in pid for s in _SAMPLE):
                continue
            urls.append(u)
        _CLOUD_CACHE["urls"] = urls
        _CLOUD_CACHE["ts"] = time.time()
        return urls
    except Exception:
        return []

def _cloudinary_foto(rank=0):
    """Restituisce una foto dall'archivio Cloudinary (a rotazione via rank). None se archivio vuoto."""
    urls = _cloudinary_lista()
    if not urls:
        return None
    u = urls[rank % len(urls)]
    return {"url": u, "autore": "", "fonte": u, "fonte_nome": "archivio"}


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


# ── preparazioni BASE: per salse madri/fondi/creme la foto del piatto finito non serve.
# Meglio la visuale di CHI PREPARA (mani, pentolino, emulsione) o l'ingrediente chiave. ──
_PAROLE_BASE = ("salsa madre", "salsa", "fondo", "besciamella", "bagna", "brodo",
                "maionese", "emulsione", "ganache", "crema pasticcera", "crema pasticcera classica",
                "sciroppo", "riduzione", "fumetto", "roux", "court", "pastissier", "pâtissière")

_CTX_PREPARAZIONE = {
    "cucina":        "cooking sauce pan kitchen hands process",
    "pasticceria":   "whisking cream bowl pastry kitchen hands",
    "bar":           "bartender making cocktail syrup pouring",
    "caffetteria":   "barista pouring espresso process",
    "gelateria":     "making ice cream churning process",
    "panificazione": "kneading dough hands bakery process",
    "vino":          "wine making barrel cellar process",
}

def _e_preparazione_base(nome):
    n = (nome or "").lower()
    return any(k in n for k in _PAROLE_BASE)

def _query_intelligente(nome, disciplina):
    disc = (disciplina or "").lower()
    nome_l = (nome or "").lower()
    # preparazione base -> visuale di chi prepara (non il piatto finito)
    if _e_preparazione_base(nome):
        ctx = _CTX_PREPARAZIONE.get(disc, "cooking process hands kitchen")
        return ctx
    ctx = _CTX_DISCIPLINA.get(disc, "food")
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
    """ROUTING: Pexels -> Unsplash -> Pixabay. Se arriva nome+disciplina costruisce la query intelligente.
    Se rank non è forzato (0) e c'è un nome, deriva un rank dal NOME: cosi ricette diverse con la stessa
    query (es. besciamella e bagna cauda, entrambe 'cooking sauce pan') prendono foto DIVERSE, non la stessa."""
    if nome is not None or disciplina is not None:
        q = _query_intelligente(nome or query, disciplina)
    else:
        q = query
    # rank automatico dal nome (stabile): due nomi diversi pescano foto diverse
    rank_nome = sum(ord(c) for c in (nome or query)) if (nome or query) else 0
    if rank == 0 and nome:
        rank = rank_nome % 5
    # 1) STOCK per disciplina (foto PERTINENTI: cocktail per i cocktail, pane per il pane).
    #    E' la fonte primaria perche' copre tutte le ricette con foto sensate.
    for fonte in (_pexels, _unsplash, _pixabay):
        res = fonte(q, rank)
        if res:
            return res
    # 2) Cloudinary (archivio di Michele) SOLO come fallback: utile quando avra' molte foto
    #    taggate per disciplina. Con poche foto generiche darebbe la stessa foto ovunque, quindi
    #    resta in coda, non in testa.
    cloud = _cloudinary_foto(rank_nome)
    if cloud:
        return cloud
    return None

def credito_immagine(autore, fonte_nome="Pexels"):
    if autore:
        return f"Foto: {autore} / {fonte_nome}"
    return f"Foto: {fonte_nome}"
