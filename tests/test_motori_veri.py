"""Motori veri (wave 4) — verifica che i calcoli siano DETERMINISTICI e FONDATI sulle fonti,
non medie di range o schede statiche.
 - Gelato: PAC/POD = media pesata della tabella ZUCCHERI (saccarosio=100).
 - Caffe' filtro: TDS = EY% / (ratio - LRR), relazione SCA Brewing Control Chart.
 - Cocktail: gradazione pre-diluizione per conservazione dell'alcol (algebra, Dave Arnold).
Niente DB, niente rete: solo funzioni pure.
"""
import pytest

from motore_gelato import progetta_gelato, _indici_blend, ZUCCHERI
import motore_caffe
from motore_caffe import progetta_caffe, LRR, EY_TARGET
from motore_cocktail import progetta_cocktail


# ---------- GELATO ----------

def test_gelato_pac_pod_media_pesata_dalla_tabella():
    # 70% saccarosio (100/100) + 30% destrosio (190/70) -> PAC 127, POD 91
    pac, pod, _ = _indici_blend({"saccarosio": 0.70, "destrosio": 0.30})
    assert pac == pytest.approx(0.70 * 100 + 0.30 * 190)  # 127
    assert pod == pytest.approx(0.70 * 100 + 0.30 * 70)   # 91


def test_gelato_saccarosio_puro_e_indice_100():
    pac, pod, _ = _indici_blend({"saccarosio": 1.0})
    assert pac == 100 and pod == 100


def test_gelato_destrosio_alza_pac_rispetto_al_saccarosio():
    # proprieta' fondante: piu' destrosio => piu' potere anticongelante
    solo_sacc, _, _ = _indici_blend({"saccarosio": 1.0})
    con_destr, _, _ = _indici_blend({"saccarosio": 0.5, "destrosio": 0.5})
    assert con_destr > solo_sacc


def test_gelato_proporzioni_non_normalizzate_ok():
    # le proporzioni vengono normalizzate: 7:3 == 0.7:0.3
    a, _, _ = _indici_blend({"saccarosio": 7, "destrosio": 3})
    b, _, _ = _indici_blend({"saccarosio": 0.7, "destrosio": 0.3})
    assert a == pytest.approx(b)


def test_gelato_zucchero_ignoto_scoppia():
    with pytest.raises(ValueError):
        _indici_blend({"zucchero_inventato": 1.0})


def test_gelato_output_espone_range_non_solo_media():
    out = progetta_gelato("crema", 1000, -12)
    # onesta': il bilanciamento e' un RANGE, non un singolo numero spacciato per esatto
    assert "16-20%" in out["bilanciamento_target"]["zuccheri"]
    assert out["mix_zuccheri"]["pac_index"] == 127.0
    # la regola di servizio e' etichettata come non derivata dalla tabella
    assert "NON" in out["servizio_vetrina"]["etichetta"].upper()


def test_gelato_pac_index_coerente_con_tabella_destrosio():
    assert ZUCCHERI["destrosio"]["pac"] == 190  # la fonte e' la tabella del file


# ---------- CAFFE' ----------

def test_caffe_filtro_tds_relazione_sca():
    # TDS% = EY% / (ratio - LRR). ratio 16, EY 20, LRR 2 -> 20/14 = 1.4286%
    out = progetta_caffe("filtro", 15, brew_ratio=16, target_ey=20)
    atteso = 20.0 / (16 - LRR)
    assert float(out["tds_previsto"]["al_target"].split("%")[0]) == pytest.approx(round(atteso, 2), abs=0.01)


def test_caffe_filtro_massa_bevanda_toglie_acqua_trattenuta():
    out = progetta_caffe("filtro", 15, brew_ratio=16.0)
    # acqua 240, trattenuta 2.0*15=30, bevanda 210
    assert "240" in out["acqua"]
    assert "30.0g" in out["acqua_trattenuta"]
    assert "210" in out["massa_bevanda"]


def test_caffe_ratio_alto_abbassa_tds():
    # piu' acqua (ratio piu' alto) => TDS piu' basso (tazza piu' debole)
    t16 = motore_caffe._tds_previsto(15, 16, EY_TARGET)
    t18 = motore_caffe._tds_previsto(15, 18, EY_TARGET)
    assert t18 < t16


def test_caffe_filtro_1a18_centra_box_sca():
    out = progetta_caffe("filtro", 15, brew_ratio=18, target_ey=20)
    assert out["tds_previsto"]["dentro_box_sca"] is True


def test_caffe_espresso_non_inventa_tds():
    out = progetta_caffe("espresso", 18)
    assert "resa" in out and "36.0g" in out["resa"]  # 18*2
    # onesta': niente TDS stimato per l'espresso
    assert "tds_previsto" not in out
    assert "rifrattometro" in out["nota_onesta"]


def test_caffe_ratio_troppo_basso_scoppia():
    with pytest.raises(ValueError):
        motore_caffe._tds_previsto(15, 2.0, 20)  # ratio == LRR


# ---------- COCKTAIL ----------

def test_cocktail_gradazione_pre_diluizione_per_conservazione_alcol():
    # 90ml a 22%, stirred (dil 22%): pre_dil = 90/1.22 = 73.77 -> 74; alcol = round(90*0.22)=20
    # gradazione_pre = 20/74*100 = 27.0%
    out = progetta_cocktail(90, 22, "stirred", 40)
    assert out["gradazione"]["prima_della_diluizione"] == "~27.0% vol"


def test_cocktail_pre_diluizione_sempre_maggiore_del_finale():
    # la diluizione aggiunge acqua: prima della diluizione la gradazione e' piu' alta
    out = progetta_cocktail(90, 22, "shaken", 40)
    pre = float(out["gradazione"]["prima_della_diluizione"].strip("~% vol"))
    assert pre > 22
