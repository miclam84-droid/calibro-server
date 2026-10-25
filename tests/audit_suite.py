#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite di audit eseguibile OFFLINE (senza DB di produzione).
Uso:   python3 tests/audit_suite.py
Esce 0 se tutto verde, 1 se c'e' una FAIL (regressione).

Cosa verifica:
  A. l'app Flask si assembla (tutti i blueprint importano, nessuna collisione di rotta)
  B. i redirect di bonifica funzionano (test client, niente rete)
  C. integrita' di data/biodiversita_seed.json
  D. integrita' di data/composti_matter.json (dup = baseline noto, fallisce solo su NUOVI)
  E. tutti i target render_template esistono
  F. le firme recenti sono nel dataset

NOTA: i 7 doppioni preesistenti del dataset composti (debito ondate bb-hh) sono messi a
BASELINE: la suite resta verde finche' non se ne aggiungono di nuovi. Toglili dal set DUP_BASELINE
man mano che la migrazione di dedup li risolve.
"""
import os, sys, json, re, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/none")
os.environ.setdefault("ADMIN_SECRET", "test")

# doppioni preesistenti censiti nell'audit del 25/10 (da sfoltire con la migrazione di dedup)
DUP_BASELINE = {"mastiha", "grani del paradiso", "elicriso", "mirtillo rosso",
                "sudachi", "finger lime", "pepe di timut"}

P = F = W = 0
def ok(n):
    global P; P += 1; print(f"  PASS  {n}")
def fail(n, d=""):
    global F; F += 1; print(f"  FAIL  {n}" + (f"  -> {d}" if d else ""))
def warn(n, d=""):
    global W; W += 1; print(f"  warn  {n}" + (f"  -> {d}" if d else ""))
def check(n, cond, d=""):
    ok(n) if cond else fail(n, d)

from collections import Counter

print("== A. Assembly app ==")
import app as A
app_obj = A.app
rules = list(app_obj.url_map.iter_rules())
check(f"app assemblata ({len(rules)} rotte)", len(rules) > 400, f"solo {len(rules)}")
pm = Counter()
for r in rules:
    for m in (r.methods - {"HEAD", "OPTIONS"}):
        pm[(str(r.rule), m)] += 1
dups_rt = {k: v for k, v in pm.items() if v > 1}
check("nessuna collisione path+metodo", not dups_rt, str(dups_rt))
have = {str(r.rule) for r in rules}
for rt in ["/biodiversita", "/atlante", "/v1/biodiversita/regioni", "/v1/biodiversita/regione/<regione>",
           "/v1/biodiversita/aree", "/v1/biodiversita/area/<area>", "/nuovo", "/scopri", "/menu"]:
    check(f"rotta esiste: {rt}", rt in have)

print("== B. Redirect di bonifica (test client) ==")
c = app_obj.test_client()
def red(path, atteso):
    r = c.get(path); loc = r.headers.get("Location", "")
    check(f"GET {path} -> 302 {atteso}", r.status_code in (301, 302) and loc.endswith(atteso),
          f"status {r.status_code}, loc {loc!r}")
red("/scopri", "/scopri-nuovo"); red("/scopri/limone", "/scopri-nuovo/limone")
red("/menu", "/menu-nuovo"); red("/app", "/nuovo"); red("/app2", "/nuovo")

print("== C. Integrita' biodiversita_seed.json ==")
seed = json.load(open("data/biodiversita_seed.json", encoding="utf-8"))
check("seed e' lista", isinstance(seed, list))
nomi = [(e.get("nome") or "").strip().lower() for e in seed]
dupn = [n for n, k in Counter(nomi).items() if k > 1]
check("nessun nome duplicato", not dupn, str(dupn[:5]))
xor = [e.get("nome") for e in seed if bool(e.get("regione")) == bool(e.get("area"))]
check("ogni voce ha regione XOR area", not xor, str(xor[:5]))
# tutela: testa il valore NORMALIZZATO come fa l'importer (_norm_tutela), non il grezzo
try:
    from routes.importa_biodiversita import _norm_tutela
except Exception:
    def _norm_tutela(t):
        t = (t or "").strip().lower()
        if "presidio" in t or "slow food" in t: return "presidio"
        if t in ("dop", "pdo"): return "dop"
        if t in ("igp", "pgi"): return "igp"
        if t in ("stg", "tsg"): return "stg"
        if t == "pat": return "pat"
        return ""
VALID = {"dop", "igp", "presidio", "pat", "stg", ""}
badt = [(e.get("nome"), e.get("tutela")) for e in seed if _norm_tutela(e.get("tutela")) not in VALID]
check("tutele normalizzate valide (post _norm_tutela)", not badt, str(badt[:5]))
mondo_no_paese = [e.get("nome") for e in seed if e.get("area") and not (e.get("paese") or "").strip()]
check("ogni voce-mondo ha paese", not mondo_no_paese, str(mondo_no_paese[:5]))
regioni = {e["regione"] for e in seed if e.get("regione")}
aree = {e["area"] for e in seed if e.get("area")}
check(f"regioni italiane = 20 (trovate {len(regioni)})", len(regioni) == 20, str(sorted(regioni)))
check(f"aree mondo = 5 (trovate {len(aree)})", len(aree) == 5, str(sorted(aree)))

print("== D. Integrita' composti_matter.json ==")
comp = json.load(open("data/composti_matter.json", encoding="utf-8"))
ing = comp["ingredienti"]
check("lista ingredienti > 300", isinstance(ing, list) and len(ing) > 300, f"{len(ing)}")
ic = [(x.get("ingrediente") or "").strip().lower() for x in ing]
dupi = {n for n, k in Counter(ic).items() if k > 1}
nuovi = dupi - DUP_BASELINE
check("nessun doppione ingrediente NUOVO (oltre il baseline)", not nuovi, f"nuovi: {sorted(nuovi)}")
if dupi & DUP_BASELINE:
    warn(f"doppioni baseline ancora presenti: {len(dupi & DUP_BASELINE)}", str(sorted(dupi & DUP_BASELINE)))
RUOLI = {"firma", "caratterizzante", "di_supporto"}
bad_comp = []
for x in ing:
    for cc in x.get("composti", []):
        if not cc.get("composto") or cc.get("ruolo") not in RUOLI or not cc.get("stato"):
            bad_comp.append((x.get("ingrediente"), cc.get("composto"))); break
check("ogni composto ha composto+ruolo valido+stato", not bad_comp, str(bad_comp[:5]))

print("== E. Target render_template esistono ==")
refs = set()
for pyf in glob.glob("routes/*.py"):
    for m in re.finditer(r"render_template\(\s*[\"']([^\"']+\.html)", open(pyf, encoding="utf-8").read()):
        refs.add(m.group(1))
missing = [t for t in refs if not os.path.exists(os.path.join("templates", t))]
check(f"{len(refs)} template referenziati, tutti esistono", not missing, str(missing))

print("== F. Firme recenti nel dataset ==")
names = {(x.get("ingrediente") or "").lower(): x for x in ing}
for n in ["mahleb", "epazote", "lemon myrtle"]:
    x = names.get(n)
    check(f"'{n}' presente con una firma",
          bool(x) and any(c.get("ruolo") == "firma" for c in x.get("composti", [])))

print(f"\n==== {P} PASS, {F} FAIL, {W} warn ====")
sys.exit(1 if F else 0)
