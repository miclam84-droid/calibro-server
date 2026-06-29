-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: FERMENTATI / CUCINA
-- Arricchisce prod-crauti, prod-yogurt già presenti con numeri reali.
-- Aggiunge: kimchi, miso, kombucha cucina, pickles/salamoia.
-- Fenomeni: Fermentazione (biologico) + Acidità (effetto) + Osmosi (sale).
-- I tre fenomeni si incontrano sugli stessi prodotti — come confettura in cucina.
-- Numeri: USDA/FDA/NCBI/Katz verificati.
-- ============================================================

-- ---- NUOVI PRODOTTI ----------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-kimchi',    'Prodotto', 'Kimchi', 'cucina',
 '{"spec":"sale ~3%, fermentazione a ~10°C, pH finale 4,2-4,5","note":"acidità ottimale 0,4-0,8% acido lattico"}'),
('prod-miso',      'Prodotto', 'Miso', 'cucina',
 '{"spec":"soia + koji (Aspergillus oryzae) + sale, mesi/anni","note":"fermentazione fungina + lattica; pH 4,5-5,5 a maturità"}'),
('prod-pickles',   'Prodotto', 'Pickles / salamoia lattica', 'cucina',
 '{"spec":"salamoia 2-3% sale, verdure sommerse, 7-14 giorni a 20°C","note":"pH sicuro <4,6 entro pochi giorni"}');

-- ---- PROCESSI ----------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-salatura-secca', 'Processo', 'Salatura secca (dry brining)', 'cucina',
 '{"tipo":"fisico-chimico","scheda":"Sale aggiunto direttamente alle verdure tritate. L osmosi tira l acqua fuori dalle cellule: si forma la salamoia naturale. Il cavolo del sauerkraut rilascia abbastanza liquido da sommergersi da solo se pressato. Sale 2-2,5% sul peso delle verdure. Percentuali in peso, mai in volume (un cucchiaio di sale fino pesa il doppio di uno di sale grosso)."}'),
('proc-salamoia-brine',  'Processo', 'Salamoia (brine fermentation)', 'cucina',
 '{"tipo":"fisico-chimico","scheda":"Sale disciolto in acqua (2-3%), verdure sommerse. Per verdure intere o tagliate grosse che non rilasciano abbastanza liquido. La salamoia crea la stessa selezione batterica della salatura secca: Lactobacillus prospera, patogeni soppressi."}');

-- ---- ERRORI ------------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-ferm-troppo-sale',  'Errore', 'Fermentato bloccato (troppo sale)', 'cucina',
 '{"causa":"sale >3,5-4%: inibisce anche i Lactobacillus. Fermentazione lenta o assente. Il pH non scende. Fix: ridurre il sale al 2-2,5%."}'),
('err-ferm-muffa',        'Errore', 'Muffa / deterioramento', 'cucina',
 '{"causa":"verdure non sommerse: esposizione all aria permette muffe. Il film bianco superficiale (kahm yeast) è innocuo; muffa colorata = scartare. Fix: tenere sempre sommerse."}'),
('err-verdure-molli',        'Errore', 'Verdure molli / pappa', 'cucina',
 '{"causa":"temperatura troppo alta (>25°C) o fermentazione troppo lunga. I pectinasi degradano la cellulosa. Fix: fermentare a 18-20°C, assaggiare prima del punto ottimale."}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- processi
('prod-crauti','proc-salatura-secca','realizzato_da','{}'),
('prod-kimchi','proc-salatura-secca','realizzato_da','{}'),
('prod-pickles','proc-salamoia-brine','realizzato_da','{}'),

-- FERMENTAZIONE governa (i prod-crauti e prod-yogurt già agganciati nel seed-fermentazione)
('fen-fermentazione','prod-kimchi','si_manifesta_in',
 '{"target":"sale ~3%, pH finale 4,2-4,5, acido lattico 0,4-0,8%","ruolo":"fermentazione lattica selettiva a temperatura bassa (~10°C)"}'),
('fen-fermentazione','prod-miso','si_manifesta_in',
 '{"target":"koji + sale, mesi-anni, pH 4,5-5,5","ruolo":"fermentazione fungina (koji) poi lattica: umami + conservazione"}'),
('fen-fermentazione','prod-pickles','si_manifesta_in',
 '{"target":"2-3% sale, pH <4,6 in pochi giorni","ruolo":"Lactobacillus abbassa il pH sotto la soglia di sicurezza"}'),

-- ACIDITÀ: effetto della fermentazione, ma misurabile al banco (pHmetro)
('fen-acidita','prod-crauti','si_manifesta_in',
 '{"target":"pH 3,4-4,1 (lieve 2 sett., forte 4+ sett.), acido lattico 1,5-2,5%","ruolo":"il pH è l orologio e il metro di sicurezza del fermentato"}'),
('fen-acidita','prod-kimchi','si_manifesta_in',
 '{"target":"pH 4,2-4,5 ottimale","ruolo":"pH troppo basso (<3,8) = troppo acido, inaccettabile; troppo alto (>4,6) = non sicuro"}'),
('fen-acidita','prod-pickles','si_manifesta_in',
 '{"target":"pH <4,6 soglia di sicurezza FDA","ruolo":"sotto 4,6 il botulinum non cresce; sotto 4,0 inibiti quasi tutti i patogeni"}'),

-- OSMOSI: il sale tira l acqua fuori dalle cellule (stesso fenomeno della salamoia già nel grafo)
('fen-osmosi','prod-crauti','si_manifesta_in',
 '{"target":"2-2,5% sale sul peso del cavolo","ruolo":"l osmosi forma la salamoia naturale: senza acqua aggiunta"}'),
('fen-osmosi','prod-kimchi','si_manifesta_in',
 '{"target":"~3% sale","ruolo":"pressione osmotica seleziona i Lactobacillus e ammorbidisce le verdure"}'),
('fen-osmosi','prod-pickles','si_manifesta_in',
 '{"target":"salamoia 2-3%","ruolo":"stessa legge della salamoia carne: salt draw, pressione osmotica"}'),

-- fallisce_come
('prod-crauti','err-ferm-troppo-sale','fallisce_come','{}'),
('prod-crauti','err-ferm-muffa','fallisce_come','{}'),
('prod-kimchi','err-verdure-molli','fallisce_come','{}'),
('prod-pickles','err-ferm-muffa','fallisce_come','{}');
