-- CONCENTRAZIONE
-- Cross-disciplina: Brix sciroppi, ABV cocktail, TDS caffè, gradi zucchero gelato
-- Strumento: rifrattometro · alcolimetro · bilancia

-- Nodo già esistente nel seed ponte — solo archi aggiuntivi

INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- BAR
('fen-concentrazione', 'prod-sciroppo-semplice', 'si_manifesta_in',
 '{"target":"50-65° Brix (1:1 = 50°Bx, 2:1 = 66°Bx)","causa":"Il rapporto zucchero/acqua determina dolcezza, viscosità e shelf life dello sciroppo"}'),
('fen-concentrazione', 'prod-cocktail-sour', 'si_manifesta_in',
 '{"target":"ABV finale 14-18%","causa":"La diluizione con ghiaccio abbassa la concentrazione alcolica — misurabile con alcolimetro o calcolabile"}'),
-- CAFFÈ
('fen-concentrazione', 'prod-espresso', 'si_manifesta_in',
 '{"target":"TDS 7-12% · EY 18-22%","causa":"La concentrazione di solidi disciolti (TDS) è la grandezza che il rifrattometro misura nel caffè estratto"}'),
('fen-concentrazione', 'prod-caffe-filtro', 'si_manifesta_in',
 '{"target":"TDS 1,15-1,55% (SCA Gold Cup)","causa":"Il caffè filtro ben estratto ha una concentrazione di solidi precisa e misurabile"}'),
-- GELATERIA
('fen-concentrazione', 'prod-gelato-cioccolato', 'si_manifesta_in',
 '{"target":"Solidi totali 36-38% · zuccheri 22-26°Bx","causa":"La concentrazione di zuccheri governa il punto di congelamento e la cremosità del gelato"}'),
-- BAKERY
('fen-concentrazione', 'prod-pane-lievitazione', 'si_manifesta_in',
 '{"target":"Idratazione 60-85% (baker%) · sale 1,8-2,2%","causa":"La concentrazione degli ingredienti in baker% è il linguaggio universale del fornaio"}'),
-- CONNESSIONI FENOMENI
('fen-concentrazione', 'fen-crioscopia', 'influenza',
 '{"nota":"La concentrazione di soluti determina l abbassamento del punto di congelamento — i due fenomeni sono inseparabili nel gelato"}'),
('fen-concentrazione', 'fen-estrazione', 'influenza',
 '{"nota":"L estrazione è il processo che porta un soluto in soluzione — la concentrazione è il risultato misurabile"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
