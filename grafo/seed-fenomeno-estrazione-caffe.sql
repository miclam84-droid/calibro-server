INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-estrazione-caffe', 'Fenomeno', 'Estrazione caffè (TDS / EY)', 'caffetteria',
 '{"tipo":"fisico-chimico",
   "target":"TDS filtro: 1,15-1,55% · TDS espresso: 7-12% · EY: 18-22% · Ratio filtro: 1:15-17 · Ratio espresso: 1:2-3",
   "strumento":"Rifrattometro digitale (VST, Atago) · bilancia di precisione",
   "principio":"L estrazione del caffè è descritta da due variabili indipendenti: TDS (Total Dissolved Solids = concentrazione nella tazza) e EY (Extraction Yield = % di composti estratti dalla polvere). TDS misura il quanto è forte il caffè. EY misura quanto efficacemente hai estratto. Sotto 18% EY: acido, sottosviluppato. Sopra 22%: amaro, astringente.",
   "formula":"EY% = (peso_bevanda × TDS%) / dose_caffè · TDS misurato con rifrattometro",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-estrazione-caffe', 'prod-espresso', 'si_manifesta_in',
 '{"target":"TDS 7-12% · EY 18-22% · ratio 1:2-2,5 (dose:bevanda)","causa":"L espresso è altamente concentrato rispetto al filtro perché usa meno acqua e più pressione: stesso EY target, TDS molto più alto"}'),
('fen-estrazione-caffe', 'prod-caffe-filtro', 'si_manifesta_in',
 '{"target":"TDS 1,15-1,55% (SCA Gold Cup) · EY 18-22% · ratio 1:15-17","causa":"Il caffè filtro usa molta più acqua dell espresso: stessa EY, TDS 10 volte inferiore — è meno forte ma non meno estratto"}'),
('fen-estrazione-caffe', 'prod-cold-brew', 'si_manifesta_in',
 '{"target":"Ratio 1:5-8 (concentrato) o 1:10-15 (ready-to-drink) · EY 15-20% (più basso: T fredda)","causa":"A freddo l estrazione è più lenta e meno completa: si usa più dose e più tempo (12-24h) per raggiungere EY accettabile"}'),
('fen-estrazione-caffe', 'fen-estrazione', 'influenza',
 '{"nota":"L estrazione caffè è un caso specifico dell estrazione generale: gli stessi principi (T, tempo, superficie di contatto, solvente) ma parametri ottimali specifici per il caffè"}');
