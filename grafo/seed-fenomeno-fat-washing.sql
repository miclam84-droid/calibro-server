INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fat-washing', 'Fenomeno', 'Fat washing / Infusione lipofila', 'bar',
 '{"tipo":"fisico-chimico",
   "target":"Ratio grasso/distillato: 1:4 – 1:6 (peso) · T contatto: 20-25°C · 1-4h · T solidificazione burro: 4-10°C",
   "strumento":"Termometro · bilancia · freezer",
   "principio":"I composti aromatici liposolubili (che si sciolgono nei grassi ma non nell acqua) si trasferiscono in un grasso fuso, che poi viene mescolato con un distillato. Il grasso si scioglie parzialmente nell alcol trasferendo gli aromi. Poi si congela: il grasso solidifica e si separa dall alcol aromatizzato, che viene filtrato. Tecnica di Dave Arnold.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fat-washing', 'prod-distillati-compositi', 'si_manifesta_in',
 '{"target":"Burro nocciola 50g per 200ml bourbon · contatto 2h a T ambiente · congelare 4h","causa":"Il burro trasferisce i composti aromatici liposolubili (diacetile, composti della noce) al bourbon — composti impossibili da estrarre con infusione in acqua"}'),
('fen-fat-washing', 'prod-bitter-amaro', 'si_manifesta_in',
 '{"target":"Olio di oliva 30ml per 200ml gin · ratio 1:6 · agitare e filtrare a freddo","causa":"L olio arricchisce il gin di composti aromatici dell oliva (fruttato, erbaceo) che ne cambiano completamente la texture e l aroma"}'),
('fen-fat-washing', 'fen-infusione', 'influenza',
 '{"nota":"Il fat washing è un tipo speciale di infusione in cui il solvente è un grasso invece che acqua o alcol — permette di estrarre composti aromatici che i solventi polari non raggiungono"}');
