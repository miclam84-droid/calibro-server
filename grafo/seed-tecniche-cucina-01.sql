-- ============================================================
-- TECNICHE CUCINA — batch 01
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-sous-vide-cuore', 'Tecnica', 'Cottura a temperatura controllata (sous-vide)', 'cucina',
  '{"nota":"bagno termostatato alla temperatura-cuore desiderata: la proteina non supera mai quella soglia, niente sovra-denaturazione. Es. petto pollo 62-65 gradi C, uovo 63 gradi C, manzo 54-56 gradi C"}'),
('tec-bagnomaria', 'Tecnica', 'Bagnomaria per creme e uova', 'cucina',
  '{"nota":"calore dolce e indiretto: la crema inglese resta sotto 82-85 gradi C e non straccia. Controllo termico per coagulazioni delicate"}'),
('tec-olio-giusto', 'Tecnica', 'Scelta olio per punto di fumo', 'cucina',
  '{"nota":"abbina l olio alla temperatura: alto oleico/arachide (~220-230 gradi C) per frittura, EVO a crudo o basse temperature. Evita che l olio superi il suo punto di fumo"}'),
('tec-salatura-tempi', 'Tecnica', 'Salatura a tempo controllato', 'cucina',
  '{"nota":"sala al momento giusto per governare l osmosi: salatura in anticipo (dry brine) per far riassorbire i succhi, salatura tardiva se vuoi evitare rilascio d acqua"}'),
('tec-coagulo-controllato', 'Tecnica', 'Coagulazione a temperatura controllata (yogurt/creme)', 'cucina',
  '{"nota":"mantieni la temperatura di coagulazione stabile (yogurt ~42-45 gradi C) ed evita l eccesso di acidita: la rete proteica trattiene il siero, niente sineresi"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-denaturazione','tec-sous-vide-cuore','realizzato_da','{}'),
('fen-denaturazione','tec-bagnomaria','realizzato_da','{}'),
('fen-punto-fumo','tec-olio-giusto','realizzato_da','{}'),
('fen-osmosi','tec-salatura-tempi','realizzato_da','{}'),
('fen-sineresi','tec-coagulo-controllato','realizzato_da','{}');
