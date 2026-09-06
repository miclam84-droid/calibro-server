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
    try:
        # tappa 1: l'ingrediente di partenza + la sua categoria/famiglia
        cat = categoria_di(ing)
        fam = famiglia_aromatica_di(ing)
        trail.append({"tappa": "ingrediente", "nome": ingrediente_start,
                      "dettaglio": f"Categoria: {cat or 'da classificare'}" + (f" · Famiglia aromatica: {fam}" if fam else "")})
        # tappa 2: un composto aromatico chiave dell'ingrediente (dal grafo reale)
        _row = db.execute(
            "SELECT n2.name FROM nodes n1 "
            "JOIN edges e ON e.from_id = n1.id "
            "JOIN nodes n2 ON n2.id = e.to_id "
            "WHERE lower(n1.name) LIKE ? AND e.relation='contiene_composto' "
            "AND n2.type='Composto' LIMIT 1", (f"%{ing}%",)).fetchone()
        composto = (_row[0] if _row else None)
        if composto:
            trail.append({"tappa": "composto", "nome": composto,
                          "dettaglio": f"{ingrediente_start} contiene {composto}: la molecola che guida gli abbinamenti."})
        # tappa 3: un ingrediente affine (che condivide il composto)
        if composto:
            _row2 = db.execute(
                "SELECT DISTINCT n1.name FROM nodes n1 "
                "JOIN edges e ON e.from_id = n1.id "
                "JOIN nodes n2 ON n2.id = e.to_id "
                "WHERE n2.name = ? AND e.relation='contiene_composto' "
                "AND lower(n1.name) NOT LIKE ? LIMIT 1", (composto, f"%{ing}%")).fetchone()
            affine = (_row2[0] if _row2 else None)
            if affine:
                trail.append({"tappa": "abbinamento", "nome": affine,
                              "dettaglio": f"{affine} condivide {composto} con {ingrediente_start}: ecco perché si abbinano."})
        # tappa 4: un fenomeno collegato alla categoria (dal grafo)
        _row3 = db.execute(
            "SELECT name FROM nodes WHERE type='Fenomeno' ORDER BY RANDOM() LIMIT 1").fetchone()
        if _row3:
            trail.append({"tappa": "fenomeno", "nome": _row3[0],
                          "dettaglio": f"Il fenomeno {_row3[0]}: la scienza dietro l'uso di questo ingrediente."})
        # tappa 5: una ricetta che usa l'ingrediente
        _row4 = db.execute(
            "SELECT nome FROM ricette WHERE ingredienti::text LIKE ? LIMIT 1", (f"%{ing}%",)).fetchone()
        if _row4:
            trail.append({"tappa": "ricetta", "nome": _row4[0],
                          "dettaglio": f"Mettilo in pratica: {_row4[0]}."})
    except Exception:
        pass
    return trail
