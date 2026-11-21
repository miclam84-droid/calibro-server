# -*- coding: utf-8 -*-
# termico.py — ancoraggio dell'asse TERMICO (freddo <-> caldo) ai marcatori che
# agiscono sui recettori termici (TRPM8 freddo, TRPV1/TRPA1 caldo).
#
# A DIFFERENZA degli altri assi, il termico e' DIREZIONALE (scala -10..+10):
# negativo = freddo (mentolo), positivo = caldo (capsaicina, cinnamaldeide, ...).
# Non e' intensita' misurata: e' la DIREZIONE della sensazione termica data dalla
# presenza di un agonista recettoriale documentato. Stesso spirito onesto degli
# altri (presenza sorgentata, niente potenza inventata), calcolato A LETTURA.
import csv
import os
import re
import threading

_LOCK = threading.Lock()
_REG = None

FORMULA_VER = "termico-marcatori-v1"

# magnitudine per numero di marcatori concordi nella direzione dominante (presenza).
_MAG = [(0, 0), (1, 6), (2, 7), (3, 8)]


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_termici.csv")


def _norm(s):
    return (s or "").strip().lower()


def _registro():
    global _REG
    if _REG is not None:
        return _REG
    with _LOCK:
        if _REG is not None:
            return _REG
        voci = []
        try:
            with open(_path(), encoding="utf-8") as f:
                righe = [ln for ln in f if not ln.lstrip().startswith("#")]
                for r in csv.DictReader(righe):
                    key = _norm(r.get("ingrediente_key"))
                    comp = (r.get("compound") or "").strip()
                    if not key or not comp:
                        continue
                    voci.append((key, {
                        "compound": comp,
                        "cas": (r.get("cas") or "").strip(),
                        "direzione": _norm(r.get("direzione")),
                        "classe": (r.get("classe") or "").strip(),
                        "fonte": (r.get("fonte") or "").strip(),
                    }))
        except FileNotFoundError:
            voci = []
        voci.sort(key=lambda kv: -len(kv[0]))
        _REG = voci
        return _REG


def _mag(n):
    if n <= 0:
        return 0
    prev = _MAG[0]
    for p in _MAG:
        if p[0] == n:
            return p[1]
        if p[0] > n:
            return prev[1]
        prev = p
    return _MAG[-1][1]


def _cita(fonte):
    parti = re.split(r"[;.]", fonte or "")
    cit = [s.strip() for s in parti if re.search(r"PubChem|Belitz|DOI|CID|\b(19|20)\d{2}\b", s, re.I)]
    return cit[0].strip() if cit else (fonte or "").strip()


def termico_di(nome):
    """Direzione termica di un ingrediente, o None. Scala -10..+10 (freddo..caldo).
    {voto, direzione:'caldo'|'freddo', stato, fonte, formula, stima, marcatori, nota}.
    Se i marcatori sono di direzioni opposte e pari, la direzione non e' netta -> None."""
    reg = _registro()
    if not reg:
        return None
    n = _norm(nome)
    if not n:
        return None
    key_match = []
    for key, info in reg:
        if re.search(r"\b" + re.escape(key) + r"\b", n):
            key_match.append((key, info))
    key_match = [
        (k, info) for (k, info) in key_match
        if not any(k != k2 and re.search(r"\b" + re.escape(k) + r"\b", k2) for (k2, _) in key_match)
    ]
    caldi, freddi, visti = [], [], set()
    for key, info in key_match:
        cid = (info.get("cas") or info.get("compound")).lower()
        if cid in visti:
            continue
        visti.add(cid)
        (caldi if info["direzione"] == "caldo" else freddi if info["direzione"] == "freddo" else []).append(info)
    if not caldi and not freddi:
        return None
    if len(caldi) == len(freddi):
        return None  # direzione non netta: non si forza
    dominante = caldi if len(caldi) > len(freddi) else freddi
    direzione = "caldo" if dominante is caldi else "freddo"
    marcatori = [t["compound"] for t in dominante]
    fonti = []
    for t in dominante:
        f = _cita(t.get("fonte"))
        if f and f not in fonti:
            fonti.append(f)
    mag = _mag(len(dominante))
    voto = mag if direzione == "caldo" else -mag
    return {
        "voto": voto,
        "direzione": direzione,
        "stato": "presenza-marcatori",
        "fonte": "marcatori molecolari — " + ", ".join(fonti),
        "formula": FORMULA_VER,
        "stima": True,
        "marcatori": marcatori,
        "nota": "Direzione " + direzione + ", da composti documentati: " + ", ".join(marcatori) + ".",
    }
