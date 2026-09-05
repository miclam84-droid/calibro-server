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

# ── BAKERY: formule madre (baker's percentage, fonte: Hamelman, Modernist Bread) ──
FORMULE_PANE = {
    "baguette":      {"formula": "farina 100%, acqua 65-68%, sale 2%, lievito 0.8-1% (o poolish)", "nota": "Poolish per aroma. Lame decise, forno 240°C con vapore."},
    "ciabatta":      {"formula": "farina 100%, acqua 75-85%, sale 2.2%, biga 30-40%", "nota": "Alta idratazione, impasto molle, pieghe non impastamento. Alveolatura aperta."},
    "pane comune":   {"formula": "farina 100%, acqua 62-68%, sale 2%, lievito 1.5-2%", "nota": "Pane quotidiano diretto. Cottura 220-230°C."},
    "focaccia":      {"formula": "farina 100%, acqua 70-80%, sale 2%, olio 5-8%, lievito 1%", "nota": "Alta idratazione, olio in impasto e superficie. Fossette e salamoia."},
    "sourdough":     {"formula": "farina 100%, acqua 75-85%, sale 2%, lievito madre 20%", "nota": "Stile San Francisco. Lievito madre liquido, lunga maturazione, crosta spessa."},
    "pane di segale": {"formula": "farina segale 100%, acqua 75-90%, sale 2%, madre acida", "nota": "Impasto denso e appiccicoso. L'acidità blocca l'alfa-amilasi. Cottura lunga a calore decrescente."},
    "coppia ferrarese": {"formula": "farina forte 100%, acqua 45-50%, sale 2%, strutto 5%, lievito", "nota": "Pasta dura, idratazione RIGIDA bassa. Forma a nastro attorcigliato."},
    "pane pugliese": {"formula": "semola rimacinata 100%, acqua 70-75%, sale 2%, madre", "nota": "Semola di grano duro, autolisi lunga, mollica gialla."},
    "brioche":       {"formula": "farina 100%, uova 50%, burro 50-60%, zucchero 12-15%, latte 20%, lievito", "nota": "Grande lievitato arricchito. Burro freddo incorporato a impasto sviluppato."},
    "croissant":     {"formula": "farina 100%, acqua 50%, burro tourage 50%, zucchero 10%, lievito", "nota": "Sfogliatura: 3 pieghe da 3. Burro plastico a 14-16°C. Lievitazione finale 26-28°C."},
    "panettone":     {"formula": "farina forte W380 100%, madre 30%, burro 25%, tuorli 25%, zucchero 25%, sospensione uvetta/canditi", "nota": "Doppio impasto, lievito madre, 2 giorni. Il grande lievitato più difficile."},
}


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

# ── BAR: parametri tecnici avanzati (fonte: Dave Arnold, pratica professionale) ──
PARAMETRI_BAR = {
    "sciroppo semplice":   {"brix": "1:1 = ~50 Brix, 2:1 = ~65 Brix", "nota": "1:1 (zucchero:acqua) più versatile; 2:1 (rich) più stabile e denso, meno diluizione nel drink."},
    "carbonazione":        {"target": "2.5-4 volumi CO2 (30-55 psi a 4°C)", "nota": "Per drink alla spina/frizzanti. Più freddo = più CO2 disciolta. 3-4 volumi per un frizzante deciso."},
    "acidita drink":       {"target": "0.7-0.9% acidità titolabile nel drink finito", "nota": "Bilanciamento sour: il lime è ~6% acido, il limone ~5%. Un sour equilibrato chiude intorno a 0.8%."},
    "cordiale":            {"target": "acido citrico/malico 5-6% per simulare l'agrume, zucchero 50-66%", "nota": "Cordiale = agrume stabile e shelf-stable. Bilanciare acido e zucchero come il succo fresco."},
    "shrub":               {"target": "aceto 1:1 con frutta+zucchero, macerazione 2-7 giorni", "nota": "Conserva acida di frutta. L'aceto sostituisce parte dell'agrume."},
    "shake time":          {"target": "10-15 secondi di shake energico", "nota": "Tempo di shake per raffreddamento e diluizione ottimali. Oltre 15s non migliora, diluisce solo."},
}


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
    "boulevardier":     {"ricetta": "45ml bourbon, 30ml vermouth rosso, 30ml Campari", "tecnica": "stirred", "note": "Il Negroni col whisky. Scorza d'arancia o ciliegia."},
    "mojito":           {"ricetta": "45ml rum bianco, 30ml lime, 6 foglie menta, 2 cucchiaini zucchero, soda", "tecnica": "build", "note": "Pestare menta e zucchero delicatamente, mai stracciare le foglie."},
    "whisky sour":      {"ricetta": "45ml bourbon, 30ml succo limone, 15ml sciroppo zucchero, albume (opz.)", "tecnica": "shaken", "note": "Dry shake se con albume. Diluizione shaken 35-42%."},
    "cosmopolitan":     {"ricetta": "40ml vodka citron, 15ml Cointreau, 15ml lime, 30ml succo mirtillo rosso", "tecnica": "shaken", "note": "Scorza di limone flambé opzionale."},
    "espresso martini": {"ricetta": "50ml vodka, 30ml caffè espresso, 10ml sciroppo zucchero, 10ml liquore al caffè", "tecnica": "shaken", "note": "Espresso caldo fresco, shakerare forte per la schiuma."},
    "gin tonic":        {"ricetta": "50ml gin, 100-150ml tonica", "tecnica": "build", "note": "Ghiaccio abbondante, la tonica fredda. Guarnizione secondo le botaniche del gin."},
    "aviation":         {"ricetta": "45ml gin, 15ml maraschino, 15ml succo limone, 1 cucchiaino Crème de Violette", "tecnica": "shaken", "note": "Colore azzurro dalla violetta. Ciliegia."},
    "mai tai":          {"ricetta": "30ml rum ambrato, 30ml rum scuro, 15ml orange curaçao, 15ml orgeat, 30ml lime", "tecnica": "shaken", "note": "Menta e lime a guarnire. Bilanciamento agrume-mandorla."},
    "penicillin":       {"ricetta": "60ml scotch, 22ml lime, 22ml sciroppo miele-zenzero, float di scotch torbato", "tecnica": "shaken", "note": "Zenzero fresco nello sciroppo. Il torbato in superficie."},
    "paloma":           {"ricetta": "50ml tequila, 100ml soda al pompelmo, 15ml lime, pizzico sale", "tecnica": "build", "note": "Più bevuto della Margarita in Messico."},
    "french 75":        {"ricetta": "30ml gin, 15ml succo limone, 15ml sciroppo zucchero, 60ml champagne", "tecnica": "shaken+top", "note": "Shakerare gin/limone/zucchero, poi champagne. Flûte."},
    "bellini":          {"ricetta": "50ml purea di pesca bianca, 100ml prosecco", "tecnica": "build", "note": "Inventato all'Harry's Bar di Venezia. Pesca bianca fresca."},
    "moscow mule":      {"ricetta": "45ml vodka, 15ml lime, 120ml ginger beer", "tecnica": "build", "note": "Servito in tazza di rame. Ghiaccio abbondante."},
    "sidecar":          {"ricetta": "50ml cognac, 20ml Cointreau, 20ml succo limone", "tecnica": "shaken", "note": "Bordo zucchero opzionale."},
    "mint julep":       {"ricetta": "60ml bourbon, 4-5 foglie menta, 1 cucchiaino sciroppo zucchero, ghiaccio tritato", "tecnica": "build", "note": "Tazza di metallo ghiacciata, ghiaccio tritato a montagnetta."},
    "sazerac":          {"ricetta": "50ml rye, 1 zolletta zucchero, 2 dash Peychaud's, risciacquo di assenzio", "tecnica": "stirred", "note": "Bicchiere risciacquato con assenzio. Scorza di limone (non nel drink)."},
    "vieux carre":      {"ricetta": "30ml rye, 30ml cognac, 30ml vermouth rosso, 1 cucchiaino Benedictine, dash Peychaud+Angostura", "tecnica": "stirred", "note": "Cocktail di New Orleans, stratificato e complesso."},
    "tommy's margarita": {"ricetta": "45ml tequila, 22ml lime, 22ml agave", "tecnica": "shaken", "note": "Margarita senza triple sec, agave al posto. Più agrumata e pulita."},
    "clover club":      {"ricetta": "45ml gin, 15ml lampone, 15ml limone, albume", "tecnica": "shaken", "note": "Dry shake per la schiuma. Sciroppo di lampone fresco."},
    "last word":        {"ricetta": "22ml gin, 22ml Chartreuse verde, 22ml maraschino, 22ml lime", "tecnica": "shaken", "note": "Parti uguali, equilibrio erbaceo-agrumato."},
    "corpse reviver":   {"ricetta": "22ml gin, 22ml Cointreau, 22ml Lillet Blanc, 22ml limone, dash assenzio", "tecnica": "shaken", "note": "Corpse Reviver #2. Assenzio nel risciacquo."},
    "hemingway daiquiri": {"ricetta": "60ml rum, 15ml maraschino, 22ml lime, 15ml pompelmo", "tecnica": "shaken", "note": "Daiquiri senza zucchero, con pompelmo e maraschino."},
    "caipirinha":       {"ricetta": "60ml cachaça, mezzo lime a spicchi, 2 cucchiaini zucchero", "tecnica": "build", "note": "Pestare lime e zucchero. Ghiaccio tritato. Cocktail brasiliano."},
    "pisco sour":       {"ricetta": "60ml pisco, 22ml lime, 22ml sciroppo, albume, dash Angostura", "tecnica": "shaken", "note": "Dry shake. Angostura in gocce sulla schiuma."},
    "bramble":          {"ricetta": "50ml gin, 22ml limone, 12ml sciroppo, 15ml crème de mûre", "tecnica": "build", "note": "La mora (mûre) colata sopra il ghiaccio tritato, effetto sanguinello."},
    "dark n stormy":    {"ricetta": "60ml rum scuro, 100ml ginger beer, 10ml lime", "tecnica": "build", "note": "Il rum scuro galleggia sul ginger beer (la 'tempesta')."},
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
        for pane, par in FORMULE_PANE.items():
            if pane in r:
                note.append(f"FORMULA {pane.upper()}: {par['formula']}. {par['nota']}")
    # BAR: rilevo il cocktail o la tecnica
    if d == "bar" or any(w in r for w in ("cocktail", "drink", "negroni", "spritz", "martini", "daiquiri")):
        for nome, par in COCKTAIL_IBA.items():
            if nome in r:
                note.append(f"COCKTAIL {nome.upper()} (IBA): {par['ricetta']}. Tecnica: {par['tecnica']}. {par['note']}")
        for tecnica, par in DILUIZIONE_TECNICA.items():
            if tecnica in r:
                note.append(f"DILUIZIONE {tecnica.upper()}: {par['min']}-{par['max']}%. {par['nota']}")
        for par_nome, par in PARAMETRI_BAR.items():
            if any(w in r for w in par_nome.split()):
                _v = par.get("brix") or par.get("target") or ""
                note.append(f"{par_nome.upper()}: {_v}. {par['nota']}")
    return note
