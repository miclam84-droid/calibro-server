-- PRESSIONE
-- Caffè (9 bar espresso), bar (carbonatazione), bakery (vapore in forno)
-- Strumento: manometro · pressostato

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-pressione', 'Fenomeno', 'Pressione', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Espresso: 9 bar · spumante: 5-6 bar · carbonatazione forzata birra: 1,5-3 bar a 0-4°C",
   "strumento":"Manometro · pressostato macchina espresso · manometro keg",
   "principio":"La pressione modifica due parametri critici in F&B: la solubilità dei gas (legge di Henry — più pressione = più gas disciolto) e il punto di ebollizione dei liquidi (più pressione = ebollizione a temperatura più alta). L''estrazione espresso a 9 bar è possibile solo sotto pressione: a pressione atmosferica l''acqua a 93°C non supererebbe la resistenza del panetto di caffè compresso. La pentola a pressione cuoce a 120°C invece di 100°C perché la pressione sopra 1 bar innalza il punto di ebollizione dell''acqua. Il mantecatore del gelato lavora a pressione ridotta per incorporare più aria. La carbonatazione forzata della birra (spunding valve) è un''applicazione diretta della legge di Henry.",
   "formula":"Legge di Henry: C = kH × P · Punto ebollizione: aumenta con P (pentola a pressione)",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-pressione', 'prod-espresso', 'si_manifesta_in',
 '{"target":"9 bar durante l estrazione (±0,5 bar)","causa":"La pressione forzata attraverso il cake di caffè estrae composti (oli, acidi, zuccheri) che non si estraggono con acqua a bassa pressione — inclusa la crema"}'),
('fen-pressione', 'prod-spumante', 'si_manifesta_in',
 '{"target":"5-6 bar CO2 nella bottiglia","causa":"La seconda fermentazione in bottiglia (metodo classico) o la gasatura forzata (Charmat) creano la pressione che tiene la CO2 disciolta — rilasciata all apertura"}'),
('fen-pressione', 'prod-birra-lager', 'si_manifesta_in',
 '{"target":"1,5-2,5 bar di carbonatazione · servita a 2-6 bar dalla spine","causa":"La carbonatazione forzata in keg segue la legge di Henry: più pressione + meno temperatura = più CO2 disciolta"}'),
('fen-pressione', 'prod-impasto', 'si_manifesta_in',
 '{"target":"Vapore nel forno: pressione parziale H2O alta nei primi 15 min","causa":"Il vapore nei primi minuti di cottura mantiene la crosta elastica permettendo la massima espansione prima che si solidifichi"}'),
('fen-pressione', 'fen-carbonatazione', 'influenza',
 '{"nota":"La pressione è la variabile principale della carbonatazione: la CO2 si scioglie proporzionalmente alla pressione applicata (legge di Henry)"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
