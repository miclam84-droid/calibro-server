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

        cur.close(); _release_conn(conn)
        return jsonify(stats)
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
