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
        # campi nuovi (retrocompatibili): tipo di documento e filo conduttore/filosofia
        cur.execute("ALTER TABLE menu ADD COLUMN IF NOT EXISTS tipo_menu TEXT DEFAULT 'food'")
        cur.execute("ALTER TABLE menu ADD COLUMN IF NOT EXISTS filosofia TEXT")
        cur.execute("ALTER TABLE menu ADD COLUMN IF NOT EXISTS tema_grafico TEXT DEFAULT 'gastro-bistrot'")
        c.commit()
    finally:
        _release(c)


@bp_menu.route("/v1/menu/filosofia", methods=["POST"])
def menu_filosofia():
    """P7 — Genera il FILO CONDUTTORE (filosofia) di un menu dal brief del locale.
    Body: {vibe, territorio, filo_conduttore, tipo_menu, stagione, fascia_prezzo}.
    Restituisce JSON strutturato: filosofia_riassunto, regola_di_coerenza, macro_ingredienti_target.
    Questo NON è testo libero: è una matrice logica che guiderà la generazione coerente del menu."""
    body = request.get_json(force=True, silent=True) or {}
    vibe = (body.get("vibe") or "").strip()
    territorio = (body.get("territorio") or "").strip()
    filo = (body.get("filo_conduttore") or "").strip()
    tipo_menu = (body.get("tipo_menu") or "food").strip()
    stagione = (body.get("stagione") or "").strip()
    fascia = (body.get("fascia_prezzo") or "").strip()
    if not (vibe or territorio or filo):
        return jsonify({"errore": "servono almeno vibe, territorio o filo conduttore"}), 400
    # per le carte vini, la logica di classificazione cambia (vitigno/acidità, non portate)
    _extra = ("Questo è un menu di tipo VINO: organizza per vitigno o per assi di "
              "acidità/struttura, non per portate.") if tipo_menu == "wine" else ""
    prompt = (
        f"Sei un consulente F&B. Definisci la FILOSOFIA (filo conduttore) di un menu.\n"
        f"Brief del locale: vibe='{vibe}', territorio='{territorio}', filo conduttore='{filo}', "
        f"stagione='{stagione}', fascia prezzo='{fascia}'. {_extra}\n"
        f"Rispondi SOLO con JSON valido, senza testo attorno:\n"
        f'{{"filosofia_riassunto":"una frase che cattura l\'identità del menu",'
        f'"regola_di_coerenza":"la regola che ogni piatto deve rispettare per appartenere a questa carta",'
        f'"macro_ingredienti_target":["ingrediente1","ingrediente2","ingrediente3","ingrediente4"]}}'
    )
    try:
        from ai_gateway import route_quality
        import re as _re
        raw = (route_quality(prompt, max_tokens=500) or "").strip()
        raw = _re.sub(r"```json|```", "", raw).strip()
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            raw = m.group(0)
        data = json.loads(raw)
        return jsonify({
            "ok": True,
            "filosofia_riassunto": data.get("filosofia_riassunto", ""),
            "regola_di_coerenza": data.get("regola_di_coerenza", ""),
            "macro_ingredienti_target": data.get("macro_ingredienti_target", []),
        })
    except Exception as e:
        return jsonify({"errore": "generazione filosofia fallita", "dettaglio": str(e)[:120]}), 200


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
    tipo_menu = body.get("tipo_menu", "food")   # food | drink | wine | fuso
    filosofia = body.get("filosofia", "")
    tema = body.get("tema_grafico", "gastro-bistrot")  # gastro-bistrot | minimal-blueprint | enoteca-classica
    c = _conn(); cur = c.cursor()
    try:
        cur.execute(
            "INSERT INTO menu (id, titolo, locale, lingua, voci, tipo_menu, filosofia, tema_grafico) "
            "VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
            (mid, titolo, locale, lingua, json.dumps(voci, ensure_ascii=False), tipo_menu, filosofia, tema)
        )
        c.commit()
        return jsonify({"id": mid, "titolo": titolo, "voci": len(voci),
                        "tipo_menu": tipo_menu, "tema_grafico": tema})
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
        cur.execute("SELECT id, titolo, locale, lingua, voci, note, tipo_menu, filosofia, tema_grafico FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "menu non trovato"}), 404
        voci = r[4] if isinstance(r[4], list) else (json.loads(r[4]) if r[4] else [])
        return jsonify({"id": r[0], "titolo": r[1], "locale": r[2], "lingua": r[3],
                        "voci": voci, "note": r[5],
                        "tipo_menu": r[6] or "food", "filosofia": r[7] or "",
                        "tema_grafico": r[8] or "gastro-bistrot"})
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
    """Genera il menu come HTML (stampabile PDF, o da mettere su un sito). FLESSIBILE:
    ?template=elegante|minimal|scuro  ?foto=1 (mostra le foto dei piatti)  ?sezioni=1 (raggruppa per sezione)
    Le voci possono avere: nome, prezzo, descrizione, immagine, sezione. La struttura la decide l'utente
    (frontend): il backend rende quello che riceve. Niente template fisso imposto."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT titolo, locale, voci, note FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return "<h1>Menu non trovato</h1>", 404
        titolo, locale, voci_raw, note = r[0], r[1], r[2], r[3]
        voci = voci_raw if isinstance(voci_raw, list) else (json.loads(voci_raw) if voci_raw else [])
    finally:
        _release(c)

    tpl = dict(_TEMPLATE_MENU.get(request.args.get("template", "elegante"), _TEMPLATE_MENU["elegante"]))
    mostra_foto = request.args.get("foto", "0") != "0"
    usa_sezioni = request.args.get("sezioni", "1") != "0"  # default: raggruppa per sezione se presente

    # ── PERSONALIZZAZIONE DEL RISTORATORE (logo, colore, footer) ──
    # ?logo=<url> ?accent=<hex senza #> ?footer=<testo> ?font=<serif|sans>
    logo_url = request.args.get("logo", "").strip()
    accent_custom = request.args.get("accent", "").strip()
    if accent_custom:
        # accetto sia "245979" sia "%23245979"; metto io il #
        accent_custom = accent_custom.lstrip("#")
        if len(accent_custom) in (3, 6) and all(ch in "0123456789abcdefABCDEF" for ch in accent_custom):
            tpl["accent"] = "#" + accent_custom
            tpl["linea"] = "#" + accent_custom  # la linea segue l'accento scelto
    footer_custom = request.args.get("footer", "").strip()
    font_scelta = request.args.get("font", "").strip()
    if font_scelta == "serif":
        tpl["font"] = "Georgia, 'Times New Roman', serif"
    elif font_scelta == "sans":
        tpl["font"] = "'Helvetica Neue', Arial, sans-serif"

    def esc(s):
        return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render_voce(v):
        nome = esc(v.get("nome", ""))
        prezzo = esc(v.get("prezzo", ""))
        desc = esc(v.get("descrizione", ""))
        img = v.get("immagine", "")
        foto_html = ""
        if mostra_foto and img:
            foto_html = f'<div class="voce-foto"><img src="{esc(img)}" alt="{nome}" loading="lazy"></div>'
        return f'''
        <div class="voce{' voce-con-foto' if (mostra_foto and img) else ''}">
          {foto_html}
          <div class="voce-testo">
            <div class="voce-riga">
              <span class="voce-nome">{nome}</span>
              <span class="voce-punti"></span>
              <span class="voce-prezzo">{prezzo}</span>
            </div>
            {f'<div class="voce-desc">{desc}</div>' if desc else ''}
          </div>
        </div>'''

    # raggruppo per sezione (l'utente le nomina liberamente: "Signature", "Vini", "Cibo"...)
    corpo = ""
    if usa_sezioni and any(v.get("sezione") for v in voci):
        sezioni = {}
        ordine = []
        for v in voci:
            sez = v.get("sezione", "") or "​"  # senza sezione -> gruppo vuoto
            if sez not in sezioni:
                sezioni[sez] = []; ordine.append(sez)
            sezioni[sez].append(v)
        for sez in ordine:
            titolo_sez = f'<h2 class="menu-sezione">{esc(sez)}</h2>' if sez.strip() else ''
            voci_html = ''.join(render_voce(v) for v in sezioni[sez])
            corpo += f'<div class="sezione-blocco">{titolo_sez}{voci_html}</div>'
    else:
        corpo = ''.join(render_voce(v) for v in voci)

    html = f'''<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titolo)}</title>
<style>
  @page {{ size: A4; margin: 18mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: {tpl["font"]}; background: {tpl["bg"]}; color: {tpl["ink"]};
         margin: 0 auto; padding: 40px; max-width: 820px; }}
  .menu-head {{ text-align: center; border-bottom: 2px solid {tpl["linea"]}; padding-bottom: 20px; margin-bottom: 28px; }}
  .menu-logo {{ max-width: 140px; max-height: 90px; margin: 0 auto 12px; display: block; object-fit: contain; }}
  .menu-titolo {{ font-size: 34px; letter-spacing: 2px; margin: 0 0 6px; color: {tpl["accent"]}; }}
  .menu-locale {{ font-size: 14px; opacity: 0.7; letter-spacing: 1px; text-transform: uppercase; }}
  .menu-sezione {{ font-size: 20px; color: {tpl["accent"]}; letter-spacing: 1px; text-transform: uppercase;
                   border-bottom: 1px solid {tpl["linea"]}; padding-bottom: 6px; margin: 28px 0 16px; }}
  .voce {{ margin-bottom: 18px; }}
  .voce-con-foto {{ display: flex; gap: 14px; align-items: flex-start; }}
  .voce-foto img {{ width: 84px; height: 84px; object-fit: cover; border-radius: 8px; }}
  .voce-testo {{ flex: 1; }}
  .voce-riga {{ display: flex; align-items: baseline; }}
  .voce-nome {{ font-size: 18px; font-weight: 600; }}
  .voce-punti {{ flex: 1; border-bottom: 1px dotted {tpl["linea"]}; margin: 0 8px; transform: translateY(-4px); }}
  .voce-prezzo {{ font-size: 17px; color: {tpl["accent"]}; font-weight: 600; white-space: nowrap; }}
  .voce-desc {{ font-size: 13px; opacity: 0.78; margin-top: 3px; font-style: italic; }}
  .menu-note {{ margin-top: 30px; font-size: 12px; opacity: 0.6; text-align: center; }}
  .menu-foot {{ text-align: center; margin-top: 36px; font-size: 11px; opacity: 0.45; }}
  @media print {{ body {{ padding: 0; }} .no-print {{ display: none; }} }}
</style></head>
<body>
  <div class="menu-head">
    {f'<img class="menu-logo" src="{esc(logo_url)}" alt="logo">' if logo_url else ''}
    <h1 class="menu-titolo">{esc(titolo)}</h1>
    {f'<div class="menu-locale">{esc(locale)}</div>' if locale else ''}
  </div>
  <div class="menu-corpo">{corpo}</div>
  {f'<div class="menu-note">{esc(note)}</div>' if note else ''}
  <div class="menu-foot">{esc(footer_custom) if footer_custom else 'Creato con Matter'}</div>
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


# ── UPLOAD LOGO su Cloudinary (per la personalizzazione del menu) ──
@bp_menu.route("/v1/menu/upload-logo", methods=["POST"])
def menu_upload_logo():
    """Riceve un file immagine (logo del ristoratore), lo carica su Cloudinary, torna {url}.
    Il frontend poi passa quell'url a /v1/menu/render come ?logo=<url>.
    Accetta multipart/form-data con campo 'file'."""
    f = request.files.get("file")
    if not f:
        return jsonify({"errore": "nessun file (campo 'file' mancante)"}), 400
    img_bytes = f.read()
    if not img_bytes:
        return jsonify({"errore": "file vuoto"}), 400
    if len(img_bytes) > 3 * 1024 * 1024:
        return jsonify({"errore": "logo troppo grande (max 3MB)"}), 400
    try:
        from pixabay_riempi import _carica_cloudinary
        import time as _t
        public_id = f"logo-menu-{int(_t.time())}"
        url = _carica_cloudinary(img_bytes, public_id)
        if url:
            return jsonify({"url": url, "public_id": public_id})
        return jsonify({"errore": "upload fallito (Cloudinary non configurato o errore)"}), 500
    except Exception as e:
        return jsonify({"errore": f"upload: {e}"}), 500


# ── RENDER MENU DA BODY (per menu in localStorage senza id server-side) ──
@bp_menu.route("/v1/menu/render", methods=["POST"])
def menu_render_body():
    """Come /v1/menu/<id>/render ma riceve il menu NEL BODY (non serve id server-side).
    Per i menu salvati solo in localStorage sul frontend.
    Body: {titolo, locale, voci:[{nome,prezzo,descrizione,sezione,immagine}], note,
           template?, logo?, accent?, footer?, font?}"""
    body = request.json or {}
    titolo = body.get("titolo", "Menu")
    locale = body.get("locale", "")
    note = body.get("note", "")
    voci = body.get("voci", []) or []

    tpl = dict(_TEMPLATE_MENU.get(body.get("template", "elegante"), _TEMPLATE_MENU["elegante"]))
    mostra_foto = bool(body.get("foto", False))
    usa_sezioni = body.get("sezioni", True)
    logo_url = (body.get("logo") or "").strip()
    accent_custom = (body.get("accent") or "").strip().lstrip("#")
    if accent_custom and len(accent_custom) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in accent_custom):
        tpl["accent"] = "#" + accent_custom
        tpl["linea"] = "#" + accent_custom
    footer_custom = (body.get("footer") or "").strip()
    font_scelta = (body.get("font") or "").strip()
    if font_scelta == "serif": tpl["font"] = "Georgia, 'Times New Roman', serif"
    elif font_scelta == "sans": tpl["font"] = "'Helvetica Neue', Arial, sans-serif"

    def esc(s):
        return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render_voce(v):
        nome = esc(v.get("nome", "")); prezzo = esc(v.get("prezzo", "")); desc = esc(v.get("descrizione", ""))
        img = v.get("immagine", ""); foto_html = ""
        if mostra_foto and img:
            foto_html = f'<div class="voce-foto"><img src="{esc(img)}" alt="{nome}" loading="lazy"></div>'
        return f'''<div class="voce{' voce-con-foto' if (mostra_foto and img) else ''}">{foto_html}
          <div class="voce-testo"><div class="voce-riga"><span class="voce-nome">{nome}</span>
          <span class="voce-punti"></span><span class="voce-prezzo">{prezzo}</span></div>
          {f'<div class="voce-desc">{desc}</div>' if desc else ''}</div></div>'''

    corpo = ""
    if usa_sezioni and any(v.get("sezione") for v in voci):
        sezioni = {}; ordine = []
        for v in voci:
            sez = v.get("sezione", "") or "\u200b"
            if sez not in sezioni: sezioni[sez] = []; ordine.append(sez)
            sezioni[sez].append(v)
        for sez in ordine:
            titolo_sez = f'<h2 class="menu-sezione">{esc(sez)}</h2>' if sez.strip() else ''
            corpo += f'<div class="sezione-blocco">{titolo_sez}{"".join(render_voce(v) for v in sezioni[sez])}</div>'
    else:
        corpo = ''.join(render_voce(v) for v in voci)

    html = f'''<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(titolo)}</title>
<style>@page {{ size:A4; margin:18mm; }} *{{box-sizing:border-box;}}
body{{font-family:{tpl["font"]};background:{tpl["bg"]};color:{tpl["ink"]};margin:0 auto;padding:40px;max-width:820px;}}
.menu-head{{text-align:center;border-bottom:2px solid {tpl["linea"]};padding-bottom:20px;margin-bottom:28px;}}
.menu-logo{{max-width:140px;max-height:90px;margin:0 auto 12px;display:block;object-fit:contain;}}
.menu-titolo{{font-size:34px;letter-spacing:2px;margin:0 0 6px;color:{tpl["accent"]};}}
.menu-locale{{font-size:14px;opacity:.7;letter-spacing:1px;text-transform:uppercase;}}
.menu-sezione{{font-size:20px;color:{tpl["accent"]};letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid {tpl["linea"]};padding-bottom:6px;margin:28px 0 16px;}}
.voce{{margin-bottom:18px;}} .voce-con-foto{{display:flex;gap:14px;align-items:flex-start;}}
.voce-foto img{{width:84px;height:84px;object-fit:cover;border-radius:8px;}} .voce-testo{{flex:1;}}
.voce-riga{{display:flex;align-items:baseline;}} .voce-nome{{font-size:18px;font-weight:600;}}
.voce-punti{{flex:1;border-bottom:1px dotted {tpl["linea"]};margin:0 8px;transform:translateY(-4px);}}
.voce-prezzo{{font-size:17px;color:{tpl["accent"]};font-weight:600;white-space:nowrap;}}
.voce-desc{{font-size:13px;opacity:.78;margin-top:3px;font-style:italic;}}
.menu-note{{margin-top:30px;font-size:12px;opacity:.6;text-align:center;}}
.menu-foot{{text-align:center;margin-top:36px;font-size:11px;opacity:.45;}}
@media print{{body{{padding:0;}}}}</style></head><body>
<div class="menu-head">{f'<img class="menu-logo" src="{esc(logo_url)}" alt="logo">' if logo_url else ''}
<h1 class="menu-titolo">{esc(titolo)}</h1>{f'<div class="menu-locale">{esc(locale)}</div>' if locale else ''}</div>
<div class="menu-corpo">{corpo}</div>{f'<div class="menu-note">{esc(note)}</div>' if note else ''}
<div class="menu-foot">{esc(footer_custom) if footer_custom else 'Creato con Matter'}</div></body></html>'''
    from flask import Response
    return Response(html, mimetype="text/html")


@bp_menu.route("/v1/menu/<mid>/pdf", methods=["GET"])
def menu_pdf(mid):
    """Genera il menu come PDF VERO scaricabile (non 'stampa dal browser').
    Stessi parametri di /render: ?template= ?accent= ?footer= ?logo= (url immagine).
    Usa reportlab. Il PDF è pronto per la stampa A4."""
    _ensure_menu_table()
    c = _conn(); cur = c.cursor()
    try:
        cur.execute("SELECT titolo, locale, voci, note FROM menu WHERE id=%s", (mid,))
        r = cur.fetchone()
        if not r:
            return jsonify({"errore": "menu non trovato"}), 404
        titolo, locale, voci_raw, note = r[0], r[1], r[2], r[3]
        voci = voci_raw if isinstance(voci_raw, list) else (json.loads(voci_raw) if voci_raw else [])
    finally:
        _release(c)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                        TableStyle, Image as RLImage, HRFlowable)
    except Exception:
        return jsonify({"errore": "generatore PDF non disponibile"}), 500

    # template/colori (come /render)
    tpl = dict(_TEMPLATE_MENU.get(request.args.get("template", "elegante"), _TEMPLATE_MENU["elegante"]))
    accent_custom = request.args.get("accent", "").strip().lstrip("#")
    if accent_custom and len(accent_custom) in (3, 6) and all(ch in "0123456789abcdefABCDEF" for ch in accent_custom):
        tpl["accent"] = "#" + accent_custom
        tpl["linea"] = "#" + accent_custom
    footer_custom = request.args.get("footer", "").strip()
    logo_url = request.args.get("logo", "").strip()

    ACCENT = HexColor(tpl["accent"]); INK = HexColor(tpl["ink"]); LINEA = HexColor(tpl["linea"])
    is_serif = "serif" in tpl["font"].lower() or "georgia" in tpl["font"].lower()
    font_titolo = "Times-Bold" if is_serif else "Helvetica-Bold"
    font_body = "Times-Roman" if is_serif else "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20*mm, bottomMargin=18*mm,
                            leftMargin=22*mm, rightMargin=22*mm, title=str(titolo or "Menu"))
    styles = getSampleStyleSheet()
    st_titolo = ParagraphStyle("Tit", parent=styles["Title"], fontName=font_titolo,
                               textColor=ACCENT, fontSize=26, spaceAfter=2, alignment=1)
    st_locale = ParagraphStyle("Loc", parent=styles["Normal"], fontName=font_body,
                               textColor=INK, fontSize=11, alignment=1, spaceAfter=6)
    st_sezione = ParagraphStyle("Sez", parent=styles["Heading2"], fontName=font_titolo,
                                textColor=ACCENT, fontSize=14, spaceBefore=12, spaceAfter=4)
    st_nome = ParagraphStyle("Nome", parent=styles["Normal"], fontName=font_body,
                             textColor=INK, fontSize=11, leading=14)
    st_prezzo = ParagraphStyle("Prz", parent=styles["Normal"], fontName=font_titolo,
                               textColor=ACCENT, fontSize=11, alignment=2)
    st_desc = ParagraphStyle("Desc", parent=styles["Normal"], fontName=font_body,
                             textColor=HexColor("#666666"), fontSize=8.5, leading=11, spaceAfter=3)
    st_footer = ParagraphStyle("Foot", parent=styles["Normal"], fontName=font_body,
                               textColor=HexColor("#888888"), fontSize=8, alignment=1)

    story = []
    def esc(s): return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # logo (se url fornito e scaricabile)
    if logo_url:
        try:
            import urllib.request
            req = urllib.request.Request(logo_url, headers={"User-Agent": "Mozilla/5.0"})
            logo_data = io.BytesIO(urllib.request.urlopen(req, timeout=8).read())
            im = RLImage(logo_data); im._restrictSize(45*mm, 25*mm); im.hAlign = "CENTER"
            story.append(im); story.append(Spacer(1, 6))
        except Exception:
            pass

    story.append(Paragraph(esc(titolo or "Menu"), st_titolo))
    if locale:
        story.append(Paragraph(esc(locale), st_locale))
    story.append(HRFlowable(width="40%", thickness=1.2, color=LINEA, spaceBefore=4, spaceAfter=8, hAlign="CENTER"))

    # raggruppo per sezione
    def riga_voce(v):
        nome = esc(v.get("nome", "")); prezzo = esc(v.get("prezzo", "")); desc = esc(v.get("descrizione", ""))
        t = Table([[Paragraph(nome, st_nome), Paragraph(prezzo, st_prezzo)]],
                  colWidths=[125*mm, 35*mm])
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),
                               ("RIGHTPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),2),
                               ("BOTTOMPADDING",(0,0),(-1,-1),0)]))
        story.append(t)
        if desc:
            story.append(Paragraph(desc, st_desc))

    sezioni = {}
    ordine_sez = []
    for v in voci:
        s = v.get("sezione") or ""
        if s not in sezioni:
            sezioni[s] = []; ordine_sez.append(s)
        sezioni[s].append(v)

    if len(ordine_sez) == 1 and ordine_sez[0] == "":
        for v in voci: riga_voce(v)
    else:
        for s in ordine_sez:
            if s:
                story.append(Paragraph(esc(s), st_sezione))
            for v in sezioni[s]: riga_voce(v)

    if footer_custom or note:
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="30%", thickness=0.6, color=LINEA, spaceBefore=2, spaceAfter=6, hAlign="CENTER"))
        story.append(Paragraph(esc(footer_custom or note), st_footer))

    doc.build(story)
    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"menu-{esc(titolo or mid)[:30].replace(' ','-')}.pdf")
