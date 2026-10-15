"""Rete di test — curve di derivazione del gusto (onestà dei numeri).
Funzioni pure, niente DB né rete. Se diventano rosse, una formula è cambiata
o si è rotta: il numero del gusto è il cuore della tesi di Matter.
"""
from routes.deriva_gusti import _interp, _deriva, _DOLCE


def test_interp_estremi():
    assert _interp(-10, _DOLCE) == 0     # sotto il minimo -> primo valore
    assert _interp(0, _DOLCE) == 0
    assert _interp(1000, _DOLCE) == 10   # sopra il massimo -> ultimo valore


def test_interp_monotono():
    # più zucchero -> dolce non decresce mai
    vals = [_interp(x, _DOLCE) for x in (0, 5, 12, 30, 60, 80)]
    assert vals == sorted(vals)


def test_deriva_zucchero_alto_dolce_alto():
    d = _deriva({"Total Sugars": 80.0})
    assert d["dolce"]["val"] >= 9     # zucchero quasi puro -> dolce in cima
    assert d["salato"]["val"] == 0
    assert d["grasso"]["val"] == 0


def test_deriva_sale_alto_salato_alto():
    assert _deriva({"Sodium, Na": 15000.0})["salato"]["val"] == 10


def test_deriva_grasso_alto():
    assert _deriva({"Total lipid (fat)": 60.0})["grasso"]["val"] == 10


def test_deriva_vuoto_tutto_zero():
    d = _deriva({})
    assert d["dolce"]["val"] == 0
    assert d["salato"]["val"] == 0
    assert d["grasso"]["val"] == 0


def test_deriva_zuccheri_pesati_fruttosio_piu_dolce():
    # a parità di grammi il fruttosio (peso 1.3) deve pesare più del saccarosio (1.0)
    fru = _deriva({"Fructose": 30.0})["dolce"]["grezzo"]
    sacc = _deriva({"Sucrose": 30.0})["dolce"]["grezzo"]
    assert fru > sacc
