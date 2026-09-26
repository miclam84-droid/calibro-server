# ═══ KNOWLEDGE BUS (Board #58 #325): orchestra i database, gli endpoint parlano a lui ═══
# Ogni ingrediente ha 6 Knowledge Layer (#329). Il Bus li assembla in un oggetto unico.

import os, json, urllib.request as _ur, urllib.parse as _up

# LAYER 1 - BIOLOGICAL (USDA #325A): Blueprint Biologico. USDA FoodData Central, API gratuita/libera.
def layer_biological(nome_ingrediente, usda_key=""):
    """Nutrizione da USDA (#325A). API gratuita: https://fdc.nal.usda.gov/api-key-signup.html
    Ritorna il Blueprint Biologico o {} se non trovato/no key."""
    key = usda_key or os.environ.get("USDA_API_KEY", "")
    if not key:
        return {"_fonte": "USDA", "_stato": "no_api_key", "dati": {}}
    try:
        q = _up.quote(nome_ingrediente)
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={q}&pageSize=1&api_key={key}"
        req = _ur.Request(url, headers={"User-Agent": "Matter/1.0"})
        r = _ur.urlopen(req, timeout=15); d = json.loads(r.read().decode())
        foods = d.get("foods", [])
        if not foods:
            return {"_fonte": "USDA", "_stato": "non_trovato", "dati": {}}
        f = foods[0]
        # estraggo i nutrienti principali (Blueprint Biologico)
        nutrienti = {}
        for n in f.get("foodNutrients", []):
            nome = (n.get("nutrientName") or "").lower()
            val = n.get("value")
            if val is None: continue
            if "water" in nome: nutrienti["acqua_g"] = val
            elif "protein" in nome: nutrienti["proteine_g"] = val
            elif "total lipid" in nome or "fat" in nome: nutrienti["grassi_g"] = val
            elif "carbohydrate" in nome: nutrienti["carboidrati_g"] = val
            elif "sugars" in nome: nutrienti["zuccheri_g"] = val
            elif "fiber" in nome: nutrienti["fibre_g"] = val
            elif "energy" in nome and "kcal" in nome: nutrienti["kcal"] = val
            elif "sodium" in nome: nutrienti["sodio_mg"] = val
        return {"_fonte": "USDA FoodData Central", "_stato": "ok",
                "descrizione_usda": f.get("description",""), "dati": nutrienti}
    except Exception as e:
        return {"_fonte": "USDA", "_stato": f"errore: {str(e)[:60]}", "dati": {}}


def knowledge_bus(nome_ingrediente, dd_nodo=None, layers=None):
    """#325: il Bus assembla i Knowledge Layer per un ingrediente in un oggetto unico.
    dd_nodo = i dati gia' presenti nel grafo (proprieta, territorio, operativo...).
    layers = quali layer caricare (default: tutti quelli disponibili)."""
    dd = dd_nodo or {}
    layers = layers or ["biological", "economic", "cultural", "products", "graph"]
    out = {"ingrediente": nome_ingrediente, "knowledge_layers": {}}
    # LAYER GRAPH (#329): quello che c'e' gia' nel grafo (sempre disponibile)
    if "graph" in layers:
        out["knowledge_layers"]["graph"] = {
            "proprieta": dd.get("proprieta", {}),
            "fenomeni": dd.get("fenomeni", []),
            "abbinamenti": dd.get("dialoga_con", []),
        }
    # LAYER BIOLOGICAL (USDA)
    if "biological" in layers:
        out["knowledge_layers"]["biological"] = layer_biological(nome_ingrediente)
    # LAYER ECONOMIC (ISMEA, gia' nel sistema)
    if "economic" in layers:
        out["knowledge_layers"]["economic"] = {"_fonte": "ISMEA", "prezzo_kg": dd.get("prezzo_kg")}
    # LAYER CULTURAL (territorio - da Wikidata, per ora dal grafo)
    if "cultural" in layers:
        out["knowledge_layers"]["cultural"] = {
            "territorio": dd.get("territorio",""), "regione": dd.get("regione",""),
            "tutela": dd.get("tutela",""), "_fonte": "grafo (Wikidata in arrivo)"}
    # LAYER PRODUCTS (OpenFoodFacts - allergeni, in arrivo)
    if "products" in layers:
        out["knowledge_layers"]["products"] = {
            "allergeni": (dd.get("operativo",{}) or {}).get("allergeni",[]),
            "_fonte": "grafo (OpenFoodFacts in arrivo)"}
    return out
