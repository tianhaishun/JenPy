"""构建历史记录。

第一性原理：历史记录就是「把每次执行的关键事实存成可回溯的数据」。
不需要数据库——一个 JSON 文件就足够持久化，足够查询。
本模块只管「存」和「读」，不关心执行逻辑。
"""

from __future__ import annotations
import json
import os
import time
from typing import Optional

from .executor import BuildResult, StepResult

# 所有运行时产物的根目录（被 .gitignore 忽略）
HISTORY_DIR = ".jenpy"
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")
# 保留最近多少条记录，防止文件无限增长
MAX_RECORDS = 100


def new_build_id() -> str:
    """生成构建 ID：时间戳，保证单调递增且可读。"""
    return time.strftime("%Y%m%d-%H%M%S")


def save(result: BuildResult) -> str:
    """把一次构建结果存入历史，返回 build_id。

    第一性原理：记录要能回答三个问题——何时、是什么流水线、成不成功。
    步骤明细是附加信息，便于事后排查。
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    build_id = new_build_id()

    record = {
        "build_id": build_id,
        "pipeline": result.pipeline_name,
        "status": "success" if result.success else "failed",
        "started_at": result.started_at,
        "duration": round(result.duration, 2),
        "steps": [
            {
                "stage": s.stage_name,
                "step": s.step_name,
                "success": s.success,
                "duration": round(s.duration, 2),
            }
            for s in result.steps
        ],
    }

    records = _load_all()
    records.append(record)
    # 只保留最近 MAX_RECORDS 条
    records = records[-MAX_RECORDS:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return build_id


def list_records(limit: int = 20) -> list:
    """返回最近的若干条历史记录（新的在后）。"""
    records = _load_all()
    return records[-limit:]


def get_record(build_id: str) -> Optional[dict]:
    """按 build_id 查找单条记录。"""
    for r in _load_all():
        if r.get("build_id") == build_id:
            return r
    return None


def _load_all() -> list:
    """读取全部历史记录。文件不存在时返回空列表。"""
    if not os.path.isfile(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []
