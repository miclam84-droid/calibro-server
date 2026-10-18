# Test della rilevanza del match col patrimonio in /v1/diagnosi (funzioni pure, niente DB).
# Il bug: "troppo"/"poco" matchavano ogni sintomo → 150+ cause-spazzatura tutte "da fonte".
from routes.api import _parole_sintomo, _rilevanza_patrimonio


def test_togli_parole_vuote():
    assert _parole_sintomo("pane troppo denso") == {"pane", "denso"}
    assert _parole_sintomo("il drink e' troppo dolce") == {"drink", "dolce"}
    # solo stopword -> nessuna parola di contenuto -> niente match (meglio vuoto che spazzatura)
    assert _parole_sintomo("troppo poco") == set()


def test_match_token_esatto_pesa():
    p = _parole_sintomo("maionese impazzita")
    assert _rilevanza_patrimonio(p, "la maionese e' impazzita") > 0
    # match su token esatto (maionese) pesa piu' del contenimento debole
    assert _rilevanza_patrimonio(p, "la maionese e' impazzita") >= 2


def test_niente_match_niente_rilevanza():
    # "pane denso" NON deve matchare "gelato troppo duro" (prima lo faceva via "troppo")
    assert _rilevanza_patrimonio({"pane", "denso"}, "gelato troppo duro") == 0


def test_parole_vuote_nessun_match():
    assert _rilevanza_patrimonio(set(), "qualsiasi sintomo") == 0


def test_match_debole_parola_lunga():
    # nessun token esatto, ma "lievitazione" (>=5) contenuta -> match debole > 0
    assert _rilevanza_patrimonio({"lievitazione"}, "problema di lievitazione lenta") > 0
