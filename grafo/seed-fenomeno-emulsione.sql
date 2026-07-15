-- ============================================================
-- FENOMENO: Emulsione (dispersione stabile di due liquidi immiscibili)
-- Regola di partizione: OK
-- Numero-bersaglio: frazione olio + dimensione goccia + rapporto emulsionante
--   maionese ~67-80% olio (oltre inverte/impazzisce) · goccia 0,5-20 um
--   1 tuorlo emulsiona ~150-240 ml olio
-- Strumento: rapporto emulsionante/olio · dimensione goccia (visiva/microscopio)
-- Si manifesta in: maionese, vinaigrette, ganache, gelato
-- Fonti: Lund Univ. (phase inversion mayonnaise); studi rheology maionese; brevetti O/W.
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-emulsione', 'Fenomeno', 'Emulsione', 'trasversale',
 '{"tipo":"fisico-chimico",
   "numero_bersaglio":"frazione olio ~67-80% (oltre inverte e impazzisce) · goccia 0,5-20 um (piu piccola = piu stabile) · 1 tuorlo emulsiona ~150-240 ml olio",
   "strumento":"rapporto emulsionante/olio · dimensione della goccia (visiva/microscopio)",
   "scheda":"Un'emulsione è una dispersione di due liquidi immiscibili (tipicamente olio e acqua) stabilizzata da un emulsionante. La lecitina del tuorlo d'uovo è l'emulsionante naturale più efficace in cucina: le sue molecole hanno una testa idrofila e una coda lipofila che si posizionano all'interfaccia tra le gocce di olio e l'acqua, impedendone la coalescenza. L'aggiunta di olio a filo è necessaria perché disperde l'olio in goccioline abbastanza piccole da essere stabilizzate prima che si aggreghino. Temperatura omogenea tra olio e acqua riduce la tensione interfacciale. L'acido abbassa il pH aumentando la stabilità della lecitina. Se l'emulsione impazzisce, si è aggiunto olio troppo velocemente o la temperatura era diversa tra i due liquidi."}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-maionese', 'Prodotto', 'Maionese', 'cucina',
 '{"target":"67-80% olio · tuorlo ~6-9% · olio a filo, stessa temperatura · acido (limone/aceto) stabilizza",
   "strumento":"rapporto tuorlo:olio + valutazione (cremosita)"}'),
('prod-vinaigrette', 'Prodotto', 'Vinaigrette', 'cucina',
 '{"target":"emulsione instabile (temporanea) ~3:1 olio:aceto · senape come emulsionante per tenerla piu a lungo",
   "strumento":"rapporto + valutazione visiva"}'),
('prod-ganache', 'Prodotto', 'Ganache', 'pasticceria',
 '{"target":"emulsione grasso-in-acqua di cioccolato e panna · rapporto cioccolato:panna 1:1 (montata) fino a 2:1 (soda) · temperatura di emulsionamento ~35-40C",
   "strumento":"rapporto + temperatura"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-emulsione', 'prod-maionese', 'si_manifesta_in',
 '{"target":"67-80% olio","causa":"Il tuorlo mette lecitina e proteine all interfaccia: reggono le gocce d olio finche il rapporto e rispettato. Olio troppo in fretta = gocce che coalescono = impazzita"}'),
('fen-emulsione', 'prod-vinaigrette', 'si_manifesta_in',
 '{"target":"~3:1 olio:aceto","causa":"Senza un vero emulsionante e temporanea: si separa in fretta. La senape la stabilizza abbassando la tensione fra le fasi"}'),
('fen-emulsione', 'prod-ganache', 'si_manifesta_in',
 '{"target":"1:1 - 2:1","causa":"Il grasso del cioccolato si disperde nell acqua della panna: se si scalda troppo o si mescola male, il grasso esce e la ganache si spezza (impazzisce)"}');

INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-emulsione-impazzita', 'Errore', 'Emulsione impazzita (si separa)', 'cucina',
 '{"causa":"Olio aggiunto troppo in fretta, rapporto emulsionante superato, o shock di temperatura: le gocce coalescono e le due fasi si separano","soluzione":"Ripartire da un nuovo tuorlo (o poca acqua calda per la ganache) e reincorporare a filo l emulsione impazzita, lentamente"}'),
('err-ganache-spezzata', 'Errore', 'Ganache spezzata (grasso che esce)', 'pasticceria',
 '{"causa":"Temperatura troppo alta o raffreddamento sbagliato: il grasso del cioccolato si separa e la ganache diventa granulosa e oleosa","soluzione":"Riscaldare dolcemente a ~35C e frullare con un goccio di panna calda per riformare l emulsione"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-emulsione', 'err-emulsione-impazzita', 'fallisce_come',
 '{"causa":"Coalescenza: le gocce si riuniscono, le fasi si separano"}'),
('fen-emulsione', 'err-ganache-spezzata', 'fallisce_come',
 '{"causa":"Il grasso esce dall emulsione per calore o rapporto sbagliato"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-emulsione', 'fen-montaggio', 'influenza',
 '{"nota":"Stessa fisica di interfaccia del montaggio: un emulsionante o una proteina che si mette al confine fra due fasi. Li e aria intrappolata, qui un liquido nell altro"}'),
('fen-emulsione', 'fen-struttura', 'influenza',
 '{"nota":"L emulsione e una forma di struttura: la rete che tiene disperse le gocce. Idrocolloidi e proteine la rinforzano, come nel gelato e nelle salse legate"}');
