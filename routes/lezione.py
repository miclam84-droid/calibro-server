# ============================================================
# routes/lezione.py — lezioni, home, disciplina, quiz, mappa.
# Dipende da: db, ai, contenuto, utils.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import (_scheda_tradotta, _intro, _numero_bersaglio as _nb, _genera_quiz,
               _traduci_nome, log_evento)
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _err
from auth import _utente_da_token
from config import DATABASE_URL
import os, json, time, random
import ai_gateway as GW
bp = Blueprint("lezione", __name__)

_cache_home = {}       # { lang: {"ts": float, "data": dict} }
_lezione_cache = {}    # { disciplina_nome: [fenomeni] }

# Fenomeni migrati al metodo editoriale (schede VEDI/SEPARA/.../BERSAGLIO).
# La home ("fenomeno del giorno") pesca SOLO tra questi finche' gli altri nodi
# del DB hanno ancora schede vecchie. Quando un nodo viene migrato, si aggiunge qui.
_FEN_MIGRATI = {
    "fen-acidita","fen-concentrazione","fen-fermentazione","fen-maillard","fen-emulsione",
    "fen-carbonatazione","fen-chiarificazione-latte","fen-infusioni","fen-amaro-bitter","fen-collagene-brasato","fen-rosolatura","fen-emulsione-salse","fen-pasta-acqua","fen-soffritto","fen-riposo-carne","fen-uova-coagulazione","fen-verdure-verdi","fen-ossidazione","fen-osmosi","fen-viscosita","fen-denaturazione",
    "fen-cristallizzazione","fen-gelatinizzazione","fen-diluizione","fen-estrazione","fen-solubilita",
    "fen-crioscopia","fen-overrun","fen-meringa","fen-souffle","fen-sineresi","fen-ganache",
    "fen-lievitazione","fen-crosta",
}


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
    # vetrina pulita: pesca solo tra i fenomeni migrati al metodo; se (per errore)
    # nessuno matcha, ripiega su tutti per non rompere la home.
    _mig = [x for x in fenomeni if x["id"] in _FEN_MIGRATI]
    _pool = _mig if _mig else fenomeni
    # R1: il cruscotto mostra il BERSAGLIO DEL GIORNO come numero grande. Quindi scelgo
    # SOLO tra i fenomeni che hanno un numero-bersaglio vero (non vuoto). I fenomeni
    # "concettuali" senza numero (es. Viscosità) non vanno bene per il box del giorno.
    _con_numero = [x for x in _pool if _numero_bersaglio(_dati(x["data"]))]
    f = random.choice(_con_numero if _con_numero else _pool)
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
        "bar":          ["fen-acidita","fen-diluizione","fen-concentrazione","fen-carbonatazione","fen-estrazione","fen-emulsione","fen-crioscopia","fen-osmosi","fen-ossidazione","fen-clarificazione-cocktail","fen-batch-cocktail","fen-texture-agents","fen-ghiaccio-cocktail","fen-fat-washing"],
        "caffetteria":  ["fen-estrazione","fen-estrazione-caffe","fen-concentrazione","fen-pressione","fen-trasferimento-calore","fen-acidita","fen-attivita-enzimatica","fen-temperatura-latte","fen-tostatura-caffe","fen-water-recipe-caffe"],
        "panificazione":["fen-acidita","fen-fermentazione","fen-fermentazione-lattica","fen-maglia-glutinica","fen-lievitazione","fen-crosta","fen-sale-impasto","fen-enzimi-farina","fen-shelf-life-pane","fen-poolish-biga","fen-lievito-madre","fen-tangzhong-yudane","fen-levain-pate-fermentee","fen-frittura-lievitati","fen-haccp","fen-attivita-acqua","fen-catena-freddo","fen-conserve-botulino","fen-anisakis","fen-ustioni-olio","fen-equilibrio-cocktail","fen-shakerare-mescolare","fen-emulsione-bar","fen-ghiaccio","fen-carbonatazione","fen-laminazione","fen-gelatinizzazione","fen-retrogradazione","fen-concentrazione","fen-osmosi","fen-autolisi","fen-grassi-impasto","fen-zuccheri-impasto","fen-uova-impasto","fen-latte-impasto","fen-idratazione","fen-farina-forza","fen-temperatura-impasto"],
        "cucina":       ["fen-maillard","fen-denaturazione","fen-coagulazione","fen-emulsione","fen-acidita","fen-osmosi","fen-trasferimento-calore","fen-punto-fumo","fen-cottura-sous-vide","fen-gelificazione","fen-brodo-fondo","fen-frittura"],
        "pasticceria":  ["fen-emulsione","fen-cristallizzazione","fen-caramellizzazione","fen-maillard","fen-gelatinizzazione","fen-denaturazione","fen-sineresi","fen-gelificazione","fen-temperaggio-cioccolato","fen-ganache","fen-souffle","fen-pasta-frolla","fen-montatura-panna","fen-cristalli-ghiaccio","fen-zuccheri-pac","fen-grassi-stabilizzanti","fen-fermentazione-alcolica","fen-tannini-vino","fen-luppolo","fen-macinatura-caffe","fen-zucchero-cottura"],
        "gelateria":    ["fen-crioscopia","fen-cristallizzazione-ghiaccio","fen-overrun","fen-concentrazione","fen-emulsione","fen-pac-gelateria","fen-stabilizzanti-gelato","fen-bilanciamento-gelato","fen-overrun-controllo"],
        "vino":         ["fen-acidita","fen-malolattica","fen-ossidazione","fen-fermentazione","fen-tannini","fen-chiarificazione","fen-solforosa","fen-maturazione-legno","fen-estrazione-polifenoli","fen-rifermentazione","fen-acidita-volatile","fen-brett"],
        "birra":        ["fen-fermentazione","fen-carbonatazione","fen-amilolisi","fen-acidita","fen-ossidazione","fen-attivita-enzimatica","fen-mash-enzimi","fen-isomerizzazione-luppolo","fen-dry-hopping","fen-lagering","fen-fermentazione-alta-bassa","fen-efficienza-birra"],
    }
    # GERARCHIA madre→applicazioni (ontologia fenomeno/applicazione).
    # Le applicazioni ereditano il fenomeno-madre e NON compaiono al primo livello:
    # vengono annidate sotto la madre in un campo "applicazioni". Riduce il muro di voci.
    GERARCHIA = {
        "bar": {
            "fen-estrazione": ["fen-infusione","fen-cold-brew","fen-estrazione-polifenoli","fen-fat-washing","fen-maturazione-legno","fen-dry-hopping"],
            "fen-fermentazione": ["fen-fermentazione-acetica","fen-fermentazione-alta-bassa","fen-malolattica","fen-brett","fen-lagering","fen-rifermentazione"],
            "fen-ossidazione": ["fen-solforosa","fen-acidita-volatile","fen-affinamento-vino"],
            "fen-carbonatazione": ["fen-pressione"],
            "fen-diluizione": ["fen-ghiaccio-cocktail","fen-batch-cocktail","fen-cristallizzazione-ghiaccio"],
            "fen-emulsione": ["fen-texture-agents"],
            "fen-estrazione-caffe": [],
            "fen-concentrazione": ["fen-clarificazione-cocktail","fen-chiarificazione"],
            "fen-attivita-enzimatica": ["fen-amilolisi"],
            "fen-calore": ["fen-trasferimento-calore"],
        },
        "panificazione": {
            "fen-fermentazione": ["fen-fermentazione-lattica","fen-poolish-biga"],
            "fen-maglia-glutinica": ["fen-laminazione","fen-autolisi"],
            "fen-gelatinizzazione": ["fen-retrogradazione","fen-shelf-life-pane"],
            "fen-osmosi": ["fen-sale-impasto"],
            "fen-enzimi-farina": [],
        },
    }
    # CASI-STUDIO (proc-*): livello separato, non fenomeni. Restano fuori dal primo livello.
    CASI = {
        "bar": ["proc-negroni-inconsistente","proc-q10-filo-rosso","proc-variabilita-lime"],
        "panificazione": ["proc-pane-non-lievita","proc-crosta-pallida"],
    }

    # Alias: l'app usa a volte nomi diversi per la stessa disciplina.
    # Senza questi, 'caffe'/'bakery' cadono nel fallback che restituisce TUTTI i 101 fenomeni.
    ALIAS = {"caffe": "caffetteria", "coffee": "caffetteria",
             "bakery": "panificazione", "pane": "panificazione"}
    nome_key = ALIAS.get(nome.lower(), nome.lower())
    priorita_disc = PRIORITA.get(nome_key, [])

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
        # Disciplina non riconosciuta e senza prodotti collegati.
        # NON restituiamo tutti i 101 fenomeni globali (esperienza pessima):
        # meglio un set vuoto con flag, così il frontend può mostrare
        # "disciplina in arrivo" invece di un elenco caotico e non pertinente.
        return jsonify({"disciplina": nome, "fenomeni": [], "totale": 0,
                        "non_disponibile": True})
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
    # RAGGRUPPAMENTO ontologico: annida le applicazioni sotto le madri e stacca i casi.
    gerarchia = GERARCHIA.get(nome_key, {})
    casi_ids = set(CASI.get(nome_key, []))
    if gerarchia or casi_ids:
        # indice id → oggetto fenomeno (per pescare nome/target delle applicazioni)
        per_id = {f["id"]: f for f in fenomeni}
        # tutti gli id che sono applicazioni (annidati) o casi → non vanno al primo livello
        figli = set()
        for madre, apps in gerarchia.items():
            figli.update(apps)
        top = []
        for f in fenomeni:
            fid = f["id"]
            if fid in figli or fid in casi_ids:
                continue  # sarà annidato o è un caso
            # se è una madre, allego le sue applicazioni presenti nella disciplina
            apps = gerarchia.get(fid, [])
            if apps:
                f = dict(f)
                f["applicazioni"] = [
                    {"id": a, "nome": per_id[a]["nome"], "target": per_id[a].get("target","")}
                    for a in apps if a in per_id
                ]
            top.append(f)
        casi = []
        for c in casi_ids:
            if c in per_id:
                casi.append({"id": c, "nome": per_id[c]["nome"]})
            else:
                # caso nuovo (nodo Processo non collegato a prodotti): lo cerco nel DB
                cr = db.execute("SELECT id, name FROM nodes WHERE id=?", (c,)).fetchone()
                if cr:
                    casi.append({"id": cr["id"], "nome": cr["name"]})
        return jsonify({"disciplina": nome, "fenomeni": top, "totale": len(top),
                        "casi": casi})
    return jsonify({"disciplina": nome, "fenomeni": fenomeni, "totale": len(fenomeni)})

@bp.route("/lezione/<disciplina_nome>/<int:step>")
def lezione(disciplina_nome, step):
    """FE3 — Nodo del passo corrente + scheda + quiz.
    step 0 = free · step 1+ = Pro only."""
    lang = request.args.get("lang", "it")
    token = request.args.get("token","") or request.headers.get("X-Token","")
    # NUOVA NARRAZIONE (paywall per-parti): il fenomeno è SEMPRE accessibile (la scienza è
    # gratis). Per gli utenti free calcolo solo un flag pro_locked, che dice al frontend
    # di sfocare il DATO numerico e gli ERRORI-DA-BANCO (non l'intera scheda).
    pro_locked = False
    if DATABASE_URL:
        try:
            uid = _utente_da_token(token)
            piano = "free"
            if uid:
                _conn_l = _get_conn(); _cur_l = _conn_l.cursor()
                _cur_l.execute("SELECT piano FROM utenti WHERE id=%s", (uid,))
                r = _cur_l.fetchone()
                piano = r[0] if r else "free"
                _cur_l.close(); _release_conn(_conn_l)
            pro_locked = (piano != "pro")
        except Exception:
            pro_locked = True  # in dubbio, sfoco (sicuro per i costi)
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
    # ═══ SCAVA — le ramificazioni del fenomeno (motore della longevità) ═══
    # Quattro "porte" per andare più a fondo: errori, tecniche, connessioni, strumenti.
    # Mostriamo solo quelle che hanno dati VERI (niente porte vuote).
    def _pulisci_nome(s):
        # i nomi nel grafo a volte contengono markdown (#, **, _) o code fence: li tolgo
        if not s: return ""
        import re as _re
        s = _re.sub(r'[#*_`]+', '', str(s))          # simboli markdown
        s = _re.sub(r'\s*\(This refers.*$', '', s, flags=_re.I)  # code residui
        s = _re.sub(r'\s+', ' ', s).strip()
        # se ci sono due varianti "X or Y", tengo la prima (più pulita)
        if ' or ' in s.lower():
            s = _re.split(r'\s+or\s+', s, flags=_re.I)[0].strip()
        return s
    scava = {"errori": [], "tecniche": [], "connessioni": [], "strumenti": []}
    try:
        _fid = nodo["id"]
        # errori (fallisce_come): il cuore della ritenzione
        for row in db.execute("""SELECT n.name, e.data FROM edges e
                JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='fallisce_come'""", (_fid,)).fetchall():
            _d = _dati(row["data"]) if row["data"] else {}
            scava["errori"].append({"nome": _pulisci_nome(_traduci_nome(row["name"], lang)),
                                    "sintomo": _d.get("sintomo","")})
        # tecniche (realizzato_da)
        for row in db.execute("""SELECT n.name, n.data FROM edges e
                JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='realizzato_da'""", (_fid,)).fetchall():
            _dt = _dati(row["data"]) if row["data"] else {}
            scava["tecniche"].append({"nome": _pulisci_nome(_traduci_nome(row["name"], lang)),
                                      "nota": _dt.get("nota","")})
        # connessioni trasversali (unifica): la scoperta cross-disciplina
        for row in db.execute("""SELECT n.name, n.domain, e.data FROM edges e
                JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='unifica'""", (_fid,)).fetchall():
            _d = _dati(row["data"]) if row["data"] else {}
            scava["connessioni"].append({"nome": _pulisci_nome(_traduci_nome(row["name"], lang)),
                                         "dominio": row["domain"] or "",
                                         "legame": _d.get("legge_condivisa","")})
        # anche i ponti in entrata (unifica verso questo fenomeno)
        for row in db.execute("""SELECT n.name, n.domain, e.data FROM edges e
                JOIN nodes n ON n.id=e.from_id
                WHERE e.to_id=? AND e.relation='unifica'""", (_fid,)).fetchall():
            _d = _dati(row["data"]) if row["data"] else {}
            scava["connessioni"].append({"nome": _pulisci_nome(_traduci_nome(row["name"], lang)),
                                         "dominio": row["domain"] or "",
                                         "legame": _d.get("legge_condivisa","")})
        # strumenti (controllato_con)
        for row in db.execute("""SELECT n.name FROM edges e
                JOIN nodes n ON n.id=e.to_id
                WHERE e.from_id=? AND e.relation='controllato_con'""", (_fid,)).fetchall():
            scava["strumenti"].append({"nome": _pulisci_nome(_traduci_nome(row["name"], lang))})
    except Exception:
        pass

    return jsonify({
        "step": idx,
        "totale_passi": len(fenomeni),
        "fenomeno": {
            "id": nodo["id"],
            "nome": _traduci_nome(nodo["name"], lang),
            "dominio": nodo["domain"],
            "target": target,
            "scheda": scheda,
            "gancio": (nd.get("gancio") if lang == "it" else "") or ""
        },
        "principio": principio,
        "quiz": quiz,
        "scava": scava,
        "ha_precedente": idx > 0,
        "ha_successivo": idx < len(fenomeni) - 1,
        # paywall per-parti: se true, il frontend sfoca SOLO il dato numerico + gli errori-da-banco
        # (la scienza — principio, spiegazione, tecniche — resta sempre visibile)
        "pro_locked": pro_locked
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
    """FE4 — Fenomeni della disciplina con stato statico (libero/completato/Pro) E stato_utente
    dinamico (mai_aperto/studiato/misurato) letto da X-Device-Id o X-Token. Opzione B: una chiamata sola."""
    resp = disciplina(disciplina_nome).get_json()
    fenomeni = resp.get("fenomeni", [])
    casi = resp.get("casi", [])
    # stato statico: per ora tutti liberi (la progressione Pro arriva con l'account)
    for f in fenomeni:
        f["stato"] = "libero"
    # stato_utente dinamico: leggo cosa l'utente ha studiato/misurato e lo attacco per id
    try:
        from routes.stato import _chiave_utente
        from db import _get_conn, _release_conn
        tipo, chiave = _chiave_utente()
        stati_utente = {}
        if tipo:
            conn = _get_conn()
            try:
                cur = conn.cursor()
                cur.execute("""SELECT fenomeno, stato, valore, unita, in_finestra, quando
                               FROM stato_fenomeni WHERE chiave_tipo=%s AND chiave=%s""", (tipo, chiave))
                for row in cur.fetchall():
                    g = lambda i: (row[i] if not hasattr(row,"keys") else row[list(row.keys())[i]])
                    stati_utente[g(0)] = {
                        "stato_utente": g(1), "ultima_misura": g(2), "unita": g(3),
                        "in_finestra": g(4), "quando": g(5).isoformat() if g(5) else None,
                    }
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                _release_conn(conn)
        # attacco: se l'utente ha uno stato per quel fenomeno lo uso, altrimenti mai_aperto
        for f in fenomeni:
            su = stati_utente.get(f.get("id"))
            if su:
                f["stato_utente"] = su["stato_utente"]
                f["ultima_misura"] = su["ultima_misura"]
                f["unita"] = su["unita"]
                f["in_finestra"] = su["in_finestra"]
                f["quando"] = su["quando"]
            else:
                f["stato_utente"] = "mai_aperto"
    except Exception:
        # se qualcosa va storto, degrado a mai_aperto (mai rompere la mappa)
        for f in fenomeni:
            f.setdefault("stato_utente", "mai_aperto")
    return jsonify({
        "disciplina": disciplina_nome,
        "fenomeni": fenomeni,
        "casi": casi,
        "totale": len(fenomeni)
    })
