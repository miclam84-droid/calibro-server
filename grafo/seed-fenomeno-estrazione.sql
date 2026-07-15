-- ============================================================
-- FENOMENO ESTRAZIONE — costruito con la regola.
-- Numero-bersaglio PROPRIO: EY% (extraction yield, quanto soluto porti dal solido).
-- Condivide TDS% con Concentrazione (scoperta strutturale: EY e TDS si misurano
-- insieme ma sono indipendenti — forte≠estratto). Strumento: rifrattometro + bilancia.
-- tipo: fisico-chimico. Passa la regola.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-estrazione', 'Fenomeno', 'Estrazione', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"L'estrazione è il trasferimento di composti solubili da una matrice solida a un solvente liquido. Le variabili sono sempre le stesse indipendentemente dal prodotto: temperatura (più alta = più veloce, ma rischio di estrarre composti indesiderati), tempo di contatto, dimensione delle particelle (più piccole = più superficie = più rapida estrazione), polarità del solvente (l'alcol estrae composti diversi dall'acqua, i grassi estraggono i liposolubili). L'acqua estrae zuccheri, acidi, caffeina, tannini. L'alcol estrae terpeni, esteri, polifenoli. I grassi estraggono i composti aromatici liposolubili. Conoscere la polarità è scegliere il solvente giusto per l'obiettivo.","numero_bersaglio":"EY 18-22% (zona dolce); TDS dipende dal metodo"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-ey', 'Calcolo', 'Extraction yield EY%', 'trasversale',
 '{"tipo":"fisico-chimico","formula":"EY% = (peso_bevanda x TDS%) / dose_secca","nota":"18-22% SCA; sotto=acido, sopra=amaro"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-estrazione-acqua', 'Processo', 'Estrazione in acqua', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"L'estrazione è il trasferimento di composti solubili da una matrice solida a un solvente liquido. Le variabili sono sempre le stesse indipendentemente dal prodotto: temperatura (più alta = più veloce, ma rischio di estrarre composti indesiderati), tempo di contatto, dimensione delle particelle (più piccole = più superficie = più rapida estrazione), polarità del solvente (l'alcol estrae composti diversi dall'acqua, i grassi estraggono i liposolubili). L'acqua estrae zuccheri, acidi, caffeina, tannini. L'alcol estrae terpeni, esteri, polifenoli. I grassi estraggono i composti aromatici liposolubili. Conoscere la polarità è scegliere il solvente giusto per l'obiettivo."}'),
('proc-estrazione-alcol', 'Processo', 'Estrazione in alcol (infusione)', 'bar',
 '{"tipo":"fisico-chimico","scheda":"L'estrazione è il trasferimento di composti solubili da una matrice solida a un solvente liquido. Le variabili sono sempre le stesse indipendentemente dal prodotto: temperatura (più alta = più veloce, ma rischio di estrarre composti indesiderati), tempo di contatto, dimensione delle particelle (più piccole = più superficie = più rapida estrazione), polarità del solvente (l'alcol estrae composti diversi dall'acqua, i grassi estraggono i liposolubili). L'acqua estrae zuccheri, acidi, caffeina, tannini. L'alcol estrae terpeni, esteri, polifenoli. I grassi estraggono i composti aromatici liposolubili. Conoscere la polarità è scegliere il solvente giusto per l'obiettivo."}');

-- PRODOTTI-PROVA: le discipline EMERGONO (caffetteria, bar, cucina, fermentazione)
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-espresso',  'Prodotto', 'Espresso', 'caffetteria', '{}'),
('prod-filtro',    'Prodotto', 'Caffè filtro', 'caffetteria', '{}'),
('prod-te-infuso', 'Prodotto', 'Tè in infusione', 'caffetteria', '{}'),
('prod-bitter',    'Prodotto', 'Bitter / amaro infuso', 'bar', '{}'),
('prod-brodo',     'Prodotto', 'Brodo', 'cucina', '{}'),
('prod-mash-birra','Prodotto', 'Mash del malto (birra)', 'fermentazione', '{}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-caffe-sottoestratto',  'Errore', 'Caffè acido e sottile', 'caffetteria', '{"causa":"EY sotto 18%: sotto-estratto, macina troppo grossa o tempo corto"}'),
('err-caffe-sovraestratto',  'Errore', 'Caffè amaro e astringente', 'caffetteria', '{"causa":"EY sopra 22%: sovra-estratto, macina troppo fine o tempo lungo"}'),
('err-brodo-piatto', 'Errore', 'Brodo piatto', 'cucina', '{"causa":"estrazione insufficiente: poco tempo, poca superficie, acqua troppo abbondante"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- misurato_da: EY proprio + TDS CONDIVISO con Concentrazione (scoperta strutturale)
('fen-estrazione','cal-ey','misurato_da','{"nota":"numero proprio dell''estrazione"}'),
('fen-estrazione','cal-tds','misurato_da','{"nota":"TDS condiviso con Concentrazione — forza e estrazione sono indipendenti"}'),
-- realizzato_da
('fen-estrazione','proc-estrazione-acqua','realizzato_da','{}'),
('fen-estrazione','proc-estrazione-alcol','realizzato_da','{}'),
-- si_manifesta_in (discipline emergono)
('fen-estrazione','prod-espresso','si_manifesta_in','{"target":"EY 18-22%, TDS 8-12%","ruolo":"estrazione sotto pressione, concentrata"}'),
('fen-estrazione','prod-filtro','si_manifesta_in','{"target":"EY 18-22%, TDS 1,15-1,45%","ruolo":"gold cup SCA, estrazione per gravità"}'),
('fen-estrazione','prod-te-infuso','si_manifesta_in','{"target":"tempo+temperatura per tipo di tè","ruolo":"estrazione di tannini e aromi in acqua"}'),
('fen-estrazione','prod-bitter','si_manifesta_in','{"target":"giorni in alcol","ruolo":"estrazione alcolica di botaniche amare"}'),
('fen-estrazione','prod-brodo','si_manifesta_in','{"target":"ore a bassa ebollizione","ruolo":"estrazione di sapore, gelatina, minerali dalle ossa"}'),
('fen-estrazione','prod-mash-birra','si_manifesta_in','{"target":"65-68°C, 60 min","ruolo":"estrazione degli zuccheri fermentabili dal malto"}'),
-- fallisce_come
('prod-filtro','err-caffe-sottoestratto','fallisce_come','{}'),
('prod-filtro','err-caffe-sovraestratto','fallisce_come','{}'),
('prod-brodo','err-brodo-piatto','fallisce_come','{}');
