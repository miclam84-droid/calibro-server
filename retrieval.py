# retrieval.py — candidate generation + ranking (sostituisce match->stop)
# Recepisce il parere OpenAI: genera candidati da tutte le fonti, raccoglili TUTTI, ranka, scegli.
# Deterministico e loggabile. Il dominio è un moltiplicatore, non un filtro.
import re, json

# --- dizionario parole-spia per dominio (domain detection semplice) ---
SPIE_DOMINIO = {
    "panificazione": ["impasto","farina","lievito","lievitazione","mollica","crosta","glutine","maglia",
                      "brioche","pane","pizza","manitoba","idratazione","forno","biga","poolish","autolisi",
                      "sale","focaccia","ciabatta","panettone","alveolatura","alveoli","raffermo","cottura"],
    "bar": ["cocktail","drink","gin","vodka","rum","tequila","negroni","amaro","bitter","vermouth","shakerato",
            "mescolato","diluizione","ghiaccio","infusione","fat washing","chiarificazione","garnish","citrico"],
    "caffetteria": ["caffè","caffe","espresso","estrazione","macinatura","crema","tostatura","chicco","barista"],
    "pasticceria": ["crema","pasticcera","meringa","ganache","cioccolato","temperaggio","glassa","pan di spagna","zabaione"],
    "gelateria": ["gelato","sorbetto","overrun","mantecazione","pac","pod","crioscopia","stabilizzante"],
    "cucina": ["carne","rosolatura","brasato","cottura","sottovuoto","emulsione","salsa","soffritto","maillard"],
    "vino": ["vino","fermentazione","tannini","affinamento","botte","polifenoli","solfiti","macerazione"],
}

def normalizza(s):
    s = (s or "").lower().strip()
    s = s.replace("'", "'").replace("`", "'")
    s = re.sub(r"[^\w\sàèéìòùäöü'-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def rileva_dominio(domanda):
    """Conta le parole-spia per dominio, ritorna il dominio prevalente (o None)."""
    d = normalizza(domanda)
    punteggi = {}
    for dom, spie in SPIE_DOMINIO.items():
        c = sum(1 for spia in spie if spia in d)
        if c: punteggi[dom] = c
    if not punteggi: return None, {}
    dom_top = max(punteggi, key=punteggi.get)
    return dom_top, punteggi

def _ngrams(parole, n):
    return [" ".join(parole[i:i+n]) for i in range(len(parole)-n+1)]

def genera_candidati(db, domanda, termini_extra=None):
    """Genera candidati da: alias (frase>parola), nome (esatto>parziale), testo, edges. SENZA fermarsi.
    Ritorna dict {node_id: {"node":row, "segnali":[...], "score":n}}."""
    dom_rilevato, _ = rileva_dominio(domanda)
    dnorm = normalizza(domanda)
    parole = [p for p in dnorm.split() if len(p) > 2]
    # n-grammi 3,2,1 (le frasi lunghe pesano di più)
    frasi3 = _ngrams(parole, 3)
    frasi2 = _ngrams(parole, 2)
    tutte_le_forme = [(f, 3) for f in frasi3] + [(f, 2) for f in frasi2] + [(p, 1) for p in parole]
    if termini_extra:
        for t in termini_extra:
            tn = normalizza(t)
            nw = len(tn.split())
            tutte_le_forme.append((tn, min(nw, 3)))

    candidati = {}
    def aggiungi(node, punti, motivo):
        nid = node["id"]
        if nid not in candidati:
            candidati[nid] = {"node": node, "score": 0, "segnali": []}
        candidati[nid]["score"] += punti
        candidati[nid]["segnali"].append(motivo)

    # carico tutti i fenomeni una volta (con data per alias/testo)
    fenomeni = db.execute("SELECT id, name, type, domain, data FROM nodes WHERE type='Fenomeno'").fetchall()
    # indice alias: alias_norm -> (node, n_parole)
    alias_index = {}
    for f in fenomeni:
        try:
            d = json.loads(f["data"] or "{}") if isinstance(f["data"], str) else (f["data"] or {})
        except Exception:
            d = {}
        for a in (d.get("aliases") or []):
            an = normalizza(a)
            if an:
                alias_index[an] = (f, len(an.split()))

    # 1) ALIAS matching (frase esatta batte parola)
    for forma, nwords in tutte_le_forme:
        if forma in alias_index:
            node, na = alias_index[forma]
            if na >= 2:
                aggiungi(node, 95, f"alias-frase '{forma}'")
            else:
                aggiungi(node, 80, f"alias '{forma}'")

    # 2) NOME esatto / parziale (su tutti i nodi, non solo fenomeni)
    for forma, nwords in tutte_le_forme:
        like = f"%{forma}%"
        for n in db.execute("SELECT id, name, type, domain, data FROM nodes WHERE lower(name) LIKE ? LIMIT 6", (like,)).fetchall():
            nm = normalizza(n["name"])
            if nm == forma:
                aggiungi(n, 90, f"nome-esatto '{forma}'")
            elif nwords >= 2:
                aggiungi(n, 65, f"nome-frase '{forma}'")
            else:
                aggiungi(n, 55, f"nome-parziale '{forma}'")

    # 3) TESTO scheda (solo fenomeni, peso basso)
    for forma, nwords in tutte_le_forme:
        if nwords < 2 and len(forma) < 5:
            continue  # evito parole cortissime nel testo (rumore)
        like = f"%{forma}%"
        try:
            for n in db.execute("SELECT id, name, type, domain, data FROM nodes WHERE type='Fenomeno' AND lower(CAST(data AS TEXT)) LIKE ? LIMIT 6", (like,)).fetchall():
                aggiungi(n, 30 if nwords>=2 else 20, f"testo '{forma}'")
        except Exception:
            pass

    # 4) BONUS DOMINIO (moltiplicatore leggero, non filtro)
    if dom_rilevato:
        for nid, c in candidati.items():
            nd = (c["node"]["domain"] or "").lower()
            if nd == dom_rilevato:
                c["score"] += 40
                c["segnali"].append(f"dominio={dom_rilevato} +40")

    # 5) BONUS TIPO (Fenomeno preferito come risposta)
    for nid, c in candidati.items():
        if c["node"]["type"] == "Fenomeno":
            c["score"] += 10
            c["segnali"].append("tipo=Fenomeno +10")

    return candidati, dom_rilevato

def retrieval_ranked(db, domanda, termini_extra=None, topk=5):
    """Ritorna i fenomeni migliori, rankati. Include navigazione errore->fenomeno."""
    candidati, dom = genera_candidati(db, domanda, termini_extra)
    # espansione via edges: se un candidato è un Errore, aggiungi i fenomeni che ci puntano (fallisce_come)
    extra = {}
    for nid, c in list(candidati.items()):
        if c["node"]["type"] == "Errore":
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='fallisce_come'", (nid,)).fetchall():
                fen = db.execute("SELECT id, name, type, domain, data FROM nodes WHERE id=? AND type='Fenomeno'", (e["from_id"],)).fetchone()
                if fen and fen["id"] not in candidati:
                    extra[fen["id"]] = {"node": fen, "score": c["score"]*0.6 + 25,
                                        "segnali": [f"via errore {nid} (fallisce_come)"]}
    candidati.update(extra)
    # tieni solo i Fenomeni nel risultato finale (l'utente vuole il fenomeno)
    fen_solo = {nid: c for nid, c in candidati.items() if c["node"]["type"] == "Fenomeno"}
    ordinati = sorted(fen_solo.values(), key=lambda c: c["score"], reverse=True)
    out = []
    for c in ordinati[:topk]:
        out.append({"id": c["node"]["id"], "name": c["node"]["name"],
                    "score": round(c["score"],1), "perche": c["segnali"][:4]})
    return {"dominio": dom, "fenomeni": out}
