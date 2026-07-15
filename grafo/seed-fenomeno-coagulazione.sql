-- ============================================================
-- FENOMENO: Coagulazione proteica
-- Regola: ✓ — temperature di denaturazione misurabili con termometro
-- Strumento: termometro + sonda core
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-coagulazione', 'Fenomeno', 'Coagulazione proteica', 'trasversale',
 '{"tipo":"fisico-chimico",
   "target":"Miosina 50°C · Actina 65°C · Albumina uovo 63-82°C · Caseina 85°C · Collagene 70°C+",
   "strumento":"termometro a sonda core (±0,5°C)",
   "scheda":"Le proteine coagulano quando il calore rompe i legami che ne mantengono la struttura tridimensionale, e le catene si aggregano formando una rete solida. È irreversibile. Temperature diverse coagulano proteine diverse: nella carne, la miosina coagula a 50°C (inizio della perdita di succhi), l'actina a 65°C (consistenza gommosa). Cuocere sous vide a 55-58°C lascia la miosina coagulata ma l'actina intatta — risultato morbido e succoso impossibile da ottenere in padella. L'uovo è un sistema complesso: il tuorlo coagula tra 65-70°C, l'albume tra 63-82°C a seconda della proteina. La gelatina è collagene coagulato e reidrolizzato: richiede temperatura alta (>70°C) e tempo."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-uovo-sousvide', 'Prodotto', 'Uovo sous-vide / onsen', 'cucina',
 '{"target":"63°C/1h = bianco morbido tuorlo fluido · 68°C/1h = tuorlo cremoso","strumento":"termometro + vasca sous-vide"}'),
('prod-carne-sousvide', 'Prodotto', 'Carne sous-vide', 'cucina',
 '{"target":"54-57°C medium rare · 60°C medium · 70°C+ well done","strumento":"termometro sonda core"}'),
('prod-yogurt-coag', 'Prodotto', 'Yogurt', 'cucina',
 '{"target":"pastorizzazione 85°C/30min poi inoculo a 43°C","strumento":"termometro"}'),
('prod-creme-inglese', 'Prodotto', 'Crema inglese / Zabaione', 'pasticceria',
 '{"target":"82-84°C (nappante) — sopra 85°C la crema si straccia","strumento":"termometro sonda"}'),
('prod-brodo-gelatina', 'Prodotto', 'Brodo gelatinoso / Fond', 'cucina',
 '{"target":"collagene → gelatina sopra 70°C con cottura lunga (4-8h)","strumento":"termometro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'prod-uovo-sousvide', 'si_manifesta_in',
 '{"target":"63°C albumina morbida · 82°C tuorlo sodo","causa":"Albumina coagula progressivamente: temperatura = consistenza finale"}'),
('fen-coagulazione', 'prod-carne-sousvide', 'si_manifesta_in',
 '{"target":"50°C miosina · 65°C actina","causa":"Miosina = tenerezza, actina = secchezza. Cuocere tra 50 e 65°C = tenero e succoso"}'),
('fen-coagulazione', 'prod-yogurt-coag', 'si_manifesta_in',
 '{"target":"85°C pastorizzazione · 43°C fermentazione","causa":"Il calore denatura la caseina (struttura più compatta) poi i batteri acidificano e la fanno coagulare"}'),
('fen-coagulazione', 'prod-creme-inglese', 'si_manifesta_in',
 '{"target":"82-84°C","causa":"L albumina dell uovo coagula lentamente: sotto 82°C non addensa, sopra 85°C si straccia"}'),
('fen-coagulazione', 'prod-brodo-gelatina', 'si_manifesta_in',
 '{"target":"70°C+ per 4-8h","causa":"Il collagene non indurisce con il calore: si converte in gelatina (idrolisi). Più lunga la cottura, più gelatina"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-carne-asciutta', 'Errore', 'Carne asciutta / gommosa', 'cucina',
 '{"causa":"Cottura oltre 65°C: actina coagulata stringe e espelle i liquidi","soluzione":"Sous-vide sotto 65°C oppure braisé lungo (collagene → gelatina compensa)"}'),
('err-crema-stracciatella', 'Errore', 'Crema inglese stracciatella', 'pasticceria',
 '{"causa":"Temperatura oltre 85°C: coagulazione rapida e granulosa dell albumina","soluzione":"Cuocere a bagnomaria o sotto 84°C con termometro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'err-carne-asciutta', 'fallisce_come',
 '{"causa":"Actina coagulata oltre 65°C"}'),
('fen-coagulazione', 'err-crema-stracciatella', 'fallisce_come',
 '{"causa":"Albumina coagulata oltre 85°C"}');

-- connessione con Calore e Fermentazione
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-coagulazione', 'fen-calore', 'influenza',
 '{"nota":"La temperatura è il parametro di controllo della coagulazione proteica"}'),
('fen-coagulazione', 'fen-fermentazione', 'influenza',
 '{"nota":"Nello yogurt e nei formaggi la fermentazione batterica abbassa il pH e contribuisce alla coagulazione della caseina"}');
