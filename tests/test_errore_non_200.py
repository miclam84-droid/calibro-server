"""Rete di test — onestà dei dati: un errore NON si traveste da 200.
Verifica che i percorsi d'errore di ricettario/quiz restituiscano uno status
reale (500 server/DB, 503 dipendenza assente) invece di un 200 con corpo vuoto.
Niente DB né rete: si forza l'errore o si sfrutta l'assenza di DATABASE_URL.
"""
import flask
import pytest

import routes.ricettario as ricettario
import routes.quiz_engine as quiz_engine


def _app(bp):
    app = flask.Flask(__name__)
    app.register_blueprint(bp)
    return app.test_client()


class _DbCheScoppia:
    """db finto: la query scoppia come un errore reale sul DB di produzione."""
    def execute(self, *a, **k):
        raise RuntimeError("errore query su DB")


def test_ricettario_canonico_errore_db_non_e_200(monkeypatch):
    # prima era 200 con {"ricette": []}; ora l'errore DB deve diventare 500 con "errore"
    monkeypatch.setattr(ricettario, "carica_grafo", lambda: _DbCheScoppia())
    client = _app(ricettario.bp_ricettario)
    resp = client.get("/v1/ricettario/canonico")
    assert resp.status_code != 200
    assert resp.status_code == 500
    assert "errore" in resp.get_json()


def test_ricettario_discipline_errore_db_non_e_200(monkeypatch):
    monkeypatch.setattr(ricettario, "carica_grafo", lambda: _DbCheScoppia())
    client = _app(ricettario.bp_ricettario)
    resp = client.get("/v1/ricettario/discipline")
    assert resp.status_code == 500
    assert "errore" in resp.get_json()


def test_quiz_rispondi_senza_db_non_e_200(monkeypatch):
    # senza DATABASE_URL un POST che deve scrivere non puo' riuscire: 503, non 200
    monkeypatch.setattr(quiz_engine, "DATABASE_URL", None)
    client = _app(quiz_engine.bp)
    resp = client.post("/v1/quiz/rispondi", json={"quiz_id": 1, "risposta": "x"})
    assert resp.status_code != 200
    assert resp.status_code == 503
    assert "errore" in resp.get_json()
