-- ============================================================
-- CONNESSIONI TRASVERSALI ESPLICITE
-- Il valore di Calibro non è sapere le cose: è mostrarle connesse.
-- Questi nodi sono i "fili rossi" che attraversano tutte le discipline.
-- ============================================================

-- ============================================================
-- FILO ROSSO 1: IL Q10 — la stessa legge in sei discipline
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-q10-filo-rosso', 'Processo', 'Q10 — la legge che attraversa tutto', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"Q10 è il coefficiente di temperatura: la velocità di un processo biologico raddoppia ogni ~10°C. È la stessa legge, con lo stesso numero, in sei contesti completamente diversi:\n\nPANIFICAZIONE: il bulk a 18°C richiede il doppio del tempo rispetto a 28°C. Un fornaio che segue la ricetta senza misurare la temperatura dell impasto produce pane inconsistente in inverno e in estate.\n\nFERMENTAZIONE (crauti, kimchi, yogurt): la fermentazione a 10°C richiede 4x il tempo rispetto a 20°C. Il kimchi tradizionale fermenta sotterrato perché la terra sta a 10-12°C.\n\nPASTORIZZAZIONE: il latte pastorizzato a 63°C × 30 min = 72°C × 15 secondi. Ogni grado in più dimezza il tempo. È Q10 applicato all inibizione batterica invece che all attivazione.\n\nCAFFEINA/COLD BREW: estrazione a 4°C richiede 4-5x il tempo dell estrazione a 20°C per lo stesso EY.\n\nFERMENTAZIONE ALCOLICA (birra, vino): la fermentazione a 12°C produce profili aromatici diversi da quella a 20°C — più lenta, più delicata, meno esteri.\n\nCINETICA MAILLARD: la reazione di Maillard raddoppia la velocità ogni ~10°C nella zona 140-165°C.\n\nUna sola legge. Sei discipline. Chi sa questo non insegue la ricetta — controlla la variabile.","formula":"t2 = t1 × Q10^((T1-T2)/10); Q10 ≈ 2 per la maggior parte dei processi biologici"}');

-- ============================================================
-- FILO ROSSO 2: L'ACQUA LIBERA (water activity)
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-acqua-libera', 'Processo', 'Acqua libera (water activity) — la chiave della conservazione', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"Non tutta l acqua in un alimento è disponibile per i batteri e le reazioni chimiche. L acqua libera (water activity, aw) è la frazione di acqua non legata a zuccheri, sali, proteine. I batteri patogeni non crescono sotto aw 0.85; muffe non crescono sotto aw 0.7; batteri osmofili si fermano sotto aw 0.6. Questo spiega:\n\nSALUMI STAGIONATI: il sale lega l acqua, abbassa aw, inibisce i patogeni senza cottura. Stesso principio della salamoia ma in versione solida.\n\nCONFETTURE ad alta concentrazione (>65 Brix): lo zucchero lega l acqua, aw scende sotto 0.8 = conservazione senza pastorizzazione a lungo termine.\n\nPANETTONE: lo zucchero e i grassi abbassano aw — ma la madre stiff e i lieviti selezionati devono resistere a questa pressione.\n\nCROSTA DEL PANE: in forno l acqua libera della superficie evapora rapidamente, aw scende a quasi 0, la Maillard parte. Senza questa riduzione di aw la crosta non imbrunisce.\n\nFOCAccia vs PIZZA NAPOLETANA: la focaccia ha aw alta (più morbida), la pizza napoletana in 90 secondi a 430°C ha aw superficiale che crolla istantaneamente — Maillard e leopardatura immediati.\n\naw si misura con un igrometro (strumento da laboratorio). In pratica si controlla con la concentrazione: Brix per gli zuccheri, % di sale per le salamoie.","numeri":"patogeni fermano <0.85 · muffe <0.70 · osmofili <0.60"}');

-- ============================================================
-- FILO ROSSO 3: ACIDITÀ COME CONSERVANTE (pH < 4.6)
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-ph-conservazione', 'Processo', 'pH come barriera di sicurezza alimentare', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"pH 4.6 è la soglia universale della sicurezza alimentare: sotto questo valore il Clostridium botulinum non può crescere né produrre tossina. È lo stesso numero in contesti completamente diversi:\n\nFERMENTATI (crauti, kimchi, pickles): la fermentazione lattica abbassa il pH sotto 4.6 in pochi giorni — la natura fa il lavoro di sicurezza.\n\nCONFETTURE: il pH 3.0-3.3 necessario per la gelificazione della pectina è anche molto sotto la soglia di sicurezza. Un vantaggio strutturale che diventa sicurezza alimentare.\n\nMARINATURE con aceto: il pH finale della marinatura deve stare sotto 4.6 perché la concentrazione di acido venga mantenuta nel prodotto finale, non solo nella marinatura.\n\nLIEVITO NATURALE (madre): pH 3.7-4.1 a maturità — non è solo aroma, è sicurezza microbiologica del pane. La madre acida inibisce i patogeni nell impasto crudo.\n\nYOGURT: pH 4.0-4.5 a fermentazione completa — la soglia di sicurezza è automaticamente raggiunta quando il prodotto ha il sapore giusto.\n\nUna sola soglia. Cinque contesti. Il pHmetro è lo strumento che misura la sicurezza in tutti.","numeri":"pH <4.6 = sicurezza botulinum · pH <4.0 = sicurezza quasi universale"}');

-- ============================================================
-- ARCHI — i fili rossi si connettono ai fenomeni esistenti
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- Q10 come processo che realizza Calore in ogni disciplina
('fen-calore','proc-q10-filo-rosso','realizzato_da',
 '{"nota":"Q10 è la cinetica termica universale: la stessa legge in panificazione, fermentazione, pastorizzazione, estrazione, Maillard"}'),
('proc-q10-filo-rosso','prod-madre','si_manifesta_in',
 '{"ruolo":"bulk a 18°C = doppio del tempo rispetto a 28°C"}'),
('proc-q10-filo-rosso','prod-crauti','si_manifesta_in',
 '{"ruolo":"fermentazione a 10°C = 4x il tempo rispetto a 20°C"}'),
('proc-q10-filo-rosso','prod-cold-brew','si_manifesta_in',
 '{"ruolo":"estrazione a 4°C = 4-5x il tempo dell estrazione a 20°C"}'),
('proc-q10-filo-rosso','prod-birra-carb','si_manifesta_in',
 '{"ruolo":"fermentazione a 12°C: più lenta, profilo aromatico diverso"}'),

-- acqua libera come processo che realizza Concentrazione e Osmosi
('fen-concentrazione','proc-acqua-libera','realizzato_da',
 '{"nota":"Brix governa l acqua libera: >65 Brix = aw <0.8 = conservazione naturale"}'),
('fen-osmosi','proc-acqua-libera','realizzato_da',
 '{"nota":"sale e zucchero legano l acqua: osmosi e acqua libera sono due facce della stessa cosa"}'),
('proc-acqua-libera','prod-confettura','si_manifesta_in',
 '{"ruolo":">65 Brix abbassa aw sotto 0.8: conservazione senza pastorizzazione"}'),
('proc-acqua-libera','prod-panettone','si_manifesta_in',
 '{"ruolo":"zucchero e grassi abbassano aw: stress per i lieviti, barriera per i patogeni"}'),
('proc-acqua-libera','prod-pizza-nap-adv','si_manifesta_in',
 '{"ruolo":"a 430°C aw superficiale crolla istantaneamente: Maillard immediato, leopardatura"}'),

-- pH come barriera — collega Acidità alla sicurezza alimentare
('fen-acidita','proc-ph-conservazione','realizzato_da',
 '{"nota":"pH 4.6 è la soglia universale: stessa in fermentati, confetture, lievito naturale, yogurt"}'),
('proc-ph-conservazione','prod-crauti','si_manifesta_in',
 '{"ruolo":"fermentazione lattica raggiunge pH <4.6 in pochi giorni: sicurezza automatica"}'),
('proc-ph-conservazione','prod-confettura','si_manifesta_in',
 '{"ruolo":"pH 3.0-3.3 per la gelificazione è anche molto sotto la soglia di sicurezza"}'),
('proc-ph-conservazione','prod-yogurt','si_manifesta_in',
 '{"ruolo":"pH 4.0-4.5 a fermentazione completa: sicurezza raggiunta quando il sapore è giusto"}'),
('proc-ph-conservazione','prod-madre','si_manifesta_in',
 '{"ruolo":"madre pH 3.7-4.1: acidità = sicurezza microbiologica dell impasto crudo"}');
