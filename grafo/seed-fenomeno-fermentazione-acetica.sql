INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fermentazione-acetica', 'Fenomeno', 'Fermentazione acetica', 'cross',
 '{"tipo":"biologico",
   "target":"Aceto: acido acetico 5-8% · Volatile acidity vino (difetto): >0,6 g/L HAc · Birra: volatile acidity difetto >0,3 g/L",
   "strumento":"Acidità volatile (distillazione) · pH-metro",
   "principio":"Gli acetobatteri (Acetobacter, Gluconobacter) convertono l''etanolo in acido acetico usando l''ossigeno come agente ossidante. È un processo aerobico — richiede ossigeno, a differenza della fermentazione alcolica e lattica. Nella produzione di aceto è il processo voluto; nel vino e nella birra è il principale difetto da contaminazione. L''igiene delle attrezzature e la protezione dall''ossigeno (solfiti nel vino, CO₂ di copertura nella birra) sono le misure preventive standard. La volatile acidity (VA) si misura in g/L di acido acetico; valori elevati producono l''odore pungente di aceto che maschera tutti gli altri aromi del prodotto.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione-acetica', 'prod-fermentato-lacto', 'si_manifesta_in',
 '{"target":"Acido acetico 5-7% nell aceto di vino · metodo Orleans: lento, 3-6 mesi","causa":"L aceto si produce esponendo il vino all aria in presenza di acetobatteri: alcol + ossigeno → acido acetico + acqua"}'),
('fen-fermentazione-acetica', 'prod-vino-rosso', 'si_manifesta_in',
 '{"target":"Volatile acidity difetto: >0,6 g/L · soglia percettiva: 0,4-0,6 g/L","causa":"Se il vino viene contaminato da ossigeno dopo la fermentazione gli acetobatteri trasformano l alcol in acido acetico — difetto irreversibile"}'),
('fen-fermentazione-acetica', 'prod-birra-sour-disc', 'si_manifesta_in',
 '{"target":"Volatile acidity intenzionale nelle Flanders Red/Brown: 0,2-0,8 g/L","causa":"Alcune birre belghe usano la fermentazione acetica controllata per aggiungere complessità acida — ma solo in quantità precise e controllate"}'),
('fen-fermentazione-acetica', 'fen-ossidazione', 'influenza',
 '{"nota":"La fermentazione acetica richiede ossigeno per procedere — è strettamente connessa all ossidazione. Proteggere vino e birra dall aria previene entrambi i difetti"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
