"""日志读取与实时流路由。

第一性原理：
  - GET /api/builds/{id}/logs/{stage}/{step}  读某步已落盘的完整日志
  - GET /api/builds/{id}/stream  SSE 实时推送行级输出（供浏览器 EventSource）

SSE 桥接：BuildManager 的 on_line 回调是同步的（在工作线程触发），
SSE 需要异步生成器。用线程安全的 queue.Queue 桥接——回调把行 put 进队列，
异步生成器从队列取并 yield 为 SSE 事件。
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse

from ... import history
from ...manager import BuildManager, BuildStatus
from ..deps import get_build_manager

router = APIRouter(prefix="/api/builds", tags=["logs"])


@router.get("/{build_id}/logs/{stage}/{step}")
def get_step_log(build_id: str, stage: str, step: str):
    """读取某步骤的完整日志文件。"""
    record = history.get_record(build_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"找不到构建记录: {build_id}")

    # 在记录的 steps 里匹配 stage/step，取其 log_file
    for s in record.get("steps", []):
        if s.get("stage") == stage and s.get("step") == step:
            log_file = s.get("log_file")
            if not log_file or not os.path.isfile(log_file):
                raise HTTPException(status_code=404, detail="日志文件不存在")
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    return PlainTextResponse(f.read())
            except OSError as e:
                raise HTTPException(status_code=500, detail=f"读取日志失败: {e}")

    raise HTTPException(status_code=404, detail=f"找不到步骤: {stage}/{step}")


@router.get("/{build_id}/stream")
def stream_build(build_id: str,
                 mgr: BuildManager = Depends(get_build_manager)):
    """SSE 端点：实时推送构建的行级输出与步骤完成事件。

    事件类型：
      - event: line      data: {"stage":..,"step":..,"line":..}
      - event: step      data: {StepResult 字段}
      - event: done      data: {"status":..,"success":..}
    若构建已结束（无法订阅实时流），推送已有日志后发 done。
    """
    state = mgr.get_state(build_id)

    # 若构建仍在队列或运行中，订阅实时回调
    is_live = state is not None and state.status in (BuildStatus.QUEUED, BuildStatus.RUNNING)

    line_q: "queue.Queue[Optional[dict]]" = queue.Queue()
    step_q: "queue.Queue[Optional[dict]]" = queue.Queue()

    def on_line_cb(stage, step, line):
        line_q.put({"stage": stage, "step": step, "line": line})

    def on_step_cb(result):
        step_q.put({
            "stage": result.stage_name,
            "step": result.step_name,
            "success": result.success,
            "returncode": result.returncode,
            "duration": round(result.duration, 2),
        })

    subscribed_lines = False
    subscribed_steps = False
    if is_live:
        subscribed_lines = mgr.subscribe_lines(build_id, on_line_cb)
        subscribed_steps = mgr.subscribe_steps(build_id, on_step_cb)

    async def event_generator():
        """异步生成 SSE 事件流。"""
        loop = asyncio.get_event_loop()

        if is_live and subscribed_lines:
            # 实时模式：轮询队列，直到构建结束
            import time
            while True:
                cur = mgr.get_state(build_id)
                finished = cur is not None and cur.status not in (BuildStatus.QUEUED, BuildStatus.RUNNING)
                # 排空行队列
                drained = False
                while True:
                    try:
                        item = line_q.get_nowait()
                    except queue.Empty:
                        break
                    if item is None:
                        drained = True
                        break
                    yield _sse("line", item)
                # 排空步骤队列
                while True:
                    try:
                        item = step_q.get_nowait()
                    except queue.Empty:
                        break
                    if item is None:
                        break
                    yield _sse("step", item)
                if finished:
                    break
                await asyncio.sleep(0.1)

            final = mgr.get_state(build_id)
            yield _sse("done", {
                "status": final.status.value if final else "unknown",
                "success": final.result.success if final and final.result else False,
            })
        else:
            # 回放模式：构建已结束，从历史记录读日志逐行推送
            record = history.get_record(build_id)
            if record:
                for s in record.get("steps", []):
                    log_file = s.get("log_file")
                    if log_file and os.path.isfile(log_file):
                        try:
                            with open(log_file, "r", encoding="utf-8") as f:
                                for line in f:
                                    yield _sse("line", {
                                        "stage": s.get("stage", ""),
                                        "step": s.get("step", ""),
                                        "line": line,
                                    })
                        except OSError:
                            pass
                    yield _sse("step", {
                        "stage": s.get("stage", ""),
                        "step": s.get("step", ""),
                        "success": s.get("success", False),
                        "returncode": 0 if s.get("success") else 1,
                        "duration": s.get("duration", 0.0),
                    })
                yield _sse("done", {
                    "status": record.get("status", "unknown"),
                    "success": record.get("status") == "success",
                })
            else:
                yield _sse("done", {"status": "unknown", "success": False})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    """格式化一个 SSE 事件帧。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
