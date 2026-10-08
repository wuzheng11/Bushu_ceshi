-- 创建经营归因分析系统使用的三个 MySQL 数据库。
-- 执行前请确认当前账号具有 CREATE DATABASE 权限。

CREATE DATABASE IF NOT EXISTS business_attribution_app
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS business_attribution_auth
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS business_attribution_demo
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 可选：为业务账号授予三个数据库的权限。
-- 请将 attribution_user 和 replace-me 替换为实际账号与密码。
-- CREATE USER IF NOT EXISTS 'attribution_user'@'%' IDENTIFIED BY 'replace-me';
-- GRANT ALL PRIVILEGES ON business_attribution_app.* TO 'attribution_user'@'%';
-- GRANT ALL PRIVILEGES ON business_attribution_auth.* TO 'attribution_user'@'%';
-- GRANT ALL PRIVILEGES ON business_attribution_demo.* TO 'attribution_user'@'%';
-- FLUSH PRIVILEGES;
