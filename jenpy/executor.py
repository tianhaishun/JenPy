"""流水线执行引擎。

第一性原理：CI 执行的本质是「按顺序运行一组命令，实时展示输出，记录每个命令的成败、耗时与完整日志」。
本模块只做这件事——拉起子进程、转发输出（同时落盘）、捕获结果。不关心配置怎么来的，
也不关心结果存哪里，那些是 config 和 history 的职责。
"""

from __future__ import annotations
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
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
    log_file: Optional[str] = None   # 该步骤完整输出的日志文件路径


@dataclass
class BuildResult:
    """整条流水线一次执行的结果。"""
    pipeline_name: str
    success: bool
    steps: list = field(default_factory=list)   # List[StepResult]
    duration: float = 0.0
    started_at: str = ""
    build_id: str = ""
    log_dir: Optional[str] = None   # 本次构建所有日志的目录


class Executor:
    """执行一条 Pipeline，逐阶段、逐步骤运行命令。

    设计原则：
    - 实时输出：stdout/stderr 流式转发到终端，同时落盘到日志文件
    - 失败即停：某步骤失败（且未设 continue_on_error）则中断整条流水线
    - 上下文隔离：每步用 pipeline.env + step.env 合并后的环境，不污染全局
    """

    def __init__(self, build_id: Optional[str] = None,
                 on_step: Optional[Callable[[StepResult], None]] = None):
        # build_id：本次构建的唯一标识，决定日志落盘目录
        # 不传则临时生成（history.save 会用真实 id 覆盖目录）
        self._build_id = build_id or _now_id()
        self._log_dir = os.path.join(".jenpy", "builds", self._build_id)
        os.makedirs(self._log_dir, exist_ok=True)
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
        print(_c(f"  构建ID:   {self._build_id}", "gray"))
        print(_c(f"  日志目录: {os.path.abspath(self._log_dir)}", "gray"))

        for stage in pipeline.stages:
            if not _should_run(stage, context):
                print(_c(f"\n[跳过阶段] {stage.name}（条件不满足）", "gray"))
                continue

            stage_ok = self._run_stage(stage, pipeline, context, step_results)
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
            build_id=self._build_id,
            log_dir=self._log_dir,
        )

        _print_summary(result)
        return result

    def _run_stage(self, stage: Stage, pipeline: Pipeline,
                   context: dict, step_results: list) -> bool:
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
                log_path = self._log_path(stage.name, step.name)
                ok = deploy.run(step.deploy, pipeline.workspace, step_env, log_path)
                result = StepResult(
                    stage_name=stage.name, step_name=step.name or "(deploy)",
                    success=ok, returncode=0 if ok else 1, duration=0.0,
                    log_file=log_path,
                )
                step_results.append(result)
                self._on_step(result)
                if not ok and not step.continue_on_error:
                    return False
            else:
                ok = self._run_command(
                    cmd, step, step_env, pipeline.workspace,
                    stage.name, step_results,
                )
                if not ok and not step.continue_on_error:
                    return False

        return True

    def _run_command(self, cmd, step, env, workspace,
                     stage_name, step_results) -> bool:
        """执行单条命令，实时转发输出并落盘，记录结果。返回是否成功。"""
        label = step.name or cmd or "(空步骤)"
        log_path = self._log_path(stage_name, label)
        print(_c(f"  $ {cmd}", "gray"))

        t0 = time.time()
        success, returncode = _stream_command(
            cmd, cwd=workspace, env=env, timeout=step.timeout, log_path=log_path,
        )
        duration = time.time() - t0

        status = _c("✓", "green") if success else _c("✗", "red")
        print(f"  {status} {label} ({duration:.1f}s)")

        result = StepResult(
            stage_name=stage_name,
            step_name=label,
            success=success,
            returncode=returncode,
            duration=duration,
            log_file=log_path,
        )
        step_results.append(result)
        self._on_step(result)
        return success

    def _log_path(self, stage_name: str, step_name: str) -> str:
        """为某个步骤生成安全的日志文件路径。"""
        safe = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
        fname = f"{safe(stage_name)}__{safe(step_name)}.log"
        return os.path.join(self._log_dir, fname)


def _stream_command(cmd, cwd, env, timeout, log_path) -> tuple:
    """运行命令：输出同时打到终端和日志文件，并支持超时终止。

    第一性原理：用户既要「实时看到」，又要「事后能查」，还要「超时能停」。
    关键点：超时检查不能依赖「有新输出」——命令可能长时间无输出（如 sleep），
    所以用一个后台线程来监控超时，与输出读取解耦。
    返回 (success, returncode)。
    """
    try:
        proc = subprocess.Popen(
            cmd, shell=True, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    except Exception as e:
        _write_file(log_path, f"启动命令失败: {e}\n")
        print(_c(f"  ✗ 启动失败: {e}", "red"))
        return False, -2

    timed_out = False

    # 后台超时监控线程：到点就杀进程，不依赖是否有输出
    def _watch():
        nonlocal timed_out
        if not timeout:
            return
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()

    import threading
    watcher = threading.Thread(target=_watch, daemon=True)
    watcher.start()

    with open(log_path, "w", encoding="utf-8") as f:
        try:
            for line in proc.stdout:
                print(line, end="")   # 终端
                f.write(line)          # 文件
                f.flush()
        except Exception as e:
            f.write(f"\n读取输出异常: {e}\n")

    watcher.join()
    proc.wait()

    if timed_out:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[超时：超过 {timeout}s 被终止]\n")
        print(_c(f"  ✗ 超时（>{timeout}s）", "red"))
        return False, -1

    return proc.returncode == 0, proc.returncode


def _write_file(path, text):
    """安全写入文件，忽略错误。"""
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def _should_run(stage: Stage, context: dict) -> bool:
    """评估 when 条件。

    第一性原理：条件不存在就视为 True。
    安全实现：只支持「变量 == 值」「变量 != 值」及其与/或组合，不用 eval。
    """
    if not stage.when:
        return True
    try:
        return _eval_condition(stage.when, context)
    except Exception as e:
        print(_c(f"  ! 条件表达式错误 '{stage.when}': {e}，视为不执行", "yellow"))
        return False


def _eval_condition(expr: str, context: dict) -> bool:
    """安全地求值 when 条件表达式。

    支持的语法（刻意保持极小，避免引入注入风险）：
      - 变量 == '字面量'      变量 != '字面量'
      - 多个条件用 and / or 连接，可用括号分组
    变量值来自 context；未定义的变量视为空串。
    """
    from .conditions import evaluate
    return evaluate(expr, context)


def _print_summary(result: BuildResult) -> None:
    """打印本次执行的汇总。"""
    status = _c("成功", "green") if result.success else _c("失败", "red")
    total = len(result.steps)
    passed = sum(1 for s in result.steps if s.success)
    print(_c(f"\n═══ 结果: {status}", "cyan"))
    print(_c(f"    步骤 {passed}/{total} 通过，耗时 {result.duration:.1f}s", "gray"))


def _render(template, context):
    """渲染 {{ var }} 模板变量。"""
    if template is None:
        return None
    out = template
    for key, val in context.items():
        out = out.replace("{{ " + key + " }}", str(val))
        out = out.replace("{{" + key + "}}", str(val))
    return out


def _now_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")
