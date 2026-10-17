# Test della MACCHINA amaro: curva marcatori->0-10, parser registro, match composti->marcatori.
# Funzioni PURE, nessun DB, nessun numero/composto inventato.
import os
import csv
import tempfile

from routes.deriva_amaro import (
    _indice_amaro, _AMARO, _marcatori, _registro, _norm, _interp,
)


def test_curva_estremi_clamp():
    assert _indice_amaro(0) == 0
    assert _indice_amaro(-3) == 0          # input assurdo -> clamp a 0
    assert _indice_amaro(8) == 10
    assert _indice_amaro(99) == 10         # oltre l'estremo -> clamp a 10


def test_curva_ancore():
    assert _indice_amaro(1) == 4
    assert _indice_amaro(2) == 6
    assert _indice_amaro(3) == 7
    assert _indice_amaro(4) == 8
    assert _indice_amaro(6) == 9


def test_curva_monotona_e_in_range():
    vals = [_indice_amaro(n) for n in range(0, 10)]
    assert vals == sorted(vals), "la curva deve essere non-decrescente"
    assert all(0 <= v <= 10 for v in vals)


def test_interp_interno():
    # 5 marcatori sta tra l'ancora 4(->8) e 6(->9): valore strettamente tra 8 e 9.
    v = _interp(5, _AMARO)
    assert 8 < v < 9


def test_match_per_cas_preferito():
    per_nome = {"caffeina": "58-08-2", "caffeine": "58-08-2"}
    per_cas = {"58-08-2": "58-08-2"}
    composti = [{"nome": "qualcosa_di_strano", "cas": "58-08-2"}]
    assert _marcatori(composti, per_nome, per_cas) == ["58-08-2"]


def test_match_per_nome_fallback():
    per_nome = {"chinina": "130-95-0"}
    per_cas = {"130-95-0": "130-95-0"}
    composti = [{"nome": "Chinina", "cas": None}]   # nome con maiuscola, senza CAS
    assert _marcatori(composti, per_nome, per_cas) == ["130-95-0"]


def test_sinonimi_contano_una_volta():
    # "caffeina" e "caffeine" sono lo stesso composto (stesso CAS): UN solo marcatore.
    per_nome = {"caffeina": "58-08-2", "caffeine": "58-08-2"}
    per_cas = {"58-08-2": "58-08-2"}
    composti = [{"nome": "caffeina"}, {"nome": "caffeine", "cas": "58-08-2"}]
    assert _marcatori(composti, per_nome, per_cas) == ["58-08-2"]


def test_nessun_marcatore():
    per_nome = {"chinina": "130-95-0"}
    per_cas = {"130-95-0": "130-95-0"}
    composti = [{"nome": "limonene", "cas": "138-86-3"}]  # aromatico, non amaro
    assert _marcatori(composti, per_nome, per_cas) == []


def test_marcatori_robusto_a_input_sporco():
    per_nome = {"chinina": "130-95-0"}
    per_cas = {"130-95-0": "130-95-0"}
    assert _marcatori(None, per_nome, per_cas) == []
    assert _marcatori("non una lista", per_nome, per_cas) == []
    assert _marcatori([None, 42, "x", {"nope": 1}], per_nome, per_cas) == []


def test_parser_registro_e_chiave_canonica(monkeypatch):
    import routes.deriva_amaro as mod
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("compound,cas,classe,fonte\n")
        f.write("caffeine,58-08-2,metilxantina,FonteX\n")
        f.write("caffeina,58-08-2,metilxantina,FonteX\n")   # sinonimo IT, stesso CAS
        f.write("# commento,1-1-1,x,y\n")                    # ignorata
        f.write("senzacas,,classeY,FonteY\n")               # chiave canonica = nome
        path = f.name
    try:
        monkeypatch.setattr(mod, "_REG", None)
        monkeypatch.setattr(mod, "_CSV", path)
        per_nome, per_cas, meta = mod._registro()
        # i due sinonimi condividono la chiave canonica (il CAS)
        assert per_nome["caffeine"] == "58-08-2"
        assert per_nome["caffeina"] == "58-08-2"
        assert per_cas["58-08-2"] == "58-08-2"
        assert "58-08-2" in meta and meta["58-08-2"]["classe"] == "metilxantina"
        # voce senza CAS: chiave canonica = nome normalizzato
        assert per_nome["senzacas"] == "senzacas"
        assert meta["senzacas"]["fonte"] == "FonteY"
    finally:
        mod._REG = None
        os.unlink(path)


def test_registro_reale_popolato_e_con_fonte():
    # Il registro versionato deve esistere, essere popolato e avere una fonte per ogni voce.
    import routes.deriva_amaro as mod
    mod._REG = None
    per_nome, per_cas, meta = mod._registro()
    assert len(meta) >= 5, "il registro reale deve avere i composti amari documentati"
    for k, v in meta.items():
        assert v["fonte"], f"il composto {v['compound']} deve avere una fonte citabile"
    # alcuni marcatori chiave attesi (per CAS, indipendente dalla lingua)
    assert "130-95-0" in per_cas, "chinina attesa nel registro"
    assert "58-08-2" in per_cas, "caffeina attesa nel registro"


def test_registro_csv_niente_righe_senza_fonte_o_compound():
    # Controllo diretto sul CSV reale: ogni riga-dato ha compound E fonte (no provenienza vuota).
    path = os.path.join(os.path.dirname(__file__), "..", "data", "composti_amari.csv")
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            comp = (r.get("compound") or "").strip()
            if not comp or comp.startswith("#"):
                continue
            assert (r.get("fonte") or "").strip(), f"riga senza fonte: {comp}"
            assert (r.get("classe") or "").strip(), f"riga senza classe: {comp}"
