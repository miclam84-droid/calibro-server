-- ============================================================
-- ERRORI GELATERIA — batch 01: crioscopia, PAC, overrun, cristallizzazione, bilanciamento
-- (collegato ai temi del post: zuccheri non intercambiabili, PAC)
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-gelato-duro', 'Errore', 'Gelato troppo duro alla vetrina', 'gelateria',
  '{"causa":"PAC troppo basso: pochi zuccheri anticongelanti (o solo saccarosio). Serve piu potere anticongelante (destrosio, sciroppo di glucosio ad alto DE) per tenerlo scoopabile a temperatura di vetrina"}'),
('err-gelato-molle', 'Errore', 'Gelato troppo molle che non tiene', 'gelateria',
  '{"causa":"PAC troppo alto: eccesso di destrosio o zuccheri invertiti abbassano troppo il punto di congelamento. Il gelato non struttura e fonde in fretta. Ribilanciare gli zuccheri, non aggiungerli a caso"}'),
('err-gelato-cristalli', 'Errore', 'Gelato con cristalli di ghiaccio grossi', 'gelateria',
  '{"causa":"cristallizzazione incontrollata: mantecazione lenta, pochi solidi, sbalzi termici in conservazione. I cristalli ricristallizzano grossi. Servono piu solidi, mantecazione rapida, catena del freddo stabile"}'),
('err-gelato-sabbioso', 'Errore', 'Gelato sabbioso o granuloso', 'gelateria',
  '{"causa":"cristallizzazione del lattosio o eccesso di solidi del latte: cristalli di lattosio percepiti come sabbia. Ridurre i solidi magri del latte o usare zuccheri che ne limitano la cristallizzazione"}'),
('err-gelato-poco-corpo', 'Errore', 'Gelato smontato, poco corpo e freddo in bocca', 'gelateria',
  '{"causa":"overrun basso o bilanciamento povero: poca aria incorporata o pochi solidi/grassi. Il gelato risulta pesante e ghiacciato. Aumentare solidi totali (380-420 g/kg) e overrun corretto"}'),
('err-sorbetto-scomposto', 'Errore', 'Sorbetto che spurga acqua e si scioglie subito', 'gelateria',
  '{"causa":"bilanciamento senza grassi sbagliato: senza grassi la struttura dipende tutta da zuccheri, fibre e solidi frutta. Se il PAC e i solidi non sono calcolati, l acqua libera cristallizza e spurga"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-pac-gelateria','err-gelato-duro','fallisce_come','{"sintomo":"duro alla vetrina"}'),
('fen-pac-gelateria','err-gelato-molle','fallisce_come','{"sintomo":"molle, non tiene"}'),
('fen-cristallizzazione-ghiaccio','err-gelato-cristalli','fallisce_come','{"sintomo":"cristalli grossi"}'),
('fen-cristallizzazione-ghiaccio','err-gelato-sabbioso','fallisce_come','{"sintomo":"sabbioso/granuloso"}'),
('fen-overrun','err-gelato-poco-corpo','fallisce_come','{"sintomo":"poco corpo, ghiacciato"}'),
('fen-bilanciamento-gelato','err-sorbetto-scomposto','fallisce_come','{"sintomo":"spurga acqua"}');
