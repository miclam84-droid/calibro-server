INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-chiarificazione', 'Fenomeno', 'Chiarificazione', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"NTU target <5 (brillante) · <1 (cristallino) · torbido >50 NTU",
   "strumento":"Torbidimetro (NTU) · visivo strutturato",
   "principio":"La torbidità è causata da particelle in sospensione (proteine, pectine, tannini, cellule) che diffondono la luce. La chiarificazione rimuove queste particelle per sedimentazione, filtrazione, flocculazione (aggiunta di sostanze che aggregano le particelle in fiocchi più pesanti che precipitano) o centrifugazione.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-chiarificazione', 'prod-vino-bianco', 'si_manifesta_in',
 '{"target":"NTU <5 dopo chiarificazione · bentonite 50-150g/hL per proteine","causa":"Le proteine instabili nel vino bianco precipitano con il calore (casse proteica) — la bentonite le lega prima che il vino sia in bottiglia"}'),
('fen-chiarificazione', 'prod-cocktail-sour', 'si_manifesta_in',
 '{"target":"Succo lime chiarificato: NTU <10 vs succo fresco >200 NTU","causa":"Il succo chiarificato (con pectinex o agar) ha shelf life di 5-7 giorni vs 1 giorno del fresco: la torbidità è causata da pectine che accelerano l ossidazione"}'),
('fen-chiarificazione', 'prod-brodo-consomme', 'si_manifesta_in',
 '{"target":"Consommé: NTU <2 (trasparente come acqua dorata) · tecnica: raft di albumi","causa":"Gli albumi coagulano catturando le particelle torbide del brodo — il raft sale in superficie trascinando con sé le impurità"}'),
('fen-chiarificazione', 'fen-ossidazione', 'influenza',
 '{"nota":"La chiarificazione riduce la torbidità ma può aumentare l esposizione all ossigeno: liquidi più limpidi contengono meno antiossidanti naturali"}');
