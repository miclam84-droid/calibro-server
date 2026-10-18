# -*- coding: utf-8 -*-
# ============================================================
# PAGINA FAMIGLIA BOTANICA — navigazione degli ingredienti per famiglia.
#
# Strangler-fig: pagina NUOVA e ISOLATA (come /scopri, /ingrediente, /laboratorio).
# Non tocca index.html / index2.html / /app / /app2 / scheda.html.
#
# La famiglia botanica e' scritta sui nodi da routes/tassonomia_wikidata.py, dentro
# data["tassonomia"]["famiglia"] (fonte Wikidata CC0). Qui la LEGGIAMO soltanto.
#
# Non esisteva un endpoint "elenca famiglie / ingredienti di una famiglia": lo
# costruiamo qui, SOLA LETTURA dal grafo, con un aggregatore PURO e testabile
# (_aggrega_famiglie, _ingredienti_di_famiglia) che lavora su nodi (nome, data) —
# niente DB ne' rete nei test.
#
# ONESTA' DEI DATI: gli ingredienti senza famiglia classificata NON ricevono una
# famiglia inventata: finiscono in un gruppo esplicito "Non classificato".
# ============================================================
import re
import json

from flask import Blueprint, render_template, make_response, jsonify

from db import connessione

bp_famiglia = Blueprint("pagina_famiglia", __name__)

# tipi di nodo che rappresentano un ingrediente/materia prima (stesso insieme su
# cui tassonomia_wikidata.py scrive la famiglia)
_TIPI_INGREDIENTE = ("Ingrediente", "Prodotto")

NON_CLASSIFICATO = "Non classificato"
SLUG_NON_CLASS = "non-classificato"


# ─────────────────────────────────────────────────────────────────────────────
# FUNZIONI PURE (testabili da nodi finti, senza DB ne' rete)
# ─────────────────────────────────────────────────────────────────────────────

def _estrai_famiglia(data):
    """Dal campo `data` di un nodo (dict o stringa JSON) -> nome della famiglia
    botanica, oppure None se non classificata. Onesto: se manca la tassonomia o
    la famiglia, ritorna None (= 'Non classificato'), non inventa nulla."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return None
    if not isinstance(data, dict):
        return None
    tax = data.get("tassonomia")
    if not isinstance(tax, dict):
        return None
    fam = tax.get("famiglia")
    if isinstance(fam, str) and fam.strip():
        return fam.strip()
    return None


def _slug(testo):
    """Slug stabile per URL: minuscolo, solo [a-z0-9-]. 'Solanaceae'->'solanaceae'."""
    return re.sub(r"[^a-z0-9]+", "-", (testo or "").lower()).strip("-")


def _bucket(fam):
    """(slug, display, classificata) del gruppo cui appartiene una famiglia (o None)."""
    if fam is None:
        return SLUG_NON_CLASS, NON_CLASSIFICATO, False
    return _slug(fam), fam, True


def _aggrega_famiglie(nodi):
    """nodi: iterabile di (nome, data). Ritorna la lista dei gruppi-famiglia con il
    conteggio di ingredienti, ciascuno {famiglia, slug, conteggio, classificata}.
    Ordine: le famiglie classificate prima (per conteggio desc, poi nome),
    'Non classificato' sempre in fondo."""
    conte = {}
    for nome, data in nodi:
        slug, disp, classif = _bucket(_estrai_famiglia(data))
        g = conte.get(slug)
        if g is None:
            conte[slug] = {"famiglia": disp, "slug": slug,
                           "conteggio": 1, "classificata": classif}
        else:
            g["conteggio"] += 1
    out = list(conte.values())
    out.sort(key=lambda r: (0 if r["classificata"] else 1,
                            -r["conteggio"], r["famiglia"].lower()))
    return out


def _ingredienti_di_famiglia(nodi, richiesta):
    """nodi: iterabile di (nome, data). Ritorna (display_famiglia, lista_nomi) degli
    ingredienti il cui gruppo-famiglia combacia (per slug) con `richiesta`. Se
    `richiesta` e' il gruppo 'non classificato', ritorna gli ingredienti SENZA
    famiglia. Nomi deduplicati e ordinati alfabeticamente."""
    sric = _slug(richiesta)
    display = NON_CLASSIFICATO if sric == SLUG_NON_CLASS else richiesta
    nomi = []
    for nome, data in nodi:
        fam = _estrai_famiglia(data)
        slug, disp, _ = _bucket(fam)
        if slug == sric:
            nomi.append(nome)
            if fam is not None:
                display = disp  # nome famiglia nella grafia reale del grafo
    nomi = sorted(set(n for n in nomi if n), key=lambda s: s.lower())
    return display, nomi


# ─────────────────────────────────────────────────────────────────────────────
# LETTURA GRAFO (sola lettura, dal pool condiviso)
# ─────────────────────────────────────────────────────────────────────────────

def _leggi_nodi_ingrediente():
    """Tutti i nodi ingrediente/prodotto come lista di (nome, data). Sola lettura."""
    from routes.criteri import DATABASE_URL
    if not DATABASE_URL:
        return None
    ph = ",".join(["%s"] * len(_TIPI_INGREDIENTE))
    with connessione() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, data FROM nodes WHERE type IN (%s)" % ph,
            _TIPI_INGREDIENTE,
        )
        righe = cur.fetchall()
        cur.close()
    return [(r[0], r[1]) for r in righe]


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@bp_famiglia.route("/v1/famiglie", methods=["GET"])
def v1_famiglie():
    """Elenco delle famiglie botaniche con il conteggio di ingredienti. SOLA LETTURA.
    Include il gruppo esplicito 'Non classificato' per gli ingredienti senza famiglia."""
    nodi = _leggi_nodi_ingrediente()
    if nodi is None:
        return jsonify({"nota": "DB non disponibile", "famiglie": []})
    famiglie = _aggrega_famiglie(nodi)
    classificate = [f for f in famiglie if f["classificata"]]
    non_class = next((f["conteggio"] for f in famiglie if not f["classificata"]), 0)
    return jsonify({
        "famiglie": famiglie,
        "totale_famiglie": len(classificate),
        "totale_ingredienti": sum(f["conteggio"] for f in famiglie),
        "non_classificati": non_class,
        "nota": ("La famiglia botanica viene da Wikidata (CC0). Gli ingredienti "
                 "senza famiglia classificata sono raccolti in 'Non classificato': "
                 "non ne inventiamo una."),
    })


@bp_famiglia.route("/v1/famiglia/<path:nome>", methods=["GET"])
def v1_famiglia(nome):
    """Gli ingredienti di una famiglia botanica (per slug o nome). SOLA LETTURA.
    `nome` = 'non-classificato' restituisce gli ingredienti senza famiglia."""
    nodi = _leggi_nodi_ingrediente()
    if nodi is None:
        return jsonify({"nota": "DB non disponibile", "ingredienti": []})
    display, ingredienti = _ingredienti_di_famiglia(nodi, nome)
    classificata = _slug(nome) != SLUG_NON_CLASS
    return jsonify({
        "famiglia": display,
        "slug": _slug(nome),
        "classificata": classificata,
        "conteggio": len(ingredienti),
        "ingredienti": ingredienti,
        "nota": ("" if classificata else
                 "Ingredienti ancora senza famiglia botanica classificata: "
                 "non ne inventiamo una."),
    })


@bp_famiglia.route("/famiglie", methods=["GET"])
def pagina_famiglie():
    """FRONTEND-2.0 — schermata 'Per famiglia botanica': elenco famiglie con
    conteggio -> ingredienti di quella famiglia -> scheda ingrediente. Sistema di
    design congelato (matter2.css), cablata dal vivo a /v1/famiglie e
    /v1/famiglia/<slug>. Pagina nuova e isolata: non tocca /app ne' /app2."""
    resp = make_response(render_template("famiglie.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
