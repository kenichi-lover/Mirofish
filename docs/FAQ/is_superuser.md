# 创建 Superuser：PostgreSQL 直接操作方案
先划清边界：结合你的代码，**只有一种场景必须动数据库**——系统里一个可用超管都没有（bootstrap 死锁）。你的 `AuthService.register` 硬编码 `is_superuser=False`，`AdminService.create_user` 又需要已有超管才能调路由，此时 SQL 是唯一入口。其余日常操作（提权、禁用、重置密码）都应走 `/admin/users` 路由。
---
## 第 0 步：确认表名和现有状态
SQLModel 默认表名是类名的小写。`User` → `user`，但 `user` 是 PostgreSQL 保留字，**SQL 中必须带双引号**。先核实：
```sql
-- 确认表名（可能是 user / users，取决于你 model 的 __tablename__）
\dt
-- 查看当前超管状态（对应你 _count_active_superusers 的逻辑）
SELECT id, username, email, is_active, is_superuser
FROM "user"
WHERE is_superuser = true;
```
如果查询结果里有一个 `is_active = true` 的超管，**停止，去走路由**，不需要 SQL。
---
## 方案 A：提升现有用户为超管（首选，最安全）
不插入新数据、不碰哈希，规避了你注意事项里的第 1、2、4 条风险：
```sql
BEGIN;
UPDATE "user"
SET is_superuser = true,
    is_active    = true          -- 确保是"可用"超管，你的保护逻辑按 is_active 计数
WHERE username = 'paul'           -- 你的模型写入时统一小写，这里必须用小写精确匹配
  AND email = 'paul@example.com'; -- 双条件防误伤同名
-- 确认改动符合预期再提交
SELECT id, username, is_active, is_superuser FROM "user" WHERE username = 'paul';
COMMIT;
-- 不对就 ROLLBACK;
```
## 方案 B：插入全新超管（pgcrypto 生成 bcrypt 哈希）
你的 `verify_password`（passlib/bcrypt）能识别 `$2a$` 前缀的哈希，而 pgcrypto 的 `gen_salt('bf')` 正好产出 `$2a$` 格式，所以**纯 SQL 也能生成可验证的密码**：
```sql
-- 若扩展未装（需要超级用户权限或 RDS 授权）
CREATE EXTENSION IF NOT EXISTS pgcrypto;
BEGIN;
INSERT INTO "user" (username, email, full_name, hashed_password, is_active, is_superuser)
VALUES (
    'admin',                              -- 手动模拟你 service 层的 strip().lower() 归一化
    'admin@example.com',
    NULL,                                 -- full_name 可空，与你 create_user 的行为一致
    crypt('ChangeMe_2026!', gen_salt('bf', 12)),  -- bcrypt, cost=12
    true,
    true
);
SELECT id, username, is_active, is_superuser FROM "user" WHERE username = 'admin';
COMMIT;
```
**插入后立刻用新超管登录一次**验证哈希兼容，然后走 `PATCH /users/me/password` 改掉这个已知密码。
> ⚠️ 兼容性自查：如果你的 `CryptContext(schemes=["bcrypt"])` 用的是 passlib，`$2a$` 没问题；但如果配置了 `bcrypt__identify="2b"` 之类且强制校验前缀，方案 B 的哈希会验证失败——那就退到方案 C。
## 方案 C：两步走，哈希由 Python 生成（最稳妥）
完全绕开哈希格式兼容问题。先用占位符插入，再用你的应用代码补真哈希：
```sql
BEGIN;
INSERT INTO "user" (username, email, hashed_password, is_active, is_superuser)
VALUES ('admin', 'admin@example.com',
        'x',  -- 占位，登录不了，仅占位保证非空约束通过
        true, true)
RETURNING id;
COMMIT;
```
```bash
# 在项目根目录，直接复用你的 security 模块，保证哈希与应用层完全一致
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings   # 按你的实际配置路径调整
from app.models.user import User
from app.utils.security import hash_password
from sqlmodel import select
async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        user = (await s.execute(
            select(User).where(User.username == 'admin')
        )).scalar_one()
        user.hashed_password = hash_password('ChangeMe_2026!')
        await s.commit()
    await engine.dispose()
asyncio.run(main())
"
```
这个方案本质上是“**用 ORM 做数据更正**”——正是你注意事项里“推荐做法”的路线，哈希格式、字段验证全部与应用层一致，四个风险点全规避。
---
## 验证与善后
```sql
-- 复现你 service 层的保护计数，确认超管可用
SELECT count(*) AS active_superusers
FROM "user"
WHERE is_superuser = true AND is_active = true;   -- 期望 >= 1
-- 审计：确认没有意外产生的超管
SELECT id, username, email, is_active, is_superuser, created_at
FROM "user"
WHERE is_superuser = true
ORDER BY created_at;
```
## 对照你的四条风险，各方案的规避情况
| 风险 | 方案 A（提权） | 方案 B（pgcrypto） | 方案 C（SQL+ORM 补哈希） |
|---|---|---|---|
| ① 绕过验证器 | ✅ 不插入新数据 | ⚠️ 需手动小写归一化 | ✅ Python 侧走同一套代码 |
| ② is_active 与密码不一致 | ✅ 不碰哈希 | ⚠️ 依赖 `$2a$` 兼容，登录即验 | ✅ 哈希由应用生成 |
| ③ 外键/关联数据 | ✅ 纯 UPDATE 不触发级联 | ⚠️ 新行无关联，风险低 | ✅ 同左 |
| ④ 缺少级联的高级操作 | ✅ 不涉及 | ✅ 不涉及 | ✅ 不涉及 |
**结论**：能 A 不 B，哈希有疑虑用 C。三个方案都包在事务里、先 SELECT 后 COMMIT，出问题随时 `ROLLBACK`，不会有中间态残留。

