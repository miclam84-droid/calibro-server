"""immagini.py — recupero immagini stock da Pexels (API gratuita) per le ricette.
Serve PEXELS_API_KEY nell'ambiente (registrazione gratuita su pexels.com/api).
Salva URL + autore + fonte con CREDITO obbligatorio (regola Pexels: attribuire l'autore).
"""
import os, json, urllib.request, urllib.parse, urllib.error

_PEXELS_URL = "https://api.pexels.com/v1/search"

def cerca_immagine(query, lang="it"):
    """Cerca un'immagine pertinente su Pexels. Ritorna dict {url, autore, fonte} o None.
    query: testo di ricerca (es. nome ricetta o ingrediente principale)."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None  # nessuna chiave: niente immagine (non blocca la ricetta)
    try:
        # Pexels cerca meglio in inglese; per query italiane usiamo comunque il testo dato
        params = urllib.parse.urlencode({"query": query, "per_page": 3, "orientation": "landscape"})
        req = urllib.request.Request(
            f"{_PEXELS_URL}?{params}",
            headers={"Authorization": key, "User-Agent": "MatterLab/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        fotos = data.get("photos", [])
        if not fotos:
            return None
        f = fotos[0]
        return {
            "url": f.get("src", {}).get("large") or f.get("src", {}).get("medium") or "",
            "autore": f.get("photographer", "") or "",
            "fonte": f.get("url", "") or "",  # pagina Pexels della foto (per il credito)
        }
    except Exception:
        return None

def credito_immagine(autore):
    """Testo di credito obbligatorio per Pexels."""
    return f"Foto: {autore} / Pexels" if autore else "Foto: Pexels"
