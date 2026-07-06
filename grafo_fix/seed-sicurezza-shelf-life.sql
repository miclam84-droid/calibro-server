-- ============================================================
-- SICUREZZA — SHELF LIFE E DETERIORAMENTO
-- La shelf life non dipende da un solo parametro: è la
-- combinazione di Aw + pH + temperatura + O2 che determina
-- quanto dura un alimento in sicurezza.
-- Numero bersaglio: giorni a temperatura di conservazione.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-shelf-life', 'Fenomeno', 'Shelf life e deterioramento', 'sicurezza',
 '{"tipo":"biologico","numero_bersaglio":"giorni a T di conservazione · funzione di Aw + pH + T + O2","scheda":"La shelf life non è una proprietà fissa dell''alimento — è il risultato della combinazione di quattro parametri fisici: Aw (acqua disponibile per i microbi), pH (acidità che inibisce i patogeni), temperatura di conservazione, presenza di ossigeno. Cambiane uno e la shelf life cambia. Un impasto a pH 4,0 dura il doppio di uno a pH 5,5. Un fermentato con Aw 0,92 ha shelf life diversa da uno con Aw 0,85. Il numero bersaglio è sempre relativo alle condizioni di conservazione dichiarate.","shelf_life_disclaimer":"valore orientativo basato su modelli scientifici — non è una certificazione né una data di scadenza"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('cal-shelf-life-stima', 'Calcolo', 'Stima shelf life orientativa', 'sicurezza',
 '{"formula":"giorni = f(Aw, pH, T_conservazione, O2) — modello semplificato Hurdle Technology","campi_input":["aw","ph","temperatura_frigo","presenza_ossigeno"],"output":"shelf_life_giorni (stima orientativa)","nota":"non sostituisce test microbiologici reali"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('proc-hurdle-technology', 'Processo', 'Hurdle technology', 'sicurezza',
 '{"nota":"combinare più ostacoli fisici (Aw bassa + pH acido + freddo + assenza O2) per ottenere stabilità microbiologica senza trattamenti drastici — ogni ostacolo da solo non basta, la combinazione sì"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-shelf-life-errata', 'Errore', 'Stima shelf life errata', 'sicurezza',
 '{"sintomo":"prodotto deteriorato prima della data indicata, o scartato troppo presto","causa":"calcolo basato su un solo parametro (es. solo temperatura) ignorando Aw o pH","correzione":"valutare tutti e quattro i parametri combinati; in caso di dubbio, test microbiologico"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-shelf-life', 'cal-shelf-life-stima', 'misurato_da', '{}'),
('fen-shelf-life', 'proc-hurdle-technology', 'controllato_con', '{}'),
('fen-shelf-life', 'err-shelf-life-errata', 'fallisce_come', '{}'),
('fen-aw', 'fen-shelf-life', 'determina', '{}'),
('fen-acidita', 'fen-shelf-life', 'determina', '{}'),
('fen-zona-pericolo', 'fen-shelf-life', 'determina', '{}'),
('fen-concentrazione', 'fen-shelf-life', 'influenza', '{}');