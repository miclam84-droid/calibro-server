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


def _pulisci_traduzione(t):
    """Toglie intestazioni spurie che Haiku a volte antepone alla traduzione
    (es. 'ENGLISH TECHNICAL SHEET:'), indotte dal prompt: facevano sembrare la
    scheda EN un titolo. Difesa in lettura, così pulisce anche il gia' salvato."""
    if not t:
        return t
    import re
    t = t.strip()
    t = re.sub(r'^(ENGLISH\s+)?TECHNICAL\s+SHEET\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(ENGLISH\s+)?SHEET\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^SCHEDA(\s+(TECNICA|ITALIANA))?\s*:?\s*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(Translation|Traduzione)\s*:?\s*', '', t, flags=re.IGNORECASE)
    return t.strip()


def _scheda_lang(data_dict, lang="it"):
    """GT4 — Legge il campo scheda nel formato multilingua.
    Supporta sia il formato legacy (stringa) sia il nuovo formato {it:"...", en:"..."}.
    Quando tutti i nodi saranno migrati al formato dizionario, il fallback legacy si rimuove."""
    scheda = data_dict.get("scheda", "")
    if isinstance(scheda, dict):
        return _pulisci_traduzione(scheda.get(lang) or scheda.get("it") or "")
    return scheda or ""


def _numero_bersaglio(data_dict):
    """Legge il numero-bersaglio di un nodo Fenomeno in modo canonico.
    Il seed usa la chiave 'numero_bersaglio'; il fallback 'target' copre
    eventuali nodi legacy. Fonte unica di verità per home, disciplina e lezione,
    così la chiave non torna a divergere tra i lettori."""
    if not data_dict:
        return ""
    return data_dict.get("numero_bersaglio") or data_dict.get("target") or ""


def _intro(testo, n=200):
    """Anteprima breve che NON taglia a metà parola. Tronca all'ultimo spazio
    entro n caratteri e aggiunge l'ellissi, così non compaiono monconi come
    'fa da orologi'. Se il testo è già corto, resta intero."""
    testo = (testo or "").strip()
    if len(testo) <= n:
        return testo
    taglio = testo[:n]
    sp = taglio.rfind(" ")
    if sp > 0:
        taglio = taglio[:sp]
    return taglio.rstrip(" ,.;:—-") + "…"

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
             "target": _numero_bersaglio(_dati(r["data"]))} for r in rows]

def costruisci_prompt(domanda, contesto, lang="it"):
    righe = []
    for f in contesto["fenomeni"]:
        righe.append("")
        righe.append(f"### Fenomeno: {f['name']} ({f['domain']})")
        sch = _scheda_lang(f["data"], lang)
        if sch:
            righe.append(sch)
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
    """KDF forte (pbkdf2/scrypt via werkzeug). Sostituisce lo SHA-256 veloce,
    che era forzabile in caso di fuga del DB."""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password)

def _e_hash_legacy(stored):
    """True se lo hash è nel vecchio formato debole 'salt:hash' (SHA-256),
    da rigenerare col KDF forte al primo login."""
    return bool(stored) and not str(stored).startswith(("pbkdf2:", "scrypt:", "argon2:"))

def _verifica_pw(password, stored):
    """True se la password combacia. Gestisce sia i nuovi hash werkzeug sia
    i vecchi 'salt:hash' SHA-256 (che vanno migrati al primo login)."""
    if not stored:
        return False
    if _e_hash_legacy(stored):
        import hashlib
        try:
            salt, h = str(stored).split(":")
            return hashlib.sha256((salt + password).encode()).hexdigest() == h
        except Exception:
            return False
    from werkzeug.security import check_password_hash
    try:
        return check_password_hash(stored, password)
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
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":"Troppi tentativi. Aspetta un minuto e riprova."}), 429
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
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":"Troppi tentativi. Aspetta un minuto e riprova."}), 429
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
        user_id, stored_hash, piano = row
        # migrazione trasparente: se lo hash è ancora il vecchio SHA-256, al
        # primo login corretto lo rigeneriamo col KDF forte. Zero attrito utente.
        if _e_hash_legacy(stored_hash):
            try:
                cur.execute("UPDATE utenti SET password_h=%s WHERE id=%s",
                            (_hash_pw(password), user_id))
            except Exception:
                pass
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


# ── RESET PASSWORD (AC6) ──────────────────────────────────────────

@app.route("/v1/auth/reset-richiesta", methods=["POST"])
def reset_richiesta():
    """Passo 1: genera token e manda link via Resend.
    Risponde sempre uguale (non rivela se l'email esiste)."""
    body = request.json or {}
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":"Troppi tentativi. Aspetta un minuto."}), 429
    email = (body.get("email","")).strip().lower()
    if not email or not DATABASE_URL:
        return jsonify({"ok":True,"messaggio":"Se l'email è registrata riceverai un link."})
    try:
        import psycopg2, secrets as _sec
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS reset_token (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            ts    TIMESTAMPTZ DEFAULT NOW(),
            scade TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour',
            usato BOOLEAN DEFAULT FALSE)""")
        cur.execute("SELECT id FROM utenti WHERE email=%s AND attivo=TRUE", (email,))
        if cur.fetchone():
            tok = _sec.token_urlsafe(32)
            cur.execute("INSERT INTO reset_token (token,email) VALUES (%s,%s)", (tok, email))
            conn.commit()
            base = os.environ.get("MATTER_BASE_URL","https://web-production-79457.up.railway.app")
            link = f"{base}/app?reset={tok}"
            _invia_email_resend(
                to=email,
                subject="Reimposta la tua password — Matter",
                body_html=(f"<p>Hai richiesto il reset della password di Matter.</p>"
                           f"<p><a href='{link}'>Clicca qui per reimpostare la password</a></p>"
                           f"<p>Il link scade tra 1 ora.</p>"),
                body_text=f"Reset password Matter:\n{link}\n\nIl link scade tra 1 ora."
            )
        cur.close(); conn.close()
    except Exception:
        pass
    return jsonify({"ok":True,"messaggio":"Se l'email è registrata riceverai un link."})


@app.route("/v1/auth/reset-conferma", methods=["POST"])
def reset_conferma():
    """Passo 2: token dal link + nuova password."""
    body = request.json or {}
    tok = (body.get("token","")).strip()
    nuova_pw = body.get("password","")
    if not tok or not nuova_pw:
        return jsonify({"errore":"token e password obbligatori"}), 400
    if len(nuova_pw) < 8:
        return jsonify({"errore":"password minimo 8 caratteri"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT email FROM reset_token WHERE token=%s AND scade>NOW() AND usato=FALSE", (tok,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({"errore":"Link non valido o scaduto. Richiedine uno nuovo."}), 400
        email = row[0]
        cur.execute("UPDATE utenti SET password_h=%s WHERE email=%s", (_hash_pw(nuova_pw), email))
        cur.execute("UPDATE reset_token SET usato=TRUE WHERE token=%s", (tok,))
        cur.execute("DELETE FROM sessioni WHERE user_id=(SELECT id FROM utenti WHERE email=%s)", (email,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ok":True,"messaggio":"Password aggiornata. Puoi fare login con la nuova password."})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


# ── CANCELLAZIONE ACCOUNT GDPR (AC7) ─────────────────────────────

@app.route("/v1/auth/cancella-account", methods=["DELETE"])
def cancella_account():
    """Self-service GDPR: anonimizza email e hash, invalida sessioni.
    Richiede token attivo + conferma password."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    body = request.json or {}
    password = body.get("password","")
    if not password:
        return jsonify({"errore":"inserisci la password per confermare"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2, secrets as _sec
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT password_h FROM utenti WHERE id=%s AND attivo=TRUE", (user_id,))
        row = cur.fetchone()
        if not row or not _verifica_pw(password, row[0]):
            cur.close(); conn.close()
            return jsonify({"errore":"password non corretta"}), 401
        anon = f"deleted_{_sec.token_hex(8)}@matter.deleted"
        cur.execute("UPDATE utenti SET email=%s, password_h='DELETED', attivo=FALSE WHERE id=%s",
                    (anon, user_id))
        cur.execute("DELETE FROM sessioni WHERE user_id=%s", (user_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"ok":True,"messaggio":"Account cancellato. I tuoi dati sono stati rimossi."})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


# ---- endpoint -----------------------------------------------
# ── FLAVOR NETWORK (FL3-FL4) ─────────────────────────────────────

@app.route("/v1/abbina/<ingrediente>")
def abbina(ingrediente):
    """FL3 — Abbinamenti aromatici dal grafo Ahn 2011 (edges abbinamento_aromatico).
    Cerca per nome italiano (con mappa di traduzione) o inglese direttamente.
    Sempre marcato come ipotesi eurisitca, mai come legge."""
    # mappa italiano → nome Ahn (inglese con underscore)
    ALIAS_IT = {
        "pomodoro":"tomato","limone":"lemon","aglio":"garlic","cipolla":"onion",
        "burro":"butter","panna":"cream","latte":"milk","uova":"egg","uovo":"egg",
        "basilico":"basil","prezzemolo":"parsley","rosmarino":"rosemary",
        "timo":"thyme","menta":"mint","cannella":"cinnamon","vaniglia":"vanilla",
        "cioccolato":"chocolate","caffe":"coffee","caffè":"coffee",
        "fragola":"strawberry","lampone":"raspberry","mela":"apple",
        "pera":"pear","banana":"banana","arancia":"orange","limetta":"lime","lime":"lime",
        "zenzero":"ginger","pepe":"black_pepper","sale":"salt",
        "aceto":"vinegar","vino":"wine","birra":"beer","rum":"rum",
        "whisky":"whiskey","gin":"gin","vodka":"vodka",
        "salmone":"salmon","tonno":"tuna","gambero":"shrimp",
        "manzo":"beef","pollo":"chicken","maiale":"pork","agnello":"lamb",
        "formaggio":"cheese","parmigiano":"parmesan","mozzarella":"mozzarella",
        "olio":"olive_oil","olio d oliva":"olive_oil","sesamo":"sesame",
        "mandorla":"almond","nocciola":"hazelnut","noci":"walnut","noce":"walnut",
        "caffè espresso":"espresso","espresso":"espresso",
        "ananas":"pineapple","mango":"mango","cocco":"coconut",
        "zucca":"pumpkin","carota":"carrot","sedano":"celery",
        "funghi":"mushroom","porcini":"porcini_mushroom",
        "tè":"tea","te":"tea","miele":"honey","zucchero":"sugar",
        "peperoncino":"chili","peperone":"bell_pepper","melanzana":"eggplant",
    }
    # normalizza l'input
    ing_norm = ingrediente.lower().replace("-","_").replace(" ","_")
    ing_it = ingrediente.lower().replace("_"," ")
    # cerca alias italiano
    ahn_name = ALIAS_IT.get(ing_it) or ALIAS_IT.get(ing_norm.replace("_"," "))
    # se non c'è alias, prova diretto
    search_terms = []
    if ahn_name:
        search_terms.append(f"ahn_{ahn_name}")
        search_terms.append(f"ahn_{ahn_name.replace(' ','_')}")
    search_terms.append(f"ahn_{ing_norm}")
    search_terms.append(f"ahn_{ing_norm.replace('_',' ')}")

    if not DATABASE_URL:
        return jsonify({"ingrediente":ingrediente,"abbinamenti":[],
                        "nota":"flavor network non disponibile"})
    try:
        import psycopg2, json as _j
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        rows = []
        for term in search_terms:
            cur.execute("""
                SELECT e.to_id, n.name,
                       (e.data->>'overlap')::numeric as overlap
                FROM edges e
                JOIN nodes n ON n.id = e.to_id
                WHERE e.relation = 'abbinamento_aromatico'
                AND (lower(e.from_id) = lower(%s)
                     OR lower(e.from_id) LIKE lower(%s))
                ORDER BY overlap DESC NULLS LAST LIMIT 8
            """, (term, f"%{term}%"))
            rows = cur.fetchall()
            if rows: break
        # fallback: cerca per nome parziale
        if not rows:
            cur.execute("""
                SELECT e.to_id, n.name,
                       (e.data->>'overlap')::numeric as overlap
                FROM edges e
                JOIN nodes n ON n.id = e.to_id
                WHERE e.relation = 'abbinamento_aromatico'
                AND lower(e.from_id) LIKE lower(%s)
                ORDER BY overlap DESC NULLS LAST LIMIT 8
            """, (f"%{ing_norm.replace('_','%')}%",))
            rows = cur.fetchall()
        cur.close(); conn.close()
        abbinamenti = []
        for r in rows:
            nome_pulito = r[1].replace("_"," ").title()
            overlap = float(r[2]) if r[2] else 0
            abbinamenti.append({
                "ingrediente": nome_pulito,
                "composto": f"{overlap:.0f} composti in comune",
                "overlap": overlap,
                "perche": f"condividono {overlap:.0f} composti aromatici"
            })
        return jsonify({
            "ingrediente": ingrediente,
            "abbinamenti": abbinamenti,
            "nota": "Ipotesi di abbinamento per composti volatili condivisi — non è una garanzia nutrizionale",
            "fonte": "Dataset Ahn 2011 (CC BY)"
        })
    except Exception as e:
        return jsonify({"ingrediente":ingrediente,"abbinamenti":[],
                        "nota":f"Errore: {str(e)}"}), 500

@app.route("/v1/contrasto/<ingrediente>")
def contrasto(ingrediente):
    """FL5 — Abbinamento per contrasto fisico-percettivo.
    Logica: acido taglia il grasso · dolce smorza l'amaro · sale sopprime l'amaro
            grasso porta e ammorbidisce l'acido.
    Usa i dati di grassi_pct, zuccheri_pct, sodio_mg100g, ph_min dal grafo.
    Sempre marcato come euristico — è fisica percettiva, non legge."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "contrasti": [],
                        "nota": "database non disponibile"})
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # trova il nodo dell'ingrediente cercato — preferisce nodi con dati contrasto
        cur.execute("""
            SELECT id, name, data FROM nodes
            WHERE type='Prodotto'
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            AND (data->>'profilo_contrasto') IS NOT NULL
            ORDER BY length(name) ASC
            LIMIT 1
        """, (f"%{ingrediente}%", f"%{ingrediente.replace(' ','_')}%"))
        row = cur.fetchone()
        if not row:
            # fallback: cerca anche senza dati contrasto
            cur.execute("""
                SELECT id, name, data FROM nodes
                WHERE type='Prodotto'
                AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                ORDER BY length(name) ASC
                LIMIT 1
            """, (f"%{ingrediente}%", f"%{ingrediente.replace(' ','_')}%"))
            row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({"ingrediente": ingrediente, "contrasti": [],
                            "nota": "Ingrediente non trovato nel grafo con dati di contrasto."})

        node_id, node_name, data_raw = row
        import json as _json
        d = data_raw if isinstance(data_raw, dict) else _json.loads(data_raw)

        grassi = float(d.get("grassi_pct", 0) or 0)
        zuccheri = float(d.get("zuccheri_pct", 0) or 0)
        ph = float(d.get("ph_min", 7) or 7)
        amaro = float(d.get("amaro_index", 0) or 0)
        sodio = float(d.get("sodio_mg100g", 0) or 0)
        profilo = d.get("profilo_contrasto", "")

        # determina il tipo di contrasto necessario
        regole = []
        if ph < 4.5:
            regole.append(("acido", "taglia_grasso",
                           "L'acido taglia il grasso: il pH basso emulsiona e pulisce la bocca"))
        if grassi > 10:
            regole.append(("grasso", "richiede_acido",
                           "Il grasso porta e ammorbidisce: cerca un acido per bilanciare"))
        if amaro >= 3:
            regole.append(("amaro", "smorzato_da_dolce",
                           "Il dolce smorza l'amaro: zuccheri e grassi riducono la percezione amara"))
        if amaro >= 2:
            regole.append(("amaro", "smorzato_da_sale",
                           "Il sale sopprime l'amaro: piccole quantità di sodio riducono l'amaro percepito"))
        if zuccheri > 15:
            regole.append(("dolce", "bilanciato_da_acido",
                           "Il dolce vuole acido: senza contrasto acido il dolce stanca e satura"))
        if sodio > 200:
            regole.append(("salato", "amplificato_da_acido",
                           "Il salato si amplifica con l'acido: together esaltano entrambi i sapori"))

        if not regole:
            cur.close(); conn.close()
            return jsonify({
                "ingrediente": node_name, "contrasti": [],
                "nota": "Profilo neutro — questo ingrediente non ha un contrasto dominante evidente.",
                "tipo": "contrasto"
            })

        # cerca ingredienti con il profilo opposto
        contrasti = []
        visti = set()
        for profilo_cercato, meccanismo, spiegazione in regole:
            if profilo_cercato == "acido":
                # cerca grassi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'grassi_pct')::numeric > 8
                    AND id != %s
                    ORDER BY (data->>'grassi_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "grasso":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'ph_min')::numeric < 4.5
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_dolce":
                # cerca dolci
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'zuccheri_pct')::numeric > 10
                    AND id != %s
                    ORDER BY (data->>'zuccheri_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_sale":
                # cerca salati
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'sodio_mg100g')::numeric > 100
                    AND id != %s
                    ORDER BY (data->>'sodio_mg100g')::numeric DESC LIMIT 2
                """, (node_id,))
            elif profilo_cercato == "dolce":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'ph_min')::numeric < 4.0
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "salato":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Prodotto'
                    AND (data->>'ph_min')::numeric < 4.5
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 2
                """, (node_id,))
            else:
                continue

            for r in cur.fetchall():
                rid, rname, rdata = r
                if rid not in visti:
                    visti.add(rid)
                    contrasti.append({
                        "ingrediente": rname,
                        "meccanismo": meccanismo,
                        "perche": spiegazione
                    })

        cur.close(); conn.close()
        return jsonify({
            "ingrediente": node_name,
            "contrasti": contrasti[:6],
            "nota": "Abbinamento per contrasto fisico-percettivo — euristico, non legge",
            "tipo": "contrasto"
        })
    except Exception as e:
        return jsonify({"ingrediente": ingrediente, "contrasti": [],
                        "nota": f"Errore: {str(e)}"}), 500


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
    # mini-history: ultimi scambi passati dal frontend (zero DB, solo memoria sessione)
    history = (request.json or {}).get("history", [])
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
    # se ci sono scambi precedenti, li prependo al prompt per dare continuità
    if history:
        hist_txt = "\n".join(
            f"Domanda precedente: {h['q']}\nRisposta precedente (sintesi): {h['r']}"
            for h in history[-3:] if h.get('q') and h.get('r')
        )
        if hist_txt:
            prompt = f"Contesto della conversazione in corso:\n{hist_txt}\n\n---\n{prompt}"
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
                     "target": _numero_bersaglio(_dati(f["data"]))} for f in tutti]
    else:
        fenomeni = []
        for fid in sorted(fen_ids):
            f = db.execute("SELECT id, name, data FROM nodes WHERE id=?", (fid,)).fetchone()
            if f:
                fenomeni.append({"id": f["id"], "nome": f["name"],
                                  "target": _numero_bersaglio(_dati(f["data"]))})
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


def _genera_quiz(nome, target, scheda, lang="it"):
    """Genera un quiz con Haiku (chiamata lenta, ~5s). Ritorna il quiz base
    con la risposta corretta all'indice 0 — lo shuffle avviene alla consegna.
    Usato da /quiz con cache: Haiku si paga una volta sola per nodo+lingua."""
    if not scheda:
        return None
    if lang == "en":
        quiz_prompt = f"""Create a quiz about this phenomenon for an F&B professional.
Phenomenon: {nome}
Target number: {target}
Content: {scheda[:400]}

Reply ONLY with valid JSON, no text before or after:
{{"domanda":"...","opzioni":["correct option","wrong option","wrong option"],"corretta":0,"spiegazione":"explanation with the exact mathematical calculation in 2 lines"}}

The correct answer must always be the first option (index 0).
The explanation must include the exact number."""
    else:
        quiz_prompt = f"""Crea un quiz su questo fenomeno per un professionista F&B.
Fenomeno: {nome}
Numero bersaglio: {target}
Contenuto: {scheda[:400]}

Rispondi SOLO con JSON valido, nessun testo prima o dopo:
{{"domanda":"...","opzioni":["opzione giusta","opzione sbagliata","opzione sbagliata"],"corretta":0,"spiegazione":"spiegazione con il calcolo matematico in 2 righe"}}

La risposta corretta deve essere sempre la prima opzione (indice 0).
La spiegazione deve includere il numero esatto."""
    try:
        raw = _haiku_raw(quiz_prompt)
        if raw:
            import re
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                quiz_data = json.loads(m.group())
                opzioni = quiz_data.get("opzioni", [])
                if not opzioni:
                    return None
                return {
                    "domanda": quiz_data.get("domanda", ""),
                    "opzioni": opzioni,        # corretta = indice 0
                    "corretta": 0,
                    "spiegazione": quiz_data.get("spiegazione", "")
                }
    except Exception:
        return None
    return None


@app.route("/quiz/<node_id>")
def quiz_nodo(node_id):
    """Quiz di un nodo, lazy + cache. La lezione non lo genera piu (era ~5s).
    Prima volta: Haiku + salva in quiz_cache. Poi: istantaneo dalla cache.
    quiz_cache vive in Postgres, non viene truncata dal migrate."""
    lang = request.args.get("lang", "it")
    db = carica_grafo()
    db.execute("""CREATE TABLE IF NOT EXISTS quiz_cache (
        node_id TEXT, lang TEXT, quiz_json TEXT,
        PRIMARY KEY (node_id, lang))""")
    base = None
    row = db.execute("SELECT quiz_json FROM quiz_cache WHERE node_id=? AND lang=?",
                     (node_id, lang)).fetchone()
    if row:
        try:
            base = json.loads(row["quiz_json"])
        except Exception:
            base = None
    if base is None:
        nodo = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not nodo:
            return jsonify({"quiz": None})
        nd = _dati(nodo["data"])
        base = _genera_quiz(nodo["name"], _numero_bersaglio(nd),
                            _scheda_lang(nd, lang), lang)
        if base:
            db.execute("""INSERT INTO quiz_cache (node_id, lang, quiz_json)
                          VALUES (?,?,?) ON CONFLICT (node_id, lang) DO NOTHING""",
                       (node_id, lang, json.dumps(base)))
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
    if (not os.environ.get("ADMIN_SECRET")) or secret != os.environ.get("ADMIN_SECRET"):
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
            "Translate the following Italian technical text into English. "
            "Keep the technical-professional tone, exact numbers and scientific terms. "
            "Output ONLY the translated text, with no title, no header, no label, "
            "no quotes — just the translation.\n\n" + scheda
        )
        traduzione = _haiku_raw(prompt, max_tokens=800)
        if not traduzione:
            errori += 1; click.echo("  ERRORE: " + nome); continue
        d["scheda"] = {"it": scheda, "en": _pulisci_traduzione(traduzione)}
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

    # Ingredienti prioritari per Matter
    # Dove possibile usiamo fdc_id diretto (più affidabile di query testuale)
    # fdc_id verificati da USDA FoodData Central Foundation Foods / SR Legacy
    QUERY_MAP = {
        # Frutta e succhi — query ok, risultati corretti
        "lemon juice raw": {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 167747},
        "lime juice raw":  {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 168195},
        "orange juice":    {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 169098},
        "tomatoes red raw":{"fenomeno": "fen-acidita",  "domain": "cucina",    "fdc_id": 170457},
        "apples raw":      {"fenomeno": "fen-acidita",  "domain": "bakery",    "fdc_id": 171688},
        "strawberries raw":{"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 167762},
        "raspberries raw": {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 2346410},
        "blueberries raw": {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 2346411},
        # Latticini — fdc_id corretti (erano sbagliati)
        "milk whole 3.25%":{"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 171265},
        "cream heavy whipping":{"fenomeno":"fen-struttura","domain":"cucina",  "fdc_id": 2346386},
        "butter unsalted": {"fenomeno": "fen-cristallizzazione","domain":"bakery","fdc_id": 789828},
        "yogurt plain whole milk":{"fenomeno":"fen-fermentazione","domain":"cucina","fdc_id": 170886},
        # Uova — egg white aveva 404, usiamo fdc_id diretto
        "egg white raw":   {"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 172183},
        "egg yolk raw":    {"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 172185},
        # Cereali
        "wheat flour all-purpose":{"fenomeno":"fen-struttura","domain":"bakery","fdc_id": 168944},
        "rye flour":       {"fenomeno": "fen-struttura",  "domain": "bakery",  "fdc_id": 2512375},
        # Carne — fdc_id corretti (erano corned beef e lunchmeat)
        "beef ground 80% lean raw":{"fenomeno":"fen-calore","domain":"cucina", "fdc_id": 174036},
        "chicken breast raw":{"fenomeno":"fen-calore",    "domain": "cucina",  "fdc_id": 171477},
        "salmon atlantic raw":{"fenomeno":"fen-calore",   "domain": "cucina",  "fdc_id": 175167},
        # Zuccheri
        "sugars granulated":{"fenomeno": "fen-concentrazione","domain":"pasticceria","fdc_id": 169655},
        "honey":           {"fenomeno": "fen-concentrazione","domain":"pasticceria", "fdc_id": 169640},
        # Cioccolato e caffè — fdc_id corretti
        "chocolate dark 70-85%":{"fenomeno":"fen-cristallizzazione","domain":"pasticceria","fdc_id": 170272},
        "coffee brewed espresso":{"fenomeno":"fen-estrazione","domain":"caffetteria","fdc_id": 171890},
        # Aceto e funghi
        "vinegar balsamic":{"fenomeno": "fen-acidita",   "domain": "cucina",   "fdc_id": 172241},
        "mushrooms white raw":{"fenomeno":"fen-maillard", "domain": "cucina",  "fdc_id": 169251},
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
            fdc_id = meta.get("fdc_id")

            if fdc_id:
                # fdc_id diretto — struttura JSON diversa dalla ricerca
                detail_url = (f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
                              f"?api_key={api_key}")
                detail = usda_get(detail_url)
                nome_usda = detail.get("description", query)
                # nel dettaglio diretto: n["nutrient"]["name"] e n["amount"]
                nutrients = {}
                for n in detail.get("foodNutrients", []):
                    nutrient_obj = n.get("nutrient", {})
                    name = nutrient_obj.get("name")
                    amount = n.get("amount")
                    if name and amount is not None:
                        nutrients[name] = {"value": amount,
                                           "unitName": nutrient_obj.get("unitName","")}
            else:
                # Ricerca testuale (fallback)
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
                # nella ricerca: n["nutrientName"] e n["value"]
                nutrients = {n["nutrientName"]: {"value": n.get("value"),
                                                  "unitName": n.get("unitName","")}
                             for n in food.get("foodNutrients", [])
                             if n.get("nutrientName")}
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


@app.cli.command("import-pubchem")
def import_pubchem():
    """DS7 — Importa composti aromatici da PubChem NIH (pubblico dominio, no key).
    Per ogni ingrediente prioritario cerca i composti volatili rilevanti
    e crea nodi Composto puliti (senza dipendenza da Fenaroli/Ahn).
    Uso: flask import-pubchem"""
    import urllib.request, json, re, time as _t

    if not DATABASE_URL:
        click.echo("ERRORE: DATABASE_URL non disponibile.")
        return

    # Composti aromatici chiave per F&B — PubChem CID verificati
    # Fonte: PubChem NIH, pubblico dominio
    # Solo nomi Ahn verificati come presenti nel grafo
    COMPOSTI = {
        "limonene":        {"cid": 440917, "aroma": "agrumato, fresco",           "ingr": ["lemon","lime","orange_peel"]},
        "linalool":        {"cid": 6549,   "aroma": "floreale, lavanda",           "ingr": ["lemon","coriander"]},
        "citral":          {"cid": 638011, "aroma": "limone intenso",              "ingr": ["lemon","lime"]},
        "geraniol":        {"cid": 637566, "aroma": "rosa, floreale",              "ingr": ["lemon"]},
        "eugenol":         {"cid": 3314,   "aroma": "chiodi di garofano, speziato","ingr": ["clove","cinnamon","basil"]},
        "carvone":         {"cid": 16724,  "aroma": "menta, cumino",               "ingr": ["spearmint","caraway","dill"]},
        "menthol":         {"cid": 16666,  "aroma": "menta, fresco",               "ingr": ["peppermint","spearmint"]},
        "thymol":          {"cid": 6989,   "aroma": "timo, erbaceo",               "ingr": ["thyme","oregano"]},
        "ethyl_acetate":   {"cid": 8857,   "aroma": "fruttato, solvente",          "ingr": ["strawberry","pineapple","wine"]},
        "isoamyl_acetate": {"cid": 31276,  "aroma": "banana, fruttato",            "ingr": ["banana","pear"]},
        "hexanal":         {"cid": 6184,   "aroma": "erbaceo, mela verde",         "ingr": ["apple","cucumber"]},
        "furfural":        {"cid": 7362,   "aroma": "caramello, mandorla",         "ingr": ["butter","whiskey","coffee"]},
        "2_furfurylthiol": {"cid": 13036,  "aroma": "caffè tostato",               "ingr": ["coffee","roasted_hazelnut"]},
        "vanillin":        {"cid": 1183,   "aroma": "vaniglia, dolce",             "ingr": ["tahiti_vanilla","butter","whiskey"]},
        "guaiacol":        {"cid": 460,    "aroma": "affumicato, speziato",        "ingr": ["whiskey","coffee","smoked_sausage"]},
        "diacetyl":        {"cid": 650,    "aroma": "burro, cremoso",              "ingr": ["butter","butterfat","wine"]},
        "ethanol":         {"cid": 702,    "aroma": "alcolico",                    "ingr": ["wine","beer"]},
        "acetic_acid":     {"cid": 176,    "aroma": "aceto, pungente",             "ingr": ["vinegar","wine"]},
        "lactic_acid":     {"cid": 107689, "aroma": "lattico, acidulo",            "ingr": ["yogurt","wine"]},
        "2_acetylpyrazine":{"cid": 13318,  "aroma": "pane tostato, nocciola",      "ingr": ["bread","coffee","roasted_hazelnut"]},
        "maltol":          {"cid": 10458,  "aroma": "caramello, zucchero cotto",   "ingr": ["bread","butter"]},
    }

    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    importati = 0
    errori = 0

    for nome, meta in COMPOSTI.items():
        try:
            cid = meta["cid"]
            # Fetch dettaglio da PubChem
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/JSON"
            req = urllib.request.Request(url, headers={"User-Agent": "Matter/1.0"})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read().decode())

            compound = data.get("PC_Compounds", [{}])[0]
            props = {}
            for p in compound.get("props", []):
                urn = p.get("urn", {})
                label = urn.get("label", "") + "_" + urn.get("name", "")
                val = p.get("value", {})
                v = val.get("sval") or val.get("fval") or val.get("ival")
                if v: props[label.lower()] = v

            formula = props.get("molecular formula_", "")
            iupac   = props.get("iupac name_preferred", "") or props.get("iupac name_traditional", "")
            mw      = props.get("molecular weight_", "")

            node_id = "pub_" + re.sub(r"[^a-z0-9]", "_", nome.lower())
            node_data = json.dumps({
                "pubchem_cid": cid,
                "formula": formula,
                "iupac": iupac,
                "mw": mw,
                "aroma": meta["aroma"],
                "ingredienti_tipici": meta["ingr"],
                "fonte": "PubChem NIH, pubblico dominio"
            }, ensure_ascii=False)

            cur.execute("""
                INSERT INTO nodes (id, type, name, domain, data)
                VALUES (%s, 'Composto', %s, 'chimica', %s)
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data
            """, (node_id, nome.replace("_", " "), node_data))

            # Archi verso nodi Ahn corrispondenti
            for ingr in meta["ingr"]:
                ahn_id = "ahn_" + ingr.lower().replace(" ", "_")
                cur.execute("""
                    INSERT INTO edges (from_id, to_id, relation, data)
                    VALUES (%s, %s, 'contiene_composto', '{}')
                    ON CONFLICT DO NOTHING
                """, (ahn_id, node_id))

            importati += 1
            click.echo(f"  OK: {nome} (CID:{cid}) — {meta['aroma']}")
            _t.sleep(0.5)

        except Exception as ex:
            click.echo(f"  ERRORE {nome}: {ex}")
            errori += 1

    cur.close(); conn.close()
    click.echo(f"\nFATTO: {importati} composti importati · {errori} errori")
    click.echo("Fonte: PubChem NIH — pubblico dominio, nessuna restrizione commerciale.")


@app.cli.command("import-contrasto")
def import_contrasto():
    """Aggiunge dati fisici per abbinamento per contrasto (grassi, zuccheri,
    sodio, amaro_index) ai nodi ingredienti esistenti. Eseguito in automatico
    dal migrate dopo ogni reseed. Fonti: USDA FoodData Central (CC0)."""
    if not DATABASE_URL:
        click.echo("DATABASE_URL non impostata — skip."); return
    DATI = {
        "prod_limone":   {"grassi_pct":0.2,"zuccheri_pct":2.5,"sodio_mg100g":2,"amaro_index":1,"profilo_contrasto":"acido"},
        "prod_lime":     {"grassi_pct":0.2,"zuccheri_pct":1.7,"sodio_mg100g":2,"amaro_index":1,"profilo_contrasto":"acido"},
        "prod_arancia":  {"grassi_pct":0.1,"zuccheri_pct":8.3,"sodio_mg100g":0,"amaro_index":0,"profilo_contrasto":"acido-dolce"},
        "prod_pomodoro": {"grassi_pct":0.1,"zuccheri_pct":2.4,"sodio_mg100g":5,"amaro_index":0,"profilo_contrasto":"acido"},
        "prod_aceto":    {"grassi_pct":0.0,"zuccheri_pct":0.1,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"acido-amaro"},
        "prod_fragola":  {"grassi_pct":0.3,"zuccheri_pct":5.1,"sodio_mg100g":5,"amaro_index":0,"profilo_contrasto":"acido"},
        "prod_lampone":  {"grassi_pct":0.3,"zuccheri_pct":5.7,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"acido"},
        "prod_mirtillo": {"grassi_pct":0.5,"zuccheri_pct":9.9,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"acido"},
        "prod_mela":     {"grassi_pct":0.2,"zuccheri_pct":10.1,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"dolce-acido"},
        "prod_vino_bianco":  {"grassi_pct":0.4,"zuccheri_pct":4.3,"sodio_mg100g":3,"amaro_index":3,"profilo_contrasto":"acido-amaro"},
        "prod_vino_rosso":   {"grassi_pct":0.0,"zuccheri_pct":2.6,"sodio_mg100g":5,"amaro_index":4,"profilo_contrasto":"amaro-acido"},
        "prod_burro":    {"grassi_pct":81.1,"zuccheri_pct":0.1,"sodio_mg100g":11,"amaro_index":0,"profilo_contrasto":"grasso"},
        "prod_panna":    {"grassi_pct":36.0,"zuccheri_pct":3.4,"sodio_mg100g":40,"amaro_index":0,"profilo_contrasto":"grasso"},
        "prod_latte":    {"grassi_pct":3.7,"zuccheri_pct":4.8,"sodio_mg100g":44,"amaro_index":0,"profilo_contrasto":"grasso-dolce"},
        "prod_salmone":  {"grassi_pct":20.0,"zuccheri_pct":0.0,"sodio_mg100g":55,"amaro_index":0,"profilo_contrasto":"grasso"},
        "prod_tonno":    {"grassi_pct":15.0,"zuccheri_pct":0.0,"sodio_mg100g":70,"amaro_index":0,"profilo_contrasto":"grasso"},
        "prod_manzo":    {"grassi_pct":9.0,"zuccheri_pct":0.0,"sodio_mg100g":70,"amaro_index":0,"profilo_contrasto":"grasso-proteico"},
        "prod_pollo":    {"grassi_pct":3.6,"zuccheri_pct":0.0,"sodio_mg100g":65,"amaro_index":0,"profilo_contrasto":"proteico"},
        "prod_uovo_tuorlo":  {"grassi_pct":9.5,"zuccheri_pct":0.4,"sodio_mg100g":124,"amaro_index":0,"profilo_contrasto":"grasso-proteico"},
        "prod_uovo_albume":  {"grassi_pct":0.1,"zuccheri_pct":0.7,"sodio_mg100g":166,"amaro_index":0,"profilo_contrasto":"proteico"},
        "prod_cioccolato_fondente": {"grassi_pct":43.0,"zuccheri_pct":22.0,"sodio_mg100g":1,"amaro_index":4,"profilo_contrasto":"amaro-grasso"},
        "prod_caffe_espresso": {"grassi_pct":0.2,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":4,"profilo_contrasto":"amaro"},
        "prod_caffe_filtro":  {"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":3,"profilo_contrasto":"amaro"},
        "prod_birra":    {"grassi_pct":0.6,"zuccheri_pct":3.8,"sodio_mg100g":4,"amaro_index":3,"profilo_contrasto":"amaro-acido"},
        "prod_porcini":  {"grassi_pct":3.5,"zuccheri_pct":2.0,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"amaro-aromatico"},
        "prod_shiitake": {"grassi_pct":0.5,"zuccheri_pct":1.0,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"amaro-umami"},
        "prod_zucchero": {"grassi_pct":0.0,"zuccheri_pct":82.0,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"dolce"},
        "prod_miele":    {"grassi_pct":0.0,"zuccheri_pct":82.0,"sodio_mg100g":4,"amaro_index":0,"profilo_contrasto":"dolce-aromatico"},
        "prod_yogurt":   {"grassi_pct":0.1,"zuccheri_pct":3.5,"sodio_mg100g":36,"amaro_index":0,"profilo_contrasto":"dolce-acido"},
        "prod_vaniglia": {"grassi_pct":0.1,"zuccheri_pct":0.0,"sodio_mg100g":5,"amaro_index":1,"profilo_contrasto":"aromatico"},
        "prod_cannella": {"grassi_pct":1.2,"zuccheri_pct":1.0,"sodio_mg100g":10,"amaro_index":2,"profilo_contrasto":"aromatico-amaro"},
        "prod_soia":     {"grassi_pct":1.5,"zuccheri_pct":6.0,"sodio_mg100g":400,"amaro_index":1,"profilo_contrasto":"salato-umami"},
        "prod_fagiolo":  {"grassi_pct":0.5,"zuccheri_pct":1.0,"sodio_mg100g":9,"amaro_index":3,"profilo_contrasto":"umami-amaro"},
        "prod_farina_frumento": {"grassi_pct":0.4,"zuccheri_pct":0.4,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"umami"},
        "prod_rum":      {"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":1,"amaro_index":1,"profilo_contrasto":"alcolico-speziato","abv_pct":40},
        "prod_whiskey":  {"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"alcolico-torbato","abv_pct":40},
        "prod_cognac":   {"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"alcolico-invecchiato","abv_pct":40},
        "prod_farina_segale":  {"grassi_pct":1.0,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":0,"profilo_contrasto":"neutro-base"},
        "prod_lievito_madre":  {"grassi_pct":0.7,"zuccheri_pct":3.2,"sodio_mg100g":10,"amaro_index":3,"profilo_contrasto":"acido-vivo"},
    }
    import psycopg2, json as _j
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    aggiornati = 0; saltati = 0
    for node_id, extra in DATI.items():
        cur.execute("SELECT data FROM nodes WHERE id=%s", (node_id,))
        row = cur.fetchone()
        if not row:
            saltati += 1; continue
        d = row[0] if isinstance(row[0], dict) else _j.loads(row[0])
        d.update(extra)
        cur.execute("UPDATE nodes SET data=%s::jsonb WHERE id=%s", (_j.dumps(d), node_id))
        aggiornati += 1
    conn.commit(); cur.close(); conn.close()
    click.echo(f"  Contrasto: {aggiornati} aggiornati · {saltati} saltati")


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


@app.route("/admin")
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


@app.route("/v1/admin/stats")
def admin_stats():
    """GT10 — Admin panel: statistiche base del prodotto."""
    secret = request.headers.get("X-Admin-Secret","")
    if (not os.environ.get("ADMIN_SECRET")) or secret != os.environ.get("ADMIN_SECRET"):
        return jsonify({"errore":"non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
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

        cur.close(); conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


def _invia_email_resend(to, subject, body_html, body_text=None):
    """Invia email via Resend. Mittente: onboarding@resend.dev (sandbox) finché
    non viene verificato un dominio proprio — allora cambiare RESEND_FROM.
    Ritorna True se ok, False se fallisce (mai blocca il flusso chiamante)."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        return False
    mittente = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    try:
        import urllib.request, json as _json
        payload = _json.dumps({
            "from": f"Matter <{mittente}>",
            "to": [to],
            "subject": subject,
            "html": body_html,
            "text": body_text or body_html
        }).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False


def _admin_autenticato():
    """True se la request porta un ADMIN_SECRET valido (header o query param ?s=)."""
    secret = request.headers.get("X-Admin-Secret","") or request.args.get("s","")
    return bool(os.environ.get("ADMIN_SECRET")) and secret == os.environ.get("ADMIN_SECRET")


@app.route("/v1/supporto", methods=["POST"])
def supporto():
    """Richiesta di supporto utente. Salva in log_domande con tipo='supporto',
    risponde subito via Haiku (solo info prodotto). Appare prioritaria nell'admin."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    body = request.json or {}
    testo = body.get("testo","").strip()
    if not testo:
        return jsonify({"errore":"testo vuoto"}), 400

    if DATABASE_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO log_domande (tipo, domanda, esito, user_id) VALUES (%s,%s,%s,%s)",
                ("supporto", testo[:1000], "ricevuto", str(user_id) if user_id else None))
            conn.commit(); cur.close(); conn.close()
        except Exception:
            pass

    system_supporto = (
        "Sei il supporto di Matter, strumento scientifico per professionisti F&B "
        "(bar, bakery, pasticceria, gelateria, caffetteria, cucina). "
        "Aiuta con domande su come usare l'app: lezioni, chat, flavor network, account, Pro. "
        "Non inventare funzionalita' non esistenti. Se non sai, di' che il team "
        "risponde via email entro 24 ore. Massimo 4 frasi, tono diretto e caldo."
    )
    risposta = None
    try:
        resp = _haiku_raw(system_supporto + "\n\nUtente: " + testo, max_tokens=300)
        if resp:
            risposta = resp
    except Exception:
        pass
    if not risposta:
        risposta = ("Non riesco a rispondere in questo momento. "
                    "Il tuo messaggio e' stato registrato — ti risponderemo via email entro 24 ore.")

    # notifica admin (tu) — arriva subito sulla tua Gmail
    admin_email = os.environ.get("MATTER_ADMIN_EMAIL", "miclam84@gmail.com")
    _invia_email_resend(
        to=admin_email,
        subject="⚠ Nuova richiesta supporto — Matter",
        body_html=(f"<p><strong>Nuova richiesta di supporto su Matter.</strong></p>"
                   f"<p><strong>Utente:</strong> {str(user_id) if user_id else 'non loggato'}</p>"
                   f"<p><strong>Messaggio:</strong><br>{testo}</p>"
                   f"<p><a href='/admin/assistenza'>Apri pannello assistenza →</a></p>"),
        body_text=f"Nuova richiesta supporto Matter.\nUtente: {user_id}\n\n{testo}"
    )

    return jsonify({"risposta": risposta})


@app.route("/admin/assistenza")
def admin_assistenza():
    """Pannello supporto admin: richieste esplicite (30g) + chat recenti (7g)."""
    if not _admin_autenticato():
        return "<p>Non autorizzato.</p>", 403
    if not DATABASE_URL:
        return "<p>DB non disponibile.</p>", 503
    s = request.args.get("s","")
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
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
        cur.close(); conn.close()
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


@app.route("/admin/assistenza/<user_id>/invia", methods=["POST"])
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


@app.route("/admin/assistenza/<user_id>")
def admin_assistenza_utente(user_id):
    """Scheda utente: contesto account + ultime interazioni + risposta Sonnet + mailto."""
    if not _admin_autenticato():
        return "<p>Non autorizzato.</p>", 403
    if not DATABASE_URL:
        return "<p>DB non disponibile.</p>", 503
    s = request.args.get("s","")
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT email, piano FROM utenti WHERE id=%s", (user_id,))
        u = cur.fetchone(); email = u[0] if u else "—"; piano = u[1] if u else "free"
        cur.execute("SELECT tipo, domanda, ts, esito FROM log_domande WHERE user_id=%s ORDER BY ts DESC LIMIT 20", (user_id,))
        domande = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM log_domande WHERE user_id=%s AND esito='ok'", (user_id,))
        n_ok = cur.fetchone()[0]
        cur.execute("SELECT fenomeni_trovati FROM log_domande WHERE user_id=%s AND fenomeni_trovati IS NOT NULL ORDER BY ts DESC LIMIT 1", (user_id,))
        r = cur.fetchone(); ultima_disc = r[0] if r else "—"
        cur.close(); conn.close()
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
