# ============================================================
# routes/api.py — API scientifica: composti, abbinamenti, strumenti, STT, vision.
# Dipende da: db, ai, contenuto, utils.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import estrai_entita, cerca_contesto, _haiku_raw
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _profilo_default, _aggiorna_profilo, _check_rate_limit
from auth import _utente_da_token
from config import DATABASE_URL
import os, json
import ai_gateway as GW
bp = Blueprint("api", __name__)

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
    Se salva=true, persiste la ricetta generata nel DB (con id ric-gen-<slug>)."""
    from db import carica_grafo
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
        risultato = genera_ricetta(db, richiesta, disciplina=disciplina, lang=lang)
        if risultato.get("errore"):
            return jsonify(risultato), 422
        # salvataggio opzionale
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
                    INSERT INTO ricette (id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,abbinamenti,vino_birra,scheda_en,scheda_es)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO NOTHING
                """, (rid, nome, disciplina, risultato.get("descrizione",""),
                      _j2.dumps(risultato.get("ingredienti",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("fenomeni",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("tecniche",[]),ensure_ascii=False),
                      _j2.dumps(risultato.get("numeri",{}),ensure_ascii=False),
                      risultato.get("punto_critico",""),
                      _j2.dumps(risultato.get("abbinamenti",{}),ensure_ascii=False),
                      _j2.dumps(risultato.get("vino_birra",{}),ensure_ascii=False),
                      "", ""))
                conn.commit(); cur.close(); _release_conn(conn)
                risultato["_salvata"] = True
                risultato["id"] = rid
            except Exception as se:
                risultato["_salvata"] = False
                risultato["_errore_salvataggio"] = str(se)
        return jsonify(risultato)
    except Exception as e:
        import traceback
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-300:]}), 500

@bp.route("/v1/abbina-bevanda")
def abbina_bevanda():
    """Dato un abbinamento vino/birra (query testuale), restituisce i link e-commerce.
    ?q=Barolo&cat=vino  oppure  ?q=IPA&cat=birra"""
    query = request.args.get("q", "").strip()
    cat = request.args.get("cat", "vino")
    if not query:
        return jsonify({"errore": "query mancante (?q=...)"}), 400
    return jsonify({
        "query": query,
        "categoria": cat,
        "links": _link_vino_birra(query, cat),
        "disclosure": "Link affiliati: acquistando tramite questi link supporti Matter Lab senza costi aggiuntivi."
    })


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

@bp.route("/v1/attrezzatura/<tecnica_id>")
def attrezzatura_tecnica(tecnica_id):
    """Utensili consigliati per una tecnica, con link affiliati Amazon (tag via env AMAZON_TAG)."""
    utensili = ATTREZZATURA_TECNICA.get(tecnica_id, [])
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
    """Link affiliato per un prodotto/ingrediente specializzato. ?q=destrosio+gelateria"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"errore": "query mancante (?q=...)"}), 400
    from urllib.parse import quote_plus
    tag = os.environ.get("AMAZON_TAG", "")
    q = quote_plus(query)
    url = f"https://www.amazon.it/s?k={q}"
    if tag:
        url += f"&tag={tag}"
    return jsonify({
        "query": query,
        "url": url,
        "disclosure": "Link affiliato: acquistando tramite questo link supporti Matter Lab senza costi aggiuntivi."
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
    db = carica_grafo()
    try:
        if disc:
            rows = db.execute(
                "SELECT id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,abbinamenti,vino_birra,scheda_en,scheda_es FROM ricette WHERE disciplina=%s ORDER BY nome",
                (disc,)
            )
        else:
            rows = db.execute(
                "SELECT id,nome,disciplina,descrizione,ingredienti,fenomeni,tecniche,numeri,punto_critico,abbinamenti,vino_birra,scheda_en,scheda_es FROM ricette ORDER BY disciplina,nome"
            )
        result=[]
        def _parse(v):
            if v is None: return None
            if isinstance(v,(list,dict)): return v
            try: return _j.loads(v)
            except: return v
        for row in rows:
            r = dict(row) if hasattr(row,"keys") else dict(zip(["id","nome","disciplina","descrizione","ingredienti","fenomeni","tecniche","numeri","punto_critico","abbinamenti","vino_birra","scheda_en","scheda_es"], row))
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
            result.append({
                "id":r.get("id",""),"nome":r.get("nome",""),"disciplina":r.get("disciplina",""),
                "descrizione":desc,
                "ingredienti":_parse(r.get("ingredienti")) or [],
                "fenomeni":_parse(r.get("fenomeni")) or [],
                "tecniche":_parse(r.get("tecniche")) or [],
                "numeri":_parse(r.get("numeri")) or {},
                "punto_critico":r.get("punto_critico") or "",
                "abbinamenti":_parse(r.get("abbinamenti")) or {},
                "vino_birra":vb
            })
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"errore":str(e),"type":type(e).__name__,"tb":traceback.format_exc()[-300:]}), 500

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

@bp.route("/v1/abbina/<ingrediente>")
def abbina(ingrediente):
    """FL3 — Abbinamenti aromatici dal grafo Ahn 2011 (edges abbinamento_aromatico).
    Cerca per nome italiano (con mappa di traduzione) o inglese direttamente.
    Sempre marcato come ipotesi eurisitca, mai come legge."""
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
    # se non c'è alias, prova diretto
    search_terms = []
    if ahn_name:
        search_terms.append(f"ahn_{ahn_name}")
        search_terms.append(f"ahn_{ahn_name.replace(' ','_')}")
    search_terms.append(f"ahn_{ing_norm}")
    search_terms.append(f"ahn_{ing_norm.replace('_',' ')}")

    if not DATABASE_URL:
        return jsonify({"ingrediente":ingrediente,"abbinamenti":[],
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
                    return jsonify({"ingrediente":ingrediente,"abbinamenti":_pre_abbs,
                        "fonte":"dataset Matter Lab",
                        "nota":"Abbinamenti da profilo sensoriale proprietario Matter Lab"})
                # Nodo trovato ma con pochi abbinamenti — arricchisci con AI
                _cat_pre = _pre_data.get("categoria","")
                _prof_pre = _pre_data.get("categorie_aromatiche",[])
                _ai_pre = ("Dammi 5 abbinamenti per " + str(ingrediente) +
                           " (" + str(_cat_pre) + ") con meccanismo fisico-chimico. "
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
                                return jsonify({"ingrediente":ingrediente,
                                    "abbinamenti":[{"ingrediente":a.get("ingrediente_it","?"),
                                        "composto":"abbinamento aromatico",
                                        "overlap":float(a.get("overlap_score",50)),
                                        "perche":a.get("meccanismo","affinità aromatica")}
                                        for a in _ap[:5]],
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
                AND (lower(e.from_id) = lower(%s)
                     OR lower(e.from_id) LIKE lower(%s))
                ORDER BY overlap DESC NULLS LAST LIMIT 15
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
                        return jsonify({"ingrediente":ingrediente,"abbinamenti":result_props,
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
                                        return jsonify({"ingrediente":ingrediente,
                                            "abbinamenti":result_props,
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
                            return jsonify({"ingrediente":ingrediente,
                                "abbinamenti":[{"ingrediente":a.get("ingrediente_it","?"),
                                    "composto":"abbinamento aromatico",
                                    "overlap":float(a.get("overlap_score",50)),
                                    "perche":a.get("meccanismo","affinità aromatica")}
                                    for a in _abbs5[:5]],
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
        for r in rows:
            nome_en = r[1].replace("_"," ").lower() if r[1] else ""
            # fallback: se manca la traduzione IT usa il nome Ahn in Title Case
            nome_fallback = r[1].replace("_"," ").title() if r[1] else "sconosciuto"
            nome_pulito = NOMI_IT.get(nome_en, nome_fallback)
            # salta i nodi senza nome
            if not nome_pulito or nome_pulito == "sconosciuto":
                continue
            overlap = float(r[2]) if r[2] else 0
            abbinamenti.append({
                "ingrediente": nome_pulito,
                "composto": f"{overlap:.0f} composti in comune",
                "overlap": overlap,
                "perche": f"condividono {overlap:.0f} composti aromatici"
            })
        # deduplica per nome (possono esserci nodi EN e IT con lo stesso nome)
        # ed esclude l'auto-abbinamento (l'ingrediente cercato con se stesso)
        _cercato = ingrediente.lower().strip()
        seen_nomi = set()
        abbinamenti_dedup = []
        for a in sorted(abbinamenti, key=lambda x: -x["overlap"]):
            n_lower = a["ingrediente"].lower().strip()
            if n_lower in seen_nomi:
                continue
            # salta se è l'ingrediente stesso (self-match)
            if n_lower == _cercato or n_lower == NOMI_IT.get(_cercato, "").lower():
                continue
            seen_nomi.add(n_lower)
            abbinamenti_dedup.append(a)
            if len(abbinamenti_dedup) >= 15:
                break
        abbinamenti = abbinamenti_dedup
        return jsonify({
            "ingrediente": ingrediente,
            "abbinamenti": abbinamenti,
            "nota": "Ipotesi di abbinamento per composti volatili condivisi — non è una garanzia nutrizionale",
            "fonte": "Dataset Ahn 2011 (CC BY)"
        })
    except Exception as e:
        return jsonify({"ingrediente":ingrediente,"abbinamenti":[],
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

    # mappo ogni ingrediente al suo nodo Ahn (helper condiviso _alias_ahn)
    ahn_map = {}  # nome_utente -> ahn_name
    for ing in ingredienti:
        a = _alias_ahn(ing)
        if a: ahn_map[ing] = a

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
                # cerco l'edge di abbinamento tra i due nodi; overlap = forza del legame
                cur.execute("""
                    SELECT COALESCE(MAX((e.data->>'overlap')::numeric), 0)
                    FROM edges e
                    WHERE e.relation='abbinamento_aromatico'
                      AND ((lower(e.from_id)=lower(%s) AND lower(e.to_id)=lower(%s))
                        OR (lower(e.from_id)=lower(%s) AND lower(e.to_id)=lower(%s)))
                """, (f"ahn_{a1}", f"ahn_{a2}", f"ahn_{a2}", f"ahn_{a1}"))
                r = cur.fetchone()
                forza = int(float(r[0])) if r and r[0] else 0
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
                    "connessioni": c["forza"],
                    "esplorativa": esplorativa,
                    "proof": {"ingredienti_disponibili": 2,
                              "connessioni_aromatiche": c["forza"],
                              "nota": "da esplorare al banco" if esplorativa else "legame verificato"}
                })
        # ordino: triangoli prima, poi legami forti, poi esplorative
        proposte.sort(key=lambda p: (0 if p["tipo"]=="triangolo" else 1, 1 if p.get("esplorativa") else 0, -p["connessioni"]))

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
        return jsonify({"errore": str(e), "proposte": []}), 500


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
    """Restituisce il profilo sensoriale dell'utente (9 dimensioni, pesi 0-10)."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"profilo": _profilo_default()})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT profilo_sensoriale FROM utenti WHERE id=%s", (user_id,))
            row = cur.fetchone()
            profilo = row[0] if row and row[0] else _profilo_default()
        except Exception:
            # la colonna potrebbe non esistere ancora: rollback pulito e default
            conn.rollback()
            profilo = _profilo_default()
        cur.close(); _release_conn(conn)
        return jsonify({"profilo": profilo, "interazioni": profilo.get("_n", 0)})
    except Exception as e:
        # non far crashare la UI: restituisci un profilo di default
        print(f"[PROFILO ERRORE] {e}", flush=True)
        try:
            conn.rollback(); _release_conn(conn)
        except Exception:
            pass
        return jsonify({"profilo": _profilo_default(), "interazioni": 0})

@bp.route("/v1/feedback-abbinamento", methods=["POST"])
def feedback_abbinamento():
    """Registra il feedback (like/dislike) su un abbinamento e aggiorna il profilo sensoriale.
    Body: {"ingrediente": "lime", "abbinamento": "zucchero", "voto": 1, "disciplina": "bar"}
    voto: 1=like, -1=dislike
    """
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    body = request.json or {}
    ingrediente = body.get("ingrediente","")
    abbinamento = body.get("abbinamento","")
    voto = int(body.get("voto", 0))
    disciplina = body.get("disciplina","")
    if voto not in (1, -1) or not ingrediente:
        return jsonify({"errore":"voto deve essere 1 o -1, ingrediente obbligatorio"}), 400
    if not DATABASE_URL:
        return jsonify({"ok": True})
    try:
        import psycopg2, psycopg2.extras
        conn = _get_conn()
        cur = conn.cursor()
        # Leggi profilo attuale
        cur.execute("SELECT profilo_sensoriale FROM utenti WHERE id=%s", (user_id,))
        row = cur.fetchone()
        profilo = row[0] if row and row[0] else _profilo_default()
        # Aggiorna profilo in base al voto e al profilo sensoriale dell'ingrediente
        profilo = _aggiorna_profilo(profilo, ingrediente, abbinamento, voto, disciplina)
        # Salva profilo aggiornato
        cur.execute(
            "UPDATE utenti SET profilo_sensoriale=%s WHERE id=%s",
            (psycopg2.extras.Json(profilo), user_id)
        )
        # Salva log feedback
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_abbinamenti (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                ingrediente TEXT,
                abbinamento TEXT,
                voto INTEGER,
                disciplina TEXT,
                ts TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO feedback_abbinamenti (user_id, ingrediente, abbinamento, voto, disciplina)
            VALUES (%s,%s,%s,%s,%s)
        """, (str(user_id), ingrediente, abbinamento, voto, disciplina))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "profilo": profilo, "interazioni": profilo.get("_n", 0)})
    except Exception as e:
        try:
            conn.rollback(); _release_conn(conn)
        except Exception:
            pass
        print(f"[FEEDBACK ERRORE] {e}", flush=True)
        return jsonify({"ok": False, "errore": "non salvato"}), 200

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
                    # spiegazione personalizzata per coppia
                    if meccanismo == "taglia_grasso":
                        perche = (f"{node_name} (pH {ph:.1f}) taglia il grasso di {rname}: "
                                  f"l'acidità emulsiona e pulisce la bocca dopo il grasso")
                    elif meccanismo == "richiede_acido":
                        perche = (f"Il grasso di {node_name} ammorbidisce e porta: "
                                  f"{rname} (pH {float(rd.get('ph_min',3)):.1f}) bilancia con acidità")
                    elif meccanismo == "smorzato_da_dolce":
                        perche = (f"L'amaro di {node_name} viene smorzato dai {rd.get('zuccheri_pct','?')}% "
                                  f"di zuccheri in {rname} — il dolce riduce la percezione amara")
                    elif meccanismo == "smorzato_da_sale":
                        perche = (f"Il sodio in {rname} ({rd.get('sodio_mg100g','?')}mg/100g) "
                                  f"sopprime l'amaro di {node_name} — piccole quantità bastano")
                    elif meccanismo == "bilanciato_da_acido":
                        perche = (f"Il dolce di {node_name} satura senza contrasto: "
                                  f"{rname} (pH {float(rd.get('ph_min',3)):.1f}) taglia e rinfresca")
                    elif meccanismo == "amplificato_da_acido":
                        perche = (f"Il salato di {node_name} si esalta con l'acido di {rname}: "
                                  f"insieme amplificano entrambi i sapori")
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
        return jsonify({"ingredienti": lista, "totale": len(lista), "foto_analizzate": len(imgs)})
    except Exception as e:
        import traceback
        print(f"[RICONOSCI ERRORE] {e}\n{traceback.format_exc()[-500:]}", flush=True)
        return jsonify({"errore": str(e)}), 500


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


@bp.route("/admin/tecniche-diag")
def admin_tecniche_diag():
    """TEMP: elenca Tecniche/Processi esistenti + fenomeni bar senza arco realizzato_da.
    Read-only. /admin/tecniche-diag?s=SECRET"""
    import os as _os
    if request.args.get("s") != _os.environ.get("ADMIN_SECRET", "4z3IXHDD_EL1nNXDtE82qAwuCSwNwRtv"):
        return jsonify({"errore": "non autorizzato"}), 403
    try:
        conn = _get_conn(); cur = conn.cursor()
        # tutte le tecniche e processi
        cur.execute("SELECT id, name, type, domain FROM nodes WHERE type IN ('Tecnica','Processo') ORDER BY type, name")
        tecniche = [{"id":r[0],"nome":r[1],"tipo":r[2],"dominio":r[3]} for r in cur.fetchall()]
        # fenomeni collegati a prodotti bar (via si_manifesta_in) che NON hanno realizzato_da
        cur.execute("""
            SELECT DISTINCT f.id, f.name,
                   COALESCE(NULLIF(f.data->>'numero_bersaglio',''), NULLIF(f.data->>'target','')) AS num
            FROM nodes f
            JOIN edges e1 ON e1.from_id=f.id AND e1.relation='si_manifesta_in'
            JOIN nodes p ON p.id=e1.to_id AND p.type='Prodotto' AND p.domain='bar'
            WHERE f.type='Fenomeno'
              AND NOT EXISTS (SELECT 1 FROM edges e2 WHERE e2.from_id=f.id AND e2.relation='realizzato_da')
            ORDER BY f.name
        """)
        fen_bar_senza_tecnica = [{"id":r[0],"nome":r[1],"numero":r[2]} for r in cur.fetchall()]
        # fenomeni bar CHE HANNO già una tecnica (per riferimento)
        cur.execute("""
            SELECT DISTINCT f.name, t.name AS tecnica
            FROM nodes f
            JOIN edges e1 ON e1.from_id=f.id AND e1.relation='si_manifesta_in'
            JOIN nodes p ON p.id=e1.to_id AND p.type='Prodotto' AND p.domain='bar'
            JOIN edges e2 ON e2.from_id=f.id AND e2.relation='realizzato_da'
            JOIN nodes t ON t.id=e2.to_id
            WHERE f.type='Fenomeno' ORDER BY f.name
        """)
        fen_bar_con_tecnica = [{"fenomeno":r[0],"tecnica":r[1]} for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
        return jsonify({"ok":True, "tecniche_totali":len(tecniche), "tecniche":tecniche,
                        "fen_bar_senza_tecnica":fen_bar_senza_tecnica,
                        "fen_bar_con_tecnica":fen_bar_con_tecnica})
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
    }
    archi = ARCHI_TEC.get(gruppo, [])
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
