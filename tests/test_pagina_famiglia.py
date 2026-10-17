# -*- coding: utf-8 -*-
"""Test PURI dell'aggregatore per-famiglia botanica — niente rete, niente DB.
Lavorano su NODI FINTI (nome, data) con la forma reale scritta da
tassonomia_wikidata.py: data["tassonomia"]["famiglia"].

Tesi del prodotto: ONESTA' DEI DATI — un ingrediente senza famiglia classificata
NON riceve una famiglia inventata, finisce in 'Non classificato'.
"""
import json

from routes.pagina_famiglia import (
    _estrai_famiglia,
    _slug,
    _aggrega_famiglie,
    _ingredienti_di_famiglia,
    NON_CLASSIFICATO,
    SLUG_NON_CLASS,
)


def _nodo(nome, famiglia=None, as_json=False):
    """Nodo finto (nome, data). Con famiglia=None il nodo e' senza tassonomia."""
    if famiglia is None:
        data = {"profilo": {}}
    else:
        data = {"tassonomia": {"famiglia": famiglia, "genere": "X"},
                "tassonomia_meta": {"stato": "classificato"}}
    return (nome, json.dumps(data) if as_json else data)


# --- ESTRAZIONE FAMIGLIA DAL NODO -----------------------------------------------

def test_estrai_famiglia_da_dict():
    assert _estrai_famiglia({"tassonomia": {"famiglia": "Solanaceae"}}) == "Solanaceae"


def test_estrai_famiglia_da_json_string():
    s = json.dumps({"tassonomia": {"famiglia": "Cucurbitaceae"}})
    assert _estrai_famiglia(s) == "Cucurbitaceae"


def test_estrai_famiglia_assente_e_none():
    assert _estrai_famiglia({}) is None
    assert _estrai_famiglia({"tassonomia": {}}) is None           # tassonomia senza famiglia
    assert _estrai_famiglia({"tassonomia": {"famiglia": "  "}}) is None  # stringa vuota
    assert _estrai_famiglia(None) is None
    assert _estrai_famiglia("non-un-json") is None
    assert _estrai_famiglia({"tassonomia": "boh"}) is None          # tassonomia non dict


def test_estrai_famiglia_trimma():
    assert _estrai_famiglia({"tassonomia": {"famiglia": "  Lamiaceae "}}) == "Lamiaceae"


# --- SLUG ------------------------------------------------------------------------

def test_slug_stabile():
    assert _slug("Solanaceae") == "solanaceae"
    assert _slug("Non classificato") == "non-classificato"
    assert _slug(NON_CLASSIFICATO) == SLUG_NON_CLASS


# --- AGGREGAZIONE ----------------------------------------------------------------

def _grafo_finto():
    return [
        _nodo("pomodoro", "Solanaceae"),
        _nodo("melanzana", "Solanaceae"),
        _nodo("peperone", "Solanaceae"),
        _nodo("zucchina", "Cucurbitaceae"),
        _nodo("cetriolo", "Cucurbitaceae", as_json=True),   # anche come JSON string
        _nodo("basilico", "Lamiaceae"),
        _nodo("sale", None),                                # senza famiglia
        _nodo("bicarbonato", None),
    ]


def test_aggrega_conteggi_corretti():
    fam = _aggrega_famiglie(_grafo_finto())
    per_slug = {f["slug"]: f for f in fam}
    assert per_slug["solanaceae"]["conteggio"] == 3
    assert per_slug["cucurbitaceae"]["conteggio"] == 2
    assert per_slug["lamiaceae"]["conteggio"] == 1
    assert per_slug[SLUG_NON_CLASS]["conteggio"] == 2


def test_aggrega_ordina_per_conteggio_poi_non_classificato_in_fondo():
    fam = _aggrega_famiglie(_grafo_finto())
    nomi = [f["famiglia"] for f in fam]
    # Solanaceae (3) prima di Cucurbitaceae (2) prima di Lamiaceae (1)
    assert nomi.index("Solanaceae") < nomi.index("Cucurbitaceae") < nomi.index("Lamiaceae")
    # 'Non classificato' SEMPRE ultimo, anche se ha piu' elementi di una famiglia
    assert nomi[-1] == NON_CLASSIFICATO


def test_aggrega_non_classificato_marcato():
    fam = _aggrega_famiglie(_grafo_finto())
    nc = [f for f in fam if f["slug"] == SLUG_NON_CLASS][0]
    assert nc["classificata"] is False
    assert all(f["classificata"] for f in fam if f["slug"] != SLUG_NON_CLASS)


def test_aggrega_preserva_la_forma():
    fam = _aggrega_famiglie(_grafo_finto())
    for f in fam:
        assert set(f.keys()) == {"famiglia", "slug", "conteggio", "classificata"}


def test_aggrega_non_inventa_quando_tutti_senza_famiglia():
    fam = _aggrega_famiglie([_nodo("sale", None), _nodo("acqua", None)])
    assert len(fam) == 1
    assert fam[0]["slug"] == SLUG_NON_CLASS and fam[0]["conteggio"] == 2


def test_aggrega_vuoto():
    assert _aggrega_famiglie([]) == []


# --- INGREDIENTI DI UNA FAMIGLIA -------------------------------------------------

def test_ingredienti_di_famiglia_per_slug():
    disp, nomi = _ingredienti_di_famiglia(_grafo_finto(), "solanaceae")
    assert disp == "Solanaceae"
    assert nomi == ["melanzana", "peperone", "pomodoro"]  # ordinati, dedup


def test_ingredienti_di_famiglia_case_insensitive_e_nome_pieno():
    # accetta tanto lo slug quanto il nome con grafia diversa
    _, a = _ingredienti_di_famiglia(_grafo_finto(), "SOLANACEAE")
    _, b = _ingredienti_di_famiglia(_grafo_finto(), "Solanaceae")
    assert a == b == ["melanzana", "peperone", "pomodoro"]


def test_ingredienti_non_classificato():
    disp, nomi = _ingredienti_di_famiglia(_grafo_finto(), SLUG_NON_CLASS)
    assert disp == NON_CLASSIFICATO
    assert nomi == ["bicarbonato", "sale"]


def test_ingredienti_famiglia_inesistente_vuota():
    disp, nomi = _ingredienti_di_famiglia(_grafo_finto(), "rosaceae")
    assert nomi == []


def test_ingredienti_dedup():
    nodi = [_nodo("pomodoro", "Solanaceae"), _nodo("pomodoro", "Solanaceae")]
    _, nomi = _ingredienti_di_famiglia(nodi, "solanaceae")
    assert nomi == ["pomodoro"]
