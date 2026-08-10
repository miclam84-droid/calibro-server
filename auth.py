# ============================================================
# auth.py — account: tabelle utenti/sessioni, hashing e verifica password,
# token di sessione. Estratto da app.py senza modifiche di comportamento.
# ============================================================
import os
from flask import request

from config import DATABASE_URL
from db import _get_conn, _release_conn


def _admin_autenticato():
    """True se la request porta un ADMIN_SECRET valido (header o query param ?s=).
    Confronto timing-safe (hmac.compare_digest) per non esporre il segreto via timing."""
    import hmac
    atteso = os.environ.get("ADMIN_SECRET") or ""
    secret = request.headers.get("X-Admin-Secret", "") or request.args.get("s", "")
    return bool(atteso) and hmac.compare_digest(str(secret), str(atteso))


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
