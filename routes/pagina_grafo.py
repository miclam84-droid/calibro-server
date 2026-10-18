# ============================================================
# routes/pagina_grafo.py — FRONTEND-2.0 — schermata "Grafo" ego-centrico.
# Pagina nuova e ISOLATA (strangler-fig): non tocca /app (index.html),
# /app2 (index2.html) né scheda.html. Serve solo l'HTML; i dati arrivano
# dal backend del grafo ego-centrico (routes/api.py):
#   GET /v1/grafo-ego/<ingrediente>
#     -> {centro, vicini:[{nome,tipo(analogia/contrasto),forza,perche}], fenomeni:[{nome,slug}], nota}
# Il disegno è vanilla (SVG puro, nessuna libreria esterna): l'ingrediente
# al centro, i vicini intorno. Tap su un vicino -> ricarica con quello al centro.
# Onestà: se l'ingrediente ha pochi/zero vicini lo dice, non inventa nodi.
# Header no-cache come /app e /scopri (pattern da routes/pwa.py).
# ============================================================
from flask import Blueprint, render_template, make_response

bp_pag_grafo = Blueprint("pagina_grafo", __name__)

# ingrediente di default quando si entra da /grafo senza nome
INGREDIENTE_DEFAULT = "pomodoro"


def _no_cache(html):
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@bp_pag_grafo.route("/grafo")
def grafo_home():
    """FRONTEND-2.0 — Grafo ego-centrico: parte da un ingrediente di default.
    Pagina isolata: non tocca /app né /app2."""
    return _no_cache(render_template("grafo.html", ingrediente=INGREDIENTE_DEFAULT))


@bp_pag_grafo.route("/grafo/<ingrediente>")
def grafo_ingrediente(ingrediente):
    """FRONTEND-2.0 — Grafo ego-centrico centrato su <ingrediente>.
    Cablata al vivo su GET /v1/grafo-ego/<ingrediente>, zero dati finti."""
    return _no_cache(render_template("grafo.html", ingrediente=ingrediente))
