# ============================================================
# routes/pwa.py — pagine PWA e endpoint di servizio.
# Route spostate da app.py senza modifiche di comportamento
# (@app.route -> @bp.route). Dipende solo da flask + db.
# ============================================================
from flask import Blueprint, render_template, jsonify, request
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
    """PWA principale — serve index.html."""
    return render_template("index.html")

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
