INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-solubilita', 'Fenomeno', 'Solubilità', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Zucchero: 200g/100ml a 20°C · sale: 35,7g/100ml · acido citrico: 73g/100ml · CO2: 1,7g/L a 0°C (Henry)",
   "strumento":"Bilancia · rifrattometro · termometro",
   "principio":"La solubilità è la quantità massima di un soluto che si può sciogliere in un solvente a una data temperatura. Dipende dalla temperatura (di solito aumenta con T per i solidi, diminuisce per i gas), dalla polarità del solvente e del soluto, e dal pH. In F&B: la solubilità governa sciroppi saturi, soluzioni acide, macerati, salamoie.",
   "formula":"Solubilità = g soluto / 100g solvente a T costante",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-solubilita', 'prod-sciroppo', 'si_manifesta_in',
 '{"target":"Sciroppo 2:1 (66°Bx) → satura a T ambiente · a caldo si scioglie di più","causa":"Il saccarosio è più solubile a caldo: si prepara a caldo, ma raffreddando può cristallizzare se supera la saturazione"}'),
('fen-solubilita', 'prod-salamoia', 'si_manifesta_in',
 '{"target":"Sale NaCl: max 35,7g/100ml · salamoia 2-3%","causa":"La solubilità del sale limita la concentrazione massima della salamoia — oltre questo limite non si scioglie più"}'),
('fen-solubilita', 'prod-filtro', 'si_manifesta_in',
 '{"target":"Composti solubili caffè: ~28% del peso in polvere · EY target 18-22%","causa":"Non tutti i composti del caffè sono ugualmente solubili: prima si estraggono gli acidi (sotto-estrazione), poi i dolci, poi i retrogusti amari"}'),
('fen-solubilita', 'fen-carbonatazione', 'influenza',
 '{"nota":"La CO2 è più solubile a bassa temperatura e alta pressione (legge di Henry) — la solubilità dei gas diminuisce con la temperatura, opposto ai solidi"}');
