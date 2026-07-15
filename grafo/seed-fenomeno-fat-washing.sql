INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fat-washing', 'Fenomeno', 'Fat washing / Infusione lipofila', 'bar',
 '{"tipo":"fisico-chimico",
   "target":"Ratio grasso/distillato: 1:4 – 1:6 (peso) · T contatto: 20-25°C · 1-4h · T solidificazione burro: 4-10°C",
   "strumento":"Termometro · bilancia · freezer",
   "principio":"I composti aromatici liposolubili non si trasferiscono in soluzioni acquose, ma si sciolgono nell''alcol ad alta gradazione. Il fat washing sfrutta questo principio: un grasso aromatico (burro nocciola, olio di sesamo, pancetta) viene fuso e mescolato con un distillato; a contatto con l''alcol cede i propri composti aromatici liposolubili. Si abbatte in frigo: il grasso solidifica e si separa, l''alcol resta aromatizzato e limpido. Il distillato risultante porta aromi impossibili da ottenere per infusione in acqua. È una tecnica di Dave Arnold che ha ridefinito le possibilità del bar moderno. La qualità del grasso determina tutto: grasso di qualità superiore produce distillato di qualità superiore.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fat-washing', 'prod-gin', 'si_manifesta_in',
 '{"target":"Burro nocciola 50g per 200ml bourbon · contatto 2h a T ambiente · congelare 4h","causa":"Il burro trasferisce i composti aromatici liposolubili (diacetile, composti della noce) al bourbon — composti impossibili da estrarre con infusione in acqua"}'),
('fen-fat-washing', 'prod-bitter', 'si_manifesta_in',
 '{"target":"Olio di oliva 30ml per 200ml gin · ratio 1:6 · agitare e filtrare a freddo","causa":"L olio arricchisce il gin di composti aromatici dell oliva (fruttato, erbaceo) che ne cambiano completamente la texture e l aroma"}'),
('fen-fat-washing', 'fen-infusione', 'influenza',
 '{"nota":"Il fat washing è un tipo speciale di infusione in cui il solvente è un grasso invece che acqua o alcol — permette di estrarre composti aromatici che i solventi polari non raggiungono"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
