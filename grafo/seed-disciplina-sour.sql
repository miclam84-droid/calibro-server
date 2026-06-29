-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: la famiglia SOUR (mixology)
-- Non nuovi fenomeni: cocktail reali come PROVA, agganciati ai fenomeni
-- che già li governano (acidità + concentrazione + calore/diluizione).
-- Numeri da Arnold, Liquid Intelligence (template sour verificato).
-- Mostra: un solo template chimico, molti cocktail; e che i 3 fenomeni
-- si incontrano sullo stesso prodotto (come la confettura per la cucina).
-- ============================================================

-- ---- IL TEMPLATE come processo condiviso -------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-template-sour', 'Processo', 'Template sour', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Base alcolica + acido + zucchero, shakerato col ghiaccio. Spec di Arnold: ~2 oz distillato (40%), 0,75 oz agrume fresco (pH 2,2-2,5), 0,75 oz sciroppo 1:1. Rapporto zucchero:acido ~2:1 in peso. ABV finale 18-22%. Daiquiri, Margarita, Whiskey Sour, Pisco Sour sono lo stesso template con basi diverse. Equilibrio: non deve risultare né dolce né acido, il finale è il distillato."}');

-- ---- I COCKTAIL come prova (stessa equazione, basi diverse) -
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-daiquiri',     'Prodotto', 'Daiquiri', 'bar', '{"base":"rum bianco","spec":"rum + lime + zucchero, shakerato up"}'),
('prod-margarita',    'Prodotto', 'Margarita', 'bar', '{"base":"tequila","spec":"tequila + lime + triple sec"}'),
('prod-whiskey-sour', 'Prodotto', 'Whiskey Sour', 'bar', '{"base":"bourbon","spec":"bourbon + limone + zucchero (+ albume opzionale)"}'),
('prod-gimlet',       'Prodotto', 'Gimlet', 'bar', '{"base":"gin","spec":"gin + lime + zucchero, più secco"}');

-- ---- ERRORE specifico dello squilibrio --------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-sour-squilibrato', 'Errore', 'Sour squilibrato', 'bar',
 '{"causa":"rapporto zucchero:acido lontano da ~2:1, oppure ABV fuori 18-22% per diluizione sbagliata"}');

-- ============================================================
-- ARCHI — ogni cocktail aggancia i 3 fenomeni che lo governano
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- il template è realizzato_da del prodotto-sour generico, e usa i 3 fenomeni
('prod-sour','proc-template-sour','realizzato_da','{}'),
-- ACIDITÀ governa l'acido del sour (i cocktail si manifestano qui)
('fen-acidita','prod-daiquiri','si_manifesta_in','{"target":"~1,0-1,2% titolabile (lime)","ruolo":"acido per la brillantezza"}'),
('fen-acidita','prod-margarita','si_manifesta_in','{"target":"~1,0-1,2% (lime)","ruolo":"acido bilanciato dal triple sec"}'),
('fen-acidita','prod-whiskey-sour','si_manifesta_in','{"target":"~1,0% (limone)","ruolo":"acido che taglia il dolce del bourbon"}'),
('fen-acidita','prod-gimlet','si_manifesta_in','{"target":"~1,2% (lime)","ruolo":"più acido, meno zucchero"}'),
-- CONCENTRAZIONE governa lo zucchero (rapporto ~2:1 su acido)
('fen-concentrazione','prod-daiquiri','si_manifesta_in','{"target":"zucchero:acido ~2:1","ruolo":"sciroppo che bilancia il lime"}'),
('fen-concentrazione','prod-whiskey-sour','si_manifesta_in','{"target":"zucchero:acido ~2:1","ruolo":"dolce di sostegno, non protagonista"}'),
-- CALORE governa la diluizione/temperatura dello shake
('fen-calore','prod-daiquiri','si_manifesta_in','{"target":"~27% diluizione (shakerato), ABV finale 18-22%","ruolo":"il freddo serve più zucchero alla percezione"}'),
('fen-calore','prod-margarita','si_manifesta_in','{"target":"shakerato, ABV finale ~18-20%","ruolo":"diluizione e freddo insieme"}'),
-- il template realizza tutti i cocktail
('proc-template-sour','prod-daiquiri','realizzato_da','{}'),
('proc-template-sour','prod-margarita','realizzato_da','{}'),
('proc-template-sour','prod-whiskey-sour','realizzato_da','{}'),
('proc-template-sour','prod-gimlet','realizzato_da','{}'),
-- fallisce_come
('prod-daiquiri','err-sour-squilibrato','fallisce_come','{}'),
('prod-margarita','err-sour-squilibrato','fallisce_come','{}');
