# -*- coding: utf-8 -*-
# LAB ESPERIMENTO — perno "forma-esperimento" (PROTOTIPO, isolato).
#
# Serve SOLO /lab/<ingrediente>: l'ingrediente apre il suo BANCO DI LAVORO —
# cos'e' (identita' + firma di gusto con provenienza) -> "Cosa ci fai" (gli
# esperimenti/Protocol Hub, raggruppati per rilevanza protagonista/comprimario)
# -> dentro un esperimento (obiettivo, bersaglio, la CAUSALITA' del fenomeno,
# variabile critica, osservazione, correzione, attrezzo nel punto giusto).
#
# Niente logica dati qui: la pagina fa fetch client-side degli endpoint gia'
# esistenti (/v1/ingrediente, /v1/profilo-gusto, /v1/ingrediente/<x>/protocolli,
# /v1/protocollo/<id>). Pagina nuova e isolata (strangler-fig): NON tocca
# nessuna pagina del FE esistente. E' il prototipo da testare prima di estendere.
from flask import Blueprint, render_template, make_response

bp_lab = Blueprint("lab_esperimento", __name__)


@bp_lab.route("/lab/<ingrediente>", methods=["GET"])
def lab(ingrediente):
    """FRONTEND — perno forma-esperimento: l'ingrediente apre un laboratorio,
    non una pagina. Prototipo su dati veri (Costituzione ART.5 #419)."""
    resp = make_response(render_template("lab-esperimento.html", ingrediente=ingrediente))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
