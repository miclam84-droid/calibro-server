-- ============================================================
-- PRINCIPIO — D-VALUE / Z-VALUE
-- Il kT della sicurezza alimentare.
-- Un solo principio che attraversa pastorizzazione,
-- sterilizzazione, abbattimento e zona di pericolo.
-- Spiega perché 60°C×30min = 71°C×0sec (stessa riduzione).
-- ============================================================

INSERT INTO nodes (id, type, name, domain, data) VALUES
('principio-dvalue', 'principio', 'D-value / z-value — cinetica di inattivazione batterica', 'sicurezza',
 '{"tipo":"fisico-chimico","scheda":"Il D-value (decimal reduction time) è il tempo necessario a una data temperatura per ridurre la carica batterica del 90% (1 ciclo logaritmico). Il z-value è la variazione di temperatura necessaria per cambiare il D-value di un fattore 10. Insieme definiscono la cinetica di morte batterica: non è un interruttore on/off, è una curva esponenziale. Come kT governa la cinetica chimica, D-value governa la cinetica microbiologica. La pastorizzazione non sterilizza — riduce la carica a livelli sicuri (riduzione 5–7 log) in tempi e temperature calcolabili.","formula":"D(T) = D_ref × 10^((T_ref - T) / z) — log N(t) = log N0 - t/D(T)"}');

INSERT INTO edges (from_id, to_id, relation, data) VALUES
('principio-dvalue', 'fen-zona-pericolo', 'spiega', 1.0),
('principio-dvalue', 'fen-shelf-life', 'spiega', 0.9),
('principio-dvalue', 'fen-calore', 'unifica', 0.9),
('principio-dvalue', 'fen-fermentazione', 'unifica', '{}');
