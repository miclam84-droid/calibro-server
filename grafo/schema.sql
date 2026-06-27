-- ============================================================
-- GRAFO — schema (Postgres / Railway)
-- Nodo centrale = Fenomeno. Tutto gli ruota attorno.
-- Due tabelle: nodes + edges. Niente Neo4j: regge su Postgres.
-- ============================================================

CREATE TABLE IF NOT EXISTS nodes (
  id     TEXT PRIMARY KEY,                 -- slug stabile: fen-acidita, prod-sour...
  type   TEXT NOT NULL,                    -- Fenomeno | Processo | Calcolo | Prodotto | Tecnica | Errore
  name   TEXT NOT NULL,                    -- nome leggibile
  domain TEXT,                             -- bar | cucina | bakery | trasversale
  data   JSONB DEFAULT '{}'                -- testo scheda, target, formula, ecc.
);

CREATE TABLE IF NOT EXISTS edges (
  from_id  TEXT NOT NULL REFERENCES nodes(id),
  to_id    TEXT NOT NULL REFERENCES nodes(id),
  relation TEXT NOT NULL,                  -- realizzato_da | misurato_da | si_manifesta_in | controllato_con | fallisce_come
  data     JSONB DEFAULT '{}',
  PRIMARY KEY (from_id, to_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_nodes_type   ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_domain ON nodes(domain);
CREATE INDEX IF NOT EXISTS idx_edges_from   ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to     ON edges(to_id);
