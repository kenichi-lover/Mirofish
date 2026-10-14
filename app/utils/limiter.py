from slowapi import Limiter
from slowapi.util import get_remote_address

# 优化: 引入基于 IP 的速率限制器
Limiter = Limiter(key_func=get_remote_address)
