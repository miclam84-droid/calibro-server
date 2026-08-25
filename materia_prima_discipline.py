# materia_prima_discipline.py
# Materia prima DEDICATA per gelateria, caffè, pasticceria, panificazione.
# Schede complete (aroma, profilo, applicazioni) = canovaccio di ogni disciplina.
# Diventano nodi Ingrediente col campo domini[], così entrano nel flavour network.

MATERIA_PRIMA_DISC = [
    # ═══ GELATERIA ═══
    {"id": "ing-pasta-pistacchio", "nome": "Pasta di pistacchio", "domini": ["gelateria", "pasticceria"], "aroma": "pistacchio tostato, dolce, burroso", "profilo": "pistacchi macinati 100%, aromatizzante puro", "applicazioni": "gelato al pistacchio, creme, farciture"},
    {"id": "ing-pasta-nocciola-gel", "nome": "Pasta di nocciola (gelato)", "domini": ["gelateria", "pasticceria"], "aroma": "nocciola tostata, intensa", "profilo": "nocciole IGP macinate, aromatizzante", "applicazioni": "gelato gianduia, creme"},
    {"id": "ing-latte-cocco-gel", "nome": "Latte di cocco (gelato)", "domini": ["gelateria"], "aroma": "cocco dolce, tropicale", "profilo": "base vegetale per gelati e sorbetti", "applicazioni": "gelato vegano, sorbetti tropicali"},
    {"id": "ing-fibra-gelato", "nome": "Fibra vegetale (gelato)", "domini": ["gelateria"], "aroma": "neutro", "profilo": "fibre che trattengono acqua e danno cremosità senza grassi", "applicazioni": "gelati leggeri, struttura"},
    {"id": "ing-albume-polvere", "nome": "Albume in polvere", "domini": ["gelateria", "pasticceria"], "aroma": "neutro", "profilo": "proteine che danno montabilità e struttura", "applicazioni": "meringhe, gelati, spume"},
    {"id": "ing-zucchero-invertito", "nome": "Zucchero invertito", "domini": ["gelateria", "pasticceria"], "aroma": "dolce, più del saccarosio", "profilo": "abbassa il punto di congelamento, dà morbidezza e anti-cristallizzazione", "applicazioni": "gelato morbido, lievitati soffici"},
    {"id": "ing-maltodestrine", "nome": "Maltodestrine", "domini": ["gelateria"], "aroma": "poco dolce, neutro", "profilo": "danno corpo e solidi senza dolcezza eccessiva", "applicazioni": "bilanciamento mix gelato, polveri"},
    # ═══ CAFFÈ ═══
    {"id": "ing-caffe-etiopia", "nome": "Caffè Etiopia (single origin)", "domini": ["caffe"], "aroma": "floreale, agrumi, bergamotto, tè", "profilo": "arabica lavata o naturale, acidità brillante", "applicazioni": "filtro specialty, espresso monorigine"},
    {"id": "ing-caffe-brasile", "nome": "Caffè Brasile (single origin)", "domini": ["caffe"], "aroma": "cioccolato, nocciola, dolce, corpo", "profilo": "arabica naturale, bassa acidità, corposo", "applicazioni": "blend espresso, base cremosa"},
    {"id": "ing-caffe-colombia", "nome": "Caffè Colombia (single origin)", "domini": ["caffe"], "aroma": "caramello, frutta rossa, equilibrato", "profilo": "arabica lavata, acidità media, dolce", "applicazioni": "espresso, filtro"},
    {"id": "ing-caffe-guatemala", "nome": "Caffè Guatemala (single origin)", "domini": ["caffe"], "aroma": "cioccolato, spezie, agrumi", "profilo": "arabica d'altura, complesso", "applicazioni": "espresso strutturato"},
    {"id": "ing-latte-microfoam", "nome": "Latte per microfoam", "domini": ["caffe"], "aroma": "lattico dolce", "profilo": "latte intero, proteine per la crema montata a vapore", "applicazioni": "cappuccino, latte art, flat white"},
    {"id": "ing-cacao-caffe", "nome": "Cacao in polvere (caffetteria)", "domini": ["caffe", "pasticceria"], "aroma": "cacao amaro, tostato", "profilo": "cacao magro per guarnizioni", "applicazioni": "cappuccino, marocchino, mocha"},
    # ═══ PASTICCERIA ═══
    {"id": "ing-cioccolato-latte", "nome": "Cioccolato al latte", "domini": ["pasticceria"], "aroma": "cacao dolce, latte, caramello", "profilo": "cacao + latte + zucchero, fonde morbido", "applicazioni": "ganache dolci, coperture, praline"},
    {"id": "ing-cioccolato-bianco", "nome": "Cioccolato bianco", "domini": ["pasticceria"], "aroma": "burro di cacao, vaniglia, latte", "profilo": "burro di cacao + latte + zucchero, no cacao magro", "applicazioni": "ganache, mousse, decori"},
    {"id": "ing-glassa-specchio", "nome": "Glassa a specchio", "domini": ["pasticceria"], "aroma": "dolce neutro", "profilo": "gelatina + zuccheri per finitura lucida", "applicazioni": "copertura torte moderne, entremet"},
    {"id": "ing-pectina", "nome": "Pectina", "domini": ["pasticceria"], "aroma": "neutro", "profilo": "gelificante da frutta, agisce con zucchero e acido", "applicazioni": "confetture, gelée, glasse frutta"},
    {"id": "ing-fondente-cioccolato-copertura", "nome": "Cioccolato di copertura", "domini": ["pasticceria"], "aroma": "cacao intenso", "profilo": "alta percentuale di burro di cacao, per temperaggio", "applicazioni": "cioccolatini, decori, immersioni"},
    {"id": "ing-farina-mandorle", "nome": "Farina di mandorle", "domini": ["pasticceria"], "aroma": "mandorla dolce", "profilo": "mandorle macinate, base per impasti senza glutine", "applicazioni": "macaron, frangipane, dacquoise"},
    {"id": "ing-vaniglia-bacca", "nome": "Vaniglia (bacca)", "domini": ["pasticceria", "gelateria"], "aroma": "vaniglia intensa, floreale, dolce", "profilo": "bacca di vaniglia bourbon, semi neri", "applicazioni": "creme, gelato fiordilatte, impasti"},
    # ═══ PANIFICAZIONE ═══
    {"id": "ing-farina-manitoba", "nome": "Farina Manitoba (W380+)", "domini": ["panificazione"], "aroma": "neutro, cerealicolo", "profilo": "alta forza (W alto), tanto glutine, lunghe lievitazioni", "applicazioni": "panettone, lievitati, impasti a lunga maturazione"},
    {"id": "ing-farina-tipo1", "nome": "Farina tipo 1", "domini": ["panificazione"], "aroma": "cerealicolo, rustico", "profilo": "semi-integrale, più fibra e sapore, W medio", "applicazioni": "pane rustico, pizza contemporanea"},
    {"id": "ing-farina-segale", "nome": "Farina di segale", "domini": ["panificazione"], "aroma": "intenso, rustico, leggermente acido", "profilo": "poco glutine, tanta fibra, si lega al lievito madre", "applicazioni": "pane nero, pane di segale, pane tedesco"},
    {"id": "ing-farina-farro", "nome": "Farina di farro", "domini": ["panificazione"], "aroma": "nocciolato, cerealicolo", "profilo": "cereale antico, glutine tenace ma fragile", "applicazioni": "pane di farro, focacce rustiche"},
    {"id": "ing-lievito-madre-liquido", "nome": "Lievito madre liquido (li.co.li.)", "domini": ["panificazione"], "aroma": "acido lattico, yogurt", "profilo": "coltura al 100% idratazione, più acido lattico che acetico", "applicazioni": "pane, pizza, lievitati dolci"},
    {"id": "ing-malto-diastasico", "nome": "Malto diastasico", "domini": ["panificazione"], "aroma": "dolce, maltato", "profilo": "enzimi che scindono l'amido in zuccheri, nutrono il lievito e danno colore", "applicazioni": "pane, bagel, crosta dorata"},
    {"id": "ing-semola-rimacinata", "nome": "Semola rimacinata di grano duro", "domini": ["panificazione"], "aroma": "cerealicolo, dolce", "profilo": "grano duro, glutine tenace, colore giallo", "applicazioni": "pane pugliese, pane di Altamura, orecchiette"},
    {"id": "ing-glutine-vitale", "nome": "Glutine di frumento vitale", "domini": ["panificazione"], "aroma": "neutro", "profilo": "proteine pure per rinforzare farine deboli", "applicazioni": "correzione impasti, pane ad alta idratazione"},
]
