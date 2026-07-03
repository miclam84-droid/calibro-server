-- ============================================================
-- G9: Coagulazione proteica trasversale nel grafo
-- Archi espliciti che collegano il nuovo fenomeno Coagulazione
-- ai fenomeni esistenti e ai prodotti già presenti
-- ============================================================

-- yogurt: collegamento tra coagulazione e fermentazione
-- (già esiste prod-yogurt nel grafo fermentazione)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'prod-yogurt', 'si_manifesta_in',
 '{"target":"45°C fermentazione · 85°C pastorizzazione preventiva",
   "causa":"La caseina del latte denatura a 85°C durante la pastorizzazione, poi i batteri lattici abbassano il pH e causano la coagulazione a freddo (isoelettrica a pH 4.6)"}')
ON CONFLICT DO NOTHING;

-- connessione coagulazione → struttura (glutine che coagula in cottura)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'fen-struttura', 'influenza',
 '{"nota":"Il glutine coagula in cottura sopra 60°C: le proteine del grano si aggregano e fissano la struttura del pane. Stesso principio della coagulazione proteica, applicato alla bakery"}')
ON CONFLICT DO NOTHING;

-- connessione coagulazione → acidità (pH isoelettrico caseina)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'fen-acidita', 'influenza',
 '{"nota":"La caseina coagula al suo punto isoelettrico (pH 4.6): abbassare il pH con acidi o fermentazione causa la coagulazione. Principio del formaggio fresco e dello yogurt"}')
ON CONFLICT DO NOTHING;
