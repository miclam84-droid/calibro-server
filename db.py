# ============================================================
# db.py — layer dati: compatibilita Postgres/SQLite, connection pool,
# caricamento grafo, helper _dati.
# ============================================================
import sqlite3
import json
import contextlib

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


class _PgCompatPool:
    """Versione thread-safe di _PgCompat.
    Ogni execute() prende una connessione dal pool, esegue, e la rilascia
    nel finally. Nessuna connessione globale — safe per richieste concorrenti.
    Le route usano db.execute() identico a prima — zero modifiche."""

    def execute(self, sql, params=()):
        p = _get_pool()
        if not p:
            raise RuntimeError("Pool Postgres non disponibile")
        conn = None
        import time as _time
        for attempt in range(3):
            try:
                conn = p.getconn()
                break
            except Exception:
                if attempt < 2:
                    _time.sleep(0.1 * (attempt + 1))
                    # al secondo tentativo resetta il pool
                    if attempt == 1:
                        p = _reset_pool()
                        if not p:
                            raise RuntimeError("Pool non disponibile dopo reset")
                else:
                    raise RuntimeError("Pool esaurito — riprova tra un momento")
        try:
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
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn:
                try:
                    p.putconn(conn)
                except Exception:
                    pass

def _get_pool():
    global _pg_pool
    if _pg_pool is None and DATABASE_URL:
        from psycopg2 import pool as _pgpool
        _pg_pool = _pgpool.ThreadedConnectionPool(2, 10, DATABASE_URL)
    return _pg_pool

def _reset_pool():
    """Distrugge e ricrea il pool — chiamato quando tutte le connessioni sono morte."""
    global _pg_pool
    try:
        if _pg_pool:
            _pg_pool.closeall()
    except Exception:
        pass
    _pg_pool = None
    return _get_pool()

def _get_conn():
    """Prende una connessione dal pool.
    Solleva RuntimeError se il pool è esaurito — così i try/except esistenti
    nelle route catturano l'errore invece di crashare con AttributeError su None."""
    p = _get_pool()
    if p:
        try:
            conn = p.getconn()
            if conn is None:
                raise RuntimeError("Pool esaurito")
            return conn
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Pool non disponibile: {e}") from e
    raise RuntimeError("Database non configurato")

def _release_conn(conn):
    """Rilascia la connessione al pool."""
    p = _get_pool()
    if p and conn:
        try:
            p.putconn(conn)
        except Exception:
            pass


@contextlib.contextmanager
def connessione():
    """La porta UNICA per una connessione dal pool.

    Uso:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(...)
            conn.commit()      # per le scritture

    Garantisce che la connessione torni SEMPRE nel pool, anche se dentro
    il blocco scoppia un'eccezione — elimina i leak del pattern
    'connect ... close() solo sul percorso buono'. Da preferire a
    psycopg2.connect() grezzo (che salta il pool e non è limitato).
    """
    conn = _get_conn()
    try:
        yield conn
    finally:
        # lascia la connessione pulita per il prossimo nel pool:
        # scarta eventuale transazione non committata (le scritture committano
        # esplicitamente dentro il blocco; qui è un no-op dopo un commit).
        try:
            conn.rollback()
        except Exception:
            pass
        _release_conn(conn)


def _connetti_postgres():
    global _pg_conn
    import psycopg2
    if _pg_conn is None or _pg_conn.closed:
        _pg_conn = psycopg2.connect(DATABASE_URL)
    return _PgCompat(_pg_conn)


def carica_grafo():
    """Restituisce un oggetto db compatibile con sqlite3.
    Su Postgres: _PgCompatPool — thread-safe, ogni execute prende e rilascia
    una connessione dal pool. Zero connessioni globali.
    In locale: sqlite3 in memoria dai seed."""
    if DATABASE_URL:
        return _PgCompatPool()
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    try:
        schema = (GRAFO/"schema.sql").read_text(encoding="utf-8").replace("JSONB","TEXT")
        db.executescript(schema)
        for s in sorted(GRAFO.glob("seed-*.sql")):
            try:
                db.executescript(s.read_text(encoding="utf-8"))
            except sqlite3.OperationalError:
                pass  # seed con caratteri speciali — skip in locale
    except Exception:
        pass
    return db


def _dati(campo):
    if campo is None:
        return {}
    if isinstance(campo, dict):
        return campo
    return json.loads(campo or "{}")


# DDL unico e idempotente per worker_log.
# Oggi questo CREATE TABLE IF NOT EXISTS è copiaincollato in 14+ punti
# (routes/admin.py, routes/admin_migrazioni.py). Qui c'è l'helper riutilizzabile;
# il cablaggio dei siti chiamanti è FUORI SCOPE per questa ondata (vedi PR).
_WORKER_LOG_DDL = (
    "CREATE TABLE IF NOT EXISTS worker_log "
    "(id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)"
)


def assicura_worker_log(cur):
    """Crea la tabella worker_log se non esiste (idempotente).

    Prende un cursor psycopg2 GIÀ APERTO ed esegue il DDL. NON committa:
    il commit resta responsabilità del chiamante, esattamente come nei
    siti attuali (che chiamano cur.execute(...) dentro una transazione
    e committano più avanti). Non apre connessioni né tocca il pool.

    Schema identico a quello già in uso in produzione:
        worker_log(id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW(), testo TEXT)

    Cablaggio (da fare in un'altra ondata, fuori scope qui): sostituire
        cur.execute("CREATE TABLE IF NOT EXISTS worker_log (...)")
    con
        from db import assicura_worker_log
        assicura_worker_log(cur)
    """
    cur.execute(_WORKER_LOG_DDL)
