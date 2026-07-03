-- ============================================================
-- AC1: Schema esperimento — tabella per il quaderno misure fisiche
-- Decisioni prese:
-- - Esperimento = ricetta con misure fisiche (non diario iterativo)
-- - Matter possiede la fisica, Cifra possiede i prezzi
-- - Entità separata: Matter ha la sua tabella, Cifra legge via API
-- ============================================================

CREATE TABLE IF NOT EXISTS esperimenti (
    id          SERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ DEFAULT NOW(),
    nome        TEXT NOT NULL,              -- es. "Daiquiri house v3"
    disciplina  TEXT,                       -- bar/bakery/cucina/caffetteria
    note        TEXT,                       -- note libere del professionista

    -- misure fisiche (quello che si misura al banco)
    ph          NUMERIC(4,2),              -- pH (pHmetro)
    brix        NUMERIC(5,2),              -- Brix (rifrattometro)
    abv         NUMERIC(5,2),              -- ABV % (alcolometro)
    ey_perc     NUMERIC(5,2),              -- EY% caffè (refrat. digitale)
    tds_perc    NUMERIC(5,2),              -- TDS% (refrat. digitale)
    temperatura NUMERIC(5,1),              -- °C (termometro)
    idratazione NUMERIC(5,2),             -- % baker's (bilancia)

    -- ingredienti e dosi (JSON array)
    -- formato: [{"nome":"Gin","quantita_g":60,"quantita_ml":60,"unita":"ml"}]
    ingredienti JSONB DEFAULT '[]',

    -- fenomeni coinvolti (dal grafo)
    -- formato: ["fen-acidita","fen-concentrazione"]
    fenomeni    JSONB DEFAULT '[]',

    -- costo orientativo calcolato con prezzi di mercato
    costo_mercato_eur NUMERIC(8,2),
    area_mercato      TEXT DEFAULT 'it',

    -- metadati
    user_id     TEXT,                       -- per quando ci sarà l'account
    versione    INTEGER DEFAULT 1          -- per iterazioni della stessa ricetta
);

-- indice per recuperare esperimenti per utente e disciplina
CREATE INDEX IF NOT EXISTS idx_esperimenti_user ON esperimenti(user_id, disciplina, ts DESC);

-- commento per documentazione API
COMMENT ON TABLE esperimenti IS
'Quaderno misure fisiche di Matter. Possiede la fisica della ricetta (dosi, misure, fenomeni).
NON possiede i prezzi del fornitore (quelli stanno in Cifra).
API esposta: /ricetta/{id} → Cifra legge ingredienti+dosi per calcolare food cost reale.';
