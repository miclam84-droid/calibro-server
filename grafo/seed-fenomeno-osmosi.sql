-- OSMOSI
-- Cross-disciplina: salamoie, confetture, stress osmotico lieviti
-- Strumento: bilancia · rifrattometro

-- Nodo già esistente nel seed ponte — solo archi aggiuntivi

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-osmosi', 'prod-fermentato-lacto', 'si_manifesta_in',
 '{"target":"Sale 2-3% su peso totale (verdure + acqua)","causa":"La pressione osmotica del sale seleziona i microorganismi: i patogeni si disidratano, i lattobacilli resistono e producono acido lattico"}'),
('fen-osmosi', 'prod-confettura', 'si_manifesta_in',
 '{"target":"≥65° Brix (zucchero)","causa":"Ad alta concentrazione di zucchero l acqua libera è così bassa che i microorganismi non possono crescere — conservazione per osmosi, non per acidità"}'),
('fen-osmosi', 'prod-panettone', 'si_manifesta_in',
 '{"target":"Zucchero 22-28% sul totale — stress osmotico alto","causa":"Lo zucchero in alta concentrazione disidrata le cellule dei lieviti: serve lievito madre stiff (pH 4,1, tripla in 3h) per resistere"}'),
('fen-osmosi', 'fen-fermentazione', 'influenza',
 '{"nota":"La pressione osmotica governa quali microorganismi sopravvivono durante la fermentazione — seleziona i lattobacilli nei fermentati e stessa logica nei grandi lievitati"}') ON CONFLICT (from_id, to_id, relation) DO NOTHING;
