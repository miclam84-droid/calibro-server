# ============================================================
# routes/api.py — API scientifica: composti, abbinamenti, strumenti, STT, vision.
# Dipende da: db, ai, contenuto, utils.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from ai import estrai_entita, cerca_contesto, _haiku_raw
from contenuto import _scheda_lang, _numero_bersaglio
from utils import _profilo_default, _aggiorna_profilo
from auth import _utente_da_token
from config import DATABASE_URL
import os, json
import ai_gateway as GW
bp = Blueprint("api", __name__)

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
    Gate trial/pro: la foto costa (OpenAI Vision), quindi limitata all'assaggio."""
    from utils import _trial_consentito
    _ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    _tok = (request.form.get("token") or request.args.get("token") or request.headers.get("X-Token","") or "")
    _uid = _utente_da_token(_tok) if _tok else None
    _ok, _info = _trial_consentito(_uid, _ip, tipo="foto", limite=5)
    if not _ok:
        return jsonify({"errore": "trial_esaurito", "trial_esaurito": True,
            "messaggio": "Hai esaurito le prove gratuite. Passa a Pro per usare la foto senza limiti."}), 402
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
    # gate trial/pro: l'audio costa (OpenAI TTS)
    from utils import _trial_consentito
    _ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    _tok = (body.get("token") or request.headers.get("X-Token","") or "")
    _uid = _utente_da_token(_tok) if _tok else None
    _ok, _info = _trial_consentito(_uid, _ip, tipo="foto", limite=5)
    if not _ok:
        return jsonify({"errore": "trial_esaurito", "trial_esaurito": True,
            "messaggio": "Hai esaurito le prove gratuite. Passa a Pro per l'audio."}), 402
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
