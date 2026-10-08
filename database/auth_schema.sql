-- 本地 OAuth2 认证库 MySQL DDL
-- 适用版本：MySQL 8.0+，存储引擎：InnoDB，字符集：utf8mb4。

CREATE TABLE IF NOT EXISTS auth_users (
    id               INT NOT NULL AUTO_INCREMENT,
    external_user_id VARCHAR(128) NOT NULL,
    username         VARCHAR(128) NOT NULL,
    password_hash    VARCHAR(255) NOT NULL,
    display_name     VARCHAR(128) NOT NULL,
    role             VARCHAR(32) NOT NULL DEFAULT 'analysis_user',
    status           VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_auth_users_external_user_id (external_user_id),
    UNIQUE KEY uq_auth_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS oauth_codes (
    id           INT NOT NULL AUTO_INCREMENT,
    code         VARCHAR(255) NOT NULL,
    client_id    VARCHAR(128) NOT NULL,
    user_id      INT NOT NULL,
    redirect_uri TEXT NOT NULL,
    expires_at   DATETIME NOT NULL,
    consumed_at  DATETIME NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_oauth_codes_code (code),
    KEY idx_oauth_codes_lookup (code, expires_at),
    CONSTRAINT fk_oauth_codes_user
        FOREIGN KEY (user_id) REFERENCES auth_users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
