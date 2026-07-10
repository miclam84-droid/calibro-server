"""
Costruisce la mappa COMPLETA inglese → italiano per tutti i nodi Ahn.
Usa GPT-4o-mini per tradurre in batch — costo ~$0.02 totale.
Salva in Postgres nella tabella flavor_nomi_it.

Eseguire una volta dalla Railway Console:
  python3 build_flavor_it.py
"""
import os, sys, json, time, psycopg2, urllib.request

DATABASE_URL = os.environ.get("DATABASE_URL","")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY","")

def gpt_traduci(nomi_en):
    """Traduce una lista di nomi inglesi in italiano via GPT-4o-mini."""
    prompt = (
        "Sei un traduttore di ingredienti alimentari. "
        "Traduci questi nomi di ingredienti dall'inglese all'italiano. "
        "Rispondi SOLO con un JSON array nell'ordine esatto, es: [\"pomodoro\",\"limone\"]. "
        "Nessun altro testo.\n\n"
        "Ingredienti: " + json.dumps(nomi_en)
    )
    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role":"user","content":prompt}],
        "temperature": 0,
        "max_tokens": 2000
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    testo = data["choices"][0]["message"]["content"].strip()
    # Pulizia: rimuovi backtick e json label
    testo = testo.replace("```json","").replace("```","").strip()
    return json.loads(testo)

def build():
    if not DATABASE_URL or not OPENAI_KEY:
        print("Variabili mancanti"); return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Tabella mappa nomi
    cur.execute("""CREATE TABLE IF NOT EXISTS flavor_nomi_it (
        node_id   TEXT PRIMARY KEY,
        nome_en   TEXT NOT NULL,
        nome_it   TEXT NOT NULL,
        ts        TIMESTAMPTZ DEFAULT NOW()
    )""")
    conn.commit()

    # Recupera tutti i nodi Ahn con abbinamenti
    cur.execute("""
        SELECT DISTINCT e.from_id, n.name
        FROM edges e
        LEFT JOIN nodes n ON n.id = e.from_id
        WHERE e.relation = 'abbinamento_aromatico'
        ORDER BY e.from_id
    """)
    nodi = cur.fetchall()
    print(f"Nodi Ahn totali: {len(nodi)}")

    # Quanti già tradotti
    cur.execute("SELECT COUNT(*) FROM flavor_nomi_it")
    gia = cur.fetchone()[0]
    print(f"Già tradotti: {gia}")

    # Trova quelli mancanti
    cur.execute("SELECT node_id FROM flavor_nomi_it")
    tradotti = {r[0] for r in cur.fetchall()}
    da_fare = [(nid, nome) for nid, nome in nodi if nid not in tradotti]
    print(f"Da tradurre: {len(da_fare)}")

    if not da_fare:
        print("Tutto già tradotto."); cur.close(); conn.close(); return

    # Traduzione in batch da 50
    BATCH = 50
    totale = 0
    for i in range(0, len(da_fare), BATCH):
        batch = da_fare[i:i+BATCH]
        nomi_en = [nome.replace("_"," ").lower() if nome else nid.replace("ahn_","").replace("_"," ")
                   for nid, nome in batch]
        try:
            nomi_it = gpt_traduci(nomi_en)
            if len(nomi_it) != len(batch):
                print(f"  Batch {i//BATCH+1}: risposta malformata, skip")
                continue
            for (nid, nome), it in zip(batch, nomi_it):
                nome_en = nome.replace("_"," ").lower() if nome else nid.replace("ahn_","").replace("_"," ")
                cur.execute("""
                    INSERT INTO flavor_nomi_it (node_id, nome_en, nome_it)
                    VALUES (%s,%s,%s)
                    ON CONFLICT (node_id) DO UPDATE SET nome_it=EXCLUDED.nome_it
                """, (nid, nome_en, it.lower().strip()))
            conn.commit()
            totale += len(batch)
            print(f"  Batch {i//BATCH+1}: +{len(batch)} tradotti (es: '{nomi_en[0]}' → '{nomi_it[0]}')")
            time.sleep(0.2)
        except Exception as e:
            print(f"  Batch {i//BATCH+1} ERRORE: {e}")
            conn.rollback()

    cur.close(); conn.close()
    print(f"\nCompletato. Tradotti: {totale}. Totale in DB: {gia+totale}")

if __name__ == "__main__":
    build()
