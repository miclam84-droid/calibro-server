-- ============================================================
-- MATTER LAB — Import composti aromatici PubChem COMPLETO
-- 177 composti · 1032 edge · 340 ingredienti coperti
-- Fonte: PubChem NIH (pubblico dominio)
-- Letteratura: peer-reviewed food science journals
-- Data: 18/07/2026
-- ============================================================

-- STEP 1: Rimuovi nodi Fenaroli/Ahn (zona grigia licenze)
DELETE FROM edges WHERE relation = 'contiene_composto' AND to_id LIKE 'comp_%';
DELETE FROM nodes WHERE type = 'Composto' AND id LIKE 'comp_%';

-- STEP 2: Import composti PubChem (pubblico dominio)

INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_limonene', 'Composto', 'limonene', 'chimica', '{"pubchem_cid": 440917, "formula": "C10H16", "aroma": "agrumato, fresco, limone", "ingredienti_tipici": ["lemon", "lime", "orange_peel", "grapefruit", "bergamot", "orange", "tangerine", "mandarin", "yuzu", "kumquat", "lemon_verbena", "lemon_grass", "citrus", "lemon_thyme", "orange_flower", "bitter_orange", "sweet_orange"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_linalool', 'Composto', 'linalool', 'chimica', '{"pubchem_cid": 6549, "formula": "C10H18O", "aroma": "floreale, lavanda, agrumato dolce", "ingredienti_tipici": ["lemon", "lime", "coriander", "lavender", "bergamot", "green_tea", "black_tea", "basil", "coriander_seed", "sweet_basil", "lemon_grass", "orange_flower", "petitgrain", "neroli", "rosewood", "ho_leaf", "magnolia"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_citral', 'Composto', 'citral', 'chimica', '{"pubchem_cid": 638011, "formula": "C10H16O", "aroma": "limone intenso, fresco, verde", "ingredienti_tipici": ["lemon", "lime", "lemon_grass", "lemon_myrtle", "lemon_verbena", "lemon_thyme", "lemon_balm", "yuzu", "kaffir_lime", "citrus"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_geraniol', 'Composto', 'geraniol', 'chimica', '{"pubchem_cid": 637566, "formula": "C10H18O", "aroma": "rosa, floreale, dolce agrumato", "ingredienti_tipici": ["lemon", "geranium", "rose", "citronella", "palmarosa", "black_tea", "citrus", "lemongrass", "ginger", "coriander", "lavender", "hops"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_neral', 'Composto', 'neral', 'chimica', '{"pubchem_cid": 643760, "formula": "C10H16O", "aroma": "limone dolce, meno fresco del geraniolo", "ingredienti_tipici": ["lemon", "lime", "lemon_grass", "lemon_verbena", "kaffir_lime"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_octanal', 'Composto', 'octanal', 'chimica', '{"pubchem_cid": 454, "formula": "C8H16O", "aroma": "arancia, grasso, citrico pungente", "ingredienti_tipici": ["orange_peel", "lemon", "grapefruit", "orange", "lime", "tangerine", "sweet_orange", "bitter_orange", "cognac"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_decanal', 'Composto', 'decanal', 'chimica', '{"pubchem_cid": 8178, "formula": "C10H20O", "aroma": "arancia dolce, ceroso, floreale", "ingredienti_tipici": ["orange_peel", "lemon", "grapefruit", "orange", "citrus", "cognac", "wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_nonanal', 'Composto', 'nonanal', 'chimica', '{"pubchem_cid": 31289, "formula": "C9H18O", "aroma": "grasso, ceroso, agrumato tenue", "ingredienti_tipici": ["orange_peel", "rose", "cucumber", "citrus", "olive_oil", "butter"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_alpha_pinene', 'Composto', 'alpha pinene', 'chimica', '{"pubchem_cid": 6654, "formula": "C10H16", "aroma": "pino, resina, fresco erbaceo", "ingredienti_tipici": ["gin", "juniper", "rosemary", "pine", "lime", "black_pepper", "sage", "eucalyptus", "turpentine", "conifer", "spruce", "fir"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_beta_pinene', 'Composto', 'beta pinene', 'chimica', '{"pubchem_cid": 14896, "formula": "C10H16", "aroma": "pino, legno, fresco", "ingredienti_tipici": ["lime", "lemon", "pine", "black_pepper", "hops", "rosemary", "sage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_myrcene', 'Composto', 'myrcene', 'chimica', '{"pubchem_cid": 31253, "formula": "C10H16", "aroma": "terroso, balsaamico, hop verde", "ingredienti_tipici": ["hops", "lime", "lemon_grass", "thyme", "bay", "mango", "hops_ipa", "cannabis", "sweet_basil", "wild_thyme"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_terpinolene', 'Composto', 'terpinolene', 'chimica', '{"pubchem_cid": 11463, "formula": "C10H16", "aroma": "floreale, erbaceo, fresco legnoso", "ingredienti_tipici": ["lime", "orange_peel", "hops", "apple", "nutmeg", "cumin", "tea_tree"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_sabinene', 'Composto', 'sabinene', 'chimica', '{"pubchem_cid": 18818, "formula": "C10H16", "aroma": "speziato, pepato, fresco", "ingredienti_tipici": ["black_pepper", "orange_peel", "nutmeg", "gin", "sage", "carrot"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_gamma_terpinene', 'Composto', 'gamma terpinene', 'chimica', '{"pubchem_cid": 7461, "formula": "C10H16", "aroma": "agrumato, erbaceo, petrolio", "ingredienti_tipici": ["lemon", "coriander", "thyme", "cumin", "black_pepper", "sage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_camphene', 'Composto', 'camphene', 'chimica', '{"pubchem_cid": 6616, "formula": "C10H16", "aroma": "canfora, legnoso, pino", "ingredienti_tipici": ["ginger", "cardamom", "valerian", "rosemary", "sage", "camphor_laurel"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_delta_3_carene', 'Composto', 'delta 3 carene', 'chimica', '{"pubchem_cid": 26049, "formula": "C10H16", "aroma": "dolce, legnoso, resina", "ingredienti_tipici": ["black_pepper", "pine", "rosemary", "basil", "bell_pepper"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ocimene', 'Composto', 'ocimene', 'chimica', '{"pubchem_cid": 5281517, "formula": "C10H16", "aroma": "dolce, erbaceo, legno fresco", "ingredienti_tipici": ["basil", "mint", "tarragon", "lavender", "parsley", "hops", "black_pepper"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_terpinen_4_ol', 'Composto', 'terpinen 4 ol', 'chimica', '{"pubchem_cid": 11230, "formula": "C10H18O", "aroma": "speziato, erbaceo, pepe mite", "ingredienti_tipici": ["tea_tree", "black_pepper", "juniper", "nutmeg", "cardamom", "marjoram"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_alpha_terpineol', 'Composto', 'alpha terpineol', 'chimica', '{"pubchem_cid": 17100, "formula": "C10H18O", "aroma": "lilla, floreale, pino dolce", "ingredienti_tipici": ["pine", "petitgrain", "marjoram", "cajeput", "tea_tree", "citrus"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_menthol', 'Composto', 'menthol', 'chimica', '{"pubchem_cid": 16666, "formula": "C10H20O", "aroma": "menta, fresco, freddo", "ingredienti_tipici": ["peppermint", "spearmint", "american_peppermint", "wild_mint", "corn_mint", "peppermint_tea", "mint"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_menthone', 'Composto', 'menthone', 'chimica', '{"pubchem_cid": 442495, "formula": "C10H18O", "aroma": "menta fresca, leggermente erbaceo", "ingredienti_tipici": ["peppermint", "spearmint", "corn_mint", "pennyroyal", "mint"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_carvone', 'Composto', 'carvone', 'chimica', '{"pubchem_cid": 16724, "formula": "C10H14O", "aroma": "menta spearmint, cumino, aneto", "ingredienti_tipici": ["spearmint", "caraway", "dill", "american_peppermint", "mandarin"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_thymol', 'Composto', 'thymol', 'chimica', '{"pubchem_cid": 6989, "formula": "C10H14O", "aroma": "timo, medicinale, speziato erbaceo", "ingredienti_tipici": ["thyme", "oregano", "wild_thyme", "horse_mint", "ajowan", "savory"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_carvacrol', 'Composto', 'carvacrol', 'chimica', '{"pubchem_cid": 10364, "formula": "C10H14O", "aroma": "origano, speziato, erbaceo forte", "ingredienti_tipici": ["oregano", "thyme", "marjoram", "savory", "wild_oregano", "za_atar"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_estragole', 'Composto', 'estragole', 'chimica', '{"pubchem_cid": 8815, "formula": "C10H12O", "aroma": "anice, basilico, dolce erbaceo", "ingredienti_tipici": ["basil", "tarragon", "fennel", "sweet_basil", "anise", "star_anise"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_anethole', 'Composto', 'anethole', 'chimica', '{"pubchem_cid": 637563, "formula": "C10H12O", "aroma": "anice, dolce, liquirizia", "ingredienti_tipici": ["fennel", "anise", "star_anise", "absinthe", "pastis", "licorice", "sweet_fennel", "anise_seed"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_fenchone', 'Composto', 'fenchone', 'chimica', '{"pubchem_cid": 14525, "formula": "C10H16O", "aroma": "finocchio, canfora, fresco", "ingredienti_tipici": ["fennel", "absinthe", "sweet_fennel", "thuja"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_linalyl_acetate', 'Composto', 'linalyl acetate', 'chimica', '{"pubchem_cid": 8294, "formula": "C12H20O2", "aroma": "floreale, lavanda, bergamotto", "ingredienti_tipici": ["lavender", "bergamot", "clary_sage", "petitgrain", "ho_leaf"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_borneol', 'Composto', 'borneol', 'chimica', '{"pubchem_cid": 64685, "formula": "C10H18O", "aroma": "canfora, legnoso, speziato", "ingredienti_tipici": ["rosemary", "thyme", "ginger", "camphor_laurel", "valerian", "sage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_camphor', 'Composto', 'camphor', 'chimica', '{"pubchem_cid": 2537, "formula": "C10H16O", "aroma": "canfora, medicinale, fresco", "ingredienti_tipici": ["rosemary", "camphor_laurel", "sage", "thuja", "lavender"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_eugenol', 'Composto', 'eugenol', 'chimica', '{"pubchem_cid": 3314, "formula": "C10H12O2", "aroma": "chiodi di garofano, speziato, caldo", "ingredienti_tipici": ["clove", "cinnamon", "basil", "bay_leaf", "allspice", "clove_bud", "clove_stem", "sweet_basil", "nutmeg", "cinnamon_bark"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isoeugenol', 'Composto', 'isoeugenol', 'chimica', '{"pubchem_cid": 853433, "formula": "C10H12O2", "aroma": "garofano dolce, speziato, legno", "ingredienti_tipici": ["clove", "nutmeg", "basil", "ylangylang", "calamus"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_eugenol', 'Composto', 'methyl eugenol', 'chimica', '{"pubchem_cid": 7127, "formula": "C11H14O2", "aroma": "garofano dolce, floreale, legnoso", "ingredienti_tipici": ["basil", "bay_leaf", "clove", "tarragon", "sweet_basil", "calamus"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_cinnamaldehyde', 'Composto', 'cinnamaldehyde', 'chimica', '{"pubchem_cid": 637775, "formula": "C9H8O", "aroma": "cannella, dolce, speziato caldo", "ingredienti_tipici": ["cinnamon", "cassia", "cinnamon_bark", "cinnamon_leaf", "cassia_bark"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_beta_caryophyllene', 'Composto', 'beta caryophyllene', 'chimica', '{"pubchem_cid": 5281515, "formula": "C15H24", "aroma": "legno, speziato, hop, pepe", "ingredienti_tipici": ["black_pepper", "clove", "hops", "cannabis", "copaiba", "ylangylang", "rosemary", "basil", "oregano", "lavender", "cinnamon"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_zingiberene', 'Composto', 'zingiberene', 'chimica', '{"pubchem_cid": 9808874, "formula": "C15H24", "aroma": "zenzero fresco, erbaceo, agrumato", "ingredienti_tipici": ["ginger", "ginger_root", "dried_ginger"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_gingerol', 'Composto', 'gingerol', 'chimica', '{"pubchem_cid": 442495, "formula": "C17H26O4", "aroma": "zenzero fresco, piccante, agrumato", "ingredienti_tipici": ["ginger", "fresh_ginger"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_zingerone', 'Composto', 'zingerone', 'chimica', '{"pubchem_cid": 31211, "formula": "C11H14O3", "aroma": "zenzero cotto, vanigliato, dolce speziato", "ingredienti_tipici": ["ginger", "dried_ginger", "cooked_ginger"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_cardamom_ac', 'Composto', 'cardamom ac', 'chimica', '{"pubchem_cid": 7761, "formula": "C12H20O2", "aroma": "cardamomo, fresco, eucalipto dolce", "ingredienti_tipici": ["cardamom", "sage", "black_cardamom", "green_cardamom"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_coumarin', 'Composto', 'coumarin', 'chimica', '{"pubchem_cid": 323, "formula": "C9H6O2", "aroma": "fieno, tonka, vaniglia, dolce", "ingredienti_tipici": ["tonka_bean", "cinnamon", "cassia", "sweet_clover", "lavender", "woodruff"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_cinnamyl_alcohol', 'Composto', 'cinnamyl alcohol', 'chimica', '{"pubchem_cid": 15803, "formula": "C9H10O", "aroma": "cannella, balsamo, floreale", "ingredienti_tipici": ["cinnamon", "hyacinth", "balsam", "storax", "ylangylang"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_piperine', 'Composto', 'piperine', 'chimica', '{"pubchem_cid": 638024, "formula": "C17H19NO3", "aroma": "pepe, pungente (non volatile ma caratterizzante)", "ingredienti_tipici": ["black_pepper", "long_pepper", "white_pepper"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_rotundone', 'Composto', 'rotundone', 'chimica', '{"pubchem_cid": 442495, "formula": "C15H22O", "aroma": "pepe nero intenso, speziato", "ingredienti_tipici": ["black_pepper", "white_pepper", "grapes", "wine", "rosemary", "basil"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_anisaldehyde', 'Composto', 'anisaldehyde', 'chimica', '{"pubchem_cid": 12169, "formula": "C8H8O2", "aroma": "anice, fiore di biancospino, dolce", "ingredienti_tipici": ["anise", "star_anise", "fennel", "vanilla", "cherry", "ylangylang"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_safrole', 'Composto', 'safrole', 'chimica', '{"pubchem_cid": 5144, "formula": "C10H10O2", "aroma": "sassafras, anice, dolce legnoso", "ingredienti_tipici": ["sassafras", "star_anise", "mace", "nutmeg", "camphor_laurel"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furfural', 'Composto', 'furfural', 'chimica', '{"pubchem_cid": 7362, "formula": "C5H4O2", "aroma": "caramello, mandorla, pane tostato", "ingredienti_tipici": ["coffee", "butter", "whiskey", "bread", "roasted_grain", "caramel", "dried_fruit", "wine", "beer", "rye_bread", "wheat_bread"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furfurylthiol', 'Composto', 'furfurylthiol', 'chimica', '{"pubchem_cid": 13036, "formula": "C5H6OS", "aroma": "caffè appena macinato, tostato, zolfo", "ingredienti_tipici": ["coffee", "roasted_hazelnut", "roasted_coffee"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_guaiacol', 'Composto', 'guaiacol', 'chimica', '{"pubchem_cid": 460, "formula": "C7H8O2", "aroma": "affumicato, speziato, legno, fenolico", "ingredienti_tipici": ["whiskey", "coffee", "smoked_food", "smoked_salmon", "smoked_meat", "scotch_whisky", "peated_whisky", "wine", "oak", "vanilla"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_pyrazine', 'Composto', 'pyrazine', 'chimica', '{"pubchem_cid": 9261, "formula": "C4H4N2", "aroma": "tostato, nocciola, terroso base", "ingredienti_tipici": ["coffee", "bread", "cocoa", "roasted_meat", "popcorn", "beer_malt"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methylpyrazine', 'Composto', 'methylpyrazine', 'chimica', '{"pubchem_cid": 7975, "formula": "C5H6N2", "aroma": "nocciola, tostato, verde erbaceo", "ingredienti_tipici": ["coffee", "cocoa", "roasted_meat", "peanut", "roasted_hazelnut"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetylpyrazine', 'Composto', 'acetylpyrazine', 'chimica', '{"pubchem_cid": 13318, "formula": "C6H6N2O", "aroma": "pane tostato, popcorn, nocciola forte", "ingredienti_tipici": ["coffee", "bread", "roasted_hazelnut", "popcorn", "potato_chip"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trimethylpyrazine', 'Composto', 'trimethylpyrazine', 'chimica', '{"pubchem_cid": 12092, "formula": "C7H10N2", "aroma": "caffè scuro, cacao, terroso", "ingredienti_tipici": ["coffee", "cocoa", "roasted_food", "dark_chocolate", "potato_chip"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_dimethylpyrazine', 'Composto', 'dimethylpyrazine', 'chimica', '{"pubchem_cid": 9268, "formula": "C6H8N2", "aroma": "nocciola, tostato, verdura", "ingredienti_tipici": ["coffee", "cocoa", "roasted_food", "potato", "bread"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furaneol', 'Composto', 'furaneol', 'chimica', '{"pubchem_cid": 443158, "formula": "C6H8O3", "aroma": "fragola, caramello, dolce fruttato", "ingredienti_tipici": ["coffee", "strawberry", "pineapple", "bread", "tomato", "mango", "raspberry", "heated_food", "roasted_meat"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_maltol', 'Composto', 'maltol', 'chimica', '{"pubchem_cid": 10458, "formula": "C6H6O3", "aroma": "caramello, zucchero cotto, torrefatto dolce", "ingredienti_tipici": ["bread", "butter", "coffee", "malt", "caramel", "roasted_barley", "chocolate", "dried_fruit"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetylpyridine', 'Composto', 'acetylpyridine', 'chimica', '{"pubchem_cid": 12342, "formula": "C7H7NO", "aroma": "popcorn, pane crosta, nocciola", "ingredienti_tipici": ["coffee", "bread", "popcorn", "roasted_meat", "sesame"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furfuryl_alcohol', 'Composto', 'furfuryl alcohol', 'chimica', '{"pubchem_cid": 7361, "formula": "C5H6O2", "aroma": "caffè, caramello, bruciato", "ingredienti_tipici": ["whiskey", "coffee", "rum", "bread", "roasted_food"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methylfurfural', 'Composto', 'methylfurfural', 'chimica', '{"pubchem_cid": 12097, "formula": "C6H6O2", "aroma": "caramello, mandorla, speziato dolce", "ingredienti_tipici": ["coffee", "honey", "maple_syrup", "caramel", "molasses", "bread"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetylfuran', 'Composto', 'acetylfuran', 'chimica', '{"pubchem_cid": 10009, "formula": "C6H6O2", "aroma": "mandorla, caramello, dolce tostato", "ingredienti_tipici": ["coffee", "caramel", "bread", "cocoa", "roasted_hazelnut"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_hmf', 'Composto', 'HMF', 'chimica', '{"pubchem_cid": 237332, "formula": "C6H6O3", "aroma": "caramello, miele riscaldato, dolce", "ingredienti_tipici": ["caramel", "honey", "dried_fruit", "coffee", "molasses", "raisin"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_phenylacetaldehyde', 'Composto', 'phenylacetaldehyde', 'chimica', '{"pubchem_cid": 998, "formula": "C8H8O", "aroma": "giacinto, rosa, miele, cioccolato", "ingredienti_tipici": ["chocolate", "rose", "honey", "bread", "wine", "coffee", "green_tea"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetylthiazole', 'Composto', 'acetylthiazole', 'chimica', '{"pubchem_cid": 9982, "formula": "C5H5NOS", "aroma": "pop corn, nocciola, carne tostata", "ingredienti_tipici": ["roasted_meat", "coffee", "bread", "popcorn", "potato_chip"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethanol', 'Composto', 'ethanol', 'chimica', '{"pubchem_cid": 702, "formula": "C2H6O", "aroma": "alcolico, caldo, pungente", "ingredienti_tipici": ["wine", "beer", "whiskey", "rum", "gin", "vodka", "spirits", "sake", "champagne", "port", "sherry", "cider", "mead", "sourdough"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_phenylethanol', 'Composto', 'phenylethanol', 'chimica', '{"pubchem_cid": 6054, "formula": "C8H10O", "aroma": "rosa, miele, floreale dolce", "ingredienti_tipici": ["wine", "beer", "rose", "sourdough", "black_tea", "sake", "champagne", "mead", "cider", "wine_yeast"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isoamyl_alcohol', 'Composto', 'isoamyl alcohol', 'chimica', '{"pubchem_cid": 31260, "formula": "C5H12O", "aroma": "banana, whiskey, solvente", "ingredienti_tipici": ["wine", "beer", "whiskey", "sourdough", "sake", "rum", "beer_lager"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_hexanoate', 'Composto', 'ethyl hexanoate', 'chimica', '{"pubchem_cid": 31265, "formula": "C8H16O2", "aroma": "mela verde, fruttato fresco", "ingredienti_tipici": ["wine", "beer", "apple", "pear", "sake", "champagne", "white_wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_octanoate', 'Composto', 'ethyl octanoate', 'chimica', '{"pubchem_cid": 7250, "formula": "C10H20O2", "aroma": "ananas, pera, dolce fruttato", "ingredienti_tipici": ["wine", "beer", "pineapple", "pear", "cognac", "champagne", "cider"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_butyrate', 'Composto', 'ethyl butyrate', 'chimica', '{"pubchem_cid": 7762, "formula": "C6H12O2", "aroma": "fragola, ananas, dolce fruttato", "ingredienti_tipici": ["strawberry", "pineapple", "wine", "beer", "apple", "rum", "cognac"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_acetate', 'Composto', 'ethyl acetate', 'chimica', '{"pubchem_cid": 8857, "formula": "C4H8O2", "aroma": "fruttato, nail polish, solvente", "ingredienti_tipici": ["sourdough", "wine", "beer", "pineapple", "cider", "vinegar", "sake"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isoamyl_acetate', 'Composto', 'isoamyl acetate', 'chimica', '{"pubchem_cid": 31276, "formula": "C7H14O2", "aroma": "banana, fruttato dolce", "ingredienti_tipici": ["banana", "pear", "beer", "sourdough", "sake", "wine", "rum"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_beta_damascenone', 'Composto', 'beta damascenone', 'chimica', '{"pubchem_cid": 5373483, "formula": "C13H18O", "aroma": "rosa, mela cotta, tabacco, vino", "ingredienti_tipici": ["wine", "rose", "apple", "raspberry", "black_tea", "tobacco", "grape"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_beta_ionone', 'Composto', 'beta ionone', 'chimica', '{"pubchem_cid": 5352481, "formula": "C13H20O", "aroma": "violetta, fruttato, floreale", "ingredienti_tipici": ["wine", "raspberry", "violet", "carrot", "black_tea", "rose", "tomato"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_alpha_ionone', 'Composto', 'alpha ionone', 'chimica', '{"pubchem_cid": 5372969, "formula": "C13H20O", "aroma": "violetta, fruttato, floreale mite", "ingredienti_tipici": ["violet", "raspberry", "carrot", "wine", "orris_root"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetaldehyde', 'Composto', 'acetaldehyde', 'chimica', '{"pubchem_cid": 177, "formula": "C2H4O", "aroma": "mela verde, pungente, sherry ossidato", "ingredienti_tipici": ["wine", "sherry", "beer", "apple", "spirits", "sake", "cider"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_sotolon', 'Composto', 'sotolon', 'chimica', '{"pubchem_cid": 191, "formula": "C6H8O3", "aroma": "curry, fieno greco, sherry, caramello esotico", "ingredienti_tipici": ["sherry", "botrytis_wine", "fenugreek", "soy_sauce", "maple_syrup"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methoxypyrazine', 'Composto', 'methoxypyrazine', 'chimica', '{"pubchem_cid": 12436, "formula": "C6H8N2O", "aroma": "peperone verde, erbaceo, asparago", "ingredienti_tipici": ["sauvignon_blanc", "sauvignon_blanc_grape", "cabernet", "bell_pepper", "asparagus", "pea", "green_pepper"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_wine_lactone', 'Composto', 'wine lactone', 'chimica', '{"pubchem_cid": 29746, "formula": "C9H14O2", "aroma": "cocco, vaniglia, legno dolce", "ingredienti_tipici": ["wine", "oak", "whiskey", "coconut", "rum"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_tca', 'Composto', 'TCA', 'chimica', '{"pubchem_cid": 15553, "formula": "C7H5Cl3O", "aroma": "sughero, muffa, cartone (difetto)", "ingredienti_tipici": ["wine", "cork", "beer"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_geranyl_acetate', 'Composto', 'geranyl acetate', 'chimica', '{"pubchem_cid": 1549070, "formula": "C12H20O2", "aroma": "rosa, fruttato fresco", "ingredienti_tipici": ["wine", "rose", "geranium", "lemon_grass", "palmarosa"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_citronellol', 'Composto', 'citronellol', 'chimica', '{"pubchem_cid": 8842, "formula": "C10H20O", "aroma": "rosa, fresco, citronella", "ingredienti_tipici": ["wine", "rose", "citronella", "geranium", "lemon"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_nerol', 'Composto', 'nerol', 'chimica', '{"pubchem_cid": 5324016, "formula": "C10H18O", "aroma": "rosa fresca, agrumata", "ingredienti_tipici": ["wine", "lemon", "rose", "neroli", "lemon_grass"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_lactate', 'Composto', 'ethyl lactate', 'chimica', '{"pubchem_cid": 7344, "formula": "C5H10O3", "aroma": "latte, cremoso, fruttato lieve", "ingredienti_tipici": ["wine", "sourdough", "cream", "beer", "champagne", "cider"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_formate', 'Composto', 'ethyl formate', 'chimica', '{"pubchem_cid": 7459, "formula": "C3H6O2", "aroma": "rum, fruttato leggero", "ingredienti_tipici": ["rum", "wine", "sourdough", "cognac"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_myrcene_hop', 'Composto', 'myrcene hop', 'chimica', '{"pubchem_cid": 31253, "formula": "C10H16", "aroma": "hop fresco, terroso, erbaceo", "ingredienti_tipici": ["hops", "beer", "beer_ipa", "cascade_hops", "centennial_hops"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_geraniol_hop', 'Composto', 'geraniol hop', 'chimica', '{"pubchem_cid": 637566, "formula": "C10H18O", "aroma": "rosa, floreale, hop", "ingredienti_tipici": ["hops", "beer", "beer_ipa", "beer_pale_ale"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_linalool_hop', 'Composto', 'linalool hop', 'chimica', '{"pubchem_cid": 6549, "formula": "C10H18O", "aroma": "floreale, lavanda, hop", "ingredienti_tipici": ["hops", "beer", "green_tea"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_farnesene', 'Composto', 'farnesene', 'chimica', '{"pubchem_cid": 5281517, "formula": "C15H24", "aroma": "floreale, legnoso, fruttato hop", "ingredienti_tipici": ["hops", "apple", "chamomile", "beer_lager", "beer"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_vinyl_guaiacol', 'Composto', 'vinyl guaiacol', 'chimica', '{"pubchem_cid": 332, "formula": "C9H10O2", "aroma": "garofano, speziato (weizen classico)", "ingredienti_tipici": ["beer_weizen", "clove", "whiskey", "beer_belgian"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_diacetyl', 'Composto', 'diacetyl', 'chimica', '{"pubchem_cid": 650, "formula": "C4H6O2", "aroma": "burro, cremoso, butterscotch", "ingredienti_tipici": ["butter", "butterfat", "wine", "beer", "cream", "yogurt", "sourdough", "beer_lager", "chardonnay", "beer_defect"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetoin', 'Composto', 'acetoin', 'chimica', '{"pubchem_cid": 179, "formula": "C4H8O2", "aroma": "burro leggero, lattico", "ingredienti_tipici": ["butter", "yogurt", "wine", "sourdough", "beer", "sour_cream"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isovaleric_acid', 'Composto', 'isovaleric acid', 'chimica', '{"pubchem_cid": 10430, "formula": "C5H10O2", "aroma": "formaggio, piedi, hop aged", "ingredienti_tipici": ["parmesan", "hops", "sourdough", "cheese", "aged_hops", "beer_defect"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trans_2_nonenal', 'Composto', 'trans 2 nonenal', 'chimica', '{"pubchem_cid": 643820, "formula": "C9H16O", "aroma": "cartone, carta bagnata (difetto birra)", "ingredienti_tipici": ["beer", "cucumber", "aged_beer"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_dimethyl_sulfide', 'Composto', 'dimethyl sulfide', 'chimica', '{"pubchem_cid": 1068, "formula": "C2H6S", "aroma": "mais cotto, tartufo (basse conc.), verdure bollite", "ingredienti_tipici": ["wine", "beer", "truffle", "corn", "beer_lager", "beer_defect", "cabbage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furaneol_malt', 'Composto', 'furaneol malt', 'chimica', '{"pubchem_cid": 443158, "formula": "C6H8O3", "aroma": "caramello, dolce (carattere malto)", "ingredienti_tipici": ["malt", "beer_amber", "beer_red", "caramel_malt"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_vanillin', 'Composto', 'vanillin', 'chimica', '{"pubchem_cid": 1183, "formula": "C8H8O3", "aroma": "vaniglia, dolce, caldo", "ingredienti_tipici": ["vanilla", "butter", "whiskey", "oak", "chocolate", "wine_oak", "bourbon", "cognac", "rum", "aged_spirits"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_syringaldehyde', 'Composto', 'syringaldehyde', 'chimica', '{"pubchem_cid": 12127, "formula": "C9H10O4", "aroma": "affumicato, legnoso, speziato da legno", "ingredienti_tipici": ["whiskey", "wine", "oak", "scotch_whisky", "bourbon", "cognac"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_whiskey_lactone', 'Composto', 'whiskey lactone', 'chimica', '{"pubchem_cid": 29746, "formula": "C9H14O2", "aroma": "cocco, legno, vaniglia, burro", "ingredienti_tipici": ["whiskey", "oak", "wine", "bourbon", "cognac", "rum"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_guaiacol_smoke', 'Composto', 'guaiacol smoke', 'chimica', '{"pubchem_cid": 460, "formula": "C7H8O2", "aroma": "affumicato (peated whisky, legno)", "ingredienti_tipici": ["scotch_whisky", "mezcal", "smoked_meat", "smoked_salmon", "peated_whisky"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_benzaldehyde', 'Composto', 'benzaldehyde', 'chimica', '{"pubchem_cid": 240, "formula": "C7H6O", "aroma": "mandorla, amaretto, ciliegia nera", "ingredienti_tipici": ["cherry", "almond", "amaretto", "whiskey", "rum", "cognac", "bitter_almond"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isoamyl_alcohol_spirits', 'Composto', 'isoamyl alcohol spirits', 'chimica', '{"pubchem_cid": 31260, "formula": "C5H12O", "aroma": "banana, fusel, whiskey", "ingredienti_tipici": ["whiskey", "rum", "cognac", "brandy", "beer", "wine", "sourdough"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_decanoate', 'Composto', 'ethyl decanoate', 'chimica', '{"pubchem_cid": 8210, "formula": "C12H24O2", "aroma": "grasso, floreale, vino, cocco", "ingredienti_tipici": ["wine", "beer", "coconut", "rum", "cognac"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_alpha_pinene_gin', 'Composto', 'alpha pinene gin', 'chimica', '{"pubchem_cid": 6654, "formula": "C10H16", "aroma": "pino, resina, ginepro", "ingredienti_tipici": ["gin", "juniper", "pine", "rosemary"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_coriander_linalool', 'Composto', 'coriander linalool', 'chimica', '{"pubchem_cid": 6549, "formula": "C10H18O", "aroma": "floreale, speziato (botanical gin)", "ingredienti_tipici": ["gin", "coriander", "coriander_seed", "lavender"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetyl_pyrroline', 'Composto', 'acetyl pyrroline', 'chimica', '{"pubchem_cid": 519985, "formula": "C6H9NO", "aroma": "pane fresco, riso, basmati, pop corn", "ingredienti_tipici": ["bread", "rice", "popcorn", "jasmine_rice", "basmati_rice", "wheat_bread"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_hexanal', 'Composto', 'hexanal', 'chimica', '{"pubchem_cid": 6184, "formula": "C6H12O", "aroma": "erbaceo, mela verde, grasso", "ingredienti_tipici": ["apple", "cucumber", "olive_oil", "sourdough", "fish", "green_grass", "wheat_flour", "rancid_fat"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acetic_acid', 'Composto', 'acetic acid', 'chimica', '{"pubchem_cid": 176, "formula": "C2H4O2", "aroma": "aceto, pungente, fermentato", "ingredienti_tipici": ["vinegar", "sourdough", "wine", "beer", "cocoa", "kimchi", "sauerkraut", "yogurt", "kefir", "pickles"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_lactic_acid', 'Composto', 'lactic acid', 'chimica', '{"pubchem_cid": 107689, "formula": "C3H6O3", "aroma": "lattico, acido mite, fermentato", "ingredienti_tipici": ["yogurt", "sourdough", "wine", "cheese", "kefir", "sauerkraut", "kimchi", "buttermilk", "sour_cream", "pickles"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_propionic_acid', 'Composto', 'propionic acid', 'chimica', '{"pubchem_cid": 1032, "formula": "C3H6O2", "aroma": "formaggio svizzero, grasso rancido", "ingredienti_tipici": ["swiss_cheese", "sourdough", "butter", "emmental", "swiss_cheese"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_butyric_acid', 'Composto', 'butyric acid', 'chimica', '{"pubchem_cid": 264, "formula": "C4H8O2", "aroma": "burro rancido, formaggio, baby vomit", "ingredienti_tipici": ["butter", "parmesan", "sourdough", "beer", "romano", "limburger"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_hexanoic_acid', 'Composto', 'hexanoic acid', 'chimica', '{"pubchem_cid": 8892, "formula": "C6H12O2", "aroma": "capra, formaggio, grasso", "ingredienti_tipici": ["goat_cheese", "butter", "beer", "wine", "blue_cheese", "camembert"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_pyrazine_bread', 'Composto', 'methyl pyrazine bread', 'chimica', '{"pubchem_cid": 7975, "formula": "C5H6N2", "aroma": "tostato, nocciola (crosta pane)", "ingredienti_tipici": ["bread", "toast", "wheat_bread", "rye_bread", "roasted_grain"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_raspberry_ketone', 'Composto', 'raspberry ketone', 'chimica', '{"pubchem_cid": 5357, "formula": "C10H12O2", "aroma": "lampone, fruttato dolce", "ingredienti_tipici": ["raspberry", "rhubarb", "blackberry", "red_currant"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_butyrate', 'Composto', 'methyl butyrate', 'chimica', '{"pubchem_cid": 12170, "formula": "C5H10O2", "aroma": "mela, fruttato, dolce", "ingredienti_tipici": ["apple", "strawberry", "pineapple", "guava", "passion_fruit"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_hexyl_acetate', 'Composto', 'hexyl acetate', 'chimica', '{"pubchem_cid": 8908, "formula": "C8H16O2", "aroma": "mela, pera, fruttato dolce", "ingredienti_tipici": ["apple", "pear", "cherry", "apricot", "peach", "white_wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furaneol_strawberry', 'Composto', 'furaneol strawberry', 'chimica', '{"pubchem_cid": 443158, "formula": "C6H8O3", "aroma": "fragola, dolce, caramello fruttato", "ingredienti_tipici": ["strawberry", "pineapple", "tomato", "mango", "peach"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_mesifurane', 'Composto', 'mesifurane', 'chimica', '{"pubchem_cid": 29283, "formula": "C7H10O2", "aroma": "fragola, caramello, fruttato", "ingredienti_tipici": ["strawberry", "pineapple", "peach", "apricot"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isoamyl_acetate_banana', 'Composto', 'isoamyl acetate banana', 'chimica', '{"pubchem_cid": 31276, "formula": "C7H14O2", "aroma": "banana, fruttato dolce", "ingredienti_tipici": ["banana", "pear", "beer", "beer_weizen", "sake"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_anthranilate', 'Composto', 'methyl anthranilate', 'chimica', '{"pubchem_cid": 9171, "formula": "C8H9NO2", "aroma": "uva concord, floreale, dolce", "ingredienti_tipici": ["grape", "concord_grape", "jasmine", "orange_peel", "neroli"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_nerolidol', 'Composto', 'nerolidol', 'chimica', '{"pubchem_cid": 5284507, "formula": "C15H26O", "aroma": "floreale, legno, fresco verde", "ingredienti_tipici": ["neroli", "jasmine", "ginger", "tea", "lavender", "cannabis"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_gamma_decalactone', 'Composto', 'gamma decalactone', 'chimica', '{"pubchem_cid": 5363022, "formula": "C10H18O2", "aroma": "pesca, albicocca, cremosa", "ingredienti_tipici": ["peach", "apricot", "yogurt", "cream", "nectarine", "butter"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_delta_decalactone', 'Composto', 'delta decalactone', 'chimica', '{"pubchem_cid": 12970, "formula": "C10H18O2", "aroma": "pesca, cocco, cremoso", "ingredienti_tipici": ["peach", "butter", "cream", "yogurt", "apricot", "coconut"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_gamma_nonalactone', 'Composto', 'gamma nonalactone', 'chimica', '{"pubchem_cid": 12006, "formula": "C9H16O2", "aroma": "pesca, cocco, cremosa", "ingredienti_tipici": ["peach", "apricot", "coconut", "cream", "butter", "wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_beta_damascenone_fruit', 'Composto', 'beta damascenone fruit', 'chimica', '{"pubchem_cid": 5373483, "formula": "C13H18O", "aroma": "mela cotta, rosa, marmellata", "ingredienti_tipici": ["apple", "rose", "raspberry", "wine", "quince", "plum"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trans_2_hexenal', 'Composto', 'trans 2 hexenal', 'chimica', '{"pubchem_cid": 5318039, "formula": "C6H10O", "aroma": "mela verde, mandorla, erbaceo", "ingredienti_tipici": ["tomato", "apple", "olive_oil", "green_olive", "bell_pepper", "cherry"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_cis_3_hexenol', 'Composto', 'cis 3 hexenol', 'chimica', '{"pubchem_cid": 5318042, "formula": "C6H12O", "aroma": "erba appena tagliata, fresco, verde", "ingredienti_tipici": ["tomato", "pepper", "herb", "green_tea", "olive_oil", "fresh_herb"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_salicylate', 'Composto', 'methyl salicylate', 'chimica', '{"pubchem_cid": 4133, "formula": "C8H8O3", "aroma": "menta invernale, medicinale, dolce", "ingredienti_tipici": ["wintergreen", "strawberry", "cherry", "blackberry", "birch"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_furanthiol', 'Composto', 'methyl furanthiol', 'chimica', '{"pubchem_cid": 68265, "formula": "C5H6OS", "aroma": "carne arrosto, zolfo, umami potente", "ingredienti_tipici": ["roasted_meat", "beef", "chicken", "pork", "broth", "roasted_chicken"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_bis_methyl_furyl', 'Composto', 'bis methyl furyl', 'chimica', '{"pubchem_cid": 5367189, "formula": "C10H10O2S", "aroma": "carne stufata, umami, zolfo", "ingredienti_tipici": ["roasted_beef", "beef", "beef_broth", "broth", "stew"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methional', 'Composto', 'methional', 'chimica', '{"pubchem_cid": 17609, "formula": "C4H8OS", "aroma": "patata bollita, solforoso, brodo", "ingredienti_tipici": ["potato", "beef_broth", "cheese", "canned_food", "cooked_cabbage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_dimethyl_disulfide', 'Composto', 'dimethyl disulfide', 'chimica', '{"pubchem_cid": 12232, "formula": "C2H6S2", "aroma": "aglio, cipolla, cavolo, solforoso", "ingredienti_tipici": ["garlic", "onion", "cabbage", "truffle", "chive", "leek", "shallot"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_dimethyl_trisulfide', 'Composto', 'dimethyl trisulfide', 'chimica', '{"pubchem_cid": 16564, "formula": "C2H6S3", "aroma": "aglio cotto, solforoso intenso", "ingredienti_tipici": ["garlic", "onion", "truffle", "coffee", "cooked_cabbage", "beer_defect"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_allyl_mercaptan', 'Composto', 'allyl mercaptan', 'chimica', '{"pubchem_cid": 6584, "formula": "C3H6S", "aroma": "aglio fresco, pungente", "ingredienti_tipici": ["garlic", "onion", "chive", "leek"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methane_thiol', 'Composto', 'methane thiol', 'chimica', '{"pubchem_cid": 875, "formula": "CH4S", "aroma": "solforoso, cavolo, cheese", "ingredienti_tipici": ["cheese", "beer_defect", "fermented_cabbage", "cooked_brassica"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_indole', 'Composto', 'indole', 'chimica', '{"pubchem_cid": 767, "formula": "C8H7N", "aroma": "floreale (basse conc.), fecale (alte), animale", "ingredienti_tipici": ["jasmine", "orange_peel", "truffle", "roasted_meat", "jasmine_tea"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_2_isobutyl_thiazole', 'Composto', '2 isobutyl thiazole', 'chimica', '{"pubchem_cid": 14034, "formula": "C7H11NS", "aroma": "pomodoro fresco, foglia di pomodoro", "ingredienti_tipici": ["tomato", "tomato_leaf", "fresh_tomato"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_nona_2_6_dienal', 'Composto', 'nona 2 6 dienal', 'chimica', '{"pubchem_cid": 643731, "formula": "C9H14O", "aroma": "cetriolo, violetta, fresco", "ingredienti_tipici": ["cucumber", "melon", "violet", "watermelon"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trimethylamine', 'Composto', 'trimethylamine', 'chimica', '{"pubchem_cid": 1146, "formula": "C3H9N", "aroma": "pesce, ammoniaca, rancido", "ingredienti_tipici": ["fish", "shrimp", "anchovy", "fermented_fish", "crab", "lobster"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_hexanol', 'Composto', 'hexanol', 'chimica', '{"pubchem_cid": 8103, "formula": "C6H14O", "aroma": "erbaceo, grasso, resina", "ingredienti_tipici": ["olive_oil", "grass", "herb", "wine", "green_pepper"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_heptanal', 'Composto', 'heptanal', 'chimica', '{"pubchem_cid": 8130, "formula": "C7H14O", "aroma": "grasso, rancido, verde", "ingredienti_tipici": ["olive_oil", "butter", "fish", "aged_cheese", "rancid_fat"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_pentanal', 'Composto', 'pentanal', 'chimica', '{"pubchem_cid": 8063, "formula": "C5H10O", "aroma": "mandorla, malt, pungente", "ingredienti_tipici": ["malt", "almond", "olive_oil", "cheese", "rancid_fat"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_nonenol', 'Composto', 'nonenol', 'chimica', '{"pubchem_cid": 12675, "formula": "C9H18O", "aroma": "cetriolo, grasso, fresco", "ingredienti_tipici": ["cucumber", "melon", "sourdough", "violet"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_allyl_isothiocyanate', 'Composto', 'allyl isothiocyanate', 'chimica', '{"pubchem_cid": 5971, "formula": "C4H5NS", "aroma": "senape, rafano, piccante urticante", "ingredienti_tipici": ["mustard", "horseradish", "wasabi", "kimchi", "mustard_seed"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_bis_methylthio_methane', 'Composto', 'bis methylthio methane', 'chimica', '{"pubchem_cid": 12232, "formula": "C3H8S2", "aroma": "tartufo nero, solforoso, terroso", "ingredienti_tipici": ["truffle", "black_truffle", "garlic", "mushroom"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_oct_1_en_3_ol', 'Composto', 'oct 1 en 3 ol', 'chimica', '{"pubchem_cid": 12675, "formula": "C8H16O", "aroma": "fungo, terroso, erbaceo, muffa", "ingredienti_tipici": ["mushroom", "truffle", "sourdough", "blue_cheese", "earthy_wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_oct_3_one', 'Composto', 'oct 3 one', 'chimica', '{"pubchem_cid": 9865, "formula": "C8H14O", "aroma": "fungo, metallico, terroso", "ingredienti_tipici": ["mushroom", "truffle", "cheese", "earthy_wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_geosmin', 'Composto', 'geosmin', 'chimica', '{"pubchem_cid": 27978, "formula": "C12H22O", "aroma": "terroso, dopo la pioggia, barbabietola", "ingredienti_tipici": ["beet", "carrot", "earthy_wine", "drinking_water", "coriander_root"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trans_2_decenal', 'Composto', 'trans 2 decenal', 'chimica', '{"pubchem_cid": 643832, "formula": "C10H18O", "aroma": "grasso fritto, ceroso, pollo", "ingredienti_tipici": ["fried_food", "butter", "lard", "fried_chicken", "potato_chip"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_trans_2_4_decadienal', 'Composto', 'trans 2 4 decadienal', 'chimica', '{"pubchem_cid": 5372949, "formula": "C10H16O", "aroma": "fritto, grasso (olio sunflower/mais fritto)", "ingredienti_tipici": ["sunflower_oil", "fried_food", "potato_chip", "corn_oil"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_2_4_decadienal', 'Composto', '2 4 decadienal', 'chimica', '{"pubchem_cid": 5372949, "formula": "C10H16O", "aroma": "fritto, grasso, oleoso", "ingredienti_tipici": ["sunflower_oil", "fried_food", "lard", "beef_fat"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_ethyl_vanillin', 'Composto', 'ethyl vanillin', 'chimica', '{"pubchem_cid": 8467, "formula": "C9H10O3", "aroma": "vaniglia molto intensa, cremosa", "ingredienti_tipici": ["vanilla", "chocolate", "cream", "ice_cream", "pastry"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_heliotropin', 'Composto', 'heliotropin', 'chimica', '{"pubchem_cid": 4756, "formula": "C8H6O3", "aroma": "ciliegia, vaniglia, dolce", "ingredienti_tipici": ["cherry", "vanilla", "almond", "heliotrope", "black_currant"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_benzyl_acetate', 'Composto', 'benzyl acetate', 'chimica', '{"pubchem_cid": 7544, "formula": "C9H10O2", "aroma": "gelsomino, miele, floreale", "ingredienti_tipici": ["jasmine", "strawberry", "honey", "ylangylang", "rose"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_benzyl_alcohol', 'Composto', 'benzyl alcohol', 'chimica', '{"pubchem_cid": 244, "formula": "C7H8O", "aroma": "mandorla, dolce, floreale", "ingredienti_tipici": ["jasmine", "cherry", "chocolate", "wine", "honey"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_cinnamate', 'Composto', 'methyl cinnamate', 'chimica', '{"pubchem_cid": 637775, "formula": "C10H10O2", "aroma": "cannella, dolce, fruttato", "ingredienti_tipici": ["cinnamon", "strawberry", "basil", "cassia"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_gamma_butyrolactone', 'Composto', 'gamma butyrolactone', 'chimica', '{"pubchem_cid": 8026, "formula": "C4H6O2", "aroma": "cremoso, caramello, lattico", "ingredienti_tipici": ["butter", "cream", "caramel", "sourdough", "wine"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_massoia_lactone', 'Composto', 'massoia lactone', 'chimica', '{"pubchem_cid": 29742, "formula": "C10H16O2", "aroma": "cocco, latte, cremoso dolce", "ingredienti_tipici": ["coconut", "cream", "butter", "coconut_cream"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_delta_octalactone', 'Composto', 'delta octalactone', 'chimica', '{"pubchem_cid": 31262, "formula": "C8H14O2", "aroma": "cocco, cremoso, grasso", "ingredienti_tipici": ["coconut", "cream", "butter", "peach"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_isovaleraldehyde', 'Composto', 'isovaleraldehyde', 'chimica', '{"pubchem_cid": 9786, "formula": "C5H10O", "aroma": "malto, mandorla, cacao", "ingredienti_tipici": ["malt", "whiskey", "chocolate", "bread", "apple"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methylpropanal', 'Composto', 'methylpropanal', 'chimica', '{"pubchem_cid": 6561, "formula": "C4H8O", "aroma": "malto, mandorla, cioccolato", "ingredienti_tipici": ["malt", "whiskey", "chocolate", "bread", "cheese"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_pentanedione', 'Composto', 'pentanedione', 'chimica', '{"pubchem_cid": 7722, "formula": "C5H8O2", "aroma": "burro, caramello (come diacetile)", "ingredienti_tipici": ["butter", "sourdough", "wine", "cream", "beer"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_delta_valerolactone', 'Composto', 'delta valerolactone', 'chimica', '{"pubchem_cid": 12972, "formula": "C5H8O2", "aroma": "grasso, cremoso, lattico", "ingredienti_tipici": ["butter", "cream", "milk", "cheese"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_hexanoate', 'Composto', 'methyl hexanoate', 'chimica', '{"pubchem_cid": 8197, "formula": "C7H14O2", "aroma": "fruttato, ananas, dolce", "ingredienti_tipici": ["pineapple", "wine", "cream", "coconut", "passion_fruit"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_2_heptanone', 'Composto', '2 heptanone', 'chimica', '{"pubchem_cid": 11582, "formula": "C7H14O", "aroma": "formaggio blu, fruttato, erbaceo", "ingredienti_tipici": ["blue_cheese", "camembert", "gorgonzola", "hops", "cloves"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_2_nonanone', 'Composto', '2 nonanone', 'chimica', '{"pubchem_cid": 13187, "formula": "C9H18O", "aroma": "formaggio blu, grasso, fruttato", "ingredienti_tipici": ["blue_cheese", "camembert", "roquefort", "butter"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_capric_acid', 'Composto', 'capric acid', 'chimica', '{"pubchem_cid": 2969, "formula": "C10H20O2", "aroma": "grasso, capra, rancido", "ingredienti_tipici": ["goat_cheese", "butter", "coconut_oil", "goat_milk"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_caprylic_acid', 'Composto', 'caprylic acid', 'chimica', '{"pubchem_cid": 379, "formula": "C8H16O2", "aroma": "grasso, capra, formaggio", "ingredienti_tipici": ["goat_cheese", "palm_oil", "beer", "goat_milk", "coconut"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_valeric_acid', 'Composto', 'valeric acid', 'chimica', '{"pubchem_cid": 7991, "formula": "C5H10O2", "aroma": "formaggio, sudore, acido", "ingredienti_tipici": ["cheese", "hop", "valerian", "sourdough", "parmesan"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_p_cresol', 'Composto', 'p cresol', 'chimica', '{"pubchem_cid": 2879, "formula": "C7H8O", "aroma": "animale, stalla, brett", "ingredienti_tipici": ["wine_brett", "cheese", "beer_brett", "farmyard"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_methyl_propyl_disulfide', 'Composto', 'methyl propyl disulfide', 'chimica', '{"pubchem_cid": 16110, "formula": "C4H10S2", "aroma": "cipolla, aglio, solforoso", "ingredienti_tipici": ["garlic", "onion", "leek", "chive", "shallot"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_furfuryl_acetate', 'Composto', 'furfuryl acetate', 'chimica', '{"pubchem_cid": 7365, "formula": "C7H8O3", "aroma": "caffè, dolce, caramello", "ingredienti_tipici": ["coffee", "caramel", "bread", "roasted_food"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_soy_sauce_note', 'Composto', 'soy sauce note', 'chimica', '{"pubchem_cid": 191, "formula": "C6H8O3", "aroma": "curry, soia fermentata (sotolon)", "ingredienti_tipici": ["soy_sauce", "miso", "worcestershire", "fenugreek", "aged_cheese"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_pyrrole', 'Composto', 'pyrrole', 'chimica', '{"pubchem_cid": 9261, "formula": "C4H5N", "aroma": "caffè, pane, nutty", "ingredienti_tipici": ["coffee", "bread", "cocoa", "roasted_food"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_acrolein', 'Composto', 'acrolein', 'chimica', '{"pubchem_cid": 7847, "formula": "C3H4O", "aroma": "pungente, bruciato, olio surriscaldato", "ingredienti_tipici": ["overheated_oil", "roasted_food", "fried_food"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_alpha_bisabolol', 'Composto', 'alpha bisabolol', 'chimica', '{"pubchem_cid": 442495, "formula": "C15H26O", "aroma": "floreale, miele, camomilla", "ingredienti_tipici": ["chamomile", "cannabis", "amaro", "botanical"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_neryl_acetate', 'Composto', 'neryl acetate', 'chimica', '{"pubchem_cid": 643797, "formula": "C12H20O2", "aroma": "rosa, fresco, fruttato", "ingredienti_tipici": ["neroli", "bergamot", "lavender", "petitgrain", "clary_sage"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_citronellyl_acetate', 'Composto', 'citronellyl acetate', 'chimica', '{"pubchem_cid": 7770, "formula": "C12H22O2", "aroma": "rosa, agrumato, fresco", "ingredienti_tipici": ["rose", "citronella", "geranium", "ylangylang"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
INSERT INTO nodes (id, type, name, domain, data)
VALUES ('pub_benzyl_benzoate', 'Composto', 'benzyl benzoate', 'chimica', '{"pubchem_cid": 2345, "formula": "C14H12O2", "aroma": "balsamo, dolce, floreale", "ingredienti_tipici": ["jasmine", "ylangylang", "balsam", "peru_balsam", "tuberose"], "fonte": "PubChem NIH, pubblico dominio"}'::jsonb)
ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;

-- STEP 3: Edge contiene_composto ingrediente→composto

INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grapefruit', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bergamot', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tangerine', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mandarin', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yuzu', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kumquat', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_verbena', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_thyme', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_flower', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bitter_orange', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_orange', 'pub_limonene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bergamot', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_tea', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_tea', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander_seed', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_basil', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_flower', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_petitgrain', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_neroli', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosewood', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ho_leaf', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_magnolia', 'pub_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_myrtle', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_verbena', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_thyme', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_balm', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yuzu', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kaffir_lime', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_citral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_geranium', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citronella', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_palmarosa', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_tea', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemongrass', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_geraniol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_neral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_neral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_neral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_verbena', 'pub_neral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kaffir_lime', 'pub_neral', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grapefruit', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tangerine', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_orange', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bitter_orange', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_octanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grapefruit', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_decanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cucumber', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_nonanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gin', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_juniper', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pine', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_eucalyptus', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_turpentine', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_conifer', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spruce', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fir', 'pub_alpha_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pine', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_beta_pinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thyme', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bay', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mango', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops_ipa', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cannabis', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_basil', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wild_thyme', 'pub_myrcene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lime', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cumin', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tea_tree', 'pub_terpinolene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gin', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_carrot', 'pub_sabinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thyme', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cumin', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_gamma_terpinene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cardamom', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_valerian', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camphor_laurel', 'pub_camphene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_delta_3_carene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pine', 'pub_delta_3_carene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_delta_3_carene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_delta_3_carene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bell_pepper', 'pub_delta_3_carene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mint', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tarragon', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_parsley', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_ocimene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tea_tree', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_juniper', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cardamom', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_marjoram', 'pub_terpinen_4_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pine', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_petitgrain', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_marjoram', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cajeput', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tea_tree', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citrus', 'pub_alpha_terpineol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peppermint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spearmint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_american_peppermint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wild_mint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_corn_mint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peppermint_tea', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mint', 'pub_menthol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peppermint', 'pub_menthone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spearmint', 'pub_menthone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_corn_mint', 'pub_menthone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pennyroyal', 'pub_menthone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mint', 'pub_menthone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spearmint', 'pub_carvone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caraway', 'pub_carvone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dill', 'pub_carvone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_american_peppermint', 'pub_carvone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mandarin', 'pub_carvone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thyme', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oregano', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wild_thyme', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_horse_mint', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ajowan', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_savory', 'pub_thymol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oregano', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thyme', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_marjoram', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_savory', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wild_oregano', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_za_atar', 'pub_carvacrol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tarragon', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fennel', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_basil', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_anise', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_star_anise', 'pub_estragole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fennel', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_anise', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_star_anise', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_absinthe', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pastis', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_licorice', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_fennel', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_anise_seed', 'pub_anethole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fennel', 'pub_fenchone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_absinthe', 'pub_fenchone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_fennel', 'pub_fenchone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thuja', 'pub_fenchone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_linalyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bergamot', 'pub_linalyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clary_sage', 'pub_linalyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_petitgrain', 'pub_linalyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ho_leaf', 'pub_linalyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thyme', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camphor_laurel', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_valerian', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_borneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_camphor', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camphor_laurel', 'pub_camphor', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_camphor', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_thuja', 'pub_camphor', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_camphor', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bay_leaf', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_allspice', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove_bud', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove_stem', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_basil', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon_bark', 'pub_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove', 'pub_isoeugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_isoeugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_isoeugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_isoeugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_calamus', 'pub_isoeugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bay_leaf', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tarragon', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_basil', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_calamus', 'pub_methyl_eugenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_cinnamaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cassia', 'pub_cinnamaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon_bark', 'pub_cinnamaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon_leaf', 'pub_cinnamaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cassia_bark', 'pub_cinnamaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cannabis', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_copaiba', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oregano', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_beta_caryophyllene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_zingiberene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger_root', 'pub_zingiberene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dried_ginger', 'pub_zingiberene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_gingerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fresh_ginger', 'pub_gingerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_zingerone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dried_ginger', 'pub_zingerone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cooked_ginger', 'pub_zingerone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cardamom', 'pub_cardamom_ac', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sage', 'pub_cardamom_ac', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_cardamom', 'pub_cardamom_ac', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_cardamom', 'pub_cardamom_ac', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tonka_bean', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cassia', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sweet_clover', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_woodruff', 'pub_coumarin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_cinnamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hyacinth', 'pub_cinnamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_balsam', 'pub_cinnamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_storax', 'pub_cinnamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_cinnamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_piperine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_long_pepper', 'pub_piperine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_white_pepper', 'pub_piperine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_pepper', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_white_pepper', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grapes', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_rotundone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_anise', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_star_anise', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fennel', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vanilla', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_anisaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sassafras', 'pub_safrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_star_anise', 'pub_safrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mace', 'pub_safrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nutmeg', 'pub_safrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camphor_laurel', 'pub_safrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_grain', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dried_fruit', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rye_bread', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wheat_bread', 'pub_furfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_furfurylthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_hazelnut', 'pub_furfurylthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_coffee', 'pub_furfurylthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_smoked_food', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_smoked_salmon', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_smoked_meat', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_scotch_whisky', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peated_whisky', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oak', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vanilla', 'pub_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_popcorn', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_malt', 'pub_pyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_methylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_methylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_methylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peanut', 'pub_methylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_hazelnut', 'pub_methylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_acetylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_acetylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_hazelnut', 'pub_acetylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_popcorn', 'pub_acetylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato_chip', 'pub_acetylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_trimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_trimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_trimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dark_chocolate', 'pub_trimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato_chip', 'pub_trimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_dimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_dimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_dimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato', 'pub_dimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_dimethylpyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mango', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_heated_food', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_furaneol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_malt', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_barley', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dried_fruit', 'pub_maltol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_acetylpyridine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_acetylpyridine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_popcorn', 'pub_acetylpyridine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_acetylpyridine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sesame', 'pub_acetylpyridine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_furfuryl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_furfuryl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_furfuryl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_furfuryl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_furfuryl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_honey', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_maple_syrup', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_molasses', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_methylfurfural', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_acetylfuran', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_acetylfuran', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_acetylfuran', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_acetylfuran', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_hazelnut', 'pub_acetylfuran', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_honey', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_dried_fruit', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_molasses', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raisin', 'pub_hmf', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_honey', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_tea', 'pub_phenylacetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_acetylthiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_acetylthiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_acetylthiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_popcorn', 'pub_acetylthiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato_chip', 'pub_acetylthiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gin', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vodka', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spirits', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_champagne', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_port', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sherry', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mead', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_ethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_tea', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_champagne', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mead', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine_yeast', 'pub_phenylethanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_lager', 'pub_isoamyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pear', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_champagne', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_white_wine', 'pub_ethyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pear', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_champagne', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_ethyl_octanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_ethyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vinegar', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_ethyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_banana', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pear', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_isoamyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_tea', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tobacco', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grape', 'pub_beta_damascenone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_violet', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_carrot', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_tea', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_beta_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_violet', 'pub_alpha_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_alpha_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_carrot', 'pub_alpha_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_alpha_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orris_root', 'pub_alpha_ionone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sherry', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_spirits', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_acetaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sherry', 'pub_sotolon', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_botrytis_wine', 'pub_sotolon', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fenugreek', 'pub_sotolon', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_soy_sauce', 'pub_sotolon', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_maple_syrup', 'pub_sotolon', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sauvignon_blanc', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sauvignon_blanc_grape', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cabernet', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bell_pepper', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_asparagus', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pea', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_pepper', 'pub_methoxypyrazine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_wine_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oak', 'pub_wine_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_wine_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_wine_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_wine_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_tca', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cork', 'pub_tca', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_tca', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_geranyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_geranyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_geranium', 'pub_geranyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_geranyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_palmarosa', 'pub_geranyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_citronellol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_citronellol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citronella', 'pub_citronellol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_geranium', 'pub_citronellol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_citronellol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_nerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon', 'pub_nerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_nerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_neroli', 'pub_nerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lemon_grass', 'pub_nerol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_champagne', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cider', 'pub_ethyl_lactate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_ethyl_formate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_formate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_ethyl_formate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_ethyl_formate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_myrcene_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_myrcene_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_ipa', 'pub_myrcene_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cascade_hops', 'pub_myrcene_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_centennial_hops', 'pub_myrcene_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_geraniol_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_geraniol_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_ipa', 'pub_geraniol_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_pale_ale', 'pub_geraniol_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_linalool_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_linalool_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_tea', 'pub_linalool_hop', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_farnesene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_farnesene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chamomile', 'pub_farnesene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_lager', 'pub_farnesene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_farnesene', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_weizen', 'pub_vinyl_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clove', 'pub_vinyl_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_vinyl_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_belgian', 'pub_vinyl_guaiacol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butterfat', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_lager', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chardonnay', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_defect', 'pub_diacetyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sour_cream', 'pub_acetoin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_parmesan', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_aged_hops', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_defect', 'pub_isovaleric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_trans_2_nonenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cucumber', 'pub_trans_2_nonenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_aged_beer', 'pub_trans_2_nonenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_corn', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_lager', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_defect', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cabbage', 'pub_dimethyl_sulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_malt', 'pub_furaneol_malt', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_amber', 'pub_furaneol_malt', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_red', 'pub_furaneol_malt', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel_malt', 'pub_furaneol_malt', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vanilla', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oak', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine_oak', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bourbon', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_aged_spirits', 'pub_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oak', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_scotch_whisky', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bourbon', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_syringaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_oak', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bourbon', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_whiskey_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_scotch_whisky', 'pub_guaiacol_smoke', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mezcal', 'pub_guaiacol_smoke', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_smoked_meat', 'pub_guaiacol_smoke', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_smoked_salmon', 'pub_guaiacol_smoke', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peated_whisky', 'pub_guaiacol_smoke', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_almond', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_amaretto', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bitter_almond', 'pub_benzaldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_brandy', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_isoamyl_alcohol_spirits', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_ethyl_decanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_ethyl_decanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_ethyl_decanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rum', 'pub_ethyl_decanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cognac', 'pub_ethyl_decanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gin', 'pub_alpha_pinene_gin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_juniper', 'pub_alpha_pinene_gin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pine', 'pub_alpha_pinene_gin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rosemary', 'pub_alpha_pinene_gin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gin', 'pub_coriander_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander', 'pub_coriander_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander_seed', 'pub_coriander_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_coriander_linalool', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rice', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_popcorn', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine_rice', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basmati_rice', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wheat_bread', 'pub_acetyl_pyrroline', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cucumber', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fish', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_grass', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wheat_flour', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rancid_fat', 'pub_hexanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vinegar', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kimchi', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sauerkraut', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kefir', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pickles', 'pub_acetic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kefir', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sauerkraut', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kimchi', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_buttermilk', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sour_cream', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pickles', 'pub_lactic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_swiss_cheese', 'pub_propionic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_propionic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_propionic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_emmental', 'pub_propionic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_swiss_cheese', 'pub_propionic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_parmesan', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_romano', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_limburger', 'pub_butyric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_goat_cheese', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blue_cheese', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camembert', 'pub_hexanoic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_methyl_pyrazine_bread', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_toast', 'pub_methyl_pyrazine_bread', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wheat_bread', 'pub_methyl_pyrazine_bread', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rye_bread', 'pub_methyl_pyrazine_bread', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_grain', 'pub_methyl_pyrazine_bread', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_raspberry_ketone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rhubarb', 'pub_raspberry_ketone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blackberry', 'pub_raspberry_ketone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_red_currant', 'pub_raspberry_ketone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_methyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_methyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_methyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_guava', 'pub_methyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_passion_fruit', 'pub_methyl_butyrate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pear', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apricot', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_white_wine', 'pub_hexyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_furaneol_strawberry', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_furaneol_strawberry', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_furaneol_strawberry', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mango', 'pub_furaneol_strawberry', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_furaneol_strawberry', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_mesifurane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_mesifurane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_mesifurane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apricot', 'pub_mesifurane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_banana', 'pub_isoamyl_acetate_banana', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pear', 'pub_isoamyl_acetate_banana', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_isoamyl_acetate_banana', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_weizen', 'pub_isoamyl_acetate_banana', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sake', 'pub_isoamyl_acetate_banana', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grape', 'pub_methyl_anthranilate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_concord_grape', 'pub_methyl_anthranilate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_methyl_anthranilate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_methyl_anthranilate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_neroli', 'pub_methyl_anthranilate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_neroli', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ginger', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tea', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cannabis', 'pub_nerolidol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apricot', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_nectarine', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_gamma_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_yogurt', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apricot', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_delta_decalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apricot', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_gamma_nonalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_raspberry', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_quince', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_plum', 'pub_beta_damascenone_fruit', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_olive', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bell_pepper', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_trans_2_hexenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pepper', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_herb', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_tea', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fresh_herb', 'pub_cis_3_hexenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wintergreen', 'pub_methyl_salicylate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_methyl_salicylate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_methyl_salicylate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blackberry', 'pub_methyl_salicylate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_birch', 'pub_methyl_salicylate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beef', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chicken', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pork', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_broth', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_chicken', 'pub_methyl_furanthiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_beef', 'pub_bis_methyl_furyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beef', 'pub_bis_methyl_furyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beef_broth', 'pub_bis_methyl_furyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_broth', 'pub_bis_methyl_furyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_stew', 'pub_bis_methyl_furyl', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato', 'pub_methional', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beef_broth', 'pub_methional', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_methional', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_canned_food', 'pub_methional', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cooked_cabbage', 'pub_methional', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_garlic', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_onion', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cabbage', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chive', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_leek', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_shallot', 'pub_dimethyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_garlic', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_onion', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cooked_cabbage', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_defect', 'pub_dimethyl_trisulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_garlic', 'pub_allyl_mercaptan', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_onion', 'pub_allyl_mercaptan', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chive', 'pub_allyl_mercaptan', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_leek', 'pub_allyl_mercaptan', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_methane_thiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_defect', 'pub_methane_thiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fermented_cabbage', 'pub_methane_thiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cooked_brassica', 'pub_methane_thiol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_indole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_orange_peel', 'pub_indole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_indole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_meat', 'pub_indole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine_tea', 'pub_indole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato', 'pub_2_isobutyl_thiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tomato_leaf', 'pub_2_isobutyl_thiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fresh_tomato', 'pub_2_isobutyl_thiazole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cucumber', 'pub_nona_2_6_dienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_melon', 'pub_nona_2_6_dienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_violet', 'pub_nona_2_6_dienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_watermelon', 'pub_nona_2_6_dienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fish', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_shrimp', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_anchovy', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fermented_fish', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_crab', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lobster', 'pub_trimethylamine', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_hexanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_grass', 'pub_hexanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_herb', 'pub_hexanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_hexanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_green_pepper', 'pub_hexanol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_heptanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_heptanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fish', 'pub_heptanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_aged_cheese', 'pub_heptanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rancid_fat', 'pub_heptanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_malt', 'pub_pentanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_almond', 'pub_pentanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_olive_oil', 'pub_pentanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_pentanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rancid_fat', 'pub_pentanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cucumber', 'pub_nonenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_melon', 'pub_nonenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_nonenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_violet', 'pub_nonenol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mustard', 'pub_allyl_isothiocyanate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_horseradish', 'pub_allyl_isothiocyanate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wasabi', 'pub_allyl_isothiocyanate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_kimchi', 'pub_allyl_isothiocyanate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mustard_seed', 'pub_allyl_isothiocyanate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_bis_methylthio_methane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_truffle', 'pub_bis_methylthio_methane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_garlic', 'pub_bis_methylthio_methane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mushroom', 'pub_bis_methylthio_methane', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mushroom', 'pub_oct_1_en_3_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_oct_1_en_3_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_oct_1_en_3_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blue_cheese', 'pub_oct_1_en_3_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_earthy_wine', 'pub_oct_1_en_3_ol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_mushroom', 'pub_oct_3_one', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_truffle', 'pub_oct_3_one', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_oct_3_one', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_earthy_wine', 'pub_oct_3_one', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beet', 'pub_geosmin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_carrot', 'pub_geosmin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_earthy_wine', 'pub_geosmin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_drinking_water', 'pub_geosmin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coriander_root', 'pub_geosmin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fried_food', 'pub_trans_2_decenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_trans_2_decenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lard', 'pub_trans_2_decenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fried_chicken', 'pub_trans_2_decenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato_chip', 'pub_trans_2_decenal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sunflower_oil', 'pub_trans_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fried_food', 'pub_trans_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_potato_chip', 'pub_trans_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_corn_oil', 'pub_trans_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sunflower_oil', 'pub_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fried_food', 'pub_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lard', 'pub_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beef_fat', 'pub_2_4_decadienal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vanilla', 'pub_ethyl_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_ethyl_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_ethyl_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ice_cream', 'pub_ethyl_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pastry', 'pub_ethyl_vanillin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_heliotropin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_vanilla', 'pub_heliotropin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_almond', 'pub_heliotropin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_heliotrope', 'pub_heliotropin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_black_currant', 'pub_heliotropin', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_benzyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_benzyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_honey', 'pub_benzyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_benzyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_benzyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_benzyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cherry', 'pub_benzyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_benzyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_benzyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_honey', 'pub_benzyl_alcohol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cinnamon', 'pub_methyl_cinnamate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_strawberry', 'pub_methyl_cinnamate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_basil', 'pub_methyl_cinnamate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cassia', 'pub_methyl_cinnamate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_gamma_butyrolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_gamma_butyrolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_gamma_butyrolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_gamma_butyrolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_gamma_butyrolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_massoia_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_massoia_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_massoia_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut_cream', 'pub_massoia_lactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_delta_octalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_delta_octalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_delta_octalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peach', 'pub_delta_octalactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_malt', 'pub_isovaleraldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_isovaleraldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_isovaleraldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_isovaleraldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_apple', 'pub_isovaleraldehyde', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_malt', 'pub_methylpropanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_whiskey', 'pub_methylpropanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chocolate', 'pub_methylpropanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_methylpropanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_methylpropanal', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_pentanedione', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_pentanedione', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_pentanedione', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_pentanedione', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_pentanedione', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_delta_valerolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_delta_valerolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_milk', 'pub_delta_valerolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_delta_valerolactone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_pineapple', 'pub_methyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine', 'pub_methyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cream', 'pub_methyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_methyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_passion_fruit', 'pub_methyl_hexanoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blue_cheese', 'pub_2_heptanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camembert', 'pub_2_heptanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_gorgonzola', 'pub_2_heptanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hops', 'pub_2_heptanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cloves', 'pub_2_heptanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_blue_cheese', 'pub_2_nonanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_camembert', 'pub_2_nonanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roquefort', 'pub_2_nonanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_2_nonanone', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_goat_cheese', 'pub_capric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_butter', 'pub_capric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut_oil', 'pub_capric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_goat_milk', 'pub_capric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_goat_cheese', 'pub_caprylic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_palm_oil', 'pub_caprylic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer', 'pub_caprylic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_goat_milk', 'pub_caprylic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coconut', 'pub_caprylic_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_valeric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_hop', 'pub_valeric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_valerian', 'pub_valeric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_sourdough', 'pub_valeric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_parmesan', 'pub_valeric_acid', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_wine_brett', 'pub_p_cresol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cheese', 'pub_p_cresol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_beer_brett', 'pub_p_cresol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_farmyard', 'pub_p_cresol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_garlic', 'pub_methyl_propyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_onion', 'pub_methyl_propyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_leek', 'pub_methyl_propyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chive', 'pub_methyl_propyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_shallot', 'pub_methyl_propyl_disulfide', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_furfuryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_caramel', 'pub_furfuryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_furfuryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_furfuryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_soy_sauce', 'pub_soy_sauce_note', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_miso', 'pub_soy_sauce_note', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_worcestershire', 'pub_soy_sauce_note', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fenugreek', 'pub_soy_sauce_note', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_aged_cheese', 'pub_soy_sauce_note', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_coffee', 'pub_pyrrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bread', 'pub_pyrrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cocoa', 'pub_pyrrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_pyrrole', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_overheated_oil', 'pub_acrolein', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_roasted_food', 'pub_acrolein', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_fried_food', 'pub_acrolein', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_chamomile', 'pub_alpha_bisabolol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_cannabis', 'pub_alpha_bisabolol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_amaro', 'pub_alpha_bisabolol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_botanical', 'pub_alpha_bisabolol', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_neroli', 'pub_neryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_bergamot', 'pub_neryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_lavender', 'pub_neryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_petitgrain', 'pub_neryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_clary_sage', 'pub_neryl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_rose', 'pub_citronellyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_citronella', 'pub_citronellyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_geranium', 'pub_citronellyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_citronellyl_acetate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_jasmine', 'pub_benzyl_benzoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_ylangylang', 'pub_benzyl_benzoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_balsam', 'pub_benzyl_benzoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_peru_balsam', 'pub_benzyl_benzoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES ('ahn_tuberose', 'pub_benzyl_benzoate', 'contiene_composto', '{}') ON CONFLICT DO NOTHING;

-- VERIFICA
-- SELECT COUNT(*) FROM nodes WHERE id LIKE 'pub_%';
-- SELECT COUNT(*) FROM nodes WHERE id LIKE 'comp_%'; -- deve essere 0
-- SELECT COUNT(*) FROM edges WHERE relation = 'contiene_composto';