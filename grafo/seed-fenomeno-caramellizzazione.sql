-- ============================================================
-- FENOMENO: Caramellizzazione (thermal decomposition of sugars)
-- Regola di partizione: OK
-- Numero-bersaglio: soglia di onset per tipo di zucchero (termometro)
--   saccarosio 160-180C · fruttosio 110C · maltosio 180C · lattosio 203C
--   Colore/gusto governati dalla temperatura: 170C ambra chiara, 200C scura/amara.
-- DISTINTA da Maillard: solo zucchero, NIENTE amminoacidi.
-- Strumento: termometro (curva di cottura dello zucchero)
-- Si manifesta in: caramello, creme brulee, croccante, sciroppo bruciato
-- Fonti: FoodCrumbles; American Society of Baking; Cooking Techniques Authority; formul.io.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-caramellizzazione', 'Fenomeno', 'Caramellizzazione', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"onset per zucchero: saccarosio 160-180C · fruttosio 110C · maltosio 180C · lattosio 203C · ambra chiara 170C, scura/amara 200C (solo zucchero, NO amminoacidi)",
   "strumento":"termometro (curva di cottura dello zucchero)",
   "scheda":"La caramellizzazione è la degradazione termica degli zuccheri in assenza di aminoacidi — a differenza della Maillard, non richiede proteine. Il saccarosio inizia a fondersi e decomporre intorno a 160°C; sopra i 170°C compaiono i composti aromatici caratteristici (furanoni, diacetile) e il colore ambrato. Oltre i 190°C si accumulano composti amari. Temperatura e pH sono le variabili di controllo: un ambiente leggermente acido (succo di limone, aceto) abbassa il punto di fusione e impedisce la ricristallizzazione. Il glucosio caramella a temperature inferiori rispetto al saccarosio. La differenza tra un caramello morbido e uno bruciato è una questione di 10-15°C e di pochi secondi."}');

-- prodotti dove si manifesta
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-caramello', 'Prodotto', 'Caramello / salsa mou', 'pasticceria',
 '{"target":"saccarosio a 170-185C · ambra a 170C, scuro a 190-200C · acido o glucosio per non cristallizzare",
   "strumento":"termometro da zucchero"}'),
('prod-creme-brulee', 'Prodotto', 'Creme brulee (crosta)', 'pasticceria',
 '{"target":"crosta caramellata in superficie con cannello/salamandra · zucchero a velo sottile, calore rapido e localizzato",
   "strumento":"cannello / valutazione visiva (ambra)"}'),
('prod-croccante', 'Prodotto', 'Croccante / praline', 'pasticceria',
 '{"target":"caramello secco a 175-190C poi frutta secca · piu scuro = piu amaro-tostato",
   "strumento":"termometro da zucchero"}');

-- archi: Caramellizzazione si_manifesta_in
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-caramellizzazione', 'prod-caramello', 'si_manifesta_in',
 '{"target":"170-185C","causa":"La temperatura sceglie il punto della curva: piu caldo = piu scuro, piu amaro, meno dolce. Sotto i 160C non si sviluppa colore ne aroma"}'),
('fen-caramellizzazione', 'prod-creme-brulee', 'si_manifesta_in',
 '{"target":"caramello di superficie","causa":"Calore rapido e localizzato caramella solo il velo di zucchero in cima senza cuocere la crema sotto: e caramellizzazione senza Maillard"}'),
('fen-caramellizzazione', 'prod-croccante', 'si_manifesta_in',
 '{"target":"175-190C","causa":"Caramello spinto piu scuro per la nota tostata-amara che bilancia la dolcezza della frutta secca"}');

-- errori comuni
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-caramello-bruciato', 'Errore', 'Caramello bruciato / amaro', 'pasticceria',
 '{"causa":"Portato oltre 190-200C: troppa decomposizione, dominano le note amare e i polimeri scuri, la dolcezza crolla","soluzione":"Togliere dal fuoco all ambra desiderata; il caramello continua a cuocere per calore residuo, fermarsi prima"}'),
('err-caramello-cristallizzato', 'Errore', 'Caramello granuloso (cristallizza)', 'pasticceria',
 '{"causa":"Il saccarosio ricristallizza in grani durante la cottura, spesso da un cristallo innescante sulle pareti","soluzione":"Aggiungere un acido (cremor tartaro, succo di limone) o glucosio/zucchero invertito che rompono il reticolo; non mescolare, pennellare le pareti con acqua"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-caramellizzazione', 'err-caramello-bruciato', 'fallisce_come',
 '{"causa":"Soglia superata: decomposizione eccessiva, amaro"}'),
('fen-caramellizzazione', 'err-caramello-cristallizzato', 'fallisce_come',
 '{"causa":"Ricristallizzazione del saccarosio invece di restare fuso"}');

-- connessioni cross-dominio
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-caramellizzazione', 'fen-maillard', 'influenza',
 '{"nota":"Spesso corrono insieme (nel caramello di latte), ma sono distinte: Maillard ha bisogno di proteine e amminoacidi, la caramellizzazione no. Due dorature diverse dallo stesso calore"}'),
('fen-caramellizzazione', 'fen-cristallizzazione', 'influenza',
 '{"nota":"La cristallizzazione e il modo in cui la caramellizzazione fallisce: lo zucchero che dovrebbe restare fuso torna cristallo. Si controlla con acido o zucchero invertito"}'),
('fen-caramellizzazione', 'fen-calore', 'influenza',
 '{"nota":"E una soglia termica come la fusione o la pastorizzazione, ma qui il numero governa la doratura e il gusto, non la sicurezza"}');
