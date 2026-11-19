# ============================================================
# MISURA SENSORIALE (ciclo "misurato al banco", revisore IV #56) — vista sul
# Quaderno unico (quaderno_record) con funzione='misura_sensoriale'. NON è una
# tabella nuova: eredita identità, isolamento, backup e ciclo di vita del Quaderno.
# Una misura = un assaggio reale registrato con campione/condizioni/metodo, SEMPRE
# distinto dal dato derivato dalla composizione. Un assaggio non è verità universale:
# si salvano le misure singole e si legge l'aggregato (mediana + n + dispersione).
# NON scrive sul grafo di produzione: scrive solo nei dati dell'utente.
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


def _norm(s):
    return (s or "").strip().lower()


def _mediana(valori):
    v = sorted(valori)
    n = len(v)
    if not n:
        return None
    m = n // 2
    return v[m] if n % 2 else round((v[m - 1] + v[m]) / 2.0, 2)


@bp_misura.route("/v1/misura-sensoriale", methods=["POST"])
def misura_salva():
    """Registra un ASSAGGIO REALE di un asse per un ingrediente/preparazione.
    Body: {ingrediente, asse, valore, scala?, campione?, condizioni?, metodo?}.
    Il valore è sulla scala dell'asse (0–10; termico −10..+10). Nessun dato inventato:
    servono ingrediente, asse valido e valore numerico."""
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
    scala = (d.get("scala") or ("−10..+10" if asse == "termico" else "0–10"))

    stato_input = {"ingrediente": ing, "asse": asse, "valore": round(valore, 2),
                   "scala": scala, "campione": campione, "condizioni": condizioni,
                   "metodo": metodo}
    provenienza = {"stato": "misurato", "metodo": metodo, "campione": campione,
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
    n misure, mediana, min, max, ultima data. Un assaggio solo è "da confermare";
    la dispersione (min..max) resta visibile. Sola lettura, solo i propri dati."""
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
            a = per_asse.setdefault(asse, {"valori": [], "ultima": None, "metodi": set()})
            a["valori"].append(val)
            if si.get("metodo"):
                a["metodi"].add(si.get("metodo"))
            if a["ultima"] is None and mod:
                a["ultima"] = mod.isoformat()
        cur.close()
    except Exception as e:
        return jsonify({"errore": str(e)[:160], "ingrediente": ingrediente, "misure": {}}), 500
    finally:
        if conn: _chiudi(conn, pooled)

    out = {}
    for asse, a in per_asse.items():
        vals = a["valori"]
        out[asse] = {"n": len(vals), "mediana": _mediana(vals),
                     "min": min(vals), "max": max(vals),
                     "ultima": a["ultima"], "metodi": sorted(a["metodi"]),
                     "da_confermare": len(vals) < 2}
    return jsonify({"ingrediente": ingrediente, "misure": out, "n_assi": len(out),
                    "nota": "Misure al banco (assaggi reali), aggregate per asse. "
                            "Distinte dai valori derivati dalla composizione."})
