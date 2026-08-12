-- ============================================================
-- ERRORI PANIFICAZIONE — batch 01: glutine, lievitazione, crosta, sale, enzimi
-- ============================================================
INSERT INTO nodes (id, type, name, domain, data) VALUES
('err-impasto-strappa', 'Errore', 'Impasto che si strappa e non si estende', 'panificazione',
  '{"causa":"maglia glutinica poco sviluppata o troppo giovane: proteine non allineate. Serve piu impasto, piu idratazione o piu riposo (autolisi). Farina debole (W basso) non regge lunghe lievitazioni"}'),
('err-pane-non-cresce', 'Errore', 'Pane che non cresce in cottura (oven spring assente)', 'panificazione',
  '{"causa":"sovra-lievitazione o glutine esausto: la maglia non trattiene piu i gas e collassa in forno invece di dare la spinta (oven spring). Ridurre i tempi o rinforzare la farina"}'),
('err-alveolatura-chiusa', 'Errore', 'Mollica compatta e alveolatura chiusa', 'panificazione',
  '{"causa":"sotto-lievitazione, poca idratazione o degassatura eccessiva: poca CO2 trattenuta o maglia troppo serrata. Allungare la lievitazione, alzare idratazione, maneggiare con delicatezza"}'),
('err-crosta-pallida-molle', 'Errore', 'Crosta pallida e molle', 'panificazione',
  '{"causa":"forno troppo basso o assenza di vapore/zuccheri: senza abbastanza calore e zuccheri residui il Maillard e la gelatinizzazione della crosta non partono. Alzare la temperatura, dare vapore in avvio"}'),
('err-impasto-appiccicoso', 'Errore', 'Impasto appiccicoso e ingestibile', 'panificazione',
  '{"causa":"eccesso di attivita enzimatica (amilasi/proteasi) o troppa idratazione per quella farina: gli enzimi degradano amido e glutine rendendo l impasto colloso. Farina piu forte, meno acqua, impasto piu fresco"}'),
('err-pane-insipido', 'Errore', 'Pane insipido e lievitazione incontrollata', 'panificazione',
  '{"causa":"sale mancante o scarso: oltre al gusto, il sale regola la fermentazione e rinforza il glutine. Senza, il lievito corre troppo e la maglia si indebolisce. Dosare 2-2,2 grammi di sale per 100 di farina"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('fen-maglia-glutinica','err-impasto-strappa','fallisce_come','{"sintomo":"si strappa, non si estende"}'),
('fen-lievitazione','err-pane-non-cresce','fallisce_come','{"sintomo":"non cresce in forno"}'),
('fen-lievitazione','err-alveolatura-chiusa','fallisce_come','{"sintomo":"mollica compatta"}'),
('fen-crosta','err-crosta-pallida-molle','fallisce_come','{"sintomo":"crosta pallida e molle"}'),
('fen-enzimi-farina','err-impasto-appiccicoso','fallisce_come','{"sintomo":"impasto colloso"}'),
('fen-sale-impasto','err-pane-insipido','fallisce_come','{"sintomo":"insipido, lievita troppo"}');
