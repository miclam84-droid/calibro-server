# ============================================================
# COPERTURA-PROPRIETARIA — diagnostico read-only (NON scrive nulla).
# Risponde alla domanda del "cancello 1": quali nodi-ingrediente che l'app
# SERVE (hanno composti, quindi entrano nel pairing) hanno ancora SOLO dati
# Ahn/ai e nessun arco proprietario (origine=matter_dataset)?
#
# Un nodo e' "coperto dal proprietario" se ha almeno un arco contiene_composto
# con data->>'origine' = 'matter_dataset' (lo scrive l'import del dataset).
# Gli "scoperti" sono il bersaglio delle prossime ondate: ingredienti gia'
# serviti dall'app ma ancora dipendenti da Ahn.
#
# Uso:  /admin/copertura-proprietaria?s=SECRET
#       &dominio=bar|cucina   (filtro opzionale)
#       &min_composti=3       (solo nodi con almeno N composti; default 1)
# ============================================================
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_copertura_proprietaria = Blueprint("copertura_proprietaria", __name__)


@bp_copertura_proprietaria.route("/admin/copertura-proprietaria")
def copertura_proprietaria():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    dominio = (request.args.get("dominio") or "").strip().lower()
    try:
        min_composti = int(request.args.get("min_composti", "1"))
    except ValueError:
        min_composti = 1

    conn = _get_conn()
    try:
        cur = conn.cursor()
        # universo servito: nodi Ingrediente/Prodotto con >= min_composti archi contiene_composto.
        # per ciascuno: n composti totali, n composti proprietari (origine=matter_dataset).
        cur.execute("""
            SELECT n.id, n.name, COALESCE(n.domain,''),
                   COUNT(e.to_id) AS n_comp,
                   COUNT(e.to_id) FILTER (WHERE e.data->>'origine' = 'matter_dataset') AS n_prop
            FROM nodes n
            JOIN edges e ON e.from_id = n.id AND e.relation = 'contiene_composto'
            WHERE n.type IN ('Ingrediente','Prodotto')
            GROUP BY n.id, n.name, n.domain
            HAVING COUNT(e.to_id) >= %s
            ORDER BY n_comp DESC, n.name ASC
        """, (min_composti,))
        righe = cur.fetchall()

        serviti, coperti, scoperti = [], [], []
        for _id, name, dom, n_comp, n_prop in righe:
            if dominio and dom.lower() != dominio:
                continue
            rec = {"id": _id, "nome": name, "dominio": dom, "composti": n_comp, "proprietari": n_prop}
            serviti.append(rec)
            (coperti if n_prop > 0 else scoperti).append(rec)

        # provenienza dei soli scoperti (prefisso id = fonte)
        def _fonte(_id):
            if _id.startswith("ahn_"): return "ahn"
            if _id.startswith("ai_"): return "ai"
            if _id.startswith("ing-"): return "ing (senza matter)"
            return "altro"
        per_fonte = {}
        for r in scoperti:
            k = _fonte(r["id"])
            per_fonte[k] = per_fonte.get(k, 0) + 1

        tot = len(serviti)
        return jsonify({
            "modo": "DIAGNOSTICO (read-only, non scrive nulla)",
            "filtro": {"dominio": dominio or "(tutti)", "min_composti": min_composti},
            "universo_servito": tot,
            "coperti_proprietario": len(coperti),
            "scoperti": len(scoperti),
            "copertura_pct": round(100.0 * len(coperti) / tot, 1) if tot else 0,
            "scoperti_per_fonte": per_fonte,
            "nota": "coperti = almeno un composto con origine=matter_dataset. scoperti = serviti dall'app ma "
                    "ancora solo Ahn/ai: sono il bersaglio delle prossime ondate (cancello 1). "
                    "Lista ordinata per n composti (piu' alto = piu' connesso = piu' valore convertirlo).",
            "scoperti_lista": scoperti,
        })
    except Exception as e:
        import traceback
        try: conn.rollback()
        except Exception: pass
        return jsonify({"errore": str(e)[:200], "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)
