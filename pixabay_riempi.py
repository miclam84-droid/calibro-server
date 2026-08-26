# pixabay_riempi.py
# Riempie le ricette senza foto pescando da Pixabay (licenza pulita, commerciale OK).
# Cascata: prima cerca il PIATTO, se non trova ripiega sull'INGREDIENTE principale.
# REGOLA D'ORO: verifica i tag — se la foto non è a tema (guanciale->kale), la scarta.
# Non hotlinking: scarica la foto e la carica su Cloudinary (come richiede la licenza API).
# Attribuzione: salva l'autore Pixabay in immagine_autore ("show where images are from").

import os, json, base64, hashlib, time
import urllib.request, urllib.parse

PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")

# parole che, se sono l'UNICO match, indicano un probabile mismatch (troppo generiche)
_STOPWORDS = {"food", "meal", "dinner", "lunch", "dish", "plate", "cuisine", "eat", "cooking", "kitchen"}


def _pulisci_query(q):
    """Pulisce il nome per la ricerca: toglie parentesi, suffissi tipo 'rivisitato/classico',
    e parole di rumore, per aumentare la pertinenza dei risultati Pixabay."""
    import re
    q = re.sub(r"\([^)]*\)", "", q or "").strip()
    _RUMORE = {"rivisitato", "rivisitata", "classico", "classica", "classici", "classiche",
               "tradizionale", "fatto", "in", "casa", "della", "del", "di", "al", "alla",
               "con", "e", "la", "il", "lo", "le", "i", "gli"}
    parole = [p for p in q.split() if p.lower() not in _RUMORE]
    return " ".join(parole) if parole else q


def _pixabay_cerca(query, food=True):
    """Cerca su Pixabay. Ritorna lista di hit (dict) o []."""
    if not PIXABAY_KEY:
        return []
    query = _pulisci_query(query)
    params = {
        "key": PIXABAY_KEY, "q": query, "image_type": "photo",
        "order": "popular", "safesearch": "true", "per_page": 5, "lang": "it",
    }
    if food:
        params["category"] = "food"
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            d = json.loads(r.read())
            return d.get("hits", [])
    except Exception:
        # riprova senza categoria food (alcuni ingredienti non sono in "food")
        if food:
            return _pixabay_cerca(query, food=False)
        return []


def _tag_pertinente(hit, query):
    """La foto è a tema? Filtro SEVERO per evitare i mismatch (brasato->mele, baccalà->mirtilli).
    Regole:
    - i tag NON devono contenere parole palesemente off (sfondo, wallpaper, ecc.)
    - la parola della query che combacia dev'essere SPECIFICA (>=5 lettere) e presente nei tag,
      OPPURE combaciano almeno 2 parole della query di >=4 lettere."""
    tags = (hit.get("tags") or "").lower()
    if not tags:
        return False
    # lista nera: se compaiono, la foto è quasi certamente fuori tema
    _BLACKLIST = {"wallpaper", "carta da parati", "sfondo", "background", "texture",
                  "in crescita", "crescita", "growing", "nature", "natura", "landscape",
                  "paesaggio", "wall", "muro", "astratto", "abstract"}
    for bad in _BLACKLIST:
        if bad in tags:
            return False
    q = _pulisci_query(query).lower().strip()
    parole = [p for p in q.split() if len(p) >= 4 and p not in _STOPWORDS]
    if not parole:
        return False
    # match forte: una parola specifica (>=5 lettere) presente nei tag
    forti = [p for p in parole if len(p) >= 5 and p in tags]
    if forti:
        return True
    # match medio: almeno 2 parole (>=4 lettere) presenti nei tag
    presenti = [p for p in parole if p in tags]
    if len(presenti) >= 2:
        return True
    return False


def _scarica(url):
    """Scarica i byte dell'immagine."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read()
    except Exception:
        return None


def _carica_cloudinary(img_bytes, public_id):
    """Carica su Cloudinary con upload firmato. Ritorna l'URL sicuro o None."""
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME")
    key = os.environ.get("CLOUDINARY_API_KEY")
    secret = os.environ.get("CLOUDINARY_API_SECRET")
    if not (cloud and key and secret and img_bytes):
        return None
    ts = str(int(time.time()))
    # firma: sha1 di "public_id=...&timestamp=...{secret}"
    to_sign = f"public_id={public_id}&timestamp={ts}{secret}"
    signature = hashlib.sha1(to_sign.encode()).hexdigest()
    # multipart/form-data manuale
    boundary = "----matterpixabay" + ts
    parts = []
    def campo(nome, valore):
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{nome}\"\r\n\r\n{valore}\r\n")
    campo("public_id", public_id)
    campo("timestamp", ts)
    campo("api_key", key)
    campo("signature", signature)
    # file
    pre = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{public_id}.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
    body = b"".join(p.encode() for p in parts) + pre.encode() + img_bytes + f"\r\n--{boundary}--\r\n".encode()
    url = f"https://api.cloudinary.com/v1_1/{cloud}/image/upload"
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read())
            return d.get("secure_url")
    except Exception:
        return None
