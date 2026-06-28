# ============================================================
# CALIBRO — server. Riceve una domanda, naviga il grafo in
# profondita (risale ai fenomeni), costruisce un contesto ricco,
# e chiede a Mistral di rispondere SENZA inventare.
# Flask + grafo (SQLite locale / Postgres su Railway) + Mistral via HTTP.
# ============================================================
import os, json, sqlite3, pathlib
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
HERE = pathlib.Path(__file__).parent
GRAFO = HERE / "grafo"

def carica_grafo():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    schema = (GRAFO/"schema.sql").read_text(encoding="utf-8").replace("JSONB","TEXT")
    db.executescript(schema)
    for s in sorted(GRAFO.glob("seed-*.sql")):
        db.executescript(s.read_text(encoding="utf-8"))
    return db

# ---- ricerca contesto: profonda, centrata sui fenomeni ----
def cerca_contesto(db, termine):
    t = f"%{termine.lower()}%"
    hit = db.execute(
        "SELECT * FROM nodes WHERE lower(name) LIKE ? ORDER BY "
        "CASE type WHEN 'Fenomeno' THEN 0 WHEN 'Prodotto' THEN 1 "
        "WHEN 'Errore' THEN 2 ELSE 3 END LIMIT 4", (t,)).fetchall()
    if not hit:
        return None

    fenomeni = {}
    def aggiungi_fenomeno(fid):
        if fid in fenomeni: return
        f = db.execute("SELECT * FROM nodes WHERE id=? AND type='Fenomeno'", (fid,)).fetchone()
        if f: fenomeni[fid] = f

    prodotti_interesse = set()
    for n in hit:
        if n["type"] == "Fenomeno":
            aggiungi_fenomeno(n["id"])
        elif n["type"] == "Prodotto":
            prodotti_interesse.add(n["id"])
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])
        elif n["type"] == "Errore":
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='fallisce_come'", (n["id"],)):
                prodotti_interesse.add(e["from_id"])
                for f in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (e["from_id"],)):
                    aggiungi_fenomeno(f["from_id"])
        else:
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=?", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])

    if not fenomeni:
        for n in hit:
            fenomeni[n["id"]] = n

    ctx = []
    for fid, f in fenomeni.items():
        nodo = dict(f); nodo["data"] = json.loads(f["data"] or "{}")
        coll = []
        for e in db.execute("""SELECT e.relation, e.data, n.name, n.type, n.domain, n.id
                               FROM edges e JOIN nodes n ON n.id=e.to_id
                               WHERE e.from_id=?""", (fid,)):
            coll.append({"verso": e["name"], "tipo": e["type"], "dominio": e["domain"],
                         "relazione": e["relation"], "id": e["id"],
                         "data": json.loads(e["data"] or "{}")})
        nodo["collegamenti"] = coll
        ctx.append(nodo)

    errori = []
    for pid in prodotti_interesse:
        for e in db.execute("""SELECT n.name, e.data, n.domain FROM edges e
                               JOIN nodes n ON n.id=e.to_id
                               WHERE e.from_id=? AND e.relation='fallisce_come'""", (pid,)):
            pass
    # gli errori coi loro 'causa' stanno nel nodo errore stesso
    for pid in prodotti_interesse:
        for row in db.execute("""SELECT n.name, n.data, n.domain FROM edges e
                                 JOIN nodes n ON n.id=e.to_id
                                 WHERE e.from_id=? AND e.relation='fallisce_come'""", (pid,)):
            d = json.loads(row["data"] or "{}")
            if d.get("causa"):
                errori.append(f"{row['name']} ({row['domain']}): {d['causa']}")
    return {"fenomeni": ctx, "errori": errori, "prodotti": list(prodotti_interesse)}

# ---- costruisce il prompt -----------------------------------
def costruisci_prompt(domanda, contesto):
    righe = []
    for f in contesto["fenomeni"]:
        righe.append("")
        righe.append(f"### Fenomeno: {f['name']} ({f['domain']})")
        if f["data"].get("scheda"):
            righe.append(f["data"]["scheda"])
        manif = [c for c in f["collegamenti"] if c["relazione"] == "si_manifesta_in"]
        misu  = [c for c in f["collegamenti"] if c["relazione"] == "misurato_da"]
        proc  = [c for c in f["collegamenti"] if c["relazione"] == "realizzato_da"]
        tecn  = [c for c in f["collegamenti"] if c["relazione"] == "controllato_con"]
        if misu:
            righe.append("Si misura con: " + ", ".join(c["verso"] for c in misu))
        if proc:
            righe.append("Si realizza con: " + ", ".join(c["verso"] for c in proc))
        if manif:
            righe.append("Si manifesta in questi prodotti (coi numeri-bersaglio):")
            for c in manif:
                tgt = c["data"].get("target",""); ruolo = c["data"].get("ruolo","")
                righe.append(f"  - {c['verso']} [{c['dominio']}]: {tgt} — {ruolo}")
        if tecn:
            righe.append("Si controlla con: " + ", ".join(c["verso"] for c in tecn))
    if contesto.get("errori"):
        righe.append("")
        righe.append("Errori possibili e loro causa:")
        for e in contesto["errori"]:
            righe.append(f"  - {e}")
    contesto_txt = "\n".join(righe)

    regole = (
        "Sei uno strumento che spiega la ristorazione attraverso i fenomeni fisici "
        "e chimici che la governano: acidita, concentrazione, calore, osmosi, struttura. "
        "Questi fenomeni non appartengono a una disciplina: sono le stesse leggi che "
        "attraversano pasticceria, panificazione, cucina, mixology, caffetteria. "
        "Una madre, un sour e una confettura obbediscono alla stessa acidita; non sono "
        "mestieri diversi che si somigliano, sono lo stesso fenomeno in stanze diverse. "
        "Il tuo compito e rendere visibile questa unita: parti dal fenomeno, mostra il "
        "numero che lo governa, e fai vedere che la stessa legge ricompare dove non ce lo si aspetta.\n\n"
        "COME RISPONDERE:\n"
        "- Usa SOLO le informazioni nel contesto qui sotto. Non aggiungere prodotti, esempi "
        "o numeri che non sono nel contesto. Se un dato non c'e, non inventarlo: dillo.\n"
        "- Cita i numeri-bersaglio esatti del contesto (pH, Brix, percentuali, gradi).\n"
        "- Parti dal fenomeno e dal perche fisico, poi arriva al consiglio concreto.\n"
        "- Mostra la connessione cross-disciplina solo dove e davvero nel contesto, "
        "e falla emergere come un fatto naturale, non come un collegamento forzato.\n"
        "- Prosa pulita in italiano, senza asterischi, grassetti o markdown. Massimo 6-8 frasi."
    )
    return f"{regole}\n\nCONTESTO DAL GRAFO:\n{contesto_txt}\n\nDOMANDA: {domanda}\n\nRISPOSTA:"

# ---- Mistral via HTTP diretto (nessun SDK) ------------------
def chiedi_mistral(prompt):
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None
    import urllib.request
    body = json.dumps({
        "model": "mistral-small-latest",
        "messages": [{"role":"user","content":prompt}],
        "temperature": 0.2
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[errore nella chiamata a Mistral: {e}]"

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
    parole = sorted([p.strip(".,?!").lower() for p in domanda.split() if len(p) > 4], key=len, reverse=True)
    contesto = None
    for p in parole:
        contesto = cerca_contesto(db, p)
        if contesto and contesto.get("fenomeni"): break
    if not contesto or not contesto.get("fenomeni"):
        return jsonify({"risposta": None,
                        "nota": "Nessun nodo trovato nel grafo per questa domanda."})
    prompt = costruisci_prompt(domanda, contesto)
    risposta = chiedi_mistral(prompt)
    return jsonify({
        "trovato": [f["name"] for f in contesto["fenomeni"]],
        "prompt_costruito": prompt,
        "risposta": risposta
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)
