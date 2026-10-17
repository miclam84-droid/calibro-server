# ============================================================
# routes/cottura.py — dimensione "cottura per ingrediente".
#
# COSA FA: dato un ingrediente, restituisce le tecniche di cottura/lavorazione
# RILEVANTI pescate SOLO da ciò che il grafo già collega:
#   1) le tecniche collegate ai FENOMENI che si manifestano in quell'ingrediente
#      (fenomeno --si_manifesta_in--> ingrediente  e  fenomeno --realizzato_da--> tecnica);
#   2) le tecniche della stessa DISCIPLINA dell'ingrediente (Tecnica.domain == Ingrediente.domain).
#
# ONESTÀ DEI DATI (regola ferrea del progetto):
#   NON inventiamo "qual è la cottura ideale" di un ingrediente. Quella è conoscenza
#   che va da fonte vera / prova al banco e si riempirà DOPO. Qui costruiamo solo il
#   contenitore e ci mettiamo dentro ciò che il grafo GIÀ collega, con etichette oneste.
#   Il campo curato `cottura_consigliata` è PREDISPOSTO (fill-only): l'endpoint lo espone
#   se c'è, altrimenti dichiara stato "vuoto". Questo file NON scrive mai sul DB.
#
# Dipende da: db (carica_grafo, _dati). Le parti di selezione/formattazione sono
# funzioni PURE (niente DB), testate in tests/test_cottura.py.
# ============================================================
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati

bp_cottura = Blueprint("cottura", __name__)

# Stato del campo curato quando non è ancora stato riempito da fonte vera / banco.
STATO_CURATO_VUOTO = "vuoto"
STATO_CURATO_PRESENTE = "curato"

# Etichetta onesta sul significato di ciò che restituiamo.
ETICHETTA_ONESTA = (
    "Tecniche della disciplina o collegate nel grafo, "
    "NON la cottura ideale provata al banco."
)


# ------------------------------------------------------------
# FUNZIONI PURE (selezione / formattazione) — niente DB, testabili da sole.
# Ricevono liste di dict «grezzi» già estratti dal grafo e restituiscono
# la struttura d'uscita. La separazione tiene la query SQL fuori dai test.
# ------------------------------------------------------------

def _pulisci_nome(s):
    """Toglie markdown residuo dai nomi del grafo (come in routes/lezione.py)."""
    if not s:
        return ""
    import re as _re
    s = _re.sub(r'[#*_`]+', '', str(s))
    s = _re.sub(r'\s+', ' ', s).strip()
    return s


def seleziona_tecniche_collegate(righe_fenomeno_tecnica):
    """PURA. Dalle coppie (fenomeno, tecnica) collegate nel grafo costruisce la lista
    delle tecniche DISTINTE, tenendo traccia di QUALI fenomeni le portano.

    Input: lista di dict con chiavi:
        tecnica_id, tecnica_nome, tecnica_dominio (opz.), nota (opz.),
        fenomeno_id (opz.), fenomeno_nome (opz.)
    Output: lista di dict ordinata per nome:
        {id, nome, dominio, nota, via_fenomeni: [nomi fenomeno distinti]}
    """
    per_id = {}
    for r in righe_fenomeno_tecnica:
        tid = r.get("tecnica_id")
        if not tid:
            continue
        voce = per_id.get(tid)
        if voce is None:
            voce = {
                "id": tid,
                "nome": _pulisci_nome(r.get("tecnica_nome")),
                "dominio": (r.get("tecnica_dominio") or "") or "",
                "nota": _pulisci_nome(r.get("nota")) if r.get("nota") else "",
                "via_fenomeni": [],
            }
            per_id[tid] = voce
        fen_nome = _pulisci_nome(r.get("fenomeno_nome"))
        if fen_nome and fen_nome not in voce["via_fenomeni"]:
            voce["via_fenomeni"].append(fen_nome)
        # se la nota arriva solo da una delle coppie, non perderla
        if not voce["nota"] and r.get("nota"):
            voce["nota"] = _pulisci_nome(r.get("nota"))
    for v in per_id.values():
        v["via_fenomeni"].sort()
    return sorted(per_id.values(), key=lambda v: v["nome"].lower())


def seleziona_tecniche_disciplina(righe_tecnica, escludi_ids=None):
    """PURA. Tecniche della disciplina (stesso dominio dell'ingrediente), ESCLUSE
    quelle già presenti tra le collegate (per non ripeterle).

    Input: lista di dict {id, nome, dominio}. escludi_ids: set/list di id da saltare.
    Output: lista di dict {id, nome, dominio} ordinata per nome.
    """
    escl = set(escludi_ids or [])
    per_id = {}
    for r in righe_tecnica:
        tid = r.get("id")
        if not tid or tid in escl or tid in per_id:
            continue
        per_id[tid] = {
            "id": tid,
            "nome": _pulisci_nome(r.get("nome")),
            "dominio": (r.get("dominio") or "") or "",
        }
    return sorted(per_id.values(), key=lambda v: v["nome"].lower())


def estrai_cottura_consigliata(data):
    """PURA. Legge il campo curato `cottura_consigliata` dal data del nodo, se c'è.
    È FILL-ONLY: qui non si scrive nulla, si espone solo.

    - se presente e non vuoto -> stato "curato", con valore + meta {stato, fonte}
    - se assente / vuoto       -> stato "vuoto": il contenitore è pronto a essere
                                   riempito in futuro DA FONTE VERA / prova al banco.
    Output sempre con la stessa forma: {stato, fonte, valore, nota}.
    """
    d = data if isinstance(data, dict) else {}
    valore = d.get("cottura_consigliata")
    meta = d.get("cottura_consigliata_meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    presente = valore not in (None, "", [], {})
    if presente:
        return {
            "stato": meta.get("stato") or STATO_CURATO_PRESENTE,
            "fonte": meta.get("fonte") or "",
            "valore": valore,
            "nota": "",
        }
    return {
        "stato": STATO_CURATO_VUOTO,
        "fonte": meta.get("fonte") or "",
        "valore": None,
        "nota": ("campo predisposto (fill-only), da riempire con fonte vera "
                 "o prova al banco — oggi vuoto"),
    }


def costruisci_risposta(ingrediente, disciplina, tecniche_collegate,
                        tecniche_disciplina, cottura_consigliata):
    """PURA. Assembla la risposta finale con le etichette ONESTE."""
    disc = disciplina or ""
    et_disc = (
        f"tecniche della disciplina «{disc}» collegate nel grafo"
        if disc else "tecniche della disciplina collegate nel grafo"
    )
    return {
        "ingrediente": ingrediente,
        "disciplina": disc,
        "cottura_consigliata": cottura_consigliata,
        "tecniche_collegate": {
            "etichetta": "tecniche collegate nel grafo (via i fenomeni di questo ingrediente)",
            "conteggio": len(tecniche_collegate),
            "voci": tecniche_collegate,
        },
        "tecniche_disciplina": {
            "etichetta": et_disc,
            "conteggio": len(tecniche_disciplina),
            "voci": tecniche_disciplina,
        },
        "onesta": ETICHETTA_ONESTA,
    }


# ------------------------------------------------------------
# ROUTE — qui vive la sola parte col DB (smoke su prod, non in unit test).
# ------------------------------------------------------------

def _trova_ingrediente(db, chiave):
    """Risolve l'ingrediente da id (ing-...) o nome, come fanno le altre route.
    Cerca tra Ingrediente/Prodotto. Ritorna la riga o None."""
    k = (chiave or "").strip()
    if not k:
        return None
    # match esatto per id o nome (case-insensitive)
    row = db.execute(
        """SELECT id, name, domain, data FROM nodes
           WHERE type IN ('Ingrediente','Prodotto')
             AND (lower(id)=lower(?) OR lower(name)=lower(?))
           LIMIT 1""",
        (k, k),
    ).fetchone()
    if row:
        return row
    # fallback: match parziale sul nome
    return db.execute(
        """SELECT id, name, domain, data FROM nodes
           WHERE type IN ('Ingrediente','Prodotto')
             AND lower(name) LIKE lower(?)
           ORDER BY length(name) LIMIT 1""",
        (f"%{k}%",),
    ).fetchone()


@bp_cottura.route("/v1/cottura/<ingrediente>")
def cottura_ingrediente(ingrediente):
    """GET /v1/cottura/<ingrediente> — tecniche di cottura/lavorazione rilevanti,
    pescate SOLO dal grafo esistente. Vedi l'intestazione del file per l'onestà dati."""
    db = carica_grafo()
    nodo = _trova_ingrediente(db, ingrediente)
    if not nodo:
        return jsonify({"errore": "ingrediente non trovato nel grafo",
                        "cercato": ingrediente}), 404

    nid = nodo["id"]
    disciplina = nodo["domain"] or ""
    data = _dati(nodo["data"])

    # 1) fenomeni che si manifestano in questo ingrediente, con le tecniche che li realizzano.
    #    fenomeno --si_manifesta_in--> ingrediente   e   fenomeno --realizzato_da--> tecnica
    righe_ft = []
    try:
        for fr in db.execute(
            """SELECT n.id AS fid, n.name AS fname FROM edges e
               JOIN nodes n ON n.id=e.from_id
               WHERE e.to_id=? AND e.relation='si_manifesta_in' AND n.type='Fenomeno'""",
            (nid,),
        ).fetchall():
            for tr in db.execute(
                """SELECT n2.id AS tid, n2.name AS tname, n2.domain AS tdom, e2.data AS edata
                   FROM edges e2 JOIN nodes n2 ON n2.id=e2.to_id
                   WHERE e2.from_id=? AND e2.relation='realizzato_da' AND n2.type='Tecnica'""",
                (fr["fid"],),
            ).fetchall():
                ed = _dati(tr["edata"]) if tr["edata"] else {}
                righe_ft.append({
                    "tecnica_id": tr["tid"],
                    "tecnica_nome": tr["tname"],
                    "tecnica_dominio": tr["tdom"],
                    "nota": ed.get("nota", ""),
                    "fenomeno_id": fr["fid"],
                    "fenomeno_nome": fr["fname"],
                })
    except Exception:
        righe_ft = []

    tecniche_collegate = seleziona_tecniche_collegate(righe_ft)
    gia_viste = {t["id"] for t in tecniche_collegate}

    # 2) tecniche della stessa disciplina dell'ingrediente.
    righe_disc = []
    if disciplina:
        try:
            for r in db.execute(
                """SELECT id, name, domain FROM nodes
                   WHERE type='Tecnica' AND lower(domain)=lower(?)""",
                (disciplina,),
            ).fetchall():
                righe_disc.append({"id": r["id"], "nome": r["name"], "dominio": r["domain"]})
        except Exception:
            righe_disc = []
    tecniche_disciplina = seleziona_tecniche_disciplina(righe_disc, escludi_ids=gia_viste)

    # 3) campo curato (fill-only): esposto se c'è, altrimenti stato "vuoto".
    cottura_consigliata = estrai_cottura_consigliata(data)

    ingr_out = {"id": nid, "nome": nodo["name"], "disciplina": disciplina}
    return jsonify(costruisci_risposta(
        ingr_out, disciplina, tecniche_collegate, tecniche_disciplina, cottura_consigliata
    ))
