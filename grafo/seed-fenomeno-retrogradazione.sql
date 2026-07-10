INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-retrogradazione', 'Fenomeno', 'Retrogradazione dell amido', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Massima velocità a 4-7°C (frigo) · quasi nulla a -18°C o >60°C · pane raffermo in 1-3 giorni a T ambiente",
   "strumento":"Termometro · texture test (tattile o durometro)",
   "principio":"Dopo la gelatinizzazione (cottura), le catene di amido si riarrangiano lentamente formando una struttura cristallina più rigida. È il processo che fa raffermire il pane. La retrogradazione è accelerata dal freddo (il frigo rende il pane raffermo più velocemente del bancone). Si rallenta al di sotto di -18°C (congelamento) o al di sopra di 60°C (riscaldamento).",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-retrogradazione', 'prod-pane-lievitazione', 'si_manifesta_in',
 '{"target":"Raffermimento in 1-3 giorni a T ambiente · accelerato in frigo (4-7°C = zona critica)","causa":"L amylopectina nel pane retrograda lentamente a T ambiente, rapidamente in frigo — conservare a T ambiente o congelare, mai in frigo"}'),
('fen-retrogradazione', 'prod-riso-pasta', 'si_manifesta_in',
 '{"target":"Riso cotto freddo: amido retrogradato = indice glicemico inferiore","causa":"La retrogradazione trasforma parte dell amido in amido resistente — meno digeribile, indice glicemico più basso"}'),
('fen-retrogradazione', 'prod-creme-pasticceria', 'si_manifesta_in',
 '{"target":"Crema pasticcera in frigo: si addensa ulteriormente dopo 12-24h","causa":"L amido nella crema retrograda parzialmente in frigo — la consistenza finale si raggiunge dopo il riposo"}'),
('fen-retrogradazione', 'fen-gelatinizzazione', 'influenza',
 '{"nota":"La retrogradazione è il processo inverso alla gelatinizzazione: le catene che si erano espanse durante la cottura si riaggregano lentamente durante il raffreddamento"}');
