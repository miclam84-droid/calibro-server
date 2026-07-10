"""
Flavor Network — Semantic Search via Embeddings
================================================
Precalcola gli embedding di tutti i nodi Ahn nel grafo
e li salva in Postgres per la ricerca semantica.

Uso:
  python3 flavor_embeddings.py --build    # precalcola e salva (eseguire una volta)
  python3 flavor_embeddings.py --test salame  # testa la ricerca

La ricerca semantica viene usata come fallback nell'endpoint /v1/abbina/<ingrediente>
quando il dizionario manuale non trova corrispondenza.
"""

import os, sys, json, time
import urllib.request
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL", "")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")
EMBED_MODEL  = "text-embedding-3-small"
EMBED_DIM    = 1536  # dimensione text-embedding-3-small


def _embed(texts):
    """Genera embedding per una lista di testi via OpenAI."""
    if not OPENAI_KEY:
        raise ValueError("OPENAI_API_KEY non configurata")
    body = json.dumps({
        "model": EMBED_MODEL,
        "input": texts,
        "encoding_format": "float"
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]


def build_embeddings():
    """
    Precalcola embedding per tutti i nodi Ahn con abbinamenti aromatici.
    Li salva in Postgres nella tabella flavor_embeddings.
    Costo stimato: ~1.500 nodi × ~5 token/nome × $0.02/MTok = $0.00015 (quasi zero)
    """
    if not DATABASE_URL:
        print("DATABASE_URL non configurata")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Crea tabella se non esiste (usa vector type di pgvector se disponibile, altrimenti JSON)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS flavor_embeddings (
            node_id     TEXT PRIMARY KEY,
            node_name   TEXT NOT NULL,
            embedding   JSONB NOT NULL,
            ts          TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.commit()

    # Recupera tutti i nodi Ahn che hanno almeno un abbinamento aromatico
    cur.execute("""
        SELECT DISTINCT e.from_id, n.name
        FROM edges e
        LEFT JOIN nodes n ON n.id = e.from_id
        WHERE e.relation = 'abbinamento_aromatico'
        ORDER BY e.from_id
    """)
    nodi = cur.fetchall()
    print(f"Nodi Ahn da embeddare: {len(nodi)}")

    # Conta quanti già esistono
    cur.execute("SELECT COUNT(*) FROM flavor_embeddings")
    gia_presenti = cur.fetchone()[0]
    print(f"Embedding già presenti: {gia_presenti}")

    # Processa in batch da 100
    BATCH = 100
    nuovi = 0
    for i in range(0, len(nodi), BATCH):
        batch = nodi[i:i+BATCH]

        # Salta se già presenti
        ids = [n[0] for n in batch]
        cur.execute(
            "SELECT node_id FROM flavor_embeddings WHERE node_id = ANY(%s)",
            (ids,)
        )
        gia = {r[0] for r in cur.fetchall()}
        da_fare = [(id, name) for id, name in batch if id not in gia]

        if not da_fare:
            print(f"  Batch {i//BATCH+1}: già tutti presenti, skip")
            continue

        # Prepara i testi da embeddare: nome pulito per la ricerca
        testi = [name.replace("_", " ").lower() if name else id.replace("ahn_","").replace("_"," ")
                 for id, name in da_fare]

        try:
            embeddings = _embed(testi)
            for (node_id, node_name), emb in zip(da_fare, embeddings):
                cur.execute("""
                    INSERT INTO flavor_embeddings (node_id, node_name, embedding)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (node_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """, (node_id, node_name or node_id, json.dumps(emb)))
            conn.commit()
            nuovi += len(da_fare)
            print(f"  Batch {i//BATCH+1}: +{len(da_fare)} embedding salvati")
            time.sleep(0.1)  # rate limit gentile
        except Exception as e:
            print(f"  Batch {i//BATCH+1} ERRORE: {e}")
            conn.rollback()

    cur.close(); conn.close()
    print(f"\nCompletato. Nuovi embedding: {nuovi}. Totale: {gia_presenti + nuovi}")


def search_by_embedding(query, top_k=5):
    """
    Cerca il nodo Ahn più vicino semanticamente alla query.
    Usa cosine similarity calcolata in Python (nessun pgvector richiesto).
    Ritorna lista di (node_id, node_name, similarity).
    """
    if not DATABASE_URL or not OPENAI_KEY:
        return []

    # Genera embedding della query
    try:
        query_emb = _embed([query.lower()])[0]
    except Exception as e:
        print(f"[EMBED SEARCH] errore embedding query: {e}")
        return []

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT node_id, node_name, embedding FROM flavor_embeddings LIMIT 2000")
    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        return []

    # Cosine similarity
    import math
    def cosine(a, b):
        dot = sum(x*y for x,y in zip(a,b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(x*x for x in b))
        return dot / (na * nb) if na * nb > 0 else 0

    scores = []
    for node_id, node_name, emb_json in rows:
        emb = emb_json if isinstance(emb_json, list) else json.loads(emb_json)
        sim = cosine(query_emb, emb)
        scores.append((node_id, node_name, sim))

    scores.sort(key=lambda x: -x[2])
    return scores[:top_k]


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_embeddings()
    elif "--test" in sys.argv:
        idx = sys.argv.index("--test")
        query = sys.argv[idx+1] if idx+1 < len(sys.argv) else "salame"
        print(f"\nRicerca semantica: '{query}'")
        results = search_by_embedding(query, top_k=5)
        for node_id, node_name, sim in results:
            print(f"  {sim:.3f}  {node_id}  ({node_name})")
    else:
        print("Usage: python3 flavor_embeddings.py --build | --test <query>")
