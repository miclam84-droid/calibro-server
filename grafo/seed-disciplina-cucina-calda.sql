-- ============================================================
-- ARRICCHIMENTO: CUCINA CALDA — sous-vide + denaturazione proteine
-- Il fenomeno Calore applicato alle proteine: tre soglie precise.
-- COLLEGAMENTO TRASVERSALE: la stessa denaturazione proteica
-- governa carne, uova, latte, gelatina — quattro discipline.
-- La pastorizzazione è il ponte con fermentazione (yogurt, formaggi).
-- Numeri: McGee, Baldwin (Modernist Cuisine), USDA FSIS verificati.
-- ============================================================

-- ---- PROCESSO CENTRALE: la denaturazione proteica -----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-denaturazione-proteine', 'Processo', 'Denaturazione proteica (calore + tempo)', 'cucina',
 '{"tipo":"fisico-chimico","scheda":"Le proteine sono catene piegate in strutture 3D tenute da legami deboli. Il calore le spiega — le denatura — in modo irreversibile. In un muscolo ci sono tre proteine con soglie precise:\n1. MIOSINA (~50-55°C): prima a cedere. Dà tenerezza. A 54°C la miosina è denaturata, l actina è ancora intatta: il manzo medium-rare è esattamente questa finestra.\n2. COLLAGENE (53-63°C → gelatina >70°C): si contrae a 56-65°C aumentando la durezza, poi sopra i 70°C si idrolizza lentamente in gelatina. I tagli ricchi di collagene (guancia, coda, stinco) hanno bisogno di temperatura alta e TEMPO LUNGO per la conversione.\n3. ACTINA (67-80°C): denatura per ultima. Quando l actina cede la carne diventa asciutta e fibrosa — il well-done. La cottura perfetta è il controllo di queste tre soglie.","soglie":"miosina ~50-55°C · collagene gelatina >70°C · actina 67-80°C"}'),

('proc-pastorizzazione-tempo-temp', 'Processo', 'Pastorizzazione (tempo × temperatura)', 'cucina',
 '{"tipo":"fisico-chimico","scheda":"La pastorizzazione non è una soglia: è un prodotto tempo×temperatura. La stessa riduzione batterica (6.5 log di Salmonella) si ottiene a 55°C per 112 minuti OPPURE a 71°C istantaneamente. Il logaritmo governa: ogni grado in più dimezza il tempo necessario. Questo è il principio del sous-vide: temperature basse, tempi lunghi, stesso risultato microbiologico. USDA FSIS lo ha codificato in tabelle precise per ogni tipologia di carne. È la stessa cinetica Q10 che governa la lievitazione e la fermentazione — temperature più basse, processi più lenti, risultati identici con più tempo.","numeri":"55°C × 112 min = 71°C × 0 min (6.5 log riduzione Salmonella)"}');

-- ---- PRODOTTI: la cucina calda ---------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-manzo-sousvide',  'Prodotto', 'Manzo sous-vide', 'cucina',
 '{"temp_target":"54-57°C (medium-rare: miosina denaturata, actina intatta)","note":"tempo: 1-4h per bistecca; 24-48h per tagli ricchi di collagene"}'),
('prod-pollo-sousvide',  'Prodotto', 'Pollo sous-vide', 'cucina',
 '{"temp_target":"63-65°C × 1-4h (pastorizzato e succoso)","note":"a 74°C istantaneo per via tradizionale; a 63°C con il tempo ottieni lo stesso risultato microbiologico con texture completamente diversa"}'),
('prod-uova-sousvide',   'Prodotto', 'Uova a bassa temperatura', 'cucina',
 '{"temp_target":"63-65°C × 45-60 min (tuorlo cremoso, albume appena rappreso)","note":"l uovo perfetto: albume coagula a 63°C, tuorlo resta cremoso fino a 70°C. A 64°C per 1h: l uovo onsen giapponese"}'),
('prod-gelatina-brodo',  'Prodotto', 'Brodo/gelatina da collagene', 'cucina',
 '{"temp_target":"85-95°C × 4-8h (conversione collagene → gelatina)","note":"la gelatina non si forma a meno di 70°C. Brodo a fuoco lento (90°C) per ore: il collagene si idrolizza lentamente. Bollitura forte (100°C) non accelera: disperde la gelatina e intorbidisce"}');

-- ---- ERRORI cucina calda ---------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-carne-secca-calda',      'Errore', 'Carne secca e fibrosa', 'cucina',
 '{"causa":"temperatura sopra 65-70°C: l actina è denaturata, i muscoli si contraggono e perdono acqua. Fix: abbassare la temperatura target (sous-vide a 54-57°C) o accettare il compromesso con tagli ricchi di collagene (>70°C per la conversione in gelatina)"}'),
('err-brodo-torbido',    'Errore', 'Brodo torbido e senza corpo', 'cucina',
 '{"causa":"bollitura forte (100°C): le proteine vengono agitate e disperse nell acqua invece di coagulare e affiorare. E non si forma abbastanza gelatina. Fix: fremito gentile (85-90°C), non bollitura."}'),
('err-uova-gommose',     'Errore', 'Uova strapazzate gommose', 'cucina',
 '{"causa":"temperatura troppo alta o cottura troppo lunga: l actina delle uova denatura sopra 70°C e la proteina diventa gommosa e rilascia acqua. Fix: fiamma bassa, togliere dal fuoco prima, usare sous-vide a 63-65°C per il controllo preciso"}');

-- ============================================================
-- ARCHI — Calore governa + CONNESSIONI TRASVERSALI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- processi
('prod-manzo-sousvide','proc-denaturazione-proteine','realizzato_da','{}'),
('prod-pollo-sousvide','proc-pastorizzazione-tempo-temp','realizzato_da','{}'),
('prod-uova-sousvide','proc-denaturazione-proteine','realizzato_da','{}'),
('prod-gelatina-brodo','proc-denaturazione-proteine','realizzato_da','{}'),

-- CALORE governa tutti
('fen-calore','prod-manzo-sousvide','si_manifesta_in',
 '{"target":"54-57°C × 1-4h (bistecca) o 48h (tagli collagene)","ruolo":"ogni grado decide quale proteina si denatura: la temperatura è il coltello del cuoco"}'),
('fen-calore','prod-pollo-sousvide','si_manifesta_in',
 '{"target":"63-65°C × 1-4h (pastorizzato = sicuro)","ruolo":"stesso risultato microbiologico di 74°C istantaneo, texture completamente diversa"}'),
('fen-calore','prod-uova-sousvide','si_manifesta_in',
 '{"target":"63-65°C × 45-60 min","ruolo":"la finestra tra coagulazione albume (63°C) e tuorlo (70°C) è l uovo perfetto"}'),
('fen-calore','prod-gelatina-brodo','si_manifesta_in',
 '{"target":"85-90°C × 4-8h (fremito, non bollitura)","ruolo":"collagene → gelatina: reazione lenta che vuole temperatura alta ma non bollitura"}'),

-- CONNESSIONE TRASVERSALE 1: pastorizzazione come ponte
-- La stessa cinetica tempo×temperatura governa yogurt, formaggi, uova pastorizzate
('proc-pastorizzazione-tempo-temp','prod-yogurt','si_manifesta_in',
 '{"nota":"il latte pastorizzato per lo yogurt: 72°C × 15 sec oppure 63°C × 30 min — stessa riduzione batterica, le proteine del latte si comportano diversamente"}'),

-- CONNESSIONE TRASVERSALE 2: il Q10 è lo stesso della fermentazione
-- (temperatura governa la cinetica biologica in modo esponenziale)
('proc-pastorizzazione-tempo-temp','proc-ferm-lattica','controllato_con',
 '{"nota":"la stessa cinetica logaritmica governa l attivazione batterica (fermentazione) e la loro inibizione (pastorizzazione): due facce della stessa legge"}'),

-- fallisce_come
('prod-manzo-sousvide','err-carne-secca-calda','fallisce_come','{}'),
('prod-gelatina-brodo','err-brodo-torbido','fallisce_come','{}'),
('prod-uova-sousvide','err-uova-gommose','fallisce_come','{}');
