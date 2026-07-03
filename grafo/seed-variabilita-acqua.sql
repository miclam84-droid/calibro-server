-- ============================================================
-- G8: Variabilità acqua — durezza, cloro, pH
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('var-acqua', 'Processo', 'Variabilità acqua (durezza, cloro, pH)', 'trasversale',
 '{"scheda":"L acqua del rubinetto non è costante: varia per città, stagione, impianto. Tre parametri critici per F&B: (1) Durezza (ppm CaCO3): sopra 150-200ppm il calcio e il magnesio inibiscono i lieviti e la fermentazione lattica. Acqua troppo morbida (<50ppm) non dà struttura al glutine. Zona ideale per pane: 50-150ppm. (2) Cloro residuo: inibisce i lieviti e i batteri lattici — basta 0,1mg/L per rallentare la fermentazione. Soluzione: acqua filtrata o lasciata riposare 30 minuti in contenitore aperto. (3) pH acqua: influenza il pH finale dell impasto. Acqua alcalina (pH 7,5-8) rallenta la fermentazione acida. Acqua acida (pH 6-6,5) favorisce i batteri lattici.","target":"Durezza 50-150ppm · Cloro <0,05mg/L per lievitazione · pH 6,5-7,5","strumento":"kit test durezza · pHmetro · kit cloro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('var-acqua', 'fen-fermentazione', 'influenza',
 '{"nota":"Durezza alta e cloro residuo inibiscono lieviti e batteri lattici — la fermentazione rallenta o si blocca"}'),
('var-acqua', 'fen-struttura', 'influenza',
 '{"nota":"La durezza dell acqua influenza la formazione del glutine: acqua troppo morbida o troppo dura cambia la texture dell impasto"}'),
('var-acqua', 'fen-estrazione', 'influenza',
 '{"nota":"La durezza dell acqua influenza l estrazione del caffè: acqua troppo morbida = piatta, troppo dura = precipita composti e ostruisce la macchina"}');
