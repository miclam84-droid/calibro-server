# ============================================================
# IMPORTA-BIODIVERSITA — porta il seed di biodiversita (data/biodiversita_seed.json)
# nel grafo, scrivendo regione/territorio/tutela/categoria nel data JSONB dei nodi,
# cosi' da alimentare l'Atlante /v1/biodiversita/regioni (misc.py).
#
# Differenza chiave con la vecchia migrazione #201 (che SALTAVA i nomi non trovati):
# questo loader, se il nodo non esiste, LO CREA (type 'Prodotto', id bio-<slug>). Cosi'
# la mappa puo' passare da ~38 voci a centinaia senza dipendere da nodi preesistenti.
#
# Merge non distruttivo: sui nodi esistenti fa data = data || {campi biodiversita},
# quindi NON perde i campi gia' presenti (composti, specie, gusto...).
#
# Sicurezza: _admin_ok, DRY-RUN di default; scrive solo con &esegui=1. Idempotente.
# Uso:  /admin/importa-biodiversita?s=SECRET            (anteprima)
#       /admin/importa-biodiversita?s=SECRET&esegui=1   (scrive)
# ============================================================
import os, json, re, unicodedata
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_importa_biodiversita = Blueprint("importa_biodiversita", __name__)

_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "biodiversita_seed.json")

_TUTELE_VALIDE = {"dop", "igp", "presidio", "pat", "stg"}


def _slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _norm_tutela(t):
    """Normalizza la tutela alla forma che i contatori della mappa riconoscono (dop/igp/presidio)."""
    t = (t or "").strip().lower()
    if "presidio" in t or "slow food" in t:
        return "presidio"
    if t in ("dop", "pdo"):
        return "dop"
    if t in ("igp", "pgi"):
        return "igp"
    if t in ("stg", "tsg"):
        return "stg"
    if t == "pat":
        return "pat"
    return ""  # "da verificare" o ignoto -> niente tutela (resta varieta' non conteggiata)


@bp_importa_biodiversita.route("/admin/importa-biodiversita")
def importa_biodiversita():
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
        per_voce = []
        per_regione = {}

        for v in voci:
            nome = (v.get("nome") or "").strip()
            regione = (v.get("regione") or "").strip()
            area = (v.get("area") or "").strip()      # macro-regione del mondo (Africa, Americhe, Asia...)
            paese = (v.get("paese") or "").strip()     # paese (Perù, Messico, Etiopia...)
            # Accetta una voce ITALIANA (ha regione) OPPURE una voce MONDO (ha area).
            # I due assi restano separati: le voci-mondo non hanno 'regione', quindi
            # NON inquinano la mappa Italia (/v1/biodiversita/regioni).
            if not nome or (not regione and not area):
                saltati += 1
                continue
            tutela = _norm_tutela(v.get("tutela"))
            payload = {
                "territorio": (v.get("territorio") or "").strip(),
                "tutela": tutela,
                "categoria": (v.get("categoria") or "").strip(),
                "origine": "biodiversita_seed",
            }
            if regione:
                payload["regione"] = regione
            if area:
                payload["area"] = area
            if paese:
                payload["paese"] = paese
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
                nid = "bio-" + _slug(nome)
                azione = "creato (nuovo)"
                if esegui:
                    cur.execute(
                        "INSERT INTO nodes (id,type,name,domain,data) "
                        "VALUES (%s,'Prodotto',%s,%s,%s::jsonb) "
                        "ON CONFLICT (id) DO UPDATE SET data = COALESCE(nodes.data,'{}'::jsonb) || EXCLUDED.data",
                        (nid, nome, "cucina", pj),
                    )
                    creati += 1

            chiave = regione or area   # raggruppa per territorio (regione IT o area mondo)
            per_regione[chiave] = per_regione.get(chiave, 0) + 1
            per_voce.append({"nome": nome, "territorio_geo": chiave,
                             "asse": "italia" if regione else "mondo",
                             "paese": paese, "tutela": tutela or "(nessuna)",
                             "categoria": payload["categoria"], "nodo": nid, "azione": azione})

        if esegui:
            conn.commit()

        return jsonify({
            "modo": "SCRITTO" if esegui else "DRY-RUN (anteprima, aggiungi &esegui=1 per scrivere)",
            "voci_totali": len(voci),
            "creati_nuovi": creati,
            "arricchiti_esistenti": arricchiti,
            "saltati_senza_nome_o_territorio": saltati,
            "per_territorio": dict(sorted(per_regione.items(), key=lambda x: -x[1])),
            "per_voce": per_voce,
            "nota": "Voci con 'regione' -> mappa Italia (/v1/biodiversita/regioni). Voci con 'area' -> mappa Mondo (/v1/biodiversita/aree). DOP/IGP/presidio contati sull'Italia; il mondo si conta per varieta' e paesi.",
        })
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        import traceback
        return jsonify({"errore": str(e)[:200], "trace": traceback.format_exc()[:500]}), 500
    finally:
        cur.close()
        _release_conn(conn)
