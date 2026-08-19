# ============================================================
# routes/admin.py — interfaccia admin (build, quality-test, schede,
# assistenza, statistiche, migrazione). Auth via ADMIN_SECRET.
# Dipende da: db, auth, contenuto, notifiche, oss, ai_gateway.
# ============================================================
import os, json, traceback, time, hmac
from flask import Blueprint, request, jsonify

from db import carica_grafo, _dati, _get_conn, _release_conn
from auth import _admin_autenticato, _init_account_tables
from contenuto import (_scheda_lang, _numero_bersaglio, _pulisci_traduzione, _corregge_it)
from notifiche import _invia_email_resend
import oss

bp = Blueprint("admin", __name__)


RICETTE_PANIFICATI = {
    "prod-pizza": {
        "scheda": """"Pizza" non è un piatto: è una famiglia. Napoletana, romana, in teglia, in pala, pinsa — sembrano parenti lontani, e invece sono lo stesso impasto governato da due soli assi: quanta acqua, e quanto fuoco. Impara a leggere questi due assi e non ti perdi più tra le mille pizze: capisci perché la napoletana è morbida e la romana scrocchia, perché la teglia è alta e alveolata e la napoletana no. È tutta fisica, spostata lungo due linee.

Tutte le pizze condividono gli stessi quattro ingredienti base (farina, acqua, lievito, sale) e gli stessi fenomeni. Quello che le rende diverse è dove le collochi lungo due assi.

Il primo asse: l'acqua (idratazione)

Il numero che comanda di più (vedi il fenomeno dell'idratazione). Dal più asciutto al più bagnato:
- Romana tonda (scrocchiarella): 50-55% — bassa. Impasto sodo, steso al mattarello, sottile e croccante.
- Napoletana STG: 60-65% — media. Morbida ed elastica, cornicione alveolato.
- Napoletana contemporanea: 65-70% — più alta, cornicione più pronunciato.
- Pizza in pala: ~75% — alta. Forma allungata, mollica aperta.
- Pinsa romana: ~80% — molto alta, mix di farine.
- Pizza in teglia: 75-85% — altissima. Alta, leggera, alveolatura grande e aperta.

Più acqua = mollica più aperta e leggera, ma impasto più difficile da gestire (serve farina forte e tecniche come l'autolisi). Meno acqua = impasto docile e croccante, ma mollica più chiusa. Tutta la famiglia pizza vive su questa linea.

Il secondo asse: il fuoco (temperatura e tempo di cottura)

L'altro grande discriminante (vedi crosta e Maillard):
- Napoletana: 430-485°C per 60-90 secondi — fuoco estremo, esplosione del cornicione, leopardatura.
- Pala e teglia: 300-350°C per diversi minuti — forno elettrico, cottura più lunga e uniforme.
- Romana tonda: ~350°C per qualche minuto — croccantezza secca.

Più fuoco e meno tempo = esplosione, umidità interna trattenuta, macchie scure (napoletana). Meno fuoco e più tempo = asciugatura, croccantezza uniforme (romana, teglia). Il forno determina il carattere tanto quanto l'impasto.

Come i due assi generano le pizze

Metti insieme i due assi e capisci ogni pizza. Napoletana = media idratazione + fuoco estremo → morbida con cornicione esploso. Romana tonda = bassa idratazione + fuoco medio lungo → sottile e scrocchiarella. Teglia = altissima idratazione + fuoco medio lungo → alta, alveolata, leggera. Pala = alta idratazione + fuoco medio → via di mezzo allungata. Ogni "stile" è semplicemente una posizione sui due assi, con la farina e i tempi che si adeguano di conseguenza.

E c'è un legame con i pre-fermenti: le pizze a lunga maturazione e alta idratazione (teglia, pala, contemporanea) usano spesso poolish, biga o addirittura lievito madre, mentre la napoletana classica è più spesso a impasto diretto. La scelta del pre-fermento è un terzo asse più fine, che aggiunge aroma e struttura.

Il bersaglio, letto bene

Non un numero unico, ma la mappa in testa: due assi — acqua (dal 50% della scrocchiarella all'85% della teglia) e fuoco (dai 350°C lunghi ai 485°C brevissimi) — e ogni pizza è un punto su quel piano. E la cosa da ricordare: quando qualcuno ti nomina una pizza che non conosci, non chiedere la ricetta — chiedi due cose, quanta acqua e quanto forno, e saprai già che pane sarà. Le mille pizze sono due assi.""",
        "target": "La pizza è una famiglia su due assi: acqua (idratazione 50-85%) e fuoco (cottura 350-485°C) · ogni stile è un punto sul piano · napoletana media+estremo, romana bassa+medio, teglia alta+medio",
        "nome": "La famiglia pizza (napoletana, romana, teglia, pala)",
        "aliases": ["pizza","tipi di pizza","stili di pizza","famiglia pizza","che pizza"],
    },
    "prod-pizza-nap": {
        "scheda": """La pizza napoletana è il pane più semplice e più difficile del mondo: quattro ingredienti — farina, acqua, sale, lievito — e nient'altro. Niente olio, niente zucchero, niente scorciatoie. Eppure ottenere quel cornicione gonfio e maculato, quel centro morbido e umido, è questione di parametri precisi e di un forno che pochi hanno. Ecco la napoletana spiegata non come dogma, ma come i fenomeni che la governano — e perché il disciplinare dice quello che dice.

La vera pizza napoletana è una Specialità Tradizionale Garantita (STG), riconosciuta a livello europeo (Reg. UE 97/2010) e tutelata dal disciplinare dell'AVPN (Associazione Verace Pizza Napoletana, fondata a Napoli nel 1984). Ogni suo parametro è codificato — e ognuno ha una ragione fisica.

La formula, in percentuale del panettiere

I numeri del disciplinare, letti coi fenomeni:
- Farina 00 o 0, W 220-280 (media forza): 100%. Non una farina fortissima: la napoletana lievita "poche" ore e vuole estensibilità, non tenacità estrema (vedi la forza della farina).
- Acqua: 60-65% — idratazione media (vedi l'idratazione). Abbastanza per una mollica soffice e un cornicione alveolato, non così alta da rendere l'impasto ingestibile a mano.
- Sale marino: 50-55 g per litro d'acqua (circa 2,5-3% sulla farina) (vedi il sale).
- Lievito di birra fresco: pochissimo, 0,1-3 g/L — perché la lievitazione è lunga e lenta.
- Nient'altro. Niente grassi, niente zuccheri. Questo è il punto: la napoletana è un impasto "magro" (lean dough).

Perché niente olio (a differenza della focaccia)

Una domanda che i fenomeni chiariscono. La focaccia vive attorno all'olio; la napoletana lo esclude. Perché? Perché l'obiettivo è opposto. La focaccia vuole una mollica tenera e scioglievole (l'olio ammorbidisce). La napoletana vuole un cornicione che si gonfi in modo esplosivo nel forno caldissimo e una struttura che regga quella spinta: un impasto magro, con solo glutine e acqua, sviluppa una maglia glutinica forte ed elastica che intrappola i gas e permette l'esplosione del cornicione. L'olio, ammorbidendo il glutine, lavorerebbe contro quella spinta verticale. Stesso ingrediente-chiave (il grasso) che nella focaccia è protagonista e nella napoletana è bandito, per due obiettivi diversi. Questo è capire i fenomeni invece di seguire ricette.

La lievitazione: lunga, lenta, a temperatura ambiente

Il disciplinare prevede un impasto a 23-25°C (vedi la temperatura dell'impasto), poi una puntata (prima lievitazione di massa) di circa 2 ore, lo staglio in panetti da 250±20 g, e un appretto (seconda lievitazione dei panetti) di 4-6 ore. In totale 8-24 ore. Perché così lunga con così poco lievito? Perché la fermentazione lenta sviluppa aroma e digeribilità (le catene di amido e proteine si degradano), e una maglia matura e estensibile. È il fenomeno della fermentazione usato per il sapore, non solo per la spinta.

La stesura a schiaffo (mai il mattarello)

Un dettaglio tecnico con una ragione fisica precisa. La napoletana si stende a mano, con la tecnica "a schiaffo": si spinge l'aria dal centro verso il bordo, lasciando il cornicione gonfio di gas e schiacciando solo il centro. Il mattarello è vietato dal disciplinare — perché schiaccerebbe via tutto il gas anche dal cornicione, uccidendo l'alveolatura. Stendere a schiaffo è preservare i gas della lievitazione dove servono: nel bordo. È fisica dell'alveolatura applicata con le mani.

La cottura: il forno che fa la napoletana

Qui il parametro che quasi nessuno può replicare a casa, ed è decisivo. La napoletana STG si cuoce in forno a legna a 430-485°C per 60-90 secondi. Non un minuto di più. Perché questa temperatura estrema? Perché in 60-90 secondi il calore fortissimo fa esplodere il cornicione (l'acqua diventa vapore all'istante, i gas si espandono di colpo, oven spring massimo) e crea le "leopardature" — le macchie scure di Maillard e leggera carbonizzazione — prima che il centro si secchi. Un forno domestico a 250°C non può farlo: cuoce troppo lentamente, il centro si asciuga prima che il cornicione esploda. È per questo che la napoletana fatta a casa non è mai come in pizzeria: non è la ricetta, è il forno. È termodinamica.

Le trappole

Farina troppo forte → impasto troppo tenace, difficile da stendere a schiaffo. Troppo lievito → lievitazione veloce senza sviluppo aromatico, e sapore piatto. Forno non abbastanza caldo → niente esplosione del cornicione, pizza pallida e biscottata. Mattarello → cornicione morto. Troppo condimento bagnato al centro → il centro non cuoce e resta crudo ("pizza allagata").

Il bersaglio, letto bene

I numeri sono da disciplinare: idratazione 60-65%, panetto 250±20 g, impasto a 23-25°C, cottura 430-485°C per 60-90 secondi, cornicione alto 1-2 cm. Ma il vero bersaglio è capire che la napoletana è un impasto magro pensato per una cosa sola: esplodere in un forno caldissimo. Ogni scelta — la farina media, niente olio, la stesura a schiaffo — serve a preparare e preservare quell'esplosione. E la cosa da ricordare: la napoletana non si fa con la ricetta, si fa col forno. Senza i 450°C, è un'altra cosa. Capito questo, sai perché e sai cosa puoi (e non puoi) replicare.""",
        "target": "Idratazione 60-65%, panetto 250±20g, impasto 23-25°C, cottura forno legna 430-485°C per 60-90s, cornicione 1-2cm · impasto MAGRO senza olio (maglia forte per l'esplosione) · stesura a schiaffo · la fa il forno, non la ricetta",
        "nome": "Pizza napoletana STG",
        "aliases": ["pizza napoletana","napoletana","verace","pizza napoli","STG","AVPN"],
    },
    "prod-pizza-teglia": {
        "scheda": """La pizza in teglia romana è il pane più bagnato che farai: fino all'85% di acqua. Un impasto quasi liquido, che sembra impossibile da gestire — e invece è proprio quell'acqua estrema a darti la mollica altissima, piena di buchi, leggera come una nuvola. Ma a quell'idratazione servono farina forte, autolisi e pazienza, o l'impasto ti resta in mano.

La teglia romana (o pizza al taglio) vive all'estremo dell'asse idratazione: 75-85%, il massimo del mondo pizza. Quell'acqua è tutto il suo carattere — e tutta la sua difficoltà.

Perché così tanta acqua
Più acqua = mollica più aperta e leggera (vedi l'idratazione). All'85%, l'impasto è quasi una pastella: in cottura tutta quell'acqua diventa vapore e gonfia gli alveoli in modo estremo, dando quella mollica altissima e piena di buchi che è la firma della teglia. È l'opposto della napoletana media e compatta.

Il prezzo dell'acqua: farina forte e autolisi
A quell'idratazione l'impasto è ingestibile con farina normale. Servono due cose. Primo, farina forte (W320+, vedi la forza della farina): solo un glutine robusto regge tutta quell'acqua senza sfaldarsi. Secondo, l'autolisi (vedi il fenomeno): far riposare farina e acqua prima di impastare, così il glutine si sviluppa da solo e l'impasto diventa lavorabile. Senza questi due, l'85% ti resta appiccicato alle mani.

Le pieghe, non l'impasto classico
Un impasto così idratato non si impasta a mano nel modo classico: si gestisce con le pieghe (stretch and fold) a intervalli, che costruiscono la maglia glutinica senza lavorare una massa che è quasi liquida. Lunga maturazione in frigo (24-72h) per sapore e digeribilità.

La cottura
Forno elettrico (non a legna) a 250-300°C, spesso in due tempi: prima sul fondo per asciugare la base e far esplodere gli alveoli, poi con il condimento. Più lunga della napoletana perché la massa è alta e va cotta dentro.

Il bersaglio
Idratazione 75-85%, farina W320+, autolisi obbligatoria, maturazione lunga, cottura elettrica 250-300°C. Ma il vero bersaglio è capire che l'acqua estrema è insieme il pregio (mollica a nuvola) e la sfida (serve tecnica per domarla). Non è "più acqua a caso": è più acqua sostenuta da farina forte e autolisi. Togli quei supporti e l'acqua ti annega.""",
        "target": "Idratazione 75-85% estremo, farina W320+, autolisi obbligatoria, maturazione lunga, cottura elettrica 250-300C - acqua estrema fa la mollica a nuvola ma serve farina forte e autolisi",
        "nome": "Pizza in teglia romana",
        "aliases": ["pizza in teglia","teglia romana","pizza al taglio","teglia","alta idratazione"],
    },
    "prod-pizza-rom": {
        "scheda": """La pizza romana tonda è l'esatto opposto della napoletana: dove quella è morbida e alta, questa è sottile e scrocchia. "Scrocchiarella", la chiamano a Roma — deve fare rumore sotto i denti. E il segreto di quel rumore è meno acqua e un po' d'olio: l'inverso di tutto quello che fa la napoletana.

La romana tonda vive all'estremo basso dell'idratazione: 50-55%, il minimo del mondo pizza. Poca acqua, olio nell'impasto, stesa sottilissima al mattarello: tutto punta a una cosa, la croccantezza secca.

Perché poca acqua
Meno acqua = mollica più chiusa e croccante (vedi l'idratazione). Al 50-55% l'impasto è sodo, docile, si stende sottilissimo e in cottura non fa alveoli grandi: si asciuga e diventa una lastra croccante. È il contrario della teglia (85%, tutta buchi) e della napoletana (65%, morbida).

L'olio: friabilità
La romana ha olio nell'impasto (2-4%, vedi i grassi): non per morbidezza come nella focaccia, ma per friabilità — l'olio rende la struttura più corta, che si spezza netta invece di piegarsi. È ciò che dà lo "scrocchio".

Il mattarello (a differenza della napoletana)
Qui il mattarello è ammesso, anzi necessario: schiaccia via tutto il gas e stende sottilissimo e uniforme. Nella napoletana era vietato (avrebbe ucciso il cornicione); qui è lo strumento giusto, perché la romana NON vuole cornicione né alveoli — vuole essere piatta e croccante ovunque.

Cottura
~350°C per qualche minuto, spesso forno elettrico: più bassa e più lunga della napoletana, per asciugare bene tutta la lastra e renderla croccante fino al centro.

Il bersaglio
Idratazione 50-55%, olio 2-4%, mattarello, cottura ~350°C. Il vero bersaglio: capire che ogni scelta è l'inverso della napoletana, e per la stessa ragione fisica letta al contrario — poca acqua e olio per asciugare e spezzare, invece di tanta spinta per gonfiare. Due pizze agli antipodi dello stesso asse.""",
        "target": "Idratazione 50-55% minimo, olio 2-4%, mattarello, cottura ~350C - la scrocchiarella, ogni scelta e l inverso della napoletana",
        "nome": "Pizza romana tonda (scrocchiarella)",
        "aliases": ["pizza romana","romana","scrocchiarella","pizza scrocchiarella","tonda romana"],
    },
    "prod-pizza-pala": {
        "scheda": """La pizza in pala sta a metà strada: più idratata della napoletana, meno estrema della teglia. Il suo nome viene dalla forma — lunga e stretta come la pala del fornaio — e il suo pregio è pratico: si fa in grande, si taglia, si serve in fretta. È la pizza del servizio ad alto volume.

La pala vive nella parte alta dell'asse idratazione (~75%): mollica aperta e leggera, ma un po' più gestibile della teglia all'85%. Forma allungata, cottura elettrica.

L'idratazione e i pre-fermenti
Al 75% serve comunque farina forte e spesso un pre-fermento (poolish, biga o anche lievito madre, vedi i pre-fermenti): la lunga maturazione dà aroma e la struttura per reggere l'acqua. Mollica alveolata, leggera, digeribile.

La forma funzionale
La pala non è solo estetica: la forma lunga e stretta permette di infornarla e sfornarla con la pala del fornaio, tagliarla in tranci e servirla veloce. È nata per il servizio — pizzerie al taglio, alti volumi. Va ben cotta sotto, così il trancio regge il condimento senza afflosciarsi quando lo tieni in mano.

Cottura
Forno elettrico 300-350°C, resistenze ben distribuite: la base deve cuocere a fondo. Più lunga della napoletana, per asciugare e irrigidire il fondo.

Il bersaglio
Idratazione ~75%, forma a pala, pre-fermento consigliato, cottura elettrica 300-350°C ben cotta sotto. Il vero bersaglio: la pala è la via di mezzo pratica — l'ariosità dell'alta idratazione, ma domata per il servizio veloce. Un compromesso intelligente tra qualità e operatività.""",
        "target": "Idratazione ~75%, forma a pala, pre-fermento consigliato, cottura elettrica 300-350C ben cotta sotto - la via di mezzo pratica per il servizio",
        "nome": "Pizza in pala",
        "aliases": ["pizza in pala","pala","pizza alla pala","pala romana"],
    },
    "prod-ciabatta": {
        "scheda": """La ciabatta non è un pane antico: l'ha inventata un fornaio a Adria nel 1982 per dare all'Italia una risposta alla baguette francese. Ma è diventata un classico perche fa una cosa benissimo: mollica enorme e aperta, crosta sottile e croccante, tutto grazie a due leve — tantissima acqua e la biga.

La ciabatta vive nell'alta idratazione (~80%): mollica piena di buchi grandi, quella che assorbe l'olio quando ci fai la scarpetta. Forma libera, rustica, "a ciabatta" (da cui il nome).

L'acqua alta e la biga
Come la teglia romana, l'80% di idratazione (vedi il fenomeno) da la mollica aperta e leggera. E come la maggior parte dei pani strutturati, usa un pre-fermento: la biga (vedi poolish e biga), il pre-fermento italiano sodo, che da forza, aroma e struttura per reggere l'acqua. Biga italiana vs poolish francese: stessa idea, la biga e piu asciutta.

L'olio (a differenza della baguette)
Molte ciabatte hanno olio d'oliva nell'impasto: modifica il glutine rendendolo piu estensibile, aiuta l'alta idratazione a stendersi, e da una mollica piu tenera. E la differenza mediterranea dalla baguette francese, che e magra (senza grassi).

Il bersaglio
Idratazione ~80%, biga, olio opzionale, mollica aperta e crosta sottile. Il vero bersaglio: capire che la ciabatta e la risposta italiana alla baguette, e la vince sull'apertura della mollica proprio grazie all'acqua alta e all'olio che la baguette non ha.""",
        "target": "Idratazione ~80%, biga, olio opzionale, mollica aperta e crosta sottile - la risposta italiana alla baguette (1982), vince sull apertura grazie ad acqua alta e olio",
        "nome": "Ciabatta",
        "aliases": ["ciabatta","pane ciabatta"],
    },
    "prod-baguette": {
        "scheda": """La baguette vera — la "tradition" — e un pane magro e severo: solo farina, acqua, lievito, sale, niente grassi. Il suo virtuosismo non e negli ingredienti ma nella tecnica: il poolish che le da il sapore, i tagli che le danno la forma, la crosta sottile e cantante che scrocchia appena la spezzi.

La baguette vive nell'idratazione media-alta (65-70%): mollica aperta ma non estrema come la ciabatta, crosta sottilissima e croccante, forma lunga e precisa (a differenza della ciabatta rustica e libera).

Il poolish: il sapore
Il segreto della baguette non e nell'impasto del giorno, ma nella notte prima: il poolish (vedi poolish e biga), il pre-fermento liquido francese, che matura ore e da alla baguette quella complessita leggermente acidula che una baguette diretta non ha. Poolish francese vs biga italiana: il poolish e liquido (50/50 acqua e farina).

Magra, come la napoletana
La baguette e un impasto magro: niente olio, niente grassi (a differenza della ciabatta). Solo glutine e acqua sviluppano una maglia forte, per una crosta sottile e croccante e una mollica con alveoli irregolari. Il grasso la ammorbidirebbe, e la baguette vuole croccantezza.

I tagli (grigne)
Prima del forno, tagli obliqui sulla superficie con una lametta: le "grigne". Non sono decorazione — governano dove il pane si apre in cottura (l'oven spring esce dai tagli in modo controllato, invece di spaccarsi a caso). Tagli fatti bene = quella cresta caratteristica che si apre e dora.

Il bersaglio
Idratazione 65-70%, poolish, impasto magro, tagli obliqui, crosta sottile. Il vero bersaglio: la baguette e tecnica pura su ingredienti poverissimi — il poolish per il sapore, i tagli per la forma, la magrezza per la croccantezza. Niente si nasconde: o la tecnica e giusta, o si vede.""",
        "target": "Idratazione 65-70%, poolish, impasto magro, tagli obliqui (grigne), crosta sottile - tecnica pura su ingredienti poverissimi: poolish per il sapore, tagli per la forma",
        "nome": "Baguette tradition",
        "aliases": ["baguette","baguette tradition","pane francese","filoncino francese"],
    },
    "prod-michetta": {
        "scheda": """La michetta (a Roma rosetta) e un pane che sfida la logica: dentro e vuota. Una cupola cava, con pochissima mollica, nata a Milano nell'Ottocento copiando il Kaisersemmel austriaco. E quel vuoto non e un difetto: e il suo scopo — un guscio croccante da riempire.

La michetta insegna una cosa che nessun altro pane insegna: come ottenere un pane CAVO di proposito. Il segreto e nella forma — la piega a rosa (i cinque spicchi) e una stesura che intrappola l'aria in una grande bolla centrale invece che in tanti alveoli. In cottura il vapore gonfia quella bolla e la crosta si fissa prima che collassi: resta il vuoto. Poca mollica, tanto guscio. Serviva agli operai per riempirla di companatico senza che si inzuppasse.
Lezione: la STRUTTURA CAVA governata dalla forma. Farina media, bassa idratazione, la piega fa tutto.""",
        "target": "Pane CAVO di proposito: la piega a rosa intrappola l aria in una bolla centrale, il vapore la gonfia, la crosta si fissa prima di collassare - poca mollica tanto guscio, per riempirlo",
        "nome": "Michetta (rosetta)",
        "aliases": ["michetta", "rosetta", "pane cavo"],
    },
    "prod-pane-sciapo": {
        "scheda": """Il pane toscano e umbro non ha sale. Non e una dimenticanza: e una scelta antica, e insegna piu di ogni altro pane cosa fa davvero il sale — facendone sentire l'assenza.

Togli il sale e vedi i suoi quattro lavori mancare tutti insieme (vedi il fenomeno del sale): la fermentazione corre senza freno (il sale la rallenta), la maglia glutinica e piu debole e appiccicosa (il sale la rinforza), la crosta resta pallida (il sale aiuta il colore), e il sapore e piatto. Il pane sciapo e insipido da solo — ma e nato apposta: accompagna salumi e formaggi saporiti (prosciutto toscano, pecorino), dove un pane salato coprirebbe tutto. Il pane neutro fa da tela.
Lezione: il SALE per ASSENZA. Capisci cosa fa vedendo cosa succede senza. E la gastronomia dell'abbinamento (pane neutro + companatico saporito).""",
        "target": "Il SALE per assenza: senza sale la fermentazione corre, la maglia e debole, la crosta pallida, il sapore piatto - nato per accompagnare salumi e formaggi saporiti",
        "nome": "Pane sciapo (toscano senza sale)",
        "aliases": ["pane sciapo", "pane toscano", "pane senza sale", "pane sciocco", "pane umbro"],
    },
    "prod-altamura": {
        "scheda": """Il pane di Altamura non usa farina di grano tenero come quasi tutti i pani italiani: usa semola rimacinata di grano DURO. E questo cambia tutto — colore, sapore, conservazione, crosta.

Il grano duro (quello della pasta) ha un glutine diverso e piu tenace, e una semola piu grossa e gialla. Da una mollica gialla e compatta, un sapore piu intenso e "di grano", una crosta spessa e scura, e una conservazione lunghissima (giorni). E il primo pane in Europa ad avere la DOP. Cotto in forno a legna di quercia, con lievito madre. La lezione: la FARINA cambia il pane alla radice — non e solo forza (W), e proprio il tipo di grano.
Lezione: GRANO DURO vs tenero. La farina come scelta identitaria, non solo tecnica.""",
        "target": "GRANO DURO non tenero: semola rimacinata, mollica gialla compatta, sapore intenso, crosta spessa, conservazione lunga - primo pane DOP d Europa",
        "nome": "Pane di Altamura DOP",
        "aliases": ["altamura", "pane di altamura", "pane pugliese", "semola dura"],
    },
    "prod-carasau": {
        "scheda": """Il carasau sardo — "carta da musica" — e sottile come un foglio e croccante come una cialda. Il suo segreto e la DOPPIA cottura: si cuoce, si separa in due sfoglie, e si rimette in forno. E quella seconda cottura che lo rende secco e conservabile per mesi.

La prima cottura fa gonfiare il disco che si separa in due veli. Li si taglia, e la seconda cottura (la "carasatura") asciuga tutta l'acqua residua: senza acqua, niente puo deteriorarlo (vedi shelf-life e attivita dell'acqua). Nato per i pastori che stavano mesi fuori: pane che non ammuffisce. La lezione: togliere l'ACQUA e conservare — la fisica opposta al pane fresco.
Lezione: DOPPIA COTTURA e conservazione per disidratazione. L'acqua (o la sua assenza) governa la shelf-life.""",
        "target": "DOPPIA cottura e disidratazione: si separa in due veli e si ricuoce (carasatura), senza acqua niente lo deteriora - pane che dura mesi",
        "nome": "Pane carasau (carta da musica)",
        "aliases": ["carasau", "carta da musica", "pane sardo", "pane secco"],
    },
    "prod-croissant": {
        "scheda": """Il croissant e il capolavoro della laminazione: un impasto lievitato in cui pieghi decine di strati di burro, e in forno diventa quella meraviglia di fuori croccante e dentro a nido d'ape. Non e un pane e non e una sfoglia: sta in mezzo, e prende il meglio di entrambi.

Il croissant e viennoiserie: impasto lievitato (come il pane) MA laminato col burro (come la sfoglia). Da qui la sua doppia natura — la spinta del lievito piu la separazione a strati del vapore.

La laminazione (vedi il fenomeno)
Si parte dalla detrempe (l'impasto base: farina, acqua, latte, lievito, zucchero, sale) e dal panetto di burro. Si chiude il burro nell'impasto e si piega piu volte (le "pieghe" o "turni"): ogni piega moltiplica gli strati, e dopo 3-4 turni hai decine di strati alterni burro-impasto sottilissimi. In forno l'acqua del burro diventa vapore e separa gli strati: ecco la sfogliatura.

La temperatura del burro: il punto critico
Il burro va tenuto a 16-18°C: freddo ma plastico. Troppo caldo si spalma e gli strati si fondono (croissant pesante, "brioche-oso"); troppo freddo si rompe e buca l'impasto. Si riposa in frigo tra una piega e l'altra per rilassare il glutine e rassodare il burro. Burro europeo ad alto grasso, piu plastico.

Il bersaglio
Laminazione con burro a 16-18°C, 3-4 pieghe, lievitato + laminato, forno caldo. Il vero bersaglio: il croissant e temperatura e mano leggera — il burro deve restare uno strato, mai fondersi. Se tieni il burro dov'e, la sfoglia viene da se.""",
        "target": "Laminazione con burro a 16-18C, 3-4 pieghe, lievitato+laminato - temperatura e mano leggera, il burro deve restare uno strato mai fondersi",
        "nome": "Croissant",
        "aliases": ["croissant", "cornetto", "brioche sfogliata"],
    },
    "prod-pain-chocolat": {
        "scheda": """Il pain au chocolat e un croissant che ha cambiato forma: stesso impasto laminato, ma steso rettangolare e arrotolato attorno a due barrette di cioccolato. La tecnica e identica al croissant — cambia solo la piega finale e il ripieno.

Stessa pasta viennoiserie laminata del croissant (vedi laminazione). La differenza e nel modellare: invece del triangolo arrotolato a mezzaluna, un rettangolo con due stecche di cioccolato, arrotolato dritto. Il cioccolato deve reggere la cottura senza bruciare: barrette apposite ("batons"), non gocce.
Lezione: la stessa tecnica, forma e ripieno diversi. Mostra che la laminazione e una BASE da cui derivano molti prodotti.""",
        "target": "Stessa pasta laminata del croissant, forma rettangolare arrotolata su barrette di cioccolato - stessa tecnica forma e ripieno diversi",
        "nome": "Pain au chocolat",
        "aliases": ["pain au chocolat", "pain o chocolat", "cioccolatino", "croissant al cioccolato"],
    },
    "prod-brioche-viennoiserie": {
        "scheda": """La brioche e l'opposto istruttivo del croissant: e ricchissima di burro e uova, ma NON e laminata. Il burro non e in strati — e impastato dentro. E questo cambia tutto: dove il croissant e a sfoglia, la brioche e a mollica fitta e vellutata.

La brioche insegna per contrasto col croissant. Entrambi ricchi di burro, ma: nel croissant il burro sta in STRATI (laminazione → sfoglia); nella brioche il burro e IMPASTATO nella massa (→ mollica uniforme, tenera, ricca). Stesso ingrediente (burro), due modi di usarlo, due risultati opposti. La brioche e un impasto lievitato arricchito (burro, uova, latte, zucchero) — il confine tra pane e dolce.

Il burro impastato
Il burro si incorpora poco a poco nell'impasto gia sviluppato, morbido, fino a una massa lucida e elastica. E il grasso che riveste il glutine (vedi i grassi nell'impasto) a dare la tenerezza e la mollica gialla che si affetta pulita.
Lezione: burro IN STRATI (croissant) vs burro IMPASTATO (brioche). Il come, non solo il quanto.""",
        "target": "Burro e uova ricchissimi ma NON laminata: il burro impastato nella massa (non in strati) da mollica fitta e vellutata - il contrario del croissant",
        "nome": "Brioche",
        "aliases": ["brioche", "pan brioche", "brioche francese"],
    },
    "prod-impasto-rosticceria": {
        "scheda": """A Palermo la rosticceria e un solo impasto che diventa mille cose: pizzette, rollo, ravazzate, panzerotti. Una pasta brioche soffice con lo strutto, dal sapore neutro, che regge sia il forno sia la frittura. Impari questo, e hai la base di tutta la rosticceria.

E una pasta lievitata arricchita con strutto (non burro): lo strutto (vedi i grassi nell'impasto) da morbidezza e scioglievolezza, e regge bene la frittura. Sapore neutro apposta, per accogliere ripieni salati. Da questo unico impasto: al forno (ravazzate, spennellate d'uovo) o fritto (panzerotti). Un impasto, tante forme — come la famiglia pizza.
Lezione: un impasto-madre versatile. Lo strutto come grasso della tradizione. Forno E frittura dalla stessa base.""",
        "target": "Un solo impasto brioche con strutto (neutro, morbido) diventa pizzette, rollo, ravazzate, panzerotti - forno E frittura dalla stessa base",
        "nome": "Impasto rosticceria siciliana",
        "aliases": ["rosticceria", "impasto rosticceria", "pasta brioche siciliana", "rosticceria palermitana", "pezzi"],
    },
    "prod-arancina": {
        "scheda": """L'arancina (o arancino) e una palla di riso ripiena, impanata e fritta. Ma la sua magia sta in un doppio guscio: la panatura che frigge croccante fuori, e il riso compatto che tiene tutto dentro. E un esercizio di ingegneria del fritto.

Il riso cotto e raffreddato (l'amido retrogradato lo rende compatto e modellabile, vedi la retrogradazione) si forma attorno al ripieno (ragu, burro, ecc.). Poi impanatura (farina, uovo, pangrattato) e frittura a 170-180°C (vedi la frittura di lievitati — qui e riso, ma vale il principio del sigillo). La panatura sigilla e dora, il riso resta cremoso dentro. Contrasto croccante/cremoso.
Lezione: la PANATURA come guscio sigillante. Il riso retrogradato come struttura. Doppio contrasto.""",
        "target": "Riso retrogradato (compatto) attorno al ripieno, panatura che sigilla e dora in frittura - contrasto croccante fuori cremoso dentro",
        "nome": "Arancina",
        "aliases": ["arancina", "arancino", "arancini", "arancine", "palla di riso"],
    },
    "prod-bagel": {
        "scheda": """Il bagel non e solo un panino col buco: e l'unico pane che si BOLLE prima di infornarlo. Quel passaggio nell'acqua — spesso con malto o miele — e tutto il suo segreto: gli da la crosta lucida e la mollica densa e gommosa che nessun pane al forno ha.

Il bagel si forma ad anello, poi si tuffa in acqua bollente per 30-60 secondi prima del forno. La bollitura gelatinizza l'amido in superficie (vedi la gelatinizzazione): si forma una pelle che poi in forno diventa lucida e soda, e blocca l'espansione — cosi la mollica resta densa e gommosa invece che soffice. Piu a lungo bolle, piu e gommoso. Spesso nell'acqua c'e malto o miele: zuccheri che aiutano doratura e sapore.
Lezione: la BOLLITURA pre-forno. Gelatinizzare la superficie per crosta lucida e mollica densa.""",
        "target": "Unico pane BOLLITO prima del forno: la bollitura gelatinizza la superficie (crosta lucida) e blocca l espansione (mollica densa gommosa) - piu bolle piu e gommoso",
        "nome": "Bagel",
        "aliases": ["bagel", "baigel", "pane bollito", "ciambella di pane"],
    },
    "prod-pretzel": {
        "scheda": """Il pretzel ha quel colore mogano scuro e quel sapore inconfondibile grazie a un trucco di chimica: prima del forno si immerge in un bagno ALCALINO — soda caustica o bicarbonato. Non e il forno a fare quel colore: e il pH.

La reazione di Maillard (vedi il fenomeno) — la doratura — e accelerata in ambiente alcalino. La farina e naturalmente acida (pH 6), il che frena la doratura. Immergendo il pretzel in una soluzione basica (lye pH 12, o bicarbonato pH 8-10), si alza il pH della superficie e la Maillard esplode: crosta scura, lucida, mogano, con quel sapore alcalino tipico. I professionisti usano la soda caustica (lye), a casa il bicarbonato (piu debole, colore meno intenso). Trucco: cuocere il bicarbonato in forno lo trasforma in carbonato, piu forte.
Lezione: il pH governa la Maillard. Ambiente alcalino = doratura accelerata. Chimica di superficie.""",
        "target": "Bagno ALCALINO pre-forno (lye o bicarbonato): il pH alto accelera la Maillard, crosta mogano scura lucida e sapore alcalino - non il forno, il pH fa il colore",
        "nome": "Pretzel (bretzel)",
        "aliases": ["pretzel", "bretzel", "brezel", "pane alcalino"],
    },
    "prod-bao": {
        "scheda": """Il bao cinese sfida un'idea che diamo per scontata: che il pane si cuocia in forno. Il bao si cuoce al VAPORE, e per questo e bianco come la neve, morbidissimo, senza crosta. Niente forno, niente doratura — un altro mondo.

Cotto in cestelli di bambu sopra acqua bollente (~100°C, molto meno del forno). A quella temperatura NON avviene la Maillard (serve calore secco e alto): per questo il bao resta bianco, senza crosta, con una superficie liscia e soffice. Il vapore mantiene tutto umido: mollica tenerissima. Impasto spesso con un po' di zucchero e strutto, e a volte lievito chimico oltre a quello di birra per l'estrema sofficita.
Lezione: cottura a VAPORE vs forno. Niente Maillard = niente crosta = pane bianco e soffice. La temperatura di cottura decide tutto.""",
        "target": "Cottura a VAPORE non forno (~100C): niente Maillard = niente crosta = pane bianco soffice senza doratura - la temperatura di cottura decide tutto",
        "nome": "Bao (pane al vapore)",
        "aliases": ["bao", "baozi", "pane al vapore", "panino cinese", "mantou", "pane cinese"],
    },
    "prod-soda-bread": {
        "scheda": """Il soda bread irlandese non ha lievito e non aspetta: si impasta e si inforna subito. Al posto del lievito usa il bicarbonato, che con l'acido del latticello reagisce all'istante e libera gas. Un pane pronto in un'ora, nato per chi non aveva ne tempo ne lievito.

Lievitazione CHIMICA, non biologica: il bicarbonato di sodio (base) reagisce con un acido (il latticello, buttermilk) in presenza di liquido, e produce CO2 subito (vedi la fermentazione per contrasto: qui NON e fermentazione, e una reazione acido-base istantanea). Niente attesa, niente maglia glutinica sviluppata: mollica piu compatta, briciolosa, quasi da scone. Il taglio a croce in superficie non e decorazione: aiuta il pane a espandersi e cuocere uniforme.
Lezione: lievitazione CHIMICA (acido+base→CO2 immediata) vs biologica (lievito, ore). Due modi opposti di gonfiare il pane.""",
        "target": "Lievitazione CHIMICA non biologica: bicarbonato + acido del latticello = CO2 istantanea, pronto in un ora, mollica compatta briciolosa - il taglio a croce aiuta l espansione",
        "nome": "Soda bread irlandese",
        "aliases": ["soda bread", "pane irlandese", "pane al bicarbonato", "pane senza lievito", "pane veloce"],
    },
    "prod-bagel": {
        "scheda": """Il bagel non e solo un panino col buco: e l'unico pane che si BOLLE prima di infornarlo. Quel passaggio nell'acqua — spesso con malto o miele — e tutto il suo segreto: gli da la crosta lucida e la mollica densa e gommosa che nessun pane al forno ha.

Il bagel si forma ad anello, poi si tuffa in acqua bollente per 30-60 secondi prima del forno. La bollitura gelatinizza l'amido in superficie (vedi la gelatinizzazione): si forma una pelle che poi in forno diventa lucida e soda, e blocca l'espansione — cosi la mollica resta densa e gommosa invece che soffice. Piu a lungo bolle, piu e gommoso. Spesso nell'acqua c'e malto o miele: zuccheri che aiutano doratura e sapore.
Lezione: la BOLLITURA pre-forno. Gelatinizzare la superficie per crosta lucida e mollica densa.""",
        "target": "Unico pane BOLLITO prima del forno: la bollitura gelatinizza la superficie (crosta lucida) e blocca l espansione (mollica densa gommosa)",
        "nome": "Bagel",
        "aliases": ["bagel", "baigel", "pane bollito", "ciambella di pane"],
    },
    "prod-pretzel": {
        "scheda": """Il pretzel ha quel colore mogano scuro e quel sapore inconfondibile grazie a un trucco di chimica: prima del forno si immerge in un bagno ALCALINO — soda caustica o bicarbonato. Non e il forno a fare quel colore: e il pH.

La reazione di Maillard (vedi il fenomeno) — la doratura — e accelerata in ambiente alcalino. La farina e naturalmente acida (pH 6), il che frena la doratura. Immergendo il pretzel in una soluzione basica (lye pH 12, o bicarbonato pH 8-10), si alza il pH della superficie e la Maillard esplode: crosta scura, lucida, mogano, con quel sapore alcalino tipico. I professionisti usano la soda caustica (lye), a casa il bicarbonato (piu debole, colore meno intenso). Trucco: cuocere il bicarbonato in forno lo trasforma in carbonato, piu forte.

SICUREZZA (leggi prima di usare la soda caustica). L'idrossido di sodio (soda caustica, lye) e una sostanza CORROSIVA: e lo stesso composto dei prodotti per sturare i tubi. Cruda, ustiona la pelle e puo danneggiare gli occhi in modo permanente. Chi la usa deve indossare guanti di gomma, occhiali protettivi, maniche lunghe, e lavorare in spazio ventilato, tenendola lontana dai bambini. IMPORTANTE: il pretzel COTTO e sicuro — nel forno la soda si neutralizza (reagisce con la CO2 e con l'impasto, diventando carbonato di sodio, innocuo). Il pericolo e solo nel maneggiarla prima della cottura. A CASA, o se hai qualsiasi dubbio, usa il bicarbonato di sodio sciolto in acqua (meglio ancora "cotto" in forno a 120C per un ora per renderlo piu forte): stessa chimica, molto piu debole ma del tutto sicuro.

Lezione: il pH governa la Maillard. Ambiente alcalino = doratura accelerata. Chimica di superficie. E: una tecnica potente porta con se la sua responsabilita di sicurezza.""",
        "target": "Bagno ALCALINO pre-forno (lye o bicarbonato): il pH alto accelera la Maillard, crosta mogano scura lucida - ATTENZIONE soda caustica corrosiva, a casa usa bicarbonato",
        "nome": "Pretzel (bretzel)",
        "aliases": ["pretzel", "bretzel", "brezel", "pane alcalino", "laugengeback", "soda caustica", "lye"],
    },
    "prod-bao": {
        "scheda": """Il bao cinese sfida un'idea che diamo per scontata: che il pane si cuocia in forno. Il bao si cuoce al VAPORE, e per questo e bianco come la neve, morbidissimo, senza crosta. Niente forno, niente doratura — un altro mondo.

Cotto in cestelli di bambu sopra acqua bollente (~100°C, molto meno del forno). A quella temperatura NON avviene la Maillard (serve calore secco e alto): per questo il bao resta bianco, senza crosta, con una superficie liscia e soffice. Il vapore mantiene tutto umido: mollica tenerissima. Impasto spesso con un po' di zucchero e strutto, e a volte lievito chimico oltre a quello di birra per l'estrema sofficita.
Lezione: cottura a VAPORE vs forno. Niente Maillard = niente crosta = pane bianco e soffice. La temperatura di cottura decide tutto.""",
        "target": "Cottura a VAPORE non forno (~100C): niente Maillard = niente crosta = pane bianco soffice - la temperatura di cottura decide tutto",
        "nome": "Bao (pane al vapore)",
        "aliases": ["bao", "baozi", "pane al vapore", "panino cinese", "mantou", "pane cinese"],
    },
    "prod-soda-bread": {
        "scheda": """Il soda bread irlandese non ha lievito e non aspetta: si impasta e si inforna subito. Al posto del lievito usa il bicarbonato, che con l'acido del latticello reagisce all'istante e libera gas. Un pane pronto in un'ora, nato per chi non aveva ne tempo ne lievito.

Lievitazione CHIMICA, non biologica: il bicarbonato di sodio (base) reagisce con un acido (il latticello, buttermilk) in presenza di liquido, e produce CO2 subito (vedi la fermentazione per contrasto: qui NON e fermentazione, e una reazione acido-base istantanea). Niente attesa, niente maglia glutinica sviluppata: mollica piu compatta, briciolosa, quasi da scone. Il taglio a croce in superficie non e decorazione: aiuta il pane a espandersi e cuocere uniforme.
Lezione: lievitazione CHIMICA (acido+base→CO2 immediata) vs biologica (lievito, ore). Due modi opposti di gonfiare il pane.""",
        "target": "Lievitazione CHIMICA non biologica: bicarbonato + acido del latticello = CO2 istantanea, pronto in un ora, mollica compatta",
        "nome": "Soda bread irlandese",
        "aliases": ["soda bread", "pane irlandese", "pane al bicarbonato", "pane senza lievito", "pane veloce"],
    },
    "prod-focaccia": {
        "scheda": """La focaccia genovese sembra il pane più semplice del mondo: farina, acqua, lievito, sale, olio. Eppure quasi nessuno, fuori dalla Liguria, la fa come si deve. Il segreto non è un ingrediente nascosto: è capire che ogni scelta — quanta acqua, quanto olio, le fossette, la salamoia — non è tradizione a caso, ma fisica del pane applicata. Ecco la focaccia spiegata non come ricetta da copiare, ma come i fenomeni che la governano.

La focaccia genovese autentica (Focaccia Genovese, tutelata IGP e persino Presidio Slow Food) è alta 1,5-2 centimetri, con mollica leggera e ariosa, superficie dorata e lucida punteggiata di fossette piene di una salamoia di olio. Non è la lastra alta 4-5 cm dei ristoranti fuori Italia: è più sottile, e ogni suo parametro ha una ragione scientifica.

La formula, in percentuale del panettiere

I numeri del disciplinare, letti col linguaggio dei fenomeni:
- Farina (00 o 0): 100% (la base di riferimento)
- Acqua: 55-65% — idratazione media (vedi il fenomeno dell'idratazione). Non altissima come una ciabatta: la focaccia vuole una mollica ariosa ma con struttura, che regga le fossette e l'olio.
- Olio EVO nell'impasto: almeno il 10% sul peso della farina — più della gran parte dei pani (vedi i grassi nell'impasto). L'olio ammorbidisce la mollica e la rende tenera, e dà quella scioglievolezza.
- Sale: circa 2% (vedi il sale nell'impasto).
- Lievito: piccola quantità, per una lievitazione lenta.
- Un tocco di miele o malto: nutre il lievito e aiuta la doratura.
- Più olio abbondante in teglia e in superficie.

Perché quell'idratazione, non di più

Una domanda che il fenomeno dell'idratazione ti aiuta a rispondere. Perché la focaccia sta al 55-65% e non all'80% come una ciabatta? Perché la focaccia deve reggere due cose che la ciabatta non ha: le fossette (che devono restare, non richiudersi) e l'olio (che è un peso). Un'idratazione troppo alta darebbe un impasto troppo molle per tenere le fossette e per non annegare nell'olio. Il 55-65% è il punto dove la mollica è ariosa ma la struttura tiene. È la scienza dell'idratazione applicata a un obiettivo preciso.

L'olio: dentro e fuori, due lavori diversi

L'olio nella focaccia fa il lavoro che conosci dai grassi nell'impasto, ma in due posti. Dentro l'impasto (il 10%+), riveste il glutine e ammorbidisce la mollica, la rende tenera e scioglievole — è lo shortening. Fuori, in teglia e in superficie, fa un'altra cosa: frigge leggermente il fondo e i bordi (crosta croccante e dorata) e, in superficie, dà la lucentezza e il sapore. Lo stesso ingrediente, due funzioni, in due punti. Per questo la focaccia genovese usa "scandalosamente" tanto olio: non è eccesso, è tecnica.

La salamoia: il gesto che definisce la focaccia

Ecco il cuore, il passaggio che distingue la genovese da ogni altra flatbread. Prima di infornare, si preparano le fossette premendo con le dita (fino a circa 1 cm, non fino al fondo), e ci si versa la salamoia: un'emulsione temporanea di acqua, olio e sale sbattuti insieme. Perché funziona, spiegato per fenomeni: l'acqua della salamoia, in forno, diventa vapore (come nella lievitazione) e tiene l'interno umido e morbido mentre la superficie si asciuga; l'olio dà la doratura lucida e il sapore; il sale in superficie sala e aiuta la crosta. Le fossette non sono decorazione: sono conche che raccolgono la salamoia e la trattengono, creando quelle isole di sapore e umidità. È emulsione + vapore + Maillard, tutto in un gesto.

Il procedimento, per fasi (e il fenomeno di ognuna)

1. Impasto: sciogli il lievito in acqua tiepida (non calda, uccideresti il lievito — vedi temperatura dell'impasto) con un pizzico di miele. Aggiungi farina, poi il sale, infine l'olio, e impasta fino a liscio ed elastico (maglia glutinica).
2. Prima lievitazione: 1-2 ore fino al raddoppio (fermentazione/lievitazione). Molti fanno una lievitazione lenta in frigo tutta la notte per più sapore (la temperatura bassa rallenta e aromatizza).
3. Stesura: stendi in teglia ben oliata, senza strappare.
4. Fossette + salamoia: premi le fossette, versa la salamoia.
5. Seconda lievitazione: 40-60 minuti scoperta.
6. Cottura: forno caldo 220-230°C per 15-20 minuti, fino a dorata e lucida. Non oltre: si secca.

Le trappole (dove sbagliano quasi tutti)

Cottura troppo veloce o idratazione insufficiente → manca la mollica ariosa, viene compatta. Troppo poco olio ("versione salutista") → perdi la crosta e il carattere: nella genovese l'olio non si taglia. Sovracottura → si secca, ed è il modo più comune di rovinarla. Fossette fatte fino al fondo → l'olio cola sotto e la focaccia si buca.

Il bersaglio, letto bene

I numeri ci sono e sono da disciplinare: idratazione 55-65%, olio ≥10% sulla farina, spessore finale 1,5-2 cm, cottura 220-230°C. Ma il vero bersaglio è capire che la focaccia è un sistema di fenomeni in equilibrio: l'idratazione che regge le fossette, l'olio che ammorbidisce dentro e frigge fuori, la salamoia che fa vapore e doratura. Cambia un parametro e sposti tutto. E la cosa da ricordare: la focaccia non è un pane con l'olio sopra — è un pane pensato attorno all'olio, dall'impasto alla salamoia. Capito questo, la fai bene ovunque.""",
        "target": "Idratazione 55-65% (regge fossette e olio), olio EVO ≥10% sulla farina, spessore finale 1,5-2cm, cottura 220-230°C · la salamoia (acqua+olio+sale) fa vapore e doratura · il pane pensato attorno all'olio",
        "nome": "Focaccia genovese",
        "aliases": ["focaccia","focaccia genovese","focaccia ligure","fugassa"],
    },
}
CABLA_PANIFICATI = {
    "prod-focaccia": ["fen-grassi-impasto","fen-idratazione","fen-sale-impasto","fen-maillard","fen-crosta"],
    "prod-pizza-nap": ["fen-idratazione","fen-farina-forza","fen-maglia-glutinica","fen-lievitazione","fen-temperatura-impasto","fen-maillard"],
    "prod-pizza-teglia": ["fen-idratazione","fen-farina-forza","fen-autolisi","fen-lievitazione","fen-crosta"],
    "prod-pizza-rom": ["fen-idratazione","fen-grassi-impasto","fen-maglia-glutinica","fen-crosta"],
    "prod-pizza-pala": ["fen-idratazione","fen-farina-forza","fen-lievitazione","fen-crosta"],
    "prod-ciabatta": ["fen-idratazione","fen-poolish-biga","fen-grassi-impasto","fen-maglia-glutinica"],
    "prod-baguette": ["fen-idratazione","fen-poolish-biga","fen-crosta","fen-maglia-glutinica"],
    "prod-michetta": ["fen-lievitazione","fen-crosta","fen-maglia-glutinica"],
    "prod-pane-sciapo": ["fen-sale-impasto","fen-fermentazione","fen-crosta"],
    "prod-altamura": ["fen-farina-forza","fen-lievito-madre","fen-crosta","fen-shelf-life-pane"],
    "prod-carasau": ["fen-shelf-life-pane","fen-gelatinizzazione","fen-crosta"],
    "prod-croissant": ["fen-laminazione","fen-grassi-impasto","fen-lievitazione","fen-maillard"],
    "prod-pain-chocolat": ["fen-laminazione","fen-grassi-impasto","fen-lievitazione"],
    "prod-brioche-viennoiserie": ["fen-grassi-impasto","fen-uova-impasto","fen-lievitazione"],
    "prod-impasto-rosticceria": ["fen-grassi-impasto","fen-lievitazione","fen-frittura-lievitati"],
    "prod-arancina": ["fen-frittura-lievitati","fen-retrogradazione","fen-maillard"],
    "prod-bagel": ["fen-gelatinizzazione","fen-maglia-glutinica","fen-maillard"],
    "prod-pretzel": ["fen-maillard","fen-gelatinizzazione","fen-crosta"],
    "prod-bao": ["fen-lievitazione","fen-gelatinizzazione"],
    "prod-soda-bread": ["fen-fermentazione","fen-crosta","fen-maglia-glutinica"],
}
# gerarchia famiglia: figlio -governato_da-> madre (uso relation esistente, no nuove)
CABLA_FAMIGLIA = {
    "prod-pizza-nap": "prod-pizza",
    "prod-pizza-nap-adv": "prod-pizza",
    "prod-pizza-rom": "prod-pizza",
    "prod-pizza-teglia": "prod-pizza",
    "prod-pizza-pala": "prod-pizza",
    "prod-pain-chocolat": "prod-croissant",
    "fen-frittura-lievitati": "fen-frittura",
}

SEGRETI_INGREDIENTI = {
    "ing-pomodoro": "Per cuocere i pomodorini a padella, disponili uno a uno con la faccia tagliata a contatto col fondo e la buccia in alto, senza schiacciarli, e sala solo dopo. La faccia tagliata rosola (Maillard, il sapore bruno) invece di lessare; la buccia in alto fa da coperchio e intrappola il vapore, cosi dentro restano succosi mentre sotto dorano; il sale messo dopo tira fuori l'acqua (osmosi) quando la faccia ha gia preso colore, non prima. Se li giri o li schiacci, perdi la camera di vapore e finiscono a lessare.",
    "ing-patata": "Per patate al forno croccanti fuori e morbide dentro, sbollentale qualche minuto in acqua con un goccio d'aceto prima di arrostirle. L'acido protegge la pectina che tiene insieme le cellule: gli spigoli restano integri e netti invece di sfaldarsi, e gli spigoli netti sono quelli che diventano croccanti. Intanto la breve bollitura porta in superficie l'amido e lo gelatinizza: in forno diventa la crosta vetrosa. Acido per la forma, amido per la crosta.",
    "ing-limone": "Prima di spremerlo, rotolalo sul tagliere premendo col palmo, e usalo a temperatura ambiente non da frigo. Rompi le membrane interne che trattengono il succo, e a temperatura ambiente il succo e meno viscoso: ne esce molto di piu. Se ti serve la scorza, prendila prima di spremere: la parte gialla e piena di oli aromatici, la parte bianca sotto e amara: fermati al giallo.",
    "ing-lime": "Il succo di lime e vivo e muore in fretta: appena spremuto e brillante e agrumato, ma dopo qualche ora ossida e vira su note amare e di sudore. Spremilo il piu vicino possibile al servizio, mai a inizio serata per tutta la sera. Se devi tenerlo, in frigo dura molto piu che a temperatura ambiente (la temperatura rallenta l'ossidazione), ma un lime spremuto fresco non ha rivali in un cocktail.",
    "ing-basilico": "Non tagliarlo col coltello e non cuocerlo a lungo: strappalo con le mani e aggiungilo alla fine. Il coltello schiaccia le cellule e fa ossidare i bordi (anneriscono, sanno di fieno); le mani strappano piu pulito. E gli oli aromatici del basilico sono volatili, evaporano col calore: un minuto in padella e il profumo se n'e andato. Nel sugo va a fuoco spento, nell'ultimo istante.",
    "ing-aglio": "Il sapore dell'aglio lo decidi tu con due leve: come lo tagli e a che temperatura lo cuoci. Piu lo rompi (schiacciato, tritato fine) piu e pungente, perche rompendo le cellule si libera l'allicina; a fette o in camicia e dolce e gentile. E attento al fuoco: l'aglio brucia a bassa temperatura e diventa amaro in un attimo, va sempre a fiamma dolce, mai in olio fumante. Bruciato, butta tutto e ricomincia: non si recupera."
}

@bp.route("/admin/fix-schede-testi")
def _fix_schede_testi():
    """Applica le correzioni ortografiche alle schede fenomeni nel DB.
    ?dry=1 -> anteprima (non scrive). Auth ADMIN_SECRET."""
    if not hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    dry = request.args.get("dry") == "1"
    db = carica_grafo()
    rows = db.execute("SELECT id, name, data FROM nodes").fetchall()
    import psycopg2.extras as _psx
    conn = _get_conn() if not dry else None
    report = []
    for r in rows:
        rid = r["id"]
        if not str(rid).startswith("fen-"):
            continue
        nd = _dati(r["data"])
        changed = False
        campi = []
        sch = nd.get("scheda")
        if isinstance(sch, str):
            new = _corregge_it(sch)
            if new != sch:
                nd["scheda"] = new; changed = True; campi.append("scheda")
        elif isinstance(sch, dict) and isinstance(sch.get("it"), str):
            new = _corregge_it(sch["it"])
            if new != sch["it"]:
                sch["it"] = new; changed = True; campi.append("scheda")
        for campo in ("numero_bersaglio", "target"):
            v = nd.get(campo)
            if isinstance(v, str):
                new = _corregge_it(v)
                if new != v:
                    nd[campo] = new; changed = True; campi.append(campo)
        if changed:
            report.append({"id": rid, "campi": campi})
            if not dry:
                cur = conn.cursor()
                cur.execute("UPDATE nodes SET data = %s WHERE id = %s", (_psx.Json(nd), rid))
                conn.commit(); cur.close()
    if conn:
        _release_conn(conn)
    return jsonify({"dry": dry, "schede_modificate": len(report), "dettaglio": report})

@bp.route("/admin/schede-export")
def _schede_export():
    """Export sola-lettura di tutte le schede fenomeni (IT/EN/ES) per revisione
    testi. Nessuna AI, veloce. Auth ADMIN_SECRET."""
    if not hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    db = carica_grafo()
    rows = db.execute("SELECT id, name, data FROM nodes").fetchall()
    out = []
    for r in rows:
        rid = r["id"]
        if not str(rid).startswith("fen-"):
            continue
        nd = _dati(r["data"])
        out.append({
            "id": rid,
            "nome": r["name"],
            "it": _scheda_lang(nd, "it"),
            "en": _scheda_lang(nd, "en"),
            "es": _scheda_lang(nd, "es"),
            "target": _numero_bersaglio(nd),
        })
    return jsonify(out)

@bp.route("/v1/quality-eval", methods=["POST"])
def quality_eval():
    """Endpoint di quality evaluation - LLM-as-a-Judge lato server.
    Riceve domanda + risposta, valuta con Claude e restituisce i voti."""
    import ai_gateway as GW
    body = request.json or {}
    domanda = body.get("domanda", "")
    risposta = body.get("risposta", "")
    attesa = body.get("attesa", "")
    
    if not domanda or not risposta:
        return jsonify({"errore": "domanda e risposta obbligatorie"}), 400
    
    prompt = f"""Sei un esperto valutatore di sistemi AI per professionisti F&B (bar, panificazione, caffe, gelateria, cucina, vino, birra, pasticceria).

DOMANDA POSTA DAL PROFESSIONISTA:
{domanda}

RISPOSTA DEL SISTEMA AI:
{risposta}

ELEMENTI TECNICI ATTESI:
{attesa}

Valuta su 5 criteri (0-10). Rispondi SOLO in JSON senza markdown:
{{"accuratezza":0,"utilita":0,"numeri":0,"tono":0,"allucinazioni":0,"note":"max 25 parole sul punto critico","voto_globale":0}}

CRITERI:
- accuratezza: numeri e fatti fisici/chimici corretti e precisi
- utilita: applicabile domani mattina al banco
- numeri: include numeri specifici misurabili (pH, temperature, percentuali)
- tono: collega a collega senza lezioncine ovvie
- allucinazioni: nessun dato inventato o approssimato male"""

    try:
        risposta_eval = GW.route_chat(prompt)
        import re as _re
        testo = risposta_eval.strip()
        # Estrai JSON
        match = _re.search(r'\{.*\}', testo, _re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(testo)
        return jsonify(result)
    except Exception as e:
        return jsonify({"errore": str(e), "accuratezza":5,"utilita":5,"numeri":5,"tono":5,"allucinazioni":5,"voto_globale":5,"note":"Errore valutazione"}), 500

@bp.route("/quality-test")
def quality_test():
    """Tool di test qualità interno — LLM-as-a-Judge"""
    from config import HERE
    with open(os.path.join(str(HERE), "static", "quality_test.html"), "r") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}

@bp.route("/v1/admin/migrate-modello", methods=["POST"])
def admin_migrate_modello():
    """Aggiunge colonna modello a log_domande se non esiste."""
    secret = request.json.get("secret","") if request.json else ""
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"no db"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            ALTER TABLE log_domande
            ADD COLUMN IF NOT EXISTS modello TEXT
        """)
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/admin/init", methods=["POST"])
def admin_init():
    """Inizializza le tabelle account/quaderno. Da chiamare una volta dalla Console Railway."""
    secret = request.json.get("secret","") if request.json else ""
    if (not os.environ.get("ADMIN_SECRET")) or not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET"))):
        return jsonify({"errore":"non autorizzato"}), 403
    _init_account_tables()
    # crea anche la tabella esperimenti
    if DATABASE_URL:
        try:
            import psycopg2
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS esperimenti (
                    id SERIAL PRIMARY KEY, ts TIMESTAMPTZ DEFAULT NOW(),
                    nome TEXT NOT NULL, disciplina TEXT, note TEXT,
                    ph NUMERIC(4,2), brix NUMERIC(5,2), abv NUMERIC(5,2),
                    ey_perc NUMERIC(5,2), tds_perc NUMERIC(5,2),
                    temperatura NUMERIC(5,1), idratazione NUMERIC(5,2),
                    ingredienti JSONB DEFAULT '[]',
                    fenomeni JSONB DEFAULT '[]',
                    costo_mercato_eur NUMERIC(8,2), area_mercato TEXT DEFAULT 'it',
                    user_id TEXT, versione INTEGER DEFAULT 1
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_esp_user ON esperimenti(user_id, ts DESC)")
            conn.commit(); cur.close(); _release_conn(conn)
        except Exception as e:
            return jsonify({"errore":str(e)}), 500
    return jsonify({"ok":True,"messaggio":"Tabelle create: utenti, sessioni, esperimenti"})

@bp.route("/admin/test-like")
def admin_test_like():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        termine = request.args.get("t", "grassi")
        t = "%" + termine.lower() + "%"
        rows = db.execute("SELECT id, name, type FROM nodes WHERE lower(name) LIKE ? LIMIT 10", (t,)).fetchall()
        out = [{"id": r["id"], "name": r["name"], "type": r["type"]} for r in rows]
        allrows = db.execute("SELECT id, name, type FROM nodes").fetchall()
        tot = len(allrows)
        nuovi = [{"id": r["id"], "name": r["name"], "type": r["type"]}
                 for r in allrows if "impasto" in r["id"] or r["id"] in ("fen-idratazione","fen-farina-forza")]
        return jsonify({"termine": termine, "match": out, "totale_nodi": tot, "nodi_nuovi": nuovi})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/sottografo")
def admin_sottografo():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        dominio = request.args.get("dominio", "panificazione")
        # tutti i nodi del dominio
        nodi = db.execute("SELECT id, name, type FROM nodes WHERE lower(domain)=lower(?) ORDER BY type, id", (dominio,)).fetchall()
        nodi_out = [{"id": n["id"], "name": n["name"], "type": n["type"]} for n in nodi]
        ids = set(n["id"] for n in nodi)
        # per tipo, conteggio
        per_tipo = {}
        for n in nodi_out:
            per_tipo[n["type"]] = per_tipo.get(n["type"], 0) + 1
        # tutti gli edges che toccano questi nodi (da o verso)
        edges_out = []
        rel_count = {}
        for n in nodi:
            for e in db.execute("SELECT from_id, to_id, relation FROM edges WHERE from_id=?", (n["id"],)).fetchall():
                edges_out.append({"from": e["from_id"], "rel": e["relation"], "to": e["to_id"]})
                rel_count[e["relation"]] = rel_count.get(e["relation"], 0) + 1
        # nodi senza NESSUN edge uscente (le "isole")
        con_edge = set(e["from"] for e in edges_out)
        isole = [n["id"] for n in nodi_out if n["type"]=="Fenomeno" and n["id"] not in con_edge]
        return jsonify({
            "dominio": dominio,
            "totale_nodi": len(nodi_out),
            "per_tipo": per_tipo,
            "nodi": nodi_out,
            "totale_edges": len(edges_out),
            "relazioni_usate": rel_count,
            "fenomeni_senza_edge_uscente": isole,
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/cabla-panificazione")
def admin_cabla_panificazione():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        CABLAGGIO = {
            "fen-grassi-impasto":      {"fallisce_come": ["err-impasto-appiccicoso"]},
            "fen-zuccheri-impasto":    {"fallisce_come": ["err-crosta-pallida-molle"]},
            "fen-uova-impasto":        {"fallisce_come": []},
            "fen-latte-impasto":       {"fallisce_come": ["err-crosta-pallida-molle"]},
            "fen-idratazione":         {"fallisce_come": ["err-impasto-appiccicoso", "err-impasto-strappa", "err-alveolatura-chiusa"],
                                        "realizzato_da": ["tec-autolisi-riposo", "tec-pieghe-forza"]},
            "fen-farina-forza":        {"fallisce_come": ["err-impasto-strappa", "err-alveolatura-chiusa"],
                                        "realizzato_da": ["tec-pieghe-forza"]},
            "fen-temperatura-impasto": {"fallisce_come": ["err-pane-non-cresce"],
                                        "realizzato_da": ["tec-controllo-lievitazione"]},
            "fen-lievito-madre": {"fallisce_come": ["err-madre-sovra"],
                                  "si_manifesta_in": ["fis_sourdough_starter"]},
            "fen-tangzhong-yudane": {"governato_da": ["fen-gelatinizzazione"]},
            "fen-levain-pate-fermentee": {"governato_da": ["fen-fermentazione"]},
        }
        PONTI = [
            ("fen-uova-impasto", "governato_da", "fen-grassi-impasto"),
            ("fen-latte-impasto", "governato_da", "fen-zuccheri-impasto"),
        ]
        esistenti = set()
        for e in db.execute("SELECT from_id, relation, to_id FROM edges").fetchall():
            esistenti.add((e["from_id"], e["relation"], e["to_id"]))
        tutti_id = set(r["id"] for r in db.execute("SELECT id FROM nodes").fetchall())
        creati, saltati, mancanti = [], [], []
        def crea(frm, rel, to):
            if to not in tutti_id or frm not in tutti_id:
                mancanti.append(f"{frm} -{rel}-> {to} (nodo assente)"); return
            if (frm, rel, to) in esistenti:
                saltati.append(f"{frm} -{rel}-> {to}"); return
            db.execute("INSERT INTO edges (from_id, relation, to_id, data) VALUES (?,?,?,?)",
                       (frm, rel, to, "{}"))
            creati.append(f"{frm} -{rel}-> {to}")
        for fen, rels in CABLAGGIO.items():
            for rel, tos in rels.items():
                for to in tos: crea(fen, rel, to)
        for frm, rel, to in PONTI: crea(frm, rel, to)
        db.commit() if hasattr(db, "commit") else None
        return jsonify({"creati": creati, "n_creati": len(creati),
                        "saltati_gia_esistenti": saltati, "mancanti": mancanti})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:600]}), 500

@bp.route("/admin/test-retrieval")
def admin_test_retrieval():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from ai import cerca_contesto
        from db import carica_grafo
        db = carica_grafo()
        termine = request.args.get("q", "appiccicoso")
        ctx = cerca_contesto(db, termine, termine)
        if not ctx:
            return jsonify({"termine": termine, "n_fenomeni": 0, "fenomeni": [], "nota": "nessun match"})
        fen = [{"id": f.get("id"), "name": f.get("name")} for f in ctx.get("fenomeni", [])]
        return jsonify({"termine": termine, "n_fenomeni": len(fen), "fenomeni": fen})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:600]}), 500

@bp.route("/admin/test-cast")
def admin_test_cast():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    db = carica_grafo()
    termine = request.args.get("q", "plasmolisi")
    t = f"%{termine.lower()}%"
    out = {}
    # metodo 1: CAST(data AS TEXT)
    try:
        r = db.execute("SELECT id FROM nodes WHERE lower(CAST(data AS TEXT)) LIKE ? LIMIT 5", (t,)).fetchall()
        out["cast_text"] = [x["id"] for x in r]
    except Exception as e:
        out["cast_text_errore"] = str(e)[:150]
    # metodo 2: data::text (sintassi Postgres)
    try:
        r = db.execute("SELECT id FROM nodes WHERE lower(data::text) LIKE ? LIMIT 5", (t,)).fetchall()
        out["data_colon_text"] = [x["id"] for x in r]
    except Exception as e:
        out["data_colon_text_errore"] = str(e)[:150]
    # verifica: la scheda zuccheri contiene plasmolisi? leggo il campo diretto
    try:
        row = db.execute("SELECT data FROM nodes WHERE id='fen-zuccheri-impasto'").fetchone()
        d = row["data"] if row else ""
        out["zuccheri_contiene_plasmolisi"] = "plasmolisi" in str(d).lower()
        out["zuccheri_data_len"] = len(str(d))
    except Exception as e:
        out["zuccheri_errore"] = str(e)[:150]
    return jsonify(out)

@bp.route("/admin/popola-alias")
def admin_popola_alias():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo, _dati
        import json as _json
        db = carica_grafo()
        ALIAS = {
            "fen-grassi-impasto": ["olio","burro","strutto","materia grassa","grasso","olio evo","shortening","sugna"],
            "fen-zuccheri-impasto": ["zucchero","saccarosio","miele","zuccheri","dolcificante"],
            "fen-uova-impasto": ["uovo","uova","tuorlo","albume","tuorli","albumi"],
            "fen-latte-impasto": ["latte","latticini","lattosio","panna","latte in polvere"],
            "fen-idratazione": ["idratazione","acqua","percentuale acqua","quanta acqua","impasto molle","impasto bagnato"],
            "fen-farina-forza": ["farina","forza","W","manitoba","proteine farina","glutine farina","farina forte","farina debole"],
            "fen-temperatura-impasto": ["temperatura impasto","DDT","temperatura acqua","impasto caldo","impasto freddo","estate","inverno","lievita in fretta","troppo caldo","temperatura finale"],
            "fen-autolisi": ["autolisi","riposo farina acqua","riposo impasto"],
            "fen-poolish-biga": ["biga","poolish","prefermento","preimpasto","lievitino"],
            "fen-lievitazione": ["lievita","lievitazione","cresce in forno","oven spring","non cresce","non lievita","sviluppo in forno"],
            "fen-fermentazione": ["fermenta","fermentazione","maturazione impasto"],
            "fen-fermentazione-lattica": ["lievito madre","pasta madre","sourdough","acidificazione"],
            "fen-maglia-glutinica": ["maglia glutinica","glutine","si strappa","non si estende","strappa","incordatura","struttura impasto"],
            "fen-sale-impasto": ["sale","salinita","dosaggio sale"],
            "fen-crosta": ["crosta","doratura","colore crosta","pallida"],
            "fen-idratazione": ["idratazione","acqua","percentuale acqua","quanta acqua","impasto molle","impasto bagnato","impasto appiccicoso","troppa acqua","appiccicoso","molle","troppo molle"],
            "fen-lievito-madre": ["lievito madre","pasta madre","madre","sourdough","levain","starter","picco","rinfresco","licoli"],
            "fen-tangzhong-yudane": ["tangzhong","yudane","water roux","roux","pre-gelatinizzazione","milk bread","shokupan","pane soffice","pane giapponese"],
            "fen-levain-pate-fermentee": ["levain","pate fermentee","pâte fermentée","vecchio impasto","old dough","prefermento francese","lievitino"],
            "fen-frittura-lievitati": ["frittura","friggere","friggo","fritto","fritti","unto","unti","untuoso","olio caldo","immersione","frittura di lievitati","sigillo frittura","arancini","arancine","panzerotti","panzerotto","impanato","panato","bombolone","bomboloni","zeppola","zeppole","suppli","crocche"],
            "fen-haccp": ["haccp","sicurezza alimentare","ccp","punto critico","autocontrollo","igiene","pericolo alimentare","allergeni"],
            "fen-attivita-acqua": ["attivita acqua","aw","acqua libera","conservazione","essiccazione","stagionatura","perche i salumi durano","perche il miele non scade"],
            "fen-catena-freddo": ["catena del freddo","zona di pericolo","zona pericolo","temperatura conservazione","frigo","frigorifero","congelatore","surgelato","scongelare","scongelo","scongelamento","conservare la carne","conservare carne","raffreddamento","abbattitore","abbattimento temperatura"],
            "fen-conserve-botulino": ["botulino","conserve","sottolio","sott olio","sottaceti","sterilizzazione","barattolo","conserva","clostridium","tossina"],
            "fen-anisakis": ["anisakis","pesce crudo","abbattimento","abbattitore","sushi","sashimi","crudo di pesce","marinato","tartare di pesce","parassita pesce","congelare il pesce"],
            "fen-ustioni-olio": ["ustioni","ustione","olio bollente","olio caldo sicurezza","incendio olio","schizzi olio","frittura sicurezza","olio infiammato","scottatura olio"],
            "fen-equilibrio-cocktail": ["equilibrio cocktail","bilanciare drink","bilanciare","bilancio","bilanciare sour","bilancio sour","come bilancio","dolce acido forte","sour ratio","fare un sour","struttura cocktail","proporzioni cocktail","bilanciamento drink","il drink non torna","troppo dolce cocktail","troppo aspro","sour cocktail"],
            "fen-ghiaccio": ["ghiaccio","cubo di ghiaccio","ghiaccio tritato","ghiaccio grande","che ghiaccio","tipo di ghiaccio","ghiaccio cocktail","crushed ice","sfera di ghiaccio","ghiaccio limpido"],
            "fen-carbonatazione": ["carbonatazione","bollicine","highball","soda","gassato","effervescenza","co2","frizzante","spritz bollicine","perche va flat","drink piatto bollicine"],
            "fen-chiarificazione-latte": ["chiarificazione","milk punch","milk wash","clarified","chiarificato","latte cocktail","drink limpido","clarificare","milk washing"],
            "fen-infusioni": ["infusione","macerazione","infondere","aromatizzare distillato","gin fatto in casa","infuso","macerare","botaniche","aromatizzare alcol"],
            "fen-amaro-bitter": ["bitter","amaro","angostura","peychaud","dash","gocce di bitter","campari","fernet","digestivo","aromatico cocktail","orange bitter"],
            "fen-collagene-brasato": ["brasato","collagene","gelatina carne","taglio duro","cottura lenta carne","stracotto","spezzatino","ossobuco","brisket","carne dura","perche la carne e dura","guancia","spalla"],
            "fen-rosolatura": ["rosolatura","rosolare","searing","scottare","scotto","scottare la carne","scotto una bistecca","crosta carne","crosta sulla carne","crosta della carne","crosta bistecca","sigillare carne","dorare la carne","dorare la bistecca","bistecca crosta","bistecca in padella","sear","rosolare la carne"],
            "fen-emulsione-salse": ["maionese","olandese","salsa impazzita","emulsione salsa","vinaigrette","salsa emulsionata","maionese impazzita","montare la salsa","bearnaise"],
            "fen-pasta-acqua": ["pasta","al dente","acqua di cottura","mantecatura","mantecare","cuocere la pasta","acqua della pasta","carbonara cremosa","cacio e pepe","aglio e olio","pasta scotta"],
            "fen-soffritto": ["soffritto","mirepoix","base aromatica","appassire","rosolare le verdure","sofrito","cipolla carota sedano","battuto","fondo aromatico"],
            "fen-riposo-carne": ["riposo carne","far riposare la carne","riposare la bistecca","riposo bistecca","succhi carne","carne asciutta","perche la carne e secca","tagliare la carne subito"],
            "fen-uova-coagulazione": ["uovo","uova","coagulazione uovo","uova strapazzate","uovo sodo","uovo in camicia","frittata","omelette","uova cremose","uova gommose","uovo alla coque","tuorlo albume"],
            "fen-verdure-verdi": ["verdure verdi","clorofilla","sbollentare","blanching","verde brillante","broccoli","fagiolini","verdura smorta","shock termico","sbianchire","verde militare"],
            "fen-temperaggio-cioccolato": ["temperaggio","temperare cioccolato","forma V","burro di cacao","bloom","cioccolato lucido","snap cioccolato","cristallizzazione cioccolato","cioccolato opaco","cioccolato non si stacca"],
            "fen-crema-pasticcera": ["crema pasticcera","crema pasticciera","addensare crema","crema grumi","crema inglese","custard","crema per dolci","crema sa di farina","crema impazzita"],
            "fen-montatura-panna": ["montare la panna","panna montata","chantilly","picco fermo","panna non monta","panna diventa burro","montare panna","panna smontata"],
            "fen-shakerare-mescolare": ["shakerare","mescolare","shakerato mescolato","shake stir","quando shakerare","shakerare o mescolare","stirred shaken","tecnica shaker","bar spoon"],
            "fen-emulsione-bar": ["albume cocktail","schiuma cocktail","dry shake","sour schiuma","whiskey sour schiuma","emulsione drink","aquafaba","clover club","pisco sour","foam cocktail"],
            "fen-farina-forza": ["farina","forza","W","manitoba","proteine farina","glutine farina","farina forte","farina debole","alveografo","si strappa","lunga lievitazione"],
        }
        fatti = []
        for nid, aliases in ALIAS.items():
            row = db.execute("SELECT data FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                fatti.append(f"{nid}: NODO ASSENTE"); continue
            d = _dati(row["data"])
            d["aliases"] = aliases
            db.execute("UPDATE nodes SET data=? WHERE id=?", (_json.dumps(d, ensure_ascii=False), nid))
            fatti.append(f"{nid}: {len(aliases)} alias")
        db.commit() if hasattr(db, "commit") else None
        return jsonify({"fatti": fatti})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/confronta-doppioni")
def admin_confronta_doppioni():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo, _dati
        db = carica_grafo()
        ids = request.args.get("ids", "fen-idratazione,fen-idratazione-impasto").split(",")
        out = []
        for nid in ids:
            row = db.execute("SELECT id, name, type, domain, data FROM nodes WHERE id=?", (nid.strip(),)).fetchone()
            if not row:
                out.append({"id": nid, "ESISTE": False}); continue
            d = _dati(row["data"])
            scheda = d.get("scheda", "")
            if isinstance(scheda, dict): scheda = scheda.get("it", "")
            n_out = len(db.execute("SELECT 1 FROM edges WHERE from_id=?", (nid.strip(),)).fetchall())
            n_in = len(db.execute("SELECT 1 FROM edges WHERE to_id=?", (nid.strip(),)).fetchall())
            out.append({
                "id": row["id"], "ESISTE": True, "name": row["name"], "domain": row["domain"],
                "scheda_chars": len(scheda or ""),
                "ha_target": bool(d.get("target")),
                "ha_aliases": bool(d.get("aliases")),
                "edges_uscenti": n_out, "edges_entranti": n_in,
                "scheda_inizio": (scheda or "")[:100],
            })
        return jsonify({"confronto": out})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/edges-di")
def admin_edges_di():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        nid = request.args.get("id", "fen-idratazione-impasto")
        out_e = [{"rel": e["relation"], "to": e["to_id"]}
                 for e in db.execute("SELECT relation, to_id FROM edges WHERE from_id=?", (nid,)).fetchall()]
        in_e = [{"from": e["from_id"], "rel": e["relation"]}
                for e in db.execute("SELECT from_id, relation FROM edges WHERE to_id=?", (nid,)).fetchall()]
        return jsonify({"id": nid, "uscenti": out_e, "entranti": in_e})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/merge-idratazione")
def admin_merge_idratazione():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        db = carica_grafo()
        CANONICO = "fen-idratazione"
        VECCHIO = "fen-idratazione-impasto"
        azioni = []
        # 1) ridireziona ogni edge del vecchio verso il canonico (evitando duplicati e self-loop)
        esistenti = set((e["from_id"], e["relation"], e["to_id"])
                        for e in db.execute("SELECT from_id, relation, to_id FROM edges").fetchall())
        def crea(frm, rel, to):
            if frm == to: return
            if (frm, rel, to) in esistenti:
                azioni.append(f"gia presente: {frm} -{rel}-> {to}"); return
            db.execute("INSERT INTO edges (from_id, relation, to_id, data) VALUES (?,?,?,?)", (frm, rel, to, "{}"))
            esistenti.add((frm, rel, to))
            azioni.append(f"creato: {frm} -{rel}-> {to}")
        # uscenti del vecchio → diventano uscenti del canonico
        for e in db.execute("SELECT relation, to_id FROM edges WHERE from_id=?", (VECCHIO,)).fetchall():
            crea(CANONICO, e["relation"], e["to_id"])
        # entranti del vecchio → puntano al canonico
        for e in db.execute("SELECT from_id, relation FROM edges WHERE to_id=?", (VECCHIO,)).fetchall():
            crea(e["from_id"], e["relation"], CANONICO)
        # 2) elimina tutti gli edges del vecchio
        db.execute("DELETE FROM edges WHERE from_id=? OR to_id=?", (VECCHIO, VECCHIO))
        azioni.append("edges del vecchio eliminati")
        # 3) elimina il nodo vecchio
        db.execute("DELETE FROM nodes WHERE id=?", (VECCHIO,))
        azioni.append(f"nodo {VECCHIO} eliminato")
        db.commit() if hasattr(db, "commit") else None
        # verifica
        ancora = db.execute("SELECT 1 FROM nodes WHERE id=?", (VECCHIO,)).fetchone()
        return jsonify({"azioni": azioni, "vecchio_ancora_presente": bool(ancora)})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/test-pipeline", methods=["POST"])
def admin_test_pipeline():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        from ai import cerca_contesto, estrai_entita
        try:
            from ai import cerca_fuzzy
        except Exception:
            cerca_fuzzy = None
        db = carica_grafo()
        domanda = (request.get_json(silent=True) or {}).get("domanda", "")
        termini = estrai_entita(domanda) + sorted(
            [p.strip(".,?!").lower() for p in domanda.split() if len(p) > 4],
            key=len, reverse=True)
        contesto = None
        for t in termini:
            contesto = cerca_contesto(db, t, domanda)
            if contesto and contesto.get("fenomeni"): break
        if (not contesto or not contesto.get("fenomeni")) and cerca_fuzzy:
            contesto = cerca_fuzzy(db, domanda)
        fen = []
        if contesto and contesto.get("fenomeni"):
            fen = [f.get("id") for f in contesto["fenomeni"]]
        return jsonify({"domanda": domanda, "fenomeni": fen})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/test-ranked", methods=["POST"])
def admin_test_ranked():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        from retrieval import retrieval_ranked
        from ai import estrai_entita
        db = carica_grafo()
        payload = request.get_json(silent=True) or {}
        domanda = payload.get("domanda", "")
        usa_mistral = payload.get("mistral", True)
        termini = estrai_entita(domanda) if usa_mistral else None
        res = retrieval_ranked(db, domanda, termini_extra=termini)
        return jsonify(res)
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/test-chat-reale", methods=["POST"])
def admin_test_chat_reale():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        from retrieval import retrieval_ranked
        from ai import cerca_contesto, estrai_entita
        db = carica_grafo()
        domanda = (request.get_json(silent=True) or {}).get("domanda", "")
        # STESSA logica di chat.py
        termini_mistral = estrai_entita(domanda)
        ranked = retrieval_ranked(db, domanda, termini_extra=termini_mistral, topk=5)
        fen_ids = [f["id"] for f in ranked.get("fenomeni", [])]
        contesto = None
        scelto = None
        for fid in fen_ids:
            nome = db.execute("SELECT name FROM nodes WHERE id=?", (fid,)).fetchone()
            if nome:
                contesto = cerca_contesto(db, nome["name"], domanda)
                if contesto and contesto.get("fenomeni"):
                    scelto = fid; break
        fen_contesto = [f.get("id") for f in contesto["fenomeni"]] if contesto and contesto.get("fenomeni") else []
        return jsonify({
            "domanda": domanda,
            "ranked_top": fen_ids,
            "fenomeno_scelto_per_contesto": scelto,
            "fenomeni_nel_contesto_finale": fen_contesto,
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/riempi-panificati")
def admin_riempi_panificati():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo, _dati
        import json as _json
        db = carica_grafo()
        RICETTE = RICETTE_PANIFICATI
        CABLA_RICETTE = CABLA_PANIFICATI
        fatti = []
        for nid, r in RICETTE.items():
            row = db.execute("SELECT id, data FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                fatti.append(f"{nid}: ASSENTE (creo)")
                db.execute("INSERT INTO nodes (id, type, name, domain, data) VALUES (?,?,?,?,?)",
                           (nid, "Prodotto", r["nome"], "panificazione",
                            _json.dumps({"scheda": r["scheda"], "target": r["target"], "aliases": r.get("aliases",[])}, ensure_ascii=False)))
            else:
                d = _dati(row["data"])
                d["scheda"] = r["scheda"]; d["target"] = r["target"]; d["aliases"] = r.get("aliases",[])
                db.execute("UPDATE nodes SET data=?, name=? WHERE id=?",
                           (_json.dumps(d, ensure_ascii=False), r["nome"], nid))
                fatti.append(f"{nid}: RIEMPITO ({len(r['scheda'])} chars)")
        # cablaggio: fenomeno -si_manifesta_in-> prodotto (edges mancanti)
        esistenti = set((e["from_id"], e["relation"], e["to_id"])
                        for e in db.execute("SELECT from_id, relation, to_id FROM edges").fetchall())
        tutti = set(r["id"] for r in db.execute("SELECT id FROM nodes").fetchall())
        edges_creati = []
        for prod, fenomeni in CABLA_RICETTE.items():
            for fen in fenomeni:
                if fen in tutti and prod in tutti and (fen, "si_manifesta_in", prod) not in esistenti:
                    db.execute("INSERT INTO edges (from_id, relation, to_id, data) VALUES (?,?,?,?)",
                               (fen, "si_manifesta_in", prod, "{}"))
                    esistenti.add((fen, "si_manifesta_in", prod))
                    edges_creati.append(f"{fen} -> {prod}")
        # gerarchia famiglia: figlio -governato_da-> madre
        edges_fam = []
        try:
            for figlio, madre in CABLA_FAMIGLIA.items():
                if figlio in tutti and madre in tutti and (figlio, "governato_da", madre) not in esistenti:
                    db.execute("INSERT INTO edges (from_id, relation, to_id, data) VALUES (?,?,?,?)",
                               (figlio, "governato_da", madre, "{}"))
                    esistenti.add((figlio, "governato_da", madre))
                    edges_fam.append(f"{figlio} -governato_da-> {madre}")
        except Exception as _fe:
            edges_fam.append(f"errore famiglia: {_fe}")
        db.commit() if hasattr(db, "commit") else None
        return jsonify({"riempiti": fatti, "edges_creati": edges_creati, "edges_famiglia": edges_fam})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:500]}), 500

@bp.route("/admin/popola-segreti")
def admin_popola_segreti():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo, _dati
        import json as _json
        db = carica_grafo()
        fatti = []
        for nid, seg in SEGRETI_INGREDIENTI.items():
            row = db.execute("SELECT data FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                fatti.append(f"{nid}: ASSENTE"); continue
            d = _dati(row["data"])
            d["segreto"] = seg
            db.execute("UPDATE nodes SET data=? WHERE id=?", (_json.dumps(d, ensure_ascii=False), nid))
            fatti.append(f"{nid}: segreto aggiunto ({len(seg)} char)")
        db.commit() if hasattr(db, "commit") else None
        return jsonify({"fatti": fatti})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/test-contesto-segreto")
def admin_test_contesto_segreto():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        from db import carica_grafo
        from ai import cerca_contesto
        db = carica_grafo()
        termine = request.args.get("t", "pomodoro")
        contesto = cerca_contesto(db, termine, "")
        fisici = contesto.get("prodotti_fisici", []) if contesto else []
        con_segreto = [{"nome": f.get("nome"), "segreto": f.get("segreto","(nessuno)")[:80]} for f in fisici if f.get("segreto")]
        return jsonify({"termine": termine,
                        "prodotti_fisici_totali": len(fisici),
                        "con_segreto": con_segreto})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/crea-haccp")
def admin_crea_haccp():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json, traceback
    SCHEDE = {
        "fen-haccp": {"nome":"HACCP (il metodo della sicurezza)","target":"Prevenire i pericoli dove nascono, CCP con limiti misurabili (T>=75C, pH<4.6)"},
        "fen-attivita-acqua": {"nome":"Attivita dell'acqua (Aw)","target":"Sotto Aw 0.85 i patogeni non crescono - sale e zucchero mettono a secco"},
        "fen-catena-freddo": {"nome":"Catena del freddo","target":"Zona pericolo 5-60C: freddo sospende, caldo >=75C uccide - scongelare in frigo"},
        "fen-conserve-botulino": {"nome":"Conserve e botulino","target":"Botulino anaerobio senza odore: difese pH sotto 4.6 O sterilizzazione - l'olio non protegge"},
        "fen-anisakis": {"nome":"Anisakis e abbattimento del pesce","target":"Pesce crudo abbattuto per legge: -20C al cuore 24h (o -18C 96h a casa), uccide i parassiti non i batteri"},
        "fen-ustioni-olio": {"nome":"Ustioni e sicurezza dell'olio","target":"Olio 170-180C: cibi asciutti mai acqua, incendio si soffoca mai annacqua, sotto il punto di fumo"},
        "fen-equilibrio-cocktail": {"nome":"L'equilibrio del cocktail","target":"Dolce/acido/forte/amaro: sour 2:1:1 struttura madre, bilancia a freddo"},
        "fen-shakerare-mescolare": {"nome":"Shakerare vs mescolare","target":"Opaco shakera 10-15s, limpido mescola 20-30s - cosa c'e nel bicchiere"},
        "fen-emulsione-bar": {"nome":"Emulsione e texture (albume, schiuma)","target":"Albume = denaturazione + emulsione = schiuma, dry shake sempre"},
        "fen-ghiaccio": {"nome":"Il ghiaccio (raffreddamento e diluizione)","target":"Superficie/volume: grande lento poco diluito, tritato veloce diluito - dimensione governa la velocita"},
        "fen-carbonatazione": {"nome":"La carbonatazione (bollicine)","target":"CO2 trattenuta con freddo, pressione, superfici lisce - tritato e bicchiere largo la fanno scappare"},
        "fen-chiarificazione-latte": {"nome":"La chiarificazione al latte","target":"Acido a pH 4.6 caglia la caseina, la cagliata cattura tannini e torbidita, filtri = limpido e morbido"},
        "fen-infusioni": {"nome":"Infusioni e macerazioni","target":"Alcol estrae aromi: tempo/temperatura/superficie governano, assaggia e ferma alla finestra giusta"},
        "fen-amaro-bitter": {"nome":"L'amaro e i bitter","target":"Bitter a gocce mette a fuoco (sale del bar): concentrati vs amari da bere, la 4a forza dell'equilibrio"},
        "fen-collagene-brasato": {"nome":"Collagene e brasato (i due tipi di carne)","target":"Fibre poco e caldo, collagene tanto tempo a 70-90C = gelatina, scegli la cottura dal taglio"},
        "fen-rosolatura": {"nome":"La rosolatura (searing)","target":"Maillard sulla superficie = sapore non sigillo, carne asciutta padella calda"},
        "fen-emulsione-salse": {"nome":"Emulsione delle salse (maionese, olandese)","target":"Olio in gocce tenute dall'emulsionante, olio lento, si salva da nuovo emulsionante"},
        "fen-pasta-acqua": {"nome":"La pasta e l'acqua di cottura","target":"Amido gelatinizza da fuori, al dente cuore vetroso, l'acqua amidacea emulsiona la salsa"},
        "fen-soffritto": {"nome":"Il soffritto (base aromatica)","target":"Verdure appassite piano nel grasso, fuoco dolce, il grasso cattura gli aromi liposolubili"},
        "fen-riposo-carne": {"nome":"Il riposo della carne","target":"Fibre si rilassano e succhi si ridistribuiscono, piu grosso piu lungo, succosa vs asciutta"},
        "fen-uova-coagulazione": {"nome":"Le uova (coagulazione)","target":"Albume 62-65C tuorlo 65-70C, fuoco dolce cremoso troppo caldo gommoso, latte ammorbidisce"},
        "fen-verdure-verdi": {"nome":"Le verdure verdi (clorofilla)","target":"Clorofilla a feofitina col tempo/acido, sbollenta veloce poi shock in ghiaccio fissa il verde"},
        "fen-cristalli-ghiaccio": {"nome":"Cristalli di ghiaccio (cremosita)","target":"Cristalli piccoli = cremoso, congela rapido e manteca, nemico la ricristallizzazione"},
        "fen-zuccheri-pac": {"nome":"Zuccheri e punto di congelamento (PAC)","target":"Lo zucchero abbassa il punto di congelamento, zuccheri piccoli abbassano di piu, nel sorbetto unica leva"},
        "fen-grassi-stabilizzanti": {"nome":"Grassi e stabilizzanti (gelateria)","target":"Grasso maschera i cristalli, stabilizzanti legano l'acqua = piu cremoso regge sbalzi"},
        "fen-fermentazione-alcolica": {"nome":"Fermentazione alcolica (vino e birra)","target":"Lievito mangia zucchero = alcol + CO2, vino dall'uva birra dal malto (ammostamento)"},
        "fen-tannini-vino": {"nome":"Tannini e struttura del vino","target":"Tannini di bucce/semi = astringenza, rosso con le bucce bianco senza, si ammorbidiscono nel tempo"},
        "fen-luppolo": {"nome":"Il luppolo e l'amaro della birra","target":"Luppolo = amaro + aroma, presto in bollitura amaro tardi aroma, si misura in IBU"},
        "fen-macinatura-caffe": {"nome":"Macinatura e estrazione del caffe","target":"Macinatura governa la velocita di estrazione, fine per espresso grossa per filtro, acqua 90-96C"},
    }
    risultati = []
    try:
        conn = _get_conn(); cur = conn.cursor()
        for nid, meta in SCHEDE.items():
            try:
                cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
                if cur.fetchone():
                    risultati.append(f"{nid}: gia esiste")
                    continue
                nd = {"scheda": meta["nome"] + " - scheda da riempire via update", "target": meta["target"], "numero_bersaglio": meta["target"]}
                cur.execute("INSERT INTO nodes (id, type, name, domain, data) VALUES (%s,%s,%s,%s,%s)",
                            (nid, "Fenomeno", meta["nome"], "tecnologie", json.dumps(nd, ensure_ascii=False)))
                risultati.append(f"{nid}: CREATO")
            except Exception as e1:
                risultati.append(f"{nid}: ERRORE {str(e1)[:120]}")
        conn.commit()
        return jsonify({"risultati": risultati})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/cabla-sicurezza")
def admin_cabla_sicurezza():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    # agganci: (nodo, relazione, fenomeno-sicurezza)
    AGGANCI = [
        ("fen-frittura-lievitati", "si_manifesta_in", "fen-ustioni-olio"),
        ("prod-arancina", "si_manifesta_in", "fen-ustioni-olio"),
        ("prod-impasto-rosticceria", "si_manifesta_in", "fen-ustioni-olio"),
        ("tec-frittura", "si_manifesta_in", "fen-ustioni-olio"),
        ("prod-carne-stagionata", "si_manifesta_in", "fen-attivita-acqua"),
        ("ing-bresaola", "si_manifesta_in", "fen-attivita-acqua"),
        ("ing-prosciutto-crudo", "si_manifesta_in", "fen-attivita-acqua"),
        ("prod-confettura-conserva", "si_manifesta_in", "fen-conserve-botulino"),
        ("prod-carasau", "si_manifesta_in", "fen-attivita-acqua"),
    ]
    try:
        conn = _get_conn(); cur = conn.cursor()
        fatti = []
        for src, rel, dst in AGGANCI:
            cur.execute("SELECT id FROM nodes WHERE id=%s", (src,))
            if not cur.fetchone():
                fatti.append(f"{src}: nodo assente, skip"); continue
            cur.execute("SELECT id FROM nodes WHERE id=%s", (dst,))
            if not cur.fetchone():
                fatti.append(f"{dst}: fenomeno assente, skip"); continue
            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation=%s AND to_id=%s", (src, rel, dst))
            if cur.fetchone():
                fatti.append(f"{src} -> {dst}: gia esiste"); continue
            cur.execute("INSERT INTO edges (from_id, relation, to_id, data) VALUES (%s,%s,%s,%s)",
                        (src, rel, dst, "{}"))
            fatti.append(f"{src} -{rel}-> {dst}: CREATO")
        conn.commit()
        return jsonify({"agganci": fatti})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/fix-dominio-bar")
def admin_fix_dominio_bar():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    DOMINI = {
        "bar": ["fen-equilibrio-cocktail","fen-shakerare-mescolare","fen-emulsione-bar",
                "fen-ghiaccio","fen-carbonatazione","fen-chiarificazione-latte",
                "fen-infusioni","fen-amaro-bitter"],
        "cucina": ["fen-collagene-brasato","fen-rosolatura","fen-emulsione-salse","fen-pasta-acqua","fen-soffritto","fen-riposo-carne","fen-uova-coagulazione","fen-verdure-verdi"],
        "pasticceria": ["fen-meringa","fen-montatura-panna","fen-crema-pasticcera","fen-temperaggio-cioccolato","fen-gelificazione","fen-zucchero-cottura","fen-pasta-frolla","fen-lievitazione-chimica"],
        "gelateria": ["fen-cristalli-ghiaccio","fen-zuccheri-pac","fen-grassi-stabilizzanti","fen-stabilizzanti-gelato","fen-cristallizzazione-ghiaccio","fen-overrun"],
        "vino": ["fen-fermentazione-alcolica","fen-tannini-vino"],
        "birra": ["fen-luppolo"],
        "caffetteria": ["fen-macinatura-caffe"],
    }
    try:
        conn = _get_conn(); cur = conn.cursor()
        fatti = []
        for dom, ids in DOMINI.items():
            for nid in ids:
                cur.execute("UPDATE nodes SET domain=%s WHERE id=%s", (dom, nid))
                fatti.append(f"{nid}: dominio -> {dom}")
        conn.commit()
        return jsonify({"fatti": fatti})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/reset-trial")
def admin_reset_trial():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM trial_chat")
        n = cur.rowcount
        conn.commit()
        return jsonify({"ok": True, "trial_azzerati": n})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:300]}), 500

@bp.route("/admin/coeff-zuccheri")
def admin_coeff_zuccheri():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # POD = potere dolcificante, PAC = potere anticongelante (saccarosio=100). Solidi = sostanza secca %.
    ZUCCHERI = {
        "ing-saccarosio": {"nome":"Saccarosio","pod":100,"pac":100,"solidi":100,
            "nota":"Lo zucchero di riferimento (POD 100, PAC 100). Almeno il 70% degli zuccheri di una ricetta gelato. Da durezza e cristalli piu grandi."},
        "ing-destrosio": {"nome":"Destrosio (glucosio)","pod":74,"pac":190,"solidi":92,
            "nota":"Dolcifica meno (POD 74) ma abbassa molto il punto di congelamento (PAC 190): rende il gelato piu morbido e spatolabile. 15-20% degli zuccheri. Esalta gli aromi."},
        "ing-fruttosio": {"nome":"Fruttosio","pod":170,"pac":190,"solidi":100,
            "nota":"Molto dolce (POD 170) e molto anticongelante (PAC 190). Presente nella frutta. Da usare con parsimonia o il gelato resta troppo morbido e troppo dolce."},
        "ing-zucchero-invertito": {"nome":"Zucchero invertito","pod":130,"pac":190,"solidi":75,
            "nota":"Miscela di glucosio e fruttosio (POD 130, PAC 190). Anticristallizzante: da cremosita, controlla i cristalli, trattiene umidita. Effetto riducente (rallenta l'ossidazione)."},
        "ing-sciroppo-glucosio": {"nome":"Sciroppo di glucosio (42 DE)","pod":50,"pac":90,"solidi":80,
            "nota":"POD e PAC dipendono dal DE (destrosio equivalente): piu alto il DE, piu alti POD e PAC. Il 42DE ha POD 50, PAC 90. Anticristallizzante e legante, aumenta il secco senza dolcificare troppo."},
        "ing-lattosio": {"nome":"Lattosio","pod":16,"pac":100,"solidi":100,
            "nota":"Zucchero del latte (POD 16, PAC 100). Poco dolce, forte assorbimento d'acqua. Attenzione al dosaggio: in eccesso ricristallizza e da consistenza sabbiosa."},
        "ing-maltodestrine": {"nome":"Maltodestrine","pod":10,"pac":20,"solidi":95,
            "nota":"DE basso: POD e PAC molto bassi. Alzano il secco e danno corpo senza dolcificare ne abbassare troppo il congelamento."},
    }
    try:
        conn = _get_conn(); cur = conn.cursor()
        fatti = []
        for nid, dati in ZUCCHERI.items():
            cur.execute("SELECT id, data FROM nodes WHERE id=%s", (nid,))
            row = cur.fetchone()
            payload = {"pod": dati["pod"], "pac": dati["pac"], "solidi_pct": dati["solidi"],
                       "scheda": dati["nota"], "categoria": "zucchero", "disciplina": "gelateria"}
            if row:
                raw = row[1] if isinstance(row,(list,tuple)) else row["data"]
                nd = raw if isinstance(raw, dict) else _json.loads(raw)
                nd.update(payload)
                cur.execute("UPDATE nodes SET data=%s, domain=COALESCE(NULLIF(domain,''),'gelateria') WHERE id=%s",
                            (_json.dumps(nd, ensure_ascii=False), nid))
                fatti.append(f"{nid}: aggiornato POD={dati['pod']} PAC={dati['pac']}")
            else:
                nd = {"nome": dati["nome"], **payload}
                cur.execute("INSERT INTO nodes (id, type, name, domain, data) VALUES (%s,%s,%s,%s,%s)",
                            (nid, "Ingrediente", dati["nome"], "gelateria", _json.dumps(nd, ensure_ascii=False)))
                fatti.append(f"{nid}: CREATO POD={dati['pod']} PAC={dati['pac']}")
        conn.commit()
        return jsonify({"ok": True, "zuccheri": fatti})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/crea-errori-nuovi")
def admin_crea_errori_nuovi():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # errori tipici (sintomo osservabile al banco -> causa -> fenomeno). Schema: nodo Errore + edge fallisce_come.
    ERRORI = [
        # (err_id, nome, dominio, causa, fenomeno, sintomo)
        ("err-brasato-stopposo","Brasato asciutto e stopposo","cucina",
         "cottura fermata nello stadio secco intermedio: le fibre hanno espulso acqua ma il collagene non si e ancora sciolto in gelatina. Serve insistere a 70-90C con umidita finche il collagene converte","fen-collagene-brasato","asciutto e duro a meta cottura"),
        ("err-bistecca-grigia","Bistecca grigia senza crosta","cucina",
         "carne umida o padella non abbastanza calda: l'acqua in superficie evapora a 100C e impedisce la Maillard (che parte a 140C+). La carne si lessa invece di rosolare. Asciugare bene, padella rovente, non affollare","fen-rosolatura","niente crosta, colore grigio"),
        ("err-maionese-impazzita","Maionese impazzita (separata)","cucina",
         "olio aggiunto troppo in fretta all'inizio: l'emulsionante (lecitina del tuorlo) non riesce a rivestire tutte le gocce e l'emulsione si rompe. Ripartire da un nuovo tuorlo versandoci dentro la salsa impazzita lentamente","fen-emulsione-salse","olio separato, grumi"),
        ("err-pasta-collosa","Pasta collosa e scotta","cucina",
         "amido troppo gelatinizzato: cottura eccessiva o poca acqua. L'amido esce tutto e la pasta si impasta. Scolare al dente (cuore ancora vetroso), acqua abbondante","fen-pasta-acqua","pasta appiccicata, molla"),
        ("err-carne-secca-taglio","Carne asciutta appena tagliata","cucina",
         "tagliata senza riposo: i succhi in pressione al centro (fibre contratte dal calore) escono tutti al taglio. Far riposare (bistecca 5 min, arrosto 15-20) perche le fibre si rilassino e i succhi si ridistribuiscano","fen-riposo-carne","tagliere allagato, carne secca"),
        ("err-uova-gommose","Uova strapazzate gommose e asciutte","cucina",
         "fuoco troppo alto o troppo a lungo: le proteine si stringono ed espellono l'acqua. A fuoco dolce restano cremose. Togliere dal fuoco un attimo prima (carry-over)","fen-uova-coagulazione","gommose, acquose sul fondo"),
        ("err-verdure-smorte","Verdure verdi smorte, verde militare","cucina",
         "cottura troppo lunga: la clorofilla perde il magnesio e diventa feofitina (verde-oliva). Sbollentare veloce in acqua abbondante salata, poi shock in acqua e ghiaccio per fermare la cottura","fen-verdure-verdi","verde spento, oliva"),
        # bar
        ("err-drink-piatto","Cocktail piatto e stucchevole","bar",
         "manca l'acido o l'amaro: senza il taglio dell'acido (o del bitter) il dolce-forte non ha contrasto e risulta piatto. Cercare quale delle 4 forze (dolce/acido/forte/amaro) e fuori equilibrio","fen-equilibrio-cocktail","noioso, troppo dolce/pesante"),
        ("err-schiuma-collassa","Schiuma del sour che collassa subito","bar",
         "manca il dry shake: senza la prima shakerata a secco l'albume non si denatura abbastanza e la schiuma e grossolana e instabile. Dry shake 10-15s, poi con ghiaccio","fen-emulsione-bar","schiuma sparisce in pochi secondi"),
        ("err-highball-flat","Highball che diventa subito flat","bar",
         "CO2 persa: mixer non abbastanza freddo, ghiaccio tritato (troppa superficie di nucleazione) o bicchiere largo. Usare mixer freddissimo, ghiaccio grande e liscio, bicchiere alto e stretto","fen-carbonatazione","bollicine sparite, drink piatto"),
        # gelateria (i nuovi)
        ("err-gelato-granuloso-nuovo","Gelato granuloso (cristalli grossi)","gelateria",
         "mantecazione lenta o sbalzi termici: i cristalli d'acqua crescono grossi. Congelare rapido, mantecare (movimento continuo), catena del freddo stabile","fen-cristalli-ghiaccio","sgranocchia di ghiaccio"),
        # pasticceria
        ("err-cioccolato-opaco","Cioccolato opaco e molle (mal temperato)","pasticceria",
         "cristallizzazione nella forma sbagliata: senza temperaggio il burro di cacao solidifica in forme instabili (non la Forma V). Serve fondere a 45-50C, raffreddare a 27-28C, risalire a 31-32C (o seeding)","fen-temperaggio-cioccolato","niente snap, striature bianche"),
        ("err-crema-grumi","Crema pasticcera con grumi","pasticceria",
         "amido non disperso a freddo: aggiunto al caldo forma grumi. Stemperare l'amido a freddo prima, mescolare sempre, portare a bollore per gelatinizzare del tutto","fen-crema-pasticcera","grumi, sapore di farina"),
    ]
    try:
        conn = _get_conn(); cur = conn.cursor()
        fatti = []
        for eid, nome, dom, causa, fen, sintomo in ERRORI:
            cur.execute("SELECT id FROM nodes WHERE id=%s", (eid,))
            if not cur.fetchone():
                cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                            (eid,"Errore",nome,dom,_json.dumps({"causa":causa},ensure_ascii=False)))
            cur.execute("SELECT id FROM nodes WHERE id=%s", (fen,))
            if cur.fetchone():
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='fallisce_come' AND to_id=%s",(fen,eid))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                                (fen,eid,"fallisce_come",_json.dumps({"sintomo":sintomo},ensure_ascii=False)))
                    fatti.append(f"{fen} -> {eid} ({sintomo})")
                else:
                    fatti.append(f"{eid}: edge gia esiste")
            else:
                fatti.append(f"{fen}: FENOMENO ASSENTE, errore creato ma non collegato")
        conn.commit()
        return jsonify({"ok": True, "errori": fatti})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500

@bp.route("/admin/migra-schema-ricette")
def admin_migra_schema_ricette():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    # FASE 1 dell'audit ricette: colonne mancanti per procedimento, immagine, metadati, applicazioni, twist
    COLONNE = [
        "procedimento JSONB",      # lista [{n:int, testo:str, numero_chiave:str|null}]
        "immagine TEXT",           # url foto reale (Pexels)
        "immagine_autore TEXT",    # credito "Nome / Pexels"
        "immagine_url_fonte TEXT", # link alla pagina Pexels (richiesto dalle guidelines API)
        "tempo_prep INTEGER",      # minuti
        "tempo_cottura INTEGER",   # minuti
        "difficolta TEXT",         # facile / media / difficile
        "porzioni TEXT",           # "4 persone" / "6 drink"
        "applicazioni JSONB",      # lista di str: dove si usa questa preparazione
        "twist_di TEXT",           # id ricetta madre (NULL se originale)
        "tecniche JSONB",          # (idempotente se gia c'e)
        "abbinamenti JSONB",
        "vino_birra JSONB",
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        fatte, errori = [], []
        for col in COLONNE:
            cname = col.split()[0]
            try:
                cur.execute(f"ALTER TABLE ricette ADD COLUMN IF NOT EXISTS {col}")
                fatte.append(cname)
            except Exception as me:
                errori.append(f"{cname}: {me}")
        conn.commit(); cur.close()
        return jsonify({"ok": True, "colonne_ok": fatte, "errori": errori})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)

@bp.route("/admin/stato-madri")
def admin_stato_madri():
    """Diagnostica: per una lista di nodi, ritorna lunghezza scheda + inizio, per capire
    quali hanno il metodo (scheda lunga, apertura narrativa) e quali il contenuto vecchio."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json
    ids = request.args.get("ids", "").split(",")
    ids = [i.strip() for i in ids if i.strip()]
    try:
        conn = _get_conn(); cur = conn.cursor(); out = []
        for nid in ids:
            cur.execute("SELECT data FROM nodes WHERE id=%s", (nid,))
            row = cur.fetchone()
            if not row:
                out.append({"id": nid, "stato": "NON TROVATO"}); continue
            raw = row[0] if isinstance(row,(list,tuple)) else row["data"]
            nd = raw if isinstance(raw,dict) else json.loads(raw)
            sch = nd.get("scheda","")
            if isinstance(sch, dict): sch = sch.get("it","")
            full = request.args.get("full", "")
            entry = {"id": nid, "chars": len(sch or ""),
                     "inizio": (sch or "")[:90].replace(chr(10)," ")}
            if full:
                s = sch or ""
                entry["artefatti"] = {
                    "stelle": s.count("**"),
                    "triple_quote": s.count(chr(34)*3),
                    "backslash": s.count(chr(92)),
                    "titolo_vuoto": "\n\n\n" in s,
                }
            out.append(entry)
        cur.close(); _release_conn(conn)
        return jsonify({"madri": out})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/fix-target")
def admin_fix_target():
    """Ripulisce i campi target che aprivano con formula difensiva (Non/Nessun numero...).
    Riscrive dritti: dicono cosa È, non cosa non è. Non tocca le schede."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json
    TARGET = {
        "fen-acidita": "Una finestra dentro la tua ricetta, trovata assaggiando · pH per la sicurezza, acidità titolabile per l'asprezza",
        "fen-fat-washing": "Distillato limpido, sapido e vellutato, senza sensazione untuosa · l'alcol estrae, il freddo separa, il filtro pulisce",
        "fen-fermentazione": "Uno stato da raggiungere, non un orologio: insegui il picco di attività · la sua velocità raddoppia ogni 10°C",
        "fen-infusione": "La finestra dove hai preso il carattere prima che viri all'amaro · intensifica con la dose, non allungando il tempo",
        "fen-ossidazione": "Rallenta aria, luce e calore: l'ossidazione si combatte prima, non si corregge dopo",
        "fen-tannini": "L'astringenza giusta per l'uso: struttura in un rosso, un accenno in un cocktail · è tattile, si costruisce sorso dopo sorso · non coprirla con lo zucchero",
        "fen-viscosita": "Il comportamento nelle condizioni reali d'uso: alla temperatura e sotto la forza con cui lo servi",
    }
    try:
        conn = _get_conn(); cur = conn.cursor(); out = []
        for nid, tv in TARGET.items():
            cur.execute("SELECT data FROM nodes WHERE id=%s", (nid,))
            row = cur.fetchone()
            if not row: out.append(f"{nid}: NON TROVATO"); continue
            raw = row[0] if isinstance(row,(list,tuple)) else row["data"]
            nd = raw if isinstance(raw,dict) else json.loads(raw)
            nd["target"] = tv; nd["numero_bersaglio"] = tv
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(nd,ensure_ascii=False), nid))
            out.append(f"{nid}: OK")
        conn.commit(); cur.close(); _release_conn(conn)
        try:
            from routes.lezione import _lezione_cache as _lc; _lc.clear()
            from routes.lezione import _cache_home as _ch; _ch.clear()
        except Exception: pass
        return jsonify({"ok": True, "aggiornati": out})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/update-applicazioni")
def admin_update_applicazioni():
    """Scrive le schede-APPLICAZIONE (figlie di un fenomeno-madre) col metodo.
    Endpoint separato da update-schede-v2 (le madri): si arricchisce man mano che
    scriviamo applicazioni. Stessa logica di scrittura (scheda multilingua + target)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403

    SCHEDE_APP = {
        "fen-infusione": {
            "scheda": """Metti erbe, frutta o spezie dentro un distillato e aspetti: il liquido prende il loro sapore. È estrazione — la stessa fisica del caffè o del tè — ma qui il solvente è alcol, e questo cambia le regole del gioco.

L'infusione è estrazione applicata a un distillato: trasferisci composti aromatici da una botanica al liquido. Vale tutto quello che sai sull'estrazione — è una questione di trasferimento, non di forza, e si può sotto- o sovra-estrarre. Ma la matrice-alcol aggiunge tre cose specifiche che devi governare.

Cosa cambia perché il solvente è alcol

Primo: l'alcol scioglie cose che l'acqua non scioglie. Alcuni composti aromatici sono solubili nell'alcol ma non nell'acqua — per questo un'infusione in un distillato tira fuori un profilo diverso da un'infusione in acqua della stessa botanica. La gradazione conta: più alta è, più aggredisce le botaniche dure e ne estrae i composti (anche quelli amari); più bassa, più gentile. Una regola pratica dal banco: alcol forte (40%+) per radici e spezie coriacee, più leggero (20-30%) per erbe ed elementi delicati.

Secondo: la stessa trappola dell'estrazione madre, qui vestita da tempo. Un'infusione lasciata troppo a lungo o scaldata troppo diventa amara, vegetale, "stufata" — è la sovra-estrazione. E la regola per correggerla è precisa: se vuoi più intensità, aumenta la dose di botaniche, non allungare il tempo. Allungare il tempo estrae anche le cose sbagliate; più botanica estrae più delle cose giuste nello stesso tempo.

Terzo: caldo o freddo cambiano cosa estrai. A freddo (macerazione a temperatura ambiente) hai aromi puliti e freschi, ideale per fiori e frutta delicati che il calore "cuocerebbe". A caldo apri di più le botaniche dure e vai più veloce, ma rischi le note amare e la perdita di alcol. I barman usano anche vie rapide — il sifone con protossido d'azoto forza il liquido nelle cellule della botanica ed estrae in pochi minuti quello che a freddo richiede giorni.

Le leve, in pratica

La botanica (dose e tipo: dura o delicata, fresca o secca — le secche sono più concentrate, vogliono meno tempo). La gradazione dell'alcol (forte per il coriaceo, gentile per il delicato). La temperatura (freddo per pulito e delicato, caldo per veloce e profondo, col rischio amaro). Il tempo (la leva da toccare per ultima: prima aggiusti dose e temperatura). E fermare al punto giusto — filtrare toglie la botanica e blocca l'estrazione, come togliere le foglie del tè.

Come lo verifichi

Assaggi lungo il percorso: l'infusione è pronta quando ha preso il carattere che volevi e prima che viri all'amaro/vegetale. Il colore aiuta (molte botaniche cedono colore mentre cedono aroma) ma il giudice è il palato. Se vira amara, la prossima volta meno tempo o meno calore, non meno botanica.

Il bersaglio, letto bene

Non c'è un tempo universale — dipende dalla botanica, dalla gradazione, dalla temperatura e dal metodo (una macerazione a freddo di fiori è giorni, un sifone è minuti). Quello che c'è è una finestra per il tuo metodo: il punto in cui hai preso il carattere che cerchi senza scivolare nell'amaro. Lo trovi assaggiando la tua infusione, non copiando un numero — e ricordi che la leva giusta per intensificare è la dose, non il tempo.""",
            "target": "Non un tempo universale: la finestra per il tuo metodo, dove hai preso il carattere prima dell'amaro · intensifica con la dose, non col tempo",
        },
        "fen-fat-washing": {
            "scheda": """Sciogli del burro — o grasso di bacon, o olio d'oliva — in un distillato, lasci riposare, poi metti in freezer. Il grasso si solidifica in un disco che togli, e il distillato resta: limpido, ma con dentro il sapore del grasso e una consistenza vellutata. Sapore di burro nel bourbon, senza una goccia d'unto. È fat-washing, e dentro ci sono tre fenomeni che già conosci.

Il fat-washing è una delle tecniche più eleganti del bar moderno, e il motivo per cui funziona è che mette al lavoro insieme estrazione, emulsione e cristallizzazione. Capirla è vedere tre principi che convergono.

Perché l'alcol prende il sapore del grasso (estrazione)

Il cuore è la stessa cosa dell'infusione: l'alcol è un solvente. Ma qui estrae una classe di sapori speciale — quelli liposolubili, che vivono nei grassi e che l'acqua non tocca. Il sapore tostato del burro nocciola, l'affumicato del bacon, il fruttato-pepato dell'olio buono: sono composti che stanno nel grasso, e l'alcol li tira fuori. Per questo il fat-washing dà sapori che un'infusione in acqua non potrebbe mai dare: apri una dispensa aromatica che era chiusa.

Perché serve mescolare bene (emulsione)

C'è un passaggio in cui torna l'emulsione. Quando mescoli il grasso col distillato, crei interfacce temporanee tra le due fasi — grasso e liquido che normalmente non si amano. Quelle interfacce sono il ponte su cui i sapori passano dal grasso all'alcol. È il motivo per cui si agita: più contatto tra le fasi, più sapore trasferito. Il burro stesso, che è già un'emulsione di acqua e grasso, aiuta questo passaggio.

Perché il freezer separa tutto (cristallizzazione)

E qui l'idea geniale, che è pura cristallizzazione. Il grasso si scioglie nell'alcol a temperatura ambiente, ma congelandolo si solidifica — cristallizza — mentre l'alcol resta liquido. Così puoi separarli perfettamente: il grasso diventa un disco solido in superficie che sollevi con un cucchiaio, e il sapore che aveva ceduto resta disciolto nel distillato. Togli il grasso, tieni il sapore. Il freddo non è un dettaglio: è il meccanismo di separazione.

Cosa ottieni, e le leve

Il risultato non è solo sapore: è texture. Gli oli residui rivestono il palato e danno al distillato un corpo vellutato, e smorzano la durezza e l'astringenza dell'alcol — lo rendono più morbido. Le leve: il tipo di grasso (dà il carattere: burro nocciola, bacon, olio); la dose e il tempo di infusione (qualche ora a temperatura ambiente, assaggiando — troppo lo rende pesante); il congelamento completo (il grasso deve solidificare del tutto per separarsi pulito — freezer, diverse ore o tutta la notte); e la filtratura (una o più volte, panno o filtro, per togliere ogni residuo grasso e avere un distillato limpido).

Come lo verifichi

Guardi e assaggi: il distillato finito deve essere limpido (non torbido di grasso residuo — se lo è, rifiltri) e avere il sapore del grasso senza sembrare unto in bocca. La texture si sente: più rotonda, più piena. Se è troppo grasso o pesante, la prossima volta meno grasso o meno tempo di infusione.

Il bersaglio, letto bene

Non è un numero: è uno stato. Il fat-washing è riuscito quando il distillato ha preso carattere e corpo dal grasso, resta limpido, e non lascia una sensazione untuosa. Il bersaglio è quell'equilibrio — sapore e vellutato sì, unto no — e lo riconosci al palato e all'occhio, non su una tabella. Ricorda solo le tre fasi: l'alcol estrae (mescola bene), il freddo separa (congela del tutto), il filtro pulisce.""",
            "target": "Uno stato, non un numero: distillato limpido, sapido e vellutato, senza sensazione untuosa · l'alcol estrae, il freddo separa, il filtro pulisce",
        },
        "fen-clarificazione-cocktail": {
            "scheda": """Un succo di agrumi è torbido, opaco. Lo mescoli con del latte, il latte impazzisce in fiocchi, filtri — e quello che esce è un liquido cristallino, limpido come acqua, ma con tutto il sapore dentro. Oppure usi l'agar, o una centrifuga. La chiarificazione è togliere il torbido tenendo il gusto: e il metodo giusto dipende da COSA rende torbido il tuo liquido.

Chiarificare un cocktail non è solo estetica (anche se un drink cristallino colpisce): raffina la texture, spesso toglie amarezza e durezza, e — cosa che conta per chi lavora — permette di pre-battare, perché un liquido clarificato dura più a lungo. Ma la cosa importante da capire è che ci sono metodi diversi, e non sono intercambiabili: ognuno cattura un tipo diverso di torbidità.

Il punto chiave: cosa ti rende torbido il liquido?

Qui sta la distinzione che ti fa scegliere bene. Un liquido può essere torbido per due ragioni diverse. Per polifenoli, tannini, composti di colore — la torbidità di uno spirito invecchiato in legno, del tè, dei bitter. Oppure per particelle vegetali in sospensione — pectina e cellulosa, la polpa di un succo di frutta. Sono cose diverse, e vogliono metodi diversi. Sbagliare metodo significa filtrare e restare col torbido.

Il latte (milk washing): denaturazione al lavoro

Il milk washing sfrutta un fenomeno che conosci: la denaturazione delle proteine. Aggiungi un acido (succo di agrumi) al latte, e le caseine del latte denaturano e coagulano in fiocchi — esattamente come il latte che "impazzisce". Quei fiocchi hanno una superficie enorme e una leggera carica elettrica, e mentre precipitano attraverso il liquido attraggono e intrappolano le particelle: colore, tannini, fenoli amari. Filtri via i fiocchi, e con loro se ne vanno le impurità. In più il latte ammorbidisce: toglie la durezza e dà una texture silky. Ma attenzione — il latte lega bene i polifenoli (legno, tè, bitter): è il metodo per punch e sour, dove serve anche l'acido per far cagliare. Non è il metodo per la polpa di un succo.

L'agar (gel filtration): gelificazione al lavoro

Quando il torbido è polpa (succhi di frutta, verdura), serve un altro principio: la gelificazione. Sciogli l'agar nel liquido, lo lasci gelificare in un gel morbido che intrappola le particelle solide nella sua rete, poi lo congeli e lo scongeli: mentre si scioglie, il liquido cola via cristallino e le impurità restano nel gel. È il metodo per i succhi non acidi (pomodoro, cetriolo, frutta), ed è vegano. La proporzione tipica è piccola (intorno allo 0,2% di agar).

La centrifuga: fisica pura

Il metodo più tecnico: la centrifuga fa girare il liquido ad altissima velocità e spinge le particelle sospese verso l'esterno per forza, separandole in minuti invece che ore. Non aggiunge niente (né proteine né acqua), è il più puro — ma costa, quindi si usa quando i volumi lo giustificano o quando gli altri metodi non bastano.

Le leve, in pratica

La scelta del metodo in base alla torbidità (latte per polifenoli/durezza, agar per polpa, centrifuga per volume/purezza). L'acido, se usi il latte (serve a far cagliare). La pazienza (i fiocchi o il gel devono formarsi e precipitare — spesso si lascia riposare, anche a lungo). E la filtratura finale (panno, filtro fine — a volte più passaggi per la limpidezza cristallina).

Come lo verifichi

L'occhio: il liquido finito deve essere limpido, trasparente, senza velo. E il palato: il sapore dev'essere intatto (o migliorato — meno amaro, più morbido), non annacquato. Se resta torbido, o hai scelto il metodo sbagliato per quel tipo di torbidità, o serve un altro passaggio di filtro.

Il bersaglio, letto bene

Non è un numero: è uno stato doppio — limpidezza raggiunta E sapore preservato. Il bersaglio è il liquido cristallino che sa ancora di quello che era (o meglio). E la vera abilità non è "clarificare" in astratto, ma scegliere il metodo giusto per la tua torbidità: il latte non pulisce la polpa, l'agar non serve dove basta il latte. Riconosci cosa rende torbido il tuo liquido, e scegli lo strumento che cattura proprio quello.""",
            "target": "Doppio stato: limpidezza raggiunta E sapore intatto · scegli il metodo in base a cosa ti rende torbido (latte per polifenoli, agar per polpa)",
        },
        "fen-chiarificazione": {
            "scheda": """Un succo di agrumi è torbido, opaco. Lo mescoli con del latte, il latte impazzisce in fiocchi, filtri — e quello che esce è un liquido cristallino, limpido come acqua, ma con tutto il sapore dentro. Oppure usi l'agar, o una centrifuga. La chiarificazione è togliere il torbido tenendo il gusto: e il metodo giusto dipende da COSA rende torbido il tuo liquido.

Chiarificare un cocktail non è solo estetica (anche se un drink cristallino colpisce): raffina la texture, spesso toglie amarezza e durezza, e — cosa che conta per chi lavora — permette di pre-battare, perché un liquido clarificato dura più a lungo. Ma la cosa importante da capire è che ci sono metodi diversi, e non sono intercambiabili: ognuno cattura un tipo diverso di torbidità.

Il punto chiave: cosa ti rende torbido il liquido?

Qui sta la distinzione che ti fa scegliere bene. Un liquido può essere torbido per due ragioni diverse. Per polifenoli, tannini, composti di colore — la torbidità di uno spirito invecchiato in legno, del tè, dei bitter. Oppure per particelle vegetali in sospensione — pectina e cellulosa, la polpa di un succo di frutta. Sono cose diverse, e vogliono metodi diversi. Sbagliare metodo significa filtrare e restare col torbido.

Il latte (milk washing): denaturazione al lavoro

Il milk washing sfrutta un fenomeno che conosci: la denaturazione delle proteine. Aggiungi un acido (succo di agrumi) al latte, e le caseine del latte denaturano e coagulano in fiocchi — esattamente come il latte che "impazzisce". Quei fiocchi hanno una superficie enorme e una leggera carica elettrica, e mentre precipitano attraverso il liquido attraggono e intrappolano le particelle: colore, tannini, fenoli amari. Filtri via i fiocchi, e con loro se ne vanno le impurità. In più il latte ammorbidisce: toglie la durezza e dà una texture silky. Ma attenzione — il latte lega bene i polifenoli (legno, tè, bitter): è il metodo per punch e sour, dove serve anche l'acido per far cagliare. Non è il metodo per la polpa di un succo.

L'agar (gel filtration): gelificazione al lavoro

Quando il torbido è polpa (succhi di frutta, verdura), serve un altro principio: la gelificazione. Sciogli l'agar nel liquido, lo lasci gelificare in un gel morbido che intrappola le particelle solide nella sua rete, poi lo congeli e lo scongeli: mentre si scioglie, il liquido cola via cristallino e le impurità restano nel gel. È il metodo per i succhi non acidi (pomodoro, cetriolo, frutta), ed è vegano. La proporzione tipica è piccola (intorno allo 0,2% di agar).

La centrifuga: fisica pura

Il metodo più tecnico: la centrifuga fa girare il liquido ad altissima velocità e spinge le particelle sospese verso l'esterno per forza, separandole in minuti invece che ore. Non aggiunge niente (né proteine né acqua), è il più puro — ma costa, quindi si usa quando i volumi lo giustificano o quando gli altri metodi non bastano.

Le leve, in pratica

La scelta del metodo in base alla torbidità (latte per polifenoli/durezza, agar per polpa, centrifuga per volume/purezza). L'acido, se usi il latte (serve a far cagliare). La pazienza (i fiocchi o il gel devono formarsi e precipitare — spesso si lascia riposare, anche a lungo). E la filtratura finale (panno, filtro fine — a volte più passaggi per la limpidezza cristallina).

Come lo verifichi

L'occhio: il liquido finito deve essere limpido, trasparente, senza velo. E il palato: il sapore dev'essere intatto (o migliorato — meno amaro, più morbido), non annacquato. Se resta torbido, o hai scelto il metodo sbagliato per quel tipo di torbidità, o serve un altro passaggio di filtro.

Il bersaglio, letto bene

Non è un numero: è uno stato doppio — limpidezza raggiunta E sapore preservato. Il bersaglio è il liquido cristallino che sa ancora di quello che era (o meglio). E la vera abilità non è "clarificare" in astratto, ma scegliere il metodo giusto per la tua torbidità: il latte non pulisce la polpa, l'agar non serve dove basta il latte. Riconosci cosa rende torbido il tuo liquido, e scegli lo strumento che cattura proprio quello.""",
            "target": "Doppio stato: limpidezza raggiunta E sapore intatto · scegli il metodo in base a cosa ti rende torbido (latte per polifenoli, agar per polpa)",
        },
        "fen-poolish-biga": {
            "scheda": """Prendi una parte della farina, la stessa acqua, un pizzico di lievito, mescoli e lasci lì 12-16 ore. Il giorno dopo quella pastella gonfia e profumata entra nell'impasto vero. Non hai cambiato ricetta: hai fatto lavorare il tempo prima di cominciare. È fermentazione — la stessa della madre — ma spostata prima, in un pezzo separato. E il modo in cui la fai cambia il pane.

Il poolish e la biga sono pre-fermenti: una frazione dell'impasto che fermenta da sola, in anticipo, prima di essere unita al resto. È fermentazione applicata, con tutte le sue regole. Ma sposta la fermentazione "prima" ti dà tre cose che l'impasto diretto non ha, e la scelta tra poolish e biga decide quali.

Cosa cambia perché fermenti prima e a parte

Durante quelle ore lunghe succedono tre cose insieme, e sono le stesse dei fenomeni che conosci. Gli enzimi della farina lavorano: scompongono gli amidi in zuccheri semplici (più cibo per il lievito, più sapore) e ammorbidiscono il glutine in pezzi più gestibili — è l'attività enzimatica, che qui ha tempo di agire. Il lievito si moltiplica e crea acidi e aromi: è la fermentazione, ma lenta, che produce quella complessità "di grano" che un impasto veloce non ha. E la struttura matura: l'impasto finale diventa più forte, con più spinta in forno, e ti serve meno lievito nell'impasto vero perché una parte del lavoro è già fatta.

La distinzione che conta: liquido o sodo?

Qui sta la scelta vera, ed è una sola leva: quanta acqua metti nel pre-fermento. Il poolish è liquido — pari peso di farina e acqua (100% idratazione), una pastella molle e gonfia. La biga è soda — molta meno acqua (intorno al 50-60%), una palla compatta, quasi un impasto. Non è un dettaglio estetico: l'idratazione cambia cosa fermenta e come.

Un pre-fermento liquido come il poolish tende a dare un sapore più dolce, delicato, nocciolato, e più estensibilità all'impasto (si allunga di più). Una biga soda tende a dare un sapore più complesso e profondo, e più forza e "morso" al pane — struttura, masticabilità. Per questo il poolish è amato per baguette e pani croccanti, la biga per i rustici italiani, la ciabatta, la focaccia. Stessa fermentazione, due caratteri diversi, e la differenza la fai con l'acqua.

Le leve, in pratica

L'idratazione (poolish liquido per delicatezza ed estensibilità, biga soda per profondità e forza — la leva che definisce il carattere). La quota di farina pre-fermentata (di solito una parte, dal 20% a metà o più — più ne prefermenti, più marcato il carattere). Il tempo e la temperatura (lungo e fresco per sapore, seguendo il Q10: al fresco più lento e più aromatico). E il lievito nel pre-fermento (pochissimo — deve fermentare a lungo senza esaurirsi; se ne metti troppo, va troppo in fretta e "scade" prima).

Come lo verifichi — e qui torna la regola del pane

Il pre-fermento è pronto al suo picco, e il picco lo riconosci, non lo leggi sull'orologio. È gonfio, pieno di bolle, profumato, ed è raddoppiato — e soprattutto comincia appena a cedere al centro (la cupola che inizia ad afflosciarsi). Quello è il momento: massima attività, massimo sapore. Se aspetti troppo, collassa e diventa acido e stanco; se lo usi troppo presto, non ha ancora dato quello che poteva. La biga, essendo soda, è più tollerante — puoi dimenticartela un po' di più senza che "scada"; il poolish liquido è più preciso, va preso al momento.

Il bersaglio, letto bene

Il picco riconosciuto: gonfio, bolloso, raddoppiato, appena all'inizio del cedimento. È uno stato da vedere e annusare, e cambia con la temperatura e l'idratazione (un poolish caldo è pronto prima, una biga fresca ci mette di più). La scelta a monte — poolish o biga — non è "quale è meglio" ma quale carattere vuoi: delicato ed estensibile, o profondo e strutturato. E la regola che attraversa tutto il pane vale anche qui: guarda il pre-fermento, non l'orologio.""",
            "target": "Il picco riconosciuto: gonfio, bolloso, raddoppiato, appena all'inizio del cedimento · la leva è l'acqua: poolish liquido (delicato, estensibile) o biga soda (profondo, strutturato)",
        },
        "fen-fermentazione-lattica": {
            "scheda": """Due pani a lievito madre, stessa madre, stessa farina. Uno è morbido, tondo, con un'acidità delicata quasi da yogurt. L'altro è tagliente, pungente, sa quasi di aceto. Non hai cambiato ingredienti: hai cambiato come li hai fatti fermentare. Nel pane a lievito madre l'acidità non è un caso — è una leva che governi, se sai da dove viene.

La fermentazione lattica è fermentazione applicata al lievito madre: accanto ai lieviti (che fanno il gas) lavorano i batteri lattici, che producono acidi. È fermentazione — con tutte le sue regole — ma con un prodotto in più, l'acidità, ed è quella a dare al pane il suo carattere. Governarla vuol dire scegliere il sapore.

I due acidi: dolce e aspro sono due cose diverse

Il cuore è capire che "acido" nel lievito madre non è una cosa sola. I batteri producono due acidi con caratteri opposti. L'acido lattico dà un'acidità morbida, cremosa, quasi da yogurt — il lato gentile. L'acido acetico è tagliente, pungente, è lo stesso dell'aceto — il lato aggressivo. Il sapore del tuo pane è il rapporto tra questi due: più lattico e è tondo e delicato, più acetico e è aspro e mordace. Un equilibrio spesso citato come buono è intorno a 80% lattico e 20% acetico — morbido ma con carattere. E c'è un indizio che usi già senza saperlo: l'acetico è volatile, evapora, ed è l'unico dei due che riesci ad annusare. Quando la madre "punge" di aceto al naso, è l'acetico che sta prendendo il sopravvento.

Le leve che spostano il rapporto

Due leve principali, e le conosci già dalla fermentazione. La temperatura: fermentare al caldo (indicativamente 27-30°C) favorisce i lattici → pane più dolce e morbido; fermentare al fresco (20-24°C) favorisce l'acetico → pane più aspro e tagliente. È l'opposto di quello che l'istinto suggerirebbe (freddo = aspro, non dolce). L'idratazione: una madre e un impasto molli, idratati, favoriscono i lattici (morbido); una madre soda, poco idratata, favorisce l'acetico (aspro). Più altre leve fini: il tempo (più lungo = più acido totale), e la quantità di madre che usi (più madre = parti già più acido).

Il legame con l'acidità che già conosci

Qui torna la scheda acidità master, con la sua distinzione tra pH e acidità titolabile. Nel lievito madre la sentì tutta: due impasti possono avere lo stesso pH ma un'acidità titolabile molto diversa — e a contare per il gusto è quella titolabile, non il pH. Un pane fermentato a lungo può avere lo stesso pH di uno breve ma molta più acidità reale, e sapere più aspro. Il pH ti dice il livello, la titolabile ti dice quanto lo senti. È la stessa cosa del lime al bar, applicata al pane.

Il beneficio nascosto: non solo sapore

L'acidità del lievito madre non fa solo gusto: conserva. Lattico e acetico insieme rallentano le muffe — per questo il pane a lievito madre dura di più e ammuffisce più tardi di un pane a lievito di birra. È lo stesso principio che vedrai nella vita del pane: l'acidità è anche una difesa, non solo un aroma.

Come lo verifichi

Il naso e il palato. Al naso: se punge di aceto, c'è tanto acetico (fermentazione fresca/soda); se è più lattico-cremoso, dominano i lattici (caldo/molle). Al palato: tondo e delicato o tagliente e mordace. Se il pane è troppo aspro per i tuoi gusti, sposta verso il lattico — più caldo, più idratato, fermentazione più breve. Se è troppo piatto, il contrario. Cambia una leva per volta e senti come si muove il profilo.

Il bersaglio, letto bene

Il profilo acido che vuoi, riconosciuto al naso e in bocca: morbido-lattico o tagliente-acetico, o l'equilibrio nel mezzo. Non un numero di pH da inseguire — anzi, il pH da solo inganna, perché non dice quanto sentirai l'acido (conta la titolabile). Il bersaglio è il carattere giusto per il tuo pane, e la libertà vera è sapere che lo scegli tu, con temperatura e idratazione, invece di subirlo. Caldo e molle per il gentile, fresco e sodo per il mordace.""",
            "target": "Il profilo acido che scegli tu: caldo e molle → lattico morbido (yogurt), fresco e sodo → acetico tagliente (aceto) · il pH inganna, conta l'acidità titolabile · l'acetico è l'unico che annusi",
        },
        "fen-retrogradazione": {
            "scheda": """Il pane appena sfornato è morbido, la mollica cede sotto il dito. Il giorno dopo è più duro, asciutto, gommoso. Ti viene naturale pensare: ha perso acqua, si è seccato. È la spiegazione più ovvia, ed è sbagliata. Il pane raffermisce anche chiuso in un sacchetto, anche in ambiente umido — perché il raffermimento non è essiccazione. È l'amido che si riorganizza. E capirlo ti dice l'unica cosa che conta: dove tenere il pane.

La retrogradazione è il rovescio della gelatinizzazione. Ricordi: gelatinizzando, l'amido cotto assorbe acqua e si gonfia in una rete morbida, tipo gel — è quella che dà la mollica fresca. La retrogradazione è quel gel che, raffreddandosi e invecchiando, si disfa: le molecole di amido si riallineano e ricristallizzano, tornando verso una struttura rigida. È gelatinizzazione al contrario, ed è il vero motore del raffermimento.

Non è secchezza: è ricristallizzazione

Questo è il punto che ribalta l'intuito, ed è stato dimostrato più di un secolo fa: il pane raffermisce anche se non perde acqua. Chiudilo ermeticamente e raffermisce lo stesso. Quello che succede non è che l'acqua evapora — è che l'amido, che dopo la cottura era in uno stato disordinato e morbido, si riorganizza in cristalli rigidi, e nel farlo espelle l'acqua dalla sua struttura verso gli spazi tra le molecole. L'acqua è ancora lì dentro, ma non più dove serve: la mollica diventa dura e asciutta al tatto anche se il contenuto d'acqua è quasi lo stesso. Raffermire è un fatto di struttura, non di quantità d'acqua.

Due tempi: amilosio subito, amilopectina per giorni

La retrogradazione ha due fasi, guidate dalle due parti dell'amido. L'amilosio ricristallizza in fretta — nelle prime ore — e dà l'indurimento iniziale, quello che senti già il primo giorno. L'amilopectina è più lenta: ricristallizza nei giorni successivi, ed è responsabile dell'indurimento che continua al secondo, terzo giorno. Per questo il pane non "muore" tutto insieme: c'è un peggioramento rapido subito e uno lento e prolungato dopo.

Il fatto che spiazza tutti: il frigo è il posto peggiore

Qui la conseguenza pratica più importante, e la più controintuitiva. Il freddo del frigorifero accelera il raffermimento, non lo rallenta. La velocità di retrogradazione segue una curva a U con la temperatura: è massima proprio tra 0 e 10°C — cioè la temperatura del frigo. A temperatura ambiente è più lenta. E il congelatore la quasi ferma del tutto, perché blocca il movimento delle molecole. Quindi la regola è: pane a temperatura ambiente per il breve termine, congelatore per il lungo — mai in frigo, che è la scelta peggiore anche se l'istinto "freddo = si conserva" dice il contrario.

E si può tornare indietro (per un po')

Buona notizia: la retrogradazione è in parte reversibile. Scaldare il pane raffermo — nel forno, nel tostapane — rigelatinizza parzialmente l'amido ricristallizzato e restituisce morbidezza: il pane vecchio tostato torna buono. Ma è temporaneo: appena si raffredda, ricomincia a retrogradare, e più in fretta di prima (le catene sono già parzialmente allineate). Un pane lo puoi "resuscitare" col calore una volta, non all'infinito.

Come lo rallenti (le leve)

La conservazione (ambiente per giorni, freezer per settimane, mai frigo). Grassi e zuccheri nell'impasto (interferiscono con la ricristallizzazione: per questo una brioche resta morbida più a lungo di una baguette magra). La lunga fermentazione e l'acidità (il pane a lievito madre, più acido, retrograda più lentamente). E il tenerlo ben chiuso (non contro l'essiccazione in sé, ma per non perdere anche acqua in aggiunta al raffermimento).

Il bersaglio, letto bene

Non è fermare il raffermimento — è impossibile, l'amido ricristallizza sempre. È rallentarlo il più possibile. Il bersaglio è la scelta giusta per il tuo orizzonte: temperatura ambiente e sacchetto per il pane che mangi in un giorno o due, freezer per quello che tieni, forno per resuscitare quello raffermo. E la cosa da ricordare, contro ogni istinto: il frigo è il nemico del pane, non il suo alleato.""",
            "target": "Rallentare non fermare: l'amido ricristallizza sempre · NON è secchezza (raffermisce anche sigillato) · il frigo è il PEGGIO (curva a U, max 0-10°C) · ambiente per giorni, freezer per settimane, calore resuscita",
        },
        "fen-shelf-life-pane": {
            "scheda": """"Quanto dura il pane?" è la domanda sbagliata, perché il pane muore in due modi diversi, e confonderli ti fa sbagliare la conservazione. Un pane può diventare duro e raffermo pur restando sano da mangiare; un altro può restare morbido ma ammuffire. Sono due nemici distinti — il raffermire e l'ammuffire — e vogliono difese opposte. Capire quale stai combattendo è metà del lavoro.

La vita del pane non è una cosa sola. Ci sono due processi che la limitano, indipendenti, con cause e rimedi diversi. Trattarli come se fossero lo stesso problema è l'errore che porta a mettere il pane in frigo "per conservarlo" e ottenere il peggio di entrambi.

Nemico 1: il raffermire (struttura)

Il primo è il raffermimento, ed è la retrogradazione che conosci: l'amido ricristallizza, la mollica indurisce, il pane diventa asciutto e gommoso. Non è pericoloso — un pane raffermo si mangia benissimo (tostato, in zuppa, in un panzanella) — è un decadimento di texture. E lo governi con la temperatura giusta: ambiente per il breve, freezer per il lungo, mai frigo (che lo accelera). Il raffermire è una questione di struttura dell'amido.

Nemico 2: l'ammuffire (biologia)

Il secondo è tutt'altro: la muffa, un fungo che cresce sul pane. Questo sì è un problema di sicurezza — un pane ammuffito non si mangia. E dipende da una cosa diversa: l'acqua disponibile. Non l'acqua totale, ma l'acqua "libera", quella che i microrganismi possono usare — si chiama attività dell'acqua, Aw. Più è alta (pane umido, morbido, ben chiuso in un sacchetto caldo), più le muffe crescono in fretta. La muffa ama caldo e umido. Il raffreddamento la rallenta — ed ecco il paradosso del frigo: rallenta la muffa ma accelera il raffermire. Per questo il frigo è una pessima idea per il pane fresco (peggiora la texture) ma i due nemici tirano in direzioni opposte.

Il conflitto: perché non c'è una conservazione unica

Qui sta il punto. Le condizioni che frenano un nemico spesso favoriscono l'altro. Chiudere bene il pane trattiene umidità → mollica morbida più a lungo (bene contro il raffermire) ma più acqua libera → muffa più veloce (male). Il frigo → meno muffa ma più raffermire. Il freezer è l'unico che vince su entrambi: ferma quasi il raffermimento e blocca la muffa (al gelo il fungo non cresce e l'amido non ricristallizza). Ecco perché congelare è la vera risposta per il lungo termine.

Le leve, e come l'acidità aiuta

La temperatura (ambiente per giorni, freezer per settimane, frigo mai per il pane fresco). La chiusura (un equilibrio: abbastanza da non seccare e non raffermire troppo, non così ermetica da favorire la muffa in un pane umido). E un alleato che conosci: l'acidità del lievito madre. Il pane a lievito madre dura di più per due motivi insieme — retrograda più lentamente (basso pH) e resiste meglio alla muffa (lattico e acetico sono antifungini). L'acidità difende su entrambi i fronti: è per questo che un pane a pasta madre "invecchia bene" mentre un pane a lievito di birra raffermisce e ammuffisce prima.

Come lo verifichi

Guarda e tocca, e distingui. Duro ma pulito, senza macchie né odore strano → raffermo, non pericoloso: recuperalo col calore o usalo da raffermo. Macchie (verdi, bianche, nere), odore di muffa, filamenti → ammuffito: si butta, tutto, non solo la parte visibile. Riconoscere quale dei due hai davanti ti dice se stai perdendo qualità (raffermo) o sicurezza (muffa).

Il bersaglio, letto bene

Non "far durare il pane" in astratto, ma sapere contro quale nemico stai giocando e scegliere la difesa giusta. Il bersaglio è la conservazione adatta all'orizzonte e al tipo di pane: ambiente e sacchetto per il consumo veloce, freezer per il lungo, l'acidità della pasta madre come alleato naturale su entrambi i fronti. E la regola che riassume tutto: il raffermire è texture (recuperabile), la muffa è sicurezza (no) — non curarli con lo stesso gesto, e per il pane fresco tieni lontano il frigo.""",
            "target": "Due nemici diversi: il raffermire (texture, recuperabile) e la muffa (sicurezza, si butta) · difese in conflitto, solo il freezer vince su entrambi · l'acidità della pasta madre aiuta su tutti e due",
        },
        "fen-laminazione": {
            "scheda": """Chiudi un panetto di burro dentro l'impasto, stendi, pieghi, metti in frigo. Ripeti. Ogni piega moltiplica gli strati: dopo tre o quattro giri hai decine di fogli sottilissimi di impasto alternati a burro. In forno l'acqua del burro diventa vapore, spinge gli strati uno contro l'altro e li separa: nasce il croissant, friabile e cavo. È maglia glutinica che tiene, e vapore che spinge — due cose che conosci, messe a lavorare insieme.

La laminazione è la tecnica dietro croissant, sfoglia, pain au chocolat: creare strati alternati di impasto e grasso che in forno si separano. Non è una ricetta a sé, è un principio — e capirlo ti fa capire perché riesce o fallisce.

Il cuore: il burro deve restare uno strato, non sciogliersi nell'impasto

Questa è la cosa che decide tutto. L'obiettivo è tenere il burro come fogli distinti dentro l'impasto, sottili e continui. Se il burro resta separato, in forno la sua acqua evapora, il vapore spinge, e gli strati si aprono in quella struttura a nido d'ape. Se invece il burro si scioglie e si mescola all'impasto, gli strati spariscono: ottieni pane denso, unto, senza sfoglia. Tutta la tecnica serve a una cosa sola: impedire che il burro si fonda nell'impasto prima del forno.

Perché la temperatura è la leva numero uno

Ecco perché la laminazione è ossessionata dal freddo. Il burro deve essere solido ma flessibile — indicativamente intorno ai 14-18°C: abbastanza freddo da restare uno strato, abbastanza morbido da stendersi senza rompersi. Troppo caldo si scioglie e si incorpora (strati persi); troppo freddo si spezza in schegge che bucano l'impasto (strati rotti). Ed è lo stesso motivo per cui si riposa in frigo tra una piega e l'altra: raffredda il burro che il lavoro ha scaldato, e — qui entra la madre — rilassa il glutine.

Dove entra il glutine (la madre)

Il glutine è quello che tiene. La rete glutinica dà all'impasto la struttura ed elasticità per stendersi in fogli sottili senza strapparsi e per trattenere gli strati di burro. Ma il glutine lavorato si tende e "combatte": se non lo lasci rilassare, l'impasto si ritira e si strappa, e gli strati si rovinano. Per questo la laminazione alterna sempre lavoro e riposo: stendi (tendi il glutine), riposi in frigo (il glutine si rilassa, il burro si rassoda), ripeti. È maglia glutinica governata nel tempo.

Il forno: il vapore che solleva (ponte con la crosta)

In forno succede la magia, ed è vapore. L'acqua contenuta nel burro evapora, resta intrappolata tra gli strati di impasto e li spinge separandoli: gli strati si gonfiano e si fissano. Ma serve un forno davvero caldo: se è troppo tiepido, gli strati si afflosciano e il burro cola prima che il vapore faccia in tempo a sollevarli. Forno caldo, partenza decisa — come per la crosta.

Le leve, in pratica

La temperatura di burro e impasto (la leva critica: freddi ma flessibili, alla stessa consistenza). Il numero di giri (più pieghe = più strati, ma con un limite: troppe pieghe comprimono e schiacciano gli strati, e l'interno perde l'ariosità — non è "più è meglio"). Il riposo tra i giri (per rilassare il glutine e rassodare il burro — saltarlo rovina gli strati). E il forno caldo alla partenza (perché il vapore sollevi prima che il burro coli).

Come lo verifichi

Prima del forno: taglia un bordo e guarda gli strati — devono essere visibili, distinti, netti. Se sono un blocco confuso, il burro si è fuso: lavora più freddo. Dopo il forno: il taglio deve mostrare un nido d'ape aperto, e la pasta deve sfogliarsi in scaglie leggere. Se è densa o gommosa, o il burro si è fuso, o il forno era freddo, o mancava riposo.

Il bersaglio, letto bene

Strati distinti che sopravvivono fino al forno: il burro è rimasto uno strato, mai fuso nell'impasto. È uno stato che vedi — nel taglio a crudo (strati netti) e nel taglio cotto (nido d'ape, sfoglia). Non un numero di gradi o di pieghe da inseguire, ma la condizione: burro freddo e continuo, glutine rilassato, forno caldo. Se tieni il burro dov'è — uno strato, non un ingrediente sciolto — la sfoglia viene da sé.""",
            "target": "Strati distinti che sopravvivono al forno: il burro è rimasto uno strato, mai fuso nell'impasto · burro freddo e flessibile (14-18°C), glutine rilassato, forno caldo · lo vedi nel taglio (nido d'ape)",
        },
        "fen-sale-impasto": {
            "scheda": """Metti il 2% di sale nell'impasto — dieci grammi su mezzo chilo di farina — ed è la cosa più piccola che ci butti dentro. Ma toglilo, e il pane cambia del tutto: fermenta all'impazzata, si affloscia, esce pallido e insipido. Il sale è l'ingrediente che pesa meno e fa più lavori. E il primo di quei lavori è osmosi — quella che già conosci.

Il sale nel pane non è solo sapore. Fa cinque cose insieme: controlla il lievito, rinforza il glutine, protegge la struttura dagli enzimi, tiene il colore della crosta, e sì, dà sapore. Capire come le fa — e una sorpresa su quale conta davvero — ti dà il controllo su tutto l'impasto.

Il sale e il lievito: qui c'è l'osmosi (e una sorpresa)

La spiegazione classica è osmosi pura, ed è vera: il sale è igroscopico, tira acqua. In presenza di sale, il lievito cede parte della sua acqua all'ambiente più salato — per osmosi, la stessa che governa il sale sulle cellule — e questo rallenta la sua attività. Senza sale il lievito fermenta troppo in fretta e in modo incontrollabile, produce gas più veloce di quanto il glutine possa trattenerlo, e l'impasto sovra-lievita e collassa.

Ma qui la sorpresa, ed è puro metodo: la spiegazione "il sale rallenta il lievito per osmosi" è vera solo in parte. La ricerca mostra che l'osmosi sul lievito, alle concentrazioni normali di pane, ha un effetto minore sulla velocità di fermentazione. La causa principale del rallentamento è un'altra: l'effetto del sale sul glutine. Attento a non fermarti alla prima spiegazione plausibile.

Il sale e il glutine: il vero motore del rallentamento

Ecco cosa succede davvero. Le proteine del glutine, nell'impasto, hanno cariche elettriche che si respingono, tenendo la rete allentata. Il sale neutralizza quelle cariche: sparite le forze di repulsione, i filamenti si avvicinano, la rete si compatta e si lega più forte. Una rete glutinica più compatta e forte fa due cose: trattiene meglio il gas (più struttura, più spinta) e — proprio perché è più tenace — resiste di più all'espansione, quindi l'impasto cresce più lentamente. Quindi il sale rallenta la lievitazione soprattutto rinforzando il glutine, non affamando il lievito. È la stessa maglia glutinica che conosci, governata con un pizzico di sale.

Il sale e gli enzimi, il sale e la crosta

Altri due lavori. Il sale tiene a freno le proteasi, gli enzimi che spezzano il glutine: un po' fa bene (ammorbidisce), troppo a lungo senza controllo degraderebbe la struttura fino a farla collassare in una lunga fermentazione. E il sale protegge il colore: senza sale il lievito divora tutti gli zuccheri, e senza zuccheri residui la crosta non fa la Maillard e resta pallida — lo stesso meccanismo del caso crosta pallida. Il sale, moderando il lievito, lascia zuccheri per la doratura.

Le leve, in pratica

La quantità (lo standard è circa il 2% sulla farina; è la finestra dove tutto funziona). Sotto l'1,5% il lievito corre, l'impasto diventa appiccicoso e il pane esce chiaro e scipito. Sopra il 2,5-3% l'impasto si stringe troppo, il lievito rallenta molto, la crescita cala. Quando aggiungerlo (spesso dopo l'autolisi, non all'inizio — perché il sale compete con l'acqua e frena l'idratazione della farina). Come distribuirlo (sciolto nell'acqua o ben miscelato, per evitare "tasche" di sale e — attenzione — il contatto diretto sul lievito non disciolto, che per osmosi può ucciderlo, come nel caso del pane che non lievita).

Come lo verifichi

Il sapore prima di tutto: un pane senza sale si riconosce subito, sa di cartone. Ma anche la struttura: un impasto senza sale è slegato, molle, appiccicoso, difficile da lavorare; con la giusta dose è più coeso ed elastico. E la crosta: pallida e opaca segnala spesso poco sale (lievito che ha mangiato gli zuccheri). Se hai dubbi, cambia solo il sale tenendo tutto il resto uguale, e senti la differenza su sapore, struttura e colore.

Il bersaglio, letto bene

C'è una finestra vera qui: intorno al 2% sulla farina, con un intervallo utile stretto (circa 1,8-2,2%). Ma non è un numero-legge da applicare a occhi chiusi: dipende dal pane (alcuni ne vogliono un po' meno o più), e sopra o sotto la finestra gli effetti sono noti e prevedibili — poco sale, lievito veloce e crosta pallida; troppo, impasto stretto e crescita frenata. Il bersaglio è tarare il sale dentro quella finestra per il tuo pane, sapendo che stai regolando quattro cose insieme — lievito, glutine, enzimi, colore — con un solo ingrediente.""",
            "target": "Una finestra vera: ~2% sulla farina (utile 1,8-2,2%) · poco sale = lievito veloce e crosta pallida, troppo = impasto stretto e crescita frenata · con un ingrediente regoli lievito, glutine, enzimi e colore",
        },
        "fen-autolisi": {
            "scheda": """Mescoli solo farina e acqua, appena il tempo di bagnarla, e la lasci lì. Niente impasto, niente sale, niente lievito — solo farina, acqua e mezz'ora. Quando torni, l'impasto è liscio, morbido, si allunga senza strapparsi: sembra lavorato, e tu non hai fatto niente. È autolisi, ed è la prova che nel pane il tempo può fare il lavoro delle mani.

L'autolisi è un riposo di sola farina e acqua prima di aggiungere il resto. È maglia glutinica applicata — la stessa rete che conosci — ma sviluppata da sola, dal tempo, invece che dall'impastamento. Capire come e perché funziona ti fa capire una cosa profonda sul pane: la struttura non nasce solo dalla fatica, nasce dall'acqua e dal tempo.

Il glutine si forma da solo (la madre, senza le mani)

Sai dalla scheda maglia glutinica che glutenina e gliadina, bagnate, si legano in una rete. Di solito questo lavoro lo forziamo impastando. Ma quelle proteine si organizzano anche da sole: basta acqua e tempo. Durante l'autolisi le proteine si idratano, si distendono e cominciano a legarsi senza che tu faccia niente. Per questo dopo l'autolisi l'impasto è già liscio e richiede molto meno lavoro: una parte del glutine si è sviluppata da sé. È maglia glutinica, ma governata col riposo invece che con la forza.

Gli enzimi al lavoro: la doppia azione

Intanto succede un'altra cosa, e qui entra l'attività enzimatica. Nella farina bagnata si attivano due enzimi. Le amilasi trasformano l'amido in zuccheri semplici — cibo per il lievito che arriverà, e precursori del colore e del sapore. Le proteasi fanno qualcosa di apparentemente contraddittorio: spezzano un po' i legami delle proteine del glutine. Aspetta — non stavamo costruendo il glutine? Sì. Ed è il punto bello: durante l'autolisi il glutine si costruisce e si ammorbidisce nello stesso momento. Le due cose insieme danno l'estensibilità: la capacità dell'impasto di allungarsi senza spezzarsi né ritirarsi.

Elasticità ed estensibilità: perché servono entrambe

Un buon impasto ha bisogno di due qualità opposte. L'elasticità (torna indietro, tiene la forma) e l'estensibilità (si allunga senza strapparsi). Troppa elasticità e l'impasto è duro, si ritira, combatte; troppa estensibilità e è molle, non tiene. L'autolisi lavora sull'estensibilità — l'ammorbidimento delle proteasi rende l'impasto più stendibile, meno "nervoso". Ecco perché è amata per baguette e pani a lunga fermentazione: dà quella stendibilità che rende l'impasto docile e aiuta la spinta in forno (non deve combattere contro un glutine troppo tenace).

Perché niente sale e niente lievito

C'è una ragione se durante l'autolisi si mette solo farina e acqua. Il sale stringe il glutine e rallenta gli enzimi — messo ora, frenerebbe proprio l'ammorbidimento che cerchi (è l'altra faccia di quello che hai visto nella scheda del sale). Il lievito comincerebbe a fermentare prima che l'impasto sia pronto. Ritardarli lascia all'estensibilità il tempo di svilupparsi pulita. Sale e lievito entrano dopo.

La trappola: troppo a lungo si rovescia

Qui la cosa importante, ed è puro metodo. L'autolisi sviluppa il glutine, ma lo scompone anche — è la stessa proteasi a farlo. Per un tempo giusto, l'equilibrio pende dalla parte buona: più liscio, più estensibile. Ma se esageri, le proteasi continuano a degradare e l'equilibrio si rovescia: l'impasto perde struttura, diventa troppo estensibile, molle, appiccicoso, non si modella più, e cuoce in una pagnotta piatta. Più a lungo non è meglio: c'è una finestra, e oltre quella il beneficio si trasforma nel suo contrario.

Come lo verifichi

Con le mani. Dopo il riposo l'impasto dev'essere più liscio, morbido, e allungabile senza rotture nette — tira un lembo e deve stendersi, non spezzarsi subito. Quello è il punto giusto. Se è diventato una poltiglia molle che non tiene, hai aspettato troppo: la prossima volta accorcia. Un impasto forte, tenace, poco estensibile beneficia di più dell'autolisi; uno già molle ne ha bisogno di meno.

Il bersaglio, letto bene

Uno stato riconoscibile con le mani: impasto liscio ed estensibile, che si allunga docile senza strapparsi, e prima che diventi molle e slegato. Non un tempo fisso da cronometrare — dipende dalla farina (le forti, ricche di glutine, ne traggono più beneficio e reggono riposi più lunghi; le deboli meno) e dalla temperatura. Il bersaglio è quel punto di estensibilità, riconosciuto toccando, dentro la finestra prima che le proteasi rovescino il gioco. Il tempo lavora per te — ma solo fino a un certo punto.""",
            "target": "Uno stato con le mani: impasto liscio ed estensibile, che si allunga docile senza strapparsi, prima che diventi molle · il tempo lavora al posto dell'impasto, ma solo fino a un certo punto",
        },
    }
    CASI = {
        "proc-negroni-inconsistente": {
            "scheda": """SINTOMO

Fai il Negroni come sempre: parti uguali, gin, bitter, vermouth. Niente da spremere, niente da montare, la ricetta più semplice che esista. Eppure una sera è perfetto — strutturato, aperto, equilibrato — e un'altra sera è una bomba: caldo, aggressivo, troppo dolce, o al contrario acquoso e spento. Stessa bottiglia, stesse dosi, stessa mano. Il cliente abituale te lo dice: "stasera è diverso". E ha ragione.

IPOTESI

L'istinto dice: ho sbagliato la ricetta. Ma la ricetta non è cambiata — le dosi sono quelle. Quindi l'ipotesi giusta è un'altra: il problema non è nella ricetta, è nel processo. Due Negroni con proporzioni identiche possono risultare completamente diversi, e la ragione sta in variabili che non sono scritte sulla ricetta e che cambiano ogni volta senza che tu le controlli. Il Negroni è l'esempio perfetto perché, non avendo niente da spremere o montare, mette a nudo proprio quelle variabili nascoste.

I FENOMENI IN GIOCO

Quando cerchi la causa, tre fenomeni che conosci lavorano insieme:

La diluizione. Un Negroni ha bisogno di una quantità precisa di acqua — quella che entra sciogliendo il ghiaccio mentre mescoli — per aprire il gin e ammorbidire l'amaro. Una mescolata frettolosa di dieci secondi lascia il drink poco diluito: caldo, aggressivo, e paradossalmente più dolce, perché senza acqua le note non si aprono. Una mescolata troppo lunga, o su ghiaccio piccolo e bagnato, lo annega. La diluizione non è un optional del Negroni: è un ingrediente, e se cambia di sera in sera il drink cambia.

La temperatura. Diluizione e freddo viaggiano insieme — il ghiaccio raffredda proprio sciogliendosi (lo sai dalla scheda diluizione). Ma il ghiaccio non è sempre uguale: cubetti grandi e densi si sciolgono lenti e diluiscono poco, ghiaccio piccolo e umido si scioglie in fretta e diluisce tanto. E il bicchiere: uno spesso isola e tiene freddo, uno sottile lascia che la mano scaldi e il ghiaccio corra. Se una sera usi ghiaccio diverso o un bicchiere diverso, hai cambiato diluizione e temperatura senza accorgertene.

La concentrazione. Il Negroni non è statico: al primo sorso è fermo e strutturato, poi si apre mentre il ghiaccio nel bicchiere continua a sciogliersi — la concentrazione cala nel tempo e i sapori si riequilibrano. Quindi conta anche quando lo assaggi e quanto lentamente lo bevi. Lo stesso drink è diverso al primo e all'ultimo sorso.

LA VERIFICA

Come capisci quale variabile ti sta tradendo? Una alla volta, come sempre. Non cambiare tutto insieme. Fai lo stesso Negroni e misura la sola diluizione: pesa o guarda il volume finale dopo la mescolata — se una sera è 90 ml e un'altra 108 ml, hai trovato la variabile. Oppure tieni la mescolata identica (conta le rotazioni, o cronometra 20-25 secondi) e cambia solo il ghiaccio: se il risultato cambia, è il ghiaccio. Il palato ti dice che è diverso; la misura ti dice cosa è diverso. È l'unico modo di trasformare "stasera è strano" in "stasera ho diluito il 20% invece del 25%".

LA CONCLUSIONE

Non hai un problema di ricetta. Hai un problema di processo. E i problemi di processo si risolvono standardizzando il processo, non ritoccando le dosi. Il modo più pulito: il batch. Pre-mescoli il Negroni con la sua acqua di diluizione già dentro (intorno al 20-25% del volume, l'acqua che avrebbe preso mescolando) e lo tieni in frigo o freezer. Da quel momento ogni Negroni viene dallo stesso mix: identico, sera dopo sera, indipendentemente da chi lo versa, da quanto è affollato il banco, da com'è il ghiaccio. Hai tolto le variabili nascoste rendendole fisse.

E questa è la lezione oltre il Negroni: quando un piatto o un drink "cambia senza motivo", quasi mai è la ricetta. Sono le variabili di processo che non stai controllando. Matter ti insegna a vederle, misurarle una alla volta, e fissarle.""",
            "target": "Non è la ricetta, è il processo: isola la variabile nascosta (diluizione, ghiaccio, temperatura), misurala, poi fissala col batch",
        },
        "proc-variabilita-lime": {
            "scheda": """SINTOMO

Il tuo sour è tarato alla perfezione: dose di lime fissa, sciroppo fisso, distillato fisso. Funziona da mesi. Poi arriva una cassa di lime nuova e all'improvviso lo stesso drink è troppo aspro, o troppo piatto. Non hai cambiato niente nella ricetta. Cambi fornitore, cambia stagione, e il sour balla. Ti ritrovi a "aggiustare a naso" ogni volta, e due bartender dello stesso locale fanno lo stesso drink leggermente diverso.

IPOTESI

Non è la tua mano e non è la ricetta: è la materia prima che non è mai la stessa. Il succo di lime varia in acidità secondo la dimensione del frutto, la freschezza, la stagione, la cultivar e quanto era maturo alla raccolta — e spesso gli agrumi vengono raccolti acerbi per il trasporto, con meno zucchero e più asprezza. Quindi la dose fissa di lime sulla ricetta non è una dose fissa di acidità: è un volume fisso di un liquido la cui forza cambia. Stai misurando i millilitri, ma quello che conta per il gusto è l'acido dentro quei millilitri.

I FENOMENI IN GIOCO

Qui torna in pieno la scheda acidità. Ricordi la distinzione fondamentale: una cosa è quanto liquido metti, un'altra è quanta acidità titolabile contiene. Il lime "standard" sta intorno al 6% di acidità titolabile, ma è una media — la TA reale oscilla parecchio (indicativamente 4-8% a seconda del frutto). Se un giorno il tuo lime è al 5% e un altro al 7%, la stessa dose di 22 ml porta nel bicchiere quantità di acido diverse, e il sour cambia. E non è solo intensità: il lime è fatto di acido citrico più malico (il limone è quasi solo citrico), e il malico fa durare l'asprezza più a lungo — per questo il lime "si sente" diverso, non solo più o meno forte.

C'è anche la fragilità nel tempo: il lime è l'agrume più instabile, comincia a cambiare nel momento in cui lo spremi. Un succo spremuto ora e uno di due ore fa non hanno lo stesso profilo. Quindi anche quando l'hai spremuto è una variabile.

LA VERIFICA

Il palato ti dice che il sour è cambiato; non ti dice di quanto è cambiata l'acidità. Per saperlo, misuri. Il modo semplice al banco: assaggia il succo nuovo accanto a quello vecchio, affiancati, e senti se è più o meno aspro. Il modo preciso: misuri l'acidità titolabile del succo (una titolazione veloce), e scopri che la cassa nuova è al 7% invece del 6%. A quel punto sai esattamente cosa correggere e di quanto — non vai più a naso. È la stessa logica dell'acidità master: isola la variabile (l'acidità del succo), misurala, poi correggi.

LA CONCLUSIONE

La soluzione da professionista non è rincorrere il lime aggiustando a occhio ogni sera: è fissare l'acidità invece del volume. Due strade. La prima, semplice: assaggi ogni cassa nuova e ritari la dose di conseguenza (più lime se è debole, meno se è forte) per riportare il sour al suo punto. La seconda, da bar che vuole consistenza assoluta: l'acid-adjusting — porti ogni succo a un'acidità titolabile fissa (il riferimento è ~6%, l'equilibrio classico con uno sciroppo a 50 Brix in parti uguali), aggiungendo acido dove serve. Così la tua "unità di lime" ha sempre la stessa forza, la stagione non conta più, e ogni bartender fa lo stesso identico drink.

La lezione oltre il lime: quando la materia prima varia, non inseguirla a naso. Misura la proprietà che conta (qui l'acidità, non il volume) e fissala. È la differenza tra un bar che spera e un bar che controlla.""",
            "target": "Non inseguire il lime a naso: misura l'acidità (non il volume) e fissala — assaggia ogni cassa o fai acid-adjusting",
        },
        "proc-q10-filo-rosso": {
            "scheda": """SINTOMO

Ti accorgi di un filo che torna dappertutto. Il succo di lime dura un giorno a temperatura ambiente ma tre in frigo. La fermentazione va veloce d'estate e si impunta d'inverno. Un'infusione al caldo è pronta in ore, a freddo in giorni. Un vino aperto invecchia in fretta sul bancone e piano in cantina. Sembrano cose diverse, ma sotto c'è un'unica regola: la temperatura comanda la velocità di quasi tutto quello che succede nei tuoi ingredienti. E c'è perfino un numero che gira: "ogni 10 gradi, la velocità raddoppia". È vero? E quanto puoi fidartene?

IPOTESI

L'ipotesi è che dietro decine di fenomeni diversi ci sia un solo principio: le reazioni chimiche e biologiche vanno più veloci quando fa caldo e più piano quando fa freddo, in modo regolare. Questo principio ha un nome — il coefficiente Q10 — e dice che per molti sistemi la velocità di reazione raddoppia circa a ogni 10°C in più (e si dimezza a ogni 10°C in meno). Se è vero, non è un fatto isolato: è una lente che spiega conservazione, fermentazione, ossidazione, estrazione tutte insieme.

I FENOMENI CHE ATTRAVERSA

Guarda quanti banchi tocca lo stesso principio:

Conservazione. Il lime dura poco perché appena spremuto iniziano reazioni che lo degradano. Il freddo le rallenta: ecco perché il frigo raddoppia (o più) la vita del succo. Stessa logica per sciroppi, purè, latte, garnish.

Fermentazione. I lieviti e i batteri lavorano più in fretta al caldo. Una fermentazione a temperatura più alta è più rapida ma meno controllata; una più fresca è lenta e pulita. Governare la temperatura è governare la velocità del processo.

Ossidazione. Un vino o un distillato aperto si ossida più in fretta al caldo. Tenerlo fresco rallenta il decadimento. Stesso principio del cibo che irrancidisce.

Estrazione. L'hai già visto: infusione a caldo veloce, a freddo lenta. È Q10 applicato all'estrazione — la temperatura decide quanto in fretta i composti passano nel solvente.

Un solo principio, quattro banchi diversi. Questo è il filo rosso.

LA VERIFICA — e qui il metodo ti salva

Ora la parte importante, quella che distingue Matter da un ricettario. Quel numero — "raddoppia ogni 10°C", Q10 = 2 — è vero come regola-guida, ma NON è una legge esatta da applicare a occhi chiusi. Il valore reale cambia da reazione a reazione: per alcuni deterioramenti è più vicino a 2, per altri a 3, per altri meno. Dipende dal tipo di reazione, dall'acidità, dall'umidità. È un modello, non una costante universale. Chi prende il "raddoppia ogni 10 gradi" come verità assoluta sbaglia, perché applica un numero-legge dove c'è solo una tendenza.

Come lo usi bene, allora? Come bussola, non come GPS. Ti dice la direzione con certezza — più freddo = più lento, sempre — e l'ordine di grandezza — parliamo di raddoppi, non di piccole differenze. Ma la misura vera la fai sul tuo ingrediente: quanto dura davvero il tuo lime in frigo contro fuori, quanto rallenta la tua fermentazione di quei gradi. Il principio ti dice dove guardare e cosa aspettarti; il tuo banco ti dà il numero preciso.

LA CONCLUSIONE

Q10 è il filo rosso di Matter: un principio unico che collega conservazione, fermentazione, ossidazione, estrazione, e mezzo mestiere. Impararlo bene ti dà due cose insieme. Primo, un potere: capisci che controllare la temperatura è controllare la velocità di quasi tutto, e questo cambia come conservi, fermenti, estrai. Secondo, una difesa: riconosci che il numero preciso (il "raddoppia ogni 10°C") è una guida, non una legge — e non ti fai fregare da chi lo spaccia per verità assoluta.

Ed è la lezione che riassume il metodo intero: i grandi principi sono veri e potenti come direzione, ma il numero esatto lo trovi sempre nella tua materia, non su una tabella. Sapere questo — fidarsi del principio e misurare il dettaglio — è la differenza tra sapere le cose a memoria e capirle.""",
            "target": "Un principio, non un numero: più freddo rallenta tutto (conservazione, fermentazione, ossidazione, estrazione) · il 'raddoppia ogni 10°C' è una bussola non un GPS · fidati del principio, misura il dettaglio nella tua materia",
        },
        "proc-pane-non-lievita": {
            "scheda": """SINTOMO

Impasti come sempre, copri, aspetti. Torni dopo un'ora e mezza e l'impasto è lì, piatto, uguale a quando l'hai lasciato. Non è cresciuto. Oppure è cresciuto pochissimo, e in forno resta un mattone denso invece di aprirsi. Stessa farina, stessa ricetta di sempre — eppure oggi non va. È il problema più frustrante del forno, perché quando te ne accorgi spesso è troppo tardi.

IPOTESI

L'errore è cercare "la" causa unica. Un impasto che non lievita non ha una sola spiegazione: ha una famiglia di cause possibili, e il mestiere è saperle isolare. Ma la buona notizia è che non sono infinite — si raggruppano in quattro famiglie: la vitalità del lievito (è vivo?), la temperatura (è nell'intervallo giusto?), la struttura dell'impasto (il glutine trattiene il gas?), e l'equilibrio degli ingredienti (qualcosa sta bloccando il lievito?). Quattro porte da controllare, in ordine.

I FENOMENI IN GIOCO

Sotto le quattro famiglie ci sono fenomeni che conosci:

Fermentazione — il lievito è vivo? La lievitazione è fermentazione: il lievito, un organismo vivo, mangia zuccheri e produce CO₂. Se il lievito è morto o scaduto, non produce gas, punto. È la causa numero uno. E il lievito si uccide facilmente: acqua troppo calda (sopra una certa soglia lo ammazza all'istante), o lievito vecchio che ha perso forza.

Calore — la temperatura è giusta? Il lievito è vivo ma sensibile alla temperatura, ed è puro Q10: al freddo rallenta tantissimo, al caldo giusto lavora, troppo caldo muore. In una cucina fredda lo stesso impasto che di solito raddoppia in un'ora e mezza può metterci tre o quattro ore — non è morto, è solo lento. E l'acqua con cui impasti è la leva più insidiosa: tiepida attiva, bollente uccide.

Osmosi — il sale ha bloccato il lievito? Qui torna l'osmosi. Il sale in alta concentrazione tira l'acqua fuori dalle cellule del lievito e le disidrata: se butti il sale direttamente sul lievito non disciolto, lo uccidi al contatto. È il motivo della regola classica — sale e lievito su lati opposti della ciotola, mai insieme secchi. Troppo sale in generale rallenta il lievito anche se ben distribuito.

Maglia glutinica — il gas resta intrappolato? Anche se il lievito produce CO₂, quel gas deve essere trattenuto. È il glutine a farlo: la rete di proteine che si forma impastando funziona come un palloncino che intrappola le bolle. Se l'impasto è poco lavorato la rete è debole e il gas scappa: l'impasto non si gonfia anche se il lievito lavora. Troppa farina rende l'impasto rigido e soffoca la crescita.

LA VERIFICA

Come trovi quale delle quattro porte è quella giusta? Una alla volta, in ordine di probabilità. Prima il lievito: lo "provi" (proof) — sciogli un po' di lievito in acqua tiepida con un pizzico di zucchero e aspetti; se fa schiuma è vivo, se resta fermo è morto, e hai la risposta. Poi la temperatura: misura l'acqua col termometro (tiepida, non calda) e la stanza — se è fredda, non è un problema, è lentezza, aspetta di più. Poi il sale: ricordi come l'hai aggiunto? Direttamente sul lievito? Poi la lavorazione: l'impasto era liscio ed elastico, tornava indietro se premuto, o era rigido e strappato? Ogni verifica esclude una porta finché resti con quella giusta.

E la regola d'oro che le attraversa tutte: giudica dalla condizione, non dall'orologio. "Un'ora e mezza" non è la lievitazione — il raddoppio dell'impasto è la lievitazione. Il tempo è un'indicazione, non un traguardo; guarda l'impasto, non il timer.

LA CONCLUSIONE

L'impasto che non cresce non è sfortuna: è una di quattro famiglie di cause, e il metodo è controllarle in ordine invece di indovinare. Se il lievito è morto, riparti (in forno non risorge). Se è freddo, aspetti. Se hai bruciato il lievito col sale o con l'acqua calda, sai cosa correggere la prossima volta. Se il glutine è debole, impasti di più.

La lezione oltre il pane: davanti a un fallimento con più cause possibili, non cambiare tutto a caso. Isola le variabili una alla volta, in ordine di probabilità, e lascia che ogni prova elimini una possibilità. È lo stesso metodo del Negroni e del lime — solo applicato al banco del forno.""",
            "target": "Non cercare la causa unica: 4 famiglie (lievito vivo? temperatura? glutine? sale?) da controllare in ordine · giudica dalla condizione (il raddoppio) non dall'orologio",
            "nome": "Il pane che non lievita",
            "dominio": "panificazione",
        },
        "proc-crosta-pallida": {
            "scheda": """SINTOMO

Il pane è cresciuto bene, è cotto dentro, ma esce dal forno pallido. Una crosta bianca, molliccia, senza quel colore dorato che dice "buono" ancora prima di assaggiare. Sembra crudo anche se non lo è. E un pane senza crosta ambrata non solo è meno bello: gli manca metà del sapore, perché è proprio nella crosta che si sviluppano gli aromi della cottura.

IPOTESI

La crosta pallida non è un difetto della lievitazione — quella è andata. È un problema di doratura: la reazione che colora la crosta non è avvenuta abbastanza. E quella reazione ha un nome e delle condizioni precise. Se manca il colore, manca una delle condizioni. L'ipotesi è che ci sia una tra poche cause ben identificabili, e come sempre si isolano una alla volta.

I FENOMENI IN GIOCO

Al centro c'è la reazione di Maillard — la stessa della scheda crosta. È la reazione tra zuccheri e amminoacidi (proteine) che, sotto il calore, produce il colore dorato e gli aromi tostati. Perché avvenga servono tre cose insieme: calore sufficiente, zuccheri, e amminoacidi. Togline una e la crosta resta pallida. Ecco le cause, ognuna legata a una condizione mancante:

Il calore non basta (fenomeno: calore + Maillard). La Maillard parte solo oltre una certa temperatura — indicativamente sopra i 150°C, e il pane vuole forni belli caldi (spesso 190-230°C) per una buona crosta. Se il forno è troppo tiepido, o non era davvero preriscaldato, la reazione va troppo piano e la crosta non colora. E attenzione alla trappola: il forno può mentire. Il termostato dice 200° ma dentro ce ne sono 170. Un forno che non è mai davvero caldo è la causa numero uno di croste pallide.

Manca lo zucchero (fenomeno: Maillard). Se non c'è abbastanza zucchero, la Maillard ha poco carburante. Ecco perché gli impasti magri — pane, baguette, solo farina/acqua/lievito/sale — vengono più chiari degli impasti ricchi come la brioche, pieni di zucchero e grassi che dorano splendidamente. Non è un difetto della baguette, è la sua natura; ma se vuoi più colore su un impasto magro, un velo di latte o uovo in superficie prima di infornare dà amminoacidi e zuccheri alla crosta.

Troppo vapore (fenomeno: vapore + calore). Qui c'è il paradosso che confonde tutti. Il vapore all'inizio serve — tiene la crosta morbida qualche minuto così il pane cresce bene. Ma se il vapore resta per tutta la cottura, la crosta non si asciuga e non può dorare: la Maillard ha bisogno che la superficie si secchi. Vapore all'inizio sì, poi via — deve dissiparsi perché la crosta colori.

LA VERIFICA

Una causa alla volta, in ordine di probabilità. Prima il forno: metti un termometro da forno dentro e guarda se raggiunge davvero la temperatura che imposti — è la verifica che smaschera la bugia più comune. Poi la ricetta: è un impasto magro? Allora il pallore è in parte normale, e sai che per più colore serve una spennellata o più temperatura. Poi il vapore: ne stai mettendo troppo, o troppo a lungo? Prova a farlo uscire dopo i primi minuti. Ogni prova esclude una causa. E la regola d'oro vale anche qui: giudica dalla condizione, non dall'orologio — cuoci finché la crosta è dorata e soda, non finché "sono passati i minuti".

LA CONCLUSIONE

La crosta pallida è la Maillard che non è avvenuta abbastanza, e le cause sono poche e precise: forno non abbastanza caldo (spesso perché mente), poco zucchero nell'impasto, troppo vapore che non fa asciugare la crosta. Controlli in ordine e trovi quale delle condizioni della Maillard mancava.

La lezione oltre il pane: quando una reazione non "parte", torna alle sue condizioni e controlla quale manca. La Maillard vuole calore, zuccheri, superficie asciutta — se il risultato non c'è, una di queste è assente. Sapere di quali condizioni ha bisogno un fenomeno ti dice esattamente cosa cercare quando non succede. È lo stesso ragionamento del bar, applicato al forno: non indovinare, controlla le condizioni.""",
            "target": "La crosta pallida è Maillard mancata: controlla le sue 3 condizioni (calore, zuccheri, superficie asciutta) · il forno spesso mente, verifica col termometro · vapore all'inizio poi via",
            "nome": "La crosta che resta pallida",
            "dominio": "panificazione",
        },
    }
    SCHEDE_MADRI_NUOVE = {
        "fen-cristalli-ghiaccio": {
            "scheda": """La differenza tra un gelato cremoso e uno che "sgranocchia" di ghiaccio sta tutta nella dimensione dei cristalli d'acqua. Piccoli = vellutato; grandi = granuloso. E la dimensione dei cristalli non e magia: si governa con la velocita di congelamento e col movimento. E il principio numero uno della gelateria.

Il gelato e acqua congelata in cui sono dispersi zuccheri, grassi, aria e solidi. Quando l'acqua congela forma cristalli: se sono piccolissimi (sotto i 50 micron) la lingua non li distingue = cremoso; se crescono grandi = texture granulosa, "ghiacciata".

Come si tengono piccoli i cristalli
CONGELAMENTO RAPIDO: piu veloce congeli, meno tempo hanno i cristalli per crescere, piu restano piccoli e numerosi. Per questo il gelato industriale (o all'azoto liquido) e ultra-cremoso: congela in fretta. La mantecazione lenta a casa fa cristalli piu grandi.
MOVIMENTO CONTINUO (mantecazione): mescolare durante il congelamento spezza i cristalli mentre si formano e li tiene piccoli, e insieme incorpora aria. Un composto fermo nel freezer fa un blocco di ghiaccio; mantecato, fa gelato.

Il nemico: la ricristallizzazione
Durante la conservazione, se il gelato si scalda e ri-congela (sbalzi di temperatura, freezer aperto), i cristalli piccoli si fondono e ri-crescono piu GRANDI: il gelato diventa granuloso col tempo. Per questo la catena del freddo stabile e la conservazione contano quanto la preparazione.
Il bersaglio: cristalli piccoli (sotto 50 micron) = cremoso, grandi = granuloso. Congela RAPIDO e MANTECA (movimento continuo spezza i cristalli). Il nemico e la ricristallizzazione da sbalzi di temperatura: catena del freddo stabile.""",
            "target": "Cristalli piccoli (sotto 50 micron) = cremoso, grandi = granuloso: congela RAPIDO e MANTECA (movimento spezza i cristalli), nemico la ricristallizzazione da sbalzi",
            "nome": "Cristalli di ghiaccio (cremosita)",
            "dominio": "gelateria",
        },
        "fen-zuccheri-pac": {
            "scheda": """Perche un gelato resta morbido e cavabile a -15C mentre l'acqua pura a quella temperatura e un mattone di ghiaccio? Perche lo zucchero abbassa il punto di congelamento. E i gelatieri lo misurano con un numero, il PAC (potere anticongelante): e la leva per decidere quanto morbido sara il gelato. Sbagliare lo zucchero vuol dire un gelato o troppo duro o che non tiene.

Lo zucchero disciolto nell'acqua ABBASSA il punto di congelamento (freezing point depression): l'acqua zuccherata congela sotto 0C, e piu zucchero c'e, piu bassa la temperatura serve per congelarla. Nel gelato questo significa: a temperatura di conservazione, una parte dell'acqua resta NON congelata (grazie allo zucchero), e quella frazione liquida rende il gelato morbido e cavabile invece che un blocco.

Il PAC: la misura del gelatiere
Il PAC (Potere Anti-Congelante) e un numero che quantifica quanto un ingrediente abbassa il punto di congelamento. Zuccheri diversi hanno PAC diversi: il fruttosio e il glucosio/destrosio abbassano di piu (a parita di peso) del saccarosio, perche hanno molecole piu piccole (piu molecole per grammo = piu effetto). Per questo i gelatieri MISCELANO zuccheri: saccarosio per dolcezza, destrosio/fruttosio per morbidezza extra senza troppa dolcezza. Bilanciare il PAC = decidere la consistenza a una data temperatura.

Il sorbetto: solo zucchero, niente grasso
Nel sorbetto (frutta, acqua, zucchero, niente latte) il PAC dello zucchero e l'UNICA leva contro la durezza: troppo poco e diventa un ghiacciolo, troppo e non tiene. Per questo il bilanciamento zuccheri e ancora piu critico.
Il bersaglio: lo zucchero abbassa il punto di congelamento (PAC) = gelato morbido a -15C. Zuccheri piccoli (fruttosio, destrosio) abbassano di piu del saccarosio: si miscelano per dolcezza + morbidezza. Nel sorbetto lo zucchero e l'unica leva.""",
            "target": "Lo zucchero abbassa il punto di congelamento (PAC) = gelato morbido a -15C: zuccheri piccoli (fruttosio/destrosio) abbassano piu del saccarosio, si miscelano, nel sorbetto unica leva",
            "nome": "Zuccheri e punto di congelamento (PAC)",
            "dominio": "gelateria",
        },
        "fen-grassi-stabilizzanti": {
            "scheda": """Oltre ai cristalli piccoli e allo zucchero, due ingredienti costruiscono la cremosita del gelato lavorando sull'acqua: il grasso, che maschera i cristalli e da corpo, e gli stabilizzanti, che legano l'acqua e le impediscono di formare cristalli grandi. Capirli e la differenza tra un gelato che regge e uno che "suda" e diventa ghiacciato.

Il grasso: corpo e mascheramento
Il grasso (dal latte, panna, tuorlo) fa due cose. Interferisce fisicamente con le molecole d'acqua, ostacolando la formazione dei cristalli. E MASCHERA i cristalli residui: rivestendo la lingua, fa percepire come liscio anche cio che non lo e del tutto. Il gelato ha meno grasso dell'ice cream (4-8% contro 10-20%): meno grasso vuol dire sapori piu diretti e vividi (il grasso ottunde il gusto), ma serve piu attenzione agli altri fattori per la cremosita. Il tuorlo aggiunge anche lecitina, che emulsiona.

Gli stabilizzanti: legare l'acqua
Guar, farina di semi di carrube, xantano, carragenina: sono idrocolloidi che LEGANO l'acqua libera, aumentano la viscosita del composto e frenano la crescita dei cristalli (l'acqua legata non e libera di ri-cristallizzare). Fanno tre cose: gelato piu cremoso, piu resistente agli sbalzi di temperatura, e piu longevo in conservazione. Si usano in dosi piccolissime (frazioni di percento).

L'aria (overrun) chiude il quadro
L'aria incorporata mantecando (vedi overrun) alleggerisce e contribuisce alla cremosita: le bollicine piccole e ben stabilizzate rendono il gelato piu vellutato. Il gelato ha poco overrun (20-30%) contro l'ice cream (fino al 50%): piu denso e ricco.
Il bersaglio: grasso maschera i cristalli e da corpo (ma ottunde il gusto: il gelato ne ha meno, 4-8%). Stabilizzanti legano l'acqua libera = piu cremoso, regge gli sbalzi, dura di piu (dosi piccolissime). L'aria alleggerisce.""",
            "target": "Grasso maschera i cristalli e da corpo (ottunde il gusto: gelato 4-8%), stabilizzanti legano l'acqua libera = piu cremoso regge sbalzi dura di piu (dosi minime)",
            "nome": "Grassi e stabilizzanti (gelateria)",
            "dominio": "gelateria",
        },
        "fen-fermentazione-alcolica": {
            "scheda": """Vino, birra, e ogni bevanda alcolica nascono dallo stesso gesto invisibile: un lievito che mangia zucchero e produce alcol e anidride carbonica. E lo stesso microrganismo del pane, ma qui l'alcol e il prodotto, non un effetto collaterale. Capire la fermentazione e capire la radice di intere categorie di bevande.

Il lievito (Saccharomyces) consuma gli ZUCCHERI e li trasforma in ETANOLO (alcol) + ANIDRIDE CARBONICA (CO2) + calore + centinaia di composti aromatici (esteri, che danno note fruttate e floreali). E la stessa fermentazione del pane, ma nel pane si cattura la CO2 (che gonfia) e l'alcol evapora in cottura; qui si tiene l'alcol.

Da dove viene lo zucchero: la differenza vino/birra
VINO: lo zucchero c'e gia, e quello dell'uva. Si pigia l'uva, il lievito (selvatico sulle bucce o aggiunto) fermenta il mosto. Piu zucchero nell'uva = piu alcol potenziale (10-15% secondo il clima). Se il lievito non finisce tutto lo zucchero, restano zuccheri residui = vino dolce.
BIRRA: lo zucchero NON c'e pronto, e imprigionato come amido nel malto d'orzo. Serve un passaggio in piu, l'ammostamento (mashing): il malto in acqua calda attiva enzimi che spezzano l'amido in zuccheri, creando il mosto dolce (wort). Solo dopo il lievito puo fermentare.

La temperatura governa il carattere
Fermentazioni fredde e lente (vini bianchi 7-20C, birre lager) preservano aromi delicati; fermentazioni calde (vini rossi, birre ale) estraggono e sviluppano piu carattere. La temperatura decide lo stile.
Il bersaglio: lievito mangia zucchero → alcol + CO2 + aromi (esteri). Vino: zucchero dall'uva (pronto). Birra: zucchero dal malto via ammostamento (enzimi spezzano l'amido). Freddo = delicato, caldo = carattere.""",
            "target": "Lievito mangia zucchero → alcol + CO2 + aromi: vino zucchero dall'uva (pronto), birra dal malto via ammostamento (enzimi spezzano l'amido), freddo delicato caldo carattere",
            "nome": "Fermentazione alcolica (vino e birra)",
            "dominio": "vino",
        },
        "fen-tannini-vino": {
            "scheda": """Quella sensazione asciutta e allappante che ti "graffia" la bocca dopo un sorso di vino rosso sono i tannini. Non e un difetto: e la struttura del vino, la sua ossatura. E la differenza tra un rosso e un bianco sta proprio in una scelta - fermentare con le bucce o senza.

I tannini sono polifenoli presenti nelle BUCCE, nei vinaccioli (semi) e nei raspi dell'uva (e anche nel legno delle botti). Sono amari e soprattutto ASTRINGENTI: si legano alle proteine della saliva e le fanno precipitare, da cui la sensazione di secchezza e "presa" in bocca. Sono la stessa famiglia di composti dei tannini del te e del caffe.

La scelta rosso/bianco
E qui sta la differenza fondamentale. Il ROSSO fermenta CON le bucce (e vinaccioli): durante la fermentazione l'alcol che sale estrae dai solidi il colore E i tannini. Piu contatto con le bucce = piu colore, piu struttura, piu tannino. Il BIANCO si fa pressando subito e separando il succo dalle bucce PRIMA della fermentazione: niente estrazione di colore e tannino, vino piu leggero e fresco. Non e questione di uva bianca o nera: e questione di contatto con le bucce.

I tannini nel tempo
I tannini danno al vino la capacita di invecchiare: col tempo si polimerizzano, diventano piu morbidi, e la sensazione astringente si ammorbidisce. Un rosso giovane molto tannico e "duro"; lo stesso vino dopo anni e piu rotondo. Sono anche antiossidanti naturali che proteggono il vino.
Il bersaglio: tannini (polifenoli di bucce/semi) = astringenza + struttura (legano la saliva). Rosso = fermenta CON le bucce (estrae colore e tannino), bianco = SENZA. Col tempo i tannini si ammorbidiscono (invecchiamento). Stessa famiglia del te/caffe.""",
            "target": "Tannini (polifenoli bucce/semi) = astringenza + struttura: rosso fermenta CON le bucce (estrae colore e tannino), bianco SENZA, col tempo si ammorbidiscono",
            "nome": "Tannini e struttura del vino",
            "dominio": "vino",
        },
        "fen-luppolo": {
            "scheda": """Se la birra non fosse amara sarebbe stucchevole: il malto porta zuccheri e dolcezza, e qualcosa deve bilanciarli. Quel qualcosa e il luppolo, il fiore che da alla birra amaro, aroma e persino conservazione. E quando si aggiunge nella bollitura decide se avrai amaro o profumo.

Il luppolo e il fiore di una pianta (Humulus lupulus) che si aggiunge al mosto durante la bollitura. Fa tre cose: da AMARO (bilancia la dolcezza del malto), da AROMA (note floreali, agrumate, resinose), e conserva (ha proprieta antibatteriche naturali che proteggevano la birra prima della refrigerazione).

Il momento dell'aggiunta decide tutto
Qui sta la fisica interessante. Gli acidi amari del luppolo (alfa-acidi) hanno bisogno di essere ISOMERIZZATI dalla bollitura prolungata per diventare solubili e amari - serve tempo di bollore. Ma gli oli aromatici del luppolo sono VOLATILI: se bolli a lungo, evaporano e perdi l'aroma. Da qui la regola:
- Luppolo a INIZIO bollitura (60+ min): massimo amaro, aroma evaporato. E il luppolo "da amaro".
- Luppolo a FINE bollitura (o dopo, "dry hopping"): poco amaro, massimo aroma (gli oli non evaporano). E il luppolo "da aroma".
Il birraio dosa i due momenti per costruire il profilo. L'amaro si misura in IBU (International Bitterness Units).
Il bersaglio: luppolo = amaro (bilancia il malto) + aroma + conservazione. Presto in bollitura = amaro (isomerizza gli alfa-acidi, l'aroma evapora), tardi/dry hopping = aroma (oli volatili preservati). L'amaro si misura in IBU.""",
            "target": "Luppolo = amaro (bilancia il malto) + aroma + conservazione: presto in bollitura = amaro (isomerizza, aroma evapora), tardi/dry hopping = aroma, si misura in IBU",
            "nome": "Il luppolo e l'amaro della birra",
            "dominio": "birra",
        },
        "fen-macinatura-caffe": {
            "scheda": """Lo stesso caffe, macinato fine o grosso, da due bevande diverse: una perfetta, una imbevibile. La macinatura e la leva piu potente e piu sottovalutata dell'espresso. Governa quanto velocemente l'acqua estrae, e l'estrazione decide tutto: troppo poca e acido e acquoso, troppa e amaro e bruciato.

Fare il caffe e ESTRARRE composti solubili (aromi, acidi, caffeina, oli) dalla polvere con l'acqua. Il grado di estrazione decide il gusto: SOTTO-estratto (poca) = acido, aspro, acquoso, "vuoto"; SOVRA-estratto (troppa) = amaro, astringente, bruciato. Nel mezzo c'e la finestra giusta. Si misura con TDS (solidi disciolti) e EY (extraction yield).

La macinatura governa la velocita
Piu la polvere e fine, piu superficie espone all'acqua, piu veloce l'estrazione (e viceversa). Questo deve accordarsi col metodo:
- ESPRESSO: acqua ad alta pressione che passa in ~25-30 secondi. Serve macinatura FINE (tanta superficie, estrazione veloce nel poco tempo). Troppo grossa = acqua che scorre via sotto-estratta e acquosa; troppo fine = acqua bloccata, sovra-estratta e amara.
- FILTRO/moka/french press: acqua a bassa pressione, contatto piu lungo. Serve macinatura piu GROSSA (estrazione piu lenta, adeguata al tempo lungo).

Le altre leve
Oltre alla macinatura: la DOSE (quanto caffe), la TEMPERATURA (acqua ~90-96C, troppo calda estrae amaro, troppo fredda sotto-estrae), il TEMPO di contatto, la pressione. La crema dell'espresso e un'emulsione di oli e CO2 spinta dalla pressione.
Il bersaglio: estrazione = composti solubili dall'acqua (sotto=acido/acquoso, sopra=amaro/bruciato, in mezzo la finestra). La macinatura governa la velocita: FINE per espresso (veloce), GROSSA per filtro/moka (lenta). Acqua 90-96C.""",
            "target": "Estrazione = solubili dall'acqua (sotto acido/acquoso, sopra amaro/bruciato): macinatura governa la velocita, FINE per espresso GROSSA per filtro/moka, acqua 90-96C",
            "nome": "Macinatura e estrazione del caffe",
            "dominio": "caffetteria",
        },
        "fen-temperaggio-cioccolato": {
            "scheda": """Perche il cioccolato di una tavoletta industriale fa "snap" quando lo spezzi, e lucido, e si scioglie in bocca - mentre quello fuso e ricolato in casa viene opaco, molle, striato di bianco? La differenza e il TEMPERAGGIO: un ballo di temperature che costringe il burro di cacao a cristallizzare nella forma giusta. E fisica dei cristalli, ed e la cosa che separa il cioccolatiere dal dilettante.

Il burro di cacao e un grasso POLIMORFICO: puo solidificare in sei forme cristalline diverse (I-VI), ognuna con proprieta diverse. Solo una, la FORMA V (beta), da il cioccolato perfetto: fonde a 34C (appena sotto la temperatura corporea, per questo si scioglie in bocca), fa lo snap netto, e lucido, resiste al bloom (le striature bianche). Le altre forme danno cioccolato molle, opaco, ceroso.

Le curve di temperatura (il ballo)
Temperare = guidare il cioccolato attraverso temperature precise perche si formino SOLO cristalli Forma V. Per il fondente:
1. FONDERE a 45-50C: si sciolgono TUTTI i cristalli (si azzera).
2. RAFFREDDARE a 27-28C mescolando: si formano molti cristalli, sia stabili (V) sia instabili (I-IV).
3. RISALIRE a 31-32C (temperatura di lavoro): si FONDONO le forme instabili (che fondono piu basso), SOPRAVVIVE solo la Forma V.
Restano cristalli-seme di Forma V nel cioccolato fuso: raffreddando, "seminano" tutto il resto in Forma V. Il latte vuole temperature leggermente piu basse. Anche 2 gradi di errore ti buttano nella forma sbagliata: serve il termometro.

Il metodo seeding (piu semplice)
Invece delle curve, si puo aggiungere cioccolato GIA temperato (25-30%) tritato fine al fuso a ~34C: i suoi cristalli Forma V fanno da seme e innescano la cristallizzazione giusta. Piu facile da controllare.
Il bersaglio: Forma V del burro di cacao = snap, lucido, fonde a 34C, no bloom. Curve 45-50 → 27-28 → 31-32C (fondi tutto, cristallizzi, elimini le forme instabili). O seeding con cioccolato temperato. Il termometro e obbligatorio.""",
            "target": "Forma V del burro di cacao = snap, lucido, fonde a 34C, no bloom: curve 45-50 → 27-28 → 31-32C o seeding con cioccolato temperato, termometro obbligatorio",
            "nome": "Temperaggio del cioccolato",
            "dominio": "pasticceria",
        },
        "fen-crema-pasticcera": {
            "scheda": """La crema pasticcera e un esercizio di equilibrio tra due addensanti che lavorano a temperature diverse: l'amido e il tuorlo. Capire come si comportano e la differenza tra una crema liscia e lucida e una impazzita, granulosa o che sa di uovo crudo.

La crema pasticcera si addensa grazie a DUE meccanismi: l'AMIDO (farina o amido di mais) che gelatinizza (vedi il fenomeno) assorbendo il liquido e gonfiandosi, e le proteine del TUORLO che coagulano (vedi le uova). Lavorano a temperature diverse: il tuorlo coagula intorno ai 70-80C, l'amido gelatinizza e addensa fino quasi all'ebollizione.

Perche va portata a bollore (contro l'istinto)
A differenza di una crema inglese (solo tuorlo, mai bollire o straccia), la crema pasticcera VA portata al bollore per un minuto. Due ragioni: l'amido ha bisogno di quella temperatura per gelatinizzare del tutto (altrimenti resta liquida e sa di farina cruda); e l'amido PROTEGGE il tuorlo dalla coagulazione eccessiva (le molecole di amido si frappongono), per questo puoi bollirla senza che straccia - cosa impossibile per la crema inglese. Mescolare sempre, energicamente, per non far attaccare e bruciare sul fondo.

Gli errori
Grumi = amido non disperso bene all'inizio (va stemperato a freddo). Sapore di farina = non portata a bollore abbastanza. Sa di uovo = tuorlo cotto male. Si smonta in frigo = troppo poco amido.
Il bersaglio: amido gelatinizza (addensa, va portato a bollore) + tuorlo coagula (70-80C). L'amido protegge il tuorlo (per questo bolle senza stracciare, a differenza della crema inglese). Mescola sempre, stempera l'amido a freddo.""",
            "target": "Amido gelatinizza (addensa, va a bollore) + tuorlo coagula (70-80C): l'amido protegge il tuorlo (bolle senza stracciare), stempera l'amido a freddo mescola sempre",
            "nome": "Crema pasticcera",
            "dominio": "pasticceria",
        },
        "fen-montatura-panna": {
            "scheda": """Montare la panna e intrappolare aria in una rete di grasso. Sembra semplice, ma c'e una finestra precisa tra "montata perfetta" e "burro": pochi secondi di troppo e hai rovinato tutto. E il freddo e la condizione che rende tutto possibile.

La panna monta perche i suoi globuli di GRASSO, sbattuti, si urtano e si aggregano formando una rete che intrappola le bollicine d'aria (come un'impalcatura). Serve panna con almeno il 30-35% di grasso: sotto, non c'e abbastanza grasso per costruire la rete e non monta.

Il freddo e tutto
Panna, ciotola e fruste devono essere FREDDI (4C, meglio ciotola in freezer prima). Il motivo e fisico: il grasso deve essere solido per formare la rete. Se la panna si scalda, il grasso si ammorbidisce, i globuli non si agganciano e la panna non monta (o smonta). Il calore e il nemico numero uno.

La finestra: da panna a burro
Montando, si passa per stadi: schiuma → picco morbido (le punte si piegano) → picco fermo (le punte stanno dritte, il punto ideale per dolci) → e se continui, la rete collassa, il grasso si separa dall'acqua e ottieni BURRO (e latticello). E lo stesso processo del burro, solo fermato prima. Per questo montare a mano o a bassa velocita da piu controllo vicino al punto giusto.
Il bersaglio: grasso (min 30-35%) intrappola aria = panna montata. FREDDO obbligatorio (grasso solido, il calore la rovina). Fermati al picco fermo: un attimo oltre e diventa burro. Il burro e panna "troppo montata".""",
            "target": "Grasso (min 30-35%) intrappola aria = panna montata: FREDDO obbligatorio (il calore la rovina), fermati al picco fermo un attimo oltre e diventa burro",
            "nome": "Montatura della panna",
            "dominio": "pasticceria",
        },
        "fen-uova-coagulazione": {
            "scheda": """L'uovo e forse l'ingrediente piu versatile della cucina, e tutto quello che fa - rapprendersi, montare, legare, emulsionare - dipende da una cosa: le sue proteine che si aprono col calore e si legano tra loro. Governare la temperatura dell'uovo e governare decine di preparazioni. E la differenza tra uova cremose e uova gommose e questione di pochi gradi.

Quando scaldi un uovo, le proteine (arrotolate su se stesse) si DENATURANO - si srotolano - e poi si legano tra loro formando una rete solida: la COAGULAZIONE. Il punto chiave e che le diverse parti coagulano a temperature diverse:
- ALBUME: coagula a 62-65C
- TUORLO: coagula a 65-70C
- La chalaza (il filamento): 80C

Perche questo cambia tutto
Questa differenza di pochi gradi e ciò che ti da controllo. L'uovo fritto o alla coque: l'albume (62-65C) e gia solido mentre il tuorlo (65-70C) e ancora cremoso. Se cuoci di piu, anche il tuorlo si rapprende (sodo). E se vai troppo oltre, le proteine si stringono cosi tanto da espellere l'acqua: uovo GOMMOSO e asciutto (e l'errore delle uova strapazzate troppo cotte, o l'anello verde-grigio del sodo troppo bollito).

Le leve del cuoco
CALORE DOLCE per uova cremose: strapazzate a fuoco basso restano morbide (la rete intrappola l'acqua); a fuoco alto diventano gommose. AGGIUNTE che alzano la coagulazione: il latte o la panna diluiscono le proteine (coagulano piu tardi, piu morbide); anche sale e acido influiscono. E la carry-over: l'uovo continua a cuocere dopo il fuoco, si toglie un attimo prima.
Il bersaglio: albume 62-65C, tuorlo 65-70C (la differenza fa fritto/coque). Fuoco DOLCE = cremoso, troppo caldo = gommoso (le proteine espellono acqua). Latte/panna ammorbidiscono. Togli un attimo prima (carry-over).""",
            "target": "Albume 62-65C, tuorlo 65-70C (la differenza fa fritto/coque): fuoco DOLCE = cremoso, troppo caldo = gommoso (proteine espellono acqua), latte ammorbidisce",
            "nome": "Le uova (coagulazione delle proteine)",
            "dominio": "cucina",
        },
        "fen-verdure-verdi": {
            "scheda": """Perche i fagiolini o i broccoli, cotti male, diventano di quel verde militare smorto e tristo? E perche quelli del ristorante restano verde brillante? Non e fortuna: e chimica della clorofilla, e si governa con due gesti - sbollentare veloce e raffreddare in acqua e ghiaccio. Impari questo e le tue verdure verdi non saranno mai piu smorte.

Il verde delle verdure e la CLOROFILLA. Col calore prolungato e in ambiente acido, la clorofilla perde il suo atomo di magnesio e si trasforma in FEOFITINA, di colore verde-oliva smorto, "militare". E la ragione del verde triste delle verdure stracotte. Il nemico e il tempo di cottura lungo e l'acido.

La sbollentatura (blanching): il gesto che salva il colore
Sbollentare = tuffare le verdure in acqua bollente ABBONDANTE e salata per POCHI minuti, poi raffreddarle subito in acqua e ghiaccio (l'"shock termico"). Perche funziona:
- Acqua abbondante: le verdure non abbassano la temperatura, cuociono in fretta (meno tempo = meno feofitina).
- Il calore rapido inattiva gli enzimi che degraderebbero il colore, e fissa il verde brillante (paradossalmente all'inizio la cottura RAVVIVA il verde espellendo l'aria dai tessuti).
- Lo shock in acqua ghiacciata FERMA la cottura di colpo: le verdure restano croccanti e verdi, non passano nella zona feofitina.
Non coprire la pentola: gli acidi volatili delle verdure resterebbero intrappolati e vira il colore.
Il bersaglio: clorofilla → feofitina (verde smorto) col tempo e l'acido. Sbollenta veloce in acqua abbondante salata, poi SHOCK in acqua e ghiaccio (ferma la cottura, fissa il verde). Non coprire. Croccante e verde brillante.""",
            "target": "Clorofilla → feofitina (verde smorto) col tempo e l'acido: sbollenta veloce in acqua abbondante salata poi SHOCK in ghiaccio (ferma la cottura, fissa il verde), non coprire",
            "nome": "Le verdure verdi (clorofilla)",
            "dominio": "cucina",
        },
        "fen-pasta-acqua": {
            "scheda": """Cuocere la pasta sembra la cosa piu banale del mondo, e invece dentro c'e una fisica precisa: l'amido che gelatinizza dall'esterno verso l'interno, l'al dente che e un cuore ancora crudo, e quell'acqua torbida che butti via - e invece e l'ingrediente segreto della salsa. Chi capisce questo fa una pasta da ristorante.

Quando la pasta entra nell'acqua bollente, l'acqua penetra e l'amido superficiale GELATINIZZA (vedi il fenomeno): i granuli assorbono acqua, si gonfiano e si ammorbidiscono, dall'esterno verso il centro. Le proteine (glutine) coagulano e danno struttura.

L'al dente, spiegato
Al dente = l'amido esterno e gelatinizzato (morbido) ma il CUORE e ancora vetroso, appena crudo, con "il dente". Non e solo gusto: la pasta al dente ha indice glicemico piu basso (l'amido meno gelatinizzato si digerisce piu lentamente) e regge meglio la mantecatura. Scotta = amido tutto gelatinizzato = molla e collosa. La pasta continua a cuocere dopo lo scolo (e nella salsa): scola un filo prima.

L'acqua di cottura: l'emulsionante nascosto
Durante la cottura, l'amido esce dalla pasta e si scioglie nell'acqua (per questo diventa torbida). Quell'acqua amidacea e un EMULSIONANTE: aggiunta alla salsa in padella, lega il grasso (olio, burro) con la parte acquosa e fa AGGRAPPARE la salsa alla pasta invece di scivolare sul piatto. E il segreto della mantecatura: aglio e olio, cacio e pepe, carbonara - tutte vivono di questo. Il sale nell'acqua (1-2%, "come il mare") insaporisce la pasta DENTRO, non solo in superficie.
Il bersaglio: amido gelatinizza da fuori a dentro, al dente = cuore vetroso (regge la mantecatura, IG piu basso). L'acqua amidacea EMULSIONA la salsa (mantecatura): tienila. Sale 1-2%, scola un filo prima.""",
            "target": "Amido gelatinizza da fuori a dentro, al dente = cuore vetroso (regge mantecatura, IG piu basso): l'acqua amidacea EMULSIONA la salsa (tienila!), sale 1-2%",
            "nome": "La pasta e l'acqua di cottura",
            "dominio": "cucina",
        },
        "fen-soffritto": {
            "scheda": """Quasi ogni piatto salato della tradizione parte da la stessa cosa: verdure tritate fatte appassire piano nel grasso. Soffritto in Italia, mirepoix in Francia, sofrito in Spagna - lo stesso principio ovunque. Non e un passaggio da sbrigare: e la fondazione aromatica su cui si costruisce tutto il piatto. Farlo bene o male decide il sapore finale.

Il soffritto (cipolla, carota, sedano tritati, in olio o burro a fuoco dolce) fa una cosa precisa: estrae e trasforma gli aromi delle verdure nel grasso, che li trattiene e li distribuisce. A fuoco DOLCE e lento le verdure APPASSISCONO (perdono acqua, concentrano i sapori, la cipolla diventa dolce) senza bruciare.

La chimica del soffritto
Due processi. Primo, la disidratazione dolce: l'acqua esce, i sapori si concentrano, gli zuccheri della cipolla emergono (diventa dolce e trasparente). Secondo, a temperature un po' piu alte, parte la Maillard (vedi il fenomeno) sulle verdure: le note brune, profonde, "tostate". Il grasso e fondamentale: e liposolubile, cattura gli aromi che l'acqua non prenderebbe, e li porta in tutto il piatto.

Fuoco dolce, l'errore comune
L'errore e il fuoco troppo alto: la cipolla brucia fuori restando cruda dentro, e il bruciato ammarisce tutto. Il soffritto vuole pazienza: fuoco dolce, tempo, finche le verdure sono morbide e dorate. E la base di soffritti, ragu, sughi, brasati, zuppe.
Il bersaglio: verdure appassite piano nel grasso = base aromatica. Fuoco DOLCE (bruciato ammarisce), il grasso cattura e distribuisce gli aromi liposolubili. Appassire concentra + Maillard approfondisce. La fondazione del piatto.""",
            "target": "Verdure appassite piano nel grasso = base aromatica: fuoco DOLCE (bruciato ammarisce), il grasso cattura e distribuisce gli aromi liposolubili - la fondazione del piatto",
            "nome": "Il soffritto (base aromatica)",
            "dominio": "cucina",
        },
        "fen-riposo-carne": {
            "scheda": """Tagli una bistecca appena tolta dal fuoco e il tagliere si allaga di succhi: la carne dentro sara asciutta. Aspetti cinque minuti prima di tagliarla e resta succosa. Non e magia ne pazienza fine a se stessa: e fisica dei liquidi dentro il muscolo, e vale per ogni pezzo di carne che cuoci.

Durante la cottura, il calore fa contrarre le fibre muscolari e spinge i succhi verso il centro (piu freddo) della carne. Le fibre sono strizzate, tese, e i liquidi sono in pressione al centro. Se tagli subito, quei succhi in pressione escono tutti (il tagliere si allaga) e la carne resta secca.

Cosa succede nel riposo
Lasciando riposare la carne fuori dal fuoco, due cose: la temperatura si uniforma (il centro cede calore verso l'esterno che si raffredda), le fibre si RILASSANO e i succhi si RIDISTRIBUISCONO uniformemente, riassorbiti nei tessuti. Ora, tagliando, i succhi restano nella carne invece di colare via.

Quanto riposo
Regola pratica: piu grosso il pezzo, piu lungo il riposo. Una bistecca 5 minuti, un arrosto 15-20, un grande pezzo anche di piu. Si copre lascamente con alluminio per non perdere troppo calore. Vale per la carne cotta a calore alto (bistecche, arrosti): dove le fibre si sono contratte c'e da rilassarle.
Il bersaglio: riposo = fibre si rilassano e i succhi si ridistribuiscono (non colano via al taglio). Piu grosso il pezzo piu lungo (bistecca 5min, arrosto 15-20). Copri lasco. La differenza tra carne succosa e asciutta.""",
            "target": "Riposo = fibre si rilassano e i succhi si ridistribuiscono (non colano al taglio): piu grosso piu lungo (bistecca 5min, arrosto 15-20) - succosa vs asciutta",
            "nome": "Il riposo della carne",
            "dominio": "cucina",
        },
        "fen-collagene-brasato": {
            "scheda": """C'e un motivo per cui la bistecca si cuoce in tre minuti e il brasato in tre ore - e non e la dimensione. Sono due tipi di carne opposti, governati da due proteine diverse: la bistecca dalle fibre muscolari, il brasato dal collagene. Capire questa differenza e la cosa piu importante della cottura della carne. Sbagliarla vuol dire una bistecca stopposa o un brasato duro.

Nella carne ci sono due strutture che il calore tratta in modo OPPOSTO:
- FIBRE MUSCOLARI (actina, miosina): nei tagli teneri e magri (bistecca, filetto, lombata). Cuociono in fretta ad alta temperatura. Piu le cuoci, piu si contraggono e diventano dure e secche. Vanno cotte POCO (al sangue/media), tolte al punto giusto.
- COLLAGENE (tessuto connettivo): nei tagli duri e lavorati (spalla, guancia, muscolo, brisket, ossobuco). E una proteina a tripla elica, dura e gommosa da cruda. Ma con calore + umidita + TEMPO si scioglie in GELATINA, che rende la carne succosa e fondente.

Le temperature e il paradosso
Il collagene inizia a sciogliersi verso i 60C, ma la conversione vera avviene tra 70-90C sostenuti per 2-6 ore. Attenzione allo stadio di mezzo: intorno ai 60C le fibre si contraggono ed espellono acqua - la carne sembra piu SECCA e dura proprio a meta cottura. E lo scoglio del brasato: bisogna INSISTERE oltre, e il collagene che si scioglie ripaga.

I due tipi di succosita
Una bistecca e succosa perche trattiene i suoi succhi (cotta poco). Un brasato e succoso perche la gelatina disciolta (che trattiene 3 volte il suo peso in acqua) lo rende fondente, anche se le fibre hanno perso i loro liquidi. Due succosita diverse. Per questo NON puoi fare un brasato "al sangue" (il collagene non si e sciolto = duro) ne una bistecca "brasata" (poco collagene, la cuoci a morte per niente).
Il bersaglio: taglio tenero (fibre) = poco e caldo. Taglio duro (collagene) = tanto tempo a 70-90C con umidita → gelatina. Sceglere la cottura DAL taglio. Il brasato passa da uno stadio secco intermedio: insisti.""",
            "target": "Taglio tenero poco e caldo, taglio duro (collagene) tanto tempo a 70-90C con umidita = gelatina - scegli la cottura dal taglio, il brasato passa da uno stadio secco: insisti",
            "nome": "Collagene e brasato (i due tipi di carne)",
            "dominio": "cucina",
        },
        "fen-rosolatura": {
            "scheda": """La crosta bruna e saporita di una bistecca scottata bene non e "bruciatura" ne caramellizzazione: e la reazione di Maillard, la stessa della crosta del pane. E non "sigilla i succhi" come si diceva una volta - quella e una leggenda. Serve a una cosa sola, ma fondamentale: creare sapore.

La rosolatura e Maillard (vedi il fenomeno) applicata alla superficie della carne: ad alta temperatura (sopra i 140C, meglio 160-200C sulla padella), zuccheri e amminoacidi reagiscono e creano centinaia di composti aromatici bruni - il sapore "di arrosto". E l'applicazione in cucina della stessa reazione che dora pane, caffe, birra.

Le condizioni che contano
SUPERFICIE ASCIUTTA: l'acqua in superficie deve prima evaporare (a 100C) prima che parta la Maillard (140C+). Carne bagnata = si lessa invece di rosolare, niente crosta. Va asciugata bene prima. PADELLA CALDA e non affollata: troppa carne insieme abbassa la temperatura e fa uscire acqua = bollore, non rosolatura. GRASSO adatto: con punto di fumo alto (vedi il fenomeno), o brucia.

La leggenda sfatata
Rosolare NON "sigilla i succhi dentro": la crosta non e impermeabile, la carne scottata perde succhi come e piu di quella non scottata. Si rosola per il SAPORE (la crosta Maillard + il fond in padella per le salse), non per la succosita. Prima o dopo la cottura lenta, la rosolatura e sempre una questione di gusto, non di tenuta.
Il bersaglio: rosolatura = Maillard sulla superficie (sopra 140C) = sapore, NON sigillo. Carne asciutta, padella calda, non affollata, grasso adatto. E la stessa reazione della crosta del pane.""",
            "target": "Rosolatura = Maillard sulla superficie (sopra 140C) = SAPORE non sigillo: carne asciutta padella calda non affollata - stessa reazione della crosta del pane",
            "nome": "La rosolatura (searing)",
            "dominio": "cucina",
        },
        "fen-emulsione-salse": {
            "scheda": """Maionese, olandese, vinaigrette: sono tutte la stessa magia fisica - due liquidi che si odiano, olio e acqua, costretti a stare insieme in una crema stabile. Il segreto e un terzo ingrediente, l'emulsionante, e un gesto: aggiungere l'olio LENTAMENTE. Capirlo vuol dire non "impazzire" mai piu una salsa.

Olio e acqua non si mescolano: l'olio in gocce tende a riunirsi e separarsi. Un'emulsione e olio disperso in minuscole goccioline dentro l'acqua (o viceversa), tenute separate da un EMULSIONANTE - una molecola che ha una parte che ama l'acqua e una che ama il grasso, e fa da ponte. Nella maionese l'emulsionante e la LECITINA del tuorlo d'uovo; nell'olandese sempre il tuorlo; nella vinaigrette la senape.

Perche l'olio va aggiunto piano
All'inizio serve creare l'emulsione: poche gocce d'olio alla volta, sbattendo, cosi ogni goccia viene circondata dall'emulsionante prima che arrivi la successiva. Se versi troppo olio insieme, l'emulsionante non basta a rivestirlo tutto, le gocce si riuniscono e la salsa "impazzisce" (si separa in olio e grumi). Piu emulsionante = piu olio che puoi reggere.

Come si salva una salsa impazzita
Non buttarla: ricominci con un nuovo tuorlo (o un cucchiaio d'acqua calda per l'olandese) in una ciotola pulita, e ci versi DENTRO la salsa impazzita lentamente, come fosse l'olio. Il nuovo emulsionante ricostruisce l'emulsione.
Il bersaglio: emulsione = olio in gocce nell'acqua, tenute dall'emulsionante (lecitina del tuorlo, senape). Olio LENTO all'inizio (l'emulsionante deve rivestire ogni goccia). Impazzita = troppo olio troppo in fretta, si salva ripartendo da nuovo emulsionante.""",
            "target": "Emulsione = olio in gocce tenute dall'emulsionante (lecitina tuorlo, senape): olio LENTO all'inizio, impazzita = troppo olio troppo in fretta, si salva da nuovo emulsionante",
            "nome": "Emulsione delle salse (maionese, olandese)",
            "dominio": "cucina",
        },
        "fen-chiarificazione-latte": {
            "scheda": """Prendi un cocktail torbido, lo "rovini" versandolo nel latte finche caglia, lo filtri — e ottieni un liquido limpido come acqua ma piu morbido e rotondo di prima. Sembra magia, e invece e la stessa fisica della ricotta: le proteine del latte che coagulano con l'acido, e cagliando si portano via amaro e torbidita.

Il milk punch e un trucco del Seicento (Benjamin Franklin ne aveva una ricetta) tornato di moda per la texture e la limpidezza. La fisica: la caseina del latte, a pH normale (6.6), e carica e le sue micelle si respingono, restando disperse (il latte e opaco). Aggiungi un cocktail ACIDO e il pH scende: a 4.6 la caseina si neutralizza e COAGULA in cagliata (la stessa soglia del botulino, la stessa reazione della ricotta).

Perche chiarifica E ammorbidisce
La cagliata che si forma ha una superficie enorme e una leggera carica: cattura e intrappola le particelle sospese - pigmenti, torbidita, e soprattutto TANNINI e polifenoli (l'amaro e l'astringenza). Filtrando via la cagliata, porti via anche tutto quello che ha catturato. Per questo il drink chiarificato non e solo limpido: e piu morbido, meno astringente, setoso (restano gli zuccheri del latte e le proteine del siero). I tannini invece di legarsi alla tua saliva (astringenza) si sono legati alla caseina e sono spariti.

Il metodo (i punti che contano)
Si versa il COCKTAIL NEL LATTE (non il latte nel cocktail: l'ordine conta per una cagliata pulita), rapporto ~5:1. Latte intero a temperatura ambiente (piu grasso caglia meglio). Serve un ingrediente acido o astringente nel drink, o non caglia. Riposo, poi filtraggio lento (garza o filtro da caffe) senza premere la cagliata (premere intorbidisce). Si assaggia PRIMA di chiarificare: dopo non si aggiusta piu.
Il bersaglio: acido abbassa il pH a 4.6, la caseina caglia, la cagliata intrappola tannini e torbidita, filtri = drink limpido e morbido. Cocktail nel latte 5:1, latte intero, non premere. Stessa fisica di ricotta e botulino.""",
            "target": "Acido abbassa pH a 4.6, la caseina caglia, la cagliata intrappola tannini e torbidita, filtri = drink limpido e morbido - cocktail nel latte 5:1, non premere",
            "nome": "La chiarificazione al latte",
            "dominio": "bar",
        },
        "fen-infusioni": {
            "scheda": """Mettere qualcosa a bagno in un distillato per prenderne aroma e sapore e la base di ogni gin, ogni amaro, ogni vermouth - e di infinite creazioni da bar. Ma il tempo, la temperatura e l'alcol cambiano tutto: la stessa spezia in infusione dieci minuti o dieci ore da due liquidi diversi. Governare l'estrazione e governare il sapore.

L'infusione estrae composti aromatici da un ingrediente (spezie, erbe, frutta, te) in un liquido. Nel bar il solvente e l'alcol, che estrae bene i composti sia solubili in acqua sia in grasso/olio (piu versatile dell'acqua da sola). Tre leve governano l'estrazione:

Tempo: piu a lungo, piu estrai - ma non linearmente. Gli aromi delicati e volatili escono presto; i tannini amari e le note astringenti escono TARDI. Per questo un te lasciato troppo in infusione diventa amaro, e certe botaniche vanno tolte presto. C'e una finestra dolce, poi peggiora.
Temperatura: il caldo accelera l'estrazione (piu veloce) ma puo estrarre note sgradevoli e far evaporare gli aromi piu volatili. L'infusione a freddo e piu lenta ma piu pulita e delicata. Caldo per rapidita e corpo, freddo per finezza.
Superficie: piu l'ingrediente e spezzettato, piu superficie, piu veloce l'estrazione (come per il caffe e la macinatura).

Il fat-wash e un'infusione al contrario
Nel fat-wash (gia nel grafo) si infonde un grasso (burro, olio, bacon) nell'alcol, poi si congela e filtra: l'alcol prende l'aroma del grasso ma non l'unto. E una macerazione che sfrutta il freddo per separare.
Il bersaglio: alcol estrae aromi (acqua+grasso solubili). Tempo (aromi presto, amaro tardi: finestra dolce), temperatura (caldo veloce/freddo pulito), superficie (spezzettato=veloce). Assaggia e ferma al punto giusto.""",
            "target": "Alcol estrae aromi: tempo (aromi presto amaro tardi, finestra dolce), temperatura (caldo veloce/freddo pulito), superficie (spezzettato veloce) - assaggia e ferma",
            "nome": "Infusioni e macerazioni",
            "dominio": "bar",
        },
        "fen-amaro-bitter": {
            "scheda": """I bitter sono il "sale del bar": poche gocce non rendono un drink amaro, lo mettono a fuoco. Angostura in un Old Fashioned, Peychaud's in un Sazerac - sono dosi minuscole che legano gli aromi e aggiungono profondita. Capire il ruolo dell'amaro e capire perche un drink senza bitter spesso sa di "piatto".

L'amaro e uno dei gusti fondamentali, e nel bar ha un ruolo speciale: la percezione. A basse dosi l'amaro non domina - ARMONIZZA. Come il sale in cucina non rende salato ma esalta, poche gocce di bitter legano gli altri sapori e danno complessita e "lunghezza" al drink.

Bitter concentrati vs amari da bere
Due famiglie diverse. I BITTER (Angostura, Peychaud's, orange): concentratissimi, si usano a gocce/dash, aromatizzano. Sono infusi di erbe, radici, cortecce amare in alcol ad alta gradazione. Gli AMARI (Campari, Fernet, Averna): si bevono, come base o modificatori, con la loro dose di zucchero e la loro gradazione. Stessa radice (erbe amare in infusione) ma uso opposto: goccia vs bicchiere.

Perche l'amaro "sveglia" il drink
L'amaro bilancia il dolce e il forte (torna l'equilibrio dolce/acido/forte/amaro): un drink solo dolce-forte e stucchevole e piatto; l'amaro taglia, aggiunge una dimensione, e prolunga il finale. E anche il motivo per cui gli amari funzionano come digestivi (stimolano la salivazione e i succhi gastrici).
Il bersaglio: bitter a gocce = mette a fuoco non rende amaro (il "sale del bar"). Bitter concentrati (dash) vs amari da bere (bicchiere), stessa radice uso opposto. L'amaro e la 4a forza dell'equilibrio: taglia il dolce, da profondita e lunghezza.""",
            "target": "Bitter a gocce mette a fuoco non rende amaro (il sale del bar): concentrati (dash) vs amari da bere (bicchiere) - l'amaro e la 4a forza dell'equilibrio",
            "nome": "L'amaro e i bitter",
            "dominio": "bar",
        },
        "fen-ghiaccio": {
            "scheda": """Il ghiaccio fa due lavori insieme, e sono in conflitto: raffredda il drink e lo diluisce. Il barman non "mette il ghiaccio" — sceglie QUALE ghiaccio per decidere quanto raffreddare e quanto diluire. E la stessa forza, il rapporto superficie/volume, governa entrambi.

Piu superficie di ghiaccio a contatto col liquido = raffreddamento piu veloce MA anche diluizione piu veloce. Da qui la scelta:
- CUBO GRANDE (o sfera): poca superficie. Raffredda lentamente, diluisce poco. Per drink spirit-forward serviti sul ghiaccio (Old Fashioned, Negroni) dove vuoi tenere la forza a lungo senza annacquare. Nota: la sfera e piu estetica che funzionale.
- CUBO 1 POLLICE: il tuttofare. Diluizione misurata ed equilibrata. Per shakerare e per i sour on the rocks.
- TRITATO/CRUSHED: massima superficie. Raffredda e diluisce in fretta. Per tiki, Mojito, Julep, drink dissetanti da bere subito, dove la diluizione veloce ammorbidisce l'alcol.

Il dato controintuitivo
Dopo circa 5 minuti, tutti i formati arrivano a temperatura e diluizione finali quasi identiche: la dimensione governa la VELOCITA, non il punto d'arrivo. Quindi il ghiaccio grande conta finche il drink e "giovane" - per i primi minuti. Ecco perche e giusto per i drink che sorseggi a lungo.

Il ghiaccio limpido
Il ghiaccio trasparente (senza aria intrappolata) e piu denso e si scioglie in modo uniforme e prevedibile; quello opaco ha difetti interni che lo fanno frammentare e sciogliere in modo erratico. Per questo il ghiaccio "buono" e limpido: diluizione controllata.
Il bersaglio: superficie/volume governa raffreddamento E diluizione insieme. Grande=lento e poco diluito (spirit-forward), tritato=veloce e diluito (dissetanti). La dimensione governa la velocita non il punto finale. Ghiaccio limpido = diluizione prevedibile.""",
            "target": "Superficie/volume governa raffreddamento E diluizione: grande=lento poco diluito (spirit-forward), tritato=veloce diluito (dissetanti) - la dimensione governa la velocita non il punto finale",
            "nome": "Il ghiaccio (raffreddamento e diluizione)",
            "dominio": "bar",
        },
        "fen-carbonatazione": {
            "scheda": """Le bollicine di un highball non sono solo estetica: la CO2 disciolta porta acidita (l'acido carbonico), pizzica la lingua, e cambia la percezione del drink rendendolo piu secco e vivo. Ma la CO2 e volubile - vuole scappare. Trattenerla e una questione di fisica: freddo, pressione, e superfici lisce.

La CO2 si scioglie nel liquido e crea l'effervescenza. Le regole per trattenerla, tutte fisiche:
FREDDO: il liquido freddo assorbe e trattiene MOLTA piu CO2. Vicino a 0C e l'ideale. Un mixer caldo perde le bollicine subito. E la ragione per cui gli highball si fanno con mixer freddissimo.
PRESSIONE: piu pressione = piu CO2 disciolta (e il principio della carbonatazione forzata: CO2 sotto pressione in liquido freddo). Nelle bottiglie di soda la pressione tiene dentro il gas fino all'apertura.

Cosa fa scappare le bollicine: la nucleazione
La CO2 esce dove trova "appigli" (siti di nucleazione): superfici ruvide, spigoli, impurita. Per questo:
- Il ghiaccio LISCIO e con poca superficie (cubi grandi, non tritato) fa perdere meno bollicine. Il ghiaccio tritato, pieno di spigoli, sgasa il drink.
- Il bicchiere ALTO E STRETTO (highball) espone poca superficie all'aria: la CO2 scappa piu lenta. Un bicchiere largo e basso fa smontare il drink in fretta.
- Versare inclinando il bicchiere (come la birra alla spina) riduce la perdita di gas.
Acidita e zucchero riducono LEGGERMENTE la CO2 assorbibile (effetto piccolo).
Il bersaglio: CO2 = acidita + pizzicore + secchezza. Trattienila con FREDDO (vicino a 0C), pressione, e superfici lisce (ghiaccio grande, bicchiere alto e stretto). Il tritato e il bicchiere largo la fanno scappare.""",
            "target": "CO2 = acidita + pizzicore + secchezza: trattienila con freddo (vicino 0C), pressione, superfici lisce (ghiaccio grande, bicchiere alto stretto) - tritato e bicchiere largo la fanno scappare",
            "nome": "La carbonatazione (bollicine nel drink)",
            "dominio": "bar",
        },
        "fen-equilibrio-cocktail": {
            "scheda": """Ogni cocktail che funziona e un equilibrio tra quattro forze: dolce, acido, forte, amaro. Non e una questione di gusto personale: e una struttura. Quando un drink "non torna", quasi sempre e uno di questi quattro fuori posto. Capire l'equilibrio e la prima cosa che separa chi mescola ingredienti da chi costruisce un drink.

Il cuore del bar e il triangolo dolce-acido-forte, con l'amaro come quarto giocatore. Ogni famiglia di cocktail e un modo di bilanciare queste forze:
- SOUR (Daiquiri, Whiskey Sour, Margarita): 2 parti distillato, 1 acido (agrume), 1 dolce (sciroppo). L'acido taglia il dolce, il dolce ammorbidisce l'alcol, il distillato regge tutto. E la struttura piu usata al mondo.
- SPIRIT-FORWARD (Old Fashioned, Negroni, Manhattan): dominati dal distillato, con poco dolce e l'amaro a dare profondita. Old Fashioned: 5 parti distillato, 1 dolce, bitter. Niente acido: qui l'equilibrio e tra forza e amaro.

Le leve dell'equilibrio
DOLCE (zucchero, sciroppi, liquori): ammorbidisce, arrotonda, nasconde l'alcol. ACIDO (limone, lime): da freschezza e taglia il dolce; senza, il drink e piatto e stucchevole; troppo, e aspro. FORTE (il distillato): la spina dorsale. AMARO (bitter, amari): profondita e complessita, il quarto che "sveglia" il drink.

La temperatura cambia tutto
Un drink bilanciato a temperatura ambiente puo essere sbagliato da freddo: il freddo ABBASSA la percezione del dolce. Per questo un cocktail va assaggiato e bilanciato ALLA temperatura di servizio (freddo), non prima. Un sour che sa giusto tiepido sara troppo aspro ghiacciato.
Il bersaglio: dolce/acido/forte/amaro in equilibrio. Il sour (2:1:1) e la struttura madre. Bilancia SEMPRE a freddo. Se un drink non torna, cerca quale delle 4 forze e fuori.""",
            "target": "Dolce/acido/forte/amaro in equilibrio: il sour 2:1:1 e la struttura madre, bilancia SEMPRE a freddo (il freddo abbassa il dolce) - se non torna cerca quale forza e fuori",
            "nome": "L'equilibrio del cocktail",
            "dominio": "bar",
        },
        "fen-shakerare-mescolare": {
            "scheda": """Shakerare o mescolare non e una scelta di stile (ne una battuta di James Bond): e una decisione tecnica precisa, e dipende da una sola cosa — cosa c'e nel bicchiere. La regola copre il 90% dei drink: se e opaco si shakera, se e limpido si mescola. E capire il perche ti fa sbagliare molto meno.

Shakerare e mescolare sono due modi diversi di trasferire energia, con effetti misurabili diversi su temperatura, diluizione, aerazione e testura.

SHAKERARE (drink opachi: agrumi, albume, panna)
Agitazione violenta con ghiaccio per 10-15 secondi. Fa tre cose insieme: raffredda in fretta, diluisce (aggiunge acqua), e incorpora aria (bollicine → testura piu leggera e schiumosa). Serve quando ci sono ingredienti che DEVONO amalgamarsi: gli agrumi sono opachi e densi, l'albume va denaturato. Senza shakerata, un sour oscilla tra troppo aspro e troppo dolce, con l'agrume mai integrato. Daiquiri, Margarita, Whiskey Sour: sempre shakerati.

MESCOLARE (drink limpidi: solo distillati e liquori)
Agitazione gentile col bar spoon per 20-30 secondi. Raffredda e diluisce lentamente, SENZA aerazione: mantiene il drink limpido e setoso. Serve per i drink spirit-forward, dove conta preservare la chiarezza e le note delicate del distillato. Lo shakerare li rovinerebbe (aerazione e diluizione eccessiva ossidano i terpeni delicati). Martini, Manhattan, Negrironi, Sazerac: sempre mescolati.
Il bersaglio: opaco (agrumi/albume/panna) → shakera 10-15s. Limpido (solo distillati) → mescola 20-30s. La regola copre il 90% dei drink. Non e stile, e cosa c'e nel bicchiere.""",
            "target": "Opaco (agrumi/albume/panna) shakera 10-15s, limpido (solo distillati) mescola 20-30s: la regola copre il 90% dei drink - non e stile, e cosa c'e nel bicchiere",
            "nome": "Shakerare vs mescolare",
            "dominio": "bar",
        },
        "fen-emulsione-bar": {
            "scheda": """La schiuma vellutata sopra un Whiskey Sour non e decorazione: e fisica. L'albume, shakerato con forza, si denatura e forma una rete che intrappola l'aria — la stessa cosa che succede montando gli albumi, ma nel bicchiere. Capire come si forma (e come stabilizzarla) e la differenza tra una schiuma fitta e cremosa e una che collassa in dieci secondi.

L'albume nei sour (Whiskey Sour, Clover Club, Pisco Sour) crea testura tramite due meccanismi: le proteine dell'albume, agitate, si DENATURANO (si srotolano) e formano un reticolo che intrappola bollicine d'aria — una schiuma stabile. E le stesse proteine funzionano da emulsionanti, legando componenti che altrimenti si separerebbero.

Il dry shake: il trucco che raddoppia la schiuma
La tecnica chiave: prima si shakera SENZA ghiaccio (dry shake) per 10-15 secondi, poi si aggiunge il ghiaccio e si shakera di nuovo. Perche? Senza il freddo del ghiaccio, le proteine si denaturano meglio e piu a fondo (il freddo le irrigidisce troppo presto): il dry shake pre-monta la schiuma, poi la seconda shakerata raffredda e diluisce. Salti il dry shake e ottieni una schiuma grossolana che collassa in pochi secondi.

Cosa disturba la schiuma
Agrumi troppo spremuti o con polpa introducono pectina e detriti che destabilizzano. Distillati molto invecchiati (tannini, esteri polimerizzati) sopprimono la schiuma. Distillati giovani (blanco, rum bianco) la favoriscono (piu congeneri che fanno da tensioattivi). Alternativa vegana all'albume: l'aquafaba (l'acqua dei ceci), stesse proteine-tensioattivo.
Il bersaglio: albume = denaturazione + emulsione → schiuma. Dry shake SEMPRE (raddoppia la schiuma: senza ghiaccio prima, poi col ghiaccio). Agrumi puliti, distillati giovani = schiuma migliore. Aquafaba come alternativa vegana.""",
            "target": "Albume shakerato = denaturazione + emulsione = schiuma: dry shake SEMPRE (raddoppia la schiuma, senza ghiaccio prima poi col ghiaccio) - aquafaba alternativa vegana",
            "nome": "Emulsione e texture (albume, schiuma)",
            "dominio": "bar",
        },
        "fen-anisakis": {
            "scheda": """Il pesce crudo puo contenere l'Anisakis, un parassita che vive nelle viscere e nei tessuti di molti pesci. Servire pesce crudo senza abbatterlo non e una scelta di stile: e vietato dalla legge, e per una buona ragione. L'abbattimento e la sola difesa, e ha numeri precisi da rispettare.

L'Anisakis e un parassita (un nematode) presente in molti pesci, soprattutto il pesce azzurro (sardine, alici, sgombri, aringhe) e altri. Se ingerito vivo puo causare dolori addominali gravi, reazioni allergiche, in certi casi serve un intervento. Non lo elimini a occhio: l'esame visivo NON basta.

L'abbattimento: la legge e i numeri
Dal 1992 in Italia, e dal 2004 in tutta Europa (Reg. CE 853/2004), chi serve pesce crudo o marinato DEVE abbatterlo. I numeri: -20C AL CUORE del prodotto per almeno 24 ore. Attenzione al dettaglio che molti sbagliano: le 24 ore partono da quando il CUORE del pesce raggiunge i -20C, non da quando lo metti dentro. Con un abbattitore che porta a -35C, bastano tempi piu brevi.
A CASA (Ministero Salute, decreto 2013): congelatore a tre stelle o piu, -18C per almeno 96 ore.

Cosa NON fa l'abbattimento
Elimina i PARASSITI (Anisakis), NON i batteri. I batteri col freddo vengono solo "bloccati", ripartono allo scongelamento. E la marinatura (limone, aceto) NON uccide l'Anisakis: e una falsa credenza pericolosa. Solo il freddo giusto o la cottura (>=60C al cuore per un minuto) lo uccidono.
Il bersaglio: pesce crudo = abbattuto per legge, -20C al cuore per 24h (o -18C 96h a casa). L'abbattimento uccide i parassiti non i batteri. La marinatura non basta. Numeri precisi, non impressioni.""",
            "target": "Pesce crudo = abbattuto per LEGGE: -20C al cuore per 24h (o -18C 96h a casa) - uccide i parassiti non i batteri, la marinatura non basta",
            "nome": "Anisakis e abbattimento del pesce",
            "dominio": "tecnologie",
        },
        "fen-ustioni-olio": {
            "scheda": """L'olio di frittura a 170-180C e il pericolo piu comune e piu sottovalutato di una cucina. Non e come l'acqua bollente: e piu caldo, si attacca alla pelle, e se prende fuoco l'acqua lo fa esplodere. Chi frigge deve conoscere queste tre cose prima ancora della ricetta.

L'olio caldo ustiona piu gravemente dell'acqua: e a temperatura piu alta (180C contro 100C) e, essendo oleoso, aderisce alla pelle continuando a bruciare invece di scivolare via. Le tre regole di sicurezza:

Uno: mai acqua nell'olio caldo. L'acqua a contatto con l'olio bollente evapora di colpo ed espelle olio rovente in tutte le direzioni (schizzi ustionanti). Gli alimenti bagnati vanno asciugati prima di immergerli. Un cibo gocciolante d'acqua in padella e schizzi garantiti.

Due: l'incendio da olio NON si spegne con l'acqua. Se l'olio prende fuoco (supera il punto di fumo e poi di infiammabilita), gettarci acqua e la cosa peggiore: l'acqua vaporizza istantaneamente e proietta l'olio in fiamme ovunque, allargando l'incendio. Si soffoca: coperchio, o un panno bagnato strizzato steso sopra, o estintore. Mai acqua.

Tre: la temperatura sotto controllo. Olio troppo caldo (oltre il punto di fumo, che varia per ogni olio) degrada, fuma, sviluppa composti sgradevoli e si avvicina all'infiammabilita. Serve un termometro o l'esperienza. La frittura sicura sta nella finestra 170-180C, ben sotto il punto di fumo di un olio adatto.
Il bersaglio: olio 170-180C, cibi asciutti (mai acqua), incendio si soffoca mai si annacqua, temperatura sotto il punto di fumo. Il pericolo si governa con tre regole, prima della ricetta.""",
            "target": "Olio 170-180C piu pericoloso dell'acqua: cibi asciutti (mai acqua), incendio si SOFFOCA mai annacqua, temperatura sotto il punto di fumo",
            "nome": "Ustioni e sicurezza dell'olio",
            "dominio": "tecnologie",
        },
        "fen-haccp": {
            "scheda": """HACCP non e burocrazia: e un modo di pensare la sicurezza. Nato negli anni '60 dalla Pillsbury per garantire cibo sicuro agli astronauti della NASA, oggi e obbligatorio ovunque si lavori il cibo. L'idea e semplice: invece di controllare il prodotto finito, controlli i PUNTI del processo dove puo nascere il pericolo.

HACCP (Hazard Analysis and Critical Control Points) si regge su un'intuizione: i pericoli non vanno scoperti alla fine, vanno prevenuti dove nascono. Tre famiglie di pericolo: biologici (batteri come Salmonella, Listeria; parassiti come Anisakis; muffe), chimici (detergenti, allergeni non dichiarati, metalli pesanti), fisici (vetro, plastica, frammenti).

I CCP (Punti Critici di Controllo)
Il cuore del metodo. Un CCP e una fase dove PUOI prevenire o eliminare un pericolo, e dove nessuna fase successiva lo correggera. Esempi: la cottura (uccide i patogeni), il raffreddamento rapido (evita la proliferazione), il controllo del pH nei sottoli (blocca il botulino). Non tutte le fasi sono CCP: solo quelle dove il controllo e indispensabile.

I limiti critici: MISURABILI
Qui sta la disciplina mentale che vale per tutto Matter. "La carne deve essere ben cotta" NON e un limite valido. "Temperatura al cuore >= 75C" lo e. Un limite critico e un numero che separa il sicuro dal pericoloso: temperatura, tempo, pH, Aw. Misurabile, verificabile, basato sulla scienza.
Il bersaglio: pensare la sicurezza come punti misurabili nel processo, non come impressione sul prodotto finito. Cosa monitoro, come, quando, chi.""",
            "target": "Prevenire i pericoli dove nascono, non controllarli alla fine: i CCP sono le fasi dove elimini un pericolo, con limiti MISURABILI (T>=75C, pH<4.6) non impressioni",
            "nome": "HACCP (il metodo della sicurezza)",
            "dominio": "tecnologie",
        },
        "fen-attivita-acqua": {
            "scheda": """I batteri non hanno bisogno di "acqua" in generale: hanno bisogno di acqua LIBERA, quella che possono usare. E per questo un prosciutto stagionato, il miele o la marmellata durano mesi fuori dal frigo mentre la carne fresca marcisce in giorni. Non e quanta acqua c'e: e quanta ne e disponibile. Si misura, e si chiama attivita dell'acqua, Aw.

L'Aw va da 0 a 1 (acqua pura = 1). Misura l'acqua LIBERA, non legata a sale, zucchero o strutture. I microrganismi hanno bisogno di un'Aw minima per crescere: sotto certe soglie, semplicemente non possono. Batteri patogeni: sotto Aw 0.85 non proliferano (per questo la legge usa questa soglia). Muffe e lieviti resistono piu in basso (fino a ~0.6).

Come si abbassa l'Aw (e si conserva)
Tre modi antichi, stessa fisica: TOGLIERE acqua (essiccazione: carasau, bresaola, frutta secca), LEGARE l'acqua col sale (salumi, baccala, acciughe sotto sale), LEGARE l'acqua con lo zucchero (marmellata, miele, canditi). In tutti, l'acqua c'e ancora ma non e piu "libera": i batteri non la possono usare.
Il bersaglio: capire che conservare spesso vuol dire abbassare l'Aw. Il sale e lo zucchero non "uccidono" i batteri, li mettono a secco. Aw sotto 0.85 = zona sicura per i patogeni.""",
            "target": "I batteri hanno bisogno di acqua LIBERA non totale: sotto Aw 0.85 i patogeni non crescono - sale e zucchero non uccidono, mettono a secco (salumi, conserve, essiccati)",
            "nome": "Attivita dell'acqua (Aw)",
            "dominio": "tecnologie",
        },
        "fen-catena-freddo": {
            "scheda": """Tra i 5 e i 60 gradi i batteri si moltiplicano in fretta: e la "zona di pericolo". Sotto i 5 rallentano quasi a fermarsi, sopra i 60 muoiono. Tutta la conservazione al freddo e una cosa sola: tenere il cibo FUORI da quella finestra il piu possibile.

I batteri patogeni hanno un optimum di crescita intorno alla temperatura corporea (37C): per questo la zona 5-60C e pericolosa, e il picco e proprio a meta. La regola pratica: minimizzare il tempo che un alimento passa in quella fascia. Frigo a <=4C (rallenta), congelatore a -18C (ferma), cottura >=75C al cuore (uccide). Il freddo non sterilizza — SOSPENDE: i batteri ripartono quando scaldi. Per questo scongelare a temperatura ambiente e rischioso (la superficie entra in zona pericolo mentre il cuore e ancora gelato): si scongela in frigo.

Il raffreddamento rapido
Un CCP classico: un cibo cotto va raffreddato in fretta attraverso la zona pericolo (abbattitore, o porzioni piccole in frigo), non lasciato ore sul banco. Piu tempo in zona pericolo = piu batteri.
Il bersaglio: tenere il cibo fuori dai 5-60C. Freddo sospende, caldo uccide, la zona di mezzo e dove nasce il problema. Scongelare in frigo, raffreddare in fretta.""",
            "target": "Zona di pericolo 5-60C dove i batteri proliferano: freddo SOSPENDE (non sterilizza), caldo >=75C uccide - scongelare in frigo, raffreddare in fretta",
            "nome": "Catena del freddo",
            "dominio": "tecnologie",
        },
        "fen-conserve-botulino": {
            "scheda": """Le conserve fatte in casa possono uccidere. Il botulino e un batterio che vive SENZA ossigeno (dentro un barattolo sigillato), non da odore ne sapore (non te ne accorgi), e produce una delle tossine piu potenti che esistano. Ma ha due nemici precisi: l'acido e il calore. Conoscerli e la differenza tra una conserva sicura e una pericolosa.

Il Clostridium botulinum e anaerobio: prospera proprio nell'ambiente di una conserva sottovuoto o sott'olio, dove altri batteri non vanno. La sua tossina attacca il sistema nervoso. Il problema: non altera aspetto, odore o sapore — una conserva contaminata sembra normale.

Le due difese, misurabili
ACIDITA: sotto pH 4.6 il botulino NON puo crescere. Per questo i sottaceti (aceto), i pomodori acidi, la frutta sono relativamente sicuri: l'acido lo blocca. I sott'olio di verdure poco acide (funghi, peperoni) sono i piu rischiosi — l'olio non e una difesa, e solo assenza di ossigeno (che al botulino piace!). La difesa non e l'olio, e l'acidita o la sterilizzazione.
CALORE: le spore resistono all'acqua bollente (100C). Per distruggerle davvero nei cibi poco acidi serve la sterilizzazione in autoclave (121C). La bollitura normale NON basta per i sott'olio non acidi.
Il bersaglio: conserva sicura = pH sotto 4.6 (acida) OPPURE sterilizzazione vera. Il sott'olio non acido fatto male e il pericolo classico. L'olio non protegge — protegge l'acido o il calore giusto.""",
            "target": "Il botulino vive senza ossigeno (barattoli, sott'olio), non da odore ne sapore: difese MISURABILI = pH sotto 4.6 OPPURE sterilizzazione - l'olio non protegge, protegge l'acido",
            "nome": "Conserve e botulino",
            "dominio": "tecnologie",
        },
        "fen-frittura-lievitati": {
            "scheda": """Friggere un impasto lievitato non e come friggere una cotoletta. L'olio caldo colpisce una struttura piena di gas e glutine, e succede una cosa precisa: la superficie sigilla all'istante, e dentro il vapore continua a cuocere e gonfiare. Capire questo e la differenza tra un fritto leggero e asciutto e uno unto e pesante.

Quando l'impasto lievitato entra nell'olio a 170-180°C, l'acqua superficiale evapora di colpo e forma una crosta che SIGILLA: e questa barriera che impedisce all'olio di entrare. Dentro, il calore trasforma l'acqua in vapore che continua a cuocere e gonfiare l'impasto (come un forno in miniatura). Ecco perche un fritto fatto bene non e unto: la crosta sigilla prima che l'olio penetri.

La temperatura e tutto
170-180°C e la finestra. Troppo bassa (olio non abbastanza caldo): la crosta non si forma subito, l'olio entra, il fritto si impregna e diventa unto e pesante. Troppo alta: fuori brucia prima che dentro cuocia. La temperatura giusta sigilla in fretta e cuoce dentro in tempo.

Perche i lievitati specialmente
Un impasto lievitato ha gia gas dentro (dalla fermentazione): in frittura quel gas si espande col calore e da leggerezza. Piu la crosta sigillante, ottieni quel contrasto — guscio croccante, interno soffice e arioso. E il principio di arancine, panzerotti, bomboloni, zeppole.

Il bersaglio
Olio 170-180°C, immersione completa, la crosta sigilla e il vapore interno cuoce. Il vero bersaglio: la temperatura che sigilla prima che l'olio entri. Fritto leggero = crosta veloce; fritto unto = crosta lenta. Governa la temperatura e governi tutto.""",
            "target": "Olio 170-180C, immersione completa: la crosta sigilla subito e impedisce all olio di entrare, il vapore interno cuoce e gonfia - fritto leggero=crosta veloce, unto=crosta lenta",
            "nome": "La frittura di lievitati (il sigillo)",
            "dominio": "panificazione",
        },
        "fen-levain-pate-fermentee": {
            "scheda": """A questo punto hai visto poolish, biga, il lievito madre, il tangzhong. Ma restano due parole francesi che confondono tutti: levain e pâte fermentée. E capirle serve a una cosa più grande: mettere finalmente ordine in tutto il mondo dei pre-fermenti, che sembra un caos di termini stranieri e invece ha una logica semplice. Una volta chiara quella logica, sai sempre quale scegliere.

Levain e pâte fermentée sono i due pre-fermenti della tradizione francese. Ma spiegarli bene significa dare la mappa completa: perché esistono così tanti pre-fermenti, e come si distinguono davvero.

Levain: il "figlio" della madre (o la madre stessa)

Prima una verità che sorprende. "Levain" in francese vuol dire semplicemente "lievito naturale" — e molti panettieri e autori lo usano come sinonimo di lievito madre. Nei testi classici (Hamelman) "pani a levain" vuol dire pani a lievito madre. Quindi al livello più semplice: levain = madre.

Ma c'è una sfumatura tecnica utile. Spesso il levain è un offshoot della madre: prendi una parte della tua madre e la fai crescere apposta per una specifica infornata, magari cambiandole farina (più integrale, più segale) o idratazione, per adattarla a quel pane. La madre è la coltura che mantieni per sempre, il tuo ceppo permanente; il levain è il "figlio" che ne generi per il pane di oggi. Non consumi mai tutta la madre: ne stacchi un pezzo, lo fai levain, e la madre resta viva per la prossima volta. In pratica: madre = il ceppo che custodisci; levain = la porzione che prepari per infornare.

Pâte fermentée: il "vecchio impasto"

Questa è nettamente diversa, ed è l'idea francese più ingegnosa nella sua semplicità. Pâte fermentée significa "impasto fermentato", ma si chiama colloquialmente "vecchio impasto" (old dough). È un pezzo di impasto vero e proprio — completo, con farina, acqua, lievito e sale — preso da un'infornata precedente e conservato per fermentare, poi aggiunto all'impasto nuovo. Non è una pasta farina-acqua come il poolish: è pane crudo tenuto da parte.

Due cose la rendono unica. Primo: è l'unico pre-fermento che contiene sale, perché è impasto finito — quindi quando lo usi, riduci il sale nella ricetta nuova. Secondo: si usa tipicamente al 20% del peso della farina (un quinto), ed è comodissima perché non devi preparare nulla in anticipo — basta tenere da parte un pezzo dell'impasto di ieri. Dà al pane profondità di sapore e note burrose, con zero sforzo extra.

La mappa che mette ordine: la grande divisione

Ecco la logica che cercavi, e che rende tutto chiaro. Tutti i pre-fermenti si dividono in due famiglie, secondo una domanda sola: lievito selvaggio o commerciale?

Da una parte, i selvaggi ed eterni: il lievito madre e il levain. Sono colture di lieviti e batteri selvaggi, e possono essere perpetuati all'infinito — mesi, anni, decenni, persino secoli. Li rinfreschi e vivono per sempre. Danno acidità e complessità.

Dall'altra, i commerciali e a tempo: poolish, biga, e pâte fermentée. Usano lievito commerciale (o ne ereditano da un impasto), e non si propagano all'infinito — sono preparazioni "usa e getta" per una o poche infornate. Danno aroma e forza senza l'acidità del selvaggio.

E c'è una conseguenza elegante di questa divisione: se prendi un "vecchio impasto" (pâte fermentée) e lo riusi all'infinito, rinfrescandolo di continuo, prima o poi i lieviti selvaggi dell'ambiente prendono il sopravvento — e per definizione è diventato un lievito madre. La differenza tra le due famiglie non è netta come un muro: è un continuum, e il tempo trasforma il commerciale in selvaggio.

Come si distinguono per consistenza (il ripasso completo)

Chiudendo la mappa, per idratazione: il poolish è liquido (50% farina / 50% acqua, parti uguali). La biga è soda (farina con solo il 50-60% di acqua). La pâte fermentée è un impasto completo (idratazione del pane, con sale). Madre e levain variano secondo come li gestisci (liquidi o solidi). Sapere la consistenza ti dice anche come correggere l'acqua nella ricetta: con un poolish liquido chiudi l'impasto con meno acqua, con una biga soda con più.

Come lo verifichi

Dal sapore e dal comportamento. Un pane a levain/madre ha acidità e complessità (selvaggio); uno a poolish/biga/pâte fermentée ha aroma e forza ma non la stessa punta acida (commerciale). Se vuoi il "vecchio impasto" senza mantenere nulla, tieni da parte un pezzo dell'impasto di oggi per domani: è la pâte fermentée, ed è il modo più semplice per iniziare a usare i pre-fermenti.

Il bersaglio, letto bene

Non un numero unico, ma la scelta giusta e la mappa in testa: madre/levain per acidità e complessità (selvaggi, eterni); poolish/biga/pâte fermentée per aroma e forza (commerciali, a tempo); la pâte fermentée al 20% con sale, comoda perché è solo l'impasto di ieri tenuto da parte. E la cosa da ricordare, che scioglie il caos dei termini stranieri: dietro dieci parole diverse c'è una domanda sola — selvaggio o commerciale — e il tempo può trasformare l'uno nell'altro. Capito questo, non ti perdi più.""",
            "target": "La mappa di tutti i pre-fermenti: selvaggi ed eterni (madre, levain) vs commerciali a tempo (poolish, biga, pâte fermentée) · la pâte fermentée è il 'vecchio impasto', l'unico con sale, al 20% · levain ≈ madre",
            "nome": "Levain e pâte fermentée (i pre-fermenti francesi)",
            "dominio": "panificazione",
        },
        "fen-tangzhong-yudane": {
            "scheda": """Entra in una panetteria a Tokyo, Hong Kong o Seoul e vedrai vetrine piene di pane diverso dal nostro: soffice come una nuvola, lucido, che si strappa a filamenti, e che resta morbido per giorni. Il segreto non è più burro o più zucchero. È un trucco di fisica dell'amido: cuoci una piccola parte della farina prima di impastare. Si chiama tangzhong, o yudane. E una volta capito, cambia il pane soffice per sempre.

Il tangzhong (cinese) e lo yudane (giapponese) sono la stessa idea con due esecuzioni: pre-cuocere una parte della farina con un liquido per gelatinizzare l'amido prima dell'impasto. È il cuore del pane soffice asiatico, e un'applicazione elegante di scienza che già conosci.

Il principio: gelatinizzare l'amido, per legare più acqua

Ecco il meccanismo, ed è pura fisica dell'amido. Quando scaldi la farina con un liquido intorno ai 65°C, i granuli di amido gelatinizzano: si gonfiano, assorbono acqua e la intrappolano, formando una pasta densa e vischiosa. Questo amido pre-gelatinizzato trattiene molta più acqua di quanta la farina cruda potrebbe. Aggiungi questa pasta all'impasto e succede una cosa importante: l'idratazione effettiva sale — l'impasto porta più acqua — ma senza diventare slegato e ingestibile, perché quell'acqua è legata nell'amido, non libera. Ottieni la morbidezza di un impasto molto idratato con la maneggevolezza di uno normale. È la gelatinizzazione che già conosci dalla cottura, ma usata di proposito, prima, a freddo nell'impasto.

Cosa ottieni: soffice, alto, e che dura

I risultati sono tre, e sono spettacolari. Primo: mollica soffice, fine, cotonosa, "a nuvola" — quella texture da milk bread che si strappa a filamenti. Secondo: più volume e oven spring, perché la struttura regge meglio. Terzo, il più importante: shelf-life allungata. Qui il legame diretto con il raffermimento. Il pane diventa raffermo soprattutto per la retrogradazione dell'amido — le molecole di amido, raffreddandosi, ricristallizzano ed espellono acqua. L'acqua abbondante e legata del tangzhong rallenta questa retrogradazione: il pane resta soffice per due-quattro giorni invece di seccare in una notte. Sacrifichi una piccola parte della farina a una cottura veloce, e in cambio guadagni umidità, spinta e durata che nessuna quantità di impastamento potrebbe darti.

Tangzhong o yudane: la stessa idea, due mani diverse

Qui la distinzione, ed è il cuore. Entrambi gelatinizzano l'amido, ma in due modi:

Il tangzhong è un roux cotto: metti farina e liquido (acqua o latte) in un pentolino e li scaldi mescolando fino a ~65°C, finché diventano una pasta densa. Poi la raffreddi e la aggiungi all'impasto. Dà una mollica più fine, cremosa, custardy, delicatamente soffice. È di origine cinese/taiwanese.

Lo yudane è una scottatura non cotta: versi acqua bollente sulla farina, mescoli, e lasci riposare (di solito tutta la notte). Il calore dell'acqua bollente gelatinizza l'amido senza cottura sul fuoco. Dà una mollica più masticabile, elastica, quasi mochi, con un aroma di grano più dolce. È di origine giapponese. Un vantaggio pratico dello yudane: versare acqua bollente è più facile che cuocere una pasta, per questo l'industria lo preferisce (si può fare in grande).

Quale scegliere? Tangzhong per la sofficità più delicata e cremosa; yudane per una resilienza masticabile. Nel gusto la differenza è minima — è questione di texture.

Le dosi: quanto, e il punto di equilibrio

C'è un numero che conta. Si pre-gelatinizza in genere il 15-20% della farina totale della ricetta: è il punto di equilibrio tra sofficità, volume e maneggevolezza. Puoi spingere fino al 30% per la massima morbidezza, ma oltre un certo punto paghi: meno volume e lievitazione più lenta, perché l'amido gelatinizzato trattiene gas peggio del glutine. Più non è meglio: il 15-20% è il territorio giusto per quasi tutto.

Le trappole da conoscere

Due cose. Primo: il tangzhong lavora contro i pani croccanti. Se vuoi una baguette o un pane rustico con crosta dura e mollica aperta, il tangzhong è il nemico — rende tutto soffice e a grana fine, l'opposto. È fatto per gli impasti arricchiti e soffici (milk bread, bun, sandwich, cinnamon rolls), non per il pane a crosta. Secondo, un dettaglio che lega alla temperatura dell'impasto: se aggiungi il tangzhong ancora freddo di frigo, abbassi la temperatura dell'impasto e rallenti la fermentazione. Portalo a temperatura ambiente prima di usarlo.

Come lo verifichi

Guarda la pasta e il risultato. Il roux è pronto quando è una pasta densa che lascia una traccia visibile quando ci passi il cucchiaio (intorno ai 65°C). Nel pane finito: se la mollica è soffice, fine, e il giorno dopo è ancora morbida, il tangzhong ha funzionato. Se il pane è denso o poco cresciuto, forse hai messo troppa farina nel roux (oltre il 20-25%) e hai penalizzato il glutine.

Il bersaglio, letto bene

C'è un numero — il 15-20% della farina pre-gelatinizzata, il roux portato a ~65°C — ma il vero bersaglio è l'effetto: un pane soffice come una nuvola che resta fresco per giorni, ottenuto legando più acqua nell'amido invece che aggiungendo grassi. E la cosa da ricordare, che è pura eleganza tecnica: non serve più burro per un pane più morbido — a volte serve solo cuocere un po' di farina prima. È il tipo di trucco che sembra magia e invece è fisica dell'amido applicata bene.""",
            "target": "Pre-cuoci il 15-20% della farina con liquido a ~65°C: l'amido gelatinizza e lega più acqua → pane soffice a nuvola che resta fresco giorni · tangzhong=roux cotto (fine), yudane=scottato (mochi) · non per i croccanti",
            "nome": "Tangzhong e yudane (water roux)",
            "dominio": "panificazione",
        },
        "fen-lievito-madre": {
            "scheda": """Il lievito madre non è un ingrediente che compri: è un organismo vivo che allevi. Una colonia di lieviti selvaggi e batteri che mangia, cresce, respira, invecchia. E come ogni essere vivo ha un momento in cui è al massimo della forza — il picco. Saperlo cogliere è la differenza tra un pane che esplode in forno e uno che resta piatto. Non è una ricetta, è un rapporto: impari a leggere la tua madre come leggi l'umore di una persona.

Il lievito madre (o pasta madre) è il più antico e vivo dei pre-fermenti. Governarlo bene è la competenza che separa il panettiere dal semplice esecutore, perché non segui istruzioni: interpreti segnali di un organismo che cambia ogni giorno.

Cos'è davvero: due popolazioni che convivono

Dentro la madre vivono due famiglie di microrganismi in equilibrio. I lieviti selvaggi (Saccharomyces cerevisiae, Candida humilis e altri) mangiano gli zuccheri della farina e producono anidride carbonica — la spinta, i buchi, la crescita. I batteri lattici (Lactobacillus) producono acidi: il lattico (sapore morbido, yogurt) e l'acetico (sapore acuto, aceto) — il gusto e la conservazione. Tutto quello che fai — quando rinfreschi, a che temperatura la tieni, quanto la lasci — sposta l'equilibrio tra queste due popolazioni. Governare la madre è governare questo equilibrio.

Il picco: il concetto che comanda tutto

Ecco il cuore. Dopo che la rinfreschi (le dai farina e acqua fresche), la popolazione di lievito cresce in modo esponenziale mangiando il nuovo cibo. La CO₂ aumenta, la madre gonfia e sale. A un certo punto raggiunge il picco: il momento in cui il lievito è alla massima densità e la produzione di gas è massima — di solito quando è raddoppiata o triplicata di volume, ed è sul punto di ricominciare a scendere. Quello è il momento di usarla. Prima del picco, il lievito non ha ancora la forza piena. Dopo il picco (quando ricade), la spinta cala e l'acidità sale. Cogliere il picco è la singola abilità più importante, e la più difficile: il picco non è un orario, è un momento, e cambia ogni giorno con la temperatura.

Leggere i segnali: gli odori come un quadrante

Qui la parte che nessun libro insegna davvero, ma che il naso impara. La madre ti dice a che punto è del suo ciclo con l'odore, e imparare a leggerlo è come leggere un orologio:

Appena rinfrescata: odore dolciastro, farinoso, mite. Bassa attività. Verso il picco: sempre più simile allo yogurt, acidulo ma piacevole, con una nota di lievito e pane. Al picco: odore equilibrato, acidulo ma non pungente — "sa di voler diventare pane". Oltre il picco (in calo): vira all'aceto, più acuto e pungente (l'acetico sale mentre il lievito rallenta). Molto oltre, affamata: odore di acetone, solvente, smalto per unghie — è il segnale che ha esaurito tutto il cibo e va rinfrescata subito.

Insieme all'odore, guardi la crescita: raddoppio o triplicazione affidabile, tante bolle, salita e discesa prevedibili. Questi segnali insieme battono qualsiasi trucco.

Il float test: perché non fidartene troppo

Un avvertimento da conoscere. C'è un test diffuso — metti un cucchiaino di madre nell'acqua, se galleggia è pronta. Galleggia perché è piena di gas, e un po' funziona. Ma è ingannevole: una madre molto idratata (liquida) può fallire il test anche se è attivissima, e una sovra-matura può passarlo anche se è già oltre il picco. Il gas non ti dice la forza né la maturità. Usalo come un indizio, non come giudice: rise e odore sono molto più affidabili.

Il rinfresco: la leva con cui la governi

Rinfrescare significa buttare gran parte della madre e darle farina e acqua fresche. È come si mantiene viva e si controlla l'equilibrio. Il rapporto conta: 1:1:1 (parti uguali di madre, farina, acqua) raddoppia in 4-8 ore a temperatura ambiente (21-26°C). Rapporti più alti (1:5:5, cioè poca madre e molto cibo) aumentano la popolazione di lievito e diluiscono l'acidità — li usi per rinforzare una madre debole o troppo acida. Rapporti bassi aumentano l'acidità più in fretta. Se la madre sa troppo di aceto (acidità in eccesso), rinfreschi più spesso o con più cibo per riportare l'equilibrio verso il lievito.

Attività non è forza (la distinzione che confonde tutti)

Un punto fine ma importante. Una madre che raddoppia in fretta è attiva — ma non è detto che sia forte. La forza è la capacità di reggere il picco a lungo, trattenere il gas, dare oven spring costante. Una madre debole può fare tante bolle e poi collassare subito; una forte sale con calma, tiene il picco, e spinge il pane in modo affidabile. La forza si costruisce col tempo: una madre nuova è usabile dopo due settimane, ma non è davvero matura prima di alcuni mesi. Le prime pagnotte più piatte non sono un fallimento, sono il percorso.

Come lo verifichi

Segna il livello dopo il rinfresco (un elastico intorno al barattolo). Guarda quando raddoppia/triplica e annusa: quando è al massimo del volume, con odore equilibrato e sul punto di fermarsi, è il picco — usala lì. Se è già ricaduta e sa d'aceto, o rinfreschi e aspetti il prossimo picco, o la usi accettando un pane più acido e meno spinto. Tieni un piccolo registro dei tempi di picco per una settimana: scoprirai il ritmo della tua madre.

Il bersaglio, letto bene

C'è un segno quantitativo — il raddoppio/triplicazione in 4-8 ore dopo un rinfresco 1:1:1 a 21-26°C — ma il vero bersaglio è qualitativo: cogliere il picco, quel momento in cui volume, bolle e odore dicono che il lievito è al massimo. Non un orologio, un momento da leggere. E la cosa da ricordare, che fa di te un panettiere e non un esecutore: la madre non si comanda, si ascolta. Impari il suo ritmo, e allora ti dà pani che esplodono.""",
            "target": "Cogliere il PICCO: raddoppio/triplicazione in 4-8h dopo rinfresco 1:1:1 a 21-26°C, odore equilibrato e sul punto di ricadere · leggi gli odori come un quadrante · non fidarti del float test",
            "nome": "Il lievito madre (gestione e picco)",
            "dominio": "panificazione",
        },
        "fen-temperatura-impasto": {
            "scheda": """Fai lo stesso pane a gennaio e a luglio, stessa ricetta, e ti comporta in modo diverso: d'estate lievita in metà tempo, d'inverno sembra addormentato. Non è colpa tua né della ricetta: è la temperatura dell'impasto. È la variabile che decide la velocità di tutto — e la cosa che i fornai professionisti sanno, e i dilettanti no, è che non si subisce: si calcola e si centra, ogni volta, in ogni stagione.

La temperatura finale dell'impasto — quella che ha appena finito di impastare, prima di lievitare — è uno dei controlli più potenti e meno conosciuti del pane. Governa la fermentazione, e con essa i tempi, il sapore, la riuscita. Impararla a controllare è ciò che rende il pane ripetibile.

Perché conta così tanto: la temperatura è velocità

Il legame è diretto e lo conosci già dal principio del Q10: le reazioni vanno più veloci al caldo, più piano al freddo. Nell'impasto significa che più caldo è, più veloce fermenta (tempi corti); più freddo è, più lenta (tempi lunghi). E l'effetto è sorprendentemente forte: bastano 2°C in più per aumentare la velocità di fermentazione di circa il 25%. Ecco perché lo stesso impasto d'estate corre e d'inverno arranca: pochi gradi cambiano tutto. Non è una sfumatura, è la leva principale sui tempi.

La finestra: dove sta un buon impasto

Per il pane artigianale la temperatura finale ideale sta intorno ai 24-26°C. È il punto dove la fermentazione ha una velocità gestibile e il glutine si comporta bene. C'è un limite superiore da non superare: sopra i 28°C circa, oltre a correre troppo, l'impasto assorbe troppo ossigeno durante l'impastamento e questo "sbianca" la farina, impoverendo colore e sapore. Per questo i forni artigianali tengono l'impasto sotto i 28°C. Impasti "veloci" industriali usano temperature più alte (28-32°C) apposta per accorciare i tempi, sacrificando un po' di qualità.

La leva vera: si controlla con l'acqua

Qui il cuore pratico, ed è un'idea elegante. Alla temperatura finale dell'impasto contribuiscono più cose: la temperatura della farina, quella dell'aria (ambiente), l'eventuale prefermento, e il calore generato dall'impastare. Di queste, quasi tutte non le puoi cambiare facilmente: la farina e l'aria sono quelle che sono. Ma una la controlli benissimo: l'acqua. Scaldi o raffreddi l'acqua dell'impasto, e correggi la temperatura finale. È la manopola del fornaio.

La formula DDT: come si calcola l'acqua

Esiste una formula, semplice, che i fornai usano da un secolo. Per centrare una temperatura desiderata dell'impasto (DDT), calcoli la temperatura dell'acqua così: moltiplichi la DDT per il numero di fattori (3 senza prefermento, 4 con), poi sottrai le temperature che già conosci — farina, aria, eventuale prefermento — e un "fattore di attrito", cioè il calore che l'impastare aggiunge. Il risultato è la temperatura a cui portare l'acqua. In pratica: d'inverno userai acqua tiepida, d'estate acqua fredda o con ghiaccio, per arrivare sempre alla stessa temperatura finale. Stessa DDT tutto l'anno = stesso pane tutto l'anno.

Il fattore di attrito: la parte onesta della formula

Un avvertimento da professionista. Il "fattore di attrito" è il calore che l'impastamento genera — a mano poco (circa 3-4°C), con l'impastatrice di più, e cresce coi minuti e la velocità. È la parte meno precisa della formula: alcuni fornai lo chiamano scherzosamente "fudge factor" (fattore-aggiustamento) invece di friction factor, perché è più una taratura sull'esperienza che un numero esatto. La formula ti porta vicino; poi impari a correggere per la tua impastatrice e il tuo metodo, misurando la temperatura dell'impasto a fine lavorazione e aggiustando la volta dopo.

Come lo verifichi

Con un termometro, semplicemente. Misura la temperatura dell'impasto appena finito di impastare: è la tua FDT reale. Se è più alta della DDT che volevi, la prossima volta usa acqua più fredda (o riduci il tempo di impastamento); se più bassa, acqua più calda. Tieni un piccolo registro — il fornaio serio lo fa — e in poche prove trovi il tuo fattore di attrito e centri la temperatura ogni volta. È l'abitudine che trasforma "ogni volta viene diverso" in "ogni volta viene uguale".

Il bersaglio, letto bene

C'è un numero, la DDT (tipicamente 24-26°C per il pane), da centrare regolando l'acqua. Ma il bersaglio vero non è "una temperatura giusta in assoluto" — è la temperatura adatta a ciò che vuoi: più bassa (anche 18°C o meno) per lievitazioni lunghe e fredde, più alta per tempi corti, sapendo di non superare i 28°C per non rovinare la farina. E soprattutto è la riproducibilità: il vero potere della DDT è che, centrando la stessa temperatura ogni volta, il pane viene uguale a ogni infornata, in ogni stagione. Non subire la temperatura: sceglierla e centrarla. È il segreto meno appariscente e più potente del pane costante.""",
            "target": "La temperatura finale governa la velocità di tutto (Q10: +2°C = +25% di fermentazione) · si centra regolando l'acqua, con la formula DDT · finestra 24-26°C, mai oltre 28°C · il potere vero è la riproducibilità",
            "nome": "La temperatura dell'impasto (DDT)",
            "dominio": "panificazione",
        },
        "fen-farina-forza": {
            "scheda": """Provi a fare un panettone con la farina dei biscotti e ti si affloscia: non regge le ore di lievitazione, non tiene i grassi, collassa. Provi a fare una frolla con la farina del panettone e viene dura, nervosa, si ritira. Stessa quantità di farina, risultati opposti. La differenza è la forza — quanto quella farina regge il lavoro, il tempo, l'acqua. E c'è un modo per misurarla, prima ancora di impastare.

La forza della farina è la sua capacità di formare un glutine che regge: che trattiene il gas per tutta la lievitazione, che sopporta acqua e grassi, che non cede. Non tutte le farine sono uguali, e scegliere quella giusta per il pane che fai è una decisione che viene prima di tutte le altre.

Il punto che ribalta l'intuito: quantità non è qualità

Ecco la cosa che quasi nessuno spiega bene. Verrebbe da pensare: più proteine nella farina, più glutine, più forza. È vero solo a metà. Le proteine ti dicono quanto glutine può formarsi — la quantità. Ma non ti dicono come quel glutine si comporterà sotto sforzo — la qualità. Due farine con le stesse proteine possono dare un glutine tenace e uno debole. Per questo la forza non si legge (solo) dalle proteine: serve misurare come il glutine reagisce quando lo tiri e lo gonfi. Quantità e qualità sono due cose diverse, e la forza è questione di qualità.

Come si misura: l'alveografo e l'indice W

Qui entra uno strumento da laboratorio, ed è il linguaggio del mestiere. L'alveografo di Chopin prende un disco di impasto e ci soffia dentro aria finché si gonfia come un palloncino e scoppia. Misura tre cose: P, la tenacità (quanta resistenza oppone); L, l'estensibilità (quanto si allunga prima di rompersi); e W, l'area sotto la curva — la forza totale, l'energia che serve per gonfiare e far scoppiare la bolla. Il W è il numero che i molini stampano sulle confezioni professionali, ed è il modo in cui i panettieri parlano di forza: "una farina da W300".

La scala del W: dalla frolla al panettone

Il W ti dice subito che tipo di lavoro regge la farina:

Debole, fino a W170. Glutine che trattiene poco gas, poca acqua. Perfetta per ciò che NON deve lievitare a lungo: biscotti, frolle, cialde, dolci teneri. Se la usi per il pane, non regge.

Media, W180-260. Il territorio del pane comune, della pizza, delle pagnotte, del pane francese. Regge una lievitazione normale. È la fascia più usata al banco.

Forte, oltre W300-340. Le farine "da grande lievitato", spesso chiamate "Manitoba". Glutine tenacissimo che trattiene gas per lievitazioni lunghe, regge quantità importanti di grassi, zuccheri, liquidi. È la farina del panettone, del pandoro, dei prefermenti lunghi. Assorbe molta acqua (fino al 90% per le più forti).

Il P/L: il carattere della forza

Il W dice quanta forza; il P/L dice che tipo di forza. È il rapporto tra tenacità (P) ed estensibilità (L). Un P/L basso (sotto ~0,4) è una farina molto estensibile, che si allunga tanto ma resiste poco — impasti che si stendono facili ma stanno molli. Un P/L alto è tenace, elastica, resistente ma poco estensibile — impasti che si ritirano. Per la pizza si cerca un equilibrio; per il pane in cassetta più tenacità; per la sfoglia più estensibilità. Due farine con lo stesso W possono avere caratteri diversi a seconda del P/L.

Attenzione: due trappole da tecnologo

Prima trappola: il W non predice l'acqua che la farina assorbe. Contro l'intuito, una farina più forte non è automaticamente più "assetata": l'assorbimento dipende da proteine, amido danneggiato, ceneri — non dal W in sé. Un W alto suggerisce che regge lievitazioni lunghe, non che vuole più acqua.

Seconda trappola: l'alveografo (e il W) è nato per i grani teneri europei — è uno standard di Francia e Italia. Per i grani duri e forti nordamericani (dove proteine e qualità vanno più di pari passo) si usa un altro strumento, il farinografo, e spesso basta guardare le proteine. Il W è prezioso nel mondo del grano tenero, meno altrove. Sapere quando uno strumento vale è parte del mestiere.

Come lo verifichi

Prima dall'etichetta: le farine professionali riportano il W (e a volte P/L); quelle da supermercato spesso solo le proteine — e lì, come regola grezza, più proteine = più forte, ma senza la precisione del W. Poi con le mani e col risultato: se un impasto a lunga lievitazione collassa prima di cuocere, la farina era troppo debole per quel tempo; se un dolce viene duro e nervoso, era troppo forte. La forza giusta è quella che regge esattamente il lavoro che le chiedi — né meno né più.

Il bersaglio, letto bene

C'è un numero vero, il W, con la sua scala (debole/media/forte), più il P/L per il carattere. Ma il bersaglio non è "la farina più forte" — è la forza giusta per il pane che fai: debole per ciò che non lievita, media per il pane quotidiano, forte per i grandi lievitati e le lunghe lievitazioni. Una farina troppo forte per un pane semplice lo rende nervoso e faticoso; una troppo debole per un panettone lo fa collassare. E la cosa da ricordare, che è il cuore: non conta quanto glutine c'è, conta come si comporta — la forza è qualità, non quantità.""",
            "target": "Non conta quanto glutine, conta come si comporta: la forza è qualità non quantità · si misura con l'alveografo (indice W): <170 debole (frolle), 180-260 media (pane), >340 forte (panettone) · il P/L dà il carattere",
            "nome": "La farina e la sua forza (W)",
            "dominio": "panificazione",
        },
        "fen-idratazione": {
            "scheda": """Perché un bagel è compatto e gommoso, e una ciabatta è piena di buchi e leggera? Stessa farina, stesso lievito. La differenza è una sola: quanta acqua c'è nell'impasto. L'idratazione è la leva più basilare del pane — quella che decide com'è la mollica, quanto è maneggevole l'impasto, com'è la crosta. Ed è anche il linguaggio con cui i panettieri parlano tra loro: "settanta per cento".

L'idratazione è il rapporto tra acqua e farina, ed è la prima decisione di ogni impasto. Non è un dettaglio: è la manopola che governa il carattere del pane prima di ogni altra. Capirla ti dà il controllo su texture, lavorabilità e crosta insieme.

La percentuale del panettiere: il linguaggio del mestiere

Prima lo strumento. I panettieri misurano l'acqua come percentuale sul peso della farina, non in valore assoluto. Mille grammi di farina e settecento d'acqua fanno un'idratazione del 70%. È una convenzione potente, perché rende ogni ricetta confrontabile e scalabile: "70%" dice subito che tipo di impasto è, indipendentemente dalla quantità. Quando un fornaio dice "lavoro all'80", sta dicendo una cosa precisa sul comportamento del suo impasto. Impararla è entrare nel linguaggio del mestiere.

Cosa fa l'acqua: due lavori fondamentali

L'acqua fa due cose che decidono tutto. Primo: attiva il glutine — le proteine non si legano in rete senza acqua, quindi l'acqua è la condizione perché la maglia glutinica esista. Secondo: diventa vapore in forno — e il vapore è ciò che gonfia la mollica. Più acqua c'è, più vapore si genera dentro il pane in cottura, più le bolle si espandono. Ecco il legame diretto: più acqua → più vapore → mollica più aperta. Meno acqua → meno vapore → mollica più fitta. Tutta la scala che segue viene da qui.

La scala: da fitto a aperto

Questo è il cuore pratico. Ogni pane sta a un punto della scala di idratazione, e il punto decide mollica e lavorabilità:

Bassa (circa 50-60%). Impasto sodo, asciutto, facile da impastare e modellare. Mollica fitta, uniforme, gommosa; crosta più spessa. È il territorio di bagel e pretzel — dove la struttura compatta e il "morso" sono la caratteristica voluta. Raffermisce anche più in fretta (meno acqua trattenuta).

Media (circa 65-70%). L'equilibrio. Impasto morbido ma maneggevole, tiene la forma, si lavora senza troppa fatica. Mollica di grana media, regolare. È il punto del pane in cassetta, delle pagnotte, di gran parte del pane quotidiano — e il punto giusto per imparare.

Alta (circa 75-85%). Impasto molle, appiccicoso, difficile da maneggiare: non si impasta alla vecchia maniera, si governa con pieghe (stretch and fold) e mani bagnate. In cambio dà la mollica aperta e irregolare, i buchi grandi, la crosta croccante. È il territorio di ciabatta e focaccia, e l'estetica "da Instagram" del pane artigianale.

Il tetto: oltre l'85% si rompe

Qui la trappola, ed è metodo puro. Più acqua non è sempre meglio. Oltre l'85% circa, la rete glutinica non riesce più a trattenere il gas: le bolle scoppiano e si fondono, e la mollica diventa irregolare in modo brutto — grandi buchi vuoti e zone dense, non un'alveolatura bella. C'è un limite fisico a quanto vapore la struttura può reggere. Spingere l'idratazione oltre le capacità della tua farina e della tua tecnica non dà pane più aperto, dà pane sfatto.

La dipendenza dalla farina (attenzione qui)

Un punto che confonde molti: la stessa percentuale si comporta diversamente con farine diverse. Le farine forti (più proteine) assorbono più acqua e reggono idratazioni più alte. Le integrali e la segale sono assetate — la crusca e i pentosani bevono molta acqua senza fare glutine — quindi un impasto integrale al 70% sembra più asciutto di uno bianco al 70%, e spesso serve aggiungere il 5-15% d'acqua in più per compensare. "70%" non è un valore assoluto di morbidezza: dipende da cosa c'è nel sacco.

Il legame con la cottura

Un aggancio che chiude il cerchio con la crosta: gli impasti più bagnati vogliono un forno più caldo, perché serve fissare la struttura in fretta prima che la mollica, gonfia di vapore, collassi. Più acqua, più calore alla partenza. È lo stesso principio che hai visto nella crosta e nella laminazione.

Come lo verifichi

Con le mani e con l'occhio. Impasto sodo che si modella facile → bassa idratazione, aspettati mollica fitta. Impasto molle e appiccicoso che va gestito con le pieghe → alta, aspettati mollica aperta. E il windowpane resta il giudice dello sviluppo: se a una certa idratazione l'impasto si strappa subito, o è poco sviluppato o è troppo bagnato per la tua farina. Aumenta l'idratazione poco per volta (2-3% alla volta), non a salti, mentre prendi confidenza.

Il bersaglio, letto bene

C'è un numero vero qui — la percentuale — ma non un valore unico giusto: il bersaglio è l'idratazione adatta al pane che vuoi. Fitto e maneggevole per un bagel o un pane in cassetta (55-65%); aperto e croccante per una ciabatta (75-85%); l'equilibrio nel mezzo per il pane di tutti i giorni. Il vero bersaglio è la più alta idratazione che riesci a gestire in modo affidabile con la tua farina e la tua tecnica — perché è lì che ottieni mollica aperta senza che l'impasto ti sfugga di mano. E ricorda: il numero è una guida, la farina ha l'ultima parola.""",
            "target": "La percentuale del panettiere (acqua/farina): ~55-60% mollica fitta e facile (bagel), ~65-70% equilibrio, ~75-85% aperta e appiccicosa (ciabatta) · tetto ~85% oltre si sfatta · la farina cambia tutto",
            "nome": "L'idratazione dell'impasto",
            "dominio": "panificazione",
        },
        "fen-latte-impasto": {
            "scheda": """Sostituisci l'acqua col latte nell'impasto e il pane cambia: mollica più fine e morbida, crosta più dorata, sapore più pieno, e resta soffice più a lungo. Il latte è un arricchente come il grasso e lo zucchero — ne porta un po' di entrambi. Ma ha una storia particolare, quella dello "scottare il latte", che vale la pena raccontare bene: perché una volta era necessaria, e oggi quasi non serve più. Ed è il tipo di cosa che separa chi ripete la ricetta da chi capisce cosa fa.

Il latte nell'impasto porta più cose insieme, perché è esso stesso una miscela: acqua, grasso, zuccheri (il lattosio), proteine. Capire cosa fa ciascuna parte ti dice perché un pane al latte è diverso da un pane all'acqua — e ti fa evitare un passaggio inutile che molti ancora fanno per abitudine.

Cosa porta il latte: un po' di tutto

Il latte è un arricchente "completo ma gentile". Il suo grasso ammorbidisce l'impasto come farebbe un filo d'olio — riveste il glutine, dà tenerezza (lo shortening che conosci). Il lattosio, lo zucchero del latte, fa due cose: dà una punta di dolcezza, e soprattutto colora — è uno zucchero che il lievito quasi non consuma, quindi resta nell'impasto e caramella in forno, dando quella crosta dorata e profonda tipica dei pani al latte. Le proteine danno struttura e sapore. E l'acqua del latte idrata come l'acqua normale. Il risultato è un pane con mollica più fine e soffice, crosta più colorata, sapore più ricco, e che resta morbido più giorni.

La proteina che dà fastidio (e il calore che la disattiva)

Qui la parte interessante. Nel latte c'è una proteina del siero che interferisce: indebolisce il glutine e può rallentare il lievito, ostacolando la lievitazione. Per questo, storicamente, le ricette dicevano di "scottare" il latte — scaldarlo fin quasi al bollore (intorno agli 82°C) e poi raffreddarlo. Il calore denatura quella proteina, la disattiva, e così il pane lievita meglio e viene più soffice e alto. Questa è la spiegazione classica, quella dei libri, ed è vera — per il latte crudo.

Perché oggi scottare serve quasi sempre a niente (il punto che pochi sanno)

Ed ecco la sfumatura che un tecnologo alimentare conosce e un ricettario no. Quella proteina la disattiva il calore — ma il latte che compri oggi è già pastorizzato, spesso ultra-pastorizzato, cioè già scaldato in fase industriale. Le sue proteine del siero sono in gran parte già denaturate prima che tu apra la confezione. Quindi scottare di nuovo il latte moderno aggiunge poco o nulla alla lievitazione: il lavoro è già fatto. La tecnica dello scalding era essenziale un secolo fa, col latte crudo appena munto; oggi è in gran parte un residuo del passato. Va aggiunto per onestà che il meccanismo preciso non è del tutto chiarito nemmeno in letteratura — un motivo in più per non trattarlo come dogma.

Restano due casi in cui scottare ha ancora senso, ma diversi dall'originale: se usi latte crudo (non pastorizzato), e quando vuoi infondere aromi nel latte caldo (vaniglia, spezie). Fuori da questi, puoi saltare il passaggio: userai latte tiepido, non bollito, e il pane verrà bene lo stesso.

Latte in polvere: perché l'industria lo ama

Un aggancio pratico. Molti pani industriali usano latte in polvere magro invece che liquido: costa meno, si conserva, e — dettaglio da tecnologo — quello "a basso calore" (low-heat) porta gli stessi benefici del latte fresco su morbidezza e colore. È lo stesso principio, in forma stabile e maneggevole.

Come lo verifichi

Guarda mollica, colore, durata. Mollica più fine e tenera, crosta più dorata del solito, pane che resta morbido → il latte sta lavorando. Se un pane al latte lievita male e usi latte crudo, prova a scottarlo; se usi latte del supermercato, il problema è altrove (non è la proteina del siero, quella è già disattivata). Non sprecare tempo a scottare un latte già pastorizzato aspettandoti miracoli sulla lievitazione.

Il bersaglio, letto bene

Non un numero, ma l'effetto voluto e la scelta consapevole: il latte per una mollica più tenera, una crosta più dorata (grazie al lattosio che non fermenta), un pane che dura. E la consapevolezza tecnica che ti distingue: scottare il latte, per come si compra oggi, serve quasi solo per infondere aromi o col latte crudo — non è il passaggio magico per la lievitazione che le vecchie ricette promettono. Sapere perché una tecnica esisteva, e perché oggi conta meno, è esattamente il tipo di cosa che rende un professionista diverso da un esecutore.""",
            "target": "Ammorbidisce (grasso), colora la crosta (il lattosio non fermenta e caramella), dà struttura e durata · la storia dello 'scottare il latte' è superata: oggi è già pastorizzato, la proteina è già disattivata",
            "nome": "Il latte nell'impasto",
            "dominio": "panificazione",
        },
        "fen-uova-impasto": {
            "scheda": """La differenza tra una baguette e una brioche è tutta lì: la brioche ha le uova. Danno quella mollica gialla, soffice, ricca, che si affetta pulita e resta morbida per giorni. Ma l'uovo non è un ingrediente solo — è due, incollati insieme nel guscio. Il tuorlo e l'albume fanno cose opposte, e chi sa separarli comanda la tenerezza e la struttura del pane.

L'uovo è l'arricchente più completo, perché contiene in sé due materie con ruoli diversi: il tuorlo, grasso ed emulsionante, che ammorbidisce; l'albume, proteico, che struttura. Capire questa doppia natura ti fa scegliere non solo "quante uova" ma "quale parte", per l'effetto che vuoi.

Il tuorlo: grasso, emulsionante, morbidezza

Il tuorlo porta grasso — e quel grasso fa esattamente quello che hai visto nella scheda dei grassi: riveste i filamenti di glutine e l'amido, li accorcia (lo "shortening"), e rende la mollica più tenera e meno gommosa. Ma il tuorlo ha un'arma in più: la lecitina, un emulsionante potente — lo stesso che tiene insieme olio e acqua nella maionese. Nel pane la lecitina è ciò che permette a tutto il burro di una brioche di fondersi nell'impasto senza separarsi, e all'impasto di crescere alto malgrado tutto quel grasso. Senza la lecitina del tuorlo, la brioche sarebbe impossibile. Il tuorlo dà anche il colore — i suoi pigmenti danno la mollica gialla e aiutano la doratura — e porta umidità che tiene il pane morbido. Aggiungere tuorli = più tenero, più giallo, più ricco.

L'albume: proteine, struttura, tenuta

L'albume è quasi l'opposto: quasi solo acqua e proteine, niente grasso. Le sue proteine, scaldandosi, si rassodano — come quando frigge un uovo — e formano una seconda impalcatura accanto al glutine. Questa struttura in più fa sì che il pane tenga la forma e si affetti pulito, senza sbriciolarsi: per questo i pani con uova reggono bene per i sandwich. L'albume rassoda e dà tenuta, ma non ammorbidisce come il tuorlo. Aggiungere albumi = più struttura, più "morso", impasto che tiene meglio.

La scelta che conta: tuorlo, albume, o uovo intero

Qui sta la leva vera, e la conosci ora. Solo tuorli → massima ricchezza e morbidezza, mollica quasi da torta (la brioche più decadente). Solo albumi → struttura senza grasso, pane più masticabile che tiene la forma. Uovo intero → la via di mezzo, un po' di tutto (struttura, grasso, umidità, colore). E una regola pratica da tenere a mente: se il pane esce troppo denso o duro, un tuorlo in più lo ammorbidisce; se l'impasto arricchito è troppo molle e non tiene in lievitazione, un albume in più lo rassoda. Hai due manopole, non una.

Perché le uova aiutano il pane arricchito a reggere

C'è un motivo profondo per cui l'uovo sta negli impasti ricchi. Grasso e zucchero, lo sai, ammorbidiscono il glutine e strozzano il lievito: da soli renderebbero l'impasto troppo cedevole per stare in piedi. Le proteine dell'albume danno la struttura che compensa quel rammollimento — sono l'impalcatura che regge nonostante il burro e lo zucchero. Ecco perché brioche e panettone, pieni di grasso e zucchero, hanno anche le uova: senza, collasserebbero.

Un dettaglio nascosto: il tuorlo accelera un po' la fermentazione

Una curiosità utile: il tuorlo è ricco di amilasi — lo stesso enzima della farina che spezza l'amido in zuccheri. Quindi le uova danno al lievito un po' di cibo in più e possono accelerare leggermente la fermentazione e la doratura. È un effetto minore rispetto al freno di grasso e zucchero, ma va nella direzione opposta e aiuta a bilanciare.

Come lo verifichi

Guarda mollica, colore, tenuta. Mollica gialla, ricca, morbida → tuorli al lavoro. Pane che si affetta pulito e tiene → albume che struttura. Se è troppo denso, più tuorlo; se è troppo molle in lievitazione, più albume. E ricorda che le uova portano anche acqua (l'uovo è per due terzi acqua): se aggiungi uova, spesso devi togliere un po' di liquido dall'impasto.

Il bersaglio, letto bene

Non un numero di uova, ma l'equilibrio tenerezza/struttura giusto per il tuo pane, scelto dosando le due parti. Il bersaglio è capire cosa ti serve — morbidezza (tuorlo) o tenuta (albume) — e regolare di conseguenza, sapendo che l'uovo intero è il compromesso. E la cosa da ricordare, che nessuno ti dice: l'uovo non è un ingrediente, sono due, e la maestria è saperli usare separati.""",
            "target": "L'uovo è due ingredienti in uno: il tuorlo (grasso+lecitina) ammorbidisce ed emulsiona, l'albume (proteine) struttura e tiene · scegli la parte per l'effetto: denso→più tuorlo, molle→più albume",
            "nome": "Le uova nell'impasto",
            "dominio": "panificazione",
        },
        "fen-zuccheri-impasto": {
            "scheda": """Un cucchiaino di zucchero nell'impasto del pane in cassetta lo fa lievitare meglio e dorare di più. Ma prova a fare una brioche, piena di zucchero, e scopri il paradosso: più zucchero metti, più lenta diventa la lievitazione, fino a fermarsi. Lo stesso ingrediente prima aiuta il lievito e poi lo strozza. Capire quando cambia segno è la chiave degli impasti dolci.

Lo zucchero nell'impasto fa più cose insieme — come i grassi, ma con una particolarità: il suo effetto sul lievito si rovescia a seconda di quanto ne metti. È il fenomeno che governa tutti gli impasti dolci, dal pane in cassetta al panettone.

La doppia faccia sul lievito: prima cibo, poi veleno

Questo è il cuore, ed è controintuitivo. Lo zucchero è il cibo diretto del lievito: una piccola quantità (indicativamente fino al 5% sulla farina) gli dà nutrimento immediato e accelera la fermentazione — il pane lievita prima e meglio. Ma oltre una soglia (intorno al 10%) l'effetto si rovescia: lo zucchero, sciogliendosi, crea pressione osmotica e comincia a tirare l'acqua fuori dalle cellule del lievito. Il lievito si disidrata, si raggrinzisce, rallenta — e se lo zucchero è tantissimo, muore. È lo stesso meccanismo osmotico del sale, e lo stesso principio dei grassi che soffocano il lievito: troppo di una buona cosa la ribalta. Ecco perché una brioche o un panettone lievitano lentissimi, e il fornaio corre ai ripari: più lievito, o un lievito speciale "osmotollerante", allevato apposta per resistere agli ambienti zuccherini.

L'effetto sul glutine: ammorbidisce (come i grassi, ma per un'altra via)

Anche lo zucchero ammorbidisce l'impasto e lo rende più estensibile, come i grassi — ma il meccanismo è diverso. Lo zucchero è igroscopico, avido d'acqua, e compete con il glutine per l'acqua disponibile: lega le molecole d'acqua e le sottrae alle proteine, che così si idratano e si legano meno. Il risultato è un glutine più debole e una mollica più tenera. Poco zucchero dà una briciola fine e compatta (pane in cassetta, panini); tanto zucchero dà una struttura soffice e ariosa (brioche, dolci). Ma oltre il 10% la competizione per l'acqua diventa eccessiva: il glutine non si sviluppa più bene, la struttura cede. Per questo gli impasti molto dolci richiedono più lavoro, a volte glutine aggiunto, per reggere.

Il colore: lo zucchero è carburante per la crosta

Qui il legame diretto con la crosta. Lo zucchero promuove la doratura in due modi: alimenta la reazione di Maillard (con gli amminoacidi) e, in quantità, caramellizza. Ecco perché gli impasti dolci dorano splendidamente e i magri restano pallidi — è il rovescio del caso della crosta pallida. Se un pane non colora, poco zucchero (residuo o aggiunto) è una delle cause; un impasto ricco di zucchero, al contrario, rischia di scurire troppo in fretta.

L'umidità: tiene il pane morbido più a lungo

Come i grassi, lo zucchero è idrofilo e trattiene acqua: lega l'umidità nella mollica e ne rallenta la fuga. Un pane zuccherino resta morbido e fresco più giorni — è uno dei motivi per cui il pan brioche e il pane in cassetta durano più di una baguette. L'acidità e i grassi facevano lo stesso: lo zucchero è un altro alleato contro il raffermire.

Un dettaglio che sorprende: il saccarosio "sparisce"

Una curiosità che spiega molte cose: quando c'è il lievito, il saccarosio (lo zucchero da tavola) non resta dolce — il lievito ha un enzima, l'invertasi, che lo spezza subito in glucosio e fruttosio e comincia a mangiarlo. Quindi in un impasto lievitato lo zucchero che aggiungi viene in gran parte consumato: la dolcezza finale è meno di quella che immagini, perché il lievito se ne prende una fetta. Se vuoi dolcezza che resta, ne serve abbastanza da saziare il lievito e avanzare.

Come lo verifichi

Guarda lievitazione, mollica, colore. Impasto dolce che lievita lentissimo → pressione osmotica, ti serve più lievito o osmotollerante. Mollica che collassa, slegata → troppo zucchero per il glutine. Crosta che scurisce troppo in fretta → tanto zucchero, abbassa la temperatura o accorcia. Crosta pallida su un pane magro → aggiungi un filo di zucchero (o latte) per la doratura.

Il bersaglio, letto bene

C'è una soglia da conoscere più che un numero unico: sotto il ~5% lo zucchero aiuta il lievito e la doratura senza problemi; oltre il ~10% comincia a frenare lievito e glutine per via osmotica e competizione per l'acqua, e devi compensare (più lievito, osmotollerante, più lavoro). Il bersaglio è la dose giusta per l'effetto che vuoi — poco per un pane che lievita svelto e dora bene, tanto per una brioche soffice sapendo che paghi in tempo e tecnica. E la cosa da ricordare: lo zucchero è amico del lievito solo fino a un certo punto, poi diventa il suo nemico osmotico.""",
            "target": "La doppia faccia sul lievito: sotto ~5% lo nutre e accelera, sopra ~10% lo strozza per osmosi · ammorbidisce il glutine (competizione acqua), colora la crosta, trattiene umidità · dolci → lievito osmotollerante",
            "nome": "Gli zuccheri nell'impasto",
            "dominio": "panificazione",
        },
        "fen-grassi-impasto": {
            "scheda": """Fai due impasti uguali, in uno metti un filo d'olio. Quello con l'olio si stende docile fino ai bordi della teglia senza ritirarsi, cuoce più morbido, e il giorno dopo è ancora soffice. L'altro combatte quando lo tiri, viene più gommoso, indurisce prima. Un cucchiaio d'olio ha cambiato tutto — e dietro c'è un solo fenomeno, semplice, da cui discende ogni differenza.

I grassi — olio d'oliva, strutto, burro — nell'impasto fanno una cosa sola a livello fisico, e da quella nascono tutti i loro effetti. Capire quel meccanismo unico ti fa prevedere cosa succede ogni volta che aggiungi grasso, dalla pizza in teglia alla focaccia ai panini all'olio.

Il meccanismo: il grasso riveste il glutine

Ecco il cuore. Quando lavori il grasso nell'impasto, le sue molecole rivestono i filamenti di glutine — quella rete di glutenina e gliadina che conosci. È come mettere una guaina scivolosa e impermeabile intorno a ogni filamento. Questo rivestimento fa due cose insieme: impedisce ai filamenti di legarsi troppo strettamente tra loro, e li fa scivolare uno sull'altro. Tutto quello che l'olio fa nell'impasto viene da qui — dal grasso che si interpone tra le proteine.

I quattro effetti, tutti dallo stesso meccanismo

Uno: mollica più tenera (lo "shortening"). Rivestiti dal grasso, i filamenti di glutine si legano di meno e restano più corti — in inglese "shortening", da cui il nome del grasso da forno. Un glutine più corto non si allunga tanto e non diventa gommoso: la mollica è più tenera, più fine, "scioglievole". È il motivo per cui un panino all'olio è morbido dove una baguette magra è masticabile.

Due: impasto più docile da stendere. Il grasso lubrifica: le particelle scivolano, l'impasto diventa più estensibile e meno elastico — si allunga e non si ritira. È esattamente ciò che serve alla pizza in teglia: deve allargarsi fino agli angoli e restarci, senza tirare indietro. Senza olio un impasto a bassa idratazione combatte; con l'olio si distende docile. Stessa cosa per la focaccia.

Tre: resta morbido più a lungo. Il grasso è idrofobo, respinge l'acqua. Rivestendo farina e mollica, rallenta l'evaporazione dell'acqua in cottura e la sua migrazione dopo — così il pane trattiene umidità e indurisce più lentamente. È il legame diretto con la vita del pane: i prodotti all'olio raffermiscono più tardi. Ecco perché i panini all'olio sono ancora soffici il giorno dopo.

Quattro: crosta diversa. Il grasso ammorbidisce anche la crosta, la rende meno dura e vetrosa, più tenera — e aiuta doratura e colore. Una focaccia unta di olio ha quella crosta dorata e morbida, non il guscio croccante del pane magro.

La trappola: troppo grasso rovescia il gioco

Come sempre, è un equilibrio. Un po' di grasso ammorbidisce e rende docile; troppo, e il rivestimento diventa eccessivo: i filamenti di glutine non riescono più a legarsi affatto, la struttura si indebolisce, l'impasto diventa slegato, si strappa, non tiene il gas. Oltre una certa soglia non hai più un pane morbido, hai un impasto che non sta insieme. E c'è un secondo rischio: troppo grasso, aggiunto troppo presto, incapsula il lievito e lo soffoca — non riesce a nutrirsi, e la lievitazione rallenta.

La leva del "quando": la regola del grasso ritardato

Qui una tecnica che viene dritta dal meccanismo. Se aggiungi il grasso all'inizio, prima di sviluppare il glutine, la rete si forma già rivestita e resta corta: mollica molto tenera, quasi da torta (è come si fa la brioche soffice). Se invece lasci sviluppare il glutine prima e aggiungi il grasso alla fine, la rete è già formata e forte, e il grasso la ammorbidisce senza impedirle di reggere: ottieni una mollica più aperta e strutturata ma comunque tenera. Il quando metti il grasso decide il tipo di mollica. Per una pizza in teglia o una focaccia con alveolatura si tende a ritardarlo; per un pan brioche si mette prima.

Come lo verifichi

Con le mani e in bocca. L'impasto con la giusta dose di grasso si stende docile, non si ritira, è setoso al tatto. Cotto: mollica tenera e umida, crosta morbida, e resta soffice il giorno dopo. Se l'impasto è slegato e si strappa, o non lievita bene, probabilmente c'è troppo grasso o l'hai messo troppo presto: riduci o ritarda.

Il bersaglio, letto bene

C'è una finestra: per la maggior parte dei pani il grasso sta indicativamente tra il 2 e il 5% sulla farina; sale negli impasti arricchiti (focacce unte, brioche). Sotto, l'effetto è appena percettibile; sopra la finestra, sempre più tenero fino al punto in cui la struttura cede. Il bersaglio non è "quanto grasso" in astratto, ma la combinazione di dose e momento giusti per l'effetto che vuoi: poco e ritardato per una teglia alveolata e docile, di più e anticipato per una mollica soffice da brioche. Un solo meccanismo — il grasso che riveste il glutine — e tu lo governi scegliendo quanto e quando.""",
            "target": "Un meccanismo (il grasso riveste il glutine) → quattro effetti: mollica tenera, impasto docile da stendere, resta morbido più a lungo, crosta tenera · finestra ~2-5% · conta anche QUANDO lo aggiungi",
            "nome": "I grassi nell'impasto (shortening)",
            "dominio": "panificazione",
        },
        "fen-enzimi-farina": {
            "scheda": """Il lievito mangia zuccheri, ma nella farina di zuccheri quasi non ce n'è: è quasi tutto amido. Allora da dove viene il cibo del lievito? Da enzimi già presenti nella farina, che spezzano l'amido in zuccheri mentre l'impasto riposa. Sono un motore invisibile: non li vedi, ma decidono quanto lievita il pane e quanto scurisce la crosta. E come tutti i motori, vanno né spenti né imballati.

Gli enzimi della farina — soprattutto le amilasi — fanno una cosa sola ma decisiva: trasformano l'amido in zuccheri che il lievito può mangiare. È l'attività diastatica, e sta sotto tutto quello che fa il pane: la fermentazione ha carburante grazie a loro, e la crosta prende colore grazie agli zuccheri che lasciano.

La sequenza: da amido a zucchero, in due tempi

L'amido non diventa zucchero in un colpo. Due enzimi lavorano in sequenza. L'alfa-amilasi attacca le lunghe catene di amido e le taglia in pezzi medi, le destrine. Poi la beta-amilasi prende le destrine e le rifinisce in maltosio, lo zucchero semplice che il lievito metabolizza. È una catena di montaggio: uno sgrossa, l'altro rifinisce. Senza questa conversione, il lievito resterebbe senza cibo e il pane non lieviterebbe.

Un dettaglio che sorprende: l'alfa-amilasi non tocca l'amido intatto — lavora solo su quello danneggiato o gelatinizzato. E l'amido si danneggia durante la macinatura: una piccola frazione dei granuli (indicativamente il 5-9%) si spacca sotto le macine, e proprio quei granuli rotti vengono attaccati mille volte più in fretta di quelli integri. Quindi anche come è stata macinata la farina conta.

Il cuore: è un equilibrio, né troppo né troppo poco

Qui sta la cosa da capire, ed è puro buon senso reso preciso. L'attività degli enzimi non è "più ce n'è meglio è": è una finestra. Se è troppo bassa, l'impasto fatica — poco zucchero, fermentazione lenta, e crosta pallida (mancano gli zuccheri per la doratura, esattamente il problema del pane che non colora). Se è troppo alta, il disastro opposto: gli enzimi producono troppe destrine, la beta-amilasi non sta dietro, l'impasto diventa appiccicoso, molliccio, ingestibile, e la mollica esce gommosa. Troppo poco e il pane è spento; troppo e collassa. Il bello è nel mezzo.

Dove lo incontri, anche senza saperlo

Non devi dosare enzimi a mano per farci i conti. Li governi ogni volta che scegli una farina: le farine variano nella loro attività enzimatica, e alcune sono "maltate" — cioè addizionate di malto diastatico (che è amilasi più un po' di proteasi) proprio per portare l'attività nella finestra giusta. Il malto diastatico è il trucco dei fornai per le farine povere di enzimi: un pizzico dà al lievito più cibo e alla crosta più colore. Ma è potente e variabile: troppo, e ricadi nell'impasto appiccicoso.

Come lo verifichi

Al banco, senza strumenti, lo leggi dai sintomi: impasto costantemente lento a lievitare, mollica densa, crosta pallida → farina probabilmente povera di enzimi. Impasto inspiegabilmente appiccicoso e molle, crosta che scurisce troppo in fretta → forse attività troppo alta. E c'è una misura vera, quella che usano i molini: il Falling Number, un test che misura proprio l'attività dell'alfa-amilasi.

Il bersaglio, letto bene

Qui c'è un numero difendibile, ma con una trappola: il Falling Number, misurato in secondi, ha una relazione INVERSA con l'attività. Numero basso = attività alta (gli enzimi fluidificano in fretta la pasta di prova); numero alto = attività bassa. Per le farine da pane il punto giusto sta indicativamente tra 220 e 260 secondi. Non è un valore che imposti tu — è una proprietà della farina che ricevi — ma sapere che esiste, e che più basso significa più attivo (non meno), ti fa leggere una scheda tecnica della farina e capire come si comporterà. Il bersaglio è una farina dentro quella finestra; fuori, sai già cosa aspettarti — pallida e lenta se il numero è alto, appiccicosa se è troppo basso.""",
            "target": "Un equilibrio: troppo pochi enzimi = pane pallido e lento, troppi = impasto appiccicoso e gommoso · si misura col Falling Number (relazione INVERSA: basso = attività alta), sweet spot pane ~220-260s",
        },
        "fen-maglia-glutinica": {
            "scheda": """Impasti due volte lo stesso pane. Una volta lavori poco: l'impasto è slegato, si strappa, non tiene. Un'altra lavori troppo: diventa duro, gommoso, si ritira e combatte, non si lascia stendere. In mezzo c'è il punto giusto — un impasto che si allunga docile ma tiene la forma. Quel punto è un equilibrio tra due forze opposte dentro il glutine, e riconoscerlo è metà del mestiere del pane.

La maglia glutinica è la rete di proteine che dà struttura al pane: trattiene il gas della fermentazione e fa sì che l'impasto lieviti e tenga la forma. Ma per governarla devi sapere che non è "una cosa sola forte o debole" — è fatta di due proteine con caratteri opposti, e il pane vive nel loro equilibrio.

Le due forze: elasticità ed estensibilità

Il glutine nasce da due proteine della farina, la glutenina e la gliadina, e fanno cose diverse. La glutenina dà elasticità: l'impasto resiste, torna indietro quando lo stiri, come un elastico. La gliadina dà estensibilità: l'impasto si allunga, si stende sotto pressione senza spezzarsi. Sono opposte e complementari. Troppa elasticità e l'impasto è duro, nervoso, si ritira e non si lascia lavorare; troppa estensibilità e è molle, cede, non tiene la forma. Il pane vuole entrambe in equilibrio: abbastanza elasticità per tenere la struttura e trattenere il gas, abbastanza estensibilità per espandersi mentre il lievito lo gonfia. Quasi tutti i problemi di un impasto — troppo duro, troppo molle — sono uno sbilanciamento tra queste due.

Perché il glutine si forma: acqua, poi lavoro (o tempo)

Una cosa fondamentale: nella farina asciutta il glutine non esiste. Glutenina e gliadina stanno lì dormienti, separate. Serve l'acqua per svegliarle — si idratano, si distendono, cominciano a muoversi e a legarsi. Poi serve che si colleghino in catene lunghe, e questo succede in due modi: con l'azione meccanica (impastare, piegare) oppure — ed è il ponte con l'autolisi — semplicemente col tempo. Le proteine si organizzano anche da sole, se le lasci in acqua abbastanza a lungo. Impastare accelera; il riposo fa lo stesso lavoro più piano. Per questo esistono i pani senza impasto: sviluppano il glutine con idratazione e attesa invece che con la forza.

Le leve che governano l'equilibrio

La farina (più proteine = più glutine potenziale; ma conta il rapporto elastico/estensibile, non solo la quantità — farine fortissime danno impasti troppo tenaci, difficili da stendere). L'acqua (l'idratazione è il primo passo: più acqua tende a mollica più aperta e impasto più estensibile, meno acqua a mollica più fitta e impasto più tenace). Il lavoro (più impasti, più la rete si rafforza — ma oltre un punto l'impasto diventa troppo tenace o, spinto all'estremo, si degrada). Il riposo (rilassa la rete, la distribuisce, la rende più estensibile — è la stessa autolisi). E gli additivi che conosci: il sale stringe e rinforza il glutine; grassi e zuccheri lo ammorbidiscono; gli acidi lo indeboliscono.

Come lo verifichi: il windowpane

C'è una prova diretta, ed è il modo standard: il windowpane test. Prendi un pezzetto di impasto e allargalo delicatamente tra le dita. Se il glutine è sviluppato bene, si stende in un velo sottile, quasi trasparente, senza rompersi — vedi la luce attraverso, come un vetro. Se si strappa subito, la rete non è pronta: serve più lavoro o più riposo. È il test che ti dice, con le mani, se l'equilibrio c'è. Ma attenzione: non tutti i pani vogliono un windowpane perfetto — i rustici e gli impasti molto idratati danno ottimi risultati anche con uno sviluppo moderato. Il test è una guida, non un dogma.

Il bersaglio, letto bene

L'equilibrio giusto tra elastico ed estensibile per il pane che stai facendo — riconosciuto con le mani, non su una scala. Un pane in cassetta vuole più struttura, una ciabatta più estensibilità e mollica aperta, un grissino più tenacia. Il bersaglio è quel punto in cui l'impasto si stende docile ma tiene, e lo senti stendendolo (il windowpane) più che leggendo un numero. E la cosa da ricordare sopra tutte: quando un impasto ti combatte o ti cede, non è "poco glutine" in astratto — è troppo di una delle due forze. Chiediti quale, elastica o estensibile, e correggi quella.""",
            "target": "L'equilibrio tra elastico (glutenina, torna indietro) ed estensibile (gliadina, si allunga) · quando l'impasto combatte o cede è troppo di una delle due — chiediti quale · lo verifichi col windowpane",
        },
        "fen-tannini": {
            "scheda": """Bevi un rosso giovane o un tè lasciato in infusione troppo a lungo, e la bocca ti si asciuga: le gengive tirano, la lingua diventa ruvida, senti come una carta vetrata. La chiami "amaro", ma non è amaro. È astringenza, ed è un'altra cosa — un altro senso, un altro meccanismo. Separarle è la prima cosa che ti fa capire cosa hai nel bicchiere.

I tannini sono polifenoli, una famiglia di composti presenti in vino, tè, cacao, caffè, buccia e semi della frutta, e nel legno delle botti. Danno quella sensazione secca e allappante. Ma per governarli devi prima capire che l'astringenza che senti non è un gusto: è un fatto tattile, fisico, in bocca.

Astringenza non è amaro: due cose diverse

L'amaro è un gusto — lo senti sui recettori del gusto, arriva subito e passa. L'astringenza è una sensazione tattile — la senti come texture, secchezza, rasposità. E hanno un meccanismo completamente diverso. L'astringenza nasce così: i tannini si legano alle proteine della tua saliva, quelle che normalmente rendono la bocca scivolosa e lubrificata. Legandole, le fanno precipitare, e la bocca perde lubrificazione: ecco la secchezza, il "tirare". Non è un sapore che percepisci, è la tua saliva che smette di scorrere. Per distinguerle a mente, guarda la texture sulla lingua, non il sapore: se la bocca si raggrinza e stringe, è astringenza; se è un gusto amaro, è amaro.

Perché si costruisce sorso dopo sorso

C'è una conseguenza pratica di questo meccanismo. L'amaro arriva in un istante e finisce. L'astringenza, invece, si accumula: a ogni sorso i tannini consumano altre proteine salivari, e la bocca si asciuga sempre di più. Ecco perché un rosso molto tannico o un tè troppo forte diventano più allappanti verso la fine del bicchiere che all'inizio — non è che il vino cambia, è la tua saliva che si esaurisce. E c'è una differenza tra le persone: chi produce poca saliva sente l'astringenza più forte.

Non tutti i tannini sono uguali: la dimensione conta

I tannini non sono una cosa sola: sono molecole che si legano tra loro in catene di lunghezza diversa (è il grado di polimerizzazione). E qui c'è una relazione utile: più il tannino è grande e polimerizzato, più è astringente e meno amaro; più è piccolo, più tende all'amaro e meno all'astringente. È il motivo per cui tannini di origine diversa — uva, tè, legno, semi — danno sensazioni diverse: non è solo "quanti" ma "quanto grandi". Ed è anche il motivo per cui un vino, invecchiando, cambia: i tannini si riorganizzano e la sensazione si ammorbidisce.

Le leve che hai davvero

L'astringenza non è per forza un difetto: in un grande rosso può diventare struttura, pienezza, sensazione vellutata — è quando è sbilanciata o troppo aggressiva che disturba. Quindi il gioco è governarla, non azzerarla. Le leve: la quantità di tannino che estrai (nel vino, più macerazione su bucce e semi = più tannino; nel tè, più tempo e più caldo = più tannino; sono estrazioni, valgono le regole dell'estrazione). Il tempo e l'invecchiamento (i tannini si ammorbidiscono col tempo, in bottiglia o in caraffa con l'aria). La temperatura di servizio (un rosso molto tannico servito a temperatura ambiente sembra meno aggressivo che freddo). E l'abbinamento: grassi e proteine nel cibo legano i tannini e ammorbidiscono l'astringenza — per questo un rosso tannico "si apre" con una bistecca.

Come lo verifichi

Il giudice è la bocca, ma devi sapere cosa cercare: la secchezza e il "tirare" (astringenza) separati dal gusto amaro. Un modo pratico: fai passare qualche secondo dopo il sorso e senti se la bocca si asciuga progressivamente — quella è l'astringenza che si costruisce. E se vuoi capire cosa la governa nel tuo caso, cambia una cosa per volta: stesso tè con un minuto in meno di infusione, o stesso rosso lasciato ossigenare — e senti come cambia l'allappante.

Il bersaglio, letto bene

Non c'è un numero dell'astringenza, e non c'è un "giusto" universale: un rosso da bistecca vuole struttura tannica, un tè da pomeriggio la vuole leggera, un cocktail ne vuole appena un accenno. Il bersaglio è l'astringenza giusta per quello che stai facendo, in equilibrio con dolcezza, acidità e corpo — ricordando che un po' di tannino dà struttura, troppo asciuga e stanca. Lo riconosci in bocca, come texture, non su una tabella. E ricorda la cosa che conta di più: quando qualcosa "allappa", non è un sapore da coprire con lo zucchero — è una sensazione fisica da bilanciare o ammorbidire.""",
            "target": "Nessun numero: l'astringenza giusta per l'uso (struttura in un rosso, accenno in un cocktail) · è tattile non gusto, si costruisce sorso dopo sorso · non coprire con lo zucchero",
        },
        "fen-calore": {
            "scheda": """Metti una bistecca spessa in forno rovente e la tiri fuori bruciata fuori e cruda dentro. Alzi la fiamma pensando di andare più veloce, e peggiori le cose. Il problema è che stai confondendo tre cose che sembrano una: quanto è caldo (temperatura), quanta energia stai dando (calore), e quanto in fretta arriva al centro (velocità). Separarle è capire perché il calore fa quello che fa.

Il calore governa mezzo mestiere: cuoce, scioglie, estrae, fa fermentare più in fretta o più piano, raffredda un cocktail. Ma per governarlo davvero devi smettere di pensarlo come "una manopola" e vedere le tre grandezze distinte che ci stanno dentro.

Temperatura non è calore non è velocità

La temperatura è quanto sono agitate le molecole in un punto — è il numero sul termometro. Il calore è l'energia che passa da un corpo caldo a uno freddo. La velocità è quanto in fretta quell'energia arriva dove ti serve. Sono legate ma diverse, e l'errore classico è credere che più temperatura significhi sempre più veloce. Non è così: la temperatura interna di una bistecca non sale in proporzione a quanto è caldo il forno, perché il collo di bottiglia non è quanto scalda la superficie — è quanto lentamente il calore attraversa il cibo. Alzare la fiamma brucia la superficie senza far arrivare il centro più in fretta.

Perché il centro resta indietro: la conduzione nel cibo

Il motivo sta in come il calore viaggia dentro le cose. Nel cibo, molecola dopo molecola: quelle calde vibrano, urtano le vicine, gli passano energia, e così il calore si fa strada verso l'interno. Ma il cibo è per lo più acqua, e l'acqua conduce il calore circa 25 volte peggio dell'acciaio. Il cibo è un pessimo conduttore. Ecco perché l'esterno può diventare rovente mentre il centro è ancora freddo: il calore deve farsi strada lentamente attraverso un materiale che gli resiste. Quel gradiente — caldo fuori, freddo dentro — non è un difetto, è la fisica di ogni cottura, e saperlo governare è la tecnica.

I tre modi in cui il calore arriva

Il calore raggiunge il cibo in tre modi, e cambiano il risultato. La conduzione è contatto diretto: la padella tocca la carne, l'energia passa per contatto. La convezione è il calore portato da un fluido in movimento: l'aria del forno ventilato, l'acqua che bolle, l'olio della frittura — il fluido caldo si muove e lambisce il cibo. L'irraggiamento è il calore che viaggia come onda, senza contatto: la brace, la salamandra, il grill dall'alto. Quasi sempre lavorano insieme, ma sapere quale domina ti dice cosa aspettarti: la conduzione fa la crosta dove tocca, la convezione cuoce uniforme, l'irraggiamento colora la superficie.

Il trucco nascosto: il calore latente

C'è un caso che sembra magia e invece è fisica: il vapore scotta molto più dell'acqua bollente, pur essendo entrambi a 100°C. Perché? Quando il vapore condensa sul cibo rilascia una quantità enorme di energia — il calore latente, quello che era servito a trasformare l'acqua in vapore e che torna fuori tutto insieme condensando. È lo stesso motivo per cui il ghiaccio raffredda un drink sciogliendosi (assorbe calore latente per fondere, l'hai visto nella diluizione), o per cui un getto di vapore nel forno accelera la crosta del pane. Il cambio di stato — solido/liquido/gas — sposta molta più energia del semplice scaldare.

Le leve, in pratica

La temperatura del mezzo (quanto caldo), ma sapendo che oltre un certo punto non accelera il centro, brucia solo fuori. Il tempo (il calore ha bisogno di tempo per attraversare — spesso la leva vera è aspettare, non alzare). Il mezzo e il meccanismo (acqua, olio, aria, vapore, contatto: cambiano velocità e risultato — l'olio va sopra i 100°C e fa la crosta, l'acqua no). La dimensione e la superficie (un pezzo spesso vuole più tempo perché il centro è lontano; tagliare più piccolo avvicina il centro). E dalla parte del freddo vale specularmente: raffreddare è togliere calore, e più freddo rallenta le reazioni (è il Q10 — ogni 10°C in meno le reazioni all'incirca dimezzano).

Come lo verifichi

La temperatura al centro, non la superficie né il tempo sull'orologio: un termometro a sonda ti dice la sola cosa che conta davvero in molte cotture, la temperatura del cuore. Se il fuori è pronto e il dentro no, non alzi la fiamma: abbassi e aspetti, o fai un pezzo più piccolo. Cambi una leva per volta e guardi come si muove il centro.

Il bersaglio, letto bene

Qui non c'è un numero solo: il calore è multi-parametro, sempre almeno temperatura + tempo + mezzo insieme. 60°C per un'ora nell'acqua non è come 200°C per dieci minuti in forno, anche se "cuociono" la stessa cosa. Il bersaglio è la combinazione giusta di quanto caldo, per quanto tempo, con quale mezzo, per portare il centro dove vuoi senza distruggere la superficie. E la cosa da ricordare sopra tutte: quando il fuori corre e il dentro resta indietro, il problema non è poco calore — è troppo in fretta. Rallenta.""",
            "target": "Multi-parametro: temperatura + tempo + mezzo insieme · 60°C/1h ≠ 200°C/10min · verifica al cuore non in superficie · se fuori corre e dentro resta indietro, rallenta non alzare",
        },
    }
    SCHEDE_MADRI_NUOVE2 = {
        "fen-distillazione": {
            "scheda": """Un distillato nasce da una separazione. Scaldi un liquido fermentato e i suoi componenti evaporano in ordine — prima i più volatili, poi l'alcol buono, infine i più pesanti — e il distillatore raccoglie solo la parte giusta, buttando la prima e l'ultima. Quella scelta, dove tagliare, decide tutto: il carattere, la pulizia, persino la sicurezza. Capirla ti fa capire cosa hai davvero nel bicchiere.

La distillazione separa i componenti di una miscela sfruttando il fatto che bollono a temperature diverse. Nel mosto fermentato non c'è solo etanolo e acqua: c'è una folla di composti diversi, ognuno col suo punto di ebollizione. Scaldando, evaporano in sequenza — e il mestiere del distillatore è decidere quali tenere.

Teste, cuore, code: la separazione per volatilità

Man mano che scaldi, il vapore che sale cambia composizione. Prima escono le teste: i composti più volatili, col punto di ebollizione più basso — acetone, aldeidi, e soprattutto metanolo. Sanno di solvente, di smalto, e sono da scartare. Poi arriva il cuore: principalmente etanolo, l'alcol buono, pulito, con i composti aromatici desiderabili. È la parte che si tiene. Infine le code: i composti più pesanti, gli oli di flemma (fusel oil), che danno sapori grezzi, oleosi, "cartone bagnato". Anche queste si separano. Il distillatore devia il flusso per raccogliere solo il cuore: è questo il senso di "fare i tagli".

Perché il taglio è arte, non aritmetica

Verrebbe da pensare: se ogni composto ha il suo punto di ebollizione, basta un termometro. Ma non è così, ed è la cosa più interessante. I composti non escono in blocchi netti: si sovrappongono, sfumano l'uno nell'altro. Il metanolo e l'etanolo, per dire, sono come fratelli — le loro molecole si aggrappano tra loro, e nonostante i punti di ebollizione diversi sono notoriamente difficili da separare del tutto. Per questo il distillatore non si fida solo del termometro: usa naso e palato. Sente quando le teste da solvente lasciano il posto al carattere pulito e dolce del cuore, e quando il cuore comincia a sporcarsi verso le code. Il taglio è una decisione sensoriale, e lì sta l'arte.

La sicurezza: perché le teste si buttano davvero

C'è una ragione seria dietro lo scartare le teste, non solo il sapore. Le teste concentrano il metanolo, che è tossico: attacca il nervo ottico e il fegato, e in quantità anche piccole può causare cecità o peggio. Nei distillati fatti a regola d'arte il metanolo residuo è entro limiti di sicurezza precisi (le normative fissano soglie basse) — ed è proprio il taglio corretto delle teste a garantirlo. Questo è anche il motivo per cui distillare non è un gioco da fare in casa senza competenza: la separazione che rende un distillato sicuro è tecnica, non improvvisazione. Per te dietro il banco, il senso è capire perché un distillato di qualità è quello che è: qualcuno ha fatto i tagli giusti.

Cosa cambia da distillato a distillato

Non tutti i distillati vogliono lo stesso taglio. Una vodka neutra vuole un cuore strettissimo e purissimo, teste e code tagliate larghe, per non avere quasi carattere. Un whisky o un rum da invecchiare tengono un po' più di composti aromatici (anche parte delle code buone) perché daranno complessità con l'affinamento. Un gin costruisce il suo carattere sulle botaniche infuse e ridistillate. Lo stesso principio — separa per volatilità, scegli il cuore — dà prodotti diversissimi a seconda di dove metti i tagli e cosa c'era nel mosto.

Come lo "verifichi" (al banco)

Tu non distilli, ma leggi il risultato. Un buon distillato nel cuore è pulito: niente pungente di solvente (teste rimaste), niente oleoso-grezzo o "bagnato" (code rimaste). Se un distillato economico ti sembra aggressivo, pungente, che dà mal di testa facile, spesso è un taglio fatto male o largo. Il naso e il palato ti dicono se il cuore era davvero cuore.

Il bersaglio, letto bene

Non è un numero: è il cuore riconosciuto. Il bersaglio della distillazione è quel punto in cui hai solo etanolo e i composti aromatici che vuoi, senza il solvente delle teste né l'olio delle code — e cambia con l'obiettivo (purissimo per la vodka, aromatico per il whisky). Lo si riconosce al naso e al palato, non su una scala. E la cosa da portare a casa: dietro ogni distillato che ami c'è una decisione di taglio; la qualità di quello che versi nasce lì, nella scelta di cosa tenere e cosa buttare.""",
            "target": "Il cuore riconosciuto al naso/palato: solo etanolo e aromatici voluti, senza il solvente delle teste né l'olio delle code · il taglio è arte sensoriale, non termometro · cambia col prodotto (vodka purissima, whisky aromatico)",
        },
    }
    SCHEDE_APP = {**SCHEDE_APP, **CASI, **SCHEDE_MADRI_NUOVE, **SCHEDE_MADRI_NUOVE2}
    import json
    try:
        conn = _get_conn()
        cur = conn.cursor()
        updated = []
        for node_id, data in SCHEDE_APP.items():
            cur.execute("SELECT id, data FROM nodes WHERE id=%s", (node_id,))
            row = cur.fetchone()
            if not row:
                # nodo non esistente: lo CREO (casi proc-* nuovi, fenomeni nuovi)
                is_caso = node_id.startswith("proc-")
                ntype = "Processo" if is_caso else "Fenomeno"
                ndom = data.get("dominio", "trasversale")
                nname = data.get("nome") or node_id.replace("proc-", "").replace("fen-", "").replace("-", " ").capitalize()
                nd_new = {"scheda": data["scheda"], "target": data["target"],
                          "numero_bersaglio": data["target"]}
                cur.execute(
                    "INSERT INTO nodes (id, type, name, domain, data) VALUES (%s,%s,%s,%s,%s)",
                    (node_id, ntype, nname, ndom, json.dumps(nd_new, ensure_ascii=False)))
                updated.append(f"{node_id}: CREATO ({len(data['scheda'])} chars)")
                continue
            raw = row[1] if isinstance(row, (list, tuple)) else row["data"]
            nd = raw if isinstance(raw, dict) else json.loads(raw)
            sch = nd.get("scheda")
            if isinstance(sch, dict):
                sch["it"] = data["scheda"]; nd["scheda"] = sch
            else:
                nd["scheda"] = data["scheda"]
            nd["target"] = data["target"]
            nd["numero_bersaglio"] = data["target"]
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                        (json.dumps(nd, ensure_ascii=False), node_id))
            updated.append(f"{node_id}: OK ({len(data['scheda'])} chars)")
        conn.commit(); cur.close(); _release_conn(conn)
        try:
            from routes.lezione import _lezione_cache as _lc; _lc.clear()
        except Exception: pass
        try:
            from routes.lezione import _cache_home as _ch; _ch.clear()
        except Exception: pass
        n_ok = sum(1 for u in updated if ": OK" in u)
        return jsonify({"ok": True, "aggiornati_ok": n_ok, "totale": len(SCHEDE_APP), "dettaglio": updated})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/update-schede-v2")
def admin_update_schede_v2():
    """MIGRA le 24 schede-fenomeno alla versione METODO (VEDI/SEPARA/PERCHÉ/GOVERNA/
    VERIFICA/BERSAGLIO — architettura cognitiva, non definizioni da manuale).
    Sostituisce le vecchie schede stile-Wikipedia. Scrive nel campo scheda.it se il
    nodo è in formato multilingua {it,en,es}, altrimenti in scheda (legacy stringa).
    Il target è un numero-bersaglio METODO: finestra contestuale, mai numero-legge."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403

    SCHEDE_V2 = {
        "fen-acidita": {
            "scheda": """Lo stesso sour, lo stesso limone, la stessa dose. Un giorno ha spina, un giorno è piatto, un giorno aggredisce.

Non è il palato che cambia. È che sotto la parola "acido" si nascondono due misure diverse, e finché le tratti come una sola correggi i drink a naso. Separarle è ciò che ti fa sapere cosa stai correggendo.

Due misure, non una

Il pH descrive l'acidità attiva di una soluzione: l'attività degli ioni idrogeno liberi in quel momento. L'acidità titolabile misura un'altra cosa — la quantità di acido che si riesce a neutralizzare titolando con una base, cioè una misura del contenuto acido complessivo nelle condizioni della prova.

Non sono intercambiabili, e non si prevedono a vicenda: due succhi possono avere lo stesso pH e acidità titolabile diversa, perché il legame tra le due dipende da quali acidi ci sono e da quanto la soluzione "tampona", cioè resiste al cambio di pH. Il vino e il succo sono soluzioni tamponate: puoi aggiungere acido e veder muovere il pH pochissimo.

Quale delle due senti

Tra le due, l'acidità titolabile è di solito più strettamente legata all'asprezza che percepisci; il pH da solo la predice molto meno bene. In generale una maggiore acidità titolabile si accompagna a una maggiore asprezza percepita, ma la relazione cambia con la matrice — e due bevande allo stesso pH possono essere percepite diverse.

Ecco perché, quando un sour "non ha spina", spesso in gioco c'è l'acido totale, non il pH. Ma non farne un automatismo: l'asprezza che percepisci non dipende solo dall'acido. Zucchero e alcol la smorzano — la stessa acidità in un drink più dolce o più alcolico si sente meno. Quindi un drink piatto può volere più acido, oppure meno zucchero, oppure una diluizione diversa: sono leve diverse sullo stesso risultato. E ognuna, quando la tocchi, ne muove anche altre — meno acqua non cambia solo l'acido, cambia insieme zucchero, alcol e corpo.

Il pH allora a cosa ti serve

A un'altra domanda, non al gusto: la stabilità. Un pH più basso rende in genere l'ambiente più ostile ai microrganismi — per questo conta nelle conserve, nelle fermentazioni, nella shelf life. "In genere", non "sempre": la sicurezza dipende anche da temperatura, acqua disponibile, tempo e da quale microrganismo. Il pH è una delle variabili, non una garanzia da solo.

Come lo verifichi

Tieni separate due domande. Una è gustativa — "il risultato è quello che voglio?" — e si risponde assaggiando, meglio ancora confrontando due versioni una accanto all'altra. L'altra è tecnica — "quanto acido c'è davvero, e a che pH sono?" — e si risponde misurando. La regola non è "questa misura per il gusto, quella per la sicurezza": è scegliere la misura in base alla domanda che ti stai facendo. Il palato ti dice il risultato complessivo; non ti dice quale variabile l'ha prodotto. E qui sta il punto: se un drink cambia quando muovi una sola leva per volta, hai un'indicazione; se cambi acido, zucchero e diluizione insieme, sai che è cambiato qualcosa ma non cosa. Se devi replicare un batch identico domani, o mettere in sicurezza una conserva, il naso non basta: si misura.

Il bersaglio, letto bene

Non c'è un numero dell'acidità valido sempre, perché la percezione dipende da tutto il resto: zucchero, alcol, temperatura, tipo di acido. Quello che c'è è una finestra, dentro una preparazione precisa. In un sour, l'equilibrio è quando l'acido totale regge di fronte allo zucchero senza sovrastarlo — e quel punto lo trovi sulla tua ricetta, assaggiando, non copiando una percentuale. In pasta madre, dove sei tu a condurre la fermentazione mentre lavori, si lavora dentro una finestra di acidità controllata: se scende troppo, l'attività fermentativa tende a rallentare; se resta troppo alta, la maglia dell'impasto ne risente. Nel vino, invece, l'acidità si governa in vinificazione — a monte. È lì la fase in cui quella leva esiste; su una bottiglia finita non c'è più.""",
            "target": "Nessun numero universale: una finestra dentro la tua ricetta, trovata assaggiando · pH per la sicurezza, titolabile per l'asprezza",
        },
        "fen-concentrazione": {
            "scheda": """Raddoppi lo zucchero in uno sciroppo e non ti sembra il doppio più dolce. Servi lo stesso spritz freddo di frigo e tiepido, e tiepido sembra più dolce — stessa ricetta. Qualcosa non torna tra quanto zucchero c'è e quanto dolce lo senti.

Ed è proprio così: quanto ce n'è e quanto lo percepisci sono due cose diverse, e il mestiere vive nello spazio tra le due.

Quantità, concentrazione, intensità: tre cose che confondi in una

C'è la quantità totale di una sostanza (quanti grammi di zucchero in tutto). C'è la concentrazione, che è un rapporto: quanta sostanza per quanto liquido — ed è ciò che misuri col Brix, dove un grado equivale a circa un grammo di zucchero per cento grammi di soluzione. E c'è l'intensità percepita: quanto dolce lo senti in bocca. Sono tre piani diversi. Puoi cambiarne uno senza toccare gli altri come pensi: aggiungi acqua e la quantità totale di zucchero resta identica, ma la concentrazione scende — e con lei, di solito, la percezione.

Perché il doppio non sa di doppio

La percezione non segue la concentrazione in linea retta. Salendo di concentrazione servono aumenti sempre più grandi per far sentire una differenza: raddoppiare lo zucchero non raddoppia il dolce percepito, soprattutto quando sei già su valori alti. E c'è l'adattamento: più resti esposto a un gusto, meno lo senti — il terzo sorso dolce sembra meno dolce del primo, anche se nel bicchiere non è cambiato niente.

Per questo il numero sul rifrattometro e la sensazione in bocca non sono la stessa informazione. Il Brix ti dice quanto zucchero c'è, con precisione e ripetibilità. Non ti dice quanto dolce risulterà, perché la percezione la muovono anche altre cose.

Cosa sposta la percezione oltre alla concentrazione

La temperatura, prima di tutto: lo stesso liquido tende a sembrare più dolce da caldo che da freddo — ecco perché un drink corretto a temperatura ambiente può risultare stucchevole ghiacciato, e uno bilanciato freddo può sembrare piatto quando si scalda. Poi il contesto di gusto: acidità, amaro, sale, alcol spostano tutti quanto dolce percepisci a parità di zucchero. La concentrazione è una leva potente sulla percezione, ma non è l'unica che la governa.

Come lo verifichi

Anche qui tieni separate le due domande. "Quanto zucchero c'è davvero?" si misura — il rifrattometro (Brix) ti dà un numero solido, utile soprattutto per replicare uno sciroppo o un batch identico domani. "Quanto dolce risulta?" si assaggia, e va assaggiato nelle condizioni reali di servizio: alla temperatura a cui berrai il drink, dentro la miscela finita, non isolato. Un Brix misurato caldo e un drink bevuto ghiacciato ti diranno cose diverse. E se cambi una variabile per capire un risultato, cambiane una sola: se sposti insieme zucchero, acqua e temperatura, saprai che è cambiato il dolce ma non cosa l'ha spostato.

Il bersaglio, letto bene

Non c'è un Brix "giusto" universale, perché lo stesso valore viene percepito diverso al cambiare di temperatura, acidità e contesto. Quello che c'è è un doppio bersaglio, che conviene tenere distinto: un numero da colpire per la ripetibilità (uno sciroppo standard tende a stare intorno a un rapporto fisso zucchero-acqua, che misuri e ritrovi uguale ogni volta) e un equilibrio da assaggiare per il gusto (nel drink finito, alla sua temperatura). Il primo lo controlli con lo strumento perché sia sempre lo stesso; il secondo lo chiudi in bocca. Confonderli — inseguire il numero e ignorare l'assaggio, o viceversa — è il modo più comune per avere uno sciroppo perfettamente ripetibile in un drink che non funziona.""",
            "target": "Doppio bersaglio: un numero da colpire per la ripetibilità, un equilibrio da assaggiare per il gusto",
        },
        "fen-fermentazione": {
            "scheda": """Due impasti, stessa farina, stesso lievito madre, stessa dose. Uno lievita pieno e profumato, l'altro resta indietro e sa di acido. Non hai sbagliato ricetta: hai usato lo starter in due momenti diversi della sua vita.

Perché la fermentazione non è un interruttore che accendi. È un organismo vivo che attraversa fasi, e la stessa azione dà risultati diversi a seconda della fase in cui la fai.

Non un evento, una curva nel tempo

Quando aggiungi il lievito madre all'impasto, non parte subito a pieno regime. C'è una fase iniziale lenta — i microrganismi si "svegliano" e si adattano — poi una fase di piena attività in cui gonfiano e acidificano, poi un rallentamento quando il cibo scarseggia e i prodotti di scarto si accumulano. La forza dell'impasto dipende da dove sei su questa curva. E ogni volta che rinfreschi — prendi un po' di madre e la mescoli a farina e acqua fresca — la curva riparte da capo, dalla fase lenta. Usare la madre al culmine della sua attività o mentre è ancora indietro non è la stessa cosa, anche se il barattolo è lo stesso.

Perché il tempo e la temperatura sono la stessa leva vista da due lati

Dentro il range in cui i microrganismi lavorano, temperatura più alta significa fermentazione più veloce, temperatura più bassa più lenta: puoi ottenere lo stesso grado di maturazione con poche ore al caldo o molte al fresco. Non stai scegliendo "quanto tempo" separato da "quanto caldo" — stai scegliendo un punto su una stessa relazione. Ed è per questo che una madre lasciata al caldo troppo a lungo "scappa": non è che ha fermentato di più in senso buono, ha superato il culmine ed è già nella fase di declino, più acida e meno spinta.

C'è anche un anello di ritorno da conoscere: fermentando, i microrganismi producono acidi che abbassano il pH — e quel pH più basso, oltre un certo punto, rallenta loro stessi. Il processo frena da solo. Per questo "più tempo" non significa "più lievitazione": oltre un certo punto significa più acido e meno spinta.

La leva esiste solo mentre il processo è aperto

Questo è il punto che cambia come lavori: puoi governare la fermentazione solo finché è in corso. Temperatura, tempo, momento del rinfresco, idratazione, quantità di madre — sono leve che hai in mano mentre l'impasto è vivo e lavora. Una volta cotto, il processo è chiuso: nessuna correzione recupera una fermentazione partita male. Per questo un fermentatore esperto lavora in anticipo, preparando le condizioni davanti ai microrganismi invece di rincorrerli quando qualcosa è già andato storto.

Come lo verifichi

Il segnale che conta non è l'orologio, è lo stato dell'impasto. La ricetta dice "quattro ore", ma quattro ore a 22 gradi e a 26 non sono la stessa fermentazione — il tempo è un'indicazione, non il vero riferimento. Impari a leggere i segni della fase: volume, cupole e bolle, profumo (dal dolce-lattico al più acetico man mano che avanza), la prova che l'impasto regge la pressione del dito. Se vuoi capire una variabile, cambiane una sola tra un impasto e l'altro: se sposti insieme temperatura, tempo e quantità di madre, saprai che è cambiato il risultato ma non cosa l'ha spostato. E dove la sicurezza conta — una conserva, un fermentato che deve raggiungere un certo pH per essere stabile — il naso non basta: si misura il pH, perché lì il numero è una soglia di sicurezza, non una preferenza di gusto.

Il bersaglio, letto bene

Non c'è un tempo di fermentazione giusto in assoluto, perché dipende da temperatura, forza della madre, farina, quantità. Quello che c'è è uno stato da raggiungere, e diversi cammini per arrivarci. Una madre matura e attiva vive in una finestra di acidità bassa e controllata; ma il bersaglio vero non è un numero sull'orologio, è riconoscere il punto di massima spinta e usarla lì. Il tempo e la temperatura sono le due manopole con cui arrivi a quel punto quando ti serve — di notte al fresco, in giornata al caldo. Insegui lo stato, non l'ora.""",
            "target": "Non un tempo fisso ma uno stato da raggiungere: insegui il picco di attività, non l'orologio",
        },
        "fen-maillard": {
            "scheda": """Metti in padella una fetta di carne appena tolta dalla marinata e resta grigia, bollita, triste. La asciughi col panno e la rimetti nella stessa padella, stessa fiamma: si forma la crosta bruna, il profumo di arrosto. Non hai cambiato il calore. Hai tolto l'acqua.

La doratura non è "quanto scaldi". È una reazione che ha bisogno di più condizioni giuste insieme, e la temperatura è solo una di quelle.

Doratura non è caramello, e non è solo calore

Prima una distinzione che confonde in cucina: non tutto ciò che diventa bruno è la stessa cosa. La caramellizzazione è lo zucchero da solo che si scurisce ad alta temperatura. La reazione di Maillard è un'altra cosa — ha bisogno di due protagonisti insieme: zuccheri riducenti e amminoacidi (proteine). È l'incontro tra questi due, sotto calore, a creare la crosta e l'aroma di tostato, di arrosto, di pane. Per questo una bistecca e una cipolla dorano in modo diverso: hanno proteine e zuccheri in proporzioni diverse.

E qui la cosa che ribalta l'intuito: non basta il calore. Servono anche gli ingredienti giusti sulla superficie, il giusto grado di umidità, e conta pure il pH. Un ambiente meno acido favorisce la doratura, uno più acido la frena — ecco perché una marinata molto acida può rallentare la crosta.

Perché l'acqua è la vera nemica della crosta

Questo è il punto operativo più importante. Finché sulla superficie c'è acqua libera, la temperatura di quella superficie resta inchiodata vicino ai cento gradi — l'acqua che evapora "tiene fredda" la superficie. E la reazione che fa la crosta ha bisogno di temperature ben più alte per partire davvero. Finché la carne "suda", non dora: bolle nella sua stessa acqua. Solo quando la superficie si asciuga, la temperatura sale di colpo e la crosta parte.

È controintuitivo, ma un po' d'acqua serve alla reazione, troppa la blocca: c'è una finestra di umidità intermedia in cui va meglio, mentre in un ambiente fradicio rallenta. Ecco perché la padella affollata non rosola — troppa roba fredda e bagnata butta fuori acqua, la padella si raffredda, e tutto lessa invece di dorare.

Le leve che hai davvero

Se la crosta non arriva, "alza la fiamma" è solo una delle risposte, e spesso la peggiore. Prima chiediti quale condizione manca. Superficie bagnata? Asciuga, non affollare la padella, tampona la carne. Poco substrato? Un velo di zucchero o certe cotture cambiano ciò che c'è in superficie. Ambiente troppo acido? Il pH frena. E attento: ogni leva ne muove altre. Alzare troppo la fiamma dora la superficie prima che l'interno sia pronto, e oltre un certo punto la doratura buona diventa bruciato amaro — sono reazioni diverse, e il confine si supera in fretta.

Come lo verifichi

Il segno è sensoriale, e va letto con gli occhi e il naso più che con l'orologio: colore che vira dal dorato al bruno, il profumo che passa da "cotto" a "arrostito", la crosta che si stacca dalla padella quando è pronta (prima è attaccata, poi si libera). Ma attento a non confondere la doratura buona con l'inizio del bruciato: stesso colore che avanza, momenti diversi. E se vuoi capire cosa governa la tua crosta, cambia una condizione per volta — asciuga la superficie tenendo uguale la fiamma, oppure alza la fiamma tenendo la carne asciutta — non le due insieme, o non saprai quale ha fatto la differenza.

Il bersaglio, letto bene

Non c'è "il grado" della Maillard, perché la doratura dipende dall'insieme: temperatura, umidità della superficie, cosa c'è in quella superficie, pH. La reazione diventa di solito evidente in una finestra di temperature medio-alte, ma il bersaglio vero non è un numero sul termometro — è uno stato della superficie: asciutta, calda abbastanza, ricca dei giusti ingredienti. Quando queste condizioni ci sono insieme, la crosta arriva; se ne manca una, puoi alzare la fiamma quanto vuoi e ottenere solo bruciato fuori e crudo dentro. Insegui le condizioni, non il numero.""",
            "target": "Non un grado ma uno stato della superficie: asciutta, calda abbastanza, ricca dei giusti ingredienti",
        },
        "fen-emulsione": {
            "scheda": """Monti una vinaigrette, per un attimo è cremosa e legata, poi la lasci lì e in due minuti è di nuovo olio sopra e aceto sotto. Non hai sbagliato: hai creato qualcosa che, per sua natura, vuole tornare separato.

Un'emulsione non è uno stato stabile che ottieni una volta. È una tregua tra due liquidi che non vogliono stare insieme — e il mestiere è tenerli insieme abbastanza a lungo.

Due liquidi che si rifiutano, e un terzo che fa da paciere

Olio e acqua non si mescolano: lasciati soli, si separano sempre. Quando "emulsioni" non li fai diventare amici — spezzetti uno dei due in tante minuscole goccioline e lo tieni disperso nell'altro. Ma le goccioline, appena possono, si riavvicinano e si rifondono in gocce più grandi, finché le due fasi tornano separate. Ecco perché la vinaigrette si rompe.

Quello che tiene in piedi la tregua è un terzo elemento: l'emulsionante. È una sostanza che si piazza sulla superficie di ogni gocciolina e le impedisce di rifondersi con le altre — il tuorlo nella maionese, la senape nella vinaigrette, certe proteine. Senza di lui, la separazione è questione di secondi; con lui, di ore o giorni.

Perché si rompe (e cosa la tiene insieme)

La stabilità è una gara tra le goccioline che vogliono rifondersi e ciò che glielo impedisce. Tre cose spostano l'esito. La dimensione delle gocce: più le fai piccole — sbattendo, frullando, omogeneizzando — più l'emulsione regge, perché goccioline piccole si rifondono più a fatica. La copertura dell'emulsionante: deve essercene abbastanza da rivestire tutta la superficie delle gocce; se è poco, restano zone scoperte da cui la rottura parte. E la viscosità: un ambiente più denso rallenta il movimento delle goccioline, quindi le tiene separate più a lungo — per questo una salsa più corposa "tiene" meglio di una liquida.

C'è anche un nemico da conoscere: il calore. Scaldando, le goccioline si muovono di più e si rifondono più facilmente — ecco perché molte emulsioni si "impazziscono" sul fuoco. Il freddo in genere le protegge, il caldo le mette alla prova.

Le leve che hai davvero

Se un'emulsione non lega o si rompe, "sbatti più forte" è solo una delle risposte. Prima chiediti cosa manca. Gocce troppo grosse? Serve più energia meccanica — frusta, frullatore — e aggiungere l'olio piano, non tutto insieme, così hai il tempo di spezzettarlo. Poco emulsionante rispetto all'olio? La copertura non basta: più tuorlo, più senape, o meno olio. Troppo caldo? Abbassa la temperatura. E occhio agli effetti incrociati: aggiungere olio troppo in fretta è la causa più comune di maionese impazzita, perché superi la capacità dell'emulsionante di rivestire tutto prima che le gocce si rifondano.

Come lo verifichi

Il segno è visivo e tattile, in tempo reale: l'emulsione legata è opaca, omogenea, cremosa; quando sta cedendo vedi comparire lucido d'olio, poi goccioline che si uniscono, poi la separazione netta. Impari a coglierla mentre "gira" — il momento in cui da cremosa inizia a farsi lucida è l'avviso che stai perdendo la tregua. E se vuoi capire cosa l'ha rotta, cambia una cosa per volta: più emulsionante tenendo uguale la velocità con cui aggiungi l'olio, oppure olio più lento tenendo uguale il resto — non tutto insieme, o non saprai cosa l'ha salvata.

Il bersaglio, letto bene

Non c'è un numero dell'emulsione, perché tenerla in piedi dipende dall'insieme: quanto olio rispetto all'emulsionante, quanto piccole le gocce, quanto densa la massa, a che temperatura. Quello che c'è è un rapporto da rispettare e uno stato da riconoscere. Ogni emulsionante regge fino a una certa quantità di olio: oltre quella soglia, per quanto sbatti, la copertura non basta e si rompe. Il bersaglio non è "quanto sbattere" ma restare dentro il rapporto che il tuo emulsionante sostiene, e fermarti quando la consistenza è cremosa e omogenea. Insegui lo stato legato, non la forza del braccio.""",
            "target": "Il rapporto olio/emulsionante che la tua ricetta sostiene, e lo stato legato riconosciuto a occhio",
        },
        "fen-carbonatazione": {
            "scheda": """Prepari lo stesso gin tonic due volte. Una volta è vivo, pungente, pieno di bollicine fino all'ultimo sorso; l'altra è già scarico a metà bicchiere. Stessa tonica, stesso gin. È cambiato come — e a che temperatura — l'hai versato e maneggiato.

Le bollicine non sono un ingrediente che aggiungi: sono un gas tenuto prigioniero nel liquido, che appena può scappa. Tutto il mestiere sta nel non farlo scappare prima del sorso.

Un gas in ostaggio, non un ingrediente

La CO₂ delle bollicine è disciolta nel liquido, tenuta lì da una condizione precisa: la pressione. Finché la bottiglia è chiusa e in pressione, il gas resta dentro. Appena apri, la pressione crolla e il liquido si ritrova con più gas di quanto ne possa trattenere a quella nuova condizione — è "soprasaturo". Da quel momento il gas in eccesso cerca di uscire, e lo fa formando bolle e disperdendosi nell'aria. Aprire una bottiglia non "attiva" le bollicine: fa partire il conto alla rovescia della loro fuga.

Le due manopole: pressione e temperatura

Quanto gas resta dentro dipende da due cose. La pressione: più è alta, più gas il liquido trattiene — è il motivo per cui il gas resta in una bottiglia chiusa e se ne va in una aperta. E la temperatura, ed è qui che si gioca il servizio: il freddo trattiene il gas, il caldo lo scaccia. Un liquido freddo tiene disciolta molta più CO₂ di uno tiepido. Per questo una tonica calda "spuma" e si scarica in fretta, e la stessa tonica ghiacciata resta viva a lungo.

Nota una cosa sulle due manopole: la pressione lavora in modo proporzionale — più spingi, più gas entra, in modo abbastanza regolare — mentre la temperatura è più insidiosa, perché pochi gradi in più fanno perdere gas in modo sproporzionato. Il calore è il nemico numero uno delle bollicine.

Le leve che hai davvero (e quando esistono)

Qui conta capire in quale fase sei. Se stai carbonando tu — un sifone, un sistema a pressione — le leve sono pressione e temperatura: carboni freddo e in pressione, perché è lì che il liquido assorbe più gas. Se invece stai servendo un prodotto già carbonato, non puoi aggiungere gas: puoi solo non perderlo. E lì le leve sono tutte "difensive": tenere tutto freddo (bottiglia, bicchiere), versare piano e inclinato per non agitare, evitare il ghiaccio tritato che con la sua enorme superficie fa da innesco alle bolle, non mescolare dopo. Ogni scossa, ogni grado in più, ogni superficie ruvida è un invito al gas ad andarsene.

Come lo verifichi

Il segno è sensoriale e immediato: il pizzicore in bocca, il perlage che sale fine e continuo, il "collare" di bollicine che regge. Quando la carbonazione cede lo vedi e lo senti — bolle grosse e rade, che salgono a fatica, e la puntura che si spegne. Impari a valutarlo al servizio, non con strumenti: un liquido che "spuma" tanto e subito quando versi sta già perdendo gas in fretta; uno che resta calmo e pungente lo trattiene. E se vuoi capire cosa te lo scarica, cambia una cosa per volta — versa più piano tenendo tutto uguale, o servi più freddo cambiando solo quello — non tutto insieme.

Il bersaglio, letto bene

Non c'è un livello di bollicine giusto in assoluto: un'acqua brillante, una birra e uno champagne vivono a carbonazioni diverse, e la stessa carbonazione è percepita diversa secondo la temperatura e cosa c'è nel bicchiere. Quello che c'è è un doppio bersaglio, come per altri fenomeni: se carboni, un livello da raggiungere regolando pressione e temperatura (misurabile, per la ripetibilità); se servi, uno stato da preservare — freddo, calmo, pungente al sorso. In entrambi i casi il vero avversario è lo stesso: il tempo e il calore lavorano contro di te dal momento in cui apri. Servi in fretta, servi freddo, non agitare.""",
            "target": "Doppio: un livello da raggiungere se carboni, uno stato da preservare se servi. Tempo e calore lavorano contro",
        },
        "fen-ossidazione": {
            "scheda": """Tagli una mela e in dieci minuti la superficie è bruna. Apri una bottiglia d'olio buono e dopo settimane sa di vecchio, di cartone. Lasci un vino aperto e il giorno dopo ha perso i profumi, sa di piatto. Fenomeni diversi, un solo colpevole dietro: l'ossigeno che entra dove non dovrebbe.

L'ossidazione è il modo in cui l'aria "consuma" un alimento. Non è una cosa sola: sono meccanismi diversi che condividono lo stesso innesco. E capire quale hai davanti decide cosa puoi farci — e quando.

Non un fenomeno, una famiglia di fenomeni

Sotto la parola "ossidazione" ci sono cose diverse. C'è l'imbrunimento della frutta e verdura tagliata: lì certi composti (i fenoli) reagiscono con l'ossigeno grazie a un enzima naturale del vegetale, e si formano pigmenti scuri. È un processo guidato da un enzima, e questo conta — perché tutto ciò che rallenta quell'enzima rallenta l'imbrunimento. C'è l'irrancidimento dei grassi: oli, frutta secca, latticini in cui l'ossigeno attacca i grassi e genera quelle molecole dall'odore di vecchio. E c'è l'ossidazione di prodotti come vino e certi succhi, dove l'ossigeno degrada aromi e colore.

Meccanismi chimici diversi, ma la logica del mestiere è la stessa: l'ossigeno è il motore, e la partita si gioca su quanto ossigeno lasci entrare e quanto in fretta.

Perché succede (e cosa lo accelera)

L'ossidazione ha bisogno di contatto con l'ossigeno, e va più veloce con alcuni acceleratori: la superficie esposta (una mela tagliata ossida molto più in fretta di una intera — più superficie, più aria), la temperatura (il caldo accelera, il freddo rallenta), la luce, il tempo. Per questo lo stesso alimento dura settimane o si rovina in giorni a seconda di come lo tieni: al riparo dall'aria, al freddo, al buio, l'ossidazione rallenta; esposto, caldo, illuminato, corre.

Le leve — e la cosa più importante: quando esistono

Qui devi distinguere due situazioni completamente diverse, perché confonderle porta a errori seri.

Se stai lavorando un alimento fresco, nel momento, hai leve reali e immediate. Contro l'imbrunimento di frutta e verdura: riduci il contatto con l'aria (immergi in acqua i pezzi tagliati, coprili sottovuoto), abbassa la temperatura, oppure usa un ambiente acido — il succo di limone sulla mela tagliata funziona perché l'acido rallenta l'enzima responsabile. Contro l'irrancidimento dei grassi: conserva al riparo da aria, luce e calore. Sono azioni che governi tu, adesso, sul prodotto in lavorazione.

Ma se il prodotto è finito — un vino imbottigliato, un olio già confezionato — la situazione è diversa: su quel prodotto non intervieni. Nel vino, per esempio, l'ossidazione si governa a monte, in cantina, durante la vinificazione (dove l'enologo usa strumenti specifici come l'anidride solforosa per proteggere il vino, con dosi e competenze precise). Su una bottiglia già fatta e aperta non "aggiungi" niente per salvarla: se è ossidata, il difetto viene da un processo che è già avvenuto. La regola è netta: prima di pensare a una correzione, chiediti se sei nella fase in cui quella leva esiste davvero. Sul fresco che lavori, sì. Sul prodotto finito, no.

Come lo verifichi

I segni sono sensoriali e precisi. Colore: l'imbrunimento si vede (frutta, verdura, vino bianco che vira all'ambrato). Odore: l'irrancidimento ha quell'odore inconfondibile di vecchio, di pittura, di cartone; il vino ossidato perde i profumi freschi e sa di piatto, a volte di mela marcia. Se vuoi capire cosa accelera il tuo caso, isola una variabile: lascia due metà dello stesso prodotto, una all'aria e una coperta, una al caldo e una al freddo, e guarda quale si rovina prima. E dove c'è di mezzo la sicurezza o la conservazione seria, i segni sensoriali guidano ma non bastano da soli: un grasso può essere ossidato oltre il buono ben prima che l'odore sia ovvio.

Il bersaglio, letto bene

Qui il bersaglio non è un numero da colpire ma un tempo da guadagnare: l'ossidazione non si annulla, si rallenta. Ogni alimento ha una finestra in cui è al meglio, e il tuo obiettivo è allungarla riducendo i suoi acceleratori — aria, calore, luce, tempo, superficie esposta. Non esiste "il valore giusto": esiste tenere il prodotto lontano dall'ossigeno il più a lungo possibile, e riconoscere quando la finestra si è chiusa. La vera abilità è preventiva: si vince prima, controllando l'esposizione, non dopo, cercando di recuperare un prodotto già ossidato — che quasi mai si recupera.""",
            "target": "Non un numero ma un tempo da guadagnare: rallentare aria, calore, luce. Si vince prima, non dopo",
        },
        "fen-osmosi": {
            "scheda": """Metti il sale su una fetta di melanzana e dopo mezz'ora è bagnata di liquido: l'acqua è uscita. Metti la stessa melanzana in acqua dolce e diventa turgida, gonfia: l'acqua è entrata. Stesso ortaggio, due direzioni opposte. A decidere il verso non sei tu — è la differenza di concentrazione tra dentro e fuori.

L'osmosi è il movimento dell'acqua che insegue l'equilibrio. Capirne il verso e la forza è ciò che ti fa governare salamoie, marinature, disidratazioni — e la conservazione.

L'acqua va sempre verso il più concentrato

Dentro un alimento e fuori ci sono acqua e sostanze disciolte (sale, zuccheri) in concentrazioni diverse. L'acqua tende a spostarsi verso il lato dove le sostanze disciolte sono più concentrate, per diluirle e pareggiare i conti — attraversando le membrane delle cellule, che lasciano passare l'acqua ma non il sale o lo zucchero. Questa è la regola che decide tutto: se fuori è più concentrato che dentro (una salamoia salata, uno sciroppo denso), l'acqua esce dall'alimento; se fuori è più diluito (acqua dolce), l'acqua entra.

Ecco perché lo stesso gesto — mettere qualcosa a bagno — disidrata o gonfia a seconda di cosa c'è nel bagno. Non è il liquido in sé, è il confronto tra le due concentrazioni.

Non solo esce acqua: entra anche sapore

C'è una cosa che il mestiere sfrutta e che va capita: mentre l'acqua esce dall'alimento, un po' del soluto esterno entra. Per questo la frutta candita nello sciroppo non solo perde acqua e diventa densa, ma prende dolcezza; la carne in salamoia perde parte dell'acqua ma si insaporisce di sale e aromi. La marinatura e la salamoia non sono solo "asciugare" o "bagnare": sono uno scambio nei due sensi. Il pezzo diventa più denso, più saporito, e cambia consistenza.

Cosa regola quanto e quanto in fretta

Due leve principali. La differenza di concentrazione: più forte è lo squilibrio — una salamoia molto salata, uno sciroppo molto denso — più veloce e spinto è il movimento dell'acqua. Una salamoia leggera lavora piano e delicata, una forte lavora in fretta e aggressiva. E la temperatura: al caldo l'osmosi corre, al freddo rallenta — per questo una salamoia tiepida penetra più in fretta di una in frigo, ma il freddo è più sicuro e più controllabile. C'è anche il tempo e la superficie: più a lungo lasci, più a fondo va; pezzi piccoli o incisi scambiano più in fretta di pezzi interi.

Le leve che hai davvero

Se il risultato non è quello che vuoi, chiediti prima cosa sta facendo l'acqua. Verdura che "suda" troppo e diventa molle? La stai mettendo in ambiente troppo concentrato o troppo a lungo — riduci sale o tempo. Carne in salamoia che resta insipida dentro? Concentrazione troppo bassa o tempo troppo corto perché lo scambio arrivi al cuore. E attento agli effetti incrociati: alzare il sale per insaporire più in fretta tira fuori anche più acqua, quindi asciughi di più; è la stessa leva che muove due cose. Nella conservazione la stessa osmosi lavora per te: sale e zucchero in alta concentrazione tolgono l'acqua ai microrganismi e li bloccano — è il principio con cui salumi, conserve e confetture durano. Ma lì la concentrazione non è una preferenza di gusto: è una soglia di sicurezza, e va rispettata come tale.

Come lo verifichi

I segni sono concreti: il liquido che si raccoglie (l'acqua uscita), il peso e la consistenza che cambiano (un pezzo che perde acqua si fa più sodo e denso; uno che la assorbe si gonfia), il sapore che penetra. Impari a leggere dove è arrivato lo scambio tagliando e assaggiando il cuore, non solo la superficie — spesso fuori è già saporito e dentro ancora no. E se vuoi capire cosa regola il tuo caso, cambia una variabile per volta: stessa salamoia più o meno concentrata, o stesso tutto ma più tempo. Dove c'è di mezzo la conservazione, però, i segni sensoriali non bastano: la sicurezza dipende dal raggiungere davvero una certa riduzione dell'acqua disponibile, e quella è una soglia da rispettare, non da indovinare.

Il bersaglio, letto bene

Non c'è una concentrazione giusta in assoluto, perché dipende da cosa stai facendo: insaporire in fretta, disidratare a fondo, conservare in sicurezza sono obiettivi diversi con bersagli diversi. Quello che c'è è un doppio registro. Per il gusto e la consistenza, il bersaglio è uno stato da assaggiare — la salamoia giusta è quella che ti dà la sapidità e la texture che cerchi nel tuo pezzo, e la trovi provando. Per la conservazione, il bersaglio è una soglia da raggiungere e rispettare, perché lì l'osmosi non serve al sapore ma a togliere ai microrganismi l'acqua per vivere. Sapere in quale dei due registri sei ti dice se puoi andare a occhio o se devi rispettare un numero.""",
            "target": "Doppio registro: stato da assaggiare per il gusto, soglia da rispettare per la conservazione",
        },
        "fen-viscosita": {
            "scheda": """Il ketchup non esce dalla bottiglia. La capovolgi, aspetti, niente. Poi la scuoti una volta e viene fuori tutto insieme. Non hai aggiunto né tolto niente: hai solo applicato una forza. La stessa salsa era densa un attimo prima e fluida un attimo dopo.

La viscosità — quanto un liquido resiste a scorrere — sembra una proprietà fissa del prodotto. Non lo è. E confonderla con altre due cose è l'errore che porta a "correggere" una salsa nel modo sbagliato.

Densità di sapore, densità di flusso, e "quanto è concentrato": tre cose diverse

Prima una separazione che in cucina si fa in automatico e sbagliando. "Densa" può voler dire cose diverse: quanto è concentrata (quanta sostanza per quanto liquido), e quanto resiste a scorrere (la viscosità vera). Non coincidono. Una soluzione di solo zucchero, per quanto concentrata, scorre in modo semplice e prevedibile; un concentrato di frutta con la stessa "quantità di roba" si comporta in modo completamente diverso, perché conta la sua struttura interna — le catene, le particelle sospese — non solo quanto è concentrato. Aggiungere soluto e "addensare" non sono la stessa leva.

E c'è la seconda separazione, ancora più importante al banco: per moltissime salse la viscosità non è un numero fisso. Cambia a seconda di quanta forza applichi. Ferma nel piatto è densa; sotto la forza di un cucchiaio, di una pompa, di una scossa, diventa più fluida. Chiedere "quanto è viscosa questa salsa?" senza dire "mentre fa cosa?" è una domanda incompleta.

Perché una salsa è densa a riposo e fluida quando la muovi

Dentro molte salse ci sono strutture — catene aggrovigliate, particelle sospese — che a riposo si intrecciano e fanno resistenza: la salsa "sta su". Quando applichi una forza, queste strutture si allineano nella direzione del movimento e scivolano più facilmente: la resistenza cala, la salsa scorre. Tolta la forza, si riaggrovigliano e torna densa. È il motivo per cui la maionese tiene la forma sul cucchiaio ma si spalma sotto la lama, e il ketchup sta fermo ma esce se scuoti. Questa proprietà è utile e voluta: il prodotto è stabile nel barattolo e lavorabile quando serve.

E poi c'è la temperatura, leva potente e spesso dimenticata: il caldo in genere rende più fluido, il freddo più denso. Una besciamella fluida sul fuoco si rassoda raffreddandosi — non hai aggiunto addensante, è la stessa salsa a un'altra temperatura.

Le leve — quale stai davvero usando

Se una salsa non ha la consistenza giusta, chiediti prima quale "densità" ti manca. Vuoi più corpo stabile? È una questione di struttura: un addensante (amido, gomme), una riduzione che concentra, un'emulsione. Ti sembra troppo densa solo quando la lavori a freddo? Forse è solo temperatura: scaldala e vedi. La stai giudicando ferma ma la userai in movimento (versata, pompata, spalmata)? Allora valutala in quelle condizioni, non a riposo. E occhio all'effetto incrociato: ridurre per addensare concentra anche i sapori e il sale — la stessa leva muove consistenza e gusto insieme.

Come lo verifichi

Il segno è tattile e va colto nelle condizioni d'uso reali. Non giudicare una salsa solo ferma nel pentolino: guardala mentre fa quello che dovrà fare — come cola dal cucchiaio, come vela il piatto, come si comporta quando la muovi. Il "test del cucchiaio" (quanto resta attaccata, come cola il filo) dice più di un'impressione statica. E se vuoi capire cosa regola la tua consistenza, cambia una cosa per volta: stessa salsa a due temperature, o stessa temperatura con un filo di riduzione in più — non tutto insieme, o non saprai cosa l'ha cambiata.

Il bersaglio, letto bene

Non c'è "la viscosità giusta" come numero, per due motivi che ormai conosci: dipende dalla temperatura a cui servirai e dalla forza con cui la userai. Quello che c'è è un comportamento da ottenere nelle condizioni d'uso: una salsa che vela il piatto alla temperatura di servizio, una crema che tiene sul cucchiaio ma cede in bocca, un fondo che nappa senza colare. Il bersaglio non è "quanto densa in astratto" ma "come si deve comportare quando la uso" — e lo verifichi lì, nel gesto reale, non nel pentolino fermo. Insegui il comportamento, non un numero fisso.""",
            "target": "Non un numero fisso ma un comportamento nelle condizioni d'uso: alla temperatura e sotto la forza reali",
        },
        "fen-denaturazione": {
            "scheda": """Un uovo crudo è trasparente e liquido. Lo scaldi e diventa bianco e sodo — e non torna più indietro. Ma la stessa cosa, quel diventare opaco e rassodarsi, succede anche senza fuoco: il pesce nel ceviche "cuoce" nel limone, gli albumi montati si gonfiano sotto la frusta. Non serve sempre il calore. Serve rompere la forma delle proteine.

Dietro un enorme numero di cose che fai in cucina c'è lo stesso fenomeno: le proteine perdono la loro forma originale e si riorganizzano. Capirlo ti fa governare uova, carne, montature, latticini — con una logica sola invece di tante regole slegate.

Due passaggi diversi: prima si srotola, poi si lega

Qui c'è una distinzione che conviene tenere netta. Le proteine, allo stato naturale, sono ripiegate in una forma precisa. La denaturazione è il primo passo: quella forma si srotola, la proteina si "apre". Il secondo passo è la coagulazione: le proteine srotolate si agganciano tra loro e formano una rete solida, che intrappola liquido e dà struttura. Prima si aprono, poi si legano. L'albume che da trasparente diventa bianco e sodo ha fatto tutti e due i passaggi; gli albumi montati a neve hanno fatto soprattutto il primo (aperti dalla frusta, pronti a intrappolare aria).

Tenere separati i due passaggi serve, perché spiega cose diverse: la denaturazione ti dà la possibilità di trattenere aria (meringa) o di cambiare consistenza; la coagulazione è quella che "solidifica" e che, se tiri troppo, indurisce e spreme fuori il liquido.

Tre vie per lo stesso effetto: calore, acido, forza

Ecco la chiave che unifica tanto lavoro: a srotolare le proteine non è solo il calore. Ci arrivi per tre strade diverse. Il calore le fa vibrare finché la forma cede — è la cottura. L'acido rompe la loro struttura senza fuoco — è il ceviche, è il latte che "impazzisce" e fa i fiocchi quando aggiungi limone, è la carne marinata che cambia consistenza già da cruda. La forza meccanica le apre fisicamente — è la frusta che monta gli albumi, è l'impastare. Sale forte e alcol fanno un lavoro simile. Tre leve diverse, stesso bersaglio: la forma della proteina.

Questo spiega perché lavori così diversi sono parenti stretti: montare, cuocere, marinare, cagliare il formaggio sono tutti modi di denaturare proteine.

Le leve — e il punto delicato dell'irreversibilità

Prima di intervenire, chiediti per quale via stai denaturando e a che punto sei. Se cuoci, la leva è la temperatura, e conta sapere che proteine diverse cedono a temperature diverse: nell'uovo l'albume rassoda prima del tuorlo, ed è per questo che esiste l'uovo col bianco sodo e il tuorlo morbido; nella carne, certe proteine dei tagli duri si trasformano solo a lungo e a bassa temperatura, sciogliendo il collagene in gelatina e ammorbidendo. Se usi l'acido o la forza, la leva è quanto e quanto a lungo.

E qui il punto che cambia il modo di lavorare: la denaturazione da calore è quasi sempre irreversibile. Un uovo cotto non torna crudo. Questo significa che l'errore non si corregge a valle: se hai coagulato troppo — uovo gommoso, carne asciutta e stopposa, latte stracciato dove non doveva — non c'è ritorno. La leva esiste prima e durante, non dopo. Per questo con le proteine si lavora per difetto e si controlla: meglio fermarsi un attimo prima, perché il calore residuo continua a lavorare anche a fuoco spento.

Come lo verifichi

I segni sono visivi e tattili, e vanno colti in tempo reale perché il punto di non ritorno è vicino: l'opacità che avanza (l'albume che da trasparente diventa bianco), la consistenza che passa da liquida a presa, la carne che si rassoda e si ritira. Impari a riconoscere il punto giusto un attimo prima che sia troppo: l'uovo che è appena rappreso ma ancora cremoso, la crema che vela il cucchiaio ma non ha ancora fatto grumi. E se vuoi capire cosa governa il tuo caso, cambia una via per volta: stessa temperatura più o meno tempo, o stesso tempo a temperatura più bassa — così vedi dov'è il tuo punto di presa senza rovinare il pezzo cercando alla cieca.

Il bersaglio, letto bene

Non c'è "il grado" universale, perché ogni proteina ha la sua soglia e ogni via (calore, acido, forza) lavora a modo suo — l'albume, il tuorlo, la miosina della carne, il collagene, la caseina del latte cedono a condizioni diverse. Quello che c'è è un punto di presa da riconoscere, specifico per quello che stai facendo. Il bersaglio non è un numero astratto ma lo stato in cui la proteina ha fatto esattamente il lavoro che vuoi — trattenuto l'aria, rappreso senza indurire, sciolto il collagene senza asciugare la carne — e quel punto lo riconosci con l'occhio e il tatto, sapendo che superarlo, con le proteine, di solito non si torna indietro. Insegui il punto di presa, e fermati prima che diventi troppo.""",
            "target": "Un punto di presa da riconoscere, specifico per quello che fai: superarlo, con le proteine, non torna indietro",
        },
        "fen-cristallizzazione": {
            "scheda": """Due caramelle mou fatte con gli stessi ingredienti: una è liscia e cremosa, l'altra sabbiosa in bocca, con quei granelli che senti sotto i denti. Non hai sbagliato dose. Hai perso il controllo di come lo zucchero è tornato solido.

Cristallizzare non è un interruttore acceso o spento. Lo zucchero cristallizza quasi sempre — la vera domanda è in quanti cristalli e quanto grandi. E quella differenza è tutta la differenza tra liscio e granuloso.

Non "se" cristallizza, ma "come"

Quando sciogli lo zucchero in acqua calda e poi la soluzione si raffredda o si concentra, arriva un punto in cui contiene più zucchero di quanto potrebbe tenerne disciolto: è "soprasatura", una condizione instabile. Lo zucchero in eccesso vuole tornare solido, e lo fa formando cristalli. Fin qui è inevitabile. Il punto è che quei cristalli possono essere pochi e grandi — e li senti come granelli — oppure tantissimi e microscopici, così piccoli che la lingua li percepisce come cremosità liscia.

Ecco la regola che governa tutto: molti punti di partenza fanno tanti cristalli piccoli (liscio); pochi punti di partenza fanno pochi cristalli grandi (granuloso). Tutto il mestiere dello zucchero è controllare quanti cristalli partono e quanto li lasci crescere.

Cosa decide quanti e quanto grandi

Tre leve, soprattutto. La velocità di raffreddamento: raffreddare in fretta fa partire tanti cristalli insieme, piccoli — liscio; raffreddare piano ne fa partire pochi che crescono grandi — granuloso (è così che si fa lo zucchero candito, di proposito). L'agitazione: mescolare al momento giusto fa nascere tanti nuclei contemporaneamente e dà cristalli piccoli e uniformi, come nel fondant lavorato. E i disturbatori: certi ingredienti — sciroppo di glucosio, un grasso, un acido come il cremor tartaro, le proteine del latte nel mou — si mettono tra le molecole di zucchero e impediscono loro di raggrupparsi in cristalli grandi. Non fermano la cristallizzazione, la tengono fine. Per questo una punta di glucosio in un caramello lo mantiene liscio.

E c'è un innesco insidioso da conoscere: un solo granello di zucchero non sciolto — sul bordo della pentola, su un cucchiaio — fa da seme e può scatenare una cristallizzazione a catena, grossolana. Ecco perché nelle lavorazioni delicate si pulisce il bordo e non si smuove al momento sbagliato.

Le leve — e il momento in cui esistono

Se il risultato è granuloso quando lo volevi liscio, ripensa a dove hai perso il controllo. Hai raffreddato troppo piano o lasciato fermo quando dovevi far partire tanti nuclei? Hai smosso al momento sbagliato, o un granello sul bordo ha fatto da innesco? Mancava un disturbatore che tenesse i cristalli fini? Le leve agiscono durante il processo — temperatura, agitazione, ingredienti che metti prima. Una volta che i cristalli grossi si sono formati e la massa è solida, non li rimpicciolisci: al massimo puoi rifondere tutto scaldando e ricominciare da capo con più controllo. La leva è nel come ci arrivi, non nel dopo.

Come lo verifichi

Il segno è tattile, in bocca e sotto gli strumenti: la texture liscia contro il granello che senti sulla lingua, la superficie lucida e omogenea contro quella opaca e sabbiosa. Durante la lavorazione, il colore e la consistenza che cambiano quando la cristallizzazione parte (una massa limpida che si intorbidisce, che "prende") sono l'avviso. E se vuoi capire cosa governa il tuo risultato, cambia una cosa per volta: stessa ricetta raffreddata in fretta o piano, o con e senza un pizzico di glucosio — così vedi quale leva sposta la texture.

Il bersaglio, letto bene

Non c'è "il grado" della cristallizzazione, perché il bersaglio dipende da cosa vuoi: cristalli grandi e netti per lo zucchero candito, microscopici e invisibili per un fondant o un gelato cremoso, quasi nessuno per un caramello morbido. Lo stesso fenomeno, governato in modo opposto, dà prodotti opposti. Il bersaglio non è un numero ma una dimensione di cristallo da ottenere — grande dove la vuoi, invisibile dove serve cremosità — e la raggiungi controllando quanti nuclei fai partire e quanto li lasci crescere. Decidi tu se vincere facendo tanti cristalli piccoli o pochi grandi: l'importante è deciderlo, non subirlo.""",
            "target": "Una dimensione di cristallo da ottenere: grande dove la vuoi, invisibile dove serve cremosità",
        },
        "fen-gelatinizzazione": {
            "scheda": """Scaldi acqua e farina per una salsa e a un certo punto, di colpo, il liquido diventa denso e cremoso. Fai raffreddare quella stessa salsa in frigo e il giorno dopo è un blocco sodo, con del liquido separato sopra. E il pane, lo stesso pane, se lo tieni in frigo raffermisce più in fretta che sul bancone. Dietro tutte e tre queste cose c'è l'amido e il suo rapporto con l'acqua.

L'amido è il grande addensante della cucina — salse, creme, pane, pasta. Ma ha due facce: una che ti dà cremosità, e una che, dopo, ti indurisce il prodotto. Capirle tutte e due ti fa governare l'addensare e prevedere il raffermire.

A freddo dorme, col calore assorbe e gonfia

I granuli di amido, a freddo, sono pacchetti chiusi che nell'acqua restano sospesi senza fare niente: se sciogli farina in acqua fredda, resta un liquido torbido e sottile. Serve il calore. Scaldando, oltre una certa soglia i granuli cominciano ad assorbire acqua e a gonfiarsi tantissimo, fino a occupare tutto lo spazio e a ostacolarsi tra loro: è questo affollamento di granuli gonfi d'acqua che rende densa la salsa. Questo è il momento in cui il roux "prende", la besciamella si addensa, la crema pasticcera si rassoda. È un cambiamento a senso unico: una volta gelatinizzato, l'amido non torna al granulo chiuso di prima.

Il rovescio: quando si raffredda, si riordina e indurisce

Ed ecco la seconda faccia, quella che spiega tante "sorprese". Quando la massa gelatinizzata si raffredda, le molecole di amido che si erano liberate col calore si riallineano lentamente in una struttura più ordinata e compatta. Riordinandosi, strizzano fuori l'acqua che prima trattenevano. È per questo che una salsa densa da calda diventa un blocco sodo da fredda, e che il pane, giorno dopo giorno, diventa duro e bricioloso: non è che "si secca" perdendo acqua nell'aria — è l'amido che si ricompatta e spinge fuori l'acqua che aveva dentro. E qui la cosa contro-intuitiva che quasi nessuno sa spiegare: questo riordino va più veloce alle temperature da frigorifero. Ecco perché il pane in frigo raffermisce prima, non dopo. Scaldare di nuovo il pane raffermo lo ammorbidisce un po' proprio perché rimette in gioco quell'amido riordinato — ma è un sollievo temporaneo.

Le leve — governare l'addensare e rallentare l'indurire

Se stai addensando, la leva è il calore, gestito con pazienza: l'amido va scaldato gradualmente perché i granuli si gonfino ordinatamente. Attento a due eccessi opposti: se scaldi troppo poco non gelatinizzi e resta liquido; se scaldi troppo o agiti con violenza rompi i granuli già gonfi e la salsa "si slega", perde densità o separa. E certi ingredienti spostano la soglia: lo zucchero, per esempio, può alzare la temperatura a cui l'amido gelatinizza, e questo conta nelle creme dolci.

Se invece il problema è il raffermire — un prodotto che indurisce nel tempo — sappi che è retrogradazione, e che la leva è soprattutto la temperatura di conservazione: il freddo del frigo la accelera, quindi il pane si tiene meglio a temperatura ambiente ben chiuso, o congelato (il congelamento vero, molto più freddo, quasi la ferma). Ma è un processo che rallenti, non che annulli.

Come lo verifichi

Per l'addensare, il segno è visibile e immediato: la consistenza che cambia di colpo, il liquido che "vela" il cucchiaio, la salsa che nappa. Impari a sentire il punto in cui ha preso abbastanza ma non è ancora stato scaldato troppo (oltre, comincia a slegarsi). Per il raffermire, il segno è la durezza e le briciole che avanzano nei giorni, e l'acqua che separa da un gel troppo compatto. E se vuoi capire cosa governa il tuo caso, cambia una cosa per volta: stessa salsa scaldata di più o di meno, o stesso pane conservato a temperatura ambiente o in frigo, e guarda la differenza.

Il bersaglio, letto bene

Non c'è un grado universale, perché la soglia di gelatinizzazione dipende dal tipo di amido (riso, patata, mais gelatinizzano a temperature diverse) e da cosa c'è intorno. Quello che c'è, per l'addensare, è un punto di presa da riconoscere: la densità giusta si raggiunge portando l'amido a gonfiarsi pienamente senza spingersi oltre, e la vedi nella consistenza, non su un termometro. Per il raffermire, il bersaglio è un tempo da guadagnare: non puoi impedire all'amido di riordinarsi, puoi rallentarlo con la conservazione giusta. Due facce dello stesso amido, due bersagli diversi: uno lo raggiungi col calore, l'altro lo rimandi con la temperatura di conservazione.""",
            "target": "Punto di presa col calore per addensare; tempo da guadagnare con la conservazione per rallentare il raffermare",
        },
        "fen-diluizione": {
            "scheda": """Lo stesso Negroni: shakerato è pallido, freddissimo, un po' acquoso; mescolato è limpido, meno gelido, più deciso. Stessa ricetta, stesse dosi. È cambiato quanto ghiaccio si è sciolto dentro — e quello non è un difetto, è un ingrediente.

La diluizione è l'acqua che entra nel drink mentre il ghiaccio si scioglie. Sembra il nemico — "annacquare" — ed è invece uno degli ingredienti principali di ogni cocktail. Capirla ti fa smettere di subirla e iniziare a dosarla.

Il ghiaccio non raffredda perché è freddo: raffredda perché si scioglie

Questa è la chiave che cambia tutto. Si pensa che il ghiaccio raffreddi "essendo freddo". In realtà raffredda soprattutto sciogliendosi: per passare da solido a liquido, il ghiaccio deve assorbire una grande quantità di calore, e quel calore lo ruba al liquido intorno. È l'atto stesso di fondere che toglie calore al drink. Il che porta a una conseguenza che devi avere ben chiara: non puoi raffreddare un cocktail col ghiaccio senza diluirlo. Raffreddamento e diluizione sono la stessa cosa vista da due lati — più raffreddi, più acqua entra. Non sono due leve separate: sono una sola.

Ecco perché i cocktail classici sono pensati con quell'acqua già in conto: la ricetta "giusta" lo è a diluizione avvenuta, non appena versata.

Perché quell'acqua serve al drink

L'acqua non "indebolisce" e basta: fa un lavoro sul gusto. Ammorbidisce la spigolosità dell'alcol, che da solo è aggressivo e chiude gli aromi. E c'è una cosa fine: certi aromi, ad alta gradazione, restano come "legati" all'alcol e si liberano solo quando la gradazione scende — è il motivo per cui una goccia d'acqua "apre" il naso di un whisky forte. Diluire nella giusta misura fa emergere profumi che a secco non sentiresti, rende gli agrumi più brillanti, lo zucchero meno stucchevole. Troppa, e il drink diventa piatto e slavato; troppo poca, e resta duro, alcolico, chiuso. La diluizione giusta è quella che apre il drink senza spegnerlo.

Le leve — e perché il tempo non torna indietro

Tu governi la diluizione soprattutto con il metodo e con il ghiaccio. Il metodo: mescolare è gentile e lento, scioglie poco ghiaccio, dà un drink più limpido, più forte, un po' meno freddo — per questo si usa sui cocktail di soli distillati (Negroni, Martini). Shakerare è violento e veloce, rompe il ghiaccio, aumenta la superficie e quindi la fusione: più diluizione, più freddo, più aria — per questo si usa sui drink con succo. Il ghiaccio stesso è una leva: cubi grandi e compatti si sciolgono piano (raffreddi con poca acqua), ghiaccio piccolo o tritato si scioglie in fretta (raffreddi tanto ma diluisci molto — è voluto nei tiki, dove l'acqua doma il rum forte). E il tempo: più a lungo agiti, più acqua entra.

Il punto delicato: la diluizione è a senso unico. Puoi aggiungere acqua a un drink troppo forte, ma non puoi toglierla da uno troppo annacquato. Per questo si punta a fermarsi al punto giusto, e nel dubbio un attimo prima — e conta anche cosa succede dopo, nel bicchiere: un drink servito su ghiaccio fresco continua a diluirsi piano mentre lo bevi, e la ricetta tiene conto anche di quello.

Come lo verifichi

Il segno è nel bicchiere e al palato: la temperatura, la "spina" alcolica che si ammorbidisce, il drink che passa da chiuso e duro ad aperto e rotondo. Impari a sentire il punto — mescolando, il liquido che diventa scorrevole e ben freddo sul dorso del bar spoon; shakerando, il cambio di suono e di peso quando il ghiaccio si è consumato. E se vuoi capire cosa governa il tuo drink, cambia una cosa per volta: stesso cocktail mescolato dieci secondi in più, o con un cubo grande invece che ghiaccio piccolo — e assaggia la differenza di forza e apertura.

Il bersaglio, letto bene

Non c'è una percentuale d'acqua uguale per tutti, perché il punto giusto dipende dal drink: un Martini spirit-forward vuole una diluizione diversa da un sour con succo, e lo stesso drink più freddo regge più acqua. Quello che c'è è un equilibrio da raggiungere: il momento in cui l'alcol si è ammorbidito, gli aromi si sono aperti e il drink è freddo, senza scivolare nell'acquoso. Il bersaglio non è un numero da inseguire ma quel punto di apertura, e lo riconosci assaggiando — perché lo stesso 25% d'acqua è perfetto in un drink e troppo in un altro. Diluisci fino ad aprire il drink, e fermati prima di spegnerlo.""",
            "target": "Non una percentuale fissa ma il punto di apertura: alcol ammorbidito, aromi aperti, freddo, senza scivolare nell'acquoso",
        },
        "fen-estrazione": {
            "scheda": """Lo stesso caffè, la stessa macchina. Una volta esce aspro e magro, ti allappa e sembra "acqua sporca"; un'altra esce amaro e secco, che raschia. Non hai cambiato la miscela. Hai tirato fuori dai fondi cose diverse — troppo poco, o troppo.

Estrarre è far passare le sostanze da un solido (caffè, tè, spezie, botaniche) al liquido. Il punto è che quelle sostanze non escono tutte insieme e non sono tutte buone: escono in ordine, e il mestiere è fermarsi quando hai preso il buono e prima del cattivo.

Non "quanto" estrai, ma "cosa" e "in che ordine"

L'acqua scioglie i componenti del caffè in sequenza, non tutti nello stesso istante. Prima escono gli acidi — danno brillantezza, freschezza, note fruttate. Poi gli zuccheri e i composti aromatici — danno dolcezza, corpo, equilibrio: è il cuore buono della tazza. Alla fine escono i tannini e le sostanze amare e secche — che in piccola parte danno profondità, ma in eccesso rovinano tutto con amaro e astringenza.

Questo spiega i due difetti opposti. Se fermi l'estrazione troppo presto — o l'acqua fatica a entrare — prendi solo la prima parte: tanti acidi, pochi zuccheri. Risultato aspro e acquoso: è la sotto-estrazione. Se la tiri troppo per lungo, oltre il buono arrivi al cattivo: amaro, secco, che raschia. È la sovra-estrazione. Il bersaglio sta in mezzo: abbastanza da avere la dolcezza, non tanto da sconfinare nell'amaro.

Estrazione e forza sono due cose diverse

Attento a non confondere due parole. La forza è quanto è concentrata la bevanda — quanti solidi disciolti per quanta acqua — e la governi soprattutto col rapporto caffè/acqua. L'estrazione è quanta sostanza hai tirato fuori dai fondi. Non sono la stessa cosa: puoi avere un caffè forte ma sotto-estratto (concentrato ma aspro), o uno leggero ma ben estratto (diluito ma equilibrato). "Poco caffè" e "caffè fatto male" sono problemi diversi, con leve diverse.

Le leve — e come capire quale muovere

Tre leve governano la velocità con cui l'acqua tira fuori le sostanze. La macinatura, la più potente: più fine è la polvere, più superficie esponi all'acqua, più veloce e spinta è l'estrazione (per questo l'espresso vuole macinato fine, tempi brevissimi); più grossa, più lenta (per questo la French press e il cold brew la vogliono grossa). La temperatura: l'acqua calda estrae di più e più in fretta, l'acqua fredda pochissimo e piano (il cold brew ci mette ore e viene meno acido proprio per questo). E il tempo di contatto: più a lungo l'acqua resta sui fondi, più estrae.

Qui la regola d'oro del mestiere, che è anche il modo giusto di correggere: cambia una leva per volta. Se il caffè è aspro (sotto-estratto), spingi l'estrazione — di solito macinando più fine, la leva più forte. Se è amaro (sovra-estratto), riducila — macina più grosso. Ma se cambi macinatura, temperatura e tempo tutti insieme e la tazza migliora, non hai imparato niente: non sai quale l'ha fatto, e la prossima volta ricominci a caso. Una leva, assaggia, decidi.

E un avvertimento sulla macinatura: se il macinino ti dà polveri di dimensioni molto diverse, hai il problema peggiore — i pezzi fini sovra-estraggono e i grossi sotto-estraggono nello stesso identico caffè, e senti aspro e amaro insieme. Quello non lo aggiusti con la tecnica: è uniformità della macinatura.

Come lo verifichi

Il segno è al palato, e i due difetti si distinguono nettamente: l'aspro della sotto-estrazione è acuto, allappante, in punta di lingua, e la tazza sembra vuota; l'amaro della sovra-estrazione è secco, raschiante, resta in fondo alla bocca. Imparare a dire quale dei due è ti dice subito da che parte spingere. E se senti tutti e due insieme, non è un problema di tempo o temperatura: è macinatura disuniforme. Cambia una variabile, riassaggia, e vai per gradi.

Il bersaglio, letto bene

Non c'è un tempo o una macinatura giusti in assoluto: dipendono dal metodo (espresso, filtro, French press, cold brew estraggono in modi diversi), dal caffè, dalla macchina. Quello che c'è è un punto di equilibrio da riconoscere al palato — la finestra in cui hai preso acidi e zuccheri ma non ancora i tannini amari. Il bersaglio non è un numero da copiare da una guida ma quel punto dolce, e lo trovi regolando una leva alla volta finché la tazza è equilibrata. Vale per tutto ciò che infondi: tè che diventa amaro se lo lasci troppo, un amaro fatto in casa, un'infusione di spezie. La logica è sempre la stessa: prendi il buono, fermati prima del cattivo.""",
            "target": "Il punto di equilibrio al palato: preso acidi e zuccheri, non ancora i tannini amari. Una leva per volta",
        },
        "fen-solubilita": {
            "scheda": """Vuoi sciogliere tanto zucchero in poca acqua per uno sciroppo denso. Continui a versarne, mescoli, ma a un certo punto lo zucchero smette di sparire: resta sul fondo, per quanto giri. Scaldi l'acqua e — magia — quello stesso zucchero si scioglie tutto. Non hai aggiunto acqua. Hai cambiato quanto quell'acqua può contenere.

La solubilità è quanto di una sostanza un liquido riesce a sciogliere. Sembra semplice, ma nasconde due domande diverse che al banco confondi in una: quanto se ne può sciogliere in tutto, e quanto in fretta ci arrivi. Sono governate da leve diverse.

Il limite e la velocità sono due cose diverse

C'è un tetto: ogni liquido, a una data temperatura, può sciogliere solo una certa quantità massima di una sostanza. Raggiunto quel tetto, la soluzione è "satura" — aggiungine ancora e resta lì, indisciolto, sul fondo. Questo è il limite: quanto, in totale.

E poi c'è la velocità: quanto in fretta arrivi a sciogliere quello che stai sciogliendo. Ed è qui che si fa confusione, perché mescolare e usare zucchero fine ti fanno sciogliere più in fretta — e sembra che "sciolgano di più". Non è così: mescolare e macinare fine accelerano solo la corsa verso il tetto, ma il tetto non lo spostano di un grammo. Se giri all'infinito uno zucchero che ha già saturato l'acqua, non se ne scioglierà altro. Velocità e limite sono due cose separate.

Cosa muove il limite, cosa muove la velocità

A spostare il tetto — quanto in totale si scioglie — è soprattutto la temperatura. L'acqua calda tiene disciolto molto più zucchero della fredda: quello che a freddo satura e si deposita, a caldo entra tutto in soluzione. Per questo gli sciroppi densi si fanno a caldo. E c'è un'altra cosa che decide il limite: la natura delle due sostanze. Non tutto si scioglie uguale — lo zucchero si scioglie molto più del sale in acqua, e certe sostanze in acqua non si sciolgono quasi per niente ma in alcol sì (è il principio delle infusioni alcoliche, dove l'alcol tira fuori aromi che l'acqua da sola non prenderebbe).

A muovere la velocità — quanto in fretta arrivi al tetto — sono l'agitazione (mescolare porta acqua fresca a contatto), la superficie (polvere fine si scioglie prima di cristalli grossi) e sempre la temperatura (che accelera anche la corsa, oltre ad alzare il tetto).

Le leve — e cosa succede quando raffreddi il pieno

Se qualcosa non si scioglie, chiediti prima quale delle due domande hai davanti. Ci mette troppo? È velocità: scalda, mescola, macina più fine. Non si scioglie proprio più, resta sul fondo? Hai colpito il tetto: o alzi la temperatura, o aggiungi solvente, o accetti che è saturo. E attento a un effetto importante: se saturi a caldo e poi raffreddi, il tetto si abbassa, e il liquido si ritrova con più sostanza disciolta di quanta ne regga a freddo. Quell'eccesso vuole uscire — e di solito lo fa formando cristalli. È il ponte con la cristallizzazione: uno sciroppo saturato a caldo può "zuccherare" raffreddandosi. Per questo, se vuoi uno sciroppo stabile e limpido, non lo porti al limite massimo: gli lasci margine.

Come lo verifichi

Il segno è visibile: il soluto che continua a sparire (non sei al limite) contro quello che resta sul fondo per quanto giri (sei saturo). E la limpidezza: una soluzione sotto il limite è pulita e stabile; una portata oltre, o satura e poi raffreddata, tende a intorbidirsi e a depositare. Se vuoi capire cosa ti blocca, cambia una cosa per volta: stessa acqua più calda (sposti il tetto), o solo più mescolata a parità di temperatura (sposti la velocità, non il tetto) — e vedi quale risolve. Se scaldare risolve, era il limite; se bastava mescolare meglio, era solo velocità.

Il bersaglio, letto bene

Non c'è una quantità giusta in assoluto, perché il limite dipende dalla temperatura, dal solvente e dalla sostanza. Quello che c'è è una capacità legata alle condizioni, e un margine da rispettare. Per uno sciroppo che deve restare limpido e stabile, il bersaglio non è "il massimo che riesco a sciogliere" ma "abbastanza sotto il limite da non zuccherare quando si raffredda". Per un'infusione, il bersaglio è il solvente giusto per ciò che vuoi estrarre (acqua o alcol, secondo la sostanza). Il punto non è spingere al massimo, è sapere dov'è il tetto alle tue condizioni e decidere quanto avvicinartici. Conosci il limite, poi scegli il margine.""",
            "target": "Una capacità legata alle condizioni, e un margine sotto il tetto: conosci il limite, poi scegli quanto avvicinartici",
        },
        "fen-crioscopia": {
            "scheda": """Fai un sorbetto con poco zucchero: esce un blocco duro, da scalpello, che nel congelatore diventa un mattone. Ne fai un altro con più zucchero: resta cremoso, si porziona, si mangia. Metti dell'acqua pura accanto: a zero gradi è ghiaccio pieno. La differenza non è "quanto è freddo il freezer". È cosa hai sciolto nell'acqua prima di congelarla.

Il gelato è morbido a temperature sotto lo zero per un motivo fisico preciso: le sostanze disciolte abbassano il punto a cui l'acqua congela. Capire questo ti fa governare la consistenza — e ti mostra una trappola, perché la stessa leva che ammorbidisce cambia anche il gusto.

Perché lo zucchero disciolto tiene morbido il gelato

L'acqua pura congela a zero gradi: le sue molecole si incastrano in un reticolo solido, il ghiaccio. Quando sciogli zucchero (o sale, o alcol) nell'acqua, quelle particelle si mettono in mezzo e disturbano la formazione del reticolo: l'acqua fatica di più a congelare, e ci riesce solo a temperature più basse. Questo è l'abbassamento del punto di congelamento. In un gelato, il risultato è che a temperatura da freezer non tutta l'acqua è ghiaccio: una parte resta liquida, "intrappolata" tra i cristalli, ed è quella parte non congelata che rende il gelato morbido e cremoso invece che un blocco solido. Meno soluti disciolti, più acqua congela, più duro il risultato.

Conta quante particelle, non quali (e qui c'è la leva fine)

Ecco il punto che i gelatieri sfruttano: l'effetto dipende da quante particelle hai disciolto, non da cosa sono. A parità di peso, uno zucchero fatto di molecole piccole mette in acqua più particelle di uno fatto di molecole grandi — e quindi ammorbidisce di più. Per questo il glucosio e il fruttosio abbassano il punto di congelamento più del comune zucchero da tavola: a parità di grammi, contano di più. È la leva con cui si regola la durezza di un gelato senza cambiare solo la quantità totale di dolcificante.

La trappola: la stessa leva muove dolcezza e morbidezza

E qui la cosa da capire davvero. Lo zucchero fa due lavori insieme: dolcifica e ammorbidisce. Se un gelato è troppo duro e aggiungi zucchero per ammorbidirlo, lo stai anche rendendo più dolce — e magari troppo. Se lo vuoi meno dolce e togli zucchero, rischi di indurirlo. Sono due effetti della stessa leva, e non li puoi muovere del tutto separati con il solo saccarosio. Ecco perché nel mestiere si usano zuccheri diversi come leve distinte: parte di zucchero da tavola per la dolcezza "giusta", e una quota di uno zucchero a molecole piccole (glucosio) per aggiungere morbidezza senza aggiungere troppa dolcezza. Separare i due obiettivi — dolce e consistenza — è ciò che ti fa uscire dalla trappola.

Le leve che hai davvero

Se la consistenza non va, chiediti prima da che parte. Troppo duro? Ti serve più abbassamento del punto di congelamento: più zucchero totale, o meglio una quota di zucchero a molecole piccole che ammorbidisce senza stucchevolezza; anche l'alcol abbassa fortemente il punto (per questo i sorbetti con un goccio di liquore restano morbidi, ma poco: troppo e non congela più). Troppo molle o che non rassoda? Hai troppi soluti: riduci. E ricorda che questa è la leva della composizione, che decidi prima di congelare — a gelato fatto, la ricetta è quella. C'è anche la temperatura di servizio, ma quella sposta la consistenza sul momento, non risolve una base sbilanciata.

Come lo verifichi

Il segno è tattile: la durezza appena uscito dal freezer, la porzionabilità, il modo in cui si scioglie in bocca. Un gelato ben bilanciato si porziona a temperatura da freezer; uno con pochi soluti resta duro e va temperato a lungo; uno con troppi non rassoda mai bene e si scioglie subito. E se vuoi capire cosa governa la tua base, cambia una cosa per volta: stessa ricetta con una parte di saccarosio sostituita da glucosio (più morbido a pari dolcezza), o solo più zucchero totale — e senti come cambiano durezza e dolcezza separatamente.

Il bersaglio, letto bene

Non c'è una quantità di zucchero giusta in assoluto, perché dipende da cosa congeli (un sorbetto di frutta acida e uno alla crema hanno esigenze diverse) e dalla temperatura a cui servirai. Quello che c'è è un doppio bersaglio da tenere insieme senza confonderlo: la dolcezza che vuoi al palato e la morbidezza che vuoi alla porzionatura. Il bravo gelatiere non insegue un numero unico ma bilancia i due, usando tipi di zucchero diversi come leve separate. Il bersaglio è: dolce quanto basta, morbido quanto serve — e sono due manopole, anche se sembrano una.""",
            "target": "Doppio bersaglio: dolce quanto basta e morbido quanto serve — due manopole, anche se sembrano una",
        },
        "fen-overrun": {
            "scheda": """Due gelati fatti con la stessa identica miscela. Uno è denso, pieno, il sapore ti riempie la bocca; l'altro è leggero, spumoso, gonfio — e sa di meno. Non hai cambiato ricetta. Hai montato dentro più aria in uno che nell'altro. E l'aria, che non pesa e non sa di niente, ha cambiato tutto.

L'overrun è quanta aria incorpori nel gelato mentre lo mantechi. Sembra un dettaglio tecnico, ma è uno degli ingredienti più importanti del prodotto — invisibile, ma decisivo per consistenza, sapore e resa.

L'aria è un ingrediente, e si misura

Quando la gelatiera manteca, le pale non solo congelano: sbattono aria dentro la miscela, sotto forma di microbolle. Quell'aria fa aumentare il volume — parti da un litro di miscela e ti ritrovi con un litro e mezzo di gelato: quel mezzo litro in più è aria. La quantità di aria si misura, in percentuale sul volume di partenza: è l'overrun. Il punto da capire è che l'aria non è un effetto collaterale del mantecare — è un ingrediente vero, che decidi e dosi come lo zucchero o la panna, anche se non lo versi da nessuna parte.

Perché serve, e perché troppa rovina

Un po' d'aria è necessaria: senza, il gelato sarebbe un blocco densissimo, difficile da porzionare e pesante in bocca. Le microbolle spezzano la struttura, rompono i cristalli di ghiaccio e danno quella cremosità scioglievole che ci si aspetta. Ma qui c'è il compromesso da governare. Più aria monti, più il gelato diventa leggero e soffice — e insieme più il sapore si diluisce, perché l'aria non ha gusto: a parità di cucchiaio, c'è meno gelato vero e più vuoto. E oltre un certo punto diventa spumoso, si scioglie subito, perde corpo e quella percezione di ricchezza. Poca aria: denso, sapore pieno, ma duro e pesante. Troppa: leggero e cremoso in apparenza, ma vuoto e sciocco. Il mestiere sta nel trovare il punto tra i due.

Cosa trattiene l'aria (e cosa la fa scappare)

Non tutte le miscele montano uguale. Perché l'aria resti intrappolata e non collassi, serve qualcosa che rivesta e stabilizzi le bolle. Le proteine — quelle del latte soprattutto — fanno proprio questo: si dispongono attorno alle bolle e formano una pellicola che le tiene su. Anche i grassi e i solidi totali contano: una miscela ricca e corposa intrappola e trattiene l'aria meglio di una acquosa e magra, che monta male e lascia scappare le bolle. Per questo un gelato povero di grassi e proteine fatica a montare bene, e un sorbetto (senza latticini) ha una struttura d'aria diversa e più fragile.

Le leve che hai davvero

Se la consistenza non va, ragiona sull'aria. Troppo denso e duro? Ti serve più overrun: mantecare più a lungo o più veloce incorpora più aria; ma valuta anche la ricetta, perché una miscela magra non monterà comunque. Troppo gonfio, spumoso, che sa di poco? Hai troppa aria: manteca meno, o rivedi il bilanciamento. E ricorda l'effetto incrociato con la crioscopia: l'aria e gli zuccheri sono due leve diverse della morbidezza — un gelato può essere morbido perché ben zuccherato o perché pieno d'aria, ma sono cose diverse, e confonderle porta a sbagliare la correzione (aggiungi aria quando il problema era lo zucchero, o viceversa). La velatura piena e cremosa viene da un equilibrio tra le due, non da una sola.

Come lo verifichi

Il segno più immediato è il peso: a parità di volume, un gelato con poca aria pesa di più — prova a soppesare due vaschette uguali, quella più pesante ha meno overrun e più gelato vero. Poi la bocca: il denso che riempie e persiste contro il soffice che si scioglie e sparisce; l'intensità del sapore, più piena nel primo. E se vuoi capire cosa governa il tuo prodotto, cambia una cosa per volta: stessa miscela mantecata più a lungo (più aria), o stessa mantecatura con una ricetta più ricca di grassi/proteine (monta meglio) — e senti come cambiano corpo e intensità.

Il bersaglio, letto bene

Non c'è un overrun giusto in assoluto: un gelato artigianale di qualità punta a poca aria per densità e sapore pieno; un soft serve ne vuole di più per quella leggerezza cremosa che lo caratterizza; l'industria a volte ne abusa per vendere aria al prezzo del gelato. Quello che c'è è un bersaglio legato al prodotto che vuoi e alla sua identità. Il punto non è "il massimo di cremosità apparente" ma la quantità d'aria che dà la consistenza giusta senza svuotare il sapore. Poca aria per un gelato che deve sapere di tanto; più aria dove la leggerezza è il pregio. Decidi quanta aria è ingrediente e quanta sarebbe solo vuoto.""",
            "target": "Un overrun legato all'identità del prodotto: aria-ingrediente dove serve cremosità, non aria-vuoto",
        },
        "fen-meringa": {
            "scheda": """Monti gli albumi e in pochi minuti da liquido trasparente diventano una massa bianca, gonfia, che sta su. Ma se ti distrai e monti troppo, quella stessa massa si "straccia": diventa granulosa, secca, e comincia a perdere acqua sul fondo della ciotola. Sei passato dal punto perfetto al disastro senza aggiungere niente — solo continuando a montare.

La meringa è una schiuma: aria intrappolata in un liquido, tenuta insieme dalle proteine dell'albume e stabilizzata dallo zucchero. È il punto d'incontro di tre cose che governi già separatamente — montare aria, srotolare proteine, sciogliere zucchero — e capire come cooperano ti fa smettere di andare a fortuna.

Cosa succede davvero quando monti

La frusta fa due lavori insieme. Primo: sbatte dentro aria, spezzandola in bollicine sempre più piccole e numerose — più monti energicamente, più fini le bolle, più stabile la schiuma. Secondo: apre le proteine dell'albume. Nell'albume crudo le proteine sono gomitoli ripiegati; la forza della frusta li srotola (è denaturazione, la stessa di quando cuoci un uovo, ma qui fatta a freddo dalla meccanica). Una volta aperte, le proteine hanno una parte che "ama" l'acqua e una che la "fugge": si dispongono attorno a ogni bollicina d'aria, la parte che fugge l'acqua verso l'aria e l'altra verso il liquido, formando una pellicola che avvolge la bolla e le impedisce di fondersi con le altre. È esattamente il lavoro che fa un emulsionante, qui applicato all'aria invece che all'olio.

Perché lo zucchero è indispensabile (e cosa costa)

Le proteine da sole fanno una schiuma, ma fragile: destinata a collassare, l'aria vuole scappare. Lo zucchero è ciò che la rende stabile. Sciogliendosi nell'acqua dell'albume, lo zucchero ispessisce quel liquido in uno sciroppo denso: un liquido più viscoso scorre più lentamente tra le bolle, quindi le bolle drenano e si fondono molto più a fatica. La schiuma tiene. Ma c'è un prezzo, ed è un compromesso da conoscere: lo sciroppo denso non si stira sottile come l'acqua, quindi con lo zucchero la meringa accoglie meno aria e resta più densa. Da qui una regola concreta: se metti lo zucchero presto, ottieni una meringa fine, ferma e densa; se lo metti tardi, più morbida e voluminosa. La tempistica dello zucchero è una leva, non un dettaglio.

Il punto giusto e l'over-montatura

Ecco la cosa che rovina più meringhe. Montando, la schiuma passa per stadi: schiumosa, picchi morbidi che si piegano, picchi fermi, picchi rigidi e lucidi. Il punto giusto dipende da cosa ci fai — ma esiste un oltre. Se monti troppo, la rete di proteine si stringe così tanto che spreme fuori l'acqua che teneva tra le bolle: la meringa "piange", diventa granulosa, secca, separata. E come per le proteine cotte, è quasi impossibile tornare indietro: hai stretto troppo la rete e non la rilassi. Per questo si punta al picco fermo e lucido e ci si ferma lì — un attimo prima è meglio di un attimo dopo.

Nota che lo zucchero aiuta anche qui: lubrifica le proteine e allarga il margine prima dell'over-montatura. Per questo una meringa senza zucchero è più facile da "stracciare" di una zuccherata.

Le leve che hai davvero

Se la meringa non viene, ragiona su cosa manca. Non monta, resta liquida? Cerca il nemico numero uno: il grasso. Anche una traccia — un filo di tuorlo, una ciotola unta o di plastica graffiata che trattiene grasso — impedisce alle proteine di formare il film e la schiuma non parte. Ciotola pulitissima, niente tuorlo. Monta ma è instabile, collassa? Ti serve più stabilizzazione: zucchero (nella giusta quantità e tempistica), o un tocco d'acido (cremor tartaro, limone) che rende la rete proteica più fine e resistente e allarga il margine. Troppo densa o troppo molle? Gioca sulla tempistica dello zucchero. E ricorda: montare è a senso unico oltre un certo punto, quindi la leva vera è fermarsi al momento giusto, non correggere dopo.

Come lo verifichi

Il segno è visivo e netto: il picco che si forma sulla frusta e come si comporta — si piega (morbido), sta dritto (fermo), è lucido e sodo (pronto), oppure è opaco, grumoso, con liquido che affiora (troppo montato, andato). La lucentezza è un buon segnale: una meringa pronta è lucida; una che opacizza e si granula sta cedendo. E se vuoi capire cosa governa la tua, cambia una cosa per volta: stessa ricetta con lo zucchero aggiunto prima o dopo, o con e senza un pizzico d'acido — e guarda come cambiano fermezza, volume e margine prima dell'over-montatura.

Il bersaglio, letto bene

Non c'è "il" punto giusto uguale per tutto, perché dipende da cosa fai: una meringa per alleggerire un impasto vuole picchi morbidi, una per decorare o cuocere secca vuole picchi fermi e lucidi. Quello che c'è è uno stato da riconoscere sulla frusta, specifico per l'uso, e un margine da non superare. Il bersaglio non è un tempo di montatura ma quel picco — morbido o fermo secondo lo scopo — colto un attimo prima che la rete stringa troppo. E l'equilibrio tra volume e stabilità lo decidi tu con la quantità e la tempistica dello zucchero: più stabile e denso, o più arioso e delicato. Insegui il picco giusto per ciò che devi fare, e fermati prima che pianga.""",
            "target": "Il picco giusto per l'uso (morbido o fermo), colto un attimo prima che la rete stringa troppo e pianga",
        },
        "fen-souffle": {
            "scheda": """Il souffle esce dal forno gonfio, alto, spettacolare. Lo porti in tavola e in un minuto si affloscia, si siede su se stesso. Oppure non è mai salito: è rimasto basso e denso. Tra il trionfo e il fallimento c'è una manciata di secondi e qualche errore invisibile — quasi tutti compiuti prima che il souffle entri in forno.

Il souffle è la stessa schiuma della meringa, ma portata un passo oltre: montata dentro una base, e poi cotta perché salga e si fissi. Capire cosa lo fa salire e cosa lo fa crollare ti fa governare il fenomeno più fragile della pasticceria.

Cosa lo fa salire: due motori insieme

La salita non è magia, sono due cose fisiche che spingono nello stesso momento. Primo: l'aria montata negli albumi, scaldandosi, si espande — l'aria calda occupa più volume, e le migliaia di bollicine intrappolate gonfiano tutte insieme, sollevando la massa. Secondo: l'acqua contenuta nella base, scaldandosi, evapora e diventa vapore, che spinge ancora di più dilatando le stesse bolle. Aria che si espande più vapore che si genera: ecco perché il souffle si alza in forno come niente altro.

Ma spingere non basta: se fosse solo questo, appena tolto il calore tornerebbe giù. Serve qualcosa che fissi la struttura mentre è su.

Cosa lo tiene su: le proteine che coagulano al punto giusto

Qui entra il calore come secondo lavoro. Mentre l'aria e il vapore gonfiano, il calore cuoce le proteine — degli albumi e della base — che coagulano e si irrigidiscono, trasformando la schiuma morbida in un'impalcatura solida. Se questa impalcatura si forma in tempo, regge anche quando, raffreddandosi, l'aria si ricontrae: il souffle resta su. Se le proteine non hanno coagulato abbastanza — souffle tolto troppo presto, forno troppo basso — la struttura è ancora molle quando togli il calore, l'aria si sgonfia e non c'è niente a trattenerla: collasso. È come una casa: se le mura non hanno fatto in tempo a indurire, appena togli i puntelli crolla.

Perché collassa: le cause, quasi tutte a monte

Il collasso raramente è colpa di "hai aperto il forno" (anche se lo shock di temperatura contribuisce: l'aria dentro si raffredda di colpo e si contrae). Le cause vere sono prima. Interno non fissato: cotto troppo poco, le proteine non reggono. Albumi montati male: se sotto-montati, poca aria da espandere; se sovra-montati — ed è il paradosso — la rete proteica è già così tesa e rigida che si spezza invece di stirarsi mentre l'aria spinge, e non regge la salita. Grasso di troppo: una traccia di tuorlo o una ciotola unta e gli albumi non montano, come nella meringa. Incorporazione brutale: se mescoli la schiuma nella base con violenza, spacchi le bolle e butti via l'aria che ti serviva — va incorporata con delicatezza, a movimenti larghi.

Le leve che hai davvero

Prima di cuocere, la partita è quasi già decisa. Albumi montati al punto giusto (fermi ma non stracciati), niente grasso, incorporazione gentile nella base, base con la giusta quantità di liquido (troppo lo appesantisce e non sale). In cottura: forno alla temperatura giusta — abbastanza caldo da far espandere in fretta e coagulare le proteine, non così basso da lasciarlo molle né così alto da fissare la crosta prima che sia salito. E cuocerlo finché è davvero fissato dentro, non solo gonfio fuori. Dopo il forno, la leva non esiste più: il souffle è un fenomeno a senso unico, serve subito, perché anche fatto bene un po' si siede raffreddandosi. La finestra di gloria è breve per natura, e questo fa parte del piatto.

Come lo verifichi

Il segno è visivo, in cottura e all'uscita: la salita che avviene (gonfia dritto e uniforme), il colore che scurisce in superficie, e — il segnale che è pronto — la superficie dorata con il centro appena assestato, che oscilla leggermente ma non è liquido sotto. Un souffle tolto quando ancora "balla" troppo al centro non è fissato e cadrà. E se vuoi capire cosa governa il tuo, cambia una cosa per volta: stessa ricetta con albumi montati un po' meno, o con qualche minuto in più di forno — e guarda se sale meglio o regge di più.

Il bersaglio, letto bene

Non c'è un tempo o una temperatura universali, perché dipendono dalla base (una besciamella al formaggio e una crema al cioccolato si comportano diverse), dalla dimensione, dal forno. Quello che c'è è uno stato da raggiungere: salito pienamente e fissato dentro quel tanto che basta a reggere il raffreddamento, senza asciugarsi troppo. Il bersaglio non è "il souffle più alto" ma quello che sale e sta su abbastanza da arrivare in tavola — e lo riconosci dalla superficie dorata e dal centro appena assestato, non da un cronometro. E accetta che un po' si sieda: la sua fragilità non è un difetto da eliminare, è la natura del piatto. Punta al momento in cui è salito e fissato, e servilo subito.""",
            "target": "Salito e fissato quanto basta a reggere il raffreddamento: superficie dorata, centro appena assestato. Servi subito",
        },
        "fen-sineresi": {
            "scheda": """Apri uno yogurt e sopra c'è una pozzetta di liquido chiaro. Tagli una fetta di cheesecake e il piatto si bagna. La marmellata fatta in casa dopo qualche giorno ha uno strato d'acqua. La crema pasticcera "spurga". Sono la stessa cosa: un gel che stava trattenendo l'acqua e a un certo punto la lascia andare.

La sineresi è il liquido che un gel espelle contraendosi. Non è marciume né errore di dose — è la tendenza naturale di certe strutture a strizzarsi nel tempo. Capirla ti dice perché succede e come rallentarla.

Cos'è un gel, e perché trattiene l'acqua (finché la trattiene)

Un gel è una rete: molecole lunghe — proteine, amido, pectina, gomme — che si agganciano tra loro formando una maglia tridimensionale, e in quella maglia restano intrappolate grandi quantità d'acqua. È questo che rende un gel un gel: acqua tenuta prigioniera da una struttura, così che il tutto è morbido e coeso ma non liquido. Lo yogurt, un budino, una gelatina, la marmellata, il ketchup — sono tutti acqua trattenuta da una rete.

Il punto è che questa presa non è per sempre. La maglia tende, nel tempo, a riorganizzarsi e a stringersi un po': le molecole si riavvicinano, i legami si consolidano, e la rete si contrae. Contraendosi, ha meno spazio per l'acqua, e quella in eccesso viene spinta fuori. Ecco la pozzetta sullo yogurt: non è "acqua aggiunta", è acqua che era dentro la rete e che la rete non regge più.

Cosa accelera la strizzata

La sineresi è naturale, ma alcune cose la spingono. La temperatura, spesso: il calore rilassa i legami e lascia la rete libera di riorganizzarsi e contrarsi più in fretta, e gli sbalzi termici e il tempo di conservazione peggiorano le cose. Una rete costruita male: se il gel si è formato troppo in fretta, troppo caldo, o è troppo debole, trattiene peggio l'acqua fin dall'inizio. E in certi casi l'acidità o gli enzimi, che indeboliscono la maglia (nello yogurt, un'acidità eccessiva favorisce lo spurgo). C'è anche un parente che hai già incontrato: nel pane, la stessa logica di rete che si riordina e strizza acqua è la retrogradazione dell'amido — la sineresi è quella famiglia di fenomeni, applicata ai gel.

Le leve che hai davvero

Se un gel "piange", la strada è rinforzare la rete perché trattenga meglio l'acqua. Le leve concrete: aggiungere un aiutante che leghi l'acqua — l'amido è il classico (per questo tante cheesecake e creme ne contengono: addensano e riducono lo spurgo), o gomme e addensanti che rendono la maglia più fitta. Costruire il gel nelle condizioni giuste — non troppo caldo, non troppo in fretta — perché nasca una rete solida invece che fragile. Gestire l'acidità dove conta (yogurt, latticini). E conservare a temperatura stabile, evitando sbalzi e lunghe attese, perché tempo e calore lavorano contro la presa. Nota che è soprattutto una partita che giochi quando formi il gel: a gel fatto e già "piangente", puoi a volte rimescolare, ma la struttura ottimale la decidi al momento della gelificazione.

Come lo verifichi

Il segno è evidente: il liquido che affiora in superficie o che cola quando tagli o servi, e la texture che cambia — un gel che ha spurgato è più compatto e concentrato dove è rimasto, più acquoso dove ha rilasciato. Nei latticini quel liquido è il siero; nelle salse e nelle marmellate è acqua e succhi. E se vuoi capire cosa governa il tuo caso, cambia una cosa per volta: stessa ricetta con un po' d'amido in più (rete più solida), o gelificata a temperatura più bassa, o conservata più fredda e stabile — e guarda quale riduce lo spurgo.

Il bersaglio, letto bene

Non c'è un numero della sineresi: dipende dal tipo di gel, dagli ingredienti, da come e quanto lo conservi. E soprattutto, un po' di tendenza a strizzare è il rovescio di una qualità che spesso vuoi: i gel morbidi e piacevoli da mangiare — lo yogurt cremoso, il ketchup che cola al punto giusto — sono deboli apposta, e proprio per questo tendono a spurgare. Una rete durissima non piange, ma è gommosa. Quindi il bersaglio non è "zero acqua espulsa" a ogni costo, ma la rete giusta per il prodotto: abbastanza salda da non spurgare in modo antiestetico, abbastanza morbida da essere buona. Rinforzi finché serve a tenere l'acqua, senza irrigidire fino a rovinare la texture.""",
            "target": "La rete giusta per il prodotto, non zero acqua: un gel morbido e buono spurga un po' per natura",
        },
        "fen-ganache": {
            "scheda": """Versi la panna calda sul cioccolato, mescoli, e a volte esce una crema liscia, lucida, setosa; altre volte si "impazzisce" — diventa granulosa, unta, con l'olio che affiora e la lucentezza persa. Stessi due ingredienti. È cambiato a che temperatura li hai uniti, o in che proporzione.

La ganache è un'emulsione, esattamente come una maionese o una vinaigrette: grasso e acqua tenuti insieme in una tregua. Solo che qui il grasso è il burro di cacao del cioccolato (più quello della panna) e l'acqua è quella della panna. Capire che è un'emulsione ti dice perché si rompe e come tenerla insieme.

È un'emulsione, con gli stessi problemi di tutte le emulsioni

Cioccolato fuso e panna hanno entrambi una parte grassa e una acquosa. Fare la ganache significa disperdere finemente il grasso in tante goccioline dentro la parte acquosa, e tenerle disperse: è la definizione di emulsione. Quando è ben fatta, il grasso è in microgoccioline uniformi e la texture è liscia e lucida. Quando "impazzisce", quelle goccioline si riuniscono, il grasso si separa dall'acqua e affiora: ecco l'aspetto unto e granuloso. È la stessa rottura della maionese, con lo stesso meccanismo. E come nella maionese, c'è un emulsionante che aiuta: la caseina, una proteina della panna, lavora per tenere insieme grasso e acqua.

Perché si rompe: la temperatura ha due limiti, non uno

Qui c'è la cosa che sorprende. La ganache si rompe se la fai troppo calda, ma anche se la fai troppo fredda. Sono due modi opposti di rompere la stessa emulsione. Troppo calda: il grasso diventa troppo fluido e mobile, le goccioline si muovono tanto e si riuniscono facilmente (è lo stesso motivo per cui il calore fa impazzire le emulsioni). Per questo la panna va scaldata ma non bollita oltre un certo punto: troppo calda "spacca" subito il burro di cacao. Troppo fredda: il burro di cacao inizia a ri-solidificare, a cristallizzare, e in quello stato non si disperde più uniformemente nel liquido — si aggrega e la ganache diventa granulosa. C'è quindi una finestra di temperatura, né bollente né fredda, in cui i due si uniscono lisci.

Le leve che hai davvero

La leva principale è la temperatura, dentro quella finestra: unire cioccolato e panna quando sono caldi al punto giusto — abbastanza da sciogliere il cioccolato, non tanto da destabilizzare il grasso — e mescolare con delicatezza, non con violenza (sbattere aria e agitare troppo destabilizza, come in ogni emulsione). Un frullatore a immersione usato bene aiuta, perché fa goccioline più piccole e uniformi, quindi più stabili — la stessa regola delle gocce piccole dell'emulsione. Poi c'è il rapporto cioccolato/panna, che governa la consistenza finale (più cioccolato = più fermo, da tartufi; meno = più fluido, da colare) ma anche la stabilità, perché il tipo di cioccolato conta: un cioccolato ricco di burro di cacao emulsiona meglio, e il cioccolato bianco — quasi tutto burro di cacao e latte, senza massa di cacao — è il più fragile e si rompe alla minima esagerazione di calore.

E se si è già rotta? A differenza di tante emulsioni, spesso si recupera: reintroducendo un pochino di liquido caldo e mescolando o frullando con decisione si può riformare l'emulsione. Ma è più facile non romperla.

Come lo verifichi

Il segno è visivo e netto: la ganache liscia è omogenea, lucida, setosa; quella rotta è opaca, granulosa, con lucido d'olio che affiora e a volte pozze grasse. Lo vedi mentre mescoli — se da liscia inizia a farsi granulosa o unta, sta cedendo. E se vuoi capire cosa te la rompe, cambia una cosa per volta: stessa ricetta con la panna un po' meno calda, o mescolata più gentilmente, o con un rapporto diverso di cioccolato — e guarda quale ti dà la crema liscia.

Il bersaglio, letto bene

Non c'è un rapporto o una temperatura universali, perché dipendono dall'uso (una ganache da tartufo, una da glassa e una da bere vogliono consistenze diverse) e dal cioccolato (fondente, al latte e bianco hanno contenuti di grasso diversi e reggono temperature diverse). Quello che c'è è una finestra da rispettare — la temperatura giusta per unire senza rompere — e un rapporto scelto in base a cosa devi farci. Il bersaglio non è un numero ma lo stato liscio e lucido, ottenuto unendo dentro la finestra e mescolando con calma. E ricorda che è un'emulsione: la tratti con le stesse attenzioni di una maionese, non come "cioccolato sciolto".""",
            "target": "Una finestra di temperatura da rispettare e un rapporto per l'uso: stato liscio e lucido, non un numero",
        },
        "fen-lievitazione": {
            "scheda": """Due impasti. Uno lievita pieno, alto, con la mollica ariosa; l'altro resta basso e compatto, oppure gonfia e poi al taglio è pieno di buchi sbagliati e crudo. A volte il lievito ha lavorato ma il gas è scappato; a volte c'era la struttura ma il gas non è stato prodotto. Sono due problemi diversi, e confonderli ti fa correggere la cosa sbagliata.

La lievitazione è gonfiare un impasto riempiendolo di gas. Ma dietro ci sono due lavori distinti che devono riuscire entrambi: qualcuno deve produrre il gas, e qualcos'altro deve trattenerlo. Separarli è la chiave per capire perché un pane non viene.

Due lavori diversi: fare il gas e imprigionarlo

Il primo lavoro è produrre gas dentro l'impasto. Il secondo è avere una struttura che lo trattenga, altrimenti il gas se ne va e l'impasto resta piatto — esattamente come in una bevanda gassata aperta, dove la CO₂ scappa se niente la trattiene. Nel pane, chi trattiene il gas è la maglia glutinica: le proteine della farina (glutine), impastate con l'acqua, formano una rete elastica e continua che avvolge ogni bolla come una gabbia flessibile, tenendola dentro mentre l'impasto si gonfia senza strapparsi. Se questa rete è debole o poco sviluppata, il gas fora e scappa: pane basso e denso, per quanto il lievito abbia lavorato.

Quindi: gas prodotto senza struttura = piatto; struttura senza gas = mattone. Servono tutti e due.

Tre modi di fare il gas (che danno pani diversi)

Il gas si può produrre in tre modi, e la scelta cambia tempi e sapore. Il modo biologico: il lievito (o la pasta madre) mangia gli zuccheri della farina e produce anidride carbonica — è lo stesso processo della fermentazione, lento, che oltre a gonfiare sviluppa aroma. Il modo chimico: bicarbonato e lievito per dolci producono CO₂ con una reazione quasi istantanea, senza attesa e senza il sapore di fermentazione — per questo torte, muffin e "quick bread" li usano. E il vapore: l'acqua dell'impasto che in forno diventa vapore e spinge — è il motore di sfoglia, bignè, pasta choux, dove non c'è né lievito né bicarbonato, solo acqua che evapora tra gli strati. Tre motori diversi per lo stesso scopo: riempire di bolle.

L'oven spring: l'ultima spinta in forno

C'è un momento che spiega molto: appena l'impasto entra nel forno caldo, non si ferma, anzi ha uno scatto di crescita finale — l'oven spring. Perché? Il calore fa espandere il gas già presente (un gas caldo occupa più volume), fa uscire altra CO₂ che era disciolta nell'impasto (il calore la scaccia dal liquido, come in una bibita che si scalda), fa evaporare acqua in vapore che spinge, e dà al lievito un'ultima frenesia prima di morire dal caldo. Tutte queste spinte insieme gonfiano il pane un'ultima volta — finché il calore cuoce le proteine e gli amidi, che si solidificano e fissano la struttura per sempre. Da quel momento la forma è quella: il pane è "congelato" nella sua struttura finale.

Le leve — e in quale fase esistono

Prima di correggere, capisci se il tuo problema è gas o struttura, e in che fase sei. Impasto che non cresce? Guarda il gas: lievito attivo? (uno morto o vecchio non gonfia); temperatura giusta? (il freddo rallenta i lieviti, il troppo caldo li uccide, come nella fermentazione); tempo sufficiente? Impasto che cresce ma poi collassa o resta denso al taglio? Guarda la struttura: glutine sviluppato abbastanza da reggere? (impastare/pieghe lo rinforzano); non hai lievitato troppo, fino a sfiancare la maglia che poi cede? E ricorda gli effetti incrociati: i grassi (in un impasto ricco tipo brioche) ammorbidiscono il glutine e lo rendono meno capace di trattenere gas, per questo i pani arricchiti hanno mollica più fine e densa — è un compromesso voluto, non un difetto. La leva vera è quasi tutta prima del forno: una volta cotto, non correggi più niente.

Come lo verifichi

I segni sono tattili e visivi, lungo il processo: l'impasto che cresce di volume, che diventa soffice e "vivo", che alla pressione del dito torna su lentamente (pronto) o resta segnato (troppo lievitato) o rimbalza subito (ancora indietro). In forno, l'oven spring che alza il pane e la crosta che si fissa. Al taglio, la mollica: alveoli regolari e aperti (bene), o densa e compatta (gas o struttura mancati), o grandi buchi vuoti con pareti spesse (struttura squilibrata). E se vuoi capire cosa governa il tuo, cambia una cosa per volta: stesso impasto lievitato più a lungo (più gas), o lavorato di più (più struttura) — e vedi cosa migliora.

Il bersaglio, letto bene

Non c'è un tempo di lievitazione giusto in assoluto, perché dipende da lievito, temperatura, farina, tipo di impasto. E soprattutto il bersaglio non è "il massimo di volume": un impasto lievitato oltre il punto giusto sfianca la maglia e collassa, uno lievitato poco resta denso. Quello che c'è è un punto di maturazione da riconoscere — l'impasto gonfio ma ancora con struttura da spendere in forno per l'oven spring, non già al limite. Il bersaglio è l'equilibrio tra gas prodotto e struttura che lo regge, colto un attimo prima del punto di cedimento. Insegui quel punto, e ricorda che ti serve ancora un po' di spinta per il forno: non arrivare al massimo prima di infornare.""",
            "target": "Punto di maturazione con struttura residua per l'oven spring: equilibrio gas/struttura, non il massimo volume",
        },
        "fen-crosta": {
            "scheda": """Due pani dallo stesso impasto. Uno esce con la crosta sottile, lucida, che scrocchia e si crepa quando lo tagli; l'altro con una crosta spessa, pallida e dura, o gommosa e chiara. Non hai cambiato la ricetta. Hai gestito diversamente l'umidità e il calore sulla superficie.

La crosta non è "il pane che si colora": è una zona a sé, dove la superficie perde acqua, si compatta, e subisce trasformazioni che l'interno non fa. Capire cosa la forma — e in che ordine — ti fa governare la differenza tra una crosta perfetta e una sbagliata.

La crosta è dove succedono più cose insieme

Mentre l'interno del pane resta umido e morbido, la superficie vive un destino diverso: è a contatto col calore secco del forno e perde acqua. Su quella superficie si accavallano tre cose che hai già incontrato separatamente. L'acqua evapora e gli strati esterni si asciugano e si irrigidiscono — è la disidratazione che dà compattezza. L'amido di superficie, finché c'è umidità, assorbe acqua e gelatinizza, formando un gel che poi, asciugandosi, diventa quel guscio lucido e fragile che scrocchia — è la gelatinizzazione, qui in versione superficiale. E, quando la superficie è abbastanza asciutta e calda, partono la reazione di Maillard e la caramellizzazione, che danno colore, aroma e la rigidità dorata. La crosta è il punto in cui disidratazione, gelatinizzazione e doratura si incontrano.

Perché l'ordine conta: prima umido, poi asciutto

Ecco la chiave che spiega perché il vapore in forno cambia tutto. Le tre cose non devono succedere tutte insieme: hanno un ordine giusto. All'inizio serve umidità sulla superficie. Un ambiente umido tiene la superficie morbida e flessibile un po' più a lungo, e questo fa due regali: lascia al pane il tempo di gonfiarsi in forno (l'oven spring) prima che la crosta si fissi e lo "ingabbi", e fa gelatinizzare bene l'amido di superficie, creando quel gel che diventerà croccante e lucido. Poi, nella seconda fase, l'umidità deve andarsene: solo su una superficie che si asciuga davvero la temperatura può salire abbastanza da far partire la doratura di Maillard e da rendere la crosta croccante invece che molle.

Da qui i due errori opposti. Niente umidità all'inizio: la crosta si fissa subito, il pane non si espande, e viene fuori spessa e dura. Troppa umidità fino alla fine: la superficie non si asciuga mai, non brunisce, e resta pallida e gommosa. La crosta giusta nasce dalla sequenza: prima umido per espandere e gelatinizzare, poi asciutto per dorare e rendere croccante.

Le leve che hai davvero

La leva principale è proprio la gestione dell'umidità in forno nel tempo: vapore nella prima fase (una pentola d'acqua, spruzzare, o cuocere in una pentola chiusa che intrappola l'umidità del pane stesso), poi togliere il vapore o aprire per far asciugare e dorare nella seconda. Poi c'è l'idratazione dell'impasto: una superficie più umida di partenza dà più gel di amido e quindi una crosta più "crackly". E il calore: abbastanza alto da dorare e rendere croccante, gestito perché la crosta non bruci prima che l'interno sia cotto. Anche il taglio della superficie (le lame) è una leva: apre una via allo sfogo dei gas e dirige dove il pane si espande e dove la crosta si forma di più.

E dopo il forno? Un errore comune: la crosta perfetta appena sfornata può indurire e diventare coriacea conservandola male. Non è che "si secca" nell'aria — è la stessa retrogradazione dell'amido: raffreddando, l'amido si riordina e attira acqua dalla mollica verso la crosta, che si ammoscia o indurisce. Per questo il pane crosta-croccante va consumato in giornata o conservato in modo da non far migrare quell'acqua.

Come lo verifichi

I segni sono chiari: il colore (dal pallido all'ambrato al bruno — Maillard che avanza), il suono (una crosta pronta "canta", scricchiola; battuta sul fondo suona vuota a cottura giusta), la texture (sottile e fragile che si crepa, o spessa e dura, o molle e gommosa). E il modo in cui si crepa al taglio ti dice della gelatinizzazione superficiale. Se vuoi capire cosa governa la tua crosta, cambia una cosa per volta: stesso pane con vapore nella prima fase o senza, o con più minuti di forno asciutto alla fine — e guarda come cambiano spessore, colore e croccantezza.

Il bersaglio, letto bene

Non c'è "la crosta giusta" universale, perché dipende da cosa fai: una baguette vuole crosta sottile e croccante, un pane in cassetta quasi non la vuole, un bagel (bollito prima di cuocere) la vuole densa e gommosa proprio perché l'amido è gelatinizzato a fondo nell'acqua. Quello che c'è è una crosta-obiettivo legata al prodotto, ottenuta dosando umidità, calore e tempo nella sequenza giusta. Il bersaglio non è un colore o uno spessore astratto ma la crosta che quel pane deve avere — e la ottieni governando quando la superficie sta umida e quando la lasci asciugare. Prima umido per crescere e gelatinizzare, poi asciutto per dorare: è tutta lì la crosta.""",
            "target": "Una crosta legata al prodotto: prima umido per crescere e gelatinizzare, poi asciutto per dorare",
        },
    }
    import json
    try:
        conn = _get_conn()
        cur = conn.cursor()
        updated = []
        for node_id, data in SCHEDE_V2.items():
            cur.execute("SELECT id, data FROM nodes WHERE id=%s", (node_id,))
            row = cur.fetchone()
            if not row:
                updated.append(f"{node_id}: NON TROVATO")
                continue
            raw = row[1] if isinstance(row, (list, tuple)) else row["data"]
            nd = raw if isinstance(raw, dict) else json.loads(raw)
            # scheda: rispetta il formato multilingua se presente
            sch = nd.get("scheda")
            if isinstance(sch, dict):
                sch["it"] = data["scheda"]
                nd["scheda"] = sch
            else:
                nd["scheda"] = data["scheda"]
            nd["target"] = data["target"]
            nd["numero_bersaglio"] = data["target"]
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                        (json.dumps(nd, ensure_ascii=False), node_id))
            updated.append(f"{node_id}: OK ({len(data['scheda'])} chars)")
        conn.commit()
        cur.close()
        _release_conn(conn)
        try:
            from routes.lezione import _lezione_cache as _lc
            _lc.clear()
        except Exception:
            pass
        n_ok = sum(1 for u in updated if ": OK" in u)
        return jsonify({"ok": True, "aggiornati_ok": n_ok, "totale": len(SCHEDE_V2), "dettaglio": updated})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/update-schede")
def admin_update_schede():
    """Aggiorna le schede fenomeni nel DB con contenuto specifico per disciplina."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403

    # Schede aggiornate — fenomeni base con contenuto specifico
    SCHEDE = {
        "fen-acidita": {
            "scheda": """L'acidità è la concentrazione di protoni liberi (H⁺) in soluzione, espressa come pH (scala logaritmica inversa) e come acidità titolabile (quantità totale di acidi, in %).

Al banco del bar: il lime fresco ha acidità titolabile 5-6%, il limone 4.5-5.5%, l'arancia 0.6-0.9%. Un sour bilanciato ha acidità titolabile 1.0-1.5% nel bicchiere finito — sotto quella soglia il drink è piatto, sopra è aggressivo. Il pH da solo non basta: puoi avere pH basso ma poca massa acida.

In panificazione: la pasta madre lavora a pH 3.7-3.9. Sotto 3.5 i lieviti si inibiscono, sopra 4.2 l'impasto manca di struttura. I LAB producono acido lattico (morbido, pH ~2.9) e acetico (tagliente, pKa 4.75).

In vino: pH 3.0-3.4 per bianchi freschi, 3.3-3.5 per rossi. L'acidità tartarica (principale nel vino) non si degrada con la cottura. La malolattica converte il malico (pH ~3.4) in lattico (pH ~3.9), ammorbidendo il vino.

Numero bersaglio: pH 3.7-3.9 pasta madre · sour 1.0-1.5% titolabile · vino bianco pH 3.0-3.4""",
            "target": "pH 3.7-3.9 pasta madre · sour 1.0-1.5% titolabile · vino bianco pH 3.0-3.4"
        },
        "fen-carbonatazione": {
            "scheda": """La carbonatazione è la quantità di CO₂ disciolta in un liquido, espressa in volumi (1 volume = 1L di CO₂ per 1L di liquido) o g/L.

Legge di Henry: la solubilità della CO₂ è proporzionale alla pressione e inversamente proporzionale alla temperatura. Ogni grado in più riduce la CO₂ disciolta. Un bicchiere a temperatura ambiente disperde le bollicine in secondi.

Numeri al banco: cocktail/highball 2.5-3.5 vol · birra 2.0-3.0 vol · champagne/spumante 5.0-6.0 vol · water kefir 1.5-2.5 vol.

Errori comuni: bicchiere caldo, ghiaccio tritato (superficie enorme = CO₂ dispersa rapidamente), mescolare dopo la versata. Il dry shake prima della carbonatazione distrugge le bollicine.

Servizio: bicchiere a 0-2°C, ghiaccio in blocco, versata inclinata a 45°, nessun mescolamento dopo.

Numero bersaglio: gin tonic 3.8 vol · birra artigianale 2.0-2.8 vol · prosecco 4.0-5.5 vol""",
            "target": "gin tonic 3.8 vol · birra 2.0-3.0 vol · champagne 5.0-6.0 vol"
        },
        "fen-concentrazione": {
            "scheda": """La concentrazione è il rapporto soluto/solvente in una soluzione. Si esprime in % (p/p o v/v), Brix (°Bx = g zucchero/100g soluzione), ABV (alcol per volume), TDS (solidi totali disciolti).

Al banco: un sour ha ~16% ABV nel bicchiere finito, 10-12 Brix. Lo sciroppo semplice è 50 Brix (1:1 p/p), il rich syrup 66 Brix (2:1). Il tonic commerciale è ~8 Brix.

In panificazione: idratazione 60-85% (acqua/farina). Sale 2-2.5% sulla farina — sopra inibisce i lieviti, sotto la struttura glutinica è debole. Zucchero >35% nel panettone crea stress osmotico.

In gelateria: mix gelato 32-38 Brix totali. TDS espresso 7-12%, EY 18-22%.

Concentrare per evaporazione aumenta Brix ma può bruciare gli aromi volatili a >80°C. Concentrare per freddo (freeze concentration) preserva gli aromi.

Numero bersaglio: sciroppo 1:1 = 50 Brix · sour finito 10-12 Brix · salamoia 2-3%""",
            "target": "sciroppo 1:1 = 50 Brix · sour finito 10-12 Brix · salamoia 2-3%"
        },
        "fen-fermentazione": {
            "scheda": """La fermentazione è la conversione anaerobica degli zuccheri in alcol + CO₂ (alcolica) o acidi organici (lattica, acetica) da parte di lieviti e batteri.

Saccharomyces cerevisiae: attivo 18-35°C, ottimale 20-28°C. Produce 1g etanolo per 1.7g glucosio. Inibito da pH <3.5, alcol >15%, Aw <0.92, zucchero >35%.

In pasta madre: Kazachstania humilis (ex Candida humilis) domina la flora lievitante, tollerando pH fino a 3.5 e acido acetico. I LAB (Lactobacillus sanfranciscensis) lavorano in parallelo producendo acido lattico e acetico in rapporto dipendente da temperatura e idratazione. pKa acido acetico = 4.76, pKa acido lattico = 3.86.

In birra: fermentazione alta (ale) 18-22°C, bassa (lager) 8-14°C. Densità iniziale (OG) 1.040-1.080, finale (FG) 1.008-1.020. Efficienza mash 75-85%.

Q10 = 2: ogni 8-10°C in più raddoppia la velocità di fermentazione. Fondamentale in estate.

Numero bersaglio: fermentazione pasta madre 24-27°C · birra ale 18-22°C · lager 8-14°C · Q10 bulk 6-10h a 24°C""",
            "target": "pasta madre 24-27°C · ale 18-22°C · lager 8-14°C · Q10 raddoppia ogni 8-10°C"
        },
        "fen-osmosi": {
            "scheda": """L'osmosi è il passaggio spontaneo dell'acqua attraverso una membrana semipermeabile da zona a bassa concentrazione soluti verso zona ad alta concentrazione (gradiente osmotico).

In panificazione: il sale va aggiunto DOPO il lievito — in contatto diretto crea un gradiente osmotico che disidrata le cellule di lievito, inibendo la fermentazione. Salamoia sicura: 2-3% sale sul peso totale. Il panettone ha zucchero >35%: crea osmosi anche senza sale aggiunto.

In gelateria: zuccheri iperosmotici (glucosio, fruttosio, destrosio) abbassano il punto di congelamento per depressione del punto crioscopico. PAC destrosio = 190, saccarosio = 100, fruttosio = 190.

In fermentazione: zucchero >35% inibisce S.cerevisiae per stress osmotico (Aw <0.92). Miele Aw <0.60: nessun microrganismo cresce.

In cottura: il sale sulle verdure crea osmosi che estrae l'acqua dalle cellule — ecco perché diventano molli se salate troppo presto.

Numero bersaglio: salamoia sicura 2-3% · panettone zucchero max 35% · miele Aw <0.60""",
            "target": "salamoia 2-3% · panettone zucchero max 35% · Aw miele <0.60"
        },
        "fen-emulsione": {
            "scheda": """Un'emulsione è una dispersione stabile di due liquidi immiscibili (acqua e olio) stabilizzata da molecole anfifile (emulsionanti) che si posizionano all'interfaccia abbassando la tensione superficiale.

Maionese e salse: le lecitine del tuorlo (fosfatidilcolina) stabilizzano gocce d'olio di 0.5-20 micron. Temperatura ottimale degli ingredienti: 18-20°C. Aggiungere l'olio a 1-2 ml/s — più veloce e le gocce coalescono. Il pH 4.0-4.5 (limone/aceto) stabilizza ulteriormente l'emulsione per carica elettrostatica.

Panna montata: emulsione aria/grassi. Temperatura critica: 4-8°C — sopra i 10°C i cristalli di grasso fondono e la schiuma collassa. Panna minimo 35% grassi.

Latte: emulsione naturale stabilizzata da caseine (80%) e sieroproteine (20%). Temperatura vapore: 65-68°C. Sopra 70°C le sieroproteine denaturano e la schiuma diventa instabile.

Ganache: emulsione cioccolato/panna. Ratio panna/cioccolato 1:1 per ganache morbida, 1:2 per tartufabile. Temperatura di emulsione: 40-45°C. Cristallizzazione tipo V a 27-29°C.

Numero bersaglio: maionese pH 4.0-4.5 · panna montata 4-8°C · latte vapore 65-68°C · ganache emulsione 40-45°C""",
            "target": "maionese pH 4.0-4.5 · panna montata 4-8°C · latte vapore 65-68°C"
        },
        "fen-maillard": {
            "scheda": """La reazione di Maillard è la condensazione non enzimatica tra un aminoacido e uno zucchero riducente (reazione di Amadori) che produce centinaia di composti aromatici bruni a >140°C.

Tre leve al banco: (1) Temperatura — superficie deve superare 140°C. Il vapore la blocca a 100°C: asciuga bene prima di cuocere. (2) pH — ambienti alcalini (bicarbonato, pH >7) accelerano la reazione: ecco perché i bretzel si immergono in soda caustica. pH acido la rallenta. (3) Umidità — Aw <0.6 in superficie favorisce la reazione. Forno ventilato o griglia asciuga meglio del forno statico.

In panetteria: crosta bruna richiede 150-200°C in superficie. Vapore nei primi 15 minuti impedisce la crosta — poi si apre il forno per asciugare. Zuccheri riducenti (maltosio dal malto) migliorano la doratura.

In bar/cocktail: caramellare il bordo di un bicchiere con zucchero brucia (150-180°C) attiva Maillard. Il caffè tostato deve 800+ composti aromatici a questa reazione.

Errore comune: padella a 160-170°C troppo bassa — serve almeno 180°C in superficie per reazione rapida. Target ottimale padella preriscaldata: 200-220°C. Carne umida = vapore = blocco Maillard.

Numero bersaglio: >140°C per innesco · 150-200°C per crosta · pH >7 accelera · Aw <0.6 in superficie""",
            "target": ">140°C innesco · 150-200°C crosta · pH >7 accelera · Aw <0.6 superficie"
        },
        "fen-denaturazione": {
            "scheda": """La denaturazione è la perdita irreversibile della struttura tridimensionale di una proteina per effetto di calore, pH estremo, sale o agitazione meccanica. Le catene proteiche si srotolano esponendo i gruppi idrofobici interni.

Temperature critiche al banco:
· Miosina (carne rossa): 50°C → cottura al rosa, succosa
· Actina (carne): 65-70°C → carne asciutta, stopposa  
· Albume (uovo): inizia a 63°C, completo a 82°C
· Tuorlo: inizia a 65°C, sodo a 70°C
· Latte (sieroproteine): 65-68°C → schiuma stabile cappuccino; sopra 70°C schiuma instabile
· Collagene → gelatina: >70°C prolungato (brasato 3-6h a 80-90°C)

Errori comuni: latte cappuccino sopra 70°C perde capacità schiumogena. Uova pastorizzate a 63°C per 3-5 minuti (Salmonella inattivata). Panna montata sopra 10°C: le proteine non trattengono le bolle.

Sous vide sfrutta la denaturazione selettiva: 52°C per 1h denatura miosina (tenera) senza denaturare actina (succosa).

Numero bersaglio: miosina 50°C · uovo fondente 63-65°C · latte cappuccino 65-68°C · collagene→gelatina >70°C x 3h""",
            "target": "miosina 50°C · uovo fondente 63-65°C · latte vapore 65-68°C · collagene>gelatina 70°C"
        },
        "fen-cristallizzazione": {
            "scheda": """La cristallizzazione è l'organizzazione di molecole in strutture ordinate ripetitive. In F&B riguarda principalmente zuccheri, grassi e ghiaccio.

Zucchero/caramello: il saccarosio cristallizza in soluzione sovrasatura (>67 Brix a 20°C). Per evitarlo: aggiungere glucosio (10-20%) che interferisce con la formazione reticolare, o sciroppo invertito. Temperatura sciroppo 1:1: cuocere a 105-110°C per stabilizzare. Nuclei di cristallizzazione (granelli di zucchero, residui) innescano la cristallizzazione — mantieni gli utensili puliti.

Cioccolato (burro di cacao): 6 forme cristalline. Solo la Forma V (beta) dà lucentezza e snap. Temperaggio: fondere a 45-50°C → raffreddare a 27°C → risalire a 31-32°C (fondente) o 29-30°C (latte). Bloom bianco = transizione Forma V→VI per temperatura instabile o stoccaggio errato.

Gelato: cristalli di ghiaccio <50 micron = cremoso, >100 micron = granuloso. Mantecazione rapida + zuccheri (PAC alto) = cristalli fini. Temperatura uscita mantecatore: -6/-8°C.

Numero bersaglio: sciroppo stabile 105-110°C · temperaggio fondente 31-32°C · gelato cristalli <50 micron · stoccaggio cioccolato 16-18°C""",
            "target": "sciroppo 105-110°C · temperaggio fondente 31-32°C · cristalli gelato <50 micron"
        },
        "fen-estrazione": {
            "scheda": """L'estrazione è il trasferimento di composti solubili da una matrice solida a un solvente liquido per diffusione. La velocità dipende da temperatura, granulometria, pressione e rapporto soluto/solvente.

Caffè espresso: EY (Extraction Yield) 18-22% = percentuale di caffè estratta dalla dose. TDS 7-12% = solidi disciolti nella tazza. Ratio 1:2 (18g → 36g). Temperatura acqua 90-96°C. Tempo 25-30s. Sotto 18% EY: acido e piatto. Sopra 22%: amaro e legnoso.

Caffè filtro: TDS target 1.15-1.55%, EY 18-22%, ratio 1:15-1:17. Temperatura 90-96°C. Tempo 3-4 minuti.

Cold brew: EY 18-20%, ratio 1:8-1:10, 12-24h a 4-18°C. Bassa temperatura = estrazione lenta, meno acidità, meno caffeina. Sopra 18h: tannini amari.

Moka: TDS 1.2-1.8%, temperatura in estrazione 85-92°C. Fiamma bassa = estrazione più lenta e uniforme.

Errori comuni: macinatura troppo grossa = sotto-estrazione (acido), troppo fine = sovra-estrazione (amaro). Temperatura acqua <85°C blocca l'estrazione degli esteri aromatici.

Numero bersaglio: espresso EY 18-22% · TDS espresso 7-12% · filtro TDS 1.15-1.55% · temperatura 90-96°C""",
            "target": "espresso EY 18-22% · TDS 7-12% · temperatura 90-96°C · ratio 1:2"
        },
        "fen-gelatinizzazione": {
            "scheda": """La gelatinizzazione è il rigonfiamento irreversibile dei granuli di amido in acqua calda (>60°C) con perdita della struttura cristallina e formazione di un gel. Segue la retrogradazione: ricristallizzazione parziale al raffreddamento.

Temperature di gelatinizzazione per amido:
· Frumento: 58-64°C
· Mais: 62-72°C  
· Patata: 58-66°C
· Riso: 68-78°C
· Segale: 57-70°C (più bassa = problema in panificazione)

In panificazione: l'amido gelatinizza in cottura trattenendo l'acqua nella mollica. La segale ha enzimi amilolitici attivi fino a 70°C — senza pH 4.0-4.5 (pasta acida) degradano l'amido gelatinizzato e il pane è appiccicoso. Temperatura interna minima pane di segale: 93-96°C.

Retrogradazione: l'amilosio ricristallizza in poche ore (raffermamento veloce), l'amilopectina in giorni. Conservazione a 4°C accelera la retrogradazione — il freezer (-18°C) la blocca.

Crema pasticcera: amido mais o frumento come addensante. Cuoci a 82-85°C per 1-2 minuti per inattivare le amilasi della farina.

Numero bersaglio: gelatinizzazione frumento 58-64°C · segale 57-70°C · crema pasticcera 82-85°C · retrogradazione massima 4-8°C""",
            "target": "gelatinizzazione frumento 58-64°C · pane segale T interna 96-98°C · crema 82-85°C"
        },
        "fen-ossidazione": {
            "scheda": """L'ossidazione è la reazione di molecole organiche con l'ossigeno, che degrada aromi, colori e strutture. In F&B è la principale causa di deterioramento qualitativo.

In vino: l'ossigeno dissolto reagisce con polifenoli e alcoli formando aldeidi (acetaldeide = sherry/mela appassita) e composti bruniti. SO₂ libera >25 mg/L protegge il vino bianco. Temperatura: ogni 10°C in più raddoppia la velocità di ossidazione. Vino bianco aperto: consumare entro 24-48h conservato a 4°C.

In birra: ossigeno residuo >0.5 mg/L accelera il day-light skunking (mercaptani) e l'ossidazione degli aromi luppolati. IPA: consumare entro 30 giorni dall'imbottigliamento. Stout: più resistente per presenza di antiossidanti dai malti tostati.

In olio: ossidazione degli acidi grassi polinsaturi (linoleico, linolenico) = irrancidimento. Punto fumo: olio extravergine 180-210°C, olio di girasole ad alto oleico 230°C. Conservare al buio e <20°C.

In caffè: la CO₂ nel caffè appena tostato protegge dall'ossigeno. Degassing 3-7 giorni post-tostatura. Dopo 30 giorni gli aromi volatili si degradano per ossidazione.

Numero bersaglio: SO₂ libera vino bianco >25 mg/L · O₂ residuo birra <0.5 mg/L · olio extravergine punto fumo 180-210°C""",
            "target": "SO₂ vino >25 mg/L · O₂ birra <0.5 mg/L · punto fumo EVO 180-210°C"
        },
        "fen-crioscopia": {
            "scheda": """L'abbassamento crioscopico è la depressione del punto di congelamento di una soluzione rispetto al solvente puro, proporzionale alla concentrazione di soluti (legge di Raoult).

In gelateria: ogni soluto abbassa il punto di congelamento di una quantità proporzionale al suo PAC (Potere Anti-Congelante, relativo al saccarosio = 100).

PAC degli zuccheri principali:
· Saccarosio: 100
· Destrosio (glucosio): 190
· Fruttosio: 190
· Lattosio: 40
· Sorbitolo: 190
· Maltodestrine: 10-15 (DE 10-20)

Calcolo PAC totale: somma di (grammi zucchero × PAC) / 1000. Target gelato artigianale cremoso: PAC 260-320. Sorbetto: PAC 300-380 (no grassi = cristalli più grandi).

Temperatura di servizio: gelato -11/-13°C (spatolabile), sorbetto -13/-15°C. Temperatura pozzetto conservazione: -18°C (cristalli stabili).

Errore comune: PAC basso = gelato durissimo a -18°C e granuloso in bocca. PAC troppo alto = gelato troppo morbido, si scioglie al banco.

Numero bersaglio: PAC gelato 260-320 · sorbetto 300-380 · T servizio -11/-13°C · T conservazione -18°C""",
            "target": "PAC gelato 260-320 · sorbetto 300-380 · T servizio -11/-13°C"
        },
        "fen-overrun": {
            "scheda": """L'overrun è la percentuale di aria incorporata nel gelato durante la mantecazione, calcolata come: (volume finale - volume iniziale) / volume iniziale × 100.

Formula pratica: se 1L di mix diventa 1.3L di gelato → overrun = 30%.

Target per categoria:
· Gelato artigianale italiano: 20-35%
· Gelato industriale: 50-100%
· Sorbetto: 10-20% (meno aria per struttura più densa)
· Semifreddo: 80-120% (struttura aerea)

Effetti dell'overrun: più aria = più morbido, si scioglie più velocemente, sapore meno intenso. Meno aria = più denso, freddo in bocca più intenso, più difficile da spalmare.

Controllo: pesa 1L di gelato appena uscito dal mantecatore. Gelato a 35% overrun = 750g/L. Gelato a 25% = 800g/L. Gelato industriale a 80% = 550g/L.

Temperatura uscita mantecatore: -6/-8°C. Abbattitore rapido a -40°C per bloccare la crescita dei cristalli prima dello stoccaggio.

Errore comune: overrun troppo alto (>40%) nel gelato artigianale = prodotto acquoso, si scioglie subito, sapore diluito.

Numero bersaglio: overrun artigianale 20-35% · peso gelato 750-800g/L · T uscita mantecatore -6/-8°C""",
            "target": "overrun artigianale 20-35% · peso 750-800g/L · T uscita mantecatore -6/-8°C"
        },
        "fen-diluizione": {
            "scheda": """La diluizione in miscelazione è l'aggiunta di acqua (da fusione del ghiaccio o da mixing) a una soluzione alcolica, riducendo l'ABV e modificando la struttura sensoriale del drink.

Shake: 20-28% di diluizione sul volume finale. L'agitazione violenta frantuma il ghiaccio aumentando la superficie di contatto e accelerando la fusione. Temperatura finale: -2/-4°C.

Stir: 15-22% di diluizione. Ghiaccio intero, contatto più lento. Temperatura finale: -4/-6°C. Meno diluizione per drink spirit-forward (Negroni, Manhattan, Old Fashioned).

Build: 10-18% di diluizione. Il ghiaccio nel bicchiere fonde lentamente durante il consumo — la diluizione aumenta nel tempo.

Calcolo: ABV finale = (ml spirito × ABV spirito) / (ml totali). Con Negroni 30+30+30ml a 40%+16%+25%: ABV pre-diluizione = 27%. Con 20% diluizione: 90ml → 108ml, ABV finale ≈ 22.5%.

Errore comune: ghiaccio in piccoli cubetti nello shaker = troppe superfici = diluizione eccessiva (>30%). Usa ghiaccio in blocchi grandi.

Numero bersaglio: shake 20-28% diluizione · stir 15-22% · T finale shake -2/-4°C · Negroni stirred ABV finale 22-24%""",
            "target": "shake 20-28% diluizione · stir 15-22% · T finale -4/-6°C"
        },
    }

    try:
        conn = _get_conn()
        cur = conn.cursor()
        updated = []
        for node_id, data in SCHEDE.items():
            # Leggi il nodo
            cur.execute("SELECT id, data FROM nodes WHERE id=%s", (node_id,))
            row = cur.fetchone()
            if not row:
                updated.append(f"{node_id}: NON TROVATO")
                continue
            
            import json
            # row può essere tuple (id, data) o _PgRow dict-like
            raw_data = row[1] if isinstance(row, (list, tuple)) else row["data"]
            nd = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)
            
            # Aggiorna scheda e target
            nd["scheda"] = data["scheda"]
            nd["target"] = data["target"]
            
            cur.execute(
                "UPDATE nodes SET data=%s WHERE id=%s",
                (json.dumps(nd, ensure_ascii=False), node_id)
            )
            updated.append(f"{node_id}: OK ({len(data['scheda'])} chars)")
        
        conn.commit()
        cur.close()
        _release_conn(conn)
        
        # Invalida cache lezioni (la variabile vive in routes.lezione)
        try:
            from routes.lezione import _lezione_cache as _lc
            _lc.clear()
        except Exception:
            pass
        
        return jsonify({"ok": True, "aggiornati": updated})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/insert-test-ricetta")
def admin_insert_test_ricetta():
    """Inserisce una ricetta di test per mrovazzi8@gmail.com — uso singolo."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    try:
        conn = _get_conn()
        cur = conn.cursor()
        # Trova user_id
        cur.execute("SELECT id FROM utenti WHERE email='mrovazzi8@gmail.com'")
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"errore": "utente non trovato"}), 404
        user_id = row[0] if isinstance(row, (list, tuple)) else row["id"]
        # Inserisci 3 ricette di test
        ricette = [
            ("Negroni House", "bar", '["Gin","Campari","Vermut rosso"]', None, None, 22.0),
            ("Sour al limone", "bar", '["Bourbon","Limone","Sciroppo semplice"]', 3.2, None, None),
            ("Focaccia madre", "panificazione", '["Farina","Acqua","Sale","Lievito madre"]', 3.8, None, None),
        ]
        ids = []
        for nome, disc, ing, ph, brix, abv in ricette:
            cur.execute(
                "INSERT INTO esperimenti (user_id, nome, disciplina, ingredienti, ph, brix, abv, ts) VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, NOW()) RETURNING id",
                (user_id, nome, disc, ing, ph, brix, abv)
            )
            ids.append(cur.fetchone()[0])
        conn.commit()
        cur.close()
        _release_conn(conn)
        return jsonify({"ok": True, "ids": ids, "messaggio": f"3 ricette inserite per user_id {user_id}"})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/build")
def admin_build_page():
    secret = request.args.get("s","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "<h2>Secret non valido</h2>", 403
    from flask import send_from_directory
    return send_from_directory("static", "build.html")

@bp.route("/admin/build-archi", methods=["POST"])
def admin_build_archi():
    """Crea archi abbinamento tra nodi Ingrediente già nel grafo."""
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    import threading
    def _run():
        try:
            import build_ingredient_graph as BIG
            BIG.build_archi()
        except Exception as e:
            print(f"[ARCHI] errore: {e}", flush=True)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "messaggio": "Creazione archi avviata in background (~2-3 min)"})

@bp.route("/admin/build-targets", methods=["POST"])
def admin_build_targets():
    """Popola target number nei nodi Ingrediente."""
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    import threading
    def _run():
        try:
            import build_ingredient_graph as BIG
            BIG.build_target_numbers()
        except Exception as e:
            print(f"[TARGETS] errore: {e}", flush=True)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "messaggio": "Popolamento target avviato in background (~1 min)"})

@bp.route("/admin/debug-ingredienti")
def admin_debug_ingredienti():
    """Debug: mostra quanti ingredienti vede il server nel modulo."""
    secret = request.args.get("s","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    try:
        import importlib, build_ingredient_graph as BIG
        importlib.reload(BIG)
        per_disc = {d: len(ings) for d, ings in BIG.INGREDIENTI.items()}
        totale = sum(per_disc.values())
        return jsonify({"totale": totale, "per_disciplina": per_disc})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/build-cron", methods=["POST","GET"])
def admin_build_cron():
    """Endpoint per cron job — genera UN ingrediente per chiamata.
    Railway può chiamarlo ogni 30 secondi via cron.
    Alternativa: chiamarlo in loop dal browser con setInterval.
    """
    secret = request.args.get("s","") or request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL or not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"ok":False,"errore":"config mancante"}), 503
    try:
        import psycopg2, importlib
        import build_ingredient_graph as BIG
        importlib.reload(BIG)

        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT node_id FROM ingredient_build_log")
            gia_fatti = {r[0] for r in cur.fetchall()}
        except Exception:
            gia_fatti = set()
        cur.close(); _release_conn(conn)

        # Trova il prossimo
        prossimo = None
        for d, ings in BIG.INGREDIENTI.items():
            for ing in ings:
                if BIG.node_id(ing) not in gia_fatti:
                    prossimo = (d, ing)
                    break
            if prossimo:
                break

        if not prossimo:
            return jsonify({"ok":True,"completato":True,"totale":len(gia_fatti)})

        d, ing = prossimo
        profilo, usage = BIG.gpt_ingrediente(ing, d)
        conn_ing = _get_conn()
        try:
            BIG.salva_in_grafo(conn_ing, ing, d, profilo)
            _release_conn(conn_ing)
        except Exception as db_e:
            try: conn_ing.rollback(); _release_conn(conn_ing)
            except: pass
            return jsonify({"ok":False,"errore":str(db_e)[:80]})

        return jsonify({
            "ok": True,
            "completato": False,
            "ingrediente": ing,
            "disciplina": d,
            "totale": len(gia_fatti) + 1,
            "token": usage.get("total_tokens",0)
        })
    except Exception as e:
        return jsonify({"ok":False,"errore":str(e)[:100]}), 500

@bp.route("/admin/build-continuo", methods=["POST"])
def admin_build_continuo():
    """Build continuo in background con checkpoint su DB.
    Gira finché non finisce — non dipende dal browser.
    Usa threading con loop interno che salva ogni ingrediente.
    """
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL or not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"errore":"DATABASE_URL o OPENAI_API_KEY mancante"}), 503

    import threading, importlib

    def _run_continuo():
        import psycopg2, importlib, time as _time
        try:
            import build_ingredient_graph as BIG
            importlib.reload(BIG)
        except Exception as e:
            print(f"[BUILD_C] import error: {e}", flush=True)
            return

        print(f"[BUILD_C] Avvio build continuo — {sum(len(v) for v in BIG.INGREDIENTI.values())} ingredienti totali", flush=True)
        
        while True:
            # Prendi il prossimo ingrediente non ancora fatto
            try:
                conn = _get_conn()
                cur = conn.cursor()
                try:
                    cur.execute("SELECT node_id FROM ingredient_build_log")
                    gia_fatti = {r[0] for r in cur.fetchall()}
                except Exception:
                    gia_fatti = set()
                cur.close(); _release_conn(conn)
            except Exception as e:
                print(f"[BUILD_C] DB error: {e}", flush=True)
                _time.sleep(5)
                continue

            # Trova il prossimo da fare
            prossimo = None
            for d, ings in BIG.INGREDIENTI.items():
                for ing in ings:
                    if BIG.node_id(ing) not in gia_fatti:
                        prossimo = (d, ing)
                        break
                if prossimo:
                    break

            if not prossimo:
                print(f"[BUILD_C] COMPLETATO! Totale: {len(gia_fatti)}", flush=True)
                break

            d, ing = prossimo
            try:
                profilo, usage = BIG.gpt_ingrediente(ing, d)
                conn_ing = _get_conn()
                try:
                    BIG.salva_in_grafo(conn_ing, ing, d, profilo)
                    _release_conn(conn_ing)
                except Exception as db_e:
                    try: conn_ing.rollback(); _release_conn(conn_ing)
                    except: pass
                tok = usage.get("total_tokens",0)
                print(f"[BUILD_C] ✓ {ing[:40]} ({tok} tok)", flush=True)
            except Exception as e:
                print(f"[BUILD_C] ✗ {ing[:40]}: {str(e)[:60]}", flush=True)
            
            _time.sleep(0.2)

    t = threading.Thread(target=_run_continuo, daemon=True)
    t.start()
    return jsonify({"ok": True, "messaggio": "Build continuo avviato — gira in background fino al completamento. Controlla /admin/build-status per lo stato."})

@bp.route("/admin/build-batch", methods=["POST"])
def admin_build_batch():
    """Genera un batch di N ingredienti e si ferma.
    Non va in timeout perché è sincrono e limitato.
    Chiamare ripetutamente finché totale_generati non aumenta.
    Body: {"n": 20, "discipline": ["cucina"]}  # opzionali
    """
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    body = request.json or {}
    n = int(body.get("n", 20))
    discipline = body.get("discipline", None)
    if not DATABASE_URL or not os.environ.get("OPENAI_API_KEY"):
        return jsonify({"errore":"DATABASE_URL o OPENAI_API_KEY mancante"}), 503
    try:
        import importlib, build_ingredient_graph as BIG
        importlib.reload(BIG)  # forza rilettura file aggiornato
        import psycopg2
        # Prendi gli ingredienti non ancora generati
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT node_id FROM ingredient_build_log")
            gia_fatti = {r[0] for r in cur.fetchall()}
        except Exception:
            gia_fatti = set()
        cur.close(); _release_conn(conn)

        DISC = discipline or list(BIG.INGREDIENTI.keys())
        da_fare = [(d, ing) for d in DISC
                   for ing in BIG.INGREDIENTI.get(d, [])
                   if BIG.node_id(ing) not in gia_fatti]

        da_fare = da_fare[:n]
        if not da_fare:
            return jsonify({"ok": True, "generati": 0, 
                "messaggio": "Nessun ingrediente da generare",
                "debug": {"totale_lista": sum(len(v) for v in BIG.INGREDIENTI.values()),
                          "gia_fatti": len(gia_fatti),
                          "da_fare_totale": sum(1 for d in BIG.INGREDIENTI for ing in BIG.INGREDIENTI[d] if BIG.node_id(ing) not in gia_fatti)}})

        ok = 0; errori = []; token_tot = 0
        for disc, ing in da_fare:
            try:
                profilo, usage = BIG.gpt_ingrediente(ing, disc)
                tok = usage.get("total_tokens", 0)
                conn_ing = _get_conn()
                try:
                    BIG.salva_in_grafo(conn_ing, ing, disc, profilo)
                    _release_conn(conn_ing)
                except Exception as db_e:
                    try: conn_ing.rollback(); _release_conn(conn_ing)
                    except: pass
                    errori.append(f"{ing}: {str(db_e)[:40]}")
                    continue
                token_tot += tok
                ok += 1
            except Exception as e:
                errori.append(f"{ing}: {str(e)[:40]}")

        costo = token_tot * 0.000000375
        return jsonify({
            "ok": True,
            "generati": ok,
            "errori": len(errori),
            "token": token_tot,
            "costo": f"${costo:.3f}",
            "prossimo_batch": len(da_fare) - ok > 0
        })
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/build-ingredienti", methods=["POST"])
def admin_build_ingredienti():
    """Lancia il build del dataset ingredienti in un thread background.
    Autenticato con ADMIN_SECRET. Non dipende dalla Console Railway.
    
    POST /admin/build-ingredienti
    Header: X-Admin-Secret: <ADMIN_SECRET>
    Body: {"discipline": ["bar","cucina"]}  # opzionale, default = all
    
    Risposta immediata — il build gira in background.
    Controlla lo stato con GET /admin/build-status
    """
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    
    body = request.json or {}
    discipline = body.get("discipline", None)  # None = tutte
    
    import threading
    
    def _run_build():
        try:
            import build_ingredient_graph as BIG
            BIG.build(discipline=discipline)
        except Exception as e:
            print(f"[BUILD] errore: {e}", flush=True)
    
    t = threading.Thread(target=_run_build, daemon=True)
    t.start()
    
    return jsonify({
        "ok": True,
        "messaggio": "Build avviato in background. Controlla /admin/build-status per lo stato.",
        "discipline": discipline or "tutte"
    })

@bp.route("/admin/build-status")
def admin_build_status():
    """Stato del dataset ingredienti."""
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"no db"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT disciplina, COUNT(*) as n
            FROM ingredient_build_log
            GROUP BY disciplina ORDER BY n DESC
        """)
        per_disc = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM ingredient_build_log")
        totale = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Ingrediente'")
        nodi = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        return jsonify({
            "totale_generati": totale,
            "nodi_ingrediente": nodi,
            "per_disciplina": per_disc
        })
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/seed-sicurezza", methods=["POST"])
def admin_seed_sicurezza():
    """Esegue i seed di sicurezza alimentare nel DB Postgres."""
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"no db"}), 503
    import psycopg2, glob, os as _os
    conn = _get_conn()
    cur = conn.cursor()
    seed_files = [
        "grafo/seed-fenomeno-aw.sql",
        "grafo/seed-sicurezza-zona-pericolo.sql",
        "grafo/seed-sicurezza-shelf-life.sql",
        "grafo/seed-sicurezza-contaminazione.sql",
        "grafo/seed-sicurezza-atmosfera-modificata.sql",
        "grafo/seed-agganci-sicurezza.sql",
        "grafo/seed-principio-dvalue.sql",
    ]
    ok = []; errori = []
    for f in seed_files:
        if not _os.path.exists(f):
            errori.append(f"{f}: non trovato")
            continue
        try:
            sql = open(f, encoding="utf-8").read()
            # Usa savepoint per isolare ogni file
            cur.execute(f"SAVEPOINT sp_{ok.__len__()}")
            try:
                cur.execute(sql)
                cur.execute(f"RELEASE SAVEPOINT sp_{ok.__len__()}")
                ok.append(f)
            except Exception as e:
                cur.execute(f"ROLLBACK TO SAVEPOINT sp_{ok.__len__()}")
                err_msg = str(e)[:80]
                if "already exists" in err_msg or "duplicate" in err_msg.lower():
                    ok.append(f"(già presente) {f}")
                else:
                    errori.append(f"{f}: {err_msg}")
        except Exception as e:
            errori.append(f"{f}: {str(e)[:60]}")
    conn.commit(); cur.close(); _release_conn(conn)
    return jsonify({"ok": ok, "errori": errori})

@bp.route("/admin")
def admin_ui():
    """GT10 — Admin UI grafica."""
    return """<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matter · Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f5ede3;color:#2a1f14;min-height:100vh}
.top{background:#3d2b1f;color:#f0e0cc;padding:14px 24px;display:flex;align-items:center;justify-content:space-between}
.top h1{font-size:16px;font-weight:700}.top span{font-size:10px;color:#c4a882}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px}
.card{background:#fff;border:0.5px solid #e0d4c8;border-radius:12px;padding:20px;margin-bottom:16px}
.card h2{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#8a7a6a;margin-bottom:12px}
.row{display:flex;gap:10px}.row input{flex:1;border:1px solid #e0d4c8;border-radius:8px;padding:10px 14px;font-size:14px;background:#f5ede3;outline:none}
.row input:focus{border-color:#c4622d}
button{background:#3d2b1f;color:#f0e0cc;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:600;cursor:pointer}
.err{color:#c4622d;font-size:12px;margin-top:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.sc{background:#fff;border:0.5px solid #e0d4c8;border-radius:10px;padding:14px}
.sc .n{font-size:26px;font-weight:700;color:#3d2b1f;font-variant-numeric:tabular-nums}
.sc .l{font-size:11px;color:#8a7a6a;margin-top:4px}
.sc.g .n{color:#2e7d52}.sc.o .n{color:#c4622d}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:7px;font-size:12px}
.bar-lbl{width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-t{flex:1;background:#f5ede3;border-radius:4px;height:8px;overflow:hidden}
.bar-f{height:100%;background:#c4622d;border-radius:4px}
.bar-n{font-size:11px;color:#8a7a6a;width:28px;text-align:right}
.big{font-size:24px;font-weight:700;color:#3d2b1f}
.sub{font-size:11px;color:#8a7a6a;margin-top:3px;margin-bottom:12px}
#dash{display:none}
.ref{background:none;border:1px solid #e0d4c8;color:#8a7a6a;font-size:11px;padding:6px 12px;border-radius:6px;cursor:pointer}
@media(max-width:600px){.two{grid-template-columns:1fr}}
</style></head><body>
<div class="top"><h1>Matter · Admin</h1><span id="ts"></span></div>
<div class="wrap">
<div class="card" id="auth">
  <h2>Admin Secret</h2>
  <div class="row">
    <input type="password" id="sk" placeholder="chiave admin" onkeydown="if(event.key==='Enter')go()">
    <button onclick="go()">Accedi</button>
  </div>
  <div class="err" id="er"></div>
</div>
<div id="dash">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
    <span style="font-size:11px;color:#8a7a6a" id="upd"></span>
    <button class="ref" onclick="go()">↻ Aggiorna</button>
    <a id="lnk-ass" href="#" class="ref" style="text-decoration:none;margin-left:10px">⚠ Assistenza →</a>
  </div>
  <div class="grid" id="g"></div>
  <div class="two">
    <div class="card"><h2>Grafo</h2><div id="grf"></div></div>
    <div class="card"><h2>Feedback chat</h2><div id="fb"></div></div>
  </div>
  <div class="card" style="margin-top:12px"><h2>Top fenomeni — 7 giorni</h2><div id="tf"></div></div>
</div>
</div>
<script>
let _s='';
async function go(){
  const el=document.getElementById('sk');
  _s=el.value.trim()||_s;
  if(!_s)return;
  try{
    const r=await fetch('/v1/admin/stats',{headers:{'X-Admin-Secret':_s}});
    if(r.status===403){document.getElementById('er').textContent='Chiave non valida.';return;}
    const d=await r.json();
    if(d.errore){document.getElementById('er').textContent=d.errore;return;}
    document.getElementById('auth').style.display='none';
    document.getElementById('dash').style.display='block';
    render(d);
    const t=new Date().toLocaleTimeString('it-IT',{hour:'2-digit',minute:'2-digit'});
    document.getElementById('upd').textContent='Aggiornato '+t;
    document.getElementById('ts').textContent=t;
  }catch(e){document.getElementById('er').textContent='Errore di rete.';}
}
function e(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function render(d){
  const items=[
    {n:d.utenti_attivi,l:'Utenti attivi',c:''},
    {n:d.utenti_pro,l:'Utenti Pro',c:'g'},
    {n:d.domande_totali,l:'Domande totali',c:''},
    {n:d.domande_24h,l:'Domande 24h',c:'o'},
    {n:d.risposte_ok,l:'Risposte OK',c:'g'},
    {n:d.fallback,l:'Fallback',c:''},
    {n:d.esperimenti,l:'Quaderno',c:''},
  ];
  document.getElementById('g').innerHTML=items.map(i=>
    `<div class="sc ${i.c}"><div class="n">${i.n??'—'}</div><div class="l">${i.l}</div></div>`
  ).join('');
  document.getElementById('grf').innerHTML=`
    <div class="big">${(d.nodi_grafo||0).toLocaleString()}</div><div class="sub">nodi nel grafo</div>
    <div class="big">${(d.archi_grafo||0).toLocaleString()}</div><div class="sub">archi nel grafo</div>`;
  const p=d.feedback_positivi||0,n=d.feedback_negativi||0,t=p+n;
  const pct=t>0?Math.round(p/t*100):0;
  document.getElementById('fb').innerHTML=`
    <div style="display:flex;gap:20px;margin-bottom:12px">
      <div><div class="big" style="color:#2e7d52">${p}</div><div class="sub">👍 positivi</div></div>
      <div><div class="big" style="color:#c4622d">${n}</div><div class="sub">👎 negativi</div></div>
    </div>
    <div class="bar-t" style="height:12px;margin-bottom:6px"><div class="bar-f" style="width:${pct}%;background:#2e7d52"></div></div>
    <div style="font-size:11px;color:#8a7a6a">${pct}% positivi su ${t} totali</div>`;
  const fen=d.top_fenomeni_7d||[];
  if(!fen.length){document.getElementById('tf').innerHTML='<div style="font-size:13px;color:#8a7a6a">Nessun dato ancora.</div>';return;}
  const mx=Math.max(...fen.map(f=>f.count));
  document.getElementById('tf').innerHTML=fen.map(f=>
    `<div class="bar-row"><div class="bar-lbl">${e(String(f.fenomeni||'—'))}</div>
    <div class="bar-t"><div class="bar-f" style="width:${Math.round(f.count/mx*100)}%"></div></div>
    <div class="bar-n">${f.count}</div></div>`
  ).join('');
}
const p=new URLSearchParams(location.search);
if(p.get('s')){document.getElementById('sk').value=p.get('s');go();}
document.getElementById('lnk-ass').href='/admin/assistenza?s='+(p.get('s')||'');
</script></body></html>"""

@bp.route("/v1/admin/stats-debug")
def admin_stats_debug():
    """Diagnostica: esegue la logica di stats mostrando il traceback vero.
    Serve a trovare la causa del 500. Da rimuovere dopo la diagnosi."""
    secret = request.headers.get("X-Admin-Secret","") or request.args.get("s","")
    if (not os.environ.get("ADMIN_SECRET")) or not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET"))):
        return jsonify({"errore":"non autorizzato"}), 403
    import traceback as _tb
    tappe = []
    try:
        tappe.append("inizio")
        conn = _get_conn()
        tappe.append("conn ok")
        conn.autocommit = True
        cur = conn.cursor()
        tappe.append("cursor ok")
        cur.execute("SELECT model, COUNT(*), COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days' GROUP BY model")
        rows = cur.fetchall()
        test = {"costo_per_modello": [{"model":r[0],"n":r[1],"costo":float(r[2])} for r in rows]}
        # TEST 1: il provider Flask jsonify gestisce i Decimal?
        from decimal import Decimal as _Dec
        test["decimal_grezzo"] = _Dec("1.23")
        try:
            _resp = jsonify(test)
            tappe.append("jsonify FLASK con Decimal grezzo: OK (provider attivo)")
        except Exception as je:
            tappe.append(f"jsonify FLASK FALLISCE: {je} (provider NON attivo)")
        cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "tappe": tappe})
    except Exception as e:
        return jsonify({"ok": False, "tappe": tappe, "errore": str(e),
                        "traceback": _tb.format_exc()[-1200:]}), 200


@bp.route("/v1/admin/stats-debug2")
def admin_stats_debug2():
    """Esegue admin_stats VERO con l'header giusto e SERIALIZZA la risposta."""
    secret = request.headers.get("X-Admin-Secret","") or request.args.get("s","")
    if (not os.environ.get("ADMIN_SECRET")) or not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET"))):
        return jsonify({"errore":"non autorizzato"}), 403
    import traceback as _tb
    # riesegui la logica di stats DIRETTAMENTE qui (senza ri-chiamare la route,
    # così l'auth non serve e vediamo il vero punto di rottura)
    try:
        conn = _get_conn()
        conn.autocommit = True
        cur = conn.cursor()
        stats = {}
        def q(sql, default=0):
            try:
                cur.execute(sql); return cur.fetchone()[0]
            except Exception:
                try: conn.rollback()
                except Exception: pass
                return default
        stats["utenti_attivi"] = q("SELECT COUNT(*) FROM utenti WHERE attivo=TRUE")
        stats["domande_totali"] = q("SELECT COUNT(*) FROM log_domande")
        stats["feedback_positivi"] = q("SELECT COUNT(*) FROM log_domande WHERE feedback=1")
        stats["nodi_grafo"] = q("SELECT COUNT(*) FROM nodes")
        stats["costo_oggi_usd"] = q("SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts::date = CURRENT_DATE")
        # tutte le altre query di admin_stats, con marcatore per trovare quella che rompe
        marcatori = []
        def qm(nome, sql):
            marcatori.append(nome)
            return q(sql)
        stats["utenti_pro"] = qm("utenti_pro", "SELECT COUNT(*) FROM utenti WHERE piano='pro'")
        stats["risposte_ok"] = qm("risposte_ok", "SELECT COUNT(*) FROM log_domande WHERE esito='ok'")
        stats["fallback"] = qm("fallback", "SELECT COUNT(*) FROM log_domande WHERE esito='nessun_nodo'")
        stats["domande_24h"] = qm("domande_24h", "SELECT COUNT(*) FROM log_domande WHERE ts > NOW() - INTERVAL '24 hours'")
        stats["feedback_negativi"] = qm("feedback_negativi", "SELECT COUNT(*) FROM log_domande WHERE feedback=-1")
        stats["archi_grafo"] = qm("archi_grafo", "SELECT COUNT(*) FROM edges")
        stats["esperimenti"] = qm("esperimenti", "SELECT COUNT(*) FROM esperimenti")
        stats["costo_7g_usd"] = qm("costo_7g", "SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days'")
        stats["costo_30g_usd"] = qm("costo_30g", "SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '30 days'")
        stats["chiamate_ai_oggi"] = qm("chiamate_ai", "SELECT COUNT(*) FROM ai_usage_log WHERE ts::date = CURRENT_DATE")
        stats["errori_ai_24h"] = qm("errori_ai", "SELECT COUNT(*) FROM ai_usage_log WHERE error IS NOT NULL AND ts > NOW() - INTERVAL '24 hours'")
        # top fenomeni (query con fetchall)
        try:
            cur.execute("SELECT fenomeni_trovati, COUNT(*) FROM log_domande WHERE fenomeni_trovati IS NOT NULL AND ts > NOW() - INTERVAL '7 days' GROUP BY fenomeni_trovati ORDER BY COUNT(*) DESC LIMIT 5")
            stats["top_fenomeni_7d"] = [{"fenomeni":r[0],"count":r[1]} for r in cur.fetchall()]
            marcatori.append("top_fenomeni OK")
        except Exception as te:
            marcatori.append(f"top_fenomeni ROTTO: {te}")
            try: conn.rollback()
            except Exception: pass
        # costo per modello (la lista con Decimal)
        cur.execute("SELECT model, COUNT(*), COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days' GROUP BY model")
        stats["costo_per_modello_7g"] = [{"model":r[0],"chiamate":r[1],"costo_usd":r[2]} for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
        # PROVA A SERIALIZZARE con jsonify (dove esplode il Decimal se il provider non copre)
        try:
            resp = jsonify(stats)
            body = resp.get_data(as_text=True)
            return jsonify({"stato": "SERIALIZZA OK", "tipi": {k: type(v).__name__ for k,v in stats.items()},
                            "body_len": len(body), "marcatori": marcatori})
        except Exception as se:
            return jsonify({"stato": "jsonify ESPLODE", "errore": str(se),
                            "tipi": {k: type(v).__name__ for k,v in stats.items()},
                            "traceback": _tb.format_exc()[-1000:]}), 200
    except Exception as e:
        return jsonify({"stato": "eccezione", "errore": str(e),
                        "traceback": _tb.format_exc()[-1500:]}), 200


@bp.route("/v1/admin/stats")
def admin_stats():
    """GT10 — Admin panel: statistiche base del prodotto."""
    secret = request.headers.get("X-Admin-Secret","")
    if (not os.environ.get("ADMIN_SECRET")) or not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET"))):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        conn.autocommit = True  # ogni query è isolata, nessuna transazione che blocca
        cur = conn.cursor()
        stats = {}

        def q(sql, default=0):
            try:
                cur.execute(sql)
                return cur.fetchone()[0]
            except Exception:
                # una query fallita avvelena la transazione Postgres:
                # rollback così le query successive funzionano
                try: conn.rollback()
                except Exception: pass
                return default

        # utenti
        stats["utenti_attivi"] = q("SELECT COUNT(*) FROM utenti WHERE attivo=TRUE")
        stats["utenti_pro"]    = q("SELECT COUNT(*) FROM utenti WHERE piano='pro'")
        # domande
        stats["domande_totali"] = q("SELECT COUNT(*) FROM log_domande")
        stats["risposte_ok"]    = q("SELECT COUNT(*) FROM log_domande WHERE esito='ok'")
        stats["fallback"]       = q("SELECT COUNT(*) FROM log_domande WHERE esito='nessun_nodo'")
        stats["domande_24h"]    = q("SELECT COUNT(*) FROM log_domande WHERE ts > NOW() - INTERVAL '24 hours'")
        # feedback
        stats["feedback_positivi"] = q("SELECT COUNT(*) FROM log_domande WHERE feedback=1")
        stats["feedback_negativi"] = q("SELECT COUNT(*) FROM log_domande WHERE feedback=-1")
        # grafo
        stats["nodi_grafo"]  = q("SELECT COUNT(*) FROM nodes")
        stats["archi_grafo"] = q("SELECT COUNT(*) FROM edges")
        # esperimenti
        stats["esperimenti"] = q("SELECT COUNT(*) FROM esperimenti")
        # top fenomeni 7 giorni
        try:
            cur.execute("""
                SELECT fenomeni_trovati, COUNT(*) as n
                FROM log_domande
                WHERE fenomeni_trovati IS NOT NULL AND ts > NOW() - INTERVAL '7 days'
                GROUP BY fenomeni_trovati ORDER BY n DESC LIMIT 5
            """)
            stats["top_fenomeni_7d"] = [{"fenomeni":r[0],"count":r[1]} for r in cur.fetchall()]
        except Exception:
            stats["top_fenomeni_7d"] = []

        # ═══ COSTI AI (dal ai_usage_log) ═══
        # Costi aggregati per capire in tempo reale se l'uso AI erode il margine.
        # Tutto il blocco è protetto: se ai_usage_log ha problemi, il pannello
        # continua a funzionare (mostra il resto) invece di rompersi.
        try:
            stats["costo_oggi_usd"]      = float(q("SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts::date = CURRENT_DATE") or 0)
            stats["costo_7g_usd"]        = float(q("SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days'") or 0)
            stats["costo_30g_usd"]       = float(q("SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '30 days'") or 0)
            stats["chiamate_ai_oggi"]    = q("SELECT COUNT(*) FROM ai_usage_log WHERE ts::date = CURRENT_DATE")
            stats["errori_ai_24h"]       = q("SELECT COUNT(*) FROM ai_usage_log WHERE error IS NOT NULL AND ts > NOW() - INTERVAL '24 hours'")
        except Exception:
            try: conn.rollback()
            except Exception: pass
            stats["costo_oggi_usd"] = stats.get("costo_oggi_usd", 0)
        # costo per modello (7 giorni)
        try:
            cur.execute("""
                SELECT model, COUNT(*) as chiamate, COALESCE(SUM(cost_usd),0) as costo
                FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days'
                GROUP BY model ORDER BY costo DESC
            """)
            stats["costo_per_modello_7g"] = [{"model":r[0],"chiamate":r[1],"costo_usd":float(r[2])} for r in cur.fetchall()]
        except Exception:
            stats["costo_per_modello_7g"] = []
        # costo per route/feature (7 giorni) — quale feature costa di più
        try:
            cur.execute("""
                SELECT route, COUNT(*) as chiamate, COALESCE(SUM(cost_usd),0) as costo
                FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days'
                GROUP BY route ORDER BY costo DESC
            """)
            stats["costo_per_route_7g"] = [{"route":r[0],"chiamate":r[1],"costo_usd":float(r[2])} for r in cur.fetchall()]
        except Exception:
            stats["costo_per_route_7g"] = []

        # ═══ ALLARME SOGLIA COSTI (anti-erosione margine) ═══
        # Soglie configurabili via env (default sensati per fase early). Non blocca: segnala.
        try:
            soglia_giorno = float(os.environ.get("ALERT_COSTO_GIORNO_USD", "5.0"))
            soglia_mese   = float(os.environ.get("ALERT_COSTO_MESE_USD", "80.0"))
            c_oggi = stats.get("costo_oggi_usd", 0) or 0
            c_mese = stats.get("costo_30g_usd", 0) or 0
            allarmi = []
            if c_oggi > soglia_giorno:
                allarmi.append(f"Costo oggi ${c_oggi:.2f} supera la soglia giornaliera ${soglia_giorno:.2f}")
            if c_mese > soglia_mese:
                allarmi.append(f"Costo 30g ${c_mese:.2f} supera la soglia mensile ${soglia_mese:.2f}")
            stats["allarme_costi"] = {
                "attivo": len(allarmi) > 0,
                "messaggi": allarmi,
                "soglia_giorno_usd": soglia_giorno,
                "soglia_mese_usd": soglia_mese
            }
        except Exception:
            stats["allarme_costi"] = {"attivo": False, "messaggi": []}

        cur.close(); _release_conn(conn)
        # sanitizza: i Decimal di Postgres non sono serializzabili da jsonify
        from decimal import Decimal as _Dec
        def _clean(o):
            if isinstance(o, _Dec): return float(o)
            if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
            if isinstance(o, list): return [_clean(x) for x in o]
            return o
        return jsonify(_clean(stats))
    except Exception as e:
        import traceback as _tb
        print("[STATS ERROR]", _tb.format_exc(), flush=True)
        # TEMPORANEO: espongo il traceback vero per diagnosi (bypassa handler globale)
        return jsonify({"errore_diag": str(e), "traceback": _tb.format_exc()[-1500:]}), 200
        return jsonify({"errore": str(e), "dettaglio": str(e)}), 500

@bp.route("/admin/assistenza")
def admin_assistenza():
    """Pannello supporto admin: richieste esplicite (30g) + chat recenti (7g)."""
    if not _admin_autenticato():
        return "<p>Non autorizzato.</p>", 403
    if not DATABASE_URL:
        return "<p>DB non disponibile.</p>", 503
    s = request.args.get("s","")
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT l.user_id, l.domanda, l.ts,
                   COALESCE(u.email,'—') as email,
                   COALESCE(u.piano,'free') as piano
            FROM log_domande l
            LEFT JOIN utenti u ON u.id::text = l.user_id
            WHERE l.tipo='supporto' AND l.ts > NOW() - INTERVAL '30 days'
            ORDER BY l.ts DESC LIMIT 30
        """)
        supporti = cur.fetchall()
        cur.execute("""
            SELECT l.user_id, l.domanda, l.ts, l.esito,
                   COALESCE(u.email,'—') as email
            FROM log_domande l
            LEFT JOIN utenti u ON u.id::text = l.user_id
            WHERE l.tipo IN ('risposta','fallback')
            AND l.ts > NOW() - INTERVAL '7 days'
            ORDER BY l.ts DESC LIMIT 50
        """)
        chat = cur.fetchall()
        cur.close(); _release_conn(conn)
    except Exception as e:
        return f"<p>Errore: {e}</p>", 503

    html_sup = ""
    for r in supporti:
        uid = r[0] or ""; em = r[3]; pi = r[4]; ts = str(r[2])[:16]; dom = (r[1] or "")[:120]
        link = f"/admin/assistenza/{uid}?s={s}" if uid else "#"
        html_sup += (f'<div class="sup-row"><div class="sup-top"><span class="badge">⚠ Supporto</span>'
                     f'<span class="ts">{ts}</span><span class="em">{em} · {pi}</span></div>'
                     f'<div class="dom">{dom}</div>'
                     f'<a href="{link}" class="btn-a">Rispondi →</a></div>')
    if not html_sup:
        html_sup = '<p class="niente">Nessuna richiesta di supporto negli ultimi 30 giorni.</p>'

    html_chat = ""
    for r in chat:
        uid = r[0] or ""; ts = str(r[2])[:16]; dom = (r[1] or "")[:100]; em = r[4]; esito = r[3] or ""
        link = f"/admin/assistenza/{uid}?s={s}" if uid else "#"
        cls = " fall" if esito=="nessun_nodo" else ""
        html_chat += (f'<div class="chat-row{cls}"><span class="ts">{ts}</span>'
                      f'<span class="em">{em}</span>'
                      f'<div class="dom">{dom}</div>'
                      f'<a href="{link}" class="btn-b">Apri →</a></div>')
    if not html_chat:
        html_chat = '<p class="niente">Nessuna chat negli ultimi 7 giorni.</p>'

    return f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matter · Assistenza</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5ede3;color:#2a1f14}}
.top{{background:#3d2b1f;color:#f0e0cc;padding:14px 24px;display:flex;align-items:center;gap:16px}}
.top h1{{font-size:16px;font-weight:700}}.top a{{color:#c4a882;font-size:12px;text-decoration:none}}
.wrap{{max-width:900px;margin:0 auto;padding:20px 16px}}
h2{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#8a7a6a;margin:20px 0 10px}}
.sup-row{{background:#fff;border:1.5px solid #c4622d;border-radius:10px;padding:14px;margin-bottom:10px}}
.chat-row{{background:#fff;border:0.5px solid #e0d4c8;border-radius:10px;padding:12px;margin-bottom:8px}}
.chat-row.fall{{border-color:#c4a040}}
.sup-top{{margin-bottom:6px}}
.badge{{background:#c4622d;color:#fff;font-size:10px;padding:2px 8px;border-radius:20px;margin-right:6px}}
.ts{{font-size:11px;color:#8a7a6a;margin-right:8px}}.em{{font-size:12px;font-weight:600}}
.dom{{font-size:13px;color:#5a4a3a;margin:6px 0 8px}}
.btn-a{{background:#3d2b1f;color:#f0e0cc;border:none;border-radius:7px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;text-decoration:none}}
.btn-b{{background:none;border:1px solid #e0d4c8;color:#8a7a6a;border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer;text-decoration:none}}
.niente{{font-size:13px;color:#8a7a6a;padding:10px 0}}</style></head><body>
<div class="top"><h1>Matter · Assistenza</h1><a href="/admin?s={s}">← Admin</a></div>
<div class="wrap">
<h2>⚠ Richieste supporto — ultimi 30 giorni</h2>{html_sup}
<h2>Chat recenti — ultimi 7 giorni</h2>{html_chat}
</div></body></html>""", 200, {"Content-Type": "text/html; charset=utf-8"}

@bp.route("/admin/assistenza/<user_id>/invia", methods=["POST"])
def admin_invia_risposta(user_id):
    """Invia risposta supporto via Resend all'utente, dalla scheda admin."""
    if not _admin_autenticato():
        return "<p>Non autorizzato.</p>", 403
    s = request.args.get("s","")
    email_dest = request.form.get("email","").strip()
    testo = request.form.get("testo_risposta","").strip()
    if not email_dest or not testo:
        return f"<p>Dati mancanti.</p><a href='/admin/assistenza/{user_id}?s={s}'>← Torna</a>"
    ok = _invia_email_resend(
        to=email_dest,
        subject="Risposta dal supporto Matter",
        body_html=(f"<p>Ciao,</p><p>{testo.replace(chr(10),'<br>')}</p>"
                   f"<p>— Il team Matter</p>"),
        body_text=testo
    )
    esito = "✓ Email inviata." if ok else "✗ Invio fallito — controlla RESEND_API_KEY."
    return (f"<p style='font-family:system-ui;padding:20px'>{esito}<br>"
            f"<a href='/admin/assistenza/{user_id}?s={s}'>← Torna alla scheda</a></p>")

@bp.route("/admin/assistenza/<user_id>")
def admin_assistenza_utente(user_id):
    """Scheda utente: contesto account + ultime interazioni + risposta Sonnet + mailto."""
    if not _admin_autenticato():
        return "<p>Non autorizzato.</p>", 403
    if not DATABASE_URL:
        return "<p>DB non disponibile.</p>", 503
    s = request.args.get("s","")
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT email, piano FROM utenti WHERE id=%s", (user_id,))
        u = cur.fetchone(); email = u[0] if u else "—"; piano = u[1] if u else "free"
        cur.execute("SELECT tipo, domanda, ts, esito FROM log_domande WHERE user_id=%s ORDER BY ts DESC LIMIT 20", (user_id,))
        domande = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM log_domande WHERE user_id=%s AND esito='ok'", (user_id,))
        n_ok = cur.fetchone()[0]
        cur.execute("SELECT fenomeni_trovati FROM log_domande WHERE user_id=%s AND fenomeni_trovati IS NOT NULL ORDER BY ts DESC LIMIT 1", (user_id,))
        r = cur.fetchone(); ultima_disc = r[0] if r else "—"
        cur.close(); _release_conn(conn)
    except Exception as e:
        return f"<p>Errore: {e}</p>", 503

    # Genera risposta Sonnet solo se richiesto (?genera=1)
    risposta_ai = ""
    if request.args.get("genera") == "1" and domande:
        ultime = [d[1] for d in domande if d[0]!="supporto"][:3]
        sup_list = [d[1] for d in domande if d[0]=="supporto"][:2]
        ctx_str = f"Utente: {email} | piano: {piano} | risposte ok: {n_ok} | ultima disciplina: {ultima_disc}"
        prompt_admin = (
            f"Contesto: {ctx_str}\n"
            f"Ultime domande: {'; '.join(ultime)}\n"
            f"Richieste supporto: {'; '.join(sup_list) if sup_list else 'nessuna'}\n\n"
            "Scrivi una risposta di supporto breve (max 4 frasi), diretta e calda."
        )
        try:
            import anthropic as _ac
            client = _ac.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY",""))
            msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=300,
                messages=[{"role":"user","content":prompt_admin}])
            risposta_ai = msg.content[0].text if msg.content else ""
        except Exception:
            risposta_ai = ""

    righe = ""
    for d in domande:
        tp = d[0] or "chat"; dom = (d[1] or "")[:200]; ts = str(d[2])[:16]; es = d[3] or ""
        cls = "sup" if tp=="supporto" else ("err" if es=="nessun_nodo" else "ok")
        righe += (f'<div class="msg {cls}"><span class="ts">{ts}</span>'
                  f'<span class="tipo">{tp}</span><div class="testo">{dom}</div></div>')

    ai_html = ""
    if risposta_ai:
        ai_html = (f'<div class="ai-box"><div class="ai-lbl">Risposta Sonnet</div>'
                   f'<div class="ai-testo">{risposta_ai}</div>'
                   f'<form method="POST" action="/admin/assistenza/{user_id}/invia?s={s}" style="margin-top:12px">'
                   f'<input type="hidden" name="email" value="{email}">'
                   f'<textarea name="testo_risposta" style="width:100%;min-height:80px;border:1px solid #b2d8cc;'
                   f'border-radius:8px;padding:10px;font-size:14px;font-family:system-ui;margin-bottom:10px">'
                   f'{risposta_ai}</textarea>'
                   f'<button type="submit" class="btn-mail">✉ Invia via email</button>'
                   f'</form></div>')

    return f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matter · {email}</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,sans-serif;background:#f5ede3;color:#2a1f14}}
.top{{background:#3d2b1f;color:#f0e0cc;padding:14px 24px;display:flex;align-items:center;gap:16px}}
.top h1{{font-size:16px;font-weight:700}}.top a{{color:#c4a882;font-size:12px;text-decoration:none}}
.wrap{{max-width:800px;margin:0 auto;padding:20px 16px}}
.card{{background:#fff;border:0.5px solid #e0d4c8;border-radius:12px;padding:18px;margin-bottom:14px}}
h2{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#8a7a6a;margin-bottom:10px}}
.meta{{font-size:13px;line-height:1.8}}
.btn-gen{{background:#3d2b1f;color:#f0e0cc;border:none;border-radius:8px;padding:9px 18px;
  font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-block;margin-top:10px}}
.msg{{border-radius:8px;padding:9px 12px;margin-bottom:7px;font-size:13px}}
.msg.sup{{background:#fdf0ec;border-left:3px solid #c4622d}}
.msg.err{{background:#fdf8ec;border-left:3px solid #c4a040}}
.msg.ok{{background:#f5f5f5;border-left:3px solid #e0d4c8}}
.ts{{font-size:10px;color:#8a7a6a;margin-right:6px}}
.tipo{{font-size:10px;background:#e0d4c8;border-radius:10px;padding:1px 6px;margin-right:6px}}
.testo{{margin-top:4px}}
.ai-box{{background:#f0f7f4;border:1px solid #b2d8cc;border-radius:10px;padding:16px;margin-top:12px}}
.ai-lbl{{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#2C6E63;margin-bottom:8px}}
.ai-testo{{font-size:14px;line-height:1.6;color:#1a2f28;margin-bottom:12px}}
.btn-mail{{background:#2C6E63;color:#fff;border:none;border-radius:8px;padding:9px 18px;
  font-size:13px;font-weight:600;cursor:pointer;text-decoration:none}}</style></head><body>
<div class="top"><h1>Matter · Utente</h1>
<a href="/admin/assistenza?s={s}">← Assistenza</a>
<a href="/admin?s={s}">← Admin</a></div>
<div class="wrap">
<div class="card"><h2>Account</h2>
<div class="meta">Email: <strong>{email}</strong> · Piano: <strong>{piano}</strong><br>
Risposte ok: <strong>{n_ok}</strong> · Ultima disciplina: <strong>{ultima_disc}</strong></div>
<a href="/admin/assistenza/{user_id}?s={s}&genera=1" class="btn-gen">Genera risposta Sonnet</a>
{ai_html}</div>
<div class="card"><h2>Ultime 20 interazioni</h2>{righe}</div>
</div></body></html>""", 200, {"Content-Type": "text/html; charset=utf-8"}


@bp.route("/admin/verifica-errori", methods=["GET"])
def admin_verifica_errori():
    """Verifica quali errori (fallisce_come) sono collegati ai fenomeni.
    Usa carica_grafo() — funziona anche per fenomeni Pro senza login."""
    secret = request.args.get("s","") or request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    db = carica_grafo()
    fenomeni = ["fen-diluizione","fen-fat-washing","fen-concentrazione",
                "fen-carbonatazione","fen-estrazione","fen-crioscopia",
                "fen-denaturazione","fen-punto-fumo","fen-osmosi","fen-sineresi",
                "fen-solubilita","fen-viscosita","fen-ossidazione",
                "fen-temperaggio-cioccolato","fen-ganache","fen-souffle",
                "fen-meringa","fen-montatura-panna","fen-retrogradazione",
                "fen-maglia-glutinica","fen-lievitazione","fen-crosta",
                "fen-enzimi-farina","fen-sale-impasto",
                "fen-mash-enzimi","fen-isomerizzazione-luppolo","fen-acidita-volatile",
                "fen-pac-gelateria","fen-cristallizzazione-ghiaccio","fen-overrun",
                "fen-bilanciamento-gelato"]
    out = {}
    tot = 0
    tot_tec = 0
    for fid in fenomeni:
        try:
            rows = db.execute("""SELECT n.name FROM edges e JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='fallisce_come'""", (fid,)).fetchall()
            names = [r["name"] if hasattr(r,"keys") else r[0] for r in rows]
            trows = db.execute("""SELECT n.name FROM edges e JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='realizzato_da'""", (fid,)).fetchall()
            tnames = [r["name"] if hasattr(r,"keys") else r[0] for r in trows]
            out[fid] = {"errori": names, "tecniche": tnames}
            tot += len(names)
            tot_tec += len(tnames)
        except Exception as e:
            out[fid] = f"ERR: {str(e)[:60]}"
    # conteggio totale errori nel grafo
    try:
        r = db.execute("SELECT COUNT(*) FROM nodes WHERE type='Errore'").fetchall()
        n_err = (r[0]["count"] if hasattr(r[0],"keys") else r[0][0]) if r else 0
    except Exception:
        n_err = "?"
    return jsonify({"fenomeni": out, "errori_collegati_totali": tot,
                    "tecniche_collegate_totali": tot_tec,
                    "nodi_errore_nel_grafo": n_err})


@bp.route("/admin/seed-errori", methods=["POST"])
def admin_seed_errori():
    """Applica in modo incrementale i seed-errori-*.sql e seed-tecniche-*.sql.
    Usa carica_grafo().execute() (l'astrazione _PgCompatPool che funziona in
    produzione), eseguendo ogni statement separatamente. Idempotente: i duplicati
    vengono saltati. NON ricostruisce il grafo."""
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    import glob as _glob
    db = carica_grafo()
    seed_files = sorted(_glob.glob("grafo/seed-errori-*.sql")) + \
                 sorted(_glob.glob("grafo/seed-tecniche-*.sql")) + \
                 sorted(_glob.glob("grafo/seed-ingredienti-*.sql"))
    ok = []; errori = []; stmt_ok = 0; stmt_skip = 0
    for f in seed_files:
        try:
            sql = open(f, encoding="utf-8").read()
            # rimuove i commenti -- e spezza in statement singoli
            clean = "\n".join(l for l in sql.split("\n") if not l.strip().startswith("--"))
            for stmt in clean.split(";"):
                stmt = stmt.strip()
                if not stmt:
                    continue
                # psycopg2 interpreta % come placeholder: raddoppio i % letterali
                # (i seed non usano parametri, sono INSERT con valori inline)
                stmt_safe = stmt.replace("%", "%%")
                try:
                    db.execute(stmt_safe)
                    stmt_ok += 1
                except Exception as e:
                    em = str(e).lower()
                    if "duplicate" in em or "already exists" in em or "unique" in em:
                        stmt_skip += 1
                    else:
                        errori.append(f"{f}: {str(e)[:120]}")
            ok.append(f)
        except Exception as e:
            errori.append(f"{f}: {str(e)[:120]}")
    return jsonify({"file_processati": ok, "statement_ok": stmt_ok,
                    "statement_saltati_duplicati": stmt_skip,
                    "errori": errori, "totale_file": len(seed_files)})


@bp.route("/admin/add-fenomeni", methods=["POST"])
def admin_add_fenomeni():
    """Aggiunge o aggiorna nodi fenomeno nel grafo.
    Body JSON: lista di {id, nome, it, en, es, target}.
    Fa UPSERT — safe da chiamare più volte."""
    import os, json as _j
    from db import _get_conn, _release_conn
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    body = request.json or {}
    fenomeni = body.get("fenomeni", [])
    if not fenomeni:
        return jsonify({"errore":"lista fenomeni vuota"}), 400
    conn = _get_conn(); ok = 0; errori = []
    try:
        cur = conn.cursor()
        for f in fenomeni:
            fid = f.get("id","").strip()
            nome = f.get("nome","").strip()
            if not fid or not nome:
                errori.append(f"id o nome mancante: {f}"); continue
            data = {
                "scheda": f.get("it",""),
                "scheda_en": f.get("en",""),
                "scheda_es": f.get("es",""),
                "numero_bersaglio": f.get("target",""),
                "target": f.get("target",""),  # compatibilità legacy
                "disciplina": f.get("disciplina","trasversale"),
            }
            cur.execute("""
                INSERT INTO nodes (id, type, name, domain, data)
                VALUES (%s, 'Fenomeno', %s, 'matter', %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                  SET name = EXCLUDED.name,
                      data = EXCLUDED.data
            """, (fid, nome, _j.dumps(data, ensure_ascii=False)))
            ok += 1
        conn.commit(); cur.close()
    except Exception as e:
        errori.append(str(e))
    finally:
        _release_conn(conn)
    return jsonify({"inseriti": ok, "errori": errori})


@bp.route("/admin/setup-ricette", methods=["POST"])
def admin_setup_ricette():
    """Crea la tabella ricette se non esiste. Idempotente."""
    import os
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    from db import _get_conn, _release_conn
    conn=_get_conn(); ok=False
    try:
        cur=conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ricette (
                id          TEXT PRIMARY KEY,
                nome        TEXT NOT NULL,
                disciplina  TEXT NOT NULL,
                descrizione TEXT,
                ingredienti JSONB,
                fenomeni    JSONB,
                numeri      JSONB,
                punto_critico TEXT,
                scheda_en   TEXT,
                scheda_es   TEXT,
                ts          TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit(); cur.close(); ok=True
    except Exception as e:
        return jsonify({"errore":str(e)}),500
    finally:
        _release_conn(conn)
    return jsonify({"ok":ok,"messaggio":"tabella ricette pronta"})


@bp.route("/admin/add-ricette", methods=["POST"])
def admin_add_ricette():
    """UPSERT ricette scientifiche nel DB.
    Body JSON: {ricette: [{id, nome, disciplina, descrizione, ingredienti, fenomeni,
                tecniche, numeri, punto_critico, abbinamenti, vino_birra, scheda_en, scheda_es}]}"""
    import os, json as _j
    from db import _get_conn, _release_conn
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    body = request.json or {}
    ricette = body.get("ricette",[])
    if not ricette:
        return jsonify({"errore":"lista vuota"}),400
    conn=_get_conn(); ok=0; errori=[]
    try:
        cur=conn.cursor()
        # migrazione idempotente: aggiungi colonne nuove se non esistono
        for col in ["tecniche JSONB", "abbinamenti JSONB", "vino_birra JSONB"]:
            cname = col.split()[0]
            try:
                cur.execute(f"ALTER TABLE ricette ADD COLUMN IF NOT EXISTS {col}")
            except Exception as me:
                errori.append(f"migrazione {cname}: {me}")
        conn.commit()
        for r in ricette:
            rid=r.get("id","").strip()
            if not rid: errori.append("id mancante"); continue
            cur.execute("""
                INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,abbinamenti,vino_birra,scheda_en,scheda_es)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s,%s)
                ON CONFLICT (id) DO UPDATE SET
                  nome=EXCLUDED.nome, disciplina=EXCLUDED.disciplina,
                  descrizione=EXCLUDED.descrizione, ingredienti=EXCLUDED.ingredienti,
                  fenomeni=EXCLUDED.fenomeni, tecniche=EXCLUDED.tecniche,
                  numeri=EXCLUDED.numeri, punto_critico=EXCLUDED.punto_critico,
                  abbinamenti=EXCLUDED.abbinamenti, vino_birra=EXCLUDED.vino_birra,
                  scheda_en=COALESCE(NULLIF(EXCLUDED.scheda_en,''), ricette.scheda_en),
                  scheda_es=COALESCE(NULLIF(EXCLUDED.scheda_es,''), ricette.scheda_es),
                  ts=NOW()
            """,(rid, r.get("nome",""), r.get("disciplina",""),
                 r.get("descrizione",""),
                 _j.dumps(r.get("ingredienti",[]),ensure_ascii=False),
                 _j.dumps(r.get("fenomeni",[]),ensure_ascii=False),
                 _j.dumps(r.get("tecniche",[]),ensure_ascii=False),
                 _j.dumps(r.get("numeri",{}),ensure_ascii=False),
                 r.get("punto_critico",""),
                 _j.dumps(r.get("abbinamenti",{}),ensure_ascii=False),
                 _j.dumps(r.get("vino_birra",{}),ensure_ascii=False),
                 r.get("scheda_en",""), r.get("scheda_es","")))
            ok+=1
        conn.commit(); cur.close()
    except Exception as e:
        errori.append(str(e))
    finally:
        _release_conn(conn)
    return jsonify({"inserite":ok,"errori":errori})
# /v1/ricette è definita in routes/api.py


@bp.route("/admin/test-ai")
def admin_test_ai():
    """Test diretto dell'AI gateway."""
    import os, traceback
    secret = request.args.get("s","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    import ai_gateway as GW

    results = {}

    # test 1: route_chat semplice
    try:
        out = GW.route_chat("Rispondi con una parola: OK")
        results["route_chat"] = {"ok": bool(out), "risposta": out}
    except Exception as e:
        results["route_chat"] = {"ok": False, "errore": str(e)}

    # test 2: anthropic senza tools
    try:
        data, _ = GW._anthropic_call("claude-sonnet-4-5",
            [{"role":"user","content":"Di solo: OK"}],
            max_tokens=10, temperature=0, tools=None)
        testo = " ".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
        results["anthropic_no_tools"] = {
            "ok": bool(testo), "testo": testo,
            "stop_reason": data.get("stop_reason"),
            "types": [b.get("type") for b in data.get("content",[])]
        }
    except Exception as e:
        results["anthropic_no_tools"] = {"ok": False, "errore": str(e), "tb": traceback.format_exc()[-300:]}

    # test 3: anthropic con tools (simulazione chat)
    try:
        from app import _TOOLS as TOOLS
        data2, _ = GW._anthropic_call("claude-sonnet-4-5",
            [{"role":"user","content":"sour acido\n\nRISPOSTA:"}],
            max_tokens=50, temperature=0, tools=TOOLS)
        results["anthropic_with_tools"] = {
            "stop_reason": data2.get("stop_reason"),
            "types": [b.get("type") for b in data2.get("content",[])]
        }
    except Exception as e:
        results["anthropic_with_tools"] = {"errore": str(e)}

    return jsonify(results)


@bp.route("/admin/add-tecniche", methods=["POST"])
def admin_add_tecniche():
    """Aggiunge o aggiorna nodi Tecnica nel grafo + edge 'sfrutta' verso i fenomeni.
    Body JSON: {tecniche: [{id, nome, famiglia, disciplina, it, en, es,
                            numeri, esecuzione, errori, fenomeni_sfruttati: [id...]}]}
    UPSERT — safe da chiamare più volte."""
    import os, json as _j
    from db import _get_conn, _release_conn
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    body = request.json or {}
    tecniche = body.get("tecniche", [])
    if not tecniche:
        return jsonify({"errore":"lista tecniche vuota"}), 400
    conn = _get_conn(); ok = 0; edge_ok = 0; errori = []
    try:
        cur = conn.cursor()
        for t in tecniche:
            tid = t.get("id","").strip()
            nome = t.get("nome","").strip()
            if not tid or not nome:
                errori.append(f"id o nome mancante: {t}"); continue
            data = {
                "famiglia": t.get("famiglia",""),
                "disciplina": t.get("disciplina","trasversale"),
                "scheda": t.get("it",""),
                "scheda_en": t.get("en",""),
                "scheda_es": t.get("es",""),
                "numeri": t.get("numeri",""),
                "esecuzione": t.get("esecuzione",""),
                "errori_comuni": t.get("errori",""),
                "fenomeni_sfruttati": t.get("fenomeni_sfruttati",[]),
            }
            cur.execute("""
                INSERT INTO nodes (id, type, name, domain, data)
                VALUES (%s, 'Tecnica', %s, 'matter', %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                  SET name = EXCLUDED.name, data = EXCLUDED.data
            """, (tid, nome, _j.dumps(data, ensure_ascii=False)))
            ok += 1
            # crea edge 'sfrutta' verso ogni fenomeno collegato
            for fen_id in t.get("fenomeni_sfruttati", []):
                try:
                    cur.execute("""
                        INSERT INTO edges (from_id, to_id, relation)
                        VALUES (%s, %s, 'sfrutta')
                        ON CONFLICT DO NOTHING
                    """, (tid, fen_id))
                    edge_ok += 1
                except Exception as ee:
                    errori.append(f"edge {tid}->{fen_id}: {ee}")
        conn.commit(); cur.close()
    except Exception as e:
        errori.append(str(e))
    finally:
        _release_conn(conn)
    return jsonify({"inserite": ok, "edge_create": edge_ok, "errori": errori})


@bp.route("/admin/ritraduce-ricette", methods=["POST"])
def admin_ritraduce_ricette():
    """Rigenera scheda_en/es per le ricette date, traducendo la descrizione IT con Haiku.
    Body JSON: {ids: [id1, id2...]}. Solo per riparare traduzioni perse."""
    import os, json as _j
    from db import _get_conn, _release_conn
    from ai import _haiku_raw
    secret = request.headers.get("X-Admin-Secret","")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    body = request.json or {}
    ids = body.get("ids", [])
    if not ids:
        return jsonify({"errore":"lista ids vuota"}), 400
    conn = _get_conn(); ok = 0; errori = []
    try:
        cur = conn.cursor()
        for rid in ids:
            cur.execute("SELECT descrizione FROM ricette WHERE id=%s", (rid,))
            row = cur.fetchone()
            if not row:
                errori.append(f"{rid} non trovato"); continue
            desc_it = row[0] if not hasattr(row,"keys") else row["descrizione"]
            if not desc_it:
                errori.append(f"{rid} senza descrizione"); continue
            try:
                en = _haiku_raw(f"Traduci in inglese questo testo culinario, mantenendo il tono. Rispondi SOLO con la traduzione, senza preamboli:\n\n{desc_it}", max_tokens=300)
                es = _haiku_raw(f"Traduci in spagnolo questo testo culinario, mantenendo il tono. Rispondi SOLO con la traduzione, senza preamboli:\n\n{desc_it}", max_tokens=300)
                cur.execute("UPDATE ricette SET scheda_en=%s, scheda_es=%s WHERE id=%s",
                            ((en or "").strip(), (es or "").strip(), rid))
                ok += 1
            except Exception as te:
                errori.append(f"{rid}: {te}")
        conn.commit(); cur.close()
    except Exception as e:
        errori.append(str(e))
    finally:
        _release_conn(conn)
    return jsonify({"tradotte": ok, "errori": errori})


@bp.route("/admin/genera-ganci")
def admin_genera_ganci():
    """Genera UNA domanda-gancio per ogni fenomeno, partendo dalla scheda esistente.
    La domanda apre la lezione ('Perché...?') invece del secco 'X è...'.
    Generata con GPT-4o mini (economico), salvata nel campo data.gancio.
    Uso: /admin/genera-ganci?s=SECRET  (aggiungi &solo=fen-acidita per testarne uno)"""
    import ai_gateway as GW
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    solo = request.args.get("solo", "")
    rigenera = request.args.get("rigenera", "") == "1"
    limite = int(request.args.get("limite", "12"))  # batch per evitare timeout

    conn = _get_conn()
    cur = conn.cursor()
    # prendo tutti i fenomeni (nodi con scheda) — o solo quello richiesto
    if solo:
        cur.execute("SELECT id, data FROM nodes WHERE id=%s", (solo,))
    else:
        cur.execute("SELECT id, data FROM nodes WHERE id LIKE %s", ("fen-%",))
    righe = cur.fetchall()

    fatti = []
    saltati = []
    for node_id, data in righe:
        if len(fatti) >= limite:  # batch: mi fermo, la prossima chiamata continua
            break
        nd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        scheda = nd.get("scheda", "")
        if isinstance(scheda, dict):
            scheda = scheda.get("it", "") or ""
        nome = nd.get("nome") or node_id.replace("fen-", "").replace("-", " ")
        if not scheda:
            saltati.append(node_id); continue
        if nd.get("gancio") and not rigenera:
            saltati.append(node_id + " (già presente)"); continue

        # prompt secco: una domanda pratica che un professionista si fa DAVVERO
        prompt = (
            f"Ecco la scheda del fenomeno '{nome}' (food & beverage):\n\n"
            f"{scheda[:800]}\n\n"
            "Scrivi UNA domanda che catturi la CURIOSITÀ di un professionista e lo faccia "
            "fermare a leggere. Deve toccare un problema frustrante o un fatto controintuitivo "
            "che questo fenomeno spiega. Corta (max 11 parole), inizia con Perché/Come/Quando. "
            "NON deve essere un manuale ('come fare X'), ma un enigma pratico ('perché X succede'). "
            "Esempi ottimi: 'Perché due sour identici hanno sapore diverso?' · "
            "'Perché il pane di oggi non è come ieri?' · 'Perché la panna monta male d'estate?'. "
            "Rispondi SOLO con la domanda."
        )
        try:
            gancio = GW._gpt_chat(prompt, max_tokens=40)
            if gancio:
                gancio = gancio.strip().strip('"').split("\n")[0][:120]
                nd["gancio"] = gancio
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nd, ensure_ascii=False), node_id))
                fatti.append({"id": node_id, "gancio": gancio})
            else:
                saltati.append(node_id + " (no output)")
        except Exception as e:
            saltati.append(f"{node_id} (errore: {str(e)[:40]})")

    conn.commit()
    cur.close()
    _release_conn(conn)
    return jsonify({"generati": len(fatti), "saltati": len(saltati),
                    "batch_pieno": len(fatti) >= limite,
                    "dettaglio_generati": fatti[:20], "dettaglio_saltati": saltati[:20]})


@bp.route("/admin/diag-trial")
def admin_diag_trial():
    """Diagnostica il gate trial: mostra se _trial_consentito funziona o va in fail-open."""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    from utils import _trial_consentito
    out = {}
    # provo a contare gli usi per un IP di test
    test_ip = "1.2.3.4-diag"
    # prima chiamata
    ok1, info1 = _trial_consentito(None, test_ip, tipo="diag", limite=3)
    out["chiamata_1"] = {"ok": ok1, "info": info1}
    ok2, info2 = _trial_consentito(None, test_ip, tipo="diag", limite=3)
    out["chiamata_2"] = {"ok": ok2, "info": info2}
    ok3, info3 = _trial_consentito(None, test_ip, tipo="diag", limite=3)
    out["chiamata_3"] = {"ok": ok3, "info": info3}
    ok4, info4 = _trial_consentito(None, test_ip, tipo="diag", limite=3)
    out["chiamata_4_deve_bloccare"] = {"ok": ok4, "info": info4}
    # conto diretto nel DB per conferma
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trial_uso WHERE ip=%s", (test_ip,))
        out["righe_nel_db"] = cur.fetchone()[0]
        # pulisco il test
        cur.execute("DELETE FROM trial_uso WHERE ip=%s", (test_ip,))
        conn.commit(); cur.close(); _release_conn(conn)
    except Exception as e:
        out["errore_db"] = str(e)
    return jsonify(out)


@bp.route("/admin/diag-ip")
def admin_diag_ip():
    """Mostra quale IP vede il backend e quante righe trial_uso ci sono per tipo."""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    out = {"ip_visto": ip, "x_forwarded_for": request.headers.get("X-Forwarded-For", "(assente)"),
           "remote_addr": request.remote_addr}
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT tipo, COUNT(*), COUNT(DISTINCT ip) FROM trial_uso GROUP BY tipo")
        out["usi_per_tipo"] = [{"tipo": r[0], "totale": r[1], "ip_distinti": r[2]} for r in cur.fetchall()]
        cur.execute("SELECT ip, COUNT(*) FROM trial_uso WHERE tipo='foto' GROUP BY ip ORDER BY COUNT(*) DESC LIMIT 5")
        out["top_ip_foto"] = [{"ip": r[0], "usi": r[1]} for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
    except Exception as e:
        out["errore"] = str(e)
    return jsonify(out)


@bp.route("/admin/analizza-target")
def admin_analizza_target():
    """Analizza tutti i target dei fenomeni: quali sono numeri puliti, quali frasi discorsive.
    Uso: /admin/analizza-target?s=SECRET"""
    import os as _os, re as _re
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    conn = _get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, data FROM nodes WHERE id LIKE %s", ("fen-%",))
    righe = cur.fetchall()
    puliti = []; sporchi = []; vuoti = []
    for node_id, data in righe:
        nd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        target = nd.get("target", "")
        if isinstance(target, dict): target = target.get("it", "") or ""
        nome = nd.get("nome") or node_id
        if not target:
            vuoti.append(nome); continue
        # euristica "sporco": contiene verbi/frasi, "=", "grado di", parole lunghe senza numeri nel primo pezzo
        primo = _re.split(r"\s*[·;]\s*", target)[0].strip()
        # sporco se il primo pezzo è lungo (>14 char) E contiene molte lettere senza pattern numerico chiaro
        ha_numero = bool(_re.search(r"\d", primo))
        parole = len(primo.split())
        e_frase = ("=" in target or "grado di" in target.lower() or "indice" in primo.lower()
                   or (parole > 4) or (not ha_numero and parole > 2))
        if e_frase:
            sporchi.append({"id": node_id, "nome": nome, "target": target[:90]})
        else:
            puliti.append({"nome": nome, "primo": primo[:40]})
    cur.close(); _release_conn(conn)
    return jsonify({
        "totale": len(righe),
        "puliti": len(puliti), "sporchi": len(sporchi), "vuoti": len(vuoti),
        "esempi_sporchi": sporchi[:25],
        "esempi_puliti": puliti[:10]
    })


@bp.route("/admin/proponi-target")
def admin_proponi_target():
    """Genera proposte di target pulito (eroe + condizioni) per i fenomeni con target discorsivo.
    NON salva: mostra le proposte per revisione. Aggiungi &salva=1 per salvare.
    Uso: /admin/proponi-target?s=SECRET"""
    import os as _os, re as _re
    import ai_gateway as GW
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    salva = request.args.get("salva", "") == "1"
    solo = request.args.get("solo", "")

    conn = _get_conn(); cur = conn.cursor()
    if solo:
        cur.execute("SELECT id, data FROM nodes WHERE id=%s", (solo,))
    else:
        cur.execute("SELECT id, data FROM nodes WHERE id LIKE %s", ("fen-%",))
    righe = cur.fetchall()

    proposte = []
    for node_id, data in righe:
        nd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        target = nd.get("target", "")
        if isinstance(target, dict): target = target.get("it", "") or ""
        if not target: continue
        nome = nd.get("nome") or node_id
        primo = _re.split(r"\s*[·;]\s*", target)[0].strip()
        ha_numero = bool(_re.search(r"\d", primo))
        parole = len(primo.split())
        e_frase = ("=" in target or "grado di" in target.lower() or "indice" in primo.lower()
                   or (parole > 4) or (not ha_numero and parole > 2))
        if not e_frase and not solo:
            continue

        prompt = (
            f"Fenomeno F&B: '{nome}'. Target grezzo dal database:\n\"{target}\"\n\n"
            "Riscrivilo secondo questa grammatica RIGIDA per un professionista al banco:\n"
            "- EROE: il valore che il professionista deve COLPIRE più spesso nel lavoro reale, "
            "con la sua ETICHETTA CORTA + numero+unità, MASSIMO 16 caratteri "
            "(es. 'burro 50-60%', 'raddoppio 1-2h', 'AV <0.6 g/L', 'espresso 9 bar'). "
            "L'etichetta serve a capire COSA è il numero. MAI una frase lunga, MAI verbi, MAI '=', MAI costanti di formula.\n"
            "- CONDIZIONI: gli altri valori operativi con etichetta corta, separati da ' · ' "
            "(es. 'brisée 30-40% · riposo 4°C · forno 160-175°C'). Scarta costanti di formula (es. ×131.25) e dati puramente fisici.\n"
            "Scegli come EROE il caso d'uso PIÙ COMUNE, non il primo della lista.\n"
            "Rispondi SOLO in JSON: {\"eroe\":\"...\",\"condizioni\":\"... · ...\"}\n"
            "NON inventare numeri non presenti nel target grezzo."
        )
        try:
            raw = GW._gpt_chat(prompt, max_tokens=120)
            raw = (raw or "").strip().replace("```json","").replace("```","").strip()
            prop = json.loads(raw)
            eroe = (prop.get("eroe") or "").strip()[:60]
            cond = (prop.get("condizioni") or "").strip()
            nuovo_target = eroe + (" · " + cond if cond else "")
            proposte.append({"id": node_id, "nome": nome, "prima": target[:90],
                             "eroe": eroe, "condizioni": cond, "nuovo": nuovo_target})
            if salva and eroe:
                nd["target_originale"] = target  # backup
                nd["target"] = nuovo_target
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nd, ensure_ascii=False), node_id))
        except Exception as e:
            proposte.append({"id": node_id, "nome": nome, "errore": str(e)[:60], "prima": target[:90]})

    if salva: conn.commit()
    cur.close(); _release_conn(conn)
    return jsonify({"proposte": proposte, "salvate": salva, "totale": len(proposte)})


@bp.route("/admin/set-target")
def admin_set_target():
    """Imposta manualmente il target di un fenomeno.
    Uso: /admin/set-target?s=SECRET&id=fen-x&target=...(url-encoded)"""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    node_id = request.args.get("id", "")
    nuovo = request.args.get("target", "")
    if not node_id or not nuovo:
        return jsonify({"errore": "id e target obbligatori"}), 400
    conn = _get_conn(); cur = conn.cursor()
    cur.execute("SELECT data FROM nodes WHERE id=%s", (node_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); _release_conn(conn)
        return jsonify({"errore": "fenomeno non trovato"}), 404
    nd = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    vecchio = nd.get("target", "")
    nd["target"] = nuovo
    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(nd, ensure_ascii=False), node_id))
    conn.commit(); cur.close(); _release_conn(conn)
    return jsonify({"ok": True, "id": node_id, "prima": vecchio[:80], "dopo": nuovo})


# ═══ PONTE FOOD COST — vocabolario ingredienti + arricchimento ricette (Blocco A/B) ═══

# Mappa alias→ing-id costruita dal vocabolario bar (deve restare allineata al seed-ingredienti-bar.sql)
def _build_alias_map():
    # Ricostruita ad ogni chiamata: piccola (decine di ingredienti) e senza rischio
    # di cache congelata prima del caricamento del seed.
    amap = {}
    db = carica_grafo()
    rows = db.execute("SELECT id, name, data FROM nodes WHERE type='Ingrediente'").fetchall()
    for r in rows:
        iid = r["id"]; nome = r["name"]
        data = r["data"] if isinstance(r["data"], dict) else json.loads(r["data"] or "{}")
        amap[nome.lower()] = iid
        for a in (data.get("aliases") or []):
            amap[a.lower()] = iid
    return amap

def _match_ing_id(nome_ric):
    """Match nome ricetta → ing-id via alias (più lunghi prima, per precisione)."""
    amap = _build_alias_map()
    n = (nome_ric or "").lower()
    for alias in sorted(amap.keys(), key=lambda x: -len(x)):
        if alias in n:
            return amap[alias]
    return None

@bp.route("/admin/arricchisci-ricette", methods=["POST", "GET"])
def admin_arricchisci_ricette():
    """Blocco B: aggiunge ing-id stabile + scarto_pct alle voci ricetta esistenti.
    Match automatico nome→ing-id via alias. Idempotente. Auth ADMIN_SECRET.
    ?dry=1 -> anteprima senza scrivere. ?disc=bar -> solo una disciplina.
    Convenzione scarto: scarto_pct (0 default). Neutra: Cifra può convertire in resa_pct.
    """
    if not hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    dry = request.args.get("dry") == "1"
    solo_disc = request.args.get("disc")  # opzionale: filtra per disciplina
    db = carica_grafo()
    try:
        rows = db.execute("SELECT id, nome, disciplina, ingredienti FROM ricette").fetchall()
    except Exception as e:
        return jsonify({"errore": f"lettura ricette: {e}"}), 500

    report = {"ricette_totali": len(rows), "aggiornate": 0, "voci_matchate": 0,
              "voci_totali": 0, "non_matchati": [], "dettaglio": []}
    for r in rows:
        ric_id, nome, disc, ingredienti = r["id"], r["nome"], r["disciplina"], r["ingredienti"]
        if solo_disc and disc != solo_disc:
            continue
        ings = ingredienti if isinstance(ingredienti, list) else json.loads(ingredienti or "[]")
        if not ings:
            continue
        cambiato = False
        for ing in ings:
            if not isinstance(ing, dict):
                continue
            report["voci_totali"] += 1
            # aggiungi ing_id se manca
            if not ing.get("ing_id"):
                mid = _match_ing_id(ing.get("nome", ""))
                if mid:
                    ing["ing_id"] = mid
                    report["voci_matchate"] += 1
                    cambiato = True
                else:
                    report["non_matchati"].append(ing.get("nome", ""))
            else:
                report["voci_matchate"] += 1
            # aggiungi scarto_pct se manca (default 0 = nessuno scarto)
            if "scarto_pct" not in ing:
                ing["scarto_pct"] = 0
                cambiato = True
        if cambiato and not dry:
            db.execute("UPDATE ricette SET ingredienti=%s::jsonb WHERE id=%s",
                       (json.dumps(ings, ensure_ascii=False), ric_id))
            report["aggiornate"] += 1
        elif cambiato:
            report["aggiornate"] += 1  # conta anche in dry per l'anteprima
        report["dettaglio"].append({"id": ric_id, "nome": nome, "disc": disc,
                                     "voci": len(ings)})
    report["dry_run"] = dry
    report["copertura_pct"] = round(100 * report["voci_matchate"] / max(report["voci_totali"], 1))
    return jsonify(report)


@bp.route("/admin/init-usage-log", methods=["POST", "GET"])
def admin_init_usage_log():
    """Crea la tabella ai_usage_log se non esiste (così il pannello costi mostra 0
    invece di campi assenti, anche prima della prima chiamata AI). Auth ADMIN_SECRET."""
    if not hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    db = carica_grafo()
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS ai_usage_log (
                id BIGSERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                conto_id TEXT,
                user_id TEXT,
                provider TEXT,
                model TEXT,
                route TEXT,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                cost_usd NUMERIC(12,8) DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                error TEXT
            )
        """)
        n = db.execute("SELECT COUNT(*) as n FROM ai_usage_log").fetchall()
        return jsonify({"ok": True, "tabella": "ai_usage_log pronta", "righe_attuali": n[0]["n"]})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/diag-costi")
def admin_diag_costi():
    """Diagnostico: testa ogni query costi isolatamente e riporta quale rompe."""
    if not hmac.compare_digest(str(request.args.get("s","")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    import traceback as _tb
    risultati = {}
    from db import _get_conn, _release_conn
    conn = _get_conn()
    cur = conn.cursor()
    test = {
        "tabella_esiste": "SELECT COUNT(*) FROM ai_usage_log",
        "colonne": "SELECT column_name FROM information_schema.columns WHERE table_name='ai_usage_log'",
        "costo_oggi": "SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts::date = CURRENT_DATE",
        "costo_7g": "SELECT COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days'",
        "per_modello": "SELECT model, COUNT(*), COALESCE(SUM(cost_usd),0) FROM ai_usage_log WHERE ts > NOW() - INTERVAL '7 days' GROUP BY model",
        "utenti_attivi": "SELECT COUNT(*) FROM utenti WHERE attivo=TRUE",
        "utenti_pro": "SELECT COUNT(*) FROM utenti WHERE piano='pro'",
        "log_domande": "SELECT COUNT(*) FROM log_domande",
        "feedback": "SELECT COUNT(*) FROM log_domande WHERE feedback=1",
        "nodi": "SELECT COUNT(*) FROM nodes",
        "archi": "SELECT COUNT(*) FROM edges",
        "esperimenti": "SELECT COUNT(*) FROM esperimenti",
        "top_fenomeni": "SELECT fenomeni_trovati, COUNT(*) as n FROM log_domande WHERE fenomeni_trovati IS NOT NULL AND ts > NOW() - INTERVAL '7 days' GROUP BY fenomeni_trovati ORDER BY n DESC LIMIT 5",
    }
    for nome, sql in test.items():
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            risultati[nome] = {"ok": True, "righe": len(rows), "primo": str(rows[0]) if rows else None}
        except Exception as e:
            risultati[nome] = {"ok": False, "errore": str(e)[:200]}
            try: conn.rollback()
            except Exception: pass
    cur.close(); _release_conn(conn)
    return jsonify(risultati)


@bp.route("/admin/migra-feedback", methods=["POST","GET"])
def admin_migra_feedback():
    """Migrazione una-tantum: aggiunge le colonne feedback a log_domande se mancano."""
    if not hmac.compare_digest(str(request.args.get("s","")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore":"non autorizzato"}), 403
    db = carica_grafo()
    try:
        db.execute("ALTER TABLE log_domande ADD COLUMN IF NOT EXISTS feedback INTEGER")
        db.execute("ALTER TABLE log_domande ADD COLUMN IF NOT EXISTS feedback_nota TEXT")
        return jsonify({"ok": True, "messaggio": "colonne feedback aggiunte a log_domande"})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500
# redeploy trigger 1787141666
