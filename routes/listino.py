# ============================================================
# LISTINO PREZZI PERSONALE (Blocco 1a) — i prezzi del fornitore dell'utente.
# NON è una tabella nuova: è una vista sul Quaderno unico (quaderno_record) con
# funzione='prezzo'. Così il listino eredita identità, isolamento, backup e ciclo
# di vita già verificati del Quaderno, e ogni aggiornamento resta un record DATATO
# (storico naturale del prezzo + provenienza), come chiede il revisore.
# Un prezzo = un record: {ingrediente, prezzo_kg, unita, fornitore}. Per il food
# cost conta il più recente per ingrediente.
# ============================================================
import json
import uuid

from flask import Blueprint, request, jsonify

from routes.quaderno_unico import _chiave, _conn, _chiudi, _init

bp_listino = Blueprint("listino", __name__)

FUNZIONE = "prezzo"
PORTA = "quaderno"


def _norm(nome):
    return (nome or "").strip().lower()


def carica_prezzi_utente(tipo_id, chiave):
    """{ingrediente_norm: {prezzo_kg, fornitore, data, id}} — il PIÙ RECENTE per ingrediente.
    Usata sia dall'endpoint listino sia dal food cost del Planner. Nessuna identità -> {}."""
    if not tipo_id:
        return {}
    conn = None; pooled = False
    out = {}
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""SELECT id, titolo, stato_input, modificato_at
                       FROM quaderno_record
                       WHERE chiave_tipo=%s AND chiave=%s AND funzione=%s AND archiviato=FALSE
                       ORDER BY modificato_at DESC""", (tipo_id, str(chiave), FUNZIONE))
        for rid, titolo, stato_input, mod in cur.fetchall():
            si = stato_input if isinstance(stato_input, dict) else (json.loads(stato_input) if stato_input else {})
            ing = _norm(si.get("ingrediente"))
            if not ing or ing in out:   # già visto = più recente, lo tengo
                continue
            try:
                pk = float(si.get("prezzo_kg"))
            except (TypeError, ValueError):
                continue
            if pk <= 0:
                continue
            out[ing] = {"prezzo_kg": pk, "fornitore": si.get("fornitore") or None,
                        "data": mod.isoformat() if mod else None, "id": rid}
        cur.close()
    except Exception:
        pass
    finally:
        if conn: _chiudi(conn, pooled)
    return out


@bp_listino.route("/v1/listino", methods=["GET"])
def listino_lista():
    """Il listino prezzi dell'identità corrente: un prezzo per ingrediente (il più recente)."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    prezzi = carica_prezzi_utente(tipo_id, chiave)
    voci = [{"ingrediente": k, "prezzo_kg": v["prezzo_kg"], "fornitore": v["fornitore"],
             "data": v["data"], "id": v["id"]} for k, v in prezzi.items()]
    voci.sort(key=lambda x: x["ingrediente"])
    return jsonify({"n": len(voci), "voci": voci})


@bp_listino.route("/v1/listino", methods=["POST"])
def listino_salva():
    """Salva/aggiorna il prezzo di un ingrediente. Ogni salvataggio è un record datato
    (lo storico resta); il food cost usa il più recente. Body: {ingrediente, prezzo_kg, fornitore?}."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante (serve X-Device-Id)"}), 401
    d = request.get_json(force=True, silent=True) or {}
    ing = (d.get("ingrediente") or "").strip()
    if not ing:
        return jsonify({"errore": "ingrediente mancante"}), 400
    try:
        pk = float(str(d.get("prezzo_kg")).replace(",", "."))
    except (TypeError, ValueError):
        return jsonify({"errore": "prezzo_kg non valido"}), 400
    if pk <= 0:
        return jsonify({"errore": "prezzo_kg deve essere positivo"}), 400
    fornitore = (d.get("fornitore") or "").strip() or None
    stato_input = {"ingrediente": ing, "prezzo_kg": round(pk, 4), "unita": "€/kg", "fornitore": fornitore}
    rid = "qr-" + uuid.uuid4().hex[:24]
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""INSERT INTO quaderno_record
            (id, chiave_tipo, chiave, porta, funzione, tipo, titolo, lingua,
             stato_input, stato_output, provenienza)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (rid, tipo_id, str(chiave), PORTA, FUNZIONE, "prezzo",
             "Prezzo: " + ing, "it",
             json.dumps(stato_input, ensure_ascii=False),
             json.dumps({"prezzo_kg": round(pk, 4)}, ensure_ascii=False),
             json.dumps({"origine": "listino-utente"}, ensure_ascii=False)))
        conn.commit(); cur.close()
        return jsonify({"ok": True, "id": rid, "ingrediente": ing, "prezzo_kg": round(pk, 4)})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


@bp_listino.route("/v1/listino/<rid>/elimina", methods=["POST"])
def listino_elimina(rid):
    """Archivia (non cancella) un prezzo: esce dal listino ma lo storico resta recuperabile."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""UPDATE quaderno_record SET archiviato=TRUE, modificato_at=NOW()
                       WHERE id=%s AND chiave_tipo=%s AND chiave=%s AND funzione=%s""",
                    (rid, tipo_id, str(chiave), FUNZIONE))
        n = cur.rowcount
        conn.commit(); cur.close()
        if n == 0:
            return jsonify({"ok": False, "nota": "prezzo non trovato per questa identita'"}), 404
        return jsonify({"ok": True})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)
