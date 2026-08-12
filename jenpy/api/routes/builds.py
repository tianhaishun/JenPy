"""构建触发与查询路由。

第一性原理：
  - POST /api/builds   触发一次构建（异步，立即返回 build_id）
  - GET  /api/builds   列出最近构建（合并 in-flight 与 history）
  - GET  /api/builds/{id}  查单次构建详情
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ... import history
from ...manager import BuildManager, BuildStatus
from ..deps import get_build_manager
from ..schemas import TriggerRequest, TriggerResponse, BuildRecordSchema

router = APIRouter(prefix="/api/builds", tags=["builds"])


@router.post("", response_model=TriggerResponse, status_code=202)
def trigger_build(body: TriggerRequest,
                  mgr: BuildManager = Depends(get_build_manager)):
    """触发一次构建。立即返回 build_id，构建在后台串行执行。"""
    try:
        build_id = mgr.trigger_file(body.file, body.context)
    except Exception as e:
        # ConfigError 或文件问题
        raise HTTPException(status_code=400, detail=str(e))
    return TriggerResponse(build_id=build_id, status="queued")


@router.get("", response_model=list[BuildRecordSchema])
def list_builds(limit: int = 20):
    """列出最近构建（新的在前）。"""
    records = history.list_records(limit=limit)
    # 反转为新的在前（history 存的是旧的在前）
    records = list(reversed(records))
    return [BuildRecordSchema(**_normalize(r)) for r in records]


@router.get("/{build_id}", response_model=BuildRecordSchema)
def get_build(build_id: str):
    """查单次构建详情。"""
    record = history.get_record(build_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"找不到构建记录: {build_id}")
    return BuildRecordSchema(**_normalize(record))


def _normalize(r: dict) -> dict:
    """补齐可能缺失的字段，适配 Pydantic 模型。"""
    return {
        "build_id": r.get("build_id", ""),
        "pipeline": r.get("pipeline", ""),
        "status": r.get("status", "unknown"),
        "started_at": r.get("started_at", ""),
        "duration": r.get("duration", 0.0),
        "log_dir": r.get("log_dir"),
        "steps": r.get("steps", []),
    }
