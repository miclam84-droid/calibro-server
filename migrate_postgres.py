"""
Migrazione una tantum: carica schema + tutti i seed in Postgres.
Va lanciato UNA VOLTA dopo aver collegato Postgres su Railway.
Uso: python migrate_postgres.py
Richiede la variabile d'ambiente DATABASE_URL (Railway la fornisce).
"""
import os, pathlib, sys
import psycopg2

HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"

def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERRORE: DATABASE_URL non impostata. Su Railway gira questo script")
        print("dalla tab Console del servizio web, dove la variabile è già disponibile.")
        sys.exit(1)

    print(f"Connessione a Postgres...")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()

    print("Carico schema.sql...")
    schema_sql = (GRAFO / "schema.sql").read_text(encoding="utf-8")
    cur.execute(schema_sql)

    # pulizia: se rilanciato, riparte da zero (idempotente)
    print("Pulizia tabelle esistenti (per rilanci puliti)...")
    cur.execute("TRUNCATE TABLE edges, nodes CASCADE")

    seeds = sorted(GRAFO.glob("seed-*.sql"))
    print(f"Carico {len(seeds)} file seed...")
    for s in seeds:
        try:
            cur.execute(s.read_text(encoding="utf-8"))
            print(f"  OK: {s.name}")
        except Exception as e:
            print(f"  ERRORE in {s.name}: {e}")
            conn.rollback()
            sys.exit(1)

    cur.execute("SELECT count(*) FROM nodes")
    n_nodes = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM edges")
    n_edges = cur.fetchone()[0]
    print(f"\nFATTO: {n_nodes} nodi, {n_edges} archi caricati in Postgres.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
