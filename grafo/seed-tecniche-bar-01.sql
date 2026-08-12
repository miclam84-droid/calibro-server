-- ============================================================
-- TECNICHE BAR — batch 01: correzioni con effetto sul numero-bersaglio
-- Arco fen→tecnica (relation realizzato_da, modello SCAVA)
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
-- DILUIZIONE
('tec-throwing', 'Tecnica', 'Throwing (travaso dall alto)', 'bar',
  '{"nota":"raffredda e ossigena con diluizione controllata e ripetibile: meno acqua di uno shake lungo, piu di uno stir. Utile per stabilizzare la diluizione target ~20-25 percento"}'),
('tec-ghiaccio-grande', 'Tecnica', 'Ghiaccio grande e asciutto', 'bar',
  '{"nota":"cubo/sfera grande e temprato: minor superficie a contatto = fusione lenta = diluizione controllata. Tiene il drink freddo senza annacquarlo. Fondamentale per gli stirred"}'),
('tec-dilution-calcolata', 'Tecnica', 'Diluizione pre-calcolata (batch)', 'bar',
  '{"nota":"aggiungi acqua misurata (di solito 20-30 percento del volume) al pre-batch per replicare la diluizione dello stir/shake. Rende ogni servizio identico, elimina la variabile ghiaccio"}'),
-- CONCENTRAZIONE / SCIROPPI
('tec-sciroppo-caldo', 'Tecnica', 'Sciroppo a caldo con inversione', 'bar',
  '{"nota":"scaldando si scioglie piu zucchero e una punta di acido inverte parte del saccarosio in gluco+frutto: piu stabile, non ricristallizza. Utile sopra i 60 Brix"}'),
('tec-brix-controllo', 'Tecnica', 'Controllo Brix col rifrattometro', 'bar',
  '{"nota":"misura i gradi Brix dello sciroppo per replicarlo identico e restare nella zona stabile (50-65 Brix): sotto fermenta, sopra cristallizza"}'),
-- FAT WASHING
('tec-fatwash-freddo', 'Tecnica', 'Congelamento e filtrazione del grasso', 'bar',
  '{"nota":"dopo l infusione, congela: il grasso solidifica e si separa. Filtra a freddo con carta/superbag. Rimuove il grasso lasciando solo gli aromi liposolubili, distillato limpido"}'),
-- CARBONATAZIONE
('tec-carbo-freddo', 'Tecnica', 'Carbonatazione a freddo sotto pressione', 'bar',
  '{"nota":"liquido a 2-4 gradi C, pressione CO2 costante, agitazione: la CO2 si scioglie meglio a freddo. Ottieni bollicine fini e persistenti, evita lo spritz piatto"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-diluizione','tec-throwing','realizzato_da','{}'),
('fen-diluizione','tec-ghiaccio-grande','realizzato_da','{}'),
('fen-diluizione','tec-dilution-calcolata','realizzato_da','{}'),
('fen-concentrazione','tec-sciroppo-caldo','realizzato_da','{}'),
('fen-concentrazione','tec-brix-controllo','realizzato_da','{}'),
('fen-fat-washing','tec-fatwash-freddo','realizzato_da','{}'),
('fen-carbonatazione','tec-carbo-freddo','realizzato_da','{}');
