# -*- coding: utf-8 -*-
# COMPONI NUOVO — R3 del frontend ricomposto (strangler-fig).
#
# Serve SOLO le pagine /componi-nuovo e /componi-nuovo/<iniziale>: il
# COSTRUTTORE di una preparazione con il PROFILO VIVO combinato dei 6 gusti.
# Pagina nuova e isolata: NON tocca /app, /app2, index.html, index2.html,
# scheda.html, /laboratorio, né le altre pagine del FE esistente.
#
# Niente logica di dati qui: la pagina fa fetch client-side di
# GET /v1/profilo-gusto/<nome> (sorgente viva, routes/scheda_gusto.py) e
# combina i profili SOLO nel browser, in JS puro. Nessun numero inventato:
# la provenienza di ogni asse combinato è la PEGGIORE dei suoi input e un
# asse senza dati resta "—".
#
# Stesso pattern di routes/home_nuova.py e routes/scopri_nuovo.py:
# render_template + header anti-cache, così il browser rivalida l'app-shell.
from flask import Blueprint, render_template, make_response

bp_componi_nuovo = Blueprint("componi_nuovo", __name__)


def _render(iniziale):
    resp = make_response(render_template("componi-nuovo.html", iniziale=iniziale))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@bp_componi_nuovo.route("/componi-nuovo", methods=["GET"])
def componi_nuovo_default():
    """FRONTEND R3 — Componi: costruttore + profilo vivo combinato dei 6 gusti.
    Nessun seme: si riprende dal corridoio se c'è una preparazione in corso.
    Sistema di design congelato (matter3.css). Pagina nuova e isolata."""
    return _render(None)


@bp_componi_nuovo.route("/componi-nuovo/<iniziale>", methods=["GET"])
def componi_nuovo(iniziale):
    """FRONTEND R3 — Componi seminato con un ingrediente (<iniziale>): la
    preparazione parte già con quel componente. Il profilo combinato è sempre
    derivato/stimato, mai verificato."""
    return _render(iniziale)
