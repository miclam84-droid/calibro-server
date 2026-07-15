INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-punto-fumo', 'Fenomeno', 'Punto di fumo', 'cucina',
 '{"tipo":"fisico-chimico",
   "target":"Burro: 130-150°C · EVO raffinato: 160-190°C · olio di arachide: 230°C · burro chiarificato: 250°C · strutto: 180°C",
   "strumento":"Termometro a sonda o infrarossi",
   "principio":"Il punto di fumo è la temperatura alla quale un grasso inizia a decomporsi visibilmente producendo fumo, acroleina e composti tossici. È determinato principalmente dal contenuto di acidi grassi liberi (AGL): più alti sono, più basso è il punto di fumo. L''olio extravergine d''oliva non raffinato ha molti AGL e aromi volatili che bruciano presto; l''olio raffinato ha meno AGL e punto di fumo più alto. Il burro fuma intorno a 130-150°C perché contiene acqua (evapora producendo schiuma) e proteine del latte (bruciano prima del grasso). Il burro chiarificato — privato di acqua e proteine — resiste fino a 250°C. La raffinazione degli oli industriali serve principalmente ad alzare il punto di fumo per la frittura.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-punto-fumo', 'prod-carne-rosolata', 'si_manifesta_in',
 '{"target":"Padella a 200-220°C — usare olio con punto fumo alto (arachide, avocado)","causa":"La rosolatura richiede temperature superiori al punto di fumo di burro e EVO — servono grassi stabili ad alta temperatura"}'),
('fen-punto-fumo', 'prod-carne-rosolata', 'si_manifesta_in',
 '{"target":"T frittura ottimale: 170-180°C — olio di arachide (230°C) sicuro · EVO (160-190°C) al limite","causa":"La frittura richiede olio stabile alla T di lavoro: superare il punto di fumo produce sostanze tossiche e sapori bruciati"}'),
('fen-punto-fumo', 'fen-maillard', 'influenza',
 '{"nota":"Il punto di fumo limita la T massima raggiungibile — la Maillard richiede 140°C+ ma il grasso deve reggere quella temperatura senza decomporsi"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
