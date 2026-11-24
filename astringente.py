# -*- coding: utf-8 -*-
# astringente.py — ancoraggio dell'asse ASTRINGENTE ai tannini documentati.
#
# Stesso principio onesto di piccante.py / deriva_amaro.py:
#  - i tannini (catechine/teaflavine, proantocianidine, ellagitannini) sono NON
#    volatili: NON stanno nei composti aromatici del nodo, quindi il match e' per
#    INGREDIENTE (registro data/composti_astringenti.csv), non per composto;
#  - si calcola A LETTURA (nessuna scrittura sul DB di produzione).
#
# Indice ORDINALE di PRESENZA del tannino documentato, NON l'intensita' di
# astringenza misurata. Niente potenza inventata: peso 1 per marcatore distinto.
import csv
import os
import re
import threading

try:
    import i18n_composti as _i18nc
except Exception:
    _i18nc = None

_LOCK = threading.Lock()
_REG = None

FORMULA_VER = "astringente-marcatori-v1"

# n. di tannini distinti -> voto 0-10. Un tannino documentato segnala astringenza
# netta (presenza); piu' tannini -> piu' alto, con saturazione. Scala ordinale.
_CURVA = [(0, 0), (1, 6), (2, 7), (3, 8)]


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_astringenti.csv")


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
                        "classe": (r.get("classe") or "").strip(),
                        "fonte": (r.get("fonte") or "").strip(),
                    }))
        except FileNotFoundError:
            voci = []
        voci.sort(key=lambda kv: -len(kv[0]))
        _REG = voci
        return _REG


def _indice(n):
    if n <= 0:
        return 0
    prev = _CURVA[0]
    for p in _CURVA:
        if p[0] == n:
            return p[1]
        if p[0] > n:
            return prev[1]
        prev = p
    return _CURVA[-1][1]


def astringente_di(nome, lang="it"):
    """Tannino(i) documentato(i) di un ingrediente, o None.
    {voto, stato:'presenza-marcatori', fonte, formula, stima, marcatori, nota}."""
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
    trovati = []
    visti = set()
    for key, info in key_match:
        cid = (info.get("cas") or info.get("compound")).lower()
        if cid not in visti:
            visti.add(cid)
            trovati.append(info)
    if not trovati:
        return None
    marcatori = [t["compound"] for t in trovati]

    def _cita(fonte):
        parti = re.split(r"[;.]", fonte or "")
        cit = [s.strip() for s in parti if re.search(r"PubChem|Belitz|DOI|CID|\b(19|20)\d{2}\b", s, re.I)]
        return cit[0].strip() if cit else (fonte or "").strip()

    fonti = []
    for t in trovati:
        f = _cita(t.get("fonte"))
        if f and f not in fonti:
            fonti.append(f)
    return {
        "voto": _indice(len(trovati)),
        "stato": "presenza-marcatori",
        "fonte": "marcatori molecolari — " + ", ".join(fonti),
        "formula": FORMULA_VER,
        "stima": True,
        "marcatori": marcatori,
        "nota": (_i18nc.nota_asse("astringente", marcatori, lang) if _i18nc else None)
                or ("Tannini documentati: " + ", ".join(marcatori) + "."),
    }
