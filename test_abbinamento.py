# -*- coding: utf-8 -*-
"""Test di regressione del MOTORE ABBINAMENTO (Fase 0, post-revisore).
Cattura i bug gia' visti perche' non tornino. Gira sul vivo (read-only), senza DB locale.
Uso:  python3 test_abbinamento.py            (default: produzione Railway)
      BASE=http://localhost:8000 python3 test_abbinamento.py
NON richiede pytest. Esce 0 se tutto PASS, 1 se qualcosa FALLISCE."""
import os, sys, json, urllib.request

BASE = os.environ.get("BASE", "https://web-production-79457.up.railway.app").rstrip("/")
fail = 0


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.load(r)


def check(nome, cond, dettaglio=""):
    global fail
    stato = "PASS" if cond else "FAIL"
    if not cond:
        fail += 1
    print(f"[{stato}] {nome}" + (f"  — {dettaglio}" if dettaglio and not cond else ""))


def rel_base(ing):
    d = get(f"/v1/criteri/{ing}?v=test")
    return [x for x in d.get("relazioni", []) if x.get("criterio") == "base_aromatica"], d


# 1. Anti-hub: il te' nero NON deve essere in cima al pomodoro (bug del conteggio grezzo)
base, _ = rel_base("pomodoro")
top = base[0]["ingrediente"].lower() if base else ""
check("pomodoro: il 1o abbinamento non e' 'te nero'", "te" not in top and "tè" not in top, f"1o = {top!r}")

# 2. Il ranking espone l'indice di rarita' (IDF attivo, non conteggio grezzo)
check("pomodoro: base_aromatica ha 'indice_rarita'",
      bool(base) and "indice_rarita" in (base[0].get("evidenza") or {}),
      "manca indice_rarita nell'evidenza")

# 3. I composti mostrati sono i 'caratterizzanti' (non piu' 'composti' grezzi)
check("pomodoro: evidenza mostra 'composti_caratterizzanti'",
      bool(base) and "composti_caratterizzanti" in (base[0].get("evidenza") or {}))

# 4. I tre criteri vivi esistono sull'ingrediente
_, d = rel_base("pomodoro")
criteri = {x.get("criterio") for x in d.get("relazioni", [])}
check("pomodoro: criterio 'base_aromatica' presente", "base_aromatica" in criteri)

# 5. Link verticali fenomeni: materializzati, nessuna proposta residua (idempotenza dell'apply)
lf = get("/v1/criteri/link-fenomeni?v=test")
check("link-fenomeni: 0 proposte residue (archi gia' materializzati)",
      lf.get("proposte_arco") == 0, f"proposte_arco = {lf.get('proposte_arco')}")
check("link-fenomeni: gia_linkati >= 860", (lf.get("gia_linkati") or 0) >= 860,
      f"gia_linkati = {lf.get('gia_linkati')}")

# 6. grafo-stato risponde con la copertura dati (forma attesa)
gs = get("/v1/criteri/grafo-stato?v=test")
cop = gs.get("copertura_dati", {})
check("grafo-stato: copertura_dati presente", bool(cop))

# 7. L'endpoint di scrittura e' PROTETTO (senza secret -> 403), non piu' aperto
try:
    urllib.request.urlopen(BASE + "/v1/criteri/link-fenomeni/applica?conferma=applica", timeout=20)
    check("apply protetto: senza secret deve dare 403", False, "ha risposto 200 senza secret")
except urllib.error.HTTPError as e:
    check("apply protetto: senza secret deve dare 403", e.code == 403, f"codice {e.code}")

print("\n" + ("TUTTO VERDE" if fail == 0 else f"{fail} TEST FALLITI"))
sys.exit(1 if fail else 0)
