"""Rete di test — raggruppamento per famiglia della base_aromatica (rilevanza).
Funzioni PURE, niente DB ne' rete: dimostrano che le varieta' quasi-duplicate
dello stesso ingrediente (lime*, arancia*) collassano su UN rappresentante, mentre
ingredienti legittimamente diversi (mandarino vs satsuma, olio di oliva vs olio di
semi) restano separati — tesi del prodotto: ONESTA' DEI DATI, conservativo.
"""
from routes.criteri import (
    _chiave_famiglia,
    _rappresentante_migliore,
    _raggruppa_famiglia,
)


def _rel(nome, condivisi, robustezza="moderato"):
    """Costruisce una relazione base_aromatica finta con la forma reale dell'endpoint."""
    return {
        "ingrediente": nome,
        "criterio": "base_aromatica",
        "evidenza": {"composti_condivisi": condivisi, "profilo_partner": 100,
                     "indice_rarita": 0.5, "composti_caratterizzanti": []},
        "robustezza": robustezza,
        "perche": "condivide composti caratterizzanti",
    }


# --- CHIAVE DI FAMIGLIA ----------------------------------------------------------

def test_chiave_prima_parola_significativa():
    assert _chiave_famiglia("lime") == "lime"
    assert _chiave_famiglia("lime kaffir") == "lime"
    assert _chiave_famiglia("lime italiano") == "lime"
    assert _chiave_famiglia("Lime Messicano") == "lime"  # case-insensitive


def test_chiave_salta_articoli_e_preposizioni_regionali():
    # "della California" e' un regionalismo: la testa resta "arancia"
    assert _chiave_famiglia("arancia della California") == "arancia"
    assert _chiave_famiglia("arancia israeliana") == "arancia"
    assert _chiave_famiglia("arancia scimmia") == "arancia"


def test_chiave_x_di_y_resta_distinto():
    # "X di Y": il complemento e' l'identita' vera -> chiave allargata (NON accorpa olii diversi)
    assert _chiave_famiglia("olio di oliva") == "olio oliva"
    assert _chiave_famiglia("olio di semi") == "olio semi"
    assert _chiave_famiglia("olio di oliva") != _chiave_famiglia("olio di semi")
    # apostrofo trattato come "di"
    assert _chiave_famiglia("olio d'oliva") == "olio oliva"
    # succo di limone != limone: due ingredienti diversi, restano separati
    assert _chiave_famiglia("succo di limone") != _chiave_famiglia("limone")


def test_parole_diverse_non_accorpate():
    # conservativo: mandarino e satsuma NON condividono la testa -> restano separati
    assert _chiave_famiglia("mandarino") != _chiave_famiglia("satsuma")
    assert _chiave_famiglia("lime") != _chiave_famiglia("arancia")


# --- SCELTA DEL RAPPRESENTANTE ---------------------------------------------------

def test_rappresentante_preferisce_nome_semplice():
    # il nome base vince sulla varieta' esotica ANCHE con meno composti condivisi
    plain = _rel("lime", 20)
    variet = _rel("lime kaffir", 99)
    assert _rappresentante_migliore(plain, variet) is True
    assert _rappresentante_migliore(variet, plain) is False


def test_rappresentante_per_composti_condivisi():
    # a parita' di numero di parole, decide composti_condivisi
    a = _rel("lime kaffir", 30)
    b = _rel("lime italiano", 12)
    assert _rappresentante_migliore(a, b) is True
    assert _rappresentante_migliore(b, a) is False


def test_rappresentante_parita_usa_robustezza():
    # stesse parole, stessi composti -> decide la robustezza
    a = _rel("lime italiano", 20, "marcato")
    b = _rel("lime kaffir", 20, "debole")
    assert _rappresentante_migliore(a, b) is True
    assert _rappresentante_migliore(b, a) is False


# --- RAGGRUPPAMENTO COMPLETO (scenario "limone") ---------------------------------

def _scenario_limone():
    """La base_aromatica di 'limone' PRIMA del raggruppamento: affogata di agrumi
    quasi-duplicati. (Numeri plausibili, ordinati per rilevanza decrescente.)"""
    return [
        _rel("lime kaffir", 34, "marcato"),
        _rel("lime", 31, "marcato"),
        _rel("lime italiano", 28, "moderato"),
        _rel("lime messicano", 25, "moderato"),
        _rel("arancia", 22, "moderato"),
        _rel("arancia della California", 20, "moderato"),
        _rel("arancia israeliana", 18, "debole"),
        _rel("arancia scimmia", 16, "debole"),
        _rel("satsuma", 14, "debole"),
        _rel("mandarino", 13, "moderato"),
        _rel("pompelmo", 11, "moderato"),
    ]


def test_raggruppa_limone_collassa_le_varieta():
    dopo = _raggruppa_famiglia(_scenario_limone())
    nomi = [r["ingrediente"] for r in dopo]
    # cinque famiglie distinte per prima-parola: lime, arancia, satsuma, mandarino, pompelmo
    assert nomi == ["lime", "arancia", "satsuma", "mandarino", "pompelmo"]
    # il rappresentante di "lime" e' il nome BASE (lime, 31), non la varieta' "lime kaffir" (34)
    assert dopo[0]["ingrediente"] == "lime"
    assert dopo[0]["evidenza"]["composti_condivisi"] == 31
    # il rappresentante di "arancia" e' "arancia" (22), non i regionalismi sotto
    assert dopo[1]["ingrediente"] == "arancia"
    assert dopo[1]["evidenza"]["composti_condivisi"] == 22


def test_raggruppa_riduce_il_conteggio():
    prima = _scenario_limone()
    dopo = _raggruppa_famiglia(prima)
    assert len(prima) == 11
    assert len(dopo) == 5  # 20 regionalismi -> 5 ingredienti leggibili


def test_raggruppa_conserva_ingredienti_diversi():
    # due ingredienti chiaramente diversi non devono MAI sparire a vicenda
    dopo = _raggruppa_famiglia([_rel("basilico", 20), _rel("menta", 18), _rel("timo", 15)])
    assert sorted(r["ingrediente"] for r in dopo) == ["basilico", "menta", "timo"]


def test_raggruppa_preserva_la_forma_del_dizionario():
    # il raggruppamento non deve toccare le chiavi di ogni relazione (contratto congelato)
    dopo = _raggruppa_famiglia(_scenario_limone())
    attese = {"ingrediente", "criterio", "evidenza", "robustezza", "perche"}
    for r in dopo:
        assert set(r.keys()) == attese
        assert set(r["evidenza"].keys()) == {
            "composti_condivisi", "profilo_partner", "indice_rarita", "composti_caratterizzanti"}


def test_raggruppa_order_preserving():
    # l'ordine finale segue la prima comparsa di ogni famiglia (rilevanza decrescente)
    dopo = _raggruppa_famiglia(_scenario_limone())
    nomi = [r["ingrediente"] for r in dopo]
    assert nomi.index("lime") < nomi.index("arancia") < nomi.index("mandarino")


def test_raggruppa_lista_vuota():
    assert _raggruppa_famiglia([]) == []
