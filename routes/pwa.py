# ============================================================
# routes/pwa.py — pagine PWA e endpoint di servizio.
# Route spostate da app.py senza modifiche di comportamento
# (@app.route -> @bp.route). Dipende solo da flask + db.
# ============================================================
from flask import Blueprint, render_template, jsonify
import time

from db import carica_grafo

bp = Blueprint("pwa", __name__)


@bp.route("/")
def landing():
    """LP1 — Landing page pubblica. Il CTA porta a /app."""
    return render_template("landing.html")

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
