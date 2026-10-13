"""OpenAPI 全局元数据定义。"""
from importlib.metadata import version as pkg_version

TITLE = "MiroFish Web"
SUMMARY = "多智能体群体仿真预测引擎 —— 自托管推演平台"
VERSION = pkg_version("mirofish") # 读取 pyproject.toml 中的 version

DESCRIPTION = """
**MiroFish Web** —— 多智能体仿真推演平台（自托管版）。

基于 MiroFish 引擎的五阶段流水线：
**种子材料 → 知识图谱 → 批量 Agent 生成 → OASIS 双平台模拟 → 结构化报告**

## 模块
* **任务** —— 创建推演任务、配置参数、查看进度与费用
* **引擎** —— 图谱构建 / Agent 生成 / 模拟执行 / 报告产出
* **观摩** —— SSE 事件直播、知识图谱可视化（二期）
* **后台** —— 账号、成本看板、系统配置

> ⚠️ 本平台输出为基于当前输入的**仿真推演结果**，
> 属待验证假设，不构成准确率承诺或预测背书。
"""

TAGS_METADATA = [
    {"name": "auth",   "description": "JWT 登录与账号管理"},
    {"name": "tasks",  "description": "推演任务创建、列表、参数配置"},
    {"name": "engine", "description": "五阶段流水线状态与进度"},
    {"name": "observe","description": "SSE 直播、图谱可视化（二期）"},
    {"name": "admin",  "description": "成本看板、模型配置（二期）"},
]

