"""Rete di test per l'hardening wave3 (sicurezza) — file lasciati fuori dalla wave2.

Fix #1: auth admin fail-closed in routes/admin_panel.py.
  Prima: /admin/logs e /admin/logs/summary confrontavano ?s= con os.environ.get(
  "ADMIN_SECRET", "") usando !=. Con ADMIN_SECRET ASSENTE il default "" rendeva
  "" != "" falso → accesso CONSENTITO senza secret (fail-OPEN). Ora passano per
  _admin_ok (hmac.compare_digest, NEGA se il secret manca), preservando ?s=.
  /admin/context (PANEL_SECRET, contratto con Cifra) era già fail-closed: qui si
  verifica solo che il confronto resti a tempo costante e che ?s= continui a valere.

Niente DB: oss.* non viene mai raggiunto perché il gate nega prima.
"""
import flask
import pytest

import routes.admin_panel as admin_panel


def _client():
    app = flask.Flask(__name__)
    app.register_blueprint(admin_panel.bp)
    return app.test_client()


# ── _admin_ok: fail-closed quando il secret manca ──

def test_admin_ok_negato_se_secret_non_impostato(monkeypatch):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    app = flask.Flask(__name__)
    with app.test_request_context("/admin/logs?s="):      # s vuoto + secret assente
        assert admin_panel._admin_ok(flask.request) is False
    with app.test_request_context("/admin/logs"):          # nessun s
        assert admin_panel._admin_ok(flask.request) is False


def test_admin_ok_confronto_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "giusto")
    app = flask.Flask(__name__)
    with app.test_request_context("/admin/logs?s=sbagliato"):
        assert admin_panel._admin_ok(flask.request) is False
    with app.test_request_context("/admin/logs?s=giusto"):   # retrocompat ?s=
        assert admin_panel._admin_ok(flask.request) is True
    with app.test_request_context("/admin/logs", headers={"X-Admin-Secret": "giusto"}):
        assert admin_panel._admin_ok(flask.request) is True


# ── end-to-end: i log admin negano (403) quando il secret manca (era il fail-open) ──

def test_logs_fail_closed_se_secret_assente(monkeypatch):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    c = _client()
    assert c.get("/admin/logs?s=").status_code == 403       # prima della wave3: 200
    assert c.get("/admin/logs").status_code == 403
    assert c.get("/admin/logs/summary?s=").status_code == 403
    assert c.get("/admin/logs/summary").status_code == 403


def test_logs_negano_secret_sbagliato(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "giusto")
    c = _client()
    assert c.get("/admin/logs?s=sbagliato").status_code == 403
    assert c.get("/admin/logs/summary?s=sbagliato").status_code == 403


# ── /admin/context (PANEL_SECRET): resta fail-closed e ?s= resta valido ──

def test_context_fail_closed_se_panel_secret_assente(monkeypatch):
    monkeypatch.delenv("PANEL_SECRET", raising=False)
    c = _client()
    assert c.get("/admin/context?s=").status_code == 403
    assert c.get("/admin/context").status_code == 403


def test_context_nega_secret_sbagliato(monkeypatch):
    monkeypatch.setenv("PANEL_SECRET", "giusto")
    c = _client()
    assert c.get("/admin/context?s=sbagliato").status_code == 403
