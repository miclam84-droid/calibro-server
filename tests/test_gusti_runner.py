"""Rete di test per la pagina admin /admin/gusti-search-runner.
Il runner NON reimplementa la logica USDA: serve solo una pagina HTML che, lato
browser, richiama l'endpoint esistente /admin/deriva-gusti-search a lotti.
Qui verifichiamo, offline (niente DB né rete), che:
  - la rotta sia registrata e risponda 200 con HTML;
  - la pagina punti all'endpoint esistente con pausa anti-rate e parametri giusti;
  - usi path RELATIVI (così vale sia staging sia prod);
  - gestisca fine/errore senza loop infinito (presenza dei controlli nel JS).
"""
import flask

import routes.gusti_runner as gr


def _client():
    app = flask.Flask(__name__)
    app.register_blueprint(gr.bp_gusti_runner)
    return app.test_client()


def test_rotta_registrata_e_html_200():
    r = _client().get("/admin/gusti-search-runner?s=qualsiasi")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("Content-Type", "")
    assert b"<!doctype html>" in r.data.lower()


def test_chiama_endpoint_esistente_con_esegui_e_lotti():
    html = _client().get("/admin/gusti-search-runner").data.decode()
    # richiama l'endpoint REALE, non ne reimplementa la logica
    assert "/admin/deriva-gusti-search?s=" in html
    assert "&esegui=1" in html
    assert "&limite=" in html and "&offset=" in html


def test_pausa_anti_rate_presente():
    html = _client().get("/admin/gusti-search-runner").data.decode()
    # pausa ~4s tra un lotto e l'altro per rispettare il rate USDA (1000/h)
    assert "PAUSA_MS = 4000" in html


def test_legge_prossimo_offset_e_fine():
    html = _client().get("/admin/gusti-search-runner").data.decode()
    assert "prossimo_offset" in html
    assert "d.fine === true" in html


def test_path_relativo_niente_host_assoluto():
    html = _client().get("/admin/gusti-search-runner").data.decode()
    # path relativo: eredita l'host della pagina -> vale su staging e prod
    assert "http://" not in html.replace("http://www.w3.org", "")  # eventuali namespace esclusi
    assert "fetch(url" in html or "await fetch(url" in html


def test_non_loop_infinito_su_errore():
    html = _client().get("/admin/gusti-search-runner").data.decode()
    # su errore il runner si ferma (throw -> catch -> stato errore), non ricicla
    assert "runner fermato" in html
    assert "throw new Error" in html
