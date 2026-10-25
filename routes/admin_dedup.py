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
