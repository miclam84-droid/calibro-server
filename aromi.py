# -*- coding: utf-8 -*-
# aromi.py — derivazione degli aromi dai composti reali (data/composti_matter.json).
#
# Decisione di prodotto #44 (CANONE): la NOTA CONCRETA ha la precedenza sull'etichetta
# astratta. Mostriamo prima le note aromatiche reali (i descrittori dei composti,
# ordinati per ruolo firma>caratterizzante>supporto), poi il CARATTERE caldo/fresco
# come orientamento SECONDARIO. Nessun dato inventato: le note sono i descrittori
# del dataset; il carattere e' derivato classificando quei descrittori e pesando
# per ruolo. La catena resta esplicita:
#   composto identificato -> nota associata -> profilo derivato -> percezione effettiva
# (la percezione dipende da concentrazione, matrice, soglia olfattiva e contesto:
#  presenza chimica != esperienza sensoriale).
import json
import os
import re
import threading

_LOCK = threading.Lock()
_CACHE = None  # {nome_lower: {nome, note, carattere}}

# peso del contributo al carattere, per ruolo del composto
_PESO = {"firma": 3, "caratterizzante": 2, "di_supporto": 1, "supporto": 1}

# MAPPA descrittore -> famiglia. Gli ambigui (floreale, fruttato, dolce, grasso,
# mela, rosa...) restano NEUTRI: non contribuiscono, per non forzare.
_CALDO = {
    "tostato", "legnoso", "speziato", "caramello", "miele", "maltato", "resinoso", "balsamico",
    "nocciola", "burroso", "burro", "terroso", "fungo", "fungo-terroso", "fungino", "legnoso-speziato",
    "mandorla", "patata lessa", "mela cotta", "zolfo", "cuoio", "tabacco", "affumicato", "cacao", "caffe",
    "caffè", "vaniglia", "ambrato", "fieno", "carne", "brodo", "carne arrosto-brodo", "arrosto", "pane",
    "crosta", "cannella", "chiodo", "noce moscata", "pepe", "liquirizia", "anice", "fave", "cotto",
}
_FRESCO = {
    "verde", "agrume", "fresco", "erbaceo", "erba", "verde-erba", "foglia", "verde-foglia", "menta",
    "mentolato", "agrumato", "marino", "pomodoro fresco", "foglia di pomodoro", "pino", "citrico",
    "limone", "lime", "eucalipto", "canfora", "balsamico-fresco", "cetriolo", "resinoso-pino",
    "bergamotto", "pompelmo", "mela verde", "aghi", "resina", "terpenico", "fresco-verde", "erba tagliata",
    "rinfrescante",
}

_ORD_RUOLO = {"firma": 0, "caratterizzante": 1, "di_supporto": 2, "supporto": 2}


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_matter.json")


def _tok(desc):
    """Scompone un descrittore in note atomiche leggibili. Toglie le parentesi
    (es. '(firma)', '(soprattutto cassia)') ma tiene i trattini interni, che fanno
    parte della nota ('dolce-speziato', 'patata lessa-vegetale')."""
    out = []
    for t in re.split(r"[\/,;]", str(desc or "").lower()):
        t = re.sub(r"\(.*?\)", "", t).strip()
        if t:
            out.append(t)
    return out


def _classifica(tok):
    """caldo | fresco | None. Match esatto o per inclusione su parole-chiave forti.
    Un token ambiguo (caldo E fresco insieme) resta neutro."""
    c = tok in _CALDO
    f = tok in _FRESCO
    if not c and not f:
        for k in _CALDO:
            if k in tok:
                c = True
                break
        for k in _FRESCO:
            if k in tok:
                f = True
                break
    if c and f:
        return None
    return "caldo" if c else ("fresco" if f else None)


def _costruisci():
    global _CACHE
    if _CACHE is not None:
        return
    with _LOCK:
        if _CACHE is not None:
            return
        try:
            with open(_path(), encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            _CACHE = {}
            return
        ING = d.get("ingredienti", []) or []
        per_ing = {}
        for x in ING:
            nome = (x.get("ingrediente") or "").strip()
            if not nome:
                continue
            comps = [c for c in (x.get("composti") or []) if isinstance(c, dict)]
            comps.sort(key=lambda c: _ORD_RUOLO.get((c.get("ruolo") or "").lower(), 3))
            sc_c = sc_f = 0
            note = []
            seen = set()
            nome_low = nome.lower()
            for c in comps:
                ruolo = (c.get("ruolo") or "").lower()
                peso = _PESO.get(ruolo, 1)
                fam = set()
                for t in _tok(c.get("descrittore")):
                    cl = _classifica(t)
                    if cl:
                        fam.add(cl)
                    # nota concreta: scarto il token uguale al nome dell'ingrediente
                    if t and t != nome_low and t not in seen:
                        seen.add(t)
                        note.append({"nota": t, "ruolo": ruolo, "composto": c.get("composto", "")})
                if "caldo" in fam:
                    sc_c += peso
                if "fresco" in fam:
                    sc_f += peso
            per_ing[nome_low] = {"nome": nome, "sc_c": sc_c, "sc_f": sc_f, "note": note[:6]}

        # soglie relative al dataset: "alto" = 85° percentile degli score non nulli
        cs = sorted([v["sc_c"] for v in per_ing.values() if v["sc_c"] > 0])
        fs = sorted([v["sc_f"] for v in per_ing.values() if v["sc_f"] > 0])

        def _perc(lst, p):
            if not lst:
                return 1
            return lst[min(len(lst) - 1, int(len(lst) * p))] or 1

        hic = _perc(cs, 0.85)
        hif = _perc(fs, 0.85)

        def _fascia(s, hi):
            if s <= 0:
                return None
            r = s / hi
            return "alto" if r >= 0.66 else ("medio" if r >= 0.33 else "basso")

        for v in per_ing.values():
            v["carattere"] = {"caldo": _fascia(v["sc_c"], hic), "fresco": _fascia(v["sc_f"], hif)}
        _CACHE = per_ing


def aroma_di(nome):
    """Ritorna l'aroma derivato di un ingrediente, o None se non nel dataset.
    {ingrediente, note_concrete:[{nota,ruolo,composto}], carattere:{caldo,fresco},
     fonte, catena, nota_percezione}."""
    _costruisci()
    if not _CACHE:
        return None
    key = (nome or "").strip().lower()
    v = _CACHE.get(key)
    if not v:
        cand = [k for k in _CACHE if key and (key in k or k in key)]
        cand.sort(key=len)
        v = _CACHE.get(cand[0]) if cand else None
    if not v:
        return None
    return {
        "ingrediente": v["nome"],
        "note_concrete": v["note"],
        "carattere": v["carattere"],
        "fonte": "Derivato dai composti aromatici del dataset Matter (descrittori reali da letteratura GC-MS/GC-O, pesati per ruolo).",
        "catena": "composto identificato → nota associata → profilo derivato → percezione effettiva",
        "nota_percezione": "La percezione reale dipende da concentrazione, matrice, soglia olfattiva e contesto: la presenza chimica non è l'esperienza sensoriale.",
    }


def stato_copertura():
    """Diagnostica: quanti ingredienti hanno almeno una nota / un carattere derivato."""
    _costruisci()
    tot = len(_CACHE)
    con_note = sum(1 for v in _CACHE.values() if v["note"])
    con_car = sum(1 for v in _CACHE.values() if v["carattere"]["caldo"] or v["carattere"]["fresco"])
    return {"totale": tot, "con_note": con_note, "con_carattere": con_car}
