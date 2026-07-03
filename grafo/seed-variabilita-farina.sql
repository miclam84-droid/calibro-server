-- ============================================================
-- G7: Variabilità farina — il W che cambia tra lotti
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('var-farina-w', 'Processo', 'Variabilità farina (W e proteine)', 'bakery',
 '{"scheda":"Il W (forza della farina) non è fisso: cambia tra lotti dello stesso prodotto, tra stagioni, tra annate di grano. Una farina 00 da pizza può avere W 180-280 a seconda del lotto. Le proteine variano dal 10% al 14% anche nella stessa referenza. Effetti pratici: lo stesso impasto con la stessa ricetta può avere comportamenti molto diversi. Segni di farina debole (W basso): impasto appiccicoso, scarsa tenuta in lievitazione, pane piatto. Segni di farina forte (W alto): impasto rigido, lievitazione lenta, croste dure. Come compensare: idratazione (abbassa W effettivo), autolisi (rilassa il glutine), temperatura di fermentazione.","target":"W 150-220 farina debole · W 220-300 farina media · W 300-380 farina forte · W 380+ rinforzo","strumento":"analisi del laboratorio (alveografo Chopin) — in pratica: comportamento dell impasto al tatto"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('var-farina-w', 'fen-struttura', 'realizzato_da',
 '{"nota":"Il W misura la forza della rete glutinica — direttamente collegato al fenomeno Struttura"}'),
('var-farina-w', 'fen-fermentazione', 'influenza',
 '{"nota":"Farina più forte regge tempi di fermentazione più lunghi senza collassare"}');
