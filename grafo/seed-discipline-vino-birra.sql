-- ============================================================
-- DISCIPLINE VINO e BIRRA
-- Aggiunge prodotti con dominio 'vino' e 'birra' agganciati
-- ai fenomeni esistenti. Così /disciplina/vino e /disciplina/birra
-- trovano i loro fenomeni attraverso i prodotti.
-- I fenomeni (tannini, malolattica, fermentazione, ecc.) esistono già
-- come trasversali/bar — qui li colleghiamo alle nuove discipline.
-- ============================================================

-- ── DISCIPLINA VINO ─────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-vino-rosso-disc', 'Prodotto', 'Vino rosso', 'vino',
 '{"target":"tannini 1-3 g/L · macerazione 1-3 settimane · pH 3,2-3,6 · MLF spesso completata","strumento":"pH-metro · analisi fenolica"}'),
('prod-vino-bianco-disc', 'Prodotto', 'Vino bianco', 'vino',
 '{"target":"acidita titolabile 5-8 g/L · pH 3,0-3,4 · MLF opzionale · zero contatto bucce","strumento":"pH-metro · acidita titolabile"}'),
('prod-spumante-disc', 'Prodotto', 'Spumante / Champagne', 'vino',
 '{"target":"CO2 5-6 bar (metodo classico) · zucchero residuo dosaggio · acidita alta per freschezza","strumento":"manometro · pH-metro"}'),
('prod-vino-orange-disc', 'Prodotto', 'Vino orange (macerato)', 'vino',
 '{"target":"macerazione bucce su vino bianco: tannini 0,5-1,5 g/L · colore ambrato · pH 3,2-3,6","strumento":"pH-metro · valutazione sensoriale"}'),
('prod-vino-dolce-disc', 'Prodotto', 'Vino dolce / passito', 'vino',
 '{"target":"zuccheri residui >45 g/L (abboccato) fino a >120 g/L (liquoroso) · fermentazione bloccata o parziale","strumento":"rifrattometro · analisi zuccheri"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-tannini', 'prod-vino-rosso-disc', 'si_manifesta_in',
 '{"target":"1-3 g/L","causa":"Macerazione estrae i polifenoli delle bucce: il tempo decide la struttura tannica"}'),
('fen-malolattica', 'prod-vino-rosso-disc', 'si_manifesta_in',
 '{"target":"malico <0,1 g/L","causa":"MLF quasi sempre completata nei rossi: ammorbidisce e stabilizza"}'),
('fen-malolattica', 'prod-vino-bianco-disc', 'si_manifesta_in',
 '{"target":"opzionale","causa":"Nei bianchi è una scelta stilistica: sì per morbidezza (Chardonnay), no per freschezza (Sauvignon)"}'),
('fen-fermentazione', 'prod-vino-rosso-disc', 'si_manifesta_in',
 '{"target":"18-28C · lieviti Saccharomyces cerevisiae · 7-14 giorni","causa":"Zuccheri dell uva in alcol e CO2: la temperatura governa velocità e profilo aromatico"}'),
('fen-fermentazione', 'prod-vino-bianco-disc', 'si_manifesta_in',
 '{"target":"14-18C (piu freddo per conservare aromi)","causa":"Fermentazione a freddo conserva gli esteri aromatici delicati dei bianchi"}'),
('fen-acidita', 'prod-vino-bianco-disc', 'si_manifesta_in',
 '{"target":"pH 3,0-3,4 · acidita titolabile 5-8 g/L","causa":"L acidita e la struttura portante del vino bianco: senza di essa e piatto e corto"}'),
('fen-acidita', 'prod-vino-rosso-disc', 'si_manifesta_in',
 '{"target":"pH 3,2-3,6","causa":"Nel rosso l acidita bilancia i tannini: un vino tannico senza acidita e duro e senza freschezza"}'),
('fen-ossidazione', 'prod-vino-rosso-disc', 'si_manifesta_in',
 '{"target":"ossidazione controllata in rovere","causa":"I tannini proteggono il vino e permettono l affinamento: i polifenoli sono antiossidanti naturali"}'),
('fen-carbonatazione', 'prod-spumante-disc', 'si_manifesta_in',
 '{"target":"5-6 bar CO2","causa":"Seconda fermentazione in bottiglia (metodo classico) o in autoclave (Charmat): la CO2 resta intrappolata sotto pressione"}'),
('fen-tannini', 'prod-vino-orange-disc', 'si_manifesta_in',
 '{"target":"0,5-1,5 g/L (meno del rosso)","causa":"Macerazione delle bucce su vino bianco: struttura tannica insolita per un bianco"}');

-- ── DISCIPLINA BIRRA ────────────────────────────────────────
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-birra-lager-disc', 'Prodotto', 'Lager / Pilsner', 'birra',
 '{"target":"IBU 15-30 · ABV 4-5% · fermentazione bassa 8-12C · lagering 4-6C per 4-8 settimane","strumento":"termometro · IBU · alcolimetro"}'),
('prod-birra-ale-disc', 'Prodotto', 'Ale (fermentazione alta)', 'birra',
 '{"target":"IBU variabile · ABV 4-8% · fermentazione alta 16-22C · profilo aromatico piu complesso della lager","strumento":"termometro · IBU"}'),
('prod-birra-ipa-disc', 'Prodotto', 'IPA (India Pale Ale)', 'birra',
 '{"target":"IBU 40-70 · luppolo aggiunto in piu momenti · dry-hop a freddo per aroma senza amaro","strumento":"IBU · degustazione"}'),
('prod-birra-stout-disc', 'Prodotto', 'Stout / Porter', 'birra',
 '{"target":"malto tostato o caramellato · IBU 30-50 · colore scuro da Maillard sul malto · ABV 4-8%","strumento":"EBC (colore) · IBU"}'),
('prod-birra-weizen-disc', 'Prodotto', 'Weizen / Hefeweizen', 'birra',
 '{"target":"frumento 50%+ · lieviti Weizen producono isoamilacetato (banana) e guaiacolo (chiodi di garofano) · non filtrata","strumento":"termometro fermentazione · degustazione"}'),
('prod-birra-sour-disc', 'Prodotto', 'Birra acida / Lambic', 'birra',
 '{"target":"pH 3,2-3,8 · fermentazione spontanea o con lattobacilli · acidita lattica e acetica · IBU basso","strumento":"pH-metro · acidita titolabile"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione', 'prod-birra-lager-disc', 'si_manifesta_in',
 '{"target":"8-12C · lieviti Saccharomyces pastorianus","causa":"Fermentazione bassa: piu lenta e pulita, meno esteri, profilo neutro e bilanciato"}'),
('fen-fermentazione', 'prod-birra-ale-disc', 'si_manifesta_in',
 '{"target":"16-22C · lieviti Saccharomyces cerevisiae","causa":"Fermentazione alta: piu rapida, produce piu esteri e fenoli che danno complessita aromatica"}'),
('fen-fermentazione', 'prod-birra-weizen-disc', 'si_manifesta_in',
 '{"target":"18-22C · lieviti Weizen","causa":"I lieviti Weizen producono caratteristici esteri (banana) e fenoli (chiodi di garofano) a temperature specifiche"}'),
('fen-amilolisi', 'prod-birra-lager-disc', 'si_manifesta_in',
 '{"target":"mash 62-72C · beta-amilasi 62-65C, alfa-amilasi 68-72C","causa":"La temperatura di mash decide la fermentabilita del mosto: piu bassa = birra secca, piu alta = corpo pieno"}'),
('fen-amilolisi', 'prod-birra-ale-disc', 'si_manifesta_in',
 '{"target":"mash 64-68C","causa":"Amilasi dell orzo maltato convertono l amido in zuccheri fermentabili: la finestra di temperatura e fondamentale"}'),
('fen-estrazione', 'prod-birra-ipa-disc', 'si_manifesta_in',
 '{"target":"alfa-acidi luppolo isomerizzati · dry-hop 0-4C 3-7 giorni","causa":"Il luppolo rilascia amaro (bollitura lunga) e aromi (dry-hop a freddo): due estrazioni diverse per due risultati opposti"}'),
('fen-maillard', 'prod-birra-stout-disc', 'si_manifesta_in',
 '{"target":"malto tostato a 150-220C","causa":"La malteria applica Maillard al malto tostato: crea colore, aroma di caffè/cioccolato che caratterizzano stout e porter"}'),
('fen-acidita', 'prod-birra-sour-disc', 'si_manifesta_in',
 '{"target":"pH 3,2-3,8 · acidita lattica/acetica","causa":"Fermentazione con lattobacilli e acetobatteri produce acidi organici: e la fisica dell acidita applicata alla birra"}'),
('fen-carbonatazione', 'prod-birra-lager-disc', 'si_manifesta_in',
 '{"target":"CO2 2,2-2,8 volumi · rifermentazione in bottiglia o carbonatazione forzata","causa":"La CO2 porta freschezza e mouthfeel alla lager: troppa = aggressiva, troppo poca = piatta"}');
