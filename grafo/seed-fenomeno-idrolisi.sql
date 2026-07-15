-- ============================================================
-- FAMIGLIA IDROLISI ENZIMATICA (enzima + acqua spezzano un legame)
-- Regola di partizione: OK — tre numeri diversi, tre strumenti diversi.
--   amilolisi  -> DE (dextrose equivalent) + temperatura amilasi
--   proteolisi -> grado di idrolisi DH%
--   lipolisi   -> numero di acidità / FFA%
-- Autolisi = tecnica (enzimi endogeni), non fenomeno: usa questi numeri.
-- Fonti: scienza del mash (amilasi 60-75C, DE); proteolisi (DH% 16-35%,
--   proteasi 45-55C); lipolisi formaggi (numero di acidità).
-- ============================================================

-- ---------- AMILOLISI ----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-amilolisi', 'Fenomeno', 'Amilolisi', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"amilasi: alfa ~65-75C, beta ~60-65C · pH 4,4-5,5 · DE (dextrose equivalent) 0-100 = grado di conversione dell amido in zuccheri",
   "strumento":"termometro (temperatura di conversione) · DE / rifrattometro",
   "scheda":"L'amilolisi è la degradazione enzimatica dell'amido in zuccheri più semplici. Beta-amilasi e alfa-amilasi attaccano le catene di amilosio e amilopectina in punti diversi: la beta produce maltosio (fermentabile), l'alfa produce destrine (non fermentabili, contribuiscono al corpo). Nella produzione della birra, la temperatura del mash determina quale enzima è più attivo e quindi il profilo fermentescibile del mosto. A 65°C prevale la beta-amilasi: birra secca e alcolica. A 68-70°C prevale l'alfa: birra corposa con più residuo dolce. Nel lievito madre, le amilasi presenti nella farina convertono l'amido in zuccheri che alimentano i lieviti — la maturazione del pane dipende anche da questo equilibrio."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-malto', 'Prodotto', 'Malto (orzo maltato)', 'bar',
 '{"target":"germinazione attiva le amilasi · essiccazione le ferma · nel mash 62-72C convertono l amido in zuccheri fermentabili",
   "strumento":"termometro + DE"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-amilolisi', 'prod-mash-birra', 'si_manifesta_in',
 '{"target":"62-72C","causa":"La temperatura di ammostamento decide quali amilasi lavorano: piu basso = mosto piu fermentabile e birra secca, piu alto = piu corpo residuo"}'),
('fen-amilolisi', 'prod-madre', 'si_manifesta_in',
 '{"target":"amilasi della farina","causa":"Le amilasi della farina liberano zuccheri che nutrono i lieviti e danno dolcezza e colore alla crosta"}'),
('fen-amilolisi', 'prod-malto', 'si_manifesta_in',
 '{"target":"germinazione + mash","causa":"La maltazione sviluppa gli enzimi; nel mash convertono l amido dell orzo in zuccheri per la fermentazione"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-amido-non-converte', 'Errore', 'Amido non convertito (mash bloccato)', 'bar',
 '{"causa":"Temperatura troppo alta denatura le amilasi prima della conversione, o troppo bassa e lente: l amido resta, poco zucchero fermentabile","soluzione":"Tenere il mash nella finestra 62-72C; se serve piu corpo alzare, piu secchezza abbassare"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-amilolisi', 'err-amido-non-converte', 'fallisce_come',
 '{"causa":"Amilasi denaturate o troppo lente: conversione incompleta"}'),
('fen-amilolisi', 'fen-gelatinizzazione', 'influenza',
 '{"nota":"L amido deve prima gelatinizzare (assorbire acqua e aprirsi) perche l amilasi lo raggiunga: gelatinizzazione e amilolisi lavorano in sequenza"}'),
('fen-amilolisi', 'fen-fermentazione', 'influenza',
 '{"nota":"L amilolisi prepara il cibo alla fermentazione: fabbrica gli zuccheri che poi i lieviti trasformano in alcol e CO2"}');

-- ---------- PROTEOLISI ----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-proteolisi', 'Fenomeno', 'Proteolisi', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"proteasi ~45-55C, pH 5,5-8 · grado di idrolisi DH% (tipico 16-35%) = quanto la proteina e spezzata in peptidi e amminoacidi",
   "strumento":"grado di idrolisi (DH%) · tempo x temperatura",
   "scheda":"L'amilolisi è la degradazione enzimatica dell'amido in zuccheri più semplici. Beta-amilasi e alfa-amilasi attaccano le catene di amilosio e amilopectina in punti diversi: la beta produce maltosio (fermentabile), l'alfa produce destrine (non fermentabili, contribuiscono al corpo). Nella produzione della birra, la temperatura del mash determina quale enzima è più attivo e quindi il profilo fermentescibile del mosto. A 65°C prevale la beta-amilasi: birra secca e alcolica. A 68-70°C prevale l'alfa: birra corposa con più residuo dolce. Nel lievito madre, le amilasi presenti nella farina convertono l'amido in zuccheri che alimentano i lieviti — la maturazione del pane dipende anche da questo equilibrio."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-garum', 'Prodotto', 'Garum / colatura', 'cucina',
 '{"target":"sale ~20% + tempo (mesi) · le proteasi del pesce spezzano le proteine in amminoacidi umami · alto DH%",
   "strumento":"tempo + valutazione sensoriale (umami)"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-proteolisi', 'prod-carne-stagionata', 'si_manifesta_in',
 '{"target":"settimane a 1-3C","causa":"Le proteasi endogene (autolisi) ammorbidiscono il muscolo e liberano amminoacidi che concentrano il sapore: la frollatura e proteolisi controllata"}'),
('fen-proteolisi', 'prod-garum', 'si_manifesta_in',
 '{"target":"alto DH%","causa":"Sale e tempo lasciano lavorare le proteasi del pesce fino a un concentrato di amminoacidi umami; il sale tiene a bada i patogeni intanto"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-frollatura-eccessiva', 'Errore', 'Proteolisi eccessiva (sapore/consistenza off)', 'cucina',
 '{"causa":"Troppo tempo o temperatura troppo alta: la proteolisi va oltre, la consistenza diventa molle e compaiono note ammoniacali/putride","soluzione":"Controllare temperatura (1-3C) e tempo; fermare la frollatura al punto voluto"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-proteolisi', 'err-frollatura-eccessiva', 'fallisce_come',
 '{"causa":"Idrolisi spinta oltre: struttura persa, off-flavor"}'),
('fen-proteolisi', 'fen-coagulazione', 'influenza',
 '{"nota":"E il rovescio della coagulazione: la coagulazione costruisce la rete di proteine (uovo, carne cotta), la proteolisi la smonta in frammenti saporiti"}'),
('fen-proteolisi', 'fen-amilolisi', 'influenza',
 '{"nota":"Stessa famiglia, l idrolisi: enzima + acqua che spezzano un legame. Nel koji corrono insieme, amilasi sugli amidi e proteasi sulle proteine"}');

-- ---------- LIPOLISI ----------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-lipolisi', 'Fenomeno', 'Lipolisi', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"numero di acidita / acidi grassi liberi (FFA%) = grado di lipolisi · e la leva della piccantezza dei formaggi erborinati",
   "strumento":"numero di acidita (titolazione)",
   "scheda":"L'amilolisi è la degradazione enzimatica dell'amido in zuccheri più semplici. Beta-amilasi e alfa-amilasi attaccano le catene di amilosio e amilopectina in punti diversi: la beta produce maltosio (fermentabile), l'alfa produce destrine (non fermentabili, contribuiscono al corpo). Nella produzione della birra, la temperatura del mash determina quale enzima è più attivo e quindi il profilo fermentescibile del mosto. A 65°C prevale la beta-amilasi: birra secca e alcolica. A 68-70°C prevale l'alfa: birra corposa con più residuo dolce. Nel lievito madre, le amilasi presenti nella farina convertono l'amido in zuccheri che alimentano i lieviti — la maturazione del pane dipende anche da questo equilibrio."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-formaggio-stagionato', 'Prodotto', 'Formaggio stagionato / erborinato', 'cucina',
 '{"target":"lipasi (native o microbiche) alzano il numero di acidita · piu lipolisi = piu piccante · erborinati la spingono",
   "strumento":"numero di acidita + valutazione sensoriale"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-lipolisi', 'prod-formaggio-stagionato', 'si_manifesta_in',
 '{"target":"numero di acidita crescente","causa":"Le lipasi liberano acidi grassi che danno la nota piccante: negli erborinati le muffe la spingono, e la firma del sapore"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-lipolisi-rancida', 'Errore', 'Lipolisi indesiderata (rancido saponoso)', 'cucina',
 '{"causa":"Lipasi attive dove non le vuoi (latte crudo mal conservato, grassi): acidi grassi liberi che sanno di sapone/rancido","soluzione":"Freddo e pastorizzazione fermano le lipasi; conservare i grassi al riparo da enzimi e calore"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-lipolisi', 'err-lipolisi-rancida', 'fallisce_come',
 '{"causa":"Acidi grassi liberi in eccesso: nota saponosa/rancida"}'),
('fen-lipolisi', 'fen-ossidazione', 'influenza',
 '{"nota":"Due passi dello stesso irrancidimento: la lipolisi (enzimatica) libera gli acidi grassi, l ossidazione poi li spezza in aldeidi rancide. Insieme guastano un grasso"}'),
('fen-lipolisi', 'fen-proteolisi', 'influenza',
 '{"nota":"Nel formaggio stagionato corrono insieme: proteolisi sulle caseine, lipolisi sui grassi. Stessa famiglia idrolisi, substrati diversi"}');
