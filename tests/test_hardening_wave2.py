"""Rete di test per l'hardening wave2 (sicurezza). Niente DB:
- login rate-limit dedicato e più stretto (utils)
- IDOR: _device() non accetta più il device_id dalla query string (mie_cose)
- auth admin fail-closed via _admin_ok con hmac.compare_digest (admin)
"""
import flask
import pytest

import utils
import routes.admin as admin
from routes import mie_cose


# ── Fix #4: rate-limit login dedicato e più stretto ──

def test_login_ha_limite_dedicato_piu_stretto():
    app = flask.Flask(__name__)
    utils._rate_store.clear(); utils._rate_store_login.clear()
    ip = "1.2.3.4"
    with app.test_request_context("/v1/auth/login"):
        esiti = [utils._check_rate_limit(ip) for _ in range(utils._RATE_LIMIT_LOGIN + 3)]
    # i primi N consentiti, poi bloccato esattamente al limite login
    assert esiti[:utils._RATE_LIMIT_LOGIN] == [True] * utils._RATE_LIMIT_LOGIN
    assert esiti[utils._RATE_LIMIT_LOGIN] is False
    # ...ed è davvero più stretto del generico
    assert utils._RATE_LIMIT_LOGIN < utils._RATE_LIMIT


def test_endpoint_generico_non_usa_il_limite_login():
    app = flask.Flask(__name__)
    utils._rate_store.clear(); utils._rate_store_login.clear()
    ip = "5.6.7.8"
    with app.test_request_context("/v1/chat"):
        # oltre il limite login, ma ben sotto il generico: ancora tutto consentito
        esiti = [utils._check_rate_limit(ip) for _ in range(utils._RATE_LIMIT_LOGIN + 5)]
    assert all(esiti)
    # il login non ha consumato budget generico e viceversa
    assert utils._rate_store_login == {}


# ── Fix #2: IDOR — niente device_id dalla query string ──

def test_device_ignora_query_string():
    app = flask.Flask(__name__)
    with app.test_request_context("/v1/ricette/le-mie?device_id=VITTIMA"):
        assert mie_cose._device() == ""          # la query string NON è più identità


def test_device_accetta_header():
    app = flask.Flask(__name__)
    with app.test_request_context("/v1/ricette/le-mie", headers={"X-Device-Id": "MIO-DEV"}):
        assert mie_cose._device() == "MIO-DEV"   # header: fonte che non finisce in URL/log


def test_device_header_vince_sulla_query():
    app = flask.Flask(__name__)
    with app.test_request_context("/x?device_id=VITTIMA", headers={"X-Device-Id": "MIO-DEV"}):
        assert mie_cose._device() == "MIO-DEV"


# ── Fix #3: auth admin fail-closed ──

def test_admin_ok_negato_se_secret_non_impostato(monkeypatch):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    app = flask.Flask(__name__)
    with app.test_request_context("/admin/x?s="):           # s vuoto + secret assente
        assert admin._admin_ok(flask.request) is False
    with app.test_request_context("/admin/x"):              # nessun s
        assert admin._admin_ok(flask.request) is False


def test_admin_ok_confronto_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "giusto")
    app = flask.Flask(__name__)
    with app.test_request_context("/admin/x?s=sbagliato"):
        assert admin._admin_ok(flask.request) is False
    with app.test_request_context("/admin/x?s=giusto"):
        assert admin._admin_ok(flask.request) is True
    with app.test_request_context("/admin/x", headers={"X-Admin-Secret": "giusto"}):
        assert admin._admin_ok(flask.request) is True


def test_route_admin_fail_closed_end_to_end(monkeypatch):
    # un handler reale deve negare (403) prima di toccare il DB quando il secret manca
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    app = flask.Flask(__name__)
    app.register_blueprint(admin.bp)
    r = app.test_client().get("/admin/coeff-zuccheri?s=")
    assert r.status_code == 403
