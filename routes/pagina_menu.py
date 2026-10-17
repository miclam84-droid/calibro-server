# ============================================================
# routes/pagina_menu.py — SCHERMO frontend "Menu" (strangler-fig).
# Pagina NUOVA e ISOLATA: non tocca index.html, index2.html, /app, /app2.
# Serve solo templates/menu.html con header no-cache (pattern da routes/pwa.py).
# Il cablaggio agli endpoint reali del menu builder è nel template (fetch lato client):
#   POST /v1/menu/crea          crea un menu, torna {id}
#   POST /v1/menu/<id>/salva    aggiorna titolo/locale/voci
#   GET  /v1/menu/<id>          rilegge il menu salvato
#   GET  /v1/menu/<id>/render   anteprima HTML stampabile (?template=...)
#   GET  /v1/menu/<id>/pdf      PDF vero scaricabile
#   GET  /v1/menu/<id>/qr       QR PNG (richiede PUBLIC_BASE_URL lato server)
#   GET  /v1/menu/templates     elenco temi grafici
# ============================================================
from flask import Blueprint, render_template, make_response

bp_pag_menu = Blueprint("pagina_menu", __name__)


@bp_pag_menu.route("/menu")
def pagina_menu():
    """FRONTEND-2.0 — schermata Menu: crea un menu, aggiungi voci, anteprima/PDF/QR.
    Sistema di design congelato (matter2.css), cablata dal vivo al menu builder
    (routes/menu_builder.py). Pagina nuova e isolata: non tocca /app né /app2."""
    resp = make_response(render_template("menu.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
