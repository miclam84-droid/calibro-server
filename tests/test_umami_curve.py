# Test della MACCHINA umami: curva glutammato->0-10 e parser CSV.
# Funzioni pure, nessun DB, nessun numero inventato.
import os
import tempfile
import importlib

from routes.deriva_umami import _deriva, _UMAMI, _interp


def test_curva_estremi_clamp():
    # Sotto/oltre gli estremi: si appiattisce, niente valori fuori 0-10.
    assert _deriva(0)["val"] == 0
    assert _deriva(-50)["val"] == 0
    assert _deriva(3000)["val"] == 10
    assert _deriva(99999)["val"] == 10


def test_curva_ancore():
    # Punti di ancoraggio della curva.
    assert _deriva(50)["val"] == 2
    assert _deriva(150)["val"] == 4
    assert _deriva(400)["val"] == 6
    assert _deriva(1200)["val"] == 8


def test_curva_monotona():
    vals = [_deriva(mg)["val"] for mg in (0, 10, 50, 150, 400, 1200, 3000)]
    assert vals == sorted(vals), "la curva deve essere non-decrescente"
    assert all(0 <= v <= 10 for v in vals)


def test_deriva_conserva_grezzo():
    d = _deriva(246.4)
    assert d["grezzo"] == 246.4
    assert 0 <= d["val"] <= 10


def test_interp_interno():
    # Un punto a meta' tra 50(->2) e 150(->4) sta tra 2 e 4.
    v = _interp(100, _UMAMI)
    assert 2 < v < 4


def test_tabella_vuota_e_commenti(monkeypatch):
    # CSV con solo header + commenti # -> tabella vuota (zero dati fabbricati).
    import routes.deriva_umami as mod
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("# commento\nnome,glutammato_mg_100g,fonte\n")
        path = f.name
    try:
        monkeypatch.setattr(mod, "_CSV", path)
        monkeypatch.setattr(mod, "_TBL", None)
        assert mod._tabella() == {}
    finally:
        os.unlink(path)


def test_tabella_parsa_e_scarta_righe_rotte(monkeypatch):
    import routes.deriva_umami as mod
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("nome,glutammato_mg_100g,fonte\n")
        f.write("pomodoro,246,FonteX\n")        # valida
        f.write("# riga_commento,99,x\n")         # commento -> scartata
        f.write("rotta,nonnumero,FonteY\n")       # mg non numerico -> scartata
        f.write(",50,FonteZ\n")                    # nome vuoto -> scartata
        path = f.name
    try:
        monkeypatch.setattr(mod, "_CSV", path)
        monkeypatch.setattr(mod, "_TBL", None)
        tbl = mod._tabella()
        assert set(tbl.keys()) == {"pomodoro"}
        assert tbl["pomodoro"] == (246.0, "FonteX")
    finally:
        os.unlink(path)


def test_file_reale_e_vuoto_di_dati():
    # Il CSV versionato nel repo non deve contenere numeri "a memoria".
    import routes.deriva_umami as mod
    mod._TBL = None
    assert mod._tabella() == {}, "data/glutammato.csv deve essere senza dati finche' non arriva una fonte"
