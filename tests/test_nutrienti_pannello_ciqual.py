# Test del pannello nutrizionale CIQUAL: estrazione PURA da una riga CIQUAL finta.
# Nessun DB, nessuna rete. Verifica l'ONESTÀ: solo i campi realmente presenti nella
# tabella CIQUAL normalizzata (zuccheri_g, grasso_g, sodio_mg) finiscono nel pannello;
# energia/proteine/carboidrati/fibre/grassi saturi NON esistono in CIQUAL e non si
# scrivono mai (niente zero inventato).
from routes.deriva_gusti_ciqual import _pannello_nutrienti

# Riga CIQUAL normalizzata finta ma realistica (forma di _tabella(): chiavi interne
# che mappano le colonne reali zuccheri_g/grasso_g/sodio_mg/acidi_organici_g).
RIGA_MELA = {"nome": "Apple, raw", "zuccheri": 11.6, "grasso": 0.17, "sodio": 1.0, "acidi": 0.5}


def test_pannello_campi_presenti():
    p = _pannello_nutrienti(RIGA_MELA)
    assert p["grassi"] == {"valore": 0.17, "unita": "g/100g"}
    assert p["zuccheri"] == {"valore": 11.6, "unita": "g/100g"}
    assert p["sodio"] == {"valore": 1.0, "unita": "mg/100g"}


def test_pannello_non_inventa_campi_assenti_da_ciqual():
    # CIQUAL normalizzato non ha energia/proteine/carboidrati/fibre/grassi saturi:
    # non devono MAI comparire, anche con la riga piena.
    p = _pannello_nutrienti(RIGA_MELA)
    for assente in ("energia_kcal", "proteine", "carboidrati", "fibre", "grassi_saturi"):
        assert assente not in p


def test_pannello_salta_valore_none_niente_zero():
    riga = {"zuccheri": 5.0, "grasso": None, "sodio": None, "acidi": None}
    p = _pannello_nutrienti(riga)
    assert p == {"zuccheri": {"valore": 5.0, "unita": "g/100g"}}
    assert "grassi" not in p   # None -> niente zero inventato
    assert "sodio" not in p


def test_pannello_arrotonda_a_due_decimali():
    p = _pannello_nutrienti({"grasso": 0.1734, "zuccheri": 10.389, "sodio": 1.0})
    assert p["grassi"]["valore"] == 0.17
    assert p["zuccheri"]["valore"] == 10.39


def test_pannello_vuoto_su_riga_vuota_o_none():
    assert _pannello_nutrienti({}) == {}
    assert _pannello_nutrienti(None) == {}
    assert _pannello_nutrienti({"nome": "x", "acidi": 2.0}) == {}  # solo acidi -> non è un campo pannello
