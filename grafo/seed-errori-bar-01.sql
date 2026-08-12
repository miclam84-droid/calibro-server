-- ============================================================
-- ERRORI BAR — batch 01: diluizione, fat-washing, concentrazione
-- Sintomo osservabile al banco → causa fisica. Collegati ai prodotti reali.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
-- DILUIZIONE (nota: err-drink-annacquato esiste già in seed-ponte-calore, non lo riduplico)
('err-drink-forte-caldo', 'Errore', 'Drink troppo forte e poco freddo', 'bar',
  '{"causa":"diluizione insufficiente: ghiaccio troppo grande o tempo troppo breve. Sotto il 20% di diluizione l alcol resta aggressivo e la temperatura non scende abbastanza"}'),
('err-negroni-variabile', 'Errore', 'Negroni diverso ogni volta a parità di ricetta', 'bar',
  '{"causa":"variabile nascosta: quantità e temperatura del ghiaccio non controllate. La stessa ricetta con ghiaccio diverso dà diluizione e freddo diversi"}'),
-- FAT WASHING
('err-fatwash-unto', 'Errore', 'Distillato unto o velato dopo fat washing', 'bar',
  '{"causa":"grasso non rimosso del tutto: mancata fase di congelamento o filtrazione insufficiente. Il grasso residuo resta in sospensione e vela il liquido"}'),
('err-fatwash-poco-aroma', 'Errore', 'Fat washing senza aroma percepibile', 'bar',
  '{"causa":"tempo di infusione troppo breve o rapporto grasso/distillato basso: i composti liposolubili non si sono trasferiti a sufficienza"}'),
-- CONCENTRAZIONE (sciroppi/riduzioni)
('err-sciroppo-cristallizza', 'Errore', 'Sciroppo che cristallizza nel tempo', 'bar',
  '{"causa":"concentrazione di zucchero oltre la solubilità (sopra ~65 Brix a freddo): il saccarosio in eccesso ricristallizza. Serve invertire parte dello zucchero o abbassare la concentrazione"}'),
('err-sciroppo-fermenta', 'Errore', 'Sciroppo che fermenta e fa bollicine', 'bar',
  '{"causa":"concentrazione di zucchero troppo bassa (sotto ~50 Brix): acqua libera sufficiente per lieviti e batteri. Aumentare i Brix o conservare a freddo"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- fenomeno → errore (modello SCAVA). err-drink-annacquato già collegato altrove.
('fen-diluizione','err-drink-forte-caldo','fallisce_come','{"sintomo":"drink aggressivo e poco freddo"}'),
('fen-diluizione','err-negroni-variabile','fallisce_come','{"sintomo":"stesso drink diverso ogni turno"}'),
('fen-fat-washing','err-fatwash-unto','fallisce_come','{"sintomo":"distillato velato/unto"}'),
('fen-fat-washing','err-fatwash-poco-aroma','fallisce_come','{"sintomo":"aroma assente"}'),
('fen-concentrazione','err-sciroppo-cristallizza','fallisce_come','{"sintomo":"cristalli nello sciroppo"}'),
('fen-concentrazione','err-sciroppo-fermenta','fallisce_come','{"sintomo":"bollicine, sciroppo torbido"}');
