INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-fermentazione-lattica', 'Fenomeno', 'Fermentazione lattica', 'cross',
 '{"tipo":"biologico",
   "target":"pH sicuro fermentati: <4,6 · pH madre matura: 3,7-3,9 · Acido lattico prodotto: 0,5-2,0%",
   "strumento":"pH-metro · acidità titolabile",
   "principio":"I batteri lattici (Lactobacillus, Leuconostoc, Pediococcus) convertono gli zuccheri in acido lattico in assenza di ossigeno. L''acidità prodotta abbassa il pH a livelli che inibiscono la crescita dei patogeni, rendendo il prodotto microbiologicamente stabile senza pastorizzazione né conservanti. È il meccanismo alla base di kimchi, crauti, yogurt, kefir, miso, lievito madre e salumi fermentati. La fermentazione omolattica produce solo acido lattico (sapore pulito, acido); quella eterolattica produce anche CO₂ e acido acetico (sapore più complesso). Nel lievito madre, il rapporto tra acido lattico e acetico dipende da temperatura e idratazione — a temperature più alte e idratazioni maggiori prevale il lattico.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-fermentazione-lattica', 'prod-fermentato-lacto', 'si_manifesta_in',
 '{"target":"pH <4,6 per sicurezza · 3,2-3,8 pH finale kimchi/crauti","causa":"I lattobacilli producono acido lattico finché il pH non è troppo basso per la loro stessa sopravvivenza — l acidità diventa il proprio conservante"}'),
('fen-fermentazione-lattica', 'prod-pane-madre', 'si_manifesta_in',
 '{"target":"pH madre matura: 3,7-3,9 · acido lattico + acetico in equilibrio","causa":"Il lievito madre è una co-fermentazione: lieviti producono CO2 (lievitazione), lattobacilli producono acido lattico e acetico (sapore e conservazione)"}'),
('fen-fermentazione-lattica', 'prod-birra-sour-disc', 'si_manifesta_in',
 '{"target":"pH birra sour: 3,2-3,8 · inoculo Lactobacillus a 40-50°C","causa":"Le birre acide usano la fermentazione lattica intenzionalmente: i lattobacilli producono l acidità caratteristica prima o durante la fermentazione alcolica"}'),
('fen-fermentazione-lattica', 'fen-acidita', 'influenza',
 '{"nota":"La fermentazione lattica abbassa il pH producendo acido lattico — è il meccanismo biologico che governa l acidità nei fermentati, distinto dall aggiunta diretta di acido"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
