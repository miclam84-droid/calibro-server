# -*- coding: utf-8 -*-
# ============================================================
# DEDUP NODI — migrazione di pulizia del grafo (nodi duplicati legacy).
#
# Due operazioni, entrambe in DRY-RUN di default (scrivono solo con &esegui=1):
#   1) NORMALIZZA REGIONI: porta le grafie abbreviate note alla forma piena
#      (Trentino-A.A. -> Trentino-Alto Adige, Friuli -> Friuli-Venezia Giulia).
#      Solo queste due, esplicite: niente euristiche sui nomi regione.
#   2) FONDE DOPPIONI: nodi Ingrediente/Prodotto con STESSO nome (lower, trim).
#      SICUREZZA: fonde un gruppo solo se le specie dichiarate sono compatibili
#      (stessa specie, o specie assente). Se due membri hanno specie DIVERSE
#      (es. "mirtillo rosso" = Vaccinium macrocarpon vs vitis-idaea) il gruppo
#      viene SEGNALATO e NON toccato. Il canonico e' il nodo con piu' archi
#      (tiebreak: non-ahn/non-ai, poi id piu' corto). Gli archi dei doppioni
#      vengono ri-puntati sul canonico (ON CONFLICT DO NOTHING -> niente doppi),
#      i self-loop rimossi, i nodi assorbiti cancellati. Tutto in UNA transazione.
#
# Sicurezza: _admin_ok, dry-run di default, max 6 membri per gruppo (sanity),
# solo type IN ('Ingrediente','Prodotto'). Rollback su qualsiasi errore.
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

MAX_MEMBRI = 6  # sanity: non fondere gruppi anomali


def _spec(d):
    return (d.get("specie") or "").strip().lower() if isinstance(d, dict) else ""


def _parse(v):
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v) if v else {}
    except Exception:
        return {}


def _scegli_canonico(membri):
    # membri: list di dict {id, archi, specie, data}. Canonico = piu' archi;
    # tiebreak: penalizza id ahn_/ai_ (dato Ahn da ritirare), poi id piu' corto, poi alfabetico.
    def rank(m):
        legacy = m["id"].startswith("ahn_") or m["id"].startswith("ai_")
        return (-m["archi"], 1 if legacy else 0, len(m["id"]), m["id"])
    return sorted(membri, key=rank)[0]


@bp_dedup.route("/admin/dedup-nodi")
def dedup_nodi():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # ---------- raccolta: tutti i nodi Ingrediente/Prodotto con conteggio archi ----------
        cur.execute("""
            SELECT n.id, n.name, n.data,
                   (SELECT COUNT(*) FROM edges e WHERE e.from_id=n.id OR e.to_id=n.id) AS archi
            FROM nodes n
            WHERE n.type IN ('Ingrediente','Prodotto')
        """)
        righe = cur.fetchall()
        per_nome = {}
        for nid, name, data, archi in righe:
            k = (name or "").strip().lower()
            if not k:
                continue
            per_nome.setdefault(k, []).append(
                {"id": nid, "nome": name, "data": _parse(data), "archi": archi})

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

        # ---------- 2) dedup per nome ----------
        gruppi_merge = []
        gruppi_flag = []
        for k, membri in per_nome.items():
            if len(membri) < 2:
                continue
            if len(membri) > MAX_MEMBRI:
                gruppi_flag.append({"nome": membri[0]["nome"], "motivo": f"gruppo anomalo ({len(membri)} nodi)",
                                    "nodi": [m["id"] for m in membri]})
                continue
            specie = {_spec(m["data"]) for m in membri if _spec(m["data"])}
            if len(specie) > 1:
                gruppi_flag.append({"nome": membri[0]["nome"], "motivo": "specie diverse (non fuso)",
                                    "nodi": [{"id": m["id"], "specie": _spec(m["data"])} for m in membri]})
                continue
            canon = _scegli_canonico(membri)
            assorbiti = [m for m in membri if m["id"] != canon["id"]]
            gruppi_merge.append({
                "nome": membri[0]["nome"],
                "canonico": {"id": canon["id"], "archi": canon["archi"]},
                "assorbiti": [{"id": m["id"], "archi": m["archi"]} for m in assorbiti],
            })
            if esegui:
                for m in assorbiti:
                    dup = m["id"]; c = canon["id"]
                    # out-edges dup -> canon (niente doppi)
                    cur.execute("""INSERT INTO edges (from_id,to_id,relation,data)
                                   SELECT %s, to_id, relation, data FROM edges WHERE from_id=%s
                                   ON CONFLICT (from_id,to_id,relation) DO NOTHING""", (c, dup))
                    cur.execute("DELETE FROM edges WHERE from_id=%s", (dup,))
                    # in-edges dup -> canon
                    cur.execute("""INSERT INTO edges (from_id,to_id,relation,data)
                                   SELECT from_id, %s, relation, data FROM edges WHERE to_id=%s
                                   ON CONFLICT (from_id,to_id,relation) DO NOTHING""", (c, dup))
                    cur.execute("DELETE FROM edges WHERE to_id=%s", (dup,))
                    # il canonico eredita i campi che non ha (il canonico vince sui conflitti)
                    cur.execute("""UPDATE nodes SET data =
                                     COALESCE((SELECT data FROM nodes WHERE id=%s),'{}'::jsonb)
                                     || COALESCE(data,'{}'::jsonb)
                                   WHERE id=%s""", (dup, c))
                    # cancella il nodo assorbito
                    cur.execute("DELETE FROM nodes WHERE id=%s", (dup,))
                # togli eventuali self-loop creati
                cur.execute("DELETE FROM edges WHERE from_id=to_id AND from_id=%s", (canon["id"],))

        if esegui:
            conn.commit()

        return jsonify({
            "modo": "SCRITTO" if esegui else "DRY-RUN (anteprima, aggiungi &esegui=1 per scrivere)",
            "1_regioni_normalizzate": {"totale": len(regioni_norm), "dettaglio": regioni_norm},
            "2_gruppi_da_fondere": {"totale": len(gruppi_merge), "dettaglio": gruppi_merge},
            "2_gruppi_SEGNALATI_non_fusi": {"totale": len(gruppi_flag), "dettaglio": gruppi_flag},
            "nota": "I gruppi SEGNALATI (specie diverse, es. mirtillo rosso) NON sono stati toccati: "
                    "vanno rinominati a mano, non fusi.",
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
