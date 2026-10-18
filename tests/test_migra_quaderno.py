"""Rete di test — migrazione dei 3 store vecchi nel Quaderno unico.
Funzioni PURE (niente DB, niente rete): mappatura record-vecchio -> record-unico
e idempotenza della de-dup (id deterministico). Da record finti.

Garanzia sotto test: nessuna perdita e nessun duplicato. Se due esecuzioni
mappano la stessa riga d'origine devono produrre lo STESSO id (cosi' l'INSERT
... ON CONFLICT DO NOTHING la salta), mentre righe diverse restano distinte.
"""
import json

from routes.admin_migra_quaderno import (
    _mid, _jd, _da_ricette, _da_misure, _da_chat, _COLONNE, _PIANO,
)


# --- l'INSERT scrive esattamente 12 colonne: la tupla del mapper deve combaciare
N_COLONNE = 12


def _prov(tupla):
    """provenienza e' la colonna 11 (0-based 10) nella tupla del mapper."""
    return json.loads(tupla[10])


# ---------------------------------------------------------------- ricette_salvate
def test_ricette_mappa_campi_e_colonne():
    # (device_id, ricetta_id, nome, dati, creato_il)
    r = ("dev-A", "ric-7", "Focaccia", {"idratazione": 70}, "2026-01-01T10:00:00")
    t = _da_ricette(r)
    assert len(t) == N_COLONNE == len(_COLONNE)
    assert t[1] == "device"          # chiave_tipo
    assert t[2] == "dev-A"           # chiave = device_id
    assert t[4] == "laboratorio"     # porta
    assert t[5] == "ricetta"         # funzione
    assert t[6] == "ricetta"         # tipo
    assert t[7] == "Focaccia"        # titolo
    # stato_output conserva i dati originali (riproducibile, nessuna perdita)
    assert json.loads(t[9]) == {"idratazione": 70}
    prov = _prov(t)
    assert prov["migrato_da"] == "ricette_salvate"
    assert prov["ricetta_id"] == "ric-7"


def test_ricette_titolo_di_default_se_nome_mancante():
    t = _da_ricette(("dev-A", "ric-7", None, {"x": 1}, None))
    assert t[7] == "Ricetta"


# ---------------------------------------------------------------- misure_salvate
def test_misure_mappa_campi_e_colonne():
    # (id, device_id, fenomeno, fenomeno_id, valore, unita, bersaglio, nota, creato_il)
    r = (42, "dev-B", "Temperatura impasto", "temp-imp", "24", "C", "22-24", "sala calda", "2026-02-02")
    t = _da_misure(r)
    assert len(t) == N_COLONNE
    assert t[1] == "device" and t[2] == "dev-B"
    assert t[4] == "banco"
    assert t[5] == "misura" and t[6] == "misura"
    assert t[7] == "Temperatura impasto"
    si = json.loads(t[8])   # stato_input: come riprodurre
    assert si["fenomeno_id"] == "temp-imp" and si["bersaglio"] == "22-24"
    so = json.loads(t[9])   # stato_output: il risultato misurato
    assert so["valore"] == "24" and so["unita"] == "C"
    assert t[11] == "sala calda"             # note_lab = nota originale (niente perdita)
    assert _prov(t)["migrato_da"] == "misure_salvate"


# ---------------------------------------------------------------- chat_salvate
def test_chat_mappa_campi_e_colonne():
    # (id, device_id, titolo, messaggi, tag, creato_il)
    msgs = [{"ruolo": "utente", "testo": "ciao"}]
    t = _da_chat((9, "dev-C", "Panettone", msgs, "panificazione", "2026-03-03"))
    assert len(t) == N_COLONNE
    assert t[1] == "device" and t[2] == "dev-C"
    assert t[4] == "quaderno" and t[5] == "chat" and t[6] == "chat"
    assert t[7] == "Panettone"
    assert json.loads(t[9])["messaggi"] == msgs   # messaggi integri
    assert _prov(t)["migrato_da"] == "chat_salvate"


def test_chat_titolo_di_default():
    t = _da_chat((9, "dev-C", None, [], None, None))
    assert t[7] == "Conversazione"


# ---------------------------------------------------------------- idempotenza / de-dup
def test_id_deterministico_stessa_riga_stesso_id():
    r = ("dev-A", "ric-7", "Focaccia", {"i": 1}, "2026-01-01")
    assert _da_ricette(r)[0] == _da_ricette(r)[0]
    # anche ricreando la riga da zero (altra istanza degli oggetti)
    r2 = ("dev-A", "ric-7", "Focaccia", {"i": 999}, "data-diversa")
    # l'id dipende da (device_id, ricetta_id): la chiave naturale, non dal contenuto
    assert _da_ricette(r)[0] == _da_ricette(r2)[0]


def test_id_diverso_per_righe_diverse():
    a = _da_ricette(("dev-A", "ric-7", "x", {}, None))[0]
    b = _da_ricette(("dev-A", "ric-8", "x", {}, None))[0]   # altra ricetta
    c = _da_ricette(("dev-Z", "ric-7", "x", {}, None))[0]   # altro device
    assert a != b and a != c and b != c


def test_id_namespaciato_per_store():
    # stesso device + stesso numero naturale, ma store diversi -> prefissi diversi
    ric = _da_ricette(("dev-A", "7", "x", {}, None))[0]
    mis = _da_misure((7, "dev-A", "f", None, "1", None, None, None, None))[0]
    chat = _da_chat((7, "dev-A", "t", [], None, None))[0]
    assert ric.startswith("qr-mig-ric-")
    assert mis.startswith("qr-mig-mis-")
    assert chat.startswith("qr-mig-chat-")
    assert len({ric, mis, chat}) == 3


def test_mid_stabile_e_formato():
    assert _mid("ric", "dev-A", "7") == _mid("ric", "dev-A", "7")
    assert _mid("ric", "dev-A", "7").startswith("qr-mig-ric-")


def test_jd_robusto_su_none_e_tipi():
    # le colonne stato_input/output sono NOT NULL: _jd non deve mai dare NULL
    assert json.loads(_jd(None)) == {}
    assert json.loads(_jd("stringa")) == {}
    assert json.loads(_jd({"a": 1})) == {"a": 1}
    assert json.loads(_jd([1, 2])) == [1, 2]


def test_piano_copre_i_tre_store():
    nomi = [p[0] for p in _PIANO]
    assert nomi == ["ricette_salvate", "misure_salvate", "chat_salvate"]
    assert all(callable(p[2]) for p in _PIANO)   # ogni store ha il suo mapper
