# -*- coding: utf-8 -*-
# ============================================================
# DEDUP NODI — migrazione di pulizia del grafo (nodi duplicati legacy).
#
# ATTENZIONE (lezione della dry-run del 25/10): il merge AUTOMATICO per nome e'
# PERICOLOSO. Il grafo ha decine di omonimi italiani che sono entita' botaniche
# DIVERSE (es. "valeriana" = Valeriana officinalis vs songino; "foglie di limone"
# = Litsea/Lindera/Backhousia). I nodi ahn_ non hanno il campo specie, quindi un
# controllo per-specie non li protegge. Percio' QUI non si fonde per nome.
#
# Due operazioni, DRY-RUN di default (scrivono solo con &esegui=1, in transazione):
#   1) NORMALIZZA REGIONI: grafie abbreviate NOTE -> forma piena. Esplicite.
#   2) FONDE SOLO i gruppi in MERGE_ALLOWLIST: coppie verificate A MANO, stessa
#      entita'. Nessun altro nodo viene toccato. Per ogni voce: archi degli
#      assorbiti ri-puntati sul canonico (ON CONFLICT DO NOTHING), self-loop
#      rimossi, assorbiti cancellati.
# La dry-run mostra anche, SOLO IN LETTURA, quanti gruppi-omonimi restano fuori
# dall'allowlist ("da rivedere"), senza toccarli.
#
# Uso:  /admin/dedup-nodi?s=SECRET            (anteprima, NON scrive)
#       /admin/dedup-nodi?s=SECRET&esegui=1   (scrive, in transazione)
# ============================================================
import json
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_dedup = Blueprint("admin_dedup", __name__)

# normalizzazione regioni: solo grafie abbreviate NOTE (chiave = lower)
REGION_CANON = {
    "trentino-a.a.": "Trentino-Alto Adige",
    "trentino a.a.": "Trentino-Alto Adige",
    "friuli": "Friuli-Venezia Giulia",
}

# FUSIONI VERIFICATE A MANO — solo entita' identiche, controllate una a una.
# Formato: {"canonico": id_che_resta, "assorbiti": [id_da_fondere...], "perche": "..."}
# Si aggiunge una voce SOLO dopo aver confermato che e' davvero lo stesso ingrediente.
MERGE_ALLOWLIST = [
    {"canonico": "ing-speck-alto-adige-igp",
     "assorbiti": ["ing-it-speck-alto-adige"],
     "perche": "stesso prodotto (Speck Alto Adige IGP) su due nodi; chiude la regione-fantasma Trentino-A.A."},

    # ---- Batch 1 (2026-10-28): doppioni IT/EN verificati a mano dall'hard-test robustezza.
    # Fonte: dry-run /v1/criteri/dedup-nodi (55 coppie). Qui SOLO le 36 in cui ahn_/ai_ e ing-
    # sono con certezza lo STESSO ingrediente (traduzione/sinonimo/grafia). Escluse a monte le
    # specie-ambigue: valeriana (officinalis vs songino), sgombro (Scomber vs Trachurus),
    # issopo (Hyssopus vs Agastache), mela cotogna (Cydonia vs Pseudocydonia), orata (seabream
    # diverso), citronella (lemongrass vs citronella), timo zygis, origano floribundum, curcuma
    # aromatica, cherimoya reticulata, passiflora mollissima, ecc. — restano "da rivedere".
    {"canonico": "ahn_laurel_leaf", "assorbiti": ["ahn_bay", "ahn_bay_laurel"], "perche": "alloro — Laurus nobilis, nomi EN/latino"},
    {"canonico": "ahn_pineapple", "assorbiti": ["ahn_ananas_sativus"], "perche": "ananas — Ananas comosus, nome latino"},
    {"canonico": "ai_barbabietola", "assorbiti": ["ahn_beet_root"], "perche": "barbabietola — beet root IT/EN"},
    {"canonico": "ahn_basil", "assorbiti": ["ahn_sweet_basil"], "perche": "basilico — sweet basil (Ocimum basilicum); hoary basil ESCLUSO (specie diversa)"},
    {"canonico": "ing-bergamotto", "assorbiti": ["ahn_bergamot"], "perche": "bergamotto — Citrus bergamia IT/EN"},
    {"canonico": "ahn_cherry", "assorbiti": ["ahn_pinus_avium_fruit"], "perche": "ciliegia — Prunus avium (id con refuso 'pinus')"},
    {"canonico": "ing-cime-di-rapa", "assorbiti": ["ai_cime_di_rapa"], "perche": "cime di rapa — stesso nodo IT duplicato"},
    {"canonico": "ahn_eucalyptus_citridora", "assorbiti": ["ahn_eucalyptus_citriodora"], "perche": "eucalipto limone — grafia citridora/citriodora"},
    {"canonico": "ahn_snap_bean", "assorbiti": ["ahn_french_bean"], "perche": "fagiolino — Phaseolus vulgaris, snap/french bean"},
    {"canonico": "ahn_red_kidney_bean", "assorbiti": ["ahn_kidney_bean", "ahn_red_bean"], "perche": "fagiolo rosso — kidney/red bean"},
    {"canonico": "ing-farina-di-segale", "assorbiti": ["ahn_rye_flour"], "perche": "farina di segale — rye flour IT/EN"},
    {"canonico": "ai_fava_tonka", "assorbiti": ["ahn_tonka_bean_seed"], "perche": "fava tonka — Dipteryx odorata IT/EN"},
    {"canonico": "ahn_jasmine", "assorbiti": ["ahn_jasminum_grandiflorum"], "perche": "gelsomino — Jasminum grandiflorum"},
    {"canonico": "ing-ginepro", "assorbiti": ["ai_ginepro"], "perche": "ginepro — stesso nodo IT duplicato; juniperus_sabina ESCLUSO (specie diversa)"},
    {"canonico": "ing-grani-del-paradiso", "assorbiti": ["ai_grani_del_paradiso"], "perche": "grani del paradiso — stesso nodo IT duplicato"},
    {"canonico": "ahn_helichrysum_italicum", "assorbiti": ["ahn_helichrysum_angustifolium"], "perche": "immortelle — H. italicum = angustifolium (sinonimi)"},
    {"canonico": "ahn_lovage", "assorbiti": ["ahn_lovage_leaf"], "perche": "levistico — Levisticum officinale, foglia stessa pianta"},
    {"canonico": "ahn_kaffir_lime", "assorbiti": ["ai_lime_kaffir"], "perche": "lime kaffir — stesso ingrediente IT/EN"},
    {"canonico": "ahn_lemon_balm", "assorbiti": ["ahn_balm"], "perche": "melissa — Melissa officinalis, lemon balm/balm"},
    {"canonico": "ahn_japanese_peppermint", "assorbiti": ["ahn_japanese_mint"], "perche": "menta giapponese — Mentha arvensis; agastache_rugosa ESCLUSO"},
    {"canonico": "ahn_peppermint", "assorbiti": ["ahn_american_peppermint"], "perche": "menta piperita — Mentha x piperita"},
    {"canonico": "ahn_scotch_spearmint", "assorbiti": ["ahn_mentha_viridis"], "perche": "menta verde — Mentha spicata/viridis"},
    {"canonico": "ing-mirtillo-rosso", "assorbiti": ["ahn_european_cranberry", "ahn_cranberry"], "perche": "mirtillo rosso — cranberry; consolida la chimica sul nodo IT e toglie il duplicato gonfio che inquinava le classifiche agrumi"},
    {"canonico": "ing-pepe-di-sichuan", "assorbiti": ["ahn_zanthoxylum_piperitum"], "perche": "pepe di sichuan — Zanthoxylum piperitum"},
    {"canonico": "ahn_long_pepper", "assorbiti": ["ai_pepe_lungo"], "perche": "pepe lungo — Piper longum; piper_officinarum ESCLUSO (specie diversa)"},
    {"canonico": "ahn_bell_pepper", "assorbiti": ["ahn_capsicum_annuum"], "perche": "peperone — Capsicum annuum"},
    {"canonico": "ahn_radish", "assorbiti": ["ahn_rafanus_sativus_root"], "perche": "ravanello — Raphanus sativus"},
    {"canonico": "ing-rosmarino", "assorbiti": ["ahn_rosemary"], "perche": "rosmarino — Salvia rosmarinus; consolida chimica + archi sul nodo IT"},
    {"canonico": "ing-salmone", "assorbiti": ["ahn_salmon"], "perche": "salmone — salmon IT/EN"},
    {"canonico": "ing-salvia", "assorbiti": ["ahn_sage"], "perche": "salvia — Salvia officinalis; consolida chimica sul nodo IT"},
    {"canonico": "ahn_clary_sage", "assorbiti": ["ahn_bulgarian_clary_sage"], "perche": "salvia sclarea — Salvia sclarea"},
    {"canonico": "ahn_elderberry", "assorbiti": ["ahn_elderberry_fruit"], "perche": "sambuco — Sambucus nigra, frutto stessa pianta"},
    {"canonico": "ai_sedano_rapa", "assorbiti": ["ahn_celery_root"], "perche": "sedano rapa — celeriac IT/EN"},
    {"canonico": "ing-sudachi", "assorbiti": ["ai_sudachi"], "perche": "sudachi — stesso nodo IT duplicato"},
    {"canonico": "ahn_tea", "assorbiti": ["ahn_brewed_tea"], "perche": "tè — Camellia sinensis, tea/brewed tea"},
    {"canonico": "ahn_malt_whiskey", "assorbiti": ["ahn_scotch_whiskey"], "perche": "whisky scozzese — malt/scotch whiskey"},

    # ---- Batch 2 (2026-10-29): orfani creati dall'import pasticceria. Il resolver risolve
    # sesamo/arachidi su ahn_ (via _ALIAS) ma l'importer li ha creati come ing- nuovi: i composti
    # proprietari (firma + provenienza) erano su nodi non raggiungibili. Fondo gli ing- orfani sui
    # nodi ahn_ ricchi e canonici (la query li raggiunge gia'). Verificato: stesso ingrediente.
    {"canonico": "ahn_sesame_seed", "assorbiti": ["ing-sesamo"], "perche": "sesamo — sesame seed IT/EN; migra la firma proprietaria (2-furfuriltiolo ecc.) sul nodo ahn ricco (18 comp) che il resolver raggiunge"},
    {"canonico": "ahn_peanut", "assorbiti": ["ing-arachidi"], "perche": "arachidi — peanut IT/EN; migra la firma proprietaria (2-acetil-1-pirrolina ecc.) sul nodo ahn ricco (94 comp) che il resolver raggiunge"},

    # ---- Batch 3 (2026-11-01): verificate live una a una (audit fusione nodi). SOLO le sicure.
    # friarielli: canonico = il nodo-NOME 'Friarielli' (tiene il nome campano di Michele), assorbe
    # il generico ing-cime-di-rapa (che aveva amaro + abbinamenti). I 3 riferimenti hardcoded a
    # ing-cime-di-rapa (criteri._OVERRIDE x2, importa_composti._FORZA_NODO x1) sono ripuntati a
    # ing-it-friarielli nella STESSA PR, quindi la cancellazione non rompe il resolver.
    {"canonico": "ing-it-friarielli", "assorbiti": ["ing-cime-di-rapa"], "perche": "friarielli = cime di rapa (Brassica rapa), nome campano; tiene il nome 'friarielli', assorbe i dati del generico (amaro, abbinamenti)"},
    {"canonico": "ai_anice_stellato", "assorbiti": ["ahn_star_anise", "ahn_chinese_star_anise"], "perche": "anice stellato — tutti Illicium verum (star anise = chinese star anise); verificato live. NON japanese star anise (tossico, assente). 0 riferimenti nel codice"},
    {"canonico": "ahn_passion_fruit", "assorbiti": ["ahn_passiflora_edulis"], "perche": "frutto della passione — Passiflora edulis; verificato live. passiflora_mollissima (curuba) ESCLUSO (specie diversa). 0 riferimenti nel codice"},
]


def _parse(v):
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v) if v else {}
    except Exception:
        return {}


@bp_dedup.route("/admin/dedup-nodi")
def dedup_nodi():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # ---------- 1) normalizzazione regioni ----------
        regioni_norm = []
        for abbr, canon in REGION_CANON.items():
            cur.execute("SELECT id, name FROM nodes WHERE lower(data->>'regione')=%s", (abbr,))
            for nid, name in cur.fetchall():
                regioni_norm.append({"id": nid, "nome": name, "da": abbr, "a": canon})
                if esegui:
                    cur.execute(
                        "UPDATE nodes SET data = jsonb_set(COALESCE(data,'{}'::jsonb),'{regione}', to_jsonb(%s::text)) WHERE id=%s",
                        (canon, nid))

        # ---------- 2) fusioni da allowlist (SOLO queste) ----------
        def archi(nid):
            cur.execute("SELECT COUNT(*) FROM edges WHERE from_id=%s OR to_id=%s", (nid, nid))
            return cur.fetchone()[0]
        def esiste(nid):
            cur.execute("SELECT 1 FROM nodes WHERE id=%s", (nid,))
            return cur.fetchone() is not None

        fusioni = []
        for voce in MERGE_ALLOWLIST:
            c = voce["canonico"]
            rep = {"canonico": c, "perche": voce["perche"], "assorbiti": [], "saltati": []}
            if not esiste(c):
                rep["saltati"].append({"id": c, "motivo": "canonico inesistente"})
                fusioni.append(rep); continue
            for dup in voce["assorbiti"]:
                if not esiste(dup):
                    rep["saltati"].append({"id": dup, "motivo": "assorbito inesistente (gia' fuso?)"})
                    continue
                rep["assorbiti"].append({"id": dup, "archi": archi(dup)})
                if esegui:
                    cur.execute("""INSERT INTO edges (from_id,to_id,relation,data)
                                   SELECT %s, to_id, relation, data FROM edges WHERE from_id=%s
                                   ON CONFLICT (from_id,to_id,relation) DO NOTHING""", (c, dup))
                    cur.execute("DELETE FROM edges WHERE from_id=%s", (dup,))
                    cur.execute("""INSERT INTO edges (from_id,to_id,relation,data)
                                   SELECT from_id, %s, relation, data FROM edges WHERE to_id=%s
                                   ON CONFLICT (from_id,to_id,relation) DO NOTHING""", (c, dup))
                    cur.execute("DELETE FROM edges WHERE to_id=%s", (dup,))
                    cur.execute("""UPDATE nodes SET data =
                                     COALESCE((SELECT data FROM nodes WHERE id=%s),'{}'::jsonb)
                                     || COALESCE(data,'{}'::jsonb) WHERE id=%s""", (dup, c))
                    cur.execute("DELETE FROM nodes WHERE id=%s", (dup,))
            if esegui:
                cur.execute("DELETE FROM edges WHERE from_id=to_id AND from_id=%s", (c,))
            fusioni.append(rep)

        # ---------- lettura informativa: quanti omonimi restano fuori (NON toccati) ----------
        cur.execute("""SELECT lower(trim(name)) k, COUNT(*) n
                       FROM nodes WHERE type IN ('Ingrediente','Prodotto') AND name IS NOT NULL
                       GROUP BY 1 HAVING COUNT(*) > 1 ORDER BY n DESC""")
        omonimi = cur.fetchall()
        in_allow = {a for v in MERGE_ALLOWLIST for a in (v["assorbiti"] + [v["canonico"]])}

        if esegui:
            conn.commit()

        return jsonify({
            "modo": "SCRITTO" if esegui else "DRY-RUN (anteprima, aggiungi &esegui=1 per scrivere)",
            "1_regioni_normalizzate": {"totale": len(regioni_norm), "dettaglio": regioni_norm},
            "2_fusioni_allowlist": {"totale": len(fusioni), "dettaglio": fusioni},
            "3_omonimi_da_rivedere_NON_toccati": {
                "totale_gruppi": len(omonimi),
                "nota": "Gruppi di nodi con lo stesso nome ancora nel grafo. NON fusi: molti sono "
                        "entita' diverse con lo stesso nome italiano (es. valeriana vs songino). "
                        "Vanno aggiunti a MERGE_ALLOWLIST uno a uno, solo dopo verifica botanica.",
                "primi_20": [{"nome": k, "nodi": n} for k, n in omonimi[:20]],
            },
        })
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        import traceback
        return jsonify({"errore": str(e)[:200], "trace": traceback.format_exc()[:600]}), 500
    finally:
        cur.close()
        _release_conn(conn)
