# ============================================================
# routes/misc.py — Stripe, feedback utente, supporto.
# Dipende da: db, auth, notifiche.
from flask import Blueprint, request, jsonify
from db import _get_conn, _release_conn
from auth import _utente_da_token
from notifiche import _invia_email_resend
from config import DATABASE_URL
import os, json
bp = Blueprint("misc", __name__)


@bp.route("/v1/stripe/checkout", methods=["POST"])
def stripe_checkout():
    """GT8 — Crea sessione Stripe Checkout per abbonamento Pro.
    Richiede STRIPE_SECRET_KEY nelle variabili Railway."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    if not user_id:
        return jsonify({"errore":"autenticazione richiesta"}), 401
    
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"errore":"pagamenti non configurati"}), 503
    
    try:
        import urllib.request, urllib.parse
        # crea sessione checkout Stripe
        body = urllib.parse.urlencode({
            "mode": "subscription",
            "payment_method_types[]": "card",
            "line_items[0][price]": os.environ.get("STRIPE_PRICE_PRO",""),
            "line_items[0][quantity]": "1",
            "success_url": f"{request.host_url}?piano=pro&success=1",
            "cancel_url": f"{request.host_url}?cancel=1",
            "metadata[user_id]": str(user_id)
        }).encode()
        req = urllib.request.Request(
            "https://api.stripe.com/v1/checkout/sessions",
            data=body,
            headers={"Authorization": f"Bearer {stripe_key}"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return jsonify({"url": data.get("url"), "checkout_url": data.get("url"), "session_id": data.get("id")})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/stripe/webhook", methods=["POST"])
def stripe_webhook():
    """GT8 — Webhook Stripe: aggiorna piano utente a Pro dopo pagamento."""
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return jsonify({"ok":True})
    try:
        payload = request.get_data()
        data = json.loads(payload)
        event_type = data.get("type","")
        if event_type in ("checkout.session.completed","customer.subscription.created"):
            obj = data.get("data",{}).get("object",{})
            user_id = obj.get("metadata",{}).get("user_id")
            if user_id and DATABASE_URL:
                import psycopg2
                conn = _get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE utenti SET piano='pro' WHERE id=%s", (user_id,))
                conn.commit(); cur.close(); _release_conn(conn)
    except Exception:
        pass
    return jsonify({"ok":True})

@bp.route("/v1/feedback", methods=["POST"])
def feedback():
    """AC5 — Pollice su/giù sulla risposta di Sonnet.
    Alimenta log_domande con campo feedback per affinare il prompt."""
    body = request.json or {}
    log_id = body.get("log_id")
    voto = body.get("voto")  # 1 = positivo, -1 = negativo
    nota = body.get("nota", "")
    if not log_id or voto not in (1, -1):
        return jsonify({"errore": "log_id e voto (1/-1) obbligatori"}), 400
    if not DATABASE_URL:
        return jsonify({"ok": True})
    try:
        import psycopg2
        conn = _get_conn()
        cur = conn.cursor()
        # aggiunge colonna feedback se non esiste
        cur.execute("""
            ALTER TABLE log_domande
            ADD COLUMN IF NOT EXISTS feedback INTEGER,
            ADD COLUMN IF NOT EXISTS feedback_nota TEXT
        """)
        cur.execute(
            "UPDATE log_domande SET feedback=%s, feedback_nota=%s WHERE id=%s",
            (voto, nota[:200], log_id)
        )
        conn.commit(); cur.close(); _release_conn(conn)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500

@bp.route("/v1/supporto", methods=["POST"])
def supporto():
    """Chatbot di supporto in-app. Salva in log_domande con tipo='supporto',
    risponde via Haiku (solo info prodotto reali), supporta la cronologia multi-turno.
    Notifica l'admin via email."""
    token = request.headers.get("Authorization","").replace("Bearer ","")
    user_id = _utente_da_token(token)
    body = request.json or {}
    testo = body.get("testo","").strip()
    history = body.get("history", [])  # [{ruolo, testo}, ...] per il multi-turno
    if not testo:
        return jsonify({"errore":"testo vuoto"}), 400

    if DATABASE_URL:
        try:
            import psycopg2
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO log_domande (tipo, domanda, esito, user_id) VALUES (%s,%s,%s,%s)",
                ("supporto", testo[:1000], "ricevuto", str(user_id) if user_id else None))
            conn.commit(); cur.close(); _release_conn(conn)
        except Exception:
            pass

    system_supporto = (
        "Sei l'assistente di supporto di Matter Lab, strumento scientifico per professionisti F&B "
        "(bar, panificazione, pasticceria, gelateria, caffetteria, cucina, vino, birra). "
        "COSA FA MATTER LAB: spiega la scienza del mestiere — 103 fenomeni fisici/chimici con numeri "
        "bersaglio misurabili al banco, 47 tecniche con esecuzione passo-passo, 53+ ricette ancorate "
        "a fenomeni e tecniche, un flavor network di 1.530 ingredienti per gli abbinamenti (per analogia "
        "e per contrasto), e una feature foto che riconosce ingredienti e bottiglie suggerendo abbinamenti. "
        "SEZIONI: Scopri (fenomeni), Lezione (percorso guidato), Mappa (atlante), Chiedi (assistente AI). "
        "Piano Pro a 19,99€/mese, con prova gratuita. "
        "Aiuta l'utente a usare l'app. NON inventare funzioni inesistenti. Se non sai o è un problema "
        "tecnico, di' che il team risponde via email entro 24 ore. Massimo 4 frasi, tono diretto e caldo."
    )
    # costruisci il contesto multi-turno
    conversazione = ""
    for h in history[-6:]:  # ultimi 6 messaggi
        ruolo = "Utente" if h.get("ruolo") == "utente" else "Assistente"
        conversazione += f"{ruolo}: {h.get('testo','')}\n"
    conversazione += f"Utente: {testo}"

    risposta = None
    try:
        resp = _haiku_raw(system_supporto + "\n\n" + conversazione, max_tokens=350)
        if resp:
            risposta = resp
    except Exception:
        pass
    if not risposta:
        risposta = ("Non riesco a rispondere in questo momento. "
                    "Il tuo messaggio è stato registrato — ti risponderemo via email entro 24 ore.")

    # notifica admin (tu) — arriva subito sulla tua Gmail
    admin_email = os.environ.get("MATTER_ADMIN_EMAIL", "miclam84@gmail.com")
    _invia_email_resend(
        to=admin_email,
        subject="⚠ Nuova richiesta supporto — Matter",
        body_html=(f"<p><strong>Nuova richiesta di supporto su Matter.</strong></p>"
                   f"<p><strong>Utente:</strong> {str(user_id) if user_id else 'non loggato'}</p>"
                   f"<p><strong>Messaggio:</strong><br>{testo}</p>"
                   f"<p><a href='/admin/assistenza'>Apri pannello assistenza →</a></p>"),
        body_text=f"Nuova richiesta supporto Matter.\nUtente: {user_id}\n\n{testo}"
    )

    return jsonify({"risposta": risposta})
