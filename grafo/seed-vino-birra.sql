-- ============================================================
-- VINO E BIRRA — disciplina + fenomeni propri
-- Fenomeni nuovi: fen-tannini, fen-malolattica
-- IBU non è un fenomeno (è una scala di misura dell'amaro da luppolo,
-- dipende da fen-estrazione già esistente) → aggiunto come prodotto con target IBU.
-- Fonti: ScienceDirect (tannini vino, astringenza); ScienceTopics (malolattica,
--   acido malico 1-10 g/L); BAKERpedia; America's Test Kitchen.
-- ============================================================

-- ── FENOMENO: Tannini / Polifenoli ──────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-tannini', 'Fenomeno', 'Tannini / Polifenoli', 'bar',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"tannini totali vino rosso ~1-3 g/L (fino a 4-5 g/L nei grandi rossi) · pH 3,2-3,6 modula l astringenza percepita · contatto con le bucce: giorni-settimane",
   "strumento":"analisi fenolica (mg/L) · pH-metro · valutazione sensoriale (astringenza)",
   "scheda":"I tannini sono polifenoli che si estraggono da bucce, semi e raspi dell uva durante la fermentazione alcolica. Non hanno sapore, ma si percepiscono tattilmente: si legano alle proteine della saliva e la precipitano, creando la sensazione di bocca secca e astringente tipica dei rossi strutturati. La concentrazione nei vini rossi va da 1 a 3 g/L, con punte di 4-5 g/L nei grandi vini da invecchiamento. Il pH amplifica o smorza la percezione: a pH piu basso (piu acido) l astringenza aumenta. Il tempo di contatto bucce-mosto e la leva principale: piu macera, piu tannini. Anche il rovere li cede durante l affinamento. Nell abbinamento, i tannini trovano equilibrio con le proteine dei cibi: un Barolo con la bistecca — le proteine della carne tamponano i tannini e li rendono morbidi."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-vino-rosso', 'Prodotto', 'Vino rosso (strutturato)', 'bar',
 '{"target":"tannini 1-3 g/L · macerazione 1-3 settimane (piu lunga = piu tannini) · pH 3,2-3,6",
   "strumento":"analisi fenolica · pH-metro · degustazione"}'),
('prod-vino-bianco', 'Prodotto', 'Vino bianco', 'bar',
 '{"target":"tannini quasi assenti (nessun contatto bucce) · acidita come struttura principale · pH 3,0-3,4",
   "strumento":"pH-metro · acidita titolabile"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-tannini', 'prod-vino-rosso', 'si_manifesta_in',
 '{"target":"1-3 g/L tannini","causa":"Macerazione a contatto con le bucce estrae i polifenoli: la durata decide la struttura tannica del vino. Il calore favorisce l estrazione"}'),
('fen-tannini', 'prod-vino-bianco', 'si_manifesta_in',
 '{"target":"quasi zero tannini","causa":"Fermentazione senza bucce: nessuna estrazione fenolica significativa. La struttura viene dall acidita, non dai tannini"}'),
('fen-tannini', 'fen-ossidazione', 'influenza',
 '{"nota":"I tannini sono antiossidanti naturali: proteggono il vino dall ossidazione e permettono l invecchiamento. Un vino povero di tannini ossida prima"}'),
('fen-tannini', 'fen-estrazione', 'influenza',
 '{"nota":"I tannini si estraggono con lo stesso meccanismo del caffe e del te: tempo, temperatura e solvente (l alcol favorisce l estrazione dai semi). E estrazione applicata alla vinificazione"}');

-- ── FENOMENO: Malolattica ────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-malolattica', 'Fenomeno', 'Fermentazione malolattica', 'bar',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"acido malico 1-10 g/L → acido lattico (MLF completa: malico <0,1 g/L) · pH sale di 0,1-0,3 unita · diacetile come marker (note di burro/vaniglia a concentrazioni basse)",
   "strumento":"cromatografia (acido malico/lattico) · pH-metro",
   "scheda":"La fermentazione malolattica (MLF) e una fermentazione secondaria batterica: batteri lattici (Oenococcus oeni e altri) convertono l acido malico (aspro, duro, di mela verde) in acido lattico (morbido, di yogurt) con rilascio di CO2. Il risultato e un vino con meno acidita totale, pH piu alto, sensazione di maggiore rotondita e corpo. Quasi tutti i vini rossi la fanno; nei bianchi e una scelta stilistica (Chardonnay borgognone si, Sauvignon blanc spesso no). Il marker della MLF completata e la scomparsa dell acido malico sotto 0,1 g/L. Il diacetile che si libera da note di burro e vaniglia a basse concentrazioni. La stessa chimica dei batteri lattici che acidificano lo yogurt e i crauti — qui applicata al vino per ammorbidire, non per conservare."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-chardonnay-mlf', 'Prodotto', 'Chardonnay (con MLF / beurre blanc)', 'bar',
 '{"target":"MLF completa: malico <0,1 g/L · pH 3,4-3,7 · diacetile 1-4 mg/L (burro/vaniglia)","strumento":"analisi malico · pH-metro"}'),
('prod-spumante-base', 'Prodotto', 'Vino base per spumante', 'bar',
 '{"target":"MLF spesso EVITATA per conservare acidita e freschezza · malico residuo mantenuto alto per la prise de mousse",
   "strumento":"analisi malico"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-malolattica', 'prod-chardonnay-mlf', 'si_manifesta_in',
 '{"target":"malico <0,1 g/L","causa":"MLF completa ammorbidisce il vino: da aspro e nervoso a cremoso e rotondo. Tipico dello Chardonnay della Borgogna e dei grandi bianchi strutturati"}'),
('fen-malolattica', 'prod-spumante-base', 'si_manifesta_in',
 '{"target":"malico conservato","causa":"Nello spumante l acidita serve per la seconda fermentazione e per la freschezza: la MLF viene bloccata con anidride solforosa per conservare il malico"}'),
('fen-malolattica', 'fen-fermentazione', 'influenza',
 '{"nota":"E una fermentazione secondaria, batterica, che segue quella alcolica (primaria, con lieviti). Due microorganismi diversi, due substrati diversi (zucchero prima, acido malico dopo), stesso principio biologico"}'),
('fen-malolattica', 'fen-acidita', 'influenza',
 '{"nota":"E il modo in cui il vino abbassa la sua acidita percepita: l acido malico (aspro) diventa lattico (morbido). Il pH sale di 0,1-0,3 unita — misurabile al banco con il pH-metro"}');

-- ── PRODOTTI BIRRA con IBU (amaro da luppolo, via estrazione) ───
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-birra-ipa', 'Prodotto', 'Birra IPA / amara (luppolo)', 'bar',
 '{"target":"IBU 40-70 (IPA) · luppolo aggiunto a inizio bollitura (amaro) o a freddo dry-hop (aroma) · alfa-acidi isomerizzati dalla bollitura sono la fonte dell amaro",
   "strumento":"IBU (International Bitterness Units) · valutazione sensoriale"}'),
('prod-birra-lager', 'Prodotto', 'Birra lager / pilsner', 'bar',
 '{"target":"IBU 10-25 · fermentazione bassa (8-14C) · lieviti lager (Saccharomyces pastorianus) · maturazione a freddo (lagering) 4-8C per 4-8 settimane",
   "strumento":"termometro · IBU"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-estrazione', 'prod-birra-ipa', 'si_manifesta_in',
 '{"target":"IBU 40-70","causa":"L amaro del luppolo e alfa-acidi isomerizzati dalla bollitura (estrazione termica): piu lunga la bollitura, piu amaro. Il dry-hop a freddo estrae gli aromi senza aggiungere amaro"}'),
('fen-fermentazione', 'prod-birra-lager', 'si_manifesta_in',
 '{"target":"8-14C fermentazione · lagering 4-8C","causa":"I lieviti lager lavorano al freddo: fermentazione piu lenta e pulita, poi maturazione a freddo che precipita le proteine e chiarifica la birra"}'),
('fen-amilolisi', 'prod-birra-ipa', 'si_manifesta_in',
 '{"target":"mash 65-68C per corpo pieno","causa":"La temperatura di mash decide la fermentabilita del mosto: piu alta = piu corpo residuo, piu bassa = birra secca. Nelle IPA spesso mash basso per secchezza che esalta il luppolo"}');
