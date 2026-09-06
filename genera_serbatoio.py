# genera_serbatoio.py - genera liste di piatti canonici VERI via AI per riempire il serbatoio in volume.
# Invece di scrivere 30 piatti a mano, l'AI ne genera centinaia (piatti reali, non inventati) per
# disciplina. Si validano e si aggiungono al serbatoio. Poi il generatore li trasforma in ricette.

def genera_lista_piatti(disciplina, area, quanti=50):
    """Chiede all'AI una lista di piatti/preparazioni CANONICI VERI per disciplina+area.
    Restituisce lista di dict {nome, chiave, firma}. Solo piatti REALI, non inventati."""
    from ai import _haiku_raw
    import json, re
    prompt = (
        f"Elenca {quanti} {disciplina} CANONICI e REALI della tradizione {area}. "
        f"Solo piatti/preparazioni che esistono davvero e sono conosciuti dai professionisti, "
        f"NON inventati. Per ognuno dai: nome, ingrediente-chiave, 3-5 ingredienti principali.\n"
        f"Rispondi SOLO con un array JSON, nient'altro. Formato ESATTO:\n"
        f'[{{"nome":"Nome Piatto","chiave":"ingrediente principale","firma":["ing1","ing2","ing3"]}}]\n'
        f"NON aggiungere testo prima o dopo il JSON. NON ripetere piatti."
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
        for p in lista:
            if isinstance(p, dict) and p.get("nome") and p.get("firma"):
                out.append({
                    "nome": str(p["nome"])[:80],
                    "chiave": str(p.get("chiave", ""))[:40],
                    "firma": [str(x)[:40] for x in p.get("firma", [])][:6],
                    "area": area,
                    "disciplina": disciplina,
                })
        return out
    except Exception as e:
        return []
