"""Rete di test — ONDATA INGREDIENTI.

PEZZO A (deriva-gusti-search resiliente): un nodo storto che SOLLEVA durante la
derivazione/scrittura NON deve piu' abbattere il lotto (prima -> 500). Il runner
per-nodo deve: saltarlo, contarlo in 'saltati_errore', tenere la transazione sana
(rollback al savepoint) e CONTINUARE coi nodi dopo.

PEZZO B (travaso nomi EN): la funzione pura di pianificazione deve travasare il
nome EN dalla tabella ingredienti_nomi SOLO dove manca (fill-only) e SOLO se c'e'
corrispondenza (niente invenzioni).

Niente DB ne' rete: cursori finti e funzioni pure.
"""
import flask

import routes.deriva_gusti_search as dgs
import routes.travaso_nomi as tn


# ----------------------------------------------------------------------------
# PEZZO A
# ----------------------------------------------------------------------------

class _CurFinto:
    """Cursore finto: registra le operazioni savepoint, non tocca nessun DB."""
    def __init__(self):
        self.ops = []

    def execute(self, sql, *a, **k):
        self.ops.append(sql)


def test_sweep_salta_nodo_che_solleva_e_continua(monkeypatch):
    # Il nodo di mezzo solleva (simula un dettaglio USDA storto -> derivazione che scoppia).
    def _fake_elabora(nid, nome, data, key, soglia, cur, esegui):
        if nid == "bad":
            raise ValueError("dettaglio USDA malformato")
        return {"categoria": "alta", "ricerca_fatta": True,
                "voce": {"nodo": nid, "nome": nome}, "scritto": bool(esegui)}

    monkeypatch.setattr(dgs, "_elabora_nodo", _fake_elabora)

    righe = [("ok1", "aglio", {}), ("bad", "nodo storto", {}), ("ok2", "cipolla", {})]
    cur = _CurFinto()

    # NON deve sollevare: il lotto completa.
    cont, alta, bassa, errori = dgs._sweep_nodi(righe, key="k", soglia=0.6,
                                                limite=999, cur=cur, esegui=True)

    assert cont["saltati_errore"] == 1          # il nodo storto e' contato, non propagato
    assert cont["consumati"] == 3               # tutti e tre visitati
    assert len(alta) == 2                        # i due buoni sono passati
    assert cont["scritti"] == 2
    assert errori and errori[0]["nodo"] == "bad"
    # transazione tenuta sana: sul nodo rotto e' stato emesso un ROLLBACK TO SAVEPOINT
    assert any("ROLLBACK TO SAVEPOINT" in op for op in cur.ops)


def test_sweep_rispetta_il_limite_ricerche(monkeypatch):
    def _fake_elabora(nid, nome, data, key, soglia, cur, esegui):
        return {"categoria": "bassa", "ricerca_fatta": True,
                "voce": {"nodo": nid}, "scritto": False}

    monkeypatch.setattr(dgs, "_elabora_nodo", _fake_elabora)
    righe = [(str(i), "x", {}) for i in range(10)]
    cont, alta, bassa, errori = dgs._sweep_nodi(righe, key="k", soglia=0.6,
                                                limite=3, cur=_CurFinto(), esegui=False)
    assert cont["ricerche"] == 3                # si ferma al limite
    assert cont["consumati"] == 3


def test_sweep_nodo_con_json_rotto_e_saltato(monkeypatch):
    # Qui NON monkeypatchiamo _elabora_nodo: un data non-dict e non-JSON valido
    # deve sollevare dentro _elabora_nodo (json.loads) ed essere contato come errore.
    righe = [("rotto", "nome", "{non-json")]
    cont, alta, bassa, errori = dgs._sweep_nodi(righe, key="k", soglia=0.6,
                                                limite=999, cur=_CurFinto(), esegui=False)
    assert cont["saltati_errore"] == 1
    assert cont["consumati"] == 1


# ----------------------------------------------------------------------------
# PEZZO B
# ----------------------------------------------------------------------------

def test_pianifica_travaso_fill_only_e_niente_invenzioni():
    nodi = [
        ("ing-a", {"nomi": {"it": "aglio"}}),            # senza EN, c'e' in tabella -> travaso
        ("ing-b", {"nomi": {"it": "basilico", "en": "basil"}}),  # ha gia' EN -> saltato (fill-only)
        ("ing-c", {"nomi": {"it": "cardo"}}),            # senza EN e senza corrispondenza -> saltato
        ("ing-d", {}),                                    # nessun blocco nomi, c'e' in tabella -> travaso
    ]
    nomi_en = {"ing-a": "garlic", "ing-d": "something", "ing-b": "IGNORATO"}

    da_scrivere, candidati, trovati, senza = tn._pianifica_travaso(nodi, nomi_en)

    scritti = {nid: en for nid, en, _ in da_scrivere}
    assert scritti == {"ing-a": "garlic", "ing-d": "something"}
    assert candidati == 3        # a, c, d (b ha gia' EN, non e' candidato)
    assert trovati == 2          # a, d
    assert senza == 1            # c
    # il dd nuovo porta data.nomi.en valorizzato senza perdere gli altri nomi
    dd_a = [dd for nid, en, dd in da_scrivere if nid == "ing-a"][0]
    assert dd_a["nomi"]["en"] == "garlic"
    assert dd_a["nomi"]["it"] == "aglio"
    # fill-only: il nodo che aveva gia' EN non e' stato toccato
    assert "ing-b" not in scritti


def test_ha_en():
    assert tn._ha_en({"nomi": {"en": "basil"}}) is True
    assert tn._ha_en({"nomi": {"en": ""}}) is False
    assert tn._ha_en({"nomi": {"it": "aglio"}}) is False
    assert tn._ha_en({}) is False


def test_travaso_endpoint_nega_senza_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "segreto")
    monkeypatch.setenv("DATABASE_URL", "postg://finto")
    app = flask.Flask(__name__)
    app.register_blueprint(tn.bp_travaso_nomi)
    c = app.test_client()
    # senza ?s -> 403 (compare_digest con stringa vuota), niente DB toccato
    r = c.get("/admin/travaso-nomi-en")
    assert r.status_code == 403
    # secret sbagliato -> 403
    r = c.get("/admin/travaso-nomi-en?s=sbagliato")
    assert r.status_code == 403
