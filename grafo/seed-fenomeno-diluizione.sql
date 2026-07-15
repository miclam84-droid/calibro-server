-- DILUIZIONE
-- Specifico Bar: la legge fondamentale del cocktail (Dave Arnold)
-- Strumento: bilancia · jigger

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-diluizione', 'Fenomeno', 'Diluizione', 'bar',
 '{"tipo":"fisico-chimico",
   "target":"Shake: 25-28% acqua sul volume finale · Stir: 18-22% · Build: 10-15%",
   "strumento":"Bilancia (peso prima/dopo) · jigger graduato",
   "principio":"Raffreddare e diluire sono lo stesso processo fisico: il ghiaccio assorbe calore dall''ambiente circostante (334 J per ogni grammo che si scioglie) e l''acqua prodotta entra nel drink. Non esiste raffreddamento senza diluizione, e la quantità di acqua aggiunta dipende da quanto ghiaccio si è sciolto. Lo shake produce più diluizione dello stir perché il movimento aumenta il contatto ghiaccio-liquido e accelera lo scioglimento. Un cocktail shakerato 10 secondi ha diluizione diversa da uno shakerato 15 secondi — e il profilo alcolico, la texture e la temperatura cambiano di conseguenza. La diluizione non è un effetto collaterale: è un ingrediente da calcolare. ABV finale = ABV iniziale × (volume iniziale / volume finale).",
   "formula":"% diluizione = (peso_finale - peso_iniziale) / peso_finale × 100 · ABV_finale = ABV_iniziale × (1 - %diluizione/100)",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;

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
 '{"nota":"Diluizione e concentrazione sono inversi: ogni aggiunta di acqua abbassa la concentrazione di tutti i soluti"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
