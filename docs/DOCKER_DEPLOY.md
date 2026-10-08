# Docker 容器化部署

本文使用 Docker Compose 将 MySQL、FastAPI 后端、OAuth2 认证服务、Nginx 前端和 Caddy HTTPS 网关部署到同一台云服务器。

项目只使用根目录下的一个 `Dockerfile`。该镜像先构建 React 前端，再安装 Python 后端和 Nginx；运行时通过 `APP_ROLE=backend|auth|web` 启动不同进程。

## 1. 服务器要求

- Ubuntu 22.04/24.04
- 2 核 CPU、4 GB 内存起步
- 安全组开放 `22`、`80`、`443`
- 域名 A 记录解析到服务器公网 IP

示例域名：`example.com`

## 2. 安装 Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
```

重新登录终端后执行：

```bash
docker --version
docker compose version
```

## 3. 获取项目

```bash
cd /opt
sudo mkdir -p business-attribution
sudo chown "$USER":"$USER" business-attribution
git clone <你的仓库地址> business-attribution
cd business-attribution
```

## 4. 创建生产环境变量

```bash
cp deploy/docker/.env.example .env
chmod 600 .env
nano .env
```

必须修改：

```text
DOMAIN=example.com
APP_SECRET_KEY=随机密钥
JWT_SECRET=另一个随机密钥
AUTH_CLIENT_SECRET=随机客户端密钥
MYSQL_ROOT_PASSWORD=MySQL root 强密码
MYSQL_PASSWORD=业务账号强密码
```

生成随机密钥：

```bash
openssl rand -hex 32
```

域名相关的地址保持如下形式：

```text
BACKEND_BASE_URL=https://example.com
FRONTEND_URL=https://example.com
AUTH_SERVER_URL=https://example.com
AUTH_PUBLIC_URL=https://example.com
AUTH_REDIRECT_URI=https://example.com/auth/callback
COOKIE_SECURE=true
```

Compose 会把后端容器内的 `AUTH_SERVER_URL` 覆盖为 `http://auth-server:8001`，避免容器通过公网域名回环访问认证服务；浏览器使用的 `AUTH_PUBLIC_URL` 仍为 `https://example.com`。

## 5. 检查 Compose 配置

```bash
docker compose config
```

确认没有变量缺失或 YAML 错误。

## 6. 构建并启动

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f mysql
docker compose logs -f backend
docker compose logs -f auth-server
docker compose logs -f web
docker compose logs -f caddy
```

Caddy 会自动申请并续期 HTTPS 证书。首次启动时，域名必须已经正确解析到服务器。

## 7. 验收

```bash
curl -I https://example.com
curl https://example.com/health
curl -I https://example.com/docs
```

浏览器访问 `https://example.com`，使用以下演示账号登录：

```text
analyst / analyst123
admin / admin123
```

## 8. 容器说明

| 服务 | 作用 | 对外端口 |
| --- | --- | --- |
| `caddy` | HTTPS、自动证书、反向代理 | `80`、`443` |
| `web` | React 静态文件、Nginx 内部路由 | 不直接暴露 |
| `backend` | FastAPI API、WebSocket、分析任务 | 不直接暴露 |
| `auth-server` | OAuth2 授权和令牌服务 | 不直接暴露 |
| `mysql` | MySQL 8.0 数据库 | 不直接暴露 |

数据分别保存在 Docker 命名卷中：

```text
mysql_data
app_data
uploads_data
exports_data
workspace_data
caddy_data
caddy_config
```

## 9. 常用运维命令

停止服务：

```bash
docker compose down
```

`docker compose down` 默认保留数据卷。不要执行 `docker compose down -v`，除非确定要删除 MySQL、上传附件和导出结果的全部数据。

重启：

```bash
docker compose restart
```

重新构建并滚动更新：

```bash
git pull
docker compose up -d --build
```

重新导入演示数据：

```bash
docker compose exec backend python -m backend.app.seed
```

进入 MySQL：

```bash
docker compose exec mysql mysql -uattribution -p
```

## 10. 数据备份

备份 MySQL：

```bash
docker compose exec -T mysql \
  sh -c 'mysqldump -uattribution -p"$MYSQL_PASSWORD" \
  --databases business_attribution_app business_attribution_auth business_attribution_demo' \
  > business-attribution-$(date +%F).sql
```

备份文件目录：

```bash
docker run --rm \
  -v business-attribution_uploads_data:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/uploads-$(date +%F).tar.gz -C /data .
```

实际卷名前缀可能因 Compose 项目名不同而变化，可通过 `docker volume ls` 查看。

## 11. 更新部署

```bash
cd /opt/business-attribution
git pull
docker compose up -d --build
docker compose ps
```

MySQL 初始化脚本只会在数据卷第一次创建时执行。演示业务数据也会进行幂等检查，只在数据表为空时导入，正常重启不会重复覆盖。修改数据库结构时，需要编写迁移脚本，不能依赖容器重新启动自动修改已有表。
