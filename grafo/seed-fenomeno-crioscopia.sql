-- ============================================================
-- FENOMENO: Abbassamento crioscopico (freezing point depression)
-- Regola di partizione: OK
-- Numero-bersaglio: PAC totale del mix (potere anticongelante)
--   sucrosio = 100 di riferimento. Gelato scoopabile: PAC 260-350,
--   servito a -11/-14C, con 60-80% dell'acqua congelata.
-- Strumento: curva di congelamento / calcolo PAC
-- Si manifesta in: gelato, sorbetto, granita, semifreddo
-- Fonti: Gelato Maestro; gelatorecipes.com; Underbelly; iceicedaddy PAC.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-crioscopia', 'Fenomeno', 'Abbassamento crioscopico', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"PAC totale 260-350 (scoopabile a -11/-14C) · congelamento iniziale -2/-3C · 60-80% acqua congelata al servizio",
   "strumento":"curva di congelamento / calcolo PAC (sucrosio = 100)",
   "scheda":"L acqua pura congela a 0C, ma i soluti disciolti abbassano quel punto: e la stessa fisica del sale sulle strade d inverno. Nel gelato lo zucchero e il regista della cremosita. Ogni zucchero ha un potere anticongelante (PAC): sucrosio = 100 di riferimento, destrosio ~175, fruttosio ~180, lattosio 100. Sommando i PAC del mix si ottiene quanta acqua resta liquida a una data temperatura. Un PAC totale intorno a 280-320 tiene il gelato morbido e scavabile a -12C; troppo basso e diventa un mattone, troppo alto e non tiene la forma. Al servizio (-11/-14C) circa il 60-80% dell acqua e ghiaccio e il resto e sciroppo concentrato: e quella frazione liquida che da la cremosita. Stesso principio del bilanciamento sour (concentrazione) e del gel di zucchero (cristallizzazione), applicato al freddo."}');

-- prodotti dove si manifesta
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-gelato-base', 'Prodotto', 'Gelato base (creme)', 'gelateria',
 '{"target":"PAC 280-320 · zuccheri 16-22% · grassi 4-9% · SML 9-12% · solidi totali 35-40% · servizio -11/-13C · overrun 20-35%",
   "strumento":"bilancia + calcolo PAC/POD"}'),
('prod-sorbetto', 'Prodotto', 'Sorbetto alla frutta', 'gelateria',
 '{"target":"PAC 290-330 (niente grassi a compensare) · zuccheri 24-30% · solidi 28-34% · servizio -10/-12C",
   "strumento":"rifrattometro (Brix) + calcolo PAC"}'),
('prod-granita', 'Prodotto', 'Granita', 'gelateria',
 '{"target":"cristalli grossolani voluti · PAC basso · zuccheri ~20-24% · mantecazione minima/assente",
   "strumento":"rifrattometro"}');

-- archi: Abbassamento crioscopico si_manifesta_in
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'prod-gelato-base', 'si_manifesta_in',
 '{"target":"PAC 280-320","causa":"Il PAC totale decide quanta acqua resta liquida a -12C: e la frazione liquida a dare la cremosita scoopabile"}'),
('fen-crioscopia', 'prod-sorbetto', 'si_manifesta_in',
 '{"target":"PAC 290-330","causa":"Senza grassi che ammorbidiscono, lo zucchero deve fare tutto il lavoro anticongelante: PAC piu alto per restare scavabile"}'),
('fen-crioscopia', 'prod-granita', 'si_manifesta_in',
 '{"target":"PAC basso, cristalli grossi","causa":"Qui i cristalli grossi sono voluti: poco anticongelante e nessuna mantecazione danno la texture granulosa tipica"}');

-- errori comuni
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-gelato-duro', 'Errore', 'Gelato troppo duro (mattone)', 'gelateria',
 '{"causa":"PAC totale troppo basso (pochi zuccheri o zuccheri sbagliati) oppure servito troppo freddo: troppa acqua e congelata","soluzione":"Alzare il PAC sostituendo parte del sucrosio con destrosio; servire a -11/-13C"}'),
('err-gelato-molle', 'Errore', 'Gelato che non tiene la forma', 'gelateria',
 '{"causa":"PAC totale troppo alto: troppa acqua resta liquida, la struttura collassa nella vetrina","soluzione":"Ridurre destrosio/zuccheri invertiti; ribilanciare verso PAC 280-300"}'),
('err-gelato-sabbioso', 'Errore', 'Gelato sabbioso / granuloso', 'gelateria',
 '{"causa":"Eccesso di lattosio (SML troppo alto) che ricristallizza, oppure ricristallizzazione del ghiaccio da sbalzi termici (catena del freddo rotta)","soluzione":"Tenere SML 9-12%; evitare scongelamenti parziali; abbattere in fretta"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'err-gelato-duro', 'fallisce_come',
 '{"causa":"PAC insufficiente: la curva di congelamento e troppo a sinistra"}'),
('fen-crioscopia', 'err-gelato-molle', 'fallisce_come',
 '{"causa":"PAC eccessivo: troppa frazione liquida al servizio"}'),
('fen-crioscopia', 'err-gelato-sabbioso', 'fallisce_come',
 '{"causa":"Lattosio o ghiaccio che ricristallizzano in cristalli percepibili"}');

-- connessioni cross-dominio
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'fen-concentrazione', 'influenza',
 '{"nota":"Il PAC dipende dalla concentrazione di zuccheri: e la stessa leva soluto/solvente del bilanciamento e dello sciroppo, letta come effetto sul punto di congelamento"}'),
('fen-crioscopia', 'fen-cristallizzazione', 'influenza',
 '{"nota":"Il PAC governa quanta acqua congela; la cristallizzazione governa in che cristalli. Insieme decidono se il gelato e cremoso o granuloso"}');
