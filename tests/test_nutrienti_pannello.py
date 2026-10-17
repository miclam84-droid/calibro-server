# Test del pannello nutrizionale completo: estrazione da USDA (pura) + esposizione.
# Nessun DB, nessuna rete. Verifica l'ONESTÀ: solo campi presenti, energia solo in kcal.
from routes.deriva_gusti import _pannello_nutrienti
from routes.nutrizionale import estrai_pannello

# Dettaglio USDA finto ma realistico (mela), con energia sia in KCAL sia in kJ.
DETAIL_MELA = {"description": "Apples, raw", "foodNutrients": [
    {"nutrient": {"name": "Energy", "unitName": "kJ"}, "amount": 218},
    {"nutrient": {"name": "Energy", "unitName": "KCAL"}, "amount": 52},
    {"nutrient": {"name": "Protein"}, "amount": 0.26},
    {"nutrient": {"name": "Carbohydrate, by difference"}, "amount": 13.81},
    {"nutrient": {"name": "Fiber, total dietary"}, "amount": 2.4},
    {"nutrient": {"name": "Total lipid (fat)"}, "amount": 0.17},
    {"nutrient": {"name": "Fatty acids, total saturated"}, "amount": 0.028},
    {"nutrient": {"name": "Sugars, total including NLEA"}, "amount": 10.39},
    {"nutrient": {"name": "Sodium, Na"}, "amount": 1},
]}


def test_pannello_prende_kcal_non_kj():
    p = _pannello_nutrienti(DETAIL_MELA)
    assert p["energia_kcal"] == {"valore": 52.0, "unita": "kcal/100g"}  # kcal, mai i kJ


def test_pannello_campi_completi():
    p = _pannello_nutrienti(DETAIL_MELA)
    assert p["proteine"]["valore"] == 0.26
    assert p["carboidrati"]["valore"] == 13.81
    assert p["fibre"]["valore"] == 2.4
    assert p["grassi"]["valore"] == 0.17
    assert p["grassi_saturi"]["valore"] == 0.03   # arrotondato a 2
    assert p["zuccheri"]["valore"] == 10.39
    assert p["sodio"] == {"valore": 1.0, "unita": "mg/100g"}


def test_pannello_salta_campi_mancanti_niente_zero():
    detail = {"foodNutrients": [
        {"nutrient": {"name": "Protein"}, "amount": 2.0},
        {"nutrient": {"name": "Carbohydrate, by difference"}, "amount": None},  # assente
    ]}
    p = _pannello_nutrienti(detail)
    assert "proteine" in p
    assert "carboidrati" not in p   # niente zero inventato per un dato assente
    assert "fibre" not in p
    assert "energia_kcal" not in p  # nessuna energia -> nessuna conversione dai kJ


def test_pannello_vuoto_su_detail_vuoto():
    assert _pannello_nutrienti({}) == {}
    assert _pannello_nutrienti({"foodNutrients": []}) == {}


def test_zuccheri_fallback_total_sugars():
    detail = {"foodNutrients": [{"nutrient": {"name": "Total Sugars"}, "amount": 5.5}]}
    assert _pannello_nutrienti(detail)["zuccheri"]["valore"] == 5.5


# --- esposizione sul nodo (nutrizionale.estrai_pannello) ---

def test_estrai_pannello_ordine_e_fonte():
    data = {"nutrienti": {
        "energia_kcal": {"valore": 52.0, "unita": "kcal/100g"},
        "proteine": {"valore": 0.26, "unita": "g/100g"},
        "grassi": {"valore": 0.17, "unita": "g/100g"},
    }, "nutrienti_meta": {"stato": "derivato", "fonte": "USDA FDC 171688"}}
    righe, fonte = estrai_pannello(data)
    assert fonte == "USDA FDC 171688"
    campi = [r["chiave"] for r in righe]
    # ordine etichetta: energia, grassi, ... , proteine
    assert campi == ["energia_kcal", "grassi", "proteine"]
    assert all(r["fonte"] == "USDA FDC 171688" for r in righe)


def test_estrai_pannello_senza_fonte_non_mostra():
    # senza fonte citata, niente numeri esposti (onestà)
    data = {"nutrienti": {"proteine": {"valore": 1.0, "unita": "g/100g"}}, "nutrienti_meta": {}}
    righe, fonte = estrai_pannello(data)
    assert righe == []
    assert fonte is None


def test_estrai_pannello_nodo_senza_blocco():
    righe, fonte = estrai_pannello({"proprieta": {"dolce": 5}})
    assert righe == [] and fonte is None
