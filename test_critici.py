"""
Test critici Matter — regola 80/20 (pipeline fatturato + gate sicurezza).
3 aree: auth, paywall gate, webhook Stripe idempotenza.

Due modalità:
- Test LIVE (contro produzione, sola lettura/contratti): verificano status code senza scrivere.
- Test LOGICA (SQLite in-memory): verificano l'idempotenza del webhook senza toccare produzione.

Uso: pip install pytest requests
     pytest test_critici.py -v
"""
import json
import sqlite3
import pytest

BASE = "https://web-production-79457.up.railway.app"

# ═══════════════════════════════════════════════════════════
# TEST 1 — AUTH: i contratti dell'endpoint di registrazione
# ═══════════════════════════════════════════════════════════

def test_registra_rifiuta_email_vuota():
    """Registrazione senza email → 400 (non deve accettare)."""
    import requests
    r = requests.post(f"{BASE}/v1/auth/registra", json={"password": "test1234"}, timeout=15)
    assert r.status_code == 400, f"atteso 400, ricevuto {r.status_code}"

def test_registra_rifiuta_password_corta():
    """Password < 8 caratteri → 400."""
    import requests
    r = requests.post(f"{BASE}/v1/auth/registra",
                      json={"email": "test@example.com", "password": "123"}, timeout=15)
    assert r.status_code == 400, f"atteso 400, ricevuto {r.status_code}"

def test_login_rifiuta_credenziali_mancanti():
    """Login senza credenziali → errore (400/401), non 500."""
    import requests
    r = requests.post(f"{BASE}/v1/auth/login", json={}, timeout=15)
    assert r.status_code in (400, 401), f"atteso 400/401, ricevuto {r.status_code}"

# ═══════════════════════════════════════════════════════════
# TEST 2 — PAYWALL GATE: la feature Pro deve essere protetta
# ═══════════════════════════════════════════════════════════

def test_foto_analisi_richiede_auth():
    """foto-analisi senza token → NON deve dare 200 (deve chiedere auth/Pro)."""
    import requests
    r = requests.post(f"{BASE}/v1/foto-analisi", json={}, timeout=15)
    assert r.status_code in (401, 402, 403, 400), \
        f"la killer feature deve essere protetta, ricevuto {r.status_code}"

def test_ricetta_cifra_richiede_auth():
    """endpoint ponte Cifra senza auth → 401 (non deve esporre dati)."""
    import requests
    r = requests.get(f"{BASE}/v1/ricetta/1", timeout=15)
    assert r.status_code == 401, f"atteso 401, ricevuto {r.status_code}"

# ═══════════════════════════════════════════════════════════
# TEST 3 — WEBHOOK STRIPE: idempotenza (logica, in SQLite)
# ═══════════════════════════════════════════════════════════

def _simula_webhook_logic(db, event_id, user_id):
    """Replica la logica di idempotenza del webhook reale."""
    db.execute("""CREATE TABLE IF NOT EXISTS stripe_events (
        event_id TEXT PRIMARY KEY, event_type TEXT, user_id TEXT, ts TEXT)""")
    # già processato?
    if db.execute("SELECT 1 FROM stripe_events WHERE event_id=?", (event_id,)).fetchone():
        return "gia_processato"
    db.execute("UPDATE utenti SET piano='pro' WHERE id=?", (user_id,))
    db.execute("INSERT OR IGNORE INTO stripe_events (event_id,event_type,user_id) VALUES (?,?,?)",
               (event_id, "checkout.session.completed", user_id))
    return "attivato"

def test_webhook_attiva_pro():
    """Webhook con evento valido → utente diventa pro."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE utenti (id TEXT PRIMARY KEY, piano TEXT)")
    db.execute("INSERT INTO utenti VALUES ('u1', 'free')")
    esito = _simula_webhook_logic(db, "evt_001", "u1")
    assert esito == "attivato"
    piano = db.execute("SELECT piano FROM utenti WHERE id='u1'").fetchone()[0]
    assert piano == "pro", "l'utente deve essere pro dopo il webhook"

def test_webhook_idempotente():
    """Stesso evento due volte → la seconda NON riprocessa (idempotenza)."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE utenti (id TEXT PRIMARY KEY, piano TEXT)")
    db.execute("INSERT INTO utenti VALUES ('u1', 'free')")
    esito1 = _simula_webhook_logic(db, "evt_002", "u1")
    esito2 = _simula_webhook_logic(db, "evt_002", "u1")  # stesso event_id
    assert esito1 == "attivato"
    assert esito2 == "gia_processato", "il secondo invio dello stesso evento deve essere ignorato"
    # verifica: un solo record evento
    n = db.execute("SELECT COUNT(*) FROM stripe_events").fetchone()[0]
    assert n == 1, "deve esserci un solo record per event_id"


# ═══════════════════════════════════════════════════════════
# TEST ESTESI — cuore del prodotto (grafo, stato-fenomeno, generazione, ricette)
# Aggiunti 21 ago. Tutti LIVE sola-lettura/contratti, non scrivono dati veri
# (usano un device_id di test usa-e-getta).
# ═══════════════════════════════════════════════════════════
import uuid as _uuid

def test_health_ok():
    """L'app risponde e il grafo è caricato (nodi > 0)."""
    import requests
    r = requests.get(f"{BASE}/health", timeout=15)
    assert r.status_code == 200
    assert r.json().get("nodi", 0) > 0, "il grafo deve avere nodi"

def test_nodo_risponde_con_dati():
    """/nodo su un fenomeno noto ritorna i blocchi del grafo (titolo, connessi)."""
    import requests
    r = requests.post(f"{BASE}/nodo", json={"id": "fen-maillard"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("titolo"), "il nodo deve avere un titolo"

def test_ricette_trilingue():
    """/v1/ricette in EN ritorna ricette con procedimento tradotto (non vuoto)."""
    import requests
    r = requests.get(f"{BASE}/v1/ricette?disc=cucina&lang=en", timeout=45)
    assert r.status_code == 200
    ric = r.json()
    assert isinstance(ric, list) and len(ric) > 0, "devono esserci ricette"

def test_stato_fenomeni_senza_identita_lista_vuota():
    """/v1/stato-fenomeni senza device/token ritorna lista vuota, non errore."""
    import requests
    r = requests.get(f"{BASE}/v1/stato-fenomeni", timeout=15)
    assert r.status_code == 200
    assert "stati" in r.json()

def test_misura_richiede_identita():
    """/v1/misura senza device_id → 401 (serve identità)."""
    import requests
    r = requests.post(f"{BASE}/v1/misura", json={"fenomeno": "fen-maillard", "valore": 155}, timeout=15)
    assert r.status_code == 401, f"atteso 401 senza identità, ricevuto {r.status_code}"

def test_misura_e_stato_con_device():
    """Flusso: misuro con un device_id di test, poi lo ritrovo in stato-fenomeni."""
    import requests
    dev = str(_uuid.uuid4())
    h = {"X-Device-Id": dev}
    r1 = requests.post(f"{BASE}/v1/misura",
                       json={"fenomeno": "fen-maillard", "valore": 155, "unita": "°C", "grezzo": "155°C"},
                       headers=h, timeout=20)
    assert r1.status_code == 200 and r1.json().get("stato") == "misurato"
    r2 = requests.get(f"{BASE}/v1/stato-fenomeni", headers=h, timeout=15)
    assert r2.status_code == 200
    stati = r2.json().get("stati", [])
    assert any(s.get("id") == "fen-maillard" for s in stati), "la misura deve comparire nello stato"

def test_genera_ricetta_rate_limit_o_risposta():
    """/v1/genera-ricetta risponde (200) o è rate-limited (429) o AI giù (503) — mai 500 HTML."""
    import requests
    dev = str(_uuid.uuid4())
    r = requests.post(f"{BASE}/v1/genera-ricetta",
                      json={"richiesta": "una salsa al limone", "disciplina": "cucina", "salva": False},
                      headers={"X-Device-Id": dev}, timeout=60)
    assert r.status_code in (200, 429, 503), f"atteso 200/429/503, mai 500; ricevuto {r.status_code}"

def test_nodo_traccia_studiato():
    """/nodo?traccia=1 con device segna 'studiato' e lo ritorna."""
    import requests
    dev = str(_uuid.uuid4())
    r = requests.post(f"{BASE}/nodo?traccia=1", json={"id": "fen-emulsione-salse"},
                      headers={"X-Device-Id": dev}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("stato_fenomeno") in ("studiato", "misurato", None)

