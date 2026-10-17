"""Test PURI (nessun DB) per routes/nutrizionale.py.
Verificano l'onestà: un numero esce SOLO se ha un grezzo misurato E una fonte;
dove manca il dato -> null (mai inventato). Allergeni dedotti dal nome."""
from routes.nutrizionale import estrai_valori, costruisci_scheda, CAMPI_NUTRI


def _voce(valori, campo):
    return next(v for v in valori if v["campo"] == campo)


def test_valore_con_fonte_viene_esposto():
    data = {"proprieta_meta": {
        "salato": {"stato": "derivato", "fonte": "USDA FDC 170848", "grezzo": 1602.0},
    }}
    valori = estrai_valori(data)
    sodio = _voce(valori, "Sodio")
    assert sodio["valore"] == 1602.0
    assert sodio["unita"] == "mg/100g"
    assert sodio["fonte"] == "USDA FDC 170848"


def test_numero_senza_fonte_non_viene_mai_esposto():
    # grezzo presente ma fonte assente -> NON si espone il numero (null)
    data = {"proprieta_meta": {"grasso": {"stato": "derivato", "grezzo": 28.6}}}
    grasso = _voce(estrai_valori(data), "Grassi")
    assert grasso["valore"] is None
    assert grasso["fonte"] is None
    assert grasso["unita"] is None


def test_asse_mancante_e_null_non_zero():
    valori = estrai_valori({"proprieta_meta": {}})
    # ogni campo canonico esce comunque, ma vuoto (mai uno zero inventato)
    assert len(valori) == len(CAMPI_NUTRI)
    for v in valori:
        assert v["valore"] is None
        assert v["fonte"] is None


def test_data_vuota_o_none_non_rompe():
    assert all(v["valore"] is None for v in estrai_valori(None))
    assert all(v["valore"] is None for v in estrai_valori({}))


def test_data_come_stringa_json():
    import json
    raw = json.dumps({"proprieta_meta": {
        "dolce": {"stato": "derivato", "fonte": "CIQUAL 2025 (ANSES)", "grezzo": 4.2, "via": "zuccheri_totali"}}})
    dolce = _voce(estrai_valori(raw), "Zuccheri")
    assert dolce["valore"] == 4.2
    assert dolce["fonte"] == "CIQUAL 2025 (ANSES)"


def test_scheda_completa_ha_le_chiavi_del_contratto():
    data = {"proprieta_meta": {"salato": {"stato": "derivato", "fonte": "USDA FDC 1", "grezzo": 50}}}
    s = costruisci_scheda("Parmigiano Reggiano", data)
    assert s["nome"] == "Parmigiano Reggiano"
    assert set(["nome", "valori", "allergeni", "note_onesta", "trovato"]).issubset(s.keys())
    # parmigiano -> latte dedotto dal nome
    nomi_all = [a["nome"] for a in s["allergeni"]]
    assert "Latte" in nomi_all
    # ogni valore esposto porta campo e (se valorizzato) la fonte
    for v in s["valori"]:
        assert "campo" in v and "fonte" in v and "unita" in v and "valore" in v
        if v["valore"] is not None:
            assert v["fonte"]
