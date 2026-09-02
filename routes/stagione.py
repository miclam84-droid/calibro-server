"""Stagionalità ingredienti italiani. Un menu di stagione è più economico, più buono, più
sostenibile. Calendario reale (frutta/verdura italiana per mese). Endpoint: cosa è di stagione ora."""
from flask import Blueprint, request, jsonify
from datetime import datetime

bp_stagione = Blueprint("stagione", __name__)

# Calendario stagionale italiano: ingrediente -> [mesi] (1=gennaio ... 12=dicembre).
_CALENDARIO = {
    # VERDURE
    "carciofo": [1, 2, 3, 4, 5, 11, 12], "asparago": [3, 4, 5, 6], "zucchina": [5, 6, 7, 8, 9],
    "fiori di zucca": [5, 6, 7, 8, 9], "melanzana": [6, 7, 8, 9, 10], "peperone": [6, 7, 8, 9, 10],
    "pomodoro": [6, 7, 8, 9], "zucca": [9, 10, 11, 12, 1], "cavolo": [10, 11, 12, 1, 2, 3],
    "cime di rapa": [10, 11, 12, 1, 2, 3], "friarielli": [10, 11, 12, 1, 2], "radicchio": [10, 11, 12, 1, 2],
    "cardo": [11, 12, 1, 2], "finocchio": [10, 11, 12, 1, 2, 3], "spinaci": [10, 11, 12, 1, 2, 3, 4],
    "porro": [10, 11, 12, 1, 2, 3], "broccolo": [10, 11, 12, 1, 2, 3], "cavolfiore": [10, 11, 12, 1, 2],
    "fava": [4, 5, 6], "pisello": [4, 5, 6], "fagiolino": [6, 7, 8, 9], "sedano": [9, 10, 11, 12, 1],
    "funghi porcini": [9, 10, 11], "tartufo bianco": [10, 11, 12], "tartufo nero": [12, 1, 2, 3],
    # FRUTTA
    "fragola": [4, 5, 6], "ciliegia": [5, 6], "albicocca": [6, 7], "pesca": [6, 7, 8, 9],
    "melone": [6, 7, 8, 9], "anguria": [6, 7, 8, 9], "fico": [8, 9], "uva": [9, 10, 11],
    "castagna": [10, 11, 12], "melagrana": [10, 11, 12], "cachi": [10, 11, 12],
    "arancia": [11, 12, 1, 2, 3, 4], "mandarino": [11, 12, 1, 2], "clementina": [11, 12, 1],
    "limone": [1, 2, 3, 4, 5, 11, 12], "mela": [9, 10, 11, 12, 1, 2, 3], "pera": [8, 9, 10, 11, 12],
    "kiwi": [11, 12, 1, 2, 3], "nespola": [4, 5], "prugna": [7, 8, 9],
    # PESCE (stagionalità di pesca)
    "alici": [4, 5, 6, 7, 8, 9], "sarde": [4, 5, 6, 7, 8, 9], "sgombro": [5, 6, 7, 8, 9],
    "tonno": [5, 6, 7], "polpo": [5, 6, 7, 8, 9], "seppie": [3, 4, 5, 9, 10], "vongole": [10, 11, 12, 1, 2],
    "cozze": [6, 7, 8, 9], "orata": [4, 5, 6, 7, 8], "branzino": [7, 8, 9, 10],
}

_MESI = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
         "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def _stagione_ingrediente(nome, mese=None):
    """Ritorna (di_stagione_ora: bool, mesi: list) per un ingrediente. mese default = mese corrente."""
    if mese is None:
        mese = datetime.now().month
    n = (nome or "").lower()
    for chiave, mesi in _CALENDARIO.items():
        if chiave in n or n in chiave:
            return (mese in mesi), mesi
    return None, None  # ingrediente non stagionale/non mappato


@bp_stagione.route("/v1/stagione/ora", methods=["GET"])
def stagione_ora():
    """Cosa è di stagione questo mese. ?mese= (opzionale, default corrente)."""
    try:
        mese = int(request.args.get("mese", datetime.now().month))
        if not 1 <= mese <= 12: mese = datetime.now().month
    except Exception:
        mese = datetime.now().month
    di_stagione = sorted([nome.capitalize() for nome, mesi in _CALENDARIO.items() if mese in mesi])
    return jsonify({"mese": _MESI[mese], "mese_num": mese, "di_stagione": di_stagione,
                    "totale": len(di_stagione)})


@bp_stagione.route("/v1/stagione/verifica", methods=["POST"])
def stagione_verifica():
    """Verifica quali ingredienti di una lista sono di stagione. Body: {ingredienti:[...], mese?}
    Utile nel Menu Lab: segnala i piatti con ingredienti fuori stagione."""
    body = request.json or {}
    ingredienti = body.get("ingredienti", [])
    try:
        mese = int(body.get("mese", datetime.now().month))
    except Exception:
        mese = datetime.now().month
    risultato = []
    for ing in ingredienti:
        nome = ing.get("nome", "") if isinstance(ing, dict) else str(ing)
        di_stag, mesi = _stagione_ingrediente(nome, mese)
        if di_stag is not None:
            risultato.append({"ingrediente": nome, "di_stagione": di_stag,
                              "mesi": [_MESI[m] for m in (mesi or [])]})
    fuori = [r["ingrediente"] for r in risultato if not r["di_stagione"]]
    return jsonify({"mese": _MESI[mese], "ingredienti": risultato,
                    "fuori_stagione": fuori,
                    "nota": "Un menu di stagione costa meno ed è più buono." if fuori else "Tutto di stagione."})
