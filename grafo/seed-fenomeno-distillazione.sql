-- ============================================================
-- FENOMENO: Distillazione
-- Regola di partizione: OK — numero proprio + strumento indipendente
-- Numero-bersaglio: punto di ebollizione etanolo 78,4C (vs acqua 100C)
--   ABV cuore: 65-75% (poi diluito a 40-60% all imbottigliamento)
--   Tagli: teste <64,7C (metanolo), cuore ~78,4C, code >85C (fusel oils)
-- Strumento: termometro + alcolimetro (idrometro)
-- DISTINTA da fermentazione (produce l alcol) e da estrazione (solvente).
-- Si manifesta in: whisky, rum, gin, grappa, tequila, vodka
-- Fonti: Copenhagen Distillery; ScienceInsights (distillazione alcol);
--   The Whisky School (tagli testa/cuore/coda); Difford's Guide.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-distillazione', 'Fenomeno', 'Distillazione', 'bar',
 '{"tipo":"fisico",
   "numero_bersaglio":"ebollizione etanolo 78,4C vs acqua 100C · ABV cuore 65-75% · tagli: teste (metanolo, <64,7C), cuore (etanolo + esteri, ~78,4C), code (fusel oils, >85C)",
   "strumento":"termometro · alcolimetro (idrometro)",
   "scheda":"La distillazione separa i componenti di una miscela sfruttando le differenze di punto di ebollizione. L'etanolo bolle a 78,4°C, l'acqua a 100°C: riscaldando un fermentato si ottiene un vapore più ricco in alcol che, condensato, produce il distillato. In realtà è più complesso: le teste (metanolo, acetati) passano per prime e si scartano, il cuore è la parte nobile, le code contengono alcoli pesanti. Il taglio tra cuore e code è la decisione tecnica più importante del distillatore. Per i gin, le botaniche cedono i propri aromi al vapore alcolico durante la distillazione (re-distillazione) o vengono macerate nel liquido prima (cold compounding) — due metodi con profili aromatici radicalmente diversi."}');

-- ── DISTILLATI come prodotti ────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-gin', 'Prodotto', 'Gin', 'bar',
 '{"target":"ABV 37,5-47% (tipico 40%) · botaniche: ginepro obbligatorio + agrumi, coriandolo, angelica · estrazione botaniche per macerazione o re-distillazione · London Dry: solo re-distillazione",
   "strumento":"alcolimetro · degustazione"}'),
('prod-rum', 'Prodotto', 'Rum', 'bar',
 '{"target":"ABV 37,5-80% (tipico 40-46%) · base: melassa o succo di canna fermentato · pot still (rum scuro, pesante) vs column still (rum bianco, leggero) · invecchiamento in rovere contribuisce al colore e aroma",
   "strumento":"alcolimetro"}'),
('prod-whisky', 'Prodotto', 'Whisky / Whiskey', 'bar',
 '{"target":"ABV 40-46% imbottigliato (distillato a 65-70%) · invecchiamento minimo 3 anni in legno · malto d orzo (scotch) vs mais (bourbon) vs segale (rye) · il legno cede vanillina, tannini, colore",
   "strumento":"alcolimetro · tempo (anni di invecchiamento)"}'),
('prod-vodka', 'Prodotto', 'Vodka', 'bar',
 '{"target":"ABV 40% · distillata piu volte a >95% ABV poi diluita · neutrale per definizione (minimo congeners) · base: grano, patate, mais, barbabietola",
   "strumento":"alcolimetro · analisi congeners"}'),
('prod-tequila', 'Prodotto', 'Tequila / Mezcal', 'bar',
 '{"target":"tequila: ABV 38-55% · solo agave blu (Jalisco) · cotta in autoclave (tequila) o sotto terra con carbone (mezcal, sapore affumicato) · doppia distillazione",
   "strumento":"alcolimetro"}'),
('prod-grappa', 'Prodotto', 'Grappa', 'bar',
 '{"target":"ABV 37,5-60% · distillata dalle vinacce (bucce+semi dell uva dopo la pressatura) · italiana per definizione · invecchiata (dorata) o giovane (bianca)",
   "strumento":"alcolimetro"}'),
('prod-cognac', 'Prodotto', 'Cognac / Armagnac', 'bar',
 '{"target":"ABV 40% imbottigliato · doppia distillazione in pot still (Cognac) o continua colonna (Armagnac) · invecchiamento in rovere limousin minimo 2 anni · gradi XO, VSOP, VS",
   "strumento":"alcolimetro · tempo invecchiamento"}');

-- ── ARCHI: distillazione si_manifesta_in ────────────────────────
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-distillazione', 'prod-gin', 'si_manifesta_in',
 '{"target":"65-75% ABV al cuore → 40-47% imbottigliato","causa":"Il gin e un distillato di grano neutro ri-distillato con le botaniche: e la seconda distillazione a dare il carattere del ginepro. La qualita del taglio determina la pulizia del profilo"}'),
('fen-distillazione', 'prod-rum', 'si_manifesta_in',
 '{"target":"65-75% ABV cuore","causa":"Pot still (distillazione in lotti) conserva piu congeners: rum scuro e complesso. Column still (continua) porta piu pulizia: rum bianco e leggero. La scelta dello still decide il carattere"}'),
('fen-distillazione', 'prod-whisky', 'si_manifesta_in',
 '{"target":"65-70% ABV al cuore","causa":"Il taglio del cuore e l arte del distillatore: piu hearts includi, piu complessita ma anche piu rischio di off-flavors. Il legno poi trasforma tutto in 3-25 anni"}'),
('fen-distillazione', 'prod-vodka', 'si_manifesta_in',
 '{"target":">95% ABV multipla distillazione → 40% finale","causa":"La vodka e distillata il piu a lungo possibile per eliminare quasi tutti i congeners: lo scopo e la neutralita. Il taglio e preciso e tecnico, non artistico"}'),
('fen-distillazione', 'prod-tequila', 'si_manifesta_in',
 '{"target":"doppia distillazione, ABV 38-55%","causa":"Prima distillazione (ordinario, ~25% ABV), seconda distillazione (tequila, 55-65% ABV) poi diluita. Il mezcal usa gli stessi tagli ma con agave cotta diversamente"}'),
('fen-distillazione', 'prod-grappa', 'si_manifesta_in',
 '{"target":"ABV 37,5-60%","causa":"Le vinacce hanno meno liquido del vino: la distillazione deve essere piu attenta per non bruciare. Il taglio e critico per evitare i fusel oils delle code"}'),
('fen-distillazione', 'prod-cognac', 'si_manifesta_in',
 '{"target":"doppia distillazione, ABV 40%","causa":"Il Cognac usa il pot still charentais in doppio passaggio: prima distillazione al 30% ABV, seconda al 70% (la bonne chauffe). Solo il cuore di entrambe le passate va in barrique"}');

-- ── ERRORI ──────────────────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-taglio-sbagliato', 'Errore', 'Taglio sbagliato (teste o code nel cuore)', 'bar',
 '{"causa":"Se si include troppo delle teste: odore di solvente, note pungenti. Se si include troppo delle code: sapore oleoso, pesante, amaro da fusel oils","soluzione":"Affinare il taglio con esperienza sensoriale: odore e gusto al momento del passaggio dalla testa al cuore e dal cuore alla coda"}'),
('err-fusel-oils', 'Errore', 'Fusel oils eccessivi (off-flavor pesante)', 'bar',
 '{"causa":"Fermentazione ad alta temperatura o troppo rapida produce piu alcoli superiori (isobutanolo, isoamilico) che finiscono nelle code e, se il taglio e largo, nel distillato","soluzione":"Fermentazione controllata (18-25C), taglio preciso, eventuale re-distillazione"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-distillazione', 'err-taglio-sbagliato', 'fallisce_come',
 '{"causa":"Tagli imprecisi: teste o code inquinano il cuore"}'),
('fen-distillazione', 'err-fusel-oils', 'fallisce_come',
 '{"causa":"Fermentazione calda produce fusel oils che contaminano il distillato"}');

-- ── CONNESSIONI CROSS-DOMINIO ────────────────────────────────────
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-distillazione', 'fen-fermentazione', 'influenza',
 '{"nota":"La distillazione concentra cio che la fermentazione ha prodotto: senza alcol fermentato non c e niente da distillare. E la seconda fase, non la prima. La qualita del fermentato entra nel distillato"}'),
('fen-distillazione', 'fen-estrazione', 'influenza',
 '{"nota":"Nel gin le botaniche vengono estratte durante la ri-distillazione: e estrazione termica, non a freddo. I composti aromatici del ginepro e degli agrumi passano nella fase vapore e si ritrovano nel distillato"}'),
('fen-distillazione', 'fen-concentrazione', 'influenza',
 '{"nota":"La distillazione e concentrazione per evaporazione selettiva: si toglie acqua aumentando la percentuale di etanolo. E lo stesso principio della riduzione, applicato all alcol invece che al sapore"}'),
('fen-distillazione', 'fen-ossidazione', 'influenza',
 '{"nota":"L invecchiamento in legno e ossidazione controllata: l aria che entra attraverso il rovere trasforma i congeners in molecole piu complesse (vanillina, lattoni, tannini dolci). Senza ossidazione, un whisky e solo distillato"}');
