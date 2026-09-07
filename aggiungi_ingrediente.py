# aggiungi_ingrediente.py - il modo GIUSTO di espandere il grafo.
# Non genera ABBINAMENTI (stime), genera i COMPOSTI aromatici di un ingrediente nuovo
# (fatti chimici, verificabili su PubChem). Poi il GRAFO trova gli abbinamenti DA SOLO
# collegando l'ingrediente a tutti quelli che condividono i suoi composti.

def genera_composti_ingrediente(ingrediente):
    """Genera la lista dei composti aromatici volatili di un ingrediente via AI.
    Sono FATTI CHIMICI (verificabili su PubChem/letteratura), non opinioni.
    Restituisce lista di nomi di composti."""
    from ai import chiedi_mistral
    import json
    prompt = (
        f"Da chimico degli alimenti: elenca i 6-12 principali COMPOSTI AROMATICI VOLATILI presenti "
        f"in '{ingrediente}'. Solo composti reali e documentati (es. per il limone: limonene, "
        f"citrale, beta-pinene). Usa i nomi chimici standard in minuscolo.\n"
        f"Rispondi SOLO con array JSON di stringhe: [\"limonene\",\"citrale\",...]\n"
        f"Nessun testo prima o dopo."
    )
    try:
        raw = chiedi_mistral(prompt, usa_tools=False)
        if not raw:
            return []
        _txt = raw.replace("```json","").replace("```","").strip()
        s = _txt.find("["); e = _txt.rfind("]")
        if s < 0 or e <= s:
            return []
        lista = json.loads(_txt[s:e+1])
        out = []
        for x in lista:
            nome = str(x).strip().lower()
            if 2 < len(nome) < 60 and nome not in out:
                out.append(nome)
        return out[:12]
    except Exception:
        return []


def aggiungi_al_grafo(db, ingrediente, composti):
    """Aggiunge l'ingrediente + collega ai composti ESISTENTI nel grafo (per nome parziale),
    così gli abbinamenti emergono. Se un composto non esiste, lo crea."""
    import re
    ing_id = "ai_" + re.sub(r"[^a-z0-9]+", "_", ingrediente.lower()).strip("_")
    collegati = 0
    try:
        db.execute("INSERT INTO nodes (id, name, type, data) VALUES (?, ?, 'Prodotto', ?) ON CONFLICT (id) DO NOTHING",
                   (ing_id, ingrediente.lower(), '{"provenienza":"C_ai"}'))
        for comp in composti:
            comp_clean = comp.lower().strip()
            # cerco il composto ESISTENTE nel grafo per nome parziale (limonene matcha comp_limonene, d-limonene...)
            _pat = "%" + re.sub(r"[^a-z0-9]", "%", comp_clean) + "%"
            rows = db.execute("SELECT id FROM nodes WHERE type='Composto' AND (name ILIKE ? OR id ILIKE ?) LIMIT 1",
                              (_pat, _pat)).fetchall()
            if rows:
                comp_id = rows[0]["id"] if hasattr(rows[0], "keys") else rows[0][0]
            else:
                # non esiste: lo creo
                comp_id = "comp_" + re.sub(r"[^a-z0-9]+", "_", comp_clean).strip("_")
                db.execute("INSERT INTO nodes (id, name, type, data) VALUES (?, ?, 'Composto', '{}') ON CONFLICT (id) DO NOTHING",
                           (comp_id, comp_clean))
            # arco ingrediente -> composto (collega al composto ESISTENTE se trovato)
            db.execute("INSERT INTO edges (from_id, to_id, relation, data) VALUES (?, ?, 'contiene_composto', '{}') ON CONFLICT DO NOTHING",
                       (ing_id, comp_id))
            collegati += 1
    except Exception:
        pass
    return {"ingrediente": ingrediente, "id": ing_id, "composti_aggiunti": collegati}
