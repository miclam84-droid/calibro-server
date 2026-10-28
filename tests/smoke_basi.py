#!/usr/bin/env python3
"""Smoke-test coperture basi — la rete anti-regressione.
Centra gli ingredienti piu' ovvi (cucina/bar/bakery) contro un'istanza viva e verifica:
  (1) la ricerca li RISOLVE (diag),
  (2) il nodo ha composti (>0),
  (3) esiste una foto (url != null).
Stampa la lista dei ROTTI. Uso: python3 tests/smoke_basi.py [BASE_URL]
Default BASE_URL = prod. Esce 1 se c'e' anche un solo rotto su RESOLVE o COMPOSTI
(la foto mancante e' warning, non blocco)."""
import sys, json, urllib.parse, urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else
        "https://web-production-79457.up.railway.app").rstrip("/")

# Ingredienti che un cuoco / barman / fornaio digita per PRIMI (mondo di Michele:
# cucina napoletana, cocktail bar Bucopertuso, bakery Bucolico).
BASI = [
    # --- cucina: ortaggi/verdure ---
    "pomodoro", "melanzana", "zucchina", "fiori di zucca", "peperone", "peperoncino",
    "cipolla", "aglio", "patata", "carota", "zucca", "finocchio", "carciofo", "sedano",
    "spinaci", "broccoli", "cavolfiore", "friarielli", "scarola", "cetriolo", "porro",
    # --- funghi ---
    "funghi", "champignon", "cardoncelli", "porcini",
    # --- erbe/aromi ---
    "basilico", "prezzemolo", "menta", "salvia", "rosmarino", "origano", "timo", "alloro",
    # --- frutta/agrumi ---
    "limone", "arancia", "pompelmo", "mela", "pera", "fragola", "lampone", "fico",
    # --- frutta secca ---
    "mandorla", "nocciola", "pistacchio", "pinoli", "noce",
    # --- latticini ---
    "parmigiano", "mozzarella", "ricotta", "burrata", "burro", "latte",
    # --- pesce/mare ---
    "acciughe", "tonno", "baccala", "polpo", "gambero", "vongole", "cozze",
    # --- carne ---
    "manzo", "maiale", "pollo", "agnello", "guanciale", "pancetta",
    # --- dispensa/bakery ---
    "olio di oliva", "aceto", "farina", "uova", "zucchero", "miele", "cacao", "vaniglia",
    "cannella", "lievito", "caffe",
    # --- bar/distillati/mixology ---
    "gin", "rum", "vodka", "whisky", "cognac", "vermouth", "bitter", "lime", "zenzero",
    "chiodi di garofano", "cardamomo",
]

def _get(path):
    url = BASE + "/" + urllib.parse.quote(path)
    req = urllib.request.Request(url, headers={"User-Agent": "Matter-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def check(nome):
    out = {"nome": nome, "risolve": False, "composti": 0, "foto": False, "nodo": None}
    try:
        d = _get("v1/criteri/diag/" + nome)
        if d.get("nodo_risolto"):
            out["risolve"] = True
            out["composti"] = d.get("composti_totali", 0)
            out["nodo"] = d.get("nodo_risolto")
    except Exception as e:
        out["errore"] = str(e)[:80]
    try:
        f = _get("v1/foto-ingrediente/" + nome)
        out["foto"] = bool(f.get("url"))
    except Exception:
        pass
    return out

def main():
    print(f"Smoke basi su {BASE} — {len(BASI)} ingredienti\n")
    rotti_resolve, rotti_comp, senza_foto, ok = [], [], [], []
    for n in BASI:
        r = check(n)
        if not r["risolve"]:
            rotti_resolve.append(r); stato = "NON RISOLVE"
        elif r["composti"] == 0:
            rotti_comp.append(r); stato = "RISOLVE ma 0 COMPOSTI"
        else:
            ok.append(r); stato = f"ok ({r['composti']} comp)"
        if r["risolve"] and not r["foto"]:
            senza_foto.append(r)
        foto = "" if r["foto"] else "  [SENZA FOTO]"
        print(f"  {n:<22} {stato}{foto}")

    print("\n==== RIEPILOGO ====")
    print(f"  ok: {len(ok)}/{len(BASI)}")
    print(f"  NON RISOLVE ({len(rotti_resolve)}): {[r['nome'] for r in rotti_resolve]}")
    print(f"  0 COMPOSTI ({len(rotti_comp)}): {[r['nome'] for r in rotti_comp]}")
    print(f"  senza foto ({len(senza_foto)}): {[r['nome'] for r in senza_foto]}")
    rotti = len(rotti_resolve) + len(rotti_comp)
    print(f"\n{'FALLITO' if rotti else 'VERDE'}: {rotti} ingredienti base rotti (resolve/composti).")
    return 1 if rotti else 0

if __name__ == "__main__":
    sys.exit(main())
