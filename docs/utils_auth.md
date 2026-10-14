在用户认证流程中，登录（Login）、Token 刷新（Refresh）、OAuth 回调等多个路由都需要将 JWT 写入 HttpOnly Cookie。如果将 response.set_cookie(...) 及其一长串安全参数（如 httponly, samesite, secure, max_age 等）直接写在各个路由里，会导致严重的代码重复（违反 DRY 原则），且后续修改 Cookie 策略时容易漏改。
将其抽取为一个独立的辅助函数（Helper Function）是最佳实践。

response 和 access_token 是运行时动态数据，必须由路由层传入；而 Cookie 的安全配置（如 max_age, domain, secure）是全局静态配置，应该通过配置管理（如 pydantic-settings）注入，而不是通过 FastAPI 的 Depends。

为什么不建议将其改造为依赖项？
依赖项（Depends）通常用于获取数据（如获取当前用户、获取数据库 Session）或前置校验。而“设置 Cookie”是一个副作用（Side Effect），它依赖于路由执行后产生的结果（即 access_token）。把产生副作用的操作强行塞进依赖注入系统，会导致逻辑倒置，让代码难以阅读和调试。
结论： 保持 set_auth_cookie 作为普通辅助函数，在路由中直接调用，是 FastAPI 社区最标准、最清晰的做法。

1. ⚠️ 必须补充 domain 参数
如果你的应用部署在子域名下（如 api.example.com 和 www.example.com），或者未来有跨子域共享 Cookie 的需求，缺少 domain 会导致 Cookie 无法正确传递。即使当前是单域名，显式声明也是好习惯。
2. 💡 建议补充 expires 参数
虽然现代浏览器主要依赖 max_age，但部分老旧客户端或特定代理服务器仍会回退读取 expires。FastAPI/Starlette 不会自动根据 max_age 生成 expires，建议两者同时设置以保证最大兼容性。
3. 🔍 确认 Token 格式一致性
你的代码中 value=access_token 是直接写入原始 token。请确保这与你在 auth.py 中解析 Cookie 的逻辑一致：

    如果 decode_access_token 期望接收纯 JWT 字符串 → 你的写法正确 ✅
    如果 HTTPBearer 或解析逻辑期望 Bearer <token> 格式 → 需要改为 f"Bearer {access_token}"
