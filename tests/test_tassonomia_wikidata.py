"""Test PURI dei parser Wikidata — niente rete, niente DB.
Dimostrano che la forma reale delle risposte Wikidata viene letta correttamente:
wbsearchentities -> QID, SPARQL -> {nome_scientifico, famiglia, genere, origine}.
"""
from routes.tassonomia_wikidata import _parse_search, _parse_taxonomia, _sparql_query


def test_parse_search_estrae_qid_in_ordine():
    d = {"search": [{"id": "Q23501", "label": "pomodoro"},
                    {"id": "Q20638126", "label": "Tomato"}]}
    assert _parse_search(d) == ["Q23501", "Q20638126"]


def test_parse_search_vuoto():
    assert _parse_search({}) == []
    assert _parse_search({"search": []}) == []
    assert _parse_search(None) == []


def test_parse_search_scarta_non_q():
    d = {"search": [{"id": "P225"}, {"id": "Q1"}, {"id": None}]}
    assert _parse_search(d) == ["Q1"]


def _binding(**kv):
    return {"results": {"bindings": [{k: {"value": v} for k, v in kv.items()}]}}


def test_parse_taxonomia_completa():
    d = _binding(sci="Solanum lycopersicum", familyName="Solanaceae",
                 genusName="Solanum", originLabel="America centrale e meridionale")
    out = _parse_taxonomia(d)
    assert out == {"nome_scientifico": "Solanum lycopersicum", "famiglia": "Solanaceae",
                   "genere": "Solanum", "origine": "America centrale e meridionale"}


def test_parse_taxonomia_parziale_solo_presenti():
    d = _binding(sci="Ocimum basilicum", familyName="Lamiaceae")
    out = _parse_taxonomia(d)
    assert out == {"nome_scientifico": "Ocimum basilicum", "famiglia": "Lamiaceae"}
    assert "genere" not in out and "origine" not in out


def test_parse_taxonomia_vuota():
    assert _parse_taxonomia({}) == {}
    assert _parse_taxonomia({"results": {"bindings": []}}) == {}
    assert _parse_taxonomia(None) == {}


def test_parse_taxonomia_ignora_stringhe_vuote():
    d = _binding(sci="   ", familyName="Cucurbitaceae")
    out = _parse_taxonomia(d)
    assert out == {"famiglia": "Cucurbitaceae"}  # sci vuoto scartato


def test_sparql_query_ben_formata():
    q = _sparql_query("Q23501")
    assert "wd:Q23501" in q
    assert "wdt:P225" in q          # nome scientifico
    assert "wdt:P171*" in q         # catena parent taxon
    assert "Q35409" in q and "Q34740" in q   # ranghi famiglia e genere
    assert "wdt:P495" in q          # origine
    assert q.strip().endswith("LIMIT 1")
