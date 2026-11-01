# -*- coding: utf-8 -*-
# ACCOUNT NUOVO — ingresso a registrazione / accesso / upgrade Pro nel frontend
# ricomposto (strangler-fig).
#
# Serve SOLO la pagina /account: iscrizione, accesso, richiesta reset password e,
# quando l'utente è loggato, il bottone "Passa a Pro". Pagina nuova e isolata:
# NON tocca /app, /app2, index.html, index2.html, né le altre pagine del FE nuovo.
#
# Perché /account (e non "-nuovo" come le altre pagine): le pagine /scopri-nuovo,
# /causa-nuovo, /menu-nuovo, /componi-nuovo sono RIEDIZIONI di schermate già
# esistenti, quindi portano il suffisso per non collidere col vecchio path. Questa
# invece è una destinazione NUOVA (non esiste un "/account" vecchio da affiancare):
# un nome breve e convenzionale, chiaro in it/en/es, è la scelta corretta.
#
# La pagina aggancia endpoint che ESISTONO GIÀ (routes/auth_routes.py per
# registra/login/verifica-email/reset, routes/misc.py per /v1/stripe/checkout) e
# riusa la STESSA chiave di storage del token (localStorage "matter_token" /
# "matter_piano") e lo STESSO header Bearer del foglio di login di chat-nuovo.html:
# nessun secondo sistema di auth.
#
# Stesso pattern di routes/home_nuova.py: render_template + header anti-cache,
# così il browser rivalida sempre l'app-shell.
from flask import Blueprint, render_template, make_response

bp_account_nuovo = Blueprint("account_nuovo", __name__)


@bp_account_nuovo.route("/account", methods=["GET"])
def account_nuovo():
    """FRONTEND — Account: iscrizione, accesso, reset password e "Passa a Pro".
    Aggancia gli endpoint auth/stripe esistenti; stessa chiave token del resto
    del FE nuovo. Sistema di design congelato (matter3.css). Pagina isolata."""
    resp = make_response(render_template("account-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
