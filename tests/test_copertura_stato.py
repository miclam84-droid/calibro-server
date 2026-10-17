"""Test PURI (nessun DB) per routes/copertura_stato.aggrega_copertura.
Verificano l'onestà del numero di copertura: i conteggi sono quelli veri,
«misurato» richiede grezzo + fonte, dove è 0 resta 0, e le percentuali non
sono mai gonfiate (sempre sul totale reale)."""
import json

from routes.copertura_stato import aggrega_copertura, ASSI, _famiglia_fonte


def _nodo_valore(asse, val):
    """Nodo con un valore sull'asse ma SENZA grezzo/fonte (stima AI)."""
    return {"proprieta": {asse: val}}


def _nodo_misurato(asse, val, grezzo, fonte):
    return {"proprieta": {asse: val},
            "proprieta_meta": {asse: {"stato": "derivato", "fonte": fonte, "grezzo": grezzo}}}


def test_totale_conta_tutte_le_righe():
    r = aggrega_copertura([{}, {}, {"proprieta": {"dolce": 5}}])
    assert r["totale_ingredienti"] == 3


def test_per_asse_conta_il_valore_anche_se_solo_stima():
    r = aggrega_copertura([_nodo_valore("dolce", 7), _nodo_valore("dolce", 2), {}])
    assert r["per_asse"]["dolce"] == 2
    # senza grezzo+fonte NON è misurato
    assert r["per_asse_misurato"]["dolce"] == 0


def test_misurato_richiede_grezzo_e_fonte():
    nodi = [
        _nodo_misurato("salato", 5, 500.0, "USDA FDC 170848"),   # misurato
        {"proprieta": {"salato": 3},
         "proprieta_meta": {"salato": {"stato": "derivato", "grezzo": 200.0}}},  # grezzo ma senza fonte
        {"proprieta": {"salato": 4},
         "proprieta_meta": {"salato": {"stato": "stimato", "fonte": "x"}}},      # fonte ma senza grezzo
    ]
    r = aggrega_copertura(nodi)
    assert r["per_asse"]["salato"] == 3
    assert r["per_asse_misurato"]["salato"] == 1  # solo il primo


def test_tutti_e_sei_gli_assi_sempre_presenti_anche_a_zero():
    r = aggrega_copertura([{}])
    assert set(r["per_asse"].keys()) == set(ASSI)
    assert len(ASSI) == 6
    # amaro non ha pipeline di misura: deve uscire 0, non sparire (0 è informazione)
    assert r["per_asse"]["amaro"] == 0
    assert r["per_asse_misurato"]["amaro"] == 0


def test_pannello_nutrienti_conta_solo_valori_reali():
    nodi = [
        {"nutrienti": {"energia_kcal": {"valore": 250, "unita": "kcal/100g"}}},  # reale
        {"nutrienti": {"energia_kcal": {"valore": None}}},                        # scaffolding vuoto
        {"nutrienti": {}},                                                        # vuoto
        {},                                                                       # assente
    ]
    r = aggrega_copertura(nodi)
    assert r["con_pannello_nutrienti"] == 1


def test_per_fonte_normalizza_le_famiglie_e_conta_nodi_distinti():
    nodi = [
        _nodo_misurato("dolce", 5, 12.0, "CIQUAL 2025 (ANSES) #13039"),
        _nodo_misurato("salato", 5, 500.0, "USDA FDC 170848"),
        _nodo_misurato("umami", 8, 1200.0, "glutammato — Ninomiya 1998"),
        # un nodo con due assi da due fonti: conta 1 in ciascuna famiglia
        {"proprieta": {"dolce": 5, "salato": 3},
         "proprieta_meta": {
             "dolce": {"grezzo": 12.0, "fonte": "USDA FDC 1"},
             "salato": {"grezzo": 500.0, "fonte": "CIQUAL 2025 (ANSES) #1"}}},
    ]
    r = aggrega_copertura(nodi)
    assert r["per_fonte"]["USDA"] == 2
    assert r["per_fonte"]["CIQUAL"] == 2
    assert r["per_fonte"]["glutammato"] == 1


def test_percentuali_sul_totale_reale_mai_gonfiate():
    nodi = [_nodo_valore("dolce", 5), {}, {}, {}]  # 1 su 4
    r = aggrega_copertura(nodi)
    assert r["percentuali"]["per_asse"]["dolce"] == 25.0


def test_totale_zero_non_divide_per_zero():
    r = aggrega_copertura([])
    assert r["totale_ingredienti"] == 0
    assert r["percentuali"]["per_asse"]["dolce"] == 0.0
    assert r["percentuali"]["con_pannello_nutrienti"] == 0.0


def test_accetta_tuple_name_data_e_json_string():
    # come arriva da SELECT name, data: tupla (name, data); data può essere stringa JSON
    nodi = [
        ("Mela", {"proprieta": {"dolce": 6}}),
        ("Limone", json.dumps({"proprieta": {"acido": 8}})),
    ]
    r = aggrega_copertura(nodi)
    assert r["per_asse"]["dolce"] == 1
    assert r["per_asse"]["acido"] == 1


def test_data_strano_non_rompe():
    r = aggrega_copertura([None, "non-json", 123, {"proprieta": "non-un-dict"}])
    assert r["totale_ingredienti"] == 4
    assert r["per_asse"]["dolce"] == 0


def test_famiglia_fonte_sconosciuta_e_altro_vuota_e_none():
    assert _famiglia_fonte("Food Chemistry 2019") == "altro"
    assert _famiglia_fonte("") is None
    assert _famiglia_fonte(None) is None
    assert _famiglia_fonte("USDA FDC 123") == "USDA"
