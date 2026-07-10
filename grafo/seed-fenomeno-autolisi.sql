INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-autolisi', 'Fenomeno', 'Autolisi', 'cross',
 '{"tipo":"biologico",
   "target":"Impasto: 20-60 min a 18-22C prima dell aggiunta di sale e lievito · Sur lies vino: 6-36 mesi",
   "strumento":"Timer · test windowpane (impasto) · analisi sensoriale (vino)",
   "principio":"Autolisi significa auto-digestione. Nell impasto: le proteine e gli enzimi della farina iniziano a idrolizzarsi spontaneamente non appena vengono idratati, sviluppando il glutine senza lavorazione meccanica. Nel vino: i lieviti morti si lisano rilasciando aminoacidi e polisaccaridi che arricchiscono la struttura.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-autolisi', 'prod-impasto', 'si_manifesta_in',
 '{"target":"30-60 min riposo farina+acqua prima di lievito e sale","causa":"L autolisi pre-idrata il glutine e attiva gli enzimi della farina — l impasto risultante richiede meno lavorazione meccanica ed e piu estensibile"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-autolisi', 'prod-baguette', 'si_manifesta_in',
 '{"target":"20-40 min di autolisi tipici della baguette tradizionale","causa":"La baguette sfrutta l autolisi per sviluppare il glutine senza impastamento intensivo — struttura alveolata caratteristica"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-autolisi', 'prod-spumante', 'si_manifesta_in',
 '{"target":"Metodo classico: 15+ mesi sur lies · Champagne millesimato: 36+ mesi","causa":"I lieviti morti si lisano rilasciando polisaccaridi (corpo e cremosita) e aminoacidi (complessita aromatica)"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-autolisi', 'fen-amilolisi', 'influenza',
 '{"nota":"L autolisi e un caso specifico di idrolisi enzimatica — gli enzimi presenti nella cellula o nella farina idrolizzano i propri componenti"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
