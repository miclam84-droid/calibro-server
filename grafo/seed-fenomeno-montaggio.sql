-- ============================================================
-- FENOMENO: Montaggio / Overrun (incorporazione d'aria)
-- Regola di partizione: OK
-- Numero-bersaglio: overrun % (aria incorporata, misurabile per pesata/densita)
--   overrun% = (peso_mix - peso_montato) / peso_montato x 100
--   gelato 20-35% · panna montata ~100% · meringa/souffle anche >300%
-- Strumento: bilancia (densita) / rapporto di volume
-- Si manifesta in: panna montata, meringa, mousse, semifreddo, gelato
-- Ponte pasticceria<->gelateria: stessa fisica, due stanze del freddo e del dolce.
-- Fonti: KnowledgeNuts/Underbelly (overrun gelato 20-35%); scienza della meringa.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-montaggio', 'Fenomeno', 'Montaggio / Overrun', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"overrun — gelato 20-35% · panna montata ~80-120% · meringa/souffle >300%",
   "strumento":"pesata/densita: overrun% = (peso_mix - peso_montato)/peso_montato x100",
   "scheda":"Montare vuol dire intrappolare aria in un liquido finche diventa una schiuma stabile. Serve un agente che faccia da parete alle bolle: le proteine (albume, latte) o i grassi (panna). L overrun misura quanta aria e entrata: si pesa lo stesso volume prima e dopo. Poca aria da un prodotto denso e pieno (il gelato artigianale, 20-35%), molta aria da leggerezza (panna ~100%, meringa e souffle oltre il 300%). C e una soglia in entrambi i sensi: sotto non monta, sopra collassa o si rompe (la panna che diventa burro, l albume slegato). E lo stesso numero che separa il gelato artigianale denso dall industriale gonfio d aria, e la meringa ferma dalla schiuma che cade."}');

-- prodotti dove si manifesta
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-panna-montata', 'Prodotto', 'Panna montata', 'pasticceria',
 '{"target":"overrun ~80-120% · panna 30-38% grassi · montata a 2-4C (fredda monta, calda no)",
   "strumento":"bilancia / valutazione"}'),
('prod-meringa', 'Prodotto', 'Meringa', 'pasticceria',
 '{"target":"overrun >300% · zucchero 1,5-2x il peso dell albume · picchi fermi e lucidi",
   "strumento":"planetaria + valutazione (picco)"}'),
('prod-semifreddo', 'Prodotto', 'Semifreddo', 'gelateria',
 '{"target":"overrun alto (meringa/panna montate) · niente mantecazione · PAC/zuccheri per non ghiacciare duro",
   "strumento":"bilancia + calcolo PAC", "principio":"Il montaggio incorpora aria in un liquido grasso creando una schiuma stabile. Nella panna, i globuli di grasso si aggregano attorno alle bolle d''aria formando una rete che le intrappola. Temperatura critica: la panna deve essere fredda (2-4°C) perché i cristalli di grasso parzialmente solidificati forniscono la struttura rigida necessaria a stabilizzare la schiuma. Panna a temperatura ambiente non monta perché i globuli di grasso, completamente liquidi, non si aggregano. Zucchero e aromi si aggiungono a fine montaggio per non interferire con la struttura. Montatura eccessiva fa separare il grasso in burro — la struttura collassa irreversibilmente."}')
ON CONFLICT (id) DO NOTHING;

-- archi: Montaggio si_manifesta_in
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-montaggio', 'prod-panna-montata', 'si_manifesta_in',
 '{"target":"overrun ~100%","causa":"I globuli di grasso parzialmente cristallizzati (freddi) intrappolano l aria: se la panna e calda i grassi sono liquidi e non reggono le bolle"}'),
('fen-montaggio', 'prod-meringa', 'si_manifesta_in',
 '{"target":"overrun >300%","causa":"Le proteine dell albume si dispiegano all interfaccia aria-acqua e stabilizzano una schiuma enorme; lo zucchero la rende ferma e lucida"}'),
('fen-montaggio', 'prod-semifreddo', 'si_manifesta_in',
 '{"target":"overrun da meringa/panna","causa":"Il semifreddo non si manteca: la cremosita a freddo viene tutta dall aria montata a monte, non dal churning"}');

-- errori comuni
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-meringa-collassata', 'Errore', 'Meringa che non monta / collassa', 'pasticceria',
 '{"causa":"Grassi che contaminano l albume (tuorlo, ciotola unta) o zucchero aggiunto troppo presto: le proteine non fanno rete e la schiuma cade","soluzione":"Ciotola sgrassata, albumi senza tracce di tuorlo, zucchero a pioggia quando la schiuma e gia spumosa"}'),
('err-panna-burro', 'Errore', 'Panna smontata (diventa burro)', 'pasticceria',
 '{"causa":"Sovra-montaggio: i globuli di grasso si aggregano oltre la schiuma e coalescono in burro e siero","soluzione":"Fermarsi ai picchi morbidi-fermi; montare fredda e non oltre"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-montaggio', 'err-meringa-collassata', 'fallisce_come',
 '{"causa":"Rete proteica impedita: niente schiuma stabile"}'),
('fen-montaggio', 'err-panna-burro', 'fallisce_come',
 '{"causa":"Overrun spinto oltre la soglia: la schiuma si rompe in grasso"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

-- connessioni cross-dominio
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-montaggio', 'fen-struttura', 'influenza',
 '{"nota":"L aria resta solo se una rete la trattiene (proteine, grassi cristallizzati): stesso principio del glutine che trattiene la CO2, applicato alla schiuma"}'),
('fen-montaggio', 'fen-crioscopia', 'influenza',
 '{"nota":"Nel semifreddo l aria montata sostituisce la mantecazione del gelato: due strade diverse per la stessa cremosita a freddo"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
