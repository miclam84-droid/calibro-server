# ============================================================
# AUDIT-PROVENIENZA — endpoint READ-ONLY (solo SELECT, zero scritture).
# Conta quanti nodi del grafo portano una provenienza FABBRICATA dall'AI:
# un campo 'fonte' (citazione) inventato dal modello (es. "Food Chemistry 2019 /
# McGee") salvato nel data del nodo senza flag di stima, e NON riconducibile a
# una fonte reale verificabile (USDA/FDC, misura, ricetta...).
#
# NON corregge nulla: serve solo a sapere QUANTI dati disonesti sono gia' scritti.
# Il fix che impedisce nuovi casi vive in build_ingredient_graph.marca_provenienza_ai
# (rimuove 'fonte' e marca provenienza.stato='stimato_AI'); questo audit misura il
# debito legacy rimasto prima di quel fix.
#
# Gate: ADMIN_SECRET + ?s= (stesso pattern degli altri admin, hmac.compare_digest).
# ============================================================
import os
import hmac

from flask import Blueprint, request, jsonify

from db import connessione, _dati

bp_audit_prov = Blueprint("audit_provenienza", __name__)

# ── CRITERIO (dichiarato anche nella risposta JSON, cosi' e' verificabile) ──
# stati che dichiarano ONESTAMENTE una stima / derivazione / verifica
STATI_ONESTI = {"stimato", "stimato_ai", "derivato", "corretto", "verificato"}
# token che indicano una FONTE REALE verificabile (quindi NON fabbricata dall'AI)
TOKEN_FONTE_REALE = (
    "usda", "fdc", "misura", "banco", "ricetta",
    "tabella", "densit", "resa", "etichetta", "verificat", "derivat",
)

CRITERIO = (
    "Un nodo e' 'con_fonte_ai_fabbricata' se il suo data contiene un campo "
    "'fonte' (al primo livello, oppure dentro una voce di 'composti_aromatici') "
    "che e' tutte e tre le cose: (a) una stringa non vuota; (b) NON cita una "
    "fonte reale verificabile -- nessuno dei token " + ", ".join(TOKEN_FONTE_REALE) +
    "; (c) NON e' accompagnato da una dichiarazione onesta di stima -- ne' il "
    "nodo ha provenienza.stato (o provenienza testuale tipo 'C_stima_ai') che "
    "dichiara la stima, ne' la voce del composto ha uno 'stato' onesto in " +
    "{" + ", ".join(sorted(STATI_ONESTI)) + "}. "
    "Conservativo: un nodo privo del tutto del campo 'fonte' NON e' fabbricato "
    "(conta come 'senza_fonte'). 'con_stato_onesto' e' ortogonale: conta i nodi "
    "che portano almeno uno 'stato' onesto (top-level, provenienza, "
    "proprieta_meta o composti_aromatici)."
)


def _s(x):
    """Stringa normalizzata (minuscola, trim) o '' se non e' una stringa."""
    return x.strip().lower() if isinstance(x, str) else ""


def _fonte_reale(testo):
    """True se la stringa 'fonte' cita una fonte reale nota (non fabbricata)."""
    t = testo.lower()
    return any(tok in t for tok in TOKEN_FONTE_REALE)


def _stato_dichiara_stima(stato_norm):
    """True se uno 'stato' / 'provenienza' dichiara onestamente una stima o
    un'origine AI. Gestisce sia l'enum onesto sia le stringhe libere tipo
    'c_ai' / 'c_stima_ai' usate altrove nel codice."""
    if not stato_norm:
        return False
    if stato_norm in STATI_ONESTI:
        return True
    return ("stima" in stato_norm) or stato_norm.endswith("_ai")


def _prov_stato(dd):
    """stato di provenienza del nodo (provenienza puo' essere dict {stato:..}
    oppure una stringa tipo 'C_stima_ai')."""
    prov = dd.get("provenienza")
    if isinstance(prov, dict):
        return _s(prov.get("stato"))
    if isinstance(prov, str):
        return _s(prov)
    return ""


def _stati_nodo(dd):
    """Raccoglie TUTTI gli 'stato' presenti nel nodo (per con_stato_onesto):
    top-level, provenienza, proprieta_meta[*], composti_aromatici[*]."""
    stati = set()
    s = _s(dd.get("stato"))
    if s:
        stati.add(s)
    ps = _prov_stato(dd)
    if ps:
        stati.add(ps)
    meta = dd.get("proprieta_meta")
    if isinstance(meta, dict):
        for v in meta.values():
            if isinstance(v, dict):
                vs = _s(v.get("stato"))
                if vs:
                    stati.add(vs)
    comp = dd.get("composti_aromatici")
    if isinstance(comp, list):
        for c in comp:
            if isinstance(c, dict):
                cs = _s(c.get("stato"))
                if cs:
                    stati.add(cs)
    return stati


def classifica_fabbricata(dd):
    """Ritorna (fabbricata: bool, fonte_sospetta: str|None).
    Conservativo e tollerante: data mancante/strano NON e' fabbricato."""
    if not isinstance(dd, dict):
        return False, None
    disclosed_nodo = _stato_dichiara_stima(_prov_stato(dd))
    sospette = []
    # 1) fonte di primo livello
    ft = dd.get("fonte")
    if isinstance(ft, str) and ft.strip():
        if not _fonte_reale(ft) and not disclosed_nodo:
            sospette.append(ft.strip())
    # 2) fonte dentro ogni composto aromatico (col suo eventuale stato)
    comp = dd.get("composti_aromatici")
    if isinstance(comp, list):
        for c in comp:
            if not isinstance(c, dict):
                continue
            cf = c.get("fonte")
            if not (isinstance(cf, str) and cf.strip()):
                continue
            disclosed = disclosed_nodo or _stato_dichiara_stima(_s(c.get("stato")))
            if not _fonte_reale(cf) and not disclosed:
                sospette.append(cf.strip())
    if sospette:
        return True, sospette[0]
    return False, None


def _ha_fonte(dd):
    """True se il nodo ha un qualunque campo 'fonte' (non vuoto), fabbricato o no."""
    if not isinstance(dd, dict):
        return False
    ft = dd.get("fonte")
    if isinstance(ft, str) and ft.strip():
        return True
    comp = dd.get("composti_aromatici")
    if isinstance(comp, list):
        for c in comp:
            if isinstance(c, dict) and isinstance(c.get("fonte"), str) and c.get("fonte").strip():
                return True
    return False


def audita_righe(righe):
    """Funzione PURA: dato un iterabile di (id, type, data) ritorna il report.
    Isolata dal DB cosi' e' testabile offline senza connessione."""
    tot = 0
    n_fabbricati = 0
    n_stato_onesto = 0
    n_senza_fonte = 0
    per_tipo = {}
    campione = []

    for nid, ntype, data in righe:
        tot += 1
        dd = _dati(data)
        tkey = ntype if ntype else "(senza_type)"
        t = per_tipo.setdefault(tkey, {"totali": 0, "con_fonte_ai_fabbricata": 0, "con_stato_onesto": 0})
        t["totali"] += 1

        fabbricata, fonte_sospetta = classifica_fabbricata(dd)
        if fabbricata:
            n_fabbricati += 1
            t["con_fonte_ai_fabbricata"] += 1
            if len(campione) < 25:
                campione.append({"id": nid, "type": ntype, "fonte_sospetta": fonte_sospetta})
        elif not _ha_fonte(dd):
            n_senza_fonte += 1

        if _stati_nodo(dd) & STATI_ONESTI:
            n_stato_onesto += 1
            t["con_stato_onesto"] += 1

    return {
        "ok": True,
        "nodi_totali": tot,
        "con_fonte_ai_fabbricata": n_fabbricati,
        "con_stato_onesto": n_stato_onesto,
        "senza_fonte": n_senza_fonte,
        "ripartizione_per_tipo": per_tipo,
        "campione": campione,
        "criterio": CRITERIO,
        "nota": "Audit read-only: nessuna scrittura al DB. Solo conteggio del debito legacy.",
    }


@bp_audit_prov.route("/admin/audit-provenienza")
def audit_provenienza():
    """READ-ONLY. ?s=ADMIN_SECRET. Conta i nodi con provenienza fabbricata dall'AI.
    Solo SELECT id, type, data FROM nodes — zero scritture."""
    atteso = os.environ.get("ADMIN_SECRET") or ""
    secret = request.args.get("s", "")
    if not atteso or not hmac.compare_digest(str(secret), str(atteso)):
        return jsonify({"errore": "non autorizzato"}), 403

    try:
        with connessione() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, type, data FROM nodes")
            righe = cur.fetchall()
            cur.close()
    except Exception as e:
        return jsonify({"errore": str(e)[:200]}), 500

    return jsonify(audita_righe(righe))
