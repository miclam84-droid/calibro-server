-- ============================================================
-- FENOMENO: Gelatinizzazione amido
-- Regola: ✓ — temperatura di gelatinizzazione misurabile
-- Strumento: termometro
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-gelatinizzazione', 'Fenomeno', 'Gelatinizzazione amido', 'trasversale',
 '{"tipo":"fisico-chimico",
   "target":"Frumento 58-64°C · Mais 62-72°C · Patata 58-65°C · Riso 61-78°C · Tapioca 59-70°C",
   "strumento":"termometro",
   "scheda":"I granuli di amido sono strutture cristalline compatte. In presenza di acqua e calore, assorbono acqua, si gonfiano e perdono la struttura cristallina: è la gelatinizzazione. Sopra la temperatura critica (diversa per ogni tipo di amido), il granulo si rompe e rilascia amilosio — le molecole che formano il gel. Questo è il principio delle salse addensate, della crème pâtissière, del roux, del pudding, della polenta e del risotto cremoso. Importanza pratica: la temperatura di gelatinizzazione varia per tipo di amido — la patata gelatinizza prima del mais (58°C vs 62°C), quindi si addensa prima in una salsa. Il raffreddamento dopo la gelatinizzazione causa retrogradazione: le molecole si riassociano e il gel diventa opaco e più rigido (il pane che indurisce, la salsa che si addensa ulteriormente)."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-creme-pasticcera', 'Prodotto', 'Crème pâtissière', 'pasticceria',
 '{"target":"gelatinizzazione amido 82-85°C + coagulazione uovo 82°C","strumento":"termometro"}'),
('prod-salsa-addensata', 'Prodotto', 'Salse addensate con amido', 'cucina',
 '{"target":"amido mais: addensa a 62-72°C · amido patata: 58-65°C","strumento":"termometro"}'),
('prod-polenta', 'Prodotto', 'Polenta', 'cucina',
 '{"target":"gelatinizzazione mais a 62-72°C · cottura 40-50min","strumento":"termometro"}'),
('prod-gnocchi', 'Prodotto', 'Gnocchi di patate', 'cucina',
 '{"target":"gelatinizzazione patata 58-65°C · impasto da caldo","strumento":"termometro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-gelatinizzazione', 'prod-creme-pasticcera', 'si_manifesta_in',
 '{"target":"82-85°C","causa":"L amido gelatinizza e addensa la crema — la temperatura deve essere sufficiente per completare la gelatinizzazione e inattivare l amilasi"}'),
('fen-gelatinizzazione', 'prod-salsa-addensata', 'si_manifesta_in',
 '{"target":"62-72°C secondo il tipo","causa":"Granuli di amido si gonfiano e rilasciano amilosio che forma la rete del gel"}'),
('fen-gelatinizzazione', 'prod-polenta', 'si_manifesta_in',
 '{"target":"62-72°C · cottura prolungata","causa":"I granuli di mais gelatinizzano progressivamente — la cottura lunga completa il processo e sviluppa il sapore"}'),
('fen-gelatinizzazione', 'prod-gnocchi', 'si_manifesta_in',
 '{"target":"58-65°C in cottura","causa":"L amido della patata gelatinizza durante la bollitura, poi forma la struttura degli gnocchi"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-salsa-liquida', 'Errore', 'Salsa che non addensa', 'cucina',
 '{"causa":"Temperatura non raggiunta: amido non gelatinizzato · oppure troppo amido a freddo","soluzione":"Portare sempre sopra la temperatura di gelatinizzazione specifica dell amido usato"}'),
('err-pane-duro', 'Errore', 'Pane / torta che indurisce rapidamente', 'bakery',
 '{"causa":"Retrogradazione dell amido: dopo la cottura le molecole si riassociano e il gel si irrigidisce","soluzione":"Conservare a temperatura ambiente o surgelare — il frigo accelera la retrogradazione"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-gelatinizzazione', 'err-salsa-liquida', 'fallisce_come',
 '{"causa":"Temperatura insufficiente per la gelatinizzazione"}'),
('fen-gelatinizzazione', 'err-pane-duro', 'fallisce_come',
 '{"causa":"Retrogradazione amido post-cottura"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-gelatinizzazione', 'fen-calore', 'influenza',
 '{"nota":"La temperatura è il parametro chiave: sotto la soglia nessuna gelatinizzazione, sopra la gelatinizzazione è irreversibile"}'),
('fen-gelatinizzazione', 'fen-struttura', 'influenza',
 '{"nota":"L amido gelatinizzato forma reti simili al glutine — entrambi contribuiscono alla struttura dei prodotti da forno"}');
