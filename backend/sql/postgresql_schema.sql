CREATE TABLE IF NOT EXISTS tenants (
    empresa_id VARCHAR(32) PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    api_key_hash VARCHAR(128) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tenant_agent_credentials (
    id VARCHAR(36) PRIMARY KEY,
    empresa_id VARCHAR(32) NOT NULL REFERENCES tenants (empresa_id) ON DELETE CASCADE,
    device_label VARCHAR(120) NOT NULL,
    api_key_hash VARCHAR(128) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tenant_agent_credentials_empresa_id
    ON tenant_agent_credentials (empresa_id);

CREATE INDEX IF NOT EXISTS ix_tenant_agent_credentials_active
    ON tenant_agent_credentials (active);

CREATE TABLE IF NOT EXISTS tenant_pairing_codes (
    id VARCHAR(36) PRIMARY KEY,
    empresa_id VARCHAR(32) NOT NULL REFERENCES tenants (empresa_id) ON DELETE CASCADE,
    code_hash VARCHAR(128) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(120) NOT NULL DEFAULT 'system',
    used_by VARCHAR(120) NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_tenant_pairing_codes_empresa_id
    ON tenant_pairing_codes (empresa_id);

CREATE INDEX IF NOT EXISTS ix_tenant_pairing_codes_expires_at
    ON tenant_pairing_codes (expires_at);

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
    branch_code VARCHAR(50) NULL,
    terminal_code VARCHAR(50) NULL,
    tipo_venda VARCHAR(80) NULL,
    forma_pagamento VARCHAR(120) NULL,
    familia_produto VARCHAR(160) NULL,
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

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS tipo_venda VARCHAR(80);

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(120);

ALTER TABLE vendas
    ADD COLUMN IF NOT EXISTS familia_produto VARCHAR(160);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_branch
    ON vendas (empresa_id, branch_code);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_terminal
    ON vendas (empresa_id, terminal_code);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_tipo
    ON vendas (empresa_id, tipo_venda);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_pagamento
    ON vendas (empresa_id, forma_pagamento);

CREATE INDEX IF NOT EXISTS ix_vendas_empresa_familia
    ON vendas (empresa_id, familia_produto);

CREATE TABLE IF NOT EXISTS vendas_historico (
    id BIGSERIAL PRIMARY KEY,
    uuid VARCHAR(128) NOT NULL,
    empresa_id VARCHAR(32) NOT NULL,
    produto VARCHAR(255) NOT NULL,
    branch_code VARCHAR(50) NULL,
    terminal_code VARCHAR(50) NULL,
    tipo_venda VARCHAR(80) NULL,
    forma_pagamento VARCHAR(120) NULL,
    familia_produto VARCHAR(160) NULL,
    valor NUMERIC(14,2) NOT NULL,
    data DATE NOT NULL,
    data_atualizacao TIMESTAMPTZ NOT NULL,
    arquivado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vendas_hist_empresa_data
    ON vendas_historico (empresa_id, data);

CREATE INDEX IF NOT EXISTS ix_vendas_hist_arquivado_em
    ON vendas_historico (arquivado_em);

ALTER TABLE vendas_historico
    ADD COLUMN IF NOT EXISTS branch_code VARCHAR(50);

ALTER TABLE vendas_historico
    ADD COLUMN IF NOT EXISTS terminal_code VARCHAR(50);

ALTER TABLE vendas_historico
    ADD COLUMN IF NOT EXISTS tipo_venda VARCHAR(80);

ALTER TABLE vendas_historico
    ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(120);

ALTER TABLE vendas_historico
    ADD COLUMN IF NOT EXISTS familia_produto VARCHAR(160);
