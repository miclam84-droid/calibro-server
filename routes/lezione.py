# ============================================================
# routes/lezione.py — lezioni, home, disciplina, quiz, mappa.
# Dipende da: db, ai, contenuto, utils.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import (_scheda_tradotta, _intro, _numero_bersaglio as _nb, _genera_quiz,
               _traduci_nome, log_evento)
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _err
from config import DATABASE_URL
import os, json, time
import ai_gateway as GW
bp = Blueprint("lezione", __name__)

_cache_home = {}       # { lang: {"ts": float, "data": dict} }
_lezione_cache = {}    # { disciplina_nome: [fenomeni] }


@bp.route("/home")
def home_api():
    """FE1 — Fenomeno del giorno + principio del giorno.
    Supporta ?lang=it|en — default it."""
    global _cache_home
    lang = request.args.get("lang", "it")
    now = time.time()
    # cache separata per lingua; scade dopo 24h
    cached = _cache_home.get(lang)
    if cached and now - cached["ts"] < 86400:
        return jsonify(cached["data"])
    db = carica_grafo()
    fenomeni = db.execute(
        "SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY id"
    ).fetchall()
    principi = db.execute(
        "SELECT id, name, data FROM nodes WHERE type='principio' ORDER BY id"
    ).fetchall()
    if not fenomeni:
        return jsonify({"errore": "grafo vuoto"})
    f = random.choice(fenomeni)
    fd = _dati(f["data"])
    result = {
        "fenomeno": {
            "id": f["id"],
            "nome": f["name"],
            "dominio": f["domain"],
            "target": _numero_bersaglio(fd),
            "scheda_intro": _intro(_scheda_lang(fd, lang))
        }
    }
    principi_attivi = [p for p in principi if "candidato" not in str(_dati(p["data"]))]
    if principi_attivi:
        p = principi_attivi[0]
        pd = _dati(p["data"])
        result["principio"] = {
            "id": p["id"],
            "nome": p["name"],
            "scheda_intro": _intro(_scheda_lang(pd, lang))
        }
    _cache_home[lang] = {"ts": now, "data": result}
    return jsonify(result)

@bp.route("/disciplina/<nome>")
@bp.route("/v1/disciplina/<nome>")
def disciplina(nome):
    """FE2 — Fenomeni reali di una disciplina, ordinati per percorso didattico.
    Sblocca Lezione e Mappa dinamiche."""
    db = carica_grafo()
    # trova prodotti della disciplina
    prodotti = db.execute(
        "SELECT id, name FROM nodes WHERE type='Prodotto' AND lower(domain)=lower(?)",
        (nome,)
    ).fetchall()
    # da ogni prodotto risale ai fenomeni
    fen_ids = set()
    for p in prodotti:
        for e in db.execute(
            "SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'",
            (p["id"],)
        ):
            fen_ids.add(e["from_id"])
    # Priorità per disciplina: fenomeni fondamentali prima, poi gli altri
    PRIORITA = {
        "bar":          ["fen-acidita","fen-diluizione","fen-concentrazione","fen-carbonatazione","fen-estrazione","fen-emulsione","fen-crioscopia","fen-osmosi","fen-ossidazione"],
        "caffetteria":  ["fen-estrazione","fen-estrazione-caffe","fen-concentrazione","fen-pressione","fen-trasferimento-calore","fen-acidita","fen-attivita-enzimatica"],
        "panificazione":["fen-acidita","fen-fermentazione","fen-fermentazione-lattica","fen-idrolisi","fen-gelatinizzazione","fen-retrogradazione","fen-concentrazione","fen-osmosi","fen-autolisi"],
        "cucina":       ["fen-maillard","fen-denaturazione","fen-coagulazione","fen-emulsione","fen-acidita","fen-osmosi","fen-trasferimento-calore","fen-punto-fumo"],
        "pasticceria":  ["fen-emulsione","fen-cristallizzazione","fen-caramellizzazione","fen-maillard","fen-gelatinizzazione","fen-denaturazione","fen-sineresi"],
        "gelateria":    ["fen-crioscopia","fen-cristallizzazione-ghiaccio","fen-overrun","fen-concentrazione","fen-emulsione"],
        "vino":         ["fen-acidita","fen-malolattica","fen-ossidazione","fen-fermentazione","fen-tannini","fen-chiarificazione"],
        "birra":        ["fen-fermentazione","fen-carbonatazione","fen-amilolisi","fen-acidita","fen-ossidazione","fen-attivita-enzimatica"],
    }
    priorita_disc = PRIORITA.get(nome.lower(), [])

    # Se la disciplina ha una lista di priorità definita, usa SOLO quei fenomeni
    # nell'ordine esatto — evita che fenomeni di altre discipline finiscano nel percorso
    if priorita_disc:
        fenomeni = []
        for fid in priorita_disc:
            f = db.execute("SELECT id, name, data FROM nodes WHERE id=?", (fid,)).fetchone()
            if f:
                fenomeni.append({"id": f["id"], "nome": f["name"],
                                 "target": _numero_bersaglio(_dati(f["data"]))})
        # Aggiungi gli altri fenomeni della disciplina non in priorità
        for fid in fen_ids:
            if fid not in priorita_disc:
                f = db.execute("SELECT id, name, data FROM nodes WHERE id=?", (fid,)).fetchone()
                if f:
                    fenomeni.append({"id": f["id"], "nome": f["name"],
                                     "target": _numero_bersaglio(_dati(f["data"]))})
    elif not fen_ids:
        tutti = db.execute(
            "SELECT id, name, data FROM nodes WHERE type='Fenomeno' ORDER BY name"
        ).fetchall()
        fenomeni = [{"id": f["id"], "nome": f["name"],
                     "target": _numero_bersaglio(_dati(f["data"]))} for f in tutti]
    else:
        fenomeni_raw = []
        for fid in fen_ids:
            f = db.execute("SELECT id, name, data FROM nodes WHERE id=?", (fid,)).fetchone()
            if f:
                fenomeni_raw.append({"id": f["id"], "nome": f["name"],
                                     "target": _numero_bersaglio(_dati(f["data"]))})
        def _sort_key(f):
            try:
                return (0, priorita_disc.index(f["id"]))
            except ValueError:
                return (1, f["nome"])
        fenomeni = sorted(fenomeni_raw, key=_sort_key)
    return jsonify({"disciplina": nome, "fenomeni": fenomeni, "totale": len(fenomeni)})

@bp.route("/lezione/<disciplina_nome>/<int:step>")
def lezione(disciplina_nome, step):
    """FE3 — Nodo del passo corrente + scheda + quiz.
    step 0 = free · step 1+ = Pro only."""
    lang = request.args.get("lang", "it")
    token = request.args.get("token","") or request.headers.get("X-Token","")
    if step > 0 and DATABASE_URL:
        try:
            import psycopg2
            _conn_l = _get_conn()
            _cur_l = _conn_l.cursor()
            uid = _utente_da_token(token)
            piano = "free"
            if uid:
                _cur_l.execute("SELECT piano FROM utenti WHERE id=%s", (uid,))
                r = _cur_l.fetchone()
                piano = r[0] if r else "free"
            _cur_l.close(); _release_conn(_conn_l)
            if piano != "pro":
                return jsonify({"errore":"pro_required","paywall":True,
                    "messaggio":_err("pro_required", lang)}), 402
        except Exception:
            pass
    db = carica_grafo()
    if disciplina_nome not in _lezione_cache:
        resp = disciplina(disciplina_nome).get_json()
        _lezione_cache[disciplina_nome] = resp.get("fenomeni", [])
    fenomeni = _lezione_cache[disciplina_nome]
    if not fenomeni:
        return jsonify({"errore": "disciplina non trovata o vuota"})
    idx = max(0, min(step, len(fenomeni) - 1))
    f_info = fenomeni[idx]
    nodo = db.execute("SELECT * FROM nodes WHERE id=?", (f_info["id"],)).fetchone()
    if not nodo:
        return jsonify({"errore": "nodo non trovato"})
    nd = _dati(nodo["data"])
    if lang != "it":
        import psycopg2 as _pg
        try:
            _conn_trad = _pg.connect(DATABASE_URL) if DATABASE_URL else None
        except Exception:
            _conn_trad = None
        scheda = _scheda_tradotta(nodo["id"], nd, lang, _conn_trad)
        if _conn_trad:
            try: _release_conn(_conn_trad)
            except: pass
    else:
        scheda = _scheda_lang(nd, lang)
    target = _numero_bersaglio(nd)
    # principio collegato
    principio = None
    pr = db.execute("""SELECT n.name, n.data FROM edges e
                       JOIN nodes n ON n.id=e.from_id
                       WHERE e.to_id=? AND e.relation='spiega'
                       AND n.type='principio'""", (nodo["id"],)).fetchone()
    if pr:
        principio = {"nome": pr["name"], "testo": _scheda_lang(_dati(pr["data"]), lang)[:300]}
    # quiz: NON piu generato qui. Era una chiamata Haiku sincrona (~5s) a ogni
    # apertura della lezione: quello era il collo di bottiglia. Ora la lezione
    # torna subito e il quiz si prende da /quiz/<node_id> (lazy + cache).
    quiz = None
    return jsonify({
        "step": idx,
        "totale_passi": len(fenomeni),
        "fenomeno": {
            "id": nodo["id"],
            "nome": _traduci_nome(nodo["name"], lang),
            "dominio": nodo["domain"],
            "target": target,
            "scheda": scheda
        },
        "principio": principio,
        "quiz": quiz,
        "ha_precedente": idx > 0,
        "ha_successivo": idx < len(fenomeni) - 1
    })

@bp.route("/quiz/<node_id>")
def quiz_nodo(node_id):
    """Quiz di un nodo, lazy + cache. La lezione non lo genera piu (era ~5s).
    Prima volta: Haiku + salva in quiz_cache. Poi: istantaneo dalla cache.
    quiz_cache vive in Postgres, non viene truncata dal migrate."""
    lang = request.args.get("lang", "it")
    if not DATABASE_URL:
        return jsonify({"quiz": None})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # crea la tabella se non esiste (sopravvive al migrate)
        cur.execute("""CREATE TABLE IF NOT EXISTS quiz_cache (
            node_id TEXT, lang TEXT, quiz_json TEXT,
            PRIMARY KEY (node_id, lang))""")
        cur.execute("SELECT quiz_json FROM quiz_cache WHERE node_id=%s AND lang=%s",
                    (node_id, lang))
        row = cur.fetchone()
        base = None
        if row:
            try: base = json.loads(row[0])
            except Exception: base = None
        if base is None:
            cur.execute("SELECT id, name, data FROM nodes WHERE id=%s", (node_id,))
            nrow = cur.fetchone()
            if not nrow:
                cur.close(); _release_conn(conn)
                return jsonify({"quiz": None})
            nd = _dati(nrow[2])
            base = _genera_quiz(nrow[1], _numero_bersaglio(nd),
                                _scheda_lang(nd, lang), lang)
            if base:
                cur.execute("""INSERT INTO quiz_cache (node_id, lang, quiz_json)
                              VALUES (%s,%s,%s) ON CONFLICT (node_id, lang) DO NOTHING""",
                            (node_id, lang, json.dumps(base)))
        conn.commit(); cur.close(); _release_conn(conn)
    except Exception as _eq:
        import traceback as _tb
        print(f"QUIZ ERROR {node_id}: {_eq}\n{_tb.format_exc()[:500]}", flush=True)
        return jsonify({"quiz": None})
    if not base:
        return jsonify({"quiz": None})
    # shuffle delle opzioni alla consegna (varieta senza ri-pagare Haiku)
    opzioni = list(base.get("opzioni", []))
    corretta_testo = opzioni[base.get("corretta", 0)] if opzioni else ""
    random.shuffle(opzioni)
    nuovo_idx = opzioni.index(corretta_testo) if corretta_testo in opzioni else 0
    return jsonify({"quiz": {
        "domanda": base.get("domanda", ""),
        "opzioni": opzioni,
        "corretta": nuovo_idx,
        "spiegazione": base.get("spiegazione", "")
    }})

@bp.route("/mappa/<disciplina_nome>")
def mappa(disciplina_nome):
    """FE4 — Fenomeni della disciplina con stato libero/completato.
    Senza account: tutti liberi. Con account (futuro): stato persistente."""
    resp = disciplina(disciplina_nome).get_json()
    fenomeni = resp.get("fenomeni", [])
    # per ora tutti liberi — la progressione arriva con l'account (task AC2)
    for f in fenomeni:
        f["stato"] = "libero"
    return jsonify({
        "disciplina": disciplina_nome,
        "fenomeni": fenomeni,
        "totale": len(fenomeni)
    })
