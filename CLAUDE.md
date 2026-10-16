# CLAUDE.md - MiroFish Web 项目指令指南

本文件是 Claude Code 执行代码修改、重构与新模块开发时的核心规范与架构约定。

---

## 1. 常用开发与测试命令

### 依赖与环境
- **安装依赖**: `uv sync`
- **新增依赖**: `uv add <package>`

### 开发服务器
- **启动 Web 服务**: `uv run uvicorn main:app --reload --port 8000`
- **启动 Worker 进程**: `uv run arq worker.runner.WorkerSettings`
- **Tailwind 样式监听**: `./tailwindcss/tailwindcss -i ./static/css/input.css -o ./static/css/app.css --watch`

### 数据库迁移 (Alembic)
- **生成迁移脚本**: `uv run alembic revision --autogenerate -m "描述说明"`
- **应用数据库迁移**: `uv run alembic upgrade head`
- **回滚一步迁移**: `uv run alembic downgrade -1`

### 测试与工具
- **运行全部测试**: `uv run pytest`
- **运行单个测试文件**: `uv run pytest tests/test_auth.py`
- **创建初始化管理员**: `uv run python -m app.utils.create_admin`

---

## 2. 核心架构与分层设计约定

为保证代码可读性与可测试性，代码编写必须严格遵循以下分层约定：

```
[ 请求 ] ──> [ 路由层 app/routers ] ──> [ 依赖注入 app/dependencies ]
                     │
                     ▼
          [ 服务层 app/services ] (纯领域逻辑，接裸 AsyncSession)
                     │
                     ▼
          [ 模型与工具 app/models, app/utils ]
```

### 1) 路由层 (`app/routers/`)
- **职责**：仅负责请求编排、入参校验、调用 Service、组装响应。
- **禁忌**：**严禁在路由函数内直接写业务逻辑，严禁直接操作数据库 `AsyncSession`**。
- **区分**：
  - `app/routers/api/`：仅返回 JSON、SSE 状态流或 WebSocket 响应。
  - `app/routers/web/`：仅返回 HTML（Jinja2 模板渲染）。

### 2) 服务层 (`app/services/`)
- **职责**：承载全部领域业务逻辑、事务控制与外部引擎调用。
- **规范**：构造函数统一接收裸 `AsyncSession`（**不使用 `Depends`**），确保可以脱离 FastAPI 框架单独进行单元测试。
- **示例**：
  ```python
  class UserService:
      def __init__(self, db: AsyncSession):
          self.db = db
  ```

### 3) 依赖层 (`app/dependencies/`)
- **职责**：FastAPI 专用的依赖注入定义。
- **常见依赖**：
  - `DbSession`: 获取异步数据库会话
  - `CurrentUser`: 获取并验证当前 JWT 登录用户
  - `SuperUser`: 校验管理员权限
  - `OptionalUser`: 尝试获取可选登录状态

### 4) 工具层 (`app/utils/`)
- **职责**：仅放置**无状态通用函数**（如密码哈希、JWT 签发/解析、Cookie 操作、slowapi 限流）。
- **禁忌**：不要放任何涉及具体业务流程或数据库操作的代码。

### 5) 适配层与 Worker (`worker/`)
- **上游隔离**：`vendor/mirofish/` 作为 git submodule 引入，**不得直接修改其内部代码**。
- **适配逻辑**：所有的适配与封装统一编写在 `worker/oasis_adapter.py` 或 `app/services/` 中。

---

## 3. 代码风格与约束

- **Python 版本**: Python 3.11+，强类型标注（`type hints`），使用 `async/await` 异步编写。
- **Web 技术栈**: FastAPI + Jinja2 + HTMX + Alpine.js。前端禁止引入 Node.js/NPM 构建链及 React/Vue 等 SPA 框架。
- **数据库**: SQLAlchemy 2.0 (Async) + Alembic。模型放置于 `app/models/`，Schema 放置于 `app/schemas/`。
- **安全约定**:
  - JWT 存储于 HttpOnly, SameSite Cookie 中。
  - 密码必须使用 `passlib/argon2` 或 `bcrypt` 进行异步哈希。
  - 敏感操作需进行防时序攻击校对（如 `hmac.compare_digest`）。

---

## 4. 后续模块落地路线图

在协助编写后续功能时，请参考以下规划补全相应代码目录：

1. **`templates/` & `static/`**: 编写 Jinja2 模版与 HTMX 交互逻辑。
2. **`worker/`**:
   - `runner.py`: arq 四阶段任务流水线（图谱构建 -> Agent 生成 -> OASIS 模拟 -> 报告生成）。
   - `oasis_adapter.py`: 封装上游 MiroFish/OASIS 调用。
3. **`app/services/graph_engine.py`**: 基于 LlamaIndex `PropertyGraphIndex` 的本地知识图谱构建。