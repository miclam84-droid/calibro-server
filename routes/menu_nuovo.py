# -*- coding: utf-8 -*-
# MENU NUOVO — R4b del frontend ricomposto (strangler-fig).
#
# Serve SOLO la pagina /menu-nuovo: COMPONI L'OFFERTA assemblando le
# preparazioni che hai gia' salvato (funzione="composer" nel Quaderno unico).
# Pagina nuova e isolata: NON tocca /app, /app2, index.html, index2.html,
# menu.html (vecchio), /menu, scheda.html, quaderno.html, ne' le altre pagine
# del FE esistente.
#
# Niente generazione AI e niente voci inventate: il menu e' l'assemblaggio
# ONESTO delle tue preparazioni reali. La pagina fa fetch client-side di
# GET /v1/quaderno2/lista (sorgente viva, routes/quaderno_unico.py) con header
# X-Device-Id, e salva con POST /v1/quaderno2/salva. Se non hai preparazioni,
# stato onesto con link a /componi-nuovo.
#
# Stesso pattern di routes/home_nuova.py e routes/componi_nuovo.py:
# render_template + header anti-cache, cosi' il browser rivalida l'app-shell.
from flask import Blueprint, render_template, make_response

bp_menu_nuovo = Blueprint("menu_nuovo", __name__)


@bp_menu_nuovo.route("/menu-nuovo", methods=["GET"])
def menu_nuovo():
    """FRONTEND R4b — Menu: componi l'offerta dalle TUE preparazioni salvate
    (funzione="composer"). Nessuna voce inventata, nessuna generazione AI:
    solo l'assemblaggio onesto di cio' che hai gia' nel Quaderno. Sistema di
    design congelato (matter3.css). Pagina nuova e isolata: non tocca /menu."""
    resp = make_response(render_template("menu-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
