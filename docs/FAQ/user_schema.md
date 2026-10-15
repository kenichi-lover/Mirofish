| 改动 | 原因 |
|------|------|
| `UserUpdate` 移除 `is_active`、`is_superuser` | 🔒 安全漏洞修复：普通用户不可自行提权或激活账号 |
| `UserUpdate` 不含 `password` | 密码修改走 `UserPasswordUpdate`（需验证旧密码），职责分离 |
| 新增 `AdminUserUpdate` | 管理员专属 Schema，包含权限字段 + 密码强制设置 |
| `UserPublic` 补充 `full_name` | `UserCreate` 支持传入 `full_name`，但响应体原来缺失该字段，导致创建后查不到 |
| `AdminPasswordReset` 保留 | 与 `AdminUserUpdate.password` 互补：前者是独立的重置端点，后者是 PATCH 更新时顺带改密码 |


