INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-denaturazione', 'Fenomeno', 'Denaturazione proteica', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Miosina (carne): 50°C · albumina uovo: 60-65°C · collagene→gelatina: >55°C prolungato · actina: 65°C (carne secca)",
   "strumento":"Termometro a sonda",
   "principio":"Le proteine sono catene ripiegaste in strutture tridimensionali tenute da legami deboli. Il calore rompe questi legami e la proteina perde la sua forma originale (denatura). È irreversibile. Temperature diverse denaturano proteine diverse — da qui il controllo preciso della cottura.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-denaturazione', 'prod-carne-rosolata', 'si_manifesta_in',
 '{"target":"Miosina 50°C (tenerezza), actina 65°C (durezza)","causa":"La cottura a 55-57°C denatura la miosina (tenerezza) senza raggiungere l actina (durezza) — principio del sous-vide medium-rare"}'),
('fen-denaturazione', 'prod-creme-inglese', 'si_manifesta_in',
 '{"target":"Albume: 60-65°C · tuorlo: 65-70°C","causa":"Le proteine dell uovo denaturano a temperature diverse: si può avere albume coagulato e tuorlo ancora fluido"}'),
('fen-denaturazione', 'prod-creme-inglese', 'si_manifesta_in',
 '{"target":"Crema inglese: 82-84°C (nappe) senza superare 85°C","causa":"Le uova nella crema denaturano gradualmente: sotto 80°C troppo liquida, sopra 85°C si straccia (coagulazione rapida)"}'),
('fen-denaturazione', 'prod-impasto', 'si_manifesta_in',
 '{"target":"Glutine denatura a 70-80°C durante la cottura","causa":"La denaturazione delle proteine del glutine fissa la struttura del pane — senza questo passaggio la mollica collasserebbe"}'),
('fen-denaturazione', 'fen-coagulazione', 'influenza',
 '{"nota":"La denaturazione è il processo molecolare; la coagulazione è il risultato visibile (il liquido diventa solido). Denaturazione precede sempre la coagulazione"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
