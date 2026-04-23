CREATE TABLE IF NOT EXISTS vendas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    uuid CHAR(36) NOT NULL,
    empresa_id VARCHAR(32) NOT NULL,
    produto VARCHAR(255) NOT NULL,
    valor DECIMAL(14,2) NOT NULL,
    data DATE NOT NULL,
    data_atualizacao DATETIME NOT NULL,
    UNIQUE KEY uq_vendas_empresa_uuid (empresa_id, uuid),
    KEY ix_vendas_empresa_data_atualizacao (empresa_id, data_atualizacao)
);

