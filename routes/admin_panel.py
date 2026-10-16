# ============================================================
# routes/admin_panel.py — endpoint per il Galileo Control Panel.
# /admin/context  -> metriche aggregate (auth PANEL_SECRET, contratto con Cifra)
# /admin/logs     -> consultazione log (auth ADMIN_SECRET)
# /admin/logs/summary -> errori per endpoint (auth ADMIN_SECRET)
# ============================================================
import os
import hmac

from flask import Blueprint, request, jsonify

import oss

bp = Blueprint("admin_panel", __name__)


def _admin_ok(req):
    """Auth admin fail-closed (stesso standard di routes/admin.py _admin_ok e della wave-2):
    accetta il secret dall'header X-Admin-Secret (preferito, non finisce nei log) O dal query
    param ?s= (retrocompatibile), confronto a tempo costante, e NEGA se ADMIN_SECRET è assente."""
    _secret = os.environ.get("ADMIN_SECRET") or ""
    if not _secret:
        return False
    _dato = req.headers.get("X-Admin-Secret", "") or req.args.get("s", "")
    return hmac.compare_digest(str(_dato), str(_secret))


@bp.route("/admin/context")
def admin_context():
    """Metriche aggregate lette dal Galileo Control Panel.
    Autenticato con PANEL_SECRET (segreto condiviso col pannello e con Cifra)."""
    atteso = os.environ.get("PANEL_SECRET") or ""
    if not atteso or not hmac.compare_digest(str(request.args.get("s", "")), str(atteso)):
        return "Forbidden", 403
    return jsonify(oss.metriche())


@bp.route("/admin/logs")
def admin_logs():
    """Log recenti. ?level=ERROR|WARN|INFO  ?hours=24  ?limit=100"""
    if not _admin_ok(request):
        return "Forbidden", 403
    level = request.args.get("level")
    ore = request.args.get("hours", 24)
    limite = request.args.get("limit", 100)
    return jsonify(oss.logs_recenti(level=level, ore=ore, limite=limite))


@bp.route("/admin/logs/summary")
def admin_logs_summary():
    """Conteggio log per endpoint negli ultimi N giorni. ?days=7"""
    if not _admin_ok(request):
        return "Forbidden", 403
    giorni = request.args.get("days", 7)
    return jsonify(oss.logs_summary(giorni=giorni))
