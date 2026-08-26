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


def _pixabay_cerca(query, food=True):
    """Cerca su Pixabay. Ritorna lista di hit (dict) o []."""
    if not PIXABAY_KEY:
        return []
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
    """La foto è a tema? I suoi tag devono contenere la parola cercata (o una sua parte
    significativa). Scarta i mismatch (query 'guanciale' -> foto con tag 'kale')."""
    tags = (hit.get("tags") or "").lower()
    q = query.lower().strip()
    # match diretto
    if q in tags:
        return True
    # match per parola singola significativa (>=4 lettere, non stopword)
    for parola in q.split():
        if len(parola) >= 4 and parola not in _STOPWORDS and parola in tags:
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
