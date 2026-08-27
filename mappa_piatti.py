# mappa_piatti.py
# PUNTO DI ACCESSO UNIFICATO a tutti i piatti canonici (Italia base + estesa + mondo).
# Il builder usa SOLO questo modulo. Deduplica per nome.

def _carica_tutto():
    piatti = {}

    def _aggiungi(nome, chiave, firma, area, regione=None, disc="cucina"):
        if nome not in piatti:
            piatti[nome] = {
                "nome": nome, "chiave": chiave, "firma": firma,
                "area": area, "regione": regione, "disc": disc,
            }

    # Italia base
    try:
        from mappa_italia_regioni import REGIONI as _R1
        for reg, lista in _R1.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Italia estesa
    try:
        from mappa_italia_estesa import REGIONI_ESTESE as _R2
        for reg, lista in _R2.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo
    try:
        from mappa_mondo import CUCINE as _C
        for cucina, lista in _C.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo parte 2
    try:
        from mappa_mondo2 import CUCINE2 as _C2
        for cucina, lista in _C2.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Italia parte 3
    try:
        from mappa_italia3 import REGIONI_3 as _R3
        for reg, lista in _R3.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo parte 3
    try:
        from mappa_mondo3 import CUCINE3 as _C3
        for cucina, lista in _C3.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Italia parte 4
    try:
        from mappa_italia4 import REGIONI_4 as _R4
        for reg, lista in _R4.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo parte 4
    try:
        from mappa_mondo4 import CUCINE4 as _C4
        for cucina, lista in _C4.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Italia parte 5
    try:
        from mappa_italia5 import REGIONI_5 as _R5
        for reg, lista in _R5.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo parte 5
    try:
        from mappa_mondo5 import CUCINE5 as _C5
        for cucina, lista in _C5.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Italia parte 6
    try:
        from mappa_italia6 import REGIONI_6 as _R6
        for reg, lista in _R6.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
    except Exception:
        pass
    # Mondo parte 6
    try:
        from mappa_mondo6 import CUCINE6 as _C6
        for cucina, lista in _C6.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Extra parte 7 (Italia + Mondo)
    try:
        from mappa_extra7 import ITALIA_7 as _I7, MONDO_7 as _M7
        for reg, lista in _I7.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
        for cucina, lista in _M7.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Extra parte 8 (Italia + Mondo) — chiusura verso 1000
    try:
        from mappa_extra8 import ITALIA_8 as _I8, MONDO_8 as _M8
        for reg, lista in _I8.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
        for cucina, lista in _M8.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Extra parte 9 — supera 1000
    try:
        from mappa_extra9 import ITALIA_9 as _I9, MONDO_9 as _M9
        for reg, lista in _I9.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", reg, p.get("disc", "cucina"))
        for cucina, lista in _M9.items():
            for p in lista:
                _aggiungi(p["nome"], p["chiave"], p["firma"], cucina, cucina, p.get("disc", "cucina"))
    except Exception:
        pass
    # Bar IBA + pasticceria/panificazione extra
    try:
        from mappa_bar_iba import BAR_IBA as _BAR, PASTICCERIA_EXTRA as _PAST, PANIFICAZIONE_EXTRA as _PANI
        for p in _BAR:
            _aggiungi(p["nome"], p["chiave"], p["firma"], "Bar / Cocktail", "Bar / Cocktail", "bar")
        for p in _PAST:
            _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", "Pasticceria", "pasticceria")
        for p in _PANI:
            _aggiungi(p["nome"], p["chiave"], p["firma"], "Italia", "Panificazione", "panificazione")
    except Exception:
        pass

    return list(piatti.values())


_CACHE = None

def tutti_i_piatti():
    global _CACHE
    if _CACHE is None:
        _CACHE = _carica_tutto()
    return _CACHE


def cerca_piatto(richiesta):
    """Cerca il piatto canonico che corrisponde alla richiesta. Ritorna dict o None.
    Matcha SOLO se la richiesta NOMINA il piatto (es. 'fammi una carbonara'), non se
    gli ingredienti del nome capitano in una lista (es. 'zucca e manzo' NON deve
    forzare 'Chow Fun di Manzo con Zucca' — è una richiesta di ingredienti, non di piatto)."""
    req = (richiesta or "").lower()
    for p in tutti_i_piatti():
        nome_l = p["nome"].lower()
        # match forte: il nome del piatto (o la sua parte distintiva) è nella richiesta
        if nome_l in req:
            return p
        # match sulla parola distintiva del piatto (la prima parola lunga del nome,
        # tipicamente il nome proprio: 'carbonara', 'amatriciana', 'financier')
        parole = [w for w in nome_l.replace("'", " ").replace("(", " ").replace(")", " ").split()
                  if len(w) >= 5 and w not in ("manzo", "zucca", "pollo", "pesce", "pasta", "salsa",
                                                "crema", "brodo", "carne", "verdure", "patate")]
        # scatta solo se la PRIMA parola distintiva del nome è esplicitamente nella richiesta
        if parole and parole[0] in req:
            return p
    return None


def conta():
    piatti = tutti_i_piatti()
    per_area = {}
    for p in piatti:
        per_area[p["area"]] = per_area.get(p["area"], 0) + 1
    return {"totale": len(piatti), "per_area": per_area}
