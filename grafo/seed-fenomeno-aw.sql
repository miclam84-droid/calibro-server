-- ============================================================
-- FENOMENO: Attività acqua (Aw)
-- Regola: ✓ zona grigia — strumento professionale (awmetro)
-- Numero-bersaglio: 0-1 (adimensionale)
-- Nota: awmetro non comune nel piccolo laboratorio — marcato
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-aw', 'Fenomeno', 'Attività acqua (Aw)', 'trasversale',
 '{"tipo":"fisico-chimico",
   "target":"Aw 0,85 (soglia sicurezza) · 0,70 (muffa) · 0,60 (osmofili) · <0,60 (shelf-stable)",
   "strumento":"awmetro (strumento professionale — non comune nel piccolo laboratorio)",
   "nota_strumento":"L awmetro non è uno strumento da banco quotidiano come il termometro o il pHmetro. È uno strumento di laboratorio usato principalmente in HACCP e R&D. Matter lo include perché governa la sicurezza alimentare in modo diretto.",
   "scheda":"L attività dell acqua (Aw) misura la quantità di acqua libera disponibile per i microrganismi — non l acqua totale, ma quella che i batteri possono usare per crescere. Va da 0 (nessuna acqua libera) a 1 (acqua pura). Sopra 0,85 i patogeni pericolosi possono crescere. Sopra 0,70 le muffe trovano condizioni favorevoli. Sotto 0,60 anche i microbi più resistenti (osmofili) non sopravvivono. Abbassare l Aw è uno dei metodi di conservazione più antichi: il sale lega l acqua libera (osmosi), lo zucchero fa lo stesso, l essiccazione la rimuove fisicamente. Un formaggio stagionato, una confettura ad alto Brix, un prosciutto crudo — tutti conservati in parte grazie all Aw bassa. Il collegamento con la concentrazione (Brix) è diretto: più Brix = meno Aw = più conservabile."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-confettura-conserva', 'Prodotto', 'Confettura / conserva shelf-stable', 'cucina',
 '{"target":"Aw <0,85 · Brix ≥65 · pH <4,6","strumento":"awmetro + rifrattometro + pHmetro"}'),
('prod-carne-stagionata', 'Prodotto', 'Carne stagionata / prosciutto crudo', 'cucina',
 '{"target":"Aw 0,87-0,92 a fine stagionatura","strumento":"awmetro"}'),
('prod-pane-conservazione', 'Prodotto', 'Pane e prodotti da forno (shelf life)', 'bakery',
 '{"target":"Aw 0,94-0,97 pane fresco · <0,85 per shelf life estesa","strumento":"awmetro"}'),
('prod-cioccolato-aw', 'Prodotto', 'Cioccolato e praline (sicurezza)', 'pasticceria',
 '{"target":"Aw <0,70 per cioccolato · ganache fresca 0,80-0,87","strumento":"awmetro"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-aw', 'prod-confettura-conserva', 'si_manifesta_in',
 '{"target":"Aw <0,85","causa":"Zucchero ad alta concentrazione lega l acqua libera: Brix 65+ porta Aw sotto la soglia di sicurezza"}'),
('fen-aw', 'prod-carne-stagionata', 'si_manifesta_in',
 '{"target":"Aw 0,87-0,92","causa":"Il sale penetra la carne per osmosi, lega l acqua libera e abbassa l Aw sotto la soglia di crescita patogeni"}'),
('fen-aw', 'prod-pane-conservazione', 'si_manifesta_in',
 '{"target":"Aw 0,94-0,97","causa":"Il pane fresco ha Aw alta — muffe crescono in 3-5 giorni. Aggiungere sale, zucchero o modificare la formulazione abbassa l Aw"}'),
('fen-aw', 'prod-cioccolato-aw', 'si_manifesta_in',
 '{"target":"Aw <0,70 cioccolato · 0,80-0,87 ganache","causa":"Il cioccolato puro ha Aw molto bassa (stabile). Le ganache fresche con panna hanno Aw più alta — shelf life limitata"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-muffa-confettura', 'Errore', 'Muffa in confettura / conserva', 'cucina',
 '{"causa":"Aw >0,85: Brix insufficiente o pH non abbastanza basso","soluzione":"Portare Brix a 65+ E pH sotto 4,6 — entrambi i parametri devono essere rispettati"}'),
('err-ganache-deperita', 'Errore', 'Ganache che si deteriora rapidamente', 'pasticceria',
 '{"causa":"Aw >0,87: troppa panna o acqua libera nella ricetta","soluzione":"Ridurre il contenuto d acqua, aggiungere glucosio o sorbitolo come umettanti che abbassano l Aw"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-aw', 'err-muffa-confettura', 'fallisce_come',
 '{"causa":"Aw sopra la soglia di sicurezza 0,85"}'),
('fen-aw', 'err-ganache-deperita', 'fallisce_come',
 '{"causa":"Aw troppo alta per la shelf life desiderata"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-aw', 'fen-concentrazione', 'influenza',
 '{"nota":"Brix alto → Aw bassa: la relazione è diretta. Più soluti disciolti = meno acqua libera disponibile"}'),
('fen-aw', 'fen-osmosi', 'influenza',
 '{"nota":"L osmosi è il meccanismo fisico con cui sale e zucchero abbassano l Aw: attirano l acqua libera legandola ai soluti"}'),
('fen-aw', 'fen-fermentazione', 'influenza',
 '{"nota":"Aw <0,85 blocca la crescita batterica — limite inferiore per la fermentazione sicura controllata"}');
