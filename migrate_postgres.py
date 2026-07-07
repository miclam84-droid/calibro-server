"""
Migrazione: carica schema + tutti i seed in Postgres.
Uso: python migrate_postgres.py
Richiede DATABASE_URL (Railway la fornisce automaticamente).

Versione robusta: termina le connessioni attive prima del TRUNCATE
per non bloccarsi mai, anche con l'app Flask live.
"""
import os, pathlib, sys, subprocess
import psycopg2

HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"

def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERRORE: DATABASE_URL non impostata.")
        sys.exit(1)

    print("Connessione a Postgres...")
    conn = psycopg2.connect(url)
    conn.autocommit = True          # serve per i comandi admin che seguono
    cur = conn.cursor()

    # ── 1. Termina le altre connessioni attive sul DB ──────────────
    # Flask tiene una connessione persistente aperta — questo la chiude
    # senza dover fermare il servizio web.
    print("Termino le connessioni attive sul database...")
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND pid <> pg_backend_pid()
          AND state IS NOT NULL
    """)
    terminated = cur.fetchall()
    print(f"  Connessioni terminate: {len(terminated)}")

    # ── 2. Ora riapri in modalità transazione normale ──────────────
    conn.autocommit = False
    cur.close()
    conn.close()

    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # timeout di sicurezza: se qualcosa si blocca oltre 30s, fallisce
    cur.execute("SET statement_timeout = '30s'")

    # ── 3. Schema ──────────────────────────────────────────────────
    print("Carico schema.sql...")
    schema_sql = (GRAFO / "schema.sql").read_text(encoding="utf-8")
    cur.execute(schema_sql)

    # ── 3b. Cache traduzioni (persistente, NON viene mai truncata) ──
    # Le schede EN vivono qui: il TRUNCATE svuota nodes/edges ma non
    # questa tabella, cosi l'inglese non sparisce piu a ogni reseed.
    print("Preparo la cache traduzioni...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS traduzioni (
            it_text TEXT PRIMARY KEY,
            en_text TEXT
        )
    """)
    # Raccolgo l'inglese GIA presente nei nodi (formato {it,en}) nella cache,
    # PRIMA di svuotare: quello che translate-graph ha gia tradotto viene
    # catturato qui una volta per tutte.
    cur.execute("""
        INSERT INTO traduzioni (it_text, en_text)
        SELECT data->'scheda'->>'it', data->'scheda'->>'en'
        FROM nodes
        WHERE jsonb_typeof(data->'scheda') = 'object'
          AND data->'scheda'->>'en' IS NOT NULL
          AND data->'scheda'->>'it' IS NOT NULL
        ON CONFLICT (it_text) DO UPDATE SET en_text = EXCLUDED.en_text
    """)
    print(f"  Traduzioni raccolte in cache: {cur.rowcount}")

    # ── 4. Pulizia ─────────────────────────────────────────────────
    print("Pulizia tabelle grafo (nodes + edges)...")
    cur.execute("TRUNCATE TABLE edges, nodes CASCADE")

    # ── 5. Vincoli differibili ────────────────────────────────────
    print("Rendo i vincoli differibili...")
    cur.execute("ALTER TABLE edges ALTER CONSTRAINT edges_from_id_fkey DEFERRABLE INITIALLY DEFERRED")
    cur.execute("ALTER TABLE edges ALTER CONSTRAINT edges_to_id_fkey DEFERRABLE INITIALLY DEFERRED")

    # ── 6. Seed ────────────────────────────────────────────────────
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

    # ── 6b. Riapplica l'inglese dalla cache ────────────────────────
    # Ogni scheda-stringa italiana per cui esiste una traduzione in cache
    # torna bilingue {it,en} SENZA chiamare Haiku. L'inglese non si perde.
    print("Riapplico le traduzioni EN dalla cache...")
    cur.execute("""
        UPDATE nodes n
        SET data = jsonb_set(
                n.data, '{scheda}',
                jsonb_build_object('it', n.data->'scheda', 'en', to_jsonb(t.en_text))
            )
        FROM traduzioni t
        WHERE jsonb_typeof(n.data->'scheda') = 'string'
          AND (n.data->>'scheda') = t.it_text
          AND t.en_text IS NOT NULL
    """)
    print(f"  Schede tornate bilingui: {cur.rowcount}")

    # ── 7. Commit e verifica integrità ─────────────────────────────
    print("Verifico l'integrità finale del grafo (commit)...")
    try:
        conn.commit()
    except Exception as e:
        print(f"ERRORE DI INTEGRITÀ: {e}")
        conn.rollback()
        sys.exit(1)

    cur.execute("SELECT count(*) FROM nodes")
    n_nodes = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM edges")
    n_edges = cur.fetchone()[0]
    print(f"\nFATTO: {n_nodes} nodi, {n_edges} archi caricati in Postgres.")

    cur.close()
    conn.close()

    # ── 8. Ripristino import esterni (USDA + PubChem) ──────────────
    # Questi dati NON stanno nei seed (si caricano via API), quindi il
    # TRUNCATE li cancellerebbe a ogni reseed. Rilanciandoli qui in
    # automatico, sopravvivono a ogni migrate senza doverli ricordare.
    print("\nRipristino import esterni (USDA + PubChem)...")
    for nome, cmd in (("USDA", ["flask", "import-usda"]),
                      ("PubChem", ["flask", "import-pubchem"])):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            ultima = (r.stdout.strip().splitlines() or ["(nessun output)"])[-1]
            print(f"  {nome}: {ultima}")
        except Exception as e:
            print(f"  {nome} NON ripristinato ({e}). Rilancia a mano: {' '.join(cmd)}")


if __name__ == "__main__":
    main()
