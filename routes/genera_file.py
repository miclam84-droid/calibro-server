# routes/genera_file.py — endpoint che genera e serve PDF/Excel/Word da contenuto strutturato.
# Fondazione della capability "la chat ti sforna il file". Il cablaggio nella chat (tool-calling)
# arriva in un secondo passo: qui c'e' il motore, testabile da solo.

import re, io, uuid
import psycopg2
from flask import Blueprint, request, send_file, jsonify
import generatore_file as GF
from db import _get_conn, _release_conn

bp_genera_file = Blueprint("genera_file", __name__)


def _slug(s):
    s = re.sub(r"[^\w\s-]", "", (s or "documento").lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return (s or "documento")[:60]


# ─────────────── deposito temporaneo dei file (per la chat) ───────────────
# La chat genera il file al volo: lo salviamo come byte in Postgres con un id
# breve, lo serviamo una volta su GET /v1/file/<id> e potiamo i vecchi (>24h).
_TABELLA_PRONTA = False


def _assicura_tabella():
    global _TABELLA_PRONTA
    if _TABELLA_PRONTA:
        return
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS file_temporanei (
            id TEXT PRIMARY KEY,
            nome TEXT,
            mime TEXT,
            dati BYTEA,
            creato_il TIMESTAMPTZ DEFAULT now()
        )""")
        conn.commit()
        _TABELLA_PRONTA = True
    finally:
        cur.close(); _release_conn(conn)


def salva_file_temporaneo(nome, mime, dati):
    """Salva i byte del file e torna un id. Prima pota i file piu' vecchi di 24h."""
    _assicura_tabella()
    fid = uuid.uuid4().hex
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM file_temporanei WHERE creato_il < now() - interval '24 hours'")
        cur.execute("INSERT INTO file_temporanei (id, nome, mime, dati) VALUES (%s,%s,%s,%s)",
                    (fid, (nome or "documento")[:160], mime, psycopg2.Binary(dati)))
        conn.commit()
    finally:
        cur.close(); _release_conn(conn)
    return fid


@bp_genera_file.route("/v1/file/<fid>", methods=["GET"])
def scarica_file_temporaneo(fid):
    """Serve un file generato dalla chat (deposito temporaneo)."""
    if not re.fullmatch(r"[0-9a-f]{32}", fid or ""):
        return jsonify({"errore": "id_non_valido"}), 400
    _assicura_tabella()
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT nome, mime, dati FROM file_temporanei WHERE id=%s", (fid,))
        row = cur.fetchone()
    finally:
        cur.close(); _release_conn(conn)
    if not row:
        return jsonify({"errore": "non_trovato",
                        "messaggio": "File scaduto o inesistente."}), 404
    nome, mime, dati = row
    buf = io.BytesIO(bytes(dati)); buf.seek(0)
    return send_file(buf, mimetype=mime or "application/octet-stream",
                     as_attachment=True, download_name=nome or "documento")


@bp_genera_file.route("/v1/genera-file", methods=["POST"])
def genera_file_endpoint():
    """POST {tipo:'pdf'|'excel'|'word', titolo, contenuto}. Ritorna il file in download.
    contenuto = lista di BLOCCHI (pdf/word) o di FOGLI (excel) — vedi generatore_file.py.
    NB onesta': i numeri (food cost) devono arrivare gia' veri/etichettati dal chiamante;
    questo endpoint impagina soltanto, non calcola e non inventa."""
    payload = request.get_json(force=True, silent=True) or {}
    tipo = (payload.get("tipo") or "pdf")
    titolo = (str(payload.get("titolo") or "Documento"))[:120]
    contenuto = payload.get("contenuto") or []
    if not isinstance(contenuto, list) or not contenuto:
        return jsonify({"errore": "contenuto_mancante",
                        "messaggio": "Serve 'contenuto' (lista di blocchi o fogli) non vuoto."}), 400
    try:
        buf, mime, ext = GF.genera(tipo, titolo, contenuto)
    except Exception as e:
        return jsonify({"errore": "generazione_fallita", "dettaglio": str(e)[:200]}), 500
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=f"{_slug(titolo)}.{ext}")
