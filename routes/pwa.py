# ============================================================
# routes/pwa.py — pagine PWA e endpoint di servizio.
# Route spostate da app.py senza modifiche di comportamento
# (@app.route -> @bp.route). Dipende solo da flask + db.
# ============================================================
from flask import Blueprint, render_template, jsonify, request, redirect
import os as _os, time as _time
# versione build per cache-busting dei moduli lazy (Railway espone il commit, fallback a timestamp d'avvio)
_BUILD_VER = (_os.environ.get("RAILWAY_GIT_COMMIT_SHA") or _os.environ.get("RAILWAY_DEPLOYMENT_ID") or str(int(_time.time())))[:12]
import time

from db import carica_grafo

bp = Blueprint("pwa", __name__)


@bp.route("/")
def landing():
    """LP1 — Landing page pubblica. Il CTA porta a /app."""
    return render_template("landing.html")

@bp.route("/help")
def help_page():
    """Pagina help pubblica."""
    return render_template("help.html")

@bp.route("/app")
def home():
    """SWITCHOVER (25/10): /app è ora il frontend nuovo (design congelato matter3).
    Redirect al nuovo hub /nuovo. Il vecchio index.html resta su disco per rollback:
    per ripristinarlo basta rimettere qui il render di 'index.html'."""
    return redirect("/nuovo")

@bp.route("/app2")
def home2():
    """SWITCHOVER (25/10): anche /app2 (vecchia iterazione index2.html) redirige al nuovo hub.
    index2.html resta su disco per rollback."""
    return redirect("/nuovo")

@bp.route("/scopri")
@bp.route("/scopri/<ing>")
def scopri(ing=None):
    """BONIFICA (25/10): /scopri (matter2) è superato da /scopri-nuovo (matter3, il
    grafo vero cablato a /v1/criteri). Redirect per non perdere vecchi link;
    il template scopri.html è stato rimosso. L'ingrediente viene conservato."""
    return redirect("/scopri-nuovo/" + ing if ing else "/scopri-nuovo")

@bp.route("/ingrediente/<nome>")
def scheda_ingrediente(nome):
    """FRONTEND-2.0 — scheda ingrediente (Atlante): profilo sensoriale con provenienza
    per asse + teaser abbinamenti. Cablata a /v1/profilo-gusto e /v1/criteri.
    Pagina nuova e isolata: non tocca /app né /app2."""
    from flask import make_response
    resp = make_response(render_template("scheda-nuovo.html", nome=nome))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@bp.route("/banco")
@bp.route("/banco/cocktail")
def banco_cocktail():
    """FRONTEND-2.0 — Banco: calcolatore cocktail (diluizione/gradazione, metodo Dave Arnold).
    Cablato a /v1/motore/cocktail. Pagina nuova e isolata: non tocca /app né /app2."""
    from flask import make_response
    resp = make_response(render_template("banco-cocktail-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@bp.route("/banco/panificazione")
def banco_panificazione():
    """FRONTEND-2.0 — Banco: calcolatore panificazione (dosi, temp acqua, tabella di marcia a ritroso).
    Cablato a /v1/motore/panificazione (motore Hamelman). Pagina nuova e isolata: non tocca /app né /app2."""
    from flask import make_response
    resp = make_response(render_template("banco-panificazione-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@bp.route("/banco/calcolatori")
def banco_calcolatori():
    """FRONTEND-2.0 — Banco: i calcolatori deterministici (idratazione, estrazione caffè, Q10,
    sour, teglie, Brix, resa, temp vino…). Cablati a POST /calcola (motore, nessuna AI)."""
    from flask import make_response
    resp = make_response(render_template("banco-calcolatori.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

@bp.route("/biodiversita")
@bp.route("/atlante")
def biodiversita():
    """FRONTEND-2.0 — Atlante della biodiversità: territori nord→sud, ogni regione si apre
    e rivela le sue varietà a rischio (Presìdi/DOP/IGP). Cablato dal vivo a
    /v1/biodiversita/regioni + /v1/biodiversita/regione/<x>. Lo stato di scoperta
    è solo nel browser (localStorage), per-dispositivo. Pagina nuova e isolata."""
    from flask import make_response
    resp = make_response(render_template("biodiversita-nuovo.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp

_FOTO_ING_CACHE = {}  # {nome_lower: {"dato":{...}, "t":epoch}} — cache in memoria, niente scrittura sul grafo
_FOTO_EMPTY_TTL = 3 * 3600  # un "niente foto" si RIPROVA dopo 3h: Pexels puo' fallire per quota o transitorio,
                            # e non vogliamo che un buco temporaneo blanchi per sempre un ingrediente.

def _foto_resp(dato):
    r = jsonify(dato)
    r.headers["Cache-Control"] = "public, max-age=86400"
    return r

@bp.route("/v1/foto-ingrediente/<path:nome>")
def foto_ingrediente(nome):
    """Foto ON-DEMAND per la scheda ingrediente (Atlante). Pesca da stock
    (Pexels/Unsplash/Pixabay/Wikimedia) con attribuzione; cache in memoria.
    Nessuna scrittura sul grafo. Se non trova nulla di pertinente torna url:null,
    così la scheda NON mostra una foto sbagliata (onestà: meglio niente)."""
    chiave = (nome or "").strip().lower()
    if not chiave:
        return _foto_resp({"url": None})
    import time as _t
    hit = _FOTO_ING_CACHE.get(chiave)
    if hit and (hit["dato"].get("url") or (_t.time() - hit["t"]) < _FOTO_EMPTY_TTL):
        return _foto_resp(hit["dato"])  # successo: per sempre; vuoto: solo finche' non scade il TTL
    res = None
    try:
        from immagini import cerca_immagine_ingrediente
        res = cerca_immagine_ingrediente(chiave)
    except Exception:
        res = None
    if res and res.get("url"):
        dato = {"url": res.get("url"), "autore": res.get("autore", ""),
                "fonte_nome": res.get("fonte_nome", ""), "match": res.get("match", "")}
    else:
        dato = {"url": None}
    _FOTO_ING_CACHE[chiave] = {"dato": dato, "t": _t.time()}
    return _foto_resp(dato)

@bp.route("/admin/tassonomia")
def admin_tassonomia():
    """FRONTEND-2.0 — pannello admin 'Tassonomia': classifica gli ingredienti da Wikidata (CC0)
    a blocchi, col clic. Gate ?s=ADMIN_SECRET. La scrittura parte dal browser admin."""
    import os as _os, hmac as _hmac
    from flask import make_response
    if not _hmac.compare_digest(str(request.args.get("s", "")), str(_os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    resp = make_response(render_template("tassonomia.html", sec=request.args.get("s", "")))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@bp.route("/admin/copertura")
def admin_copertura():
    """FRONTEND-2.0 — pannello admin 'Copertura gusto': rivedi i derivati USDA e scrivi col clic.
    Gate ?s=ADMIN_SECRET (stesso schema degli altri admin). La scrittura parte dal browser admin."""
    import os as _os, hmac as _hmac
    from flask import make_response
    if not _hmac.compare_digest(str(request.args.get("s", "")), str(_os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    resp = make_response(render_template("copertura.html", sec=request.args.get("s", "")))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@bp.route("/manifest.json")
def manifest():
    """PWA manifest."""
    from flask import send_from_directory
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

@bp.route("/sw.js")
def service_worker():
    """PWA Service Worker."""
    from flask import send_from_directory
    resp = send_from_directory("static", "sw.js", mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp

@bp.route("/.well-known/assetlinks.json")
def assetlinks():
    """Google Play TWA — Digital Asset Links. 
    Sostituire package_name e sha256 con i valori reali prima del deploy su Play Store."""
    return jsonify([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": "com.matterlab.app",
            "sha256_cert_fingerprints": ["SOSTITUIRE_CON_SHA256_DEL_KEYSTORE"]
        }
    }])

@bp.route("/favicon.ico")
def favicon():
    """Evita il 404 di /favicon.ico su ogni pagina (errore console Lighthouse):
    il browser lo richiede sempre, lo reindirizziamo all'icona PWA esistente."""
    return redirect("/static/icons/icon-96.png", code=302)


@bp.route("/apple-touch-icon.png")
@bp.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon():
    return redirect("/static/icons/icon-152.png", code=302)


@bp.route("/health")
def health():
    """IN3 — Endpoint per monitoring (UptimeRobot punta qui).
    Verifica che Flask risponda E che Postgres sia raggiungibile."""
    try:
        db = carica_grafo()
        r = db.execute("SELECT count(*) as n FROM nodes").fetchone()
        nodi = r["n"] if r else 0
        return jsonify({"status": "ok", "nodi": nodi, "ts": time.time()})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@bp.route("/health/check")
def health_check():
    """Health ESTESO per osservabilità: DB, provider AI, conteggi chiave.
    Protetto da chiave (?s=ADMIN_SECRET) perché espone dettagli interni.
    Un solo colpo d'occhio sullo stato del sistema per un founder solo."""
    import os as _os, hmac as _hmac
    if not _hmac.compare_digest(str(request.args.get("s", "")), str(_os.environ.get("ADMIN_SECRET") or "")):
        return jsonify({"errore": "non autorizzato"}), 403
    stato = {"ts": time.time(), "componenti": {}}
    problemi = []
    # 1) DB + latenza
    try:
        _t0 = time.time()
        db = carica_grafo()
        r = db.execute("SELECT count(*) as n FROM nodes").fetchone()
        lat = round((time.time() - _t0) * 1000, 1)
        stato["componenti"]["db"] = {"ok": True, "latenza_ms": lat, "nodi": r["n"] if r else 0}
        if lat > 2000:
            problemi.append(f"DB lento ({lat}ms)")
    except Exception as e:
        stato["componenti"]["db"] = {"ok": False, "errore": str(e)[:100]}
        problemi.append("DB non raggiungibile")
    # 2) provider AI configurati (presenza chiavi, non chiamate — per non spendere)
    for prov, env in [("anthropic", "ANTHROPIC_API_KEY"), ("openai", "OPENAI_API_KEY"),
                      ("mistral", "MISTRAL_API_KEY"), ("gemini", "GEMINI_API_KEY")]:
        ok = bool(_os.environ.get(env))
        stato["componenti"][prov] = {"configurato": ok}
        if not ok:
            problemi.append(f"{prov} senza chiave")
    # 3) conteggi chiave (per accorgersi se il DB si svuota)
    try:
        db = carica_grafo()
        fen = db.execute("SELECT count(*) as n FROM nodes WHERE type='Fenomeno'").fetchone()
        ric = db.execute("SELECT count(*) as n FROM ricette").fetchone()
        stato["componenti"]["contenuti"] = {
            "fenomeni": fen["n"] if fen else 0, "ricette": ric["n"] if ric else 0}
        if (fen["n"] if fen else 0) < 100:
            problemi.append("pochi fenomeni nel DB")
    except Exception:
        pass
    stato["status"] = "ok" if not problemi else "degradato"
    stato["problemi"] = problemi
    return jsonify(stato), (200 if not problemi else 503)


@bp.route("/static/sw.js")
def sw():
    """IN5 — Serve il service worker dalla cartella static."""
    import pathlib
    sw_path = pathlib.Path(__file__).parent / "static" / "sw.js"
    if sw_path.exists():
        return sw_path.read_text(), 200, {
            'Content-Type': 'application/javascript',
            'Service-Worker-Allowed': '/'
        }
    return '', 404
