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
        f"in '{ingrediente}'. Usa i NOMI CHIMICI IN INGLESE (es. per il limone: limonene, citral, "
        f"beta-pinene; per il basilico: linalool, eugenol, estragole). Solo composti reali documentati.\n"
        f"Rispondi SOLO con array JSON di stringhe in inglese: [\"limonene\",\"citral\",...]\n"
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


def _norm_composto(s):
    """Normalizza un nome di composto per il matching."""
    import re
    s = (s or "").lower()
    # traduzioni composti IT->EN comuni (il grafo Ahn è in inglese)
    _it_en = {"linalolo":"linalool","citrale":"citral","geraniolo":"geraniol",
              "nerolo":"nerol","terpineolo":"terpineol","citronellolo":"citronellol",
              "citronellale":"citronellal","mircene":"myrcene","canfora":"camphor",
              "eugenolo":"eugenol","vanillina":"vanillin","mentolo":"menthol"}
    s = _it_en.get(s.strip(), s)
    s = re.sub(r"^comp[_-]", "", s)
    s = re.sub(r"^(d|l|dl|r|s|e|z|n|o|m|p|alpha|beta|gamma|delta|cis|trans|iso)[\s_-]+", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def aggiungi_al_grafo(db, ingrediente, composti):
    """Aggiunge l'ingrediente + lo collega ai composti ESISTENTI nel grafo (matching normalizzato),
    così gli abbinamenti emergono dai composti condivisi con gli ingredienti Ahn."""
    import re
    ing_id = "ai_" + re.sub(r"[^a-z0-9]+", "_", ingrediente.lower()).strip("_")
    collegati = 0; agganciati_esistenti = 0
    try:
        db.execute("INSERT INTO nodes (id, name, type, data) VALUES (?, ?, 'Prodotto', ?) ON CONFLICT (id) DO NOTHING",
                   (ing_id, ingrediente.lower(), '{"provenienza":"C_ai"}'))
        # carico TUTTI i composti del grafo una volta, con nome normalizzato -> id
        tutti = db.execute("SELECT id, name FROM nodes WHERE type='Composto'").fetchall()
        mappa = {}
        for r in tutti:
            _id = r["id"] if hasattr(r, "keys") else r[0]
            _nm = r["name"] if hasattr(r, "keys") else r[1]
            mappa[_norm_composto(_nm)] = _id
            mappa[_norm_composto(_id)] = _id  # anche per id
        for comp in composti:
            key = _norm_composto(comp)
            if not key:
                continue
            if key in mappa:
                comp_id = mappa[key]  # AGGANCIO a un composto ESISTENTE (l'abbinamento emergerà!)
                agganciati_esistenti += 1
            else:
                comp_id = "comp_" + re.sub(r"[^a-z0-9]+", "_", comp.lower()).strip("_")
                db.execute("INSERT INTO nodes (id, name, type, data) VALUES (?, ?, 'Composto', '{}') ON CONFLICT (id) DO NOTHING",
                           (comp_id, comp.lower()))
                mappa[key] = comp_id
            db.execute("INSERT INTO edges (from_id, to_id, relation, data) VALUES (?, ?, 'contiene_composto', '{}') ON CONFLICT DO NOTHING",
                       (ing_id, comp_id))
            collegati += 1
    except Exception:
        pass
    return {"ingrediente": ingrediente, "id": ing_id, "composti_aggiunti": collegati, "agganciati_a_esistenti": agganciati_esistenti}
