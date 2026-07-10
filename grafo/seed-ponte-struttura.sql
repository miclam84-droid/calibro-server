-- ============================================================
-- PONTE STRUTTURA / COLLOIDI — quinto fenomeno.
-- Reti che intrappolano: il glutine intrappola gas (pane), la
-- pectina intrappola acqua (gel confettura), gli idrocolloidi
-- sostituiscono il glutine (senza glutine). Stesso principio:
-- una rete molecolare che dà struttura a un fluido.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-struttura', 'Fenomeno', 'Struttura / colloidi', 'trasversale',
 '{"tipo":"fisico-chimico","numero_bersaglio":"misurato via altri numeri — gel pectina: >=60 Brix + pH 3,0-3,3 · glutine: test velo · idrocolloidi 0,2-1%","scheda":"Una rete molecolare che intrappola qualcosa e dà struttura a un fluido. Il glutine intrappola il CO2 nel pane; la pectina intrappola l''acqua nel gel; gli idrocolloidi (xantano, psyllium) fanno da rete dove il glutine manca."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-proteine',  'Calcolo', 'Forza farina (W / % proteine)', 'bakery', '{"nota":"più proteine = glutine più forte"}'),
('cal-windowpane','Calcolo', 'Test windowpane', 'bakery', '{"nota":"impasto trasparente = glutine sviluppato"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-glutine',     'Processo', 'Sviluppo del glutine', 'bakery',
 '{"scheda":"Glutenina (elasticità) + gliadina (estensibilità) + acqua + lavoro meccanico = rete di ponti disolfuro che intrappola il CO2."}'),
('proc-gelificazione','Processo', 'Gelificazione', 'cucina',
 '{"scheda":"La pectina, con abbastanza zucchero e acido, lega le catene in un reticolo che intrappola l''acqua: il gel."}'),
('proc-idrocolloidi','Processo', 'Rete da idrocolloidi', 'bakery',
 '{"scheda":"Senza glutine: xantano, guar, psyllium aumentano la viscosità e tengono in sospensione gas e amido. Struttura da gelatinizzazione + colloidi."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-injera', 'Prodotto', 'Injera / pane senza glutine', 'bakery', '{}');
-- prod-impasto (pane) e prod-confettura (gel) esistono già

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-mollica-fitta', 'Errore', 'Mollica fitta / pane basso', 'bakery', '{"causa":"glutine poco sviluppato o farina debole"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','cal-proteine','misurato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','cal-windowpane','misurato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','proc-glutine','realizzato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','proc-gelificazione','realizzato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','proc-idrocolloidi','realizzato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','prod-impasto','si_manifesta_in','{"target":"glutine sviluppato","ruolo":"rete che intrappola il CO2"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','prod-confettura','si_manifesta_in','{"target":"pectina + 65 Brix + pH 3,0-3,3","ruolo":"rete che intrappola l''acqua"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-struttura','prod-injera','si_manifesta_in','{"target":"amido + idrocolloidi","ruolo":"struttura senza glutine"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

