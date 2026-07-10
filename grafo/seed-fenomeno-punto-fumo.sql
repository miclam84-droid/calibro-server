INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-punto-fumo', 'Fenomeno', 'Punto di fumo', 'cucina',
 '{"tipo":"fisico-chimico",
   "target":"Burro: 130-150°C · EVO raffinato: 160-190°C · olio di arachide: 230°C · burro chiarificato: 250°C · strutto: 180°C",
   "strumento":"Termometro a sonda o infrarossi",
   "principio":"Il punto di fumo è la temperatura alla quale un grasso inizia a decomporsi visibilmente (fuma) producendo acroleina e altri composti tossici. Dipende dal contenuto di acidi grassi liberi: più alto è (olio vergine), più basso è il punto di fumo. Il burro fuma presto perché contiene acqua e proteine del latte che bruciano prima del grasso.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-punto-fumo', 'prod-bistecca', 'si_manifesta_in',
 '{"target":"Padella a 200-220°C — usare olio con punto fumo alto (arachide, avocado)","causa":"La rosolatura richiede temperature superiori al punto di fumo di burro e EVO — servono grassi stabili ad alta temperatura"}'),
('fen-punto-fumo', 'prod-frittura', 'si_manifesta_in',
 '{"target":"T frittura ottimale: 170-180°C — olio di arachide (230°C) sicuro · EVO (160-190°C) al limite","causa":"La frittura richiede olio stabile alla T di lavoro: superare il punto di fumo produce sostanze tossiche e sapori bruciati"}'),
('fen-punto-fumo', 'fen-maillard', 'influenza',
 '{"nota":"Il punto di fumo limita la T massima raggiungibile — la Maillard richiede 140°C+ ma il grasso deve reggere quella temperatura senza decomporsi"}');
