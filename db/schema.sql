-- Med Assist user data schema (PostgreSQL 16+).
-- Apply once on a fresh Postgres database:
--   psql "$DATABASE_URL" -f db/schema.sql

CREATE TABLE IF NOT EXISTS health_profiles (
    user_id              TEXT PRIMARY KEY,
    name                 TEXT,
    age                  INTEGER CHECK (age >= 0 AND age <= 120),
    gender               TEXT CHECK (gender IN ('male', 'female', 'other')),
    is_pregnant          BOOLEAN NOT NULL DEFAULT FALSE,
    pregnancy_due_date   DATE,
    allergies            JSONB NOT NULL DEFAULT '[]'::jsonb,
    conditions           JSONB NOT NULL DEFAULT '[]'::jsonb,
    medications          JSONB NOT NULL DEFAULT '[]'::jsonb,
    onboarded            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cabinet_items (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              TEXT NOT NULL,
    name                 TEXT NOT NULL,
    generic_name         TEXT,
    dosage               TEXT,
    item_type            TEXT,
    quantity             INTEGER NOT NULL DEFAULT 1,
    expiration_date      DATE NOT NULL,
    added_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cabinet_items_user_id ON cabinet_items(user_id);
CREATE INDEX IF NOT EXISTS idx_cabinet_items_expiration ON cabinet_items(user_id, expiration_date);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              TEXT NOT NULL,
    title                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id           UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role                 TEXT NOT NULL CHECK (role IN ('user','assistant')),
    text                 TEXT NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);
