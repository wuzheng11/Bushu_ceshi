# 数据库设计

## 数据库划分

系统默认使用 MySQL 8.0+，通过 SQLAlchemy 和 PyMySQL 访问三个逻辑数据库：

| 数据库 | 默认库名 | 用途 |
| --- | --- | --- |
| 应用库 | `business_attribution_app` | 用户、会话、消息、附件、任务、结果、配置和日志 |
| 认证库 | `business_attribution_auth` | 认证中心用户和授权码 |
| 演示业务库 | `business_attribution_demo` | 商品目录和客户行为分析数据 |

完整 DDL：

- 建库脚本：[database/create_mysql_databases.sql](../database/create_mysql_databases.sql)
- 应用库：[database/schema.sql](../database/schema.sql)
- 认证库：[database/auth_schema.sql](../database/auth_schema.sql)
- 演示业务表：由 [backend/app/seed.py](../backend/app/seed.py) 创建

## 连接配置

项目会读取根目录 `.env`，也支持直接设置系统环境变量。常用配置：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=replace-me
MYSQL_CHARSET=utf8mb4
APP_DB_NAME=business_attribution_app
AUTH_DB_NAME=business_attribution_auth
DEMO_DB_NAME=business_attribution_demo
```

也可以通过 `APP_DATABASE_URL`、`AUTH_DATABASE_URL`、`DEMO_DATABASE_URL` 直接覆盖完整连接地址。

## 应用库关系

```text
users
  1 -> N conversations
  1 -> N analysis_tasks
  1 -> N websocket_tokens

conversations
  1 -> N messages
  1 -> N attachments
  1 -> N analysis_tasks
  1 -> N analysis_results
  1 -> N context_summaries

messages
  1 -> N attachments

analysis_tasks
  1 -> 1 analysis_results
  1 -> N task_logs
```

## 状态枚举

会话状态：

- `active`
- `archived`
- `deleted`

任务状态：

- `queued`
- `running`
- `success`
- `failed`
- `cancelled`

附件解析状态：

- `pending`
- `parsed`
- `stored`
- `failed`

用户角色：

- `analysis_user`
- `admin`

## 删除规则

删除会话时：

1. 删除该会话的任务日志。
2. 删除分析结果。
3. 删除上下文摘要。
4. 删除附件记录和物理附件。
5. 删除消息。
6. 删除分析任务。
7. 将会话状态标记为 `deleted`。
8. 删除：
   - `uploads/{user_id}/{conversation_id}/`
   - `exports/{user_id}/{conversation_id}/`
   - `workspace/{user_id}/{conversation_id}/`

## 数据类型

- 主键使用 `INT AUTO_INCREMENT`。
- 长文本使用 `LONGTEXT`，普通可变字符串使用 `VARCHAR`。
- 时间字段使用 `DATETIME`，创建和更新时间由 MySQL 默认值维护。
- 所有业务表使用 InnoDB、`utf8mb4_unicode_ci`，外键使用显式约束和级联删除。

自动化测试不会写入正式 MySQL 库，而是通过环境变量注入临时 SQLite URL，以便测试环境独立运行。

## 演示业务表

商品目录场景：

- `category_master`
- `product_master`
- `search_impressions`
- `product_clicks`
- `product_conversions`

客户行为场景：

- `business_users`
- `visit_events`
- `add_cart_events`
- `order_events`
