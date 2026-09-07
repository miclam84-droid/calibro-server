# arricchisci_abbinamenti.py - genera abbinamenti AI per ingredienti poveri, filtrati e marcati.
# LIVELLO 2 (stima AI) sopra il LIVELLO 0 (Ahn verificato). Provenienza 'C' = da verificare.
# Il filtro anti-rumore (categorie compatibili) impedisce gli abbinamenti assurdi.

def genera_abbinamenti_ai(ingrediente, categoria=None):
    """Genera abbinamenti plausibili per un ingrediente via AI, filtrati per compatibilità
    merceologica. Restituisce lista di {ingrediente, forza, provenienza:'C_stima_ai'}."""
    from ai import chiedi_mistral
    import json, re
    prompt = (
        f"Da chef professionista: elenca 8-12 ingredienti che si abbinano bene con '{ingrediente}' "
        f"in cucina/pasticceria/mixology. SOLO abbinamenti gastronomicamente sensati e usati davvero "
        f"dai professionisti, NON teorici. Per ognuno indica la forza (forte/media/esplorativa).\n"
        f"Rispondi SOLO con array JSON: [{{\"ingrediente\":\"nome\",\"forza\":\"forte|media|esplorativa\"}}]\n"
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
        _visti = set()
        for x in lista:
            if not isinstance(x, dict) or not x.get("ingrediente"):
                continue
            nome = str(x["ingrediente"]).strip().lower()
            if nome == ingrediente.lower() or nome in _visti or len(nome) < 2:
                continue
            # filtro anti-rumore: categoria compatibile
            try:
                from knowledge_architecture import categoria_di, categorie_compatibili
                cat_a = categoria or categoria_di(ingrediente)
                cat_b = categoria_di(nome)
                if not categorie_compatibili(cat_a, cat_b):
                    continue
            except Exception:
                pass
            _visti.add(nome)
            out.append({
                "ingrediente": nome,
                "forza": x.get("forza", "media"),
                "provenienza": "C_stima_ai",  # da verificare - non è fonte primaria
            })
        return out[:12]
    except Exception:
        return []
