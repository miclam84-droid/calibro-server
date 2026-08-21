# ============================================================
# routes/auth_routes.py — endpoint autenticazione utenti.
# Dipende da: db, auth, notifiche, utils.
# ============================================================
import os, json, secrets
from flask import Blueprint, request, jsonify

from db import _get_conn, _release_conn
from routes.stato import merge_device_su_utente
from auth import (_hash_pw, _verifica_pw, _genera_token, _utente_da_token,
                  _init_account_tables, _e_hash_legacy)
from notifiche import _invia_email_resend
from utils import _err, _check_rate_limit
from config import DATABASE_URL

bp = Blueprint("auth_routes", __name__)


@bp.route("/v1/auth/registra", methods=["POST"])
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

@bp.route("/v1/auth/verifica-email", methods=["POST"])
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
        _dev = request.headers.get("X-Device-Id","").strip()
        if _dev:
            try: merge_device_su_utente(_dev, user_id)
            except Exception: pass
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

@bp.route("/v1/auth/login", methods=["POST"])
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
        # merge stato-fenomeno dal device anonimo all'account
        _dev = request.headers.get("X-Device-Id","").strip()
        if _dev:
            try: merge_device_su_utente(_dev, user_id)
            except Exception: pass
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"token":token,"piano":piano})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/auth/reset-richiesta", methods=["POST"])
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

@bp.route("/v1/auth/reset-conferma", methods=["POST"])
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

@bp.route("/v1/auth/cancella-account", methods=["DELETE"])
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
