INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-autolisi', 'Fenomeno', 'Autolisi', 'cross',
 '{"tipo":"biologico",
   "target":"Impasto: 20-60 min a 18-22C prima dell aggiunta di sale e lievito · Sur lies vino: 6-36 mesi",
   "strumento":"Timer · test windowpane (impasto) · analisi sensoriale (vino)",
   "principio":"L''autolisi è l''idrolisi spontanea delle proteine e degli amidi della farina ad opera dei propri enzimi, non appena vengono idratati. Non serve lavorazione meccanica: bastano farina, acqua e tempo. Il risultato è una rete glutinica già parzialmente sviluppata prima ancora di impastare, con meno sforzo meccanico necessario e una struttura finale più estensibile. Per il panettiere è uno strumento per migliorare la lavorabilità degli impasti ad alta idratazione. Nel vino sur lies, i lieviti esauriti si lisano cedendo al liquido polisaccaridi e aminoacidi che aggiungono rotondità e complessità strutturale — è la tecnica base dello Champagne e dei grandi bianchi borgognoni.",
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
