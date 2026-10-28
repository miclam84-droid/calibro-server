# -*- coding: utf-8 -*-
# PAGINA IMPARA / PALESTRA — schermo frontend (strangler-fig).
#
# Serve SOLO la pagina /impara: la "palestra del mestiere", cablata dal vivo
# agli endpoint di sola lettura gia' esistenti di routes/lezione.py:
#   /v1/discipline            -> elenco discipline + n. lezioni
#   /v1/disciplina/<nome>     -> fenomeni (lezioni) di una disciplina
#   /lezione/<disc>/<step>    -> una lezione (gancio, scheda, scava, nav)
#   /quiz/<fenomeno-id>       -> quiz del fenomeno (domanda, opzioni, corretta)
# Pagina nuova e isolata, sistema di design congelato (matter3.css). Non tocca
# il vecchio frontend (index.html/index2.html). Stesso pattern anti-cache di
# routes/pagina_laboratorio.py.
from flask import Blueprint, render_template, make_response

bp_pag_impara = Blueprint("pagina_impara", __name__)


@bp_pag_impara.route("/impara", methods=["GET"])
def pagina_impara():
    """FRONTEND — "Impara / palestra del mestiere": discipline, lezioni e quiz.
    Cablata dal vivo agli endpoint di lettura di routes/lezione.py. Pagina nuova
    e isolata: non tocca il vecchio frontend."""
    resp = make_response(render_template("impara.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
