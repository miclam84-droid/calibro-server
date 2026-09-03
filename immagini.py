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
    # ── CUCINA ITALIANA (il target di Matter) — query inglese efficace piatto+ingredienti ──
    "ossobuco": "braised veal shank ossobuco plated", "bagna cauda": "garlic anchovy dip raw vegetables",
    "vitello tonnato": "veal with tuna sauce sliced plated", "baccala": "creamed salt cod dish plated",
    "baccalà": "creamed salt cod dish plated", "caponata": "sicilian eggplant caponata bowl",
    "panzanella": "panzanella bread tomato salad", "parmigiana": "eggplant parmigiana baked plated",
    "melanzane": "eggplant dish plated", "amatriciana": "spaghetti amatriciana tomato bacon",
    "carbonara": "spaghetti carbonara egg guanciale", "cacio e pepe": "cacio e pepe pasta cheese pepper",
    "gricia": "pasta gricia guanciale pecorino", "arrabbiata": "penne arrabbiata tomato",
    "puttanesca": "spaghetti puttanesca olives capers", "ragu": "pasta ragu bolognese meat sauce",
    "bolognese": "tagliatelle bolognese meat sauce", "lasagne": "lasagna baked layers plated",
    "gnocchi": "potato gnocchi plated", "tortellini": "tortellini pasta broth", "ravioli": "ravioli pasta plated",
    "risotto milanese": "saffron risotto milanese yellow", "risotto": "creamy risotto plated",
    "minestrone": "minestrone vegetable soup bowl", "ribollita": "tuscan ribollita bread soup",
    "acqua pazza": "fish in tomato broth plated", "cacciucco": "cacciucco seafood tomato stew",
    "brasato": "braised beef wine plated", "bollito": "boiled meat mixed plated", "arrosto": "roast meat sliced plated",
    "saltimbocca": "saltimbocca veal ham sage", "scaloppine": "veal scaloppine plated",
    "polpette": "meatballs tomato sauce plated", "involtini": "meat rolls involtini plated",
    "caprese": "caprese tomato mozzarella basil", "bruschetta": "bruschetta tomato bread",
    "burrata": "burrata cheese plated", "prosciutto": "prosciutto ham plate", "salumi": "cured meats board",
    "frittata": "frittata italian omelette", "carciofi": "artichoke dish plated", "friarielli": "broccoli rabe sauteed",
    "pesto": "pesto pasta green basil", "genovese": "pasta genovese onion sauce",
    "orata": "sea bream fish plated", "branzino": "sea bass fish plated", "polpo": "octopus dish plated",
    "cozze": "mussels bowl plated", "vongole": "spaghetti clams vongole", "fritto misto": "mixed fried seafood",
    "cannoli": "sicilian cannoli dessert", "cannolo": "sicilian cannolo dessert", "cassata": "sicilian cassata cake",
    "panna cotta": "panna cotta dessert plated", "zabaione": "zabaglione cream dessert",
    "sfogliatella": "sfogliatella pastry", "babà": "baba rum dessert", "baba": "baba rum dessert",
    "pastiera": "neapolitan pastiera tart", "cantucci": "cantucci almond biscotti", "amaretti": "amaretti cookies",
    "polenta": "polenta plated", "arancini": "sicilian arancini rice balls", "supplì": "suppli rice croquette",
    "porchetta": "porchetta roast pork sliced", "nduja": "nduja spicy spread", "mortadella": "mortadella slices",
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


_BLACKLIST_FOTO = {"wallpaper", "sfondo", "background", "texture", "growing", "raw meat",
                   "raw beef", "uncooked", "landscape", "paesaggio", "abstract", "astratto",
                   "carne cruda", "field", "campo", "farm", "fattoria", "bottle", "bottiglia",
                   "still life", "market", "mercato", "grocery", "supermarket"}

def _foto_pertinente(testo_foto, query):
    """La foto e' GIUSTA per il piatto? La query ora e' precisa (piatto+ingredienti in inglese).
    Regole: (1) mai mismatch palese (carne cruda, sfondi); (2) almeno una parola SPECIFICA della
    query (>=4 lettere, non generica) dev'essere nella descrizione della foto. Se la foto non ha
    descrizione, la accetto con cautela (le banche foto di cibo di solito sono a tema)."""
    t = (testo_foto or "").lower()
    for bad in _BLACKLIST_FOTO:
        if bad in t:
            return False
    if not t:
        return None  # niente descrizione: accetto (banca foto di cibo)
    _GEN = {"food", "dish", "plated", "meal", "italian", "fresh", "homemade", "delicious",
            "cuisine", "plate", "bowl", "cooking", "kitchen", "table", "restaurant"}
    parole = [p for p in query.lower().split() if len(p) >= 4 and p not in _GEN]
    if not parole:
        return None
    # almeno una parola specifica della query nella descrizione della foto
    if any(p in t for p in parole):
        return True
    return False  # la foto non contiene nessun ingrediente/nome del piatto -> scarto

def _pexels(query, rank=0, no_filtro=False):
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
        # scorro dal rank in poi, prendo la prima PERTINENTE (alt = descrizione foto)
        ordine = fotos[rank:] + fotos[:rank]
        for f in ordine:
            alt = f.get("alt", "")
            pert = _foto_pertinente(alt, query)
            if not no_filtro and pert is False:
                continue  # mismatch certo, scarto
            return _norm(f.get("src", {}).get("large") or f.get("src", {}).get("medium"),
                         f.get("photographer", ""), f.get("url", ""), "Pexels")
        return None
    except Exception:
        return None

def _unsplash(query, rank=0, no_filtro=False):
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
        ordine = res[rank:] + res[:rank]
        for f in ordine:
            alt = (f.get("alt_description") or "") + " " + " ".join(
                (t.get("title","") if isinstance(t,dict) else str(t)) for t in (f.get("tags") or []))
            if not no_filtro and _foto_pertinente(alt, query) is False:
                continue
            autore = (f.get("user", {}) or {}).get("name", "")
            return _norm((f.get("urls", {}) or {}).get("regular"),
                         autore, (f.get("links", {}) or {}).get("html", ""), "Unsplash")
        return None
    except Exception:
        return None

def _pixabay(query, rank=0, no_filtro=False):
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
        ordine = hits[rank:] + hits[:rank]
        for f in ordine:
            if not no_filtro and _foto_pertinente(f.get("tags", ""), query) is False:
                continue
            return _norm(f.get("largeImageURL") or f.get("webformatURL"),
                         f.get("user", ""), f.get("pageURL", ""), "Pixabay")
        return None
    except Exception:
        return None


def _wikimedia(query, rank=0, no_filtro=False):
    """Wikimedia Commons: enorme, ha i piatti tradizionali/italiani che Pexels/Pixabay non hanno
    (Bourride, cocktail classici, piatti regionali). Aperto, serve solo uno User-Agent identificativo."""
    try:
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 8,
            "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 900})
        req = urllib.request.Request(
            f"https://commons.wikimedia.org/w/api.php?{params}",
            headers={"User-Agent": "MatterBench/1.0 (https://matterbench.app; info@matterbench.app)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None
        items = sorted(pages.values(), key=lambda x: x.get("index", 99))
        ordine = items[rank:] + items[:rank]
        for pg in ordine:
            ii = (pg.get("imageinfo") or [{}])[0]
            url = ii.get("thumburl") or ii.get("url")
            titolo = pg.get("title", "").replace("File:", "")
            # scarto SVG/loghi/mappe (non sono foto di cibo)
            if not url or any(bad in url.lower() for bad in (".svg", ".pdf", "logo", "icon", "map", "diagram")):
                continue
            # FILTRO LICENZA (uso commerciale sicuro): SOLO Pubblico Dominio, CC0, CC BY.
            # Escludo CC BY-SA (share-alike problematico) e NC (non-commerciale, vietato).
            _ext = ii.get("extmetadata", {})
            _lic = (_ext.get("License", {}).get("value", "") or "").lower()
            _lic_short = (_ext.get("LicenseShortName", {}).get("value", "") or "").lower()
            _lic_all = _lic + " " + _lic_short
            _sicura = (
                ("cc0" in _lic_all) or ("public domain" in _lic_all) or ("pd" == _lic.strip())
                or ("cc-by-4" in _lic) or ("cc-by-3" in _lic) or ("cc-by-2" in _lic)
                or ("cc-by-1" in _lic) or (_lic in ("cc-by", "cc-by-sa") and False)
            )
            # esclusione esplicita: mai NC né SA
            if "-sa" in _lic or "-nc" in _lic or "nc" in _lic_short or "share" in _lic_all:
                continue
            if not _sicura:
                continue
            if not no_filtro and _foto_pertinente(titolo, query) is False:
                continue
            _autore = ""
            try:
                import re as _re
                _raw_aut = _ext.get("Artist", {}).get("value", "")
                # tolgo tutti i tag HTML e prendo solo il testo dell'autore
                _autore = _re.sub(r"<[^>]+>", "", _raw_aut).strip()
                _autore = _re.sub(r"\s+", " ", _autore)[:40].strip()
            except Exception:
                pass
            _lic_nome = _ext.get("LicenseShortName", {}).get("value", "CC BY")
            return _norm(url, (_autore or "Wikimedia Commons") + f" ({_lic_nome})",
                         "https://commons.wikimedia.org", "Wikimedia Commons")
        return None
    except Exception:
        return None

def cerca_immagine(query, lang="it", disciplina=None, nome=None, rank=0, ingredienti=None, evita_urls=None):
    """ROUTING: Pexels -> Unsplash -> Pixabay. Se arriva nome+disciplina costruisce la query intelligente.
    Se rank non è forzato (0) e c'è un nome, deriva un rank dal NOME: cosi ricette diverse con la stessa
    query (es. besciamella e bagna cauda, entrambe 'cooking sauce pan') prendono foto DIVERSE, non la stessa."""
    _evita = set(evita_urls or [])
    def _ok_url(_r):
        return _r and _r.get("url") and _r["url"] not in _evita
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
        for _rk in range(rank, rank + 5):
            for fonte in (_wikimedia, _pexels, _unsplash, _pixabay):
                res = fonte(nome_pulito, _rk % 5)
                if _ok_url(res):
                    res["match"] = "piatto"
                    return res
    # 3) INGREDIENTI PRINCIPALI: se il piatto esatto non c'è, meglio gli INGREDIENTI
    #    (guanciale pecorino) che una foto di un altro piatto. Passati da chi chiama.
    if ingredienti:
        ing_query = " ".join(str(i).lower() for i in ingredienti[:2] if i)
        if ing_query.strip():
            for _rk in range(rank, rank + 5):
                for fonte in (_pexels, _unsplash, _pixabay, _wikimedia):
                    res = fonte(ing_query, _rk % 5)
                    if _ok_url(res):
                        res["match"] = "ingredienti"
                        return res
    # 4) FALLBACK INGREDIENTE SINGOLO (regola: MAI blueprint, sempre piatto o ingrediente).
    #    Se piatto e ingredienti-combinati falliscono, cerco il PRIMO ingrediente da solo
    #    (manzo, pomodoro, gin...) traducendolo in inglese, e prendo la prima foto SENZA filtro:
    #    una foto di "beef" per una ricetta di manzo è sempre giusta, non serve filtrarla.
    if ingredienti:
        for _ing in ingredienti[:4]:
            _ing_en = _KW_IT_EN.get(str(_ing).lower().strip(), str(_ing).lower().strip())
            # prendo solo la prima parola-chiave utile (es. "beef" da "beef dish plated")
            _ing_kw = _ing_en.split()[0] if _ing_en else ""
            if len(_ing_kw) < 3:
                continue
            for _rk in range(rank, rank + 6):
                for fonte in (_pexels, _unsplash, _pixabay, _wikimedia):
                    res = fonte(_ing_kw + " food", _rk % 6, no_filtro=True)
                    if _ok_url(res):
                        res["match"] = "ingrediente"
                        return res
    # 5) ULTIMA RISORSA: foto generica della disciplina (mai blueprint vuoto). Vario col rank_nome
    #    così piatti diversi della stessa disciplina prendono foto DIVERSE, non tutte uguali.
    _disc_q = {"bar": "cocktail glass drink", "cucina": "gourmet plated dish", "pasticceria": "dessert plate",
               "panificazione": "artisan bread bakery", "gelateria": "gelato ice cream cup",
               "caffetteria": "coffee espresso cup"}.get((disciplina or "").lower(), "plated food dish")
    for _rk in range(rank_nome % 8, (rank_nome % 8) + 8):
        for fonte in (_pexels, _unsplash, _pixabay):
            res = fonte(_disc_q, _rk % 8, no_filtro=True)
            if _ok_url(res):
                res["match"] = "disciplina"
                return res
    return None

def credito_immagine(autore, fonte_nome="Pexels"):
    if autore:
        return f"Foto: {autore} / {fonte_nome}"
    return f"Foto: {fonte_nome}"
