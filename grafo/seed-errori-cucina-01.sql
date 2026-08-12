-- ============================================================
-- ERRORI CUCINA — batch 01: denaturazione, punto-fumo, osmosi, sineresi
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
-- DENATURAZIONE
('err-uovo-stracciato', 'Errore', 'Crema inglese/uovo stracciato e granuloso', 'cucina',
  '{"causa":"denaturazione eccessiva: temperatura oltre 82-85°C, le proteine dell uovo coagulano troppo e si separano dall acqua. Cuocere a bagnomaria e fermarsi a 82°C"}'),
('err-carne-stopposa', 'Errore', 'Carne asciutta e stopposa', 'cucina',
  '{"causa":"denaturazione e contrazione eccessiva delle proteine: temperatura interna troppo alta, le fibre espellono acqua. Rispettare la temperatura al cuore per taglio"}'),
-- PUNTO DI FUMO
('err-olio-bruciato', 'Errore', 'Olio che fuma e sapore acre', 'cucina',
  '{"causa":"superato il punto di fumo: l olio si degrada, libera acroleina e composti amari. Usare oli adatti alla temperatura (alto oleico/arachide per frittura, EVO a crudo)"}'),
-- OSMOSI
('err-verdura-flaccida', 'Errore', 'Verdura flaccida e acquosa dopo la salatura', 'cucina',
  '{"causa":"osmosi: il sale ha richiamato l acqua dalle cellule. Voluto per alcune preparazioni (disidratazione), ma se non gestito rende molli e diluisce. Salare al momento giusto"}'),
-- SINERESI
('err-yogurt-siero', 'Errore', 'Yogurt/crema che rilascia siero', 'cucina',
  '{"causa":"sineresi: il gel proteico si contrae ed espelle acqua. Causata da eccesso di acidità, temperatura troppo alta in coagulazione, o rottura del coagulo. Coagulare a temperatura controllata"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('prod-creme-inglese','err-uovo-stracciato','fallisce_come','{}'),
('prod-carne-rosolata','err-carne-stopposa','fallisce_come','{}'),
('prod-carne-rosolata','err-olio-bruciato','fallisce_come','{}'),
('prod-fermentato-lacto','err-verdura-flaccida','fallisce_come','{}'),
('prod-yogurt','err-yogurt-siero','fallisce_come','{}');
