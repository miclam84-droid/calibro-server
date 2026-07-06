-- ============================================================
-- PONTE CALORE / CINETICA — terzo fenomeno.
-- La fisica del calore lega tre stanze con la stessa legge:
--  • diluizione del ghiaccio (calore latente di fusione)
--  • lievitazione (Q10: velocità raddoppia ogni ~8°C)
--  • pastorizzazione sous-vide (tempo × temperatura)
--  • sfoglia (acqua del burro → vapore: calore latente al contrario)
-- Tre stanze, una legge: la temperatura governa tempo e stato.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-calore', 'Fenomeno', 'Calore / cinetica termica', 'trasversale',
 '{"tipo":"fisico-chimico","numero_bersaglio":"calore latente fusione ghiaccio 334 J/g · Q10: tempo x2 ogni ~8-10°C","scheda":"La temperatura governa due cose: la VELOCITÀ delle reazioni (raddoppia ogni ~8-10°C, è il Q10) e i CAMBI DI STATO (sciogliere, vaporizzare, che costano calore latente). È la stessa fisica sotto il ghiaccio che si scioglie, l''impasto che lievita e la carne che pastorizza."}');

-- ---- CALCOLI / PARAMETRI -----------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-q10',          'Calcolo', 'Q10 / tempo-temperatura', 'trasversale', '{"nota":"t = t_base × 2^((Tref−T)/8)"}'),
('cal-calorelatente','Calcolo', 'Calore latente', 'trasversale', '{"nota":"334 J/g per fondere il ghiaccio; energia nascosta nel cambio di stato"}'),
('cal-pastorizz',    'Calcolo', 'Pastorizzazione (tempo×temp)', 'cucina', '{"nota":"60°C/30min = 71°C istantaneo, riduzione logaritmica"}');

-- ---- PROCESSI ----------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-fusione',     'Processo', 'Fusione del ghiaccio', 'bar', '{"scheda":"Il ghiaccio per sciogliersi assorbe calore dal drink: raffredda e diluisce insieme."}'),
('proc-vaporizz',    'Processo', 'Vaporizzazione', 'bakery', '{"scheda":"L''acqua del burro in forno diventa vapore e gonfia gli strati della sfoglia: calore latente al contrario."}'),
('proc-denaturazione','Processo', 'Denaturazione proteica', 'cucina', '{"scheda":"Le proteine cambiano stato in sequenza al salire della temperatura: miosina ~50°C, collagene>55°C, actina ~65°C."}');
-- proc-ferm-lattica esiste già (acidità): la temperatura ne governa la velocità → la colleghiamo

-- ---- PRODOTTI (dove si manifesta) --------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-drink-freddo','Prodotto', 'Drink shakerato/mescolato', 'bar', '{}'),
('prod-sousvide',    'Prodotto', 'Carne a bassa temperatura', 'cucina', '{}'),
('prod-sfoglia',     'Prodotto', 'Croissant / sfoglia', 'bakery', '{}');
-- prod-pane-madre e prod-impasto esistono già: la lievitazione è governata dalla temperatura

-- ---- ERRORI ------------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-drink-annacquato','Errore', 'Drink annacquato', 'bar', '{"causa":"troppo ghiaccio/tempo: diluizione oltre il 30%"}'),
('err-carne-secca',     'Errore', 'Carne secca/fibrosa', 'cucina', '{"causa":"sopra 65°C l''actina denatura e spreme l''acqua"}'),
('err-sfoglia-piatta',  'Errore', 'Sfoglia che non sfoglia', 'bakery', '{"causa":"burro fuso (sopra 18°C): niente strati, niente vapore"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- misurato_da
('fen-calore','cal-q10','misurato_da','{}'),
('fen-calore','cal-calorelatente','misurato_da','{}'),
('fen-calore','cal-pastorizz','misurato_da','{}'),
-- realizzato_da
('fen-calore','proc-fusione','realizzato_da','{}'),
('fen-calore','proc-vaporizz','realizzato_da','{}'),
('fen-calore','proc-denaturazione','realizzato_da','{}'),
('fen-calore','proc-ferm-lattica','realizzato_da','{"nota":"la temperatura governa la velocità della fermentazione (Q10)"}'),
-- si_manifesta_in
('fen-calore','prod-drink-freddo','si_manifesta_in','{"target":"22-27% diluizione","ruolo":"raffredda e diluisce insieme"}'),
('fen-calore','prod-sousvide','si_manifesta_in','{"target":"55-65°C","ruolo":"denatura senza seccare"}'),
('fen-calore','prod-sfoglia','si_manifesta_in','{"target":"burro 13-18°C","ruolo":"vapore che gonfia gli strati"}'),
('fen-calore','prod-pane-madre','si_manifesta_in','{"target":"Q10: raddoppia ogni 8°C","ruolo":"governa il tempo di lievitazione"}'),
('fen-calore','prod-impasto','si_manifesta_in','{"target":"DDT 24-26°C","ruolo":"temperatura impasto = velocità"}'),
-- fallisce_come
('prod-drink-freddo','err-drink-annacquato','fallisce_come','{}'),
('prod-sousvide','err-carne-secca','fallisce_come','{}'),
('prod-sfoglia','err-sfoglia-piatta','fallisce_come','{}');
