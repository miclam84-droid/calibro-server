# ============================================================
# USDA SR LEGACY — regole di DEDUP (funzioni pure, niente rete, niente DB).
#
# Scopo: da food.csv di USDA SR Legacy (7.793 righe) ricavare una "voce-base"
# per alimento, collassando le VARIANTI di stato/cottura dello STESSO alimento
# (crudo/cotto/bollito/arrostito/in scatola/...) ma TENENDO distinti i tagli,
# i tipi e le specie (es. "Beef, chuck" != "Beef, rib"; "Rice, white" != "Rice, brown").
#
# Convenzione del nome USDA: "Base, qualificatore1, qualificatore2, ...".
# Un segmento che è SOLO stato/cottura/preparazione non distingue un alimento,
# quindi viene scartato per costruire la CHIAVE-BASE.
#
# NB: queste sono funzioni di ANALISI/FATTIBILITÀ. Non scrivono nel grafo,
# non toccano app.py. Servono a stimare quante voci-base si otterrebbero.
# Allineate nello spirito alle guardie già presenti in
# routes/deriva_gusti_search.py (_usda_composito, _non_sensoriale).
# ============================================================
import re

# Segmenti che sono puro stato / cottura / preparazione / qualificatore di resa.
# Se un segmento è composto SOLO da queste parole, non identifica un alimento
# diverso: è la stessa materia prima in un altro stato.
STATO = set("""
raw cooked boiled broiled braised roasted baked fried stewed grilled steamed
microwaved poached simmered sauteed toasted blanched canned frozen dried dehydrated
fresh unprepared prepared uncooked ready-to-eat ready heated unheated reheated
drained undrained rinsed unrinsed solids liquid without with added salt unsalted salted
sweetened unsweetened skin bone boneless skinless trimmed untrimmed lean fat
moist low moisture regular light heavy enriched unenriched fortified pasteurized
all grades choice select prime commercial retail cuts composite separable only to
and or of in from eaten percent not do made new year includes usda commodity
fat-free reduced whole part nonfat including year-old
""".split())

# Categorie USDA che sono prodotti COMPOSITI / preparati / di marca, non materia
# prima "profilabile" (un profilo dolce/salato/grasso misurabile al banco):
# da escludere quando si vuole la sola materia prima.
CATEGORIE_COMPOSITE = {
    "Baked Products", "Baby Foods", "Fast Foods", "Beverages", "Sweets",
    "Soups, Sauces, and Gravies", "Breakfast Cereals", "Snacks",
    "Sausages and Luncheon Meats", "Restaurant Foods",
    "Meals, Entrees, and Side Dishes", "American Indian/Alaska Native Foods",
}

_SOLO_MISURA = re.compile(r'^[\d\s%./"\'-]+$')  # "1/8\" fat", "80%", ecc.


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def is_segmento_stato(segmento):
    """True se il segmento è SOLO stato/cottura/preparazione/misura (non distingue
    un alimento). Es.: 'raw', 'cooked, boiled', 'trimmed to 1/8\" fat', 'without salt'."""
    s = _norm(segmento).replace("-", " ")
    if not s:
        return True
    if _SOLO_MISURA.match(segmento):
        return True
    toks = re.findall(r"[a-z]+", s)
    return bool(toks) and all(t in STATO for t in toks)


def base_key(descrizione):
    """Chiave-base: la descrizione USDA senza i segmenti di solo-stato.
    'Apples, raw, with skin' e 'Apples, cooked, boiled' -> stessa radice 'apples, with skin'/'apples'
    ma 'Beef, chuck, raw' resta diverso da 'Beef, rib, raw' (il taglio non è stato)."""
    parti = [p.strip() for p in str(descrizione).split(",") if p.strip()]
    tenuti = [p for p in parti if not is_segmento_stato(p)]
    if not tenuti:
        tenuti = parti[:1]
    return _norm(", ".join(tenuti))


def is_categoria_composita(categoria):
    """True per categorie di prodotti compositi/preparati/di marca (non materia prima)."""
    return categoria in CATEGORIE_COMPOSITE


def is_raw(descrizione):
    d = str(descrizione).lower()
    return ", raw" in d or d.endswith("raw")


def scegli_canonico(membri, key_fdc="fdc_id", key_descr="description"):
    """Dato un gruppo di righe-USDA con la stessa base_key, sceglie la voce canonica:
    la variante 'raw' se esiste (profilo della materia prima pulita), altrimenti
    la riga col fdc_id più basso (deterministico)."""
    raws = [m for m in membri if is_raw(m[key_descr])]
    pool = raws or list(membri)
    return sorted(pool, key=lambda m: int(m[key_fdc]))[0]


def dedup(righe, key_fdc="fdc_id", key_descr="description", key_cat=None,
          solo_materia_prima=False):
    """Deduplica una lista di dict-riga (da food.csv arricchito con la categoria).
    Ritorna un dict ordinato {base_key: [righe...]}.
    Se solo_materia_prima=True scarta le categorie composite (serve key_cat)."""
    from collections import OrderedDict
    g = OrderedDict()
    for r in righe:
        if solo_materia_prima and key_cat is not None and is_categoria_composita(r.get(key_cat)):
            continue
        g.setdefault(base_key(r[key_descr]), []).append(r)
    return g
