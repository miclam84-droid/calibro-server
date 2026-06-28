-- ============================================================
-- FENOMENO FERMENTAZIONE — l'unico nodo di tipo BIOLOGICO.
-- Rompe lo schema fisico-chimico: non e una legge che agisce, e un ORGANISMO
-- (lieviti, batteri) che mangia e produce. Il numero (pH, tempo, temperatura)
-- ne misura l'EFFETTO, non la causa. La causa e viva.
-- Numeri: pH (orologio), temperatura (cinetica biologica non-lineare), % acido.
-- Strumento: pHmetro, termometro, acidita titolabile (CONDIVISI con Acidita e Calore).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fermentazione', 'Fenomeno', 'Fermentazione', 'trasversale',
 '{"tipo":"biologico","scheda":"Un organismo vivo - lieviti, batteri lattici - mangia zuccheri e produce acidi, alcol, CO2, aromi. Non e una legge fisica: e biologia. Il pH che scende e l''orologio (i batteri lattici acidificano: ottimo a pH 5-5,5, lavorano fino a 3,6); la temperatura governa la velocita in modo non-lineare (lactobacilli ottimali a 32-33°C, fermi sotto 4°C e sopra 41°C). Il numero misura l''EFFETTO dell''organismo, mai la causa. Per questo e l''unico fenomeno di tipo biologico: dietro non c''e una legge, c''e qualcosa di vivo.","numero_bersaglio":"pH 3,4-4,2 (effetto); 32-33°C ottimo lattici; acido 1,5-2,5%"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-quoziente-ferm', 'Calcolo', 'Quoziente di fermentazione', 'trasversale',
 '{"tipo":"biologico","nota":"rapporto acido lattico/acetico nella madre; insieme a pH e tempo dice a che punto e la fermentazione"}');

-- proc-ferm-lattica esiste già nel ponte acidità (lì realizza l'acidità): solo arco, niente reinserimento
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-ferm-alcolica', 'Processo', 'Fermentazione alcolica', 'fermentazione',
 '{"tipo":"biologico","scheda":"I lieviti (Saccharomyces) trasformano zuccheri in alcol + CO2. E il vino, la birra, la base alcolica di ogni distillato, e la spinta del lievito nel pane (qui conta la CO2, non l''alcol che evapora in forno)."}');

-- PRODOTTI-PROVA: la fermentazione e il fenomeno PIU trasversale
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-madre',     'Prodotto', 'Lievito madre', 'bakery', '{}'),
('prod-crauti',    'Prodotto', 'Crauti / kimchi', 'cucina', '{}'),
('prod-yogurt',    'Prodotto', 'Yogurt', 'cucina', '{}'),
('prod-vino',      'Prodotto', 'Vino', 'fermentazione', '{}'),
('prod-kombucha',  'Prodotto', 'Kombucha', 'bar', '{}');
-- prod-birra-carb e prod-sour esistono gia: la fermentazione li tocca

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-madre-debole', 'Errore', 'Madre debole / non parte', 'bakery', '{"causa":"temperatura sbagliata (sotto i 18-20°C i lattici rallentano molto) o rinfreschi troppo distanti"}'),
('err-ferm-bloccata','Errore', 'Fermentazione bloccata', 'fermentazione', '{"causa":"troppo freddo, troppo sale, o pH gia troppo basso: l''organismo smette di lavorare"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- misurato_da: pH e temperatura CONDIVISI (scoperta strutturale) + quoziente proprio
('fen-fermentazione','cal-ph','misurato_da','{"nota":"il pH e l''orologio della fermentazione — condiviso con Acidita (effetto, non causa)"}'),
('fen-fermentazione','cal-q10','misurato_da','{"nota":"la temperatura governa la cinetica biologica — condivisa con Calore"}'),
('fen-fermentazione','cal-quoziente-ferm','misurato_da','{}'),
-- realizzato_da
('fen-fermentazione','proc-ferm-lattica','realizzato_da','{}'),
('fen-fermentazione','proc-ferm-alcolica','realizzato_da','{}'),
-- si_manifesta_in: il piu cross-dominio (bakery, cucina, fermentazione, bar)
('fen-fermentazione','prod-madre','si_manifesta_in','{"target":"pH 3,7-4,1 a maturita, 24-28°C","ruolo":"lievitazione + acidita + aroma del pane naturale"}'),
('fen-fermentazione','prod-crauti','si_manifesta_in','{"target":"2-3% sale, pH finale 3,4-4,1","ruolo":"conservazione e sapore per via lattica"}'),
('fen-fermentazione','prod-yogurt','si_manifesta_in','{"target":"42-45°C, pH ~4,5","ruolo":"latte addensato e acidificato dai lattici"}'),
('fen-fermentazione','prod-vino','si_manifesta_in','{"target":"lieviti + eventuale malolattica","ruolo":"zucchero dell''uva in alcol, poi ammorbidimento lattico"}'),
('fen-fermentazione','prod-kombucha','si_manifesta_in','{"target":"SCOBY, 1-2 settimane","ruolo":"te zuccherato fermentato, acido e leggermente frizzante"}'),
('fen-fermentazione','prod-birra-carb','si_manifesta_in','{"target":"lieviti birrari","ruolo":"mosto del malto in alcol e CO2"}'),
-- fallisce_come
('prod-madre','err-madre-debole','fallisce_come','{}'),
('prod-vino','err-ferm-bloccata','fallisce_come','{}');
