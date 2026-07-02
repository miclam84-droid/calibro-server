-- ============================================================
-- PRIMO IPER-ARCO PRINCIPIO: kT / energia termica
-- Regola soddisfatta: legge fisica con nome (coda di Boltzmann,
-- costante kT) + unifica 4 fenomeni già presenti nel grafo
-- (Calore, Estrazione, Fermentazione, Carbonatazione) +
-- la sua rimozione lascia quei fenomeni scollegati.
--
-- Modellazione: reificazione — nodo type='principio' + archi
-- relation='spiega'. Zero tabelle nuove. Schema esistente.
--
-- NOTA CRITICA: questo nodo NON ha numero-bersaglio.
-- Non è misurabile al banco. Non apparire come un fenomeno.
-- Il campo tipo='principio' lo distingue nella UI e nel traversal.
-- La regola: relation='spiega' viene esclusa dal CTE di
-- costruzione-contesto di default, inclusa solo su domande
-- esplicitamente sul "perché" (parole: perché, causa, principio,
-- legge, spiega).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('princ-kt', 'principio', 'kT — energia termica (coda di Boltzmann)', 'trasversale',
 '{"tipo":"principio",
   "misurabile_al_banco": false,
   "nota_ai": "Questo è un principio fisico sottostante, NON un numero da misurare al banco. Citarlo come causa comune di più fenomeni, mai come parametro operativo.",
   "scheda": "kT è il prodotto della costante di Boltzmann (k = 1.38×10⁻²³ J/K) per la temperatura assoluta T. Rappresenta l energia termica media disponibile per ogni grado di libertà di un sistema. La coda di Boltzmann descrive la frazione di molecole che supera una barriera di attivazione Ea: quella frazione cresce come e^(-Ea/kT) — esponenzialmente con la temperatura.\n\nPerché scaldare accelera quasi tutto in cucina, al banco e in fermentazione: più caldo = più molecole oltre la barriera = reazione più veloce. Il Q10 (ogni 8-10°C la velocità raddoppia) è la manifestazione pratica di questa legge — il numero che il professionista misura, la cui causa è kT.\n\nPerché la curva ha un picco e poi crolla: la salita esponenziale (Boltzmann) vale finché le proteine reggono. Sopra una soglia critica (tipicamente 45-70°C secondo il sistema) le proteine si denaturano e il sistema biologico si spegne. Due fisiche diverse che si passano il testimone: kT accelera, la denaturazione interrompe.\n\nUn solo principio, quattro fenomeni: Calore/cinetica (Q10 della lievitazione e cottura), Estrazione caffè (l acqua calda estrae più velocemente), Fermentazione (i batteri lattici seguono la stessa cinetica), Carbonatazione (CO2 in soluzione dipende da temperatura)."}');

-- ============================================================
-- ARCHI relation='spiega' — kT verso i 4 fenomeni che unifica
-- Direzione: principio → fenomeno (kT spiega Calore, non viceversa)
-- Peso 0.9: connessione forte, causa diretta
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('princ-kt', 'fen-calore', 'spiega',
 '{"peso": 0.9, "nota": "Q10 è la manifestazione operativa di kT: ogni 8-10°C in più, la frazione di molecole oltre la barriera di attivazione raddoppia, e quindi la velocità raddoppia. Il Q10 è il numero che misuri; kT è il perché."}'),
('princ-kt', 'fen-estrazione', 'spiega',
 '{"peso": 0.9, "nota": "L acqua calda estrae di più e più velocemente perché più molecole hanno energia sufficiente a dissolvere i composti solubili del caffè. La stessa cinetica del Q10 governa la curva EY vs temperatura."}'),
('princ-kt', 'fen-fermentazione', 'spiega',
 '{"peso": 0.9, "nota": "I batteri lattici e i lieviti seguono la coda di Boltzmann: il Q10 della fermentazione (~2 ogni 8°C) è direttamente derivabile dalla forma e^(-Ea/kT) con una energia di attivazione biologica tipica (~0.6 eV)."}'),
('princ-kt', 'fen-carbonatazione', 'spiega',
 '{"peso": 0.8, "nota": "La solubilità della CO2 in acqua diminuisce con la temperatura (legge di Henry) — ma la cinetica con cui la CO2 raggiunge l equilibrio in soluzione dipende ancora da kT. Connessione più indiretta degli altri tre."}');
