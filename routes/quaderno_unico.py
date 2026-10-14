# ============================================================
# QUADERNO UNICO — il collante: un solo archivio su identita' (user o device)
# dove OGNI funzione salva il suo risultato in modo riproducibile e riapribile.
# Contratto (SPEC-QUADERNO-UNICO): identita' + classificazione + contenuto riproducibile
# + provenienza + relazione (parent_id) + ciclo di vita.
# NB: utenti.id e' SERIAL (intero) nel DB reale -> identita' come (chiave_tipo, chiave),
# coerente con stato.py, cosi' funziona anche per utenti device-only (non loggati).
# Questa e' la FONDAZIONE: non fa migrazione distruttiva dei 3 store vecchi
# (quella arriva DOPO, superato il test di accettazione). Qui: schema + CRUD del ciclo di vita.
# ============================================================
import os
import json
import uuid

from flask import Blueprint, request, jsonify

try:
    from db import _get_conn, _release_conn
except Exception:  # pragma: no cover
    _get_conn = _release_conn = None

bp_quaderno2 = Blueprint("quaderno_unico", __name__)

FUNZIONE_VER = "quaderno-1.0"


def _chiave():
    """(tipo, chiave) con tipo in {'user','device'} o (None,None). Riusa la logica di stato.py."""
    try:
        from routes.stato import _chiave_utente
    except Exception:
        try:
            from stato import _chiave_utente
        except Exception:
            _chiave_utente = None
    if _chiave_utente:
        try:
            return _chiave_utente()
        except Exception:
            pass
    # fallback minimale
    tok = request.headers.get("X-Token", "").strip()
    dev = request.headers.get("X-Device-Id", "").strip()
    if dev:
        return ("device", dev)
    if tok:
        return ("user", tok)
    return (None, None)


def _init(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quaderno_record (
            id            TEXT PRIMARY KEY,
            chiave_tipo   TEXT NOT NULL,          -- 'user' | 'device'
            chiave        TEXT NOT NULL,          -- user_id (stringa) o device_id
            creato_at     TIMESTAMPTZ DEFAULT NOW(),
            modificato_at TIMESTAMPTZ DEFAULT NOW(),
            porta         TEXT,                   -- atlante | banco | causa | laboratorio | quaderno
            funzione      TEXT NOT NULL,          -- idratazione | composer | ricetta_ai | misura ...
            tipo          TEXT NOT NULL,          -- ricetta | misura | grafo | esperimento | calcolo
            titolo        TEXT NOT NULL,
            lingua        TEXT DEFAULT 'it',
            parent_id     TEXT,                   -- relazione gerarchica (es. ricetta <- calcolo Banco)
            stato_input   JSONB NOT NULL,         -- per RIPRODURRE (quantita' strutturate {valore,unita})
            stato_output  JSONB NOT NULL,         -- il risultato
            provenienza   JSONB,                  -- {fonti, formule, versione_motore, stato_dato}
            ai_metadata   JSONB,                  -- {model, tokens, costo}
            note_lab      TEXT,                   -- evidenza empirica al banco
            archiviato    BOOLEAN DEFAULT FALSE
        )
    """)
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_quaderno2_identita
                   ON quaderno_record(chiave_tipo, chiave, porta)""")
    cur.execute("""CREATE INDEX IF NOT EXISTS idx_quaderno2_parent
                   ON quaderno_record(parent_id)""")


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


@bp_quaderno2.route("/v1/quaderno2/salva", methods=["POST"])
def salva():
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante (serve X-Token o X-Device-Id)"}), 401
    d = request.get_json(force=True, silent=True) or {}
    obbligatori = ("funzione", "tipo", "titolo", "stato_input", "stato_output")
    mancanti = [k for k in obbligatori if k not in d or d.get(k) in (None, "")]
    if mancanti:
        return jsonify({"errore": "campi mancanti", "mancanti": mancanti}), 400
    rid = "qr-" + uuid.uuid4().hex[:24]
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor()
        _init(cur)
        cur.execute("""INSERT INTO quaderno_record
            (id, chiave_tipo, chiave, porta, funzione, tipo, titolo, lingua, parent_id,
             stato_input, stato_output, provenienza, ai_metadata, note_lab)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (rid, tipo_id, str(chiave), d.get("porta"), d["funzione"], d["tipo"], d["titolo"],
             d.get("lingua", "it"), d.get("parent_id"),
             json.dumps(d["stato_input"], ensure_ascii=False),
             json.dumps(d["stato_output"], ensure_ascii=False),
             json.dumps(d.get("provenienza"), ensure_ascii=False) if d.get("provenienza") is not None else None,
             json.dumps(d.get("ai_metadata"), ensure_ascii=False) if d.get("ai_metadata") is not None else None,
             d.get("note_lab")))
        conn.commit(); cur.close()
        return jsonify({"ok": True, "id": rid})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


def _riga(row, cols):
    return {c: row[i] for i, c in enumerate(cols)}


@bp_quaderno2.route("/v1/quaderno2/<rid>", methods=["GET"])
def apri(rid):
    """Riapri un record — SOLO se appartiene all'identita' corrente (no accesso incrociato)."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        cols = ["id", "chiave_tipo", "chiave", "creato_at", "modificato_at", "porta", "funzione",
                "tipo", "titolo", "lingua", "parent_id", "stato_input", "stato_output",
                "provenienza", "ai_metadata", "note_lab", "archiviato"]
        cur.execute(f"""SELECT {','.join(cols)} FROM quaderno_record
                        WHERE id=%s AND chiave_tipo=%s AND chiave=%s""", (rid, tipo_id, str(chiave)))
        row = cur.fetchone(); cur.close()
        if not row:
            return jsonify({"trovato": False}), 404
        rec = _riga(row, cols)
        for k in ("creato_at", "modificato_at"):
            rec[k] = rec[k].isoformat() if rec[k] else None
        return jsonify({"trovato": True, "record": rec})
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


@bp_quaderno2.route("/v1/quaderno2/lista", methods=["GET"])
def lista():
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    porta = request.args.get("porta")
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        q = """SELECT id, porta, funzione, tipo, titolo, creato_at, modificato_at, parent_id, archiviato
               FROM quaderno_record WHERE chiave_tipo=%s AND chiave=%s AND archiviato=FALSE"""
        params = [tipo_id, str(chiave)]
        if porta:
            q += " AND porta=%s"; params.append(porta)
        q += " ORDER BY modificato_at DESC LIMIT 200"
        cur.execute(q, params)
        out = []
        for r in cur.fetchall():
            out.append({"id": r[0], "porta": r[1], "funzione": r[2], "tipo": r[3], "titolo": r[4],
                        "creato_at": r[5].isoformat() if r[5] else None,
                        "modificato_at": r[6].isoformat() if r[6] else None,
                        "parent_id": r[7], "archiviato": r[8]})
        cur.close()
        return jsonify({"identita": {"tipo": tipo_id}, "n": len(out), "record": out})
    except Exception as e:
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)


@bp_quaderno2.route("/v1/quaderno2/<rid>/aggiorna", methods=["POST"])
def aggiorna(rid):
    """Ciclo di vita: modifica titolo/stato_output/note_lab, o archivia. Solo sul proprio record."""
    tipo_id, chiave = _chiave()
    if not tipo_id:
        return jsonify({"errore": "identita' mancante"}), 401
    d = request.get_json(force=True, silent=True) or {}
    campi, valori = [], []
    if "titolo" in d: campi.append("titolo=%s"); valori.append(d["titolo"])
    if "stato_output" in d: campi.append("stato_output=%s"); valori.append(json.dumps(d["stato_output"], ensure_ascii=False))
    if "note_lab" in d: campi.append("note_lab=%s"); valori.append(d["note_lab"])
    if "archiviato" in d: campi.append("archiviato=%s"); valori.append(bool(d["archiviato"]))
    if not campi:
        return jsonify({"errore": "niente da aggiornare"}), 400
    campi.append("modificato_at=NOW()")
    conn = None; pooled = False
    try:
        conn, pooled = _conn()
        cur = conn.cursor(); _init(cur)
        valori += [rid, tipo_id, str(chiave)]
        cur.execute(f"""UPDATE quaderno_record SET {','.join(campi)}
                        WHERE id=%s AND chiave_tipo=%s AND chiave=%s""", valori)
        n = cur.rowcount
        conn.commit(); cur.close()
        if n == 0:
            return jsonify({"ok": False, "nota": "record non trovato per questa identita'"}), 404
        return jsonify({"ok": True, "aggiornati": n})
    except Exception as e:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return jsonify({"errore": str(e)[:160]}), 500
    finally:
        if conn: _chiudi(conn, pooled)
