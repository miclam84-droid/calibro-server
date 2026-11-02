# ============================================================
# DERIVA-GUSTI-MIRATO — rilancia il motore del search USDA SOLO su una lista
# esplicita di nodi, invece di scorrere tutti i ~3850 per offset.
#
# PERCHE': il runner a offset aveva gia' superato questi nodi PRIMA che gli
# dessimo il nome EN (nomi-en-curati), quindi li aveva saltati come "senza EN".
# Rifare 3850 per ripescarne 29 e' spreco. Qui si punta il motore esistente
# (_sweep_nodi -> _elabora_nodo) esattamente su quei 29 id: stesso cancello di
# confidenza 0.6, stesso fill-only, stesso backup (_backup_gusti_derivati).
#
# ONESTA': nessuna logica nuova di derivazione. Riusa _sweep_nodi cosi' com'e'.
# I 5 senza-gusto-base (acqua frizzante, soda, lievito US-05, acqua di fiori
# d'arancio, bottarga) sono ESCLUSI di proposito: gusto base non ne hanno o
# USDA non li copre. DRY-RUN di default; scrive con &esegui=1.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

from routes.deriva_gusti_search import _sweep_nodi

bp_gusti_mirato = Blueprint("deriva_gusti_mirato", __name__)

# I 29 cibi veri che USDA copre, da ri-processare col nome EN ora presente.
_IDS = [
    "prod-kimchi", "ing-rocoto", "ing-achiote-annatto", "ai_gochujang",
    "ing-farina-0", "ing-chaas-buttermilk", "ing-mortadella", "ing-ricci-di-mare",
    "ing-fecola-di-patate", "ai_lenticchie_rosse", "ai_alga_kombu",
    "ing-zenzero-in-polvere", "prod-maionese", "ing-granella-di-pistacchio",
    "ing-latte-magro-polvere", "ing-noci-tritate", "ai_miso_bianco",
    "ing-arancia-candita", "ing-cannella-in-stecca", "ing-ricotta-salata",
    "ing-cannella-di-ceylon", "ai_mirin", "ing-cedro-candito",
    "ing-bacca-di-vaniglia", "ing-paneer", "ing-habanero",
    "ing-kombu-saccharina-japonica", "ahn_anise", "ing-fagioli-borlotti",
]


@bp_gusti_mirato.route("/admin/deriva-gusti-mirato")
def deriva_gusti_mirato():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive. &soglia=N per il
    cancello (default 0.6). Rilancia il motore del search SOLO sui 29 cibi veri
    appena sbloccati col nome EN. Stesso fill-only/backup del search normale."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    key = os.environ.get("USDA_API_KEY", "")
    if not key:
        return jsonify({"errore": "USDA_API_KEY non impostata su Railway"}), 400
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    try:
        soglia = float(request.args.get("soglia", "0.6"))
    except Exception:
        soglia = 0.6

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_gusti_derivati
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (_IDS,))
        righe = cur.fetchall()
        trovati = {r[0] for r in righe}
        non_trovati = [i for i in _IDS if i not in trovati]

        # limite alto: vogliamo processarli TUTTI in un colpo (sono solo 29)
        cont, proposte_alta, proposte_bassa, errori = _sweep_nodi(
            righe, key, soglia, 60, cur, esegui)

        if esegui:
            conn.commit()
        else:
            conn.rollback()
        cur.close()
        conn.close()
        return jsonify({
            "modo": "ESEGUITO (scritto)" if esegui else "DRY-RUN (nessuna scrittura)",
            "soglia": soglia,
            "nodi_bersaglio": len(_IDS),
            "nodi_trovati_db": len(righe),
            "non_trovati_nel_db": non_trovati,
            "ricerche_usda": cont["ricerche"],
            "scritti_alta": cont["scritti"],
            "saltati_senza_en": cont["senza_en"],
            "gia_derivati": cont["gia_derivati"],
            "non_sensoriali": cont["non_sensoriali"],
            "saltati_errore": cont["saltati_errore"],
            "alta_confidenza": proposte_alta,
            "bassa_confidenza_NON_scritti": proposte_bassa,
            "errori": errori,
            "nota": ("Motore del search puntato sui 29 cibi veri. 'alta_confidenza' = "
                     "scritti (con &esegui=1); 'bassa' = match deboli NON scritti (da "
                     "controllare a occhio). Fill-only, backup _backup_gusti_derivati."),
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
