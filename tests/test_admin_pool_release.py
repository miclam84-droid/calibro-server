"""Rete di test — leak del pool: un handler che SCOPPIA dopo aver preso una
connessione DEVE comunque rilasciarla (nel finally), altrimenti il pool (max ~10)
si esaurisce e l'app intera si blocca.

Niente DB vero: si inietta una connessione finta la cui query scoppia come sul DB
di produzione, e si verifica che il rilascio avvenga lo stesso.
  - handler dal pool (_get_conn/_release_conn): si controlla _release_conn
  - handler con psycopg2.connect grezzo: si controlla conn.close()
"""
import os
import flask
import psycopg2
import pytest

import routes.admin as admin


def _client():
    app = flask.Flask(__name__)
    app.register_blueprint(admin.bp)
    return app.test_client()


class _CursoreCheScoppia:
    def execute(self, *a, **k):
        raise RuntimeError("errore query su DB")

    def close(self):
        pass


class _ConnFinta:
    def __init__(self):
        self.rilasciata = False
        self.chiusa = False

    def cursor(self):
        return _CursoreCheScoppia()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.chiusa = True


def test_handler_pool_rilascia_connessione_su_errore(monkeypatch):
    # handler dal pool: admin_stato_madri prende conn, poi cur.execute scoppia.
    monkeypatch.setenv("ADMIN_SECRET", "segreto-test")
    finta = _ConnFinta()
    rilasci = []
    monkeypatch.setattr(admin, "_get_conn", lambda: finta)
    monkeypatch.setattr(admin, "_release_conn", lambda c: rilasci.append(c))

    resp = _client().get("/admin/stato-madri?s=segreto-test&ids=fen-x")

    assert resp.status_code == 500          # l'errore resta un errore onesto
    assert finta in rilasci                 # ...ma la connessione è tornata al pool


def test_handler_psycopg2_chiude_connessione_su_errore(monkeypatch):
    # handler con psycopg2.connect grezzo: admin_conta_portate prende conn, cur.execute scoppia.
    monkeypatch.setenv("ADMIN_SECRET", "segreto-test")
    monkeypatch.setenv("DATABASE_URL", "postgres://finto")  # serve all'argomento di connect()
    finta = _ConnFinta()
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: finta)

    resp = _client().get("/admin/conta-portate?s=segreto-test")

    assert "errore" in resp.get_json()      # errore gestito
    assert finta.chiusa is True             # ...e la connessione è stata chiusa (niente leak)
