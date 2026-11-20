# ============================================================
# DERIVA-UMAMI — asse UMAMI DERIVATO da letteratura (Umami Information Center)
# Fratello di deriva_gusti_ciqual.py. L'umami NON e' derivabile da CIQUAL/USDA
# (nessun nutriente-proxy: il glutammato LIBERO e i ribonucleotidi non sono nelle
# tabelle nutrizionali). Fonte: Umami Information Center (umamiinfo.com), che
# pubblica glutammato libero + inosinato (IMP) + guanilato (GMP) in mg/100g.
#
# MODELLO: Equivalent Umami Concentration (EUC, Yamaguchi 1967), lo standard di
# letteratura per la SINERGIA glutammato x ribonucleotidi:
#   EUC = Glu + 1218 * Glu * (IMP + 2.3*GMP)    [g MSG-equivalenti / 100 g]
# dove Glu/IMP/GMP sono in g/100g; 2.3 = coefficiente umami del GMP rispetto all'IMP;
# 1218 = costante di sinergia. Poi EUC -> scala 0-10 con curva LOGARITMICA (la
# percezione del gusto e' ~logaritmica, Weber-Fechner), ancorata a cibi noti
# (carota ~2, pomodoro secco ~9, shiitake secco ~10).
#
# ONESTA': stato = "derivato" (da letteratura), MAI "misurato". Solo dove il dato
# esiste nella fonte. Dati locali: data/umami_umamiinfo.csv (niente rete).
# Fill-only: non tocca mai umami gia' verificato/misurato/corretto (ne' manuale,
# salvo &supera_manuale=1). DRY-RUN di default; con &esegui=1 scrive in transazione
# con backup in _backup_umami_derivati.
# ============================================================
import os
import csv
import json
import math

from flask import Blueprint, request, jsonify
from routes.deriva_gusti import _interp, _ESCLUDI

bp_umami = Blueprint("deriva_umami", __name__)

FORMULA_VER = "umami-euc-v1"
FONTE = "Umami Information Center (letteratura)"
FONTE_URL = "https://www.umamiinfo.com/richfood/foodstuff/"

# Costanti del modello EUC (Yamaguchi 1967; usato nella letteratura sull'umami).
_K_SINERGIA = 1218.0   # costante di sinergia Glu x ribonucleotidi
_COEF_GMP = 2.3        # umami del GMP relativo all'IMP (=1)

# Curva LOG10(EUC) -> umami 0-10. CALIBRATA sulle ancore solide della scala
# del prodotto (SCALE-SENSORIALI-DEFINIZIONE.md): pomodoro maturo = 4, parmigiano = 8.
#   pomodoro maturo EUC~0.2 (log -0.70) -> 4.0  [ancora prodotto]
#   parmigiano      EUC~1.3 (log  0.11) -> 8.0  [ancora prodotto]
# I cibi con SINERGIA (glutammato + ribonucleotidi) salgono sopra 8 verso 10:
#   katsuobushi EUC~25 (log 1.4) -> 9.4 ; shiitake secco EUC~446 (log 2.65) -> 10.
# NOTA: due ancore-bozza della scala (funghi secchi=6, colatura=10) risultano
# mis-tarate alla luce della sinergia — vedi briefing/canone, decisione di Michele.
_UMAMI_LOG = [(-2.0, 0.5), (-1.3, 2.0), (-0.7, 4.0), (-0.3, 6.0), (0.11, 8.0),
              (0.5, 8.7), (1.0, 9.2), (1.5, 9.5), (2.0, 9.8), (2.65, 10.0)]

_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "umami_umamiinfo.csv")
_TBL = None


def _tabella():
    """Carica (una volta) la tabella Umami Information Center: {chiave: {misure}}."""
    global _TBL
    if _TBL is not None:
        return _TBL
    _TBL = {}
    try:
        with open(_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ch = (r.get("chiave") or "").strip()
                if not ch:
                    continue

                def fl(k):
                    v = (r.get(k) or "").strip()
                    if v in ("", "nan", "None"):
                        return 0.0
                    try:
                        return float(v)
                    except ValueError:
                        return 0.0

                _TBL[ch] = {
                    "nome": r.get("nome_fonte", ""),
                    "categoria": r.get("categoria", ""),
                    "glu": fl("glu"), "glu_raw": (r.get("glu_raw") or "").strip(),
                    "imp": fl("imp"), "imp_raw": (r.get("imp_raw") or "").strip(),
                    "gmp": fl("gmp"), "gmp_raw": (r.get("gmp_raw") or "").strip(),
                }
    except FileNotFoundError:
        _TBL = {}
    return _TBL


def _calc_euc(glu_mg, imp_mg, gmp_mg):
    """EUC (g MSG-eq/100g) dalla formula di Yamaguchi. Input in mg/100g."""
    glu = (glu_mg or 0.0) / 1000.0
    imp = (imp_mg or 0.0) / 1000.0
    gmp = (gmp_mg or 0.0) / 1000.0
    return glu + _K_SINERGIA * glu * (imp + _COEF_GMP * gmp)


def _deriva(row):
    """Da misure Umami Information Center -> asse umami 0-10 (via EUC + curva log).
    Ritorna None se non c'e' glutammato (niente umami derivabile dalla fonte)."""
    if not row or (row.get("glu") or 0.0) <= 0.0:
        return None
    euc = _calc_euc(row.get("glu"), row.get("imp"), row.get("gmp"))
    if euc <= 0:
        return None
    val = _interp(math.log10(euc), _UMAMI_LOG)
    return {
        "val": val,
        "euc": round(euc, 3),
        "grezzo": {
            "glutammato_mg": row.get("glu"), "glutammato_raw": row.get("glu_raw"),
            "inosinato_mg": row.get("imp"), "inosinato_raw": row.get("imp_raw"),
            "guanilato_mg": row.get("gmp"), "guanilato_raw": row.get("gmp_raw"),
            "euc_g_eq": round(euc, 3),
        },
    }


# --- Match CURATO nome italiano del nodo -> chiave della tabella umami (verificato
#     a mano: solo cibi la cui forma corrisponde davvero al dato della fonte) ---
_MATCH = {
    # mare
    "nori": "nori", "wakame": "wakame", "katsuobushi": "katsuobushi",
    "tonno essiccato": "tonno_essiccato",
    "vongola": "vongola", "vongole": "vongola", "vongola verace": "vongola_verace",
    "capesante": "capesante", "cozza": "cozza", "cozze": "cozza",
    "gambero": "gambero", "gamberi": "gambero",
    "ricci di mare": "ricci", "ricci": "ricci",
    "calamaro": "calamaro", "polpo": "polpo", "ricciola": "ricciola",
    "sardina": "sardina", "sardine": "sardina", "tonno": "tonno",
    "orata": "orata", "sugarello": "sugarello", "sgombro": "sgombro",
    "merluzzo": "merluzzo", "ostrica": "ostrica", "ostriche": "ostrica",
    "acciughe": "acciughe", "acciuga": "acciughe", "alici": "acciughe",
    "acciuga salata": "acciughe", "acciughe sott'olio": "acciughe",
    # ortaggi
    "pomodori secchi": "pomodori_secchi", "pomodoro secco": "pomodori_secchi",
    "piselli": "piselli", "aglio": "aglio", "mais": "mais",
    "soia": "soia", "fave": "fave", "fava": "fave",
    "patata": "patata", "patata dolce": "patata_dolce",
    "spinaci": "spinaci", "carota": "carota", "asparago": "asparago",
    "asparagi": "asparago", "cavolo": "cavolo", "cipolla": "cipolla",
    "cipollotto": "cipollotto", "broccolo": "broccolo", "sedano": "sedano",
    "zenzero": "zenzero", "daikon": "daikon",
    # fermentati
    "natto": "natto", "colatura di alici": "colatura", "colatura": "colatura",
    "garum": "colatura", "salsa di pesce": "colatura",
    "salsa di ostriche": "salsa_ostriche", "salsa di soia": "salsa_soia",
    "miso": "miso",
    # funghi
    "shiitake": "shiitake", "shiitake secco": "shiitake_secco",
    "shimeji": "shimeji", "enoki": "enoki",
    "champignon": "champignon", "funghi": "champignon", "tartufo": "tartufo",
    # carne / uovo
    "uovo": "uovo", "manzo": "manzo", "maiale": "maiale", "pollo": "pollo",
}


@bp_umami.route("/admin/deriva-umami")
def deriva_umami():
    """DRY-RUN di default (?s=SECRET). Con &esegui=1 scrive (fill-only, backup+transazione).
    &offset / &limite per blocchi. &supera_manuale=1 per sovrascrivere anche umami
    'manuale'/'stimato' non taggato (default: no). Dati locali: niente rete."""
    import psycopg2

    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    tbl = _tabella()
    if not tbl:
        return jsonify({"errore": "tabella umami non trovata (data/umami_umamiinfo.csv)"}), 500

    esegui = request.args.get("esegui") == "1"
    # &supera_manuale=1: puo' reclamare un umami gia' presente ma tagga solo come
    # "stimato" o senza stato/fonte affidabile. Default conservativo: NON tocca nulla
    # che non sia None o 'stimato'. Mai tocca verificato/misurato/corretto/derivato.
    supera_manuale = request.args.get("supera_manuale") == "1"
    try:
        limite = int(request.args.get("limite", "0"))
    except ValueError:
        limite = 0
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    if offset < 0:
        offset = 0

    coppie = list(_MATCH.items())
    if offset:
        coppie = coppie[offset:]
    if limite > 0:
        coppie = coppie[:limite]

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_umami_derivati
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        campione, scritti = [], 0
        saltati_nomatch, saltati_protetti, saltati_dato, saltati_protetto_stato = 0, 0, 0, 0

        for nome_it, chiave in coppie:
            cur.execute("""SELECT id, name, data FROM nodes
                           WHERE type IN ('Ingrediente','Prodotto') AND LOWER(name)=LOWER(%s)
                           ORDER BY (id LIKE 'ing-%%') DESC, id LIMIT 1""", (nome_it,))
            row = cur.fetchone()
            if not row:
                saltati_nomatch += 1
                continue
            nid, nome_nodo, data = row
            dd = data if isinstance(data, dict) else (json.loads(data) if data else {})

            testo = (str(nome_nodo) + " " + str(dd.get("kind", "")) + " " + str(dd.get("varieta_di", ""))).lower()
            if dd.get("kind") == "varieta" or any(x in testo for x in _ESCLUDI):
                saltati_protetti += 1
                continue

            src = tbl.get(chiave)
            der = _deriva(src)
            if not der:
                saltati_dato += 1
                continue

            prop = dict(dd.get("proprieta", {}) or {})
            meta = dict(dd.get("proprieta_meta", {}) or {})
            vecchio = prop.get("umami")
            meta_u = meta.get("umami", {}) or {}
            stato_vecchio = meta_u.get("stato")

            # fill-only: scrivibile solo se assente o 'stimato'. Con supera_manuale
            # include anche uno stato non riconosciuto (manuale senza tag affidabile).
            scrivibile = stato_vecchio in (None, "stimato")
            if (not scrivibile and supera_manuale
                    and stato_vecchio not in ("verificato", "misurato", "corretto", "derivato")):
                scrivibile = True
            if not scrivibile:
                saltati_protetto_stato += 1

            riga = {
                "nodo": nid, "nome": nome_nodo, "chiave_fonte": chiave,
                "nome_fonte": src.get("nome", ""), "categoria": src.get("categoria", ""),
                "vecchio": vecchio, "stato_vecchio": stato_vecchio or "assente",
                "nuovo_derivato": der["val"], "euc": der["euc"],
                "grezzo": der["grezzo"], "scrivibile": scrivibile,
            }
            if len(campione) < 60:
                campione.append(riga)

            if esegui and scrivibile:
                cur.execute("INSERT INTO _backup_umami_derivati (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                prop["umami"] = der["val"]
                meta["umami"] = {
                    "stato": "derivato", "fonte": FONTE, "fonte_url": FONTE_URL,
                    "formula": FORMULA_VER, "grezzo": der["grezzo"],
                    "nota": "derivato da letteratura: glutammato libero + ribonucleotidi "
                            "(Equivalent Umami Concentration, Yamaguchi). Non misurato al banco.",
                }
                dd["proprieta"] = prop
                dd["proprieta_meta"] = meta
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd, ensure_ascii=False), nid))
                scritti += 1

        if esegui:
            conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "dry_run": (not esegui),
            "fonte": FONTE, "fonte_url": FONTE_URL, "formula": FORMULA_VER,
            "modello": "EUC = Glu + 1218*Glu*(IMP + 2.3*GMP), poi log10(EUC) -> 0-10",
            "match_tentati": len(coppie), "offset": offset,
            "totale_match_curati": len(_MATCH),
            "voci_tabella_fonte": len(tbl),
            "nodi_non_trovati": saltati_nomatch,
            "saltati_protetti_rari": saltati_protetti,
            "saltati_dato": saltati_dato,
            "saltati_gia_affidabile": saltati_protetto_stato,
            "supera_manuale": supera_manuale,
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato modificato. Aggiungi &esegui=1 per scrivere."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_umami_derivati; "
                     "asse umami derivato da letteratura (Umami Information Center), mai "
                     "sovrascritto verificato/misurato/corretto/derivato."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback()
                conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
