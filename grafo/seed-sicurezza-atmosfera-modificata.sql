-- ============================================================
-- SICUREZZA — ATMOSFERA MODIFICATA E SOTTOVUOTO
-- Rimuovere O2 cambia la biologia: blocca i patogeni aerobi
-- ma può favorire gli anaerobi (C. botulinum).
-- Numero bersaglio: O2 < 1% (sottovuoto/MAP).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-atmosfera-modificata', 'Fenomeno', 'Atmosfera modificata e sottovuoto', 'sicurezza',
 '{"tipo":"fisico-chimico","numero_bersaglio":"O2 <1% (sottovuoto/MAP) · CO2 20–30% (inibizione muffe) · N2 bilanciamento inerte","scheda":"Modificare la composizione dell''aria intorno all''alimento cambia quali microrganismi sopravvivono. Togliere l''ossigeno (sottovuoto, MAP) blocca la crescita di muffe e batteri aerobi. Ma attenzione: C. botulinum è anaerobio — in assenza di O2 può crescere anche a temperature di frigo se il pH è sopra 4,6 e Aw è alta. Il sottovuoto non è una soluzione universale: è efficace solo combinato con pH acido o Aw bassa o temperatura <3°C."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-sottovuoto', 'Processo', 'Confezionamento sottovuoto', 'sicurezza',
 '{"nota":"rimuove O2 > 99% — blocca ossidazione e crescita aerobi; richiede pH <4,6 o Aw <0,93 o T <3°C per inibire C. botulinum"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-map', 'Processo', 'Modified Atmosphere Packaging (MAP)', 'sicurezza',
 '{"nota":"sostituisce l''aria con mix N2/CO2/O2 calibrato — CO2 inibisce muffe e gram-negativi; O2 residuo mantiene colore carni; N2 inerte come carrier"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-botulinum-sottovuoto', 'Errore', 'C. botulinum in sottovuoto', 'sicurezza',
 '{"sintomo":"prodotto sottovuoto deteriorato senza segni visibili (C. botulinum non produce odori evidenti)","causa":"pH >4,6 + Aw >0,93 + T refrigerazione insufficiente in assenza di O2","correzione":"non aprire; scartare; in ambienti professionali: abbinare sempre sottovuoto ad almeno uno tra pH acido, Aw bassa, T <3°C"}');

INSERT INTO edges (from_id, to_id, relation, weight) VALUES
('fen-atmosfera-modificata', 'proc-sottovuoto', 'realizzato_da', 1.0),
('fen-atmosfera-modificata', 'proc-map', 'realizzato_da', 1.0),
('fen-atmosfera-modificata', 'err-botulinum-sottovuoto', 'fallisce_come', 1.0),
('fen-atmosfera-modificata', 'fen-shelf-life', 'influenza', 0.9),
('fen-acidita', 'fen-atmosfera-modificata', 'interagisce_con', 0.8),
('fen-aw', 'fen-atmosfera-modificata', 'interagisce_con', 0.8);
