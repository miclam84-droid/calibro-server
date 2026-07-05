-- ============================================================
-- PARAMETRI FISICI INGREDIENTI — dataset curato Matter
-- Fonti: FDA, USDA, letteratura peer-reviewed (pubblico dominio)
-- Aggiornato: 05/07/2026
-- Struttura: nodi Prodotto con pH_min, pH_max, Aw, fenomeno fisico
-- ============================================================

-- ── LATTICINI ──────────────────────────────────────────────
UPDATE nodes SET data = data::jsonb || '{
  "ph_min":4.6,"ph_max":4.6,"ph_note":"soglia sicurezza C.botulinum",
  "aw_min":0.95,"aw_max":0.99,
  "fenomeno":"acidita",
  "variabilita":"pH scende con maturazione e tipo di caglio",
  "fonte":"FDA Bad Bug Book 2012"
}'::jsonb WHERE name='cheese' AND type='Prodotto';

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_latte', 'Prodotto', 'latte', 'cucina', '{
  "ph_min":6.4,"ph_max":6.8,
  "ph_note":"fresco; scende a 6.0-6.2 se inizia acidificazione batterica",
  "aw_min":0.993,"aw_max":0.998,
  "fenomeno":"coagulazione",
  "variabilita":"pH cala di 0.1-0.2 in 24h a temperatura ambiente",
  "fonte":"USDA FoodData Central; FDA"
}'),
('prod_panna', 'Prodotto', 'panna', 'cucina', '{
  "ph_min":6.5,"ph_max":6.8,
  "aw_min":0.982,"aw_max":0.996,
  "fenomeno":"struttura",
  "variabilita":"Aw scende con contenuto di grasso",
  "fonte":"USDA FoodData Central"
}'),
('prod_burro', 'Prodotto', 'burro', 'bakery', '{
  "ph_min":6.1,"ph_max":6.4,
  "aw_min":0.900,"aw_max":0.925,
  "fenomeno":"struttura",
  "cristallizzazione_t":"28-32°C (forme cristalline β)",
  "variabilita":"Aw bassa per contenuto grasso >80%",
  "fonte":"USDA FoodData Central; Walstra 2006"
}')
ON CONFLICT DO NOTHING;

-- ── FRUTTA ─────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_limone', 'Prodotto', 'limone', 'bar', '{
  "ph_min":2.0,"ph_max":2.6,
  "ph_note":"succo; acido citrico 5-8% peso fresco",
  "acidita_titolabile_pct":"5-8",
  "aw_min":0.982,"aw_max":0.990,
  "fenomeno":"acidita",
  "variabilita":"pH varia 0.3-0.4 tra varietà e stagione",
  "fonte":"FDA Acidified Foods; Codex Alimentarius"
}'),
('prod_lime', 'Prodotto', 'lime', 'bar', '{
  "ph_min":2.0,"ph_max":2.4,
  "ph_note":"succo; più acido del limone, acido citrico 6-9%",
  "acidita_titolabile_pct":"6-9",
  "aw_min":0.980,"aw_max":0.988,
  "fenomeno":"acidita",
  "variabilita":"pH differisce 0.2-0.3 da limone",
  "fonte":"FDA; USDA FoodData Central"
}'),
('prod_arancia', 'Prodotto', 'arancia', 'bar', '{
  "ph_min":3.0,"ph_max":4.0,
  "ph_note":"succo; acido citrico 0.6-1.2%",
  "acidita_titolabile_pct":"0.6-1.2",
  "aw_min":0.980,"aw_max":0.990,
  "fenomeno":"acidita",
  "variabilita":"pH più alto del lime — meno acido, più zuccheri",
  "fonte":"USDA FoodData Central"
}'),
('prod_pomodoro', 'Prodotto', 'pomodoro', 'cucina', '{
  "ph_min":3.5,"ph_max":4.7,
  "ph_note":"frutto intero; varia con varietà, maturazione, condizioni coltura",
  "ph_sicurezza":"<4.6 per conserve acidificate (FDA)",
  "aw_min":0.970,"aw_max":0.993,
  "fenomeno":"acidita",
  "variabilita":"pH varia 1.2 unità tra varietà — il motivo per cui alcuni pomodori sembrano acidi e altri no",
  "fonte":"FDA Acidified Foods Guide; USDA"
}'),
('prod_mela', 'Prodotto', 'mela', 'bakery', '{
  "ph_min":3.3,"ph_max":4.0,
  "ph_note":"acido malico principalmente (0.3-0.7%)",
  "aw_min":0.981,"aw_max":0.992,
  "fenomeno":"acidita",
  "variabilita":"pH più alto nelle mele dolci (Golden), più basso nelle acide (Granny Smith)",
  "fonte":"USDA FoodData Central"
}'),
('prod_fragola', 'Prodotto', 'fragola', 'pasticceria', '{
  "ph_min":3.0,"ph_max":3.9,
  "ph_note":"acido citrico 0.6-0.8%; acido malico 0.2-0.3%",
  "aw_min":0.978,"aw_max":0.990,
  "fenomeno":"acidita",
  "fonte":"USDA FoodData Central"
}'),
('prod_lampone', 'Prodotto', 'lampone', 'pasticceria', '{
  "ph_min":3.0,"ph_max":3.7,
  "aw_min":0.977,"aw_max":0.988,
  "fenomeno":"acidita",
  "fonte":"USDA FoodData Central"
}'),
('prod_mirtillo', 'Prodotto', 'mirtillo', 'pasticceria', '{
  "ph_min":3.1,"ph_max":3.5,
  "aw_min":0.978,"aw_max":0.987,
  "fenomeno":"acidita",
  "fonte":"USDA FoodData Central"
}')
ON CONFLICT DO NOTHING;

-- ── BEVANDE ALCOLICHE ──────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_vino_bianco', 'Prodotto', 'vino bianco', 'bar', '{
  "ph_min":3.0,"ph_max":3.4,
  "ph_note":"acido tartarico, malico, lattico; pH sale se fa malolattica",
  "acidita_totale_g_l":"4-8 (acido tartarico equivalente)",
  "abv_pct":"11-14",
  "aw_min":0.978,"aw_max":0.985,
  "fenomeno":"acidita",
  "variabilita":"pH sale di 0.3-0.5 dopo fermentazione malolattica",
  "fonte":"OIV; Wine Chemistry Boulton 2001"
}'),
('prod_vino_rosso', 'Prodotto', 'vino rosso', 'bar', '{
  "ph_min":3.3,"ph_max":3.8,
  "ph_note":"pH più alto del bianco per tannini e malolattica quasi sempre svolta",
  "abv_pct":"12-15",
  "aw_min":0.978,"aw_max":0.985,
  "fenomeno":"acidita",
  "fonte":"OIV; Wine Chemistry Boulton 2001"
}'),
('prod_birra', 'Prodotto', 'birra', 'bar', '{
  "ph_min":3.8,"ph_max":4.5,
  "ph_note":"acidi prodotti da fermentazione; lager più alta del lambic",
  "abv_pct":"3-12",
  "aw_min":0.988,"aw_max":0.995,
  "fenomeno":"fermentazione",
  "variabilita":"pH lambic 3.2-3.5; lager 4.0-4.5",
  "fonte":"Briggs Malting and Brewing Science 2004"
}'),
('prod_rum', 'Prodotto', 'rum', 'bar', '{
  "ph_min":4.5,"ph_max":6.0,
  "ph_note":"pH varia con invecchiamento — rovere cede composti acidi",
  "abv_pct":"37.5-50",
  "aw_min":0.920,"aw_max":0.960,
  "fenomeno":"concentrazione",
  "variabilita":"pH scende con invecchiamento in botte",
  "fonte":"Lea & Piggott Fermented Beverage Production 2003"
}'),
('prod_whiskey', 'Prodotto', 'whiskey', 'bar', '{
  "ph_min":3.7,"ph_max":5.0,
  "abv_pct":"40-63",
  "aw_min":0.915,"aw_max":0.955,
  "fenomeno":"concentrazione",
  "variabilita":"pH scende con invecchiamento; Bourbon più acido di Scotch",
  "fonte":"Russell Whisky: Technology, Production and Marketing 2003"
}'),
('prod_cognac', 'Prodotto', 'cognac', 'bar', '{
  "ph_min":3.5,"ph_max":4.5,
  "abv_pct":"40-45",
  "aw_min":0.918,"aw_max":0.952,
  "fenomeno":"concentrazione",
  "fonte":"BNIC; Lea & Piggott 2003"
}')
ON CONFLICT DO NOTHING;

-- ── CARNE E PESCE ──────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_manzo', 'Prodotto', 'manzo', 'cucina', '{
  "ph_min":5.3,"ph_max":5.7,
  "ph_note":"post-rigor mortis; DFD se pH >6.0; PSE se pH <5.3",
  "aw_min":0.970,"aw_max":0.985,
  "fenomeno":"calore",
  "coagulazione_t":"50-70°C (miosina 50°C, actina 65-70°C)",
  "variabilita":"pH determina tenerezza, colore, water-holding capacity",
  "fonte":"Lawrie Meat Science 2006; USDA"
}'),
('prod_pollo', 'Prodotto', 'pollo', 'cucina', '{
  "ph_min":5.7,"ph_max":6.2,
  "aw_min":0.980,"aw_max":0.990,
  "fenomeno":"calore",
  "t_sicurezza":"74°C interno (FDA/USDA)",
  "fonte":"USDA FSIS"
}'),
('prod_salmone', 'Prodotto', 'salmone', 'cucina', '{
  "ph_min":6.0,"ph_max":6.5,
  "aw_min":0.978,"aw_max":0.988,
  "fenomeno":"calore",
  "coagulazione_t":"43-50°C (miosina pesce)",
  "t_sicurezza":"63°C interno (FDA)",
  "fonte":"FDA Fish and Fishery Products Hazards 2022"
}'),
('prod_tonno', 'Prodotto', 'tonno', 'cucina', '{
  "ph_min":5.2,"ph_max":6.2,
  "aw_min":0.975,"aw_max":0.986,
  "fenomeno":"calore",
  "fonte":"FDA Fish and Fishery Products Hazards 2022"
}')
ON CONFLICT DO NOTHING;

-- ── CEREALI E FARINE ───────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_farina_frumento', 'Prodotto', 'farina di frumento', 'bakery', '{
  "ph_min":5.9,"ph_max":6.4,
  "ph_note":"farina bianca; integrale più bassa 5.5-6.0",
  "aw_min":0.60,"aw_max":0.70,
  "fenomeno":"struttura",
  "proteine_pct":"9-14 (W dipende da varietà)",
  "variabilita":"pH impasto scende durante fermentazione",
  "fonte":"AACC International; Cauvain Baking Problems Solved 2012"
}'),
('prod_farina_segale', 'Prodotto', 'farina di segale', 'bakery', '{
  "ph_min":5.5,"ph_max":6.0,
  "aw_min":0.60,"aw_max":0.70,
  "fenomeno":"struttura",
  "variabilita":"pentosani alti — assorbe più acqua del frumento",
  "fonte":"Cauvain; AACC"
}'),
('prod_lievito_madre', 'Prodotto', 'lievito madre', 'bakery', '{
  "ph_min":3.5,"ph_max":5.5,
  "ph_note":"fresca rinfrescata 5.0-5.5; matura 4.0-4.5; sovramatura <3.8",
  "aw_min":0.950,"aw_max":0.975,
  "fenomeno":"fermentazione",
  "variabilita":"pH è il numero bersaglio principale — misuralo con pHmetro",
  "fonte":"Hamelman Bread 2012; De Vuyst & Neysens 2005"
}')
ON CONFLICT DO NOTHING;

-- ── UOVA ───────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_uovo_albume', 'Prodotto', 'albume', 'cucina', '{
  "ph_min":7.6,"ph_max":8.0,
  "ph_note":"fresco; sale fino a 9.0-9.7 in 24-48h per perdita CO2",
  "aw_min":0.990,"aw_max":0.997,
  "fenomeno":"coagulazione",
  "coagulazione_t":"60-65°C",
  "variabilita":"pH determina stabilità schiuma — fresco (pH basso) monta meglio",
  "fonte":"USDA; McGee On Food and Cooking 2004"
}'),
('prod_uovo_tuorlo', 'Prodotto', 'tuorlo', 'cucina', '{
  "ph_min":6.0,"ph_max":6.3,
  "aw_min":0.960,"aw_max":0.975,
  "fenomeno":"coagulazione",
  "coagulazione_t":"65-70°C",
  "fonte":"USDA; McGee 2004"
}')
ON CONFLICT DO NOTHING;

-- ── ZUCCHERI E DOLCIFICANTI ────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_zucchero', 'Prodotto', 'zucchero', 'pasticceria', '{
  "ph_min":6.0,"ph_max":7.0,
  "ph_note":"saccarosio puro è neutro",
  "aw_note":"dipende interamente dalla concentrazione in soluzione",
  "brix_sciroppo_1_1":"50",
  "brix_sciroppo_2_1":"65",
  "fenomeno":"concentrazione",
  "cristallizzazione_t":"135-145°C (caramello)",
  "fonte":"USDA; McGee 2004"
}'),
('prod_miele', 'Prodotto', 'miele', 'pasticceria', '{
  "ph_min":3.4,"ph_max":6.1,
  "ph_note":"acido gluconico prodotto da glucosio ossidasi",
  "aw_min":0.50,"aw_max":0.60,
  "fenomeno":"concentrazione",
  "variabilita":"Aw bassa impedisce fermentazione — sopra 0.60 fermenta",
  "fonte":"White Honey: A Comprehensive Survey 1975; Codex"
}')
ON CONFLICT DO NOTHING;

-- ── FUNGHI ─────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_porcini', 'Prodotto', 'porcino', 'cucina', '{
  "ph_min":5.0,"ph_max":6.0,
  "aw_min":0.975,"aw_max":0.988,
  "fenomeno":"maillard",
  "variabilita":"essiccazione porta Aw <0.70 — shelf stable",
  "fonte":"USDA FoodData Central"
}'),
('prod_shiitake', 'Prodotto', 'shiitake', 'cucina', '{
  "ph_min":4.5,"ph_max":5.5,
  "aw_min":0.970,"aw_max":0.985,
  "fenomeno":"maillard",
  "fonte":"USDA FoodData Central"
}')
ON CONFLICT DO NOTHING;

-- ── CAFFÈ ──────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_caffe_espresso', 'Prodotto', 'caffè espresso', 'caffetteria', '{
  "ph_min":4.5,"ph_max":5.5,
  "ph_note":"acidi clorogenici (principale), acetico, citrico, malico",
  "tds_pct":"7-12",
  "fenomeno":"estrazione",
  "variabilita":"pH scende con sovraestrazione; acidi volatili evaporano se servito caldo",
  "fonte":"SCAA; Illy & Viani Espresso Coffee 2005"
}'),
('prod_caffe_filtro', 'Prodotto', 'caffè filtro', 'caffetteria', '{
  "ph_min":4.9,"ph_max":5.2,
  "tds_pct":"1.15-1.55",
  "fenomeno":"estrazione",
  "variabilita":"pH più alto dell espresso per minor concentrazione",
  "fonte":"SCAA Brewing Control Chart"
}')
ON CONFLICT DO NOTHING;

-- ── CIOCCOLATO ─────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_cioccolato_fondente', 'Prodotto', 'cioccolato fondente', 'pasticceria', '{
  "ph_min":5.5,"ph_max":6.0,
  "ph_note":"naturale non alcalinizzato; olandese (dutch process) pH 6.8-8.1",
  "aw_min":0.40,"aw_max":0.50,
  "fenomeno":"cristallizzazione",
  "tempera_t":"27-31°C (Forma V stabile)",
  "variabilita":"pH cambia con alcalinizzazione — altera colore e sapore",
  "fonte":"Beckett Industrial Chocolate Manufacture 2009"
}')
ON CONFLICT DO NOTHING;

-- ── ACETO E FERMENTATI ─────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_aceto', 'Prodotto', 'aceto', 'cucina', '{
  "ph_min":2.4,"ph_max":3.4,
  "ph_note":"acido acetico 4-8% (vino), 5% (mela)",
  "acidita_totale_pct":"4-8",
  "aw_min":0.972,"aw_max":0.985,
  "fenomeno":"acidita",
  "variabilita":"pH varia con tipo: aceto balsamico 2.7-3.1, mela 3.0-3.5",
  "fonte":"FDA CFR Title 21; Codex Alimentarius"
}'),
('prod_yogurt', 'Prodotto', 'yogurt', 'cucina', '{
  "ph_min":3.8,"ph_max":4.6,
  "ph_note":"acido lattico prodotto da L.bulgaricus e S.thermophilus",
  "aw_min":0.978,"aw_max":0.994,
  "fenomeno":"fermentazione",
  "variabilita":"pH determina la texture: <4.0 gel sieroso, 4.0-4.6 cremoso",
  "fonte":"Tamime & Robinson Yoghurt 1999"
}')
ON CONFLICT DO NOTHING;

-- ── LEGUMI ─────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_fagiolo', 'Prodotto', 'fagiolo', 'cucina', '{
  "ph_min":5.6,"ph_max":6.5,
  "ph_note":"cotto; crudo pH 6.0-6.5",
  "aw_min":0.975,"aw_max":0.990,
  "fenomeno":"osmosi",
  "variabilita":"pH scende in salamoia (fermentazione lattica)",
  "fonte":"USDA FoodData Central"
}'),
('prod_soia', 'Prodotto', 'soia', 'cucina', '{
  "ph_min":6.0,"ph_max":7.0,
  "aw_min":0.930,"aw_max":0.960,
  "fenomeno":"struttura",
  "variabilita":"pH latte di soia 6.8-7.0; tofu 4.5-5.5 (acidificato)",
  "fonte":"USDA FoodData Central"
}')
ON CONFLICT DO NOTHING;

-- ── AROMI BASE ─────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod_vaniglia', 'Prodotto', 'vaniglia', 'pasticceria', '{
  "ph_min":5.5,"ph_max":7.0,
  "ph_note":"estratto in alcol",
  "aw_min":0.60,"aw_max":0.75,
  "fenomeno":"concentrazione",
  "fonte":"FDA; McCormick flavor chemistry"
}'),
('prod_cannella', 'Prodotto', 'cannella', 'pasticceria', '{
  "ph_min":3.9,"ph_max":4.1,
  "ph_note":"in soluzione acquosa",
  "aw_min":0.50,"aw_max":0.65,
  "fenomeno":"concentrazione",
  "fonte":"USDA FoodData Central"
}')
ON CONFLICT DO NOTHING;

-- ── ARCHI: collegamento ai fenomeni fisici del grafo ───────
-- Ogni ingrediente viene collegato al suo fenomeno fisico primario
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('prod_latte',            'fen-coagulazione',    'governato_da', '{}'),
('prod_panna',            'fen-struttura',        'governato_da', '{}'),
('prod_burro',            'fen-cristallizzazione','governato_da', '{}'),
('prod_limone',           'fen-acidita',          'governato_da', '{}'),
('prod_lime',             'fen-acidita',          'governato_da', '{}'),
('prod_arancia',          'fen-acidita',          'governato_da', '{}'),
('prod_pomodoro',         'fen-acidita',          'governato_da', '{}'),
('prod_mela',             'fen-acidita',          'governato_da', '{}'),
('prod_fragola',          'fen-acidita',          'governato_da', '{}'),
('prod_lampone',          'fen-acidita',          'governato_da', '{}'),
('prod_mirtillo',         'fen-acidita',          'governato_da', '{}'),
('prod_vino_bianco',      'fen-acidita',          'governato_da', '{}'),
('prod_vino_rosso',       'fen-acidita',          'governato_da', '{}'),
('prod_birra',            'fen-fermentazione',    'governato_da', '{}'),
('prod_rum',              'fen-concentrazione',   'governato_da', '{}'),
('prod_whiskey',          'fen-concentrazione',   'governato_da', '{}'),
('prod_cognac',           'fen-concentrazione',   'governato_da', '{}'),
('prod_manzo',            'fen-calore',           'governato_da', '{}'),
('prod_pollo',            'fen-calore',           'governato_da', '{}'),
('prod_salmone',          'fen-calore',           'governato_da', '{}'),
('prod_tonno',            'fen-calore',           'governato_da', '{}'),
('prod_farina_frumento',  'fen-struttura',        'governato_da', '{}'),
('prod_farina_segale',    'fen-struttura',        'governato_da', '{}'),
('prod_lievito_madre',    'fen-fermentazione',    'governato_da', '{}'),
('prod_uovo_albume',      'fen-coagulazione',     'governato_da', '{}'),
('prod_uovo_tuorlo',      'fen-coagulazione',     'governato_da', '{}'),
('prod_zucchero',         'fen-concentrazione',   'governato_da', '{}'),
('prod_miele',            'fen-concentrazione',   'governato_da', '{}'),
('prod_porcini',          'fen-maillard',         'governato_da', '{}'),
('prod_shiitake',         'fen-maillard',         'governato_da', '{}'),
('prod_caffe_espresso',   'fen-estrazione',       'governato_da', '{}'),
('prod_caffe_filtro',     'fen-estrazione',       'governato_da', '{}'),
('prod_cioccolato_fondente','fen-cristallizzazione','governato_da','{}'),
('prod_aceto',            'fen-acidita',          'governato_da', '{}'),
('prod_yogurt',           'fen-fermentazione',    'governato_da', '{}'),
('prod_fagiolo',          'fen-osmosi',           'governato_da', '{}'),
('prod_soia',             'fen-struttura',        'governato_da', '{}'),
('prod_vaniglia',         'fen-concentrazione',   'governato_da', '{}'),
('prod_cannella',         'fen-concentrazione',   'governato_da', '{}')
ON CONFLICT DO NOTHING;

-- ── ARCHI: collegamento ingredienti Matter → nodi Ahn ──────
-- Collega i nodi prod_ con i corrispondenti nodi ahn_ per unificare il grafo
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('prod_limone',           'ahn_lemon',            'stesso_ingrediente', '{}'),
('prod_arancia',          'ahn_orange',           'stesso_ingrediente', '{}'),
('prod_mela',             'ahn_apple',            'stesso_ingrediente', '{}'),
('prod_fragola',          'ahn_strawberry',       'stesso_ingrediente', '{}'),
('prod_lampone',          'ahn_raspberry',        'stesso_ingrediente', '{}'),
('prod_mirtillo',         'ahn_blueberry',        'stesso_ingrediente', '{}'),
('prod_vino_bianco',      'ahn_white_wine',       'stesso_ingrediente', '{}'),
('prod_vino_rosso',       'ahn_red_wine',         'stesso_ingrediente', '{}'),
('prod_birra',            'ahn_beer',             'stesso_ingrediente', '{}'),
('prod_rum',              'ahn_rum',              'stesso_ingrediente', '{}'),
('prod_whiskey',          'ahn_whiskey',          'stesso_ingrediente', '{}'),
('prod_cognac',           'ahn_cognac',           'stesso_ingrediente', '{}'),
('prod_manzo',            'ahn_beef',             'stesso_ingrediente', '{}'),
('prod_pollo',            'ahn_chicken',          'stesso_ingrediente', '{}'),
('prod_salmone',          'ahn_salmon',           'stesso_ingrediente', '{}'),
('prod_tonno',            'ahn_tuna',             'stesso_ingrediente', '{}'),
('prod_soia',             'ahn_soybean',          'stesso_ingrediente', '{}'),
('prod_porcini',          'ahn_porcini',          'stesso_ingrediente', '{}'),
('prod_shiitake',         'ahn_shiitake',         'stesso_ingrediente', '{}')
ON CONFLICT DO NOTHING;
