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


# Categorie vegetali/fungine: l'inosinato (IMP) viene dal muscolo animale -> nelle
# piante e' NON APPLICABILE, non "assunto zero". Il guanilato (GMP) e' tipico dei
# funghi/vegetali essiccati -> negli animali e' di norma non applicabile.
_CAT_VEG = {"ortaggi", "funghi", "fermentati"}


def _provenienza(raw, comp, cat):
    """Distingue (il punto del revisore) misurato / misurato_zero / non_riportato /
    non_applicabile per un componente, dal grezzo + biochimica della categoria."""
    raw = (raw or "").strip()
    if raw == "0":
        return "misurato_zero"
    if raw != "":
        return "misurato"
    if comp == "imp":
        return "non_applicabile" if cat in _CAT_VEG else "non_riportato"
    return "non_applicabile" if cat in ("mare", "carne") else "non_riportato"


def _deriva(row):
    """Da misure Umami Information Center -> asse umami 0-10 (via EUC + curva log).
    Ritorna None se non c'e' glutammato (niente umami derivabile dalla fonte).
    Allega la PROVENIENZA per componente e una CONFIDENZA: 'bassa' se un nucleotide
    rilevante e' solo 'non_riportato' (non misurato), 'media' altrimenti. Mai 'alta'
    (quella e' riservata alla misura al banco)."""
    if not row or (row.get("glu") or 0.0) <= 0.0:
        return None
    euc = _calc_euc(row.get("glu"), row.get("imp"), row.get("gmp"))
    if euc <= 0:
        return None
    val = _interp(math.log10(euc), _UMAMI_LOG)
    cat = row.get("categoria", "")
    imp_prov = _provenienza(row.get("imp_raw"), "imp", cat)
    gmp_prov = _provenienza(row.get("gmp_raw"), "gmp", cat)
    # confidenza: bassa se un nucleotide che POTREBBE esserci non e' stato riportato
    confidenza = "bassa" if ("non_riportato" in (imp_prov, gmp_prov)) else "media"
    return {
        "val": val,
        "euc": round(euc, 3),
        "confidenza": confidenza,
        "grezzo": {
            "glutammato_mg": row.get("glu"), "glutammato_raw": row.get("glu_raw"),
            "inosinato_mg": row.get("imp"), "inosinato_raw": row.get("imp_raw"),
            "inosinato_provenienza": imp_prov,
            "guanilato_mg": row.get("gmp"), "guanilato_raw": row.get("gmp_raw"),
            "guanilato_provenienza": gmp_prov,
            "euc_g_eq": round(euc, 3),
        },
    }


# Corrispondenze AFFINI: nomi che NON sono il prodotto della fonte ma un prodotto
# imparentato. Il valore e' una stima da prodotto affine, con confidenza abbassata e
# fonte dichiarata come tale (il punto del revisore: non spacciare garum/colatura per
# nam pla misurata). Chiave = nome nodo; valore = (prodotto-affine, confidenza, nota).
_AFFINE = {
    "garum": ("salsa di pesce / nam pla",
              "Prodotto fermentato affine (non la stessa cosa). Stima da prodotto affine."),
    "colatura": ("salsa di pesce / nam pla",
                 "Colatura di alici: salsa di pesce affine da alici. Stima da prodotto affine."),
    "colatura di alici": ("salsa di pesce / nam pla",
                          "Salsa di pesce affine da alici. Stima da prodotto affine."),
}


# --- Match CURATO nome italiano del nodo -> chiave della tabella umami (verificato
#     a mano: solo cibi la cui forma corrisponde davvero al dato della fonte) ---
_MATCH = {
    # mare
    "nori": "nori", "wakame": "wakame", "katsuobushi": "katsuobushi",
    "kombu": "kombu", "alga kombu": "kombu",
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
    "niboshi": "niboshi",
    # ortaggi
    "pomodori secchi": "pomodori_secchi", "pomodoro secco": "pomodori_secchi",
    "piselli": "piselli", "aglio": "aglio", "mais": "mais",
    "soia": "soia", "fave": "fave", "fava": "fave",
    "patata": "patata", "patata dolce": "patata_dolce",
    "spinaci": "spinaci", "carota": "carota", "asparago": "asparago",
    "asparagi": "asparago", "cavolo": "cavolo", "cipolla": "cipolla",
    "cipollotto": "cipollotto", "broccolo": "broccolo", "sedano": "sedano",
    "zenzero": "zenzero", "daikon": "daikon",
    "cavolo cinese": "cavolo_cinese", "germogli di bambù": "germogli_bambu",
    "radice di loto": "radice_loto",
    # fermentati
    "natto": "natto", "colatura di alici": "colatura", "colatura": "colatura",
    "garum": "colatura", "salsa di pesce": "colatura",
    "salsa di ostriche": "salsa_ostriche", "salsa di soia": "salsa_soia",
    "miso": "miso",
    # funghi
    "shiitake": "shiitake", "shiitake secco": "shiitake_secco",
    "shimeji": "shimeji", "enoki": "enoki",
    "champignon": "champignon", "tartufo": "tartufo",
    # NB: "funghi" (generico) NON mappato: in cucina pende verso i secchi/porcini
    # (umami-ricchi), non il champignon fresco. Mapparlo lo declasserebbe. Caso a mano.
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
    # &correggi=1: RECUPERA i valori umami prodotti dal vecchio metodo-macchina
    # (derivato/corretto/derivato-da-generico e qualsiasi stato NON del banco) e li
    # ricalcola col modello di sinergia EUC. Serve perche' il vecchio umami a solo
    # glutammato e' cieco su pesce/carne (guidati dall'inosinato). MAI tocca i valori
    # del banco: 'verificato' e 'misurato' restano sacri. Default: NON corregge niente.
    correggi = request.args.get("correggi") == "1"
    _BENCH = ("verificato", "misurato")
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

        campione, scritti, reclamati, recuperabili, nuovi = [], 0, 0, 0, 0
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

            # fill-only: scrivibile se assente o 'stimato'. Con &correggi=1 RECUPERA
            # anche i valori-macchina vecchi (qualsiasi stato NON del banco: derivato,
            # corretto, derivato-da-generico...). I valori del banco (_BENCH) sono sacri.
            e_reclamo = False
            scrivibile = stato_vecchio in (None, "stimato")
            if not scrivibile and correggi and stato_vecchio not in _BENCH:
                scrivibile = True
                e_reclamo = True
            if not scrivibile:
                saltati_protetto_stato += 1
            elif e_reclamo:
                recuperabili += 1
            else:
                nuovi += 1

            # corrispondenza affine (garum/colatura ≠ nam pla): confidenza abbassata,
            # fonte dichiarata come stima-da-affine (punto del revisore).
            aff = _AFFINE.get((nome_it or "").lower())
            confidenza = "bassa" if aff else der.get("confidenza", "media")

            riga = {
                "nodo": nid, "nome": nome_nodo, "chiave_fonte": chiave,
                "nome_fonte": src.get("nome", ""), "categoria": src.get("categoria", ""),
                "vecchio": vecchio, "stato_vecchio": stato_vecchio or "assente",
                "nuovo_derivato": der["val"], "euc": der["euc"],
                "delta": (round(der["val"] - vecchio, 1) if isinstance(vecchio, (int, float)) else None),
                "confidenza": confidenza,
                "corrispondenza": ("affine" if aff else "diretta"),
                "affine_di": (aff[0] if aff else None),
                "imp_prov": der["grezzo"]["inosinato_provenienza"],
                "gmp_prov": der["grezzo"]["guanilato_provenienza"],
                "grezzo": der["grezzo"], "scrivibile": scrivibile, "reclamo": e_reclamo,
            }
            if len(campione) < 80:
                campione.append(riga)

            if esegui and scrivibile:
                cur.execute("INSERT INTO _backup_umami_derivati (id, data_old) VALUES (%s, %s)",
                            (nid, json.dumps(dd, ensure_ascii=False)))
                prop["umami"] = der["val"]
                base_nota = ("umami ricalcolato col modello di sinergia (EUC): il valore precedente "
                             "ignorava i ribonucleotidi. " if e_reclamo else
                             "derivato da letteratura (glutammato + ribonucleotidi, EUC Yamaguchi). ")
                m = {
                    "stato": ("corretto" if e_reclamo else "derivato"),
                    "fonte": (f"{FONTE} — stima da prodotto affine: {aff[0]}" if aff else FONTE),
                    "fonte_url": FONTE_URL, "formula": FORMULA_VER,
                    "confidenza": confidenza, "corrispondenza": ("affine" if aff else "diretta"),
                    "grezzo": der["grezzo"],
                    "nota": base_nota + (aff[1] + " " if aff else "") + "Non misurato al banco.",
                }
                meta["umami"] = m
                if e_reclamo:
                    reclamati += 1
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
            "saltati_banco_protetti": saltati_protetto_stato,
            "correggi": correggi,
            "nuovi_da_scrivere": nuovi,
            "recuperabili_da_ricalcolare": recuperabili,
            "scritti": scritti if esegui else 0,
            "nota": ("DRY RUN: nessun dato modificato. &esegui=1 per scrivere; "
                     "&correggi=1 per ricalcolare anche i valori-macchina vecchi "
                     "(mai verificato/misurato del banco)."
                     if not esegui else
                     "ESEGUITO: fill-only in transazione; backup in _backup_umami_derivati; "
                     "asse umami da letteratura (Umami Information Center). Con &correggi=1 "
                     "ricalcolati i valori-macchina vecchi; mai toccati verificato/misurato."),
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


@bp_umami.route("/admin/ripristina-umami", methods=["GET", "POST"])
def ripristina_umami():
    """PROVA DI ROLLBACK dell'asse umami dal backup _backup_umami_derivati.
    SICUREZZA: la lettura (DRY-RUN) e' in GET; la SCRITTURA (&esegui=1) e' consentita
    SOLO in POST, cosi' un'operazione distruttiva non e' attivabile visitando un link
    (niente GET distruttivo, niente attivazione accidentale). Autorizzazione via
    ADMIN_SECRET lato server. Ogni ripristino salva prima lo stato corrente.
    DRY-RUN di default (?s=SECRET): mostra, per ogni nodo con backup, il valore
    umami ATTUALE e quello a cui tornerebbe (dal backup), SENZA scrivere.
    Con &esegui=1 (in POST) ripristina SOLO i campi umami (proprieta.umami +
    proprieta_meta.umami) dallo stato di backup — chirurgico, non tocca il resto del
    nodo. &nodo=<id> per un solo nodo (lotto di test); &limite per un blocco.
    Usa il backup PIU' VECCHIO per id (stato originale pre-intervento)."""
    import psycopg2
    sec = os.environ.get("ADMIN_SECRET")
    if not sec or request.args.get("s") != sec:
        return jsonify({"errore": "non autorizzato"}), 403
    dburl = os.environ.get("DATABASE_URL")
    if not dburl:
        return jsonify({"errore": "DATABASE_URL non disponibile"}), 400

    esegui = request.args.get("esegui") == "1"
    # scrittura distruttiva: solo POST. In GET resta sempre DRY-RUN (no GET distruttivo).
    if esegui and request.method != "POST":
        return jsonify({"errore": "scrittura consentita solo via POST",
                        "come": "ripeti la richiesta in POST (stesso URL con &esegui=1). "
                                "In GET l'endpoint esegue sempre e solo il DRY-RUN."}), 405
    esegui = esegui and request.method == "POST"
    solo_nodo = (request.args.get("nodo") or "").strip()
    try:
        limite = int(request.args.get("limite", "0"))
    except ValueError:
        limite = 0

    def _um(dd):
        """Estrae (valore, meta) di umami da un dict-nodo, None se assente."""
        prop = (dd or {}).get("proprieta", {}) or {}
        meta = (dd or {}).get("proprieta_meta", {}) or {}
        return prop.get("umami"), meta.get("umami")

    conn = None
    try:
        conn = psycopg2.connect(dburl)
        conn.autocommit = False
        cur = conn.cursor()
        # esiste il backup?
        cur.execute("SELECT to_regclass('_backup_umami_derivati')")
        if cur.fetchone()[0] is None:
            cur.close(); conn.close()
            return jsonify({"errore": "nessun backup: _backup_umami_derivati non esiste"}), 404

        # backup PIU' VECCHIO per id (stato originale pre-intervento)
        q = """SELECT DISTINCT ON (id) id, data_old, ts
               FROM _backup_umami_derivati {w}
               ORDER BY id, ts ASC"""
        if solo_nodo:
            cur.execute(q.format(w="WHERE id=%s"), (solo_nodo,))
        else:
            cur.execute(q.format(w=""))
        backup = cur.fetchall()
        if limite > 0:
            backup = backup[:limite]

        if esegui:
            cur.execute("""CREATE TABLE IF NOT EXISTS _backup_umami_ripristino
                           (id TEXT, data_old JSONB, ts TIMESTAMPTZ DEFAULT NOW())""")

        campione, ripristinati, invariati, nodo_sparito = [], 0, 0, 0
        for nid, data_old, ts in backup:
            dd_old = data_old if isinstance(data_old, dict) else (json.loads(data_old) if data_old else {})
            val_old, meta_old = _um(dd_old)   # stato umami PRIMA dell'intervento

            cur.execute("SELECT data FROM nodes WHERE id=%s", (nid,))
            r = cur.fetchone()
            if not r:
                nodo_sparito += 1
                continue
            dd_cur = r[0] if isinstance(r[0], dict) else (json.loads(r[0]) if r[0] else {})
            val_cur, _ = _um(dd_cur)

            riga = {"nodo": nid, "umami_attuale": val_cur, "ripristina_a": val_old,
                    "backup_ts": str(ts)}
            if len(campione) < 80:
                campione.append(riga)

            if esegui:
                # salva lo stato corrente (ripristino reversibile)
                cur.execute("INSERT INTO _backup_umami_ripristino (id, data_old) VALUES (%s,%s)",
                            (nid, json.dumps(dd_cur, ensure_ascii=False)))
                prop = dict(dd_cur.get("proprieta", {}) or {})
                meta = dict(dd_cur.get("proprieta_meta", {}) or {})
                if val_old is None:
                    prop.pop("umami", None)      # prima non c'era -> si rimuove
                else:
                    prop["umami"] = val_old
                if meta_old is None:
                    meta.pop("umami", None)
                else:
                    meta["umami"] = meta_old
                dd_cur["proprieta"] = prop
                dd_cur["proprieta_meta"] = meta
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (json.dumps(dd_cur, ensure_ascii=False), nid))
                ripristinati += 1

        if esegui:
            conn.commit()
        cur.close(); conn.close()
        return jsonify({
            "dry_run": (not esegui),
            "backup_trovati": len(backup),
            "nodi_spariti": nodo_sparito,
            "ripristinati": ripristinati if esegui else 0,
            "nota": ("DRY RUN: nessuna modifica. Mostra umami attuale vs valore di backup. "
                     "&esegui=1 ripristina i soli campi umami; &nodo=<id> per un lotto di test."
                     if not esegui else
                     "ESEGUITO: ripristinati i soli campi umami dallo stato di backup piu' vecchio; "
                     "stato pre-ripristino salvato in _backup_umami_ripristino (reversibile)."),
            "campione": campione,
        })
    except Exception as e:
        try:
            if conn:
                conn.rollback(); conn.close()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:200]}), 500
