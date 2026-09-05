# grounding_bar_bakery.py
# Parametri VERI (fonti: Hamelman, Modernist Bread, Dave Arnold "Liquid Intelligence", IBA).
# Servono come ANCORA DI VERITÀ per il generatore: impediscono gli errori catastrofici che
# distruggono la credibilità B2B (segale al 60%, Negroni senza spumante).
# Michele (cocktail bar + bakery reali) può verificare/correggere questi valori sul campo.

# ── BAKERY: idratazione per tipo di farina (fonte: Hamelman, Modernist Bread) ──
# La segale NON sviluppa glutine, assorbe via pentosani: al 60% è "cemento" (errore trovato).
IDRATAZIONE_FARINA = {
    "segale":        {"min": 75, "max": 90, "nota": "La segale assorbe via pentosani, non glutine. Sotto il 70% è cemento. Controllare l'acidificazione (madre) per bloccare l'alfa-amilasi."},
    "grano integrale": {"min": 75, "max": 85, "nota": "La crusca taglia il glutine e assorbe per igroscopicità. Serve più acqua del bianco."},
    "integrale":     {"min": 75, "max": 85, "nota": "La crusca assorbe acqua: idratazione alta."},
    "semola":        {"min": 65, "max": 75, "nota": "Rimacinata di grano duro. Richiede autolisi prolungata."},
    "grano tenero forte": {"min": 70, "max": 85, "nota": "Farina di forza (W 280-350): regge idratazioni alte, lunghe lievitazioni."},
    "grano tenero debole": {"min": 55, "max": 60, "nota": "Farina debole (W 150-200): idratazione bassa, impasti diretti brevi."},
    "manitoba":      {"min": 70, "max": 80, "nota": "Farina di forza: alta idratazione, lievitazioni lunghe."},
    "00":            {"min": 58, "max": 65, "nota": "Farina 00 media: pizza/pane comune. Dipende dalla forza (W)."},
    "farro":         {"min": 65, "max": 75, "nota": "Glutine fragile: impastare poco, idratazione media-alta."},
}

# ── BAKERY: metodi di lievitazione (fonte: Hamelman, Modernist Bread) ──
METODI_LIEVITAZIONE = {
    "diretta":     {"tempo": "2-4h a temperatura ambiente", "lievito": "1.5-2.5% lievito di birra", "nota": "Metodo veloce, meno aroma. Per pane comune same-day."},
    "biga":        {"tempo": "16-18h a 18°C", "lievito": "1% lievito su biga (44-45% acqua)", "nota": "Pre-impasto secco italiano. A 24h/temp ambiente va in acidità acetica distruttiva."},
    "poolish":     {"tempo": "12-15h a temp ambiente (o 1-2h con più lievito)", "lievito": "0.1% a 12-15h, 2.5% a 1-2h", "nota": "Pre-impasto liquido 1:1. Temperatura impasto finale 23-24°C."},
    "lievito madre": {"tempo": "8-24h secondo maturazione", "lievito": "rinfresco 1:1:0.5 (madre:farina:acqua)", "nota": "pH pre-impasto target 4.1-4.3. Tempi dipendono da forza e temperatura della madre."},
    "freddo":      {"tempo": "24-72h in frigo a 4°C", "lievito": "0.3-0.8% lievito", "nota": "Maturazione lunga a freddo: massimo aroma e digeribilità (pizza contemporanea)."},
}

# ── BAR: diluizione per tecnica (fonte: Dave Arnold "Liquid Intelligence") ──
# Errore trovato: Negroni sbagliato con "acqua frizzante" invece di spumante.
DILUIZIONE_TECNICA = {
    "stirred":  {"min": 20, "max": 25, "nota": "Drink mescolati (Martini, Manhattan, Negroni): ~20-25% acqua aggiunta sul volume. Formula Arnold."},
    "shaken":   {"min": 35, "max": 42, "nota": "Drink shakerati: diluizione più aggressiva (collasso del ghiaccio), 35-42% acqua."},
    "build":    {"min": 10, "max": 20, "nota": "Costruiti nel bicchiere (Old Fashioned, Spritz): diluizione bassa, controllata dal ghiaccio nel tempo."},
    "throwing": {"min": 25, "max": 32, "nota": "Tecnica del lancio: raffredda e ossigena, diluizione media."},
}

# ── BAR: temperatura di servizio ──
TEMP_SERVIZIO_DRINK = {
    "up":       {"min": -4, "max": 2, "nota": "Servito senza ghiaccio (coppa): freddissimo, -4/+2°C."},
    "rocks":    {"min": 2, "max": 6, "nota": "Sul ghiaccio: 2-6°C, si diluisce nel tempo."},
    "highball": {"min": 4, "max": 8, "nota": "Long drink: 4-8°C, servito con ghiaccio abbondante."},
}

# ── BAR: cocktail IBA canonici con proporzioni VERE (estratto — i più comuni) ──
# Fonte: IBA Official Cocktails. Le PROPORZIONI non sono copyright (sono dati/formule).
COCKTAIL_IBA = {
    "negroni":          {"ricetta": "30ml gin, 30ml vermouth rosso, 30ml bitter Campari", "tecnica": "stirred", "note": "Parti uguali 1:1:1. Guarnizione arancia."},
    "negroni sbagliato": {"ricetta": "30ml bitter Campari, 30ml vermouth rosso, 60ml spumante brut/prosecco", "tecnica": "build", "note": "IL NEGRONI SBAGLIATO HA SPUMANTE, NON ACQUA FRIZZANTE. Nato sostituendo il gin col prosecco."},
    "americano":        {"ricetta": "30ml Campari, 30ml vermouth rosso, spruzzo di soda", "tecnica": "build", "note": "L'Americano ha la soda; il Negroni sbagliato ha lo spumante. Non confonderli."},
    "martini":          {"ricetta": "60ml gin, 10ml vermouth dry", "tecnica": "stirred", "note": "Rapporto variabile fino a 6:1. Oliva o scorza di limone."},
    "manhattan":        {"ricetta": "50ml rye/bourbon, 20ml vermouth rosso, 2 dash Angostura", "tecnica": "stirred", "note": "Ciliegia. Diluizione stirred 20-25%."},
    "old fashioned":    {"ricetta": "45ml bourbon/rye, 1 zolletta zucchero, 2 dash Angostura", "tecnica": "build", "note": "Costruito sul ghiaccio, scorza d'arancia."},
    "daiquiri":         {"ricetta": "60ml rum bianco, 20ml succo lime, 15ml sciroppo zucchero", "tecnica": "shaken", "note": "Shaken, diluizione 35-42%. Fresco e bilanciato."},
    "margarita":        {"ricetta": "50ml tequila, 20ml Cointreau, 15ml succo lime", "tecnica": "shaken", "note": "Bordo sale opzionale."},
    "spritz":           {"ricetta": "60ml Aperol, 90ml prosecco, spruzzo soda", "tecnica": "build", "note": "3-2-1: prosecco-Aperol-soda. Fetta d'arancia."},
    "aperol spritz":    {"ricetta": "60ml Aperol, 90ml prosecco, spruzzo soda", "tecnica": "build", "note": "Servire con ghiaccio abbondante e arancia."},
}


def grounding_per_richiesta(richiesta, disciplina):
    """Restituisce i parametri VERI pertinenti alla richiesta, da iniettare nel prompt del generatore
    come ancora di verità. Impedisce gli errori catastrofici (segale 60%, Negroni senza spumante)."""
    r = (richiesta or "").lower()
    d = (disciplina or "").lower()
    note = []
    # BAKERY: rilevo il tipo di farina
    if d in ("panificazione", "pasticceria") or any(w in r for w in ("pane", "pizza", "focaccia", "impasto", "lievitat")):
        for farina, par in IDRATAZIONE_FARINA.items():
            if farina in r:
                note.append(f"IDRATAZIONE {farina.upper()}: {par['min']}-{par['max']}%. {par['nota']}")
        for metodo, par in METODI_LIEVITAZIONE.items():
            if metodo in r:
                note.append(f"LIEVITAZIONE {metodo.upper()}: {par['tempo']}, {par['lievito']}. {par['nota']}")
    # BAR: rilevo il cocktail o la tecnica
    if d == "bar" or any(w in r for w in ("cocktail", "drink", "negroni", "spritz", "martini", "daiquiri")):
        for nome, par in COCKTAIL_IBA.items():
            if nome in r:
                note.append(f"COCKTAIL {nome.upper()} (IBA): {par['ricetta']}. Tecnica: {par['tecnica']}. {par['note']}")
        for tecnica, par in DILUIZIONE_TECNICA.items():
            if tecnica in r:
                note.append(f"DILUIZIONE {tecnica.upper()}: {par['min']}-{par['max']}%. {par['nota']}")
    return note
