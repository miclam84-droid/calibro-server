"""Test PURI della macchina di ingestione scheletro Wikidata — niente rete, niente DB.
Verificano i parser (forma reale delle risposte Wikidata), il builder del nodo
scheletro (solo dati Wikidata, nessun gusto) e la logica fill-only (mai duplicare).
"""
from routes.ingest_skeleton import (
    _slug, _parse_ricerca, _rango_da_entita, _parse_specie,
    _nodo_scheletro, _fill_only, _sparql_specie, _Q_FAMIGLIA, _Q_SPECIE,
)


# --- _slug -------------------------------------------------------------------

def test_slug_normalizza_accenti_e_spazi():
    assert _slug("Malus doméstica") == "malus-domestica"
    assert _slug("Rubus idaeus (lampone)") == "rubus-idaeus-lampone"
    assert _slug("  Crataegus   ") == "crataegus"


def test_slug_vuoto():
    assert _slug("") == ""
    assert _slug(None) == ""


# --- _parse_ricerca (wbsearchentities) ---------------------------------------

def test_parse_ricerca_estrae_qid_in_ordine():
    d = {"search": [{"id": "Q46299", "label": "Rosaceae"},
                    {"id": "Q56783209", "label": "Rosaceæ"}]}
    assert _parse_ricerca(d) == ["Q46299", "Q56783209"]


def test_parse_ricerca_scarta_non_q_e_vuoto():
    assert _parse_ricerca({"search": [{"id": "P105"}, {"id": "Q1"}, {"id": None}]}) == ["Q1"]
    assert _parse_ricerca({}) == []
    assert _parse_ricerca(None) == []


# --- _rango_da_entita (wbgetentities P105) -----------------------------------

def _entita(qid, rango_qid):
    return {"entities": {qid: {"claims": {"P105": [
        {"mainsnak": {"datavalue": {"value": {"id": rango_qid}}}}]}}}}


def test_rango_riconosce_famiglia():
    assert _rango_da_entita(_entita("Q46299", _Q_FAMIGLIA), "Q46299") == _Q_FAMIGLIA


def test_rango_assente_o_malformato():
    assert _rango_da_entita({"entities": {"Q1": {"claims": {}}}}, "Q1") is None
    assert _rango_da_entita({}, "Q1") is None
    assert _rango_da_entita(None, "Q1") is None


# --- _parse_specie (SPARQL, forma reale con item URI) ------------------------

def _binding(**kv):
    return {k: {"value": v} for k, v in kv.items()}


def _sparql(rows):
    return {"results": {"bindings": rows}}


def test_parse_specie_forma_reale():
    d = _sparql([
        _binding(item="http://www.wikidata.org/entity/Q18550",
                 sci="Malus domestica", nome="melo"),
        _binding(item="http://www.wikidata.org/entity/Q1023525",
                 sci="Rubus niveus", nome="Rubus niveus"),
    ])
    out = _parse_specie(d)
    assert out[0] == {"qid": "Q18550", "nome": "melo", "nome_scientifico": "Malus domestica"}
    assert out[1] == {"qid": "Q1023525", "nome": "Rubus niveus", "nome_scientifico": "Rubus niveus"}


def test_parse_specie_usa_sci_se_manca_etichetta():
    d = _sparql([_binding(item="http://www.wikidata.org/entity/Q42", sci="Prunus avium")])
    assert _parse_specie(d) == [{"qid": "Q42", "nome": "Prunus avium", "nome_scientifico": "Prunus avium"}]


def test_parse_specie_porta_origine_se_presente():
    d = _sparql([_binding(item="http://www.wikidata.org/entity/Q1", sci="X", nome="x",
                          origine="Asia orientale")])
    assert _parse_specie(d)[0]["origine"] == "Asia orientale"


def test_parse_specie_dedup_per_qid():
    d = _sparql([
        _binding(item="http://www.wikidata.org/entity/Q1", nome="a"),
        _binding(item="http://www.wikidata.org/entity/Q1", nome="a-bis"),
    ])
    assert len(_parse_specie(d)) == 1


def test_parse_specie_salta_righe_senza_nome():
    d = _sparql([_binding(item="http://www.wikidata.org/entity/Q1")])  # né sci né label
    assert _parse_specie(d) == []


def test_parse_specie_vuota():
    assert _parse_specie({}) == []
    assert _parse_specie({"results": {"bindings": []}}) == []
    assert _parse_specie(None) == []


# --- _nodo_scheletro: SOLO dati Wikidata, nessun gusto -----------------------

def test_nodo_scheletro_onesto():
    s = {"qid": "Q18550", "nome": "melo", "nome_scientifico": "Malus domestica"}
    nid, nome, data = _nodo_scheletro(s, "Rosaceae", "Q46299")
    assert nid == "scheletro-melo-q18550"
    assert nome == "melo"
    assert data["kind"] == "scheletro"
    assert data["stato"] == "non_profilato"
    assert data["famiglia"] == "Rosaceae"
    assert data["famiglia_qid"] == "Q46299"
    assert data["wikidata_qid"] == "Q18550"
    assert data["fonte"] == "Wikidata CC0"
    assert data["nome_scientifico"] == "Malus domestica"


def test_nodo_scheletro_nessun_dato_di_gusto_inventato():
    nid, nome, data = _nodo_scheletro({"qid": "Q1", "nome": "x"}, "F", "Q2")
    vietati = {"dolce", "salato", "grasso", "acido", "umami", "amaro",
               "gusto", "tassonomia", "aroma", "profilo", "nutrienti"}
    assert vietati.isdisjoint(data.keys())
    assert "nome_scientifico" not in data  # non c'era -> non inventato


# --- _fill_only: mai duplicare un nodo esistente -----------------------------

def test_fill_only_scarta_per_qid_esistente():
    cand = [{"qid": "Q1", "nome": "a"}, {"qid": "Q2", "nome": "b"}]
    nuovi, saltati = _fill_only(cand, nomi_esistenti=set(), qid_esistenti={"Q1"})
    assert [c["qid"] for c in nuovi] == ["Q2"]
    assert saltati == 1


def test_fill_only_scarta_per_nome_esistente_case_insensitive():
    cand = [{"qid": "Q9", "nome": "Melo"}]
    nuovi, saltati = _fill_only(cand, nomi_esistenti={"melo"}, qid_esistenti=set())
    assert nuovi == [] and saltati == 1


def test_fill_only_dedup_dentro_al_batch():
    cand = [{"qid": "Q1", "nome": "a"}, {"qid": "Q1", "nome": "a"}]
    nuovi, saltati = _fill_only(cand, set(), set())
    assert len(nuovi) == 1 and saltati == 1


def test_fill_only_tutti_nuovi():
    cand = [{"qid": "Q1", "nome": "a"}, {"qid": "Q2", "nome": "b"}]
    nuovi, saltati = _fill_only(cand, set(), set())
    assert len(nuovi) == 2 and saltati == 0


# --- _sparql_specie: query ben formata ---------------------------------------

def test_sparql_specie_ben_formata():
    q = _sparql_specie("Q46299", limite=50, offset=100)
    assert "wd:Q46299" in q
    assert "wdt:P171*" in q              # catena parent taxon
    assert ("wd:" + _Q_SPECIE) in q      # rango specie
    assert "LIMIT 50" in q and "OFFSET 100" in q
