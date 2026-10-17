"""Rete di test — audit READ-ONLY delle fonti sospette (/admin/audit-fonti).
Verifica il GATE (senza segreto -> 403) e le EURISTICHE pure (sospetta sì/no)
su data finti, offline (niente DB né rete: la connessione è monkeypatchata).
Se questa rete diventa rossa, o il cancello si è aperto o un'euristica è regredita.
"""
import contextlib

import flask

import routes.audit_fonti as af
from routes.audit_fonti import (
    fonte_e_citabile,
    fonte_sembra_ai,
    cas_valido,
    cas_presente,
    classifica_fonte,
    classifica_cas,
    audita_nodo,
    audita_righe,
)


def _app():
    app = flask.Flask(__name__)
    app.register_blueprint(af.bp_audit_fonti)
    return app.test_client()


# ── GATE ────────────────────────────────────────────────────────────────────

def test_senza_segreto_e_403(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "topolino")
    resp = _app().get("/admin/audit-fonti")
    assert resp.status_code == 403
    assert "errore" in resp.get_json()


def test_segreto_sbagliato_e_403(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "topolino")
    resp = _app().get("/admin/audit-fonti?s=paperino")
    assert resp.status_code == 403


def test_senza_admin_secret_configurato_e_403(monkeypatch):
    # se ADMIN_SECRET non è impostato, l'endpoint resta chiuso (non si apre a tutti)
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    resp = _app().get("/admin/audit-fonti?s=qualunque")
    assert resp.status_code == 403


# ── EURISTICA: fonte citabile vs no ──────────────────────────────────────────

def test_usda_e_citabile():
    assert fonte_e_citabile("USDA FDC 167747") is True

def test_ciqual_wikidata_ahn_matter_citabili():
    assert fonte_e_citabile("CIQUAL 2020") is True
    assert fonte_e_citabile("Wikidata Q12345") is True
    assert fonte_e_citabile("Ahn flavor network") is True
    assert fonte_e_citabile("scala Matter / banco") is True

def test_fonte_inventata_non_e_citabile():
    assert fonte_e_citabile("Food Chemistry / McGee") is False

def test_fonte_vuota_non_e_citabile():
    assert fonte_e_citabile("") is False
    assert fonte_e_citabile(None) is False


# ── EURISTICA: impronta di citazione AI ──────────────────────────────────────

def test_anno_e_impronta_ai():
    assert fonte_sembra_ai("Food Chemistry 2019 / McGee") is True

def test_et_al_e_impronta_ai():
    assert fonte_sembra_ai("Belitz et al.") is True

def test_nome_modello_e_impronta_ai():
    assert fonte_sembra_ai("generato con GPT-4") is True
    assert fonte_sembra_ai("Claude") is True

def test_termine_biblio_e_impronta_ai():
    assert fonte_sembra_ai("Journal of Agricultural and Food Chemistry") is True

def test_token_breve_non_e_impronta_ai():
    # una sigla breve senza anno/autore/modello NON scatta come citazione AI
    assert fonte_sembra_ai("lotto-A") is False
    assert fonte_sembra_ai("") is False
    assert fonte_sembra_ai(None) is False


# ── EURISTICA: CAS valido / malformato ───────────────────────────────────────

def test_cas_valido_caffeina():
    # 58-08-2 (caffeina): checksum corretto
    assert cas_valido("58-08-2") is True

def test_cas_valido_limonene():
    # 5989-27-5 (D-limonene)
    assert cas_valido("5989-27-5") is True

def test_cas_formato_sbagliato_e_invalido():
    assert cas_valido("12345") is False
    assert cas_valido("abc-de-f") is False
    assert cas_valido("58/08/2") is False

def test_cas_checksum_sbagliato_e_invalido():
    # formato giusto ma cifra di controllo errata (58-08-2 reale -> 58-08-3 finto)
    assert cas_valido("58-08-3") is False

def test_cas_presente_ignora_nulli():
    assert cas_presente(None) is False
    assert cas_presente("null") is False
    assert cas_presente("") is False
    assert cas_presente("N/A") is False
    assert cas_presente("58-08-2") is True


# ── classifica_fonte: sospetta sì / no, con motivo giusto ────────────────────

def test_classifica_fonte_citabile_e_pulita():
    assert classifica_fonte("USDA FDC 167747", disclosed=False) is None

def test_classifica_fonte_ai_sempre_sospetta_anche_se_dichiarata():
    # impronta AI: segnalata ANCHE se il nodo dichiara la stima (residuo da pulire)
    assert classifica_fonte("Food Chemistry 2019 / McGee", disclosed=True) == "fonte_testo_libero_ai"
    assert classifica_fonte("Food Chemistry 2019 / McGee", disclosed=False) == "fonte_testo_libero_ai"

def test_classifica_fonte_non_citabile_solo_se_non_dichiarata():
    assert classifica_fonte("appunti interni", disclosed=False) == "fonte_non_citabile"
    # se dichiarata stima -> conservativo, niente rumore
    assert classifica_fonte("appunti interni", disclosed=True) is None

def test_classifica_fonte_vuota_o_assente_pulita():
    assert classifica_fonte("", disclosed=False) is None
    assert classifica_fonte(None, disclosed=False) is None


# ── classifica_cas ───────────────────────────────────────────────────────────

def test_classifica_cas_valido_pulito():
    assert classifica_cas("58-08-2") is None

def test_classifica_cas_malformato():
    assert classifica_cas("1234567") == "cas_malformato"

def test_classifica_cas_checksum_errato_segnalato():
    assert classifica_cas("58-08-3") == "cas_malformato"

def test_classifica_cas_nullo_pulito():
    assert classifica_cas(None) is None
    assert classifica_cas("null") is None


# ── audita_nodo: aggregazione per nodo ───────────────────────────────────────

def test_audita_nodo_fonte_top_level():
    sosp = audita_nodo("ing-x", "Ingrediente X", {"fonte": "McGee 2019"})
    assert len(sosp) == 1
    assert sosp[0] == {
        "id": "ing-x", "nome": "Ingrediente X", "campo": "fonte",
        "valore_fonte": "McGee 2019", "motivo": "fonte_testo_libero_ai",
    }

def test_audita_nodo_composti_fonte_e_cas():
    dd = {"composti_aromatici": [
        {"nome": "limonene", "cas": "5989-27-5", "fonte": "USDA"},   # tutto pulito
        {"nome": "x", "cas": "99-99-9", "fonte": "Belitz et al."},   # cas malformato + fonte AI
    ]}
    sosp = audita_nodo("ing-y", "Y", dd)
    campi = {s["campo"]: s["motivo"] for s in sosp}
    assert campi == {
        "composti_aromatici[1].fonte": "fonte_testo_libero_ai",
        "composti_aromatici[1].cas": "cas_malformato",
    }

def test_audita_nodo_meta_fonte_usda_pulita():
    dd = {"proprieta_meta": {"dolce": {"stato": "derivato", "fonte": "USDA FDC 171688"}}}
    assert audita_nodo("ing-mela", "Mela", dd) == []

def test_audita_nodo_data_non_dict_non_rompe():
    assert audita_nodo("x", "X", None) == []
    assert audita_nodo("x", "X", "stringa") == []
    assert audita_nodo("x", "X", ["lista"]) == []

def test_audita_nodo_senza_fonte_e_pulito():
    assert audita_nodo("ing-sale", "Sale", {"nomi": {"it": "sale"}}) == []


# ── audita_righe: report completo ────────────────────────────────────────────

def test_audita_righe_report():
    righe = [
        ("ing-limone", "Ingrediente", "Limone", {"fonte": "Food Chemistry 2019 / McGee"}),
        ("ing-sale", "Ingrediente", "Sale", {"nomi": {"it": "sale"}}),
        ("ing-mela", "Prodotto", "Mela", {"fonte": "USDA FDC 171688"}),
        ("ing-z", "Ingrediente", "Z", {"composti_aromatici": [{"cas": "11-11-1", "fonte": "note"}]}),
    ]
    r = audita_righe(righe)
    assert r["totale_esaminati"] == 4
    # sospetti: limone (fonte AI), z (cas malformato + fonte non citabile)
    assert r["per_motivo"].get("fonte_testo_libero_ai") == 1
    assert r["per_motivo"].get("cas_malformato") == 1
    assert r["per_motivo"].get("fonte_non_citabile") == 1
    assert len(r["sospetti"]) == 3
    assert "criterio" in r


# ── ENDPOINT end-to-end con connessione monkeypatchata (niente DB reale) ─────

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, sql, params=()):
        # blinda l'onestà: l'audit deve restare SOLO lettura
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
        ("ing-limone", "Ingrediente", "Limone", {"fonte": "Food Chemistry 2019 / McGee"}),
        ("ing-sale", "Ingrediente", "Sale", {"nomi": {"it": "sale"}}),
    ]

    @contextlib.contextmanager
    def _fake_conn():
        yield _FakeConn(rows)

    monkeypatch.setattr(af, "connessione", _fake_conn)
    resp = _app().get("/admin/audit-fonti?s=topolino")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["totale_esaminati"] == 2
    assert len(body["sospetti"]) == 1
    assert body["sospetti"][0]["id"] == "ing-limone"
    assert body["sospetti"][0]["motivo"] == "fonte_testo_libero_ai"
    assert body["per_motivo"]["fonte_testo_libero_ai"] == 1
