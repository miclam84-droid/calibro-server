# ============================================================
# routes/pagina_community.py — FRONTEND v5 — pagina "Vetrina del Banco".
# Serve solo l'HTML; i dati arrivano dal backend community (bp_community,
# routes/community.py): GET /v1/community/feed, POST /clona, GET/POST /profilo.
# Identità via X-Device-Id (come le altre pagine). Header no-cache.
# ============================================================
from flask import Blueprint, render_template, make_response

bp_pag_community = Blueprint("pagina_community", __name__)


@bp_pag_community.route("/vetrina")
def vetrina():
    """Vetrina del Banco: feed sola-lettura delle ricette pubbliche, clona nel
    Quaderno, profilo leggero con contatto esterno. Cablata al backend community."""
    resp = make_response(render_template("community-nuova.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
