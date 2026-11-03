# ============================================================
# GUSTI-PULISCI — riporta a VUOTO il profilo dolce/salato/grasso su una lista
# PICCOLA e verificata a mano di nodi che la deriva mirata ha scritto con un
# match USDA sbagliato (nome generico -> cibo sbagliato ad alto punteggio).
#
# PERCHE': "meglio vuoto che sbagliato". Meglio il badge "non disponibile" che
# un numero finto. I casi (dal giro del 3 nov, gruppo B):
#   - cannella in stecca / di Ceylon -> "Bread, cinnamon" (valori del PANE)
#   - noci tritate -> "Oil, walnut" (olio, non la granella)
#   - habanero -> "Peppers, hot pickled, canned" (salato dalla salamoia)
#
# COSA FA: rimuove SOLO dolce/salato/grasso da proprieta e proprieta_meta sui
# nodi elencati (gli altri assi non si toccano), riportandoli a vuoto. Backup in
# _backup_gusti_pulisci + transazione. DRY-RUN di default; scrive con &esegui=1.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_gusti_pulisci = Blueprint("gusti_pulisci", __name__)

# Nodi da ripulire + motivo (per tracciabilita' onesta nella risposta).
_PULISCI = {
    "ing-cannella-in-stecca": "match 'Bread, cinnamon' (valori del pane, non della spezia)",
    "ing-cannella-di-ceylon": "match 'Bread, cinnamon' (valori del pane, non della spezia)",
    "ing-noci-tritate":       "match 'Oil, walnut' (olio, non la granella)",
    "ing-habanero":           "match 'Peppers, hot pickled' (salato dalla salamoia)",
}
_ASSI = ("dolce", "salato", "grasso")


def _pianifica(nodi_db, ids):
    """PURA: (da_scrivere, campione, non_trovati). Rimuove SOLO dolce/salato/grasso."""
    da_scrivere, campione, non_trovati = [], [], []
    for nid in ids:
        if nid not in nodi_db:
            non_trovati.append(nid)
            continue
        nome, dd = nodi_db[nid]
        if not isinstance(dd, dict):
            dd = {}
        prop = dict(dd.get("proprieta", {}) or {})
        meta = dict(dd.get("proprieta_meta", {}) or {})
        tolti = [a for a in _ASSI if a in prop or a in meta]
        campione.append({"nodo": nid, "nome": nome, "assi_rimossi": tolti,
                         "valori_vecchi": {a: prop.get(a) for a in tolti}})
        if not tolti:
            continue
        for a in _ASSI:
            prop.pop(a, None)
            meta.pop(a, None)
        nuovo = dict(dd)
        nuovo["proprieta"] = prop
        nuovo["proprieta_meta"] = meta
        da_scrivere.append((nid, nuovo))
    return da_scrivere, campione, non_trovati


@bp_gusti_pulisci.route("/admin/gusti-pulisci")
def gusti_pulisci():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive. Riporta a vuoto
    dolce/salato/grasso sui nodi con match USDA sbagliato (meglio vuoto che
    sbagliato). Backup in _backup_gusti_pulisci."""
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
        ids = list(_PULISCI.keys())
        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (ids,))
        nodi_db = {}
        for rid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi_db[rid] = (nome, dd)

        da_scrivere, campione, non_trovati = _pianifica(nodi_db, ids)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_gusti_pulisci
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, nuovo in da_scrivere:
                _nome, dd_old = nodi_db[nid]
                cur.execute("INSERT INTO _backup_gusti_pulisci (id, data_old) VALUES (%s, %s)",
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
            "nodi_in_tabella": len(_PULISCI),
            "nodi_trovati_db": len(nodi_db),
            "da_scrivere": len(da_scrivere),
            "scritti": scritti,
            "non_trovati_nel_db": non_trovati,
            "motivi": _PULISCI,
            "nota": ("Riporta a vuoto dolce/salato/grasso sui nodi con match USDA "
                     "sbagliato (meglio vuoto che sbagliato). Backup in "
                     "_backup_gusti_pulisci. Gli altri assi non si toccano."),
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
