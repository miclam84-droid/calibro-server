# ============================================================
# MOTORI CALCOLO — caffe' / cocktail / gelato: SOLO matematica deterministica.
# (revisori) niente narrazione AI nei calcolatori: il "che gusto invento" va alla chat.
# Caffe': resa di estrazione da TDS. Cocktail: diluizione + ABV finale. Gelato: PAC/POD.
# Tutto GET, testabile dal browser. Coefficienti = valori di riferimento standard, dichiarati.
# ============================================================
from flask import Blueprint, request, jsonify

bp_motori = Blueprint("motori_calcolo", __name__)


# ---------------------------------------------------------------------------
# CAFFE' — resa di estrazione (EY%) dal TDS misurato al rifrattometro
#   solidi disciolti = massa_bevanda * TDS%  ;  EY% = solidi / dose
# ---------------------------------------------------------------------------
@bp_motori.route("/v1/motore/caffe", methods=["GET"])
def caffe():
    """?dose=<g caffe>&bevanda=<g bevanda nella tazza>&tds=<% misurato>"""
    try:
        dose = float(request.args.get("dose", ""))
        bevanda = float(request.args.get("bevanda", ""))
        tds = float(request.args.get("tds", ""))
    except Exception:
        return jsonify({"errore": "servono numeri: dose, bevanda, tds"}), 400
    if dose <= 0:
        return jsonify({"errore": "dose deve essere > 0"}), 400
    solidi_g = bevanda * tds / 100.0
    ey = solidi_g / dose * 100.0
    ratio = bevanda / dose
    # fasce di riferimento (SCA): EY 18-22% = equilibrata
    if ey < 18: giudizio = "sotto-estratto (acido/erbaceo)"
    elif ey > 22: giudizio = "sovra-estratto (amaro/astringente)"
    else: giudizio = "estrazione equilibrata"
    return jsonify({
        "dose_g": dose, "bevanda_g": bevanda, "tds_pct": tds,
        "solidi_disciolti_g": round(solidi_g, 2),
        "resa_estrazione_pct": round(ey, 2),
        "brew_ratio": round(ratio, 2),
        "fascia_riferimento": "EY 18-22% equilibrata (SCA)",
        "giudizio": giudizio,
        "provenienza": {"stato": "calcolato", "formula": "EY% = bevanda*TDS/dose", "fonte": "rifrattometria, fasce SCA"},
    })


# ---------------------------------------------------------------------------
# COCKTAIL — diluizione per tecnica + ABV finale
#   drink = coppie volume:abv separate da virgola (es. 60:40,30:0,15:15)
# ---------------------------------------------------------------------------
_DILUIZIONE = {"shake": 0.28, "stir": 0.22, "throw": 0.20, "build": 0.05, "blend": 0.35}


@bp_motori.route("/v1/motore/cocktail", methods=["GET"])
def cocktail():
    """?drink=60:40,30:0,15:15&tecnica=shake   (volume_ml:abv% per ogni ingrediente)"""
    raw = request.args.get("drink", "")
    tecnica = (request.args.get("tecnica", "stir") or "stir").lower()
    if tecnica not in _DILUIZIONE:
        return jsonify({"errore": "tecnica non nota", "tecniche": list(_DILUIZIONE.keys())}), 400
    voci = []
    try:
        for p in raw.split(","):
            p = p.strip()
            if not p:
                continue
            vol_s, abv_s = p.split(":")
            voci.append((float(vol_s), float(abv_s)))
    except Exception:
        return jsonify({"errore": "formato drink: volume:abv,volume:abv (es. 60:40,30:0,15:15)"}), 400
    if not voci:
        return jsonify({"errore": "nessun ingrediente"}), 400
    vol_iniziale = sum(v for v, _ in voci)
    alcol_puro = sum(v * a / 100.0 for v, a in voci)
    acqua = vol_iniziale * _DILUIZIONE[tecnica]
    vol_finale = vol_iniziale + acqua
    abv_finale = (alcol_puro / vol_finale * 100.0) if vol_finale else 0.0
    return jsonify({
        "tecnica": tecnica, "diluizione_pct": round(_DILUIZIONE[tecnica] * 100, 1),
        "volume_iniziale_ml": round(vol_iniziale, 1),
        "acqua_diluizione_ml": round(acqua, 1),
        "volume_finale_ml": round(vol_finale, 1),
        "alcol_puro_ml": round(alcol_puro, 2),
        "abv_finale_pct": round(abv_finale, 1),
        "provenienza": {"stato": "calcolato",
                        "formula": "ABV = alcol_puro / (vol + acqua_diluizione)",
                        "fonte": "diluizione per tecnica (valori di riferimento, Liquid Intelligence); da affinare col tempo di agitazione"},
        "nota": "La diluizione per tecnica e' un riferimento: dipende da ghiaccio, tempo e temperatura. Correggibile al banco.",
    })


# ---------------------------------------------------------------------------
# GELATO — PAC (potere anticongelante) e POD (potere dolcificante) dalla miscela zuccheri
#   coefficienti relativi al saccarosio = 100
# ---------------------------------------------------------------------------
_POD = {"saccarosio": 100, "destrosio": 70, "fruttosio": 170, "zucchero_invertito": 125,
        "sciroppo_glucosio": 50, "lattosio": 16, "miele": 130}
_PAC = {"saccarosio": 100, "destrosio": 190, "fruttosio": 190, "zucchero_invertito": 190,
        "sciroppo_glucosio": 55, "lattosio": 100, "miele": 190}


@bp_motori.route("/v1/motore/gelato", methods=["GET"])
def gelato():
    """?saccarosio=120&destrosio=30&fruttosio=20&...&acqua=650  (grammi). Ritorna PAC/POD totali."""
    zuccheri = {}
    for k in _PAC:
        try:
            g = float(request.args.get(k, "0") or "0")
        except Exception:
            g = 0.0
        if g:
            zuccheri[k] = g
    if not zuccheri:
        return jsonify({"errore": "indica almeno uno zucchero in grammi",
                        "zuccheri_noti": list(_PAC.keys())}), 400
    acqua = 0.0
    try:
        acqua = float(request.args.get("acqua", "0") or "0")
    except Exception:
        acqua = 0.0
    pod_tot = sum(g * _POD[k] / 100.0 for k, g in zuccheri.items())
    pac_tot = sum(g * _PAC[k] / 100.0 for k, g in zuccheri.items())
    zuccheri_g = sum(zuccheri.values())
    # indice su base acqua (PAC per 1000 g di acqua): piu' alto = piu' morbido
    pac_su_acqua = (pac_tot / acqua * 1000.0) if acqua else None
    scoop = None
    if pac_su_acqua is not None:
        if pac_su_acqua < 220: scoop = "duro (poco anticongelante)"
        elif pac_su_acqua > 320: scoop = "troppo morbido / non indurisce"
        else: scoop = "spatolabile (zona di riferimento)"
    return jsonify({
        "zuccheri_g": zuccheri, "zuccheri_totali_g": round(zuccheri_g, 1), "acqua_g": acqua or None,
        "POD_totale": round(pod_tot, 1),
        "PAC_totale": round(pac_tot, 1),
        "PAC_su_1000g_acqua": round(pac_su_acqua, 1) if pac_su_acqua is not None else None,
        "spatolabilita": scoop,
        "fascia_riferimento": "PAC/acqua ~220-320 = spatolabile",
        "provenienza": {"stato": "calcolato", "formula": "PAC/POD = somma(g*coeff/100), coeff rel. saccarosio=100",
                        "fonte": "coefficienti PAC/POD standard di gelateria"},
        "nota": "Coefficienti di riferimento; la spatolabilita' reale dipende anche da grassi e solidi. Da affinare al banco.",
    })
