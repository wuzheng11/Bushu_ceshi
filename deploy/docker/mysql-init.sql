CREATE DATABASE IF NOT EXISTS business_attribution_auth
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS business_attribution_demo
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON business_attribution_auth.* TO 'attribution'@'%';
GRANT ALL PRIVILEGES ON business_attribution_demo.* TO 'attribution'@'%';
FLUSH PRIVILEGES;
