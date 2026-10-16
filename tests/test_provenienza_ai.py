"""Rete di test — marca_provenienza_ai (onestà dei dati).
Funzione pura di build_ingredient_graph.py. Tutto ciò che il modello (gpt-4o-mini)
genera è una STIMA: CAS, soglie ppb, parametri fisici, profilo sensoriale. Una
'fonte' inventata che sembra autorevole è il buco peggiore e non deve MAI finire
nel nodo. Questa rete blinda quel fix: se diventa rossa, l'onestà dei dati è
regredita.

Nota import: build_ingredient_graph importa psycopg2 a livello modulo (dipendenza
reale pinnata in requirements.txt, presente in CI). Non apre connessioni
all'import. Se psycopg2 manca nell'ambiente locale, i test si saltano invece di
rompersi (nessun DB né rete viene toccato comunque).
"""
import copy
import pytest

pytest.importorskip("psycopg2", reason="build_ingredient_graph importa psycopg2 a livello modulo")
from build_ingredient_graph import marca_provenienza_ai


def _profilo_tipo():
    return {
        "nomi": {"it": "limone"},
        "fonte": "Food Chemistry 2019 / McGee",   # fonte INVENTATA dal modello
        "composti_aromatici": [
            {"nome": "limonene", "cas": "138-86-3", "fonte": "McGee"},
            {"nome": "citrale", "cas": "5392-40-5"},
        ],
    }


def test_rimuove_fonte_top_level():
    out = marca_provenienza_ai(_profilo_tipo())
    assert "fonte" not in out


def test_rimuove_fonte_dentro_ogni_composto():
    out = marca_provenienza_ai(_profilo_tipo())
    for c in out["composti_aromatici"]:
        assert "fonte" not in c


def test_tagga_ogni_composto_stimato_ai():
    out = marca_provenienza_ai(_profilo_tipo())
    assert all(c["stato"] == "stimato_AI" for c in out["composti_aromatici"])


def test_blocco_provenienza_presente_e_marcato():
    out = marca_provenienza_ai(_profilo_tipo())
    prov = out.get("provenienza")
    assert isinstance(prov, dict)
    assert prov["stato"] == "stimato_AI"
    assert prov["modello"] == "gpt-4o-mini"
    assert "nota" in prov and prov["nota"]


def test_non_tocca_altri_campi():
    out = marca_provenienza_ai(_profilo_tipo())
    assert out["nomi"] == {"it": "limone"}
    # i dati del composto diversi da 'fonte' restano
    assert out["composti_aromatici"][0]["nome"] == "limonene"
    assert out["composti_aromatici"][0]["cas"] == "138-86-3"


# ── edge case: non deve mai sollevare, deve restare conservativa ──

def test_profilo_non_dict_ritorna_invariato():
    assert marca_provenienza_ai(None) is None
    assert marca_provenienza_ai("x") == "x"
    assert marca_provenienza_ai(["lista"]) == ["lista"]


def test_composti_none_non_rompe():
    out = marca_provenienza_ai({"composti_aromatici": None})
    assert out["composti_aromatici"] is None
    assert out["provenienza"]["stato"] == "stimato_AI"


def test_composti_non_lista_non_rompe():
    out = marca_provenienza_ai({"composti_aromatici": {"nope": 1}})
    # non essendo una lista, non viene iterato: resta com'è, senza eccezioni
    assert out["composti_aromatici"] == {"nope": 1}
    assert out["provenienza"]["stato"] == "stimato_AI"


def test_composto_non_dict_saltato_senza_errore():
    out = marca_provenienza_ai({"composti_aromatici": ["stringa", 42, {"nome": "x", "fonte": "y"}]})
    composti = out["composti_aromatici"]
    assert composti[0] == "stringa" and composti[1] == 42
    # il dict valido viene comunque taggato e ripulito
    assert composti[2]["stato"] == "stimato_AI" and "fonte" not in composti[2]


def test_senza_fonte_aggiunge_comunque_provenienza():
    out = marca_provenienza_ai({"nomi": {"it": "sale"}})
    assert out["provenienza"]["stato"] == "stimato_AI"
    assert "fonte" not in out
