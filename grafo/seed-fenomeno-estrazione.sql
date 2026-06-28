-- ============================================================
-- FENOMENO ESTRAZIONE — costruito con la regola.
-- Numero-bersaglio PROPRIO: EY% (extraction yield, quanto soluto porti dal solido).
-- Condivide TDS% con Concentrazione (scoperta strutturale: EY e TDS si misurano
-- insieme ma sono indipendenti — forte≠estratto). Strumento: rifrattometro + bilancia.
-- tipo: fisico-chimico. Passa la regola.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-estrazione', 'Fenomeno', 'Estrazione', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"Portare i composti solubili da un solido a un liquido: il caffè dalla polvere, gli aromi dalle botaniche, il sapore dalle ossa. Due numeri indipendenti la governano: EY% (extraction yield) = quanto hai tirato fuori dal solido; TDS% = quanto è concentrata la bevanda finale. Si muovono separati: puoi avere forte ma sotto-estratto (ristretto) o debole ma sovra-estratto (lungo diluito). La leva sono macinatura, temperatura, tempo, rapporto.","numero_bersaglio":"EY 18-22% (zona dolce); TDS dipende dal metodo"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-ey', 'Calcolo', 'Extraction yield EY%', 'trasversale',
 '{"tipo":"fisico-chimico","formula":"EY% = (peso_bevanda x TDS%) / dose_secca","nota":"18-22% SCA; sotto=acido, sopra=amaro"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-estrazione-acqua', 'Processo', 'Estrazione in acqua', 'trasversale',
 '{"tipo":"fisico-chimico","scheda":"Acqua calda scioglie prima acidi, poi zuccheri, infine composti amari/astringenti. Fermarsi al punto giusto (EY 18-22% per il caffè) prende il dolce senza l''amaro. Macinatura fine, temperatura alta, tempo lungo = più estrazione."}'),
('proc-estrazione-alcol', 'Processo', 'Estrazione in alcol (infusione)', 'bar',
 '{"tipo":"fisico-chimico","scheda":"L''alcol è un solvente più potente dell''acqua per molti aromi: estrae oli essenziali e composti delle botaniche che l''acqua non prende. È la base di bitter, amari, gin infusi, vermouth."}');

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
