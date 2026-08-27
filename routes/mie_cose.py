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
