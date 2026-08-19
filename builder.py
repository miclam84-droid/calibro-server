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


def genera_ricetta(db, richiesta, disciplina="cucina", lang="it"):
    """Genera una ricetta strutturata a partire da una richiesta libera.
    richiesta: es. 'un dolce al cioccolato', 'cocktail al gin agrumato', 'pane con le noci'
    Ritorna dict con la ricetta o {errore}.

    I numeri e i fenomeni vengono dal grafo REALE. L'AI compone la struttura
    ma è vincolata a usare fenomeni/tecniche/numeri forniti nel contesto.
    """
    from ai import chiedi_mistral, estrai_entita

    # 1) raccogli contesto reale dal grafo
    tecniche = _nodi_tecniche(db, disciplina)
    fenomeni = _fenomeni_disciplina(db, disciplina)

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

    prompt = (
        f"Sei un consulente scientifico F&B. Genera UNA ricetta per la disciplina '{disciplina}' "
        f"a partire da questa richiesta: \"{richiesta}\".\n\n"
        f"USA SOLO questi dati REALI (non inventare numeri o fenomeni):\n"
        f"FENOMENI DISPONIBILI CON NUMERI BERSAGLIO: {fen_str}\n\n"
        f"TECNICHE DISPONIBILI: {tec_str}\n\n"
        + (f"ABBINAMENTI AROMATICI (per analogia): {abb_str}\n\n" if abb_str else "")
        + f"Rispondi in {LINGUA} SOLO con un oggetto JSON (nessun testo extra) in questo formato ESATTO:\n"
        f'{{"nome": "...", "descrizione": "1-2 frasi sul principio scientifico", '
        f'"ingredienti": [{{"nome": "...", "quantita": "...", "unita": "..."}}], '
        f'"procedimento": [{{"n": 1, "testo": "passaggio operativo chiaro e specifico", "numero_chiave": "es. 80-85 gradi oppure null se il passo non ha un numero critico"}}], '
        f'"applicazioni": ["dove si usa questa preparazione", ...], '
        f'"tempo_prep": minuti_interi, "tempo_cottura": minuti_interi, '
        f'"difficolta": "facile|media|difficile", "porzioni": "es. 4 persone", '
        f'"fenomeni": ["nome fenomeno usato", ...], '
        f'"tecniche": ["nome tecnica usata", ...], '
        f'"numeri": {{"parametro": "valore con unità", ...}}, '
        f'"punto_critico": "il punto dove si sbaglia e perché, con un numero", '
        f'"abbinamenti": {{"analogia": "...", "contrasto": "..."}}}}\n\n'
        f"I numeri devono venire dai fenomeni/tecniche forniti sopra. "
        f"Il PROCEDIMENTO deve essere una sequenza di passaggi REALI e specifici: ogni passo che tocca "
        f"un parametro critico DEVE avere il numero_chiave preso dai fenomeni sopra. "
        f"Le APPLICAZIONI dicono dove si usa la preparazione. "
        f"Il punto critico deve citare un numero specifico. Niente markdown, solo JSON."
    )

    try:
        raw = chiedi_mistral(prompt)
        if not raw:
            return {"errore": "generazione fallita — nessuna risposta"}
        # estrai il JSON
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"errore": "output non-JSON", "raw": raw[:200]}
        ricetta = _j.loads(m.group(0))
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
        ricetta["_generata"] = True
        ricetta["disciplina"] = disciplina
        ricetta["_disclaimer"] = "Ricetta generata dall'AI sui dati scientifici del grafo. Verifica i numeri al banco."
        return ricetta
    except _j.JSONDecodeError as e:
        return {"errore": f"JSON non valido: {e}", "raw": raw[:300] if 'raw' in dir() else ""}
    except Exception as e:
        return {"errore": str(e)}
