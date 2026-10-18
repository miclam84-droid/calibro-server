# -*- coding: utf-8 -*-
# CHAT NUOVA — "Chiedi a Matter" nel frontend ricomposto (strangler-fig).
#
# Serve SOLO la pagina /chiedi-nuovo: la chat col sistema di design "pelle A"
# (matter3.css), wordmark, UI mobile-first. La pagina parla con il backend
# ESISTENTE e ANONIMO POST /chiedi (routes/chat.py) — non reinventa nulla:
# invia {domanda, lang, history} con header X-Device-Id, mostra la risposta.
#
# Pagina nuova e isolata: NON tocca /app, /app2, index.html, index2.html,
# /laboratorio né le altre pagine (vecchie o nuove). Stesso pattern di
# routes/home_nuova.py: render_template + header anti-cache, così il browser
# rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_chat_nuovo = Blueprint("chat_nuovo", __name__)


@bp_chat_nuovo.route("/chiedi-nuovo", methods=["GET"])
def chiedi_nuovo():
    """FRONTEND — "Chiedi a Matter" ricomposta: chat mobile-first ancorata al
    grafo tramite il backend anonimo POST /chiedi. Sistema di design congelato
    (matter3.css). Pagina nuova e isolata: non tocca /app né /app2."""
    resp = make_response(render_template("chat-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
