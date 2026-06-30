-- ============================================================
-- AGGANCI COMPLETI — lavoro editoriale.
-- Prodotti che vivevano sotto UN fenomeno ma ne toccano di più.
-- Ogni riga è una connessione vera del mestiere, aggiunta a mano.
-- Niente nuovi nodi: solo archi si_manifesta_in mancanti.
-- ============================================================

INSERT INTO edges (from_id, to_id, relation, data) VALUES
-- SOUR: non solo acidità — anche concentrazione (dolce) e calore (diluizione shake)
('fen-concentrazione','prod-sour','si_manifesta_in','{"target":"~12 Brix","ruolo":"la dolcezza che bilancia l acido"}'),
('fen-calore','prod-sour','si_manifesta_in','{"target":"27% diluizione","ruolo":"lo shake raffredda e diluisce"}'),

-- SCIROPPO: concentrazione + osmosi (lo zucchero alto conserva)
('fen-osmosi','prod-sciroppo','si_manifesta_in','{"target":"65 Brix (2:1)","ruolo":"lo zucchero denso resiste ai microbi"}'),

-- CAFFÈ: concentrazione (TDS) + calore (acqua di estrazione 90-96°C)
('fen-calore','prod-caffe','si_manifesta_in','{"target":"90-96°C","ruolo":"la temperatura governa la resa di estrazione"}'),

-- DRINK FREDDO: calore + concentrazione (l acqua di fusione cambia l ABV)
('fen-concentrazione','prod-drink-freddo','si_manifesta_in','{"target":"ABV finale","ruolo":"l acqua di fusione diluisce la concentrazione alcolica"}'),

-- CARNE SOUS-VIDE: calore + struttura (denaturazione = cambio struttura proteica)
('fen-struttura','prod-sousvide','si_manifesta_in','{"target":"collagene>55°C","ruolo":"le proteine cambiano struttura in sequenza"}'),

-- CROISSANT/SFOGLIA: calore (vapore) + struttura (glutine rilassato) + concentrazione (idratazione bassa)
('fen-struttura','prod-sfoglia','si_manifesta_in','{"target":"glutine rilassato","ruolo":"rete elastica che regge i fogli di burro"}'),
('fen-concentrazione','prod-sfoglia','si_manifesta_in','{"target":"50-55% + 30% burro","ruolo":"impasto magro, il grasso è a strati"}'),

-- FOCACCIA: concentrazione + struttura (glutine medio) + calore (forno)
('fen-struttura','prod-focaccia','si_manifesta_in','{"target":"glutine medio","ruolo":"rete morbida che tiene gli alveoli"}'),
('fen-calore','prod-focaccia','si_manifesta_in','{"target":"220-230°C","ruolo":"crosta sotto, mollica soffice sopra"}'),

-- PIZZA ROMANA: concentrazione + struttura + calore
('fen-struttura','prod-pizza-rom','si_manifesta_in','{"target":"glutine medio-forte","ruolo":"regge l alta idratazione"}'),
('fen-calore','prod-pizza-rom','si_manifesta_in','{"target":"280-320°C","ruolo":"croccante sotto, alveolata sopra"}'),

-- INJERA: struttura (idrocolloidi) + acidità (fermentazione lattica 2-3 giorni) + calore (mitad)
('fen-acidita','prod-injera','si_manifesta_in','{"target":"pH acido","ruolo":"fermentazione lattica lunga, sapore acido"}'),
('fen-calore','prod-injera','si_manifesta_in','{"target":"mitad ~180°C","ruolo":"vapore buca la superficie, occhi tipici"}'),

-- PANETTONE: osmosi + struttura (glutine fortissimo) + acidità (madre pH 4,1) + calore (lievitazione + cottura)
('fen-struttura','prod-panettone','si_manifesta_in','{"target":"W360+ glutine fortissimo","ruolo":"regge il peso di uova e burro"}'),
('fen-acidita','prod-panettone','si_manifesta_in','{"target":"madre pH 4,1","ruolo":"acidità che dà forza e conservazione"}'),
('fen-calore','prod-panettone','si_manifesta_in','{"target":"28-30°C lievitazione","ruolo":"la madre stiff tripla in 3-4h"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
