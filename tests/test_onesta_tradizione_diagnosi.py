# -*- coding: utf-8 -*-
"""Rete di test — ONESTA' DEI DATI (il principio centrale del prodotto).

Due fix blindati qui, entrambi con funzioni PURE (nessun DB, nessuna rete, nessun Flask):

FIX A) routes/criteri.py `_classifica_tradizione(edge_data)`: un arco di
   abbinamento tradizionale va marcato "documentato" (da fonte) SOLO se nasce da
   ricette reali (da_ricette >= 2) e NON e' una proposta AI; altrimenti e'
   "proposta" (da verificare). La parola "documentato" non deve MAI comparire nel
   `perche` di un arco AI.

FIX B) routes/api.py `_fondi_cause(patrimonio, ai)`: le cause del patrimonio
   (da fonte, con `da_protocollo`) vanno SEMPRE in risposta, PRIMA di quelle AI,
   con dedup per testo causa case-insensitive. Con AI vuota torna solo il
   patrimonio; con AI piena torna patrimonio + AI senza duplicati.

Se questa rete diventa rossa, l'onesta' dei dati e' regredita.
"""
from routes.criteri import _classifica_tradizione
from routes.api import _fondi_cause


# ─────────────────────────────────────────────────────────────────────────────
# FIX A — tradizione: documentato (da fonte) vs proposta (AI)
# ─────────────────────────────────────────────────────────────────────────────

def test_A_arco_da_ricette_e_documentato_col_piatto():
    cls = _classifica_tradizione({"piatto": "cacio e pepe", "da_ricette": 3})
    assert cls["evidenza"]["tipo"] == "documentato"
    assert cls["evidenza"]["piatto"] == "cacio e pepe"
    assert cls["evidenza"]["da_ricette"] == 3
    assert cls["provenienza"] == "da fonte"
    assert "3 ricette" in cls["perche"]
    assert "cacio e pepe" in cls["perche"]


def test_A_arco_ai_validato_e_proposta_mai_documentato():
    cls = _classifica_tradizione({"piatto": "pizza strana", "fonte": "ai_validato",
                                  "verificato": False, "da_ricette": 5})
    assert cls["evidenza"]["tipo"] == "proposta"
    assert cls["provenienza"] == "proposta"
    # il cuore del fix: mai spacciare un'invenzione AI per un dato documentato
    assert "documentato" not in cls["perche"]
    assert "da verificare" in cls["perche"]
    assert "pizza strana" in cls["perche"]


def test_A_verificato_false_declassa_a_proposta():
    cls = _classifica_tradizione({"da_ricette": 9, "verificato": False})
    assert cls["evidenza"]["tipo"] == "proposta"
    assert "documentato" not in cls["perche"]


def test_A_senza_segnale_ricette_e_proposta():
    cls = _classifica_tradizione({"piatto": "boh"})
    assert cls["evidenza"]["tipo"] == "proposta"
    assert "documentato" not in cls["perche"]


def test_A_da_ricette_uno_non_basta():
    # soglia: da_ricette >= 2
    cls = _classifica_tradizione({"da_ricette": 1})
    assert cls["evidenza"]["tipo"] == "proposta"


def test_A_edge_data_none_non_rompe():
    cls = _classifica_tradizione(None)
    assert cls["evidenza"]["tipo"] == "proposta"
    assert "documentato" not in cls["perche"]


def test_A_documentato_senza_piatto_non_aggiunge_suffisso():
    cls = _classifica_tradizione({"da_ricette": 4})
    assert cls["evidenza"]["tipo"] == "documentato"
    assert "piatto" not in cls["evidenza"]
    assert cls["perche"].endswith("4 ricette")


# ─────────────────────────────────────────────────────────────────────────────
# FIX B — fusione cause patrimonio (da fonte) + AI (proposta)
# ─────────────────────────────────────────────────────────────────────────────

def _patrimonio_tipo():
    return [
        {"causa": "Lievitazione insufficiente", "probabilita": "—", "sensore_conferma": "",
         "patch": "Allunga la lievitazione", "da_protocollo": "Focaccia base"},
    ]


def test_B_ai_vuota_torna_solo_patrimonio_con_da_protocollo():
    out = _fondi_cause(_patrimonio_tipo(), [])
    assert len(out) == 1
    assert out[0]["causa"] == "Lievitazione insufficiente"
    assert out[0]["da_protocollo"] == "Focaccia base"


def test_B_ai_none_torna_solo_patrimonio():
    out = _fondi_cause(_patrimonio_tipo(), None)
    assert len(out) == 1
    assert out[0]["da_protocollo"] == "Focaccia base"


def test_B_patrimonio_prima_poi_ai_dedup():
    ai = [
        {"causa": "Forno troppo freddo", "probabilita": "media", "patch": "Alza a 250"},
        # duplicato del patrimonio, case-insensitive -> scartato
        {"causa": "lievitazione INSUFFICIENTE", "probabilita": "alta", "patch": "altro"},
    ]
    out = _fondi_cause(_patrimonio_tipo(), ai)
    assert len(out) == 2
    # patrimonio PRIMA
    assert out[0]["causa"] == "Lievitazione insufficiente"
    assert out[0]["da_protocollo"] == "Focaccia base"
    # la causa AV unica resta, quella duplicata no
    assert out[1]["causa"] == "Forno troppo freddo"
    assert "da_protocollo" not in out[1]


def test_B_scarta_cause_senza_testo_e_non_dict():
    out = _fondi_cause([{"causa": ""}, "stringa", 42], [{"causa": "Valida"}])
    assert len(out) == 1
    assert out[0]["causa"] == "Valida"


def test_B_dedup_interno_patrimonio():
    patr = [
        {"causa": "X", "da_protocollo": "P1"},
        {"causa": "x", "da_protocollo": "P2"},
    ]
    out = _fondi_cause(patr, [])
    assert len(out) == 1
    assert out[0]["da_protocollo"] == "P1"
