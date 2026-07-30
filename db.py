# ============================================================
# db.py — layer dati: compatibilita Postgres/SQLite, connection pool,
# caricamento grafo, helper _dati.
# ============================================================
import sqlite3
import json

from config import DATABASE_URL, GRAFO


class _PgRow(dict):
    """Riga Postgres accessibile come dizionario."""
    pass


class _PgCompat:
    """Avvolge una connessione Postgres per farla sembrare sqlite3."""

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


_pg_conn = None
_pg_pool = None

def _get_pool():
    global _pg_pool
    if _pg_pool is None and DATABASE_URL:
        from psycopg2 import pool as _pgpool
        _pg_pool = _pgpool.ThreadedConnectionPool(1, 5, DATABASE_URL)
    return _pg_pool

def _get_conn():
    """Prende una connessione dal pool."""
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


def _connetti_postgres():
    global _pg_conn
    import psycopg2
    if _pg_conn is None or _pg_conn.closed:
        _pg_conn = psycopg2.connect(DATABASE_URL)
    return _PgCompat(_pg_conn)


def carica_grafo():
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
    if campo is None:
        return {}
    if isinstance(campo, dict):
        return campo
    return json.loads(campo or "{}")
