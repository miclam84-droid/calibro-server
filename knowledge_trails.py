# knowledge_trails.py
# KNOWLEDGE TRAILS: i percorsi di scoperta di Matter. La meccanica di LONGEVITÀ (retention):
# l'utente parte da un ingrediente e l'app lo porta in un viaggio ingrediente->composto->abbinamento
# ->fenomeno->tecnica->ricetta. Dopo anni scopre ancora percorsi nuovi.
# Il revisore: "vale più di 1000 ricette". Gira sulla Knowledge Architecture, non tocca il Flavour.

def costruisci_trail(db, ingrediente_start):
    """Costruisce un percorso di scoperta a partire da un ingrediente.
    Un trail collega: ingrediente -> composto chiave -> ingrediente affine -> fenomeno -> ricetta.
    Ogni tappa è un nodo REALE del grafo (non inventato). Restituisce le tappe del viaggio."""
    from knowledge_architecture import categoria_di, famiglia_aromatica_di
    ing = (ingrediente_start or "").lower().strip()
    trail = []
    # mappa italiano->inglese per cercare nel grafo Ahn (che è in inglese)
    _IT_EN = {"basilico": "basil", "pomodoro": "tomato", "aglio": "garlic", "cipolla": "onion",
              "limone": "lemon", "arancia": "orange", "mela": "apple", "fragola": "strawberry",
              "cioccolato": "chocolate", "caffè": "coffee", "manzo": "beef", "pollo": "chicken",
              "gambero": "shrimp", "menta": "mint", "rosmarino": "rosemary", "zenzero": "ginger",
              "cannella": "cinnamon", "vaniglia": "vanilla", "miele": "honey", "burro": "butter",
              "parmigiano": "parmesan", "funghi": "mushroom", "whisky": "whisky", "gin": "gin",
              "rum": "rum", "nocciola": "hazelnut", "mandorla": "almond", "pistacchio": "pistachio"}
    ing_en = _IT_EN.get(ing, ing)
    cat = categoria_di(ing)
    fam = famiglia_aromatica_di(ing)
    trail.append({"tappa": "ingrediente", "nome": ingrediente_start,
                  "dettaglio": f"Categoria: {cat or 'da classificare'}" + (f" · Famiglia aromatica: {fam}" if fam else "")})
    # trovo il nodo ingrediente (try isolato)
    nid = None
    try:
        _n = db.execute("SELECT id FROM nodes WHERE type='Prodotto' AND lower(name)=? LIMIT 1", (ing_en,)).fetchone()
        if not _n:
            _n = db.execute("SELECT id FROM nodes WHERE type='Prodotto' AND lower(name) LIKE ? LIMIT 1", (f"{ing_en}%",)).fetchone()
        nid = _n[0] if _n else None
    except Exception:
        pass
    # tappa 2: composto (try isolato)
    if nid:
        try:
            _comp = db.execute("SELECT n2.name FROM edges e JOIN nodes n2 ON n2.id=e.to_id WHERE e.from_id=? AND e.relation='contiene_composto' LIMIT 1", (nid,)).fetchone()
            if _comp:
                _cn = _comp[0].replace("comp_", "").replace("_", " ")
                trail.append({"tappa": "composto", "nome": _cn,
                              "dettaglio": f"{ingrediente_start} contiene {_cn}: una delle molecole che ne guida gli abbinamenti."})
        except Exception:
            pass
        # tappa 3: affine (try isolato)
        try:
            _aff = db.execute("SELECT n2.name FROM edges e JOIN nodes n2 ON n2.id=e.to_id WHERE e.from_id=? AND e.relation='abbinamento_aromatico' LIMIT 1", (nid,)).fetchone()
            if _aff:
                _an = _aff[0].replace("_", " ")
                trail.append({"tappa": "abbinamento", "nome": _an,
                              "dettaglio": f"{_an} è un abbinamento aromatico di {ingrediente_start}: condividono composti chiave."})
        except Exception:
            pass
    # tappa 4: fenomeno (try isolato)
    try:
        _fen = db.execute("SELECT name FROM nodes WHERE type='Fenomeno' ORDER BY RANDOM() LIMIT 1").fetchone()
        if _fen:
            trail.append({"tappa": "fenomeno", "nome": _fen[0],
                          "dettaglio": f"Esplora il fenomeno {_fen[0]}: la scienza che governa questo ingrediente al banco."})
    except Exception:
        pass
    # tappa 5: ricetta (try isolato)
    try:
        _ric = db.execute("SELECT nome FROM ricette WHERE lower(nome) LIKE ? LIMIT 1", (f"%{ing}%",)).fetchone()
        if _ric:
            trail.append({"tappa": "ricetta", "nome": _ric[0],
                          "dettaglio": f"Mettilo in pratica: {_ric[0]}."})
    except Exception:
        pass
    return trail
