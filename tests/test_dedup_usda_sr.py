"""Rete di test — regole di dedup USDA SR Legacy (funzioni pure, niente rete/DB).
Verificano che la dedup collassi stato/cottura dello stesso alimento ma NON
unisca tagli/tipi/specie diversi (un falso merge = un profilo di gusto falso).
"""
from usda_sr_dedup import (
    is_segmento_stato, base_key, is_categoria_composita, is_raw,
    scegli_canonico, dedup,
)


def test_segmento_stato_riconosce_stato_e_cottura():
    assert is_segmento_stato("raw") is True
    assert is_segmento_stato("cooked, boiled") is True  # (passato come singolo pezzo)
    assert is_segmento_stato("without salt") is True
    assert is_segmento_stato('trimmed to 1/8" fat') is True
    assert is_segmento_stato("80%") is True


def test_segmento_stato_non_scarta_cibo_vero():
    assert is_segmento_stato("chuck") is False
    assert is_segmento_stato("San Marzano") is False
    assert is_segmento_stato("Atlantic") is False


def test_base_key_collassa_cottura_stesso_alimento():
    # stesso alimento, stati diversi -> stessa chiave
    assert base_key("Apples, raw, with skin") == base_key("Apples, cooked, boiled, with skin")
    assert base_key("Asparagus, raw") == base_key("Asparagus, cooked, boiled, drained, without salt")


def test_base_key_tiene_distinti_tagli_e_tipi():
    # tagli/tipi diversi -> chiavi diverse (NON si fondono)
    assert base_key("Beef, chuck, blade roast, raw") != base_key("Beef, rib, small end, raw")
    assert base_key("Rice, white, long-grain, raw") != base_key("Rice, brown, long-grain, raw")


def test_categoria_composita():
    assert is_categoria_composita("Fast Foods") is True
    assert is_categoria_composita("Baby Foods") is True
    assert is_categoria_composita("Vegetables and Vegetable Products") is False


def test_scegli_canonico_preferisce_raw():
    membri = [
        {"fdc_id": "200", "description": "Carrots, cooked, boiled, drained"},
        {"fdc_id": "100", "description": "Carrots, frozen, unprepared"},
        {"fdc_id": "150", "description": "Carrots, raw"},
    ]
    assert scegli_canonico(membri)["fdc_id"] == "150"


def test_scegli_canonico_senza_raw_prende_fdc_min():
    membri = [
        {"fdc_id": "300", "description": "Carrots, cooked, boiled"},
        {"fdc_id": "120", "description": "Carrots, frozen, unprepared"},
    ]
    assert scegli_canonico(membri)["fdc_id"] == "120"


def test_dedup_raggruppa_e_filtra_composite():
    righe = [
        {"fdc_id": "1", "description": "Apples, raw, with skin", "cat": "Fruits and Fruit Juices"},
        {"fdc_id": "2", "description": "Apples, cooked, boiled", "cat": "Fruits and Fruit Juices"},
        {"fdc_id": "3", "description": "Pizza, cheese", "cat": "Fast Foods"},
    ]
    tutte = dedup(righe, key_cat="cat")
    assert len(tutte) == 2  # mele (collassate) + pizza
    solo_mp = dedup(righe, key_cat="cat", solo_materia_prima=True)
    assert len(solo_mp) == 1  # la pizza (Fast Foods) è esclusa
    assert "pizza" not in " ".join(solo_mp.keys())


def test_is_raw():
    assert is_raw("Cod, Atlantic, raw") is True
    assert is_raw("Cod, Atlantic, cooked, dry heat") is False
