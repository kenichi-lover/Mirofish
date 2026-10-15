"""
本模块基于 slowapi 提供 API 速率限制能力，采用基于客户端 IP 的
限流键策略。限流器实例通过本模块导出，供应用工厂注册到 app.state，
路由层通过 @limiter.limit("5/minute") 装饰器声明限流规则。

主要组件:
    - limiter: 全局速率限制器实例（基于客户端远程地址）
    - register_rate_limiter: 将限流器注册到 FastAPI 应用的辅助函数

使用方式:
    # 1. 应用工厂中注册（main.py / factory.py）
    register_rate_limiter(app)

    # 2. 路由中声明限流规则
    @router.post("/login")
    @limiter.limit("5/minute")          # 注意: 必须在路由装饰器之下
    async def login(request: Request, ...):
        ...
"""

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# 限流键：以客户端 IP 作为限流维度
# 注意: 若部署在反向代理（Nginx 等）之后，需确保代理设置
# X-Forwarded-For 并启用 uvicorn 的 --proxy-headers，否则所有
# 请求将共享代理服务器的 IP，导致全体用户被合并限流。
_get_client_ip = get_remote_address

# 全局限流器实例（单例，整个应用共享内存计数）
limiter = Limiter(key_func=_get_client_ip)


def register_rate_limiter(app: FastAPI) -> None:
    """将限流器及其异常处理器注册到 FastAPI 应用。

    必须在应用创建后、启动前调用：
        app.include_router(...) 之后调用即可。

    Args:
        app: FastAPI 应用实例。
    """
    # slowapi 约定：从 app.state.limiter 读取限流器实例
    app.state.limiter = limiter
    # 超限请求统一返回 429 Too Many Requests
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

