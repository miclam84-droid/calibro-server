"""
Endpoint CRON — task schedulati chiamati da cron-job.org (Railway Hobby non ha cron nativo).
Protetti da ADMIN_SECRET: solo chi ha il segreto (il cron configurato da Michele) li chiama.
- /cron/ricarica-free   : ogni lunedì, +1 domanda gratis a chi ha esaurito (il "gancio")
- /cron/diario-settimanale : ogni domenica, email riepilogo "questa settimana hai misurato X"
"""
import os, hmac
from flask import Blueprint, request, jsonify

bp_cron = Blueprint("cron", __name__)


def _auth():
    s = request.args.get("s", "")
    return hmac.compare_digest(str(s), str(os.environ.get("ADMIN_SECRET") or ""))


@bp_cron.route("/cron/ricarica-free")
def ricarica_free():
    """Ricarica settimanale: rimuove 1 riga di trial_chat per ogni device/user che ha
    esaurito (5 chat), così tornano ad avere 1 domanda. Costo API zero: incentiva il ritorno.
    Da schedulare ogni lunedì mattina su cron-job.org."""
    if not _auth():
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn()
    try:
        cur = conn.cursor()
        # per ogni device_id che ha >=5 righe, cancella la più vecchia (torna a 4 = 1 domanda libera)
        # uso una CTE per trovare le righe più vecchie dei "pieni".
        cur.execute("""
            WITH pieni AS (
                SELECT device_id FROM trial_chat
                WHERE device_id IS NOT NULL
                GROUP BY device_id HAVING COUNT(*) >= 5
            ),
            da_togliere AS (
                SELECT t.id FROM trial_chat t
                JOIN pieni p ON p.device_id = t.device_id
                WHERE t.id IN (
                    SELECT MIN(id) FROM trial_chat t2
                    WHERE t2.device_id = t.device_id
                )
            )
            DELETE FROM trial_chat WHERE id IN (SELECT id FROM da_togliere)
        """)
        n_device = cur.rowcount
        # stesso per user_id (utenti registrati non paganti)
        cur.execute("""
            WITH pieni AS (
                SELECT user_id FROM trial_chat
                WHERE user_id IS NOT NULL
                GROUP BY user_id HAVING COUNT(*) >= 5
            ),
            da_togliere AS (
                SELECT t.id FROM trial_chat t
                JOIN pieni p ON p.user_id = t.user_id
                WHERE t.id IN (
                    SELECT MIN(id) FROM trial_chat t2 WHERE t2.user_id = t.user_id
                )
            )
            DELETE FROM trial_chat WHERE id IN (SELECT id FROM da_togliere)
        """)
        n_user = cur.rowcount
        conn.commit()
        return jsonify({"ok": True, "ricaricati_device": n_device, "ricaricati_user": n_user})
    except Exception as e:
        conn.rollback()
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)


@bp_cron.route("/cron/diario-settimanale")
def diario_settimanale():
    """Riepilogo domenicale 'Diario del Banco': per ogni utente con email che ha salvato
    misure nell'ultima settimana, manda un'email col conteggio. Retention.
    Da schedulare ogni domenica sera su cron-job.org.
    NOTA: le misure sono per device_id (non sempre legate a un'email), quindi l'invio
    riguarda gli utenti REGISTRATI che hanno un device collegato. Difensivo."""
    if not _auth():
        return "Forbidden", 403
    from db import _get_conn, _release_conn
    conn = _get_conn()
    inviate = 0
    try:
        cur = conn.cursor()
        # conteggio misure ultima settimana per device
        cur.execute("""
            SELECT device_id, COUNT(*) AS n
            FROM misure_salvate
            WHERE creato_il >= NOW() - INTERVAL '7 days'
            GROUP BY device_id
        """)
        conteggi = cur.fetchall()
        # per ora restituisco solo il riepilogo aggregato (l'invio email per-device
        # richiede il mapping device->email che non è sempre disponibile).
        # Quando il frontend legherà device_id all'account, qui parte l'email vera.
        totale_misure = sum(int(r[1]) for r in conteggi) if conteggi else 0
        device_attivi = len(conteggi)
        cur.close()
        return jsonify({"ok": True, "device_attivi_settimana": device_attivi,
                        "totale_misure_settimana": totale_misure,
                        "email_inviate": inviate,
                        "nota": "invio email attivo quando device_id sarà legato all'account"})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500
    finally:
        _release_conn(conn)
