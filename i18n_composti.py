# i18n_composti.py — localizzazione EN/ES delle NOTE d'asse generate
# (amaro / astringente / piccante / termico). SOLO presentazione: non tocca
# voti, stati, provenienza o i marcatori grezzi. IT = passthrough identico al
# comportamento precedente, cosi' nessun output italiano esistente cambia.
# Dati in data/composti_i18n.json; se il file manca o e' illeggibile, i
# generatori usano il loro fallback IT hardcoded (robusto: mai un crash).
import os
import json

_P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_i18n.json")
_D = None


def _dati():
    global _D
    if _D is None:
        try:
            with open(_P, encoding="utf-8") as f:
                _D = json.load(f)
        except Exception:
            _D = {"marcatori": {}, "frame": {}}
    return _D


def marcatori_loc(marcatori, lang):
    """Traduce i nomi dei marcatori. IT (o lang vuota) = invariato. Un termine
    non in dizionario passa invariato: una traduzione falsa e' peggio di nessuna."""
    if not lang or lang == "it":
        return list(marcatori)
    mp = _dati().get("marcatori", {})
    out = []
    for m in marcatori:
        t = mp.get(m) or mp.get(str(m).lower())
        out.append((t or {}).get(lang) or m)
    return out


def nota_asse(asse, marcatori, lang, direzione=None):
    """Costruisce la nota localizzata per un asse. Ritorna None se non c'e' una
    cornice (il chiamante tiene allora il suo testo IT di default)."""
    fr = _dati().get("frame", {}).get(asse)
    if fr is not None and direzione is not None:
        fr = fr.get(direzione)
    if not fr:
        return None
    tmpl = fr.get(lang) or fr.get("it")
    if not tmpl:
        return None
    return tmpl.replace("{m}", ", ".join(marcatori_loc(marcatori, lang)))
