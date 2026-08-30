"""Sistema immagini ricette: foto vera se c'è, altrimenti l'illustrazione BLUEPRINT del
fenomeno dominante (16 macro-famiglie, coerenti con l'identità Matter Bench).
Ogni ricetta ha SEMPRE un'immagine: nessun vuoto, zero costi, zero foto AI grottesche."""
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn, carica_grafo
from config import DATABASE_URL
import json

bp_img = Blueprint("immagini_ricette", __name__)

# 16 famiglie-blueprint: il frontend disegna un SVG geometrico per ognuna (Prussia/teal).
# Mappa: parola chiave nel nome/dominio del fenomeno → famiglia blueprint.
_FAMIGLIE_BLUEPRINT = {
    "emulsione": "emulsione", "maionese": "emulsione", "ganache": "emulsione",
    "maillard": "reazione-termica", "caramell": "reazione-termica", "cottura": "reazione-termica",
    "frittura": "reazione-termica", "barbecue": "reazione-termica", "tostatura": "reazione-termica",
    "lievit": "fermentazione", "ferment": "fermentazione", "madre": "fermentazione",
    "biga": "fermentazione", "poolish": "fermentazione", "malolattica": "fermentazione",
    "coagul": "coagulazione", "denatura": "coagulazione", "proteine": "coagulazione",
    "glutin": "impasto", "idratazione": "impasto", "impasto": "impasto", "laminazione": "impasto",
    "cristall": "cristallizzazione", "temperagg": "cristallizzazione", "zucchero": "cristallizzazione",
    "gelatinizz": "gelificazione", "amido": "gelificazione", "gel": "gelificazione",
    "estrazione": "estrazione", "infusione": "estrazione", "macerazione": "estrazione",
    "diluizione": "diluizione", "acqua": "diluizione",
    "acidità": "acidita", "acido": "acidita", "ph": "acidita", "sour": "acidita",
    "ossidazione": "ossidazione", "brett": "ossidazione", "tannini": "ossidazione",
    "carbonazione": "gas", "carbonat": "gas", "luppolo": "gas",
    "osmosi": "osmosi", "sale": "osmosi", "salamoia": "osmosi",
    "affumica": "affumicatura", "koji": "affumicatura", "fat-washing": "affumicatura",
    "distillaz": "distillazione", "chiarific": "distillazione",
    "conserv": "conservazione", "shelf": "conservazione", "haccp": "conservazione",
}
_FAMIGLIA_DEFAULT = "reazione-termica"


def _famiglia_da_testo(testo):
    t = (testo or "").lower()
    for chiave, fam in _FAMIGLIE_BLUEPRINT.items():
        if chiave in t:
            return fam
    return None


@bp_img.route("/v1/ricetta/<rid>/immagine", methods=["GET"])
def immagine_ricetta(rid):
    """Restituisce l'immagine da mostrare per una ricetta:
    - se ha una foto vera (campo immagine) → {tipo:'foto', url, autore, fonte}
    - altrimenti → {tipo:'blueprint', famiglia} (il frontend disegna l'SVG di quella famiglia)."""
    if not DATABASE_URL:
        return jsonify({"tipo": "blueprint", "famiglia": _FAMIGLIA_DEFAULT})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT immagine, immagine_autore, immagine_url_fonte, fenomeni, disciplina, nome "
                    "FROM ricette WHERE id=%s", (rid,))
        r = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not r:
            return jsonify({"errore": "ricetta non trovata"}), 404
        immagine, autore, fonte, fenomeni, disciplina, nome = r
        # 1) foto vera → vince sempre
        if immagine and isinstance(immagine, str) and immagine.strip():
            return jsonify({"tipo": "foto", "url": immagine.strip(),
                            "autore": autore or "", "fonte": fonte or ""})
        # 2) blueprint dal fenomeno dominante
        fam = None
        try:
            fen_list = fenomeni if isinstance(fenomeni, list) else (json.loads(fenomeni) if fenomeni else [])
            for f in fen_list:
                nome_fen = f if isinstance(f, str) else (f.get("nome") or f.get("id") or "")
                fam = _famiglia_da_testo(nome_fen)
                if fam:
                    break
        except Exception:
            pass
        # 3) fallback: dalla disciplina o dal nome ricetta
        if not fam:
            fam = _famiglia_da_testo(disciplina) or _famiglia_da_testo(nome) or _FAMIGLIA_DEFAULT
        return jsonify({"tipo": "blueprint", "famiglia": fam})
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"tipo": "blueprint", "famiglia": _FAMIGLIA_DEFAULT, "errore": str(e)[:80]}), 200


@bp_img.route("/v1/blueprint/famiglie", methods=["GET"])
def lista_famiglie():
    """Le 16 famiglie-blueprint disponibili (il frontend disegna un SVG per ognuna)."""
    famiglie = sorted(set(_FAMIGLIE_BLUEPRINT.values()))
    return jsonify({"famiglie": famiglie, "totale": len(famiglie), "default": _FAMIGLIA_DEFAULT})
