-- ============================================================
-- FENOMENO: Vaporizzazione / Lievitazione fisica
-- Regola di partizione: OK — numero proprio + strumento indipendente
-- Numero-bersaglio: umidità impasto ~50-60% (acqua+uova) · forno 200-220°C
--   per generare pressione di vapore sufficiente a gonfiare
-- Strumento: termometro forno · bilancia (rapporto acqua/farina)
-- DISTINTA da lievitazione biologica (lieviti) e chimica (bicarbonato).
-- Si manifesta in: choux, sfoglia, soufflé, poppadum
-- Fonti: BAKERpedia (choux); America's Test Kitchen; cake-labs (Medium).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-vaporizzazione', 'Fenomeno', 'Vaporizzazione / Lievitazione fisica', 'trasversale',
 '{"tipo":"fisico",
   "numero_bersaglio":"umidita impasto ~50-60% (acqua+uova) · forno 200-220C · a 100C il vapore occupa 1700x il volume dell acqua: e la pressione che gonfia",
   "strumento":"termometro forno · bilancia (rapporto acqua:farina)",
   "scheda":"La lievitazione fisica usa il vapore acqueo come agente lievitante, non gas biologici né chimici. Nella pâte à choux, l'acqua intrappolata nella pasta — circa il 55-60% del peso totale — evapora in forno producendo vapore che gonfia la struttura mentre le proteine delle uova coagulano formando le pareti. Il principio è lo stesso nella pasta sfoglia: l'acqua contenuta nel burro vaporizza creando le lamine di sfoglia. La temperatura del forno deve essere alta (200°C+) per produrre vapore rapidamente prima che la struttura si solidifichi. Aprire lo sportello nella prima fase fa uscire il vapore e collassare la struttura — irreversibilmente."}');

-- prod-choux e prod-souffle nuovi; prod-sfoglia gia definito in seed-ponte-calore.sql
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-choux', 'Prodotto', 'Pasta choux (eclair, bigne)', 'pasticceria',
 '{"target":"acqua+burro portati a bollore · farina aggiunta e cotta · uova incorporate: umidita totale ~55-60% · forno 200-210C · MAI aprire lo sportello prima della fine",
   "strumento":"termometro forno · bilancia"}'),
('prod-souffle', 'Prodotto', 'Souffle', 'cucina',
 '{"target":"albumi montati + base calda · forno 180-190C · vapore + aria nelle bolle degli albumi · mangiare subito: il vapore si condensa e il souffle crolla",
   "strumento":"termometro forno"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-vaporizzazione', 'prod-choux', 'si_manifesta_in',
 '{"target":"200-210C, umidita 55-60%","causa":"Il vapore dell acqua nell impasto gonfia la struttura: senza vapore il choux resta piatto. La crosta si solidifica mentre il vapore ancora spinge, creando il vuoto interno caratteristico"}'),
('fen-vaporizzazione', 'prod-sfoglia', 'si_manifesta_in',
 '{"target":"200-220C","causa":"Il burro tra i fogli fonde e rilascia vapore che separa gli strati: e il vapore a creare la sfogliatura, non un lievito"}'),
('fen-vaporizzazione', 'prod-souffle', 'si_manifesta_in',
 '{"target":"180-190C","causa":"Vapore + aria negli albumi montati: la struttura sale finche il calore la solidifica. Se cade il forno o si apre lo sportello, il vapore si disperde e il souffle collassa"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-choux-piatto', 'Errore', 'Choux piatto (non gonfia)', 'pasticceria',
 '{"causa":"Forno troppo freddo (vapore insufficiente), impasto troppo asciutto, o sportello aperto durante la cottura (il vapore esce e la pressione cade)","soluzione":"Forno a 200-210C preriscaldato, non aprire mai prima di 20 minuti, verificare il rapporto acqua:farina"}'),
('err-choux-collassa', 'Errore', 'Choux collassa dopo cottura', 'pasticceria',
 '{"causa":"Sfornato troppo presto: la struttura non e ancora asciutta e il vapore residuo la fa cedere","soluzione":"Prolungare la cottura abbassando il forno (190C) negli ultimi 10 minuti con lo sportello leggermente aperto per asciugare senza bruciare"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-vaporizzazione', 'err-choux-piatto', 'fallisce_come',
 '{"causa":"Pressione di vapore insufficiente: forno freddo, impasto asciutto o dispersione precoce"}'),
('fen-vaporizzazione', 'err-choux-collassa', 'fallisce_come',
 '{"causa":"Struttura non asciugata: vapore residuo la fa cedere appena fuori dal forno"}'),
('fen-vaporizzazione', 'fen-lievitazione-chimica', 'influenza',
 '{"nota":"Le tre lievitazioni: fisica (vapore), chimica (bicarbonato+acido), biologica (lieviti). Stessa funzione — CO2 o vapore che gonfiano — meccanismi completamente diversi. Nel choux: solo vapore. Nel plumcake: solo chimica. Nel pane: solo biologica."}'),
('fen-vaporizzazione', 'fen-gelatinizzazione', 'influenza',
 '{"nota":"La gelatinizzazione dell amido nel choux (cottura della farina sul fuoco prima di aggiungere le uova) e il prerequisito: rende l impasto abbastanza elastico da intrappolare il vapore senza rompersi"}');
