# -*- coding: utf-8 -*-
# SCOPRI NUOVO — il GRAFO VERO dentro il frontend ricomposto (strangler-fig, R2).
#
# Serve SOLO le pagine /scopri-nuovo e /scopri-nuovo/<ingrediente>: un grafo
# ego-centrico in SVG vanilla, nel sistema di design congelato (matter3.css).
# Pagina nuova e isolata: NON tocca /scopri, /app, /app2, grafo.html,
# pagina_grafo.py, index.html, index2.html né le altre pagine del FE esistente.
#
# La pagina fa fetch client-side di GET /v1/criteri/<ingrediente> (sorgente viva,
# routes/criteri.py): lo spessore del legame = evidenza.composti_condivisi VERO.
# Un legame di tradizione/contrasto senza composti_condivisi resta una linea
# sottile tratteggiata: nessun numero finto.
#
# Stesso pattern di routes/home_nuova.py: render_template + header anti-cache,
# cosi' il browser rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_scopri_nuovo = Blueprint("scopri_nuovo", __name__)


def _render(ingrediente):
    resp = make_response(render_template("scopri-nuovo.html", ingrediente=ingrediente))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@bp_scopri_nuovo.route("/scopri-nuovo", methods=["GET"])
def scopri_nuovo_default():
    """FRONTEND R2 — grafo vero ego-centrico (default: pomodoro). Sistema di
    design congelato (matter3.css). Pagina nuova e isolata."""
    return _render("pomodoro")


@bp_scopri_nuovo.route("/scopri-nuovo/<ingrediente>", methods=["GET"])
def scopri_nuovo(ingrediente):
    """FRONTEND R2 — grafo vero ego-centrico per un ingrediente specifico.
    Fetch client-side di /v1/criteri/<ingrediente>: spessore = composti_condivisi."""
    return _render(ingrediente)
