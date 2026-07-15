INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-attivita-enzimatica', 'Fenomeno', 'Attività enzimatica', 'cross',
 '{"tipo":"biologico",
   "target":"Beta-amilasi: attiva 62-65°C (birra secca) · Alfa-amilasi: attiva 68-72°C (birra corposa) · Proteasi: 45-55°C · Inattivazione enzimi: >75-80°C",
   "strumento":"Termometro (la T è lo strumento di controllo)",
   "principio":"Gli enzimi sono proteine catalitiche con una finestra di temperatura precisa: fuori da quella finestra rallentano o si inattivano irreversibilmente. Nel mash della birra, la scelta di temperatura tra 62 e 72°C non è arbitraria — determina il rapporto tra zuccheri fermentabili e destrine non fermentabili, cioè la secchezza o il corpo finale della birra. Nel lievito madre, le proteasi rompono i legami del glutine durante la maturazione rendendolo più estensibile. Nel caffè verde, gli enzimi responsabili degli aromi fruttati vengono inattivati dalla torrefazione — la differenza tra una tostatura chiara e una scura è anche una differenza enzimatica. Temperatura e tempo sono le due leve: stessa temperatura ma tempi diversi producono risultati diversi.",
   "settore":"f&b"}')
ON CONFLICT (id) DO NOTHING;
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-attivita-enzimatica', 'prod-birra-lager', 'si_manifesta_in',
 '{"target":"Mash a 62-65°C: birra secca (beta-amilasi) · 68-72°C: birra corposa (alfa-amilasi)","causa":"La temperatura del mash seleziona quale enzima è più attivo: beta-amilasi produce zuccheri fermentabili (secco), alfa-amilasi produce destrine non fermentabili (corpo)"}'),
('fen-attivita-enzimatica', 'prod-pane-madre', 'si_manifesta_in',
 '{"target":"Proteasi attive nel lievito madre: 45-50°C · degradano glutine se T troppo alta","causa":"I lattobacilli nel lievito madre producono proteasi che rendono il glutine più estensibile — ma a T troppo alte degradano la rete proteica indebolendo l impasto"}'),
('fen-attivita-enzimatica', 'prod-espresso', 'si_manifesta_in',
 '{"target":"Enzimi del caffè verde inattivati a 60-80°C durante torrefazione · lipasi attive nel caffè macinato","causa":"La lipasi nel caffè macinato degrada i grassi producendo acidi grassi liberi — causa di rancidità se il macinato non è fresco"}'),
('fen-attivita-enzimatica', 'prod-carne-stagionata', 'si_manifesta_in',
 '{"target":"Frollatura a 2-4°C: 7-28 giorni · enzimi muscolari (catepsine) rompono le proteine migliorando tenerezza","causa":"Le catepsine (enzimi proteolitici) nella carne continuano ad agire dopo la macellazione a T controllata — la frollatura è attività enzimatica controllata"}'),
('fen-attivita-enzimatica', 'fen-fermentazione', 'influenza',
 '{"nota":"La fermentazione è guidata dagli enzimi dei microrganismi — i lieviti producono zimasi (enzima) che converte gli zuccheri in alcol e CO2"}')
ON CONFLICT (from_id, to_id, relation) DO NOTHING;
