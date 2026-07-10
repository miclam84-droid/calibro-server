-- ============================================================
-- PONTE OSMOSI — quarto fenomeno.
-- La pressione osmotica: l'acqua si sposta verso dove c'è più soluto.
-- Lega sale (salamoia) e zucchero (panettone, confettura) che
-- stressano i microbi tirando loro l'acqua. Stessa fisica, soluti diversi.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-osmosi', 'Fenomeno', 'Osmosi', 'trasversale',
 '{"tipo":"fisico-chimico","numero_bersaglio":"sale 2-3% (fermentazione lattica sicura) · zucchero: stress osmotico sui lieviti (grandi lievitati)","scheda":"L''acqua attraversa le membrane verso la zona più concentrata di soluto. Sale o zucchero in abbastanza quantità tirano l''acqua FUORI dai microbi e li stressano: è la base della conservazione e della selezione dei fermenti."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-pressione-osm', 'Calcolo', 'Pressione osmotica (% soluto)', 'trasversale', '{"nota":"cresce con la concentrazione del soluto disciolto"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-disidratazione', 'Processo', 'Disidratazione osmotica', 'trasversale',
 '{"scheda":"Soluto fuori, acqua fuori dalle cellule: il sale asciuga i microbi nella salamoia, lo zucchero stressa i lieviti nel panettone."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-panettone', 'Prodotto', 'Panettone / grandi lievitati', 'bakery', '{}');
-- prod-salamoia e prod-confettura esistono già: l'osmosi li tocca entrambi

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-panettone-fermo', 'Errore', 'Panettone che non cresce', 'bakery', '{"causa":"lievito stressato dallo zucchero: serve lievito madre fortissimo"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-osmosi','cal-pressione-osm','misurato_da','{}'),
('fen-osmosi','cal-salepct','misurato_da','{"nota":"la % di sale determina la pressione osmotica"}'),
('fen-osmosi','proc-disidratazione','realizzato_da','{}'),
('fen-osmosi','prod-salamoia','si_manifesta_in','{"target":"2-3% sale","ruolo":"asciuga i patogeni, salva i lattici"}'),
('fen-osmosi','prod-confettura','si_manifesta_in','{"target":"65 Brix","ruolo":"lo zucchero blocca i microbi: conserva"}'),
('fen-osmosi','prod-panettone','si_manifesta_in','{"target":"LM stiff 40-45%","ruolo":"zucchero stressa il lievito: serve madre forte"}'),
('prod-panettone','err-panettone-fermo','fallisce_come','{}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
