# ============================================================
# IMPORTA-INGREDIENTI-CUCINA — crea nodi ingrediente "base" da un seed curato
# (data/ingredienti_cucina_seed.json), per salire con la copertura di ingredienti
# da cucina. Gemello di importa_biodiversita, ma SENZA campi di tutela/territorio:
# qui le voci sono ingredienti comuni (ortaggi, frutta, erbe, ...), non varietà.
#
# Il seed porta SOLO nome + categoria (il gusto si riempie dopo, coi runner USDA /
# pH / umami che leggono _USDA_CORE/_PH_CORE/_GLU_CORE in criteri.py). Qui si creano
# solo i NODI, così _risolvi_nodo li trova e i runner possono profilarli.
#
# Merge non distruttivo: sui nodi esistenti fa data = data || {categoria, origine},
# quindi NON perde composti/gusto già presenti. Dedup per nome (lower).
#
# Sicurezza: _admin_ok, DRY-RUN di default; scrive solo con &esegui=1. Idempotente.
# Uso:  /admin/importa-ingredienti-cucina?s=SECRET            (anteprima)
#       /admin/importa-ingredienti-cucina?s=SECRET&esegui=1   (scrive)
# ============================================================
import os, json, re, unicodedata
from flask import Blueprint, request, jsonify
from db import _get_conn
from routes.admin import _admin_ok

bp_importa_ingredienti_cucina = Blueprint("importa_ingredienti_cucina", __name__)

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ingredienti_cucina_seed.json")


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


@bp_importa_ingredienti_cucina.route("/admin/importa-ingredienti-cucina")
def importa_ingredienti_cucina():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    try:
        voci = json.load(open(_PATH, encoding="utf-8"))
    except Exception as e:
        return jsonify({"errore": "seed non leggibile: " + str(e)[:150]}), 500
    if not isinstance(voci, list):
        return jsonify({"errore": "il seed deve essere una lista di voci"}), 400

    conn = _get_conn()
    try:
        cur = conn.cursor()
        creati = 0
        arricchiti = 0
        saltati = 0
        per_categoria = {}
        per_voce = []
        visti = set()

        for v in voci:
            nome = (v.get("nome") or "").strip()
            categoria = (v.get("categoria") or "").strip()
            if not nome:
                saltati += 1
                continue
            chiave = nome.lower()
            if chiave in visti:      # dedup interno al seed
                saltati += 1
                continue
            visti.add(chiave)

            payload = {"categoria": categoria, "origine": "ingredienti_cucina_seed", "kind": "base"}
            pj = json.dumps(payload, ensure_ascii=False)

            # nodo esistente con lo stesso nome? (arricchisci, non duplicare)
            cur.execute(
                "SELECT id FROM nodes WHERE type IN ('Ingrediente','Prodotto') "
                "AND lower(name)=lower(%s) ORDER BY (id LIKE 'ahn_%%') DESC LIMIT 1",
                (nome,),
            )
            r = cur.fetchone()
            if r:
                nid = r[0]
                azione = "arricchito (" + nid + ")"
                if esegui:
                    cur.execute("UPDATE nodes SET data = COALESCE(data,'{}'::jsonb) || %s::jsonb WHERE id=%s",
                                (pj, nid))
                    arricchiti += 1
            else:
                nid = "ing-cuc-" + _slug(nome)
                azione = "creato (nuovo)"
                if esegui:
                    cur.execute(
                        "INSERT INTO nodes (id,type,name,domain,data) "
                        "VALUES (%s,'Ingrediente',%s,%s,%s::jsonb) "
                        "ON CONFLICT (id) DO UPDATE SET data = COALESCE(nodes.data,'{}'::jsonb) || EXCLUDED.data",
                        (nid, nome, "cucina", pj),
                    )
                    creati += 1

            per_categoria[categoria or "(nessuna)"] = per_categoria.get(categoria or "(nessuna)", 0) + 1
            per_voce.append({"nome": nome, "categoria": categoria, "nodo": nid, "azione": azione})

        if esegui:
            conn.commit()

        return jsonify({
            "modo": "SCRITTO" if esegui else "DRY-RUN (anteprima, aggiungi &esegui=1 per scrivere)",
            "voci_totali": len(voci),
            "creati_nuovi": creati,
            "arricchiti_esistenti": arricchiti,
            "saltati": saltati,
            "per_categoria": dict(sorted(per_categoria.items(), key=lambda x: -x[1])),
            "dettaglio": per_voce[:400],
            "nota": ("Crea solo i NODI. Il gusto si riempie dopo: mergia il PR con le mappature "
                     "USDA/pH/umami, poi lancia i runner /v1/criteri/usda-gusti-blocco e "
                     "/v1/criteri/gusti-ph-umami."),
        })
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
