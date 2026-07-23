"""流水线数据模型。

第一性原理：一条流水线本质上是「若干阶段的有序集合，每个阶段含若干步骤」。
不需要复杂的继承或状态机，用朴素的 dataclass 直接描述这个结构即可。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Step:
    """单个步骤：一条 shell 命令，或一次部署动作。

    一切能力都从「执行一条命令」这个原子操作派生：
    - run: 要执行的命令（核心）
    - timeout: 防止命令挂死（真实工程的必需约束）
    - env: 该步骤专属的环境变量
    - continue_on_error: 失败是否继续后续步骤（真实场景中测试常需要）
    - deploy: 部署配置（run 之外唯一的另一种动作）
    """
    name: str = ""
    run: Optional[str] = None
    timeout: Optional[int] = None
    env: dict = field(default_factory=dict)
    continue_on_error: bool = False
    deploy: Optional[dict] = None


@dataclass
class Stage:
    """阶段：一组逻辑相关的步骤。失败默认中断后续阶段。"""
    name: str
    steps: list = field(default_factory=list)
    when: Optional[str] = None  # 条件表达式，如 "branch == 'main'"


@dataclass
class Pipeline:
    """整条流水线：环境变量 + 有序的阶段列表。"""
    name: str
    stages: list = field(default_factory=list)
    workspace: str = "."       # 命令的工作目录
    env: dict = field(default_factory=dict)
