# ============================================================
# DERIVA-AMARO — pipeline dell'amaro da MARCATORI MOLECOLARI (composti amari noti)
# L'amaro NON sta nelle tabelle nutrizionali (USDA/CIQUAL): sta nei COMPOSTI.
# Qui si deriva l'asse amaro contando, fra i `composti_aromatici` del nodo, quanti
# sono marcatori amari DOCUMENTATI (registro data/composti_amari.csv, ogni voce con
# fonte citabile). È una STIMA da marcatori — presenza di composti amari noti — NON
# una misura al banco. Taggata esplicitamente come stima.
#
# DECISIONE DI METODO (argomentata, non opzioni):
#  - Niente proxy generico sui polifenoli: sarebbe un'analogia falsa (molti polifenoli
#    non sono amari). Si usano SOLO composti amari attribuiti a una fonte reale.
#  - Niente peso per "potenza" del singolo composto: i coefficienti di potenza non
#    hanno una base citabile comune, inventarli sarebbe il bug della provenienza
#    fabbricata. Quindi peso 1 per marcatore: l'indice è ORDINALE, sulla PRESENZA.
#  - Le intensità stimate dall'AI nei composti (intensita_nel_prodotto) NON si usano:
#    sono stime del modello, non misure. Si guarda solo la presenza del marcatore.
#  - Il match preferisce il CAS (identificatore robusto, indipendente dalla lingua);
#    il nome è fallback.
#
# DRY-RUN di default (?s=ADMIN_SECRET). Con &esegui=1 scrive (fill-only, backup, transazione):
#  proprieta["amaro"] + proprieta_meta["amaro"]={stato:derivato, fonte:marcatori molecolari,
#  formula, stima:true}. Dove il nodo non ha composti amari noti -> NON scrive (amaro resta "—").
# ============================================================
import os
import csv
import json

from flask import Blueprint, request, jsonify
from routes.deriva_gusti import _interp, _ESCLUDI

bp_amaro = Blueprint("deriva_amaro", __name__)

FORMULA_VER = "amaro-marcatori-v1"

# Curva PURA e documentata: n. di marcatori amari DISTINTI nel nodo -> asse amaro 0-10.
# Saturante: un marcatore amaro noto (es. chinina nel tonico, caffeina nel caffè,
# naringina nel pompelmo) segnala già amaro netto; più marcatori -> più alto, con saturazione.
# È una scala ordinale di PRESENZA, non una misura di concentrazione.
_AMARO = [(0, 0), (1, 4), (2, 6), (3, 7), (4, 8), (6, 9), (8, 10)]

_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "composti_amari.csv")
_REG = None


def _norm(s):
    return (s or "").strip().lower()


def _registro():
    """Carica (una volta) il registro dei composti amari dal CSV citabile.
    Ritorna (per_nome, per_cas, meta):
      per_nome: {nome_norm -> chiave_canonica}
      per_cas:  {cas_norm  -> chiave_canonica}
      meta:     {chiave_canonica -> {"compound","classe","fonte"}}
    La chiave canonica è il CAS se presente (così sinonimi IT/EN dello stesso composto
    contano come UN marcatore), altrimenti il nome normalizzato. Vuoto -> nessuna scrittura."""
    global _REG
    if _REG is not None:
        return _REG
    per_nome, per_cas, meta = {}, {}, {}
    try:
        with open(_CSV, encoding="utf-8") as f:
            # Salta le righe di commento (#) PRIMA dell'header: altrimenti csv.DictReader
            # prenderebbe la prima riga-commento come intestazione e perderebbe tutte le colonne.
            righe = [ln for ln in f if not ln.lstrip().startswith("#")]
            for r in csv.DictReader(righe):
                comp = (r.get("compound") or "").strip()
                nome = _norm(comp)
                if not comp or nome.startswith("#"):
                    continue
                cas = _norm(r.get("cas"))
                classe = (r.get("classe") or "").strip()
                fonte = (r.get("fonte") or "").strip()
                chiave = cas if cas else nome
                if nome:
                    per_nome[nome] = chiave
                if cas:
                    per_cas[cas] = chiave
                # prima voce vince per la meta della chiave (sinonimi condividono classe/fonte)
                meta.setdefault(chiave, {"compound": comp, "classe": classe, "fonte": fonte})
    except FileNotFoundError:
        pass
    _REG = (per_nome, per_cas, meta)
    return _REG


def _marcatori(composti, per_nome, per_cas):
    """Funzione PURA: dai `composti_aromatici` di un nodo ricava i marcatori amari
    DISTINTI presenti. Match per CAS (preferito) o per nome. Ritorna la lista ordinata
    delle chiavi canoniche trovate (senza duplicati). Robusta a input sporchi."""
    trovati = []
    visti = set()
    if not isinstance(composti, list):
        return trovati
    for c in composti:
        if not isinstance(c, dict):
            continue
        cas = _norm(c.get("cas"))
        nome = _norm(c.get("nome"))
        chiave = None
        if cas and cas in per_cas:
            chiave = per_cas[cas]
        elif nome and nome in per_nome:
            chiave = per_nome[nome]
        if chiave and chiave not in visti:
            visti.add(chiave)
            trovati.append(chiave)
    return sorted(trovati)


def _indice_amaro(n):
    """Funzione PURA: n. di marcatori amari distinti -> voto amaro 0-10 (curva _AMARO).
    n=0 è gestito dal chiamante (non scrive: amaro resta ignoto, non 0)."""
    return _interp(n, _AMARO)


@bp_amaro.route("/admin/deriva-amaro")
def deriva_amaro():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (fill-only, backup, transazione).
    &limite=N / &offset=N per lavorare a blocchi. Legge i composti_aromatici del nodo e
    deriva l'asse amaro dai marcatori molecolari noti (STIMA, non misura al banco).
    Se il registro data/composti_amari.csv è vuoto, non scrive niente."""
    import os as _os, hmac as _hmac
    import psycopg2

    if not _hmac.compare_digest(str(request.args.get("s", "")), str(_os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    per_nome, per_cas, meta = _registro()
    if not meta:
        return jsonify({
            "dry_run": True, "fonte_registro": "data/composti_amari.csv", "voci_registro": 0,
            "nota": "Registro composti amari VUOTO. La macchina è pronta: popola "
                    "data/composti_amari.csv (colonne: compound, cas, classe, fonte) con composti "
                    "amari da fonte citabile. Nessun composto viene inventato.",
            "campione": [],
        })

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
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_amaro
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        sql = ("SELECT id, name, data FROM nodes "
               "WHERE type IN ('Ingrediente','Prodotto') ORDER BY id")
        if limite > 0:
            sql += " LIMIT %s OFFSET %s"
            cur.execute(sql, (limite, offset))
        elif offset:
            sql += " LIMIT ALL OFFSET %s"
            cur.execute(sql, (offset,))
        else:
            cur.execute(sql)
        righe = cur.fetchall()

        campione, scritti, senza_marcatori, protetti = [], 0, 0, 0
        for nid, nome_nodo, data in righe:
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                protetti += 1
                continue

            chiavi = _marcatori(dd.get("composti_aromatici"), per_nome, per_cas)
            n = len(chiavi)
            if n == 0:
                senza_marcatori += 1
                continue  # nessun marcatore amaro noto -> amaro resta "—", non si scrive 0

            prop = dict(dd.get("proprieta", {}) or {})
            meta_prop = dict(dd.get("proprieta_meta", {}) or {})
            stato_vecchio = (meta_prop.get("amaro", {}) or {}).get("stato")
            scrivibile = stato_vecchio in (None, "stimato")  # fill-only: mai su corretto/verificato/derivato

            voto = _indice_amaro(n)
            marcatori_nomi = [meta[k]["compound"] for k in chiavi]
            fonti = sorted({meta[k]["fonte"].split(";")[0].strip() for k in chiavi})

            if len(campione) < 50:
                campione.append({
                    "nodo": nid, "nome": nome_nodo, "vecchio": prop.get("amaro"),
                    "stato_vecchio": stato_vecchio or "non-taggato",
                    "n_marcatori": n, "marcatori": marcatori_nomi,
                    "nuovo_stima": voto, "scrivibile": scrivibile,
                })

            if esegui and scrivibile:
                cur.execute("INSERT INTO _backup_amaro (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                prop["amaro"] = voto
                meta_prop["amaro"] = {
                    "stato": "derivato",
                    "fonte": "marcatori molecolari — " + ", ".join(fonti),
                    "formula": FORMULA_VER,
                    "stima": True,
                    "nota": "STIMA da marcatori molecolari (presenza di composti amari noti), NON misura al banco",
                    "n_marcatori": n,
                    "marcatori": marcatori_nomi,
                }
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta_prop
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()
        return jsonify({
            "dry_run": (not esegui), "formula": FORMULA_VER,
            "fonte_registro": "data/composti_amari.csv", "voci_registro": len(meta),
            "nodi_esaminati": len(righe), "offset": offset,
            "senza_marcatori_amari": senza_marcatori, "saltati_protetti_rari": protetti,
            "scritti": scritti if esegui else 0,
            "metodo": "STIMA da marcatori molecolari (composti amari noti nel nodo), NON misura al banco.",
            "nota": ("DRY RUN: nessun dato scritto. Aggiungi &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_amaro; amaro taggato "
                     "stima:true con le fonti dei marcatori; mai sovrascritto corretto/verificato."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
