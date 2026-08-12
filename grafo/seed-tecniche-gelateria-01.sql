-- ============================================================
-- TECNICHE GELATERIA — batch 01 (bilanciamento zuccheri, PAC, struttura)
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-bilanciamento-pac', 'Tecnica', 'Bilanciamento del PAC con mix di zuccheri', 'gelateria',
  '{"nota":"non usare un solo zucchero: combina saccarosio (POD 100/PAC 100), destrosio (POD 70/PAC 190) e sciroppo di glucosio (DE variabile) per centrare il PAC 260-320 e la giusta scoopabilita. Ogni zucchero cambia dolcezza E durezza"}'),
('tec-solidi-totali', 'Tecnica', 'Controllo dei solidi totali', 'gelateria',
  '{"nota":"tieni i solidi totali a 380-420 g/kg: abbastanza per limitare l acqua libera che cristallizza. Piu solidi = cristalli piu piccoli = struttura cremosa"}'),
('tec-mantecazione-rapida', 'Tecnica', 'Mantecazione rapida e catena del freddo', 'gelateria',
  '{"nota":"manteca in fretta e abbatti: il congelamento veloce forma cristalli piccoli. Evita gli sbalzi termici in conservazione che li fanno ricristallizzare grossi (freezer burn)"}'),
('tec-stabilizzanti-dosaggio', 'Tecnica', 'Dosaggio di stabilizzanti/emulsionanti', 'gelateria',
  '{"nota":"stabilizzanti (farina di semi di carrube, guar) a 2-5 g/kg legano l acqua libera e migliorano la struttura e la resistenza allo scioglimento. Non eccedere o diventa gommoso"}'),
('tec-sorbetto-frutta', 'Tecnica', 'Bilanciamento sorbetto senza grassi', 'gelateria',
  '{"nota":"senza grassi la struttura dipende da zuccheri, fibre della frutta e solidi: calcola il PAC e i solidi (280-320 PAC, ~300-340 solidi) perche l acqua non spurghi"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-pac-gelateria','tec-bilanciamento-pac','realizzato_da','{}'),
('fen-cristallizzazione-ghiaccio','tec-solidi-totali','realizzato_da','{}'),
('fen-cristallizzazione-ghiaccio','tec-mantecazione-rapida','realizzato_da','{}'),
('fen-bilanciamento-gelato','tec-stabilizzanti-dosaggio','realizzato_da','{}'),
('fen-bilanciamento-gelato','tec-sorbetto-frutta','realizzato_da','{}');
