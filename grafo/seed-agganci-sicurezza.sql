-- ============================================================
-- AGGANCI SICUREZZA → FENOMENI ESISTENTI
-- Archi che collegano i nuovi nodi sicurezza ai fenomeni
-- già nel grafo — rende la sicurezza parte dello stesso grafo,
-- non un modulo separato.
-- ============================================================

-- Acidità → sicurezza (stesso pH, angolazione diversa)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-acidita', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-acidita', 'fen-contaminazione', 'riduce', '{}'),

-- Aw → sicurezza (osmosi come barriera microbiologica)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-aw', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-aw', 'fen-shelf-life', 'determina', '{}'),
('fen-aw', 'fen-atmosfera-modificata', 'interagisce_con', '{}');

-- Calore → sicurezza (stessa fisica, applicazione diversa)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-calore', 'fen-zona-pericolo', 'determina', '{}'),
('fen-calore', 'fen-shelf-life', 'influenza', '{}');

-- Osmosi → sicurezza (sale e zucchero come ostacoli)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-osmosi', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-osmosi', 'fen-shelf-life', 'influenza', '{}');

-- Fermentazione → sicurezza (produce acidi protettivi)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione', 'fen-contaminazione', 'riduce', '{}'),
('fen-fermentazione', 'fen-shelf-life', 'influenza', '{}');

-- Maillard → sicurezza (cottura come CCP)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-maillard', 'fen-zona-pericolo', 'supera', '{}');

-- Concentrazione → sicurezza (salamoia, conserve)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-concentrazione', 'fen-shelf-life', 'influenza', '{}');

-- Prodotti specifici che hanno profilo sicurezza
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-impasto-frigo', 'Prodotto', 'Impasto in frigo', 'sicurezza',
 '{"nota":"shelf life: 24–72h a 4°C (dipende da idratazione, pH, lievito) — il parametro critico è la temperatura, non il tempo"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-fermentato-lacto', 'Prodotto', 'Fermentato lattico (salamoia)', 'sicurezza',
 '{"nota":"sicuro quando pH <4,6 — il pH è l''indicatore principale; Aw e concentrazione sale sono barriere aggiuntive"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-mousse-cruda', 'Prodotto', 'Preparazione con uova crude', 'sicurezza',
 '{"nota":"prodotto ad alto rischio (Salmonella) — shelf life max 24h a 4°C; pastorizzare le uova se shelf life >24h o se servito a categorie vulnerabili"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-zona-pericolo', 'prod-impasto-frigo', 'si_manifesta_in', '{}'),
('fen-shelf-life', 'prod-impasto-frigo', 'si_manifesta_in', '{}'),
('fen-shelf-life', 'prod-fermentato-lacto', 'si_manifesta_in', '{}'),
('fen-contaminazione', 'prod-mousse-cruda', 'si_manifesta_in', '{}'),
('fen-zona-pericolo', 'prod-mousse-cruda', 'si_manifesta_in', '{}');