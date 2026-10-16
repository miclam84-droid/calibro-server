"""Rete di test — onestà dei dati su evidence/provenienza.

Due fix blindati qui:

1) routes/api.py `_classifica_evidence`: un nodo la cui provenienza è una STIMA
   (data['provenienza']['stato'] == 'stimato_AI') NON può valere 'A' ("Dato
   molecolare verificato"), anche quando manca una 'fonte' top-level. Prima
   restava 'A' (disonesto): ora scende a 'C'.

2) build_ingredient_graph.py `_dati_arco_molecolare` / `_dati_arco_contrasto`:
   gli archi di abbinamento sono AI-derivati, quindi la provenienza è dichiarata
   come stima ('fonte': 'stima_AI', 'stato': 'stimato_AI'), non 'dataset Matter
   Lab' (che sarebbe provenienza gonfiata).

Entrambe le funzioni sono pure: nessun DB, nessuna rete, nessun contesto Flask.
Nota import: build_ingredient_graph importa psycopg2 a livello modulo (come gli
altri test di questo pacchetto): se manca in locale si salta invece di rompere.
"""
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1) Classificatore evidence (routes/api.py) — declassamento dei nodi stimati
# ─────────────────────────────────────────────────────────────────────────────
from routes.api import _classifica_evidence


def test_nodo_stimato_ai_non_resta_A_senza_fonte():
    # Il buco segnalato: provenienza stimato_AI, nessuna 'fonte' top-level.
    # Prima diventava 'A'; ora deve scendere a 'C'.
    data = {"abbinamenti": [], "provenienza": {"stato": "stimato_AI"}}
    assert _classifica_evidence(data, None) == "C"


def test_nodo_stimato_generico_non_resta_A():
    data = {"provenienza": {"stato": "stimato"}}
    assert _classifica_evidence(data, None) == "C"


def test_stima_declassa_anche_se_livello_gia_A():
    # Se a monte è stato rilevato 'A' ma la provenienza è una stima, va declassato.
    data = {"provenienza": {"stato": "stimato_AI"}}
    assert _classifica_evidence(data, "A") == "C"


def test_nodo_verificato_resta_A():
    # Nessuna stima, nessuna fonte 'ai' → comportamento invariato: 'A'.
    data = {"abbinamenti": [], "fonte": "USDA FoodData Central"}
    assert _classifica_evidence(data, None) == "A"


def test_fonte_ai_resta_C_comportamento_invariato():
    data = {"fonte": "Matter Lab AI"}
    assert _classifica_evidence(data, None) == "C"


def test_livello_B_preservato_se_non_stima():
    # Un livello già rilevato diverso da 'A' non viene toccato.
    data = {"provenienza": {"stato": "verificato"}}
    assert _classifica_evidence(data, "B") == "B"


def test_stima_non_declassa_un_livello_gia_basso():
    # 'C' resta 'C' (il declassamento riguarda solo il salto disonesto verso 'A').
    data = {"provenienza": {"stato": "stimato_AI"}}
    assert _classifica_evidence(data, "C") == "C"


def test_provenienza_malformata_non_rompe():
    # provenienza non-dict / assente: nessuna eccezione, logica 'fonte' invariata.
    assert _classifica_evidence({"provenienza": None}, None) == "A"
    assert _classifica_evidence({}, None) == "A"
    assert _classifica_evidence(None, None) == "A"


# ─────────────────────────────────────────────────────────────────────────────
# 2) Etichetta onesta degli archi (build_ingredient_graph.py)
# ─────────────────────────────────────────────────────────────────────────────
pytest.importorskip("psycopg2", reason="build_ingredient_graph importa psycopg2 a livello modulo")
from build_ingredient_graph import _dati_arco_molecolare, _dati_arco_contrasto


def test_arco_molecolare_non_si_spaccia_per_dataset():
    out = _dati_arco_molecolare({"overlap_score": 12, "composti_condivisi": ["limonene"]})
    assert out["fonte"] != "dataset Matter Lab"
    assert out["fonte"] == "stima_AI"
    assert out["stato"] == "stimato_AI"


def test_arco_molecolare_conserva_i_dati_veri():
    out = _dati_arco_molecolare({"overlap_score": 7, "composti_condivisi": ["x"], "meccanismo": "m"})
    assert out["overlap"] == 7
    assert out["composti"] == ["x"]
    assert out["meccanismo"] == "m"


def test_arco_contrasto_non_si_spaccia_per_dataset():
    out = _dati_arco_contrasto({"tipo": "acido/grasso", "perche": "taglio", "fenomeno_matter": "f"})
    assert out["fonte"] != "dataset Matter Lab"
    assert out["fonte"] == "stima_AI"
    assert out["stato"] == "stimato_AI"


def test_arco_contrasto_conserva_i_dati_veri():
    out = _dati_arco_contrasto({"tipo": "t", "perche": "p", "fenomeno_matter": "fen"})
    assert out["tipo"] == "t" and out["perche"] == "p" and out["fenomeno"] == "fen"


def test_archi_robusti_su_abb_vuoto():
    # Nessuna chiave presente: default coerenti, nessuna eccezione.
    m = _dati_arco_molecolare({})
    c = _dati_arco_contrasto({})
    assert m["overlap"] == 0 and m["composti"] == [] and m["fonte"] == "stima_AI"
    assert c["tipo"] == "" and c["fonte"] == "stima_AI"
