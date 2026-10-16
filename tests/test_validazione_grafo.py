# Test del gate di forma validazione_grafo + helper db.assicura_worker_log.
# Tutto PURO: nessun DB reale, nessuna rete.
import validazione_grafo as vg


# ----------------------------- NODI -----------------------------

def test_nodo_valido_passa():
    ok, problemi = vg.valida_nodo({
        "id": "fen-aw",
        "type": "Fenomeno",
        "name": "Attività acqua (Aw)",
        "domain": "trasversale",
        "data": {"target": "Aw 0,85", "strumento": "awmetro"},
    })
    assert ok is True
    assert problemi == []


def test_nodo_minimo_senza_opzionali_passa():
    # domain e data sono nullable/opzionali: il record minimo è valido.
    ok, problemi = vg.valida_nodo({"id": "prod-x", "type": "Prodotto", "name": "X"})
    assert ok is True, problemi
    assert problemi == []


def test_nodo_chiave_obbligatoria_mancante_bocciato():
    # manca `type` (NOT NULL): deve fallire con problema chiaro su 'type'.
    ok, problemi = vg.valida_nodo({"id": "prod-x", "name": "X"})
    assert ok is False
    assert any("type" in p for p in problemi)


def test_nodo_data_non_dict_bocciato():
    # il JSONB deve essere un oggetto: una stringa è drift e va bocciata.
    ok, problemi = vg.valida_nodo({
        "id": "prod-x", "type": "Prodotto", "name": "X", "data": "non-un-oggetto",
    })
    assert ok is False
    assert any("data" in p and "dict" in p for p in problemi)


def test_nodo_id_vuoto_bocciato():
    ok, problemi = vg.valida_nodo({"id": "   ", "type": "Prodotto", "name": "X"})
    assert ok is False
    assert any("id" in p for p in problemi)


def test_nodo_type_tipo_sbagliato_bocciato():
    ok, problemi = vg.valida_nodo({"id": "x", "type": 123, "name": "X"})
    assert ok is False
    assert any("type" in p and "str" in p for p in problemi)


def test_nodo_domain_tipo_sbagliato_bocciato():
    ok, problemi = vg.valida_nodo({
        "id": "x", "type": "Prodotto", "name": "X", "domain": 7,
    })
    assert ok is False
    assert any("domain" in p for p in problemi)


def test_nodo_chiave_inattesa_bocciata():
    # 'colore' non è una colonna: segnalata come drift.
    ok, problemi = vg.valida_nodo({
        "id": "x", "type": "Prodotto", "name": "X", "colore": "rosso",
    })
    assert ok is False
    assert any("colore" in p for p in problemi)


def test_nodo_type_valore_libero_passa():
    # vocabolario APERTO: 'Ingrediente' esiste nei dati reali e NON va rifiutato.
    ok, problemi = vg.valida_nodo({"id": "ing-x", "type": "Ingrediente", "name": "X"})
    assert ok is True, problemi


def test_nodo_non_dict_bocciato():
    ok, problemi = vg.valida_nodo(["non", "un", "dict"])
    assert ok is False
    assert problemi


# ----------------------------- ARCHI -----------------------------

def test_arco_valido_passa():
    ok, problemi = vg.valida_arco({
        "from_id": "fen-aw",
        "to_id": "prod-confettura-conserva",
        "relation": "si_manifesta_in",
        "data": {"target": "Aw <0,85"},
    })
    assert ok is True
    assert problemi == []


def test_arco_minimo_passa():
    ok, problemi = vg.valida_arco({
        "from_id": "a", "to_id": "b", "relation": "influenza",
    })
    assert ok is True, problemi


def test_arco_relation_mancante_bocciato():
    ok, problemi = vg.valida_arco({"from_id": "a", "to_id": "b"})
    assert ok is False
    assert any("relation" in p for p in problemi)


def test_arco_data_lista_bocciata():
    ok, problemi = vg.valida_arco({
        "from_id": "a", "to_id": "b", "relation": "influenza", "data": [1, 2],
    })
    assert ok is False
    assert any("data" in p for p in problemi)


def test_arco_chiave_inattesa_bocciata():
    ok, problemi = vg.valida_arco({
        "from_id": "a", "to_id": "b", "relation": "influenza", "peso": 0.9,
    })
    assert ok is False
    assert any("peso" in p for p in problemi)


# --------------------- helper db.assicura_worker_log ---------------------

def test_assicura_worker_log_emette_ddl_idempotente():
    import db

    class FakeCur:
        def __init__(self):
            self.eseguiti = []

        def execute(self, sql, params=None):
            self.eseguiti.append(sql)

    cur = FakeCur()
    db.assicura_worker_log(cur)
    assert len(cur.eseguiti) == 1
    sql = cur.eseguiti[0]
    assert "CREATE TABLE IF NOT EXISTS worker_log" in sql
    assert "id SERIAL PRIMARY KEY" in sql
    assert "ts TIMESTAMP DEFAULT NOW()" in sql
    assert "testo TEXT" in sql


def test_assicura_worker_log_non_committa():
    # L'helper NON deve committare: il FakeCur non ha commit, quindi se
    # l'helper provasse a committare solleverebbe AttributeError.
    import db

    class FakeCur:
        def execute(self, sql, params=None):
            pass

    db.assicura_worker_log(FakeCur())  # non deve sollevare
