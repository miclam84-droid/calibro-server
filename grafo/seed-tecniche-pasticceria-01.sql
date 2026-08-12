-- ============================================================
-- TECNICHE PASTICCERIA — batch 01
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-temperaggio-curve', 'Tecnica', 'Temperaggio a curve (tablage o seeding)', 'pasticceria',
  '{"nota":"porta il cioccolato alle temperature di cristallizzazione della forma beta V: fondente 45-50 poi 27 poi 31-32 gradi C. Cristalli stabili = lucido, snap, niente fat bloom"}'),
('tec-ganache-emulsione', 'Tecnica', 'Emulsione della ganache al centro', 'pasticceria',
  '{"nota":"versa la panna calda (35-40 gradi C) in tre volte mescolando dal centro: crei un nucleo emulsionato lucido e stabile. Se impazzisce, correggi con poco liquido caldo e frulla"}'),
('tec-albumi-picco', 'Tecnica', 'Montaggio albumi al picco fermo', 'pasticceria',
  '{"nota":"monta con zucchero aggiunto gradualmente fino al picco fermo e lucido, senza superarlo: la rete proteica e stabile, meringa e souffle non collassano ne rilasciano sciroppo"}'),
('tec-panna-fredda', 'Tecnica', 'Panna e ciotola a 4 gradi C, stop al picco morbido', 'pasticceria',
  '{"nota":"tutto ben freddo e fermati al picco morbido: i globuli di grasso intrappolano aria senza rompersi. Evita che la panna diventi burrosa"}'),
('tec-conservazione-amido', 'Tecnica', 'Gestione retrogradazione (zuccheri, grassi, sigillo)', 'pasticceria',
  '{"nota":"zuccheri e grassi rallentano la retrogradazione dell amido; conserva a temperatura ambiente sigillato (NON in frigo, che la accelera). Prolunga la morbidezza"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-temperaggio-cioccolato','tec-temperaggio-curve','realizzato_da','{}'),
('fen-ganache','tec-ganache-emulsione','realizzato_da','{}'),
('fen-meringa','tec-albumi-picco','realizzato_da','{}'),
('fen-souffle','tec-albumi-picco','realizzato_da','{}'),
('fen-montatura-panna','tec-panna-fredda','realizzato_da','{}'),
('fen-retrogradazione','tec-conservazione-amido','realizzato_da','{}');
