-- ============================================================
-- G10: Secondo principio-arco — Legge di Henry
-- CO₂ in soluzione = k × P_CO₂
-- Unifica: Carbonatazione + Estrazione + Fermentazione (CO₂)
-- Regola: ✓ — legge fisica con nome, ≥3 fenomeni unificati
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('princ-henry', 'principio', 'Legge di Henry — gas in soluzione', 'trasversale',
 '{"tipo":"principio",
   "misurabile_al_banco": false,
   "nota_ai": "Questo è un principio fisico sottostante. Citarlo come causa comune di fenomeni legati ai gas disciolti, mai come numero da misurare al banco.",
   "scheda": "La legge di Henry (William Henry, 1803) afferma che la quantità di gas disciolto in un liquido è proporzionale alla pressione parziale di quel gas sopra il liquido: C = k × P, dove k è la costante di Henry (dipende dal gas, dal solvente e dalla temperatura). Conseguenze pratiche immediate: (1) Carbonatazione: più pressione di CO₂ = più CO₂ disciolta nella birra o nella soda. Aprire la bottiglia abbassa la pressione, il gas esce. (2) Estrazione caffè: i gas disciolti nel caffè appena macinato (principalmente CO₂ da tostatura) influenzano l estrazione — il degassing è Henry in azione. (3) Fermentazione: la CO₂ prodotta dai lieviti si discioglie parzialmente nell impasto o nel mosto secondo Henry prima di uscire come gas. La temperatura è critica: Henry vale in modo inverso alla temperatura (gas meno solubile a temperature più alte) — ecco perché il champagne fresco ha più bollicine del champagne caldo."}')
ON CONFLICT (id) DO NOTHING;

-- archi spiega (filtrati dal traversal — appaiono solo su domande con "perché")
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('princ-henry', 'fen-carbonatazione', 'spiega',
 '{"peso":0.95, "nota":"La carbonatazione è Henry applicato alla CO₂: P × k = volumi CO₂ disciolti. La pressione nel fusto o nella bottiglia determina direttamente i volumi di carbonatazione"}'),
('princ-henry', 'fen-estrazione', 'spiega',
 '{"peso":0.75, "nota":"Il degassing del caffè (CO₂ che esce dopo la tostatura) è Henry: la CO₂ disciolta nei vacuoli del chicco si libera quando la pressione ambiente è inferiore alla pressione di saturazione. Influenza il bloom e l estrazione"}'),
('princ-henry', 'fen-fermentazione', 'spiega',
 '{"peso":0.80, "nota":"La CO₂ prodotta dai lieviti si discioglie parzialmente nel mosto/impasto secondo Henry prima di formare bolle. La temperatura del mosto determina quanta CO₂ rimane disciolta vs quanto gassifica"}')
ON CONFLICT DO NOTHING;
