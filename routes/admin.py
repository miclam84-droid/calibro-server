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
    from db import carica_grafo
    db = carica_grafo()
    termine = request.args.get("t", "grassi")
    t = f"%{termine.lower()}%"
    rows = db.execute("SELECT id, name, type FROM nodes WHERE lower(name) LIKE ? LIMIT 10", (t,)).fetchall()
    out = [{"id": r["id"], "name": r["name"], "type": r["type"]} for r in rows]
    # conto anche quanti nodi totali e quanti fen-*-impasto
    tot = db.execute("SELECT COUNT(*) as c FROM nodes").fetchone()["c"]
    imp = db.execute("SELECT id, name, type FROM nodes WHERE id LIKE 'fen-%impasto%' OR id='fen-idratazione' OR id='fen-farina-forza'").fetchall()
    return jsonify({"termine": termine, "match": out, "totale_nodi": tot,
                    "nodi_nuovi": [{"id":r["id"],"name":r["name"],"type":r["type"]} for r in imp]})

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
