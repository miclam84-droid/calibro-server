"""Rete di test — guardie della ricerca USDA.
Impediscono i match sbagliati (es. "aceto di bambù" -> "Bamboo shoots",
"acido ascorbico" -> una mela ricca di vit. C). Funzioni pure, niente rete.
"""
from routes.deriva_gusti_search import (
    _non_sensoriale, _usda_composito, _match_tok, _score, _stem,
)


def test_non_sensoriale_additivi_saltati():
    assert _non_sensoriale("acido ascorbico") is True
    assert _non_sensoriale("amido di mais") is True
    assert _non_sensoriale("lecitina di soia") is True


def test_non_sensoriale_cibo_vero_passa():
    assert _non_sensoriale("limone") is False
    assert _non_sensoriale("pomodoro san marzano") is False


def test_usda_composito():
    assert _usda_composito("Beverages, Acai berry drink, fortified") is True
    assert _usda_composito("Cereal, with added fruit") is True
    assert _usda_composito("Lemon juice, raw") is False


def test_stem_plurali():
    assert _stem("strawberries") == "strawberry"
    assert _stem("tomatoes") == "tomato"
    assert _stem("carrots") == "carrot"


def test_match_tok_plurali():
    assert _match_tok("strawberries", "strawberry") is True
    assert _match_tok("tomato", "tomatoes") is True
    assert _match_tok("apple", "banana") is False


def test_score_match_buono_batte_scarso():
    buono, testa = _score("lemon juice", "Lemon juice, raw")
    assert buono >= 0.9 and testa is True
    scarso, _ = _score("bamboo vinegar", "Bamboo shoots, raw")
    assert scarso < buono
