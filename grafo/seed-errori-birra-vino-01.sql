-- ============================================================
-- ERRORI BIRRA + VINO — batch 01
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
-- BIRRA
('err-mash-poco-fermentabile', 'Errore', 'Mosto poco fermentabile, birra dolce e pastosa', 'birra',
  '{"causa":"saccarificazione a temperatura troppo alta (68-72 gradi C): favorisce la beta-amilasi sbagliata e lascia destrine non fermentabili. Per una birra piu secca mashare piu basso (63-65 gradi C)"}'),
('err-birra-poco-amara', 'Errore', 'Birra poco amara nonostante il luppolo', 'birra',
  '{"causa":"isomerizzazione insufficiente: bolliture troppo brevi o luppolo aggiunto tardi. Gli alfa-acidi non si isomerizzano in iso-alfa-acidi solubili. Per amaro servono 60 minuti di bollitura"}'),
('err-birra-ossidata', 'Errore', 'Birra con note di cartone (ossidazione)', 'birra',
  '{"causa":"ossigeno introdotto dopo la fermentazione (hot side o in imbottigliamento): reazioni di stanling che danno il tipico cartone/carta bagnata. Minimizzare lo splash, purgare con CO2"}'),
-- VINO
('err-vino-spunto', 'Errore', 'Vino con odore di aceto (spunto)', 'vino',
  '{"causa":"acidita volatile alta: batteri acetici in presenza di ossigeno trasformano l etanolo in acido acetico. Colmare le botti, gestire la SO2, limitare il contatto con l aria"}'),
('err-vino-ridotto', 'Errore', 'Vino con odore di uovo/ridotto', 'vino',
  '{"causa":"riduzione: carenza di ossigeno e azoto in fermentazione, il lievito produce composti solforati (acido solfidrico). Arieggiare/travasare, in prevenzione nutrire il lievito"}'),
('err-vino-ossidato', 'Errore', 'Vino ossidato, colore bruno e frutta cotta', 'vino',
  '{"causa":"eccesso di ossigeno e SO2 insufficiente: i polifenoli si ossidano, il bianco imbrunisce e perde freschezza. Gestire i travasi, adeguare la solforosa libera"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-mash-enzimi','err-mash-poco-fermentabile','fallisce_come','{"sintomo":"birra dolce, pastosa"}'),
('fen-isomerizzazione-luppolo','err-birra-poco-amara','fallisce_come','{"sintomo":"poco amara"}'),
('fen-ossidazione','err-birra-ossidata','fallisce_come','{"sintomo":"note di cartone"}'),
('fen-acidita-volatile','err-vino-spunto','fallisce_come','{"sintomo":"odore di aceto"}'),
('fen-fermentazione','err-vino-ridotto','fallisce_come','{"sintomo":"odore di uovo"}'),
('fen-ossidazione','err-vino-ossidato','fallisce_come','{"sintomo":"colore bruno, frutta cotta"}');
