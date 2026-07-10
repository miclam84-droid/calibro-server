"""
Matter Lab — Ingredient Graph Builder
======================================
Genera il dataset completo di ingredienti F&B con:
- Composti aromatici (con CAS, soglia, fonte letteratura)
- Profilo sensoriale con spiegazione fisica
- Abbinamenti molecolari + contrasto + congruenza + regionali
- Collegamento ai fenomeni del grafo
- 5 lingue: IT EN ES FR DE

Salva direttamente in Postgres come nodi tipo 'Ingrediente' + archi.

Uso (Railway Console):
  python3 build_ingredient_graph.py --test        # testa 5 ingredienti
  python3 build_ingredient_graph.py --discipline bar
  python3 build_ingredient_graph.py --all         # tutti 3750 ingredienti
  python3 build_ingredient_graph.py --status      # quanti già fatti
"""

import os, sys, json, time, re
import urllib.request
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

# ── LISTA INGREDIENTI PER DISCIPLINA ─────────────────────────────────────────
INGREDIENTI = {
    "bar": [
        # Distillati base
        "whisky scozzese single malt","bourbon","rye whiskey","Irish whiskey",
        "gin London Dry","gin contemporaneo","vodka","rum bianco","rum scuro",
        "rum agricolo","tequila blanco","tequila reposado","tequila añejo",
        "mezcal","cognac","armagnac","grappa","pisco","calvados","cachaça",
        "brandy","marc","soju","baijiu","aquavit",
        # Liquori e amari
        "Campari","Aperol","Cointreau","Grand Marnier","Chartreuse verde",
        "Chartreuse gialla","Benedictine","Amaretto","Frangelico","Kahlua",
        "Baileys","Midori","Galliano","Sambuca","Limoncello","Maraschino",
        "Absinthe","Pastis","Fernet","Cynar","Amaro Montenegro","Averna",
        "Borghetti","Strega","Nocino","Vermouth dry","Vermouth rosso",
        "Vermouth bianco","Punt e Mes","Lillet Blanc","Suze","Aperol Spritz base",
        # Bitter e tinture
        "Angostura bitter","Peychaud's bitter","Orange bitter","Mole bitter",
        "Cardamom bitter","Chocolate bitter","Celery bitter","Lavender bitter",
        # Succhi e puree
        "succo di lime fresco","succo di limone fresco","succo di arancia fresco",
        "succo di pompelmo fresco","succo di ananas","succo di mela",
        "succo di melograno","succo di passion fruit","succo di mango",
        "succo di lampone","succo di fragola","succo di pesca","succo di pera",
        "purea di fragola","purea di lampone","purea di mango","purea di passion fruit",
        # Sciroppi
        "sciroppo semplice 1:1","sciroppo rich 2:1","sciroppo di gomma arabica",
        "sciroppo di orgeat","sciroppo di falernum","sciroppo di grenadine",
        "sciroppo di elderflower","sciroppo di lavanda","sciroppo di menta",
        "sciroppo di cannella","sciroppo di zenzero","sciroppo di cardamomo",
        "sciroppo di ibisco","sciroppo di tè Earl Grey","sciroppo di miele",
        "sciroppo di agave","sciroppo di acero","sciroppo di canna da zucchero",
        # Acidi
        "acido citrico","acido malico","acido tartarico","acido lattico",
        "acido ascorbico","acido fosforico","verjus",
        # Frutta fresca
        "fragola","lampone","mora","mirtillo","ciliegia","pesca","albicocca",
        "fico","melograno","arancia","mandarino","pompelmo","bergamotto",
        "lime","limone","yuzu","cedro","kaffir lime","banana","ananas",
        "mango","passion fruit","lychee","papaia","kiwi","uva","pera","mela",
        # Erbe e botaniche
        "menta piperita","menta spearmint","basilico","rosmarino","timo",
        "lavanda","verbena","melissa","salvia","origano","finocchietto",
        "dragoncello","coriandolo fresco","aneto",
        # Spezie bar
        "cannella","cardamomo verde","cardamomo nero","pepe nero","pepe rosa",
        "pepe lungo","anice stellato","chiodo di garofano","noce moscata",
        "vaniglia Madagascar","vaniglia Tahiti","zafferano","curcuma",
        "zenzero fresco","zenzero secco","peperoncino","jalapeño",
        # Altro bar
        "albume d'uovo","uovo intero","panna fresca","latte intero",
        "latte di cocco","crema di cocco","latte di mandorla","latte di avena",
        "acqua tonica","soda water","ginger beer","ginger ale",
        "sale","sale affumicato","salsa worcestershire","salsa tabasco",
        "salsa sriracha","olive","capperi","cetriolo","sedano",
        "miele","sciroppo di zucchero grezzo",
    ],
    "cucina": [
        # Carni
        "manzo (controfiletto)","manzo (costata)","manzo (filetto)",
        "manzo (chuck/spalla)","vitello","agnello (coscia)","agnello (costolette)",
        "maiale (lombo)","maiale (pancetta)","maiale (spalla)","maiale (guancia)",
        "pollo (petto)","pollo (coscia)","pollo (ali)","tacchino",
        "anatra","coniglio","cinghiale","cervo","quaglia","piccione",
        # Salumi
        "prosciutto crudo","prosciutto cotto","salame","pancetta","guanciale",
        "lardo","coppa","bresaola","mortadella","speck","nduja","salsiccia",
        "cotechino","zampone","porchetta","lardo di Colonnata",
        # Pesce e frutti di mare
        "branzino","orata","salmone","tonno","sgombro","acciughe",
        "sardine","merluzzo","baccalà","polpo","calamaro","seppia",
        "gamberi","scampi","astice","granchio","cozze","vongole",
        "ostriche","capesante","ricci di mare","bottarga","caviale",
        # Verdure
        "pomodoro","pomodorino ciliegino","pomodoro San Marzano",
        "melanzana","zucchina","peperone rosso","peperone giallo",
        "peperone verde","carota","cipolla bianca","cipolla rossa",
        "aglio","scalogno","porri","finocchio","sedano","sedano rapa",
        "rucola","spinaci","cicoria","radicchio rosso","catalogna",
        "bietola","cavolo nero","verza","cavolfiore","broccoli",
        "carciofo","asparagi bianchi","asparagi verdi","piselli",
        "fave","fagiolini","zucca","topinambur","barbabietola",
        "patata","patata dolce","rapanelli","cetriolo","avocado",
        # Funghi
        "porcini","champignon","shiitake","pleurotus","gallinacci",
        "finferli","trombette dei morti","tartufo nero","tartufo bianco",
        # Legumi
        "ceci","lenticchie rosse","lenticchie verdi","fagioli borlotti",
        "fagioli cannellini","fagioli neri","fave","piselli secchi","edamame",
        # Cereali e pasta
        "riso Carnaroli","riso Arborio","riso Vialone Nano","riso basmati",
        "riso jasmine","pasta di semola","pasta all'uovo","gnocchi",
        "farro","orzo perlato","quinoa","bulgur","polenta","couscous",
        # Latticini
        "burro","panna fresca","latte intero","mozzarella di bufala",
        "fior di latte","burrata","stracciatella","ricotta","mascarpone",
        "parmigiano reggiano","grana padano","pecorino romano",
        "pecorino sardo","gorgonzola","taleggio","fontina","asiago",
        "provolone","caciocavallo","scamorza","brie","camembert",
        # Uova
        "uova di gallina","uova di quaglia","uova di anatra",
        # Condimenti e grassi
        "olio extravergine di oliva fruttato","olio extravergine leggero",
        "olio di sesamo","olio di arachide","strutto","burro chiarificato",
        "aceto di vino rosso","aceto di vino bianco","aceto balsamico",
        "aceto balsamico tradizionale","aceto di mele","aceto di riso",
        "salsa di soia","salsa worcestershire","miso bianco","miso rosso",
        "pasta di tamarindo","colatura di alici","garum","nduja",
        # Erbe aromatiche
        "basilico genovese","prezzemolo","origano","rosmarino","timo",
        "salvia","alloro","dragoncello","maggiorana","mentuccia",
        "erba cipollina","aneto","cerfoglio","santoreggia",
        # Spezie cucina
        "pepe nero","pepe bianco","pepe di Sichuan","pepe lungo",
        "peperoncino calabrese","peperoncino habanero","paprica dolce",
        "paprica affumicata","curcuma","zafferano","cannella","cardamomo",
        "cumino","coriandolo secco","anice stellato","noce moscata",
        "chiodo di garofano","ginepro","finocchio selvatico","sumac",
        "za'atar","ras el hanout","garam masala","curry","harissa",
        # Frutta in cucina
        "limone","arancia","pompelmo","lime","melograno","fico",
        "albicocca","pesca","prugna","mela verde","pera","cachi",
        "castagna","dattero","uvetta","pomodoro secco",
        # Frutta secca e semi
        "mandorle","nocciole","pinoli","noci","pistacchi","anacardi",
        "noci pecan","noci di macadamia","semi di sesamo","semi di lino",
        "semi di zucca","semi di girasole","semi di papavero",
        # Altro cucina
        "pane raffermo","pangrattato","acciughe sott'olio","capperi",
        "olive taggiasche","olive Kalamata","olive verdi",
        "peperoni in agrodolce","melanzane sott'olio","crostini",
    ],
    "panificazione": [
        # Farine
        "farina 00 di grano tenero","farina 0","farina 1","farina 2",
        "farina integrale di grano tenero","farina di semola rimacinata",
        "farina di semola integrale","farina di segale integrale",
        "farina di farro monococco","farina di farro spelta",
        "farina di kamut","farina di mais","farina di riso",
        "farina di grano saraceno","farina di soia","farina di avena",
        "farina di ceci","farina di mandorle",
        # Lieviti e fermentazione
        "lievito di birra fresco","lievito di birra secco attivo",
        "lievito di birra istantaneo","lievito madre liquido (idratazione 100%)",
        "lievito madre solido (idratazione 50%)","biga","poolish",
        "lievito chimico (baking powder)","bicarbonato di sodio",
        "cremor tartaro",
        # Grassi
        "burro 82% mg","burro 84% mg","burro chiarificato","olio EVO",
        "olio di girasole","strutto","margarina vegetale",
        "burro di cacao","olio di cocco",
        # Zuccheri
        "saccarosio","zucchero di canna grezzo","miele di acacia",
        "miele millefiori","maltosio","sciroppo di malto",
        "sciroppo di glucosio","sciroppo di fruttosio",
        "zucchero invertito","trehalosio","lattosio","malto diastasico",
        # Latticini panificazione
        "latte intero fresco","latte in polvere intero",
        "latte in polvere scremato","panna fresca","yogurt intero",
        "kefir","burro acido",
        # Uova panificazione
        "uova intere fresche","tuorli","albumi","uova in polvere",
        # Miglioratori e additivi
        "lecitina di soia","acido ascorbico (vitamina C)",
        "malto diastasico in polvere","farina di soia attiva",
        "glutine vitale di frumento","enzima amilasi","enzima proteasi",
        # Aromi panificazione
        "estratto di vaniglia","bacca di vaniglia","scorza di limone",
        "scorza di arancia","acqua di fiori d'arancio","semi di anice",
        "semi di finocchio","semi di cumino","semi di carvi",
        "rosmarino secco","olive denocciolate","pomodori secchi",
        # Semi e inclusioni
        "semi di sesamo","semi di papavero","semi di lino","semi di girasole",
        "semi di zucca","noci tritate","uvetta","fichi secchi",
        "albicocche secche","cranberry essiccati","gocce di cioccolato",
        # Acqua
        "acqua oligominerale (residuo fisso < 50 mg/L)",
        "acqua mediominerale (residuo fisso 50-500 mg/L)",
        "acqua minerale calcica","acqua dura (alta durezza)",
    ],
    "pasticceria": [
        # Cioccolati
        "cioccolato fondente 55%","cioccolato fondente 64%",
        "cioccolato fondente 70%","cioccolato fondente 85%",
        "cioccolato fondente 100% (cacao puro)","cioccolato al latte 33%",
        "cioccolato al latte 40%","cioccolato bianco 28%",
        "cioccolato ruby","cioccolato biondo (Dulcey)","cacao in polvere",
        "burro di cacao","massa di cacao",
        # Zuccheri pasticceria
        "saccarosio fine","zucchero a velo","zucchero semolato",
        "zucchero di canna demerara","miele","glucosio DE42",
        "glucosio DE60","fruttosio cristallino","sciroppo di glucosio-fruttosio",
        "zucchero invertito (trimoline)","isomalt","sorbitolo","xilitolo",
        "trealosio","lattosio","maltitolo",
        # Farine pasticceria
        "farina 00 per pasticceria","farina di mandorle fine",
        "farina di nocciole","farina di pistacchio","farina di cocco",
        "fecola di patate","amido di mais","amido di riso","amido di tapioca",
        # Grassi pasticceria
        "burro 84% mg di alta qualità","burro di noisette (burro nocciola)",
        "panna fresca 35% mg","panna UHT 35% mg","mascarpone",
        "burro di cacao","olio di cocco deodorato","burro vegetale temperabile",
        # Uova pasticceria
        "uova intere fresche","tuorli freschi","albumi freschi",
        "albumi pastorizzati","uova in polvere",
        # Frutta fresca pasticceria
        "fragola","lampone","mora","mirtillo","ribes rosso",
        "passion fruit","mango Alphonso","mango Tommy","albicocca",
        "pesca noce","ciliegia Amarena","ciliegia Marasca","fico",
        "melograno","pera Williams","mela Granny Smith",
        "banana","ananas","lychee","yuzu","bergamotto","lime",
        "limone Amalfi","arancia sanguinella","mandarino",
        # Frutta secca pasticceria
        "pistacchio di Bronte","pistacchio iraniano","nocciola Piemonte IGP",
        "nocciola turca","mandorla di Avola","mandorla californiana",
        "noci di Grenoble","noci pecan","noci di macadamia",
        "pinoli","anacardi","arachidi tostati",
        # Frutta candita e secca
        "arancia candita","cedro candito","ciliegia candita",
        "zenzero candito","uvetta sultanina","uvetta di Corinto",
        "albicocche secche","prugne secche","datteri Medjool",
        "fichi secchi","mirtilli rossi essiccati",
        # Latticini pasticceria
        "latte intero fresco","latte intero UHT","panna fresca 35%",
        "panna vegetale","mascarpone","ricotta di mucca",
        "ricotta di pecora","cream cheese","crème fraîche",
        "yogurt greco","latte condensato zuccherato","latte evaporato",
        # Gelatine e addensanti
        "gelatina in fogli oro (200 bloom)","gelatina in fogli argento (160 bloom)",
        "gelatina in polvere","agar agar","pectina NH",
        "pectina 325 NH95","carragenina kappa","carragenina iota",
        "gomma xantano","gomma di guar","farina di semi di carrube",
        "metilcellulosa","agar di arrowroot",
        # Aromi ed estratti
        "estratto di vaniglia bourbon","bacca di vaniglia Madagascar",
        "bacca di vaniglia Tahiti","bacca di vaniglia Papua",
        "pasta di vaniglia","acqua di fiori d'arancio",
        "acqua di rose","estratto di caffè","pasta di caffè",
        "aroma di limone naturale","aroma di arancia naturale",
        "rum agricolo (per dolci)","Grand Marnier","Cointreau",
        "Kirsch","Amaretto","Frangelico","Malibù",
        # Spezie pasticceria
        "cannella di Ceylon","cassia","cardamomo verde",
        "zenzero in polvere","noce moscata","chiodo di garofano",
        "anice stellato","pepe nero (in pasticceria)","peperoncino",
        "fiore di sale","sale Maldon","sale affumicato",
        # Caffè e tè pasticceria
        "espresso concentrato","caffè solubile freeze-dried",
        "matcha cerimonia","matcha culinario","tè Earl Grey",
        "tè Lapsang Souchong","tè Oolong","hibiscus",
        # Coloranti naturali
        "carbone vegetale attivo","cacao nero","barbabietola in polvere",
        "spirulina","curcuma","paprica","estratto di carota",
    ],
    "gelateria": [
        # Basi lattiere
        "latte intero fresco","latte intero UHT","latte scremato",
        "latte in polvere intero","latte in polvere scremato",
        "panna fresca 35%","panna UHT 35%","panna vegetale",
        "latte condensato zuccherato","latte evaporato",
        "panna acida","latte di capra",
        # Zuccheri gelateria
        "saccarosio","destrosio monoidrato","fruttosio cristallino",
        "sciroppo di glucosio DE60","sciroppo di glucosio-fruttosio",
        "zucchero invertito (trimoline)","trealosio","lattosio",
        "maltitolo","sorbitolo","miele di acacia",
        "sciroppo di agave","zucchero di cocco",
        # Paste frutta secca
        "pasta di pistacchio 100% Sicilia","pasta di pistacchio 100% Iran",
        "pasta di nocciola 100% Piemonte","pasta di mandorla 100%",
        "pasta di arachide","pasta di noci di macadamia",
        "pasta di cocco","pralinato nocciola","pralinato mandorla",
        "pasta di sesamo (tahini)","pasta di semi di girasole",
        # Frutta per sorbetti
        "fragola (IQF)","lampone (IQF)","mora (IQF)","mirtillo (IQF)",
        "passion fruit (polpa)","mango Alphonso (polpa)",
        "mango Tommy (polpa)","ananas (polpa)","banana","cocco (polpa)",
        "limone (succo e scorza)","arancia (succo e scorza)",
        "pompelmo rosa","lime","yuzu","bergamotto","cedro",
        "pesca (polpa)","albicocca (polpa)","ciliegia Amarena",
        "fico","melograno (succo)","anguria","melone Cantalupo",
        "kiwi","lychee","papaia","maracujà","cachi","pera Williams",
        # Cioccolati gelateria
        "copertura fondente 55%","copertura fondente 70%",
        "copertura al latte 33%","copertura bianca 28%",
        "cacao in polvere 10-12%","cacao in polvere 20-22%",
        "burro di cacao","granella di cacao",
        # Caffè gelateria
        "espresso doppio concentrato","caffè solubile premium",
        "cold brew concentrate","matcha cerimonia","matcha culinario",
        "tè Earl Grey (infuso concentrato)","tè verde Sencha",
        # Stabilizzanti ed emulsionanti
        "farina di semi di carrube (LBG)","gomma di guar",
        "gomma xantano","carragenina kappa","agar agar",
        "pectina","mono e digliceridi (E471)","lecitina di soia",
        "mix neutro per gelato","mix stabilizzante professionale",
        # Variegature
        "variegato di fragola","variegato di lampone",
        "variegato di cioccolato","variegato caramello salato",
        "variegato di pistacchio","variegato di nocciola",
        "marmellata di albicocche","confettura di fragole",
        # Inclusi e decorazioni
        "biscotto Oreo sbriciolato","wafer sbriciolato",
        "brownie a cubetti","cornflakes caramellati",
        "nocciole caramellate","granella di pistacchio",
        "pinoli tostati","cialda in coni",
        # Alcolici per semifreddi
        "rum scuro (per gelati alcolici)","Grand Marnier",
        "Cointreau","limoncello","Baileys","Amaretto",
        "grappa","whisky (per parfait)","Prosecco (per sorbetti)",
        # Aromi naturali gelateria
        "estratto di vaniglia bourbon","bacca di vaniglia",
        "acqua di fiori d'arancio","acqua di rose",
        "estratto di menta piperita","pasta di limone naturale",
        "aroma di arancia naturale",
    ],
    "caffe": [
        # Origini singole
        "caffè Etiopia Yirgacheffe (washed)","caffè Etiopia Sidamo",
        "caffè Etiopia Guji (natural)","caffè Kenya AA (washed)",
        "caffè Kenya Nyeri","caffè Colombia Huila",
        "caffè Colombia Nariño","caffè Guatemala Antigua",
        "caffè Guatemala Huehuetenango","caffè Costa Rica Tarrazú",
        "caffè Panama Geisha (washed)","caffè Panama Geisha (natural)",
        "caffè Brasile Santos","caffè Brasile Cerrado Mineiro",
        "caffè Brasile Yellow Bourbon","caffè Honduras SHG",
        "caffè Nicaragua SHG","caffè El Salvador Pacamara",
        "caffè Peru organic","caffè Bolivia","caffè Perù",
        "caffè Yemen Mocha","caffè Indonesia Sumatra Mandheling",
        "caffè Java","caffè Sulawesi Toraja","caffè Timor-Leste",
        "caffè Papua Nuova Guinea","caffè India Monsoon Malabar",
        "caffè Hawaii Kona","caffè Jamaica Blue Mountain",
        # Lavorazioni
        "caffè washed (lavato)","caffè natural (secco)",
        "caffè honey process","caffè anaerobic natural",
        "caffè anaerobic washed","caffè carbonic maceration",
        "caffè pulped natural","caffè wet-hulled (Giling Basah)",
        # Tostature
        "tostatura chiara (light roast)","tostatura media (medium roast)",
        "tostatura medio-scura (medium-dark)","tostatura scura (dark roast)",
        "tostatura espresso italiana tradizionale",
        # Latte e alternative
        "latte intero fresco (per cappuccino)","latte parzialmente scremato",
        "latte scremato","latte di avena barista","latte di soia barista",
        "latte di mandorla barista","latte di cocco barista",
        "latte di macadamia","panna fresca per latte art",
        # Sciroppi caffetteria
        "sciroppo di vaniglia","sciroppo di caramello",
        "sciroppo di nocciola","sciroppo di cioccolato",
        "sciroppo di lavanda","sciroppo di cannella",
        "sciroppo di amaretto","sciroppo di menta",
        # Spezie per caffè
        "cardamomo (per caffè arabo)","cannella (per caffè speziato)",
        "zenzero (per caffè chai)","noce moscata",
        "pepe nero (per caffè etiope)","chiodo di garofano",
    ],
    "vino": [
        # Uve bianche italiane
        "Chardonnay","Sauvignon Blanc","Pinot Grigio","Riesling Renano",
        "Gewürztraminer","Vermentino","Fiano di Avellino","Greco di Tufo",
        "Falanghina","Catarratto","Grillo","Carricante","Ansonica",
        "Verdicchio","Pecorino (uva)","Passerina","Ribolla Gialla",
        "Friulano (Tocai)","Malvasia Istriana","Glera (Prosecco)",
        "Moscato Bianco","Garganega (Soave)","Trebbiano Toscano",
        "Arneis","Cortese (Gavi)","Grechetto","Orvieto blend",
        # Uve bianche internazionali
        "Chenin Blanc","Viognier","Roussanne","Marsanne",
        "Albariño","Verdejo","Grüner Veltliner","Pinot Blanc",
        "Muscat Blanc à Petits Grains","Sémillon","Torrontés",
        # Uve rosse italiane
        "Sangiovese","Nebbiolo","Barbera","Dolcetto","Montepulciano",
        "Aglianico","Nero d'Avola","Primitivo","Negroamaro",
        "Nerello Mascalese","Nerello Cappuccio","Cannonau (Grenache Sarda)",
        "Gaglioppo","Sagrantino","Ciliegiolo","Colorino",
        "Cesanese","Teroldego","Lagrein","Schiava",
        "Lambrusco Grasparossa","Lambrusco Sorbara","Brachetto",
        # Uve rosse internazionali
        "Cabernet Sauvignon","Merlot","Pinot Nero","Syrah/Shiraz",
        "Grenache","Mourvèdre","Tempranillo","Garnacha",
        "Malbec","Carménère","Zinfandel","Petite Sirah",
        "Carignan","Cinsault","Cabernet Franc","Petit Verdot",
        # Composti del vino (fenomeni)
        "acido tartarico","acido malico","acido citrico","acido lattico",
        "acido acetico (volatile acidity)","acido succinico",
        "tannini condensati (proantocianidine)","tannini idrolizzabili",
        "antociani","flavonoli","resveratrolo","SO2 libera","SO2 totale",
        "glicerolo","etanolo","acetaldeide","etil acetato",
        "linalolo","geraniolo","nerol","beta-ionone","rotundone",
        "pirazine (2-isobutil-3-metossipirazina)","TCA (tappo)",
        # Additivi enologici
        "lievito Saccharomyces cerevisiae (neutro)","lievito aromatico Zymaflore",
        "batteri malolattici Oenococcus oeni","bentonite",
        "gomma arabica","tannino enologico","enzimi pectolitici",
    ],
    "birra": [
        # Malti base
        "malto Pilsner (2 row)","malto Pale Ale","malto Vienna",
        "malto Monaco (Munich)","malto Maris Otter","malto Golden Promise",
        "malto di frumento (Wheat Malt)","malto di segale","malto di farro",
        "malto di avena","malto di mais","malto di riso",
        # Malti speciali
        "malto Crystal 20L","malto Crystal 40L","malto Crystal 60L",
        "malto Crystal 80L","malto Crystal 120L","malto Carapils (Dextrin)",
        "malto Aromatic","malto Biscuit","malto Melanoidin","malto Special B",
        "malto Chocolate","malto Roasted Barley","malto Black Patent",
        "malto Acid (acidificato)","malto Smoked (affumicato Beechwood)",
        "malto Rauch (affumicato Bamberga)","malto Peated (torbato)",
        # Luppoli aroma
        "luppolo Cascade","luppolo Citra","luppolo Mosaic","luppolo Simcoe",
        "luppolo Centennial","luppolo Columbus/CTZ","luppolo Amarillo",
        "luppolo Galaxy","luppolo Nelson Sauvin","luppolo Motueka",
        "luppolo Wai-iti","luppolo Hallertau Mittelfrüh","luppolo Saaz",
        "luppolo Tettnang","luppolo Spalt","luppolo Styrian Goldings",
        "luppolo East Kent Goldings","luppolo Fuggles","luppolo Target",
        "luppolo Challenger","luppolo Northern Brewer","luppolo Magnum",
        "luppolo Perle","luppolo Polaris","luppolo Mandarina Bavaria",
        "luppolo Huell Melon","luppolo Ekuanot","luppolo Idaho 7",
        "luppolo Strata","luppolo Sabro","luppolo El Dorado",
        # Lieviti birra
        "lievito Ale americano (US-05)","lievito Ale inglese (S-04)",
        "lievito Lager (W-34/70)","lievito belga ad alta fermentazione",
        "lievito belga Saison (3724)","lievito Hefeweizen (WB-06)",
        "lievito Kveik Voss","lievito Kveik Hornindal",
        "Brettanomyces bruxellensis","Brettanomyces anomalus",
        "Lactobacillus plantarum","Lactobacillus brevis",
        "Pediococcus damnosus","lievito Champagne (per alti alcoli)",
        # Aggiunte e spezie birra
        "scorza d'arancia dolce","scorza d'arancia amara",
        "coriandolo in semi","cannella in stecca","zenzero fresco",
        "vaniglia","peperoncino","caffè (cold brew per porter)",
        "cioccolato fondente (per stout)","miele (per braggot)",
        "avena (per oatmeal stout)","latte (lattosio per milk stout)",
        "cocco","ananas","mango","passion fruit","lampone","ciliegia",
        "prugna","peche","albicocca","fico",
        "quercia americana (oak chips)","quercia francese",
        "bourbon barrel chips","whisky barrel chips",
        # Acqua e sali
        "solfato di calcio (gypsum)","cloruro di calcio",
        "bicarbonato di sodio","carbonato di calcio",
        "cloruro di sodio (sale)","solfato di magnesio (sale epsom)",
        "acido lattico (per abbassare pH mash)","acido fosforico",
    ],
}

# ── PROMPT TEMPLATE ───────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """Sei un esperto di chimica degli alimenti e scienza sensoriale con accesso alla letteratura scientifica (Food Chemistry, Journal of Agricultural and Food Chemistry, Meat Science, LWT, Flavour and Fragrance Journal, McGee On Food and Cooking).

Genera un profilo scientifico completo per l'ingrediente: **{ingrediente}**
Disciplina principale: {disciplina}

Rispondi ESCLUSIVAMENTE in JSON valido, senza testo aggiuntivo, con questa struttura:

{{
  "nomi": {{
    "it": "<nome ufficiale italiano>",
    "en": "<nome inglese>",
    "es": "<nome spagnolo>",
    "fr": "<nome francese>",
    "de": "<nome tedesco>"
  }},
  "categoria": "<categoria merceologica es: salumi/frutta/cereali/distillati/luppoli>",
  "sottocategoria": "<più specifica>",
  "disciplina_principale": "{disciplina}",
  "discipline_correlate": ["<altre discipline dove si usa>"],
  "composti_aromatici": [
    {{
      "nome": "<nome composto>",
      "cas": "<numero CAS se noto, altrimenti null>",
      "famiglia_chimica": "<es: terpeni/esteri/aldeidi/fenoli/acidi organici>",
      "soglia_percezione_ppb": <numero o null>,
      "descrittore_olfattivo": "<es: agrumato/floreale/erbaceo/tostato>",
      "intensita_nel_prodotto": <1-5>,
      "fonte": "<es: Food Chemistry 2019 / McGee / USDA / stima da letteratura>"
    }}
  ],
  "profilo_sensoriale": {{
    "dolce": {{"valore": <0-10>, "perche": "<meccanismo fisico-chimico>"}},
    "salato": {{"valore": <0-10>, "perche": "<meccanismo>"}},
    "acido": {{"valore": <0-10>, "perche": "<meccanismo con pH se noto>"}},
    "amaro": {{"valore": <0-10>, "perche": "<meccanismo>"}},
    "umami": {{"valore": <0-10>, "perche": "<meccanismo, glutammato libero ecc>"}},
    "grasso": {{"valore": <0-10>, "perche": "<acidi grassi, texture>"}},
    "piccante": {{"valore": <0-10>, "perche": "<capsaicina/piperina/isotiocianati>"}},
    "astringente": {{"valore": <0-10>, "perche": "<tannini, polifenoli>"}},
    "affumicato": {{"valore": <0-10>, "perche": "<guaiacolo, siringolo se presenti>"}}
  }},
  "parametri_fisici": {{
    "ph": "<es: 4.8-5.2 o null>",
    "aw": "<es: 0.85 o null>",
    "brix": "<se rilevante>",
    "abv_pct": "<se alcolico>",
    "grassi_pct": <numero o null>,
    "proteine_pct": <numero o null>,
    "zuccheri_pct": <numero o null>,
    "temperatura_servizio_c": "<es: 16-18 o null>"
  }},
  "categorie_aromatiche": ["<es: carnoso/fermentato/speziato/fruttato/floreale/erbaceo/tostato/affumicato/terroso/marino>"],
  "fenomeni_collegati": ["<id fenomeni Matter Lab es: fen-acidita/fen-maillard/fen-fermentazione-lattica/fen-ossidazione/fen-emulsione>"],
  "abbinamenti": {{
    "molecolari": [
      {{
        "ingrediente_it": "<nome it>",
        "ingrediente_en": "<nome en>",
        "composti_condivisi": ["<composto1>", "<composto2>"],
        "overlap_score": <numero 1-100>,
        "meccanismo": "<spiegazione scientifica>"
      }}
    ],
    "contrasto": [
      {{
        "ingrediente_it": "<nome>",
        "ingrediente_en": "<nome>",
        "tipo": "<acido_taglia_grasso/dolce_bilancia_salato/sale_sopprime_amaro/umami_amplifica_umami/piccante_contrasta_dolce/acido_contrasta_dolce/astringente_pulisce_grasso>",
        "perche": "<meccanismo fisico-percettivo dettagliato>",
        "fenomeno_matter": "<id fenomeno>"
      }}
    ],
    "congruenza": [
      {{
        "ingrediente_it": "<nome>",
        "ingrediente_en": "<nome>",
        "tipo": "<famiglia_aromatica/umami_sinergico/texture_complementare>",
        "perche": "<perché funzionano insieme>"
      }}
    ],
    "regionali": {{
      "it": ["<abbinamento tradizionale italiano>"],
      "fr": ["<abbinamento francese>"],
      "es": ["<abbinamento spagnolo>"],
      "en": ["<abbinamento anglosassone>"]
    }}
  }},
  "note_professionista": "<consiglio pratico per il professionista F&B, con numero misurabile se possibile>"
}}

Sii preciso scientificamente. Cita almeno 3-5 composti aromatici reali con CAS quando possibile.
Per i profili sensoriali usa valori calibrati su scala 0-10 (0=assente, 10=dominante).
Gli abbinamenti devono avere una spiegazione fisico-chimica reale, non generica."""


def gpt_ingrediente(ingrediente, disciplina):
    """Genera il profilo completo di un ingrediente via GPT-4o-mini."""
    prompt = PROMPT_TEMPLATE.format(
        ingrediente=ingrediente,
        disciplina=disciplina
    )
    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    usage = data.get("usage", {})
    testo = data["choices"][0]["message"]["content"].strip()
    return json.loads(testo), usage


def node_id(ingrediente):
    """Genera un ID nodo dal nome ingrediente."""
    clean = ingrediente.lower()
    clean = re.sub(r'[^a-z0-9\s]', '', clean)
    clean = re.sub(r'\s+', '-', clean.strip())
    clean = clean[:60]
    return f"ing-{clean}"


def salva_in_grafo(conn, ingrediente, disciplina, profilo):
    """Salva il profilo come nodo Ingrediente + archi nel grafo."""
    cur = conn.cursor()
    nid = node_id(ingrediente)
    nome_it = profilo.get("nomi", {}).get("it", ingrediente)

    # Inserisci nodo principale
    cur.execute("""
        INSERT INTO nodes (id, type, name, domain, data)
        VALUES (%s, 'Ingrediente', %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            domain = EXCLUDED.domain,
            data = EXCLUDED.data
    """, (
        nid,
        nome_it,
        disciplina,
        psycopg2.extras.Json(profilo)
    ))

    # Salva nomi multilingua
    nomi = profilo.get("nomi", {})
    for lang, nome in nomi.items():
        if nome:
            cur.execute("""
                INSERT INTO ingredienti_nomi (node_id, lang, nome)
                VALUES (%s, %s, %s)
                ON CONFLICT (node_id, lang) DO UPDATE SET nome = EXCLUDED.nome
            """, (nid, lang, nome.lower()))

    # Crea archi verso fenomeni collegati
    fenomeni = profilo.get("fenomeni_collegati", [])
    for fen_id in fenomeni:
        if fen_id:
            # Verifica che il fenomeno esista
            cur.execute("SELECT 1 FROM nodes WHERE id=%s", (fen_id,))
            if cur.fetchone():
                cur.execute("""
                    INSERT INTO edges (from_id, to_id, relation, data)
                    VALUES (%s, %s, 'si_manifesta_in', '{}')
                    ON CONFLICT (from_id, to_id, relation) DO NOTHING
                """, (fen_id, nid))

    # Crea archi abbinamento molecolare verso altri ingredienti noti
    for abb in profilo.get("abbinamenti", {}).get("molecolari", []):
        target_name = abb.get("ingrediente_en", "") or abb.get("ingrediente_it", "")
        if target_name:
            # Cerca se esiste già nel grafo (Ahn o altro)
            cur.execute("""
                SELECT id FROM nodes
                WHERE type IN ('Prodotto','Ingrediente')
                AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                LIMIT 1
            """, (f"%{target_name}%", f"%{target_name.replace(' ','%')}%"))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    INSERT INTO edges (from_id, to_id, relation, data)
                    VALUES (%s, %s, 'abbinamento_aromatico', %s)
                    ON CONFLICT (from_id, to_id, relation) DO NOTHING
                """, (nid, row[0], psycopg2.extras.Json({
                    "overlap": abb.get("overlap_score", 0),
                    "composti": abb.get("composti_condivisi", []),
                    "meccanismo": abb.get("meccanismo", "")
                })))

    # Log
    cur.execute("""
        INSERT INTO ingredient_build_log (node_id, disciplina)
        VALUES (%s, %s)
        ON CONFLICT (node_id) DO UPDATE SET ts=NOW(), disciplina=EXCLUDED.disciplina
    """, (nid, disciplina))

    conn.commit()
    cur.close()
    return nid


def status():
    """Mostra quanti ingredienti sono già stati generati."""
    if not DATABASE_URL:
        print("DATABASE_URL non configurata"); return
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("SELECT disciplina, COUNT(*) FROM ingredient_build_log GROUP BY disciplina ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
        if not rows:
            print("Nessun ingrediente ancora generato.")
            return
        totale = sum(r[1] for r in rows)
        print(f"INGREDIENTI GENERATI: {totale}")
        for disc, n in rows:
            stima = len(INGREDIENTI.get(disc, []))
            print(f"  {disc:<20} {n:>4} / {stima:>4}")
        # Totale stimato
        tot_stima = sum(len(v) for v in INGREDIENTI.values())
        print(f"  {'TOTALE':<20} {totale:>4} / {tot_stima:>4}")
    except Exception as e:
        print(f"Tabella non ancora creata: {e}")
    finally:
        cur.close(); conn.close()


def init_tables():
    """Crea le tabelle necessarie una volta sola."""""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ingredienti_nomi (
        node_id TEXT,
        lang    TEXT NOT NULL,
        nome    TEXT NOT NULL,
        PRIMARY KEY (node_id, lang)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ingredient_build_log (
        node_id     TEXT PRIMARY KEY,
        disciplina  TEXT,
        ts          TIMESTAMPTZ DEFAULT NOW(),
        tokens_used INTEGER DEFAULT 0
    )""")
    conn.commit(); cur.close(); conn.close()


def build(discipline=None, test=False):
    """Genera e salva i profili ingredienti."""
    if not DATABASE_URL or not OPENAI_KEY:
        print("DATABASE_URL o OPENAI_API_KEY non configurata"); return

    # Crea tabelle una volta sola prima di tutto
    init_tables()

    conn = psycopg2.connect(DATABASE_URL)

    # Determina cosa processare
    if test:
        da_fare = [("bar", "whisky scozzese single malt"),
                   ("cucina", "salame"),
                   ("pasticceria", "cioccolato fondente 70%"),
                   ("panificazione", "farina di semola rimacinata"),
                   ("birra", "luppolo Citra")]
    elif discipline:
        disc_list = [discipline] if isinstance(discipline, str) else discipline
        da_fare = [(d, ing) for d in disc_list for ing in INGREDIENTI.get(d, [])]
    else:
        da_fare = [(d, ing) for d, ings in INGREDIENTI.items() for ing in ings]

    # Filtra già processati
    cur = conn.cursor()
    try:
        cur.execute("SELECT node_id FROM ingredient_build_log")
        gia_fatti = {r[0] for r in cur.fetchall()}
    except Exception:
        gia_fatti = set()
    cur.close()

    da_fare = [(d, ing) for d, ing in da_fare if node_id(ing) not in gia_fatti]
    print(f"Ingredienti da generare: {len(da_fare)}")

    ok = 0; errori = 0; token_tot = 0
    for i, (disc, ing) in enumerate(da_fare):
        try:
            profilo, usage = gpt_ingrediente(ing, disc)
            tok = usage.get("total_tokens", 0)
            # Connessione fresca per ogni ingrediente — zero transaction pollution
            conn_ing = psycopg2.connect(DATABASE_URL)
            try:
                nid = salva_in_grafo(conn_ing, ing, disc, profilo)
                conn_ing.close()
            except Exception as db_e:
                try: conn_ing.rollback(); conn_ing.close()
                except: pass
                raise db_e
            token_tot += tok
            ok += 1
            costo = token_tot * 0.000000375
            print(f"  [{i+1}/{len(da_fare)}] ✓ {ing[:40]} → {nid} ({tok} tok, ${costo:.4f} tot)")
            time.sleep(0.15)
        except Exception as e:
            errori += 1
            print(f"  [{i+1}/{len(da_fare)}] ✗ {ing[:40]}: {str(e)[:80]}")

    conn.close()
    costo_finale = token_tot * 0.000000375
    print(f"\nCompletato: {ok} OK, {errori} errori | Token: {token_tot} | Costo: ${costo_finale:.3f}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        status()
    elif "--test" in sys.argv:
        build(test=True)
    elif "--all" in sys.argv:
        build()
    elif "--discipline" in sys.argv:
        idx = sys.argv.index("--discipline")
        disc = sys.argv[idx+1] if idx+1 < len(sys.argv) else None
        if disc:
            build(discipline=disc)
        else:
            print("Specifica la disciplina: bar|cucina|panificazione|pasticceria|gelateria|caffe|vino|birra")
    else:
        print(__doc__)
