-- ============================================================
-- ORÁCULO ERA DE ACUARIO — Schema de Supabase
-- Ejecutar en el SQL Editor de Supabase
-- ============================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Tabla: users ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instagram_id        VARCHAR(255) UNIQUE,
    manychat_id         VARCHAR(255) UNIQUE,
    email               VARCHAR(255),
    first_name          VARCHAR(255),
    last_name           VARCHAR(255),
    reading_count       INTEGER DEFAULT 0,
    free_reading_used   BOOLEAN DEFAULT FALSE,
    primary_archetype   VARCHAR(50),  -- El arquetipo más frecuente del usuario
    is_premium          BOOLEAN DEFAULT FALSE,
    premium_since       TIMESTAMPTZ,
    stripe_customer_id  VARCHAR(255),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tabla: oracle_sessions ────────────────────────────────────
CREATE TABLE IF NOT EXISTS oracle_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    archetype       VARCHAR(50) NOT NULL,
    reading_type    VARCHAR(20) CHECK (reading_type IN ('free', 'premium', 'full')),
    messages        JSONB DEFAULT '[]',  -- Historial completo de la sesión
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    channel         VARCHAR(50) DEFAULT 'instagram'  -- 'instagram' | 'web'
);

-- ── Tabla: readings ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS readings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID REFERENCES oracle_sessions(id) ON DELETE CASCADE,
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    archetype               VARCHAR(50) NOT NULL,
    user_input              TEXT NOT NULL,
    oracle_response         TEXT NOT NULL,
    question_for_user       TEXT,
    archetype_confidence    FLOAT,
    classification_method   VARCHAR(50),
    reading_type            VARCHAR(20),
    tokens_used             INTEGER,
    response_time_ms        INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ── Tabla: payments ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    stripe_payment_id   VARCHAR(255) UNIQUE,
    stripe_session_id   VARCHAR(255),
    amount              INTEGER NOT NULL,  -- En centavos (2700 = $27)
    currency            VARCHAR(10) DEFAULT 'usd',
    product_type        VARCHAR(50),  -- 'lectura_profunda' | 'portal_sagrado'
    status              VARCHAR(50) DEFAULT 'pending',  -- 'pending' | 'completed' | 'failed' | 'refunded'
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- ── Índices ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_instagram_id ON users(instagram_id);
CREATE INDEX IF NOT EXISTS idx_users_manychat_id ON users(manychat_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON oracle_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_readings_user_id ON readings(user_id);
CREATE INDEX IF NOT EXISTS idx_readings_archetype ON readings(archetype);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ── Función: actualizar updated_at automáticamente ────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ── Vista: métricas básicas ───────────────────────────────────
CREATE OR REPLACE VIEW oracle_metrics AS
SELECT
    COUNT(DISTINCT u.id) AS total_users,
    COUNT(DISTINCT CASE WHEN u.is_premium THEN u.id END) AS premium_users,
    COUNT(r.id) AS total_readings,
    COUNT(DISTINCT CASE WHEN r.reading_type = 'free' THEN r.id END) AS free_readings,
    COUNT(DISTINCT CASE WHEN r.reading_type IN ('premium', 'full') THEN r.id END) AS premium_readings,
    AVG(r.archetype_confidence) AS avg_confidence,
    AVG(r.response_time_ms) AS avg_response_ms,
    COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'completed'), 0) / 100.0 AS total_revenue_usd
FROM users u
LEFT JOIN readings r ON r.user_id = u.id
LEFT JOIN payments p ON p.user_id = u.id;

-- ── Vista: arquetipos más frecuentes ─────────────────────────
CREATE OR REPLACE VIEW archetype_stats AS
SELECT
    archetype,
    COUNT(*) AS total_readings,
    AVG(archetype_confidence) AS avg_confidence,
    COUNT(DISTINCT user_id) AS unique_users
FROM readings
GROUP BY archetype
ORDER BY total_readings DESC;

-- ── RLS (Row Level Security) ──────────────────────────────────
-- Activar RLS para proteger los datos
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE oracle_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- Policy: el backend (service_role) puede hacer todo
-- Los usuarios solo pueden ver sus propios datos
CREATE POLICY "Service role full access" ON users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON oracle_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON readings
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON payments
    FOR ALL USING (auth.role() = 'service_role');
