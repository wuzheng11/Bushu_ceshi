# 项目目录树

```text
3组_张三_经营归因分析_电商/
├─ README.md
├─ Dockerfile
├─ requirements.txt
├─ pytest.ini
├─ .env.example
├─ backend/
│  ├─ __init__.py
│  └─ app/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ config.py
│     ├─ database.py
│     ├─ deps.py
│     ├─ models.py
│     ├─ schemas.py
│     ├─ security.py
│     ├─ seed.py
│     ├─ routers/
│     │  ├─ __init__.py
│     │  ├─ admin.py
│     │  ├─ attachment.py
│     │  ├─ auth.py
│     │  ├─ chat.py
│     │  ├─ configs.py
│     │  ├─ results.py
│     │  └─ tasks.py
│     └─ services/
│        ├─ __init__.py
│        ├─ analysis_engine.py
│        ├─ config_service.py
│        ├─ file_service.py
│        ├─ task_service.py
│        ├─ tools.py
│        └─ websocket_manager.py
├─ auth_server/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models.py
│  └─ security.py
├─ frontend/
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ index.html
│  ├─ vite.config.ts
│  ├─ tsconfig.json
│  ├─ tsconfig.app.json
│  ├─ tsconfig.node.json
│  └─ src/
│     ├─ main.tsx
│     ├─ App.tsx
│     ├─ styles.css
│     ├─ types.ts
│     ├─ vite-env.d.ts
│     ├─ lib/
│     │  └─ api.ts
│     ├─ components/
│     │  ├─ AppHeader.tsx
│     │  ├─ AttachmentPanel.tsx
│     │  ├─ ChatPanel.tsx
│     │  ├─ ConversationSidebar.tsx
│     │  ├─ ResultPanel.tsx
│     │  └─ TaskPanel.tsx
│     └─ pages/
│        ├─ AdminConfigPage.tsx
│        ├─ AdminLogsPage.tsx
│        ├─ AuthCallbackPage.tsx
│        ├─ LoginPage.tsx
│        └─ WorkbenchPage.tsx
├─ database/
│  ├─ create_mysql_databases.sql
│  ├─ schema.sql
│  └─ auth_schema.sql
├─ deploy/
│  ├─ attribution-auth-server.service
│  ├─ attribution-backend.service
│  ├─ nginx.conf
│  └─ docker/
│     ├─ .env.example
│     ├─ Caddyfile
│     ├─ entrypoint.sh
│     ├─ mysql-init.sql
│     └─ nginx.conf
├─ docker-compose.yml
├─ sample_data/
│  ├─ README.md
│  ├─ scenario_a/
│  │  ├─ category_master.csv
│  │  ├─ product_master.csv
│  │  ├─ search_impressions.csv
│  │  ├─ product_clicks.csv
│  │  └─ product_conversions.csv
│  └─ scenario_b/
│     ├─ business_users.csv
│     ├─ visit_events.csv
│     ├─ add_cart_events.csv
│     └─ order_events.csv
├─ scripts/
│  ├─ init_db.py
│  ├─ run_services.py
│  └─ smoke_live.py
├─ tests/
│  ├─ conftest.py
│  ├─ test_api.py
│  └─ test_oauth.py
└─ docs/
   ├─ ACCEPTANCE.md
   ├─ API.md
   ├─ DATABASE.md
   ├─ DEMO.md
   ├─ DEPLOY.md
   ├─ DOCKER_DEPLOY.md
   ├─ PROJECT_TREE.md
   └─ TESTING.md
```

运行时生成且不随代码提交的目录：

```text
data/
uploads/
exports/
workspace/
frontend/node_modules/
frontend/dist/
```
