# ============================================================
# ai.py — helper AI condivisi: chiamate a Mistral/Claude/Haiku,
# ricerca contesto nel grafo, costruzione prompt, estrazione entità,
# traduzione schede. Usato da app.py e dai blueprint (chat/lezione/api).
# Dipende da: db (carica_grafo/_dati), contenuto (_scheda_lang/
# _numero_bersaglio/_pulisci_traduzione), config (DATABASE_URL).
# ============================================================
import os, json
import ai_gateway as GW

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
    hit = db.execute(
        "SELECT * FROM nodes WHERE lower(name) LIKE ? ORDER BY "
        "CASE type WHEN 'Fenomeno' THEN 0 WHEN 'Prodotto' THEN 1 "
        "WHEN 'Errore' THEN 2 ELSE 3 END LIMIT 8", (t,)).fetchall()
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
                      "cristallizzazione_t","proteine_pct","note","fonte"):
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
            f"Ingredienti di stagione ora disponibili: {_frutti}.\n"
            f"Quando suggerisci abbinamenti o ingredienti, usa SOLO prodotti di stagione "
            f"a meno che la domanda non riguardi esplicitamente prodotti fuori stagione.\n\n"
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
            "- Tono da collega a collega: il professionista sa gia fare il suo lavoro, "
            "tu gli mostri il perche fisico. Niente lezioni, niente ovvieta.\n"
            "- Mostra la connessione cross-disciplina quando aggiunge valore, in modo naturale.\n"
            "- Se la domanda ha numeri propri dell'utente (ml, grammi, gradi, percentuali), "
            "usa il tool 'calcola' per dare risultati esatti.\n"
            "- Struttura la risposta in questo formato ESATTO (usa questi label in maiuscolo seguiti da due punti):\n"
            "PROBLEMA: [una frase — la causa fisica precisa, non una diagnosi vaga]\n"
            "PERCHÉ: [meccanismo fisico o chimico verificato, max 2 frasi. Solo fatti certi]\n"
            "NUMERO: [il numero bersaglio dal contesto. Se non esiste nel contesto, dai un range scientifico verificato — mai inventare]\n"
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

def chiedi_mistral(prompt, history=None):
    """Nome storico mantenuto — ora usa AI Gateway route_chat con fallback automatico."""
    import ai_gateway as GW
    try:
        out = GW.route_chat(prompt, tools=_TOOLS, history=history)
        if out:
            return out
    except Exception as e:
        print(f"[GW] route_chat fallito in chiedi_mistral: {e}", flush=True)
    return None
