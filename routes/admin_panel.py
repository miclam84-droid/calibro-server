# ============================================================
# routes/admin_panel.py — endpoint per il Galileo Control Panel.
# /admin/context  -> metriche aggregate (auth PANEL_SECRET, contratto con Cifra)
# /admin/logs     -> consultazione log (auth ADMIN_SECRET)
# /admin/logs/summary -> errori per endpoint (auth ADMIN_SECRET)
# ============================================================
import os

from flask import Blueprint, request, jsonify

import oss

bp = Blueprint("admin_panel", __name__)


@bp.route("/admin/context")
def admin_context():
    """Metriche aggregate lette dal Galileo Control Panel.
    Autenticato con PANEL_SECRET (segreto condiviso col pannello e con Cifra)."""
    atteso = os.environ.get("PANEL_SECRET")
    if not atteso or request.args.get("s", "") != atteso:
        return "Forbidden", 403
    return jsonify(oss.metriche())


@bp.route("/admin/logs")
def admin_logs():
    """Log recenti. ?level=ERROR|WARN|INFO  ?hours=24  ?limit=100"""
    if request.args.get("s", "") != os.environ.get("ADMIN_SECRET", ""):
        return "Forbidden", 403
    level = request.args.get("level")
    ore = request.args.get("hours", 24)
    limite = request.args.get("limit", 100)
    return jsonify(oss.logs_recenti(level=level, ore=ore, limite=limite))


@bp.route("/admin/logs/summary")
def admin_logs_summary():
    """Conteggio log per endpoint negli ultimi N giorni. ?days=7"""
    if request.args.get("s", "") != os.environ.get("ADMIN_SECRET", ""):
        return "Forbidden", 403
    giorni = request.args.get("days", 7)
    return jsonify(oss.logs_summary(giorni=giorni))
