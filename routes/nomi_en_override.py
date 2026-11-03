# ============================================================
# NOMI-EN-OVERRIDE — sovrascrive data.nomi.en su una lista PICCOLA e verificata
# a mano di nodi il cui nome EN esistente faceva agganciare al search USDA il
# cibo SBAGLIATO (es. "cinnamon stick" -> "mozzarella sticks").
#
# PERCHE' OVERWRITE (non fill-only): questi nodi un nome EN ce l'hanno gia', ma
# scomodo. nomi-en-curati (fill-only) non poteva correggerlo. Qui si corregge,
# con backup, SOLO su una lista hand-checked dove il nome giusto e' certo e USDA
# ha davvero il cibo. Il nome 'it' (mostrato agli utenti italiani) NON si tocca.
#
# ONESTA': non scrive gusto, solo il nome EN (il gusto lo deriva poi il search
# col gate 0.6). Backup in _backup_nomi_en_override + transazione. DRY-RUN di
# default; scrive con &esegui=1.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_nomi_en_override = Blueprint("nomi_en_override", __name__)

# ID nodo -> nome EN CORRETTO (sostituisce quello scomodo). Hand-checked: USDA
# ha il cibo sotto questo nome. Fuori da questa lista non si sovrascrive nulla.
_OVERRIDE = {
    "ing-noci-tritate":              "walnuts",       # era "chopped nuts" -> prosciutto tritato
    "ing-granella-di-pistacchio":    "pistachios",    # era "pistachio granules" -> zucchero
    "ing-cannella-in-stecca":        "cinnamon",      # era "cinnamon stick" -> mozzarella sticks
    "ing-cannella-di-ceylon":        "cinnamon",      # era "Ceylon cinnamon" -> pane alla cannella
    "ing-kombu-saccharina-japonica": "kelp seaweed",  # era "kombu" (nessun candidato)
    "ing-habanero":                  "hot pepper",    # era "habanero" (nessun candidato)
}


def _pianifica(nodi_db, override):
    """PURA: (da_scrivere, campione, non_trovati). Sovrascrive nomi.en, preserva il resto."""
    da_scrivere, campione, non_trovati = [], [], []
    for nid, en_nuovo in override.items():
        if nid not in nodi_db:
            non_trovati.append(nid)
            continue
        nome_it, dd = nodi_db[nid]
        if not isinstance(dd, dict):
            dd = {}
        nomi = dd.get("nomi") if isinstance(dd.get("nomi"), dict) else {}
        en_vecchio = (nomi.get("en") or "").strip()
        campione.append({"nodo": nid, "nome_it": nome_it,
                         "en_vecchio": en_vecchio or None, "en_nuovo": en_nuovo,
                         "cambia": en_vecchio != en_nuovo})
        if en_vecchio == en_nuovo:
            continue
        nuovo = dict(dd)
        nn = dict(nomi)
        nn["en"] = en_nuovo
        nuovo["nomi"] = nn
        da_scrivere.append((nid, nuovo))
    return da_scrivere, campione, non_trovati


@bp_nomi_en_override.route("/admin/nomi-en-override")
def nomi_en_override():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (overwrite, backup).
    Corregge il nome EN scomodo di 6 nodi hand-checked. Dopo: rilanciare
    deriva-gusti-mirato per derivarne il gusto con dati USDA veri."""
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
        ids = list(_OVERRIDE.keys())
        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (ids,))
        nodi_db = {}
        for rid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi_db[rid] = (nome, dd)

        da_scrivere, campione, non_trovati = _pianifica(nodi_db, _OVERRIDE)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_nomi_en_override
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, nuovo in da_scrivere:
                _nome, dd_old = nodi_db[nid]
                cur.execute("INSERT INTO _backup_nomi_en_override (id, data_old) VALUES (%s, %s)",
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
            "nodi_in_tabella": len(_OVERRIDE),
            "nodi_trovati_db": len(nodi_db),
            "da_scrivere": len(da_scrivere),
            "scritti": scritti,
            "non_trovati_nel_db": non_trovati,
            "nota": ("Overwrite del solo nome EN (hand-checked), backup in "
                     "_backup_nomi_en_override. Dopo &esegui=1, rilancia "
                     "deriva-gusti-mirato (gli stessi 4 lotti) per derivare il gusto."),
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
