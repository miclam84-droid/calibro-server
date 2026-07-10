INSERT INTO nodes (id, type, name, domain, data) VALUES
('fen-sineresi', 'Fenomeno', 'Sineresi', 'cross',
 '{"tipo":"fisico-chimico",
   "target":"Perdita acqua accettabile: <2% · Difetto visibile: >5% · Accelerata a T>15°C o per agitazione meccanica",
   "strumento":"Bilancia (peso prima/dopo nel tempo) · temperatura · osservazione visiva",
   "principio":"La sineresi è la separazione spontanea di liquido (siero) da un gel o una struttura colloide. Avviene quando le catene polimeriche del gel si contraggono espellendo l acqua intrappolata. È il liquido che appare sullo yogurt, sulla panna cotta dopo 24h, sulla crema pasticcera conservata, sui fermentati. Non è sempre un difetto.",
   "settore":"f&b"}');
INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-sineresi', 'prod-yogurt', 'si_manifesta_in',
 '{"target":"Siero in superficie: normale <5% · eccessivo se >10%","causa":"La rete proteica dello yogurt si contrae leggermente espellendo siero — è normale e reversibile mescolando, ma indica concentrazione proteica insufficiente se eccessivo"}'),
('fen-sineresi', 'prod-creme-inglese', 'si_manifesta_in',
 '{"target":"Perdita liquido dopo 24h in frigo: accettabile <2% · usare amido di mais per ridurre sineresi","causa":"L amido gelatinizzato nella crema tende a retrogradare e rilasciare acqua nel tempo — l amido di mais è più stabile della farina"}'),
('fen-sineresi', 'prod-panna-montata', 'si_manifesta_in',
 '{"target":"Sineresi visibile dopo 12h se caldo (>15°C) · stabile a 4°C per 48h","causa":"La gelatina nella panna cotta rilascia acqua quando la T sale — servire freddo e consumare entro 24h"}'),
('fen-sineresi', 'fen-gelatinizzazione', 'influenza',
 '{"nota":"La sineresi è legata alla gelatinizzazione: gel più forti (più amido o gelatina) tendono a mostrare meno sineresi ma possono diventare troppo rigidi"}');
