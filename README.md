```markdown
# MiroFish Web
> 基于 [MiroFish](https://github.com/666ghj/MiroFish) 引擎的自托管多智能体
> 仿真推演平台 —— 上传材料、观看群体模拟、产出结构化推演报告。
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Debian](https://img.shields.io/badge/Debian-13-A81D33?logo=debian&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue)
## 这是什么
MiroFish 是一个群体智能预测引擎：从种子材料构建知识图谱，批量生成带人设的
Agent，在 OASIS 双平台中并行模拟群体互动，最终生成趋势推演报告，并支持
运行中的"上帝视角"变量注入。
本项目不改动 MiroFish 的模拟能力，而是重做它的"壳"：
| | 原版 MiroFish | MiroFish Web（本项目） |
|---|---|---|
| Web 层 | Flask + Vue 前后端分离 | FastAPI + Jinja2 服务端渲染，无 Node 构建链 |
| Agent 记忆 | Zep Cloud（外部 SaaS） | LlamaIndex 本地知识图谱 + PostgreSQL |
| 任务管理 | 单次运行 | 多任务队列、进度追踪、失败重跑、预算控制 |
| 过程观摩 | 基础 | SSE 实时沙盘直播、图谱可视化、Agent 对话 |
| 部署 | macOS 优先 | 单台 Debian 13，systemd 多服务 |
## 开发进度
本项目按模块推进，当前状态：
| 模块 | 状态 | 说明 |
|---|---|---|
| 用户认证（注册 / 登录 / 登出，JWT + Cookie） | ✅ 完成 | 限流、防时序攻击、HttpOnly Cookie |
| 用户自助（改资料 / 改密码 / 注销） | ✅ 完成 | `routers/api/user.py` |
| 管理后台（用户治理） | ✅ 完成 | `routers/api/user_admin.py`，含超管保护 |
| 数据库迁移（Alembic） | ✅ 完成 | `users` 表及扩展字段 |
| 页面渲染（Jinja2 + HTMX） | 🚧 进行中 | `routers/web/` |
| 推演任务（arq 四阶段流水线） | ⏳ 规划中 | `worker/` |
| 图谱构建（LlamaIndex） | ⏳ 规划中 | `services/graph_engine.py` |
| 沙盘直播（SSE）/ 图谱可视化 / Agent 对话 | ⏳ 规划中 | |
| 报告生成 / 成本看板 | ⏳ 规划中 | |
## 核心功能（目标形态）
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
## 目录结构（当前实际）
```
mirofish/
├── main.py                  # FastAPI 入口
├── pyproject.toml           # uv 依赖声明
├── uv.lock
├── alembic/                 # 数据库迁移（users 表）
├── alembic.ini
├── .env.example             # 配置模板（复制为 .env）
│
├── app/
│   ├── config/              # 配置（settings、database、metadata）
│   ├── dependencies/        # 依赖注入：DbSession、JWT 认证、当前用户
│   │   └── auth.py          #   get_current_user / require_superuser / 可选认证
│   ├── models/              # SQLAlchemy 模型（users 表 + mixins）
│   ├── schemas/             # Pydantic 模型（请求/响应体）
│   ├── routers/
│   │   ├── api/             # JSON 接口
│   │   │   ├── auth.py      #   /auth/register /login /logout
│   │   │   ├── user.py      #   /users/me 资料、密码、注销
│   │   │   └── user_admin.py#   /admin/users 用户治理
│   │   └── web/             # 页面路由（Jinja2，规划中）
│   ├── services/            # 领域逻辑（路由只做编排，业务全在这里）
│   │   ├── auth_service.py  #   注册 + 登录凭据校验
│   │   ├── user_service.py  #   用户资料管理
│   │   └── admin_service.py #   管理员用户治理
│   └── utils/               # 无状态通用函数
│       ├── auth.py          #   Cookie 设置/清除
│       ├── jwt.py           #   Token 签发/解析
│       ├── limiter.py       #   slowapi 限流
│       └── security.py      #   密码哈希/校验
│
├── docs/                    # 设计文档（PRD、模块说明）
├── tests/                   # pytest
└── README.md
```
> 随任务队列、仿真引擎等模块落地，将逐步补充
> `worker/`、`vendor/mirofish/`、`templates/`、`static/` 目录。
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
git clone <your-repo-url> mirofish
cd mirofish
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
| `COOKIE_SECURE` | 生产环境设为 `true`（HTTPS-only Cookie） |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | JWT 有效期（秒） |
| `LLM_API_KEY` | OpenAI 兼容 API Key（任务模块上线后使用） |
| `LLM_BASE_URL` | 如 `https://api.deepseek.com/v1` |
| `DEFAULT_BUDGET_CNY` | 单任务默认预算（元），超限自动暂停 |
### 6. 数据库迁移
```bash
uv run alembic upgrade head
```
### 7. 启动（开发模式）
```bash
uv run uvicorn main:app --reload --port 8000
```
访问 <http://localhost:8000>，首次运行创建管理员：
```bash
uv run python -m app.utils.create_admin
```
> 任务队列模块上线后，需额外启动 Worker：
> `uv run arq worker.runner.WorkerSettings`
## 生产部署
使用 systemd 管理服务（PostgreSQL / Redis 用系统自带服务）：
```bash
sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mirofish-web
```
查看日志：
```bash
journalctl -u mirofish-web -f
```
反向代理与 HTTPS 配置见 `DEPLOYMENT.md`。
## 开发
```bash
uv run pytest                                              # 运行测试
uv run alembic revision --autogenerate -m "msg"            # 生成迁移
uv run uvicorn main:app --reload                           # 开发服务器
```
分层约定（详见 `docs/`）：
- **路由层**（`app/routers/`）只做请求编排：解析请求 → 调 Service → 组装响应，
  不写业务逻辑，不直接操作数据库；
- **服务层**（`app/services/`）承载全部领域逻辑，构造函数接收裸
  `AsyncSession`（不带 `Depends`，保证可脱离 FastAPI 单测）；
- **依赖层**（`app/dependencies/`）是唯一使用 `Depends` 的地方：
  `DbSession`、`CurrentUser`、`SuperUser`、`OptionalUser`；
- **工具层**（`app/utils/`）只放无状态通用函数（哈希、JWT、Cookie、限流）；
- `app/routers/web/` 只返回 HTML，`app/routers/api/` 只返回 JSON/SSE/WS。
## 许可证与致谢
- 本项目基于 [MiroFish](https://github.com/666ghj/MiroFish)（AGPL-3.0）构建。
  仿真引擎引入后将放入 `vendor/mirofish/`（git submodule），
  遵循上游 AGPL-3.0 协议。**若你修改本仓库代码并对外提供网络服务，需按
  AGPL-3.0 开源相应修改**；仅内部使用不受影响。
- 感谢 [CAMEL-AI](https://github.com/camel-ai/camel) 的 OASIS 仿真引擎，
  以及 MiroFish 原作者与社区。
## 免责声明
本平台输出的是基于给定输入的**群体仿真推演结果**，反映"在这些条件与规则下
可能长出的演化路径"，不构成对真实事件的预测或投资/决策建议。请在报告中
保持"待验证假设"的表述。
```
