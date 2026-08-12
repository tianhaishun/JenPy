"""构建编排器：Web 层与执行引擎之间的桥梁。

第一性原理：Web 层不应直接调用 Executor——它需要的是「触发一个构建、
查它的状态、订阅它的实时输出」，而不是「同步跑完一条流水线」。
BuildManager 把这些交互需求封装起来：
  - trigger()    异步触发，立即返回 build_id
  - get_status() 查某次构建的实时状态（queued / running / done）
  - subscribe()  订阅某次构建的行级输出（供 SSE）和步骤完成事件（供 WebSocket）
  - 内部串行执行，避免并发构建互相干扰（共享工作目录、日志目录）
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from . import history
from .config import load_pipeline
from .executor import BuildResult, Executor, StepResult
from .pipeline import Pipeline


class BuildStatus(str, Enum):
    """构建生命周期状态。"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class BuildState:
    """单次构建的运行时状态（内存中跟踪，构建结束写 history）。"""
    build_id: str
    pipeline_name: str = ""
    status: BuildStatus = BuildStatus.QUEUED
    started_at: str = ""
    duration: float = 0.0
    # 订阅者回调列表：on_line(stage, step, line) 和 on_step(StepResult)
    line_subs: list = field(default_factory=list)   # list[Callable[[str,str,str],None]]
    step_subs: list = field(default_factory=list)    # list[Callable[[StepResult],None]]
    result: Optional[BuildResult] = None


class BuildManager:
    """单例风格的构建编排器。

    用一个工作线程 + 队列串行处理构建，保证：
      1. 同一时刻只有一个构建在跑（避免工作目录/日志冲突）
      2. 触发请求立即返回，不阻塞调用方（Web 层）
    """

    def __init__(self):
        self._states: dict[str, BuildState] = {}      # build_id -> state
        self._queue: "queue.Queue[Optional[tuple]]" = queue.Queue()
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._started = False

    def start(self) -> None:
        """启动后台工作线程（幂等）。"""
        if self._started:
            return
        self._started = True
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

    def trigger(self, pipeline: Pipeline,
                context: Optional[dict] = None) -> str:
        """触发一次构建，立即返回 build_id。

        构建排入队列，由后台工作线程串行执行。
        """
        self.start()
        build_id = history.new_build_id()
        state = BuildState(build_id=build_id, pipeline_name=pipeline.name)
        with self._lock:
            self._states[build_id] = state
        self._queue.put((build_id, pipeline, context or {}))
        return build_id

    def trigger_file(self, config_file: str,
                     context: Optional[dict] = None) -> str:
        """从配置文件加载流水线并触发。便捷方法。"""
        pipeline = load_pipeline(config_file)
        return self.trigger(pipeline, context)

    def get_state(self, build_id: str) -> Optional[BuildState]:
        """查构建状态。完成后从 history 读取最终结果。"""
        with self._lock:
            state = self._states.get(build_id)
        if state is None:
            # 可能是重启后内存丢失，回退到 history
            record = history.get_record(build_id)
            if record:
                return BuildState(
                    build_id=build_id,
                    pipeline_name=record.get("pipeline", ""),
                    status=BuildStatus.SUCCESS if record.get("status") == "success" else BuildStatus.FAILED,
                    started_at=record.get("started_at", ""),
                    duration=record.get("duration", 0.0),
                )
            return None
        return state

    def list_recent(self, limit: int = 20) -> list:
        """列出最近构建（合并内存中 in-flight 与 history 落盘的）。"""
        records = history.list_records(limit=limit)
        # 内存中正在跑的也可能还没落盘，补充进去
        with self._lock:
            inflight = [
                {
                    "build_id": s.build_id,
                    "pipeline": s.pipeline_name,
                    "status": s.status.value,
                    "started_at": s.started_at,
                    "duration": s.duration,
                    "log_dir": None,
                    "steps": [],
                }
                for s in self._states.values()
                if s.status in (BuildStatus.QUEUED, BuildStatus.RUNNING)
            ]
        # 去重：history 里没有的 in-flight 才补
        known = {r["build_id"] for r in records}
        for r in inflight:
            if r["build_id"] not in known:
                records.insert(0, r)
        return records

    def subscribe_lines(self, build_id: str,
                        callback: Callable[[str, str, str], None]) -> bool:
        """订阅某次构建的行级输出。构建已结束则返回 False（无法订阅历史流）。"""
        with self._lock:
            state = self._states.get(build_id)
            if state is None or state.status not in (BuildStatus.QUEUED, BuildStatus.RUNNING):
                return False
            state.line_subs.append(callback)
            return True

    def subscribe_steps(self, build_id: str,
                        callback: Callable[[StepResult], None]) -> bool:
        """订阅某次构建的步骤完成事件。"""
        with self._lock:
            state = self._states.get(build_id)
            if state is None or state.status not in (BuildStatus.QUEUED, BuildStatus.RUNNING):
                return False
            state.step_subs.append(callback)
            return True

    # ---------- 内部：工作线程 ----------

    def _run_loop(self) -> None:
        """后台工作线程：从队列取构建任务，串行执行。"""
        while True:
            item = self._queue.get()
            if item is None:
                break  # 哨兵，用于优雅关闭（目前不调用）
            build_id, pipeline, context = item
            try:
                self._execute(build_id, pipeline, context)
            except Exception:
                # 构建异常不应让工作线程退出
                import traceback
                traceback.print_exc()
                with self._lock:
                    state = self._states.get(build_id)
                    if state:
                        state.status = BuildStatus.FAILED

    def _execute(self, build_id: str, pipeline: Pipeline, context: dict) -> None:
        """实际执行一次构建（在工作线程内调用）。"""
        with self._lock:
            state = self._states.get(build_id)
            if state is None:
                state = BuildState(build_id=build_id, pipeline_name=pipeline.name)
                self._states[build_id] = state

        # 捕获当前 state 的订阅者快照，构造回调
        def on_line(stage, step, line):
            with self._lock:
                subs = list(state.line_subs)
            for cb in subs:
                try:
                    cb(stage, step, line)
                except Exception:
                    pass

        def on_step(result: StepResult):
            with self._lock:
                subs = list(state.step_subs)
            for cb in subs:
                try:
                    cb(result)
                except Exception:
                    pass

        state.status = BuildStatus.RUNNING
        executor = Executor(build_id=build_id, on_step=on_step, on_line=on_line)
        result = executor.run(pipeline, context)

        state.result = result
        state.status = BuildStatus.SUCCESS if result.success else BuildStatus.FAILED
        state.started_at = result.started_at
        state.duration = result.duration

        # 落盘到 history
        history.save(result)


# 模块级单例：Web 层和 CLI 共用
_manager: Optional[BuildManager] = None
_manager_lock = threading.Lock()


def get_manager() -> BuildManager:
    """获取全局 BuildManager 单例。"""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = BuildManager()
    return _manager
