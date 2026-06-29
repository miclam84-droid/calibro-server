-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: CAFFETTERIA
-- Arricchisce prod-espresso, prod-filtro, prod-te-infuso già presenti
-- con numeri reali (EY, TDS, ratio, temperatura, diagnosi per quadrante).
-- Aggiunge: moka, cold brew, la struttura diagnostica a 4 quadranti.
-- Il caffè è il caso paradigmatico di Estrazione: due assi indipendenti
-- (EY = quanto hai estratto; TDS = quanto è concentrato).
-- ============================================================

-- ---- ARRICCHIMENTO dei nodi esistenti (UPDATE via inserimento archi) -
-- prod-espresso e prod-filtro esistono già: aggiungo archi di dettaglio

-- ---- NUOVI PRODOTTI -------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-moka',       'Prodotto', 'Caffè moka', 'caffetteria',
 '{"spec":"rapporto ~1:7, alta temperatura, pressione vapore","note":"TDS alto (~3-5%), EY spesso sotto 18% per via della temperatura"}'),
('prod-cold-brew',  'Prodotto', 'Cold brew', 'caffetteria',
 '{"spec":"rapporto 1:8 circa, acqua fredda, 12-24h","note":"EY bassa per efficienza estrattiva ridotta del freddo; TDS compensato dalla concentrazione"}'),
('prod-aeropress',  'Prodotto', 'AeroPress', 'caffetteria',
 '{"spec":"recipe-dipendente: può imitare filtro o espresso","note":"variabile: 1:6 (concentrato) a 1:16 (filtro)"}');

-- ---- PROCESSI specifici della caffetteria ----------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-percolazione', 'Processo', 'Percolazione (filtro/pour-over)', 'caffetteria',
 '{"tipo":"fisico-chimico","scheda":"Acqua a 90-96°C percola attraverso il letto di caffè per gravità. Contatto 3-4 minuti per filtro. La macinatura governa la resistenza al flusso: troppo fine = stallo, troppo grossa = bypass. Ratio 1:15-1:17. EY target 18-22%, TDS 1,15-1,35%."}'),
('proc-pressione-espresso', 'Processo', 'Estrazione sotto pressione (espresso)', 'caffetteria',
 '{"tipo":"fisico-chimico","scheda":"9 bar di pressione forzano acqua a 90-96°C attraverso il puck in 25-30 secondi. La pressione estrae oli e colloidi che la percolazione non cattura: da qui la crema. Ratio 1:2 (18g in → 36g out). EY 18-22%, TDS 8-12%."}');

-- ---- DIAGNOSI a 4 quadranti (il valore diagnostico di Calibro) -
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-sotto-estratto',  'Errore', 'Sotto-estratto (EY <18%)', 'caffetteria',
 '{"causa":"macinatura troppo grossa, temperatura bassa (<90°C), contatto troppo breve o ratio troppo abbondante. Sapore: acido, sottile, erbaceo. Fix: macina più fine, alza temperatura, allunga il contatto."}'),
('err-sovra-estratto',  'Errore', 'Sovra-estratto (EY >22%)', 'caffetteria',
 '{"causa":"macinatura troppo fine, temperatura alta (>96°C), contatto troppo lungo. Sapore: amaro, secco, astringente. Fix: macina più grossa, abbassa temperatura, accorcia il contatto."}'),
('err-debole-tds',      'Errore', 'Debole (TDS basso, EY ok)', 'caffetteria',
 '{"causa":"ratio troppo abbondante (troppa acqua). Estratto bilanciato ma diluito. Fix: aumenta la dose o riduci l acqua (ratio 1:15 invece di 1:18)."}'),
('err-intenso-tds',     'Errore', 'Intenso/fangoso (TDS alto)', 'caffetteria',
 '{"causa":"ratio troppo ristretto (poca acqua). Fix: aggiungi acqua, allarga il ratio."}');

-- ============================================================
-- ARCHI — arricchisco i prodotti esistenti + i nuovi
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- ESTRAZIONE governa la caffetteria (arricchimento dei nodi esistenti)
-- (arco già presente in seed-fenomeno-estrazione, non duplicare)
-- (arco già presente in seed-fenomeno-estrazione, non duplicare)
('fen-estrazione','prod-moka','si_manifesta_in',
 '{"target":"ratio ~1:7, TDS alto ~3-5%","ruolo":"vapore a pressione, spesso sotto-estratto per temperatura irregolare"}'),
('fen-estrazione','prod-cold-brew','si_manifesta_in',
 '{"target":"ratio ~1:8, 12-24h a freddo","ruolo":"il freddo abbassa l efficienza: serve più tempo per raggiungere EY simile"}'),
('fen-estrazione','prod-aeropress','si_manifesta_in',
 '{"target":"recipe-dipendente, 1:6-1:16","ruolo":"il metodo più versatile: può imitare filtro o espresso"}'),

-- CALORE: la temperatura governa la cinetica di estrazione
('fen-calore','prod-espresso','si_manifesta_in',
 '{"target":"90-96°C, 25-30 secondi","ruolo":"temperatura + pressione + tempo = la tripla leva dell espresso"}'),
('fen-calore','prod-filtro','si_manifesta_in',
 '{"target":"90-96°C, 3-4 minuti","ruolo":"sotto 90°C estrazione lenta e incompleta; sopra 96°C rischio sovra-estrazione"}'),
('fen-calore','prod-cold-brew','si_manifesta_in',
 '{"target":"4-20°C, 12-24h","ruolo":"il freddo rallenta tutto: stesso EY richiede molto più tempo"}'),

-- processi
('prod-filtro','proc-percolazione','realizzato_da','{}'),
('prod-espresso','proc-pressione-espresso','realizzato_da','{}'),

-- diagnosi a 4 quadranti
('prod-filtro','err-sotto-estratto','fallisce_come','{}'),
('prod-filtro','err-sovra-estratto','fallisce_come','{}'),
('prod-filtro','err-debole-tds','fallisce_come','{}'),
('prod-espresso','err-sotto-estratto','fallisce_come','{}'),
('prod-espresso','err-sovra-estratto','fallisce_come','{}');
