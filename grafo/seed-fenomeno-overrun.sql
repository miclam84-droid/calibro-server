INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-overrun', 'Fenomeno', 'Overrun', 'gelateria',
 '{"tipo":"fisico-chimico",
   "target":"Gelato artigianale: 20-35% · Sorbetto: 0-20% · Gelato industriale: 50-100% · Soft serve: 33-45%",
   "strumento":"Bilancia + contenitore calibrato: overrun% = ((vol_finale - vol_iniziale) / vol_iniziale) × 100",
   "principio":"L overrun è la percentuale di aria incorporata nel gelato durante la mantecatura. Più aria = gelato più leggero, meno denso, che fonde più rapidamente. Il gelato artigianale ha meno aria del gelato industriale — si sente nella consistenza più cremosa e densa.",
   "formula":"Overrun% = (peso_mix_stesso_volume - peso_gelato) / peso_gelato × 100",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-overrun', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"20-25% overrun tipico · pesare 1L di gelato: deve essere 800-850g (non 1kg)","causa":"Il gelato con 25% overrun contiene 25% aria per volume: 1L pesa ~800g invece di 1kg — misura pratica dell overrun al banco"}'),
('fen-overrun', 'prod-stracciatella', 'si_manifesta_in',
 '{"target":"20-30% overrun · il cioccolato aggiunto riduce leggermente l overrun","causa":"La stracciatella incorpora meno aria del gelato base per l aggiunta di cioccolato che addensa il mix"}'),
('fen-overrun', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"0-20% overrun · sorbetto classico: 0-10%","causa":"Senza grassi latenti il sorbetto incorpora meno aria: la struttura è più compatta e cristallina — è corretto così"}'),
('fen-overrun', 'fen-cristallizzazione', 'influenza',
 '{"nota":"L aria incorporata (overrun) ostacola la formazione di grandi cristalli di ghiaccio — più overrun = cristalli più piccoli = texture più morbida"}');
