"""流水线执行引擎。

第一性原理：CI 执行的本质是「按顺序运行一组命令，实时展示输出，记录每个命令的成败与耗时」。
本模块只做这件事——拉起子进程、转发输出、捕获结果。不关心配置怎么来的，
也不关心结果存哪里，那些是 config 和 history 的职责。
"""

from __future__ import annotations
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .pipeline import Pipeline, Stage, Step


# 终端颜色（第一性原理：即使没颜色也能用，颜色只是锦上添花）
_USE_COLOR = sys.stdout.isatty()


def _c(text: str, color: str) -> str:
    """给文本上色；非交互终端则原样返回。"""
    if not _USE_COLOR:
        return text
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "gray": "90"}
    return f"\033[{codes.get(color, '0')}m{text}\033[0m"


@dataclass
class StepResult:
    """单个步骤的执行结果——执行引擎产出的最小信息单元。"""
    stage_name: str
    step_name: str
    success: bool
    returncode: int
    duration: float           # 秒
    skipped: bool = False


@dataclass
class BuildResult:
    """整条流水线一次执行的结果。"""
    pipeline_name: str
    success: bool
    steps: list               # List[StepResult]
    duration: float
    started_at: str           # ISO 格式


class Executor:
    """执行一条 Pipeline，逐阶段、逐步骤运行命令。

    设计原则：
    - 实时输出：stdout/stderr 流式转发，不等命令结束才打印
    - 失败即停：某步骤失败（且未设 continue_on_error）则中断整条流水线
    - 上下文隔离：每步用 pipeline.env + step.env 合并后的环境，不污染全局
    """

    def __init__(self, on_step: Optional[Callable[[StepResult], None]] = None):
        # on_step 回调：每个步骤结束后通知调用方（history 用它落盘）
        self._on_step = on_step or (lambda r: None)

    def run(self, pipeline: Pipeline, context: Optional[dict] = None) -> BuildResult:
        """执行整条流水线。

        Args:
            pipeline: 要执行的流水线
            context: 模板变量上下文，如 {"branch": "main", "repo_url": "..."}
        """
        context = context or {}
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        t0 = time.time()
        step_results: list = []
        overall_success = True

        print(_c(f"\n▶ 执行流水线: {pipeline.name}", "cyan"))
        print(_c(f"  工作目录: {os.path.abspath(pipeline.workspace)}", "gray"))

        for stage in pipeline.stages:
            if not self._should_run(stage, context):
                print(_c(f"\n[跳过阶段] {stage.name}（条件不满足）", "gray"))
                continue

            stage_ok = self._run_stage(
                stage, pipeline, context, step_results
            )
            if not stage_ok:
                overall_success = False
                break  # 阶段失败，终止整条流水线

        duration = time.time() - t0
        result = BuildResult(
            pipeline_name=pipeline.name,
            success=overall_success,
            steps=step_results,
            duration=duration,
            started_at=started_at,
        )

        self._print_summary(result)
        return result

    def _run_stage(
        self, stage: Stage, pipeline: Pipeline,
        context: dict, step_results: list,
    ) -> bool:
        """执行单个阶段，返回是否成功。"""
        print(_c(f"\n● 阶段: {stage.name}", "yellow"))

        # 合并环境变量：系统环境 < pipeline.env < step.env（后者优先级最高）
        base_env = {**os.environ, **pipeline.env}

        for step in stage.steps:
            step_env = {**base_env, **step.env}
            cmd = _render(step.run, context) if step.run else None

            # 延迟导入 deploy，避免未使用部署功能时的硬依赖
            if step.deploy is not None:
                from . import deploy
                ok = deploy.run(step.deploy, pipeline.workspace, step_env)
            else:
                ok = self._run_command(
                    cmd, step, step_env, pipeline.workspace,
                    stage.name, step_results,
                )

            if not ok and not step.continue_on_error:
                return False

        return True

    def _run_command(
        self, cmd: Optional[str], step: Step, env: dict,
        workspace: str, stage_name: str, step_results: list,
    ) -> bool:
        """执行单条命令，实时转发输出，记录结果。返回是否成功。"""
        label = step.name or cmd or "(空步骤)"
        print(_c(f"  $ {cmd}", "gray"))

        t0 = time.time()
        try:
            # 实时输出：stdout/stderr 都直接继承到当前进程的终端
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=workspace,
                env=env,
                timeout=step.timeout,
            )
            success = proc.returncode == 0
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            print(_c(f"  ✗ 超时（>{step.timeout}s）", "red"))
            success = False
            returncode = -1
        except Exception as e:
            print(_c(f"  ✗ 执行异常: {e}", "red"))
            success = False
            returncode = -2

        duration = time.time() - t0
        status = _c("✓", "green") if success else _c("✗", "red")
        print(f"  {status} {label} ({duration:.1f}s)")

        result = StepResult(
            stage_name=stage_name,
            step_name=label,
            success=success,
            returncode=returncode,
            duration=duration,
        )
        step_results.append(result)
        self._on_step(result)
        return success

    @staticmethod
    def _should_run(stage: Stage, context: dict) -> bool:
        """评估 when 条件。第一性原理：条件不存在就视为 True。"""
        if not stage.when:
            return True
        try:
            # 受限求值：把 context 里的变量作为命名空间
            # 注意：这是用于受信配置文件，不接受外部输入
            return bool(eval(stage.when, {"__builtins__": {}}, context))
        except Exception as e:
            print(_c(f"  ! 条件表达式错误 '{stage.when}': {e}，视为不执行", "yellow"))
            return False

    @staticmethod
    def _print_summary(result: BuildResult) -> None:
        """打印本次执行的汇总。"""
        status = _c("成功", "green") if result.success else _c("失败", "red")
        total = len(result.steps)
        passed = sum(1 for s in result.steps if s.success)
        print(_c(f"\n═══ 结果: {status}", "cyan"))
        print(_c(f"    步骤 {passed}/{total} 通过，耗时 {result.duration:.1f}s", "gray"))


def _render(template: Optional[str], context: dict) -> Optional[str]:
    """渲染 {{ var }} 模板变量。"""
    if template is None:
        return None
    out = template
    for key, val in context.items():
        out = out.replace("{{ " + key + " }}", str(val))
        out = out.replace("{{" + key + "}}", str(val))
    return out
