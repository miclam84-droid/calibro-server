-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: la famiglia STIRRED (mixology)
-- Mondo diverso dal sour: niente acido, tutto diluizione controllata.
-- Tre famiglie madri: Old Fashioned, Manhattan, Negroni.
-- Fenomeni: Calore (diluizione dello stir) + Concentrazione (ABV alto).
-- Il bitter/vermouth tocca Estrazione (composti amari in alcol).
-- Numeri da Arnold (formula diluizione) + fonti verificate.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-template-stirred', 'Processo', 'Template stirred', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Solo distillati + bitter/vermouth, niente succo. Lo stir raffredda e diluisce senza incorporare aria: il risultato è limpido, setoso, mai torbido. Diluizione ideale 20-25% del volume finale (formula Arnold: diluizione = -1,21 x ABV² + 1,26 x ABV + 0,145). Più è alcolico il drink, più diluizione serve per ammorbidire. Niente acido: l amaro struttura il bilanciamento al posto del limone."}');

-- ---- I COCKTAIL delle tre famiglie madri ----
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-negroni',      'Prodotto', 'Negroni', 'bar',
 '{"spec":"parti uguali gin + Campari + vermouth dolce; su roccia con scorza darancia","abv_finale":"~24%"}'),
('prod-manhattan',    'Prodotto', 'Manhattan', 'bar',
 '{"spec":"2 parti rye/bourbon + 1 parte vermouth dolce + 2 dash Angostura; up in coppa","abv_finale":"~28%"}'),
('prod-old-fashioned','Prodotto', 'Old Fashioned', 'bar',
 '{"spec":"bourbon/rye + zucchero + Angostura + scorza arancia; su roccia","abv_finale":"~32%"}'),
('prod-martini-dry',  'Prodotto', 'Martini Dry', 'bar',
 '{"spec":"gin + vermouth secco (rapporto variabile, da 3:1 a 8:1); up in coppa","abv_finale":"~30-35%"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-stirred-acquoso', 'Errore', 'Drink stirred acquoso/piatto', 'bar',
 '{"causa":"troppa diluizione (stir troppo lungo) o ghiaccio troppo bagnato: ABV finale cala sotto il target, il drink perde corpo"}'),
('err-stirred-caldo',   'Errore', 'Drink stirred non abbastanza freddo', 'bar',
 '{"causa":"stir troppo breve: non ha raggiunto i -2°C ottimali, manca la texture setosa"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- il template stirred è il processo condiviso
('prod-negroni','proc-template-stirred','realizzato_da','{}'),
('prod-manhattan','proc-template-stirred','realizzato_da','{}'),
('prod-old-fashioned','proc-template-stirred','realizzato_da','{}'),
('prod-martini-dry','proc-template-stirred','realizzato_da','{}'),

-- CALORE: la diluizione dello stir governa tutto (formula Arnold)
('fen-calore','prod-negroni','si_manifesta_in',
 '{"target":"20-22% diluizione, ABV finale ~24%","ruolo":"lo stir raffredda senza aria: limpido e setoso"}'),
('fen-calore','prod-manhattan','si_manifesta_in',
 '{"target":"22-25% diluizione, ABV finale ~28%, servire a -2°C","ruolo":"la diluizione ammorbidisce il rye senza perderlo"}'),
('fen-calore','prod-old-fashioned','si_manifesta_in',
 '{"target":"20% diluizione, ABV finale ~32%","ruolo":"il più forte: serve meno diluizione, la roccia completa sul bicchiere"}'),
('fen-calore','prod-martini-dry','si_manifesta_in',
 '{"target":"20-25% diluizione, ABV finale ~30-35%","ruolo":"freddo estremo: -2°C, la texture è tutto"}'),

-- CONCENTRAZIONE: ABV alto è la firma degli stirred
('fen-concentrazione','prod-old-fashioned','si_manifesta_in',
 '{"target":"ABV finale ~32%","ruolo":"il più concentrato degli stirred: lo zucchero ammorbidisce, non diluisce"}'),
('fen-concentrazione','prod-martini-dry','si_manifesta_in',
 '{"target":"ABV finale ~30-35%","ruolo":"rapporto gin:vermouth governa la concentrazione finale"}'),

-- ESTRAZIONE: bitter e vermouth portano composti amari estratti in alcol
-- (il ponte con fen-estrazione, proc-estrazione-alcol già esiste)
('fen-estrazione','prod-negroni','si_manifesta_in',
 '{"target":"Campari: estrazione alcolica di botaniche amare","ruolo":"il Campari E un amaro infuso: estrazione in alcol di erbe e radici"}'),
('fen-estrazione','prod-manhattan','si_manifesta_in',
 '{"target":"vermouth + bitters: aromi estratti in alcol/acqua","ruolo":"il vermouth è vino aromatizzato con botaniche in infusione"}'),

-- fallisce_come
('prod-negroni','err-stirred-acquoso','fallisce_come','{}'),
('prod-manhattan','err-stirred-caldo','fallisce_come','{}');
