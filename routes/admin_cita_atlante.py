# ============================================================
# CITA-ATLANTE — popola il campo `provenienza.fonti` delle schede scienza
# (Fenomeno/Tecnica) con le fonti canoniche di dominio.
#
# Perché: su uno strumento che vive sulla provenienza, una scheda senza fonte
# è una promessa non mantenuta. Tutte le 355 schede avevano `fonti` vuoto.
# Qui NON si inventa nulla: si assegnano i LIBRI CANONICI reali (già nella
# bibliografia _BIBLIO_LIBRI di misc.py) che coprono davvero quel dominio,
# scelti per categoria + parole chiave. Le stringhe contengono la chiave-biblio
# così la pagina scheda (via /biblioteca → _pulisci_fonti) le risolve pulite.
#
# Sicurezza:
#   - auth ADMIN_SECRET (_admin_ok): header X-Admin-Secret o ?s=
#   - FILL-ONLY: scrive solo dove `fonti` è vuoto; non sovrascrive mai → idempotente
#   - DRY-RUN di default: mostra cosa farebbe. Scrive solo con &esegui=1
#   - una sola transazione, commit alla fine
#
# Uso:
#   anteprima:  /admin/cita-atlante?s=ADMIN_SECRET
#   scrivi:     /admin/cita-atlante?s=ADMIN_SECRET&esegui=1
# ============================================================
import json as _json, traceback
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from routes.admin import _admin_ok

bp_cita_atlante = Blueprint("cita_atlante", __name__)

# Stringhe-citazione leggibili; ognuna CONTIENE la chiave di _BIBLIO_LIBRI (match substring)
MCGEE  = "Harold McGee, On Food and Cooking (2004)"
MC     = "Nathan Myhrvold, Modernist Cuisine (2011)"
MB     = "Nathan Myhrvold, Modernist Bread (2017)"
HAM    = "Jeffrey Hamelman, Bread (2004)"
SUAS   = "Michel Suas, Advanced Bread and Pastry (2008)"
LIQ    = "Dave Arnold, Liquid Intelligence (2014)"
CIA    = "The Culinary Institute of America, The Professional Chef (2011)"
FENN   = "Damodaran & Parkin, Fennema's Food Chemistry (2017)"
WINE   = "Boulton, Singleton, Bisson & Kunkee, Principles and Practices of Winemaking (1999)"
COFFEE = "Britta Folmer (a cura di), The Craft and Science of Coffee (2017)"
ICE    = "Chris Clarke, The Science of Ice Cream (2012)"
CORV   = "Angelo Corvitto, Los secretos del helado (2011)"
FERM   = "Sandor Ellix Katz, The Art of Fermentation (2012)"
BREW   = "John Palmer, How to Brew (2017)"

_BASE = {
    "panificazione": [MB, HAM, SUAS, MCGEE],
    "pasticceria":   [SUAS, MC, MCGEE],
    "gelateria":     [CORV, ICE, MC],
    "bar":           [LIQ, MCGEE],
    "caffe":         [COFFEE, MCGEE],
    "caffetteria":   [COFFEE, MCGEE],
    "vino":          [WINE, MCGEE],
    "birra":         [BREW, MCGEE],
    "cucina":        [MC, CIA, MCGEE],
    "trasversale":   [MCGEE, MC, FENN],
}


def _fonti_per(slug, nome, categoria):
    """Fonti canoniche per una scheda. Dominio (categoria) + parole chiave distintive.
    Max 4. McGee resta la fonte universale quasi ovunque."""
    t = (str(slug) + " " + str(nome)).lower()
    cat = categoria or "trasversale"
    # guardia mis-categorizzazione: scheda 'caffe' che in realtà è cucina (brodi/fondi/carne)
    if cat in ("caffe", "caffetteria") and any(k in t for k in
            ["brodo", "brod", "fondi", "fondo", "collagene", "brasat", "carne", "osso", "gelatina"]):
        cat = "cucina"
    out = list(_BASE.get(cat, [MCGEE, MC]))

    def add(x):
        if x not in out:
            out.append(x)

    # fermentazione microbica (non "gelatina" né lievitazione chimica)
    if any(k in t for k in ["fermentaz", "lievito madre", "pasta madre", "starter",
                            "kombucha", "miso", "koji", "aceto", "lattob", "salamoia", "garum", "kefir"]):
        add(FERM)
    # vino / enologia
    if any(k in t for k in ["vino", "mosto", "tannin", "solfor", "malolatt", "enolog",
                            "chaptal", "carbonic maceration", "so2", "vinific", "brett"]):
        add(WINE)
    # birra
    if any(k in t for k in ["birra", "brassic", "mash", "ammostamento", "luppol", "wort"]):
        add(BREW)
    # gelato — SOLO termini del gelato, non "gelatina"/"gelatinizzazione"
    if any(k in t for k in ["gelato", "gelati ", "sorbett", "mantecaz", "overrun",
                            " snfs", "pacoss", "mix gelato", "potere anticongelante"]):
        add(CORV); add(ICE)
    # caffè — termini distintivi, non "crema"/"macinatura"
    if any(k in t for k in ["caffe", "espresso", "cold brew", "backflush", "portafiltro", "percolaz", "moka"]):
        add(COFFEE)
    # chimica di base (reazioni nominate) -> testo accademico Fennema
    if any(k in t for k in ["maillard", "caramell", "gelatinizz", "emuls", "denaturaz",
                            "ossidaz", "coagulaz", "cristallizz", "idrolisi"]):
        add(FENN)
    return out[:4]


@bp_cita_atlante.route("/admin/cita-atlante")
def cita_atlante():
    if not _admin_ok(request):
        return jsonify({"errore": "non autorizzato"}), 403
    esegui = request.args.get("esegui") in ("1", "true", "si", "yes")
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, domain, data FROM nodes WHERE type IN ('Fenomeno','Tecnica')")
        righe = cur.fetchall()
        tot = len(righe)
        scritte = 0
        gia_citate = 0
        per_categoria = {}
        esempi = []
        for r in righe:
            nid, nome, domain, data = r[0], r[1], r[2], r[3]
            dd = data if isinstance(data, dict) else (_json.loads(data) if data else {})
            prov = dd.get("provenienza") or {}
            esistenti = prov.get("fonti") or []
            if esistenti:
                gia_citate += 1
                continue
            # categoria: come la calcola la lista schede (data.categoria/disciplina/dominio, poi 'trasversale')
            categoria = dd.get("categoria") or dd.get("disciplina") or dd.get("dominio") or domain or "trasversale"
            fonti = _fonti_per(nid, nome, categoria)
            per_categoria[categoria] = per_categoria.get(categoria, 0) + 1
            if len(esempi) < 12:
                esempi.append({"slug": nid, "nome": nome, "categoria": categoria, "fonti": fonti})
            if esegui:
                prov["fonti"] = fonti
                prov.setdefault("fonti_nota", "Fonti tecniche canoniche del dominio.")
                dd["provenienza"] = prov
                cur.execute("UPDATE nodes SET data=%s WHERE id=%s",
                            (_json.dumps(dd, ensure_ascii=False), nid))
                scritte += 1
        if esegui:
            conn.commit()
        return jsonify({
            "modo": "SCRITTO" if esegui else "ANTEPRIMA (dry-run) — aggiungi &esegui=1 per scrivere",
            "totale_schede": tot,
            "gia_citate": gia_citate,
            "da_scrivere" if not esegui else "scritte": (tot - gia_citate) if not esegui else scritte,
            "per_categoria": per_categoria,
            "esempi": esempi,
            "nota": "FILL-ONLY: non sovrascrive schede già citate. Idempotente, rilanciabile.",
        })
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return jsonify({"errore": str(e)[:200], "trace": traceback.format_exc()[:400]}), 500
    finally:
        _release_conn(conn)
