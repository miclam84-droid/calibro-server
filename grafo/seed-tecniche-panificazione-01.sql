-- ============================================================
-- TECNICHE PANIFICAZIONE — batch 01
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-autolisi-riposo', 'Tecnica', 'Autolisi (riposo farina-acqua)', 'panificazione',
  '{"nota":"mescola farina e acqua e lascia riposare 30-60 min prima di sale e lievito: il glutine si sviluppa da solo, l impasto diventa estensibile senza impastare a lungo. Meno strappi"}'),
('tec-pieghe-forza', 'Tecnica', 'Pieghe di rinforzo (stretch and fold)', 'panificazione',
  '{"nota":"serie di pieghe durante la puntata: allineano e rinforzano la maglia glutinica soprattutto su impasti idratati. Danno forza senza impastatrice"}'),
('tec-controllo-lievitazione', 'Tecnica', 'Controllo lievitazione a temperatura', 'panificazione',
  '{"nota":"gestisci tempo e temperatura per centrare il punto: prova del dito (torna lenta = pronta). Retard in frigo 4 gradi C per rallentare e sviluppare aroma. Evita sovra/sotto-lievitazione"}'),
('tec-vapore-forno', 'Tecnica', 'Vapore in avvio cottura', 'panificazione',
  '{"nota":"vapore nei primi minuti: ritarda la formazione della crosta permettendo l oven spring, poi crosta lucida e croccante via Maillard. Senza vapore la crosta e pallida e spessa"}'),
('tec-sale-dosaggio', 'Tecnica', 'Dosaggio del sale (2-2,2 percento)', 'panificazione',
  '{"nota":"2-2,2 g di sale per 100 g di farina: regola la fermentazione, rinforza il glutine e da sapore. Aggiungilo dopo l autolisi per non rallentare l idratazione"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-maglia-glutinica','tec-autolisi-riposo','realizzato_da','{}'),
('fen-maglia-glutinica','tec-pieghe-forza','realizzato_da','{}'),
('fen-lievitazione','tec-controllo-lievitazione','realizzato_da','{}'),
('fen-crosta','tec-vapore-forno','realizzato_da','{}'),
('fen-sale-impasto','tec-sale-dosaggio','realizzato_da','{}');
