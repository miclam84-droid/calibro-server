-- ============================================================
-- SICUREZZA — CONTAMINAZIONE CROCIATA
-- Fisicamente: trasferimento di carica batterica da una
-- superficie/alimento a un altro tramite contatto diretto
-- o superfici intermedie.
-- Numero bersaglio: UFC/g (carica batterica nella matrice finale).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-contaminazione', 'Fenomeno', 'Contaminazione crociata', 'sicurezza',
 '{"tipo":"biologico","numero_bersaglio":"0 UFC/g per L. monocytogenes e Salmonella in prodotti RTE · <100 UFC/g E. coli in prodotti cotti","scheda":"La contaminazione crociata è un problema di trasferimento di massa: batteri da una matrice colonizzano un''altra attraverso superfici, mani, utensili o aria. Il percorso fisico è prevedibile e prevenibile. La regola è semplice: tutto ciò che tocca alimenti crudi non tocca alimenti cotti senza sanificazione intermedia. I colori dei taglieri esistono per questo — non è estetica, è separazione fisica dei flussi."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-separazione-flussi', 'Processo', 'Separazione flussi sporco/pulito', 'sicurezza',
 '{"nota":"percorsi fisici separati per materie prime crude (sporco) e prodotti pronti (pulito) — non si incrociano mai nella stessa fase operativa"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-sanificazione', 'Processo', 'Sanificazione superfici e utensili', 'sicurezza',
 '{"nota":"detersione (rimuove lo sporco organico) + disinfezione (riduce la carica batterica) — l''ordine conta: prima detergi, poi disinfetti; il disinfettante su superfici sporche non funziona"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-haccp-ccp', 'Processo', 'Punto critico di controllo (CCP)', 'sicurezza',
 '{"nota":"il momento del processo dove una misura fisica (temperatura, pH, Aw) è l''unico ostacolo tra il rischio e il consumatore — ogni CCP ha un limite critico misurabile, un monitoraggio e un''azione correttiva"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-cross-contamination', 'Errore', 'Contaminazione da utensili non sanificati', 'sicurezza',
 '{"sintomo":"positività microbiologica in prodotto finito nonostante materie prime conformi","causa":"tagliere/coltello/piano lavoro usato per crudo e poi per cotto senza sanificazione intermedia","correzione":"separazione fisica obbligatoria (colori diversi) + sanificazione documentata tra un uso e l''altro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-contaminazione', 'proc-separazione-flussi', 'controllato_con', '{}'),
('fen-contaminazione', 'proc-sanificazione', 'controllato_con', '{}'),
('fen-contaminazione', 'proc-haccp-ccp', 'controllato_con', '{}'),
('fen-contaminazione', 'err-cross-contamination', 'fallisce_come', '{}'),
('fen-zona-pericolo', 'fen-contaminazione', 'amplifica', '{}'),
('fen-contaminazione', 'fen-shelf-life', 'riduce', '{}');