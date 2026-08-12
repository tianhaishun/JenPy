"""依赖注入：BuildManager 单例与配置。

第一性原理：FastAPI 的 Depends 机制让「全局资源从哪来」显式且可测试。
BuildManager 是进程内单例，所有路由共享同一个构建队列。
"""

from __future__ import annotations

from ..manager import BuildManager, get_manager


def get_build_manager() -> BuildManager:
    """提供全局 BuildManager 实例（FastAPI 依赖注入入口）。"""
    return get_manager()
