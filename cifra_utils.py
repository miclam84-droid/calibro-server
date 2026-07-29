# ============================================================
# cifra_utils.py — helper per l'integrazione Matter→Cifra:
# autenticazione service key, costo categoria, profilo sicurezza.
# ============================================================
import os, json
from flask import request
from db import _get_conn, _release_conn
from config import DATABASE_URL


def _stima_costo_categoria(categoria, nome=None):
    """Stima orientativa del costo per categoria merceologica (€/kg o €/L).
    Usa prezzi ISMEA se disponibili per nome specifico."""
    # Prima cerca per nome specifico nei prezzi ISMEA
    if nome:
        nome_low = nome.lower()
        for k, v in _PREZZI_ISMEA.items():
            if k in nome_low or nome_low in k:
                return v
    COSTI = {
        "distillati": 35.0, "liquori": 20.0, "vino": 8.0, "birra": 3.5,
        "succhi": 4.0, "sciroppi": 5.0, "frutta fresca": 3.5,
        "verdure": 2.0, "carni": 12.0, "salumi": 18.0, "pesce": 15.0,
        "latticini": 4.0, "formaggi": 14.0, "uova": 3.0,
        "farine": 1.5, "zuccheri": 1.2, "grassi": 6.0,
        "spezie": 25.0, "erbe aromatiche": 8.0,
        "cioccolato": 12.0, "cacao": 8.0,
        "caffè": 18.0, "tè": 12.0,
        "frutta secca": 20.0, "paste frutta secca": 35.0,
        "luppoli": 30.0, "malti": 2.5, "lieviti": 5.0,
        "uve": 2.0, "gelatine": 20.0, "addensanti": 15.0,
    }
    cat_low = categoria.lower() if categoria else ""
    for k, v in COSTI.items():
        if k in cat_low or cat_low in k:
            return v
    return 5.0  # default generico


def _auth_cifra():
    """Risolve l'identità utente per le API Cifra.
    Accetta due modalità:
    - Token utente Matter: Authorization: Bearer {token}
    - Integrazione Cifra: Authorization: Bearer {MATTER_SERVICE_KEY}
                          X-User-Email: {email_utente}
    Restituisce user_id (str) o None se non autenticato.
    """
    auth = request.headers.get("Authorization","").replace("Bearer ","").strip()
    service_key = _os.environ.get("MATTER_SERVICE_KEY","")

    # Modalità Cifra: service key + email
    if service_key and auth == service_key:
        email = request.headers.get("X-User-Email","").strip().lower()
        if not email or not DATABASE_URL:
            return None
        try:
            import psycopg2
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("SELECT id FROM utenti WHERE lower(email)=%s AND attivo=TRUE", (email,))
            row = cur.fetchone()
            cur.close(); _release_conn(conn)
            return str(row[0]) if row else None
        except Exception:
            return None

    # Modalità utente diretto: token sessione Matter
    return _utente_da_token(auth)


def _calcola_profilo_sicurezza(ph=None, brix=None, aw=None, idratazione=None,
                               temperatura=4.0, nome=None, disciplina=None):
    """Helper condiviso per il calcolo del profilo sicurezza alimentare.
    Usato sia dall'endpoint con ricetta salvata che dall'endpoint stateless Cifra.
    Tutti i parametri sono opzionali — i valori mancanti restano None.
    """
    # ── Stima Aw ────────────────────────────────────────────
    aw_stimata = aw  # se Cifra la manda direttamente, usiamo quella
    if aw_stimata is None:
        if brix is not None:
            aw_stimata = round(1.0 - float(brix) * 0.0023, 3)
        elif idratazione is not None:
            aw_stimata = round(0.95 + float(idratazione) * 0.0004, 3)
            aw_stimata = min(aw_stimata, 0.99)

    t_cons = float(temperatura) if temperatura else 4.0
    ph_val = float(ph) if ph else None
    zona_pericolo = (t_cons > 4.0 and t_cons < 60.0)

    # ── Score Hurdle Technology ──────────────────────────────
    score = 0
    if aw_stimata is not None:
        if aw_stimata < 0.60: score += 4
        elif aw_stimata < 0.85: score += 3
        elif aw_stimata < 0.93: score += 2
        elif aw_stimata < 0.97: score += 1
    if ph_val is not None:
        if ph_val < 3.5: score += 4
        elif ph_val < 4.0: score += 3
        elif ph_val < 4.6: score += 2
        elif ph_val < 5.5: score += 1
    if t_cons <= 4: score += 2
    elif t_cons <= 8: score += 1

    giorni_map = [1, 2, 4, 7, 14, 30, 90, 180]
    shelf_life = giorni_map[min(score, 7)]

    # ── Flag rischio ─────────────────────────────────────────
    metodo_conservazione = []
    if zona_pericolo:
        flag_rischio = "conservare fuori dalla zona di pericolo (4°C–60°C)"
        metodo_conservazione = ["refrigerazione"]
    elif t_cons <= 4:
        flag_rischio = "conservare sotto 4°C — shelf life limitata" if shelf_life <= 3 else None
        metodo_conservazione = ["refrigerazione"]
    else:
        flag_rischio = "verificare temperatura di conservazione"
        metodo_conservazione = ["refrigerazione"]

    if aw_stimata and aw_stimata < 0.85:
        metodo_conservazione.append("conservazione a temperatura ambiente")
    if ph_val and ph_val < 4.6:
        metodo_conservazione.append("acidificazione")

    note = (f"shelf life orientativa {shelf_life} giorni a {t_cons}°C"
            + (f" · pH {ph_val}" if ph_val else "")
            + (f" · Aw {aw_stimata}" if aw_stimata else ""))

    return {
        "aw_stimata": aw_stimata,
        "ph_stimato": ph_val,
        "temperatura_conservazione_max_c": t_cons,
        "shelf_life_giorni": shelf_life,
        "zona_pericolo": zona_pericolo,
        "flag_rischio": flag_rischio,
        "metodo_conservazione": metodo_conservazione,
        "note_sicurezza": note,
        "disclaimer": (
            "Valori orientativi basati su modelli scientifici. "
            "Non sostituiscono test microbiologici né la consulenza "
            "di un professionista HACCP abilitato."
        )
    }


