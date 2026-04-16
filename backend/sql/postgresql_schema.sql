CREATE TABLE IF NOT EXISTS tenants (
    empresa_id VARCHAR(32) PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    api_key_hash VARCHAR(128) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS server_settings (
    key VARCHAR(64) PRIMARY KEY,
    value VARCHAR(255) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendas (
    id BIGSERIAL PRIMARY KEY,
    uuid VARCHAR(128) NOT NULL,
    empresa_id VARCHAR(32) NOT NULL REFERENCES tenants (empresa_id) ON DELETE RESTRICT,
    produto VARCHAR(255) NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    data DATE NOT NULL,
    data_atualizacao TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_vendas_empresa_uuid UNIQUE (empresa_id, uuid)
);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_data
    ON vendas (empresa_id, data);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_data_atualizacao
    ON vendas (empresa_id, data_atualizacao);

CREATE TABLE IF NOT EXISTS vendas_historico (
    id BIGSERIAL PRIMARY KEY,
    uuid VARCHAR(128) NOT NULL,
    empresa_id VARCHAR(32) NOT NULL,
    produto VARCHAR(255) NOT NULL,
    valor NUMERIC(14,2) NOT NULL,
    data DATE NOT NULL,
    data_atualizacao TIMESTAMPTZ NOT NULL,
    arquivado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vendas_hist_empresa_data
    ON vendas_historico (empresa_id, data);

CREATE INDEX IF NOT EXISTS ix_vendas_hist_arquivado_em
    ON vendas_historico (arquivado_em);
