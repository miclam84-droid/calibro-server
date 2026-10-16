"""Rete di test — audit READ-ONLY della provenienza fabbricata dall'AI.
Verifica il GATE (senza segreto -> 403) e la CLASSIFICAZIONE su data finti,
offline (niente DB ne' rete: la connessione e' monkeypatchata). Se questa rete
diventa rossa, o il cancello si e' aperto o il criterio di 'fabbricata' e'
regredito.
"""
import contextlib

import flask
import pytest

import routes.audit_provenienza as ap
from routes.audit_provenienza import classifica_fabbricata, audita_righe


def _app():
    app = flask.Flask(__name__)
    app.register_blueprint(ap.bp_audit_prov)
    return app.test_client()


# ── GATE ──────────────────────────────────────────────────────────────────

def test_senza_segreto_e_403(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "topolino")
    resp = _app().get("/admin/audit-provenienza")
    assert resp.status_code == 403
    assert "errore" in resp.get_json()


def test_segreto_sbagliato_e_403(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "topolino")
    resp = _app().get("/admin/audit-provenienza?s=paperino")
    assert resp.status_code == 403


def test_senza_admin_secret_configurato_e_403(monkeypatch):
    # se ADMIN_SECRET non e' impostato, l'endpoint resta chiuso (non si apre a tutti)
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    resp = _app().get("/admin/audit-provenienza?s=qualunque")
    assert resp.status_code == 403


# ── CLASSIFICAZIONE (funzione pura) ─────────────────────────────────────────

def test_fonte_top_level_inventata_e_fabbricata():
    fab, sospetta = classifica_fabbricata({"fonte": "Food Chemistry 2019 / McGee"})
    assert fab is True
    assert sospetta == "Food Chemistry 2019 / McGee"


def test_fonte_dentro_composto_e_fabbricata():
    dd = {"composti_aromatici": [{"nome": "limonene", "fonte": "McGee"}]}
    fab, sospetta = classifica_fabbricata(dd)
    assert fab is True
    assert sospetta == "McGee"


def test_fonte_reale_usda_non_e_fabbricata():
    fab, _ = classifica_fabbricata({"fonte": "USDA FDC 167747"})
    assert fab is False


def test_provenienza_dichiara_stima_non_e_fabbricata():
    # fonte sospetta ma il nodo dichiara onestamente la stima AI -> non fabbricata
    dd = {"fonte": "McGee", "provenienza": {"stato": "stimato_AI"}}
    assert classifica_fabbricata(dd)[0] is False


def test_provenienza_stringa_c_stima_ai_non_e_fabbricata():
    dd = {"fonte": "McGee", "provenienza": "C_stima_ai"}
    assert classifica_fabbricata(dd)[0] is False


def test_composto_con_stato_onesto_non_e_fabbricato():
    dd = {"composti_aromatici": [{"nome": "x", "fonte": "McGee", "stato": "stimato_AI"}]}
    assert classifica_fabbricata(dd)[0] is False


def test_senza_fonte_non_e_fabbricata():
    assert classifica_fabbricata({"nomi": {"it": "sale"}})[0] is False


def test_data_non_dict_non_rompe():
    assert classifica_fabbricata(None) == (False, None)
    assert classifica_fabbricata("stringa") == (False, None)
    assert classifica_fabbricata(["lista"]) == (False, None)


def test_composti_non_lista_non_rompe():
    assert classifica_fabbricata({"composti_aromatici": {"nope": 1}})[0] is False


# ── REPORT aggregato (funzione pura su righe finte) ─────────────────────────

def test_audita_righe_conta_e_ripartisce():
    righe = [
        ("ing-limone", "Ingrediente", {"fonte": "Food Chemistry 2019 / McGee"}),      # fabbricato
        ("ing-sale", "Ingrediente", {"nomi": {"it": "sale"}}),                          # senza_fonte
        ("ing-mela", "Prodotto", {"fonte": "USDA FDC 171688"}),                         # fonte reale -> non fabbricato
        ("ing-uva", "Prodotto", {"fonte": "McGee", "provenienza": {"stato": "stimato_AI"}}),  # dichiarato
        ("fen-x", "Fenomeno", {"proprieta_meta": {"dolce": {"stato": "derivato"}}}),    # stato onesto, senza fonte
    ]
    r = audita_righe(righe)
    assert r["nodi_totali"] == 5
    assert r["con_fonte_ai_fabbricata"] == 1
    # senza_fonte: sale + fen-x (nessun campo fonte)
    assert r["senza_fonte"] == 2
    # stato onesto: uva (provenienza stimato_AI) + fen-x (proprieta_meta derivato)
    assert r["con_stato_onesto"] == 2
    assert r["ripartizione_per_tipo"]["Ingrediente"]["con_fonte_ai_fabbricata"] == 1
    assert r["ripartizione_per_tipo"]["Prodotto"]["totali"] == 2
    assert len(r["campione"]) == 1
    assert r["campione"][0]["id"] == "ing-limone"
    assert "criterio" in r


def test_campione_max_25():
    righe = [("ing-%d" % i, "Ingrediente", {"fonte": "McGee %d" % i}) for i in range(40)]
    r = audita_righe(righe)
    assert r["con_fonte_ai_fabbricata"] == 40
    assert len(r["campione"]) == 25


# ── ENDPOINT end-to-end con connessione monkeypatchata (niente DB reale) ────

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, sql, params=()):
        # blinda l'onesta' del codice: l'audit deve restare SOLO lettura
        assert sql.strip().upper().startswith("SELECT"), "l'audit deve essere read-only"
        self._sql = sql
    def fetchall(self):
        return self._rows
    def close(self):
        pass


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
    def cursor(self):
        return _FakeCursor(self._rows)


def test_endpoint_con_segreto_e_connessione_finta(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "topolino")
    rows = [
        ("ing-limone", "Ingrediente", {"fonte": "Food Chemistry 2019 / McGee"}),
        ("ing-sale", "Ingrediente", {"nomi": {"it": "sale"}}),
    ]

    @contextlib.contextmanager
    def _fake_conn():
        yield _FakeConn(rows)

    monkeypatch.setattr(ap, "connessione", _fake_conn)
    resp = _app().get("/admin/audit-provenienza?s=topolino")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["nodi_totali"] == 2
    assert body["con_fonte_ai_fabbricata"] == 1
    assert body["campione"][0]["id"] == "ing-limone"
