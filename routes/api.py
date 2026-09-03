# ============================================================
# routes/api.py — API scientifica: composti, abbinamenti, strumenti, STT, vision.
# Dipende da: db, ai, contenuto, utils.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import estrai_entita, cerca_contesto, _haiku_raw


# ── Fase 1 flavor network: filtro di presentazione dei nomi sporchi ──────────
# Il dataset Ahn ha nomi da laboratorio ("Petitgrain Lemon", "Aroma Di Limone
# Naturale"). Questo NON è la bonifica completa (entity resolution) — è un filtro
# leggero che, al momento di MOSTRARE un abbinamento, normalizza o scarta i nomi
# palesemente tecnici, così l'utente non vede "roba da database".
_NOMI_SPORCHI_MAP = {
    "petitgrain lemon": "limone", "aroma di limone naturale": "limone",
    "lemon peel": "limone", "lemon juice": "limone", "succo di limone": "limone",
    "lime juice": "lime", "mozzarella di bufala": "mozzarella",
    "mozzarella di giornata": "mozzarella", "basilico genovese": "basilico",
    "muscat grape": "uva", "uva concord": "uva",
}
# marcatori che indicano un nome tecnico da scartare se non mappato
_MARCATORI_SPORCHI = ("aroma di", "aroma naturale", "natural flavor", "extract",
                      "estratto di", "oleoresin", "distillate", "concentrate")

# ── Fase 2: famiglie per ridurre la ridondanza (non 4 agrumi di fila) ────────
# Mappa ingrediente → famiglia. Limitiamo a max 2 elementi per famiglia e
# scartiamo il nome-categoria generico ("agrumi") se ci sono già ingredienti
# specifici di quella famiglia.
_FAMIGLIA = {
    "limone":"agrumi","lime":"agrumi","arancia":"agrumi","mandarino":"agrumi",
    "pompelmo":"agrumi","bergamotto":"agrumi","cedro":"agrumi","clementina":"agrumi",
    "tè nero":"tè","tè verde":"tè","tè bianco":"tè","matcha":"tè",
    "lampone":"frutti_rossi","mora":"frutti_rossi","mirtillo":"frutti_rossi",
    "fragola":"frutti_rossi","ribes":"frutti_rossi",
    "basilico":"erbe","menta":"erbe","rosmarino":"erbe","timo":"erbe",
    "prezzemolo":"erbe","salvia":"erbe","origano":"erbe",
}
# nomi-categoria generici da scartare quando c'è già un ingrediente specifico
_CATEGORIE_GENERICHE = {"agrumi", "erbe", "frutti rossi", "frutti di bosco",
                        "spezie", "tè", "frutta", "verdura", "latticini"}

def _nome_pulito(nome):
    """Restituisce (nome_pulito, tienilo). tienilo=False → scarta dall'output."""
    if not nome:
        return (nome, False)
    n = nome.strip().lower()
    # 1) mappa esplicita
    if n in _NOMI_SPORCHI_MAP:
        return (_NOMI_SPORCHI_MAP[n], True)
    # 2) contiene marcatori tecnici → scarta (non sappiamo pulirlo bene)
    for m in _MARCATORI_SPORCHI:
        if m in n:
            return (nome, False)
    # 3) nome con troppe maiuscole interne (es. "Carne Cruda Di Manzo", "Manzo Arrosto"):
    #    normalizzo in minuscolo pulito (title-case inglese → italiano leggibile)
    parole = nome.strip().split()
    if len(parole) >= 2 and sum(1 for p in parole if p[:1].isupper()) >= 2:
        # metto tutto minuscolo, poi maiuscola solo sulla prima parola
        pulito = " ".join(parole).lower()
        pulito = pulito[:1].upper() + pulito[1:] if pulito else pulito
        return (pulito, True)
    return (nome.strip(), True)

def _pulisci_abbinamenti(lista, campo="ingrediente", max_famiglia=3, ingrediente_base=None):
    """Filtra una lista di abbinamenti: normalizza nomi, scarta gli sporchi,
    deduplica per nome pulito, e limita la ridondanza di famiglia (max 2 agrumi,
    ecc.) scartando anche le categorie generiche. Mantiene l'ordine.
    Se ingrediente_base è passato, scarta i partner che sono varianti dello stesso
    ingrediente (maiale -> Maiale Arrosto, Pancetta): abbinare X con X non è utile."""
    visti = set()
    fam_count = {}
    out = []
    # radice dell'ingrediente base per scartare le auto-varianti (maiale->maiale arrosto)
    base_radice = None
    if ingrediente_base:
        base_radice = ingrediente_base.strip().lower()[:5]
        # famiglia del base: scarto anche i partner della stessa famiglia-carne se base è carne
    # prima passata: quali famiglie hanno ingredienti specifici?
    fam_presenti = set()
    for a in lista:
        nome = (a.get(campo) or a.get("nome") or a.get("a") or "") if isinstance(a, dict) else str(a)
        fam = _FAMIGLIA.get(nome.strip().lower())
        if fam:
            fam_presenti.add(fam)
    for a in lista:
        if isinstance(a, dict):
            nome = a.get(campo) or a.get("nome") or a.get("a") or ""
        else:
            nome = str(a)
        pulito, tieni = _nome_pulito(nome)
        if not tieni:
            continue
        chiave = pulito.lower()
        if chiave in visti:
            continue
        # scarta le auto-varianti: partner che condivide la radice col base
        if base_radice and len(base_radice) >= 4 and base_radice in chiave:
            continue
        # scarta la categoria generica se c'è già un ingrediente specifico
        if chiave in _CATEGORIE_GENERICHE:
            continue
        # limita la ridondanza di famiglia
        fam = _FAMIGLIA.get(chiave)
        if fam:
            if fam_count.get(fam, 0) >= max_famiglia:
                continue
            fam_count[fam] = fam_count.get(fam, 0) + 1
        visti.add(chiave)
        if isinstance(a, dict):
            a2 = dict(a)
            if campo in a2: a2[campo] = pulito
            elif "nome" in a2: a2["nome"] = pulito
            elif "a" in a2: a2["a"] = pulito
            out.append(a2)
        else:
            out.append(pulito)
    # SCORE DI SPECIFICITÀ (Sprint 3): declasso gli ingredienti-hub (manzo, carne...) che per
    # composti ubiquitari si abbinano a QUALSIASI cosa. Non li elimino (a volte sono validi), ma
    # li spingo in fondo così emergono gli abbinamenti caratteristici. Salta se il base è un hub.
    base_l = (ingrediente_base or "").strip().lower()
    if base_l not in _INGREDIENTI_HUB:
        def _e_hub(item):
            nm = (item.get(campo) or item.get("nome") or item.get("a") or "") if isinstance(item, dict) else str(item)
            return 1 if nm.strip().lower() in _INGREDIENTI_HUB else 0
        out.sort(key=_e_hub)  # gli hub (1) vanno in fondo, stabile
    return out


# ingredienti che dominano gli abbinamenti per composti generici (rumore di fondo):
# vanno declassati per far emergere gli abbinamenti caratteristici (score di specificità)
_INGREDIENTI_HUB = {
    "manzo", "manzo arrosto", "carne cruda di manzo", "carne di manzo", "maiale arrosto",
    "maiale stagionato", "carne", "brodo di carne", "carne cotta", "fegato",
}
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _profilo_default, _aggiorna_profilo, _check_rate_limit, _check_rate_limit_ai, _chiave_rate, _ai_giu_response
from auth import _utente_da_token
from config import DATABASE_URL
import os, json, re
import ai_gateway as GW
bp = Blueprint("api", __name__)


@bp.after_request
def _inietta_evidence(response):
    """Confidence Layer: aggiunge il badge evidence a TUTTE le risposte del Flavour (/v1/abbina),
    qualunque percorso di return abbiano usato. Legge il livello rilevato in request.environ."""
    try:
        if request.path.startswith("/v1/abbina/") and response.content_type and "json" in response.content_type:
            import json as _je
            _ev = request.environ.get("_evidence_level")
            _lang_req = request.args.get("lang", "it")
            data = _je.loads(response.get_data(as_text=True))
            # FIX TRADUZIONE: ritraduco la dicitura 'composto' se è rimasta in italiano ma lang è en/es
            # (succede per gli ingredienti del Knowledge Layer italiano).
            if isinstance(data, dict) and _lang_req in ("en", "es") and data.get("abbinamenti"):
                _MAP_DIC = {
                    "affinità molto alta": {"en": "very high affinity", "es": "afinidad muy alta"},
                    "affinità alta": {"en": "high affinity", "es": "afinidad alta"},
                    "affinità media": {"en": "medium affinity", "es": "afinidad media"},
                    "affinità presente": {"en": "some affinity", "es": "afinidad presente"},
                    "affinità debole": {"en": "weak affinity", "es": "afinidad débil"},
                }
                for _ab in data["abbinamenti"]:
                    _c = _ab.get("composto", "")
                    if _c in _MAP_DIC:
                        _ab["composto"] = _MAP_DIC[_c][_lang_req]
                        _tradotto = True
            if isinstance(data, dict) and "abbinamenti" in data:
                _cambiato = locals().get("_tradotto", False)
                # evidence: aggiungo se manca
                if "evidence" not in data:
                    _fonte = str(data.get("fonte", "")).lower()
                    if _ev is None:
                        _ev = "C" if ("ai" in _fonte or "matter lab ai" in _fonte) else "A"
                    data["evidence"] = _ev
                    data["evidence_label"] = {"A": "Dato molecolare verificato",
                        "B": "Profilo ereditato da ingrediente equivalente",
                        "C": "Suggerimento AI (non verificato molecolarmente)"}.get(_ev, "")
                    _cambiato = True
                # CONFIDENCE SCORE 0-100: sempre, su ogni abbinamento che non ce l'ha già
                _ev_finale = data.get("evidence", _ev or "C")
                _peso_ev = {"A": 1.0, "B": 0.75, "C": 0.5}.get(_ev_finale, 0.5)
                for _ab in data.get("abbinamenti", []):
                    if "confidence" in _ab:
                        continue
                    try:
                        _ov = float(_ab.get("overlap", 0))
                    except Exception:
                        _ov = 0
                    _base = min(100, (_ov / 60.0) * 100) if _ov > 0 else 55
                    _ab["confidence"] = int(round(_base * _peso_ev))
                    _cambiato = True
                # FILTRO CONFIDENCE (revisori): sotto 15 taglio via, 15-30 marco "debole".
                _abb_filtrati = []
                for _ab in data.get("abbinamenti", []):
                    _cf = _ab.get("confidence", 50)
                    if _cf < 15:
                        continue  # troppo debole, non mostrare
                    if _cf < 30:
                        _ab["soglia_critica"] = True
                        _ab["nota_soglia"] = "Affinità molecolare debole"
                    _abb_filtrati.append(_ab)
                if len(_abb_filtrati) != len(data.get("abbinamenti", [])):
                    data["abbinamenti"] = _abb_filtrati
                    _cambiato = True
                if _cambiato:
                    response.set_data(_je.dumps(data, ensure_ascii=False))
    except Exception:
        pass
    return response

# mappa italiano → nome Ahn (inglese), condivisa tra /abbina e /menu/proposte
_ALIAS_AHN = {
    "pomodoro":"tomato","limone":"lemon","aglio":"garlic","cipolla":"onion",
    "burro":"butter","panna":"cream","latte":"milk","uova":"egg","uovo":"egg",
    "basilico":"basil","prezzemolo":"parsley","rosmarino":"rosemary","timo":"thyme","menta":"mint",
    "cioccolato":"cocoa","caffe":"coffee","caffè":"coffee","espresso":"espresso",
    "fragola":"strawberry","lampone":"raspberry","mela":"apple","pera":"pear","banana":"banana",
    "arancia":"orange","limetta":"lime","lime":"lime","zenzero":"ginger","pepe":"black_pepper",
    "sale":"salt","aceto":"vinegar","vino":"wine","birra":"beer","rum":"rum","whisky":"whiskey",
    "gin":"gin","vodka":"vodka","salmone":"salmon","tonno":"tuna","gambero":"shrimp",
    "manzo":"beef","pollo":"chicken","maiale":"pork","agnello":"lamb","formaggio":"cheese",
    "parmigiano":"parmesan","mozzarella":"mozzarella","olio":"olive_oil","sesamo":"sesame",
    "mandorla":"almond","nocciola":"hazelnut","noci":"walnut","ananas":"pineapple","mango":"mango",
    "cocco":"coconut","zucca":"pumpkin","carota":"carrot","sedano":"celery","funghi":"mushroom",
    "tè":"tea","te":"tea","miele":"honey","zucchero":"sugar","peperoncino":"chili","melanzana":"eggplant",
    "prosciutto":"prosciutto","pancetta":"bacon","gorgonzola":"blue_cheese","ricotta":"ricotta",
    "pecorino":"pecorino","zucchine":"zucchini","rucola":"arugula","radicchio":"radicchio",
    "finocchio":"fennel","carciofo":"artichoke","asparago":"asparagus","spinaci":"spinach",
    "cavolo":"cabbage","broccolo":"broccoli","fico":"fig","albicocca":"apricot","pesca":"peach",
    "prugna":"plum","melograno":"pomegranate","mirtillo":"blueberry","pompelmo":"grapefruit",
    "bergamotto":"bergamot","uva":"grape","castagna":"chestnut","baccalà":"cod","acciuga":"anchovy",
    "polpo":"octopus","calamaro":"squid","orata":"sea_bream","branzino":"sea_bass","sgombro":"mackerel",
    "vongola":"clam","cozza":"mussel","ostrica":"oyster","riso":"rice","farina":"flour","pane":"bread",
    "salvia":"sage","alloro":"bay_leaf","origano":"oregano","noce moscata":"nutmeg","cardamomo":"cardamom",
    "zafferano":"saffron","cannella":"cinnamon","vaniglia":"vanilla","pistacchio":"pistachio",
    "campari":"amaro","aperol":"amaro","amaro":"amaro","vermouth":"vermouth","prosecco":"sparkling_wine",
    "cacao":"cocoa","caramello":"caramel","cetriolo":"cucumber","anguria":"watermelon","melone":"melon",
}
def _alias_ahn(nome):
    """Mappa un nome ingrediente (IT o EN) al nodo Ahn, o None."""
    if not nome: return None
    k = nome.lower().strip().replace("_"," ")
    if k in _ALIAS_AHN: return _ALIAS_AHN[k]
    # prova diretto (già inglese)
    kn = k.replace(" ","_")
    return _ALIAS_AHN.get(k) or (kn if kn.isalpha() or "_" in kn else None)


# ── AFFILIATI VINO/BIRRA ────────────────────────────────────────────────
# Tag affiliato da impostare dopo l'iscrizione ai programmi (ottobre 2026).
# Struttura come Amazon Associates per gli strumenti: link di ricerca verso
# e-commerce, il tag si aggiunge in coda quando disponibile.
AFFILIATE_TAGS = {
    "tannico": os.environ.get("TANNICO_TAG", ""),      # es. "?ref=matterlab"
    "vivino": os.environ.get("VIVINO_TAG", ""),
    "callmewine": os.environ.get("CALLMEWINE_TAG", ""),
}

def _classifica_bevanda(query):
    """Classifica una bevanda come 'vino' o 'birra' in modo affidabile (era il bug: IPA->vino).
    Usa liste di stili/nomi noti. Default prudente: se incerto, 'vino' (piu' comune negli abbinamenti)."""
    q = (query or "").lower()
    _BIRRA = ("ipa", "lager", "pilsner", "pils", "stout", "porter", "ale", "weiss", "weizen",
              "blanche", "saison", "tripel", "dubbel", "bock", "helles", "gose", "sour ale",
              "barleywine", "barley wine", "apa", "neipa", "birra", "beer", "hazy", "witbier",
              "kolsch", "kellerbier", "marzen", "dunkel", "schwarzbier", "trappist", "lambic")
    _VINO = ("barolo", "amarone", "chianti", "brunello", "nebbiolo", "sangiovese", "merlot",
             "cabernet", "primitivo", "aglianico", "montepulciano", "nero d'avola", "vermentino",
             "chardonnay", "sauvignon", "riesling", "verdicchio", "fiano", "greco", "falanghina",
             "prosecco", "franciacorta", "champagne", "spumante", "moscato", "passito", "gewurz",
             "pinot", "traminer", "lambrusco", "cerasuolo", "rose", "rosato", "vino", "wine",
             "bianco", "rosso", "barbera", "dolcetto", "valpolicella", "soave", "gavi")
    for k in _BIRRA:
        if k in q:
            return "birra"
    for k in _VINO:
        if k in q:
            return "vino"
    return "vino"  # default prudente

def _link_vino_birra(query, categoria="vino"):
    """Genera link di ricerca verso e-commerce per un vino/birra.
    Il tag affiliato viene aggiunto se configurato (via env var)."""
    from urllib.parse import quote_plus
    q = quote_plus(query)
    links = []
    if categoria in ("vino", "wine"):
        links = [
            {"store": "Tannico", "url": f"https://www.tannico.it/catalogsearch/result/?q={q}{AFFILIATE_TAGS['tannico']}"},
            {"store": "Vivino", "url": f"https://www.vivino.com/search/wines?q={q}{AFFILIATE_TAGS['vivino']}"},
            {"store": "Callmewine", "url": f"https://www.callmewine.com/ricerca?q={q}{AFFILIATE_TAGS['callmewine']}"},
        ]
    else:  # birra
        links = [
            {"store": "Vivino", "url": f"https://www.vivino.com/search?q={q}{AFFILIATE_TAGS['vivino']}"},
            {"store": "Amazon", "url": f"https://www.amazon.it/s?k={q}+birra+artigianale"},
        ]
    return links


def _estrai_nome_bevanda(testo):
    """Estrae un nome di vino/birra ricercabile dal testo descrittivo dell'abbinamento.
    Es. 'Un rosso strutturato (Barolo, Amarone)' → 'Barolo'.
    Cerca prima nomi tra parentesi (spesso i nomi propri), poi parole capitalizzate."""
    import re as _re
    if not testo:
        return ""
    # 1) nomi tra parentesi (es. "(Barolo, Amarone)")
    m = _re.search(r"\(([^)]+)\)", testo)
    if m:
        primo = m.group(1).split(",")[0].split("/")[0].strip()
        if primo:
            return primo
    # 2) parole capitalizzate (nomi propri/stili di vini/birre)
    # rimuovo prima gli articoli iniziali così non "mangiano" la parola dello stile
    ignora = {"Un", "Una", "Uno", "Il", "La", "Le", "Lo", "Per", "Con", "Dalle", "Delle", "Dei"}
    # togli gli articoli capitalizzati dal testo prima del match
    testo_pulito = _re.sub(r"\b(Un|Una|Uno|Il|La|Le|Lo|Per|Con)\b\s*", "", testo)
    parole = _re.findall(r"\b([A-ZÀ-Ù][a-zà-ù]{2,}(?:\s[A-ZÀ-Ù][a-zà-ù]+)?)\b", testo_pulito)
    for p in parole:
        if p.split()[0] not in ignora:
            return p
    return ""


@bp.route("/v1/genera-ricetta", methods=["POST"])
def genera_ricetta_endpoint():
    """Recipe Builder AI: genera una ricetta strutturata dai dati reali del grafo.
    Body JSON: {richiesta: 'un dolce al cioccolato', disciplina: 'pasticceria', lang: 'it', salva: false}
    Se salva=true, persiste la ricetta generata nel DB (con id ric-gen-<slug>).

    Sprint 1: la generazione è vincolata dal CONTRATTO PIATTO (contratto_piatto.py) che impedisce
    le allucinazioni (Tiramisù Gratinato) classificando la famiglia e vietando le tecniche
    incompatibili, senza spegnere la funzione."""
    from db import carica_grafo
    # rate limit stretto: genera-ricetta chiama l'AI, va protetto dal loop che brucia credito
    if not _check_rate_limit_ai(_chiave_rate()):
        return jsonify({"errore":"rate_limit","messaggio":"Troppe generazioni. Attendi un minuto."}), 429
    body = request.json or {}
    richiesta = body.get("richiesta", "").strip()
    disciplina = body.get("disciplina", "cucina")
    lang = body.get("lang", "it")
    salva = bool(body.get("salva", False))
    if not richiesta:
        return jsonify({"errore": "richiesta mancante (es. 'un dolce al cioccolato')"}), 400
    try:
        from builder import genera_ricetta
        db = carica_grafo()
        # Genero in IT (veloce, sotto il timeout worker). Le traduzioni EN/ES NON si fanno in-request
        # (3 chiamate AI sforano i 30s): la ricetta salvata resta con nome_en=NULL, e il batch
        # /admin/traduci-ricette la traduce dopo (flusso trilingue garantito, ma asincrono).
        risultato = genera_ricetta(db, richiesta, disciplina=disciplina, lang="it")
        # FILTRO SENSATEZZA: NON rigenero più dentro la request (una seconda chiamata AI completa
        # faceva sforare i 30s del worker Railway → 500). La sensatezza resta come nota informativa:
        # il frontend può segnalare "abbinamento audace" senza bloccare la generazione.
        _sens = risultato.get("_sensatezza", {})
        if _sens and not _sens.get("ok", True) and not risultato.get("errore"):
            risultato["_nota_abbinamento"] = "Abbinamento audace: ingredienti con affinità non convenzionale."
        if risultato.get("errore"):
            return jsonify(risultato), 422
        # VERIFICA ANTI-ERESIE: controlla la ricetta contro le regole canoniche (no panna nella carbonara ecc.)
        try:
            from verificatore_ricette import verifica_ricetta
            verifica = verifica_ricetta(risultato.get("nome",""), risultato.get("ingredienti",[]))
            risultato["_verifica"] = verifica
            # se ci sono ERESIE GRAVI, non salvo automaticamente: serve revisione (verifica SEMPRE)
            if not verifica["ok"]:
                salva = False
                risultato["_bloccata"] = True
                risultato["_motivo_blocco"] = verifica["errori_gravi"]
        except Exception as _ve:
            risultato["_verifica"] = {"ok": True, "nota": "verificatore non disponibile"}
        # CONTRATTO PIATTO: se il red team ha trovato un'incoerenza (tiramisù gratinato, gelato coi
        # gamberi), NON restituisco la fusione assurda. Cerco il piatto BASE fedele tra le canoniche
        # e restituisco quello, con una nota che spiega come aggiungere a parte l'elemento richiesto.
        if risultato.get("_incoerente"):
            salva = False
            try:
                from db import carica_grafo as _cg
                _db2 = _cg()
                # estraggo il nome-base: la prima parola-chiave del piatto (tiramisù, gelato...)
                _fam = (risultato.get("_coerenza") or {}).get("famiglia", "")
                _base = richiesta.lower().split(" con ")[0].split(" saltat")[0].split(" gratin")[0].strip()
                # cerco prima un nome che INIZIA con la parola base (più fedele), poi che la contiene
                _rows = _db2.execute(
                    "SELECT nome, disciplina, descrizione, ingredienti, fenomeni, tecniche, numeri, "
                    "punto_critico, procedimento, esperimento, difficolta, porzioni, tempo_prep, "
                    "tempo_cottura FROM ricette WHERE lower(nome) LIKE %s "
                    "ORDER BY (CASE WHEN lower(nome) LIKE %s THEN 0 ELSE 1 END), length(nome) LIMIT 1",
                    ("%" + _base[:20] + "%", _base[:15] + "%")).fetchall()
                if _rows:
                    _r = _rows[0]
                    def _jj(v):
                        if v is None: return None
                        return v if isinstance(v,(list,dict)) else (json.loads(v) if isinstance(v,str) and v.strip()[:1] in '[{' else v)
                    _fedele = {"nome": _r["nome"], "disciplina": _r["disciplina"], "descrizione": _r["descrizione"],
                        "ingredienti": _jj(_r["ingredienti"]) or [], "fenomeni": _jj(_r["fenomeni"]) or [],
                        "tecniche": _jj(_r["tecniche"]) or [], "numeri": _jj(_r["numeri"]) or {},
                        "punto_critico": _r["punto_critico"], "procedimento": _jj(_r["procedimento"]) or [],
                        "esperimento": _r["esperimento"], "difficolta": _r["difficolta"],
                        "porzioni": _r["porzioni"], "tempo_prep": _r["tempo_prep"], "tempo_cottura": _r["tempo_cottura"],
                        "_certificata": True,
                        "_nota_contratto": "Ho tenuto il piatto fedele alla sua natura. La variante che "
                            "hai chiesto non è compatibile con questo tipo di preparazione: se vuoi un "
                            "elemento in più (es. una parte croccante), va aggiunto a parte senza snaturare il piatto."}
                    return jsonify({"ricetta": _fedele, "certificata": True, "corretta_da_contratto": True})
            except Exception:
                pass
        # salvataggio opzionale — salva TUTTI i campi, incluse procedimento/applicazioni e le 3 lingue
        if salva and risultato.get("nome"):
            try:
                import re as _re, json as _j2, unicodedata
                from db import _get_conn, _release_conn
                nome = risultato["nome"]
                slug = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
                slug = _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
                rid = f"ric-gen-{slug}"
                conn = _get_conn(); cur = conn.cursor()
                cur.execute("""
                    INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,
                        punto_critico,abbinamenti,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                """, (rid, nome, disciplina, risultato.get("descrizione",""),
                      _j2.dumps(risultato.get("ingredienti",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("fenomeni",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("tecniche",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("numeri",{}),ensure_ascii=False),
                      risultato.get("punto_critico",""),
                      _j2.dumps(risultato.get("abbinamenti",{}),ensure_ascii=False),
                      _j2.dumps(risultato.get("procedimento",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("applicazioni",[]),ensure_ascii=False),
                      risultato.get("tempo_prep"), risultato.get("tempo_cottura"),
                      risultato.get("difficolta",""), risultato.get("porzioni","")))
                conn.commit(); cur.close(); _release_conn(conn)
                risultato["_salvata"] = True
                risultato["id"] = rid
            except Exception as se:
                risultato["_salvata"] = False
                risultato["_errore_salvataggio"] = str(se)
        # evento funnel: activation (l'utente ha generato la sua prima ricetta = ha visto il valore)
        try:
            import oss
            _tok = request.headers.get("X-Token","") or body.get("token","")
            _uid = _utente_da_token(_tok) if _tok else None
            if _uid and not risultato.get("errore"):
                oss.funnel_write("activation", user_id=_uid,
                                 utm_campaign=body.get("utm_campaign"), utm_content=body.get("utm_content"))
        except Exception:
            pass
        return jsonify(risultato)
    except Exception as e:
        # se l'AI è giù / credito finito, risposta pulita 503 invece di 500 HTML
        _m = str(e).lower()
        if any(k in _m for k in ["api_key","anthropic","mistral","credit","billing","rate","timeout","gateway","503","429"]):
            return _ai_giu_response()
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/v1/abbina-bevanda")
def abbina_bevanda():
    """Dato un abbinamento vino/birra (query testuale), restituisce l'abbinamento.
    ?q=Barolo&cat=vino  oppure  ?q=IPA&cat=birra
    NB: i link e-commerce sono CONGELATI per il lancio (il rilevamento categoria
    sbagliava, es. IPA->vino, e un link sbagliato distrugge la fiducia più di
    quanto renda l'affiliazione). Si riattivano dopo aver stabilizzato il rilevamento.
    Flag: ABBINA_BEVANDA_LINK_ATTIVI (env, default off)."""
    query = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()
    if not query:
        return jsonify({"errore": "query mancante (?q=...)"}), 400
    # rilevamento categoria robusto: se non esplicito, classifico (IPA=birra, Barolo=vino)
    if cat not in ("vino", "birra", "wine"):
        cat = _classifica_bevanda(query)
    import os as _os
    link_attivi = _os.environ.get("ABBINA_BEVANDA_LINK_ATTIVI", "").lower() in ("1", "true", "yes")
    risp = {
        "query": query,
        "categoria": cat,
        "beta": True,
        "nota": "Suggerimento di categoria. Gli abbinamenti commerciali sono in preparazione.",
    }
    if link_attivi:
        risp["links"] = _link_vino_birra(query, cat)
        risp["disclosure"] = "Link affiliati: acquistando tramite questi link supporti Matter Lab senza costi aggiuntivi."
    else:
        risp["links"] = []
    return jsonify(risp)


# ── ATTREZZATURA per tecnica ────────────────────────────────────────────
ATTREZZATURA_TECNICA = {
    "tec-shake": ["shaker boston professionale", "strainer cocktail", "jigger dosatore"],
    "tec-stir": ["mixing glass yarai", "bar spoon", "julep strainer"],
    "tec-muddle": ["muddler professionale", "pestello cocktail"],
    "tec-milk-punch": ["colino fine maglia", "carta filtro superbag"],
    "tec-fat-washing-tecnica": ["contenitore infusione", "colino fine"],
    "tec-carbonatazione-tecnica": ["soda maker professionale", "cilindro co2"],
    "tec-estrazione-espresso": ["macchina espresso", "macinacaffe conico", "tamper 58mm"],
    "tec-tamping": ["tamper 58mm calibrato", "tamping station"],
    "tec-pour-over": ["v60 hario", "kettle collo cigno", "bilancia caffe"],
    "tec-vaporizzazione-latte": ["lancia vapore", "bricco montalatte acciaio", "termometro latte"],
    "tec-mantecatura": ["mantecatore gelato domestico", "spatola gelato"],
    "tec-pastorizzazione-gelato": ["pastorizzatore", "termometro cucina digitale"],
    "tec-bilanciamento-mix": ["rifrattometro brix", "bilancia precisione 0.1g"],
    "tec-raschiatura-granita": ["vassoio inox basso", "forchetta granita"],
    "tec-temperaggio": ["termometro cioccolato", "marmo temperaggio", "spatola offset"],
    "tec-laminazione": ["matterello professionale", "raschietto pasta"],
    "tec-macaronage": ["tappetino macaron silicone", "sac a poche", "bocchette lisce"],
    "tec-cottura-zucchero": ["termometro zucchero", "pentolino rame"],
    "tec-montatura": ["planetaria", "frusta acciaio", "ciotola inox"],
    "tec-impasto": ["planetaria gancio", "tarocco pasta"],
    "tec-pieghe": ["ciotola impasto", "tarocco"],
    "tec-formatura": ["banneton cestino lievitazione", "tarocco"],
    "tec-scoring": ["lame scoring pane grignette", "coltello lametta"],
    "tec-autolisi": ["ciotola grande", "bilancia cucina"],
    "tec-sous-vide-tecnica": ["roner sous vide", "sacchetti sottovuoto", "macchina sottovuoto"],
    "tec-frittura": ["termometro frittura", "friggitrice", "ragno frittura"],
    "tec-brasatura-tecnica": ["cocotte ghisa", "termometro sonda"],
    "tec-emulsione": ["frullatore immersione", "frusta"],
    "tec-tagli": ["coltello chef professionale", "tagliere", "acciaino affilatura"],
    "tec-fermentazione-lattica": ["barattoli fermentazione", "pesi fermentazione vetro"],
    "tec-affumicatura": ["affumicatore", "chips legno affumicatura"],
    "tec-curing": ["contenitore stagionatura", "bilancia precisione"],
    "tec-mash": ["pentola cotta birra", "termometro mash", "mulino malto"],
    "tec-dry-hopping-tecnica": ["sacchetto luppolo", "fermentatore"],
    "tec-vinificazione-bianco": ["densimetro mosto", "damigiana", "gorgogliatore"],
    "tec-macerazione": ["tino fermentazione", "follatore"],
}

# match per parole chiave: le tecniche NUOVE del grafo hanno id diversi dal dizionario storico.
# Invece di id rigidi, cerchiamo termini nel nome/id della tecnica -> attrezzature giuste.
ATTREZZATURA_KEYWORD = {
    "shake": ["shaker boston professionale","strainer cocktail","jigger dosatore"],
    "stir": ["mixing glass yarai","bar spoon","julep strainer"],
    "muddle": ["muddler professionale","pestello cocktail"],
    "espresso": ["macchina espresso","macinacaffe conico","tamper 58mm"],
    "tamp": ["tamper 58mm calibrato","tamping station"],
    "pour-over": ["v60 hario","kettle collo cigno","bilancia caffe"],
    "latte": ["lancia vapore","bricco montalatte acciaio","termometro latte"],
    "mantec": ["mantecatore gelato","spatola gelato"],
    "temperagg": ["termometro cioccolato","marmo temperaggio","spatola offset"],
    "lamina": ["matterello professionale","raschietto pasta"],
    "impast": ["planetaria gancio","tarocco pasta"],
    "piegh": ["ciotola impasto","tarocco"],
    "formatura": ["banneton cestino lievitazione","tarocco"],
    "autolisi": ["ciotola grande","bilancia cucina"],
    "sous-vide": ["roner sous vide","sacchetti sottovuoto","macchina sottovuoto"],
    "sottovuoto": ["roner sous vide","sacchetti sottovuoto","macchina sottovuoto"],
    "friggit": ["termometro frittura","friggitrice","ragno frittura"],
    "frittura": ["termometro frittura","friggitrice","ragno frittura"],
    "brasat": ["cocotte ghisa","termometro sonda"],
    "emulsion": ["frullatore immersione","frusta"],
    "taglio": ["coltello chef professionale","tagliere","acciaino affilatura"],
    "fermentazione": ["barattoli fermentazione","pesi fermentazione vetro"],
    "affumicat": ["affumicatore","chips legno affumicatura"],
    "frollatura": ["contenitore stagionatura","bilancia precisione"],
    "curing": ["contenitore stagionatura","bilancia precisione"],
    "mash": ["pentola cotta birra","termometro mash","mulino malto"],
    "dry-hop": ["sacchetto luppolo","fermentatore"],
    "luppol": ["sacchetto luppolo","fermentatore"],
    "vinifica": ["densimetro mosto","damigiana","gorgogliatore"],
    "macera": ["tino fermentazione","follatore"],
    "carbonatazione": ["soda maker professionale","cilindro co2"],
    "reverse": ["termometro sonda wireless","roner sous vide","griglia ghisa"],
    "oliocottura": ["termometro sonda","pentola bassa","olio evo"],
    "confit": ["termometro sonda","pentola bassa"],
    "sferificaz": ["siringa sferificazione","alginato","cucchiaio dosatore"],
    "gelificaz": ["agar agar","gellan","bilancia precisione 0.1g"],
    "affinamento": ["contenitore stagionatura","termometro cantina"],
    "essicca": ["essiccatore alimentare","termometro forno"],
    "montatura": ["planetaria","frusta acciaio","ciotola inox"],
    "cottura-zucchero": ["termometro zucchero","pentolino rame"],
    "caramellizz": ["termometro zucchero","pentolino rame"],
    "vapore": ["cestello vapore","termometro sonda"],
    "brew": ["v60 hario","kettle collo cigno","bilancia caffe"],
    "wok": ["wok acciaio al carbonio","paletta wok","fornello wok alta potenza"],
    "salt": ["wok acciaio al carbonio","paletta wok"],
    "tandoor": ["forno tandoor","spiedini tandoor","pietra refrattaria"],
    "tikka": ["spiedini acciaio","pietra refrattaria","griglia"],
    "nixtamal": ["pentola acciaio","colino a maglia fine","calce alimentare E526"],
    "tortilla": ["pressa per tortillas","comal piastra","carta forno"],
    "koji": ["fermentatore temperatura controllata","termometro sonda","spore koji"],
    "kansui": ["bilancia precisione 0.1g","carbonato di sodio","macchina per pasta"],
    "tadka": ["padellino tadka","pestello spezie","colino a rete"],
    "mochi": ["mortaio grande","pestello legno","stampi mochi"],
    "vapore-bao": ["cestello bambu vapore","carta forno","pentola wok"],
}

def _attrezzatura_per_tecnica(tecnica_id, tecnica_nome=""):
    """Trova le attrezzature per una tecnica: prima l'id esatto (dizionario storico),
    poi match per parola chiave su id+nome (per le tecniche nuove del grafo)."""
    if tecnica_id in ATTREZZATURA_TECNICA:
        return ATTREZZATURA_TECNICA[tecnica_id]
    testo = (str(tecnica_id) + " " + str(tecnica_nome)).lower()
    for chiave, lista in ATTREZZATURA_KEYWORD.items():
        if chiave in testo:
            return lista
    return []

@bp.route("/v1/attrezzatura/<tecnica_id>")
def attrezzatura_tecnica(tecnica_id):
    """Utensili consigliati per una tecnica, con link affiliati Amazon (tag via env AMAZON_TAG).
    Match per id esatto o per parola chiave (tecniche nuove del grafo)."""
    # recupero il nome della tecnica dal grafo per il match a parole chiave
    tecnica_nome = ""
    try:
        from db import carica_grafo
        r = carica_grafo().execute("SELECT name FROM nodes WHERE id=?", (tecnica_id,)).fetchone()
        if r: tecnica_nome = r["name"]
    except Exception:
        pass
    utensili = _attrezzatura_per_tecnica(tecnica_id, tecnica_nome)
    if not utensili:
        return jsonify({"tecnica": tecnica_id, "attrezzatura": [],
                        "nota": "Nessuna attrezzatura specifica mappata per questa tecnica."})
    from urllib.parse import quote_plus
    tag = os.environ.get("AMAZON_TAG", "")
    items = []
    for u in utensili:
        q = quote_plus(u)
        url = f"https://www.amazon.it/s?k={q}"
        if tag:
            url += f"&tag={tag}"
        items.append({"nome": u, "url": url})
    return jsonify({
        "tecnica": tecnica_id,
        "attrezzatura": items,
        "disclosure": "Link affiliati: acquistando tramite questi link supporti Matter Lab senza costi aggiuntivi."
    })

@bp.route("/v1/prodotto")
def prodotto_affiliato():
    """Link affiliato per un prodotto/ingrediente specializzato. ?q=destrosio+gelateria
    Restituisce Amazon + Special Ingredients (per additivi/texture: agar, xantana, lecitina...)."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"errore": "query mancante (?q=...)"}), 400
    from urllib.parse import quote_plus
    q = quote_plus(query)
    tag = os.environ.get("AMAZON_TAG", "")
    tag_special = os.environ.get("SPECIAL_INGREDIENTS_TAG", "")
    # Special Ingredients: negozio specializzato in additivi/texture per cucina tecnica.
    # È lo store giusto per idrocolloidi, gelificanti, addensanti (agar, xantana, lecitina, ecc.).
    _kw_special = ("agar", "xantana", "xanthan", "lecitina", "gellan", "gluco", "calcic",
                   "alginat", "carragenina", "pectina", "maltodestrina", "destrosio", "isomalto",
                   "sferificaz", "gelifica", "addensant", "idrocolloid", "citrato", "transglutaminasi")
    stores = []
    amazon_url = f"https://www.amazon.it/s?k={q}"
    if tag:
        amazon_url += f"&tag={tag}"
    stores.append({"store": "Amazon", "url": amazon_url})
    if any(k in query.lower() for k in _kw_special):
        si_url = f"https://www.specialingredients.it/ricerca?controller=search&s={q}"
        if tag_special:
            si_url += f"&ref={tag_special}"
        stores.append({"store": "Special Ingredients", "url": si_url,
                       "nota": "specializzato in additivi e texture per cucina tecnica"})
    return jsonify({
        "query": query,
        "url": stores[0]["url"],   # retrocompatibile: url singolo = il primo
        "stores": stores,
        "disclosure": "Link affiliati: acquistando tramite questi link supporti Matter senza costi aggiuntivi."
    })


@bp.route("/v1/lievitazione-meteo", methods=["GET", "POST"])
def lievitazione_meteo():
    """Misura attiva automatica: adatta i tempi di lievitazione al meteo reale.
    GET  ?lat=&lon=&tempo_base=4
    POST {lat, lon, tempo_base}
    Usa Open-Meteo (temp+umidità) + Q10 (cinetica fermentazione)."""
    if request.method == "POST":
        body = request.json or {}
        lat = body.get("lat"); lon = body.get("lon")
        tempo_base = body.get("tempo_base", 4.0)
        lang = body.get("lang", "it")
    else:
        lat = request.args.get("lat"); lon = request.args.get("lon")
        tempo_base = request.args.get("tempo_base", 4.0)
        lang = request.args.get("lang", "it")
    if lat is None or lon is None:
        return jsonify({"errore": "posizione mancante (lat/lon)"}), 400
    try:
        lat = float(lat); lon = float(lon); tempo_base = float(tempo_base)
    except (TypeError, ValueError):
        return jsonify({"errore": "lat/lon/tempo_base non validi"}), 400
    try:
        from meteo_lievitazione import adatta_lievitazione
        risultato = adatta_lievitazione(lat, lon, tempo_base_ore=tempo_base, lang=lang)
        if risultato.get("errore"):
            return jsonify(risultato), 503
        return jsonify(risultato)
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/v1/strumenti")
@bp.route("/v1/strumenti/<disciplina>")
def strumenti(disciplina=None):
    """Restituisce gli strumenti di misura per disciplina.
    Ogni strumento ha: nome, misura, numero_bersaglio, link_amazon."""
    STRUMENTI_DB = {
        "bar": [
            {"nome":"pH-metro da banco","misura":"pH","target":"0-14","uso":"Misura l'acidità reale del cocktail. Un sour equilibrato sta tra pH 3,0 e 3,4 — sotto è aggressivo, sopra è piatto.","amazon":"https://www.amazon.it/s?k=phmetro+digitale+professionale","prezzo_approx":"€25-80"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"0-85°","uso":"Legge lo zucchero disciolto in sciroppi e liquori. Ti dà la dolcezza esatta invece di andare a occhio.","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+professionale","prezzo_approx":"€15-60"},
            {"nome":"Bilancia di precisione 0.1g","misura":"grammi","target":"0-500g","uso":"Pesa acidi, zuccheri e soluzioni con precisione 0,1g. La base per ricette ripetibili al decimo.","amazon":"https://www.amazon.it/s?k=bilancia+precisione+0.1g+cocktail","prezzo_approx":"€20-50"},
            {"nome":"Alcolimetro/ebulliometro","misura":"ABV%","target":"0-100%","uso":"Verifica il grado alcolico finale del drink. Utile per batch e pre-mix dove l'ABV deve essere costante.","amazon":"https://www.amazon.it/s?k=alcolimetro+digitale","prezzo_approx":"€30-150"},
            {"nome":"Termometro digitale sonda","misura":"°C","target":"-50/+300°C","uso":"Controlla la temperatura di servizio e degli infusi. La T finale di un drink shakerato sta tra -4 e -6°C.","amazon":"https://www.amazon.it/s?k=termometro+digitale+sonda+cucina","prezzo_approx":"€10-40"},
            {"nome":"Jigger graduato","misura":"ml","target":"5-60ml","uso":"Dosa i volumi al millilitro. La differenza tra un drink ripetibile e uno che cambia ogni volta.","amazon":"https://www.amazon.it/s?k=jigger+professionale+graduato","prezzo_approx":"€5-25"},
        ],
        "caffe": [
            {"nome":"Rifrattometro TDS caffè (VST/Atago)","misura":"TDS%","target":"1.15-1.55% filtro · 7-12% espresso","uso":"Misura la concentrazione dell'estratto. Filtro ben fatto sta a 1,15-1,55% TDS, espresso a 7-12%.","amazon":"https://www.amazon.it/s?k=rifrattometro+caffe+tds","prezzo_approx":"€50-300"},
            {"nome":"Bilancia barista 0.1g con timer","misura":"grammi + tempo","target":"ratio 1:2-17","uso":"Pesa dose e resa col tempo. La base per un ratio costante (1:2 espresso, 1:16 filtro).","amazon":"https://www.amazon.it/s?k=bilancia+barista+timer+professionale","prezzo_approx":"€25-150"},
            {"nome":"Termometro sonda digitale","misura":"°C","target":"90-96°C","uso":"Controlla la temperatura dell'acqua. L'estrazione ideale sta tra 90 e 96°C.","amazon":"https://www.amazon.it/s?k=termometro+sonda+caffetteria","prezzo_approx":"€10-40"},
            {"nome":"Manometro espresso","misura":"bar","target":"9 bar","uso":"Verifica la pressione in erogazione. Lo standard è 9 bar — fuori range l'estrazione cambia.","amazon":"https://www.amazon.it/s?k=manometro+macchina+espresso","prezzo_approx":"€15-60"},
        ],
        "panificazione": [
            {"nome":"pH-metro","misura":"pH","target":"pH madre: 3.7-3.9","uso":"Legge l'acidità della madre. Una madre in forza sta a pH 3,7-3,9: sotto è troppo acida, sopra è debole.","amazon":"https://www.amazon.it/s?k=phmetro+lievito+madre","prezzo_approx":"€25-80"},
            {"nome":"Termometro sonda digitale","misura":"°C","target":"96-98°C interno pane","uso":"Controlla la temperatura dell'acqua. L'estrazione ideale sta tra 90 e 96°C.","amazon":"https://www.amazon.it/s?k=termometro+sonda+forno+pane","prezzo_approx":"€10-40"},
            {"nome":"Bilancia professionale 1g","misura":"grammi","target":"baker%","uso":"Pesa gli ingredienti in baker's percentage. La precisione fa la differenza sull'idratazione.","amazon":"https://www.amazon.it/s?k=bilancia+professionale+panificazione","prezzo_approx":"€20-80"},
            {"nome":"Igrometro forno","misura":"umidità%","target":"80-90% primi minuti cottura","uso":"Controlla l'umidità in camera. I primi minuti a 80-90% danno crosta e sviluppo giusti.","amazon":"https://www.amazon.it/s?k=igrometro+forno+cottura+pane","prezzo_approx":"€15-50"},
            {"nome":"Acidimetro titolabile","misura":"acido lattico%","target":"0.5-2%","uso":"Misura l'acidità totale, non solo il pH. Dice quanto acido c'è davvero da tamponare.","amazon":"https://www.amazon.it/s?k=kit+acidita+titolabile+vino","prezzo_approx":"€20-60"},
        ],
        "pasticceria": [
            {"nome":"Termometro digitale sonda","misura":"°C","target":"crema 82-84°C · caramello 160°C","uso":"Controlla creme e zuccheri cotti. Crema inglese a 82-84°C, caramello a 160°C.","amazon":"https://www.amazon.it/s?k=termometro+sonda+pasticceria","prezzo_approx":"€10-40"},
            {"nome":"Bilancia 0.1g","misura":"grammi","target":"precisione fondamentale","uso":"In pasticceria la precisione è tutto: 0,1g cambia la resa di meringhe e gel.","amazon":"https://www.amazon.it/s?k=bilancia+precisione+pasticceria","prezzo_approx":"€20-50"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"sciroppi · confetture ≥65°","uso":"Misura lo zucchero di sciroppi e confetture. Gelificazione sopra i 65° Brix.","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+pasticceria","prezzo_approx":"€15-60"},
            {"nome":"Termometro IR (infrarossi)","misura":"°C","target":"temperaggio cioccolato 28-32°C","uso":"Legge la superficie senza contatto. Fondamentale per il temperaggio (28-32°C).","amazon":"https://www.amazon.it/s?k=termometro+infrarossi+cucina+professionale","prezzo_approx":"€20-60"},
        ],
        "gelateria": [
            {"nome":"Termometro sonda digitale","misura":"°C","target":"-10/-12°C servizio · -18°C conservazione","uso":"Controlla la temperatura dell'acqua. L'estrazione ideale sta tra 90 e 96°C.","amazon":"https://www.amazon.it/s?k=termometro+sonda+gelateria+professionale","prezzo_approx":"€10-40"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"POD/PAC mix gelato","uso":"Misura lo zucchero di sciroppi e confetture. Gelificazione sopra i 65° Brix.","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+gelateria","prezzo_approx":"€15-60"},
            {"nome":"Bilancia professionale 1g","misura":"grammi","target":"overrun: peso × volume","uso":"Pesa gli ingredienti in baker's percentage. La precisione fa la differenza sull'idratazione.","amazon":"https://www.amazon.it/s?k=bilancia+professionale+gelateria","prezzo_approx":"€20-80"},
            {"nome":"Misuratore Aw (attività acqua)","misura":"Aw","target":"<0.85 per sicurezza","uso":"Misura l'acqua libera. Sotto 0,85 il prodotto è sicuro dalla proliferazione.","amazon":"https://www.amazon.it/s?k=misuratore+attivita+acqua+aw","prezzo_approx":"€200-800"},
        ],
        "vino": [
            {"nome":"pH-metro da banco","misura":"pH","target":"pH vino 3.0-3.8","uso":"Legge l'acidità del vino. Bianchi freschi a pH 3,0-3,4, rossi 3,4-3,6.","amazon":"https://www.amazon.it/s?k=phmetro+enologico+vino","prezzo_approx":"€25-150"},
            {"nome":"Kit acidità volatile","misura":"g/L acido acetico","target":"<0.6 g/L","uso":"Misura l'acido acetico. Sopra 0,6 g/L il vino sa di aceto: difetto da tenere sotto controllo.","amazon":"https://www.amazon.it/s?k=kit+acidita+volatile+vino","prezzo_approx":"€20-80"},
            {"nome":"Rifrattometro mosto","misura":"°Brix/Babo","target":"maturità uva","uso":"Misura gli zuccheri dell'uva. Dice quando l'uva è matura per la vendemmia.","amazon":"https://www.amazon.it/s?k=rifrattometro+mosto+uva","prezzo_approx":"£15-50"},
            {"nome":"Alcoolmetro Gay-Lussac","misura":"ABV%","target":"vino 10-15% vol","uso":"Verifica il grado del vino finito, tipicamente 10-15% vol.","amazon":"https://www.amazon.it/s?k=alcoolmetro+gay+lussac+vino","prezzo_approx":"€10-40"},
            {"nome":"Kit SO2 libera/totale","misura":"mg/L","target":"SO2 libera 20-40 mg/L","uso":"Misura l'anidride solforosa. La SO2 libera va tenuta a 20-40 mg/L per proteggere il vino.","amazon":"https://www.amazon.it/s?k=kit+analisi+so2+vino","prezzo_approx":"€30-100"},
        ],
        "birra": [
            {"nome":"Densimetro/areometro","misura":"densità/OG/FG","target":"OG 1.040-1.080","uso":"Misura la densità del mosto. OG prima della fermentazione (1.040-1.080), FG dopo.","amazon":"https://www.amazon.it/s?k=densimetro+birra+homebrewing","prezzo_approx":"€5-20"},
            {"nome":"Rifrattometro birra","misura":"°Brix/Plato","target":"attenuation%","uso":"Legge i gradi Plato. Comodo per controlli veloci durante la cotta.","amazon":"https://www.amazon.it/s?k=rifrattometro+birra+professionale","prezzo_approx":"€15-50"},
            {"nome":"pH-metro digitale","misura":"pH","target":"mash pH 5.2-5.4","uso":"Controlla il pH del mash. La zona giusta è 5,2-5,4 per l'azione degli enzimi.","amazon":"https://www.amazon.it/s?k=phmetro+digitale+birra","prezzo_approx":"€25-80"},
            {"nome":"Termometro sonda","misura":"°C","target":"mash 62-72°C · lagerizzazione 0-2°C","uso":"Governa le soste enzimatiche del mash (62-72°C) e la lagerizzazione.","amazon":"https://www.amazon.it/s?k=termometro+sonda+birra+homebrewing","prezzo_approx":"€10-40"},
            {"nome":"Manometro CO2 keg","misura":"bar","target":"carbonatazione 1.5-3 bar","uso":"Regola la carbonatazione in fusto, tra 1,5 e 3 bar secondo lo stile.","amazon":"https://www.amazon.it/s?k=manometro+co2+fusto+birra","prezzo_approx":"€15-50"},
        ],
        "cucina": [
            {"nome":"Termometro sonda digitale","misura":"°C","target":"manzo MR 55-57°C · pollo 74°C","uso":"Controlla la temperatura dell'acqua. L'estrazione ideale sta tra 90 e 96°C.","amazon":"https://www.amazon.it/s?k=termometro+sonda+cucina+professionale","prezzo_approx":"€10-40"},
            {"nome":"pH-metro","misura":"pH","target":"fermentati pH<4.6","uso":"Legge l'acidità della madre. Una madre in forza sta a pH 3,7-3,9: sotto è troppo acida, sopra è debole.","amazon":"https://www.amazon.it/s?k=phmetro+cucina+fermentati","prezzo_approx":"€25-80"},
            {"nome":"Termometro IR infrarossi","misura":"°C","target":"olio frittura 170-180°C","uso":"Legge la superficie: olio di frittura ideale a 170-180°C.","amazon":"https://www.amazon.it/s?k=termometro+infrarossi+cucina","prezzo_approx":"€20-60"},
            {"nome":"Bilancia precisione 1g","misura":"grammi","target":"dosaggi sale/acido","uso":"Dosaggi esatti di sale e acidi, dove l'occhio sbaglia.","amazon":"https://www.amazon.it/s?k=bilancia+precisione+cucina+professionale","prezzo_approx":"€20-50"},
            {"nome":"Rifrattometro Brix","misura":"°Brix","target":"confetture ≥65°","uso":"Misura lo zucchero di sciroppi e confetture. Gelificazione sopra i 65° Brix.","amazon":"https://www.amazon.it/s?k=rifrattometro+brix+marmellata","prezzo_approx":"€15-60"},
        ],
    }

    if disciplina:
        disc_norm = disciplina.lower().replace("caffetteria","caffe")
        strumenti_disc = STRUMENTI_DB.get(disc_norm, [])
        return jsonify({"disciplina":disciplina,"strumenti":strumenti_disc})

    # Tutti
    return jsonify({"strumenti":STRUMENTI_DB})

@bp.route("/v1/stt", methods=["POST"])
def stt():
    """Trascrizione audio via OpenAI Whisper (AI Gateway route_stt).
    Accetta audio WebM/MP4/WAV/M4A da browser.
    Pro-only: il barman parla al banco, l app trascrive e risponde."""
    token = request.headers.get("X-Token","") or (request.json or {}).get("token","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    # verifica piano pro
    if DATABASE_URL:
        try:
            import psycopg2
            conn_p = _get_conn()
            cur_p = conn_p.cursor()
            cur_p.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
            row_p = cur_p.fetchone()
            cur_p.close(); _release_conn(conn_p)
            if not row_p or row_p[0] != "pro":
                return jsonify({"errore":"Whisper è disponibile nel piano Pro"}), 403
        except Exception:
            pass
    if "audio" not in request.files:
        return jsonify({"errore":"file audio mancante"}), 400
    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()
    lang = request.args.get("lang","it")
    try:
        import ai_gateway as GW
        testo = GW.route_stt(audio_bytes, filename=audio_file.filename or "audio.webm", language=lang)
        if not testo:
            return jsonify({"errore":"trascrizione vuota"}), 422
        return jsonify({"trascrizione":testo,"lang":lang})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/vision", methods=["POST"])
def vision():
    """Analisi immagine via OpenAI Vision gpt-4o-mini.
    Accetta foto di schede tecniche, etichette, piatti.
    Pro-only."""
    token = request.headers.get("X-Token","") or (request.json or {}).get("token","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if DATABASE_URL:
        try:
            import psycopg2
            conn_v = _get_conn()
            cur_v = conn_v.cursor()
            cur_v.execute("SELECT piano FROM utenti WHERE id=%s", (user_id,))
            row_v = cur_v.fetchone()
            cur_v.close(); _release_conn(conn_v)
            if not row_v or row_v[0] != "pro":
                return jsonify({"errore":"Vision è disponibile nel piano Pro"}), 403
        except Exception:
            pass
    if "immagine" not in request.files:
        return jsonify({"errore":"immagine mancante"}), 400
    img_file = request.files["immagine"]
    img_bytes = img_file.read()
    media_type = img_file.content_type or "image/jpeg"
    lang = request.args.get("lang","it")
    prompt = (
        "Sei un esperto di chimica degli alimenti. "
        "Analizza questa immagine e identifica: "
        "1) Se è una scheda tecnica: estrai tutti i parametri fisici (pH, Aw, Brix, ABV, temperatura, ecc.) "
        "2) Se è un piatto/drink: identifica gli ingredienti principali e suggerisci i fenomeni fisici rilevanti "
        "3) Se è un'etichetta: estrai ingredienti, valori nutrizionali, parametri rilevanti. "
        f"Rispondi in {'italiano' if lang=='it' else 'English'}, in modo sintetico e professionale."
    )
    try:
        import ai_gateway as GW
        risposta = GW.route_vision(img_bytes, prompt, media_type=media_type)
        return jsonify({"analisi":risposta,"lang":lang})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/composti/<ingrediente>")
def composti_ingrediente(ingrediente):
    """FL4 — Composti aromatici di un ingrediente da PubChem NIH (pubblico dominio).
    Restituisce i composti volatili con profilo aromatico."""
    import unicodedata
    def _norm(s):
        s = s.lower().strip()
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.replace(" ","_").replace("-","_")

    ALIAS_IT = {
        "limone":"lemon","lime":"lime","arancia":"orange_peel","arancia_dolce":"sweet_orange",
        "pompelmo":"grapefruit","bergamotto":"bergamot","mandarino":"mandarin",
        "yuzu":"yuzu","cedro":"citrus","agrumi":"citrus",
        "aglio":"garlic","cipolla":"onion","scalogno":"shallot","porro":"leek",
        "burro":"butter","panna":"cream","latte":"milk","uova":"egg","uovo":"egg",
        "vaniglia":"vanilla","caffe":"coffee","caffè":"coffee","espresso":"coffee",
        "menta":"peppermint","menta piperita":"peppermint","menta verde":"spearmint",
        "basilico":"basil","timo":"thyme","origano":"oregano","rosmarino":"rosemary",
        "salvia":"sage","finocchio":"fennel","aneto":"dill","coriandolo":"coriander",
        "prezzemolo":"parsley","erba cipollina":"chive","maggiorana":"marjoram",
        "lavanda":"lavender","dragoncello":"tarragon","menta romana":"spearmint",
        "cannella":"cinnamon","garofano":"clove","noce moscata":"nutmeg",
        "zenzero":"ginger","pepe nero":"black_pepper","pepe":"black_pepper",
        "cardamomo":"cardamom","cumino":"cumin","curcuma":"turmeric",
        "zafferano":"saffron","anice":"anise","anice stellato":"star_anise",
        "fieno greco":"fenugreek","paprika":"paprika","peperoncino":"chili",
        "senape":"mustard","rafano":"horseradish","wasabi":"wasabi",
        "nocciola tostata":"roasted_hazelnut","nocciola":"hazelnut",
        "mandorla":"almond","noce":"walnut","pistacchio":"pistachio",
        "cocco":"coconut","arachide":"peanut","sesamo":"sesame","pino":"pine",
        "cioccolato":"chocolate","cacao":"cocoa","cioccolato fondente":"dark_chocolate",
        "cioccolato al latte":"chocolate",
        "lampone":"raspberry","fragola":"strawberry","mela":"apple","mela verde":"apple",
        "pera":"pear","banana":"banana","ananas":"pineapple","mango":"mango",
        "pesca":"peach","albicocca":"apricot","prugna":"plum","susina":"plum",
        "ciliegia":"cherry","uva":"grape","fico":"fig","melograno":"pomegranate",
        "melone":"melon","anguria":"watermelon","kiwi":"kiwi","papaya":"papaya",
        "mirtillo":"blueberry","ribes nero":"black_currant","ribes rosso":"red_currant",
        "mora":"blackberry","uva spina":"gooseberry","sambuco":"elderberry",
        "pomodoro":"tomato","cetriolo":"cucumber","carota":"carrot",
        "sedano":"celery","patata":"potato","patata dolce":"sweet_potato",
        "barbabietola":"beet","ravanello":"radish","carciofo":"artichoke",
        "asparago":"asparagus","peperone":"bell_pepper","melanzana":"eggplant",
        "zucchina":"zucchini","zucca":"pumpkin","spinaci":"spinach",
        "cavolo":"cabbage","cavolfiore":"cauliflower","broccoli":"broccoli",
        "mais":"corn","piselli":"pea","funghi":"mushroom","tartufo":"truffle",
        "funghi porcini":"mushroom","fungo":"mushroom",
        "vino":"wine","vino bianco":"white_wine","vino rosso":"red_wine",
        "champagne":"champagne","prosecco":"wine","spumante":"wine",
        "birra":"beer","birra ipa":"beer_ipa","birra weizen":"beer_weizen",
        "birra lager":"beer_lager","birra stout":"stout","birra porter":"porter",
        "whiskey":"whiskey","whisky":"scotch_whisky","bourbon":"bourbon",
        "rum":"rum","gin":"gin","vodka":"vodka","tequila":"tequila",
        "cognac":"cognac","brandy":"brandy","mezcal":"mezcal",
        "grappa":"grappa","sherry":"sherry","porto":"port",
        "aceto":"vinegar","aceto balsamico":"vinegar","salsa di soia":"soy_sauce",
        "miso":"miso","kimchi":"kimchi","crauti":"sauerkraut","kefir":"kefir",
        "yogurt":"yogurt","yogurt greco":"yogurt",
        "parmigiano":"parmesan","parmigiano reggiano":"parmesan",
        "cheddar":"cheddar","brie":"brie","camembert":"camembert",
        "mozzarella":"mozzarella","ricotta":"ricotta","grana":"parmesan",
        "formaggio capra":"goat_cheese","gorgonzola":"blue_cheese",
        "roquefort":"blue_cheese","formaggio erborinato":"blue_cheese",
        "pane":"bread","pane di segale":"rye_bread","pasta madre":"sourdough",
        "lievito madre":"sourdough","lievito":"yeast","malto":"malt",
        "luppolo":"hops","orzo":"barley","frumento":"wheat",
        "manzo":"beef","maiale":"pork","pollo":"chicken","agnello":"lamb",
        "anatra":"duck","tacchino":"turkey","pancetta":"bacon","prosciutto":"ham",
        "salsiccia":"sausage","carne arrosto":"roasted_meat","brodo":"broth",
        "salmone":"salmon","tonno":"tuna","merluzzo":"cod","acciuga":"anchovy",
        "gamberetto":"shrimp","ostrica":"oyster","vongola":"clam",
        "calamaro":"squid","anguilla":"eel","pesce":"fish",
        "olio oliva":"olive_oil","olio di oliva":"olive_oil","olio":"olive_oil",
        "strutto":"lard","grasso":"fat","miele":"honey","sciroppo acero":"maple_syrup",
        "caramello":"caramel","zucchero":"sugar","sale":"salt",
        "the verde":"green_tea","tè verde":"green_tea",
        "the nero":"black_tea","tè nero":"black_tea",
        "the":"black_tea","tè":"black_tea","matcha":"matcha",
        "camomilla":"chamomile","rosa":"rose","gelsomino":"jasmine",
        "ginepro":"juniper","rabarbaro":"rhubarb",
        "popcorn":"popcorn","patatine":"potato_chip",
        "affumicato":"smoked_food","carne affumicata":"smoked_meat",
    }

    ing_lower = ingrediente.lower().strip()
    ing_norm = _norm(ingrediente)
    ahn_name = ALIAS_IT.get(ing_lower) or ALIAS_IT.get(ing_norm.replace("_"," ")) or ing_norm

    try:
        conn = _get_conn()
        conn.autocommit = True
        cur = conn.cursor()

        # Cerca composti PubChem collegati a questo ingrediente
        ahn_ids = [
            f"ahn_{ahn_name}",
            f"ahn_{ahn_name.replace('_',' ')}",
            f"ahn_{ahn_name.replace(' ','_')}",
        ]
        cur.execute('''
            SELECT DISTINCT n.id, n.name, n.data
            FROM nodes n
            JOIN edges e ON e.to_id = n.id
            WHERE e.from_id IN %s
            AND e.relation = 'contiene_composto'
            AND n.id LIKE 'pub_%%'
            ORDER BY n.name
            LIMIT 15
        ''', (tuple(ahn_ids),))

        rows = cur.fetchall()

        # Fallback fuzzy
        if not rows:
            cur.execute('''
                SELECT DISTINCT n.id, n.name, n.data
                FROM nodes n
                JOIN edges e ON e.to_id = n.id
                JOIN nodes ing ON e.from_id = ing.id
                WHERE ing.name ILIKE %s
                AND e.relation = \'contiene_composto\'
                AND n.id LIKE \'pub_%%\'
                ORDER BY n.name LIMIT 10
            ''', (f"%{ahn_name.replace('_',' ')}%",))
            rows = cur.fetchall()

        composti = []
        for row in rows:
            nid, nome, data = row
            d = data if isinstance(data, dict) else {}
            composti.append({
                "nome": nome.replace("_"," "),
                "aroma": d.get("aroma",""),
                "formula": d.get("formula",""),
                "pubchem_cid": d.get("pubchem_cid",""),
                "fonte": "PubChem NIH"
            })

        return jsonify({
            "ingrediente": ingrediente,
            "composti": composti,
            "nota": "Composti aromatici volatili principali — PubChem NIH (pubblico dominio)",
            "count": len(composti)
        })
    except Exception as e:
        try: _release_conn(conn)
        except: pass
        return jsonify({"errore": str(e), "composti": []}), 500



@bp.route("/v1/ricette")
def api_ricette_list():
    """Lista ricette ancorate ai fenomeni. ?disc=bar&lang=it"""
    import json as _j
    from db import carica_grafo
    disc = request.args.get("disc","")
    lang = request.args.get("lang","it")
    fenomeno = request.args.get("fenomeno","").strip()
    db = carica_grafo()
    SEL = "SELECT id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,abbinamenti,vino_birra,scheda_en,scheda_es,procedimento,immagine,immagine_autore,immagine_url_fonte,tempo_prep,tempo_cottura,difficolta,porzioni,applicazioni,twist_di,nome_en,nome_es,procedimento_en,procedimento_es,applicazioni_en,applicazioni_es,punto_critico_en,punto_critico_es,esperimento,limite,esperimento_en,esperimento_es,limite_en,limite_es,twist,twist_en,twist_es FROM ricette"
    COLS = ["id","nome","disciplina","descrizione","ingredienti","fenomeni","tecniche","numeri","punto_critico","abbinamenti","vino_birra","scheda_en","scheda_es","procedimento","immagine","immagine_autore","immagine_url_fonte","tempo_prep","tempo_cottura","difficolta","porzioni","applicazioni","twist_di","nome_en","nome_es","procedimento_en","procedimento_es","applicazioni_en","applicazioni_es","punto_critico_en","punto_critico_es","esperimento","limite","esperimento_en","esperimento_es","limite_en","limite_es","twist","twist_en","twist_es"]
    try:
        if disc:
            rows = db.execute(SEL + " WHERE disciplina=%s ORDER BY nome", (disc,))
        else:
            rows = db.execute(SEL + " ORDER BY disciplina,nome")
        result=[]
        def _parse(v):
            if v is None: return None
            if isinstance(v,(list,dict)): return v
            try: return _j.loads(v)
            except: return v
        for row in rows:
            r = dict(row) if hasattr(row,"keys") else dict(zip(COLS, row))
            desc = r.get("descrizione") or ""
            if lang=="en" and r.get("scheda_en"): desc=r["scheda_en"]
            elif lang=="es" and r.get("scheda_es"): desc=r["scheda_es"]
            vb = _parse(r.get("vino_birra")) or {}
            # arricchisci con link affiliati estratti dal testo
            if isinstance(vb, dict) and vb:
                vb_arricchito = dict(vb)
                if vb.get("vino"):
                    nome_v = _estrai_nome_bevanda(vb["vino"])
                    if nome_v:
                        vb_arricchito["vino_links"] = _link_vino_birra(nome_v, "vino")
                        vb_arricchito["vino_query"] = nome_v
                if vb.get("birra"):
                    nome_b = _estrai_nome_bevanda(vb["birra"])
                    if nome_b:
                        vb_arricchito["birra_links"] = _link_vino_birra(nome_b, "birra")
                        vb_arricchito["birra_query"] = nome_b
                vb = vb_arricchito
            nome_out = r.get("nome","")
            proc_out = _parse(r.get("procedimento")) or []
            appl_out = _parse(r.get("applicazioni")) or []
            pc_out = r.get("punto_critico") or ""
            esp_out = r.get("esperimento") or ""
            lim_out = r.get("limite") or ""
            tw_out = r.get("twist") or ""
            if lang=="en":
                if r.get("nome_en"): nome_out=r["nome_en"]
                if r.get("procedimento_en"): proc_out=_parse(r.get("procedimento_en")) or proc_out
                if r.get("applicazioni_en"): appl_out=_parse(r.get("applicazioni_en")) or appl_out
                if r.get("punto_critico_en"): pc_out=r["punto_critico_en"]
                if r.get("esperimento_en"): esp_out=r["esperimento_en"]
                if r.get("limite_en"): lim_out=r["limite_en"]
                if r.get("twist_en"): tw_out=r["twist_en"]
            elif lang=="es":
                if r.get("nome_es"): nome_out=r["nome_es"]
                if r.get("procedimento_es"): proc_out=_parse(r.get("procedimento_es")) or proc_out
                if r.get("applicazioni_es"): appl_out=_parse(r.get("applicazioni_es")) or appl_out
                if r.get("punto_critico_es"): pc_out=r["punto_critico_es"]
                if r.get("esperimento_es"): esp_out=r["esperimento_es"]
                if r.get("limite_es"): lim_out=r["limite_es"]
                if r.get("twist_es"): tw_out=r["twist_es"]
            fen_list = _parse(r.get("fenomeni")) or []
            if fenomeno:
                ids_norm = [str(f).strip() for f in fen_list] if isinstance(fen_list,list) else []
                if fenomeno not in ids_norm and not any(fenomeno in str(f) for f in ids_norm):
                    continue
            result.append({
                "id":r.get("id",""),"nome":nome_out,"disciplina":r.get("disciplina",""),
                "descrizione":desc,
                "ingredienti":_parse(r.get("ingredienti")) or [],
                "fenomeni":fen_list,
                "tecniche":_parse(r.get("tecniche")) or [],
                "numeri":_parse(r.get("numeri")) or {},
                "punto_critico":pc_out,
                "abbinamenti":_parse(r.get("abbinamenti")) or {},
                "vino_birra":vb,
                "procedimento":proc_out,
                "immagine":r.get("immagine") or "",
                "immagine_autore":r.get("immagine_autore") or "",
                "immagine_url_fonte":r.get("immagine_url_fonte") or "",
                "tempo_prep":r.get("tempo_prep"),
                "tempo_cottura":r.get("tempo_cottura"),
                "difficolta":r.get("difficolta") or "",
                "porzioni":r.get("porzioni") or "",
                "applicazioni":appl_out,
                "twist_di":r.get("twist_di") or None,
                "esperimento":esp_out,
                "limite":lim_out,
                "twist":tw_out
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"errore":str(e),"type":type(e).__name__,"tb":traceback.format_exc()[-300:]}), 500

@bp.route("/v1/ricetta/<rid>/twist", methods=["POST"])
def ricetta_twist(rid):
    """Twist: genera una variante di una ricetta esistente per creare voci-menu al volo.
    Body JSON: {modifica: 'rendi vegano' | 'versione bar' | 'sostituisci X con Y', salva: false, lang: 'it'}
    """
    import json as _j, re as _re, unicodedata
    from db import carica_grafo, _get_conn, _release_conn
    from builder import genera_twist
    body = request.json or {}
    modifica = body.get("modifica","").strip()
    lang = body.get("lang","it")
    salva = bool(body.get("salva", False))
    if not modifica:
        return jsonify({"errore":"modifica mancante (es. 'rendi vegano', 'versione bar')"}), 400
    db = carica_grafo()
    # carico la ricetta madre
    try:
        rows = db.execute("SELECT id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico FROM ricette WHERE id=%s", (rid,)).fetchall()
        row = rows[0] if rows else None
    except Exception as e:
        return jsonify({"errore":f"lettura ricetta: {e}"}), 500
    if not row:
        return jsonify({"errore":"ricetta madre non trovata"}), 404
    def _p(v):
        if v is None: return None
        if isinstance(v,(list,dict)): return v
        try: return _j.loads(v)
        except: return v
    madre = {"id":row["id"] if hasattr(row,"keys") else row[0],
             "nome":row["nome"] if hasattr(row,"keys") else row[1],
             "disciplina":row["disciplina"] if hasattr(row,"keys") else row[2],
             "ingredienti":_p(row["ingredienti"] if hasattr(row,"keys") else row[4]) or [],
             "fenomeni":_p(row["fenomeni"] if hasattr(row,"keys") else row[5]) or [],
             "numeri":_p(row["numeri"] if hasattr(row,"keys") else row[7]) or {},
             "punto_critico":(row["punto_critico"] if hasattr(row,"keys") else row[8]) or ""}
    variante = genera_twist(madre, modifica, lang=lang)
    if variante.get("errore"):
        return jsonify(variante), 422
    variante["twist_di"] = rid
    # salvataggio opzionale
    if salva and variante.get("nome"):
        try:
            slug = unicodedata.normalize("NFKD", variante["nome"].lower()).encode("ascii","ignore").decode()
            slug = _re.sub(r"[^a-z0-9]+","-",slug).strip("-")[:40]
            nid = f"ric-twist-{slug}"
            conn = _get_conn(); cur = conn.cursor()
            cur.execute("""INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,numeri,punto_critico,procedimento,applicazioni,tempo_prep,tempo_cottura,difficolta,porzioni,twist_di)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING""",
                (nid, variante["nome"], madre["disciplina"], variante.get("descrizione",""),
                 _j.dumps(variante.get("ingredienti",[]),ensure_ascii=False),
                 _j.dumps(variante.get("fenomeni",[]),ensure_ascii=False),
                 _j.dumps(variante.get("numeri",{}),ensure_ascii=False),
                 variante.get("punto_critico",""),
                 _j.dumps(variante.get("procedimento",[]),ensure_ascii=False),
                 _j.dumps(variante.get("applicazioni",[]),ensure_ascii=False),
                 variante.get("tempo_prep"), variante.get("tempo_cottura"),
                 variante.get("difficolta",""), variante.get("porzioni",""), rid))
            conn.commit(); cur.close(); _release_conn(conn)
            variante["_salvata"] = True; variante["id"] = nid
        except Exception as se:
            variante["_salvata"] = False; variante["_errore_salvataggio"] = str(se)
    return jsonify(variante)

@bp.route("/v1/tecniche")
def api_tecniche_list():
    """Lista tecniche (nodi type='Tecnica'). ?disc=cucina&lang=it&famiglia=calore_secco"""
    import json as _j
    from db import carica_grafo
    disc = request.args.get("disc","")
    lang = request.args.get("lang","it")
    famiglia = request.args.get("famiglia","")
    db = carica_grafo()
    try:
        rows = db.execute(
            "SELECT id, name, data FROM nodes WHERE type='Tecnica' ORDER BY name"
        ).fetchall()
        result = []
        for row in rows:
            r = dict(row) if hasattr(row,"keys") else {"id":row[0],"name":row[1],"data":row[2]}
            data = r.get("data") or {}
            if isinstance(data, str):
                try: data = _j.loads(data)
                except: data = {}
            # filtro per disciplina
            if disc and data.get("disciplina") not in (disc, "trasversale"):
                continue
            if famiglia and data.get("famiglia") != famiglia:
                continue
            scheda = data.get("scheda","")
            if lang=="en" and data.get("scheda_en"): scheda = data["scheda_en"]
            elif lang=="es" and data.get("scheda_es"): scheda = data["scheda_es"]
            result.append({
                "id": r.get("id",""),
                "nome": r.get("name",""),
                "famiglia": data.get("famiglia",""),
                "disciplina": data.get("disciplina",""),
                "scheda": scheda,
                "numeri": data.get("numeri",""),
                "esecuzione": data.get("esecuzione",""),
                "errori_comuni": data.get("errori_comuni",""),
                "fenomeni_sfruttati": data.get("fenomeni_sfruttati",[]),
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"errore":str(e),"tb":traceback.format_exc()[-300:]}), 500

@bp.route("/v1/tecnica/<tec_id>")
def api_tecnica_dettaglio(tec_id):
    """Dettaglio di una tecnica: scheda completa + ricette che la usano + fenomeni sfruttati."""
    import json as _j
    from db import carica_grafo
    lang = request.args.get("lang","it")
    db = carica_grafo()
    try:
        # la tecnica
        row = db.execute("SELECT id, name, data FROM nodes WHERE id=%s AND type='Tecnica'", (tec_id,)).fetchone()
        if not row:
            return jsonify({"errore":"tecnica non trovata"}), 404
        r = dict(row) if hasattr(row,"keys") else {"id":row[0],"name":row[1],"data":row[2]}
        data = r.get("data") or {}
        if isinstance(data,str):
            try: data=_j.loads(data)
            except: data={}
        scheda = data.get("scheda","")
        if lang=="en" and data.get("scheda_en"): scheda=data["scheda_en"]
        elif lang=="es" and data.get("scheda_es"): scheda=data["scheda_es"]

        # ricette che usano questa tecnica (JSONB contains)
        ricette = []
        try:
            rows = db.execute(
                "SELECT id, nome, disciplina FROM ricette WHERE tecniche @> %s::jsonb ORDER BY nome",
                (_j.dumps([tec_id]),)
            ).fetchall()
            for rr in rows:
                rd = dict(rr) if hasattr(rr,"keys") else {"id":rr[0],"nome":rr[1],"disciplina":rr[2]}
                ricette.append(rd)
        except Exception:
            pass

        # fenomeni sfruttati (dalla data)
        fenomeni = data.get("fenomeni_sfruttati",[])

        return jsonify({
            "id": r.get("id",""),
            "nome": r.get("name",""),
            "famiglia": data.get("famiglia",""),
            "disciplina": data.get("disciplina",""),
            "scheda": scheda,
            "numeri": data.get("numeri",""),
            "esecuzione": data.get("esecuzione",""),
            "errori_comuni": data.get("errori_comuni",""),
            "fenomeni_sfruttati": fenomeni,
            "ricette_che_la_usano": ricette
        })
    except Exception as e:
        import traceback
        return jsonify({"errore":str(e),"tb":traceback.format_exc()[-300:]}), 500

# ── ARRICCHIMENTO BEACHHEAD BAR: abbinamenti curati per gli spiriti chiave ──
# Il dataset Ahn è di ingredienti alimentari, non di distillati: vodka/campari/
# aperol hanno pochi o zero composti mappati. Questi abbinamenti sono da PRATICA
# BAR reale (classici verificati), non da composti aromatici. Curati a mano,
# validabili. Formato uniforme con l'output Ahn: {ingrediente, composto, overlap, perche}.
_ABBINAMENTI_BAR = {
    "vodka": ["lime", "zenzero", "mirtillo", "pepe nero", "basilico", "cetriolo", "pompelmo", "menta"],
    "campari": ["arancia", "pompelmo", "vermut rosso", "soda", "prosecco", "bergamotto"],
    "aperol": ["prosecco", "arancia", "soda", "pompelmo", "timo"],
    "gin": ["tè nero", "cannella", "noce moscata", "rosmarino", "ginepro", "cetriolo", "lime", "cardamomo"],
    "tequila": ["lime", "pompelmo", "peperoncino", "coriandolo", "agave", "arancia", "pomodoro"],
    "rum": ["lime", "menta", "zucchero di canna", "ananas", "cocco", "cannella", "vaniglia", "caffè"],
    "whisky": ["arancia", "miele", "zenzero", "cannella", "ciliegia", "cioccolato", "torba"],
    "vermut rosso": ["arancia", "gin", "campari", "chiodi di garofano", "vaniglia"],
    "vermut": ["arancia", "gin", "campari", "chiodi di garofano", "vaniglia"],
    "mezcal": ["lime", "peperoncino", "arancia", "ananas", "sale affumicato"],
    "prosecco": ["aperol", "campari", "pesca", "sambuco", "fragola"],
}
def _fascia_affinita(overlap, lang="it"):
    """Fascia di affinità qualitativa, trilingue."""
    try:
        n = float(overlap)
    except Exception:
        n = 0
    _T = {
        "molto_alta": {"it": "affinità molto alta", "en": "very high affinity", "es": "afinidad muy alta"},
        "alta": {"it": "affinità alta", "en": "high affinity", "es": "afinidad alta"},
        "media": {"it": "affinità media", "en": "medium affinity", "es": "afinidad media"},
        "presente": {"it": "affinità presente", "en": "some affinity", "es": "afinidad presente"},
        "debole": {"it": "affinità debole", "en": "weak affinity", "es": "afinidad débil"},
    }
    if lang not in ("it", "en", "es"): lang = "it"
    if n >= 100: k = "molto_alta"
    elif n >= 50: k = "alta"
    elif n >= 20: k = "media"
    elif n >= 5: k = "presente"
    else: k = "debole"
    return _T[k][lang]

def _perche_affinita(overlap, lang="it"):
    try:
        n = float(overlap)
    except Exception:
        n = 0
    _T = {
        "alta": {"it": "condividono molti composti aromatici: abbinamento robusto",
                 "en": "they share many aroma compounds: robust pairing",
                 "es": "comparten muchos compuestos aromáticos: maridaje robusto"},
        "media": {"it": "condividono diversi composti aromatici: buona base di abbinamento",
                  "en": "they share several aroma compounds: good pairing base",
                  "es": "comparten varios compuestos aromáticos: buena base de maridaje"},
        "bassa": {"it": "condividono alcuni composti aromatici",
                  "en": "they share some aroma compounds",
                  "es": "comparten algunos compuestos aromáticos"},
    }
    if lang not in ("it", "en", "es"): lang = "it"
    if n >= 50: return _T["alta"][lang]
    if n >= 20: return _T["media"][lang]
    return _T["bassa"][lang]

def _abbinamenti_bar_curati(ingrediente, max_n=8):
    key = ingrediente.strip().lower()
    lista = _ABBINAMENTI_BAR.get(key)
    if not lista:
        return None
    return [{
        "ingrediente": x,
        "composto": "abbinamento da pratica bar",
        "overlap": 90 - i * 3,
        "perche": "abbinamento classico verificato nel bartending",
    } for i, x in enumerate(lista[:max_n])]

def _segreto_di(ingrediente):
    """Trova il segreto del mestiere per un ingrediente, se presente nel suo nodo.
    Preferisce: match esatto sul nome > nodo che HA un segreto > primo parziale."""
    try:
        from db import carica_grafo, _dati
        db = carica_grafo()
        ing_it = ingrediente.lower().replace("_", " ").strip()
        # prendo TUTTI i candidati (esatti e parziali), poi scelgo il migliore
        righe = db.execute(
            "SELECT name, data FROM nodes WHERE type='Ingrediente' AND (lower(name)=? OR lower(name) LIKE ?)",
            (ing_it, f"%{ing_it}%")).fetchall()
        if not righe:
            return None
        # 1) match esatto sul nome che ha un segreto
        for r in righe:
            if (r["name"] or "").lower() == ing_it:
                seg = _dati(r["data"]).get("segreto")
                if seg:
                    return seg
        # 2) qualsiasi candidato che abbia un segreto
        for r in righe:
            seg = _dati(r["data"]).get("segreto")
            if seg:
                return seg
    except Exception:
        pass
    return None

def _display_name_locale(nome_en_raw, node_id, lang, fallback):
    """Knowledge Layer Opzione B: restituisce il nome dell'ingrediente nella lingua richiesta.
    Legge names {it,en,es} dal nodo. Carica il grafo internamente (robusto)."""
    if lang not in ("it", "en", "es"):
        lang = "it"
    try:
        if node_id:
            from db import carica_grafo as _cgl
            _dbl = _cgl()
            row = _dbl.execute("SELECT data FROM nodes WHERE id=?", (node_id,)).fetchone()
            if row:
                d = row["data"] if hasattr(row, "keys") and isinstance(row["data"], dict) else None
                if d is None:
                    import json as _j2
                    _raw = row["data"] if hasattr(row, "keys") else row[0]
                    d = _raw if isinstance(_raw, dict) else (_j2.loads(_raw) if _raw else {})
                names = d.get("names") or {}
                if names.get(lang):
                    return names[lang]
                if lang == "en" and names.get("en"):
                    return names["en"]
    except Exception:
        pass
    return fallback


@bp.route("/v1/abbina/<ingrediente>")
def abbina(ingrediente):
    """FL3 — Abbinamenti aromatici dal grafo Ahn 2011 (edges abbinamento_aromatico).
    Cerca per nome italiano (con mappa di traduzione) o inglese direttamente.
    Sempre marcato come ipotesi eurisitca, mai come legge."""
    if not _check_rate_limit(request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()):
        return jsonify({"errore":"Troppe richieste. Attendi un momento."}), 429
    # VALIDAZIONE PLAUSIBILITÀ: un ingrediente vero ha vocali e non è una stringa casuale.
    # Evita di inventare abbinamenti per input senza senso (xyzabc, qwerty) — questione di credibilità.
    _ing_check = (ingrediente or "").lower().strip()
    _lettere = [c for c in _ing_check if c.isalpha()]
    _vocali = sum(1 for c in _lettere if c in "aeiouàèéìòù")
    _consec_cons = 0; _max_cons = 0
    for c in _ing_check:
        if c.isalpha() and c not in "aeiouàèéìòù":
            _consec_cons += 1; _max_cons = max(_max_cons, _consec_cons)
        else:
            _consec_cons = 0
    # rapporto vocali: un ingrediente vero ha almeno ~25% di vocali. "xyzabc" ne ha 1 su 6 = 17%.
    _rapp_voc = (_vocali / len(_lettere)) if _lettere else 0
    _implausibile = (len(_lettere) >= 4 and (_vocali == 0 or _max_cons >= 5 or _rapp_voc < 0.22
                     or _ing_check in ("qwerty", "qwertyuiop", "asdf", "asdfgh", "test", "aaaa", "xxxx")))
    if _implausibile:
        return jsonify({"ingrediente": ingrediente, "abbinamenti": [],
                        "nota": "Ingrediente non riconosciuto. Controlla l'ortografia o prova un ingrediente diverso.",
                        "non_riconosciuto": True})
    _seg = _segreto_di(ingrediente)  # segreto del mestiere, se c'è
    # CONFIDENCE LAYER: rilevo il livello di evidenza dell'ingrediente cercato (A/B/C)
    _evidence = "C"  # default: stima (finché non trovo dati)
    try:
        from db import carica_grafo as _cg0
        _db0 = _cg0()
        _n0 = _db0.execute(
            "SELECT data FROM nodes WHERE type='Ingrediente' "
            "AND (lower(name)=lower(?) OR id=? OR id=?) LIMIT 1",
            (ingrediente.strip(), ingrediente.strip(),
             "ahn_" + ingrediente.strip().lower().replace(" ", "_"))).fetchone()
        if _n0:
            _d0 = _n0["data"] if hasattr(_n0, "keys") and isinstance(_n0["data"], dict) else None
            if _d0 is None:
                _raw0 = _n0["data"] if hasattr(_n0, "keys") else _n0[0]
                _d0 = _raw0 if isinstance(_raw0, dict) else (json.loads(_raw0) if _raw0 else {})
            _evidence = _d0.get("evidence_level", "C")
    except Exception:
        pass
    request.environ["_evidence_level"] = _evidence
    # ITALIAN KNOWLEDGE LAYER: se è un ingrediente italiano del layer, eredita gli abbinamenti
    # dal padre Ahn (il nome italiano si mostra, la chimica viene dal padre scientifico).
    try:
        from db import carica_grafo as _cg
        _dbi = _cg()
        _il = _dbi.execute(
            "SELECT id, name, padre_ahn_id, data FROM nodes WHERE type='Ingrediente' "
            "AND padre_ahn_id IS NOT NULL AND (lower(name)=lower(?) OR id=?) LIMIT 1",
            (ingrediente.strip(), ingrediente.strip())).fetchone()
        if _il and _il["padre_ahn_id"]:
            _padre = _dbi.execute("SELECT name FROM nodes WHERE id=?", (_il["padre_ahn_id"],)).fetchone()
            if _padre:
                # ricalcolo gli abbinamenti usando il NOME DEL PADRE, ma mantengo il nome italiano nel titolo
                _nome_it = _il["name"]
                _dic = ""
                try:
                    _dd = _il["data"] if isinstance(_il["data"], dict) else json.loads(_il["data"] or "{}")
                    _dic = _dd.get("dicitura", "")
                except Exception:
                    pass
                ingrediente_padre = _padre["name"]
                # sostituisco l'ingrediente cercato col padre per il resto della funzione
                ingrediente = ingrediente_padre
                # marco che è un ingrediente italiano ereditato (il frontend mostra nome_it + dicitura)
                request.environ["_italian_layer"] = {"nome_it": _nome_it, "dicitura": _dic, "padre": ingrediente_padre}
    except Exception:
        pass
    # ARRICCHIMENTO BAR: se è uno spirito curato, usa gli abbinamenti da pratica bar.
    # (Il dataset Ahn ha pochi/zero composti per i distillati — vodka, campari, ecc.)
    _bar_curati = _abbinamenti_bar_curati(ingrediente)
    if _bar_curati:
        return jsonify({
            "segreto": _seg,
            "ingrediente": ingrediente,
            "abbinamenti": _pulisci_abbinamenti(_bar_curati),
            "nota": "Abbinamenti classici del bartending, verificati nella pratica.",
            "fonte": "Matter Lab — curatela bar",
        })
    # mappa italiano → nome Ahn (inglese con underscore)
    ALIAS_IT = {
        "pomodoro":"tomato","limone":"lemon","aglio":"garlic","cipolla":"onion",
        "burro":"butter","panna":"cream","latte":"milk","uova":"egg","uovo":"egg",
        "basilico":"basil","prezzemolo":"parsley","rosmarino":"rosemary",
        "timo":"thyme","menta":"mint",
        "cioccolato":"cocoa",
        "caffe":"coffee","caffè":"coffee",
        "fragola":"strawberry","lampone":"raspberry","mela":"apple",
        "pera":"pear","banana":"banana","arancia":"orange","limetta":"lime","lime":"lime",
        "zenzero":"ginger","pepe":"black_pepper","sale":"salt",
        "aceto":"vinegar","vino":"wine","birra":"beer","rum":"rum",
        "whisky":"whiskey","gin":"gin","vodka":"vodka",
        "salmone":"salmon","tonno":"tuna","gambero":"shrimp",
        "manzo":"beef","pollo":"chicken","maiale":"pork","agnello":"lamb",
        "formaggio":"cheese","parmigiano":"parmesan","mozzarella":"mozzarella",
        "olio":"olive_oil","olio d oliva":"olive_oil","sesamo":"sesame",
        "mandorla":"almond","nocciola":"hazelnut","noci":"walnut","noce":"walnut",
        "caffè espresso":"espresso","espresso":"espresso",
        "ananas":"pineapple","mango":"mango","cocco":"coconut",
        "zucca":"pumpkin","carota":"carrot","sedano":"celery",
        "funghi":"mushroom","porcini":"porcini_mushroom",
        "tè":"tea","te":"tea","miele":"honey","zucchero":"sugar",
        "peperoncino":"chili","peperone":"bell_pepper","melanzana":"eggplant",
        # salumi e carni italiane
        "salame":"salami","salumi":"salami","prosciutto":"prosciutto",
        "pancetta":"bacon","guanciale":"guanciale","mortadella":"mortadella",
        "speck":"smoked_ham","salsiccia":"pork_sausage",
        "bresaola":"beef","lardo":"lard","coppa":"pork",
        # formaggi italiani
        "ricotta":"ricotta","pecorino":"pecorino","grana":"parmesan",
        "gorgonzola":"blue_cheese","taleggio":"cheese","asiago":"cheese",
        "scamorza":"cheese","provolone":"provolone","caciocavallo":"cheese",
        "burrata":"mozzarella","stracciatella":"mozzarella",
        # verdure stagionali
        "zucchine":"zucchini","pomodorino":"tomato","ciliegino":"tomato",
        "rucola":"arugula",
        "radicchio":"radicchio","cicoria":"chicory","finocchio":"fennel",
        "carciofo":"artichoke","asparago":"asparagus","pisello":"pea",
        "fava":"fava_bean","spinaci":"spinach","spinacio":"spinach",
        "cavolo":"cabbage","cavolfiore":"cauliflower",
        "broccolo":"broccoli","bietola":"beet","barbabietola":"beet",
        "fagiolino":"green_bean","fagiolo":"bean","ceci":"chickpea",
        "lenticchie":"lentil","cipollotto":"onion","porro":"leek",
        # frutta
        "fico":"fig","albicocca":"apricot","pesca":"peach","nettarina":"peach",
        "susina":"plum","prugna":"plum","caco":"persimmon","cachi":"persimmon",
        "melograno":"pomegranate","mora":"blackberry","ribes":"currant",
        "mirtillo":"blueberry",
        "pompelmo":"grapefruit","bergamotto":"bergamot",
        "cedro":"citron","uva":"grape","castagna":"chestnut",
        # pesce
        "baccalà":"cod","acciuga":"anchovy","alice":"anchovy",
        "seppia":"squid","polpo":"octopus","calamaro":"squid",
        "orata":"sea_bream","branzino":"sea_bass","sgombro":"mackerel",
        "vongola":"clam","cozza":"mussel","ostrica":"oyster",
        # pasta e cereali
        "pasta":"pasta","riso":"rice","farro":"spelt","orzo":"barley",
        "mais":"corn","farina":"flour","pane":"bread",
        # condimenti e grassi
        "olio extravergine":"olive_oil","evo":"olive_oil",
        "burro di cacao":"cocoa_butter","tahini":"sesame",
        "aceto balsamico":"balsamic_vinegar","salsa di soia":"soy_sauce",
        # erbe aromatiche
        "maggiorana":"marjoram","origano":"oregano","salvia":"sage",
        "alloro":"bay_leaf","erba cipollina":"chive",
        "finocchietto":"fennel","dragoncello":"tarragon",
        # spezie
        "noce moscata":"nutmeg","cardamomo":"cardamom","curcuma":"turmeric",
        "zafferano":"saffron","anice stellato":"star_anise",
        "chiodo di garofano":"clove","paprica":"paprika",
        # distillati e vini
        "amaro":"amaro","campari":"amaro","aperol":"amaro",
        "grappa":"grappa","cognac":"cognac","brandy":"brandy",
        "prosecco":"sparkling_wine","champagne":"sparkling_wine",
        "vino rosso":"red_wine","vino bianco":"white_wine",
        "marsala":"wine","vermouth":"vermouth",
        # dolci e dessert
        "cioccolato fondente":"dark_chocolate","cioccolato al latte":"milk_chocolate",
        "cioccolato bianco":"white_chocolate","cacao":"cocoa",
        "caramello":"caramel","vaniglia":"vanilla","cannella":"cinnamon",
        "pistacchio":"pistachio","mandorle":"almond",
    }
    # normalizza l'input
    ing_norm = ingrediente.lower().replace("-","_").replace(" ","_")
    ing_it = ingrediente.lower().replace("_"," ")
    # cerca alias italiano
    ahn_name = ALIAS_IT.get(ing_it) or ALIAS_IT.get(ing_norm.replace("_"," "))
    # GRAFO-FIRST: se non c'è alias italiano ma l'input assomiglia a un nome Ahn (inglese, o già
    # normalizzato), provalo come ahn_name così i search_terms includono ahn_<nome> e il grafo
    # (dati veri) ha priorità sull'AI. Solo assegnazione, nessuna query rischiosa.
    if not ahn_name and ing_norm and all(c.isalpha() or c == "_" for c in ing_norm):
        ahn_name = ing_norm
    # se non c'è alias, prova diretto
    search_terms = []
    if ahn_name:
        search_terms.append(f"ahn_{ahn_name}")
        search_terms.append(f"ahn_{ahn_name.replace(' ','_')}")
    search_terms.append(f"ahn_{ing_norm}")
    search_terms.append(f"ahn_{ing_norm.replace('_',' ')}")

    if not DATABASE_URL:
        return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,"abbinamenti":[],
                        "nota":"flavor network non disponibile"})
    try:
        import psycopg2, json as _j
        conn = _get_conn()
        cur = conn.cursor()
        rows = []

        # Pre-check: se non c'è alias Ahn, prova prima il dataset proprietario
        if not ahn_name:
            _ing_id_pre = f"ing-{ing_norm.replace(' ','-').replace('_','-')}"
            cur.execute("""
                SELECT id, name, data FROM nodes
                WHERE type='Ingrediente'
                AND (lower(name) = lower(%s) OR lower(id) = lower(%s)
                     OR lower(name) LIKE lower(%s))
                LIMIT 1
            """, (ing_it, _ing_id_pre, f"%{ing_it}%"))
            _pre_row = cur.fetchone()
            if _pre_row:
                _pre_data = _pre_row[2] if isinstance(_pre_row[2], dict) else _j.loads(_pre_row[2] or "{}")
                _pre_abbs = []
                for a in _pre_data.get("abbinamenti",{}).get("molecolari",[])[:5]:
                    _pre_abbs.append({"ingrediente":a.get("ingrediente_it",a.get("ingrediente_en","?")),
                        "composto":f"{a.get('overlap_score',50)} composti condivisi",
                        "overlap":float(a.get("overlap_score",50)),
                        "perche":a.get("meccanismo","affinità aromatica")})
                for a in _pre_data.get("abbinamenti",{}).get("contrasto",[])[:2]:
                    _pre_abbs.append({"ingrediente":a.get("ingrediente_it","?"),
                        "composto":"contrasto","overlap":30.0,
                        "perche":a.get("perche","contrasto fisico-percettivo")})
                # Integra con AI se abbinamenti sono meno di 4
                if _pre_abbs and len(_pre_abbs) >= 4:
                    cur.close(); _release_conn(conn)
                    return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,"abbinamenti":_pulisci_abbinamenti(_pre_abbs, ingrediente_base=ingrediente),
                        "fonte":"dataset Matter Lab",
                        "nota":"Abbinamenti da profilo sensoriale proprietario Matter Lab"})
                # Nodo trovato ma con pochi abbinamenti — arricchisci con AI
                _cat_pre = _pre_data.get("categoria","")
                _prof_pre = _pre_data.get("categorie_aromatiche",[])
                _lang_fl = request.args.get("lang", "it")
                _lingua_nome = {"it": "italiano", "en": "inglese", "es": "spagnolo"}.get(_lang_fl, "italiano")
                _ai_pre = ("Dammi 5 abbinamenti per " + str(ingrediente) +
                           " (" + str(_cat_pre) + ") con meccanismo fisico-chimico. "
                           "I nomi degli ingredienti e il meccanismo DEVONO essere in " + _lingua_nome + ". "
                           "JSON: {abbinamenti:[{ingrediente_it:str,meccanismo:str,overlap_score:int}]}")
                try:
                    _raw_pre = _haiku_raw(_ai_pre)
                    if _raw_pre:
                        import re as _re_pre
                        _mp = _re_pre.search(r'\{.*\}', _raw_pre, _re_pre.DOTALL)
                        if _mp:
                            _dp = _j.loads(_mp.group())
                            _ap = _dp.get("abbinamenti",[])
                            if _ap:
                                cur.close(); _release_conn(conn)
                                return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,
                                    "abbinamenti":_pulisci_abbinamenti([{"ingrediente":a.get("ingrediente_it","?"),
                                        "composto":{"it":"abbinamento aromatico","en":"aroma pairing","es":"maridaje aromático"}.get(request.args.get("lang","it"),"abbinamento aromatico"),
                                        "overlap":float(a.get("overlap_score",50)),
                                        "perche":a.get("meccanismo","affinità aromatica")}
                                        for a in _ap[:5]]),
                                    "fonte":"Matter Lab AI",
                                    "nota":"Abbinamenti generati da AI su profilo sensoriale"})
                except Exception:
                    pass

        for term in search_terms:
            cur.execute("""
                SELECT e.to_id, n.name,
                       (e.data->>'overlap')::numeric as overlap
                FROM edges e
                JOIN nodes n ON n.id = e.to_id
                WHERE e.relation = 'abbinamento_aromatico'
                AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
                AND (lower(e.from_id) = lower(%s)
                     OR lower(e.from_id) LIKE lower(%s))
                ORDER BY overlap DESC NULLS LAST LIMIT 40
            """, (term, f"%{term}%"))
            rows = cur.fetchall()
            if rows: break
        # fallback 1: cerca per nome parziale
        if not rows:
            cur.execute("""
                SELECT e.to_id, n.name,
                       (e.data->>'overlap')::numeric as overlap
                FROM edges e
                JOIN nodes n ON n.id = e.to_id
                WHERE e.relation = 'abbinamento_aromatico'
                AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
                AND lower(e.from_id) LIKE lower(%s)
                ORDER BY overlap DESC NULLS LAST LIMIT 15
            """, (f"%{ing_norm.replace('_','%')}%",))
            rows = cur.fetchall()
        # fallback 2: cerca nella mappa nomi italiani (flavor_nomi_it)
        if not rows:
            try:
                cur.execute("""
                    SELECT e.to_id, n.name,
                           (e.data->>'overlap')::numeric as overlap
                    FROM edges e
                    JOIN nodes n ON n.id = e.to_id
                    JOIN flavor_nomi_it fi ON fi.node_id = e.from_id
                    WHERE e.relation = 'abbinamento_aromatico'
                AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
                    AND (lower(fi.nome_it) LIKE lower(%s)
                         OR lower(fi.nome_en) LIKE lower(%s))
                    ORDER BY overlap DESC NULLS LAST LIMIT 15
                """, (f"%{ing_it}%", f"%{ing_it}%"))
                rows = cur.fetchall()
                if rows:
                    print(f"[NOMI_IT] '{ingrediente}' trovato via flavor_nomi_it", flush=True)
            except Exception as _fi_err:
                pass  # tabella non ancora popolata
        # Se Ahn ha trovato meno di 4 risultati, o tutti con lo stesso overlap (match fasullo),
        # prova il dataset proprietario più ricco
        if rows and len(rows) < 4:
            rows = []
        elif rows:
            overlaps = set(r[2] for r in rows if r[2] is not None)
            if len(overlaps) == 1:  # tutti lo stesso overlap = Ahn non ha dati reali
                rows = []

        # fallback 3: dataset proprietario Matter Lab (nodi Ingrediente)
        if not rows:
            try:
                cur.execute("""
                    SELECT e.to_id, n.name,
                           COALESCE((e.data->>'overlap')::numeric, 50) as overlap
                    FROM edges e
                    JOIN nodes n ON n.id = e.to_id
                    WHERE e.relation = 'abbinamento_aromatico'
                AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
                    AND e.from_id IN (
                        SELECT id FROM nodes WHERE type='Ingrediente'
                        AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                    )
                    ORDER BY overlap DESC NULLS LAST LIMIT 15
                """, (f"%{ing_it}%", f"%ing-{ing_norm.replace('_','-')}%"))
                rows = cur.fetchall()
                if rows:
                    print(f"[ML] '{ingrediente}' trovato via nodi Ingrediente", flush=True)
            except Exception as _ml_e:
                print(f"[ML ERR] {_ml_e}", flush=True)
        # fallback 4: abbinamenti da profilo sensoriale proprietario
        if not rows:
            try:
                # Cerca con più varianti del nome
                _ing_id = f"ing-{ing_norm.replace(' ','-').replace('_','-')}"
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type='Ingrediente'
                    AND (
                        lower(name) LIKE lower(%s)
                        OR lower(id) LIKE lower(%s)
                        OR lower(id) = lower(%s)
                        OR lower(name) = lower(%s)
                    )
                    LIMIT 1
                """, (f"%{ing_it}%", f"%{_ing_id}%", _ing_id, ing_it))
                ing_row = cur.fetchone()
                if ing_row:
                    ing_data = ing_row[2] if isinstance(ing_row[2], dict) else json.loads(ing_row[2] or "{}")
                    result_props = []
                    for a in ing_data.get("abbinamenti",{}).get("molecolari",[])[:5]:
                        result_props.append({
                            "ingrediente": a.get("ingrediente_it", a.get("ingrediente_en","?")),
                            "composto": f"{a.get('overlap_score',0)} composti condivisi",
                            "overlap": float(a.get("overlap_score",0)),
                            "perche": a.get("meccanismo","affinità aromatica")
                        })
                    for a in ing_data.get("abbinamenti",{}).get("contrasto",[])[:3]:
                        result_props.append({
                            "ingrediente": a.get("ingrediente_it","?"),
                            "composto": "contrasto",
                            "overlap": 30.0,
                            "perche": a.get("perche","contrasto fisico-percettivo")
                        })
                    if result_props:
                        cur.close(); _release_conn(conn)
                        return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,"abbinamenti":_pulisci_abbinamenti(result_props, ingrediente_base=ingrediente),
                            "fonte":"dataset Matter Lab",
                            "nota":"Abbinamenti da profilo sensoriale proprietario Matter Lab"})
                    # Nodo trovato ma senza abbinamenti nel JSON — genera via AI
                    if ing_row:
                        _nome_ing = ing_row[1]
                        _cat = (ing_row[2] if isinstance(ing_row[2],dict) else {}).get("categoria","")
                        _profilo = (ing_row[2] if isinstance(ing_row[2],dict) else {}).get("categorie_aromatiche",[])
                        _ai_prompt = (
                            f"Sei un esperto di chimica degli alimenti. "
                            f"Dammi 5 abbinamenti per '{_nome_ing}' ({_cat}, profilo: {', '.join(_profilo[:3])}) "
                            f"con il meccanismo fisico-chimico per ognuno. "
                            f"Formato JSON: {{abbinamenti:[{{ingrediente_it:str,meccanismo:str,overlap_score:int}}]}}"
                        )
                        try:
                            _ai_raw = _haiku_raw(_ai_prompt)
                            if _ai_raw:
                                import re as _re2
                                _m = _re2.search(r'\{.*\}', _ai_raw, _re2.DOTALL)
                                if _m:
                                    _ai_data = json.loads(_m.group())
                                    _ai_abbs = _ai_data.get("abbinamenti",[])
                                    result_props = [{"ingrediente":a.get("ingrediente_it","?"),
                                        "composto":f"{a.get('overlap_score',50)} composti condivisi",
                                        "overlap":float(a.get("overlap_score",50)),
                                        "perche":a.get("meccanismo","affinità aromatica")}
                                        for a in _ai_abbs[:5]]
                                    if result_props:
                                        cur.close(); _release_conn(conn)
                                        return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,
                                            "abbinamenti":_pulisci_abbinamenti(result_props, ingrediente_base=ingrediente),
                                            "fonte":"Matter Lab AI",
                                            "nota":"Abbinamenti generati da AI su profilo sensoriale"})
                        except Exception as _ai_e:
                            print(f"[AI ABB] {_ai_e}", flush=True)
            except Exception as _pe:
                print(f"[PROP ERR] {_pe}", flush=True)

        # fallback 5: AI diretto se nessun nodo trovato nel grafo
        if not rows:
            try:
                _ai_prompt5 = (
                    "Sei un esperto di chimica degli alimenti. "
                    + "Dammi 5 abbinamenti per " + str(ingrediente) + " con meccanismo fisico-chimico. "
                    + "Rispondi SOLO in JSON: {abbinamenti:[{ingrediente_it:str,meccanismo:str,overlap_score:int}]}"
                )
                _ai_raw5 = _haiku_raw(_ai_prompt5)
                if _ai_raw5:
                    import re as _re5
                    _m5 = _re5.search(r'\{.*\}', _ai_raw5, _re5.DOTALL)
                    if _m5:
                        _ai_data5 = json.loads(_m5.group())
                        _abbs5 = _ai_data5.get("abbinamenti",[])
                        if _abbs5:
                            cur.close(); _release_conn(conn)
                            return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,
                                "abbinamenti":_pulisci_abbinamenti([{"ingrediente":a.get("ingrediente_it","?"),
                                    "composto":{"it":"abbinamento aromatico","en":"aroma pairing","es":"maridaje aromático"}.get(request.args.get("lang","it"),"abbinamento aromatico"),
                                    "overlap":float(a.get("overlap_score",50)),
                                    "perche":a.get("meccanismo","affinità aromatica")}
                                    for a in _abbs5[:5]]),
                                "fonte":"Matter Lab AI",
                                "nota":"Abbinamenti generati da AI — ingrediente non ancora nel dataset molecolare"})
            except Exception as _ai5_e:
                print(f"[AI5] {_ai5_e}", flush=True)

        # fallback 2: ricerca semantica via embeddings OpenAI
        if not rows:
            try:
                import flavor_embeddings as FE, psycopg2 as _pg
                sem = FE.search_by_embedding(ingrediente, top_k=3)
                for _nid, _nname, _sim in sem:
                    if _sim > 0.72:
                        _c2 = _pg.connect(DATABASE_URL)
                        _cur2 = _c2.cursor()
                        _cur2.execute("""
                            SELECT e.to_id, n.name,
                                   (e.data->>'overlap')::numeric as overlap
                            FROM edges e
                            JOIN nodes n ON n.id = e.to_id
                            WHERE e.relation = 'abbinamento_aromatico'
                AND (n.data->>'visibility') IS DISTINCT FROM 'hidden'
                            AND e.from_id = %s
                            ORDER BY overlap DESC NULLS LAST LIMIT 15
                        """, (_nid,))
                        rows = _cur2.fetchall()
                        _cur2.close(); _release_conn(_c2)
                        if rows:
                            print(f"[EMBED] '{ingrediente}' → '{_nname}' (sim={_sim:.2f})", flush=True)
                            break
            except Exception as _ee:
                print(f"[EMBED FALLBACK] {_ee}", flush=True)
        cur.close(); _release_conn(conn)
        NOMI_IT = {
            "roasted beef":"manzo arrosto","beef":"manzo","chicken":"pollo",
            "pork":"maiale","lamb":"agnello","turkey":"tacchino",
            "salmon":"salmone","tuna":"tonno","shrimp":"gambero","cod":"merluzzo",
            "tomato":"pomodoro","garlic":"aglio","onion":"cipolla","carrot":"carota",
            "celery":"sedano","mushroom":"fungo","porcini mushroom":"porcini",
            "potato":"patata","eggplant":"melanzana","bell pepper":"peperone",
            "pumpkin":"zucca","zucchini":"zucchine",
            "apple":"mela","pear":"pera","strawberry":"fragola","raspberry":"lampone",
            "blueberry":"mirtillo","orange":"arancia","lemon":"limone","lime":"lime",
            "banana":"banana","pineapple":"ananas","mango":"mango","coconut":"cocco",
            "butter":"burro","cream":"panna","milk":"latte","cheese":"formaggio",
            "parmesan":"parmigiano","mozzarella":"mozzarella","yogurt":"yogurt",
            "egg":"uovo","olive oil":"olio d'oliva","sesame":"sesamo",
            "almond":"mandorla","hazelnut":"nocciola","walnut":"noce","peanut":"arachide",
            "coffee":"caffè","espresso":"espresso","tea":"tè","cocoa":"cacao",
            "chocolate":"cioccolato","vanilla":"vaniglia","honey":"miele","sugar":"zucchero",
            "basil":"basilico","rosemary":"rosmarino","thyme":"timo","mint":"menta",
            "parsley":"prezzemolo","cinnamon":"cannella","ginger":"zenzero",
            "black pepper":"pepe nero","chili":"peperoncino",
            "red wine":"vino rosso","white wine":"vino bianco","beer":"birra",
            "rum":"rum","whiskey":"whisky","gin":"gin","vodka":"vodka",
            "vinegar":"aceto","soy sauce":"salsa di soia",
            "mandarin":"mandarino","tangerine":"mandarino","grapefruit":"pompelmo",
            "concord grape":"uva concord","grape":"uva","fig":"fico",
            "leek":"porro","nira":"erba cipollina cinese","chive":"erba cipollina",
            "cheddar cheese":"cheddar","brie":"brie","camembert":"camembert",
            "cucumber":"cetriolo","zucchini":"zucchine","pumpkin":"zucca",
            "raw beef":"manzo crudo","cooked beef":"manzo cotto",
            "pork meat":"carne di maiale","lamb meat":"carne d'agnello",
            "white bread":"pane bianco","wheat bread":"pane di frumento",
            "rice":"riso","corn":"mais","oat":"avena",
            "olive":"oliva","capers":"capperi","anchovy":"acciuga",
            "lobster":"aragosta","crab":"granchio","mussel":"cozza","oyster":"ostrica",
            "lemon juice":"succo di limone","orange juice":"succo d'arancia",
            "apple juice":"succo di mela","tomato juice":"succo di pomodoro",
            "black coffee":"caffè nero","roasted coffee":"caffè tostato",
            "black tea":"tè nero","green tea":"tè verde","white tea":"tè bianco",
            "chamomile":"camomilla","peppermint":"menta piperita",
            "dark chocolate":"cioccolato fondente","milk chocolate":"cioccolato al latte",
            "caramel":"caramello","maple syrup":"sciroppo d'acero",
            "saffron":"zafferano","turmeric":"curcuma","cardamom":"cardamomo",
            "clove":"chiodo di garofano","nutmeg":"noce moscata","anise":"anice",
            "lavender":"lavanda","rose":"rosa","jasmine":"gelsomino",
            "citrus":"agrumi","citrus peel":"scorza d'agrumi","bitter orange":"arancia amara",
            "lemongrass":"citronella","kumquat":"kumquat","bergamot":"bergamotto",
            "grapefruit":"pompelmo","yuzu":"yuzu","blood orange":"arancia rossa",
            "elderflower":"fiori di sambuco","hibiscus":"ibisco","juniper":"ginepro",
            "coriander":"coriandolo","fennel":"finocchio","dill":"aneto","tarragon":"dragoncello",
            "sage":"salvia","oregano":"origano","marjoram":"maggiorana","bay leaf":"alloro",
            "star anise":"anice stellato","licorice":"liquirizia","cocoa powder":"cacao in polvere",
            "roasted almond":"mandorla tostata","pistachio":"pistacchio","pecan":"noce pecan",
            "cashew":"anacardo","macadamia":"macadamia","chestnut":"castagna",
            "cranberry":"mirtillo rosso","blackberry":"mora","cherry":"ciliegia","peach":"pesca",
            "apricot":"albicocca","plum":"prugna","melon":"melone","watermelon":"anguria",
            "passion fruit":"frutto della passione","lychee":"litchi","papaya":"papaya",
            "guava":"guava","kiwi":"kiwi","pomegranate":"melograno","date":"dattero",
            "raisin":"uvetta","prune":"prugna secca","currant":"ribes",
        }
        abbinamenti = []
        _lang_out = request.args.get("lang", "it")
        for r in rows:
            nome_en = r[1].replace("_"," ").lower() if r[1] else ""
            # fallback: se manca la traduzione IT usa il nome Ahn in Title Case
            nome_fallback = r[1].replace("_"," ").title() if r[1] else "sconosciuto"
            nome_it = NOMI_IT.get(nome_en, nome_fallback)
            # display_name locale-aware: usa names {it,en,es} dal nodo; per EN usa il nome Ahn
            if _lang_out == "en":
                nome_pulito = _display_name_locale(nome_en, r[0], "en", nome_fallback)
            elif _lang_out == "es":
                nome_pulito = _display_name_locale(nome_en, r[0], "es", nome_it)
            else:
                nome_pulito = _display_name_locale(nome_en, r[0], "it", nome_it)
            # salta i nodi senza nome
            if not nome_pulito or nome_pulito == "sconosciuto":
                continue
            overlap = float(r[2]) if r[2] else 0
            # ANTI-HUB (revisori): gli ingredienti-hub (tè nero, ecc.) con moltissimi collegamenti
            # schiacciano gli abbinamenti rari. Penalizzo l'overlap in modo log-inverso alla diffusione.
            import math as _math
            try:
                _to_id = r[0]
                _n_link = db.execute("SELECT COUNT(*) FROM edges WHERE from_id=? AND relation='abbinamento_aromatico'", (_to_id,)).fetchone()
                _cnt = (_n_link[0] if _n_link else 0) or 0
                if _cnt > 250:
                    overlap = overlap * (1.0 / _math.log10(_cnt))
            except Exception:
                pass
            abbinamenti.append({
                "ingrediente": nome_pulito,
                "composto": _fascia_affinita(overlap, _lang_out),
                "overlap": overlap,
                "perche": _perche_affinita(overlap, _lang_out)
            })
        # deduplica per nome (possono esserci nodi EN e IT con lo stesso nome)
        # ed esclude l'auto-abbinamento (l'ingrediente cercato con se stesso)
        _cercato = ingrediente.lower().strip()
        seen_nomi = set()
        _fam_count = {}  # limita la ridondanza: non 5 formaggi identici, ma max 2 per categoria
        abbinamenti_dedup = []
        for a in sorted(abbinamenti, key=lambda x: -x["overlap"]):
            n_lower = a["ingrediente"].lower().strip()
            if n_lower in seen_nomi:
                continue
            # salta se è l'ingrediente stesso (self-match)
            if n_lower == _cercato or n_lower == NOMI_IT.get(_cercato, "").lower():
                continue
            # limite di categoria: max 2 abbinamenti della stessa famiglia (evita 5 formaggi uguali)
            _fam = None
            _dairy_kw = ("parmigiano","pecorino","mozzarella","gruyère","gruyere","provolone","grana",
                "caciocavallo","fontina","gorgonzola","ricotta","stracchino","asiago","emmental","cheddar",
                "brie","taleggio","scamorza","camembert","feta","formaggio","caprino","burrata","mascarpone",
                "robiola","edam","gouda","manchego","roquefort","stilton","comté","comte","raclette","latte",
                "panna","burro","yogurt","kefir")
            _agrume_kw = ("limone","lime","arancia","pompelmo","mandarino","bergamotto","cedro","clementina")
            _erba_kw = ("basilico","prezzemolo","rosmarino","timo","salvia","origano","maggiorana","aneto",
                "dragoncello","coriandolo","menta","erba cipollina")
            if any(k in n_lower for k in _dairy_kw): _fam = "latticino"
            elif any(k in n_lower for k in _agrume_kw): _fam = "agrume"
            elif any(k in n_lower for k in _erba_kw): _fam = "erba"
            if _fam:
                if _fam_count.get(_fam, 0) >= 2:
                    continue
                _fam_count[_fam] = _fam_count.get(_fam, 0) + 1
            seen_nomi.add(n_lower)
            abbinamenti_dedup.append(a)
            if len(abbinamenti_dedup) >= 15:
                break
        # ── ABBINAMENTI SORPRENDENTI (puramente ADDITIVI) ──
        # Il flavour network premia lo scontato (i primi per overlap sono i parenti stretti:
        # fragola->mela). Facciamo emergere ANCHE il sorprendente-fondato: overlap medio-alto
        # ma di categoria diversa (fragola->basilico). NON si toglie nulla degli scontati:
        # i classici restano tutti, i sorprendenti si AGGIUNGONO in fondo. Marcati "sorprendente".
        try:
            _CATEGORIE = {
                "frutta": {"mela","pera","fragola","lampone","mirtillo","arancia","limone","lime","banana",
                           "ananas","mango","cocco","pesca","albicocca","prugna","ciliegia","uva","melone",
                           "anguria","fico","kiwi","melograno","pompelmo","guava","mora","ribes"},
                "erba": {"basilico","prezzemolo","rosmarino","timo","menta","salvia","origano","maggiorana",
                         "aneto","dragoncello","coriandolo","alloro","erba cipollina","citronella"},
                "spezia": {"pepe nero","peperoncino","cannella","zenzero","cardamomo","curcuma","zafferano",
                           "chiodo di garofano","noce moscata","anice stellato","liquirizia","paprika"},
                "carne": {"manzo","pollo","maiale","agnello","tacchino","prosciutto","pancetta","guanciale"},
                "pesce": {"salmone","tonno","gambero","merluzzo","acciuga","cozza","ostrica","granchio","polpo"},
                "latticino": {"burro","panna","latte","formaggio","parmigiano","mozzarella","yogurt","ricotta"},
                "ortaggio": {"pomodoro","aglio","cipolla","carota","sedano","fungo","patata","melanzana",
                             "peperone","zucca","zucchine","broccoli","cavolfiore","spinaci","carciofo"},
            }
            def _categoria(nome):
                nl = nome.lower().strip()
                for cat, membri in _CATEGORIE.items():
                    if nl in membri:
                        return cat
                return None
            _cat_cercato = _categoria(ingrediente) or _categoria(NOMI_IT.get(_cercato, ""))
            if _cat_cercato:
                # tra TUTTI gli abbinamenti (non solo i top-15 già tenuti), pesca quelli di
                # categoria diversa con overlap decente (>= 30), non già presenti nella lista.
                _gia = {a["ingrediente"].lower() for a in abbinamenti_dedup}
                _sorprendenti = []
                for a in sorted(abbinamenti, key=lambda x: -x["overlap"]):
                    nl = a["ingrediente"].lower().strip()
                    if nl in _gia or nl == _cercato:
                        continue
                    cat_a = _categoria(a["ingrediente"])
                    if cat_a and cat_a != _cat_cercato and a["overlap"] >= 30:
                        b = dict(a)
                        b["sorprendente"] = True
                        b["perche"] = f"sorprendente: {a['perche']} pur essendo di un'altra famiglia ({cat_a})"
                        _sorprendenti.append(b)
                        _gia.add(nl)
                    if len(_sorprendenti) >= 3:
                        break
                # ADDITIVO: i classici restano TUTTI, i sorprendenti si aggiungono in fondo.
                abbinamenti_dedup = abbinamenti_dedup + _sorprendenti

                # ── SORPRENDENTI CALCOLATI DAI COMPOSTI CONDIVISI ──
                # Se gli archi Ahn non danno sorprendenti cross-categoria (es. fragola non ha
                # arco diretto col basilico), li calcoliamo dai composti condivisi reali
                # (edges contiene_composto). Fondato sul dato molecolare, non inventato.
                # NB: qui la connessione precedente è già chiusa, ne apriamo una nuova.
                if len(_sorprendenti) < 2:
                    _c3 = None
                    try:
                        _c3 = _get_conn(); _cur3 = _c3.cursor()
                        # trova l'id ingrediente di partenza (ahn_ o ing-)
                        _from_id = None
                        if ahn_name:
                            _from_id = f"ahn_{ahn_name.replace(' ', '_')}"
                        else:
                            _cur3.execute("""SELECT id FROM nodes WHERE type='Ingrediente'
                                           AND (lower(name)=lower(%s) OR lower(id)=lower(%s)) LIMIT 1""",
                                        (ing_it, f"ing-{ing_norm.replace('_','-')}"))
                            _rr = _cur3.fetchone()
                            if _rr:
                                _from_id = _rr[0]
                        if _from_id:
                            _cur3.execute("""
                                SELECT e2.from_id, n.name, count(*) as ov
                                FROM edges e1
                                JOIN edges e2 ON e1.to_id = e2.to_id
                                JOIN nodes n ON n.id = e2.from_id
                                WHERE e1.relation='contiene_composto' AND e1.from_id=%s
                                AND e2.relation='contiene_composto' AND e2.from_id != %s
                                AND n.type='Ingrediente'
                                GROUP BY e2.from_id, n.name
                                HAVING count(*) >= 4
                                ORDER BY ov DESC LIMIT 60
                            """, (_from_id, _from_id))
                            _gia2 = {a["ingrediente"].lower() for a in abbinamenti_dedup}
                            _sorp2 = []
                            for _rid, _rname, _ov in _cur3.fetchall():
                                _nm = (_rname or "").strip()
                                _nl = _nm.lower()
                                if not _nm or _nl in _gia2 or _nl == _cercato:
                                    continue
                                cat_r = _categoria(_nm)
                                if cat_r and cat_r != _cat_cercato:
                                    _sorp2.append({
                                        "ingrediente": _nm,
                                        "composto": _fascia_affinita(_ov),
                                        "overlap": float(_ov),
                                        "perche": f"sorprendente: {_perche_affinita(_ov)}, pur essendo di un'altra famiglia ({cat_r})",
                                        "sorprendente": True,
                                    })
                                    _gia2.add(_nl)
                                if len(_sorp2) >= 3:
                                    break
                            abbinamenti_dedup = abbinamenti_dedup + _sorp2
                    except Exception as _ce:
                        print(f"[SORP COMPOSTI] {_ce}", flush=True)
                    finally:
                        if _c3:
                            _release_conn(_c3)
        except Exception:
            pass
        abbinamenti = abbinamenti_dedup
        abbinamenti_puliti = _pulisci_abbinamenti(abbinamenti, ingrediente_base=ingrediente)
        # FALLBACK AI: se dopo la pulizia restano troppo pochi abbinamenti,
        # completa con abbinamenti plausibili generati da AI (marcati come tali).
        fonte = "Dataset Ahn 2011 (CC BY)"
        if len(abbinamenti_puliti) < 3:
            try:
                _prompt_ai = (
                    f"Dammi 5 ingredienti che si abbinano a '{ingrediente}'. "
                    f"SOLO nomi di ingredienti SINGOLI (1-2 parole: es. basilico, limone, mandorla). "
                    f"NON piatti, NON frasi, NON descrizioni, nessuna marca. "
                    f'Rispondi SOLO con JSON: {{"abbinamenti":["basilico","limone","..."]}}'
                )
                _raw = GW.route_free(_prompt_ai, max_tokens=300)
                if _raw:
                    import re as _re, json as _js
                    _m = _re.search(r'\{.*\}', _raw, _re.DOTALL)
                    if _m:
                        _lista_ai = _js.loads(_m.group()).get("abbinamenti", [])
                        def _e_ingrediente_singolo(x):
                            # scarta le frasi-piatto: niente virgole, niente " con ", max 3 parole, max 30 char
                            if not isinstance(x, str): return False
                            x = x.strip()
                            if not x or len(x) > 30: return False
                            if "," in x or " con " in x.lower() or " e " in x.lower(): return False
                            if len(x.split()) > 3: return False
                            return True
                        _nuovi = [{"ingrediente": x.strip(), "composto": "abbinamento suggerito",
                                   "overlap": 60, "perche": "abbinamento plausibile (AI)"}
                                  for x in _lista_ai if _e_ingrediente_singolo(x)]
                        # unisci evitando duplicati coi già presenti
                        _esistenti = {a["ingrediente"].lower() for a in abbinamenti_puliti}
                        for n in _nuovi:
                            if n["ingrediente"].lower() not in _esistenti:
                                abbinamenti_puliti.append(n)
                        abbinamenti_puliti = _pulisci_abbinamenti(abbinamenti_puliti)
                        if _lista_ai:
                            fonte = "Dataset Ahn + completamento AI"
            except Exception:
                pass
        return jsonify({
            "segreto": _seg,
            "ingrediente": ingrediente,
            "abbinamenti": abbinamenti_puliti,
            "nota": "Ipotesi di abbinamento per composti volatili condivisi — non è una garanzia nutrizionale",
            "fonte": fonte,
            "evidence": _evidence,
            "evidence_label": {"A": "Dato molecolare verificato", "B": "Profilo ereditato da ingrediente equivalente",
                               "C": "Suggerimento AI (non verificato molecolarmente)"}.get(_evidence, "")
        })
    except Exception as e:
        return jsonify({
            "segreto": _seg,"ingrediente":ingrediente,"abbinamenti":[],
                        "nota":f"Errore: {str(e)}"}), 500

@bp.route("/v1/menu/proposte", methods=["POST"])
def menu_proposte():
    """FEATURE MENÙ DA FOTO — Step 2: motore delle proposte (grafo-RAG deterministico).
    Riceve {ingredienti:[nomi], tipo:'drink_list'}. Trova le CONNESSIONI REALI nel Flavor
    Network tra gli ingredienti forniti (composti aromatici condivisi), le raggruppa in
    proposte (coppie forti + triangoli), ognuna con un 'proof' verificabile.
    Nessuna allucinazione: le connessioni vengono SOLO dal grafo, non inventate dall'AI.
    Freemium: gratis vede il riconoscimento + le prime 2 proposte; il resto è Pro."""
    body = request.json or {}
    ingredienti = [x.strip() for x in (body.get("ingredienti") or []) if x and x.strip()]
    if len(ingredienti) < 2:
        return jsonify({"errore": "servono almeno 2 ingredienti", "proposte": []}), 400

    # mappo ogni ingrediente: uso l'alias se c'è, altrimenti il nome stesso.
    # (la query cerca per nome italiano su id 'ing-*', non serve l'alias inglese)
    ahn_map = {}  # nome_utente -> alias (o nome stesso)
    for ing in ingredienti:
        a = _alias_ahn(ing)
        ahn_map[ing] = a or ing

    if not DATABASE_URL or len(ahn_map) < 2:
        return jsonify({"ingredienti": ingredienti, "proposte": [],
                        "nota": "Connessioni non disponibili per questi ingredienti."})

    try:
        conn = _get_conn(); cur = conn.cursor()
        # per ogni COPPIA di ingredienti mappati, conto i composti condivisi (forza del legame)
        coppie = []
        items = list(ahn_map.items())
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                n1, a1 = items[i]; n2, a2 = items[j]
                # Come /v1/abbina: parto da n1, prendo TUTTI i suoi archi di abbinamento,
                # e cerco n2 tra i partner. Il grafo ha DUE sistemi di id: 'ahn_*' (inglese,
                # ahn_strawberry) e 'ing-*' (italiano). Cerco n1 in entrambi, e riconosco n2
                # sia col nome italiano che con l'alias inglese (a2, es. tomato). Niente LIMIT.
                def _norm_acc(s):
                    return (s.lower().replace("à","a").replace("è","e").replace("é","e")
                            .replace("ì","i").replace("ò","o").replace("ù","u").strip())
                s1 = _norm_acc(n1); s2 = _norm_acc(n2)
                # alias inglese di n1 e n2 (per il sistema ahn_*)
                a1_en = _norm_acc(a1) if a1 and a1 != n1 else ""
                a2_en = _norm_acc(a2) if a2 and a2 != n2 else ""
                cur.execute("""
                    SELECT nt.name, translate(lower(e.to_id),'àèéìòù','aeeiou') AS toid,
                           (e.data->>'overlap')::numeric AS ov
                    FROM edges e
                    JOIN nodes nf ON nf.id = e.from_id
                    JOIN nodes nt ON nt.id = e.to_id
                    WHERE e.relation='abbinamento_aromatico'
                      AND (translate(lower(e.from_id),'àèéìòù','aeeiou') LIKE %s
                        OR translate(lower(e.from_id),'àèéìòù','aeeiou') LIKE %s
                        OR translate(lower(nf.name),'àèéìòù','aeeiou') LIKE %s)
                """, (f"%{s1.replace(' ','-')}%", f"%{a1_en}%" if a1_en else "%__nomatch__%", f"%{s1}%"))
                forza = 0
                for rname, rtoid, rov in cur.fetchall():
                    partner = _norm_acc(rname or "")
                    toid = rtoid or ""
                    ok = (s2 in partner or s2.replace(" ", "-") in toid
                          or (a2_en and (a2_en in partner or a2_en in toid)))
                    if ok and rov and int(float(rov)) > forza:
                        forza = int(float(rov))
                if forza > 0:
                    coppie.append({"a": n1, "b": n2, "forza": forza})
        cur.close(); _release_conn(conn)

        # ordino le coppie per forza del legame
        coppie.sort(key=lambda x: -x["forza"])

        # FALLBACK: se ci sono poche connessioni forti, aggiungo proposte esplorative
        # (combinazioni degli ingredienti disponibili, con forza dichiarata onestamente)
        nomi = list(ahn_map.keys())
        if len(coppie) < 2 and len(nomi) >= 2:
            esistenti = {frozenset([c["a"],c["b"]]) for c in coppie}
            for i in range(len(nomi)):
                for j in range(i+1, len(nomi)):
                    fs = frozenset([nomi[i], nomi[j]])
                    if fs not in esistenti:
                        coppie.append({"a": nomi[i], "b": nomi[j], "forza": 0, "esplorativa": True})
                        esistenti.add(fs)

        # costruisco le proposte: coppie forti + triangoli (A-B-C tutti connessi)
        proposte = []
        # 1) triangoli: tre ingredienti tutti connessi tra loro
        conn_set = {(c["a"], c["b"]) for c in coppie} | {(c["b"], c["a"]) for c in coppie}
        usati_tri = set()
        nomi = list(ahn_map.keys())
        for i in range(len(nomi)):
            for j in range(i+1, len(nomi)):
                for k in range(j+1, len(nomi)):
                    a, b, c = nomi[i], nomi[j], nomi[k]
                    if (a,b) in conn_set and (b,c) in conn_set and (a,c) in conn_set:
                        conns = sum(1 for c2 in coppie if set([c2["a"],c2["b"]]) <= set([a,b,c]))
                        proposte.append({
                            "tipo": "triangolo", "ingredienti": [a,b,c],
                            "nome": f"{a.capitalize()}, {b} e {c}",
                            "connessioni": conns,
                            "proof": {"ingredienti_disponibili": 3, "connessioni_aromatiche": conns}
                        })
                        usati_tri |= {a,b,c}
        # 2) coppie non già coperte da un triangolo
        for c in coppie[:6]:
            if not ({c["a"],c["b"]} <= usati_tri):
                esplorativa = c.get("esplorativa") or c["forza"]==0
                proposte.append({
                    "tipo": "coppia", "ingredienti": [c["a"], c["b"]],
                    "nome": f'{c["a"].capitalize()} e {c["b"]}',
                    "connessioni": c["forza"],
                    "esplorativa": esplorativa,
                    "proof": {"ingredienti_disponibili": 2,
                              "connessioni_aromatiche": c["forza"],
                              "nota": "da esplorare al banco" if esplorativa else "legame verificato"}
                })
        # ordino: triangoli prima, poi legami forti, poi esplorative
        proposte.sort(key=lambda p: (0 if p["tipo"]=="triangolo" else 1, 1 if p.get("esplorativa") else 0, -p["connessioni"]))

        # SPRINT 2 — etichetta di robustezza leggibile per ogni proposta (punto revisori)
        for pr in proposte:
            c = pr.get("connessioni", 0)
            if pr.get("esplorativa") or c == 0:
                pr["robustezza"] = "da esplorare"
            elif c >= 3:
                pr["robustezza"] = "forte"
            else:
                pr["robustezza"] = "media"

        return jsonify({
            "ingredienti": ingredienti,
            "ingredienti_mappati": list(ahn_map.keys()),
            "proposte": proposte[:8],
            "totale": len(proposte),
            "fonte": "Dataset Ahn 2011 (CC BY) — connessioni per composti aromatici condivisi"
        })
    except Exception as e:
        import traceback
        print(f"[PROPOSTE ERRORE] {e}\n{traceback.format_exc()[-500:]}", flush=True)
        # SPRINT 2 — mai 500 all'utente: fallback che permette di continuare a costruire il menu a mano
        return jsonify({
            "ingredienti": ingredienti,
            "proposte": [],
            "stato": "errore_recuperabile",
            "messaggio": "Non sono riuscito a calcolare gli abbinamenti in questo momento. "
                         "Puoi comporre le voci del menu a mano e continuare.",
            "puoi_inserire_a_mano": True}), 200


@bp.route("/v1/menu/naming", methods=["POST"])
def menu_naming():
    """FEATURE MENÙ — nome suggerito per una voce (l'AI nomina, non inventa la scienza).
    Riceve {ingredienti:[...], disciplina, tecnica?}. Restituisce un nome breve e
    suggestivo. L'utente resta padrone: è solo una proposta pre-compilata."""
    from flask import request as _rq, jsonify as _js
    _ip = _rq.headers.get("X-Forwarded-For", _rq.remote_addr or "?").split(",")[0].strip()
    if not _check_rate_limit(_ip):
        return _js({"errore": "Troppe richieste. Attendi un momento."}), 429
    body = request.json or {}
    ingredienti = body.get("ingredienti", [])
    disciplina = (body.get("disciplina") or "").strip()
    tecnica = (body.get("tecnica") or "").strip()
    if not ingredienti:
        return jsonify({"nome": ""})
    ing_str = ", ".join(str(i) for i in ingredienti[:6])
    tipo = {"bar":"cocktail/drink", "bakery":"lievitato/pizza", "cucina":"piatto"}.get(disciplina, "piatto o drink")
    tec_str = f" La tecnica usata è: {tecnica}." if tecnica else ""
    prompt = (
        f"Sei un menu writer di alto livello per locali F&B. "
        f"Inventa UN nome breve, evocativo e originale (2-4 parole) per una voce di menù ({tipo}) "
        f"a base di: {ing_str}.{tec_str} "
        f"REGOLA FONDAMENTALE: NON elencare gli ingredienti. Crea un nome vero, come su una carta reale. "
        f"Esempi dello stile giusto: ingredienti fragola/basilico/limone → 'Rosso Giardino' o 'Basil Smash'; "
        f"polpo/limone/prezzemolo → 'Mediterraneo' o 'Scoglio'; gin/pompelmo → 'Pompelmo Bruciato'. "
        f"Esempi SBAGLIATI (mai così): 'Fragola, Basilico e Limone', 'Polpo con Limone'. "
        f"Rispondi SOLO col nome inventato, senza virgolette né punteggiatura finale."
    )
    try:
        import ai_gateway as GW
        nome = GW.route_fast(prompt, max_tokens=24, temperature=0.9)
        # pulizia: prima riga, senza virgolette, max ~50 char
        nome = (nome or "").strip().split("\n")[0].strip().strip('"').strip("'")[:50]
        return jsonify({"nome": nome, "ingredienti": ingredienti})
    except Exception as e:
        print(f"[NAMING ERRORE] {e}", flush=True)
        return jsonify({"nome": "", "errore": str(e)})


@bp.route("/v1/menu/tecniche", methods=["POST"])
def menu_tecniche():
    """FEATURE MENÙ — tecniche pertinenti per una voce di menù.
    Riceve {disciplina:'cucina'|'bar'|..., ingredienti:[...]}. Restituisce le tecniche
    del database (nodi Tecnica) pertinenti alla disciplina, coi loro numeri-bersaglio.
    Serve nel laboratorio: 'cosa posso farci' con i target verificabili col Mirino."""
    import json as _j
    from db import carica_grafo
    body = request.json or {}
    disc = (body.get("disciplina") or "").strip()
    lang = body.get("lang","it")
    db = carica_grafo()
    try:
        rows = db.execute("SELECT id, name, data FROM nodes WHERE type='Tecnica' ORDER BY name").fetchall()
        tecniche = []
        for row in rows:
            r = dict(row) if hasattr(row,"keys") else {"id":row[0],"name":row[1],"data":row[2]}
            data = r.get("data") or {}
            if isinstance(data,str):
                try: data = _j.loads(data)
                except: data = {}
            # filtro per disciplina (trasversale sempre incluso)
            if disc and data.get("disciplina") not in (disc, "trasversale"):
                continue
            numeri = data.get("numeri","")
            if not numeri: continue  # solo tecniche con numeri-bersaglio
            tecniche.append({
                "id": r.get("id",""),
                "nome": r.get("name",""),
                "famiglia": data.get("famiglia",""),
                "numeri": numeri,
                "esecuzione": (data.get("esecuzione","") or "")[:200],
            })
        return jsonify({"disciplina": disc, "tecniche": tecniche, "totale": len(tecniche)})
    except Exception as e:
        import traceback
        print(f"[TECNICHE ERRORE] {e}\n{traceback.format_exc()[-400:]}", flush=True)
        return jsonify({"errore": str(e), "tecniche": []}), 500


@bp.route("/v1/profilo-sensoriale", methods=["GET"])
def get_profilo_sensoriale():
    """DEPRECATO. La feature Sommelier (like/dislike + profilo gusto) è stata rimossa perché parte da
    un'opinione, non da una misura (rompe 'Numeri. Non opinioni.'). La sostituirà il Laboratorio Sensoriale.
    Vedi LABORATORIO-SENSORIALE-DECISIONE.md."""
    return jsonify({"rimossa": True, "sostituita_da": "Laboratorio Sensoriale",
                    "nota": "Feature sommelier deprecata."}), 410

@bp.route("/v1/feedback-abbinamento", methods=["POST"])
def feedback_abbinamento():
    """DEPRECATO. Il like/dislike sugli abbinamenti è stato rimosso: è raccolta dati che parte da
    un'opinione, non da una misura (rompe 'Numeri. Non opinioni.'). Lo sostituirà il Laboratorio
    Sensoriale (osservazioni percettive, non voti). Vedi LABORATORIO-SENSORIALE-DECISIONE.md."""
    return jsonify({"rimossa": True, "sostituita_da": "Laboratorio Sensoriale",
                    "nota": "Il like/dislike sugli abbinamenti è stato rimosso."}), 410

@bp.route("/v1/contrasto/<ingrediente>")
def contrasto(ingrediente):
    """FL5 — Abbinamento per contrasto fisico-percettivo.
    Logica: acido taglia il grasso · dolce smorza l'amaro · sale sopprime l'amaro
            grasso porta e ammorbidisce l'acido.
    Usa i dati di grassi_pct, zuccheri_pct, sodio_mg100g, ph_min dal grafo.
    Sempre marcato come euristico — è fisica percettiva, non legge."""
    if not DATABASE_URL:
        return jsonify({"ingrediente": ingrediente, "contrasti": [],
                        "nota": "database non disponibile"})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # trova il nodo dell'ingrediente cercato — preferisce nodi con dati contrasto
        # Cerca in Prodotto E Ingrediente
        cur.execute("""
            SELECT id, name, data FROM nodes
            WHERE type IN ('Prodotto','Ingrediente')
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            ORDER BY CASE WHEN (data->>'profilo_contrasto') IS NOT NULL THEN 0 ELSE 1 END,
                     length(name) ASC
            LIMIT 1
        """, (f"%{ingrediente}%", f"%ing-{ingrediente.lower().replace(' ','-')}%"))
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"ingrediente": ingrediente, "contrasti": [],
                            "nota": "Ingrediente non trovato nel grafo con dati di contrasto."})

        node_id, node_name, data_raw = row
        import json as _json
        d = data_raw if isinstance(data_raw, dict) else _json.loads(data_raw)

        grassi = float(d.get("grassi_pct", 0) or 0)
        zuccheri = float(d.get("zuccheri_pct", 0) or 0)
        ph = float(d.get("ph_min", 7) or 7)
        amaro = float(d.get("amaro_index", 0) or 0)
        sodio = float(d.get("sodio_mg100g", 0) or 0)
        profilo = d.get("profilo_contrasto", "")

        # determina il tipo di contrasto necessario
        regole = []
        if ph < 4.5:
            regole.append(("acido", "taglia_grasso",
                           "L'acido taglia il grasso: il pH basso emulsiona e pulisce la bocca"))
        if grassi > 10:
            regole.append(("grasso", "richiede_acido",
                           "Il grasso porta e ammorbidisce: cerca un acido per bilanciare"))
        if amaro >= 3:
            regole.append(("amaro", "smorzato_da_dolce",
                           "Il dolce smorza l'amaro: zuccheri e grassi riducono la percezione amara"))
        if amaro >= 2:
            regole.append(("amaro", "smorzato_da_sale",
                           "Il sale sopprime l'amaro: piccole quantità di sodio riducono l'amaro percepito"))
        if zuccheri > 15:
            regole.append(("dolce", "bilanciato_da_acido",
                           "Il dolce vuole acido: senza contrasto acido il dolce stanca e satura"))
        if sodio > 200:
            regole.append(("salato", "amplificato_da_acido",
                           "Il salato si amplifica con l'acido: together esaltano entrambi i sapori"))

        if not regole:
            cur.close(); _release_conn(conn)
            return jsonify({
                "ingrediente": node_name, "contrasti": [],
                "nota": "Profilo neutro — questo ingrediente non ha un contrasto dominante evidente.",
                "tipo": "contrasto"
            })

        # cerca ingredienti con il profilo opposto
        contrasti = []
        visti = set()
        for profilo_cercato, meccanismo, spiegazione in regole:
            if profilo_cercato == "acido":
                # cerca grassi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'grassi_pct')::numeric > 8
                    AND id != %s
                    ORDER BY (data->>'grassi_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "grasso":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'ph_min')::numeric < 4.5
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_dolce":
                # cerca dolci
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'zuccheri_pct')::numeric > 10
                    AND id != %s
                    ORDER BY (data->>'zuccheri_pct')::numeric DESC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "amaro" and meccanismo == "smorzato_da_sale":
                # cerca salati
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'sodio_mg100g')::numeric > 100
                    AND id != %s
                    ORDER BY (data->>'sodio_mg100g')::numeric DESC LIMIT 2
                """, (node_id,))
            elif profilo_cercato == "dolce":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'ph_min')::numeric < 4.0
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 3
                """, (node_id,))
            elif profilo_cercato == "salato":
                # cerca acidi
                cur.execute("""
                    SELECT id, name, data FROM nodes
                    WHERE type IN ('Prodotto','Ingrediente')
                    AND (data->>'ph_min')::numeric < 4.5
                    AND id != %s
                    ORDER BY (data->>'ph_min')::numeric ASC LIMIT 2
                """, (node_id,))
            else:
                continue

            for r in cur.fetchall():
                rid, rname, rdata = r
                if rid not in visti:
                    visti.add(rid)
                    import json as _j2
                    rd = rdata if isinstance(rdata, dict) else _j2.loads(rdata or "{}")
                    # spiegazione: template BREVE e completo (non si tronca).
                    # Il meccanismo è chiaro, senza numeri grezzi ballerini in mezzo alla frase.
                    if meccanismo == "taglia_grasso":
                        perche = f"L'acidità di {node_name} taglia il grasso e pulisce la bocca."
                    elif meccanismo == "richiede_acido":
                        perche = f"Il grasso di {node_name} chiede acidità: {rname} bilancia."
                    elif meccanismo == "smorzato_da_dolce":
                        perche = f"Il dolce di {rname} smorza l'amaro di {node_name}."
                    elif meccanismo == "smorzato_da_sale":
                        perche = f"Il sale di {rname} sopprime l'amaro di {node_name}."
                    elif meccanismo == "bilanciato_da_acido":
                        perche = f"L'acidità di {rname} taglia il dolce di {node_name} e rinfresca."
                    elif meccanismo == "amplificato_da_acido":
                        perche = f"L'acido di {rname} esalta il salato di {node_name}."
                    else:
                        perche = spiegazione
                    contrasti.append({
                        "ingrediente": rname,
                        "meccanismo": meccanismo,
                        "perche": perche
                    })

        cur.close(); _release_conn(conn)
        return jsonify({
            "ingrediente": node_name,
            "contrasti": contrasti[:6],
            "nota": "Abbinamento per contrasto fisico-percettivo — euristico, non legge",
            "tipo": "contrasto"
        })
    except Exception as e:
        return jsonify({"ingrediente": ingrediente, "contrasti": [],
                        "nota": f"Errore: {str(e)}"}), 500

@bp.route("/prezzi_mercato/<ingrediente>")
@bp.route("/prezzi_mercato/<ingrediente>/<area>")
def prezzi_mercato(ingrediente, area="it"):
    """PR1 — Prezzi di mercato orientativi per area geografica.
    Fonte attuale: dati medi ISMEA incorporati nel grafo (campo prezzo_mercato).
    Futuro: aggiornamento automatico via API ISMEA/Eurostat/USDA."""
    db = carica_grafo()
    # cerca il nodo prodotto per nome
    nodi = db.execute(
        "SELECT id, name, data FROM nodes WHERE lower(name) LIKE lower(?) AND type='Prodotto' LIMIT 5",
        (f"%{ingrediente}%",)
    ).fetchall()
    risultati = []
    for n in nodi:
        d = _dati(n["data"])
        prezzo = d.get(f"prezzo_mercato_{area}") or d.get("prezzo_mercato_it")
        if prezzo:
            risultati.append({
                "ingrediente": n["name"],
                "id": n["id"],
                "prezzo": prezzo,
                "area": area,
                "fonte": "ISMEA/orientativo",
                "nota": "Prezzo medio di mercato orientativo — non vincolante"
            })
    if not risultati:
        return jsonify({
            "ingrediente": ingrediente,
            "area": area,
            "prezzo": None,
            "nota": "Prezzo non disponibile — usa i prezzi del tuo fornitore in Cifra"
        })
    return jsonify({"risultati": risultati, "totale": len(risultati)})


@bp.route("/v1/foto-analisi", methods=["POST"])
def foto_analisi():
    """Pipeline foto → analisi scientifica.
    Riceve immagine multipart (campo 'immagine') o JSON con base64 (campo 'immagine_b64').
    Restituisce ingredienti riconosciuti, abbinamenti aromatici, fenomeni fisici, output AI.
    Gate: FOTO SOLO PRO (feature riservata agli abbonati, costa OpenAI Vision)."""
    from flask import request as _rq, jsonify as _js
    _ip = _rq.headers.get("X-Forwarded-For", _rq.remote_addr or "?").split(",")[0].strip()
    if not _check_rate_limit(_ip):
        return _js({"errore": "Troppe richieste. Attendi un momento."}), 429
    if not _check_rate_limit_ai(_chiave_rate()):
        return _js({"errore":"rate_limit","messaggio":"Troppe analisi foto. Attendi un minuto."}), 429
    from utils import _e_pro
    _tok = (request.form.get("token") or request.args.get("token") or request.headers.get("X-Token","") or "")
    _uid = _utente_da_token(_tok) if _tok else None
    if not _e_pro(_uid):
        return jsonify({"errore": "solo_pro", "solo_pro": True,
            "messaggio": "L'analisi foto è una funzione Pro. Abbonati per usarla."}), 402
    lang = request.args.get("lang", request.json.get("lang", "it") if request.is_json else "it")

    # lettura immagine — multipart o base64
    img_bytes = None
    media_type = "image/jpeg"
    if "immagine" in request.files:
        f = request.files["immagine"]
        img_bytes = f.read()
        media_type = f.content_type or "image/jpeg"
    elif request.is_json and request.json.get("immagine_b64"):
        import base64
        raw_b64 = request.json["immagine_b64"]
        # gestisce sia il raw base64 sia il data-url
        if "," in raw_b64:
            header, raw_b64 = raw_b64.split(",", 1)
            media_type = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
        img_bytes = base64.b64decode(raw_b64)
    if not img_bytes:
        return jsonify({"errore": "immagine mancante — invia 'immagine' (multipart) o 'immagine_b64' (base64)"}), 400

    try:
        from foto import analizza_foto
        risultato = analizza_foto(img_bytes, media_type=media_type, lang=lang)
        return jsonify(risultato)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[FOTO ERRORE] {e}\n{tb}", flush=True)
        return jsonify({"errore": str(e), "trace": tb[-600:]}), 500


# ── 14 allergeni obbligatori UE (Reg. 1169/2011) — mappa tag OFF → nome IT ──
_ALLERGENI_UE = {
    "gluten":"Glutine", "crustaceans":"Crostacei", "eggs":"Uova", "fish":"Pesce",
    "peanuts":"Arachidi", "soybeans":"Soia", "milk":"Latte", "nuts":"Frutta a guscio",
    "celery":"Sedano", "mustard":"Senape", "sesame-seeds":"Sesamo", "sulphur-dioxide-and-sulphites":"Solfiti",
    "lupin":"Lupini", "molluscs":"Molluschi",
}

def _mappa_allergeni_off(tags):
    """Converte i tag allergeni di Open Food Facts (es. 'en:milk') nei 14 nomi UE in italiano.
    Deterministico: nessuna AI. Ritorna lista ordinata di nomi IT riconosciuti."""
    out = []
    for t in (tags or []):
        chiave = t.split(":")[-1].strip().lower() if ":" in t else t.strip().lower()
        nome = _ALLERGENI_UE.get(chiave)
        if nome and nome not in out:
            out.append(nome)
    return out

@bp.route("/v1/menu/barcode/<codice>", methods=["GET"])
def barcode_lookup(codice):
    """Scan codice a barre → prodotto confezionato via Open Food Facts.
    Deterministico e GRATIS (nessuna AI, nessuna chiave): riconosce prodotti di dispensa
    senza chiamata Vision. Restituisce nome, ingredienti, allergeni UE.
    Fonte: Open Food Facts (ODbL, uso commerciale consentito con attribuzione)."""
    import urllib.request, urllib.error
    codice = "".join(ch for ch in (codice or "") if ch.isdigit())
    if not (8 <= len(codice) <= 14):
        return jsonify({"errore": "codice a barre non valido"}), 400
    # solo i campi che servono (riduce il payload, come raccomanda OFF)
    campi = "product_name,product_name_it,brands,ingredients_text,ingredients_text_it,allergens_tags,image_front_small_url"
    url = f"https://world.openfoodfacts.org/api/v2/product/{codice}?fields={campi}"
    req = urllib.request.Request(url, headers={"User-Agent": "MatterLab/1.0 (matterlab.app) - contact via app"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return jsonify({"trovato": False, "codice": codice,
                            "messaggio": "Prodotto non in Open Food Facts. Inseriscilo a mano."}), 200
        return jsonify({"errore": f"Open Food Facts non raggiungibile ({e.code})"}), 502
    except Exception:
        return jsonify({"errore": "Open Food Facts non raggiungibile. Riprova o inserisci a mano."}), 502

    # status 0 = codice valido ma prodotto assente (OFF risponde 200 anche in questo caso)
    if not data or data.get("status") == 0 or not data.get("product"):
        return jsonify({"trovato": False, "codice": codice,
                        "messaggio": "Prodotto non trovato. Inseriscilo a mano."}), 200

    p = data["product"]
    nome = (p.get("product_name_it") or p.get("product_name") or "").strip()
    marca = (p.get("brands") or "").split(",")[0].strip()
    ingredienti_txt = (p.get("ingredients_text_it") or p.get("ingredients_text") or "").strip()
    allergeni = _mappa_allergeni_off(p.get("allergens_tags"))
    return jsonify({
        "trovato": True,
        "codice": codice,
        "nome": nome or (marca or "Prodotto senza nome"),
        "marca": marca,
        "ingredienti_testo": ingredienti_txt,
        "allergeni": allergeni,
        "immagine": p.get("image_front_small_url", ""),
        "fonte": "Open Food Facts",
        # onestà: il dato è crowdsourced, non una fonte normativa
        "avviso": "Dati da Open Food Facts. Verifica sempre la composizione effettiva.",
    })


@bp.route("/v1/menu/riconosci-ingredienti", methods=["POST"])
def riconosci_ingredienti():
    """FEATURE MENÙ DA FOTO — Step 1: riconoscimento ingredienti.
    Riceve una o più immagini (multipart 'immagini' multiple, o JSON con 'immagini_b64' lista).
    Usa Vision in JSON Mode con schema rigido. Restituisce lista ingredienti da validare.
    Freemium: il RICONOSCIMENTO è gratis (effetto WOW). La generazione del menù sarà Pro.
    Costo contenuto: 1 chiamata Vision per foto (max 6)."""
    from flask import request as _rq, jsonify as _js
    _ip = _rq.headers.get("X-Forwarded-For", _rq.remote_addr or "?").split(",")[0].strip()
    if not _check_rate_limit(_ip):
        return _js({"errore": "Troppe richieste. Attendi un momento."}), 429
    import base64, json as _json
    # raccolgo le immagini (max 6)
    imgs = []  # lista di (bytes, media_type)
    if request.files:
        for key in request.files:
            for f in request.files.getlist(key):
                imgs.append((f.read(), f.content_type or "image/jpeg"))
    elif request.is_json and request.json.get("immagini_b64"):
        for raw in request.json["immagini_b64"][:6]:
            mt = "image/jpeg"
            if "," in raw:
                header, raw = raw.split(",", 1)
                mt = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
            imgs.append((base64.b64decode(raw), mt))
    imgs = imgs[:6]
    if not imgs:
        return jsonify({"errore": "nessuna immagine — invia 'immagini' (multipart) o 'immagini_b64' (lista base64)"}), 400

    # prompt JSON Mode rigido: solo materie prime alimentari, no stoviglie/sfondo
    prompt = (
        "Sei un assistente per chef e bartender. Analizza l'immagine e identifica SOLO gli "
        "ingredienti alimentari e le materie prime commestibili (frutta, verdura, carne, pesce, "
        "erbe, spezie, distillati, vini, latticini, farine). IGNORA stoviglie, contenitori, "
        "cassette, sfondi, mani, utensili. Rispondi ESCLUSIVAMENTE con un oggetto JSON valido, "
        "senza testo prima o dopo, in questo schema:\n"
        '{"ingredienti":[{"nome":"<nome italiano>","categoria":"<proteine|vegetali|frutta|erbe|spezie|distillati|vini|latticini|farine|altro>","confidenza":<0-1>}]}'
        "\nSe non riconosci nulla di commestibile, restituisci {\"ingredienti\":[]}."
    )
    tutti = {}  # dedup per nome
    try:
        from ai_gateway import route_vision
        for img_bytes, mt in imgs:
            out = route_vision(img_bytes, prompt, media_type=mt)
            # estraggo il JSON dalla risposta (robusto a eventuali backtick)
            txt = (out or "").strip()
            if txt.startswith("```"):
                txt = txt.strip("`")
                if txt.startswith("json"): txt = txt[4:]
            i0, i1 = txt.find("{"), txt.rfind("}")
            if i0 >= 0 and i1 > i0:
                try:
                    parsed = _json.loads(txt[i0:i1+1])
                    for ing in parsed.get("ingredienti", []):
                        nome = (ing.get("nome") or "").strip()
                        if not nome: continue
                        key = nome.lower()
                        if key not in tutti or (ing.get("confidenza",0) > tutti[key].get("confidenza",0)):
                            tutti[key] = {"nome": nome,
                                          "categoria": ing.get("categoria","altro"),
                                          "confidenza": round(float(ing.get("confidenza",0.8)),2)}
                except Exception:
                    pass
        lista = sorted(tutti.values(), key=lambda x: -x["confidenza"])
        # SPRINT 2 — robustezza: separo per confidenza e do sempre una guida, mai un vicolo cieco.
        sicuri = [x for x in lista if x["confidenza"] >= 0.6]
        da_confermare = [x for x in lista if x["confidenza"] < 0.6]
        if not lista:
            # nessun ingrediente: foto probabilmente brutta. NON è un errore: guido l'utente.
            return jsonify({
                "ingredienti": [], "totale": 0, "foto_analizzate": len(imgs),
                "stato": "nessun_riconoscimento",
                "messaggio": "Non sono riuscito a riconoscere ingredienti. La foto potrebbe essere "
                             "poco nitida o buia. Puoi riprovare con più luce, oppure aggiungere gli "
                             "ingredienti a mano qui sotto.",
                "puoi_inserire_a_mano": True})
        return jsonify({
            "ingredienti": lista, "totale": len(lista), "foto_analizzate": len(imgs),
            "stato": "ok",
            "sicuri": sicuri,
            "da_confermare": da_confermare,  # il frontend li mostra come chip "È corretto?"
            "messaggio": (f"Ho riconosciuto {len(sicuri)} ingredienti." +
                          (f" Altri {len(da_confermare)} sono incerti: confermali o correggili."
                           if da_confermare else "")),
            "puoi_inserire_a_mano": True})
    except Exception as e:
        import traceback
        print(f"[RICONOSCI ERRORE] {e}\n{traceback.format_exc()[-500:]}", flush=True)
        # SPRINT 2 — mai errore 500 all'utente: fallback pulito che permette di continuare a mano.
        return jsonify({
            "ingredienti": [], "totale": 0, "foto_analizzate": len(imgs),
            "stato": "errore_recuperabile",
            "messaggio": "Non sono riuscito ad analizzare la foto in questo momento. Puoi "
                         "aggiungere gli ingredienti a mano qui sotto e continuare.",
            "puoi_inserire_a_mano": True}), 200


@bp.route("/v1/tts", methods=["POST"])
def tts():
    """Text-to-speech per l'output della feature foto.
    Riceve {testo, lang?, voce?} e restituisce audio MP3.
    Solo per l'output foto (non per tutta la chat) per contenere i costi."""
    from flask import Response
    body = request.json or {}
    testo = (body.get("testo") or "").strip()
    if not testo:
        return jsonify({"errore": "testo mancante"}), 400
    # gate: VOCE SOLO PRO (output della foto, stessa feature)
    from utils import _e_pro
    _tok = (body.get("token") or request.headers.get("X-Token","") or "")
    _uid = _utente_da_token(_tok) if _tok else None
    if not _e_pro(_uid):
        return jsonify({"errore": "solo_pro", "solo_pro": True,
            "messaggio": "L'audio è una funzione Pro. Abbonati per usarlo."}), 402
    voce = body.get("voce", "onyx")  # onyx=maschile caldo, nova=femminile
    lang = body.get("lang", "it")
    try:
        import ai_gateway as GW
        audio = GW.tts_openai(testo, voce=voce, lang=lang)
        if not audio:
            return jsonify({"errore": "audio non generato"}), 500
        return Response(audio, mimetype="audio/mpeg",
                        headers={"Content-Disposition": "inline; filename=matter.mp3"})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/crea-colonna-profilo")
def admin_crea_colonna_profilo():
    """Crea la colonna profilo_sensoriale UNA VOLTA (non ad ogni richiesta).
    Uso: /admin/crea-colonna-profilo?s=SECRET"""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"ok": True, "nota": "no db"})
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("ALTER TABLE utenti ADD COLUMN IF NOT EXISTS profilo_sensoriale JSONB DEFAULT '{}'::jsonb")
        conn.commit()
        cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "messaggio": "colonna profilo_sensoriale creata/verificata"})
    except Exception as e:
        try:
            conn.rollback(); _release_conn(conn)
        except Exception:
            pass
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/diag-profilo")
def admin_diag_profilo():
    """Diagnostica: cattura l'errore esatto dell'endpoint profilo. /admin/diag-profilo?s=SECRET"""
    import os as _os, traceback as _tb
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    out = {}
    # test 1: _utente_da_token con token vuoto
    try:
        out["utente_da_token_vuoto"] = repr(_utente_da_token(""))
    except Exception as e:
        out["utente_da_token_vuoto"] = "CRASH: " + repr(e) + "\n" + _tb.format_exc()[-400:]
    # test 2: _profilo_default
    try:
        out["profilo_default"] = "ok" if _profilo_default() else "vuoto"
    except Exception as e:
        out["profilo_default"] = "CRASH: " + repr(e)
    # test 3: query sulla colonna
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT profilo_sensoriale FROM utenti LIMIT 1")
        cur.fetchone(); cur.close(); _release_conn(conn)
        out["query_colonna"] = "ok"
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        out["query_colonna"] = "CRASH: " + repr(e)[:200]
    return jsonify(out)


# ══════════════════════════════════════════════════════════════════
# FUNNEL / KPI — tracking eventi di conversione + dashboard read-only
# Base per il pannello di controllo. Registra da subito così al lancio c'è storico.
# ══════════════════════════════════════════════════════════════════

@bp.route("/v1/funnel/track", methods=["POST"])
def funnel_track():
    """Riceve un evento del funnel dal frontend e lo registra.
    Body JSON: {evento, user_id?, email?, meta?, utm?{source,medium,campaign,content}}
    Eventi canonici: signup, activation, paywall_hit, checkout, paid, churn.
    Pubblico ma rate-limited: il frontend lo chiama nei momenti chiave del funnel."""
    from flask import request as _rq, jsonify as _js
    from ai import log_funnel
    _ip = _rq.headers.get("X-Forwarded-For", _rq.remote_addr or "?").split(",")[0].strip()
    if not _check_rate_limit(_ip):
        return _js({"ok": False, "errore": "rate_limit"}), 429
    d = request.get_json(silent=True) or {}
    evento = (d.get("evento") or "").strip()
    CANONICI = {"signup", "activation", "paywall_hit", "checkout", "paid", "churn",
                "landing_view", "trial_start", "photo_menu", "mirino_use"}
    if evento not in CANONICI:
        return jsonify({"ok": False, "errore": "evento_non_valido"}), 400
    fid = log_funnel(
        evento,
        user_id=d.get("user_id"),
        email=d.get("email"),
        meta=d.get("meta"),
        utm=d.get("utm"),
    )
    return jsonify({"ok": True, "id": fid})


@bp.route("/admin/kpi")
def admin_kpi():
    """Dashboard KPI read-only (base del pannello). /admin/kpi?s=SECRET&giorni=30
    Restituisce conteggi per evento, conversioni tra stadi, e content→paid via UTM.
    NON scrive nulla: sola lettura. Il pannello front-end consumerà questo JSON."""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"ok": True, "nota": "no db"})
    try:
        giorni = int(request.args.get("giorni", 30))
    except Exception:
        giorni = 30
    giorni = max(1, min(giorni, 365))
    try:
        conn = _get_conn(); cur = conn.cursor()
        # la tabella potrebbe non esistere ancora (nessun evento registrato)
        cur.execute("SELECT to_regclass('funnel_eventi')")
        if not cur.fetchone()[0]:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "vuoto": True, "nota": "nessun evento ancora registrato"})
        # 1. conteggio per evento nel periodo
        cur.execute("""
            SELECT evento, COUNT(*) FROM funnel_eventi
            WHERE ts > NOW() - (%s || ' days')::interval
            GROUP BY evento
        """, (giorni,))
        per_evento = {r[0]: r[1] for r in cur.fetchall()}
        # 2. utenti unici per stadio (conversione del funnel)
        cur.execute("""
            SELECT evento, COUNT(DISTINCT COALESCE(user_id, email)) FROM funnel_eventi
            WHERE ts > NOW() - (%s || ' days')::interval AND (user_id IS NOT NULL OR email IS NOT NULL)
            GROUP BY evento
        """, (giorni,))
        unici = {r[0]: r[1] for r in cur.fetchall()}
        # 3. content→paid: paganti per campagna/contenuto UTM
        cur.execute("""
            SELECT COALESCE(utm_campaign,'(nessuna)'), COALESCE(utm_content,'(nessuno)'), COUNT(*)
            FROM funnel_eventi
            WHERE evento='paid' AND ts > NOW() - (%s || ' days')::interval
            GROUP BY utm_campaign, utm_content ORDER BY COUNT(*) DESC LIMIT 20
        """, (giorni,))
        content_paid = [{"campagna": r[0], "contenuto": r[1], "paganti": r[2]} for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
        # conversioni chiave (guardrail: evita divisione per zero)
        def _pct(a, b): return round(100.0 * a / b, 1) if b else None
        sign = unici.get("signup", 0)
        act = unici.get("activation", 0)
        pw = unici.get("paywall_hit", 0)
        paid = unici.get("paid", 0)
        conversioni = {
            "signup_to_activation_pct": _pct(act, sign),
            "activation_to_paywall_pct": _pct(pw, act),
            "paywall_to_paid_pct": _pct(paid, pw),
            "signup_to_paid_pct": _pct(paid, sign),
        }
        return jsonify({
            "ok": True,
            "periodo_giorni": giorni,
            "eventi_totali": per_evento,
            "utenti_unici_per_stadio": unici,
            "conversioni": conversioni,
            "content_to_paid": content_paid,
        })
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


# ══════════════════════════════════════════════════════════════════
# GRAPH COVERAGE SCORE — diagnostica del grafo (profondità + ampiezza)
# Read-only. Misura quanto è coperta ogni disciplina: base decisionale
# per sapere DOVE il grafo è debole, sia in profondità che in ampiezza.
# ══════════════════════════════════════════════════════════════════

@bp.route("/admin/coverage")
def admin_coverage():
    """Graph Coverage Score. /admin/coverage?s=SECRET
    Analizza il grafo reale (nodes+edges) e restituisce, per disciplina:
    fenomeni, prodotti, tecniche, errori, densità di connessioni, e i buchi
    (fenomeni senza prodotti collegati, prodotti orfani, target mancanti).
    Non scrive nulla."""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    if not DATABASE_URL:
        return jsonify({"ok": True, "nota": "no db"})
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT to_regclass('nodes')")
        if not cur.fetchone()[0]:
            cur.close(); _release_conn(conn)
            return jsonify({"ok": True, "vuoto": True, "nota": "grafo non presente"})

        # 1. conteggio nodi per tipo
        cur.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
        nodi_per_tipo = {r[0]: r[1] for r in cur.fetchall()}

        # 2. nodi per dominio × tipo (la mappa disciplina × copertura)
        cur.execute("SELECT COALESCE(domain,'(nessuno)'), type, COUNT(*) FROM nodes GROUP BY domain, type")
        per_dominio = {}
        for dom, tp, n in cur.fetchall():
            per_dominio.setdefault(dom, {})[tp] = n

        # 3. archi per relazione
        cur.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation ORDER BY COUNT(*) DESC")
        archi_per_relazione = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT COUNT(*) FROM edges")
        archi_totali = cur.fetchone()[0]

        # 4. densità: archi / nodi (quanto è connesso il grafo)
        n_nodi = sum(nodi_per_tipo.values())
        densita = round(archi_totali / n_nodi, 2) if n_nodi else 0

        # 5. BUCHI — fenomeni senza prodotti collegati (si_manifesta_in)
        cur.execute("""
            SELECT n.id, n.name FROM nodes n
            WHERE n.type='Fenomeno' AND NOT EXISTS (
                SELECT 1 FROM edges e WHERE e.from_id=n.id AND e.relation='si_manifesta_in')
            ORDER BY n.name
        """)
        fenomeni_orfani = [{"id": r[0], "nome": r[1]} for r in cur.fetchall()]

        # 6. BUCHI — fenomeni senza numero-bersaglio nel data (regola di partizione)
        # Il numero canonico è numero_bersaglio OPPURE target (fallback legacy),
        # come fa contenuto._numero_bersaglio (fonte unica di verità).
        cur.execute("""
            SELECT id, name FROM nodes
            WHERE type='Fenomeno'
              AND COALESCE(NULLIF(data->>'numero_bersaglio',''), NULLIF(data->>'target','')) IS NULL
            ORDER BY name
        """)
        fenomeni_senza_target = [{"id": r[0], "nome": r[1]} for r in cur.fetchall()]

        # 7. COVERAGE per disciplina: fenomeni collegati a prodotti di quel dominio
        cur.execute("""
            SELECT p.domain, COUNT(DISTINCT e.from_id) AS fenomeni_attivi, COUNT(*) AS connessioni
            FROM edges e
            JOIN nodes p ON p.id=e.to_id AND p.type='Prodotto'
            WHERE e.relation='si_manifesta_in' AND p.domain IS NOT NULL
            GROUP BY p.domain ORDER BY connessioni DESC
        """)
        coverage_disciplina = [
            {"disciplina": r[0], "fenomeni_collegati": r[1], "connessioni": r[2]}
            for r in cur.fetchall()
        ]

        # 8. prodotti per dominio (ampiezza)
        cur.execute("SELECT COALESCE(domain,'(nessuno)'), COUNT(*) FROM nodes WHERE type='Prodotto' GROUP BY domain ORDER BY COUNT(*) DESC")
        prodotti_per_dominio = [{"disciplina": r[0], "prodotti": r[1]} for r in cur.fetchall()]

        # 9. INGREDIENT COVERAGE (metrica-chiave per foto→menù):
        # % di ingredienti con almeno un arco verso un fenomeno/tecnica/prodotto.
        # Un ingrediente "coperto" = ha almeno una connessione uscente o entrante utile.
        cur.execute("SELECT COUNT(*) FROM nodes WHERE type='Ingrediente'")
        ing_totali = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(DISTINCT n.id) FROM nodes n
            WHERE n.type='Ingrediente' AND (
                EXISTS (SELECT 1 FROM edges e WHERE e.from_id=n.id)
                OR EXISTS (SELECT 1 FROM edges e WHERE e.to_id=n.id)
            )
        """)
        ing_connessi = cur.fetchone()[0]
        # ingredienti con percorso verso un FENOMENO (coverage "forte")
        cur.execute("""
            SELECT COUNT(DISTINCT n.id) FROM nodes n
            JOIN edges e ON (e.from_id=n.id OR e.to_id=n.id)
            JOIN nodes f ON (f.id=e.from_id OR f.id=e.to_id) AND f.type='Fenomeno'
            WHERE n.type='Ingrediente'
        """)
        ing_verso_fenomeno = cur.fetchone()[0]
        ingredient_coverage = {
            "ingredienti_totali": ing_totali,
            "ingredienti_connessi": ing_connessi,
            "ingredienti_verso_fenomeno": ing_verso_fenomeno,
            "coverage_pct": round(100.0 * ing_connessi / ing_totali, 1) if ing_totali else 0,
            "coverage_forte_pct": round(100.0 * ing_verso_fenomeno / ing_totali, 1) if ing_totali else 0,
        }

        # ── MENU-READY COVERAGE ──
        # Un prodotto è "menu-ready" quando percorre il percorso completo verificato:
        # prodotto ← si_manifesta_in ← Fenomeno (con numero-bersaglio) → realizzato_da → Tecnica/Processo.
        # È la metrica che misura quanto la feature foto→menù può produrre proposte AZIONABILI,
        # non solo quante connessioni esistono. Calcolata per disciplina.
        menu_ready = {}
        try:
            cur.execute("""
                SELECT p.domain,
                       COUNT(DISTINCT p.id) AS prodotti_tot,
                       COUNT(DISTINCT CASE WHEN mr.pid IS NOT NULL THEN p.id END) AS prodotti_ready
                FROM nodes p
                LEFT JOIN (
                    -- prodotti che hanno un percorso completo fen(con target)→tecnica
                    SELECT e1.to_id AS pid
                    FROM edges e1
                    JOIN nodes f ON f.id = e1.from_id AND f.type = 'Fenomeno'
                    JOIN edges e2 ON e2.from_id = f.id AND e2.relation = 'realizzato_da'
                    JOIN nodes t ON t.id = e2.to_id AND t.type IN ('Tecnica','Processo')
                    WHERE e1.relation = 'si_manifesta_in'
                      AND COALESCE(NULLIF(f.data->>'numero_bersaglio',''), NULLIF(f.data->>'target','')) IS NOT NULL
                ) mr ON mr.pid = p.id
                WHERE p.type = 'Prodotto' AND p.domain IS NOT NULL
                GROUP BY p.domain
            """)
            for dom, tot, ready in cur.fetchall():
                menu_ready[dom] = {
                    "prodotti": tot,
                    "menu_ready": ready,
                    "pct": round(100.0 * ready / tot, 1) if tot else 0,
                }
        except Exception:
            pass

        # ── LONGEVITÀ (Exploration Depth + Deep-Connectivity Score) ──
        # Misura la PROFONDITÀ RAMIFICATA di ogni fenomeno: quante ramificazioni
        # attive ha (errori, tecniche, strumenti, connessioni concettuali).
        # È la metrica dell'"inesauribilità": un fenomeno con molte ramificazioni
        # può essere esplorato per mesi. Un pozzo, non una biblioteca.
        # Exploration Depth per fenomeno = errori + tecniche + strumenti + ponti.
        # Deep-Connectivity Score globale = media di (errori+strumenti+ponti) per fenomeno.
        longevita = {}
        try:
            # per ogni fenomeno conto le ramificazioni per tipo di relazione
            cur.execute("""
                SELECT f.id, f.name, f.domain,
                    COUNT(*) FILTER (WHERE e.relation='fallisce_come')     AS errori,
                    COUNT(*) FILTER (WHERE e.relation='realizzato_da')     AS tecniche,
                    COUNT(*) FILTER (WHERE e.relation='controllato_con')   AS strumenti,
                    COUNT(*) FILTER (WHERE e.relation IN ('governato_da','sfrutta','unifica','spiega')) AS ponti
                FROM nodes f
                LEFT JOIN edges e ON e.from_id = f.id
                WHERE f.type='Fenomeno'
                GROUP BY f.id, f.name, f.domain
            """)
            righe = cur.fetchall()
            n_fen = len(righe)
            somma_expl = 0        # exploration depth totale
            somma_dcs = 0         # (errori+strumenti+ponti) totale, per il DCS
            con_errori = 0        # fenomeni con almeno 1 errore
            con_tecnica = 0
            distribuzione = {"core": 0, "secondary": 0, "passive": 0}  # per classe di profondità
            fen_poveri = []       # fenomeni con 0-1 ramificazioni (candidati a stratificazione)
            for fid, nome, dom, err, tec, strum, ponti in righe:
                expl = err + tec + strum + ponti   # exploration depth del fenomeno
                somma_expl += expl
                somma_dcs += err + strum + ponti
                if err > 0: con_errori += 1
                if tec > 0: con_tecnica += 1
                # classe di profondità (soglie da OpenAI: core 5-8, secondary 3-5, passive 1-3)
                if expl >= 5:   distribuzione["core"] += 1
                elif expl >= 3: distribuzione["secondary"] += 1
                else:           distribuzione["passive"] += 1
                if expl <= 1:
                    fen_poveri.append({"id": fid, "nome": nome, "dominio": dom, "ramificazioni": expl})
            longevita = {
                "fenomeni_analizzati": n_fen,
                "exploration_depth_media": round(somma_expl / n_fen, 2) if n_fen else 0,
                "deep_connectivity_score": round(somma_dcs / n_fen, 2) if n_fen else 0,
                "dcs_soglia_target": 3.5,
                "fenomeni_con_errori": con_errori,
                "fenomeni_con_errori_pct": round(100.0 * con_errori / n_fen, 1) if n_fen else 0,
                "fenomeni_con_tecnica": con_tecnica,
                "distribuzione_profondita": distribuzione,
                "fenomeni_poveri": sorted(fen_poveri, key=lambda x: x["ramificazioni"])[:30],
            }
        except Exception:
            pass

        cur.close(); _release_conn(conn)

        # SCORE sintetico per disciplina: combina ampiezza (prodotti) e profondità (connessioni)
        prod_map = {d["disciplina"]: d["prodotti"] for d in prodotti_per_dominio}
        conn_map = {d["disciplina"]: d["connessioni"] for d in coverage_disciplina}
        fen_map = {d["disciplina"]: d["fenomeni_collegati"] for d in coverage_disciplina}
        discipline = sorted(set(list(prod_map.keys()) + list(conn_map.keys())))
        score = []
        for d in discipline:
            if d == "(nessuno)": continue
            prodotti = prod_map.get(d, 0)
            connessioni = conn_map.get(d, 0)
            fenomeni = fen_map.get(d, 0)
            # densità applicativa: connessioni per prodotto (quanto è "spiegato" ogni prodotto)
            dens_app = round(connessioni / prodotti, 2) if prodotti else 0
            score.append({
                "disciplina": d,
                "prodotti": prodotti,              # ampiezza
                "fenomeni_collegati": fenomeni,    # profondità (varietà)
                "connessioni": connessioni,        # profondità (densità)
                "densita_applicativa": dens_app,   # connessioni/prodotto
            })
        score.sort(key=lambda x: x["connessioni"], reverse=True)

        return jsonify({
            "ok": True,
            "sintesi": {
                "nodi_totali": n_nodi,
                "archi_totali": archi_totali,
                "densita_grafo": densita,
                "nodi_per_tipo": nodi_per_tipo,
            },
            "score_per_disciplina": score,
            "ingredient_coverage": ingredient_coverage,
            "menu_ready_coverage": menu_ready,
            "longevita": longevita,
            "archi_per_relazione": archi_per_relazione,
            "buchi": {
                "fenomeni_senza_prodotti": fenomeni_orfani,
                "fenomeni_senza_numero_bersaglio": fenomeni_senza_target,
            },
            "dettaglio_nodi_per_disciplina": per_dominio,
        })
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/collega-orfani", methods=["POST","GET"])
def admin_collega_orfani():
    """Collega i fenomeni orfani ai prodotti (relazione si_manifesta_in).
    Gli archi sono definiti nel codice (non SQL da fuori = sicuro). Idempotente.
    /admin/collega-orfani?s=SECRET&gruppo=bar"""
    import os as _os, json as _json
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    gruppo = request.args.get("gruppo", "bar")

    # Archi definiti nel codice: (fenomeno, prodotto, target, causa)
    ARCHI = {
        "bar": [
            ("fen-batch-cocktail","prod-negroni","diluizione 20-25% da replicare · acqua vol×0.22 · T <4°C","Il batch pre-diluito replica la diluizione dello stir: senza acqua aggiunta il drink risulta troppo forte"),
            ("fen-batch-cocktail","prod-manhattan","diluizione 20-25% · shelf life 2-3 sett a <4°C","Manhattan in batch: la diluizione va pre-calcolata perché non c'è il ghiaccio a scioglierla al momento"),
            ("fen-clarificazione-cocktail","prod-sour","agar 0.3-0.5g/L · NTU <10 · perdita aromi <5%","Il sour clarificato diventa limpido mantenendo l'acidità: l'agar intrappola le particelle"),
            ("fen-clarificazione-cocktail","prod-daiquiri","agar 0.3-0.5g/L · gel 4°C · NTU <10","Daiquiri clarificato: la gel filtration rimuove la torbidità del lime mantenendo il profilo aromatico"),
            ("fen-ghiaccio-cocktail","prod-old-fashioned","stirring 30-45s · diluizione 15-18% · T -4/-6°C","L'Old Fashioned si mescola: il ghiaccio raffredda e diluisce lentamente fino al punto di equilibrio"),
            ("fen-ghiaccio-cocktail","prod-drink-freddo","shake 10-15s diluizione 20-25% · stir 30-45s 15-18%","Shaking vs stirring determinano diluizione e temperatura finali diverse: il ghiaccio è l'ingrediente invisibile"),
            ("fen-texture-agents","prod-whiskey-sour","albume 2-3cl · dry shake 10-15s · aquafaba 3-4cl","Il Whiskey Sour con albume: il dry shake denatura le proteine creando la schiuma stabile"),
            ("fen-texture-agents","prod-sour","albume 2-3cl · xantano 0.1-0.3g/L · glicerina 5-10ml/L","Gli agenti di texture danno corpo e schiuma al sour: albume per la foam, xantano per la viscosità"),
            ("fen-cold-brew","prod-caffe","rapporto 1:8 concentrato / 1:15 pronto · macinatura grossa · 12-24h · pH 5.2-6.3","Il cold brew estrae a freddo per 12-24h: meno acidità e amaro rispetto all'estrazione a caldo"),
            ("fen-estrazione-polifenoli","prod-bitter","macerazione 7-21 giorni · T 25-28°C · IPT 50-80","Il bitter estrae polifenoli e principi amari dalle botaniche per macerazione idroalcolica"),
            ("fen-estrazione-polifenoli","prod-vino-rosso","macerazione 7-21 giorni · antociani >200 mg/L · IPT 50-80","La macerazione delle bucce nel vino rosso estrae antociani (colore) e tannini (struttura)"),
        ],
        "pasticceria": [
            ("fen-crema-pasticcera","prod-creme-pasticcera","T finale 82-85°C · amido 80-100g/L · tuorli 6-8/L · gelatinizza da 62°C","La crema pasticcera coagula i tuorli e gelatinizza l'amido: sotto 82°C resta liquida, sopra 85°C stracci"),
            ("fen-ganache","prod-ganache","panna/cioccolato 1:1 morbida · 1:2 soda · T panna 80-85°C","La ganache è un'emulsione: la panna calda scioglie il cioccolato e il grasso si disperde nell'acqua"),
            ("fen-meringa","prod-meringa","zucchero/albume 2:1 · italiana 118-121°C · svizzera 45-50°C · pH 4-5","La meringa è schiuma proteica: lo zucchero stabilizza l'albume montato, l'acido abbassa il pH per la stabilità"),
            ("fen-montatura-panna","prod-panna-montata","grasso >35% · T panna 4-6°C · non oltre 80% volume","La panna monta solo fredda e con grasso >35%: le bolle d'aria sono stabilizzate dai globuli di grasso"),
            ("fen-pasta-frolla","prod-biscotti","burro 50-60% (sablée) · riposo 30-60 min 4°C","La frolla impermeabilizza il glutine col burro: più grasso = più friabile, il riposo rilassa la maglia"),
            ("fen-temperaggio-cioccolato","prod-cioccolato-temperato","fondente 31-32°C · latte 29-30°C · bianco 28-29°C","Il temperaggio cristallizza il burro di cacao nella forma beta stabile: lucido, croccante, che non fiorisce"),
            ("fen-zucchero-cottura","prod-caramello","palline 112-115°C · hard crack 149-154°C · caramello 160-180°C","Gli stadi di cottura dello zucchero dipendono dalla temperatura: ogni soglia dà una consistenza diversa"),
            ("fen-souffle","prod-choux","T forno 170-180°C · 12-15 min · neve ferma","Il soufflé sale per l'aria nella montata proteica che si espande col calore: apri il forno e collassa"),
            ("fen-gelificazione","prod-creme-brulee","gelatina 6-12g/L · agar 2-5g/L · pectina HM 5-15g/L · pH <3.5","La gelificazione crea un reticolo che intrappola il liquido: ogni gelificante ha dosi e temperature proprie"),
            ("fen-laminazione","prod-sfoglia","T burro 14-16°C · strati 27-55 · riposo 20-30 min 4°C","La laminazione alterna strati di pasta e burro: il vapore li separa in cottura creando la sfogliatura"),
        ],
        "bakery": [
            ("fen-idratazione-impasto","prod-ciabatta","ciabatta 75-85% · focaccia 80-90% · farina W>300","L'idratazione determina la struttura: più acqua = alveolatura più aperta, ma serve farina forte"),
            ("fen-maglia-glutinica","prod-pane-madre","W 280-350 · P/L 0.5-0.8 · idratazione 65-80%","La maglia glutinica trattiene i gas della lievitazione: si sviluppa con l'impasto e l'idratazione corretta"),
            ("fen-poolish-biga","prod_lievito_madre","poolish 1:1 · 0.1-0.3% lievito · 8-16h 18-20°C","I pre-fermentati sviluppano aromi e forza prima dell'impasto finale: poolish liquido, biga solida"),
            ("fen-sale-impasto","prod-impasto","1.8-2.2% su farina · mai sul lievito · Aw ~0.97","Il sale rinforza il glutine e regola la fermentazione: a contatto diretto disidrata e uccide il lievito"),
            ("fen-enzimi-farina","prod_farina_frumento","Falling Number 280-350s · proteina 11-14% · amilasi 150-300 FU","Gli enzimi della farina (amilasi, proteasi) determinano panificabilità: il Falling Number li misura"),
            ("fen-shelf-life-pane","prod-pane-conservazione","Aw fresco 0.96-0.97 · shelf life 2-4 giorni · muffe <0.8","Il pane raffermma per retrogradazione dell'amido; l'Aw alta favorisce le muffe: sono due degradi diversi"),
            ("fen-lievitazione","prod-focaccia","raddoppio 1-2h a 24°C · madre 3-5h a 28°C","La lievitazione produce CO₂ che gonfia l'impasto: tempo e temperatura governano il raddoppio"),
            ("fen-crosta","prod-baguette","crosta 160-220°C · vapore primi 12-15 min · colore L* 60-70","La crosta si forma per Maillard + gelatinizzazione superficiale: il vapore iniziale ritarda e migliora la doratura"),
        ],
        "gelateria": [
            ("fen-bilanciamento-gelato","fis_gelato_base","zuccheri 180-220g/kg · grassi 60-110g/kg · solidi 380-420g/kg · PAC 280-320","Il bilanciamento del mix determina cremosità e spatolabilità: zuccheri, grassi e solidi vanno in equilibrio"),
            ("fen-pac-gelateria","prod-gelato-cioccolato","PAC 250-350/kg · congelamento -6.25/-8.75°C · servizio -11/-13°C","Il Potere Anticongelante degli zuccheri decide a che temperatura il gelato resta spatolabile"),
            ("fen-sorbetto","fis_sorbet_base","zuccheri 26-32% · residuo secco 30-36% · PAC 26-30 · frutta 40-60%","Il sorbetto si bilancia senza grassi: gli zuccheri fanno da anticongelante e da struttura"),
            ("fen-overrun-controllo","prod-stracciatella","overrun artigianale 20-35% · T uscita -6/-8°C","L'overrun è l'aria incorporata: troppo poca = gelato duro, troppa = gelato gommoso e povero"),
            ("fen-stabilizzanti-gelato","prod-semifreddo","stabilizzanti 3-8g/kg · carruba 0.2-0.5g/kg · emulsionanti 2-5g/kg","Gli stabilizzanti legano l'acqua libera e impediscono i cristalli di ghiaccio grandi: struttura più liscia"),
        ],
        "birra": [
            ("fen-isomerizzazione-luppolo","prod-birra-ipa","lager 8-15 IBU · IPA 40-100 IBU · BU/GU 0.5-1.0","L'isomerizzazione degli alfa-acidi del luppolo in bollitura crea l'amaro: gli IBU lo misurano"),
            ("fen-efficienza-birra","fis_beer_mash","efficienza mash 75-85% · attenuazione 70-85% · ABV=(OG-FG)×131.25","L'efficienza di birrificazione lega OG, FG e ABV: quanto zucchero estrai e quanto ne fermenti"),
            ("fen-lagering","prod-birra-lager","T 0-4°C · 4-12 settimane · diacetile <0.10 mg/L · NTU <5","Il lagering matura la birra a freddo: riassorbe il diacetile e chiarifica per precipitazione"),
            ("fen-dry-hopping","prod-birra-ipa","dry hopping 2-10g/L · T 2-12°C · 7-14 giorni","Il dry hopping aromatizza a freddo senza amaro: estrae oli essenziali del luppolo per solo aroma"),
            ("fen-fermentazione-alta-bassa","prod-birra-lager","ale 15-24°C 5-10gg · lager 4-12°C 7-14gg + lagering","Lieviti ad alta (ale) e bassa (lager) fermentazione lavorano a temperature diverse dando profili diversi"),
            ("fen-mash-enzimi","fis_beer_mash","saccarificazione 64-68°C · pH mash 5.2-5.4 · 60-90 min","Il mash attiva le amilasi che spezzano l'amido del malto in zuccheri fermentabili: la temperatura sceglie il profilo"),
            ("fen-acqua-birra","fis_beer_mash","pH mash 5.2-5.6 · calcio 50-150 mg/L · SO₄/Cl >2:1 hoppy","Il profilo dell'acqua (sali, pH) modella l'estrazione e il carattere: solfati per l'amaro, cloruri per il maltato"),
            ("fen-rifermentazione","prod-spumante-base","pressione 4.5-6.5 atm · liqueur 20-24g/L · sur lies 12+ mesi","La rifermentazione in bottiglia produce CO₂ e pressione: la spumantizzazione classica affina sui lieviti"),
        ],
        "vino": [
            ("fen-acidita-volatile","prod-vino-ossidato","AV <0.6 g/L sano · limite 1.08-1.20 g/L · soglia 0.6-0.9 g/L","L'acidità volatile (acido acetico) è un difetto: sopra soglia dà sentori di aceto e smalto"),
            ("fen-affinamento-vino","prod-vino-rosso","micro-ossigenazione 1-2 mg/L/anno · T 12-15°C · umidità 70-80%","L'affinamento in bottiglia è evoluzione riduttiva: micro-ossigeno lento che ammorbidisce e complessa"),
            ("fen-solforosa","prod_vino_bianco","SO₂ libero 25-35 mg/L · molecolare 0.5-0.8 mg/L · pH 3.2-3.4","La solforosa protegge da ossidazione e microbi: la frazione molecolare (dipende dal pH) è quella attiva"),
            ("fen-brett","prod-vino-rosso","4-EP <230 μg/L · 4-EG <33 μg/L · SO₂ molecolare >0.5 mg/L","Il Brettanomyces produce fenoli volatili (sentori di stalla, cerotto): la solforosa lo previene"),
            ("fen-maturazione-legno","prod-vino-rosso","barrique 6-18 mesi · O₂ 20-40 mL/L/anno · tannini eluibili","La maturazione in legno cede tannini e aromi e permette micro-ossigenazione controllata"),
        ],
        "caffetteria": [
            ("fen-tostatura-caffe","prod-caffe-tostato","primo crack 196-205°C · sviluppo 12-20% · riposo 7-14gg","La tostatura sviluppa gli aromi via Maillard e caramellizzazione: il primo crack segna l'inizio dello sviluppo"),
            ("fen-water-recipe-caffe","prod-espresso","TDS 75-250 mg/L · Ca 50-75 · Mg 10-30 · alcalinità 40-75","La ricetta dell'acqua governa l'estrazione: minerali e alcalinità cambiano cosa e quanto si estrae"),
            ("fen-temperatura-latte","prod-espresso","T finale 60-65°C · mai sopra 70°C · aria +20-30% · pH 6.6-6.8","La montatura del latte incorpora aria e denatura le proteine: sopra 70°C sa di cotto e la schiuma collassa"),
        ],
        "cucina": [
            ("fen-brasatura","prod-carne-sousvide","T 80-85°C · 2-4h · collagene da 68°C · rosolatura >140°C","La brasatura converte il collagene in gelatina a bassa temperatura e lunga cottura: carne che si sfalda"),
            ("fen-brodo-fondo","prod-brodo","T 85-95°C sobbollire · pollo 3-4h · vitello 6-8h · gelatina >2%","Il brodo estrae collagene e gelatina dalle ossa a lungo sobbollire: mai bollire o diventa torbido"),
            ("fen-cottura-sous-vide","prod-sousvide","pollo 63°C×4h · manzo 57°C×2h · pesce 52-55°C×30min","Il sous-vide cuoce a temperatura esatta e costante: il cuore raggiunge il target senza superarlo"),
            ("fen-salamoia","prod-carne-stagionata","salamoia 5-8% sale · pollo 4-12h · dry brine 12-24h","La salamoia idrata e insaporisce per osmosi e denatura le proteine: carne più succosa in cottura"),
        ],
    }
    archi = ARCHI.get(gruppo, [])
    if gruppo == "all":
        archi = [a for lst in ARCHI.values() for a in lst]
    if not archi:
        return jsonify({"errore": f"gruppo '{gruppo}' non definito", "gruppi": list(ARCHI.keys()) + ["all"]}), 400
    try:
        conn = _get_conn(); cur = conn.cursor()
        inseriti, saltati, mancanti = 0, 0, []
        for fen, prod, target, causa in archi:
            # verifica che entrambi i nodi esistano
            cur.execute("SELECT COUNT(*) FROM nodes WHERE id IN (%s,%s)", (fen, prod))
            if cur.fetchone()[0] != 2:
                mancanti.append({"fenomeno": fen, "prodotto": prod})
                continue
            cur.execute("""
                INSERT INTO edges (from_id, to_id, relation, data)
                VALUES (%s, %s, 'si_manifesta_in', %s)
                ON CONFLICT (from_id, to_id, relation) DO NOTHING
            """, (fen, prod, _json.dumps({"target": target, "causa": causa})))
            if cur.rowcount > 0: inseriti += 1
            else: saltati += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "gruppo": gruppo, "inseriti": inseriti,
                        "gia_presenti": saltati, "nodi_mancanti": mancanti})
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/collega-tecniche", methods=["POST","GET"])
def admin_collega_tecniche():
    """Collega i fenomeni bar alle tecniche (relazione realizzato_da).
    Archi definiti nel codice = sicuro. Idempotente. Ogni arco ha una nota causale.
    /admin/collega-tecniche?s=SECRET&gruppo=bar"""
    import os as _os, json as _json
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    gruppo = request.args.get("gruppo", "bar")

    # (fenomeno, tecnica, nota) — abbinamenti tecnici verificati sui dati reali
    ARCHI_TEC = {
        "bar": [
            ("fen-diluizione","tec-shake","Lo shake diluisce del 20-28% raffreddando a -4/-6°C"),
            ("fen-diluizione","tec-stir","Lo stir diluisce del 15-22%, più controllato dello shake"),
            ("fen-ghiaccio-cocktail","tec-shake","Il ghiaccio nello shake: 10-15s, diluizione 20-25%"),
            ("fen-ghiaccio-cocktail","tec-stir","Il ghiaccio nello stir: 30-45s, diluizione 15-18%"),
            ("fen-batch-cocktail","tec-stir","Il batch replica la diluizione dello stir pre-calcolata"),
            ("fen-clarificazione-cocktail","tec-milk-punch","Milk punch: clarificazione al latte, NTU finale <10"),
            ("fen-clarificazione-cocktail","tec-chiarifica","Chiarifica con agar 0.3-0.5g/L, gel a 4°C"),
            ("fen-fat-washing","tec-fat-washing-tecnica","Fat washing: ratio grasso/spirito 1:4-1:6, contatto 20-25°C"),
            ("fen-infusione","tec-macerazione","Infusione/macerazione: fredda 24-72h o calda 50-60°C"),
            ("fen-cold-brew","tec-macerazione","Cold brew: macerazione a freddo prolungata 12-24h"),
            ("fen-estrazione-polifenoli","tec-macerazione","Estrazione polifenoli per macerazione 7-21 giorni"),
            ("fen-texture-agents","tec-shake","Dry shake 10-15s per la schiuma proteica (albume/aquafaba)"),
            ("fen-pressione","tec-carbonatazione-tecnica","Carbonatazione: 2-4 bar per i sodati custom"),
            ("fen-rifermentazione","tec-carbonatazione-tecnica","Rifermentazione: pressione 4.5-6.5 atm in bottiglia"),
            ("fen-chiarificazione","tec-chiarifica","Chiarifica e stabilizzazione: NTU <5 brillante, <1 cristallino"),
            ("fen-isomerizzazione-luppolo","tec-mash","Isomerizzazione in bollitura del mash: 8-100 IBU secondo stile"),
            ("fen-dry-hopping","tec-dry-hopping-tecnica","Dry hopping 2-10g/L a freddo 2-12°C per 7-14 giorni"),
            ("fen-lagering","tec-lagerizzazione","Lagerizzazione: maturazione a freddo 0-4°C, 4-12 settimane"),
            ("fen-fermentazione-alta-bassa","tec-lagerizzazione","Bassa fermentazione (lager) matura a freddo"),
            ("fen-macerazione" if False else "fen-maturazione-legno","tec-macerazione","Maturazione ed estrazione dal legno per contatto prolungato"),
            ("fen-fermentazione-acetica","tec-fermentazione-lattica","Fermentazione acetica: processo fermentativo controllato (5-8% acido acetico)"),
            ("fen-malolattica","tec-fermentazione-lattica","Malolattica: conversione acido malico→lattico"),
            ("fen-solubilita","tec-cottura-zucchero","Solubilità zuccheri: sciroppi (saccarosio 200g/100ml a 20°C)"),
            ("fen-cristallizzazione-ghiaccio","tec-shake","Cristallizzazione del ghiaccio in miscelazione: cristalli <50 micron"),
        ],
        "pasticceria": [
            ("fen-temperaggio-cioccolato","tec-temperaggio","Temperaggio: cristallizzazione beta stabile del burro di cacao (fondente 31-32°C)"),
            ("fen-meringa","tec-montatura","Meringa: montatura dell'albume in schiuma proteica stabile"),
            ("fen-montatura-panna","tec-montatura","Montatura panna: incorporazione d'aria stabilizzata dai grassi (panna >35%)"),
            ("fen-souffle","tec-montatura","Soufflé: montata proteica che si espande col calore in forno"),
            ("fen-zucchero-cottura","tec-cottura-zucchero","Stadi di cottura dello zucchero: dal filo (112°C) al caramello (160-180°C)"),
            ("fen-gelificazione","tec-gelificazione-agar","Gelificazione: reticolo che intrappola il liquido (gelatina/agar/pectina)"),
            ("fen-ganache","tec-emulsione","Ganache: emulsione grasso-acqua tra cioccolato e panna"),
            ("fen-emulsione","tec-emulsione","Emulsione: dispersione stabile di due fasi immiscibili"),
            ("fen-crema-pasticcera","tec-montatura","Crema pasticcera: coagulazione controllata dei tuorli con amido"),
            ("fen-pasta-frolla","tec-impasto","Pasta frolla: impasto che impermeabilizza il glutine col burro"),
            ("fen-caramellizzazione","tec-cottura-zucchero","Caramellizzazione: pirolisi degli zuccheri sopra i 160°C"),
            ("fen-cristallizzazione","tec-temperaggio","Cristallizzazione controllata (burro di cacao, zuccheri)"),
            ("fen-montaggio","tec-montatura","Montaggio/overrun: incorporazione d'aria controllata"),
            ("fen-gelatinizzazione","tec-cottura-zucchero","Gelatinizzazione dell'amido: rigonfiamento in acqua calda (62-70°C)"),
        ],
        "caffetteria": [
            ("fen-estrazione-caffe","tec-estrazione-espresso","Estrazione espresso: 9 bar, TDS/EY nel range corretto"),
            ("fen-tostatura-caffe","tec-mash" if False else "tec-croccante","Tostatura: sviluppo aromatico via Maillard fino al primo crack (196-205°C)"),
            ("fen-temperatura-latte","tec-vaporizzazione-latte","Vaporizzazione del latte: montatura a 60-65°C, mai sopra 70°C"),
            ("fen-water-recipe-caffe","tec-pour-over","Water recipe: mineralità e pH dell'acqua per l'estrazione filtro"),
            ("fen-maillard-controllo","tec-croccante","Maillard: reazione di imbrunimento controllata per temperatura"),
        ],
        "birra": [
            ("fen-mash-enzimi","tec-mash","Saccarificazione del mash: enzimi amilasici a 64-68°C"),
            ("fen-amilolisi","tec-mash","Amilolisi: le amilasi spezzano l'amido in zuccheri fermentabili"),
            ("fen-efficienza-birra","tec-mash","Efficienza: quanto zucchero si estrae nel mash (75-85%)"),
            ("fen-fermentazione-lattica","tec-fermentazione-lattica","Fermentazione lattica: acidificazione controllata (sour/lambic)"),
        ],
        "vino": [
            ("fen-ossidazione","tec-macerazione","Ossidazione controllata in macerazione/affinamento"),
            ("fen-tannini","tec-macerazione","Estrazione tannini per macerazione delle bucce"),
        ],
    }
    archi = ARCHI_TEC.get(gruppo, [])
    if gruppo == "all":
        archi = [a for lst in ARCHI_TEC.values() for a in lst]
    if not archi:
        return jsonify({"errore": f"gruppo '{gruppo}' non definito", "gruppi": list(ARCHI_TEC.keys())}), 400
    try:
        conn = _get_conn(); cur = conn.cursor()
        inseriti, saltati, mancanti = 0, 0, []
        for fen, tec, nota in archi:
            cur.execute("SELECT COUNT(*) FROM nodes WHERE id IN (%s,%s)", (fen, tec))
            if cur.fetchone()[0] != 2:
                mancanti.append({"fenomeno": fen, "tecnica": tec}); continue
            cur.execute("""
                INSERT INTO edges (from_id, to_id, relation, data)
                VALUES (%s, %s, 'realizzato_da', %s)
                ON CONFLICT (from_id, to_id, relation) DO NOTHING
            """, (fen, tec, _json.dumps({"nota": nota})))
            if cur.rowcount > 0: inseriti += 1
            else: saltati += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "gruppo": gruppo, "inseriti": inseriti,
                        "gia_presenti": saltati, "nodi_mancanti": mancanti})
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/collega-errori", methods=["POST","GET"])
def admin_collega_errori():
    """Collega gli Errori ai Fenomeni (relazione fallisce_come). Archi nel codice, idempotente.
    È il cuore della longevità/ritenzione: l'utente col problema al banco risale al fenomeno.
    /admin/collega-errori?s=SECRET&gruppo=bar"""
    import os as _os, json as _json
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    gruppo = request.args.get("gruppo", "bar")

    # (fenomeno, errore, sintomo/nota diagnostica)
    ARCHI_ERR = {
        "bar": [
            ("fen-acidita","err-sour-piatto","Sour piatto: acidità troppo bassa, manca tensione (pH sopra range)"),
            ("fen-acidita","err-sour-squilibrato","Sour squilibrato: rapporto acido/zucchero fuori bilanciamento"),
            ("fen-diluizione","err-drink-annacquato","Drink annacquato: diluizione eccessiva (shake troppo lungo o ghiaccio bagnato)"),
            ("fen-diluizione","err-stirred-acquoso","Stirred acquoso: diluizione oltre il 22% (stir troppo lungo)"),
            ("fen-ghiaccio-cocktail","err-stirred-caldo","Stirred non abbastanza freddo: tempo di stir insufficiente o ghiaccio piccolo"),
            ("fen-ghiaccio-cocktail","err-collins-acquoso","Collins acquoso: ghiaccio che fonde troppo, diluizione non controllata"),
            ("fen-pressione","err-collins-piatto","Collins/Spritz piatto: carbonatazione persa (pressione insufficiente o servizio lento)"),
            ("fen-pressione","err-bevanda-scarica","Bevanda scarica: volumi di CO2 sotto target (2-4 bar)"),
            ("fen-cold-brew","err-caffe-acido","Caffè acido/sottoestratto: estrazione a freddo troppo breve o macinatura troppo grossa"),
        ],
    }
    archi = ARCHI_ERR.get(gruppo, [])
    if gruppo == "all":
        archi = [a for lst in ARCHI_ERR.values() for a in lst]
    if not archi:
        return jsonify({"errore": f"gruppo '{gruppo}' non definito", "gruppi": list(ARCHI_ERR.keys())+["all"]}), 400
    try:
        conn = _get_conn(); cur = conn.cursor()
        inseriti, saltati, mancanti = 0, 0, []
        for fen, err, nota in archi:
            cur.execute("SELECT COUNT(*) FROM nodes WHERE id IN (%s,%s)", (fen, err))
            if cur.fetchone()[0] != 2:
                mancanti.append({"fenomeno": fen, "errore": err}); continue
            cur.execute("""
                INSERT INTO edges (from_id, to_id, relation, data)
                VALUES (%s, %s, 'fallisce_come', %s)
                ON CONFLICT (from_id, to_id, relation) DO NOTHING
            """, (fen, err, _json.dumps({"sintomo": nota})))
            if cur.rowcount > 0: inseriti += 1
            else: saltati += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "gruppo": gruppo, "inseriti": inseriti,
                        "gia_presenti": saltati, "nodi_mancanti": mancanti})
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


@bp.route("/admin/collega-ponti", methods=["POST","GET"])
def admin_collega_ponti():
    """Crea i PONTI TRASVERSALI tra fenomeni di discipline diverse che condividono
    la stessa fisica/chimica (relazione 'unifica'). Sono il motore della longevità:
    l'utente scopre che una legge che usa nei cocktail governa anche la pasticceria.
    Ogni ponte ha la spiegazione scientifica del legame. /admin/collega-ponti?s=SECRET"""
    import os as _os, json as _json
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403

    # (fenomeno_A, fenomeno_B, legge_condivisa) — i 6 ponti su cui OpenAI+Gemini convergono.
    # Ogni ponte è bidirezionale concettualmente ma lo inseriamo come arco 'unifica'.
    PONTI = [
        # 1. CRIOSCOPIA: bar ↔ gelateria
        ("fen-crioscopia","fen-bilanciamento-gelato",
         "Abbassamento crioscopico: la stessa legge che regola la spatolabilità del gelato (PAC, punto di congelamento -6/-9°C) governa la texture dei frozen cocktail e la fusione del ghiaccio da miscelazione."),
        # 2. OSMOSI: cucina/fermentati ↔ pasticceria/canditura
        ("fen-osmosi","fen-salamoia",
         "Pressione osmotica: la stessa legge che estrae l'acqua vegetale nella salamoia (2-3%) e nella fermentazione lattica governa la canditura della frutta e lo sciroppo osmotico dei grandi lievitati."),
        # 3. EMULSIONE: cucina ↔ pasticceria ↔ bar
        ("fen-emulsione","fen-fat-washing",
         "Stabilità dell'emulsione: la frazione olio critica (67-80%) che fa impazzire una maionese è la stessa legge della ganache e del fat washing nei cocktail strutturati."),
        # 4. MAILLARD: cucina ↔ caffè ↔ birra
        ("fen-maillard-controllo","fen-tostatura-caffe",
         "Reazione di Maillard: zuccheri riducenti + amminoacidi col calore secco. Unisce la crosta della bistecca, la tostatura del caffè specialty e i malti scuri della birra."),
        # 5. IDROCOLLOIDI/AGAR: bar/chiarificazioni ↔ pasticceria/gel
        ("fen-gelificazione","fen-clarificazione-cocktail",
         "Reticolazione idrocolloidale: l'agar allo 0.3-0.5% che chiarifica un cocktail (gel filtration) è lo stesso processo che stabilizza un gel specchio in pasticceria."),
        # 6. AMILASI: bakery ↔ birra
        ("fen-enzimi-farina","fen-mash-enzimi",
         "Attività amilasica: alfa e beta-amilasi che scompongono l'amido in zuccheri fermentabili. Lega il riposo del poolish/biga al mash (ammostamento) del birraio."),
    ]
    try:
        conn = _get_conn(); cur = conn.cursor()
        inseriti, saltati, mancanti = 0, 0, []
        for a, b, legge in PONTI:
            cur.execute("SELECT COUNT(*) FROM nodes WHERE id IN (%s,%s)", (a, b))
            if cur.fetchone()[0] != 2:
                mancanti.append({"A": a, "B": b}); continue
            cur.execute("""
                INSERT INTO edges (from_id, to_id, relation, data)
                VALUES (%s, %s, 'unifica', %s)
                ON CONFLICT (from_id, to_id, relation) DO NOTHING
            """, (a, b, _json.dumps({"legge_condivisa": legge})))
            if cur.rowcount > 0: inseriti += 1
            else: saltati += 1
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "inseriti": inseriti, "gia_presenti": saltati, "nodi_mancanti": mancanti})
    except Exception as e:
        try: conn.rollback(); _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)}), 500


# ── CARTA DEI VINI PER CATEGORIE (il canovaccio del sommelier) ──
@bp.route("/v1/carta-vini")
def carta_vini_endpoint():
    """Ritorna la carta dei vini organizzata per categoria (rossi corposi, bianchi freschi,
    bollicine, ecc.) con profilo e abbinamenti. Il canovaccio per costruire la carta."""
    try:
        from carta_vini import CARTA_VINI
    except Exception as e:
        return jsonify({"errore": f"carta non disponibile: {e}"}), 500
    categoria = request.args.get("categoria", "").strip()
    if categoria and categoria in CARTA_VINI:
        return jsonify({"categoria": categoria, "dettaglio": CARTA_VINI[categoria]})
    # tutta la carta, sintetica
    return jsonify({
        "categorie": list(CARTA_VINI.keys()),
        "carta": CARTA_VINI,
        "nota": "Carta dei vini per categorie — canovaccio del sommelier. Usa ?categoria=... per una sola.",
    })


# ── DIALOGO VINO ↔ MENU: dato un piatto/ingrediente, suggerisci la categoria di vino ──
@bp.route("/v1/vino-per-piatto")
def vino_per_piatto():
    """Dato un piatto o ingrediente-chiave, suggerisce quali categorie di vino dialogano,
    col perché scientifico. Il ponte tra la carta dei vini e il menu dello chef."""
    piatto = (request.args.get("piatto", "") or request.args.get("q", "")).strip().lower()
    if not piatto:
        return jsonify({"errore": "specifica ?piatto=..."}), 400
    try:
        from carta_vini import CARTA_VINI
    except Exception as e:
        return jsonify({"errore": f"carta non disponibile: {e}"}), 500
    # regole di dialogo: parole-chiave del piatto -> categorie di vino adatte
    REGOLE = [
        (["brasato", "selvaggina", "cinghiale", "arrosto", "stracotto", "cervo"], ["Rossi corposi"]),
        (["ragù", "lasagne", "pasta al forno", "agnello", "arrosticini", "carne"], ["Rossi medi", "Rossi corposi"]),
        (["pizza", "salumi", "prosciutto", "pancetta", "tortellini"], ["Rossi medi", "Bollicine"]),
        (["pesce", "crudo", "ostrica", "vongole", "frutti di mare", "gambero", "branzino", "orata"], ["Bianchi freschi", "Bollicine"]),
        (["fritto", "frittura", "tempura", "paranza"], ["Bollicine", "Bianchi freschi"]),
        (["mozzarella", "burrata", "formaggio fresco", "latticini"], ["Bianchi freschi", "Bollicine"]),
        (["risotto", "zuppa", "crema", "cremoso"], ["Bianchi strutturati", "Bianchi freschi"]),
        (["formaggio stagionato", "pecorino", "parmigiano", "erborinato", "gorgonzola"], ["Rossi corposi", "Dolci e da meditazione"]),
        (["dolce", "torta", "cioccolato", "pasticceria", "cantucci", "crostata", "tiramisu", "tiramisù", "panna cotta", "cheesecake", "gelato", "semifreddo", "profiterole", "babà", "baba", "cannolo", "sfogliatella", "millefoglie", "zabaione", "mousse", "budino", "dessert"], ["Dolci e da meditazione", "Bollicine"]),
        (["aperitivo", "stuzzichini", "antipasti"], ["Bollicine", "Bianchi freschi"]),
    ]
    categorie_suggerite = []
    for chiavi, categorie in REGOLE:
        if any(k in piatto for k in chiavi):
            for c in categorie:
                if c not in categorie_suggerite:
                    categorie_suggerite.append(c)
    if not categorie_suggerite:
        categorie_suggerite = ["Rossi medi", "Bianchi freschi"]  # default versatile
    # costruisci la risposta con i vini di quelle categorie
    suggerimenti = []
    for cat in categorie_suggerite[:3]:
        dati = CARTA_VINI.get(cat, {})
        vini = dati.get("vini", [])
        suggerimenti.append({
            "categoria": cat,
            "descrizione": dati.get("descrizione", ""),
            "vini_consigliati": [{"nome": v["nome"], "territorio": v["territorio"], "perche": v["perche"]} for v in vini[:3]],
        })
    return jsonify({
        "piatto": piatto,
        "categorie_in_dialogo": categorie_suggerite,
        "suggerimenti": suggerimenti,
        "nota": "Il vino dialoga col piatto: l'acidità pulisce il grasso, il tannino sgrassa, la bollicina rinfresca il fritto.",
    })


# ── PONTI TRA DISCIPLINE (il dialogo della Bibbia) ──
@bp.route("/v1/birra-per-piatto")
def birra_per_piatto_endpoint():
    """Dato un piatto, suggerisce le categorie di birra che dialogano, col perché."""
    piatto = (request.args.get("piatto", "") or request.args.get("q", "")).strip()
    if not piatto:
        return jsonify({"errore": "specifica ?piatto=..."}), 400
    try:
        from dialogo_discipline import birra_per_piatto
        return jsonify({"piatto": piatto, "birre_in_dialogo": birra_per_piatto(piatto),
                        "nota": "La birra dialoga col piatto: l'amaro del luppolo taglia il grasso, il malto richiama la Maillard."})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/v1/dolce-per-menu")
def dolce_per_menu_endpoint():
    """Dato il carattere del menu, suggerisce il dessert che lo chiude (dialogo pasticceria↔cucina)."""
    menu = (request.args.get("menu", "") or request.args.get("q", "")).strip()
    if not menu:
        return jsonify({"errore": "specifica ?menu=... (es. 'menu di pesce leggero')"}), 400
    try:
        from dialogo_discipline import dolce_per_menu
        return jsonify({"menu": menu, "dessert_consigliato": dolce_per_menu(menu)})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/v1/creativita-bar/<spirito>")
def creativita_bar_endpoint(spirito):
    """Dato un distillato, dà spunti per CREARE nuove ricette (il canovaccio del barman creativo)."""
    try:
        from dialogo_discipline import distillato_creativita
        d = distillato_creativita(spirito)
        if not d:
            return jsonify({"errore": f"distillato '{spirito}' non in archivio", "disponibili": ["gin", "rum", "whisky", "tequila", "vodka", "cognac"]}), 404
        return jsonify(d)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


@bp.route("/v1/menu/costruisci", methods=["POST"])
def menu_costruisci():
    """MENU BUILDER VERO: da ingredienti → VOCI DI MENU reali (non il triangolo di connessioni).
    Per ogni piatto realizzabile con gli ingredienti dati, restituisce nome, ingredienti, tecnica,
    e il perché scientifico. Riusa la mappa piatti canonici + il motore di generazione ricette.
    Body: {ingredienti:[nomi], disciplina?:'cucina', max?:5}"""
    body = request.json or {}
    ingredienti = [x.strip().lower() for x in (body.get("ingredienti") or []) if x and x.strip()]
    disc_filtro = (body.get("disciplina") or "").strip()
    max_voci = min(int(body.get("max", 5)), 8)
    if len(ingredienti) < 1:
        return jsonify({"errore": "servi almeno 1 ingrediente", "voci": []}), 400
    try:
        import mappa_piatti
    except Exception as e:
        return jsonify({"errore": f"mappa piatti non disponibile: {e}", "voci": []}), 500

    # 1) trova i piatti realizzabili con questi ingredienti (match sulla firma)
    piatti = mappa_piatti.tutti_i_piatti()
    if disc_filtro:
        piatti = [p for p in piatti if (p.get("disc") or "cucina") == disc_filtro]
    scored = []
    for p in piatti:
        firma = [x.lower() for x in p.get("firma", [])]
        if not firma:
            continue
        n_match = sum(1 for t in ingredienti if any(t in f or f in t for f in firma))
        if n_match >= 1:
            scored.append((n_match, p))
    scored.sort(key=lambda x: -x[0])
    candidati = [p for _, p in scored[:max_voci]]

    if not candidati:
        return jsonify({"ingredienti": ingredienti, "voci": [],
                        "nota": "Nessun piatto noto con questi ingredienti. Prova ad aggiungerne altri."})

    # 2) per ogni candidato, prova a recuperare la ricetta GIÀ generata (veloce), o dà la scheda base
    voci = []
    try:
        conn = _get_conn(); cur = conn.cursor()
        import re, unicodedata
        def _slug(nome):
            s = unicodedata.normalize("NFKD", nome.lower()).encode("ascii","ignore").decode()
            return re.sub(r"[^a-z0-9]+","-",s).strip("-")[:40]
        for p in candidati:
            nome = p["nome"]; disc = p.get("disc") or "cucina"
            rid = f"ric-gen-{_slug(nome)}"
            cur.execute("""SELECT nome, ingredienti, tecniche, fenomeni, punto_critico, descrizione
                           FROM ricette WHERE id=%s OR lower(nome)=lower(%s) LIMIT 1""", (rid, nome))
            row = cur.fetchone()
            if row:
                import json as _j
                def _load(x):
                    if isinstance(x, (list, dict)): return x
                    try: return _j.loads(x) if x else []
                    except: return []
                ingr = _load(row[1]); tec = _load(row[2]); fen = _load(row[3])
                voci.append({
                    "piatto": row[0],
                    "nome": row[0],
                    "disciplina": disc,
                    "ingredienti": [i.get("nome") if isinstance(i, dict) else i for i in ingr][:8],
                    "tecnica": (tec[0].get("nome") if tec and isinstance(tec[0], dict) else (tec[0] if tec else "")),
                    "fenomeni": [f.get("nome") if isinstance(f, dict) else f for f in fen][:2],
                    "perche": row[4] or (row[5] or "")[:140],
                    "pronta": True
                })
            else:
                # ricetta non ancora generata: dò la scheda-base dalla mappa (nome + firma + area)
                voci.append({
                    "piatto": nome,
                    "nome": nome,
                    "disciplina": disc,
                    "ingredienti": p.get("firma", [])[:8],
                    "tecnica": "",
                    "fenomeni": [],
                    "perche": f"Piatto {('tipico ' + p.get('area','')) if p.get('area') else 'classico'}. Ricetta scientifica in generazione.",
                    "pronta": False
                })
        _release_conn(conn)
    except Exception as e:
        return jsonify({"errore": f"db: {e}", "voci": []}), 500

    # ── CREAZIONI INEDITE: dagli abbinamenti aromatici del grafo ──
    # DISATTIVATE al lancio (feature flag). Il grafo Ahn ranking-per-composti propone gli
    # abbinamenti OVVI (nocciola-cioccolato), non gli inediti veri: fa brutta figura e abbassa
    # la fiducia nella parte scientifica. Il codice resta per una v2 con novelty score
    # (molecole × distanza culinaria / frequenza). Per riattivare: FLAG_INEDITE = True.
    FLAG_INEDITE = False
    creazioni_inedite = []
    if FLAG_INEDITE:
      try:
        from builder import _abbinamenti_ingrediente
        db_ab = carica_grafo()
        # per ogni ingrediente, trovo il partner (tra gli altri dati) con più composti condivisi
        migliori_coppie = []
        for i, ing in enumerate(ingredienti):
            ab = _abbinamenti_ingrediente(db_ab, ing, max_n=40)
            for a in ab:
                partner = (a.get("ingrediente") or "").lower()
                overlap = a.get("overlap", 0)
                # il partner è un altro ingrediente della lista?
                for altro in ingredienti[i+1:]:
                    if altro.lower() in partner or partner in altro.lower():
                        migliori_coppie.append((overlap, ing, altro))
        # ordino per composti condivisi (più alto = abbinamento più forte)
        migliori_coppie.sort(key=lambda x: -x[0])
        viste = set()
        for overlap, a, b in migliori_coppie[:2]:
            chiave = tuple(sorted([a.lower(), b.lower()]))
            if chiave in viste or overlap < 20:
                continue
            viste.add(chiave)
            creazioni_inedite.append({
                "piatto": f"Creazione: {a.capitalize()} e {b}",
                "nome": f"Creazione: {a.capitalize()} e {b}",
                "disciplina": disc_filtro or "cucina",
                "ingredienti": [a, b],
                "tecnica": "",
                "fenomeni": [],
                "perche": f"Abbinamento inedito: {a} e {b} condividono {int(overlap)} composti aromatici. "
                          f"Non è un piatto classico — è una creazione suggerita dalla chimica. "
                          f"Tocca 'genera' per la ricetta completa.",
                "pronta": False,
                "inedita": True,
                "composti_condivisi": int(overlap)
            })
      except Exception:
        pass  # se la scoperta inedita fallisce, il menu coi classici resta valido

    return jsonify({
        "ingredienti": ingredienti,
        "voci": voci,
        "creazioni_inedite": creazioni_inedite,
        "totale": len(voci),
        "nota": "Voci di menu realizzabili con i tuoi ingredienti, con la scienza dietro ogni piatto."
                + (" In fondo, creazioni inedite suggerite dagli abbinamenti molecolari." if creazioni_inedite else "")
    })


# ── FOOD COST DI UNA RICETTA (grammature reali × prezzi ISMEA) ──
_PREZZI_FC = {
    "manzo":8.50,"vitello":9.20,"maiale":4.80,"agnello":9.80,"pollo":2.90,"tacchino":3.20,"coniglio":5.50,
    "prosciutto crudo":14.00,"prosciutto cotto":8.50,"salame":9.00,"pancetta":6.50,"mortadella":5.20,
    "speck":13.00,"bresaola":18.00,"guanciale":8.00,"nduja":12.00,
    "salmone":12.00,"tonno":15.00,"branzino":14.00,"orata":12.00,"baccala":9.00,"baccalà":9.00,
    "gamberi":16.00,"gambero":16.00,"cozze":3.50,"vongole":6.00,"acciughe":5.00,"polpo":8.00,"calamaro":7.00,
    "pomodoro":1.20,"pomodori":1.20,"pomodori pelati":1.40,"melanzana":1.50,"melanzane":1.50,"zucchina":1.30,
    "zucchine":1.30,"peperone":2.00,"carota":0.80,"cipolla":0.90,"aglio":3.50,"patata":0.70,"patate":0.70,
    "spinaci":2.50,"rucola":3.00,"finocchio":1.20,"carciofo":2.80,"asparagi":4.50,"funghi":3.50,
    "champignon":3.50,"porcini":18.00,"basilico":12.00,"prezzemolo":8.00,
    "limone":1.50,"arancia":1.20,"fragola":4.00,"pesca":2.50,"mela":1.20,"pera":1.50,"uva":2.00,"lime":3.00,
    "latte":0.95,"panna":2.80,"panna fresca":2.80,"burro":5.50,"mozzarella":6.50,"mozzarella di bufala":8.50,
    "parmigiano":12.00,"parmigiano reggiano":12.00,"pecorino":9.00,"pecorino romano":9.00,"ricotta":4.50,
    "ricotta salata":7.00,"gorgonzola":10.00,"provola":7.00,"provolone":8.00,
    "farina":0.85,"farina 00":0.85,"farina integrale":1.20,"semola":1.00,"semola rimacinata":1.00,
    "riso":2.80,"riso carnaroli":3.20,"riso basmati":2.50,"farro":2.00,"pasta":1.20,"spaghetti":1.20,
    "rigatoni":1.20,"bucatini":1.30,"impasto":1.00,"impasto pizza":1.00,"pane":2.50,
    "olio":7.50,"olio extravergine":7.50,"olio di girasole":2.50,"olio evo":7.50,
    "gin":15.00,"vodka":10.00,"rum":11.00,"whisky":18.00,"tequila":18.00,"cognac":30.00,
    "vino rosso":3.50,"vino bianco":3.00,"prosecco":4.50,"vino":3.20,
    "pepe":15.00,"pepe nero":15.00,"cannella":12.00,"zafferano":1500.00,"vaniglia":200.00,"sale":0.50,
    "zucchero":1.20,"miele":8.00,"uova":3.00,"uovo":3.00,"tuorli":4.50,"tuorlo":4.50,"albume":2.50,
    "cioccolato":8.00,"cioccolato fondente":8.00,"cacao":9.00,"caffe":18.00,"caffè":18.00,
    "mascarpone":6.00,"savoiardi":4.00,"lievito":5.00,"peperoncino":10.00,"olive":6.00,"cozze":3.50,
}

def _prezzo_kg(nome):
    """Trova il prezzo €/kg di un ingrediente (match sul nome, dai prezzi ISMEA)."""
    n = (nome or "").lower().strip()
    if n in _PREZZI_FC: return _PREZZI_FC[n]
    # match parziale: cerca la chiave più lunga contenuta nel nome
    best = None; best_len = 0
    for k, v in _PREZZI_FC.items():
        if (k in n or n in k) and len(k) > best_len:
            best = v; best_len = len(k)
    return best

def _parse_qta(q, unita=""):
    """Converte quantità in kg (o litri). '400'+'g' -> 0.4. 'q.b.' -> None.
    Gestisce anche i pezzi: '4 pz' di uova/tuorli -> peso stimato."""
    import re
    s = str(q or "").lower().strip()
    if not s or "q.b" in s or "qb" in s: return None
    m = re.search(r"(\d+[.,]?\d*)", s)
    if not m: return None
    val = float(m.group(1).replace(",", "."))
    u = (unita or "").lower() + " " + s
    # pezzi: uovo ~55g, tuorlo ~18g (gestiti a monte col nome)
    if "pz" in u or "pezz" in u or " n" in u:
        return ("pz", int(val))  # segnalo che è in pezzi
    if "kg" in u or "litr" in u or " l" in u: return val
    if "mg" in u: return val / 1_000_000
    if "ml" in u or " g" in u or "gr" in u or "grammi" in u: return val / 1000
    return val / 1000 if val >= 10 else None

# peso medio per pezzo di ingredienti contati a unità (kg)
_PESO_PEZZO = {"uovo": 0.055, "uova": 0.055, "tuorlo": 0.018, "tuorli": 0.018,
               "albume": 0.033, "limone": 0.10, "lime": 0.07, "arancia": 0.20,
               "cipolla": 0.15, "patata": 0.15, "pomodoro": 0.12, "melanzana": 0.25}

@bp.route("/v1/ricetta/<rid>/food-cost")
def ricetta_food_cost(rid):
    """Calcola il FOOD COST di una ricetta: grammature reali × prezzi ISMEA.
    ?prezzo_vendita=12 per avere anche il food cost %. Fonte prezzi: ISMEA 2024-2025 (orientativi)."""
    from db import carica_grafo
    db = carica_grafo()
    import json as _j
    rows = db.execute("SELECT nome, ingredienti, porzioni FROM ricette WHERE id=%s", (rid,)).fetchall()
    if not rows:
        return jsonify({"errore": "ricetta non trovata"}), 404
    row = rows[0]
    nome = row["nome"] if hasattr(row, "keys") else row[0]
    ingr_raw = row["ingredienti"] if hasattr(row, "keys") else row[1]
    porzioni_raw = row["porzioni"] if hasattr(row, "keys") else row[2]
    try:
        porzioni = int(re.search(r"\d+", str(porzioni_raw)).group()) if porzioni_raw else 4
    except Exception:
        porzioni = 4
    ingredienti = ingr_raw if isinstance(ingr_raw, list) else (_j.loads(ingr_raw) if ingr_raw else [])

    voci = []; costo_totale = 0.0; mancanti = 0
    for i in ingredienti:
        if not isinstance(i, dict):
            continue
        nome_i = i.get("nome", "")
        qta = i.get("quantita", "") or i.get("quantità", "")
        unita = i.get("unita", "") or i.get("unità", "")
        kg = _parse_qta(qta, unita)
        # se è in pezzi, converto col peso medio dell'ingrediente
        if isinstance(kg, tuple) and kg[0] == "pz":
            n_pezzi = kg[1]
            nome_low = nome_i.lower()
            peso_u = None
            for k, v in _PESO_PEZZO.items():
                if k in nome_low or nome_low in k:
                    peso_u = v; break
            kg = n_pezzi * peso_u if peso_u else None
        prezzo_kg = _prezzo_kg(nome_i)
        if kg is not None and prezzo_kg is not None:
            costo = round(kg * prezzo_kg, 2)
            costo_totale += costo
            voci.append({"ingrediente": nome_i, "quantita": f"{qta} {unita}".strip(),
                         "prezzo_kg": prezzo_kg, "costo": costo})
        else:
            motivo = "prezzo non in ISMEA" if prezzo_kg is None else "quantità q.b."
            voci.append({"ingrediente": nome_i, "quantita": f"{qta} {unita}".strip(),
                         "costo": None, "nota": motivo})
            if prezzo_kg is None: mancanti += 1

    costo_totale = round(costo_totale, 2)
    costo_porzione = round(costo_totale / porzioni, 2) if porzioni else costo_totale
    out = {
        "ricetta": nome, "porzioni": porzioni,
        "costo_totale_ingredienti": costo_totale,
        "costo_per_porzione": costo_porzione,
        "voci": voci, "ingredienti_senza_prezzo": mancanti,
        "fonte": "ISMEA 2024-2025 (prezzi all'ingrosso orientativi)",
        "nota": "Stima orientativa. Per il food cost reale usa i prezzi del tuo fornitore."
    }
    pv = request.args.get("prezzo_vendita")
    if pv:
        try:
            pv = float(pv)
            fc_pct = round(100 * costo_porzione / pv, 1) if pv > 0 else None
            out["prezzo_vendita"] = pv
            out["food_cost_percentuale"] = fc_pct
            out["giudizio"] = ("ottimo" if fc_pct and fc_pct <= 30 else
                               "buono" if fc_pct and fc_pct <= 35 else
                               "alto" if fc_pct and fc_pct <= 45 else "troppo alto")
            out["margine_lordo"] = round(pv - costo_porzione, 2)
        except Exception:
            pass
    return jsonify(out)


# ── DRINK COST (per i cocktail: dosi in ml × prezzi distillati/ingredienti) ──
_PREZZI_BAR = {  # €/litro per i liquidi da bar (in aggiunta a _PREZZI_FC)
    "gin": 15.00, "vodka": 10.00, "rum": 11.00, "rum bianco": 10.00, "rum scuro": 12.00,
    "whisky": 18.00, "whiskey": 18.00, "bourbon": 16.00, "tequila": 18.00, "mezcal": 25.00,
    "cognac": 30.00, "brandy": 18.00, "grappa": 12.00,
    "vermouth": 9.00, "vermouth rosso": 9.00, "vermouth dry": 9.00, "vermut": 9.00,
    "bitter": 14.00, "campari": 14.00, "aperol": 12.00, "amaro": 15.00,
    "triple sec": 12.00, "cointreau": 22.00, "curacao": 14.00, "maraschino": 20.00,
    "prosecco": 4.50, "spumante": 5.00, "champagne": 25.00, "vino bianco": 3.00, "vino rosso": 3.50,
    "succo di limone": 2.00, "succo di lime": 3.00, "succo d'arancia": 1.50, "succo di pompelmo": 2.50,
    "sciroppo di zucchero": 3.00, "sciroppo": 4.00, "soda": 0.80, "tonica": 1.50, "acqua tonica": 1.50,
    "ginger beer": 2.50, "cola": 1.20, "caffè": 6.00, "espresso": 6.00, "latte": 0.95,
    "albume": 3.00, "bianco d'uovo": 3.00, "angostura": 40.00, "bitters": 40.00,
}

def _prezzo_litro_bar(nome):
    n = (nome or "").lower().strip()
    if n in _PREZZI_BAR: return _PREZZI_BAR[n]
    best = None; best_len = 0
    for k, v in _PREZZI_BAR.items():
        if (k in n or n in k) and len(k) > best_len:
            best = v; best_len = len(k)
    if best is not None: return best
    # fallback sui prezzi food (per ingredienti tipo frutta)
    return _prezzo_kg(nome)

@bp.route("/v1/drink-cost", methods=["POST"])
def drink_cost():
    """Calcola il DRINK COST di un cocktail: dosi in ml × prezzi (distillati, mixer, ecc.).
    Body: {nome, ingredienti:[{nome, ml}], prezzo_vendita?}. Fonte prezzi: medi di distribuzione."""
    body = request.json or {}
    nome = body.get("nome", "Cocktail")
    ingredienti = body.get("ingredienti", []) or []
    if not ingredienti:
        return jsonify({"errore": "servono gli ingredienti con le dosi in ml"}), 400
    voci = []; costo_totale = 0.0; mancanti = 0
    for i in ingredienti:
        if not isinstance(i, dict): continue
        nome_i = i.get("nome", "")
        ml = i.get("ml") or i.get("quantita") or 0
        try: ml = float(str(ml).replace(",", "."))
        except Exception: ml = 0
        prezzo_l = _prezzo_litro_bar(nome_i)
        if ml > 0 and prezzo_l is not None:
            costo = round((ml / 1000) * prezzo_l, 3)
            costo_totale += costo
            voci.append({"ingrediente": nome_i, "ml": ml, "prezzo_litro": prezzo_l, "costo": round(costo, 2)})
        else:
            voci.append({"ingrediente": nome_i, "ml": ml, "costo": None,
                         "nota": "prezzo non disponibile" if prezzo_l is None else "dose mancante"})
            if prezzo_l is None: mancanti += 1
    costo_totale = round(costo_totale, 2)
    out = {"drink": nome, "costo_ingredienti": costo_totale, "voci": voci,
           "ingredienti_senza_prezzo": mancanti,
           "fonte": "Prezzi medi di distribuzione (orientativi)",
           "nota": "Stima orientativa. Aggiungi ghiaccio/guarnizione e usa i prezzi del tuo fornitore per il dato reale."}
    pv = body.get("prezzo_vendita")
    if pv:
        try:
            pv = float(pv)
            pct = round(100 * costo_totale / pv, 1) if pv > 0 else None
            out["prezzo_vendita"] = pv
            out["drink_cost_percentuale"] = pct
            out["giudizio"] = ("ottimo" if pct and pct <= 20 else "buono" if pct and pct <= 25 else
                               "alto" if pct and pct <= 35 else "troppo alto")
            out["margine_lordo"] = round(pv - costo_totale, 2)
        except Exception:
            pass
    return jsonify(out)


# ── GENERATORE RICETTE ASINCRONO (evita il timeout 30s di Railway) ──
import threading as _threading
import uuid as _uuid
_JOBS_RICETTE = {}   # fallback in-memory (se il DB non è disponibile)

def _ensure_jobs_table():
    """Tabella job condivisa tra i worker (il dizionario in memoria non è visibile ad altri worker)."""
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS jobs_ricette (
            job_id TEXT PRIMARY KEY, stato TEXT, risultato JSONB, creato_il TIMESTAMP DEFAULT NOW())""")
        conn.commit(); cur.close(); _release_conn(conn)
    except Exception:
        pass

def _job_set(job_id, stato, risultato=None):
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("""INSERT INTO jobs_ricette (job_id, stato, risultato) VALUES (%s,%s,%s::jsonb)
                       ON CONFLICT (job_id) DO UPDATE SET stato=EXCLUDED.stato, risultato=EXCLUDED.risultato""",
                    (job_id, stato, json.dumps(risultato) if risultato is not None else None))
        conn.commit(); cur.close(); _release_conn(conn)
    except Exception:
        _JOBS_RICETTE[job_id] = {"stato": stato, "risultato": risultato}

def _job_get(job_id):
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("SELECT stato, risultato FROM jobs_ricette WHERE job_id=%s", (job_id,))
        r = cur.fetchone(); cur.close(); _release_conn(conn)
        if r:
            return {"stato": r[0], "risultato": r[1]}
    except Exception:
        pass
    return _JOBS_RICETTE.get(job_id)

def _pulisci_job_vecchi():
    """Rimuove i job più vecchi di 15 minuti."""
    try:
        conn = _get_conn(); cur = conn.cursor()
        cur.execute("DELETE FROM jobs_ricette WHERE creato_il < NOW() - INTERVAL '30 minutes'")
        conn.commit(); cur.close(); _release_conn(conn)
    except Exception:
        pass

def _genera_in_background(job_id, richiesta, disciplina, salva, token):
    """Gira in un thread separato: genera la ricetta e mette il risultato nel job."""
    try:
        from builder import genera_ricetta
        from db import carica_grafo
        db = carica_grafo()
        risultato = genera_ricetta(db, richiesta, disciplina=disciplina, lang="it")
        # verifica anti-eresie (leggera)
        try:
            from verificatore_ricette import verifica_ricetta
            verifica = verifica_ricetta(risultato.get("nome", ""), risultato.get("ingredienti", []))
            risultato["_verifica"] = verifica
            if not verifica.get("ok"):
                risultato["_bloccata"] = True
        except Exception:
            pass
        _job_set(job_id, "pronto", risultato)
    except Exception as e:
        _job_set(job_id, "errore", {"errore": str(e)[:150]})

@bp.route("/v1/genera-ricetta-async", methods=["POST"])
def genera_ricetta_async():
    """Avvia la generazione in background. Risponde SUBITO con job_id (202).
    Il frontend poi fa polling su /v1/genera-ricetta-stato/<job_id>. Evita il timeout Railway."""
    if not _check_rate_limit_ai(_chiave_rate()):
        return jsonify({"errore": "rate_limit", "messaggio": "Troppe generazioni. Attendi un minuto."}), 429
    body = request.json or {}
    richiesta = (body.get("richiesta") or "").strip()
    disciplina = body.get("disciplina", "cucina")
    salva = bool(body.get("salva", False))
    token = request.headers.get("X-Token", "") or body.get("token", "")
    if not richiesta:
        return jsonify({"errore": "richiesta mancante"}), 400
    _ensure_jobs_table()
    _pulisci_job_vecchi()
    job_id = "job-" + _uuid.uuid4().hex[:12]
    _job_set(job_id, "in_corso", None)
    t = _threading.Thread(target=_genera_in_background, args=(job_id, richiesta, disciplina, salva, token), daemon=True)
    t.start()
    return jsonify({"job_id": job_id, "stato": "in_corso",
                    "messaggio": "Generazione avviata. Controlla lo stato tra qualche secondo."}), 202

@bp.route("/v1/genera-ricetta-stato/<job_id>", methods=["GET"])
def genera_ricetta_stato(job_id):
    """Polling: restituisce lo stato del job. Quando 'pronto', include la ricetta."""
    job = _job_get(job_id)
    if not job:
        # il job potrebbe non essere ancora visibile su questo worker (i job stanno nel DB ma
        # può esserci un attimo di latenza). Se il job_id ha il formato giusto, rispondo "in_corso"
        # così il frontend continua il polling invece di rompere con un 404 spurio.
        if job_id and job_id.startswith("job-"):
            return jsonify({"stato": "in_corso"})
        return jsonify({"stato": "non_trovato", "messaggio": "Job inesistente, rilancia la generazione."}), 404
    if job["stato"] == "in_corso":
        return jsonify({"stato": "in_corso"})
    if job["stato"] == "errore":
        return jsonify({"stato": "errore", "errore": (job.get("risultato") or {}).get("errore", "errore")})
    return jsonify({"stato": "pronto", "ricetta": job.get("risultato")})
