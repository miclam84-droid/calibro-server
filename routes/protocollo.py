# ============================================================
# PROTOCOLLO — il deliverable: un record del Quaderno reso come foglio operativo
# esportabile (non una foto del piatto: un protocollo da laboratorio, deciso coi revisori).
# Legge quaderno_record per identita' (no accesso incrociato). Due uscite:
#  /v1/protocollo/<id>  -> JSON strutturato (identita', formula, profilo, registro)
#  /protocollo/<id>     -> pagina stampabile (design congelato) con righe per annotare a penna
# NON tocca i motori: assembla da cio' che e' gia' salvato.
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify, Response

bp_protocollo = Blueprint("protocollo", __name__)


def _chiave():
    try:
        from routes.stato import _chiave_utente
        return _chiave_utente()
    except Exception:
        try:
            from stato import _chiave_utente
            return _chiave_utente()
        except Exception:
            dev = request.headers.get("X-Device-Id", "").strip()
            return ("device", dev) if dev else (None, None)


def _leggi(rid, tipo_id, chiave):
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        cols = ["id", "creato_at", "porta", "funzione", "tipo", "titolo", "lingua",
                "stato_input", "stato_output", "provenienza", "note_lab"]
        cur.execute(f"""SELECT {','.join(cols)} FROM quaderno_record
                        WHERE id=%s AND chiave_tipo=%s AND chiave=%s""", (rid, tipo_id, str(chiave)))
        row = cur.fetchone(); cur.close()
        if not row:
            return None
        rec = {c: row[i] for i, c in enumerate(cols)}
        rec["creato_at"] = rec["creato_at"].isoformat() if rec["creato_at"] else None
        return rec
    finally:
        conn.close()


def _formula_righe(stato_input):
    """Estrae righe formula {nome, valore, unita} da stato_input (quantita' strutturate o piatte)."""
    righe = []
    if not isinstance(stato_input, dict):
        return righe
    for k, v in stato_input.items():
        if isinstance(v, dict) and "valore" in v:
            righe.append({"voce": k, "valore": v.get("valore"), "unita": v.get("unita", "")})
        elif isinstance(v, (int, float)):
            righe.append({"voce": k, "valore": v, "unita": ""})
    return righe


@bp_protocollo.route("/v1/protocollo/<rid>", methods=["GET"])
def protocollo_json(rid):
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    try:
        rec = _leggi(rid, tipo_id, chiave)
    except Exception as e:
        return jsonify({"errore": str(e)[:150]}), 500
    if not rec:
        return jsonify({"trovato": False}), 404
    return jsonify({
        "trovato": True,
        "identita": {"titolo": rec["titolo"], "registro": rec["id"], "data": rec["creato_at"],
                     "porta": rec["porta"], "funzione": rec["funzione"], "tipo": rec["tipo"]},
        "formula": _formula_righe(rec["stato_input"]),
        "profilo_atteso": rec["stato_output"],
        "provenienza": rec["provenienza"],
        "registro_empirico": rec.get("note_lab") or "",
    })


_CSS = """:root{--ink:#1D2A22;--muted:#4A5B50;--verde:#1E593C;--disp:'Schibsted Grotesk';--read:'Hanken Grotesk'}
*{box-sizing:border-box;margin:0}
body{font-family:var(--read);color:var(--ink);background:#fff;padding:26px 30px;max-width:760px;margin:0 auto}
.k{font-family:var(--disp);font-weight:700;font-size:11px;color:var(--verde);letter-spacing:.06em;text-transform:uppercase}
h1{font-family:var(--disp);font-weight:800;font-size:26px;letter-spacing:-.02em;margin:6px 0 2px}
.meta{color:var(--muted);font-size:12px;margin-bottom:18px;border-bottom:2px solid var(--ink);padding-bottom:10px}
h2{font-family:var(--disp);font-weight:700;font-size:13px;color:var(--verde);text-transform:uppercase;letter-spacing:.03em;margin:18px 0 6px}
table{width:100%;border-collapse:collapse;font-size:13px}
td{padding:5px 6px;border-bottom:1px solid #e3e8e3}
td.v{text-align:right;font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.out{font-size:13px;background:#f3f6f2;border-radius:10px;padding:12px 14px;white-space:pre-wrap}
.reg{margin-top:8px}
.reg .line{border-bottom:1px solid #c9d2c9;height:26px}
.src{font-size:10.5px;color:var(--muted);margin-top:18px;border-top:1px solid #e3e8e3;padding-top:8px}
@media print{body{padding:0}}
"""


@bp_protocollo.route("/protocollo/<rid>")
def protocollo_pagina(rid):
    tipo_id, chiave = _chiave()
    # la pagina chiede l'identita' via header non sempre disponibile dal browser;
    # supporta anche ?dev=<device-id> per la stampa diretta
    if not tipo_id:
        dev = request.args.get("dev", "").strip()
        if dev:
            tipo_id, chiave = ("device", dev)
    if not tipo_id:
        return Response("<p>Identita' mancante. Aggiungi ?dev=&lt;device-id&gt; all'URL.</p>", mimetype="text/html")
    try:
        rec = _leggi(rid, tipo_id, chiave)
    except Exception as e:
        return Response(f"<p>Errore: {str(e)[:120]}</p>", mimetype="text/html")
    if not rec:
        return Response("<p>Protocollo non trovato per questa identita'.</p>", mimetype="text/html")
    righe = _formula_righe(rec["stato_input"])
    righe_html = "".join(
        f"<tr><td>{r['voce']}</td><td class='v'>{r['valore']} {r['unita']}</td></tr>" for r in righe
    ) or "<tr><td colspan=2>—</td></tr>"
    try:
        out_txt = json.dumps(rec["stato_output"], ensure_ascii=False, indent=2) if rec["stato_output"] else "—"
    except Exception:
        out_txt = str(rec["stato_output"])
    reg_lines = "".join("<div class='line'></div>" for _ in range(6))
    note = rec.get("note_lab") or ""
    prov = ""
    if rec.get("provenienza"):
        try:
            prov = json.dumps(rec["provenienza"], ensure_ascii=False)
        except Exception:
            prov = str(rec["provenienza"])
    html = f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Protocollo · {rec['titolo']}</title>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@700;800&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{_CSS}</style></head><body>
<div class="k">Protocollo operativo · Matter</div>
<h1>{rec['titolo']}</h1>
<div class="meta">Registro {rec['id']} · {rec['creato_at'] or ''} · {rec['porta'] or ''} / {rec['funzione'] or ''}</div>
<h2>Formula</h2>
<table>{righe_html}</table>
<h2>Profilo / risultato atteso</h2>
<div class="out">{out_txt}</div>
<h2>Registro empirico — osservazioni al banco</h2>
<div class="out" style="background:#fff;border:1px solid #e3e8e3">{note or ''}</div>
<div class="reg">{reg_lines}</div>
<div class="src">Provenienza: {prov or 'n/d'}. Protocollo generato da Matter — i valori stimati/derivati vanno verificati al banco.</div>
</body></html>"""
    return Response(html, mimetype="text/html")
