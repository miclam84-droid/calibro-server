# ============================================================
# routes/pagina_quaderno.py — FRONTEND-2.0 — schermata "Quaderno".
# Pagina nuova e ISOLATA (strangler-fig): non tocca /app (index.html),
# /app2 (index2.html) né scheda.html. Serve solo l'HTML; i dati arrivano
# dal backend dell'archivio unico (blueprint bp_quaderno2, routes/quaderno_unico.py):
#   POST /v1/quaderno2/salva        GET /v1/quaderno2/lista
#   GET  /v1/quaderno2/<rid>        POST /v1/quaderno2/<rid>/aggiorna
# L'identità (user o device) la gestisce il backend; qui si manda solo X-Device-Id.
# Header no-cache come /app e /scopri (pattern da routes/pwa.py).
# ============================================================
from flask import Blueprint, render_template, make_response

bp_pag_quaderno = Blueprint("pagina_quaderno", __name__)


@bp_pag_quaderno.route("/quaderno")
def quaderno():
    """FRONTEND-2.0 — Quaderno: l'archivio unico degli appunti salvati.
    Lista i record (/lista), ne apre uno (/<rid>), crea un appunto (/salva),
    lo modifica o lo archivia (/<rid>/aggiorna). Cablata al vivo, zero dati finti.
    Pagina isolata: non tocca /app né /app2."""
    resp = make_response(render_template("quaderno.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
