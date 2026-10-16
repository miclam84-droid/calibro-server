"""Rete di test — fail-loud sulla base URL pubblica (wave 3).

Tesi: un guasto di CONFIGURAZIONE (variabile d'ambiente della base URL mancante) non
deve passare inosservato ricadendo in silenzio su un host fisso. I link di verifica
email / reset password e il QR del menu diventerebbero sbagliati senza alcun avviso.

Qui si blindano tre garanzie, tutte senza DB né rete reali:
  1. /v1/auth/registra        -> 503 esplicito se MATTER_BASE_URL manca (prima di creare l'utente);
  2. /v1/auth/reset-richiesta -> 503 esplicito se MATTER_BASE_URL manca (senza rivelare l'email);
  3. /v1/menu/<id>/qr         -> 503 esplicito se PUBLIC_BASE_URL manca (nessun QR verso host errato).
"""
import pytest
from flask import Flask

import routes.auth_routes as auth_routes
from routes.auth_routes import bp as bp_auth
from routes.menu_builder import bp_menu


@pytest.fixture
def auth_client(monkeypatch):
    # base URL assente: è il guasto di configurazione sotto test.
    monkeypatch.delenv("MATTER_BASE_URL", raising=False)
    # DATABASE_URL "presente" così si supera la guardia DB e si arriva a quella sulla base URL,
    # che sta PRIMA di qualsiasi connessione reale: nessun DB viene toccato.
    monkeypatch.setattr(auth_routes, "DATABASE_URL", "postgres://fake", raising=False)
    app = Flask(__name__)
    app.register_blueprint(bp_auth)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def menu_client():
    app = Flask(__name__)
    app.register_blueprint(bp_menu)
    app.config["TESTING"] = True
    return app.test_client()


# ── 1. registrazione: base URL mancante -> 503, e l'utente NON viene creato ─────

def test_registra_senza_base_url_503(auth_client):
    r = auth_client.post("/v1/auth/registra",
                         json={"email": "mario@example.com", "password": "unapassword8"})
    assert r.status_code == 503
    body = r.get_json()
    assert "MATTER_BASE_URL" in body.get("errore", "")


# ── 2. reset: base URL mancante -> 503 (fail-loud, senza leak sull'esistenza email) ─

def test_reset_richiesta_senza_base_url_503(auth_client):
    r = auth_client.post("/v1/auth/reset-richiesta", json={"email": "mario@example.com"})
    assert r.status_code == 503
    assert "MATTER_BASE_URL" in r.get_json().get("errore", "")


# ── 3. QR del menu: base URL mancante -> 503, mai un QR verso un host fisso errato ─

def test_menu_qr_senza_base_url_503(menu_client, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    r = menu_client.get("/v1/menu/menu-abc123/qr")
    assert r.status_code == 503
    assert "PUBLIC_BASE_URL" in r.get_json().get("errore", "")
