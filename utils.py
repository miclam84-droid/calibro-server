# ============================================================
# utils.py — piccoli helper trasversali: messaggi di errore localizzati,
# rate limiting per IP. Usati da auth-routes, lezione, chat.
# ============================================================
import time as _time


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

def _trial_consentito(user_id, ip, tipo="varie", limite=5):
    """Gate a PUNTI (struttura OpenAI).
    FREE: 5 assaggi chat TOTALI (non a tempo). Foto/voce mai (sono solo-Pro via _e_pro).
    PRO: fair use interno a punti (~budget €5/mese di costo AI), invisibile all'utente.
    Ritorna (consentito: bool, info: dict). Le funzioni gratis (atlante/mirino/calcolatori) non passano di qui.
    """
    from db import _get_conn, _release_conn
    # punti per tipo di chiamata (riflettono il costo relativo)
    PUNTI = {"chat": 1, "chat_operativa": 3, "foto": 5, "voce": 3, "diag": 1, "varie": 1}
    punti_uso = PUNTI.get(tipo, 1)
    FREE_ASSAGGI = 5        # assaggi chat totali per il free
    PRO_PUNTI_MESE = 300   # fair use Pro: ~budget interno mensile
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS trial_uso (
            id SERIAL PRIMARY KEY, user_id TEXT, ip TEXT, tipo TEXT,
            costo_cent REAL DEFAULT 1.0, punti INTEGER DEFAULT 1, ts TIMESTAMPTZ DEFAULT NOW())""")
        cur.execute("ALTER TABLE trial_uso ADD COLUMN IF NOT EXISTS punti INTEGER DEFAULT 1")
        conn.commit()
        piano = "free"
        if user_id:
            cur.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
            r = cur.fetchone()
            piano = (r[0] if r else "free") or "free"

        if piano == "pro":
            # PRO: fair use a punti sugli ultimi 30 giorni
            if user_id:
                cur.execute("SELECT COALESCE(SUM(punti),0) FROM trial_uso WHERE user_id=%s AND ts > NOW() - INTERVAL '30 days'", (user_id,))
                usati = int(cur.fetchone()[0] or 0)
                if usati + punti_uso > PRO_PUNTI_MESE:
                    cur.close(); _release_conn(conn)
                    return False, {"pro": True, "fair_use": True, "punti_usati": usati}
                cur.execute("INSERT INTO trial_uso (user_id, ip, tipo, punti) VALUES (%s,%s,%s,%s)", (user_id, ip, tipo, punti_uso))
                conn.commit()
            cur.close(); _release_conn(conn)
            return True, {"pro": True}

        # FREE: solo la chat ha assaggi; foto/voce sono bloccate altrove (_e_pro)
        # conto gli assaggi chat totali (senza finestra temporale: 5 e basta)
        if user_id:
            cur.execute("SELECT COUNT(*) FROM trial_uso WHERE user_id=%s AND tipo IN ('chat','chat_operativa','varie')", (user_id,))
        else:
            cur.execute("SELECT COUNT(*) FROM trial_uso WHERE ip=%s AND tipo IN ('chat','chat_operativa','varie')", (ip,))
        n = int(cur.fetchone()[0] or 0)
        if n >= FREE_ASSAGGI:
            cur.close(); _release_conn(conn)
            return False, {"assaggi_finiti": True, "usati": n, "totali": FREE_ASSAGGI}
        cur.execute("INSERT INTO trial_uso (user_id, ip, tipo, punti) VALUES (%s,%s,%s,%s)", (user_id, ip, tipo, punti_uso))
        conn.commit(); cur.close(); _release_conn(conn)
        return True, {"assaggio": True, "usati": n + 1, "rimasti": max(0, FREE_ASSAGGI - n - 1)}
    except Exception as e:
        print(f"[GATE] errore: {e}", flush=True)
        try:
            conn.rollback(); _release_conn(conn)
        except Exception:
            pass
        return True, {"errore_check": True}


def _e_pro(user_id):
    """True solo se l'utente è Pro. Per feature riservate agli abbonati (foto, voce)."""
    if not user_id:
        return False
    from db import _get_conn, _release_conn
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
        r = cur.fetchone()
        cur.close(); _release_conn(conn)
        return bool(r and r[0] == "pro")
    except Exception as e:
        print(f"[E_PRO] errore: {e}", flush=True)
        try:
            _release_conn(conn)
        except Exception:
            pass
        return False  # in dubbio, NON dà accesso (fail-closed: protegge i costi)
