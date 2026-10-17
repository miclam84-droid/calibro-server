# ============================================================
# NUTRIZIONALE — valori nutrizionali + allergeni per ingrediente.
# ONESTÀ: mostra SOLO ciò che è realmente sul nodo. Il grafo NON contiene
# un pannello nutrizionale USDA grezzo completo: gli UNICI numeri misurati
# persistiti sul nodo sono i `grezzo` dentro proprieta_meta, scritti dalle
# pipeline di derivazione del gusto (USDA / CIQUAL / glutammato), e SOLO per
# gli assi derivati. Ognuno porta la sua `fonte`. Niente numeri senza fonte.
# Gli allergeni NON sono memorizzati sul nodo: si deducono in modo
# DETERMINISTICO dal nome (Reg. UE 1169/2011), riusando routes/allergeni.py.
# Dove un dato non c'è: "—" / null, mai inventato. Sola lettura.
# ============================================================
import os
import json

from flask import Blueprint, jsonify, render_template

bp_nutri = Blueprint("nutrizionale", __name__)

# Mappa asse-gusto -> campo nutrizionale misurato + unità.
# Il `grezzo` di questi assi è l'unica misura compositiva reale persistita
# sul nodo (vedi routes/deriva_gusti.py, deriva_gusti_ciqual.py, deriva_umami.py).
CAMPI_NUTRI = [
    ("dolce",  "Zuccheri",          "g/100g"),
    ("salato", "Sodio",             "mg/100g"),
    ("grasso", "Grassi",            "g/100g"),
    ("acido",  "Acidi organici",    "g/100g"),
    ("umami",  "Glutammato libero", "mg/100g"),
]


def estrai_valori(data):
    """Funzione PURA (nessun DB): dal `data` JSONB del nodo estrae i valori
    nutrizionali realmente presenti. Ogni voce esce SEMPRE (così il pannello
    dichiara anche ciò che manca con "—"), ma `valore`/`unita`/`fonte` sono
    valorizzati SOLO se c'è un grezzo misurato con una fonte citata.
    Un numero senza fonte NON viene mai esposto: diventa null."""
    dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
    meta = dd.get("proprieta_meta", {}) or {}
    valori = []
    for asse, campo, unita in CAMPI_NUTRI:
        m = (meta.get(asse) or {}) if isinstance(meta.get(asse), dict) else {}
        grezzo = m.get("grezzo")
        fonte = m.get("fonte")
        # presente solo se abbiamo SIA un numero misurato SIA la sua provenienza
        presente = (grezzo is not None) and bool(fonte)
        valori.append({
            "campo": campo,
            "asse": asse,
            "valore": grezzo if presente else None,
            "unita": unita if presente else None,
            "fonte": fonte if presente else None,
            "stato": m.get("stato") if presente else None,
        })
    return valori


def _deduci_allergeni_da_nome(nome):
    """Allergeni dedotti dal NOME dell'ingrediente (non memorizzati sul nodo).
    Deterministico, Reg. UE 1169/2011. Riusa la logica legale di routes/allergeni.py."""
    try:
        from routes.allergeni import deduci_allergeni, ALLERGENI_UE
    except Exception:
        return []
    ids, _warning = deduci_allergeni([nome], nome_piatto="")
    _map = {a["id"]: a for a in ALLERGENI_UE}
    return [{"id": i, "nome": _map[i]["it"], "icona": _map[i]["icona"]}
            for i in ids if i in _map]


_NOTA = ("Pannello onesto: i valori nutrizionali mostrati sono gli UNICI "
         "realmente misurati e persistiti sul nodo (il `grezzo` compositivo "
         "degli assi derivati, con la sua fonte). Il grafo non contiene un "
         "pannello USDA completo (energia, proteine, carboidrati, fibre): dove "
         "non c'è un dato si legge “—”, non si inventa uno zero. Gli "
         "allergeni sono dedotti in modo deterministico dal nome "
         "(Reg. UE 1169/2011), non sono un campo del nodo: il professionista "
         "verifica e conferma.")


def costruisci_scheda(nome_reale, data):
    """Compone il payload completo da nome + data del nodo. Pura, testabile."""
    valori = estrai_valori(data)
    allergeni = _deduci_allergeni_da_nome(nome_reale)
    return {
        "trovato": True,
        "nome": nome_reale,
        "valori": valori,
        "allergeni": allergeni,
        "note_onesta": _NOTA,
    }


def _cerca_nodo(nome):
    """Legge il nodo da Postgres (sola lettura). Ritorna (nome_reale, data) o None."""
    import psycopg2
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return None, "no db"
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        cur = conn.cursor()
        cur.execute("""SELECT name, data FROM nodes
                       WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name) LIKE LOWER(%s)
                       ORDER BY LENGTH(name) LIMIT 1""", (f"%{nome}%",))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return None, None
        return (row[0], row[1]), None
    except Exception as e:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        return None, str(e)[:150]


@bp_nutri.route("/v1/nutrizionale/<path:nome>", methods=["GET"])
def nutrizionale_json(nome):
    """JSON: {nome, valori:[{campo, valore, unita, fonte}], allergeni:[...], note_onesta}.
    Ogni valore porta la sua fonte da proprieta_meta. Niente numeri senza fonte."""
    esito, errore = _cerca_nodo(nome)
    if errore == "no db":
        return jsonify({"errore": "no db"}), 400
    if errore:
        return jsonify({"errore": errore}), 500
    if esito is None:
        return jsonify({"trovato": False, "nome_cercato": nome,
                        "valori": [], "allergeni": [], "note_onesta": _NOTA})
    nome_reale, data = esito
    return jsonify(costruisci_scheda(nome_reale, data))


@bp_nutri.route("/nutrizione/", defaults={"nome": ""})
@bp_nutri.route("/nutrizione/<path:nome>")
def nutrizione_page(nome):
    """Pagina isolata (riusa matter2.css) che rende il JSON in modo leggibile."""
    return render_template("nutrizione.html", nome=nome)
