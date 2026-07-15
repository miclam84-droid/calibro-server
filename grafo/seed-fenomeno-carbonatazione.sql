-- ============================================================
-- FENOMENO CARBONATAZIONE — costruito con la regola.
-- Numero-bersaglio: volumi di CO2 (litri CO2 a STP per litro di liquido).
-- Legge di Henry: gas disciolto proporzionale alla pressione, inverso alla temperatura.
-- Strumento: manometro / volumi misurati. tipo: fisico-chimico. Passa la regola.
-- Ponte inatteso: la CO2 della lievitazione è lo STESSO gas, intrappolato nel glutine
-- invece che disciolto nel liquido.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-carbonatazione', 'Fenomeno', 'Carbonatazione', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"La carbonatazione è la dissoluzione di CO₂ in un liquido secondo la legge di Henry: la quantità di gas disciolto è proporzionale alla pressione e inversamente proporzionale alla temperatura. Raffreddare il liquido prima di carbonatare aumenta la resa. La CO₂ disciolta forma acido carbonico (H₂CO₃), che abbassa il pH del drink di 0,3-0,5 unità — effetto percettivo rilevante sull'equilibrio acido-dolce. Nella pratica del bar: un mixer caldo o un bicchiere caldo fanno uscire la CO₂ prima che raggiunga il palato. Il ghiaccio non è solo raffreddamento: abbassa la temperatura del sistema e mantiene la carbonatazione più a lungo.","numero_bersaglio":"volumi di CO2: 1-2,5 (frutta) fino a 5-6 (champagne)"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-volumi-co2', 'Calcolo', 'Volumi di CO2', 'trasversale',
 '{"tipo":"fisico-chimico","nota":"litri CO2 (STP) per litro di liquido; legge di Henry: C = kH x P, kH dipende dalla temperatura"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-carb-forzata', 'Processo', 'Carbonatazione forzata', 'bar',
 '{"tipo":"fisico-chimico","scheda":"La carbonatazione è la dissoluzione di CO₂ in un liquido secondo la legge di Henry: la quantità di gas disciolto è proporzionale alla pressione e inversamente proporzionale alla temperatura. Raffreddare il liquido prima di carbonatare aumenta la resa. La CO₂ disciolta forma acido carbonico (H₂CO₃), che abbassa il pH del drink di 0,3-0,5 unità — effetto percettivo rilevante sull'equilibrio acido-dolce. Nella pratica del bar: un mixer caldo o un bicchiere caldo fanno uscire la CO₂ prima che raggiunga il palato. Il ghiaccio non è solo raffreddamento: abbassa la temperatura del sistema e mantiene la carbonatazione più a lungo."}'),
('proc-carb-fermentativa', 'Processo', 'Carbonatazione da fermentazione', 'fermentazione',
 '{"tipo":"biologico-fisico","scheda":"La carbonatazione è la dissoluzione di CO₂ in un liquido secondo la legge di Henry: la quantità di gas disciolto è proporzionale alla pressione e inversamente proporzionale alla temperatura. Raffreddare il liquido prima di carbonatare aumenta la resa. La CO₂ disciolta forma acido carbonico (H₂CO₃), che abbassa il pH del drink di 0,3-0,5 unità — effetto percettivo rilevante sull'equilibrio acido-dolce. Nella pratica del bar: un mixer caldo o un bicchiere caldo fanno uscire la CO₂ prima che raggiunga il palato. Il ghiaccio non è solo raffreddamento: abbassa la temperatura del sistema e mantiene la carbonatazione più a lungo."}');

-- PRODOTTI-PROVA: discipline emergono (bar, fermentazione, e il ponte col pane)
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-soda',       'Prodotto', 'Soda / acqua gassata', 'bar', '{}'),
('prod-spritz',     'Prodotto', 'Cocktail carbonato', 'bar', '{}'),
('prod-birra-carb', 'Prodotto', 'Birra (carbonatazione)', 'bar', '{}'),
('prod-spumante',   'Prodotto', 'Spumante / champagne', 'fermentazione', '{}');
-- prod-impasto (il pane) esiste già: la CO2 della lievitazione lo tocca

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-bevanda-scarica', 'Errore', 'Bevanda scarica/piatta', 'bar', '{"causa":"pochi volumi: pressione troppo bassa o liquido troppo caldo in carbonazione (Henry)"}'),
('err-gushing',         'Errore', 'Schiuma incontrollata (gushing)', 'fermentazione', '{"causa":"troppi volumi o sbalzo di temperatura: la CO2 esce tutta insieme cercando l''equilibrio"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-carbonatazione','cal-volumi-co2','misurato_da','{}'),
('fen-carbonatazione','cal-q10','misurato_da','{"nota":"la temperatura governa la solubilita (Henry) — leva condivisa con Calore"}'),
('fen-carbonatazione','proc-carb-forzata','realizzato_da','{}'),
('fen-carbonatazione','proc-carb-fermentativa','realizzato_da','{}'),
-- si_manifesta_in: bar, fermentazione, e il PONTE col pane
('fen-carbonatazione','prod-soda','si_manifesta_in','{"target":"3-4 volumi","ruolo":"CO2 iniettata, frizzantezza pulita"}'),
('fen-carbonatazione','prod-spritz','si_manifesta_in','{"target":"2-3 volumi","ruolo":"bollicine che portano gli aromi al naso"}'),
('fen-carbonatazione','prod-birra-carb','si_manifesta_in','{"target":"1,5-3,5 volumi per stile","ruolo":"corpo, schiuma, percezione del gusto"}'),
('fen-carbonatazione','prod-spumante','si_manifesta_in','{"target":"5-6 volumi, ~6 bar","ruolo":"presa di spuma, perlage fine"}'),
('fen-carbonatazione','prod-impasto','si_manifesta_in','{"target":"volume +50-75%","ruolo":"la STESSA CO2, ma intrappolata nel glutine invece che disciolta nel liquido"}'),
('prod-soda','err-bevanda-scarica','fallisce_come','{}'),
('prod-spumante','err-gushing','fallisce_come','{}');
