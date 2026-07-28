# ============================================================
# notifiche.py — invio email via Resend. Util autocontenuto (os + urllib).
# Usato da app.py (registrazione/reset) e dal blueprint admin (assistenza).
# ============================================================
import os


def _invia_email_resend(to, subject, body_html, body_text=None):
    """Invia email via Resend. Mittente: onboarding@resend.dev (sandbox) finché
    non viene verificato un dominio proprio — allora cambiare RESEND_FROM.
    Ritorna True se ok, False se fallisce (mai blocca il flusso chiamante)."""
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        return False
    mittente = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    try:
        import urllib.request, json as _json
        payload = _json.dumps({
            "from": f"Matter <{mittente}>",
            "to": [to],
            "subject": subject,
            "html": body_html,
            "text": body_text or body_html
        }).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception:
        return False
