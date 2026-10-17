# USDA SR Legacy — analisi di dedup per una base di ingredienti "profilabili"

**Corsia:** analisi / fattibilità (NON un merge nel grafo, NON tocca `app.py`).
**Dataset:** USDA FoodData Central — *SR Legacy* (release CSV `2018-04`).
**Scaricato e verificato il:** 2026-10-18 (file reale, niente numeri a memoria).
**Script delle regole (pure, testate):** `usda_sr_dedup.py` + `tests/test_dedup_usda_sr.py`.

---

## 0. Il dataset era raggiungibile?

**Sì.** Il proxy ha raggiunto `fdc.nal.usda.gov` e scaricato lo ZIP ufficiale
`FoodData_Central_sr_legacy_food_csv_2018-04.zip` (~6,07 MB). `food.csv` contiene
**7.793 righe** (coerente con `all_downloaded_table_record_counts.csv`: food = 7793).

La verifica live del singolo `fdc_id` via `api.nal.usda.gov` con `DEMO_KEY` è andata
in `OVER_RATE_LIMIT` (chiave pubblica condivisa, non è un problema del dataset). Gli
`fdc_id` del campione qui sotto sono comunque **presi direttamente dal `food.csv`
ufficiale** e verificati presenti nel file (grep 1 riga ciascuno). Con una
`USDA_API_KEY` propria la ri-verifica live è immediata.

---

## 1. La stima reale (ed è una doccia fredda onesta)

Il punto di partenza dell'idea era: "SR Legacy deduplicato → ~5-8k ingredienti
profilabili". **I numeri reali dicono che la dedup RIDUCE, non amplia.** Il totale
grezzo è già solo 7.793 righe, e deduplicare lo porta sotto. Quanto sotto dipende da
quanto si è aggressivi:

| Granularità di dedup | Tutte le righe | Solo categorie materia-prima¹ |
|---|---:|---:|
| **Famiglia** (1° segmento: `Beef` → 1) — *aggressiva* | **917** | 564 |
| **Base + taglio** (2 segmenti: `Beef, chuck`) | 2.960 | 1.475 |
| **Regola proposta²** (collassa solo stato/cottura, tiene tagli/tipi/specie) | **5.706** | **2.752** |
| Grezzo (nessuna dedup) | 7.793 | 4.748 |

¹ Escluse le 12 categorie composite/preparate/di marca (vedi §2).
² È la regola implementata in `usda_sr_dedup.py`, spiegata sotto.

**Lettura onesta:**

- La soglia **5-8k è raggiungibile solo con dedup LEGGERA** (collassando esclusivamente
  gli stati di cottura, tenendo distinti tutti i tagli) e **contando TUTTE le categorie**,
  comprese quelle composite: così si arriva a **5.706**. Ma dentro ci sono Fast Foods,
  Baby Foods, bevande di marca, condimenti già fatti — non sono "materia prima".
- Se si vuole la sola **materia prima davvero profilabile**, la stima reale scende a
  **~2.750** voci-base (regola proposta) e crolla a **~900** se si collassa per famiglia.
- SR Legacy da solo **non contiene 5-8k ingredienti-base distinti**. Più della metà
  delle 7.793 righe sono varianti di stato/cottura/taglio dello stesso alimento
  (954 righe di solo manzo → 2 famiglie; 464 di agnello/vitello → 4 famiglie).

**Conclusione per la decisione:** se l'obiettivo è ~5-8k ingredienti-base puliti,
SR Legacy **da solo non basta**. Serve o (a) accettare ~2,7k di materia prima pulita,
oppure (b) affiancare altre fonti (Foundation Foods, FNDDS, CIQUAL — già in casa come
`data/ciqual2025_norm.csv`, OpenFoodFacts per i di-marca) e deduplicare a monte
l'unione. SR Legacy è un ottimo **nucleo** di ~2,7k basi, non il totale.

---

## 2. Metodo di dedup proposto (regole)

Convenzione USDA: la descrizione è `Base, qualificatore1, qualificatore2, ...`.
I qualificatori finali sono spesso stato/cottura; i qualificatori intermedi sono
spesso tagli/tipi/specie **che vanno tenuti** (hanno profili grasso/sale diversi:
`Beef, tenderloin` ≠ `Beef, brisket`).

**Regole (vedi `usda_sr_dedup.py`):**

1. **Scarta le categorie composite/preparate/di marca** quando serve la materia prima:
   Baked Products, Baby Foods, Fast Foods, Beverages, Sweets, Soups/Sauces/Gravies,
   Breakfast Cereals, Snacks, Sausages and Luncheon Meats, Restaurant Foods,
   Meals/Entrees/Side Dishes, American Indian/Alaska Native Foods.
   *(Allineato allo spirito di `_usda_composito` / `_non_sensoriale` già in
   `routes/deriva_gusti_search.py`.)*
2. **Chiave-base** = descrizione **senza i segmenti di solo-stato**. Un segmento è
   "solo-stato" se è composto esclusivamente da parole del vocabolario `STATO`
   (raw, cooked, boiled, roasted, canned, frozen, dried, without/added salt,
   drained, `trimmed to 1/8" fat`, `80%`, lean/fat, pasteurized, all grades, ...).
   I tagli/tipi/specie **non** sono in quel vocabolario, quindi restano nella chiave.
3. **Collasso:** tutte le righe con la stessa chiave-base = una voce-base.
4. **Voce canonica del gruppo:** la variante `raw` se esiste (profilo della materia
   prima pulita), altrimenti il `fdc_id` più basso (deterministico).

Esempi di collasso corretto (verificati sul dataset):
- `Apples, raw, with skin` + `Apples, cooked, boiled, with skin` → **1 voce**.
- 25 righe di `Beef, retail cuts, separable fat, *` → **1 voce** (`fdc 168605`).
- `Rice, white, long-grain, raw, enriched` tiene distinto `Rice, brown, long-grain` (giusto).

Limiti noti (onestà): la regola è lessicale, non semantica. Non unisce sinonimi
("Garbanzo" vs "Chickpeas") né errori di battitura, e tiene separate alcune varianti
che un umano fonderebbe. È una **prima passata deterministica e ispezionabile**, non
un dedup perfetto; il passo successivo (se si procede) è una revisione a occhio dei
gruppi grandi + eventuale lookup sinonimi.

---

## 3. Campione di 50 voci-base (stratificato per categoria materia-prima)

`fdc_id` = voce canonica del gruppo; `n_varianti` = righe SR Legacy collassate in quella
voce-base. Tutti gli `fdc_id` sono presenti in `food.csv` ufficiale.

| # | fdc_id | descrizione canonica USDA | n_varianti | categoria |
|---|--------|----------------------------|-----------|-----------|
| 1 | 170032 | Potatoes, raw, skin | 10 | Vegetables and Vegetable Products |
| 2 | 169303 | Sweet potato leaves, raw | 3 | Vegetables and Vegetable Products |
| 3 | 168446 | Potato flour | 1 | Vegetables and Vegetable Products |
| 4 | 169286 | Spinach, canned, regular pack, drained solids | 1 | Vegetables and Vegetable Products |
| 5 | 170048 | Potato puffs, frozen, oven-heated | 1 | Vegetables and Vegetable Products |
| 6 | 171711 | Blueberries, raw | 3 | Fruits and Fruit Juices |
| 7 | 167793 | Apples, raw, fuji, with skin | 1 | Fruits and Fruit Juices |
| 8 | 168203 | Apples, raw, granny smith, with skin | 1 | Fruits and Fruit Juices |
| 9 | 169918 | Oranges, raw, Florida | 1 | Fruits and Fruit Juices |
| 10 | 173027 | Fruit cocktail, canned, light syrup, solids and liquids | 1 | Fruits and Fruit Juices |
| 11 | 170893 | Egg, whole, raw, frozen, salted, pasteurized | 5 | Dairy and Egg Products |
| 12 | 170859 | Cream, fluid, heavy whipping | 1 | Dairy and Egg Products |
| 13 | 170916 | Yogurt, Greek, nonfat, Fruit on Bottom, Blackberry, CHOBANI | 1 | Dairy and Egg Products |
| 14 | 171301 | Kefir, lowfat, strawberry, LIFEWAY | 1 | Dairy and Egg Products |
| 15 | 172224 | Cheese, white, queso blanco | 1 | Dairy and Egg Products |
| 16 | 171955 | Fish, cod, Atlantic, raw | 3 | Finfish and Shellfish Products |
| 17 | 171983 | Mollusks, whelk, unspecified, raw | 1 | Finfish and Shellfish Products |
| 18 | 173694 | Fish, sea bass, mixed species, cooked, dry heat | 1 | Finfish and Shellfish Products |
| 19 | 174203 | Crustaceans, crab, alaska king, imitation, made from surimi | 1 | Finfish and Shellfish Products |
| 20 | 175125 | Fish, ocean perch, Atlantic, raw | 1 | Finfish and Shellfish Products |
| 21 | 171052 | Chicken, broilers or fryers, meat only, raw | 4 | Poultry Products |
| 22 | 171136 | Turkey, drumstick, from whole bird, meat only, raw | 2 | Poultry Products |
| 23 | 173641 | Chicken, stewing, giblets, raw | 2 | Poultry Products |
| 24 | 171118 | Chicken, broiler, rotisserie, BBQ, thigh, meat only | 1 | Poultry Products |
| 25 | 172416 | Guinea hen, meat and skin, raw | 1 | Poultry Products |
| 26 | 168605 | Beef, retail cuts, separable fat, raw | 25 | Beef Products |
| 27 | 168672 | Beef, chuck, blade roast, separable lean and fat, trimmed to 1/8" fat, select, raw | 8 | Beef Products |
| 28 | 174696 | Beef, ribeye petite roast/filet, boneless, separable lean only, trimmed to 0" fat, all grades, raw | 3 | Beef Products |
| 29 | 173971 | Beef, Australian, imported, grass-fed, round, bottom round steak/roast, boneless, separable lean only, raw | 2 | Beef Products |
| 30 | 171798 | Beef, ground, 80% lean meat / 20% fat, patty, cooked, pan-broiled | 1 | Beef Products |
| 31 | 175189 | Beans, cranberry (roman), mature seeds, raw | 4 | Legumes and Legume Products |
| 32 | 173806 | Peanuts, all types, dry-roasted, without salt | 2 | Legumes and Legume Products |
| 33 | 172451 | Tofu, fried | 1 | Legumes and Legume Products |
| 34 | 173777 | SILK Mocha, soymilk | 1 | Legumes and Legume Products |
| 35 | 174297 | Vitasoy USA, Organic Nasoya Super Firm Cubed Tofu | 1 | Legumes and Legume Products |
| 36 | 171019 | Salad dressing, italian dressing, commercial, regular | 4 | Fats and Oils |
| 37 | 171002 | Salad dressing, KRAFT Mayo Light Mayonnaise | 1 | Fats and Oils |
| 38 | 171402 | Salad dressing, thousand island, commercial, regular | 1 | Fats and Oils |
| 39 | 172328 | Oil, sunflower, linoleic, (partially hydrogenated) | 1 | Fats and Oils |
| 40 | 173565 | Oil, soybean, salad or cooking, (partially hydrogenated) and cottonseed | 1 | Fats and Oils |
| 41 | 172496 | Lamb, shoulder, whole (arm and blade), separable lean and fat, trimmed to 1/4" fat, choice, raw | 12 | Lamb, Veal, and Game Products |
| 42 | 172633 | Lamb, New Zealand, imported, hind-shank, separable lean and fat, raw | 4 | Lamb, Veal, and Game Products |
| 43 | 172622 | Lamb, New Zealand, imported, tenderloin, separable lean only, cooked, fast fried | 2 | Lamb, Veal, and Game Products |
| 44 | 174356 | Veal, variety meats and by-products, kidneys, raw | 2 | Lamb, Veal, and Game Products |
| 45 | 172608 | Lamb, Australian, ground, 85% lean / 15% fat, raw | 1 | Lamb, Veal, and Game Products |
| 46 | 168877 | Rice, white, long-grain, regular, raw, enriched | 6 | Cereal Grains and Pasta |
| 47 | 168147 | Vital wheat gluten | 1 | Cereal Grains and Pasta |
| 48 | 168907 | Noodles, japanese, soba, cooked | 1 | Cereal Grains and Pasta |
| 49 | 169703 | Rice, brown, long-grain, raw | 1 | Cereal Grains and Pasta |
| 50 | 169740 | Barley malt flour | 1 | Cereal Grains and Pasta |

> Nota sul campione: anche dentro le categorie "materia prima" restano residui di
> marca/preparato (es. #13 CHOBANI, #34 SILK, #48 soba cotta). È la prova che la
> dedup lessicale è una prima passata: pulisce i doppioni di cottura, non promuove da
> sola a "ingrediente-base pulito". La categoria aiuta ma non basta a filtrare i di-marca.

---

## 4. Cosa servirebbe per il passo successivo (se si procede)

- Una `USDA_API_KEY` propria (non `DEMO_KEY`) per ri-verificare live gli `fdc_id` e
  tirare giù i nutrienti delle voci canoniche.
- Decidere la granularità (famiglia ~900 / base+taglio ~1.475 / regola proposta ~2.752).
- Se l'obiettivo resta 5-8k: unione con Foundation Foods + CIQUAL (già in repo) +
  eventuale OpenFoodFacts per i di-marca, con dedup sull'unione.
- Un giro di revisione a occhio sui gruppi grandi (il manzo e l'agnello dominano) e
  un piccolo dizionario di sinonimi EN per unire ciò che la regola lessicale lascia separato.
