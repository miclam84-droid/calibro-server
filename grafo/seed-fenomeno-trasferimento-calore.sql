-- TRASFERIMENTO DI CALORE
-- Cross-disciplina: raffreddamento cocktail, cottura, pastorizzazione, infusione
-- Strumento: termometro a sonda

INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-trasferimento-calore', 'Fenomeno', 'Trasferimento di calore', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Calore specifico acqua: 4,18 J/g°C · ghiaccio latente: 334 J/g · pastorizzazione: 72°C×15s o 63°C×30min",
   "strumento":"Termometro a sonda · termocoppia · sonda a infrarossi",
   "principio":"Il calore si trasferisce per conduzione (contatto diretto solido-solido, es. padella-carne), convezione (movimento del fluido, es. acqua bollente, forno a convezione) e irraggiamento (trasmissione elettromagnetica, es. griglia, salamandra, microonde). La velocità dipende dal gradiente di temperatura (ΔT), dalla superficie di contatto e dalla conducibilità termica del materiale. Il ghiaccio è un caso particolare: per sciogliersi da 0°C a 0°C assorbe 334 J/g — 80 volte l''energia necessaria per riscaldare un grammo d''acqua di 1°C. Questo è il motivo per cui il ghiaccio raffredda in modo così efficiente. Il principio della pastorizzazione (combinazione tempo×temperatura) si basa sulla distruzione logaritmica dei patogeni — la stessa riduzione batterica si ottiene a temperature diverse con tempi diversi.",
   "formula":"Q = m × c × ΔT (calore sensibile) · Q = m × L (calore latente di fusione)",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-trasferimento-calore', 'prod-sour', 'si_manifesta_in',
 '{"target":"T finale drink: -5/-7°C (shake) · tempo: 10-12s","causa":"Il calore si trasferisce dal liquido al ghiaccio: 334 J/g per sciogliere + 4,18 J/g°C per raffreddare. In 10s si raggiunge l equilibrio"}'),
('fen-trasferimento-calore', 'prod-carne-rosolata', 'si_manifesta_in',
 '{"target":"T interna target: 55-57°C (medium rare) · gradiente esterno-interno: 20-30°C","causa":"La crosta a 150°C e l interno a 55°C: la conduzione è lenta nella carne (bassa conducibilità termica)"}'),
('fen-trasferimento-calore', 'prod-impasto', 'si_manifesta_in',
 '{"target":"T interna cottura: 96-98°C · T crosta: 150-200°C","causa":"Il trasferimento di calore nel pane è più lento al centro che in superficie — da qui il gradiente interno/esterno"}'),
('fen-trasferimento-calore', 'prod-espresso', 'si_manifesta_in',
 '{"target":"T acqua estrazione: 90-96°C · ΔT da group head: -2-4°C","causa":"La temperatura dell acqua al gruppo cade leggermente rispetto alla caldaia: il trasferimento termico attraverso il metallo perde calore"}'),
('fen-trasferimento-calore', 'fen-maillard', 'influenza',
 '{"nota":"La velocità di trasferimento di calore determina se si raggiunge la T di Maillard (140°C+) in superficie — metodi diversi (boiling, arrosto, friggere) producono risultati opposti"}'),
('fen-trasferimento-calore', 'fen-caramellizzazione', 'influenza',
 '{"nota":"La caramellizzazione richiede T≥160°C — il trasferimento di calore deve essere abbastanza rapido da raggiungere questa soglia in superficie senza bruciare il centro"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
