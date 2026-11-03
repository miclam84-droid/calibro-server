# ============================================================
# SCIENZA-CLASSI-FIX — corregge la categoria (disciplina) di poche schede-scienza
# classificate in modo chiaramente sbagliato (es. Backflushing sotto panificazione,
# Brettanomyces sotto panificazione).
#
# PERCHE' (revisore): "la classificazione sbagliata danneggia la credibilità
# scientifica più di una grafica imperfetta. Correggere SOLO gli errori certi,
# lasciare non classificati gli incerti, non forzare." Qui stanno SOLO i certi.
#
# La categoria vive in node.data.categoria (letta da /v1/schede-scienza).
# ONESTA': lista hand-checked, nessun incerto (fermentazione alcolica = davvero
# trasversale -> lasciata stare; le creme/pasticceria erano falsi positivi).
# fill-safe: scrive solo se la categoria attuale è diversa. Backup + dry-run.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_classi_fix = Blueprint("scienza_classi_fix", __name__)

# node_id (= slug) -> categoria CORRETTA. Solo errori certi, verificati a mano.
_FIX = {
    # vino / enologia (erano sotto panificazione o bar)
    "fen-solforosa":               "vino",   # Anidride solforosa (SO2) — conservante enologico
    "fen-brett":                   "vino",   # Brettanomyces — difetto fenolico del vino
    "fen-malolattica":             "vino",   # Fermentazione malolattica — enologia
    # birra
    "fen-luppolo":                 "birra",  # Il luppolo e l'amaro della birra
    "fen-lagering":                "birra",  # Lagering — maturazione a freddo della birra
    "fen-acqua-birra":             "birra",  # Profilo dell'acqua in birrificazione
    # caffè (erano sotto panificazione / bar / pasticceria)
    "tec-backflushing":            "caffe",  # pulizia gruppi macchina espresso
    "tec-basket-preparation":      "caffe",  # preparazione del filtro espresso
    "tec-calibrazione-macinatura": "caffe",  # calibrazione macinacaffè
    "fen-cold-brew":               "caffe",  # estrazione a freddo del caffè
    "tec-purging-macinacaffe":     "caffe",  # purging del macinacaffè
    "fen-tostatura-caffe":         "caffe",  # tostatura del caffè
}
_CAT_VALIDE = {"vino", "birra", "caffe", "panificazione", "pasticceria",
               "cucina", "bar", "gelateria", "trasversale"}


def _pianifica(nodi_db, fix):
    """PURA: (da_scrivere, campione, non_trovati). Scrive solo se la categoria cambia."""
    da_scrivere, campione, non_trovati = [], [], []
    for nid, cat_nuova in fix.items():
        if cat_nuova not in _CAT_VALIDE:
            continue  # guardia
        if nid not in nodi_db:
            non_trovati.append(nid)
            continue
        nome, dd = nodi_db[nid]
        if not isinstance(dd, dict):
            dd = {}
        cat_vecchia = dd.get("categoria") or dd.get("disciplina") or dd.get("dominio") or "(vuoto)"
        cambia = (cat_vecchia != cat_nuova)
        campione.append({"nodo": nid, "nome": nome, "da": cat_vecchia, "a": cat_nuova, "cambia": cambia})
        if not cambia:
            continue
        nuovo = dict(dd)
        nuovo["categoria"] = cat_nuova
        da_scrivere.append((nid, nuovo))
    return da_scrivere, campione, non_trovati


@bp_classi_fix.route("/admin/scienza-classi-fix")
def scienza_classi_fix():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (backup, transazione).
    Corregge la categoria delle schede-scienza chiaramente mis-classificate."""
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
        ids = list(_FIX.keys())
        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (ids,))
        nodi_db = {}
        for rid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi_db[rid] = (nome, dd)

        da_scrivere, campione, non_trovati = _pianifica(nodi_db, _FIX)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_scienza_classi
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, nuovo in da_scrivere:
                _nome, dd_old = nodi_db[nid]
                cur.execute("INSERT INTO _backup_scienza_classi (id, data_old) VALUES (%s, %s)",
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
            "nodi_in_lista": len(_FIX),
            "nodi_trovati_db": len(nodi_db),
            "da_scrivere": len(da_scrivere),
            "scritti": scritti,
            "non_trovati_nel_db": non_trovati,
            "nota": ("Solo errori di classificazione certi (vino/birra/caffè finiti sotto "
                     "panificazione/bar/pasticceria). Gli incerti NON si toccano. Backup in "
                     "_backup_scienza_classi. &esegui=1 per scrivere."),
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
