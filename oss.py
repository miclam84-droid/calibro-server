# ============================================================
# oss.py — osservabilità: tabella app_logs, scrittura log difensiva,
# e metriche per /admin/context (Galileo Control Panel).
# Usa gli helper di db.py (_get_conn/_release_conn). Il logging non deve
# MAI rompere l'app: ogni funzione è avvolta in try/except e fallisce in
# silenzio se il DB non è disponibile.
# ============================================================
from datetime import datetime, timezone

from db import _get_conn, _release_conn

_TABLE_PRONTA = False  # flag: crea la tabella una sola volta per processo


def _iso(ts):
    """TIMESTAMPTZ -> stringa ISO8601 con Z. Robusto se ts è None o già stringa."""
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    try:
        return ts.astimezone(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    except Exception:
        try:
            return ts.isoformat()
        except Exception:
            return str(ts)


def _ensure(conn):
    """Crea app_logs + indici se non esistono, e purga i log oltre 30 giorni.
    Idempotente. Gira una sola volta per processo grazie al flag."""
    global _TABLE_PRONTA
    if _TABLE_PRONTA:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_logs (
            id           SERIAL PRIMARY KEY,
            ts           TIMESTAMPTZ DEFAULT NOW(),
            level        VARCHAR(10),
            endpoint     VARCHAR(200),
            user_id      INTEGER,
            message      TEXT,
            stack_trace  TEXT,
            duration_ms  INTEGER
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts    ON app_logs(ts DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON app_logs(level, ts DESC)")
    cur.execute("DELETE FROM app_logs WHERE ts < NOW() - INTERVAL '30 days'")
    conn.commit()
    cur.close()
    _TABLE_PRONTA = True


def log_write(level, endpoint, user_id, message, stack, duration_ms):
    """Scrive una riga in app_logs. Non solleva mai eccezioni:
    se il DB non risponde, il log si perde ma la richiesta continua."""
    conn = None
    try:
        conn = _get_conn()
        if conn is None:
            return
        _ensure(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO app_logs (level, endpoint, user_id, message, stack_trace, duration_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (level, (endpoint or "")[:200], user_id, message, stack, duration_ms),
        )
        conn.commit()
        cur.close()
    except Exception:
        pass
    finally:
        if conn is not None:
            _release_conn(conn)


def _scalar(cur, sql):
    """Esegue una query che ritorna un singolo numero; 0 in caso di errore."""
    try:
        cur.execute(sql)
        r = cur.fetchone()
        return int(r[0]) if r and r[0] is not None else 0
    except Exception:
        return 0


def metriche():
    """Costruisce il dict del contratto /admin/context concordato con Cifra.
    Difensiva: se una query fallisce, quel campo torna a 0 / [] senza far
    fallire l'intero endpoint."""
    out = {
        "app": "matter",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "utenti_totali": 0,
        "utenti_attivi_7gg": 0,
        "nuovi_7gg": 0,
        "errori_24h": 0,
        "ultimi_errori": [],
        "endpoint_lenti": [],
        "piano_pro": 0,
        "piano_free": 0,
    }
    conn = None
    try:
        conn = _get_conn()
        if conn is None:
            return out
        _ensure(conn)
        cur = conn.cursor()

        tot = _scalar(cur, "SELECT COUNT(*) FROM utenti")
        pro = _scalar(cur, "SELECT COUNT(*) FROM utenti WHERE piano = 'pro'")
        out["utenti_totali"] = tot
        out["piano_pro"] = pro
        out["piano_free"] = max(tot - pro, 0)
        out["nuovi_7gg"] = _scalar(
            cur, "SELECT COUNT(*) FROM utenti WHERE ts > NOW() - INTERVAL '7 days'")
        out["utenti_attivi_7gg"] = _scalar(
            cur, "SELECT COUNT(DISTINCT user_id) FROM sessioni "
                 "WHERE ts > NOW() - INTERVAL '7 days'")
        out["errori_24h"] = _scalar(
            cur, "SELECT COUNT(*) FROM app_logs "
                 "WHERE level = 'ERROR' AND ts > NOW() - INTERVAL '24 hours'")

        # ultimi 10 errori
        try:
            cur.execute(
                "SELECT endpoint, message, ts FROM app_logs "
                "WHERE level = 'ERROR' ORDER BY ts DESC LIMIT 10")
            out["ultimi_errori"] = [
                {"endpoint": r[0], "message": r[1], "ts": _iso(r[2])}
                for r in cur.fetchall()
            ]
        except Exception:
            pass

        # endpoint lenti (media ms, ultime 24h)
        try:
            cur.execute(
                "SELECT endpoint, AVG(duration_ms)::int AS avg_ms FROM app_logs "
                "WHERE level = 'WARN' AND ts > NOW() - INTERVAL '24 hours' "
                "GROUP BY endpoint ORDER BY avg_ms DESC LIMIT 10")
            out["endpoint_lenti"] = [
                {"endpoint": r[0], "avg_ms": int(r[1]) if r[1] is not None else 0}
                for r in cur.fetchall()
            ]
        except Exception:
            pass

        cur.close()
    except Exception:
        pass
    finally:
        if conn is not None:
            _release_conn(conn)
    return out


def logs_recenti(level=None, ore=24, limite=100):
    """Righe di log recenti per /admin/logs (consultazione interna)."""
    conn = None
    righe = []
    try:
        conn = _get_conn()
        if conn is None:
            return righe
        _ensure(conn)
        cur = conn.cursor()
        sql = ("SELECT ts, level, endpoint, user_id, message, duration_ms FROM app_logs "
               "WHERE ts > NOW() - INTERVAL %s")
        params = [f"{int(ore)} hours"]
        if level:
            sql += " AND level = %s"
            params.append(level)
        sql += " ORDER BY ts DESC LIMIT %s"
        params.append(int(limite))
        cur.execute(sql, params)
        righe = [
            {"ts": _iso(r[0]), "level": r[1], "endpoint": r[2],
             "user_id": r[3], "message": r[4], "duration_ms": r[5]}
            for r in cur.fetchall()
        ]
        cur.close()
    except Exception:
        pass
    finally:
        if conn is not None:
            _release_conn(conn)
    return righe


def logs_summary(giorni=7):
    """Conteggio errori per endpoint negli ultimi N giorni, per /admin/logs/summary."""
    conn = None
    out = []
    try:
        conn = _get_conn()
        if conn is None:
            return out
        _ensure(conn)
        cur = conn.cursor()
        cur.execute(
            "SELECT endpoint, level, COUNT(*) AS n FROM app_logs "
            "WHERE ts > NOW() - INTERVAL %s "
            "GROUP BY endpoint, level ORDER BY n DESC LIMIT 50",
            [f"{int(giorni)} days"])
        out = [{"endpoint": r[0], "level": r[1], "count": int(r[2])}
               for r in cur.fetchall()]
        cur.close()
    except Exception:
        pass
    finally:
        if conn is not None:
            _release_conn(conn)
    return out
