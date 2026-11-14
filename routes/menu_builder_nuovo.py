# -*- coding: utf-8 -*-
# MENU BUILDER NUOVO — ricollega il Menu Builder ricco (static/matter-menubuilder.js),
# già costruito col backend vivo (/v1/menu/analizza, /v1/dolce-per-menu, /v1/foto-analisi),
# dentro il nuovo frontend. Diventa IL Menu (la home ora punta qui al posto del /menu-nuovo
# magro). Pagina autonoma, isolata: fornisce gli shim minimi (_escV, _apriVista, _toast,
# _statoHeaders, _chatConContesto, chiudiVista) + CSS via matter.css.
from flask import Blueprint, render_template, make_response

bp_menu_builder_nuovo = Blueprint("menu_builder_nuovo", __name__)


@bp_menu_builder_nuovo.route("/menu-builder-nuovo", methods=["GET"])
def menu_builder_nuovo():
    """FRONTEND — Menu Builder: tipo menu -> voci (Quaderno/foto/a mano) -> analisi
    equilibrio -> chiusura (dolce). Motore gia' costruito."""
    resp = make_response(render_template("menu-builder-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
