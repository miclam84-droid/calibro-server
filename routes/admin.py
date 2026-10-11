# ============================================================
# routes/admin.py — interfaccia admin (build, quality-test, schede,
# assistenza, statistiche, migrazione). Auth via ADMIN_SECRET.
# Dipende da: db, auth, contenuto, notifiche, oss, ai_gateway.
# ============================================================
# ⚠️ DEBITO TECNICO NOTO (refactoring POST-LANCIO, non toccare prima):
#   Questo file è grande (~6.500 righe). Congelato per il lancio: stabile e testato.
#   PIANO post-lancio: spezzare in moduli per dominio →
#     admin_fenomeni.py · admin_ricette.py · admin_generazione.py · admin_monitoraggio.py
#   Auth unificata su _admin_ok() (header X-Admin-Secret o query ?s=). NON spezzare le route ora:
#   rischio regressioni sui percorsi di import Flask. Prima il lancio, poi il refactoring.
# ============================================================
import os, json, traceback, time, hmac
from flask import Blueprint, request, jsonify, render_template

from db import carica_grafo, _dati, _get_conn, _release_conn
from auth import _admin_autenticato, _init_account_tables
from contenuto import (_scheda_lang, _numero_bersaglio, _pulisci_traduzione, _corregge_it)
from notifiche import _invia_email_resend
import oss

bp = Blueprint("admin", __name__)


def _admin_ok(req):
    """Auth admin unificata: accetta il secret dall'header X-Admin-Secret (preferito, non finisce
    nei log del browser/proxy) O dal query param ?s= (retrocompatibile per i tool interni).
    Sicurezza migliorata senza rompere gli endpoint esistenti."""
    _secret = os.environ.get("ADMIN_SECRET") or ""
    if not _secret:
        return False
    _dato = req.headers.get("X-Admin-Secret", "") or req.args.get("s", "")
    return hmac.compare_digest(str(_dato), str(_secret))


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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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




@bp.route("/admin/coverage-fenomeni")
def admin_coverage_fenomeni():
    """Diagnostica 'Bibbia': per ogni fenomeno misura quanto è completo e collegato.
    Assi: principio (governato_da), numero-bersaglio (data o si_manifesta_in.target),
    errore (fallisce_come), tecnica (realizzato_da/controllato_con), prodotto (si_manifesta_in)."""
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
        # --- i 16 fenomeni etnici/specialistici prima non mappati (governato_da) ---
        (["wok-hei","wok hei","tandoor","tadka","barbecue","low-and-slow","stall","strecker","espansione-termica","oven-spring","oven spring"], "princ-calore"),
        (["kansui","nixtamal","inversione-zucchero","inversione dello zucchero","saccarosio"], "princ-ph"),
        (["koji","imbrunimento-enzimatico","imbrunimento enzimatico","enzimatico"], "princ-denaturazione"),
        (["gelatinizzazione-del-riso","riso-glutinoso","riso glutinoso","riso"], "princ-gelatinizzazione"),
        (["emulsione-forzata","paitan","tonkotsu"], "princ-emulsione"),
        (["umami","glutammato","inosinato","capillarita","capillarità","tissotropia","assorbimento-porosi"], "princ-diffusione"),
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








@bp.route("/admin/coeff-farine")
def admin_coeff_farine():
    """Arricchisce i nodi-farina con i coefficienti di panificazione: W (forza), P/L (tenacita/estensibilita),
    proteine %, uso consigliato. Come i coefficienti POD/PAC per gli zuccheri."""
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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



@bp.route("/admin/lista-storia")
def admin_lista_storia():
    """Elenca i nodi Storia col testo (per verificare le date storiche)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    db = carica_grafo()
    rows = db.execute("SELECT id, name, domain, data FROM nodes WHERE type='Storia' ORDER BY domain").fetchall()
    out = []
    for r in rows:
        data = _dati(r["data"])
        out.append({"id": r["id"], "nome": r["name"], "disciplina": r["domain"],
                    "testo": data.get("testo", ""), "svolte": data.get("svolte", []),
                    "da_rivedere": data.get("da_rivedere", "")})
    return jsonify({"totale": len(out), "storie": out})

@bp.route("/admin/aggiorna-storia", methods=["POST"])
def admin_aggiorna_storia():
    """Aggiorna il testo/svolte di un nodo Storia e toglie da_rivedere. Body: {id, testo, svolte:[]}."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    b = request.json or {}
    nid = b.get("id", "")
    if not nid:
        return jsonify({"errore": "id mancante"}), 400
    db = carica_grafo()
    row = db.execute("SELECT data FROM nodes WHERE id=?", (nid,)).fetchone()
    if not row:
        return jsonify({"errore": "nodo non trovato"}), 404
    data = _dati(row["data"])
    if b.get("testo"):
        data["testo"] = b["testo"]
    if b.get("svolte"):
        data["svolte"] = b["svolte"]
    data["da_rivedere"] = "false"
    data["date_verificate"] = "true"
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(data, ensure_ascii=False), nid))
        conn.commit()
        return jsonify({"ok": True, "id": nid})
    finally:
        _release_conn(conn)





@bp.route("/admin/audit-fenomeni-numeri")
def admin_audit_fenomeni_numeri():
    """Elenca i fenomeni SENZA numero_bersaglio (la radice delle ricette senza numeri)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import carica_grafo
    db = carica_grafo()
    rows = db.execute("SELECT id, name, domain, data FROM nodes").fetchall()
    con_numero, senza_numero = [], []
    disc_filtro = request.args.get("disc", "")
    dettaglio_disc = []
    for r in rows:
        rid = r["id"]
        if not str(rid).startswith("fen-"):
            continue
        data = _dati(r["data"])
        nb = (data.get("numero_bersaglio") or data.get("target") or "").strip()
        entry = {"id": rid, "nome": r["name"], "disciplina": r["domain"]}
        (con_numero if nb else senza_numero).append(entry)
        if disc_filtro and (r["domain"] or "").lower() == disc_filtro.lower():
            dettaglio_disc.append({"id": rid, "nome": r["name"], "numero_bersaglio": nb,
                                   "chiavi_data": list(data.keys())})
    return jsonify({"totale": len(con_numero)+len(senza_numero),
                    "con_numero": len(con_numero), "senza_numero": len(senza_numero),
                    "lista_senza": senza_numero,
                    "dettaglio_disciplina": dettaglio_disc})

@bp.route("/admin/conta-nodi")
def admin_conta_nodi():
    """Conta i nodi per tipo (Fenomeno, Tecnica, Attrezzatura, ecc.) e per disciplina.
    Serve a capire dove il grafo è povero (es. poche tecniche/attrezzature)."""
    if not _admin_ok(request):
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

# ── Rigenerazione IMMAGINI in background (tracciata, varia le foto) ──
_IMG_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "corrente": ""}

def _img_worker(solo_mancanti):
    from db import carica_grafo
    from immagini import cerca_immagine, credito_immagine
    global _IMG_STATO
    try:
        db = carica_grafo()
        if solo_mancanti:
            rows = db.execute("SELECT id, nome, disciplina, ingredienti FROM ricette WHERE (immagine IS NULL OR immagine='') ORDER BY id").fetchall()
        else:
            rows = db.execute("SELECT id, nome, disciplina, ingredienti FROM ricette ORDER BY id").fetchall()
        lista = [{"id": r["id"], "nome": r["nome"], "disc": r["disciplina"], "ing": r["ingredienti"]} for r in rows]
        _IMG_STATO.update({"attivo": True, "fatte": 0, "totale": len(lista), "errori": 0})
        # per variare: tengo un contatore per disciplina, così pesco risultati diversi (rank 0..4)
        rank_disc = {}
        # set delle foto GIÀ usate: nessuna ricetta deve ripetere una foto (no sciatteria).
        _url_usate = set()
        try:
            for _r in db.execute("SELECT immagine FROM ricette WHERE immagine IS NOT NULL AND immagine<>''").fetchall():
                _u = _r["immagine"] if hasattr(_r, "keys") else _r[0]
                if _u: _url_usate.add(_u)
        except Exception:
            pass
        for m in lista:
            _IMG_STATO["corrente"] = m["nome"]
            disc = m["disc"] or "x"
            rank = rank_disc.get(disc, 0)
            try:
                # ingrediente principale per il fallback (caponata->melanzana, mai foto sbagliata)
                _ings = []
                try:
                    import json as _ji
                    _raw = m.get("ing")
                    _lst = _raw if isinstance(_raw, list) else (_ji.loads(_raw) if _raw else [])
                    for _x in _lst[:3]:
                        _n = _x.get("nome") if isinstance(_x, dict) else str(_x)
                        if _n: _ings.append(_n)
                except Exception:
                    pass
                img = cerca_immagine(m["nome"], disciplina=m["disc"], nome=m["nome"], rank=rank, ingredienti=_ings, evita_urls=_url_usate)
                if img and img.get("url") and img["url"] not in _url_usate:
                    # foto NUOVA (non già usata): la salvo. Se fosse un duplicato, lascio il blueprint.
                    _url_usate.add(img["url"])
                    cred = credito_immagine(img["autore"], img.get("fonte_nome", "Pexels"))
                    db.execute("UPDATE ricette SET immagine=?, immagine_autore=?, immagine_url_fonte=? WHERE id=?",
                               (img["url"], cred, img["fonte"], m["id"]))
                    _IMG_STATO["fatte"] += 1
                    rank_disc[disc] = (rank + 1) % 5  # ruota tra i primi 5 risultati
                else:
                    # nessuna foto NUOVA disponibile -> lascio il blueprint (meglio che ripetere)
                    _IMG_STATO["errori"] += 1
            except Exception:
                _IMG_STATO["errori"] += 1
    finally:
        _IMG_STATO["attivo"] = False
        _IMG_STATO["corrente"] = ""

@bp.route("/admin/immagini-bg")
def admin_immagini_bg():
    """Rigenera le immagini in background (tracciato). ?mancanti=1 solo le mancanti, altrimenti TUTTE."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _IMG_STATO
    if _IMG_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _IMG_STATO})
    import threading
    solo_mancanti = request.args.get("mancanti", "0") != "0"
    t = threading.Thread(target=_img_worker, args=(solo_mancanti,), daemon=True)
    t.start()
    return jsonify({"avviato": True, "modo": "solo_mancanti" if solo_mancanti else "tutte"})

@bp.route("/admin/immagini-bg-stato")
def admin_immagini_bg_stato():
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_IMG_STATO)

@bp.route("/admin/diag-cloudinary")
def admin_diag_cloudinary():
    """Diagnostica: le variabili Cloudinary ci sono? quante foto vede l'app nell'archivio?"""
    if not _admin_ok(request):
        return "Forbidden", 403
    import os as _os
    from immagini import _cloudinary_lista
    has = {
        "CLOUDINARY_CLOUD_NAME": bool(_os.environ.get("CLOUDINARY_CLOUD_NAME")),
        "CLOUDINARY_API_KEY": bool(_os.environ.get("CLOUDINARY_API_KEY")),
        "CLOUDINARY_API_SECRET": bool(_os.environ.get("CLOUDINARY_API_SECRET")),
        "cloud_name_valore": _os.environ.get("CLOUDINARY_CLOUD_NAME") or "(vuoto)",
    }
    urls = _cloudinary_lista()
    # elenco completo dei nomi file per capire cosa c'è nell'archivio
    nomi = [u.split("/")[-1] for u in urls]
    return jsonify({"variabili": has, "foto_usabili_dopo_filtro": len(urls),
                    "nomi_file": nomi})

@bp.route("/admin/riempi-immagini-ricette")
def admin_riempi_immagini():
    """Riempie le immagini mancanti delle ricette cercando su Pexels (API gratuita).
    Serve PEXELS_API_KEY nell'ambiente. Salva url+autore+fonte con credito.
    ?n=8 quante per chiamata (timeout). ?dry=1 per contare quante ne mancano."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import carica_grafo
    from immagini import cerca_immagine, credito_immagine
    dry = request.args.get("dry", "0") != "0"
    n = int(request.args.get("n", "8"))
    if not (os.environ.get("PEXELS_API_KEY") or os.environ.get("UNSPLASH_ACCESS_KEY") or os.environ.get("PIXABAY_API_KEY")):
        return jsonify({"errore": "manca almeno una chiave immagini (PEXELS_API_KEY, UNSPLASH_ACCESS_KEY o PIXABAY_API_KEY)",
                        "come": "aggiungi almeno una chiave nelle variabili Railway"}), 400
    db = carica_grafo()
    try:
        rifai = request.args.get("rifai", "0") != "0"
        if rifai:
            # rifà TUTTE le immagini con la query intelligente (per sostituire quelle sbagliate)
            rows = db.execute("""SELECT id, nome, disciplina FROM ricette ORDER BY id""").fetchall()
        else:
            rows = db.execute("""SELECT id, nome, disciplina FROM ricette
                                 WHERE (immagine IS NULL OR immagine='') ORDER BY id""").fetchall()
        mancanti = [{"id": r["id"], "nome": r["nome"], "disc": r["disciplina"]} for r in rows]
        if dry:
            return jsonify({"ricette_da_fare": len(mancanti),
                            "esempi": [m["nome"] for m in mancanti[:10]]})
        fatte = []
        for m in mancanti[:n]:
            # query INTELLIGENTE: contesto disciplina + parola-chiave, non il nome esatto (evita foto sbagliate)
            img = cerca_immagine(m["nome"], disciplina=m["disc"], nome=m["nome"])
            if img and img.get("url"):
                cred = credito_immagine(img["autore"], img.get("fonte_nome", "Pexels"))
                db.execute("UPDATE ricette SET immagine=?, immagine_autore=?, immagine_url_fonte=? WHERE id=?",
                           (img["url"], cred, img["fonte"], m["id"]))
                fatte.append({"ricetta": m["nome"], "autore": img["autore"], "fonte": img.get("fonte_nome")})
        return jsonify({"riempite_ora": len(fatte), "totale_da_fare": len(mancanti),
                        "dettaglio": fatte, "nota": "ripeti per le altre"})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/admin/colonne-ricette")
def admin_colonne_ricette():
    """Diagnostica: elenca le colonne reali della tabella ricette."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette' ORDER BY column_name")
        cols = [r[0] for r in cur.fetchall()]
        # controllo diretto: prendo una ricetta -v2 e leggo esperimento raw
        cur.execute("SELECT id, esperimento, limite FROM ricette WHERE id LIKE 'ric-cls-%%-v2' LIMIT 3")
        campioni = [{"id": r[0], "esperimento": (r[1] or "NULL")[:50], "limite": (r[2] or "NULL")[:50]} for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine IS NOT NULL AND immagine <> ''")
        con_img = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        cur.execute("SELECT id, nome, immagine, immagine_autore FROM ricette WHERE immagine IS NOT NULL AND immagine <> '' LIMIT 3")
        img_campioni = [{"id": r[0], "nome": r[1], "immagine": (r[2] or "")[:50], "autore": r[3]} for r in cur.fetchall()]
        return jsonify({"colonne": cols, "ha_esperimento": "esperimento" in cols, "ha_limite": "limite" in cols,
                        "ha_twist": "twist" in cols, "campioni": campioni,
                        "ricette_con_immagine": con_img, "ricette_totali": tot, "img_campioni": img_campioni})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)


@bp.route("/admin/cancella-nodo")
def admin_cancella_nodo():
    """Cancella un nodo per id (e i suoi archi). Per rimuovere contenuti sbagliati/inventati. ?id= obbligatorio."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import carica_grafo
    nid = request.args.get("id", "")
    if not nid:
        return jsonify({"errore": "serve ?id="}), 400
    db = carica_grafo()
    try:
        n = db.execute("SELECT name FROM nodes WHERE id=?", (nid,)).fetchone()
        if not n:
            return jsonify({"errore": "nodo non trovato", "id": nid}), 404
        nome = n["name"]
        db.execute("DELETE FROM edges WHERE from_id=? OR to_id=?", (nid, nid))
        db.execute("DELETE FROM nodes WHERE id=?", (nid,))
        return jsonify({"cancellato": nid, "nome": nome})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/admin/conta-ricette-vecchie")
def admin_conta_ricette_vecchie():
    """Diagnostica veloce: conta le ricette vecchie SENZA generare (per misurare la query)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    import time as _t
    conn = _get_conn(); cur = conn.cursor()
    try:
        t0=_t.time()
        cur.execute("SELECT id,nome FROM ricette WHERE (esperimento IS NULL OR esperimento='' OR twist IS NULL OR twist='') ORDER BY nome LIMIT 3")
        righe=cur.fetchall()
        dt=_t.time()-t0
        return jsonify({"query_secondi": round(dt,2), "prime_3": [{"id":r[0],"nome":r[1]} for r in righe]})
    finally:
        _release_conn(conn)


@bp.route("/admin/lista-ricette-vecchie")
def admin_lista_ricette_vecchie():
    """Ritorna la lista (id, nome, disciplina) delle ricette da rigenerare. Veloce, nessuna AI."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    disc_filtro = request.args.get("disc", "")
    limite = int(request.args.get("limite", "200"))
    conn = _get_conn(); cur = conn.cursor()
    try:
        q = """SELECT id, nome, disciplina FROM ricette
               WHERE (esperimento IS NULL OR esperimento='' OR twist IS NULL OR twist='')"""
        params = []
        if disc_filtro:
            q += " AND disciplina=%s"; params.append(disc_filtro)
        q += " ORDER BY nome LIMIT %s"; params.append(limite)
        cur.execute(q, tuple(params))
        righe = [{"id": r[0], "nome": r[1], "disciplina": r[2]} for r in cur.fetchall()]
        return jsonify({"totale": len(righe), "ricette": righe})
    finally:
        _release_conn(conn)

# ── Rigenerazione ricette in BACKGROUND (aggira il timeout 30s del proxy Railway) ──
_RIGEN_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "corrente": "", "ultimi": []}

def _rigen_worker(disc_filtro, solo_n, solo_senza_numeri=False):
    """Gira in un thread: genera e salva le ricette vecchie SENZA limiti di tempo HTTP.
    solo_senza_numeri=True: rigenera le ricette col campo numeri vuoto (per far ereditare i numeri estratti)."""
    import json as _json
    from db import carica_grafo, _get_conn, _release_conn
    from builder import genera_ricetta
    global _RIGEN_STATO
    try:
        db = carica_grafo()
        conn = _get_conn(); cur = conn.cursor()
        if solo_senza_numeri:
            q = """SELECT id, nome, disciplina FROM ricette
                   WHERE (numeri IS NULL OR numeri::text = '{}' OR numeri::text = 'null')"""
        else:
            q = """SELECT id, nome, disciplina FROM ricette
                   WHERE (esperimento IS NULL OR esperimento='' OR twist IS NULL OR twist='')"""
        params = []
        if disc_filtro:
            q += " AND disciplina=%s"; params.append(disc_filtro)
        q += " ORDER BY nome"
        if solo_n:
            q += " LIMIT %s"; params.append(solo_n)
        cur.execute(q, tuple(params))
        righe = cur.fetchall()
        _release_conn(conn)
        _RIGEN_STATO.update({"attivo": True, "fatte": 0, "totale": len(righe), "errori": 0, "ultimi": []})
        for row in righe:
            rid, nome, disc = row[0], row[1], row[2]
            _RIGEN_STATO["corrente"] = nome
            try:
                ric = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc, lang="it")
                if ric.get("errore") or not ric.get("nome"):
                    _RIGEN_STATO["errori"] += 1; continue
                c2 = _get_conn(); cur2 = c2.cursor()
                try:
                    cur2.execute("""UPDATE ricette SET
                        descrizione=%s, numeri=%s::jsonb, punto_critico=%s, procedimento=%s::jsonb,
                        tecniche=%s::jsonb, fenomeni=%s::jsonb, abbinamenti=%s::jsonb,
                        esperimento=%s, limite=%s, twist=%s,
                        scheda_en=NULL, scheda_es=NULL, nome_en=NULL, nome_es=NULL,
                        procedimento_en=NULL, procedimento_es=NULL, punto_critico_en=NULL, punto_critico_es=NULL,
                        esperimento_en=NULL, esperimento_es=NULL, limite_en=NULL, limite_es=NULL,
                        twist_en=NULL, twist_es=NULL, applicazioni_en=NULL, applicazioni_es=NULL
                        WHERE id=%s""",
                        (ric.get("descrizione",""), _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                         ric.get("punto_critico",""), _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                         _json.dumps(ric.get("tecniche",[]),ensure_ascii=False), _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                         _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                         ric.get("esperimento",""), ric.get("limite",""), ric.get("twist",""), rid))
                    c2.commit()
                    _RIGEN_STATO["fatte"] += 1
                    _RIGEN_STATO["ultimi"] = ([nome] + _RIGEN_STATO["ultimi"])[:5]
                except Exception:
                    c2.rollback(); _RIGEN_STATO["errori"] += 1
                finally:
                    _release_conn(c2)
            except Exception:
                _RIGEN_STATO["errori"] += 1
    finally:
        _RIGEN_STATO["attivo"] = False
        _RIGEN_STATO["corrente"] = ""




def _get_repertorio_ampio():
    """Repertorio classico/regionale/moderno ampio per disciplina (verso le migliaia). Fonte condivisa."""
    return {
    "cucina": ["risotto alla milanese","risotto ai funghi porcini","risotto al nero di seppia","risotto cacio e pepe","carbonara","cacio e pepe","amatriciana","gricia","pasta alla norma","pasta alle vongole","spaghetti aglio olio e peperoncino","pasta al pomodoro","lasagne alla bolognese","tagliatelle al ragu","pappardelle al cinghiale","orecchiette cime di rapa","trofie al pesto","gnocchi di patate","tortellini in brodo","ravioli ricotta e spinaci","paccheri alla genovese","pasta alla puttanesca","brasato al vino rosso","ossobuco","cotoletta alla milanese","vitello tonnato","tagliata di manzo","bollito misto","arrosto di vitello","spezzatino di manzo","polpette al sugo","involtini di carne","scaloppine al limone","saltimbocca alla romana","pollo alla cacciatora","coniglio alla ligure","agnello al forno","porchetta","stracotto","bistecca alla fiorentina","branzino al forno","orata all acqua pazza","polpo alla griglia","calamari ripieni","baccala mantecato","seppie in umido","frittura di paranza","salmone in crosta","tonno scottato","cozze alla marinara","parmigiana di melanzane","caponata siciliana","peperonata","carciofi alla romana","patate al forno","verdure grigliate","insalata di finocchi","cavolfiore gratinato","zucchine trifolate","frittata di verdure","uova strapazzate","besciamella","maionese","pesto alla genovese","sugo di pomodoro","ragu napoletano","brodo di carne","fondo bruno","salsa verde","bagna cauda","minestrone","ribollita","pasta e fagioli","zuppa di lenticchie","vellutata di zucca"],
    "bar": ["negroni","margarita","old fashioned","daiquiri","manhattan","aperol spritz","mojito","whiskey sour","espresso martini","americano","boulevardier","penicillin","gin tonic","cosmopolitan","martini dry","negroni sbagliato","paloma","mai tai","pina colada","caipirinha","moscow mule","dark n stormy","sidecar","french 75","bellini","rossini","tom collins","gimlet","aviation","last word","vieux carre","sazerac","mint julep","bramble","clover club","bee's knees","corpse reviver","white lady","between the sheets","hemingway daiquiri","jungle bird","zombie","singapore sling","long island iced tea","cuba libre","tequila sunrise","bloody mary","irish coffee","god father","rusty nail","white russian","grasshopper","amaretto sour","mimosa","kir royale","clarified milk punch","cordiale al lime","shrub ai frutti rossi","oleo saccharum","vermouth infuso"],
    "panificazione": ["baguette","ciabatta","pane pugliese","focaccia genovese","pizza napoletana","pane in cassetta","panini all olio","grissini","pane integrale","brioche","pane di segale","pane ai cereali","focaccia barese","pizza romana","pizza in teglia","pane toscano","michetta","pane di altamura","carasau","piadina romagnola","tigelle","gnocco fritto","panettone","pandoro","colomba","croissant sfogliato","pain au chocolat","bagel","pretzel","naan","pita","pane hamburger","focaccia con cipolle","schiacciata toscana","pane cafone","biga","poolish","lievito madre","tangzhong"],
    "pasticceria": ["crema pasticcera","pan di spagna","bigne","meringa italiana","frolla","ganache","creme brulee","tiramisu","cannoli siciliani","macaron","panna cotta","bavarese","mousse al cioccolato","sfogliatella riccia","baba","zeppole","cassata siciliana","sacher torte","millefoglie","profiteroles","eclair","saint honore","crostata di frutta","torta della nonna","zuppa inglese","crema chantilly","crema diplomatica","glassa a specchio","pasta choux","pasta sfoglia","frolla sablee","biscotto savoiardo","dacquoise","pralinato","gianduia","caramello salato","confettura","namelaka","cremoso al cioccolato","torta caprese","pastiera napoletana","panforte","cantucci","amaretti","baci di dama"],
    "gelateria": ["gelato fiordilatte","sorbetto al limone","gelato al pistacchio","gelato al cioccolato","stracciatella","granita siciliana","semifreddo","gelato alla vaniglia","gelato alla nocciola","gelato al caffe","sorbetto alla fragola","sorbetto al mango","gelato allo yogurt","gelato al fior di panna","gelato alla crema","gelato al torroncino","gelato alla menta","gelato al cocco","sorbetto ai frutti di bosco","gelato al caramello salato","gelato al tiramisu","spumone","affogato al caffe","base bianca gelato","base gialla gelato","stecco gelato"],
    "caffetteria": ["espresso","cappuccino","caffe filtro V60","moka","cold brew","flat white","latte macchiato","americano","macchiato","cortado","ristretto","lungo","chemex","aeropress","french press","caffe shakerato","marocchino","espresso doppio","caffe d orzo","affogato","irish coffee","caffe leccese","espresso tonic","nitro cold brew"],
    "vino": ["vinificazione in rosso","vinificazione in bianco","spumante metodo classico","macerazione sulle bucce","vino rosato","affinamento in barrique","fermentazione malolattica","vino passito","metodo charmat","vendemmia tardiva","chiarifica","vino novello"],
    "birra": ["american IPA","pilsner","weizen","stout","porter","pale ale","lager","saison","dubbel","tripel","session IPA","barley wine","gose","sour ale","blanche","bitter","brown ale","imperial stout","dry hopping","ammostamento"],
}

# ── Espansione ricette in BACKGROUND (genera tutto il repertorio mancante, no timeout) ──
_ESP_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "corrente": "", "disc": ""}
_REPERTORIO_BG = None  # popolato al primo avvio dall'endpoint

def _esp_worker(repertorio):
    import json as _json, re as _re, unicodedata
    from db import carica_grafo, _get_conn, _release_conn
    from builder import genera_ricetta
    global _ESP_STATO
    try:
        db = carica_grafo()
        # calcolo cosa manca: per ogni disciplina, i piatti non ancora presenti
        conn = _get_conn(); cur = conn.cursor()
        da_fare = []  # (disc, piatto)
        for disc, lista in repertorio.items():
            cur.execute("SELECT LOWER(nome) FROM ricette WHERE disciplina=%s", (disc,))
            gia = set(r[0] for r in cur.fetchall())
            def presente(piatto):
                pl = piatto.lower()
                for g in gia:
                    if pl in g: return True
                    parole = [w for w in pl.split() if len(w) > 3]
                    if parole and all(w in g for w in parole): return True
                return False
            for piatto in lista:
                if not presente(piatto):
                    da_fare.append((disc, piatto))
        _release_conn(conn)
        _ESP_STATO.update({"attivo": True, "fatte": 0, "totale": len(da_fare), "errori": 0})
        for disc, piatto in da_fare:
            _ESP_STATO["disc"] = disc; _ESP_STATO["corrente"] = piatto
            try:
                ric = genera_ricetta(db, f"la ricetta classica di {piatto}", disciplina=disc, lang="it")
                if ric.get("errore") or not ric.get("nome"):
                    _ESP_STATO["errori"] += 1; continue
                nome = ric["nome"]
                slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
                slug = "ric-cls-" + _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
                c2 = _get_conn(); cur2 = c2.cursor()
                try:
                    cur2.execute("""INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                        punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,esperimento,limite,twist)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING""",
                        (slug, nome, disc, ric.get("descrizione",""),
                         _json.dumps(ric.get("ingredienti",[]),ensure_ascii=False),
                         _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                         _json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                         _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                         ric.get("punto_critico",""),
                         _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                         _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                         _json.dumps(ric.get("applicazioni",[]),ensure_ascii=False),
                         ric.get("tempo_prep",""), ric.get("tempo_cottura",""),
                         ric.get("difficolta",""), ric.get("porzioni",""),
                         ric.get("esperimento",""), ric.get("limite",""), ric.get("twist","")))
                    c2.commit(); _ESP_STATO["fatte"] += 1
                except Exception:
                    c2.rollback(); _ESP_STATO["errori"] += 1
                finally:
                    _release_conn(c2)
            except Exception:
                _ESP_STATO["errori"] += 1
    finally:
        _ESP_STATO["attivo"] = False; _ESP_STATO["corrente"] = ""

@bp.route("/admin/espandi-bg")
def admin_espandi_bg():
    """Genera TUTTO il repertorio mancante in background (verso le migliaia). Risponde subito."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _ESP_STATO
    if _ESP_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _ESP_STATO})
    # il repertorio e' quello cablato in admin_espandi_ricette: lo ricostruisco qui identico
    import threading
    # recupero REPERTORIO dalla funzione espandi (stessa fonte) via variabile modulo
    from routes.admin import _get_repertorio_ampio
    t = threading.Thread(target=_esp_worker, args=(_get_repertorio_ampio(),), daemon=True)
    t.start()
    return jsonify({"avviato": True, "nota": "espansione in background, controlla /admin/espandi-bg-stato"})

@bp.route("/admin/espandi-bg-stato")
def admin_espandi_bg_stato():
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_ESP_STATO)

@bp.route("/admin/espandi-ricette")
def admin_espandi_ricette():
    """Espande il repertorio: genera ricette CLASSICHE del mestiere per una disciplina (verso la Bibbia),
    non legate ai buchi ma al repertorio che un pro DEVE conoscere. ?disc= obbligatorio, ?n=1 per timeout.
    Evita i duplicati sui nomi gia presenti. Ogni ricetta nasce IT (traduzioni poi via batch)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    import json as _json, re as _re, unicodedata
    from db import carica_grafo, _get_conn
    from builder import genera_ricetta
    disc = request.args.get("disc", "")
    n = int(request.args.get("n", "1"))
    if not disc:
        return jsonify({"errore": "serve ?disc=cucina|bar|panificazione|..."}), 400
    # repertorio classico per disciplina (i piatti/drink che un pro DEVE padroneggiare)
    REPERTORIO = _get_repertorio_ampio()
    lista = REPERTORIO.get(disc, [])
    if not lista:
        return jsonify({"errore": f"nessun repertorio per {disc}", "disponibili": list(REPERTORIO.keys())}), 400
    db = carica_grafo()
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT LOWER(nome) FROM ricette WHERE disciplina=%s", (disc,))
        gia = set(r[0] for r in cur.fetchall())
        # match STRETTO: un piatto del repertorio è "già presente" solo se il suo nome compare
        # quasi per intero in una ricetta esistente (non basta una parola condivisa come "gelato")
        def gia_presente(piatto):
            pl = piatto.lower()
            for g in gia:
                # il nome repertorio è contenuto quasi tutto nel nome esistente
                if pl in g:
                    return True
                # o il nome esistente inizia con le parole chiave del repertorio
                parole_p = [w for w in pl.split() if len(w) > 3]
                if parole_p and all(w in g for w in parole_p):
                    return True
            return False
        forza = request.args.get("forza", "0") != "0"
        candidati = lista if forza else [x for x in lista if not gia_presente(x)]
        if not candidati:
            return jsonify({"disciplina": disc, "generate": 0, "nota": "repertorio classico gia coperto"})
        generate = []
        saltati = []
        for piatto in candidati[:n]:
            ric = genera_ricetta(db, f"la ricetta classica di {piatto}", disciplina=disc, lang="it")
            if ric.get("errore") or not ric.get("nome"):
                saltati.append({"piatto": piatto, "motivo": ric.get("errore", "nessun nome")})
                continue
            nome = ric["nome"]
            slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
            slug = "ric-cls-" + _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:36]
            if forza: slug = slug + "-v2"
            cur.execute("""INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                    punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,esperimento,limite,twist)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING""",
                (slug, nome, disc, ric.get("descrizione",""),
                 _json.dumps(ric.get("ingredienti",[]),ensure_ascii=False),
                 _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                 _json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                 _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                 ric.get("punto_critico",""),
                 _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                 _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                 _json.dumps(ric.get("applicazioni",[]),ensure_ascii=False),
                 ric.get("tempo_prep",""), ric.get("tempo_cottura",""),
                 ric.get("difficolta",""), ric.get("porzioni",""),
                 ric.get("esperimento",""), ric.get("limite",""), ric.get("twist","")))
            generate.append({"ricetta": nome, "id": slug,
                             "esperimento": bool(ric.get("esperimento")),
                             "limite": bool(ric.get("limite")),
                             "fenomeni": ric.get("fenomeni",[])[:3]})
        conn.commit()
        return jsonify({"disciplina": disc, "generate": len(generate), "dettaglio": generate,
                        "saltati": saltati,
                        "repertorio_restante": len(candidati)-len(generate),
                        "nota": "classici del mestiere. Traduci poi via /admin/traduci-ricette."})
    except Exception as e:
        conn.rollback()
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500
    finally:
        from db import _release_conn
        _release_conn(conn)


@bp.route("/admin/fenomeni-senza-ricetta")
def admin_fenomeni_senza_ricetta():
    """Trova i fenomeni che NON hanno ancora una ricetta che li dimostra (i buchi veri da riempire).
    Guida l'espansione mirata: ogni ricetta nuova deve coprire un fenomeno scoperto, non duplicare."""
    if not _admin_ok(request):
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
            # coperto se l'id O il nome è tra i fenomeni citati (le ricette salvano il NOME)
            if fid in coperti or (fname and fname.strip() in coperti): con+=1
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


# ── Traduzione ricette in BACKGROUND (EN+ES, tutti i campi inclusi i nuovi) ──
_TRAD_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "corrente": "", "lingua": ""}

def _trad_worker():
    """Traduce in background nome/descrizione/procedimento/applicazioni/punto_critico/esperimento/limite/twist
    in EN e ES per tutte le ricette che ne hanno bisogno. Nessun limite di tempo HTTP."""
    import json as _json
    from db import _get_conn, _release_conn
    from ai import _haiku_raw
    global _TRAD_STATO

    def _one(testo, lname):
        if not testo or not str(testo).strip(): return ""
        out = _haiku_raw(f"Translate this Italian cooking text to {lname}. Keep numbers and units. "
                         f"Return ONLY the translation on a single line, no quotes, no notes:\n{testo}")
        return (out or "").strip().strip('"').strip()

    try:
        # conto totale lavoro (ricette x 2 lingue che mancano)
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("""SELECT COUNT(*) FROM ricette WHERE nome_en IS NULL OR esperimento_en IS NULL
                       OR nome_es IS NULL OR esperimento_es IS NULL""")
        _TRAD_STATO.update({"attivo": True, "fatte": 0, "totale": cur.fetchone()[0], "errori": 0})
        _release_conn(conn)

        for lang, lname in [("en","English"), ("es","Spanish")]:
            _TRAD_STATO["lingua"] = lang
            conn = _get_conn(); cur = conn.cursor()
            cur.execute(f"""SELECT id,nome,descrizione,procedimento,applicazioni,punto_critico,esperimento,limite,twist
                            FROM ricette WHERE nome_{lang} IS NULL OR esperimento_{lang} IS NULL ORDER BY id""")
            rows = cur.fetchall()
            _release_conn(conn)
            for row in rows:
                rid, nome, desc, proc, appl, pc, esp, lim, tw = row
                _TRAD_STATO["corrente"] = f"{nome} [{lang}]"
                try:
                    proc_p = proc if isinstance(proc,list) else (_json.loads(proc) if proc else [])
                    appl_p = appl if isinstance(appl,list) else (_json.loads(appl) if appl else [])
                    passi = [step.get("testo","") for step in proc_p if isinstance(step,dict)]
                    passi_join = "\n@@@\n".join(passi)
                    proc_out = _haiku_raw(
                        f"Translate to {lname} each cooking step. Steps separated by a line with @@@. "
                        f"Keep EXACTLY the same number of steps and @@@ separators. Keep numbers/units. "
                        f"Return ONLY the translated steps with @@@ between them:\n\n{passi_join}") or ""
                    passi_tr = [x.strip() for x in proc_out.split("@@@") if x.strip()]
                    if len(passi_tr) != len(passi):
                        passi_tr = [_one(pz, lname) for pz in passi]
                    proc_t = []
                    for i,step in enumerate([s for s in proc_p if isinstance(s,dict)]):
                        st = dict(step)
                        if i < len(passi_tr) and passi_tr[i]: st["testo"]=passi_tr[i]
                        proc_t.append(st)
                    # OTTIMIZZAZIONE: i 6 campi brevi in UNA sola chiamata (era 6) col separatore |||
                    campi_brevi = [nome or "", desc or "", pc or "", esp or "", lim or "", tw or ""]
                    blob = "\n|||\n".join(campi_brevi)
                    tradotto = _haiku_raw(
                        f"Translate to {lname} each text block. Blocks separated by a line with |||. "
                        f"Keep EXACTLY 6 blocks and the ||| separators, same order. Keep numbers/units. "
                        f"If a block is empty leave it empty. Return ONLY the translated blocks with ||| between:\n\n{blob}") or ""
                    parti = [x.strip() for x in tradotto.split("|||")]
                    if len(parti) == 6:
                        nome_t = parti[0] or nome
                        desc_t, pc_t, esp_t, lim_t, tw_t = parti[1], parti[2], parti[3], parti[4], parti[5]
                    else:
                        # fallback: se lo split non torna, traduco singolarmente (raro)
                        nome_t = _one(nome, lname) or nome
                        desc_t = _one(desc, lname) if desc else ""
                        pc_t = _one(pc, lname) if pc else ""
                        esp_t = _one(esp, lname) if esp else ""
                        lim_t = _one(lim, lname) if lim else ""
                        tw_t = _one(tw, lname) if tw else ""
                    appl_t = [_one(a, lname) or a for a in appl_p if isinstance(a,str)][:4]
                    c2 = _get_conn(); cur2 = c2.cursor()
                    try:
                        cur2.execute(f"""UPDATE ricette SET nome_{lang}=%s, scheda_{lang}=%s,
                            procedimento_{lang}=%s::jsonb, applicazioni_{lang}=%s::jsonb, punto_critico_{lang}=%s,
                            esperimento_{lang}=%s, limite_{lang}=%s, twist_{lang}=%s WHERE id=%s""",
                            (nome_t, desc_t, _json.dumps(proc_t,ensure_ascii=False),
                             _json.dumps(appl_t,ensure_ascii=False), pc_t, esp_t, lim_t, tw_t, rid))
                        c2.commit(); _TRAD_STATO["fatte"] += 1
                    except Exception:
                        c2.rollback(); _TRAD_STATO["errori"] += 1
                    finally:
                        _release_conn(c2)
                except Exception:
                    _TRAD_STATO["errori"] += 1
    finally:
        _TRAD_STATO["attivo"] = False
        _TRAD_STATO["corrente"] = ""

@bp.route("/admin/traduci-bg")
def admin_traduci_bg():
    """Avvia la traduzione EN+ES in background (thread). Risponde subito. Stato: /admin/traduci-bg-stato."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _TRAD_STATO
    if _TRAD_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _TRAD_STATO})
    import threading
    t = threading.Thread(target=_trad_worker, daemon=True)
    t.start()
    return jsonify({"avviato": True, "nota": "traduzione in background, controlla /admin/traduci-bg-stato"})

@bp.route("/admin/traduci-bg-stato")
def admin_traduci_bg_stato():
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_TRAD_STATO)

@bp.route("/admin/traduci-ricette")
def admin_traduci_ricette():
    """Traduce nome/procedimento/applicazioni/punto_critico delle ricette in EN e ES via Haiku.
    Ancorato: traduce il testo esistente, non rigenera. Batch con limite/skip."""
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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


@bp.route("/admin/audit-flavor")
def admin_audit_flavor():
    """Audit del flavor network: quanti ingredienti Ahn, quanti composti, copertura abbinamenti,
    e quanti nomi sono ancora 'sporchi' (inglesi/laboratorio non tradotti)."""
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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



# ── REVISIONE PROSA (qualità testi) — rilegge e pulisce i campi testuali delle ricette ──
# MANTIENE voce e numeri, sistema solo errori di prosa/punteggiatura/parole sciatte.
# Usa provider gratuiti (Mistral/Gemini). Background (AI su 361 ricette = lungo).
_REVISIONE_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "campioni": []}

def _revisiona_testo(testo, tipo, nome_ricetta, usa_openai=False):
    """Rilegge UN campo testuale e lo pulisce. Ritorna il testo corretto o l'originale se fallisce."""
    import ai_gateway as GW
    if not testo or len(testo.strip()) < 10:
        return testo
    prompt = (
        "Sei un editor di testi gastronomici in italiano. Correggi SOLO gli errori di prosa, punteggiatura, "
        "scelta delle parole e scorrevolezza in questo testo. REGOLE FERREE:\n"
        "- NON cambiare i NUMERI (temperature, tempi, percentuali, rapporti): restano IDENTICI.\n"
        "- NON riscrivere da zero: mantieni la voce diretta e concreta (tono 'collega al banco').\n"
        "- NON aggiungere né togliere informazioni: solo pulire la forma.\n"
        "- NON usare virgolette attorno alla risposta. Rispondi SOLO col testo corretto, nient'altro.\n"
        f"\nTesto ({tipo}) della ricetta '{nome_ricetta}':\n{testo}"
    )
    try:
        if usa_openai:
            out = GW._gpt_chat(prompt, max_tokens=500)
        else:
            out = GW.route_free(prompt, max_tokens=500)
        if out and len(out.strip()) >= len(testo.strip()) * 0.5:  # sanity: non deve dimezzare il testo
            return out.strip().strip('"')
    except Exception:
        pass
    return testo

def _revisione_worker(solo_n, usa_openai=False):
    from db import carica_grafo, _get_conn, _release_conn
    global _REVISIONE_STATO
    try:
        db = carica_grafo()
        conn = _get_conn(); cur = conn.cursor()
        q = "SELECT id, nome, descrizione, punto_critico, esperimento, limite, twist FROM ricette ORDER BY nome"
        if solo_n:
            q += f" LIMIT {int(solo_n)}"
        cur.execute(q)
        righe = cur.fetchall()
        _release_conn(conn)
        _REVISIONE_STATO.update({"attivo": True, "fatte": 0, "totale": len(righe), "errori": 0, "campioni": []})
        for r in righe:
            rid, nome = r[0], r[1]
            campi = {"descrizione": r[2], "punto_critico": r[3], "esperimento": r[4], "limite": r[5], "twist": r[6]}
            nuovi = {}
            for tipo, testo in campi.items():
                corretto = _revisiona_testo(testo, tipo, nome, usa_openai)
                if corretto and corretto != testo:
                    nuovi[tipo] = corretto
            if nuovi:
                sets = ", ".join(f"{k}=%s" for k in nuovi)
                vals = list(nuovi.values()) + [rid]
                conn2 = _get_conn(); cur2 = conn2.cursor()
                cur2.execute(f"UPDATE ricette SET {sets} WHERE id=%s", vals)
                conn2.commit(); _release_conn(conn2)
                if len(_REVISIONE_STATO["campioni"]) < 5:
                    _REVISIONE_STATO["campioni"].append({"ricetta": nome, "campi_corretti": list(nuovi.keys())})
            _REVISIONE_STATO["fatte"] += 1
    except Exception as e:
        _REVISIONE_STATO["errori"] += 1
    finally:
        _REVISIONE_STATO["attivo"] = False

@bp.route("/admin/revisiona-prosa")
def admin_revisiona_prosa():
    """Rilegge e pulisce la prosa dei testi ricetta (voce e numeri invariati). ?n=3 per provare su poche."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _REVISIONE_STATO
    if _REVISIONE_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _REVISIONE_STATO})
    import threading
    solo_n = request.args.get("n", "0")
    usa_openai = request.args.get("openai", "0") != "0"
    t = threading.Thread(target=_revisione_worker,
                         args=(int(solo_n) if solo_n.isdigit() and solo_n!="0" else None, usa_openai), daemon=True)
    t.start()
    return jsonify({"avviato": True, "provider": "openai" if usa_openai else "gratuiti",
                    "nota": "revisione prosa in background, controlla /admin/revisiona-prosa-stato"})

@bp.route("/admin/revisiona-prosa-stato")
def admin_revisiona_prosa_stato():
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_REVISIONE_STATO)


# ── ABBINAMENTI BEVANDE: genera vino/birra (col PERCHÉ) per le ricette di cibo che non li hanno ──
_ABBINA_STATO = {"attivo": False, "fatte": 0, "totale": 0, "errori": 0, "campioni": []}

def _abbina_worker(solo_n, usa_openai=False):
    from db import carica_grafo, _get_conn, _release_conn
    import ai_gateway as GW
    global _ABBINA_STATO
    try:
        db = carica_grafo()
        conn = _get_conn(); cur = conn.cursor()
        # solo CIBO (cucina/pasticceria/panificazione) senza vino_birra
        q = """SELECT id, nome, disciplina, descrizione FROM ricette
               WHERE disciplina IN ('cucina','pasticceria','panificazione')
               AND (vino_birra IS NULL OR vino_birra::text = '' OR vino_birra::text = '{}' OR vino_birra::text = 'null')
               ORDER BY nome"""
        if solo_n:
            q += f" LIMIT {int(solo_n)}"
        cur.execute(q)
        righe = cur.fetchall()
        _release_conn(conn)
        _ABBINA_STATO.update({"attivo": True, "fatte": 0, "totale": len(righe), "errori": 0, "campioni": []})
        for r in righe:
            rid, nome, disc, desc = r[0], r[1], r[2], (r[3] or "")
            prompt = (
                f"Sei un sommelier tecnico. Per il piatto '{nome}' ({disc}), proponi UN abbinamento vino e UN "
                f"abbinamento birra, ciascuno col PERCHÉ FISICO/PERCETTIVO (affinità o contrasto: tannini che "
                f"reggono il grasso, bollicine che puliscono, note tostate che richiamano la Maillard, ecc.). "
                f"Sii concreto: indica un vitigno/tipo preciso, non 'un vino rosso'.\n"
                f"Descrizione piatto: {desc[:200]}\n"
                f'Rispondi SOLO con JSON: {{"vino":"Nome preciso — perché","birra":"Tipo preciso — perché"}}'
            )
            try:
                out = GW._gpt_chat(prompt, max_tokens=200) if usa_openai else GW.route_free(prompt, max_tokens=200)
                if not out:
                    _ABBINA_STATO["errori"] += 1; _ABBINA_STATO["fatte"] += 1; continue
                # estraggo il JSON
                import re as _re, json as _json
                m = _re.search(r'\{.*\}', out, _re.DOTALL)
                if not m:
                    _ABBINA_STATO["errori"] += 1; _ABBINA_STATO["fatte"] += 1; continue
                vb = _json.loads(m.group(0))
                if not vb.get("vino") or not vb.get("birra"):
                    _ABBINA_STATO["errori"] += 1; _ABBINA_STATO["fatte"] += 1; continue
                conn2 = _get_conn(); cur2 = conn2.cursor()
                cur2.execute("UPDATE ricette SET vino_birra=%s WHERE id=%s",
                             (_json.dumps(vb, ensure_ascii=False), rid))
                conn2.commit(); _release_conn(conn2)
                if len(_ABBINA_STATO["campioni"]) < 5:
                    _ABBINA_STATO["campioni"].append({"ricetta": nome, "vino": vb["vino"][:60], "birra": vb["birra"][:60]})
                _ABBINA_STATO["fatte"] += 1
            except Exception:
                _ABBINA_STATO["errori"] += 1; _ABBINA_STATO["fatte"] += 1
    finally:
        _ABBINA_STATO["attivo"] = False




# ── CREA FENOMENO DEL MONDO (nodi-fenomeno custom coi numeri veri, es. nixtamalizzazione) ──


# ── FORZA FENOMENO DEL MONDO: aggancia il fenomeno giusto alle ricette internazionali ──
# Mappa: parola-chiave nel nome ricetta -> fenomeno del mondo che DEVE agganciare.
_MAPPA_FENOMENO_MONDO = {
    "nixtamalizz": "nixtamalizzazione", "tortilla": "nixtamalizzazione", "tamale": "nixtamalizzazione",
    "pozole": "nixtamalizzazione", "di masa": "nixtamalizzazione", "masa harina": "nixtamalizzazione",
    "wok": "Wok hei", "saltat": "Wok hei", "stir": "Wok hei", "mapo": "Wok hei", "kung pao": "Wok hei",
    "nasi goreng": "Wok hei",
    "miso": "fermentazione enzimatica", "koji": "fermentazione enzimatica", "salsa di soia": "fermentazione enzimatica",
    "amazake": "fermentazione enzimatica", "doenjang": "fermentazione enzimatica",
    "kimchi": "fermentazione lattica", "crauti": "fermentazione lattica", "sauerkraut": "fermentazione lattica",
    "dosa ": "fermentazione lattica", "dosa fermentata": "fermentazione lattica", "idli": "fermentazione lattica", "verdure lacto": "fermentazione lattica",
    "tonkotsu": "Emulsione forzata", "paitan": "Emulsione forzata",
    "kansui": "Kansui", "noodles al kansui": "Kansui", "ramen fatti": "Kansui", "lamian": "Kansui",
    "tadka": "Tadka", "dal": "Tadka", "curry": "Tadka", "tempering": "Tadka",
    "mochi": "Gelatinizzazione del riso glutinoso", "riso glutinoso": "Gelatinizzazione del riso glutinoso",
    "sushi": "Gelatinizzazione del riso glutinoso", "tteokbokki": "Gelatinizzazione del riso glutinoso",
    "zongzi": "Gelatinizzazione del riso glutinoso", "sticky rice": "Gelatinizzazione del riso glutinoso",
    "naan": "Cottura nel tandoor", "tandoor": "Cottura nel tandoor", "tikka": "Cottura nel tandoor",
    "tandoori": "Cottura nel tandoor",
    "brisket": "Barbecue low and slow", "pulled pork": "Barbecue low and slow", "barbecue": "Barbecue low and slow",
    "affumicat": "Barbecue low and slow", "costine": "Barbecue low and slow", "bbq": "Barbecue low and slow",
    "pastor": "nixtamalizzazione",
}



# ── PULISCI FOTO STOCK SBAGLIATE: toglie le foto Pexels/Unsplash/Pixabay, tiene SOLO le foto vere (archivio) ──


# ── PULISCI FOTO ARCHIVIO MAL-MATCHATE: toglie le Cloudinary il cui nome-file NON combacia con la ricetta ──


# ── DIAG FONTI: legge la fonte reale di composti e archi (verifica legale, no Fenaroli) ──
@bp.route("/admin/diag-fonti-legali")
def admin_diag_fonti_legali():
    """Verifica la PROVENIENZA reale di nodi Composto e archi contiene_composto, per la due diligence
    legale. Conta le fonti dichiarate nel campo data e nel campo fonte di ogni composto/arco."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    out = {}
    try:
        # 1. nodi Composto: quante fonti diverse dichiarano nel data JSONB?
        cur.execute("SELECT id, data FROM nodes WHERE type='Composto'")
        comp_fonti = {}
        comp_totale = 0
        esempi_comp = []
        for r in cur.fetchall():
            comp_totale += 1
            d = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
            fonte = (d.get("fonte") or d.get("source") or "NON_DICHIARATA")
            comp_fonti[fonte] = comp_fonti.get(fonte, 0) + 1
            if len(esempi_comp) < 5:
                esempi_comp.append({"id": r[0], "fonte": fonte, "campi_data": list(d.keys())})
        out["composti_totale"] = comp_totale
        out["composti_per_fonte"] = comp_fonti
        out["composti_esempi"] = esempi_comp

        # 2. archi contiene_composto: fonte nel data
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='contiene_composto'")
        out["archi_contiene_composto_totale"] = cur.fetchone()[0]
        cur.execute("SELECT data FROM edges WHERE relation='contiene_composto' LIMIT 500")
        arc_fonti = {}
        for r in cur.fetchall():
            d = r[0] if isinstance(r[0], dict) else (json.loads(r[0]) if r[0] else {})
            fonte = (d.get("fonte") or d.get("source") or "vuoto")
            arc_fonti[fonte] = arc_fonti.get(fonte, 0) + 1
        out["archi_per_fonte_campione500"] = arc_fonti

        # 3. archi abbinamento_aromatico (il backbone Ahn)
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='abbinamento_aromatico'")
        out["archi_abbinamento_aromatico_totale"] = cur.fetchone()[0]

        # 4. cerca QUALSIASI menzione di 'fenaroli' nei dati (nodi e archi)
        cur.execute("SELECT COUNT(*) FROM nodes WHERE LOWER(data::text) LIKE '%fenaroli%'")
        out["nodi_con_fenaroli_nei_dati"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges WHERE LOWER(data::text) LIKE '%fenaroli%'")
        out["archi_con_fenaroli_nei_dati"] = cur.fetchone()[0]

        return jsonify(out)
    finally:
        _release_conn(conn)


# ── APPLICA IL RISOLUTORE IMMAGINI A CASCATA (piatto -> ingrediente -> niente) ──
@bp.route("/admin/applica-immagini-cascata")
def admin_applica_immagini_cascata():
    """Assegna a ogni ricetta l'immagine a cascata: foto-piatto se c'è su Cloudinary,
    altrimenti foto dell'ingrediente principale (dalla mappa piatti canonici), altrimenti niente.
    Regola: meglio la foto dell'ingrediente giusto che una foto-piatto sbagliata."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    from db import _get_conn, _release_conn
    try:
        from risolutore_immagini import risolvi_immagine
        from mappa_piatti import cerca_piatto
    except Exception as e:
        return jsonify({"errore": f"import: {e}"}), 500

    # elenco file su Cloudinary (HTTP diretto, come immagini.py — la libreria non è configurata)
    import urllib.request as _ur, base64 as _b64, json as _json
    lista_file = []
    try:
        cloud = os.environ.get("CLOUDINARY_CLOUD_NAME")
        key = os.environ.get("CLOUDINARY_API_KEY")
        secret = os.environ.get("CLOUDINARY_API_SECRET")
        if not (cloud and key and secret):
            return jsonify({"errore": "credenziali Cloudinary mancanti"}), 500
        url = f"https://api.cloudinary.com/v1_1/{cloud}/resources/image?max_results=500"
        auth = _b64.b64encode(f"{key}:{secret}".encode()).decode()
        req = _ur.Request(url, headers={"Authorization": f"Basic {auth}"})
        with _ur.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        for res in data.get("resources", []):
            pid = res.get("public_id") or ""
            fmt = res.get("format", "jpg")
            if pid:
                lista_file.append(f"{pid}.{fmt}")
    except Exception as e:
        return jsonify({"errore": f"cloudinary: {e}"}), 500

    conn = _get_conn(); cur = conn.cursor()
    stat = {"piatto": 0, "ingrediente": 0, "niente": 0, "totale": 0}
    esempi = []
    try:
        cur.execute("SELECT id, nome, immagine FROM ricette")
        righe = cur.fetchall()
        for rid, nome, img_esistente in righe:
            stat["totale"] += 1
            # ingrediente-chiave dal piatto canonico
            piatto = cerca_piatto(nome)
            chiave = piatto["chiave"] if piatto else None
            # foto-piatto già nel DB (curata) ha priorità
            foto_piatto_db = img_esistente if (img_esistente and "cloudinary" in str(img_esistente)) else None
            r = risolvi_immagine(nome, chiave, foto_piatto_db, lista_file)
            stat[r["tipo"] or "niente"] += 1
            if len(esempi) < 12:
                esempi.append({"nome": nome, "tipo": r["tipo"], "url": (r["url"] or "")[-45:]})
            if not dry and r["url"]:
                cur.execute("UPDATE ricette SET immagine=%s, immagine_autore=%s WHERE id=%s",
                            (r["url"], r["autore"], rid))
        if not dry:
            conn.commit()
        return jsonify({"dry_run": dry, "statistiche": stat, "esempi": esempi})
    finally:
        _release_conn(conn)


# ── DIAG INGREDIENTI PER DOMINIO: conta la materia prima di ogni disciplina ──
@bp.route("/admin/diag-ingredienti-dominio")
def admin_diag_ingredienti_dominio():
    """Conta i nodi Ingrediente per dominio/disciplina, per capire quali discipline hanno
    poca materia prima. Legge il campo domain nel data JSONB."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, data FROM nodes WHERE type='Ingrediente'")
        per_dominio = {}
        senza_dominio = 0
        totale = 0
        esempi_bar = []
        for rid, data in cur.fetchall():
            totale += 1
            d = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dom = d.get("domain") or d.get("dominio") or "NON_ASSEGNATO"
            per_dominio[dom] = per_dominio.get(dom, 0) + 1
            if dom == "NON_ASSEGNATO":
                senza_dominio += 1
            if dom == "bar" and len(esempi_bar) < 15:
                esempi_bar.append(rid)
        return jsonify({
            "totale_ingredienti": totale,
            "per_dominio": dict(sorted(per_dominio.items(), key=lambda x: -x[1])),
            "senza_dominio": senza_dominio,
            "esempi_bar": esempi_bar,
        })
    finally:
        _release_conn(conn)


# ── ASSEGNA DISCIPLINA (domain) a tutti gli ingredienti ──


# ── INSERISCI NUOVA MATERIA PRIMA (bar, gelateria, caffè, pasticceria) come nodi Ingrediente ──
@bp.route("/admin/inserisci-materia-prima")
def admin_inserisci_materia_prima():
    """Aggiunge la materia prima mancante (distillati, bitter, vermouth, sodati, tecnici gelato/pasticceria)
    come nodi Ingrediente con domini[] e scheda (aroma, profilo, applicazioni)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    from db import _get_conn, _release_conn
    try:
        from nuova_materia_prima import MATERIA_PRIMA as _MP1
    except Exception as e:
        return jsonify({"errore": f"import: {e}"}), 500
    try:
        from materia_prima_discipline import MATERIA_PRIMA_DISC as _MP2
    except Exception:
        _MP2 = []
    MATERIA_PRIMA = list(_MP1) + list(_MP2)
    conn = _get_conn(); cur = conn.cursor()
    inseriti = 0; gia_presenti = 0; esempi = []
    try:
        for m in MATERIA_PRIMA:
            cur.execute("SELECT 1 FROM nodes WHERE id=%s", (m["id"],))
            if cur.fetchone():
                gia_presenti += 1
                continue
            data = {
                "domini": m["domini"], "domain": m["domini"][0],
                "aroma": m.get("aroma", ""), "profilo": m.get("profilo", ""),
                "applicazioni": m.get("applicazioni", ""),
                "kind": "ingredient", "visibility": "public",
                "scheda_materia_prima": True,
            }
            if not dry:
                cur.execute(
                    "INSERT INTO nodes (id, name, type, data) VALUES (%s,%s,'Ingrediente',%s) ON CONFLICT (id) DO NOTHING",
                    (m["id"], m["nome"], json.dumps(data, ensure_ascii=False)))
                inseriti += 1
            if len(esempi) < 10:
                esempi.append({"nome": m["nome"], "domini": m["domini"]})
        if not dry:
            conn.commit()
        return jsonify({"dry_run": dry, "da_inserire": len(MATERIA_PRIMA), "inseriti": inseriti,
                        "gia_presenti": gia_presenti, "esempi": esempi})
    finally:
        _release_conn(conn)


# ── DIAG FLAVOUR NETWORK: quanti ingredienti hanno abbinamenti, e potenziale di espansione ──
@bp.route("/admin/diag-flavour")
def admin_diag_flavour():
    """Fotografa il flavour network: quanti ingredienti hanno archi abbinamento_aromatico,
    quanti composti ci sono, e quanti ingredienti Ahn potrebbero essere attivati."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        out = {}
        cur.execute("SELECT count(*) FROM nodes WHERE type='Ingrediente'")
        out["ingredienti_totali"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM nodes WHERE type='Composto'")
        out["composti_totali"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM edges WHERE relation='abbinamento_aromatico'")
        out["archi_abbinamento"] = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM edges WHERE relation='contiene_composto'")
        out["archi_contiene_composto"] = cur.fetchone()[0]
        # quanti ingredienti DISTINTI hanno almeno un abbinamento
        cur.execute("SELECT count(DISTINCT from_id) FROM edges WHERE relation='abbinamento_aromatico'")
        out["ingredienti_con_abbinamenti"] = cur.fetchone()[0]
        # quanti ingredienti hanno composti (potenziali abbinamenti calcolabili)
        cur.execute("SELECT count(DISTINCT from_id) FROM edges WHERE relation='contiene_composto'")
        out["ingredienti_con_composti"] = cur.fetchone()[0]
        # prefissi id ingrediente (per capire le fonti: ahn_, ing-, ecc.)
        cur.execute("""SELECT split_part(id,'_',1) as pfx, count(*) FROM nodes
                       WHERE type='Ingrediente' GROUP BY pfx ORDER BY count(*) DESC LIMIT 10""")
        out["prefissi_id"] = {r[0]: r[1] for r in cur.fetchall()}
        return jsonify(out)
    finally:
        _release_conn(conn)


# ── DIAG: ingredienti nel flavour network ma NON come nodo pieno (da attivare) ──
@bp.route("/admin/diag-ingredienti-mancanti")
def admin_diag_ingredienti_mancanti():
    """Trova gli ingredienti che compaiono negli archi abbinamento_aromatico ma NON hanno
    un nodo Ingrediente pieno. Sono ingredienti VERI (Ahn) da attivare come materia prima."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        # from_id degli archi che non sono nodi Ingrediente
        cur.execute("""
            SELECT DISTINCT e.from_id
            FROM edges e
            WHERE e.relation='abbinamento_aromatico'
            AND e.from_id NOT IN (SELECT id FROM nodes WHERE type='Ingrediente')
            LIMIT 300
        """)
        mancanti = [r[0] for r in cur.fetchall()]
        # esempio: quanti sono, e un campione
        return jsonify({
            "totale_mancanti_campione": len(mancanti),
            "esempi": mancanti[:40],
        })
    finally:
        _release_conn(conn)


# ── ATTIVA INGREDIENTI AHN come nodi pieni (espansione con dati veri) ──
@bp.route("/admin/attiva-ingredienti-ahn")
def admin_attiva_ingredienti_ahn():
    """Attiva come nodi Ingrediente gli ahn_* che hanno abbinamenti nel flavour network
    ma non sono ancora materia prima consultabile. Nome IT dalla mappa, domini dal classificatore.
    Espansione con DATI VERI (composti e abbinamenti già nel grafo), niente inventato."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    from db import _get_conn, _release_conn
    try:
        from nomi_ahn_it import NOMI_IT
    except Exception:
        NOMI_IT = {}
    try:
        from classificatore_domini import classifica
    except Exception:
        classifica = lambda x: ["cucina"]
    conn = _get_conn(); cur = conn.cursor()
    creati = 0; esempi = []; senza_traduzione = 0
    try:
        # conteggio PRIMA
        cur.execute("SELECT count(*) FROM nodes WHERE type='Ingrediente'")
        prima = cur.fetchone()[0]
        # gli ahn_* del flavour network ESISTONO GIÀ come type='Prodotto'.
        # Non vanno inseriti: vanno RI-ETICHETTATI a 'Ingrediente' (con domini), così
        # diventano materia prima consultabile. Sono ingredienti veri con composti.
        # Prendiamo TUTTI gli ahn_ Prodotto che hanno almeno un composto (contiene_composto):
        # anche senza archi Ahn diretti, il flavour network calcola gli abbinamenti dai composti.
        cur.execute("""
            SELECT DISTINCT n.id, n.name, n.data
            FROM nodes n
            JOIN edges e ON e.from_id = n.id
            WHERE e.relation='contiene_composto'
            AND n.id LIKE 'ahn_%'
            AND n.type = 'Prodotto'
        """)
        da_attivare = cur.fetchall()
        for nid, name, data in da_attivare:
            nome_en = nid.replace("ahn_", "").replace("_", " ")
            # se il name è già italiano curato lo tengo, altrimenti traduco
            nome_it = name if (name and name != nome_en) else NOMI_IT.get(nome_en, (name or nome_en.title()))
            if nome_it == nome_en.title():
                senza_traduzione += 1
            domini = classifica(nome_it)
            d = data if isinstance(data, dict) else (json.loads(data) if data else {})
            d["domini"] = domini
            d.setdefault("kind", "ingredient")
            d.setdefault("visibility", "public")
            if not dry:
                cur.execute(
                    "UPDATE nodes SET type='Ingrediente', name=%s, domain=%s, data=%s WHERE id=%s",
                    (nome_it, domini[0], json.dumps(d, ensure_ascii=False), nid))
            if len(esempi) < 20:
                esempi.append({"id": nid, "nome_it": nome_it, "domini": domini})
        if not dry:
            conn.commit()
            cur.execute("SELECT count(*) FROM nodes WHERE type='Ingrediente'")
            dopo = cur.fetchone()[0]
            creati = dopo - prima
        return jsonify({"dry_run": dry, "da_attivare": len(da_attivare), "creati_davvero": creati,
                        "totale_prima": prima, "senza_traduzione_it": senza_traduzione, "esempi": esempi})
    finally:
        _release_conn(conn)


# ── DIAG: che type hanno gli ahn_* del flavour network? ──
@bp.route("/admin/diag-ahn-type")
def admin_diag_ahn_type():
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        # gli ahn_ che sono nel network: esistono come nodo? con che type?
        cur.execute("""
            SELECT n.type, count(*) FROM nodes n
            WHERE n.id LIKE 'ahn_%'
            GROUP BY n.type ORDER BY count(*) DESC
        """)
        per_type = {r[0]: r[1] for r in cur.fetchall()}
        # campione di ahn_ nel network e loro stato
        cur.execute("""
            SELECT DISTINCT e.from_id FROM edges e
            WHERE e.relation='abbinamento_aromatico' AND e.from_id LIKE 'ahn_%'
            LIMIT 5
        """)
        campione = [r[0] for r in cur.fetchall()]
        dettaglio = []
        for cid in campione:
            cur.execute("SELECT id, type, name FROM nodes WHERE id=%s", (cid,))
            row = cur.fetchone()
            dettaglio.append({"id": cid, "esiste": bool(row), "type": row[1] if row else None, "name": row[2] if row else None})
        return jsonify({"ahn_per_type": per_type, "campione_dettaglio": dettaglio})
    finally:
        _release_conn(conn)


# ── DIAG: overlap composti tra due ingredienti (verifica fragola-basilico) ──
@bp.route("/admin/diag-overlap-composti")
def admin_diag_overlap_composti():
    """Verifica quanti composti condividono due ingredienti, calcolandolo da contiene_composto.
    Prova ?a=ahn_strawberry&b=ahn_basil"""
    if not _admin_ok(request):
        return "Forbidden", 403
    a = request.args.get("a", "ahn_strawberry")
    b = request.args.get("b", "ahn_basil")
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        # composti di A
        cur.execute("SELECT to_id FROM edges WHERE relation='contiene_composto' AND from_id=%s", (a,))
        comp_a = set(r[0] for r in cur.fetchall())
        cur.execute("SELECT to_id FROM edges WHERE relation='contiene_composto' AND from_id=%s", (b,))
        comp_b = set(r[0] for r in cur.fetchall())
        comuni = comp_a & comp_b
        # top 5 ingredienti per overlap con A (calcolato dai composti)
        cur.execute("""
            SELECT e2.from_id, count(*) as overlap
            FROM edges e1
            JOIN edges e2 ON e1.to_id = e2.to_id
            WHERE e1.relation='contiene_composto' AND e1.from_id=%s
            AND e2.relation='contiene_composto' AND e2.from_id != %s
            GROUP BY e2.from_id
            ORDER BY overlap DESC LIMIT 20
        """, (a, a))
        top = [{"ingrediente": r[0], "composti_condivisi": r[1]} for r in cur.fetchall()]
        return jsonify({
            "a": a, "b": b,
            "composti_a": len(comp_a), "composti_b": len(comp_b),
            "composti_condivisi_a_b": len(comuni),
            "top_overlap_calcolato_da_composti": top,
        })
    finally:
        _release_conn(conn)


# ── RIEMPI FOTO DA PIXABAY (cascata piatto->ingrediente, verifica tag, upload Cloudinary) ──
@bp.route("/admin/pixabay-riempi")
def admin_pixabay_riempi():
    """Riempie le ricette senza foto pescando da Pixabay. Cascata: prima il piatto, poi
    l'ingrediente principale. Verifica i tag (scarta i mismatch). Scarica e carica su Cloudinary.
    ?dry=1 mostra solo cosa troverebbe; ?dry=0 applica. ?limite=N per lotti."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    limite = int(request.args.get("limite", "30"))
    from db import _get_conn, _release_conn
    try:
        from pixabay_riempi import _pixabay_cerca, _tag_pertinente, _scarica, _carica_cloudinary
    except Exception as e:
        return jsonify({"errore": f"import: {e}"}), 500
    conn = _get_conn(); cur = conn.cursor()
    trovate = 0; caricate = 0; scartate = 0; esempi = []
    try:
        cur.execute("""SELECT id, nome, disciplina, ingredienti FROM ricette
                       WHERE (immagine IS NULL OR immagine='') ORDER BY id LIMIT %s""", (limite,))
        righe = cur.fetchall()
        for r in righe:
            rid = r[0]; nome = r[1]; disc = r[2]; ings = r[3]
            # candidati di ricerca: prima il piatto, poi l'ingrediente principale
            candidati = [nome]
            try:
                lista_ing = ings if isinstance(ings, list) else (json.loads(ings) if ings else [])
                if lista_ing:
                    primo = lista_ing[0]
                    nome_ing = primo.get("nome") if isinstance(primo, dict) else str(primo)
                    if nome_ing:
                        candidati.append(nome_ing)
            except Exception:
                pass
            # cerca in cascata: primo candidato con una foto pertinente vince
            scelto = None; query_vinta = None
            for q in candidati:
                hits = _pixabay_cerca(q)
                for h in hits:
                    if _tag_pertinente(h, q):
                        scelto = h; query_vinta = q
                        break
                if scelto:
                    break
            if not scelto:
                scartate += 1
                continue
            trovate += 1
            autore = scelto.get("user", "Pixabay")
            img_url = scelto.get("largeImageURL") or scelto.get("webformatURL")
            if len(esempi) < 25:
                esempi.append({"ricetta": nome, "query_vinta": query_vinta,
                               "tags": scelto.get("tags", "")[:50], "autore": autore})
            if not dry:
                img_bytes = _scarica(img_url)
                public_id = f"ricetta_{rid}"
                secure_url = _carica_cloudinary(img_bytes, public_id)
                if secure_url:
                    cur.execute("UPDATE ricette SET immagine=%s, immagine_autore=%s WHERE id=%s",
                                (secure_url, f"{autore} / Pixabay", rid))
                    caricate += 1
        if not dry:
            conn.commit()
        return jsonify({"dry_run": dry, "esaminate": len(righe), "trovate": trovate,
                        "caricate": caricate, "scartate_no_match": scartate, "esempi": esempi})
    finally:
        _release_conn(conn)


# ── GENERAZIONE DI MASSA dai piatti canonici (a lotti, riprendibile) ──


# ── GENERAZIONE CANONICI IN BACKGROUND (thread, si autocompleta) ──
_GENCAN_STATO = {"attivo": False, "generate": 0, "bloccate": 0, "errori": 0,
                 "mancano": None, "corrente": "", "disc": ""}

def _gencan_worker(disc_filtro, limite_totale):
    global _GENCAN_STATO
    import re as _re, json as _j2, unicodedata
    from db import carica_grafo, _get_conn, _release_conn
    try:
        import mappa_piatti
        from builder import genera_ricetta
        try:
            from verificatore_ricette import verifica_ricetta
        except Exception:
            verifica_ricetta = None

        def _slug(nome):
            s = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
            return _re.sub(r"[^a-z0-9]+","-",s).strip("-")[:40]

        piatti = mappa_piatti.tutti_i_piatti()
        if disc_filtro:
            piatti = [p for p in piatti if (p.get("disc") or "cucina") == disc_filtro]

        db = carica_grafo()
        fatti = 0
        while True:
            # ricalcolo cosa manca (così è robusto a interruzioni)
            conn = _get_conn(); cur = conn.cursor()
            try:
                cur.execute("SELECT id FROM ricette")
                esistenti = set(r[0] for r in cur.fetchall())
            finally:
                _release_conn(conn)
            da_fare = [p for p in piatti if f"ric-gen-{_slug(p['nome'])}" not in esistenti]
            _GENCAN_STATO["mancano"] = len(da_fare)
            if not da_fare:
                break
            if limite_totale and fatti >= limite_totale:
                break
            p = da_fare[0]
            nome = p["nome"]; disc = p.get("disc") or "cucina"
            _GENCAN_STATO["corrente"] = nome
            try:
                ris = genera_ricetta(db, nome, disciplina=disc, lang="it")
                if ris.get("errore"):
                    _GENCAN_STATO["errori"] += 1; fatti += 1; continue
                if verifica_ricetta:
                    v = verifica_ricetta(ris.get("nome",""), ris.get("ingredienti",[]))
                    if not v.get("ok"):
                        _GENCAN_STATO["bloccate"] += 1; fatti += 1; continue
                rid = f"ric-gen-{_slug(ris.get('nome', nome))}"
                c2 = _get_conn(); cur2 = c2.cursor()
                try:
                    cur2.execute("""
                        INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                            punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING
                    """, (rid, ris.get("nome",nome), disc, ris.get("descrizione",""),
                          _j2.dumps(ris.get("ingredienti",[]),ensure_ascii=False),
                          _j2.dumps(ris.get("fenomeni",[]),ensure_ascii=False),
                          _j2.dumps(ris.get("tecniche",[]),ensure_ascii=False),
                          _j2.dumps(ris.get("numeri",{}),ensure_ascii=False),
                          ris.get("punto_critico",""),
                          _j2.dumps(ris.get("abbinamenti",{}),ensure_ascii=False),
                          _j2.dumps(ris.get("procedimento",[]),ensure_ascii=False),
                          _j2.dumps(ris.get("applicazioni",[]),ensure_ascii=False),
                          ris.get("tempo_prep"), ris.get("tempo_cottura"),
                          ris.get("difficolta",""), ris.get("porzioni","")))
                    c2.commit()
                    _GENCAN_STATO["generate"] += 1
                except Exception:
                    c2.rollback(); _GENCAN_STATO["errori"] += 1
                finally:
                    _release_conn(c2)
            except Exception:
                _GENCAN_STATO["errori"] += 1
            fatti += 1
    finally:
        _GENCAN_STATO["attivo"] = False
        _GENCAN_STATO["corrente"] = ""




# ── PULIZIA IMMAGINI STOCK SBAGLIATE (foodiesfeed agganciate per matching furbo) ──


# ── TEST RETRIEVAL (misura qualità chat senza paywall) ──
@bp.route("/admin/test-retrieval")
def admin_test_retrieval():
    """Misura il retrieval@1 su una batteria di domande da banco, senza il limite trial.
    Per ogni domanda mostra il fenomeno top trovato. Aiuta a monitorare la qualità della chat."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import carica_grafo
    try:
        from retrieval import retrieval_ranked
    except Exception as e:
        return jsonify({"errore": f"retrieval non disponibile: {e}"}), 500

    casi = [
        ("a quanto deve stare l'idratazione della pizza", "idratazione"),
        ("perche la carbonara impazzisce", "emulsione"),
        ("quanto acido in un sour", "acidit"),
        ("a che temperatura coagula l'uovo", "coagula"),
        ("quanto deve diluire un negroni", "diluizione"),
        ("perche il pane non lievita", "lievit"),
        ("a che temperatura si fa il caramello", "caramell"),
        ("quanto sale nell'impasto del pane", "sale"),
        ("come faccio la meringa stabile", "albume"),
        ("perche il gelato e troppo duro", "zucchero"),
    ]
    db = carica_grafo()
    risultati = []; ok = 0
    for domanda, atteso in casi:
        try:
            ranked = retrieval_ranked(db, domanda, topk=3)
            fenomeni = ranked.get("fenomeni", []) if isinstance(ranked, dict) else []
            top_nome = fenomeni[0]["name"] if fenomeni else ""
            top3 = [f["name"] for f in fenomeni[:3]]
            hit = atteso.lower() in (top_nome or "").lower()
            # hit@3: giusto se è nei primi 3 (più realistico)
            hit3 = any(atteso.lower() in (n or "").lower() for n in top3)
            if hit: ok += 1
            risultati.append({"domanda": domanda, "atteso": atteso, "top": top_nome,
                              "top3": top3, "hit@1": hit, "hit@3": hit3})
        except Exception as e:
            risultati.append({"domanda": domanda, "errore": repr(e)[:80]})
    ok3 = sum(1 for r in risultati if r.get("hit@3"))
    return jsonify({
        "retrieval_at_1": f"{ok}/{len(casi)} = {round(100*ok/len(casi))}%",
        "retrieval_at_3": f"{ok3}/{len(casi)} = {round(100*ok3/len(casi))}%",
        "ok": ok, "totale": len(casi), "dettaglio": risultati
    })


# ── AGGIUNGE ALIAS a un fenomeno (per migliorare il retrieval) ──


# ── TEST CHAT COMPLETO (retrieval + risposta, senza paywall) ──
@bp.route("/admin/test-chat")
def admin_test_chat():
    """Testa la chat completa (retrieval + risposta generata) su una domanda, senza limite trial.
    ?domanda=... — per hardtest della qualità delle risposte."""
    if not _admin_ok(request):
        return "Forbidden", 403
    domanda = request.args.get("domanda", "").strip()
    if not domanda:
        return jsonify({"errore": "specifica ?domanda=..."}), 400
    from db import carica_grafo
    from retrieval import retrieval_ranked
    from ai import cerca_contesto, costruisci_prompt, chiedi_mistral
    db = carica_grafo()
    try:
        ranked = retrieval_ranked(db, domanda, topk=3)
        fenomeni = ranked.get("fenomeni", []) if isinstance(ranked, dict) else []
        top_id = fenomeni[0]["id"] if fenomeni else None
        top_nome = fenomeni[0]["name"] if fenomeni else ""
        # costruisco il contesto dal fenomeno top e genero la risposta
        contesto = cerca_contesto(db, top_nome, domanda) if top_nome else ""
        prompt = costruisci_prompt(domanda, contesto, lang="it")
        risposta = chiedi_mistral(prompt)
        return jsonify({
            "domanda": domanda,
            "fenomeno_trovato": top_nome,
            "fenomeno_id": top_id,
            "altri_candidati": [f["name"] for f in fenomeni[1:3]],
            "risposta": risposta,
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[:400]}), 500


@bp.route("/admin/debug-chiedi")
def admin_debug_chiedi():
    """Diagnostica: esegue il percorso di /chiedi e restituisce il traceback vero se crasha."""
    if not _admin_ok(request):
        return "Forbidden", 403
    domanda = request.args.get("domanda", "a che temperatura coagula il tuorlo")
    import traceback
    try:
        from db import carica_grafo
        from retrieval import retrieval_ranked
        from ai import cerca_contesto, costruisci_prompt, chiedi_mistral
        db = carica_grafo()
        ranked = retrieval_ranked(db, domanda, topk=3)
        fenomeni = ranked.get("fenomeni", []) if isinstance(ranked, dict) else []
        top = fenomeni[0]["name"] if fenomeni else ""
        contesto = cerca_contesto(db, top, domanda) if top else None
        prompt = costruisci_prompt(domanda, contesto, lang="it")
        risposta = chiedi_mistral(prompt)
        # ora provo i pezzi aggiunti da me: validazione numero
        import re as _re
        numeri = [f.get("data", {}).get("target", "") or f.get("target", "") for f in (contesto.get("fenomeni", []) if contesto else [])]
        agg = " · ".join([n for n in numeri if n][:2])
        def _valida(s):
            if not s: return ""
            s = str(s).strip()
            if not _re.search(r"\d", s): return ""
            if "→" in s or "·" in s or len(s) > 40: return ""
            if s.count(",") > 1: return ""
            return s
        agg2 = _valida(agg)
        # provo i pezzi che /chiedi fa dopo: log_evento, funnel
        _extra = {}
        try:
            from ai import log_evento
            lid = log_evento("risposta", domanda, risposta[:100] if risposta else "", top or "")
            _extra["log_evento_ok"] = True
        except Exception as _le:
            import traceback as _tb
            _extra["log_evento_errore"] = str(_le)
            _extra["log_evento_trace"] = _tb.format_exc()[:600]
        return jsonify({"ok": True, "fenomeno": top, "risposta_len": len(risposta or ""),
                        "numero_grezzo": agg, "numero_validato": agg2, "extra": _extra})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e), "traceback": traceback.format_exc()[:1500]}), 200






@bp.route("/admin/diagnosi-grafo")
def admin_diagnosi_grafo():
    """Diagnostica la struttura del grafo abbinamenti: quanti archi, quanti composti,
    e se coppie note (fragola-basilico) condividono composti anche senza arco diretto."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    out = {}
    try:
        # 1. quanti archi abbinamento_aromatico?
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='abbinamento_aromatico'")
        out["archi_abbinamento"] = cur.fetchone()[0]
        # 2. quanti archi contiene_composto?
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='contiene_composto'")
        out["archi_contiene_composto"] = cur.fetchone()[0]
        # 3. quanti ingredienti?
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Ingrediente'")
        out["ingredienti"] = cur.fetchone()[0]
        # 4. quanti composti?
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Composto'")
        out["composti"] = cur.fetchone()[0]
        # 5. fragola e basilico: quanti composti ciascuno, e quanti CONDIVISI?
        def composti_di(nome):
            cur.execute("""
                SELECT COUNT(DISTINCT e.to_id) FROM edges e
                JOIN nodes n ON n.id=e.from_id
                WHERE e.relation='contiene_composto' AND lower(n.name)=lower(%s)
            """, (nome,))
            return cur.fetchone()[0]
        out["fragola_composti"] = composti_di("fragola")
        out["basilico_composti"] = composti_di("basilico")
        # composti condivisi fragola-basilico
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT e1.to_id FROM edges e1 JOIN nodes n1 ON n1.id=e1.from_id
                WHERE e1.relation='contiene_composto' AND lower(n1.name)='fragola'
                INTERSECT
                SELECT e2.to_id FROM edges e2 JOIN nodes n2 ON n2.id=e2.from_id
                WHERE e2.relation='contiene_composto' AND lower(n2.name)='basilico'
            ) x
        """)
        out["fragola_basilico_composti_condivisi"] = cur.fetchone()[0]
        # bonus: l'arco abbinamento fragola-basilico esiste? con che overlap?
        cur.execute("""
            SELECT (e.data->>'overlap') FROM edges e
            WHERE e.relation='abbinamento_aromatico'
            AND lower(e.from_id) LIKE '%fragola%' AND lower(e.to_id) LIKE '%basilico%' LIMIT 1
        """)
        arco = cur.fetchone()
        out["arco_diretto_fragola_basilico"] = arco[0] if arco else "NESSUN ARCO"
        return jsonify(out)
    finally:
        _release_conn(conn)


@bp.route("/admin/trova-nodo")
def admin_trova_nodo():
    """Cerca un nodo per nome parziale e mostra id, name, type (per debug traduzioni)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    q = request.args.get("q", "")
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, type FROM nodes WHERE lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s) LIMIT 10",
                    (f"%{q}%", f"%{q}%"))
        rows = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]
        return jsonify({"query": q, "nodi": rows})
    finally:
        _release_conn(conn)


@bp.route("/admin/prova-immagine")
def admin_prova_immagine():
    """Mostra la query costruita e l'URL foto per un piatto (per verificare che non siano inquietanti)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    nome = request.args.get("nome", "")
    disc = request.args.get("disciplina", "cucina")
    from immagini import _query_intelligente, cerca_immagine
    q = _query_intelligente(nome, disc)
    # recupero gli ingredienti e la disciplina VERI della ricetta (per testare la cascata completa)
    _ings = None
    try:
        from db import carica_grafo as _cg
        _dbp = _cg()
        _row = _dbp.execute("SELECT disciplina, ingredienti FROM ricette WHERE lower(nome)=lower(?) LIMIT 1", (nome,)).fetchone()
        if _row:
            disc = (_row["disciplina"] if hasattr(_row, "keys") else _row[0]) or disc
            import json as _ji
            _raw = _row["ingredienti"] if hasattr(_row, "keys") else _row[1]
            _lst = _raw if isinstance(_raw, list) else (_ji.loads(_raw) if _raw else [])
            _ings = []
            for _x in _lst[:4]:
                _n = _x.get("nome") if isinstance(_x, dict) else str(_x)
                if _n: _ings.append(_n)
    except Exception:
        pass
    res = cerca_immagine(nome, disciplina=disc, nome=nome, ingredienti=_ings)
    return jsonify({
        "nome": nome, "disciplina": disc, "query_costruita": q, "ingredienti_usati": _ings,
        "foto_url": res.get("url") if res else None,
        "autore": res.get("autore") if res else None,
        "fonte": res.get("fonte_nome") if res else None,
        "match": res.get("match") if res else "nessuna",
    })


@bp.route("/admin/debug-proposte")
def admin_debug_proposte():
    """Debug: testa il match di una coppia (default fragola+pomodoro) come fa proposte."""
    import os, hmac
    if not _admin_ok(request):
        return "Forbidden", 403
    n1 = request.args.get("a", "fragola")
    n2 = request.args.get("b", "pomodoro")
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    out = {"coppia": [n1, n2]}
    try:
        def _norm_acc(s):
            return (s.lower().replace("à","a").replace("è","e").replace("é","e")
                    .replace("ì","i").replace("ò","o").replace("ù","u").strip())
        s1 = _norm_acc(n1); s2 = _norm_acc(n2)
        # esattamente la query di proposte
        cur.execute("""
            SELECT nt.name, translate(lower(e.to_id),'àèéìòù','aeeiou') AS toid,
                   (e.data->>'overlap')::numeric AS ov,
                   translate(lower(e.from_id),'àèéìòù','aeeiou') AS fromid
            FROM edges e
            JOIN nodes nf ON nf.id = e.from_id
            JOIN nodes nt ON nt.id = e.to_id
            WHERE e.relation='abbinamento_aromatico'
              AND (translate(lower(e.from_id),'àèéìòù','aeeiou') LIKE %s
                OR translate(lower(nf.name),'àèéìòù','aeeiou') LIKE %s)
            LIMIT 25
        """, (f"%{s1.replace(' ','-')}%", f"%{s1}%"))
        righe = cur.fetchall()
        out["archi_di_n1"] = [{"partner_name": r[0], "toid": r[1], "overlap": str(r[2]), "fromid": r[3]} for r in righe]
        # quali matchano n2?
        match = []
        for rname, rtoid, rov, rfrom in righe:
            partner = _norm_acc(rname or "")
            if s2 in partner or s2.replace(" ", "-") in (rtoid or ""):
                match.append({"partner": rname, "overlap": str(rov)})
        out["match_n2"] = match
        # cerca DIRETTA dell'arco n1-n2 in QUALSIASI sistema id, senza limite
        cur.execute("""
            SELECT e.from_id, e.to_id, (e.data->>'overlap')
            FROM edges e
            WHERE e.relation='abbinamento_aromatico'
              AND (
                (translate(lower(e.from_id),'àèéìòù','aeeiou') LIKE %s AND translate(lower(e.to_id),'àèéìòù','aeeiou') LIKE %s)
                OR (translate(lower(e.from_id),'àèéìòù','aeeiou') LIKE %s AND translate(lower(e.to_id),'àèéìòù','aeeiou') LIKE %s)
                OR (lower(e.from_id) LIKE %s AND lower(e.to_id) LIKE %s)
                OR (lower(e.from_id) LIKE %s AND lower(e.to_id) LIKE %s)
              )
            LIMIT 5
        """, (f"%{s1}%", f"%{s2}%", f"%{s2}%", f"%{s1}%",
              "%strawberry%", "%tomato%", "%tomato%", "%strawberry%"))
        out["arco_diretto"] = [{"from": r[0], "to": r[1], "overlap": r[2]} for r in cur.fetchall()]
        return jsonify(out)
    finally:
        _release_conn(conn)




@bp.route("/admin/audit-principi")
def admin_audit_principi():
    """Audit della QUALITÀ dei principi: per ogni fenomeno, il primo principio (quello che
    l'utente legge in cima nella nuova scheda). Serve a trovare i fenomeni col primo-principio
    sbagliato o mancante. ?s=SECRET."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import carica_grafo
    db = carica_grafo()
    fenomeni = db.execute("SELECT id, name, domain FROM nodes WHERE id LIKE 'fen-%%'").fetchall()
    # UNA sola query per tutti gli edge principio (governato_da) + nomi dei principi
    # NOTA: i %% letterali dei LIKE vanno RADDOPPIATI con questo wrapper Postgres.
    edge_rows = db.execute("""
        SELECT e.from_id AS fen, n.name AS princ
        FROM edges e JOIN nodes n ON n.id = e.to_id
        WHERE e.relation = 'governato_da' AND e.from_id LIKE 'fen-%%'
    """).fetchall()
    # mappa fenomeno -> lista principi
    mappa = {}
    for r in edge_rows:
        mappa.setdefault(r["fen"], []).append(r["princ"])
    senza_principio, con_principio, dettaglio = [], 0, []
    for f in fenomeni:
        fid = f["id"]
        lista_prin = mappa.get(fid, [])
        if lista_prin:
            con_principio += 1
        else:
            senza_principio.append({"id": fid, "nome": f["name"]})
        dettaglio.append({"id": fid, "nome": f["name"], "disciplina": f["domain"],
                          "n_principi": len(lista_prin),
                          "primo_principio": lista_prin[0] if lista_prin else None,
                          "tutti_principi": lista_prin})
    return jsonify({
        "totale_fenomeni": len(fenomeni),
        "con_principio": con_principio,
        "senza_principio": len(senza_principio),
        "lista_senza_principio": senza_principio,
        "dettaglio": dettaglio
    })




# ── SPRINT 3 — marca i 31 fenomeni avanzati (orfani) come is_avanzato nel campo data ──
_FENOMENI_AVANZATI = [
    'fen-affinamento-vino','fen-atmosfera-modificata','fen-autolisi','fen-barbecue-low-slow',
    'fen-batch-cocktail','fen-browning-enzimatico','fen-capillarita','fen-clarificazione-cocktail',
    'fen-cold-brew','fen-contaminazione','fen-emulsione-violenta','fen-espansione-termica',
    'fen-fat-washing','fen-infusione','fen-inversione-zucchero','fen-kansui','fen-koji',
    'fen-laminazione','fen-nixtamalizzazione','fen-poolish-biga','fen-riso-glutinoso',
    'fen-sale-impasto','fen-shelf-life','fen-shelf-life-pane','fen-strecker','fen-tadka',
    'fen-tandoor','fen-texture-agents','fen-tissotropia','fen-wok-hei','fen-zona-pericolo',
]

@bp.route("/admin/marca-avanzati")
def admin_marca_avanzati():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    conn = _get_conn()
    try:
        cur = conn.cursor()
        fatti = 0; errori = []
        for fid in _FENOMENI_AVANZATI:
            try:
                cur.execute("SELECT data FROM nodes WHERE id=%s AND type='Fenomeno'", (fid,))
                row = cur.fetchone()
                if not row:
                    errori.append(fid + " (non trovato)")
                    continue
                d = row[0]
                if isinstance(d, str):
                    try: d = json.loads(d)
                    except Exception: d = {}
                if not isinstance(d, dict):
                    d = {}
                d["avanzato"] = True
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(d, ensure_ascii=False), fid))
                fatti += 1
            except Exception as e:
                errori.append(f"{fid}: {e}")
        conn.commit()
        return jsonify({"ok": True, "marcati": fatti, "su_totale": len(_FENOMENI_AVANZATI),
                        "errori": errori})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)


# ── Genera didattica in BATCH: esperimento + quiz per i fenomeni (anti-allucinazione sui numeri) ──


# ── BATCH API: genera quiz per i fenomeni ancora scoperti, a metà prezzo (asincrono) ──


@bp.route("/admin/batch-quiz-raccogli")
def admin_batch_quiz_raccogli():
    """Controlla lo stato del batch; se 'ended', salva i quiz risultanti nel DB."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    batch_id = request.args.get("batch_id", "")
    if not batch_id:
        return jsonify({"errore": "batch_id mancante"}), 400
    import ai_gateway as GW, re as _re
    try:
        stato = GW.batch_stato(batch_id)
        if stato.get("processing_status") != "ended":
            return jsonify({"ok": True, "stato": stato.get("processing_status"),
                            "counts": stato.get("request_counts"), "nota": "non ancora pronto, riprova"})
        results_url = stato.get("results_url")
        if not results_url:
            return jsonify({"errore": "results_url mancante"}), 500
        risultati = GW.batch_risultati(results_url)
        conn = _get_conn(); cur = conn.cursor()
        salvati = 0
        for r in risultati:
            if r.get("result", {}).get("type") != "succeeded":
                continue
            fid = r.get("custom_id", "")
            msg = r.get("result", {}).get("message", {})
            testo = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text")
            testo = _re.sub(r"```json|```", "", testo).strip()
            m = _re.search(r"\{.*\}", testo, _re.DOTALL)
            if not m: continue
            try:
                qj = json.loads(m.group(0))
                dom = qj.get("domanda", ""); opz = qj.get("opzioni", []); ins = qj.get("insight", "")
                if dom and len(opz) >= 2:
                    # recupero disciplina del fenomeno
                    cur.execute("SELECT domain FROM nodes WHERE id=%s", (fid,))
                    _dr = cur.fetchone(); disc = _dr[0] if _dr else ""
                    cur.execute("SELECT 1 FROM quiz WHERE fenomeno_id=%s AND tipo='fenomeno'", (fid,))
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO quiz (fenomeno_id, disciplina, tipo, difficolta, domanda, opzioni, risposta_corretta, insight_didattico) "
                            "VALUES (%s,%s,'fenomeno','base',%s,%s,%s,%s)",
                            (fid, disc, dom, json.dumps(opz, ensure_ascii=False), opz[0], ins))
                        salvati += 1
            except Exception:
                pass
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "salvati": salvati, "totale_risultati": len(risultati)})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


# ── NORMALIZZAZIONE FENOMENI: consolida il contenuto in uno schema unico (via i fallback) ──


# ── PULIZIA NOMI RICETTE: via l'AI slop ("Rivisitato", "Classico" superfluo) ──


# ── MODELLO MADRE/FIGLIA: schema + generazione varianti (briefing OpenAI) ──
@bp.route("/admin/setup-madre-figlia")
def admin_setup_madre_figlia():
    """Aggiunge le colonne per il modello madre/figlia. Le 454 esistenti diventano madri.
    Idempotente. Non rompe nulla (colonne nuove con default)."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS recipe_type TEXT DEFAULT 'madre'")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS parent_recipe_id TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS variante_di TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ricette_parent ON ricette(parent_recipe_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ricette_type ON ricette(recipe_type)")
        # le esistenti senza type diventano madri
        cur.execute("UPDATE ricette SET recipe_type='madre' WHERE recipe_type IS NULL")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM ricette WHERE recipe_type='madre'")
        madri = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "madri": madri, "messaggio": "schema madre/figlia pronto"})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"errore": str(e)}), 500






# ── ITALIAN KNOWLEDGE LAYER: ingredienti italiani che ereditano il profilo molecolare da Ahn ──
# Livello 2/3 sopra il grafo Ahn (Livello 4). NON tocca la chimica: mappa il nome italiano al padre.
_ITALIAN_LAYER = [
    # (id_italiano, nome_display, padre_ahn_nome, categoria, dicitura)
    ("ing-it-fiori-di-zucca", "Fiori di zucca", "squash", "ortaggio", ""),
    ("ing-it-peperone-crusco", "Peperone crusco", "bell_pepper", "ortaggio", "IGP Senise"),
    ("ing-it-nduja", "'Nduja", "pork", "salume", "Calabria"),
    ("ing-it-colatura-di-alici", "Colatura di alici", "anchovy", "condimento", "Cetara"),
    ("ing-it-friarielli", "Friarielli", "broccoli", "ortaggio", "Campania"),
    ("ing-it-guanciale", "Guanciale", "pork", "salume", ""),
    ("ing-it-parmigiano-dop", "Parmigiano Reggiano DOP", "parmesan", "formaggio", "DOP"),
    ("ing-it-pecorino-romano-dop", "Pecorino Romano DOP", "pecorino", "formaggio", "DOP"),
    ("ing-it-san-marzano-dop", "Pomodoro San Marzano DOP", "tomato", "ortaggio", "DOP"),
    ("ing-it-mozzarella-bufala-dop", "Mozzarella di Bufala DOP", "mozzarella", "formaggio", "DOP Campana"),
    ("ing-it-gorgonzola-dop", "Gorgonzola DOP", "blue cheese", "formaggio", "DOP"),
    ("ing-it-culatello", "Culatello di Zibello DOP", "ham", "salume", "DOP"),
    ("ing-it-bottarga", "Bottarga di muggine", "roe", "condimento", "Sardegna"),
    ("ing-it-cime-di-rapa", "Cime di rapa", "turnip", "ortaggio", "Puglia"),
    ("ing-it-radicchio-treviso", "Radicchio di Treviso IGP", "chicory", "ortaggio", "IGP"),
    ("ing-it-carciofo-romanesco", "Carciofo Romanesco IGP", "artichoke", "ortaggio", "IGP"),
    ("ing-it-cipolla-tropea", "Cipolla Rossa di Tropea IGP", "onion", "ortaggio", "IGP"),
    ("ing-it-limone-sorrento", "Limone di Sorrento IGP", "lemon", "agrume", "IGP"),
    ("ing-it-pistacchio-bronte", "Pistacchio di Bronte DOP", "pistachio", "frutta secca", "DOP"),
    ("ing-it-nocciola-piemonte", "Nocciola Piemonte IGP", "hazelnut", "frutta secca", "IGP"),
    ("ing-it-castelmagno-dop", "Castelmagno DOP", "cheese", "formaggio", "DOP"),
    ("ing-it-speck-alto-adige", "Speck Alto Adige IGP", "ham", "salume", "IGP"),
    ("ing-it-finocchiona", "Finocchiona IGP", "pork", "salume", "IGP Toscana"),
    ("ing-it-lardo-colonnata", "Lardo di Colonnata IGP", "pork", "salume", "IGP"),
    ("ing-it-provolone-valpadana", "Provolone Valpadana DOP", "cheese", "formaggio", "DOP"),
]

@bp.route("/admin/setup-italian-layer")
def admin_setup_italian_layer():
    """Crea l'Italian Knowledge Layer: ingredienti italiani che ereditano il profilo molecolare
    dal padre Ahn. NON duplica composti: mappa nome_it -> padre_ahn_id."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE nodes ADD COLUMN IF NOT EXISTS padre_ahn_id TEXT")
        created = 0; mappati = 0; nomap = []
        for iid, nome, padre_nome, cat, dicitura in _ITALIAN_LAYER:
            # cerco il padre Ahn: prima per id (ahn_nome), poi per name
            _padre_key = padre_nome.replace(" ", "_")
            cur.execute("""SELECT id FROM nodes WHERE type='Ingrediente'
                           AND (id = %s OR id = %s OR lower(name)=lower(%s) OR lower(name) LIKE lower(%s))
                           ORDER BY (id=%s) DESC LIMIT 1""",
                        ("ahn_"+_padre_key, "ahn_"+padre_nome, padre_nome, "%"+padre_nome+"%", "ahn_"+_padre_key))
            padre = cur.fetchone()
            padre_id = padre[0] if padre else None
            if not padre_id:
                nomap.append((nome, padre_nome)); continue
            mappati += 1
            data = {"nome_it": nome, "categoria": cat, "dicitura": dicitura,
                    "padre_ahn": padre_id, "italian_layer": True}
            cur.execute("""INSERT INTO nodes (id, name, type, data, padre_ahn_id)
                           VALUES (%s,%s,'Ingrediente',%s::jsonb,%s)
                           ON CONFLICT (id) DO UPDATE SET padre_ahn_id=EXCLUDED.padre_ahn_id,
                           data=EXCLUDED.data""",
                        (iid, nome, json.dumps(data, ensure_ascii=False), padre_id))
            created += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "creati": created, "mappati": mappati,
                        "senza_padre": nomap, "totale_layer": len(_ITALIAN_LAYER)})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


# ── KNOWLEDGE LAYER MULTILINGUA (Opzione B): names {it,en,es} sui nodi ingrediente ──
@bp.route("/admin/traduci-ingredienti")
def admin_traduci_ingredienti():
    """Aggiunge names {it,en,es} agli ingredienti Ahn (l'EN è il nome originale). Batch da N.
    Opzione B: un nodo unico multilingua, display_name(locale) sceglie la lingua. ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    from ai import _haiku_raw
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 20)), 40)
    except Exception:
        offset, limit = 0, 20
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # ingredienti Ahn senza traduzione (names non ancora popolato)
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Ingrediente'
                       AND id LIKE 'ahn%%' ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        righe = cur.fetchall()
        if not righe:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "tradotti": 0, "fine": True})
        # preparo il batch: chiedo all'AI le traduzioni IT/ES in un colpo
        nomi_en = []
        for r in righe:
            data = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
            if data.get("names"):  # già tradotto
                continue
            nomi_en.append((r[0], r[1]))
        if not nomi_en:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "tradotti": 0, "gia_fatti": len(righe), "prossimo_offset": offset+limit})
        _lista = "\n".join(f"{i+1}. {n[1]}" for i, n in enumerate(nomi_en))
        prompt = (f"Traduci questi ingredienti alimentari dall'inglese in italiano e spagnolo culinario. "
                  f"Solo il nome dell'ingrediente, niente spiegazioni. Rispondi SOLO JSON:\n"
                  f'{{"t":[{{"n":numero,"it":"...","es":"..."}}]}}\n\n{_lista}')
        raw = (_haiku_raw(prompt, max_tokens=1500) or "").strip()
        raw = _re.sub(r"```json|```", "", raw)
        mm = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if not mm:
            cur.close(); _release_conn(conn)
            return jsonify({"errore": "no_json", "prossimo_offset": offset+limit})
        trad = json.loads(mm.group(0)).get("t", [])
        trad_map = {t.get("n"): t for t in trad if isinstance(t, dict)}
        fatti = 0
        for i, (iid, nome_en) in enumerate(nomi_en):
            t = trad_map.get(i+1, {})
            nome_it = (t.get("it") or nome_en).strip()
            nome_es = (t.get("es") or nome_en).strip()
            cur.execute("SELECT data FROM nodes WHERE id=%s", (iid,))
            d = cur.fetchone()[0]
            d = d if isinstance(d, dict) else (json.loads(d) if d else {})
            d["names"] = {"it": nome_it, "en": nome_en, "es": nome_es}
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(d, ensure_ascii=False), iid))
            fatti += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "tradotti": fatti, "offset": offset,
                        "prossimo_offset": offset + limit,
                        "esempi": [(nomi_en[i][1], trad_map.get(i+1, {}).get("it")) for i in range(min(3, len(nomi_en)))]})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


# ── CONFIDENCE LAYER: livello di evidenza per ogni ingrediente (A verificato/B ereditato/C stima) ──
# Regola congelata: Matter non inventa mai un profilo molecolare. Ogni dato dichiara la sua origine.
_ARCHETIPI_FAMIGLIA = [
    # (parole chiave nel nome, padre archetipo Ahn) - per l'ereditarietà degli orfani
    (("cheese","formagg","caciocavallo","provolone","scamorza","caciotta","pecorino"), "cheese"),
    (("fish","pesce","branzino","orata","spigola","merluzzo","nasello"), "fish"),
    (("shrimp","gamber","scampi","crostace","aragosta"), "shrimp"),
    (("pepper","peperone","peperoncino"), "bell_pepper"),
    (("tomato","pomodor","datterino","ciliegino"), "tomato"),
    (("citrus","agrume","arancia","limone","mandarino","cedro","bergamotto"), "orange"),
    (("apple","mela"), "apple"),
    (("berry","bacca","mirtillo","lampone","mora","ribes"), "berry"),
    (("herb","erba","basilico","prezzemolo","timo","origano","salvia","menta"), "basil"),
    (("pork","maiale","salume","salsiccia","salame","pancetta","guanciale","lardo"), "pork"),
    (("beef","manzo","vitello","bovino"), "beef"),
    (("mushroom","fungo","porcino","champignon"), "mushroom"),
    (("wine","vino"), "wine"),
    (("bread","pane","pizza","focaccia"), "bread"),
    (("nut","noce","nocciola","mandorla","pistacchio","pinolo"), "nut"),
    (("onion","cipolla","scalogno","porro"), "onion"),
]

@bp.route("/admin/setup-confidence-layer")
def admin_setup_confidence():
    """Assegna evidence_level a ogni ingrediente: A (ha composti Ahn), B (eredita da archetipo),
    C (nessun dato). Mappa gli orfani ai padri archetipo per famiglia. ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 200)), 500)
    except Exception:
        offset, limit = 0, 200
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Ingrediente'
                       ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        righe = cur.fetchall()
        if not righe:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        conta = {"A": 0, "B": 0, "C": 0}
        for r in righe:
            iid, nome, data = r[0], r[1], (r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {}))
            # ha già composti reali? (arco contiene_composto)
            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='contiene_composto' LIMIT 1", (iid,))
            ha_composti = cur.fetchone() is not None
            # ha già un padre (Italian Layer)?
            padre_esistente = data.get("padre_ahn") or data.get("names", {}).get("padre")
            if ha_composti:
                livello = "A"; padre = None
            elif padre_esistente:
                livello = "B"; padre = padre_esistente
            else:
                # cerco un archetipo di famiglia dal nome
                nl = (nome or "").lower()
                padre_nome = None
                for chiavi, arch in _ARCHETIPI_FAMIGLIA:
                    if any(k in nl for k in chiavi):
                        padre_nome = arch; break
                if padre_nome:
                    # trovo l'id del padre archetipo (che ha composti)
                    cur.execute("""SELECT n.id FROM nodes n WHERE n.type='Ingrediente'
                                   AND (n.id=%s OR n.id=%s OR lower(n.name)=%s)
                                   AND EXISTS(SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                                   LIMIT 1""", ("ahn_"+padre_nome, padre_nome, padre_nome))
                    pr = cur.fetchone()
                    if pr:
                        livello = "B"; padre = pr[0]
                    else:
                        livello = "C"; padre = None
                else:
                    livello = "C"; padre = None
            data["evidence_level"] = livello
            if padre:
                data["padre_archetipo"] = padre
            conta[livello] += 1
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(data, ensure_ascii=False), iid))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "processati": len(righe), "livelli": conta,
                        "prossimo_offset": offset + limit})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


# ── recipe_ingredients: il PONTE ricetta ↔ ingrediente grafo ↔ composti (la tabella più importante dopo nodes) ──


# ── CONTRATTO VISIVO: hero_prompt per le immagini ricette (briefing OpenAI) ──


# ── FOTO RICETTE: cerca foto vere da Wikimedia Commons (libere) per le ricette senza immagine ──
@bp.route("/admin/cerca-foto-ricette")
def admin_cerca_foto_ricette():
    """Cerca una foto reale (Wikimedia Commons, licenza libera) per le ricette senza immagine,
    usando il nome del piatto. Se trova, salva l'URL. Altrimenti resta il blueprint. ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import urllib.request as _ur, urllib.parse as _up, re as _re
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 15)), 30)
    except Exception:
        offset, limit = 0, 15
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # solo ricette MADRI senza immagine (le figlie ereditano dalla madre)
        cur.execute("""SELECT id, nome FROM ricette
                       WHERE (immagine IS NULL OR immagine='') AND recipe_type='madre'
                       ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        ricette = cur.fetchall()
        if not ricette:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        trovate = 0; esempi = []; errori_rete = 0
        for rid, nome in ricette:
            # nome pulito per la ricerca (tolgo parentesi)
            q = _re.sub(r"\s*\(.*?\)", "", nome).strip()
            try:
                # API Wikimedia Commons: cerco immagini per il nome del piatto
                url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
                       "&gsrsearch=" + _up.quote(q + " food") + "&gsrlimit=1&gsrnamespace=6"
                       "&prop=imageinfo&iiprop=url&iiurlwidth=800")
                req = _ur.Request(url, headers={"User-Agent": "MatterBench/1.0 (food app; contact@matterbench.app)"})
                with _ur.urlopen(req, timeout=12) as r:
                    data = _j.loads(r.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                foto_url = None
                for _pid, page in pages.items():
                    ii = page.get("imageinfo", [{}])
                    if ii and ii[0].get("thumburl"):
                        foto_url = ii[0]["thumburl"]; break
                if foto_url:
                    cur.execute("UPDATE ricette SET immagine=%s, immagine_autore=%s WHERE id=%s",
                                (foto_url, "Wikimedia Commons", rid))
                    trovate += 1
                    if len(esempi) < 3:
                        esempi.append({"nome": nome, "url": foto_url[:60]})
            except Exception as _er:
                errori_rete += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "foto_trovate": trovate, "errori_rete": errori_rete, "su": len(ricette),
                        "esempi": esempi, "prossimo_offset": offset + limit})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


# ── PONTI UNIFICA tra fenomeni (la navigazione "approfondisci" cross-disciplina) ──


# ── INGREDIENT FAMILY (correzione OpenAI #3): famiglia per ogni ingrediente ──
# Usata per retrieval, flavor ranking, sostituzioni, stagionalità, planner. Campo piccolo, ovunque.
_FAMIGLIE_ING = {
    "citrus": ("lemon", "lime", "orange", "grapefruit", "mandarin", "bergamot", "limone", "arancia",
               "pompelmo", "mandarino", "cedro", "clementina"),
    "aged_cheese": ("parmesan", "pecorino", "grana", "gruyere", "cheddar", "gouda", "manchego",
                    "provolone", "parmigiano", "caciocavallo", "asiago", "comte"),
    "fresh_cheese": ("mozzarella", "ricotta", "burrata", "stracchino", "mascarpone", "robiola",
                     "crescenza", "feta", "cottage"),
    "blue_cheese": ("gorgonzola", "roquefort", "stilton", "blue cheese", "erborinato"),
    "leafy_green": ("spinach", "lettuce", "arugula", "chard", "kale", "rocket", "spinaci", "lattuga",
                    "rucola", "bietola", "cavolo", "radicchio", "cime di rapa", "friarielli"),
    "stone_fruit": ("peach", "apricot", "plum", "cherry", "nectarine", "pesca", "albicocca", "prugna",
                    "ciliegia", "susina"),
    "berry": ("strawberry", "raspberry", "blueberry", "blackberry", "currant", "fragola", "lampone",
              "mirtillo", "mora", "ribes"),
    "pome_fruit": ("apple", "pear", "quince", "mela", "pera", "cotogna"),
    "allium": ("onion", "garlic", "shallot", "leek", "chive", "cipolla", "aglio", "scalogno", "porro",
               "erba cipollina"),
    "nightshade": ("tomato", "pepper", "eggplant", "potato", "chili", "pomodoro", "peperone",
                   "melanzana", "patata", "peperoncino"),
    "brassica": ("broccoli", "cauliflower", "cabbage", "brussels", "turnip", "cavolfiore", "broccolo",
                 "verza", "rapa"),
    "root_veg": ("carrot", "beet", "radish", "parsnip", "carota", "barbabietola", "ravanello", "sedano rapa"),
    "mushroom": ("mushroom", "porcini", "champignon", "shiitake", "fungo", "chiodini", "finferli"),
    "red_meat": ("beef", "veal", "lamb", "pork", "manzo", "vitello", "agnello", "maiale", "bovino"),
    "poultry": ("chicken", "turkey", "duck", "pollo", "tacchino", "anatra", "faraona"),
    "cured_meat": ("prosciutto", "salami", "guanciale", "pancetta", "speck", "nduja", "bresaola",
                   "salame", "mortadella", "lardo", "culatello", "coppa"),
    "fish": ("salmon", "tuna", "cod", "bass", "bream", "anchovy", "sardine", "salmone", "tonno",
             "merluzzo", "branzino", "orata", "acciuga", "baccala", "sgombro"),
    "shellfish": ("shrimp", "prawn", "lobster", "crab", "clam", "mussel", "oyster", "gambero",
                  "scampo", "aragosta", "granchio", "vongola", "cozza", "ostrica", "calamaro", "polpo"),
    "herb": ("basil", "parsley", "thyme", "rosemary", "sage", "oregano", "mint", "basilico",
             "prezzemolo", "timo", "rosmarino", "salvia", "origano", "menta", "maggiorana"),
    "spice": ("pepper", "cinnamon", "nutmeg", "clove", "cumin", "saffron", "pepe", "cannella",
              "noce moscata", "chiodo di garofano", "cumino", "zafferano", "paprika", "curry"),
    "nut": ("almond", "hazelnut", "walnut", "pistachio", "pine nut", "mandorla", "nocciola", "noce",
            "pistacchio", "pinolo", "anacardo"),
    "grain": ("wheat", "rice", "corn", "barley", "oat", "rye", "grano", "riso", "mais", "orzo",
              "avena", "segale", "farro", "farina"),
    "wine_spirit": ("wine", "vino", "gin", "vodka", "rum", "whisky", "tequila", "brandy", "vermouth",
                    "campari", "aperol", "liqueur", "grappa"),
    "beer": ("beer", "birra", "ipa", "lager", "stout", "ale", "pilsner"),
    "dairy": ("milk", "cream", "butter", "yogurt", "latte", "panna", "burro"),
    "egg": ("egg", "uovo", "uova", "tuorlo", "albume"),
    "sweetener": ("sugar", "honey", "syrup", "zucchero", "miele", "sciroppo", "glucosio", "malto"),
    "oil_fat": ("oil", "olio", "lard", "strutto", "ghee", "margarine"),
    "coffee": ("coffee", "espresso", "caffe", "cold brew"),
    "chocolate": ("chocolate", "cocoa", "cioccolato", "cacao"),
}

def _famiglia_ingrediente(nome):
    n = (nome or "").lower()
    for fam, chiavi in _FAMIGLIE_ING.items():
        if any(k in n for k in chiavi):
            return fam
    return None



# ── NODE KIND: Ingrediente / Prodotto / Trasformato (correzione OpenAI #2) ──
# Pomodoro=ingrediente, San Marzano DOP=prodotto, Passata=trasformato. Utile a Planner/Menu Builder.






@bp.route("/admin/worker-log")
def admin_worker_log():
    """Legge il log del worker genera-da-serbatoio per capire cosa fallisce."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT ts, testo FROM worker_log ORDER BY id DESC LIMIT 5")
        logs = [{"ts": str(r[0]), "testo": r[1]} for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"log": logs})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/trova-foto-sospette")
def admin_trova_foto_sospette():
    """TUTTO PERFETTO: stacca TUTTE le foto esterne (Pexels/stock non verificabili) e mette
    blueprint ovunque. Zero rischio di foto sbagliate/chirurgiche. Con ?fix=1 applica."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    fix = request.args.get("fix") == "1"
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # conto quante ricette hanno una foto esterna (pexels/wikimedia/foodiesfeed/unsplash)
        cur.execute("""SELECT COUNT(*) FROM ricette WHERE immagine IS NOT NULL
                       AND immagine::text != 'null'
                       AND (immagine::text ILIKE '%pexels%' OR immagine::text ILIKE '%wikimedia%'
                            OR immagine::text ILIKE '%foodiesfeed%' OR immagine::text ILIKE '%unsplash%'
                            OR immagine::text ILIKE '%http%')""")
        con_foto_esterna = cur.fetchone()[0]
        if fix:
            # stacco TUTTE le foto esterne -> il frontend mostrerà il blueprint
            cur.execute("""UPDATE ricette SET immagine = NULL WHERE immagine IS NOT NULL
                           AND immagine::text != 'null'
                           AND (immagine::text ILIKE '%pexels%' OR immagine::text ILIKE '%wikimedia%'
                                OR immagine::text ILIKE '%foodiesfeed%' OR immagine::text ILIKE '%unsplash%'
                                OR immagine::text ILIKE '%http%')""")
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"foto_esterne_trovate": con_foto_esterna, "staccate": fix,
                        "nota": "Tutte le foto esterne staccate → blueprint ovunque. Zero rischio foto sbagliate." if fix
                                else "Aggiungi &fix=1 per staccarle tutte e mettere blueprint."})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/diag-openai")
def admin_diag_openai():
    """Verifica se la chiave OpenAI è configurata e funziona (per la verifica foto con vision)."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    out = {"chiave_presente": bool(key), "prefisso": key[:7] + "..." if key else "NESSUNA"}
    if not key:
        out["nota"] = "Manca OPENAI_API_KEY su Railway. Aggiungila per usare vision (verifica foto) e generazione immagini."
        return jsonify(out)
    # test: la chiave funziona? (chiamata leggera)
    try:
        import urllib.request as ur, json as _j
        req = ur.Request("https://api.openai.com/v1/models",
                         headers={"Authorization": f"Bearer {key}"})
        r = ur.urlopen(req, timeout=15)
        d = _j.loads(r.read().decode())
        modelli = [m["id"] for m in d.get("data", [])]
        out["chiave_valida"] = True
        out["ha_vision"] = any("gpt-4o" in m or "vision" in m for m in modelli)
        out["ha_dalle"] = any("dall-e" in m for m in modelli)
        out["nota"] = "Chiave OK. Posso usarla per verificare le foto (vision) e generare immagini (dall-e)."
    except Exception as e:
        out["chiave_valida"] = False
        out["errore"] = str(e)[:100]
    return jsonify(out)


@bp.route("/admin/verifica-foto-vision")
def admin_verifica_foto_vision():
    """FASE 1: GPT-4o vision GUARDA ogni foto e dice se corrisponde al piatto.
    Tiene le giuste, scarta le sbagliate (la chirurgica sparisce). ?n=quante ?fix=1 per applicare."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "10")), 40)
    fix = request.args.get("fix") == "1"
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return jsonify({"errore": "manca OPENAI_API_KEY"})
    def _url_foto(img):
        # il campo immagine è direttamente l'URL (stringa)
        s = str(img).strip()
        if s.startswith("http"):
            return s
        try:
            d = img if isinstance(img, dict) else json.loads(img)
            return d.get("url", "")
        except Exception:
            return ""
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, nome, immagine FROM ricette
                       WHERE immagine IS NOT NULL AND immagine::text != 'null'
                       AND immagine::text ILIKE '%%http%%' LIMIT %s""", (n,))
        risultati = []; scartate = 0; tenute = 0
        for rid, nome, img in cur.fetchall():
            url = _url_foto(img)
            if not url.startswith("http"):
                continue
            # chiedo a GPT-4o vision se la foto mostra il piatto
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": f"Questa immagine mostra il piatto/bevanda '{nome}' (o un cibo simile e appropriato)? Rispondi SOLO 'SI' o 'NO'. Se mostra qualcosa di NON alimentare (persone, oggetti, medico, chirurgia) rispondi 'NO'."},
                    {"type": "image_url", "image_url": {"url": url}}
                ]}],
                "max_tokens": 5
            }
            try:
                req = ur.Request("https://api.openai.com/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                r = ur.urlopen(req, timeout=25)
                resp = json.loads(r.read().decode())
                if "choices" not in resp or not resp["choices"]:
                    risultati.append({"nome": nome, "errore": "no choices: " + str(resp.get("error",resp))[:60]})
                    continue
                risposta = resp["choices"][0]["message"]["content"].strip().upper()
                giusta = "SI" in risposta or "SÌ" in risposta or "YES" in risposta
                if giusta:
                    tenute += 1
                else:
                    scartate += 1
                    if fix:
                        cur.execute("UPDATE ricette SET immagine = NULL WHERE id = %s", (rid,))
                        conn.commit()
                risultati.append({"nome": nome, "verdetto": "TIENI" if giusta else "SCARTA"})
            except Exception as _e:
                risultati.append({"nome": nome, "errore": str(_e)[:50]})
        cur.close(); conn.close()
        return jsonify({"controllate": len(risultati), "tenute": tenute, "scartate": scartate,
                        "applicato": fix, "dettaglio": risultati})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e)[:120], "traceback": traceback.format_exc()[-400:]})


@bp.route("/admin/diag-formato-foto")
def admin_diag_formato_foto():
    """Vede COME è salvato il campo immagine (per aggiustare la query di verifica)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, nome, immagine FROM ricette WHERE immagine IS NOT NULL AND immagine::text != 'null' LIMIT 5")
        esempi = []
        for rid, nome, img in cur.fetchall():
            esempi.append({"nome": nome, "tipo_py": str(type(img).__name__), "valore": str(img)[:120]})
        cur.close(); conn.close()
        return jsonify({"esempi": esempi})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/verifica-foto-worker")
def admin_verifica_foto_worker():
    """Worker in BACKGROUND: verifica TUTTE le foto con vision, scarta le sbagliate. Gira da solo."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return jsonify({"errore": "manca OPENAI_API_KEY"})

    def _worker():
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("""SELECT id, nome, immagine FROM ricette
                           WHERE immagine IS NOT NULL AND immagine::text != 'null'
                           AND immagine::text ILIKE '%%http%%'""")
            righe = cur.fetchall()
            tenute = scartate = 0
            for rid, nome, img in righe:
                url = str(img).strip()
                if not url.startswith("http"):
                    continue
                payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": [
                    {"type": "text", "text": f"Questa immagine mostra il piatto/bevanda '{nome}' o un cibo appropriato? Rispondi SOLO 'SI' o 'NO'. Se mostra cose NON alimentari (persone, oggetti, medico) rispondi 'NO'."},
                    {"type": "image_url", "image_url": {"url": url}}]}], "max_tokens": 5}
                try:
                    req = ur.Request("https://api.openai.com/v1/chat/completions",
                                     data=json.dumps(payload).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                    r = ur.urlopen(req, timeout=25)
                    resp = json.loads(r.read().decode())
                    if "choices" not in resp or not resp["choices"]:
                        continue
                    risposta = resp["choices"][0]["message"]["content"].strip().upper()
                    if "SI" in risposta or "SÌ" in risposta or "YES" in risposta:
                        tenute += 1
                    else:
                        cur.execute("UPDATE ricette SET immagine = NULL WHERE id = %s", (rid,))
                        conn.commit(); scartate += 1
                except Exception:
                    continue
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"verifica-foto: {tenute} tenute, {scartate} scartate su {len(righe)}",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify({"avviato": True, "nota": "verifica foto in background - controlla worker-log per il risultato"})


@bp.route("/admin/test-dalle")
def admin_test_dalle():
    """Test generazione immagine con gpt-image-1 (verifica che funzioni)."""
    from flask import request, jsonify
    import os, json, urllib.request as ur, urllib.error
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return jsonify({"errore": "manca OPENAI_API_KEY"})
    piatto = request.args.get("piatto", "spaghetti carbonara")
    modello = request.args.get("modello", "gpt-image-1")
    prompt = f"Professional food photography of {piatto}, top view, natural light, restaurant quality, appetizing, no text"
    payload = {"model": modello, "prompt": prompt, "n": 1, "size": "1024x1024"}
    try:
        req = ur.Request("https://api.openai.com/v1/images/generations",
                         data=json.dumps(payload).encode(),
                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        r = ur.urlopen(req, timeout=90)
        d = json.loads(r.read().decode())
        item = d["data"][0]
        # gpt-image-1 ritorna b64_json, dall-e ritorna url
        if item.get("url"):
            return jsonify({"ok": True, "modello": modello, "tipo": "url", "url": item["url"]})
        elif item.get("b64_json"):
            return jsonify({"ok": True, "modello": modello, "tipo": "base64", "lunghezza_b64": len(item["b64_json"])})
        else:
            return jsonify({"ok": True, "modello": modello, "chiavi": list(item.keys())})
    except urllib.error.HTTPError as he:
        try: body = he.read().decode()[:300]
        except: body = str(he)
        return jsonify({"ok": False, "errore_http": he.code, "dettaglio": body})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e)[:200]})


@bp.route("/admin/test-img-bg")
def admin_test_img_bg():
    """Genera immagine in BACKGROUND (evita timeout Railway). Salva esito in worker_log."""
    from flask import request, jsonify
    import os, json, urllib.request as ur, urllib.error, threading, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    piatto = request.args.get("piatto", "carbonara")
    modello = request.args.get("modello", "gpt-image-1")
    def _w():
        esito = ""
        try:
            prompt = f"Professional food photography of {piatto}, top view, natural light, appetizing"
            payload = {"model": modello, "prompt": prompt, "n": 1, "size": "1024x1024"}
            req = ur.Request("https://api.openai.com/v1/images/generations",
                             data=json.dumps(payload).encode(),
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r = ur.urlopen(req, timeout=120)
            d = json.loads(r.read().decode())
            item = d["data"][0]
            if item.get("b64_json"): esito = f"OK b64 len={len(item['b64_json'])}"
            elif item.get("url"): esito = f"OK url={item['url'][:80]}"
            else: esito = f"OK chiavi={list(item.keys())}"
        except urllib.error.HTTPError as he:
            try: esito = f"HTTP {he.code}: {he.read().decode()[:150]}"
            except: esito = f"HTTP {he.code}"
        except Exception as e:
            esito = f"ERR: {str(e)[:120]}"
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"test-img [{modello}] {piatto}: {esito}",))
            conn.commit(); cur.close(); conn.close()
        except: pass
    threading.Thread(target=_w, daemon=True).start()
    return jsonify({"avviato": True, "nota": "generazione in background, controlla worker-log tra 60s"})





@bp.route("/admin/test-foto-una")
def admin_test_foto_una():
    """Genera UNA foto in background, logga ogni step nel worker-log (evita timeout Railway)."""
    from flask import request, jsonify
    import os, json, urllib.request as ur, psycopg2, base64, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    def _log(txt):
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", ("test-foto-step: "+txt,))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass
    def _run():
        try:
            _log("1-inizio generazione")
            prompt = "Professional food photography of spaghetti carbonara, top view, natural light"
            payload = {"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1024x1024"}
            req = ur.Request("https://api.openai.com/v1/images/generations",
                             data=json.dumps(payload).encode(),
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r = ur.urlopen(req, timeout=120)
            d = json.loads(r.read().decode())
            item = d["data"][0]
            b64 = item.get("b64_json")
            if not b64:
                _log("2-NO b64: "+str(list(item.keys()))); return
            img_bytes = base64.b64decode(b64)
            _log(f"2-generata e decodificata {len(img_bytes)} bytes")
            cn = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
            ck = os.environ.get("CLOUDINARY_API_KEY", "")
            cs = os.environ.get("CLOUDINARY_API_SECRET", "")
            _log(f"3-cloudinary vars: name={bool(cn)} key={bool(ck)} secret={bool(cs)}")
            import cloudinary, cloudinary.uploader
            cloudinary.config(cloud_name=cn, api_key=ck, api_secret=cs)
            up = cloudinary.uploader.upload(img_bytes, folder="ricette_ai", public_id="test-carbonara", overwrite=True)
            _log("4-UPLOAD OK: "+str(up.get("secure_url","?"))[:90])
        except Exception as e:
            import traceback
            _log("ERRORE: "+str(e)[:100]+" | "+traceback.format_exc()[-150:])
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"avviato": True, "nota": "controlla worker-log per gli step"})




@bp.route("/admin/conta-punto-critico")
def admin_conta_punto_critico():
    """Conta ESATTAMENTE quante ricette hanno il punto_critico vuoto su tutto il DB."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE punto_critico IS NULL OR TRIM(punto_critico) = ''")
        vuoti = cur.fetchone()[0]
        # per disciplina
        cur.execute("""SELECT disciplina, COUNT(*) FILTER (WHERE punto_critico IS NULL OR TRIM(punto_critico)='') as vuoti,
                       COUNT(*) as tot FROM ricette GROUP BY disciplina ORDER BY vuoti DESC""")
        per_disc = [{"disciplina": r[0], "vuoti": r[1], "tot": r[2]} for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"totale_ricette": tot, "senza_punto_critico": vuoti,
                        "percentuale": round(vuoti/tot*100,1) if tot else 0, "per_disciplina": per_disc})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/test-mistral")
def admin_test_mistral():
    """Testa se chiedi_mistral funziona da solo (per capire perché il worker punto critico genera 0)."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        from ai import chiedi_mistral
        r1 = chiedi_mistral("Qual è il punto critico della carbonara? Una frase.", usa_tools=False)
        r2 = chiedi_mistral("Qual è il punto critico della carbonara? Una frase.", usa_tools=True)
        return jsonify({
            "con_usa_tools_False": (r1[:150] if r1 else "VUOTO"),
            "con_usa_tools_True": (r2[:150] if r2 else "VUOTO"),
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e)[:100], "tb": traceback.format_exc()[-200:]})


@bp.route("/admin/test-builder-pc")
def admin_test_builder_pc():
    """Testa se il builder (genera_ricetta) produce il punto_critico - così so se usarlo per completare le vecchie."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        from db import carica_grafo
        from builder import genera_ricetta
        db = carica_grafo()
        r = genera_ricetta(db, "la ricetta classica di Bagel ai semi", disciplina="panificazione", lang="it")
        return jsonify({
            "ha_punto_critico": bool(r.get("punto_critico")),
            "punto_critico": str(r.get("punto_critico",""))[:150],
            "ha_ingredienti": len(r.get("ingredienti",[])),
        })
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e)[:100], "tb": traceback.format_exc()[-200:]})


@bp.route("/admin/test-provider")
def admin_test_provider():
    """Testa ogni provider AI separatamente per trovare quale è morto (credito/errore)."""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {}
    # Anthropic - con dettaglio 400
    try:
        import os, json as _j, urllib.request as _ur, urllib.error as _ue
        _key = os.environ.get("ANTHROPIC_API_KEY","")
        _payload = {"model":"claude-sonnet-4-5","max_tokens":20,"messages":[{"role":"user","content":"Di solo ciao"}]}
        _req = _ur.Request("https://api.anthropic.com/v1/messages", data=_j.dumps(_payload).encode(),
                           headers={"x-api-key":_key,"anthropic-version":"2023-06-01","content-type":"application/json"})
        try:
            _r = _ur.urlopen(_req, timeout=30)
            _d = _j.loads(_r.read().decode())
            out["anthropic"] = "OK: "+_d.get("content",[{}])[0].get("text","?")[:40]
        except _ue.HTTPError as _he:
            out["anthropic"] = f"HTTP {_he.code}: "+_he.read().decode()[:200]
    except Exception as e:
        out["anthropic"] = "ERR: "+str(e)[:100]
    # OpenAI (gpt chat)
    try:
        import ai_gateway as GW
        r = GW._gpt_chat("Di' solo: ciao", max_tokens=20)
        out["openai_gpt"] = "OK: "+r[:40] if r else "VUOTO"
    except Exception as e:
        out["openai_gpt"] = "ERR: "+str(e)[:80]
    # Mistral
    try:
        import ai_gateway as GW
        r = GW._mistral_call("Di' solo: ciao")
        out["mistral"] = "OK: "+r[:40] if r else "VUOTO"
    except Exception as e:
        out["mistral"] = "ERR: "+str(e)[:80]
    return jsonify(out)


@bp.route("/admin/conta-foto")
def admin_conta_foto():
    """Conta quante ricette hanno foto AI (cloudinary) vs blueprint vs niente."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%cloudinary%%'")
        cloud = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%http%%' AND immagine::text NOT ILIKE '%%cloudinary%%'")
        stock = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%blueprint%%'")
        blueprint = cur.fetchone()[0]
        # per disciplina, quante blueprint
        cur.execute("""SELECT disciplina, COUNT(*) FILTER (WHERE immagine::text ILIKE '%%blueprint%%') bp,
                       COUNT(*) tot FROM ricette GROUP BY disciplina ORDER BY bp DESC""")
        per_disc = [{"disc": r[0], "blueprint": r[1], "tot": r[2]} for r in cur.fetchall() if r[1] > 0]
        cur.close(); conn.close()
        return jsonify({"totale": tot, "foto_ai_cloudinary": cloud, "foto_stock": stock,
                        "blueprint": blueprint, "blueprint_per_disciplina": per_disc})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/diag-fonti-foto")
def admin_diag_fonti_foto():
    """Verifica quali fonti foto (Pexels/Pixabay/Unsplash) sono configurate e rispondono."""
    from flask import request, jsonify
    import os, urllib.request as ur, json as _j
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {}
    # Pexels
    pk = os.environ.get("PEXELS_API_KEY", "")
    out["pexels_key"] = bool(pk)
    out["pexels_prefisso"] = (pk[:8] + "..." + pk[-4:]) if pk else "VUOTA"
    out["pexels_lunghezza"] = len(pk)
    if pk:
        try:
            req = ur.Request("https://api.pexels.com/v1/search?query=pizza&per_page=1",
                             headers={"Authorization": pk.strip(), "User-Agent": "MatterLab/1.0"})
            r = ur.urlopen(req, timeout=15); d = _j.loads(r.read().decode())
            out["pexels_test"] = "OK: " + str(len(d.get("photos", []))) + " foto"
        except Exception as e:
            _det = ""
            try: _det = e.read().decode()[:100]
            except: _det = str(e)[:60]
            out["pexels_test"] = "ERR: " + _det
    # Pixabay
    px = os.environ.get("PIXABAY_API_KEY", "")
    out["pixabay_key"] = bool(px)
    if px:
        try:
            r = ur.urlopen(f"https://pixabay.com/api/?key={px}&q=pizza&per_page=3", timeout=15)
            d = _j.loads(r.read().decode())
            out["pixabay_test"] = "OK: " + str(d.get("totalHits", 0)) + " hits"
        except Exception as e:
            out["pixabay_test"] = "ERR: " + str(e)[:60]
    # Unsplash
    uk = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    out["unsplash_key"] = bool(uk)
    return jsonify(out)


@bp.route("/admin/conta-ricette-complete")
def admin_conta_ricette_complete():
    """Conta ricette con ingredienti/procedimento vuoti (buchi di qualità come i punti critici)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # vedo le colonne
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette'")
        colonne = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        out = {"totale": tot, "colonne": colonne}
        if "ingredienti" in colonne:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE ingredienti IS NULL OR ingredienti::text IN ('[]','null','')")
            out["senza_ingredienti"] = cur.fetchone()[0]
        if "procedimento" in colonne:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE procedimento IS NULL OR TRIM(procedimento)=''")
            out["senza_procedimento"] = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/worker-continuo")
def admin_worker_continuo():
    """Worker che processa ricette vuote + traduzioni in CICLO finché non finisce, auto-rilanciandosi.
    Un solo avvio, gira fino a completamento (rispettando i limiti)."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403

    def _ciclo():
        try:
            from db import carica_grafo
            from builder import genera_ricetta
            db = carica_grafo()
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            totale_fatti = 0
            for _batch in range(50):  # max 50 batch per avvio (poi Railway può killare, si rilancia)
                cur.execute("""SELECT id, nome, disciplina FROM ricette
                               WHERE ingredienti IS NULL OR ingredienti::text IN ('[]','null','') LIMIT 5""")
                righe = cur.fetchall()
                if not righe:
                    break  # finito le ricette vuote
                for rid, nome, disc in righe:
                    try:
                        r = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc or "cucina", lang="it")
                        ing = r.get("ingredienti", [])
                        proc = r.get("procedimento", "")
                        if ing:
                            cur.execute("UPDATE ricette SET ingredienti=%s, procedimento=%s WHERE id=%s",
                                        (json.dumps(ing), json.dumps(proc) if not isinstance(proc, str) else proc, rid))
                            conn.commit(); totale_fatti += 1
                    except Exception:
                        conn.rollback()
                    time.sleep(1)
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"worker-continuo: {totale_fatti} ricette completate in questo avvio",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_ciclo, daemon=True).start()
    return jsonify({"avviato": True, "nota": "worker continuo: processa fino a 250 ricette per avvio. Rilancia se serve."})


@bp.route("/admin/traduci-continuo")
def admin_traduci_continuo():
    """Worker continuo traduzioni: traduce ricette in EN/ES in cicli finché non finisce."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    lang = request.args.get("lang", "en")

    def _ciclo(lang):
        try:
            from ai import chiedi_mistral
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            # verifico se esiste la colonna traduzioni
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette'")
            colonne = [r[0] for r in cur.fetchall()]
            col_trad = "traduzioni" if "traduzioni" in colonne else None
            if not col_trad:
                cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", ("traduci-continuo: nessuna colonna traduzioni",))
                conn.commit(); cur.close(); conn.close(); return
            fatti = 0
            for _batch in range(40):
                cur.execute(f"""SELECT id, nome FROM ricette
                                WHERE (traduzioni IS NULL OR NOT (traduzioni ? %s)) LIMIT 5""", (lang,))
                righe = cur.fetchall()
                if not righe:
                    break
                for rid, nome in righe:
                    try:
                        t = chiedi_mistral(f"Translate to {lang} only the dish name, nothing else: {nome}", usa_tools=False)
                        if t and len(t.strip()) > 1:
                            cur.execute(f"""UPDATE ricette SET traduzioni =
                                COALESCE(traduzioni,'{{}}'::jsonb) || jsonb_build_object(%s, %s) WHERE id=%s""",
                                (lang, t.strip()[:100], rid))
                            conn.commit(); fatti += 1
                    except Exception:
                        conn.rollback()
                    time.sleep(1)
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"traduci-continuo [{lang}]: {fatti} tradotte",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_ciclo, args=(lang,), daemon=True).start()
    return jsonify({"avviato": True, "lingua": lang})


@bp.route("/admin/trova-quiz-anisakis")
def admin_trova_quiz_anisakis():
    """Trova le domande quiz che parlano di anisakis/abbattimento pesce (dato sicurezza da verificare)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # cerco nelle tabelle quiz
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%%quiz%%' OR table_name LIKE '%%domand%%'")
        tabelle = [r[0] for r in cur.fetchall()]
        risultati = {"tabelle_quiz": tabelle}
        for t in tabelle:
            try:
                # vedo le colonne della tabella
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}'")
                colT = [r[0] for r in cur.fetchall()]
                # costruisco la WHERE solo sulle colonne testuali che esistono
                cond = []
                for col in colT:
                    if col in ('domanda','insight','spiegazione','risposta','opzioni','testo','corretta'):
                        cond.append(f"{col}::text ILIKE '%%anisakis%%' OR {col}::text ILIKE '%%abbatti%%' OR {col}::text ILIKE '%%-35%%' OR {col}::text ILIKE '%%853%%'")
                if not cond:
                    continue
                cur.execute(f"SELECT * FROM {t} WHERE {' OR '.join(cond)} LIMIT 5")
                cols = [d[0] for d in cur.description]
                righe = [dict(zip(cols, r)) for r in cur.fetchall()]
                if righe: risultati[t] = [{k: str(v)[:250] for k, v in r.items()} for r in righe]
            except Exception as _e:
                conn.rollback()
                risultati[t + "_err"] = str(_e)[:50]
        cur.close(); conn.close()
        return jsonify(risultati)
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/foto-definitiva")
def admin_foto_definitiva():
    """Worker foto DEFINITIVO: per ogni ricetta senza foto vera, cerca su Pexels con query precisa,
    VERIFICA con vision (no insegne/persone/sbagliate), se fallisce genera con gpt-image-1. Salva su Cloudinary."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, urllib.parse, base64
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "6")), 12)
    key_ai = os.environ.get("OPENAI_API_KEY", "")
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    cn = os.environ.get("CLOUDINARY_CLOUD_NAME", ""); ck = os.environ.get("CLOUDINARY_API_KEY", ""); cs = os.environ.get("CLOUDINARY_API_SECRET", "")

    def _vision_ok(img_url, nome):
        """gpt-4o-mini verifica: è una foto del piatto (no insegne/persone/loghi)?"""
        try:
            payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": [
                {"type": "text", "text": f"Questa immagine mostra il PIATTO/CIBO '{nome}' pronto da mangiare? Rispondi SOLO SI o NO. Rispondi NO se e' un'insegna, un logo, un ristorante, persone, un menu scritto, o cibo diverso."},
                {"type": "image_url", "image_url": {"url": img_url}}]}], "max_tokens": 5}
            req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                             headers={"Authorization": f"Bearer {key_ai}", "Content-Type": "application/json"})
            r = ur.urlopen(req, timeout=25); d = json.loads(r.read().decode())
            risp = d["choices"][0]["message"]["content"].strip().upper()
            return "SI" in risp
        except Exception:
            return False

    def _cerca_pexels(nome):
        try:
            q = urllib.parse.quote(nome + " dish food plated")
            req = ur.Request(f"https://api.pexels.com/v1/search?query={q}&per_page=5&orientation=landscape",
                             headers={"Authorization": pexels_key, "User-Agent": "MatterLab/1.0"})
            r = ur.urlopen(req, timeout=15); d = json.loads(r.read().decode())
            return [ph["src"]["large"] for ph in d.get("photos", [])]
        except Exception:
            return []

    def _genera_ai(nome):
        try:
            prompt = f"Professional food photography of {nome}, plated dish, top view, natural light, appetizing, no text, no people, no signage"
            payload = {"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1024x1024"}
            req = ur.Request("https://api.openai.com/v1/images/generations", data=json.dumps(payload).encode(),
                             headers={"Authorization": f"Bearer {key_ai}", "Content-Type": "application/json"})
            r = ur.urlopen(req, timeout=120); d = json.loads(r.read().decode())
            return d["data"][0].get("b64_json")
        except Exception:
            return None

    def _upload_cloud(img_bytes, rid):
        try:
            import cloudinary, cloudinary.uploader
            cloudinary.config(cloud_name=cn, api_key=ck, api_secret=cs)
            up = cloudinary.uploader.upload(img_bytes, folder="ricette_ok", public_id=str(rid), overwrite=True)
            return up.get("secure_url")
        except Exception:
            return None

    def _w(n):
        fatte_pexels = fatte_ai = 0
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("""SELECT id, nome FROM ricette
                           WHERE immagine IS NULL OR immagine::text = 'null'
                           OR immagine::text ILIKE '%%blueprint%%' LIMIT %s""", (n,))
            for rid, nome in cur.fetchall():
                url_finale = None
                # 1. prova Pexels + vision
                for foto_url in _cerca_pexels(nome):
                    if _vision_ok(foto_url, nome):
                        cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s", (foto_url, rid))
                        conn.commit(); url_finale = foto_url; fatte_pexels += 1; break
                # 2. se Pexels fallisce, genera con AI
                if not url_finale and key_ai:
                    b64 = _genera_ai(nome)
                    if b64:
                        cloud_url = _upload_cloud(base64.b64decode(b64), rid)
                        if cloud_url:
                            cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s", (cloud_url, rid))
                            conn.commit(); fatte_ai += 1
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"foto-definitiva: {fatte_pexels} pexels + {fatte_ai} AI",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": "foto definitiva: Pexels+vision, fallback AI. Controlla worker-log."})


@bp.route("/admin/mostra-quiz-anisakis")
def admin_mostra_quiz_anisakis():
    """Mostra la domanda anisakis COMPLETA (tutti i campi) per correggere il dato sbagliato."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT * FROM quiz WHERE domanda ILIKE '%%abbattut%%' OR domanda ILIKE '%%anisak%%' OR domanda ILIKE '%%pesce%%'")
        cols = [d[0] for d in cur.description]
        righe = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"trovate": len(righe), "domande": [{k: str(v)[:300] for k, v in r.items()} for r in righe]})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/quiz-22-completo")
def admin_quiz_22():
    """Mostra il quiz id 22 (anisakis) con TUTTI i campi completi per la correzione."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT * FROM quiz WHERE id = '22' OR id = 22")
        cols = [d[0] for d in cur.description]
        righe = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"quiz": [{k: str(v)[:500] for k, v in r.items()} for r in righe]})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/stato-foto")
def admin_stato_foto():
    """Stato foto in tempo reale: quante hanno foto vera (verificata) vs blueprint. Per controllo onesto."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%http%%'")
        con_foto = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%cloudinary%%' OR immagine::text ILIKE '%%ricette_ok%%'")
        foto_ai = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%pexels%%'")
        foto_pexels = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine IS NULL OR immagine::text = 'null' OR immagine::text ILIKE '%%blueprint%%'")
        senza = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"totale": tot, "con_foto_vera": con_foto, "di_cui_AI": foto_ai,
                        "di_cui_pexels": foto_pexels, "senza_foto_o_blueprint": senza,
                        "percentuale_con_foto": round(con_foto/tot*100, 1) if tot else 0})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/verifica-foto-esistenti")
def admin_verifica_foto_esistenti():
    """Verifica con VISION le foto GIÀ assegnate (dal filtro vecchio): quelle sbagliate (insegne, piatti
    diversi) le rifà con Pexels+vision o AI. Ogni foto controllata visivamente."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, urllib.parse, base64
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "6")), 12)
    key_ai = os.environ.get("OPENAI_API_KEY", "")
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    cn = os.environ.get("CLOUDINARY_CLOUD_NAME",""); ck=os.environ.get("CLOUDINARY_API_KEY",""); cs=os.environ.get("CLOUDINARY_API_SECRET","")

    _vision_err=[]
    def _vision_ok(img_url, nome):
        try:
            payload={"model":"gpt-4o-mini","messages":[{"role":"user","content":[
                {"type":"text","text":f"Questa immagine mostra il PIATTO/CIBO '{nome}' pronto? Rispondi SOLO SI o NO. NO se e' un'insegna, logo, ristorante, persone, menu scritto, o cibo diverso."},
                {"type":"image_url","image_url":{"url":img_url}}]}],"max_tokens":5}
            req=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(payload).encode(),
                headers={"Authorization":f"Bearer {key_ai}","Content-Type":"application/json"})
            r=ur.urlopen(req,timeout=25); d=json.loads(r.read().decode())
            return "SI" in d["choices"][0]["message"]["content"].strip().upper()
        except Exception as _e:
            if "429" in str(_e):
                try:
                    import time as _t2; _t2.sleep(20)
                    r=ur.urlopen(req,timeout=25); d=json.loads(r.read().decode())
                    return "SI" in d["choices"][0]["message"]["content"].strip().upper()
                except Exception as _e2:
                    if len(_vision_err)<2: _vision_err.append("retry: "+str(_e2)[:50])
                    return None
            if len(_vision_err)<2: _vision_err.append(str(_e)[:70])
            return None

    def _cerca_pexels(nome):
        try:
            q=urllib.parse.quote(nome+" dish food plated")
            req=ur.Request(f"https://api.pexels.com/v1/search?query={q}&per_page=5&orientation=landscape",
                headers={"Authorization":pexels_key,"User-Agent":"MatterLab/1.0"})
            r=ur.urlopen(req,timeout=15); d=json.loads(r.read().decode())
            return [ph["src"]["large"] for ph in d.get("photos",[])]
        except Exception: return []

    def _genera_ai(nome):
        try:
            payload={"model":"gpt-image-1","prompt":f"Professional food photography of {nome}, plated dish, top view, natural light, appetizing, no text, no people, no signage","n":1,"size":"1024x1024"}
            req=ur.Request("https://api.openai.com/v1/images/generations",data=json.dumps(payload).encode(),
                headers={"Authorization":f"Bearer {key_ai}","Content-Type":"application/json"})
            r=ur.urlopen(req,timeout=120); d=json.loads(r.read().decode())
            return d["data"][0].get("b64_json")
        except Exception: return None

    def _upload(img_bytes, rid):
        try:
            import cloudinary, cloudinary.uploader
            cloudinary.config(cloud_name=cn,api_key=ck,api_secret=cs)
            return cloudinary.uploader.upload(img_bytes,folder="ricette_ok",public_id=str(rid),overwrite=True).get("secure_url")
        except Exception: return None

    def _w(n):
        ok=0; sostituite=0
        try:
            conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
            # foto esistenti NON ancora verificate (non su ricette_ok, che è la cartella verificata)
            cur.execute("""SELECT id, nome, immagine FROM ricette
                           WHERE immagine::text ILIKE '%%http%%'
                           AND immagine::text NOT ILIKE '%%ricette_ok%%'
                           ORDER BY random() LIMIT %s""",(n,))
            _righe=cur.fetchall()
            _nrighe=len(_righe)
            _errv=[]
            import time as _tm
            for _i,(rid,nome,img) in enumerate(_righe):
                if _i>0: _tm.sleep(8)  # pausa anti rate-limit tra le verifiche vision
                url=img if isinstance(img,str) else ""
                if not str(url).startswith("http"):
                    _errv.append("url non http: "+str(url)[:30]); continue
                verdetto=_vision_ok(str(url),nome)
                if verdetto is None: _errv.append("vision None")
                if verdetto is True:
                    # foto giusta: la marco come verificata (sposto logica: aggiungo tag ok non serve, la lascio)
                    ok+=1
                elif verdetto is False:
                    # foto SBAGLIATA: la rifaccio
                    nuova=None
                    for furl in _cerca_pexels(nome):
                        if _vision_ok(furl,nome):
                            cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s",(furl,rid)); conn.commit(); nuova=furl; break
                    if not nuova and key_ai:
                        b64=_genera_ai(nome)
                        if b64:
                            cu=_upload(base64.b64decode(b64),rid)
                            if cu: cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s",(cu,rid)); conn.commit()
                    sostituite+=1
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            _et=(" | vision_err: "+_vision_err[0]) if _vision_err else ((" | "+_errv[0]) if _errv else "")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)",(f"verifica-foto-esistenti: {ok} ok, {sostituite} rifatte su {_nrighe} righe{_et}",))
            conn.commit(); cur.close(); conn.close()
        except Exception: pass
    threading.Thread(target=_w,args=(n,),daemon=True).start()
    return jsonify({"avviato":True,"nota":"verifica VISIVA delle foto esistenti, rifà le sbagliate"})




@bp.route("/admin/foto-pexels-diretta")
def admin_foto_pexels_diretta():
    """Worker SEMPLICE senza vision: cerca su Pexels col nome preciso del piatto, prende la foto migliore.
    Nessuna chiamata AI = nessun rate-limit. Query precisa = foto giuste. Rifà TUTTE le foto."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, urllib.parse
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "20")), 40)
    solo_mancanti = request.args.get("solo_mancanti") == "1"
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "")

    # parole che indicano una foto SBAGLIATA nella descrizione/alt (insegne, persone, ecc.)
    BLOCCA = ["sign", "restaurant exterior", "logo", "storefront", "people", "portrait", "man ", "woman ", "chef ", "kitchen staff", "waiter", "menu board", "building", "facade"]

    def _pexels(nome):
        """cerca su Pexels col nome del piatto, ritorna la migliore foto food."""
        try:
            # query precisa: nome piatto + food/dish
            q = urllib.parse.quote(f"{nome} food dish")
            req = ur.Request(f"https://api.pexels.com/v1/search?query={q}&per_page=8&orientation=landscape",
                             headers={"Authorization": pexels_key, "User-Agent": "MatterLab/1.0"})
            r = ur.urlopen(req, timeout=15); d = json.loads(r.read().decode())
            for ph in d.get("photos", []):
                alt = (ph.get("alt", "") or "").lower()
                # scarto se l'alt indica insegna/persone/edificio
                if any(bad in alt for bad in BLOCCA):
                    continue
                return ph["src"]["large"]
            # se tutte scartate, prendo la prima comunque (meglio una foto food generica che un'insegna)
            if d.get("photos"):
                return d["photos"][0]["src"]["large"]
        except Exception:
            pass
        return None

    def _pixabay(nome):
        try:
            q = urllib.parse.quote(f"{nome} food")
            r = ur.urlopen(f"https://pixabay.com/api/?key={pixabay_key}&q={q}&image_type=photo&category=food&per_page=5&orientation=horizontal", timeout=15)
            d = json.loads(r.read().decode())
            if d.get("hits"):
                return d["hits"][0].get("largeImageURL") or d["hits"][0].get("webformatURL")
        except Exception:
            pass
        return None

    def _w(n):
        fatte = 0; pex = pix = 0
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            # PRIMA le ricette senza foto (sistematico, non random - così copre tutto)
            _solo_wiki = request.args.get("solo_wikimedia") == "1"
            if _solo_wiki:
                cur.execute("""SELECT id, nome FROM ricette WHERE immagine::text ILIKE '%%wik%%' ORDER BY id LIMIT %s""", (n,))
            else:
                cur.execute("""SELECT id, nome FROM ricette
                           WHERE immagine IS NULL OR immagine::text='null' OR immagine::text ILIKE '%%blueprint%%'
                           ORDER BY id LIMIT %s""", (n,))
            _r = cur.fetchall()
            if not _r and not solo_mancanti and not _solo_wiki:
                # finite le mancanti: rifà le foto vecchie non verificate (le potenzialmente sbagliate)
                cur.execute("""SELECT id, nome FROM ricette
                               WHERE immagine::text ILIKE '%%http%%' AND immagine::text NOT ILIKE '%%ricette_ok%%'
                               ORDER BY id LIMIT %s""", (n,))
                _r = cur.fetchall()
            # (uso _r invece di ri-fetchare)
            for rid, nome in _r:
                url = _pexels(nome)
                if url: pex += 1
                elif pixabay_key:
                    url = _pixabay(nome)
                    if url: pix += 1
                if url:
                    cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s", (url, rid))
                    conn.commit(); fatte += 1
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"foto-pexels-diretta: {fatte} foto ({pex} pexels, {pix} pixabay)",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": "foto da Pexels/Pixabay SENZA vision (no rate-limit). Query precisa."})






@bp.route("/admin/conta-traduzioni")
def admin_conta_traduzioni():
    """Conta quante ricette hanno le traduzioni EN/ES (per sapere se il worker traduzioni ha finito)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette'")
        colonne = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        out = {"totale": tot}
        if "nome_en" in colonne:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE nome_en IS NOT NULL AND nome_en != ''")
            out["con_nome_en"] = cur.fetchone()[0]
        if "scheda_en" in colonne:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE scheda_en IS NOT NULL AND scheda_en::text NOT IN ('null','')")
            out["con_scheda_en"] = cur.fetchone()[0]
        if "nome_es" in colonne:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE nome_es IS NOT NULL AND nome_es != ''")
            out["con_nome_es"] = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/categorizza-portate")
def admin_categorizza_portate():
    """Categorizza le ricette per PORTATA (primo/secondo/contorno/dolce/antipasto/drink) con regole
    sul nome. Prima passata veloce senza AI (no rate-limit). I casi ambigui restano 'da_rivedere'."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "300")), 1300)

    REGOLE = {
        "primo": ["risotto", "pasta", "spaghetti", "penne", "lasagn", "gnocch", "zuppa", "minestr", "vellutata", "pappardelle", "pici", "cavatelli", "strozzapreti", "maltagliati", "pasta e", "crema di", "passato", "brodo", "ramen", "pho", "laksa", "congee", "jok", "porridge", "ragù", "genovese", "gricia", "norma", "puttanesca", "aglio e olio", "cacio e pepe",
                  "tagliatelle", "ravioli", "tortell", "cannellon", "carbonara", "amatriciana", "cacio", "gramigna",
                  "orecchiette", "trofie", "linguine", "bucatini", "paccheri", "fusilli", "maccheron", "polenta", "riso "],
        "secondo": ["filetto", "bistecca", "arrosto", "spezzatino", "scaloppin", "cotoletta", "brasato", "stufato",
                    "polpett", "involtini", "roast", "tagliata", "salmone", "branzino", "orata", "baccal", "merluzzo",
                    "tonno", "gamber", "cozze", "vongole", "polpo", "calamar", "seppie", "frittura", "pollo", "tacchino",
                    "coniglio", "agnello", "abbacchio", "maiale", "vitello", "manzo", "ossobuco", "cacciatora", "scottadito"],
        "contorno": ["insalata", "verdure", "patate", "spinaci", "friggitelli", "melanzane grigliate", "zucchine grigliate",
                     "cicoria", "broccoli", "cavolfiore", "fagiolini", "carciofi", "caponata", "parmigiana", "ratatouille"],
        "dolce": ["torta", "crostata", "tiramis", "crema", "budino", "panna cotta", "gelato", "sorbetto", "semifreddo",
                  "cheesecake", "muffin", "biscott", "cannol", "sfogliatell", "babà", "profiterol", "bignè", "millefoglie",
                  "cioccolat", "mousse", "dolce", "dessert", "zabaion", "zeppol", "struffoli", "pastiera", "delizia"],
        "antipasto": ["bruschett", "crostini", "tartare", "carpaccio", "antipasto", "tagliere", "fritt", "supplì",
                      "arancin", "crocchett", "frittatina", "montanara", "crostone", "vol-au-vent"],
        "base": ["besciamella", "fondo di", "fondo bruno", "salsa madre", "salsa verde", "sugo di", "ragù di", "brodo di", "fumetto", "court bouillon", "roux", "maionese", "olandese", "demi-glace", "salsa di pomodoro", "passata", "pesto", "hummus", "salamoia", "marinatura", "impasto base", "pasta madre", "lievito madre", "biga", "poolish", "mash per"],
        "drink": ["cocktail", "spritz", "negroni", "martini", "margarita", "mojito", "daiquiri", "sour", "punch",
                  "americano", "manhattan", "old fashioned", "gin tonic", "aperol", "bellini", "caffè", "espresso",
                  "cappuccino", "tè ", "tisana", "frappè", "smoothie", "centrifuga"],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # aggiungo la colonna portata se non esiste
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette' AND column_name='portata'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE ricette ADD COLUMN portata TEXT")
            conn.commit()
        cur.execute("SELECT id, nome, disciplina FROM ricette WHERE portata IS NULL OR portata='' OR portata='da_rivedere' LIMIT %s", (n,))
        righe = cur.fetchall()
        conteggi = {}
        for rid, nome, disc in righe:
            nl = (nome or "").lower()
            portata = None
            # bar/caffetteria/birra/vino -> drink
            if disc in ("bar", "caffetteria", "cocktail", "caffè", "birra", "vino"):
                portata = "drink"
            else:
                for p, chiavi in REGOLE.items():
                    if any(k in nl for k in chiavi):
                        portata = p; break
            # recupero per disciplina se il nome non ha dato risultato
            if not portata:
                if disc in ("pasticceria", "dolce", "gelateria"):
                    portata = "dolce"
                elif disc in ("pane", "panificazione", "lievitato"):
                    portata = "pane"
            if not portata:
                portata = "da_rivedere"
            cur.execute("UPDATE ricette SET portata=%s WHERE id=%s", (portata, rid))
            conteggi[portata] = conteggi.get(portata, 0) + 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"categorizzate": len(righe), "per_portata": conteggi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/esempi-da-rivedere")
def admin_esempi_da_rivedere():
    """Mostra esempi di ricette da_rivedere con la loro disciplina, per capire come categorizzarle."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT nome, disciplina FROM ricette WHERE portata='da_rivedere' LIMIT 30")
        esempi = [{"nome": r[0], "disciplina": r[1]} for r in cur.fetchall()]
        # conteggio da_rivedere per disciplina
        cur.execute("SELECT disciplina, COUNT(*) FROM ricette WHERE portata='da_rivedere' GROUP BY disciplina ORDER BY COUNT(*) DESC")
        per_disc = {r[0]: r[1] for r in cur.fetchall()}
        cur.close(); conn.close()
        return jsonify({"esempi": esempi, "da_rivedere_per_disciplina": per_disc})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/categorizza-ai")
def admin_categorizza_ai():
    """Categorizza i da_rivedere (cucina ambigui) con AI, batch piccolo + pause anti rate-limit."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "10")), 15)
    key = os.environ.get("ANTHROPIC_API_KEY", "")

    _err = []
    def _classifica(nome):
        try:
            prompt = (f"Classifica il piatto '{nome}' in UNA portata tra: antipasto, primo, secondo, "
                      f"contorno, dolce, pane, drink. Rispondi SOLO con la parola, minuscolo, niente altro.")
            payload = {"model": "claude-sonnet-4-5", "max_tokens": 10,
                       "messages": [{"role": "user", "content": prompt}]}
            req = ur.Request("https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode(),
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            r = ur.urlopen(req, timeout=25); d = json.loads(r.read().decode())
            risp = d["content"][0]["text"].strip().lower()
            valide = ["antipasto", "primo", "secondo", "contorno", "dolce", "pane", "drink"]
            for v in valide:
                if v in risp:
                    return v
        except Exception as e:
            if len(_err) < 2: _err.append(str(e)[:60])
        return None

    def _w(n):
        fatti = 0
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("SELECT id, nome FROM ricette WHERE portata='da_rivedere' LIMIT %s", (n,))
            for rid, nome in cur.fetchall():
                p = _classifica(nome)
                if p:
                    cur.execute("UPDATE ricette SET portata=%s WHERE id=%s", (p, rid))
                    conn.commit(); fatti += 1
                time.sleep(5)  # pausa anti rate-limit
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"categorizza-ai: {fatti}"+(" | "+_err[0] if _err else ""),))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": "categorizza da_rivedere con AI, pause 5s"})


@bp.route("/admin/conta-portate")
def admin_conta_portate():
    """Conta le ricette per portata."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COALESCE(portata,'(vuoto)'), COUNT(*) FROM ricette GROUP BY portata ORDER BY COUNT(*) DESC")
        out = {r[0]: r[1] for r in cur.fetchall()}
        cur.close(); conn.close()
        return jsonify({"per_portata": out})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/conta-fonti-foto")
def admin_conta_fonti_foto():
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%pexels%%'"); pexels = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%wik%%'"); wiki = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%cloudinary%%' OR immagine::text ILIKE '%%ricette_ok%%'"); cloud = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"pexels_sicure": pexels, "wikimedia_arischio": wiki, "cloudinary_ai": cloud})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/rifai-wikimedia")
def admin_rifai_wikimedia():
    """Worker DEDICATO: rifà le foto Wikimedia con Pexels. Log dettagliato."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, urllib.parse
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "20")), 50)
    pexels_key = os.environ.get("PEXELS_API_KEY", "")

    def _pexels(nome):
        try:
            q = urllib.parse.quote(f"{nome} food dish")
            req = ur.Request(f"https://api.pexels.com/v1/search?query={q}&per_page=5&orientation=landscape",
                             headers={"Authorization": pexels_key, "User-Agent": "MatterLab/1.0"})
            r = ur.urlopen(req, timeout=15); d = json.loads(r.read().decode())
            BLOCCA = ["sign", "restaurant exterior", "logo", "storefront", "people", "portrait", "building", "facade"]
            for ph in d.get("photos", []):
                alt = (ph.get("alt", "") or "").lower()
                if any(bad in alt for bad in BLOCCA):
                    continue
                return ph["src"]["large"]
            if d.get("photos"):
                return d["photos"][0]["src"]["large"]
        except Exception:
            pass
        return None

    def _w(n):
        fatte = 0; nessuna = 0; err = ""
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("SELECT id, nome FROM ricette WHERE immagine::text ILIKE '%%wik%%' ORDER BY id LIMIT %s", (n,))
            righe = cur.fetchall()
            for rid, nome in righe:
                url = _pexels(nome)
                if url:
                    cur.execute("UPDATE ricette SET immagine=%s WHERE id=%s", (url, rid))
                    conn.commit(); fatte += 1
                else:
                    nessuna += 1
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"rifai-wikimedia: {fatte} rifatte, {nessuna} senza foto pexels, su {len(righe)}",))
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            try:
                conn2 = psycopg2.connect(os.environ["DATABASE_URL"]); c2 = conn2.cursor()
                c2.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"rifai-wikimedia ERRORE: {str(e)[:80]}",))
                conn2.commit(); c2.close(); conn2.close()
            except Exception:
                pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True})


@bp.route("/admin/diag-duplicati-ingredienti")
def admin_diag_duplicati_ingredienti():
    """Conta i duplicati ingredienti (stesso nome, id diversi) per capire la pulizia necessaria."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti totali
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        tot = cur.fetchone()[0]
        # nomi duplicati (stesso name lowercase, più id)
        cur.execute("""SELECT LOWER(name) nome, COUNT(*) c FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name) HAVING COUNT(*) > 1 ORDER BY c DESC LIMIT 20""")
        dup = [{"nome": r[0], "copie": r[1]} for r in cur.fetchall()]
        cur.execute("""SELECT COUNT(*) FROM (SELECT LOWER(name) FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name) HAVING COUNT(*) > 1) t""")
        n_nomi_dup = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"totale_nodi": tot, "nomi_con_duplicati": n_nomi_dup, "top_duplicati": dup})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/mappa-grafo")
def admin_mappa_grafo():
    """Mappa completa del grafo: unici veri, fonti (ahn vs italiano), struttura abbinamenti."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        out = {}
        # ingredienti per prefisso id (fonte)
        cur.execute("""SELECT
            COUNT(*) FILTER (WHERE id LIKE 'ahn_%%') ahn,
            COUNT(*) FILTER (WHERE id LIKE 'ing-%%') ita,
            COUNT(*) FILTER (WHERE id LIKE 'ai_%%') ai,
            COUNT(*) FILTER (WHERE id LIKE 'fis_%%') fis,
            COUNT(*) FILTER (WHERE id LIKE 'prod-%%') prod,
            COUNT(*) tot
            FROM nodes WHERE type IN ('Ingrediente','Prodotto')""")
        r = cur.fetchone()
        out["ingredienti_per_fonte"] = {"ahn": r[0], "italiani": r[1], "ai": r[2], "fisici": r[3], "prodotti": r[4], "totale": r[5]}
        # unici per nome (dopo dedup teorico)
        cur.execute("""SELECT COUNT(DISTINCT LOWER(name)) FROM nodes WHERE type IN ('Ingrediente','Prodotto')""")
        out["nomi_unici"] = cur.fetchone()[0]
        # composti
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Composto'")
        out["composti"] = cur.fetchone()[0]
        # archi per relazione
        cur.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC")
        out["archi_per_relazione"] = {r[0]: r[1] for r in cur.fetchall()}
        # quanti ingredienti HANNO composti collegati vs quanti no
        cur.execute("""SELECT COUNT(DISTINCT from_id) FROM edges WHERE relation='contiene_composto'""")
        out["ingredienti_con_composti"] = cur.fetchone()[0]
        # esempio struttura abbinamento (un arco)
        cur.execute("SELECT from_id, to_id, data FROM edges WHERE relation='abbinamento_aromatico' LIMIT 1")
        ex = cur.fetchone()
        out["esempio_abbinamento"] = {"from": ex[0], "to": ex[1], "data": str(ex[2])[:150]} if ex else None
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/diag-clausole")
def admin_diag_clausole():
    """Mostra come sono fatte le clausole di abbinamento: analogia vs contrasto, esempi con criteri."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        out = {}
        # esempi di ANALOGIA (abbinamento_aromatico)
        cur.execute("""SELECT e.from_id, e.to_id, e.data FROM edges e
                       WHERE e.relation='abbinamento_aromatico' AND e.data->>'overlap' IS NOT NULL
                       ORDER BY (e.data->>'overlap')::numeric DESC LIMIT 5""")
        out["analogia_top_overlap"] = [{"from": r[0], "to": r[1], "data": str(r[2])[:100]} for r in cur.fetchall()]
        # esempi di CONTRASTO
        cur.execute("""SELECT e.from_id, e.to_id, e.data FROM edges e
                       WHERE e.relation='abbinamento_contrasto' LIMIT 5""")
        out["contrasto_esempi"] = [{"from": r[0], "to": r[1], "data": str(r[2])[:150]} for r in cur.fetchall()]
        # che campi hanno gli archi contrasto?
        cur.execute("""SELECT data FROM edges WHERE relation='abbinamento_contrasto' AND data IS NOT NULL LIMIT 1""")
        ex = cur.fetchone()
        out["struttura_contrasto"] = str(ex[0]) if ex else "nessun dato"
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/surface-zero-foto")
def admin_surface_zero_foto():
    """SURFACE ZERO: toglie TUTTE le foto stock dal ricettario (meglio nessuna foto che una sbagliata).
    Founder Rule #122. Le foto Pexels/Wikimedia vanno via; restano solo eventuali AI verificate."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    conferma = request.args.get("conferma") == "SI"
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # conta prima
        cur.execute("SELECT COUNT(*) FROM ricette WHERE immagine::text ILIKE '%%pexels%%' OR immagine::text ILIKE '%%wik%%'")
        da_togliere = cur.fetchone()[0]
        if not conferma:
            cur.close(); conn.close()
            return jsonify({"anteprima": True, "foto_da_togliere": da_togliere,
                            "nota": "Aggiungi &conferma=SI per eseguire. Toglie le foto stock (Pexels/Wikimedia)."})
        # esegue: mette immagine NULL dove è pexels o wikimedia (foto stock inaffidabili)
        cur.execute("UPDATE ricette SET immagine=NULL WHERE immagine::text ILIKE '%%pexels%%' OR immagine::text ILIKE '%%wik%%'")
        tolte = cur.rowcount
        conn.commit(); cur.close(); conn.close()
        return jsonify({"foto_stock_tolte": tolte, "nota": "Ricette ora senza foto sbagliate. Meglio vuoto che errato."})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/surface-zero-pubblica")
def admin_surface_zero_pubblica():
    """SURFACE ZERO: aggiunge il campo 'pubblica' e lo imposta. Solo le ricette validate a mano
    (pubblica=true) si vedono nel ricettario pubblico. Le altre restano come dati (Creatore/Planner)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='ricette' AND column_name='pubblica'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE ricette ADD COLUMN pubblica BOOLEAN DEFAULT FALSE")
            conn.commit()
        # di default TUTTE nascoste (pubblica=false) finché non validate a mano
        cur.execute("UPDATE ricette SET pubblica=FALSE WHERE pubblica IS NULL")
        cur.execute("SELECT COUNT(*) FROM ricette WHERE pubblica=TRUE")
        pubb = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM ricette")
        tot = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return jsonify({"campo_pubblica": "pronto", "pubbliche": pubb, "totali": tot,
                        "nota": "Tutte nascoste di default. Le specchietto validate si marcano pubblica=true una a una."})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/trova-refusi")
def admin_trova_refusi():
    """Trova i refusi comuni nei testi dei fenomeni: c'e/pero/piu senza accento, l'al dente, ecc."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # pattern di refuso: parola sbagliata -> quante volte appare
    PATTERN = [
        (r"\bc'e\b", "c'e (manca accento: c'è)"),
        (r"\bpero\b", "pero (manca accento: però)"),
        (r"\bpiu\b", "piu (manca accento: più)"),
        (r"\bperche\b", "perche (manca accento: perché)"),
        (r"\bgia\b", "gia (manca accento: già)"),
        (r"\bcosi\b", "cosi (manca accento: così)"),
        (r"\bpoiche\b", "poiche (manca accento: poiché)"),
        (r"l'al dente", "l'al dente (apostrofo errato)"),
        (r"\bqualita\b", "qualita (manca accento: qualità)"),
        (r"\bquantita\b", "quantita (manca accento: quantità)"),
        (r"\bproprieta\b", "proprieta (manca accento: proprietà)"),
        (r"\bpuo\b", "puo (manca accento: può)"),
        (r"\be'\b", "e' (dovrebbe essere è)"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type='Fenomeno'")
        conteggi = {}
        esempi = {}
        for nid, nome, data in cur.fetchall():
            testo = json.dumps(data, ensure_ascii=False).lower() if data else ""
            for pat, desc in PATTERN:
                m = re.findall(pat, testo)
                if m:
                    conteggi[desc] = conteggi.get(desc, 0) + len(m)
                    if desc not in esempi: esempi[desc] = nome
        cur.close(); conn.close()
        return jsonify({"refusi_trovati": conteggi, "esempio_fenomeno": esempi})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/amplia-contrasto")
def admin_amplia_contrasto():
    """Aggiunge i 4 vettori di contrasto nuovi (grasso/acido, piccante/dolce, umami, amaro/grasso)
    creando archi abbinamento_contrasto tra ingredienti che rispettano le clausole sensoriali."""
    from flask import request, jsonify
    import os, psycopg2, json, itertools
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403

    # gruppi di ingredienti per marcatore sensoriale (per nome, sul grafo italiano)
    GRUPPI = {
        "grasso": ["panna", "mascarpone", "burro", "midollo", "lardo", "guanciale", "stracchino",
                   "gorgonzola", "mozzarella di bufala", "avocado", "tahini", "maionese"],
        "acido": ["limone", "lime", "aceto", "aceto balsamico", "aceto di mele", "yogurt", "kefir",
                  "pomodoro", "tamarindo", "melagrana", "verjus", "passiflora"],
        "piccante": ["peperoncino", "pepe lungo", "pepe di sichuan", "harissa", "gochujang",
                     "wasabi", "senape", "zenzero", "nduja"],
        "dolce": ["miele", "sciroppo d'acero", "riduzione di fichi", "melassa di melograno",
                  "zucchero di canna", "datteri", "uvetta", "mela cotta"],
        "umami": ["parmigiano", "grana", "colatura di alici", "garum", "fungo secco", "shiitake secco",
                  "pomodoro secco", "miso", "salsa di soia", "katsuobushi", "bottarga"],
        "amaro": ["carciofo", "cicoria", "radicchio", "cavolo nero", "rucola", "cardo", "tarassaco",
                  "birra amara", "caffè", "cacao amaro", "china"],
    }
    # i 4 vettori: (gruppo_A, gruppo_B, tipo, spiegazione)
    VETTORI = [
        ("grasso", "acido", "grasso_taglia_acido",
         "L'acidità taglia la patina dei grassi saturi e resetta il palato."),
        ("piccante", "dolce", "piccante_bilancia_dolce",
         "Gli zuccheri saturano i recettori TRPV1 e riducono la percezione del piccante senza spegnere l'aroma."),
        ("umami", "acido", "umami_esalta_sapidita",
         "L'acido glutammico agisce in sinergia col sodio, amplificando la sapidità percepita."),
        ("amaro", "grasso", "amaro_pulisce_grasso",
         "I composti amari stimolano la secrezione biliare e puliscono la persistenza dei grassi densi."),
    ]

    def _trova_id(cur, nome):
        cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name) LIKE %s LIMIT 1",
                    (f"%{nome.lower()}%",))
        r = cur.fetchone()
        return r[0] if r else None

    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        creati = 0
        for gA, gB, tipo, spieg in VETTORI:
            for nomeA in GRUPPI[gA]:
                idA = _trova_id(cur, nomeA)
                if not idA: continue
                for nomeB in GRUPPI[gB]:
                    idB = _trova_id(cur, nomeB)
                    if not idB or idA == idB: continue
                    # evito duplicati
                    cur.execute("""SELECT 1 FROM edges WHERE relation='abbinamento_contrasto'
                                   AND from_id=%s AND to_id=%s LIMIT 1""", (idA, idB))
                    if cur.fetchone(): continue
                    data = {"tipo": tipo, "fonte": "dataset Matter Lab (vettori estesi)", "perche": spieg}
                    cur.execute("""INSERT INTO edges (from_id, to_id, relation, data)
                                   VALUES (%s, %s, 'abbinamento_contrasto', %s)""",
                                (idA, idB, json.dumps(data, ensure_ascii=False)))
                    creati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"archi_contrasto_creati": creati, "vettori": [v[2] for v in VETTORI]})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/diag-copertura-composti")
def admin_diag_copertura_composti():
    """Verifica la copertura composti: quanti ingredienti hanno composti vs quanti sono 'vuoti'
    (senza composti = inutili per l'abbinamento aromatico e per il Creatore)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti totali
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        tot = cur.fetchone()[0]
        # ingredienti CON almeno un composto
        cur.execute("""SELECT COUNT(DISTINCT from_id) FROM edges WHERE relation='contiene_composto'""")
        con_comp = cur.fetchone()[0]
        # ingredienti italiani (ing-) senza composti (i più a rischio - il Creatore li userebbe)
        cur.execute("""SELECT COUNT(*) FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto')
                       AND n.id LIKE 'ing-%%'
                       AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation='contiene_composto')""")
        ita_senza = cur.fetchone()[0]
        # esempi di italiani senza composti
        cur.execute("""SELECT n.name FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto')
                       AND n.id LIKE 'ing-%%'
                       AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id = n.id AND e.relation='contiene_composto')
                       LIMIT 15""")
        esempi = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"totale_ingredienti": tot, "con_composti": con_comp,
                        "italiani_senza_composti": ita_senza, "esempi_vuoti": esempi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/admin/duplicati-anteprima")
def admin_duplicati_anteprima():
    """Anteprima unione duplicati: per ogni nome doppio, mostra chi si terrebbe (quello con più archi)
    e chi si unirebbe. NON tocca nulla. Serve a decidere prima di unire."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # nomi con duplicati (type ingrediente/prodotto)
        cur.execute("""SELECT LOWER(name) nome, COUNT(*) c FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name) HAVING COUNT(*) > 1 ORDER BY c DESC LIMIT 12""")
        nomi = cur.fetchall()
        anteprima = []
        for nome, c in nomi:
            # i nodi con questo nome + quanti archi ha ciascuno
            cur.execute("""SELECT n.id,
                           (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) archi
                           FROM nodes n WHERE LOWER(n.name)=%s AND n.type IN ('Ingrediente','Prodotto')
                           ORDER BY archi DESC""", (nome,))
            nodi = [{"id": r[0], "archi": r[1]} for r in cur.fetchall()]
            anteprima.append({"nome": nome, "copie": c, "tiene": nodi[0] if nodi else None,
                              "unisce": nodi[1:]})
        # totale duplicati
        cur.execute("""SELECT COUNT(*) FROM (SELECT LOWER(name) FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name) HAVING COUNT(*) > 1) t""")
        tot_nomi_dup = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"nomi_con_duplicati": tot_nomi_dup, "anteprima_primi_12": anteprima})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/unisci-duplicati")
def admin_unisci_duplicati():
    """Unisce i duplicati: per ogni nome doppio tiene il nodo con più archi (di solito Ahn),
    sposta gli archi delle copie su di lui, cancella le copie. Batch per non sovraccaricare."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "40")), 80)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT LOWER(name) nome FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto')
                       GROUP BY LOWER(name) HAVING COUNT(*) > 1 LIMIT %s""", (n,))
        nomi = [r[0] for r in cur.fetchall()]
        uniti = 0; copie_rimosse = 0; archi_spostati = 0
        for nome in nomi:
            # nodi con questo nome, ordinati per archi (tiene il primo)
            cur.execute("""SELECT n.id,
                           (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) archi
                           FROM nodes n WHERE LOWER(n.name)=%s AND n.type IN ('Ingrediente','Prodotto')
                           ORDER BY archi DESC""", (nome,))
            nodi = [r[0] for r in cur.fetchall()]
            if len(nodi) < 2: continue
            tiene = nodi[0]
            for copia in nodi[1:]:
                # sposta gli archi in uscita (evitando duplicati e self-loop)
                cur.execute("""UPDATE edges SET from_id=%s WHERE from_id=%s
                               AND NOT EXISTS (SELECT 1 FROM edges e2 WHERE e2.from_id=%s AND e2.to_id=edges.to_id AND e2.relation=edges.relation)
                               AND to_id != %s""", (tiene, copia, tiene, tiene))
                archi_spostati += cur.rowcount
                # sposta gli archi in entrata
                cur.execute("""UPDATE edges SET to_id=%s WHERE to_id=%s
                               AND NOT EXISTS (SELECT 1 FROM edges e2 WHERE e2.to_id=%s AND e2.from_id=edges.from_id AND e2.relation=edges.relation)
                               AND from_id != %s""", (tiene, copia, tiene, tiene))
                archi_spostati += cur.rowcount
                # cancella gli archi residui della copia (duplicati o self-loop) e la copia
                cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s", (copia, copia))
                cur.execute("DELETE FROM nodes WHERE id=%s", (copia,))
                copie_rimosse += 1
            uniti += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"nomi_uniti": uniti, "copie_rimosse": copie_rimosse, "archi_spostati": archi_spostati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/danno-unione")
def admin_danno_unione():
    """Verifica quanti nodi 'tenuti' dall'unione hanno pochi archi (danneggiati) vs sani."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti ahn con POCHI archi (sospetti danneggiati: un ahn dovrebbe averne decine)
        cur.execute("""SELECT n.name,
                       (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) archi
                       FROM nodes n WHERE n.id LIKE 'ahn_%%' AND n.type IN ('Ingrediente','Prodotto')
                       ORDER BY archi ASC LIMIT 30""")
        poveri = [{"nome": r[0], "archi": r[1]} for r in cur.fetchall()]
        # quanti ahn hanno meno di 5 archi (probabile danno)
        cur.execute("""SELECT COUNT(*) FROM nodes n WHERE n.id LIKE 'ahn_%%' AND n.type IN ('Ingrediente','Prodotto')
                       AND (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) < 5""")
        n_poveri = cur.fetchone()[0]
        # totale archi abbinamento nel grafo (per confronto - erano ~4078)
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='abbinamento_aromatico'")
        tot_archi = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"ahn_con_meno_di_5_archi": n_poveri, "archi_aromatici_totali_ora": tot_archi,
                        "erano_circa": 4078, "esempi_poveri": poveri})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})






@bp.route("/admin/ingredienti-poveri-composti")
def admin_ingredienti_poveri_composti():
    """Trova gli ingredienti IMPORTANTI (usati nelle ricette) che hanno pochi o zero composti,
    per sapere dove aggiungere composti PubChem mirati."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti italiani (ing-) con 0 composti - i più rilevanti per il Creatore
        cur.execute("""SELECT n.name FROM nodes n
                       WHERE n.type IN ('Ingrediente','Prodotto') AND n.id LIKE 'ing-%%'
                       AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                       ORDER BY n.name LIMIT 60""")
        senza = [r[0] for r in cur.fetchall()]
        # quanti composti PubChem ci sono
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Composto' AND id LIKE 'pub_%%'")
        n_pub = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"composti_pubchem": n_pub, "ingredienti_senza_composti": senza})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})






@bp.route("/admin/top-ingredienti-chiave")
def admin_top_ingredienti_chiave():
    """Trova i ~300 ingredienti PIU importanti: piu connessi nel grafo (li usera il Composer).
    Sono quelli da mappare per primi con le proprieta (Anello 1)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "300")), 400)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti ordinati per numero di connessioni (i piu centrali nel grafo)
        cur.execute("""SELECT n.name,
                       (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) archi,
                       (n.data ? 'proprieta') ha_prop
                       FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto')
                       AND n.name NOT LIKE '%%(%%'
                       ORDER BY archi DESC LIMIT %s""", (n,))
        righe = cur.fetchall()
        con_prop = sum(1 for r in righe if r[2])
        senza_prop = [r[0] for r in righe if not r[2]][:50]
        cur.close(); conn.close()
        return jsonify({"top_ingredienti": len(righe), "gia_con_proprieta": con_prop,
                        "da_mappare_esempi": senza_prop})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/mappa-proprieta-ai")
def admin_mappa_proprieta_ai():
    """Assegna le 15 proprieta ai top ingredienti (Anello 1) con AI, batch + pause. Valutazione
    sensoriale nota (caffe amaro, lime acido...), non dati inventati. Sonnet, JSON rigido."""
    from flask import request, jsonify
    import os, psycopg2, threading, json, urllib.request as ur, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "8")), 12)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    P = ["dolce","salato","acido","amaro","umami","grasso","corposita","croccante","astringente","piccante","termico","aroma_fresco","aroma_caldo","effervescenza","fermentato","alcolico"]

    def _valuta(nome):
        try:
            prompt = (f"Sei un esperto di analisi sensoriale. Valuta l'ingrediente '{nome}' su 15 proprieta, "
                      f"scala 0-10 (termico da -10 freddo/mentolato a +10 caldo/piccante). "
                      f"Proprieta: dolce, salato, acido, amaro, umami, grasso, corposita, croccante, astringente, "
                      f"piccante, termico, aroma_fresco, aroma_caldo, effervescenza, fermentato. "
                      f"Rispondi SOLO con un oggetto JSON {{\"dolce\":N,...}} con tutte le 15 chiavi, niente altro.")
            payload = {"model": "claude-sonnet-4-5", "max_tokens": 300,
                       "messages": [{"role": "user", "content": prompt}]}
            req = ur.Request("https://api.anthropic.com/v1/messages", data=json.dumps(payload).encode(),
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            r = ur.urlopen(req, timeout=30); d = json.loads(r.read().decode())
            txt = d["content"][0]["text"].strip()
            # estraggo il JSON
            i0 = txt.find("{"); i1 = txt.rfind("}")
            if i0 >= 0 and i1 > i0:
                prop = json.loads(txt[i0:i1+1])
                # tengo solo le 15 chiavi valide, numeri
                out = {}
                for k in P:
                    v = prop.get(k, 0)
                    try: out[k] = max(-10, min(10, int(round(float(v)))))
                    except: out[k] = 0
                return out
        except Exception:
            pass
        return None

    def _w(n):
        fatti = 0; err = ""
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            # top per connessioni, senza proprieta
            cur.execute("""SELECT n.id, n.name, n.data,
                           (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) ar
                           FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto')
                           AND n.name NOT LIKE '%%(%%' AND NOT (n.data ? 'proprieta')
                           ORDER BY ar DESC LIMIT %s""", (n,))
            for nid, nome, data, ar in cur.fetchall():
                prop = _valuta(nome)
                if prop:
                    dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
                    dd["proprieta"] = prop
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                    conn.commit(); fatti += 1
                time.sleep(4)
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"mappa-proprieta-ai: {fatti}",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": f"mappa {n} ingredienti con AI, pause 4s"})


@bp.route("/admin/vedi-proprieta")
def admin_vedi_proprieta():
    """Mostra le proprieta di alcuni ingredienti mappati (per verifica)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data ? 'proprieta') ORDER BY random() LIMIT 8""")
        out = []
        for nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else json.loads(data)
            prop = dd.get("proprieta", {})
            alte = {k: v for k, v in prop.items() if abs(v) >= 5}
            out.append({"nome": nome, "proprieta_alte": alte})
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'proprieta')")
        tot = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"totale_con_proprieta": tot, "esempi": out})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/proprieta-eredita-varianti")
def admin_proprieta_eredita_varianti():
    """Anello 2: le varianti senza proprieta ereditano dal genitore che le ha (limone di X -> limone).
    Match per parola-madre contenuta nel nome. No AI, gratis."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "80")), 150)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti CON proprieta (i genitori candidati), nome -> proprieta
        cur.execute("""SELECT LOWER(name), data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data ? 'proprieta')""")
        genitori = []
        for nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else json.loads(data)
            genitori.append((nome, dd.get("proprieta")))
        # ordino i genitori per nome piu corto (piu generico = madre migliore)
        genitori.sort(key=lambda x: len(x[0]))
        # ingredienti SENZA proprieta
        cur.execute("""SELECT id, LOWER(name), data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'proprieta') AND name NOT LIKE '%%(%%' LIMIT %s""", (n,))
        ereditati = 0
        for nid, nomev, data in cur.fetchall():
            # trovo il genitore piu generico il cui nome e' contenuto nella variante
            madre_prop = None
            for gnome, gprop in genitori:
                if len(gnome) >= 3 and gnome in nomev:
                    madre_prop = gprop; break
            if not madre_prop: continue
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dd["proprieta"] = madre_prop
            dd["proprieta_ereditata"] = True
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            ereditati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"varianti_ereditate": ereditati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})










@bp.route("/admin/rivedi-varieta")
def admin_rivedi_varieta():
    """Elenca tutte le varieta' profonde aggiunte (carne, pomodoro, farina, formaggio, pesce) con
    caratteristica e proprieta', per la revisione manuale di Michele (correggere errori, aggiungere)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    cat = request.args.get("categoria", "")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        if cat:
            cur.execute("""SELECT name, data FROM nodes WHERE type='Ingrediente' AND data->>'categoria'=%s ORDER BY name""", (cat,))
        else:
            cur.execute("""SELECT name, data FROM nodes WHERE type='Ingrediente'
                           AND data->>'categoria' IN ('carne_bovina','pomodoro_varieta','farina','formaggio','pesce') ORDER BY data->>'categoria', name""")
        out = []
        for nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else json.loads(data)
            out.append({"nome": nome, "categoria": dd.get("categoria"),
                        "caratteristica": dd.get("caratteristica","")[:80]})
        cur.close(); conn.close()
        return jsonify({"totale": len(out), "varieta": out})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/attributi-operativi")
def admin_attributi_operativi():
    """Aggiunge attributi OPERATIVI (yield/resa, scarto, shelf life, conservazione, allergeni) agli
    ingredienti dei 5 domini profondi. Grounding su valori standard (CREA/settore). Carburante per Cifra."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # attributi per CATEGORIA (valori standard di settore, orientativi - Michele affina in dogfooding)
    # yield = resa % dopo pulizia; shelf_life_giorni a frigo; allergeni lista UE
    PER_CATEGORIA = {
        "carne_bovina": {"yield": 85, "scarto_perc": 15, "shelf_life_giorni": 4, "conservazione": "0-4°C", "allergeni": []},
        "pomodoro_varieta": {"yield": 92, "scarto_perc": 8, "shelf_life_giorni": 7, "conservazione": "ambiente/frigo", "allergeni": []},
        "farina": {"yield": 100, "scarto_perc": 0, "shelf_life_giorni": 365, "conservazione": "luogo secco", "allergeni": ["glutine"]},
        "formaggio": {"yield": 98, "scarto_perc": 2, "shelf_life_giorni": 20, "conservazione": "0-4°C", "allergeni": ["latte"]},
        "pesce": {"yield": 65, "scarto_perc": 35, "shelf_life_giorni": 2, "conservazione": "0-2°C", "allergeni": ["pesce"]},
    }
    # override specifici per alcuni ingredienti (dove il valore di categoria non basta)
    OVERRIDE = {
        "Filetto di manzo": {"yield": 92, "scarto_perc": 8},
        "Guancia di manzo": {"yield": 80, "scarto_perc": 20},
        "Ossobuco": {"yield": 60, "scarto_perc": 40, "note": "osso incluso"},
        "Baccala (merluzzo salato)": {"shelf_life_giorni": 120, "note": "sotto sale, da dissalare"},
        "Farina Manitoba (W350+)": {"shelf_life_giorni": 300},
        "Semola di grano duro": {"allergeni": ["glutine"]},
        "Cozze": {"yield": 30, "scarto_perc": 70, "allergeni": ["molluschi"], "note": "guscio"},
        "Vongole": {"yield": 25, "scarto_perc": 75, "allergeni": ["molluschi"], "note": "guscio"},
        "Polpo": {"yield": 75, "scarto_perc": 25, "allergeni": ["molluschi"]},
        "Gambero rosso di Mazara": {"yield": 55, "scarto_perc": 45, "allergeni": ["crostacei"]},
        "Acciughe del Cantabrico": {"allergeni": ["pesce"], "shelf_life_giorni": 90},
        "Mozzarella di Bufala Campana DOP": {"shelf_life_giorni": 5},
        "Ricotta": {"shelf_life_giorni": 4},
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Ingrediente'
                       AND data->>'categoria' IN ('carne_bovina','pomodoro_varieta','farina','formaggio','pesce')""")
        aggiornati = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else json.loads(data)
            cat = dd.get("categoria")
            attr = dict(PER_CATEGORIA.get(cat, {}))
            if nome in OVERRIDE:
                attr.update(OVERRIDE[nome])
            dd["operativo"] = attr
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            aggiornati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ingredienti_con_attributi_operativi": aggiornati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/admin/vedi-data-raw")
def admin_vedi_data_raw():
    """Mostra il data RAW di un ingrediente per debug (quali chiavi ha davvero)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    nome = request.args.get("nome", "Filetto di manzo")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE LOWER(name)=LOWER(%s) LIMIT 1", (nome,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "non trovato"})
        nid, nm, data = r
        dd = data if isinstance(data, dict) else json.loads(data)
        cur.close(); conn.close()
        return jsonify({"id": nid, "nome": nm, "chiavi_data": list(dd.keys()),
                        "ha_operativo": "operativo" in dd, "ha_proprieta": "proprieta" in dd,
                        "operativo_valore": dd.get("operativo")})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})










@bp.route("/admin/operativo-per-categoria-ahn")
def admin_operativo_per_categoria_ahn():
    """Assegna attributi operativi di default agli ingredienti-tipo che ancora non ne hanno, in base
    alla famiglia (ingredient_family/domini). Copertura larga per Cifra, valori standard orientativi."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "200")), 400)
    # default per famiglia (yield, shelf_life, allergeni, conservazione)
    DEF = {
        "meat": {"yield":80,"shelf_life_giorni":4,"conservazione":"0-4°C","allergeni":[]},
        "fish": {"yield":65,"shelf_life_giorni":2,"conservazione":"0-2°C","allergeni":["pesce"]},
        "seafood": {"yield":50,"shelf_life_giorni":2,"conservazione":"0-2°C","allergeni":["molluschi"]},
        "vegetable": {"yield":85,"shelf_life_giorni":6,"conservazione":"frigo","allergeni":[]},
        "fruit": {"yield":88,"shelf_life_giorni":7,"conservazione":"fresco","allergeni":[]},
        "dairy": {"yield":98,"shelf_life_giorni":15,"conservazione":"0-4°C","allergeni":["latte"]},
        "cheese": {"yield":98,"shelf_life_giorni":20,"conservazione":"0-4°C","allergeni":["latte"]},
        "grain": {"yield":100,"shelf_life_giorni":365,"conservazione":"secco","allergeni":["glutine"]},
        "cereal": {"yield":100,"shelf_life_giorni":365,"conservazione":"secco","allergeni":["glutine"]},
        "spice": {"yield":100,"shelf_life_giorni":365,"conservazione":"secco","allergeni":[]},
        "herb": {"yield":90,"shelf_life_giorni":5,"conservazione":"fresco","allergeni":[]},
        "nut": {"yield":95,"shelf_life_giorni":180,"conservazione":"secco","allergeni":["frutta a guscio"]},
        "legume": {"yield":100,"shelf_life_giorni":365,"conservazione":"secco","allergeni":[]},
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'operativo') LIMIT %s""", (n,))
        aggiornati = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            fam = (dd.get("ingredient_family") or "").lower()
            dominio = str(dd.get("domini","")).lower()
            scelto = None
            for k in DEF:
                if k in fam or k in dominio or k in str(dd.get("categoria","")).lower():
                    scelto = k; break
            if not scelto: continue
            op = dict(DEF[scelto]); op["scarto_perc"] = 100 - op["yield"]
            dd["operativo"] = op
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            aggiornati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"operativo_assegnato": aggiornati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/anteprima-doppioni-ai")
def admin_anteprima_doppioni_ai():
    """Anteprima: trova i nodi ai_ vecchi (vuoti) che duplicano un mio nodo ing- dettagliato (stesso nome).
    NON tocca nulla. Per decidere l'unione."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # nomi che hanno SIA un nodo ai_ SIA un nodo ing- con caratteristica
        cur.execute("""SELECT LOWER(a.name), a.id, i.id
                       FROM nodes a JOIN nodes i ON LOWER(a.name)=LOWER(i.name)
                       WHERE a.id LIKE 'ai_%%' AND i.id LIKE 'ing-%%'
                       AND (i.data ? 'caratteristica') AND (i.data->>'caratteristica') != ''
                       LIMIT 40""")
        coppie = [{"nome": r[0], "ai_vuoto": r[1], "ing_dettagliato": r[2]} for r in cur.fetchall()]
        cur.execute("""SELECT COUNT(*) FROM nodes a JOIN nodes i ON LOWER(a.name)=LOWER(i.name)
                       WHERE a.id LIKE 'ai_%%' AND i.id LIKE 'ing-%%' AND (i.data ? 'caratteristica')""")
        tot = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"totale_doppioni_ai": tot, "esempi": coppie})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/unisci-doppioni-ai")
def admin_unisci_doppioni_ai():
    """Unisce i doppioni ai_: sposta gli archi del nodo ai_ vuoto sul mio ing- dettagliato, poi cancella
    l'ai_. Solo i casi dell'anteprima (pochi, sicuri)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT a.id, i.id FROM nodes a JOIN nodes i ON LOWER(a.name)=LOWER(i.name)
                       WHERE a.id LIKE 'ai_%%' AND i.id LIKE 'ing-%%'
                       AND (i.data ? 'caratteristica') AND (i.data->>'caratteristica') != ''""")
        coppie = cur.fetchall()
        uniti = 0; archi = 0
        for ai_id, ing_id in coppie:
            # sposto gli archi dell'ai_ sul mio ing- (evitando duplicati e self-loop)
            cur.execute("""UPDATE edges SET from_id=%s WHERE from_id=%s AND to_id!=%s
                           AND NOT EXISTS (SELECT 1 FROM edges e2 WHERE e2.from_id=%s AND e2.to_id=edges.to_id AND e2.relation=edges.relation)""",
                        (ing_id, ai_id, ing_id, ing_id))
            archi += cur.rowcount
            cur.execute("""UPDATE edges SET to_id=%s WHERE to_id=%s AND from_id!=%s
                           AND NOT EXISTS (SELECT 1 FROM edges e2 WHERE e2.to_id=%s AND e2.from_id=edges.from_id AND e2.relation=edges.relation)""",
                        (ing_id, ai_id, ing_id, ing_id))
            archi += cur.rowcount
            # cancello archi residui dell'ai_ e il nodo
            cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s", (ai_id, ai_id))
            cur.execute("DELETE FROM nodes WHERE id=%s", (ai_id,))
            uniti += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"doppioni_uniti": uniti, "archi_spostati": archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/hq/crediti-ai")
def admin_hq_crediti_ai():
    """MONITOR CREDITI AI: consumo stimato dell'assistente + traccia il consumo cumulato per allertare
    prima dell'esaurimento. Nota: OpenAI/Anthropic non espongono il saldo via API in modo affidabile,
    quindi si traccia il CONSUMO nostro (token -> euro stimati) come proxy per l'alert."""
    from flask import request, jsonify
    import os, psycopg2, datetime
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # prezzi indicativi per 1M token (input+output medio)
    PREZZI = {"gpt-4o-mini": 0.30, "sonnet": 3.0, "gemini-flash": 0.10}
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # consumo assistente per giorno (ultimi 7 giorni)
        cur.execute("""SELECT giorno, COALESCE(SUM(token_usati),0) FROM assistente_uso
                       GROUP BY giorno ORDER BY giorno DESC LIMIT 7""")
        per_giorno = [{"giorno": r[0], "token": r[1], "costo_stimato_eur": round(r[1]/1_000_000*PREZZI["gpt-4o-mini"],4)} for r in cur.fetchall()]
        # totale storico assistente
        cur.execute("SELECT COALESCE(SUM(token_usati),0) FROM assistente_uso")
        tot_token = cur.fetchone()[0]
        cur.close(); conn.close()
        costo_tot = round(tot_token/1_000_000*PREZZI["gpt-4o-mini"], 4)
        return jsonify({
            "assistente_token_totali": tot_token,
            "assistente_costo_totale_eur": costo_tot,
            "consumo_ultimi_7_giorni": per_giorno,
            "nota": "Il saldo credito dei provider va controllato sui loro dashboard (non esposto via API). Qui si traccia il consumo dell'assistente come proxy.",
            "modello_assistente": "gpt-4o-mini",
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/hq/stato-ecosistema")
def admin_hq_stato_ecosistema():
    """PANNELLO GALILEO-HQ: stato di salute dell'ecosistema in un colpo."""
    from flask import request, jsonify
    import os, psycopg2, datetime
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {"timestamp": datetime.datetime.now().isoformat()[:19]}
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        out["ingredienti"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'proprieta')")
        out["con_proprieta"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'operativo')")
        out["con_operativo"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'caratteristica') AND (data->>'caratteristica')!=''")
        out["varieta_profonde"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges WHERE relation='abbinamento_aromatico'")
        out["archi_abbinamento"] = cur.fetchone()[0]
        try:
            cur.execute("SELECT COUNT(*) FROM ricette WHERE pubblica=true")
            out["ricette_pubbliche"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ricette")
            out["ricette_totali"] = cur.fetchone()[0]
        except Exception: out["ricette"] = "n/d"
        oggi = datetime.date.today().isoformat()
        try:
            cur.execute("SELECT COUNT(DISTINCT account), COALESCE(SUM(token_usati),0) FROM assistente_uso WHERE giorno=%s", (oggi,))
            r = cur.fetchone()
            out["assistente_oggi"] = {"account_attivi": r[0], "token_totali": r[1]}
        except Exception: out["assistente_oggi"] = "n/d"
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data ? 'operativo') AND NOT (data->'operativo' ? 'allergeni')""")
        out["operativo_senza_allergeni"] = cur.fetchone()[0]
        cur.close(); conn.close()
        out["stato"] = "ok"
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/hq")
def hq_panel():
    """Serve la pagina del pannello Galileo-HQ (monitoraggio ecosistema).
    La pagina si auto-protegge col secret (gate lato client contro gli endpoint /admin/hq/*)."""
    from flask import render_template
    try:
        return render_template("hq.html")
    except Exception as e:
        return f"Pannello HQ non disponibile: {str(e)[:100]}", 500


@bp.route("/admin/debug-analogia")
def admin_debug_analogia():
    """Debug: perche l'analogia (composti condivisi) non esce nel grafo. Passo per passo su pomodoro."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        out = {}
        # 1. che id ha pomodoro
        cur.execute("""SELECT id, name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND LOWER(name) LIKE '%%pomodoro%%' ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""")
        r = cur.fetchone(); out["pomodoro_scelto"] = {"id": r[0], "name": r[1]} if r else None
        id_c = r[0] if r else None
        # 2. quanti composti ha
        cur.execute("SELECT COUNT(*) FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_c,))
        out["composti_del_pomodoro"] = cur.fetchone()[0]
        # 3. esempi di to_id (i composti)
        cur.execute("SELECT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto' LIMIT 5", (id_c,))
        comp = [x[0] for x in cur.fetchall()]
        out["esempi_composti"] = comp
        # 4. altri ingredienti che condividono QUEI composti (il cuore dell'analogia)
        if comp:
            cur.execute("""SELECT n.name, COUNT(*) ov FROM edges e JOIN nodes n ON n.id=e.from_id
                           WHERE e.relation='contiene_composto' AND e.to_id = ANY(%s) AND e.from_id != %s
                           AND n.type IN ('Ingrediente','Prodotto')
                           GROUP BY n.name ORDER BY ov DESC LIMIT 8""", (comp, id_c))
            out["condividono_composti"] = [{"nome": x[0], "n": x[1]} for x in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/grafo-gerarchia")
def admin_grafo_gerarchia():
    """LIVELLO 1 teoria dei grafi: la GERARCHIA dei nodi. Assegna a ogni ingrediente un 'tipo_base'
    (il nodo-tipo di cui e' variante) cosi' il grafo puo' escludere i parenti dagli abbinamenti.
    Es. San Marzano, Piennolo, Datterino -> tipo_base 'pomodoro'. Non e' un algoritmo: e' il modello."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "300")), 500)
    # mappa parola-chiave -> tipo_base (la gerarchia gastronomica)
    TIPI = {
        "pomodoro":"pomodoro","limone":"limone","arancia":"arancia","mandarino":"agrume","bergamotto":"agrume",
        "lime":"agrume","farina":"farina","semola":"farina","cioccolato":"cioccolato","cacao":"cioccolato",
        "manzo":"manzo","vitello":"manzo","controfiletto":"manzo","filetto":"manzo","costata":"manzo",
        "fiorentina":"manzo","scamone":"manzo","guancia":"manzo","ossobuco":"manzo","brisket":"manzo",
        "picanha":"manzo","tomahawk":"manzo","reale":"manzo","bresaola":"manzo","parmigiano":"formaggio",
        "grana":"formaggio","pecorino":"formaggio","mozzarella":"formaggio","gorgonzola":"formaggio",
        "ricotta":"formaggio","caciocavallo":"formaggio","stracciatella":"formaggio","fior di latte":"formaggio",
        "branzino":"pesce","orata":"pesce","salmone":"pesce","tonno":"pesce","baccala":"pesce","acciughe":"pesce",
        "gambero":"crostaceo","cozze":"mollusco","vongole":"mollusco","polpo":"mollusco","seppia":"mollusco",
        "zucchina":"zucchina","melanzana":"melanzana","peperone":"peperone","friggitello":"peperone",
        "carciofo":"carciofo","radicchio":"radicchio","puntarelle":"cicoria","cavolo":"cavolo","zucca":"zucca",
        "patata":"patata","asparago":"asparago","basilico":"basilico","menta":"menta","prezzemolo":"prezzemolo",
        "salvia":"salvia","rosmarino":"rosmarino","fico":"fico","pesca":"pesca","fragola":"fragola","mela":"mela",
        "uva":"uva","fagiol":"legume","cece":"legume","lenticchia":"legume","fava":"legume","pisello":"legume",
        "riso":"riso","olio":"olio","aceto":"aceto","miele":"miele","sale":"sale","pepe":"spezia",
        "zafferano":"spezia","peperoncino":"spezia","guanciale":"salume","pancetta":"salume","prosciutto":"salume",
        "mortadella":"salume","nduja":"salume","speck":"salume","salame":"salume","lardo":"salume",
        "gin":"distillato","rum":"distillato","tequila":"distillato","whisky":"distillato","vermouth":"vino",
        "prosecco":"vino","vino":"vino","campari":"bitter","angostura":"bitter","zucchero":"zucchero",
        "panna":"latticino","burro":"grasso","gelatina":"addensante","vaniglia":"spezia","pasta di nocciola":"frutta secca",
        "pasta di pistacchio":"frutta secca",
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # processo TUTTI i nodi senza tipo_base (non solo i primi n): scorro a scaglioni con OFFSET
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND NOT (data ? 'tipo_base')""")
        da_fare = cur.fetchone()[0]
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'tipo_base')""")
        righe = cur.fetchall()
        assegnati = 0; senza_match = 0
        keys_sorted = sorted(TIPI.keys(), key=len, reverse=True)
        for nid, nome, data in righe:
            nl = nome.lower()
            tipo = None
            for k in keys_sorted:
                if k in nl: tipo = TIPI[k]; break
            # se il nome non matcha ma il nodo ha gia un 'genitore', usa quello
            if not tipo:
                dd0 = data if isinstance(data, dict) else (json.loads(data) if data else {})
                gen = dd0.get('genitore')
                if gen:
                    gl = str(gen).lower()
                    for k in keys_sorted:
                        if k in gl: tipo = TIPI[k]; break
                    if not tipo: tipo = gl  # il genitore stesso come tipo
            if not tipo:
                senza_match += 1; continue
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dd["tipo_base"] = tipo
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            assegnati += 1
            if assegnati % 200 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"tipo_base_assegnati": assegnati, "senza_match": senza_match, "totale_processati": len(righe)})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/conta-gerarchia")
def admin_conta_gerarchia():
    """Quanti nodi hanno il tipo_base (gerarchia) e verifica su esempi."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        tot = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data ? 'tipo_base')")
        con = cur.fetchone()[0]
        # esempi: San Marzano, filetto, datterino -> che tipo_base hanno
        esempi = {}
        for nome in ['Pomodoro San Marzano DOP','Filetto di manzo','Pomodoro Datterino','Guancia di manzo']:
            cur.execute("SELECT data FROM nodes WHERE LOWER(name)=LOWER(%s) LIMIT 1", (nome,))
            r = cur.fetchone()
            if r:
                dd = r[0] if isinstance(r[0], dict) else json.loads(r[0])
                esempi[nome] = dd.get('tipo_base','(nessuno)')
        cur.close(); conn.close()
        return jsonify({"totale": tot, "con_tipo_base": con, "percentuale": round(con/tot*100,1) if tot else 0, "esempi": esempi})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/conta-prezzi")
def admin_conta_prezzi():
    """Quanti ingredienti hanno un prezzo (per il food cost). Il buco che fa uscire food cost a zero."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        tot = cur.fetchone()[0]
        # cerco chi ha un prezzo nel data (prezzo, prezzo_kg, costo...)
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data ? 'prezzo' OR data ? 'prezzo_kg' OR data ? 'costo_kg' OR data->'operativo' ? 'prezzo_kg')""")
        con_prezzo = cur.fetchone()[0]
        # esempi senza prezzo tra i piu usati
        cur.execute("""SELECT name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'prezzo' OR data ? 'prezzo_kg' OR data ? 'costo_kg')
                       AND id LIKE 'ing-%%' LIMIT 12""")
        esempi = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"totale": tot, "con_prezzo": con_prezzo,
                        "percentuale": round(con_prezzo/tot*100,1) if tot else 0, "esempi_senza": esempi})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})




@bp.route("/admin/vedi-fenomeno-completo")
def admin_vedi_fenomeno_completo():
    """Mostra il CONTENUTO completo di un fenomeno esistente (per capire cosa c'e' gia' e non duplicare)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    nome = request.args.get("nome", "Emulsione")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE LOWER(name) LIKE LOWER(%s) AND type IN ('Fenomeno','Tecnica') LIMIT 1", (f"%{nome}%",))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "non trovato"})
        dd = r[2] if isinstance(r[2], dict) else json.loads(r[2])
        # restituisco i valori veri (troncati) per capire il formato
        out = {"id": r[0], "nome": r[1], "campi": {}}
        for k, v in dd.items():
            out["campi"][k] = (str(v)[:200] if v else None)
        cur.close(); conn.close()
        return jsonify(out)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/admin/marca-preparazioni")
def admin_marca_preparazioni():
    """Separa le PREPARAZIONI/derivati (concentrato, passata, pelato, secco) dalle VARIETA/cultivar vere.
    Marca i derivati con e_preparazione=true cosi la lista varieta mostra solo le cultivar (ontologia #192)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # parole che indicano una preparazione/derivato, non una cultivar
    PREP = ["concentrato", "passata", "pelato", "pelati", "secco", "secchi", "essiccato",
            "conserva", "salsa", "sugo", "in scatola", "sott'olio", "sottolio", "polpa",
            "confettura", "marmellata", "sciroppo", "succo", "purea", "estratto",
            "farina di", "pasta di", "granella", "in polvere", "candito", "disidratato"]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data ? 'tipo_base')""")
        marcati = 0
        for nid, nome, data in cur.fetchall():
            nl = nome.lower()
            if any(p in nl for p in PREP):
                dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
                if not dd.get("e_preparazione"):
                    dd["e_preparazione"] = True
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                    marcati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"preparazioni_marcate": marcati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/prezzi-bar")
def admin_prezzi_bar():
    """Completa i prezzi dei distillati/liquori/bar mancanti (il food cost dei cocktail usciva a zero
    perche' l'ingrediente principale - il distillato - non aveva prezzo). EUR/L all'ingrosso."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    PREZZI = {
        "amaretto":14,"aperol":13,"campari":16,"martini":9,"vermouth bianco":9,"vermouth dry":9,
        "prosecco":7,"spumante":8,"gin":18,"vodka":16,"rum bianco":15,"rum scuro":18,"rum":16,
        "tequila":24,"whisky":22,"whiskey":22,"bourbon":24,"cognac":35,"brandy":18,"grappa":16,
        "triple sec":13,"cointreau":22,"curacao":14,"curaçao":14,"maraschino":20,"amaro":15,
        "limoncello":12,"sambuca":13,"bitter":16,"angostura":45,"fernet":16,"chartreuse":40,
        "st germain":28,"aperitivo":13,"liquore":16,"sciroppo di zucchero":2,"sciroppo":4,
        "succo di limone":3,"succo di lime":4,"succo d'arancia":2,"soda":1,"acqua tonica":2,
        "ginger beer":3,"ginger ale":2,"albume":4,"albume d'uovo":4,"prosecco doc":8,
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        keys_sorted = sorted(PREZZI.keys(), key=len, reverse=True)
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'prezzo_kg')""")
        agg = 0
        for nid, nome, data in cur.fetchall():
            nl = nome.lower()
            pr = None
            for k in keys_sorted:
                if k in nl: pr = PREZZI[k]; break
            if pr is None: continue
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dd["prezzo_kg"] = pr  # per i liquidi prezzo_kg vale come EUR/L
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            agg += 1
            if agg % 100 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"prezzi_bar_assegnati": agg})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/target-type-fenomeni")
def admin_target_type_fenomeni():
    """Board #46: assegna a ogni fenomeno tipo_bersaglio (numero/multiplo/concetto), header_bersaglio
    (il parametro DOMINANTE) e target_chips (secondari). Il backend espone il significato (#218A)."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    def _analizza(nb, nome_fen=""):
        nb = (nb or "").strip()
        if not nb:
            return {"tipo_bersaglio": "concetto", "header_bersaglio": nome_fen, "target_chips": []}
        # spezzo sui separatori
        parti = [p.strip() for p in re.split(r"[·|]", nb) if p.strip()]
        # una parte "buona" per un chip: ha un numero+unita ed e corta
        def _num_pulito(t):
            # tollerante: ~, virgole decimali, range con - o –, unita varie
            m = re.search(r"(pH\s*)?[~≈]?\s*\d+[.,]?\d*\s*[-–]?\s*\d*[.,]?\d*\s*(°\s?C|°C|%|pH|mg/L|g/L|kg|ml|h|ore|min|mesi|giorni|Aw|µm|bar|mbar|°|DE)", t, re.IGNORECASE)
            return m.group(0).strip() if m else None
        chips = []
        for p in parti:
            n = _num_pulito(p)
            if n:
                # etichetta = il testo prima del numero (max 20 char)
                lab = p.split(n)[0].strip(" :=-")[:22] if n in p else p[:22]
                chips.append({"valore": n, "label": lab})
        if not chips:
            # concetto: header = una frase CORTA intera; se il testo e lungo/complesso, uso il NOME del fenomeno
            testo = (parti[0] if parti else nb).strip()
            if len(testo) <= 55 and '(' not in testo:
                head = testo  # gia corto e pulito
            else:
                head = nome_fen or testo[:50].rsplit(' ',1)[0]  # il nome del fenomeno e' l'header
            return {"tipo_bersaglio": "concetto", "header_bersaglio": head, "target_chips": []}
        # DOMINANTE (#218): preferisci temperatura (°C), poi pH, poi il primo
        dominante = None
        for c in chips:
            if "C" in c["valore"] or "°" in c["valore"]: dominante = c; break
        if not dominante:
            for c in chips:
                if "pH" in c["valore"]: dominante = c; break
        if not dominante: dominante = chips[0]
        tipo = "numero" if len(chips) == 1 else "multiplo"
        secondari = [c for c in chips if c is not dominante]
        return {"tipo_bersaglio": tipo, "header_bersaglio": dominante["valore"],
                "header_label": dominante.get("label",""), "target_chips": secondari}
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        n_num=0; n_multi=0; n_concetto=0; tot=0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            cs0 = dd.get("contenuto_strutturato") or {}
            if isinstance(cs0,str):
                try: cs0=json.loads(cs0)
                except: cs0={}
            nb = (dd.get("numero_bersaglio") or dd.get("target") or dd.get("numeri")
                  or cs0.get("numero_bersaglio") or cs0.get("numeri") or "")
            if isinstance(nb,(list,dict)): nb=str(nb)
            res = _analizza(nb, nome)
            dd["tipo_bersaglio"] = res["tipo_bersaglio"]
            dd["header_bersaglio"] = res["header_bersaglio"]
            if res.get("header_label"): dd["header_label"] = res["header_label"]
            dd["target_chips"] = res["target_chips"]
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            tot += 1
            if res["tipo_bersaglio"]=="numero": n_num+=1
            elif res["tipo_bersaglio"]=="multiplo": n_multi+=1
            else: n_concetto+=1
            if tot % 50 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"totale": tot, "numero": n_num, "multiplo": n_multi, "concetto": n_concetto})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/admin/calcola-maturita-schede")
def admin_calcola_maturita_schede():
    """Board #53: assegna a ogni fenomeno uno STATO DI MATURITA' (#283) basato su quanti campi sono pieni.
    3 strati (#285): Fondamenta (definizione/principio), Operativita' (punto critico/errori), Esperienza (casi/collegamenti).
    Nessuna scheda 'vuota': ognuna dichiara il suo stato. #282: dichiarata incompleta > finta completa."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        completa=0; espansione=0; fondamenta=0; tot=0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            cs = dd.get("contenuto_strutturato") or {}
            if isinstance(cs, str):
                try: cs = json.loads(cs)
                except: cs = {}
            # STRATO 1 - Fondamenta: definizione/principio/scheda
            has_fondamenta = bool(dd.get("scheda") or cs.get("spiegazione") or cs.get("principio") or dd.get("risposta_cache_it"))
            # STRATO 2 - Operativita': punto critico, errori, numero bersaglio
            has_operativo = bool(cs.get("punto_critico") or dd.get("errori_comuni") or cs.get("errori_comuni") or dd.get("numero_bersaglio") or dd.get("target"))
            # STRATO 3 - Esperienza Matter: esecuzione, tecniche, collegamenti
            has_esperienza = bool(dd.get("esecuzione") or cs.get("esecuzione") or cs.get("casi_reali"))
            n_strati = sum([has_fondamenta, has_operativo, has_esperienza])
            if n_strati >= 3: stato = "completa"; completa+=1
            elif n_strati == 2: stato = "in_completamento"; espansione+=1
            elif n_strati == 1: stato = "fondamenta"; fondamenta+=1
            else: stato = "in_espansione"; espansione+=1
            dd["stato_maturita"] = stato
            dd["strati"] = {"fondamenta": has_fondamenta, "operativita": has_operativo, "esperienza": has_esperienza}
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            tot += 1
            if tot % 50 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"totale": tot, "completa": completa, "in_completamento": espansione,
                        "solo_fondamenta": fondamenta,
                        "indice_copertura_pct": round(completa/tot*100) if tot else 0})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/coverage-score")
def admin_coverage_score():
    """Board #54: Knowledge Coverage Score 0-100 (#293A) + struttura provenienza strato 0 (#294A).
    Lo score pesa i 3 strati; la provenienza traccia fonti/autore/revisione (metadati invisibili)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        dist = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
        somma = 0; tot = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            cs = dd.get("contenuto_strutturato") or {}
            if isinstance(cs, str):
                try: cs = json.loads(cs)
                except: cs = {}
            # Coverage Score pesato: Fondamenta 40, Operativita 35, Esperienza 25
            score = 0
            # Fondamenta (40): definizione/principio
            f = dd.get("scheda") or cs.get("spiegazione") or cs.get("principio") or dd.get("risposta_cache_it") or ""
            if len(str(f)) > 200: score += 40
            elif len(str(f)) > 50: score += 25
            elif f: score += 10
            # Operativita (35): punto critico + errori + numero bersaglio
            op = 0
            if cs.get("punto_critico") or dd.get("punto_critico"): op += 12
            if dd.get("errori_comuni") or cs.get("errori_comuni"): op += 12
            if dd.get("numero_bersaglio") or dd.get("target"): op += 11
            score += op
            # Esperienza Matter (25): esecuzione/casi/collegamenti
            if dd.get("esecuzione") or cs.get("esecuzione"): score += 13
            if cs.get("casi_reali"): score += 12
            score = min(100, score)
            dd["coverage_score"] = score
            # STRATO 0 provenienza (#294A): se non c'e', inizializzo la struttura
            if "provenienza" not in dd:
                dd["provenienza"] = {"fonti": [], "autore_strato1": "", "validato_da": "", "ultima_revisione": "", "stato_pipeline": "da_fare"}
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            somma += score; tot += 1
            if score <= 25: dist["0-25"] += 1
            elif score <= 50: dist["26-50"] += 1
            elif score <= 75: dist["51-75"] += 1
            else: dist["76-100"] += 1
            if tot % 50 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"totale": tot, "score_medio": round(somma/tot) if tot else 0,
                        "distribuzione": dist,
                        "knowledge_coverage_score": round(somma/tot) if tot else 0})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/atlas-studio/coda")
def admin_atlas_coda():
    """Atlas Studio (#300): la CODA di lavorazione - le schede ordinate per costo marginale (#293).
    Prima le 'quasi pronte' (score alto ma non 100): massimo impatto, minimo sforzo."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        schede = []
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            score = dd.get("coverage_score", 0)
            if score >= 100: continue  # gia complete
            strati = dd.get("strati", {})
            mancanti = [k for k in ["fondamenta","operativita","esperienza"] if not strati.get(k)]
            schede.append({"id": nid, "nome": nome, "score": score, "strati_mancanti": mancanti,
                           "provenienza": dd.get("provenienza",{}).get("stato_pipeline","da_fare")})
        # ordino per score DESC (le quasi-pronte prima - minimo sforzo per completarle)
        schede.sort(key=lambda x: -x["score"])
        return jsonify({"totale_da_lavorare": len(schede),
                        "quasi_pronte": [s for s in schede if s["score"] >= 65][:30],
                        "coda_completa": schede[:100]})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/atlas-studio")
def atlas_studio():
    """Atlas Studio (#300): il laboratorio editoriale interno. Serve la pagina (auto-protetta col secret)."""
    return render_template("atlas-studio.html")




@bp.route("/admin/atlas-studio/salva", methods=["POST"])
def admin_atlas_salva():
    """Salva il contenuto di uno strato + ricalcola coverage_score."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    slug = d.get("slug", ""); strato = d.get("strato", ""); testo = d.get("testo", "")
    fonti_in = d.get("fonti", [])
    if not slug or not strato:
        return jsonify({"errore": "manca slug o strato"}), 400
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE id=%s OR LOWER(name) LIKE LOWER(%s) LIMIT 1", (slug, f"%{slug}%"))
        r = cur.fetchone()
        if not r: return jsonify({"errore": "non trovata"})
        dd = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
        # mappo lo strato al campo giusto
        if strato == "fondamenta": dd["scheda"] = testo
        elif strato == "operativita": dd["errori_comuni"] = testo
        elif strato == "esperienza": dd["esecuzione"] = testo
        # provenienza
        prov = dd.get("provenienza", {})
        prov["ultima_revisione"] = "curatore"
        if fonti_in:
            _ff = prov.get("fonti", [])
            for _f in fonti_in:
                if _f not in _ff: _ff.append(_f)
            prov["fonti"] = _ff[:8]
        dd["provenienza"] = prov
        if not dd.get("stato_editoriale"): dd["stato_editoriale"] = "ai_generated"
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), r[0]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"slug": r[0], "strato": strato, "salvato": True})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/atlas-studio/stato", methods=["POST"])
def admin_atlas_stato():
    """Sposta la scheda tra le colonne pipeline (da_fare->ai_pronta->in_revisione->validata->pubblicata)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    slug = d.get("slug", ""); nuovo = d.get("nuovo_stato", "")
    validi = ["da_fare", "ai_pronta", "in_revisione", "validata", "pubblicata", "ai_generated", "ai_verified", "curated", "canon"]
    if nuovo not in validi:
        return jsonify({"errore": f"stato non valido, usa: {validi}"}), 400
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE id=%s OR LOWER(name) LIKE LOWER(%s) LIMIT 1", (slug, f"%{slug}%"))
        r = cur.fetchone()
        if not r: return jsonify({"errore": "non trovata"})
        dd = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
        prov = dd.get("provenienza", {})
        prov["stato_pipeline"] = nuovo
        dd["provenienza"] = prov
        # stato editoriale visibile all'utente (#304)
        if nuovo in ("ai_generated","ai_verified","curated","canon"):
            dd["stato_editoriale"] = nuovo
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), r[0]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"slug": r[0], "nuovo_stato": nuovo, "spostata": True})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


# ═══ KNOWLEDGE COMPILER (Board #56): versionamento + gate + circuit breaker ═══

# GERARCHIA FONTI (#309/#309A) - Tier 0 italiano + internazionali
_FONTI_TIER = {
    0: ["disciplinare dop", "disciplinare igp", "slow food", "presidi slow food", "aibi", "ministero",
        "gazzetta ufficiale", "consorzio", "accademia italiana della cucina", "ismea"],
    1: ["mcgee", "on food and cooking", "modernist cuisine", "modernist bread", "myhrvold", "this",
        "harold mcgee", "peer-reviewed", "journal of food"],
    2: ["hamelman", "suas", "advanced bread", "difford", "liquid intelligence", "arnold",
        "professional chef", "culinary institute", "the food lab"],
    3: ["king arthur", "serious eats", "kenji", "la cucina italiana", "gambero rosso"],
}


# REGISTRO OPERE NOTE (#310A: fonti = entita verificate, non stringhe). Coppie autore/opera REALI.
_OPERE_NOTE = {
    "mcgee": ["on food and cooking", "il cibo e la cucina", "keys to good cooking"],
    "myhrvold": ["modernist cuisine", "modernist bread", "modernist pizza"],
    "hamelman": ["bread"],
    "suas": ["advanced bread and pastry"],
    "this": ["gastronomia molecolare", "molecular gastronomy", "casseroles and clay pots"],
    "arnold": ["liquid intelligence"],
    "difford": ["difford's guide"],
    "mcgee harold": ["on food and cooking"],
    "reinhart": ["the bread baker's apprentice", "crust and crumb"],
    "calvel": ["the taste of bread", "le gout du pain"],
    "bertinet": ["dough", "crust"],
    "cia": ["the professional chef"],
    "culinary institute": ["the professional chef"],
    "this": ["gastronomia molecolare", "molecular gastronomy", "casseroles and clay pots", "the science of the oven"],
    "herve this": ["gastronomia molecolare", "molecular gastronomy"],
    "corriher": ["cookwise", "bakewise"],
    "ruhlman": ["ratio", "the elements of cooking"],
    "lopez-alt": ["the food lab"],
    "kenji": ["the food lab"],
    "migoya": ["the elements of dessert", "frozen desserts"],
    "francisco migoya": ["the elements of dessert", "modernist bread", "modernist pizza"],
    "blumenthal": ["the fat duck cookbook", "heston blumenthal at home"],
    "adria": ["el bulli", "the family meal"],
    "ferran adria": ["el bulli"],
    "mcgee harold": ["on food and cooking", "keys to good cooking", "nose dive"],
    "harold mcgee": ["on food and cooking", "keys to good cooking"],
    "davide cassi": ["il gelato estremo", "la scienza in cucina"],
    "bressanini": ["la scienza della pasticceria", "la scienza della carne", "pane e bugie", "la scienza delle pulizie"],
    "dario bressanini": ["la scienza della pasticceria", "la scienza della carne", "la scienza delle verdure"],
}

def _fonte_verificata(testo_fonte):
    """#310A: verifica che la fonte sia una coppia autore/opera NOTA (anti-allucinazione)."""
    t = (testo_fonte or "").lower()
    # se cita un autore noto, l'opera deve essere tra le sue opere reali
    for autore, opere in _OPERE_NOTE.items():
        if autore in t:
            # l'autore c'e': l'opera citata e' tra le sue? (match tollerante su parole chiave)
            for op in opere:
                # match se l'opera intera c'e', o almeno le sue parole significative (>3 char)
                parole_op = [w for w in op.split() if len(w) > 3]
                if op in t or (parole_op and all(w in t for w in parole_op[:2])):
                    return True  # coppia verificata
            # autore noto ma opera non riconosciuta -> sospetta SOLO se non e' solo il cognome
            # (se e' solo "McGee" senza opera, non e' una fonte formattata male: e' una menzione)
            if len(t.strip()) > len(autore) + 8:  # c'e' altro testo oltre il cognome
                return "sospetta"
            return "non_verificata"  # solo il cognome, non giudico
    # disciplinari/istituzioni italiane (Tier 0) - riconosciute per keyword
    if any(k in t for k in ["disciplinare", "slow food", "dop", "igp", "accademia italiana", "aibi"]):
        return True
    return "non_verificata"  # fonte non nel registro (non per forza falsa, ma non verificabile)


def _classifica_fonte(testo_fonte):
    """Classifica una fonte nel suo Tier (#310A: fonti = entita verificate)."""
    t = (testo_fonte or "").lower()
    for tier in [0, 1, 2, 3]:
        if any(k in t for k in _FONTI_TIER[tier]):
            return tier
    return 4  # fonte non riconosciuta / bassa affidabilita


@bp.route("/admin/compiler/valida", methods=["POST"])
def admin_compiler_valida():
    """Knowledge Compiler (#308A): valida una scheda coi due Gate. Se fallisce, NON passa a ai_verified.
    Gate A (sintattico #310): forma. Gate B (semantico #310): fonti Tier 0-2, coerenza numerica."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    slug = d.get("slug", "")
    if not slug: return jsonify({"errore": "manca slug"}), 400
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE (id=%s OR LOWER(name) LIKE LOWER(%s)) AND type IN ('Fenomeno','Tecnica') LIMIT 1", (slug, f"%{slug}%"))
        r = cur.fetchone()
        if not r: return jsonify({"errore": "non trovata"})
        dd = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
        testo_tot = str(dd.get("scheda","")) + str(dd.get("errori_comuni","")) + str(dd.get("esecuzione",""))
        gate_a = {"passato": True, "problemi": []}
        gate_b = {"passato": True, "problemi": []}
        # GATE A - SINTATTICO (#310): forma
        if len(testo_tot) < 150: gate_a["passato"]=False; gate_a["problemi"].append("contenuto troppo breve")
        if "non trovo" in testo_tot.lower() or "non disponibile" in testo_tot.lower():
            gate_a["passato"]=False; gate_a["problemi"].append("contiene 'non trovo dati'")
        # GATE B - SEMANTICO (#310, #309A): fonti + coerenza numerica
        fonti = dd.get("provenienza",{}).get("fonti",[])
        if not fonti:
            # estraggo le fonti dal testo (dopo "FONTI:")
            m = re.search(r"FONTI?:(.+?)(?:CONFIDENZA|$)", testo_tot, re.IGNORECASE|re.DOTALL)
            if m: fonti = [x.strip() for x in re.split(r"[;\n]", m.group(1)) if x.strip() and len(x.strip())>5][:5]
        tiers = [_classifica_fonte(f) for f in fonti]
        has_autorevole = any(t <= 2 for t in tiers)  # #309A: almeno una Tier 0-2
        if not fonti: gate_b["passato"]=False; gate_b["problemi"].append("nessuna fonte citata")
        elif not has_autorevole: gate_b["passato"]=False; gate_b["problemi"].append("nessuna fonte Tier 0-2 (solo blog)")
        # GATE ANTI-ALLUCINAZIONE (#310A): le fonti autorevoli citate sono coppie autore/opera REALI?
        sospette = [f for f in fonti if _fonte_verificata(f) == "sospetta"]
        if sospette:
            gate_b["passato"]=False
            gate_b["problemi"].append(f"possibile fonte allucinata (autore noto, opera non riconosciuta): {sospette[0][:40]}")
        # coerenza numerica: temperature assurde
        temps = re.findall(r"(\d{2,3})\s*°?\s*[cC]", testo_tot)
        for tp in temps:
            if int(tp) > 300: gate_b["problemi"].append(f"temperatura sospetta: {tp}C"); gate_b["passato"]=False
        # ESITO
        compilata = gate_a["passato"] and gate_b["passato"]
        nuovo_stato = "ai_verified" if compilata else "ai_generated"
        dd["stato_editoriale"] = nuovo_stato
        dd["fonti_tier"] = min(tiers) if tiers else 4
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), r[0]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"slug": r[0], "compilata": compilata, "stato": nuovo_stato,
                        "gate_a": gate_a, "gate_b": gate_b,
                        "fonti_trovate": len(fonti), "tier_migliore": min(tiers) if tiers else 4})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/compiler/versiona", methods=["POST"])
def admin_compiler_versiona():
    """Versionamento (#312A): salva uno snapshot della scheda prima di modificarla. Reversibile."""
    from flask import request, jsonify
    import os, psycopg2, json, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    slug = d.get("slug", "")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE id=%s OR LOWER(name) LIKE LOWER(%s) LIMIT 1", (slug, f"%{slug}%"))
        r = cur.fetchone()
        if not r: return jsonify({"errore": "non trovata"})
        dd = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
        versioni = dd.get("_versioni", [])
        # snapshot dei campi contenuto (non tutto il nodo, solo cio' che cambia)
        snap = {"ts": int(time.time()), "scheda": dd.get("scheda",""), "errori_comuni": dd.get("errori_comuni",""),
                "esecuzione": dd.get("esecuzione",""), "stato_editoriale": dd.get("stato_editoriale","")}
        versioni.append(snap)
        dd["_versioni"] = versioni[-10:]  # tengo le ultime 10
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), r[0]))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"slug": r[0], "versione_salvata": len(versioni), "versioni_totali": len(dd["_versioni"])})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/knowledge-density")
def admin_knowledge_density():
    """Board #57 (#322A): Knowledge Density Index per ingrediente = quante RELAZIONI genera nel grafo.
    Prima i collegamenti, poi i composti (#322): un ingrediente vale per le sue relazioni, non i dati isolati."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    limite = int(request.args.get("limite", "0"))  # 0 = tutti, altrimenti processa N
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        lim = limite if limite else 200  # batch di default 200 (evita timeout)
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto') LIMIT %s", (lim,))
        rows = cur.fetchall()
        ids = [r[0] for r in rows]
        # UNA query aggregata per TUTTI gli archi degli ingredienti del batch (invece di 3 per ognuno)
        archi = {}
        if ids:
            cur.execute("""SELECT from_id, relation, COUNT(*) FROM edges WHERE from_id = ANY(%s)
                           GROUP BY from_id, relation""", (ids,))
            for fid, rel, cnt in cur.fetchall():
                archi.setdefault(fid, {})[rel] = cnt
        dist = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
        poveri = []; tot = 0; somma = 0
        for nid, nome, data in rows:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            a = archi.get(nid, {})
            score = 0
            if dd.get("proprieta"): score += min(20, len(dd.get("proprieta",{}))*3)
            if dd.get("operativo"): score += 15
            if dd.get("territorio") or dd.get("regione"): score += 10
            if dd.get("tutela"): score += 5
            nf = a.get("governato_da",0)+a.get("sfrutta_fenomeno",0)+a.get("coinvolge",0); score += min(20, nf*7)
            score += min(15, a.get("abbinamento_aromatico",0)*3)
            score += min(15, a.get("contiene_composto",0))
            score = min(100, score)
            dd["knowledge_density"] = score
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            tot += 1; somma += score
            if score <= 25:
                dist["0-25"] += 1
                if len(poveri) < 30: poveri.append(nome)
            elif score <= 50: dist["26-50"] += 1
            elif score <= 75: dist["51-75"] += 1
            else: dist["76-100"] += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"totale": tot, "density_media": round(somma/tot) if tot else 0,
                        "distribuzione": dist, "esempi_poveri_da_arricchire": poveri[:20]})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/atlas-studio/batch", methods=["POST"])
def admin_atlas_batch():
    """Batch generation con CIRCUIT BREAKER (#311A): genera N schede a ondata, si ferma se troppe falliscono.
    Impedisce il 'disastro x300' (#308). Ondate piccole, controllo, stop automatico se errori sopra soglia."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, time
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    n_ondata = min(int(d.get("n", 6)), 8)  # max 8 per ondata (evita timeout Railway ~55s)
    soglia_errori = int(d.get("soglia", 3))  # stop se piu' di N falliscono
    solo_dominio = d.get("dominio", "")  # es. "pane" per filtrare
    key = os.environ.get("OPENAI_API_KEY", "")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # prendo le schede NON ancora complete/verified, direttamente in SQL (coverage < 100 o stato non verified)
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND COALESCE(data->>'stato_editoriale','') NOT IN ('ai_verified','curated','canon')
                       ORDER BY (data->>'coverage_score')::int DESC NULLS LAST LIMIT 60""")
        candidate = cur.fetchall()
        # DESC: prendo prima le "quasi pronte" (score alto ma non verified) - massimo impatto minimo sforzo
        processate = []; falliti = 0; compilate = 0; interrotto = False
        for nid, nome, data in candidate:
            if len(processate) >= n_ondata: break
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            if dd.get("stato_editoriale") in ("ai_verified","curated","canon"): continue  # gia' fatta
            # genero TUTTI E 3 GLI STRATI (Fondamenta + Operativita + Esperienza) in una chiamata
            try:
                import re as _re
                sys = (f"Esperto scienza alimenti per Matter. Fenomeno: {nome}. Scrivi una scheda in 3 blocchi: "
                       f"[FONDAMENTA] definizione, perche' succede, meccanismo (80-120 parole). "
                       f"[OPERATIVITA] punto critico, errori comuni, segnali, range temperatura/tempo se pertinente (80-120 parole). "
                       f"[ESPERIENZA] il segnale pratico che un professionista riconosce al banco, l'errore piu' comune (60-90 parole). "
                       f"VIETATO blog/link. Cita SOLO libri autorevoli (McGee 'On Food and Cooking', Hamelman 'Bread', "
                       f"Modernist Cuisine/Bread di Myhrvold, Suas 'Advanced Bread and Pastry', Arnold 'Liquid Intelligence', "
                       f"Reinhart, Calvel, This) dal tuo training. Usa ESATTAMENTE i marcatori [FONDAMENTA] [OPERATIVITA] "
                       f"[ESPERIENZA]. Fine: FONTI: Cognome, Titolo (anno); Cognome, Titolo (anno) e CONFIDENZA: alta/media/bassa.")
                payload = {"model": "gpt-4o", "max_tokens": 1100,
                           "messages": [{"role":"system","content":sys},{"role":"user","content":"Scrivi la scheda completa nei 3 blocchi."}]}
                req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                rr = ur.urlopen(req, timeout=70); testo = json.loads(rr.read().decode())["choices"][0]["message"]["content"]
                # estraggo i 3 blocchi
                def _blocco(nome_b, testo):
                    m = _re.search(r"\[" + nome_b + r"\](.+?)(?:\[[A-Z]|FONTI|CONFIDENZA|$)", testo, _re.IGNORECASE|_re.DOTALL)
                    return m.group(1).strip() if m else ""
                fond = _blocco("FONDAMENTA", testo); oper = _blocco("OPERATIVITA", testo); esp = _blocco("ESPERIENZA", testo)
                # uno strato "conta" solo se ha contenuto REALE (>60 char). Se i marcatori mancano, l'AI ha
                # scritto tutto insieme: NON spezzo male, salvo tutto in fondamenta e gli altri restano vuoti.
                fond_ok = len(fond) > 60; oper_ok = len(oper) > 60; esp_ok = len(esp) > 60
                if not (oper_ok or esp_ok) and len(testo) > 200:
                    # l'AI non ha usato i marcatori: metto tutto il testo (meno le fonti) in fondamenta
                    _txt = _re.split(r"FONTI?:", testo, flags=_re.IGNORECASE)[0].strip()
                    fond = _txt; fond_ok = True; oper_ok = esp_ok = False
                if fond_ok: dd["scheda"] = fond
                if oper_ok: dd["errori_comuni"] = oper
                if esp_ok: dd["esecuzione"] = esp
                # fonti
                _m = _re.search(r"FONTI?:(.+?)(?:CONFIDENZA|$)", testo, _re.IGNORECASE|_re.DOTALL)
                fonti = [x.strip(" .-") for x in _re.split(r"[;\n]", _m.group(1))] if _m else []
                fonti = [f for f in fonti if len(f) > 5][:4]
                prov = dd.get("provenienza", {}); prov["fonti"] = fonti; dd["provenienza"] = prov
                # strati presenti (solo se contenuto reale)
                dd["strati"] = {"fondamenta": fond_ok, "operativita": oper_ok, "esperienza": esp_ok}
                n_strati = sum([fond_ok, oper_ok, esp_ok])
                sc = (40 if fond_ok else 0) + (35 if oper_ok else 0) + (25 if esp_ok else 0)
                dd["coverage_score"] = sc
                tiers = [_classifica_fonte(f) for f in fonti]
                fonti_ok = any(t <= 2 for t in tiers) and not any(_fonte_verificata(f)=="sospetta" for f in fonti)
                # verified richiede almeno 2 strati REALI + fonti buone
                ok = fonti_ok and n_strati >= 2
                dd["stato_maturita"] = "completa" if (n_strati == 3 and fonti_ok) else ("in_completamento" if n_strati==2 else "in_espansione")
                dd["stato_editoriale"] = "ai_verified" if ok else "ai_generated"
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                conn.commit()
                if ok: compilate += 1
                else: falliti += 1
                processate.append({"nome": nome, "compilata": ok, "strati": sum([bool(fond),bool(oper),bool(esp)]), "fonti": len(fonti)})
                if falliti > soglia_errori:
                    interrotto = True
                    break
            except Exception as _e:
                falliti += 1; processate.append({"nome": nome, "errore": str(_e)[:40]})
                if falliti > soglia_errori: interrotto = True; break
        cur.close(); conn.close()
        return jsonify({"ondata": len(processate), "compilate": compilate, "falliti": falliti,
                        "circuit_breaker_scattato": interrotto,
                        "dettaglio": processate,
                        "nota": "STOP: troppi errori" if interrotto else "Ondata ok, puoi lanciare la successiva"})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/marca-nodi-grezzi")
def admin_marca_nodi_grezzi():
    """Pulizia: marca i nodi con nomi grezzi (ahn: 'barosma_pulchella_oil') come nascosti dall'utente.
    Restano nel grafo per i composti, ma non appaiono in ricerca/abbinamenti (qualita' percepita)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        marcati = 0
        for nid, nome, data in cur.fetchall():
            n = nome or ""
            # nome grezzo: ha underscore E e' tutto minuscolo (stile ahn) e non gia' marcato
            if "_" in n and n == n.lower():
                dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
                if not dd.get("nascosto_utente"):
                    dd["nascosto_utente"] = True
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                    marcati += 1
            if marcati % 100 == 0 and marcati: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"nodi_grezzi_nascosti": marcati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




@bp.route("/admin/categorizza-schede")
def admin_categorizza_schede():
    """Board #64 #376: nessuna scheda vive in 'Altro'. Assegna una categoria a tutte le schede senza."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # parole chiave -> categoria (tassonomia fissa)
    MAP = {
        "bar": ["cocktail","drink","shake","sour","distillat","liquore","bitter","sciroppo","carbonaz","gin","rum","vermouth","amaro","fat wash","milk punch","clarific","infus","macera","stir","muddle","batch","diluizion"],
        "caffe": ["caffe","espresso","estrazione","tamping","grooming","wdt","macinac","brew","pour over","moka","crema caffe","grind","dose caffe","purging"],
        "panificazione": ["impasto","lievit","farina","idratazione","autolisi","biga","poolish","pieghe","forno","pane","pizza","glutine","maglia","formatura","pirlatura","cottura pane","crosta","alveol","bassinage","ddt","preferimenti"],
        "pasticceria": ["crema","pasticc","meringa","zucchero","caramell","cioccolat","temperaggio","ganache","frolla","choux","biscott","dolce","glass","pan di spagna","bagna","gelatina"],
        "gelateria": ["gelato","sorbetto","mantecaz","pac","overrun","stabilizz","sfere","mix gelato","catena del freddo","antifreez"],
        "cucina": ["cottura","brasa","arrost","frittura","saltat","confit","sous vide","roner","maillard","riduzione","fondo","emulsion","salsa","sbianch","imbiondire","glassatura verdure","deglassare","frollatura","salagione","curing","affumicat","carne","bassa temperatura"],
        "birra": ["birra","ammostamento","mashing","luppolo","dry hop","fermentazione birra","mosto"],
        "vino": ["vino","svinatura","macerazione uve","tannin","solfiti","fermentazione vino"],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        assegnate = 0; gia = 0; senza = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            if dd.get("categoria") and dd.get("categoria") not in ("", "?", "Altro", "SENZA"):
                gia += 1; continue
            testo = (nome + " " + str(dd.get("scheda",""))[:200]).lower()
            cat = None
            for c, kws in MAP.items():
                if any(k in testo for k in kws): cat = c; break
            if not cat: cat = "trasversale"  # mai "Altro": trasversale come fallback dignitoso
            dd["categoria"] = cat
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            assegnate += 1
            if assegnate % 50 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"assegnate": assegnate, "gia_categorizzate": gia, "nessuna_in_altro": True})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




# ═══ EVIDENCE LAYER (Costituzione Art.3 #424): le fonti come nodi condivisi, non testo sparso ═══
_EVIDENCE_CANON = {
    # chiave di riconoscimento -> nodo Evidence pulito {nome, autore, anno, tier, asin, tipo}
    "mcgee": {"id":"ev-mcgee","nome":"On Food and Cooking","autore":"Harold McGee","anno":2004,"tier":1,"asin":"0684800012","tipo":"libro"},
    "hamelman": {"id":"ev-hamelman","nome":"Bread","autore":"Jeffrey Hamelman","anno":2004,"tier":1,"asin":"0471168572","tipo":"libro"},
    "modernist": {"id":"ev-modernist","nome":"Modernist Cuisine","autore":"Nathan Myhrvold","anno":2011,"tier":1,"asin":"0982761007","tipo":"libro"},
    "arnold": {"id":"ev-arnold","nome":"Liquid Intelligence","autore":"Dave Arnold","anno":2014,"tier":1,"asin":"0393089037","tipo":"libro"},
    "suas": {"id":"ev-suas","nome":"Advanced Bread and Pastry","autore":"Michel Suas","anno":2008,"tier":2,"asin":"1418011694","tipo":"libro"},
    "calvel": {"id":"ev-calvel","nome":"The Taste of Bread","autore":"Raymond Calvel","anno":2001,"tier":2,"asin":"0834216469","tipo":"libro"},
    "this": {"id":"ev-this","nome":"Gastronomia molecolare","autore":"Hervé This","anno":2001,"tier":1,"tipo":"libro"},
    "bressanini": {"id":"ev-bressanini","nome":"La scienza della pasticceria","autore":"Dario Bressanini","anno":2014,"tier":1,"tipo":"libro"},
    "reinhart": {"id":"ev-reinhart","nome":"The Bread Baker's Apprentice","autore":"Peter Reinhart","anno":2001,"tier":2,"tipo":"libro"},
    "corriher": {"id":"ev-corriher","nome":"CookWise","autore":"Shirley Corriher","anno":1997,"tier":2,"tipo":"libro"},
    "usda": {"id":"ev-usda","nome":"USDA FoodData Central","autore":"USDA","anno":2024,"tier":0,"tipo":"database"},
}
def _riconosci_evidence(testo_fonte):
    """Da una fonte scritta caoticamente -> la chiave canonica, o None se blog/grezzo."""
    t = (testo_fonte or "").lower()
    if any(b in t for b in ['http','www.','.it/','.com/','blog','.net']): return None  # blog/url: scartati
    for chiave in _EVIDENCE_CANON:
        if chiave in t: return chiave
    return None

@bp.route("/admin/evidence/costruisci")
def admin_evidence_costruisci():
    """Costituzione Art.3: costruisce l'EVIDENCE LAYER. Crea i nodi Evidence canonici e collega ogni scheda
    (che cita quella fonte in modo caotico) al nodo pulito. McGee scritto in 6 modi -> 1 nodo condiviso."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # 1. creo i nodi Evidence (se non esistono)
        creati = 0
        for chiave, ev in _EVIDENCE_CANON.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s", (ev["id"],))
            if not cur.fetchone():
                data = dict(ev); data["kind"]="evidence"; data["livello"]="curated"
                cur.execute("INSERT INTO nodes (id, name, type, data) VALUES (%s,%s,'Evidence',%s)",
                            (ev["id"], ev["nome"], json.dumps(data, ensure_ascii=False)))
                creati += 1
        conn.commit()
        # 2. per ogni scheda con fonti, normalizzo e collego al nodo Evidence
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        schede_collegate = 0; link_creati = 0; blog_scartati = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            fonti_raw = dd.get("fonti") or (dd.get("provenienza",{}) or {}).get("fonti") or []
            if not fonti_raw: continue
            evidence_ids = []
            for f in fonti_raw:
                chiave = _riconosci_evidence(str(f))
                if chiave:
                    ev_id = _EVIDENCE_CANON[chiave]["id"]
                    if ev_id not in evidence_ids: evidence_ids.append(ev_id)
                    # arco scheda -> evidence
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='ha_evidence'", (nid, ev_id))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id, to_id, relation) VALUES (%s,%s,'ha_evidence')", (nid, ev_id))
                        link_creati += 1
                elif any(b in str(f).lower() for b in ['http','www','blog','.it/','.com/']):
                    blog_scartati += 1
            if evidence_ids:
                # salvo gli evidence_ids puliti nella scheda (sostituiscono le fonti caotiche)
                dd["evidence"] = evidence_ids
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
                schede_collegate += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"nodi_evidence_creati": creati, "schede_collegate": schede_collegate,
                        "link_creati": link_creati, "blog_scartati": blog_scartati,
                        "nota": "Evidence Layer costruito: le fonti sono nodi condivisi, i blog scartati."})
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})

@bp.route("/v1/evidence/<ev_id>")
def get_evidence(ev_id):
    """La scheda di una fonte: cosa e', chi la cita, il link Biblioteca."""
    from flask import jsonify
    import os, psycopg2, json
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT data FROM nodes WHERE id=%s AND type='Evidence'", (ev_id,))
        r = cur.fetchone()
        if not r: return jsonify({"errore":"evidence non trovata"}), 404
        ev = r[0] if isinstance(r[0], dict) else json.loads(r[0])
        # chi la cita
        cur.execute("SELECT n.name FROM edges e JOIN nodes n ON n.id=e.from_id WHERE e.to_id=%s AND e.relation='ha_evidence' LIMIT 20", (ev_id,))
        citata_da = [x[0] for x in cur.fetchall()]
        cur.close(); conn.close()
        ev["citata_da"] = citata_da; ev["n_citazioni"] = len(citata_da)
        return jsonify(ev)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})



@bp.route("/v1/fenomeno/<slug>/causalita")
def get_causalita(slug):
    """La causalita di un fenomeno: cosa lo accelera/rallenta + conseguenze."""
    from flask import jsonify
    import os, psycopg2, json
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT data FROM nodes WHERE (id=%s OR data->>'slug'=%s) AND type IN ('Fenomeno','Tecnica') LIMIT 1", (slug, slug))
        r = cur.fetchone(); cur.close(); conn.close()
        if not r: return jsonify({"errore":"fenomeno non trovato"}), 404
        dd = r[0] if isinstance(r[0], dict) else json.loads(r[0])
        caus = dd.get("causalita")
        if not caus: return jsonify({"slug":slug, "causalita": None, "nota":"causalita non ancora generata"})
        return jsonify({"slug": slug, "nome": dd.get("nome"), "causalita": caus})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})




# ═══ GOVERNANCE DEGLI ARCHI (Board 65F #463 #472): ogni arco ha pedigree + confidenza ═══
# La confidenza per tipo di arco: quanto ci si puo' fidare di quell'abbinamento/relazione.
_ARCO_CONFIDENZA = {
    "abbinamento_tradizionale": {"livello": "alta", "layer": "tradizione", "fonte": "documentato"},
    "tradizione": {"livello": "alta", "layer": "tradizione", "fonte": "documentato"},
    "abbinamento_aromatico": {"livello": "bassa", "layer": "scoperta", "fonte": "ahn_molecolare"},
    "contiene_composto": {"livello": "tecnico", "layer": "dato", "fonte": "ahn"},
    "ha_evidence": {"livello": "alta", "layer": "evidence", "fonte": "biblioteca"},
    "sfrutta_fenomeno": {"livello": "media", "layer": "scientifico", "fonte": "grafo"},
    "governato_da": {"livello": "media", "layer": "scientifico", "fonte": "grafo"},
}

@bp.route("/admin/grafo/governance")
def admin_grafo_governance():
    """Board 65F: censisce gli archi per tipo e assegna PEDIGREE + CONFIDENZA. Gli archi molecolari
    (Ahn) restano nel layer SCOPERTA (bassa fiducia), mai spacciati per tradizione. Diagnosi del grafo."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # censimento: quanti archi per tipo
        cur.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC")
        censimento = []
        for relation, n in cur.fetchall():
            gov = _ARCO_CONFIDENZA.get(relation, {"livello": "sconosciuta", "layer": "non_classificato", "fonte": "?"})
            censimento.append({"relation": relation, "n": n, **gov})
        cur.close(); conn.close()
        # diagnosi: quanti archi alta fiducia (tradizione) vs bassa (scoperta molecolare)
        alta = sum(c["n"] for c in censimento if c.get("livello")=="alta")
        bassa = sum(c["n"] for c in censimento if c.get("livello")=="bassa")
        return jsonify({
            "censimento": censimento,
            "diagnosi": {
                "archi_alta_fiducia": alta, "archi_bassa_fiducia_molecolare": bassa,
                "nota": ("Se bassa >> alta, il grafo e' dominato da abbinamenti molecolari (scoperta), "
                         "non da tradizione documentata. La tradizione va arricchita.") if bassa > alta*2 else "equilibrio ok"
            },
            "regola": "Gli archi 'abbinamento_aromatico' (Ahn) restano layer SCOPERTA (bassa). Mai in Tradizione. Lo Score di Senso li filtra."
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})



@bp.route("/admin/composti-top")
def admin_composti_top():
    """Diagnostico: i composti aromatici piu' comuni nel grafo (per ampliare il dizionario spiegazioni)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # i nodi piu' referenziati come composto (to_id di contiene_composto)
        cur.execute("""SELECT n.name, COUNT(*) c FROM edges e JOIN nodes n ON n.id=e.to_id
                       WHERE e.relation='contiene_composto' GROUP BY n.name ORDER BY c DESC LIMIT 40""")
        composti = [{"nome": r[0], "in_n_ingredienti": r[1]} for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"composti_piu_comuni": composti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/leggi-nodo/<nid>")
def admin_leggi_nodo(nid):
    """Legge un nodo per ID esatto (per progettare il Protocollo dalle ricette esistenti)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, type, data FROM nodes WHERE id=%s", (nid,))
        r = cur.fetchone()
        if not r: cur.close(); conn.close(); return jsonify({"errore":"nodo non trovato"}), 404
        dd = r[3] if isinstance(r[3], dict) else (json.loads(r[3]) if r[3] else {})
        # archi in uscita (ingredienti, tecniche...)
        cur.execute("""SELECT e.relation, n.name FROM edges e JOIN nodes n ON n.id=e.to_id
                       WHERE e.from_id=%s LIMIT 30""", (nid,))
        archi = [{"relation": x[0], "verso": x[1]} for x in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"id": r[0], "nome": r[1], "type": r[2], "data": dd, "archi_uscita": archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})



# [RIMOSSA] route /v1/protocollo duplicata - ora la serve routes/api.py (leggi_protocollo, schema nuovo)


# ═══ RIEMPITORE AUTOMATICO: macina TUTTE le ondate da solo (causalita, tradizione, protocolli, schede) ═══
_RIEMPITORE_STATO = {"attivo": False, "fase": "", "fatti": {}, "iniziato": "", "ultimo": "", "chiamate_ai": 0}

def _valida_ai(tipo, soggetto, contenuto):
    """GATE: una seconda AI valida il lavoro della prima. Ritorna (ok: bool, motivo: str).
    tipo = 'causalita' | 'tradizione' | 'protocollo'. Controlla la correttezza scientifica/culinaria."""
    import os, json, urllib.request as ur
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return (True, "no-key")  # senza key, non blocco (fail-open)
    try:
        if tipo == "causalita":
            dom = (f"Fenomeno: {soggetto}. Causalita proposta: {json.dumps(contenuto,ensure_ascii=False)[:600]}. "
                   f"Verifica: gli acceleranti/rallentanti sono scientificamente CORRETTI per questo fenomeno? "
                   f"Un fattore non puo' accelerare E rallentare. Rispondi JSON {{\"ok\":true/false,\"motivo\":\"...\"}}.")
        elif tipo == "tradizione":
            dom = (f"Ingrediente: {soggetto}. Abbinamento proposto: {json.dumps(contenuto,ensure_ascii=False)[:400]}. "
                   f"Verifica: il PIATTO citato esiste DAVVERO e usa quell'abbinamento? Non inventato? "
                   f"Rispondi JSON {{\"ok\":true/false,\"motivo\":\"...\"}}.")
        else:  # protocollo
            dom = (f"Preparazione: {soggetto}. Dati: {json.dumps(contenuto,ensure_ascii=False)[:600]}. "
                   f"Verifica: il bersaglio e' plausibile? l'ipotesi e la diagnosi sono corrette? "
                   f"Rispondi JSON {{\"ok\":true/false,\"motivo\":\"...\"}}.")
        pl = {"model":"gpt-4o-mini","max_tokens":150,"temperature":0,
              "messages":[{"role":"system","content":"Sei un revisore di food science equilibrato. Approva se il contenuto e ragionevole e plausibile. Blocca SOLO errori gravi ed evidenti (abbinamenti palesemente inventati, bersagli assurdi, contraddizioni chiare). Nel dubbio APPROVA."},
                          {"role":"user","content":dom}]}
        rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
        tx = json.loads(ur.urlopen(rq, timeout=30).read().decode())["choices"][0]["message"]["content"]
        import re as _re
        m = _re.search(r'\{.*\}', tx, _re.DOTALL)
        if m:
            v = json.loads(m.group(0))
            return (bool(v.get("ok", True)), str(v.get("motivo",""))[:80])
        return (True, "parse-fail")  # se non parsa, non blocco
    except Exception:
        return (True, "err")  # fail-open: in caso di errore non blocco (meglio salvare che perdere)

# Ingredienti base che hanno VARIETA reali (biodiversita 65G) - non tutti ce l'hanno
_BASE_CON_VARIETA = ["pomodoro","mela","patata","cipolla","riso","mozzarella","limone","pera","pesca",
    "uva","fragola","arancia","carota","zucca","melanzana","zucchina","fagiolo","lenticchia","cece",
    "grano","farro","orzo","avena","mais","caffè","cacao","oliva","basilico","peperoncino","aglio",
    "fungo","radicchio","cavolo","broccolo","finocchio","carciofo","asparago","spinaci","lattuga",
    "prugna","ciliegia","albicocca","fico","melone","anguria","kiwi","mandorla","nocciola","noce",
    "castagna","miele","olio extravergine di oliva","aceto","vino","birra","tè","pomodorino"]

def _riempitore_worker(max_ondate):
    import os, psycopg2, json, urllib.request as ur, time, datetime
    global _RIEMPITORE_STATO
    _RIEMPITORE_STATO = {"attivo": True, "fase": "avvio", "fatti": {"causalita":0,"tradizione":0,"protocolli":0,"varieta":0},
                         "iniziato": datetime.datetime.now().isoformat()[:19], "ultimo": ""}
    key = os.environ.get("OPENAI_API_KEY", "")
    DB = os.environ["DATABASE_URL"]
    def _log(msg):
        _RIEMPITORE_STATO["ultimo"] = msg
    try:
        # FASE 0: FIX IPOTESI placeholder (priorita: serve al frontend)
        _RIEMPITORE_STATO["fase"] = "fix_ipotesi"
        for giro in range(max_ondate):
            if not _RIEMPITORE_STATO["attivo"]: return
            conn = psycopg2.connect(DB); cur = conn.cursor()
            cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo'
                           AND (data->>'ipotesi'='1 frase' OR data->>'ipotesi'='' OR LENGTH(data->>'ipotesi')<10) LIMIT 15""")
            righe = cur.fetchall()
            if not righe: cur.close(); conn.close(); break
            for pid, nome, data in righe:
                dd = data if isinstance(data,dict) else (json.loads(data) if data else {})
                pc = dd.get("punto_critico_originale","")
                try:
                    sysi = (f"Preparazione: {nome}. Punto critico: {pc}. JSON: "
                            f'{{"ipotesi":"cosa vuoi ottenere, frase concreta come la direbbe un cuoco","sensori":{{"vista":"...","tatto":"...","olfatto":"..."}}}}. SOLO JSON.')
                    pli = {"model":"gpt-4o-mini","max_tokens":300,"temperature":0.3,"messages":[{"role":"system","content":sysi},{"role":"user","content":"Genera."}]}
                    rqi = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pli).encode(), headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                    _RIEMPITORE_STATO["chiamate_ai"]=_RIEMPITORE_STATO.get("chiamate_ai",0)+1
                    txi = json.loads(ur.urlopen(rqi,timeout=40).read().decode())["choices"][0]["message"]["content"]
                    import re as _re
                    mi = _re.search(r'\{.*\}', txi, _re.DOTALL)
                    if mi:
                        est = json.loads(mi.group(0))
                        ip = est.get("ipotesi","").strip()
                        if ip and ip!="1 frase" and len(ip)>10:
                            dd["ipotesi"]=ip
                            if est.get("sensori") and not dd.get("sensori"): dd["sensori"]=est["sensori"]
                            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid))
                            conn.commit(); _RIEMPITORE_STATO["fatti"]["ipotesi_fix"]=_RIEMPITORE_STATO["fatti"].get("ipotesi_fix",0)+1
                            _log(f"ipotesi: {nome}")
                except: pass
            cur.close(); conn.close()
        # FASE 1: CAUSALITA sui fenomeni che non ce l'hanno
        _RIEMPITORE_STATO["fase"] = "causalita"
        for giro in range(max_ondate):
            conn = psycopg2.connect(DB); cur = conn.cursor()
            cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                           AND NOT (data ? 'causalita') ORDER BY (data->>'coverage_score')::int DESC NULLS LAST LIMIT 4""")
            righe = cur.fetchall()
            if not righe: cur.close(); conn.close(); break
            for nid, nome, data in righe:
                dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
                try:
                    sys = (f"Esperto scienza alimenti. Fenomeno: {nome}. Genera CAUSALITA JSON: "
                           f'{{"acceleranti":[{{"fattore":"...","direzione":"su/giu","peso":"alto/medio/basso"}}],'
                           f'"rallentanti":[...],"conseguenze":[{{"effetto":"...","descrizione":"..."}}]}}. SOLO JSON.')
                    pl = {"model":"gpt-4o","max_tokens":600,"temperature":0.3,"messages":[{"role":"system","content":sys},{"role":"user","content":"Genera."}]}
                    rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                    tx = json.loads(ur.urlopen(rq, timeout=50).read().decode())["choices"][0]["message"]["content"]
                    import re as _re
                    m = _re.search(r'\{.*\}', tx, _re.DOTALL)
                    if m:
                        cs = json.loads(m.group(0))
                        if cs.get("acceleranti") or cs.get("rallentanti"):
                            ok, motivo = _valida_ai("causalita", nome, cs)
                            if ok:
                                dd["causalita"] = cs; dd["causalita_verificata"] = True
                                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), nid))
                                conn.commit(); _RIEMPITORE_STATO["fatti"]["causalita"] += 1
                                _log(f"causalita OK: {nome}")
                            else:
                                _RIEMPITORE_STATO.setdefault("scartati",{}); _RIEMPITORE_STATO["scartati"]["causalita"]=_RIEMPITORE_STATO["scartati"].get("causalita",0)+1
                                _log(f"causalita SCARTATA ({motivo}): {nome}")
                except: pass
            cur.close(); conn.close()
            if not _RIEMPITORE_STATO["attivo"]: return
        # FASE 2: TRADIZIONE sugli ingredienti senza abbinamenti
        _RIEMPITORE_STATO["fase"] = "tradizione"
        for giro in range(max_ondate):
            if not _RIEMPITORE_STATO["attivo"]: return
            conn = psycopg2.connect(DB); cur = conn.cursor()
            cur.execute("""SELECT id, name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND (data ? 'proprieta') AND COALESCE((data->>'nascosto_utente'),'false')<>'true'
                           AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=nodes.id AND e.relation='abbinamento_tradizionale')
                           AND name NOT LIKE '%%(%%' AND POSITION('_' IN name)=0 AND LENGTH(name)>3
                           ORDER BY (data ? 'operativo') DESC, LENGTH(name) ASC LIMIT 5""")
            righe = cur.fetchall()
            if not righe: cur.close(); conn.close(); break
            for nid, nome in righe:
                try:
                    sys = (f"Gastronomia. Ingrediente: {nome}. 4-6 abbinamenti TRADIZIONALI con il PIATTO reale. "
                           f'JSON: {{"abbinamenti":[{{"ingrediente":"...","piatto":"...","tradizione":"..."}}]}}. Niente piatto=escludi. SOLO JSON.')
                    pl = {"model":"gpt-4o","max_tokens":500,"temperature":0.2,"messages":[{"role":"system","content":sys},{"role":"user","content":"Gli abbinamenti."}]}
                    rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                    tx = json.loads(ur.urlopen(rq, timeout=50).read().decode())["choices"][0]["message"]["content"]
                    import re as _re
                    m = _re.search(r'\{.*\}', tx, _re.DOTALL)
                    if m:
                        for a in json.loads(m.group(0)).get("abbinamenti", []):
                            inm = (a.get("ingrediente") or "").strip(); pt = (a.get("piatto") or "").strip()
                            if not inm or not pt: continue
                            _il = inm.lower(); _nl = nome.lower()
                            if _il == _nl or _il in _nl or _nl in _il: continue
                            cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) AND COALESCE((data->>'nascosto_utente'),'false')<>'true' LIMIT 1",(inm,))
                            rr2 = cur.fetchone()
                            if not rr2: continue
                            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_tradizionale'",(nid,rr2[0]))
                            if cur.fetchone(): continue
                            okt, mt = _valida_ai("tradizione", nome, {"ingrediente":inm,"piatto":pt})
                            if not okt:
                                _RIEMPITORE_STATO.setdefault("scartati",{}); _RIEMPITORE_STATO["scartati"]["tradizione"]=_RIEMPITORE_STATO["scartati"].get("tradizione",0)+1
                                continue
                            cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'abbinamento_tradizionale',%s)",
                                        (nid,rr2[0],json.dumps({"piatto":pt,"tradizione":a.get("tradizione",""),"confidenza":"alta","verificato":False,"fonte":"ai_validato"},ensure_ascii=False)))
                            _RIEMPITORE_STATO["fatti"]["tradizione"] += 1
                        conn.commit(); _log(f"tradizione: {nome}")
                except: pass
            cur.close(); conn.close()
        # FASE 3: PROTOCOLLI dalle ricette (trasforma ricette in esperimenti)
        _RIEMPITORE_STATO["fase"] = "protocolli"
        for giro in range(max_ondate):
            if not _RIEMPITORE_STATO["attivo"]: return
            conn = psycopg2.connect(DB); cur = conn.cursor()
            # ricette senza protocollo (il protocollo ha id prot-<slug>, deriva_da_ricetta=ric-id)
            cur.execute("""SELECT id,nome,disciplina,ingredienti,fenomeni,tecniche,numeri,punto_critico
                           FROM ricette WHERE id NOT IN (
                             SELECT data->>'deriva_da_ricetta' FROM nodes WHERE type='Protocollo' AND data ? 'deriva_da_ricetta'
                           ) LIMIT 4""")
            righe = cur.fetchall()
            if not righe: cur.close(); conn.close(); break
            for r_id, r_nome, disc, ingr, fen, tec, num, pc in righe:
                try:
                    def _pp(x):
                        if isinstance(x,(list,dict)): return x
                        try: return json.loads(x) if x else []
                        except: return []
                    ingr=_pp(ingr); fen=_pp(fen)
                    reagenti=[]
                    for ing in ingr:
                        inome = ing.get("nome","") if isinstance(ing,dict) else str(ing)
                        if not inome: continue
                        cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1",(inome,))
                        nr=cur.fetchone()
                        reagenti.append({"nome":inome,"quantita":ing.get("quantita","") if isinstance(ing,dict) else "","unita":ing.get("unita","") if isinstance(ing,dict) else "","reagente_id":nr[0] if nr else None})
                    fenomeni_nodi=[]
                    for f in fen:
                        fnome = f if isinstance(f,str) else f.get("nome","")
                        cur.execute("SELECT id FROM nodes WHERE type IN ('Fenomeno','Tecnica') AND LOWER(name)=LOWER(%s) LIMIT 1",(fnome,))
                        nf=cur.fetchone()
                        fenomeni_nodi.append({"nome":fnome,"fenomeno_id":nf[0] if nf else None})
                    ipotesi="";bersaglio={};sensori={};diagnosi=[];variabile_critica=""
                    try:
                        sysp=(f"Preparazione: {r_nome}. Punto critico: {pc}. Estrai JSON: "
                              f'{{"ipotesi":"cosa vuoi ottenere con questa preparazione, una frase concreta","variabile_critica":"la variabile che governa il risultato","bersaglio":{{"valore":"...","unita":"..."}},'
                              f'"diagnosi":[{{"sintomo":"...","causa":"...","correzione":"..."}}],"sensori":{{"vista":"...","tatto":"...","olfatto":"..."}}}}. SOLO JSON.')
                        plp={"model":"gpt-4o","max_tokens":500,"temperature":0.2,"messages":[{"role":"system","content":sysp},{"role":"user","content":"Estrai."}]}
                        rqp=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(plp).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                        txp=json.loads(ur.urlopen(rqp,timeout=45).read().decode())["choices"][0]["message"]["content"]
                        import re as _re
                        mp=_re.search(r'\{.*\}',txp,_re.DOTALL)
                        if mp:
                            ep=json.loads(mp.group(0))
                            ipotesi=ep.get("ipotesi","");bersaglio=ep.get("bersaglio",{});sensori=ep.get("sensori",{})
                            diagnosi=ep.get("diagnosi",[]);variabile_critica=ep.get("variabile_critica","")
                    except: pass
                    prot_id="prot-"+r_id.replace("ric-gen-","").replace("ric-cls-","").replace("ric-fig-","").replace("ric-","")
                    okp, mp2 = _valida_ai("protocollo", r_nome, {"ipotesi":ipotesi,"bersaglio":bersaglio,"diagnosi":diagnosi})
                    prot={"kind":"protocollo","tipo":"canonico","nome":r_nome,"disciplina":disc,"ipotesi":ipotesi,
                          "variabile_critica":variabile_critica,"reagenti":reagenti,"fenomeni":fenomeni_nodi,"bersaglio":bersaglio,
                          "sensori":sensori,"diagnosi":diagnosi,"punto_critico_originale":pc,"deriva_da_ricetta":r_id,
                          "verificato": okp}
                    if not okp:
                        _RIEMPITORE_STATO.setdefault("scartati",{}); _RIEMPITORE_STATO["scartati"]["protocolli"]=_RIEMPITORE_STATO["scartati"].get("protocolli",0)+1
                    cur.execute("SELECT id FROM nodes WHERE id=%s",(prot_id,))
                    if cur.fetchone():
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(prot,ensure_ascii=False),prot_id))
                    else:
                        cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Protocollo',%s)",(prot_id,r_nome,json.dumps(prot,ensure_ascii=False)))
                    for rg in reagenti:
                        if rg["reagente_id"]:
                            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='usa_reagente'",(prot_id,rg["reagente_id"]))
                            if not cur.fetchone(): cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'usa_reagente')",(prot_id,rg["reagente_id"]))
                    for fn in fenomeni_nodi:
                        if fn["fenomeno_id"]:
                            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='attraversa_fenomeno'",(prot_id,fn["fenomeno_id"]))
                            if not cur.fetchone(): cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'attraversa_fenomeno')",(prot_id,fn["fenomeno_id"]))
                    conn.commit(); _RIEMPITORE_STATO["fatti"]["protocolli"]+=1; _log(f"protocollo: {r_nome}")
                except: pass
            cur.close(); conn.close()
        # FASE 4: VARIETA (biodiversita) sui base che ne hanno, economico (gpt-4o-mini)
        _RIEMPITORE_STATO["fase"] = "varieta"
        for base in _BASE_CON_VARIETA:
            if not _RIEMPITORE_STATO["attivo"]: return
            conn = psycopg2.connect(DB); cur = conn.cursor()
            # salto se ha gia varieta
            cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1",(base,))
            rb = cur.fetchone()
            if not rb: cur.close(); conn.close(); continue
            cur.execute("SELECT 1 FROM edges WHERE to_id=%s AND relation='varieta_di' LIMIT 1",(rb[0],))
            if cur.fetchone(): cur.close(); conn.close(); continue  # gia fatte
            base_id = rb[0]
            try:
                sysv = (f"Esperto biodiversita alimentare. Ingrediente: {base}. Elenca 8-12 VARIETA reali "
                        f"(internazionali) con proprieta. JSON: {{\"varieta\":[{{\"nome\":\"...\",\"proprieta\":{{\"acqua\":\"alta/media/bassa\",\"zuccheri\":\"...\",\"acidita\":\"...\",\"struttura\":\"...\"}},\"esperimenti_ideali\":[\"...\"],\"origine\":\"...\",\"note\":\"...\"}}]}}. Solo REALI. SOLO JSON.")
                plv = {"model":"gpt-4o-mini","max_tokens":1400,"temperature":0.3,"messages":[{"role":"system","content":sysv},{"role":"user","content":"Le varieta."}]}
                rqv = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(plv).encode(), headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                _RIEMPITORE_STATO["chiamate_ai"] = _RIEMPITORE_STATO.get("chiamate_ai",0)+1
                txv = json.loads(ur.urlopen(rqv,timeout=60).read().decode())["choices"][0]["message"]["content"]
                import re as _re
                mv = _re.search(r'\{.*\}', txv, _re.DOTALL)
                if mv:
                    for v in json.loads(mv.group(0)).get("varieta",[]):
                        vn = (v.get("nome") or "").strip()
                        if not vn: continue
                        vid = "var-" + _re.sub(r'[^a-z0-9]+','-', vn.lower()).strip('-')[:50]
                        vdata = {"kind":"varieta","nome":vn,"varieta_di":base,"proprieta":v.get("proprieta",{}),
                                 "esperimenti_ideali":v.get("esperimenti_ideali",[]),"origine":v.get("origine",""),"note":v.get("note",""),
                                 "verificato":False,"fonte":"ai_generato","stato":"stimato"}
                        cur.execute("SELECT id FROM nodes WHERE id=%s",(vid,))
                        if cur.fetchone(): cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(vdata,ensure_ascii=False),vid))
                        else: cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Varieta',%s)",(vid,vn,json.dumps(vdata,ensure_ascii=False)))
                        cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='varieta_di'",(vid,base_id))
                        if not cur.fetchone(): cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'varieta_di')",(vid,base_id))
                        _RIEMPITORE_STATO["fatti"]["varieta"] = _RIEMPITORE_STATO["fatti"].get("varieta",0)+1
                    conn.commit(); _log(f"varieta: {base}")
            except: pass
            cur.close(); conn.close()
        _RIEMPITORE_STATO["fase"] = "completato"; _RIEMPITORE_STATO["attivo"] = False
    except Exception as e:
        _RIEMPITORE_STATO["fase"] = "errore: " + str(e)[:100]; _RIEMPITORE_STATO["attivo"] = False

@bp.route("/admin/riempitore/avvia")
def admin_riempitore_avvia():
    from flask import request, jsonify
    import os, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore":"non autorizzato"}), 403
    if _RIEMPITORE_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _RIEMPITORE_STATO})
    max_ondate = int(request.args.get("ondate", "50"))
    t = threading.Thread(target=_riempitore_worker, args=(max_ondate,), daemon=True)
    t.start()
    return jsonify({"avviato": True, "nota": "Riempie causalita + tradizione in background. Stato: /admin/riempitore/stato"})

@bp.route("/admin/riempitore/stato")
def admin_riempitore_stato():
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore":"non autorizzato"}), 403
    return jsonify(_RIEMPITORE_STATO)

@bp.route("/admin/riempitore/stop")
def admin_riempitore_stop():
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore":"non autorizzato"}), 403
    _RIEMPITORE_STATO["attivo"] = False
    return jsonify({"fermato": True})


# Mappa normalizzazione: nomi-figli nelle ricette -> ingrediente-base nel grafo
_NORMALIZZA_ING = {
    # pomodoro e derivati
    "pomodorini":"pomodoro","pomodorino":"pomodoro","pelati":"pomodoro","passata":"pomodoro",
    "passata di pomodoro":"pomodoro","concentrato di pomodoro":"pomodoro","pomodori":"pomodoro",
    "pomodori pelati":"pomodoro","san marzano":"pomodoro","datterini":"pomodoro","ciliegini":"pomodoro",
    "pomodori ciliegino":"pomodoro","pomodoro san marzano":"pomodoro","polpa di pomodoro":"pomodoro",
    # cioccolato
    "cioccolato fondente":"cioccolato","cioccolato al latte":"cioccolato","cacao":"cioccolato",
    "cacao amaro":"cioccolato","cioccolato bianco":"cioccolato","gocce di cioccolato":"cioccolato",
    "cioccolato in polvere":"cioccolato",
    # uovo
    "uova":"uovo","tuorli":"uovo","tuorlo":"uovo","albumi":"uovo","albume":"uovo","uovo intero":"uovo",
    # farina
    "farina 00":"farina","farina 0":"farina","farina manitoba":"farina","farina integrale":"farina",
    "farina di grano":"farina","farina di semola":"semola","semola rimacinata":"semola",
    # latte/panna
    "latte intero":"latte","latte fresco":"latte","panna fresca":"panna","panna liquida":"panna",
    # formaggi
    "parmigiano reggiano":"parmigiano","grana":"parmigiano","pecorino romano":"pecorino",
    "mozzarella di bufala":"mozzarella","fior di latte":"mozzarella",
    # carne/pesce
    "guanciale a cubetti":"guanciale","pancetta":"guanciale","manzo macinato":"manzo","carne macinata":"manzo",
    "salmone fresco":"salmone","salmone affumicato":"salmone","tonno fresco":"tonno",
    # aromi
    "basilico fresco":"basilico","prezzemolo fresco":"prezzemolo","aglio fresco":"aglio",
    "olio extravergine d'oliva":"olio extravergine di oliva","olio evo":"olio extravergine di oliva",
    "olio d'oliva":"olio extravergine di oliva","limoni":"limone","succo di limone":"limone",
    "zucchero semolato":"zucchero","zucchero a velo":"zucchero","burro fuso":"burro",
}




@bp.route("/v1/ingrediente/<ingrediente>/varieta")
def get_varieta(ingrediente):
    """Le varieta di un ingrediente (la biodiversita: reagenti diversi con proprieta diverse)."""
    from flask import jsonify
    import os, psycopg2, json
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1",(ingrediente,))
        rb = cur.fetchone()
        if not rb: cur.close(); conn.close(); return jsonify({"errore":"non trovato"}), 404
        cur.execute("""SELECT n.name, n.data FROM edges e JOIN nodes n ON n.id=e.from_id
                       WHERE e.to_id=%s AND e.relation='varieta_di' AND n.type='Varieta'""",(rb[0],))
        varieta = []
        for nome, data in cur.fetchall():
            dd = data if isinstance(data,dict) else json.loads(data)
            varieta.append({"nome":nome,"proprieta":dd.get("proprieta",{}),"esperimenti_ideali":dd.get("esperimenti_ideali",[]),
                            "origine":dd.get("origine",""),"note":dd.get("note","")})
        cur.close(); conn.close()
        return jsonify({"ingrediente": ingrediente, "varieta": varieta, "n_varieta": len(varieta)})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/onesta-dati")
def admin_onesta_dati():
    """A3 — rende onesti i dati vecchi che l'AI aveva marcato verificato:true.
    DEFAULT = DRY RUN: conta + campione, NON scrive niente.
    Con ?esegui=1: backup (tabelle _backup_onesta_*) + UPDATE in transazione + conteggio prima/dopo.
    Tocca SOLO righe senza chiave 'fonte' (le curate a mano, che hanno 'fonte', non vengono sfiorate).
    Idempotente: dopo la correzione le righe hanno 'fonte' e non rientrano piu' nel filtro."""
    from flask import request, jsonify
    import os, psycopg2
    _sec = os.environ.get("ADMIN_SECRET")
    if not _sec or request.args.get("s") != _sec:
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") == "1"
    W_VAR = "type='Varieta' AND data->>'verificato'='true' AND (data->>'fonte') IS NULL"
    W_TRAD = ("relation='abbinamento_tradizionale' AND data->>'verificato'='true' "
              "AND (data->>'fonte') IS NULL AND data->>'confidenza'='alta'")
    conn = None
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE " + W_VAR); n_var = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges WHERE " + W_TRAD); n_trad = cur.fetchone()[0]
        cur.execute("SELECT name FROM nodes WHERE " + W_VAR + " LIMIT 6"); camp_var = [r[0] for r in cur.fetchall()]
        if not esegui:
            cur.close(); conn.close()
            return jsonify({"dry_run": True,
                            "varieta_da_correggere": n_var, "tradizione_da_correggere": n_trad,
                            "campione_varieta": camp_var,
                            "nota": "DRY RUN: nessun dato modificato. Per eseguire aggiungi &esegui=1 all'URL."})
        cur.execute("CREATE TABLE IF NOT EXISTS _backup_onesta_varieta (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())")
        cur.execute("CREATE TABLE IF NOT EXISTS _backup_onesta_tradizione (from_id TEXT, to_id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())")
        cur.execute("INSERT INTO _backup_onesta_varieta (id, data_old) SELECT id, data FROM nodes WHERE " + W_VAR)
        cur.execute("INSERT INTO _backup_onesta_tradizione (from_id, to_id, data_old) SELECT from_id, to_id, data FROM edges WHERE " + W_TRAD)
        cur.execute("UPDATE nodes SET data = data || '{\"verificato\":false,\"fonte\":\"ai_generato\",\"stato\":\"stimato\"}'::jsonb WHERE " + W_VAR)
        agg_var = cur.rowcount
        cur.execute("UPDATE edges SET data = data || '{\"verificato\":false,\"fonte\":\"ai_validato\"}'::jsonb WHERE " + W_TRAD)
        agg_trad = cur.rowcount
        cur.execute("SELECT COUNT(*) FROM nodes WHERE " + W_VAR); res_var = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges WHERE " + W_TRAD); res_trad = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return jsonify({"eseguito": True,
                        "varieta_prima": n_var, "varieta_corrette": agg_var, "varieta_residue": res_var,
                        "tradizione_prima": n_trad, "tradizione_corrette": agg_trad, "tradizione_residue": res_trad,
                        "backup": "_backup_onesta_varieta + _backup_onesta_tradizione (contengono i dati originali, ripristinabili)",
                        "nota": "fatto in transazione; righe con 'fonte' (curate) non toccate"})
    except Exception as e:
        try:
            if conn: conn.rollback(); conn.close()
        except Exception: pass
        return jsonify({"errore": str(e)[:200]}), 500












@bp.route("/admin/tradizione-da-ricette")
def admin_tradizione_da_ricette():
    """GRATIS (no AI): estrae abbinamenti tradizionali dai CO-INGREDIENTI delle ricette esistenti.
    Se caffe e cioccolato appaiono insieme in N ricette, e' un abbinamento documentato. Riempie i buchi
    senza spendere crediti. Risolve i 40 euro: usa cio che e' gia pagato."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # mappa nome-ingrediente -> nodo (per collegare)
        cur.execute("""SELECT id, LOWER(name) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND COALESCE((data->>'nascosto_utente'),'false')<>'true'""")
        ing_map = {}
        for iid, inl in cur.fetchall():
            ing_map[inl] = iid
        def _match(nome):
            n=nome.lower().strip()
            if n in ing_map: return ing_map[n]
            prima=n.split()[0] if n.split() else n
            if len(prima)>3 and prima in ing_map: return ing_map[prima]
            return None
        # leggo tutte le ricette e conto le coppie di co-ingredienti
        cur.execute("SELECT nome, ingredienti FROM ricette")
        from collections import defaultdict
        coppie = defaultdict(lambda: {"n":0,"piatti":[]})
        for nome_ric, ingr in cur.fetchall():
            if isinstance(ingr,str):
                try: ingr=json.loads(ingr)
                except: continue
            if not isinstance(ingr,list): continue
            nomi=[]
            for ig in ingr:
                inm = ig.get("nome","") if isinstance(ig,dict) else str(ig)
                iid=_match(inm)
                if iid: nomi.append((iid,inm))
            # tutte le coppie in questa ricetta
            for i in range(len(nomi)):
                for j in range(i+1,len(nomi)):
                    a,b=nomi[i],nomi[j]
                    if a[0]==b[0]: continue
                    key=tuple(sorted([a[0],b[0]]))
                    coppie[key]["n"]+=1
                    if len(coppie[key]["piatti"])<1: coppie[key]["piatti"].append(nome_ric)
        # creo archi tradizione per le coppie che appaiono in >=2 ricette (documentate)
        creati=0
        for (id1,id2),info in coppie.items():
            if info["n"] < 2: continue  # almeno 2 piatti = documentato
            piatto = info["piatti"][0] if info["piatti"] else ""
            for frm,to in [(id1,id2),(id2,id1)]:
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_tradizionale'",(frm,to))
                if not cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'abbinamento_tradizionale',%s)",
                                (frm,to,json.dumps({"piatto":piatto,"da_ricette":info["n"],"confidenza":"alta"},ensure_ascii=False)))
                    creati+=1
            if creati % 500 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"archi_tradizione_creati":creati,"coppie_documentate":sum(1 for v in coppie.values() if v['n']>=2),
                        "nota":"Estratti dai co-ingredienti delle ricette. Zero spesa AI."})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/fenomeni/marca-madre")
def admin_marca_fenomeni_madre():
    """P2 - ATLANTE: marca i ~15-20 FENOMENI MADRE come trasversali e collega le MANIFESTAZIONI.
    Il fenomeno madre e' uno; le manifestazioni (dry shake, ganache...) puntano ad esso. La disciplina = filtro.
    Risolve 'Trasversale 0%'. Zero AI - solo riorganizzazione del grafo esistente."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    dry = request.args.get("dry") == "1"
    # i fenomeni MADRE (fondamentali, trasversali) + le parole che identificano le loro manifestazioni
    MADRE = {
        "emulsione": ["emulsion","dry shake","ganache","maionese","vinaigrette","beurre blanc","aioli"],
        "fermentazione": ["fermentazion","lievitazion","lievito madre","koji","lacto","malolattica","kombucha","poolish","biga"],
        "maillard": ["maillard","rosolatura","crosta","doratura","tostatura","brunitura"],
        "gelatinizzazione": ["gelatinizz","amido","roux","addensant"],
        "coagulazione": ["coagulazion","denaturazion","cagliata","crema pasticcera","custard"],
        "caramellizzazione": ["caramellizz","caramello","imbrunimento zuccher"],
        "estrazione": ["estrazion","infusion","macerazion","cold brew","espresso","decotto"],
        "cristallizzazione": ["cristallizz","tempera","nucleazione","sciroppo"],
        "denaturazione proteica": ["denaturazion proteic","montatura albumi","meringa"],
        "coagulazione proteica": ["coagulazion","cagliata","crema pasticcera","custard","yogurt","uovo cotto"],
        "osmosi": ["osmosi","disidratazion","salamoia","marinatura","cura"],
        "ossidazione": ["ossidazion","imbrunimento enzimatic","irrancidiment"],
        "coagulazione termica": ["coagulazione termic"],
        "schiuma": ["schiuma","espuma","aria","montatura panna","foam"],
        "abbassamento crioscopico": ["crioscop","congelament","pac","sorbetto"],
        "viscosita": ["viscosit","addensament","gelificazion","gel "],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE data ? 'strati' OR id LIKE 'fen-%' OR id LIKE 'tec-%'")
        schede = cur.fetchall()
        madri_marcate = 0; manifest_collegate = 0; dettaglio = []
        # mappa madre -> id del nodo madre (se esiste)
        madre_id = {}
        for sid, sname, sdata in schede:
            nl = (sname or "").lower()
            for madre in MADRE:
                if nl == madre or nl == madre+"i" or nl.replace(" ","") == madre.replace(" ","") or (madre=="coagulazione proteica" and sid=="fen-coagulazione"):
                    madre_id[madre] = sid
        # marco i madre + collego le manifestazioni
        for sid, sname, sdata in schede:
            dd = sdata if isinstance(sdata,dict) else (json.loads(sdata) if sdata else {})
            nl = (sname or "").lower()
            e_madre = sid in madre_id.values()
            manifesta_di = None
            if not e_madre:
                for madre, parole in MADRE.items():
                    if any(p in nl for p in parole) and madre in madre_id:
                        manifesta_di = madre; break
            if e_madre:
                dd["is_fenomeno_madre"] = True
                dd["categoria"] = "trasversale"  # i madre sono trasversali
                if not dry:
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
                madri_marcate += 1; dettaglio.append({"madre":sname})
            elif manifesta_di:
                dd["manifestazione_di"] = manifesta_di
                mid = madre_id[manifesta_di]
                if not dry:
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='manifestazione_di'",(sid,mid))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'manifestazione_di')",(sid,mid))
                manifest_collegate += 1
            if not dry and (madri_marcate+manifest_collegate) % 50 == 0: conn.commit()
        if not dry: conn.commit()
        cur.close(); conn.close()
        return jsonify({"madri_marcate":madri_marcate,"manifestazioni_collegate":manifest_collegate,
                        "madri_trovate":list(madre_id.keys()),"dry_run":dry})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})






@bp.route("/admin/fenomeni/marca-madre-extra")
def admin_marca_madre_extra():
    """Marca come madre i fenomeni fondamentali gia esistenti ma non marcati (maillard, gelatinizzazione)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    EXTRA = {"fen-maillard":["maillard","rosolatura","crosta","doratura","tostatura","brunitura"],
             "fen-gelatinizzazione":["gelatinizz","amido","roux","besciamella"]}
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        marcati=0; collegati=0
        for slug, parole in EXTRA.items():
            cur.execute("SELECT data FROM nodes WHERE id=%s",(slug,))
            r=cur.fetchone()
            if not r: continue
            dd = r[0] if isinstance(r[0],dict) else json.loads(r[0])
            dd["is_fenomeno_madre"]=True; dd["categoria"]="trasversale"
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),slug))
            marcati+=1
            cur.execute("SELECT id,name FROM nodes WHERE type IN ('Fenomeno','Tecnica') AND id<>%s",(slug,))
            for mid,mname in cur.fetchall():
                if any(pp in (mname or "").lower() for pp in parole):
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='manifestazione_di'",(mid,slug))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'manifestazione_di')",(mid,slug))
                        collegati+=1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"marcati":marcati,"manifestazioni_collegate":collegati})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})










@bp.route("/admin/ricuratela/dry-run")
def admin_ricuratela_dry_run():
    """DRY-RUN AVVERSARIALE (contratto epistemico): Evidence Resolver + Pertinence + Classifier sui casi test.
    NON salva - mostra cosa FAREBBE. L'AI VERIFICA e ATTRIBUISCE, non inventa. Michele e' il gate."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # i 10 casi avversariali REALI
    CASI = [
        "prot-acqua-pazza-alle-vongole",   # numero sospetto (90C) + fenomeni sbagliati -> deve dare segnale o D
        "prot-vino-bianco",                # vino: dominio giusto del fenomeno
        "prot-bagel-integrale",            # 75% idratazione: numero VERO -> deve tenerlo (A)
        "prot-baci-di-dama-al-pistacchio", # 15min tempo cottura: NON e' bersaglio scientifico -> B o rimuovi
        "prot-acqua-pazza-al-pomodoro",    # senza bersaglio -> non deve inventarne uno
        "prot-amaretto-sour-rivisitato",   # 3 fenomeni -> deve scegliere la relazione pertinente
        "prot-anatra-alla-pechinese-rivisitata", # temp forno senza valore -> D o segnale
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        risultati = []
        for pid in CASI:
            cur.execute("SELECT data FROM nodes WHERE id=%s", (pid,))
            row = cur.fetchone()
            if not row: 
                risultati.append({"preparazione":pid, "errore":"non trovata"}); continue
            dd = row[0] if isinstance(row[0],dict) else json.loads(row[0])
            nome = dd.get("nome","")
            bers = dd.get("bersaglio",{}) or {}
            val = str(bers.get("valore","")).strip()
            unita = str(bers.get("unita","")).strip()
            var = str(dd.get("variabile_critica","")).lower()
            fenomeni = dd.get("fenomeni",[])
            fen_nomi = [f.get("nome","") if isinstance(f,dict) else str(f) for f in fenomeni]
            # FASE 1 - EVIDENCE RESOLVER: il fenomeno ha evidenza (bersaglio/segnale con fonte)?
            evidenza_trovata = None
            for f in fenomeni:
                fid = f.get("fenomeno_id") if isinstance(f,dict) else None
                if fid:
                    cur.execute("SELECT data FROM nodes WHERE id=%s", (fid,))
                    fr = cur.fetchone()
                    if fr:
                        fdd = fr[0] if isinstance(fr[0],dict) else json.loads(fr[0])
                        fbers = fdd.get("numero_bersaglio") or fdd.get("bersaglio")
                        if fbers: evidenza_trovata = {"fenomeno":f.get("nome"),"evidenza":str(fbers)[:60]}
            # FASE 2 - PERTINENCE: il numero attuale e' coerente col fenomeno?
            # euristica dry-run: tempo (min) = sospetto; temp acqua/forno generica = sospetta; idrataz/coagulaz = ok
            sospetto = ("min" in unita.lower() or "temperatura dell" in var or "temperatura del forno" in var or
                        "cottura del" in var or "tempo di" in var)
            vero = any(v in var for v in ["idrataz","coagulaz","estrazione","gelatinizz","emulsion","fermentaz","diluizione"])
            # FASE 3 - CLASSIFIER + AZIONE (dry-run)
            if not val:
                classif = "D-assente"; azione = "nessun bersaglio: cercare segnale dal fenomeno, altrimenti D. NON inventare numero."
            elif vero and not sospetto:
                classif = "A"; azione = f"TIENE il bersaglio {val}{unita} (variabile scientifica vera, pertinente)"
            elif sospetto:
                classif = "B/D"; azione = f"RIMUOVE {val}{unita} (non e' bersaglio scientifico: e' {var}). Cerca SEGNALE dal fenomeno. Se non c'e -> D. NON inventare."
            else:
                classif = "DA-VERIFICARE"; azione = f"{val}{unita} incerto: verificare pertinenza col fenomeno {fen_nomi}"
            risultati.append({
                "preparazione": nome,
                "bersaglio_attuale": f"{val}{unita}" if val else "(nessuno)",
                "variabile": var[:40],
                "fenomeni_collegati": fen_nomi,
                "evidenza_dal_fenomeno": evidenza_trovata or "nessuna evidenza pertinente trovata",
                "classificazione": classif,
                "AZIONE_PROPOSTA": azione
            })
        cur.close(); conn.close()
        return jsonify({"dry_run":True, "nota":"NON salvato - mostra cosa farebbe. Michele verifica.", "casi":risultati})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})










@bp.route("/admin/ricura-ricette-scienza")
def admin_ricura_ricette_scienza():
    """Ri-cura i campi scienza delle RICETTE (punto_critico, perche_funziona) che hanno 'scienza sopra'.
    L'AI legge la ricetta VERA (ingredienti+procedimento) e riscrive il punto critico e la spiegazione in modo
    corretto e ancorato alla preparazione reale. NON inventa numeri. Il punto critico diventa osservazionale
    dove serve (es. 'togli le vongole appena si aprono' non '90C').
    Default DRY-RUN. ?applica=1 scrive. ?n=N quante."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",20))
    solo_sospette = request.args.get("solo_sospette","1")=="1"
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    # pattern sospetti nel punto_critico (scienza sopra)
    SOSPETTI = ["temperatura dell'acqua","temperatura dell acqua","°c per","gradi per","a 90","a 85","a 80",
                "temperatura del forno","emulsione, gelatinizzazione","gelatinizzazione"]
    def ricura(nome, ingredienti, procedimento, punto_vecchio, pf_vecchio):
        ing_txt = ", ".join([i.get("nome","")+" "+str(i.get("quantita","")) for i in ingredienti[:12]]) if isinstance(ingredienti,list) else str(ingredienti)[:200]
        proc_txt = " ".join([p.get("testo","") if isinstance(p,dict) else str(p) for p in procedimento[:8]]) if isinstance(procedimento,list) else str(procedimento)[:400]
        dom = (f"Ricetta: '{nome}'. Ingredienti: {ing_txt}. Procedimento: {proc_txt[:400]}. "
               f"Punto critico attuale (forse SBAGLIATO): {str(punto_vecchio)[:150]}. "
               f"COMPITO: scrivi il PUNTO CRITICO VERO di questa preparazione - la cosa che conta davvero per "
               f"farla bene. REGOLE: se c'e' una soglia misurabile REALE (es. temperatura coagulazione, "
               f"idratazione) usala; altrimenti descrivi il SEGNALE OSSERVABILE (es. 'togli le vongole appena "
               f"si aprono', 'la crema vela il cucchiaio'). NON inventare numeri (niente '90C' se non e' una "
               f"soglia scientifica vera). Scrivi anche il PERCHE funziona (la scienza vera, breve). "
               f"Rispondi SOLO JSON: {{\"punto_critico\":\"...\", \"perche\":\"...spiegazione scientifica vera...\", "
               f"\"era_sbagliato\":true/false}}")
        pl={"model":"gpt-4o-mini","max_tokens":350,"temperature":0.2,
            "messages":[{"role":"system","content":"Sei un esperto di cucina e scienza degli alimenti rigoroso. "
                        "Scrivi il controllo VERO di una preparazione: numero solo se e' una soglia scientifica "
                        "reale, altrimenti segnale osservabile. NON inventare precisione. Spiega la scienza vera, "
                        "concisa e corretta."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=35).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return None
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]);cur=conn.cursor()
        # le ricette stanno nella TABELLA 'ricette', non nei nodes
        MARK = "\u200b"  # zero-width space: marca le curate, invisibile all'utente, rimosso dall'endpoint pulizia
        cur.execute("SELECT id,nome,ingredienti,procedimento,punto_critico FROM ricette WHERE punto_critico IS NOT NULL AND TRIM(punto_critico)<>'' AND LEFT(punto_critico,1)<>%s",(MARK,))
        righe=cur.fetchall()
        curati=[]; saltati=0; processati=0
        for rid,nome,ingr,proc,pc in righe:
            if processati>=limite: break
            pcl=str(pc).lower()
            sospetto=any(s in pcl for s in SOSPETTI)
            if solo_sospette and not sospetto:
                saltati+=1; continue
            processati+=1
            r=ricura(nome,ingr,proc,pc,{})
            nuovo_pc=(r.get("punto_critico","").strip() if r else "")
            if nuovo_pc:
                curati.append({"nome":nome,"vecchio":str(pc)[:50],"nuovo":nuovo_pc[:60]})
                if applica:
                    cur.execute("UPDATE ricette SET punto_critico=%s WHERE id=%s",(MARK+nuovo_pc,rid)); conn.commit()
            elif applica:
                cur.execute("UPDATE ricette SET punto_critico=%s WHERE id=%s",(MARK+str(pc),rid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","curati":len(curati),
                        "processati":processati,"saltati_non_sospetti":saltati,"esempi":curati[:12]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})




@bp.route("/admin/dedup-ricette")
def admin_dedup_ricette():
    """Elimina i duplicati ESATTI (stesso nome) nella tabella ricette, tiene il piu completo.
    Default DRY-RUN. ?applica=1 elimina."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]);cur=conn.cursor()
        # trovo nomi duplicati
        cur.execute("""SELECT LOWER(TRIM(nome)) nn, COUNT(*) c, array_agg(id) ids
                       FROM ricette GROUP BY LOWER(TRIM(nome)) HAVING COUNT(*)>1 ORDER BY c DESC""")
        gruppi=cur.fetchall()
        da_eliminare=[]; esempi=[]
        for nn,c,ids in gruppi:
            # per ogni gruppo, tengo quello con procedimento piu lungo (piu completo), elimino gli altri
            cur.execute("""SELECT id, LENGTH(COALESCE(procedimento::text,'')) l FROM ricette
                           WHERE id = ANY(%s) ORDER BY l DESC""",(ids,))
            ordinati=cur.fetchall()
            tieni=ordinati[0][0]
            elimina=[r[0] for r in ordinati[1:]]
            da_eliminare.extend(elimina)
            if len(esempi)<12: esempi.append({"nome":nn,"copie":c,"tengo":1,"elimino":len(elimina)})
        if applica and da_eliminare:
            cur.execute("DELETE FROM ricette WHERE id = ANY(%s)",(da_eliminare,))
            conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN",
                        "gruppi_duplicati":len(gruppi),"ricette_da_eliminare":len(da_eliminare),"esempi":esempi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})




@bp.route("/admin/test-import-uno")
def admin_test_import_uno():
    """Test: importa UN canonico semplice per isolare l'errore 500."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        data={"nome":"Roux","kind":"protocollo","tipo":"canonico","disciplina":"cucina",
              "cosa_voglio_ottenere":"preparare un roux","ingredienti":[{"nome":"burro","quantita":"50g"}],
              "il_punto":{"tipo":"segnale","bersaglio":None,"segnale":"cuoci la farina"},
              "fenomeni":[{"nome":"gelatinizzazione","fenomeno_id":None}],"metodo":"test",
              "verificato":True,"classificazione_qualita":"A"}
        cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Protocollo',%s) ON CONFLICT (id) DO NOTHING",
                    ("ric-base-roux-test","Roux Test",json.dumps(data,ensure_ascii=False)))
        conn.commit()
        cur.close();conn.close()
        return jsonify({"ok":True,"nota":"import singolo riuscito"})
    except Exception as e:
        return jsonify({"errore_vero":str(e)})




@bp.route("/admin/classifica-modo-punto")
def admin_classifica_modo_punto():
    """Aggiunge il_punto.modo: target (raggiungi X) / limite (non superare X) / range (tra X e Y).
    L'AI giudica dal mestiere (la maionese 60C = limite, non target). Default DRY-RUN. ?applica=1. ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",20))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def giudica(nome, disciplina, valore, unita, segnale):
        dom = (f"Preparazione: '{nome}' ({disciplina}). Ha un punto numerico: {valore}{unita}. "
               f"Nota: {segnale[:100]}. DOMANDA: questo numero e':\n"
               f"- TARGET (da RAGGIUNGERE: 'porta il tuorlo a 65C per coagularlo')\n"
               f"- LIMITE_SUP (NON SUPERARE, il pericolo e' SOPRA: 'olio sotto 60C sennò impazzisce')\n"
               f"- LIMITE_INF (NON SCENDERE SOTTO, il pericolo e' SOTTO: 'conserva sopra 4C', 'servi sopra 55C')\n"
               f"- RANGE (resta TRA due valori: 60-65% idratazione)?\n"
               f"Pensa al mestiere: raggiungere X, non-superare X, non-scendere-sotto X sono azioni DIVERSE. "
               f'SOLO JSON: {{"modo":"target"|"limite_sup"|"limite_inf"|"range", "motivo":"...breve..."}}')
        pl={"model":"gpt-4o-mini","max_tokens":120,"temperature":0,
            "messages":[{"role":"system","content":"Esperto di cucina/bar. Distingui: RAGGIUNGERE X / NON SUPERARE X (pericolo sopra) / NON SCENDERE SOTTO X "
                        "(pericolo sotto) / RESTA TRA X e Y. Sono azioni diverse. Nel dubbio: target."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=25).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return None
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]);cur=conn.cursor()
        cur.execute("""SELECT id,name,data FROM nodes WHERE type='Protocollo'
                       AND data->'il_punto'->>'tipo' IN ('bersaglio','misto')
                       AND data->'il_punto'->'bersaglio'->>'valore' IS NOT NULL
                       AND (data->'il_punto'->>'modo' IS NULL OR data->'il_punto'->>'modo'='limite') LIMIT %s""",(limite,))
        righe=cur.fetchall()
        risultati={"target":0,"limite_sup":0,"limite_inf":0,"range":0}; esempi=[]
        for pid,nome,data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            ip=dd.get("il_punto",{}); bers=ip.get("bersaglio",{}) or {}
            g=giudica(nome, dd.get("disciplina",""), bers.get("valore",""), bers.get("unita",""), str(ip.get("segnale","")))
            if not g: continue
            modo=g.get("modo","target")
            risultati[modo]=risultati.get(modo,0)+1
            if modo in ("limite_sup","limite_inf","range") and len(esempi)<12:
                val_str = str(bers.get('valore',''))+str(bers.get('unita',''))
                esempi.append({"nome":nome,"valore":val_str,"modo":modo,"motivo":g.get("motivo","")[:50]})
            if applica:
                ip["modo"]=modo
                dd["il_punto"]=ip
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","conteggio":risultati,"esempi_limite_range":esempi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


# ============ SISTEMA DI CURATELA DEL PATRIMONIO ============
# AI prepara -> Michele giudica -> dato canonico. L'AI NON decide "e' vero".

def _tabella_revisione(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS revisione_patrimonio (
        id TEXT PRIMARY KEY, tipo_oggetto TEXT, nome TEXT, contenuto JSONB,
        sospetto TEXT, priorita INT DEFAULT 5,
        giudizio TEXT, nota_michele TEXT, giudicato_il TIMESTAMP)""")

@bp.route("/admin/revisione/prepara")
def admin_revisione_prepara():
    """L'AI PREPARA la coda di revisione: raccoglie i contenuti generati-non-verificati, li pre-classifica per
    SOSPETTO (segnale vago, punto senza fonte, variante generata) e PRIORITA. NON giudica 'e' vero'.
    ?applica=1 popola la tabella."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    applica = request.args.get("applica")=="1"
    # pattern di segnale VAGO (fuffa che suona tecnica)
    VAGHI = ["osservare la","osservare l'","la consistenza","la tenerezza","l'equilibrio del sapore",
             "il sapore e","e pronto quando","al punto giusto","la giusta consistenza"]
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        _tabella_revisione(cur); conn.commit()
        casi=[]
        # 1. PROTOCOLLI: segnali vaghi + punti senza evidence
        cur.execute("SELECT id,name,data FROM nodes WHERE type='Protocollo'")
        for pid,nome,data in cur.fetchall():
            dd=data if isinstance(data,dict) else json.loads(data)
            ip=dd.get("il_punto",{}) or {}
            seg=str(ip.get("segnale","")).lower()
            ev=ip.get("evidence") or []
            sospetto=None; prio=5
            if ip.get("tipo")=="segnale" and any(v in seg for v in VAGHI):
                sospetto="segnale_vago"; prio=1
            elif ip.get("tipo")=="bersaglio" and not ev:
                sospetto="numero_senza_fonte"; prio=2
            elif ip.get("tipo")=="da_verificare":
                sospetto="da_verificare"; prio=1
            if sospetto:
                casi.append({"id":pid,"tipo_oggetto":"protocollo","nome":nome,
                    "contenuto":{"il_punto":ip,"disciplina":dd.get("disciplina",""),"fenomeni":[f.get("nome") for f in dd.get("fenomeni",[])]},
                    "sospetto":sospetto,"priorita":prio})
        # 2. RICETTE generate (fig/gen): variante generata senza fonte
        cur.execute("SELECT id,nome,punto_critico FROM ricette WHERE id LIKE 'ric-fig%%' OR id LIKE 'ric-gen%%'")
        for rid,nome,pc in cur.fetchall():
            pcl=str(pc or "").lower().lstrip(chr(0x200b))
            prio=3; sospetto="variante_generata"
            if any(v in pcl for v in VAGHI): sospetto="ricetta_punto_vago"; prio=2
            casi.append({"id":rid,"tipo_oggetto":"ricetta","nome":nome,
                "contenuto":{"punto_critico":str(pc or "").lstrip(chr(0x200b))[:200]},
                "sospetto":sospetto,"priorita":prio})
        if applica:
            for c in casi:
                cur.execute("""INSERT INTO revisione_patrimonio (id,tipo_oggetto,nome,contenuto,sospetto,priorita)
                    VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET
                    sospetto=EXCLUDED.sospetto, priorita=EXCLUDED.priorita, contenuto=EXCLUDED.contenuto""",
                    (c["id"],c["tipo_oggetto"],c["nome"],json.dumps(c["contenuto"],ensure_ascii=False),c["sospetto"],c["priorita"]))
            conn.commit()
        # conteggio per sospetto
        from collections import Counter
        per_sospetto=Counter(c["sospetto"] for c in casi)
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "ANTEPRIMA","totale_casi":len(casi),
                        "per_sospetto":dict(per_sospetto)})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/revisione")
def admin_revisione_pagina():
    """La pagina di revisione per Michele: un caso alla volta, 4 bottoni. Mobile."""
    from flask import request, Response
    import os
    s = request.args.get("s","")
    if s != os.environ.get("ADMIN_SECRET",""):
        return Response("non autorizzato", status=403)
    html = """<!DOCTYPE html><html lang=it><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Revisione Patrimonio Matter</title><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#0B0F14;color:#E8EDF2;padding:16px;max-width:600px;margin:0 auto}
.prog{font-size:13px;color:#7A8694;margin-bottom:16px;font-variant-numeric:tabular-nums}
.prog b{color:#36E0A8}
.caso{background:#141A22;border:1px solid #232D3A;border-radius:4px;padding:20px;margin-bottom:20px;min-height:200px}
.sosp{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding:3px 8px;border-radius:3px;margin-bottom:12px;font-weight:600}
.sosp.segnale_vago,.sosp.ricetta_punto_vago{background:#3A1F1F;color:#FF8A8A}
.sosp.numero_senza_fonte{background:#3A341F;color:#FFD88A}
.sosp.variante_generata{background:#1F2A3A;color:#8AB8FF}
.sosp.da_verificare{background:#2A1F3A;color:#C88AFF}
.nome{font-size:22px;font-weight:700;margin-bottom:14px;line-height:1.2}
.campo{font-size:14px;color:#AEB9C5;margin:6px 0;line-height:1.5}
.campo b{color:#E8EDF2;font-weight:600}
.punto{font-size:16px;color:#36E0A8;margin:10px 0;padding:10px;background:#0E1419;border-radius:4px}
.btns{display:grid;grid-template-columns:1fr 1fr;gap:10px}
button{padding:18px;font-size:16px;font-weight:700;border:none;border-radius:4px;cursor:pointer;color:#fff}
.vero{background:#1B7A4B}.falso{background:#A83232}.corr{background:#B8820A}.nonso{background:#3A4654}
.nota{width:100%;padding:12px;margin-top:12px;background:#0E1419;border:1px solid #232D3A;border-radius:4px;color:#E8EDF2;font-size:14px;display:none}
.fine{text-align:center;padding:40px;font-size:20px;color:#36E0A8}
</style></head><body>
<div class=prog id=prog>Carico...</div>
<div id=app></div>
<script>
const S=new URLSearchParams(location.search).get('s');
let caso=null;
async function carica(){
  const r=await fetch('/admin/revisione/prossimo?s='+encodeURIComponent(S));
  const d=await r.json();
  if(d.finito){document.getElementById('app').innerHTML='<div class=fine>Finito! '+d.fatti+' casi giudicati. Grazie.</div>';document.getElementById('prog').innerHTML='';return;}
  caso=d;
  document.getElementById('prog').innerHTML='<b>'+d.fatti+'</b> fatti · '+d.rimasti+' rimasti';
  let c=d.contenuto||{};
  let dett='';
  if(c.il_punto){let ip=c.il_punto;let v=ip.bersaglio?(ip.bersaglio.valore+''+(ip.bersaglio.unita||'')):'';
    dett+='<div class=punto>IL PUNTO: '+(v||ip.segnale||'(vuoto)')+(ip.modo?' ['+ip.modo+']':'')+'</div>';}
  if(c.punto_critico)dett+='<div class=punto>PUNTO: '+c.punto_critico+'</div>';
  if(c.disciplina)dett+='<div class=campo><b>disciplina:</b> '+c.disciplina+'</div>';
  if(c.fenomeni&&c.fenomeni.length)dett+='<div class=campo><b>fenomeni:</b> '+c.fenomeni.join(', ')+'</div>';
  document.getElementById('app').innerHTML=
    '<div class=caso><span class="sosp '+d.sospetto+'">'+d.sospetto.replace(/_/g,' ')+'</span>'+
    '<div class=nome>'+d.nome+'</div><div class=campo><b>origine:</b> '+d.id+'</div>'+dett+'</div>'+
    '<textarea class=nota id=nota placeholder="nota (opzionale, per correggi)"></textarea>'+
    '<div class=btns>'+
    '<button class=vero onclick="giudica(\\'vero\\')">VERO</button>'+
    '<button class=falso onclick="mostraNota();giudica(\\'falso\\')">FALSO</button>'+
    '<button class=corr onclick="mostraNota()">DA CORREGGERE</button>'+
    '<button class=nonso onclick="giudica(\\'non_so\\')">NON SO</button></div>';
}
function mostraNota(){document.getElementById('nota').style.display='block';}
async function giudica(g){
  let nota=document.getElementById('nota')?document.getElementById('nota').value:'';
  if(g==='correggi'&&!nota){alert('scrivi la correzione nella nota');return;}
  await fetch('/admin/revisione/giudica?s='+encodeURIComponent(S),{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({id:caso.id,giudizio:g,nota:nota})});
  carica();
}
document.querySelector('.corr')&&0;
carica();
</script></body></html>"""
    return Response(html, mimetype="text/html")


@bp.route("/admin/revisione/prossimo")
def admin_revisione_prossimo():
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("SELECT id,tipo_oggetto,nome,contenuto,sospetto FROM revisione_patrimonio WHERE giudizio IS NULL ORDER BY priorita, id LIMIT 1")
        r=cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM revisione_patrimonio WHERE giudizio IS NULL")
        rimasti=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM revisione_patrimonio WHERE giudizio IS NOT NULL")
        fatti=cur.fetchone()[0]
        cur.close();conn.close()
        if not r: return jsonify({"finito":True,"fatti":fatti})
        cont=r[3] if isinstance(r[3],dict) else json.loads(r[3])
        return jsonify({"id":r[0],"tipo":r[1],"nome":r[2],"contenuto":cont,"sospetto":r[4],"rimasti":rimasti,"fatti":fatti})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/revisione/giudica", methods=["POST"])
def admin_revisione_giudica():
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    body=request.get_json(force=True)
    cid=body.get("id"); giudizio=body.get("giudizio"); nota=body.get("nota","")
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("UPDATE revisione_patrimonio SET giudizio=%s, nota_michele=%s, giudicato_il=NOW() WHERE id=%s",(giudizio,nota,cid))
        if giudizio=="falso":
            cur.execute("SELECT data FROM nodes WHERE id=%s",(cid,))
            r=cur.fetchone()
            if r:
                dd=r[0] if isinstance(r[0],dict) else json.loads(r[0])
                if dd.get("il_punto"):
                    dd["il_punto"]={"tipo":"da_verificare","bersaglio":None,"segnale":"","_rimosso_da_michele":True,"_nota":nota}
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),cid))
        conn.commit(); cur.close();conn.close()
        return jsonify({"ok":True})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})






@bp.route("/admin/conta-ingredienti-stato")
def admin_conta_ingredienti_stato():
    """Conta: totali, consultabili (non solo_motore), col profilo pieno, e un campione dei nascosti."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')")
        tot=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data->>'solo_motore') IS NULL")
        consultabili=cur.fetchone()[0]
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data->>'solo_motore') IS NULL AND jsonb_typeof(data->'proprieta')='object'
                       AND (SELECT COUNT(*) FROM jsonb_object_keys(data->'proprieta'))>=10""")
        col_profilo=cur.fetchone()[0]
        # campione dei NASCOSTI (solo_motore) - erano tecnici veri o roba utile?
        cur.execute("SELECT name FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data->>'solo_motore')='true' ORDER BY RANDOM() LIMIT 20")
        nascosti=[r[0] for r in cur.fetchall()]
        # campione dei CONSULTABILI (cosa resta visibile)
        cur.execute("SELECT name FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND (data->>'solo_motore') IS NULL ORDER BY RANDOM() LIMIT 20")
        visibili=[r[0] for r in cur.fetchall()]
        cur.close();conn.close()
        return jsonify({"totali":tot,"consultabili":consultabili,"nascosti_solo_motore":tot-consultabili,
                        "col_profilo_pieno":col_profilo,
                        "campione_NASCOSTI":nascosti,"campione_VISIBILI":visibili})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/traduci-ingredienti-inglesi")
def admin_traduci_ingredienti_inglesi():
    """Traduce i nomi degli ingredienti inglesi (sesame_oil->olio di sesamo) e li rende consultabili
    (toglie solo_motore). Se il nome e' una pianta latina senza nome comune italiano -> resta solo_motore.
    L'AI TRADUCE (non inventa contenuto). Default DRY-RUN. ?applica=1. ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",30))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def traduci(nome_eng):
        nome_pulito = nome_eng.replace("_"," ")
        dom = (f"Nome ingrediente (database internazionale): '{nome_pulito}'. "
               f"Qual e' il nome ITALIANO COMUNE con cui un cuoco/barman lo chiamerebbe? "
               f"Es: 'sesame oil'->'olio di sesamo', 'jamaican rum'->'rum giamaicano', 'red currant'->'ribes rosso'. "
               f"Se e' una pianta/sostanza SCIENTIFICA senza nome comune italiano (es. 'myrcia acris', "
               f"'melilotus officinalis'), rispondi nome_italiano VUOTO e scientifico true. "
               f'SOLO JSON: {{"nome_italiano":"...o vuoto...", "scientifico": true/false}}')
        pl={"model":"gpt-4o-mini","max_tokens":60,"temperature":0,
            "messages":[{"role":"system","content":"Traduttore culinario. Dai il nome italiano COMUNE di un "
                        "ingrediente. Se e' solo un nome scientifico latino senza equivalente comune, lascia vuoto."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=20).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return None
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("""SELECT id,name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data->>'solo_motore')='true' AND (data->>'_tradotto') IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        tradotti=[]; restano_scientifici=0
        for iid,nome in righe:
            r=traduci(nome)
            if not r: continue
            nit=r.get("nome_italiano","").strip()
            if nit and not r.get("scientifico"):
                tradotti.append({"da":nome,"a":nit})
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s",(iid,))
                    dd=cur.fetchone()[0]; dd=dd if isinstance(dd,dict) else json.loads(dd)
                    dd["nome_italiano"]=nit; dd.pop("solo_motore",None); dd["_tradotto"]=True
                    cur.execute("UPDATE nodes SET name=%s, data=%s WHERE id=%s",(nit,json.dumps(dd,ensure_ascii=False),iid)); conn.commit()
            else:
                restano_scientifici+=1
                if applica:
                    cur.execute("SELECT data FROM nodes WHERE id=%s",(iid,))
                    dd=cur.fetchone()[0]; dd=dd if isinstance(dd,dict) else json.loads(dd)
                    dd["_tradotto"]=True  # visto, resta solo_motore
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),iid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","tradotti_consultabili":len(tradotti),
                        "restano_scientifici":restano_scientifici,"esempi":tradotti[:15]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


















@bp.route("/admin/vedi-tipo-base/<nome>")
def admin_vedi_tipo_base(nome):
    """Debug varieta: mostra il tipo_base di un nodo e chi altro ce l'ha uguale (per capire i raggruppamenti sbagliati)."""
    from flask import jsonify, request
    import os, json as _j
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    try:
        from db import carica_grafo
        db = carica_grafo()
        def _c(r,k,i): return r[k] if hasattr(r,"keys") else r[i]
        rows=db.execute("SELECT id,name,data FROM nodes WHERE LOWER(name)=LOWER(?) AND type IN ('Ingrediente','Prodotto') LIMIT 2",(nome,)).fetchall()
        out=[]
        for r in rows:
            dd=_c(r,"data",2); dd=dd if isinstance(dd,dict) else _j.loads(dd)
            tb=dd.get("tipo_base")
            # chi altro ha questo tipo_base?
            altri=[]
            if tb:
                ar=db.execute("SELECT name FROM nodes WHERE data->>'tipo_base'=? LIMIT 30",(tb,)).fetchall()
                altri=[_c(x,"name",0) for x in ar]
            out.append({"id":_c(r,"id",0),"tipo_base":tb,"altri_con_stesso_tipo_base":altri})
        return jsonify({"nome":nome,"nodi":out})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


# ── MIGRAZIONI SPOSTATE ───────────────────────────────────────────────
# 120 endpoint one-shot (popola-*/genera-*/migra-*/ripara-*...) sono stati spostati in
# routes/admin_migrazioni.py: erano 6.280 righe di script gia eseguiti, caricate a ogni
# avvio senza mai servire. Si riattivano con ABILITA_MIGRAZIONI=1. Nulla e' stato perso.
