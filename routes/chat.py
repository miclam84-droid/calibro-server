# ============================================================
# routes/chat.py — chat AI, nodo, calcolatori.
# Dipende da: db, ai, contenuto, utils, motore.
from routes.stato import segna_studiato
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import (cerca_contesto, costruisci_prompt, chiedi_mistral, estrai_entita,
               _scheda_tradotta, _traduci_nome, _numero_bersaglio as _nb,
               cerca_fuzzy, fenomeni_suggeriti, log_evento)
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _err, _check_rate_limit, _check_rate_limit_ai, _chiave_rate, _ai_giu_response
from auth import _utente_da_token
from config import DATABASE_URL
import os, json
import motore as Motore
import ai_gateway as GW
bp = Blueprint("chat", __name__)


@bp.route("/chiedi", methods=["POST"])
def chiedi():
    # IN4: rate limiting per IP
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":"Troppe richieste. Aspetta un minuto e riprova."}), 429
    # rate limit AI severo: /chiedi chiama l'AI, protegge il credito da loop
    if not _check_rate_limit_ai(_chiave_rate()):
        return jsonify({"errore":"rate_limit","messaggio":"Troppe domande in poco tempo. Attendi un minuto."}), 429
    domanda = (request.json or {}).get("domanda","").strip()
    lang = (request.json or {}).get("lang", "it")
    history = (request.json or {}).get("history", [])
    contesto_scheda = (request.json or {}).get("contesto") or None
    token_sess = (request.json or {}).get("token","") or request.headers.get("X-Token","")
    if not domanda:
        return jsonify({"errore":"domanda vuota"}), 400

    # ── RICONOSCIMENTO INTENTO RICETTA ──
    # se l'utente chiede di CREARE una ricetta (non di spiegare un fenomeno),
    # instrado al generatore di ricette strutturate invece della chat esplicativa.
    import re as _re_intent
    _dl = domanda.lower()
    _pattern_ricetta = _re_intent.search(
        r"\b(fa(?:cciamo|i|mmi)|cre(?:a|iamo|ami)|prepar(?:a|iamo|ami)|gener(?:a|ami)|"
        r"invent(?:a|iamo|ami)|propon(?:i|imi)|dammi|voglio|vorrei)\b.{0,25}\bricetta\b", _dl)
    _pattern_ricetta2 = _re_intent.search(r"\bricetta (con|di|per|a base)\b", _dl)
    if _pattern_ricetta or _pattern_ricetta2:
        try:
            from builder import genera_ricetta
            _db = carica_grafo()
            _ric = genera_ricetta(_db, domanda, disciplina="cucina", lang=lang)
            if _ric and _ric.get("nome") and not _ric.get("errore"):
                _ric["_tipo"] = "ricetta"  # il frontend riconosce che è una ricetta, non una risposta chat
                return jsonify(_ric)
        except Exception:
            pass  # se fallisce, prosegui con la chat normale

    # ── DOMANDE SULL'APP: risposta fissa operativa prima del grafo ──────
    _dl = domanda.lower()
    _kw_app = ["cosa posso fare","cosa fai","cosa puoi fare","come funziona",
               "a cosa servi","a cosa serve","come si usa","come funzione",
               "cosa sei","cosa fa quest","cosa fa l'app","cosa fa questa app",
               "come ti uso","come inizio","da dove inizio","chi sei","help",
               "aiutami a capire","spiegami l'app","cosa offri"]
    if any(k in _dl for k in _kw_app):
        _risp = {
            "it": ("PROBLEMA: Vuoi sapere cosa puoi fare qui.\n"
                   "PERCHÉ: Matter Lab è uno strumento scientifico per chi lavora nel food & beverage — non un ricettario, ma il perché fisico e chimico dietro ogni gesto del mestiere.\n"
                   "NUMERO: 103 fenomeni · 47 tecniche · 53 ricette, tutti con numeri da controllare al banco.\n"
                   "MISURA: Fammi una domanda tecnica reale — 'perché il mio sour cambia ogni volta', 'il lievito madre non sale', 'la maionese impazzisce' — e ti do la spiegazione con i numeri.\n"
                   "AZIONE: Puoi anche fotografare ingredienti o bottiglie per scoprire abbinamenti e fenomeni, o esplorare la Mappa per disciplina."),
            "en": ("PROBLEM: You want to know what you can do here.\n"
                   "WHY: Matter Lab is a scientific tool for food & beverage professionals — not a recipe book, but the physics and chemistry behind every move of the craft.\n"
                   "NUMBER: 103 phenomena · 47 techniques · 53 recipes, all with numbers to control at the bench.\n"
                   "MEASURE: Ask me a real technical question — 'why does my sour change every time', 'my sourdough won't rise' — and I'll explain with the numbers.\n"
                   "ACTION: You can also photograph ingredients or bottles to discover pairings and phenomena, or explore the Map by discipline."),
            "es": ("PROBLEMA: Quieres saber qué puedes hacer aquí.\n"
                   "POR QUÉ: Matter Lab es una herramienta científica para profesionales del food & beverage — no un recetario, sino la física y química detrás de cada gesto del oficio.\n"
                   "NÚMERO: 103 fenómenos · 47 técnicas · 53 recetas, todos con números para controlar en la barra.\n"
                   "MEDIDA: Hazme una pregunta técnica real — 'por qué mi sour cambia cada vez', 'mi masa madre no sube' — y te lo explico con los números.\n"
                   "ACCIÓN: También puedes fotografiar ingredientes o botellas para descubrir maridajes y fenómenos, o explorar el Mapa por disciplina."),
        }.get(lang, None)
        if _risp is None:
            _risp = {"it":"","en":"","es":""}.get("it")
        if not _risp:
            _risp = ("PROBLEMA: Vuoi sapere cosa puoi fare qui.\n"
                     "PERCHÉ: Matter Lab spiega la scienza del mestiere F&B.\n"
                     "AZIONE: Fammi una domanda tecnica reale del tuo lavoro.")
        return jsonify({
            "risposta": _risp,
            "trovato": ["Matter Lab"],
            "connessi": [],
            "trial": {}
        })
    # ── FINE DOMANDE APP ────────────────────────────────────────────────


    # ── TRIAL / PAYWALL ─────────────────────────────────────────────────
    trial_info = {}
    if DATABASE_URL:
        try:
            import psycopg2, datetime as _dt
            conn_t = _get_conn()
            cur_t = conn_t.cursor()
            cur_t.execute("""CREATE TABLE IF NOT EXISTS trial_chat (
                id SERIAL PRIMARY KEY, ip TEXT, user_id INTEGER,
                ts TIMESTAMPTZ DEFAULT NOW())""")
            user_id_t = _utente_da_token(token_sess) if token_sess else None
            piano_t = "free"
            if user_id_t:
                cur_t.execute("SELECT piano FROM utenti WHERE id=%s", (user_id_t,))
                rp = cur_t.fetchone()
                piano_t = rp[0] if rp else "free"
            if piano_t != "pro":
                # 5 assaggi chat TOTALI (struttura OpenAI: non a tempo, 5 e basta)
                if user_id_t:
                    cur_t.execute("SELECT COUNT(*) FROM trial_chat WHERE user_id=%s", (user_id_t,))
                else:
                    cur_t.execute("SELECT COUNT(*) FROM trial_chat WHERE ip=%s", (ip,))
                rt = cur_t.fetchone()
                n_chat = int(rt[0]) if rt and rt[0] else 0
                if n_chat >= 5:
                    cur_t.close(); _release_conn(conn_t)
                    return jsonify({"errore":"trial_esaurito","n_chat":n_chat,
                        "messaggio":"Hai visto cosa può fare Matter.",
                        "paywall":{
                          "titolo":"Hai visto cosa può fare Matter.",
                          "sottotitolo":"Hai usato i tuoi 5 assaggi gratuiti. Da qui Matter può continuare a lavorare con te:",
                          "vantaggi":["Analisi operative dei tuoi problemi","Foto di impasti e preparazioni","Risposte a voce, mani libere","Ragionamento sui tuoi valori","Indicazioni personalizzate"],
                          "prezzo":"€19,99 / mese",
                          "cta":"Continua con Matter →",
                          "nota":"L'Atlante, il Mirino e i Calcolatori restano gratuiti."},
                        "trial_esaurito":True}), 402
                if user_id_t:
                    cur_t.execute("INSERT INTO trial_chat (user_id,ip) VALUES (%s,%s)", (user_id_t, ip))
                else:
                    cur_t.execute("INSERT INTO trial_chat (ip) VALUES (%s)", (ip,))
                conn_t.commit()
                n_usate = n_chat + 1
                trial_info = {"trial_attivo":True,"chat_usate":n_usate,
                    "chat_rimaste":max(0,5-n_usate),
                    "notifica":n_usate==3,"ultimo":n_usate>=5}
            cur_t.close(); _release_conn(conn_t)
        except Exception as _te:
            print(f"[TRIAL] {_te}", flush=True)
    # ── FINE TRIAL ──────────────────────────────────────────────────────


    db = carica_grafo()
    # RETRIEVAL RANKED (candidate generation + scoring + dominio): sceglie i fenomeni migliori.
    # Poi cerca_contesto costruisce il contesto ricco (collegamenti, errori, target) sui fenomeni scelti.
    contesto = None
    try:
        from retrieval import retrieval_ranked
        termini_mistral = estrai_entita(domanda)
        ranked = retrieval_ranked(db, domanda, termini_extra=termini_mistral, topk=5)
        fen_ids = [f["id"] for f in ranked.get("fenomeni", [])]
        if fen_ids:
            # costruisco il contesto ricco cercando per il PRIMO fenomeno (nome), poi il contesto
            # include i suoi collegamenti; per robustezza uso cerca_contesto sul nome del top.
            for fid in fen_ids:
                nome = db.execute("SELECT name FROM nodes WHERE id=?", (fid,)).fetchone()
                if nome:
                    contesto = cerca_contesto(db, nome["name"], domanda)
                    if contesto and contesto.get("fenomeni"): break
    except Exception as _re:
        print(f"[RANKED] errore, fallback vecchia logica: {_re}", flush=True)
        contesto = None

    # FALLBACK alla vecchia logica se il ranker non ha prodotto contesto
    if not contesto or not contesto.get("fenomeni"):
        termini = estrai_entita(domanda) + sorted(
            [p.strip(".,?!").lower() for p in domanda.split() if len(p) > 4],
            key=len, reverse=True)
        for t in termini:
            contesto = cerca_contesto(db, t, domanda)
            if contesto and contesto.get("fenomeni"): break

    # LIVELLO 2 — niente match esatto: provo per somiglianza sull'intera domanda
    if not contesto or not contesto.get("fenomeni"):
        contesto = cerca_fuzzy(db, domanda)

    # LIVELLO 3 — nessun aggancio nel grafo: invece di lasciare l'utente a un
    # vicolo cieco, faccio rispondere l'AI con la sua conoscenza scientifica
    # (taglio Matter), e allego i fenomeni suggeriti come spunto di approfondimento.
    fallback_suggeriti = None
    if not contesto or not contesto.get("fenomeni"):
        suggeriti = fenomeni_suggeriti(db)
        log_evento("fallback", domanda, esito="nessun_nodo_ai_generale")
        # contesto vuoto ma valido: costruisci_prompt lo regge (for su lista vuota)
        contesto = {"fenomeni": [], "errori": [], "prodotti_fisici": []}
        fallback_suggeriti = [{"id": f["id"], "nome": f["nome"], "dominio": f["dominio"],
                               "target": f["target"]} for f in suggeriti]

    # se la domanda arriva da una scheda lezione, inietto il contesto così
    # la chat risponde già informata su QUEL fenomeno
    domanda_arricchita = domanda
    if contesto_scheda and isinstance(contesto_scheda, dict):
        fen = (contesto_scheda.get("fenomeno") or "").strip()
        tgt = (contesto_scheda.get("target") or "").strip()
        if fen:
            _ctx_txt = f"[L'utente sta studiando la scheda del fenomeno '{fen}'"
            if tgt:
                _ctx_txt += f" (numero bersaglio: {tgt})"
            _ctx_txt += ". Rispondi restando su questo fenomeno, applicandolo al suo caso specifico.] "
            domanda_arricchita = _ctx_txt + domanda

    prompt = costruisci_prompt(domanda_arricchita, contesto, lang=lang)
    # history strutturata: passa i turni precedenti come messages[], non come testo
    history_msgs = []
    if history:
        for h in history[-3:]:
            if h.get('q') and h.get('r'):
                history_msgs.append({"role": "user", "content": h['q']})
                history_msgs.append({"role": "assistant", "content": h['r']})
    risposta = chiedi_mistral(prompt, history=history_msgs)
    # log_evento ritorna l'id della riga inserita (RETURNING id) — fix log_id bug
    log_id = log_evento("risposta", domanda,
               fenomeni=[f["name"] for f in contesto["fenomeni"]],
               esito="ok" if risposta else "errore_modello")
    # nodi navigabili: i prodotti/discipline collegati ai fenomeni trovati (per l'esploratore)
    connessi = []
    visti = set()
    for f in contesto["fenomeni"]:
        for c in f["collegamenti"]:
            if c["relazione"] == "si_manifesta_in" and c["id"] not in visti:
                visti.add(c["id"])
                connessi.append({"id": c["id"], "nome": c["verso"],
                                 "dominio": c["dominio"],
                                 "target": c["data"].get("target","")})

    # sanitizza la risposta: rimuove caratteri di controllo che rompono il JSON
    # \x00-\x1f = tutti i control chars eccetto \x09 (tab) \x0a (newline) \x0d (CR)
    # ma dentro un campo JSON anche newline e CR devono essere escaped — jsonify lo fa
    # il problema reale è i caratteri \x00-\x08 \x0b \x0c \x0e-\x1f che non sono mai validi
    import re as _re
    if risposta:
        risposta = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', risposta)
        # normalizza newline multipli in uno solo
        risposta = _re.sub(r'\n{3,}', '\n\n', risposta).strip()
    # Aggrega numeri bersaglio dai fenomeni trovati
    numeri_bersaglio = []
    for f in contesto["fenomeni"]:
        t = f.get("data", {}).get("target", "") or f.get("target", "")
        if t and t not in numeri_bersaglio:
            numeri_bersaglio.append(t)
    numero_bersaglio_agg = " · ".join(numeri_bersaglio[:2]) if numeri_bersaglio else ""
    # PULIZIA: il numero bersaglio deve essere un NUMERO/intervallo, non una frase.
    # Se contiene simboli discorsivi (→, virgole multiple) o è troppo lungo, lo svuoto.
    def _valida_numero(s):
        if not s: return ""
        s = str(s).strip()
        # deve contenere almeno una cifra
        if not _re.search(r"\d", s): return ""
        # non deve essere una frase: niente frecce, punti elenco, o troppo lunga
        if "→" in s or "·" in s or len(s) > 40: return ""
        # troppe virgole = elenco/frase
        if s.count(",") > 1: return ""
        return s
    numero_bersaglio_agg = _valida_numero(numero_bersaglio_agg)

    # se siamo nel fallback (nessun aggancio grafo), aggiungi i fenomeni suggeriti
    # come spunto, MA la risposta AI c'è comunque (non è più un vicolo cieco)
    if fallback_suggeriti:
        connessi = fallback_suggeriti + connessi

    return jsonify({
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta,
        "connessi": connessi,
        "log_id": log_id,
        "trial": trial_info,
        "numero_bersaglio": numero_bersaglio_agg
    })

@bp.route("/nodo", methods=["POST"])
def nodo():
    """Click su un nodo dalla scheda: interroga il grafo PER ID (non per testo).
    È il follow-up dell'esploratore — robusto, niente estrazione di entità."""
    nid = (request.json or {}).get("id","").strip()
    if not nid:
        return jsonify({"errore":"id vuoto"}), 400
    db = carica_grafo()
    n = db.execute("SELECT * FROM nodes WHERE id=?", (nid,)).fetchone()
    if not n:
        return jsonify({"risposta": None, "nota": "Nodo non trovato."})
    # uso il nome del nodo come termine: ricostruisce il contesto profondo attorno ad esso
    contesto = cerca_contesto(db, n["name"].split()[0])
    if not contesto or not contesto.get("fenomeni"):
        return jsonify({"risposta": None, "nota": "Nessun fenomeno collegato."})
    lang = request.args.get('lang','it')
    domanda = f"Spiegami {n['name']} e i fenomeni che lo governano."
    prompt = costruisci_prompt(domanda, contesto, lang=lang)
    # traccia "studiato" se richiesto (?traccia=1) — feature stato-fenomeno
    _stato_fen = None
    if request.args.get("traccia") == "1":
        try: _stato_fen = segna_studiato(nid)
        except Exception: _stato_fen = None
    # CACHE: la risposta AI di un nodo è deterministica (stesso nodo, stessa lingua).
    # La calcolo una volta e la salvo, poi la servo istantanea (evita 5s di attesa AI a ogni apertura).
    import json as _cjson
    cache_key = f"risposta_cache_{lang}"
    _ndata = n["data"] if isinstance(n["data"],dict) else (_cjson.loads(n["data"]) if n["data"] else {})
    risposta = _ndata.get(cache_key) if isinstance(_ndata,dict) else None
    if not risposta:
        risposta = chiedi_mistral(prompt)
        if risposta:
            try:
                if not isinstance(_ndata,dict): _ndata={}
                _ndata[cache_key] = risposta
                db.execute("UPDATE nodes SET data=? WHERE id=?", (_cjson.dumps(_ndata,ensure_ascii=False), nid))
            except Exception:
                pass
    log_evento("nodo", n["name"],
               fenomeni=[f["name"] for f in contesto["fenomeni"]],
               esito="ok" if risposta else "errore_modello")
    connessi, visti = [], set()
    errori, visti_err = [], set()
    principi, visti_pr = [], set()
    tecniche, visti_tec = [], set()
    strumenti, visti_str = [], set()
    # se il nodo APERTO è uno Strumento, espongo i suoi campi (parametri, errore, scheda)
    strumento_info = None
    try:
        nd = n["data"] if isinstance(n["data"],dict) else __import__("json").loads(n["data"] or "{}")
        if n["type"] == "Strumento":
            strumento_info = {"parametri": nd.get("parametri",""), "errore_tipico": nd.get("errore_tipico",""), "scheda": nd.get("scheda","")}
    except Exception:
        pass
    for f in contesto["fenomeni"]:
        for c in f["collegamenti"]:
            if c["relazione"] == "si_manifesta_in" and c["id"] not in visti:
                visti.add(c["id"])
                connessi.append({"id": c["id"], "nome": c["verso"],
                                 "dominio": c["dominio"],
                                 "target": c["data"].get("target","")})
            # PRINCIPIO: il perche fisico profondo (il tetto della Bibbia)
            elif c["relazione"] == "governato_da" and c["id"] not in visti_pr:
                visti_pr.add(c["id"])
                principi.append({"id": c["id"], "nome": c["verso"]})
            # TECNICHE: come si governa il fenomeno
            elif c["relazione"] in ("realizzato_da","controllato_con") and c["id"] not in visti_tec:
                visti_tec.add(c["id"])
                tecniche.append({"id": c["id"], "nome": c["verso"]})
                # STRUMENTI che abilitano questa tecnica (relazione abilita inversa)
                try:
                    for s in db.execute("SELECT n.id, n.name FROM edges e JOIN nodes n ON n.id=e.from_id WHERE e.to_id=? AND e.relation='abilita'", (c["id"],)).fetchall():
                        if s["id"] not in visti_str:
                            visti_str.add(s["id"])
                            strumenti.append({"id": s["id"], "nome": s["name"], "per_tecnica": c["verso"]})
                except Exception:
                    pass
            # ERRORI: sintomo osservabile al banco -> causa (il valore "bibbia")
            elif c["relazione"] == "fallisce_come" and c["id"] not in visti_err:
                visti_err.add(c["id"])
                sintomo = c["data"].get("sintomo","") if isinstance(c.get("data"),dict) else ""
                # recupero la causa dal nodo errore
                causa = ""
                try:
                    er = db.execute("SELECT data FROM nodes WHERE id=?", (c["id"],)).fetchone()
                    if er:
                        ed = er["data"] if isinstance(er["data"],dict) else __import__("json").loads(er["data"] or "{}")
                        causa = ed.get("causa","")
                except Exception:
                    pass
                errori.append({"id": c["id"], "nome": c["verso"],
                               "sintomo": sintomo, "causa": causa})
    # ── DATI PER IL FORM DI MISURA (richiesta frontend) ──
    # id del fenomeno principale aperto + target strutturato per il confronto misura.
    _fen_id = None; _target = None; _target_num = None; _unita = None; _grandezza = None
    try:
        # il fenomeno principale è il primo del contesto; il suo id è quello del nodo se è un Fenomeno,
        # altrimenti prendo il primo fenomeno collegato
        if n["type"] == "Fenomeno":
            _fen_id = nid
            _fd = n["data"] if isinstance(n["data"],dict) else __import__("json").loads(n["data"] or "{}")
        else:
            _primo = contesto["fenomeni"][0] if contesto.get("fenomeni") else None
            if _primo:
                _fen_id = _primo.get("id")
                _fd = _primo.get("data") if isinstance(_primo.get("data"),dict) else {}
            else:
                _fd = {}
        _target = _fd.get("target") or _fd.get("numero_bersaglio")
        _unita = _fd.get("unita") or _fd.get("unità")
        _grandezza = _fd.get("grandezza") or _fd.get("grandezza_principale")
        # provo a estrarre un numero dal target testuale (quando c'è un bersaglio secco)
        if _target:
            import re as _re
            m = _re.search(r"(\d+[.,]?\d*)\s*[-–a]\s*(\d+[.,]?\d*)", str(_target))  # range
            if m:
                _target_num = f"{m.group(1)}-{m.group(2)}"
            else:
                m2 = _re.search(r"(\d+[.,]?\d*)\s*(%|°C|°|pH|g|ml|bar)?", str(_target))
                if m2 and m2.group(1):
                    _target_num = m2.group(1)
                    if not _unita and m2.group(2):
                        _unita = m2.group(2)
    except Exception:
        pass
    return jsonify({
        "titolo": n["name"],
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta,
        "connessi": connessi,
        "errori": errori,
        "principi": principi,
        "tecniche": tecniche,
        "strumenti": strumenti,
        "strumento_info": strumento_info,
        "stato_fenomeno": _stato_fen,
        # dati per il form di misura:
        "id": _fen_id,
        "target": _target,
        "target_numero": _target_num,
        "unita": _unita,
        "grandezza": _grandezza
    })

@bp.route("/calcola", methods=["POST"])
def calcola():
    """Endpoint del motore di calcolo deterministico.
    Riceve {calcolo: str, parametri: dict}, restituisce il risultato esatto.
    Nessuna AI — numeri calcolati da formule fisiche/chimiche verificate.
    Usato sia dal frontend (calcolatori) che potenzialmente da tool-calling di Sonnet."""
    body = request.json or {}
    nome = body.get("calcolo", "").strip()
    parametri = body.get("parametri", {})
    if not nome:
        return jsonify({"errore": "campo 'calcolo' obbligatorio"}), 400
    risultato = Motore.esegui(nome, parametri)
    log_evento("calcolo", nome, esito="ok" if "errore" not in risultato else "errore")
    return jsonify(risultato)
