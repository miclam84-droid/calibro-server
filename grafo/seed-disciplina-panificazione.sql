-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: PANIFICAZIONE
-- Le famiglie di pane come prova dei fenomeni (idratazione, struttura, fermentazione).
-- Ogni famiglia tocca Struttura + Calore + Fermentazione in modo diverso.
-- Idratazione (baker's %) è la leva che connette tutto.
-- Numeri da Hamelman, Robertson, mappa Calibro verificata.
-- ============================================================

-- ---- TEMPLATE per famiglia ---------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-baker-pct', 'Processo', 'Baker''s percentage', 'bakery',
 '{"tipo":"fisico-chimico","scheda":"Tutti gli ingredienti in percentuale sulla farina (= 100%). Idratazione = acqua/farina x 100. Il numero che governa tutto: più idratazione = glutine più estensibile = alveoli più grandi = mollica più aperta. Ma sopra ~85% la rete glutinica non regge più: le bolle scoppiano. Ogni stile risolve diversamente l equilibrio tra apertura e forza."}');

-- ---- LE FAMIGLIE (una per stile, con il numero-bersaglio) --
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-pizza-nap-adv', 'Prodotto', 'Pizza napoletana', 'bakery',
 '{"idratazione":"60-65%","note":"bassa idratazione = regge 430°C/90sec; farina 00 W260-280"}'),
-- prod-baguette già presente in seed-forno-prodotti (solo archi)
-- prod-ciabatta già presente in seed-forno-prodotti (solo archi)
('prod-pane-segale',   'Prodotto', 'Pane di segale', 'bakery',
 '{"idratazione":"80-100%","note":"segale senza glutine classico: amido e pentosani assorbono molta acqua; acidità alta fondamentale (pH 3,8-4,2) per struttura"}'),
('prod-sourdough-usa', 'Prodotto', 'Sourdough americano', 'bakery',
 '{"idratazione":"72-80%","note":"bulk + notte in frigo; crosta spessa, mollica aperta; acidità media-alta"}');
-- prod-bagel già presente in seed-forno-prodotti (solo archi)


-- ---- ERRORI panificazione ----------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-pane-piatto',     'Errore', 'Pane piatto (no sviluppo)', 'bakery',
 '{"causa":"glutine non sviluppato (impastamento insufficiente o farina debole) oppure fermentazione insufficiente: la CO2 non ha rete che la trattenga"}'),
('err-mollica-densa',   'Errore', 'Mollica densa e gommosa', 'bakery',
 '{"causa":"sotto-fermentazione o idratazione troppo bassa per lo stile; alveoli piccoli perché la CO2 non si espande"}'),
('err-crosta-pallida-p','Errore', 'Crosta pallida (panificazione)', 'bakery',
 '{"causa":"forno troppo basso (<220°C per pane normale) o impasto troppo acido: la reazione di Maillard rallenta in ambiente acido. Collegamento: fen-maillard + fen-fermentazione sullo stesso prodotto"}');

-- ============================================================
-- ARCHI — tre fenomeni per ogni famiglia
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- processo condiviso
('prod-pizza-nap-adv','proc-baker-pct','realizzato_da','{}'),
('prod-baguette','proc-baker-pct','realizzato_da','{}'),
('prod-ciabatta','proc-baker-pct','realizzato_da','{}'),
('prod-pane-segale','proc-baker-pct','realizzato_da','{}'),
('prod-sourdough-usa','proc-baker-pct','realizzato_da','{}'),
('prod-bagel','proc-baker-pct','realizzato_da','{}'),

-- STRUTTURA: idratazione governa il glutine e la mollica
('fen-struttura','prod-pizza-nap-adv','si_manifesta_in',
 '{"target":"60-65% idratazione, farina 00 W260+","ruolo":"bassa idratazione = rete glutinica fitta = regge la forma ad alta temp"}'),
('fen-struttura','prod-baguette','si_manifesta_in',
 '{"target":"68-75% idratazione","ruolo":"equilibrio tra estensibilità e forza: alveoli medi, crosta fragile"}'),
-- fen-struttura->prod-ciabatta già in seed-forno (solo aggiorno nel grafo)
('fen-struttura','prod-pane-segale','si_manifesta_in',
 '{"target":"80-100% idratazione, senza glutine classico","ruolo":"struttura da amido+pentosani, non dal glutine: serve acidità alta per gelatinizzare"}'),
-- fen-struttura->prod-bagel già in seed-forno

-- FERMENTAZIONE: lievitazione governa lo sviluppo
('fen-fermentazione','prod-pizza-nap-adv','si_manifesta_in',
 '{"target":"24-72h a freddo (retard), oppure 8h a temp ambiente","ruolo":"fermentazione lenta = sviluppo aromatico senza sovra-acidità"}'),
('fen-fermentazione','prod-sourdough-usa','si_manifesta_in',
 '{"target":"bulk 4-6h + notte in frigo, madre pH 3,7-3,9","ruolo":"acidità media-alta: acido lattico morbido + acetico pungente dal freddo"}'),
('fen-fermentazione','prod-pane-segale','si_manifesta_in',
 '{"target":"pH 3,8-4,2 fondamentale per la struttura","ruolo":"senza acidità alta l amido di segale non gelatinizza correttamente: crosta crolla"}'),

-- CALORE/MAILLARD: la crosta
('fen-calore','prod-pizza-nap-adv','si_manifesta_in',
 '{"target":"430°C / 90 secondi","ruolo":"calore estremo: vapore interno gonfia, Maillard rapido = leopardatura"}'),
-- fen-calore->prod-baguette già in seed-forno
('fen-maillard','prod-pizza-nap-adv','si_manifesta_in',
 '{"target":">140°C, leopardatura a 430°C","ruolo":"le macchie brune del cornicione: Maillard a temperatura estrema"}'),
('fen-maillard','prod-baguette','si_manifesta_in',
 '{"target":"crosta dorata a 240°C","ruolo":"il colore e l aroma della crosta: Maillard che richiede calore secco"}'),

-- fallisce_come
('prod-pizza-nap-adv','err-pane-piatto','fallisce_come','{}'),
('prod-baguette','err-crosta-pallida-p','fallisce_come','{}'),
('prod-sourdough-usa','err-mollica-densa','fallisce_come','{}'),
('prod-pane-segale','err-mollica-densa','fallisce_come','{}');
