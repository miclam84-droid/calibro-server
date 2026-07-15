INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-retrogradazione', 'Fenomeno', 'Retrogradazione dell amido', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Massima velocità a 4-7°C (frigo) · quasi nulla a -18°C o >60°C · pane raffermo in 1-3 giorni a T ambiente",
   "strumento":"Termometro · texture test (tattile o durometro)",
   "principio":"Dopo la gelatinizzazione (cottura), le catene di amilosio e amilopectina, disperse nel gel acquoso, iniziano a riorientarsi e a formare nuovi legami tra di loro, producendo una struttura cristallina più rigida. È la retrogradazione, ed è il processo che fa raffermire il pane e la polenta, e che rende la pasta fredda meno digeribile. La velocità di retrogradazione è massima intorno a 4-7°C — il frigo accelera il raffermimento del pane rispetto al bancone. Al di sotto di -18°C il processo si blocca quasi completamente (congelamento); al di sopra di 60°C le strutture già formate si sciolgono di nuovo (reversibile con il calore). È per questo che il pane riscaldato a 60°C+ recupera parte della morbidezza originale.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-retrogradazione', 'prod-impasto', 'si_manifesta_in',
 '{"target":"Raffermimento in 1-3 giorni a T ambiente · accelerato in frigo (4-7°C = zona critica)","causa":"L amylopectina nel pane retrograda lentamente a T ambiente, rapidamente in frigo — conservare a T ambiente o congelare, mai in frigo"}'),
('fen-retrogradazione', 'prod-impasto', 'si_manifesta_in',
 '{"target":"Riso cotto freddo: amido retrogradato = indice glicemico inferiore","causa":"La retrogradazione trasforma parte dell amido in amido resistente — meno digeribile, indice glicemico più basso"}'),
('fen-retrogradazione', 'prod-creme-inglese', 'si_manifesta_in',
 '{"target":"Crema pasticcera in frigo: si addensa ulteriormente dopo 12-24h","causa":"L amido nella crema retrograda parzialmente in frigo — la consistenza finale si raggiunge dopo il riposo"}'),
('fen-retrogradazione', 'fen-gelatinizzazione', 'influenza',
 '{"nota":"La retrogradazione è il processo inverso alla gelatinizzazione: le catene che si erano espanse durante la cottura si riaggregano lentamente durante il raffreddamento"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
