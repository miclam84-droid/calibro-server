-- ============================================================
-- SICUREZZA — ZONA DI PERICOLO TERMICA
-- Il range 4°C–60°C dove i patogeni si moltiplicano.
-- Non è un fenomeno nuovo: è Calore visto dalla sicurezza.
-- Numero bersaglio: temperatura fuori dalla zona di pericolo.
-- Strumento: termometro (già in uso per Calore).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-zona-pericolo', 'Fenomeno', 'Zona di pericolo termica', 'sicurezza',
 '{"tipo":"biologico","numero_bersaglio":"<4°C o >60°C (fuori zona pericolo) · doubling time ~20 min a 37°C · abbattimento: -18°C in <240 min","scheda":"Tra 4°C e 60°C i batteri patogeni si moltiplicano. Sotto 4°C rallentano quasi del tutto. Sopra 60°C muoiono progressivamente. La zona di pericolo non è una metafora — è un numero fisico con una conseguenza biologica precisa: ogni 20 minuti a 37°C la carica batterica raddoppia. Il termometro è l''unico strumento che conta."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-abbattimento', 'Processo', 'Abbattimento rapido', 'sicurezza',
 '{"nota":"portare un alimento da +90°C a +3°C in meno di 90 minuti — impedisce la moltiplicazione batterica nella zona di pericolo durante il raffreddamento"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-catena-freddo', 'Processo', 'Catena del freddo', 'sicurezza',
 '{"nota":"mantenere la temperatura sotto 4°C in modo continuo dalla produzione alla somministrazione — ogni interruzione riavvia il contatore batterico"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-doubling-time', 'Calcolo', 'Doubling time batterico', 'sicurezza',
 '{"formula":"N(t) = N0 × 2^(t/td) — N0: carica iniziale, t: tempo (min), td: tempo di raddoppio (~20 min a 37°C)","nota":"stima orientativa — dipende dalla specie batterica e dalla matrice alimentare"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-interruzione-catena', 'Errore', 'Interruzione catena del freddo', 'sicurezza',
 '{"sintomo":"alimento rientrato in zona di pericolo per tempo indeterminato","causa":"trasporto non refrigerato, abbattimento incompleto, aperture prolungate del frigo","correzione":"non basta riportare in temperatura — il danno microbiologico è già avvenuto; scartare se il tempo in zona pericolo supera 2 ore cumulative"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-zona-pericolo', 'proc-abbattimento', 'controllato_con', 1.0),
('fen-zona-pericolo', 'proc-catena-freddo', 'controllato_con', 1.0),
('fen-zona-pericolo', 'cal-doubling-time', 'misurato_da', 1.0),
('fen-zona-pericolo', 'err-interruzione-catena', 'fallisce_come', 1.0),
('fen-zona-pericolo', 'fen-fermentazione', 'influenza', 0.8),
('fen-calore', 'fen-zona-pericolo', 'determina', '{}');
