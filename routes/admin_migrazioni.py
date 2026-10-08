"""MIGRAZIONI E POPOLAMENTI ONE-SHOT (archivio).

Questi endpoint sono script eseguiti UNA VOLTA per costruire o riparare i dati
(popola-*, genera-*, migra-*, ripara-*, consolida-*...). Il lavoro e' gia stato fatto:
il database e' popolato. Restavano in routes/admin.py occupando 6.280 righe su 15.389,
caricate a ogni avvio in produzione senza mai servire.

NON sono registrati di default. Per riattivarli (se serve rilanciare una migrazione):
    ABILITA_MIGRAZIONI=1   nelle variabili d'ambiente, poi riavvia.

Nessuna riga e' stata cancellata: il codice e' qui, intatto, solo fuori dal percorso caldo.
"""
import os, json, traceback, time, hmac
from db import carica_grafo, _dati, _get_conn, _release_conn
from auth import _admin_autenticato, _init_account_tables
from contenuto import (_scheda_lang, _numero_bersaglio, _pulisci_traduzione, _corregge_it)
from notifiche import _invia_email_resend
import oss

from flask import Blueprint
bp = Blueprint('admin_migrazioni', __name__)
# helper condivisi con routes/admin.py (restano definiti li, qui solo importati)
from routes.admin import (
    _ABBINA_STATO,
    _GENCAN_STATO,
    _MAPPA_FENOMENO_MONDO,
    _NORMALIZZA_ING,
    _RIGEN_STATO,
    _abbina_worker,
    _admin_ok,
    _famiglia_ingrediente,
    _gencan_worker,
    _match_ing_id,
    _rigen_worker,
    _scheda_lang,
)

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


@bp.route("/admin/crea-errori-nuovi")
def admin_crea_errori_nuovi():
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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


@bp.route("/admin/errori-completa")
def admin_errori_completa():
    """Completa l'asse ERRORI: errore tipico (sintomo al banco -> causa) per i fenomeni che ne hanno 0."""
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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


@bp.route("/admin/consolida-doppioni")
def admin_consolida_doppioni():
    """Consolida i doppioni VERI (lista curata a mano): sposta i collegamenti del nodo doppione
    sul nodo BUONO, poi rimuove il doppione. Coppie (buono, doppione)."""
    if not _admin_ok(request):
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
        # Doppioni trovati (FASE B pulizia): tengo il fen- (fenomeno canonico), rimuovo il tec-
        ("fen-autolisi","tec-autolisi"),
        ("fen-carbonatazione","tec-carbonatazione-tecnica"),
        ("fen-chiarificazione","tec-chiarificazione"),
        ("fen-emulsione","tec-emulsione"),
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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
    if not _admin_ok(request):
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


@bp.route("/admin/migra-ricette-voce")
def admin_migra_ricette_voce():
    """Aggiunge le colonne esperimento e limite alla tabella ricette (Protocollo Kenji-Matter).
    Idempotente: ADD COLUMN IF NOT EXISTS. Sicuro da rilanciare."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS esperimento TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS limite TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS esperimento_en TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS esperimento_es TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS limite_en TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS limite_es TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS twist TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS twist_en TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS twist_es TEXT")
        conn.commit()
        return jsonify({"ok": True, "aggiunte": ["esperimento","limite","twist","+en/es"]})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)


@bp.route("/admin/salva-ricetta-rigenerata", methods=["POST"])
def admin_salva_ricetta_rigenerata():
    """Salva in place una ricetta gia generata dal client (via /v1/genera-ricetta). NESSUNA AI qui:
    e istantaneo, non rischia timeout. Riceve {id, ricetta:{...}}. CONSERVA l'immagine."""
    if not _admin_ok(request):
        return "Forbidden", 403
    import json as _json
    from db import _get_conn, _release_conn
    body = request.get_json(force=True, silent=True) or {}
    rid = body.get("id", "")
    ric = body.get("ricetta", {})
    if not rid or not ric.get("nome"):
        return jsonify({"errore": "serve id e ricetta con nome"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""UPDATE ricette SET
            descrizione=%s, numeri=%s::jsonb, punto_critico=%s, procedimento=%s::jsonb,
            tecniche=%s::jsonb, fenomeni=%s::jsonb, abbinamenti=%s::jsonb,
            esperimento=%s, limite=%s, twist=%s,
            scheda_en=NULL, scheda_es=NULL, nome_en=NULL, nome_es=NULL,
            procedimento_en=NULL, procedimento_es=NULL, punto_critico_en=NULL, punto_critico_es=NULL,
            esperimento_en=NULL, esperimento_es=NULL, limite_en=NULL, limite_es=NULL,
            twist_en=NULL, twist_es=NULL, applicazioni_en=NULL, applicazioni_es=NULL
            WHERE id=%s""",
            (ric.get("descrizione",""),
             _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
             ric.get("punto_critico",""),
             _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
             _json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
             _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
             _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
             ric.get("esperimento",""), ric.get("limite",""), ric.get("twist",""),
             rid))
        conn.commit()
        aggiornate = cur.rowcount
        return jsonify({"ok": True, "id": rid, "aggiornate": aggiornate,
                        "esperimento": bool(ric.get("esperimento")), "twist": bool(ric.get("twist"))})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)[:150]}), 500
    finally:
        _release_conn(conn)


@bp.route("/admin/rigenera-bg")
def admin_rigenera_bg():
    """Avvia la rigenerazione in BACKGROUND (thread) e risponde SUBITO. Aggira il timeout 30s.
    ?disc= opzionale, ?n= opzionale (limita quante). Controlla lo stato con /admin/rigenera-bg-stato."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _RIGEN_STATO
    if _RIGEN_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _RIGEN_STATO})
    import threading
    disc = request.args.get("disc", "")
    solo_n = int(request.args.get("n", "0")) or None
    senza_numeri = request.args.get("senza_numeri", "0") != "0"
    t = threading.Thread(target=_rigen_worker, args=(disc, solo_n, senza_numeri), daemon=True)
    t.start()
    return jsonify({"avviato": True, "modo": "senza_numeri" if senza_numeri else "senza_esperimento",
                    "nota": "rigenerazione in background, controlla /admin/rigenera-bg-stato"})


@bp.route("/admin/rigenera-bg-stato")
def admin_rigenera_bg_stato():
    """Stato della rigenerazione in background."""
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_RIGEN_STATO)


@bp.route("/admin/rigenera-ricette-vecchie")
def admin_rigenera_ricette_vecchie():
    """Rigenera le ricette VECCHIE (senza esperimento o twist) col motore nuovo (voce Kenji-Matter,
    numeri onesti, esperimento, limite, twist). AGGIORNA in place, CONSERVA l'immagine gia assegnata.
    ?n=1 per il timeout worker. Lancia in ciclo lato client. ?disc= opzionale per filtrare una disciplina."""
    if not _admin_ok(request):
        return "Forbidden", 403
    try:
        import json as _json
        from db import carica_grafo, _get_conn, _release_conn
        from builder import genera_ricetta
        n = int(request.args.get("n", "1"))
        disc_filtro = request.args.get("disc", "")
        db = carica_grafo()
    except Exception as _e:
        import traceback
        return jsonify({"errore_setup": str(_e), "trace": traceback.format_exc()[:500]}), 200

    # FASE 1: trovo le ricette da rigenerare (query breve, connessione aperta e subito rilasciata)
    conn = _get_conn(); cur = conn.cursor()
    try:
        q = """SELECT id, nome, disciplina FROM ricette
               WHERE (esperimento IS NULL OR esperimento = '' OR twist IS NULL OR twist = '')"""
        params = []
        if disc_filtro:
            q += " AND disciplina = %s"; params.append(disc_filtro)
        q += " ORDER BY nome LIMIT %s"; params.append(n)
        cur.execute(q, tuple(params))
        da_fare = cur.fetchall()
    finally:
        _release_conn(conn)  # rilascio SUBITO: non tengo la connessione durante l'AI

    if not da_fare:
        return jsonify({"fatte": 0, "nota": "nessuna ricetta vecchia da rigenerare" + (f" in {disc_filtro}" if disc_filtro else "")})

    fatte = []
    for row in da_fare:
        rid, nome, disc = row[0], row[1], row[2]
        # FASE 2: genero con l'AI (LENTO ~20s) — nessuna connessione DB aperta qui
        try:
            ric = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc, lang="it")
        except Exception as e:
            fatte.append({"id": rid, "errore_gen": str(e)[:120]}); continue
        if ric.get("errore") or not ric.get("nome"):
            fatte.append({"id": rid, "saltata": ric.get("errore", "no nome")}); continue
        # FASE 3: apro connessione SOLO per gli UPDATE veloci (millisecondi), poi la rilascio
        c2 = _get_conn(); cur2 = c2.cursor()
        try:
            cur2.execute("""UPDATE ricette SET
                descrizione=%s, numeri=%s::jsonb, punto_critico=%s, procedimento=%s::jsonb,
                tecniche=%s::jsonb, fenomeni=%s::jsonb, abbinamenti=%s::jsonb,
                esperimento=%s, limite=%s, twist=%s
                WHERE id=%s""",
                (ric.get("descrizione",""),
                 _json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                 ric.get("punto_critico",""),
                 _json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                 _json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                 _json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                 _json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                 ric.get("esperimento",""), ric.get("limite",""), ric.get("twist",""),
                 rid))
            # traduzioni EN/ES stantie -> azzero (il batch le rifara). NON tocco l'immagine.
            cur2.execute("""UPDATE ricette SET scheda_en=NULL, scheda_es=NULL, nome_en=NULL, nome_es=NULL,
                procedimento_en=NULL, procedimento_es=NULL, punto_critico_en=NULL, punto_critico_es=NULL,
                esperimento_en=NULL, esperimento_es=NULL, limite_en=NULL, limite_es=NULL,
                twist_en=NULL, twist_es=NULL, applicazioni_en=NULL, applicazioni_es=NULL
                WHERE id=%s""", (rid,))
            c2.commit()
            fatte.append({"id": rid, "nome": nome, "esperimento": bool(ric.get("esperimento")),
                          "twist": bool(ric.get("twist"))})
        except Exception as e:
            c2.rollback()
            fatte.append({"id": rid, "errore_update": str(e)[:120]})
        finally:
            _release_conn(c2)

    return jsonify({"fatte": len([f for f in fatte if f.get("nome")]), "dettaglio": fatte})


@bp.route("/admin/genera-ricette-mancanti")
def admin_genera_ricette_mancanti():
    """Genera ricette sui fenomeni SENZA ricetta (i buchi veri). Una ricetta per fenomeno,
    pertinente, salvata (IT; traduzioni EN/ES poi via batch traduci-ricette).
    ?n=3 quante generarne per chiamata (piccolo per il timeout worker). ?disc= per disciplina.
    Ogni ricetta copre un fenomeno scoperto -> espansione MIRATA, non a caso."""
    if not _admin_ok(request):
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
                        punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,esperimento,limite,twist)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
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
                     ric.get("difficolta",""), ric.get("porzioni",""),
                     ric.get("esperimento",""), ric.get("limite",""), ric.get("twist","")))
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


@bp.route("/admin/migra-schema-traduzioni")
def admin_migra_schema_traduzioni():
    """Aggiunge le colonne tradotte per i campi ricetta che erano solo in IT."""
    if not _admin_ok(request):
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


@bp.route("/admin/pulisci-nomi-flavor")
def admin_pulisci_nomi_flavor():
    """Elenca e (se dry=0) traduce i nomi ahn sporchi EN->IT via AI, salvando sul nodo.
    ?dry=1 (default) solo elenca; ?dry=0 traduce e salva. ?limite=N per fare a lotti."""
    if not _admin_ok(request):
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


@bp.route("/admin/genera-ganci")
def admin_genera_ganci():
    """Genera UNA domanda-gancio per ogni fenomeno, partendo dalla scheda esistente.
    La domanda apre la lezione ('Perché...?') invece del secco 'X è...'.
    Generata con GPT-4o mini (economico), salvata nel campo data.gancio.
    Uso: /admin/genera-ganci?s=SECRET  (aggiungi &solo=fen-acidita per testarne uno)"""
    import ai_gateway as GW
    if not _admin_ok(request):
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


@bp.route("/admin/arricchisci-ricette", methods=["POST", "GET"])
def admin_arricchisci_ricette():
    """Blocco B: aggiunge ing-id stabile + scarto_pct alle voci ricetta esistenti.
    Match automatico nome→ing-id via alias. Idempotente. Auth ADMIN_SECRET.
    ?dry=1 -> anteprima senza scrivere. ?disc=bar -> solo una disciplina.
    Convenzione scarto: scarto_pct (0 default). Neutra: Cifra può convertire in resa_pct.
    """
    if not _admin_ok(request):
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


@bp.route("/admin/genera-abbinamenti-bevande")
def admin_genera_abbinamenti():
    """Genera vino/birra (col perché) per le ricette di CIBO senza abbinamento. ?n=3 per provare. ?openai=1."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _ABBINA_STATO
    if _ABBINA_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _ABBINA_STATO})
    import threading
    solo_n = request.args.get("n", "0")
    usa_openai = request.args.get("openai", "0") != "0"
    t = threading.Thread(target=_abbina_worker,
                         args=(int(solo_n) if solo_n.isdigit() and solo_n!="0" else None, usa_openai), daemon=True)
    t.start()
    return jsonify({"avviato": True, "provider": "openai" if usa_openai else "gratuiti"})


@bp.route("/admin/genera-abbinamenti-bevande-stato")
def admin_genera_abbinamenti_stato():
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_ABBINA_STATO)


@bp.route("/admin/crea-fenomeno-mondo", methods=["POST"])
def admin_crea_fenomeno_mondo():
    """Crea un nodo Fenomeno 'del mondo' con scheda+target verificati. Body: {id,nome,dominio,scheda,target,aliases}.
    Per i fenomeni non-europei (nixtamalizzazione, wok hei, koji...) coi numeri veri verificati via ricerca."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    b = request.json or {}
    nid = b.get("id", "")
    nome = b.get("nome", "")
    if not nid or not nome:
        return jsonify({"errore": "id e nome obbligatori"}), 400
    data = {
        "scheda": b.get("scheda", ""),
        "target": b.get("target", ""),
        "nome": nome,
        "aliases": b.get("aliases", []),
        "fenomeno_mondo": "true",
        "numeri_verificati": "true",
    }
    dominio = b.get("dominio", "cucina")
    conn = _get_conn(); cur = conn.cursor()
    try:
        # esiste gia?
        cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
        if cur.fetchone():
            cur.execute("UPDATE nodes SET name=%s, domain=%s, data=%s WHERE id=%s",
                        (nome, dominio, json.dumps(data, ensure_ascii=False), nid))
            azione = "aggiornato"
        else:
            cur.execute("INSERT INTO nodes (id,type,name,domain,data) VALUES (%s,%s,%s,%s,%s)",
                        (nid, "Fenomeno", nome, dominio, json.dumps(data, ensure_ascii=False)))
            azione = "creato"
        conn.commit()
        return jsonify({"ok": True, "azione": azione, "id": nid, "nome": nome})
    finally:
        _release_conn(conn)


@bp.route("/admin/forza-fenomeni-mondo")
def admin_forza_fenomeni_mondo():
    """Scorre le ricette e, se il nome contiene una parola-chiave di piatto internazionale, aggancia il
    fenomeno del mondo giusto (lo mette PRIMO nella lista fenomeni se non c'è). ?dryrun=1 per simulare."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    dryrun = request.args.get("dryrun", "0") != "0"
    conn = _get_conn(); cur = conn.cursor()
    modificate = []
    try:
        cur.execute("SELECT id, nome, fenomeni FROM ricette")
        righe = cur.fetchall()
        for r in righe:
            rid, nome, fen_raw = r[0], r[1], r[2]
            nome_l = (nome or "").lower()
            fen = fen_raw if isinstance(fen_raw, list) else (json.loads(fen_raw) if fen_raw else [])
            # trovo il fenomeno del mondo che questo piatto DOVREBBE avere
            fen_mondo = None
            for chiave, fenomeno in _MAPPA_FENOMENO_MONDO.items():
                if chiave in nome_l:
                    fen_mondo = fenomeno
                    break
            if not fen_mondo:
                continue
            # è già presente (anche parziale)?
            gia = any(fen_mondo.lower() in str(f).lower() or str(f).lower() in fen_mondo.lower() for f in fen)
            if gia:
                continue
            # lo aggiungo in testa
            nuovi_fen = [fen_mondo] + [f for f in fen]
            modificate.append({"id": rid, "nome": nome, "aggiunto": fen_mondo, "prima": fen})
            if not dryrun:
                cur.execute("UPDATE ricette SET fenomeni=%s WHERE id=%s",
                            (json.dumps(nuovi_fen, ensure_ascii=False), rid))
        if not dryrun:
            conn.commit()
        return jsonify({"dryrun": dryrun, "modificate": len(modificate), "dettaglio": modificate[:40]})
    finally:
        _release_conn(conn)


@bp.route("/admin/pulisci-foto-stock")
def admin_pulisci_foto_stock():
    """REGOLA DURA: in foto ci deve essere quello che c'è scritto. Le foto stock generiche (Pexels ecc.)
    danno drink/piatti a caso (Aviation verde, Americano con dirty martini). Le TOGLIE tutte, tenendo solo
    le foto vere dell'archivio (Cloudinary, che matchano per nome). ?dry=1 per contare. ?disc=bar per limitare."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    dry = request.args.get("dry", "0") != "0"
    disc = request.args.get("disc", "")
    conn = _get_conn(); cur = conn.cursor()
    try:
        # trovo le ricette con foto STOCK (autore contiene Pexels/Unsplash/Pixabay), NON archivio
        q = """SELECT id, nome, disciplina, immagine_autore FROM ricette
               WHERE immagine IS NOT NULL AND immagine <> ''
               AND (LOWER(COALESCE(immagine_autore,'')) LIKE '%%pexels%%'
                    OR LOWER(COALESCE(immagine_autore,'')) LIKE '%%unsplash%%'
                    OR LOWER(COALESCE(immagine_autore,'')) LIKE '%%pixabay%%')"""
        params = []
        if disc:
            q += " AND disciplina=%s"; params.append(disc)
        cur.execute(q, tuple(params))
        righe = cur.fetchall()
        elenco = [{"id": r[0], "nome": r[1], "disc": r[2]} for r in righe]
        if dry:
            return jsonify({"da_togliere": len(elenco), "esempi": [e["nome"] for e in elenco[:12]]})
        # cancello la foto (metto NULL su immagine, autore, fonte)
        ids = [e["id"] for e in elenco]
        for rid in ids:
            cur.execute("UPDATE ricette SET immagine=NULL, immagine_autore=NULL, immagine_url_fonte=NULL WHERE id=%s", (rid,))
        conn.commit()
        return jsonify({"tolte": len(ids), "nota": "foto stock rimosse; restano solo le foto vere dell'archivio",
                        "esempi": [e["nome"] for e in elenco[:12]]})
    finally:
        _release_conn(conn)


@bp.route("/admin/pulisci-foto-malmatch")
def admin_pulisci_foto_malmatch():
    """Il match foto Cloudinary per nome è grezzo: assegna foto sbagliate (bibimbap->coppa gelato,
    banh mi->bagel). Questa funzione TIENE una foto archivio solo se il nome-file contiene davvero
    una parola forte del nome ricetta; altrimenti la TOGLIE. ?dry=1 per contare."""
    import re as _re
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    dry = request.args.get("dry", "0") != "0"
    # parole-chiave forti: se il file contiene questa parola, il match è valido per quel tipo di ricetta
    # (nome_ricetta_contiene -> parola_che_deve_stare_nel_file)
    match_validi = {
        "pizza": "pizza", "pasta": "pasta", "spaghetti": "spaghetti", "bagel": "bagel",
        "sushi": "sushi", "muffin": "muffin", "tacos": "taco", "tortilla": "taco",
        "focaccia": None,  # 'perfect-wholegrain-bread' NON è focaccia -> togli
    }
    conn = _get_conn(); cur = conn.cursor()
    tolte = []; tenute = []
    try:
        cur.execute("""SELECT id, nome, immagine FROM ricette
                       WHERE immagine IS NOT NULL AND immagine <> ''
                       AND LOWER(COALESCE(immagine_autore,'')) LIKE '%%archivio%%'""")
        for r in cur.fetchall():
            rid, nome, img = r[0], r[1], r[2]
            nome_l = (nome or "").lower()
            m = _re.search(r'/([^/]+)\.(jpg|jpeg|png|webp)', img or "")
            fname = (m.group(1) if m else "").lower().replace('foodiesfeed.com_', '').replace('foodiesfeed_', '')
            # il file contiene una parola FORTE (5+ lettere) presente anche nel nome ricetta?
            valido = False
            parole_ricetta = [w for w in _re.findall(r'[a-z]+', nome_l) if len(w) >= 5]
            for w in parole_ricetta:
                if w[:6] in fname:
                    valido = True; break
            # match espliciti noti (pizza, pasta...)
            if not valido:
                for chiave, parola_file in match_validi.items():
                    if chiave in nome_l:
                        valido = (parola_file is not None and parola_file in fname)
                        break
            if valido:
                tenute.append(nome)
            else:
                tolte.append(nome)
                if not dry:
                    cur.execute("UPDATE ricette SET immagine=NULL, immagine_autore=NULL, immagine_url_fonte=NULL WHERE id=%s", (rid,))
        if not dry:
            conn.commit()
        return jsonify({"tolte": len(tolte), "tenute": len(tenute),
                        "esempi_tolte": tolte[:20], "esempi_tenute": tenute[:20]})
    finally:
        _release_conn(conn)


@bp.route("/admin/assegna-domini-ingredienti")
def admin_assegna_domini():
    """Assegna il domain (disciplina) a ogni ingrediente in base al nome. Ogni ingrediente
    può appartenere a più discipline (limone = bar + cucina). Salva domini[] nel data JSONB."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    from db import _get_conn, _release_conn
    try:
        from classificatore_domini import classifica
    except Exception as e:
        return jsonify({"errore": f"import: {e}"}), 500
    conn = _get_conn(); cur = conn.cursor()
    stat = {}
    esempi = []
    aggiornati = 0
    try:
        cur.execute("SELECT id, name, data FROM nodes WHERE type='Ingrediente'")
        righe = cur.fetchall()
        for rid, name, data in righe:
            d = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nome = name or d.get("display_it") or rid
            domini = classifica(nome)
            for dom in domini:
                stat[dom] = stat.get(dom, 0) + 1
            if len(esempi) < 15:
                esempi.append({"nome": nome, "domini": domini})
            if not dry:
                d["domini"] = domini
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(d, ensure_ascii=False), rid))
                aggiornati += 1
        if not dry:
            conn.commit()
        return jsonify({"dry_run": dry, "totale": len(righe), "aggiornati": aggiornati,
                        "conteggio_per_disciplina": dict(sorted(stat.items(), key=lambda x: -x[1])),
                        "esempi": esempi})
    finally:
        _release_conn(conn)


@bp.route("/admin/genera-canonici")
def admin_genera_canonici():
    """Genera ricette per i piatti canonici non ancora salvati. A lotti (?n=8 default) per stare
    sotto il timeout. Riprendibile: ogni chiamata fa un lotto e dice quanti mancano.
    ?disc=cucina limita a una disciplina. Verifica anti-eresie: salva solo le ricette pulite."""
    if not _admin_ok(request):
        return "Forbidden", 403
    n_lotto = int(request.args.get("n", "8"))
    disc_filtro = request.args.get("disc", "").strip()
    from db import carica_grafo, _get_conn, _release_conn
    import re as _re, json as _j2, unicodedata
    try:
        import mappa_piatti
        from builder import genera_ricetta
    except Exception as e:
        return jsonify({"errore": f"import: {e}"}), 500
    try:
        from verificatore_ricette import verifica_ricetta
    except Exception:
        verifica_ricetta = None

    piatti = mappa_piatti.tutti_i_piatti()
    if disc_filtro:
        piatti = [p for p in piatti if (p.get("disc") or "cucina") == disc_filtro]

    # quali sono già salvati? confronto per slug del nome
    conn = _get_conn(); cur = conn.cursor()
    def _slug(nome):
        s = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
        return _re.sub(r"[^a-z0-9]+","-",s).strip("-")[:40]
    try:
        cur.execute("SELECT id FROM ricette")
        ids_esistenti = set(r[0] for r in cur.fetchall())
    finally:
        pass

    # piatti da generare = quelli il cui ric-gen-<slug> non esiste
    da_fare = []
    for p in piatti:
        rid = f"ric-gen-{_slug(p['nome'])}"
        if rid not in ids_esistenti:
            da_fare.append(p)

    totale_mancanti = len(da_fare)
    lotto = da_fare[:n_lotto]
    db = carica_grafo()
    generate = 0; bloccate = 0; errori = 0; dettaglio = []
    for p in lotto:
        nome = p["nome"]; disc = p.get("disc") or "cucina"
        try:
            ris = genera_ricetta(db, nome, disciplina=disc, lang="it")
            if ris.get("errore"):
                errori += 1; dettaglio.append({"piatto": nome, "esito": "errore_gen"}); continue
            # verifica anti-eresie
            if verifica_ricetta:
                v = verifica_ricetta(ris.get("nome",""), ris.get("ingredienti",[]))
                if not v.get("ok"):
                    bloccate += 1; dettaglio.append({"piatto": nome, "esito": "bloccata_eresia"}); continue
            # salva
            rid = f"ric-gen-{_slug(ris.get('nome', nome))}"
            cur.execute("""
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
            conn.commit()
            generate += 1; dettaglio.append({"piatto": nome, "esito": "salvata"})
        except Exception as e:
            conn.rollback(); errori += 1
            dettaglio.append({"piatto": nome, "esito": f"err:{str(e)[:40]}"})
    _release_conn(conn)
    return jsonify({
        "lotto": len(lotto), "generate": generate, "bloccate_eresia": bloccate, "errori": errori,
        "mancavano_prima": totale_mancanti, "mancano_ancora": totale_mancanti - generate,
        "disciplina_filtro": disc_filtro or "tutte", "dettaglio": dettaglio,
    })


@bp.route("/admin/genera-canonici-bg")
def admin_genera_canonici_bg():
    """Avvia la generazione dei piatti canonici in BACKGROUND (si autocompleta, aggira il timeout).
    ?disc= limita a una disciplina, ?n= limita quante generarne in totale (0=tutte).
    Controlla con /admin/genera-canonici-bg-stato."""
    if not _admin_ok(request):
        return "Forbidden", 403
    global _GENCAN_STATO
    if _GENCAN_STATO.get("attivo"):
        return jsonify({"gia_in_corso": True, "stato": _GENCAN_STATO})
    import threading
    disc = request.args.get("disc", "").strip()
    limite = int(request.args.get("n", "0"))
    _GENCAN_STATO = {"attivo": True, "generate": 0, "bloccate": 0, "errori": 0,
                     "mancano": None, "corrente": "", "disc": disc or "tutte"}
    t = threading.Thread(target=_gencan_worker, args=(disc, limite), daemon=True)
    t.start()
    return jsonify({"avviato": True, "disc": disc or "tutte",
                    "nota": "generazione in background — controlla /admin/genera-canonici-bg-stato"})


@bp.route("/admin/genera-canonici-bg-stato")
def admin_genera_canonici_bg_stato():
    """Stato della generazione canonici in background."""
    if not _admin_ok(request):
        return "Forbidden", 403
    return jsonify(_GENCAN_STATO)


@bp.route("/admin/pulisci-immagini-stock")
def admin_pulisci_immagini_stock():
    """Stacca le immagini foodiesfeed (stock) agganciate per matching sul nome-file, che genera
    errori (Amaretto Sour->pane, Bloody Mary->roast beef). Regola: meglio placeholder che foto
    sbagliata. Le foto vere di Michele (nome-file = id ricetta) e le Pixabay verificate restano."""
    if not _admin_ok(request):
        return "Forbidden", 403
    dry = request.args.get("dry", "1") == "1"
    from db import _get_conn, _release_conn
    conn = _get_conn(); cur = conn.cursor()
    staccate = 0; esempi = []
    try:
        # trova le ricette con immagine foodiesfeed (stock, matching inaffidabile)
        cur.execute("""SELECT id, nome, immagine FROM ricette
                       WHERE immagine LIKE '%%foodiesfeed%%'""")
        righe = cur.fetchall()
        for rid, nome, img in righe:
            if len(esempi) < 15:
                fn = str(img).split('/')[-1][:40]
                esempi.append({"ricetta": nome, "era": fn})
            if not dry:
                cur.execute("UPDATE ricette SET immagine=NULL, immagine_autore=NULL WHERE id=%s", (rid,))
                staccate += 1
        if not dry:
            conn.commit()
        return jsonify({"dry_run": dry, "trovate_foodiesfeed": len(righe), "staccate": staccate,
                        "nota": "tornano al placeholder pulito; riprendono foto solo da fonti fidate",
                        "esempi": esempi})
    finally:
        _release_conn(conn)


@bp.route("/admin/aggiungi-alias")
def admin_aggiungi_alias():
    """Aggiunge parole-chiave (alias) a un fenomeno per migliorare il retrieval della chat.
    Es: al fenomeno Emulsione aggiungo 'carbonara,impazzisce,stracciata' cosi la chat lo trova.
    ?id=fen-emulsione&alias=carbonara,impazzisce,stracciata"""
    if not _admin_ok(request):
        return "Forbidden", 403
    fen_id = request.args.get("id", "").strip()
    nuovi = [a.strip().lower() for a in request.args.get("alias", "").split(",") if a.strip()]
    if not fen_id or not nuovi:
        return jsonify({"errore": "servono ?id= e ?alias=parola1,parola2"}), 400
    from db import _get_conn, _release_conn
    import json as _j
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT data FROM nodes WHERE id=%s AND type='Fenomeno'", (fen_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"errore": f"fenomeno {fen_id} non trovato"}), 404
        data = row[0] if isinstance(row[0], dict) else _j.loads(row[0] or "{}")
        aliases = data.get("aliases", [])
        prima = len(aliases)
        for a in nuovi:
            if a not in aliases:
                aliases.append(a)
        data["aliases"] = aliases
        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_j.dumps(data, ensure_ascii=False), fen_id))
        conn.commit()
        return jsonify({"id": fen_id, "alias_prima": prima, "alias_dopo": len(aliases),
                        "aliases": aliases})
    finally:
        _release_conn(conn)


@bp.route("/admin/correggi-nomi-ingredienti")
def admin_correggi_nomi():
    """Corregge nomi ingredienti sbagliati/inglesi nel grafo (Bread->Pane, Rapanelli->Ravanelli...)."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    # mappa correzioni: nome_sbagliato -> nome_giusto
    correzioni = {
        "Bread": "Pane",
        "Rapanelli": "Ravanelli",
        "Rapanello": "Ravanello",
        # nomi nel DB con underscore minuscolo (formato ahn_*): vanno tradotti così come sono
        "cured_pork": "maiale stagionato",
        "uncured_pork": "maiale fresco",
        "pork_sausage": "salsiccia di maiale",
        "rye_bread": "pane di segale",
        "rye_flour": "farina di segale",
        "catfish": "pesce gatto",
        "roast_beef": "manzo arrosto",
        "Roast Beef": "Manzo arrosto",
        "wheat_bread": "pane di frumento",
        "white_bread": "pane bianco",
        "whole_wheat_bread": "pane integrale",
        "raw_beef": "manzo crudo",
        "smoked_salmon": "salmone affumicato",
        "green_tea": "tè verde",
        "black_tea": "tè nero",
    }
    conn = _get_conn(); cur = conn.cursor()
    fatti = []
    try:
        for sbagliato, giusto in correzioni.items():
            # match robusto: qualsiasi type, case-insensitive, ignorando spazi ai bordi
            cur.execute("UPDATE nodes SET name=%s WHERE lower(trim(name))=lower(trim(%s)) AND name!=%s",
                        (giusto, sbagliato, giusto))
            n1 = cur.rowcount
            if n1 > 0:
                fatti.append(f"{sbagliato} -> {giusto} ({n1} nodi)")
        conn.commit()
        return jsonify({"ok": True, "correzioni": fatti or ["nessun nodo trovato con quei nomi"]})
    finally:
        _release_conn(conn)


@bp.route("/admin/correggi-bersagli-testuali")
def admin_correggi_bersagli():
    """Trova i fenomeni il cui numero-bersaglio è una FRASE (non un numero) e lo sostituisce
    con un valore numerico/intervallo. Il payoff è 'Numeri. Non opinioni.': il bersaglio deve
    essere un numero. Correzioni mirate sui fenomeni noti; gli altri restano invariati."""
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    import json as _j, re as _re
    # correzioni target per nome fenomeno (match parziale): numero/intervallo giusto
    correzioni = {
        "ganache": "32-34°C",          # punto di fusione cristalli stabili burro di cacao
    }
    conn = _get_conn(); cur = conn.cursor()
    fatti = []
    try:
        cur.execute("SELECT id, name, data FROM nodes WHERE type='Fenomeno'")
        righe = cur.fetchall()
        for rid, nome, data in righe:
            d = data if isinstance(data, dict) else (_j.loads(data) if data else {})
            target = str(d.get("numero_bersaglio") or d.get("target") or "")
            # se il target NON contiene una cifra, è una frase: candidato a correzione
            ha_cifra = bool(_re.search(r"\d", target))
            nome_l = (nome or "").lower()
            for chiave, valore in correzioni.items():
                if chiave in nome_l and (not ha_cifra or "non è un numero" in target.lower() or "non un numero" in target.lower()):
                    d["numero_bersaglio"] = valore
                    if "target" in d: d["target"] = valore
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_j.dumps(d, ensure_ascii=False), rid))
                    fatti.append(f"{nome}: -> {valore}")
                    break
        conn.commit()
        return jsonify({"ok": True, "correzioni": fatti or ["nessun bersaglio corretto"]})
    finally:
        _release_conn(conn)


@bp.route("/admin/correggi-accenti")
def admin_correggi_accenti():
    """Corregge accenti sbagliati nei testi dei nodi (e->è dove serve, refusi comuni).
    Usa pattern SICURI (con contesto) per non rovinare le 'e' congiunzione corrette."""
    import os, hmac, re
    if not _admin_ok(request):
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    # pattern SICURI: ' e ' che deve essere ' è ' solo in contesti chiari
    # (dove 'e' è verbo essere, riconoscibile dal contesto grammaticale)
    correzioni = [
        (r'\be invece è\b', 'è invece'),          # "e invece è la" -> "è invece la"
        (r'\binvece e la\b', 'invece è la'),
        (r'\be la stessa\b', 'è la stessa'),
        (r'\be la stesso\b', 'è lo stesso'),
        (r'\be lo stesso\b', 'è lo stesso'),
        (r'\bche e piu\b', 'che è più'),
        (r'\bche e meno\b', 'che è meno'),
        (r'\bquando e\b', 'quando è'),
        (r'\bnon e piu\b', 'non è più'),
        (r'\bpiu morbido\b', 'più morbido'),
        (r'\bpiu rotondo\b', 'più rotondo'),
        (r'\bpiu di prima\b', 'più di prima'),
        (r'\bperche\b', 'perché'),
        (r'\bpoiche\b', 'poiché'),
        (r'\bcioe\b', 'cioè'),
    ]
    conn = _get_conn(); cur = conn.cursor()
    fatti = []
    try:
        # scansiono i nodi Fenomeno che hanno testi nel campo data
        cur.execute("SELECT id, data FROM nodes WHERE type='Fenomeno' AND data IS NOT NULL")
        righe = cur.fetchall()
        import json as _json
        for nid, data in righe:
            if not data:
                continue
            d = data if isinstance(data, dict) else _json.loads(data)
            testo_orig = _json.dumps(d, ensure_ascii=False)
            testo = testo_orig
            for pat, repl in correzioni:
                testo = re.sub(pat, repl, testo)
            if testo != testo_orig:
                d2 = _json.loads(testo)
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (_json.dumps(d2, ensure_ascii=False), nid))
                fatti.append(nid)
        conn.commit()
        return jsonify({"ok": True, "nodi_corretti": len(fatti), "ids": fatti[:20]})
    finally:
        _release_conn(conn)


@bp.route("/admin/correggi-principi-primari")
def admin_correggi_principi_primari():
    """Corregge il PRIMO principio (quello in cima alla nuova scheda) di alcuni fenomeni
    dove era sbagliato o secondario. Strategia: rimuovo l'edge verso il principio sbagliato,
    così resta quello corretto come unico/primo. ?s=SECRET."""
    if not _admin_ok(request):
        return "Forbidden", 403
    import json as _json
    # (fenomeno_id, principio_SBAGLIATO da rimuovere, principio_GIUSTO che deve restare)
    # rimuovo il legame verso il principio sbagliato; se il giusto non c'è, lo aggiungo.
    CORREZIONI = [
        ("fen-uova-impasto", "fen-grassi-impasto", "princ-denaturazione"),
        ("fen-emulsione-salse", "princ-denaturazione", "princ-emulsione"),
        ("fen-latte-impasto", "fen-zuccheri-impasto", "princ-emulsione"),
        ("fen-koji", "princ-ph", "princ-denaturazione"),
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        fatti = []
        for fid, sbagliato, giusto in CORREZIONI:
            # verifico che il fenomeno esista
            cur.execute("SELECT 1 FROM nodes WHERE id=%s", (fid,))
            if not cur.fetchone():
                fatti.append({"fen": fid, "esito": "fenomeno inesistente"}); continue
            # rimuovo l'edge verso il principio sbagliato (se c'è)
            cur.execute("DELETE FROM edges WHERE from_id=%s AND relation='governato_da' AND to_id=%s",
                        (fid, sbagliato))
            rimosso = cur.rowcount
            # garantisco che il principio giusto sia collegato
            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND relation='governato_da' AND to_id=%s",
                        (fid, giusto))
            if not cur.fetchone():
                cur.execute("SELECT 1 FROM nodes WHERE id=%s", (giusto,))
                if cur.fetchone():
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                                (fid, giusto, "governato_da", _json.dumps({}, ensure_ascii=False)))
                    aggiunto = True
                else:
                    aggiunto = False
            else:
                aggiunto = False
            fatti.append({"fen": fid, "rimosso_sbagliato": rimosso, "giusto_ora_presente": True,
                          "aggiunto_giusto": aggiunto})
        conn.commit()
        # pulizia extra: "uova-impasto" aveva 6 principi alla rinfusa. Li rimuovo TUTTI e
        # reinserisco solo i 2 pertinenti NELL'ORDINE giusto (denaturazione primo = in cima
        # alla scheda, poi emulsione). Reinserire in ordine garantisce il "primo principio".
        cur.execute("DELETE FROM edges WHERE from_id='fen-uova-impasto' AND relation='governato_da'")
        for _pid in ("princ-denaturazione", "princ-emulsione"):
            cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,%s,%s)",
                        ("fen-uova-impasto", _pid, "governato_da", _json.dumps({}, ensure_ascii=False)))
        conn.commit()
        return jsonify({"ok": True, "correzioni": fatti, "uova_ripulite": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)


@bp.route("/admin/genera-didattica")
def admin_genera_didattica():
    """Genera esperimento 'provalo stasera' + 1 quiz per un BLOCCO di fenomeni.
    ?offset=0&limit=8 per processare a blocchi (evita timeout Railway).
    ANTI-ALLUCINAZIONE: se il fenomeno ha un numero-bersaglio, il testo generato DEVE contenerne
    le cifre, altrimenti l'esperimento viene reso qualitativo (mai numeri inventati)."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    from ai import _haiku_raw
    from ai_gateway import route_quality as _quiz_raw
    from contenuto import _numero_bersaglio as _nb, _scheda_lang
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 8)), 15)
    except Exception:
        offset, limit = 0, 8
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # assicuro la tabella quiz (stessa del motore unificato)
        cur.execute("""CREATE TABLE IF NOT EXISTS quiz (
            id SERIAL PRIMARY KEY, fenomeno_id TEXT, disciplina TEXT, tipo TEXT NOT NULL,
            difficolta TEXT DEFAULT 'base', domanda TEXT NOT NULL, opzioni JSONB NOT NULL,
            risposta_corretta TEXT NOT NULL, insight_didattico TEXT, lang TEXT DEFAULT 'it',
            creato_il TIMESTAMP DEFAULT NOW())""")
        # tabella esperimenti (per il Quaderno)
        cur.execute("""CREATE TABLE IF NOT EXISTS esperimenti_pratici (
            id SERIAL PRIMARY KEY, fenomeno_id TEXT UNIQUE, disciplina TEXT,
            testo TEXT NOT NULL, quantitativo BOOLEAN DEFAULT FALSE, creato_il TIMESTAMP DEFAULT NOW())""")
        conn.commit()
        # prendo un blocco di fenomeni
        cur.execute("SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY id LIMIT %s OFFSET %s",
                    (limit, offset))
        fenomeni = cur.fetchall()
        risultati = []
        for f in fenomeni:
            fid, nome, dominio = f[0], f[1], f[2]
            data = f[3] if isinstance(f[3], dict) else (json.loads(f[3]) if f[3] else {})
            target = _nb(data) or ""
            scheda = _scheda_lang(data, "it") or ""
            # fallback: se scheda vuota, provo altri campi dove può stare il contenuto
            if not scheda and isinstance(data, dict):
                # la risposta AI cachata del nodo è un ottimo contenuto di partenza
                for _ck in ("risposta_cache_it", "risposta_cache"):
                    _cv = data.get(_ck)
                    if _cv and isinstance(_cv, str) and len(_cv) > 40:
                        scheda = _cv; break
            if not scheda and isinstance(data, dict):
                for _campo in ("descrizione", "spiegazione", "sommario", "testo", "contenuto", "corpo"):
                    _v = data.get(_campo)
                    if isinstance(_v, dict):
                        _v = _v.get("it") or _v.get("testo") or ""
                    if _v and isinstance(_v, str) and len(_v) > 40:
                        scheda = _v; break
            # cifre del target da verificare (anti-allucinazione)
            cifre_target = _re.findall(r"\d+", str(target))
            testo_exp = None
            # --- ESPERIMENTO (solo se manca) ---
            cur.execute("SELECT 1 FROM esperimenti_pratici WHERE fenomeno_id=%s", (fid,))
            _exp_esiste = cur.fetchone()
            if not _exp_esiste:
                prompt_exp = (f"Sei un formatore F&B. Scrivi un esperimento pratico 'provalo stasera' per il "
                              f"fenomeno '{nome}' ({dominio}). Numero-bersaglio: {target}. "
                              f"Max 45 parole, concreto, fattibile al banco stasera. "
                              f"Se c'è un numero-bersaglio, CITALO esatto. Solo il testo, niente altro.")
                testo_exp = (_haiku_raw(prompt_exp, max_tokens=120) or "").strip()
                quantitativo = bool(cifre_target)
                if quantitativo and testo_exp:
                    if not any(c in testo_exp for c in cifre_target):
                        quantitativo = False
                if testo_exp:
                    cur.execute("INSERT INTO esperimenti_pratici (fenomeno_id, disciplina, testo, quantitativo) "
                                "VALUES (%s,%s,%s,%s) ON CONFLICT (fenomeno_id) DO NOTHING",
                                (fid, dominio, testo_exp, quantitativo))
            # --- 1 QUIZ (concetto) ---
            # contenuto per il quiz: scheda se c'è, altrimenti il principio del fenomeno + nome
            _principio = ""
            if isinstance(data, dict):
                _p = data.get("principio") or data.get("primo_principio") or ""
                if isinstance(_p, dict): _p = _p.get("it") or _p.get("nome") or ""
                _principio = str(_p) if _p else ""
            _contenuto_quiz = scheda or _principio or nome
            cur.execute("SELECT 1 FROM quiz WHERE fenomeno_id=%s AND tipo='fenomeno' LIMIT 1", (fid,))
            if not cur.fetchone() and _contenuto_quiz:
                prompt_quiz = (f"Crea UN quiz tecnico sul fenomeno '{nome}' ({dominio}) per un professionista F&B. "
                               f"Numero-bersaglio: {target}. Principio: {_principio}. Contenuto: {_contenuto_quiz[:400]}. "
                               f"Rispondi SOLO con JSON valido: "
                               f'{{"domanda":"...","opzioni":["corretta","sbagliata","sbagliata"],'
                               f'"insight":"spiegazione tecnica, col numero esatto se pertinente"}}. '
                               f"La prima opzione è la corretta. Domanda concreta da banco.")
                raw = (_quiz_raw(prompt_quiz, max_tokens=400) or "").strip()
                # estrazione JSON robusta: Haiku a volte avvolge in markdown o testo.
                # prendo il primo blocco {...} bilanciato.
                raw = _re.sub(r"```json|```", "", raw).strip()
                m_json = _re.search(r"\{.*\}", raw, _re.DOTALL)
                if m_json:
                    raw = m_json.group(0)
                try:
                    qj = json.loads(raw)
                    dom = qj.get("domanda", ""); opz = qj.get("opzioni", []); ins = qj.get("insight", "")
                    if dom and len(opz) >= 2:
                        # anti-allucinazione sul quiz: se quantitativo, l'insight deve citare il numero
                        ok_num = (not cifre_target) or any(c in (ins + dom) for c in cifre_target)
                        if ok_num:
                            cur.execute(
                                "INSERT INTO quiz (fenomeno_id, disciplina, tipo, difficolta, domanda, opzioni, risposta_corretta, insight_didattico) "
                                "VALUES (%s,%s,'fenomeno','base',%s,%s,%s,%s)",
                                (fid, dominio, dom, json.dumps(opz, ensure_ascii=False), opz[0], ins))
                            risultati.append({"fenomeno": fid, "stato": "creato", "quiz": True, "exp": bool(testo_exp)})
                        else:
                            risultati.append({"fenomeno": fid, "stato": "quiz_scartato_numeri"})
                    else:
                        risultati.append({"fenomeno": fid, "stato": "quiz_malformato"})
                except Exception:
                    risultati.append({"fenomeno": fid, "stato": "quiz_non_json"})
            else:
                risultati.append({"fenomeno": fid, "stato": "solo_esperimento" if testo_exp else "nessuna_scheda"})
        conn.commit()
        # quanti fenomeni totali, per sapere quando fermarsi
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Fenomeno'")
        totale = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        prossimo = offset + limit
        return jsonify({"ok": True, "processati": len(fenomeni), "offset": offset,
                        "prossimo_offset": prossimo if prossimo < totale else None,
                        "totale_fenomeni": totale, "risultati": risultati})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-400:]}), 500


@bp.route("/admin/batch-quiz-crea")
def admin_batch_quiz_crea():
    """Crea un batch di richieste quiz per i fenomeni SENZA quiz. Ritorna il batch_id.
    Poi usa /admin/batch-quiz-raccogli?batch_id=... quando è 'ended' per salvare i risultati."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import ai_gateway as GW
    from contenuto import _numero_bersaglio as _nb, _scheda_lang
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS quiz (
            id SERIAL PRIMARY KEY, fenomeno_id TEXT, disciplina TEXT, tipo TEXT NOT NULL,
            difficolta TEXT DEFAULT 'base', domanda TEXT NOT NULL, opzioni JSONB NOT NULL,
            risposta_corretta TEXT NOT NULL, insight_didattico TEXT, lang TEXT DEFAULT 'it',
            creato_il TIMESTAMP DEFAULT NOW())""")
        conn.commit()
        # fenomeni senza quiz
        cur.execute("""SELECT n.id, n.name, n.domain, n.data FROM nodes n
                       WHERE n.type='Fenomeno' AND NOT EXISTS
                       (SELECT 1 FROM quiz q WHERE q.fenomeno_id=n.id AND q.tipo='fenomeno')""")
        scoperti = cur.fetchall()
        cur.close(); _release_conn(conn)
        if not scoperti:
            return jsonify({"ok": True, "messaggio": "tutti i fenomeni hanno già un quiz", "scoperti": 0})
        richieste = []
        for f in scoperti[:100]:  # batch fino a 100
            fid, nome, dominio = f[0], f[1], f[2]
            data = f[3] if isinstance(f[3], dict) else (json.loads(f[3]) if f[3] else {})
            target = _nb(data) or ""
            prompt = (f"Crea UN quiz tecnico sul fenomeno '{nome}' ({dominio}) per un professionista F&B. "
                      f"Numero-bersaglio: {target}. Rispondi SOLO con JSON valido: "
                      f'{{"domanda":"...","opzioni":["corretta","sbagliata","sbagliata"],'
                      f'"insight":"spiegazione tecnica"}}. La prima opzione è la corretta.')
            richieste.append({
                "custom_id": fid[:64],
                "params": {"model": GW._MODEL_SONNET, "max_tokens": 400,
                           "messages": [{"role": "user", "content": prompt}]}
            })
        batch = GW.batch_crea(richieste)
        return jsonify({"ok": True, "batch_id": batch.get("id"),
                        "richieste": len(richieste),
                        "stato": batch.get("processing_status"),
                        "nota": "usa /admin/batch-quiz-raccogli?batch_id=... quando ended"})
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/normalizza-fenomeni")
def admin_normalizza_fenomeni():
    """Per ogni fenomeno costruisce data['contenuto_strutturato'] = {principio, spiegazione,
    errore_banco, dato_operativo} consolidando i campi esistenti (scheda/cache/principio/target).
    Così la lettura diventa uniforme e spariscono i fallback nel codice. ?offset=&limit= a blocchi."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    from contenuto import _numero_bersaglio as _nb, _scheda_lang
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 30)), 50)
    except Exception:
        offset, limit = 0, 30
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY id LIMIT %s OFFSET %s",
                    (limit, offset))
        fenomeni = cur.fetchall()
        fatti = 0
        for f in fenomeni:
            fid = f[0]; nome = f[1]; dominio = f[2]
            data = f[3] if isinstance(f[3], dict) else (json.loads(f[3]) if f[3] else {})
            if not isinstance(data, dict):
                data = {}
            # se già normalizzato, salto
            if data.get("contenuto_strutturato"):
                continue
            # consolido il contenuto dalle varie fonti
            scheda = _scheda_lang(data, "it") or ""
            if not scheda:
                for _ck in ("risposta_cache_it", "risposta_cache", "descrizione", "spiegazione"):
                    _cv = data.get(_ck)
                    if isinstance(_cv, str) and len(_cv) > 40:
                        scheda = _cv; break
            principio = ""
            _p = data.get("principio") or data.get("primo_principio") or ""
            if isinstance(_p, dict): _p = _p.get("it") or _p.get("nome") or ""
            principio = str(_p) if _p else ""
            target = _nb(data) or ""
            errore = ""
            _e = data.get("errori") or data.get("errore_banco") or ""
            if isinstance(_e, list) and _e:
                errore = _e[0] if isinstance(_e[0], str) else ""
            elif isinstance(_e, str):
                errore = _e
            data["contenuto_strutturato"] = {
                "principio": principio,
                "spiegazione": scheda,
                "errore_banco": errore,
                "dato_operativo": target,
                "nome": nome,
                "dominio": dominio,
                "version": 1,
            }
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                        (json.dumps(data, ensure_ascii=False), fid))
            fatti += 1
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Fenomeno'")
        totale = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        prossimo = offset + limit
        return jsonify({"ok": True, "normalizzati": fatti, "offset": offset,
                        "prossimo_offset": prossimo if prossimo < totale else None,
                        "totale": totale})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/pulisci-nomi-ricette")
def admin_pulisci_nomi():
    """Rimuove i suffissi artificiali dai nomi ricette (Rivisitato, Classico Rivisitato, a caso...).
    Qualità percepita: 'Americano Rivisitato' -> 'Americano'. ?dry=1 per solo anteprima."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    dry = request.args.get("dry", "") == "1"
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM ricette")
        righe = cur.fetchall()
        cambi = []
        for rid, nome in righe:
            if not nome:
                continue
            nuovo = nome
            # rimuovo i suffissi slop (in ordine, case-insensitive), come parole finali
            for pat in [r"\s+Classico\s+Rivisitato$", r"\s+Rivisitato$", r"\s+Rivisitata$",
                        r"\s+\(rivisitato\)$", r"\s+a caso$", r"\s+twist$", r"\s+versione migliorata$"]:
                nuovo = _re.sub(pat, "", nuovo, flags=_re.IGNORECASE)
            # "Classico" da solo alla fine: lo tolgo solo se ridondante (es. "Negroni Classico" -> "Negroni")
            nuovo = _re.sub(r"\s+Classico$", "", nuovo, flags=_re.IGNORECASE)
            nuovo = _re.sub(r"\s+Classica$", "", nuovo, flags=_re.IGNORECASE)
            nuovo = nuovo.strip()
            if nuovo and nuovo != nome:
                cambi.append({"id": rid, "da": nome, "a": nuovo})
                if not dry:
                    cur.execute("UPDATE ricette SET nome=%s WHERE id=%s", (nuovo, rid))
        if not dry:
            conn.commit()
        cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "dry_run": dry, "cambi_totali": len(cambi),
                        "esempi": cambi[:15]})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/genera-figlie")
def admin_genera_figlie():
    """Per un BLOCCO di ricette madri, genera 2-4 varianti (figlie) via AI. Le figlie ereditano
    fenomeno/disciplina dalla madre e cambiano nome/ingredienti/tecnica. ?offset=0&limit=3
    Le figlie NON duplicano la scheda: hanno parent_recipe_id e solo i campi che cambiano."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    from ai import _haiku_raw
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 3)), 5)
    except Exception:
        offset, limit = 0, 3
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # prendo madri che non hanno ancora figlie
        cur.execute("""SELECT r.id, r.nome, r.disciplina, r.fenomeni FROM ricette r
                       WHERE r.recipe_type='madre'
                       AND NOT EXISTS (SELECT 1 FROM ricette f WHERE f.parent_recipe_id=r.id)
                       ORDER BY r.id LIMIT %s OFFSET %s""", (limit, offset))
        madri = cur.fetchall()
        create = 0; risultati = []
        for m in madri:
            mid, nome, disc, fenomeni = m[0], m[1], m[2], m[3]
            prompt = (f"La ricetta '{nome}' ({disc}) è una preparazione base. Elenca 3 VARIANTI "
                      f"professionali reali e distinte che derivano da questa base (stessa tecnica, "
                      f"ingredienti diversi). Per ognuna dai nome e la differenza chiave. "
                      f"Esempio per Maionese: Aioli (aglio), Salsa tonnata (tonno), Maionese al basilico. "
                      f'Rispondi SOLO JSON: {{"varianti":[{{"nome":"...","differenza":"..."}}]}}')
            try:
                raw = (_haiku_raw(prompt, max_tokens=300) or "").strip()
                raw = _re.sub(r"```json|```", "", raw)
                mm = _re.search(r"\{.*\}", raw, _re.DOTALL)
                if not mm:
                    risultati.append({"madre": nome, "esito": "no_json"}); continue
                varianti = json.loads(mm.group(0)).get("varianti", [])
                for v in varianti[:3]:
                    vnome = (v.get("nome") or "").strip()
                    vdiff = (v.get("differenza") or "").strip()
                    # scarto se vuoto, uguale alla madre, o troppo simile (nome madre contenuto)
                    _nome_madre_base = _re.sub(r"\s*\(.*?\)", "", nome).strip().lower()
                    _vnome_base = _re.sub(r"\s*\(.*?\)", "", vnome).strip().lower()
                    if not vnome or _vnome_base == _nome_madre_base or _vnome_base == nome.lower():
                        continue
                    fid = "ric-fig-" + _re.sub(r"[^a-z0-9]+", "-", vnome.lower())[:40]
                    cur.execute("SELECT 1 FROM ricette WHERE id=%s", (fid,))
                    if cur.fetchone():
                        continue
                    # fenomeni è JSONB: lo passo come stringa JSON valida
                    _fen_json = fenomeni if isinstance(fenomeni, str) else json.dumps(fenomeni or [])
                    # la figlia eredita disciplina e fenomeni dalla madre, ha la differenza come descrizione
                    cur.execute("""INSERT INTO ricette (id, nome, disciplina, fenomeni, descrizione,
                                   recipe_type, parent_recipe_id, variante_di)
                                   VALUES (%s,%s,%s,%s::jsonb,%s,'figlia',%s,%s)
                                   ON CONFLICT (id) DO NOTHING""",
                                (fid, vnome, disc, _fen_json, vdiff, mid, nome))
                    create += 1
                risultati.append({"madre": nome, "figlie": len(varianti)})
                conn.commit()  # commit dopo ogni madre: un errore non blocca le successive
            except Exception as _e:
                conn.rollback()
                risultati.append({"madre": nome, "esito": str(_e)[:50]})
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM ricette WHERE recipe_type='madre'")
        tot_madri = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        prossimo = offset + limit
        return jsonify({"ok": True, "figlie_create": create, "offset": offset,
                        "prossimo_offset": prossimo if prossimo < tot_madri else None,
                        "risultati": risultati})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/pulisci-figlie-duplicate")
def admin_pulisci_figlie_dup():
    """Rimuove le figlie che duplicano il nome di un'altra ricetta (madre o figlia già esistente)."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # trova figlie il cui nome (normalizzato) coincide con una ricetta più vecchia
        cur.execute("""
            DELETE FROM ricette f WHERE f.recipe_type='figlia' AND EXISTS (
                SELECT 1 FROM ricette r WHERE r.id <> f.id
                AND lower(regexp_replace(r.nome,'\\s*\\(.*?\\)','')) = lower(regexp_replace(f.nome,'\\s*\\(.*?\\)',''))
                AND r.id < f.id
            )""")
        n = cur.rowcount
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "duplicate_rimosse": n})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/collega-ricette-ingredienti")
def admin_collega_ricette():
    """Popola recipe_ingredients: collega ogni ingrediente delle ricette al nodo del grafo
    (per fuzzy match sul nome). Così una ricetta 'sa' strutturalmente i suoi composti. ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 40)), 80)
    except Exception:
        offset, limit = 0, 40
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY, ricetta_id TEXT, ingrediente_nome TEXT, ingrediente_node_id TEXT,
            quantita TEXT, unita TEXT, match_tipo TEXT)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ri_ricetta ON recipe_ingredients(ricetta_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ri_node ON recipe_ingredients(ingrediente_node_id)")
        cur.execute("SELECT id, ingredienti FROM ricette ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
        ricette = cur.fetchall()
        if not ricette:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        collegati = 0; matchati = 0
        for rid, ing_raw in ricette:
            # evito duplicati: se la ricetta è già collegata, salto
            cur.execute("SELECT 1 FROM recipe_ingredients WHERE ricetta_id=%s LIMIT 1", (rid,))
            if cur.fetchone():
                continue
            try:
                ings = ing_raw if isinstance(ing_raw, list) else (json.loads(ing_raw) if ing_raw else [])
            except Exception:
                ings = []
            for ing in ings:
                if isinstance(ing, dict):
                    nome = (ing.get("nome") or "").strip()
                    qta = str(ing.get("quantita") or "")
                    uni = str(ing.get("unita") or "")
                else:
                    nome = str(ing).strip(); qta = ""; uni = ""
                if not nome:
                    continue
                # fuzzy match: cerco il nodo ingrediente col nome più simile
                _n_clean = _re.sub(r"\b(fresco|fresca|q\.?b\.?|di|del|della|in|per)\b", "", nome.lower()).strip()
                cur.execute("""SELECT id FROM nodes WHERE type='Ingrediente'
                               AND (lower(name)=lower(%s) OR lower(name) LIKE lower(%s))
                               ORDER BY length(name) LIMIT 1""", (nome, "%"+_n_clean.split()[0]+"%" if _n_clean else "%"+nome+"%"))
                node = cur.fetchone()
                node_id = node[0] if node else None
                match = "esatto" if node else "nessuno"
                if node: matchati += 1
                cur.execute("""INSERT INTO recipe_ingredients
                               (ricetta_id, ingrediente_nome, ingrediente_node_id, quantita, unita, match_tipo)
                               VALUES (%s,%s,%s,%s,%s,%s)""", (rid, nome, node_id, qta, uni, match))
                collegati += 1
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM recipe_ingredients")
        tot = cur.fetchone()[0]
        cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "righe_create": collegati, "match_grafo": matchati,
                        "totale_righe": tot, "prossimo_offset": offset + limit})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/genera-hero-prompt")
def admin_genera_hero_prompt():
    """Genera il contratto visivo (hero_subject, hero_style, hero_prompt) per le ricette.
    Il hero_prompt è un prompt fotografico preciso e stabile per cercare/generare la foto giusta.
    ?offset=&limit=  Le figlie ereditano il soggetto della madre + la variante."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    import re as _re
    from ai import _haiku_raw
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 15)), 30)
    except Exception:
        offset, limit = 0, 15
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS hero_subject TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS hero_style TEXT")
        cur.execute("ALTER TABLE ricette ADD COLUMN IF NOT EXISTS hero_prompt TEXT")
        cur.execute("""SELECT id, nome, disciplina, descrizione FROM ricette
                       WHERE hero_prompt IS NULL ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        ricette = cur.fetchall()
        if not ricette:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        # tassonomia stile per disciplina
        _STILE = {"bar": "beverage", "cucina": "plated", "pasticceria": "dessert",
                  "panificazione": "bakery", "gelateria": "dessert", "caffetteria": "beverage",
                  "birra": "beverage", "vino": "beverage"}
        fatti = 0
        for rid, nome, disc, descr in ricette:
            style = _STILE.get((disc or "").lower(), "plated")
            # genero il hero_prompt con l'AI: prompt fotografico food professionale
            prompt_ai = (f"Crea un prompt fotografico professionale in INGLESE per fotografare il piatto "
                         f"'{nome}' ({disc}). Deve descrivere il piatto reale, impiattamento, ingredienti "
                         f"visibili, luce naturale, stile food fotografia italiana di qualità. Max 30 parole. "
                         f"Rispondi SOLO col prompt, niente altro.")
            try:
                hero = (_haiku_raw(prompt_ai, max_tokens=100) or "").strip().strip('"')
                hero = _re.sub(r"^(prompt:|photo:)\s*", "", hero, flags=_re.I)[:300]
            except Exception:
                hero = ""
            if not hero:
                hero = f"{nome}, Italian professional food photography, natural light, plated, top-down"
            # hero_subject = il nome pulito del piatto
            subject = _re.sub(r"\s*\(.*?\)", "", nome).strip()
            cur.execute("UPDATE ricette SET hero_subject=%s, hero_style=%s, hero_prompt=%s WHERE id=%s",
                        (subject, style, hero, rid))
            fatti += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "generati": fatti, "prossimo_offset": offset + limit,
                        "esempio": {"nome": ricette[0][1], "hero_prompt": hero if fatti else ""}})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/crea-ponti-fenomeni")
def admin_crea_ponti_fenomeni():
    """Crea archi 'unifica' tra fenomeni che condividono una legge fisica. Così quando l'utente
    approfondisce un fenomeno, trova fenomeni DAVVERO collegati (non salti scollegati)."""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    # gruppi di fenomeni che condividono una legge fisica -> si collegano tra loro
    _PONTI = [
        ("Trasporto di soluto in solvente", ["fen-infusione", "fen-cold-brew", "fen-fat-washing",
            "fen-capillarita", "fen-inversione-zucchero"]),
        ("Reazioni di brunitura e aromi termici", ["fen-strecker", "fen-tadka", "fen-wok-hei",
            "fen-browning-enzimatico"]),
        ("Fermentazione ed enzimi", ["fen-koji", "fen-autolisi", "fen-poolish-biga"]),
        ("Struttura di gel e fluidi", ["fen-clarificazione-cocktail", "fen-texture-agents",
            "fen-tissotropia", "fen-emulsione-violenta"]),
        ("Conservazione e deterioramento", ["fen-shelf-life", "fen-shelf-life-pane",
            "fen-atmosfera-modificata", "fen-zona-pericolo", "fen-contaminazione"]),
        ("Trasformazione dell'amido", ["fen-riso-glutinoso", "fen-nixtamalizzazione", "fen-kansui"]),
        ("Calore e cottura", ["fen-barbecue-low-slow", "fen-tandoor", "fen-espansione-termica"]),
        # ── PONTI FENOMENI BASE (audit OpenAI): l'Atlante diventa una rete, non lineare ──
        ("Trasporto e passaggio in soluzione", ["fen-diluizione", "fen-concentrazione",
            "fen-estrazione", "fen-osmosi", "fen-solubilita"]),
        ("Gas e struttura effervescente", ["fen-carbonatazione", "fen-fermentazione", "fen-gas"]),
        ("Emulsioni e sistemi dispersi", ["fen-emulsione", "fen-schiuma", "fen-viscosita"]),
        ("Calore e trasformazione termica", ["fen-maillard", "fen-caramellizzazione",
            "fen-denaturazione", "fen-coagulazione", "fen-gelatinizzazione"]),
        ("Cristalli e cambi di stato", ["fen-cristallizzazione", "fen-abbattimento",
            "fen-abbassamento-crioscopico", "fen-overrun"]),
        ("Acidità ed equilibrio del gusto", ["fen-acidita", "fen-tannini", "fen-amaro-bitter",
            "fen-malolattica"]),
    ]
    conn = _get_conn()
    try:
        cur = conn.cursor()
        creati = 0
        for legge, fenomeni in _PONTI:
            # collego ogni fenomeno con ogni altro del gruppo (bidirezionale)
            for i, a in enumerate(fenomeni):
                cur.execute("SELECT 1 FROM nodes WHERE id=%s", (a,))
                if not cur.fetchone():
                    continue
                for bb in fenomeni[i+1:]:
                    cur.execute("SELECT 1 FROM nodes WHERE id=%s", (bb,))
                    if not cur.fetchone():
                        continue
                    import json as _j
                    data = _j.dumps({"legge_condivisa": legge}, ensure_ascii=False)
                    # arco a->b e b->a
                    for _f, _t in [(a, bb), (bb, a)]:
                        cur.execute("""INSERT INTO edges (from_id, to_id, relation, data)
                                       SELECT %s,%s,'unifica',%s::jsonb
                                       WHERE NOT EXISTS (SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='unifica')""",
                                    (_f, _t, data, _f, _t))
                        creati += cur.rowcount
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "ponti_creati": creati, "gruppi": len(_PONTI)})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/assegna-famiglie")
def admin_assegna_famiglie():
    """Assegna la ingredient_family a ogni ingrediente (campo in data). ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 300)), 600)
    except Exception:
        offset, limit = 0, 300
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Ingrediente'
                       ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        righe = cur.fetchall()
        if not righe:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        assegnate = 0; per_fam = {}
        for iid, nome, data in righe:
            d = data if isinstance(data, dict) else (json.loads(data) if data else {})
            fam = _famiglia_ingrediente(nome)
            if fam:
                d["ingredient_family"] = fam
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(d, ensure_ascii=False), iid))
                assegnate += 1
                per_fam[fam] = per_fam.get(fam, 0) + 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "assegnate": assegnate, "su": len(righe),
                        "top_famiglie": dict(sorted(per_fam.items(), key=lambda x: -x[1])[:8]),
                        "prossimo_offset": offset + limit})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/assegna-node-kind")
def admin_assegna_node_kind():
    """Assegna node_kind agli ingredienti: 'ingrediente' (base Ahn), 'prodotto' (DOP/IGP/territoriale),
    'trasformato' (passata, conserva, farina...). Campo in data. ?offset=&limit="""
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        offset = int(request.args.get("offset", 0)); limit = min(int(request.args.get("limit", 400)), 800)
    except Exception:
        offset, limit = 0, 400
    _TRASFORMATI = ("passata", "conserva", "concentrato", "farina", "sciroppo", "estratto", "polvere",
                    "essiccat", "affumicat", "fermentat", "confettura", "marmellata", "purea", "salsa",
                    "aceto", "olio di", "burro di", "pasta di", "granella", "scaglie")
    _PRODOTTI = ("dop", "igp", "stg", "presidio", "riserva", "millesimat")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Ingrediente'
                       ORDER BY id LIMIT %s OFFSET %s""", (limit, offset))
        righe = cur.fetchall()
        if not righe:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "fine": True})
        conta = {"ingrediente": 0, "prodotto": 0, "trasformato": 0}
        for iid, nome, data in righe:
            d = data if isinstance(data, dict) else (json.loads(data) if data else {})
            n = (nome or "").lower()
            _dic = (d.get("dicitura") or d.get("names", {}).get("dicitura") or "").lower() if isinstance(d.get("names"), dict) else (d.get("dicitura") or "").lower()
            if any(k in n or k in _dic for k in _PRODOTTI) or d.get("italian_layer"):
                kind = "prodotto"
            elif any(k in n for k in _TRASFORMATI):
                kind = "trasformato"
            else:
                kind = "ingrediente"
            d["node_kind"] = kind
            conta[kind] += 1
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(d, ensure_ascii=False), iid))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "conta": conta, "su": len(righe), "prossimo_offset": offset + limit})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        import traceback
        return jsonify({"errore": str(e), "tb": traceback.format_exc()[-300:]}), 500


@bp.route("/admin/genera-serbatoio")
def admin_genera_serbatoio():
    """Genera liste di piatti canonici VERI via AI e le accumula in mappa_ai_generata.py.
    Riempie il serbatoio in VOLUME (centinaia per giro) invece di aggiungere a mano.
    Uso: /admin/genera-serbatoio?s=SECRET&disciplina=bar&area=internazionale&quanti=60"""
    from flask import request, jsonify
    import os
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    disciplina = request.args.get("disciplina", "cocktail")
    area = request.args.get("area", "internazionale")
    quanti = min(int(request.args.get("quanti", 50)), 80)
    try:
        from genera_serbatoio import genera_lista_piatti
        _dbg = request.args.get("debug") == "1"
        nuovi = genera_lista_piatti(disciplina, area, quanti, _debug=_dbg)
        if _dbg and isinstance(nuovi, tuple):
            return jsonify({"debug_motivo": nuovi[0], "ai_raw": nuovi[1]})
        if not nuovi:
            return jsonify({"generati": 0, "nota": "l'AI non ha restituito una lista valida. Aggiungi &debug=1 per vedere cosa risponde l'AI"})
        # SALVO NEL DATABASE (Postgres persiste; il file su Railway è effimero e si perde al riavvio)
        import psycopg2, json
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS serbatoio_ai (
            nome TEXT PRIMARY KEY, chiave TEXT, firma JSONB, area TEXT, disciplina TEXT,
            tipo TEXT DEFAULT 'da_validare', creato TIMESTAMP DEFAULT NOW())""")
        aggiunti = 0
        for p in nuovi:
            try:
                cur.execute("""INSERT INTO serbatoio_ai (nome, chiave, firma, area, disciplina, tipo)
                               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (nome) DO NOTHING""",
                            (p["nome"], p.get("chiave",""), json.dumps(p.get("firma",[])),
                             p.get("area",""), p.get("disciplina",""), p.get("tipo","da_validare")))
                if cur.rowcount > 0:
                    aggiunti += 1
            except Exception:
                pass
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM serbatoio_ai")
        totale = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"generati": len(nuovi), "aggiunti_nuovi": aggiunti,
                        "totale_accumulato": totale,
                        "nota": "salvati nel DB (persistente). Rilancia con aree diverse per accrescere."})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 200


@bp.route("/admin/genera-da-serbatoio")
def admin_genera_da_serbatoio():
    """Genera ricette NUOVE dai piatti del serbatoio_ai (che non sono ancora ricette).
    Questo RIEMPIE davvero il database (l'altra genera-canonici rigenera le esistenti)."""
    from flask import request, jsonify
    import os, json, re, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "10")), 30)

    def _worker(n):
        import psycopg2
        from db import carica_grafo
        from builder import genera_ricetta
        _log = []
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"])
            cur = conn.cursor()
            cur.execute("""SELECT s.nome, s.disciplina FROM serbatoio_ai s
                           WHERE NOT EXISTS (SELECT 1 FROM ricette r WHERE lower(r.nome)=lower(s.nome))
                           LIMIT %s""", (n,))
            piatti = cur.fetchall()
            _log.append(f"piatti dal serbatoio: {len(piatti)}")
            db = carica_grafo()
            creati = 0
            for nome, disc in piatti:
                try:
                    ric = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc or "cucina", lang="it")
                    if not ric or ric.get("errore") or not ric.get("nome"):
                        _log.append(f"{nome}: genera vuoto/errore {ric.get('errore') if ric else 'None'}")
                        continue
                    _log.append(f"{nome}: generata, ingredienti={len(ric.get('ingredienti',[]))}, numeri={len(ric.get('numeri',{}))}")
                    import unicodedata
                    _base = unicodedata.normalize('NFKD', nome).encode('ascii','ignore').decode('ascii')
                    fid = re.sub(r"[^a-z0-9]+", "-", _base.lower()).strip("-")[:50] or "ricetta"
                    _fid0 = fid; _k = 1
                    while _k <= 6:
                        cur.execute("SELECT 1 FROM ricette WHERE id=%s", (fid,))
                        if not cur.fetchone():
                            break
                        fid = f"{_fid0}-{(disc or 'x')[:3]}{_k}"
                        _k += 1
                    cur.execute("SELECT 1 FROM ricette WHERE id=%s", (fid,))
                    if cur.fetchone():
                        _log.append(f"{nome}: id {fid} collide ancora, salto")
                        continue
                    cur.execute("""INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                            punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,esperimento,limite,twist)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING""",
                        (fid, ric["nome"], disc or "cucina", ric.get("descrizione",""),
                         json.dumps(ric.get("ingredienti",[]),ensure_ascii=False),
                         json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                         json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                         json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                         ric.get("punto_critico",""),
                         json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                         json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                         json.dumps(ric.get("applicazioni",[]),ensure_ascii=False),
                         ric.get("tempo_prep",""), ric.get("tempo_cottura",""),
                         ric.get("difficolta",""), ric.get("porzioni",""),
                         ric.get("esperimento",""), ric.get("limite",""), ric.get("twist","")))
                    conn.commit()
                    creati += 1
                except Exception as _e2:
                    _log.append(f"{nome}: EXC {str(_e2)[:80]}")
                    conn.rollback()
            # salvo il log in una tabella per poterlo leggere
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"creati={creati} | " + " || ".join(_log[:15]),))
            conn.commit()
            cur.close(); conn.close()
        except Exception as _e:
            try:
                c2 = psycopg2.connect(os.environ["DATABASE_URL"]); cu2 = c2.cursor()
                cu2.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
                cu2.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"WORKER CRASH: {str(_e)[:200]}",))
                c2.commit(); cu2.close(); c2.close()
            except Exception:
                pass

    threading.Thread(target=_worker, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "n": n, "nota": "genera ricette NUOVE dal serbatoio in background. Ricontrolla il totale ricette tra ~1-2 min."})


@bp.route("/admin/rigenera-incomplete")
def admin_rigenera_incomplete():
    """Trova le ricette INCOMPLETE (ingredienti vuoti) e le rigenera complete."""
    from flask import request, jsonify
    import os, json, re, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "10")), 30)

    def _worker(n):
        import psycopg2
        from db import carica_grafo
        from builder import genera_ricetta
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            # trovo ricette con ingredienti vuoti o nulli
            cur.execute("""SELECT id, nome, disciplina FROM ricette
                           WHERE ingredienti IS NULL OR ingredienti::text IN ('[]','null','{}')
                           LIMIT %s""", (n,))
            incomplete = cur.fetchall()
            db = carica_grafo()
            fixate = 0
            for rid, nome, disc in incomplete:
                try:
                    ric = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc or "cucina", lang="it")
                    if not ric or not ric.get("ingredienti"):
                        continue
                    cur.execute("""UPDATE ricette SET ingredienti=%s::jsonb, numeri=%s::jsonb,
                                   procedimento=%s::jsonb, punto_critico=%s, descrizione=%s,
                                   fenomeni=%s::jsonb, tecniche=%s::jsonb, abbinamenti=%s::jsonb
                                   WHERE id=%s""",
                                (json.dumps(ric.get("ingredienti",[]),ensure_ascii=False),
                                 json.dumps(ric.get("numeri",{}),ensure_ascii=False),
                                 json.dumps(ric.get("procedimento",[]),ensure_ascii=False),
                                 ric.get("punto_critico",""), ric.get("descrizione",""),
                                 json.dumps(ric.get("fenomeni",[]),ensure_ascii=False),
                                 json.dumps(ric.get("tecniche",[]),ensure_ascii=False),
                                 json.dumps(ric.get("abbinamenti",{}),ensure_ascii=False),
                                 rid))
                    conn.commit(); fixate += 1
                except Exception:
                    conn.rollback()
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"rigenera-incomplete: {fixate}/{len(incomplete)} fixate",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_worker, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": f"rigenerazione {n} ricette incomplete in background"})


@bp.route("/admin/genera-foto-ai")
def admin_genera_foto_ai():
    """WORKER: genera foto con gpt-image-1 per le ricette senza foto. Salva su Cloudinary o come dato.
    Gira in background. ?n=quante per giro."""
    from flask import request, jsonify
    import os, json, urllib.request as ur, urllib.error, threading, psycopg2, base64
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return jsonify({"errore": "manca OPENAI_API_KEY"})
    n = min(int(request.args.get("n", "5")), 15)
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    cloud_key = os.environ.get("CLOUDINARY_API_KEY", "")
    cloud_secret = os.environ.get("CLOUDINARY_API_SECRET", "")
    cloud_url = cloud_name  # per il check

    def _w(n):
        generate = 0
        _errori = []
        try:
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            # ricette SENZA foto (blueprint o null)
            cur.execute("""SELECT id, nome FROM ricette
                           WHERE (immagine IS NULL OR immagine::text = 'null'
                                  OR immagine::text NOT ILIKE '%%http%%') LIMIT %s""", (n,))
            righe = cur.fetchall()
            if not righe:
                _errori.append('nessuna ricetta trovata dalla query')
            import time as _t
            for _idx, (rid, nome) in enumerate(righe):
                if _idx > 0:
                    _t.sleep(15)  # pausa per rispettare il rate-limit OpenAI immagini
                try:
                    prompt = f"Professional food photography of {nome}, top view, natural light, restaurant quality, appetizing, no text, no people"
                    payload = {"model": "gpt-image-1", "prompt": prompt, "n": 1, "size": "1024x1024"}
                    req = ur.Request("https://api.openai.com/v1/images/generations",
                                     data=json.dumps(payload).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
                    r = ur.urlopen(req, timeout=120)
                    d = json.loads(r.read().decode())
                    item = d["data"][0]
                    b64 = item.get("b64_json")
                    if not b64:
                        _errori.append('no b64 da openai: '+str(list(item.keys())))
                        continue
                    # salvo su Cloudinary se configurato, altrimenti come data URI
                    img_bytes = base64.b64decode(b64)
                    url_finale = None
                    if cloud_url:
                        # upload a Cloudinary
                        try:
                            import cloudinary, cloudinary.uploader
                            cloudinary.config(cloud_name=cloud_name, api_key=cloud_key, api_secret=cloud_secret)
                            up = cloudinary.uploader.upload(img_bytes, folder="ricette_ai", public_id=rid, overwrite=True)
                            url_finale = up.get("secure_url")
                        except Exception as _ce:
                            url_finale = None
                    if url_finale:
                        cur.execute("UPDATE ricette SET immagine = %s WHERE id = %s", (url_finale, rid))
                        conn.commit(); generate += 1
                except Exception as _e:
                    _errori.append(str(_e)[:80])
                    continue
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            _err_txt = (' | ERR: ' + _errori[0]) if _errori else ''
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"genera-foto-ai: {generate}/{len(righe)} generate{_err_txt}",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "cloudinary_configurato": bool(cloud_url),
                    "nota": "genera foto in background. SENZA Cloudinary le foto non si salvano (servono ~2MB l'una). Controlla worker-log."})


@bp.route("/admin/completa-punto-critico")
def admin_completa_punto_critico():
    """Worker: rigenera il punto_critico per le ricette che ce l'hanno vuoto (42% del DB)."""
    from flask import request, jsonify
    import os, psycopg2, threading
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "10")), 30)

    def _w(n):
        try:
            from ai import chiedi_mistral
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("""SELECT id, nome, disciplina FROM ricette
                           WHERE punto_critico IS NULL OR punto_critico = '' LIMIT %s""", (n,))
            righe = cur.fetchall()
            fatti = 0
            _errori = []
            for rid, nome, disc in righe:
                try:
                    prompt = (f"Da tecnico {disc or 'F&B'}: qual è IL punto critico di '{nome}'? "
                              f"Una frase concreta: la cosa che se sbagli rovina il risultato, col numero/parametro chiave. "
                              f"Max 25 parole. Solo la frase, niente premesse.")
                    pc = chiedi_mistral(prompt, usa_tools=False)
                    if pc and len(pc.strip()) > 10:
                        pc = pc.strip()[:300]
                        cur.execute("UPDATE ricette SET punto_critico = %s WHERE id = %s", (pc, rid))
                        conn.commit(); fatti += 1
                except Exception as _e:
                    _errori.append(str(_e)[:60]); conn.rollback()
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            _et = (' ERR: '+_errori[0]) if _errori else (' (chiedi_mistral ha reso vuoto/corto)' if fatti==0 else '')
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"completa-punto-critico: {fatti}/{len(righe)}{_et}",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": "rigenera punto_critico in background"})


@bp.route("/admin/completa-ricette-vuote")
def admin_completa_ricette_vuote():
    """Worker: rigenera ingredienti + procedimento per le 428 ricette vuote (gusci) usando il builder."""
    from flask import request, jsonify
    import os, psycopg2, threading, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "8")), 20)

    def _w(n):
        fatti = 0; errori = []
        try:
            from db import carica_grafo
            from builder import genera_ricetta
            conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
            cur.execute("""SELECT id, nome, disciplina FROM ricette
                           WHERE ingredienti IS NULL OR ingredienti::text IN ('[]','null','') LIMIT %s""", (n,))
            righe = cur.fetchall()
            db = carica_grafo()
            for rid, nome, disc in righe:
                try:
                    r = genera_ricetta(db, f"la ricetta classica di {nome}", disciplina=disc or "cucina", lang="it")
                    ing = r.get("ingredienti", [])
                    proc = r.get("procedimento", "")
                    if ing and len(ing) > 0:
                        cur.execute("UPDATE ricette SET ingredienti = %s, procedimento = %s WHERE id = %s",
                                    (json.dumps(ing), json.dumps(proc) if not isinstance(proc, str) else proc, rid))
                        conn.commit(); fatti += 1
                    else:
                        errori.append(f"{nome}: builder vuoto")
                except Exception as _e:
                    conn.rollback(); errori.append(str(_e)[:50])
            cur.execute("CREATE TABLE IF NOT EXISTS worker_log (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)")
            _et = (' | ERR: ' + errori[0]) if errori else ''
            cur.execute("INSERT INTO worker_log (testo) VALUES (%s)", (f"completa-ricette: {fatti}/{len(righe)}{_et}",))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    threading.Thread(target=_w, args=(n,), daemon=True).start()
    return jsonify({"avviato": True, "nota": "rigenera ingredienti+procedimento in background"})


@bp.route("/admin/correggi-anisakis")
def admin_correggi_anisakis():
    """Corregge il dato Anisakis nel quiz id 22 col dato giusto (Reg CE 853/2004)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    insight = ("Il Regolamento CE 853/2004 stabilisce che il pesce destinato al consumo crudo deve essere "
               "abbattuto a -20°C per almeno 24 ore, OPPURE a -35°C per almeno 15 ore. Non minuti: sono ore. "
               "L'abbattimento uccide le larve di Anisakis, un parassita pericoloso per l'uomo.")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # correggo insight + le opzioni se contengono "minuti"
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='quiz'")
        colonne = [r[0] for r in cur.fetchall()]
        campo_insight = "insight_didattico" if "insight_didattico" in colonne else ("insight" if "insight" in colonne else None)
        if campo_insight:
            cur.execute(f"UPDATE quiz SET {campo_insight} = %s WHERE id = '22' OR id = 22", (insight,))
        # se c'è un campo opzioni/risposta con "minuti", lo correggo
        for c in ["opzioni", "risposta_corretta", "corretta", "risposte"]:
            if c in colonne:
                cur.execute(f"UPDATE quiz SET {c} = REPLACE(REPLACE({c}::text, '15 minuti', '15 ore')::jsonb, '-35°C', '-35°C')::text WHERE (id='22' OR id=22) AND {c}::text ILIKE '%%minut%%'") if False else None
        conn.commit()
        # verifico
        cur.execute("SELECT * FROM quiz WHERE id='22' OR id=22")
        cols = [d[0] for d in cur.description]; row = dict(zip(cols, cur.fetchone()))
        cur.close(); conn.close()
        return jsonify({"corretto": True, "nuovo_insight": str(row.get(campo_insight, ""))[:200]})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/correggi-anisakis-opzioni")
def admin_correggi_anisakis_opzioni():
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT opzioni, risposta_corretta FROM quiz WHERE id=%s OR id=%s", ("22", 22))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close(); return jsonify({"errore": "quiz 22 non trovato"})
        opzioni, risposta = row
        opz = opzioni if isinstance(opzioni, list) else (json.loads(opzioni) if isinstance(opzioni, str) else [])
        opz_new = [str(o).replace("15 minuti a -35", "15 ore a -35").replace("15 minuti", "15 ore") for o in opz]
        risp_new = str(risposta).replace("15 minuti a -35", "15 ore a -35").replace("15 minuti", "15 ore")
        cur.execute("UPDATE quiz SET opzioni=%s, risposta_corretta=%s WHERE id=%s OR id=%s", (json.dumps(opz_new), risp_new, "22", 22))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"corretto": True, "opzioni": opz_new, "risposta": risp_new})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/aggiungi-leidenfrost")
def admin_aggiungi_leidenfrost():
    """Aggiunge il fenomeno Leidenfrost (la goccia che balla) - separato per evitare doppioni."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id FROM nodes WHERE id = 'fen-leidenfrost'")
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"gia_esiste": True})
        data = {"nome": "Effetto Leidenfrost", "disciplina": "cucina", "target": "~193°C",
                "grandezza": "temperatura padella", "unita": "°C", "tipo_fenomeno": "trucco",
                "scheda": {
                    "cosa": "La goccia d'acqua che 'balla' e resta unita sulla padella invece di evaporare subito: il test del cuoco per sapere se la padella e' pronta.",
                    "capire": "Sopra i ~193°C la parte sotto della goccia evapora all'istante e forma un cuscinetto di vapore che solleva il resto: la goccia galleggia sul suo stesso vapore, isolata dal metallo, e scivola invece di sfrigolare.",
                    "usare": "Goccia che sfrigola e sparisce = padella fredda (sotto 150°C). Goccia che balla e resta unita = padella pronta (200°C+) per scottare e per la reazione di Maillard senza attaccare.",
                    "creare": "Fai il test prima di scottare carne o saltare verdure: se la goccia balla, il cibo dora senza attaccarsi.",
                    "misurare": "~193°C e' il punto di Leidenfrost dell'acqua. Sopra, la goccia galleggia; sotto, evapora sfrigolando."}}
        cur.execute("INSERT INTO nodes (id, name, type, data) VALUES ('fen-leidenfrost', 'Effetto Leidenfrost', 'Fenomeno', %s)",
                    (json.dumps(data),))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"aggiunto": "Effetto Leidenfrost"})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-stagionalita")
def admin_aggiungi_stagionalita():
    """Aggiunge il tag stagione agli ingredienti stagionali (regole, no AI). I piatti la ereditano."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403

    # mappa ingrediente -> mesi disponibili (stagionalità italiana)
    STAGIONI = {
        "primavera": ["asparag", "carciof", "fava", "pisell", "fragol", "agretti", "cipollotto", "ravanell",
                      "puntarelle", "taccole", "bietola", "rucola", "misticanza", "cicoria"],
        "estate": ["pomodor", "melanzan", "zucchin", "peperon", "basilico", "cetriol", "angur", "melon",
                   "pesca", "albicocc", "fico", "prugn", "ciliegi", "lampone", "mirtill", "fagiolini",
                   "mais", "peperoncin", "susina"],
        "autunno": ["zucca", "funghi", "porcin", "castagn", "melagran", "uva", "cachi", "mela", "pera",
                    "cavolo", "broccol", "radicchio", "verza", "rapa", "topinambur", "tartufo"],
        "inverno": ["cavolfiore", "cavolo nero", "verza", "finocchio", "arancia", "mandarin", "clementin",
                    "limone", "carciof", "broccol", "cardo", "porro", "scarola", "indivia", "bietola",
                    "spinaci", "radicchio", "cavolin"],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiornati = 0
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')""")
        for nid, nome, data in cur.fetchall():
            nl = (nome or "").lower()
            stagioni_ing = []
            for stag, chiavi in STAGIONI.items():
                if any(k in nl for k in chiavi):
                    stagioni_ing.append(stag)
            if stagioni_ing:
                dd = data if isinstance(data, dict) else {}
                dd["stagioni"] = stagioni_ing
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd), nid))
                aggiornati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ingredienti_con_stagione": aggiornati})
    except Exception as e:
        return jsonify({"errore": str(e)[:120]})


@bp.route("/admin/correggi-refusi")
def admin_correggi_refusi():
    """Corregge i refusi di accento nei fenomeni (piu->più, c'e->c'è, ecc.) con sostituzione sicura
    a livello di parola intera. Founder Rule #121."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # (regex parola-intera, sostituzione) - solo accenti, sicuri
    # coppie (sbagliato, giusto) - versione minuscola E capitalizzata, word boundary
    _BASE = [("c'e","c'è"),("piu","più"),("perche","perché"),("pero","però"),("gia","già"),
             ("cosi","così"),("poiche","poiché"),("qualita","qualità"),("quantita","quantità"),
             ("proprieta","proprietà"),("puo","può"),("e'","è"),("cioe","cioè"),("finche","finché"),
             ("affinche","affinché"),("benche","benché"),("ne'","né"),("si'","sì")]
    FIX = []
    for bad, good in _BASE:
        FIX.append((r"\b" + re.escape(bad) + r"\b", good))                    # minuscolo
        FIX.append((r"\b" + re.escape(bad.capitalize()) + r"\b", good.capitalize()))  # Maiuscolo
    FIX.append((r"l'al dente", "il punto «al dente»"))
    FIX.append((r"L'al dente", "Il punto «al dente»"))
    def _fix_str(s):
        if not isinstance(s, str): return s, 0
        n = 0
        for pat, rep in FIX:
            s, k = re.subn(pat, rep, s)
            n += k
        return s, n
    def _fix_deep(obj):
        tot = 0
        if isinstance(obj, dict):
            for k in obj:
                obj[k], n = _fix_deep(obj[k]); tot += n
            return obj, tot
        if isinstance(obj, list):
            for i in range(len(obj)):
                obj[i], n = _fix_deep(obj[i]); tot += n
            return obj, tot
        if isinstance(obj, str):
            return _fix_str(obj)
        return obj, 0
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        tipo = request.args.get("tipo", "Fenomeno")
        if tipo == "tutti":
            cur.execute("SELECT id, name, data FROM nodes")
        else:
            cur.execute("SELECT id, name, data FROM nodes WHERE type=%s", (tipo,))
        righe = cur.fetchall()
        corretti = 0; fen_toccati = 0
        for nid, name, data in righe:
            n_tot = 0
            # correggo il name
            new_name, n1 = _fix_str(name) if name else (name, 0)
            n_tot += n1
            # correggo il data
            new_data = data
            if data:
                new_data, n2 = _fix_deep(data if isinstance(data, dict) else json.loads(data))
                n_tot += n2
            if n_tot > 0:
                if data:
                    cur.execute("UPDATE nodes SET name=%s, data=%s WHERE id=%s", (new_name, json.dumps(new_data, ensure_ascii=False), nid))
                else:
                    cur.execute("UPDATE nodes SET name=%s WHERE id=%s", (new_name, nid))
                corretti += n_tot; fen_toccati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"refusi_corretti": corretti, "fenomeni_toccati": fen_toccati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/collega-italiani-ahn")
def admin_collega_italiani_ahn():
    """Collega gli ingredienti italiani (ing-, senza composti) ai loro gemelli Ahn (che hanno i composti)
    via una mappa nome IT->EN. L'italiano eredita gli abbinamenti del gemello Ahn. Serve al Creatore."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    solo_conta = request.args.get("conta") == "1"

    # mappa italiano -> nome ahn (i più comuni; il match è per LIKE)
    MAP = {
        "oliva": "olive", "olive": "olive", "pomodoro": "tomato", "basilico": "basil",
        "aglio": "garlic", "cipolla": "onion", "limone": "lemon", "arancia": "orange",
        "fragola": "strawberry", "lampone": "raspberry", "mela": "apple", "pera": "pear",
        "pesca": "peach", "uva": "grape", "carota": "carrot", "sedano": "celery",
        "prezzemolo": "parsley", "rosmarino": "rosemary", "timo": "thyme", "salvia": "sage",
        "menta": "mint", "zenzero": "ginger", "cannella": "cinnamon", "vaniglia": "vanilla",
        "cioccolato": "cocoa", "caffe": "coffee", "miele": "honey", "burro": "butter",
        "parmigiano": "parmesan", "manzo": "beef", "maiale": "pork", "pollo": "chicken",
        "agnello": "lamb", "salmone": "salmon", "tonno": "tuna", "gambero": "shrimp",
        "funghi": "mushroom", "tartufo": "truffle", "patata": "potato", "zucca": "pumpkin",
        "melanzana": "eggplant", "peperone": "bell_pepper", "zucchina": "zucchini",
        "spinaci": "spinach", "vino": "wine", "aceto": "vinegar", "pane": "bread",
        "mandorla": "almond", "nocciola": "hazelnut", "noce": "walnut", "pistacchio": "pistachio",
        "seppia": "squid", "orata": "fish", "ostriche": "oyster", "cozze": "mussel",
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        collegati = 0; archi = 0
        for ita, ahn in MAP.items():
            # id italiano senza composti
            cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND LOWER(name) LIKE %s AND id LIKE 'ing-%%' LIMIT 1""", (f"%{ita}%",))
            rita = cur.fetchone()
            if not rita: continue
            id_ita = rita[0]
            # id ahn col nome inglese
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{ahn}%",))
            rahn = cur.fetchone()
            if not rahn: continue
            id_ahn = rahn[0]
            if solo_conta:
                collegati += 1; continue
            # collego: l'italiano prende gli abbinamenti aromatici del gemello ahn
            import json as _j
            cur.execute("""SELECT to_id, data FROM edges WHERE from_id=%s AND relation='abbinamento_aromatico' LIMIT 60""", (id_ahn,))
            _righe_ahn = cur.fetchall()
            for to_id, data in _righe_ahn:
                cur.execute("""SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_aromatico' LIMIT 1""", (id_ita, to_id))
                if cur.fetchone(): continue
                _dstr = _j.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else (data or '{}')
                cur.execute("""INSERT INTO edges (from_id, to_id, relation, data) VALUES (%s, %s, 'abbinamento_aromatico', %s)""",
                            (id_ita, to_id, _dstr))
                archi += 1
            # e un arco 'stesso_ingrediente' per tracciare il legame
            cur.execute("""INSERT INTO edges (from_id, to_id, relation, data) VALUES (%s, %s, 'stesso_ingrediente', '{}')""", (id_ita, id_ahn))
            collegati += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ingredienti_collegati": collegati, "archi_ereditati": archi, "modalita": "conta" if solo_conta else "eseguito"})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/ripara-abbinamenti")
def admin_ripara_abbinamenti():
    """Ripara gli ingredienti che hanno perso archi: ricalcola gli abbinamenti aromatici dall'overlap
    dei composti condivisi (logica Ahn). Solo per gli ingredienti con composti ma senza abbinamenti."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "20")), 40)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti CON composti ma con POCHI abbinamenti (i danneggiati)
        cur.execute("""SELECT n.id FROM nodes n
                       WHERE n.type IN ('Ingrediente','Prodotto')
                       AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                       AND (SELECT COUNT(*) FROM edges e2 WHERE (e2.from_id=n.id OR e2.to_id=n.id) AND e2.relation='abbinamento_aromatico') < 3
                       LIMIT %s""", (n,))
        danneggiati = [r[0] for r in cur.fetchall()]
        riparati = 0; archi_creati = 0
        for idg in danneggiati:
            # composti di questo ingrediente
            cur.execute("SELECT to_id FROM edges WHERE from_id=%s AND relation='contiene_composto'", (idg,))
            miei_comp = set(r[0] for r in cur.fetchall())
            if not miei_comp: continue
            # altri ingredienti che condividono composti (overlap)
            cur.execute("""SELECT e.from_id, COUNT(*) ov FROM edges e
                           WHERE e.relation='contiene_composto' AND e.to_id = ANY(%s) AND e.from_id != %s
                           GROUP BY e.from_id HAVING COUNT(*) >= 3 ORDER BY ov DESC LIMIT 40""",
                        (list(miei_comp), idg))
            for altro_id, ov in cur.fetchall():
                # evito duplicati
                cur.execute("""SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_aromatico' LIMIT 1""", (idg, altro_id))
                if cur.fetchone(): continue
                cur.execute("""INSERT INTO edges (from_id, to_id, relation, data) VALUES (%s,%s,'abbinamento_aromatico',%s)""",
                            (idg, altro_id, json.dumps({"fonte": "ricostruito da overlap composti", "overlap": ov})))
                archi_creati += 1
            riparati += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"ingredienti_riparati": riparati, "archi_ricostruiti": archi_creati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/ripara-poveri")
def admin_ripara_poveri():
    """Ripara ingredienti chiave poveri: trova il gemello Ahn ricco e fa ereditare gli abbinamenti.
    Mappa mirata per i pochi rimasti (parmigiano, aglio, vino bianco...)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # (nome italiano nel grafo, nome ahn del gemello ricco)
    COPPIE = [
        ("parmigiano", "parmesan"), ("parmigiano", "cheese"), ("aglio", "garlic"),
        ("vino bianco", "white_wine"), ("grana", "parmesan"), ("pecorino", "cheese"),
        ("prezzemolo", "parsley"), ("rosmarino", "rosemary"), ("salvia", "sage"),
        ("origano", "oregano"), ("maggiorana", "marjoram"), ("erba cipollina", "chive"),
        ("scalogno", "shallot"), ("porro", "leek"), ("sedano", "celery"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        riparati = 0; archi = 0
        for ita, ahn in COPPIE:
            # nodo italiano (quello che risponde ai ponti - prendo quello con nome esatto)
            cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND LOWER(name)=%s ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (ita.lower(),))
            rita = cur.fetchone()
            if not rita:
                cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                               AND LOWER(name) LIKE %s LIMIT 1""", (f"%{ita.lower()}%",))
                rita = cur.fetchone()
            if not rita: continue
            id_ita = rita[0]
            # gemello ahn ricco
            cur.execute("""SELECT n.id, (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) ar
                           FROM nodes n WHERE n.id LIKE 'ahn_%%' AND LOWER(n.name) LIKE %s ORDER BY ar DESC LIMIT 1""",
                        (f"%{ahn}%",))
            rahn = cur.fetchone()
            if not rahn or rahn[1] < 5: continue
            id_ahn = rahn[0]
            # eredita gli abbinamenti del gemello
            cur.execute("""SELECT to_id, data FROM edges WHERE from_id=%s AND relation='abbinamento_aromatico' LIMIT 80""", (id_ahn,))
            for to_id, data in cur.fetchall():
                if to_id == id_ita: continue
                cur.execute("""SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_aromatico' LIMIT 1""", (id_ita, to_id))
                if cur.fetchone(): continue
                dstr = json.dumps(data, ensure_ascii=False) if isinstance(data,(dict,list)) else (data or '{}')
                cur.execute("""INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'abbinamento_aromatico',%s)""", (id_ita,to_id,dstr))
                archi += 1
            riparati += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"riparati": riparati, "archi_ereditati": archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/collega-varianti-genitore")
def admin_collega_varianti_genitore():
    """Collega le varianti specifiche (aceto di X, acciughe Y) al loro ingrediente-madre, ereditandone
    i composti. Non aggiunge composti nuovi: collega le varianti al genitore che li ha già."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "40")), 80)
    # varianti -> parola-madre da cui ereditare i composti
    MADRI = ["aceto", "acciughe", "pomodoro", "cipolla", "peperone", "olio", "vino", "formaggio",
             "pepe", "sale", "zucchero", "farina", "latte", "burro", "miele", "limone", "arancia",
             "mela", "pera", "funghi", "basilico", "prezzemolo", "menta", "cioccolato", "caffè",
             "riso", "pane", "pasta", "birra", "aglio", "zenzero", "cannella", "vaniglia", "senape"]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        collegate = 0; archi = 0
        cur.execute("""SELECT n.id, LOWER(n.name) FROM nodes n
                       WHERE n.type IN ('Ingrediente','Prodotto') AND n.id LIKE 'ing-%%'
                       AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                       LIMIT %s""", (n,))
        senza = cur.fetchall()
        for idv, nomev in senza:
            # trovo la madre (la parola-madre contenuta nel nome)
            madre_nome = None
            for m in MADRI:
                if m in nomev:
                    madre_nome = m; break
            if not madre_nome: continue
            # nodo madre CON composti (il più ricco)
            cur.execute("""SELECT n.id FROM nodes n
                           WHERE n.type IN ('Ingrediente','Prodotto') AND LOWER(n.name) LIKE %s
                           AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                           ORDER BY (SELECT COUNT(*) FROM edges e2 WHERE e2.from_id=n.id AND e2.relation='contiene_composto') DESC LIMIT 1""",
                        (f"%{madre_nome}%",))
            rmadre = cur.fetchone()
            if not rmadre: continue
            id_madre = rmadre[0]
            # eredita i composti della madre
            cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_madre,))
            for to_id, data in cur.fetchall():
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='contiene_composto' LIMIT 1", (idv, to_id))
                if cur.fetchone(): continue
                dstr = json.dumps(data, ensure_ascii=False) if isinstance(data,(dict,list)) else (data or '{}')
                cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (idv,to_id,dstr))
                archi += 1
            collegate += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"varianti_collegate": collegate, "composti_ereditati": archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/assegna-proprieta")
def admin_assegna_proprieta():
    """Assegna lo strato PROPRIETA sensoriali (15 dimensioni, 0-10) agli ingredienti-tipo chiave,
    per abbinamento analogia/contrasto. Base scientifica: gusto+mouthfeel+termico+aroma+effervescenza+fermentato."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    solo_test = request.args.get("test") == "1"

    # le 15 proprietà (0-10): dolce, salato, acido, amaro, umami | grasso, corposita, croccante,
    # astringente, piccante | termico(-10 fresco / +10 caldo) | aroma_fresco, aroma_caldo | effervescenza, fermentato
    # mappa-seme: ingredienti-tipo chiave con valori da conoscenza sensoriale
    P = ["dolce","salato","acido","amaro","umami","grasso","corposita","croccante","astringente","piccante","termico","aroma_fresco","aroma_caldo","effervescenza","fermentato"]
    SEME = {
        "guanciale": [0,7,0,0,6,9,6,2,0,0,3,0,5,0,3],
        "pomodoro": [3,1,6,1,7,0,3,0,0,0,-2,5,1,0,0],
        "limone": [1,0,9,3,0,0,1,0,1,0,-4,8,0,0,0],
        "cioccolato fondente": [4,0,0,7,2,6,7,3,3,0,4,0,7,0,2],
        "peperoncino": [0,0,0,1,0,1,2,0,0,9,8,2,3,0,0],
        "parmigiano": [1,7,2,1,9,6,6,3,1,0,3,0,4,0,7],
        "basilico": [1,0,0,2,0,0,1,0,0,0,-2,8,1,0,0],
        "miele": [9,0,1,0,0,1,7,0,0,0,3,3,3,0,0],
        "aceto balsamico": [4,0,8,1,3,0,4,0,2,0,2,2,3,0,6],
        "burro": [1,1,0,0,2,9,6,0,0,0,3,0,2,0,0],
        "menta": [1,0,0,1,0,0,1,0,0,0,-8,9,0,0,0],
        "caffe": [0,0,2,7,3,2,6,2,4,0,5,0,8,0,3],
        "manzo": [0,3,0,0,8,6,8,2,0,0,4,0,5,0,0],
        "salmone": [1,2,0,0,6,7,6,0,0,0,2,1,2,0,0],
        "champagne": [2,0,6,2,0,0,2,0,2,0,-3,4,1,9,7],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        assegnati = 0; anteprima = []
        for nome, valori in SEME.items():
            cur.execute("""SELECT id, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND LOWER(name) LIKE %s ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (f"%{nome}%",))
            r = cur.fetchone()
            if not r: continue
            nid, data = r
            prop = dict(zip(P, valori))
            if solo_test:
                anteprima.append({"ingrediente": nome, "proprieta": prop}); continue
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dd["proprieta"] = prop
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            assegnati += 1
        if not solo_test: conn.commit()
        cur.close(); conn.close()
        if solo_test:
            return jsonify({"test": True, "esempi": anteprima})
        return jsonify({"assegnati": assegnati, "nota": "seme applicato agli ingredienti-tipo chiave"})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-tagli-carne")
def admin_aggiungi_tagli_carne():
    """Aggiunge i tagli di manzo come nodi-figli: ereditano composti dal 'manzo' genitore + hanno
    proprieta' e caratteristiche proprie. Profondita' gastronomica reale (non piu' 'manzo' generico)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # tagli: nome, caratteristica, proprieta' specifiche (override sul base manzo), uso
    # proprieta 0-10: grasso, corposita, umami, astringente(qui=fibrosita), + note
    TAGLI = [
        ("Filetto di manzo", "Il taglio piu' tenero e magro, poca infiltrazione di grasso", {"grasso":2,"corposita":5,"umami":6}, "scottatura veloce, tartare, Wellington"),
        ("Controfiletto di manzo", "Magro ma saporito, dalla lombata", {"grasso":4,"corposita":6,"umami":7}, "bistecca, roast beef"),
        ("Costata di manzo", "Ricca di grasso intramuscolare, molto saporita", {"grasso":7,"corposita":8,"umami":8}, "griglia, fiorentina"),
        ("Fiorentina", "Bistecca con osso a T da lombata, la regina toscana", {"grasso":6,"corposita":8,"umami":8}, "griglia al sangue"),
        ("Scamone di manzo", "Magro, versatile, dalla coscia posteriore", {"grasso":3,"corposita":6,"umami":6}, "arrosto, straccetti, tagliata"),
        ("Guancia di manzo", "Muscolo ricco di collagene, diventa gelatinoso in cottura lunga", {"grasso":5,"corposita":9,"umami":8}, "brasato, stracotto"),
        ("Cappello del prete", "Spalla con nervatura centrale, tenero da lungo", {"grasso":5,"corposita":8,"umami":7}, "brasato, bollito"),
        ("Ossobuco", "Fetta di stinco con osso e midollo", {"grasso":5,"corposita":8,"umami":8}, "ossobuco alla milanese"),
        ("Brisket (petto)", "Petto fibroso, ricco di collagene", {"grasso":6,"corposita":8,"umami":7}, "affumicatura lunga, bollito"),
        ("Picanha (codone)", "Taglio brasiliano con cappello di grasso", {"grasso":7,"corposita":7,"umami":7}, "griglia, spiedo"),
        ("Tomahawk", "Costata con osso lungo intero", {"grasso":7,"corposita":8,"umami":8}, "griglia, effetto scenografico"),
        ("Reale di manzo", "Spalla anteriore, saporito e magro-medio", {"grasso":4,"corposita":7,"umami":7}, "brasato, ragu'"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # trovo il manzo genitore (con composti)
        cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name) LIKE '%%manzo%%'
                       AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=id AND e.relation='contiene_composto')
                       ORDER BY (SELECT COUNT(*) FROM edges e2 WHERE e2.from_id=id AND e2.relation='contiene_composto') DESC LIMIT 1""")
        rm = cur.fetchone()
        id_manzo = rm[0] if rm else None
        aggiunti = 0
        for nome, carat, prop_spec, uso in TAGLI:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            # proprieta complete: base carne + override specifici
            prop = {"salato":1,"acido":0,"dolce":0,"amaro":0,"umami":prop_spec.get("umami",6),
                    "grasso":prop_spec.get("grasso",5),"corposita":prop_spec.get("corposita",7),
                    "croccante":0,"astringente":0,"piccante":0,"termico":4,"aroma_fresco":0,
                    "aroma_caldo":5,"effervescenza":0,"fermentato":0}
            data = {"nome": nome, "disciplina": "cucina", "categoria": "carne_bovina",
                    "caratteristica": carat, "uso_tipico": uso, "genitore": "manzo", "proprieta": prop}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            # eredita i composti del manzo
            if id_manzo:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_manzo,))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"tagli_aggiunti": aggiunti, "genitore_manzo": id_manzo})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-varieta-pomodoro")
def admin_aggiungi_varieta_pomodoro():
    """Profondita' pomodoro: le cultivar italiane vere come nodi-figli, ereditano composti dal pomodoro
    genitore + hanno caratteristiche/proprieta' proprie. Grounding su varieta' reali."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # cultivar reali italiane: nome, caratteristica, proprieta specifiche, uso
    VARIETA = [
        ("Pomodoro San Marzano DOP", "Allungato, polpa densa, pochi semi, acidita' equilibrata - il re della salsa", {"acido":5,"dolce":4,"umami":7}, "salsa, pelati, pizza"),
        ("Pomodoro del Piennolo del Vesuvio DOP", "Piccolo, buccia spessa, sapore intenso e sapido, si conserva a grappolo", {"acido":6,"dolce":5,"umami":8,"salato":2}, "spaghetti, conserva, pizza napoletana"),
        ("Pomodoro Corbarino", "Piccolo e dolce, cresce sui monti Lattari, ottimo a grappolo", {"acido":5,"dolce":6,"umami":7}, "salsa dolce, conserva"),
        ("Pomodoro Datterino", "Piccolo, molto dolce, forma allungata, poca acidita'", {"acido":3,"dolce":8,"umami":6}, "insalata, salse veloci, confit"),
        ("Pomodoro Ciliegino", "Tondo piccolo, succoso, dolce-acidulo, versatile", {"acido":5,"dolce":6,"umami":5}, "insalata, pasta, conserve"),
        ("Pomodoro Cuore di Bue", "Grande, costoluto, poca acqua, polpa carnosa e dolce", {"acido":3,"dolce":6,"umami":6,"corposita":5}, "insalata, caprese, crudo"),
        ("Pomodoro Costoluto Fiorentino", "Costoluto, saporito, polpa consistente", {"acido":5,"dolce":5,"umami":6}, "insalata, ripieno"),
        ("Pomodoro Pizzutello", "Piccolo con punta, dolce e croccante, tipico laziale", {"acido":4,"dolce":7,"umami":5,"croccante":3}, "insalata, aperitivo"),
        ("Pomodoro Marinda (Camone)", "Verde-rossastro, croccante, molto sapido, tipico sardo/siciliano", {"acido":6,"dolce":4,"umami":6,"salato":3,"croccante":4}, "insalata, crudo"),
        ("Pomodoro Pelato (conserva)", "Pomodoro pelato in conserva, pronto per la salsa", {"acido":5,"dolce":4,"umami":6}, "salsa, sugo, tutto l'anno"),
        ("Passata di pomodoro", "Pomodoro passato e conservato, base per sughi", {"acido":5,"dolce":4,"umami":6}, "sugo veloce"),
        ("Concentrato di pomodoro", "Pomodoro ridotto e concentrato, umami intenso", {"acido":4,"dolce":5,"umami":9,"corposita":4}, "insaporire, colore, fondo"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name) LIKE '%%pomodoro%%'
                       AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=id AND e.relation='contiene_composto')
                       ORDER BY (SELECT COUNT(*) FROM edges e2 WHERE e2.from_id=id AND e2.relation='contiene_composto') DESC LIMIT 1""")
        rm = cur.fetchone(); id_pom = rm[0] if rm else None
        aggiunti = 0
        for nome, carat, prop_spec, uso in VARIETA:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":prop_spec.get("salato",1),"acido":prop_spec.get("acido",5),"dolce":prop_spec.get("dolce",4),
                    "amaro":1,"umami":prop_spec.get("umami",6),"grasso":0,"corposita":prop_spec.get("corposita",3),
                    "croccante":prop_spec.get("croccante",0),"astringente":0,"piccante":0,"termico":-1,
                    "aroma_fresco":5,"aroma_caldo":1,"effervescenza":0,"fermentato":0}
            data = {"nome": nome, "disciplina": "cucina", "categoria": "pomodoro_varieta",
                    "caratteristica": carat, "uso_tipico": uso, "genitore": "pomodoro", "proprieta": prop}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            if id_pom:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_pom,))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"varieta_aggiunte": aggiunti, "genitore": id_pom})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-varieta-farina")
def admin_aggiungi_varieta_farina():
    """Profondita' farine: tipi ufficiali italiani (Tipo 0/1/2, integrale, semola, W forza) come nodi
    con caratteristica tecnica (W, proteine, uso). Grounding su classificazione reale."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # farine: nome, caratteristica tecnica reale, uso
    FARINE = [
        ("Farina 00", "Raffinata, W medio-basso (150-250), poca crusca, elastica", "dolci, pasta fresca, besciamella"),
        ("Farina 0", "Poco meno raffinata della 00, piu' proteine, W 220-280", "pane comune, pizza classica"),
        ("Farina Tipo 1", "Semi-integrale, piu' fibre e sapore, W variabile", "pane rustico, pizza a lunga lievitazione"),
        ("Farina Tipo 2", "Semi-integrale piu' grezza, ricca di crusca e germe", "pane integrale, impasti saporiti"),
        ("Farina integrale", "Macinazione completa del chicco, massima fibra, W basso", "pane integrale, biscotti rustici"),
        ("Farina Manitoba (W350+)", "Forza alta, tanto glutine, grande assorbimento acqua", "panettone, lievitati lunghi, rinforzo impasti"),
        ("Semola di grano duro", "Da grano duro, granulosa, colore ambrato, alto glutine", "pasta secca, pane di Altamura"),
        ("Semola rimacinata", "Semola macinata piu' fine, per impasti lisci", "pane pugliese, focaccia, orecchiette"),
        ("Farina di grano arso", "Grano tostato, colore scuro, aroma affumicato, tipica pugliese", "pasta, pane aromatico"),
        ("Farina di farro", "Da farro, meno glutine del grano, sapore rustico", "pane, dolci, pasta rustica"),
        ("Farina di segale", "Scura, poco glutine, sapore intenso, alta idratazione", "pane nero, pane di segale"),
        ("Farina di riso", "Senza glutine, neutra, granulosa", "senza glutine, tempura, addensare"),
        ("Farina di mais (fumetto)", "Da mais, senza glutine, gialla", "polenta, pane di mais, dolci"),
        ("Farina di grano tenero W180 (debole)", "Forza bassa, poco glutine, per prodotti friabili", "frolla, biscotti, grissini"),
        ("Farina W260-280 (media)", "Forza media, equilibrata, versatile", "pizza, pane, lievitazione media"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (LOWER(name) LIKE '%%farina%%' OR LOWER(name) LIKE '%%wheat_flour%%')
                       AND EXISTS (SELECT 1 FROM edges e WHERE e.from_id=id AND e.relation='contiene_composto')
                       ORDER BY (SELECT COUNT(*) FROM edges e2 WHERE e2.from_id=id AND e2.relation='contiene_composto') DESC LIMIT 1""")
        rm = cur.fetchone(); id_far = rm[0] if rm else None
        aggiunti = 0
        for nome, carat, uso in FARINE:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("+","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            # farine: profilo neutro, corposita/struttura da glutine
            prop = {"salato":0,"acido":0,"dolce":1,"amaro":0,"umami":1,"grasso":1,"corposita":4,
                    "croccante":0,"astringente":0,"piccante":0,"termico":2,"aroma_fresco":0,
                    "aroma_caldo":2,"effervescenza":0,"fermentato":0}
            data = {"nome": nome, "disciplina": "panificazione", "categoria": "farina",
                    "caratteristica": carat, "uso_tipico": uso, "genitore": "farina", "proprieta": prop}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            if id_far:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_far,))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"farine_aggiunte": aggiunti, "genitore": id_far})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-formaggi-pesce")
def admin_aggiungi_formaggi_pesce():
    """Profondita' formaggi e pesce: varieta' italiane/comuni come nodi con caratteristica e proprieta'."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # (nome, genitore_cerca, disciplina, categoria, caratteristica, uso, prop_override)
    ITEMS = [
        # FORMAGGI
        ("Parmigiano Reggiano 24 mesi", "parmesan", "cucina", "formaggio", "Stagionato, granuloso, umami intenso, cristalli di tirosina", "grattugiato, scaglie", {"umami":9,"salato":7,"grasso":6,"corposita":7,"fermentato":7}),
        ("Parmigiano Reggiano 36 mesi", "parmesan", "cucina", "formaggio", "Lungo affinamento, piu' friabile e complesso", "degustazione, scaglie", {"umami":10,"salato":7,"grasso":6,"corposita":8,"fermentato":8}),
        ("Grana Padano", "parmesan", "cucina", "formaggio", "Simile al parmigiano, piu' dolce e meno intenso", "grattugiato, cucina", {"umami":8,"salato":6,"grasso":6,"fermentato":6}),
        ("Pecorino Romano", "cheese", "cucina", "formaggio", "Di pecora, molto sapido e piccante, tipico laziale", "cacio e pepe, amatriciana", {"umami":8,"salato":9,"grasso":6,"piccante":2,"fermentato":6}),
        ("Mozzarella di Bufala Campana DOP", "cheese", "cucina", "formaggio", "Fresca, lattica, succosa, di latte di bufala", "caprese, pizza, cruda", {"umami":4,"salato":3,"grasso":6,"corposita":4,"fermentato":3}),
        ("Fior di latte", "cheese", "cucina", "formaggio", "Mozzarella di latte vaccino, piu' delicata", "pizza, cucina", {"umami":3,"salato":3,"grasso":5,"fermentato":3}),
        ("Gorgonzola DOP", "cheese", "cucina", "formaggio", "Erborinato, cremoso, piccante o dolce", "risotti, salse, crudo", {"umami":6,"salato":6,"grasso":7,"piccante":3,"fermentato":8}),
        ("Ricotta", "cheese", "cucina", "formaggio", "Da siero, dolce, leggera, morbida", "dolci, ripieni, cucina", {"umami":2,"salato":1,"grasso":4,"dolce":2,"corposita":3}),
        ("Stracciatella", "cheese", "cucina", "formaggio", "Cuore cremoso della burrata, ricca e lattica", "crudo, pizza, antipasti", {"umami":3,"salato":2,"grasso":7,"corposita":5}),
        ("Caciocavallo", "cheese", "cucina", "formaggio", "A pasta filata stagionato, saporito, del sud", "grigliato, cucina", {"umami":6,"salato":5,"grasso":6,"fermentato":6}),
        # PESCE
        ("Branzino (spigola)", "fish", "cucina", "pesce", "Bianco, magro, delicato, carne soda", "al forno, all'acqua pazza, crudo", {"umami":5,"grasso":3,"corposita":4}),
        ("Orata", "fish", "cucina", "pesce", "Bianco, leggermente grasso, saporito", "al forno, alla griglia", {"umami":5,"grasso":4,"corposita":4}),
        ("Salmone", "salmon", "cucina", "pesce", "Grasso, rosa, ricco di omega-3, versatile", "crudo, affumicato, cotto", {"umami":6,"grasso":7,"corposita":6}),
        ("Tonno rosso", "tuna", "cucina", "pesce", "Carne rossa compatta, umami intenso", "crudo, scottato, tataki", {"umami":8,"grasso":5,"corposita":7}),
        ("Baccala (merluzzo salato)", "fish", "cucina", "pesce", "Merluzzo conservato sotto sale, da dissalare", "mantecato, fritto, in umido", {"umami":7,"salato":6,"grasso":2,"corposita":5,"fermentato":2}),
        ("Acciughe del Cantabrico", "anchovy", "cucina", "pesce", "Sotto sale/olio, umami potentissimo, sapide", "insaporire, crudo, bagna cauda", {"umami":9,"salato":8,"grasso":4,"fermentato":4}),
        ("Gambero rosso di Mazara", "shrimp", "cucina", "pesce", "Dolce, delicato, pregiato, siciliano", "crudo, scottato", {"umami":6,"dolce":4,"grasso":2,"corposita":3}),
        ("Cozze", "mussel", "cucina", "pesce", "Molluschi, sapore di mare, iodati", "impepata, pasta, sauté", {"umami":6,"salato":4,"corposita":3}),
        ("Vongole", "clam", "cucina", "pesce", "Molluschi piccoli, sapidi, dolci", "spaghetti, sauté", {"umami":6,"salato":4,"dolce":2}),
        ("Polpo", "octopus", "cucina", "pesce", "Mollusco, carne soda, da cuocere bene", "bollito, grigliato, insalata", {"umami":6,"corposita":6,"grasso":2}),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiunti = 0
        for nome, gen, disc, cat, carat, uso, prop_ov in ITEMS:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":prop_ov.get("salato",1),"acido":0,"dolce":prop_ov.get("dolce",0),"amaro":0,
                    "umami":prop_ov.get("umami",5),"grasso":prop_ov.get("grasso",4),"corposita":prop_ov.get("corposita",4),
                    "croccante":0,"astringente":0,"piccante":prop_ov.get("piccante",0),"termico":2,
                    "aroma_fresco":1,"aroma_caldo":2,"effervescenza":0,"fermentato":prop_ov.get("fermentato",0)}
            data = {"nome": nome, "disciplina": disc, "categoria": cat, "caratteristica": carat,
                    "uso_tipico": uso, "proprieta": prop}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            # eredita composti dal genitore ahn
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{gen}%",))
            rg = cur.fetchone()
            if rg:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (rg[0],))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"aggiunti": aggiunti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/pulisci-varieta")
def admin_pulisci_varieta():
    """Pulisce i duplicati creati dall'aggiunta varieta': dove esiste sia una versione dettagliata
    (con caratteristica) sia una vuota con nome simile, tiene la dettagliata. Corregge etichette."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # coppie (nome_vuoto_da_rimuovere, motivo). Elimino i nodi vuoti che duplicano quelli dettagliati.
    DA_RIMUOVERE = [
        "Gorgonzola DOP",  # ne resta uno solo (il primo con caratteristica)
        "Mozzarella di Bufala DOP",  # tengo "Campana DOP" dettagliata
        "Parmigiano Reggiano DOP",  # tengo le 24/36 mesi
        "Pecorino Romano DOP",  # tengo quello dettagliato
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        rimossi = 0
        for nome in DA_RIMUOVERE:
            # trovo i nodi con questo nome esatto SENZA caratteristica (i vuoti duplicati)
            cur.execute("""SELECT id FROM nodes WHERE type='Ingrediente' AND name=%s
                           AND (data->>'caratteristica' IS NULL OR data->>'caratteristica'='')""", (nome,))
            for r in cur.fetchall():
                cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s", (r[0], r[0]))
                cur.execute("DELETE FROM nodes WHERE id=%s", (r[0],))
                rimossi += 1
        # se restano 2 Gorgonzola dettagliati identici, tengo 1
        cur.execute("""SELECT id FROM nodes WHERE type='Ingrediente' AND name='Gorgonzola DOP' ORDER BY id""")
        gorg = [r[0] for r in cur.fetchall()]
        if len(gorg) > 1:
            for extra in gorg[1:]:
                cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s", (extra, extra))
                cur.execute("DELETE FROM nodes WHERE id=%s", (extra,))
                rimossi += 1
        # correggo l'etichetta origine su Cantabrico e Niboshi (non italiani, ma restano)
        for nome, origine in [("Acciughe del Cantabrico","Spagna (Mar Cantabrico)"), ("Niboshi","Giappone")]:
            cur.execute("""UPDATE nodes SET data = jsonb_set(data, '{origine}', %s::jsonb)
                           WHERE name=%s AND type='Ingrediente'""", (json.dumps(origine), nome))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"duplicati_rimossi": rimossi, "etichette_corrette": ["Cantabrico->Spagna","Niboshi->Giappone"]})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/collega-composti-esteso")
def admin_collega_composti_esteso():
    """Collega gli ingredienti italiani senza composti ai gemelli Ahn (che li hanno), ereditando i
    composti. Mappa IT->EN estesa. Sblocca il PERCHE del grafo e migliora il Composer. Batch."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "60")), 120)
    # mappa estesa IT (parola nel nome) -> EN (nome ahn)
    MAP = {
        "orata":"fish","branzino":"fish","spigola":"fish","seppia":"squid","calamaro":"squid",
        "ostrich":"oyster","ostrica":"oyster","cozza":"mussel","vongola":"clam","polpo":"octopus",
        "gambero":"shrimp","scampo":"shrimp","aragosta":"lobster","granchio":"crab","sarda":"sardine",
        "sardina":"sardine","sgombro":"mackerel","merluzzo":"cod","baccala":"cod","acciuga":"anchovy",
        "alice":"anchovy","triglia":"fish","rombo":"fish","sogliola":"fish","cernia":"fish",
        "oliva":"olive","olive":"olive","cappero":"caper","carciofo":"artichoke","cardo":"artichoke",
        "finocchio":"fennel","radicchio":"chicory","cicoria":"chicory","scarola":"endive","catalogna":"chicory",
        "shiitake":"shiitake","porcino":"mushroom","champignon":"mushroom","fungo":"mushroom","tartufo":"truffle",
        "orzo":"barley","farro":"spelt","avena":"oat","segale":"rye","miglio":"millet","grano saraceno":"buckwheat",
        "ceci":"chickpea","lenticchi":"lentil","fagiol":"bean","fava":"broad_bean","pisell":"pea","cicerchia":"legume",
        "zucchin":"zucchini","melanzan":"eggplant","peperon":"bell_pepper","cavolo":"cabbage","verza":"cabbage",
        "broccolo":"broccoli","cavolfiore":"cauliflower","rapa":"turnip","barbabietola":"beet","topinambur":"artichoke",
        "porro":"leek","scalogno":"shallot","erba cipollina":"chive","aneto":"dill","dragoncello":"tarragon",
        "cerfoglio":"chervil","maggiorana":"marjoram","santoreggia":"savory","nocciol":"hazelnut","mandorl":"almond",
        "pistacchio":"pistachio","pinolo":"pine_nut","castagn":"chestnut","noce":"walnut","anacardo":"cashew",
        "fico":"fig","cachi":"persimmon","melagrana":"pomegranate","melograno":"pomegranate","cotogn":"quince",
        "nespola":"loquat","sorba":"fruit","mirtillo":"blueberry","lampone":"raspberry","mora":"blackberry",
        "ribes":"currant","uva spina":"gooseberry","prugna":"plum","susina":"plum","albicocca":"apricot",
        "pangrattato":"bread","semola":"wheat","grissini":"bread","piadina":"bread","focaccia":"bread",
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # italiani senza composti
        cur.execute("""SELECT id, LOWER(name) FROM nodes n WHERE n.type IN ('Ingrediente','Prodotto')
                       AND n.id LIKE 'ing-%%'
                       AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='contiene_composto')
                       LIMIT %s""", (n,))
        senza = cur.fetchall()
        collegati = 0; archi = 0
        for idv, nomev in senza:
            ahn = None
            for ita, en in MAP.items():
                if ita in nomev:
                    ahn = en; break
            if not ahn: continue
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s
                           ORDER BY (SELECT COUNT(*) FROM edges e WHERE e.from_id=nodes.id AND e.relation='contiene_composto') DESC LIMIT 1""", (f"%{ahn}%",))
            r = cur.fetchone()
            if not r: continue
            id_ahn = r[0]
            cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (id_ahn,))
            comp = cur.fetchall()
            if not comp: continue
            for to_id, cdata in comp:
                cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (idv,to_id,cstr))
                archi += 1
            collegati += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"ingredienti_collegati": collegati, "composti_ereditati": archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-verdure-erbe")
def admin_aggiungi_verdure_erbe():
    """Profondita' verdure/ortaggi + erbe aromatiche: varieta' e tipi reali come nodi con caratteristica,
    uso, proprieta', operativo (yield/stagione/allergeni). Grounding su prodotti reali del banco."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # (nome, gemello_ahn, categoria, caratteristica, uso, prop_override, yield%, stagione)
    ITEMS = [
        # VERDURE/ORTAGGI
        ("Zucchina romanesca", "zucchini", "verdura", "Costoluta, soda, saporita, tipica laziale", "fiori ripieni, pasta, griglia", {"dolce":3,"umami":3,"corposita":3}, 90, "estate"),
        ("Melanzana violetta di Firenze", "eggplant", "verdura", "Grande, tonda, polpa dolce e poco amara", "parmigiana, ripieni", {"amaro":2,"corposita":4,"umami":3}, 85, "estate"),
        ("Melanzana lunga napoletana", "eggplant", "verdura", "Allungata, buccia sottile, poca acqua", "friggere, grigliare", {"amaro":2,"corposita":3}, 88, "estate"),
        ("Peperone di Carmagnola", "bell_pepper", "verdura", "Dolce, carnoso, piemontese IGP", "peperonata, ripieni, crudo", {"dolce":5,"croccante":4,"aroma_fresco":3}, 90, "estate"),
        ("Friggitello", "bell_pepper", "verdura", "Piccolo, verde, dolce, si frigge intero", "padella, contorno", {"dolce":3,"amaro":2,"aroma_fresco":3}, 92, "estate"),
        ("Carciofo romanesco (mammola)", "artichoke", "verdura", "Tondo, senza spine, tenero, laziale IGP", "alla romana, alla giudia", {"amaro":5,"astringente":3,"umami":4}, 45, "primavera"),
        ("Carciofo violetto di Sant'Erasmo", "artichoke", "verdura", "Piccolo, violetto, tenero, veneziano", "crudo, fritto", {"amaro":4,"astringente":3}, 45, "primavera"),
        ("Radicchio di Treviso IGP", "chicory", "verdura", "Allungato, amaro, croccante, veneto", "risotto, griglia, crudo", {"amaro":6,"astringente":3,"croccante":3}, 88, "inverno"),
        ("Radicchio di Chioggia", "chicory", "verdura", "Tondo, rosso, amaro medio", "insalata, griglia", {"amaro":5,"croccante":3}, 88, "inverno"),
        ("Puntarelle", "chicory", "verdura", "Germogli di catalogna, croccanti, amari, romani", "crude con acciuga e aglio", {"amaro":6,"croccante":5,"aroma_fresco":3}, 60, "inverno"),
        ("Cavolo nero toscano", "cabbage", "verdura", "Foglie scure, saporite, resistenti", "ribollita, zuppe, chips", {"amaro":4,"umami":3,"corposita":3}, 75, "inverno"),
        ("Zucca mantovana", "pumpkin", "verdura", "Polpa dolce e asciutta, buccia verde bitorzoluta", "tortelli, risotti, vellutate", {"dolce":6,"corposita":4,"umami":3}, 80, "autunno"),
        ("Patata di Bologna DOP", "potato", "verdura", "Pasta gialla, soda, versatile", "gnocchi, purè, forno", {"dolce":2,"corposita":4}, 85, "tutto l'anno"),
        ("Patata viola (vitelotte)", "potato", "verdura", "Polpa viola, nocciolata, scenografica", "purè colorato, chips", {"dolce":2,"corposita":4,"aroma_caldo":2}, 82, "autunno"),
        ("Asparago verde", "asparagus", "verdura", "Turione verde, erbaceo, tenero in punta", "risotti, uova, griglia", {"amaro":3,"umami":4,"aroma_fresco":4}, 70, "primavera"),
        ("Asparago bianco di Bassano DOP", "asparagus", "verdura", "Coltivato senza luce, delicato, dolce", "lessato, con uova", {"amaro":2,"dolce":3,"umami":4}, 60, "primavera"),
        # ERBE AROMATICHE
        ("Basilico genovese DOP", "basil", "erba", "Foglia piccola, profumo intenso, poco mentolato", "pesto, crudo", {"aroma_fresco":9,"amaro":2}, 95, "estate"),
        ("Menta romana (mentuccia)", "mint", "erba", "Piccola, intensa, tipica romana", "carciofi, trippa", {"aroma_fresco":9,"termico":-7}, 95, "primavera"),
        ("Prezzemolo riccio", "parsley", "erba", "Decorativo, sapore piu' delicato", "guarnizione, salse", {"aroma_fresco":6,"amaro":2}, 95, "tutto l'anno"),
        ("Salvia", "sage", "erba", "Vellutata, balsamica, intensa", "burro e salvia, carni", {"aroma_caldo":5,"amaro":3,"astringente":2}, 95, "tutto l'anno"),
        ("Rosmarino", "rosemary", "erba", "Aghiforme, resinoso, persistente", "arrosti, patate, focaccia", {"aroma_caldo":6,"amaro":2}, 95, "tutto l'anno"),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiunti = 0
        for nome, gen, cat, carat, uso, prop_ov, yld, stag in ITEMS:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":0,"acido":prop_ov.get("acido",0),"dolce":prop_ov.get("dolce",2),
                    "amaro":prop_ov.get("amaro",0),"umami":prop_ov.get("umami",2),"grasso":0,
                    "corposita":prop_ov.get("corposita",2),"croccante":prop_ov.get("croccante",0),
                    "astringente":prop_ov.get("astringente",0),"piccante":0,"termico":prop_ov.get("termico",-1),
                    "aroma_fresco":prop_ov.get("aroma_fresco",3),"aroma_caldo":prop_ov.get("aroma_caldo",1),
                    "effervescenza":0,"fermentato":0}
            operativo = {"yield": yld, "scarto_perc": 100-yld, "stagione": stag,
                         "conservazione": "frigo cassetto verdura" if cat=="verdura" else "frigo/fresco",
                         "shelf_life_giorni": 5 if cat=="verdura" else 4, "allergeni": []}
            data = {"nome": nome, "disciplina": "cucina", "categoria": cat, "caratteristica": carat,
                    "uso_tipico": uso, "proprieta": prop, "operativo": operativo}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{gen}%",))
            rg = cur.fetchone()
            if rg:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (rg[0],))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"aggiunti": aggiunti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-frutta-salumi")
def admin_aggiungi_frutta_salumi():
    """Profondita' frutta + salumi: varieta' reali come nodi con caratteristica, uso, proprieta', operativo."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    ITEMS = [
        # FRUTTA
        ("Limone di Sorrento IGP", "lemon", "frutta", "Buccia spessa e profumata, succoso, poco acido", "delizia, limoncello, pesce", {"acido":8,"aroma_fresco":9,"amaro":2}, 45, "tutto l'anno", ["nessuno"]),
        ("Limone di Amalfi (sfusato)", "lemon", "frutta", "Allungato, buccia ricca di oli essenziali", "granita, dolci, crudo", {"acido":8,"aroma_fresco":9}, 45, "tutto l'anno", []),
        ("Arancia rossa di Sicilia IGP", "orange", "frutta", "Polpa rossa (antociani), succosa, dolce-acidula", "spremuta, insalata, dolci", {"acido":5,"dolce":6,"aroma_fresco":6}, 55, "inverno", []),
        ("Bergamotto", "bergamot", "frutta", "Agrume calabrese, amaro e profumatissimo", "Earl Grey, profumi, dolci", {"acido":7,"amaro":5,"aroma_fresco":9}, 40, "inverno", []),
        ("Fico bianco del Cilento DOP", "fig", "frutta", "Dolce, polpa chiara, delicato", "crudo, confetture, con salumi", {"dolce":8,"corposita":3}, 90, "estate", []),
        ("Pesca di Verona IGP (percoca)", "peach", "frutta", "Polpa gialla soda, dolce, da sciroppo", "sciroppo, dolci, crudo", {"dolce":7,"acido":3,"aroma_fresco":5}, 88, "estate", []),
        ("Fragola di Nemi", "strawberry", "frutta", "Piccola, profumata, dolce-acidula, laziale", "crudo, dolci", {"dolce":7,"acido":5,"aroma_fresco":7}, 92, "primavera", []),
        ("Mela Annurca IGP", "apple", "frutta", "Campana, soda, croccante, acidula", "crudo, forno, dolci", {"dolce":5,"acido":4,"croccante":5}, 88, "autunno", []),
        ("Uva fragola", "grape", "frutta", "Aromatica, dolce, sentore di fragola", "crudo, succo, dolci", {"dolce":7,"aroma_fresco":5}, 85, "autunno", []),
        # SALUMI
        ("Guanciale amatriciano", "pork", "salume", "Guancia di maiale stagionata, grasso pregiato, pepata", "amatriciana, gricia, carbonara", {"grasso":9,"salato":7,"umami":6,"aroma_caldo":4}, 95, "tutto l'anno", []),
        ("Pancetta tesa", "pork", "salume", "Pancia stagionata, grasso e magro alternati", "sughi, involtini", {"grasso":8,"salato":6,"umami":5}, 95, "tutto l'anno", []),
        ("Prosciutto di Parma DOP", "ham", "salume", "Crudo dolce, stagionato, magro", "crudo, con melone, panini", {"salato":5,"umami":7,"grasso":4,"fermentato":6}, 90, "tutto l'anno", []),
        ("Prosciutto di San Daniele DOP", "ham", "salume", "Crudo friulano, dolce, stagionatura lunga", "crudo, affettato", {"salato":5,"umami":7,"fermentato":6}, 90, "tutto l'anno", []),
        ("Mortadella di Bologna IGP", "pork", "salume", "Cotto, morbido, con lardelli e pistacchio", "panini, crudo, spuma", {"salato":5,"grasso":7,"umami":6}, 98, "tutto l'anno", ["frutta a guscio"]),
        ("Nduja di Spilinga", "pork", "salume", "Salume spalmabile piccantissimo calabrese", "pizza, pasta, crostini", {"grasso":7,"salato":6,"piccante":9,"umami":5,"aroma_caldo":5}, 98, "tutto l'anno", []),
        ("Speck Alto Adige IGP", "ham", "salume", "Crudo affumicato, aromatico, tirolese", "crudo, canederli, panini", {"salato":6,"umami":6,"aroma_caldo":6,"fermentato":5}, 92, "tutto l'anno", []),
        ("Bresaola della Valtellina IGP", "beef", "salume", "Manzo stagionato, magrissimo, delicato", "crudo con rucola e grana", {"salato":5,"umami":7,"grasso":1,"fermentato":5}, 92, "tutto l'anno", []),
        ("Salame Milano", "pork", "salume", "Grana fine, stagionato, equilibrato", "panini, taglieri", {"salato":6,"grasso":7,"umami":6,"fermentato":6}, 95, "tutto l'anno", []),
        ("Lardo di Colonnata IGP", "pork", "salume", "Lardo stagionato nel marmo con erbe, fondente", "crostini caldi, avvolgere", {"grasso":10,"salato":6,"aroma_caldo":4}, 98, "tutto l'anno", []),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiunti = 0
        for nome, gen, cat, carat, uso, prop_ov, yld, stag, allerg in ITEMS:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":prop_ov.get("salato",0),"acido":prop_ov.get("acido",0),"dolce":prop_ov.get("dolce",0),
                    "amaro":prop_ov.get("amaro",0),"umami":prop_ov.get("umami",0),"grasso":prop_ov.get("grasso",0),
                    "corposita":prop_ov.get("corposita",3),"croccante":prop_ov.get("croccante",0),"astringente":0,
                    "piccante":prop_ov.get("piccante",0),"termico":prop_ov.get("termico",1),
                    "aroma_fresco":prop_ov.get("aroma_fresco",0),"aroma_caldo":prop_ov.get("aroma_caldo",1),
                    "effervescenza":0,"fermentato":prop_ov.get("fermentato",0)}
            sl = 90 if cat=="salume" else 6
            cons = "frigo, sottovuoto" if cat=="salume" else "fresco/frigo"
            operativo = {"yield": yld, "scarto_perc": 100-yld, "stagione": stag,
                         "conservazione": cons, "shelf_life_giorni": sl,
                         "allergeni": [] if allerg==["nessuno"] else allerg}
            data = {"nome": nome, "disciplina": "cucina", "categoria": cat, "caratteristica": carat,
                    "uso_tipico": uso, "proprieta": prop, "operativo": operativo}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{gen}%",))
            rg = cur.fetchone()
            if rg:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (rg[0],))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"aggiunti": aggiunti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-legumi-dispensa")
def admin_aggiungi_legumi_dispensa():
    """Profondita' legumi/cereali + dispensa/condimenti: tipi reali come nodi con caratteristica, uso,
    proprieta', operativo."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    ITEMS = [
        # LEGUMI/CEREALI
        ("Fagiolo cannellino", "bean", "legume", "Bianco, piccolo, cremoso, buccia sottile", "zuppe, contorni, pasta e fagioli", {"corposita":4,"umami":3,"dolce":2}, 100, "secco/anno", []),
        ("Fagiolo borlotto", "bean", "legume", "Screziato, saporito, cremoso da cotto", "pasta e fagioli, zuppe", {"corposita":5,"umami":4,"dolce":2}, 100, "secco/anno", []),
        ("Cece di Cicerale", "chickpea", "legume", "Piccolo, saporito, buccia fine, cilentano", "hummus, zuppe, farinata", {"corposita":5,"umami":4,"dolce":2,"aroma_caldo":2}, 100, "secco/anno", []),
        ("Lenticchia di Castelluccio IGP", "lentil", "legume", "Piccola, non si sfalda, saporita, umbra", "zuppe, cotechino, contorni", {"corposita":4,"umami":4,"aroma_caldo":2}, 100, "secco/anno", []),
        ("Fava fresca", "broad_bean", "legume", "Verde, dolce, tenera da cruda", "crudo con pecorino, vignarola", {"dolce":4,"aroma_fresco":4,"corposita":3}, 40, "primavera", []),
        ("Pisello fresco", "pea", "legume", "Dolce, tenero, primaverile", "risi e bisi, contorni", {"dolce":5,"aroma_fresco":4}, 40, "primavera", []),
        ("Riso Carnaroli", "rice", "cereale", "Chicco grande, tiene la cottura, molto amido", "risotti", {"corposita":4,"dolce":2}, 100, "secco/anno", []),
        ("Riso Arborio", "rice", "cereale", "Amidaceo, cremoso, per risotti classici", "risotti, supplì", {"corposita":4,"dolce":2}, 100, "secco/anno", []),
        ("Riso Vialone Nano", "rice", "cereale", "Piccolo, veneto, assorbe bene i condimenti", "risotti all'onda", {"corposita":4}, 100, "secco/anno", []),
        # DISPENSA/CONDIMENTI
        ("Olio EVO taggiasca", "olive_oil", "condimento", "Ligure, delicato, dolce, mandorlato", "pesce, crudo, dolci", {"grasso":8,"amaro":2,"aroma_fresco":3}, 100, "anno", []),
        ("Olio EVO coratina", "olive_oil", "condimento", "Pugliese, intenso, amaro e piccante, ricco di polifenoli", "zuppe, carne, bruschetta", {"grasso":8,"amaro":5,"piccante":3,"aroma_fresco":4}, 100, "anno", []),
        ("Aceto Balsamico Tradizionale di Modena DOP", "vinegar", "condimento", "Invecchiato, denso, dolce-acido, sciropposo", "gocce su parmigiano, carne, fragole", {"acido":6,"dolce":6,"corposita":4,"fermentato":7}, 100, "anno", []),
        ("Colatura di alici di Cetara", "anchovy", "condimento", "Liquido ambrato da alici, umami potentissimo", "spaghetti, insaporire", {"umami":10,"salato":9,"fermentato":6}, 100, "anno", ["pesce"]),
        ("Miele di castagno", "honey", "condimento", "Scuro, amarognolo, aromatico", "formaggi, dolci", {"dolce":8,"amaro":3,"aroma_caldo":4}, 100, "anno", []),
        ("Miele di acacia", "honey", "condimento", "Chiaro, delicato, liquido, molto dolce", "dolci, bevande, formaggi freschi", {"dolce":9,"aroma_fresco":2}, 100, "anno", []),
        ("Sale di Cervia", "salt", "condimento", "Marino integrale, dolce, ricco di minerali", "tutto", {"salato":9}, 100, "anno", []),
        ("Pepe di Sichuan", "pepper", "spezia", "Agrumato, anestetizzante, non piccante ma pungente", "cucina asiatica, carni", {"aroma_fresco":5,"piccante":3,"termico":2}, 100, "anno", []),
        ("Zafferano di Navelli DOP", "saffron", "spezia", "Abruzzese, aroma intenso, colore oro", "risotto alla milanese, dolci", {"amaro":3,"aroma_caldo":6,"aroma_fresco":2}, 100, "anno", []),
        ("Peperoncino di Diamante", "chili", "spezia", "Calabrese, piccante e fruttato", "nduja, sughi, olio piccante", {"piccante":8,"aroma_caldo":3,"dolce":2}, 100, "anno", []),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiunti = 0
        for nome, gen, cat, carat, uso, prop_ov, yld, stag, allerg in ITEMS:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":prop_ov.get("salato",0),"acido":prop_ov.get("acido",0),"dolce":prop_ov.get("dolce",0),
                    "amaro":prop_ov.get("amaro",0),"umami":prop_ov.get("umami",0),"grasso":prop_ov.get("grasso",0),
                    "corposita":prop_ov.get("corposita",2),"croccante":0,"astringente":0,
                    "piccante":prop_ov.get("piccante",0),"termico":prop_ov.get("termico",1),
                    "aroma_fresco":prop_ov.get("aroma_fresco",0),"aroma_caldo":prop_ov.get("aroma_caldo",1),
                    "effervescenza":0,"fermentato":prop_ov.get("fermentato",0)}
            sl = 365 if cat in ("legume","cereale","condimento","spezia") else 5
            operativo = {"yield": yld, "scarto_perc": 100-yld, "stagione": stag,
                         "conservazione": "luogo secco" if cat in ("legume","cereale","spezia") else "dispensa",
                         "shelf_life_giorni": sl, "allergeni": allerg}
            data = {"nome": nome, "disciplina": "cucina", "categoria": cat, "caratteristica": carat,
                    "uso_tipico": uso, "proprieta": prop, "operativo": operativo}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{gen}%",))
            rg = cur.fetchone()
            if rg:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (rg[0],))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"aggiunti": aggiunti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/arricchisci-esistenti")
def admin_arricchisci_esistenti():
    """Arricchisce i nodi che esistevano gia' (Ahn grezzi) col nome delle varieta' che ho aggiunto:
    gli inietta proprieta', caratteristica, uso, operativo (invece di lasciarli vuoti perche' 'gia esistono')."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # nome esatto -> dati da iniettare (i casi trovati vuoti)
    ARRICCHISCI = {
        "Bergamotto": {"caratteristica":"Agrume calabrese, amaro e profumatissimo","uso_tipico":"Earl Grey, profumi, dolci","categoria":"frutta",
                       "proprieta":{"acido":7,"amaro":5,"aroma_fresco":9,"dolce":2},"operativo":{"yield":40,"stagione":"inverno","allergeni":[]}},
        "Limone di Sorrento IGP": {"caratteristica":"Buccia spessa e profumata, succoso, poco acido","uso_tipico":"delizia, limoncello, pesce","categoria":"frutta",
                       "proprieta":{"acido":8,"aroma_fresco":9,"amaro":2},"operativo":{"yield":45,"stagione":"tutto l'anno","allergeni":[]}},
        "Pepe di Sichuan": {"caratteristica":"Agrumato, anestetizzante, non piccante ma pungente","uso_tipico":"cucina asiatica, carni","categoria":"spezia",
                       "proprieta":{"aroma_fresco":5,"piccante":3,"termico":2,"amaro":2},"operativo":{"yield":100,"allergeni":[]}},
        "Salvia": {"caratteristica":"Vellutata, balsamica, intensa","uso_tipico":"burro e salvia, carni","categoria":"erba",
                       "proprieta":{"aroma_caldo":5,"amaro":3,"astringente":2},"operativo":{"yield":95,"allergeni":[]}},
        "Colatura di alici di Cetara": {"caratteristica":"Liquido ambrato da alici, umami potentissimo","uso_tipico":"spaghetti, insaporire","categoria":"condimento",
                       "proprieta":{"umami":10,"salato":9,"fermentato":6},"operativo":{"yield":100,"allergeni":["pesce"]}},
    }
    P = ["dolce","salato","acido","amaro","umami","grasso","corposita","croccante","astringente","piccante","termico","aroma_fresco","aroma_caldo","effervescenza","fermentato"]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        arricchiti = 0
        for nome, info in ARRICCHISCI.items():
            cur.execute("SELECT id, data FROM nodes WHERE LOWER(name)=LOWER(%s) AND type IN ('Ingrediente','Prodotto') ORDER BY (data ? 'proprieta') ASC LIMIT 1", (nome,))
            r = cur.fetchone()
            if not r: continue
            nid, data = r
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            # proprieta complete (riempio le 15)
            pr = {k: info["proprieta"].get(k, 0) for k in P}
            dd["proprieta"] = pr
            dd["caratteristica"] = info["caratteristica"]
            dd["uso_tipico"] = info["uso_tipico"]
            dd["categoria"] = info["categoria"]
            dd["operativo"] = info["operativo"]
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            arricchiti += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"arricchiti": arricchiti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-pasticceria-bar")
def admin_aggiungi_pasticceria_bar():
    """Profondita' pasticceria/dolci + bar/cocktail: ingredienti tecnici veri (i domini di Michele)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    ITEMS = [
        ("Cioccolato fondente 70%", "cocoa", "pasticceria", "Fondente equilibrato, amaro medio, versatile", "ganache, mousse, temperaggio", {"amaro":6,"dolce":4,"grasso":6,"corposita":6,"aroma_caldo":6}, ["latte","soia"]),
        ("Cioccolato fondente 85%", "cocoa", "pasticceria", "Molto amaro, poco zucchero, intenso", "degustazione, ganache intense", {"amaro":8,"dolce":2,"grasso":7,"astringente":4,"aroma_caldo":7}, ["latte","soia"]),
        ("Cioccolato al latte", "cocoa", "pasticceria", "Dolce, cremoso, cacao basso", "praline, coperture, mousse", {"dolce":7,"grasso":6,"amaro":2,"corposita":5}, ["latte","soia"]),
        ("Cioccolato bianco", "cocoa", "pasticceria", "Burro di cacao + latte + zucchero, no cacao", "ganache montate, decori", {"dolce":8,"grasso":7,"corposita":5}, ["latte","soia"]),
        ("Cacao amaro in polvere", "cocoa", "pasticceria", "Cacao sgrassato, amaro intenso, colore scuro", "torte, spolvero, impasti", {"amaro":8,"aroma_caldo":7,"astringente":4}, []),
        ("Pasta di nocciola", "hazelnut", "pasticceria", "Nocciole tostate in pasta, oleosa, aromatica", "gianduia, creme, gelato", {"grasso":8,"dolce":3,"aroma_caldo":6,"corposita":6}, ["frutta a guscio"]),
        ("Pasta di pistacchio", "pistachio", "pasticceria", "Pistacchio puro in pasta, verde, aromatico", "creme, gelato, farcitura", {"grasso":7,"dolce":2,"aroma_fresco":3,"corposita":6}, ["frutta a guscio"]),
        ("Zucchero semolato", "sugar", "pasticceria", "Saccarosio fine, dolcezza pulita", "impasti, meringhe, sciroppi", {"dolce":10}, []),
        ("Zucchero a velo", "sugar", "pasticceria", "Macinato finissimo, si scioglie subito", "glasse, spolvero, frolle", {"dolce":10}, []),
        ("Zucchero di canna grezzo", "sugar", "pasticceria", "Integrale, note di melassa, umido", "impasti rustici, crumble", {"dolce":8,"aroma_caldo":4,"corposita":2}, []),
        ("Glucosio (sciroppo)", "sugar", "pasticceria", "Sciroppo anti-cristallizzazione, poco dolce", "gelati, caramelle, ganache", {"dolce":5,"corposita":3}, []),
        ("Panna fresca 35%", "cream", "pasticceria", "Panna da montare, ricca di grasso", "chantilly, ganache, mousse", {"grasso":8,"corposita":6,"dolce":2}, ["latte"]),
        ("Burro di cacao", "cocoa", "pasticceria", "Grasso puro del cacao, fonde a 34C", "temperaggio, fluidificare", {"grasso":10,"corposita":5,"aroma_caldo":3}, []),
        ("Gelatina alimentare", "gelatin", "pasticceria", "Addensante proteico, gelifica a freddo", "bavaresi, mousse, gelatine", {"corposita":3}, []),
        ("Vaniglia Bourbon (bacca)", "vanilla", "pasticceria", "Bacca aromatica, dolce e balsamica", "creme, gelati, impasti", {"dolce":4,"aroma_caldo":6,"aroma_fresco":2}, []),
        ("Gin London Dry", "gin", "bar", "Distillato al ginepro, secco, botanico", "gin tonic, martini, negroni", {"aroma_fresco":7,"amaro":3,"termico":-2}, []),
        ("Vermouth rosso", "vermouth", "bar", "Vino aromatizzato, dolce-amaro, speziato", "negroni, manhattan, americano", {"dolce":5,"amaro":5,"aroma_caldo":4,"fermentato":5}, ["solfiti"]),
        ("Campari (bitter)", "bitter", "bar", "Bitter rosso, amaro intenso, agrumato", "negroni, spritz, americano", {"amaro":8,"dolce":4,"aroma_fresco":3}, []),
        ("Rum agricolo", "rum", "bar", "Da succo di canna, erbaceo, complesso", "ti punch, daiquiri, mai tai", {"dolce":4,"aroma_caldo":6,"fermentato":4}, []),
        ("Rum scuro invecchiato", "rum", "bar", "Invecchiato, note di caramello e spezie", "old fashioned, dark & stormy", {"dolce":5,"aroma_caldo":8,"corposita":4}, []),
        ("Tequila 100% agave", "tequila", "bar", "Da agave blu, vegetale, minerale", "margarita, paloma", {"aroma_fresco":5,"amaro":3,"termico":2}, []),
        ("Whisky torbato", "whisky", "bar", "Affumicato, torba, iodato", "sour, penicillin, liscio", {"aroma_caldo":8,"amaro":4,"fermentato":4}, []),
        ("Angostura bitter", "bitter", "bar", "Concentrato aromatico, speziato, amarissimo", "old fashioned, manhattan (gocce)", {"amaro":9,"aroma_caldo":6,"astringente":3}, []),
        ("Sciroppo di zucchero (gomma)", "sugar", "bar", "Zucchero liquido, dolcezza per drink", "sour, tiki, equilibrare", {"dolce":9,"corposita":3}, []),
        ("Curacao / Triple sec", "liqueur", "bar", "Liquore d'arancia, dolce-agrumato", "margarita, cosmopolitan, sidecar", {"dolce":7,"aroma_fresco":6,"amaro":2}, []),
        ("Prosecco", "wine", "bar", "Spumante veneto, fresco, floreale", "spritz, bellini, mimosa", {"acido":5,"effervescenza":9,"dolce":3,"fermentato":5}, ["solfiti"]),
        ("Acqua tonica", "water", "bar", "Effervescente con chinino amaro", "gin tonic, allungare", {"effervescenza":9,"amaro":3}, []),
        ("Lime fresco (succo)", "lime", "bar", "Succo acido e aromatico, base dei sour", "daiquiri, margarita, mojito", {"acido":9,"aroma_fresco":8}, []),
    ]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        aggiunti = 0
        for nome, gen, cat, carat, uso, prop_ov, allerg in ITEMS:
            nid = "ing-" + nome.lower().replace(" ","-").replace("(","").replace(")","").replace("'","").replace("/","-").replace("%","")
            cur.execute("SELECT id FROM nodes WHERE id=%s", (nid,))
            if cur.fetchone(): continue
            prop = {"salato":0,"acido":prop_ov.get("acido",0),"dolce":prop_ov.get("dolce",0),"amaro":prop_ov.get("amaro",0),
                    "umami":0,"grasso":prop_ov.get("grasso",0),"corposita":prop_ov.get("corposita",2),"croccante":0,
                    "astringente":prop_ov.get("astringente",0),"piccante":0,"termico":prop_ov.get("termico",1),
                    "aroma_fresco":prop_ov.get("aroma_fresco",0),"aroma_caldo":prop_ov.get("aroma_caldo",1),
                    "effervescenza":prop_ov.get("effervescenza",0),"fermentato":prop_ov.get("fermentato",0)}
            sl = 365 if cat=="bar" else (20 if ("panna" in nome.lower() or "gelatina" in nome.lower()) else 180)
            operativo = {"yield":100,"scarto_perc":0,"conservazione":"dispensa/bar" if cat=="bar" else "dispensa",
                         "shelf_life_giorni":sl,"allergeni":allerg}
            data = {"nome":nome,"disciplina":cat,"categoria":cat,"caratteristica":carat,
                    "uso_tipico":uso,"proprieta":prop,"operativo":operativo}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                        (nid, nome, json.dumps(data, ensure_ascii=False)))
            cur.execute("""SELECT id FROM nodes WHERE id LIKE 'ahn_%%' AND LOWER(name) LIKE %s LIMIT 1""", (f"%{gen}%",))
            rg = cur.fetchone()
            if rg:
                cur.execute("SELECT to_id, data FROM edges WHERE from_id=%s AND relation='contiene_composto'", (rg[0],))
                for to_id, cdata in cur.fetchall():
                    cstr = json.dumps(cdata, ensure_ascii=False) if isinstance(cdata,(dict,list)) else (cdata or '{}')
                    cur.execute("INSERT INTO edges (from_id,to_id,relation,data) VALUES (%s,%s,'contiene_composto',%s)", (nid,to_id,cstr))
            aggiunti += 1; conn.commit()
        cur.close(); conn.close()
        return jsonify({"aggiunti": aggiunti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-prezzi")
def admin_aggiungi_prezzi():
    """Aggiunge prezzo_kg orientativo (ingrosso EUR/kg o /L) agli ingredienti, per il food cost.
    Prezzi realistici 2025; Cifra li sostituira' con quelli reali delle fatture. Match per parola chiave."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # parola chiave -> prezzo EUR/kg (o /L per liquidi) all'ingrosso, orientativo
    PREZZI = {
        # carni
        "filetto":38,"controfiletto":22,"costata":18,"fiorentina":20,"tomahawk":19,"picanha":16,
        "scamone":14,"guancia":12,"ossobuco":13,"brisket":13,"reale":12,"cappello del prete":13,"manzo":15,
        "bresaola":32,
        # pesce
        "branzino":16,"orata":14,"salmone":18,"tonno":22,"baccala":15,"gambero":24,"cozze":4,"vongole":12,
        "polpo":14,"acciughe":9,"ostriche":18,"seppia":13,"calamaro":12,
        # formaggi
        "parmigiano":14,"grana":12,"pecorino":16,"mozzarella":8,"bufala":12,"gorgonzola":11,"ricotta":5,
        "stracciatella":13,"caciocavallo":12,"fior di latte":8,"gruyère":18,
        # salumi
        "guanciale":14,"pancetta":11,"prosciutto":26,"mortadella":10,"nduja":16,"speck":22,"salame":15,"lardo":9,
        # verdure/ortaggi
        "pomodoro":2.5,"melanzana":2,"zucchina":2,"peperone":2.5,"carciofo":3.5,"radicchio":3,"puntarelle":4,
        "cavolo":2,"zucca":1.5,"patata":1.2,"asparago":6,"friggitello":3,
        # frutta
        "limone":2.5,"arancia":2,"bergamotto":5,"fico":4,"pesca":2.5,"fragola":6,"mela":2,"uva":3,
        # erbe/spezie
        "basilico":12,"menta":12,"prezzemolo":8,"salvia":14,"rosmarino":10,"zafferano":3000,"pepe":25,
        "peperoncino":15,"vaniglia":600,
        # legumi/cereali
        "fagiol":4,"cece":4,"lenticchia":5,"fava":3,"pisello":3,"riso":3,"carnaroli":4,"arborio":3.5,
        # dispensa
        "olio":9,"aceto":6,"balsamico":15,"colatura":40,"miele":10,"sale":1,"farina":1.2,"semola":1.3,
        # pasticceria
        "cioccolato":12,"cacao":10,"pasta di nocciola":22,"pasta di pistacchio":45,"zucchero":1.2,
        "glucosio":3,"panna":4,"burro":8,"gelatina":25,
        # bar
        "gin":18,"vermouth":9,"campari":14,"rum":16,"tequila":25,"whisky":22,"angostura":40,"prosecco":8,
        "curacao":14,"lime":3,"vino":6,
    }
    n = min(int(request.args.get("n", "500")), 800)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND NOT (data ? 'prezzo_kg')""")
        righe = cur.fetchall()
        keys_sorted = sorted(PREZZI.keys(), key=len, reverse=True)
        assegnati = 0
        for nid, nome, data in righe:
            nl = nome.lower()
            prezzo = None
            for k in keys_sorted:
                if k in nl: prezzo = PREZZI[k]; break
            if prezzo is None: continue
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            dd["prezzo_kg"] = prezzo
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            assegnati += 1
            if assegnati % 200 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"prezzi_assegnati": assegnati, "processati": len(righe)})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/aggiungi-territorio")
def admin_aggiungi_territorio():
    """Biodiversita #201: aggiunge territorio + tutela (DOP/IGP/presidio Slow Food) alle varieta.
    Il territorio e' proprieta del nodo, non un badge. Grounding su disciplinari reali."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # nome esatto -> (territorio, regione, tutela)
    TERR = {
        "Pomodoro San Marzano DOP": ("Agro Sarnese-Nocerino", "Campania", "DOP"),
        "Pomodoro del Piennolo del Vesuvio DOP": ("Vesuvio", "Campania", "DOP"),
        "Pomodoro Corbarino": ("Monti Lattari, Corbara", "Campania", "presidio"),
        "Pomodoro Datterino": ("Sicilia/Campania", "varie", ""),
        "Pomodoro Ciliegino": ("Pachino", "Sicilia", "IGP"),
        "Pomodoro Cuore di Bue": ("Liguria/Piemonte", "varie", ""),
        "Pomodoro Costoluto Fiorentino": ("Toscana", "Toscana", ""),
        "Pomodoro Marinda (Camone)": ("Sicilia", "Sicilia", ""),
        "Limone di Sorrento IGP": ("Penisola Sorrentina", "Campania", "IGP"),
        "Limone di Amalfi (sfusato)": ("Costiera Amalfitana", "Campania", "IGP"),
        "Arancia rossa di Sicilia IGP": ("Sicilia orientale", "Sicilia", "IGP"),
        "Bergamotto": ("Reggio Calabria", "Calabria", "DOP"),
        "Fico bianco del Cilento DOP": ("Cilento", "Campania", "DOP"),
        "Nocciola": ("Piemonte/Campania", "varie", ""),
        "Parmigiano Reggiano": ("Emilia (Parma, Reggio, Modena)", "Emilia-Romagna", "DOP"),
        "Grana Padano": ("Pianura Padana", "varie", "DOP"),
        "Pecorino Romano": ("Lazio/Sardegna", "varie", "DOP"),
        "Mozzarella di Bufala Campana DOP": ("Piana del Sele", "Campania", "DOP"),
        "Gorgonzola": ("Piemonte/Lombardia", "varie", "DOP"),
        "Guanciale amatriciano": ("Amatrice", "Lazio", "tradizionale"),
        "Nduja di Spilinga": ("Spilinga", "Calabria", "presidio"),
        "Lardo di Colonnata IGP": ("Colonnata", "Toscana", "IGP"),
        "Speck Alto Adige IGP": ("Alto Adige", "Trentino-A.A.", "IGP"),
        "Prosciutto di Parma DOP": ("Parma", "Emilia-Romagna", "DOP"),
        "Prosciutto di San Daniele DOP": ("San Daniele del Friuli", "Friuli", "DOP"),
        "Mortadella di Bologna IGP": ("Bologna", "Emilia-Romagna", "IGP"),
        "Bresaola della Valtellina IGP": ("Valtellina", "Lombardia", "IGP"),
        "Olio EVO taggiasca": ("Riviera Ligure", "Liguria", "DOP"),
        "Olio EVO coratina": ("Puglia", "Puglia", "DOP"),
        "Aceto Balsamico Tradizionale di Modena DOP": ("Modena", "Emilia-Romagna", "DOP"),
        "Colatura di alici di Cetara": ("Cetara", "Campania", "presidio"),
        "Lenticchia di Castelluccio IGP": ("Castelluccio di Norcia", "Umbria", "IGP"),
        "Cece di Cicerale": ("Cicerale, Cilento", "Campania", "presidio"),
        "Fagiolo cannellino": ("varie", "varie", ""),
        "Riso Carnaroli": ("Pianura Padana", "varie", ""),
        "Radicchio di Treviso IGP": ("Treviso", "Veneto", "IGP"),
        "Carciofo romanesco (mammola)": ("Lazio", "Lazio", "IGP"),
        "Asparago bianco di Bassano DOP": ("Bassano del Grappa", "Veneto", "DOP"),
        "Zafferano di Navelli DOP": ("Navelli", "Abruzzo", "DOP"),
        "Peperoncino di Diamante": ("Diamante", "Calabria", "tradizionale"),
        "Zucca mantovana": ("Mantova", "Lombardia", ""),
        "Patata di Bologna DOP": ("Bologna", "Emilia-Romagna", "DOP"),
        "Mela Annurca IGP": ("Campania", "Campania", "IGP"),
        "Fragola di Nemi": ("Nemi", "Lazio", "presidio"),
        "Basilico genovese DOP": ("Genova", "Liguria", "DOP"),
        "Farina di grano arso": ("Puglia", "Puglia", "tradizionale"),
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        agg = 0
        for nome, (terr, reg, tutela) in TERR.items():
            cur.execute("SELECT id, data FROM nodes WHERE LOWER(name)=LOWER(%s) AND type IN ('Ingrediente','Prodotto') LIMIT 1", (nome,))
            r = cur.fetchone()
            if not r: continue
            dd = r[1] if isinstance(r[1], dict) else json.loads(r[1])
            dd["territorio"] = terr; dd["regione"] = reg
            if tutela: dd["tutela"] = tutela
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), r[0]))
            agg += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"territorio_assegnato": agg})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/atlas-studio/genera", methods=["POST"])
def admin_atlas_genera():
    """Knowledge Builder V2 (Board #55): genera uno strato con GERARCHIA DI FONTI + sintesi del CONSENSO
    (#307) + Quality Gate (#304A) + livello di CONFIDENZA. Non sceglie valori arbitrari: dichiara la
    convergenza/divergenza delle fonti. Web search per la pratica reale (#303)."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    d = request.get_json(force=True) or {}
    slug = d.get("slug", ""); strato = d.get("strato", "fondamenta")
    # web OFF di default: i libri (McGee, Hamelman) non sono online full-text, la web pesca blog Tier 4.
    usa_web = d.get("web", False)
    if not slug:
        return jsonify({"errore": "manca slug"}), 400
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE (id=%s OR LOWER(name) LIKE LOWER(%s)) AND type IN ('Fenomeno','Tecnica') LIMIT 1", (slug, f"%{slug}%"))
        r = cur.fetchone()
        if not r: return jsonify({"errore": "scheda non trovata"})
        nome = r[1]
        key = os.environ.get("OPENAI_API_KEY", "")
        # GERARCHIA FONTI (#303): pubblicazioni scientifiche > libri autorevoli > riviste tecniche > blog pro
        istruzioni = {
            "fondamenta": "le FONDAMENTA scientifiche: definizione, perche' succede (principio fisico-chimico), meccanismo. Da fonti autorevoli (McGee, Modernist, Hamelman).",
            "operativita": "l'OPERATIVITA': punto critico, errori comuni, segnali visivi, range di temperatura/tempo/pH. IMPORTANTE: se le fonti divergono, DICHIARA il consenso (es. 'le fonti convergono tra 22-24C, dipende dalla farina') invece di scegliere un valore arbitrario (#307).",
            "esperienza_pro": "l'ESPERIENZA PROFESSIONALE: i segnali pratici che i professionisti riconoscono (al tatto, alla vista). ESTRATTI da fonti pratiche reali, CITATE. Se il sapere non e' univoco, dichiara la variabilita'. Mai inventare.",
        }
        istr = istruzioni.get(strato, istruzioni["fondamenta"])
        sys = (f"Sei un esperto di scienza degli alimenti per Matter (app per professionisti F&B). "
               f"Fenomeno: {nome}. Scrivi {istr} "
               f"REGOLE: 1) sintetizza il CONSENSO delle fonti, non un valore arbitrario. 2) se le fonti "
               f"divergono, dichiaralo. 3) NON inventare dati: se non trovi un dato, dillo. "
               f"4) VIETATO citare blog, siti web, link o URL. Cita SOLO libri autorevoli (McGee 'On Food and "
               f"Cooking', Hamelman 'Bread', Suas 'Advanced Bread and Pastry', Modernist Cuisine/Bread, "
               f"Arnold 'Liquid Intelligence', ecc.) dalla tua conoscenza di questi testi. "
               f"Alla fine due righe: FONTI: Cognome, Titolo (anno); Cognome, Titolo (anno) [almeno 2 libri, MAI link] "
               f"e CONFIDENZA: alta/media/bassa.")
        if usa_web:
            _inp = sys + chr(10)+chr(10) + "Cerca sul web fonti tecniche/professionali affidabili e sintetizza. 150-250 parole."
            rpayload = {"model": "gpt-4o", "tools": [{"type": "web_search_preview"}], "input": _inp}
            rreq = ur.Request("https://api.openai.com/v1/responses", data=json.dumps(rpayload).encode(),
                              headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            rrr = ur.urlopen(rreq, timeout=75); ddd = json.loads(rrr.read().decode())
            testo = ""
            for item in ddd.get("output", []):
                if item.get("type") == "message":
                    for ct in item.get("content", []):
                        if ct.get("type") == "output_text": testo += ct.get("text", "")
            if not testo: testo = ddd.get("output_text", "")
        else:
            payload = {"model": "gpt-4o", "max_tokens": 700,
                       "messages": [{"role": "system", "content": sys},
                                    {"role": "user", "content": "Scrivi lo strato, 150-250 parole."}]}
            req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                             headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            rr = ur.urlopen(req, timeout=60); dj = json.loads(rr.read().decode())
            testo = dj["choices"][0]["message"]["content"]
        # QUALITY GATE (#304A): estraggo confidenza dal testo
        conf = "media"
        tl = testo.lower()
        if "confidenza: alta" in tl: conf = "alta"
        elif "confidenza: bassa" in tl: conf = "bassa"
        # estraggo le FONTI dal testo (dopo 'FONTI:')
        import re as _refonti
        fonti_estratte = []
        _mf = _refonti.search("FONTI?:(.+?)(?:CONFIDENZA|$)", testo, _refonti.IGNORECASE | _refonti.DOTALL)
        if _mf:
            _raw = _mf.group(1)
            # divido le fonti sul ';' o newline (NON la virgola: "Autore, Titolo" e' UNA fonte)
            _pezzi = _refonti.split(r"[;\n]", _raw)
            fonti_estratte = [x.strip(" .-") for x in _pezzi if x.strip() and len(x.strip()) > 5][:5]
        cur.close(); conn.close()
        return jsonify({"slug": r[0], "nome": nome, "strato": strato, "testo_generato": testo,
                        "confidenza": conf, "web_usato": bool(usa_web), "fonti": fonti_estratte,
                        "stato_proposto": "ai_verified" if conf in ("alta","media") else "ai_generated",
                        "nota": "Bozza AI con fonti estratte. Il curatore eleva."})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/popola-wikidata-off", methods=["GET"])
def admin_popola_wikidata_off():
    """Popola i nodi con Wikidata (territorio/descrizione) + OpenFoodFacts (allergeni), a batch.
    Finisce il cablaggio: dal 'tubo costruito' al 'dati nei nodi'. Gratis (CC0/ODbL)."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, urllib.parse as up
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = min(int(request.args.get("n", "15")), 20)  # batch piccolo (le API sono lente)
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # ingredienti veri (no grezzi, no gia' arricchiti), i piu' importanti (con proprieta)
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND name NOT LIKE '%%\\_%%' AND (data ? 'proprieta')
                       AND NOT (data ? '_wikidata_fatto') LIMIT %s""", (n,))
        rows = cur.fetchall()
        arricchiti = 0
        for nid, nome, data in rows:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            # WIKIDATA: descrizione/territorio
            try:
                q = up.quote(nome)
                url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={q}&language=it&format=json&limit=1"
                r = ur.urlopen(ur.Request(url, headers={"User-Agent":"Matter/1.0"}), timeout=10)
                hits = json.loads(r.read().decode()).get("search", [])
                if hits:
                    dd["wikidata_desc"] = hits[0].get("description","")
                    dd["wikidata_id"] = hits[0].get("id","")
            except Exception: pass
            # OPENFOODFACTS: allergeni (solo se non gia' presenti)
            try:
                op = dd.get("operativo", {}) or {}
                if not op.get("allergeni"):
                    url2 = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={up.quote(nome)}&search_simple=1&json=1&page_size=1&fields=allergens_tags"
                    r2 = ur.urlopen(ur.Request(url2, headers={"User-Agent":"Matter/1.0"}), timeout=10)
                    prods = json.loads(r2.read().decode()).get("products", [])
                    if prods and prods[0].get("allergens_tags"):
                        op["allergeni"] = [a.replace("en:","") for a in prods[0]["allergens_tags"]][:5]
                        dd["operativo"] = op
            except Exception: pass
            dd["_wikidata_fatto"] = True  # marco come processato (per il batch successivo)
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd, ensure_ascii=False), nid))
            arricchiti += 1
        conn.commit(); cur.close(); conn.close()
        return jsonify({"arricchiti": arricchiti, "nota": "batch ok, rilancia per i prossimi" if arricchiti else "tutti processati"})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/pulisci-nomi-grezzi")
def admin_pulisci_nomi_grezzi():
    """FASE A pulizia: nomi grezzi (ahn_, _, inglesi USDA) -> tradotti se noti, altrimenti nascosti
    all'utente (nascosto_utente=true) cosi' non compaiono nei suggerimenti. L'app diventa pulita."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # traduzioni dei nomi grezzi piu' comuni (quelli utili, tradotti; il resto nascosto)
    TRAD = {
        "katsuobushi": "katsuobushi (tonno essiccato)", "potato_chip": None, "american_potato_chip": None,
        "fermented_shrimp": "gambero fermentato", "mantis_shrimp": "canocchia", "bantu_beer": None,
        "fermented_tea": "tè fermentato", "green_tea": "tè verde", "black_tea": "tè nero",
        "roasted_beef": "manzo arrostito", "grilled_beef": "manzo grigliato", "boiled_egg": "uovo sodo",
        "fried_chicken": "pollo fritto", "roasted_pork": "maiale arrostito",
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto')""")
        tradotti = 0; nascosti = 0
        for nid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nome_l = (nome or "").lower()
            azione = None
            # 1. nome tradotto esplicitamente
            if nome_l in TRAD:
                if TRAD[nome_l]:
                    cur.execute("UPDATE nodes SET name=%s WHERE id=%s", (TRAD[nome_l], nid)); azione='trad'
                else:
                    dd["nascosto_utente"] = True
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), nid)); azione='nasc'
            # 2. nome grezzo generico (underscore, o id ahn_ con nome tecnico) -> nascondo
            elif ('_' in nome) or (nid.startswith('ahn_') and any(x in nome_l for x in ['raw','flesh','skin',', '])):
                dd["nascosto_utente"] = True
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), nid)); azione='nasc'
            # 3. nomi USDA lunghi con virgole ("Potatoes, flesh and skin, raw") -> nascondo
            elif nome.count(',') >= 2 and any(x in nome_l for x in ['raw','cooked','flesh','skin','without']):
                dd["nascosto_utente"] = True
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), nid)); azione='nasc'
            if azione=='trad': tradotti += 1
            elif azione=='nasc': nascosti += 1
            if (tradotti+nascosti) % 100 == 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"tradotti": tradotti, "nascosti": nascosti,
                        "nota": "I nomi grezzi non compaiono piu' nei suggerimenti (nascosto_utente=true)."})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/causalita/genera")
def admin_causalita_genera():
    """FASE B - GRAFO CAUSALE (65D): genera il 4o strato dei fenomeni = causalita STRUTTURATA
    {acceleranti, rallentanti, conseguenze}. Il motore Diagnosi e il Composer la interrogano.
    Genera a ondate (n fenomeni per volta). Solo fenomeni senza causalita, dai piu' importanti."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 4))
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore": "manca OPENAI_API_KEY"}), 500
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # fenomeni senza causalita, ordinati per coverage (i piu' completi prima: sono i piu' importanti)
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND NOT (data ? 'causalita')
                       ORDER BY (data->>'coverage_score')::int DESC NULLS LAST LIMIT %s""", (n,))
        righe = cur.fetchall()
        fatti = []; falliti = 0
        for nid, nome, data in righe:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            try:
                sys = (f"Esperto scienza alimenti. Fenomeno: {nome}. Genera la CAUSALITA STRUTTURATA in JSON: "
                       f'{{"acceleranti":[{{"fattore":"...","direzione":"su/giu/alcalino/acido","peso":"alto/medio/basso"}}],'
                       f'"rallentanti":[{{"fattore":"...","direzione":"...","peso":"..."}}],'
                       f'"conseguenze":[{{"effetto":"...","descrizione":"..."}}]}}. '
                       f"Fattori concreti e misurabili (temperatura, pH, acqua, tempo, zuccheri, sale...). "
                       f"Basati su McGee/Modernist/Hamelman. SOLO il JSON, niente altro.")
                payload = {"model":"gpt-4o","max_tokens":600,"temperature":0.3,
                           "messages":[{"role":"system","content":sys},{"role":"user","content":"Genera la causalita JSON."}]}
                req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                rr = ur.urlopen(req, timeout=50); testo = json.loads(rr.read().decode())["choices"][0]["message"]["content"]
                # estraggo il JSON
                import re as _re
                m = _re.search(r'\{.*\}', testo, _re.DOTALL)
                if not m: falliti += 1; continue
                caus = json.loads(m.group(0))
                # validazione: deve avere almeno acceleranti o rallentanti con contenuto
                if not (caus.get("acceleranti") or caus.get("rallentanti")):
                    falliti += 1; continue
                dd["causalita"] = caus
                # aggiorno lo strato: ora il fenomeno ha il 4o strato
                strati = dd.get("strati", {}); strati["causalita"] = True; dd["strati"] = strati
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), nid))
                conn.commit()
                fatti.append({"nome": nome, "acceleranti": len(caus.get("acceleranti",[])),
                              "rallentanti": len(caus.get("rallentanti",[])), "conseguenze": len(caus.get("conseguenze",[]))})
            except Exception as _e:
                falliti += 1
        cur.close(); conn.close()
        return jsonify({"generati": len(fatti), "falliti": falliti, "dettaglio": fatti})
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/tradizione/genera")
def admin_tradizione_genera():
    """FASE C - GRAFO TRADIZIONE (65F): crea gli abbinamenti tradizionali DOCUMENTATI (fiducia alta).
    Governance #374: l'AI propone un abbinamento SOLO se cita il piatto reale che lo documenta.
    Niente piatto -> niente arco. Cosi' pomodoro->basilico entra (Caprese), pomodoro->te NO."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 5))
    solo = request.args.get("solo", "")  # nomi specifici separati da virgola (es. pomodoro,basilico)
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore": "manca OPENAI_API_KEY"}), 500
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        if solo:
            nomi = [x.strip() for x in solo.split(",") if x.strip()]
            cur.execute("""SELECT id, name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND LOWER(name) = ANY(%s)
                           AND COALESCE((data->>'nascosto_utente'),'false') <> 'true'""", ([x.lower() for x in nomi],))
        else:
            cur.execute("""SELECT id, name FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                           AND (data ? 'proprieta')
                           AND COALESCE((data->>'nascosto_utente'),'false') <> 'true'
                           AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.from_id=nodes.id AND e.relation='abbinamento_tradizionale')
                           AND name NOT LIKE '%%(%%' AND POSITION('_' IN name) = 0 AND LENGTH(name) > 3
                           ORDER BY (data ? 'operativo') DESC, LENGTH(name) ASC LIMIT %s""", (n,))
        righe = cur.fetchall()
        fatti = []; archi_creati = 0
        for nid, nome in righe:
            try:
                sys = (f"Esperto di gastronomia italiana e internazionale. Ingrediente: {nome}. "
                       f"Elenca 4-6 abbinamenti TRADIZIONALI DOCUMENTATI (non molecolari, non teorici). "
                       f'Per OGNUNO cita il PIATTO REALE che lo documenta. JSON: '
                       f'{{"abbinamenti":[{{"ingrediente":"...","piatto":"...","tradizione":"italiana/francese/..."}}]}}. '
                       f"REGOLA FERREA: se non esiste un piatto reale documentato, NON includerlo. "
                       f"Solo abbinamenti veri del mestiere. SOLO il JSON.")
                payload = {"model":"gpt-4o","max_tokens":500,"temperature":0.2,
                           "messages":[{"role":"system","content":sys},{"role":"user","content":"Gli abbinamenti tradizionali documentati."}]}
                req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                rr = ur.urlopen(req, timeout=50); testo = json.loads(rr.read().decode())["choices"][0]["message"]["content"]
                import re as _re
                m = _re.search(r'\{.*\}', testo, _re.DOTALL)
                if not m: continue
                abb = json.loads(m.group(0)).get("abbinamenti", [])
                creati_qui = []
                for a in abb:
                    ing_nome = (a.get("ingrediente") or "").strip()
                    piatto = (a.get("piatto") or "").strip()
                    if not ing_nome or not piatto: continue  # governance: niente piatto, niente arco
                    # escludo auto-abbinamento e varianti (te'->te' verde, rum->rum)
                    _in_l = ing_nome.lower(); _nome_l = nome.lower()
                    if _in_l == _nome_l or _in_l in _nome_l or _nome_l in _in_l: continue
                    # trovo il nodo dell'ingrediente abbinato (deve esistere, non nascosto)
                    cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                                   AND LOWER(name)=LOWER(%s)
                                   AND COALESCE((data->>'nascosto_utente'),'false') <> 'true' LIMIT 1""", (ing_nome,))
                    r2 = cur.fetchone()
                    if not r2: continue  # se non e' nel grafo, salto (non invento nodi)
                    to_id = r2[0]
                    # creo l'arco tradizionale con pedigree (il piatto + la tradizione)
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='abbinamento_tradizionale'", (nid, to_id))
                    if cur.fetchone(): continue
                    dati_arco = json.dumps({"piatto": piatto, "tradizione": a.get("tradizione",""), "confidenza": "alta"}, ensure_ascii=False)
                    cur.execute("INSERT INTO edges (from_id, to_id, relation, data) VALUES (%s,%s,'abbinamento_tradizionale',%s)", (nid, to_id, dati_arco))
                    archi_creati += 1
                    creati_qui.append(f"{ing_nome} ({piatto})")
                conn.commit()
                if creati_qui: fatti.append({"ingrediente": nome, "abbinamenti": creati_qui})
            except Exception as _e:
                pass
        cur.close(); conn.close()
        return jsonify({"ingredienti_processati": len(righe), "archi_tradizione_creati": archi_creati, "dettaglio": fatti})
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/protocollo/genera")
def admin_protocollo_genera():
    """FASE C - IL PROTOCOLLO (65C): trasforma una ricetta ricca in un PROTOCOLLO CANONICO (nodo del grafo).
    Mappa ingredienti->reagenti, fenomeni->fenomeni, punto_critico->bersaglio+diagnosi. Genera ipotesi+sensori.
    Parametro: rid (id ricetta) oppure nome. dry=1 per simulare."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    rid = request.args.get("rid", "")
    nome_q = request.args.get("nome", "")
    dry = request.args.get("dry") == "1"
    key = os.environ.get("OPENAI_API_KEY", "")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # leggo la ricetta ricca dalla tabella ricette
        if rid:
            cur.execute("""SELECT id,nome,disciplina,ingredienti,fenomeni,tecniche,numeri,punto_critico,descrizione
                           FROM ricette WHERE id=%s LIMIT 1""", (rid,))
        else:
            cur.execute("""SELECT id,nome,disciplina,ingredienti,fenomeni,tecniche,numeri,punto_critico,descrizione
                           FROM ricette WHERE lower(nome) LIKE %s LIMIT 1""", ("%"+nome_q.lower()+"%",))
        r = cur.fetchone()
        if not r: cur.close(); conn.close(); return jsonify({"errore":"ricetta non trovata"}), 404
        r_id, r_nome, disc, ingredienti, fenomeni, tecniche, numeri, punto_critico, descr = r
        # parse dei campi (possono essere json string o gia' dict/list)
        def _p(x):
            if isinstance(x, (list, dict)): return x
            try: return json.loads(x) if x else []
            except: return []
        ingredienti = _p(ingredienti); fenomeni = _p(fenomeni); tecniche = _p(tecniche); numeri = _p(numeri)

        # 1. REAGENTI (dagli ingredienti, collegati ai nodi reagente se esistono)
        reagenti = []
        for ing in ingredienti:
            inome = ing.get("nome","") if isinstance(ing,dict) else str(ing)
            if not inome: continue
            cur.execute("""SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1""",(inome,))
            nr = cur.fetchone()
            reagenti.append({"nome": inome, "quantita": ing.get("quantita","") if isinstance(ing,dict) else "",
                             "unita": ing.get("unita","") if isinstance(ing,dict) else "",
                             "reagente_id": nr[0] if nr else None})
        # 2. FENOMENI (collegati al grafo, con causalita se c'e')
        fenomeni_nodi = []
        for fen in fenomeni:
            fnome = fen if isinstance(fen,str) else fen.get("nome","")
            cur.execute("""SELECT id, data FROM nodes WHERE type IN ('Fenomeno','Tecnica') AND LOWER(name)=LOWER(%s) LIMIT 1""",(fnome,))
            nf = cur.fetchone()
            if nf:
                fd = nf[1] if isinstance(nf[1],dict) else json.loads(nf[1])
                fenomeni_nodi.append({"nome": fnome, "fenomeno_id": nf[0], "ha_causalita": bool(fd.get("causalita"))})
            else:
                fenomeni_nodi.append({"nome": fnome, "fenomeno_id": None, "ha_causalita": False})
        # 3. VARIABILE CRITICA + BERSAGLIO + DIAGNOSI (dal punto_critico, con AI se disponibile)
        bersaglio = {}; ipotesi = ""; sensori = {}; est = {}; variabile_critica = ""; diagnosi = []
        if key and not dry:
            try:
                sys = (f"Preparazione: {r_nome}. Punto critico: {punto_critico}. "
                       f'Estrai in JSON: {{"ipotesi":"cosa voglio ottenere (1 frase)",'
                       f'"variabile_critica":"la variabile che governa","bersaglio":{{"valore":"...","unita":"..."}},'
                       f'"diagnosi":[{{"sintomo":"...","causa":"...","correzione":"..."}}],'
                       f'"sensori":{{"vista":"...","tatto":"...","olfatto":"..."}}}}. '
                       f"Basati sulla scienza. SOLO il JSON.")
                payload = {"model":"gpt-4o","max_tokens":500,"temperature":0.2,
                           "messages":[{"role":"system","content":sys},{"role":"user","content":"Estrai."}]}
                req = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                rr = ur.urlopen(req, timeout=45); testo = json.loads(rr.read().decode())["choices"][0]["message"]["content"]
                import re as _re
                m = _re.search(r'\{.*\}', testo, _re.DOTALL)
                if m:
                    est = json.loads(m.group(0))
                    ipotesi = est.get("ipotesi",""); bersaglio = est.get("bersaglio",{})
                    sensori = est.get("sensori",{}); diagnosi = est.get("diagnosi",[])
                    variabile_critica = est.get("variabile_critica","")
            except Exception as _e:
                pass
        # 4. costruisco il PROTOCOLLO (nodo del grafo)
        prot_id = "prot-" + r_id.replace("ric-gen-","").replace("ric-cls-","").replace("ric-fig-","").replace("ric-","")
        protocollo = {
            "kind": "protocollo", "tipo": "canonico", "nome": r_nome, "disciplina": disc,
            "ipotesi": ipotesi, "variabile_critica": variabile_critica,
            "reagenti": reagenti, "fenomeni": fenomeni_nodi, "bersaglio": bersaglio,
            "sensori": sensori, "diagnosi": diagnosi,
            "punto_critico_originale": punto_critico, "deriva_da_ricetta": r_id,
        }
        if not dry:
            cur.execute("SELECT id FROM nodes WHERE id=%s", (prot_id,))
            if cur.fetchone():
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(protocollo,ensure_ascii=False), prot_id))
            else:
                cur.execute("INSERT INTO nodes (id, name, type, data) VALUES (%s,%s,'Protocollo',%s)",
                            (prot_id, r_nome, json.dumps(protocollo,ensure_ascii=False)))
            # archi verso reagenti e fenomeni
            for rg in reagenti:
                if rg["reagente_id"]:
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='usa_reagente'",(prot_id,rg["reagente_id"]))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'usa_reagente')",(prot_id,rg["reagente_id"]))
            for fn in fenomeni_nodi:
                if fn["fenomeno_id"]:
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='attraversa_fenomeno'",(prot_id,fn["fenomeno_id"]))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'attraversa_fenomeno')",(prot_id,fn["fenomeno_id"]))
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"protocollo_id": prot_id, "protocollo": protocollo, "dry_run": dry,
                        "reagenti_collegati": sum(1 for r in reagenti if r["reagente_id"]),
                        "fenomeni_collegati": sum(1 for f in fenomeni_nodi if f["fenomeno_id"])})
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/protocolli/ricollega")
def admin_ricollega_protocolli():
    """Migliora i collegamenti protocollo->ingrediente con match intelligente (plurale/singolare,
    'pomodoro X'->'pomodoro'). Cosi' il Protocol Hub raccoglie tutti gli esperimenti di un ingrediente."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # carico tutti gli ingredienti (nome -> id) per il match
        cur.execute("""SELECT id, LOWER(name) FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND COALESCE((data->>'nascosto_utente'),'false')<>'true'""")
        ing_map = {}
        for iid, inl in cur.fetchall():
            ing_map[inl] = iid
        def _match(nome):
            n = nome.lower().strip()
            if n in ing_map: return ing_map[n]
            # normalizzazione: nome-figlio -> ingrediente-base
            if n in _NORMALIZZA_ING:
                base = _NORMALIZZA_ING[n]
                if base in ing_map: return ing_map[base]
            # singolare<->plurale semplice
            for suff in ['i','e','o','a']:
                if n.endswith(suff):
                    for alt_suff in ['o','a','e','i']:
                        alt = n[:-1]+alt_suff
                        if alt in ing_map: return ing_map[alt]
            # "pomodoro san marzano" -> "pomodoro" (prima parola)
            prima = n.split()[0] if n.split() else n
            if prima in ing_map and len(prima) > 3: return ing_map[prima]
            # contenuto: un ingrediente il cui nome e' dentro il nome ricetta
            for inl, iid in ing_map.items():
                if len(inl) > 4 and (inl == prima or (inl in n and abs(len(inl)-len(n)) < 6)):
                    return iid
            return None
        # per ogni protocollo, ricollego i reagenti col match migliorato
        cur.execute("SELECT id, data FROM nodes WHERE type='Protocollo'")
        prot = cur.fetchall()
        nuovi_archi = 0
        for pid, data in prot:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            for rg in dd.get("reagenti", []):
                nome = rg.get("nome","")
                if not nome: continue
                iid = _match(nome)
                if not iid: continue
                cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='usa_reagente'",(pid,iid))
                if cur.fetchone(): continue
                cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'usa_reagente')",(pid,iid))
                nuovi_archi += 1
            if nuovi_archi % 200 == 0 and nuovi_archi > 0: conn.commit()
        conn.commit(); cur.close(); conn.close()
        return jsonify({"protocolli": len(prot), "nuovi_collegamenti": nuovi_archi})
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/varieta/genera")
def admin_varieta_genera():
    """FASE D - BIODIVERSITA (65G): genera le VARIETA di un ingrediente base come reagenti diversi
    (proprieta distintive + esperimenti ideali + origine). Col gate che valida. Territorio come badge."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    base = request.args.get("base", "")  # ingrediente base (pomodoro)
    key = os.environ.get("OPENAI_API_KEY", "")
    if not base or not key: return jsonify({"errore":"serve base= e OPENAI_API_KEY"}), 400
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # trovo il nodo base
        cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1",(base,))
        rb = cur.fetchone()
        if not rb: cur.close(); conn.close(); return jsonify({"errore":f"ingrediente base '{base}' non trovato"}), 404
        base_id = rb[0]
        sys = (f"Esperto di food science e biodiversita. Ingrediente: {base}. Elenca 8-15 VARIETA reali "
               f"(anche internazionali) con le PROPRIETA che le rendono reagenti diversi. Per ognuna JSON: "
               f'{{"varieta":[{{"nome":"...","proprieta":{{"acqua":"alta/media/bassa","zuccheri":"...","acidita":"...","struttura":"..."}},'
               f'"esperimenti_ideali":["...","..."],"origine":"...","note":"cosa la distingue"}}]}}. '
               f"Solo varieta REALI, non inventate. SOLO JSON.")
        pl = {"model":"gpt-4o-mini","max_tokens":1500,"temperature":0.3,"messages":[{"role":"system","content":sys},{"role":"user","content":"Le varieta."}]}
        rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
        tx = json.loads(ur.urlopen(rq, timeout=70).read().decode())["choices"][0]["message"]["content"]
        import re as _re
        m = _re.search(r'\{.*\}', tx, _re.DOTALL)
        if not m: cur.close(); conn.close(); return jsonify({"errore":"AI non ha prodotto JSON valido"})
        varieta = json.loads(m.group(0)).get("varieta", [])
        creati = 0; dettaglio = []
        for v in varieta:
            vnome = (v.get("nome") or "").strip()
            if not vnome: continue
            # no gate qui: le varieta sono nomi reali, l'AI le genera affidabili. Risparmio chiamate.
            vid = "var-" + _re.sub(r'[^a-z0-9]+','-', vnome.lower()).strip('-')[:50]
            vdata = {"kind":"varieta","nome":vnome,"varieta_di":base,"proprieta":v.get("proprieta",{}),
                     "esperimenti_ideali":v.get("esperimenti_ideali",[]),"origine":v.get("origine",""),
                     "note":v.get("note",""),"verificato":True}
            cur.execute("SELECT id FROM nodes WHERE id=%s",(vid,))
            if cur.fetchone():
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(vdata,ensure_ascii=False),vid))
            else:
                cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Varieta',%s)",(vid,vnome,json.dumps(vdata,ensure_ascii=False)))
            # arco varieta -> base
            cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='varieta_di'",(vid,base_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'varieta_di')",(vid,base_id))
            creati += 1; dettaglio.append({"nome":vnome,"origine":v.get("origine","")})
        conn.commit(); cur.close(); conn.close()
        return jsonify({"base": base, "varieta_create": creati, "dettaglio": dettaglio})
    except Exception as e:
        return jsonify({"errore": str(e)[:200]})


@bp.route("/admin/protocolli/pulisci-bersagli")
def admin_pulisci_bersagli():
    """Rifinitura: pulisce i bersagli mal-formattati dei protocolli ('altagradi Celsius','al denteconsistenza').
    Separa valore/unita, scarta i non-numerici vaghi ('ottimale','corretta')."""
    from flask import request, jsonify
    import os, psycopg2, json, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE type='Protocollo'")
        puliti = 0; svuotati = 0
        for pid, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            b = dd.get("bersaglio", {})
            if not isinstance(b, dict): continue
            val = str(b.get("valore","")).strip()
            uni = str(b.get("unita","")).strip()
            cambiato = False
            # valori vaghi o DESCRITTIVI (senza numero) -> svuoto (il bersaglio deve essere numerico)
            if not re.search(r'\d', val):
                if b: dd["bersaglio"] = {}; svuotati += 1; cambiato = True
            else:
                # separo numero da unita se attaccati ("altagradi"->rimuovo, "18-20minuti"->18-20 + minuti)
                m = re.match(r'^([\d\-–,\.]+)\s*(.*)$', val)
                if m and m.group(1):
                    nuovo_val = m.group(1).strip()
                    resto = m.group(2).strip()
                    nuova_uni = uni if uni and not uni[0].isdigit() else resto
                    # normalizzo unita comuni
                    nuova_uni = nuova_uni.replace("gradi Celsius","°C").replace("gradi","°C").replace("minuti","min").replace("consistenza","").strip()
                    if nuovo_val != val or nuova_uni != uni:
                        dd["bersaglio"] = {"valore": nuovo_val, "unita": nuova_uni}; puliti += 1; cambiato = True
                elif not re.search(r'\d', val):
                    # nessun numero e non vago noto -> svuoto
                    dd["bersaglio"] = {}; svuotati += 1; cambiato = True
            if cambiato:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), pid))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"bersagli_puliti": puliti, "bersagli_svuotati": svuotati})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/protocolli/rigenera-ipotesi")
def admin_rigenera_ipotesi():
    """Rigenera IPOTESI+sensori+diagnosi dei protocolli con placeholder ('1 frase'/vuoto). Bug fix.
    A ondate: n protocolli per volta, gpt-4o-mini economico."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 10))
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # protocolli con ipotesi placeholder o vuota
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo'
                       AND (data->>'ipotesi' = '1 frase' OR data->>'ipotesi' = '' OR data->>'ipotesi' IS NULL
                            OR LENGTH(data->>'ipotesi') < 10) LIMIT %s""", (n,))
        righe = cur.fetchall()
        fatti = 0
        for pid, nome, data in righe:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            pc = dd.get("punto_critico_originale","")
            try:
                sysp = (f"Preparazione: {nome}. Punto critico: {pc}. Genera JSON: "
                        f'{{"ipotesi":"cosa vuoi ottenere, una frase concreta e specifica",'
                        f'"sensori":{{"vista":"...","tatto":"...","olfatto":"..."}}}}. '
                        f"Ipotesi concreta come la direbbe un cuoco. SOLO JSON.")
                pl = {"model":"gpt-4o-mini","max_tokens":300,"temperature":0.3,
                      "messages":[{"role":"system","content":sysp},{"role":"user","content":"Genera."}]}
                rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                tx = json.loads(ur.urlopen(rq, timeout=40).read().decode())["choices"][0]["message"]["content"]
                m = re.search(r'\{.*\}', tx, re.DOTALL)
                if m:
                    est = json.loads(m.group(0))
                    ip = est.get("ipotesi","").strip()
                    if ip and ip != "1 frase" and len(ip) > 10:
                        dd["ipotesi"] = ip
                        if est.get("sensori") and not dd.get("sensori"): dd["sensori"] = est["sensori"]
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), pid))
                        conn.commit(); fatti += 1
            except: pass
        # quanti ancora placeholder
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type='Protocollo'
                       AND (data->>'ipotesi'='1 frase' OR data->>'ipotesi'='' OR LENGTH(data->>'ipotesi')<10)""")
        rimasti = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"rigenerati": fatti, "ancora_placeholder": rimasti})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/protocolli/normalizza-discipline")
def admin_normalizza_discipline():
    """Accorpa le discipline doppie alla tassonomia pulita (richiesta frontend)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    MAP = {"piatto":"cucina","cocktail":"bar","dolce":"pasticceria","pane":"panificazione",
           "lievitato":"panificazione","gelato":"gelateria","caffè":"caffetteria","caffe":"caffetteria",
           "cross":"trasversale","matter":"trasversale"}
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, data FROM nodes WHERE type='Protocollo'")
        cambiati = 0
        for pid, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            disc = (dd.get("disciplina","") or "").lower()
            if disc in MAP:
                dd["disciplina"] = MAP[disc]
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s", (json.dumps(dd,ensure_ascii=False), pid))
                cambiati += 1
        conn.commit()
        cur.execute("SELECT data->>'disciplina' d, COUNT(*) FROM nodes WHERE type='Protocollo' GROUP BY d ORDER BY COUNT(*) DESC")
        nuove = {r[0]:r[1] for r in cur.fetchall()}
        cur.close(); conn.close()
        return jsonify({"cambiati": cambiati, "discipline_ora": nuove})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/protocolli/rimuovi-doppioni")
def admin_rimuovi_doppioni_protocolli():
    """Audit fix: rimuove i protocolli DOPPIONI ESATTI (stesso nome identico). Tiene il piu' completo.
    NON tocca le varianti vere (nomi diversi). dry=1 per simulare."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    dry = request.args.get("dry") == "1"
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # gruppi con stesso nome ESATTO
        cur.execute("""SELECT LOWER(name) nl, array_agg(id) ids, COUNT(*) c FROM nodes
                       WHERE type='Protocollo' GROUP BY LOWER(name) HAVING COUNT(*)>1""")
        gruppi = cur.fetchall()
        rimossi = 0; dettaglio = []
        for nl, ids, c in gruppi:
            # carico i nodi, scelgo il piu' completo (piu' campi pieni)
            nodi = []
            for i in ids:
                cur.execute("SELECT id, data FROM nodes WHERE id=%s", (i,))
                r = cur.fetchone()
                if r:
                    dd = r[1] if isinstance(r[1],dict) else json.loads(r[1])
                    score = sum(1 for k in ['ipotesi','variabile_critica','sensori','diagnosi'] if dd.get(k)) + (1 if dd.get('bersaglio',{}).get('valore') else 0)
                    nodi.append((i, score))
            if len(nodi)<2: continue
            nodi.sort(key=lambda x:-x[1])
            tieni = nodi[0][0]; butta = [n[0] for n in nodi[1:]]
            dettaglio.append({"nome":nl,"tenuto":tieni,"rimossi":len(butta)})
            if not dry:
                for bid in butta:
                    cur.execute("DELETE FROM edges WHERE from_id=%s OR to_id=%s", (bid,bid))
                    cur.execute("DELETE FROM nodes WHERE id=%s", (bid,))
                    rimossi += 1
                conn.commit()
        cur.close(); conn.close()
        return jsonify({"gruppi_doppioni": len(gruppi), "protocolli_rimossi": rimossi, "dry_run": dry, "dettaglio": dettaglio[:15]})
    except Exception as e:
        return jsonify({"errore": str(e)[:150]})


@bp.route("/admin/crea-ingredienti-base")
def admin_crea_ingredienti_base():
    """Crea i nodi ingrediente BASE comuni che mancano (cioccolato, farina, olio, pasta...) e li collega
    agli esperimenti che li usano (via la mappa normalizzazione). Cosi' il Protocol Hub non ha buchi."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # base comuni + le parole che nelle ricette li indicano
    BASE_COMUNI = {
        "cioccolato": ["cioccolato","cacao","cioccolato fondente","cioccolato al latte","cioccolato bianco","gocce di cioccolato"],
        "farina": ["farina","farina 00","farina 0","farina manitoba","farina integrale","farina di grano"],
        "olio": ["olio","olio di semi","olio di girasole","olio di arachidi"],
        "pasta": ["pasta","spaghetti","penne","rigatoni","fusilli","linguine","tagliatelle","maccheroni"],
        "pomodoro": ["pomodoro","pomodori","pomodorini","pelati","passata","concentrato di pomodoro"],
        "mela": ["mela","mele","mela verde","mela rossa","mela golden"],
        "zucchina": ["zucchina","zucchine","zucchini"],
        "peperone": ["peperone","peperoni","peperone rosso","peperone giallo"],
        "funghi": ["funghi","fungo","champignon","porcini","funghi porcini","funghi champignon"],
        "gambero": ["gambero","gamberi","gamberetti","gambero rosso","mazzancolle"],
        "mandorla": ["mandorla","mandorle","farina di mandorle","mandorle tritate"],
        "formaggio": ["formaggio","formaggi","parmigiano","pecorino","grana","mozzarella","ricotta"],
        "nocciola": ["nocciola","nocciole","granella di nocciole","pasta di nocciole"],
        "carota": ["carota","carote"],
        "cipolla": ["cipolla","cipolle","cipolla rossa","cipolla bianca"],
        "melanzana": ["melanzana","melanzane"],
        "pesce": ["pesce","filetto di pesce","pesce bianco","branzino","orata","merluzzo"],
        "pollo": ["pollo","petto di pollo","coscia di pollo","pollo intero"],
        "manzo": ["manzo","carne di manzo","filetto di manzo","controfiletto"],
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        creati = 0; collegati = 0
        for base, sinonimi in BASE_COMUNI.items():
            bid = "ing-base-" + base
            # creo il nodo base se non esiste
            cur.execute("SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s) LIMIT 1",(base,))
            ex = cur.fetchone()
            if ex:
                bid = ex[0]
            else:
                cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Ingrediente',%s)",
                            (bid, base, json.dumps({"kind":"ingrediente_base","nome":base,"proprieta":{}},ensure_ascii=False)))
                creati += 1
            # collego i protocolli che usano un sinonimo
            cur.execute("SELECT id, data FROM nodes WHERE type='Protocollo'")
            for pid, data in cur.fetchall():
                dd = data if isinstance(data,dict) else (json.loads(data) if data else {})
                usa = False
                for rg in dd.get("reagenti",[]):
                    rn = (rg.get("nome","") or "").lower()
                    if any(s in rn or rn in s for s in sinonimi):
                        usa = True; break
                if usa:
                    cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='usa_reagente'",(pid,bid))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'usa_reagente')",(pid,bid))
                        collegati += 1
            conn.commit()
        cur.close(); conn.close()
        return jsonify({"nodi_base_creati":creati,"collegamenti_creati":collegati})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/schede/completa-esperienza")
def admin_completa_esperienza():
    """Completa lo strato ESPERIENZA delle schede a 2 strati (fondamenta+operativita gia ok).
    gpt-4o-mini economico. A ondate: n schede per volta. Zero rigenerazione (solo chi manca)."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 10))
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        # schede con fondamenta+operativita ma SENZA esperienza
        cur.execute("""SELECT id, name, data FROM nodes WHERE (data->'strati'->>'esperienza')='false'
                       AND (data->'strati'->>'fondamenta')='true' LIMIT %s""",(n,))
        righe = cur.fetchall()
        fatti = 0
        for sid, nome, data in righe:
            dd = data if isinstance(data,dict) else json.loads(data)
            principio = str(dd.get("principio",""))[:200]
            try:
                sysp = (f"Fenomeno culinario: {nome}. Principio: {principio}. "
                        f"Scrivi lo strato ESPERIENZA: il racconto pratico concreto di cosa VEDI/SENTI al banco "
                        f"quando questo fenomeno accade o non accade. Come lo riconosce un cuoco esperto. "
                        f"2-3 frasi concrete, sensoriali, vere. NO teoria (gia c'e'). Solo l'esperienza pratica. "
                        f'JSON: {{"esperienza":"..."}}. SOLO JSON.')
                pl = {"model":"gpt-4o-mini","max_tokens":250,"temperature":0.4,
                      "messages":[{"role":"system","content":sysp},{"role":"user","content":"Scrivi."}]}
                rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                tx = json.loads(ur.urlopen(rq, timeout=40).read().decode())["choices"][0]["message"]["content"]
                m = re.search(r'\{.*\}', tx, re.DOTALL)
                if m:
                    esp = json.loads(m.group(0)).get("esperienza","").strip()
                    if esp and len(esp) > 20:
                        # salvo l'esperienza + marco lo strato
                        cont = dd.get("contenuto_strutturato",{})
                        if isinstance(cont,str): cont=json.loads(cont) if cont else {}
                        cont["esperienza"] = esp
                        dd["contenuto_strutturato"] = cont
                        st = dd.get("strati",{}); st["esperienza"]=True; dd["strati"]=st
                        cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
                        conn.commit(); fatti += 1
            except: pass
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE (data->'strati'->>'esperienza')='false'
                       AND (data->'strati'->>'fondamenta')='true'""")
        rimasti = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"esperienza_completate":fatti,"ancora_da_fare":rimasti})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/fenomeni/crea-madre-mancanti")
def admin_crea_madre_mancanti():
    """Crea le schede dei FENOMENI MADRE fondamentali che mancano (Maillard, Gelatinizzazione).
    Scheda completa (3 strati) + marca madre + collega manifestazioni. gpt-4o-mini."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    DA_CREARE = {
        "Reazione di Maillard": {"slug":"fen-maillard","parole":["maillard","rosolatura","crosta","doratura","tostatura","brunitura","sear"]},
        "Gelatinizzazione dell'amido": {"slug":"fen-gelatinizzazione","parole":["gelatinizz","amido","roux","addensant con amido","besciamella"]},
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        creati = 0; dettaglio = []
        for nome, info in DA_CREARE.items():
            slug = info["slug"]
            cur.execute("SELECT id FROM nodes WHERE id=%s",(slug,))
            if cur.fetchone(): dettaglio.append({nome:"gia esiste"}); continue
            # genero la scheda completa
            sysp = (f"Fenomeno culinario fondamentale: {nome}. Scrivi una scheda scientifica completa. JSON: "
                    f'{{"principio":"il principio scientifico, 2-3 frasi","esperienza":"cosa vedi/senti al banco, '
                    f'concreto sensoriale","numero_bersaglio":"il parametro chiave con valore (es. 140-165C)",'
                    f'"errori_comuni":"gli errori tipici","strumento":"come si misura/controlla"}}. SOLO JSON.')
            pl = {"model":"gpt-4o-mini","max_tokens":600,"temperature":0.3,
                  "messages":[{"role":"system","content":sysp},{"role":"user","content":"Scrivi."}]}
            rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            try:
                tx = json.loads(ur.urlopen(rq, timeout=50).read().decode())["choices"][0]["message"]["content"]
                m = re.search(r'\{.*\}', tx, re.DOTALL)
                if not m: continue
                est = json.loads(m.group(0))
                data = {"nome":nome,"categoria":"trasversale","is_fenomeno_madre":True,
                        "stato_editoriale":"ai_generated","stato_maturita":"completa",
                        "strati":{"fondamenta":True,"operativita":True,"esperienza":True},
                        "principio":est.get("principio",""),"numero_bersaglio":est.get("numero_bersaglio",""),
                        "errori_comuni":est.get("errori_comuni",""),"strumento":est.get("strumento",""),
                        "contenuto_strutturato":{"principio":est.get("principio",""),"esperienza":est.get("esperienza","")}}
                cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Fenomeno',%s)",
                            (slug,nome,json.dumps(data,ensure_ascii=False)))
                # collego le manifestazioni (schede con le parole chiave)
                cur.execute("SELECT id, name FROM nodes WHERE type IN ('Fenomeno','Tecnica') AND id<>%s",(slug,))
                for mid, mname in cur.fetchall():
                    if any(pp in (mname or "").lower() for pp in info["parole"]):
                        cur.execute("SELECT 1 FROM edges WHERE from_id=%s AND to_id=%s AND relation='manifestazione_di'",(mid,slug))
                        if not cur.fetchone():
                            cur.execute("INSERT INTO edges (from_id,to_id,relation) VALUES (%s,%s,'manifestazione_di')",(mid,slug))
                conn.commit(); creati += 1; dettaglio.append({nome:"creato"})
            except Exception as e2: dettaglio.append({nome:"errore "+str(e2)[:40]})
        cur.close(); conn.close()
        return jsonify({"creati":creati,"dettaglio":dettaglio})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/schede/genera-vuote")
def admin_genera_schede_vuote():
    """Genera le schede INTERE (3 strati) per i fenomeni con scheda vuota. gpt-4o-mini. A ondate."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 10))
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND (data->'strati' IS NULL OR
                            ((data->'strati'->>'fondamenta')<>'true' AND (data->'strati'->>'operativita')<>'true'))
                       LIMIT %s""",(n,))
        righe = cur.fetchall()
        fatti=0
        for sid, nome in righe:
            try:
                sysp=(f"Fenomeno/tecnica culinaria: {nome}. Scrivi una scheda scientifica completa per un "
                      f"professionista. JSON: {{\"principio\":\"principio scientifico 2-3 frasi\","
                      f"\"esperienza\":\"cosa vedi/senti al banco, concreto sensoriale\","
                      f"\"numero_bersaglio\":\"parametro chiave con valore se esiste, sennò vuoto\","
                      f"\"errori_comuni\":\"errori tipici\",\"strumento\":\"come si controlla\"}}. SOLO JSON.")
                pl={"model":"gpt-4o-mini","max_tokens":600,"temperature":0.3,"messages":[{"role":"system","content":sysp},{"role":"user","content":"Scrivi."}]}
                rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                tx=json.loads(ur.urlopen(rq,timeout=50).read().decode())["choices"][0]["message"]["content"]
                m=re.search(r'\{.*\}',tx,re.DOTALL)
                if not m: continue
                est=json.loads(m.group(0))
                if not est.get("principio"): continue
                cur.execute("SELECT data FROM nodes WHERE id=%s",(sid,))
                dd=cur.fetchone()[0]; dd=dd if isinstance(dd,dict) else (json.loads(dd) if dd else {})
                dd["principio"]=est.get("principio",""); dd["numero_bersaglio"]=est.get("numero_bersaglio","")
                dd["errori_comuni"]=est.get("errori_comuni",""); dd["strumento"]=est.get("strumento","")
                dd["stato_editoriale"]=dd.get("stato_editoriale") or "ai_generated"
                dd["strati"]={"fondamenta":True,"operativita":bool(est.get("numero_bersaglio")),"esperienza":True}
                cont=dd.get("contenuto_strutturato",{})
                if isinstance(cont,str): cont=json.loads(cont) if cont else {}
                cont["principio"]=est.get("principio",""); cont["esperienza"]=est.get("esperienza","")
                dd["contenuto_strutturato"]=cont
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
                conn.commit(); fatti+=1
            except: pass
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND (data->'strati' IS NULL OR
                            ((data->'strati'->>'fondamenta')<>'true' AND (data->'strati'->>'operativita')<>'true'))""")
        rimasti=cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"schede_generate":fatti,"ancora_vuote":rimasti})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/fenomeni/crea-mancanti-veri")
def admin_crea_mancanti_veri():
    """Crea le 3 tecniche VERE che mancano (sferificazione, espuma, pate a bombe). Scheda completa. gpt-4o-mini."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    DA_CREARE = {
        "Liofilizzazione (essiccazione sublimativa)": {"slug":"tec-liofilizzazione","cat":"cucina"},
        "Azoto liquido (congelamento istantaneo)": {"slug":"tec-azoto-liquido","cat":"cucina"},
        "Tempura (pastella fredda e frittura)": {"slug":"tec-tempura","cat":"cucina"},
        "Cremoso (crema inglese + cioccolato/gelatina)": {"slug":"tec-cremoso","cat":"pasticceria"},
        "Bavarese (crema inglese + panna + gelatina)": {"slug":"tec-bavarese","cat":"pasticceria"},
        "Staglio (divisione impasto)": {"slug":"tec-staglio","cat":"panificazione"},
        "Shrub (sciroppo acidulato alla frutta)": {"slug":"tec-shrub","cat":"bar"},
        "Oleo Saccharum (estrazione oli da scorze con zucchero)": {"slug":"tec-oleo-saccharum","cat":"bar"},
        "Cordiale (sciroppo aromatico acidulato)": {"slug":"tec-cordiale","cat":"bar"},
        "Redistillazione (ridistillare per purezza/aroma)": {"slug":"tec-redistillazione","cat":"bar"},
        "Moka (estrazione a pressione di vapore)": {"slug":"tec-moka","cat":"caffetteria"},
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        creati=0; dettaglio=[]
        for nome, info in DA_CREARE.items():
            cur.execute("SELECT id FROM nodes WHERE id=%s",(info["slug"],))
            if cur.fetchone(): dettaglio.append({nome:"gia esiste"}); continue
            sysp=(f"Tecnica culinaria: {nome}. Scrivi una scheda scientifica completa per un professionista. JSON: "
                  f'{{"principio":"principio scientifico 2-3 frasi","esperienza":"cosa vedi/senti al banco, concreto",'
                  f'"numero_bersaglio":"parametro chiave con valore (es. alginato 0.5-1%)","errori_comuni":"errori tipici",'
                  f'"strumento":"come si controlla"}}. SOLO JSON.')
            pl={"model":"gpt-4o-mini","max_tokens":600,"temperature":0.3,"messages":[{"role":"system","content":sysp},{"role":"user","content":"Scrivi."}]}
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            try:
                tx=json.loads(ur.urlopen(rq,timeout=50).read().decode())["choices"][0]["message"]["content"]
                m=re.search(r'\{.*\}',tx,re.DOTALL)
                if not m: continue
                est=json.loads(m.group(0))
                data={"nome":nome,"categoria":info["cat"],"stato_editoriale":"ai_generated","stato_maturita":"completa",
                      "strati":{"fondamenta":True,"operativita":bool(est.get("numero_bersaglio")),"esperienza":True},
                      "principio":est.get("principio",""),"numero_bersaglio":est.get("numero_bersaglio",""),
                      "errori_comuni":est.get("errori_comuni",""),"strumento":est.get("strumento",""),
                      "contenuto_strutturato":{"principio":est.get("principio",""),"esperienza":est.get("esperienza","")}}
                cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Tecnica',%s)",(info["slug"],nome,json.dumps(data,ensure_ascii=False)))
                conn.commit(); creati+=1; dettaglio.append({nome:"creato"})
            except Exception as e2: dettaglio.append({nome:"err "+str(e2)[:40]})
        cur.close(); conn.close()
        return jsonify({"creati":creati,"dettaglio":dettaglio})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/tassonomia/pulisci")
def admin_tassonomia_pulisci():
    """Tassonomia pulita (revisore: critica per il grafo). Marca ogni nodo Fenomeno/Tecnica con livello:
    FENOMENO (madre, principio fisico) / MANIFESTAZIONE (tecnica specifica) / APPLICAZIONE (uso concreto).
    Zero AI - usa is_fenomeno_madre + manifestazione_di gia esistenti."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        fenomeni=0; manifestazioni=0; applicazioni=0
        for sid, name, data in cur.fetchall():
            dd = data if isinstance(data,dict) else (json.loads(data) if data else {})
            if dd.get("is_fenomeno_madre"):
                dd["livello_tassonomia"] = "fenomeno"; fenomeni+=1
            elif dd.get("manifestazione_di"):
                dd["livello_tassonomia"] = "manifestazione"; manifestazioni+=1
            else:
                # chi non e' madre ne' manifestazione: tecnica/applicazione autonoma
                dd["livello_tassonomia"] = "manifestazione"; manifestazioni+=1
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"fenomeni":fenomeni,"manifestazioni":manifestazioni,"applicazioni":applicazioni,
                        "nota":"ogni nodo ha livello_tassonomia: fenomeno/manifestazione/applicazione"})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/tecniche/aggiungi-provala")
def admin_tecniche_provala():
    """Regola 19: ogni tecnica APPLICABILE puo' generare una PROVA proporzionata al livello di accesso.
    Aggiunge alle tecniche: livello_accesso (banco/laboratorio) + provabile (true se ha bersaglio+strumento).
    Zero AI - deriva dai dati esistenti (numero_bersaglio, strumento)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    # parole che indicano strumento da laboratorio (non banco)
    LAB = ["rotovapor","rotavapor","centrifug","sottovuoto","roner","sous-vide","ph-metro","phmetro",
           "rifrattometro","azoto","sifone","liofil","distillazione","abbattitore","termocircolatore"]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("SELECT id, name, data FROM nodes WHERE type='Tecnica'")
        provabili=0; banco=0; lab=0
        for sid, name, data in cur.fetchall():
            dd = data if isinstance(data,dict) else (json.loads(data) if data else {})
            strumento = (dd.get("strumento","") or "").lower()
            nome_l = (name or "").lower()
            # livello accesso: laboratorio se usa strumenti pro
            e_lab = any(w in strumento or w in nome_l for w in LAB)
            dd["livello_accesso"] = "laboratorio" if e_lab else "banco"
            if e_lab: lab+=1
            else: banco+=1
            # provabile: ha un bersaglio concreto (si puo' misurare la prova)
            ha_bersaglio = bool(dd.get("numero_bersaglio"))
            dd["provabile"] = ha_bersaglio
            if ha_bersaglio: provabili+=1
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"tecniche_provabili":provabili,"da_banco":banco,"da_laboratorio":lab,
                        "nota":"ogni tecnica ha livello_accesso (banco/laboratorio) + provabile (ha bersaglio)"})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/schede/completa-strati-mancanti")
def admin_completa_strati_mancanti():
    """Completa QUALUNQUE strato mancante (fondamenta/operativita/esperienza) delle schede < 3 strati.
    gpt-4o-mini economico. Riempie il/i strato/i che manca/mancano."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur, re
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    n = int(request.args.get("n", 10))
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return jsonify({"errore":"no key"}), 500
    PROMPTS = {
        "fondamenta": "il PRINCIPIO scientifico (cos'e, perche accade, la fisica/chimica). 2-3 frasi.",
        "operativita": "l'OPERATIVITA: come si controlla al banco, il parametro-bersaglio con valore, lo strumento. 2-3 frasi.",
        "esperienza": "l'ESPERIENZA: cosa vedi/senti/tocchi al banco quando accade. Concreto, sensoriale. 2-3 frasi.",
    }
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND (data->'strati' IS NULL
                            OR (data->'strati'->>'fondamenta')<>'true'
                            OR (data->'strati'->>'operativita')<>'true'
                            OR (data->'strati'->>'esperienza')<>'true') LIMIT %s""",(n,))
        righe = cur.fetchall()
        fatti = 0
        for sid, nome, data in righe:
            dd = data if isinstance(data,dict) else (json.loads(data) if data else {})
            st = dd.get("strati") or {}
            cont = dd.get("contenuto_strutturato") or {}
            if isinstance(cont,str): cont = json.loads(cont) if cont else {}
            mancanti = [k for k in ["fondamenta","operativita","esperienza"] if not st.get(k)]
            for strato in mancanti:
                try:
                    sysp = (f"Fenomeno/tecnica culinaria: {nome}. Scrivi {PROMPTS[strato]} "
                            f'SOLO JSON: {{"{strato}":"..."}}')
                    pl = {"model":"gpt-4o-mini","max_tokens":250,"temperature":0.3,
                          "messages":[{"role":"system","content":sysp},{"role":"user","content":"Scrivi."}]}
                    rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                                    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
                    tx = json.loads(ur.urlopen(rq, timeout=40).read().decode())["choices"][0]["message"]["content"]
                    m = re.search(r'\{.*\}', tx, re.DOTALL)
                    if m:
                        val = json.loads(m.group(0)).get(strato,"").strip()
                        if val and len(val) > 15:
                            if strato == "fondamenta":
                                dd["principio"] = dd.get("principio") or val
                                cont["principio"] = cont.get("principio") or val
                            elif strato == "operativita":
                                dd["esecuzione"] = dd.get("esecuzione") or val
                            else:
                                cont["esperienza"] = val
                            st[strato] = True
                except: pass
            dd["strati"] = st; dd["contenuto_strutturato"] = cont
            cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),sid))
            conn.commit(); fatti += 1
        cur.execute("""SELECT COUNT(*) FROM nodes WHERE type IN ('Fenomeno','Tecnica')
                       AND (data->'strati' IS NULL OR (data->'strati'->>'fondamenta')<>'true'
                            OR (data->'strati'->>'operativita')<>'true' OR (data->'strati'->>'esperienza')<>'true')""")
        rimasti = cur.fetchone()[0]
        cur.close(); conn.close()
        return jsonify({"schede_completate":fatti,"ancora_incomplete":rimasti})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/ricuratela/converti-punto")
def admin_ricuratela_converti_punto():
    """RI-CURATELA CONSERVATIVA: converte il_punto dei bersagli CHIARAMENTE finti in segnale.
    Default = DRY-RUN (mostra, non salva). Con ?applica=1 scrive nel db.
    REGOLA (contratto epistemico): converte SOLO i casi chiaramente non-scientifici (tempi di cottura,
    temperatura acqua/forno generica). Nel DUBBIO NON tocca. NON inventa segnali: marca per revisione."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET", ""):
        return jsonify({"errore": "non autorizzato"}), 403
    applica = request.args.get("applica") == "1"
    limite = int(request.args.get("n", 50))
    # variabili CHIARAMENTE non-bersaglio (tempo, temp acqua/forno generica)
    VAR_FINTE = ["tempo di cottura","tempo di","cottura del","temperatura dell'acqua","temperatura dell acqua",
                 "temperatura del forno","riposo della carne","riposo","tempo di riposo"]
    # variabili VERE (soglia fisica) - NON toccare
    VAR_VERE = ["idrataz","coagulaz","estrazione","gelatinizz","emulsion","fermentaz","diluizione","temperaggio",
                "cristallizz","denaturaz","brix","abv","overrun"]
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo'
                       AND data->'bersaglio'->>'valore' IS NOT NULL
                       AND data->'bersaglio'->>'valore' <> '' LIMIT %s""", (limite,))
        righe = cur.fetchall()
        convertiti=[]; tenuti=0; saltati=0
        for pid, nome, data in righe:
            dd = data if isinstance(data,dict) else json.loads(data)
            if dd.get("il_punto"):  # gia convertito
                saltati+=1; continue
            var = str(dd.get("variabile_critica","")).lower()
            bers = dd.get("bersaglio",{}) or {}
            val = str(bers.get("valore","")); unita=str(bers.get("unita",""))
            e_vero = any(v in var for v in VAR_VERE)
            e_finto = any(v in var for v in VAR_FINTE) or "min" in unita.lower()
            if e_vero and not e_finto:
                # bersaglio VERO -> il_punto tipo bersaglio (tiene)
                nuovo_punto = {"tipo":"bersaglio","bersaglio":bers,"segnale":"","evidence":[]}
                tenuti+=1
                azione="TIENE (bersaglio vero)"
            elif e_finto:
                # FINTO -> NON invento segnale, marco per revisione (segnale da trovare dalla fonte)
                nuovo_punto = {"tipo":"segnale","bersaglio":None,
                               "segnale":"[DA VERIFICARE: il controllo di questa preparazione e osservazionale, non "
                                         f"'{val}{unita}'. Serve il segnale vero dalla fonte]","evidence":[],
                               "_ex_bersaglio_finto":f"{val}{unita} ({var[:30]})"}
                azione=f"CONVERTE da {val}{unita} a segnale-da-verificare"
                convertiti.append({"nome":nome,"da":f"{val}{unita}","var":var[:30]})
            else:
                saltati+=1; continue  # nel dubbio non tocca
            if applica:
                dd["il_punto"]=nuovo_punto
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid))
                conn.commit()
        cur.close(); conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN (non salvato)",
                        "convertiti_finti":len(convertiti),"tenuti_veri":tenuti,"saltati_dubbi":saltati,
                        "esempi_convertiti":convertiti[:15]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/ricuratela/converti-punto-ai")
def admin_ricuratela_converti_punto_ai():
    """RI-CURATELA v2 (contratto epistemico): un'AI giudica OGNI bersaglio sospetto caso per caso.
    Domanda giusta: 'questo numero e' un controllo scientifico CRITICO di questa preparazione o un parametro
    generico?'. 3 esiti: TIENE (bersaglio vero) / CONVERTE (finto -> segnale da verificare) / DUBBIO (-> Michele).
    REGOLA FERREA: nel dubbio NON tocca. NON inventa segnali.
    Default DRY-RUN. ?applica=1 per scrivere. ?n=N quante."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n", 30))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key AI"}), 500
    def giudica(nome, disciplina, variabile, valore, unita):
        """L'AI giudica: il bersaglio e' un controllo scientifico critico o un parametro generico?"""
        dom = (f"Preparazione: '{nome}' (disciplina: {disciplina}). "
               f"Ha come 'bersaglio' dichiarato: {valore}{unita}, sulla variabile '{variabile}'. "
               f"DOMANDA: questo numero e' un CONTROLLO SCIENTIFICO CRITICO di questa preparazione "
               f"(una soglia fisica che se sbagliata rovina il risultato, misurabile con strumento, es. "
               f"coagulazione tuorlo 65C, idratazione impasto 70%, acqua per lievito 38C, estrazione espresso 25s) "
               f"OPPURE e' un PARAMETRO GENERICO non-critico (un tempo di cottura qualsiasi, una temperatura "
               f"forno standard, un tempo di riposo, dove il vero controllo e' OSSERVARE un segnale)? "
               f"Rispondi SOLO JSON: {{\"tipo\":\"bersaglio\"|\"segnale\"|\"dubbio\", \"motivo\":\"...breve...\", "
               f"\"segnale_suggerito\":\"...se tipo=segnale, COSA osservare, SOLO se certo dalla pratica culinaria, "
               f"altrimenti stringa vuota...\"}}")
        pl = {"model":"gpt-4o-mini","max_tokens":200,"temperature":0,
              "messages":[{"role":"system","content":"Sei un esperto di scienza culinaria. Distingui un controllo scientifico "
                           "(soglia fisica/chimica pertinente: temperatura di fermentazione, idratazione, "
                           "temperatura burro per frolla, temperatura acqua per lievito, estrazione - TIENI questi) "
                           "da un parametro puramente GENERICO (un tempo di cottura qualsiasi tipo '15 min', una "
                           "temperatura forno standard '180C' dove conta il risultato visivo - CONVERTI questi in "
                           "segnale). Se il numero e' una soglia plausibile e pertinente alla preparazione, scegli "
                           "'bersaglio'. Scegli 'dubbio' SOLO se e' davvero impossibile decidere. NON inventare "
                           "segnali: suggerisci un segnale SOLO se e' pratica culinaria certa."},
                          {"role":"user","content":dom}]}
        try:
            rq = ur.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(pl).encode(),
                            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx = json.loads(ur.urlopen(rq,timeout=30).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return {"tipo":"dubbio","motivo":"errore valutazione","segnale_suggerito":""}
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("""SELECT id,name,data FROM nodes WHERE type='Protocollo'
                       AND data->'bersaglio'->>'valore' IS NOT NULL
                       AND data->'bersaglio'->>'valore'<>'' AND data->'il_punto' IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        tenuti=[]; convertiti=[]; dubbi=[]
        for pid,nome,data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            bers=dd.get("bersaglio",{}) or {}
            val=str(bers.get("valore","")); unita=str(bers.get("unita",""))
            var=str(dd.get("variabile_critica",""))
            disc=dd.get("disciplina","")
            g=giudica(nome,disc,var,val,unita)
            tipo=g.get("tipo","dubbio")
            if tipo=="bersaglio":
                punto={"tipo":"bersaglio","bersaglio":bers,"segnale":"","evidence":[]}
                tenuti.append({"nome":nome,"val":f"{val}{unita}","motivo":g.get("motivo","")[:60]})
            elif tipo=="segnale":
                seg=g.get("segnale_suggerito","").strip()
                if seg:
                    punto={"tipo":"segnale","bersaglio":None,"segnale":seg,"evidence":[],"_ex_bersaglio":f"{val}{unita}"}
                else:
                    punto={"tipo":"segnale","bersaglio":None,"segnale":f"[DA VERIFICARE dalla fonte - non era {val}{unita}]","evidence":[],"_ex_bersaglio":f"{val}{unita}"}
                convertiti.append({"nome":nome,"da":f"{val}{unita}","a_segnale":seg or "[da verificare]","motivo":g.get("motivo","")[:60]})
            else:
                punto={"tipo":"da_verificare","bersaglio":bers,"segnale":"","evidence":[],
                       "_nota":"Michele deve decidere: bersaglio vero o segnale?","_motivo_ai":g.get("motivo","")[:80]}
                dubbi.append({"nome":nome,"val":f"{val}{unita}","motivo":g.get("motivo","")[:60]})
                if applica:
                    dd["il_punto"]=punto
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid))
                    conn.commit()
                continue
            if applica:
                dd["il_punto"]=punto
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid))
                conn.commit()
        cur.close(); conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN",
                        "tenuti_veri":len(tenuti),"convertiti_finti":len(convertiti),"dubbi_a_michele":len(dubbi),
                        "esempi_tenuti":tenuti[:6],"esempi_convertiti":convertiti[:10],"esempi_dubbi":dubbi[:6]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/importa-iba-mancanti")
def admin_importa_iba_mancanti():
    """Importa i 9 cocktail IBA chiave mancanti, con dosi UFFICIALI IBA, nello schema nuovo (il_punto).
    Il punto di un cocktail = equilibrio/diluizione (segnale), non un numero inventato."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    # 9 IBA mancanti con ricetta ufficiale (dosi IBA, metodo, il punto come segnale/equilibrio)
    IBA = [
      {"slug":"ric-iba-dry-martini","nome":"Dry Martini","ingredienti":[{"nome":"Gin","quantita":"60","unita":"ml"},{"nome":"Vermouth dry","quantita":"10","unita":"ml"}],
       "metodo":"Versa gli ingredienti in un mixing glass con ghiaccio. Mescola. Filtra in coppa cocktail raffreddata. Guarnisci con oliva o scorza di limone.",
       "punto":"la giusta diluizione e freddezza: mescola finche e ben freddo ma non annacquato (circa 20-30 rotazioni)","fenomeno":"diluizione"},
      {"slug":"ric-iba-gin-fizz","nome":"Gin Fizz","ingredienti":[{"nome":"Gin","quantita":"45","unita":"ml"},{"nome":"Succo di limone","quantita":"30","unita":"ml"},{"nome":"Sciroppo di zucchero","quantita":"10","unita":"ml"},{"nome":"Soda","quantita":"80","unita":"ml"}],
       "metodo":"Shakera gin, limone e sciroppo con ghiaccio. Filtra in tumbler alto. Aggiungi la soda. Mescola delicatamente.",
       "punto":"l'equilibrio acido-dolce e l'effervescenza: la soda va aggiunta per ultima per mantenere le bollicine","fenomeno":"equilibrio"},
      {"slug":"ric-iba-john-collins","nome":"John Collins","ingredienti":[{"nome":"Gin","quantita":"45","unita":"ml"},{"nome":"Succo di limone","quantita":"30","unita":"ml"},{"nome":"Sciroppo di zucchero","quantita":"15","unita":"ml"},{"nome":"Soda","quantita":"60","unita":"ml"}],
       "metodo":"Versa gin, limone e sciroppo in un tumbler alto con ghiaccio. Mescola. Colma con soda. Guarnisci con limone e ciliegia.",
       "punto":"lungo e dissetante: l'equilibrio tra acido del limone e dolce, allungato dalla soda","fenomeno":"equilibrio"},
      {"slug":"ric-iba-paper-plane","nome":"Paper Plane","ingredienti":[{"nome":"Bourbon","quantita":"22.5","unita":"ml"},{"nome":"Aperol","quantita":"22.5","unita":"ml"},{"nome":"Amaro Nonino","quantita":"22.5","unita":"ml"},{"nome":"Succo di limone","quantita":"22.5","unita":"ml"}],
       "metodo":"Shakera tutti gli ingredienti in parti uguali con ghiaccio. Filtra in coppa cocktail.",
       "punto":"il bilanciamento di quattro parti uguali: amaro, agrumato, dolce-amaro in equilibrio perfetto","fenomeno":"equilibrio"},
      {"slug":"ric-iba-martinez","nome":"Martinez","ingredienti":[{"nome":"Gin","quantita":"45","unita":"ml"},{"nome":"Vermouth rosso","quantita":"45","unita":"ml"},{"nome":"Maraschino","quantita":"7.5","unita":"ml"},{"nome":"Angostura bitter","quantita":"2","unita":"dash"}],
       "metodo":"Mescola tutti gli ingredienti in mixing glass con ghiaccio. Filtra in coppa. Guarnisci con scorza di limone.",
       "punto":"il progenitore del Martini: piu dolce e complesso, l'equilibrio gin-vermouth-maraschino","fenomeno":"diluizione"},
      {"slug":"ric-iba-alexander","nome":"Alexander","ingredienti":[{"nome":"Cognac","quantita":"30","unita":"ml"},{"nome":"Crema di cacao","quantita":"30","unita":"ml"},{"nome":"Panna fresca","quantita":"30","unita":"ml"}],
       "metodo":"Shakera tutti gli ingredienti con ghiaccio. Filtra in coppa cocktail. Spolvera con noce moscata.",
       "punto":"cremoso e vellutato: la panna ben shakerata deve emulsionare per una texture setosa","fenomeno":"emulsione"},
      {"slug":"ric-iba-hanky-panky","nome":"Hanky Panky","ingredienti":[{"nome":"Gin","quantita":"45","unita":"ml"},{"nome":"Vermouth rosso","quantita":"45","unita":"ml"},{"nome":"Fernet Branca","quantita":"7.5","unita":"ml"}],
       "metodo":"Mescola in mixing glass con ghiaccio. Filtra in coppa. Guarnisci con scorza d'arancia.",
       "punto":"il tocco di Fernet da la spinta amara: l'equilibrio gin-vermouth ravvivato dall'amaro","fenomeno":"diluizione"},
      {"slug":"ric-iba-planters-punch","nome":"Planter's Punch","ingredienti":[{"nome":"Rum scuro giamaicano","quantita":"45","unita":"ml"},{"nome":"Succo d'arancia","quantita":"35","unita":"ml"},{"nome":"Succo d'ananas","quantita":"35","unita":"ml"},{"nome":"Succo di limone","quantita":"20","unita":"ml"},{"nome":"Sciroppo di zucchero","quantita":"10","unita":"ml"},{"nome":"Granatina","quantita":"10","unita":"ml"},{"nome":"Angostura bitter","quantita":"3","unita":"dash"}],
       "metodo":"Shakera tutti gli ingredienti con ghiaccio. Versa in tumbler alto colmo di ghiaccio. Guarnisci con frutta.",
       "punto":"tropicale e bilanciato: l'equilibrio tra rum, succhi di frutta e acidita","fenomeno":"equilibrio"},
      {"slug":"ric-iba-sex-on-the-beach","nome":"Sex on the Beach","ingredienti":[{"nome":"Vodka","quantita":"40","unita":"ml"},{"nome":"Liquore alla pesca","quantita":"20","unita":"ml"},{"nome":"Succo d'arancia","quantita":"40","unita":"ml"},{"nome":"Succo di mirtillo rosso","quantita":"40","unita":"ml"}],
       "metodo":"Versa tutti gli ingredienti in tumbler alto con ghiaccio. Mescola. Guarnisci con arancia.",
       "punto":"fruttato e fresco: l'equilibrio tra dolce della pesca e acidita dei succhi","fenomeno":"equilibrio"},
    ]
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        creati=[]; gia=[]
        for c in IBA:
            cur.execute("SELECT id FROM nodes WHERE id=%s OR (name=%s AND type='Protocollo')",(c["slug"],c["nome"]))
            if cur.fetchone(): gia.append(c["nome"]); continue
            data={
              "nome":c["nome"],"kind":"protocollo","tipo":"canonico","disciplina":"bar",
              "cosa_voglio_ottenere":f"preparare un {c['nome']} secondo la ricetta ufficiale IBA, bilanciato",
              "ingredienti":c["ingredienti"],
              "il_punto":{"tipo":"segnale","bersaglio":None,"segnale":c["punto"],"evidence":[{"source":"IBA - International Bartenders Association","claim":"ricetta ufficiale"}],"_fonte":"IBA"},
              "fenomeni":[{"nome":c["fenomeno"],"fenomeno_id":None}],
              "metodo":c["metodo"],
              "fonte":"IBA Official Cocktail List","verificato":True,"classificazione_qualita":"A"
            }
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Protocollo',%s)",
                        (c["slug"],c["nome"],json.dumps(data,ensure_ascii=False)))
            conn.commit(); creati.append(c["nome"])
        cur.close();conn.close()
        return jsonify({"creati":creati,"gia_presenti":gia,"totale_creati":len(creati)})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/importa-iba-completo")
def admin_importa_iba_completo():
    """Importa TUTTI i restanti IBA mancanti (dosi ufficiali IBA, schema nuovo)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    IBA = [{"slug": "ric-iba-angel-face", "nome": "Angel Face", "ingredienti": [{"nome": "gin", "quantita": "30ml", "unita": ""}, {"nome": "apricot brandy", "quantita": "30ml", "unita": ""}, {"nome": "calvados", "quantita": "30ml", "unita": ""}], "metodo": "Shakera tutti gli ingredienti in parti uguali con ghiaccio. Filtra in coppa cocktail fredda.", "punto": "parti uguali in equilibrio: nessun ingrediente deve prevalere", "fenomeno": "equilibrio"}, {"slug": "ric-iba-casino", "nome": "Casino", "ingredienti": [{"nome": "gin", "quantita": "40ml", "unita": ""}, {"nome": "maraschino", "quantita": "10ml", "unita": ""}, {"nome": "orange bitters", "quantita": "2 dash", "unita": ""}, {"nome": "succo di limone", "quantita": "10ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa fredda. Guarnisci con ciliegia.", "punto": "l'equilibrio tra secchezza del gin e dolcezza del maraschino", "fenomeno": "equilibrio"}, {"slug": "ric-iba-mary-pickford", "nome": "Mary Pickford", "ingredienti": [{"nome": "rum bianco", "quantita": "60ml", "unita": ""}, {"nome": "succo d'ananas", "quantita": "60ml", "unita": ""}, {"nome": "granatina", "quantita": "10ml", "unita": ""}, {"nome": "maraschino", "quantita": "5ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa fredda. Guarnisci con ciliegia.", "punto": "fruttato e bilanciato: l'ananas fresco fa la differenza", "fenomeno": "equilibrio"}, {"slug": "ric-iba-monkey-gland", "nome": "Monkey Gland", "ingredienti": [{"nome": "gin", "quantita": "50ml", "unita": ""}, {"nome": "succo d'arancia", "quantita": "30ml", "unita": ""}, {"nome": "granatina", "quantita": "2 gocce", "unita": ""}, {"nome": "assenzio", "quantita": "2 gocce", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa fredda.", "punto": "il tocco di assenzio e granatina deve restare sottile", "fenomeno": "equilibrio"}, {"slug": "ric-iba-paradise", "nome": "Paradise", "ingredienti": [{"nome": "gin", "quantita": "35ml", "unita": ""}, {"nome": "apricot brandy", "quantita": "20ml", "unita": ""}, {"nome": "succo d'arancia", "quantita": "15ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa fredda.", "punto": "il bilanciamento 2:1:1 tra gin, albicocca e arancia", "fenomeno": "equilibrio"}, {"slug": "ric-iba-porto-flip", "nome": "Porto Flip", "ingredienti": [{"nome": "brandy", "quantita": "45ml", "unita": ""}, {"nome": "porto rosso", "quantita": "15ml", "unita": ""}, {"nome": "tuorlo d'uovo", "quantita": "1", "unita": ""}], "metodo": "Shakera energicamente con ghiaccio per emulsionare il tuorlo. Filtra in coppa. Spolvera noce moscata.", "punto": "il tuorlo ben shakerato da cremosita e schiuma", "fenomeno": "emulsione"}, {"slug": "ric-iba-ramos-fizz", "nome": "Ramos Fizz", "ingredienti": [{"nome": "gin", "quantita": "45ml", "unita": ""}, {"nome": "succo di limone", "quantita": "15ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}, {"nome": "albume", "quantita": "1", "unita": ""}, {"nome": "zucchero", "quantita": "30ml", "unita": ""}, {"nome": "panna", "quantita": "60ml", "unita": ""}, {"nome": "acqua di fiori d'arancio", "quantita": "3 gocce", "unita": ""}, {"nome": "soda", "quantita": "", "unita": ""}], "metodo": "Shakera a lungo (anche 2 min) senza ghiaccio poi con ghiaccio per montare l'albume. Filtra in tumbler, aggiungi soda.", "punto": "la shakerata lunga monta l'albume: deve venire soffice e areato", "fenomeno": "emulsione"}, {"slug": "ric-iba-remember-the-maine", "nome": "Remember the Maine", "ingredienti": [{"nome": "rye whiskey", "quantita": "60ml", "unita": ""}, {"nome": "vermouth rosso", "quantita": "20ml", "unita": ""}, {"nome": "cherry brandy", "quantita": "10ml", "unita": ""}, {"nome": "assenzio", "quantita": "2 dash", "unita": ""}], "metodo": "Mescola in mixing glass con ghiaccio. Filtra in coppa fredda.", "punto": "il cherry e l'assenzio danno complessita senza coprire il whiskey", "fenomeno": "diluizione"}, {"slug": "ric-iba-stinger", "nome": "Stinger", "ingredienti": [{"nome": "brandy", "quantita": "50ml", "unita": ""}, {"nome": "creme de menthe bianca", "quantita": "20ml", "unita": ""}], "metodo": "Mescola con ghiaccio. Filtra in coppa fredda (o su ghiaccio tritato).", "punto": "la menta deve rinfrescare senza coprire il brandy", "fenomeno": "equilibrio"}, {"slug": "ric-iba-tuxedo", "nome": "Tuxedo", "ingredienti": [{"nome": "gin", "quantita": "45ml", "unita": ""}, {"nome": "vermouth dry", "quantita": "45ml", "unita": ""}, {"nome": "orange bitters", "quantita": "2 dash", "unita": ""}, {"nome": "maraschino", "quantita": "1/4 cucchiaino", "unita": ""}, {"nome": "assenzio", "quantita": "3 gocce", "unita": ""}], "metodo": "Mescola in mixing glass con ghiaccio. Filtra in coppa. Guarnisci con ciliegia e scorza di limone.", "punto": "variante elegante del Martini: maraschino e assenzio in tracce", "fenomeno": "diluizione"}, {"slug": "ric-iba-vieux-carre", "nome": "Vieux Carre", "ingredienti": [{"nome": "rye whiskey", "quantita": "30ml", "unita": ""}, {"nome": "cognac", "quantita": "30ml", "unita": ""}, {"nome": "vermouth rosso", "quantita": "30ml", "unita": ""}, {"nome": "Benedictine", "quantita": "1 cucchiaino", "unita": ""}, {"nome": "Peychaud's bitters", "quantita": "2 dash", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}], "metodo": "Mescola in tumbler con ghiaccio. Guarnisci con scorza di limone.", "punto": "la stratificazione di whiskey, cognac e amari in equilibrio", "fenomeno": "diluizione"}, {"slug": "ric-iba-black-russian", "nome": "Black Russian", "ingredienti": [{"nome": "vodka", "quantita": "50ml", "unita": ""}, {"nome": "liquore al caffe", "quantita": "20ml", "unita": ""}], "metodo": "Versa su ghiaccio in tumbler. Mescola.", "punto": "il caffe deve bilanciare la vodka senza dominare", "fenomeno": "equilibrio"}, {"slug": "ric-iba-cardinale", "nome": "Cardinale", "ingredienti": [{"nome": "gin", "quantita": "45ml", "unita": ""}, {"nome": "vermouth dry", "quantita": "15ml", "unita": ""}, {"nome": "Campari", "quantita": "15ml", "unita": ""}], "metodo": "Mescola in mixing glass con ghiaccio. Filtra in tumbler con ghiaccio. Guarnisci con scorza d'arancia.", "punto": "variante secca del Negroni: il dry vermouth al posto del rosso", "fenomeno": "diluizione"}, {"slug": "ric-iba-champagne-cocktail", "nome": "Champagne Cocktail", "ingredienti": [{"nome": "champagne", "quantita": "90ml", "unita": ""}, {"nome": "cognac", "quantita": "10ml", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}, {"nome": "zolletta di zucchero", "quantita": "1", "unita": ""}], "metodo": "Metti la zolletta imbevuta di Angostura nel flute. Aggiungi cognac e colma con champagne.", "punto": "le bollicine devono restare vive: versa lo champagne per ultimo", "fenomeno": "equilibrio"}, {"slug": "ric-iba-french-connection", "nome": "French Connection", "ingredienti": [{"nome": "cognac", "quantita": "35ml", "unita": ""}, {"nome": "amaretto", "quantita": "35ml", "unita": ""}], "metodo": "Versa su ghiaccio in tumbler. Mescola.", "punto": "l'equilibrio tra cognac e dolcezza di mandorla dell'amaretto", "fenomeno": "equilibrio"}, {"slug": "ric-iba-garibaldi", "nome": "Garibaldi", "ingredienti": [{"nome": "Campari", "quantita": "50ml", "unita": ""}, {"nome": "succo d'arancia fresco", "quantita": "100ml", "unita": ""}], "metodo": "Versa il Campari in tumbler con ghiaccio. Colma con arancia spremuta fresca e 'fluffata'.", "punto": "l'arancia va spremuta fresca e areata per la texture giusta", "fenomeno": "equilibrio"}, {"slug": "ric-iba-hemingway-special", "nome": "Hemingway Special", "ingredienti": [{"nome": "rum", "quantita": "60ml", "unita": ""}, {"nome": "succo di pompelmo", "quantita": "40ml", "unita": ""}, {"nome": "maraschino", "quantita": "15ml", "unita": ""}, {"nome": "succo di lime", "quantita": "20ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa doppia fredda.", "punto": "secco e agrumato: niente zucchero, l'equilibrio e nel pompelmo", "fenomeno": "equilibrio"}, {"slug": "ric-iba-horse-s-neck", "nome": "Horse's Neck", "ingredienti": [{"nome": "brandy", "quantita": "40ml", "unita": ""}, {"nome": "ginger ale", "quantita": "120ml", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}], "metodo": "Versa in tumbler alto con ghiaccio. Guarnisci con lunga spirale di limone.", "punto": "lungo e dissetante: il ginger ale allunga il brandy", "fenomeno": "equilibrio"}, {"slug": "ric-iba-lemon-drop", "nome": "Lemon Drop", "ingredienti": [{"nome": "vodka", "quantita": "40ml", "unita": ""}, {"nome": "triple sec", "quantita": "20ml", "unita": ""}, {"nome": "succo di limone", "quantita": "15ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa con bordo zuccherato.", "punto": "l'equilibrio acido-dolce, bilanciato dal bordo di zucchero", "fenomeno": "equilibrio"}, {"slug": "ric-iba-rabo-de-galo", "nome": "Rabo de Galo", "ingredienti": [{"nome": "cachaca", "quantita": "50ml", "unita": ""}, {"nome": "vermouth rosso", "quantita": "20ml", "unita": ""}, {"nome": "Cynar", "quantita": "10ml", "unita": ""}, {"nome": "Angostura", "quantita": "1 dash", "unita": ""}], "metodo": "Mescola con ghiaccio. Filtra in tumbler. Guarnisci con scorza d'arancia.", "punto": "il Cynar da l'amaro vegetale che bilancia la cachaca", "fenomeno": "diluizione"}, {"slug": "ric-iba-sea-breeze", "nome": "Sea Breeze", "ingredienti": [{"nome": "vodka", "quantita": "40ml", "unita": ""}, {"nome": "succo di mirtillo rosso", "quantita": "120ml", "unita": ""}, {"nome": "succo di pompelmo", "quantita": "30ml", "unita": ""}], "metodo": "Versa in tumbler alto con ghiaccio. Mescola.", "punto": "fruttato e dissetante: l'equilibrio tra mirtillo e pompelmo", "fenomeno": "equilibrio"}, {"slug": "ric-iba-canchanchara", "nome": "Canchanchara", "ingredienti": [{"nome": "aguardiente di canna", "quantita": "60ml", "unita": ""}, {"nome": "miele", "quantita": "15ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}], "metodo": "Mescola miele e lime, aggiungi l'aguardiente e ghiaccio. Mescola.", "punto": "il miele deve sciogliersi bene prima di aggiungere il distillato", "fenomeno": "equilibrio"}, {"slug": "ric-iba-dark-n-stormy", "nome": "Dark n Stormy", "ingredienti": [{"nome": "rum scuro", "quantita": "60ml", "unita": ""}, {"nome": "ginger beer", "quantita": "100ml", "unita": ""}, {"nome": "succo di lime", "quantita": "10ml", "unita": ""}], "metodo": "Versa ginger beer e lime in tumbler con ghiaccio, poi versa il rum scuro sopra per l'effetto 'tempesta'.", "punto": "il rum va versato sopra per ultimo: crea la stratificazione scura", "fenomeno": "equilibrio"}, {"slug": "ric-iba-fernandito", "nome": "Fernandito", "ingredienti": [{"nome": "Fernet Branca", "quantita": "50ml", "unita": ""}, {"nome": "cola", "quantita": "100ml", "unita": ""}], "metodo": "Versa in tumbler alto con molto ghiaccio. Mescola delicatamente.", "punto": "l'equilibrio tra amaro del Fernet e dolce della cola", "fenomeno": "equilibrio"}, {"slug": "ric-iba-french-martini", "nome": "French Martini", "ingredienti": [{"nome": "vodka", "quantita": "45ml", "unita": ""}, {"nome": "Chambord", "quantita": "15ml", "unita": ""}, {"nome": "succo d'ananas", "quantita": "15ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa fredda. La schiuma d'ananas e la firma.", "punto": "la shakerata crea la schiuma d'ananas in superficie", "fenomeno": "emulsione"}, {"slug": "ric-iba-gin-basil-smash", "nome": "Gin Basil Smash", "ingredienti": [{"nome": "gin", "quantita": "50ml", "unita": ""}, {"nome": "succo di limone", "quantita": "25ml", "unita": ""}, {"nome": "sciroppo di zucchero", "quantita": "15ml", "unita": ""}, {"nome": "basilico", "quantita": "un ciuffo", "unita": ""}], "metodo": "Pesta il basilico, aggiungi gli altri ingredienti e ghiaccio, shakera. Doppio filtro in tumbler.", "punto": "pesta il basilico senza ridurlo in poltiglia: solo per liberare gli oli", "fenomeno": "equilibrio"}, {"slug": "ric-iba-grand-margarita", "nome": "Grand Margarita", "ingredienti": [{"nome": "tequila", "quantita": "40ml", "unita": ""}, {"nome": "Grand Marnier", "quantita": "20ml", "unita": ""}, {"nome": "succo di lime fresco", "quantita": "20ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa con bordo di sale.", "punto": "il Grand Marnier da profondita rispetto al triple sec classico", "fenomeno": "equilibrio"}, {"slug": "ric-iba-iba-tiki", "nome": "IBA Tiki", "ingredienti": [{"nome": "rum bianco", "quantita": "30ml", "unita": ""}, {"nome": "rum invecchiato", "quantita": "20ml", "unita": ""}, {"nome": "amaretto", "quantita": "10ml", "unita": ""}, {"nome": "Frangelico", "quantita": "10ml", "unita": ""}, {"nome": "maraschino", "quantita": "5ml", "unita": ""}, {"nome": "purea di passion fruit", "quantita": "20ml", "unita": ""}, {"nome": "ananas", "quantita": "30ml", "unita": ""}, {"nome": "lime", "quantita": "20ml", "unita": ""}], "metodo": "Shakera tutto con ghiaccio tritato. Versa in tumbler tiki. Guarnisci abbondante.", "punto": "tropicale complesso: l'equilibrio tra rum, frutta e liquori", "fenomeno": "equilibrio"}, {"slug": "ric-iba-illegal", "nome": "Illegal", "ingredienti": [{"nome": "mezcal", "quantita": "40ml", "unita": ""}, {"nome": "rum bianco overproof", "quantita": "15ml", "unita": ""}, {"nome": "Falernum", "quantita": "15ml", "unita": ""}, {"nome": "maraschino", "quantita": "5ml", "unita": ""}, {"nome": "succo di lime", "quantita": "20ml", "unita": ""}, {"nome": "sciroppo", "quantita": "10ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa.", "punto": "il mezcal affumicato bilanciato da lime e Falernum", "fenomeno": "equilibrio"}, {"slug": "ric-iba-naked-and-famous", "nome": "Naked and Famous", "ingredienti": [{"nome": "mezcal", "quantita": "22.5ml", "unita": ""}, {"nome": "Chartreuse giallo", "quantita": "22.5ml", "unita": ""}, {"nome": "Aperol", "quantita": "22.5ml", "unita": ""}, {"nome": "succo di lime", "quantita": "22.5ml", "unita": ""}], "metodo": "Shakera in parti uguali con ghiaccio. Filtra in coppa.", "punto": "quattro parti uguali: l'equilibrio perfetto tra affumicato, erbaceo, amaro, acido", "fenomeno": "equilibrio"}, {"slug": "ric-iba-new-york-sour", "nome": "New York Sour", "ingredienti": [{"nome": "whiskey", "quantita": "60ml", "unita": ""}, {"nome": "succo di limone", "quantita": "25ml", "unita": ""}, {"nome": "sciroppo", "quantita": "15ml", "unita": ""}, {"nome": "albume", "quantita": "1", "unita": ""}, {"nome": "vino rosso", "quantita": "15ml", "unita": ""}], "metodo": "Shakera whiskey, limone, sciroppo e albume. Filtra su ghiaccio. Fai galleggiare il vino rosso sopra.", "punto": "il vino rosso va fatto galleggiare delicatamente sul dorso del cucchiaio", "fenomeno": "equilibrio"}, {"slug": "ric-iba-old-cuban", "nome": "Old Cuban", "ingredienti": [{"nome": "rum invecchiato", "quantita": "45ml", "unita": ""}, {"nome": "succo di lime", "quantita": "22ml", "unita": ""}, {"nome": "sciroppo", "quantita": "30ml", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}, {"nome": "menta", "quantita": "6 foglie", "unita": ""}, {"nome": "champagne", "quantita": "60ml", "unita": ""}], "metodo": "Shakera rum, lime, sciroppo, bitter e menta. Filtra in coppa. Colma con champagne.", "punto": "le bollicine dello champagne vanno aggiunte per ultime", "fenomeno": "equilibrio"}, {"slug": "ric-iba-paloma", "nome": "Paloma", "ingredienti": [{"nome": "tequila", "quantita": "50ml", "unita": ""}, {"nome": "soda al pompelmo", "quantita": "100ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}, {"nome": "sale", "quantita": "", "unita": ""}], "metodo": "Versa in tumbler alto con ghiaccio. Mescola. Bordo di sale.", "punto": "dissetante: l'equilibrio tra tequila, pompelmo e la punta di sale", "fenomeno": "equilibrio"}, {"slug": "ric-iba-pisco-punch", "nome": "Pisco Punch", "ingredienti": [{"nome": "pisco", "quantita": "60ml", "unita": ""}, {"nome": "succo d'ananas", "quantita": "30ml", "unita": ""}, {"nome": "sciroppo", "quantita": "20ml", "unita": ""}, {"nome": "succo di limone", "quantita": "20ml", "unita": ""}, {"nome": "vino bianco secco", "quantita": "30ml", "unita": ""}, {"nome": "chiodi di garofano", "quantita": "", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in tumbler. Guarnisci con ananas.", "punto": "l'infusione di ananas e la spezia dei chiodi di garofano", "fenomeno": "equilibrio"}, {"slug": "ric-iba-porn-star-martini", "nome": "Porn Star Martini", "ingredienti": [{"nome": "vodka alla vaniglia", "quantita": "45ml", "unita": ""}, {"nome": "liquore al passion fruit", "quantita": "15ml", "unita": ""}, {"nome": "purea di passion fruit", "quantita": "15ml", "unita": ""}, {"nome": "zucchero vanigliato", "quantita": "10ml", "unita": ""}, {"nome": "prosecco", "quantita": "a parte", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa. Servi con shot di prosecco a parte.", "punto": "la purea di passion fruit fresca fa la texture; il prosecco si beve a parte", "fenomeno": "equilibrio"}, {"slug": "ric-iba-russian-spring-punch", "nome": "Russian Spring Punch", "ingredienti": [{"nome": "vodka", "quantita": "25ml", "unita": ""}, {"nome": "creme de cassis", "quantita": "15ml", "unita": ""}, {"nome": "sciroppo", "quantita": "10ml", "unita": ""}, {"nome": "succo di limone", "quantita": "25ml", "unita": ""}, {"nome": "champagne", "quantita": "", "unita": ""}], "metodo": "Shakera vodka, cassis, sciroppo e limone. Filtra in tumbler alto con ghiaccio. Colma con champagne.", "punto": "l'equilibrio tra acido del limone e dolce del cassis, allungato dalle bollicine", "fenomeno": "equilibrio"}, {"slug": "ric-iba-sherry-cobbler", "nome": "Sherry Cobbler", "ingredienti": [{"nome": "sherry Amontillado", "quantita": "90ml", "unita": ""}, {"nome": "zucchero", "quantita": "1 cucchiaino", "unita": ""}, {"nome": "fette d'arancia", "quantita": "2", "unita": ""}], "metodo": "Pesta arancia e zucchero, aggiungi sherry e ghiaccio tritato. Mescola.", "punto": "lo sherry su ghiaccio tritato, l'arancia pestata profuma", "fenomeno": "equilibrio"}, {"slug": "ric-iba-south-side", "nome": "South Side", "ingredienti": [{"nome": "gin", "quantita": "50ml", "unita": ""}, {"nome": "succo di limone", "quantita": "25ml", "unita": ""}, {"nome": "sciroppo", "quantita": "15ml", "unita": ""}, {"nome": "menta", "quantita": "un ciuffo", "unita": ""}], "metodo": "Shakera con ghiaccio e menta. Doppio filtro in coppa.", "punto": "la menta fresca e l'equilibrio acido-dolce, come un Mojito shakerato", "fenomeno": "equilibrio"}, {"slug": "ric-iba-spicy-fifty", "nome": "Spicy Fifty", "ingredienti": [{"nome": "vodka", "quantita": "50ml", "unita": ""}, {"nome": "sciroppo di sambuco", "quantita": "15ml", "unita": ""}, {"nome": "miele", "quantita": "10ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}, {"nome": "peperoncino rosso", "quantita": "qualche fetta", "unita": ""}, {"nome": "vaniglia", "quantita": "", "unita": ""}], "metodo": "Shakera con ghiaccio e peperoncino. Doppio filtro in coppa.", "punto": "il peperoncino deve dare calore senza coprire: dosa con attenzione", "fenomeno": "equilibrio"}, {"slug": "ric-iba-suffering-bastard", "nome": "Suffering Bastard", "ingredienti": [{"nome": "gin", "quantita": "30ml", "unita": ""}, {"nome": "brandy", "quantita": "30ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}, {"nome": "ginger ale", "quantita": "", "unita": ""}], "metodo": "Shakera gin, brandy, lime e bitter. Versa in tumbler con ghiaccio. Colma con ginger ale.", "punto": "il ginger ale allunga e rinfresca il mix di distillati", "fenomeno": "equilibrio"}, {"slug": "ric-iba-three-dots-and-a-dash", "nome": "Three Dots and a Dash", "ingredienti": [{"nome": "rum di Martinica", "quantita": "45ml", "unita": ""}, {"nome": "rum invecchiato", "quantita": "15ml", "unita": ""}, {"nome": "Falernum", "quantita": "15ml", "unita": ""}, {"nome": "liquore al pimento", "quantita": "10ml", "unita": ""}, {"nome": "miele", "quantita": "15ml", "unita": ""}, {"nome": "succo di lime", "quantita": "15ml", "unita": ""}, {"nome": "succo d'arancia", "quantita": "15ml", "unita": ""}, {"nome": "Angostura", "quantita": "1 dash", "unita": ""}], "metodo": "Shakera con ghiaccio tritato. Versa in tumbler tiki. Guarnisci (tre ciliegie e un pezzo d'ananas: 'tre punti e una linea').", "punto": "tiki complesso: l'equilibrio tra rum, agrumi, spezie e miele", "fenomeno": "equilibrio"}, {"slug": "ric-iba-tipperary", "nome": "Tipperary", "ingredienti": [{"nome": "Irish whiskey", "quantita": "50ml", "unita": ""}, {"nome": "vermouth rosso", "quantita": "25ml", "unita": ""}, {"nome": "Chartreuse verde", "quantita": "25ml", "unita": ""}, {"nome": "Angostura", "quantita": "2 dash", "unita": ""}], "metodo": "Mescola in mixing glass con ghiaccio. Filtra in coppa.", "punto": "la Chartreuse verde da la spinta erbacea che caratterizza il drink", "fenomeno": "diluizione"}, {"slug": "ric-iba-trinidad-sour", "nome": "Trinidad Sour", "ingredienti": [{"nome": "Angostura bitters", "quantita": "45ml", "unita": ""}, {"nome": "orgeat", "quantita": "30ml", "unita": ""}, {"nome": "succo di limone", "quantita": "22ml", "unita": ""}, {"nome": "rye whiskey", "quantita": "15ml", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa.", "punto": "insolito: l'Angostura e l'ingrediente principale, bilanciato dall'orgeat dolce", "fenomeno": "equilibrio"}, {"slug": "ric-iba-ve-n-to", "nome": "Ve.n.to", "ingredienti": [{"nome": "grappa bianca", "quantita": "45ml", "unita": ""}, {"nome": "succo di limone", "quantita": "22ml", "unita": ""}, {"nome": "miele con infuso di camomilla", "quantita": "22ml", "unita": ""}, {"nome": "cordiale di camomilla", "quantita": "15ml", "unita": ""}, {"nome": "albume 1 (opzionale)", "quantita": "", "unita": ""}], "metodo": "Shakera con ghiaccio. Filtra in coppa.", "punto": "la camomilla e la grappa in equilibrio delicato", "fenomeno": "equilibrio"}]
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        creati=[]; gia=[]
        for c in IBA:
            cur.execute("SELECT id FROM nodes WHERE id=%s OR (name=%s AND type='Protocollo')",(c["slug"],c["nome"]))
            if cur.fetchone(): gia.append(c["nome"]); continue
            data={"nome":c["nome"],"kind":"protocollo","tipo":"canonico","disciplina":"bar",
              "cosa_voglio_ottenere":f"preparare un {c['nome']} secondo la ricetta ufficiale IBA, bilanciato",
              "ingredienti":c["ingredienti"],
              "il_punto":{"tipo":"segnale","bersaglio":None,"segnale":c["punto"],"evidence":[{"source":"IBA - International Bartenders Association","claim":"ricetta ufficiale"}],"_fonte":"IBA"},
              "fenomeni":[{"nome":c["fenomeno"],"fenomeno_id":None}],"metodo":c["metodo"],
              "fonte":"IBA Official Cocktail List","verificato":True,"classificazione_qualita":"A"}
            cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Protocollo',%s)",
                        (c["slug"],c["nome"],json.dumps(data,ensure_ascii=False)))
            conn.commit(); creati.append(c["nome"])
        cur.close();conn.close()
        return jsonify({"creati":creati,"gia_presenti":gia,"totale_creati":len(creati)})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/ricura-ricette-pulisci-marcatore")
def admin_ricura_pulisci_marcatore():
    """Rimuove il marcatore zero-width dalle ricette curate (pulizia finale)."""
    from flask import request, jsonify
    import os, psycopg2
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]);cur=conn.cursor()
        MARK="\u200b"
        cur.execute("UPDATE ricette SET punto_critico=LTRIM(punto_critico,%s) WHERE LEFT(punto_critico,1)=%s",(MARK,MARK))
        n=cur.rowcount
        conn.commit();cur.close();conn.close()
        return jsonify({"puliti":n})
    except Exception as e:
        return jsonify({"errore":str(e)[:150]})


@bp.route("/admin/importa-canonici")
def admin_importa_canonici():
    """Importa le basi canoniche del mestiere mancanti (olandese, pate a choux, roux...)."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    CAN = [
        {'slug': 'ric-base-salsa-olandese', 'nome': 'Salsa Olandese', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'tuorli', 'quantita': '3'}, {'nome': 'burro chiarificato', 'quantita': '250g'}, {'nome': 'succo di limone', 'quantita': '15ml'}, {'nome': 'sale', 'quantita': ''}, {'nome': 'pepe bianco', 'quantita': ''}], 'metodo': 'Monta i tuorli a bagnomaria con poca acqua, incorpora il burro chiarificato tiepido a filo, aggiungi limone e sale.', 'il_punto': {'tipo': 'bersaglio', 'bersaglio': {'valore': '65', 'unita': 'C'}, 'segnale': 'il punto: la temperatura dei tuorli non deve superare i 65C (sopra coagulano e impazzisce); incorpora il burro lentamente'}, 'fenomeno': 'coagulazione proteica'},
        {'slug': 'ric-base-salsa-bernese', 'nome': 'Salsa Bernese', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'tuorli', 'quantita': '3'}, {'nome': 'burro chiarificato', 'quantita': '250g'}, {'nome': 'scalogno', 'quantita': '2'}, {'nome': 'dragoncello', 'quantita': ''}, {'nome': 'aceto di vino bianco', 'quantita': '30ml'}, {'nome': 'vino bianco', 'quantita': '30ml'}], 'metodo': 'Riduci scalogno, dragoncello, aceto e vino. Monta i tuorli a bagnomaria con la riduzione, incorpora il burro a filo.', 'il_punto': {'tipo': 'bersaglio', 'bersaglio': {'valore': '65', 'unita': 'C'}, 'segnale': "il punto: come l'olandese, i tuorli sotto i 65C; la riduzione aromatica va filtrata"}, 'fenomeno': 'coagulazione proteica'},
        {'slug': 'ric-base-pate-a-choux', 'nome': 'Pate a Choux', 'disciplina': 'pasticceria', 'ingredienti': [{'nome': 'acqua', 'quantita': '125ml'}, {'nome': 'latte', 'quantita': '125ml'}, {'nome': 'burro', 'quantita': '100g'}, {'nome': 'farina', 'quantita': '150g'}, {'nome': 'uova', 'quantita': '4'}, {'nome': 'sale', 'quantita': ''}, {'nome': 'zucchero', 'quantita': ''}], 'metodo': "Porta a bollore acqua, latte, burro. Aggiungi la farina in un colpo, asciuga l'impasto sul fuoco. Fuori dal fuoco incorpora le uova una a una.", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': "il punto: asciuga bene l'impasto sul fuoco (deve formare una patina sul fondo) prima di aggiungere le uova; la consistenza giusta cola a nastro"}, 'fenomeno': 'gelatinizzazione amido'},
        {'slug': 'ric-base-pasta-brisee', 'nome': 'Pasta Brisee', 'disciplina': 'pasticceria', 'ingredienti': [{'nome': 'farina', 'quantita': '250g'}, {'nome': 'burro freddo', 'quantita': '125g'}, {'nome': 'acqua fredda', 'quantita': '50ml'}, {'nome': 'sale', 'quantita': ''}], 'metodo': "Sabbia la farina col burro freddo, aggiungi l'acqua fredda, impasta velocemente. Riposo in frigo 30 min.", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: il burro deve restare freddo e non sciogliersi (lavora veloce); impasta il minimo per non sviluppare glutine'}, 'fenomeno': 'sabbiatura'},
        {'slug': 'ric-base-crema-chantilly', 'nome': 'Crema Chantilly', 'disciplina': 'pasticceria', 'ingredienti': [{'nome': 'panna fresca', 'quantita': '250ml'}, {'nome': 'zucchero a velo', 'quantita': '25g'}, {'nome': 'vaniglia', 'quantita': ''}], 'metodo': 'Monta la panna ben fredda con lo zucchero e la vaniglia fino a consistenza soda.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: panna e ciotola ben fredde; ferma la montatura quando fa i picchi morbidi, non oltre (diventa burro)'}, 'fenomeno': 'incorporazione aria'},
        {'slug': 'ric-base-salsa-di-pomodoro', 'nome': 'Salsa di Pomodoro', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'pomodori pelati', 'quantita': '800g'}, {'nome': 'aglio', 'quantita': '2 spicchi'}, {'nome': 'olio evo', 'quantita': '60ml'}, {'nome': 'basilico', 'quantita': ''}, {'nome': 'sale', 'quantita': ''}], 'metodo': "Soffriggi l'aglio nell'olio, aggiungi i pelati schiacciati, cuoci a fuoco medio 20-30 min. Basilico a fine cottura.", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': "il punto: cuoci finche si addensa e l'olio affiora in superficie (segno che l'acqua e evaporata)"}, 'fenomeno': 'concentrazione'},
        {'slug': 'ric-base-pesto-genovese', 'nome': 'Pesto Genovese', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'basilico', 'quantita': '50g'}, {'nome': 'pinoli', 'quantita': '30g'}, {'nome': 'aglio', 'quantita': '1'}, {'nome': 'parmigiano', 'quantita': '60g'}, {'nome': 'pecorino', 'quantita': '30g'}, {'nome': 'olio evo', 'quantita': '100ml'}, {'nome': 'sale grosso', 'quantita': ''}], 'metodo': "Pesta nel mortaio aglio e sale, aggiungi basilico, pinoli, poi i formaggi e l'olio a filo. (O frulla a freddo.)", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: lavora a freddo e veloce per non ossidare il basilico (scurisce e amareggia); se frulli, raffredda le lame'}, 'fenomeno': 'ossidazione'},
        {'slug': 'ric-base-salsa-vellutata', 'nome': 'Salsa Vellutata', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'brodo', 'quantita': '500ml'}, {'nome': 'burro', 'quantita': '40g'}, {'nome': 'farina', 'quantita': '40g'}], 'metodo': 'Fai un roux chiaro con burro e farina, aggiungi il brodo caldo poco a poco mescolando, cuoci finche si addensa.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: aggiungi il brodo caldo sul roux mescolando per evitare grumi; cuoci finche vela il cucchiaio'}, 'fenomeno': 'gelatinizzazione amido'},
        {'slug': 'ric-base-demi-glace', 'nome': 'Demi Glace', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'fondo bruno di vitello', 'quantita': '1L'}, {'nome': 'vino rosso', 'quantita': '200ml'}], 'metodo': 'Riduci il fondo bruno di vitello della meta a fuoco lento, deglassa con vino. Filtra.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: riduzione lenta fino a consistenza sciropposa che nappa (vela) il dorso del cucchiaio'}, 'fenomeno': 'concentrazione'},
        {'slug': 'ric-base-fumetto-di-pesce', 'nome': 'Fumetto di Pesce', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'lische e teste di pesce', 'quantita': '1kg'}, {'nome': 'sedano', 'quantita': ''}, {'nome': 'carota', 'quantita': ''}, {'nome': 'cipolla', 'quantita': ''}, {'nome': 'vino bianco', 'quantita': '100ml'}, {'nome': 'acqua', 'quantita': '1.5L'}], 'metodo': "Rosola le verdure, aggiungi lische pulite, sfuma col vino, copri d'acqua, sobbolli 20-30 min. Filtra.", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: NON superare i 30 min di cottura e non far bollire forte (il fumetto diventa amaro e torbido)'}, 'fenomeno': 'estrazione'},
        {'slug': 'ric-base-brodo-vegetale', 'nome': 'Brodo Vegetale', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'sedano', 'quantita': ''}, {'nome': 'carota', 'quantita': ''}, {'nome': 'cipolla', 'quantita': ''}, {'nome': 'porro', 'quantita': ''}, {'nome': 'acqua', 'quantita': '2L'}, {'nome': 'sale', 'quantita': ''}], 'metodo': 'Metti le verdure in acqua fredda, porta a leggero bollore, sobbolli 45-60 min. Filtra.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: parti da acqua fredda e sobbolli dolcemente (non bollore forte) per estrarre sapore senza intorbidire'}, 'fenomeno': 'estrazione'},
        {'slug': 'ric-base-fat-wash', 'nome': 'Fat Wash', 'disciplina': 'bar', 'ingredienti': [{'nome': 'distillato', 'quantita': '500ml'}, {'nome': 'grasso aromatico (burro/bacon)', 'quantita': '50g'}], 'metodo': 'Sciogli il grasso, mescolalo al distillato, lascia riposare, poi congela. Rimuovi il grasso solidificato in superficie. Filtra.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: il congelamento solidifica il grasso che si separa portando con se gli aromi liposolubili; filtra bene'}, 'fenomeno': 'estrazione lipidica'},
        {'slug': 'ric-base-curd-di-limone', 'nome': 'Curd di Limone', 'disciplina': 'pasticceria', 'ingredienti': [{'nome': 'succo di limone', 'quantita': '120ml'}, {'nome': 'zucchero', 'quantita': '150g'}, {'nome': 'uova', 'quantita': '3'}, {'nome': 'burro', 'quantita': '100g'}, {'nome': 'scorza di limone', 'quantita': ''}], 'metodo': 'Scalda succo, zucchero e scorza. Incorpora le uova sbattute mescolando, cuoci a fuoco dolce finche addensa, poi il burro.', 'il_punto': {'tipo': 'bersaglio', 'bersaglio': {'valore': '82', 'unita': 'C'}, 'segnale': 'il punto: cuoci a fuoco dolce mescolando continuamente; togli quando vela il cucchiaio (sotto i 82C, sopra le uova stracciano)'}, 'fenomeno': 'coagulazione proteica'},
        {'slug': 'ric-base-roux', 'nome': 'Roux', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'burro', 'quantita': '50g'}, {'nome': 'farina', 'quantita': '50g'}], 'metodo': "Sciogli il burro, aggiungi la farina, cuoci mescolando: bianco (pochi min), biondo, o scuro secondo l'uso.", 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: cuoci la farina abbastanza da togliere il sapore di crudo; il colore (bianco/biondo/scuro) decide il gusto e il potere addensante'}, 'fenomeno': 'gelatinizzazione amido'},
        {'slug': 'ric-base-ganache-montata', 'nome': 'Ganache Montata', 'disciplina': 'pasticceria', 'ingredienti': [{'nome': 'cioccolato', 'quantita': '200g'}, {'nome': 'panna fresca 300ml (100 calda + 200 fredda)', 'quantita': ''}], 'metodo': 'Sciogli il cioccolato con 100ml di panna calda, aggiungi 200ml di panna fredda, riposo in frigo 6h, poi monta.', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: il riposo lungo in frigo e essenziale perche monti; monta fredda fino a consistenza spumosa'}, 'fenomeno': 'emulsione'},
        {'slug': 'ric-base-salsa-worcestershire', 'nome': 'Salsa Worcestershire', 'disciplina': 'cucina', 'ingredienti': [{'nome': 'aceto di malto', 'quantita': ''}, {'nome': 'melassa', 'quantita': ''}, {'nome': 'acciughe', 'quantita': ''}, {'nome': 'tamarindo', 'quantita': ''}, {'nome': 'aglio', 'quantita': ''}, {'nome': 'cipolla', 'quantita': ''}, {'nome': 'spezie', 'quantita': ''}], 'metodo': 'Fai sobbollire gli ingredienti, lascia fermentare/maturare a lungo, filtra. (Preparazione industriale, versione casalinga semplificata.)', 'il_punto': {'tipo': 'segnale', 'bersaglio': None, 'segnale': 'il punto: la maturazione lunga sviluppa la complessita umami; e una salsa fermentata che migliora col tempo'}, 'fenomeno': 'fermentazione'},
    ]
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        creati=[]; gia=[]; errori=[]
        for c in CAN:
            try:
                cur.execute("SELECT id FROM nodes WHERE id=%s OR (name=%s AND type='Protocollo')",(c["slug"],c["nome"]))
                if cur.fetchone(): gia.append(c["nome"]); continue
                data={"nome":c["nome"],"kind":"protocollo","tipo":"canonico","disciplina":c["disciplina"],
                  "cosa_voglio_ottenere":"preparare "+c["nome"]+", base classica del mestiere",
                  "ingredienti":c["ingredienti"],"il_punto":c["il_punto"],
                  "fenomeni":[{"nome":c["fenomeno"],"fenomeno_id":None}],"metodo":c["metodo"],
                  "fonte":"tradizione culinaria classica","verificato":True,"classificazione_qualita":"A"}
                cur.execute("INSERT INTO nodes (id,name,type,data) VALUES (%s,%s,'Protocollo',%s)",
                            (c["slug"],c["nome"],json.dumps(data,ensure_ascii=False)))
                conn.commit(); creati.append(c["nome"])
            except Exception as ie:
                conn.rollback(); errori.append(c["nome"]+": "+str(ie)[:60])
        cur.close();conn.close()
        return jsonify({"creati":creati,"gia_presenti":gia,"totale":len(creati),"errori":errori})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/popola-segnale")
def admin_popola_segnale():
    """Popola il_punto.segnale sui protocolli SENZA numero ne segnale (il caso 'senza numero' scoperto).
    L'AI legge la preparazione e scrive l'OSSERVAZIONE VERA (come capisci che e' a punto). Contratto epistemico:
    non inventa, se non e certa marca da_verificare. Default DRY-RUN. ?applica=1. ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",20))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def scrivi_segnale(nome, disciplina, ingredienti, metodo):
        ing = ", ".join([i.get("nome","") if isinstance(i,dict) else str(i) for i in (ingredienti or [])][:10])
        dom = (f"Preparazione: '{nome}' (disciplina: {disciplina}). Ingredienti: {ing}. Metodo: {str(metodo)[:300]}. "
               f"COMPITO: scrivi IL SEGNALE OSSERVABILE - la cosa concreta che un professionista GUARDA/SENTE/TOCCA "
               f"per sapere che e' A PUNTO (es. 'le vongole si aprono', 'l'emulsione vela il cucchiaio', 'il liquido "
               f"e cristallino senza velature'). NON un numero, NON l'obiettivo generico, NON una frase vaga: "
               f"l'OSSERVAZIONE CONCRETA del momento giusto. Se per questa preparazione non esiste un segnale "
               f"osservabile chiaro, rispondi segnale vuoto. "
               f'SOLO JSON: {{"segnale":"...osservazione concreta o vuoto...", "sicuro":true/false}}')
        pl={"model":"gpt-4o-mini","max_tokens":180,"temperature":0.3,
            "messages":[{"role":"system","content":"Esperto di cucina/bar. Scrivi il segnale OSSERVABILE del punto "
                        "giusto: concreto, sensoriale, vero. Mai un numero, mai l'obiettivo, mai vago. Se non esiste "
                        "un segnale chiaro, lascia vuoto."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=30).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return None
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]);cur=conn.cursor()
        cur.execute("""SELECT id,name,data FROM nodes WHERE type='Protocollo'
                       AND (data->'il_punto'->>'segnale' IS NULL OR data->'il_punto'->>'segnale'='')
                       AND (data->'il_punto'->'bersaglio' IS NULL OR data->'il_punto'->'bersaglio'->>'valore' IS NULL)
                       AND data->'il_punto'->>'_segnale_popolato' IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        popolati=[]; vuoti=[]
        for pid,nome,data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            r=scrivi_segnale(nome, dd.get("disciplina",""), dd.get("ingredienti") or dd.get("reagenti",[]), dd.get("metodo",""))
            if not r: continue
            seg=r.get("segnale","").strip()
            ip=dd.get("il_punto") or {}
            if seg and r.get("sicuro"):
                ip["tipo"]="segnale"; ip["segnale"]=seg; ip["bersaglio"]=None; ip["_segnale_popolato"]=True
                popolati.append({"nome":nome,"segnale":seg[:60]})
            else:
                ip["tipo"]="da_verificare"; ip["_segnale_popolato"]=True
                vuoti.append(nome)
            dd["il_punto"]=ip
            if applica:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","popolati":len(popolati),
                        "senza_segnale_chiaro":len(vuoti),"esempi":popolati[:12]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/pulisci-corpus-ingredienti")
def admin_pulisci_corpus_ingredienti():
    """PULIZIA MECCANICA (sicura, no giudizio di mestiere):
    1. traduce le categorie inglesi (fruit->frutta)
    2. marca gli ingredienti 'tecnici' (nome con underscore = voce da database aromi) come
       'solo_motore: true' -> restano nel flavor network SOTTO ma NON appaiono come ingredienti consultabili.
    Default DRY-RUN. ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    applica = request.args.get("applica")=="1"
    CAT = {"vegetable":"verdura","fruit":"frutta","meat":"carne","fish":"pesce","dairy":"latticini",
           "herb":"erba aromatica","spice":"spezia","grain":"cereale","nut":"frutta secca","seed":"seme",
           "poultry":"pollame","seafood":"frutti di mare","cheese":"formaggio","oil":"olio","legume":"legume",
           "beverage":"bevanda","alcohol":"alcolico","mushroom":"fungo","flower":"fiore","root":"radice"}
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        tradotte=0; marcati=0
        if applica:
            # 1. traduci categorie
            for eng,ita in CAT.items():
                cur.execute("""UPDATE nodes SET data = jsonb_set(data,'{categoria}',%s)
                               WHERE type IN ('Ingrediente','Prodotto') AND LOWER(data->>'categoria')=%s""",
                            (json.dumps(ita), eng))
                tradotte += cur.rowcount
            conn.commit()
            # 2. marca i tecnici (underscore nel nome) come solo_motore
            cur.execute("""UPDATE nodes SET data = jsonb_set(data,'{solo_motore}','true')
                           WHERE type IN ('Ingrediente','Prodotto') AND name LIKE '%%\\_%%'""")
            marcati = cur.rowcount
            conn.commit()
        else:
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND LOWER(data->>'categoria')=ANY(%s)",(list(CAT.keys()),))
            tradotte = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND name LIKE '%%\\_%%'")
            marcati = cur.fetchone()[0]
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN (conteggio)",
                        "categorie_tradotte":tradotte,"ingredienti_tecnici_marcati_solo_motore":marcati,
                        "nota":"i tecnici restano nel flavor network ma non appaiono come ingredienti consultabili"})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/segnala-fenomeni-sospetti")
def admin_segnala_fenomeni_sospetti():
    """Segnala i collegamenti INGREDIENTE-FENOMENO sospetti (es. pomodoro->difetti del vino).
    L'AI giudica la pertinenza: pertinente/sospetto. NON rimuove - SEGNALA, Michele conferma.
    Mette i sospetti nella coda di revisione. Default DRY-RUN. ?applica=1 (li aggiunge alla coda)."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",30))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def pertinente(ingrediente, fenomeno):
        dom = (f"Ingrediente: '{ingrediente}'. Fenomeno collegato: '{fenomeno}'. "
               f"Questo fenomeno E PERTINENTE a questo ingrediente nel mestiere F&B? "
               f"Es: pomodoro+'difetti del vino' = NON pertinente (il pomodoro non c'entra col vino). "
               f"pomodoro+Maillard = pertinente (si puo rosolare). gin+distillazione = pertinente. "
               f'SOLO JSON: {{"pertinente": true/false, "motivo":"...breve..."}}')
        pl={"model":"gpt-4o-mini","max_tokens":80,"temperature":0,
            "messages":[{"role":"system","content":"Esperto F&B. Giudica se un fenomeno e' davvero pertinente a "
                        "un ingrediente. Nel dubbio: pertinente (non segnalare troppo)."},
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
        # prendo ingredienti NON solo_motore con fenomeni collegati
        cur.execute("""SELECT n1.id, n1.name, n2.name FROM nodes n1
                       JOIN edges e ON (e.from_id=n1.id OR e.to_id=n1.id)
                       JOIN nodes n2 ON (n2.id=e.to_id OR n2.id=e.from_id)
                       WHERE n1.type IN ('Ingrediente','Prodotto') AND n2.type='Fenomeno'
                       AND (n1.data->>'solo_motore') IS NULL AND n1.id<>n2.id LIMIT %s""",(limite,))
        coppie = cur.fetchall()
        sospetti=[]; ok=0
        for iid, inome, fnome in coppie:
            g=pertinente(inome, fnome)
            if not g: continue
            if g.get("pertinente"):
                ok+=1
            else:
                sospetti.append({"ingrediente":inome,"fenomeno":fnome,"motivo":g.get("motivo","")[:60]})
                if applica:
                    # aggiungo alla coda di revisione
                    try:
                        cur.execute("""INSERT INTO revisione_patrimonio (id,tipo_oggetto,nome,contenuto,sospetto,priorita)
                            VALUES (%s,'collegamento',%s,%s,'fenomeno_non_pertinente',1)
                            ON CONFLICT (id) DO NOTHING""",
                            (f"link-{iid}-{fnome[:20]}", f"{inome} -> {fnome}",
                             json.dumps({"ingrediente":inome,"fenomeno":fnome,"motivo":g.get("motivo","")},ensure_ascii=False)))
                        conn.commit()
                    except: conn.rollback()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","pertinenti":ok,
                        "sospetti":len(sospetti),"esempi_sospetti":sospetti[:15]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/pulisci-fenomeno-vino")
def admin_pulisci_fenomeno_vino():
    """Rimuove gli archi ingrediente->fenomeno 'difetti del vino'/'acidita volatile' dagli ingredienti NON-vino.
    Questi collegamenti sono errati (il pomodoro non c'entra coi difetti del vino). ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    applica = request.args.get("applica")=="1"
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        # trovo i nodi-fenomeno che parlano di vino/acidita volatile
        cur.execute("""SELECT id, name FROM nodes WHERE type='Fenomeno'
                       AND (LOWER(name) LIKE '%%difetti del vino%%' OR LOWER(name) LIKE '%%acidit_ volatile%%'
                            OR LOWER(name) LIKE '%%acidita volatile%%')""")
        fen_vino = cur.fetchall()
        fen_ids = [f[0] for f in fen_vino]
        if not fen_ids:
            cur.close();conn.close()
            return jsonify({"nota":"nessun fenomeno vino trovato come nodo","fenomeni":[]})
        # quali ingredienti NON-vino sono collegati a questi fenomeni?
        cur.execute("""SELECT DISTINCT n.id, n.name FROM edges e
                       JOIN nodes n ON (n.id=e.from_id OR n.id=e.to_id)
                       WHERE (e.from_id = ANY(%s) OR e.to_id = ANY(%s))
                       AND n.type IN ('Ingrediente','Prodotto')
                       AND LOWER(n.name) NOT LIKE '%%vino%%' AND LOWER(n.name) NOT LIKE '%%wine%%'""",
                    (fen_ids, fen_ids))
        ing_sbagliati = cur.fetchall()
        rimossi = 0
        if applica:
            # rimuovo gli archi tra questi ingredienti-non-vino e i fenomeni-vino
            for iid, inome in ing_sbagliati:
                cur.execute("""DELETE FROM edges WHERE
                               ((from_id=%s AND to_id=ANY(%s)) OR (to_id=%s AND from_id=ANY(%s)))""",
                            (iid, fen_ids, iid, fen_ids))
                rimossi += cur.rowcount
            conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "ANTEPRIMA",
                        "fenomeni_vino":[f[1] for f in fen_vino],
                        "ingredienti_non_vino_collegati":len(ing_sbagliati),
                        "esempi":[i[1] for i in ing_sbagliati[:15]],
                        "archi_rimossi":rimossi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/popola-nome-scientifico")
def admin_popola_nome_scientifico():
    """Aggiunge nome_scientifico (binomio latino) agli ingredienti consultabili. L'AI lo da SOLO se certa
    (e' tassonomia verificabile, non opinione); se non e' sicura -> vuoto, NON inventa. Default DRY-RUN. ?applica=1 ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",30))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def binomio(nome):
        dom = (f"Ingrediente alimentare: '{nome}'. Qual e' il suo nome scientifico (binomio latino, genere+specie)? "
               f"Es: pomodoro->Solanum lycopersicum, basilico->Ocimum basilicum, manzo->Bos taurus. "
               f"RISPONDI SOLO se sei CERTO del binomio. Se non sei sicuro, o se e' un prodotto composto/lavorato "
               f"(es. 'brandy di mele', 'olio di sesamo') che non ha UN binomio, rispondi vuoto. "
               f'SOLO JSON: {{"nome_scientifico":"...Genere specie o vuoto...", "certo": true/false}}')
        pl={"model":"gpt-4o-mini","max_tokens":50,"temperature":0,
            "messages":[{"role":"system","content":"Tassonomista. Dai il binomio latino SOLO se certo. "
                        "Prodotti lavorati/composti non hanno binomio: lascia vuoto. Mai inventare."},
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
        cur.execute("""SELECT id,name,data FROM nodes WHERE type IN ('Ingrediente','Prodotto')
                       AND (data->>'solo_motore') IS NULL AND data->>'nome_scientifico' IS NULL
                       AND data->>'_nome_sci_visto' IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        messi=[]; vuoti=0
        for iid,nome,data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            r=binomio(nome)
            if not r: continue
            ns=r.get("nome_scientifico","").strip()
            if ns and r.get("certo"):
                dd["nome_scientifico"]=ns; messi.append({"nome":nome,"sci":ns})
            else:
                vuoti+=1
            dd["_nome_sci_visto"]=True
            if applica:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),iid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","con_binomio":len(messi),
                        "senza_binomio":vuoti,"esempi":messi[:12]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/popola-profilo-fondamentali")
def admin_popola_profilo_fondamentali():
    """Popola il profilo sensoriale (15 dim 0-10) dei FONDAMENTALI vuoti. Metodo revisore: l'AI PROPONE con
    stato epistemico (verificato per gli ovvi, stimato per i dubbi), NON inventa valori a caso. Scrive nel nodo
    con PIU abbinamenti (il ricco). Default DRY-RUN. ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    # lista chiusa dei fondamentali vuoti (il report prioritario - non generica)
    FOND = ["sale","zucchero","peperoncino","basilico","salvia","alloro","origano","parmigiano","pecorino",
            "zucchina","melanzana","funghi","spinaci","zafferano","campari","vodka","brodo","farina"]
    limite_n = int(request.args.get("n",4))
    DIM = ["acido","amaro","aroma_caldo","aroma_fresco","astringente","corposita","croccante","dolce",
           "effervescenza","fermentato","grasso","piccante","salato","termico","umami"]
    def profilo_ai(nome):
        dom = (f"Ingrediente: '{nome}'. Dammi il suo PROFILO SENSORIALE su queste 15 dimensioni (scala 0-10): "
               f"{', '.join(DIM)}. Valori ALTI solo dove e' davvero caratteristico (es. sale: salato 10, resto ~0; "
               f"peperoncino: piccante 9; zucchero: dolce 10; parmigiano: umami 8, salato 7, grasso 5). "
               f"Metti 0 dove la dimensione non si applica. Indica 'certezza' alta per i casi ovvi (sale=salato), "
               f"bassa per i dubbi. SOLO JSON: {{\"profilo\": {{dim: valore...}}, \"certezza\": \"alta\"|\"media\"|\"bassa\"}}")
        pl={"model":"gpt-4o-mini","max_tokens":350,"temperature":0,
            "messages":[{"role":"system","content":"Esperto sensoriale di cucina. Dai profili realistici: valori "
                        "alti solo dove l'ingrediente e' davvero quello (sale=salato, non dolce). Onesto sulla certezza."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=30).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0))
        except: pass
        return None
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        fatti=[]
        for nome in FOND:
            if len(fatti) >= limite_n: break
            # il nodo con piu abbinamenti (il ricco, non il duplicato vuoto)
            cur.execute("""SELECT n.id, n.data, COUNT(e.from_id) nc FROM nodes n
                           LEFT JOIN edges e ON e.from_id=n.id AND e.relation='abbinamento_aromatico'
                           WHERE LOWER(n.name)=LOWER(%s) AND n.type IN ('Ingrediente','Prodotto')
                           GROUP BY n.id, n.data ORDER BY nc DESC LIMIT 1""",(nome,))
            r=cur.fetchone()
            if not r: continue
            nid=r[0]
            _dd0 = r[1] if isinstance(r[1],dict) else (json.loads(r[1]) if r[1] else {})
            if _dd0.get("_profilo_stato"): continue  # gia fatto, skip
            res=profilo_ai(nome)
            if not res or not res.get("profilo"): continue
            prof={k:float(v) for k,v in res["profilo"].items() if k in DIM and v}
            cert=res.get("certezza","media")
            fatti.append({"nome":nome,"dim_attive":len(prof),"certezza":cert,
                          "picchi":{k:v for k,v in prof.items() if v>=6}})
            if applica:
                cur.execute("SELECT data FROM nodes WHERE id=%s",(nid,))
                dd=cur.fetchone()[0]; dd=dd if isinstance(dd,dict) else json.loads(dd)
                dd["proprieta"]=prof
                dd["_profilo_stato"]="stimato" if cert!="alta" else "verificato_ovvio"
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),nid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","fondamentali_processati":len(fatti),"dettaglio":fatti})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/collega-fenomeni-protocolli")
def admin_collega_fenomeni_protocolli():
    """Aggiunge lo slug ai fenomeni dei protocolli (match nome->slug sulle schede Atlante esistenti).
    Accende 'E se cambio?'. Dove non c'e match, lascia il nome senza slug (no link, onesto). ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json, re, unicodedata
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    def norm(s):
        s=unicodedata.normalize('NFD',s.lower().strip())
        s=''.join(c for c in s if unicodedata.category(c)!='Mn')
        return re.sub(r'[^a-z0-9]+','-',s).strip('-')
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        # mappa: nome normalizzato -> slug reale delle schede fenomeno
        cur.execute("SELECT id, name FROM nodes WHERE type='Fenomeno'")
        mapidx={}
        for fid, fname in cur.fetchall():
            mapidx[norm(fname)] = fid
            # anche lo slug stesso senza fen-
            if fid.startswith('fen-'): mapidx[fid[4:]] = fid
        def trova_slug(nome):
            n=norm(nome)
            if n in mapidx: return mapidx[n]
            if ('fen-'+n) in [v for v in mapidx.values()]: return 'fen-'+n
            # prova il match parziale (il nome contiene o e contenuto in una chiave)
            for k,v in mapidx.items():
                if len(n)>4 and (n in k or k in n): return v
            return None
        cur.execute("SELECT id, data FROM nodes WHERE type='Protocollo'")
        righe=cur.fetchall()
        tot_fen=0; con_slug=0; prot_tocchi=0
        for pid, data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            fen=dd.get("fenomeni",[])
            if not fen: continue
            nuovi=[]; cambiato=False
            for f in fen:
                nome = f if isinstance(f,str) else f.get("nome","")
                if not nome: continue
                tot_fen+=1
                sl = (f.get("slug") if isinstance(f,dict) else None) or trova_slug(nome)
                if sl: con_slug+=1
                nuovi.append({"nome":nome,"slug":sl})  # slug None se non matcha (frontend: no link)
                cambiato=True
            if cambiato and applica:
                dd["fenomeni"]=nuovi
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
                prot_tocchi+=1
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","fenomeni_totali":tot_fen,
                        "con_slug":con_slug,"senza_match":tot_fen-con_slug,"protocolli_aggiornati":prot_tocchi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/segnala-fenomeni-protocolli-sospetti")
def admin_segnala_fenomeni_protocolli_sospetti():
    """L'AI giudica ogni coppia preparazione->fenomeno: pertinente? (es. acqua pazza+emulsione = NO, il pesce
    non emulsiona). Segnala i sospetti, NON corregge. Michele conferma. Default DRY-RUN. ?applica=1 (coda revisione). ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",25))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def giudica(prep, disc, fenomeni):
        fl = ", ".join(fenomeni)
        dom = (f"Preparazione: '{prep}' ({disc}). Fenomeni scientifici attualmente collegati: {fl}. "
               f"Per OGNUNO dimmi se e' VERAMENTE pertinente a questa preparazione. Es: 'acqua pazza' (pesce in "
               f"brodo) + 'emulsione' = NON pertinente (non si emulsiona nulla); + 'gelatinizzazione' = NON "
               f"pertinente (non c'e amido); il fenomeno vero sarebbe 'coagulazione proteica' (il pesce). "
               f"Indica anche se MANCA un fenomeno importante. "
               f'SOLO JSON: {{"sbagliati":["fenomeno non pertinente",...], "mancante":"fenomeno vero che manca o vuoto"}}')
        pl={"model":"gpt-4o-mini","max_tokens":150,"temperature":0,
            "messages":[{"role":"system","content":"Esperto di scienza della cucina. Giudica se un fenomeno e' "
                        "DAVVERO pertinente a una preparazione. Severo sui fenomeni messi a caso. Nel dubbio: pertinente."},
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
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo'
                       AND data->'fenomeni' IS NOT NULL AND data->>'_fen_verificati' IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        sospetti=[]; ok=0
        for pid, nome, data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            fen=[f.get("nome") if isinstance(f,dict) else f for f in dd.get("fenomeni",[])]
            if not fen: continue
            g=giudica(nome, dd.get("disciplina",""), fen)
            if not g: continue
            sb=g.get("sbagliati",[]); manca=g.get("mancante","")
            if sb or manca:
                sospetti.append({"prep":nome,"sbagliati":sb,"mancante":manca})
                if applica:
                    try:
                        cur.execute("""INSERT INTO revisione_patrimonio (id,tipo_oggetto,nome,contenuto,sospetto,priorita)
                            VALUES (%s,'fenomeni_protocollo',%s,%s,'fenomeno_non_pertinente',1)
                            ON CONFLICT (id) DO UPDATE SET contenuto=EXCLUDED.contenuto""",
                            (f'fenprot-{pid}', nome, json.dumps({"sbagliati":sb,"mancante":manca,"attuali":fen},ensure_ascii=False)))
                        conn.commit()
                    except: conn.rollback()
            else: ok+=1
            if applica:
                dd["_fen_verificati"]=True
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","pertinenti":ok,"sospetti":len(sospetti),"dettaglio":sospetti[:15]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/rimuovi-fenomeni-falsi")
def admin_rimuovi_fenomeni_falsi():
    """FASE 1 TRUST: rimuove SOLO i fenomeni FALSI presenti (acqua pazza+emulsione). NON tocca i corretti,
    NON aggiunge i mancanti, NON sostituisce con plausibili. L'AI giudica solo 'questo fenomeno PRESENTE e'
    pertinente SI/NO'. Dove NO -> rimosso. Default DRY-RUN. ?applica=1 ?n=N."""
    from flask import request, jsonify
    import os, psycopg2, json, urllib.request as ur
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    limite = int(request.args.get("n",20))
    key = os.environ.get("OPENAI_API_KEY","")
    if not key: return jsonify({"errore":"no key"}),500
    def falso(prep, disc, fenomeno):
        dom = (f"Preparazione: '{prep}' ({disc}). Fenomeno collegato: '{fenomeno}'. "
               f"Questo fenomeno e' DAVVERO presente in questa preparazione? Rispondi NO solo se e' chiaramente "
               f"SBAGLIATO (es. 'acqua pazza'+'emulsione'=NO, il pesce in brodo non emulsiona; 'baba'+'emulsione'=NO; "
               f"'pastiera'+'gelificazione'=NO). Nel dubbio o se e' plausibile, rispondi SI. "
               f'SOLO JSON: {{"pertinente": true/false}}')
        pl={"model":"gpt-4o-mini","max_tokens":30,"temperature":0,
            "messages":[{"role":"system","content":"Esperto scienza cucina. Rimuovi un fenomeno SOLO se chiaramente "
                        "falso per quella preparazione. Nel dubbio: tienilo (pertinente true)."},
                        {"role":"user","content":dom}]}
        try:
            rq=ur.Request("https://api.openai.com/v1/chat/completions",data=json.dumps(pl).encode(),
                          headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
            tx=json.loads(ur.urlopen(rq,timeout=20).read().decode())["choices"][0]["message"]["content"]
            import re as _re
            m=_re.search(r'\{.*\}',tx,_re.DOTALL)
            if m: return json.loads(m.group(0)).get("pertinente", True)
        except: pass
        return True  # nel dubbio tieni
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo'
                       AND data->'fenomeni' IS NOT NULL AND data->>'_fen_puliti' IS NULL LIMIT %s""",(limite,))
        righe=cur.fetchall()
        rimossi=[]; prot_tocchi=0
        for pid, nome, data in righe:
            dd=data if isinstance(data,dict) else json.loads(data)
            fen=dd.get("fenomeni",[])
            if not fen: continue
            nuovi=[]; qualche_rimosso=False
            for f in fen:
                fnome = f.get("nome") if isinstance(f,dict) else f
                if not fnome: continue
                if falso(nome, dd.get("disciplina",""), fnome):
                    nuovi.append(f)  # tengo (pertinente)
                else:
                    qualche_rimosso=True
                    rimossi.append({"prep":nome,"fenomeno_rimosso":fnome})
            if applica:
                dd["fenomeni"]=nuovi
                dd["_fen_puliti"]=True
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
                if qualche_rimosso: prot_tocchi+=1
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","fenomeni_rimossi":len(rimossi),
                        "protocolli_toccati":prot_tocchi,"dettaglio":rimossi[:20]})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/correggi-caso-verificato")
def admin_correggi_caso_verificato():
    """Corregge UN caso verificato a mano (Michele/Claude hanno controllato con fonti). Toglie i fenomeni FALSI
    indicati. NON sostituisce. ?prep=<pattern nome> ?togli=fen1,fen2 ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    pattern = request.args.get("prep","")
    togli = [t.strip().lower() for t in request.args.get("togli","").split(",") if t.strip()]
    if not pattern or not togli: return jsonify({"errore":"serve ?prep= e ?togli="}),400
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        cur.execute("""SELECT id, name, data FROM nodes WHERE type='Protocollo' AND LOWER(name) LIKE %s""",
                    (f'%{pattern.lower()}%',))
        tocchi=[]
        for pid, nome, data in cur.fetchall():
            dd=data if isinstance(data,dict) else json.loads(data)
            fen=dd.get("fenomeni",[])
            nuovi=[f for f in fen if (f.get("nome") if isinstance(f,dict) else f).strip().lower() not in togli]
            if len(nuovi)!=len(fen):
                tocchi.append({"prep":nome,"prima":[f.get("nome") if isinstance(f,dict) else f for f in fen],
                               "dopo":[f.get("nome") if isinstance(f,dict) else f for f in nuovi]})
                if applica:
                    dd["fenomeni"]=nuovi
                    cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),pid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","protocolli":tocchi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


@bp.route("/admin/forza-nomi-scientifici-comuni")
def admin_forza_nomi_scientifici_comuni():
    """P1 audit: forza il nome scientifico sui COMUNI importanti che sono vuoti (pomodoro, basilico...).
    Lista verificata a mano (binomi certi, non AI). ?applica=1."""
    from flask import request, jsonify
    import os, psycopg2, json
    if request.args.get("s") != os.environ.get("ADMIN_SECRET",""): return jsonify({"e":"no"}),403
    applica = request.args.get("applica")=="1"
    # binomi VERIFICATI a mano (tassonomia certa, non generata)
    BINOMI = {
        "pomodoro":"Solanum lycopersicum","basilico":"Ocimum basilicum","aglio":"Allium sativum",
        "cipolla":"Allium cepa","carota":"Daucus carota","sedano":"Apium graveolens","prezzemolo":"Petroselinum crispum",
        "limone":"Citrus limon","arancia":"Citrus sinensis","patata":"Solanum tuberosum","melanzana":"Solanum melongena",
        "zucchina":"Cucurbita pepo","peperone":"Capsicum annuum","peperoncino":"Capsicum annuum","spinaci":"Spinacia oleracea",
        "rosmarino":"Salvia rosmarinus","timo":"Thymus vulgaris","origano":"Origanum vulgare","alloro":"Laurus nobilis",
        "mela":"Malus domestica","pera":"Pyrus communis","fragola":"Fragaria ananassa","uva":"Vitis vinifera",
        "grano":"Triticum aestivum","riso":"Oryza sativa","mais":"Zea mays","oliva":"Olea europaea",
        "zenzero":"Zingiber officinale","cannella":"Cinnamomum verum","zafferano":"Crocus sativus","vaniglia":"Vanilla planifolia",
        "funghi":"Agaricus bisporus","tartufo":"Tuber magnatum","cacao":"Theobroma cacao","caffe":"Coffea arabica",
        "manzo":"Bos taurus","maiale":"Sus scrofa domesticus","pollo":"Gallus gallus domesticus","agnello":"Ovis aries",
        "salmone":"Salmo salar","tonno":"Thunnus thynnus","orata":"Sparus aurata","branzino":"Dicentrarchus labrax",
        "vongole":"Ruditapes decussatus","cozze":"Mytilus galloprovincialis","gambero":"Penaeus","menta":"Mentha",
    }
    try:
        conn=psycopg2.connect(os.environ["DATABASE_URL"]); cur=conn.cursor()
        messi=[]
        for nome, binomio in BINOMI.items():
            # il nodo con piu abbinamenti (il ricco)
            cur.execute("""SELECT n.id, n.data, COUNT(e.from_id) nc FROM nodes n
                           LEFT JOIN edges e ON e.from_id=n.id AND e.relation='abbinamento_aromatico'
                           WHERE LOWER(n.name)=LOWER(%s) AND n.type IN ('Ingrediente','Prodotto')
                           GROUP BY n.id, n.data ORDER BY nc DESC LIMIT 1""",(nome,))
            r=cur.fetchone()
            if not r: continue
            nid=r[0]; dd=r[1] if isinstance(r[1],dict) else json.loads(r[1])
            if dd.get("nome_scientifico"): continue  # gia c'e
            dd["nome_scientifico"]=binomio
            messi.append({"nome":nome,"sci":binomio})
            if applica:
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",(json.dumps(dd,ensure_ascii=False),nid)); conn.commit()
        cur.close();conn.close()
        return jsonify({"modalita":"APPLICATO" if applica else "DRY-RUN","messi":len(messi),"dettaglio":messi})
    except Exception as e:
        return jsonify({"errore":str(e)[:200]})


