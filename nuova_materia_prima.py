# nuova_materia_prima.py
# Materia prima NUOVA per le discipline con pochi ingredienti (bar, gelateria, caffè, pasticceria).
# Ogni voce è una SCHEDA: nome, dominio, aroma/profilo, applicazioni — il canovaccio per creare.
# Diventano nodi Ingrediente col campo domini[], così entrano nel flavour network.

# schema: {id, nome, domini:[], aroma, profilo, applicazioni}
MATERIA_PRIMA = [
    # ── BAR: distillati ──
    {"id": "ing-rum-bianco", "nome": "Rum bianco", "domini": ["bar"], "aroma": "canna da zucchero, vaniglia, floreale", "profilo": "distillato di melassa/succo di canna, invecchiamento breve o filtrato", "applicazioni": "daiquiri, mojito, base tiki"},
    {"id": "ing-rum-scuro", "nome": "Rum scuro", "domini": ["bar"], "aroma": "melassa, caramello, spezie, legno", "profilo": "invecchiato in botte, note di zucchero bruciato", "applicazioni": "dark 'n' stormy, mai tai, sipping"},
    {"id": "ing-whisky-scozzese", "nome": "Whisky scozzese", "domini": ["bar"], "aroma": "malto, torba, affumicato (se islay), miele", "profilo": "single malt o blended, invecchiato in botte", "applicazioni": "rob roy, penicillin, liscio"},
    {"id": "ing-bourbon", "nome": "Bourbon", "domini": ["bar"], "aroma": "mais dolce, vaniglia, caramello, quercia", "profilo": "min 51% mais, botte di rovere vergine tostata", "applicazioni": "old fashioned, manhattan, whiskey sour"},
    {"id": "ing-rye-whiskey", "nome": "Rye whiskey", "domini": ["bar"], "aroma": "segale speziata, pepe, secco", "profilo": "min 51% segale, più secco e piccante del bourbon", "applicazioni": "sazerac, manhattan classico"},
    {"id": "ing-cognac", "nome": "Cognac", "domini": ["bar"], "aroma": "uva, frutta secca, vaniglia, legno", "profilo": "acquavite di vino invecchiata (VS/VSOP/XO)", "applicazioni": "sidecar, sazerac, french connection"},
    {"id": "ing-mezcal", "nome": "Mezcal", "domini": ["bar"], "aroma": "agave affumicata, terroso, vegetale", "profilo": "agave cotta in forni interrati, distillato artigianale", "applicazioni": "naked and famous, mezcal negroni"},
    # ── BAR: vermouth e aromatizzati ──
    {"id": "ing-vermouth-rosso", "nome": "Vermouth rosso", "domini": ["bar"], "aroma": "erbe amare, caramello, spezie, china", "profilo": "vino fortificato e aromatizzato, dolce", "applicazioni": "negroni, manhattan, americano"},
    {"id": "ing-vermouth-dry", "nome": "Vermouth dry", "domini": ["bar"], "aroma": "erbe secche, floreale, agrume", "profilo": "vino fortificato secco, pallido", "applicazioni": "martini, dirty martini"},
    # ── BAR: bitter e liquori ──
    {"id": "ing-angostura", "nome": "Angostura bitter", "domini": ["bar"], "aroma": "genziana, spezie, chiodi di garofano, cannella", "profilo": "bitter concentrato aromatico, usato a gocce", "applicazioni": "old fashioned, manhattan, pisco sour"},
    {"id": "ing-orange-bitter", "nome": "Orange bitter", "domini": ["bar"], "aroma": "scorza d'arancia amara, spezie", "profilo": "bitter agli agrumi, a gocce", "applicazioni": "martini, negroni twist"},
    {"id": "ing-maraschino", "nome": "Maraschino", "domini": ["bar"], "aroma": "marasca, mandorla, floreale", "profilo": "liquore di ciliegie marasche distillate", "applicazioni": "aviation, last word, hemingway"},
    {"id": "ing-triple-sec", "nome": "Triple sec / Curaçao", "domini": ["bar"], "aroma": "scorza d'arancia dolce e amara", "profilo": "liquore all'arancia (cointreau è il riferimento)", "applicazioni": "margarita, sidecar, cosmopolitan"},
    {"id": "ing-chartreuse", "nome": "Chartreuse verde", "domini": ["bar"], "aroma": "130 erbe, mentolato, complesso, dolce-amaro", "profilo": "liquore erbale dei monaci certosini, 55%", "applicazioni": "last word, naked and famous, bijou"},
    {"id": "ing-campari", "nome": "Campari", "domini": ["bar"], "aroma": "china, rabarbaro, arancia amara, erbe", "profilo": "bitter rosso amaro, 25%", "applicazioni": "negroni, americano, boulevardier"},
    {"id": "ing-aperol", "nome": "Aperol", "domini": ["bar"], "aroma": "arancia amara, rabarbaro, genziana, leggero", "profilo": "aperitivo, 11%, più dolce e meno amaro del campari", "applicazioni": "spritz, paper plane"},
    {"id": "ing-amaro-nonino", "nome": "Amaro", "domini": ["bar"], "aroma": "erbe, radici, agrume, dolce-amaro", "profilo": "digestivo a base di erbe macerate", "applicazioni": "paper plane, black manhattan, liscio"},
    # ── BAR: sodati e mixer ──
    {"id": "ing-acqua-tonica", "nome": "Acqua tonica", "domini": ["bar"], "aroma": "chinino amaro, agrume, effervescente", "profilo": "soda aromatizzata al chinino", "applicazioni": "gin tonic, americano allungato"},
    {"id": "ing-ginger-beer", "nome": "Ginger beer", "domini": ["bar"], "aroma": "zenzero pungente, speziato, effervescente", "profilo": "bevanda allo zenzero fermentata o gassata", "applicazioni": "moscow mule, dark 'n' stormy"},
    {"id": "ing-soda-club", "nome": "Soda / Club soda", "domini": ["bar"], "aroma": "neutro, effervescente", "profilo": "acqua gassata neutra per allungare", "applicazioni": "highball, spritz, tom collins"},
    {"id": "ing-sciroppo-zucchero", "nome": "Sciroppo di zucchero", "domini": ["bar"], "aroma": "dolce neutro", "profilo": "zucchero e acqua 1:1 o 2:1 (rich)", "applicazioni": "quasi tutti i cocktail, bilanciamento"},
    {"id": "ing-orgeat", "nome": "Orgeat", "domini": ["bar"], "aroma": "mandorla, fiori d'arancio, dolce", "profilo": "sciroppo di mandorla", "applicazioni": "mai tai, japanese cocktail"},
    {"id": "ing-grenadine", "nome": "Grenadine", "domini": ["bar"], "aroma": "melograno, dolce, acidulo", "profilo": "sciroppo di melograno", "applicazioni": "tequila sunrise, planter's punch"},
    # ── GELATERIA: materia prima tecnica ──
    {"id": "ing-destrosio", "nome": "Destrosio", "domini": ["gelateria"], "aroma": "dolce meno del saccarosio", "profilo": "zucchero semplice, abbassa il punto di congelamento (anti-cristallizzazione)", "applicazioni": "bilanciamento mix gelato, controllo PAC"},
    {"id": "ing-latte-magro-polvere", "nome": "Latte magro in polvere", "domini": ["gelateria"], "aroma": "lattico neutro", "profilo": "solidi del latte non grassi, danno struttura e cremosità", "applicazioni": "corpo del gelato, riduce cristalli di ghiaccio"},
    {"id": "ing-neutro-gelato", "nome": "Neutro (stabilizzante)", "domini": ["gelateria"], "aroma": "neutro", "profilo": "mix di addensanti (farina di semi di carrube, guar) che legano l'acqua", "applicazioni": "struttura, riduce cristallizzazione, overrun"},
    {"id": "ing-sciroppo-glucosio", "nome": "Sciroppo di glucosio", "domini": ["gelateria", "pasticceria"], "aroma": "poco dolce", "profilo": "zucchero che dà corpo e contrasta la cristallizzazione", "applicazioni": "gelato, caramello, ganache lucide"},
    {"id": "ing-inulina", "nome": "Inulina", "domini": ["gelateria"], "aroma": "neutro, leggermente dolce", "profilo": "fibra che dà cremosità senza grassi", "applicazioni": "gelato light, sorbetti cremosi"},
    # ── CAFFÈ ──
    {"id": "ing-caffe-arabica", "nome": "Caffè Arabica", "domini": ["caffe"], "aroma": "floreale, fruttato, acidità viva, dolce", "profilo": "specie pregiata, meno caffeina, più aromi", "applicazioni": "espresso specialty, filtro"},
    {"id": "ing-caffe-robusta", "nome": "Caffè Robusta", "domini": ["caffe"], "aroma": "terroso, cioccolato, amaro, corpo pieno", "profilo": "più caffeina, più crema, meno acidità", "applicazioni": "blend espresso italiano, crema"},
    # ── PASTICCERIA: materia prima tecnica ──
    {"id": "ing-gelatina-fogli", "nome": "Gelatina in fogli", "domini": ["pasticceria"], "aroma": "neutro", "profilo": "collagene, gelifica a freddo, fonde in bocca", "applicazioni": "bavaresi, panna cotta, mousse"},
    {"id": "ing-cioccolato-fondente-70", "nome": "Cioccolato fondente 70%", "domini": ["pasticceria"], "aroma": "cacao intenso, frutta secca, amaro", "profilo": "alta percentuale di cacao, poco zucchero", "applicazioni": "ganache, mousse, temperaggio"},
    {"id": "ing-burro-cacao", "nome": "Burro di cacao", "domini": ["pasticceria"], "aroma": "cacao delicato, burroso", "profilo": "grasso del cacao, cristallizza in forme stabili", "applicazioni": "temperaggio, cioccolatini, lucido"},
    {"id": "ing-pasta-nocciola", "nome": "Pasta di nocciola", "domini": ["pasticceria"], "aroma": "nocciola tostata, dolce", "profilo": "nocciole macinate a pasta, 100%", "applicazioni": "gianduia, praline, gelato"},
]
