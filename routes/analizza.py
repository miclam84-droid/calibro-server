# -*- coding: utf-8 -*-
# ANALIZZA LA TUA PREPARAZIONE — la "porta dedicata" che mancava (#cipolle, 20/11).
#
# Serve SOLO la pagina /analizza: un ingresso STRUTTURATO (nome + ingredienti +
# passaggi) che compone una domanda ben formata e la manda al backend ESISTENTE
# e ANONIMO POST /chiedi (routes/chat.py) — NON reinventa il motore: lo stesso
# che risponde alle cipolle in chat. Mostra "cosa succede" + "come migliorare".
#
# Pagina nuova e isolata (stesso pattern di chat_nuovo.py): render_template +
# header anti-cache. Non tocca /app, /app2, le altre pagine né il backend.
from flask import Blueprint, render_template, make_response

bp_analizza = Blueprint("analizza", __name__)


@bp_analizza.route("/analizza", methods=["GET"])
def analizza():
    """FRONTEND — "Analizza la tua preparazione": l'utente scrive ingredienti e
    passaggi della SUA preparazione e Matter la analizza (cosa succede davvero +
    come migliorare), riusando il backend anonimo POST /chiedi con X-Device-Id.
    Pagina nuova e isolata; nessun motore nuovo."""
    resp = make_response(render_template("analizza.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
