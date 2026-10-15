"""Rete di test — deduzione allergeni (obbligo di legge, Reg. UE 1169/2011).
Funzione pura. La linea è "meglio segnalare in più"; i falsi positivi da
match-per-sottostringa sono bug noti, marcati xfail finché il matching non
passa ai confini di parola.

id allergeni: 1 glutine · 2 crostacei · 3 uova · 7 latte · 12 solfiti
"""
import pytest
from routes.allergeni import deduci_allergeni


def test_pizza_margherita_glutine_e_latte():
    ids, _ = deduci_allergeni([], nome_piatto="Pizza margherita")
    assert 1 in ids   # glutine
    assert 7 in ids   # margherita -> latte (mozzarella)


def test_carbonara_glutine_uova_latte():
    ids, _ = deduci_allergeni([], nome_piatto="Spaghetti alla carbonara")
    assert {1, 3, 7} <= set(ids)


def test_gamberi_crostacei():
    ids, _ = deduci_allergeni(["gamberi"])
    assert 2 in ids


def test_solfiti_warning_su_vino():
    ids, warn = deduci_allergeni(["vino rosso"])
    assert 12 in ids
    assert warn and "solfiti" in warn.lower()


def test_ingredienti_come_dict():
    # accetta sia stringhe sia dict {'nome': ...}
    ids, _ = deduci_allergeni([{"nome": "gamberi"}, {"nome": "vino"}])
    assert 2 in ids and 12 in ids


@pytest.mark.xfail(reason="bug noto: match sottostringa — 'latte di cocco' non è un latticino", strict=False)
def test_latte_di_cocco_non_e_latticino():
    ids, _ = deduci_allergeni(["latte di cocco"])
    assert 7 not in ids


@pytest.mark.xfail(reason="bug noto: 'pizza' in _MAPPA scatta prima dell'esclusione senza-glutine", strict=False)
def test_pizza_senza_glutine_non_segnala_glutine():
    ids, _ = deduci_allergeni([], nome_piatto="Pizza senza glutine")
    assert 1 not in ids
