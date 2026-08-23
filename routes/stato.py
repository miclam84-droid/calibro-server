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
        # merge anche lo STORICO del banco (append, nessun conflitto: sposto le righe device su user)
        cur.execute("""UPDATE misure_banco SET chiave_tipo='user', chiave=%s
                       WHERE chiave_tipo='device' AND chiave=%s""", (str(user_id), device_id))
        # rimuovo le righe del device (ora fuse nell'account)
        cur.execute("DELETE FROM stato_fenomeni WHERE chiave_tipo='device' AND chiave=%s", (device_id,))
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        _release_conn(conn)


# ============================================================
# MEMORIA DEL BANCO (Profilo Tecnico) — lo STORICO delle misure dell'utente.
# Diverso da stato_fenomeni (che tiene solo l'ULTIMA misura): qui ogni misura
# è una riga (append), per calcolare medie e pattern ("negli ultimi 5 sour media 1.08%").
# Vantaggio non copiabile: Matter conosce COME LAVORI TU. Design (Gemini+OpenAI concordi):
# 1 tap dal Mirino, zero testo. 3 misure -> primo pattern. Timeline per fenomeno.
# ============================================================

def _init_banco(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS misure_banco (
            id           SERIAL PRIMARY KEY,
            chiave_tipo  TEXT NOT NULL,          -- 'user' | 'device'
            chiave       TEXT NOT NULL,
            fenomeno     TEXT NOT NULL,          -- id o nome del fenomeno misurato
            valore       DOUBLE PRECISION NOT NULL,
            unita        TEXT,
            ricetta      TEXT,                   -- opzionale: contesto (es. "Sour classico")
            quando       TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_banco_chiave_fen ON misure_banco(chiave_tipo, chiave, fenomeno)")


@bp.route("/v1/banco/salva", methods=["POST"])
def banco_salva():
    """Salva UNA misura nello storico del banco (append). Body: {fenomeno, valore, unita, ricetta, bersaglio_min, bersaglio_max}.
    3 secondi, un tap. Ritorna subito il pattern aggiornato (se ci sono >=3 misure). Aggiorna anche stato_fenomeni (ultima misura)."""
    b = request.json or {}
    fen = (b.get("fenomeno") or "").strip()
    if not fen:
        return jsonify({"errore": "fenomeno mancante"}), 400
    tipo, chiave = _chiave_utente()
    if not tipo:
        return jsonify({"errore": "identità mancante (X-Device-Id o X-Token)"}), 401
    try:
        valore = float(b.get("valore"))
    except (TypeError, ValueError):
        return jsonify({"errore": "valore numerico mancante"}), 400
    unita = b.get("unita")
    ricetta = (b.get("ricetta") or "").strip() or None
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_banco(cur)
        _init_tabella(cur)
        # 1) append allo storico
        cur.execute("""INSERT INTO misure_banco (chiave_tipo, chiave, fenomeno, valore, unita, ricetta, quando)
                       VALUES (%s,%s,%s,%s,%s,%s,NOW())""",
                    (tipo, chiave, fen, valore, unita, ricetta))
        # 2) aggiorna anche stato_fenomeni (ultima misura, per il Mirino)
        cur.execute("""
            INSERT INTO stato_fenomeni (chiave_tipo, chiave, fenomeno, stato, valore, unita, grezzo, quando)
            VALUES (%s,%s,%s,'misurato',%s,%s,%s,NOW())
            ON CONFLICT (chiave_tipo, chiave, fenomeno)
            DO UPDATE SET stato='misurato', valore=EXCLUDED.valore, unita=EXCLUDED.unita, quando=NOW()
        """, (tipo, chiave, fen, valore, unita, str(valore)))
        conn.commit()
        # 3) calcolo il pattern sulle misure di questo fenomeno
        pattern = _calcola_pattern(cur, tipo, chiave, fen,
                                   b.get("bersaglio_min"), b.get("bersaglio_max"))
        return jsonify({"ok": True, "fenomeno": fen, "valore": valore, "unita": unita, "pattern": pattern})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)[:200]}), 500
    finally:
        _release_conn(conn)


def _calcola_pattern(cur, tipo, chiave, fen, bersaglio_min=None, bersaglio_max=None):
    """Calcola media, conteggio e un messaggio-pattern per un fenomeno. None se <3 misure."""
    cur.execute("""SELECT valore, unita FROM misure_banco
                   WHERE chiave_tipo=%s AND chiave=%s AND fenomeno=%s
                   ORDER BY quando DESC LIMIT 20""", (tipo, chiave, fen))
    righe = cur.fetchall()
    valori = [float(r[0]) for r in righe]
    unita = righe[0][1] if righe and righe[0][1] else ""
    n = len(valori)
    if n < 3:
        return {"misure": n, "messaggio": None, "pronto": False}
    media = round(sum(valori) / n, 3)
    recenti = valori[:min(n, 5)]
    media_recenti = round(sum(recenti) / len(recenti), 3)
    msg = None
    try:
        bmin = float(bersaglio_min) if bersaglio_min is not None else None
        bmax = float(bersaglio_max) if bersaglio_max is not None else None
    except (TypeError, ValueError):
        bmin = bmax = None
    # messaggio-pattern: posizione rispetto al bersaglio, se fornito
    if bmin is not None and bmax is not None:
        centro = (bmin + bmax) / 2
        if media_recenti < bmin:
            scarto = round(centro - media_recenti, 3)
            msg = f"Nelle ultime {len(recenti)} misure sei quasi sempre SOTTO il bersaglio (media {media_recenti}{unita}, circa {scarto}{unita} sotto il centro)."
        elif media_recenti > bmax:
            scarto = round(media_recenti - centro, 3)
            msg = f"Nelle ultime {len(recenti)} misure sei quasi sempre SOPRA il bersaglio (media {media_recenti}{unita}, circa {scarto}{unita} sopra il centro)."
        else:
            msg = f"Nelle ultime {len(recenti)} misure sei DENTRO finestra (media {media_recenti}{unita}). Costante."
    else:
        msg = f"Nelle ultime {len(recenti)} misure la tua media è {media_recenti}{unita}."
    return {"misure": n, "media": media, "media_recenti": media_recenti, "unita": unita,
            "messaggio": msg, "pronto": True}


@bp.route("/v1/banco/pattern", methods=["GET"])
def banco_pattern():
    """Ritorna il pattern per un fenomeno (media, conteggio, messaggio). ?fenomeno=&bersaglio_min=&bersaglio_max="""
    fen = (request.args.get("fenomeno") or "").strip()
    if not fen:
        return jsonify({"errore": "fenomeno mancante"}), 400
    tipo, chiave = _chiave_utente()
    if not tipo:
        return jsonify({"misure": 0, "messaggio": None, "pronto": False})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_banco(cur)
        pattern = _calcola_pattern(cur, tipo, chiave, fen,
                                   request.args.get("bersaglio_min"), request.args.get("bersaglio_max"))
        conn.commit()
        return jsonify(pattern)
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)[:200], "misure": 0, "pronto": False}), 500
    finally:
        _release_conn(conn)


@bp.route("/v1/banco/profilo", methods=["GET"])
def banco_profilo():
    """Il PROFILO TECNICO dell'utente: media per ogni fenomeno misurato (>=3 volte).
    'Acidità media Sour 1.08%, Idratazione media focaccia 74%...'. È il gemello digitale del professionista."""
    tipo, chiave = _chiave_utente()
    if not tipo:
        return jsonify({"profilo": []})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _init_banco(cur)
        cur.execute("""SELECT fenomeno, COUNT(*) n, ROUND(AVG(valore)::numeric,3) media, MAX(unita) unita
                       FROM misure_banco WHERE chiave_tipo=%s AND chiave=%s
                       GROUP BY fenomeno HAVING COUNT(*) >= 3
                       ORDER BY COUNT(*) DESC""", (tipo, chiave))
        profilo = [{"fenomeno": r[0], "misure": r[1], "media": float(r[2]) if r[2] is not None else None,
                    "unita": r[3] or ""} for r in cur.fetchall()]
        conn.commit()
        return jsonify({"profilo": profilo, "fenomeni_tracciati": len(profilo)})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)[:200], "profilo": []}), 500
    finally:
        _release_conn(conn)
