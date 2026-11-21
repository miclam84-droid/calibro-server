# -*- coding: utf-8 -*-
# amaro.py — ancoraggio dell'asse AMARO ai marcatori molecolari documentati, PER
# INGREDIENTE (a lettura, nessuna scrittura sul DB di produzione).
#
# Perche' per ingrediente e non per composto aromatico: i composti amari (caffeina,
# naringina, limonina, cinaropicrina, amarogentina, umulone...) sono NON volatili ->
# NON stanno nei `composti_aromatici` del nodo. Lo stesso problema dei tannini in
# astringente.py: percio' si usa il registro data/composti_amari_ingredienti.csv,
# che lega il marcatore amaro all'ALIMENTO (fonte citabile), non al composto aromatico.
# La macchina vecchia routes/deriva_amaro.py (match sui composti aromatici) resta per
# i casi in cui il marcatore e' davvero fra gli aromi; questa copre i non-volatili.
#
# Indice ORDINALE di PRESENZA del marcatore amaro documentato, NON l'intensita' amara
# misurata. Peso 1 per marcatore distinto. I CAS/fonti sono quelli gia' verificati in
# data/composti_amari.csv (PubChem per i CAS).
import csv
import os
import re
import threading

_LOCK = threading.Lock()
_REG = None

FORMULA_VER = "amaro-marcatori-ingrediente-v1"

# n. di marcatori amari distinti -> voto 0-10. Un marcatore documentato segnala amaro
# netto (presenza); piu' marcatori -> piu' alto, con saturazione. Scala ORDINALE di
# presenza, NON intensita'. (L'intensita' vera e' la misura al banco, decisione #56.)
_CURVA = [(0, 0), (1, 5), (2, 6.5), (3, 7.5), (4, 8.5)]


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_amari_ingredienti.csv")


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


def amaro_di(nome):
    """Marcatore(i) amaro(i) documentato(i) di un ingrediente, o None.
    {voto, stato:'presenza-marcatori', fonte, formula, stima, marcatori, nota}.
    Match per ingrediente a confini di parola; se piu' chiavi combaciano, tiene solo
    le piu' specifiche (evita che 'arancia' mangi 'arancia amara')."""
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
    # tieni solo le chiavi non contenute in un'altra chiave combaciante (piu' specifica vince)
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
        "nota": "Presenza di composti amari documentati (" + ", ".join(marcatori) + "): indice ordinale, NON l'intensità amara misurata al banco.",
    }
