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
    # traduzione IT->EN dei termini comuni (USDA e' in inglese)
    _IT_EN = {"pomodoro":"tomato","basilico":"basil","mozzarella":"mozzarella","guanciale":"pork jowl",
              "pecorino":"pecorino cheese","parmigiano":"parmesan","farina":"wheat flour","uovo":"egg",
              "burro":"butter","olio":"olive oil","limone":"lemon","aglio":"garlic","cipolla":"onion",
              "carota":"carrot","patata":"potato","riso":"rice","latte":"milk","zucchero":"sugar",
              "sale":"salt","manzo":"beef","pollo":"chicken","maiale":"pork","tonno":"tuna",
              "melanzana":"eggplant","zucchina":"zucchini","peperone":"pepper","spinaci":"spinach",
              "mela":"apple","arancia":"orange","fragola":"strawberry","miele":"honey","caffe":"coffee"}
    q_en = _IT_EN.get(nome_ingrediente.lower().split()[0], nome_ingrediente)
    try:
        q = _up.quote(q_en)
        # dataType Foundation/SR Legacy = ingredienti base (NON Branded = prodotti industriali)
        url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={q}&pageSize=3&dataType=Foundation,SR%20Legacy&api_key={key}"
        req = _ur.Request(url, headers={"User-Agent": "Matter/1.0"})
        r = _ur.urlopen(req, timeout=15); d = json.loads(r.read().decode())
        foods = d.get("foods", [])
        if not foods:
            # fallback senza filtro dataType
            url2 = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={q}&pageSize=1&api_key={key}"
            r2 = _ur.urlopen(_ur.Request(url2, headers={"User-Agent":"Matter/1.0"}), timeout=15)
            foods = json.loads(r2.read().decode()).get("foods", [])
            if not foods: return {"_fonte": "USDA", "_stato": "non_trovato", "dati": {}}
        # preferisco il match piu corto/pulito (ingrediente base, non "raw" con additivi)
        f = sorted(foods, key=lambda x: len(x.get("description","")))[0]
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



# LAYER 3 - CULTURAL (Wikidata #326A): territorio, origine, tradizione. SPARQL gratuito, CC0.
def layer_cultural_wikidata(nome_ingrediente):
    """Territorio/origine da Wikidata. Gratis, nessuna licenza (CC0)."""
    try:
        # cerco l'entita Wikidata dell'ingrediente
        q = _up.quote(nome_ingrediente)
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={q}&language=it&format=json&limit=1"
        r = _ur.urlopen(_ur.Request(url, headers={"User-Agent":"Matter/1.0"}), timeout=12)
        d = json.loads(r.read().decode())
        hits = d.get("search", [])
        if not hits:
            return {"_fonte": "Wikidata", "_stato": "non_trovato", "dati": {}}
        h = hits[0]
        return {"_fonte": "Wikidata", "_stato": "ok",
                "dati": {"nome": h.get("label",""), "descrizione": h.get("description",""), "wikidata_id": h.get("id","")}}
    except Exception as e:
        return {"_fonte": "Wikidata", "_stato": f"errore: {str(e)[:50]}", "dati": {}}


# LAYER 4 - PRODUCTS (OpenFoodFacts #327): allergeni, additivi dei prodotti. Gratis, ODbL.
def layer_products_off(nome_ingrediente):
    """Allergeni/additivi da OpenFoodFacts. Gratis (ODbL). Cerca il prodotto piu' rilevante."""
    try:
        q = _up.quote(nome_ingrediente)
        url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={q}&search_simple=1&json=1&page_size=1&fields=product_name,allergens_tags,additives_tags"
        r = _ur.urlopen(_ur.Request(url, headers={"User-Agent":"Matter/1.0"}), timeout=12)
        d = json.loads(r.read().decode())
        prods = d.get("products", [])
        if not prods:
            return {"_fonte": "OpenFoodFacts", "_stato": "non_trovato", "dati": {}}
        pr = prods[0]
        allerg = [a.replace("en:","") for a in pr.get("allergens_tags",[])]
        addit = [a.replace("en:","") for a in pr.get("additives_tags",[])][:8]
        return {"_fonte": "OpenFoodFacts", "_stato": "ok",
                "dati": {"allergeni": allerg, "additivi": addit}}
    except Exception as e:
        return {"_fonte": "OpenFoodFacts", "_stato": f"errore: {str(e)[:50]}", "dati": {}}


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
    # LAYER CULTURAL (territorio dal grafo + Wikidata se richiesto)
    if "cultural" in layers:
        cult = {"territorio": dd.get("territorio",""), "regione": dd.get("regione",""),
                "tutela": dd.get("tutela","")}
        if "cultural_live" in layers:  # chiamata Wikidata solo se richiesta esplicita (e' lenta)
            cult["wikidata"] = layer_cultural_wikidata(nome_ingrediente).get("dati", {})
        out["knowledge_layers"]["cultural"] = cult
    # LAYER PRODUCTS (allergeni dal grafo + OpenFoodFacts se richiesto)
    if "products" in layers:
        prod = {"allergeni": (dd.get("operativo",{}) or {}).get("allergeni",[])}
        if "products_live" in layers:  # chiamata OFF solo se richiesta (e' lenta)
            prod["openfoodfacts"] = layer_products_off(nome_ingrediente).get("dati", {})
        out["knowledge_layers"]["products"] = prod
    return out
