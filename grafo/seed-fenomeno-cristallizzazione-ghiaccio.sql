INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-cristallizzazione-ghiaccio', 'Fenomeno', 'Cristallizzazione del ghiaccio', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Cristalli ottimali: <50 micron (cremoso) · Cristalli difetto: >100 micron (sabbioso) · T servizio gelato: -10/-12°C · T abbattimento: -18°C",
   "strumento":"Termometro · abbattitore (termometro integrato)",
   "principio":"La dimensione dei cristalli di ghiaccio determina la texture del gelato: cristalli sotto i 50 micron non sono percepibili dalla lingua (cremoso), sopra i 100 micron danno sensazione sabbiosa. La velocità di congelamento è la leva principale: abbattimento rapido produce cristalli piccoli e omogenei, congelamento lento produce cristalli grandi. I cicli di scongelamento e ricongelamento (sbalzi termici nella catena del freddo) fanno crescere i cristalli per ricristallizzazione — è la ragione principale del degrado qualitativo durante lo stoccaggio. Gli stabilizzanti (farina di semi di carruba, guar, xantano) rallentano la ricristallizzazione intrappolando acqua libera.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-cristallizzazione-ghiaccio', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"T estrazione mantecatrice: -6/-8°C · T abbattimento: -18°C rapido","causa":"L abbattimento rapido congela i cristalli mentre sono ancora piccoli. Se il gelato scende lentamente a -18°C i cristalli crescono diventando percepibili"}'),
('fen-cristallizzazione-ghiaccio', 'prod-sour', 'si_manifesta_in',
 '{"target":"Ghiaccio cristallino: congelamento direzionale lento · ghiaccio industriale: veloce","causa":"Il ghiaccio fatto in casa contiene aria e bolle perché si congela rapidamente dall esterno all interno — il ghiaccio professionale si congela lentamente in una sola direzione espellendo le bolle"}'),
('fen-cristallizzazione-ghiaccio', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"Cristalli nel sorbetto più grandi del gelato (meno grassi che li ostacolano)","causa":"I grassi nel gelato interferiscono fisicamente con la crescita dei cristalli di ghiaccio — nel sorbetto questa interferenza manca"}'),
('fen-cristallizzazione-ghiaccio', 'fen-crioscopia', 'influenza',
 '{"nota":"La crioscopia determina A QUALE temperatura inizia la cristallizzazione (punto di congelamento abbassato). Questo fenomeno descrive COME avviene la cristallizzazione e quale dimensione raggiungono i cristalli"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
