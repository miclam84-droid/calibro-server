# genera_serbatoio.py - genera liste di piatti canonici VERI via AI per riempire il serbatoio in volume.
# Invece di scrivere 30 piatti a mano, l'AI ne genera centinaia (piatti reali, non inventati) per
# disciplina. Si validano e si aggiungono al serbatoio. Poi il generatore li trasforma in ricette.

def genera_lista_piatti(disciplina, area, quanti=50):
    """Chiede all'AI una lista di piatti/preparazioni CANONICI VERI per disciplina+area.
    Restituisce lista di dict {nome, chiave, firma}. Solo piatti REALI, non inventati."""
    from ai import _haiku_raw
    import json, re
    prompt = (
        f"Elenca {quanti} {disciplina} CANONICI riconosciuti da almeno una fonte professionale "
        f"internazionale (IBA, Difford's, guide gastronomiche, tradizione documentata) della {area}. "
        f"SOLO preparazioni che ESISTONO DAVVERO e sono conosciute dai professionisti del settore, "
        f"MAI inventate. Se non sei sicuro che una esista, NON includerla. "
        f"Per ognuno dai: nome, ingrediente-chiave, 3-5 ingredienti principali reali.\n"
        f"Rispondi SOLO con un array JSON, nient'altro. Formato ESATTO:\n"
        f'[{{"nome":"Nome Piatto","chiave":"ingrediente principale","firma":["ing1","ing2","ing3"]}}]\n'
        f"NON aggiungere testo prima o dopo il JSON. NON ripetere piatti. Meglio pochi VERI che tanti inventati."
    )
    try:
        raw = _haiku_raw(prompt, max_tokens=3000)
        # estraggo il JSON
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if not m:
            return []
        lista = json.loads(m.group(0))
        # valido: ogni voce deve avere nome, chiave, firma
        out = []
        _visti = set()
        for p in lista:
            if not (isinstance(p, dict) and p.get("nome") and p.get("firma")):
                continue
            nome = str(p["nome"])[:80].strip()
            firma = [str(x)[:40] for x in p.get("firma", [])][:6]
            # FILTRO 1 - deduplica interna
            if nome.lower() in _visti:
                continue
            # FILTRO 2 - coerenza: la firma deve avere almeno 2 ingredienti reali (non vuoti)
            firma_valida = [f for f in firma if f and len(f) > 1]
            if len(firma_valida) < 2:
                continue
            # FILTRO 3 - canonicità bar: un cocktail DEVE avere un distillato/fermentato nella firma
            if disciplina.lower() in ("cocktail", "bar", "drink"):
                _distillati = ("gin", "vodka", "rum", "whisky", "whiskey", "bourbon", "rye", "tequila",
                               "cognac", "brandy", "mezcal", "pisco", "cachaça", "vermouth", "campari",
                               "aperol", "prosecco", "champagne", "vino", "amaro", "sherry", "liquore",
                               "scotch", "chartreuse", "cointreau", "maraschino", "bitter")
                testo_firma = " ".join(firma_valida).lower()
                if not any(d in testo_firma for d in _distillati):
                    continue  # un cocktail senza alcol/fermentato = scartato (probabile invenzione)
            _visti.add(nome.lower())
            out.append({
                "nome": nome,
                "chiave": str(p.get("chiave", ""))[:40],
                "firma": firma_valida,
                "area": area,
                "disciplina": disciplina,
                "tipo": "da_validare",  # pipeline 2 fasi: entra come "da validare", non pubblicato
            })
        return out
    except Exception as e:
        return []
