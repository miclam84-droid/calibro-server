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
# ── CONNECTION POOL Postgres ─────────────────────────────
_pg_pool = None

def _get_pool():
    global _pg_pool
    if _pg_pool is None and DATABASE_URL:
        from psycopg2 import pool as _pgpool
        _pg_pool = _pgpool.ThreadedConnectionPool(1, 10, DATABASE_URL)
    return _pg_pool

def _get_conn():
    """Prende una connessione dal pool. Usare con contesto try/finally + _release_conn."""
    p = _get_pool()
    if p:
        return p.getconn()
    return None

def _release_conn(conn):
    """Rilascia la connessione al pool."""
    p = _get_pool()
    if p and conn:
        try:
            p.putconn(conn)
        except Exception:
            pass




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



def _err(codice, lang="it"):
    """Restituisce il messaggio di errore nella lingua richiesta."""
    MSGS = {
        "email_gia_registrata": {
            "it": "email già registrata",
            "en": "email already registered",
            "es": "email ya registrado"
        },
        "credenziali_non_valide": {
            "it": "credenziali non valide",
            "en": "invalid credentials",
            "es": "credenciales no válidas"
        },
        "email_password_obbligatorie": {
            "it": "email e password obbligatorie",
            "en": "email and password required",
            "es": "email y contraseña requeridos"
        },
        "account_non_attivo": {
            "it": "Account non ancora attivo. Controlla la tua email.",
            "en": "Account not yet active. Check your email.",
            "es": "Cuenta aún no activa. Revisa tu email."
        },
        "troppi_tentativi": {
            "it": "Troppi tentativi. Aspetta un minuto e riprova.",
            "en": "Too many attempts. Wait a minute and try again.",
            "es": "Demasiados intentos. Espera un minuto e inténtalo de nuevo."
        },
        "autenticazione_richiesta": {
            "it": "autenticazione richiesta",
            "en": "authentication required",
            "es": "autenticación requerida"
        },
        "pro_required": {
            "it": "Le lezioni dalla 2 in poi sono disponibili con Matter Lab Pro.",
            "en": "Lessons from step 2 onwards are available with Matter Lab Pro.",
            "es": "Las lecciones desde el paso 2 están disponibles con Matter Lab Pro."
        },
        "trial_esaurito": {
            "it": "Hai esaurito le 5 chat di prova.",
            "en": "You have used all 5 trial chats.",
            "es": "Has agotado las 5 conversaciones de prueba."
        },
    }
    msg = MSGS.get(codice, {})
    return msg.get(lang) or msg.get("it") or codice


def _scheda_lang(data_dict, lang="it"):
    """GT4 — Legge il campo scheda nel formato multilingua.
    Supporta sia il formato legacy (stringa) sia il nuovo formato {it:"...", en:"..."}.
    Quando tutti i nodi saranno migrati al formato dizionario, il fallback legacy si rimuove."""
    scheda = data_dict.get("scheda", "")
    if isinstance(scheda, dict):
        return _pulisci_traduzione(scheda.get(lang) or scheda.get("it") or "")
    return scheda or ""



def _scheda_tradotta(node_id, data_dict, lang, conn):
    """Traduzione lazy della scheda: se non esiste per la lingua richiesta,
    la genera con Haiku e la salva nel nodo. Una volta sola per nodo+lingua."""
    if lang == "it":
        return _scheda_lang(data_dict, "it")
    
    scheda = data_dict.get("scheda", "")
    
    # Se è già un dizionario con la lingua richiesta, usa quella
    if isinstance(scheda, dict):
        if scheda.get(lang):
            return _pulisci_traduzione(scheda[lang])
        scheda_it = scheda.get("it", "") or ""
    else:
        scheda_it = scheda or ""
        scheda = {"it": scheda_it}
    
    if not scheda_it:
        return ""
    
    # Genera traduzione con Haiku
    if lang == "en":
        prompt = (f"Translate this Italian F&B technical sheet to English. "
                  f"Keep technical terms, numbers, and scientific accuracy. "
                  f"Output ONLY the translation, no headers or labels:\n\n{scheda_it[:1500]}")
    elif lang == "es":
        prompt = (f"Traduce esta ficha técnica italiana de F&B al español. "
                  f"Mantén los términos técnicos, números y precisión científica. "
                  f"Escribe SOLO la traducción, sin encabezados ni etiquetas:\n\n{scheda_it[:1500]}")
    else:
        return scheda_it
    
    try:
        traduzione = _haiku_raw(prompt, max_tokens=800)
        traduzione = _pulisci_traduzione(traduzione)
        if traduzione:
            scheda[lang] = traduzione
            # Salva nel nodo
            if conn and node_id:
                import psycopg2.extras as _psx
                cur = conn.cursor()
                data_dict["scheda"] = scheda
                cur.execute(
                    "UPDATE nodes SET data = %s WHERE id = %s",
                    (_psx.Json(data_dict), node_id)
                )
                conn.commit()
                cur.close()
            return traduzione
    except Exception as _te:
        print(f"[TRAD] {node_id} {lang}: {_te}", flush=True)
    
    return scheda_it  # fallback IT


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
                      "acidita_titolabile_pct","acidita_titolabile_g_l",
                      "coagulazione_t","t_sicurezza","variabilita",
                      "abv_pct","abv_min","abv_max",
                      "tds_pct","tds_pct_min","tds_pct_max",
                      "ey_pct_min","ey_pct_max",
                      "brix","brix_min","brix_max","brix_sciroppo_1_1",
                      "punto_fumo_c","ibu_min","ibu_max","co2_volumi",
                      "sale_pct","overrun_pct_min","overrun_pct_max",
                      "t_servizio","t_conservazione",
                      "t_beta_amilasi","t_alfa_amilasi","t_caramellizzazione",
                      "grassi_pct","acidita_libera_pct_max",
                      "cristallizzazione_t","proteine_pct","note","fonte"):
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
            if "acidita_titolabile_g_l" in p:
                r += f" · acidità titolabile: {p['acidita_titolabile_g_l']} g/L"
            if "brix" in p:
                r += f" · {p['brix']}°Brix"
            if "brix_min" in p and "brix_max" in p:
                r += f" · {p['brix_min']}-{p['brix_max']}°Brix"
            if "abv_min" in p and "abv_max" in p:
                r += f" · ABV {p['abv_min']}-{p['abv_max']}%"
            if "tds_pct_min" in p and "tds_pct_max" in p:
                r += f" · TDS {p['tds_pct_min']}-{p['tds_pct_max']}%"
            if "ey_pct_min" in p and "ey_pct_max" in p:
                r += f" · EY {p['ey_pct_min']}-{p['ey_pct_max']}%"
            if "punto_fumo_c" in p:
                r += f" · punto fumo: {p['punto_fumo_c']}°C"
            if "ibu_min" in p and "ibu_max" in p:
                r += f" · IBU {p['ibu_min']}-{p['ibu_max']}"
            if "co2_volumi" in p:
                r += f" · CO₂: {p['co2_volumi']} volumi"
            if "sale_pct" in p:
                r += f" · sale: {p['sale_pct']}%"
            if "overrun_pct_min" in p:
                r += f" · overrun: {p['overrun_pct_min']}-{p.get('overrun_pct_max','?')}%"
            if "t_servizio" in p:
                r += f" · T servizio: {p['t_servizio']}"
            if "t_conservazione" in p:
                r += f" · T conservazione: {p['t_conservazione']}"
            if "t_beta_amilasi" in p:
                r += f" · beta-amilasi: {p['t_beta_amilasi']}"
            if "t_alfa_amilasi" in p:
                r += f" · alfa-amilasi: {p['t_alfa_amilasi']}"
            if "t_caramellizzazione" in p:
                r += f" · caramellizzazione: {p['t_caramellizzazione']}"
            if "grassi_pct" in p:
                r += f" · grassi: {p['grassi_pct']}%"
            if "acidita_libera_pct_max" in p:
                r += f" · acidità libera max: {p['acidita_libera_pct_max']}%"
            if "note" in p:
                r += f" · note: {p['note']}"
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
            "- Structure the response in this EXACT format (use these labels in uppercase followed by a colon):\n"
            "PROBLEM: [one sentence identifying the physical cause]\n"
            "WHY: [physical explanation, max 2 sentences]\n"
            "NUMBER: [exact target number — temperature, pH, percentage, etc.]\n"
            "MEASURE: [how to measure at the counter — tool and method]\n"
            "ACTION: [what to do concretely — max 2 sentences]\n"
            "No markdown, asterisks, bold. Only the format above.\n"
            "- Never mention being an AI or using a graph.\n"
            "IMPORTANT: Always respond in English, regardless of the language of the technical context provided."
        )
    elif lang == "es":
        import datetime as _dt
        _oggi = _dt.date.today()
        _mese = _oggi.month
        _stagione_es = (
            "invierno (diciembre-febrero)" if _mese in (12,1,2) else
            "primavera (marzo-mayo)"       if _mese in (3,4,5) else
            "verano (junio-agosto)"        if _mese in (6,7,8) else
            "otono (septiembre-noviembre)"
        )
        _frutti_es = {
            "verano":    "tomates, calabacines, berenjenas, pimientos, albahaca, melocotones, sandía, melón",
            "otono":     "setas, trufa, calabaza, manzanas, peras, uvas, castanas, col",
            "invierno":  "cítricos (naranjas, mandarinas, limones), col, brocoli, hinojo, alcachofas",
            "primavera": "espárragos, guisantes, habas, alcachofas, espinacas, fresas, cerezas",
        }.get(_stagione_es.split(" ")[0], "")
        regole = (
            f"Hoy es {_oggi.strftime('%d/%m/%Y')} — estamos en {_stagione_es}.\n"
            f"Ingredientes de temporada: {_frutti_es}.\n"
            f"Usa SOLO productos de temporada salvo que la pregunta lo especifique.\n\n"
            "Eres una herramienta que explica la gastronomía a través de los fenómenos físicos "
            "y químicos: acidez, concentración, calor, ósmosis, estructura.\n\n"
            "CÓMO RESPONDER:\n"
            "- Ancla la respuesta al fenómeno físico del contexto y muestra el número objetivo.\n"
            "- Usa los números exactos del contexto. Si no están, usa tu conocimiento científico.\n"
            "- Nunca expliques tu razonamiento ni menciones el grafo. Responde directamente.\n"
            "- Tono de colega a colega: muestra el porqué físico. Sin lecciones.\n"
            "- Si hay números del usuario (ml, gramos, grados), usa la herramienta calcola.\n"
            "- Estructura la respuesta en este formato EXACTO (usa estas etiquetas en mayúsculas seguidas de dos puntos):\n"
            "PROBLEMA: [una frase que identifica la causa física]\n"
            "POR QUÉ: [explicación física, máx. 2 frases]\n"
            "NÚMERO: [el número objetivo exacto — temperatura, pH, porcentaje, etc.]\n"
            "MIDE: [cómo medirlo en el trabajo — herramienta y método]\n"
            "ACCIÓN: [qué hacer concretamente — máx. 2 frases]\n"
            "Sin markdown, asteriscos, negrita. Solo el formato anterior.\n"
            "- Nunca menciones ser una IA.\n"
            "IMPORTANTE: Responde SIEMPRE en español, independientemente del idioma del contexto técnico proporcionado."
        )
    else:
        import datetime as _dt
        _oggi = _dt.date.today()
        _mese = _oggi.month
        _stagione = (
            "inverno (dicembre-febbraio)" if _mese in (12,1,2) else
            "primavera (marzo-maggio)"   if _mese in (3,4,5) else
            "estate (giugno-agosto)"     if _mese in (6,7,8) else
            "autunno (settembre-novembre)"
        )
        _prodotti_stagione = {
            "estate":    "pomodori, zucchine, melanzane, peperoni, basilico, fichi, albicocche, pesche, more, anguria, melone",
            "autunno":   "funghi porcini, tartufo, zucca, mele, pere, uva, fichi d'India, cachi, radicchio, castagne, cavolo",
            "inverno":   "agrumi (arance, mandarini, limoni), cavolo nero, verza, broccoli, finocchi, carciofi, topinambur, cardi",
            "primavera": "asparagi, piselli, fave, carciofi, spinaci, agretti, fragole, ciliegie, erbe fresche (menta, erba cipollina)",
        }
        _stagione_key = _stagione.split(" ")[0]
        _frutti = _prodotti_stagione.get(_stagione_key, "")
        regole = (
            f"Data odierna: {_oggi.strftime('%d %B %Y')} — siamo in {_stagione}.\n"
            f"Ingredienti di stagione ora disponibili: {_frutti}.\n"
            f"Quando suggerisci abbinamenti o ingredienti, usa SOLO prodotti di stagione "
            f"a meno che la domanda non riguardi esplicitamente prodotti fuori stagione.\n\n"
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
            "- Struttura la risposta in questo formato ESATTO (usa questi label in maiuscolo seguiti da due punti):\n"
            "PROBLEMA: [una frase che identifica la causa fisica]\n"
            "PERCHÉ: [spiegazione fisica, max 2 frasi]\n"
            "NUMERO: [il numero bersaglio esatto — temperatura, pH, percentuale, ecc.]\n"
            "MISURA: [come si misura al banco — strumento e metodo]\n"
            "AZIONE: [cosa fare concretamente — max 2 frasi]\n"
            "Non usare markdown, asterischi, grassetti. Solo il formato sopra.\n"
            "- Non menzionare mai di essere un AI o di usare un grafo."
        )
    return f"{regole}\n\nCONTESTO DAL GRAFO:\n{contesto_txt}\n\nDOMANDA: {domanda}\n\nRISPOSTA:"

# ---- Mistral via HTTP diretto (nessun SDK) ------------------
def _mistral_raw(prompt, max_tokens=None):
    """Wrapper retrocompatibile → AI Gateway compat_mistral_raw."""
    import ai_gateway as GW
    return GW.compat_mistral_raw(prompt, max_tokens=max_tokens)

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
    """Wrapper retrocompatibile → AI Gateway route_chat."""
    import ai_gateway as GW
    return GW.route_chat(prompt, tools=_TOOLS)


def _haiku_raw(prompt, max_tokens=600):
    """Wrapper retrocompatibile → AI Gateway route_fast."""
    import ai_gateway as GW
    return GW.route_fast(prompt, max_tokens=max_tokens)


def chiedi_mistral(prompt, history=None):
    """Nome storico mantenuto — ora usa AI Gateway route_chat con fallback automatico."""
    import ai_gateway as GW
    try:
        out = GW.route_chat(prompt, tools=_TOOLS, history=history)
        if out:
            return out
    except Exception as e:
        print(f"[GW] route_chat fallito in chiedi_mistral: {e}", flush=True)
    return None

def log_evento(tipo, domanda, fenomeni=None, esito=None):
    """Log minimo per osservabilità. Ritorna id del log per feedback (AC5)."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS log_domande (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                tipo TEXT, domanda TEXT,
                fenomeni_trovati TEXT, esito TEXT
            )
        """)
        cur.execute(
            "INSERT INTO log_domande (tipo, domanda, fenomeni_trovati, esito) VALUES (%s,%s,%s,%s) RETURNING id",
            (tipo, domanda[:500], ",".join(fenomeni) if fenomeni else None, esito)
        )
        log_id = cur.fetchone()[0]
        conn.commit(); cur.close(); _release_conn(conn)
        return log_id
    except Exception:
        return None


def _init_account_tables():
    """Crea le tabelle account se non esistono. Chiamata al primo avvio."""
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        conn = _get_conn()
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
        conn.commit(); cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id FROM sessioni WHERE token=%s AND scade > NOW()",
            (token,))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
        return row[0] if row else None
    except Exception:
        return None

@app.route("/v1/auth/registra", methods=["POST"])
def registra():
    """AC2 — Registrazione: crea utente attivo=FALSE → email verifica → utente clicca → attivo=TRUE."""
    body = request.json or {}
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":_err("troppi_tentativi", body.get("lang","it"))}), 429
    email = (body.get("email","")).strip().lower()
    password = body.get("password","")
    if not email or not password:
        return jsonify({"errore":_err("email_password_obbligatorie", body.get("lang","it"))}), 400
    if len(password) < 8:
        return jsonify({"errore":"password minimo 8 caratteri"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2, secrets as _sec
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS verifica_email (
            token TEXT PRIMARY KEY, email TEXT NOT NULL,
            ts TIMESTAMPTZ DEFAULT NOW(),
            scade TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours',
            usato BOOLEAN DEFAULT FALSE)""")
        cur.execute(
            "INSERT INTO utenti (email, password_h, attivo) VALUES (%s,%s,FALSE) RETURNING id",
            (email, _hash_pw(password))
        )
        user_id = cur.fetchone()[0]
        tok = _sec.token_urlsafe(32)
        cur.execute("INSERT INTO verifica_email (token,email) VALUES (%s,%s)", (tok, email))
        conn.commit(); cur.close(); _release_conn(conn)
        base = os.environ.get("MATTER_BASE_URL","https://web-production-79457.up.railway.app")
        link = f"{base}/app?verifica={tok}"
        lang_reg = request.json.get("lang","it") if request.json else "it"
        if lang_reg == "en":
            _subj = "Confirm your email — Matter Lab"
            _btn  = "Activate my account"
            _p1   = "Welcome to <strong>Matter Lab</strong>."
            _p2   = "Confirm your email to activate your account:"
            _p3   = "Link valid for 24 hours."
            _txt  = f"Welcome to Matter Lab.\n\nConfirm email:\n{link}\n\nLink valid 24 hours."
            _msg  = "Account created. Check your email to activate it."
        elif lang_reg == "es":
            _subj = "Confirma tu email — Matter Lab"
            _btn  = "Activar mi cuenta"
            _p1   = "Bienvenido a <strong>Matter Lab</strong>."
            _p2   = "Confirma tu email para activar tu cuenta:"
            _p3   = "Enlace válido 24 horas."
            _txt  = f"Bienvenido a Matter Lab.\n\nConfirma email:\n{link}\n\nEnlace válido 24 horas."
            _msg  = "Cuenta creada. Revisa tu email para activarla."
        else:
            _subj = "Conferma la tua email — Matter Lab"
            _btn  = "Attiva il mio account"
            _p1   = "Benvenuto in <strong>Matter Lab</strong>."
            _p2   = "Conferma la tua email per attivare l'account:"
            _p3   = "Link valido 24 ore."
            _txt  = f"Benvenuto in Matter Lab.\n\nConferma email:\n{link}\n\nLink valido 24 ore."
            _msg  = "Account creato. Controlla la tua email per attivarlo."
        _invia_email_resend(
            to=email,
            subject=_subj,
            body_html=(
                f"<p style='font-family:sans-serif'>{_p1}</p>"
                f"<p style='font-family:sans-serif'>{_p2}</p>"
                f"<p><a href='{link}' style='background:#2C6E63;color:#fff;padding:12px 24px;"
                f"border-radius:8px;text-decoration:none;font-family:sans-serif;font-weight:600'>"
                f"{_btn}</a></p>"
                f"<p style='font-family:sans-serif;color:#999;font-size:13px'>{_p3}</p>"
            ),
            body_text=_txt
        )
        return jsonify({"ok":True,"messaggio":_msg,"verifica_richiesta":True})
    except Exception as e:
        lang_reg_fallback = (request.json or {}).get("lang","it")
        if "unique" in str(e).lower():
            return jsonify({"errore":_err("email_gia_registrata", lang_reg_fallback)}), 409
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/auth/verifica-email", methods=["POST"])
def verifica_email_route():
    """AC2b — Attiva account dal token email. Ritorna token sessione."""
    body = request.json or {}
    tok = (body.get("token","")).strip()
    if not tok or not DATABASE_URL:
        return jsonify({"errore":"token mancante"}), 400
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT email FROM verifica_email WHERE token=%s AND scade>NOW() AND usato=FALSE", (tok,)
        )
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"errore":"Link non valido o scaduto. Registrati di nuovo."}), 400
        email = row[0]
        cur.execute("UPDATE utenti SET attivo=TRUE WHERE email=%s", (email,))
        cur.execute("UPDATE verifica_email SET usato=TRUE WHERE token=%s", (tok,))
        cur.execute("SELECT id, piano FROM utenti WHERE email=%s", (email,))
        user_id, piano = cur.fetchone()
        token_sess = _genera_token()
        cur.execute("INSERT INTO sessioni (token, user_id) VALUES (%s,%s)", (token_sess, user_id))
        conn.commit(); cur.close(); _release_conn(conn)
        # Invia email di benvenuto
        lang_w = request.args.get("lang","it")
        base_w = os.environ.get("MATTER_BASE_URL","https://web-production-79457.up.railway.app")
        if lang_w == "en":
            _w_sub  = "Welcome to Matter Lab"
            _w_body = (
                f"<p style='font-family:sans-serif'>Your account is active. Welcome to <strong>Matter Lab</strong>.</p>"
                f"<p style='font-family:sans-serif'>Start with the phenomenon of the day in your discipline, "
                f"then explore the flavor network and ask questions in the chat.</p>"
                f"<p><a href='{base_w}/app' style='background:#2C6E63;color:#fff;padding:12px 24px;"
                f"border-radius:8px;text-decoration:none;font-family:sans-serif;font-weight:600'>Open Matter Lab</a></p>"
                f"<p style='font-family:sans-serif;color:#999;font-size:13px'>Science & Craft</p>"
            )
        elif lang_w == "es":
            _w_sub  = "Bienvenido a Matter Lab"
            _w_body = (
                f"<p style='font-family:sans-serif'>Tu cuenta está activa. Bienvenido a <strong>Matter Lab</strong>.</p>"
                f"<p style='font-family:sans-serif'>Empieza con el fenómeno del día en tu disciplina, "
                f"luego explora la red de sabores y haz preguntas en el chat.</p>"
                f"<p><a href='{base_w}/app' style='background:#2C6E63;color:#fff;padding:12px 24px;"
                f"border-radius:8px;text-decoration:none;font-family:sans-serif;font-weight:600'>Abrir Matter Lab</a></p>"
                f"<p style='font-family:sans-serif;color:#999;font-size:13px'>Science & Craft</p>"
            )
        else:
            _w_sub  = "Benvenuto in Matter Lab"
            _w_body = (
                f"<p style='font-family:sans-serif'>Il tuo account è attivo. Benvenuto in <strong>Matter Lab</strong>.</p>"
                f"<p style='font-family:sans-serif'>Inizia con il fenomeno del giorno nella tua disciplina, "
                f"poi esplora il flavor network e fai domande in chat.</p>"
                f"<p><a href='{base_w}/app' style='background:#2C6E63;color:#fff;padding:12px 24px;"
                f"border-radius:8px;text-decoration:none;font-family:sans-serif;font-weight:600'>Apri Matter Lab</a></p>"
                f"<p style='font-family:sans-serif;color:#999;font-size:13px'>Science & Craft</p>"
            )
        try:
            _invia_email_resend(to=email, subject=_w_sub, body_html=_w_body)
        except Exception:
            pass  # non bloccare il login se l'email di benvenuto fallisce
        lang_conf = request.args.get("lang", request.json.get("lang","it") if request.json else "it")
        _conf_msg = {"en":"Email confirmed. Welcome to Matter Lab.", "es":"Email confirmado. Bienvenido a Matter Lab."}.get(lang_conf, "Email confermata. Benvenuto in Matter Lab.")
        return jsonify({"ok":True,"token":token_sess,"piano":piano or "free","messaggio":_conf_msg})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@app.route("/v1/auth/login", methods=["POST"])
def login():
    """AC2 — Login con email + password, restituisce token sessione."""
    body = request.json or {}
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not _check_rate_limit(ip):
        return jsonify({"errore":_err("troppi_tentativi", body.get("lang","it"))}), 429
    email = (body.get("email","")).strip().lower()
    password = body.get("password","")
    if not email or not password:
        return jsonify({"errore":_err("email_password_obbligatorie", body.get("lang","it"))}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, password_h, piano FROM utenti WHERE email=%s AND attivo=TRUE",
                    (email,))
        row = cur.fetchone()
        if not row or not _verifica_pw(password, row[1]):
            cur.close(); _release_conn(conn)
            return jsonify({"errore":_err("credenziali_non_valide", body.get("lang","it"))}), 401
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
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"token":token,"piano":piano})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/quaderno", methods=["GET"])
def quaderno_lista():
    """AC3 — Lista esperimenti salvati dall'utente."""
    token = (request.headers.get("Authorization","").replace("Bearer ","") or
               request.headers.get("X-Token","") or
               (request.json or {}).get("token",""))
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"esperimenti":[]})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts, ph, brix, abv, ey_perc,
                   temperatura, idratazione, costo_mercato_eur
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC LIMIT 50
        """, (str(user_id),))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols,[str(v) if v is not None else None for v in r])) for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
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
        conn = _get_conn()
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
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"id":exp_id,"ok":True})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/prezzi/<ingrediente>")
def prezzi_ingrediente(ingrediente):
    """Restituisce il prezzo orientativo di mercato per un ingrediente.
    Cerca prima nei nodi Ingrediente del grafo (dataset Matter Lab),
    poi nei nodi Prodotto con costo_mercato_eur popolato."""
    lang = request.args.get("lang","it")
    ing_norm = ingrediente.lower().replace("-"," ")
    if not DATABASE_URL:
        return jsonify({"ingrediente":ingrediente,"prezzi":[]})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # Cerca nel dataset proprietario (nodi Ingrediente)
        cur.execute("""
            SELECT id, name, data
            FROM nodes
            WHERE type='Ingrediente'
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            LIMIT 3
        """, (f"%{ing_norm}%", f"%ing-{ing_norm.replace(' ','-')}%"))
        rows = cur.fetchall()
        prezzi = []
        for row in rows:
            d = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
            params = d.get("parametri_fisici", {})
            # Cerca costo nei parametri fisici del profilo
            costo = d.get("costo_mercato_eur") or params.get("costo_mercato_eur")
            if not costo:
                # Stima da categoria
                cat = d.get("categoria","")
                costo = _stima_costo_categoria(cat)
            prezzi.append({
                "nome": row[1],
                "costo_eur_kg": costo,
                "categoria": d.get("categoria",""),
                "fonte": "Matter Lab / ISMEA orientativo",
                "nota": "Prezzo orientativo di mercato. Per prezzi fornitore reali usa Cifra."
            })
        cur.close(); _release_conn(conn)
        return jsonify({"ingrediente":ingrediente,"prezzi":prezzi})
    except Exception as e:
        return jsonify({"ingrediente":ingrediente,"prezzi":[],"errore":str(e)})


def _stima_costo_categoria(categoria, nome=None):
    """Stima orientativa del costo per categoria merceologica (€/kg o €/L).
    Usa prezzi ISMEA se disponibili per nome specifico."""
    # Prima cerca per nome specifico nei prezzi ISMEA
    if nome:
        nome_low = nome.lower()
        for k, v in _PREZZI_ISMEA.items():
            if k in nome_low or nome_low in k:
                return v
    COSTI = {
        "distillati": 35.0, "liquori": 20.0, "vino": 8.0, "birra": 3.5,
        "succhi": 4.0, "sciroppi": 5.0, "frutta fresca": 3.5,
        "verdure": 2.0, "carni": 12.0, "salumi": 18.0, "pesce": 15.0,
        "latticini": 4.0, "formaggi": 14.0, "uova": 3.0,
        "farine": 1.5, "zuccheri": 1.2, "grassi": 6.0,
        "spezie": 25.0, "erbe aromatiche": 8.0,
        "cioccolato": 12.0, "cacao": 8.0,
        "caffè": 18.0, "tè": 12.0,
        "frutta secca": 20.0, "paste frutta secca": 35.0,
        "luppoli": 30.0, "malti": 2.5, "lieviti": 5.0,
        "uve": 2.0, "gelatine": 20.0, "addensanti": 15.0,
    }
    cat_low = categoria.lower() if categoria else ""
    for k, v in COSTI.items():
        if k in cat_low or cat_low in k:
            return v
    return 5.0  # default generico


@app.route("/v1/quaderno/<int:exp_id>/costo", methods=["GET","POST"])
def quaderno_calcola_costo(exp_id):
    """Calcola il food/drink cost di un esperimento nel quaderno.

    GET: calcola costo con ingredienti e quantità già salvati
    POST: calcola costo con ingredienti passati nel body
    {
      "ingredienti": [
        {"nome": "bourbon", "quantita_ml": 50},
        {"nome": "lime", "quantita_g": 22}
      ],
      "prezzo_vendita": 12.0  # opzionale
    }
    """
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401

    body = request.json or {}
    ingredienti_input = body.get("ingredienti", [])

    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503

    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()

        # Se GET, leggi ingredienti dall'esperimento salvato
        if request.method == "GET":
            cur.execute("SELECT ingredienti FROM esperimenti WHERE id=%s AND user_id=%s",
                       (exp_id, str(user_id)))
            row = cur.fetchone()
            if not row:
                cur.close(); _release_conn(conn)
                return jsonify({"errore":"esperimento non trovato"}), 404
            ingredienti_input = json.loads(row[0] or "[]")

        # Calcola costo per ogni ingrediente
        dettaglio = []
        costo_totale = 0.0

        for ing in ingredienti_input:
            nome = ing.get("nome","").lower()
            # Quantità — supporta ml, g, cl, oz, pz
            qty_ml = float(ing.get("quantita_ml", ing.get("ml", 0)) or 0)
            qty_g  = float(ing.get("quantita_g",  ing.get("g",  0)) or 0)
            qty_cl = float(ing.get("quantita_cl", ing.get("cl", 0)) or 0)
            qty_oz = float(ing.get("quantita_oz", ing.get("oz", 0)) or 0)
            qty_pz = float(ing.get("quantita_pz", ing.get("pz", 0)) or 0)

            # Normalizza tutto in grammi (approssimazione: 1ml ≈ 1g per liquidi)
            qty_totale_g = qty_g + qty_ml + (qty_cl * 10) + (qty_oz * 28.35) + (qty_pz * 100)

            # Cerca il prezzo nel grafo
            cur.execute("""
                SELECT name, data FROM nodes
                WHERE type='Ingrediente'
                AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                LIMIT 1
            """, (f"%{nome}%", f"%ing-{nome.replace(' ','-')}%"))
            ing_row = cur.fetchone()

            costo_eur_kg = 5.0  # default
            fonte = "stima generica"
            categoria = ""
            if ing_row:
                d = ing_row[1] if isinstance(ing_row[1], dict) else json.loads(ing_row[1] or "{}")
                categoria = d.get("categoria","")
                costo_eur_kg = (d.get("costo_mercato_eur") or
                               _stima_costo_categoria(categoria))
                fonte = "Matter Lab / ISMEA orientativo"

            costo_porzione = (qty_totale_g / 1000) * costo_eur_kg
            costo_totale += costo_porzione

            dettaglio.append({
                "ingrediente": nome,
                "quantita_g": round(qty_totale_g, 1),
                "costo_eur_kg": costo_eur_kg,
                "costo_porzione_eur": round(costo_porzione, 3),
                "categoria": categoria,
                "fonte": fonte
            })

        # Food cost percentuale
        prezzo_vendita = float(body.get("prezzo_vendita", 0) or 0)
        food_cost_pct = (costo_totale / prezzo_vendita * 100) if prezzo_vendita > 0 else None

        # Prezzo vendita suggerito a diversi food cost target
        suggeriti = {
            "fc_25pct": round(costo_totale / 0.25, 2),
            "fc_30pct": round(costo_totale / 0.30, 2),
            "fc_33pct": round(costo_totale / 0.33, 2),
        }

        cur.close(); _release_conn(conn)
        return jsonify({
            "exp_id": exp_id,
            "costo_totale_eur": round(costo_totale, 3),
            "dettaglio": dettaglio,
            "food_cost_pct": round(food_cost_pct, 1) if food_cost_pct else None,
            "prezzo_vendita": prezzo_vendita or None,
            "prezzi_vendita_suggeriti": suggeriti,
            "nota": "Prezzi orientativi di mercato. Per prezzi fornitore reali usa Cifra.",
            "fonte": "Matter Lab / ISMEA"
        })
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/strumenti")
@app.route("/v1/strumenti/<disciplina>")
def strumenti(disciplina=None):
    """Restituisce gli strumenti di misura per disciplina.
    Ogni strumento ha: nome, misura, numero_bersaglio, link_amazon."""
    STRUMENTI_DB = {
        "bar": [
            {"nome":"pH-metro da banco","misura":"pH","target":"0-14","amazon":"https://www.amazon.it/s?k=phmetro+digitale+professionale","prezzo_approx":"€25-80"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"0-85°","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+professionale","prezzo_approx":"€15-60"},
            {"nome":"Bilancia di precisione 0.1g","misura":"grammi","target":"0-500g","amazon":"https://www.amazon.it/s?k=bilancia+precisione+0.1g+cocktail","prezzo_approx":"€20-50"},
            {"nome":"Alcolimetro/ebulliometro","misura":"ABV%","target":"0-100%","amazon":"https://www.amazon.it/s?k=alcolimetro+digitale","prezzo_approx":"€30-150"},
            {"nome":"Termometro digitale sonda","misura":"°C","target":"-50/+300°C","amazon":"https://www.amazon.it/s?k=termometro+digitale+sonda+cucina","prezzo_approx":"€10-40"},
            {"nome":"Jigger graduato","misura":"ml","target":"5-60ml","amazon":"https://www.amazon.it/s?k=jigger+professionale+graduato","prezzo_approx":"€5-25"},
        ],
        "caffe": [
            {"nome":"Rifrattometro TDS caffè (VST/Atago)","misura":"TDS%","target":"1.15-1.55% filtro · 7-12% espresso","amazon":"https://www.amazon.it/s?k=rifrattometro+caffe+tds","prezzo_approx":"€50-300"},
            {"nome":"Bilancia barista 0.1g con timer","misura":"grammi + tempo","target":"ratio 1:2-17","amazon":"https://www.amazon.it/s?k=bilancia+barista+timer+professionale","prezzo_approx":"€25-150"},
            {"nome":"Termometro sonda digitale","misura":"°C","target":"90-96°C","amazon":"https://www.amazon.it/s?k=termometro+sonda+caffetteria","prezzo_approx":"€10-40"},
            {"nome":"Manometro espresso","misura":"bar","target":"9 bar","amazon":"https://www.amazon.it/s?k=manometro+macchina+espresso","prezzo_approx":"€15-60"},
        ],
        "panificazione": [
            {"nome":"pH-metro","misura":"pH","target":"pH madre: 3.7-3.9","amazon":"https://www.amazon.it/s?k=phmetro+lievito+madre","prezzo_approx":"€25-80"},
            {"nome":"Termometro sonda digitale","misura":"°C","target":"96-98°C interno pane","amazon":"https://www.amazon.it/s?k=termometro+sonda+forno+pane","prezzo_approx":"€10-40"},
            {"nome":"Bilancia professionale 1g","misura":"grammi","target":"baker%","amazon":"https://www.amazon.it/s?k=bilancia+professionale+panificazione","prezzo_approx":"€20-80"},
            {"nome":"Igrometro forno","misura":"umidità%","target":"80-90% primi minuti cottura","amazon":"https://www.amazon.it/s?k=igrometro+forno+cottura+pane","prezzo_approx":"€15-50"},
            {"nome":"Acidimetro titolabile","misura":"acido lattico%","target":"0.5-2%","amazon":"https://www.amazon.it/s?k=kit+acidita+titolabile+vino","prezzo_approx":"€20-60"},
        ],
        "pasticceria": [
            {"nome":"Termometro digitale sonda","misura":"°C","target":"crema 82-84°C · caramello 160°C","amazon":"https://www.amazon.it/s?k=termometro+sonda+pasticceria","prezzo_approx":"€10-40"},
            {"nome":"Bilancia 0.1g","misura":"grammi","target":"precisione fondamentale","amazon":"https://www.amazon.it/s?k=bilancia+precisione+pasticceria","prezzo_approx":"€20-50"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"sciroppi · confetture ≥65°","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+pasticceria","prezzo_approx":"€15-60"},
            {"nome":"Termometro IR (infrarossi)","misura":"°C","target":"temperaggio cioccolato 28-32°C","amazon":"https://www.amazon.it/s?k=termometro+infrarossi+cucina+professionale","prezzo_approx":"€20-60"},
        ],
        "gelateria": [
            {"nome":"Termometro sonda digitale","misura":"°C","target":"-10/-12°C servizio · -18°C conservazione","amazon":"https://www.amazon.it/s?k=termometro+sonda+gelateria+professionale","prezzo_approx":"€10-40"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"POD/PAC mix gelato","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+gelateria","prezzo_approx":"€15-60"},
            {"nome":"Bilancia professionale 1g","misura":"grammi","target":"overrun: peso × volume","amazon":"https://www.amazon.it/s?k=bilancia+professionale+gelateria","prezzo_approx":"€20-80"},
            {"nome":"Misuratore Aw (attività acqua)","misura":"Aw","target":"<0.85 per sicurezza","amazon":"https://www.amazon.it/s?k=misuratore+attivita+acqua+aw","prezzo_approx":"€200-800"},
        ],
        "vino": [
            {"nome":"pH-metro da banco","misura":"pH","target":"pH vino 3.0-3.8","amazon":"https://www.amazon.it/s?k=phmetro+enologico+vino","prezzo_approx":"€25-150"},
            {"nome":"Kit acidità volatile","misura":"g/L acido acetico","target":"<0.6 g/L","amazon":"https://www.amazon.it/s?k=kit+acidita+volatile+vino","prezzo_approx":"€20-80"},
            {"nome":"Rifrattometro mosto","misura":"°Brix/Babo","target":"maturità uva","amazon":"https://www.amazon.it/s?k=rifrattometro+mosto+uva","prezzo_approx":"£15-50"},
            {"nome":"Alcoolmetro Gay-Lussac","misura":"ABV%","target":"vino 10-15% vol","amazon":"https://www.amazon.it/s?k=alcoolmetro+gay+lussac+vino","prezzo_approx":"€10-40"},
            {"nome":"Kit SO2 libera/totale","misura":"mg/L","target":"SO2 libera 20-40 mg/L","amazon":"https://www.amazon.it/s?k=kit+analisi+so2+vino","prezzo_approx":"€30-100"},
        ],
        "birra": [
            {"nome":"Densimetro/areometro","misura":"densità/OG/FG","target":"OG 1.040-1.080","amazon":"https://www.amazon.it/s?k=densimetro+birra+homebrewing","prezzo_approx":"€5-20"},
            {"nome":"Rifrattometro birra","misura":"°Brix/Plato","target":"attenuation%","amazon":"https://www.amazon.it/s?k=rifrattometro+birra+professionale","prezzo_approx":"€15-50"},
            {"nome":"pH-metro digitale","misura":"pH","target":"mash pH 5.2-5.4","amazon":"https://www.amazon.it/s?k=phmetro+digitale+birra","prezzo_approx":"€25-80"},
            {"nome":"Termometro sonda","misura":"°C","target":"mash 62-72°C · lagerizzazione 0-2°C","amazon":"https://www.amazon.it/s?k=termometro+sonda+birra+homebrewing","prezzo_approx":"€10-40"},
            {"nome":"Manometro CO2 keg","misura":"bar","target":"carbonatazione 1.5-3 bar","amazon":"https://www.amazon.it/s?k=manometro+co2+fusto+birra","prezzo_approx":"€15-50"},
        ],
        "cucina": [
            {"nome":"Termometro sonda digitale","misura":"°C","target":"manzo MR 55-57°C · pollo 74°C","amazon":"https://www.amazon.it/s?k=termometro+sonda+cucina+professionale","prezzo_approx":"€10-40"},
            {"nome":"pH-metro","misura":"pH","target":"fermentati pH<4.6","amazon":"https://www.amazon.it/s?k=phmetro+cucina+fermentati","prezzo_approx":"€25-80"},
            {"nome":"Termometro IR infrarossi","misura":"°C","target":"olio frittura 170-180°C","amazon":"https://www.amazon.it/s?k=termometro+infrarossi+cucina","prezzo_approx":"€20-60"},
            {"nome":"Bilancia precisione 1g","misura":"grammi","target":"dosaggi sale/acido","amazon":"https://www.amazon.it/s?k=bilancia+precisione+cucina+professionale","prezzo_approx":"€20-50"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"confetture ≥65°","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+marmellata","prezzo_approx":"€15-60"},
        ],
    }

    if disciplina:
        disc_norm = disciplina.lower().replace("caffetteria","caffe")
        strumenti_disc = STRUMENTI_DB.get(disc_norm, [])
        return jsonify({"disciplina":disciplina,"strumenti":strumenti_disc})

    # Tutti
    return jsonify({"strumenti":STRUMENTI_DB})


@app.route("/v1/stt", methods=["POST"])
def stt():
    """Trascrizione audio via OpenAI Whisper (AI Gateway route_stt).
    Accetta audio WebM/MP4/WAV/M4A da browser.
    Pro-only: il barman parla al banco, l app trascrive e risponde."""
    token = request.headers.get("X-Token","") or (request.json or {}).get("token","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    # verifica piano pro
    if DATABASE_URL:
        try:
            import psycopg2
            conn_p = _get_conn()
            cur_p = conn_p.cursor()
            cur_p.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
            row_p = cur_p.fetchone()
            cur_p.close(); _release_conn(conn_p)
            if not row_p or row_p[0] != "pro":
                return jsonify({"errore":"Whisper è disponibile nel piano Pro"}), 403
        except Exception:
            pass
    if "audio" not in request.files:
        return jsonify({"errore":"file audio mancante"}), 400
    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    lang = request.args.get("lang","it")
    try:
        import ai_gateway as GW
        testo = GW.route_stt(audio_bytes, filename=audio_file.filename or "audio.webm", language=lang)
        if not testo:
            return jsonify({"errore":"trascrizione vuota"}), 422
        return jsonify({"trascrizione":testo,"lang":lang})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


@app.route("/v1/vision", methods=["POST"])
def vision():
    """Analisi immagine via OpenAI Vision gpt-4o-mini.
    Accetta foto di schede tecniche, etichette, piatti.
    Pro-only."""
    token = request.headers.get("X-Token","") or (request.json or {}).get("token","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if DATABASE_URL:
        try:
            import psycopg2
            conn_v = _get_conn()
            cur_v = conn_v.cursor()
            cur_v.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
            row_v = cur_v.fetchone()
            cur_v.close(); _release_conn(conn_v)
            if not row_v or row_v[0] != "pro":
                return jsonify({"errore":"Vision è disponibile nel piano Pro"}), 403
        except Exception:
            pass
    if "immagine" not in request.files:
        return jsonify({"errore":"immagine mancante"}), 400
    img_file = request.files["immagine"]
    img_bytes = img_file.read()
    media_type = img_file.content_type or "image/jpeg"
    lang = request.args.get("lang","it")
    prompt = (
        "Sei un esperto di chimica degli alimenti. "
        "Analizza questa immagine e identifica: "
        "1) Se è una scheda tecnica: estrai tutti i parametri fisici (pH, Aw, Brix, ABV, temperatura, ecc.) "
        "2) Se è un piatto/drink: identifica gli ingredienti principali e suggerisci i fenomeni fisici rilevanti "
        "3) Se è un'etichetta: estrai ingredienti, valori nutrizionali, parametri rilevanti. "
        f"Rispondi in {'italiano' if lang=='it' else 'English'}, in modo sintetico e professionale."
    )
    try:
        import ai_gateway as GW
        risposta = GW.route_vision(img_bytes, prompt, media_type=media_type)
        return jsonify({"analisi":risposta,"lang":lang})
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ingredienti, fenomeni,
                   ph, brix, abv, ey_perc, temperatura, idratazione,
                   costo_mercato_eur, area_mercato, ts
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
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
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM utenti WHERE lower(email)=%s AND attivo=TRUE", (email,))
            row = cur.fetchone()
            cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC
        """, (str(user_id),))
        rows = cur.fetchall()
        cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ph, brix, abv,
                   temperatura, idratazione, ingredienti, fenomeni
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM sessioni WHERE token=%s", (token,))
        conn.commit(); cur.close(); _release_conn(conn)
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
        conn = _get_conn()
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
        cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT email FROM reset_token WHERE token=%s AND scade>NOW() AND usato=FALSE", (tok,))
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"errore":"Link non valido o scaduto. Richiedine uno nuovo."}), 400
        email = row[0]
        cur.execute("UPDATE utenti SET password_h=%s WHERE email=%s", (_hash_pw(nuova_pw), email))
        cur.execute("UPDATE reset_token SET usato=TRUE WHERE token=%s", (tok,))
        cur.execute("DELETE FROM sessioni WHERE user_id=(SELECT id FROM utenti WHERE email=%s)", (email,))
        conn.commit(); cur.close(); _release_conn(conn)
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
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT password_h FROM utenti WHERE id=%s AND attivo=TRUE", (user_id,))
        row = cur.fetchone()
        if not row or not _verifica_pw(password, row[0]):
            cur.close(); _release_conn(conn)
            return jsonify({"errore":"password non corretta"}), 401
        anon = f"deleted_{_sec.token_hex(8)}@matter.deleted"
        cur.execute("UPDATE utenti SET email=%s, password_h='DELETED', attivo=FALSE WHERE id=%s",
                    (anon, user_id))
        cur.execute("DELETE FROM sessioni WHERE user_id=%s", (user_id,))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok":True,"messaggio":"Account cancellato. I tuoi dati sono stati rimossi."})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500


# ---- endpoint -----------------------------------------------
# ── FLAVOR NETWORK (FL3-FL4) ─────────────────────────────────────

@app.route("/v1/composti/<ingrediente>")
def composti_ingrediente(ingrediente):
    """FL4 — Composti aromatici di un ingrediente da PubChem NIH (pubblico dominio).
    Restituisce i composti volatili con profilo aromatico."""
    import unicodedata
    def _norm(s):
        s = s.lower().strip()
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.replace(" ","_").replace("-","_")

    ALIAS_IT = {
        "limone":"lemon","lime":"lime","arancia":"orange_peel","arancia_dolce":"sweet_orange",
        "pompelmo":"grapefruit","bergamotto":"bergamot","mandarino":"mandarin",
        "yuzu":"yuzu","cedro":"citrus","agrumi":"citrus",
        "aglio":"garlic","cipolla":"onion","scalogno":"shallot","porro":"leek",
        "burro":"butter","panna":"cream","latte":"milk","uova":"egg","uovo":"egg",
        "vaniglia":"vanilla","caffe":"coffee","caffè":"coffee","espresso":"coffee",
        "menta":"peppermint","menta piperita":"peppermint","menta verde":"spearmint",
        "basilico":"basil","timo":"thyme","origano":"oregano","rosmarino":"rosemary",
        "salvia":"sage","finocchio":"fennel","aneto":"dill","coriandolo":"coriander",
        "prezzemolo":"parsley","erba cipollina":"chive","maggiorana":"marjoram",
        "lavanda":"lavender","dragoncello":"tarragon","menta romana":"spearmint",
        "cannella":"cinnamon","garofano":"clove","noce moscata":"nutmeg",
        "zenzero":"ginger","pepe nero":"black_pepper","pepe":"black_pepper",
        "cardamomo":"cardamom","cumino":"cumin","curcuma":"turmeric",
        "zafferano":"saffron","anice":"anise","anice stellato":"star_anise",
        "fieno greco":"fenugreek","paprika":"paprika","peperoncino":"chili",
        "senape":"mustard","rafano":"horseradish","wasabi":"wasabi",
        "nocciola tostata":"roasted_hazelnut","nocciola":"hazelnut",
        "mandorla":"almond","noce":"walnut","pistacchio":"pistachio",
        "cocco":"coconut","arachide":"peanut","sesamo":"sesame","pino":"pine",
        "cioccolato":"chocolate","cacao":"cocoa","cioccolato fondente":"dark_chocolate",
        "cioccolato al latte":"chocolate",
        "lampone":"raspberry","fragola":"strawberry","mela":"apple","mela verde":"apple",
        "pera":"pear","banana":"banana","ananas":"pineapple","mango":"mango",
        "pesca":"peach","albicocca":"apricot","prugna":"plum","susina":"plum",
        "ciliegia":"cherry","uva":"grape","fico":"fig","melograno":"pomegranate",
        "melone":"melon","anguria":"watermelon","kiwi":"kiwi","papaya":"papaya",
        "mirtillo":"blueberry","ribes nero":"black_currant","ribes rosso":"red_currant",
        "mora":"blackberry","uva spina":"gooseberry","sambuco":"elderberry",
        "pomodoro":"tomato","cetriolo":"cucumber","carota":"carrot",
        "sedano":"celery","patata":"potato","patata dolce":"sweet_potato",
        "barbabietola":"beet","ravanello":"radish","carciofo":"artichoke",
        "asparago":"asparagus","peperone":"bell_pepper","melanzana":"eggplant",
        "zucchina":"zucchini","zucca":"pumpkin","spinaci":"spinach",
        "cavolo":"cabbage","cavolfiore":"cauliflower","broccoli":"broccoli",
        "mais":"corn","piselli":"pea","funghi":"mushroom","tartufo":"truffle",
        "funghi porcini":"mushroom","fungo":"mushroom",
        "vino":"wine","vino bianco":"white_wine","vino rosso":"red_wine",
        "champagne":"champagne","prosecco":"wine","spumante":"wine",
        "birra":"beer","birra ipa":"beer_ipa","birra weizen":"beer_weizen",
        "birra lager":"beer_lager","birra stout":"stout","birra porter":"porter",
        "whiskey":"whiskey","whisky":"scotch_whisky","bourbon":"bourbon",
        "rum":"rum","gin":"gin","vodka":"vodka","tequila":"tequila",
        "cognac":"cognac","brandy":"brandy","mezcal":"mezcal",
        "grappa":"grappa","sherry":"sherry","porto":"port",
        "aceto":"vinegar","aceto balsamico":"vinegar","salsa di soia":"soy_sauce",
        "miso":"miso","kimchi":"kimchi","crauti":"sauerkraut","kefir":"kefir",
        "yogurt":"yogurt","yogurt greco":"yogurt",
        "parmigiano":"parmesan","parmigiano reggiano":"parmesan",
        "cheddar":"cheddar","brie":"brie","camembert":"camembert",
        "mozzarella":"mozzarella","ricotta":"ricotta","grana":"parmesan",
        "formaggio capra":"goat_cheese","gorgonzola":"blue_cheese",
        "roquefort":"blue_cheese","formaggio erborinato":"blue_cheese",
        "pane":"bread","pane di segale":"rye_bread","pasta madre":"sourdough",
        "lievito madre":"sourdough","lievito":"yeast","malto":"malt",
        "luppolo":"hops","orzo":"barley","frumento":"wheat",
        "manzo":"beef","maiale":"pork","pollo":"chicken","agnello":"lamb",
        "anatra":"duck","tacchino":"turkey","pancetta":"bacon","prosciutto":"ham",
        "salsiccia":"sausage","carne arrosto":"roasted_meat","brodo":"broth",
        "salmone":"salmon","tonno":"tuna","merluzzo":"cod","acciuga":"anchovy",
        "gamberetto":"shrimp","ostrica":"oyster","vongola":"clam",
        "calamaro":"squid","anguilla":"eel","pesce":"fish",
        "olio oliva":"olive_oil","olio di oliva":"olive_oil","olio":"olive_oil",
        "strutto":"lard","grasso":"fat","miele":"honey","sciroppo acero":"maple_syrup",
        "caramello":"caramel","zucchero":"sugar","sale":"salt",
        "the verde":"green_tea","tè verde":"green_tea",
        "the nero":"black_tea","tè nero":"black_tea",
        "the":"black_tea","tè":"black_tea","matcha":"matcha",
        "camomilla":"chamomile","rosa":"rose","gelsomino":"jasmine",
        "ginepro":"juniper","rabarbaro":"rhubarb",
        "popcorn":"popcorn","patatine":"potato_chip",
        "affumicato":"smoked_food","carne affumicata":"smoked_meat",
    }

    ing_lower = ingrediente.lower().strip()
    ing_norm = _norm(ingrediente)
    ahn_name = ALIAS_IT.get(ing_lower) or ALIAS_IT.get(ing_norm.replace("_"," ")) or ing_norm

    try:
        conn = _get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        # Cerca composti PubChem collegati a questo ingrediente
        ahn_ids = [
            f"ahn_{ahn_name}",
            f"ahn_{ahn_name.replace('_',' ')}",
            f"ahn_{ahn_name.replace(' ','_')}",
        ]
        cur.execute('''
            SELECT DISTINCT n.id, n.name, n.data
            FROM nodes n
            JOIN edges e ON e.to_id = n.id
            WHERE e.from_id IN %s
            AND e.relation = 'contiene_composto'
            AND n.id LIKE 'pub_%%'
            ORDER BY n.name
            LIMIT 15
        ''', (tuple(ahn_ids),))

        rows = cur.fetchall()

        # Fallback fuzzy
        if not rows:
            cur.execute('''
                SELECT DISTINCT n.id, n.name, n.data
                FROM nodes n
                JOIN edges e ON e.to_id = n.id
                JOIN nodes ing ON e.from_id = ing.id
                WHERE ing.name ILIKE %s
                AND e.relation = \'contiene_composto\'
                AND n.id LIKE \'pub_%%\'
                ORDER BY n.name LIMIT 10
            ''', (f"%{ahn_name.replace('_',' ')}%",))
            rows = cur.fetchall()

        composti = []
        for row in rows:
            nid, nome, data = row
            d = data if isinstance(data, dict) else {}
            composti.append({
                "nome": nome.replace("_"," "),
                "aroma": d.get("aroma",""),
                "formula": d.get("formula",""),
                "pubchem_cid": d.get("pubchem_cid",""),
                "fonte": "PubChem NIH"
            })

        return jsonify({
            "ingrediente": ingrediente,
            "composti": composti,
            "nota": "Composti aromatici volatili principali — PubChem NIH (pubblico dominio)",
            "count": len(composti)
        })
    except Exception as e:
        try: _release_conn(conn)
        except: pass
        return jsonify({"errore": str(e), "composti": []}), 500


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
        "timo":"thyme","menta":"mint",
        "cioccolato":"cocoa",
        "caffe":"coffee","caffè":"coffee",
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
        # salumi e carni italiane
        "salame":"salami","salumi":"salami","prosciutto":"prosciutto",
        "pancetta":"bacon","guanciale":"guanciale","mortadella":"mortadella",
        "speck":"smoked_ham","salsiccia":"pork_sausage",
        "bresaola":"beef","lardo":"lard","coppa":"pork",
        # formaggi italiani
        "ricotta":"ricotta","pecorino":"pecorino","grana":"parmesan",
        "gorgonzola":"blue_cheese","taleggio":"cheese","asiago":"cheese",
        "scamorza":"cheese","provolone":"provolone","caciocavallo":"cheese",
        "burrata":"mozzarella","stracciatella":"mozzarella",
        # verdure stagionali
        "zucchine":"zucchini","pomodorino":"tomato","ciliegino":"tomato",
        "rucola":"arugula",
        "radicchio":"radicchio","cicoria":"chicory","finocchio":"fennel",
        "carciofo":"artichoke","asparago":"asparagus","pisello":"pea",
        "fava":"fava_bean","spinaci":"spinach","spinacio":"spinach",
        "cavolo":"cabbage","cavolfiore":"cauliflower",
        "broccolo":"broccoli","bietola":"beet","barbabietola":"beet",
        "fagiolino":"green_bean","fagiolo":"bean","ceci":"chickpea",
        "lenticchie":"lentil","cipollotto":"onion","porro":"leek",
        # frutta
        "fico":"fig","albicocca":"apricot","pesca":"peach","nettarina":"peach",
        "susina":"plum","prugna":"plum","caco":"persimmon","cachi":"persimmon",
        "melograno":"pomegranate","mora":"blackberry","ribes":"currant",
        "mirtillo":"blueberry",
        "pompelmo":"grapefruit","bergamotto":"bergamot",
        "cedro":"citron","uva":"grape","castagna":"chestnut",
        # pesce
        "baccalà":"cod","acciuga":"anchovy","alice":"anchovy",
        "seppia":"squid","polpo":"octopus","calamaro":"squid",
        "orata":"sea_bream","branzino":"sea_bass","sgombro":"mackerel",
        "vongola":"clam","cozza":"mussel","ostrica":"oyster",
        # pasta e cereali
        "pasta":"pasta","riso":"rice","farro":"spelt","orzo":"barley",
        "mais":"corn","farina":"flour","pane":"bread",
        # condimenti e grassi
        "olio extravergine":"olive_oil","evo":"olive_oil",
        "burro di cacao":"cocoa_butter","tahini":"sesame",
        "aceto balsamico":"balsamic_vinegar","salsa di soia":"soy_sauce",
        # erbe aromatiche
        "maggiorana":"marjoram","origano":"oregano","salvia":"sage",
        "alloro":"bay_leaf","erba cipollina":"chive",
        "finocchietto":"fennel","dragoncello":"tarragon",
        # spezie
        "noce moscata":"nutmeg","cardamomo":"cardamom","curcuma":"turmeric",
        "zafferano":"saffron","anice stellato":"star_anise",
        "chiodo di garofano":"clove","paprica":"paprika",
        # distillati e vini
        "amaro":"amaro","campari":"amaro","aperol":"amaro",
        "grappa":"grappa","cognac":"cognac","brandy":"brandy",
        "prosecco":"sparkling_wine","champagne":"sparkling_wine",
        "vino rosso":"red_wine","vino bianco":"white_wine",
        "marsala":"wine","vermouth":"vermouth",
        # dolci e dessert
        "cioccolato fondente":"dark_chocolate","cioccolato al latte":"milk_chocolate",
        "cioccolato bianco":"white_chocolate","cacao":"cocoa",
        "caramello":"caramel","vaniglia":"vanilla","cannella":"cinnamon",
        "pistacchio":"pistachio","mandorle":"almond",
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
        conn = _get_conn()
        cur = conn.cursor()
        rows = []

        # Pre-check: se non c'è alias Ahn, prova prima il dataset proprietario
        if not ahn_name:
            _ing_id_pre = f"ing-{ing_norm.replace(' ','-').replace('_','-')}"
            cur.execute("""
                SELECT id, name, data FROM nodes
                WHERE type='Ingrediente'
                AND (lower(name) = lower(%s) OR lower(id) = lower(%s)
                     OR lower(name) LIKE lower(%s))
                LIMIT 1
            """, (ing_it, _ing_id_pre, f"%{ing_it}%"))
            _pre_row = cur.fetchone()
            if _pre_row:
                _pre_data = _pre_row[2] if isinstance(_pre_row[2], dict) else _j.loads(_pre_row[2] or "{}")
                _pre_abbs = []
                for a in _pre_data.get("abbinamenti",{}).get("molecolari",[])[:5]:
                    _pre_abbs.append({"ingrediente":a.get("ingrediente_it",a.get("ingrediente_en","?")),
                        "composto":f"{a.get('overlap_score',50)} composti condivisi",
                        "overlap":float(a.get("overlap_score",50)),
                        "perche":a.get("meccanismo","affinità aromatica")})
                for a in _pre_data.get("abbinamenti",{}).get("contrasto",[])[:2]:
                    _pre_abbs.append({"ingrediente":a.get("ingrediente_it","?"),
                        "composto":"contrasto","overlap":30.0,
                        "perche":a.get("perche","contrasto fisico-percettivo")})
                # Integra con AI se abbinamenti sono meno di 4
                if _pre_abbs and len(_pre_abbs) >= 4:
                    cur.close(); _release_conn(conn)
                    return jsonify({"ingrediente":ingrediente,"abbinamenti":_pre_abbs,
                        "fonte":"dataset Matter Lab",
                        "nota":"Abbinamenti da profilo sensoriale proprietario Matter Lab"})
                # Nodo trovato ma con pochi abbinamenti — arricchisci con AI
                _cat_pre = _pre_data.get("categoria","")
                _prof_pre = _pre_data.get("categorie_aromatiche",[])
                _ai_pre = ("Dammi 5 abbinamenti per " + str(ingrediente) +
                           " (" + str(_cat_pre) + ") con meccanismo fisico-chimico. "
                           "JSON: {abbinamenti:[{ingrediente_it:str,meccanismo:str,overlap_score:int}]}")
                try:
                    _raw_pre = _haiku_raw(_ai_pre)
                    if _raw_pre:
                        import re as _re_pre
                        _mp = _re_pre.search(r'\{.*\}', _raw_pre, _re_pre.DOTALL)
                        if _mp:
                            _dp = _j.loads(_mp.group())
                            _ap = _dp.get("abbinamenti",[])
                            if _ap:
                                cur.close(); _release_conn(conn)
                                return jsonify({"ingrediente":ingrediente,
                                    "abbinamenti":[{"ingrediente":a.get("ingrediente_it","?"),
                                        "composto":"abbinamento aromatico",
                                        "overlap":float(a.get("overlap_score",50)),
                                        "perche":a.get("meccanismo","affinità aromatica")}
                                        for a in _ap[:5]],
                                    "fonte":"Matter Lab AI",
                                    "nota":"Abbinamenti generati da AI su profilo sensoriale"})
                except Exception:
                    pass

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
        # fallback 1: cerca per nome parziale
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
        # fallback 2: cerca nella mappa nomi italiani (flavor_nomi_it)
        if not rows:
            try:
                cur.execute("""
                    SELECT e.to_id, n.name,
                           (e.data->>'overlap')::numeric as overlap
                    FROM edges e
                    JOIN nodes n ON n.id = e.to_id
                    JOIN flavor_nomi_it fi ON fi.node_id = e.from_id
                    WHERE e.relation = 'abbinamento_aromatico'
                    AND (lower(fi.nome_it) LIKE lower(%s)
                         OR lower(fi.nome_en) LIKE lower(%s))
                    ORDER BY overlap DESC NULLS LAST LIMIT 8
                """, (f"%{ing_it}%", f"%{ing_it}%"))
                rows = cur.fetchall()
                if rows:
                    print(f"[NOMI_IT] '{ingrediente}' trovato via flavor_nomi_it", flush=True)
            except Exception as _fi_err:
                pass  # tabella non ancora popolata
        # Se Ahn ha trovato meno di 4 risultati, o tutti con lo stesso overlap (match fasullo),
        # prova il dataset proprietario più ricco
        if rows and len(rows) < 4:
            rows = []
        elif rows:
            overlaps = set(r[2] for r in rows if r[2] is not None)
            if len(overlaps) == 1:  # tutti lo stesso overlap = Ahn non ha dati reali
                rows = []

        # fallback 3: dataset proprietario Matter Lab (nodi Ingrediente)
        if not rows:
            try:
                cur.execute("""
                    SELECT e.to_id, n.name,
                           COALESCE((e.data->>'overlap')::numeric, 50) as overlap
                    FROM edges e
                    JOIN nodes n ON n.id = e.to_id
                    WHERE e.relation = 'abbinamento_aromatico'
                    AND e.from_id IN (
                        SELECT id FROM nodes WHERE type='Ingrediente'
                        AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                    )
                    ORDER BY overlap DESC NULLS LAST LIMIT 8
                """, (f"%{ing_it}%", f"%ing-{ing_norm.replace('_','-')}%"))
                rows = cur.fetchall()
                if rows:
                    print(f"[ML] '{ingrediente}' trovato via nodi Ingrediente", flush=True)
            except Exception as _ml_e:
                print(f"[ML ERR] {_ml_e}", flush=True)
        # fallback 4: abbinamenti da profilo sensoriale proprietario
        if not rows:
            try:
                # Cerca con più varianti del nome
                _ing_id = f"ing-{ing_norm.replace(' ','-').replace('_','-')}"
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Ingrediente'
                    AND (
                        lower(name) LIKE lower(%s)
                        OR lower(id) LIKE lower(%s)
                        OR lower(id) = lower(%s)
                        OR lower(name) = lower(%s)
                    )
                    LIMIT 1
                """, (f"%{ing_it}%", f"%{_ing_id}%", _ing_id, ing_it))
                ing_row = cur.fetchone()
                if ing_row:
                    ing_data = ing_row[2] if isinstance(ing_row[2], dict) else json.loads(ing_row[2] or "{}")
                    result_props = []
                    for a in ing_data.get("abbinamenti",{}).get("molecolari",[])[:5]:
                        result_props.append({
                            "ingrediente": a.get("ingrediente_it", a.get("ingrediente_en","?")),
                            "composto": f"{a.get('overlap_score',0)} composti condivisi",
                            "overlap": float(a.get("overlap_score",0)),
                            "perche": a.get("meccanismo","affinità aromatica")
                        })
                    for a in ing_data.get("abbinamenti",{}).get("contrasto",[])[:3]:
                        result_props.append({
                            "ingrediente": a.get("ingrediente_it","?"),
                            "composto": "contrasto",
                            "overlap": 30.0,
                            "perche": a.get("perche","contrasto fisico-percettivo")
                        })
                    if result_props:
                        cur.close(); _release_conn(conn)
                        return jsonify({"ingrediente":ingrediente,"abbinamenti":result_props,
                            "fonte":"dataset Matter Lab",
                            "nota":"Abbinamenti da profilo sensoriale proprietario Matter Lab"})
                    # Nodo trovato ma senza abbinamenti nel JSON — genera via AI
                    if ing_row:
                        _nome_ing = ing_row[1]
                        _cat = (ing_row[2] if isinstance(ing_row[2],dict) else {}).get("categoria","")
                        _profilo = (ing_row[2] if isinstance(ing_row[2],dict) else {}).get("categorie_aromatiche",[])
                        _ai_prompt = (
                            f"Sei un esperto di chimica degli alimenti. "
                            f"Dammi 5 abbinamenti per '{_nome_ing}' ({_cat}, profilo: {', '.join(_profilo[:3])}) "
                            f"con il meccanismo fisico-chimico per ognuno. "
                            f"Formato JSON: {{abbinamenti:[{{ingrediente_it:str,meccanismo:str,overlap_score:int}}]}}"
                        )
                        try:
                            _ai_raw = _haiku_raw(_ai_prompt)
                            if _ai_raw:
                                import re as _re2
                                _m = _re2.search(r'\{.*\}', _ai_raw, _re2.DOTALL)
                                if _m:
                                    _ai_data = json.loads(_m.group())
                                    _ai_abbs = _ai_data.get("abbinamenti",[])
                                    result_props = [{"ingrediente":a.get("ingrediente_it","?"),
                                        "composto":f"{a.get('overlap_score',50)} composti condivisi",
                                        "overlap":float(a.get("overlap_score",50)),
                                        "perche":a.get("meccanismo","affinità aromatica")}
                                        for a in _ai_abbs[:5]]
                                    if result_props:
                                        cur.close(); _release_conn(conn)
                                        return jsonify({"ingrediente":ingrediente,
                                            "abbinamenti":result_props,
                                            "fonte":"Matter Lab AI",
                                            "nota":"Abbinamenti generati da AI su profilo sensoriale"})
                        except Exception as _ai_e:
                            print(f"[AI ABB] {_ai_e}", flush=True)
            except Exception as _pe:
                print(f"[PROP ERR] {_pe}", flush=True)

        # fallback 5: AI diretto se nessun nodo trovato nel grafo
        if not rows:
            try:
                _ai_prompt5 = (
                    "Sei un esperto di chimica degli alimenti. "
                    + "Dammi 5 abbinamenti per " + str(ingrediente) + " con meccanismo fisico-chimico. "
                    + "Rispondi SOLO in JSON: {abbinamenti:[{ingrediente_it:str,meccanismo:str,overlap_score:int}]}"
                )
                _ai_raw5 = _haiku_raw(_ai_prompt5)
                if _ai_raw5:
                    import re as _re5
                    _m5 = _re5.search(r'\{.*\}', _ai_raw5, _re5.DOTALL)
                    if _m5:
                        _ai_data5 = json.loads(_m5.group())
                        _abbs5 = _ai_data5.get("abbinamenti",[])
                        if _abbs5:
                            cur.close(); _release_conn(conn)
                            return jsonify({"ingrediente":ingrediente,
                                "abbinamenti":[{"ingrediente":a.get("ingrediente_it","?"),
                                    "composto":"abbinamento aromatico",
                                    "overlap":float(a.get("overlap_score",50)),
                                    "perche":a.get("meccanismo","affinità aromatica")}
                                    for a in _abbs5[:5]],
                                "fonte":"Matter Lab AI",
                                "nota":"Abbinamenti generati da AI — ingrediente non ancora nel dataset molecolare"})
            except Exception as _ai5_e:
                print(f"[AI5] {_ai5_e}", flush=True)

        # fallback 2: ricerca semantica via embeddings OpenAI
        if not rows:
            try:
                import flavor_embeddings as FE, psycopg2 as _pg
                sem = FE.search_by_embedding(ingrediente, top_k=3)
                for _nid, _nname, _sim in sem:
                    if _sim > 0.72:
                        _c2 = _pg.connect(DATABASE_URL)
                        _cur2 = _c2.cursor()
                        _cur2.execute("""
                            SELECT e.to_id, n.name,
                                   (e.data->>'overlap')::numeric as overlap
                            FROM edges e
                            JOIN nodes n ON n.id = e.to_id
                            WHERE e.relation = 'abbinamento_aromatico'
                            AND e.from_id = %s
                            ORDER BY overlap DESC NULLS LAST LIMIT 8
                        """, (_nid,))
                        rows = _cur2.fetchall()
                        _cur2.close(); _release_conn(_c2)
                        if rows:
                            print(f"[EMBED] '{ingrediente}' → '{_nname}' (sim={_sim:.2f})", flush=True)
                            break
            except Exception as _ee:
                print(f"[EMBED FALLBACK] {_ee}", flush=True)
        cur.close(); _release_conn(conn)
        NOMI_IT = {
            "roasted beef":"manzo arrosto","beef":"manzo","chicken":"pollo",
            "pork":"maiale","lamb":"agnello","turkey":"tacchino",
            "salmon":"salmone","tuna":"tonno","shrimp":"gambero","cod":"merluzzo",
            "tomato":"pomodoro","garlic":"aglio","onion":"cipolla","carrot":"carota",
            "celery":"sedano","mushroom":"fungo","porcini mushroom":"porcini",
            "potato":"patata","eggplant":"melanzana","bell pepper":"peperone",
            "pumpkin":"zucca","zucchini":"zucchine",
            "apple":"mela","pear":"pera","strawberry":"fragola","raspberry":"lampone",
            "blueberry":"mirtillo","orange":"arancia","lemon":"limone","lime":"lime",
            "banana":"banana","pineapple":"ananas","mango":"mango","coconut":"cocco",
            "butter":"burro","cream":"panna","milk":"latte","cheese":"formaggio",
            "parmesan":"parmigiano","mozzarella":"mozzarella","yogurt":"yogurt",
            "egg":"uovo","olive oil":"olio d'oliva","sesame":"sesamo",
            "almond":"mandorla","hazelnut":"nocciola","walnut":"noce","peanut":"arachide",
            "coffee":"caffè","espresso":"espresso","tea":"tè","cocoa":"cacao",
            "chocolate":"cioccolato","vanilla":"vaniglia","honey":"miele","sugar":"zucchero",
            "basil":"basilico","rosemary":"rosmarino","thyme":"timo","mint":"menta",
            "parsley":"prezzemolo","cinnamon":"cannella","ginger":"zenzero",
            "black pepper":"pepe nero","chili":"peperoncino",
            "red wine":"vino rosso","white wine":"vino bianco","beer":"birra",
            "rum":"rum","whiskey":"whisky","gin":"gin","vodka":"vodka",
            "vinegar":"aceto","soy sauce":"salsa di soia",
            "mandarin":"mandarino","tangerine":"mandarino","grapefruit":"pompelmo",
            "concord grape":"uva concord","grape":"uva","fig":"fico",
            "leek":"porro","nira":"erba cipollina cinese","chive":"erba cipollina",
            "cheddar cheese":"cheddar","brie":"brie","camembert":"camembert",
            "cucumber":"cetriolo","zucchini":"zucchine","pumpkin":"zucca",
            "raw beef":"manzo crudo","cooked beef":"manzo cotto",
            "pork meat":"carne di maiale","lamb meat":"carne d'agnello",
            "white bread":"pane bianco","wheat bread":"pane di frumento",
            "rice":"riso","corn":"mais","oat":"avena",
            "olive":"oliva","capers":"capperi","anchovy":"acciuga",
            "lobster":"aragosta","crab":"granchio","mussel":"cozza","oyster":"ostrica",
            "lemon juice":"succo di limone","orange juice":"succo d'arancia",
            "apple juice":"succo di mela","tomato juice":"succo di pomodoro",
            "black coffee":"caffè nero","roasted coffee":"caffè tostato",
            "black tea":"tè nero","green tea":"tè verde","white tea":"tè bianco",
            "chamomile":"camomilla","peppermint":"menta piperita",
            "dark chocolate":"cioccolato fondente","milk chocolate":"cioccolato al latte",
            "caramel":"caramello","maple syrup":"sciroppo d'acero",
            "saffron":"zafferano","turmeric":"curcuma","cardamom":"cardamomo",
            "clove":"chiodo di garofano","nutmeg":"noce moscata","anise":"anice",
            "lavender":"lavanda","rose":"rosa","jasmine":"gelsomino",
        }
        abbinamenti = []
        for r in rows:
            nome_en = r[1].replace("_"," ").lower() if r[1] else ""
            # fallback: se manca la traduzione IT usa il nome Ahn in Title Case
            nome_fallback = r[1].replace("_"," ").title() if r[1] else "sconosciuto"
            nome_pulito = NOMI_IT.get(nome_en, nome_fallback)
            # salta i nodi senza nome
            if not nome_pulito or nome_pulito == "sconosciuto":
                continue
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



def _personalizza_abbinamenti(abbinamenti, profilo_utente):
    """Riordina gli abbinamenti in base al profilo sensoriale utente.
    Gli ingredienti con profilo simile a quello dell'utente vengono prima."""
    if not DATABASE_URL or not abbinamenti:
        return abbinamenti
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        scored = []
        for abb in abbinamenti:
            nome = abb.get("ingrediente","")
            cur.execute("""
                SELECT data FROM nodes WHERE type='Ingrediente'
                AND lower(name) LIKE lower(%s) LIMIT 1
            """, (f"%{nome}%",))
            row = cur.fetchone()
            score = abb.get("overlap", 0)
            if row:
                d = row[0] if isinstance(row[0], dict) else {}
                ps = d.get("profilo_sensoriale", {})
                # Calcola similarità coseno semplificata
                dims = ["acido","dolce","amaro","salato","umami","grasso","piccante","astringente","affumicato"]
                dot = sum(
                    profilo_utente.get(dim, 5) * (ps.get(dim, {}).get("valore", 5) if isinstance(ps.get(dim), dict) else float(ps.get(dim, 5)))
                    for dim in dims
                )
                score = abb.get("overlap", 0) * 0.5 + dot * 0.5
            scored.append((score, abb))
        cur.close(); _release_conn(conn)
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored]
    except Exception:
        return abbinamenti


# ── SOMMELIER DIGITALE v1 ────────────────────────────────────────────────────

@app.route("/v1/profilo-sensoriale", methods=["GET"])
def get_profilo_sensoriale():
    """Restituisce il profilo sensoriale dell'utente (9 dimensioni, pesi 0-10)."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"profilo": _profilo_default()})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # Aggiungi colonna se non esiste
        cur.execute("""
            ALTER TABLE utenti
            ADD COLUMN IF NOT EXISTS profilo_sensoriale JSONB DEFAULT '{}'::jsonb
        """)
        cur.execute("SELECT profilo_sensoriale FROM utenti WHERE id=%s", (user_id,))
        row = cur.fetchone()
        conn.commit(); cur.close(); _release_conn(conn)
        profilo = row[0] if row and row[0] else _profilo_default()
        return jsonify({"profilo": profilo, "interazioni": profilo.get("_n", 0)})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@app.route("/v1/feedback-abbinamento", methods=["POST"])
def feedback_abbinamento():
    """Registra il feedback (like/dislike) su un abbinamento e aggiorna il profilo sensoriale.
    Body: {"ingrediente": "lime", "abbinamento": "zucchero", "voto": 1, "disciplina": "bar"}
    voto: 1=like, -1=dislike
    """
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    body = request.json or {}
    ingrediente = body.get("ingrediente","")
    abbinamento = body.get("abbinamento","")
    voto = int(body.get("voto", 0))
    disciplina = body.get("disciplina","")
    if voto not in (1, -1) or not ingrediente:
        return jsonify({"errore":"voto deve essere 1 o -1, ingrediente obbligatorio"}), 400
    if not DATABASE_URL:
        return jsonify({"ok": True})
    try:
        import psycopg2, psycopg2.extras
        conn = _get_conn()
        cur = conn.cursor()
        # Leggi profilo attuale
        cur.execute("SELECT profilo_sensoriale FROM utenti WHERE id=%s", (user_id,))
        row = cur.fetchone()
        profilo = row[0] if row and row[0] else _profilo_default()
        # Aggiorna profilo in base al voto e al profilo sensoriale dell'ingrediente
        profilo = _aggiorna_profilo(profilo, ingrediente, abbinamento, voto, disciplina)
        # Salva profilo aggiornato
        cur.execute(
            "UPDATE utenti SET profilo_sensoriale=%s WHERE id=%s",
            (psycopg2.extras.Json(profilo), user_id)
        )
        # Salva log feedback
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_abbinamenti (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                ingrediente TEXT,
                abbinamento TEXT,
                voto INTEGER,
                disciplina TEXT,
                ts TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO feedback_abbinamenti (user_id, ingrediente, abbinamento, voto, disciplina)
            VALUES (%s,%s,%s,%s,%s)
        """, (str(user_id), ingrediente, abbinamento, voto, disciplina))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "profilo": profilo, "interazioni": profilo.get("_n", 0)})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


def _profilo_default():
    """Profilo sensoriale neutro di partenza (tutti i pesi a 5)."""
    return {
        "acido": 5.0, "dolce": 5.0, "amaro": 5.0,
        "salato": 5.0, "umami": 5.0, "grasso": 5.0,
        "piccante": 5.0, "astringente": 5.0, "affumicato": 5.0,
        "_n": 0  # numero di interazioni
    }


def _aggiorna_profilo(profilo, ingrediente, abbinamento, voto, disciplina):
    """Aggiorna il profilo sensoriale dell'utente in base al feedback.
    Usa un learning rate decrescente: le prime interazioni pesano di più.
    """
    import psycopg2
    # Cerca il profilo sensoriale dell'ingrediente abbinato nel DB
    if not DATABASE_URL:
        return profilo
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT data FROM nodes
            WHERE type='Ingrediente'
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            LIMIT 1
        """, (f"%{abbinamento}%", f"%ing-{abbinamento.lower().replace(' ','-')}%"))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not row:
            return profilo
        d = row[0] if isinstance(row[0], dict) else {}
        ps = d.get("profilo_sensoriale", {})
    except Exception:
        return profilo

    # Learning rate decrescente: lr = 0.3 / (1 + n/10)
    n = profilo.get("_n", 0)
    lr = 0.3 / (1 + n / 10)

    dim_map = {
        "acido": "acido", "dolce": "dolce", "amaro": "amaro",
        "salato": "salato", "umami": "umami", "grasso": "grasso",
        "piccante": "piccante", "astringente": "astringente", "affumicato": "affumicato"
    }
    for dim in dim_map:
        ing_val = ps.get(dim, {})
        ing_score = ing_val.get("valore", 5) if isinstance(ing_val, dict) else float(ing_val or 5)
        delta = lr * voto * (ing_score - 5)  # sposta verso il profilo dell'ingrediente se like, via se dislike
        profilo[dim] = max(0.0, min(10.0, profilo.get(dim, 5.0) + delta))

    profilo["_n"] = n + 1
    return profilo


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
        conn = _get_conn()
        cur = conn.cursor()
        # trova il nodo dell'ingrediente cercato — preferisce nodi con dati contrasto
        # Cerca in Prodotto E Ingrediente
        cur.execute("""
            SELECT id, name, data FROM nodes
            WHERE type IN ('Prodotto','Ingrediente')
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            ORDER BY CASE WHEN (data->>'profilo_contrasto') IS NOT NULL THEN 0 ELSE 1 END,
                     length(name) ASC
            LIMIT 1
        """, (f"%{ingrediente}%", f"%ing-{ingrediente.lower().replace(' ','-')}%"))
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
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
            cur.close(); _release_conn(conn)
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
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'grassi_pct')::numeric > 8
                    AND id != %s
                    ORDER BY (data->>'grassi_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "grasso":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'ph_min')::numeric < 4.5
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_dolce":
                # cerca dolci
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'zuccheri_pct')::numeric > 10
                    AND id != %s
                    ORDER BY (data->>'zuccheri_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_sale":
                # cerca salati
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'sodio_mg100g')::numeric > 100
                    AND id != %s
                    ORDER BY (data->>'sodio_mg100g')::numeric DESC LIMIT 2
                """, (node_id,))
            elif profilo_cercato == "dolce":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'ph_min')::numeric < 4.0
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "salato":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
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
                    import json as _j2
                    rd = rdata if isinstance(rdata, dict) else _j2.loads(rdata or "{}")
                    # spiegazione personalizzata per coppia
                    if meccanismo == "taglia_grasso":
                        perche = (f"{node_name} (pH {ph:.1f}) taglia il grasso di {rname}: "
                                  f"l'acidità emulsiona e pulisce la bocca dopo il grasso")
                    elif meccanismo == "richiede_acido":
                        perche = (f"Il grasso di {node_name} ammorbidisce e porta: "
                                  f"{rname} (pH {float(rd.get('ph_min',3)):.1f}) bilancia con acidità")
                    elif meccanismo == "smorzato_da_dolce":
                        perche = (f"L'amaro di {node_name} viene smorzato dai {rd.get('zuccheri_pct','?')}% "
                                  f"di zuccheri in {rname} — il dolce riduce la percezione amara")
                    elif meccanismo == "smorzato_da_sale":
                        perche = (f"Il sodio in {rname} ({rd.get('sodio_mg100g','?')}mg/100g) "
                                  f"sopprime l'amaro di {node_name} — piccole quantità bastano")
                    elif meccanismo == "bilanciato_da_acido":
                        perche = (f"Il dolce di {node_name} satura senza contrasto: "
                                  f"{rname} (pH {float(rd.get('ph_min',3)):.1f}) taglia e rinfresca")
                    elif meccanismo == "amplificato_da_acido":
                        perche = (f"Il salato di {node_name} si esalta con l'acido di {rname}: "
                                  f"insieme amplificano entrambi i sapori")
                    else:
                        perche = spiegazione
                    contrasti.append({
                        "ingrediente": rname,
                        "meccanismo": meccanismo,
                        "perche": perche
                    })

        cur.close(); _release_conn(conn)
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


@app.route("/manifest.json")
def manifest():
    """PWA manifest."""
    from flask import send_from_directory
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    """PWA Service Worker."""
    from flask import send_from_directory
    resp = send_from_directory("static", "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp

@app.route("/v1/quality-eval", methods=["POST"])
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

@app.route("/quality-test")
def quality_test():
    """Tool di test qualità interno — LLM-as-a-Judge"""
    with open(os.path.join(os.path.dirname(__file__), "static", "quality_test.html"), "r") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}

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
@app.route("/v1/disciplina/<nome>")
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

    if not fen_ids:
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
        # ordina: prima i prioritari (nell'ordine della lista), poi gli altri alfabetici
        def _sort_key(f):
            try:
                return (0, priorita_disc.index(f["id"]))
            except ValueError:
                return (1, f["nome"])
        fenomeni = sorted(fenomeni_raw, key=_sort_key)
    return jsonify({"disciplina": nome, "fenomeni": fenomeni, "totale": len(fenomeni)})


_lezione_cache = {}  # cache fenomeni per disciplina {nome: [fenomeni]}

@app.route("/lezione/<disciplina_nome>/<int:step>")
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
    elif lang == "es":
        quiz_prompt = f"""Crea un quiz sobre este fenómeno para un profesional F&B.
Fenómeno: {nome}
Número objetivo: {target}
Contenido: {scheda[:400]}

Responde SOLO con JSON válido, ningún texto antes o después:
{{"domanda":"...","opzioni":["opción correcta","opción incorrecta","opción incorrecta"],"corretta":0,"spiegazione":"explicación con el cálculo matemático en 2 líneas"}}

La respuesta correcta debe ser siempre la primera opción (índice 0).
La explicación debe incluir el número exacto."""
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
            import re as _re
            print(f"QUIZ RAW ({nome}): {raw[:300]}", flush=True)
            # rimuove caratteri di controllo che rompono json.loads
            raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
            # cerca il blocco JSON — anche se Haiku aggiunge testo prima/dopo
            m = _re.search(r'\{.*?\}', raw, _re.DOTALL)
            if not m:
                # prova a cercare pattern più ampio
                m = _re.search(r'\{.*\}', raw, _re.DOTALL)
            if m:
                try:
                    quiz_data = json.loads(m.group())
                except Exception as _je:
                    # prova a pulire apostrofi non escaped
                    cleaned = m.group().replace("'", '"')
                    try:
                        quiz_data = json.loads(cleaned)
                    except Exception:
                        print(f"QUIZ PARSE ERROR ({nome}): {_je} | raw: {raw[:300]}", flush=True)
                        return None
                opzioni = quiz_data.get("opzioni", [])
                if not opzioni or len(opzioni) < 2:
                    print(f"QUIZ NO OPZIONI ({nome}): {quiz_data}", flush=True)
                    return None
                return {
                    "domanda": quiz_data.get("domanda", ""),
                    "opzioni": opzioni,
                    "corretta": 0,
                    "spiegazione": quiz_data.get("spiegazione", "")
                }
            else:
                print(f"QUIZ NO JSON ({nome}): raw={raw[:300]}", flush=True)
    except Exception as _e:
        print(f"QUIZ EXCEPTION ({nome}): {_e}", flush=True)
        return None
    return None


@app.route("/quiz/<node_id>")
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
        return jsonify({"url": data.get("url"), "checkout_url": data.get("url"), "session_id": data.get("id")})
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
                conn = _get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE utenti SET piano='pro' WHERE id=%s", (user_id,))
                conn.commit(); cur.close(); _release_conn(conn)
    except Exception:
        pass
    return jsonify({"ok":True})


@app.route("/v1/admin/migrate-modello", methods=["POST"])
def admin_migrate_modello():
    """Aggiunge colonna modello a log_domande se non esiste."""
    secret = request.json.get("secret","") if request.json else ""
    if secret != os.environ.get("ADMIN_SECRET",""):
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


# ── FLASK CLI COMMANDS ────────────────────────────────────────────
import click


@app.cli.command("translate-graph")
def translate_graph():
    """GT4 - Traduce schede nodi IT->EN con Haiku. Uso: flask translate-graph"""
    if not DATABASE_URL:
        click.echo("DATABASE_URL non impostato"); return
    import psycopg2, time as _t
    conn = _get_conn()
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
    conn.commit(); cur.close(); _release_conn(conn)
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
            conn.commit(); cur.close(); _release_conn(conn)
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
        # Frutta e succhi
        "lemon juice raw": {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 167747},
        "lime juice raw":  {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 168195},
        "orange juice":    {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 169098},
        "grapefruit juice raw": {"fenomeno": "fen-acidita", "domain": "bar",   "fdc_id": 169106},
        "tomatoes red raw":{"fenomeno": "fen-acidita",  "domain": "cucina",    "fdc_id": 170457},
        "apples raw":      {"fenomeno": "fen-acidita",  "domain": "bakery",    "fdc_id": 171688},
        "strawberries raw":{"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 167762},
        "raspberries raw": {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 2346410},
        "blueberries raw": {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 2346411},
        "peaches raw":     {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 169928},
        "apricots raw":    {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 171697},
        "cherries raw":    {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 171719},
        "mango raw":       {"fenomeno": "fen-concentrazione","domain": "pasticceria","fdc_id": 169910},
        "pineapple raw":   {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 169949},
        "banana raw":      {"fenomeno": "fen-concentrazione","domain": "pasticceria","fdc_id": 173944},
        "pears raw":       {"fenomeno": "fen-acidita",  "domain": "pasticceria","fdc_id": 169943},
        "grapes red raw":  {"fenomeno": "fen-fermentazione","domain": "vino",  "fdc_id": 174683},
        "pomegranate raw": {"fenomeno": "fen-acidita",  "domain": "bar",       "fdc_id": 169134},
        # Latticini
        "milk whole 3.25%":{"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 171265},
        "cream heavy whipping":{"fenomeno":"fen-struttura","domain":"cucina",  "fdc_id": 2346386},
        "butter unsalted": {"fenomeno": "fen-cristallizzazione","domain":"bakery","fdc_id": 789828},
        "yogurt plain whole milk":{"fenomeno":"fen-fermentazione","domain":"cucina","fdc_id": 170886},
        "cheese parmesan": {"fenomeno": "fen-fermentazione","domain": "cucina","fdc_id": 173420},
        "cheese cheddar":  {"fenomeno": "fen-fermentazione","domain": "cucina","fdc_id": 173414},
        "cream cheese":    {"fenomeno": "fen-struttura", "domain": "pasticceria","fdc_id": 173417},
        "sour cream":      {"fenomeno": "fen-fermentazione","domain": "cucina","fdc_id": 170862},
        "buttermilk":      {"fenomeno": "fen-fermentazione","domain": "bakery","fdc_id": 170874},
        # Uova
        "egg white raw":   {"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 172183},
        "egg yolk raw":    {"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 172185},
        "egg whole raw":   {"fenomeno": "fen-coagulazione","domain": "cucina", "fdc_id": 171287},
        # Cereali e farine
        "wheat flour all-purpose":{"fenomeno":"fen-struttura","domain":"bakery","fdc_id": 168944},
        "rye flour":       {"fenomeno": "fen-struttura",  "domain": "bakery",  "fdc_id": 2512375},
        "bread sourdough": {"fenomeno": "fen-fermentazione","domain": "bakery","fdc_id": 172686},
        "oat flour":       {"fenomeno": "fen-struttura",  "domain": "bakery",  "fdc_id": 173903},
        "rice white raw":  {"fenomeno": "fen-concentrazione","domain": "cucina","fdc_id": 169756},
        "barley raw":      {"fenomeno": "fen-fermentazione","domain": "birra", "fdc_id": 169700},
        # Carne
        "beef ground 80% lean raw":{"fenomeno":"fen-calore","domain":"cucina", "fdc_id": 174036},
        "chicken breast raw":{"fenomeno":"fen-calore",    "domain": "cucina",  "fdc_id": 171477},
        "salmon atlantic raw":{"fenomeno":"fen-calore",   "domain": "cucina",  "fdc_id": 175167},
        "pork loin raw":   {"fenomeno": "fen-calore",     "domain": "cucina",  "fdc_id": 167903},
        "lamb raw":        {"fenomeno": "fen-calore",     "domain": "cucina",  "fdc_id": 174404},
        "turkey breast raw":{"fenomeno": "fen-calore",   "domain": "cucina",  "fdc_id": 171497},
        "tuna raw":        {"fenomeno": "fen-calore",     "domain": "cucina",  "fdc_id": 175159},
        "shrimp raw":      {"fenomeno": "fen-calore",     "domain": "cucina",  "fdc_id": 175178},
        "anchovy raw":     {"fenomeno": "fen-acidita",    "domain": "cucina",  "fdc_id": 174178},
        # Verdure
        "garlic raw":      {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 169230},
        "onion raw":       {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 170000},
        "carrots raw":     {"fenomeno": "fen-acidita",    "domain": "cucina",  "fdc_id": 170393},
        "cucumber raw":    {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 168409},
        "bell pepper raw": {"fenomeno": "fen-acidita",    "domain": "cucina",  "fdc_id": 170108},
        "spinach raw":     {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 168462},
        "cabbage raw":     {"fenomeno": "fen-fermentazione","domain": "cucina","fdc_id": 169975},
        "potato raw":      {"fenomeno": "fen-calore",     "domain": "cucina",  "fdc_id": 170026},
        "sweet potato raw":{"fenomeno": "fen-calore",    "domain": "cucina",  "fdc_id": 168482},
        "beets raw":       {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 169145},
        "asparagus raw":   {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 168390},
        "broccoli raw":    {"fenomeno": "fen-osmosi",     "domain": "cucina",  "fdc_id": 170379},
        # Oli e grassi
        "olive oil":       {"fenomeno": "fen-punto-fumo", "domain": "cucina",  "fdc_id": 171413},
        "coconut oil":     {"fenomeno": "fen-cristallizzazione","domain":"pasticceria","fdc_id": 172337},
        "lard":            {"fenomeno": "fen-punto-fumo", "domain": "cucina",  "fdc_id": 173411},
        # Zuccheri e dolcificanti
        "sugars granulated":{"fenomeno": "fen-concentrazione","domain":"pasticceria","fdc_id": 169655},
        "honey":           {"fenomeno": "fen-concentrazione","domain":"pasticceria", "fdc_id": 169640},
        "maple syrup":     {"fenomeno": "fen-concentrazione","domain":"pasticceria", "fdc_id": 169661},
        "molasses":        {"fenomeno": "fen-concentrazione","domain":"pasticceria", "fdc_id": 169652},
        # Cioccolato e caffè
        "chocolate dark 70-85%":{"fenomeno":"fen-cristallizzazione","domain":"pasticceria","fdc_id": 170272},
        "cocoa powder":    {"fenomeno": "fen-maillard",   "domain": "pasticceria","fdc_id": 169593},
        "coffee brewed espresso":{"fenomeno":"fen-estrazione","domain":"caffetteria","fdc_id": 171890},
        "coffee brewed filtered":{"fenomeno":"fen-estrazione","domain":"caffetteria","fdc_id": 171889},
        "tea black brewed":{"fenomeno": "fen-estrazione", "domain": "caffetteria","fdc_id": 171917},
        "tea green brewed":{"fenomeno": "fen-estrazione", "domain": "caffetteria","fdc_id": 171920},
        # Aceti e fermentati
        "vinegar balsamic":{"fenomeno": "fen-acidita",   "domain": "cucina",   "fdc_id": 172241},
        "vinegar apple cider":{"fenomeno": "fen-fermentazione","domain": "cucina","fdc_id": 173468},
        "sauerkraut":      {"fenomeno": "fen-fermentazione","domain": "cucina", "fdc_id": 169279},
        "miso":            {"fenomeno": "fen-fermentazione","domain": "cucina", "fdc_id": 172444},
        "soy sauce":       {"fenomeno": "fen-fermentazione","domain": "cucina", "fdc_id": 172234},
        # Funghi
        "mushrooms white raw":{"fenomeno":"fen-maillard", "domain": "cucina",  "fdc_id": 169251},
        "mushrooms shiitake raw":{"fenomeno":"fen-maillard","domain":"cucina", "fdc_id": 169253},
        # Frutta secca
        "almonds raw":     {"fenomeno": "fen-maillard",   "domain": "pasticceria","fdc_id": 170567},
        "hazelnuts raw":   {"fenomeno": "fen-maillard",   "domain": "pasticceria","fdc_id": 170581},
        "walnuts raw":     {"fenomeno": "fen-maillard",   "domain": "pasticceria","fdc_id": 170187},
        "coconut raw":     {"fenomeno": "fen-concentrazione","domain":"pasticceria","fdc_id": 169910},
        # Spezie
        "ginger raw":      {"fenomeno": "fen-osmosi",     "domain": "bar",      "fdc_id": 169231},
        "cinnamon ground": {"fenomeno": "fen-maillard",   "domain": "pasticceria","fdc_id": 171320},
        "black pepper":    {"fenomeno": "fen-estrazione", "domain": "cucina",   "fdc_id": 170931},
        "vanilla extract": {"fenomeno": "fen-estrazione", "domain": "pasticceria","fdc_id": 170627},
    }

    import psycopg2
    conn = _get_conn()
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
    _release_conn(conn)
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
    conn = _get_conn()
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

    cur.close(); _release_conn(conn)
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
    conn = _get_conn()
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
    conn.commit(); cur.close(); _release_conn(conn)
    click.echo(f"  Contrasto: {aggiornati} aggiornati · {saltati} saltati")


@app.cli.command("import-settore")
def import_settore():
    """Aggiunge campo 'settore':'f&b' a tutti i nodi esistenti (retrocompatibile).
    Prepara l'architettura per l'espansione a mestieri non F&B (ceramica, falegnameria, ecc.)
    senza toccare i 55 seed esistenti. Eseguito in automatico dal migrate."""
    if not DATABASE_URL:
        click.echo("  Settore: DATABASE_URL non impostata — skip."); return
    import psycopg2, json as _j
    conn = _get_conn()
    cur = conn.cursor()
    # aggiorna solo i nodi che non hanno ancora il campo settore
    cur.execute("SELECT id, data FROM nodes WHERE data->>'settore' IS NULL")
    rows = cur.fetchall()
    aggiornati = 0
    for node_id, data_raw in rows:
        d = data_raw if isinstance(data_raw, dict) else _j.loads(data_raw or '{}')
        d['settore'] = 'f&b'
        cur.execute("UPDATE nodes SET data=%s::jsonb WHERE id=%s", (_j.dumps(d), node_id))
        aggiornati += 1
    conn.commit(); cur.close(); _release_conn(conn)
    click.echo(f"  Settore: {aggiornati} nodi aggiornati con settore=f&b")


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
        conn = _get_conn()
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
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500



@app.route("/admin/build")
def admin_build_page():
    secret = request.args.get("s","")
    if secret != os.environ.get("ADMIN_SECRET",""):
        return "<h2>Secret non valido</h2>", 403
    from flask import send_from_directory
    return send_from_directory("static", "build.html")



@app.route("/admin/build-archi", methods=["POST"])
def admin_build_archi():
    """Crea archi abbinamento tra nodi Ingrediente già nel grafo."""
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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


@app.route("/admin/build-targets", methods=["POST"])
def admin_build_targets():
    """Popola target number nei nodi Ingrediente."""
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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




@app.route("/admin/debug-ingredienti")
def admin_debug_ingredienti():
    """Debug: mostra quanti ingredienti vede il server nel modulo."""
    secret = request.args.get("s","")
    if secret != os.environ.get("ADMIN_SECRET",""):
        return jsonify({"errore":"non autorizzato"}), 403
    try:
        import importlib, build_ingredient_graph as BIG
        importlib.reload(BIG)
        per_disc = {d: len(ings) for d, ings in BIG.INGREDIENTI.items()}
        totale = sum(per_disc.values())
        return jsonify({"totale": totale, "per_disciplina": per_disc})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500




@app.route("/admin/build-cron", methods=["POST","GET"])
def admin_build_cron():
    """Endpoint per cron job — genera UN ingrediente per chiamata.
    Railway può chiamarlo ogni 30 secondi via cron.
    Alternativa: chiamarlo in loop dal browser con setInterval.
    """
    secret = request.args.get("s","") or request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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


@app.route("/admin/build-continuo", methods=["POST"])
def admin_build_continuo():
    """Build continuo in background con checkpoint su DB.
    Gira finché non finisce — non dipende dal browser.
    Usa threading con loop interno che salva ogni ingrediente.
    """
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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


@app.route("/admin/build-batch", methods=["POST"])
def admin_build_batch():
    """Genera un batch di N ingredienti e si ferma.
    Non va in timeout perché è sincrono e limitato.
    Chiamare ripetutamente finché totale_generati non aumenta.
    Body: {"n": 20, "discipline": ["cucina"]}  # opzionali
    """
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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


@app.route("/admin/build-ingredienti", methods=["POST"])
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
    if secret != os.environ.get("ADMIN_SECRET",""):
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


@app.route("/admin/build-status")
def admin_build_status():
    """Stato del dataset ingredienti."""
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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



# Prezzi orientativi ISMEA 2024-2025 per ingredienti principali F&B
# Fonte: ISMEA mercati, prezzi all'ingrosso
_PREZZI_ISMEA = {
    # Carni (€/kg)
    "manzo": 8.50, "vitello": 9.20, "maiale": 4.80, "agnello": 9.80,
    "pollo": 2.90, "tacchino": 3.20, "coniglio": 5.50,
    # Salumi (€/kg)
    "prosciutto crudo": 14.00, "prosciutto cotto": 8.50, "salame": 9.00,
    "pancetta": 6.50, "mortadella": 5.20, "speck": 13.00,
    "bresaola": 18.00, "guanciale": 8.00, "nduja": 12.00,
    # Pesce (€/kg)
    "salmone": 12.00, "tonno": 15.00, "branzino": 14.00, "orata": 12.00,
    "baccalà": 9.00, "gamberi": 16.00, "cozze": 3.50, "vongole": 6.00,
    "acciughe": 5.00, "polpo": 8.00, "calamaro": 7.00,
    # Verdure (€/kg)
    "pomodoro": 1.20, "melanzana": 1.50, "zucchina": 1.30, "peperone": 2.00,
    "carota": 0.80, "cipolla": 0.90, "aglio": 3.50, "patata": 0.70,
    "spinaci": 2.50, "rucola": 3.00, "finocchio": 1.20, "carciofo": 2.80,
    "asparagi": 4.50, "funghi champignon": 3.50, "porcini": 18.00,
    # Frutta (€/kg)
    "limone": 1.50, "arancia": 1.20, "fragola": 4.00, "pesca": 2.50,
    "albicocca": 2.80, "mela": 1.20, "pera": 1.50, "uva": 2.00,
    "banana": 1.20, "ananas": 2.50, "mango": 4.50, "lime": 3.00,
    # Latticini (€/kg o L)
    "latte": 0.95, "panna fresca": 2.80, "burro": 5.50,
    "mozzarella di bufala": 8.50, "parmigiano reggiano": 12.00,
    "pecorino romano": 9.00, "ricotta": 4.50, "gorgonzola": 10.00,
    # Farine e cereali (€/kg)
    "farina 00": 0.85, "farina integrale": 1.20, "semola rimacinata": 1.00,
    "riso carnaroli": 3.20, "riso basmati": 2.50, "farro": 2.00,
    # Oli e grassi (€/L o kg)
    "olio extravergine": 7.50, "olio di girasole": 2.50,
    # Distillati (€/L)
    "gin": 15.00, "vodka": 10.00, "rum bianco": 10.00, "rum scuro": 12.00,
    "whisky": 18.00, "bourbon": 16.00, "tequila": 18.00, "mezcal": 25.00,
    "cognac": 30.00, "grappa": 12.00,
    # Vino (€/L)
    "vino rosso": 3.50, "vino bianco": 3.00, "prosecco": 4.50,
    # Spezie (€/kg)
    "pepe nero": 15.00, "cannella": 12.00, "curcuma": 8.00,
    "zafferano": 1500.00, "cardamomo": 25.00, "vaniglia": 200.00,
    # Zuccheri (€/kg)
    "zucchero": 1.20, "miele": 8.00, "sciroppo di agave": 6.00,
    # Cioccolato (€/kg)
    "cioccolato fondente 70%": 8.00, "cioccolato al latte": 6.50,
    "cioccolato bianco": 7.00, "cacao in polvere": 9.00,
}



# Traduzioni statiche nomi fenomeni e discipline (IT→EN→ES)
_NOME_TRAD = {
    "en": {
        # Fenomeni completi (52)
        "Acidità": "Acidity", "Fermentazione lattica": "Lactic fermentation",
        "Fermentazione acetica": "Acetic fermentation", "Maillard": "Maillard reaction",
        "Reazione di Maillard": "Maillard reaction",
        "Abbassamento crioscopico": "Cryoscopic depression",
        "Punto di congelamento": "Freezing point", "Overrun": "Overrun",
        "Attività dell'acqua": "Water activity",
        "Concentrazione zuccherina": "Sugar concentration",
        "Estrazione caffè": "Coffee extraction", "TDS": "TDS",
        "Solubilità": "Solubility", "Saturazione": "Saturation",
        "Struttura proteica": "Protein structure",
        "Reticolo proteico": "Protein network",
        "Lievitazione chimica": "Chemical leavening",
        "Cottura sous vide": "Sous vide cooking",
        "Temperatura di servizio": "Service temperature",
        "Diluizione": "Dilution", "Bilanciamento": "Balance",
        "Carbonatazione forzata": "Forced carbonation",
        "Rifermentazione": "Refermentation",
        "Caramellizzazione": "Caramelization", "Gelatinizzazione": "Gelatinization",
        "Emulsione": "Emulsion", "Cristallizzazione": "Crystallization",
        "Osmosi": "Osmosis", "Denaturazione": "Denaturation",
        "Carbonatazione": "Carbonation", "Estrazione": "Extraction",
        "Concentrazione": "Concentration", "Idratazione": "Hydration",
        "Struttura del glutine": "Gluten structure", "Lievitazione": "Leavening",
        "Ossidazione": "Oxidation", "Riduzione": "Reduction",
        "Fermentazione alcolica": "Alcoholic fermentation", "Fermentazione": "Fermentation",
        "Distillazione": "Distillation", "Infusione": "Infusion",
        "Macerazione": "Maceration", "Filtrazione": "Filtration",
        "Pastorizzazione": "Pasteurization", "Sterilizzazione": "Sterilization",
        "Calore / cinetica termica": "Heat / thermal kinetics",
        "Pressione": "Pressure", "Viscosità": "Viscosity",
        "Tensione superficiale": "Surface tension", "Diffusione": "Diffusion",
        "Coagulazione": "Coagulation", "Proteolisi": "Proteolysis",
        "Lipolisi": "Lipolysis", "Amidolisi": "Starch hydrolysis",
        "Fermentazione malolattica": "Malolactic fermentation",
        "Invecchiamento": "Aging", "Affinamento": "Maturation",
        "Tostatura": "Roasting", "Affumicatura": "Smoking",
        "Essiccazione": "Drying", "Salatura": "Salting",
        "Fermentazione lattica spontanea": "Wild lactic fermentation",
        "Attività enzimatica": "Enzymatic activity",
        "Reazione di Bruno": "Browning reaction",
        "Struttura": "Structure", "Tessitura": "Texture",
        "Colore": "Color", "Aroma": "Aroma",
        # Sicurezza
        "Zona di pericolo": "Danger zone", "Shelf life": "Shelf life",
        "Aw": "Water activity", "Contaminazione": "Contamination",
        "Atmosfera modificata": "Modified atmosphere",
        # Discipline
        "Bar": "Bar", "Cucina": "Kitchen", "Panificazione": "Baking",
        "Pasticceria": "Pastry", "Gelateria": "Gelato", "Caffè": "Coffee",
        "Vino": "Wine", "Birra": "Beer", "Sicurezza alimentare": "Food safety",
        "Cucina asiatica": "Asian cuisine", "Cucina indiana": "Indian cuisine",
        "Cucina giapponese": "Japanese cuisine",
    },
    "es": {
        # Fenomeni completi (52)
        "Acidità": "Acidez", "Fermentazione lattica": "Fermentación láctica",
        "Fermentazione acetica": "Fermentación acética", "Maillard": "Reacción de Maillard",
        "Reazione di Maillard": "Reacción de Maillard",
        "Abbassamento crioscopico": "Descenso crioscópico",
        "Punto di congelamento": "Punto de congelación", "Overrun": "Overrun",
        "Attività dell'acqua": "Actividad del agua",
        "Concentrazione zuccherina": "Concentración de azúcar",
        "Estrazione caffè": "Extracción de café", "TDS": "TDS",
        "Solubilità": "Solubilidad", "Saturazione": "Saturación",
        "Struttura proteica": "Estructura proteica",
        "Reticolo proteico": "Red proteica",
        "Lievitazione chimica": "Leudado químico",
        "Cottura sous vide": "Cocción sous vide",
        "Temperatura di servizio": "Temperatura de servicio",
        "Diluizione": "Dilución", "Bilanciamento": "Equilibrio",
        "Carbonatazione forzata": "Carbonatación forzada",
        "Rifermentazione": "Refermentación",
        "Caramellizzazione": "Caramelización", "Gelatinizzazione": "Gelatinización",
        "Emulsione": "Emulsión", "Cristallizzazione": "Cristalización",
        "Osmosi": "Ósmosis", "Denaturazione": "Desnaturalización",
        "Carbonatazione": "Carbonatación", "Estrazione": "Extracción",
        "Concentrazione": "Concentración", "Idratazione": "Hidratación",
        "Struttura del glutine": "Estructura del gluten", "Lievitazione": "Leudado",
        "Ossidazione": "Oxidación", "Riduzione": "Reducción",
        "Fermentazione alcolica": "Fermentación alcohólica", "Fermentazione": "Fermentación",
        "Distillazione": "Destilación", "Infusione": "Infusión",
        "Macerazione": "Maceración", "Filtrazione": "Filtración",
        "Pastorizzazione": "Pasteurización", "Sterilizzazione": "Esterilización",
        "Calore / cinetica termica": "Calor / cinética térmica",
        "Pressione": "Presión", "Viscosità": "Viscosidad",
        "Tensione superficiale": "Tensión superficial", "Diffusione": "Difusión",
        "Coagulazione": "Coagulación", "Proteolisi": "Proteólisis",
        "Lipolisi": "Lipólisis", "Amidolisi": "Hidrólisis del almidón",
        "Fermentazione malolattica": "Fermentación maloláctica",
        "Invecchiamento": "Envejecimiento", "Affinamento": "Maduración",
        "Tostatura": "Tostado", "Affumicatura": "Ahumado",
        "Essiccazione": "Secado", "Salatura": "Salazón",
        "Fermentazione lattica spontanea": "Fermentación láctica espontánea",
        "Attività enzimatica": "Actividad enzimática",
        "Reazione di Bruno": "Reacción de pardeamiento",
        "Struttura": "Estructura", "Tessitura": "Textura",
        "Colore": "Color", "Aroma": "Aroma",
        # Sicurezza
        "Zona di pericolo": "Zona de peligro", "Shelf life": "Vida útil",
        "Aw": "Actividad de agua", "Contaminazione": "Contaminación",
        "Atmosfera modificata": "Atmósfera modificada",
        # Discipline
        "Bar": "Bar", "Cucina": "Cocina", "Panificazione": "Panadería",
        "Pasticceria": "Pastelería", "Gelateria": "Heladería", "Caffè": "Café",
        "Vino": "Vino", "Birra": "Cerveza", "Sicurezza alimentare": "Seguridad alimentaria",
        "Cucina asiatica": "Cocina asiática", "Cucina indiana": "Cocina india",
        "Cucina giapponese": "Cocina japonesa",
    }
}

def _traduci_nome(nome, lang, conn=None):
    """Traduce il nome di un fenomeno o disciplina nella lingua richiesta.
    Se non trovato nel dizionario statico, usa Haiku e salva nel DB."""
    if not nome or lang == "it":
        return nome
    # Cerca nel dizionario statico
    tradotto = _NOME_TRAD.get(lang, {}).get(nome)
    if tradotto:
        return tradotto
    # Traduzione lazy via Haiku
    if lang == "en":
        prompt = f"Translate this Italian F&B technical term to English (2-5 words max): {nome}"
    elif lang == "es":
        prompt = f"Traduce este término técnico italiano de F&B al español (2-5 palabras): {nome}"
    else:
        return nome
    try:
        trad = _haiku_raw(prompt, max_tokens=20)
        if trad:
            trad = trad.strip().strip('"').strip("'")
            # Salva nel dizionario statico per questa sessione
            _NOME_TRAD.setdefault(lang, {})[nome] = trad
            return trad
    except Exception:
        pass
    return nome


@app.route("/admin/seed-sicurezza", methods=["POST"])
def admin_seed_sicurezza():
    """Esegue i seed di sicurezza alimentare nel DB Postgres."""
    secret = request.headers.get("X-Admin-Secret","")
    if secret != os.environ.get("ADMIN_SECRET",""):
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




@app.route("/trust")
@app.route("/trust-center")
def trust_center():
    lang = request.args.get("lang","it")
    if lang == "en":
        titolo = "Trust Center"
        corpo = """<h2>Trust Center</h2>
<p>Matter Lab is built on transparency. This page explains who we are, what data we collect, which AI systems we use, and how we protect your information.</p>

<h3>Who we are</h3>
<p>Matter Lab is an educational tool for F&B professionals developed by Michele Lamorte, Naples, Italy. P.IVA: pending registration.</p>

<h3>AI systems used</h3>
<ul>
<li><strong>Claude Sonnet (Anthropic)</strong> — main chat responses</li>
<li><strong>Claude Haiku (Anthropic)</strong> — quiz generation, fast tasks</li>
<li><strong>Whisper (OpenAI)</strong> — voice transcription (Pro only)</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — image analysis (Pro only)</li>
<li><strong>Mistral Small</strong> — fallback for fast tasks</li>
<li><strong>OpenAI Embeddings</strong> — semantic search in flavor network</li>
</ul>

<h3>Data we collect</h3>
<ul>
<li>Email address — for authentication only</li>
<li>Questions asked in chat — stored anonymously to improve the service</li>
<li>Notebook entries — saved by the user, visible only to the user</li>
<li>Usage data — chat count, trial status</li>
</ul>

<h3>Data we do NOT collect</h3>
<ul>
<li>Payment data (handled by Stripe, not stored by us)</li>
<li>Location data</li>
<li>Device fingerprinting</li>
<li>Advertising tracking</li>
</ul>

<h3>Data retention</h3>
<p>Account data is retained until you delete your account. Anonymous question logs are retained for 12 months. You can request deletion at any time: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>

<h3>AI response disclaimer</h3>
<p>Matter Lab AI responses are generated by language models and may contain errors. They do not replace advice from qualified food technologists or HACCP consultants. Shelf life values are indicative estimates only.</p>

<h3>Sub-processors (GDPR Art. 28)</h3>
<p>Matter Lab uses the following third-party AI providers as sub-processors. Each has an active Data Processing Agreement (DPA) automatically incorporated into their commercial terms of service.</p>
<ul>
<li><strong>Anthropic PBC</strong> (San Francisco, USA) — Claude Sonnet, Claude Haiku. DPA: <a href="https://www.anthropic.com/legal/data-processing-addendum" target="_blank">anthropic.com/legal/dpa</a></li>
<li><strong>OpenAI OpCo LLC</strong> (San Francisco, USA) — Whisper STT, GPT-4o Vision, text-embedding-3-small. DPA: <a href="https://openai.com/policies/data-processing-addendum/" target="_blank">openai.com/policies/dpa</a></li>
<li><strong>Mistral AI SAS</strong> (Paris, France) — Mistral Small fallback. DPA: <a href="https://legal.mistral.ai/terms/data-processing-addendum" target="_blank">legal.mistral.ai/dpa</a></li>
<li><strong>Railway Corp</strong> (San Francisco, USA) — hosting and database infrastructure.</li>
<li><strong>Resend Inc</strong> (San Francisco, USA) — transactional email (verification, password reset).</li>
</ul>
<p>Data processed by these sub-processors consists only of: anonymised chat questions and AI responses. No personal identifiers (email, name) are sent to AI providers.</p>

<h3>Contact</h3>
<p>For privacy, data, or AI-related questions: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>"""
    elif lang == "es":
        titolo = "Centro de Confianza"
        corpo = """<h2>Centro de Confianza</h2>
<p>Matter Lab se construye sobre la transparencia. Esta página explica quiénes somos, qué datos recopilamos, qué sistemas de IA utilizamos y cómo protegemos tu información.</p>

<h3>Quiénes somos</h3>
<p>Matter Lab es una herramienta educativa para profesionales F&B desarrollada por Michele Lamorte, Nápoles, Italia.</p>

<h3>Sistemas de IA utilizados</h3>
<ul>
<li><strong>Claude Sonnet (Anthropic)</strong> — respuestas del chat principal</li>
<li><strong>Claude Haiku (Anthropic)</strong> — generación de quiz, tareas rápidas</li>
<li><strong>Whisper (OpenAI)</strong> — transcripción de voz (solo Pro)</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — análisis de imágenes (solo Pro)</li>
<li><strong>Mistral Small</strong> — fallback para tareas rápidas</li>
<li><strong>OpenAI Embeddings</strong> — búsqueda semántica en la red de sabores</li>
</ul>

<h3>Datos que recopilamos</h3>
<ul>
<li>Dirección de email — solo para autenticación</li>
<li>Preguntas del chat — almacenadas anónimamente para mejorar el servicio</li>
<li>Entradas del cuaderno — guardadas por el usuario, visibles solo para el usuario</li>
<li>Datos de uso — contador de chats, estado del trial</li>
</ul>

<h3>Sub-procesadores (RGPD Art. 28)</h3>
<p>Matter Lab utiliza los siguientes proveedores de IA como sub-procesadores. Cada uno tiene un Acuerdo de Procesamiento de Datos (DPA) activo incorporado en sus términos comerciales de servicio.</p>
<ul>
<li><strong>Anthropic PBC</strong> (San Francisco, EE.UU.) — Claude Sonnet, Claude Haiku. DPA: <a href="https://www.anthropic.com/legal/data-processing-addendum" target="_blank">anthropic.com/legal/dpa</a></li>
<li><strong>OpenAI OpCo LLC</strong> (San Francisco, EE.UU.) — Whisper STT, GPT-4o Vision, text-embedding-3-small. DPA: <a href="https://openai.com/policies/data-processing-addendum/" target="_blank">openai.com/policies/dpa</a></li>
<li><strong>Mistral AI SAS</strong> (París, Francia) — Mistral Small fallback. DPA: <a href="https://legal.mistral.ai/terms/data-processing-addendum" target="_blank">legal.mistral.ai/dpa</a></li>
<li><strong>Railway Corp</strong> (San Francisco, EE.UU.) — hosting e infraestructura de base de datos.</li>
<li><strong>Resend Inc</strong> (San Francisco, EE.UU.) — email transaccional (verificación, recuperación de contraseña).</li>
</ul>
<p>Los datos procesados por estos sub-procesadores consisten únicamente en: preguntas de chat anonimizadas y respuestas de IA. Ningún identificador personal (email, nombre) se envía a los proveedores de IA.</p>

<h3>Contacto</h3>
<p>Para preguntas sobre privacidad o IA: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>"""
    else:
        titolo = "Trust Center"
        corpo = """<h2>Trust Center</h2>
<p>Matter Lab è costruito sulla trasparenza. Questa pagina spiega chi siamo, quali dati raccogliamo, quali sistemi AI utilizziamo e come proteggiamo le tue informazioni.</p>

<h3>Chi siamo</h3>
<p>Matter Lab è uno strumento educativo per professionisti F&B sviluppato da Michele Lamorte, Napoli, Italia. P.IVA: in fase di registrazione.</p>

<h3>Sistemi AI utilizzati</h3>
<ul>
<li><strong>Claude Sonnet (Anthropic)</strong> — risposte chat principali</li>
<li><strong>Claude Haiku (Anthropic)</strong> — generazione quiz, task veloci</li>
<li><strong>Whisper (OpenAI)</strong> — trascrizione vocale (solo Pro)</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — analisi foto schede tecniche (solo Pro)</li>
<li><strong>Mistral Small</strong> — fallback per task veloci</li>
<li><strong>OpenAI Embeddings</strong> — ricerca semantica nel flavor network</li>
</ul>

<h3>Dati che raccogliamo</h3>
<ul>
<li>Indirizzo email — solo per autenticazione</li>
<li>Domande poste in chat — conservate in forma anonima per migliorare il servizio</li>
<li>Voci del Quaderno — salvate dall'utente, visibili solo all'utente</li>
<li>Dati di utilizzo — contatore chat, stato trial</li>
</ul>

<h3>Dati che NON raccogliamo</h3>
<ul>
<li>Dati di pagamento (gestiti da Stripe, non conservati da noi)</li>
<li>Dati di geolocalizzazione</li>
<li>Device fingerprinting</li>
<li>Tracking pubblicitario</li>
</ul>

<h3>Conservazione dati</h3>
<p>I dati dell'account vengono conservati fino alla cancellazione. I log anonimi delle domande vengono conservati per 12 mesi. Puoi richiedere la cancellazione in qualsiasi momento: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>

<h3>Disclaimer risposte AI</h3>
<p>Le risposte AI di Matter Lab sono generate da modelli linguistici e possono contenere errori. Non sostituiscono il parere di tecnici alimentari o consulenti HACCP qualificati. I valori di shelf life sono stime orientative.</p>

<h3>Sub-responsabili del trattamento (GDPR Art. 28)</h3>
<p>Matter Lab si avvale dei seguenti fornitori AI come sub-responsabili del trattamento. Ciascuno dispone di un Data Processing Agreement (DPA) attivo, automaticamente incorporato nei propri termini commerciali di servizio.</p>
<ul>
<li><strong>Anthropic PBC</strong> (San Francisco, USA) — Claude Sonnet, Claude Haiku. DPA: <a href="https://www.anthropic.com/legal/data-processing-addendum" target="_blank">anthropic.com/legal/dpa</a></li>
<li><strong>OpenAI OpCo LLC</strong> (San Francisco, USA) — Whisper STT, GPT-4o Vision, text-embedding-3-small. DPA: <a href="https://openai.com/policies/data-processing-addendum/" target="_blank">openai.com/policies/dpa</a></li>
<li><strong>Mistral AI SAS</strong> (Parigi, Francia) — Mistral Small fallback. DPA: <a href="https://legal.mistral.ai/terms/data-processing-addendum" target="_blank">legal.mistral.ai/dpa</a></li>
<li><strong>Railway Corp</strong> (San Francisco, USA) — hosting e infrastruttura database.</li>
<li><strong>Resend Inc</strong> (San Francisco, USA) — email transazionali (verifica account, reset password).</li>
</ul>
<p>I dati trasmessi a questi sub-responsabili consistono esclusivamente in: domande chat anonimizzate e risposte AI. Nessun identificatore personale (email, nome) viene inviato ai provider AI.</p>

<h3>Contatti</h3>
<p>Per domande su privacy, dati o AI: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>"""
    return _pagina_legale(titolo, corpo)


@app.route("/cookie-policy")
def cookie_policy():
    lang = request.args.get("lang","it")
    if lang == "en":
        titolo = "Cookie Policy"
        corpo = """<h2>Cookie Policy</h2>
<p>Matter Lab uses only technical cookies necessary for the service to function. No profiling or advertising cookies are used.</p>
<h3>Cookies used</h3>
<ul>
<li><strong>matter_token</strong> — authentication token, stored in localStorage. Duration: session.</li>
<li><strong>ml_lang</strong> — language preference. Duration: persistent.</li>
<li><strong>matter_disc</strong> — selected discipline. Duration: persistent.</li>
</ul>
<p>No third-party cookies. No data shared with advertising platforms.</p>
<p>For information: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>"""
    elif lang == "es":
        titolo = "Política de Cookies"
        corpo = """<h2>Política de Cookies</h2>
<p>Matter Lab utiliza únicamente cookies técnicas necesarias para el funcionamiento del servicio. No se utilizan cookies de perfilado ni publicitarias.</p>
<h3>Cookies utilizadas</h3>
<ul>
<li><strong>matter_token</strong> — token de autenticación, almacenado en localStorage. Duración: sesión.</li>
<li><strong>ml_lang</strong> — preferencia de idioma. Duración: persistente.</li>
<li><strong>matter_disc</strong> — disciplina seleccionada. Duración: persistente.</li>
</ul>
<p>Sin cookies de terceros. Sin datos compartidos con plataformas publicitarias.</p>"""
    else:
        titolo = "Cookie Policy"
        corpo = """<h2>Cookie Policy</h2>
<p>Matter Lab utilizza esclusivamente cookie tecnici necessari al funzionamento del servizio. Non vengono utilizzati cookie di profilazione né pubblicitari.</p>
<h3>Cookie utilizzati</h3>
<ul>
<li><strong>matter_token</strong> — token di autenticazione, memorizzato in localStorage. Durata: sessione.</li>
<li><strong>ml_lang</strong> — preferenza lingua. Durata: persistente.</li>
<li><strong>matter_disc</strong> — disciplina selezionata. Durata: persistente.</li>
</ul>
<p>Nessun cookie di terze parti. Nessun dato condiviso con piattaforme pubblicitarie.</p>
<p>Per informazioni: <a href="mailto:privacy@matterlab.app">privacy@matterlab.app</a></p>"""
    return _pagina_legale(titolo, corpo)


@app.route("/come-funziona-ai")
def come_funziona_ai():
    lang = request.args.get("lang","it")
    if lang == "es":
        titolo = "Cómo funciona la IA"
        corpo = """<h2>Cómo funciona la IA de Matter Lab</h2>
<p>Matter Lab utiliza modelos de lenguaje IA para responder tus preguntas sobre ciencia gastronómica.</p>
<h3>Modelos utilizados</h3>
<ul>
<li><strong>Claude (Anthropic)</strong> — chat principal. Responde sobre fenómenos físicos y químicos.</li>
<li><strong>Haiku (Anthropic)</strong> — generación de quiz y traducciones rápidas.</li>
<li><strong>Whisper (OpenAI)</strong> — transcripción de voz (solo Pro).</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — análisis de fotos de fichas técnicas (solo Pro).</li>
</ul>
<h3>Qué hace y no hace la IA</h3>
<ul>
<li>La IA responde basándose en el grafo de conocimiento de Matter Lab (fenómenos físicos, números objetivo).</li>
<li>La IA no reemplaza a un tecnólogo alimentario ni a un consultor HACCP.</li>
<li>Los valores de vida útil son estimaciones orientativas, no certificaciones.</li>
<li>Cada respuesta de IA incluye un aviso legal.</li>
</ul>
<h3>Tus datos</h3>
<p>Las preguntas se registran de forma anónima para mejorar el servicio. Ningún dato personal se comparte con los proveedores de IA más allá de lo necesario para generar la respuesta.</p>
<p>EU AI Act: Matter Lab es una herramienta de IA de uso general para formación profesional.</p>"""
    elif lang == "en":
        titolo = "How the AI works"
        corpo = """<h2>How Matter Lab AI works</h2>
<p>Matter Lab uses AI language models to answer your questions about food science.</p>
<h3>Models used</h3>
<ul>
<li><strong>Claude (Anthropic)</strong> — main chat. Answers questions about physical and chemical phenomena.</li>
<li><strong>Haiku (Anthropic)</strong> — quiz generation and fast translations.</li>
<li><strong>Whisper (OpenAI)</strong> — voice transcription (Pro only).</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — image analysis of technical sheets (Pro only).</li>
</ul>
<h3>What AI does and does not do</h3>
<ul>
<li>AI answers based on the Matter Lab knowledge graph (physical phenomena, target numbers, scientific principles).</li>
<li>AI does not replace a food technologist or HACCP consultant.</li>
<li>Shelf life values are indicative estimates, not certifications.</li>
<li>Every AI response includes a disclaimer.</li>
</ul>
<h3>Your data</h3>
<p>Questions are logged anonymously to improve the service. No personal data is shared with AI providers beyond what is necessary to generate the response.</p>
<p>EU AI Act: Matter Lab is a general-purpose AI tool for professional education. It does not make autonomous decisions affecting people.</p>"""
    else:
        titolo = "Come funziona l'AI"
        corpo = """<h2>Come funziona l'AI di Matter Lab</h2>
<p>Matter Lab utilizza modelli linguistici AI per rispondere alle tue domande sulla scienza degli alimenti.</p>
<h3>Modelli utilizzati</h3>
<ul>
<li><strong>Claude (Anthropic)</strong> — chat principale. Risponde alle domande sui fenomeni fisici e chimici.</li>
<li><strong>Haiku (Anthropic)</strong> — generazione quiz e traduzioni rapide.</li>
<li><strong>Whisper (OpenAI)</strong> — trascrizione vocale (solo Pro).</li>
<li><strong>GPT-4o Vision (OpenAI)</strong> — analisi foto schede tecniche (solo Pro).</li>
</ul>
<h3>Cosa fa e non fa l'AI</h3>
<ul>
<li>L'AI risponde basandosi sul grafo di conoscenza di Matter Lab (fenomeni fisici, numeri bersaglio, principi scientifici).</li>
<li>L'AI non sostituisce un tecnologo alimentare né un consulente HACCP.</li>
<li>I valori di shelf life sono stime orientative, non certificazioni.</li>
<li>Ogni risposta AI include un disclaimer.</li>
</ul>
<h3>I tuoi dati</h3>
<p>Le domande vengono registrate in forma anonima per migliorare il servizio. Nessun dato personale viene condiviso con i provider AI oltre a quanto necessario per generare la risposta.</p>
<p>EU AI Act: Matter Lab è uno strumento AI a uso generale per la formazione professionale. Non prende decisioni autonome che riguardano le persone.</p>"""
    return _pagina_legale(titolo, corpo)


def _pagina_legale(titolo, corpo):
    """Wrapper HTML per pagine legali."""
    return f"""<!DOCTYPE html>
<html lang="it"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titolo} — Matter Lab</title>
<style>
body{{font-family:sans-serif;background:#FAF6EE;color:#1A1A18;max-width:680px;margin:0 auto;padding:30px 20px}}
h1{{font-family:Georgia,serif;color:#2C6E63;font-size:22px;margin-bottom:4px}}
h2{{font-family:Georgia,serif;font-size:18px;margin-top:28px}}
h3{{font-size:14px;font-weight:600;margin-top:20px;color:#2C6E63}}
p,li{{font-size:14px;line-height:1.7;color:#3A3830}}
a{{color:#2C6E63}}
.back{{display:inline-block;margin-bottom:20px;color:#2C6E63;text-decoration:none;font-size:13px}}
</style>
</head><body>
<a href="/app" class="back">← Matter Lab</a>
<h1>Matter Lab</h1>
{corpo}
<p style="margin-top:40px;font-size:12px;color:#999">Ultimo aggiornamento: luglio 2026</p>
</body></html>"""


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
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO log_domande (tipo, domanda, esito, user_id) VALUES (%s,%s,%s,%s)",
                ("supporto", testo[:1000], "ricevuto", str(user_id) if user_id else None))
            conn.commit(); cur.close(); _release_conn(conn)
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
