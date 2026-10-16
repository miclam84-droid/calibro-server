"""Rete di test per l'hardening wave4 (robustezza input) — routes/api.py.

Fix #1: input malformato → 400 (richiesta sbagliata), non 500 (errore server).
  Sui due endpoint che leggevano direttamente request.json["immagine(i)_b64"]
  e facevano base64.b64decode senza validare forma/contenuto:
    - /v1/foto-analisi            (campo 'immagine_b64',  stringa)
    - /v1/menu/riconosci-ingredienti (campo 'immagini_b64', lista di stringhe)
  Prima: un tipo sbagliato o un base64 non valido sollevava un'eccezione fuori
  dal try → 500. Ora la forma/validità è controllata e si risponde 400.

Niente DB: la validazione risponde 400 PRIMA di qualsiasi chiamata Vision/DB.
Il percorso di SUCCESSO (immagini valide) non è testato qui perché richiede la AI.
"""
import flask

import routes.api as api
import utils


def _client():
    app = flask.Flask(__name__)
    app.register_blueprint(api.bp)
    return app.test_client()


def _reset_rate():
    # il rate-limit è in memoria: azzero per non far scattare 429 nei test
    utils._rate_store.clear()
    try:
        utils._rate_store_login.clear()
    except Exception:
        pass


# ── /v1/menu/riconosci-ingredienti: 'immagini_b64' malformato → 400 ──

def test_riconosci_immagini_b64_non_lista_da_400():
    _reset_rate()
    c = _client()
    # una stringa è "truthy" ma non è una lista: prima iterava char-per-char → 500
    r = c.post("/v1/menu/riconosci-ingredienti", json={"immagini_b64": "nonUnaLista"})
    assert r.status_code == 400


def test_riconosci_immagini_b64_elemento_non_stringa_da_400():
    _reset_rate()
    c = _client()
    r = c.post("/v1/menu/riconosci-ingredienti", json={"immagini_b64": [123]})
    assert r.status_code == 400


def test_riconosci_immagini_b64_base64_non_valido_da_400():
    _reset_rate()
    c = _client()
    # 'abcde' = 5 caratteri base64 → padding impossibile → b64decode solleva
    r = c.post("/v1/menu/riconosci-ingredienti", json={"immagini_b64": ["abcde"]})
    assert r.status_code == 400


def test_riconosci_senza_immagini_resta_400():
    # caso di SUCCESSO del controllo "nessuna immagine": deve restare 400 come prima
    _reset_rate()
    c = _client()
    r = c.post("/v1/menu/riconosci-ingredienti", json={"qualcosa": "altro"})
    assert r.status_code == 400
