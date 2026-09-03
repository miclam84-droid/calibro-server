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


@bp_mie.route("/v1/chat/salva", methods=["POST"])
def salva_conversazione():
    """Salva una conversazione chat (per ritrovarla dopo). Body: {titolo, messaggi:[{ruolo,testo}]}.
    Le chat NON si perdono più al reload — l'utente costruisce il suo archivio di domande/risposte."""
    dev = _device()
    if not dev:
        return jsonify({"errore": "device non identificato"}), 400
    body = request.json or {}
    messaggi = body.get("messaggi", [])
    if not messaggi:
        return jsonify({"errore": "conversazione vuota"}), 400
    # titolo: prima domanda dell'utente (troncata) se non fornito
    titolo = (body.get("titolo") or "").strip()
    if not titolo:
        for m in messaggi:
            if m.get("ruolo") == "user" or m.get("q"):
                titolo = (m.get("testo") or m.get("q") or "")[:60]; break
        titolo = titolo or "Conversazione"
    # TAG AUTOMATICO (revisori): deduco l'ambito dal contenuto per ritrovare le chat per argomento.
    _testo_tot = " ".join((m.get("testo") or m.get("q") or m.get("r") or "") for m in messaggi).lower()
    _TAG_KW = {
        "bar": ("cocktail", "drink", "gin", "sour", "negroni", "shake", "diluizione", "bitter", "vermouth", "amaro"),
        "forno": ("impasto", "lievito", "farina", "pane", "pizza", "focaccia", "idratazione", "glutine", "maglia"),
        "cucina": ("carne", "pesce", "cottura", "brasato", "risotto", "salsa", "maillard", "sonda", "brodo"),
        "pasticceria": ("crema", "cioccolato", "ganache", "meringa", "zucchero", "tuorlo", "spuma", "gelatina"),
        "caffè": ("caffè", "espresso", "estrazione", "tostatura", "brew"),
        "gelateria": ("gelato", "sorbetto", "mantecazione", "cristalli", "overrun"),
        "vino": ("vino", "barolo", "servizio", "tannini", "affinamento", "solfiti"),
    }
    tag = ""
    _best = 0
    for _t, _kw in _TAG_KW.items():
        _score = sum(1 for k in _kw if k in _testo_tot)
        if _score > _best:
            _best = _score; tag = _t
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS chat_salvate (
            id SERIAL PRIMARY KEY, device_id TEXT, titolo TEXT, messaggi JSONB, tag TEXT,
            creato_il TIMESTAMP DEFAULT NOW())""")
        cur.execute("ALTER TABLE chat_salvate ADD COLUMN IF NOT EXISTS tag TEXT")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_dev ON chat_salvate(device_id)")
        import json as _j
        cur.execute("INSERT INTO chat_salvate (device_id, titolo, messaggi, tag) VALUES (%s,%s,%s::jsonb,%s) RETURNING id",
                    (dev, titolo, _j.dumps(messaggi, ensure_ascii=False), tag))
        cid = cur.fetchone()[0]
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True, "id": cid, "titolo": titolo, "tag": tag})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"errore": str(e)[:120]}), 200


@bp_mie.route("/v1/chat/mie", methods=["GET"])
def mie_conversazioni():
    """Elenco delle conversazioni salvate dell'utente (titolo + data). Per ritrovare le chat."""
    dev = _device()
    if not dev:
        return jsonify({"conversazioni": []})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, titolo, creato_il, tag FROM chat_salvate WHERE device_id=%s ORDER BY creato_il DESC LIMIT 50", (dev,))
        out = [{"id": r[0], "titolo": r[1], "data": r[2].isoformat() if r[2] else None, "tag": r[3] or ""} for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
        return jsonify({"conversazioni": out, "totale": len(out)})
    except Exception:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"conversazioni": []})


@bp_mie.route("/v1/chat/<int:cid>", methods=["GET"])
def leggi_conversazione(cid):
    """Riapre una conversazione salvata coi suoi messaggi."""
    dev = _device()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT titolo, messaggi FROM chat_salvate WHERE id=%s AND device_id=%s", (cid, dev))
        r = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not r:
            return jsonify({"errore": "conversazione non trovata"}), 404
        return jsonify({"titolo": r[0], "messaggi": r[1]})
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"errore": str(e)[:100]}), 200


@bp_mie.route("/v1/dna-professionale", methods=["GET"])
def dna_professionale():
    """DNA Professionale: analizza le misure/esperimenti dell'utente e genera il suo profilo con
    pattern reali (medie, tendenze, zone di lavoro). 'Matter ti conosce come professionista.'
    È il motore del rinnovo: più usi l'app, più ti conosce. Richiede almeno qualche misura."""
    dev = _device()
    if not dev:
        return jsonify({"errore": "device non identificato"}), 400
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # tutte le misure dell'utente, per fenomeno
        cur.execute("""SELECT fenomeno, valore, unita, bersaglio, creato_il
                       FROM misure_salvate WHERE device_id=%s ORDER BY fenomeno, creato_il""", (dev,))
        righe = cur.fetchall()
        if not righe:
            cur.close(); _release_conn(conn)
            return jsonify({"pronto": False, "messaggio": "Registra qualche misura al banco e Matter "
                            "inizierà a conoscerti: dopo alcune misure vedrai qui il tuo profilo professionale."})
        # raggruppo per fenomeno e calcolo i pattern
        import re as _re
        from collections import defaultdict
        per_fen = defaultdict(list)
        for r in righe:
            fen = r[0]; val_raw = r[1]; uni = r[2] or ""; ber = r[3] or ""
            # estraggo il numero dal valore
            m = _re.search(r"-?\d+[.,]?\d*", str(val_raw))
            if m:
                try:
                    v = float(m.group(0).replace(",", "."))
                    per_fen[fen].append({"v": v, "uni": uni, "ber": ber, "data": r[4]})
                except Exception:
                    pass
        pattern = []
        for fen, misure in per_fen.items():
            if len(misure) < 1:
                continue
            valori = [m["v"] for m in misure]
            media = round(sum(valori) / len(valori), 1)
            uni = misure[0]["uni"]
            ber = misure[0]["ber"]
            n = len(misure)
            # GRADO DI AFFIDABILITÀ (Gemini + coerente col Confidence Layer):
            # <5 misure = ipotesi, 5-10 = indicativo, >10 = consolidato.
            if n < 5:
                affidabilita = "ipotesi"
            elif n <= 10:
                affidabilita = "indicativo"
            else:
                affidabilita = "consolidato"
            p = {"fenomeno": fen, "n_misure": n, "media": media, "unita": uni,
                 "affidabilita": affidabilita}
            # tendenza (almeno 3 misure)
            if n >= 3:
                delta = valori[-1] - valori[0]
                if abs(delta) >= max(0.5, abs(media) * 0.03):
                    verso = "aumentato" if delta > 0 else "abbassato"
                    p["tendenza"] = f"Hai {verso} {fen.lower()} di {abs(round(delta,1))}{uni} nel tempo."
            # zona di lavoro
            if n >= 2:
                p["zona"] = f"Lavori {fen.lower()} tra {round(min(valori),1)} e {round(max(valori),1)}{uni} (media {media}{uni})."
            if ber:
                p["nota_bersaglio"] = f"Bersaglio consigliato: {ber}{uni}."
            # INSIGHT AZIONABILE (OpenAI: non descrittivo ma actionable) — solo se abbastanza dati
            if n >= 5:
                _vmin, _vmax = round(min(valori), 1), round(max(valori), 1)
                if _vmax > _vmin:
                    p["azione"] = (f"La tua zona migliore per {fen.lower()} sembra intorno a {media}{uni}: "
                                   f"prova a restare vicino a questo valore per costanza, e annota il risultato.")
            pattern.append(p)
        # frase-firma del DNA
        cur.execute("SELECT COUNT(DISTINCT fenomeno), COUNT(*) FROM misure_salvate WHERE device_id=%s", (dev,))
        _c = cur.fetchone()
        n_fen = _c[0] if _c else 0; n_tot = _c[1] if _c else 0
        cur.close(); _release_conn(conn)
        # suggerimento: il fenomeno più misurato
        top = max(pattern, key=lambda x: x["n_misure"]) if pattern else None
        suggerimento = None
        if top:
            suggerimento = f"Il parametro che segui di più è {top['fenomeno'].lower()}: sei un professionista che tiene sotto controllo questo aspetto. Continua a misurarlo per affinare la tua costanza."
        return jsonify({
            "pronto": True,
            "riepilogo": {"fenomeni_seguiti": n_fen, "misure_totali": n_tot},
            "pattern": pattern,
            "suggerimento": suggerimento,
            "firma": "Matter ti conosce dal tuo lavoro al banco: questo profilo cresce a ogni misura che salvi."
        })
    except Exception as e:
        try: _release_conn(conn)
        except Exception: pass
        import traceback
        return jsonify({"errore": str(e)[:120], "tb": traceback.format_exc()[-200:]}), 200


@bp_mie.route("/v1/dna-contesto", methods=["GET"])
def dna_contesto():
    """Contesto DNA per un fenomeno specifico — da iniettare nei calcolatori e nella chat.
    Es. aprendo il calcolatore idratazione: 'Di solito lavori al 71% (18 misure)'.
    ?fenomeno=Idratazione impasto  → {ha_dati, media, zona, frase} (o ha_dati:false)."""
    dev = _device()
    fen = (request.args.get("fenomeno") or "").strip()
    if not dev or not fen:
        return jsonify({"ha_dati": False})
    conn = _get_conn()
    try:
        import re as _re
        cur = conn.cursor()
        cur.execute("""SELECT valore, unita FROM misure_salvate
                       WHERE device_id=%s AND lower(fenomeno)=lower(%s) ORDER BY creato_il""", (dev, fen))
        righe = cur.fetchall()
        cur.close(); _release_conn(conn)
        valori = []
        uni = ""
        for r in righe:
            m = _re.search(r"-?\d+[.,]?\d*", str(r[0]))
            if m:
                try:
                    valori.append(float(m.group(0).replace(",", "."))); uni = r[1] or uni
                except Exception:
                    pass
        # soglia: sotto 3 misure non do contesto (troppo rumore)
        if len(valori) < 3:
            return jsonify({"ha_dati": False, "n_misure": len(valori)})
        media = round(sum(valori) / len(valori), 1)
        n = len(valori)
        affid = "ipotesi" if n < 5 else ("indicativo" if n <= 10 else "consolidato")
        frase = f"Di solito lavori {fen.lower()} intorno a {media}{uni} ({n} misure)."
        return jsonify({"ha_dati": True, "media": media, "unita": uni, "n_misure": n,
                        "affidabilita": affid, "frase": frase,
                        "min": round(min(valori), 1), "max": round(max(valori), 1),
                        # alias per compatibilità col frontend (nomi campo alternativi)
                        "valore_medio": media, "unita_misura": uni, "misure_totali": n})
    except Exception:
        try: _release_conn(conn)
        except Exception: pass
        return jsonify({"ha_dati": False})
