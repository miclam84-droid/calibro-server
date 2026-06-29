-- ============================================================
-- ARRICCHIMENTO DISCIPLINA: famiglia COLLINS/FIZZ/HIGHBALL (bar)
-- Il sour che incontra la carbonatazione: acidità + calore + CO2.
-- Il Collins è un sour allungato con soda — tre fenomeni, ABV basso.
-- Il Gin Tonic porta la carbonatazione + l'estrazione del chinino.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-template-collins', 'Processo', 'Template Collins/Highball', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Il sour che incontra la carbonatazione. Base: distillato + acido + zucchero (come il sour), ma costruito nel bicchiere alto su ghiaccio abbondante e allungato con soda. La soda non è solo acqua: rilascia gli aromi del distillato e abbassa l ABV (10-12% finale vs 18-22% del sour). Tecnica critica: non shakerasre la soda, aggiungerla ultima e mescolare delicatamente per non perdere la CO2."}'),
('proc-template-fizz', 'Processo', 'Template Fizz', 'bar',
 '{"tipo":"fisico-chimico","scheda":"Il cugino del Collins: stessa base (distillato + acido + zucchero) shakerata SENZA soda, poi soda aggiunta nel bicchiere senza ghiaccio. Più concentrato, più immediato, meno durata della carbonatazione. Con albume diventa Silver Fizz: la proteina crea la schiuma prima che la soda arrivi."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-tom-collins',  'Prodotto', 'Tom Collins', 'bar',
 '{"spec":"gin + limone + zucchero + soda, bicchiere alto su ghiaccio","abv_finale":"~10-12%"}'),
('prod-gin-tonic',    'Prodotto', 'Gin Tonic', 'bar',
 '{"spec":"gin + acqua tonica (rapporto 1:2), su ghiaccio abbondante","abv_finale":"~10-12%"}'),
('prod-aperol-spritz','Prodotto', 'Aperol Spritz', 'bar',
 '{"spec":"3 parti prosecco + 2 parti Aperol + 1 parte soda, su ghiaccio","abv_finale":"~8-10%"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-collins-piatto',  'Errore', 'Collins/Spritz piatto', 'bar',
 '{"causa":"soda aggiunta troppo presto o mescolata troppo vigorosamente: la CO2 scappa prima che il drink arrivi al cliente"}'),
('err-collins-acquoso', 'Errore', 'Collins acquoso', 'bar',
 '{"causa":"troppa soda o ghiaccio troppo sciolto: ABV scende sotto 10%, il distillato sparisce"}');

-- ============================================================
-- ARCHI
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- template
('prod-tom-collins','proc-template-collins','realizzato_da','{}'),
('prod-aperol-spritz','proc-template-collins','realizzato_da','{}'),
('prod-gin-tonic','proc-template-collins','realizzato_da','{}'),

-- ACIDITÀ: il Collins è un sour — porta l'acido
('fen-acidita','prod-tom-collins','si_manifesta_in',
 '{"target":"~0,8-1,0% titolabile (limone)","ruolo":"acido bilanciato dal zucchero, poi diluito dalla soda"}'),

-- CALORE: ghiaccio abbondante + soda fredda = drink molto più freddo e diluito del sour
('fen-calore','prod-tom-collins','si_manifesta_in',
 '{"target":"ABV finale ~10-12% (da ~40% a ~10% con la soda)","ruolo":"diluizione massima: la soda fa il grosso del lavoro"}'),
('fen-calore','prod-aperol-spritz','si_manifesta_in',
 '{"target":"ABV finale ~8-10%","ruolo":"prosecco + Aperol + soda: tre apporti di diluizione insieme"}'),

-- CARBONATAZIONE: il fenomeno che distingue questa famiglia dal sour
('fen-carbonatazione','prod-tom-collins','si_manifesta_in',
 '{"target":"soda club 2-3 volumi CO2","ruolo":"CO2 porta gli aromi del gin al naso; non shakerarla"}'),
('fen-carbonatazione','prod-gin-tonic','si_manifesta_in',
 '{"target":"tonica 3-4 volumi CO2","ruolo":"la tonica è carbonatazione + chinino amaro (estrazione)"}'),
('fen-carbonatazione','prod-aperol-spritz','si_manifesta_in',
 '{"target":"prosecco 3-4 volumi + soda","ruolo":"le bollicine del prosecco più la soda: doppia fonte di CO2"}'),

-- ESTRAZIONE: il chinino della tonica è un composto amaro estratto
('fen-estrazione','prod-gin-tonic','si_manifesta_in',
 '{"target":"chinino in acqua tonica","ruolo":"la tonica E un amaro: il chinino è estratto dalla corteccia di china. Ponte col Negroni (Campari) e col Bitter"}'),

-- fallisce_come
('prod-tom-collins','err-collins-piatto','fallisce_come','{}'),
('prod-gin-tonic','err-collins-acquoso','fallisce_come','{}');
