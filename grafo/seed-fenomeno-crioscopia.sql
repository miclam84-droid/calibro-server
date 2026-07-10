-- FENOMENO: Abbassamento crioscopico (freezing point depression)
-- Regola di partizione: OK
-- Numero-bersaglio: PAC totale del mix (potere anticongelante)
-- sucrosio = 100 di riferimento. Gelato scoopabile: PAC 260-350
-- servito a -11/-14C, con 60-80% dell acqua congelata
-- Strumento: curva di congelamento / calcolo PAC
-- Si manifesta in: gelato, sorbetto, granita, semifreddo

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-crioscopia', 'Fenomeno', 'Abbassamento crioscopico', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"PAC totale 260-350 (scoopabile a -11/-14C) · congelamento iniziale -2/-3C · 60-80% acqua congelata al servizio",
   "strumento":"curva di congelamento / calcolo PAC (sucrosio = 100)",
   "scheda":"L acqua pura congela a 0C, ma i soluti disciolti abbassano quel punto: e la stessa fisica del sale sulle strade d inverno. Nel gelato lo zucchero e il regista della cremosita. Ogni zucchero ha un potere anticongelante (PAC): sucrosio = 100 di riferimento, destrosio ~175, fruttosio ~180, lattosio 100. Sommando i PAC del mix si ottiene quanta acqua resta liquida a una data temperatura. Un PAC totale intorno a 280-320 tiene il gelato morbido e scavabile a -12C."}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-gelato-cristalli', 'Prodotto', 'Gelato — controllo cristalli', 'gelateria',
 '{"target":"PAC 280-320 · zuccheri 16-22% · grassi 4-9% · servizio -11/-13C · overrun 20-35%",
   "strumento":"bilancia + calcolo PAC/POD"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-semifreddo', 'Prodotto', 'Semifreddo', 'gelateria',
 '{"target":"PAC 220-260 · non mantecato · servizio -14/-16C",
   "strumento":"calcolo PAC + termometro"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"PAC 280-320 · cremoso a -12C","causa":"Il PAC governa quanta acqua resta liquida: troppo basso = mattone, troppo alto = non tiene la forma"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'prod-sorbetto', 'si_manifesta_in',
 '{"target":"PAC 290-330 (senza grassi) · Brix 24-30%","causa":"Senza grassi il sorbetto ha bisogno di PAC piu alto per raggiungere la stessa morbidezza"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'prod-semifreddo', 'si_manifesta_in',
 '{"target":"PAC 220-260 · servizio piu freddo","causa":"Il semifreddo non viene mantecato: servito piu freddo per compensare la mancanza di overrun"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'fen-cristallizzazione', 'influenza',
 '{"nota":"La crioscopia determina A QUALE temperatura inizia la cristallizzazione — la dimensione dei cristalli dipende poi dalla velocita di raffreddamento"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
