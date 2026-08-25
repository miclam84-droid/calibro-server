# ============================================================
# builder.py — Recipe Builder AI generativo.
# Genera ricette strutturate attingendo ai dati REALI del grafo:
# fenomeni (con numeri bersaglio), tecniche (con esecuzione),
# abbinamenti aromatici (analogia) e sensoriali (contrasto).
# L'AI compone, ma i numeri e i fenomeni vengono dal grafo — non inventati.
# ============================================================
import json as _j


def _nodi_tecniche(db, disciplina):
    """Tecniche disponibili per una disciplina (o trasversali)."""
    rows = db.execute(
        "SELECT id, name, data FROM nodes WHERE type='Tecnica' ORDER BY name"
    ).fetchall()
    out = []
    for row in rows:
        r = dict(row) if hasattr(row, "keys") else {"id": row[0], "name": row[1], "data": row[2]}
        data = r.get("data") or {}
        if isinstance(data, str):
            try: data = _j.loads(data)
            except: data = {}
        d = data.get("disciplina", "trasversale")
        if disciplina and d not in (disciplina, "trasversale"):
            continue
        out.append({
            "id": r.get("id"),
            "nome": r.get("name"),
            "numeri": data.get("numeri", ""),
            "fenomeni": data.get("fenomeni_sfruttati", []),
        })
    return out


def _fenomeni_disciplina(db, disciplina, limite=12):
    """Fenomeni rilevanti per una disciplina, con numero bersaglio."""
    from contenuto import _numero_bersaglio, _scheda_lang
    rows = db.execute(
        "SELECT id, name, data, domain FROM nodes WHERE type='Fenomeno' ORDER BY name"
    ).fetchall()
    out = []
    for row in rows:
        r = dict(row) if hasattr(row, "keys") else {"id": row[0], "name": row[1], "data": row[2], "domain": row[3]}
        data = r.get("data")
        d = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        # filtro per disciplina se il fenomeno la specifica
        discipline_fen = d.get("discipline", []) or d.get("disciplina", "")
        target = _numero_bersaglio(d) if d else ""
        out.append({
            "id": r.get("id"),
            "nome": r.get("name"),
            "target": target,
        })
    return out[:limite]


def _abbinamenti_ingrediente(db, ingrediente, max_n=6):
    """Abbinamenti per ANALOGIA (composti condivisi) dal grafo Ahn."""
    from urllib.parse import quote
    out = []
    try:
        rows = db.execute(
            """SELECT n.name, (e.data->>'overlap')::numeric AS overlap
               FROM edges e JOIN nodes n ON n.id = e.to_id
               WHERE e.relation='abbinamento_aromatico'
               AND (lower(e.from_id) = lower(?) OR lower(e.from_id) LIKE lower(?))
               ORDER BY overlap DESC NULLS LAST LIMIT ?""",
            (ingrediente, f"%{ingrediente}%", max_n)
        ).fetchall()
        for row in rows:
            r = dict(row) if hasattr(row, "keys") else {"name": row[0], "overlap": row[1]}
            out.append({"ingrediente": r.get("name"), "overlap": float(r.get("overlap") or 0)})
    except Exception:
        pass
    return out



def _fenomeni_pertinenti(db, richiesta, disciplina, limite=10):
    """Sceglie i fenomeni PERTINENTI alla richiesta (non i primi alfabetici).
    Punteggio: match dei termini della richiesta col nome/scheda del fenomeno + affinità disciplina.
    Risolve il problema 'maionese al limone -> Anisakis' (fenomeno a caso preso dai primi 12)."""
    from contenuto import _numero_bersaglio
    import re as _re
    rows = db.execute("SELECT id, name, data, domain FROM nodes WHERE type='Fenomeno'").fetchall()
    # parole chiave dalla richiesta (>2 lettere)
    parole = [w.lower() for w in _re.findall(r"\w+", richiesta or "") if len(w) > 2]
    scored = []
    for row in rows:
        r = dict(row) if hasattr(row, "keys") else {"id": row[0], "name": row[1], "data": row[2], "domain": row[3]}
        data = r.get("data")
        d = data if isinstance(data, dict) else (_j.loads(data) if data else {})
        nome = (r.get("name") or "")
        dom = (r.get("domain") or "")
        # testo del fenomeno su cui matchare (nome + scheda breve)
        testo = (nome + " " + str(d.get("scheda", "") or d.get("descrizione", ""))).lower()
        score = 0
        for p in parole:
            if p in testo:
                score += 3 if p in nome.lower() else 1
        # affinità disciplina: bonus se il fenomeno è della stessa disciplina
        discipline_fen = d.get("discipline", []) or d.get("disciplina", "")
        if disciplina and (disciplina in str(discipline_fen).lower() or disciplina in dom.lower()):
            score += 2
        target = _numero_bersaglio(d) if d else ""
        scored.append((score, {"id": r.get("id"), "nome": nome, "target": target}))
    # ordina per punteggio decrescente; se tutti a 0 (nessun match), fallback ai primi con target
    scored.sort(key=lambda x: x[0], reverse=True)
    pertinenti = [s[1] for s in scored if s[0] > 0][:limite]
    if not pertinenti:  # nessun match: prendi fenomeni con target (meglio che alfabetici a caso)
        pertinenti = [s[1] for s in scored if s[1]["target"]][:limite]
    return pertinenti


def _cerca_piatto_canonico(richiesta):
    """Cerca se la richiesta corrisponde a un piatto canonico noto (mappa verificata).
    Ritorna il dict del piatto {nome, firma, chiave, regione} o None. L'AI non inventa gli ingredienti-firma."""
    try:
        from mappa_italia_regioni import tutti_i_piatti_italia
        req = (richiesta or "").lower()
        piatti = tutti_i_piatti_italia()
        # match: il nome del piatto (o una sua parola forte) compare nella richiesta
        migliore = None
        for p in piatti:
            nome_l = p["nome"].lower()
            # match diretto sul nome completo
            if nome_l in req or req in nome_l:
                return p
            # match su parola forte del nome (>=5 lettere) presente nella richiesta
            parole = [w for w in nome_l.replace("'", " ").split() if len(w) >= 5]
            if parole and all(w in req for w in parole[:2]):
                migliore = p
        return migliore
    except Exception:
        return None


def _blocco_knowledge_tecnico(richiesta, disciplina="cucina", ingredienti=None):
    """Inietta le regole tecniche verificate (grounding) pertinenti alla richiesta.
    Isolato in try/except: se il modulo manca, la generazione continua senza grounding."""
    try:
        from knowledge_tecnico import blocco_grounding
        return blocco_grounding(richiesta, disciplina, ingredienti)
    except Exception:
        return ""


def genera_ricetta(db, richiesta, disciplina="cucina", lang="it"):
    """Genera una ricetta strutturata a partire da una richiesta libera.
    richiesta: es. 'un dolce al cioccolato', 'cocktail al gin agrumato', 'pane con le noci'
    Ritorna dict con la ricetta o {errore}.

    I numeri e i fenomeni vengono dal grafo REALE. L'AI compone la struttura
    ma è vincolata a usare fenomeni/tecniche/numeri forniti nel contesto.
    """
    from ai import chiedi_mistral, estrai_entita

    # 0) è un piatto CANONICO noto? Se sì, uso gli ingredienti-firma VERIFICATI (l'AI non li inventa)
    piatto_canonico = _cerca_piatto_canonico(richiesta)

    # 1) raccogli contesto reale dal grafo
    tecniche = _nodi_tecniche(db, disciplina)
    fenomeni = _fenomeni_pertinenti(db, richiesta, disciplina)  # pertinenti alla richiesta, non alfabetici

    # 2) estrai eventuali ingredienti dalla richiesta per gli abbinamenti
    termini = estrai_entita(richiesta) if richiesta else []
    abbinamenti = []
    for t in termini[:3]:
        ab = _abbinamenti_ingrediente(db, t)
        if ab:
            abbinamenti.append({"ingrediente": t, "abbina_con": ab})

    # 3) costruisci il contesto testuale per l'AI (solo dati reali)
    # nomi tecniche puliti (senza i numeri incorporati) per evitare che l'AI li copi nel campo tecniche
    tec_str = "; ".join(
        f"{t['nome']} [numeri: {t['numeri'][:60]}]" for t in tecniche[:10]
    ) if tecniche else "nessuna tecnica disponibile"
    nomi_tecniche_validi = [t['nome'] for t in tecniche]

    fen_str = "; ".join(
        f"{f['nome']} → {f['target']}" for f in fenomeni[:10] if f['target']
    ) if fenomeni else "nessun fenomeno disponibile"

    abb_str = ""
    if abbinamenti:
        parts = []
        for a in abbinamenti:
            coppie = ", ".join(f"{x['ingrediente']}" for x in a["abbina_con"][:4])
            parts.append(f"{a['ingrediente']} si abbina (composti condivisi) con: {coppie}")
        abb_str = " · ".join(parts)

    LINGUA = {"it": "italiano", "en": "English", "es": "español"}.get(lang, "italiano")
    _termine_var = termine_variante(disciplina, lang)

    prompt = (
        f"Sei un professionista del mestiere ('{disciplina}') che è ANCHE scienziato del cibo. "
        f"Scrivi come se spiegassi una cosa a un collega durante il prep delle 17:30: curioso ma ASCIUTTO, "
        f"frasi corte, mai da professore. Genera UNA ricetta a partire da: \"{richiesta}\".\n\n"
        f"REGOLA FERREA SUI NUMERI: usa ESCLUSIVAMENTE i numeri elencati qui sotto nei FENOMENI e TECNICHE. "
        f"NON inventare temperature, tempi, percentuali o gradi che non sono in questa lista. "
        f"Se un passaggio richiede un numero che NON trovi qui sotto, scrivilo in modo QUALITATIVO "
        f"(es. 'a fuoco basso', 'finché non vela il cucchiaio') SENZA inventare una cifra precisa. "
        f"Un numero sbagliato è molto peggio di nessun numero.\n\n"
        + (
            f"PIATTO CANONICO (verificato): '{piatto_canonico['nome']}' ({piatto_canonico.get('regione','Italia')}). "
            f"Gli ingredienti-firma OBBLIGATORI sono: {', '.join(piatto_canonico['firma'])}. "
            f"USA QUESTI ingredienti (puoi aggiungere solo sale/acqua/olio di supporto). "
            f"NON sostituire mai un ingrediente-firma con un'alternativa estera (es. MAI 'bacon' al posto del guanciale, "
            f"MAI 'panna' se non è nella firma). Rispetta la tradizione della regione.\n\n"
            if piatto_canonico else ""
        )
        + _blocco_knowledge_tecnico(richiesta, disciplina)
        + f"DATI REALI DISPONIBILI (l'unica fonte di numeri consentita):\n"
        f"FENOMENI CON NUMERI BERSAGLIO: {fen_str}\n\n"
        f"TECNICHE DISPONIBILI: {tec_str}\n\n"
        + (f"ABBINAMENTI AROMATICI (per analogia): {abb_str}\n\n" if abb_str else "")
        + f"VOCE DEI TESTI (regole obbligatorie):\n"
        f"- La 'descrizione' NON è una definizione da manuale. Apri con un PROBLEMA reale del banco "
        f"(es. 'La carbonara ti diventa una frittata? Non è colpa tua, è la temperatura.').\n"
        f"- Il 'punto_critico' nomina la VARIABILE che il professionista confonde, col numero SE è nei dati sopra.\n"
        f"- L''esperimento' è una prova semplice da fare domani al banco per capire (non teoria).\n"
        f"- Il 'limite' dice quando il numero-bersaglio NON basta e decide il palato/l'occhio.\n"
        f"- Il 'twist' è UN consiglio di variazione/rivisitazione della ricetta ({_termine_var}): "
        f"una modifica concreta e sensata che un professionista proverebbe (nuovo ingrediente, tecnica, presentazione), "
        f"spiegata in 1-2 frasi asciutte col PERCHÉ funziona.\n\n"
        f"REGOLA FONDAMENTALE SUL PROCEDIMENTO (la ricetta deve essere VERA, non un abbozzo):\n"
        f"- Ogni passaggio deve essere DETTAGLIATO come in una vera ricetta professionale, non generico. "
        f"MALE: 'soffriggi la cipolla finché trasparente'. BENE: 'Trita finemente la cipolla e falla appassire "
        f"in 40 ml d'olio a fuoco medio-basso per 8-10 minuti, mescolando, finché diventa traslucida e dolce senza colorire'.\n"
        f"- Richiama le QUANTITÀ degli ingredienti dentro i passaggi in cui si usano (es. 'aggiungi i 500 g di pesce'), "
        f"non dire mai solo 'aggiungi il pesce' senza la quantità.\n"
        f"- Dai il TEMPO e il SEGNALE SENSORIALE di ogni passo (quanti minuti, e come si capisce che è pronto: "
        f"'finché il fondo non vela il cucchiaio', 'finché i bordi si arricciano', 'finché sfrigola e profuma').\n"
        f"- Usa da 6 a 10 passaggi: una ricetta vera non si liquida in 4 righe. Ogni passo è un'azione concreta e completa.\n"
        f"- Resta comunque ASCIUTTO e da professionista: dettagliato non vuol dire prolisso, vuol dire preciso.\n\n"
        f"Rispondi in {LINGUA} SOLO con un oggetto JSON (nessun testo extra) in questo formato ESATTO:\n"
        f'{{"nome": "...", "descrizione": "apri con un problema del banco, 1-2 frasi asciutte", '
        f'"ingredienti": [{{"nome": "...", "quantita": "...", "unita": "..."}}], '
        f'"procedimento": [{{"n": 1, "testo": "passaggio operativo chiaro e specifico", "numero_chiave": "es. 80-85 gradi oppure null se il passo non ha un numero critico"}}], '
        f'"applicazioni": ["dove si usa questa preparazione", ...], '
        f'"tempo_prep": minuti_interi, "tempo_cottura": minuti_interi, '
        f'"difficolta": "facile|media|difficile", "porzioni": "es. 4 persone", '
        f'"fenomeni": ["nome fenomeno usato", ...], '
        f'"tecniche": ["nome tecnica usata", ...], '
        f'"numeri": {{"parametro": "valore con unità", ...}}, '
        f'"punto_critico": "la variabile che si confonde e perché si sbaglia, con un numero", '
        f'"esperimento": "una prova semplice da fare al banco per capire il fenomeno (1 frase concreta)", '
        f'"limite": "quando il numero-bersaglio non basta e decide il palato/occhio (1 frase)", '
        f'"twist": "un consiglio di {_termine_var} concreto col perché (1-2 frasi)", '
        f'"abbinamenti": {{"analogia": "...", "contrasto": "..."}}}}\n\n'
        f"I numeri devono venire dai fenomeni/tecniche forniti sopra. "
        f"IMPORTANTE per il campo 'numeri': le descrizioni-bersaglio dei fenomeni contengono spesso cifre "
        f"dentro le frasi (es. 'shakera 10-15s', 'sour 2:1:1', 'pH 4.6', 'vicino 0°C'). ESTRAI quelle cifre "
        f"e mettile in 'numeri' come coppie parametro→valore (es. {{\"tempo shake\": \"10-15s\", \"struttura sour\": \"2:1:1\"}}). "
        f"Se un fenomeno dà solo indicazioni qualitative senza cifre, NON inventare numeri per quel parametro. "
        f"Il PROCEDIMENTO deve essere una sequenza di passaggi REALI e specifici: ogni passo che tocca "
        f"un parametro critico DEVE avere il numero_chiave preso dai fenomeni sopra. "
        f"Le APPLICAZIONI dicono dove si usa la preparazione. "
        f"Niente markdown, solo JSON."
    )

    try:
        raw = chiedi_mistral(prompt, usa_tools=False)
        if not raw:
            return {"errore": "generazione fallita — nessuna risposta"}
        # estrai il JSON
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"errore": "output non-JSON", "raw": raw[:200]}
        blob = m.group(0)
        try:
            ricetta = _j.loads(blob)
        except _j.JSONDecodeError:
            # 1° tentativo: strict=False tollera newline/caratteri di controllo dentro le stringhe (causa comune)
            try:
                ricetta = _j.loads(blob, strict=False)
            except _j.JSONDecodeError:
                # 2° tentativo: riparazione virgole (mancanti/in eccesso)
                fix = re.sub(r",\s*([}\]])", r"\1", blob)
                fix = re.sub(r'([}\]])\s*\n(\s*["{\[])', r'\1,\n\2', fix)
                try:
                    ricetta = _j.loads(fix, strict=False)
                except _j.JSONDecodeError:
                    return {"errore": "JSON non recuperabile", "raw": blob[:400]}
        # pulizia: normalizza i nomi tecniche (l'AI a volte copia la label con i numeri)
        if "tecniche" in ricetta and isinstance(ricetta["tecniche"], list):
            pulite = []
            for t in ricetta["tecniche"]:
                if not isinstance(t, str):
                    continue
                # rimuovi tutto dopo '[' o '(' (i numeri incorporati)
                nome_pulito = t.split("[")[0].split("(numeri")[0].strip()
                # match con un nome valido se possibile
                match = next((v for v in nomi_tecniche_validi if v.lower() in nome_pulito.lower() or nome_pulito.lower() in v.lower()), nome_pulito)
                pulite.append(match)
            ricetta["tecniche"] = pulite
        # FALLBACK: se l'AI ha lasciato le tecniche vuote (o quasi), aggancia quelle collegate
        # ai FENOMENI della ricetta tramite il grafo (arco realizzato_da) - non match di testo fragile.
        if not ricetta.get("tecniche") or len(ricetta.get("tecniche", [])) < 2:
            agganciate = list(ricetta.get("tecniche") or [])
            fen_ricetta = ricetta.get("fenomeni", [])
            if fen_ricetta:
                try:
                    # trovo gli id dei fenomeni della ricetta (per nome)
                    ph = ",".join("?" for _ in fen_ricetta)
                    fen_rows = db.execute(
                        f"SELECT id FROM nodes WHERE type='Fenomeno' AND name IN ({ph})",
                        tuple(fen_ricetta)
                    ).fetchall()
                    fen_ids = [r["id"] for r in fen_rows]
                    if fen_ids:
                        ph2 = ",".join("?" for _ in fen_ids)
                        # tecniche collegate a quei fenomeni (arco realizzato_da: fenomeno -> tecnica)
                        tec_rows = db.execute(
                            f"""SELECT DISTINCT n.name FROM edges e JOIN nodes n ON e.to_id = n.id
                                WHERE e.from_id IN ({ph2}) AND e.relation='realizzato_da' AND n.type='Tecnica'
                                AND n.domain=? LIMIT 6""",
                            tuple(fen_ids) + (disciplina,)
                        ).fetchall()
                        for tr in tec_rows:
                            if tr["name"] not in agganciate:
                                agganciate.append(tr["name"])
                except Exception:
                    pass
            if agganciate:
                ricetta["tecniche"] = agganciate[:5]
        ricetta["_generata"] = True
        ricetta["disciplina"] = disciplina
        ricetta["_disclaimer"] = "Ricetta generata dall'AI sui dati scientifici del grafo. Verifica i numeri al banco."
        return ricetta
    except _j.JSONDecodeError as e:
        return {"errore": f"JSON non valido: {e}", "raw": raw[:300] if 'raw' in dir() else ""}
    except Exception as e:
        return {"errore": str(e)}



def termine_variante(disciplina, lang="it"):
    """Il termine giusto per una variante secondo la disciplina.
    Bar/drink = 'Twist' (termine del mestiere); cucina/pasticceria/pane = 'Rivisitazione'.
    Mai hardcodare un solo termine ovunque (regola Michele)."""
    d = (disciplina or "").lower()
    bar = d in ("bar", "cocktail", "drink", "caffetteria", "birra", "vino")
    if lang == "en":
        return "Twist" if bar else "Variation"
    if lang == "es":
        return "Twist" if bar else "Reinterpretación"
    return "Twist" if bar else "Rivisitazione"


def genera_twist(ricetta_madre, modifica, lang="it"):
    """Genera una variante (twist) di una ricetta esistente applicando una modifica.
    ricetta_madre: dict con la ricetta originale (nome, ingredienti, procedimento, fenomeni, numeri...)
    modifica: es. "rendi vegano", "versione per il bar", "sostituisci il burro con olio"
    Mantiene i fenomeni pertinenti, adatta ingredienti/procedimento, ricalcola i numeri dove serve.
    """
    import json as _jj, re as _re
    from ai import chiedi_mistral
    LINGUA = {"it":"italiano","en":"English","es":"español"}.get(lang,"italiano")
    _termine = termine_variante(ricetta_madre.get("disciplina",""), lang)
    ingr = ricetta_madre.get("ingredienti",[])
    ingr_str = ", ".join(f"{i.get('quantita','')}{i.get('unita','')} {i.get('nome','')}" for i in ingr if isinstance(i,dict))
    num = ricetta_madre.get("numeri",{})
    num_str = "; ".join(f"{k}: {v}" for k,v in num.items()) if isinstance(num,dict) else ""
    fen = ricetta_madre.get("fenomeni",[])
    prompt = (
        f"Sei un consulente scientifico F&B. Parti da questa ricetta e applica UNA modifica creando una VARIANTE.\n\n"
        f"RICETTA MADRE: {ricetta_madre.get('nome','')}\n"
        f"INGREDIENTI: {ingr_str}\n"
        f"NUMERI BERSAGLIO: {num_str}\n"
        f"FENOMENI (mantieni quelli ancora pertinenti): {', '.join(fen) if isinstance(fen,list) else ''}\n"
        f"PUNTO CRITICO: {ricetta_madre.get('punto_critico','')}\n\n"
        f"MODIFICA RICHIESTA: {modifica}\n\n"
        f"Questa variante si chiama un '{_termine}' (usa questo termine nella disciplina). "
        f"Genera la variante in {LINGUA}. Adatta ingredienti e procedimento alla modifica, "
        f"ricalcola i numeri SOLO se la modifica li cambia, mantieni i fenomeni ancora validi. "
        f"Rispondi SOLO con questo JSON (niente altro):\n"
        f'{{"nome":"nome della variante (deve richiamare la modifica)","descrizione":"1-2 frasi",'
        f'"ingredienti":[{{"nome":"...","quantita":"...","unita":"..."}}],'
        f'"procedimento":[{{"n":1,"testo":"...","numero_chiave":"numero o null"}}],'
        f'"fenomeni":["fen-..."],"numeri":{{"parametro":"valore"}},'
        f'"punto_critico":"...","applicazioni":["dove si usa in un menu"],'
        f'"tempo_prep":30,"tempo_cottura":0,"difficolta":"media","porzioni":"4"}}'
    )
    try:
        raw = chiedi_mistral(prompt, usa_tools=False)
        if not raw:
            return {"errore":"generazione twist fallita"}
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if not m:
            return {"errore":"output non-JSON","raw":raw[:200]}
        testo = _re.sub(r",\s*([}\]])", r"\1", m.group(0))
        variante = _jj.loads(testo)
        variante["_twist"] = True
        variante["disciplina"] = ricetta_madre.get("disciplina","")
        return variante
    except Exception as e:
        return {"errore":str(e)}


def traduci_campi_ricetta(ricetta, lang):
    """Traduce i campi testuali di una ricetta (dict) in 'en' o 'es' via Haiku.
    Ritorna dict {nome, procedimento, applicazioni, punto_critico} tradotti.
    Strategia robusta: passi in 1 chiamata con separatore @@@, fallback passo-per-passo.
    Questo chiude il flusso TRILINGUE alla creazione: nessun debito traduzioni a valle."""
    from ai import _haiku_raw
    lname = {"en": "English", "es": "Spanish"}.get(lang, "English")
    nome = ricetta.get("nome", "")
    proc = ricetta.get("procedimento", []) or []
    appl = ricetta.get("applicazioni", []) or []
    pc = ricetta.get("punto_critico", "") or ""

    def _one(testo):
        if not testo or not str(testo).strip():
            return ""
        out = _haiku_raw(f"Translate this Italian cooking text to {lname}. Keep numbers and units. "
                         f"Return ONLY the translation on a single line, no quotes:\n{testo}")
        return (out or "").strip().strip('"').strip()

    # passi in una chiamata sola con separatore @@@
    passi = [p.get("testo", "") for p in proc if isinstance(p, dict)]
    passi_tr = []
    if passi:
        joined = "\n@@@\n".join(passi)
        out = _haiku_raw(
            f"Translate to {lname} each cooking step. Steps are separated by a line with @@@. "
            f"Keep EXACTLY the same number of steps and the same @@@ separators. Keep numbers/units. "
            f"Return ONLY the translated steps with @@@ between them:\n\n{joined}") or ""
        passi_tr = [x.strip() for x in out.split("@@@") if x.strip()]
        if len(passi_tr) != len(passi):  # fallback affidabile
            passi_tr = [_one(x) for x in passi]

    proc_tr = []
    idx = 0
    for p in proc:
        if isinstance(p, dict):
            np = dict(p)
            if idx < len(passi_tr) and passi_tr[idx]:
                np["testo"] = passi_tr[idx]
            proc_tr.append(np)
            idx += 1

    return {
        "nome": _one(nome) or nome,
        "procedimento": proc_tr,
        "applicazioni": [_one(a) or a for a in appl if isinstance(a, str)],
        "punto_critico": _one(pc) if pc else "",
    }


def genera_ricetta_trilingue(db, richiesta, disciplina="cucina"):
    """Genera una ricetta IN ITALIANO e subito le traduzioni EN/ES dei campi testuali.
    Ritorna la ricetta con i campi *_en e *_es pronti da salvare. Chiude il flusso trilingue
    alla CREAZIONE (regola: la traduzione va nel flusso, non alla fine)."""
    ric = genera_ricetta(db, richiesta, disciplina=disciplina, lang="it")
    if ric.get("errore"):
        return ric
    for lang in ("en", "es"):
        try:
            tr = traduci_campi_ricetta(ric, lang)
            ric[f"nome_{lang}"] = tr["nome"]
            ric[f"procedimento_{lang}"] = tr["procedimento"]
            ric[f"applicazioni_{lang}"] = tr["applicazioni"]
            ric[f"punto_critico_{lang}"] = tr["punto_critico"]
        except Exception:
            pass  # se una lingua fallisce, la ricetta IT resta valida; traducibile dopo
    ric["_trilingue"] = True
    return ric

