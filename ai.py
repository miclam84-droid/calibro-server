# ============================================================
# ai.py — helper AI condivisi: chiamate a Mistral/Claude/Haiku,
# ricerca contesto nel grafo, costruzione prompt, estrazione entità,
# traduzione schede. Usato da app.py e dai blueprint (chat/lezione/api).
# Dipende da: db (carica_grafo/_dati), contenuto (_scheda_lang/
# _numero_bersaglio/_pulisci_traduzione), config (DATABASE_URL).
# ============================================================
import os, json, difflib, re
import ai_gateway as GW

# Tool definitions per il calcolatore deterministico
_TOOLS = [
    {
        "name": "calcola",
        "description": "Esegui un calcolo deterministico esatto. Usa questo tool quando la domanda contiene numeri propri dell'utente (ml, gradi, grammi, Brix, temperatura...). Restituisce numero + interpretazione + leva d'azione.",
        "input_schema": {
            "type": "object",
            "properties": {
                "calcolo": {
                    "type": "string",
                    "enum": ["diluizione","bilanciamento_sour","idratazione_pane","q10_fermentazione",
                             "estrazione_caffe","pareggia_acidita","scalatore_impasto","conversione_teglie",
                             "food_cost_piatto","temperatura_servizio_vino","brix_to_abv"],
                    "description": "Il tipo di calcolo: diluizione cocktail, bilanciamento sour, idratazione pane, Q10 fermentazione, estrazione caffè, pareggia acidità, scalatore impasto, conversione teglie, food cost piatto, temperatura servizio vino, Brix→ABV"
                },
                "parametri": {
                    "type": "object",
                    "description": "Parametri del calcolo"
                }
            },
            "required": ["calcolo","parametri"]
        }
    }
]

from db import carica_grafo, _dati, _get_conn, _release_conn
from contenuto import _scheda_lang, _numero_bersaglio, _pulisci_traduzione
from config import DATABASE_URL


def _scheda_tradotta(node_id, data_dict, lang, conn):
    """Traduzione lazy della scheda: se non esiste per la lingua richiesta,
    la genera con Haiku e la salva nel nodo. Una volta sola per nodo+lingua."""
    if lang == "it":
        return _scheda_lang(data_dict, "it")
    
    scheda = data_dict.get("scheda", "")
    
    # Se è già un dizionario con la lingua richiesta, usa quella
    if isinstance(scheda, dict):
        if scheda.get(lang):
            return _pulisci_traduzione(scheda[lang])
        scheda_it = scheda.get("it", "") or ""
    else:
        scheda_it = scheda or ""
        scheda = {"it": scheda_it}
    
    if not scheda_it:
        return ""
    
    # Genera traduzione con Haiku
    if lang == "en":
        prompt = (f"Translate this Italian F&B technical sheet to English. "
                  f"Keep technical terms, numbers, and scientific accuracy. "
                  f"Output ONLY the translation, no headers or labels:\n\n{scheda_it[:1500]}")
    elif lang == "es":
        prompt = (f"Traduce esta ficha técnica italiana de F&B al español. "
                  f"Mantén los términos técnicos, números y precisión científica. "
                  f"Escribe SOLO la traducción, sin encabezados ni etiquetas:\n\n{scheda_it[:1500]}")
    else:
        return scheda_it
    
    try:
        traduzione = _haiku_raw(prompt, max_tokens=800)
        traduzione = _pulisci_traduzione(traduzione)
        if traduzione:
            scheda[lang] = traduzione
            # Salva nel nodo
            if conn and node_id:
                import psycopg2.extras as _psx
                cur = conn.cursor()
                data_dict["scheda"] = scheda
                cur.execute(
                    "UPDATE nodes SET data = %s WHERE id = %s",
                    (_psx.Json(data_dict), node_id)
                )
                conn.commit()
                cur.close()
            return traduzione
    except Exception as _te:
        print(f"[TRAD] {node_id} {lang}: {_te}", flush=True)
    
    return scheda_it  # fallback IT

def _intro(testo, n=200):
    """Anteprima breve che NON taglia a metà parola. Tronca all'ultimo spazio
    entro n caratteri e aggiunge l'ellissi, così non compaiono monconi come
    'fa da orologi'. Se il testo è già corto, resta intero."""
    testo = (testo or "").strip()
    if len(testo) <= n:
        return testo
    taglio = testo[:n]
    sp = taglio.rfind(" ")
    if sp > 0:
        taglio = taglio[:sp]
    return taglio.rstrip(" ,.;:—-") + "…"

def _domanda_chiede_perche(domanda):
    """True se la domanda chiede il principio sottostante ('perché', 'causa', ecc.)
    In quel caso includiamo gli archi relation='spiega' nel contesto."""
    parole = {"perché", "perche", "causa", "principio", "legge", "spiega", "spiegami",
               "why", "because", "underlying", "behind"}
    return any(p in domanda.lower() for p in parole)

def cerca_contesto(db, termine, domanda=""):
    t = f"%{termine.lower()}%"
    # LIVELLO 0 (priorita massima): ALIAS contestuali. Se il termine e' un alias di un fenomeno,
    # quel fenomeno va in testa. Cosi "olio" trova fen-grassi-impasto anche se 10 nodi hanno "olio" nel nome.
    alias_hit = []
    try:
        tl = termine.lower().strip()
        cand = db.execute("SELECT * FROM nodes WHERE lower(CAST(data AS TEXT)) LIKE ? AND type='Fenomeno'",
                          (f'%"{tl}"%',)).fetchall()
        for n in cand:
            d = _dati(n["data"])
            al = d.get("aliases", [])
            if isinstance(al, list) and tl in [str(a).lower() for a in al]:
                alias_hit.append(n)
    except Exception:
        pass
    # Ricerca a due livelli con ranking (due query separate per compatibilita SQLite-locale / Postgres-prod):
    #  livello 0 = match nel NOME (piu forte)
    #  livello 1 = match nel TESTO della scheda (campo data) — cosi "olio" trova fen-grassi-impasto
    ord_tipo = ("ORDER BY CASE type WHEN 'Fenomeno' THEN 0 WHEN 'Prodotto' THEN 1 "
                "WHEN 'Errore' THEN 2 ELSE 3 END LIMIT 8")
    per_nome = db.execute("SELECT * FROM nodes WHERE lower(name) LIKE ? " + ord_tipo, (t,)).fetchall()
    visti_id = set(n["id"] for n in per_nome)
    hit = list(per_nome)
    if len(hit) < 8:
        try:
            per_testo = db.execute(
                "SELECT * FROM nodes WHERE lower(CAST(data AS TEXT)) LIKE ? " + ord_tipo, (t,)).fetchall()
            for n in per_testo:
                if n["id"] not in visti_id:
                    hit.append(n); visti_id.add(n["id"])
                    if len(hit) >= 8: break
        except Exception:
            pass  # se il CAST non e' supportato, resta la ricerca per nome
    # anteponi gli alias_hit (priorita massima), evitando duplicati
    if alias_hit:
        ids_hit = set(n["id"] for n in hit)
        hit = alias_hit + [n for n in hit if n["id"] not in set(a["id"] for a in alias_hit)]
    if not hit:
        return None

    fenomeni = {}
    def aggiungi_fenomeno(fid):
        if fid in fenomeni: return
        f = db.execute("SELECT * FROM nodes WHERE id=? AND type='Fenomeno'", (fid,)).fetchone()
        if f: fenomeni[fid] = f

    prodotti_interesse = set()
    prodotti_fisici = {}   # id → dati fisici (pH, Aw, ecc.)

    for n in hit:
        if n["type"] == "Fenomeno":
            aggiungi_fenomeno(n["id"])
        elif n["type"] == "Prodotto":
            prodotti_interesse.add(n["id"])
            d = _dati(n["data"])
            # raccoglie parametri fisici se presenti
            fisici = {}
            for k in ("ph_min","ph_max","ph_note","aw_min","aw_max",
                      "acidita_titolabile_pct","acidita_titolabile_g_l",
                      "coagulazione_t","t_sicurezza","variabilita",
                      "abv_pct","abv_min","abv_max",
                      "tds_pct","tds_pct_min","tds_pct_max",
                      "ey_pct_min","ey_pct_max",
                      "brix","brix_min","brix_max","brix_sciroppo_1_1",
                      "punto_fumo_c","ibu_min","ibu_max","co2_volumi",
                      "sale_pct","overrun_pct_min","overrun_pct_max",
                      "t_servizio","t_conservazione",
                      "t_beta_amilasi","t_alfa_amilasi","t_caramellizzazione",
                      "grassi_pct","acidita_libera_pct_max",
                      "cristallizzazione_t","proteine_pct","note","fonte","segreto"):
                if k in d:
                    fisici[k] = d[k]
            if fisici:
                fisici["nome"] = n["name"]
                prodotti_fisici[n["id"]] = fisici
            # risali al fenomeno via governato_da o si_manifesta_in
            for e in db.execute(
                "SELECT to_id FROM edges WHERE from_id=? AND relation IN ('governato_da','si_manifesta_in')",
                (n["id"],)):
                aggiungi_fenomeno(e["to_id"])
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])
        elif n["type"] == "Errore":
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='fallisce_come'", (n["id"],)):
                origine = db.execute("SELECT id, type FROM nodes WHERE id=?", (e["from_id"],)).fetchone()
                if origine and origine["type"] == "Fenomeno":
                    # cablaggio diretto Fenomeno -fallisce_come-> Errore
                    aggiungi_fenomeno(e["from_id"])
                else:
                    # cablaggio originale Prodotto -fallisce_come-> Errore, risali via si_manifesta_in
                    prodotti_interesse.add(e["from_id"])
                    for f in db.execute("SELECT from_id FROM edges WHERE to_id=? AND relation='si_manifesta_in'", (e["from_id"],)):
                        aggiungi_fenomeno(f["from_id"])
        else:
            for e in db.execute("SELECT from_id FROM edges WHERE to_id=?", (n["id"],)):
                aggiungi_fenomeno(e["from_id"])

    if not fenomeni:
        for n in hit:
            fenomeni[n["id"]] = n

    includi_principi = _domanda_chiede_perche(domanda)

    ctx = []
    for fid, f in fenomeni.items():
        nodo = dict(f); nodo["data"] = _dati(f["data"])
        coll = []
        for e in db.execute("""SELECT e.relation, e.data, n.name, n.type, n.domain, n.id
                               FROM edges e JOIN nodes n ON n.id=e.to_id
                               WHERE e.from_id=?
                               AND e.relation != 'spiega'""", (fid,)):
            coll.append({"verso": e["name"], "tipo": e["type"], "dominio": e["domain"],
                         "relazione": e["relation"], "id": e["id"],
                         "data": _dati(e["data"])})
        if includi_principi:
            for e in db.execute("""SELECT n.name, n.id, n.data FROM edges e
                                   JOIN nodes n ON n.id=e.from_id
                                   WHERE e.to_id=? AND e.relation='spiega'
                                   AND n.type='principio'""", (fid,)):
                d = _dati(e["data"])
                coll.append({"verso": e["name"], "tipo": "principio", "dominio": "trasversale",
                             "relazione": "spiega", "id": e["id"], "data": d})
        nodo["collegamenti"] = coll
        ctx.append(nodo)

    errori = []
    for pid in prodotti_interesse:
        for row in db.execute("""SELECT n.name, n.data, n.domain FROM edges e
                                 JOIN nodes n ON n.id=e.to_id
                                 WHERE e.from_id=? AND e.relation='fallisce_come'""", (pid,)):
            d = _dati(row["data"])
            if d.get("causa"):
                errori.append(f"{row['name']} ({row['domain']}): {d['causa']}")

    return {
        "fenomeni": ctx,
        "errori": errori,
        "prodotti": list(prodotti_interesse),
        "prodotti_fisici": list(prodotti_fisici.values())  # nuovo
    }

def costruisci_prompt(domanda, contesto, lang="it"):
    righe = []
    for f in contesto["fenomeni"]:
        righe.append("")
        righe.append(f"### Fenomeno: {f['name']} ({f['domain']})")
        sch = _scheda_lang(f["data"], lang)
        if sch:
            righe.append(sch)
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

    # Aggiungi parametri fisici ingredienti se presenti
    fisici = contesto.get("prodotti_fisici", [])
    if fisici:
        righe_f = ["\n### Parametri fisici ingredienti (dal dataset Matter):"]
        for p in fisici:
            nome = p.get("nome", "?")
            r = f"  {nome}:"
            if "ph_min" in p and "ph_max" in p:
                r += f" pH {p['ph_min']}-{p['ph_max']}"
            if "ph_note" in p:
                r += f" ({p['ph_note']})"
            if "variabilita" in p:
                r += f" · variabilità: {p['variabilita']}"
            if "aw_min" in p:
                r += f" · Aw {p['aw_min']}-{p.get('aw_max','?')}"
            if "coagulazione_t" in p:
                r += f" · coagulazione: {p['coagulazione_t']}"
            if "t_sicurezza" in p:
                r += f" · T sicurezza: {p['t_sicurezza']}"
            if "acidita_titolabile_pct" in p:
                r += f" · acidità titolabile: {p['acidita_titolabile_pct']}%"
            if p.get("segreto"):
                r += f"\n    SEGRETO DEL MESTIERE: {p['segreto']}"
            if "acidita_titolabile_g_l" in p:
                r += f" · acidità titolabile: {p['acidita_titolabile_g_l']} g/L"
            if "brix" in p:
                r += f" · {p['brix']}°Brix"
            if "brix_min" in p and "brix_max" in p:
                r += f" · {p['brix_min']}-{p['brix_max']}°Brix"
            if "abv_min" in p and "abv_max" in p:
                r += f" · ABV {p['abv_min']}-{p['abv_max']}%"
            if "tds_pct_min" in p and "tds_pct_max" in p:
                r += f" · TDS {p['tds_pct_min']}-{p['tds_pct_max']}%"
            if "ey_pct_min" in p and "ey_pct_max" in p:
                r += f" · EY {p['ey_pct_min']}-{p['ey_pct_max']}%"
            if "punto_fumo_c" in p:
                r += f" · punto fumo: {p['punto_fumo_c']}°C"
            if "ibu_min" in p and "ibu_max" in p:
                r += f" · IBU {p['ibu_min']}-{p['ibu_max']}"
            if "co2_volumi" in p:
                r += f" · CO₂: {p['co2_volumi']} volumi"
            if "sale_pct" in p:
                r += f" · sale: {p['sale_pct']}%"
            if "overrun_pct_min" in p:
                r += f" · overrun: {p['overrun_pct_min']}-{p.get('overrun_pct_max','?')}%"
            if "t_servizio" in p:
                r += f" · T servizio: {p['t_servizio']}"
            if "t_conservazione" in p:
                r += f" · T conservazione: {p['t_conservazione']}"
            if "t_beta_amilasi" in p:
                r += f" · beta-amilasi: {p['t_beta_amilasi']}"
            if "t_alfa_amilasi" in p:
                r += f" · alfa-amilasi: {p['t_alfa_amilasi']}"
            if "t_caramellizzazione" in p:
                r += f" · caramellizzazione: {p['t_caramellizzazione']}"
            if "grassi_pct" in p:
                r += f" · grassi: {p['grassi_pct']}%"
            if "acidita_libera_pct_max" in p:
                r += f" · acidità libera max: {p['acidita_libera_pct_max']}%"
            if "note" in p:
                r += f" · note: {p['note']}"
            if "fonte" in p:
                r += f" · fonte: {p['fonte']}"
            righe_f.append(r)
        contesto_txt += "\n".join(righe_f)

    if lang == "en":
        regole = (
            "You are a tool that explains food and drink through the physical and chemical "
            "phenomena that govern them: acidity, concentration, heat, osmosis, structure. "
            "These phenomena belong to no single discipline — they are the same laws that run "
            "through pastry, bread, cooking, mixology, and coffee.\n\n"
            "HOW TO RESPOND:\n"
            "- Always anchor the answer to the physical phenomenon found in the context. "
            "Start from the phenomenon, show the number that governs it, then apply it to the question.\n"
            "- Use the exact target numbers from the context when available. "
            "When the context does not contain a specific product or number, "
            "use your scientific knowledge of that phenomenon to answer — "
            "do not say 'the context does not contain this data'. Just answer.\n"
            "- Never explain your reasoning process, never mention the graph, "
            "never say what you can or cannot do. Respond directly.\n"
            "- Tone: colleague to colleague. The professional knows their craft — "
            "show them the physical why. No lectures, no obvious explanations.\n"
            "- Show cross-disciplinary connections naturally when they add value.\n"
            "- If the question contains specific numbers (ml, grams, degrees, percentages), "
            "use the 'calcola' tool for exact results.\n"
            "- Structure the response in this EXACT format (use these labels in uppercase followed by a colon):\n"
            "PROBLEM: [one sentence identifying the physical cause]\n"
            "WHY: [physical explanation, max 2 sentences]\n"
            "NUMBER: [exact target number — temperature, pH, percentage, etc.]\n"
            "MEASURE: [how to measure at the counter — tool and method]\n"
            "ACTION: [what to do concretely — max 2 sentences]\n"
            "No markdown, asterisks, bold. Only the format above.\n"
            "- Never mention being an AI or using a graph.\n"
            "IMPORTANT: Always respond in English, regardless of the language of the technical context provided."
        )
    elif lang == "es":
        import datetime as _dt
        _oggi = _dt.date.today()
        _mese = _oggi.month
        _stagione_es = (
            "invierno (diciembre-febrero)" if _mese in (12,1,2) else
            "primavera (marzo-mayo)"       if _mese in (3,4,5) else
            "verano (junio-agosto)"        if _mese in (6,7,8) else
            "otono (septiembre-noviembre)"
        )
        _frutti_es = {
            "verano":    "tomates, calabacines, berenjenas, pimientos, albahaca, melocotones, sandía, melón",
            "otono":     "setas, trufa, calabaza, manzanas, peras, uvas, castanas, col",
            "invierno":  "cítricos (naranjas, mandarinas, limones), col, brocoli, hinojo, alcachofas",
            "primavera": "espárragos, guisantes, habas, alcachofas, espinacas, fresas, cerezas",
        }.get(_stagione_es.split(" ")[0], "")
        regole = (
            f"Hoy es {_oggi.strftime('%d/%m/%Y')} — estamos en {_stagione_es}.\n"
            f"Ingredientes de temporada: {_frutti_es}.\n"
            f"Usa SOLO productos de temporada salvo que la pregunta lo especifique.\n\n"
            "Eres una herramienta que explica la gastronomía a través de los fenómenos físicos "
            "y químicos: acidez, concentración, calor, ósmosis, estructura.\n\n"
            "CÓMO RESPONDER:\n"
            "- Ancla la respuesta al fenómeno físico del contexto y muestra el número objetivo.\n"
            "- Usa los números exactos del contexto. Si no están, usa tu conocimiento científico.\n"
            "- Nunca expliques tu razonamiento ni menciones el grafo. Responde directamente.\n"
            "- Tono de colega a colega: muestra el porqué físico. Sin lecciones.\n"
            "- Si hay números del usuario (ml, gramos, grados), usa la herramienta calcola.\n"
            "- Estructura la respuesta en este formato EXACTO (usa estas etiquetas en mayúsculas seguidas de dos puntos):\n"
            "PROBLEMA: [una frase que identifica la causa física]\n"
            "POR QUÉ: [explicación física, máx. 2 frases]\n"
            "NÚMERO: [el número objetivo exacto — temperatura, pH, porcentaje, etc.]\n"
            "MIDE: [cómo medirlo en el trabajo — herramienta y método]\n"
            "ACCIÓN: [qué hacer concretamente — máx. 2 frases]\n"
            "Sin markdown, asteriscos, negrita. Solo el formato anterior.\n"
            "- Nunca menciones ser una IA.\n"
            "IMPORTANTE: Responde SIEMPRE en español, independientemente del idioma del contexto técnico proporcionado."
        )
    else:
        import datetime as _dt
        _oggi = _dt.date.today()
        _mese = _oggi.month
        _stagione = (
            "inverno (dicembre-febbraio)" if _mese in (12,1,2) else
            "primavera (marzo-maggio)"   if _mese in (3,4,5) else
            "estate (giugno-agosto)"     if _mese in (6,7,8) else
            "autunno (settembre-novembre)"
        )
        _prodotti_stagione = {
            "estate":    "pomodori, zucchine, melanzane, peperoni, basilico, fichi, albicocche, pesche, more, anguria, melone",
            "autunno":   "funghi porcini, tartufo, zucca, mele, pere, uva, fichi d'India, cachi, radicchio, castagne, cavolo",
            "inverno":   "agrumi (arance, mandarini, limoni), cavolo nero, verza, broccoli, finocchi, carciofi, topinambur, cardi",
            "primavera": "asparagi, piselli, fave, carciofi, spinaci, agretti, fragole, ciliegie, erbe fresche (menta, erba cipollina)",
        }
        _stagione_key = _stagione.split(" ")[0]
        _frutti = _prodotti_stagione.get(_stagione_key, "")
        regole = (
            f"Data odierna: {_oggi.strftime('%d %B %Y')} — siamo in {_stagione}.\n"
            f"Prodotti di stagione ora (utile come contesto): {_frutti}.\n"
            f"La stagionalità è solo un'informazione di contesto: se l'utente chiede una ricetta o "
            f"un abbinamento con ingredienti specifici, USALI SEMPRE senza rifiutare e senza fare "
            f"la morale sulla stagionalità. Non rifiutare mai una richiesta legittima. Puoi al "
            f"massimo menzionare la stagione se è pertinente, ma l'utente ha sempre ragione sugli "
            f"ingredienti che vuole usare.\n\n"
            "Sei uno strumento che spiega la ristorazione attraverso i fenomeni fisici "
            "e chimici che la governano: acidita, concentrazione, calore, osmosi, struttura. "
            "Questi fenomeni non appartengono a una disciplina: sono le stesse leggi che "
            "attraversano pasticceria, panificazione, cucina, mixology, caffetteria.\n\n"
            "COME RISPONDERE:\n"
            "- Aggancia sempre la risposta al fenomeno fisico trovato nel contesto. "
            "Parti dal fenomeno, mostra il numero che lo governa, poi applicalo alla domanda.\n"
            "- Usa i numeri-bersaglio esatti del contesto quando ci sono. "
            "Quando il contesto non contiene un ingrediente o un prodotto specifico, "
            "usa la tua conoscenza scientifica di quel fenomeno per rispondere — "
            "non dire 'il contesto non contiene questo dato'. Rispondi e basta.\n"
            "- Non spiegare mai il tuo processo di ragionamento, non menzionare il grafo, "
            "non dire cosa puoi o non puoi fare. Rispondi direttamente.\n"
            "- L'app Matter PUÒ analizzare foto di ingredienti e bottiglie (funzione 'Foto' Pro): "
            "se l'utente chiede di fotografare o creare un menù dalle foto, NON dire che non puoi — "
            "invitalo a usare il pulsante Foto. Non negare mai le capacità dell'app.\n"
            "- Tono da collega a collega: il professionista sa gia fare il suo lavoro, "
            "tu gli mostri il perche fisico. Niente lezioni, niente ovvieta.\n"
            "- Mostra la connessione cross-disciplina quando aggiunge valore, in modo naturale.\n"
            "- Se la domanda ha numeri propri dell'utente (ml, grammi, gradi, percentuali), "
            "usa il tool 'calcola' per dare risultati esatti.\n"
            "- Struttura la risposta in questo formato ESATTO (usa questi label in maiuscolo seguiti da due punti):\n"
            "PROBLEMA: [una frase — la causa fisica precisa, non una diagnosi vaga]\n"
            "PERCHÉ: [meccanismo fisico o chimico verificato, max 2 frasi. Solo fatti certi]\n"
            "NUMERO: [SOLO un valore numerico o un intervallo con unità — es: 65°C, 1.2-1.5%, 2-5%, pH 4-5. "
            "Se il fenomeno non ha un numero misurabile, scrivi esattamente: — (un trattino). "
            "MAI mettere frasi, spiegazioni, elenchi o simboli come → o · in questo campo. Solo il numero o il trattino.]\n"
            "MISURA: [strumento + metodo in 1 frase secca — es: pH-metro, leggi dopo 30s. NON fare liste]\n"
            "AZIONE: [cosa fare concretamente, max 2 frasi operative]\n"
            "Non usare markdown, asterischi, grassetti. Solo il formato sopra.\n"
            "REGOLE SCIENTIFICHE INVIOLABILI:\n"
            "1. Il glutine NON contiene collagene — sono proteine diverse\n"
            "2. Acido citrico e malico NON sono volatili — non evaporano con la cottura\n"
            "3. Q10 si applica solo a reazioni biologiche/enzimatiche — NON al rilassamento glutinico\n"
            "4. Pasta madre: pH ottimale 4.2-4.5, non 3.8-4.2\n"
            "5. Latte per cappuccino: temperatura target 65-68°C, non 60-65°C\n"
            "6. I terpeni precipitano per separazione di fase — NON polimerizzano\n"
            "7. Nella pasta madre prevale Kazachstania humilis, non Saccharomyces cerevisiae\n"
            "8. Il calore latente di fusione del ghiaccio (334 J/g) non c'entra con la crosta in padella\n"
            "9. MAI inventare dati numerici non presenti nel contesto — usa range verificati\n"
            "10. MISURA deve essere breve: uno strumento, un metodo. Non fare liste\n"
            "SICUREZZA ALIMENTARE (HACCP): se la domanda tocca conservazione, catena del freddo, "
            "temperature di sicurezza al cuore, sottovuoto/cottura a bassa temperatura, fermentazioni, "
            "conserve, crudo (pesce/carne/uova), o rischio microbiologico (listeria, salmonella, botulino, "
            "clostridi), AGGIUNGI in fondo alla risposta, su una riga nuova, esattamente questa nota:\n"
            "HACCP: questo è un principio generale — verifica sempre col tuo piano HACCP e con un consulente qualificato.\n"
            "Non allarmare inutilmente: aggiungi la nota SOLO quando il tema è davvero di sicurezza alimentare, "
            "non per ogni temperatura (un cappuccino a 65°C non è sicurezza alimentare).\n"
            "- Non menzionare mai di essere un AI o di usare un grafo."
        )
    return f"{regole}\n\nCONTESTO DAL GRAFO:\n{contesto_txt}\n\nDOMANDA: {domanda}\n\nRISPOSTA:"

def _mistral_raw(prompt, max_tokens=None):
    """Wrapper retrocompatibile → AI Gateway compat_mistral_raw."""
    import ai_gateway as GW
    return GW.compat_mistral_raw(prompt, max_tokens=max_tokens)

def estrai_entita(domanda):
    """Fa estrarre a Mistral i concetti del dominio, per agganciare meglio i nodi del grafo.
    Esempio: 'perché la carne non rosola?' -> ['rosolatura','carne','Maillard'].
    Se fallisce, ritorna [] e il chiamante ripiega sulle parole della domanda."""
    prompt = (
        "Sei un estrattore di concetti per uno strumento di scienza della ristorazione. "
        "Dalla domanda qui sotto estrai da 1 a 4 termini-chiave: il fenomeno fisico-chimico "
        "coinvolto (es. Maillard, acidità, fermentazione, estrazione, carbonatazione, osmosi, "
        "concentrazione, calore, struttura) e/o il prodotto (es. carne, pane, caffè, confettura). "
        "Rispondi SOLO con i termini separati da virgola, nient'altro.\n\n"
        f"Domanda: {domanda}\nTermini:"
    )
    try:
        out = _mistral_raw(prompt, max_tokens=40)
        if not out:
            return []
        termini = [t.strip(" .\n").lower() for t in out.split(",")]
        return [t for t in termini if t][:4]
    except Exception:
        return []

def _anthropic_raw(prompt):
    """Wrapper retrocompatibile → AI Gateway route_chat."""
    import ai_gateway as GW
    return GW.route_chat(prompt, tools=_TOOLS)

def _haiku_raw(prompt, max_tokens=600):
    """Wrapper retrocompatibile → AI Gateway route_fast."""
    import ai_gateway as GW
    return GW.route_fast(prompt, max_tokens=max_tokens)

def chiedi_mistral(prompt, history=None, usa_tools=True):
    """Nome storico mantenuto — ora usa AI Gateway route_chat con fallback automatico.
    I tools (calcola) vengono passati solo se il prompt contiene numeri — altrimenti
    Sonnet tende a fare tool_use su domande semplici esaurendo i token.
    usa_tools=False: forza NESSUN tool (per la generazione ricette, dove i numeri
    vengono gia dal grafo: cosi Sonnet fa UN solo round-trip, molto piu veloce, no timeout)."""
    import ai_gateway as GW
    import re as _re2
    if not usa_tools:
        _tools_da_usare = None
    else:
        # passa tools solo se ci sono numeri/unità nella domanda
        _ha_numeri = bool(_re2.search(r'\d+[\s,.]?\d*\s*(ml|g|kg|°|%|bar|L|cl)', prompt[-500:]))
        _tools_da_usare = _TOOLS if _ha_numeri else None
    try:
        out = GW.route_chat(prompt, tools=_tools_da_usare, history=history)
        if out:
            return out
    except Exception as e:
        print(f"[GW] route_chat fallito in chiedi_mistral: {e}", flush=True)
    return None


_STOPWORD = {"quanto","costa","tempo","oggi","sempre","abbastanza","molto","poco",
             "questo","quella","quello","perche","perché","dopo","prima","viene",
             "fanno","fatto","faccio","vorrei","volevo","sento","vedo","sono",
             "della","dello","delle","degli","quando","dove","come","cosa"}

def cerca_fuzzy(db, domanda):
    """Quando nessun termine estratto matcha ESATTAMENTE un nodo, cerca per
    SOMIGLIANZA parola-per-parola tra la domanda e i nomi dei nodi del grafo.
    Gestisce forme diverse della stessa parola (es. 'rosolisce' vs 'rosolata',
    'lievita' vs 'lievito') senza generare falsi positivi su parole comuni
    italiane (stopword) o parole troppo corte per essere distintive."""
    tutti = db.execute("SELECT id, name, type FROM nodes").fetchall()
    parole_domanda = [p.strip(".,?!").lower() for p in domanda.split()
                       if len(p) > 4 and p.strip(".,?!").lower() not in _STOPWORD]
    if not parole_domanda:
        return None

    candidati = set()
    for n in tutti:
        for parola_nodo in n["name"].lower().split():
            parola_nodo = parola_nodo.strip("(),./")
            if parola_nodo in _STOPWORD or len(parola_nodo) < 5:
                continue
            for p in parole_domanda:
                if difflib.SequenceMatcher(None, p, parola_nodo).ratio() > 0.8:
                    candidati.add(n["name"])
                    break

    for nome in candidati:
        ctx = cerca_contesto(db, nome)
        if ctx and ctx.get("fenomeni"):
            return ctx
    return None

def fenomeni_suggeriti(db):
    """Ultima rete di sicurezza: se proprio non si trova nulla, non si lascia
    l'utente con un vicolo cieco. Si mostrano i fenomeni del grafo come punto
    di partenza — l'utente può cliccare e iniziare da lì."""
    rows = db.execute(
        "SELECT id, name, domain, data FROM nodes WHERE type='Fenomeno' ORDER BY name").fetchall()
    return [{"id": r["id"], "nome": r["name"], "dominio": r["domain"],
             "target": _numero_bersaglio(_dati(r["data"]))} for r in rows]

def log_funnel(evento, user_id=None, email=None, meta=None, utm=None):
    """Traccia gli eventi del FUNNEL di conversione (distinti dall'uso in log_domande).
    Eventi canonici: 'signup', 'activation' (Aha Moment), 'paywall_hit', 'checkout', 'paid', 'churn'.
    - user_id/email: chi (email hashata a monte se serve privacy; qui accetta l'id utente)
    - meta: dict JSON con dettagli (es. quale feature ha dato l'Aha, quale paywall)
    - utm: dict con source/medium/campaign/content per l'attribuzione content→paid
    Base per i KPI del pannello: conversione, retention, content→paid. Silenzioso se il DB non c'è."""
    if not DATABASE_URL:
        return None
    try:
        import json as _json
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS funnel_eventi (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                evento TEXT NOT NULL,
                user_id TEXT,
                email TEXT,
                meta JSONB,
                utm_source TEXT, utm_medium TEXT, utm_campaign TEXT, utm_content TEXT
            )
        """)
        # indici per le query del pannello (idempotenti)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funnel_evento ON funnel_eventi(evento)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funnel_ts ON funnel_eventi(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_funnel_user ON funnel_eventi(user_id)")
        u = utm or {}
        cur.execute("""
            INSERT INTO funnel_eventi
              (evento, user_id, email, meta, utm_source, utm_medium, utm_campaign, utm_content)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (
            evento[:40],
            str(user_id)[:80] if user_id else None,
            (email or "")[:160] or None,
            _json.dumps(meta) if meta else None,
            (u.get("source") or "")[:80] or None,
            (u.get("medium") or "")[:80] or None,
            (u.get("campaign") or "")[:120] or None,
            (u.get("content") or "")[:120] or None,
        ))
        fid = cur.fetchone()[0]
        conn.commit(); cur.close(); _release_conn(conn)
        return fid
    except Exception:
        return None

def log_evento(tipo, domanda, fenomeni=None, esito=None):
    """Log minimo per osservabilità. Ritorna id del log per feedback (AC5)."""
    if not DATABASE_URL:
        return None
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS log_domande (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                tipo TEXT, domanda TEXT,
                fenomeni_trovati TEXT, esito TEXT,
                feedback INTEGER, feedback_nota TEXT
            )
        """)
        cur.execute(
            "INSERT INTO log_domande (tipo, domanda, fenomeni_trovati, esito) VALUES (%s,%s,%s,%s) RETURNING id",
            (tipo, domanda[:500], ",".join(fenomeni) if fenomeni else None, esito)
        )
        log_id = cur.fetchone()[0]
        conn.commit(); cur.close(); _release_conn(conn)
        return log_id
    except Exception:
        return None

def _genera_quiz(nome, target, scheda, lang="it"):
    """Genera un quiz con Haiku (chiamata lenta, ~5s). Ritorna il quiz base
    con la risposta corretta all'indice 0 — lo shuffle avviene alla consegna.
    Usato da /quiz con cache: Haiku si paga una volta sola per nodo+lingua."""
    if not scheda:
        return None
    if lang == "en":
        quiz_prompt = f"""Create a quiz about this phenomenon for an F&B professional.
Phenomenon: {nome}
Target number: {target}
Content: {scheda[:400]}

Reply ONLY with valid JSON, no text before or after:
{{"domanda":"...","opzioni":["correct option","wrong option","wrong option"],"corretta":0,"spiegazione":"explanation with the exact mathematical calculation in 2 lines"}}

The correct answer must always be the first option (index 0).
The explanation must include the exact number."""
    elif lang == "es":
        quiz_prompt = f"""Crea un quiz sobre este fenómeno para un profesional F&B.
Fenómeno: {nome}
Número objetivo: {target}
Contenido: {scheda[:400]}

Responde SOLO con JSON válido, ningún texto antes o después:
{{"domanda":"...","opzioni":["opción correcta","opción incorrecta","opción incorrecta"],"corretta":0,"spiegazione":"explicación con el cálculo matemático en 2 líneas"}}

La respuesta correcta debe ser siempre la primera opción (índice 0).
La explicación debe incluir el número exacto."""
    else:
        quiz_prompt = f"""Crea un quiz su questo fenomeno per un professionista F&B.
Fenomeno: {nome}
Numero bersaglio: {target}
Contenuto: {scheda[:400]}

Rispondi SOLO con JSON valido, nessun testo prima o dopo:
{{"domanda":"...","opzioni":["opzione giusta","opzione sbagliata","opzione sbagliata"],"corretta":0,"spiegazione":"spiegazione con il calcolo matematico in 2 righe"}}

La risposta corretta deve essere sempre la prima opzione (indice 0).
La spiegazione deve includere il numero esatto."""
    try:
        raw = _haiku_raw(quiz_prompt)
        if raw:
            import re as _re
            print(f"QUIZ RAW ({nome}): {raw[:300]}", flush=True)
            # rimuove caratteri di controllo che rompono json.loads
            raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
            # cerca il blocco JSON — anche se Haiku aggiunge testo prima/dopo
            m = _re.search(r'\{.*?\}', raw, _re.DOTALL)
            if not m:
                # prova a cercare pattern più ampio
                m = _re.search(r'\{.*\}', raw, _re.DOTALL)
            if m:
                try:
                    quiz_data = json.loads(m.group())
                except Exception as _je:
                    # prova a pulire apostrofi non escaped
                    cleaned = m.group().replace("'", '"')
                    try:
                        quiz_data = json.loads(cleaned)
                    except Exception:
                        print(f"QUIZ PARSE ERROR ({nome}): {_je} | raw: {raw[:300]}", flush=True)
                        return None
                opzioni = quiz_data.get("opzioni", [])
                if not opzioni or len(opzioni) < 2:
                    print(f"QUIZ NO OPZIONI ({nome}): {quiz_data}", flush=True)
                    return None
                return {
                    "domanda": quiz_data.get("domanda", ""),
                    "opzioni": opzioni,
                    "corretta": 0,
                    "spiegazione": quiz_data.get("spiegazione", "")
                }
            else:
                print(f"QUIZ NO JSON ({nome}): raw={raw[:300]}", flush=True)
    except Exception as _e:
        print(f"QUIZ EXCEPTION ({nome}): {_e}", flush=True)
        return None
    return None

_NOME_TRAD = {
    "en": {
        # Fenomeni completi (52)
        "Acidità": "Acidity", "Fermentazione lattica": "Lactic fermentation",
        "Fermentazione acetica": "Acetic fermentation", "Maillard": "Maillard reaction",
        "Reazione di Maillard": "Maillard reaction",
        "Abbassamento crioscopico": "Cryoscopic depression",
        "Punto di congelamento": "Freezing point", "Overrun": "Overrun",
        "Attività dell'acqua": "Water activity",
        "Concentrazione zuccherina": "Sugar concentration",
        "Estrazione caffè": "Coffee extraction", "TDS": "TDS",
        "Solubilità": "Solubility", "Saturazione": "Saturation",
        "Struttura proteica": "Protein structure",
        "Reticolo proteico": "Protein network",
        "Lievitazione chimica": "Chemical leavening",
        "Cottura sous vide": "Sous vide cooking",
        "Temperatura di servizio": "Service temperature",
        "Diluizione": "Dilution", "Bilanciamento": "Balance",
        "Carbonatazione forzata": "Forced carbonation",
        "Rifermentazione": "Refermentation",
        "Caramellizzazione": "Caramelization", "Gelatinizzazione": "Gelatinization",
        "Emulsione": "Emulsion", "Cristallizzazione": "Crystallization",
        "Osmosi": "Osmosis", "Denaturazione": "Denaturation",
        "Carbonatazione": "Carbonation", "Estrazione": "Extraction",
        "Concentrazione": "Concentration", "Idratazione": "Hydration",
        "Struttura del glutine": "Gluten structure", "Lievitazione": "Leavening",
        "Ossidazione": "Oxidation", "Riduzione": "Reduction",
        "Fermentazione alcolica": "Alcoholic fermentation", "Fermentazione": "Fermentation",
        "Distillazione": "Distillation", "Infusione": "Infusion",
        "Macerazione": "Maceration", "Filtrazione": "Filtration",
        "Pastorizzazione": "Pasteurization", "Sterilizzazione": "Sterilization",
        "Calore / cinetica termica": "Heat / thermal kinetics",
        "Pressione": "Pressure", "Viscosità": "Viscosity",
        "Tensione superficiale": "Surface tension", "Diffusione": "Diffusion",
        "Coagulazione": "Coagulation", "Proteolisi": "Proteolysis",
        "Lipolisi": "Lipolysis", "Amidolisi": "Starch hydrolysis",
        "Fermentazione malolattica": "Malolactic fermentation",
        "Invecchiamento": "Aging", "Affinamento": "Maturation",
        "Tostatura": "Roasting", "Affumicatura": "Smoking",
        "Essiccazione": "Drying", "Salatura": "Salting",
        "Fermentazione lattica spontanea": "Wild lactic fermentation",
        "Attività enzimatica": "Enzymatic activity",
        "Reazione di Bruno": "Browning reaction",
        "Struttura": "Structure", "Tessitura": "Texture",
        "Colore": "Color", "Aroma": "Aroma",
        # Sicurezza
        "Zona di pericolo": "Danger zone", "Shelf life": "Shelf life",
        "Aw": "Water activity", "Contaminazione": "Contamination",
        "Atmosfera modificata": "Modified atmosphere",
        # Discipline
        "Bar": "Bar", "Cucina": "Kitchen", "Panificazione": "Baking",
        "Pasticceria": "Pastry", "Gelateria": "Gelato", "Caffè": "Coffee",
        "Vino": "Wine", "Birra": "Beer", "Sicurezza alimentare": "Food safety",
        "Cucina asiatica": "Asian cuisine", "Cucina indiana": "Indian cuisine",
        "Cucina giapponese": "Japanese cuisine",
    },
    "es": {
        # Fenomeni completi (52)
        "Acidità": "Acidez", "Fermentazione lattica": "Fermentación láctica",
        "Fermentazione acetica": "Fermentación acética", "Maillard": "Reacción de Maillard",
        "Reazione di Maillard": "Reacción de Maillard",
        "Abbassamento crioscopico": "Descenso crioscópico",
        "Punto di congelamento": "Punto de congelación", "Overrun": "Overrun",
        "Attività dell'acqua": "Actividad del agua",
        "Concentrazione zuccherina": "Concentración de azúcar",
        "Estrazione caffè": "Extracción de café", "TDS": "TDS",
        "Solubilità": "Solubilidad", "Saturazione": "Saturación",
        "Struttura proteica": "Estructura proteica",
        "Reticolo proteico": "Red proteica",
        "Lievitazione chimica": "Leudado químico",
        "Cottura sous vide": "Cocción sous vide",
        "Temperatura di servizio": "Temperatura de servicio",
        "Diluizione": "Dilución", "Bilanciamento": "Equilibrio",
        "Carbonatazione forzata": "Carbonatación forzada",
        "Rifermentazione": "Refermentación",
        "Caramellizzazione": "Caramelización", "Gelatinizzazione": "Gelatinización",
        "Emulsione": "Emulsión", "Cristallizzazione": "Cristalización",
        "Osmosi": "Ósmosis", "Denaturazione": "Desnaturalización",
        "Carbonatazione": "Carbonatación", "Estrazione": "Extracción",
        "Concentrazione": "Concentración", "Idratazione": "Hidratación",
        "Struttura del glutine": "Estructura del gluten", "Lievitazione": "Leudado",
        "Ossidazione": "Oxidación", "Riduzione": "Reducción",
        "Fermentazione alcolica": "Fermentación alcohólica", "Fermentazione": "Fermentación",
        "Distillazione": "Destilación", "Infusione": "Infusión",
        "Macerazione": "Maceración", "Filtrazione": "Filtración",
        "Pastorizzazione": "Pasteurización", "Sterilizzazione": "Esterilización",
        "Calore / cinetica termica": "Calor / cinética térmica",
        "Pressione": "Presión", "Viscosità": "Viscosidad",
        "Tensione superficiale": "Tensión superficial", "Diffusione": "Difusión",
        "Coagulazione": "Coagulación", "Proteolisi": "Proteólisis",
        "Lipolisi": "Lipólisis", "Amidolisi": "Hidrólisis del almidón",
        "Fermentazione malolattica": "Fermentación maloláctica",
        "Invecchiamento": "Envejecimiento", "Affinamento": "Maduración",
        "Tostatura": "Tostado", "Affumicatura": "Ahumado",
        "Essiccazione": "Secado", "Salatura": "Salazón",
        "Fermentazione lattica spontanea": "Fermentación láctica espontánea",
        "Attività enzimatica": "Actividad enzimática",
        "Reazione di Bruno": "Reacción de pardeamiento",
        "Struttura": "Estructura", "Tessitura": "Textura",
        "Colore": "Color", "Aroma": "Aroma",
        # Sicurezza
        "Zona di pericolo": "Zona de peligro", "Shelf life": "Vida útil",
        "Aw": "Actividad de agua", "Contaminazione": "Contaminación",
        "Atmosfera modificata": "Atmósfera modificada",
        # Discipline
        "Bar": "Bar", "Cucina": "Cocina", "Panificazione": "Panadería",
        "Pasticceria": "Pastelería", "Gelateria": "Heladería", "Caffè": "Café",
        "Vino": "Vino", "Birra": "Cerveza", "Sicurezza alimentare": "Seguridad alimentaria",
        "Cucina asiatica": "Cocina asiática", "Cucina indiana": "Cocina india",
        "Cucina giapponese": "Cocina japonesa",
    }
}


def _traduci_nome(nome, lang, conn=None):
    """Traduce il nome di un fenomeno o disciplina nella lingua richiesta.
    Se non trovato nel dizionario statico, usa Haiku e salva nel DB."""
    if not nome or lang == "it":
        return nome
    # Cerca nel dizionario statico
    tradotto = _NOME_TRAD.get(lang, {}).get(nome)
    if tradotto:
        return tradotto
    # Traduzione lazy via Haiku
    if lang == "en":
        prompt = f"Translate this Italian F&B technical term to English (2-5 words max): {nome}"
    elif lang == "es":
        prompt = f"Traduce este término técnico italiano de F&B al español (2-5 palabras): {nome}"
    else:
        return nome
    try:
        trad = _haiku_raw(prompt, max_tokens=20)
        if trad:
            trad = trad.strip().strip('"').strip("'")
            # Salva nel dizionario statico per questa sessione
            _NOME_TRAD.setdefault(lang, {})[nome] = trad
            return trad
    except Exception:
        pass
    return nome