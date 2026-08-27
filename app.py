# ============================================================
# MATTER — server. Riceve una domanda, naviga il grafo in
# profondita (risale ai fenomeni), costruisce un contesto ricco,
# e chiede a Mistral di rispondere SENZA inventare.
# Flask + grafo (Postgres su Railway / SQLite in locale) + Mistral via HTTP.
# ============================================================
import os, json, sqlite3, pathlib, difflib, uuid
from flask import Flask, request, jsonify, render_template
import motore as Motore

# ── Sentry (monitoraggio errori) — init PRIMA di tutto il resto ──
# Il DSN sta in variabile d'ambiente SENTRY_DSN (impostata su Railway).
# Se manca (es. in locale), Sentry non parte e l'app funziona comunque.
try:
    _sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
    if _sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            # traces_sample_rate basso: campiona il 10% delle richieste per le performance,
            # cattura il 100% degli ERRORI. Tiene basso il volume (e i costi) su Sentry.
            traces_sample_rate=0.1,
            send_default_pii=False,  # GDPR: niente dati personali negli errori
            environment=os.environ.get("RAILWAY_ENVIRONMENT", "production"),
        )
except Exception:
    pass  # Sentry non deve mai impedire l'avvio dell'app

# ── Fondazione ──────────────────────────────────────────
from config import HERE, GRAFO, DATABASE_URL
from db import (_PgRow, _PgCompat, _PgCursorResult, _get_pool, _get_conn,
                _release_conn, _connetti_postgres, carica_grafo, _dati)
from auth import (_init_account_tables, _hash_pw, _e_hash_legacy, _verifica_pw,
                  _genera_token, _utente_da_token, _admin_autenticato)
from contenuto import (_pulisci_traduzione, _scheda_lang, _numero_bersaglio, _corregge_it)
from notifiche import _invia_email_resend
from ai import (_scheda_tradotta, _intro, _domanda_chiede_perche, cerca_contesto,
               costruisci_prompt, _mistral_raw, estrai_entita, _anthropic_raw,
               _haiku_raw, chiedi_mistral, cerca_fuzzy, fenomeni_suggeriti,
               log_evento, _genera_quiz, _traduci_nome)
from cifra_utils import _auth_cifra, _stima_costo_categoria, _calcola_profilo_sicurezza
from utils import (_err, _check_rate_limit, _rate_store, _RATE_LIMIT, _RATE_WINDOW,
                   _profilo_default, _aggiorna_profilo)

# ── Fondazione estratta (config/db/auth) ──
from config import HERE, GRAFO, DATABASE_URL
from db import (_PgRow, _PgCompat, _PgCursorResult, _get_pool, _get_conn,
                _release_conn, _connetti_postgres, carica_grafo, _dati)
from auth import (_init_account_tables, _hash_pw, _e_hash_legacy, _verifica_pw,
                  _genera_token, _utente_da_token)

app = Flask(__name__)

# ── Rotta di test Sentry: genera un errore apposta per verificare che Sentry lo catturi.
#    Protetta da admin secret (nessun utente la trova). Uso: /admin/test-sentry?s=SECRET
@app.route("/admin/test-sentry")
def _test_sentry():
    if request.args.get("s", "") != os.environ.get("ADMIN_SECRET", ""):
        return "Forbidden", 403
    _ = 1 / 0  # errore volontario → deve comparire su Sentry
    return "non arriva mai qui"

# ── JSON provider globale: converte i Decimal di Postgres in float ──────────
# Risolve alla radice il problema "Object of type Decimal is not JSON
# serializable" per OGNI endpoint (es. /v1/admin/stats), senza dover
# sanitizzare a mano in ogni funzione.
from decimal import Decimal as _Decimal
try:
    from flask.json.provider import DefaultJSONProvider
    class _DecimalJSONProvider(DefaultJSONProvider):
        @staticmethod
        def default(o):
            if isinstance(o, _Decimal):
                return float(o)
            return DefaultJSONProvider.default(o)
    app.json = _DecimalJSONProvider(app)
except Exception:
    # fallback per versioni Flask più vecchie
    import json as _stdjson
    class _DecEncoder(_stdjson.JSONEncoder):
        def default(self, o):
            if isinstance(o, _Decimal):
                return float(o)
            return super().default(o)
    app.json_encoder = _DecEncoder

# ── Blueprint ───────────────────────────────────────────
from routes.pwa import bp as pwa_bp; app.register_blueprint(pwa_bp)
from routes.admin_panel import bp as admin_panel_bp; app.register_blueprint(admin_panel_bp)
from routes.legal import bp as legal_bp; app.register_blueprint(legal_bp)
from routes.admin import bp as admin_bp; app.register_blueprint(admin_bp)
from routes.auth_routes import bp as auth_routes_bp; app.register_blueprint(auth_routes_bp)
from routes.api import bp as api_bp; app.register_blueprint(api_bp)
from routes.lezione import bp as lezione_bp; app.register_blueprint(lezione_bp)
from routes.chat import bp as chat_bp; app.register_blueprint(chat_bp)
from routes.cifra import bp as cifra_bp; app.register_blueprint(cifra_bp)
from routes.misc import bp as misc_bp; app.register_blueprint(misc_bp)
from routes.mie_cose import bp_mie as mie_cose_bp; app.register_blueprint(mie_cose_bp)
from routes.community import bp_community; app.register_blueprint(bp_community)
from routes.menu_builder import bp_menu as menu_builder_bp; app.register_blueprint(menu_builder_bp)
from routes.stato import bp as stato_bp; app.register_blueprint(stato_bp)

# ── OSS hooks ───────────────────────────────────────────
import time as _time, traceback as _traceback
import oss

@app.before_request
def _oss_start():
    request._t0 = _time.time()

@app.after_request
def _oss_after(resp):
    try:
        dur=int((_time.time()-getattr(request,'_t0',_time.time()))*1000)
        if resp.status_code>=500: oss.log_write('ERROR',request.path,None,f'HTTP {resp.status_code}',None,dur)
        elif dur>2000: oss.log_write('WARN',request.path,None,f'lento {dur}ms',None,dur)
    except Exception: pass
    # CORS ristretto: solo origini fidate (il dominio di produzione + sviluppo locale).
    # Le richieste same-origin dalla PWA non passano di qui; questo blocca solo
    # i siti terzi che tentano di consumare gli endpoint AI dal browser di un utente.
    try:
        if request.path.startswith('/v1/'):
            origin = request.headers.get('Origin', '')
            _allow = {
                'https://web-production-79457.up.railway.app',
                'https://matterlab.app', 'https://www.matterlab.app',
                'http://localhost:5001', 'http://127.0.0.1:5001',
            }
            if origin in _allow:
                resp.headers['Access-Control-Allow-Origin'] = origin
                resp.headers['Vary'] = 'Origin'
                resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Admin-Secret'
    except Exception: pass
    return resp

@app.teardown_request
def _oss_teardown(exc):
    if exc is not None:
        try:
            dur=int((_time.time()-getattr(request,'_t0',_time.time()))*1000)
            oss.log_write('ERROR',getattr(request,'path','?'),None,str(exc),_traceback.format_exc(),dur)
        except Exception: pass


# ── Blueprint route ──────────────────────────────────────

# ── Osservabilità: logging errori/lentezze + hook richieste ──
import time as _time, traceback as _traceback
import oss

@app.before_request
def _oss_start():
    request._t0 = _time.time()

@app.after_request
def _oss_after(resp):
    # logga risposte gestite con 5xx o richieste lente (>2s). Mai bloccante.
    try:
        dur = int((_time.time() - getattr(request, "_t0", _time.time())) * 1000)
        if resp.status_code >= 500:
            oss.log_write("ERROR", request.path, None, f"HTTP {resp.status_code}", None, dur)
        elif dur > 2000:
            oss.log_write("WARN", request.path, None, f"lento {dur}ms", None, dur)
    except Exception:
        pass
    return resp

@app.teardown_request
def _oss_teardown(exc):
    # cattura le eccezioni non gestite (after_request non gira in quel caso).
    if exc is not None:
        try:
            dur = int((_time.time() - getattr(request, "_t0", _time.time())) * 1000)
            oss.log_write("ERROR", getattr(request, "path", "?"), None,
                          str(exc), _traceback.format_exc(), dur)
        except Exception:
            pass


@app.errorhandler(500)
@app.errorhandler(Exception)
def _handle_uncaught(e):
    """Handler globale: qualsiasi eccezione non gestita non restituisce più
    uno stack trace crudo, ma una risposta pulita. JSON per le API, testo per il resto.
    L'eccezione è già loggata da teardown_request."""
    from werkzeug.exceptions import HTTPException
    # lascio passare i 4xx voluti (404, 403, 400...) senza trasformarli
    if isinstance(e, HTTPException) and e.code and e.code < 500:
        return e
    # registro l'eccezione su Sentry PRIMA di restituire la risposta pulita.
    # (l'handler cattura tutto, quindi senza questo Sentry non vedrebbe l'errore)
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except Exception:
        pass
    try:
        p = request.path or ""
    except Exception:
        p = ""
    if p.startswith("/v1/") or p in ("/chiedi", "/calcola", "/nodo") or p.startswith("/api/"):
        return jsonify({"errore": "Si è verificato un problema temporaneo. Riprova tra poco."}), 500
    return "Si è verificato un problema temporaneo. Riprova tra poco.", 500


# ── Correzione ortografica deterministica schede (accenti + apostrofi) ──




















# ---- ricerca contesto: profonda, centrata sui fenomeni ----



# ---- costruisce il prompt -----------------------------------
_STOPWORD = {"quanto","costa","tempo","oggi","sempre","abbastanza","molto","poco",
             "questo","quella","quello","perche","perché","dopo","prima","viene",
             "fanno","fatto","faccio","vorrei","volevo","sento","vedo","sono",
             "della","dello","delle","degli","quando","dove","come","cosa"}






# ---- Mistral via HTTP diretto (nessun SDK) ------------------


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




























import os as _os









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



# ── SSO DEEP LINK — Token generator per Cifra ─────────────────








# ── CANCELLAZIONE ACCOUNT GDPR (AC7) ─────────────────────────────



# ---- endpoint -----------------------------------------------
# ── FLAVOR NETWORK (FL3-FL4) ─────────────────────────────────────






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














import random, time

# cache semplice per il fenomeno del giorno (ruota ogni 24h)
_cache_home = {}  # { lang: {"ts": float, "data": dict} }





_lezione_cache = {}  # cache fenomeni per disciplina {nome: [fenomeni]}
















# ── STRIPE PAGAMENTI (GT8) ────────────────────────────────────────








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


































if __name__ == "__main__":
    # debug solo se esplicitamente richiesto in locale (mai in produzione).
    _debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=_debug, port=5001)
