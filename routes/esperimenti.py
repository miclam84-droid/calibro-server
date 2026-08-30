"""Esperimenti pratici 'provalo stasera' collegati al Quaderno.
- GET /v1/esperimento/<fenomeno_id> → l'esperimento pratico del fenomeno.
- POST /v1/esperimento/completa → marca completato + salva nel Quaderno (così la chat lo usa).
Consolidamento (OpenAI punto 5): ogni esperimento completato alimenta il Notebook."""
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from config import DATABASE_URL
import json

bp_exp = Blueprint("esperimenti", __name__)


def _assicura(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS esperimenti_completati (
        id SERIAL PRIMARY KEY,
        device_id TEXT NOT NULL,
        fenomeno_id TEXT NOT NULL,
        esito TEXT,
        nota TEXT,
        completato_il TIMESTAMP DEFAULT NOW()
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exp_dev ON esperimenti_completati(device_id)")


@bp_exp.route("/v1/esperimento/<fenomeno_id>", methods=["GET"])
def get_esperimento(fenomeno_id):
    """Restituisce l'esperimento pratico di un fenomeno (dalla tabella esperimenti_pratici)."""
    if not DATABASE_URL:
        return jsonify({"esperimento": None})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT testo, disciplina, quantitativo FROM esperimenti_pratici WHERE fenomeno_id=%s",
                    (fenomeno_id,))
        r = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not r:
            return jsonify({"esperimento": None, "nota": "nessun esperimento per questo fenomeno"})
        return jsonify({"esperimento": r[0], "disciplina": r[1], "quantitativo": r[2],
                        "fenomeno_id": fenomeno_id})
    except Exception as e:
        _release_conn(conn)
        return jsonify({"esperimento": None, "errore": str(e)[:100]}), 200


@bp_exp.route("/v1/esperimento/completa", methods=["POST"])
def completa_esperimento():
    """Marca un esperimento come completato e lo salva nel Quaderno.
    Body: {fenomeno_id, esito?, nota?}. device_id da header X-Device-Id."""
    if not DATABASE_URL:
        return jsonify({"errore": "db non disponibile"}), 200
    body = request.json or {}
    fenomeno_id = (body.get("fenomeno_id") or "").strip()
    device_id = (request.headers.get("X-Device-Id", "") or body.get("device_id", "") or "").strip()[:80]
    esito = (body.get("esito") or "").strip()[:200]
    nota = (body.get("nota") or "").strip()[:500]
    if not fenomeno_id:
        return jsonify({"errore": "fenomeno_id mancante"}), 400
    if not device_id:
        return jsonify({"errore": "device_id mancante"}), 400
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _assicura(cur)
        cur.execute("INSERT INTO esperimenti_completati (device_id, fenomeno_id, esito, nota) "
                    "VALUES (%s,%s,%s,%s)", (device_id, fenomeno_id, esito, nota))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "messaggio": "Esperimento salvato nel Quaderno"})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"errore": str(e)[:100]}), 200


@bp_exp.route("/v1/esperimento/miei", methods=["GET"])
def miei_esperimenti():
    """Gli esperimenti completati dall'utente (per il Quaderno). device_id da header."""
    if not DATABASE_URL:
        return jsonify({"esperimenti": []})
    device_id = (request.headers.get("X-Device-Id", "") or request.args.get("device_id", "") or "").strip()[:80]
    if not device_id:
        return jsonify({"esperimenti": []})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _assicura(cur)
        cur.execute("""SELECT ec.fenomeno_id, ec.esito, ec.nota, ec.completato_il, n.name
                       FROM esperimenti_completati ec LEFT JOIN nodes n ON n.id=ec.fenomeno_id
                       WHERE ec.device_id=%s ORDER BY ec.completato_il DESC LIMIT 30""", (device_id,))
        righe = cur.fetchall()
        cur.close(); _release_conn(conn)
        return jsonify({"esperimenti": [
            {"fenomeno_id": r[0], "esito": r[1], "nota": r[2],
             "data": r[3].isoformat() if r[3] else None, "fenomeno": r[4]}
            for r in righe]})
    except Exception as e:
        _release_conn(conn)
        return jsonify({"esperimenti": [], "errore": str(e)[:100]}), 200
