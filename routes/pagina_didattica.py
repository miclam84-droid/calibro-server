# -*- coding: utf-8 -*-
# PAGINA DIDATTICA — schermo frontend (strangler-fig).
#
# Serve SOLO la pagina /didattica: una PWA isolata, cablata dal vivo agli
# endpoint GIA' ESISTENTI del backend (sola lettura):
#   GET /v1/fenomeni-madre                         (routes/api.py)
#   GET /v1/principi                               (routes/api.py)
#   GET /v1/fenomeno/<slug>/manifestazioni         (routes/api.py)
#   GET /v1/scheda-scienza/<slug>                  (routes/misc.py) -> i 3 livelli
#                                                   faccio/capisco/approfondisco
#   GET /v1/quiz?fenomeno_id=<slug>                (routes/quiz_engine.py)
#   POST /v1/quiz/rispondi                          (routes/quiz_engine.py)
#
# Non tocca /app, /app2, index.html, index2.html, scheda.html: pagina nuova e
# isolata come /scopri, /ingrediente e /laboratorio.
#
# Stesso pattern di routes/pwa.py (funzione scopri): render_template + header
# anti-cache, cosi' il browser rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_pag_didattica = Blueprint("pagina_didattica", __name__)


@bp_pag_didattica.route("/didattica", methods=["GET"])
def pagina_didattica():
    """FRONTEND-2.0 — schermata Didattica: elenco dei fenomeni madre e dei
    principi; aperto un fenomeno, mostra i 3 livelli reali del grafo
    (Faccio / Capisco / Approfondisco) con i campi veri della scheda-scienza,
    piu' le manifestazioni e, se presente, un'autoverifica dal motore quiz.
    Sistema di design congelato (matter2.css), cablata dal vivo. Pagina nuova e
    isolata: non tocca /app (vecchio) ne' /app2."""
    resp = make_response(render_template("didattica.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
