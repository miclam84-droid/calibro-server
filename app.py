# ============================================================
# CALIBRO — server. Riceve una domanda, naviga il grafo,
# costruisce il contesto, chiede a Mistral di rispondere.
# Stessa forma di Cruscotto: Flask + Postgres + Mistral.
# Gira in locale (SQLite) per provarlo, identico su Railway (Postgres).
# ============================================================
import os, json, sqlite3, pathlib
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"            # la cartella coi seed .sql

# ---- DB: SQLite in locale, Postgres su Railway -------------
def carica_grafo():
    """In locale costruisce il grafo in memoria dai .sql.
       Su Railway questa funzione leggerà invece da Postgres."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    schema = (GRAFO/"schema.sql").read_text(encoding="utf-8").replace("JSONB","TEXT")
    db.executescript(schema)
    for s in sorted(GRAFO.glob("seed-*.sql")):
        db.executescript(s.read_text(encoding="utf-8"))
    return db

# ---- il cuore: naviga il grafo dato un termine -------------
def cerca_contesto(db, termine):
    """Trova i nodi che matchano il termine e il loro vicinato.
       È il 'recupero strutturato': la base della risposta."""
    t = f"%{termine.lower()}%"
    hit = db.execute(
        "SELECT * FROM nodes WHERE lower(name) LIKE ? ORDER BY "
        "CASE type WHEN 'Fenomeno' THEN 0 WHEN 'Prodotto' THEN 1 ELSE 2 END LIMIT 5",
        (t,)).fetchall()
    if not hit:
        return None
    ctx = []
    for n in hit:
        nodo = dict(n); nodo["data"] = json.loads(n["data"] or "{}")
        # archi in uscita e in entrata
        out = db.execute("""SELECT e.relation, e.data, n.name, n.type, n.domain
                            FROM edges e JOIN nodes n ON n.id=e.to_id
                            WHERE e.from_id=?""",(n["id"],)).fetchall()
        inc = db.execute("""SELECT e.relation, e.data, n.name, n.type, n.domain
                            FROM edges e JOIN nodes n ON n.id=e.from_id
                            WHERE e.to_id=?""",(n["id"],)).fetchall()
        nodo["collegamenti"] = (
            [{"verso": r["name"], "tipo": r["type"], "dominio": r["domain"],
              "relazione": r["relation"], "data": json.loads(r["data"] or "{}")} for r in out] +
            [{"da": r["name"], "tipo": r["type"], "dominio": r["domain"],
              "relazione": r["relation"], "data": json.loads(r["data"] or "{}")} for r in inc]
        )
        ctx.append(nodo)
    return ctx

# ---- costruisce il prompt per Mistral dal contesto ---------
def costruisci_prompt(domanda, contesto):
    righe = []
    for n in contesto:
        righe.append(f"\n## {n['name']} ({n['type']}, {n['domain']})")
        if n["data"].get("scheda"): righe.append(n["data"]["scheda"])
        for c in n["collegamenti"]:
            altro = c.get("verso") or c.get("da")
            extra = c["data"].get("target") or c["data"].get("ruolo") or c["data"].get("causa") or ""
            righe.append(f"  - {c['relazione']}: {altro} ({c['dominio']}) {extra}")
    contesto_txt = "\n".join(righe)
    return f"""Sei Calibro, uno strumento che spiega la scienza della ristorazione
collegando bar, cucina e forno sotto gli stessi fenomeni fisici.
Rispondi alla domanda usando SOLO il contesto qui sotto, che viene da un grafo
di conoscenza. Mostra le connessioni cross-dominio quando ci sono.
Non inventare numeri: usa solo quelli nel contesto.

CONTESTO DAL GRAFO:
{contesto_txt}

DOMANDA: {domanda}

RISPOSTA (chiara, concreta, col taglio cross-dominio):"""

# ---- Mistral: su Railway con la chiave, in locale stampa il prompt
def chiedi_mistral(prompt):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None  # in locale senza chiave: mostriamo solo il prompt costruito
    from mistralai import Mistral
    client = Mistral(api_key=key)
    resp = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role":"user","content":prompt}])
    return resp.choices[0].message.content

# ---- endpoint -----------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chiedi", methods=["POST"])
def chiedi():
    domanda = (request.json or {}).get("domanda","").strip()
    if not domanda:
        return jsonify({"errore":"domanda vuota"}), 400
    db = carica_grafo()
    # estrazione termine ingenua: la parola più lunga (in locale).
    # Su Railway: Mistral estrae le entità. Qui teniamo semplice e funzionante.
    parole = [p.strip(".,?!").lower() for p in domanda.split() if len(p) > 4]
    contesto = None
    for p in parole:
        contesto = cerca_contesto(db, p)
        if contesto: break
    if not contesto:
        return jsonify({"risposta": None,
                        "nota": "Nessun nodo trovato nel grafo per questa domanda."})
    prompt = costruisci_prompt(domanda, contesto)
    risposta = chiedi_mistral(prompt)
    return jsonify({
        "trovato": [n["name"] for n in contesto],
        "prompt_costruito": prompt,       # così vedi COSA il grafo ha estratto
        "risposta": risposta              # None in locale senza chiave Mistral
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)
