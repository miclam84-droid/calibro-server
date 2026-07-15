-- ============================================================
-- FENOMENO: Lievitazione chimica (CO2 da reazione acido-base)
-- Regola di partizione: OK
-- Numero-bersaglio: dosaggio + valore neutralizzante + bilancio pH
--   dosaggio 1-2% sul peso farina · NV = g bicarbonato neutralizzati da 100g acido
--   CO2 ~15% a freddo + 85% in forno (double-action)
-- Strumento: bilancia (dosaggio) · pH-metro (bilanciamento acido-base)
-- DISTINTA da fermentazione (biologica) e carbonatazione (Henry).
-- Si manifesta in: torta, biscotti, pancake, soda bread
-- Fonti: Wikipedia (neutralizing value); ASB/BAKERpedia; LibreTexts food science.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-lievitazione-chimica', 'Fenomeno', 'Lievitazione chimica', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"dosaggio 1-2% sul peso farina · valore neutralizzante (NV): l acido bilancia il bicarbonato per pH neutro · CO2 ~15% a freddo, 85% in forno (double-action)",
   "strumento":"bilancia (dosaggio) · pH-metro (bilanciamento acido-base)",
   "scheda":"Il lievito chimico non è un organismo biologico: è una combinazione di bicarbonato di sodio (base) e un acido (cremor tartaro, sodio pirofosfato, acido citrico) che reagiscono in presenza di umidità e calore producendo CO₂. Il lievito double-action libera gas in due fasi: una prima reazione a freddo e umido quando si mescola l'impasto, una seconda in forno al di sopra dei 60°C — questo permette all'impasto di strutturarsi prima della seconda spinta. Il pH finale influenza il colore della mollica: eccesso di bicarbonato produce un pH alcalino che accelera la reazione di Maillard e produce torte dal sapore saponoso. Il bilanciamento acido-base è il parametro tecnico critico."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-torta-lievito-chimico', 'Prodotto', 'Torta / plumcake', 'pasticceria',
 '{"target":"lievito chimico 1-2% farina · double-action (spinta in forno) · pH bilanciato per mollica chiara",
   "strumento":"bilancia + pH indicativo"}'),
('prod-biscotti', 'Prodotto', 'Biscotti', 'pasticceria',
 '{"target":"bicarbonato + acido (o lievito chimico) · soda in eccesso = crosta scura e retrogusto · spesso dosaggio basso 0,5-1%",
   "strumento":"bilancia"}'),
('prod-pancake-soda', 'Prodotto', 'Pancake / soda bread', 'bakery',
 '{"target":"bicarbonato + latticello (acido) · reazione rapida, cuocere subito prima che il gas si esaurisca",
   "strumento":"bilancia + tempi"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-lievitazione-chimica', 'prod-torta-lievito-chimico', 'si_manifesta_in',
 '{"target":"1-2% farina","causa":"Il double-action tiene la spinta per il forno: la CO2 gonfia la struttura mentre l uovo e l amido la fissano col calore"}'),
('fen-lievitazione-chimica', 'prod-biscotti', 'si_manifesta_in',
 '{"target":"0,5-1%","causa":"Poco gas, si vuole spinta contenuta e doratura: qui la soda serve anche ad alzare il pH e favorire Maillard e allargamento"}'),
('fen-lievitazione-chimica', 'prod-pancake-soda', 'si_manifesta_in',
 '{"target":"bicarbonato + acido","causa":"Bicarbonato e latticello reagiscono subito a freddo: l impasto va cotto senza attesa o il gas si esaurisce prima della padella"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-retrogusto-soda', 'Errore', 'Retrogusto di bicarbonato / mollica gialla', 'pasticceria',
 '{"causa":"Troppa soda senza acido sufficiente a neutralizzarla: l impasto diventa alcalino, mollica giallastra e sapore saponoso","soluzione":"Bilanciare con un acido (cremor tartaro, latticello, succo) secondo il valore neutralizzante, o usare lievito chimico gia bilanciato"}'),
('err-lievitazione-debole', 'Errore', 'Lievitazione debole (piatto)', 'bakery',
 '{"causa":"Dosaggio insufficiente, lievito scaduto, o impasto lasciato riposare finche il gas si e esaurito prima del forno","soluzione":"Verificare dosaggio e freschezza; per il bicarbonato+acido, infornare subito senza attesa"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-lievitazione-chimica', 'err-retrogusto-soda', 'fallisce_come',
 '{"causa":"Eccesso di base non neutralizzata: alcalinita, colore e sapore alterati"}'),
('fen-lievitazione-chimica', 'err-lievitazione-debole', 'fallisce_come',
 '{"causa":"CO2 insufficiente o esaurita prima della cottura"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-lievitazione-chimica', 'fen-fermentazione', 'influenza',
 '{"nota":"Stesso risultato (CO2 che gonfia), meccanismo opposto: qui una reazione chimica istantanea, nella fermentazione dei lieviti vivi e ore di tempo. Sapore diverso: niente aromi di fermentazione"}'),
('fen-lievitazione-chimica', 'fen-acidita', 'influenza',
 '{"nota":"Il cuore e un equilibrio acido-base: l acido misurato (valore neutralizzante) decide il pH finale e quindi colore, sapore e spinta"}');
