-- DILUIZIONE
-- Specifico Bar: la legge fondamentale del cocktail (Dave Arnold)
-- Strumento: bilancia · jigger

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-diluizione', 'Fenomeno', 'Diluizione', 'bar',
 '{"tipo":"fisico-chimico",
   "target":"Shake: 25-28% acqua sul volume finale · Stir: 18-22% · Build: 10-15%",
   "strumento":"Bilancia (peso prima/dopo) · jigger graduato",
   "principio":"Shakerare o mescolare con ghiaccio non raffredda soltanto: aggiunge acqua al drink. Il ghiaccio si scioglie assorbendo calore (334 J/g di calore latente) e l acqua prodotta diluisce il cocktail. I due effetti sono inseparabili — non si può raffreddare senza diluire.",
   "formula":"% diluizione = (peso_finale - peso_iniziale) / peso_finale × 100 · ABV_finale = ABV_iniziale × (1 - %diluizione/100)",
   "settore":"f&b"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-diluizione', 'prod-sour', 'si_manifesta_in',
 '{"target":"~27% acqua (shake energico 10-12s)","causa":"Lo shake produce più contatto ghiaccio-liquido dello stir: più scioglimento, più diluizione, più raffreddamento"}'),
('fen-diluizione', 'prod-negroni', 'si_manifesta_in',
 '{"target":"~20-22% acqua (stir 30-40 giri)","causa":"Lo stir mescola senza aerare: meno scioglimento dello shake, diluizione più controllata e precisa"}'),
('fen-diluizione', 'prod-spritz', 'si_manifesta_in',
 '{"target":"10-15% acqua (dipende da tempo e tipo di ghiaccio)","causa":"I drink built sul ghiaccio si diluiscono lentamente mentre vengono consumati — il timing è un ingrediente"}'),
('fen-diluizione', 'fen-crioscopia', 'influenza',
 '{"nota":"La diluizione abbassa la concentrazione di alcol che a sua volta modifica il punto di congelamento del drink — i due fenomeni si intrecciano"}'),
('fen-diluizione', 'fen-concentrazione', 'influenza',
 '{"nota":"Diluizione e concentrazione sono inversi: ogni aggiunta di acqua abbassa la concentrazione di tutti i soluti"}');
