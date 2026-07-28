# ============================================================
# routes/cifra.py — integrazione Matter→Cifra: ricette, token SSO, sicurezza, quaderno.
# Dipende da: db, auth, cifra_utils, contenuto.
from flask import Blueprint, request, jsonify
from db import carica_grafo, _dati, _get_conn, _release_conn
from auth import _utente_da_token, _genera_token
from cifra_utils import _auth_cifra, _stima_costo_categoria, _calcola_profilo_sicurezza
from contenuto import _scheda_lang, _numero_bersaglio
from config import DATABASE_URL
import os, json, secrets
bp = Blueprint("cifra", __name__)


@bp.route("/v1/quaderno", methods=["GET"])
def quaderno_lista():
    """AC3 — Lista esperimenti salvati dall'utente."""
    token = (request.headers.get("Authorization","").replace("Bearer ","") or
               request.headers.get("X-Token","") or
               (request.json or {}).get("token",""))
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"esperimenti":[]})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts, ph, brix, abv, ey_perc,
                   temperatura, idratazione, costo_mercato_eur
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC LIMIT 50
        """, (str(user_id),))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols,[str(v) if v is not None else None for v in r])) for r in cur.fetchall()]
        cur.close(); _release_conn(conn)
        return jsonify({"esperimenti":rows,"totale":len(rows)})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/quaderno", methods=["POST"])
def quaderno_salva():
    """AC3 — Salva un nuovo esperimento nel quaderno."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    body = request.json or {}
    nome = body.get("nome","").strip()
    if not nome:
        return jsonify({"errore":"nome esperimento obbligatorio"}), 400
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO esperimenti
            (nome, disciplina, note, ph, brix, abv, ey_perc, tds_perc,
             temperatura, idratazione, ingredienti, fenomeni,
             costo_mercato_eur, area_mercato, user_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            nome,
            body.get("disciplina"),
            body.get("note"),
            body.get("ph"), body.get("brix"), body.get("abv"),
            body.get("ey_perc"), body.get("tds_perc"),
            body.get("temperatura"), body.get("idratazione"),
            json.dumps(body.get("ingredienti",[])),
            json.dumps(body.get("fenomeni",[])),
            body.get("costo_mercato_eur"),
            body.get("area_mercato","it"),
            str(user_id)
        ))
        exp_id = cur.fetchone()[0]
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"id":exp_id,"ok":True})
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/prezzi/<ingrediente>")
def prezzi_ingrediente(ingrediente):
    """Restituisce il prezzo orientativo di mercato per un ingrediente.
    Cerca prima nei nodi Ingrediente del grafo (dataset Matter Lab),
    poi nei nodi Prodotto con costo_mercato_eur popolato."""
    lang = request.args.get("lang","it")
    ing_norm = ingrediente.lower().replace("-"," ")
    if not DATABASE_URL:
        return jsonify({"ingrediente":ingrediente,"prezzi":[]})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # Cerca nel dataset proprietario (nodi Ingrediente)
        cur.execute("""
            SELECT id, name, data
            FROM nodes
            WHERE type='Ingrediente'
            AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
            LIMIT 3
        """, (f"%{ing_norm}%", f"%ing-{ing_norm.replace(' ','-')}%"))
        rows = cur.fetchall()
        prezzi = []
        for row in rows:
            d = row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}")
            params = d.get("parametri_fisici", {})
            # Cerca costo nei parametri fisici del profilo
            costo = d.get("costo_mercato_eur") or params.get("costo_mercato_eur")
            if not costo:
                # Stima da categoria
                cat = d.get("categoria","")
                costo = _stima_costo_categoria(cat)
            prezzi.append({
                "nome": row[1],
                "costo_eur_kg": costo,
                "categoria": d.get("categoria",""),
                "fonte": "Matter Lab / ISMEA orientativo",
                "nota": "Prezzo orientativo di mercato. Per prezzi fornitore reali usa Cifra."
            })
        cur.close(); _release_conn(conn)
        return jsonify({"ingrediente":ingrediente,"prezzi":prezzi})
    except Exception as e:
        return jsonify({"ingrediente":ingrediente,"prezzi":[],"errore":str(e)})

@bp.route("/v1/quaderno/<int:exp_id>/costo", methods=["GET","POST"])
def quaderno_calcola_costo(exp_id):
    """Calcola il food/drink cost di un esperimento nel quaderno.

    GET: calcola costo con ingredienti e quantità già salvati
    POST: calcola costo con ingredienti passati nel body
    {
      "ingredienti": [
        {"nome": "bourbon", "quantita_ml": 50},
        {"nome": "lime", "quantita_g": 22}
      ],
      "prezzo_vendita": 12.0  # opzionale
    }
    """
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401

    body = request.json or {}
    ingredienti_input = body.get("ingredienti", [])

    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503

    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()

        # Se GET, leggi ingredienti dall'esperimento salvato
        if request.method == "GET":
            cur.execute("SELECT ingredienti FROM esperimenti WHERE id=%s AND user_id=%s",
                       (exp_id, str(user_id)))
            row = cur.fetchone()
            if not row:
                cur.close(); _release_conn(conn)
                return jsonify({"errore":"esperimento non trovato"}), 404
            ingredienti_input = json.loads(row[0] or "[]")

        # Calcola costo per ogni ingrediente
        dettaglio = []
        costo_totale = 0.0

        for ing in ingredienti_input:
            nome = ing.get("nome","").lower()
            # Quantità — supporta ml, g, cl, oz, pz
            qty_ml = float(ing.get("quantita_ml", ing.get("ml", 0)) or 0)
            qty_g  = float(ing.get("quantita_g",  ing.get("g",  0)) or 0)
            qty_cl = float(ing.get("quantita_cl", ing.get("cl", 0)) or 0)
            qty_oz = float(ing.get("quantita_oz", ing.get("oz", 0)) or 0)
            qty_pz = float(ing.get("quantita_pz", ing.get("pz", 0)) or 0)

            # Normalizza tutto in grammi (approssimazione: 1ml ≈ 1g per liquidi)
            qty_totale_g = qty_g + qty_ml + (qty_cl * 10) + (qty_oz * 28.35) + (qty_pz * 100)

            # Cerca il prezzo nel grafo
            cur.execute("""
                SELECT name, data FROM nodes
                WHERE type='Ingrediente'
                AND (lower(name) LIKE lower(%s) OR lower(id) LIKE lower(%s))
                LIMIT 1
            """, (f"%{nome}%", f"%ing-{nome.replace(' ','-')}%"))
            ing_row = cur.fetchone()

            costo_eur_kg = 5.0  # default
            fonte = "stima generica"
            categoria = ""
            if ing_row:
                d = ing_row[1] if isinstance(ing_row[1], dict) else json.loads(ing_row[1] or "{}")
                categoria = d.get("categoria","")
                costo_eur_kg = (d.get("costo_mercato_eur") or
                               _stima_costo_categoria(categoria))
                fonte = "Matter Lab / ISMEA orientativo"

            costo_porzione = (qty_totale_g / 1000) * costo_eur_kg
            costo_totale += costo_porzione

            dettaglio.append({
                "ingrediente": nome,
                "quantita_g": round(qty_totale_g, 1),
                "costo_eur_kg": costo_eur_kg,
                "costo_porzione_eur": round(costo_porzione, 3),
                "categoria": categoria,
                "fonte": fonte
            })

        # Food cost percentuale
        prezzo_vendita = float(body.get("prezzo_vendita", 0) or 0)
        food_cost_pct = (costo_totale / prezzo_vendita * 100) if prezzo_vendita > 0 else None

        # Prezzo vendita suggerito a diversi food cost target
        suggeriti = {
            "fc_25pct": round(costo_totale / 0.25, 2),
            "fc_30pct": round(costo_totale / 0.30, 2),
            "fc_33pct": round(costo_totale / 0.33, 2),
        }

        cur.close(); _release_conn(conn)
        return jsonify({
            "exp_id": exp_id,
            "costo_totale_eur": round(costo_totale, 3),
            "dettaglio": dettaglio,
            "food_cost_pct": round(food_cost_pct, 1) if food_cost_pct else None,
            "prezzo_vendita": prezzo_vendita or None,
            "prezzi_vendita_suggeriti": suggeriti,
            "nota": "Prezzi orientativi di mercato. Per prezzi fornitore reali usa Cifra.",
            "fonte": "Matter Lab / ISMEA"
        })
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/ricetta/<int:exp_id>")
def ricetta_per_cifra(exp_id):
    """AC4 — API per Cifra: espone la ricetta fisica di un esperimento.
    Accetta sia token utente Matter che email+service key Cifra."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ingredienti, fenomeni,
                   ph, brix, abv, ey_perc, temperatura, idratazione,
                   costo_mercato_eur, area_mercato, ts
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not row:
            return jsonify({"errore":"esperimento non trovato"}), 404
        cols = [d[0] for d in cur.description] if False else [
            "id","nome","disciplina","ingredienti","fenomeni",
            "ph","brix","abv","ey_perc","temperatura","idratazione",
            "costo_mercato_eur","area_mercato","ts"
        ]
        d = dict(zip(cols, row))
        # ingredienti già in JSONB — pronti per Cifra
        return jsonify({
            "id": d["id"],
            "nome": d["nome"],
            "disciplina": d["disciplina"],
            "ingredienti": d["ingredienti"] or [],
            "misure_fisiche": {
                "ph": d["ph"], "brix": d["brix"], "abv": d["abv"],
                "ey_perc": d["ey_perc"], "temperatura": d["temperatura"],
                "idratazione": d["idratazione"]
            },
            "fenomeni": d["fenomeni"] or [],
            "costo_mercato_eur": d["costo_mercato_eur"],
            "area_mercato": d["area_mercato"],
            "ts": str(d["ts"]),
            "nota": "Matter possiede la fisica. Cifra applica i prezzi reali del fornitore."
        })
    except Exception as e:
        return jsonify({"errore":str(e)}), 500

@bp.route("/v1/ricette")
def ricette_per_cifra():
    """Lista ricette (esperimenti) dell'utente — endpoint Cifra.
    Cifra passa X-User-Email + MATTER_SERVICE_KEY.
    Restituisce solo id, nome, disciplina — Cifra chiede i dettagli per ID."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ts
            FROM esperimenti WHERE user_id=%s ORDER BY ts DESC
        """, (str(user_id),))
        rows = cur.fetchall()
        cur.close(); _release_conn(conn)
        return jsonify([{
            "id": r[0],
            "nome": r[1],
            "disciplina": r[2],
            "ts": str(r[3])
        } for r in rows])
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/sicurezza", methods=["POST"])
def sicurezza_stateless():
    """SEC15 — Endpoint stateless per Cifra.
    Calcola il profilo di sicurezza da parametri in input,
    senza che la ricetta esista su Matter.
    Auth: Authorization: Bearer {MATTER_SERVICE_KEY} (no X-User-Email richiesta).
    """
    auth = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    service_key = os.environ.get("MATTER_SERVICE_KEY", "")
    if not service_key or auth != service_key:
        return jsonify({"errore": "autenticazione richiesta"}), 401

    body = request.json or {}
    nome       = body.get("nome")
    disciplina = body.get("disciplina")
    ph         = body.get("ph")
    brix       = body.get("brix")
    aw         = body.get("aw")
    idratazione = body.get("idratazione")
    temperatura = body.get("temperatura_conservazione_c", 4.0)
    ingredienti = body.get("ingredienti", [])  # lista [{nome, quantita_g}] — per ora loggata, non usata nel calcolo

    profilo = _calcola_profilo_sicurezza(
        ph=ph, brix=brix, aw=aw, idratazione=idratazione,
        temperatura=temperatura, nome=nome, disciplina=disciplina
    )
    profilo["nome"] = nome
    profilo["disciplina"] = disciplina
    profilo["ingredienti_ricevuti"] = len(ingredienti)

    return jsonify(profilo)

@bp.route("/v1/ricetta/<int:exp_id>/sicurezza")
def ricetta_sicurezza(exp_id):
    """SEC14 — Profilo di sicurezza alimentare di un esperimento.
    Accetta sia token utente Matter che email+service key Cifra.
    Formato concordato con Cifra (tutti i campi nullable).
    I valori sono stime orientative basate su modelli scientifici —
    non sostituiscono test microbiologici né certificazioni professionali."""
    user_id = _auth_cifra()
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    if not DATABASE_URL:
        return jsonify({"errore":"database non disponibile"}), 503
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome, disciplina, ph, brix, abv,
                   temperatura, idratazione, ingredienti, fenomeni
            FROM esperimenti WHERE id=%s AND user_id=%s
        """, (exp_id, str(user_id)))
        row = cur.fetchone()
        cur.close(); _release_conn(conn)
        if not row:
            return jsonify({"errore":"esperimento non trovato"}), 404

        (rid, nome, disc, ph, brix, abv,
         temp, idratazione, ingredienti, fenomeni) = row

        profilo = _calcola_profilo_sicurezza(
            ph=ph, brix=brix, aw=None, idratazione=idratazione,
            temperatura=float(temp) if temp else 4.0,
            nome=nome, disciplina=disc
        )
        profilo["id"] = rid
        profilo["nome"] = nome
        profilo["disciplina"] = disc
        return jsonify(profilo)
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/token/generate", methods=["POST"])
def token_generate():
    """Genera un token monouso per SSO Matter → Cifra.
    Autenticato con token sessione Matter (utente loggato).
    Body: {email, ricetta_id}
    Returns: {token, expires_at}
    """
    auth = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    user_id = _utente_da_token(auth)
    if not user_id:
        return jsonify({"errore": "non autenticato"}), 401

    data = request.get_json(silent=True) or {}
    ricetta_id = data.get("ricetta_id")
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"errore": "email obbligatoria"}), 400

    token = str(uuid.uuid4())

    try:
        import datetime
        conn = _get_conn()
        cur = conn.cursor()
        # Crea tabella se non esiste
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sso_tokens (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                ricetta_id INTEGER,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        cur.execute(
            "INSERT INTO sso_tokens (token, email, ricetta_id, expires_at) VALUES (%s, %s, %s, %s)",
            (token, email, ricetta_id, expires_at)
        )
        conn.commit()
        cur.close()
        _release_conn(conn)
        return jsonify({
            "token": token,
            "expires_at": expires_at.isoformat() + "Z",
            "deep_link": f"https://cruscotto-production.up.railway.app/import?matter_token={token}&matter_email={email}" + (f"&ricetta_id={ricetta_id}" if ricetta_id else "")
        })
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/token/verify")
def token_verify():
    """Verifica un token SSO monouso (burn after read).
    Autenticato con MATTER_SERVICE_KEY.
    Query param: ?token=...
    Returns: {valid, email, ricetta_id}
    """
    service_key = os.environ.get("MATTER_SERVICE_KEY", "")
    auth = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not service_key or auth != service_key:
        return jsonify({"errore": "non autorizzato"}), 403

    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"valid": False, "errore": "token mancante"}), 400

    try:
        import datetime
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT email, ricetta_id, expires_at, used FROM sso_tokens WHERE token=%s",
            (token,)
        )
        row = cur.fetchone()

        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"valid": False, "errore": "token non trovato"})

        email, ricetta_id, expires_at, used = row["email"] if hasattr(row, "__getitem__") else row

        # Gestisci sia dict che tuple
        if isinstance(row, dict):
            email = row["email"]
            ricetta_id = row["ricetta_id"]
            expires_at = row["expires_at"]
            used = row["used"]
        else:
            email, ricetta_id, expires_at, used = row

        if used:
            cur.close(); _release_conn(conn)
            return jsonify({"valid": False, "errore": "token già usato"})

        now = datetime.datetime.utcnow()
        if isinstance(expires_at, str):
            expires_at = datetime.datetime.fromisoformat(expires_at.replace("Z", ""))
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)

        if now > expires_at:
            cur.close(); _release_conn(conn)
            return jsonify({"valid": False, "errore": "token scaduto"})

        # Burn — marca come usato
        cur.execute("UPDATE sso_tokens SET used=TRUE WHERE token=%s", (token,))
        conn.commit()
        cur.close()
        _release_conn(conn)

        return jsonify({
            "valid": True,
            "email": email,
            "ricetta_id": ricetta_id
        })
    except Exception as e:
        return jsonify({"valid": False, "errore": str(e)}), 500
