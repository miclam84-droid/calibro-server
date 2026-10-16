# ============================================================
# validazione_grafo.py — gate di FORMA per i record del grafo
# nodes/edges, da usare PRIMA di una scrittura su Postgres/SQLite.
#
# Funzioni PURE: nessun DB, nessuna rete, nessun I/O. Prendono il dict
# che rappresenta il record da scrivere e restituiscono (ok, problemi).
# NON sono imposte da nessuna parte: libreria ADDITIVA, pronta da cablare
# ai siti di scrittura (INSERT INTO nodes / INSERT INTO edges).
#
# ------------------------------------------------------------
# CONTRATTO DEDOTTO (da grafo/schema.sql + grafo/seed-*.sql, non inventato)
# ------------------------------------------------------------
#   nodes(id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL,
#         domain TEXT, data JSONB DEFAULT '{}')
#   edges(from_id TEXT NOT NULL, to_id TEXT NOT NULL, relation TEXT NOT NULL,
#         data JSONB DEFAULT '{}', PRIMARY KEY(from_id, to_id, relation))
#
# Regole (ciò che è davvero invariante nei dati reali):
#  - le colonne NOT NULL / PK sono OBBLIGATORIE e devono essere stringhe
#    non vuote: id/type/name (nodo), from_id/to_id/relation (arco);
#  - `domain` (nodo) è OPZIONALE (colonna nullable): se presente dev'essere
#    stringa. Vocabolario APERTO — nei seed compaiono bar, cucina, bakery,
#    trasversale, pasticceria, flower, plant, herb, fruit... — quindi NON si
#    valida contro un enum;
#  - `type` (nodo) e `relation` (arco) sono obbligatori ma a vocabolario
#    APERTO: nei dati reali type ∈ {Fenomeno, Processo, Calcolo, Prodotto,
#    Tecnica, Errore, Composto, Ingrediente...} e relation ∈ {si_manifesta_in,
#    influenza, fallisce_come, contiene_composto, controllato_con, spiega,
#    realizzato_da...}. Si valida che siano stringhe non vuote, NON il valore:
#    il drift dei VALORI è previsto, quello della FORMA no;
#  - `data` è la colonna JSONB: se presente DEVE essere un oggetto (dict).
#    Questo è il cuore del gate anti-drift del JSONB — liste, stringhe,
#    numeri o None-garbage al posto dell'oggetto vengono bocciati. La
#    validazione avviene sulla forma in-memory (dict) PRIMA di json.dumps;
#  - chiavi fuori dalle colonne reali vengono segnalate: non potrebbero
#    finire nel DB e indicano un chiamante confuso (altro sintomo di drift).
#
# I valori di ritorno sono sempre (ok: bool, problemi: list[str]): ok=True
# e lista vuota quando il record è ben formato; ok=False con uno o più
# messaggi chiari quando non lo è. Nessuna eccezione sollevata.
# ============================================================

# Colonne reali delle due tabelle (ordine = schema.sql).
CHIAVI_NODO = ("id", "type", "name", "domain", "data")
CHIAVI_NODO_OBBLIGATORIE = ("id", "type", "name")
CHIAVI_NODO_OPZIONALI_STRINGA = ("domain",)

CHIAVI_ARCO = ("from_id", "to_id", "relation", "data")
CHIAVI_ARCO_OBBLIGATORIE = ("from_id", "to_id", "relation")
CHIAVI_ARCO_OPZIONALI_STRINGA = ()


def _valida_record(record, obbligatorie, opzionali_stringa, chiavi_ammesse, tipo_record):
    """Nucleo condiviso: applica le regole di forma a un record dict.

    Puro, senza side-effect. Ritorna (ok, problemi).
    """
    if not isinstance(record, dict):
        return False, ["%s: atteso dict, trovato %s" % (tipo_record, type(record).__name__)]

    problemi = []

    # Colonne NOT NULL / PK: presenti, non None, stringa non vuota.
    for k in obbligatorie:
        if k not in record or record[k] is None:
            problemi.append("chiave obbligatoria mancante o nulla: '%s'" % k)
            continue
        valore = record[k]
        if not isinstance(valore, str):
            problemi.append(
                "campo '%s': atteso str, trovato %s" % (k, type(valore).__name__)
            )
        elif not valore.strip():
            problemi.append("campo '%s': stringa vuota non ammessa" % k)

    # Colonne stringa opzionali (es. domain): se presenti e non None -> str.
    for k in opzionali_stringa:
        if k in record and record[k] is not None and not isinstance(record[k], str):
            problemi.append(
                "campo '%s': atteso str, trovato %s" % (k, type(record[k]).__name__)
            )

    # Colonna JSONB `data`: se presente e non None -> oggetto (dict).
    if "data" in record and record["data"] is not None and not isinstance(record["data"], dict):
        problemi.append(
            "campo 'data' (JSONB): atteso oggetto/dict, trovato %s"
            % type(record["data"]).__name__
        )

    # Chiavi inattese: non mappano su nessuna colonna reale.
    for k in record:
        if k not in chiavi_ammesse:
            problemi.append(
                "chiave inattesa: '%s' (colonne ammesse: %s)"
                % (k, ", ".join(chiavi_ammesse))
            )

    return (len(problemi) == 0), problemi


def valida_nodo(data):
    """Valida la forma di un record `nodes` da scrivere.

    `data` è il dict del record (NON solo la colonna JSONB): chiavi attese
    id/type/name/domain/data. Vedi il contratto in testa al modulo.
    Ritorna (ok: bool, problemi: list[str]).
    """
    return _valida_record(
        data,
        CHIAVI_NODO_OBBLIGATORIE,
        CHIAVI_NODO_OPZIONALI_STRINGA,
        CHIAVI_NODO,
        "nodo",
    )


def valida_arco(data):
    """Valida la forma di un record `edges` da scrivere.

    `data` è il dict del record (NON solo la colonna JSONB): chiavi attese
    from_id/to_id/relation/data. Vedi il contratto in testa al modulo.
    Ritorna (ok: bool, problemi: list[str]).
    """
    return _valida_record(
        data,
        CHIAVI_ARCO_OBBLIGATORIE,
        CHIAVI_ARCO_OPZIONALI_STRINGA,
        CHIAVI_ARCO,
        "arco",
    )
