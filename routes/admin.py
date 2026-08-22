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
    COLONNE = ["procedimento JSONB","immagine TEXT","immagine_autore TEXT","immagine_url_fonte TEXT",
        "tempo_prep INTEGER","tempo_cottura INTEGER","difficolta TEXT","porzioni TEXT",
        "applicazioni JSONB","twist_di TEXT","tecniche JSONB","abbinamenti JSONB","vino_birra JSONB"]
    conn = _get_conn()
    try:
        cur = conn.cursor(); fatte, errori = [], []
        for col in COLONNE:
            cname = col.split()[0]
            try:
                cur.execute(f"ALTER TABLE ricette ADD COLUMN IF NOT EXISTS {col}"); fatte.append(cname)
            except Exception as me:
                errori.append(f"{cname}: {me}")
        conn.commit(); cur.close()
        return jsonify({"ok": True, "colonne_ok": fatte, "errori": errori})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)

@bp.route("/admin/genera-procedimenti")
def admin_genera_procedimenti():
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json, re as _re
    import ai_gateway as GW
    disc = request.args.get("disc", "")
    limite = int(request.args.get("limite", "3"))
    solo_vuote = request.args.get("solo_vuote", "1") == "1"
    skip = int(request.args.get("skip", "0"))  # salta le prime N vuote (bypassa ricette che si bloccano)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        q = "SELECT id,nome,disciplina,descrizione,ingredienti,fenomeni,numeri,punto_critico,procedimento FROM ricette"
        if disc: q += " WHERE disciplina=%s"
        q += " ORDER BY nome"
        cur.execute(q, (disc,) if disc else ())
        rows = cur.fetchall()
        fatte, saltate, errori, n, visti_vuote = [], 0, [], 0, 0
        for row in rows:
            if n >= limite: break
            rid, nome, rdisc, desc, ingr, fen, num, pc, proc = row
            proc_parsed = proc if isinstance(proc,(list,dict)) else (_json.loads(proc) if proc else [])
            if solo_vuote and proc_parsed:
                saltate += 1; continue
            # skip: salta le prime N ricette vuote (per superare quelle che si bloccano)
            visti_vuote += 1
            if visti_vuote <= skip:
                continue
            ingr_p = ingr if isinstance(ingr,list) else (_json.loads(ingr) if ingr else [])
            num_p = num if isinstance(num,dict) else (_json.loads(num) if num else {})
            ingr_str = ", ".join(f"{i.get('quantita','')}{i.get('unita','')} {i.get('nome','')}" for i in ingr_p) if ingr_p else ""
            num_str = "; ".join(f"{k}: {v}" for k,v in num_p.items()) if num_p else ""
            prompt = (
                f"Sei un consulente scientifico F&B. Per questa ricetta REALE genera SOLO il procedimento operativo, "
                f"le applicazioni e i metadati. NON cambiare ingredienti o numeri.\n\n"
                f"RICETTA: {nome} (disciplina: {rdisc})\nINGREDIENTI: {ingr_str}\n"
                f"NUMERI BERSAGLIO: {num_str}\nPUNTO CRITICO: {pc or ''}\n\n"
                f"Rispondi in italiano SOLO con questo JSON (nessun testo extra):\n"
                f'{{"procedimento": [{{"n":1,"testo":"passaggio specifico e reale","numero_chiave":"il numero critico di questo passo (es. 80-85 gradi) o null"}}], '
                f'"applicazioni":["dove si usa questa preparazione nel mestiere"], '
                f'"tempo_prep":minuti_interi, "tempo_cottura":minuti_interi, '
                f'"difficolta":"facile|media|difficile", "porzioni":"es. 4 persone"}}\n\n'
                f"I passaggi devono essere SPECIFICI di questa ricetta e usare i numeri bersaglio dove pertinente. "
                f"Ogni passo che tocca un parametro critico DEVE avere numero_chiave. Niente markdown."
            )
            prompt_semplice = (
                f"Genera il procedimento per: {nome} ({rdisc}). Ingredienti: {ingr_str}. "
                f"Numeri: {num_str}. Rispondi SOLO con JSON valido, niente altro, massimo 7 passi brevi:\n"
                f'{{"procedimento":[{{"n":1,"testo":"...","numero_chiave":null}}],"applicazioni":["..."],'
                f'"tempo_prep":30,"tempo_cottura":0,"difficolta":"media","porzioni":"4"}}'
            )
            dati = None
            for tentativo in range(3):
                try:
                    pr = prompt if tentativo < 2 else prompt_semplice  # 3° tentativo: prompt semplificato
                    raw = GW.route_fast(pr, max_tokens=1400, temperature=0)
                    if not raw:
                        continue
                    m = _re.search(r"\{.*\}", raw, _re.DOTALL)
                    if not m:
                        continue
                    testo = m.group(0)
                    testo = _re.sub(r",\s*([}\]])", r"\1", testo)  # virgole finali
                    testo = testo.replace("\n"," ").replace("\t"," ")  # newline dentro stringhe
                    dati = _json.loads(testo)
                    break
                except Exception:
                    dati = None
            if dati is None:
                errori.append(f"{rid}: JSON non valido dopo 3 tentativi"); n+=1; continue
            try:
                cur.execute("UPDATE ricette SET procedimento=%s::jsonb, applicazioni=%s::jsonb, tempo_prep=%s, tempo_cottura=%s, difficolta=%s, porzioni=%s WHERE id=%s",
                    (_json.dumps(dati.get("procedimento",[]),ensure_ascii=False),
                     _json.dumps(dati.get("applicazioni",[]),ensure_ascii=False),
                     dati.get("tempo_prep"), dati.get("tempo_cottura"),
                     dati.get("difficolta",""), dati.get("porzioni",""), rid))
                conn.commit()
                fatte.append(f"{nome}: {len(dati.get('procedimento',[]))} passi")
            except Exception as ge:
                errori.append(f"{rid}: {str(ge)[:80]}")
            n += 1
        return jsonify({"ok":True, "generate":fatte, "saltate_gia_pronte":saltate, "errori":errori})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)

@bp.route("/admin/coverage-fenomeni")
def admin_coverage_fenomeni():
    """Diagnostica 'Bibbia': per ogni fenomeno misura quanto è completo e collegato.
    Assi: principio (governato_da), numero-bersaglio (data o si_manifesta_in.target),
    errore (fallisce_come), tecnica (realizzato_da/controllato_con), prodotto (si_manifesta_in)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno'")
        fen = cur.fetchall()
        # tutti gli edge in uscita dai fenomeni
        cur.execute("SELECT from_id, relation, to_id, data FROM edges")
        edges = cur.fetchall()
        out = {}
        for e in edges:
            fid = e[0] if not hasattr(e,"keys") else e["from_id"]
            out.setdefault(fid, []).append((e[1] if not hasattr(e,"keys") else e["relation"],
                                            e[2] if not hasattr(e,"keys") else e["to_id"],
                                            e[3] if not hasattr(e,"keys") else e["data"]))
        report = []
        conteggi = {"principio":0,"numero":0,"errore":0,"tecnica":0,"prodotto":0,"completi":0,"orfani":0}
        for f in fen:
            fid = f[0] if not hasattr(f,"keys") else f["id"]
            fname = f[1] if not hasattr(f,"keys") else f["name"]
            fdom = f[2] if not hasattr(f,"keys") else f["domain"]
            fdata = f[3] if not hasattr(f,"keys") else f["data"]
            fd = fdata if isinstance(fdata,dict) else (_json.loads(fdata) if fdata else {})
            rels = out.get(fid, [])
            has_princ = any(r[0]=="governato_da" for r in rels)
            has_err = any(r[0]=="fallisce_come" for r in rels)
            has_tec = any(r[0] in ("realizzato_da","controllato_con") for r in rels)
            prods = [r for r in rels if r[0]=="si_manifesta_in"]
            has_prod = len(prods)>0
            # numero: nel data del fenomeno o in un target di prodotto
            has_num = bool(fd.get("numero_bersaglio") or fd.get("target") or fd.get("bersaglio"))
            if not has_num:
                for r in prods:
                    rd = r[2] if isinstance(r[2],dict) else (_json.loads(r[2]) if r[2] else {})
                    if rd.get("target"): has_num=True; break
            for k,v in [("principio",has_princ),("numero",has_num),("errore",has_err),("tecnica",has_tec),("prodotto",has_prod)]:
                if v: conteggi[k]+=1
            score = sum([has_princ,has_num,has_err,has_tec,has_prod])
            if score==5: conteggi["completi"]+=1
            if score<=1: conteggi["orfani"]+=1
            mancano = [k for k,v in [("principio",has_princ),("numero",has_num),("errore",has_err),("tecnica",has_tec),("prodotto",has_prod)] if not v]
            report.append({"id":fid,"nome":fname,"dom":fdom,"score":score,"mancano":mancano})
        report.sort(key=lambda x:x["score"])
        senza = {"principio":[],"numero":[],"errore":[],"tecnica":[],"prodotto":[]}
        for r in report:
            for asse in r["mancano"]:
                senza[asse].append(r["id"])
        return jsonify({"totale_fenomeni":len(fen), "conteggi":conteggi,
                        "peggiori_20":report[:20], "senza":senza,
                        "nota":"score 5 = completo (Bibbia); score<=1 = orfano"})
    except Exception as e:
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)

@bp.route("/admin/principi-cardine")
def admin_principi_cardine():
    """La Bibbia ha bisogno del suo tetto: i principi fisici fondamentali.
    Crea i principi mancanti e collega OGNI fenomeno al principio che lo governa (governato_da)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # I PRINCIPI CARDINE (pochi, fondamentali). id -> (nome, scheda)
    PRINCIPI = {
        "princ-kt": ("kT - energia termica",
            "L'energia termica kT e la moneta con cui la temperatura governa la velocita di ogni reazione e trasformazione. Piu sale la temperatura, piu le molecole si agitano: la 'coda di Boltzmann' spiega perche una reazione parte a una certa soglia e accelera col calore (regola Q10). E il principio sotto Maillard, caramellizzazione, denaturazione, fermentazione: sono tutte reazioni la cui velocita e governata da kT."),
        "princ-calore": ("Trasporto di calore - conduzione, convezione, irraggiamento",
            "Il calore si muove in tre modi: conduzione (contatto diretto, la padella alla carne), convezione (attraverso un fluido, l'aria del forno o l'acqua che bolle), irraggiamento (onde elettromagnetiche, la brace o il grill). Il MODO con cui il calore arriva al cibo decide il risultato: la crosta della bistecca (conduzione ad alta T), la cottura uniforme del forno ventilato (convezione), la doratura del grill (irraggiamento). Governa cottura, rosolatura, frittura, panificazione."),
        "princ-denaturazione": ("Denaturazione e coagulazione proteica",
            "Le proteine sono catene ripiegate: il calore (o l'acido, o il sale) rompe i legami deboli che tengono la forma, la proteina si 'srotola' (denatura) e poi si lega alle vicine (coagula). E' un processo a soglia di temperatura: albume 62-65C, tuorlo 65-70C, collagene che diventa gelatina a 68C+. Governa uova, carne, pesce, la schiuma dell'albume, la chiarificazione."),
        "princ-ph": ("Equilibri acido-base (pH)",
            "Il pH misura quanti ioni idrogeno liberi ci sono: sotto 7 acido, sopra 7 basico. Il pH decide se una proteina precipita (il latte che taglia a pH 4.6, la stessa fisica della ricotta e della chiarificazione al latte), il colore delle verdure verdi (la clorofilla vira a feofitina in ambiente acido), la sicurezza delle conserve (sotto pH 4.6 il botulino non cresce), l'equilibrio di un cocktail. Governa fermentazioni, conserve, colore, coagulazione acida."),
        "princ-diffusione": ("Diffusione e osmosi - trasporto di massa",
            "Le molecole si spostano spontaneamente da dove sono concentrate a dove lo sono meno (diffusione); attraverso una membrana, e l'acqua a muoversi verso la maggior concentrazione (osmosi). Governa la salamoia e la marinatura (il sale entra, l'acqua esce), l'estrazione del caffe e delle infusioni, la disidratazione, la stagionatura, il modo in cui uno sciroppo penetra la frutta."),
        "princ-emulsione": ("Emulsioni e tensioattivi",
            "Acqua e grasso non si mescolano: un'emulsione e grasso disperso in acqua (o viceversa) in goccioline stabilizzate da un tensioattivo (lecitina del tuorlo, caseina del latte, saponine dell'albume) che fa da ponte tra i due. La tensione superficiale e la forza che i tensioattivi abbassano per tenere unite le gocce. Governa maionese, salse, il sour col bianco d'uovo, la panna montata, la ganache, l'espresso."),
        "princ-cristallizzazione": ("Cristallizzazione e transizioni di fase",
            "Quando un liquido solidifica, le molecole si ordinano in cristalli: la DIMENSIONE dei cristalli decide la texture. Cristalli piccoli = liscio (gelato mantecato in fretta, cioccolato temperato in Forma V); cristalli grossi = ruvido (gelato ricristallizzato, zucchero che afra). Governa gelato, sorbetti, temperaggio del cioccolato, caramello, la gestione dell'acqua che congela."),
        "princ-gelatinizzazione": ("Gelatinizzazione e reti (amidi e glutine)",
            "Alcune molecole formano reti che intrappolano acqua e danno struttura: l'amido che assorbe acqua e gonfia col calore (gelatinizzazione, 60-70C: addensa creme e salse, cuoce la pasta e il pane), il glutine che forma la maglia elastica dell'impasto, la pectina e la gelatina che gelificano. Governa pane, pasta, creme, salse addensate, gel, la mollica."),
    }
    # MAPPA: quale principio governa un fenomeno (per keyword nel nome/id). Ordine = priorita.
    REGOLE = [
        (["maillard","rosolatura","caramell","soffritto","doratura","crosta"], "princ-calore"),
        (["collagene","brasato","denaturazione","coagulazione","uova","uovo","carne","albume","riposo-carne","sous-vide"], "princ-denaturazione"),
        (["ph","acido","botulino","conserve","chiarificazione","verdure-verdi","clorofilla","malolattica","catena-freddo","haccp","anisakis","attivita-acqua","aw"], "princ-ph"),
        (["diffusion","osmosi","salamoia","marinat","estrazione","infusion","macinatura","caffe","fat-washing","stagionat","disidrat"], "princ-diffusione"),
        (["emulsion","maionese","salse","montatura","panna","ganache","sour","dry-shake","tensione","schiuma","fat-wash"], "princ-emulsione"),
        (["cristall","gelato","temperaggio","cioccolato","sorbetto","overrun","zuccheri-pac","congelamento","ghiaccio"], "princ-cristallizzazione"),
        (["gelatinizz","amido","glutine","impasto","lievitazione","pane","pasta","crema-pasticcera","addensant","pectina","gelificazione","tangzhong","maglia"], "princ-gelatinizzazione"),
        (["carbonazione","carbonatazione","gas","henry","birra","luppolo","spuma","highball"], "princ-kt"),
        (["fermentazione","lievito","alcol","tannini","vino","mosto","luppolo"], "princ-ph"),
        (["temperatura","calore","cottura","frittura","forno","q10","boltzmann","punto-fumo","ustioni","pressione","concentrazione"], "princ-calore"),
        (["acidita","ossidazione","solforosa","solubilita","enzim","autolisi","proteolisi","amilolisi","lipolisi","mash-enzimi","attivita-enzimatica","maturazione-legno","atmosfera-modificata","contaminazione","shelf-life","zona-pericolo","levain","poolish","biga","pate-fermentee"], "princ-ph"),
        (["diffusion","distillazione","dry-hopping","clarificazione","clarification","solubilita"], "princ-diffusione"),
        (["equilibrio-cocktail","amaro-bitter","shakerare","diluizione","viscosita","sineresi","texture-agents","struttura","souffle","grassi-stabil"], "princ-emulsione"),
        (["crioscopia","pac-gelateria"], "princ-cristallizzazione"),
        (["farina-forza","enzimi-farina"], "princ-gelatinizzazione"),
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        creati = []
        for pid,(nome,scheda) in PRINCIPI.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(pid,))
            if not cur.fetchone():
                cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                    (pid,"principio",nome,"trasversale",_json.dumps({"scheda":scheda},ensure_ascii=False)))
                creati.append(pid)
            else:
                cur.execute("UPDATE nodes SET data=jsonb_set(COALESCE(data,'{}')::jsonb,'{scheda}',%s::jsonb) WHERE id=%s",
                    (_json.dumps(scheda,ensure_ascii=False),pid))
        # collego i fenomeni
        cur.execute("SELECT id,name FROM nodes WHERE type='Fenomeno'")
        fen = cur.fetchall()
        collegati, gia, nonmappati = 0, 0, []
        for f in fen:
            fid = (f[0] if not hasattr(f,"keys") else f["id"])
            fname = (f[1] if not hasattr(f,"keys") else f["name"]) or ""
            testo = (fid+" "+fname).lower()
            principio = None
            for keys, pid in REGOLE:
                if any(k in testo for k in keys):
                    principio = pid; break
            if not principio:
                nonmappati.append(fid); continue
            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='governato_da' AND to_id=%s",(fid,principio))
            if cur.fetchone(): gia+=1; continue
            cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                (fid,principio,"governato_da",_json.dumps({},ensure_ascii=False)))
            collegati+=1
        conn.commit()
        return jsonify({"ok":True,"principi_creati":creati,"fenomeni_collegati":collegati,
                        "gia_collegati":gia,"non_mappati":nonmappati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/errori-completa")
def admin_errori_completa():
    """Completa l'asse ERRORI: errore tipico (sintomo al banco -> causa) per i fenomeni che ne hanno 0."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # (err_id, nome, dom, causa, fenomeno, sintomo)
    ERRORI = [
        ("err-catena-freddo-rotta","Catena del freddo interrotta","tecnologie",
         "il prodotto e rimasto sopra i 4C troppo a lungo: i batteri patogeni si moltiplicano nella zona di pericolo 4-60C. Mantenere sotto 4C in frigo, sopra 63C in mantenimento caldo, e ridurre al minimo il tempo intermedio","fen-catena-freddo","condensa, odore, prodotto tiepido"),
        ("err-aw-alta","Prodotto secco che ammuffisce","tecnologie",
         "attivita dell'acqua (Aw) troppo alta: sopra 0.6 le muffe crescono, sopra 0.85 i batteri. Un salume o un biscotto poco essiccato ha Aw alta e non e stabile a temperatura ambiente. Ridurre l'umidita libera con essiccazione, sale o zucchero","fen-attivita-acqua","muffa, irrancidimento, consistenza molle"),
        ("err-anisakis-vivo","Pesce crudo non abbattuto","tecnologie",
         "parassita Anisakis vivo: il pesce destinato al consumo crudo DEVE essere abbattuto a -20C per 24h (o -35C per 15h) per legge (Reg. CE 853/2004). Saltare l'abbattimento e un rischio sanitario grave","fen-anisakis","(rischio invisibile - per questo la regola e tassativa)"),
        ("err-haccp-saltato","Punto critico non monitorato","tecnologie",
         "un CCP (punto critico di controllo) senza limite misurato e senza registrazione: l'HACCP funziona solo se ogni punto critico ha un limite (es. temperatura), un monitoraggio e un'azione correttiva. Saltare la registrazione rende il sistema cieco","fen-haccp","non conformita, nessuna tracciabilita"),
        ("err-conserva-botulino","Conserva a rischio botulino","tecnologie",
         "conserva a bassa acidita (pH sopra 4.6) non sterilizzata correttamente: il Clostridium botulinum produce tossina in assenza di ossigeno. Le conserve non acide vanno sterilizzate in autoclave; sotto pH 4.6 (acidificando) il batterio non cresce","fen-conserve-botulino","coperchio gonfio, odore, bolle"),
        ("err-olio-fiamma","Olio di frittura che prende fuoco","tecnologie",
         "olio oltre il punto di fumo verso il punto di fiamma: olio surriscaldato (oltre 200-230C) fuma e puo incendiarsi. Mai acqua su un incendio d'olio (esplode): soffocare con un coperchio. Controllare la temperatura","fen-ustioni-olio","fumo acre, poi fiamma"),
        ("err-shake-sbagliato","Drink torbido quando doveva essere limpido","bar",
         "shakerato invece che mescolato (o viceversa): si shakera solo con agrumi/albume/latticini (serve emulsione e aria); si mescola quando tutti gli ingredienti sono limpidi (Negroni, Martini) per un drink cristallino e setoso","fen-shakerare-mescolare","torbido, o al contrario piatto e poco freddo"),
        ("err-infusione-amara","Infusione troppo amara o astringente","bar",
         "infusione troppo lunga o troppo calda: si estraggono i tannini e le note amare oltre gli aromi. Ridurre tempo e temperatura, assaggiare spesso: l'estrazione degli aromi e piu veloce di quella degli amari","fen-infusioni","amaro pungente, astringenza"),
        ("err-ghiaccio-annacqua","Drink annacquato dal ghiaccio","bar",
         "ghiaccio piccolo o bagnato: troppa superficie fonde in fretta e diluisce. Usare ghiaccio grande e asciutto (da congelatore, non da secchiello bagnato); il cubo grande raffredda con meno diluizione","fen-ghiaccio","acquoso, sapore diluito"),
        ("err-bitter-squilibrato","Amaro che copre tutto","bar",
         "troppo bitter o amaro non integrato: l'amaro deve incorniciare, non dominare. Dosare a gocce, bilanciare con la dolcezza; l'amaro percepito cambia con la temperatura e la diluizione","fen-amaro-bitter","drink sbilanciato sull'amaro"),
        ("err-chiarifica-fallita","Chiarificazione al latte che resta torbida","bar",
         "il latte non ha coagulato bene: serve acidita (il pH deve scendere sotto 4.6 col succo di agrumi) perche la caseina precipiti e intrappoli le particelle. Latte troppo poco, o acido insufficiente, lasciano il liquido torbido","fen-chiarificazione-latte","liquido opaco invece che cristallino"),
        ("err-pac-sbagliato","Gelato troppo duro o troppo molle","gelateria",
         "PAC (potere anticongelante) sbilanciato: troppo zucchero anticongelante (destrosio, fruttosio, invertito) e il gelato non indurisce; troppo poco ed e un mattone. Bilanciare gli zuccheri sul PAC target","fen-zuccheri-pac","non spatolabile, o si scioglie subito"),
        ("err-stabilizzanti-sbagliati","Gelato che si sfalda o e gommoso","gelateria",
         "grassi e stabilizzanti fuori dose: pochi e il gelato e ghiacciato e instabile; troppi ed e gommoso, pastoso. I grassi danno cremosita, gli stabilizzanti trattengono l'acqua: vanno dosati","fen-grassi-stabilizzanti","sfaldato, oppure gommoso"),
        ("err-fermentazione-bloccata","Fermentazione che si ferma","vino",
         "fermentazione bloccata: lievito morto per temperatura troppo alta (sopra 30-35C), carenza di nutrienti, o troppo alcol. Controllare la temperatura, nutrire il lievito, verificare la densita","fen-fermentazione-alcolica","densita ferma, sapore dolce residuo"),
        ("err-tannini-aggressivi","Vino/tannino troppo astringente","vino",
         "estrazione tannica eccessiva: troppa macerazione su bucce e semi, o tannini verdi da uve non mature. Ridurre il contatto con le bucce, l'affinamento ammorbidisce; servire piu caldo attenua l'astringenza","fen-tannini-vino","bocca secca, allappante"),
        ("err-luppolo-squilibrato","Birra troppo amara o senza aroma","birra",
         "luppolo mal gestito: luppolo da amaro aggiunto troppo (IBU alti squilibrati) o luppolo da aroma bollito troppo a lungo (l'aroma volatile evapora). Amaro a inizio bollitura, aroma a fine o in dry hopping","fen-luppolo","amaro aggressivo, o nessun profumo"),
        ("err-macinatura-sbagliata","Caffe sotto o sovra-estratto","caffetteria",
         "macinatura sbagliata per il metodo: troppo grossa = sotto-estratto (acido, acquoso); troppo fine = sovra-estratto (amaro, astringente). Regolare la macinatura sul metodo (fine espresso, media V60, grossa French press)","fen-macinatura-caffe","acido e debole, oppure amaro"),
        ("err-soffritto-bruciato","Soffritto bruciato o crudo","cucina",
         "temperatura sbagliata: troppo alta brucia l'aglio e le verdure (amaro); troppo bassa le lessa senza sviluppare aromi. Fuoco medio-basso, olio non fumante, pazienza: il soffritto e una base aromatica, non una doratura","fen-soffritto","bruciato e amaro, o crudo e slegato"),
        ("err-tangzhong-liquido","Tangzhong troppo liquido o troppo denso","panificazione",
         "rapporto acqua/farina o temperatura sbagliata: il tangzhong (roux di acqua e farina) va portato a 65C perche l'amido gelatinizzi e trattenga acqua. Troppo liquido non lega, troppo cotto e un grumo","fen-tangzhong-yudane","impasto che non trattiene umidita"),
        ("err-levain-debole","Lievito madre/levain debole","panificazione",
         "madre non abbastanza attiva o matura: rinfreschi irregolari, temperatura bassa, poca forza. Il levain deve raddoppiare e passare il test del galleggiamento prima dell'uso; una madre debole non solleva l'impasto","fen-levain-pate-fermentee","impasto che non lievita, acidita eccessiva"),
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor(); fatti=[]
        for eid,nome,dom,causa,fen,sintomo in ERRORI:
            cur.execute("SELECT id FROM nodes WHERE id=%s",(eid,))
            if not cur.fetchone():
                cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                    (eid,"Errore",nome,dom,_json.dumps({"causa":causa},ensure_ascii=False)))
            cur.execute("SELECT id FROM nodes WHERE id=%s",(fen,))
            if cur.fetchone():
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='fallisce_come' AND to_id=%s",(fen,eid))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        (fen,eid,"fallisce_come",_json.dumps({"sintomo":sintomo},ensure_ascii=False)))
                    fatti.append(f"{fen} -> {eid}")
            else:
                fatti.append(f"{fen}: FENOMENO ASSENTE")
        conn.commit()
        return jsonify({"ok":True,"errori":fatti})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/tecniche-completa")
def admin_tecniche_completa():
    """Completa l'asse TECNICHE: collega i fenomeni alle tecniche esistenti (realizzato_da)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # fenomeno -> [tecniche che lo realizzano/governano] (tecniche gia esistenti nel grafo)
    MAPPA = {
        "fen-frittura": ["tec-frittura"],
        "fen-gelatinizzazione-salse": ["tec-emulsione","tec-deglassare"],
        "fen-catena-freddo": ["tec-lettura-ph","tec-curing"],
        "fen-attivita-acqua": ["tec-curing","tec-affumicatura"],
        "fen-anisakis": ["tec-curing"],
        "fen-haccp": ["tec-lettura-ph"],
        "fen-conserve-botulino": ["tec-lettura-ph","tec-fermentazione-lattica"],
        "fen-ustioni-olio": ["tec-frittura"],
        "fen-shakerare-mescolare": ["tec-shake","tec-stir"],
        "fen-attivita-enzimatica": ["tec-fermentazione-lattica","tec-curing"],
        "fen-collagene-brasato": ["tec-brasatura-tecnica","tec-sobbollitura"],
        "fen-infusioni": ["tec-fat-washing-tecnica","tec-muddle"],
        "fen-zuccheri-impasto": ["tec-impasto"],
        "fen-uova-impasto": ["tec-impasto"],
        "fen-latte-impasto": ["tec-impasto"],
        "fen-cottura-sous-vide": ["tec-sous-vide-tecnica"],
        "fen-tangzhong-yudane": ["tec-impasto"],
        "fen-levain-pate-fermentee": ["tec-poolish-preferment","tec-retard"],
        "fen-rosolatura": ["tec-rosolatura","tec-saltatura"],
        "fen-ghiaccio": ["tec-shake","tec-stir"],
        "fen-amaro-bitter": ["tec-muddle"],
        "fen-chiarificazione-latte": ["tec-milk-punch"],
        "fen-diluizione": ["tec-shake","tec-stir"],
        "fen-distillazione": ["tec-fat-washing-tecnica"],
        "fen-macinatura-caffe": ["tec-estrazione-espresso","tec-pour-over"],
        "fen-zuccheri-pac": ["tec-bilanciamento-mix"],
        "fen-grassi-stabilizzanti": ["tec-bilanciamento-mix","tec-mantecatura"],
        "fen-fermentazione-alcolica": ["tec-vinificazione-bianco","tec-macerazione"],
        "fen-tannini-vino": ["tec-macerazione"],
        "fen-luppolo": ["tec-mash","tec-dry-hopping-tecnica"],
        "fen-soffritto": ["tec-saltatura"],
        "fen-mash-enzimi": ["tec-mash"],
        "fen-dry-hopping": ["tec-dry-hopping-tecnica"],
        "fen-maturazione-legno": ["tec-macerazione"],
        "fen-autolisi": ["tec-autolisi"],
        "fen-poolish-biga": ["tec-poolish-preferment"],
    }
    conn = _get_conn()
    try:
        cur = conn.cursor(); fatti=[]; saltati=[]
        for fen, tecs in MAPPA.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(fen,))
            if not cur.fetchone():
                saltati.append(f"{fen}(no fen)"); continue
            for tec in tecs:
                cur.execute("SELECT id FROM nodes WHERE id=%s",(tec,))
                if not cur.fetchone():
                    saltati.append(f"{tec}(no tec)"); continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='realizzato_da' AND to_id=%s",(fen,tec))
                if cur.fetchone(): continue
                cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                    (fen,tec,"realizzato_da",_json.dumps({},ensure_ascii=False)))
                fatti.append(f"{fen}->{tec}")
        conn.commit()
        return jsonify({"ok":True,"collegati":fatti,"saltati":saltati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/genera-errori-ai")
def admin_genera_errori_ai():
    """Genera con AI un errore tipico (sintomo->causa) per i fenomeni senza errore, ancorato ai dati reali."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json, re as _re
    import ai_gateway as GW
    limite = int(request.args.get("limite","3"))
    skip = int(request.args.get("skip","0"))
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # fenomeni senza errore
        cur.execute("""SELECT n.id, n.name, n.domain, n.data FROM nodes n
            WHERE n.type='Fenomeno' AND NOT EXISTS
            (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='fallisce_come')
            ORDER BY n.id""")
        rows = cur.fetchall()
        fatti, errori, n, visti = [], [], 0, 0
        for row in rows:
            if n>=limite: break
            visti+=1
            if visti<=skip: continue
            fid = row[0] if not hasattr(row,"keys") else row["id"]
            fname = row[1] if not hasattr(row,"keys") else row["name"]
            fdom = row[2] if not hasattr(row,"keys") else row["domain"]
            fdata = row[3] if not hasattr(row,"keys") else row["data"]
            fd = fdata if isinstance(fdata,dict) else (_json.loads(fdata) if fdata else {})
            scheda = str(fd.get("scheda") or fd.get("scheda_it") or "")[:600]
            numero = str(fd.get("numero_bersaglio") or fd.get("target") or "")
            prompt = (
                f"Sei un consulente scientifico F&B. Per questo fenomeno, scrivi UN errore tipico che un "
                f"professionista fa al banco. Rispondi SOLO con JSON valido.\n\n"
                f"FENOMENO: {fname}\nSCHEDA: {scheda}\nNUMERO BERSAGLIO: {numero}\n\n"
                f'{{"nome_errore":"nome breve dell errore (es. Brasato stopposo)",'
                f'"sintomo":"cosa vede/sente il professionista al banco, concreto",'
                f'"causa":"la causa fisica + come si rimedia, 1-2 frasi con un numero se pertinente"}}'
            )
            try:
                raw = GW.route_fast(prompt, max_tokens=500, temperature=0)
                m = _re.search(r"\{.*\}", raw or "", _re.DOTALL)
                if not m: errori.append(f"{fid}: no-json"); n+=1; continue
                d = _json.loads(_re.sub(r",\s*([}\]])",r"\1",m.group(0)))
                eid = "err-"+_re.sub(r"[^a-z0-9]+","-", (d.get("nome_errore","") or fid).lower()).strip("-")[:40]
                cur.execute("SELECT id FROM nodes WHERE id=%s",(eid,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                        (eid,"Errore",d.get("nome_errore","Errore"),fdom,_json.dumps({"causa":d.get("causa","")},ensure_ascii=False)))
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='fallisce_come' AND to_id=%s",(fid,eid))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        (fid,eid,"fallisce_come",_json.dumps({"sintomo":d.get("sintomo","")},ensure_ascii=False)))
                conn.commit()
                fatti.append(f"{fid} -> {d.get('nome_errore','')[:30]}")
            except Exception as ge:
                errori.append(f"{fid}: {str(ge)[:60]}")
            n+=1
        # quanti restano
        cur.execute("""SELECT COUNT(*) FROM nodes n WHERE n.type='Fenomeno' AND NOT EXISTS
            (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='fallisce_come')""")
        restano = cur.fetchone()[0]
        return jsonify({"ok":True,"generati":fatti,"errori":errori,"restano_senza_errore":restano})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/tecniche-completa2")
def admin_tecniche_completa2():
    """Completa TECNICHE al 100%: collega a tecniche esistenti + crea tecniche NUOVE (incluse strumentali)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # tecniche NUOVE da creare (id -> nome, disciplina, scheda)
    NUOVE = {
        "tec-bilanciamento-drink": ("Bilanciamento del drink","bar","Regolare le quattro forze (dolce, acido, forte, amaro) verso l'equilibrio. Il sour classico e 2:1:1 (distillato:acido:dolce). Si assaggia e si corregge: piu acido se stucchevole, piu dolce se aggressivo."),
        "tec-cottura-pasta": ("Cottura della pasta","cucina","Acqua abbondante (1L ogni 100g), sale 7-10g/L, bollore vivace. Scolare al dente (cuore ancora vetroso). L'acqua di cottura, ricca di amido, emulsiona la salsa: tenerne un mestolo."),
        "tec-dry-shake": ("Dry shake (emulsione albume)","bar","Shakerata SENZA ghiaccio prima (10-15s) per denaturare l'albume e creare la schiuma, poi con ghiaccio per raffreddare e diluire. Senza il dry shake la schiuma e grossolana e instabile."),
        "tec-shock-termico": ("Sbollentatura e shock termico","cucina","Tuffo veloce in acqua bollente salata, poi shock in acqua e ghiaccio per fermare la cottura. Fissa il verde della clorofilla (evita il viraggio a feofitina) e ferma la cottura al punto giusto."),
        "tec-riposo-carne": ("Riposo della carne","cucina","Far riposare la carne dopo la cottura (bistecca 5 min, arrosto 15-20) coperta. Le fibre si rilassano e i succhi si ridistribuiscono invece di uscire al taglio. Salta il riposo = tagliere allagato."),
        "tec-roner-sottovuoto": ("Cottura a bassa temperatura (roner/sottovuoto)","cucina","Cottura in sacchetto sottovuoto immerso in acqua a temperatura controllata dal roner (termocircolatore). Precisione al grado: uovo 63C, petto di pollo 62-64C, manzo 54-56C. Tempo lungo, risultato uniforme cuore-superficie. La macchina sottovuoto toglie l'aria (trasferimento di calore migliore, no ossidazione)."),
        "tec-abbattimento": ("Abbattimento e crioscopia","gelateria","Raffreddamento rapido sotto zero (abbattitore): congela in fretta = cristalli piccoli = liscio. Nel gelato governa la crioscopia (abbassamento del punto di congelamento con gli zuccheri). Rallentare = cristalli grossi = ruvido."),
        "tec-sifone-spuma": ("Sifone e spume","cucina","Caricare un liquido (con addensante o grasso) in un sifone con cartuccia di N2O: il gas si scioglie sotto pressione e in uscita espande in spuma/espuma. Governa aria, texture, aromi concentrati in leggerezza."),
        "tec-disidratazione": ("Essiccazione e disidratazione","cucina","Rimuovere acqua a bassa temperatura (essiccatore/disidratatore, 40-60C) per concentrare aromi e abbassare l'attivita dell'acqua (Aw) sotto le soglie di crescita microbica. Governa conservazione, chips, polveri, croccantezze."),
        "tec-rotovapor": ("Distillazione a freddo (rotavapor)","bar","Distillare sotto vuoto a bassa temperatura (rotavapor): il vuoto abbassa il punto di ebollizione, si estraggono aromi delicati senza cuocerli. Per distillati aromatici, essenze, riduzioni limpide che a caldo si degraderebbero."),
        "tec-fermentazione-controllata": ("Fermentazione controllata","vino","Governare la fermentazione controllando temperatura (lieviti fragili sopra 30-35C), nutrienti, e densita. Vale per vino, birra, impasti: il lievito e vivo, va tenuto nella finestra giusta."),
        "tec-affinamento": ("Affinamento e maturazione","vino","Far evolvere il prodotto nel tempo in condizioni controllate (bottiglia, botte, cella): i tannini si ammorbidiscono, gli aromi si integrano. Governa vino, distillati, formaggi, salumi."),
        "tec-montatura": ("Montatura (aria in emulsione)","pasticceria","Incorporare aria sbattendo: la panna monta perche i globuli di grasso inglobano bolle (tra 4C e non oltre, o si smonta in burro); l'albume monta perche le proteine intrappolano aria. Governa panna, meringhe, mousse, souffle."),
        "tec-controllo-acqua": ("Gestione dell'acqua (brewing)","caffetteria","Regolare durezza e minerali dell'acqua: troppo dura estrae male e incrosta, troppo pura e piatta. L'acqua e il 98% del caffe e oltre il 90% della birra: profilo minerale giusto = estrazione giusta."),
    }
    # fenomeno -> tecniche (esistenti O nuove appena create)
    MAPPA = {
        "fen-equilibrio-cocktail": ["tec-bilanciamento-drink"],
        "fen-pasta-acqua": ["tec-cottura-pasta"],
        "fen-emulsione-bar": ["tec-dry-shake","tec-shake"],
        "fen-uova-coagulazione": ["tec-poche","tec-roner-sottovuoto"],
        "fen-emulsione-salse": ["tec-emulsione"],
        "fen-verdure-verdi": ["tec-shock-termico","tec-sbianchitura"],
        "fen-riposo-carne": ["tec-riposo-carne","tec-arrostitura"],
        "fen-cristalli-ghiaccio": ["tec-mantecatura","tec-abbattimento"],
        "fen-enzimi-farina": ["tec-autolisi","tec-impasto"],
        "fen-aw": ["tec-disidratazione","tec-curing"],
        "fen-grassi-impasto": ["tec-impasto","tec-laminazione" if False else "tec-formatura"],
        "fen-lievito-madre": ["tec-poolish-preferment","tec-retard"],
        "fen-lievitazione-chimica": ["tec-impasto"],
        "fen-coagulazione": ["tec-poche","tec-roner-sottovuoto"],
        "fen-lipolisi": ["tec-curing","tec-affinamento"],
        "fen-solforosa": ["tec-lettura-ph","tec-fermentazione-controllata"],
        "fen-overrun": ["tec-mantecatura"],
        "fen-vaporizzazione": ["tec-vaporizzazione-latte"],
        "fen-crioscopia": ["tec-abbattimento","tec-bilanciamento-mix"],
        "fen-viscosita": ["tec-emulsione"],
        "fen-shelf-life-pane": ["tec-disidratazione"],
        "fen-stabilizzanti-gelato": ["tec-bilanciamento-mix","tec-mantecatura"],
        "fen-laminazione": ["tec-formatura"],
        "fen-overrun-controllo": ["tec-mantecatura"],
        "fen-brett": ["tec-fermentazione-controllata","tec-affinamento"],
        "fen-brodo-fondo": ["tec-sobbollitura"],
        "fen-brasatura": ["tec-brasatura-tecnica"],
        "fen-salamoia": ["tec-marinatura","tec-curing"],
        "fen-affinamento-vino": ["tec-affinamento","tec-macerazione"],
        "fen-sorbetto": ["tec-mantecatura","tec-abbattimento"],
        "fen-acqua-birra": ["tec-controllo-acqua","tec-mash"],
        "fen-proteolisi": ["tec-curing","tec-affinamento"],
        "fen-trasferimento-calore": ["tec-roner-sottovuoto","tec-arrostitura"],
        "fen-acidita-volatile": ["tec-fermentazione-controllata"],
        "fen-frittura-lievitati": ["tec-frittura"],
    }
    conn = _get_conn()
    try:
        cur = conn.cursor()
        creati=[]
        for tid,(nome,disc,scheda) in NUOVE.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(tid,))
            if not cur.fetchone():
                cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                    (tid,"Tecnica",nome,disc,_json.dumps({"scheda":scheda},ensure_ascii=False)))
                creati.append(tid)
        collegati=[]; saltati=[]
        for fen,tecs in MAPPA.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(fen,))
            if not cur.fetchone(): saltati.append(f"{fen}(no fen)"); continue
            for tec in tecs:
                cur.execute("SELECT id FROM nodes WHERE id=%s",(tec,))
                if not cur.fetchone(): saltati.append(f"{tec}(no tec)"); continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='realizzato_da' AND to_id=%s",(fen,tec))
                if cur.fetchone(): continue
                cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                    (fen,tec,"realizzato_da",_json.dumps({},ensure_ascii=False)))
                collegati.append(f"{fen}->{tec}")
        conn.commit()
        return jsonify({"ok":True,"tecniche_create":creati,"collegati":len(collegati),"dettaglio":collegati,"saltati":saltati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/collega-fenomeni-ricette")
def admin_collega_fenomeni_ricette():
    """Completa PRODOTTO: collega ogni fenomeno alle RICETTE che lo usano (si_manifesta_in).
    Usa il campo 'fenomeni' gia presente in ogni ricetta - relazione inversa."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # collega i fenomeni orfani ai PRODOTTI reali del grafo (nodi prod-*/fis_*) per keyword
    MAPPA = {
        "fen-collagene-brasato": ["fis_beef_raw"], "fen-riposo-carne": ["fis_beef_raw"],
        "fen-rosolatura": ["fis_beef_raw","fis_chicken_breast"], "fen-soffritto": ["fis_beef_raw"],
        "fen-uova-coagulazione": ["fis_egg_white","fis_egg_yolk"], "fen-emulsione-salse": ["fis_egg_yolk"],
        "fen-emulsione-bar": ["fis_egg_white"], "fen-chiarificazione-latte": ["fis_milk_whole"],
        "fen-verdure-verdi": ["fis_apple"], "fen-frittura": ["fis_lard"],
        "fen-pasta-acqua": ["fis_wheat_flour"], "fen-gelatinizzazione-salse": ["fis_wheat_flour"],
        "fen-zuccheri-impasto": ["fis_bread_baked","prod-brioche-viennoiserie"],
        "fen-latte-impasto": ["prod-bao","prod-brioche-viennoiserie"],
        "fen-tangzhong-yudane": ["prod-bao"], "fen-levain-pate-fermentee": ["fis_sourdough_starter","prod-altamura"],
        "fen-cristalli-ghiaccio": ["fis_gelato_base","prod-gelato-cristalli"],
        "fen-zuccheri-pac": ["fis_gelato_base","fis_sorbet_base"], "fen-grassi-stabilizzanti": ["fis_gelato_base"],
        "fen-equilibrio-cocktail": ["prod-aperol-spritz"], "fen-shakerare-mescolare": ["prod-aperol-spritz"],
        "fen-ghiaccio": ["prod-aperol-spritz"], "fen-amaro-bitter": ["prod-aperol-spritz"],
        "fen-infusioni": ["fis_honey"], "fen-fermentazione-alcolica": ["prod_birra","prod-birra-ipa"],
        "fen-luppolo": ["prod-birra-ipa"], "fen-tannini-vino": ["prod_birra"],
        "fen-macinatura-caffe": ["fis_honey"],
    }
    conn = _get_conn()
    try:
        cur = conn.cursor()
        collegati, saltati = [], []
        for fid, prods in MAPPA.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(fid,))
            if not cur.fetchone(): saltati.append(f"{fid}(no fen)"); continue
            for pid in prods:
                cur.execute("SELECT id, name FROM nodes WHERE id=%s",(pid,))
                pr = cur.fetchone()
                if not pr: saltati.append(f"{pid}(no prod)"); continue
                pnome = pr[1] if not hasattr(pr,"keys") else pr["name"]
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='si_manifesta_in' AND to_id=%s",(fid,pid))
                if cur.fetchone(): continue
                cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                    (fid,pid,"si_manifesta_in",_json.dumps({"nome":pnome or pid},ensure_ascii=False)))
                collegati.append(f"{fid}->{pid}")
        conn.commit()
        return jsonify({"ok":True,"collegamenti_creati":len(collegati),"dettaglio":collegati,"saltati":saltati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/crea-strumenti")
def admin_crea_strumenti():
    """Crea i nodi-Strumento (attrezzature di trasformazione) con scienza/parametri/errori,
    collegati alle tecniche che abilitano (abilita) e usati come attrezzatura moderna del mestiere."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # id -> (nome, disciplina, scheda, parametri, errore_tipico, [tecniche che abilita])
    STRUMENTI = {
        "strum-roner": ("Roner / termocircolatore","cucina",
            "Il roner (termocircolatore a immersione) mantiene un bagno d'acqua a temperatura esatta e costante per la cottura sottovuoto. La precisione al grado permette di colpire la soglia di denaturazione voluta senza superarla: il cuore raggiunge esattamente la stessa T della superficie. E' il controllo del principio di denaturazione portato al grado.",
            "Uovo 63C - pesce 50-55C - manzo medio 56-58C - pollo 62-65C - maiale 60-62C - costine 70-75C per 24-36h - verdure 85C. Nei bar per infusioni: 55-71C per 1-3h.",
            "Cottura non uniforme o sacchetto che galleggia: se il sacchetto non e ben sottovuoto l'aria fa da isolante e la parte emersa non cuoce. Sigillare bene, tenere immerso, acqua in circolo.",
            ["tec-roner-sottovuoto","tec-sous-vide-tecnica"]),
        "strum-sottovuoto": ("Macchina sottovuoto (camera)","cucina",
            "La macchina sottovuoto toglie l'aria dal sacchetto (o dal contenitore) prima della cottura o della conservazione. Meno aria = miglior trasferimento di calore nel roner, niente ossidazione, marinature piu veloci (la depressione apre le fibre), conservazione piu lunga. La versione a campana fa il vuoto anche sui liquidi.",
            "Vuoto tipico 99% (camera) - marinatura sottovuoto minuti invece di ore - conservazione 3-5x piu lunga.",
            "Liquidi che bollono in camera: sotto vuoto spinto l'acqua evapora a temperatura ambiente. Fermare il vuoto al punto giusto o raffreddare prima di sigillare i liquidi.",
            ["tec-roner-sottovuoto","tec-marinatura"]),
        "strum-abbattitore": ("Abbattitore di temperatura","gelateria",
            "L'abbattitore porta il cuore del prodotto da +70C a +3C (abbattimento positivo) o a -18C (surgelazione) in tempi rapidissimi. Attraversa in fretta la zona di pericolo microbico e - nel gelato e nei surgelati - forma cristalli di ghiaccio PICCOLI (congelamento rapido) invece che grossi: e la differenza tra un liscio e un ruvido.",
            "Abbattimento positivo +70->+3C in <90 min - surgelazione -18C al cuore - abbattere prima di conservare.",
            "Cristalli grossi da raffreddamento lento: se il prodotto raffredda piano (freezer domestico) i cristalli crescono e il gelato diventa sabbioso. L'abbattitore rapido li tiene piccoli.",
            ["tec-abbattimento","tec-mantecatura","tec-pastorizzazione-gelato"]),
        "strum-sifone": ("Sifone (whipping siphon)","cucina",
            "Il sifone carica un liquido con cartucce di N2O (per spume/panna) o CO2 (per gassate): il gas si scioglie sotto pressione e in uscita espande la preparazione in schiuma leggera. Con addensanti o grassi si fanno espume, arie, mousse; con N2O si accelerano anche le infusioni (pressione-rilascio).",
            "1-2 cariche N2O per 0.5L - riposo in frigo prima dell'uso - infusione rapida: carica, agita, sgasa.",
            "Spuma liquida o che non tiene: manca il corpo (grasso o addensante) o troppo poche cariche. Serve una base con abbastanza materia per intrappolare il gas.",
            ["tec-sifone-spuma"]),
        "strum-rotovapor": ("Rotavapor (evaporatore rotante)","bar",
            "Il rotavapor distilla sotto vuoto a bassa temperatura: il vuoto abbassa il punto di ebollizione (l'acqua bolle a 30-40C invece di 100C), cosi si estraggono e concentrano aromi delicati senza cuocerli. Per distillati aromatici, essenze, riduzioni cristalline che a caldo si degraderebbero.",
            "Vuoto ~50-150 mbar - bagno 40-50C - rotazione costante del pallone - aromi volatili preservati.",
            "Aromi cotti o persi: temperatura del bagno troppo alta o vuoto insufficiente cuociono l'aroma. Abbassare la T e spingere il vuoto per distillare a freddo.",
            ["tec-rotovapor"]),
        "strum-disidratatore": ("Essiccatore / disidratatore","cucina",
            "L'essiccatore rimuove acqua a bassa temperatura con aria ventilata: concentra gli aromi e abbassa l'attivita dell'acqua (Aw) sotto le soglie di crescita microbica, rendendo il prodotto stabile. Per chips, polveri aromatiche, frutta secca, croccantezze, guarnizioni.",
            "40-60C per ore - Aw target <0.6 (muffe) e <0.85 (batteri) per stabilita - aria in circolo.",
            "Prodotto che ammuffisce: essiccazione incompleta, Aw ancora alta. Prolungare finche il prodotto e davvero secco e stabile.",
            ["tec-disidratazione"]),
        "strum-pacojet": ("Pacojet","gelateria",
            "Il Pacojet micronizza un blocco surgelato in una crema finissima senza scongelarlo: lame ad alta velocita raschiano strati sottilissimi, creando texture ultra-lisce (gelati, sorbetti, mousse, farce) al momento, porzione per porzione. Lavora sul principio dei cristalli piccoli: micronizza invece di mantecare.",
            "Blocco a -18/-20C - micronizzazione al momento - texture liscia porzione singola.",
            "Texture granulosa: blocco non abbastanza freddo o non compatto. Congelare bene e pieno prima di pacossare.",
            ["tec-abbattimento","tec-mantecatura"]),
    }
    conn = _get_conn()
    try:
        cur = conn.cursor(); creati=[]; collegati=[]
        for sid,(nome,disc,scheda,parametri,errore,tecs) in STRUMENTI.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(sid,))
            data={"scheda":scheda,"parametri":parametri,"errore_tipico":errore,"tipo":"attrezzatura"}
            if not cur.fetchone():
                cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                    (sid,"Strumento",nome,disc,_json.dumps(data,ensure_ascii=False)))
                creati.append(sid)
            else:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(_json.dumps(data,ensure_ascii=False),sid))
            for tec in tecs:
                cur.execute("SELECT id FROM nodes WHERE id=%s",(tec,))
                if not cur.fetchone(): continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='abilita' AND to_id=%s",(sid,tec))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        (sid,tec,"abilita",_json.dumps({},ensure_ascii=False)))
                    collegati.append(f"{sid}->{tec}")
        conn.commit()
        return jsonify({"ok":True,"strumenti_creati":creati,"collegamenti":collegati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/ripara-accenti")
def admin_ripara_accenti():
    """Ripara gli accenti nei testi del grafo (nodi scritti a mano con UTF-8 tolto).
    Applica correzioni sicure basate su parole intere, non tocca i testi gia corretti."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json, re as _re
    # correzioni parola-intera: (regex parola senza accento) -> con accento
    FIX = [
        (r"\bperche\b","perché"), (r"\bpiu\b","più"), (r"\bcosi\b","così"),
        (r"\bgia\b","già"), (r"\bpuo\b","può"), (r"\bpero\b","però"),
        (r"\bcitta\b","città"), (r"\bqualita\b","qualità"), (r"\bquantita\b","quantità"),
        (r"\battivita\b","attività"), (r"\bumidita\b","umidità"), (r"\bacidita\b","acidità"),
        (r"\bdensita\b","densità"), (r"\bviscosita\b","viscosità"), (r"\bstabilita\b","stabilità"),
        (r"\bmeta\b","metà"), (r"\bpieta\b","pietà"), (r"\bfinche\b","finché"),
        (r"\bpoiche\b","poiché"), (r"\baffinche\b","affinché"), (r"\bpercio\b","perciò"),
        (r"\bcioe\b","cioè"), (r"\bcaffe\b","caffè"), (r"\bte\b","tè"),
        (r"\bpapa\b","papà" ), (r"\bpurche\b","purché"), (r"\bne\b(?= )","né"),
        (r"\bproprieta\b","proprietà"), (r"\bvarieta\b","varietà"), (r"\bnovita\b","novità"),
        (r"\bsocieta\b","società"), (r"\bpossibilita\b","possibilità"), (r"\brealta\b","realtà"),
        (r"\bcapacita\b","capacità"), (r"\bsalinita\b","salinità"), (r"\bfermenta\b","fermenta"),
    ]
    # NB: "e" isolato -> "è" e' pericoloso (congiunzione). Lo gestiamo solo in pattern sicuri:
    # " si e " -> " si è ", " non e " -> " non è ", "che e " -> "che è ", "l'aspetto e "
    FIX_E = [
        (r"\bsi e\b","si è"), (r"\bnon e\b","non è"), (r"\bche e\b","che è"),
        (r"\bcome e\b","come è"), (r"\bquando e\b","quando è"), (r"\bse e\b","se è"),
        (r"\bqui e\b","qui è"), (r"\bgia e\b","già è"),
    ]
    def ripara(t):
        if not isinstance(t,str) or not t: return t, False
        orig = t
        for pat,rep in FIX + FIX_E:
            t = _re.sub(pat, rep, t)
        return t, (t != orig)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE data IS NOT NULL")
        rows = cur.fetchall()
        toccati = 0
        for row in rows:
            nid = row[0] if not hasattr(row,"keys") else row["id"]
            raw = row[1] if not hasattr(row,"keys") else row["data"]
            d = raw if isinstance(raw,dict) else (_json.loads(raw) if raw else {})
            if not isinstance(d,dict): continue
            cambiato = False
            for campo in ["scheda","scheda_it","causa","parametri","errore_tipico","nota"]:
                if campo in d and isinstance(d[campo],str):
                    nuovo, ch = ripara(d[campo])
                    if ch: d[campo]=nuovo; cambiato=True
            if cambiato:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(_json.dumps(d,ensure_ascii=False),nid))
                toccati+=1
        # anche i sintomi negli edge fallisce_come
        cur.execute("SELECT from_id,to_id,data FROM edges WHERE relation='fallisce_come' AND data IS NOT NULL")
        edges = cur.fetchall()
        edge_toccati=0
        for e in edges:
            fr=e[0] if not hasattr(e,"keys") else e["from_id"]
            to=e[1] if not hasattr(e,"keys") else e["to_id"]
            raw=e[2] if not hasattr(e,"keys") else e["data"]
            d = raw if isinstance(raw,dict) else (_json.loads(raw) if raw else {})
            if isinstance(d,dict) and "sintomo" in d and isinstance(d["sintomo"],str):
                nuovo,ch=ripara(d["sintomo"])
                if ch:
                    d["sintomo"]=nuovo
                    cur.execute("UPDATE edges SET data=%s WHERE from_id=%s AND to_id=%s AND relation='fallisce_come'",
                        (_json.dumps(d,ensure_ascii=False),fr,to))
                    edge_toccati+=1
        conn.commit()
        return jsonify({"ok":True,"nodi_riparati":toccati,"edge_riparati":edge_toccati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/coeff-farine")
def admin_coeff_farine():
    """Arricchisce i nodi-farina con i coefficienti di panificazione: W (forza), P/L (tenacita/estensibilita),
    proteine %, uso consigliato. Come i coefficienti POD/PAC per gli zuccheri."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # id_nodo -> (W, P/L, proteine%, uso). Dati verificati.
    FARINE = {
        "ing-farina-00-di-grano-tenero": ("90-180","0.4-0.5","9-11%","Farina debole. Frolle, biscotti, besciamella, prodotti che NON devono sviluppare glutine. Lievitazioni brevi."),
        "ing-farina-0": ("180-260","0.5-0.6","11-12.5%","Media forza. Pane comune, pizza a lievitazione media (8-24h), focaccia. Il compromesso piu versatile."),
        "ing-farina-1": ("200-280","0.55","12-13%","Semi-integrale di media-alta forza. Pane rustico, pizza, impasti con lunga maturazione. Piu fibra, piu sapore."),
        "ing-farina-2": ("170-240","0.5","11.5-12.5%","Semi-integrale. Pane casareccio, impasti saporiti. Assorbe piu acqua dell'00."),
        "fis_wheat_flour": ("180-260","0.5-0.6","11-12.5%","Farina 00 media. Uso generale panificazione, pizza napoletana (W 220-260, 8-24h)."),
        "ing-farina-integrale-di-grano-tenero": ("150-220","0.6","12-14%","Integrale: tutto il chicco. Assorbe molta acqua, la crusca taglia il glutine (impasto meno estensibile). Pane integrale, spesso tagliata con farina forte."),
        "ing-farina-di-semola-rimacinata": ("200-280","0.6-0.7","12-13.5%","Grano DURO rimacinato. Pane di Altamura, pane pugliese, alcune paste. Colore giallo, glutine tenace."),
        "ing-farina-di-semola-integrale": ("180-240","0.65","13-15%","Semola integrale di grano duro. Pane rustico del sud, alta assorbenza."),
    }
    # tabella di riferimento W -> uso (per il calcolatore)
    TABELLA_W = [
        {"range":"90-170","forza":"debole","uso":"frolle, biscotti, grissini, torte","idratazione":"50-55%","lievitazione":"corta (2-4h)"},
        {"range":"180-260","forza":"media","uso":"pane comune, pizza, focaccia","idratazione":"60-70%","lievitazione":"media (8-24h)"},
        {"range":"280-350","forza":"forte","uso":"baguette, pane a lunga lievitazione, panettone base","idratazione":"70-80%","lievitazione":"lunga (24-48h)"},
        {"range":"350-450","forza":"molto forte (manitoba)","uso":"grandi lievitati (panettone, pandoro, colomba), rinforzo di farine deboli","idratazione":"75-90%","lievitazione":"molto lunga (48-72h)"},
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor(); fatti=[]
        for nid,(w,pl,prot,uso) in FARINE.items():
            cur.execute("SELECT id, data FROM nodes WHERE id=%s",(nid,))
            row = cur.fetchone()
            if not row: fatti.append(f"{nid}: ASSENTE"); continue
            raw = row[1] if not hasattr(row,"keys") else row["data"]
            d = raw if isinstance(raw,dict) else (_json.loads(raw) if raw else {})
            if not isinstance(d,dict): d={}
            d["W"]=w; d["P_L"]=pl; d["proteine"]=prot; d["uso_panificazione"]=uso
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(_json.dumps(d,ensure_ascii=False),nid))
            fatti.append(f"{nid}: W={w} P/L={pl} prot={prot}")
        # salvo la tabella W come nodo di riferimento
        cur.execute("SELECT id FROM nodes WHERE id=%s",("tab-forza-farine",))
        tdata = {"scheda":"Tabella di riferimento: quale forza (W) per quale uso in panificazione.","tabella":TABELLA_W}
        if not cur.fetchone():
            cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                ("tab-forza-farine","Calcolo","Tabella forza farine (W)","panificazione",_json.dumps(tdata,ensure_ascii=False)))
        else:
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(_json.dumps(tdata,ensure_ascii=False),"tab-forza-farine"))
        conn.commit()
        return jsonify({"ok":True,"farine_arricchite":fatti,"tabella_W_creata":True})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/tabella-temperature")
def admin_tabella_temperature():
    """Crea la tabella delle temperature-cuore: quale grado per quale risultato, per proteina.
    Il cuore della cottura di precisione (roner/sous-vide). Dati verificati."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    TEMPERATURE = {
        "manzo": [
            {"punto":"al sangue (rare)","temp":"50-52°C","note":"rosso, succoso, morbido"},
            {"punto":"medio (medium-rare)","temp":"54-56°C","note":"il punto classico della bistecca"},
            {"punto":"a puntino (medium)","temp":"58-60°C","note":"rosa, ancora succoso"},
            {"punto":"ben cotto","temp":"68-71°C","note":"grigio, piu asciutto"},
            {"punto":"brasato (taglio duro)","temp":"70-75°C x 24-36h","note":"collagene -> gelatina, morbido"},
        ],
        "pollo": [
            {"punto":"petto succoso","temp":"62-64°C","note":"sicuro e ancora umido (contro i 74°C tradizionali che asciugano)"},
            {"punto":"coscia","temp":"70-74°C","note":"il tessuto connettivo si scioglie meglio piu in alto"},
        ],
        "maiale": [
            {"punto":"lombo rosa","temp":"58-60°C","note":"succoso, leggermente rosa"},
            {"punto":"a puntino","temp":"62-65°C","note":"il compromesso sicurezza/succosita"},
        ],
        "pesce": [
            {"punto":"salmone morbido","temp":"45-50°C","note":"traslucido, setoso"},
            {"punto":"pesce a scaglie","temp":"52-55°C","note":"si sfalda, ancora umido"},
            {"punto":"tonno scottato","temp":"45-48°C","note":"cuore crudo"},
        ],
        "uovo": [
            {"punto":"uovo 63 (onsen)","temp":"63°C x 45min","note":"albume cremoso, tuorlo vellutato"},
            {"punto":"tuorlo denso","temp":"65°C","note":"tuorlo che cola denso"},
            {"punto":"sodo cremoso","temp":"68-70°C","note":"entrambi sodi ma non gessosi"},
        ],
        "verdure": [
            {"punto":"croccanti","temp":"83-85°C","note":"cottura sotto la gelatinizzazione totale, mantengono struttura"},
            {"punto":"morbide","temp":"85-90°C","note":"amido gelatinizzato, tenere"},
        ],
    }
    conn = _get_conn()
    try:
        cur = conn.cursor()
        data = {"scheda":"Temperature-cuore per la cottura di precisione (roner/sous-vide): quale grado per quale risultato. La temperatura governa la denaturazione proteica - colpisci la soglia voluta senza superarla.","tabella":TEMPERATURE}
        cur.execute("SELECT id FROM nodes WHERE id=%s",("tab-temperature-cuore",))
        if not cur.fetchone():
            cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                ("tab-temperature-cuore","Calcolo","Temperature-cuore (sous-vide)","cucina",_json.dumps(data,ensure_ascii=False)))
            azione="creata"
        else:
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(_json.dumps(data,ensure_ascii=False),"tab-temperature-cuore"))
            azione="aggiornata"
        # la collego al fenomeno denaturazione e allo strumento roner
        for target,rel in [("princ-denaturazione","spiega"),("strum-roner","abilita")]:
            cur.execute("SELECT id FROM nodes WHERE id=%s",(target,))
            if cur.fetchone():
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s",("tab-temperature-cuore",target))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        ("tab-temperature-cuore",target,rel,_json.dumps({},ensure_ascii=False)))
        conn.commit()
        return jsonify({"ok":True,"tabella":azione,"proteine":list(TEMPERATURE.keys())})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/audit-ricette")
def admin_audit_ricette():
    """Audit QUALITA delle ricette: misura se ogni ricetta rispetta i criteri professionali.
    Una ricetta 'legge' (non accozzaglia) ha: procedimento vero, numeri ancorati ai passaggi,
    fenomeni collegati, numeri-bersaglio, punto critico, applicazioni, metadati completi."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id,nome,disciplina,ingredienti,fenomeni,numeri,punto_critico,
            procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,twist_di FROM ricette ORDER BY disciplina,nome""")
        rows = cur.fetchall()
        def P(v):
            if v is None: return None
            if isinstance(v,(list,dict)): return v
            try: return _json.loads(v)
            except: return v
        report=[]
        conteggi={"procedimento":0,"numeri_ancorati":0,"fenomeni":0,"numeri":0,"punto_critico":0,"applicazioni":0,"metadati":0,"legge":0,"riempitivo":0}
        for row in rows:
            g=lambda i: (row[i] if not hasattr(row,"keys") else row[list(row.keys())[i]])
            rid,nome,disc=g(0),g(1),g(2)
            ingr,fen,num,pc=P(g(3)),P(g(4)),P(g(5)),g(6)
            proc,appl=P(g(7)),P(g(8))
            tprep,tcott,diff,porz,twist=g(9),g(10),g(11),g(12),g(13)
            proc=proc or []; appl=appl or []; fen=fen or []; num=num or {}
            # criteri
            c_proc = isinstance(proc,list) and len(proc)>=4
            c_anc = isinstance(proc,list) and sum(1 for p in proc if isinstance(p,dict) and p.get("numero_chiave") and str(p.get("numero_chiave")).lower() not in ("","null","none"))>=2
            c_fen = isinstance(fen,list) and len(fen)>=1
            c_num = isinstance(num,dict) and len(num)>=1
            c_pc = bool(pc and len(str(pc))>10)
            c_appl = isinstance(appl,list) and len(appl)>=1
            c_meta = bool(tprep is not None and diff and porz)
            for k,v in [("procedimento",c_proc),("numeri_ancorati",c_anc),("fenomeni",c_fen),("numeri",c_num),("punto_critico",c_pc),("applicazioni",c_appl),("metadati",c_meta)]:
                if v: conteggi[k]+=1
            score=sum([c_proc,c_anc,c_fen,c_num,c_pc,c_appl,c_meta])
            if score>=6: conteggi["legge"]+=1
            if score<=3: conteggi["riempitivo"]+=1
            manca=[k for k,v in [("procedimento",c_proc),("numeri_ancorati",c_anc),("fenomeni",c_fen),("numeri",c_num),("punto_critico",c_pc),("applicazioni",c_appl),("metadati",c_meta)] if not v]
            report.append({"id":rid,"nome":nome,"disc":disc,"score":score,"manca":manca,"twist":bool(twist)})
        report.sort(key=lambda x:x["score"])
        return jsonify({"totale_ricette":len(rows),"conteggi":conteggi,
            "peggiori":[r for r in report if r["score"]<6][:25],
            "nota":"score 7 = ricetta 'legge' (criteri pro completi); <=3 = riempitivo da curare"})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/warmup-cache")
def admin_warmup_cache():
    """Scalda la cache AI di /nodo per un batch di nodi, così gli utenti non beccano mai
    la prima apertura lenta (5s). Chiama internamente la logica di nodo. Param: limite, skip, tipo."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    from db import carica_grafo
    from ai import cerca_contesto, costruisci_prompt, chiedi_mistral
    limite = int(request.args.get("limite","10"))
    skip = int(request.args.get("skip","0"))
    tipo = request.args.get("tipo","Fenomeno")
    lang = request.args.get("lang","it")
    cache_key = f"risposta_cache_{lang}"
    db = carica_grafo()
    try:
        nodi = db.execute("SELECT id, name, data FROM nodes WHERE type=? ORDER BY id", (tipo,)).fetchall()
        scaldati, gia, saltati, n, visti = [], 0, 0, 0, 0
        for nd in nodi:
            if n>=limite: break
            visti+=1
            if visti<=skip: continue
            nid = nd["id"]; nome = nd["name"]
            raw = nd["data"]
            d = raw if isinstance(raw,dict) else (_json.loads(raw) if raw else {})
            if isinstance(d,dict) and d.get(cache_key):
                gia+=1; continue
            contesto = cerca_contesto(db, (nome or "").split()[0])
            if not contesto or not contesto.get("fenomeni"):
                saltati+=1; n+=1; continue
            prompt = costruisci_prompt(f"Spiegami {nome} e i fenomeni che lo governano.", contesto, lang=lang)
            risposta = chiedi_mistral(prompt)
            if risposta:
                if not isinstance(d,dict): d={}
                d[cache_key]=risposta
                db.execute("UPDATE nodes SET data=? WHERE id=?", (_json.dumps(d,ensure_ascii=False), nid))
                scaldati.append(nid)
            n+=1
        # quanti restano senza cache
        tutti = db.execute("SELECT data FROM nodes WHERE type=?", (tipo,)).fetchall()
        restano=0
        for t in tutti:
            dd = t["data"] if isinstance(t["data"],dict) else (_json.loads(t["data"]) if t["data"] else {})
            if not (isinstance(dd,dict) and dd.get(cache_key)): restano+=1
        return jsonify({"ok":True,"scaldati":scaldati,"gia_caldi":gia,"saltati":saltati,"restano_freddi":restano})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500

@bp.route("/admin/trova-doppioni")
def admin_trova_doppioni():
    """Diagnostica: trova nodi potenzialmente duplicati (stesso tipo, nomi simili) per il consolidamento."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json, re as _re
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, type, domain FROM nodes WHERE type IN ('Tecnica','Fenomeno','Strumento','principio','Errore') ORDER BY type, name")
        nodi = cur.fetchall()
        def norm(s):
            s = (s or "").lower()
            s = _re.sub(r'[^a-z0-9 ]','',s)
            # tolgo parole comuni per confrontare il concetto
            for w in ["tecnica","la","il","di","del","della","e","a","con","per","dei","le","i"]:
                s = _re.sub(r'\b'+w+r'\b','',s)
            return _re.sub(r'\s+',' ',s).strip()
        # raggruppo per (tipo, nome normalizzato simile)
        by_type = {}
        for n in nodi:
            nid = n[0] if not hasattr(n,"keys") else n["id"]
            nome = n[1] if not hasattr(n,"keys") else n["name"]
            tipo = n[2] if not hasattr(n,"keys") else n["type"]
            by_type.setdefault(tipo,[]).append((nid,nome,norm(nome)))
        sospetti = []
        for tipo, items in by_type.items():
            for i in range(len(items)):
                for j in range(i+1,len(items)):
                    id1,n1,k1 = items[i]; id2,n2,k2 = items[j]
                    if not k1 or not k2: continue
                    # doppione se: nome normalizzato uguale, o uno contiene l'altro, o keyword condivisa forte
                    w1=set(k1.split()); w2=set(k2.split())
                    common = w1 & w2
                    if k1==k2 or (common and (len(common)>=min(len(w1),len(w2)) or (len(common)>=2))):
                        sospetti.append({"tipo":tipo,"a":id1,"nome_a":n1,"b":id2,"nome_b":n2,"comune":list(common)})
        return jsonify({"totale_sospetti":len(sospetti),"doppioni":sospetti})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/consolida-doppioni")
def admin_consolida_doppioni():
    """Consolida i doppioni VERI (lista curata a mano): sposta i collegamenti del nodo doppione
    sul nodo BUONO, poi rimuove il doppione. Coppie (buono, doppione)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    # (nodo_BUONO_da_tenere, nodo_DOPPIONE_da_rimuovere) - lista CURATA, non automatica
    COPPIE = [
        # Errori
        ("err-brasato-stopposo","err-brasato-stopposo-per-temperatura-troppo-"),
        ("err-brodo-torbido","err-brodo-torbido-per-bollore-eccessivo"),
        ("err-catena-freddo-rotta","err-interruzione-catena"),
        ("err-cioccolato-fiorito","err-cioccolato-grigio"),
        ("err-crosta-pallida","err-crosta-pallida-molle"),
        ("err-crosta-pallida","err-crosta-pallida-p"),
        ("err-gelato-cristalli","err-gelato-granuloso-nuovo"),
        ("err-panna-burrosa","err-panna-burro"),
        ("err-alveoli-no","err-alveolatura-chiusa"),
        ("err-carne-asciutta","err-carne-stopposa"),
        ("err-carne-asciutta","err-carne-secca-taglio"),
        ("err-cioccolato-opaco","err-cioccolato-non-lucido"),
        ("err-drink-annacquato","err-ghiaccio-annacqua"),
        ("err-gelato-molle","err-gelato-duro"),
        # Fenomeni
        ("fen-ghiaccio","fen-ghiaccio-cocktail"),
        ("fen-overrun","fen-montaggio"),
        ("fen-overrun","fen-overrun-controllo"),
        ("fen-grassi-stabilizzanti","fen-stabilizzanti-gelato"),
        ("fen-acidita-volatile","fen-acidita"),
        ("fen-cristallizzazione","fen-cristallizzazione-ghiaccio"),
        ("fen-emulsione-salse","fen-emulsione-bar"),
        # Tecniche (le tre sous-vide -> una)
        ("tec-sous-vide-tecnica","tec-sous-vide-cuore"),
        ("tec-sous-vide-tecnica","tec-roner-sottovuoto"),
        ("tec-autolisi","tec-autolisi-riposo"),
        ("tec-pieghe","tec-pieghe-forza"),
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        fusi, saltati = [], []
        for buono, doppione in COPPIE:
            cur.execute("SELECT id FROM nodes WHERE id=%s",(buono,))
            if not cur.fetchone(): saltati.append(f"{buono}(BUONO assente)"); continue
            cur.execute("SELECT id FROM nodes WHERE id=%s",(doppione,))
            if not cur.fetchone(): saltati.append(f"{doppione}(dop assente)"); continue
            # sposto gli edge in USCITA dal doppione verso il buono (evitando duplicati e auto-loop)
            cur.execute("SELECT to_id, relation, data FROM edges WHERE from_id=%s",(doppione,))
            for e in cur.fetchall():
                to_id = e[0] if not hasattr(e,"keys") else e["to_id"]
                rel = e[1] if not hasattr(e,"keys") else e["relation"]
                dat = e[2] if not hasattr(e,"keys") else e["data"]
                if to_id==buono: continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation=%s",(buono,to_id,rel))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        (buono,to_id,rel,dat if isinstance(dat,str) else _json.dumps(dat or {},ensure_ascii=False)))
            # sposto gli edge in ENTRATA verso il doppione -> verso il buono
            cur.execute("SELECT from_id, relation, data FROM edges WHERE to_id=%s",(doppione,))
            for e in cur.fetchall():
                from_id = e[0] if not hasattr(e,"keys") else e["from_id"]
                rel = e[1] if not hasattr(e,"keys") else e["relation"]
                dat = e[2] if not hasattr(e,"keys") else e["data"]
                if from_id==buono: continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation=%s",(from_id,buono,rel))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        (from_id,buono,rel,dat if isinstance(dat,str) else _json.dumps(dat or {},ensure_ascii=False)))
            # rimuovo tutti gli edge del doppione e il nodo doppione
            cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s",(doppione,doppione))
            cur.execute("DELETE FROM nodes WHERE id=%s",(doppione,))
            fusi.append(f"{doppione} -> {buono}")
        conn.commit()
        return jsonify({"ok":True,"fusi":fusi,"saltati":saltati})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/estrai-attrezzature")
def admin_estrai_attrezzature():
    """Estrae gli strumenti GIA' NOMINATI nel campo 'strumento' di fenomeni/tecniche e li rende
    NODI Strumento veri, collegati ai nodi che li citano. NON inventa: parte dai dati reali del grafo.
    Normalizza le varianti (termometro a sonda/IR/integrato -> Termometro). ?dry=1 per anteprima."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json, re as _re, unicodedata
    from db import carica_grafo
    dry = request.args.get("dry", "0") != "0"
    db = carica_grafo()
    # mappa di normalizzazione: variante -> nome canonico
    def canonico(s):
        s = s.strip().lower()
        s = _re.sub(r"\(.*?\)", "", s).strip()  # togli parentesi
        if not s: return None
        if "termometro" in s: return "Termometro"
        if "phmetro" in s or "ph-metro" in s or "ph metro" in s or "phmetr" in s: return "pH-metro"
        if "rifrattometro" in s: return "Rifrattometro"
        if "bilancia" in s: return "Bilancia di precisione"
        if "alcolimetro" in s or "idrometro" in s: return "Alcolimetro"
        if "awmetro" in s or "aw metro" in s: return "Awmetro"
        if "manometro" in s: return "Manometro"
        if "timer" in s: return "Timer"
        if "torbidimetro" in s: return "Torbidimetro"
        if "alveografo" in s: return "Alveografo Chopin"
        if "acidita titolabile" in s or "acidità titolabile" in s: return "Kit acidita titolabile"
        # scarta metriche non-strumento (IBU, PAC, EBC, DE, analisi...)
        if any(x in s for x in ["ibu","pac","ebc"," de ","analisi","test ","calcolat","sensoriale","congeners","malico","fenolica","zuccheri"]):
            return None
        return None  # solo strumenti riconosciuti (niente invenzioni)
    try:
        rows = db.execute("SELECT id, name, data, domain FROM nodes WHERE data::text LIKE '%%strumento%%'").fetchall()
        # raccogli strumento->nodi che lo citano
        strum_nodi = {}
        for r in rows:
            data = r["data"] if isinstance(r["data"], dict) else (_json.loads(r["data"]) if r["data"] else {})
            raw = data.get("strumento", "")
            if not raw: continue
            for pezzo in _re.split(r"[·,;/]| e ", raw):
                canon = canonico(pezzo)
                if canon:
                    strum_nodi.setdefault(canon, {"cita": [], "dom": r["domain"]})
                    strum_nodi[canon]["cita"].append(r["id"])
        if dry:
            return jsonify({"strumenti_trovati": len(strum_nodi),
                            "dettaglio": {k: len(v["cita"]) for k, v in strum_nodi.items()}})
        creati = 0; archi = 0
        for nome, info in strum_nodi.items():
            slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
            slug = "str-" + _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:35]
            db.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (?,?,?,?,?) ON CONFLICT (id) DO NOTHING",
                       (slug, "Strumento", nome, info["dom"] or "trasversale", _json.dumps({"nota": "strumento di misura/lavorazione del mestiere"}, ensure_ascii=False)))
            creati += 1
            for nid in info["cita"][:20]:
                try:
                    db.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                               (nid, slug, "misurato_con", "{}"))
                    archi += 1
                except Exception: pass
        return jsonify({"strumenti_creati": creati, "archi_creati": archi,
                        "nota": "estratti dai dati reali del grafo, non inventati. Collegati ai nodi che li citano."})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/admin/genera-storia")
def admin_genera_storia():
    """Crea un nodo Storia per una disciplina: l'evoluzione del mestiere collegata alle tecniche/fenomeni
    che ha prodotto (non Wikipedia: storia CHE SPIEGA il mestiere di oggi). ?disc= obbligatorio.
    Marcata da_rivedere=true (le date/nomi storici vanno verificati da Michele)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json, re as _re
    from db import carica_grafo
    from ai import chiedi_mistral
    disc = request.args.get("disc", "")
    if not disc:
        return jsonify({"errore": "serve ?disc=bar|cucina|panificazione|caffetteria|..."}), 400
    db = carica_grafo()
    try:
        # tecniche della disciplina, per collegare la storia a cosa ha prodotto
        tec = db.execute("SELECT id, name FROM nodes WHERE type='Tecnica' AND domain=?", (disc,)).fetchall()
        tec_str = "; ".join(r["name"] for r in tec[:15])
        righe = [
            "Sei uno storico del mestiere di " + disc + ". Scrivi una STORIA sintetica (400-600 parole) del mestiere di " + disc + ".",
            "REGOLA: SOLO fatti storici REALI (date, nomi, luoghi veri). Se non sei sicuro di una data, NON inventarla: parla in termini generali.",
            "NON deve essere un elenco enciclopedico: deve spiegare COME si e' arrivati alle tecniche di oggi.",
            "Collega la storia alle tecniche attuali del mestiere, per esempio: " + (tec_str if tec_str else "le tecniche fondamentali"),
            "Racconta: origini, svolte chiave (invenzioni, personaggi, epoche), e come hanno prodotto il modo di lavorare di oggi.",
            "Rispondi SOLO con JSON: {\"titolo\":\"Storia di ...\",\"testo\":\"...\",\"svolte\":[\"svolta 1\",\"svolta 2\",\"svolta 3\"]}"
        ]
        prompt = "\n".join(righe)
        out = chiedi_mistral(prompt)
        if not out:
            return jsonify({"errore": "AI non ha risposto"}), 503
        testo = out.strip()
        m = _re.search(r"\{.*\}", testo, _re.DOTALL)
        if m: testo = m.group(0)
        data_ai = _json.loads(testo)
        nodo_data = _json.dumps({
            "scheda": data_ai.get("testo", ""),
            "svolte": data_ai.get("svolte", []),
            "da_rivedere": "true",
            "tipo": "storia"
        }, ensure_ascii=False)
        sid = "storia-" + disc
        titolo = data_ai.get("titolo") or ("Storia di " + disc)
        db.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data, name=EXCLUDED.name",
                   (sid, "Storia", titolo, disc, nodo_data))
        # collega la storia alle tecniche della disciplina
        coll = 0
        for r in tec[:15]:
            try:
                db.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                           (sid, r["id"], "ha_prodotto", "{}"))
                coll += 1
            except Exception: pass
        return jsonify({"storia": titolo, "id": sid, "tecniche_collegate": coll,
                        "svolte": data_ai.get("svolte", []),
                        "nota": "marcata da_rivedere: verifica date/nomi storici prima di pubblicare"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/admin/aggiungi-fenomeni-mancanti")
def admin_aggiungi_fenomeni_mancanti():
    """Aggiunge i fenomeni-cardine mancanti con DATI REALI (non AI): Strecker, inversione zucchero,
    browning enzimatico, capillarità, espansione termica, saponificazione, tissotropia, salting.
    Scritti a mano perché sono scienza precisa."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json
    from db import carica_grafo
    db = carica_grafo()
    FENOMENI = [
        ("fen-strecker", "Reazione di Strecker (aromi della rosolatura)", "cucina", {
            "scheda": "Parte della reazione di Maillard: gli amminoacidi reagiscono con i composti dicarbonilici e si degradano in aldeidi di Strecker, responsabili degli aromi tostati/di rosolatura (malto, pane, carne arrostita, caffe). E' cio' che da' l'AROMA, mentre la Maillard classica da' il COLORE. Avviene sopra i 130-140C.",
            "numeri": "attiva sopra 130-140C · massima resa aromatica 150-180C · richiede amminoacidi liberi + zuccheri riducenti",
            "target": "temperatura superficie 150-180C per aromi di Strecker ottimali",
            "tipo": "chimico", "discipline": ["cucina","panificazione","caffetteria"]}),
        ("fen-inversione-zucchero", "Inversione dello zucchero (saccarosio in glucosio+fruttosio)", "pasticceria", {
            "scheda": "Il saccarosio si scinde in glucosio + fruttosio (zucchero invertito) per idrolisi acida o enzimatica (invertasi). Lo zucchero invertito e' piu' dolce, igroscopico (trattiene umidita'), abbassa il punto di congelamento e previene la cristallizzazione. Base di sciroppi, gelati morbidi, prodotti da forno che restano soffici.",
            "numeri": "inversione con acido citrico 0,1-0,2%% a 110-114C · fruttosio POD 173 (piu dolce del saccarosio 100) · abbassa il punto di congelamento",
            "target": "grado di inversione 50-95%% secondo l'uso (sciroppi, gelato, confetti)",
            "tipo": "chimico", "discipline": ["pasticceria","gelateria"]}),
        ("fen-browning-enzimatico", "Imbrunimento enzimatico (mela, carciofo, avocado)", "cucina", {
            "scheda": "Quando frutta/verdura viene tagliata, l'enzima polifenolossidasi (PPO) reagisce coi polifenoli e l'ossigeno formando melanine brune. Si blocca con: acido (limone, pH sotto 3-4 disattiva la PPO), freddo (rallenta), calore (denatura la PPO sopra 70-80C), o togliendo l'ossigeno (acqua, sottovuoto).",
            "numeri": "PPO inattiva a pH <3-4 · denaturata sopra 70-80C · rallentata sotto 4C",
            "target": "pH <4 o blanching 70-80C per bloccare l'imbrunimento",
            "tipo": "enzimatico", "discipline": ["cucina"]}),
        ("fen-capillarita", "Capillarita (assorbimento nei porosi)", "panificazione", {
            "scheda": "L'acqua risale nei canali stretti (pori del pane, polvere di caffe, zolletta) per tensione superficiale, senza pompa. Governa l'assorbimento dell'acqua nella farina, la bagnatura del caffe (pre-infusione), l'inzuppo dei dolci.",
            "numeri": "risalita inversamente proporzionale al diametro del poro · pre-infusione caffe 5-15 secondi",
            "target": "bagnatura uniforme: pre-infusione 5-15s nel caffe filtro",
            "tipo": "fisico", "discipline": ["panificazione","caffetteria","pasticceria"]}),
        ("fen-espansione-termica", "Espansione termica (spinta in forno, oven spring)", "panificazione", {
            "scheda": "Col calore i gas (CO2, vapore, aria) si espandono e l'impasto cresce di colpo in forno (oven spring) prima che la crosta si fissi. Vale per pane, bigne' (vapore che gonfia), souffle'. Gestita da temperatura del forno e umidita'.",
            "numeri": "oven spring nei primi 5-10 min a 220-250C · il vapore raddoppia il volume del bigne",
            "target": "forno 220-250C con vapore iniziale per massima spinta",
            "tipo": "fisico", "discipline": ["panificazione","pasticceria"]}),
        ("fen-tissotropia", "Tissotropia (fluidi che cambiano con lo sforzo)", "cucina", {
            "scheda": "Alcuni fluidi (ketchup, salse con amido, gel) diventano piu' fluidi quando agitati/sforzati e si ri-addensano a riposo. Governa la scorrevolezza delle salse, la stesura dei gel, il comportamento degli impasti.",
            "numeri": "recupero viscosita' a riposo secondi-minuti secondo l'addensante",
            "target": "viscosita' operativa secondo la salsa (scorre sotto sforzo, tiene a riposo)",
            "tipo": "reologico", "discipline": ["cucina","bar"]}),
    ]
    creati = 0
    try:
        for fid, nome, dom, data in FENOMENI:
            db.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data, name=EXCLUDED.name",
                       (fid, "Fenomeno", nome, dom, _json.dumps(data, ensure_ascii=False)))
            creati += 1
        return jsonify({"fenomeni_aggiunti": creati, "nota": "dati reali scritti a mano, non AI"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/aggiungi-umami")
def admin_aggiungi_umami():
    """Aggiunge il fenomeno UMAMI / esaltazione dei sapori con dati REALI (non AI).
    Numeri veri: sinergia glutammato+inosinato moltiplica l'intensità fino a ~8x.
    Collegato alle discipline dove conta (cucina, bar, fermentati)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json
    from db import carica_grafo
    db = carica_grafo()
    try:
        # nodo fenomeno umami (dati reali, scritti a mano)
        scheda = ("L'umami è il quinto gusto, dato dai glutammati liberi (MSG naturale in parmigiano, "
                  "pomodoro, funghi, alghe kombu) e dai nucleotidi (inosinato nella carne/pesce, "
                  "guanilato nei funghi secchi). La chiave e' la SINERGIA: glutammato + inosinato insieme "
                  "danno un'intensita' umami fino a 7-8 volte superiore alla somma dei singoli. "
                  "E' il motivo scientifico di abbinamenti classici: parmigiano+pomodoro, dashi (kombu+katsuobushi), "
                  "prosciutto+melone. L'esaltazione dei sapori passa anche da sale (abbassa la soglia di percezione), "
                  "acido (bilancia e pulisce), grasso (veicola gli aromi liposolubili) e temperatura di servizio.")
        data = _json.dumps({
            "scheda": scheda,
            "numeri": "sinergia glutammato+inosinato fino a 8x · glutammato libero: parmigiano 1200mg/100g, "
                      "pomodoro maturo 140-250mg, kombu 1400-3200mg · soglia umami MSG ~0,012%",
            "target": "rapporto ottimale glutammato:inosinato circa 1:1 per massima sinergia",
            "tipo": "sensoriale-chimico",
            "discipline": ["cucina", "bar", "trasversale"]
        }, ensure_ascii=False)
        db.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (?,?,?,?,?) ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data",
                   ("fen-umami", "Fenomeno", "Umami e esaltazione dei sapori (sinergia glutammato-inosinato)", "trasversale", data))
        # archi verso prodotti/discipline dove l'umami si manifesta
        archi = [
            ("fen-umami", "prod-brodo", "si_manifesta_in", '{"target":"dashi: kombu 1% peso acqua a 60C + katsuobushi","causa":"sinergia glutammato(kombu)+inosinato(katsuobushi) = umami esplosivo"}'),
            ("fen-umami", "prod-sour", "si_manifesta_in", '{"target":"umami in cocktail: dash di salsa di soia o brodo","causa":"il glutammato aggiunge rotondita e persistenza al drink"}'),
        ]
        creati = 0
        for a in archi:
            try:
                # verifica che il nodo destinazione esista
                dest = db.execute("SELECT id FROM nodes WHERE id=?", (a[1],)).fetchone()
                if dest:
                    db.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (?,?,?,?) ON CONFLICT DO NOTHING", a)
                    creati += 1
            except Exception:
                pass
        return jsonify({"fenomeno": "fen-umami creato/aggiornato", "archi_creati": creati,
                        "nota": "dati reali scritti a mano (non AI). Numeri verificabili."})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/genera-tecniche")
def admin_genera_tecniche():
    """Arricchisce le tecniche di una disciplina generando quelle FONDAMENTALI mancanti.
    L'AI propone tecniche vere del mestiere (con nota concreta + numeri), salvate come nodi Tecnica
    e collegate ai fenomeni pertinenti. ?disc=cucina obbligatorio. ?n=3 quante per chiamata.
    Stesso formato dei nodi Tecnica esistenti (nota coi numeri operativi)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json, re as _re, unicodedata
    from db import carica_grafo
    from ai import chiedi_mistral
    disc = request.args.get("disc", "")
    n = int(request.args.get("n", "3"))
    if not disc:
        return jsonify({"errore": "serve ?disc=cucina|panificazione|caffetteria|vino|..."}), 400
    db = carica_grafo()
    try:
        # tecniche già presenti (per non duplicare)
        esist = db.execute("SELECT name FROM nodes WHERE type='Tecnica' AND domain=?", (disc,)).fetchall()
        nomi_esist = [r["name"] for r in esist]
        # fenomeni della disciplina (per collegare le tecniche)
        fen = db.execute("SELECT id, name FROM nodes WHERE type='Fenomeno' AND domain=?", (disc,)).fetchall()
        fen_lista = [{"id": r["id"], "nome": r["name"]} for r in fen]
        fen_str = "; ".join(f"{f['id']}={f['nome']}" for f in fen_lista[:20])
        lista_esist = ", ".join(nomi_esist) if nomi_esist else "nessuna"
        righe_prompt = [
            "Sei un consulente tecnico esperto di " + disc + " di ALTO LIVELLO. Elenca " + str(n) + " TECNICHE REALI di " + disc + ".",
            "REGOLA FERREA: SOLO tecniche VERE, riconosciute e usate nel mestiere, col loro nome reale. MAI inventare nomi o tecniche.",
            "Includi le MODERNE e D'AVANGUARDIA realmente esistenti, non solo le basi.",
            "Esempi REALI del livello richiesto (cucina): reverse searing, cottura sous-vide col Roner, oliocottura, confit,",
            "sferificazione, gelificazione con agar/gellan, fermentazione con koji, garum, affumicatura a freddo, frollatura dry-aged,",
            "cottura in crosta di sale, marinatura, brasatura. Per altre discipline usa le tecniche reali equivalenti di quel mestiere.",
            "Se non conosci abbastanza tecniche NUOVE e reali, restituiscine MENO ma vere: meglio poche vere che una inventata.",
            "NON ripetere queste gia presenti: " + lista_esist + ".",
            "Per ognuna: nome reale del mestiere, nota concreta CON NUMERI operativi, fenomeno collegato.",
            "Scegli un fenomeno id da questa lista se pertinente: " + fen_str,
            'Rispondi SOLO con JSON valido: {"tecniche":[{"nome":"...","nota":"nota con numeri","fenomeno_id":"fen-... o null"}]}',
        ]
        prompt = "\n".join(righe_prompt)
        out = chiedi_mistral(prompt)
        if not out:
            return jsonify({"errore": "AI non ha risposto"}), 503
        testo = out.strip()
        m = _re.search(r"\{.*\}", testo, _re.DOTALL)
        if m: testo = m.group(0)
        data = _json.loads(testo)
        tecniche = data.get("tecniche", [])[:n]
        create = []
        for t in tecniche:
            nome = (t.get("nome") or "").strip()
            if not nome or nome in nomi_esist: continue
            slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
            slug = "tec-" + _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:35]
            nota = (t.get("nota") or "").strip()
            db.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (?,?,?,?,?) ON CONFLICT (id) DO NOTHING",
                       (slug, "Tecnica", nome, disc, _json.dumps({"nota": nota}, ensure_ascii=False)))
            # collega al fenomeno se indicato e valido
            fid = t.get("fenomeno_id")
            if fid and any(f["id"] == fid for f in fen_lista):
                db.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                           (fid, slug, "realizzato_da", "{}"))
            create.append({"nome": nome, "id": slug, "collegata_a": fid if fid else None})
        return jsonify({"disciplina": disc, "create": len(create), "dettaglio": create,
                        "gia_presenti": len(nomi_esist),
                        "nota": "ripeti per aggiungerne altre; l'AI evita i duplicati"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/admin/conta-nodi")
def admin_conta_nodi():
    """Conta i nodi per tipo (Fenomeno, Tecnica, Attrezzatura, ecc.) e per disciplina.
    Serve a capire dove il grafo è povero (es. poche tecniche/attrezzature)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    db = carica_grafo()
    try:
        per_tipo = db.execute("SELECT type, COUNT(*) n FROM nodes GROUP BY type ORDER BY n DESC").fetchall()
        tipi = {r["type"]: r["n"] for r in per_tipo}
        # tecniche e attrezzature per disciplina (dal campo domain)
        tec = db.execute("SELECT domain, COUNT(*) n FROM nodes WHERE type='Tecnica' GROUP BY domain").fetchall()
        att = db.execute("SELECT domain, COUNT(*) n FROM nodes WHERE type IN ('Attrezzatura','Attrezzo') GROUP BY domain").fetchall()
        return jsonify({
            "per_tipo": tipi,
            "tecniche_per_disciplina": {r["domain"] or "?": r["n"] for r in tec},
            "attrezzature_per_disciplina": {r["domain"] or "?": r["n"] for r in att},
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/riempi-immagini-ricette")
def admin_riempi_immagini():
    """Riempie le immagini mancanti delle ricette cercando su Pexels (API gratuita).
    Serve PEXELS_API_KEY nell'ambiente. Salva url+autore+fonte con credito.
    ?n=8 quante per chiamata (timeout). ?dry=1 per contare quante ne mancano."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    from immagini import cerca_immagine, credito_immagine
    dry = request.args.get("dry", "0") != "0"
    n = int(request.args.get("n", "8"))
    if not os.environ.get("PEXELS_API_KEY"):
        return jsonify({"errore": "manca PEXELS_API_KEY nell'ambiente",
                        "come": "registrati gratis su pexels.com/api e aggiungi la chiave nelle variabili Railway"}), 400
    db = carica_grafo()
    try:
        rows = db.execute("""SELECT id, nome, disciplina FROM ricette
                             WHERE (immagine IS NULL OR immagine='') ORDER BY id""").fetchall()
        mancanti = [{"id": r["id"], "nome": r["nome"], "disc": r["disciplina"]} for r in rows]
        if dry:
            return jsonify({"ricette_senza_immagine": len(mancanti),
                            "esempi": [m["nome"] for m in mancanti[:10]]})
        fatte = []
        for m in mancanti[:n]:
            # query: nome ricetta (pulito) — Pexels trova cibo/drink pertinente
            q = m["nome"]
            img = cerca_immagine(q)
            if not img and m["disc"]:  # fallback sulla disciplina generica
                img = cerca_immagine({"bar":"cocktail","cucina":"food dish","pasticceria":"dessert",
                                      "panificazione":"bread","gelateria":"ice cream"}.get(m["disc"], "food"))
            if img and img.get("url"):
                db.execute("UPDATE ricette SET immagine=?, immagine_autore=?, immagine_url_fonte=? WHERE id=?",
                           (img["url"], credito_immagine(img["autore"]), img["fonte"], m["id"]))
                fatte.append({"ricetta": m["nome"], "autore": img["autore"]})
        return jsonify({"riempite_ora": len(fatte), "rimanenti": len(mancanti)-len(fatte),
                        "dettaglio": fatte, "nota": "ripeti per riempire le altre"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/admin/genera-ricette-mancanti")
def admin_genera_ricette_mancanti():
    """Genera ricette sui fenomeni SENZA ricetta (i buchi veri). Una ricetta per fenomeno,
    pertinente, salvata (IT; traduzioni EN/ES poi via batch traduci-ricette).
    ?n=3 quante generarne per chiamata (piccolo per il timeout worker). ?disc= per disciplina.
    Ogni ricetta copre un fenomeno scoperto -> espansione MIRATA, non a caso."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import json as _json, re as _re, unicodedata
    from db import carica_grafo, _get_conn, _release_conn
    from builder import genera_ricetta
    n = int(request.args.get("n", "3"))
    disc_filtro = request.args.get("disc", "")
    db = carica_grafo()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # fenomeni coperti dalle ricette esistenti
        cur.execute("SELECT fenomeni FROM ricette")
        coperti = set()
        for row in cur.fetchall():
            rf = row[0] if not hasattr(row,"keys") else row["fenomeni"]
            fl = rf if isinstance(rf,list) else (_json.loads(rf) if rf else [])
            for f in (fl or []): coperti.add(str(f).strip())
        # fenomeni senza ricetta (con nome e disciplina)
        if disc_filtro:
            cur.execute("SELECT id,name,domain FROM nodes WHERE type='Fenomeno' AND domain=%s ORDER BY name",(disc_filtro,))
        else:
            cur.execute("SELECT id,name,domain FROM nodes WHERE type='Fenomeno' ORDER BY domain,name")
        scoperti = []
        for f in cur.fetchall():
            fid = f[0] if not hasattr(f,"keys") else f["id"]
            fname = f[1] if not hasattr(f,"keys") else f["name"]
            fdom = f[2] if not hasattr(f,"keys") else f["domain"]
            # scoperto se né l'id né il nome sono tra i coperti
            if fid not in coperti and fname not in coperti:
                scoperti.append({"id":fid,"nome":fname,"disc":fdom or "cucina"})
        generate = []
        for fen in scoperti[:n]:
            try:
                # richiesta guidata dal nome del fenomeno -> il builder aggancia i fenomeni pertinenti
                ric = genera_ricetta(db, f"una preparazione che dimostra: {fen['nome']}", disciplina=fen["disc"], lang="it")
                if ric.get("errore") or not ric.get("nome"): continue
                nome = ric["nome"]
                slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
                slug = _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
                rid = f"ric-gen-{slug}"
                cur.execute("""INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                        punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING""",
                    (rid, nome, fen["disc"], ric.get("descrizione",""),
                     _json.dumps(ric.get("ingredienti",[]),ensure_ascii=False),
                     _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                     _json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                     _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                     ric.get("punto_critico",""),
                     _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                     _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                     _json.dumps(ric.get("applicazioni",[]),ensure_ascii=False),
                     ric.get("tempo_prep"), ric.get("tempo_cottura"),
                     ric.get("difficolta",""), ric.get("porzioni","")))
                conn.commit()
                generate.append({"fenomeno":fen["nome"],"ricetta":nome,"id":rid,"fenomeni_agganciati":ric.get("fenomeni",[])})
            except Exception as ge:
                conn.rollback()
                generate.append({"fenomeno":fen["nome"],"errore":str(ge)[:100]})
        return jsonify({"scoperti_totali":len(scoperti),"generate_ora":len([g for g in generate if g.get("id")]),
                        "dettaglio":generate,
                        "nota":"traduzioni EN/ES: poi via /admin/traduci-ricette. Ripeti per generare le altre."})
    except Exception as e:
        import traceback
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[-300:]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/fenomeni-senza-ricetta")
def admin_fenomeni_senza_ricetta():
    """Trova i fenomeni che NON hanno ancora una ricetta che li dimostra (i buchi veri da riempire).
    Guida l'espansione mirata: ogni ricetta nuova deve coprire un fenomeno scoperto, non duplicare."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json
    disc = request.args.get("disc","")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # tutti i fenomeni (per disciplina se richiesto)
        if disc:
            cur.execute("SELECT id,name,domain FROM nodes WHERE type='Fenomeno' AND domain=%s ORDER BY name",(disc,))
        else:
            cur.execute("SELECT id,name,domain FROM nodes WHERE type='Fenomeno' ORDER BY domain,name")
        fen = cur.fetchall()
        # i fenomeni citati nelle ricette (campo fenomeni della tabella ricette)
        cur.execute("SELECT fenomeni FROM ricette")
        coperti = set()
        for row in cur.fetchall():
            rf = row[0] if not hasattr(row,"keys") else row["fenomeni"]
            fl = rf if isinstance(rf,list) else (_json.loads(rf) if rf else [])
            for f in (fl or []):
                coperti.add(str(f).strip())
        senza, con = [], 0
        for f in fen:
            fid = f[0] if not hasattr(f,"keys") else f["id"]
            fname = f[1] if not hasattr(f,"keys") else f["name"]
            fdom = f[2] if not hasattr(f,"keys") else f["domain"]
            if fid in coperti: con+=1
            else: senza.append({"id":fid,"nome":fname,"disc":fdom})
        # raggruppo per disciplina
        per_disc = {}
        for s in senza:
            per_disc.setdefault(s["disc"],[]).append(s["nome"])
        return jsonify({"totale_fenomeni":len(fen),"con_ricetta":con,"senza_ricetta":len(senza),
                        "per_disciplina":{k:{"quanti":len(v),"fenomeni":v} for k,v in sorted(per_disc.items())}})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/migra-schema-traduzioni")
def admin_migra_schema_traduzioni():
    """Aggiunge le colonne tradotte per i campi ricetta che erano solo in IT."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    COLONNE = ["nome_en TEXT","nome_es TEXT","procedimento_en JSONB","procedimento_es JSONB",
               "applicazioni_en JSONB","applicazioni_es JSONB","punto_critico_en TEXT","punto_critico_es TEXT"]
    conn = _get_conn()
    try:
        cur = conn.cursor(); fatte=[]
        for col in COLONNE:
            try:
                cur.execute(f"ALTER TABLE ricette ADD COLUMN IF NOT EXISTS {col}"); fatte.append(col.split()[0])
            except Exception as me:
                pass
        conn.commit()
        return jsonify({"ok":True,"colonne":fatte})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:300]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/traduci-ricette")
def admin_traduci_ricette():
    """Traduce nome/procedimento/applicazioni/punto_critico delle ricette in EN e ES via Haiku.
    Ancorato: traduce il testo esistente, non rigenera. Batch con limite/skip."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback, json as _json, re as _re
    from ai import _haiku_raw
    limite = int(request.args.get("limite","2"))
    skip = int(request.args.get("skip","0"))
    lang = request.args.get("lang","en")  # UNA lingua per chiamata (evita timeout)
    lname = {"en":"English","es":"Spanish"}.get(lang,"English")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"""SELECT id,nome,procedimento,applicazioni,punto_critico FROM ricette
            WHERE nome_{lang} IS NULL OR procedimento_{lang} IS NULL ORDER BY id""")
        rows = cur.fetchall()
        fatti, errori, n, visti = [], [], 0, 0
        for row in rows:
            if n>=limite: break
            visti+=1
            if visti<=skip: continue
            rid = row[0] if not hasattr(row,"keys") else row["id"]
            nome = row[1] if not hasattr(row,"keys") else row["nome"]
            proc = row[2] if not hasattr(row,"keys") else row["procedimento"]
            appl = row[3] if not hasattr(row,"keys") else row["applicazioni"]
            pc = row[4] if not hasattr(row,"keys") else row["punto_critico"]
            proc_p = proc if isinstance(proc,list) else (_json.loads(proc) if proc else [])
            appl_p = appl if isinstance(appl,list) else (_json.loads(appl) if appl else [])
            try:
                def _one(testo):
                    """1 chiamata Haiku per 1 testo. Ritorna la traduzione pulita."""
                    if not testo or not str(testo).strip(): return ""
                    out = _haiku_raw(f"Translate this Italian cooking text to {lname}. Keep numbers and units. "
                                     f"Return ONLY the translation on a single line, no quotes, no notes:\n{testo}")
                    return (out or "").strip().strip('"').strip()
                # i passi in UNA chiamata, separati da @@@ (un solo separatore semplice)
                passi = [step.get("testo","") for step in proc_p if isinstance(step,dict)]
                passi_join = "\n@@@\n".join(passi)
                proc_out_txt = _haiku_raw(
                    f"Translate to {lname} each cooking step. The steps are separated by a line with @@@. "
                    f"Keep EXACTLY the same number of steps and the same @@@ separators. Keep numbers/units. "
                    f"Return ONLY the translated steps with @@@ between them:\n\n{passi_join}") or ""
                passi_tr = [x.strip() for x in proc_out_txt.split("@@@") if x.strip()]
                # se il conteggio non torna, traduco passo per passo (fallback sicuro)
                if len(passi_tr) != len(passi):
                    passi_tr = [_one(pz) for pz in passi]
                proc_t = []
                for i,step in enumerate([s for s in proc_p if isinstance(s,dict)]):
                    st = dict(step)
                    if i < len(passi_tr) and passi_tr[i]: st["testo"]=passi_tr[i]
                    proc_t.append(st)
                nome_t = _one(nome) or nome
                pc_t = _one(pc) if pc else ""
                appl_t = [_one(a) or a for a in appl_p if isinstance(a,str)]
                cur.execute(f"""UPDATE ricette SET nome_{lang}=%s, procedimento_{lang}=%s::jsonb,
                    applicazioni_{lang}=%s::jsonb, punto_critico_{lang}=%s WHERE id=%s""",
                    (nome_t, _json.dumps(proc_t,ensure_ascii=False),
                     _json.dumps(appl_t,ensure_ascii=False), pc_t, rid))
                conn.commit()
                fatti.append(f"{rid}: {len(passi_tr)}/{len(passi)} passi -> {lang}")
            except Exception as le:
                errori.append(f"{rid}: {str(le)[:60]}")
            n+=1
        cur.execute(f"SELECT COUNT(*) FROM ricette WHERE nome_{lang} IS NULL OR procedimento_{lang} IS NULL")
        restano = cur.fetchone()[0]
        return jsonify({"ok":True,"tradotti":fatti,"errori":errori,"restano":restano})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:400]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/azzera-traduzioni-sbagliate")
def admin_azzera_traduzioni_sbagliate():
    """Azzera le traduzioni dove nome_en/es e uguale all'italiano (salvate male dal metodo vecchio),
    cosi traduci-ricette le ripesca e rifa."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # azzero dove nome_en == nome (non tradotto davvero) - euristica: procedimento_en col primo testo == it
        for lang in ["en","es"]:
            cur.execute(f"""UPDATE ricette SET nome_{lang}=NULL, procedimento_{lang}=NULL,
                applicazioni_{lang}=NULL, punto_critico_{lang}=NULL
                WHERE procedimento_{lang}::text = procedimento::text""")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM ricette WHERE procedimento_en IS NULL")
        return jsonify({"ok":True,"da_ritradurre_en":cur.fetchone()[0]})
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:300]}),500
    finally:
        _release_conn(conn)

@bp.route("/admin/costi-ai")
def admin_costi_ai():
    """Cruscotto costi AI: legge ai_usage_log e mostra spesa totale, per modello, per route,
    media per chiamata, e le ultime chiamate. Rende VISIBILE dove vanno i soldi."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    giorni = int(request.args.get("giorni", "7"))
    db = carica_grafo()
    try:
        tot = db.execute("""SELECT COUNT(*) n, COALESCE(SUM(cost_usd),0) c,
                            COALESCE(SUM(tokens_in),0) ti, COALESCE(SUM(tokens_out),0) to_
                            FROM ai_usage_log WHERE ts > NOW() - (? || ' days')::interval""",
                         (str(giorni),)).fetchone()
        per_modello = db.execute("""SELECT model, COUNT(*) n, COALESCE(SUM(cost_usd),0) c
                            FROM ai_usage_log WHERE ts > NOW() - (? || ' days')::interval
                            GROUP BY model ORDER BY c DESC""", (str(giorni),)).fetchall()
        per_route = db.execute("""SELECT route, COUNT(*) n, COALESCE(SUM(cost_usd),0) c
                            FROM ai_usage_log WHERE ts > NOW() - (? || ' days')::interval
                            GROUP BY route ORDER BY c DESC""", (str(giorni),)).fetchall()
        n = tot["n"] or 0; costo = float(tot["c"] or 0)
        return jsonify({
            "periodo_giorni": giorni,
            "chiamate_totali": n,
            "costo_totale_usd": round(costo, 4),
            "costo_medio_per_chiamata_usd": round(costo / n, 6) if n else 0,
            "token_in": tot["ti"], "token_out": tot["to_"],
            "per_modello": [{"modello": r["model"], "chiamate": r["n"], "costo_usd": round(float(r["c"]), 4)} for r in per_modello],
            "per_route": [{"route": r["route"], "chiamate": r["n"], "costo_usd": round(float(r["c"]), 4)} for r in per_route],
            "nota": "Il costo di sviluppo (generazioni di prova, audit, batch) NON è il costo per utente. "
                    "Un utente reale fa poche chiamate leggere: vedi costo_medio_per_chiamata."
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/classifica-flavor")
def admin_classifica_flavor():
    """Classifica i nodi Ahn: kind (essential_oil/ingredient) + visibility (public/hidden).
    Gli oli essenziali diventano hidden (restano nel grafo per il calcolo, ma spariscono dall'UI),
    tranne i pochi usati davvero in cucina/bar. ?dry=1 per contare, ?dry=0 per applicare.
    Scrive in data JSONB: nessuna migrazione schema."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    import json as _j
    dry = request.args.get("dry", "1") != "0"
    db = carica_grafo()
    # oli essenziali che RESTANO visibili (ingredienti reali in cucina/bar)
    OIL_VISIBILI = {"ahn_bergamot_oil","ahn_lemon_oil","ahn_orange_oil","ahn_bitter_orange_oil",
                    "ahn_sweet_orange_oil","ahn_lime_oil","ahn_mandarin_oil","ahn_grapefruit_oil",
                    "ahn_peppermint_oil","ahn_spearmint_oil","ahn_vanilla_oil"}
    try:
        rows = db.execute("SELECT id, name, data FROM nodes WHERE id LIKE 'ahn_%%'", ()).fetchall()
        n_oil_hidden = n_oil_public = n_ingredient = 0
        for r in rows:
            nid = r["id"]; nm = (r["name"] or "")
            data = r["data"] if isinstance(r["data"], dict) else (_j.loads(r["data"]) if r["data"] else {})
            is_oil = nm.endswith("_oil") or nid.endswith("_oil")
            if is_oil and nid not in OIL_VISIBILI:
                kind, vis = "essential_oil", "hidden"; n_oil_hidden += 1
            elif is_oil:
                kind, vis = "essential_oil", "public"; n_oil_public += 1
            else:
                kind, vis = "ingredient", "public"; n_ingredient += 1
            if not dry:
                data["kind"] = kind; data["visibility"] = vis
                db.execute("UPDATE nodes SET data=? WHERE id=?", (_j.dumps(data, ensure_ascii=False), nid))
        return jsonify({"dry_run": dry, "totale_ahn": len(rows),
                        "essential_oil_hidden": n_oil_hidden,
                        "essential_oil_public": n_oil_public,
                        "ingredient_public": n_ingredient,
                        "nota": "hidden = resta nel grafo per il calcolo abbinamenti, sparisce dall'UI utente" if dry
                                else "applicato: data.kind + data.visibility scritti"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/pulisci-nomi-flavor")
def admin_pulisci_nomi_flavor():
    """Elenca e (se dry=0) traduce i nomi ahn sporchi EN->IT via AI, salvando sul nodo.
    ?dry=1 (default) solo elenca; ?dry=0 traduce e salva. ?limite=N per fare a lotti."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    from db import carica_grafo
    dry = request.args.get("dry", "1") != "0"
    limite = int(request.args.get("limite", "80"))
    db = carica_grafo()
    try:
        # pattern che funziona in admin.py: db.execute con ? e accesso per nome colonna
        # NOTA: il wrapper passa params a psycopg → i % letterali dei LIKE vanno RADDOPPIATI (%%).
        # solo nodi VISIBILI (visibility != hidden): gli oli nascosti non servono tradotti.
        # Escludo anche gli _oil per sicurezza. Traduco solo i CIBI veri con nome sporco.
        rows = db.execute(r"""SELECT id, name FROM nodes WHERE id LIKE 'ahn_%%'
                       AND (data->>'visibility') IS DISTINCT FROM 'hidden'
                       AND (data->>'nome_verificato') IS DISTINCT FROM 'true'
                       AND name NOT LIKE '%%_oil'
                       AND (lower(name) LIKE '%%cheese%%' OR lower(name) LIKE '%%wine%%'
                            OR lower(name) LIKE '%%beef%%' OR lower(name) LIKE '%%roasted%%'
                            OR lower(name) LIKE '%%dried%%' OR lower(name) LIKE '%%smoked%%'
                            OR lower(name) LIKE '%%fried%%' OR lower(name) LIKE '%%raw%%'
                            OR lower(name) LIKE '%%sauce%%' OR lower(name) LIKE '%%boiled%%'
                            OR lower(name) LIKE '%%seed%%' OR lower(name) LIKE '%%green %%'
                            OR lower(name) LIKE '%%black %%' OR lower(name) LIKE '%%white %%'
                            OR lower(name) LIKE '%%red %%' OR lower(name) LIKE '%%broth%%'
                            OR lower(name) LIKE '%%liver%%' OR lower(name) LIKE '%%meat%%')
                       ORDER BY name LIMIT ?""", (limite,)).fetchall()
        items = [{"id": r["id"], "nome": r["name"]} for r in rows]
        if dry:
            return jsonify({"dry_run": True, "totale": len(items), "nomi": items,
                            "nota": "per tradurre e salvare: aggiungi &dry=0"})
        from ai import _haiku_raw
        aggiornati = []
        saltati = []
        for it in items:
            en = it["nome"]
            prompt_t = (f"Traduci in italiano culinario questo ingrediente. REGOLE: "
                        f"1) usa il nome che un cuoco italiano direbbe spontaneamente "
                        f"(es. 'blue cheese'->'formaggio erborinato', 'butter oil'->'burro chiarificato'). "
                        f"2) se è un nome proprio internazionale (katsuobushi, mirin), LASCIALO. "
                        f"3) NON inventare: se non sei sicuro, restituisci il nome originale. "
                        f"Rispondi SOLO col nome, minuscolo, senza virgolette. Nome: {en.replace('_',' ')}")
            out = _haiku_raw(prompt_t)
            if not out:  # fallback su Mistral se Haiku non risponde (credito/rate intermittente)
                try:
                    from ai import chiedi_mistral
                    out = chiedi_mistral(prompt_t)
                except Exception:
                    out = None
            it_nome = (out or "").strip().strip('"').strip().lower()
            # confronto col nome SENZA underscore (l'AI riceve gli spazi, deve differire da quello)
            en_confronto = en.replace('_', ' ').lower()
            if it_nome and it_nome != en_confronto and it_nome != en.lower() and len(it_nome) < 60:
                db.execute("UPDATE nodes SET name=? WHERE id=?", (it_nome, it["id"]))
                aggiornati.append({"id": it["id"], "da": en, "a": it_nome})
            else:
                # l'AI lascia il nome invariato (botanico latino, nome proprio): marco come
                # verificato così il ciclo NON lo ripesca e avanza ai nomi successivi.
                try:
                    import json as _jj
                    rr = db.execute("SELECT data FROM nodes WHERE id=?", (it["id"],)).fetchone()
                    dd = rr["data"] if (rr and isinstance(rr["data"], dict)) else (_jj.loads(rr["data"]) if (rr and rr["data"]) else {})
                    dd["nome_verificato"] = "true"
                    db.execute("UPDATE nodes SET data=? WHERE id=?", (_jj.dumps(dd, ensure_ascii=False), it["id"]))
                except Exception:
                    pass
                saltati.append({"nome": en, "ai": it_nome or "(vuoto)"})
        return jsonify({"dry_run": False, "aggiornati": len(aggiornati), "dettaglio": aggiornati, "saltati": saltati[:10]})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-200:]}), 500

@bp.route("/admin/audit-flavor")
def admin_audit_flavor():
    """Audit del flavor network: quanti ingredienti Ahn, quanti composti, copertura abbinamenti,
    e quanti nomi sono ancora 'sporchi' (inglesi/laboratorio non tradotti)."""
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    import traceback
    conn = _get_conn()
    try:
        cur = conn.cursor()
        out = {}
        # nodi ahn (ingredienti del flavor network)
        cur.execute("SELECT COUNT(*) FROM nodes WHERE id LIKE 'ahn_%'")
        out["nodi_ahn"] = cur.fetchone()[0]
        # nodi composto
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Composto' OR id LIKE 'comp_%' OR id LIKE 'cmp_%'")
        out["nodi_composto"] = cur.fetchone()[0]
        # archi contiene_composto (ingrediente->composto)
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='contiene_composto'")
        out["archi_contiene_composto"] = cur.fetchone()[0]
        # archi abbinamento_aromatico
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='abbinamento_aromatico'")
        out["archi_abbinamento"] = cur.fetchone()[0]
        # ingredienti ahn con QUANTI composti (distribuzione)
        cur.execute("""SELECT from_id, COUNT(*) c FROM edges WHERE relation='contiene_composto'
                       GROUP BY from_id ORDER BY c""")
        rows = cur.fetchall()
        conteggi = [r[1] if not hasattr(r,"keys") else r["c"] for r in rows]
        out["ingredienti_con_composti"] = len(conteggi)
        if conteggi:
            out["composti_min"] = min(conteggi)
            out["composti_max"] = max(conteggi)
            out["composti_mediana"] = sorted(conteggi)[len(conteggi)//2]
            out["ingredienti_meno_5_composti"] = sum(1 for c in conteggi if c<5)
        # nomi sporchi: nodi ahn il cui name ha maiuscole interne o parole inglesi tipiche
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE id LIKE 'ahn_%'
                       AND (name ~ '[A-Z][a-z]+ [A-Z]' OR name ILIKE '%cheese%' OR name ILIKE '%wine%'
                            OR name ILIKE '%beef%' OR name ILIKE '%roasted%')""")
        out["nomi_sporchi_stimati"] = cur.fetchone()[0]
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore":str(e),"trace":traceback.format_exc()[:300]}),500
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

