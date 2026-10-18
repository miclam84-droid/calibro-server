# ============================================================
# TRAVASO-NOMI-EN — travasa i nomi inglesi dalla tabella `ingredienti_nomi`
# dentro `data.nomi.en` dei nodi che non ce l'hanno.
#
# PERCHE': il search USDA (deriva-gusti-search) deriva il gusto SOLO se conosce il
# nome EN dell'ingrediente (data.nomi.en del nodo, o _ALIAS_AHN). ~40% dei nodi senza
# gusto vengono saltati come "senza nome EN". Ma il nome EN spesso ESISTE gia' nella
# tabella `ingredienti_nomi` (popolata da build_ingredient_graph.salva_in_grafo), che
# il search NON legge. Travasandolo nei nodi, il search profila molti piu' ingredienti.
#
# SCHEMA sorgente (build_ingredient_graph.init_tables):
#   ingredienti_nomi(node_id TEXT, lang TEXT, nome TEXT, PRIMARY KEY(node_id, lang))
#   -> match AFFIDABILE per node_id (= nodes.id); il nome EN e' la riga con lang='en'.
#   Il nome e' salvato in minuscolo: lo travasiamo com'e' (il search USDA e'
#   case-insensitive), senza reinventarne la grafia.
#
# ONESTA' DEI DATI (vincolo):
#   - fill-only: scrive data.nomi.en SOLO sui nodi Ingrediente/Prodotto che NON ce l'hanno.
#   - niente invenzioni: se per un nodo non c'e' riga EN in ingredienti_nomi -> SALTA.
#   - backup in _backup_travaso_nomi + transazione; DRY-RUN di default, scrive con &esegui=1.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_travaso_nomi = Blueprint("travaso_nomi", __name__)


def _ha_en(dd):
    """True se il nodo ha gia' un data.nomi.en non vuoto (fill-only lo salta)."""
    nomi = dd.get("nomi") if isinstance(dd, dict) and isinstance(dd.get("nomi"), dict) else {}
    return bool((nomi.get("en") or "").strip())


def _pianifica_travaso(nodi, nomi_en):
    """PURA (niente DB/rete, testabile): decide cosa travasare.
      nodi    = [(id, dd_dict), ...]   (dd gia' parsato a dict)
      nomi_en = {node_id: nome_en}     (dalla tabella ingredienti_nomi, lang='en')
    Ritorna (da_scrivere, candidati, trovati, senza_corrispondenza) dove
      da_scrivere = [(id, nome_en, dd_nuovo), ...]   (dd_nuovo con data.nomi.en valorizzato)
    Regole: fill-only (salta chi ha gia' EN); niente invenzioni (no match -> salta)."""
    da_scrivere = []
    candidati = 0
    trovati = 0
    senza = 0
    for nid, dd in nodi:
        if not isinstance(dd, dict):
            dd = {}
        if _ha_en(dd):
            continue  # ha gia' EN: fill-only, non e' candidato
        candidati += 1
        en = (nomi_en.get(nid) or "").strip()
        if not en:
            senza += 1
            continue  # nessuna corrispondenza: NON si inventa, si salta
        trovati += 1
        nuovo = dict(dd)
        nomi = dict(nuovo["nomi"]) if isinstance(nuovo.get("nomi"), dict) else {}
        nomi["en"] = en
        nuovo["nomi"] = nomi
        da_scrivere.append((nid, en, nuovo))
    return da_scrivere, candidati, trovati, senza


@bp_travaso_nomi.route("/admin/travaso-nomi-en")
def travaso_nomi_en():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (fill-only, backup, transazione).
    &limite=N / &offset=N per lavorare a blocchi. Travasa data.nomi.en dai nomi gia'
    presenti nella tabella `ingredienti_nomi` (lang='en'), sbloccando il search USDA."""
    import hmac as _hmac
    import psycopg2

    if not _hmac.compare_digest(str(request.args.get("s", "")), str(os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    try:
        limite = int(request.args.get("limite", "0"))
    except Exception:
        limite = 0
    try:
        offset = int(request.args.get("offset", "0"))
    except Exception:
        offset = 0
    if offset < 0:
        offset = 0

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()

        # La sorgente deve esistere: senza ingredienti_nomi non c'e' nulla da travasare.
        cur.execute("SELECT to_regclass('ingredienti_nomi')")
        if cur.fetchone()[0] is None:
            cur.close(); conn.close()
            return jsonify({
                "errore": "tabella ingredienti_nomi assente",
                "nota": "La sorgente dei nomi EN non esiste ancora su questo DB "
                        "(build_ingredient_graph.init_tables non e' mai girato). Niente da travasare.",
            }), 400

        # Mappa node_id -> nome EN (unica fonte, nessuna invenzione).
        cur.execute("SELECT node_id, nome FROM ingredienti_nomi WHERE lang='en'")
        nomi_en = {r[0]: r[1] for r in cur.fetchall() if r[0] and r[1]}

        # Nodi candidati (stesso universo del search: Ingrediente/Prodotto).
        sql = ("SELECT id, data FROM nodes WHERE type IN ('Ingrediente','Prodotto') "
               "ORDER BY id")
        if limite > 0:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, (limite, offset))
        elif offset:
            sql += " LIMIT ALL OFFSET %s"
            cur.execute(sql, (offset,))
        else:
            cur.execute(sql)
        righe = cur.fetchall()

        nodi = []
        for nid, data in righe:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi.append((nid, dd))

        da_scrivere, candidati, trovati, senza = _pianifica_travaso(nodi, nomi_en)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_travaso_nomi
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, en, dd_nuovo in da_scrivere:
                # backup del data PRIMA (dd_nuovo deriva da dd, basta togliere nomi.en per tornare indietro)
                dd_old = dict(dd_nuovo)
                nomi_old = dict(dd_old.get("nomi") or {})
                nomi_old.pop("en", None)
                dd_old["nomi"] = nomi_old
                cur.execute("INSERT INTO _backup_travaso_nomi (id, data_old) VALUES (%s,%s)",
                            (nid, json.dumps(dd_old, ensure_ascii=False)))
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd_nuovo, ensure_ascii=False), nid))
                scritti += 1
            conn.commit()

        esempi = [{"nodo": nid, "nome_en": en} for nid, en, _ in da_scrivere[:50]]
        cur.close(); conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "fonte": "ingredienti_nomi (lang='en'), match per node_id",
            "limite": limite,
            "offset": offset,
            "candidati": candidati,                 # nodi Ingrediente/Prodotto SENZA data.nomi.en
            "trovati_en": trovati,                  # di questi, quanti hanno un nome EN nella tabella
            "senza_corrispondenza": senza,          # candidati senza riga EN: NON toccati
            "scritti": scritti if esegui else 0,    # 0 in dry-run
            "nota": ("DRY RUN: nessuna scrittura. 'trovati_en' verrebbero scritti in data.nomi.en "
                     "(fill-only). Aggiungi &esegui=1 per scrivere; backup in _backup_travaso_nomi."
                     if not esegui else
                     "ESEGUITO: data.nomi.en valorizzato SOLO dove mancava e c'era corrispondenza in "
                     "ingredienti_nomi. Fill-only, backup in _backup_travaso_nomi. Niente nomi inventati."),
            "esempi": esempi,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
