-- ============================================================
-- FENOMENO MAILLARD — primo fenomeno costruito CON LA REGOLA.
-- Numero-bersaglio: soglia ~140-165°C (imbrunimento rapido), pH-dipendente
-- (sopra pH 6 accelera, sotto rallenta). Strumento: termometro + pHmetro.
-- tipo: fisico-chimico. Passa la regola di partizione.
-- Scoperta strutturale: usa la temperatura (di Calore) e il pH (di Acidità).
-- ============================================================

-- ---- NODO CENTRALE -----------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-maillard', 'Fenomeno', 'Reazione di Maillard', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"La reazione di Maillard è la condensazione tra un gruppo amminico (aminoacidi liberi) e un gruppo carbonilico (zuccheri riducenti) ad alta temperatura. Produce centinaia di composti aromatici — pirazine, furani, maltolo — e i pigmenti bruni (melanoidine). Non è caramellizzazione: richiede proteine oltre agli zuccheri. Tre condizioni sono necessarie: temperatura >140°C, superficie asciutta (l'acqua non supera i 100°C), e presenza di zuccheri riducenti e aminoacidi. Questa è la ragione per cui l'umidità inibisce la doratura: asciugare la superficie prima di cuocere non è un dettaglio estetico, è una condizione fisica. Il pH alcalino (bicarbonato, idrossido di sodio nel brezel) accelera la reazione — da qui il colore intenso tipico dei prodotti da forno alcalini.","numero_bersaglio":"soglia 140-165°C, pH>6 accelera"}');

-- ---- CALCOLI / PARAMETRI (misurano il fenomeno) ------------
-- riusa cal-q10 (temperatura) e cal-ph? no: dichiaro i parametri propri ma li collego
INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-soglia-maillard', 'Calcolo', 'Soglia di imbrunimento (°C)', 'trasversale',
 '{"tipo":"fisico-chimico","nota":"140-165°C zona rapida; raddoppia ogni 10°C"}');

-- ---- PROCESSI ----------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-imbrunimento', 'Processo', 'Imbrunimento non-enzimatico', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"La reazione di Maillard è la condensazione tra un gruppo amminico (aminoacidi liberi) e un gruppo carbonilico (zuccheri riducenti) ad alta temperatura. Produce centinaia di composti aromatici — pirazine, furani, maltolo — e i pigmenti bruni (melanoidine). Non è caramellizzazione: richiede proteine oltre agli zuccheri. Tre condizioni sono necessarie: temperatura >140°C, superficie asciutta (l'acqua non supera i 100°C), e presenza di zuccheri riducenti e aminoacidi. Questa è la ragione per cui l'umidità inibisce la doratura: asciugare la superficie prima di cuocere non è un dettaglio estetico, è una condizione fisica. Il pH alcalino (bicarbonato, idrossido di sodio nel brezel) accelera la reazione — da qui il colore intenso tipico dei prodotti da forno alcalini."}');

-- ---- PRODOTTI (dove si manifesta — le discipline EMERGONO) -
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-carne-rosolata', 'Prodotto', 'Carne rosolata', 'cucina', '{}'),
('prod-caffe-tostato',  'Prodotto', 'Caffè in tostatura', 'caffetteria', '{}'),
('prod-cipolla-caram',  'Prodotto', 'Cipolla caramellata', 'cucina', '{}'),
('prod-birra-scura',    'Prodotto', 'Malto / birra scura', 'fermentazione', '{}');
-- prod-impasto (crosta del pane) e prod-pizza-nap esistono già: Maillard li tocca

-- ---- ERRORI ------------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-carne-grigia',  'Errore', 'Carne grigia, non rosolata', 'cucina', '{"causa":"superficie bagnata o padella sotto i 140°C: resta a 100°C, niente Maillard"}'),
('err-crosta-pallida','Errore', 'Crosta pallida', 'bakery', '{"causa":"forno troppo basso o impasto troppo acido: imbrunimento lento"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- misurato_da (i parametri propri + la SCOPERTA STRUTTURALE: usa temperatura e pH di altri fenomeni)
('fen-maillard','cal-soglia-maillard','misurato_da','{}'),
('fen-maillard','cal-q10','misurato_da','{"nota":"la temperatura governa la velocità (raddoppia ogni 10°C)"}'),
('fen-maillard','cal-ph','misurato_da','{"nota":"pH alto accelera, acido rallenta — leva condivisa con Acidità"}'),
-- realizzato_da
('fen-maillard','proc-imbrunimento','realizzato_da','{}'),
-- si_manifesta_in (le discipline emergono: cucina, caffetteria, fermentazione, panificazione)
('fen-maillard','prod-carne-rosolata','si_manifesta_in','{"target":"superficie >140°C, asciutta","ruolo":"crosta saporita, composti tostati"}'),
('fen-maillard','prod-caffe-tostato','si_manifesta_in','{"target":"190-230°C in tostatura","ruolo":"aromi di tostatura, colore"}'),
('fen-maillard','prod-cipolla-caram','si_manifesta_in','{"target":"a fuoco medio, lenta","ruolo":"dolcezza e bruno da zuccheri+amminoacidi"}'),
('fen-maillard','prod-birra-scura','si_manifesta_in','{"target":"maltazione/tostatura del grano","ruolo":"colore e note di caffè/cioccolato del malto"}'),
('fen-maillard','prod-impasto','si_manifesta_in','{"target":"crosta >150°C","ruolo":"colore e aroma della crosta del pane"}'),
('fen-maillard','prod-pizza-nap','si_manifesta_in','{"target":"430°C, leopardatura","ruolo":"le macchie brune del cornicione"}'),
-- fallisce_come
('prod-carne-rosolata','err-carne-grigia','fallisce_come','{}'),
('prod-impasto','err-crosta-pallida','fallisce_come','{}');
