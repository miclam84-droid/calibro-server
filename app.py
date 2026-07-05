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
        "WHEN 'Errore' THEN 2 ELSE 3 END LIMIT 8", (t,)).fetchall()
    if not hit:
        return None

    fenomeni = {}
    def aggiungi_fenomeno(fid):
        if fid in fenomeni: return
        f = db.execute("SELECT * FROM nodes WHERE id=? AND type='Fenomeno'", (fid,)).fetchone()
        if f: fenomeni[fid] = f

    prodotti_interesse = set()
    prodotti_fisici = {}   # id → dati fisici (pH, Aw, ecc.)

    for n in hit:
        if n["type"] == "Fenomeno":
            aggiungi_fenomeno(n["id"])
        elif n["type"] == "Prodotto":
            prodotti_interesse.add(n["id"])
            d = _dati(n["data"])
            # raccoglie parametri fisici se presenti
            fisici = {}
            for k in ("ph_min","ph_max","ph_note","aw_min","aw_max",
                      "acidita_titolabile_pct","coagulazione_t","t_sicurezza",
                      "variabilita","abv_pct","tds_pct","brix_sciroppo_1_1",
                      "cristallizzazione_t","proteine_pct","fonte"):
                if k in d:
                    fisici[k] = d[k]
            if fisici:
                fisici["nome"] = n["name"]
                prodotti_fisici[n["id"]] = fisici
            # risali al fenomeno via governato_da o si_manifesta_in
            for e in db.execute(
                "SELECT to_id FROM edges WHERE from_id=? AND relation IN ('governato_da','si_manifesta_in')",
                (n["id"],)):
                aggiungi_fenomeno(e["to_id"])
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

    return {
        "fenomeni": ctx,
        "errori": errori,
        "prodotti": list(prodotti_interesse),
        "prodotti_fisici": list(prodotti_fisici.values())  # nuovo
    }

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

def costruisci_prompt(domanda, contesto, lang="it"):
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

    # Aggiungi parametri fisici ingredienti se presenti
    fisici = contesto.get("prodotti_fisici", [])
    if fisici:
        righe_f = ["\n### Parametri fisici ingredienti (dal dataset Matter):"]
        for p in fisici:
            nome = p.get("nome", "?")
            r = f"  {nome}:"
            if "ph_min" in p and "ph_max" in p:
                r += f" pH {p['ph_min']}-{p['ph_max']}"
            if "ph_note" in p:
                r += f" ({p['ph_note']})"
            if "variabilita" in p:
                r += f" · variabilità: {p['variabilita']}"
            if "aw_min" in p:
                r += f" · Aw {p['aw_min']}-{p.get('aw_max','?')}"
            if "coagulazione_t" in p:
                r += f" · coagulazione: {p['coagulazione_t']}"
            if "t_sicurezza" in p:
                r += f" · T sicurezza: {p['t_sicurezza']}"
            if "acidita_titolabile_pct" in p:
                r += f" · acidità titolabile: {p['acidita_titolabile_pct']}%"
            if "fonte" in p:
                r += f" · fonte: {p['fonte']}"
            righe_f.append(r)
        contesto_txt += "\n".join(righe_f)

    if lang == "en":
        regole = (
            "You are a tool that explains food and drink through the physical and chemical "
            "phenomena that govern them: acidity, concentration, heat, osmosis, structure. "
            "These phenomena belong to no single discipline — they are the same laws that run "
            "through pastry, bread, cooking, mixology, and coffee.\n\n"
            "HOW TO RESPOND:\n"
            "- Always anchor the answer to the physical phenomenon found in the context. "
            "Start from the phenomenon, show the number that governs it, then apply it to the question.\n"
            "- Use the exact target numbers from the context when available. "
            "When the context does not contain a specific product or number, "
            "use your scientific knowledge of that phenomenon to answer — "
            "do not say 'the context does not contain this data'. Just answer.\n"
            "- Never explain your reasoning process, never mention the graph, "
            "never say what you can or cannot do. Respond directly.\n"
            "- Tone: colleague to colleague. The professional knows their craft — "
            "show them the physical why. No lectures, no obvious explanations.\n"
            "- Show cross-disciplinary connections naturally when they add value.\n"
            "- If the question contains specific numbers (ml, grams, degrees, percentages), "
            "use the 'calcola' tool for exact results.\n"
            "- Clean prose, no asterisks, bold or markdown. Maximum 6-8 sentences.\n"
            "- Never mention being an AI or using a graph."
        )
    else:
        regole = (
            "Sei uno strumento che spiega la ristorazione attraverso i fenomeni fisici "
            "e chimici che la governano: acidita, concentrazione, calore, osmosi, struttura. "
            "Questi fenomeni non appartengono a una disciplina: sono le stesse leggi che "
            "attraversano pasticceria, panificazione, cucina, mixology, caffetteria.\n\n"
            "COME RISPONDERE:\n"
            "- Aggancia sempre la risposta al fenomeno fisico trovato nel contesto. "
            "Parti dal fenomeno, mostra il numero che lo governa, poi applicalo alla domanda.\n"
            "- Usa i numeri-bersaglio esatti del contesto quando ci sono. "
            "Quando il contesto non contiene un ingrediente o un prodotto specifico, "
            "usa la tua conoscenza scientifica di quel fenomeno per rispondere — "
            "non dire 'il contesto non contiene questo dato'. Rispondi e basta.\n"
            "- Non spiegare mai il tuo processo di ragionamento, non menzionare il grafo, "
            "non dire cosa puoi o non puoi fare. Rispondi direttamente.\n"
            "- Tono da collega a collega: il professionista sa gia fare il suo lavoro, "
            "tu gli mostri il perche fisico. Niente lezioni, niente ovvieta.\n"
            "- Mostra la connessione cross-disciplina quando aggiunge valore, in modo naturale.\n"
            "- Se la domanda ha numeri propri dell'utente (ml, grammi, gradi, percentuali), "
            "usa il tool 'calcola' per dare risultati esatti.\n"
            "- Prosa pulita in italiano, senza asterischi, grassetti o markdown. Massimo 6-8 frasi.\n"
            "- Non menzionare mai di essere un AI o di usare un grafo."
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


def _haiku_raw(prompt, max_tokens=600):
    """Haiku 4.5 per compiti semplici: quiz, traduzioni. Costo ~4x inferiore a Sonnet."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import urllib.request
    body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        return "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    except Exception:
        return None


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
        import psycopg2
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



# ── ACCOUNT UTENTE (AC2) ──────────────────────────────────────────
def _init_account_tables():
    """Crea le tabelle account se non esistono. Chiamata al primo avvio."""
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                id          SERIAL PRIMARY KEY,
                ts          TIMESTAMPTZ DEFAULT NOW(),
                email       TEXT UNIQUE NOT NULL,
                password_h  TEXT NOT NULL,
                piano       TEXT DEFAULT 'free',
                attivo      BOOLEAN DEFAULT TRUE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessioni (
                token       TEXT PRIMARY KEY,
                user_id     INTEGER REFERENCES utenti(id),
                ts          TIMESTAMPTZ DEFAULT NOW(),
                scade       TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
            )
        """)
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"[account tables] {e}")

def _hash_pw(password):
    import hashlib, os
    salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"

def _verifica_pw(password, stored):
    import hashlib
    try:
        salt, h = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

def _genera_token():
    import secrets
    return secrets.token_urlsafe(32)

def _utente_da_token(token):
    """Restituisce user_id se il token è valido e non scaduto."""
    if not DATABASE_URL or not token:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM sessioni WHERE token=%s AND scade > NOW()",
            (token,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return row[0] if row else None
    except Exception:
        return None

@app.route("/v1/auth/registra", methods=["POST"])
def registra():
    """AC2 — Registrazione utente con email + password."""
    body = request.json or {}
    email = (body.get("email","")).strip().lower()
    password = body.get("password","")
    if not email or not password:
        return jsonify({"errore":"email e password obbligatorie"}), 400
    if len(password) < 8:
        return jsonify({"errore":"password minimo 8 caratteri"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO utenti (email, password_h) VALUES (%s,%s) RETURNING id",
                    (email, _hash_pw(password)))
        user_id = cur.fetchone()[0]
        token = _genera_token()
        cur.execute("INSERT INTO sessioni (token, user_id) VALUES (%s,%s)", (token, user_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"token":token,"piano":"free","messaggio":"Benvenuto in Matter."})
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"errore":"email già registrata"}), 409
        return jsonify({"errore":str(e)}), 500

@app.route("/v1/auth/login", methods=["POST"])
def login():
    """AC2 — Login con email + password, restituisce token sessione."""
    body = request.json or {}
    email = (body.get("email","")).strip().lower()
    password = body.get("password","")
    if not email or not password:
        return jsonify({"errore":"email e password obbligatorie"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT id, password_h, piano FROM utenti WHERE email=%s AND attivo=TRUE",
                    (email,))
        row = cur.fetchone()
        if not row or not _verifica_pw(password, row[1]):
            cur.close(); conn.close()
            return jsonify({"errore":"credenziali non valide"}), 401
        user_id, _, piano = row
        token = _genera_token()
        cur.execute("INSERT INTO sessioni (token, user_id) VALUES (%s,%s)", (token, user_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"token":token,"piano":piano})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/quaderno", methods=["GET"])
def quaderno_lista():
    """AC3 — Lista esperimenti salvati dall'utente."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"esperimenti":[]})
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts, ph, brix, abv, ey_perc,
                   temperatura, idratazione, costo_mercato_eur
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC LIMIT 50
        """, (str(user_id),))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols,[str(v) if v is not None else None for v in r])) for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify({"esperimenti":rows,"totale":len(rows)})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@app.route("/v1/quaderno", methods=["POST"])
def quaderno_salva():
    """AC3 — Salva un nuovo esperimento nel quaderno."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    body = request.json or {}
    nome = body.get("nome","").strip()
    if not nome:
        return jsonify({"errore":"nome esperimento obbligatorio"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO esperimenti
            (nome, disciplina, note, ph, brix, abv, ey_perc, tds_perc,
             temperatura, idratazione, ingredienti, fenomeni,
             costo_mercato_eur, area_mercato, user_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            nome,
            body.get("disciplina"),
            body.get("note"),
            body.get("ph"), body.get("brix"), body.get("abv"),
            body.get("ey_perc"), body.get("tds_perc"),
            body.get("temperatura"), body.get("idratazione"),
            json.dumps(body.get("ingredienti",[])),
            json.dumps(body.get("fenomeni",[])),
            body.get("costo_mercato_eur"),
            body.get("area_mercato","it"),
            str(user_id)
        ))
        exp_id = cur.fetchone()[0]
        conn.commit(); cur.close(); conn.close()
        return jsonify({"id":exp_id,"ok":True})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@app.route("/v1/ricetta/<int:exp_id>")
def ricetta_per_cifra(exp_id):
    """AC4 — API per Cifra: espone la ricetta fisica di un esperimento.
    Accetta sia token utente Matter che email+service key Cifra."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ingredienti, fenomeni,
                   ph, brix, abv, ey_perc, temperatura, idratazione,
                   costo_mercato_eur, area_mercato, ts
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"errore":"esperimento non trovato"}), 404
        cols = [d[0] for d in cur.description] if False else [
            "id","nome","disciplina","ingredienti","fenomeni",
            "ph","brix","abv","ey_perc","temperatura","idratazione",
            "costo_mercato_eur","area_mercato","ts"
        ]
        d = dict(zip(cols, row))
        # ingredienti già in JSONB — pronti per Cifra
        return jsonify({
            "id": d["id"],
            "nome": d["nome"],
            "disciplina": d["disciplina"],
            "ingredienti": d["ingredienti"] or [],
            "misure_fisiche": {
                "ph": d["ph"], "brix": d["brix"], "abv": d["abv"],
                "ey_perc": d["ey_perc"], "temperatura": d["temperatura"],
                "idratazione": d["idratazione"]
            },
            "fenomeni": d["fenomeni"] or [],
            "costo_mercato_eur": d["costo_mercato_eur"],
            "area_mercato": d["area_mercato"],
            "ts": str(d["ts"]),
            "nota": "Matter possiede la fisica. Cifra applica i prezzi reali del fornitore."
        })
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

import os as _os

def _auth_cifra():
    """Risolve l'identità utente per le API Cifra.
    Accetta due modalità:
    - Token utente Matter: Authorization: Bearer {token}
    - Integrazione Cifra: Authorization: Bearer {MATTER_SERVICE_KEY}
                          X-User-Email: {email_utente}
    Restituisce user_id (str) o None se non autenticato.
    """
    auth = request.headers.get("Authorization","").replace("Bearer ","").strip()
    service_key = _os.environ.get("MATTER_SERVICE_KEY","")

    # Modalità Cifra: service key + email
    if service_key and auth == service_key:
        email = request.headers.get("X-User-Email","").strip().lower()
        if not email or not DATABASE_URL:
            return None
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT id FROM utenti WHERE lower(email)=%s AND attivo=TRUE", (email,))
            row = cur.fetchone()
            cur.close(); conn.close()
            return str(row[0]) if row else None
        except Exception:
            return None

    # Modalità utente diretto: token sessione Matter
    return _utente_da_token(auth)


@app.route("/v1/ricette")
def ricette_per_cifra():
    """Lista ricette (esperimenti) dell'utente — endpoint Cifra.
    Cifra passa X-User-Email + MATTER_SERVICE_KEY.
    Restituisce solo id, nome, disciplina — Cifra chiede i dettagli per ID."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC
        """, (str(user_id),))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            "id": r[0],
            "nome": r[1],
            "disciplina": r[2],
            "ts": str(r[3])
        } for r in rows])
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


def _calcola_profilo_sicurezza(ph=None, brix=None, aw=None, idratazione=None,
                               temperatura=4.0, nome=None, disciplina=None):
    """Helper condiviso per il calcolo del profilo sicurezza alimentare.
    Usato sia dall'endpoint con ricetta salvata che dall'endpoint stateless Cifra.
    Tutti i parametri sono opzionali — i valori mancanti restano None.
    """
    # ── Stima Aw ────────────────────────────────────────────
    aw_stimata = aw  # se Cifra la manda direttamente, usiamo quella
    if aw_stimata is None:
        if brix is not None:
            aw_stimata = round(1.0 - float(brix) * 0.0023, 3)
        elif idratazione is not None:
            aw_stimata = round(0.95 + float(idratazione) * 0.0004, 3)
            aw_stimata = min(aw_stimata, 0.99)

    t_cons = float(temperatura) if temperatura else 4.0
    ph_val = float(ph) if ph else None
    zona_pericolo = (t_cons > 4.0 and t_cons < 60.0)

    # ── Score Hurdle Technology ──────────────────────────────
    score = 0
    if aw_stimata is not None:
        if aw_stimata < 0.60: score += 4
        elif aw_stimata < 0.85: score += 3
        elif aw_stimata < 0.93: score += 2
        elif aw_stimata < 0.97: score += 1
    if ph_val is not None:
        if ph_val < 3.5: score += 4
        elif ph_val < 4.0: score += 3
        elif ph_val < 4.6: score += 2
        elif ph_val < 5.5: score += 1
    if t_cons <= 4: score += 2
    elif t_cons <= 8: score += 1

    giorni_map = [1, 2, 4, 7, 14, 30, 90, 180]
    shelf_life = giorni_map[min(score, 7)]

    # ── Flag rischio ─────────────────────────────────────────
    metodo_conservazione = []
    if zona_pericolo:
        flag_rischio = "conservare fuori dalla zona di pericolo (4°C–60°C)"
        metodo_conservazione = ["refrigerazione"]
    elif t_cons <= 4:
        flag_rischio = "conservare sotto 4°C — shelf life limitata" if shelf_life <= 3 else None
        metodo_conservazione = ["refrigerazione"]
    else:
        flag_rischio = "verificare temperatura di conservazione"
        metodo_conservazione = ["refrigerazione"]

    if aw_stimata and aw_stimata < 0.85:
        metodo_conservazione.append("conservazione a temperatura ambiente")
    if ph_val and ph_val < 4.6:
        metodo_conservazione.append("acidificazione")

    note = (f"shelf life orientativa {shelf_life} giorni a {t_cons}°C"
            + (f" · pH {ph_val}" if ph_val else "")
            + (f" · Aw {aw_stimata}" if aw_stimata else ""))

    return {
        "aw_stimata": aw_stimata,
        "ph_stimato": ph_val,
        "temperatura_conservazione_max_c": t_cons,
        "shelf_life_giorni": shelf_life,
        "zona_pericolo": zona_pericolo,
        "flag_rischio": flag_rischio,
        "metodo_conservazione": metodo_conservazione,
        "note_sicurezza": note,
        "disclaimer": (
            "Valori orientativi basati su modelli scientifici. "
            "Non sostituiscono test microbiologici né la consulenza "
            "di un professionista HACCP abilitato."
        )
    }


@app.route("/v1/sicurezza", methods=["POST"])
def sicurezza_stateless():
    """SEC15 — Endpoint stateless per Cifra.
    Calcola il profilo di sicurezza da parametri in input,
    senza che la ricetta esista su Matter.
    Auth: Authorization: Bearer {MATTER_SERVICE_KEY} (no X-User-Email richiesta).
    """
    auth = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    service_key = _os.environ.get("MATTER_SERVICE_KEY", "")
    if not service_key or auth != service_key:
        return jsonify({"errore": "autenticazione richiesta"}), 401

    body = request.json or {}
    nome       = body.get("nome")
    disciplina = body.get("disciplina")
    ph         = body.get("ph")
    brix       = body.get("brix")
    aw         = body.get("aw")
    idratazione = body.get("idratazione")
    temperatura = body.get("temperatura_conservazione_c", 4.0)
    ingredienti = body.get("ingredienti", [])  # lista [{nome, quantita_g}] — per ora loggata, non usata nel calcolo

    profilo = _calcola_profilo_sicurezza(
        ph=ph, brix=brix, aw=aw, idratazione=idratazione,
        temperatura=temperatura, nome=nome, disciplina=disciplina
    )
    profilo["nome"] = nome
    profilo["disciplina"] = disciplina
    profilo["ingredienti_ricevuti"] = len(ingredienti)

    return jsonify(profilo)


@app.route("/v1/ricetta/<int:exp_id>/sicurezza")
def ricetta_sicurezza(exp_id):
    """SEC14 — Profilo di sicurezza alimentare di un esperimento.
    Accetta sia token utente Matter che email+service key Cifra.
    Formato concordato con Cifra (tutti i campi nullable).
    I valori sono stime orientative basate su modelli scientifici —
    non sostituiscono test microbiologici né certificazioni professionali."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ph, brix, abv,
                   temperatura, idratazione, ingredienti, fenomeni
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return jsonify({"errore":"esperimento non trovato"}), 404

        (rid, nome, disc, ph, brix, abv,
         temp, idratazione, ingredienti, fenomeni) = row

        profilo = _calcola_profilo_sicurezza(
            ph=ph, brix=brix, aw=None, idratazione=idratazione,
            temperatura=float(temp) if temp else 4.0,
            nome=nome, disciplina=disc
        )
        profilo["id"] = rid
        profilo["nome"] = nome
        profilo["disciplina"] = disc
        return jsonify(profilo)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500
def logout():
    """AC2 — Invalida il token sessione."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    if not token or not DATABASE_URL:
        return jsonify({"ok":True})
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("DELETE FROM sessioni WHERE token=%s", (token,))
        conn.commit(); cur.close(); conn.close()
    except Exception:
        pass
    return jsonify({"ok":True})

# ---- endpoint -----------------------------------------------
# ── FLAVOR NETWORK (FL3-FL4) ─────────────────────────────────────

@app.route("/v1/abbina/<ingrediente>")
def abbina(ingrediente):
    """FL3 — Restituisce ingredienti con composti volatili condivisi.
    Query deterministica su flavor_abbinamenti — zero AI.
    Sempre marcato come ipotesi di abbinamento, mai come legge."""
    if not DATABASE_URL:
        return jsonify({"ingrediente":ingrediente,"abbinamenti":[],"nota":"flavor network non disponibile"})
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # cerca per nome esatto o simile
        cur.execute("""
            SELECT ingrediente_2, composto, overlap_score
            FROM flavor_abbinamenti
            WHERE lower(ingrediente_1) LIKE lower(%s)
            ORDER BY overlap_score DESC LIMIT 8
        """, (f"%{ingrediente}%",))
        rows = cur.fetchall()
        cur.close(); conn.close()
        abbinamenti = [
            {"ingrediente": r[0], "composto": r[1], "overlap": float(r[2]),
             "perche": f"{ingrediente.replace('_',' ')} e {r[0].replace('_',' ')} condividono {r[1]}"}
            for r in rows
        ]
        return jsonify({
            "ingrediente": ingrediente,
            "abbinamenti": abbinamenti,
            "nota": "Ipotesi di abbinamento per composti volatili condivisi — non è una garanzia nutrizionale",
            "fonte": "Dataset Ahn 2011 (CC BY) + PubChem"
        })
    except Exception as e:
        # tabella non ancora creata — avvia import
        return jsonify({
            "ingrediente": ingrediente,
            "abbinamenti": [],
            "nota": "Flavor network in costruzione — usa: python import_flavor_network.py"
        })

@app.route("/v1/abbina_batch", methods=["POST"])
def abbina_batch():
    """FL3b — Abbinamenti per lista di ingredienti (per modulo Produzione Cifra).
    Cifra passa gli ingredienti disponibili in magazzino, Matter restituisce suggerimenti."""
    ingredienti = (request.json or {}).get("ingredienti", [])
    if not ingredienti:
        return jsonify({"errore":"lista ingredienti vuota"}), 400
    risultati = {}
    for ing in ingredienti[:10]:  # limite 10 per chiamata
        r = abbina(ing).get_json()
        if r.get("abbinamenti"):
            risultati[ing] = r["abbinamenti"][:3]
    return jsonify({"risultati":risultati,"totale_ingredienti":len(ingredienti)})


@app.route("/")
def landing():
    """LP1 — Landing page pubblica. Il CTA porta a /app."""
    return render_template("landing.html")

@app.route("/app")
def home():
    """PWA principale — serve index.html."""
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
    # IN4: rate limiting per IP
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":"Troppe richieste. Aspetta un minuto e riprova."}), 429
    domanda = (request.json or {}).get("domanda","").strip()
    lang = (request.json or {}).get("lang", "it")
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

    prompt = costruisci_prompt(domanda, contesto, lang=lang)
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
    # log_id per feedback utente (AC5)
    log_id = None
    if DATABASE_URL:
        try:
            import psycopg2
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2 = conn2.cursor()
            cur2.execute("SELECT id FROM log_domande ORDER BY ts DESC LIMIT 1")
            row = cur2.fetchone()
            log_id = row[0] if row else None
            cur2.close(); conn2.close()
        except Exception:
            pass
    return jsonify({
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta,
        "connessi": connessi,
        "log_id": log_id
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

import random, time

# cache semplice per il fenomeno del giorno (ruota ogni 24h)
_cache_home = {}  # { lang: {"ts": float, "data": dict} }

@app.route("/home")
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
            "target": fd.get("target", ""),
            "scheda_intro": _scheda_lang(fd, lang)[:200]
        }
    }
    principi_attivi = [p for p in principi if "candidato" not in str(_dati(p["data"]))]
    if principi_attivi:
        p = principi_attivi[0]
        pd = _dati(p["data"])
        result["principio"] = {
            "id": p["id"],
            "nome": p["name"],
            "scheda_intro": _scheda_lang(pd, lang)[:200]
        }
    _cache_home[lang] = {"ts": now, "data": result}
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
    """FE3 — Nodo del passo corrente + scheda + quiz generato da Haiku.
    Supporta ?lang=it|en — default it."""
    lang = request.args.get("lang", "it")
    db = carica_grafo()
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
    scheda = _scheda_lang(nd, lang)
    target = nd.get("target", "")
    # principio collegato
    principio = None
    pr = db.execute("""SELECT n.name, n.data FROM edges e
                       JOIN nodes n ON n.id=e.from_id
                       WHERE e.to_id=? AND e.relation='spiega'
                       AND n.type='principio'""", (nodo["id"],)).fetchone()
    if pr:
        principio = {"nome": pr["name"], "testo": _scheda_lang(_dati(pr["data"]), lang)[:300]}
    # quiz generato da Sonnet
    quiz = None
    if scheda:
        if lang == "en":
            quiz_prompt = f"""Create a quiz about this phenomenon for an F&B professional.
Phenomenon: {nodo['name']}
Target number: {target}
Content: {scheda[:400]}

Reply ONLY with valid JSON, no text before or after:
{{"domanda":"...","opzioni":["correct option","wrong option","wrong option"],"corretta":0,"spiegazione":"explanation with the exact mathematical calculation in 2 lines"}}

The correct answer must always be the first option (index 0).
The explanation must include the exact number."""
        else:
            quiz_prompt = f"""Crea un quiz su questo fenomeno per un professionista F&B.
Fenomeno: {nodo['name']}
Numero bersaglio: {target}
Contenuto: {scheda[:400]}

Rispondi SOLO con JSON valido, nessun testo prima o dopo:
{{"domanda":"...","opzioni":["opzione giusta","opzione sbagliata","opzione sbagliata"],"corretta":0,"spiegazione":"spiegazione con il calcolo matematico in 2 righe"}}

La risposta corretta deve essere sempre la prima opzione (indice 0).
La spiegazione deve includere il numero esatto."""
        try:
            raw = _haiku_raw(quiz_prompt)  # Haiku: quiz semplice, costo ridotto
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



@app.route("/privacy")
def privacy():
    """LE2 — Privacy policy (testo minimo legale, da aggiornare con consulente)."""
    return """<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Privacy Policy — Matter</title>
<style>body{font-family:Georgia,serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.7;color:#1A1A18}
h1{font-size:24px;margin-bottom:8px}h2{font-size:18px;margin-top:32px}p,li{font-size:15px}</style>
</head><body>
<h1>Privacy Policy — Matter</h1>
<p><strong>Ultimo aggiornamento:</strong> luglio 2026</p>
<h2>Chi siamo</h2>
<p>Matter è uno strumento scientifico per professionisti F&B. Il titolare del trattamento è il soggetto che gestisce il servizio.</p>
<h2>Dati raccolti</h2>
<ul>
<li><strong>Domande al grafo:</strong> testo delle domande, fenomeni trovati, tipo di risposta. Conservati per migliorare il servizio.</li>
<li><strong>Account:</strong> email e password (in hash). Conservati fino alla cancellazione dell'account.</li>
<li><strong>Cookie tecnici:</strong> necessari per il funzionamento. Nessun cookie di profilazione.</li>
</ul>
<h2>Trasferimento dati</h2>
<p>Le domande sono processate da Anthropic (USA) e Mistral (FR) tramite API. Entrambi dispongono di garanzie adeguate per il trasferimento extra-UE.</p>
<h2>I tuoi diritti</h2>
<p>Hai diritto di accesso, rettifica, cancellazione, portabilità e opposizione. Contatta il titolare per esercitarli.</p>
<h2>Cookie</h2>
<p>Usiamo solo cookie tecnici essenziali. Puoi rifiutare i cookie non essenziali dal banner.</p>
<p><a href="/">← Torna a Matter</a></p>
</body></html>""", 200, {'Content-Type': 'text/html; charset=utf-8'}


# ── STRIPE PAGAMENTI (GT8) ────────────────────────────────────────

@app.route("/v1/stripe/checkout", methods=["POST"])
def stripe_checkout():
    """GT8 — Crea sessione Stripe Checkout per abbonamento Pro.
    Richiede STRIPE_SECRET_KEY nelle variabili Railway."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"errore":"pagamenti non configurati"}), 503
    
    try:
        import urllib.request, urllib.parse
        # crea sessione checkout Stripe
        body = urllib.parse.urlencode({
            "mode": "subscription",
            "payment_method_types[]": "card",
            "line_items[0][price]": os.environ.get("STRIPE_PRICE_PRO",""),
            "line_items[0][quantity]": "1",
            "success_url": f"{request.host_url}?piano=pro&success=1",
            "cancel_url": f"{request.host_url}?cancel=1",
            "metadata[user_id]": str(user_id)
        }).encode()
        req = urllib.request.Request(
            "https://api.stripe.com/v1/checkout/sessions",
            data=body,
            headers={"Authorization": f"Bearer {stripe_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return jsonify({"checkout_url": data.get("url"), "session_id": data.get("id")})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@app.route("/v1/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """GT8 — Webhook Stripe: aggiorna piano utente a Pro dopo pagamento."""
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"ok":True})
    try:
        payload = request.get_data()
        data = json.loads(payload)
        event_type = data.get("type","")
        if event_type in ("checkout.session.completed","customer.subscription.created"):
            obj = data.get("data",{}).get("object",{})
            user_id = obj.get("metadata",{}).get("user_id")
            if user_id and DATABASE_URL:
                import psycopg2
                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()
                cur.execute("UPDATE utenti SET piano='pro' WHERE id=%s", (user_id,))
                conn.commit(); cur.close(); conn.close()
    except Exception:
        pass
    return jsonify({"ok":True})


@app.route("/v1/admin/init", methods=["POST"])
def admin_init():
    """Inizializza le tabelle account/quaderno. Da chiamare una volta dalla Console Railway."""
    secret = request.json.get("secret","") if request.json else ""
    if secret != os.environ.get("ADMIN_SECRET","matter-init-2026"):
        return jsonify({"errore":"non autorizzato"}), 403
    _init_account_tables()
    # crea anche la tabella esperimenti
    if DATABASE_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
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
            conn.commit(); cur.close(); conn.close()
        except Exception as e:
            return jsonify({"errore":str(e)}), 500
    return jsonify({"ok":True,"messaggio":"Tabelle create: utenti, sessioni, esperimenti"})


# ── FLASK CLI COMMANDS ────────────────────────────────────────────
import click


@app.cli.command("translate-graph")
def translate_graph():
    """GT4 - Traduce schede nodi IT->EN con Haiku. Uso: flask translate-graph"""
    if not DATABASE_URL:
        click.echo("DATABASE_URL non impostato"); return
    import psycopg2, time as _t
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT id, name, data FROM nodes ORDER BY id")
    nodi = cur.fetchall()
    click.echo("Traduzione di " + str(len(nodi)) + " nodi con Haiku 4.5...")
    tradotti = 0; saltati = 0; errori = 0
    for nid, nome, data_raw in nodi:
        d = _dati(data_raw) if data_raw else {}
        scheda = d.get("scheda","")
        if not scheda or isinstance(scheda, dict):
            saltati += 1; continue
        prompt = (
            "Traduci questa scheda tecnica dall'italiano all'inglese. "
            "Mantieni tono tecnico-professionale, numeri esatti e termini scientifici. "
            "Rispondi SOLO con la traduzione in inglese, niente altro.\n\n"
            "SCHEDA ITALIANA:\n" + scheda
        )
        traduzione = _haiku_raw(prompt, max_tokens=800)
        if not traduzione:
            errori += 1; click.echo("  ERRORE: " + nome); continue
        d["scheda"] = {"it": scheda, "en": traduzione.strip()}
        cur.execute(
            "UPDATE nodes SET data = %s::jsonb WHERE id = %s",
            (json.dumps(d, ensure_ascii=False), nid)
        )
        tradotti += 1
        if tradotti % 10 == 0:
            conn.commit()
            click.echo("  " + str(tradotti) + " tradotti...")
        _t.sleep(0.3)
    conn.commit(); cur.close(); conn.close()
    click.echo("FATTO: " + str(tradotti) + " tradotti - " + str(saltati) + " saltati - " + str(errori) + " errori")

@app.cli.command("init-db")
def init_db():
    """Inizializza tabelle account, sessioni, esperimenti e flavor network.
    Uso dalla Console Railway: flask init-db"""
    click.echo("Inizializzazione database Matter...")
    _init_account_tables()
    if DATABASE_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS flavor_abbinamenti (
                    id SERIAL PRIMARY KEY,
                    ingrediente_1 TEXT NOT NULL,
                    ingrediente_2 TEXT NOT NULL,
                    composto TEXT,
                    overlap_score NUMERIC(4,2),
                    fonte TEXT DEFAULT 'ahn_2011',
                    UNIQUE(ingrediente_1, ingrediente_2)
                )
            """)
            conn.commit(); cur.close(); conn.close()
            click.echo("OK: tabelle create (utenti, sessioni, esperimenti, flavor_abbinamenti)")
        except Exception as e:
            click.echo(f"ERRORE: {e}")
    else:
        click.echo("DATABASE_URL non impostato — skip")

@app.cli.command("import-usda")
def import_usda():
    """DS4 — Importa parametri fisici da USDA FoodData Central.
    Richiede variabile d'ambiente USDA_API_KEY su Railway.
    Uso: flask import-usda"""
    import urllib.request, json, re, time as _t

    api_key = _os.environ.get("USDA_API_KEY", "")
    if not api_key:
        click.echo("ERRORE: variabile USDA_API_KEY non impostata su Railway.")
        return

    if not DATABASE_URL:
        click.echo("ERRORE: DATABASE_URL non disponibile.")
        return

    def usda_get(url, max_retries=3):
        """Fetch con retry automatico e timeout generoso."""
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Matter/1.0"})
                resp = urllib.request.urlopen(req, timeout=30)
                return json.loads(resp.read().decode())
            except Exception as e:
                if attempt < max_retries - 1:
                    click.echo(f"    retry {attempt+1}/{max_retries-1}...")
                    _t.sleep(2 * (attempt + 1))
                else:
                    raise e

    # ── Ingredienti prioritari per Matter ────────────────────
    # Selezionati per rilevanza F&B professionale (bar, bakery, cucina, caffetteria)
    QUERY_MAP = {
        # Frutta e succhi
        "lemon juice": {"fenomeno": "fen-acidita", "domain": "bar"},
        "lime juice":  {"fenomeno": "fen-acidita", "domain": "bar"},
        "orange juice":{"fenomeno": "fen-acidita", "domain": "bar"},
        "tomato":      {"fenomeno": "fen-acidita", "domain": "cucina"},
        "apple raw":   {"fenomeno": "fen-acidita", "domain": "bakery"},
        "strawberry":  {"fenomeno": "fen-acidita", "domain": "pasticceria"},
        "raspberry":   {"fenomeno": "fen-acidita", "domain": "pasticceria"},
        "blueberry":   {"fenomeno": "fen-acidita", "domain": "pasticceria"},
        # Latticini
        "whole milk":  {"fenomeno": "fen-coagulazione", "domain": "cucina"},
        "heavy cream": {"fenomeno": "fen-struttura",    "domain": "cucina"},
        "butter unsalted": {"fenomeno": "fen-cristallizzazione", "domain": "bakery"},
        "yogurt plain":{"fenomeno": "fen-fermentazione","domain": "cucina"},
        # Uova
        "egg white":   {"fenomeno": "fen-coagulazione", "domain": "cucina"},
        "egg yolk":    {"fenomeno": "fen-coagulazione", "domain": "cucina"},
        # Cereali
        "wheat flour": {"fenomeno": "fen-struttura",    "domain": "bakery"},
        "rye flour":   {"fenomeno": "fen-struttura",    "domain": "bakery"},
        # Carne e pesce
        "beef raw":    {"fenomeno": "fen-calore",       "domain": "cucina"},
        "chicken breast": {"fenomeno": "fen-calore",    "domain": "cucina"},
        "salmon raw":  {"fenomeno": "fen-calore",       "domain": "cucina"},
        # Zuccheri
        "sugar granulated": {"fenomeno": "fen-concentrazione", "domain": "pasticceria"},
        "honey":       {"fenomeno": "fen-concentrazione","domain": "pasticceria"},
        # Cioccolato e caffè
        "dark chocolate": {"fenomeno": "fen-cristallizzazione", "domain": "pasticceria"},
        "coffee brewed":  {"fenomeno": "fen-estrazione",        "domain": "caffetteria"},
        # Aceto e fermentati
        "vinegar":     {"fenomeno": "fen-acidita",      "domain": "cucina"},
        # Funghi
        "mushroom":    {"fenomeno": "fen-maillard",     "domain": "cucina"},
    }

    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    tradotti = 0
    saltati = 0
    errori = 0

    for query, meta in QUERY_MAP.items():
        try:
            # Cerca il cibo su USDA FDC
            url = (f"https://api.nal.usda.gov/fdc/v1/foods/search"
                   f"?query={urllib.request.quote(query)}"
                   f"&dataType=Foundation,SR%20Legacy"
                   f"&pageSize=1&api_key={api_key}")
            data = usda_get(url)

            foods = data.get("foods", [])
            if not foods:
                click.echo(f"  SALTATO (non trovato): {query}")
                saltati += 1
                continue

            food = foods[0]
            fdc_id = food.get("fdcId")
            nome_usda = food.get("description", query)

            # Estrai nutrienti rilevanti
            nutrients = {n["nutrientName"]: n for n in food.get("foodNutrients", [])}

            # Recupera dettaglio
            detail_url = (f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
                          f"?api_key={api_key}")
            detail = usda_get(detail_url)

            # Parametri fisici disponibili in FDC
            food_data = {
                "fdc_id": fdc_id,
                "nome_usda": nome_usda,
                "fonte": "USDA FoodData Central CC0",
                "fenomeno": meta["fenomeno"],
            }

            # Acqua (proxy per Aw)
            water = nutrients.get("Water")
            if water:
                water_pct = float(water.get("value", 0))
                if water_pct > 0:
                    # Aw approssimata da % acqua (semplificazione)
                    food_data["water_pct"] = water_pct
                    food_data["aw_nota"] = f"contenuto acqua: {water_pct}% (Aw stimata dalla composizione)"

            # Energia, proteine, grassi per contesto
            energia = nutrients.get("Energy")
            if energia:
                food_data["energia_kcal"] = float(energia.get("value", 0))

            proteine = nutrients.get("Protein")
            if proteine:
                food_data["proteine_pct"] = float(proteine.get("value", 0))

            # Nodo ID nel grafo
            node_id = "usda_" + re.sub(r"[^a-z0-9]", "_", query.lower().strip())

            # Upsert nodo
            cur.execute("""
                INSERT INTO nodes (id, type, name, domain, data)
                VALUES (%s, 'Prodotto', %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data
            """, (node_id, nome_usda, meta["domain"], json.dumps(food_data, ensure_ascii=False)))

            # Arco verso fenomeno
            cur.execute("""
                INSERT INTO edges (from_id, to_id, relation, data)
                VALUES (%s, %s, 'governato_da', '{}')
                ON CONFLICT DO NOTHING
            """, (node_id, meta["fenomeno"]))

            tradotti += 1
            click.echo(f"  OK: {query} → {nome_usda} (fdc_id:{fdc_id})")

            _t.sleep(0.3)  # rispetta rate limit USDA (1000/h)

        except Exception as e:
            click.echo(f"  ERRORE {query}: {e}")
            errori += 1
            continue

    conn.commit()
    cur.close()
    conn.close()
    click.echo(f"\nFATTO: {tradotti} importati · {saltati} saltati · {errori} errori")


@app.cli.command("load-flavor")
def load_flavor():
    """Carica il flavor network nel database. Uso: flask load-flavor"""
    click.echo("Caricamento flavor network...")
    try:
        import import_flavor_network
        import_flavor_network.carica_flavor_network()
        click.echo("OK: flavor network caricato")
    except Exception as e:
        click.echo(f"ERRORE: {e}")


# ── RATE LIMITING (IN4) ───────────────────────────────────────────
import time as _time
_rate_store = {}  # {ip: [timestamp, ...]}
_RATE_LIMIT = 30   # max 30 richieste
_RATE_WINDOW = 60  # per minuto

def _check_rate_limit(ip):
    """Rate limit per IP: 30 richieste/minuto su endpoint AI costosi."""
    now = _time.time()
    if ip not in _rate_store:
        _rate_store[ip] = []
    # rimuovi richieste fuori dalla finestra
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        return False
    _rate_store[ip].append(now)
    return True


@app.route("/v1/feedback", methods=["POST"])
def feedback():
    """AC5 — Pollice su/giù sulla risposta di Sonnet.
    Alimenta log_domande con campo feedback per affinare il prompt."""
    body = request.json or {}
    log_id = body.get("log_id")
    voto = body.get("voto")  # 1 = positivo, -1 = negativo
    nota = body.get("nota", "")
    if not log_id or voto not in (1, -1):
        return jsonify({"errore": "log_id e voto (1/-1) obbligatori"}), 400
    if not DATABASE_URL:
        return jsonify({"ok": True})
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # aggiunge colonna feedback se non esiste
        cur.execute("""
            ALTER TABLE log_domande
            ADD COLUMN IF NOT EXISTS feedback INTEGER,
            ADD COLUMN IF NOT EXISTS feedback_nota TEXT
        """)
        cur.execute(
            "UPDATE log_domande SET feedback=%s, feedback_nota=%s WHERE id=%s",
            (voto, nota[:200], log_id)
        )
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@app.route("/v1/admin/stats")
def admin_stats():
    """GT10 — Admin panel: statistiche base del prodotto."""
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET","matter-init-2026"):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        stats = {}
        # utenti
        cur.execute("SELECT COUNT(*) FROM utenti WHERE attivo=TRUE")
        stats["utenti_attivi"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM utenti WHERE piano='pro'")
        stats["utenti_pro"] = cur.fetchone()[0]
        # domande
        cur.execute("SELECT COUNT(*) FROM log_domande")
        stats["domande_totali"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM log_domande WHERE esito='ok'")
        stats["risposte_ok"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM log_domande WHERE esito='nessun_nodo'")
        stats["fallback"] = cur.fetchone()[0]
        # feedback
        try:
            cur.execute("SELECT COUNT(*) FROM log_domande WHERE feedback=1")
            stats["feedback_positivi"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM log_domande WHERE feedback=-1")
            stats["feedback_negativi"] = cur.fetchone()[0]
        except Exception:
            stats["feedback_positivi"] = 0
            stats["feedback_negativi"] = 0
        # grafo
        cur.execute("SELECT COUNT(*) FROM nodes")
        stats["nodi_grafo"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM edges")
        stats["archi_grafo"] = cur.fetchone()[0]
        # esperimenti
        try:
            cur.execute("SELECT COUNT(*) FROM esperimenti")
            stats["esperimenti"] = cur.fetchone()[0]
        except Exception:
            stats["esperimenti"] = 0
        # domande ultime 24h
        cur.execute("SELECT COUNT(*) FROM log_domande WHERE ts > NOW() - INTERVAL '24 hours'")
        stats["domande_24h"] = cur.fetchone()[0]
        # top fenomeni cercati
        cur.execute("""
            SELECT fenomeni_trovati, COUNT(*) as n
            FROM log_domande
            WHERE fenomeni_trovati IS NOT NULL AND ts > NOW() - INTERVAL '7 days'
            GROUP BY fenomeni_trovati ORDER BY n DESC LIMIT 5
        """)
        stats["top_fenomeni_7d"] = [{"fenomeni":r[0],"count":r[1]} for r in cur.fetchall()]
        cur.close(); conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@app.route("/termini")
def termini():
    """LE3 — Termini di servizio."""
    return """<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Termini di Servizio — Matter</title>
<style>body{font-family:Georgia,serif;max-width:700px;margin:40px auto;padding:0 20px;line-height:1.7;color:#1A1A18}
h1{font-size:24px}h2{font-size:18px;margin-top:32px}p,li{font-size:15px}</style>
</head><body>
<h1>Termini di Servizio — Matter</h1>
<p><strong>Ultimo aggiornamento:</strong> luglio 2026</p>
<h2>Cosa è Matter</h2>
<p>Matter è uno strumento informativo di supporto per professionisti F&B. Le risposte sono generate da modelli AI (Anthropic/Mistral) sulla base di un grafo di conoscenza scientifica verificata.</p>
<h2>Limitazioni di responsabilità</h2>
<p>Le informazioni fornite da Matter hanno scopo esclusivamente informativo e didattico. Non sostituiscono la competenza professionale, la consulenza di esperti alimentari o le normative vigenti in materia di sicurezza alimentare (HACCP). L'utente è l'unico responsabile delle decisioni operative prese sulla base delle informazioni ricevute.</p>
<h2>Flavor network</h2>
<p>Gli abbinamenti suggeriti dal flavor network sono ipotesi basate su composti volatili condivisi (dataset scientifico Ahn 2011). Non costituiscono garanzie nutrizionali, mediche o di sicurezza alimentare.</p>
<h2>Account e abbonamento</h2>
<p>Il piano Free è gratuito e include funzionalità limitate. Il piano Pro è a pagamento (€11,99/mese) e include l'accesso completo al grafo, alla chat AI e al flavor network. L'abbonamento è rinnovabile mensilmente e cancellabile in qualsiasi momento.</p>
<h2>Proprietà intellettuale</h2>
<p>Il grafo di conoscenza, il codice e il design di Matter sono proprietà del titolare. I dati scientifici provengono da fonti pubbliche citate (dataset Ahn CC BY, PubChem NCBI).</p>
<p><a href="/">← Torna a Matter</a></p>
</body></html>""", 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route("/static/sw.js")
def sw():
    """IN5 — Serve il service worker dalla cartella static."""
    import pathlib
    sw_path = pathlib.Path(__file__).parent / "static" / "sw.js"
    if sw_path.exists():
        return sw_path.read_text(), 200, {
            'Content-Type': 'application/javascript',
            'Service-Worker-Allowed': '/'
        }
    return '', 404

if __name__ == "__main__":
    app.run(debug=True, port=5001)
