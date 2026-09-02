"""Le cose dell'utente: ricette salvate, per device_id. Chiude il buco 'salvo ma sparisce'."""
import json
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn

bp_mie = Blueprint("mie_cose", __name__)

def _ensure_tabella():
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ricette_salvate (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                ricetta_id TEXT NOT NULL,
                nome TEXT,
                dati JSONB,
                creato_il TIMESTAMP DEFAULT NOW(),
                UNIQUE(device_id, ricetta_id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ricette_salvate_device ON ricette_salvate(device_id)")
        conn.commit()
    finally:
        _release_conn(conn)

def _device():
    # header per primo (usato da tutti), poi body json, poi query param
    dev = request.headers.get("X-Device-Id")
    if dev:
        return dev
    if request.is_json:
        dev = (request.json or {}).get("device_id")
        if dev:
            return dev
    return request.args.get("device_id") or ""

@bp_mie.route("/v1/ricette/salva", methods=["POST"])
def salva_ricetta_utente():
    """Salva una ricetta tra 'le mie'. Body: {ricetta_id?, nome, dati:{...}}.
    Traccia chi (device_id) ha salvato cosa, così la ritrova nel Quaderno."""
    _ensure_tabella()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device_id mancante"}), 400
    body = request.json or {}
    dati = body.get("dati") or body  # accetta l'intera ricetta o un campo 'dati'
    nome = body.get("nome") or dati.get("nome") or "Ricetta"
    ric_id = body.get("ricetta_id") or dati.get("id") or ("ric-user-" + str(abs(hash(nome)) % 10**8))
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO ricette_salvate (device_id, ricetta_id, nome, dati)
            VALUES (%s,%s,%s,%s::jsonb)
            ON CONFLICT (device_id, ricetta_id) DO UPDATE SET nome=EXCLUDED.nome, dati=EXCLUDED.dati
        """, (dev, ric_id, nome, json.dumps(dati, ensure_ascii=False)))
        conn.commit()
        return jsonify({"ok": True, "ricetta_id": ric_id, "nome": nome})
    finally:
        _release_conn(conn)

@bp_mie.route("/v1/ricette/le-mie", methods=["GET"])
def le_mie_ricette():
    """Restituisce le ricette salvate dall'utente (per device_id). Per la sezione Ricette del Quaderno."""
    _ensure_tabella()
    dev = _device()
    if not dev:
        return jsonify({"ricette": [], "totale": 0})
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""SELECT ricetta_id, nome, dati, creato_il FROM ricette_salvate
                       WHERE device_id=%s ORDER BY creato_il DESC""", (dev,))
        rows = cur.fetchall()
        ricette = []
        for r in rows:
            dati = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
            ricette.append({"ricetta_id": r[0], "nome": r[1], "dati": dati,
                            "creato_il": str(r[3]) if r[3] else None})
        return jsonify({"ricette": ricette, "totale": len(ricette)})
    finally:
        _release_conn(conn)

@bp_mie.route("/v1/ricette/rimuovi", methods=["POST"])
def rimuovi_ricetta_utente():
    """Rimuove una ricetta dalle 'mie'. Body: {ricetta_id}."""
    _ensure_tabella()
    dev = _device()
    ric_id = (request.json or {}).get("ricetta_id", "")
    if not dev or not ric_id:
        return jsonify({"errore": "device_id o ricetta_id mancante"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM ricette_salvate WHERE device_id=%s AND ricetta_id=%s", (dev, ric_id))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        _release_conn(conn)


@bp_mie.route("/v1/ricette/food-cost", methods=["POST"])
def ricetta_food_cost():
    """Food cost di una ricetta generata/salvata, dagli ingredienti nel body.
    NON richiede autenticazione né exp_id — pensato per la scheda ricetta.
    Body: {ingredienti:[{nome, quantita, unita}], porzioni?, prezzo_vendita?}
    Restituisce sempre i prezzi_vendita_suggeriti, anche senza prezzo_vendita in input."""
    from config import DATABASE_URL
    if not DATABASE_URL:
        return jsonify({"errore": "database non disponibile"}), 503
    try:
        from cifra_utils import _stima_costo_categoria
    except Exception:
        def _stima_costo_categoria(cat): return 5.0
    body = request.json or {}
    ingredienti_input = body.get("ingredienti", [])
    porzioni = float(body.get("porzioni", 1) or 1)

    def _to_grammi(q, u):
        """Normalizza una quantità in grammi. u = unita (g, ml, kg, cl, l, pz, ...)."""
        try:
            q = float(str(q).replace(",", ".").strip())
        except Exception:
            return 0.0
        u = (u or "").lower().strip()
        if u in ("g", "gr", "grammi", "grammo"): return q
        if u in ("kg", "kilo", "kg."): return q * 1000
        if u in ("ml", "millilitri"): return q          # 1ml ≈ 1g liquidi
        if u in ("cl",): return q * 10
        if u in ("l", "lt", "litri", "litro"): return q * 1000
        if u in ("oz",): return q * 28.35
        if u in ("pz", "pezzo", "pezzi", "unità", "unita", ""): return q * 100  # stima pezzo
        if u in ("q.b.", "qb", "qb."): return 2         # trascurabile
        return q  # default: tratto come grammi

    conn = _get_conn(); cur = conn.cursor()
    try:
        import json as _j
        dettaglio = []
        costo_totale = 0.0
        for ing in ingredienti_input:
            nome = (ing.get("nome", "") if isinstance(ing, dict) else str(ing)).lower().strip()
            if not nome:
                continue
            qty_totale_g = _to_grammi(ing.get("quantita", ing.get("quantita_g", 0)),
                                      ing.get("unita", ing.get("unità", "g")))
            nome_id = f"ing-{nome.replace(' ','-')}"
            cur.execute("""
                SELECT name, data FROM nodes
                WHERE type='Ingrediente'
                AND (lower(id)=lower(%s) OR lower(data->>'aliases') LIKE lower(%s)
                     OR lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                ORDER BY CASE WHEN lower(id)=lower(%s) THEN 1
                              WHEN lower(data->>'aliases') LIKE lower(%s) THEN 2 ELSE 3 END
                LIMIT 1
            """, (nome_id, f'%"{nome}"%', f"%{nome}%", f"%{nome_id}%", nome_id, f'%"{nome}"%'))
            ing_row = cur.fetchone()
            costo_eur_kg = 5.0; fonte = "stima generica"; categoria = ""
            if ing_row:
                d = ing_row[1] if isinstance(ing_row[1], dict) else _j.loads(ing_row[1] or "{}")
                categoria = d.get("categoria", "")
                costo_eur_kg = d.get("costo_mercato_eur") or _stima_costo_categoria(categoria)
                fonte = "Matter Lab / ISMEA orientativo"
            costo_porzione = (qty_totale_g / 1000) * costo_eur_kg
            costo_totale += costo_porzione
            dettaglio.append({
                "ingrediente": nome, "quantita_g": round(qty_totale_g, 1),
                "costo_eur_kg": costo_eur_kg, "costo_porzione_eur": round(costo_porzione, 3),
                "categoria": categoria, "fonte": fonte
            })
        # costo per porzione
        costo_per_porzione = costo_totale / porzioni if porzioni > 0 else costo_totale
        prezzo_vendita = float(body.get("prezzo_vendita", 0) or 0)
        food_cost_pct = (costo_per_porzione / prezzo_vendita * 100) if prezzo_vendita > 0 else None
        # prezzi suggeriti SEMPRE presenti (anche senza prezzo_vendita in input)
        base = costo_per_porzione if costo_per_porzione > 0 else costo_totale
        suggeriti = {
            "fc_25pct": round(base / 0.25, 2),
            "fc_30pct": round(base / 0.30, 2),
            "fc_33pct": round(base / 0.33, 2),
        }
        return jsonify({
            "costo_totale_eur": round(costo_totale, 3),
            "costo_per_porzione_eur": round(costo_per_porzione, 3),
            "porzioni": porzioni,
            "dettaglio": dettaglio,
            "food_cost_pct": round(food_cost_pct, 1) if food_cost_pct else None,
            "prezzo_vendita": prezzo_vendita or None,
            "prezzi_vendita_suggeriti": suggeriti,
            "nota": "Prezzi orientativi ISMEA. Per prezzi fornitore reali usa Cifra.",
            "fonte": "Matter Lab / ISMEA"
        })
    finally:
        _release_conn(conn)


# ============================================================
# STORICO MISURE — il cuore del Quaderno: l'utente salva i bersagli che misura
# al banco, e ne rivede l'evoluzione nel tempo ("impasto: 26° a sett, 24° a ott").
# Alimenta la North Star: bersagli misurati/salvati a settimana.
# ============================================================

def _ensure_misure():
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS misure_salvate (
                id SERIAL PRIMARY KEY,
                device_id TEXT NOT NULL,
                fenomeno TEXT NOT NULL,
                fenomeno_id TEXT,
                valore TEXT NOT NULL,
                unita TEXT,
                bersaglio TEXT,
                nota TEXT,
                creato_il TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_misure_dev ON misure_salvate(device_id, fenomeno)")
        conn.commit()
    finally:
        _release_conn(conn)


@bp_mie.route("/v1/misure/salva", methods=["POST"])
def salva_misura():
    """Salva una misura fatta al banco. Body:
    {fenomeno:'Temperatura impasto', fenomeno_id?, valore:'24', unita:'°C', bersaglio?:'22-24', nota?}.
    device_id da header X-Device-Id. È il gesto centrale: 'ho misurato, salvo nel Quaderno'."""
    _ensure_misure()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device_id mancante"}), 400
    b = request.json or {}
    fenomeno = (b.get("fenomeno") or "").strip()
    valore = (b.get("valore") or "").strip()
    if not fenomeno or not valore:
        return jsonify({"errore": "fenomeno e valore obbligatori"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO misure_salvate (device_id, fenomeno, fenomeno_id, valore, unita, bersaglio, nota)
            VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id, creato_il
        """, (dev, fenomeno[:120], (b.get("fenomeno_id") or None), valore[:40],
              (b.get("unita") or "")[:20], (b.get("bersaglio") or "")[:40], (b.get("nota") or "")[:300]))
        r = cur.fetchone()
        conn.commit()
        # segnale North Star: una misura salvata (per il pannello, via funnel opzionale)
        try:
            import oss
            oss.funnel_write("misura_salvata", user_id=None, email=None)
        except Exception:
            pass
        return jsonify({"ok": True, "id": r[0], "creato_il": r[1].isoformat() if r[1] else None})
    finally:
        _release_conn(conn)


@bp_mie.route("/v1/quaderno/insight", methods=["GET"])
def quaderno_insight():
    """Organizer: insight-trend automatici per la home del Quaderno. Rileva i fenomeni dove le
    misure stanno cambiando in modo significativo e genera un avviso ('la tua ganache è più stabile',
    'l'acidità del lime è aumentata'). Deterministico, niente AI. device_id da header."""
    _ensure_misure()
    dev = _device()
    lang = (request.args.get("lang") or "it").strip().lower()
    if not dev:
        return jsonify({"insight": []})
    conn = _get_conn(); cur = conn.cursor()
    try:
        # per ogni fenomeno con almeno 3 misure, guardo la tendenza (prime vs ultime)
        cur.execute("""
            SELECT fenomeno, ARRAY_AGG(valore ORDER BY creato_il ASC) AS valori,
                   ARRAY_AGG(unita ORDER BY creato_il ASC) AS unita,
                   MAX(bersaglio) AS bersaglio, COUNT(*) AS n
            FROM misure_salvate WHERE device_id=%s
            GROUP BY fenomeno HAVING COUNT(*) >= 3
        """, (dev,))
        insight = []
        import re as _re
        for row in cur.fetchall():
            fen, valori, unita_arr, bersaglio, n = row
            # estraggo i numeri dai valori (possono avere unità nel testo)
            nums = []
            for v in valori:
                m = _re.search(r"-?\d+[.,]?\d*", str(v))
                if m:
                    try: nums.append(float(m.group(0).replace(",", ".")))
                    except Exception: pass
            if len(nums) < 3:
                continue
            uni = (unita_arr[-1] if unita_arr else "") or ""
            # confronto media delle prime metà vs seconda metà
            meta = len(nums) // 2
            prima = sum(nums[:meta]) / meta if meta else nums[0]
            dopo = sum(nums[meta:]) / (len(nums) - meta)
            if prima == 0:
                continue
            delta_perc = round((dopo - prima) / abs(prima) * 100, 1)
            if abs(delta_perc) < 5:
                # stabile → insight positivo di stabilità
                insight.append({
                    "tipo": "stabilita", "fenomeno": fen,
                    "testo": f"La tua misura di {fen} è stabile ({nums[-1]}{uni}): controllo costante, buon segno.",
                })
            else:
                direzione = "aumentata" if delta_perc > 0 else "diminuita"
                insight.append({
                    "tipo": "trend", "fenomeno": fen,
                    "delta_perc": delta_perc,
                    "testo": f"La tua misura di {fen} è {direzione} del {abs(delta_perc)}% "
                             f"nelle ultime rilevazioni (ora {nums[-1]}{uni}). Tienila d'occhio.",
                })
        cur.close(); _release_conn(conn)
        # ordino: prima i trend (più urgenti), poi le stabilità
        insight.sort(key=lambda x: 0 if x["tipo"] == "trend" else 1)
        insight = insight[:5]
        if lang in ("en", "es"):
            try:
                from traduzioni import traduci
                for it in insight:
                    if it.get("testo"):
                        it["testo"] = traduci(it["testo"], lang)
            except Exception:
                pass
        return jsonify({"insight": insight})
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"insight": [], "errore": str(e)[:80]}), 200


@bp_mie.route("/v1/misure/storico", methods=["GET"])
def storico_misure():
    """Storico di un fenomeno nel tempo (l'evoluzione: '26°→24°').
    ?fenomeno=<nome> — restituisce le misure di quel fenomeno in ordine cronologico.
    Senza ?fenomeno, restituisce l'elenco dei fenomeni misurati (per la lista del Quaderno)."""
    _ensure_misure()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device_id mancante"}), 400
    fenomeno = (request.args.get("fenomeno") or "").strip()
    conn = _get_conn(); cur = conn.cursor()
    try:
        if fenomeno:
            # serie temporale di UN fenomeno (per il grafico dell'evoluzione)
            cur.execute("""
                SELECT valore, unita, bersaglio, nota, creato_il
                FROM misure_salvate WHERE device_id=%s AND fenomeno=%s
                ORDER BY creato_il ASC
            """, (dev, fenomeno))
            serie = [{"valore": r[0], "unita": r[1], "bersaglio": r[2], "nota": r[3],
                      "data": r[4].isoformat() if r[4] else None} for r in cur.fetchall()]
            # calcolo l'evoluzione: primo vs ultimo (il "26°→24°")
            evoluzione = None
            if len(serie) >= 2:
                evoluzione = {"da": serie[0]["valore"], "a": serie[-1]["valore"],
                              "unita": serie[-1]["unita"], "n_misure": len(serie)}
            return jsonify({"fenomeno": fenomeno, "serie": serie, "evoluzione": evoluzione})
        else:
            # elenco fenomeni misurati, con conteggio e ultima misura (per la lista)
            cur.execute("""
                SELECT fenomeno, COUNT(*) AS n,
                       (ARRAY_AGG(valore ORDER BY creato_il DESC))[1] AS ultimo,
                       (ARRAY_AGG(unita ORDER BY creato_il DESC))[1] AS unita,
                       MAX(creato_il) AS ultima_data
                FROM misure_salvate WHERE device_id=%s
                GROUP BY fenomeno ORDER BY ultima_data DESC
            """, (dev,))
            lista = [{"fenomeno": r[0], "n_misure": r[1], "ultimo_valore": r[2],
                      "unita": r[3], "ultima_data": r[4].isoformat() if r[4] else None}
                     for r in cur.fetchall()]
            return jsonify({"fenomeni": lista, "totale_misure": sum(x["n_misure"] for x in lista)})
    finally:
        _release_conn(conn)


@bp_mie.route("/v1/misure/rimuovi", methods=["POST"])
def rimuovi_misura():
    """Rimuove una misura per id. Body: {id}."""
    _ensure_misure()
    dev = _device()
    if not dev:
        return jsonify({"errore": "device_id mancante"}), 400
    mid = (request.json or {}).get("id")
    if not mid:
        return jsonify({"errore": "id mancante"}), 400
    conn = _get_conn(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM misure_salvate WHERE id=%s AND device_id=%s", (mid, dev))
        conn.commit()
        return jsonify({"ok": True})
    finally:
        _release_conn(conn)


@bp_mie.route("/v1/miei-dati/export", methods=["GET"])
def export_dati_utente():
    """GDPR + utilità: esporta TUTTI i dati dell'utente (device_id) in un JSON scaricabile.
    Ricette salvate, misure, esperimenti, menu. Diritto alla portabilità dei dati (art. 20 GDPR)."""
    dev = _device()
    if not dev:
        return jsonify({"errore": "device non identificato"}), 400
    conn = _get_conn()
    export = {"device_id": dev, "esportato_il": __import__("datetime").datetime.now().isoformat(),
              "ricette_salvate": [], "misure": [], "esperimenti": [], "menu": []}
    try:
        cur = conn.cursor()
        # ricette salvate
        try:
            cur.execute("SELECT nome, dati, creato_il FROM ricette_salvate WHERE device_id=%s", (dev,))
            for r in cur.fetchall():
                export["ricette_salvate"].append({"nome": r[0], "dati": r[1],
                    "creato_il": r[2].isoformat() if r[2] else None})
        except Exception:
            pass
        # misure
        try:
            cur.execute("SELECT fenomeno, valore, unita, bersaglio, creato_il FROM misure_salvate WHERE device_id=%s", (dev,))
            for r in cur.fetchall():
                export["misure"].append({"fenomeno": r[0], "valore": r[1], "unita": r[2],
                    "bersaglio": r[3], "data": r[4].isoformat() if r[4] else None})
        except Exception:
            pass
        # esperimenti completati
        try:
            cur.execute("SELECT fenomeno_id, esito, nota, completato_il FROM esperimenti_completati WHERE device_id=%s", (dev,))
            for r in cur.fetchall():
                export["esperimenti"].append({"fenomeno": r[0], "esito": r[1], "nota": r[2],
                    "data": r[3].isoformat() if r[3] else None})
        except Exception:
            pass
        cur.close(); _release_conn(conn)
        export["totali"] = {k: len(v) for k, v in export.items() if isinstance(v, list)}
        from flask import Response
        import json as _j
        resp = Response(_j.dumps(export, ensure_ascii=False, indent=2), mimetype="application/json")
        resp.headers["Content-Disposition"] = "attachment; filename=matter-bench-miei-dati.json"
        return resp
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)[:120]}), 200
