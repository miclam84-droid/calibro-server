# ============================================================
# MODELLO QUANTITA — densita' (g<->ml) e calo peso (crudo->cotto)
# Le due omissioni critiche F&B (revisori): i liquidi non hanno densita' 1,0
# (miele/olio/sciroppi), e il peso cotto != peso crudo. Senza, food-cost per
# porzione e allergeni sul piatto finito sono falsati.
# Tutto DETERMINISTICO e DICHIARATO: valori di riferimento da tabelle standard,
# approssimati, correggibili al banco (stato 'riferimento'/'stima', mai 'misurato').
# Fonti: pesi specifici standard di food-science; cottura = ordine di grandezza da
# tabelle di resa (USDA cooking yields e pratica professionale) — da affinare.
# ============================================================
import unicodedata

from flask import Blueprint, request, jsonify

bp_quantita = Blueprint("misura_quantita", __name__)

# --- DENSITA' / peso specifico (g per 1 ml) — valori di riferimento standard ---
# I LIQUIDI sono il punto critico (densita' != 1,0). Gli aridi variano molto col
# confezionamento: segnati come stima grossolana.
DENSITA = {
    # liquidi (riferimento)
    "acqua": 1.00, "latte": 1.03, "panna": 1.01, "panna liquida": 1.01,
    "olio": 0.91, "olio di oliva": 0.91, "olio d'oliva": 0.91, "burro fuso": 0.91,
    "miele": 1.42, "sciroppo d'acero": 1.32, "sciroppo di zucchero": 1.30,
    "sciroppo di glucosio": 1.43, "melassa": 1.40, "aceto": 1.01, "aceto balsamico": 1.13,
    "vino": 0.99, "succo di limone": 1.03, "succo di lime": 1.03, "salsa di soia": 1.20,
    "yogurt": 1.04, "uovo": 1.03, "albume": 1.04, "tuorlo": 1.03,
    # distillati ~40% vol
    "distillato": 0.95, "gin": 0.94, "vodka": 0.95, "rum": 0.94,
    # aridi (STIMA grossolana, varia col confezionamento)
    "farina": 0.53, "zucchero": 0.85, "zucchero a velo": 0.56, "sale fino": 1.20,
    "cacao": 0.52, "riso": 0.85,
}
_LIQUIDI_RIFERIMENTO = set(["acqua", "latte", "panna", "panna liquida", "olio", "olio di oliva",
    "olio d'oliva", "burro fuso", "miele", "sciroppo d'acero", "sciroppo di zucchero",
    "sciroppo di glucosio", "melassa", "aceto", "aceto balsamico", "vino", "succo di limone",
    "succo di lime", "salsa di soia", "yogurt", "uovo", "albume", "tuorlo",
    "distillato", "gin", "vodka", "rum"])

# --- CALO PESO: resa = peso finale / peso crudo (tecniche di PERDITA) ---
# Ordine di grandezza da tabelle standard; da affinare (USDA cooking yields / banco).
# NB: pasta/riso/legumi ASSORBONO acqua (resa > 1): caso separato, non qui.
CALO = {
    "arrosto": 0.70, "griglia": 0.70, "brasato": 0.65, "bollito carne": 0.65,
    "stufato": 0.68, "forno carne": 0.72, "pesce al forno": 0.80, "pesce in padella": 0.82,
    "frittura": 0.80, "saltato": 0.85, "verdure arrosto": 0.75, "verdure bollite": 0.90,
    "pane": 0.88, "dolci al forno": 0.90, "focaccia": 0.87,
}
# assorbimento (resa > 1) — dichiarato a parte
ASSORBIMENTO = {"pasta": 2.4, "riso": 2.6, "legumi secchi": 2.5}

_NOTA = ("Valore di riferimento da tabelle standard, approssimato: e' un ordine di grandezza "
         "dichiarato, non una misura. Correggilo con la tua prova al banco.")


def _norm(s):
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _cerca(d, nome):
    n = _norm(nome)
    for k in d:
        if _norm(k) == n:
            return k, d[k]
    for k in d:
        if _norm(k) in n or n in _norm(k):
            return k, d[k]
    return None, None


@bp_quantita.route("/v1/converti-quantita", methods=["GET"])
def converti_quantita():
    """g<->ml per un ingrediente. ?valore=&da=g|ml&a=ml|g&ingrediente=miele"""
    try:
        valore = float(request.args.get("valore", ""))
    except Exception:
        return jsonify({"errore": "valore non numerico"}), 400
    da = (request.args.get("da", "g") or "g").lower()
    a = (request.args.get("a", "ml") or "ml").lower()
    ingr = request.args.get("ingrediente", "")
    if da == a:
        return jsonify({"valore_in": valore, "unita_in": da, "valore_out": round(valore, 2), "unita_out": a})
    k, dens = _cerca(DENSITA, ingr)
    if dens is None:
        return jsonify({"errore": "densita' non nota per questo ingrediente",
                        "ingrediente": ingr, "nota": "aggiungibile alla tabella densita'"}), 404
    # g -> ml : ml = g / densita ; ml -> g : g = ml * densita
    if da == "g" and a == "ml":
        out = valore / dens
    elif da == "ml" and a == "g":
        out = valore * dens
    else:
        return jsonify({"errore": "conversione supportata solo tra g e ml"}), 400
    stato = "riferimento" if k in _LIQUIDI_RIFERIMENTO else "stima"
    return jsonify({
        "ingrediente": k, "densita_g_ml": dens,
        "valore_in": valore, "unita_in": da,
        "valore_out": round(out, 2), "unita_out": a,
        "provenienza": {"stato": stato, "fonte": "tabella densita' standard", "formula": "ml=g/d ; g=ml*d"},
        "nota": _NOTA + (" Densita' arida: varia molto col confezionamento." if stato == "stima" else ""),
    })


@bp_quantita.route("/v1/calo-peso", methods=["GET"])
def calo_peso():
    """Peso cotto da peso crudo. ?crudo=<g>&tecnica=arrosto  (anche assorbimento per pasta/riso)"""
    try:
        crudo = float(request.args.get("crudo", ""))
    except Exception:
        return jsonify({"errore": "crudo non numerico"}), 400
    tecnica = request.args.get("tecnica", "")
    k, fatt = _cerca(CALO, tecnica)
    tipo = "calo"
    if fatt is None:
        k, fatt = _cerca(ASSORBIMENTO, tecnica)
        tipo = "assorbimento"
    if fatt is None:
        return jsonify({"errore": "tecnica non nota", "tecnica": tecnica,
                        "tecniche_note": sorted(list(CALO.keys()) + list(ASSORBIMENTO.keys()))}), 404
    cotto = crudo * fatt
    return jsonify({
        "tecnica": k, "tipo": tipo, "resa": fatt,
        "peso_crudo_g": round(crudo, 1), "peso_cotto_g": round(cotto, 1),
        "variazione_pct": round((fatt - 1) * 100, 1),
        "provenienza": {"stato": "stima", "fonte": "tabelle di resa standard (USDA cooking yields / pratica)",
                        "formula": "cotto = crudo * resa"},
        "nota": _NOTA,
    })


@bp_quantita.route("/v1/quantita/tabelle", methods=["GET"])
def tabelle():
    """Le tabelle, per trasparenza e per la UI."""
    return jsonify({"densita_g_ml": DENSITA, "calo_resa": CALO, "assorbimento_resa": ASSORBIMENTO,
                    "nota": _NOTA})
