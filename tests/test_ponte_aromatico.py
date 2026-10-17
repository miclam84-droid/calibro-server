# -*- coding: utf-8 -*-
"""Ponte aromatico — test delle parti PURE (costruzione, ranking, dedup, nota onesta).

Tutte le funzioni qui sotto sono senza DB e senza rete: costruiscono i suggerimenti
da NODI FINTI (dict con la stessa forma che l'endpoint riceve da _base_aromatica e
dalle query di famiglia) e verificano l'onesta' dei dati del nuovo endpoint:
  - nessun ponte dove non c'e' alcun composto condiviso;
  - ogni suggerimento DICHIARA la sua base ("composti" | "famiglia");
  - il ranking mette prima i composti (per numero di condivisi), poi la famiglia;
  - dedup per ingrediente tenendo il segnale piu' forte (composti > famiglia);
  - la nota onesta e' vuota di promesse quando non ci sono segnali.
Le query DB si verificano in smoke su prod come gli altri endpoint del progetto.
"""
from routes.ponte_aromatico import (
    ponte_da_composti,
    ponte_da_famiglia,
    ordina_e_dedup,
    nota_onesta,
)


def _voce_base(nome, condivisi, caratt=None):
    """Nodo finto con la forma reale di una voce _base_aromatica."""
    return {
        "ingrediente": nome,
        "criterio": "base_aromatica",
        "evidenza": {"composti_condivisi": condivisi, "profilo_partner": 100,
                     "indice_rarita": 0.5,
                     "composti_caratterizzanti": caratt or []},
        "robustezza": "Media",
        "perche": "x",
    }


# ── ponte_da_composti: dichiara la base, usa solo i composti, niente gusti ──────
def test_composti_costruisce_suggerimento_dichiarato():
    s = ponte_da_composti(_voce_base("basilico", 7, ["linalolo", "eucaliptolo"]))
    assert s["base"] == "composti"
    assert s["composti_condivisi"] == 7
    assert s["ingrediente"] == "basilico"
    assert "linalolo" in s["perche"]


def test_composti_zero_condivisi_niente_ponte():
    # onesta' dei dati: nessun composto condiviso -> nessun suggerimento inventato
    assert ponte_da_composti(_voce_base("acqua", 0)) is None


def test_composti_senza_caratterizzanti_lo_dice():
    s = ponte_da_composti(_voce_base("x", 4, []))
    assert s is not None
    assert "poco caratterizzanti" in s["perche"]


# ── ponte_da_famiglia: base famiglia, composti_condivisi sempre 0 ───────────────
def test_famiglia_stessa_categoria():
    s = ponte_da_famiglia("pomodoro ramato", "stessa_famiglia", "pomodoro_varieta")
    assert s["base"] == "famiglia"
    assert s["composti_condivisi"] == 0
    assert "pomodoro_varieta" in s["perche"]


def test_famiglia_tradizione_e_cultura_non_chimica():
    s = ponte_da_famiglia("mozzarella", "tradizione")
    assert s["base"] == "famiglia"
    assert s["composti_condivisi"] == 0
    assert "tradizional" in s["perche"].lower()


def test_famiglia_senza_nome_none():
    assert ponte_da_famiglia(None, "tradizione") is None


# ── ordina_e_dedup: ranking dei composti condivisi + dedup per forza del segnale ─
def test_ranking_composti_prima_della_famiglia():
    sugg = [
        ponte_da_famiglia("aglio", "tradizione"),
        ponte_da_composti(_voce_base("menta", 3)),
        ponte_da_composti(_voce_base("timo", 9)),
    ]
    out = ordina_e_dedup(sugg)
    # i due su composti vengono prima, ordinati per composti_condivisi desc
    assert [s["ingrediente"] for s in out] == ["timo", "menta", "aglio"]
    assert out[0]["base"] == "composti" and out[-1]["base"] == "famiglia"


def test_ranking_ordina_composti_per_numero_condivisi():
    sugg = [
        ponte_da_composti(_voce_base("a", 2)),
        ponte_da_composti(_voce_base("b", 11)),
        ponte_da_composti(_voce_base("c", 5)),
    ]
    assert [s["ingrediente"] for s in ordina_e_dedup(sugg)] == ["b", "c", "a"]


def test_dedup_composti_batte_famiglia_stesso_ingrediente():
    # stesso ingrediente da due segnali: tiene quello su composti (piu' forte)
    sugg = [
        ponte_da_famiglia("salvia", "tradizione"),
        ponte_da_composti(_voce_base("salvia", 6)),
    ]
    out = ordina_e_dedup(sugg)
    assert len(out) == 1
    assert out[0]["base"] == "composti" and out[0]["composti_condivisi"] == 6


def test_dedup_case_insensitive_e_limite():
    sugg = [ponte_da_composti(_voce_base("Timo", 4)),
            ponte_da_composti(_voce_base("timo", 8))]
    out = ordina_e_dedup(sugg, limite=12)
    assert len(out) == 1 and out[0]["composti_condivisi"] == 8
    # limite rispettato
    tanti = [ponte_da_famiglia("ing%d" % i, "tradizione") for i in range(20)]
    assert len(ordina_e_dedup(tanti, limite=5)) == 5


def test_ordina_ignora_voci_non_dict_e_senza_nome():
    sugg = [None, "spazzatura", {"base": "composti"}, ponte_da_composti(_voce_base("x", 3))]
    out = ordina_e_dedup(sugg)
    assert [s["ingrediente"] for s in out] == ["x"]


# ── nota_onesta: onesta' dei dati, nessuna promessa senza segnali ───────────────
def test_nota_nessun_segnale_dice_non_abbastanza_dati():
    n = nota_onesta(ha_gusti=False, n_suggeriti=0, ha_composti=False, ha_famiglia=False)
    assert "non abbastanza dati" in n.lower()
    assert "banco" in n.lower()


def test_nota_senza_gusti_dichiara_nessun_gusto_inventato():
    n = nota_onesta(ha_gusti=False, n_suggeriti=3, ha_composti=True, ha_famiglia=True)
    assert "composti aromatici condivisi" in n
    assert "famiglia" in n.lower()
    assert "inventato" in n.lower()


def test_nota_segnali_presenti_ma_nessun_partner():
    n = nota_onesta(ha_gusti=False, n_suggeriti=0, ha_composti=False, ha_famiglia=True)
    assert "nessun partner" in n.lower()
    assert "banco" in n.lower()


def test_nota_con_gusti_niente_disclaimer_gusti():
    n = nota_onesta(ha_gusti=True, n_suggeriti=2, ha_composti=True, ha_famiglia=False)
    assert "inventato" not in n.lower()
    assert "banco" in n.lower()
