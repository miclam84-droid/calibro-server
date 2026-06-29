-- ============================================================
-- VARIABILITÀ DEGLI INGREDIENTI — conoscenza operativa
-- La domanda vera del professionista non è "cos'è il pH"
-- ma "perché il risultato cambia se faccio sempre la stessa cosa".
-- Queste sono le variabili nascoste che il grafo deve conoscere.
-- Fonte: Arnold (Liquid Intelligence), Schramm (Existing Conditions),
-- ricerca agronomica verificata.
-- ============================================================

-- ---- PROCESSI: le variabili nascoste per ingrediente ----------

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-variabilita-lime', 'Processo', 'Variabilità del lime (e degli agrumi)', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Il lime non è costante. Quattro variabili cambiano la sua acidità titolabile anche a parità di frutto visivamente identico:\n1. VARIETÀ: il Key lime (più piccolo, più aromatico) è più acido del Tahiti (quello grande da supermercato). In Italia si trovano quasi sempre Tahiti.\n2. MATURITÀ: il lime verde e sodo è più acido di quello giallo e cedevole. Paradosso: un lime maturo (giallo) sembra di qualità superiore ma ha meno acido. La zona target è il verde brillante, sodo, pesante per la sua dimensione.\n3. SPREMITURA: il frullatore introduce ossigeno che degrada l acido citrico. La spremitura a mano o con centrifuga è più conservativa. Spremerlo ore prima e lasciarlo all aria abbassa la titolabile nel tempo.\n4. STAGIONE: la concentrazione di acido citrico nei citrus varia con le stagioni anche sullo stesso albero. In certi periodi lo stesso fornitore ti dà lime molto più dolci.\nLa soluzione professionale: misura la titolabile del lotto e correggi con acido citrico/malico se necessario (acid adjustment). Arnold lo codifica in Liquid Intelligence: il target è 6% e si raggiunge indipendentemente dal frutto."}'),

('proc-variabilita-succo-fresco', 'Processo', 'Degrado del succo fresco nel tempo', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Il succo di limone o lime appena spremuto ha acidità titolabile intorno al 5-6%. Dopo 4-8 ore a temperatura ambiente, l acido citrico si degrada per ossidazione e l acidità cala misurabilmente. Dopo 24 ore in frigo la perdita è minore ma presente. Per questo il sour fatto con succo del giorno prima sa diverso da quello fatto con succo fresco: non è la tecnica, è la chimica. La soluzione: spremere al momento o conservare in contenitore ermetico e freddo, massimo 24h."}'),

('proc-acid-adjustment', 'Processo', 'Acid adjustment (correzione acida)', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Tecnica professionale codificata da Arnold: invece di usare il lime com è, si porta qualsiasi succo al 6% di acidità titolabile aggiungendo acido citrico (e malico per imitare il lime). Vantaggi: consistenza assoluta, nessuna variabilità stagionale, possibilità di usare succhi poveri di acido (arancia 0,7%, ananas 0,5%) come base aromatica senza sacrificare l equilibrio. Il pareggiatore di acidità nel calcolatore fa esattamente questo: calcola quanti grammi di acido citrico aggiungere per portare un succo debole al target."}');

-- ---- ARCHI: aggancio ai fenomeni esistenti -------------------
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- la variabilità del lime è un processo che realizza il fenomeno Acidità nel bar
('fen-acidita','proc-variabilita-lime','realizzato_da',
 '{"nota":"la variabilità del lime è la causa più comune di inconsistenza nel sour"}'),
('fen-acidita','proc-variabilita-succo-fresco','realizzato_da',
 '{"nota":"il degrado ossidativo è una variabile nascosta che il barman spesso non vede"}'),
('fen-acidita','proc-acid-adjustment','controllato_con',
 '{"nota":"la soluzione professionale alla variabilità: misura e correggi"}'),
-- il sour e i cocktail acidi sono i prodotti dove questo si manifesta
('proc-variabilita-lime','prod-sour','si_manifesta_in',
 '{"ruolo":"il sour è il cocktail più sensibile alla variabilità del lime"}'),
('proc-variabilita-lime','prod-daiquiri','si_manifesta_in',
 '{"ruolo":"3/4 oz di lime: piccole variazioni cambiano l equilibrio"}'),
('proc-variabilita-lime','prod-margarita','si_manifesta_in',
 '{"ruolo":"idem: il triple sec maschera parzialmente la variazione ma non la elimina"}'),
('proc-acid-adjustment','prod-sour','controllato_con','{}'),
('proc-acid-adjustment','prod-daiquiri','controllato_con','{}');

-- ============================================================
-- VARIABILI NASCOSTE — panificazione con lievito naturale
-- "La madre triplica ma il pane non sviluppa in cottura"
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-madre-vs-pane', 'Processo', 'Madre attiva ≠ pane che sviluppa (le variabili nascoste)', 'bakery',
 '{"tipo":"biologico","scheda":"La madre che triplica in 4 ore è condizione necessaria ma non sufficiente. Il pane non sviluppa in cottura (oven spring) per queste variabili nascoste, in ordine di frequenza:\n1. SOVRA-FERMENTAZIONE: il glutine ha cominciato a cedere prima della cottura. La massa è cresciuta oltre il 75-80% durante il bulk fermentation: le proteine si sono esaurite, le bolle di CO2 scappano. Il segno: l impasto è appiccicoso, non tiene la forma, sa molto di acido. Il termometro della cucina non mente: a 26-28°C il bulk finisce in 4-5 ore, non 8.\n2. GLUTINE NON SVILUPPATO: la farina è debole (meno del 12% di proteine) o l impasto ha bisogno di più pieghe. Senza rete glutinica il gas non viene trattenuto in cottura. Test: il windowpane — se l impasto si strappa, serve altro lavoro.\n3. FORNO NON ABBASTANZA CALDO O SENZA VAPORE: l oven spring (il salto in forno) richiede 230-250°C e vapore nei primi 15 minuti. Senza vapore la crosta si solidifica subito e blocca il rigonfiamento prima che sia completo.\n4. FORMATURA TROPPO MOLLE: la tensione superficiale dell impasto è la molla che il calore fa scattare. Senza tensione il pane si allarga invece di crescere in altezza."}'),

-- ---- VARIABILI NASCOSTE — cold brew debole
('proc-cold-brew-debole', 'Processo', 'Cold brew debole (variabili nascoste)', 'caffetteria',
 '{"tipo":"fisico-chimico","scheda":"Il cold brew debole a parità di 18 ore e stesso rapporto ha sempre la stessa causa: la temperatura governa la cinetica di estrazione in modo esponenziale. Le variabili nascoste:\n1. TEMPERATURA REALE DEL FRIGO: un frigo a 4°C estrae in 18-24h quello che un frigo a 10°C estrae in 12-16h. Non tutti i frigoriferi sono a 4°C — spesso sono a 6-8°C, e in estivo salgono ancora. Un termometro dentro il frigo risolve il mistero.\n2. MACINATURA TROPPO GROSSA: il cold brew tollera una macinatura grossissima, ma c è un limite. Se la macinatura è da french press molto grossa, l EY finale è sotto il 12% anche con 24h. Per cold brew: macinatura media-grossa, non grossissima.\n3. QUALITÀ DEL CAFFÈ: un caffè vecchio (ossidato) o di tostatura chiara perde molti composti solubili. Il cold brew è impietoso con il caffè mediocre perché non ha il calore a compensare.\n4. RAPPORTO REALE vs PERCEPITO: spesso si misura per volume (1 tazza di caffè in 8 tazze d acqua) invece che per peso. In peso il ratio corretto è 1:8 in g/g — in volume è sbagliato perché il caffè macinato ha densità variabile."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
-- variabili nascoste negroni inconsistente
('proc-negroni-inconsistente', 'Processo', 'Negroni inconsistente a parità di ricetta (variabili nascoste)', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Il Negroni stirred cambia gusto a parità di ricetta per queste variabili che il barman spesso non controlla:\n1. GHIACCIO: il ghiaccio industriale (duro, denso, -18°C) diluisce diversamente dal ghiaccio domestico (poroso, più caldo). Un ghiaccio poroso scioglie il 30-40% più velocemente a parità di tempo di stir. La diluizione finale cambia l ABV di 2-3 gradi e cambia la percezione del gusto.\n2. TEMPERATURA DI SERVIZIO: il Negroni stirred va servito a circa -2°C nel bicchiere. Se il bicchiere è a temperatura ambiente la temperatura sale rapidamente e la percezione del gusto cambia — il Campari amaro emerge di più al caldo.\n3. VARIABILITÀ DEL VERMOUTH: il vermouth è vino aromatizzato — una volta aperto ossida. Un vermouth aperto da 3 settimane e uno fresco danno un Negroni completamente diverso. Il vermouth va tenuto in frigo e consumato entro 2-3 settimane.\n4. TECNICA DI STIR: 20 giri danno ~20% di diluizione, 30 giri ~22%, 40 giri ~25%. La differenza sembra piccola ma cambia l equilibrio percepito."}'),

-- variabili nascoste kimchi molle
('proc-kimchi-molle', 'Processo', 'Kimchi molle (variabili nascoste)', 'cucina',
 '{"tipo":"biologico","scheda":"Il kimchi viene molle per cause diverse dai crauti, nonostante seguano la stessa logica fermentativa. Le variabili nascoste:\n1. TEMPERATURA DI FERMENTAZIONE TROPPO ALTA: il kimchi vuole fermentare lentamente a 10-15°C (tradizionalmente sotterrato in giare). A temperatura ambiente (20-25°C) la fermentazione corre troppo veloce, i pectinasi delle verdure degradano la cellulosa e la consistenza si perde prima che il sapore si sviluppi. Il frigorifero a 4-6°C è la soluzione moderna.\n2. SALE INSUFFICIENTE O MAL DISTRIBUITO: il sale deve stare a contatto con le verdure abbastanza a lungo (la fase di salatura dura 1-2 ore per il cavolo cinese prima di aggiungere il condimento). Sale insufficiente = pectinasi non inibiti = verdure molli.\n3. TIPO DI VERDURA: il cavolo cinese (baechu) regge meglio del cavolo cappuccio. Il daikon tiene bene. Le zucchine e i cetrioli diventano molli in pochi giorni — sono verdure ad alto contenuto d acqua. Se si usano verdure non tradizionali il risultato è diverso.\n4. TROPPO ACETO nella ricetta (ricette non tradizionali): l acido acetico degrada le verdure più rapidamente dell acido lattico."}');

-- ARCHI
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione','proc-madre-vs-pane','realizzato_da',
 '{"nota":"la madre attiva è condizione necessaria ma non sufficiente per l oven spring"}'),
('fen-struttura','proc-madre-vs-pane','controllato_con',
 '{"nota":"il glutine non sviluppato è la seconda causa di pane piatto dopo la sovra-fermentazione"}'),
('fen-estrazione','proc-cold-brew-debole','realizzato_da',
 '{"nota":"la temperatura del frigo è la variabile nascosta più comune nel cold brew inconsistente"}'),
('fen-calore','proc-cold-brew-debole','controllato_con',
 '{"nota":"il cold brew è estrazione a freddo: la temperatura governa la cinetica in modo esponenziale"}'),
('fen-calore','proc-negroni-inconsistente','realizzato_da',
 '{"nota":"la diluizione dello stir è governata dalla temperatura e dalla qualità del ghiaccio"}'),
('fen-fermentazione','proc-kimchi-molle','realizzato_da',
 '{"nota":"kimchi molle = temperatura di fermentazione troppo alta o sale insufficiente"}'),
('fen-osmosi','proc-kimchi-molle','controllato_con',
 '{"nota":"il sale inibisce i pectinasi osmoticamente — sale giusto = consistenza mantenuta"}'),
-- aggancio ai prodotti
('proc-madre-vs-pane','prod-sourdough-usa','si_manifesta_in','{}'),
('proc-cold-brew-debole','prod-cold-brew','si_manifesta_in','{}'),
('proc-negroni-inconsistente','prod-negroni','si_manifesta_in','{}'),
('proc-kimchi-molle','prod-kimchi','si_manifesta_in','{}');
