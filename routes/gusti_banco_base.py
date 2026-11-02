# ============================================================
# GUSTI-BANCO-BASE — profili gusto a REGOLA DI MESTIERE per gli ingredienti
# che i database di composizione (USDA / CIQUAL) non potranno mai coprire:
# spiriti, liquori, bitter/amari, luppoli, malti, sciroppi, aceto, acido
# citrico, lieviti/koji, vino. Per questi "gusto" non e' un nutriente: e'
# carattere di mestiere (gin = alcolico; luppolo = amaro; sciroppo = dolce).
#
# PERCHE' A MANO E NON DAL SEARCH:
#   /admin/deriva-gusti-search deriva dai nutrienti USDA. L'alcol, l'amaro dei
#   luppoli, l'acido dell'aceto NON stanno nei pannelli nutrizionali -> questi
#   nodi restano a gusto vuoto per sempre. Sono pero' la tavolozza del bartender
#   (Bucopertuso): gin, amaro, bitter, vermouth, sciroppi. Lasciarli vuoti e'
#   un buco nel caso d'uso numero uno. Li riempiamo con profili MINIMI.
#
# ONESTA' DEI DATI (vincoli duri):
#   - stato = "stimato" (badge giallo "proposta/stimato", MAI "verificato").
#     fonte = "regola di mestiere — da verificare al banco". Michele conferma
#     i valori esatti al banco (feature verifica gia' presente).
#   - profili MINIMI: scriviamo SOLO gli assi che definiscono l'ingrediente,
#     gli altri restano vuoti. Niente 4.0 piatto su 16 assi.
#   - fill-only per-asse: si scrive un asse SOLO se mancante o gia' "stimato".
#     Mai sopra "corretto"/"verificato"/"da_fonte"/"derivato".
#   - backup in _backup_gusti_base + transazione. DRY-RUN di default; scrive
#     solo con &esegui=1. Match per ID nodo (esatto), non per nome.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

bp_gusti_base = Blueprint("gusti_banco_base", __name__)

# Assi validi (le 16 proprieta' del grafo). Qualsiasi chiave fuori da qui e' un bug.
_ASSI_VALIDI = {
    "dolce", "salato", "acido", "amaro", "umami", "grasso", "corposita",
    "croccante", "astringente", "piccante", "termico", "aroma_fresco",
    "aroma_caldo", "effervescenza", "fermentato", "alcolico",
}

# Profili curati per ID nodo. Valori 0-10. Solo assi definitori.
# Fonte: regola di mestiere (bartending / brewing / cucina di base).
_PROFILI = {
    # — sciroppi / zuccheri / acidi / acque (definizionali) —
    "prod-sciroppo":            {"dolce": 10},
    "ing-sciroppo-zucchero":    {"dolce": 10},
    "ing-sciroppo-semplice-11": {"dolce": 10},
    "ing-saccarosio":           {"dolce": 10},
    "ing-acido-citrico":        {"acido": 9},
    "ing-aceto-di-vino-bianco": {"acido": 8},
    "ing-soda-water":           {"effervescenza": 7},
    "ing-soda":                 {"effervescenza": 7},

    # — spiriti (carattere: alcolico; aroma secondo il distillato) —
    "ahn_scotch":         {"alcolico": 8, "aroma_caldo": 4},   # whisky: caldo/affumicato
    "prod_whiskey":       {"alcolico": 8, "aroma_caldo": 3},
    "ing-gin-london-dry": {"alcolico": 8, "aroma_fresco": 4},  # ginepro/botaniche
    "ing-tequila-blanco": {"alcolico": 8},
    "ing-cachaa":         {"alcolico": 8},
    "ing-absinthe":       {"alcolico": 9, "amaro": 4, "aroma_fresco": 5},  # anice/assenzio

    # — liquori (dolce + alcol + aroma firma) —
    "ing-amaretto":     {"dolce": 7, "alcolico": 5, "aroma_caldo": 4},  # mandorla
    "ing-maraschino":   {"dolce": 6, "alcolico": 5},
    "ing-cointreau":    {"dolce": 6, "alcolico": 6, "aroma_fresco": 4}, # arancia
    "ing-grand-marnier":{"dolce": 6, "alcolico": 6, "aroma_caldo": 3},

    # — bitter / amari / vermouth (amaro + alcol) —
    "ing-amaro":            {"amaro": 8, "alcolico": 5, "dolce": 3},
    "ing-peychauds-bitter": {"amaro": 7, "alcolico": 6, "aroma_caldo": 3},  # anice
    "ing-angostura-bitter": {"amaro": 8, "alcolico": 6, "aroma_caldo": 4},  # spezie
    "ing-bitter-angostura": {"amaro": 8, "alcolico": 6, "aroma_caldo": 4},
    "ing-vermouth-dry":     {"amaro": 3, "alcolico": 4, "aroma_fresco": 3},
    "ing-ginger-ale":       {"dolce": 6, "effervescenza": 6, "piccante": 3},  # zenzero

    # — luppoli (amaricanti; aroma secondo varieta') —
    "ing-luppolo-saaz":              {"amaro": 6, "aroma_fresco": 4},  # nobile, delicato
    "ing-luppolo-styrian-goldings":  {"amaro": 6, "aroma_fresco": 4},
    "ing-luppolo-cascade":           {"amaro": 7, "aroma_fresco": 5},  # agrume
    "ing-luppolo-amarillo":          {"amaro": 7, "aroma_fresco": 5},  # agrume
    "ing-luppolo-mosaic":            {"amaro": 7, "aroma_fresco": 5},
    "ing-luppolo-citra":             {"amaro": 7, "aroma_fresco": 6},  # agrume intenso

    # — malti (dolce basso, corpo) —
    "ing-malto-pilsner-2-row": {"dolce": 3, "corposita": 2},
    "ing-malto-special-b":     {"dolce": 4, "corposita": 3, "aroma_caldo": 3},  # caramello/uvetta
    "ing-malto-crystal-40l":   {"dolce": 4, "corposita": 3},                     # caramello
    "ing-malto-pale-ale":      {"dolce": 3, "corposita": 2},
    "ing-malto-diastasico":    {"dolce": 3},                                     # enzimatico, poco gusto

    # — lieviti / koji (fermentazione) —
    "prod-madre":                  {"acido": 3, "fermentato": 6},  # lievito madre
    "ing-lievito-ale-americano-us05": {"fermentato": 2},            # US-05: pulito
    "ai_koji":                     {"fermentato": 6, "umami": 4},   # sviluppa umami

    # — vino (tannico) —
    "ing-nebbiolo": {"astringente": 6, "acido": 5, "alcolico": 4, "amaro": 3},
}

_FONTE = "regola di mestiere — da verificare al banco"


def _pianifica(nodi_db, profili):
    """PURA (niente DB/rete, testabile): decide cosa scrivere.
      nodi_db = {id: (nome, dd_dict)}   (dd gia' parsato)
      profili = {id: {asse: val}}
    Ritorna (da_scrivere, campione, non_trovati) dove
      da_scrivere = [(id, dd_nuovo, cambi_dict), ...]
    Regole: fill-only per-asse (scrive solo se mancante o gia' 'stimato');
            profili minimi (solo assi elencati); nessuna invenzione fuori lista."""
    da_scrivere = []
    campione = []
    non_trovati = []
    for nid, assi in profili.items():
        if nid not in nodi_db:
            non_trovati.append(nid)
            continue
        nome, dd = nodi_db[nid]
        if not isinstance(dd, dict):
            dd = {}
        prop = dict(dd.get("proprieta", {}) or {})
        meta = dict(dd.get("proprieta_meta", {}) or {})
        cambi = {}
        riga = {"nodo": nid, "nome": nome, "assi": {}}
        for asse, val in assi.items():
            if asse not in _ASSI_VALIDI:
                continue  # guardia: mai scrivere un asse inesistente
            vecchio = prop.get(asse)
            stato_vecchio = (meta.get(asse, {}) or {}).get("stato")
            scrivibile = stato_vecchio in (None, "stimato")  # fill-only
            riga["assi"][asse] = {
                "vecchio": vecchio, "stato_vecchio": stato_vecchio or "(vuoto)",
                "nuovo": val, "scrivibile": scrivibile,
            }
            if scrivibile:
                cambi[asse] = val
        if cambi:
            nuovo = dict(dd)
            np = dict(prop)
            nm = dict(meta)
            for asse, val in cambi.items():
                np[asse] = val
                nm[asse] = {"stato": "stimato", "fonte": _FONTE}
            nuovo["proprieta"] = np
            nuovo["proprieta_meta"] = nm
            da_scrivere.append((nid, nuovo, cambi))
        campione.append(riga)
    return da_scrivere, campione, non_trovati


@bp_gusti_base.route("/admin/deriva-gusti-base")
def deriva_gusti_base():
    """DRY-RUN di default (?s=ADMIN_SECRET). &esegui=1 scrive (fill-only, backup,
    transazione). Profili gusto a regola di mestiere per bar/birra/base che USDA
    non copre. Match per ID nodo. Stato 'stimato' — da verificare al banco."""
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

        # carica i nodi bersaglio (solo quelli in _PROFILI)
        ids = list(_PROFILI.keys())
        cur.execute("SELECT id, name, data FROM nodes WHERE id = ANY(%s)", (ids,))
        nodi_db = {}
        for rid, nome, data in cur.fetchall():
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            nodi_db[rid] = (nome, dd)

        da_scrivere, campione, non_trovati = _pianifica(nodi_db, _PROFILI)

        scritti = 0
        if esegui and da_scrivere:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_gusti_base
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
            for nid, nuovo, _cambi in da_scrivere:
                _nome, dd_old = nodi_db[nid]
                cur.execute("INSERT INTO _backup_gusti_base (id, data_old) VALUES (%s, %s)",
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
            "nodi_in_tabella": len(_PROFILI),
            "nodi_trovati_db": len(nodi_db),
            "da_scrivere": len(da_scrivere),
            "scritti": scritti,
            "non_trovati_nel_db": non_trovati,
            "stato_assegnato": "stimato",
            "fonte": _FONTE,
            "nota": ("Profili minimi a regola di mestiere per cio' che USDA non copre "
                     "(alcol/amaro/sciroppi/malti). Fill-only: mai sopra valori "
                     "corretti/verificati. &esegui=1 per scrivere. Verifica i valori al banco."),
            "campione": campione[:50],
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
