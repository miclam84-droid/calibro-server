-- ============================================================
-- GELATERIA — arricchimento prodotti
-- I fenomeni esistono già (crioscopia, montaggio/overrun, cristallizzazione,
-- gelatinizzazione, aw, emulsione). Mancano i prodotti specifici.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-gelato-cioccolato', 'Prodotto', 'Gelato al cioccolato', 'gelateria',
 '{"target":"PAC 260-310 · zuccheri bilanciati (saccarosio + destrosio) · cacao 20-24% sulla miscela · servizio -11/-13C",
   "strumento":"termometro · PAC calcolato"}'),
('prod-stracciatella', 'Prodotto', 'Stracciatella / fior di latte', 'gelateria',
 '{"target":"base fior di latte (latte+panna+zucchero) · overrun 25-35% · servizio -11/-13C · cioccolato fondente colato a filo durante il mantecamento (60-70C) per solidificare in scaglie",
   "strumento":"termometro · overrun meter"}'),
('prod-gelato-nocciola', 'Prodotto', 'Gelato alla nocciola (pasta di frutta secca)', 'gelateria',
 '{"target":"pasta nocciola 15-20% · grassi alti = PAC da ricalcolare · servizio -11/-13C · rischio irrancidimento (fen-ossidazione) se la pasta e vecchia",
   "strumento":"termometro · PAC"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-crioscopia', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"PAC 260-310","causa":"Il cacao ha zuccheri propri che contribuiscono al PAC: va ricalcolato quando si aggiunge. Un errore qui e il gelato troppo duro o che non congela"}'),
('fen-montaggio', 'prod-stracciatella', 'si_manifesta_in',
 '{"target":"overrun 25-35%","causa":"L aria incorporata nel mantecamento alleggerisce la texture. La stracciatella ha overrun basso per restare cremosa e densa — l aria non deve dominare"}'),
('fen-emulsione', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"emulsione grasso-acqua","causa":"Il gelato e un sistema emulsionato: i grassi del latte si disperdono nell acqua con l aiuto degli emulsionanti (spesso tuorlo o lecitina). Il cacao aggiunge altra fase grassa da tenere in emulsione"}'),
('fen-ossidazione', 'prod-gelato-nocciola', 'si_manifesta_in',
 '{"target":"FFA% nella pasta","causa":"I grassi insaturi della nocciola irrancidiscono: la pasta vecchia o mal conservata porta note rancide nel gelato. Stessa chimica dell olio — solo che qui e intrappolata nel congelato"}'),
('fen-cristallizzazione', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"cristalli ghiaccio <50 micron","causa":"Il cacao altera la struttura dei cristalli: la mantecatura rapida li tiene piccoli. Se il gelato al cioccolato si scongela e riconggela, i cristalli crescono e la texture diventa granulosa"}');

-- fix archi orfani preesistenti (prod-drink-freddo e prod-sousvide referenziati ma mai creati)
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-drink-freddo', 'Prodotto', 'Drink servito freddo / su ghiaccio', 'bar',
 '{"target":"servizio 0-5C · ghiaccio come diluente e raffreddante · concentrazione si abbassa durante il servizio","strumento":"termometro"}'),
('prod-sousvide', 'Prodotto', 'Cottura sous vide', 'cucina',
 '{"target":"temperatura core 55-85C secondo il taglio · tempo lungo (1-72h) · struttura controllata senza sovracottura","strumento":"circolatore termico · termometro a sonda"}')
ON CONFLICT DO NOTHING;
