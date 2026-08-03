# ============================================================
# foto.py — Pipeline foto → analisi scientifica
# Flusso: immagine → visione (gpt-4o-mini) → lista ingredienti/bottiglie
#         → matching sul grafo (esatto + alias + fuzzy) → output ricco
#         (composti condivisi, abbinamenti, fenomeni, numero-bersaglio)
#
# Dipende da: ai_gateway (route_vision), db (carica_grafo/_dati),
#             contenuto (_scheda_lang/_numero_bersaglio), ai (costruisci_prompt/chiedi_mistral)
# ============================================================
import re
import difflib

# ── ALIAS: nomi comuni → nome nel grafo (case-insensitive) ──────────────────
# Il dataset Ahn è prevalentemente in inglese. Mappiamo i termini comuni
# IT/EN/ES ai nomi nel grafo. Aggiungi alias man mano che si scoprono gap.
ALIAS = {
    # Italiano → EN grafo
    "aglio": "garlic", "cipolla": "onion", "cipolla rossa": "red onion",
    "pomodoro": "tomato", "basilico": "basil", "prezzemolo": "parsley",
    "rosmarino": "rosemary", "timo": "thyme", "origano": "oregano",
    "salvia": "sage", "lavanda": "lavender",
    "burro": "butter", "panna": "cream", "latte": "milk",
    "uova": "egg", "uovo": "egg",
    "farina": "wheat flour", "lievito": "yeast", "sale": "salt",
    "pepe": "black pepper", "pepe nero": "black pepper",
    "olio d'oliva": "olive oil", "olio di oliva": "olive oil",
    "aceto": "white wine vinegar", "aceto balsamico": "balsamic vinegar",
    "miele": "honey", "zenzero": "ginger", "cannella": "cinnamon",
    "vaniglia": "vanilla", "cioccolato": "chocolate",
    "fragola": "strawberry", "lampone": "raspberry",
    "pesca": "peach", "albicocca": "apricot", "mela": "apple",
    "pera": "pear", "arancia": "orange", "pompelmo": "grapefruit",
    "banana": "banana", "ananas": "pineapple", "mango": "mango",
    "fico": "fig", "uva": "grape", "melograno": "pomegranate",
    "cocco": "coconut", "mandorla": "almond", "nocciola": "hazelnut",
    "noci": "walnut", "pistacchio": "pistachio",
    "caffè": "coffee", "caffe": "coffee", "tè": "tea", "te": "tea",
    "cioccolato fondente": "dark chocolate",
    "mela verde": "green apple", "lime": "lime", "limone": "lemon",
    "menta": "mint", "menta piperita": "peppermint",
    "peperoncino": "chili pepper", "paprika": "paprika",
    "curcuma": "turmeric", "cardamomo": "cardamom",
    "anice": "anise", "finocchio": "fennel",
    "cetriolo": "cucumber", "sedano": "celery", "carota": "carrot",
    "zucchine": "zucchini", "melanzana": "eggplant",
    "peperone": "bell pepper", "peperone rosso": "red bell pepper",
    "spinaci": "spinach", "rucola": "arugula",
    "parmigiano": "parmesan", "mozzarella": "mozzarella",
    "ricotta": "ricotta", "pecorino": "pecorino",
    "prosciutto": "prosciutto", "pancetta": "bacon",
    "salmone": "salmon", "tonno": "tuna",
    "sciroppo di zucchero": "sugar",
    "sciroppo": "sugar",
    "simple syrup": "sugar",
    "angostura": "bitter",
    "bitter": "bitter",
    "acqua tonica": "tonic water",
    "tonica": "tonic water",
    "ginger beer": "ginger beer",
    "ginger ale": "ginger beer",
    "san pellegrino": "sparkling water",
    "seltz": "sparkling water",
    "grasso di maiale": "lard",
    "lardo": "lard",
    "pancetta": "bacon",
    "guanciale": "pork",
    "farina 00": "wheat flour",
    "farina 0": "wheat flour",
    "manitoba": "wheat flour",
    "lievito di birra": "yeast",
    "lievito madre": "sourdough",
    "lievito secco": "yeast",
    "panna da montare": "cream",
    "panna fresca": "cream",
    "latte intero": "milk",
    "latte parzialmente scremato": "milk",
    "pecorino": "pecorino cheese",
    "grana padano": "parmesan",
    "aceto di vino bianco": "white wine vinegar",
    "aceto di vino rosso": "red wine vinegar",
    "aceto di mele": "apple cider vinegar",
    "limone giallo": "lemon",
    "succo di limone": "lemon",
    "succo di lime": "lime",
    # Bottiglie / distillati → categorie F&B
    "whiskey": "whisky", "bourbon": "bourbon whiskey",
    "whisky": "whisky", "single malt": "whisky",
    "vodka": "vodka", "gin": "gin", "rum": "rum",
    "tequila": "tequila", "mezcal": "mezcal",
    "brandy": "brandy", "cognac": "cognac",
    "grappa": "grappa", "amaro": "amaro",
    "campari": "campari", "aperol": "aperol",
    "vermouth": "vermouth", "vermouth rosso": "vermouth",
    "prosecco": "white wine", "champagne": "white wine",
    "vino rosso": "red wine", "vino bianco": "white wine",
    "birra": "beer", "ipa": "beer", "lager": "beer",
    "acquavite": "brandy",
    # Spagnolo → EN grafo
    "ajo": "garlic", "cebolla": "onion", "tomate": "tomato",
    "albahaca": "basil", "mantequilla": "butter", "leche": "milk",
    "harina": "wheat flour", "levadura": "yeast", "azúcar": "sugar",
    "azucar": "sugar", "miel": "honey", "aceite de oliva": "olive oil",
    "pimienta": "black pepper", "canela": "cinnamon",
    "jengibre": "ginger", "limon": "lemon", "lima": "lime",
    "naranja": "orange", "fresa": "strawberry",
}

# Nomi che la visione restituisce in inglese già corretti
CANONICAL_EN = {
    "garlic", "onion", "tomato", "basil", "butter", "cream", "milk",
    "egg", "eggs", "wheat flour", "yeast", "salt", "black pepper",
    "olive oil", "honey", "ginger", "cinnamon", "vanilla", "chocolate",
    "strawberry", "raspberry", "lemon", "lime", "orange", "mint",
    "coffee", "sugar", "whisky", "gin", "rum", "vodka", "tequila",
    "beer", "red wine", "white wine", "vermouth", "chocolate",
}


def _normalizza(termine: str) -> str:
    """Lowercase + strip + collassa spazi."""
    return re.sub(r"\s+", " ", termine.strip().lower())


def _trova_nodo(db, termine: str):
    """Cerca il nodo ingrediente nel grafo con 3 livelli:
    1. match esatto sul nome normalizzato
    2. alias hardcoded (IT/ES → EN)
    3. fuzzy match (SequenceMatcher ≥ 0.85)
    Restituisce (node_row, metodo) o (None, None)."""
    t = _normalizza(termine)

    # 1) esatto
    row = db.execute(
        "SELECT * FROM nodes WHERE lower(name)=? AND type='Ingrediente' LIMIT 1", (t,)
    ).fetchone()
    if row:
        return row, "esatto"

    # 2) alias
    alias_t = ALIAS.get(t)
    if alias_t:
        row = db.execute(
            "SELECT * FROM nodes WHERE lower(name)=? AND type='Ingrediente' LIMIT 1",
            (alias_t.lower(),)
        ).fetchone()
        if row:
            return row, "alias"

    # 3) fuzzy sui nomi dei nodi ingrediente
    candidati = db.execute(
        "SELECT * FROM nodes WHERE type='Ingrediente'"
    ).fetchall()
    best_ratio, best_row = 0, None
    for c in candidati:
        ratio = difflib.SequenceMatcher(None, t, c["name"].lower()).ratio()
        if ratio > best_ratio:
            best_ratio, best_row = ratio, c
    if best_ratio >= 0.85:
        return best_row, f"fuzzy({best_ratio:.2f})"

    return None, None


def _abbinamenti_tra(db, nodi_ids: list, max_pairs: int = 5) -> list:
    """Coppie di ingredienti con overlap aromatico alto tra i nodi trovati.
    Gli abbinamenti sono edge con relation='abbinamento_aromatico', overlap in data->>'overlap'."""
    if len(nodi_ids) < 2:
        return []
    pairs = []
    for i in range(len(nodi_ids)):
        for j in range(i + 1, len(nodi_ids)):
            a, b = nodi_ids[i], nodi_ids[j]
            row = db.execute(
                """SELECT (data->>'overlap')::numeric AS overlap
                   FROM edges
                   WHERE relation='abbinamento_aromatico'
                   AND ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?))
                   LIMIT 1""",
                (a, b, b, a)
            ).fetchone()
            if row:
                ov = row["overlap"] if hasattr(row,"keys") else row[0]
                pairs.append({"a": a, "b": b, "overlap": float(ov or 0), "score": float(ov or 0)})
    pairs.sort(key=lambda x: x["overlap"] or 0, reverse=True)
    return pairs[:max_pairs]


def _fenomeni_rilevanti(db, nodi_ids: list) -> list:
    """Fenomeni collegati agli ingredienti trovati."""
    seen = set()
    fenomeni = []
    for nid in nodi_ids:
        for e in db.execute(
            "SELECT to_id FROM edges WHERE from_id=? AND relation='si_manifesta_in'", (nid,)
        ).fetchall():
            fid = e["to_id"]
            if fid in seen:
                continue
            seen.add(fid)
            f = db.execute(
                "SELECT id, name, data FROM nodes WHERE id=? AND type='Fenomeno'", (fid,)
            ).fetchone()
            if f:
                fenomeni.append(f)
    return fenomeni[:4]


def analizza_foto(image_bytes: bytes, media_type: str = "image/jpeg",
                  lang: str = "it") -> dict:
    """Entry point della pipeline.
    Restituisce dict con:
      - ingredienti_riconosciuti: [{termine, nodo, metodo}]
      - ingredienti_sconosciuti: [termini non matchati]
      - abbinamenti: coppie con overlap aromatico
      - fenomeni: fenomeni fisici collegati
      - output_scientifico: testo ricco generato dall'AI
      - meta: {lang, coverage, totale_riconosciuti}
    """
    import ai_gateway as GW
    from db import carica_grafo, _dati
    from contenuto import _scheda_lang, _numero_bersaglio

    PROMPT_LINGUA = {
        "it": "italiano",
        "en": "English",
        "es": "español",
    }.get(lang, "italiano")

    # ── 1) VISIONE: estrai ingredienti/bottiglie dalla foto ──────────────────
    prompt_vision = (
        f"Analizza questa immagine e identifica TUTTI gli ingredienti alimentari "
        f"o le bottiglie visibili. "
        f"Restituisci SOLO un elenco JSON nel formato: "
        f'[{{"nome": "...", "tipo": "ingrediente|bottiglia", "certezza": "alta|media|bassa"}}] '
        f"con i nomi in {PROMPT_LINGUA}. "
        f"Se è una bottiglia, includi anche la categoria (gin, rum, vino rosso, birra IPA, ecc.). "
        f"Niente testo extra, solo il JSON."
    )
    try:
        raw = GW.route_vision(image_bytes, prompt_vision, media_type=media_type)
        # estrai il JSON dalla risposta
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        items = __import__("json").loads(m.group(0)) if m else []
    except Exception as e:
        return {"errore": f"visione: {e}", "output_scientifico": None}

    # filtra solo alta/media certezza
    items = [i for i in items if isinstance(i, dict)
             and i.get("certezza", "alta") in ("alta", "media")]

    # ── 2) MATCHING: termini → nodi grafo ────────────────────────────────────
    db = carica_grafo()
    riconosciuti = []
    sconosciuti = []

    for item in items:
        nome = item.get("nome", "").strip()
        if not nome:
            continue
        nodo, metodo = _trova_nodo(db, nome)
        if nodo:
            riconosciuti.append({
                "termine": nome,
                "nodo_id": nodo["id"],
                "nodo_nome": nodo["name"],
                "metodo": metodo,
                "tipo": item.get("tipo", "ingrediente"),
            })
        else:
            sconosciuti.append(nome)

    nodi_ids = [r["nodo_id"] for r in riconosciuti]

    # ── 3) ABBINAMENTI AROMATICI tra ingredienti trovati ─────────────────────
    abbinamenti_raw = _abbinamenti_tra(db, nodi_ids)
    # arricchisci con i nomi
    abbinamenti = []
    for p in abbinamenti_raw:
        na = db.execute("SELECT name FROM nodes WHERE id=?", (p["a"],)).fetchone()
        nb = db.execute("SELECT name FROM nodes WHERE id=?", (p["b"],)).fetchone()
        abbinamenti.append({
            "a": na["name"] if na else p["a"],
            "b": nb["name"] if nb else p["b"],
            "overlap": p["overlap"],
            "perche": f"condividono {int(p['overlap'] or 0)} composti aromatici",
        })

    # ── 4) FENOMENI collegati ─────────────────────────────────────────────────
    fenomeni_rows = _fenomeni_rilevanti(db, nodi_ids)
    fenomeni = []
    for f in fenomeni_rows:
        nd = _dati(f["data"])
        fenomeni.append({
            "id": f["id"],
            "nome": f["name"],
            "target": _numero_bersaglio(nd),
            "scheda": _scheda_lang(nd, lang)[:200] + "…" if _scheda_lang(nd, lang) else "",
        })

    # ── 5) OUTPUT SCIENTIFICO ricco ───────────────────────────────────────────
    if not riconosciuti:
        output = (
            "Non ho trovato ingredienti riconoscibili nel grafo scientifico. "
            "Prova con una foto più nitida o con ingredienti più comuni."
        )
    else:
        nomi_trovati = ", ".join(r["nodo_nome"] for r in riconosciuti)
        abb_str = "; ".join(
            f"{a['a']} + {a['b']} ({a['overlap']:.0f} composti)" for a in abbinamenti[:3]
        ) if abbinamenti else "nessuna coppia analizzata"

        fen_str = ", ".join(f["nome"] for f in fenomeni) if fenomeni else "nessuno"

        lingua_prompt = {
            "it": (
                f"Sei un consulente scientifico F&B. Dalla foto ho riconosciuto: {nomi_trovati}. "
                f"Abbinamenti aromatici principali: {abb_str}. "
                f"Fenomeni fisici collegati: {fen_str}. "
                f"Scrivi un'analisi operativa in 4-6 frasi: cosa lega questi ingredienti "
                f"scientificamente, quali abbinamenti sono sorprendenti e perché, "
                f"e un consiglio pratico con un numero (temperatura, pH, Brix, ABV, o altro). "
                f"Tono: professionista al banco, non divulgativo."
            ),
            "en": (
                f"You are a scientific F&B consultant. From the photo I identified: {nomi_trovati}. "
                f"Main aromatic pairings: {abb_str}. Related physical phenomena: {fen_str}. "
                f"Write an operational analysis in 4-6 sentences: what links these ingredients "
                f"scientifically, which pairings are surprising and why, "
                f"and one practical tip with a number (temp, pH, Brix, ABV, or similar). "
                f"Tone: professional at the bench, not popularizing."
            ),
            "es": (
                f"Eres un consultor científico F&B. De la foto identifiqué: {nomi_trovati}. "
                f"Maridajes aromáticos principales: {abb_str}. Fenómenos físicos: {fen_str}. "
                f"Escribe un análisis operativo en 4-6 frases: qué une científicamente "
                f"estos ingredientes, qué maridajes son sorprendentes y por qué, "
                f"y un consejo práctico con un número (temp, pH, Brix, ABV u otro). "
                f"Tono: profesional en el banco, no divulgativo."
            ),
        }
        prompt_out = lingua_prompt.get(lang, lingua_prompt["it"])
        try:
            from ai import chiedi_mistral
            output = chiedi_mistral(prompt_out)
        except Exception as e:
            output = f"[errore generazione output: {e}]"

    # ── RISULTATO ─────────────────────────────────────────────────────────────
    totale = len(items)
    trovati = len(riconosciuti)
    return {
        "ingredienti_riconosciuti": riconosciuti,
        "ingredienti_sconosciuti": sconosciuti,
        "abbinamenti": abbinamenti,
        "fenomeni": fenomeni,
        "output_scientifico": output,
        "meta": {
            "lang": lang,
            "totale_visione": totale,
            "trovati_grafo": trovati,
            "coverage": f"{100*trovati//totale if totale else 0}%",
        },
    }
