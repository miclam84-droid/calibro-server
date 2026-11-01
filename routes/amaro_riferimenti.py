# ============================================================
# AMARO-RIFERIMENTI — valori di amaro (0-10) per i bitter NOTI, da LETTERATURA, con la
# distinzione onesta misurato/stimato. Complementa /admin/deriva-amaro (che stima
# l'amaro dal CONTEGGIO dei marcatori molecolari nel profilo del nodo).
#
# Perche' serve accanto alla macchina marcatori:
#  - il conteggio marcatori e' potency-cieco (la genziana ha 1 marcatore ma e'
#    amarissima: finirebbe bassa); qui la genziana ha il valore giusto da letteratura.
#  - molti composti amari sono non-volatili e NON stanno nei profili aromatici dei nodi,
#    quindi la macchina marcatori su di loro spara a vuoto; qui il valore c'e' comunque.
#
# Tre stati nel grafo: "riferimento" (questo file, da letteratura) ha PRECEDENZA sul
# "derivato" (marcatori) ma NON sovrascrive "verificato"/"banco" (assaggio tuo).
# La macchina marcatori, a sua volta, protegge "riferimento" (non e' in None/"stimato"),
# quindi l'ordine di lancio e' indifferente. Dove non c'e' ne' riferimento ne' marcatori,
# l'amaro resta ASSENTE (non caratterizzato), mai 0 inventato.
#
# tipo per riga: "misurato" = punteggio sensoriale 0-10 da panel; "stimato" = inferito
# dal composto amaro, NON misurato al palato.
#
# Sicurezza: _admin_ok, DRY-RUN di default, &esegui=1 scrive (backup in _backup_amaro).
# Uso:  /admin/amaro-riferimenti?s=SECRET          (anteprima)
#       /admin/amaro-riferimenti?s=SECRET&esegui=1 (scrive)
# ============================================================
import json, traceback
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_amaro_riferimenti = Blueprint("amaro_riferimenti", __name__)

# nome (match esatto LOWER(name), preferisce ing-), amaro 0-10, tipo, confidenza, fonte.
# Solo righe alta/media confidenza. Lasciati "non caratterizzati" (nessuna fonte solida):
# rabarbaro, noce, melanzana, mandorla amara, arancia amara, bergamotto, chinotto, scarola.
_RIF = [
    ("olio extravergine", 3.0, "misurato", "alta", "panel IOC/COI T.20/Doc.15 (mediana amaro 0-10)"),
    ("cioccolato fondente", 7.5, "misurato", "alta", "Wagner et al. 2023 Physiol Behav 270:114308 (panel, 85% cacao)"),
    ("caffè espresso", 8.0, "stimato", "media", "caffeina+clorogenici+fenilindani; Gao&Peterson; Chambers 2016"),
    ("caffè filtro", 6.0, "stimato", "media", "caffeina+acidi clorogenici; Hunaefi 2019"),
    ("cacao", 8.0, "stimato", "media", "teobromina+flavanoli; BitterDB; Wagner 2023"),
    ("luppolo", 9.0, "stimato", "media", "iso-alfa-acidi (isoumuloni)"),
    ("pompelmo", 6.0, "stimato", "media", "naringina+limonina sopra soglia; Guadagni 1973"),
    ("carciofo", 5.0, "stimato", "media", "cinaropicrina; Zuccolo et al. 2025 Molecules 30:2649"),
    ("radicchio", 6.5, "stimato", "media", "lattoni sesquiterpenici; Domont 2023; Leclercq 1992"),
    ("cicoria", 6.0, "stimato", "media", "lattoni sesquiterpenici (Cichorium); Domont 2023"),
    ("tarassaco", 7.0, "stimato", "media", "lattoni sesquiterpenici; VTT"),
    ("rucola", 5.0, "stimato", "media", "glucosinolati; Bell et al. 2020 Foods 9:1799"),
    ("cavoletti di bruxelles", 5.0, "stimato", "media", "sinigrina+progoitrina; van Doorn 1998"),
    ("cime di rapa", 6.0, "stimato", "media", "glucosinolati Brassica rapa; van Doorn 1998"),
    ("broccolo", 3.5, "stimato", "media", "glucosinolati; van Doorn 1998"),
    ("cavolo", 3.0, "stimato", "media", "glucosinolati (sinigrina); van Doorn 1998"),
    ("tè verde", 4.0, "stimato", "media", "catechine/EGCG; Nakamura et al. 2026 Foods 15:1409"),
    ("acqua tonica", 5.5, "stimato", "media", "chinino; FDA 21 CFR 172.575"),
    ("genziana", 9.5, "stimato", "media", "amarogentina (tra i piu' amari noti); Behrens 2009; BitterDB"),
    ("birra", 4.0, "stimato", "media", "iso-alfa-acidi (IBU); varia per stile, valore lager standard"),
]

# la macchina marcatori scrive stato "derivato"; "riferimento" ha precedenza su quello,
# ma non su un valore verificato al banco dall'autore.
_SOVRASCRIVIBILI = (None, "", "stimato", "derivato")


@bp_amaro_riferimenti.route("/admin/amaro-riferimenti")
def amaro_riferimenti():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    conn = _get_conn()
    righe = []
    scritti = 0
    try:
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_amaro
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")
        for nome, val, tipo, conf, fonte in _RIF:
            r = {"ingrediente": nome, "amaro": val, "tipo": tipo, "conf": conf}
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC LIMIT 1""", (nome,))
            row = cur.fetchone()
            if not row:
                r["stato"] = "nodo non trovato"
                righe.append(r)
                continue
            nid, nome_nodo, data = row
            r["nodo"] = nid
            r["nodo_nome"] = nome_nodo
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
            prop = dict(dd.get("proprieta", {}) or {})
            meta_prop = dict(dd.get("proprieta_meta", {}) or {})
            stato_vecchio = (meta_prop.get("amaro", {}) or {}).get("stato")
            if stato_vecchio not in _SOVRASCRIVIBILI:
                r["stato"] = "protetto (%s) — non tocco" % stato_vecchio
                righe.append(r)
                continue
            r["vecchio"] = prop.get("amaro")
            r["stato_vecchio"] = stato_vecchio or "non-taggato"
            if esegui:
                cur.execute("INSERT INTO _backup_amaro (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                metodo = ("0-10 panel sensoriale" if tipo == "misurato"
                          else "0-10 stima dal composto amaro (NON misurato al palato)")
                prop["amaro"] = val
                meta_prop["amaro"] = {"stato": "riferimento", "tipo": tipo, "fonte": fonte,
                                      "confidenza": conf, "metodo": metodo,
                                      "stima": (tipo != "misurato")}
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta_prop
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1
                r["stato"] = "scritto (%s)" % tipo
            else:
                r["stato"] = "da scrivere (%s)" % tipo
            righe.append(r)
        if esegui:
            conn.commit()
        cur.close()
        trovati = sum(1 for r in righe if "nodo" in r)
        misurati = sum(1 for x in _RIF if x[2] == "misurato")
        return jsonify({
            "modo": "SCRITTO" if esegui else "ANTEPRIMA (dry-run) — aggiungi &esegui=1 per scrivere",
            "totale_tabella": len(_RIF),
            "di_cui_misurato": misurati, "di_cui_stimato": len(_RIF) - misurati,
            "nodi_risolti": trovati, "nodi_non_trovati": len(_RIF) - trovati,
            "scritti": scritti if esegui else "(dry-run)",
            "nota": "amaro da letteratura (stato 'riferimento'): precede i marcatori, non il "
                    "verificato al banco. Fill su vuoto/stimato/derivato. Chi non c'e' resta non caratterizzato.",
            "righe": righe,
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e), "trace": traceback.format_exc()[-800:]}), 500
    finally:
        _release_conn(conn)
