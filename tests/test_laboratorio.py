# -*- coding: utf-8 -*-
"""Laboratorio Sensoriale V1 — test delle parti PURE (ranking/formattazione).

Tutte le funzioni qui sotto sono senza DB e senza rete: coprono l'onesta' dei
dati (nessun ponte dove non c'e' nulla di condiviso), la banda di evidenza che
pesa i composti caratterizzanti (rari), l'indice di rarita' IDF e il confronto
degli assi sensoriali. Le query DB si verificano in smoke su prod come gli altri
endpoint del progetto.
"""
import math

from routes.laboratorio_sensoriale import (
    indice_rarita,
    seleziona_caratterizzanti,
    banda_evidenza,
    partiziona_composti,
    confronta_assi,
)


# ── indice_rarita (IDF normalizzato per sqrt(profilo_a*profilo_b)) ──────────────
def test_indice_rarita_vuoto_e_zero():
    assert indice_rarita([], 1000, 10, 10) == 0.0


def test_indice_rarita_profilo_nullo_e_zero():
    assert indice_rarita([5, 5], 1000, 0, 10) == 0.0


def test_composto_raro_pesa_piu_di_uno_comune():
    # un composto in 2 ingredienti pesa piu' di uno in 900, a parita' di profili.
    raro = indice_rarita([2], 1000, 10, 10)
    comune = indice_rarita([900], 1000, 10, 10)
    assert raro > comune > 0.0


def test_indice_rarita_formula_coerente_con_base_aromatica():
    # stessa formula: sum(ln(Ntot/df)) / sqrt(na*nb)
    df = [10, 50]
    atteso = (math.log(1000 / 10) + math.log(1000 / 50)) / math.sqrt(8 * 12)
    assert indice_rarita(df, 1000, 8, 12) == round(atteso, 3)


# ── seleziona_caratterizzanti (tiene solo i rari) ───────────────────────────────
def test_seleziona_caratterizzanti_scarta_i_comuni():
    comp_df = [("c_raro", 10), ("c_comune", 800), ("c_medio", 40)]
    rari = seleziona_caratterizzanti(comp_df, n_tot=1000, soglia_frazione=0.05)  # soglia 50
    ids = [c for c, _ in rari]
    assert ids == ["c_raro", "c_medio"]  # ordinati dal piu' raro, 800 escluso


def test_seleziona_caratterizzanti_vuoto_se_tutti_comuni():
    comp_df = [("a", 900), ("b", 950)]
    assert seleziona_caratterizzanti(comp_df, n_tot=1000) == []


# ── banda_evidenza (robustezza qualitativa, pesa i caratterizzanti) ─────────────
def test_banda_none_senza_condivisi():
    assert banda_evidenza(0, 0) is None


def test_banda_alta_con_tre_caratterizzanti():
    assert banda_evidenza(5, 3) == "Alta"


def test_banda_media_con_un_caratterizzante():
    assert banda_evidenza(4, 1) == "Media"


def test_banda_media_con_molti_comuni_senza_caratterizzanti():
    assert banda_evidenza(8, 0) == "Media"


def test_banda_esplorativa_pochi_e_comuni():
    assert banda_evidenza(2, 0) == "Esplorativa"


# ── partiziona_composti (condivisi vs distinti) ─────────────────────────────────
def test_partiziona_composti():
    cond, solo_a, solo_b = partiziona_composti(["x", "y", "z"], ["y", "z", "w"])
    assert cond == ["y", "z"]
    assert solo_a == ["x"]
    assert solo_b == ["w"]


def test_partiziona_composti_nessuna_sovrapposizione():
    cond, solo_a, solo_b = partiziona_composti(["a"], ["b"])
    assert cond == []
    assert solo_a == ["a"]
    assert solo_b == ["b"]


def test_partiziona_composti_input_vuoto():
    assert partiziona_composti(None, None) == ([], [], [])


# ── confronta_assi (profili sensoriali affiancati, delta) ───────────────────────
def test_confronta_assi_delta():
    a = {"dolce": 8.0, "acido": 2.0}
    b = {"dolce": 3.0, "acido": 6.0}
    out = confronta_assi(a, b)
    d = {r["asse"]: r for r in out}
    assert d["dolce"]["delta"] == 5.0
    assert d["acido"]["delta"] == -4.0


def test_confronta_assi_salta_assenti_in_entrambi():
    out = confronta_assi({"dolce": 5.0}, {"dolce": 5.0})
    assert [r["asse"] for r in out] == ["dolce"]  # salato/acido/... assenti, saltati


def test_confronta_assi_senza_delta_se_manca_un_lato():
    out = confronta_assi({"umami": 7.0}, {})
    assert len(out) == 1
    assert out[0]["a"] == 7.0 and out[0]["b"] is None
    assert "delta" not in out[0]
