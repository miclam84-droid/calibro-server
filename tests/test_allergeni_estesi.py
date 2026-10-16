"""Rete di test — deduzione allergeni, casi aggiuntivi certi (Reg. UE 1169/2011).
Funzione pura. Completa test_allergeni.py con altri casi verificati sul _MAPPA
reale di routes/allergeni.py e con i falsi positivi noti da match-sottostringa,
marcati xfail finché il matching non passa ai confini di parola.

id allergeni: 3 uova · 5 arachidi · 6 soia · 7 latte · 8 frutta a guscio ·
11 sesamo · 13 lupini · 14 molluschi
"""
import pytest
from routes.allergeni import deduci_allergeni


def test_tiramisu_uova_e_latte():
    ids, _ = deduci_allergeni(["tiramisù"])
    assert {3, 7} <= set(ids)   # uova + latte


def test_cozze_molluschi():
    ids, _ = deduci_allergeni(["cozze"])
    assert 14 in ids


def test_salsa_di_soia_soia():
    ids, _ = deduci_allergeni(["salsa di soia"])
    assert 6 in ids


def test_sesamo_e_tahin():
    ids_s, _ = deduci_allergeni(["sesamo"])
    ids_t, _ = deduci_allergeni(["tahin"])
    assert 11 in ids_s
    assert 11 in ids_t


def test_tofu_soia():
    ids, _ = deduci_allergeni(["tofu"])
    assert 6 in ids


def test_lupini():
    ids, _ = deduci_allergeni(["lupini"])
    assert 13 in ids


def test_mandorle_frutta_a_guscio():
    ids, _ = deduci_allergeni(["mandorle"])
    assert 8 in ids


def test_arachidi_non_sono_frutta_a_guscio():
    # arachide = legume (allergene 5), NON frutta a guscio (8): insidia classica
    ids, _ = deduci_allergeni(["arachidi"])
    assert 5 in ids
    assert 8 not in ids


def test_multi_ingrediente_unione():
    ids, _ = deduci_allergeni(["cozze", "vino bianco", "sesamo"])
    assert {11, 12, 14} <= set(ids)   # sesamo + solfiti + molluschi


# ── FALSI POSITIVI NOTI da match-per-sottostringa (xfail, non-strict) ──

@pytest.mark.xfail(reason="bug noto: 'burro di arachidi' contiene 'burro' -> latte, ma è burro di arachidi", strict=False)
def test_burro_di_arachidi_non_e_latte():
    ids, _ = deduci_allergeni(["burro di arachidi"])
    assert 5 in ids       # arachidi: corretto
    assert 7 not in ids   # latte: falso positivo


@pytest.mark.xfail(reason="bug noto: 'noce moscata' contiene 'noce' -> frutta a guscio, ma è una spezia", strict=False)
def test_noce_moscata_non_e_frutta_a_guscio():
    ids, _ = deduci_allergeni(["noce moscata"])
    assert 8 not in ids


@pytest.mark.xfail(reason="bug noto: 'melagrana' contiene 'grana' -> latte, ma è un frutto", strict=False)
def test_melagrana_non_e_latte():
    ids, _ = deduci_allergeni(["melagrana"])
    assert 7 not in ids
