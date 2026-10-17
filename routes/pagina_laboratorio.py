# -*- coding: utf-8 -*-
# PAGINA LABORATORIO SENSORIALE — schermo frontend (strangler-fig).
#
# Serve SOLO la pagina /laboratorio: una PWA isolata, cablata dal vivo ai 3
# endpoint di sola lettura di routes/laboratorio_sensoriale.py
# (/v1/laboratorio/perche, /sostituisci, /confronta). Non tocca /app, /app2,
# index.html, index2.html: pagina nuova e isolata come /scopri e /ingrediente.
#
# Stesso pattern di routes/pwa.py (funzione scopri): render_template + header
# anti-cache, cosi' il browser rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_pag_lab = Blueprint("pagina_laboratorio", __name__)


@bp_pag_lab.route("/laboratorio", methods=["GET"])
def pagina_laboratorio():
    """FRONTEND-2.0 — schermata Laboratorio Sensoriale: "perche' due ingredienti
    funzionano, cosa li sostituisce, come si confrontano". Sistema di design
    congelato (matter2.css), cablata dal vivo a /v1/laboratorio. Pagina nuova e
    isolata: non tocca /app (vecchio) ne' /app2."""
    resp = make_response(render_template("laboratorio.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
