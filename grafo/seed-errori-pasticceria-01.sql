-- ============================================================
-- ERRORI PASTICCERIA — batch 01: temperaggio, ganache, souffle, meringa, panna, retrogradazione
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-cioccolato-fiorito', 'Errore', 'Cioccolato con velo bianco (fat bloom)', 'pasticceria',
  '{"causa":"temperaggio fallito o sbalzo termico: il burro di cacao cristallizza in forme instabili e risale in superficie. Servono le curve corrette (fondente 31-32 gradi C finali, forma beta V) e conservazione a temperatura stabile"}'),
('err-cioccolato-non-lucido', 'Errore', 'Cioccolato opaco e senza snap', 'pasticceria',
  '{"causa":"cristalli instabili per mancato temperaggio: senza la forma beta V il cioccolato non contrae, resta molle, non si stacca dallo stampo e non fa lo snap secco"}'),
('err-ganache-impazzita', 'Errore', 'Ganache separata e oleosa', 'pasticceria',
  '{"causa":"emulsione rotta: panna troppo calda o troppo poca, o mescolata male. Il grasso si separa. Emulsionare al centro a piccole aggiunte, temperatura 35-40 gradi C, o correggere con poco liquido caldo"}'),
('err-souffle-sgonfio', 'Errore', 'Souffle che si sgonfia subito', 'pasticceria',
  '{"causa":"schiuma instabile o cottura sbagliata: albumi montati male, forno aperto durante la cottura, o base troppo pesante. La rete proteica non trattiene il vapore. Servire subito"}'),
('err-meringa-granulosa', 'Errore', 'Meringa granulosa e che rilascia sciroppo', 'pasticceria',
  '{"causa":"albumi sovra-montati o zucchero non sciolto: la rete proteica collassa ed espelle liquido (weeping). Aggiungere lo zucchero gradualmente e non superare il picco fermo"}'),
('err-panna-burro', 'Errore', 'Panna montata che diventa burrosa', 'pasticceria',
  '{"causa":"sovra-montatura: la membrana dei globuli di grasso si rompe e il grasso si aggrega. Panna e ciotola devono essere ben fredde (4 gradi C) e fermarsi al picco morbido"}'),
('err-pane-raffermo-veloce', 'Errore', 'Dolce/pane che diventa raffermo in fretta', 'pasticceria',
  '{"causa":"retrogradazione dell amido: le catene di amilosio si riorganizzano ed espellono acqua. Accelerata dal freddo di frigo. Rallentata da zuccheri, grassi e conservazione a temperatura ambiente sigillata"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-temperaggio-cioccolato','err-cioccolato-fiorito','fallisce_come','{"sintomo":"velo bianco in superficie"}'),
('fen-temperaggio-cioccolato','err-cioccolato-non-lucido','fallisce_come','{"sintomo":"opaco, niente snap"}'),
('fen-ganache','err-ganache-impazzita','fallisce_come','{"sintomo":"separata e oleosa"}'),
('fen-souffle','err-souffle-sgonfio','fallisce_come','{"sintomo":"si sgonfia subito"}'),
('fen-meringa','err-meringa-granulosa','fallisce_come','{"sintomo":"granulosa, rilascia sciroppo"}'),
('fen-montatura-panna','err-panna-burro','fallisce_come','{"sintomo":"diventa burrosa"}'),
('fen-retrogradazione','err-pane-raffermo-veloce','fallisce_come','{"sintomo":"raffermo in fretta"}');
