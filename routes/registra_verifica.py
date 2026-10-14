# ============================================================
# REGISTRA-VERIFICA — il "fossato": un professionista corregge/verifica un valore
# sensoriale di una preparazione, con metodo e provenienza.
#
# DECISIONE (deviazione voluta dallo SPEC-VETRINA): NON si muta il nodo condiviso del
# grafo (un utente qualsiasi cambierebbe il dato canonico PER TUTTI = vandalismo).
# La verifica si salva PER IDENTITA' (come il Quaderno), in OVERLAY sopra la base del
# sistema. Tabella append-only -> lo storico e il rollback sono gratis (ogni verifica
# e' una riga; l'ultima per (identita', nodo, asse) vince).
#
# Tre endpoint:
#  POST /v1/registra-verifica        -> registra una verifica (corretto|verificato)
#  GET  /v1/verifiche/<nodo_id>      -> le MIE verifiche su quel nodo (overlay)
#  GET  /v1/proprieta-effettive/<id> -> base del sistema (normalizzata) + il mio overlay
# ============================================================
import os
import json

from flask import Blueprint, request, jsonify

try:
    from db import _get_conn, _release_conn
except Exception:  # pragma: no cover
    _get_conn = _release_conn = None

bp_verifica = Blueprint("registra_verifica", __name__)

# stati che un utente puo' registrare (stimato/derivato sono basi di sistema, non utente)
_STATI_UTENTE = ("corretto", "verificato")
# assi noti (non si rifiuta un asse fuori lista, ma si valida che sia una stringa sensata)
_ASSI = ("dolce", "salato", "acido", "amaro", "umami", "grasso", "corposita", "croccante",
         "astringente", "piccante", "termico", "aroma_fresco", "aroma_caldo",
         "effervescenza", "fermentato", "alcolico")


def _chiave():
    """(tipo, chiave) con tipo in {'user','device'} o (None,None). Riusa stato.py."""
    try:
        from routes.stato import _chiave_utente
        return _chiave_utente()
    except Exception:
        pass
    dev = request.headers.get("X-Device-Id", "").strip()
    tok = request.headers.get("X-Token", "").strip()
    if dev:
        return ("device", dev)
    if tok:
        return ("user", tok)
    return (None, None)


def _conn():
    if _get_conn:
        return _get_conn(), True
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"]), False


def _chiudi(conn, pooled):
    try:
        if pooled and _release_conn:
            _release_conn(conn)
        else:
            conn.close()
    except Exception:
        pass


def _init(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verifiche_proprieta (
            id           BIGSERIAL PRIMARY KEY,
            chiave_tipo  TEXT NOT NULL,       -- 'user' | 'device'
            chiave       TEXT NOT NULL,
            nodo_id      TEXT NOT NULL,       -- es. prep-cordiale-al-lime
            asse         TEXT NOT NULL,       -- es. dolce
            valore       DOUBLE PRECISION NOT NULL,
            stato        TEXT NOT NULL,       -- corretto | verificato
            autore       TEXT,                -- nome/ruolo dichiarato
            metodo       TEXT,                -- 'valutazione sensoriale' | 'rifrattometro (Brix)' | ...
            condizioni   TEXT,
            base         TEXT,                -- spiegazione del numero
            creato_at    TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_verifiche_lookup
                   ON verifiche_proprieta(chiave_tipo, chiave, nodo_id, asse, creato_at DESC)""")


def _norm_base(asse, prop, fonti):
    """Normalizza la base di sistema (vecchio formato) al formato provenienza completo."""
    if asse not in prop or prop.get(asse) is None:
        return None
    f = (fonti.get(asse) or {}) if isinstance(fonti, dict) else {}
    stato = f.get("stato") or "stimato"
    metodo = f.get("metodo") or f.get("fonte") or ("calcolo da ricetta" if stato == "stimato" else "")
    return {
        "valore": prop.get(asse),
        "stato": stato,                       # derivato | stimato (base di sistema)
        "autore": f.get("autore") or "sistema",
        "metodo": metodo,
        "base": f.get("base") or f.get("formula") or "",
        "condizioni": f.get("condizioni") or "",
    }


@bp_verifica.route("/v1/registra-verifica", methods=["POST"])
def registra_verifica():
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante (serve X-Token o X-Device-Id)"}), 401
    d = request.get_json(force=True, silent=True) or {}
    nodo_id = (d.get("nodo_id") or "").strip()
    asse = (d.get("asse") or "").strip().lower()
    stato = (d.get("stato") or "").strip().lower()
    if not nodo_id or not asse:
        return jsonify({"errore": "servono nodo_id e asse"}), 400
    if stato not in _STATI_UTENTE:
        return jsonify({"errore": "stato deve essere 'corretto' o 'verificato'",
                        "ricevuto": stato}), 400
    try:
        valore = float(d.get("valore"))
    except Exception:
        return jsonify({"errore": "valore non numerico"}), 400
    if not (-50 <= valore <= 1000):
        return jsonify({"errore": "valore fuori scala plausibile"}), 400

    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("""INSERT INTO verifiche_proprieta
            (chiave_tipo, chiave, nodo_id, asse, valore, stato, autore, metodo, condizioni, base)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, creato_at""",
            (tipo_id, str(chiave), nodo_id, asse, valore, stato,
             d.get("autore"), d.get("metodo"), d.get("condizioni"), d.get("base")))
        rid, creato = cur.fetchone()
        conn.commit(); cur.close()
        return jsonify({"ok": True, "id": rid, "nodo_id": nodo_id, "asse": asse,
                        "valore": valore, "stato": stato,
                        "creato_at": creato.isoformat() if creato else None})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


def _mie_verifiche(cur, tipo_id, chiave, nodo_id):
    """Ultima verifica per asse + storico, per l'identita' corrente."""
    cur.execute("""SELECT asse, valore, stato, autore, metodo, condizioni, base, creato_at
                   FROM verifiche_proprieta
                   WHERE chiave_tipo=%s AND chiave=%s AND nodo_id=%s
                   ORDER BY asse, creato_at DESC""", (tipo_id, str(chiave), nodo_id))
    corrente, storico = {}, {}
    for asse, val, stato, autore, metodo, cond, base, creato in cur.fetchall():
        voce = {"valore": val, "stato": stato, "autore": autore, "metodo": metodo,
                "condizioni": cond, "base": base,
                "data": creato.isoformat() if creato else None}
        storico.setdefault(asse, []).append(voce)
        if asse not in corrente:
            corrente[asse] = voce   # il primo (ORDER BY creato_at DESC) = l'ultima verifica
    return corrente, storico


@bp_verifica.route("/v1/verifiche/<path:nodo_id>", methods=["GET"])
def verifiche(nodo_id):
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        corrente, storico = _mie_verifiche(cur, tipo_id, chiave, nodo_id)
        cur.close()
        return jsonify({"nodo_id": nodo_id, "verifiche": corrente, "storico": storico})
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


@bp_verifica.route("/v1/proprieta-effettive/<path:nodo_id>", methods=["GET"])
def proprieta_effettive(nodo_id):
    """Base del sistema (normalizzata) + overlay dell'identita' corrente.
    E' il profilo che la Vetrina mostra: ogni asse col suo stato/provenienza."""
    tipo_id, chiave = _chiave()
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cur.execute("SELECT name, data FROM nodes WHERE id=%s", (nodo_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"trovato": False, "nodo_id": nodo_id}), 404
        name, data = row
        dd = data if isinstance(data, dict) else (json.loads(data) if data else {})
        prop = dd.get("proprieta", {}) or {}
        fonti = dd.get("proprieta_fonti", dd.get("proprieta_meta", {})) or {}

        effettive = {}
        assi_presenti = set(list(prop.keys()))
        for asse in assi_presenti:
            nb = _norm_base(asse, prop, fonti)
            if nb:
                effettive[asse] = nb

        overlay = {}
        if tipo_id:
            overlay, _ = _mie_verifiche(cur, tipo_id, chiave, nodo_id)
            for asse, voce in overlay.items():
                effettive[asse] = voce   # la verifica dell'utente vince sulla base
        cur.close()
        return jsonify({
            "trovato": True, "nodo_id": nodo_id, "nome": name,
            "proprieta_effettive": effettive,
            "ha_overlay_utente": bool(overlay),
            "nota": "stato: derivato/stimato = base di sistema; corretto/verificato = tua verifica.",
        })
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)
