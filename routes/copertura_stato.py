# ============================================================
# COPERTURA-STATO — numero di copertura ONESTO e vivo del grafo (SOLA LETTURA).
# Risponde a una domanda semplice: quanto è coperto davvero il grafo?
#   - quanti ingredienti hanno un valore su ciascun asse del gusto
#     (dolce/salato/grasso/acido/umami/amaro);
#   - di questi, quanti sono MISURATI (hanno un grezzo compositivo + una fonte
#     citata in proprieta_meta) e non solo una stima AI;
#   - quanti hanno il pannello nutrizionale completo (campo `nutrienti`);
#   - da quali fonti arrivano i dati (USDA / CIQUAL / glutammato / banco / ...).
#
# ONESTÀ: i numeri sono quelli veri del grafo. Dove un conteggio è 0, si mostra 0
# (è informazione: dice che quell'asse/fonte non è ancora coperto). Nessuna
# percentuale gonfiata: le percentuali sono sempre sul totale reale degli
# ingredienti. Zero scritture — solo SELECT name, data FROM nodes.
# ============================================================
import json

from flask import Blueprint, jsonify, render_template

from db import connessione

bp_cop_stato = Blueprint("copertura_stato", __name__)

# Assi del gusto nell'ordine canonico (SCALE-SENSORIALI).
# amaro è incluso: il grafo può averlo (stima AI) anche se nessuna pipeline di
# derivazione lo misura ancora — se il conteggio misurato è 0, lo diciamo.
ASSI = ("dolce", "salato", "grasso", "acido", "umami", "amaro")

NOTA = (
    "Numero di copertura onesto, sola lettura. «per_asse» conta gli ingredienti "
    "che hanno un valore su quell'asse (inclusa la stima AI). "
    "«per_asse_misurato» conta solo quelli con un grezzo compositivo misurato E "
    "una fonte citata (il dato vero da USDA/CIQUAL/glutammato): è sempre ≤ per_asse, "
    "e la differenza è quanto resta da misurare. «con_pannello_nutrienti» conta gli "
    "ingredienti col pannello nutrizionale completo. «per_fonte» conta quanti "
    "ingredienti portano almeno un dato da quella famiglia di fonti (un ingrediente "
    "può comparire in più fonti). Dove un conteggio è 0, 0 è la risposta vera."
)


# Clausola SQL per escludere le scorie `solo_motore` dall'universo: voci tecniche
# del flavor network (es. "bell_pepper") che hanno composti ma mai gusto. Tenute
# dentro gonfiano il denominatore e diluiscono la %. Stessa clausola usata ovunque
# nel codice (misc.py, api.py, admin.py). Esclude se il campo è valorizzato (anche
# false): si tiene solo quando è NULL (= chiave assente o valore JSON null).
COND_NO_SOLO_MOTORE = "(data->>'solo_motore') IS NULL"

NOTA_DENOMINATORE = (
    "esclusi i nodi solo_motore (voci tecniche del flavor network non consultabili "
    "come ingredienti): non entrano nel denominatore, così la % è onesta."
)


def _e_solo_motore(dd):
    """True se il nodo è una scoria `solo_motore` (campo valorizzato, anche false).
    Rispecchia la semantica SQL di COND_NO_SOLO_MOTORE: valorizzato -> fuori universo,
    NULL/assente -> dentro. Funzione pura, nessun DB."""
    if not isinstance(dd, dict):
        return False
    return dd.get("solo_motore") is not None


def _coerce_data(row):
    """Estrae il `data` del nodo da una riga, tollerante al formato.
    row può essere il data diretto (dict o stringa JSON) oppure una tupla/lista
    (name, data) come la ritorna SELECT name, data. Mai solleva: data strano -> {}."""
    campo = row[-1] if isinstance(row, (tuple, list)) else row
    if isinstance(campo, dict):
        return campo
    if not campo:
        return {}
    try:
        return json.loads(campo)
    except (ValueError, TypeError):
        return {}


def _famiglia_fonte(fonte):
    """Normalizza una stringa 'fonte' nella sua famiglia di provenienza.
    None/vuoto -> None (nessun dato). Fonte non riconosciuta -> 'altro'
    (onesto: non la nascondiamo, ma non fingiamo di sapere quale sia)."""
    if not isinstance(fonte, str):
        return None
    t = fonte.strip().lower()
    if not t:
        return None
    if "usda" in t or "fdc" in t:
        return "USDA"
    if "ciqual" in t or "anses" in t:
        return "CIQUAL"
    if "glutammato" in t or "umami" in t or "ninomiya" in t:
        return "glutammato"
    if "banco" in t or "misura" in t:
        return "banco"
    if "ricetta" in t:
        return "ricetta"
    if "etichetta" in t:
        return "etichetta"
    return "altro"


def _pct(n, tot):
    """Percentuale sul totale reale, 1 decimale. tot=0 -> 0.0 (niente divisione gonfiata)."""
    return round(100.0 * n / tot, 1) if tot else 0.0


def aggrega_copertura(nodi):
    """Funzione PURA (nessun DB): dato un iterabile di righe dei nodi
    (ognuna è il `data` del nodo, dict o JSON, oppure una tupla (name, data)),
    ritorna il numero di copertura onesto. Testabile offline senza connessione."""
    tot = 0
    per_asse = {a: 0 for a in ASSI}
    per_asse_misurato = {a: 0 for a in ASSI}
    con_pannello = 0
    per_fonte = {}

    for row in nodi:
        dd = _coerce_data(row)
        # fuori universo: scorie solo_motore (voci tecniche, mai gusto) — non contano
        # nel denominatore. Onestà: tolgono rumore, non gonfiano la %.
        if _e_solo_motore(dd):
            continue
        tot += 1

        prop = dd.get("proprieta")
        prop = prop if isinstance(prop, dict) else {}
        meta = dd.get("proprieta_meta")
        meta = meta if isinstance(meta, dict) else {}

        famiglie = set()
        for a in ASSI:
            if prop.get(a) is not None:
                per_asse[a] += 1
            m = meta.get(a)
            m = m if isinstance(m, dict) else {}
            if m.get("grezzo") is not None and m.get("fonte"):
                per_asse_misurato[a] += 1
            fam = _famiglia_fonte(m.get("fonte"))
            if fam:
                famiglie.add(fam)

        # pannello nutrizionale: presente se c'è almeno un valore reale, non scaffolding vuoto
        nutr = dd.get("nutrienti")
        if isinstance(nutr, dict) and any(
            isinstance(v, dict) and v.get("valore") is not None for v in nutr.values()
        ):
            con_pannello += 1

        nmeta = dd.get("nutrienti_meta")
        nmeta = nmeta if isinstance(nmeta, dict) else {}
        fam = _famiglia_fonte(nmeta.get("fonte"))
        if fam:
            famiglie.add(fam)

        for fam in famiglie:
            per_fonte[fam] = per_fonte.get(fam, 0) + 1

    # per_fonte ordinato per conteggio decrescente, poi nome (lettura a colpo d'occhio)
    per_fonte_ord = dict(sorted(per_fonte.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "totale_ingredienti": tot,
        "per_asse": per_asse,
        "per_asse_misurato": per_asse_misurato,
        "con_pannello_nutrienti": con_pannello,
        "per_fonte": per_fonte_ord,
        "percentuali": {
            "per_asse": {a: _pct(per_asse[a], tot) for a in ASSI},
            "per_asse_misurato": {a: _pct(per_asse_misurato[a], tot) for a in ASSI},
            "con_pannello_nutrienti": _pct(con_pannello, tot),
        },
        "assi": list(ASSI),
        "nota": NOTA,
        "nota_denominatore": NOTA_DENOMINATORE,
    }


@bp_cop_stato.route("/v1/copertura-stato", methods=["GET"])
def copertura_stato_json():
    """JSON SOLA LETTURA: numero di copertura del grafo.
    {totale_ingredienti, per_asse, per_asse_misurato, con_pannello_nutrienti,
     per_fonte, percentuali}. Solo SELECT name, data FROM nodes — zero scritture."""
    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name, data FROM nodes WHERE type IN ('Ingrediente','Prodotto') "
                "AND " + COND_NO_SOLO_MOTORE
            )
            righe = cur.fetchall()
            cur.close()
    except Exception as e:
        return jsonify({"errore": str(e)[:200]}), 500
    return jsonify(aggrega_copertura(righe))


@bp_cop_stato.route("/copertura-stato")
def copertura_stato_page():
    """Pagina interna (ops) col numero di copertura. Gate server-side ?s=ADMIN_SECRET."""
    import os as _os, hmac as _hmac
    from flask import request as _req, make_response
    if not _hmac.compare_digest(str(_req.args.get("s", "")), str(_os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    resp = make_response(render_template("copertura-stato.html"))
    resp.headers["Cache-Control"] = "no-store"
    return resp
