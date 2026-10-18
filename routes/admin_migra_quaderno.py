# ============================================================
# MIGRAZIONE -> QUADERNO UNICO
# Copia i 3 store vecchi (ricette_salvate, misure_salvate, chat_salvate),
# tutti per device_id, dentro quaderno_record come record riapribili.
#
# MODELLO DI SICUREZZA (deciso con Michele):
#  - NON distruttiva: copia, non sposta. Gli originali restano intatti.
#  - Idempotente: id deterministico con prefisso 'qr-mig-...' (da device_id +
#    chiave naturale) + ON CONFLICT DO NOTHING -> rilanci senza duplicare.
#  - Annullabile: DELETE FROM quaderno_record WHERE id LIKE 'qr-mig-%'.
#  - Backup esplicito (solo in esegui): _backup_mig_ricette/_misure/_chat.
#  - DRY-RUN di default: senza &esegui=1 conta e basta, non scrive nulla.
# Auth: ADMIN_SECRET via ?s=  (stesso schema del resto dell'admin).
# ============================================================
import os
import json
import hmac
import hashlib
from datetime import datetime

from flask import Blueprint, request, jsonify

from db import _get_conn, _release_conn

bp_migra_q = Blueprint("admin_migra_quaderno", __name__)


def _auth():
    # Gate HMAC (confronto a tempo costante), stesso schema di pwa.admin_copertura.
    atteso = os.environ.get("ADMIN_SECRET") or ""
    return bool(atteso) and hmac.compare_digest(str(request.args.get("s", "")), str(atteso))


def _mid(prefix, *parti):
    h = hashlib.md5("|".join(str(p) for p in parti).encode("utf-8")).hexdigest()[:16]
    return "qr-mig-%s-%s" % (prefix, h)


def _esiste(cur, tabella):
    cur.execute("SELECT to_regclass(%s)", (tabella,))
    return cur.fetchone()[0] is not None


def _jd(x):
    """dict/list -> testo JSON; None/altro -> oggetto vuoto (le colonne sono NOT NULL)."""
    if isinstance(x, (dict, list)):
        return json.dumps(x, ensure_ascii=False)
    return json.dumps({}, ensure_ascii=False)


def _init_quaderno(cur):
    """Garantisce lo schema di quaderno_record (riuso quaderno_unico, con fallback)."""
    try:
        from routes.quaderno_unico import _init
        _init(cur)
        return
    except Exception:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quaderno_record (
            id TEXT PRIMARY KEY, chiave_tipo TEXT NOT NULL, chiave TEXT NOT NULL,
            creato_at TIMESTAMPTZ DEFAULT NOW(), modificato_at TIMESTAMPTZ DEFAULT NOW(),
            porta TEXT, funzione TEXT NOT NULL, tipo TEXT NOT NULL, titolo TEXT NOT NULL,
            lingua TEXT DEFAULT 'it', parent_id TEXT,
            stato_input JSONB NOT NULL, stato_output JSONB NOT NULL,
            provenienza JSONB, ai_metadata JSONB, note_lab TEXT,
            archiviato BOOLEAN DEFAULT FALSE)
    """)


# --- mappatura dei 3 store su record del Quaderno -----------------------------
# ogni mapper ritorna la tupla pronta per l'INSERT (stesso ordine di _COLONNE)
_COLONNE = ("id", "chiave_tipo", "chiave", "creato_at", "porta", "funzione", "tipo",
            "titolo", "stato_input", "stato_output", "provenienza", "note_lab")


def _da_ricette(r):
    # r: device_id, ricetta_id, nome, dati, creato_il
    dev, ric_id, nome, dati, creato = r
    rid = _mid("ric", dev, ric_id)
    return (rid, "device", str(dev), creato, "laboratorio", "ricetta", "ricetta",
            (nome or "Ricetta"), _jd({}), _jd(dati),
            json.dumps({"migrato_da": "ricette_salvate", "ricetta_id": ric_id, "stato": "migrato"}, ensure_ascii=False),
            None)


def _da_misure(r):
    # r: id, device_id, fenomeno, fenomeno_id, valore, unita, bersaglio, nota, creato_il
    sid, dev, fen, fen_id, val, unita, bers, nota, creato = r
    rid = _mid("mis", dev, sid)
    return (rid, "device", str(dev), creato, "banco", "misura", "misura",
            (fen or "Misura"),
            _jd({"fenomeno": fen, "fenomeno_id": fen_id, "bersaglio": bers}),
            _jd({"valore": val, "unita": unita}),
            json.dumps({"migrato_da": "misure_salvate", "stato": "migrato"}, ensure_ascii=False),
            nota)


def _da_chat(r):
    # r: id, device_id, titolo, messaggi, tag, creato_il
    sid, dev, titolo, messaggi, tag, creato = r
    rid = _mid("chat", dev, sid)
    return (rid, "device", str(dev), creato, "quaderno", "chat", "chat",
            (titolo or "Conversazione"),
            _jd({"tag": tag}), _jd({"messaggi": messaggi}),
            json.dumps({"migrato_da": "chat_salvate", "stato": "migrato"}, ensure_ascii=False),
            None)


_PIANO = [
    ("ricette_salvate", "SELECT device_id, ricetta_id, nome, dati, creato_il FROM ricette_salvate", _da_ricette),
    ("misure_salvate",  "SELECT id, device_id, fenomeno, fenomeno_id, valore, unita, bersaglio, nota, creato_il FROM misure_salvate", _da_misure),
    ("chat_salvate",    "SELECT id, device_id, titolo, messaggi, tag, creato_il FROM chat_salvate", _da_chat),
]


def _gia_presenti(cur, ids):
    """Quanti di questi id esistono gia' in quaderno_record (per il conteggio dei saltati)."""
    if not ids:
        return 0
    cur.execute("SELECT COUNT(*) FROM quaderno_record WHERE id = ANY(%s)", (list(ids),))
    row = cur.fetchone()
    return int(row[0]) if row else 0


@bp_migra_q.route("/admin/migra-quaderno", methods=["GET"])
def migra_quaderno():
    """Dry-run di default. ?s=<ADMIN_SECRET>  [&esegui=1 per scrivere davvero].

    Garanzie: ADDITIVO (solo INSERT ... ON CONFLICT DO NOTHING; mai DELETE/UPDATE,
    i 3 store vecchi NON vengono toccati), idempotente (id deterministico qr-mig-...),
    annullabile (DELETE ... WHERE id LIKE 'qr-mig-%'), backup del destinatario
    quaderno_record prima di scrivere, tutto in un'unica transazione.
    """
    if not _auth():
        return jsonify({"errore": "non autorizzato"}), 401
    esegui = request.args.get("esegui", "") == "1"
    conn = _get_conn()
    report = {"modalita": "esegui" if esegui else "dry-run (nessuna scrittura)",
              "store": {}, "totale_sorgente": 0, "totale_scritti": 0,
              "totale_saltati": 0, "backup": []}
    try:
        cur = conn.cursor()
        _init_quaderno(cur)
        # Backup del DESTINATARIO (quaderno_record) prima di qualsiasi scrittura.
        # Copia congelata, non distruttiva (nome con timestamp: non sovrascrive backup precedenti).
        if esegui:
            backup = "_backup_mig_quaderno_record_%s" % datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            cur.execute('CREATE TABLE "%s" AS SELECT * FROM quaderno_record' % backup)
            report["backup"].append(backup)
        for nome, query, mapper in _PIANO:
            if not _esiste(cur, nome):
                report["store"][nome] = {"presente": False, "righe": 0, "scritti": 0, "saltati": 0}
                continue
            cur.execute(query)
            righe = cur.fetchall()
            report["totale_sorgente"] += len(righe)
            scritti = 0
            saltati = 0
            esempi = []
            if esegui:
                for r in righe:
                    t = mapper(r)
                    cur.execute("""INSERT INTO quaderno_record
                        (id, chiave_tipo, chiave, creato_at, porta, funzione, tipo,
                         titolo, stato_input, stato_output, provenienza, note_lab)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING""", t)
                    scritti += cur.rowcount
                saltati = len(righe) - scritti  # gia' presenti -> non duplicati
                report["totale_scritti"] += scritti
            else:
                # Dry-run: nessuna scrittura. Conta quanti sarebbero gia' presenti
                # (saltati) interrogando il destinatario, e mostra un campione.
                ids = [mapper(r)[0] for r in righe]
                saltati = _gia_presenti(cur, ids)
                for r in righe[:3]:
                    t = mapper(r)
                    esempi.append({"id": t[0], "titolo": t[7], "porta": t[4]})
            report["totale_saltati"] += saltati
            report["store"][nome] = {"presente": True, "righe": len(righe),
                                     "scritti": scritti, "saltati": saltati,
                                     "esempi": esempi}
        if esegui:
            conn.commit()
        else:
            conn.rollback()
        cur.close()
        report["ok"] = True
        report["annulla"] = "DELETE FROM quaderno_record WHERE id LIKE 'qr-mig-%'"
        return jsonify(report)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({"ok": False, "errore": str(e)[:200], "report_parziale": report}), 500
    finally:
        _release_conn(conn)
