-- ============================================================
-- PONTE CONCENTRAZIONE — secondo fenomeno.
-- Una primitiva (soluto/solvente) che lega QUATTRO stanze:
-- bar (sciroppo + caffè), cucina (salamoia), bakery (baker's %).
-- Stesso modello del ponte acidità. Si aggiunge al grafo esistente.
-- ============================================================

-- ---- NODO CENTRALE -----------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-concentrazione', 'Fenomeno', 'Concentrazione', 'trasversale',
 '{"tipo":"fisico-chimico","numero_bersaglio":"% soluto/solvente — sour ~16% ABV / ~12 Brix · salamoia 2-3% · idratazione pane 60-85% · EY caffe 18-22%","scheda":"Quanto soluto c''è in un solvente. È la stessa operazione ovunque: sale sull''acqua della salamoia, zucchero nello sciroppo, acqua sulla farina (baker''s %), caffè estratto nell''acqua (TDS). Cambia il soluto, non la matematica."}');

-- ---- CALCOLI / PARAMETRI (misurano il fenomeno) ------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-bakerpct', 'Calcolo', 'Baker''s %', 'bakery', '{"nota":"ingrediente come % della farina (=100%)"}'),
('cal-salepct',  'Calcolo', 'Sale %', 'cucina', '{"nota":"sale come % del peso totale"}'),
('cal-tds',      'Calcolo', 'TDS / Extraction yield %', 'bar', '{"nota":"solidi disciolti e resa di estrazione del caffè"}');
-- cal-brix esiste già dal ponte acidità: lo riusiamo (concentrazione zuccheri)

-- ---- PROCESSI (realizzano il fenomeno) ---------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-dissoluzione', 'Processo', 'Dissoluzione di un soluto', 'trasversale',
 '{"scheda":"Sciogliere sale, zucchero o estrarre solubili: portare massa dentro un liquido fino a una concentrazione voluta."}'),
('proc-evaporazione', 'Processo', 'Evaporazione / concentrazione', 'trasversale',
 '{"scheda":"Togliere acqua per alzare la concentrazione: la confettura che cuoce fino a 65 Brix."}');

-- ---- PRODOTTI (dove si manifesta — CROSS-DOMINIO) ----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-sciroppo',  'Prodotto', 'Sciroppo', 'bar',    '{}'),
('prod-caffe',     'Prodotto', 'Caffè estratto', 'bar', '{}'),
('prod-salamoia',  'Prodotto', 'Salamoia / fermentato', 'cucina', '{}'),
('prod-impasto',   'Prodotto', 'Impasto del pane', 'bakery', '{}');
-- prod-confettura esiste già: la concentrazione la tocca (Brix del gel)

-- ---- ERRORI ------------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-impasto-molle', 'Errore', 'Impasto troppo molle', 'bakery', '{"causa":"idratazione troppo alta per la forza della farina"}'),
('err-caffe-acido',   'Errore', 'Caffè acido/sottoestratto', 'bar', '{"causa":"extraction yield sotto 18%"}'),
('err-ferm-molle',    'Errore', 'Fermentato molle/muffe', 'cucina', '{"causa":"sale sotto il 2%"}');

-- ============================================================
-- ARCHI — tutto parte da Concentrazione
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','cal-bakerpct','misurato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','cal-salepct','misurato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','cal-tds','misurato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','cal-brix','misurato_da','{"nota":"il Brix è concentrazione di zucchero"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','proc-dissoluzione','realizzato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','proc-evaporazione','realizzato_da','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','prod-sciroppo','si_manifesta_in','{"target":"50 Brix (1:1) o 65 (2:1)","ruolo":"dolcezza dosabile"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','prod-caffe','si_manifesta_in','{"target":"EY 18-22% / TDS 1,15-1,55%","ruolo":"forza ed estrazione"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','prod-salamoia','si_manifesta_in','{"target":"2-3% sale","ruolo":"selezione dei microbi"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','prod-impasto','si_manifesta_in','{"target":"60-85% idratazione","ruolo":"struttura della mollica"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-concentrazione','prod-confettura','si_manifesta_in','{"target":"65 Brix","ruolo":"set del gel"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('prod-impasto','err-impasto-molle','fallisce_come','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('prod-caffe','err-caffe-acido','fallisce_come','{}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

