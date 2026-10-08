# 接口说明

## 通用约定

- 后端地址：`http://localhost:8000`
- 认证中心地址：`http://localhost:8001`
- 除登录入口、OAuth 回调和健康检查外，业务接口要求浏览器 `access_token` HttpOnly Cookie。
- JSON 请求使用 `Content-Type: application/json`。
- 附件上传和附件删除使用 `multipart/form-data`。
- 业务时间统一使用 ISO 8601 格式。
- 错误响应使用 FastAPI 标准结构：`{"detail": "错误信息"}`。

## 认证接口

### `GET /auth/login`

用途：生成 OAuth2 `state`，跳转到本地认证中心。

响应：`302`，`Location` 指向认证中心 `/oauth/authorize`。

### `GET /auth/callback`

查询参数：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `code` | string | 是 | 认证中心授权码 |
| `state` | string | 是 | 防 CSRF 状态值 |

处理内容：校验状态、调用 `/oauth/token`、校验 JWT、创建或更新本地用户、设置 `access_token` Cookie。

响应：`302` 到前端 `/login/callback?login=success`。

### `GET /api/auth/me`

响应：

```json
{
  "id": 1,
  "external_user_id": "demo:analyst",
  "username": "analyst",
  "display_name": "经营分析师",
  "role": "analysis_user",
  "status": "active",
  "created_at": "2026-09-30T06:00:00"
}
```

### `POST /api/auth/logout`

响应：

```json
{"status": "ok"}
```

## 会话接口

### `POST /api/chat/create`

请求：

```json
{"title": "商品目录分析"}
```

响应：

```json
{
  "conversation_id": 1,
  "title": "商品目录分析",
  "status": "active",
  "last_message_at": null,
  "created_at": "2026-09-30T06:00:00",
  "updated_at": "2026-09-30T06:00:00"
}
```

### `POST /api/chat/delete`

请求：

```json
{"conversation_ids": [1, 2]}
```

行为：标记会话为 `deleted`，删除消息、附件记录、任务、结果、上下文摘要及三类会话文件目录。

### `POST /api/chat/update`

请求：

```json
{"conversation_id": 1, "title": "新的会话标题"}
```

### `GET /api/chat/ls`

响应为当前用户的非删除会话数组：

```json
[
  {
    "conversation_id": 1,
    "title": "商品目录分析",
    "status": "active",
    "last_message_at": "2026-09-30T06:10:00",
    "created_at": "2026-09-30T06:00:00",
    "updated_at": "2026-09-30T06:10:00"
  }
]
```

### `GET /api/chat/ls/{conversation_id}`

响应：

```json
[
  {
    "message_id": 1,
    "role": "user",
    "message_type": "text",
    "content": "请分析商品目录问题",
    "tool_name": null,
    "tool_status": null,
    "seq_no": 1,
    "attachments": [
      {
        "attachment_id": 1,
        "file_name": "catalog.csv",
        "file_type": "text/csv",
        "file_size": 1024
      }
    ],
    "created_at": "2026-09-30T06:10:00"
  }
]
```

### `POST /api/chat/send`

用途：写入用户消息并创建分析任务。同一会话存在 `queued` 或 `running` 任务时返回 `409`。

请求：

```json
{
  "conversation_id": 1,
  "content": "请分析最近30天商品目录曝光和转化问题",
  "attachment_ids": [1],
  "scenario": "auto"
}
```

响应：

```json
{
  "message_id": 2,
  "task_id": 1,
  "conversation_id": 1,
  "task_status": "queued",
  "current_step": "等待分析"
}
```

## 附件接口

### `POST /api/attachment/upload`

请求类型：`multipart/form-data`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `conversation_id` | integer | 会话 ID |
| `file` | file | 最大 20MB |

响应：

```json
{
  "attachment_id": 1,
  "conversation_id": 1,
  "message_id": null,
  "file_name": "catalog.csv",
  "file_path": "D:/.../uploads/1/1/catalog.csv",
  "file_type": "text/csv",
  "file_size": 1024,
  "parse_status": "parsed",
  "created_at": "2026-09-30T06:00:00"
}
```

### `GET /api/attachment/ls?conversation_id=1`

响应：附件对象数组，字段同上。

### `GET /api/attachment/get?attachment_id=1`

响应：附件二进制流，带 `Content-Disposition` 文件名。

### `POST /api/attachment/delete`

请求类型：`multipart/form-data`

```text
attachment_id=1
```

响应：

```json
{"status": "deleted", "attachment_id": 1}
```

## WebSocket

### `POST /api/chat/ws-token?conversation_id=1`

响应：

```json
{
  "websocket_token": "one-time-token",
  "expires_in": 120
}
```

### `WS /api/chat/ws/chat`

查询参数：

```text
websocket_token=<token>&conversation_id=1
```

连接时 token 立即消耗。连接建立后先回放该会话最近 200 条事件，再推送实时事件。

事件公共字段：

```json
{
  "event": "task_status",
  "task_id": 1,
  "conversation_id": 1,
  "timestamp": "2026-09-30T06:10:00+00:00"
}
```

事件类型：

| 事件 | 附加字段 |
| --- | --- |
| `message_start` | `message_id`, `role` |
| `message_delta` | `delta_text`, `message_id` |
| `tool_start` | `tool_name` |
| `tool_finish` | `tool_name`, `tool_result_summary`, `tool_status` |
| `task_status` | `task_status`, `current_step` |
| `result_ready` | `result_id` |
| `error` | `error_message` |
| `done` | `finished_at` |

客户端可发送文本 `ping` 接收 `{"event": "pong", "conversation_id": 1}`。

## 任务接口

### `GET /api/tasks/{task_id}`

```json
{
  "task_id": 1,
  "conversation_id": 1,
  "task_status": "running",
  "current_step": "查询经营数据",
  "started_at": "2026-09-30T06:10:00",
  "finished_at": null,
  "error_message": null
}
```

### `GET /api/tasks?conversation_id=1`

响应：会话任务数组，按 `task_id` 倒序。

### `POST /api/tasks/{task_id}/cancel`

用途：将排队中或运行中的任务标记为 `cancelled`。

### `GET /api/tasks/{task_id}/events`

响应：任务持久化事件日志，可用于 WebSocket 断开后的补偿查询。

## 结果接口

### `GET /api/results/{task_id}`

```json
{
  "result_id": 1,
  "task_id": 1,
  "problem_definition": "问题定义",
  "key_metrics": [
    {
      "metric_name": "整体点击率",
      "metric_value": 3.8,
      "metric_unit": "%",
      "metric_period": "最近30天"
    }
  ],
  "evidence_list": [
    {
      "source_type": "database",
      "source_name": "search_impressions / product_clicks",
      "evidence_text": "证据",
      "related_metric": "点击率",
      "confidence": 0.86
    }
  ],
  "conclusion_text": "归因结论",
  "missing_data_text": "待补充数据",
  "next_action_text": "1. 动作一\n2. 动作二",
  "result_markdown": "# 经营归因分析报告",
  "result_file_path": "D:/.../exports/1/1/task_1_result.md",
  "created_at": "2026-09-30T06:11:00"
}
```

### `GET /api/results/{task_id}/download`

响应：Markdown 文件。

### `POST /api/results/{task_id}/save`

用途：将当前结果再次写入 `exports/{user_id}/{conversation_id}/` 并更新文件路径。

## 管理和配置接口

### `POST /api/admin/reload`

管理员接口。重新从 `system_configs` 加载内存配置。

```json
{"status": "ok", "message": "配置已热更新，共加载 13 项"}
```

### `GET /api/admin/configs`

响应配置列表。

### `PUT /api/admin/configs/{config_key}`

```json
{"config_value": "0.04", "config_group": "analysis"}
```

### `GET /api/admin/logs`

查询参数：`task_id`、`log_level`、`limit`。

### `GET /api/admin/data-sources`

管理员查看数据源连接。

### `POST /api/admin/data-sources`

```json
{
  "name": "经营数据仓库",
  "dialect": "mysql",
  "connection_url": "mysql+pymysql://root:password@127.0.0.1:3306/business_attribution_demo?charset=utf8mb4",
  "status": "active"
}
```

### `PUT /api/admin/data-sources/{source_id}`

请求字段同创建接口。

### `POST /api/admin/data-sources/{source_id}/test`

使用保存的 SQLAlchemy URL 执行 `SELECT 1`，成功返回 `ok`，连接失败返回 `failed` 和错误信息。

### `GET /api/config/effective`

返回当前用户可用的分析阈值、功能开关和 WebSocket token 有效期。
