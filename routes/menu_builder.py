"""
Menu Builder V1 — persistenza + QR.
Il "cervello" (proposte dal Flavor Network) è già in routes/api.py (/v1/menu/proposte).
Qui: salvare un menu creato dall'utente, recuperarlo, generarne il QR.
V2 (analisi equilibrio del menu-insieme) arriverà come endpoint separato.
"""
import os, json, io, uuid, time, hmac
from flask import Blueprint, request, jsonify, send_file

bp_menu = Blueprint("menu_builder", __name__)


def _conn():
    from db import _get_conn
    return _get_conn()

def _release(c):
    from db import _release_conn
    _release_conn(c)


def _ensure_menu_table():
    """Crea la tabella menu se non esiste. Idempotente."""
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS menu (
                id TEXT PRIMARY KEY,
                titolo TEXT,
                locale TEXT,
                lingua TEXT DEFAULT 'it',
                voci JSONB DEFAULT '[]'::jsonb,
                note TEXT,
                creato_il TIMESTAMP DEFAULT NOW(),
                aggiornato_il TIMESTAMP DEFAULT NOW()
            )
        """)
        c.commit()
    finally:
        _release(c)


@bp_menu.route("/v1/menu/crea", methods=["POST"])
def menu_crea():
    """Crea un nuovo menu vuoto o con voci iniziali.
    Body: {titolo, locale, lingua, voci:[{nome, prezzo, descrizione, ricetta_id?}]}
    Ritorna l'id del menu creato."""
    _ensure_menu_table()
    body = request.get_json(force=True, silent=True) or {}
    mid = "menu-" + uuid.uuid4().hex[:12]
    titolo = body.get("titolo", "Menu senza titolo")
    locale = body.get("locale", "")
    lingua = body.get("lingua", "it")
    voci = body.get("voci", [])
    c = _conn(); cur = c.cursor()
    try:
        cur.execute(
            "INSERT INTO menu (id, titolo, locale, lingua, voci) VALUES (%s,%s,%s,%s,%s::jsonb)",
            (mid, titolo, locale, lingua, json.dumps(voci, ensure_ascii=False))
        )
        c.commit()
        return jsonify({"id": mid, "titolo": titolo, "voci": len(voci)})
    except Exception as e:
        c.rollback()
        return jsonify({"errore": str(e)[:150]}), 500
    finally:
        _release(c)


@bp_menu.route("/v1/menu/<mid>", methods=["GET"])
def menu_get(mid):
    """Recupera un menu per id."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT id, titolo, locale, lingua, voci, note FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "menu non trovato"}), 404
        voci = r[4] if isinstance(r[4], list) else (json.loads(r[4]) if r[4] else [])
        return jsonify({"id": r[0], "titolo": r[1], "locale": r[2], "lingua": r[3],
                        "voci": voci, "note": r[5]})
    finally:
        _release(c)


@bp_menu.route("/v1/menu/<mid>/salva", methods=["POST"])
def menu_salva(mid):
    """Aggiorna un menu esistente (titolo, voci, note). Body come /crea."""
    _ensure_menu_table()
    body = request.get_json(force=True, silent=True) or {}
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT id FROM menu WHERE id=%s", (mid,))
        if not cur.fetchone():
            return jsonify({"errore": "menu non trovato"}), 404
        campi = []
        valori = []
        if "titolo" in body: campi.append("titolo=%s"); valori.append(body["titolo"])
        if "locale" in body: campi.append("locale=%s"); valori.append(body["locale"])
        if "lingua" in body: campi.append("lingua=%s"); valori.append(body["lingua"])
        if "note" in body: campi.append("note=%s"); valori.append(body["note"])
        if "voci" in body:
            campi.append("voci=%s::jsonb"); valori.append(json.dumps(body["voci"], ensure_ascii=False))
        campi.append("aggiornato_il=NOW()")
        valori.append(mid)
        cur.execute(f"UPDATE menu SET {', '.join(campi)} WHERE id=%s", tuple(valori))
        c.commit()
        return jsonify({"ok": True, "id": mid})
    except Exception as e:
        c.rollback()
        return jsonify({"errore": str(e)[:150]}), 500
    finally:
        _release(c)


@bp_menu.route("/v1/menu/<mid>/qr", methods=["GET"])
def menu_qr(mid):
    """Genera il QR code del menu (PNG). Punta all'URL pubblico del menu digitale."""
    try:
        import qrcode
    except ImportError:
        return jsonify({"errore": "qrcode non installato"}), 500
    base = os.environ.get("PUBLIC_BASE_URL", "https://web-production-79457.up.railway.app")
    url = f"{base}/menu/{mid}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"menu-{mid}-qr.png")


@bp_menu.route("/v1/menu/lista", methods=["GET"])
def menu_lista():
    """Lista dei menu salvati (id, titolo, n voci). Per un eventuale pannello."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT id, titolo, locale, lingua, jsonb_array_length(voci) FROM menu ORDER BY aggiornato_il DESC LIMIT 100")
        out = [{"id": r[0], "titolo": r[1], "locale": r[2], "lingua": r[3], "voci": r[4]} for r in cur.fetchall()]
        return jsonify({"menu": out, "totale": len(out)})
    finally:
        _release(c)


# ============================================================
# MENU BUILDER V2 — Analisi EQUILIBRIO SENSORIALE del menu-insieme.
# Direzione decisa (Gemini + OpenAI concordi): partire dall'ASSE DEI GUSTI
# (acido/dolce/amaro/salato/umami + texture), NON dall'aromatico (falsi positivi).
# Output: "il menu vira al 65% sull'asse acido, rischio saturazione". Feature Pro.
# ============================================================

_ASSI = ["acido", "dolce", "amaro", "salato", "umami"]

def _stima_profilo_voce(nome, descrizione=""):
    """L'AI stima il profilo gusto di UNA voce di menu su scala 0-10 per ogni asse.
    Ritorna dict {acido,dolce,amaro,salato,umami, texture} o None se fallisce."""
    from ai import _haiku_raw
    import json as _json, re as _re
    ctx = f"{nome}. {descrizione}".strip()
    prompt = (
        "Sei un tecnico del gusto. Per questo piatto/drink stima l'intensità di ogni gusto su scala 0-10 "
        "(0=assente, 10=dominante) e la texture prevalente. Rispondi SOLO con JSON, nessun'altra parola:\n"
        '{"acido":N,"dolce":N,"amaro":N,"salato":N,"umami":N,"texture":"una parola"}\n\n'
        f"Piatto/drink: {ctx}"
    )
    out = _haiku_raw(prompt, max_tokens=120) or ""
    m = _re.search(r'\{.*\}', out, _re.DOTALL)
    if not m:
        return None
    try:
        d = _json.loads(m.group(0))
        prof = {}
        for a in _ASSI:
            v = d.get(a, 0)
            try: prof[a] = max(0, min(10, float(v)))
            except (TypeError, ValueError): prof[a] = 0.0
        prof["texture"] = str(d.get("texture", "")).strip()[:20]
        return prof
    except Exception:
        return None


@bp_menu.route("/v1/menu/<mid>/equilibrio", methods=["GET"])
def menu_equilibrio(mid):
    """V2: analizza l'equilibrio sensoriale del menu salvato. Ritorna il profilo medio sugli assi del gusto
    + eventuali avvisi di squilibrio ('vira sull'acido'). Il valore che giustifica il Pro."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT titolo, voci FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "menu non trovato"}), 404
        titolo = r[0]
        voci = r[1] if isinstance(r[1], list) else (json.loads(r[1]) if r[1] else [])
    finally:
        _release(c)
    if len(voci) < 2:
        return jsonify({"errore": "servono almeno 2 voci per analizzare l'equilibrio"}), 400

    # stimo il profilo di ogni voce (max 15 voci per non esagerare coi tempi)
    profili = []
    texture_count = {}
    for v in voci[:15]:
        nome = v.get("nome", "")
        if not nome:
            continue
        p = _stima_profilo_voce(nome, v.get("descrizione", ""))
        if p:
            profili.append({"nome": nome, **p})
            tx = p.get("texture", "")
            if tx:
                texture_count[tx] = texture_count.get(tx, 0) + 1

    if not profili:
        return jsonify({"errore": "non è stato possibile analizzare le voci"}), 500

    n = len(profili)
    # media per asse
    medie = {a: round(sum(p[a] for p in profili) / n, 1) for a in _ASSI}
    somma_totale = sum(medie.values()) or 1
    # percentuale di ogni asse sul totale (per l'avviso "vira al X% sull'asse Y")
    percentuali = {a: round(100 * medie[a] / somma_totale) for a in _ASSI}

    avvisi = []
    # 1) asse dominante: se un gusto supera il 40% del totale
    asse_dom = max(percentuali, key=percentuali.get)
    if percentuali[asse_dom] >= 40:
        avvisi.append(f"Il menu vira al {percentuali[asse_dom]}% sull'asse {asse_dom.upper()}. Rischio di saturazione del palato.")
    # 2) asse assente: un gusto sotto 1.5/10 di media
    for a in _ASSI:
        if medie[a] < 1.5:
            avvisi.append(f"L'asse {a.upper()} è quasi assente (media {medie[a]}/10): il menu manca di contrasto su questo gusto.")
    # 3) texture monotona: se >60% delle voci condivide la stessa texture
    if texture_count:
        tx_dom, tx_n = max(texture_count.items(), key=lambda x: x[1])
        if tx_n / n > 0.6 and tx_n >= 3:
            avvisi.append(f"Texture ripetitiva: {tx_n} voci su {n} sono '{tx_dom}'. Varia la consistenza.")

    if not avvisi:
        avvisi.append("Menu equilibrato: nessun asse domina, buon contrasto tra i gusti.")

    return jsonify({
        "menu": titolo,
        "voci_analizzate": n,
        "profilo_medio": medie,       # {acido:5, dolce:8, ...} scala 0-10
        "percentuali": percentuali,   # {acido:22%, dolce:35%, ...}
        "texture_dominante": max(texture_count, key=texture_count.get) if texture_count else None,
        "avvisi": avvisi,
        "dettaglio_voci": profili
    })


# ============================================================
# MENU BUILDER V3 — GRAFICA: render del menu come HTML stampabile (PDF via browser).
# 3 template professionali. Palette Matter. Il frontend lo mostra e lo fa stampare/scaricare.
# ============================================================

_TEMPLATE_MENU = {
    "elegante": {
        "font": "Georgia, 'Times New Roman', serif",
        "bg": "#faf6ee", "ink": "#1a1a1a", "accent": "#245979", "linea": "#c77b3f",
    },
    "minimal": {
        "font": "'Helvetica Neue', Arial, sans-serif",
        "bg": "#ffffff", "ink": "#222222", "accent": "#12545d", "linea": "#dddddd",
    },
    "scuro": {
        "font": "'Helvetica Neue', Arial, sans-serif",
        "bg": "#1a2530", "ink": "#f0f0f0", "accent": "#c77b3f", "linea": "#3a4a58",
    },
}

@bp_menu.route("/v1/menu/<mid>/render", methods=["GET"])
def menu_render(mid):
    """Genera il menu come HTML stampabile. ?template=elegante|minimal|scuro. Stampabile come PDF dal browser."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT titolo, locale, voci FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return "<h1>Menu non trovato</h1>", 404
        titolo, locale, voci_raw = r[0], r[1], r[2]
        voci = voci_raw if isinstance(voci_raw, list) else (json.loads(voci_raw) if voci_raw else [])
    finally:
        _release(c)

    tpl = _TEMPLATE_MENU.get(request.args.get("template", "elegante"), _TEMPLATE_MENU["elegante"])

    def esc(s):
        return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    righe_html = []
    for v in voci:
        nome = esc(v.get("nome", ""))
        prezzo = esc(v.get("prezzo", ""))
        desc = esc(v.get("descrizione", ""))
        righe_html.append(f'''
        <div class="voce">
          <div class="voce-riga">
            <span class="voce-nome">{nome}</span>
            <span class="voce-punti"></span>
            <span class="voce-prezzo">{prezzo}</span>
          </div>
          {f'<div class="voce-desc">{desc}</div>' if desc else ''}
        </div>''')

    html = f'''<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titolo)}</title>
<style>
  @page {{ size: A4; margin: 20mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: {tpl["font"]}; background: {tpl["bg"]}; color: {tpl["ink"]};
         margin: 0; padding: 40px; max-width: 800px; margin: 0 auto; }}
  .menu-head {{ text-align: center; border-bottom: 2px solid {tpl["linea"]}; padding-bottom: 20px; margin-bottom: 30px; }}
  .menu-titolo {{ font-size: 34px; letter-spacing: 2px; margin: 0 0 6px; color: {tpl["accent"]}; }}
  .menu-locale {{ font-size: 14px; opacity: 0.7; letter-spacing: 1px; text-transform: uppercase; }}
  .voce {{ margin-bottom: 18px; }}
  .voce-riga {{ display: flex; align-items: baseline; }}
  .voce-nome {{ font-size: 18px; font-weight: 600; }}
  .voce-punti {{ flex: 1; border-bottom: 1px dotted {tpl["linea"]}; margin: 0 8px; transform: translateY(-4px); }}
  .voce-prezzo {{ font-size: 17px; color: {tpl["accent"]}; font-weight: 600; }}
  .voce-desc {{ font-size: 13px; opacity: 0.75; margin-top: 3px; font-style: italic; }}
  .menu-foot {{ text-align: center; margin-top: 40px; font-size: 11px; opacity: 0.5; }}
  @media print {{ body {{ padding: 0; }} .no-print {{ display: none; }} }}
</style></head>
<body>
  <div class="menu-head">
    <h1 class="menu-titolo">{esc(titolo)}</h1>
    {f'<div class="menu-locale">{esc(locale)}</div>' if locale else ''}
  </div>
  <div class="menu-voci">{''.join(righe_html)}</div>
  <div class="menu-foot">Creato con Matter</div>
</body></html>'''
    from flask import Response
    return Response(html, mimetype="text/html")

@bp_menu.route("/v1/menu/templates", methods=["GET"])
def menu_templates():
    """Elenca i template grafici disponibili per il menu."""
    return jsonify({"templates": [
        {"id": "elegante", "nome": "Elegante", "descrizione": "Serif classico, crema e blu di Prussia"},
        {"id": "minimal", "nome": "Minimal", "descrizione": "Sans-serif pulito, bianco e teal"},
        {"id": "scuro", "nome": "Scuro", "descrizione": "Fondo scuro, accenti terracotta"},
    ]})
