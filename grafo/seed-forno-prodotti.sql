-- ============================================================
-- FORNO — popolamento prodotti.
-- I lievitati del mondo come nodi Prodotto, agganciati ai
-- fenomeni che GIÀ esistono (Concentrazione, Calore, Struttura,
-- Osmosi, Acidità). Ogni pane si dispone sugli assi scientifici.
-- Niente nuovi fenomeni: solo prodotti + tecniche + errori.
-- ============================================================

-- ---- PRODOTTI (i pani del mondo) ---------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('prod-pizza-nap',   'Prodotto', 'Pizza napoletana',      'bakery', '{"idr":"60-65%","forno":"430°C/90s","glutine":"forte 00"}'),
('prod-pizza-rom',   'Prodotto', 'Pizza romana in teglia','bakery', '{"idr":"75-85%","forno":"280-320°C","glutine":"medio-forte"}'),
('prod-baguette',    'Prodotto', 'Baguette',              'bakery', '{"idr":"68-75%","ferm":"poolish","forno":"240°C+vapore"}'),
('prod-segale',      'Prodotto', 'Pane di segale',        'bakery', '{"idr":"80-100%","acido":"pH 3,8-4,2","glutine":"debole"}'),
('prod-ciabatta',    'Prodotto', 'Ciabatta',              'bakery', '{"idr":"75-85%","ferm":"biga","glutine":"forte"}'),
('prod-sourdough',   'Prodotto', 'Sourdough',             'bakery', '{"idr":"72-80%","acido":"media-alta","forno":"Dutch oven"}'),
('prod-naan',        'Prodotto', 'Naan',                  'bakery', '{"idr":"60-65%","acido":"yogurt","forno":"tandoor 480°C"}'),
('prod-focaccia',    'Prodotto', 'Focaccia',              'bakery', '{"idr":"70-80%","grasso":"olio","forno":"220°C"}'),
('prod-bagel',       'Prodotto', 'Bagel',                 'bakery', '{"idr":"55-60%","glutine":"fortissimo","cottura":"bollito+forno"}');
-- prod-injera, prod-panettone, prod-sfoglia (croissant), prod-impasto (pane base),
-- prod-pane-madre esistono già dai ponti precedenti.

-- ---- TECNICHE ----------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('tec-pieghe',     'Tecnica', 'Pieghe / tourage', 'bakery', '{"nota":"3 giri da 3 = 27 strati, 4 = 81"}'),
('tec-autolisi',   'Tecnica', 'Autolisi', 'bakery', '{"nota":"riposo farina+acqua: glutine si sviluppa senza impastare"}'),
('tec-retard',     'Tecnica', 'Retard in frigo (4°C)', 'bakery', '{"nota":"fermentazione quasi ferma, aroma dagli enzimi"}');

-- ---- ERRORI ------------------------------------------------
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-pizza-gommosa','Errore', 'Pizza gommosa/cruda', 'bakery', '{"causa":"forno non abbastanza caldo per quell''idratazione"}'),
('err-alveoli-no',   'Errore', 'Mollica chiusa, niente alveoli', 'bakery', '{"causa":"idratazione bassa o glutine poco sviluppato"}');

-- ============================================================
-- ARCHI — ogni pane si aggancia ai fenomeni sugli assi
-- ============================================================
INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- CONCENTRAZIONE (idratazione): tutti i pani
('fen-concentrazione','prod-pizza-nap','si_manifesta_in','{"target":"60-65% idr","ruolo":"bassa: tiene a 430°C"}'),
('fen-concentrazione','prod-pizza-rom','si_manifesta_in','{"target":"75-85% idr","ruolo":"alta: mollica soffice"}'),
('fen-concentrazione','prod-baguette','si_manifesta_in','{"target":"68-75% idr","ruolo":"media: crosta+alveoli"}'),
('fen-concentrazione','prod-segale','si_manifesta_in','{"target":"80-100% idr","ruolo":"altissima: assorbe la segale"}'),
('fen-concentrazione','prod-ciabatta','si_manifesta_in','{"target":"75-85% idr","ruolo":"alta: alveoli grandi"}'),
('fen-concentrazione','prod-sourdough','si_manifesta_in','{"target":"72-80% idr","ruolo":"alta: mollica aperta"}'),
('fen-concentrazione','prod-naan','si_manifesta_in','{"target":"60-65% idr","ruolo":"media: soffice"}'),
('fen-concentrazione','prod-focaccia','si_manifesta_in','{"target":"70-80% idr","ruolo":"alta+olio"}'),
('fen-concentrazione','prod-bagel','si_manifesta_in','{"target":"55-60% idr","ruolo":"bassa: mollica densa"}'),
-- CALORE (forno / Q10): pani con cottura caratteristica
('fen-calore','prod-pizza-nap','si_manifesta_in','{"target":"430°C / 90s","ruolo":"calore estremo, cottura lampo"}'),
('fen-calore','prod-baguette','si_manifesta_in','{"target":"240°C + vapore","ruolo":"il vapore fa la crosta"}'),
('fen-calore','prod-naan','si_manifesta_in','{"target":"tandoor 480°C","ruolo":"parete rovente"}'),
('fen-calore','prod-bagel','si_manifesta_in','{"target":"bollito poi 220°C","ruolo":"bollitura gelatinizza la crosta"}'),
-- STRUTTURA (glutine sì/no): la forza della rete
('fen-struttura','prod-pizza-nap','si_manifesta_in','{"target":"glutine forte (00)","ruolo":"regge la lunga maturazione"}'),
('fen-struttura','prod-segale','si_manifesta_in','{"target":"glutine debole","ruolo":"poca gliadina: mollica fitta"}'),
('fen-struttura','prod-bagel','si_manifesta_in','{"target":"glutine fortissimo","ruolo":"mollica gommosa e densa"}'),
('fen-struttura','prod-ciabatta','si_manifesta_in','{"target":"glutine forte","ruolo":"trattiene alveoli grandi"}'),
-- ACIDITÀ: i pani acidi
('fen-acidita','prod-segale','si_manifesta_in','{"target":"pH 3,8-4,2","ruolo":"pasta acida lunga"}'),
('fen-acidita','prod-sourdough','si_manifesta_in','{"target":"media-alta","ruolo":"sapore dalla madre"}'),
-- TECNICHE controllano i fenomeni
('fen-struttura','tec-pieghe','controllato_con','{}'),
('fen-struttura','tec-autolisi','controllato_con','{}'),
('fen-calore','tec-retard','controllato_con','{"nota":"il freddo rallenta, sposta nel tempo"}'),
-- ERRORI
('prod-pizza-nap','err-pizza-gommosa','fallisce_come','{}'),
('prod-ciabatta','err-alveoli-no','fallisce_come','{}');
