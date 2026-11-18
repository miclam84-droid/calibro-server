# -*- coding: utf-8 -*-
# MENU BUILDER NUOVO — ricollega il Menu Builder ricco (static/matter-menubuilder.js),
# già costruito col backend vivo (/v1/menu/analizza, /v1/dolce-per-menu, /v1/foto-analisi),
# dentro il nuovo frontend. Diventa IL Menu (la home ora punta qui al posto del /menu-nuovo
# magro). Pagina autonoma, isolata: fornisce gli shim minimi (_escV, _apriVista, _toast,
# _statoHeaders, _chatConContesto, chiudiVista) + CSS via matter.css.
from flask import Blueprint, redirect

bp_menu_builder_nuovo = Blueprint("menu_builder_nuovo", __name__)


@bp_menu_builder_nuovo.route("/menu-builder-nuovo", methods=["GET"])
def menu_builder_nuovo():
    """CONSOLIDAMENTO (revisore 18/11, #46): un solo Menu Builder. Il builder ricco
    (salva/PDF/QR/pagina pubblica/template/allergeni) e' /menu-nuovo, dove ora sono
    stati portati anche gli strumenti del vecchio builder (accostamenti, tecniche,
    filo, equilibrio, chiusura). Questa vecchia pagina reindirizza, per non perdere
    i vecchi link; menu-builder-nuovo.html e matter-menubuilder.js restano nel repo
    finche' non si rimuovono, ma non sono piu' raggiungibili dalla nav."""
    return redirect("/menu-nuovo", code=302)
