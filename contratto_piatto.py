"""
CONTRATTO PIATTO — Sprint 1: il vincolo che impedisce le allucinazioni del generatore
(es. 'Tiramisù Gratinato', 'Gelato saltato in padella') SENZA spegnere la generazione.

Idea: prima di generare, si classifica la famiglia del piatto richiesto. Ogni famiglia ha
tecniche/cotture INCOMPATIBILI. Il contratto viene iniettato nel prompt come vincolo, e usato
dopo per validare (red team). Se l'utente chiede una variante impossibile ('tiramisù gratinato'),
il contratto permette di aggiungere un elemento compatibile (una cialda croccante SOPRA) senza
snaturare il piatto — non di trasformarlo in qualcosa che non è.
"""

# Famiglie di piatti con le loro regole. Ogni famiglia dichiara:
# - cotture_vietate: tecniche di cottura che snaturano il piatto
# - tecniche_vietate: lavorazioni incompatibili
# - nota: vincolo in linguaggio naturale per il prompt
FAMIGLIE = {
    "dessert_freddo": {
        "esempi": ["tiramisù", "tiramisu", "panna cotta", "semifreddo", "mousse", "bavarese",
                   "cheesecake", "gelato", "sorbetto", "granita", "affogato"],
        "cotture_vietate": ["gratinare", "friggere", "saltare in padella", "grigliare", "arrostire",
                            "brasare", "bollire a lungo", "cuocere al forno ad alta temperatura"],
        "tecniche_vietate": ["impanare", "soffriggere"],
        "ingredienti_estranei": ["gambero", "gamberi", "manzo", "pollo", "pesce", "carne", "riso saltato",
                                 "cipolla", "aglio", "guanciale", "pancetta", "acciughe", "vongole"],
        "nota": "È un dessert freddo/a temperatura controllata. NON si gratina, non si frigge, "
                "non si salta in padella. Eventuali elementi croccanti vanno AGGIUNTI a parte "
                "(es. una cialda), mai cuocendo il dolce stesso. NON contiene carne, pesce o "
                "ingredienti salati (gamberi, manzo, cipolla): è un dolce.",
    },
    "cocktail": {
        "esempi": ["negroni", "spritz", "margarita", "mojito", "martini", "daiquiri", "americano",
                   "cocktail", "drink", "aperitivo alcolico", "sour", "collins", "gin tonic"],
        "cotture_vietate": ["friggere", "cuocere", "gratinare", "arrostire", "bollire", "saltare in padella"],
        "tecniche_vietate": ["impastare", "lievitare", "impanare"],
        "nota": "È un cocktail/bevanda. NON si cuoce né si frigge. Si costruisce con tecniche da bar "
                "(mescolato, shakerato, build, macerazione a freddo). Ingredienti liquidi/aromatici.",
    },
    "primo_pasta": {
        "esempi": ["carbonara", "cacio e pepe", "gricia", "amatriciana", "spaghetti", "pasta",
                   "risotto", "lasagne", "gnocchi", "tagliatelle", "orecchiette", "paccheri"],
        "cotture_vietate": ["cuocere come dolce", "congelare come gelato"],
        "tecniche_vietate": ["montare a neve", "mantecare con panna nella carbonara"],
        "nota": "È un primo piatto salato. Si cuoce la pasta/riso e si condisce. NON si trasforma "
                "in dolce né si congela come gelato.",
    },
    "carne_brasata": {
        "esempi": ["brasato", "stracotto", "spezzatino", "ossobuco", "coda alla vaccinara",
                   "guancia", "stufato", "pulled pork", "brisket"],
        "cotture_vietate": ["friggere velocemente", "servire crudo", "congelare"],
        "tecniche_vietate": [],
        "nota": "È una carne a cottura lunga e bassa (collagene→gelatina). NON si frigge veloce "
                "né si serve cruda.",
    },
    "lievitato": {
        "esempi": ["pane", "pizza", "focaccia", "baguette", "ciabatta", "brioche", "croissant",
                   "panino", "bagel", "grissini", "pandoro", "panettone"],
        "cotture_vietate": ["friggere come tempura", "servire crudo l'impasto"],
        "tecniche_vietate": ["shakerare", "mantecare"],
        "nota": "È un impasto lievitato da forno. Richiede lievitazione e cottura. NON si shakera "
                "né si serve l'impasto crudo.",
    },
    "salsa_emulsione": {
        "esempi": ["maionese", "hollandaise", "olandese", "besciamella", "vinaigrette", "pesto",
                   "salsa", "emulsione"],
        "cotture_vietate": ["far bollire l'emulsione (impazzisce)"],
        "tecniche_vietate": ["lievitare", "shakerare a caldo"],
        "nota": "È una salsa/emulsione. Va gestita a temperatura controllata: bollire rompe "
                "l'emulsione. NON si lievita.",
    },
    "frittura": {
        "esempi": ["tempura", "frittura", "fritto", "cotoletta", "milanese", "katsu", "fried chicken",
                   "falafel", "bomboloni", "zeppole"],
        "cotture_vietate": ["bollire", "cuocere al vapore come piatto finale"],
        "tecniche_vietate": ["shakerare"],
        "nota": "È una frittura. Richiede olio a temperatura corretta (160-180°C). NON si bollisce.",
    },
}


def _norm(s):
    s = (s or "").lower().strip()
    for a, b in [("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u")]:
        s = s.replace(a, b)
    return s


def classifica_famiglia(richiesta):
    """Dato il testo della richiesta, ritorna (chiave_famiglia, dict_regole) o (None, None)
    se non riconosciuta. Match sugli esempi noti."""
    r = _norm(richiesta)
    for chiave, regole in FAMIGLIE.items():
        for es in regole["esempi"]:
            if _norm(es) in r:
                return chiave, regole
    return None, None


def contratto_per_prompt(richiesta):
    """Ritorna un blocco di testo da iniettare nel prompt di generazione, che vincola l'AI a
    rispettare la famiglia del piatto. Vuoto se la famiglia non è riconosciuta (generazione libera)."""
    chiave, regole = classifica_famiglia(richiesta)
    if not regole:
        return ""
    vietate = ", ".join(regole["cotture_vietate"][:5])
    return (f"\n\nVINCOLO DI COERENZA (famiglia: {chiave}). {regole['nota']} "
            f"Tecniche/cotture VIETATE per questo piatto: {vietate}. "
            f"Se la richiesta contiene una di queste (es. 'gratinato' su un dolce freddo), NON "
            f"applicarla al piatto: al massimo aggiungi un elemento compatibile a parte, mantenendo "
            f"il piatto fedele alla sua natura.")


def valida_coerenza(richiesta, ricetta):
    """RED TEAM: dopo la generazione, verifica che la ricetta non contenga tecniche vietate per la
    sua famiglia. Ritorna {ok: bool, problemi: [..], famiglia: str}."""
    chiave, regole = classifica_famiglia(richiesta)
    if not regole:
        return {"ok": True, "problemi": [], "famiglia": None}
    problemi = []
    # controllo il procedimento e il nome per tecniche vietate
    testo = _norm(ricetta.get("nome", "") + " ")
    for passo in ricetta.get("procedimento", []):
        t = passo if isinstance(passo, str) else passo.get("testo", "")
        testo += _norm(t) + " "
    for vietata in regole["cotture_vietate"] + regole["tecniche_vietate"]:
        # cerco la radice del verbo vietato (es. 'gratin' da 'gratinare')
        radice = _norm(vietata).split()[0][:6]
        if radice and radice in testo:
            problemi.append(f"tecnica vietata per {chiave}: '{vietata}' trovata nella ricetta")
    # controllo ingredienti ESTRANEI alla famiglia (es. gamberi in un dolce)
    estranei = regole.get("ingredienti_estranei", [])
    if estranei:
        # testo di nome + ingredienti
        testo_ing = _norm(ricetta.get("nome", "") + " ")
        for ing in ricetta.get("ingredienti", []):
            nome_ing = ing.get("nome", "") if isinstance(ing, dict) else str(ing)
            testo_ing += _norm(nome_ing) + " "
        for estraneo in estranei:
            e = _norm(estraneo)
            if e and e in testo_ing:
                problemi.append(f"ingrediente estraneo alla famiglia {chiave}: '{estraneo}'")
    return {"ok": len(problemi) == 0, "problemi": problemi, "famiglia": chiave}
