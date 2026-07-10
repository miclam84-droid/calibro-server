INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-infusione', 'Fenomeno', 'Infusione / Macerazione', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Botaniche a freddo: 4-8°C · 12-48h · A caldo: 60-70°C · 1-4h · Ratio solido/liquido: 1:5 – 1:20",
   "strumento":"Termometro · bilancia · timer",
   "principio":"L infusione trasferisce composti aromatici solubili da un solido a un liquido solvente. La velocità di trasferimento dipende dalla temperatura (più alta = più veloce ma rischio di estrarre composti indesiderati), dalla dimensione delle particelle (più piccole = più superficie = più rapida) e dalla polarità del solvente (alcol estrae aromi diversi dall acqua).",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-infusione', 'prod-bitter-amaro', 'si_manifesta_in',
 '{"target":"Botaniche in alcol 65-70%: 2-4 settimane a T ambiente al riparo dalla luce","causa":"L alcol ad alta concentrazione estrae i composti aromatici liposolubili che l acqua non riesce a estrarre — ideale per radici, cortecce, botaniche"}'),
('fen-infusione', 'prod-aceto-aromatizzato', 'si_manifesta_in',
 '{"target":"Erbe fresche in aceto: 7-14 giorni a T ambiente · filtrare · pH <4 per sicurezza","causa":"L aceto (pH 2-3) estrae composti diversi dall alcol e conserva naturalmente grazie all acidità"}'),
('fen-infusione', 'prod-olio-aromatizzato', 'si_manifesta_in',
 '{"target":"Erbe in olio: 60-70°C × 1-2h (metodo a caldo sicuro) o 2-4 settimane a T ambiente","causa":"L olio estrae composti liposolubili diversi da acqua e alcol — ma è un terreno a rischio botulino se non trattato correttamente"}'),
('fen-infusione', 'fen-estrazione', 'influenza',
 '{"nota":"L infusione è una forma di estrazione: la differenza è che nell infusione il solido rimane intero (foglie, radici) mentre nell estrazione caffè/tè il solido è macinato finemente per massimizzare la superficie"}');
