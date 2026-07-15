INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-infusione', 'Fenomeno', 'Infusione / Macerazione', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Botaniche a freddo: 4-8°C · 12-48h · A caldo: 60-70°C · 1-4h · Ratio solido/liquido: 1:5 – 1:20",
   "strumento":"Termometro · bilancia · timer",
   "principio":"L''infusione trasferisce composti solubili aromatici da un solido a un solvente liquido per diffusione passiva. Le variabili sono temperatura, tempo, dimensione delle particelle e polarità del solvente. A freddo l''estrazione è lenta ma selettiva: si estraggono aromi delicati senza i tannini e i composti amari che si sviluppano ad alta temperatura. A caldo è più rapida ma meno selettiva. L''alcol estrae composti diversi dall''acqua — molti aromi terziari (vanillina, beta-damascenone) sono liposolubili e si estraggono meglio in alcol. La dimensione delle particelle è critica: macinatura più fine aumenta la superficie di estrazione ma può rendere la filtrazione difficile. Tè, birre dry-hopped, amari, liquori e gin a freddo usano tutti questo stesso principio fisico.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-infusione', 'prod-bitter', 'si_manifesta_in',
 '{"target":"Botaniche in alcol 65-70%: 2-4 settimane a T ambiente al riparo dalla luce","causa":"L alcol ad alta concentrazione estrae i composti aromatici liposolubili che l acqua non riesce a estrarre — ideale per radici, cortecce, botaniche"}'),
('fen-infusione', 'prod-fermentato-lacto', 'si_manifesta_in',
 '{"target":"Erbe fresche in aceto: 7-14 giorni a T ambiente · filtrare · pH <4 per sicurezza","causa":"L aceto (pH 2-3) estrae composti diversi dall alcol e conserva naturalmente grazie all acidità"}'),
('fen-infusione', 'prod-bitter', 'si_manifesta_in',
 '{"target":"Erbe in olio: 60-70°C × 1-2h (metodo a caldo sicuro) o 2-4 settimane a T ambiente","causa":"L olio estrae composti liposolubili diversi da acqua e alcol — ma è un terreno a rischio botulino se non trattato correttamente"}'),
('fen-infusione', 'fen-estrazione', 'influenza',
 '{"nota":"L infusione è una forma di estrazione: la differenza è che nell infusione il solido rimane intero (foglie, radici) mentre nell estrazione caffè/tè il solido è macinato finemente per massimizzare la superficie"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
