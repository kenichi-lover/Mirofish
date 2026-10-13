# MiroFish Web
> 基于 [MiroFish](https://github.com/666ghj/MiroFish) 引擎的自托管多智能体
> 仿真推演平台 —— 上传材料、观看群体模拟、产出结构化推演报告。
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex- 🦙-pink)
![Debian](https://img.shields.io/badge/Debian-13-A81D33?logo=debian&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue)
## 这是什么
MiroFish 是一个群体智能预测引擎：从种子材料构建知识图谱，批量生成带人设的
Agent，在 OASIS 双平台中并行模拟群体互动，最终生成趋势推演报告，并支持
运行中的"上帝视角"变量注入。
本项目没有改动 MiroFish 的模拟能力，而是重做了它的"壳"：
| | 原版 MiroFish | MiroFish Web（本项目） |
|---|---|---|
| Web 层 | Flask + Vue 前后端分离 | FastAPI + Jinja2 服务端渲染，无 Node 构建链 |
| Agent 记忆 | Zep Cloud（外部 SaaS） | LlamaIndex 本地知识图谱 + PostgreSQL |
| 任务管理 | 单次运行 | 多任务队列、进度追踪、失败重跑、预算控制 |
| 过程观摩 | 基础 | SSE 实时沙盘直播、图谱可视化、Agent 对话 |
| 部署 | macOS 优先 | 单台 Debian 13，systemd 三服务 |
## 核心功能
- **推演任务**：上传种子材料 + 提问 → 自动完成图谱构建、Agent 生成、模拟、报告四阶段
- **沙盘直播**：SSE 实时观看模拟事件流，模拟进行中可注入新变量做 what-if
- **图谱可视化**：ECharts 力导向图浏览实体关系，点击查看事件详情
- **Agent 对话**：与模拟世界中的任意 Agent 一对一聊天
- **推演报告**：结构化 Markdown 报告（事件脉络 / 关键节点 / 趋势判断），支持追问
- **成本控制**：单任务预算硬上限、token 计量、月度费用看板
- **后台管理**：任务治理、模型配置、账号管理
## 技术栈
| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + uvicorn |
| 页面渲染 | Jinja2 + HTMX + Alpine.js |
| 可视化 | Apache ECharts |
| RAG / 图谱 | LlamaIndex（PropertyGraphIndex） |
| 仿真引擎 | OASIS（CAMEL-AI），经 MiroFish 引擎层调用 |
| 任务队列 | arq（Redis-based asyncio queue） |
| 数据库 | PostgreSQL 16 + Redis 7 |
| LLM | 任意 OpenAI 兼容 API（默认 DeepSeek） |
| Embedding | BGE-M3（本地运行，无需显卡） |
| 样式 | Tailwind CSS（Standalone CLI，免 Node） |
| 包管理 | uv |
| 部署 | systemd on Debian 13 |
## 架构
```
┌────────────────────────────────────────────────┐
│     Jinja2 前端（HTMX / Alpine / ECharts）       │
│  任务创建 │ 沙盘直播 │ 图谱 │ 报告 │ 对话 │ 后台   │
└──────────────────┬─────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────┐
│              FastAPI（Web 进程）                 │
│   页面路由 │ 任务 API │ SSE 进度 │ WS 对话        │
└───────┬───────────────────────────┬────────────┘
        ▼                           ▼
┌─────────────────┐       ┌──────────────────────┐
│   PostgreSQL    │       │  Redis               │
│ 任务/Agent/事件/  │       │  arq 队列 + PubSub    │
│ 报告/图谱        │       │  + 变量注入队列        │
└─────────────────┘       └──────────┬───────────┘
                                     ▼
                  ┌──────────────────────────────────┐
                  │   arq Worker（独立进程）            │
                  │ ① LlamaIndex 图谱构建              │
                  │ ② Agent 人设批量生成               │
                  │ ③ OASIS 双平台模拟 ←─ 变量注入       │
                  │ ④ ReportAgent 报告生成             │
                  └──────────┬───────────────────────┘
                             ▼
                    DeepSeek API / 本地 BGE-M3
```
## 目录结构
```
mirofish-web/
├── main.py                  # FastAPI 入口
├── pyproject.toml           # uv 依赖声明
├── uv.lock
├── alembic/                 # 数据库迁移
├── alembic.ini
├── tailwind.config.js
├── tailwindcss/             # Tailwind Standalone 二进制
├── .env.example             # 配置模板（复制为 .env）
├── CLAUDE.md  README.md  DEPLOYMENT.md  SECURITY.md
│
├── app/
│   ├── config/              # 配置（env 解析、路径、预算规则）
│   ├── dependencies/        # JWT 鉴权、DB session、当前用户
│   ├── models/              # SQLAlchemy 模型（8 张核心表）
│   ├── schemas/             # Pydantic 模型
│   ├── routers/
│   │   ├── web/             # 页面路由（tasks/graph/report/chat/admin）
│   │   └── api/             # JSON / SSE / WebSocket 接口
│   ├── services/
│   │   ├── graph_engine.py  # LlamaIndex 图谱封装
│   │   ├── agent_factory.py # Agent 人设生成
│   │   └── report.py        # 报告生成
│   └── utils/
│
├── worker/                  # arq Worker（独立进程）
│   ├── runner.py            # 四阶段流水线编排
│   └── oasis_adapter.py     # OASIS / MiroFish 引擎适配
│
├── vendor/
│   └── mirofish/            # 上游引擎（git submodule，AGPL-3.0）
│
├── templates/               # Jinja2 模板
├── static/                  # 静态资源
└── tests/
```
运行时数据不在仓库内：日志写 `/var/log/mirofish-web/`，上传文件写
`/var/lib/mirofish-web/uploads/`，路径由 `.env` 配置。
## 快速开始（Debian 13）
### 1. 系统依赖
```bash
sudo apt update
sudo apt install postgresql redis-server git
```
### 2. 数据库初始化
```bash
sudo -u postgres createuser mirofish -P      # 按提示设置密码
sudo -u postgres createdb mirofish -O mirofish
```
### 3. 拉取项目
```bash
git clone --recurse-submodules <your-repo-url> mirofish-web
cd mirofish-web
```
### 4. 安装依赖（uv）
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # 若未安装 uv
uv sync
```
### 5. 配置
```bash
cp .env.example .env
vim .env
```
关键配置项：
| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://mirofish:***@localhost/mirofish` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `LLM_API_KEY` | OpenAI 兼容 API Key（默认 DeepSeek） |
| `LLM_BASE_URL` | 如 `https://api.deepseek.com/v1` |
| `LLM_MODEL_NAME` | 如 `deepseek-chat` |
| `UPLOAD_DIR` | `/var/lib/mirofish-web/uploads` |
| `DEFAULT_BUDGET_CNY` | 单任务默认预算（元），超限自动暂停 |
### 6. 数据库迁移 & 编译样式
```bash
uv run alembic upgrade head
./tailwindcss/tailwindcss -i ./static/css/input.css -o ./static/css/app.css --minify
```
### 7. 启动（开发模式）
```bash
# 终端 1：Web
uv run uvicorn main:app --reload --port 8000
# 终端 2：Worker
uv run arq worker.runner.WorkerSettings
```
访问 <http://localhost:8000>，首次运行执行以下命令创建管理员：
```bash
uv run python -m app.utils.create_admin
```
## 生产部署
使用 systemd 管理两个服务（PostgreSQL / Redis 用系统自带服务）：
```bash
sudo cp deploy/mirofish-web.service /etc/systemd/system/
sudo cp deploy/mirofish-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mirofish-web mirofish-worker
```
查看日志：
```bash
journalctl -u mirofish-web -f
journalctl -u mirofish-worker -f
```
反向代理与 HTTPS 配置见 [DEPLOYMENT.md](DEPLOYMENT.md)。
## 开发
```bash
uv run pytest              # 运行测试
uv run alembic revision --autogenerate -m "msg"   # 生成迁移
./tailwindcss/tailwindcss -i ... --watch           # 样式监听模式
```
约定：
- `app/routers/web/` 只返回 HTML，`app/routers/api/` 只返回 JSON/SSE/WS；
- `app/utils/` 只放无状态通用函数，领域逻辑进 `app/services/`；
- `vendor/mirofish/` 内的代码不直接修改，适配层写在 `worker/oasis_adapter.py`。
## 许可证与致谢
- 本项目基于 [MiroFish](https://github.com/666ghj/MiroFish)（AGPL-3.0）构建，
  `vendor/mirofish/` 目录遵循上游 AGPL-3.0 协议。**若你修改本仓库代码并对外
  提供网络服务，需按 AGPL-3.0 开源相应修改**；仅内部使用不受影响。
- 感谢 [CAMEL-AI](https://github.com/camel-ai/camel) 的 OASIS 仿真引擎，
  以及 MiroFish 原作者与社区。
## 免责声明
本平台输出的是基于给定输入的**群体仿真推演结果**，反映"在这些条件与规则下
可能长出的演化路径"，不构成对真实事件的预测或投资/决策建议。请在报告中
保持"待验证假设"的表述。
