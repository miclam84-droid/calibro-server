INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-autolisi', 'Fenomeno', 'Autolisi', 'cross',
 '{"tipo":"biologico",
   "target":"Impasto: 20-60 min a 18-22°C prima dell aggiunta di sale e lievito · Sur lies vino: 6-36 mesi a contatto con i lieviti morti",
   "strumento":"Timer · test windowpane (impasto) · analisi sensoriale (vino)",
   "principio":"Autolisi significa letteralmente auto-digestione. Nell impasto: le proteine e gli enzimi della farina iniziano a idrolizzarsi spontaneamente non appena vengono idratati, sviluppando il glutine senza lavorazione meccanica e producendo composti aromatici. Nel vino: i lieviti morti (dopo la fermentazione) si lisano rilasciando aminoacidi, polisaccaridi e composti che arricchiscono la struttura del vino.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-autolisi', 'prod-pane-lievitazione', 'si_manifesta_in',
 '{"target":"30-60 min riposo farina+acqua prima di aggiungere lievito e sale","causa":"L autolisi pre-idrata il glutine e attiva gli enzimi della farina: l impasto risultante richiede meno lavorazione meccanica ed è più estensibile"}'),
('fen-autolisi', 'prod-baguette', 'si_manifesta_in',
 '{"target":"20-40 min di autolisi tipici della baguette tradizionale","causa":"La baguette sfrutta l autolisi per sviluppare il glutine senza impastamento intensivo — contribuisce alla struttura alveolata"}'),
('fen-autolisi', 'prod-spumante', 'si_manifesta_in',
 '{"target":"Metodo classico: 15+ mesi sur lies · Champagne millesimato: 36+ mesi","causa":"I lieviti morti a contatto con il vino si lisano rilasciando polisaccaridi (corpo e cremosità) e aminoacidi (complessità aromatica)"}'),
('fen-autolisi', 'fen-idrolisi', 'influenza',
 '{"nota":"L autolisi è un caso specifico di idrolisi enzimatica — gli enzimi presenti nella cellula stessa (o nella farina) idrolizzano i propri componenti"}');
