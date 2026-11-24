# -*- coding: utf-8 -*-
# piccante.py — ancoraggio dell'asse PICCANTE ai principi pungenti documentati.
#
# Stesso principio onesto della macchina-amaro (routes/deriva_amaro.py), ma:
#  - i marcatori del piccante sono NON volatili (capsaicinoidi, piperina, gingeroli,
#    isotiocianati, sanshool): NON stanno nei composti aromatici del nodo, quindi il
#    match e' per INGREDIENTE (registro data/composti_piccanti.csv), non per composto;
#  - si calcola A LETTURA (nessuna scrittura sul DB di produzione), come aromi.py.
#
# L'indice e' ORDINALE, sulla PRESENZA del principio pungente documentato, NON
# l'intensita' Scoville (che varia di ordini di grandezza e qui non e' sorgentata).
# Niente peso per potenza (non ha base citabile comune): peso 1 per marcatore distinto.
# Dove non c'e' un principio pungente noto -> None (non si tocca l'asse).
import csv
import os
import re
import threading

try:
    import i18n_composti as _i18nc
except Exception:
    _i18nc = None

_LOCK = threading.Lock()
_REG = None  # [(key, {compound, cas, classe, fonte})], ordinato per key piu' lunga prima

FORMULA_VER = "piccante-marcatori-v1"

# n. di principi pungenti distinti -> voto 0-10. Un principio pungente documentato
# segnala gia' piccante netto (presenza), piu' principi -> piu' alto, con saturazione.
_CURVA = [(0, 0), (1, 7), (2, 8), (3, 9)]


def _path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "composti_piccanti.csv")


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
        # key piu' lunga prima: "pepe bianco" batte "pepe"
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


def piccante_di(nome, lang="it"):
    """Principio(i) pungente(i) documentato(i) di un ingrediente, o None.
    {voto, stato:'presenza-marcatori', fonte, formula, stima, marcatori:[...], nota}.
    Match per inclusione sul nome (key piu' specifica prima); un marcatore conta una
    volta sola (per compound)."""
    reg = _registro()
    if not reg:
        return None
    n = _norm(nome)
    if not n:
        return None
    # chiavi che combaciano a CONFINE DI PAROLA ("pepe" NON matcha "peperoncino";
    # "pepe di sichuan" matcha solo la sua riga). Poi scarto la chiave generica quando
    # ne ha gia' matchata una piu' specifica che la contiene (pepe di sichuan > pepe).
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
        """Estrae la CITAZIONE della sorgente (PubChem/Belitz/DOI/anno), non la frase
        descrittiva. Se non trova un marcatore di citazione, ripiega sull'intero testo."""
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
        "nota": (_i18nc.nota_asse("piccante", marcatori, lang) if _i18nc else None)
                or ("Principio pungente documentato: " + ", ".join(marcatori) + "."),
    }
