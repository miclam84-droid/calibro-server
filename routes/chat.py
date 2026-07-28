# ============================================================
# routes/chat.py — chat AI, nodo, calcolatori.
# Dipende da: db, ai, contenuto, utils, motore.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import (cerca_contesto, costruisci_prompt, chiedi_mistral, estrai_entita,
               _scheda_tradotta, _traduci_nome, _numero_bersaglio as _nb,
               cerca_fuzzy, fenomeni_suggeriti, log_evento)
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _err, _check_rate_limit
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
    domanda = (request.json or {}).get("domanda","").strip()
    lang = (request.json or {}).get("lang", "it")
    history = (request.json or {}).get("history", [])
    token_sess = (request.json or {}).get("token","") or request.headers.get("X-Token","")
    if not domanda:
        return jsonify({"errore":"domanda vuota"}), 400

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
                if user_id_t:
                    cur_t.execute("SELECT COUNT(*), MIN(ts) FROM trial_chat WHERE user_id=%s AND ts > NOW() - INTERVAL '7 days'", (user_id_t,))
                else:
                    cur_t.execute("SELECT COUNT(*), MIN(ts) FROM trial_chat WHERE ip=%s AND ts > NOW() - INTERVAL '7 days'", (ip,))
                rt = cur_t.fetchone()
                n_chat = int(rt[0]) if rt else 0
                prima = rt[1] if rt else None
                giorni = (_dt.datetime.now(_dt.timezone.utc) - prima).days if prima else 0
                if n_chat >= 5 or giorni >= 7:
                    cur_t.close(); _release_conn(conn_t)
                    return jsonify({"errore":"trial_esaurito","n_chat":n_chat,
                        "messaggio":"Hai usato le 5 chat di prova. Passa a Pro per continuare.",
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
    # estrazione entità: prima provo i termini che estrae Mistral (capisce il dominio),
    # poi, se non agganciano nulla, ripiego sulle parole della domanda (rete di sicurezza).
    termini = estrai_entita(domanda) + sorted(
        [p.strip(".,?!").lower() for p in domanda.split() if len(p) > 4],
        key=len, reverse=True)
    contesto = None
    for t in termini:
        contesto = cerca_contesto(db, t, domanda)
        if contesto and contesto.get("fenomeni"): break

    # LIVELLO 2 — niente match esatto: provo per somiglianza sull'intera domanda
    if not contesto or not contesto.get("fenomeni"):
        contesto = cerca_fuzzy(db, domanda)

    # LIVELLO 3 — ancora niente: non lascio l'utente a un vicolo cieco,
    # mostro i fenomeni del grafo come punto di partenza cliccabile
    if not contesto or not contesto.get("fenomeni"):
        suggeriti = fenomeni_suggeriti(db)
        log_evento("fallback", domanda, esito="nessun_nodo")
        return jsonify({
            "risposta": None,
            "nota": "Non ho trovato un aggancio preciso nel grafo per questa domanda. "
                    "Prova a partire da uno di questi fenomeni, o riformula con un "
                    "ingrediente o un prodotto specifico.",
            "connessi": [{"id": f["id"], "nome": f["nome"], "dominio": f["dominio"],
                          "target": f["target"]} for f in suggeriti]
        })

    prompt = costruisci_prompt(domanda, contesto, lang=lang)
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
    domanda = f"Spiegami {n['name']} e i fenomeni che lo governano."
    prompt = costruisci_prompt(domanda, contesto, lang=request.args.get('lang','it'))
    risposta = chiedi_mistral(prompt)
    log_evento("nodo", n["name"],
               fenomeni=[f["name"] for f in contesto["fenomeni"]],
               esito="ok" if risposta else "errore_modello")
    connessi, visti = [], set()
    for f in contesto["fenomeni"]:
        for c in f["collegamenti"]:
            if c["relazione"] == "si_manifesta_in" and c["id"] not in visti:
                visti.add(c["id"])
                connessi.append({"id": c["id"], "nome": c["verso"],
                                 "dominio": c["dominio"],
                                 "target": c["data"].get("target","")})
    return jsonify({
        "titolo": n["name"],
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta,
        "connessi": connessi
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
