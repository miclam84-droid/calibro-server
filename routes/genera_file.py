# routes/genera_file.py — endpoint che genera e serve PDF/Excel/Word da contenuto strutturato.
# Fondazione della capability "la chat ti sforna il file". Il cablaggio nella chat (tool-calling)
# arriva in un secondo passo: qui c'e' il motore, testabile da solo.

import re
from flask import Blueprint, request, send_file, jsonify
import generatore_file as GF

bp_genera_file = Blueprint("genera_file", __name__)


def _slug(s):
    s = re.sub(r"[^\w\s-]", "", (s or "documento").lower()).strip()
    s = re.sub(r"[\s_-]+", "-", s)
    return (s or "documento")[:60]


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
