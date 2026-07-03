# ============================================================
# MATTER — server. Riceve una domanda, naviga il grafo in
# profondita (risale ai fenomeni), costruisce un contesto ricco,
# e chiede a Mistral di rispondere SENZA inventare.
# Flask + grafo (Postgres su Railway / SQLite in locale) + Mistral via HTTP.
# ============================================================
import os, json, sqlite3, pathlib, difflib
from flask import Flask, request, jsonify, render_template
import motore as Motore

app = Flask(__name__)
HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"

DATABASE_URL = os.environ.get("DATABASE_URL")


class _PgRow(dict):
    """Riga Postgres accessibile come dizionario, per compatibilita con sqlite3.Row
    (il resto del codice usa n["id"], n["data"], ecc. — qui funziona identico)."""
    pass


class _PgCompat:
    """Avvolge una connessione Postgres per farla sembrare sqlite3:
    stessa firma db.execute(sql, params).fetchone()/.fetchall(), stesso
    accesso a riga come dizionario. Traduce i placeholder '?' in '%s'.
    Cosi tutte le query esistenti restano IDENTICHE — zero rischio sulla logica."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = [_PgRow(zip(cols, r)) for r in cur.fetchall()]
            return _PgCursorResult(rows)
        self._conn.commit()
        return _PgCursorResult([])


class _PgCursorResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


_pg_conn = None  # connessione persistente, riusata tra le richieste


def _connetti_postgres():
    global _pg_conn
    import psycopg2
    if _pg_conn is None or _pg_conn.closed:
        _pg_conn = psycopg2.connect(DATABASE_URL)
    return _PgCompat(_pg_conn)


def carica_grafo():
    """Su Railway (DATABASE_URL impostata): riusa la connessione Postgres,
    NIENTE ricostruzione a ogni chiamata — il grafo e gia li, caricato una
    volta con migrate_postgres.py.
    In locale (nessuna DATABASE_URL): ricostruisce SQLite in memoria dai
    seed, comodo per lo sviluppo senza dover avere Postgres a portata."""
    if DATABASE_URL:
        return _connetti_postgres()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    schema = (GRAFO/"schema.sql").read_text(encoding="utf-8").replace("JSONB","TEXT")
    db.executescript(schema)
    for s in sorted(GRAFO.glob("seed-*.sql")):
        db.executescript(s.read_text(encoding="utf-8"))
    return db


def _dati(campo):
    """Il campo 'data' arriva come stringa JSON da SQLite, ma già come
    dict da Postgres (JSONB). Questa funzione gestisce entrambi i casi
    senza che il resto del codice debba saperlo."""
    if campo is None:
        return {}
    if isinstance(campo, dict):
        return campo
    return json.loads(campo or "{}")


def _scheda_lang(data_dict, lang="it"):
    """GT4 — Legge il campo scheda nel formato multilingua.
    Supporta sia il formato legacy (stringa) sia il nuovo formato {it:"...", en:"..."}.
    Quando tutti i nodi saranno migrati al formato dizionario, il fallback legacy si rimuove."""
    scheda = data_dict.get("scheda", "")
    if isinstance(scheda, dict):
        return scheda.get(lang) or scheda.get("it") or ""
    return scheda or ""

# ---- ricerca contesto: profonda, centrata sui fenomeni ----
def _domanda_chiede_perche(domanda):
    """True se la domanda chiede il principio sottostante ('perché', 'causa', ecc.)
    In quel caso includiamo gli archi relation='spiega' nel contesto."""
    parole = {"perché", "perche", "causa", "principio", "legge", "spiega", "spiegami",
               "why", "because", "underlying", "behind"}
    return any(p in domanda.lower() for p in parole)


def cerca_contesto(db, termine, domanda=""):
    t = f"%{termine.lower()}%"
    hit = db.execute(
        "SELECT * FROM nodes WHERE lower(name) LIKE ? ORDER BY "
        "CASE type WHEN 'Fenomeno' THEN 0 WHEN 'Prodotto' THEN 1 "
        "WHEN 'Errore' THEN 2 ELSE 3 END LIMIT 4", (t,)).fetchall()
    if not hit:
        return None

    fenomeni = {}
    def aggiungi_fenomeno(fid):
        if fid in fenomeni: return
        f = db.execute("SELECT * FROM nodes WHERE id=? AND type='Fenomeno'", (fid,)).fetchone()
        if f: fenomeni[fid] = f

    prodotti_interesse = set()
    for n in hit:
        if n["type"] == "Fenomeno":
            aggiungi_fenomeno(n["id"])
        elif n["type"] == "Prodotto":
            prodotti_interesse.add(n["id"])
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])
        elif n["type"] == "Errore":
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='fallisce_come'", (n["id"],)):
                prodotti_interesse.add(e["from_id"])
                for f in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (e["from_id"],)):
                    aggiungi_fenomeno(f["from_id"])
        else:
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=?", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])

    if not fenomeni:
        for n in hit:
            fenomeni[n["id"]] = n

    # include i principi (iper-archi) solo se la domanda chiede il "perché"
    includi_principi = _domanda_chiede_perche(domanda)

    ctx = []
    for fid, f in fenomeni.items():
        nodo = dict(f); nodo["data"] = _dati(f["data"])
        coll = []
        for e in db.execute("""SELECT e.relation, e.data, n.name, n.type, n.domain, n.id
                               FROM edges e JOIN nodes n ON n.id=e.to_id
                               WHERE e.from_id=?
                               AND e.relation != 'spiega'""", (fid,)):
            coll.append({"verso": e["name"], "tipo": e["type"], "dominio": e["domain"],
                         "relazione": e["relation"], "id": e["id"],
                         "data": _dati(e["data"])})
        # aggiungi principi che spiegano questo fenomeno solo se la domanda lo chiede
        if includi_principi:
            for e in db.execute("""SELECT n.name, n.id, n.data FROM edges e
                                   JOIN nodes n ON n.id=e.from_id
                                   WHERE e.to_id=? AND e.relation='spiega'
                                   AND n.type='principio'""", (fid,)):
                d = _dati(e["data"])
                coll.append({"verso": e["name"], "tipo": "principio", "dominio": "trasversale",
                             "relazione": "spiega", "id": e["id"], "data": d})
        nodo["collegamenti"] = coll
        ctx.append(nodo)

    errori = []
    for pid in prodotti_interesse:
        for row in db.execute("""SELECT n.name, n.data, n.domain FROM edges e
                                 JOIN nodes n ON n.id=e.to_id
                                 WHERE e.from_id=? AND e.relation='fallisce_come'""", (pid,)):
            d = _dati(row["data"])
            if d.get("causa"):
                errori.append(f"{row['name']} ({row['domain']}): {d['causa']}")
    return {"fenomeni": ctx, "errori": errori, "prodotti": list(prodotti_interesse)}

# ---- costruisce il prompt -----------------------------------
_STOPWORD = {"quanto","costa","tempo","oggi","sempre","abbastanza","molto","poco",
             "questo","quella","quello","perche","perché","dopo","prima","viene",
             "fanno","fatto","faccio","vorrei","volevo","sento","vedo","sono",
             "della","dello","delle","degli","quando","dove","come","cosa"}


def cerca_fuzzy(db, domanda):
    """Quando nessun termine estratto matcha ESATTAMENTE un nodo, cerca per
    SOMIGLIANZA parola-per-parola tra la domanda e i nomi dei nodi del grafo.
    Gestisce forme diverse della stessa parola (es. 'rosolisce' vs 'rosolata',
    'lievita' vs 'lievito') senza generare falsi positivi su parole comuni
    italiane (stopword) o parole troppo corte per essere distintive."""
    tutti = db.execute("SELECT id, name, type FROM nodes").fetchall()
    parole_domanda = [p.strip(".,?!").lower() for p in domanda.split()
                       if len(p) > 4 and p.strip(".,?!").lower() not in _STOPWORD]
    if not parole_domanda:
        return None

    candidati = set()
    for n in tutti:
        for parola_nodo in n["name"].lower().split():
            parola_nodo = parola_nodo.strip("(),./")
            if parola_nodo in _STOPWORD or len(parola_nodo) < 5:
                continue
            for p in parole_domanda:
                if difflib.SequenceMatcher(None, p, parola_nodo).ratio() > 0.8:
                    candidati.add(n["name"])
                    break

    for nome in candidati:
        ctx = cerca_contesto(db, nome)
        if ctx and ctx.get("fenomeni"):
            return ctx
    return None


def fenomeni_suggeriti(db):
    """Ultima rete di sicurezza: se proprio non si trova nulla, non si lascia
    l'utente con un vicolo cieco. Si mostrano i fenomeni del grafo come punto
    di partenza — l'utente può cliccare e iniziare da lì."""
    rows = db.execute(
        "SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY name").fetchall()
    return [{"id": r["id"], "nome": r["name"], "dominio": r["domain"],
             "target": _dati(r["data"]).get("numero_bersaglio", "")} for r in rows]

def costruisci_prompt(domanda, contesto):
    righe = []
    for f in contesto["fenomeni"]:
        righe.append("")
        righe.append(f"### Fenomeno: {f['name']} ({f['domain']})")
        if f["data"].get("scheda"):
            righe.append(f["data"]["scheda"])
        manif = [c for c in f["collegamenti"] if c["relazione"] == "si_manifesta_in"]
        misu  = [c for c in f["collegamenti"] if c["relazione"] == "misurato_da"]
        proc  = [c for c in f["collegamenti"] if c["relazione"] == "realizzato_da"]
        tecn  = [c for c in f["collegamenti"] if c["relazione"] == "controllato_con"]
        if misu:
            righe.append("Si misura con: " + ", ".join(c["verso"] for c in misu))
        if proc:
            righe.append("Si realizza con: " + ", ".join(c["verso"] for c in proc))
        if manif:
            righe.append("Si manifesta in questi prodotti (coi numeri-bersaglio):")
            for c in manif:
                tgt = c["data"].get("target",""); ruolo = c["data"].get("ruolo","")
                righe.append(f"  - {c['verso']} [{c['dominio']}]: {tgt} — {ruolo}")
        if tecn:
            righe.append("Si controlla con: " + ", ".join(c["verso"] for c in tecn))
    if contesto.get("errori"):
        righe.append("")
        righe.append("Errori possibili e loro causa:")
        for e in contesto["errori"]:
            righe.append(f"  - {e}")
    contesto_txt = "\n".join(righe)

    regole = (
        "Sei uno strumento che spiega la ristorazione attraverso i fenomeni fisici "
        "e chimici che la governano: acidita, concentrazione, calore, osmosi, struttura. "
        "Questi fenomeni non appartengono a una disciplina: sono le stesse leggi che "
        "attraversano pasticceria, panificazione, cucina, mixology, caffetteria. "
        "Una madre, un sour e una confettura obbediscono alla stessa acidita; non sono "
        "mestieri diversi che si somigliano, sono lo stesso fenomeno in stanze diverse. "
        "Il tuo compito e rendere visibile questa unita: parti dal fenomeno, mostra il "
        "numero che lo governa, e fai vedere che la stessa legge ricompare dove non ce lo si aspetta.\n\n"
        "COME RISPONDERE:\n"
        "- Usa SOLO le informazioni nel contesto qui sotto. Non aggiungere prodotti, esempi "
        "o numeri che non sono nel contesto. Se un dato non c'e, non inventarlo: dillo.\n"
        "- Cita i numeri-bersaglio esatti del contesto (pH, Brix, percentuali, gradi).\n"
        "- Parti dal fenomeno e dal perche fisico, poi arriva al consiglio concreto.\n"
        "- Tono da collega a collega: il professionista sa gia fare il suo lavoro, "
        "tu gli mostri il perche. Non spiegare l'ovvio, non dare lezioni.\n"
        "- Mostra la connessione cross-disciplina solo dove e davvero nel contesto, "
        "e falla emergere come un fatto naturale: 'la stessa legge vale anche per i crauti' "
        "non 'come puoi vedere dall'analisi trasversale...'.\n"
        "- Se la domanda ha numeri propri dell'utente (ml, grammi, gradi, percentuali), "
        "usa il tool 'calcola' per dare risultati esatti — non stimare.\n"
        "- Prosa pulita in italiano, senza asterischi, grassetti o markdown. Massimo 6-8 frasi.\n"
        "- Non menzionare mai di essere un AI o di usare un grafo — rispondi come uno strumento."
    )
    return f"{regole}\n\nCONTESTO DAL GRAFO:\n{contesto_txt}\n\nDOMANDA: {domanda}\n\nRISPOSTA:"

# ---- Mistral via HTTP diretto (nessun SDK) ------------------
def _mistral_raw(prompt, max_tokens=None):
    """Chiamata Mistral grezza, riusata sia per la risposta sia per l'estrazione entità."""
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None
    import urllib.request
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role":"user","content":prompt}],
        "temperature": 0
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def estrai_entita(domanda):
    """Fa estrarre a Mistral i concetti del dominio, per agganciare meglio i nodi del grafo.
    Esempio: 'perché la carne non rosola?' -> ['rosolatura','carne','Maillard'].
    Se fallisce, ritorna [] e il chiamante ripiega sulle parole della domanda."""
    prompt = (
        "Sei un estrattore di concetti per uno strumento di scienza della ristorazione. "
        "Dalla domanda qui sotto estrai da 1 a 4 termini-chiave: il fenomeno fisico-chimico "
        "coinvolto (es. Maillard, acidità, fermentazione, estrazione, carbonatazione, osmosi, "
        "concentrazione, calore, struttura) e/o il prodotto (es. carne, pane, caffè, confettura). "
        "Rispondi SOLO con i termini separati da virgola, nient'altro.\n\n"
        f"Domanda: {domanda}\nTermini:"
    )
    try:
        out = _mistral_raw(prompt, max_tokens=40)
        if not out:
            return []
        termini = [t.strip(" .\n").lower() for t in out.split(",")]
        return [t for t in termini if t][:4]
    except Exception:
        return []

# ── TOOL DEFINITIONS per tool-calling Sonnet → motore.py ──────────
_TOOLS = [
    {
        "name": "calcola",
        "description": "Esegui un calcolo deterministico esatto (diluizione, bilanciamento sour, idratazione pane, Q10, estrazione caffè, pareggiamento acidità). Usa questo tool quando la domanda contiene numeri propri dell'utente — non stimare mai, chiama sempre il motore.",
        "input_schema": {
            "type": "object",
            "properties": {
                "calcolo": {
                    "type": "string",
                    "enum": ["diluizione","bilanciamento_sour","idratazione_pane","q10_fermentazione","estrazione_caffe","pareggia_acidita"],
                    "description": "Il tipo di calcolo da eseguire"
                },
                "parametri": {
                    "type": "object",
                    "description": "Parametri del calcolo (varia per tipo)"
                }
            },
            "required": ["calcolo","parametri"]
        }
    }
]

def _anthropic_raw(prompt):
    """Chiamata a Sonnet con tool-calling per motore.py.
    Quando la domanda ha numeri propri dell'utente, Sonnet chiama il motore
    invece di stimare — risultato deterministico, zero invenzione."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import urllib.request
    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 800,
        "temperature": 0,
        "tools": _TOOLS,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))

    # gestisci tool_use: se Sonnet chiama il motore, esegui e dai il risultato
    testo = []
    tool_results = []
    for block in data.get("content", []):
        if block.get("type") == "text":
            testo.append(block.get("text",""))
        elif block.get("type") == "tool_use":
            tool_id = block.get("id","")
            tool_input = block.get("input", {})
            risultato = Motore.esegui(tool_input.get("calcolo",""), tool_input.get("parametri",{}))
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(risultato, ensure_ascii=False)
            })

    # se c'era un tool call, fai una seconda chiamata con il risultato
    if tool_results:
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": data.get("content", [])},
            {"role": "user", "content": tool_results}
        ]
        body2 = json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 800,
            "temperature": 0,
            "messages": messages
        }).encode("utf-8")
        req2 = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body2,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req2, timeout=30) as r2:
            data2 = json.loads(r2.read().decode("utf-8"))
        return "".join(b.get("text","") for b in data2.get("content",[]) if b.get("type")=="text")

    return "".join(testo) if testo else None


def chiedi_mistral(prompt):
    """Nome storico mantenuto per non toccare i due punti che la chiamano.
    Prova Sonnet (qualità migliore sul grafo ricco); se la chiave non c'è
    o la chiamata fallisce, ripiega su Mistral — il prodotto non si ferma."""
    try:
        out = _anthropic_raw(prompt)
        if out:
            return out
    except Exception:
        pass
    try:
        out = _mistral_raw(prompt)
        return out if out is not None else None
    except Exception as e:
        return f"[errore nella chiamata: {e}]"

def log_evento(tipo, domanda, fenomeni=None, esito=None):
    """Log minimo per osservabilità: cosa chiedono gli utenti, cosa trova il grafo,
    dove fallisce. Una riga per evento, tabella separata in Postgres.
    Wrapped in try/except: se il log fallisce, la risposta arriva lo stesso."""
    if not DATABASE_URL:
        return  # in locale non logghiamo
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS log_domande (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                tipo TEXT,
                domanda TEXT,
                fenomeni_trovati TEXT,
                esito TEXT
            )
        """)
        cur.execute(
            "INSERT INTO log_domande (tipo, domanda, fenomeni_trovati, esito) VALUES (%s,%s,%s,%s)",
            (tipo, domanda[:500],
             ",".join(fenomeni) if fenomeni else None,
             esito)
        )
        conn.commit()
        cur.close(); conn.close()
    except Exception:
        pass  # mai bloccare la risposta per un log fallito


# ---- endpoint -----------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    """IN3 — Endpoint per monitoring (UptimeRobot punta qui).
    Verifica che Flask risponda E che Postgres sia raggiungibile."""
    try:
        db = carica_grafo()
        r = db.execute("SELECT count(*) as n FROM nodes").fetchone()
        nodi = r["n"] if r else 0
        return jsonify({"status": "ok", "nodi": nodi, "ts": time.time()})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/chiedi", methods=["POST"])
def chiedi():
    domanda = (request.json or {}).get("domanda","").strip()
    if not domanda:
        return jsonify({"errore":"domanda vuota"}), 400
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

    prompt = costruisci_prompt(domanda, contesto)
    risposta = chiedi_mistral(prompt)
    log_evento("risposta", domanda,
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
    return jsonify({
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta,
        "connessi": connessi
    })

@app.route("/nodo", methods=["POST"])
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
    prompt = costruisci_prompt(domanda, contesto)
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

import random, time

# cache semplice per il fenomeno del giorno (ruota ogni 24h)
_cache_home = {"ts": 0, "data": None}

@app.route("/home")
def home_api():
    """FE1 — Fenomeno del giorno + principio del giorno.
    Ruota ogni 24h. Sblocca la tab Scopri dinamica."""
    global _cache_home
    now = time.time()
    if now - _cache_home["ts"] < 86400 and _cache_home["data"]:
        return jsonify(_cache_home["data"])
    db = carica_grafo()
    fenomeni = db.execute(
        "SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY id"
    ).fetchall()
    principi = db.execute(
        "SELECT id, name, data FROM nodes WHERE type='principio' AND data::text NOT LIKE '%candidato%' ORDER BY id"
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
            "target": fd.get("target", ""),
            "scheda_intro": (fd.get("scheda", "") or "")[:200]
        }
    }
    if principi:
        p = principi[0]
        pd = _dati(p["data"])
        result["principio"] = {
            "id": p["id"],
            "nome": p["name"],
            "scheda_intro": (pd.get("scheda", "") or "")[:200]
        }
    _cache_home["ts"] = now
    _cache_home["data"] = result
    return jsonify(result)


@app.route("/disciplina/<nome>")
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
    if not fen_ids:
        # fallback: tutti i fenomeni
        tutti = db.execute(
            "SELECT id, name, data FROM nodes WHERE type='Fenomeno' ORDER BY name"
        ).fetchall()
        fenomeni = [{"id": f["id"], "nome": f["name"],
                     "target": _dati(f["data"]).get("target", "")} for f in tutti]
    else:
        fenomeni = []
        for fid in sorted(fen_ids):
            f = db.execute("SELECT id, name, data FROM nodes WHERE id=?", (fid,)).fetchone()
            if f:
                fenomeni.append({"id": f["id"], "nome": f["name"],
                                  "target": _dati(f["data"]).get("target", "")})
    return jsonify({"disciplina": nome, "fenomeni": fenomeni, "totale": len(fenomeni)})


@app.route("/lezione/<disciplina_nome>/<int:step>")
def lezione(disciplina_nome, step):
    """FE3 — Nodo del passo corrente + scheda + quiz generato da Sonnet.
    Il quiz ha sempre: domanda + 3 opzioni + spiegazione matematica."""
    db = carica_grafo()
    # recupera fenomeni della disciplina
    resp = disciplina(disciplina_nome).get_json()
    fenomeni = resp.get("fenomeni", [])
    if not fenomeni:
        return jsonify({"errore": "disciplina non trovata o vuota"})
    idx = max(0, min(step, len(fenomeni) - 1))
    f_info = fenomeni[idx]
    nodo = db.execute("SELECT * FROM nodes WHERE id=?", (f_info["id"],)).fetchone()
    if not nodo:
        return jsonify({"errore": "nodo non trovato"})
    nd = _dati(nodo["data"])
    scheda = nd.get("scheda", "") or ""
    target = nd.get("target", "")
    # principio collegato
    principio = None
    pr = db.execute("""SELECT n.name, n.data FROM edges e
                       JOIN nodes n ON n.id=e.from_id
                       WHERE e.to_id=? AND e.relation='spiega'
                       AND n.type='principio'""", (nodo["id"],)).fetchone()
    if pr:
        principio = {"nome": pr["name"],
                     "testo": (_dati(pr["data"]).get("scheda","") or "")[:300]}
    # quiz generato da Sonnet
    quiz = None
    if scheda:
        quiz_prompt = f"""Crea un quiz su questo fenomeno per un professionista F&B.
Fenomeno: {nodo['name']}
Numero bersaglio: {target}
Contenuto: {scheda[:400]}

Rispondi SOLO con JSON valido, nessun testo prima o dopo:
{{"domanda":"...","opzioni":["opzione giusta","opzione sbagliata","opzione sbagliata"],"corretta":0,"spiegazione":"spiegazione con il calcolo matematico in 2 righe"}}

La risposta corretta deve essere sempre la prima opzione (indice 0).
La spiegazione deve includere il numero esatto."""
        try:
            raw = chiedi_mistral(quiz_prompt)
            if raw:
                import re
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    quiz_data = json.loads(m.group())
                    # mescola le opzioni
                    opzioni = quiz_data.get("opzioni", [])
                    corretta_testo = opzioni[0] if opzioni else ""
                    random.shuffle(opzioni)
                    nuovo_idx = opzioni.index(corretta_testo) if corretta_testo in opzioni else 0
                    quiz = {
                        "domanda": quiz_data.get("domanda", ""),
                        "opzioni": opzioni,
                        "corretta": nuovo_idx,
                        "spiegazione": quiz_data.get("spiegazione", "")
                    }
        except Exception:
            quiz = None
    return jsonify({
        "step": idx,
        "totale_passi": len(fenomeni),
        "fenomeno": {
            "id": nodo["id"],
            "nome": nodo["name"],
            "dominio": nodo["domain"],
            "target": target,
            "scheda": scheda
        },
        "principio": principio,
        "quiz": quiz,
        "ha_precedente": idx > 0,
        "ha_successivo": idx < len(fenomeni) - 1
    })


@app.route("/mappa/<disciplina_nome>")
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



@app.route("/prezzi_mercato/<ingrediente>")
@app.route("/prezzi_mercato/<ingrediente>/<area>")
def prezzi_mercato(ingrediente, area="it"):
    """PR1 — Prezzi di mercato orientativi per area geografica.
    Fonte attuale: dati medi ISMEA incorporati nel grafo (campo prezzo_mercato).
    Futuro: aggiornamento automatico via API ISMEA/Eurostat/USDA."""
    db = carica_grafo()
    # cerca il nodo prodotto per nome
    nodi = db.execute(
        "SELECT id, name, data FROM nodes WHERE lower(name) LIKE lower(?) AND type='Prodotto' LIMIT 5",
        (f"%{ingrediente}%",)
    ).fetchall()
    risultati = []
    for n in nodi:
        d = _dati(n["data"])
        prezzo = d.get(f"prezzo_mercato_{area}") or d.get("prezzo_mercato_it")
        if prezzo:
            risultati.append({
                "ingrediente": n["name"],
                "id": n["id"],
                "prezzo": prezzo,
                "area": area,
                "fonte": "ISMEA/orientativo",
                "nota": "Prezzo medio di mercato orientativo — non vincolante"
            })
    if not risultati:
        return jsonify({
            "ingrediente": ingrediente,
            "area": area,
            "prezzo": None,
            "nota": "Prezzo non disponibile — usa i prezzi del tuo fornitore in Cifra"
        })
    return jsonify({"risultati": risultati, "totale": len(risultati)})

@app.route("/calcola", methods=["POST"])
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
