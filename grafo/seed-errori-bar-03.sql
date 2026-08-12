-- ============================================================
-- ERRORI BAR — batch 03: solubilità, viscosità, ossidazione
-- Archi fen→errore (modello SCAVA) + sintomo osservabile.
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
-- SOLUBILITA (sciroppi, cordiali)
('err-sciroppo-non-scioglie', 'Errore', 'Zucchero che non si scioglie del tutto', 'bar',
  '{"causa":"limite di solubilita: a freddo il saccarosio si ferma verso i 2:1 (2 parti zucchero 1 acqua). Serve calore o meno zucchero. Con lo sciroppo caldo si arriva piu in alto ma poi ricristallizza raffreddando"}'),
('err-cordiale-torbido', 'Errore', 'Cordiale/liquore torbido dopo il freddo', 'bar',
  '{"causa":"louching: composti aromatici poco solubili in acqua precipitano quando l alcol scende sotto ~20 percento o al freddo. Voluto in alcuni casi (ouzo effect), difetto se cercavi limpidezza"}'),
-- VISCOSITA (texture drink)
('err-drink-slegato-acquoso', 'Errore', 'Drink dal corpo acquoso e slegato', 'bar',
  '{"causa":"viscosita bassa: pochi zuccheri, gomme o agenti di corpo. La texture non trattiene aromi e alcol, il sorso e piatto. Aumentare zucchero o aggiungere un idrocolloide (gomma xantana punta di coltello)"}'),
('err-drink-troppo-denso', 'Errore', 'Drink troppo denso e stucchevole', 'bar',
  '{"causa":"viscosita eccessiva: troppo zucchero o addensante. Il drink risulta pesante e coprente, smorza la beva. Ridurre gli zuccheri o allungare"}'),
-- OSSIDAZIONE (vermouth, agrumi, drink pre-batch)
('err-vermouth-piatto', 'Errore', 'Vermouth/vino aromatizzato piatto e ossidato', 'bar',
  '{"causa":"ossidazione: bottiglia aperta a temperatura ambiente troppo a lungo. Gli aromi volatili si degradano, compaiono note di mela marcia e cartone. Conservare in frigo e consumare entro settimane"}'),
('err-agrume-amaro-ossidato', 'Errore', 'Succo di agrume amaro e slegato dopo qualche ora', 'bar',
  '{"causa":"ossidazione enzimatica e degradazione: il succo spremuto perde freschezza e sviluppa amaro in poche ore. Spremere fresco o gestire con pastorizzazione leggera per il batch"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-solubilita','err-sciroppo-non-scioglie','fallisce_come','{"sintomo":"zucchero sul fondo"}'),
('fen-solubilita','err-cordiale-torbido','fallisce_come','{"sintomo":"liquido torbido a freddo"}'),
('fen-viscosita','err-drink-slegato-acquoso','fallisce_come','{"sintomo":"corpo acquoso, piatto"}'),
('fen-viscosita','err-drink-troppo-denso','fallisce_come','{"sintomo":"denso e stucchevole"}'),
('fen-ossidazione','err-vermouth-piatto','fallisce_come','{"sintomo":"note di mela marcia/cartone"}'),
('fen-ossidazione','err-agrume-amaro-ossidato','fallisce_come','{"sintomo":"succo amaro dopo ore"}');
