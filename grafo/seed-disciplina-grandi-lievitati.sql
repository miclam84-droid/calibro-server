-- ============================================================
-- ARRICCHIMENTO: GRANDI LIEVITATI (panettone)
-- prod-panettone esiste già in seed-ponte-osmosi — solo processi, errori e archi nuovi.
-- 4 fenomeni: Osmosi + Fermentazione + Struttura + Acidità.
-- Numeri: formula Giorilli verificata.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-madre-stiff', 'Processo', 'Lievito madre stiff (pasta madre)', 'bakery',
 '{"tipo":"biologico","scheda":"Madre a 40-45% idratazione (vs 100% della madre normale). La bassa idratazione seleziona i lattici resistenti: producono meno acetico (meno acidità pungente) e più lattico (dolcezza). Deve triplicare in 3-4h a 28-30°C prima dell uso. pH al momento dell uso: 4,0-4,1. Il 90% dei fallimenti del panettone viene dalla madre."}'),
('proc-doppio-impasto', 'Processo', 'Doppio impasto (primo + secondo)', 'bakery',
 '{"tipo":"fisico-chimico","scheda":"Primo impasto: farina + madre + acqua + tuorli + burro (senza aromi). Fermentazione 8-20h a 20-26°C fino a triplicare. Secondo impasto: si aggiungono gli aromi, lo zucchero restante, il burro restante, la frutta. Due impasti perché i grassi indeboliscono il glutine: si sviluppa prima la rete, poi si aggiungono i grassi."}'),
('err-panettone-acido',    'Errore', 'Panettone acido', 'bakery',
 '{"causa":"madre troppo acida (pH sotto 3,8 all uso) o primo impasto fermentato troppo. Fix: accorciare i tempi di rinfresco, controllare il pH."}'),
('err-panettone-collassa', 'Errore', 'Panettone che collassa', 'bakery',
 '{"causa":"glutine non sviluppato (farina debole o impasto insufficiente) o cottura incompleta. Il capovolgimento serve a preservare la struttura mentre raffredda."}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- processi
('prod-panettone','proc-madre-stiff','realizzato_da','{}'),
('prod-panettone','proc-doppio-impasto','realizzato_da','{}'),
-- FERMENTAZIONE: madre stiff = cuore biologico
('fen-fermentazione','prod-panettone','si_manifesta_in',
 '{"target":"madre stiff 40-45% idr, triplica in 3-4h a 28-30°C, pH uso 4,0-4,1","ruolo":"osmosi dello zucchero riduce i LAB: madre stiff seleziona quelli resistenti"}'),
-- STRUTTURA: glutine fortissimo
-- fen-struttura->prod-panettone già in seed-ponte-osmosi
-- ACIDITÀ: pH come orologio (stessa logica della madre normale)
-- fen-acidita->prod-panettone già in seed-ponte-osmosi
-- fallisce_come
('prod-panettone','err-panettone-acido','fallisce_come','{}'),
('prod-panettone','err-panettone-collassa','fallisce_come','{}');
