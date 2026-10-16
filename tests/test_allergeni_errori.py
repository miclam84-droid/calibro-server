"""Rete di test — onestà degli errori allergeni (Reg. UE 1169/2011).

La tesi del prodotto: un GUASTO non deve MAI travestirsi da "nessun allergene".
Un allergene omesso per un errore è responsabilità legale. Qui si blindano due garanzie:

  1. input 'ingredienti' non-lista  -> 400 esplicito (mai iterato in silenzio,
     e la risposta NON contiene un campo 'allergeni' spurio);
  2. errore DB sul percorso ricetta -> 5xx SENZA spacciarsi per lista vuota;
     il percorso di SUCCESSO include invece SEMPRE il campo 'allergeni'.

Niente DB né rete reali: il percorso d'errore si simula via monkeypatch.
"""
import pytest
from flask import Flask

import db
from routes.allergeni import bp_allergeni


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(bp_allergeni)
    app.config["TESTING"] = True
    return app.test_client()


# ── 1. input non-lista -> 400, e MAI un risultato allergeni ────────────────────

def test_deduci_ingredienti_stringa_rifiutata(client):
    # una stringa è iterabile: senza la guardia produrrebbe match per-carattere in silenzio.
    r = client.post("/v1/allergeni/deduci", json={"ingredienti": "farina, pomodoro"})
    assert r.status_code == 400
    body = r.get_json()
    assert "allergeni" not in body        # un errore non diventa un risultato
    assert "errore" in body


def test_deduci_ingredienti_dict_rifiutato(client):
    r = client.post("/v1/allergeni/deduci", json={"ingredienti": {"nome": "farina"}})
    assert r.status_code == 400
    assert "allergeni" not in r.get_json()


def test_deduci_successo_include_sempre_allergeni(client):
    # il percorso valido deve SEMPRE portare il campo 'allergeni'.
    r = client.post("/v1/allergeni/deduci", json={"ingredienti": ["gamberi", "vino"]})
    assert r.status_code == 200
    body = r.get_json()
    assert "allergeni" in body
    assert 2 in body["allergeni"] and 12 in body["allergeni"]  # crostacei + solfiti


# ── 2. errore DB -> 5xx, mai 200-senza-allergeni ───────────────────────────────

class _DBCheGuasta:
    """Finto grafo: qualsiasi query esplode, come un guasto reale del DB."""
    def execute(self, *a, **k):
        raise RuntimeError("guasto DB simulato")


def test_ricetta_errore_db_non_e_200_senza_allergeni(client, monkeypatch):
    # l'endpoint fa `from db import carica_grafo` a runtime: basta patchare db.carica_grafo.
    monkeypatch.setattr(db, "carica_grafo", lambda: _DBCheGuasta())
    r = client.get("/v1/ricetta/qualunque/allergeni")
    assert r.status_code >= 500           # 500/503, MAI 200
    body = r.get_json()
    # la garanzia legale: il guasto non si traveste da "nessun allergene".
    assert body.get("allergeni") is None
    assert body.get("stato") == "error" or "errore" in body
