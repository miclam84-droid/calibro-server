# ============================================================
# MISURA SENSORIALE (ciclo "misurato al banco", revisore IV #56) — vista sul
# Quaderno unico (quaderno_record) con funzione='misura_sensoriale'. NON è una
# tabella nuova: eredita identità, isolamento, backup e ciclo di vita del Quaderno.
# Una misura = un assaggio reale registrato con campione/stato/condizioni/metodo,
# SEMPRE distinto dal dato derivato dalla composizione. Un assaggio NON è verità
# universale: si salvano le misure singole e si legge l'aggregato (mediana + IQR +
# dispersione + n + valutatori distinti + livello di maturità).
# NON scrive sul grafo di produzione: scrive solo nei dati dell'utente.
#
# Livelli di maturità (revisore, soglia operativa N=5):
#   L1 osservazione iniziale  (1–4 assaggi)  — NON sostituisce il derivato
#   L2 riscontro ripetuto     (5–9 assaggi)  — può diventare riferimento condiviso
#                                               SOLO con ≥3 valutatori distinti
#   L3 profilo consolidato    (10+ assaggi)  — più robusto
# "5 ripetizioni della stessa persona" ≠ "5 valutatori": il riferimento condiviso
# richiede valutatori distinti, non solo ripetizioni.
# ============================================================
import json
import uuid

from flask import Blueprint, request, jsonify

from routes.quaderno_unico import _chiave, _conn, _chiudi, _init

bp_misura = Blueprint("misura_sensoriale", __name__)

FUNZIONE = "misura_sensoriale"
PORTA = "laboratorio"

ASSI = {"dolce", "salato", "acido", "amaro", "umami", "grasso", "corposita",
        "croccante", "astringente", "piccante", "termico", "aroma_fresco",
        "aroma_caldo", "effervescenza", "fermentato", "alcolico"}

METODI = {"diretto", "triangolo", "panel"}   # test gustativo diretto · triangolare · panel

# Stato dell'ingrediente nel momento dell'assaggio (la SCALE-SENSORIALI insiste:
# un pomodoro crudo e una salsa cotta non hanno lo stesso profilo). Campo aperto,
# ma normalizziamo i casi frequenti per poter raggruppare gli assaggi confrontabili.
STATI = {"crudo", "cotto", "diluito", "trasformato", "fresco", "stagionato", "essiccato"}

# Soglie di maturità.
SOGLIA_RIFERIMENTO = 5      # N operativo per L2
SOGLIA_VALUTATORI = 3       # valutatori distinti per "riferimento condiviso"
SOGLIA_CONSOLIDATO = 10     # N per L3
SOGLIA_DISCORDANZA = 2.0    # IQR oltre il quale segnaliamo alta variabilità (scala 0–10)

# ---------------------------------------------------------------------------
# ANCORE DELLA SCALA 0–10 (fonte: claude/SCALE-SENSORIALI-DEFINIZIONE.md).
# Servono a dare lo STESSO significato a un voto tra persone e campioni diversi:
# senza ancore, numeri coerenti nella forma ma non confrontabili nel significato.
# Solo i 6 assi-gusto hanno ancore documentate; gli altri restano "da tarare al
# banco" — non si inventano ancore che non esistono.
# ---------------------------------------------------------------------------
ANCORE = {
    "acido": {
        "cosa": "quanto l'ingrediente è percepito aspro/acidulo",
        "riferimento": "pH e/o acidità titolabile — non coincidono con l'acidità percepita "
                       "(uno zuccherato sembra meno acido anche a pH basso)",
        "ancore": [(0, "acqua/olio"), (3, "pomodoro maturo"), (6, "yogurt"),
                   (8, "limone"), (10, "aceto / acido citrico puro")],
    },
    "dolce": {
        "cosa": "percezione di dolcezza",
        "riferimento": "contenuto di zuccheri (°Brix dove misurabile); la matrice conta "
                       "(grasso e acido cambiano quanto senti il dolce)",
        "ancore": [(0, "sale/limone"), (2, "carota cruda"), (4, "mela"),
                   (6, "uva matura/datterino"), (8, "miele"), (10, "zucchero/sciroppo")],
    },
    "salato": {
        "cosa": "percezione di sapidità da sale",
        "riferimento": "sodio mg/100g (etichetta/USDA); la percezione è modulata da acido e dolce",
        "ancore": [(0, "acqua dolce/frutta"), (3, "burro salato"), (5, "pane"),
                   (7, "prosciutto crudo"), (9, "acciughe/colatura"), (10, "sale")],
    },
    "amaro": {
        "cosa": "percezione di amaro",
        "riferimento": "quasi sempre SOLO percettivo; casi noti sì (iso-alfa-acidi/IBU nella birra, "
                       "caffeina/polifenoli nel caffè). Quando è solo sensoriale, va dichiarato",
        "ancore": [(0, "zucchero"), (2, "mandorla dolce"), (4, "cacao fondente"),
                   (6, "radicchio/friarielli"), (8, "caffè espresso"), (10, "china/genziana/Campari")],
    },
    "umami": {
        "cosa": "sapidità \"saporita\" (brodo, maturo, fondo)",
        "riferimento": "glutammato libero + nucleotidi (inosinato carne/pesce, guanilato funghi) "
                       "e la loro sinergia (il rapporto moltiplica la percezione)",
        "ancore": [(0, "zucchero/olio"), (2, "latte"), (4, "pomodoro maturo"),
                   (6, "funghi secchi"), (8, "parmigiano"), (10, "colatura di alici / dashi concentrato")],
    },
    "grasso": {
        "cosa": "grassezza/untuosità percepita (come riveste la bocca)",
        "riferimento": "% lipidi come riferimento quando c'è; da non confondere con l'untuosità percepita",
        "ancore": [(0, "acqua/verdura cruda"), (2, "latte intero"), (4, "mozzarella"),
                   (6, "avocado"), (8, "burro"), (10, "strutto/olio")],
    },
}


def _norm(s):
    return (s or "").strip().lower()


def _mediana(valori):
    v = sorted(valori)
    n = len(v)
    if not n:
        return None
    m = n // 2
    return v[m] if n % 2 else round((v[m - 1] + v[m]) / 2.0, 2)


def _quartile(valori_ordinati, q):
    """Quartile per interpolazione lineare (metodo semplice). q in (0,1)."""
    v = valori_ordinati
    n = len(v)
    if n == 0:
        return None
    if n == 1:
        return v[0]
    pos = q * (n - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < n:
        return round(v[lo] + frac * (v[lo + 1] - v[lo]), 2)
    return round(v[lo], 2)


def _livello(n, valutatori):
    """Livello di maturità + se può fare da riferimento condiviso. Onesto: il
    riferimento condiviso richiede valutatori distinti, non sole ripetizioni."""
    if n >= SOGLIA_CONSOLIDATO:
        liv, etich = "L3", "profilo consolidato"
    elif n >= SOGLIA_RIFERIMENTO:
        liv, etich = "L2", "riscontro ripetuto"
    else:
        liv, etich = "L1", "osservazione iniziale"
    riferimento = (n >= SOGLIA_RIFERIMENTO and valutatori >= SOGLIA_VALUTATORI)
    return liv, etich, riferimento


@bp_misura.route("/v1/scala-sensoriale", methods=["GET"])
@bp_misura.route("/v1/scala-sensoriale/<asse>", methods=["GET"])
def scala_sensoriale(asse=None):
    """Ancore 0–10 per asse (cosa misura, riferimento oggettivo, punti della scala).
    Dati di riferimento, non dati utente: nessuna identità richiesta. Servono a dare
    lo STESSO significato a un voto tra persone e campioni diversi."""
    if asse:
        a = _norm(asse)
        if a not in ANCORE:
            return jsonify({"asse": asse, "ancore": None, "assi_con_ancore": sorted(ANCORE.keys()),
                            "nota": "Ancore non ancora definite per questo asse — si tarano al banco."}), 200
        d = ANCORE[a]
        return jsonify({"asse": a, "cosa": d["cosa"], "riferimento": d["riferimento"],
                        "scala": "0–10", "ancore": [{"v": v, "nota": t} for v, t in d["ancore"]]})
    tutte = {a: {"cosa": d["cosa"], "riferimento": d["riferimento"], "scala": "0–10",
                 "ancore": [{"v": v, "nota": t} for v, t in d["ancore"]]}
             for a, d in ANCORE.items()}
    return jsonify({"scale": tutte, "assi_con_ancore": sorted(ANCORE.keys()),
                    "nota": "Ancoraggio 0–10 per asse. Solo gli assi-gusto documentati hanno ancore; "
                            "gli altri si tarano al banco. Fonte: SCALE-SENSORIALI-DEFINIZIONE."})


@bp_misura.route("/v1/misura-sensoriale", methods=["POST"])
def misura_salva():
    """Registra un ASSAGGIO REALE di un asse per un ingrediente/preparazione.
    Body: {ingrediente, asse, valore, scala?, campione?, stato?, condizioni?, metodo?, valutatore?}.
    Il valore è sulla scala dell'asse (0–10; termico −10..+10). Nessun dato inventato:
    servono ingrediente, asse valido e valore numerico. Lo stato (crudo/cotto/…) e il
    valutatore restano con la misura: due campioni in stati diversi non si confondono."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante (serve X-Device-Id o X-Token)"}), 401
    d = request.get_json(force=True, silent=True) or {}
    ing = (d.get("ingrediente") or "").strip()
    asse = _norm(d.get("asse"))
    if not ing:
        return jsonify({"errore": "ingrediente mancante"}), 400
    if asse not in ASSI:
        return jsonify({"errore": "asse non valido", "assi": sorted(ASSI)}), 400
    try:
        valore = float(str(d.get("valore")).replace(",", "."))
    except (TypeError, ValueError):
        return jsonify({"errore": "valore non numerico"}), 400
    lo, hi = (-10.0, 10.0) if asse == "termico" else (0.0, 10.0)
    if not (lo <= valore <= hi):
        return jsonify({"errore": f"valore fuori scala ({lo}..{hi})"}), 400
    metodo = _norm(d.get("metodo")) or "diretto"
    if metodo not in METODI:
        metodo = "diretto"
    campione = (d.get("campione") or "").strip() or None
    condizioni = (d.get("condizioni") or "").strip() or None
    # stato: normalizzato se riconosciuto, altrimenti tenuto come testo libero (minuscolo)
    stato_raw = _norm(d.get("stato"))
    stato = stato_raw if stato_raw else None
    # valutatore: etichetta libera (dati dell'utente nel suo Quaderno). Serve a distinguere
    # "più ripetizioni della stessa persona" da "più valutatori". Vuoto = identità corrente.
    valutatore = (d.get("valutatore") or "").strip() or None
    scala = (d.get("scala") or ("−10..+10" if asse == "termico" else "0–10"))

    stato_input = {"ingrediente": ing, "asse": asse, "valore": round(valore, 2),
                   "scala": scala, "campione": campione, "stato": stato,
                   "condizioni": condizioni, "metodo": metodo, "valutatore": valutatore}
    provenienza = {"stato": "misurato", "metodo": metodo, "campione": campione,
                   "stato_ingrediente": stato, "valutatore": valutatore,
                   "nota": "assaggio reale al banco — non derivato dalla composizione"}
    rid = "qr-" + uuid.uuid4().hex[:24]
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""INSERT INTO quaderno_record
            (id, chiave_tipo, chiave, porta, funzione, tipo, titolo, lingua,
             stato_input, stato_output, provenienza)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (rid, tipo_id, str(chiave), PORTA, FUNZIONE, "misura",
             f"Misura: {ing} · {asse}", "it",
             json.dumps(stato_input, ensure_ascii=False),
             json.dumps({"valore": round(valore, 2), "asse": asse}, ensure_ascii=False),
             json.dumps(provenienza, ensure_ascii=False)))
        conn.commit(); cur.close()
        return jsonify({"ok": True, "id": rid, "ingrediente": ing, "asse": asse,
                        "valore": round(valore, 2), "stato": "misurato"})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


@bp_misura.route("/v1/misure-sensoriali/<ingrediente>", methods=["GET"])
def misure_lista(ingrediente):
    """Le misure al banco dell'identità corrente per un ingrediente, AGGREGATE per asse:
    n assaggi, valutatori distinti, mediana, IQR (q1–q3), min–max, livello di maturità,
    metodi, stati, ultima data. Un assaggio solo è "osservazione iniziale" e NON sostituisce
    il derivato; la dispersione resta sempre visibile. Sola lettura, solo i propri dati."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    ing = _norm(ingrediente)
    conn = None; pooled = False
    per_asse = {}
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""SELECT stato_input, modificato_at FROM quaderno_record
                       WHERE chiave_tipo=%s AND chiave=%s AND funzione=%s AND archiviato=FALSE
                       ORDER BY modificato_at DESC""", (tipo_id, str(chiave), FUNZIONE))
        for stato_input, mod in cur.fetchall():
            si = stato_input if isinstance(stato_input, dict) else (json.loads(stato_input) if stato_input else {})
            if _norm(si.get("ingrediente")) != ing:
                continue
            asse = _norm(si.get("asse"))
            try:
                val = float(si.get("valore"))
            except (TypeError, ValueError):
                continue
            a = per_asse.setdefault(asse, {"valori": [], "ultima": None,
                                           "metodi": set(), "stati": set(), "valutatori": set()})
            a["valori"].append(val)
            if si.get("metodo"):
                a["metodi"].add(si.get("metodo"))
            if si.get("stato"):
                a["stati"].add(si.get("stato"))
            if si.get("valutatore"):
                a["valutatori"].add(_norm(si.get("valutatore")))
            if a["ultima"] is None and mod:
                a["ultima"] = mod.isoformat()
        cur.close()
    except Exception as e:
        return jsonify({"errore": str(e)[:160], "ingrediente": ingrediente, "misure": {}}), 500
    finally:
        if conn: _chiudi(conn, pooled)

    out = {}
    for asse, a in per_asse.items():
        vals = sorted(a["valori"])
        n = len(vals)
        # valutatori distinti: etichette esplicite; se nessuna, assumiamo 1 (l'identità corrente)
        n_valutatori = len(a["valutatori"]) or 1
        q1 = _quartile(vals, 0.25)
        q3 = _quartile(vals, 0.75)
        iqr = round(q3 - q1, 2) if (q1 is not None and q3 is not None) else None
        liv, etich, riferimento = _livello(n, n_valutatori)
        discordanza = bool(n >= 3 and iqr is not None and iqr >= SOGLIA_DISCORDANZA)
        out[asse] = {
            "n": n, "n_valutatori": n_valutatori,
            "mediana": _mediana(vals), "min": vals[0], "max": vals[-1],
            "q1": q1, "q3": q3, "iqr": iqr,
            "ultima": a["ultima"], "metodi": sorted(a["metodi"]),
            "stati": sorted(a["stati"]),
            "livello": liv, "livello_etichetta": etich,
            "riferimento_condiviso": riferimento,
            "discordanza": discordanza,
            "da_confermare": n < SOGLIA_RIFERIMENTO,
        }
    return jsonify({
        "ingrediente": ingrediente, "misure": out, "n_assi": len(out),
        "soglie": {"riferimento": SOGLIA_RIFERIMENTO, "valutatori": SOGLIA_VALUTATORI,
                   "consolidato": SOGLIA_CONSOLIDATO},
        "nota": "Misure al banco (assaggi reali), aggregate per asse, con livello di maturità e "
                "dispersione. Un assaggio non è verità universale: distinte dai valori derivati "
                "dalla composizione, e dichiarate al loro grado di robustezza.",
    })
