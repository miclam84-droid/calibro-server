# -*- coding: utf-8 -*-
# HOME NUOVA — fondazione del frontend ricomposto (strangler-fig).
#
# Serve SOLO la pagina /nuovo: la Home/nav con il sistema di design "pelle A"
# (matter3.css) — wordmark, ricerca, "Il banco di oggi", le 5 porte, corridoio.
# Pagina nuova e isolata: NON tocca /app, /app2, index.html, index2.html,
# né le pagine esistenti del nuovo FE (/scopri, /ingrediente, /banco, ...).
#
# Stesso pattern di routes/pwa.py (funzione scopri): render_template + header
# anti-cache, cosi' il browser rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_home_nuova = Blueprint("home_nuova", __name__)


@bp_home_nuova.route("/nuovo", methods=["GET"])
def home_nuova():
    """FRONTEND — Home/nav ricomposta: wordmark Matter Bench, ricerca,
    "Il banco di oggi" (gesto + dato d'esempio), le 5 porte (Atlante, Banco,
    Laboratorio, Menu, Quaderno), "Chiedi a Matter". Sistema di design
    congelato (matter3.css). Pagina nuova e isolata: non tocca /app né /app2."""
    resp = make_response(render_template("home-nuova.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
