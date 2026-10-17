"""Rete di test — funzioni PURE di routes/cottura.py (dimensione "cottura per
ingrediente"). Niente DB, niente rete: si passano dict grezzi come se arrivassero
dal grafo e si controlla selezione + formattazione + onestà del campo curato.

Regola di onestà verificata qui:
  - le tecniche restituite sono "della disciplina / collegate nel grafo", MAI
    "la cottura ideale provata al banco";
  - il campo curato `cottura_consigliata` è FILL-ONLY: se assente/vuoto risulta
    stato "vuoto" (contenitore pronto), se presente espone valore + meta.
"""
from routes.cottura import (
    seleziona_tecniche_collegate,
    seleziona_tecniche_disciplina,
    estrai_cottura_consigliata,
    costruisci_risposta,
    STATO_CURATO_VUOTO,
    STATO_CURATO_PRESENTE,
    ETICHETTA_ONESTA,
)


# ---- seleziona_tecniche_collegate -------------------------------------------

def test_collegate_dedup_e_via_fenomeni():
    # stessa tecnica portata da due fenomeni diversi -> una voce, due fenomeni
    righe = [
        {"tecnica_id": "tec-brasare", "tecnica_nome": "Brasare", "tecnica_dominio": "cucina",
         "fenomeno_id": "fen-collagene-brasato", "fenomeno_nome": "Collagene"},
        {"tecnica_id": "tec-brasare", "tecnica_nome": "Brasare", "tecnica_dominio": "cucina",
         "fenomeno_id": "fen-maillard", "fenomeno_nome": "Maillard", "nota": "a fuoco basso"},
    ]
    out = seleziona_tecniche_collegate(righe)
    assert len(out) == 1
    assert out[0]["id"] == "tec-brasare"
    assert out[0]["via_fenomeni"] == ["Collagene", "Maillard"]
    assert out[0]["nota"] == "a fuoco basso"  # recuperata anche se su una sola coppia


def test_collegate_ordina_per_nome_e_pulisce_markdown():
    righe = [
        {"tecnica_id": "t2", "tecnica_nome": "**Rosolare**", "fenomeno_nome": "Rosolatura"},
        {"tecnica_id": "t1", "tecnica_nome": "Affumicare", "fenomeno_nome": "Affumicatura"},
    ]
    out = seleziona_tecniche_collegate(righe)
    assert [v["nome"] for v in out] == ["Affumicare", "Rosolare"]  # markdown tolto, ordinato


def test_collegate_salta_righe_senza_tecnica():
    out = seleziona_tecniche_collegate([{"tecnica_nome": "boh", "fenomeno_nome": "x"}])
    assert out == []


def test_collegate_vuoto():
    assert seleziona_tecniche_collegate([]) == []


# ---- seleziona_tecniche_disciplina ------------------------------------------

def test_disciplina_esclude_le_gia_collegate():
    righe = [
        {"id": "tec-brasare", "nome": "Brasare", "dominio": "cucina"},
        {"id": "tec-saltare", "nome": "Saltare", "dominio": "cucina"},
    ]
    out = seleziona_tecniche_disciplina(righe, escludi_ids={"tec-brasare"})
    assert [v["id"] for v in out] == ["tec-saltare"]  # la già-collegata non si ripete


def test_disciplina_dedup_e_ordina():
    righe = [
        {"id": "b", "nome": "Zuppa", "dominio": "cucina"},
        {"id": "a", "nome": "Arrosto", "dominio": "cucina"},
        {"id": "a", "nome": "Arrosto", "dominio": "cucina"},  # duplicato id
    ]
    out = seleziona_tecniche_disciplina(righe)
    assert [v["nome"] for v in out] == ["Arrosto", "Zuppa"]
    assert len(out) == 2


def test_disciplina_vuoto():
    assert seleziona_tecniche_disciplina([]) == []


# ---- estrai_cottura_consigliata (fill-only) ---------------------------------

def test_curato_assente_e_vuoto():
    r = estrai_cottura_consigliata({})
    assert r["stato"] == STATO_CURATO_VUOTO
    assert r["valore"] is None
    assert r["nota"]  # spiega che è un contenitore predisposto


def test_curato_campo_vuoto_resta_vuoto():
    # presente ma vuoto -> comunque "vuoto", non si finge che ci sia contenuto
    for vuoto in ("", [], {}, None):
        r = estrai_cottura_consigliata({"cottura_consigliata": vuoto})
        assert r["stato"] == STATO_CURATO_VUOTO
        assert r["valore"] is None


def test_curato_presente_espone_valore_e_meta():
    data = {
        "cottura_consigliata": {"metodo": "sous-vide", "temp_c": 56},
        "cottura_consigliata_meta": {"stato": "curato", "fonte": "banco 2026-10"},
    }
    r = estrai_cottura_consigliata(data)
    assert r["stato"] == "curato"
    assert r["fonte"] == "banco 2026-10"
    assert r["valore"] == {"metodo": "sous-vide", "temp_c": 56}


def test_curato_presente_senza_meta_default_stato():
    r = estrai_cottura_consigliata({"cottura_consigliata": "arrostire"})
    assert r["stato"] == STATO_CURATO_PRESENTE
    assert r["valore"] == "arrostire"
    assert r["fonte"] == ""


def test_curato_robusto_a_data_non_dict():
    assert estrai_cottura_consigliata(None)["stato"] == STATO_CURATO_VUOTO
    assert estrai_cottura_consigliata("stringa")["stato"] == STATO_CURATO_VUOTO


# ---- costruisci_risposta ----------------------------------------------------

def test_risposta_etichette_oneste_e_conteggi():
    ingr = {"id": "ing-manzo", "nome": "Manzo", "disciplina": "cucina"}
    collegate = [{"id": "t1", "nome": "Brasare", "dominio": "cucina", "via_fenomeni": ["Collagene"]}]
    disc = [{"id": "t2", "nome": "Saltare", "dominio": "cucina"}]
    curato = estrai_cottura_consigliata({})
    out = costruisci_risposta(ingr, "cucina", collegate, disc, curato)
    assert out["onesta"] == ETICHETTA_ONESTA
    assert "NON la cottura ideale provata al banco" in out["onesta"]
    assert out["tecniche_collegate"]["conteggio"] == 1
    assert out["tecniche_disciplina"]["conteggio"] == 1
    assert "cucina" in out["tecniche_disciplina"]["etichetta"]
    assert out["cottura_consigliata"]["stato"] == STATO_CURATO_VUOTO


def test_risposta_senza_disciplina_etichetta_generica():
    out = costruisci_risposta({"id": "x"}, "", [], [], estrai_cottura_consigliata({}))
    assert out["disciplina"] == ""
    assert "disciplina" in out["tecniche_disciplina"]["etichetta"]
