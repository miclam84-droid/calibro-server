"""Test di _nome_en (routes/deriva_gusti_search): il motore ora usa il NOME
inglese dei nodi Ahn in categoria alimentare, invece di saltarli. Il cancello
di confidenza (verificato altrove, contro USDA) resta il garante del match."""
from routes.deriva_gusti_search import _nome_en


def test_nodo_ahn_alimentare_usa_il_nome():
    # nodo Ahn in categoria cibo, senza nomi.en: il name (slug EN) va usato
    en, fonte = _nome_en("brussels_sprout", {"ahn_id": "123", "categoria": "vegetable"})
    assert en == "brussels sprout"
    assert fonte == "nodo.name(ahn)"


def test_nodo_ahn_non_alimentare_non_usa_il_nome():
    # categoria botanica/non-cibo: NON si usa il name (evita query a vuoto su USDA)
    en, fonte = _nome_en("abies_alba", {"ahn_id": "999", "categoria": "plant"})
    assert en is None

    en2, _ = _nome_en("rosa_oil", {"ahn_id": "998", "categoria": "plant derivative"})
    assert en2 is None


def test_nomi_en_esplicito_vince():
    en, fonte = _nome_en("qualcosa", {"ahn_id": "1", "categoria": "vegetable",
                                       "nomi": {"en": "kimchi"}})
    assert en == "kimchi"
    assert fonte == "nodo.nomi.en"


def test_nodo_italiano_con_alias_invariato():
    # nodo NON-Ahn (nessun ahn_id): resta la via alias IT->EN di prima
    en, fonte = _nome_en("cipolla", {})
    assert en == "onion"
    assert fonte == "alias_ahn"


def test_nodo_senza_en_ne_alias_resta_none():
    en, fonte = _nome_en("ingrediente-inventato-xyz", {})
    assert en is None
