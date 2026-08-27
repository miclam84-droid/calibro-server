"""Le cose dell'utente: ricette salvate, per device_id. Chiude il buco 'salvo ma sparisce'."""
import json
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn

bp_mie = Blueprint("mie_cose", __name__)

def _ensure_tabella():
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ricette_salvate (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                ricetta_id TEXT NOT NULL,
                nome TEXT,
                dati JSONB,
                creato_il TIMESTAMP DEFAULT NOW(),
                UNIQUE(device_id, ricetta_id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ricette_salvate_device ON ricette_salvate(device_id)")
        conn.commit()
    finally:
        _release_conn(conn)

def _device():
    # header per primo (usato da tutti), poi body json, poi query param
    dev = request.headers.get("X-Device-Id")
    if dev:
        return dev
    if request.is_json:
        dev = (request.json or {}).get("device_id")
        if dev:
            return dev
    return request.args.get("device_id") or ""

@bp_mie.route("/v1/ricette/salva", methods=["POST"])
def salva_ricetta_utente():
    """Salva una ricetta tra 'le mie'. Body: {ricetta_id?, nome, dati:{...}}.
    Traccia chi (device_id) ha salvato cosa, così la ritrova nel Quaderno."""
    _ensure_tabella()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device_id mancante"}), 400
    body = request.json or {}
    dati = body.get("dati") or body  # accetta l'intera ricetta o un campo 'dati'
    nome = body.get("nome") or dati.get("nome") or "Ricetta"
    ric_id = body.get("ricetta_id") or dati.get("id") or ("ric-user-" + str(abs(hash(nome)) % 10**8))
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ricette_salvate (device_id, ricetta_id, nome, dati)
            VALUES (%s,%s,%s,%s::jsonb)
            ON CONFLICT (device_id, ricetta_id) DO UPDATE SET nome=EXCLUDED.nome, dati=EXCLUDED.dati
        """, (dev, ric_id, nome, json.dumps(dati, ensure_ascii=False)))
        conn.commit()
        return jsonify({"ok": True, "ricetta_id": ric_id, "nome": nome})
    finally:
        _release_conn(conn)

@bp_mie.route("/v1/ricette/le-mie", methods=["GET"])
def le_mie_ricette():
    """Restituisce le ricette salvate dall'utente (per device_id). Per la sezione Ricette del Quaderno."""
    _ensure_tabella()
    dev = _device()
    if not dev:
        return jsonify({"ricette": [], "totale": 0})
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT ricetta_id, nome, dati, creato_il FROM ricette_salvate
                       WHERE device_id=%s ORDER BY creato_il DESC""", (dev,))
        rows = cur.fetchall()
        ricette = []
        for r in rows:
            dati = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
            ricette.append({"ricetta_id": r[0], "nome": r[1], "dati": dati,
                            "creato_il": str(r[3]) if r[3] else None})
        return jsonify({"ricette": ricette, "totale": len(ricette)})
    finally:
        _release_conn(conn)

@bp_mie.route("/v1/ricette/rimuovi", methods=["POST"])
def rimuovi_ricetta_utente():
    """Rimuove una ricetta dalle 'mie'. Body: {ricetta_id}."""
    _ensure_tabella()
    dev = _device()
    ric_id = (request.json or {}).get("ricetta_id", "")
    if not dev or not ric_id:
        return jsonify({"errore": "device_id o ricetta_id mancante"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM ricette_salvate WHERE device_id=%s AND ricetta_id=%s", (dev, ric_id))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        _release_conn(conn)
