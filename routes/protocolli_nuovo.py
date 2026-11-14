# -*- coding: utf-8 -*-
# PROTOCOLLI NUOVO — ricollega la libreria dei protocolli (il cuore sorgentato
# dell'app: ~600 schede con bersaglio, fenomeni, causalità, diagnosi, sensori)
# nel frontend nuovo. Finora era raggiungibile solo di rimbalzo (vecchio
# frontend / scheda ingrediente), mai come libreria sfogliabile.
#
# ONESTÀ: il badge di provenienza NON si fida del flag `verificato` del dato.
# Lo deriva dall'evidenza reale (il_punto.evidence + bersaglio_fonte):
#   evidenza presente      -> "Verificato" con la fonte mostrata
#   verificato ma 0 fonti  -> "Verificato · senza riferimento" (giallo)
#   altrimenti             -> "Da validare al banco"
# Così l'interfaccia può solo dichiarare MENO di quanto il flag pretenda, mai di più.
# Legge /v1/protocolli e /v1/protocollo/<id> (già vivi). Pagina autonoma, isolata.
from flask import Blueprint, render_template, make_response

bp_protocolli_nuovo = Blueprint("protocolli_nuovo", __name__)


@bp_protocolli_nuovo.route("/protocolli-nuovo", methods=["GET"])
def protocolli_nuovo():
    """FRONTEND — Libreria dei protocolli: filtro per disciplina + ricerca ->
    scheda (bersaglio, variabile critica, sensori, fenomeni+causalità, diagnosi,
    ingredienti) con provenienza onesta e stampa per il banco."""
    resp = make_response(render_template("protocolli-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
