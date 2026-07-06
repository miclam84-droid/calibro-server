-- ============================================================
-- AGGANCI SICUREZZA → FENOMENI ESISTENTI
-- ============================================================

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-acidita', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-acidita', 'fen-contaminazione', 'riduce', '{}'),
('fen-aw', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-aw', 'fen-atmosfera-modificata', 'interagisce_con', '{}'),
('fen-calore', 'fen-shelf-life', 'influenza', '{}'),
('fen-osmosi', 'fen-zona-pericolo', 'inibisce', '{}'),
('fen-osmosi', 'fen-shelf-life', 'influenza', '{}'),
('fen-fermentazione', 'fen-contaminazione', 'riduce', '{}'),
('fen-fermentazione', 'fen-shelf-life', 'influenza', '{}'),
('fen-maillard', 'fen-zona-pericolo', 'supera', '{}'),
('fen-concentrazione', 'fen-zona-pericolo', 'inibisce', '{}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-impasto-frigo', 'Prodotto', 'Impasto in frigo', 'sicurezza',
 '{"nota":"shelf life orientativa 24-72h a 4C"}'),
('prod-fermentato-lacto', 'Prodotto', 'Fermentato lattico (salamoia)', 'sicurezza',
 '{"nota":"sicuro quando pH sotto 4,6"}'),
('prod-mousse-cruda', 'Prodotto', 'Preparazione con uova crude', 'sicurezza',
 '{"nota":"shelf life max 24h a 4C"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-zona-pericolo', 'prod-impasto-frigo', 'si_manifesta_in', '{}'),
('fen-shelf-life', 'prod-impasto-frigo', 'si_manifesta_in', '{}'),
('fen-shelf-life', 'prod-fermentato-lacto', 'si_manifesta_in', '{}'),
('fen-contaminazione', 'prod-mousse-cruda', 'si_manifesta_in', '{}'),
('fen-zona-pericolo', 'prod-mousse-cruda', 'si_manifesta_in', '{}');
