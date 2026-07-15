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
 '{"tipo":"biologico","scheda":"Il Saccharomyces cerevisiae converte gli zuccheri semplici in etanolo e CO₂ in assenza di ossigeno. La fermentazione alcolica è il processo fondamentale di birra, vino, pane e distillati. La temperatura di fermentazione influenza direttamente il profilo aromatico: fermentazioni a bassa temperatura (10-15°C per i lager) producono birre pulite con pochi esteri; ad alta temperatura (18-22°C per le ale) si producono più esteri e fenoli, tipici delle birre belghe e inglesi. I lieviti producono anche composti secondari (alcoli superiori, esteri, diacetile) che definiscono il carattere del prodotto finale. Il lievito muore oltre i 50-55°C — per questo il pane in forno non continua a lievitare dopo la prima fase di cottura.","numero_bersaglio":"pH 3,4-4,2 (effetto); 32-33°C ottimo lattici; acido 1,5-2,5%"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-quoziente-ferm', 'Calcolo', 'Quoziente di fermentazione', 'trasversale',
 '{"tipo":"biologico","nota":"rapporto acido lattico/acetico nella madre; insieme a pH e tempo dice a che punto e la fermentazione"}');

-- proc-ferm-lattica esiste già nel ponte acidità (lì realizza l'acidità): solo arco, niente reinserimento
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-ferm-alcolica', 'Processo', 'Fermentazione alcolica', 'fermentazione',
 '{"tipo":"biologico","scheda":"Il Saccharomyces cerevisiae converte gli zuccheri semplici in etanolo e CO₂ in assenza di ossigeno. La fermentazione alcolica è il processo fondamentale di birra, vino, pane e distillati. La temperatura di fermentazione influenza direttamente il profilo aromatico: fermentazioni a bassa temperatura (10-15°C per i lager) producono birre pulite con pochi esteri; ad alta temperatura (18-22°C per le ale) si producono più esteri e fenoli, tipici delle birre belghe e inglesi. I lieviti producono anche composti secondari (alcoli superiori, esteri, diacetile) che definiscono il carattere del prodotto finale. Il lievito muore oltre i 50-55°C — per questo il pane in forno non continua a lievitare dopo la prima fase di cottura."}');

-- PRODOTTI-PROVA: la fermentazione e il fenomeno PIU trasversale
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-madre',     'Prodotto', 'Lievito madre', 'bakery', '{}'),
('prod-crauti',    'Prodotto', 'Crauti / kimchi', 'cucina', '{}'),
('prod-yogurt',    'Prodotto', 'Yogurt', 'cucina', '{}'),
('prod-vino',      'Prodotto', 'Vino', 'bar', '{}'),
('prod-kombucha',  'Prodotto', 'Kombucha', 'bar', '{}'),
('prod-lievito-birra','Prodotto','Lievito di birra (fresco/secco)','bakery','{"target":"attivo 25-35°C · dosaggio ~2-3% sul peso farina (fresco) · muore oltre 50-55°C","strumento":"bilancia + termometro"}');
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
('fen-fermentazione','prod-lievito-birra','si_manifesta_in','{"target":"25-35°C, dosaggio 2-3%","ruolo":"il lievito comune del fornaio: CO2 rapida per la lievitazione biologica di ogni giorno"}'),
-- fallisce_come
('prod-madre','err-madre-debole','fallisce_come','{}'),
('prod-vino','err-ferm-bloccata','fallisce_come','{}');
