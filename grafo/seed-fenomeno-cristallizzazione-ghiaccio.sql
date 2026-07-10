INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-cristallizzazione-ghiaccio', 'Fenomeno', 'Cristallizzazione del ghiaccio', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Cristalli ottimali: <50 micron (cremoso) · Cristalli difetto: >100 micron (sabbioso) · T servizio gelato: -10/-12°C · T abbattimento: -18°C",
   "strumento":"Termometro · abbattitore (termometro integrato)",
   "principio":"Quando un liquido si congela, l acqua forma cristalli di ghiaccio. La dimensione dei cristalli dipende dalla velocità di congelamento: più veloce = cristalli piccoli (cremosi), più lento = cristalli grandi (sabbiosi). Nel gelato l obiettivo è cristalli <50 micron non percepibili dalla lingua. I cicli di scongelamento/congelamento (sbalzi termici) fanno crescere i cristalli.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-cristallizzazione-ghiaccio', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"T estrazione mantecatrice: -6/-8°C · T abbattimento: -18°C rapido","causa":"L abbattimento rapido congela i cristalli mentre sono ancora piccoli. Se il gelato scende lentamente a -18°C i cristalli crescono diventando percepibili"}'),
('fen-cristallizzazione-ghiaccio', 'prod-sour', 'si_manifesta_in',
 '{"target":"Ghiaccio cristallino: congelamento direzionale lento · ghiaccio industriale: veloce","causa":"Il ghiaccio fatto in casa contiene aria e bolle perché si congela rapidamente dall esterno all interno — il ghiaccio professionale si congela lentamente in una sola direzione espellendo le bolle"}'),
('fen-cristallizzazione-ghiaccio', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"Cristalli nel sorbetto più grandi del gelato (meno grassi che li ostacolano)","causa":"I grassi nel gelato interferiscono fisicamente con la crescita dei cristalli di ghiaccio — nel sorbetto questa interferenza manca"}'),
('fen-cristallizzazione-ghiaccio', 'fen-crioscopia', 'influenza',
 '{"nota":"La crioscopia determina A QUALE temperatura inizia la cristallizzazione (punto di congelamento abbassato). Questo fenomeno descrive COME avviene la cristallizzazione e quale dimensione raggiungono i cristalli"}');
