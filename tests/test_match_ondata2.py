"""Rete di test — Ondata 2 del _MATCH curato (routes/deriva_gusti.py).
Funzione pura, niente rete. Blocca una regressione sui match AGGIUNTI il 18/10,
tutti con fdc_id verificati sul dataset ufficiale USDA SR Legacy (food.csv).
Se un id viene toccato per sbaglio, il test lo segnala: il valore e' la verita'
verificata, non un numero a caso.
"""
from routes.deriva_gusti import _MATCH, _ESCLUDI

# campione rappresentativo per categoria: ingrediente -> fdc_id SR Legacy verificato
ONDATA2_ATTESI = {
    "melanzana": 169228,
    "finocchio": 169385,
    "carciofo": 169205,
    "peperoncino": 170106,
    "pera": 169118,
    "mandarino": 169105,
    "mirtillo rosso": 171722,   # cranberry, non blueberry
    "basilico": 172232,
    "lenticchie": 172420,
    "ceci": 173756,
    "pecorino": 171249,         # Cheese, romano
    "merluzzo": 171955,
    "polpo": 174218,
    "coniglio": 172521,
    "pistacchio": 170184,
    "farro": 169745,
    "salsa di soia": 174277,    # risolve il pendente del 15/10 (prima era sbagliato -> Mustard)
}


def test_ondata2_id_presenti_e_corretti():
    for nome, fdc_id in ONDATA2_ATTESI.items():
        assert nome in _MATCH, f"manca il match ondata2: {nome!r}"
        assert _MATCH[nome] == fdc_id, (
            f"fdc_id cambiato per {nome!r}: atteso {fdc_id}, trovato {_MATCH[nome]}"
        )


def test_ondata2_distingue_mirtillo_da_mirtillo_rosso():
    # 'mirtillo' (blueberry) e 'mirtillo rosso' (cranberry) sono ingredienti diversi
    assert _MATCH.get("mirtillo") != _MATCH.get("mirtillo rosso")


def test_nessun_match_ondata2_viola_escludi():
    for nome in ONDATA2_ATTESI:
        assert not any(escl in nome.lower() for escl in _ESCLUDI)


def test_nessun_fdc_id_duplicato_tra_ingredienti_diversi():
    # due ingredienti distinti non dovrebbero puntare allo stesso fdc_id
    # (eccezione nota e voluta: alias dello stesso ingrediente gia' presenti nel dizionario)
    alias_noti = {
        frozenset({"olio di oliva", "olio d'oliva"}),
        frozenset({"pollo", "petto di pollo"}),
    }
    visti = {}
    for nome, fid in _MATCH.items():
        visti.setdefault(fid, []).append(nome)
    collisioni = {
        fid: nomi for fid, nomi in visti.items()
        if len(nomi) > 1 and frozenset(nomi) not in alias_noti
    }
    assert collisioni == {}, f"fdc_id condivisi da ingredienti diversi: {collisioni}"
