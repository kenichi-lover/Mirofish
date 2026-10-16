# docs/DEPLOYMENT.md - MiroFish Web 生产环境部署指南

本文档介绍如何在单台 **Debian 13** 服务器上，使用 `systemd`、`Nginx` 和 `Let's Encrypt SSL` 将 MiroFish Web 部署为高可用生产服务。

---

## 一、 服务器环境准备

### 1. 更新系统并安装基础组件

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql postgresql-contrib redis-server nginx git curl ufw

```

### 2. 配置 PostgreSQL 数据库

登录 PostgreSQL 并创建数据库和用户：

```bash
sudo -u postgres psql

```

在 psql 命令行中执行：

```sql
CREATE DATABASE mirofish;
CREATE USER mirofish WITH PASSWORD 'your_secure_password';
ALTER ROLE mirofish SET client_encoding TO 'utf8';
ALTER ROLE mirofish SET default_transaction_isolation TO 'read committed';
ALTER ROLE mirofish SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE mirofish TO mirofish;
\q

```

### 3. 配置系统用户与目录

为了安全起见，建议创建一个专用的系统用户运行应用：

```bash
sudo useradd -m -d /opt/mirofish-web -s /bin/bash mirofish
sudo mkdir -p /var/log/mirofish-web /var/lib/mirofish-web/uploads
sudo chown -R mirofish:mirofish /opt/mirofish-web /var/log/mirofish-web /var/lib/mirofish-web

```

---

## 二、 部署应用代码与依赖

### 1. 克隆代码库

切换到 `mirofish` 用户并克隆项目：

```bash
sudo su - mirofish
git clone --recurse-submodules <your-repo-url> app
cd app

```

### 2. 安装 Python 与 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv sync --frozen

```

### 3. 编译 Tailwind 生产样式

```bash
./tailwindcss/tailwindcss -i ./static/css/input.css -o ./static/css/app.css --minify

```

### 4. 编写生产环境 `.env`

复制并修改配置文件：

```bash
cp .env.example .env
nano .env

```

生产环境关键配置修改：

```env
DEBUG=false
DATABASE_URL=postgresql+asyncpg://mirofish:your_secure_password@localhost/mirofish
REDIS_URL=redis://localhost:6379/0
COOKIE_SECURE=true
LLM_API_KEY=your_production_llm_api_key
UPLOAD_DIR=/var/lib/mirofish-web/uploads

```

### 5. 执行数据库迁移

```bash
uv run alembic upgrade head

```

---

## 三、 配置 Systemd 服务

我们需要配置两个 systemd 服务：`mirofish-web`（FastAPI 服务）和 `mirofish-worker`（arq 任务异步队列）。

### 1. 创建 Web 服务单元

创建 `/etc/systemd/system/mirofish-web.service`：

```ini
[Unit]
Description=MiroFish Web FastAPI Service
After=network.target postgresql.service redis-server.service

[Service]
User=mirofish
Group=mirofish
WorkingDirectory=/opt/mirofish-web/app
ExecStart=/opt/mirofish-web/.local/bin/uv run uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5
StandardOutput=append:/var/log/mirofish-web/web.log
StandardError=append:/var/log/mirofish-web/web_error.log

[Install]
WantedBy=multi-user.target

```

### 2. 创建 Worker 服务单元

创建 `/etc/systemd/system/mirofish-worker.service`：

```ini
[Unit]
Description=MiroFish Arq Worker Service
After=network.target redis-server.service postgresql.service

[Service]
User=mirofish
Group=mirofish
WorkingDirectory=/opt/mirofish-web/app
ExecStart=/opt/mirofish-web/.local/bin/uv run arq worker.runner.WorkerSettings
Restart=always
RestartSec=5
StandardOutput=append:/var/log/mirofish-web/worker.log
StandardError=append:/var/log/mirofish-web/worker_error.log

[Install]
WantedBy=multi-user.target

```

### 3. 启动并启用服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mirofish-web mirofish-worker

```

检查服务状态：

```bash
sudo systemctl status mirofish-web mirofish-worker

```

---

## 四、 配置 Nginx 反向代理与 SSL

### 1. 安装 Certbot (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx

```

### 2. 配置 Nginx 站点

创建 `/etc/nginx/sites-available/mirofish`：

```nginx
server {
    server_name yourdomain.com;

    client_max_body_size 100M; # 支持上传较大的种子材料文件

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 支持 SSE (Server-Sent Events) 与 WebSocket
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }
}

```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/mirofish /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

```

### 3. 签发 SSL 证书 (HTTPS)

```bash
sudo certbot --nginx -d yourdomain.com

```

按照提示输入邮箱并同意条款后，Certbot 会自动配置 HTTPS 重定向。

---

## 五、 日常运维与日志排查

* **查看 Web 实时日志**:
```bash
tail -f /var/log/mirofish-web/web.log

```


* **查看 Worker 实时日志**:
```bash
tail -f /var/log/mirofish-web/worker.log

```


* **重启服务**:
```bash
sudo systemctl restart mirofish-web mirofish-worker

```
