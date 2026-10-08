# 经营归因分析系统

这是一个可本地运行的多轮经营归因分析系统，覆盖本地 OAuth2 授权码登录、JWT 会话、会话与附件管理、WebSocket 实时分析、数据库查询、文件读写、文本检索、安全命令执行、结果导出、配置热更新和运行日志。

项目默认提供两个完整业务场景：

1. 商品目录优化：检索曝光、点击、转化与类目属性数据。
2. 客户行为分析：访问、加购、下单漏斗与用户分群数据。

## 快速启动

环境要求：

- Python 3.11+
- Node.js 20+
- npm 10+
- MySQL 8.0+

在项目根目录依次执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Get-Content .\database\create_mysql_databases.sql | mysql -u root -p
Copy-Item .env.example .env
# 编辑 .env，填写 MYSQL_USER 和 MYSQL_PASSWORD
.\.venv\Scripts\python.exe -m backend.app.seed
.\.venv\Scripts\python.exe scripts/run_services.py
```

然后新开终端启动前端：

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`。点击“进入认证中心”，可使用以下演示账号：

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `analyst` | `analyst123` | 分析用户 |
| `admin` | `admin123` | 系统管理员 |

服务端口：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- 认证中心：`http://localhost:8001`
- 后端接口文档：`http://localhost:8000/docs`

## 演示问题

场景 A：

```text
请分析最近 30 天商品目录优化问题。重点检查高曝光低点击类目、类目属性完整度与转化变化，并给出下一步动作。
```

场景 B：

```text
请分析最近 30 天客户行为漏斗，定位访问到加购、加购到下单的主要流失环节和用户分群差异。
```

系统会通过规则、SQL 查询、文件、文本检索和受限命令工具生成六部分结构化结果，并导出 Markdown 文件。

## 文档

- [接口说明](docs/API.md)
- [验收测试](docs/TESTING.md)
- [验收自检表](docs/ACCEPTANCE.md)
- [演示脚本](docs/DEMO.md)
- [数据库设计](docs/DATABASE.md)
- [项目目录树](docs/PROJECT_TREE.md)
- [云服务器部署](docs/DEPLOY.md)
- [Docker 容器化部署](docs/DOCKER_DEPLOY.md)

## 目录说明

```text
backend/       FastAPI 后端、分析引擎和工具
auth_server/   本地 OAuth2 授权服务器
frontend/      React + Vite 前端
database/      MySQL 建库与建表 DDL
deploy/        systemd 与 Nginx 部署模板
Dockerfile     前后端统一镜像
docker-compose.yml  Docker 容器编排
sample_data/   两个业务场景的 CSV 示例数据
scripts/       初始化、服务和冒烟测试脚本
tests/         后端与验收测试
uploads/       运行时附件目录
exports/       运行时导出目录
workspace/     运行时临时目录
data/          运行时日志目录
```

> `3组_张三_经营归因分析_电商` 是题目示例命名。提交前可整体重命名为实际组名、姓名和行业。
