-- ============================================================
-- PONTE ACIDITÀ — primo deliverable testabile.
-- Un fenomeno (Acidità) modellato in profondità su TRE domini.
-- È il mini-gate del grafo: se la risposta cross-dominio ha valore, regge.
-- ============================================================

-- ---- NODO CENTRALE -----------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-acidita', 'Fenomeno', 'Acidità', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"L''acidità è la stessa grandezza fisica in tre mestieri: protoni liberi (pH) e quantità totale di acido (titolabile). Al banco bilancia un sour, in pentola fa rapprendere un gel, al forno fa da orologio alla madre. Una primitiva, tre stanze."}');

-- ---- CALCOLI / PARAMETRI (misurano il fenomeno) ------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-ph',         'Calcolo', 'pH', 'trasversale', '{"nota":"scala logaritmica dei protoni liberi"}'),
('cal-titolabile', 'Calcolo', 'Acidità titolabile %', 'trasversale', '{"nota":"massa di acido per volume — numero operativo del bar"}'),
('cal-brix',       'Calcolo', 'Brix', 'trasversale', '{"nota":"concentrazione zuccheri — entra nel bilanciamento"}');

-- ---- PROCESSI (realizzano il fenomeno) ---------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-ferm-lattica', 'Processo', 'Fermentazione lattica', 'trasversale',
 '{"scheda":"I batteri lattici producono acido nel tempo, abbassando il pH. È il motore dell''acidità nella madre, nella salamoia, nei fermentati."}'),
('proc-aggiunta',     'Processo', 'Aggiunta diretta di acido', 'trasversale',
 '{"scheda":"Acido citrico o succo d''agrume: acidità immediata, non biologica. Il pareggiatore lavora qui."}');

-- ---- PRODOTTI (dove si manifesta — CROSS-DOMINIO) ----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-sour',       'Prodotto', 'Sour cocktail',                'bar',    '{}'),
('prod-pane-madre', 'Prodotto', 'Pane a lievitazione naturale', 'bakery', '{}'),
('prod-confettura', 'Prodotto', 'Confettura',                   'cucina', '{}');

-- ---- TECNICHE (controllano il fenomeno) --------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-pareggiatore',  'Tecnica', 'Pareggiatore di acidità', 'trasversale',
 '{"calcolo":"g acido = vol × (target − attuale)/100"}'),
('tec-lettura-ph',    'Tecnica', 'Lettura pH della madre', 'bakery',
 '{"nota":"misura, non aggiunge: l''acido lo produce il batterio"}');

-- ---- ERRORI (come fallisce in ogni stanza) -----------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-sour-piatto',   'Errore', 'Sour piatto',          'bar',    '{"causa":"acidità titolabile sotto ~1%"}'),
('err-madre-sovra',   'Errore', 'Madre sovra-matura',   'bakery', '{"causa":"pH sotto 3,7: ha già speso la forza"}'),
('err-conf-liquida',  'Errore', 'Confettura liquida',   'cucina', '{"causa":"pH sopra 3,3: la pectina non lega"}');

-- ============================================================
-- ARCHI — tutto parte dal Fenomeno
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- misurato_da
('fen-acidita','cal-ph','misurato_da','{}'),
('fen-acidita','cal-titolabile','misurato_da','{}'),
('fen-acidita','cal-brix','misurato_da','{"nota":"l''acidità si bilancia contro la dolcezza"}'),
-- realizzato_da
('fen-acidita','proc-ferm-lattica','realizzato_da','{}'),
('fen-acidita','proc-aggiunta','realizzato_da','{}'),
-- si_manifesta_in  ← il cross-dominio vive qui
('fen-acidita','prod-sour','si_manifesta_in','{"target":"1,0-1,5% titolabile","ruolo":"bilancia il dolce"}'),
('fen-acidita','prod-pane-madre','si_manifesta_in','{"target":"pH 3,7-3,9","ruolo":"orologio della maturità"}'),
('fen-acidita','prod-confettura','si_manifesta_in','{"target":"pH 3,0-3,3","ruolo":"attiva il gel di pectina"}'),
-- controllato_con
('fen-acidita','tec-pareggiatore','controllato_con','{}'),
('fen-acidita','tec-lettura-ph','controllato_con','{}'),
-- fallisce_come  (il prodotto fallisce quando l'acidità è fuori finestra)
('prod-sour','err-sour-piatto','fallisce_come','{}'),
('prod-pane-madre','err-madre-sovra','fallisce_come','{}'),
('prod-confettura','err-conf-liquida','fallisce_come','{}');
