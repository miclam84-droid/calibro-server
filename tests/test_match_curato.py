"""Rete di test — sanità del _MATCH curato (routes/deriva_gusti.py).
Funzione pura, niente rete. Regola di sicurezza: "mai derivare un raro/DOP/
presidio da un match generico". Il dizionario _MATCH mappa ingredienti italiani
comuni a fdc_id USDA verificati; _ESCLUDI elenca i termini da NON derivare mai
automaticamente (DOP/IGP/presìdi/varietà rare). Nessuna chiave di _MATCH deve
contenere un termine di _ESCLUDI, altrimenti una varietà rara verrebbe derivata
da un dato generico.
"""
from routes.deriva_gusti import _MATCH, _ESCLUDI


def test_nessuna_chiave_match_contiene_termine_escludi():
    violazioni = [
        (chiave, escl)
        for chiave in _MATCH
        for escl in _ESCLUDI
        if escl in chiave.lower()
    ]
    assert violazioni == [], f"chiavi _MATCH che contengono un termine _ESCLUDI: {violazioni}"


def test_match_e_escludi_non_vuoti():
    # se uno dei due si svuota, il controllo sopra passerebbe a vuoto senza valore
    assert len(_MATCH) > 0
    assert len(_ESCLUDI) > 0


def test_fdc_id_sono_interi_positivi():
    # i fdc_id curati devono essere id USDA reali (interi > 0), non placeholder
    assert all(isinstance(v, int) and v > 0 for v in _MATCH.values())
