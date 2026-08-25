# knowledge_tecnico.py
# KNOWLEDGE TECNICO VERIFICATO — le regole del mestiere coi numeri, controllate su fonti food science.
# Serve da GROUNDING: viene iniettato nel prompt PRIMA che l'AI generi, così le ricette nascono
# dentro regole vere invece che su plausibilità inventata (es. il burro del risotto).
#
# METODO: ogni regola è verificata su fonti (McGee "On Food and Cooking", food science, pratica
# professionale documentata). NON inventata dall'AI. Scritta con parole nostre, mai copiata.
# Ogni regola ha: chiave (parole che attivano la regola), testo (la regola col numero e il perché).

# Regole per parola-chiave: se la richiesta o gli ingredienti contengono la chiave, la regola entra nel prompt.
REGOLE_TECNICHE = {
    "risotto": (
        "MANTECATURA (verificato): il burro si aggiunge FREDDO di frigo (anche brevemente dal freezer), "
        "a fuoco SPENTO. Lo shock termico tra riso caldo e burro freddo rilascia il latticello e crea "
        "l'emulsione stabile del 'risotto all'onda'. L'emulsionante vero è l'AMIDO rilasciato dal riso, "
        "che lega grasso e liquido. MAI dire che il burro freddo 'non emulsiona': è il contrario, il burro "
        "freddo emulsiona MEGLIO perché si incorpora gradualmente. Riso: Carnaroli o Arborio (ricchi di "
        "amilopectina). Tostatura del riso prima del brodo. Brodo caldo un mestolo alla volta."
    ),
    "mantecatura": (
        "MANTECATURA (verificato): fat + acqua + amido + agitazione + fuoco spento. Il grasso (burro freddo, "
        "formaggio) va incorporato a fuoco spento; l'amido (del riso o dell'acqua di pasta) è l'emulsionante. "
        "Burro freddo per shock termico. Troppo calore o burro già sciolto = l'emulsione 'unge' invece di legare."
    ),
    "cacio e pepe": (
        "CACIO E PEPE (verificato): l'emulsione la fa l'AMIDO dell'acqua di cottura della pasta col pecorino. "
        "Il punto critico è la TEMPERATURA: il pecorino va mantecato con acqua di pasta TIEPIDA (sotto ~65°C), "
        "non bollente, altrimenti le proteine del formaggio coagulano e si formano grumi. Acqua di pasta "
        "ricca di amido (poca acqua, molto amido). Fuori dal fuoco o fiamma bassissima."
    ),
    "carbonara": (
        "CARBONARA (verificato): la crema è un'emulsione di tuorlo + grasso del guanciale + amido dell'acqua "
        "di pasta. Le uova NON devono cuocere: si mantecano FUORI dal fuoco o a fiamma spenta, altrimenti "
        "si rapprendono in frittata. Temperatura di coagulazione del tuorlo ~65-70°C: stare sotto."
    ),
    "maionese": (
        "MAIONESE (verificato): emulsione olio-in-acqua stabilizzata dalla LECITINA del tuorlo. L'olio va "
        "aggiunto LENTAMENTE all'inizio (a filo/goccia), poi si può accelerare. Se impazzisce (si separa): "
        "troppo olio troppo in fretta; si recupera ripartendo da un nuovo tuorlo (o poca senape/acqua) e "
        "aggiungendo la maionese impazzita lentamente. Ingredienti a temperatura ambiente aiutano."
    ),
    "carne": (
        "COTTURA CARNE (verificato): la reazione di Maillard (crosta, sapore) parte in modo significativo "
        "sopra i ~140-150°C in superficie. Il RIPOSO dopo la cottura (5-10 min per tagli piccoli, di più "
        "per grandi) permette ai succhi di ridistribuirsi: tagliare subito li fa colare. Temperature interne "
        "indicative: manzo al sangue ~50-52°C, media ~57-60°C, ben cotta 68°C+. Maiale/pollame per sicurezza "
        "~72-75°C al cuore."
    ),
    "bistecca": (
        "BISTECCA (verificato): padella/griglia ROVENTE per la crosta (Maillard sopra ~150°C). Carne a "
        "temperatura ambiente prima. RIPOSO 5-10 min dopo la cottura prima di tagliare (i succhi si "
        "ridistribuiscono). Manzo: al sangue ~50-52°C interni, media ~57-60°C. Non pungere con la forchetta."
    ),
    "brasato": (
        "BRASATO / STUFATO (verificato): taglio ricco di COLLAGENE (muscoli lavorati). Il collagene si scioglie "
        "in gelatina tra ~71-93°C interni, ma serve TEMPO (ore) a bassa temperatura. Cottura lenta e umida. "
        "Troppo alta e veloce = la carne resta dura e secca. La gelatina dà la morbidezza fondente."
    ),
    "lievitazione": (
        "LIEVITAZIONE / IMPASTO (verificato, logica Tafuri): la TEMPERATURA FINALE dell'impasto governa la "
        "fermentazione e si CALCOLA prima, non si misura dopo. Formula acqua: T°acqua = (T°finale impasto × 3) "
        "− (T°ambiente + T°farina + T°impastatrice). L'impastatrice scalda: spirale +5-8°C, braccia tuffanti "
        "+4-6°C, planetaria +10-15°C. Target: impasto diretto 24-26°C (fermentazione veloce, profilo dolce); "
        "puntata lunga/freddo 20-22°C (più lento, profilo acido); lievito madre ~24°C. Bassa T + impasto solido "
        "→ acetico/pungente; T moderata + idratato → lattico/dolce."
    ),
    "pane": (
        "PANE (verificato): la temperatura dell'impasto si calcola prima (vedi lievitazione). Idratazione "
        "tipica 60-75%. Il glutine si sviluppa con l'impasto; l'autolisi (farina+acqua a riposo 20-40 min "
        "prima del sale) facilita. Cottura in forno molto caldo (230-250°C) con vapore iniziale per la crosta."
    ),
    "pizza": (
        "PIZZA NAPOLETANA (verificato): forno 430-485°C, cottura 60-90 secondi. L'alta temperatura fa "
        "esplodere l'acqua dell'impasto in vapore (cornicione gonfio) e dà la leopardatura (Maillard) prima "
        "che il centro secchi. Impasto ad alta idratazione, lunga fermentazione."
    ),
    "emulsione": (
        "EMULSIONE (verificato): due liquidi che non si mescolano (grasso/acqua) tenuti insieme da un "
        "EMULSIONANTE (lecitina del tuorlo, amido, senape, gelatina) e da AGITAZIONE. La fase dispersa va "
        "aggiunta lentamente. Calore eccessivo o aggiunta troppo rapida rompono l'emulsione."
    ),
    "frittura": (
        "FRITTURA (verificato): olio a 170-180°C per la maggior parte delle fritture (fino a 190°C per "
        "croccantezza rapida). Sotto i 160°C il cibo assorbe olio e viene unto; sopra i 190-200°C l'olio "
        "degrada e fuma. Non sovraccaricare (abbassa la temperatura). Cibo asciutto in superficie."
    ),
    "caramello": (
        "CARAMELLO / ZUCCHERO (verificato): lo zucchero fonde a ~160°C e caramellizza tra 160-180°C "
        "(dorato → ambrato). Sopra i ~190°C diventa amaro e brucia. Stadi dello zucchero cotto per pasticceria: "
        "filo 110-112°C, palla morbida 116-120°C, palla dura 121-130°C, caramello 160-170°C."
    ),
    "meringa": (
        "MERINGA / ALBUMI (verificato): gli albumi montano meglio a temperatura ambiente; una traccia di "
        "grasso o tuorlo impedisce il montaggio. Lo zucchero va aggiunto gradualmente a schiuma già formata. "
        "Un pizzico di acido (cremor tartaro, limone) stabilizza. Meringa italiana: sciroppo a 118-121°C."
    ),
    "cioccolato": (
        "TEMPERAGGIO CIOCCOLATO (verificato): serve a formare i cristalli beta stabili (lucido, croccante, "
        "non striato). Fondente: fusione ~45-50°C, raffreddamento ~27-28°C, risalita lavorazione ~31-32°C. "
        "Al latte e bianco: temperature di 1-2°C più basse. Fuori curva = affiora il burro di cacao (fat bloom)."
    ),
}

# Regole per DISCIPLINA (entrano sempre per quella disciplina, oltre a quelle per parola-chiave)
REGOLE_DISCIPLINA = {
    "panificazione": (
        "La temperatura finale dell'impasto è il numero che governa tutto e si calcola PRIMA. "
        "Idratazione in percentuale sul peso farina. Sale 2-2.2% sul peso farina."
    ),
    "pasticceria": (
        "La pasticceria è precisione: pesare in grammi, temperature esatte. Zucchero, uova e grassi hanno "
        "punti critici di temperatura precisi (coagulazione uova ~65-70°C, stadi zucchero, temperaggio)."
    ),
}


def regole_per_richiesta(richiesta, disciplina="cucina", ingredienti=None):
    """Ritorna le regole tecniche pertinenti a una richiesta, da iniettare nel prompt.
    Cerca le parole-chiave nella richiesta e negli ingredienti."""
    testo = (richiesta or "").lower()
    if ingredienti:
        testo += " " + " ".join(str(i).lower() for i in ingredienti)
    regole = []
    viste = set()
    for chiave, regola in REGOLE_TECNICHE.items():
        if chiave in testo and regola not in viste:
            regole.append(regola)
            viste.add(regola)
    # regola di disciplina
    rd = REGOLE_DISCIPLINA.get(disciplina)
    if rd:
        regole.append(rd)
    return regole


def blocco_grounding(richiesta, disciplina="cucina", ingredienti=None):
    """Costruisce il blocco di testo da iniettare nel prompt. Vuoto se nessuna regola pertinente."""
    regole = regole_per_richiesta(richiesta, disciplina, ingredienti)
    if not regole:
        return ""
    corpo = "\n".join(f"- {r}" for r in regole)
    return (
        "\n\nKNOWLEDGE TECNICO VERIFICATO (regole del mestiere controllate su fonti di food science — "
        "DEVI rispettarle, sono la verità tecnica; se contraddicono ciò che 'suona giusto', vale questa lista):\n"
        f"{corpo}\n"
    )


# ── GROUNDING BAR: regole tecniche dei cocktail (mescolato vs shakerato, diluizione) ──
REGOLE_BAR = {
    "negroni": "NEGRONI: si MESCOLA nel mixing glass con ghiaccio (mai shakerato: è tutto alcolico, lo shake lo rovina). Parti uguali gin/vermouth rosso/bitter Campari (30-30-30ml). Guarnizione: fetta d'arancia. Diluizione dalla mescolata ~20%.",
    "martini": "MARTINI: si MESCOLA (stirred), mai shakerato (lo shake intorbidisce e diluisce troppo un drink alcolico). Gin + vermouth dry, guarnizione oliva o scorza di limone.",
    "manhattan": "MANHATTAN: si MESCOLA. Rye/bourbon + vermouth rosso + angostura. Guarnizione: ciliegia.",
    "old fashioned": "OLD FASHIONED: si costruisce nel bicchiere (build), si MESCOLA. Bourbon + zolletta di zucchero + angostura + poca acqua. Ghiaccio grande (fonde lento).",
    "daiquiri": "DAIQUIRI: si SHAKERA (ha succo di lime: gli agrumi vanno shakerati per emulsionare e raffreddare). Rum bianco + lime + zucchero. Doppio colino.",
    "margarita": "MARGARITA: si SHAKERA (ha lime). Tequila + triple sec + lime. Bordo di sale opzionale.",
    "whiskey sour": "WHISKEY SOUR: si SHAKERA. Con albume = DRY SHAKE prima (senza ghiaccio, per montare la schiuma) poi shake con ghiaccio. Bourbon + limone + zucchero + albume.",
    "espresso martini": "ESPRESSO MARTINI: si SHAKERA forte (l'espresso fresco crea la schiuma/crema in superficie). Vodka + caffè espresso + liquore al caffè. Va servito con la cremina.",
    "aviation": "AVIATION: si SHAKERA (ha limone). Gin + maraschino + crème de violette + succo di limone. Colore viola tenue dalla violette. NON è verde.",
    "mojito": "MOJITO: pesta delicatamente la menta (non stracciarla, rilascia amaro), build nel bicchiere. Rum + lime + zucchero + menta + soda. Ghiaccio tritato.",
    "regola_generale_bar": "REGOLA BAR: si SHAKERANO i drink con succhi/agrumi/uovo/panna (serve emulsione e aerazione); si MESCOLANO i drink solo alcolici (gin, vermouth, bitter, whiskey: lo shake li intorbidisce). La DILUIZIONE dal ghiaccio è parte della ricetta, non un difetto: un cocktail ben fatto è diluito ~20-25%. Ghiaccio grande fonde lento (diluisce meno), tritato fonde veloce.",
}


def blocco_grounding_bar(richiesta):
    """Regole tecniche del bar pertinenti alla richiesta."""
    req = (richiesta or "").lower()
    regole = []
    for chiave, regola in REGOLE_BAR.items():
        if chiave == "regola_generale_bar":
            continue
        if chiave in req:
            regole.append(regola)
    # la regola generale entra sempre per i drink
    regole.append(REGOLE_BAR["regola_generale_bar"])
    corpo = "\n".join(f"- {r}" for r in regole)
    return (
        "\n\nKNOWLEDGE TECNICO BAR (regole verificate — mescolato vs shakerato, diluizione, ghiaccio. "
        "RISPETTALE: es. il Negroni si MESCOLA, mai shakerato; niente 'acqua tonica' dove non c'è):\n"
        f"{corpo}\n"
    )
