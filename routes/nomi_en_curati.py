# ============================================================
# NOMI-EN-CURATI — assegna il nome inglese (data.nomi.en) ai nodi cibo che
# NON ce l'hanno da nessuna parte (ne' in data.nomi.en, ne' nella tabella
# ingredienti_nomi), SBLOCCANDO il search USDA a derivarne il gusto reale.
#
# PERCHE': /admin/deriva-gusti-search profila un nodo SOLO se conosce il suo
# nome EN. Il travaso (ingredienti_nomi) per questi nodi non trova nulla (la
# tabella e' quasi vuota di EN: 3309/3316 senza corrispondenza). Restano cibi
# veri che USDA HA (strutto, succo di pompelmo, fecola, miso, kombu...): basta
# dar loro il nome inglese giusto e il search li deriva con dati veri.
#
# ONESTA' DEI DATI (vincoli duri):
#   - NON e' invenzione di gusto: scriviamo solo la TRADUZIONE del nome. Il
#     valore di gusto lo deriva il search dai nutrienti USDA, col suo cancello
#     di confidenza 0.6 (un nome che non trova buon match NON scrive nulla).
#   - nomi EN ACCURATI: solo dove USDA ha davvero il cibo. Gli specialty che
#     USDA non ha (o che darebbero match fuorviante) restano fuori: niente
#     nome a caso pur di riempire.
#   - fill-only: scrive data.nomi.en SOLO sui nodi che non ce l'hanno.
#   - backup in _backup_nomi_en_curati + transazione. DRY-RUN di default;
#     scrive con &esegui=1. Match per ID nodo (esatto).
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_nomi_en_curati = Blueprint("nomi_en_curati", __name__)

# ID nodo -> nome EN accurato (stile USDA FoodData Central, minuscolo).
# Solo cibi che USDA copre: il search li derivera' con dati veri (gate 0.6).
_NOMI_EN = {
    # — alta confidenza: USDA li ha quasi certamente —
    "prod-kimchi":                   "kimchi",
    "ai_gochujang":                  "gochujang",
    "ing-farina-0":                  "wheat flour white all-purpose",
    "ing-chaas-buttermilk":          "buttermilk",
    "fis_grapefruit_juice":          "grapefruit juice",
    "ing-mortadella":                "mortadella",
    "ing-fecola-di-patate":          "potato starch",
    "ai_lenticchie_rosse":           "red lentils",
    "ai_alga_kombu":                 "kelp seaweed",
    "ing-kombu-saccharina-japonica": "kelp seaweed",
    "ing-zenzero-in-polvere":        "ground ginger",
    "prod-maionese":                 "mayonnaise",
    "ing-granella-di-pistacchio":    "pistachio nuts",
    "ing-latte-magro-polvere":       "nonfat dry milk",
    "ing-noci-tritate":              "walnuts",
    "ai_miso_bianco":                "miso",
    "ing-cannella-in-stecca":        "ground cinnamon",
    "ing-cannella-di-ceylon":        "ground cinnamon",
    "ing-ricotta-salata":            "ricotta cheese",
    "ing-paneer":                    "paneer",
    "ahn_anise":                     "anise seed",
    "ing-fagioli-borlotti":          "cranberry beans",
    "ing-bacca-di-vaniglia":         "vanilla",
    # — media confidenza: nome corretto per classe, il gate 0.6 fa da filtro —
    "ing-habanero":                  "hot chili pepper",
    "ing-rocoto":                    "hot chili pepper",
    "ing-achiote-annatto":           "annatto",
    "ai_pepe_rosa":                  "pink peppercorn",
    "ai_mirin":                      "mirin",
    "ing-arancia-candita":           "candied orange peel",
    "ing-cedro-candito":             "candied citron",
    "ing-ricci-di-mare":             "sea urchin",
    # NB: lasciati FUORI di proposito (USDA non li ha / match fuorviante):
    #   ing-it-bottarga (bottarga), e i senza-gusto-base (acqua frizzante, soda,
    #   lievito ale US-05, acqua di fiori d'arancio) che gusto base non hanno.
}


def _ha_en(dd):
    """True se il nodo ha gia' un data.nomi.en non vuoto (fill-only lo salta)."""
    nomi = dd.get("nomi") if isinstance(dd, dict) and isinstance(dd.get("nomi"), dict) else {}
    return bool((nomi.get("en") or "").strip())


def _pianifica(nodi_db, nomi_en):
    """PURA (niente DB/rete, testabile): decide cosa scrivere.
      nodi_db = {id: (nome_it, dd_dict)}
      nomi_en = {id: nome_en}
    Ritorna (da_scrivere, campione, non_trovati). Fill-only: salta chi ha gia' EN."""
    da_scrivere, campione, non_trovati = [], [], []
    for nid, en in nomi_en.items():
        if nid not in nodi_db:
            non_trovati.append(nid)
            continue
        nome_it, dd = nodi_db[nid]
        if not isinstance(dd, dict):
            dd = {}
        gia = _ha_en(dd)
        campione.append({"nodo": nid, "nome_it": nome_it, "nome_en": en,
                         "scrivibile": (not gia),
                         "en_esistente": (dd.get("nomi", {}) or {}).get("en") if gia else None})
        if gia:
            continue
        nuovo = dict(dd)
        nomi = dict(nuovo.get("nomi")) if isinstance(nuovo.get("nomi"), dict) else {}
        nomi["en"] = en
        nuovo["nomi"] = nomi
        da_scrivere.append((nid, nuovo))
    return da_scrivere, campione, non_trovati


@bp_nomi_en_curati.route("/admin/nomi-en-curati")
def nomi_en_curati():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (fill-only, backup,
    transazione). Assegna data.nomi.en curato ai cibi senza nome EN, sbloccando
    il search USDA. Dopo: girare deriva-gusti-search per derivarne il gusto."""
    import hmac as _hmac
    import psycopg2

    if not _hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()

        ids = list(_NOMI_EN.keys())
        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (ids,))
        nodi_db = {}
        for rid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi_db[rid] = (nome, dd)

        da_scrivere, campione, non_trovati = _pianifica(nodi_db, _NOMI_EN)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_nomi_en_curati
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, nuovo in da_scrivere:
                _nome, dd_old = nodi_db[nid]
                cur.execute("INSERT INTO _backup_nomi_en_curati (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd_old, ensure_ascii=False)))
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(nuovo, ensure_ascii=False), nid))
                scritti += 1
            conn.commit()
        else:
            conn.rollback()

        cur.close()
        conn.close()
        return jsonify({
            "modo": "ESEGUITO (scritto)" if esegui else "DRY-RUN (nessuna scrittura)",
            "nodi_in_tabella": len(_NOMI_EN),
            "nodi_trovati_db": len(nodi_db),
            "da_scrivere": len(da_scrivere),
            "scritti": scritti,
            "non_trovati_nel_db": non_trovati,
            "nota": ("Scrive SOLO il nome EN (traduzione), non il gusto. Dopo &esegui=1, "
                     "gira /admin/deriva-gusti-search (o il runner) per derivare il gusto "
                     "da USDA con cancello 0.6. Fill-only, backup in _backup_nomi_en_curati."),
            "campione": campione,
        })
    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({"errore": str(e)[:200]}), 500
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
