# -*- coding: utf-8 -*-
# CAUSA NUOVO — R4b del frontend ricomposto (strangler-fig).
#
# Serve SOLO la pagina /causa-nuovo: il PERCORSO DIAGNOSTICO. Parti dal
# problema ("il cornicione non cresce", "il drink e' troppo dolce") e la
# pagina restringe le IPOTESI — non da' una causa certa.
# Pagina nuova e isolata: NON tocca /app, /app2, index.html, index2.html,
# le pagine FE vecchie, ne' le altre pagine del FE esistente.
#
# La pagina fa fetch client-side di POST /v1/diagnosi (sorgente viva,
# routes/api.py) con header X-Device-Id. Vincolo del revisore: la Causa NON
# e' un motore sintomo->causa certa. Banner fermo in cima ai risultati, le
# cause sono ipotesi (probabilita + come verificarle + cosa provare), con
# provenienza esplicita (da fonte vs proposta). Se nessuna ipotesi: stato
# onesto, niente cause inventate.
#
# Stesso pattern di routes/home_nuova.py: render_template + header anti-cache.
from flask import Blueprint, render_template, make_response

bp_causa_nuovo = Blueprint("causa_nuovo", __name__)


@bp_causa_nuovo.route("/causa-nuovo", methods=["GET"])
def causa_nuovo():
    """FRONTEND R4b — Causa: percorso diagnostico. Dal problema alle ipotesi
    (mai una certezza): probabilita, come verificarle al banco, cosa provare,
    con provenienza da-fonte vs proposta. Stato onesto se il patrimonio non
    ha ipotesi. Sistema di design congelato (matter3.css). Pagina isolata."""
    resp = make_response(render_template("causa-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
