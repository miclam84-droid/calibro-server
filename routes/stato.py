# ============================================================
# stato.py — Stato-fenomeno per utente (device_id o user_id).
# Feature: il Mirino nell'Atlante indica la progressione dell'utente.
# Stati: mai_aperto -> studiato (ha letto la scheda) -> misurato (ha inserito un valore).
# in_finestra (dentro il bersaglio) = TEMPO 2, quando i bersagli saranno strutturati.
# ============================================================
from flask import Blueprint, request, jsonify
import os, json, re
from db import _get_conn, _release_conn
from auth import _utente_da_token

bp = Blueprint("stato", __name__)

def _chiave_utente():
    """Identità: user_id se loggato (X-Token valido), altrimenti device_id (X-Device-Id).
    Ritorna (tipo, valore) con tipo in {'user','device'} o (None,None) se manca tutto."""
    token = request.headers.get("X-Token","").strip()
    if not token and request.is_json:
        token = ((request.json or {}).get("token") or "").strip()
    if token:
        uid = _utente_da_token(token)
        if uid:
            return ("user", str(uid))
    dev = request.headers.get("X-Device-Id","").strip()
    # valido: UUID v4 puro, 36 char
    if dev and re.fullmatch(r"[0-9a-fA-F-]{36}", dev):
        return ("device", dev)
    return (None, None)

def _init_tabella(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stato_fenomeni (
            id           SERIAL PRIMARY KEY,
            chiave_tipo  TEXT NOT NULL,          -- 'user' | 'device'
            chiave       TEXT NOT NULL,          -- user_id o device_id
            fenomeno     TEXT NOT NULL,
            stato        TEXT NOT NULL DEFAULT 'studiato',  -- studiato | misurato
            valore       DOUBLE PRECISION,       -- numero puro (per confronti futuri)
            unita        TEXT,                   -- unità se nota
            grezzo       TEXT,                   -- stringa esatta digitata dall'utente
            in_finestra  BOOLEAN,                -- null per ora (TEMPO 2)
            quando       TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (chiave_tipo, chiave, fenomeno)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stato_chiave ON stato_fenomeni(chiave_tipo, chiave)")

@bp.route("/v1/misura", methods=["POST"])
def misura():
    """Salva una misura per l'utente corrente. Body: {fenomeno, valore, unita, grezzo, lang}.
    Ritorna lo stato aggiornato. in_finestra=null per ora (bersagli non ancora strutturati)."""
    b = request.json or {}
    fen = (b.get("fenomeno") or "").strip()
    if not fen:
        return jsonify({"errore":"fenomeno mancante"}), 400
    tipo, chiave = _chiave_utente()
    if not tipo:
        return jsonify({"errore":"identità mancante (X-Device-Id o X-Token)"}), 401
    valore = b.get("valore")
    try: valore = float(valore) if valore is not None and valore != "" else None
    except: valore = None
    unita = b.get("unita")
    grezzo = b.get("grezzo") or (str(b.get("valore")) if b.get("valore") is not None else None)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_tabella(cur)
        # upsert: se esiste già uno stato per (chiave, fenomeno), aggiorna a 'misurato'
        cur.execute("""
            INSERT INTO stato_fenomeni (chiave_tipo, chiave, fenomeno, stato, valore, unita, grezzo, in_finestra, quando)
            VALUES (%s,%s,%s,'misurato',%s,%s,%s,NULL,NOW())
            ON CONFLICT (chiave_tipo, chiave, fenomeno)
            DO UPDATE SET stato='misurato', valore=EXCLUDED.valore, unita=EXCLUDED.unita,
                          grezzo=EXCLUDED.grezzo, quando=NOW()
        """, (tipo, chiave, fen, valore, unita, grezzo))
        conn.commit()
        return jsonify({"ok":True, "fenomeno":fen, "valore":valore, "unita":unita,
                        "in_finestra":None, "bersaglio":None, "stato":"misurato"})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore":str(e)[:200]}), 500
    finally:
        _release_conn(conn)

@bp.route("/v1/stato-fenomeni", methods=["GET"])
def stato_fenomeni():
    """Lista degli stati dei fenomeni per l'utente corrente (per accendere i Mirini nell'Atlante)."""
    tipo, chiave = _chiave_utente()
    if not tipo:
        # nessuna identità: lista vuota, non errore (l'Atlante mostra tutto mai_aperto)
        return jsonify({"stati": []})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_tabella(cur)
        cur.execute("""SELECT fenomeno, stato, valore, unita, grezzo, in_finestra, quando
                       FROM stato_fenomeni WHERE chiave_tipo=%s AND chiave=%s""", (tipo, chiave))
        stati = []
        for row in cur.fetchall():
            g = lambda i: (row[i] if not hasattr(row,"keys") else row[list(row.keys())[i]])
            stati.append({"id":g(0), "stato":g(1),
                          "ultima_misura":g(2), "unita":g(3), "grezzo":g(4),
                          "in_finestra":g(5),
                          "quando": g(6).isoformat() if g(6) else None})
        conn.commit()
        return jsonify({"stati": stati})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore":str(e)[:200], "stati":[]}), 500
    finally:
        _release_conn(conn)

def segna_studiato(fenomeno_id):
    """Chiamata da /nodo?traccia=1: segna 'studiato' se non è già 'misurato'. Ritorna lo stato o None."""
    tipo, chiave = _chiave_utente()
    if not tipo or not fenomeno_id:
        return None
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_tabella(cur)
        cur.execute("""
            INSERT INTO stato_fenomeni (chiave_tipo, chiave, fenomeno, stato, quando)
            VALUES (%s,%s,%s,'studiato',NOW())
            ON CONFLICT (chiave_tipo, chiave, fenomeno) DO NOTHING
        """, (tipo, chiave, fenomeno_id))
        conn.commit()
        cur.execute("SELECT stato FROM stato_fenomeni WHERE chiave_tipo=%s AND chiave=%s AND fenomeno=%s",
                    (tipo, chiave, fenomeno_id))
        r = cur.fetchone()
        return (r[0] if not hasattr(r,"keys") else r["stato"]) if r else "studiato"
    except Exception:
        conn.rollback()
        return None
    finally:
        _release_conn(conn)

def merge_device_su_utente(device_id, user_id):
    """Al login/registrazione: fonde lo stato del device nell'account. Misura più recente vince."""
    if not device_id or not user_id:
        return
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_tabella(cur)
        # per ogni fenomeno del device, sposta su user se non esiste o se è più recente
        cur.execute("""
            INSERT INTO stato_fenomeni (chiave_tipo, chiave, fenomeno, stato, valore, unita, grezzo, in_finestra, quando)
            SELECT 'user', %s, fenomeno, stato, valore, unita, grezzo, in_finestra, quando
            FROM stato_fenomeni WHERE chiave_tipo='device' AND chiave=%s
            ON CONFLICT (chiave_tipo, chiave, fenomeno)
            DO UPDATE SET stato=EXCLUDED.stato, valore=EXCLUDED.valore, unita=EXCLUDED.unita,
                          grezzo=EXCLUDED.grezzo, quando=EXCLUDED.quando
            WHERE stato_fenomeni.quando < EXCLUDED.quando
        """, (str(user_id), device_id))
        # rimuovo le righe del device (ora fuse nell'account)
        cur.execute("DELETE FROM stato_fenomeni WHERE chiave_tipo='device' AND chiave=%s", (device_id,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        _release_conn(conn)
