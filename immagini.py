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

def _cloudinary_foto(rank=0, nome_ricetta="", disciplina=""):
    """Restituisce una foto dall'archivio Cloudinary SOLO se c'è un match FORTE sul nome del piatto
    (challah->pane, pizza->pizza). Niente match debole (una parola generica): meglio lo stock per disciplina
    che una foto sbagliata (es. Negroni con marmellata di pomodoro). None se nessun match forte."""
    urls = _cloudinary_lista()
    if not urls or not nome_ricetta:
        return None
    import re as _re
    nome_l = nome_ricetta.lower()
    # parole-piatto FORTI: dal nome (parole lunghe) + traduzione EN della parola-chiave
    parole_ric = set()
    for it, en in _KW_IT_EN.items():
        if it in nome_l:
            parole_ric.update(w for w in en.split() if len(w) > 3)  # solo parole significative
    parole_ric.update(w for w in _re.findall(r'[a-zàèéìòù]+', nome_l) if len(w) > 4)  # nomi propri: challah, tiramisu, focaccia
    # parole generiche che NON devono da sole far scattare un match (troppo comuni)
    _GENERICHE = {"rice", "cream", "fresh", "classic", "classico", "with", "delicious", "homemade", "sauce"}
    parole_ric -= _GENERICHE
    if not parole_ric:
        return None
    # disciplina -> categorie di file ammesse (per non mettere cucina su bar, ecc.)
    _DISC_OK = {
        "bar": ("cocktail", "drink", "negroni", "spritz", "martini", "sour", "mojito", "margarita"),
        "caffetteria": ("coffee", "espresso", "cappuccino", "latte", "barista"),
        "cucina": ("food", "dish", "meat", "fish", "pasta", "risotto", "burger", "sandwich", "salad", "soup", "vegetable", "roast", "stew", "sauce", "tomato", "egg", "taco", "meatball", "chicken"),
        "pasticceria": ("dessert", "cake", "pastry", "chocolate", "tiramisu", "cream", "tart", "sweet"),
        "panificazione": ("bread", "bakery", "challah", "bagel", "baguette", "focaccia", "sourdough", "dough", "pizza", "croissant"),
        "gelateria": ("ice", "gelato", "sorbet", "popsicle", "scoop"),
        "vino": ("wine", "barrel", "cellar"),
        "birra": ("beer", "craft"),
    }
    ok_words = _DISC_OK.get((disciplina or "").lower(), ())
    best, best_score = None, 0
    for u in urls:
        fname = u.split("/")[-1].lower()
        fname_parole = set(_re.findall(r'[a-z]+', fname))
        # match sul nome del piatto
        match_nome = len(parole_ric & fname_parole)
        # la foto è della disciplina giusta?
        disc_ok = any(w in fname for w in ok_words) if ok_words else True
        if match_nome >= 1 and disc_ok:
            score = match_nome * 2 + (1 if disc_ok else 0)
            if score > best_score:
                best, best_score = u, score
    # match valido SOLO se nome forte + disciplina compatibile
    if best and best_score >= 3:
        return {"url": best, "autore": "", "fonte": best, "fonte_nome": "archivio"}
    return None


_PEXELS_URL   = "https://api.pexels.com/v1/search"
_UNSPLASH_URL = "https://api.unsplash.com/search/photos"
_PIXABAY_URL  = "https://pixabay.com/api/"

_CTX_DISCIPLINA = {
    "bar":            "cocktail drink glass",
    "caffetteria":    "coffee cup barista",
    "cucina":         "plated food dish gourmet appetizing served",
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
    "tacos": "tacos mexican food plated", "taco": "tacos mexican food plated",
    "tortilla": "corn tortillas mexican", "tamale": "tamales mexican food",
    "pozole": "pozole mexican soup", "mole": "mole mexican dish", "guacamole": "guacamole bowl",
    "ceviche": "ceviche seafood plated", "carnitas": "carnitas mexican tacos",
    "ramen": "ramen bowl japanese", "sushi": "sushi plated japanese", "miso": "miso soup japanese",
    "dashi": "japanese broth bowl", "katsu": "katsu japanese fried", "teriyaki": "teriyaki chicken plated",
    "tempura": "tempura japanese fried", "mochi": "mochi dessert japanese", "chawanmushi": "japanese custard",
    "kimchi": "kimchi korean side dish", "bibimbap": "bibimbap korean bowl", "bulgogi": "bulgogi korean beef",
    "japchae": "japchae korean noodles", "tteokbokki": "tteokbokki korean", "korean fried chicken": "korean fried chicken plated",
    "brisket": "sliced brisket barbecue plated", "pulled pork": "pulled pork sandwich",
    "costine": "barbecue ribs plated", "burger": "gourmet burger plated", "cheesecake": "cheesecake slice dessert",
    "tikka": "chicken tikka masala plated", "butter chicken": "butter chicken indian plated",
    "biryani": "biryani rice indian plated", "paneer": "paneer indian dish", "dosa": "dosa indian plated",
    "naan": "naan bread indian", "dal": "dal indian lentil bowl", "curry": "curry dish plated",
    "wok": "stir fry wok vegetables", "mapo": "mapo tofu plated", "kung pao": "kung pao chicken plated",
    "jiaozi": "dumplings chinese plated", "xiao long bao": "soup dumplings chinese", "char siu": "char siu pork",
    "bao": "bao buns steamed", "pad thai": "pad thai noodles plated", "tom yum": "tom yum soup thai",
    "green curry": "thai green curry", "pho": "pho vietnamese soup bowl", "banh mi": "banh mi sandwich",
    "satay": "chicken satay skewers", "hummus": "hummus bowl", "falafel": "falafel plated",
    "shawarma": "shawarma plated", "tabbouleh": "tabbouleh salad", "tagine": "moroccan tagine",
    "couscous": "couscous plated", "baklava": "baklava dessert", "labneh": "labneh bowl",
    "coq au vin": "coq au vin plated", "bourguignon": "beef bourguignon plated", "confit": "duck confit plated",
    "creme brulee": "creme brulee dessert", "souffle": "souffle plated", "hollandaise": "hollandaise sauce",
    "bouillabaisse": "bouillabaisse seafood soup", "bibimbap": "bibimbap korean bowl",
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
    # NUOVO: cerco prima il NOME DEL PIATTO (pulito), non solo la categoria generica.
    # Era il motivo delle "foto inquietanti": query tipo "food" o "cooking hands"
    # tornano risultati a caso. "gricia" -> "gricia pasta" torna foto pertinenti.
    nome_pulito = _nome_per_query(nome_l)
    extra = ""
    for it, en in _KW_IT_EN.items():
        if it in nome_l:
            extra = " " + en
            break
    # priorità: nome del piatto + eventuale keyword + un aggancio di categoria breve
    if nome_pulito:
        # aggancio breve alla categoria (es. "italian food", "cocktail") per restare in tema
        aggancio = ctx.split()[0] if ctx else "food"
        return f"{nome_pulito}{extra} {aggancio}".strip()
    return (ctx + extra).strip()


def _nome_per_query(nome_l):
    """Pulisce il nome del piatto per la ricerca immagini: toglie parole di rumore
    (rivisitato, base, scientifico, con, e, di...) e tiene le parole distintive."""
    if not nome_l:
        return ""
    rumore = {"rivisitato", "rivisitata", "base", "scientifico", "scientifica", "con", "e", "di",
              "al", "alla", "allo", "ai", "il", "la", "lo", "un", "una", "del", "della", "in",
              "per", "da", "the", "of", "with", "and", "bilanciamento", "versione"}
    parole = [w for w in nome_l.replace("(", " ").replace(")", " ").replace(",", " ").split()
              if w not in rumore and len(w) >= 3]
    return " ".join(parole[:3])  # max 3 parole distintive

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

def cerca_immagine(query, lang="it", disciplina=None, nome=None, rank=0, ingredienti=None):
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
    # 1) CLOUDINARY col MATCH PER NOME: se una foto dell'archivio corrisponde al piatto
    #    (challah->pane, cheeseburger->panino), quella è la migliore. Se nessun match, torna None.
    cloud = _cloudinary_foto(rank_nome, nome_ricetta=(nome or query or ""), disciplina=(disciplina or ""))
    if cloud:
        cloud["match"] = "archivio"
        return cloud
    # 2) NOME DEL PIATTO ESATTO: cerco il piatto specifico (gricia, non 'pasta qualsiasi').
    nome_pulito = _nome_per_query((nome or query or "").lower())
    if nome_pulito:
        for fonte in (_pexels, _unsplash, _pixabay):
            res = fonte(nome_pulito, rank)
            if res:
                res["match"] = "piatto"   # match forte: cercato il nome del piatto
                return res
    # 3) INGREDIENTI PRINCIPALI: se il piatto esatto non c'è, meglio gli INGREDIENTI
    #    (guanciale pecorino) che una foto di un altro piatto. Passati da chi chiama.
    if ingredienti:
        ing_query = " ".join(str(i).lower() for i in ingredienti[:2] if i)
        if ing_query.strip():
            for fonte in (_pexels, _unsplash, _pixabay):
                res = fonte(ing_query, rank)
                if res:
                    res["match"] = "ingredienti"  # match debole: foto degli ingredienti
                    return res
    # 4) NIENTE foto sbagliata: se non trovo il piatto né gli ingredienti, torno None
    #    (il frontend mostra un placeholder pulito, meglio che una foto errata).
    return None

def credito_immagine(autore, fonte_nome="Pexels"):
    if autore:
        return f"Foto: {autore} / {fonte_nome}"
    return f"Foto: {fonte_nome}"
