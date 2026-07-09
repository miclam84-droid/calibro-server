-- ============================================================
-- CONTRASTO — dati nutrizionali per abbinamento per contrasto
-- Estende i nodi esistenti (UPDATE su Postgres) con:
--   grassi_pct, zuccheri_pct, sodio_mg100g, amaro_index (0-5)
-- Fonti: USDA FoodData Central (CC0) · valori medi su 100g/100ml
-- Non duplica nodi: solo aggiorna il campo data con jsonb_set
-- Nota SQLite: UPDATE su SQLite usa json_patch, Postgres usa jsonb_set
-- ============================================================

-- ── ACIDI (pH basso, taglio per il grasso) ───────────────────
UPDATE nodes SET data = data || '{"grassi_pct":0.2,"zuccheri_pct":2.5,"sodio_mg100g":2,"amaro_index":1,"profilo_contrasto":"acido"}' WHERE id='prod_limone';
UPDATE nodes SET data = data || '{"grassi_pct":0.2,"zuccheri_pct":1.7,"sodio_mg100g":2,"amaro_index":1,"profilo_contrasto":"acido"}' WHERE id='prod_lime';
UPDATE nodes SET data = data || '{"grassi_pct":0.1,"zuccheri_pct":8.3,"sodio_mg100g":0,"amaro_index":0,"profilo_contrasto":"acido-dolce"}' WHERE id='prod_arancia';
UPDATE nodes SET data = data || '{"grassi_pct":0.1,"zuccheri_pct":2.4,"sodio_mg100g":5,"amaro_index":0,"profilo_contrasto":"acido"}' WHERE id='prod_pomodoro';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":0.1,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"acido-amaro"}' WHERE id='prod_aceto';
UPDATE nodes SET data = data || '{"grassi_pct":0.3,"zuccheri_pct":5.1,"sodio_mg100g":5,"amaro_index":0,"profilo_contrasto":"acido"}' WHERE id='prod_fragola';
UPDATE nodes SET data = data || '{"grassi_pct":0.3,"zuccheri_pct":5.7,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"acido"}' WHERE id='prod_lampone';
UPDATE nodes SET data = data || '{"grassi_pct":0.5,"zuccheri_pct":9.9,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"acido-dolce"}' WHERE id='prod_mirtillo';
UPDATE nodes SET data = data || '{"grassi_pct":0.2,"zuccheri_pct":10.1,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"dolce-acido"}' WHERE id='prod_mela';
UPDATE nodes SET data = data || '{"grassi_pct":0.4,"zuccheri_pct":4.3,"sodio_mg100g":3,"amaro_index":3,"profilo_contrasto":"acido-amaro"}' WHERE id='prod_vino_bianco';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":2.6,"sodio_mg100g":5,"amaro_index":4,"profilo_contrasto":"amaro-acido"}' WHERE id='prod_vino_rosso';

-- ── GRASSI (richiedono acido per essere tagliati) ────────────
UPDATE nodes SET data = data || '{"grassi_pct":81.1,"zuccheri_pct":0.1,"sodio_mg100g":11,"amaro_index":0,"profilo_contrasto":"grasso"}' WHERE id='prod_burro';
UPDATE nodes SET data = data || '{"grassi_pct":36.0,"zuccheri_pct":3.4,"sodio_mg100g":40,"amaro_index":0,"profilo_contrasto":"grasso"}' WHERE id='prod_panna';
UPDATE nodes SET data = data || '{"grassi_pct":3.7,"zuccheri_pct":4.8,"sodio_mg100g":44,"amaro_index":0,"profilo_contrasto":"grasso-dolce"}' WHERE id='prod_latte';
UPDATE nodes SET data = data || '{"grassi_pct":20.0,"zuccheri_pct":0.1,"sodio_mg100g":27,"amaro_index":0,"profilo_contrasto":"grasso"}' WHERE id='prod_salmone';
UPDATE nodes SET data = data || '{"grassi_pct":15.0,"zuccheri_pct":0.0,"sodio_mg100g":55,"amaro_index":0,"profilo_contrasto":"grasso"}' WHERE id='prod_tonno';
UPDATE nodes SET data = data || '{"grassi_pct":9.0,"zuccheri_pct":0.0,"sodio_mg100g":70,"amaro_index":0,"profilo_contrasto":"grasso-proteico"}' WHERE id='prod_manzo';
UPDATE nodes SET data = data || '{"grassi_pct":3.6,"zuccheri_pct":0.0,"sodio_mg100g":65,"amaro_index":0,"profilo_contrasto":"proteico"}' WHERE id='prod_pollo';
UPDATE nodes SET data = data || '{"grassi_pct":9.5,"zuccheri_pct":0.4,"sodio_mg100g":124,"amaro_index":0,"profilo_contrasto":"grasso-proteico"}' WHERE id='prod_uovo_tuorlo';
UPDATE nodes SET data = data || '{"grassi_pct":0.1,"zuccheri_pct":0.7,"sodio_mg100g":166,"amaro_index":0,"profilo_contrasto":"proteico"}' WHERE id='prod_uovo_albume';

-- ── AMARI (richiedono dolce per essere smorzati) ─────────────
UPDATE nodes SET data = data || '{"grassi_pct":43.0,"zuccheri_pct":22.0,"sodio_mg100g":1,"amaro_index":4,"profilo_contrasto":"amaro-grasso"}' WHERE id='prod_cioccolato_fondente';
UPDATE nodes SET data = data || '{"grassi_pct":0.2,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":4,"profilo_contrasto":"amaro"}' WHERE id='prod_caffe_espresso';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":3,"profilo_contrasto":"amaro"}' WHERE id='prod_caffe_filtro';
UPDATE nodes SET data = data || '{"grassi_pct":0.6,"zuccheri_pct":3.8,"sodio_mg100g":4,"amaro_index":3,"profilo_contrasto":"amaro-acido"}' WHERE id='prod_birra';
UPDATE nodes SET data = data || '{"grassi_pct":3.5,"zuccheri_pct":2.0,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"amaro-aromatico"}' WHERE id='prod_porcini';
UPDATE nodes SET data = data || '{"grassi_pct":0.5,"zuccheri_pct":1.0,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"amaro-umami"}' WHERE id='prod_shiitake';

-- ── DOLCI (smorzano amaro e acido) ───────────────────────────
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":82.0,"sodio_mg100g":1,"amaro_index":0,"profilo_contrasto":"dolce"}' WHERE id='prod_zucchero';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":82.0,"sodio_mg100g":4,"amaro_index":0,"profilo_contrasto":"dolce-aromatico"}' WHERE id='prod_miele';
UPDATE nodes SET data = data || '{"grassi_pct":0.1,"zuccheri_pct":3.5,"sodio_mg100g":36,"amaro_index":0,"profilo_contrasto":"dolce-acido"}' WHERE id='prod_yogurt';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":4.8,"sodio_mg100g":0,"amaro_index":0,"profilo_contrasto":"dolce"}' WHERE id='prod_latte';
UPDATE nodes SET data = data || '{"grassi_pct":0.1,"zuccheri_pct":0.0,"sodio_mg100g":5,"amaro_index":1,"profilo_contrasto":"aromatico"}' WHERE id='prod_vaniglia';
UPDATE nodes SET data = data || '{"grassi_pct":1.2,"zuccheri_pct":1.0,"sodio_mg100g":10,"amaro_index":2,"profilo_contrasto":"aromatico-amaro"}' WHERE id='prod_cannella';

-- ── SALATI / UMAMI ────────────────────────────────────────────
UPDATE nodes SET data = data || '{"grassi_pct":1.5,"zuccheri_pct":6.0,"sodio_mg100g":400,"amaro_index":1,"profilo_contrasto":"salato-umami"}' WHERE id='prod_soia';
UPDATE nodes SET data = data || '{"grassi_pct":0.5,"zuccheri_pct":1.0,"sodio_mg100g":9,"amaro_index":3,"profilo_contrasto":"umami-amaro"}' WHERE id='prod_fagiolo';
UPDATE nodes SET data = data || '{"grassi_pct":0.4,"zuccheri_pct":0.4,"sodio_mg100g":8,"amaro_index":2,"profilo_contrasto":"umami"}' WHERE id='prod_farina_frumento';

-- ── ALCOLICI (profilo complesso) ──────────────────────────────
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":1,"amaro_index":1,"profilo_contrasto":"alcolico-speziato","abv_pct":40}' WHERE id='prod_rum';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"alcolico-torbato","abv_pct":40}' WHERE id='prod_whiskey';
UPDATE nodes SET data = data || '{"grassi_pct":0.0,"zuccheri_pct":0.0,"sodio_mg100g":0,"amaro_index":2,"profilo_contrasto":"alcolico-invecchiato","abv_pct":40}' WHERE id='prod_cognac';

-- ── IMPASTI / BASE ────────────────────────────────────────────
UPDATE nodes SET data = data || '{"grassi_pct":1.0,"zuccheri_pct":0.0,"sodio_mg100g":2,"amaro_index":0,"profilo_contrasto":"neutro-base"}' WHERE id='prod_farina_segale';
UPDATE nodes SET data = data || '{"grassi_pct":0.7,"zuccheri_pct":3.2,"sodio_mg100g":10,"amaro_index":3,"profilo_contrasto":"acido-vivo"}' WHERE id='prod_lievito_madre';
