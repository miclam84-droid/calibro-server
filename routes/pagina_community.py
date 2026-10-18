# -*- coding: utf-8 -*-
# ============================================================
# PAGINA COMMUNITY — "Vetrina del Banco" nel nuovo frontend.
#
# Strangler-fig: pagina NUOVA e ISOLATA (come /scopri, /famiglie, /quaderno).
# Non tocca index.html / index2.html / /app / /app2 / scheda.html.
#
# Qui NON definiamo endpoint dati: il feed/pubblica/profilo/clona esistono gia'
# in routes/community.py (blueprint bp_community). Questa pagina si limita a
# servire la schermata HTML che li cabla dal vivo. Design congelato (matter2.css),
# identita' via X-Device-Id da localStorage come il resto della PWA.
# ============================================================
from flask import Blueprint, render_template, make_response

bp_pag_community = Blueprint("pagina_community", __name__)


@bp_pag_community.route("/community", methods=["GET"])
def pagina_community():
    """FRONTEND-2.0 — schermata 'Community / Vetrina del Banco': feed dei
    contributi, pubblica un contributo, vedi/modifica il profilo, clona un
    contributo nel proprio Quaderno. Cablata dal vivo agli endpoint esistenti
    /v1/community/*. Pagina nuova e isolata: non tocca /app ne' /app2."""
    resp = make_response(render_template("community.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
