# ============================================================
# UMAMI COMPOSIZIONE — la sinergia umami su una COMPOSIZIONE (piatto/pizza).
# Il punto che nessuno rende: l'umami non si somma, si MOLTIPLICA. Il glutammato
# di un ingrediente incontra i nucleotidi (inosinato/guanilato) di un altro e
# l'umami salta (modello EUC di Yamaguchi). Questo endpoint, data una lista di
# ingredienti, legge glu/imp/gmp di ciascuno (dal nodo, o dalla tabella Umami
# Information Center), calcola l'EUC del POOL combinato vs la somma dei singoli,
# e dice se la sinergia e' attiva o se "manca il moltiplicatore".
# ONESTA': tutto DERIVATO, indicativo, NON un assaggio al banco. Sola lettura.
# Niente quantita' (per-100g di ciascuno): e' una lettura DIREZIONALE, non la
# misura esatta del piatto — e lo dichiara.
# ============================================================
import os
import json
import math

from flask import Blueprint, request, jsonify

from routes.deriva_umami import _calc_euc, _UMAMI_LOG, _MATCH, _tabella, FONTE, FONTE_URL
from routes.deriva_gusti import _interp

bp_umami_comp = Blueprint("umami_composizione", __name__)

# soglie (mg/100g) per classificare il ruolo di un ingrediente nella sinergia
_SOGLIA_GLU = 100.0   # sopra: porta glutammato in quantita' utile
_SOGLIA_NUC = 50.0    # sopra (imp + gmp): porta nucleotidi (il moltiplicatore)


def _umami_di_nodo(dd):
    """Dal `data` di un nodo estrae glu/imp/gmp (mg/100g) dell'umami, se presenti.
    Il motore EUC salva `grezzo` come dict ricco; le vecchie pipeline come scalare
    (solo glutammato). Ritorna (glu, imp, gmp, fonte) o None se il nodo non ha umami."""
    meta = (dd.get("proprieta_meta") or {}) if isinstance(dd, dict) else {}
    um = meta.get("umami") if isinstance(meta.get("umami"), dict) else None
    if not um:
        return None
    grezzo = um.get("grezzo")
    fonte = um.get("fonte")
    if isinstance(grezzo, dict):
        glu = grezzo.get("glutammato_mg") or 0.0
        imp = grezzo.get("inosinato_mg") or 0.0
        gmp = grezzo.get("guanilato_mg") or 0.0
    elif grezzo is not None:
        glu, imp, gmp = (grezzo or 0.0), 0.0, 0.0   # vecchia pipeline: solo glutammato
    else:
        return None
    if not fonte:
        return None
    return float(glu), float(imp), float(gmp), fonte


def _umami_da_tabella(nome):
    """Fallback: tabella Umami Information Center via _MATCH (per nodi non ancora
    scritti in produzione). Ritorna (glu, imp, gmp, fonte) o None."""
    chiave = _MATCH.get((nome or "").strip().lower())
    if not chiave:
        return None
    riga = _tabella().get(chiave)
    if not riga or (riga.get("glu") or 0.0) <= 0.0:
        return None
    return float(riga["glu"]), float(riga.get("imp") or 0.0), float(riga.get("gmp") or 0.0), FONTE


def _cerca_umami(nome, cur):
    """Prima il nodo (verita' di produzione), poi la tabella. Ritorna dict componente."""
    trovato_nodo = None
    if cur is not None:
        try:
            cur.execute(
                """SELECT name, data FROM nodes
                   WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                   ORDER BY (id LIKE 'ing-%%') DESC, id LIMIT 1""", (nome,))
            row = cur.fetchone()
            if row:
                dd = row[1] if isinstance(row[1], dict) else (json.loads(row[1]) if row[1] else {})
                trovato_nodo = _umami_di_nodo(dd)
                nome = row[0]  # nome reale del nodo
        except Exception:
            trovato_nodo = None
    dati = trovato_nodo or _umami_da_tabella(nome)
    if not dati:
        return {"nome": nome, "trovato": False, "glu": 0.0, "imp": 0.0, "gmp": 0.0,
                "euc": 0.0, "umami": None, "fonte": None, "ruolo": "senza dato umami"}
    glu, imp, gmp, fonte = dati
    euc = _calc_euc(glu, imp, gmp)
    umami = round(_interp(math.log10(euc), _UMAMI_LOG), 1) if euc > 0 else 0.0
    nuc = imp + gmp
    if glu >= _SOGLIA_GLU and nuc >= _SOGLIA_NUC:
        ruolo = "glutammato + nucleotidi"
    elif glu >= _SOGLIA_GLU:
        ruolo = "glutammato"
    elif nuc >= _SOGLIA_NUC:
        ruolo = "nucleotidi"
    else:
        ruolo = "umami debole"
    return {"nome": nome, "trovato": True,
            "glu": round(glu, 1), "imp": round(imp, 1), "gmp": round(gmp, 1),
            "euc": round(euc, 3), "umami": umami, "fonte": fonte, "ruolo": ruolo,
            "provenienza": "nodo" if trovato_nodo else "tabella"}


def _db_cursor():
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return None, None
    try:
        import psycopg2
        conn = psycopg2.connect(dburl)
        return conn, conn.cursor()
    except Exception:
        return None, None


def componi_umami(ingredienti, cur=None):
    """Nucleo testabile. Ritorna il payload completo della sinergia."""
    comp = [_cerca_umami(n, cur) for n in ingredienti if (n or "").strip()]
    con_dato = [c for c in comp if c["trovato"]]

    tot_glu = sum(c["glu"] for c in con_dato)
    tot_imp = sum(c["imp"] for c in con_dato)
    tot_gmp = sum(c["gmp"] for c in con_dato)

    euc_mix = _calc_euc(tot_glu, tot_imp, tot_gmp)              # pool combinato (sinergia incrociata)
    euc_somma = sum(c["euc"] for c in con_dato)                 # ognuno per se', nessuna sinergia incrociata
    umami_mix = round(_interp(math.log10(euc_mix), _UMAMI_LOG), 1) if euc_mix > 0 else 0.0
    delta = round(euc_mix - euc_somma, 3)

    porta_glu = [c["nome"] for c in con_dato if c["glu"] >= _SOGLIA_GLU]
    porta_nuc = [c["nome"] for c in con_dato if (c["imp"] + c["gmp"]) >= _SOGLIA_NUC]

    # Diagnosi direzionale + guida onesta (suggerimento, non comando)
    if porta_glu and porta_nuc:
        stato = "sinergia_attiva"
        titolo = "Sinergia attiva"
        spiega = ("Il glutammato di " + ", ".join(porta_glu[:3]) +
                  " incontra i nucleotidi di " + ", ".join(porta_nuc[:3]) +
                  ": l'umami si moltiplica, non si somma.")
        guida = None
    elif porta_glu and not porta_nuc:
        stato = "manca_moltiplicatore"
        titolo = "Manca il moltiplicatore"
        spiega = ("C'e' glutammato (" + ", ".join(porta_glu[:3]) +
                  ") ma nessuna fonte di nucleotidi: l'umami resta la somma, non salta.")
        guida = ("Aggiungi una fonte di nucleotidi — shiitake secco, katsuobushi, "
                 "niboshi, o carne/pesce freschi — e l'umami sale. (Acciuga, colatura e "
                 "pomodoro portano glutammato, non il moltiplicatore.)")
    elif porta_nuc and not porta_glu:
        stato = "manca_glutammato"
        titolo = "Manca la base di glutammato"
        spiega = ("Ci sono nucleotidi (" + ", ".join(porta_nuc[:3]) +
                  ") ma poca base di glutammato da moltiplicare.")
        guida = ("Aggiungi una base ricca di glutammato — parmigiano/grana, "
                 "pomodoro maturo, kombu, salsa di soia — per dare corpo alla sinergia.")
    else:
        stato = "umami_basso"
        titolo = "Umami di fondo basso"
        spiega = "Nessun ingrediente porta umami in quantita' utile."
        guida = ("Per costruire umami servono due mattoni: una base di glutammato "
                 "(parmigiano, pomodoro, kombu) e un moltiplicatore di nucleotidi "
                 "(shiitake secco, katsuobushi, niboshi).")

    confidenze = []  # la confidenza del piatto non e' mai sopra il piu' debole
    note = ("Lettura DERIVATA dalla composizione, non un assaggio al banco. "
            "Indicativa della direzione (c'e' sinergia o manca un mattone), non la "
            "misura esatta del piatto: le quantita' reali spostano i numeri. "
            "Fonte dei valori per ingrediente: " + FONTE + ".")

    senza_dato = [c["nome"] for c in comp if not c["trovato"]]

    return {
        "ingredienti": [c["nome"] for c in comp],
        "componenti": comp,
        "totali_mg": {"glutammato": round(tot_glu, 1), "inosinato": round(tot_imp, 1),
                      "guanilato": round(tot_gmp, 1)},
        "euc_mix": round(euc_mix, 3),
        "euc_somma_ingenua": round(euc_somma, 3),
        "umami_composizione": umami_mix,
        "sinergia": {
            "stato": stato,
            "titolo": titolo,
            "spiegazione": spiega,
            "guida": guida,
            "guadagno_euc": delta,                   # quanto la sinergia aggiunge oltre la somma
            "porta_glutammato": porta_glu,
            "porta_nucleotidi": porta_nuc,
        },
        "senza_dato_umami": senza_dato,
        "stato_dato": "derivato",
        "fonte": FONTE, "fonte_url": FONTE_URL,
        "note_onesta": note,
    }


@bp_umami_comp.route("/v1/umami-composizione", methods=["GET", "POST"])
def umami_composizione():
    """Sinergia umami su una composizione.
    GET  ?ingredienti=pomodoro,parmigiano,acciughe
    POST {"ingredienti": ["pomodoro","parmigiano","acciughe"]}"""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        ingredienti = body.get("ingredienti") or []
    else:
        grezzo = request.args.get("ingredienti", "")
        ingredienti = [x.strip() for x in grezzo.split(",") if x.strip()]
    if not ingredienti:
        return jsonify({"errore": "nessun ingrediente",
                        "come": "?ingredienti=pomodoro,parmigiano,acciughe"}), 400
    if len(ingredienti) > 30:
        ingredienti = ingredienti[:30]

    conn, cur = _db_cursor()
    try:
        payload = componi_umami(ingredienti, cur)
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return jsonify(payload)
