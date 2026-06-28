-- ============================================================
-- PONTE CONCENTRAZIONE — secondo fenomeno.
-- Una primitiva (soluto/solvente) che lega QUATTRO stanze:
-- bar (sciroppo + caffè), cucina (salamoia), bakery (baker's %).
-- Stesso modello del ponte acidità. Si aggiunge al grafo esistente.
-- ============================================================

-- ---- NODO CENTRALE -----------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-concentrazione', 'Fenomeno', 'Concentrazione', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"Quanto soluto c''è in un solvente. È la stessa operazione ovunque: sale sull''acqua della salamoia, zucchero nello sciroppo, acqua sulla farina (baker''s %), caffè estratto nell''acqua (TDS). Cambia il soluto, non la matematica."}');

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
-- misurato_da (incluso cal-brix che già esiste)
('fen-concentrazione','cal-bakerpct','misurato_da','{}'),
('fen-concentrazione','cal-salepct','misurato_da','{}'),
('fen-concentrazione','cal-tds','misurato_da','{}'),
('fen-concentrazione','cal-brix','misurato_da','{"nota":"il Brix è concentrazione di zucchero"}'),
-- realizzato_da
('fen-concentrazione','proc-dissoluzione','realizzato_da','{}'),
('fen-concentrazione','proc-evaporazione','realizzato_da','{}'),
-- si_manifesta_in  ← quattro stanze
('fen-concentrazione','prod-sciroppo','si_manifesta_in','{"target":"50 Brix (1:1) o 65 (2:1)","ruolo":"dolcezza dosabile"}'),
('fen-concentrazione','prod-caffe','si_manifesta_in','{"target":"EY 18-22% / TDS 1,15-1,55%","ruolo":"forza ed estrazione"}'),
('fen-concentrazione','prod-salamoia','si_manifesta_in','{"target":"2-3% sale","ruolo":"selezione dei microbi"}'),
('fen-concentrazione','prod-impasto','si_manifesta_in','{"target":"60-85% idratazione","ruolo":"struttura della mollica"}'),
('fen-concentrazione','prod-confettura','si_manifesta_in','{"target":"65 Brix","ruolo":"set del gel"}'),
-- fallisce_come
('prod-impasto','err-impasto-molle','fallisce_come','{}'),
('prod-caffe','err-caffe-acido','fallisce_come','{}'),
('prod-salamoia','err-ferm-molle','fallisce_come','{}');
