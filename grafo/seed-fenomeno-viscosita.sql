INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-viscosita', 'Fenomeno', 'Viscosità / Reologia', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Acqua: 1 cP · latte intero: 2 cP · olio oliva: 100-200 cP · miele: 2.000-10.000 cP · caramello: 1.000-50.000 cP",
   "strumento":"Test spatola/filo (al banco) · cup Ford · viscosimetro rotazionale (lab)",
   "principio":"La viscosità misura la resistenza di un fluido allo scorrimento. Nel lavoro quotidiano il professionista valuta la viscosità con il test spatola: una salsa nappa (copre e scivola lentamente) ha viscosità diversa da una che cola. La reologia studia come la viscosità cambia con temperatura, agitazione e pH — fondamentale per salse, caramelli, ganache, gelati.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-viscosita', 'prod-salsa-addensata', 'si_manifesta_in',
 '{"target":"Nappe: copre il dorso del cucchiaio e resta attaccata · test dito: lascia traccia netta","causa":"La viscosità della salsa nappe è circa 50-200 cP a 80°C — più bassa a caldo, più alta a freddo: sempre valutare alla T di servizio"}'),
('fen-viscosita', 'prod-ganache', 'si_manifesta_in',
 '{"target":"Ganache spalmabile: 500-2.000 cP a 25°C · colabile: 100-500 cP a 40°C","causa":"La viscosità della ganache dipende dal ratio cioccolato/panna e dalla temperatura — la stessa ganache è liquida a 40°C e spalmabile a 25°C"}'),
('fen-viscosita', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"Mix gelato prima della mantecatura: 50-200 cP a 4°C","causa":"La viscosità del mix prima della mantecatura influenza l incorporazione di aria (overrun) e la dimensione dei cristalli di ghiaccio"}'),
('fen-viscosita', 'prod-sour', 'si_manifesta_in',
 '{"target":"Sciroppo 2:1: ~50 cP a 20°C vs acqua 1 cP · influenza il mouthfeel del cocktail","causa":"La viscosità dello sciroppo aggiunge corpo al cocktail — un drink con sciroppo denso ha mouthfeel diverso da uno con sciroppo 1:1"}'),
('fen-viscosita', 'fen-emulsione', 'influenza',
 '{"nota":"Le emulsioni sono generalmente più viscose dei liquidi che le compongono — la presenza di goccioline disperse aumenta la resistenza allo scorrimento"}');
