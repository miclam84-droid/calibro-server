INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fermentazione-acetica', 'Fenomeno', 'Fermentazione acetica', 'cross',
 '{"tipo":"biologico",
   "target":"Aceto: acido acetico 5-8% · Volatile acidity vino (difetto): >0,6 g/L HAc · Birra: volatile acidity difetto >0,3 g/L",
   "strumento":"Acidità volatile (distillazione) · pH-metro",
   "principio":"Gli acetobatteri (Acetobacter, Gluconobacter) convertono l alcol in acido acetico in presenza di ossigeno. È il meccanismo di produzione dell aceto (voluto) ma anche del difetto di volatile acidity nel vino e nella birra (non voluto). La fermentazione acetica richiede ossigeno: nei vini protetti dall aria non avviene.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione-acetica', 'prod-aceto-vino', 'si_manifesta_in',
 '{"target":"Acido acetico 5-7% nell aceto di vino · metodo Orleans: lento, 3-6 mesi","causa":"L aceto si produce esponendo il vino all aria in presenza di acetobatteri: alcol + ossigeno → acido acetico + acqua"}'),
('fen-fermentazione-acetica', 'prod-vino-rosso', 'si_manifesta_in',
 '{"target":"Volatile acidity difetto: >0,6 g/L · soglia percettiva: 0,4-0,6 g/L","causa":"Se il vino viene contaminato da ossigeno dopo la fermentazione gli acetobatteri trasformano l alcol in acido acetico — difetto irreversibile"}'),
('fen-fermentazione-acetica', 'prod-birra-sour', 'si_manifesta_in',
 '{"target":"Volatile acidity intenzionale nelle Flanders Red/Brown: 0,2-0,8 g/L","causa":"Alcune birre belghe usano la fermentazione acetica controllata per aggiungere complessità acida — ma solo in quantità precise e controllate"}'),
('fen-fermentazione-acetica', 'fen-ossidazione', 'influenza',
 '{"nota":"La fermentazione acetica richiede ossigeno per procedere — è strettamente connessa all ossidazione. Proteggere vino e birra dall aria previene entrambi i difetti"}');
