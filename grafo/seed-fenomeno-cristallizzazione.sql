-- ============================================================
-- FENOMENO: Cristallizzazione
-- Regola di partizione: ✓
-- Numero-bersaglio: temperatura di cristallizzazione
--   (27-31°C per Forma V β del burro di cacao;
--    32°C per burro; 135-145°C per zucchero fondente)
-- Strumento: termometro di precisione (±0,1°C)
-- Si manifesta in: temperaggio cioccolato, burro, zucchero cotto, gelato
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-cristallizzazione', 'Fenomeno', 'Cristallizzazione', 'trasversale',
 '{"tipo":"fisico-chimico",
   "target":"27-31°C (Forma V cioccolato) · 32°C (burro) · 135-145°C (zucchero)",
   "strumento":"termometro di precisione ±0,1°C",
   "scheda":"La cristallizzazione è il processo per cui le molecole di un liquido raffreddato si organizzano in strutture solide ordinate. In pasticceria è il fenomeno più critico: il burro di cacao ha sei forme cristalline diverse (Forma I-VI), e solo la Forma V β produce il cioccolato temperato corretto — quello che suona, brilla e si spezza netto. Scaldando il cioccolato oltre 45°C si sciolgono tutti i cristalli. Raffreddando a 27-28°C si formano cristalli instabili (Forma IV). Portando di nuovo a 31-32°C rimangono solo i cristalli Forma V: questo è il temperaggio. Lo stesso principio governa la cristallizzazione del burro (burro pomata vs burro granuloso) e dello zucchero (fondente, caramello, pralinato)."}')
ON CONFLICT (id) DO NOTHING;

-- prodotti dove si manifesta
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-cioccolato-temperato', 'Prodotto', 'Cioccolato temperato', 'pasticceria',
 '{"target":"Forma V β · 31-32°C · brillante e sonoro",
   "strumento":"termometro, marmo"}'),
('prod-burro-cristallizzato', 'Prodotto', 'Burro pomata / burro lavorato', 'pasticceria',
 '{"target":"18-20°C per burro pomata · 32°C cristallizzazione",
   "strumento":"termometro"}'),
('prod-zucchero-cotto', 'Prodotto', 'Zucchero cotto (fondente, pralinato)', 'pasticceria',
 '{"target":"135-145°C per fondente · 160-170°C per caramello",
   "strumento":"termometro sonda"}'),
('prod-gelato-cristalli', 'Prodotto', 'Gelato — controllo cristalli', 'gelateria',
 '{"target":"cristalli <50µm = texture cremosa · >100µm = granulosità",
   "strumento":"microscopio o valutazione organolettica"}')
ON CONFLICT (id) DO NOTHING;

-- archi: Cristallizzazione si_manifesta_in
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-cristallizzazione', 'prod-cioccolato-temperato', 'si_manifesta_in',
 '{"target":"27-31°C (Forma V β)","causa":"La Forma V β è l unica che produce lucentezza, snap e fusione corretta in bocca"}'),
('fen-cristallizzazione', 'prod-burro-cristallizzato', 'si_manifesta_in',
 '{"target":"18-20°C pomata · 32°C cristallizzazione completa","causa":"La struttura cristallina del burro determina la texture di creme e frolle"}'),
('fen-cristallizzazione', 'prod-zucchero-cotto', 'si_manifesta_in',
 '{"target":"135-145°C fondente · 160-170°C caramello","causa":"A temperature diverse lo zucchero cristallizza in forme diverse (fondente vs granuloso vs caramello)"}'),
('fen-cristallizzazione', 'prod-gelato-cristalli', 'si_manifesta_in',
 '{"target":"cristalli <50µm","causa":"Cristalli di ghiaccio piccoli = texture cremosa. Grandi cristalli = gelato granuloso (effetto ricristallizzazione da sbalzi termici)"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

-- errori comuni
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-cioccolato-grigio', 'Errore', 'Cioccolato grigio / fat bloom', 'pasticceria',
 '{"causa":"Temperature di temperaggio non rispettate: cristalli Forma VI in superficie","soluzione":"Temperare correttamente: sciogliere >45°C, raffreddare a 27°C, riportare a 31-32°C"}'),
('err-cristallizzazione-indesiderata', 'Errore', 'Zucchero cristallizzato (indesiderato)', 'pasticceria',
 '{"causa":"Sciroppo perturbato meccanicamente o contaminato da cristalli durante la cottura","soluzione":"Non mescolare durante la cottura, usare glucosio come agente anticristallizzante"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-cristallizzazione', 'err-cioccolato-grigio', 'fallisce_come',
 '{"causa":"Temperaggio non corretto: Forma IV invece di Forma V"}'),
('fen-cristallizzazione', 'err-cristallizzazione-indesiderata', 'fallisce_come',
 '{"causa":"Nucleazione incontrollata dei cristalli di zucchero"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;

-- connessione con Calore (la temperatura governa il processo)
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-cristallizzazione', 'fen-calore', 'influenza',
 '{"nota":"La temperatura è il parametro di controllo della cristallizzazione: ogni tipo di cristallo ha la sua finestra termica di stabilità"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
