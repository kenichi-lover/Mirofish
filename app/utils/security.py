from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

# Argon2 默认参数已平衡安全与性能，如需自定义可传入 time_cost, memory_cost, parallelism
ph = PasswordHasher()

# ⭐ 时序攻击防护：预计算一个虚拟哈希，确保用户不存在时验证耗时与正常验证一致
_DUMMY_HASH: str = ph.hash("dummy-password-for-timing-attack")

def hash_password(password: str) -> str:
    """对明文密码进行 Argon2id 哈希。

    Raises:
        ValueError: 密码为空或少于 8 位时抛出
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 charactors")
    return ph.hash(password)

def verity_password(plain_password: str, hash_password: str) -> bool:
    """验证明文密码是否匹配 Argon2 哈希。"""
    if not plain_password or not hash_password:
        return False
    try:
        ph.verify(hash_password, plain_password)
        return True
    except (VerifyMismatchError, InvalidHash):
        return False

def verity_dummy_password(plain_password: str) -> None:
    """对不存在的用户执行等价耗时的密码验证，防止时序攻击猜解用户名。"""
    try:
        ph.verify(_DUMMY_HASH, plain_password)
    except (VerifyMismatchError, InvalidHash):
        pass # 必定失败，目的只是消耗等量时间

def check_needs_rehash(hashed_password: str) -> bool:
    """检查哈希是否需要重新哈希（例如算法参数升级后）。"""
    return ph.check_needs_rehash(hashed_password)
