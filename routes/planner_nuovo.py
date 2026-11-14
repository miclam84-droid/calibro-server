# -*- coding: utf-8 -*-
# PLANNER NUOVO — ricollega il modulo Planner (static/matter-planner.js), già costruito
# e col backend vivo (/v1/planner/genera, /v1/planner/lista-ordini), dentro il nuovo
# frontend. Pagina autonoma, isolata (strangler-fig): fornisce solo gli shim minimi che
# il modulo si aspetta (_escV, _apriVista, _chatConContesto) e la CSS pl-* via matter.css.
# NON tocca nessuna pagina esistente.
from flask import Blueprint, render_template, make_response

bp_planner_nuovo = Blueprint("planner_nuovo", __name__)


@bp_planner_nuovo.route("/planner-nuovo", methods=["GET"])
def planner_nuovo():
    """FRONTEND — Planner Menu: progetta il calendario dei menu (periodo, portate,
    no-ripeti, stagionalità del mese, food cost). Motore gia' costruito."""
    resp = make_response(render_template("planner-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
