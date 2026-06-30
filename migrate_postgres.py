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
    cur = conn.cursor()

    print("Carico schema.sql...")
    schema_sql = (GRAFO / "schema.sql").read_text(encoding="utf-8")
    cur.execute(schema_sql)

    # pulizia: se rilanciato, riparte da zero (idempotente)
    print("Pulizia tabelle esistenti (per rilanci puliti)...")
    cur.execute("TRUNCATE TABLE edges, nodes CASCADE")

    # i seed referenziano nodi definiti in ALTRI file (es. un arco in
    # 'agganci-completi' punta a un nodo definito in 'ponte-concentrazione').
    # L'ordine alfabetico dei file non garantisce che i nodi esistano prima
    # degli archi che li usano. Soluzione: rendere i vincoli DEFERRABLE e
    # controllarli solo alla fine della transazione, non riga per riga.
    print("Rendo i vincoli differibili (l'ordine dei file non conta più)...")
    cur.execute("ALTER TABLE edges ALTER CONSTRAINT edges_from_id_fkey DEFERRABLE INITIALLY DEFERRED")
    cur.execute("ALTER TABLE edges ALTER CONSTRAINT edges_to_id_fkey DEFERRABLE INITIALLY DEFERRED")

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

    # qui Postgres controlla finalmente tutti i vincoli rimasti in sospeso:
    # se un arco punta a un nodo che NON esiste da nessuna parte (typo vero,
    # non solo ordine sbagliato), l'errore esce qui, pulito e chiaro.
    print("Verifico l'integrità finale del grafo (commit)...")
    try:
        conn.commit()
    except Exception as e:
        print(f"ERRORE DI INTEGRITÀ: {e}")
        print("C'è un arco che punta a un nodo che non esiste in NESSUN seed (non è solo ordine).")
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
