"""Community 'Vetrina del Banco' — modello a bassa manutenzione:
- feed di sola lettura di ricette rese pubbliche (niente commenti, niente like → zero moderazione)
- solo due azioni: CLONA (copia nel proprio quaderno) e CONNETTI (profilo leggero)
- il contatto avviene FUORI dall'app: il profilo mostra un link esterno (WhatsApp/Telegram/LinkedIn)
  scelto dall'utente. L'app non gestisce chat interna → nessun costo di messaggistica/moderazione.
"""
import json
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn

bp_community = Blueprint("community", __name__)


def _ensure_tabelle():
    conn = _get_conn(); cur = conn.cursor()
    try:
        # ricette pubblicate nel feed
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ricette_pubbliche (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                autore_nome TEXT,
                autore_postazione TEXT,
                ricetta_id TEXT,
                nome TEXT,
                dati JSONB,
                lingua TEXT DEFAULT 'it',
                dal_team BOOLEAN DEFAULT FALSE,
                creato_il TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pub_lingua ON ricette_pubbliche(lingua, creato_il DESC)")
        # profilo leggero dell'utente (solo nome, postazione, contatto esterno)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profili (
                device_id TEXT PRIMARY KEY,
                nome TEXT,
                postazione TEXT,
                contatto_tipo TEXT,          -- 'whatsapp' | 'telegram' | 'linkedin' | 'instagram'
                contatto_valore TEXT,        -- numero o handle
                creato_il TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    finally:
        _release_conn(conn)


def _device():
    dev = request.headers.get("X-Device-Id")
    if dev:
        return dev
    body = request.json if request.is_json else None
    if body and body.get("device_id"):
        return body["device_id"]
    return request.args.get("device_id", "")


def _link_esterno(tipo, valore):
    """Costruisce il link di contatto esterno. L'app non gestisce la chat: rimanda fuori."""
    if not tipo or not valore:
        return None
    v = valore.strip()
    if tipo == "whatsapp":
        num = "".join(c for c in v if c.isdigit())
        return f"https://wa.me/{num}" if num else None
    if tipo == "telegram":
        return f"https://t.me/{v.lstrip('@')}"
    if tipo == "linkedin":
        return v if v.startswith("http") else f"https://www.linkedin.com/in/{v}"
    if tipo == "instagram":
        return f"https://instagram.com/{v.lstrip('@')}"
    return None


@bp_community.route("/v1/community/pubblica", methods=["POST"])
def pubblica_ricetta():
    """Rende pubblica una ricetta nel feed. Body: {ricetta_id, nome, dati, autore_nome, autore_postazione, lingua}"""
    _ensure_tabelle()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device mancante"}), 400
    body = request.json or {}
    nome = (body.get("nome") or "").strip()
    dati = body.get("dati") or {}
    if not nome:
        return jsonify({"errore": "nome ricetta mancante"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ricette_pubbliche (device_id, autore_nome, autore_postazione, ricetta_id, nome, dati, lingua)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (dev, body.get("autore_nome", "Anonimo"), body.get("autore_postazione", ""),
              body.get("ricetta_id", ""), nome, json.dumps(dati, ensure_ascii=False), body.get("lingua", "it")))
        pid = cur.fetchone()[0]
        conn.commit()
        return jsonify({"ok": True, "id": pid, "messaggio": "Ricetta pubblicata nella Vetrina del Banco."})
    finally:
        _release_conn(conn)


@bp_community.route("/v1/community/feed", methods=["GET"])
def feed():
    """Feed di sola lettura delle ricette pubbliche. ?lingua=it&offset=0"""
    _ensure_tabelle()
    lingua = request.args.get("lingua", "it")
    try:
        offset = int(request.args.get("offset", 0))
    except Exception:
        offset = 0
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, autore_nome, autore_postazione, nome, dati, dal_team, creato_il, device_id
            FROM ricette_pubbliche WHERE lingua=%s
            ORDER BY creato_il DESC LIMIT 20 OFFSET %s
        """, (lingua, offset))
        ricette = []
        for r in cur.fetchall():
            d = r[4] if isinstance(r[4], dict) else (json.loads(r[4]) if r[4] else {})
            ricette.append({
                "id": r[0], "autore": r[1], "postazione": r[2], "nome": r[3],
                "dati": d, "dal_team": r[5], "creato_il": str(r[6]),
                "autore_device": r[7],
            })
        return jsonify({"ricette": ricette, "totale": len(ricette)})
    finally:
        _release_conn(conn)


@bp_community.route("/v1/community/profilo", methods=["GET", "POST"])
def profilo():
    """GET ?device_id=... → profilo leggero + link esterno. POST → salva il proprio profilo."""
    _ensure_tabelle()
    conn = _get_conn(); cur = conn.cursor()
    try:
        if request.method == "POST":
            dev = _device()
            if not dev:
                return jsonify({"errore": "device mancante"}), 400
            body = request.json or {}
            cur.execute("""
                INSERT INTO profili (device_id, nome, postazione, contatto_tipo, contatto_valore)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (device_id) DO UPDATE SET
                  nome=EXCLUDED.nome, postazione=EXCLUDED.postazione,
                  contatto_tipo=EXCLUDED.contatto_tipo, contatto_valore=EXCLUDED.contatto_valore
            """, (dev, body.get("nome", ""), body.get("postazione", ""),
                  body.get("contatto_tipo", ""), body.get("contatto_valore", "")))
            conn.commit()
            return jsonify({"ok": True})
        # GET
        dev = request.args.get("device_id", "")
        cur.execute("SELECT nome, postazione, contatto_tipo, contatto_valore FROM profili WHERE device_id=%s", (dev,))
        r = cur.fetchone()
        if not r:
            return jsonify({"trovato": False})
        return jsonify({
            "trovato": True, "nome": r[0], "postazione": r[1],
            "contatto_link": _link_esterno(r[2], r[3]),  # il ponte FUORI dall'app
            "contatto_tipo": r[2],
        })
    finally:
        _release_conn(conn)


@bp_community.route("/v1/community/clona", methods=["POST"])
def clona():
    """Clona una ricetta pubblica nel proprio quaderno. Body: {id_pubblica}"""
    _ensure_tabelle()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device mancante"}), 400
    body = request.json or {}
    id_pub = body.get("id_pubblica")
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT nome, dati, ricetta_id FROM ricette_pubbliche WHERE id=%s", (id_pub,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "ricetta non trovata"}), 404
        # salvo nel quaderno personale (tabella ricette_salvate)
        d = r[1] if isinstance(r[1], dict) else (json.loads(r[1]) if r[1] else {})
        cur.execute("""
            INSERT INTO ricette_salvate (device_id, ricetta_id, nome, dati)
            VALUES (%s,%s,%s,%s) ON CONFLICT (device_id, ricetta_id) DO NOTHING
        """, (dev, f"clone-{id_pub}", r[0], json.dumps(d, ensure_ascii=False)))
        conn.commit()
        return jsonify({"ok": True, "messaggio": "Ricetta clonata nel tuo Quaderno."})
    finally:
        _release_conn(conn)


@bp_community.route("/admin/popola-feed")
def admin_popola_feed():
    """Popola il feed con ricette canoniche 'dal Team di Matter Lab' (per non averlo vuoto al lancio)."""
    import os, hmac
    secret = request.args.get("s", "")
    if not hmac.compare_digest(str(secret), str(os.environ.get("ADMIN_SECRET") or "")):
        return "Forbidden", 403
    _ensure_tabelle()
    conn = _get_conn(); cur = conn.cursor()
    try:
        # pesco alcune ricette canoniche dalla tabella ricette
        cur.execute("SELECT id, nome, disciplina, ingredienti, punto_critico FROM ricette LIMIT 40")
        righe = cur.fetchall()
        n = 0
        for r in righe:
            ing = r[3] if isinstance(r[3], (list, dict)) else (json.loads(r[3]) if r[3] else [])
            dati = {"nome": r[1], "disciplina": r[2], "ingredienti": ing, "punto_critico": r[4]}
            # evito doppioni: pubblico solo se non già presente dal team
            cur.execute("SELECT 1 FROM ricette_pubbliche WHERE nome=%s AND dal_team=TRUE LIMIT 1", (r[1],))
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO ricette_pubbliche (device_id, autore_nome, autore_postazione, ricetta_id, nome, dati, lingua, dal_team)
                VALUES ('team','Team Matter Lab',%s,%s,%s,%s,'it',TRUE)
            """, (r[2] or "", r[0], r[1], json.dumps(dati, ensure_ascii=False)))
            n += 1
        conn.commit()
        return jsonify({"ok": True, "pubblicate": n})
    finally:
        _release_conn(conn)
