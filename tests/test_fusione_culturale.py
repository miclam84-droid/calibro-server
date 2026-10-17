# -*- coding: utf-8 -*-
"""Rete di test — logica PURA del ponte aromatico (Ondata 3: fusione culturale).

Niente DB, niente rete: solo l'aritmetica dei composti condivisi + IDF.
Se diventano rosse, la regola del ponte (soglia, peso per rarita', ordinamento)
e' cambiata. Il ponte deve basarsi SEMPRE su composti realmente condivisi:
questi test lo blindano.
"""
from routes.fusione_culturale import ponti_aromatici, _nome_composto


def test_nome_composto_pulisce_prefissi():
    assert _nome_composto("comp_pub_1_octanol") == "1 octanol"
    assert _nome_composto("comp_jasmone") == "jasmone"


def test_soglia_min_condivisi_esclude_i_deboli():
    base = {"c1", "c2", "c3"}
    partner = {
        "forte": {"c1", "c2", "c3"},   # 3 condivisi -> passa
        "debole": {"c1", "c9"},        # 1 condiviso -> scartato con min_shared=3
    }
    df = {"c1": 2, "c2": 2, "c3": 2, "c9": 2}
    out = ponti_aromatici(base, partner, df, n_tot=100, min_shared=3)
    nomi = [p["ingrediente"] for p in out]
    assert "forte" in nomi
    assert "debole" not in nomi


def test_base_vuota_nessun_ponte():
    assert ponti_aromatici(set(), {"x": {"c1", "c2", "c3"}}, {"c1": 1}, 50) == []


def test_idf_premia_i_composti_rari():
    # due partner con lo STESSO numero di composti condivisi (3), stesso profilo,
    # ma uno condivide composti RARI (df basso) e l'altro composti COMUNI (df alto).
    # L'IDF deve mettere il raro davanti.
    base = {"raro1", "raro2", "raro3", "comune1", "comune2", "comune3"}
    partner = {
        "caratterizzante": {"raro1", "raro2", "raro3"},
        "banale": {"comune1", "comune2", "comune3"},
    }
    df = {"raro1": 2, "raro2": 2, "raro3": 2,
          "comune1": 900, "comune2": 900, "comune3": 900}
    out = ponti_aromatici(base, partner, df, n_tot=1000, min_shared=3)
    assert out[0]["ingrediente"] == "caratterizzante"
    # il banale ha indice di rarita' quasi nullo (composti ovunque)
    banale = [p for p in out if p["ingrediente"] == "banale"][0]
    carat = out[0]
    assert carat["indice_rarita"] > banale["indice_rarita"]


def test_composti_condivisi_ordinati_dal_piu_raro():
    base = {"a", "b", "c"}
    partner = {"p": {"a", "b", "c"}}
    df = {"a": 500, "b": 10, "c": 3}   # c piu' raro, poi b, poi a
    out = ponti_aromatici(base, partner, df, n_tot=1000, min_shared=3)
    assert out[0]["composti_condivisi"][:3] == ["c", "b", "a"]


def test_il_perche_cita_i_composti_reali():
    base = {"vanillin", "eugenol", "limonene"}
    partner = {"p": {"vanillin", "eugenol", "limonene"}}
    df = {"vanillin": 5, "eugenol": 7, "limonene": 9}
    out = ponti_aromatici(base, partner, df, n_tot=500, min_shared=3)
    p = out[0]
    # ogni composto nel 'perche' deve venire dai composti realmente condivisi
    for nome in p["composti_condivisi"]:
        assert nome in base  # qui i nomi coincidono con gli id (niente prefisso comp_)
    assert "condivide composti" in p["perche"]
    assert p["n_condivisi"] == 3


def test_ordinamento_per_forza_del_ponte():
    base = {"c1", "c2", "c3", "c4", "c5"}
    partner = {
        "molti": {"c1", "c2", "c3", "c4", "c5"},  # 5 condivisi
        "pochi": {"c1", "c2", "c3"},              # 3 condivisi
    }
    df = {c: 3 for c in base}
    out = ponti_aromatici(base, partner, df, n_tot=200, min_shared=3)
    assert out[0]["ingrediente"] == "molti"


def test_limite_rispettato():
    base = {"c1", "c2", "c3"}
    partner = {f"p{i}": {"c1", "c2", "c3"} for i in range(20)}
    df = {"c1": 3, "c2": 3, "c3": 3}
    out = ponti_aromatici(base, partner, df, n_tot=200, min_shared=3, limit=5)
    assert len(out) == 5
