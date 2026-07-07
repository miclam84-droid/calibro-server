-- ============================================================
-- FENOMENO: Ossidazione (enzimatica e dei grassi)
-- Regola di partizione: OK
-- Numero-bersaglio: numero di perossidi (rancidita) + pH ottimale PPO (imbrunimento)
--   rancidita: perossidi <= 20 meq O2/kg (limite olio) 
--   imbrunimento enzimatico: PPO ottimale pH 4,5-5,5, bloccato sotto pH 3
-- Strumento: titolazione (numero di perossidi) · pH-metro
-- Si manifesta in: mela/avocado tagliati, olio/frutta secca, vino
-- Fonti: studi PPO (pH ottimale 4,5-5,5); shelf-life olio (>20 meq/kg in 4 settimane).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-ossidazione', 'Fenomeno', 'Ossidazione', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"rancidita: numero di perossidi <= 20 meq O2/kg (limite olio) · imbrunimento enzimatico: PPO ottimale pH 4,5-5,5, bloccato sotto pH 3 (limone, ac. ascorbico)",
   "strumento":"titolazione (numero di perossidi) · pH-metro",
   "scheda":"L ossigeno attacca il cibo in due modi diversi. Sui grassi: irrancidimento. L olio esposto a luce, calore e aria forma perossidi e poi aldeidi che sanno di rancido; l olio buono sta sotto i 20 meq O2/kg, ma in bottiglia chiara al sole li supera in poche settimane. Sui vegetali tagliati: imbrunimento enzimatico. Un enzima (la polifenolossidasi, PPO) usa l ossigeno per ossidare i fenoli in pigmenti bruni: e la mela, l avocado, il carciofo che anneriscono. La PPO lavora meglio a pH 4,5-5,5 e ha il rame come cofattore, quindi si blocca in tre modi: abbassare il pH sotto 3 (limone, acido ascorbico, che chela anche il rame), togliere l ossigeno (acqua, sottovuoto), o il freddo. Stesso avversario, l ossigeno; due chimiche diverse, un solo numero da tenere d occhio per stanza."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-mela-tagliata', 'Prodotto', 'Frutta tagliata (mela, avocado)', 'cucina',
 '{"target":"annerisce in minuti · blocco: pH<3 (limone), acqua fredda (meno O2), sottovuoto",
   "strumento":"pH-metro / valutazione visiva"}'),
('prod-olio-conservato', 'Prodotto', 'Olio e frutta secca', 'cucina',
 '{"target":"perossidi <=20 meq O2/kg · luce+calore+O2 accelerano · vetro scuro, fresco, 6 mesi da aperto",
   "strumento":"numero di perossidi (titolazione)"}'),
('prod-vino-ossidato', 'Prodotto', 'Vino esposto all aria', 'bar',
 '{"target":"ossidazione da O2: colore che vira, aromi piatti · gas inerte o sottovuoto per rallentare",
   "strumento":"valutazione sensoriale"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-ossidazione', 'prod-mela-tagliata', 'si_manifesta_in',
 '{"target":"pH<3 blocca","causa":"La PPO ossida i fenoli col rame e l ossigeno: abbassare il pH sotto il suo ottimo (4,5-5,5) o togliere l O2 la ferma"}'),
('fen-ossidazione', 'prod-olio-conservato', 'si_manifesta_in',
 '{"target":"<=20 meq O2/kg","causa":"Luce, calore e ossigeno innescano la perossidazione dei grassi insaturi: si formano aldeidi rancide. Vetro scuro e fresco rallentano tutto"}'),
('fen-ossidazione', 'prod-vino-ossidato', 'si_manifesta_in',
 '{"target":"ridurre O2","causa":"L ossigeno consuma gli aromi e ossida i polifenoli: gas inerte o sottovuoto tolgono l ossigeno dalla bottiglia aperta"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-irrancidimento', 'Errore', 'Irrancidimento (grassi ossidati)', 'cucina',
 '{"causa":"Grassi insaturi esposti a O2, luce e calore: perossidi oltre soglia, odore e sapore di rancido","soluzione":"Conservare al buio, al fresco, in contenitori pieni e chiusi; consumare entro i tempi; antiossidanti naturali (vitamina E)"}'),
('err-annerimento', 'Errore', 'Annerimento (imbrunimento enzimatico)', 'cucina',
 '{"causa":"Superficie tagliata esposta all aria: la PPO ossida i fenoli in pigmenti bruni","soluzione":"Limone o acido ascorbico (pH<3, chela il rame), immersione in acqua fredda, sottovuoto, o scottatura che denatura l enzima"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-ossidazione', 'err-irrancidimento', 'fallisce_come',
 '{"causa":"Perossidazione dei grassi oltre la soglia"}'),
('fen-ossidazione', 'err-annerimento', 'fallisce_come',
 '{"causa":"PPO che ossida i fenoli in melanine brune"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-ossidazione', 'fen-atmosfera-modificata', 'influenza',
 '{"nota":"Togliere ossigeno e la difesa comune: l atmosfera modificata (basso O2) rallenta sia irrancidimento sia imbrunimento. Stessa leva, l O2"}'),
('fen-ossidazione', 'fen-shelf-life', 'influenza',
 '{"nota":"L ossidazione e uno degli orologi della shelf life: il numero di perossidi misura quanto e avanzata la degradazione di un grasso"}');
