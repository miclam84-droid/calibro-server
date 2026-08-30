"""Riuso scarti / cross-utilization: dato uno scarto di lavorazione, propone i riusi.
Libreria delle corrispondenze più frequenti del banco (scarto → riusi), agganciata al Flavour
Network per il rinforzo molecolare. Ottimizzazione: recupera margine e riduce sprechi."""
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from config import DATABASE_URL
import json

bp_scarti = Blueprint("scarti", __name__)

# Libreria scarto → riusi (le corrispondenze più frequenti della ristorazione).
# origine = da cosa nasce lo scarto · scarto · riusi = dove reimpiegarlo · shelf_giorni = durata
_LIBRERIA_SCARTI = {
    "albumi": {"da": "tuorli usati (creme, paste, zabaione)", "scarto": "Albumi d'uovo",
               "riusi": ["Meringhe", "Sour (cocktail)", "Financier", "Amaretti", "Chiarificazione consommé"],
               "shelf_giorni": 4, "fenomeno": "fen-coagulazione"},
    "tuorli": {"da": "albumi usati (meringhe, bianco d'uovo)", "scarto": "Tuorli d'uovo",
               "riusi": ["Crema pasticcera", "Maionese", "Zabaione", "Pasta all'uovo", "Ganache montata"],
               "shelf_giorni": 2, "fenomeno": "fen-emulsione"},
    "bucce agrumi": {"da": "spremitura succhi, guarnizioni", "scarto": "Bucce di agrumi",
                     "riusi": ["Oleo saccharum", "Cordial", "Sciroppi", "Candite", "Zest per finish", "Gin infuso"],
                     "shelf_giorni": 5, "fenomeno": "fen-estrazione"},
    "gambi erbe": {"da": "foglie usate (guarnizioni, pesti)", "scarto": "Gambi di erbe aromatiche",
                   "riusi": ["Oli aromatici", "Brodi vegetali", "Sciroppi erbacei", "Sale aromatizzato"],
                   "shelf_giorni": 3, "fenomeno": "fen-estrazione"},
    "fondi caffè": {"da": "estrazione espresso", "scarto": "Fondi di caffè",
                    "riusi": ["Infusi alcolici (liquori)", "Rub per carni", "Crumble aromatico"],
                    "shelf_giorni": 2, "fenomeno": "fen-estrazione-caffe"},
    "lische pesce": {"da": "sfilettatura pesce", "scarto": "Lische e teste di pesce",
                     "riusi": ["Fumetto", "Fondo di pesce", "Bisque (crostacei)", "Garum"],
                     "shelf_giorni": 1, "fenomeno": "fen-estrazione"},
    "scarti verdure": {"da": "mondatura (bucce, cime, foglie esterne)", "scarto": "Scarti di verdure",
                       "riusi": ["Brodo vegetale", "Estratti", "Chips (bucce)", "Polvere di verdure disidratate"],
                       "shelf_giorni": 2, "fenomeno": "fen-estrazione"},
    "siero": {"da": "cagliata (formaggi freschi, ricotta)", "scarto": "Siero di latte",
              "riusi": ["Pane al siero", "Marinature (acido lattico)", "Bevande fermentate", "Cottura risotti"],
              "shelf_giorni": 3, "fenomeno": "fen-fermentazione"},
    "pane raffermo": {"da": "pane del giorno prima", "scarto": "Pane raffermo",
                      "riusi": ["Pangrattato", "Pappa al pomodoro", "Canederli", "Crostoni", "Panzanella"],
                      "shelf_giorni": 7, "fenomeno": "fen-shelf-life-pane"},
    "grasso cottura": {"da": "cottura carni grasse", "scarto": "Grasso di cottura",
                       "riusi": ["Fat-washing (cocktail)", "Confit", "Rosolatura", "Sapone (non food)"],
                       "shelf_giorni": 10, "fenomeno": "fen-fat-washing"},
}


def _trova_scarto(query):
    q = (query or "").lower().strip()
    for chiave, dati in _LIBRERIA_SCARTI.items():
        if chiave in q or q in chiave or q in dati["scarto"].lower():
            return chiave, dati
    return None, None


@bp_scarti.route("/v1/scarti/riusi", methods=["GET"])
def riusi_scarto():
    """Dato uno scarto, propone i riusi. ?scarto=albumi
    Restituisce i riusi, la shelf life, il fenomeno collegato."""
    query = (request.args.get("scarto") or "").strip()
    if not query:
        return jsonify({"errore": "manca ?scarto="}), 400
    chiave, dati = _trova_scarto(query)
    if not dati:
        return jsonify({"trovato": False, "scarto": query,
                        "nota": "Scarto non ancora in libreria. Scarti mappati: " +
                                ", ".join(v["scarto"] for v in _LIBRERIA_SCARTI.values())})
    return jsonify({
        "trovato": True,
        "scarto": dati["scarto"],
        "nasce_da": dati["da"],
        "riusi": dati["riusi"],
        "shelf_giorni": dati["shelf_giorni"],
        "fenomeno_id": dati["fenomeno"],
        "nota": f"Riutilizza entro {dati['shelf_giorni']} giorni per non sprecare.",
    })


@bp_scarti.route("/v1/scarti/libreria", methods=["GET"])
def libreria_scarti():
    """Tutta la libreria scarti (per la sezione ottimizzazione del Menu Lab / Quaderno)."""
    return jsonify({
        "scarti": [{"scarto": v["scarto"], "nasce_da": v["da"], "riusi": v["riusi"],
                    "shelf_giorni": v["shelf_giorni"], "fenomeno_id": v["fenomeno"]}
                   for v in _LIBRERIA_SCARTI.values()],
        "totale": len(_LIBRERIA_SCARTI),
    })


@bp_scarti.route("/v1/scarti/incastri", methods=["POST"])
def incastri_menu():
    """Cross-utilization: dato un set di piatti/preparazioni, rileva gli INCASTRI degli scarti.
    Body: {piatti:[nomi]}. Se un piatto genera uno scarto che un altro può usare → incastro trovato.
    Ottimizzazione dei sottoprodotti: recupero margine + riduzione sprechi."""
    body = request.json or {}
    piatti = body.get("piatti", [])
    if not isinstance(piatti, list) or not piatti:
        return jsonify({"errore": "manca piatti:[...]"}), 400
    testo = " ".join(str(p).lower() for p in piatti)
    incastri = []
    for chiave, dati in _LIBRERIA_SCARTI.items():
        # se nel menu c'è qualcosa che genera questo scarto...
        genera = any(k in testo for k in (dati["da"].lower().split()[0], chiave.split()[0]))
        if genera:
            # ...e un riuso è pertinente al tipo di locale (bar/cucina), lo propongo
            incastri.append({
                "scarto": dati["scarto"],
                "riusi_suggeriti": dati["riusi"][:3],
                "recupero": f"Lo scarto '{dati['scarto']}' delle tue preparazioni può alimentare: "
                            f"{', '.join(dati['riusi'][:2])}. Recupero margine + meno sprechi.",
                "shelf_giorni": dati["shelf_giorni"],
            })
    return jsonify({"incastri": incastri, "totale": len(incastri),
                    "nota": "Progetta il menu perché gli scarti di un piatto alimentino un altro."})
