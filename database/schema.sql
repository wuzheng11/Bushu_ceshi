-- 经营归因分析系统 MySQL DDL
-- 适用版本：MySQL 8.0+，存储引擎：InnoDB，字符集：utf8mb4。

CREATE TABLE IF NOT EXISTS users (
    id               INT NOT NULL AUTO_INCREMENT,
    external_user_id VARCHAR(128) NOT NULL,
    username         VARCHAR(128) NOT NULL,
    display_name     VARCHAR(128) NOT NULL,
    role             VARCHAR(32) NOT NULL DEFAULT 'analysis_user',
    status           VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_external_user_id (external_user_id),
    UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS conversations (
    id              INT NOT NULL AUTO_INCREMENT,
    user_id         INT NOT NULL,
    title           VARCHAR(255) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    last_message_at DATETIME NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_conversations_user_status (user_id, status, updated_at),
    CONSTRAINT fk_conversations_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS messages (
    id              INT NOT NULL AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    role            VARCHAR(32) NOT NULL,
    message_type    VARCHAR(32) NOT NULL DEFAULT 'text',
    content         LONGTEXT NOT NULL,
    tool_name       VARCHAR(128) NULL,
    tool_status     VARCHAR(32) NULL,
    seq_no          INT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_message_sequence (conversation_id, seq_no),
    KEY idx_messages_conversation_seq (conversation_id, seq_no),
    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attachments (
    id              INT NOT NULL AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    message_id      INT NULL,
    file_name       VARCHAR(255) NOT NULL,
    file_path       TEXT NOT NULL,
    file_type       VARCHAR(128) NOT NULL,
    file_size       BIGINT NOT NULL DEFAULT 0,
    parse_status    VARCHAR(32) NOT NULL DEFAULT 'pending',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_attachments_conversation (conversation_id, created_at),
    CONSTRAINT fk_attachments_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_attachments_message
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_tasks (
    id              INT NOT NULL AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    user_id         INT NOT NULL,
    input_text      LONGTEXT NOT NULL,
    task_status     VARCHAR(32) NOT NULL DEFAULT 'queued',
    current_step    VARCHAR(128) NULL,
    started_at      DATETIME NULL,
    finished_at     DATETIME NULL,
    error_message   LONGTEXT NULL,
    PRIMARY KEY (id),
    KEY idx_tasks_conversation_status (conversation_id, task_status),
    CONSTRAINT fk_tasks_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_tasks_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS analysis_results (
    id                 INT NOT NULL AUTO_INCREMENT,
    task_id            INT NOT NULL,
    conversation_id    INT NOT NULL,
    problem_definition LONGTEXT NOT NULL,
    key_metrics_json   LONGTEXT NOT NULL,
    evidence_list_json LONGTEXT NOT NULL,
    conclusion_text    LONGTEXT NOT NULL,
    missing_data_text  LONGTEXT NOT NULL,
    next_action_text   LONGTEXT NOT NULL,
    result_markdown    LONGTEXT NOT NULL,
    result_file_path   TEXT NULL,
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_analysis_results_task (task_id),
    KEY idx_results_conversation (conversation_id, created_at),
    CONSTRAINT fk_results_task
        FOREIGN KEY (task_id) REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_results_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS context_summaries (
    id              INT NOT NULL AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    start_seq_no    INT NOT NULL,
    end_seq_no      INT NOT NULL,
    summary_text    LONGTEXT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_summaries_conversation (conversation_id, created_at),
    CONSTRAINT fk_summaries_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS websocket_tokens (
    id              INT NOT NULL AUTO_INCREMENT,
    user_id         INT NOT NULL,
    conversation_id INT NOT NULL,
    token           VARCHAR(255) NOT NULL,
    expires_at      DATETIME NOT NULL,
    consumed_at     DATETIME NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_websocket_tokens_token (token),
    KEY idx_ws_tokens_lookup (token, expires_at),
    CONSTRAINT fk_ws_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_ws_tokens_conversation
        FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS system_configs (
    id           INT NOT NULL AUTO_INCREMENT,
    config_key   VARCHAR(128) NOT NULL,
    config_value LONGTEXT NOT NULL,
    config_group VARCHAR(64) NOT NULL DEFAULT 'general',
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_system_configs_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS task_logs (
    id          INT NOT NULL AUTO_INCREMENT,
    task_id     INT NOT NULL,
    log_level   VARCHAR(16) NOT NULL DEFAULT 'INFO',
    log_type    VARCHAR(64) NOT NULL,
    log_content LONGTEXT NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_task_logs_task (task_id, created_at),
    CONSTRAINT fk_task_logs_task
        FOREIGN KEY (task_id) REFERENCES analysis_tasks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 以下表用于管理员维护数据源连接，是业务功能表之外的扩展表。
CREATE TABLE IF NOT EXISTS data_source_connections (
    id             INT NOT NULL AUTO_INCREMENT,
    name           VARCHAR(128) NOT NULL,
    dialect        VARCHAR(32) NOT NULL DEFAULT 'mysql',
    connection_url TEXT NOT NULL,
    status         VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_data_source_connections_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
