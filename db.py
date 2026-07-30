# ============================================================
# db.py — layer dati: compatibilita Postgres/SQLite, connection pool,
# caricamento grafo, helper _dati.
# ============================================================
import sqlite3
import json

from config import DATABASE_URL, GRAFO


class _PgRow(dict):
    """Riga Postgres accessibile come dizionario, per compatibilita con sqlite3.Row."""
    pass


class _PgCompat:
    """Avvolge il POOL Postgres per farla sembrare sqlite3.
    Ogni execute() prende una connessione dal pool, esegue, e la rilascia.
    Thread-safe: nessuna connessione globale condivisa tra richieste.
    Le route non cambiano nulla — usano db.execute() identico a prima.
    """

    def execute(self, sql, params=()):
        p = _get_pool()
        if not p:
            raise RuntimeError("Postgres pool non disponibile")
        conn = None
        try:
            conn = p.getconn()
            if conn is None:
                raise RuntimeError("Pool esaurito")
            cur = conn.cursor()
            cur.execute(sql.replace("?", "%s"), params)
            if cur.description:
                cols = [d[0] for d in cur.description]
                rows = [_PgRow(zip(cols, r)) for r in cur.fetchall()]
                cur.close()
                return _PgCursorResult(rows)
            conn.commit()
            cur.close()
            return _PgCursorResult([])
        except Exception:
            if conn:
                try: conn.rollback()
                except Exception: pass
            raise
        finally:
            if conn:
                try: p.putconn(conn)
                except Exception: pass


class _PgCursorResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


# ── CONNECTION POOL Postgres ─────────────────────────────
_pg_pool = None

def _get_pool():
    global _pg_pool
    if _pg_pool is None and DATABASE_URL:
        from psycopg2 import pool as _pgpool
        # max 8 connessioni — con _PgCompat che rilascia subito dopo ogni execute,
        # non c'è più la connessione globale persistente. Possiamo salire da 5 a 8
        # perché il ciclo vita è brevissimo (acquire → execute → release).
        _pg_pool = _pgpool.ThreadedConnectionPool(2, 8, DATABASE_URL)
    return _pg_pool

def _get_conn():
    """Prende una connessione dal pool. Usare con try/finally + _release_conn."""
    p = _get_pool()
    if p:
        try:
            return p.getconn()
        except Exception:
            return None
    return None

def _release_conn(conn):
    """Rilascia la connessione al pool."""
    p = _get_pool()
    if p and conn:
        try:
            p.putconn(conn)
        except Exception:
            pass


def carica_grafo():
    """Su Railway (DATABASE_URL impostata): restituisce un _PgCompat che usa il pool.
    Ogni execute() prende e rilascia una connessione — thread-safe.
    In locale: SQLite in memoria dai seed."""
    if DATABASE_URL:
        return _PgCompat()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    schema = (GRAFO/"schema.sql").read_text(encoding="utf-8").replace("JSONB","TEXT")
    db.executescript(schema)
    for s in sorted(GRAFO.glob("seed-*.sql")):
        db.executescript(s.read_text(encoding="utf-8"))
    return db


def _dati(campo):
    """Il campo 'data' arriva come stringa JSON da SQLite, ma già come
    dict da Postgres (JSONB). Gestisce entrambi i casi."""
    if campo is None:
        return {}
    if isinstance(campo, dict):
        return campo
    return json.loads(campo or "{}")
