# 验收自检表

## 交付物

| 项目 | 状态 | 文件或页面 |
| --- | --- | --- |
| 可运行后端 | 通过 | `backend/app/main.py` |
| 本地 OAuth2 认证服务 | 通过 | `auth_server/main.py` |
| React + Vite 前端 | 通过 | `frontend/src` |
| MySQL 建库脚本 | 通过 | `database/create_mysql_databases.sql` |
| MySQL DDL | 通过 | `database/schema.sql` |
| 认证库 DDL | 通过 | `database/auth_schema.sql` |
| 数据库初始化脚本 | 通过 | `backend/app/seed.py`, `scripts/init_db.py` |
| 两组示例数据 | 通过 | `sample_data/scenario_a`, `sample_data/scenario_b` |
| API 文档 | 通过 | `docs/API.md` |
| 测试说明 | 通过 | `docs/TESTING.md` |
| 演示脚本 | 通过 | `docs/DEMO.md` |

## 功能验收

| 验收标准 | 状态 | 实现与验证 |
| --- | --- | --- |
| 授权登录进入工作台 | 通过 | 授权码流程、state 校验、JWT Cookie、回调页 |
| 创建会话并查看历史 | 通过 | `/api/chat/create`, `/api/chat/ls/{id}` |
| 上传附件 | 通过 | `/api/attachment/upload`，字段完整 |
| 附件删除和下载 | 通过 | `/api/attachment/delete`, `/api/attachment/get` |
| 发送消息并生成任务 | 通过 | `/api/chat/send` |
| WebSocket 实时中间消息 | 通过 | `message_start`, `message_delta` |
| 工具执行过程 | 通过 | `tool_start`, `tool_finish` |
| 最终结果实时通知 | 通过 | `result_ready`, `task_status`, `done` |
| 切换旧会话继续追问 | 通过 | 会话列表和历史消息恢复 |
| 六部分结构化结果 | 通过 | 定义、指标、证据、结论、缺失数据、行动建议 |
| 结果复制、保存、导出 | 通过 | 前端按钮和两个后端结果接口 |
| 配置热更新 | 通过 | `/api/admin/reload` 和配置缓存重载 |
| 运行日志 | 通过 | `task_logs`、管理员日志查询页 |
| 管理员维护数据源 | 通过 | 数据源 CRUD、数据库连接测试 |
| 商品目录完整链路 | 通过 | 自动化测试和进程级冒烟测试 |
| 客户行为完整链路 | 通过 | 自动化测试 |
| 会话删除清理依赖和文件 | 通过 | 级联删除、三类目录清理 |
| 单会话单运行任务 | 通过 | 发送接口返回 `409` 保护 |

## 自动验收结果

```text
Python 编译：通过
pytest：7 passed
前端 TypeScript + Vite 构建：通过
真实 OAuth2 授权码登录：通过
真实 WebSocket 事件回放：通过
商品目录进程级分析：通过，5 个指标、5 条证据
```

## 运行残留风险

- 演示默认关闭 `secure` Cookie，仅用于本地 HTTP；生产环境必须开启 HTTPS 和 Secure Cookie。
- MySQL 适合当前本地演示和一般部署场景；高并发生产环境建议配合连接池和独立后台任务 Worker。
- 真实 LLM 接口目前为可替换占位，默认规则引擎不依赖网络。
- 自动化测试使用临时 SQLite 隔离测试数据，正式运行默认连接 MySQL。
