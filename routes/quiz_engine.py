"""Motore quiz/esercizi UNIFICATO — un solo sistema per tutte le discipline.
Tipi: fenomeno, degustazione, abbinamento, diagnosi. Adattato allo schema reale:
i fenomeni hanno id TESTUALI (fen-*) nella tabella nodes, non interi.
Non tocca quiz_cache (il vecchio sistema delle lezioni resta com'è)."""
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from config import DATABASE_URL
import json

bp = Blueprint("quiz_engine", __name__)


def _assicura_tabelle(cur):
    """Crea le tabelle del motore quiz se non esistono. Idempotente."""
    # tabella polimorfica: un esercizio di qualsiasi tipo/disciplina
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz (
            id SERIAL PRIMARY KEY,
            fenomeno_id TEXT,                 -- id testuale del nodo fenomeno (fen-*), può essere NULL
            disciplina TEXT,                  -- bar, cucina, vino...
            tipo TEXT NOT NULL,               -- fenomeno | degustazione | abbinamento | diagnosi
            difficolta TEXT DEFAULT 'base',   -- base | avanzato
            domanda TEXT NOT NULL,
            opzioni JSONB NOT NULL,           -- ["opzione A", "opzione B", ...]
            risposta_corretta TEXT NOT NULL,  -- il testo dell'opzione corretta
            insight_didattico TEXT,           -- la spiegazione (il "perché")
            lang TEXT DEFAULT 'it',
            creato_il TIMESTAMP DEFAULT NOW()
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quiz_disc ON quiz(disciplina, tipo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quiz_fen ON quiz(fenomeno_id)")
    # tracciamento progressi per device (come misure_salvate)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS utente_quiz (
            id SERIAL PRIMARY KEY,
            device_id TEXT NOT NULL,
            quiz_id INTEGER REFERENCES quiz(id) ON DELETE CASCADE,
            superato BOOLEAN DEFAULT FALSE,
            data TIMESTAMP DEFAULT NOW()
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_uq_dev ON utente_quiz(device_id)")


@bp.route("/v1/quiz", methods=["GET"])
def lista_quiz():
    """Restituisce quiz filtrabili per disciplina/tipo/fenomeno/difficoltà.
    Query params: disciplina, tipo, fenomeno_id, difficolta, limit (default 10)."""
    if not DATABASE_URL:
        return jsonify({"quiz": [], "totale": 0})
    disciplina = request.args.get("disciplina")
    tipo = request.args.get("tipo")
    fenomeno_id = request.args.get("fenomeno_id")
    difficolta = request.args.get("difficolta")
    try:
        limit = min(int(request.args.get("limit", 10)), 50)
    except Exception:
        limit = 10
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _assicura_tabelle(cur)
        conn.commit()
        where = []; params = []
        if disciplina: where.append("disciplina=%s"); params.append(disciplina)
        if tipo:       where.append("tipo=%s");       params.append(tipo)
        if fenomeno_id:where.append("fenomeno_id=%s");params.append(fenomeno_id)
        if difficolta: where.append("difficolta=%s"); params.append(difficolta)
        sql = "SELECT id, fenomeno_id, disciplina, tipo, difficolta, domanda, opzioni, risposta_corretta, insight_didattico FROM quiz"
        if where: sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY RANDOM() LIMIT %s"; params.append(limit)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close(); _release_conn(conn)
        quiz = []
        for r in rows:
            opz = r[6]
            if isinstance(opz, str):
                try: opz = json.loads(opz)
                except Exception: opz = []
            quiz.append({
                "id": r[0], "fenomeno_id": r[1], "disciplina": r[2], "tipo": r[3],
                "difficolta": r[4], "domanda": r[5], "opzioni": opz,
                "risposta_corretta": r[7], "insight": r[8],
            })
        return jsonify({"quiz": quiz, "totale": len(quiz)})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"quiz": [], "errore": str(e)}), 200


@bp.route("/v1/quiz/rispondi", methods=["POST"])
def rispondi_quiz():
    """Registra la risposta di un utente e dice se è corretta.
    Body: {quiz_id, risposta, device_id?}. device_id anche da header X-Device-Id."""
    if not DATABASE_URL:
        return jsonify({"errore": "db non disponibile"}), 200
    body = request.json or {}
    quiz_id = body.get("quiz_id")
    risposta = (body.get("risposta") or "").strip()
    device_id = (request.headers.get("X-Device-Id", "") or body.get("device_id", "") or "").strip()[:80]
    if not quiz_id:
        return jsonify({"errore": "quiz_id mancante"}), 400
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _assicura_tabelle(cur)
        cur.execute("SELECT risposta_corretta, insight_didattico FROM quiz WHERE id=%s", (quiz_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); _release_conn(conn)
            return jsonify({"errore": "quiz non trovato"}), 404
        corretta = (row[0] or "").strip()
        insight = row[1] or ""
        superato = (risposta.lower() == corretta.lower())
        if device_id:
            cur.execute("INSERT INTO utente_quiz (device_id, quiz_id, superato) VALUES (%s,%s,%s)",
                        (device_id, quiz_id, superato))
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"superato": superato, "risposta_corretta": corretta, "insight": insight})
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"errore": str(e)}), 200


@bp.route("/v1/quiz/progressi", methods=["GET"])
def progressi_quiz():
    """Progressi dell'utente: quanti quiz superati, per disciplina.
    device_id da header X-Device-Id o query param."""
    if not DATABASE_URL:
        return jsonify({"progressi": {}})
    device_id = (request.headers.get("X-Device-Id", "") or request.args.get("device_id", "") or "").strip()[:80]
    if not device_id:
        return jsonify({"progressi": {}, "nota": "device_id mancante"})
    conn = _get_conn()
    try:
        cur = conn.cursor()
        _assicura_tabelle(cur)
        cur.execute("""
            SELECT q.disciplina, COUNT(DISTINCT uq.quiz_id) FILTER (WHERE uq.superato)
            FROM utente_quiz uq JOIN quiz q ON q.id=uq.quiz_id
            WHERE uq.device_id=%s GROUP BY q.disciplina""", (device_id,))
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(DISTINCT quiz_id) FROM utente_quiz WHERE device_id=%s AND superato", (device_id,))
        tot = cur.fetchone()
        cur.close(); _release_conn(conn)
        return jsonify({
            "progressi": {r[0]: r[1] for r in rows if r[0]},
            "totale_superati": (tot[0] if tot else 0),
        })
    except Exception as e:
        conn.rollback(); _release_conn(conn)
        return jsonify({"progressi": {}, "errore": str(e)}), 200
