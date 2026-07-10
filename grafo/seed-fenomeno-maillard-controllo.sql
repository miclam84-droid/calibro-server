INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-maillard-controllo', 'Fenomeno', 'Maillard — controllo e varianti', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"T di innesco: 140°C · zona ottimale crosta pane: 150-165°C · carne: 140-160°C · caffè tostato: 195-205°C · pH: +1 unità pH raddoppia la velocità della reazione",
   "strumento":"Termometro IR · sonda · colorimetro",
   "principio":"La reazione di Maillard (già in grafo) descrive il meccanismo. Questo nodo descrive il CONTROLLO: come si modula la velocità e il risultato. Tre leve: (1) Temperatura — più alta = più veloce ma rischio bruciatura. (2) pH — ambiente alcalino accelera Maillard (brezel con idrossido di sodio, biscotto con bicarbonato). (3) Umidità — superficie asciutta è prerequisito per T>100°C. Queste leve spiegano perché stessa ricetta dà colori diversi.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-maillard-controllo', 'prod-brezel', 'si_manifesta_in',
 '{"target":"pH >12 in soluzione NaOH 3-4% · crosta bruno scura intensa · T forno 220-230°C","causa":"La lisciva (idrossido di sodio) alza il pH della superficie al di sopra di 12: Maillard avviene molto più rapidamente dando la caratteristica crosta scura e il sapore distintivo"}'),
('fen-maillard-controllo', 'prod-biscotto-frollino', 'si_manifesta_in',
 '{"target":"Bicarbonato di sodio alza il pH locale · colore più dorato, sapore più intenso","causa":"Il bicarbonato crea un ambiente leggermente alcalino nella pasta che accelera Maillard — stessa ricetta con e senza bicarbonato dà colori diversi"}'),
('fen-maillard-controllo', 'prod-caffe-espresso', 'si_manifesta_in',
 '{"target":"Tostatura caffè: Maillard inizia a 150°C · massima a 195-205°C · second crack: 225°C","causa":"La tostatura del caffè è Maillard in progressione: ogni grado cambia il profilo aromatico. La finestra tra primo e secondo crack è dove si concentra la complessità"}'),
('fen-maillard-controllo', 'prod-bistecca', 'si_manifesta_in',
 '{"target":"Crosta: T>140°C necessaria · superficie asciutta è prerequisito","causa":"Per avere Maillard bisogna che la superficie sia asciutta — l acqua evaporando mantiene la T a 100°C finché non è tutta evaporata. Asciugare la carne prima di cuocere accelera la formazione della crosta"}'),
('fen-maillard-controllo', 'fen-maillard', 'influenza',
 '{"nota":"Questo nodo è complementare al nodo fen-maillard (meccanismo). Questo descrive le leve di controllo: pH, umidità, temperatura — come modulare il risultato nella pratica"}');
