# 云服务器部署

本文以 Ubuntu 22.04/24.04、MySQL 8.0、Nginx 和 systemd 为例。示例域名为 `example.com`，部署目录为 `/opt/business-attribution`。

## 1. 服务器准备

建议配置：

- 2 核 CPU、4 GB 内存起步
- Ubuntu 22.04 LTS 或 24.04 LTS
- 安全组开放 `22`、`80`、`443`
- DNS 将 `example.com` 解析到服务器公网 IP

安装系统软件：

```bash
sudo apt update
sudo apt install -y git nginx mysql-server python3 python3-venv python3-pip curl
```

安装 Node.js 20：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
```

## 2. 创建部署用户和目录

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin attribution
sudo mkdir -p /opt/business-attribution
sudo chown -R attribution:attribution /opt/business-attribution
```

将项目上传到 `/opt/business-attribution`。可以使用 Git：

```bash
sudo -u attribution git clone <你的仓库地址> /opt/business-attribution
```

也可以在本地使用 `scp` 或 `rsync` 上传。

## 3. 创建 MySQL 数据库和账号

登录 MySQL：

```bash
sudo mysql
```

执行：

```sql
CREATE DATABASE IF NOT EXISTS business_attribution_app
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS business_attribution_auth
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS business_attribution_demo
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'attribution'@'localhost'
  IDENTIFIED BY '替换为强密码';

GRANT ALL PRIVILEGES ON business_attribution_app.* TO 'attribution'@'localhost';
GRANT ALL PRIVILEGES ON business_attribution_auth.* TO 'attribution'@'localhost';
GRANT ALL PRIVILEGES ON business_attribution_demo.* TO 'attribution'@'localhost';
FLUSH PRIVILEGES;
```

## 4. 配置环境变量

```bash
cd /opt/business-attribution
sudo -u attribution cp .env.example .env
sudo -u attribution chmod 600 .env
sudo -u attribution nano .env
```

生产环境示例：

```text
APP_SECRET_KEY=使用随机字符串
JWT_SECRET=使用另一个随机字符串
BACKEND_BASE_URL=https://example.com
FRONTEND_URL=https://example.com
AUTH_SERVER_URL=https://example.com
AUTH_REDIRECT_URI=https://example.com/auth/callback
AUTH_CLIENT_ID=business-attribution-web
AUTH_CLIENT_SECRET=替换为强随机字符串
ACCESS_TOKEN_EXPIRE_MINUTES=480
COOKIE_SECURE=true

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=attribution
MYSQL_PASSWORD=替换为MySQL强密码
MYSQL_CHARSET=utf8mb4

APP_DB_NAME=business_attribution_app
AUTH_DB_NAME=business_attribution_auth
DEMO_DB_NAME=business_attribution_demo
```

生成随机密钥：

```bash
openssl rand -hex 32
```

## 5. 初始化 Python 环境

```bash
cd /opt/business-attribution
sudo -u attribution rm -rf .venv frontend/node_modules
sudo -u attribution python3 -m venv .venv
sudo -u attribution .venv/bin/python -m pip install --upgrade pip
sudo -u attribution .venv/bin/python -m pip install -r requirements.txt
sudo -u attribution .venv/bin/python -m backend.app.seed
```

`backend.app.seed` 会创建应用库和演示业务库的表，并导入 `sample_data` 中的 CSV。认证库表会在认证服务首次启动时自动创建。

## 6. 构建前端

```bash
cd /opt/business-attribution/frontend
sudo -u attribution npm ci
sudo -u attribution npm run build
```

构建产物位于：

```text
/opt/business-attribution/frontend/dist
```

## 7. 配置 systemd 服务

项目提供了两个服务模板：

- `deploy/attribution-backend.service`
- `deploy/attribution-auth-server.service`

复制并启用：

```bash
sudo cp /opt/business-attribution/deploy/attribution-backend.service /etc/systemd/system/
sudo cp /opt/business-attribution/deploy/attribution-auth-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now attribution-backend attribution-auth-server
sudo systemctl status attribution-backend
sudo systemctl status attribution-auth-server
```

查看日志：

```bash
sudo journalctl -u attribution-backend -f
sudo journalctl -u attribution-auth-server -f
```

后端和认证服务只监听 `127.0.0.1:8000` 和 `127.0.0.1:8001`，不直接暴露到公网。

## 8. 配置 Nginx

修改 `deploy/nginx.conf` 中的 `server_name`：

```nginx
server_name example.com;
```

安装配置：

```bash
sudo cp /opt/business-attribution/deploy/nginx.conf /etc/nginx/sites-available/business-attribution
sudo ln -s /etc/nginx/sites-available/business-attribution /etc/nginx/sites-enabled/business-attribution
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

此时路由关系为：

- `/`：React 前端静态文件
- `/api/`：后端 API 和 WebSocket
- `/auth/`：后端登录和 OAuth2 回调
- `/oauth/`：认证中心
- `/health`：后端健康检查

## 9. 配置 HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d example.com
```

Certbot 会自动修改 Nginx 配置并设置证书续期。验证：

```bash
sudo certbot renew --dry-run
```

HTTPS 生效后，确认 `.env` 中已设置 `COOKIE_SECURE=true`，然后重启后端：

```bash
sudo systemctl restart attribution-backend
```

## 10. 验收

```bash
curl -I https://example.com
curl https://example.com/health
curl -I https://example.com/docs
```

浏览器访问 `https://example.com`，使用 `analyst / analyst123` 或 `admin / admin123` 登录。

检查服务状态：

```bash
sudo systemctl status attribution-backend attribution-auth-server nginx mysql
```

## 11. 后续更新

```bash
cd /opt/business-attribution
sudo -u attribution git pull
sudo -u attribution .venv/bin/python -m pip install -r requirements.txt
sudo -u attribution .venv/bin/python -m backend.app.seed
cd frontend
sudo -u attribution npm ci
sudo -u attribution npm run build
sudo systemctl restart attribution-backend attribution-auth-server
sudo systemctl reload nginx
```
