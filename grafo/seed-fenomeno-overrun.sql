INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-overrun', 'Fenomeno', 'Overrun', 'gelateria',
 '{"tipo":"fisico-chimico",
   "target":"Gelato artigianale: 20-35% · Sorbetto: 0-20% · Gelato industriale: 50-100% · Soft serve: 33-45%",
   "strumento":"Bilancia + contenitore calibrato: overrun% = ((vol_finale - vol_iniziale) / vol_iniziale) × 100",
   "principio":"L''overrun è la percentuale di aria incorporata nel gelato durante la mantecatura, calcolata come (volume finale - volume iniziale) / volume iniziale × 100. Un gelato con 30% overrun ha il 30% del suo volume finale costituito da aria. Più aria significa gelato più leggero, meno denso, che fonde più rapidamente e pesa meno per volume. Il gelato artigianale a basso overrun (20-35%) ha consistenza più densa e cremosa, fonde più lentamente, ha sapore più intenso per grammo. Il gelato industriale ad alto overrun (50-100%) è economicamente più conveniente perché si vende volume, non peso. Il sorbetto ha overrun quasi nullo perché l''acqua (priva di grassi) non trattiene l''aria efficacemente.",
   "formula":"Overrun% = (peso_mix_stesso_volume - peso_gelato) / peso_gelato × 100",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-overrun', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"20-25% overrun tipico · pesare 1L di gelato: deve essere 800-850g (non 1kg)","causa":"Il gelato con 25% overrun contiene 25% aria per volume: 1L pesa ~800g invece di 1kg — misura pratica dell overrun al banco"}'),
('fen-overrun', 'prod-stracciatella', 'si_manifesta_in',
 '{"target":"20-30% overrun · il cioccolato aggiunto riduce leggermente l overrun","causa":"La stracciatella incorpora meno aria del gelato base per l aggiunta di cioccolato che addensa il mix"}'),
('fen-overrun', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"0-20% overrun · sorbetto classico: 0-10%","causa":"Senza grassi latenti il sorbetto incorpora meno aria: la struttura è più compatta e cristallina — è corretto così"}'),
('fen-overrun', 'fen-cristallizzazione', 'influenza',
 '{"nota":"L aria incorporata (overrun) ostacola la formazione di grandi cristalli di ghiaccio — più overrun = cristalli più piccoli = texture più morbida"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
