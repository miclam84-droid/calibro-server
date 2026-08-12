-- ============================================================
-- ERRORI BAR — batch 02: carbonatazione, estrazione, crioscopia
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
-- CARBONATAZIONE
('err-spritz-piatto', 'Errore', 'Spritz/soda piatto, poche bollicine', 'bar',
  '{"causa":"CO2 insufficiente o persa: liquido troppo caldo in fase di carbonatazione (la CO2 si scioglie meglio a freddo, ~2-4°C), o pressione troppo bassa, o agitazione che ha fatto sfiatare il gas"}'),
('err-spritz-schiuma', 'Errore', 'Eccesso di schiuma che trabocca al servizio', 'bar',
  '{"causa":"sovra-carbonatazione o servizio troppo veloce su liquido caldo: la CO2 esce tutta insieme (nucleazione). Versare lento su bicchiere freddo e inclinato"}'),
-- ESTRAZIONE (bitter/infusi/cold brew)
('err-bitter-amaro-slegato', 'Errore', 'Bitter/infuso troppo amaro e slegato', 'bar',
  '{"causa":"sovra-estrazione: tempo di macerazione troppo lungo o gradazione alcolica troppo alta che estrae anche i tannini e gli amari duri. Ridurre tempo o diluire l alcol"}'),
('err-infuso-debole', 'Errore', 'Infuso alcolico debole e senza aroma', 'bar',
  '{"causa":"sotto-estrazione: tempo troppo breve, botanica poco superficie (interi invece che rotti), o temperatura troppo bassa. Gli aromi liposolubili non si sono trasferiti"}'),
-- CRIOSCOPIA (semifreddi/ghiaccio al bar)
('err-semifreddo-duro', 'Errore', 'Semifreddo/granita troppo duro da servire', 'bar',
  '{"causa":"pochi soluti anticongelanti (zucchero/alcol): senza abbassamento crioscopico l acqua congela compatta. Aumentare zucchero o aggiungere una punta di alcol per tenerlo morbido"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-carbonatazione','err-spritz-piatto','fallisce_come','{"sintomo":"poche bollicine, piatto"}'),
('fen-carbonatazione','err-spritz-schiuma','fallisce_come','{"sintomo":"schiuma che trabocca"}'),
('fen-estrazione','err-bitter-amaro-slegato','fallisce_come','{"sintomo":"amaro duro e slegato"}'),
('fen-estrazione','err-infuso-debole','fallisce_come','{"sintomo":"aroma debole"}'),
('fen-crioscopia','err-semifreddo-duro','fallisce_come','{"sintomo":"troppo duro da servire"}');
