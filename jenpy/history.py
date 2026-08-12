"""构建历史记录。

第一性原理：历史记录就是「把每次执行的关键事实存成可回溯的数据」。
不需要数据库——一个 JSON 文件就足够持久化，足够查询。
本模块只管「存」和「读」，不关心执行逻辑。
"""

from __future__ import annotations
import json
import os
import random
import string
import threading
import time
from typing import Optional

from .executor import BuildResult, StepResult

# 所有运行时产物的根目录（被 .gitignore 忽略）
HISTORY_DIR = ".jenpy"
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")
# 保留最近多少条记录，防止文件无限增长
MAX_RECORDS = 100

# 保护 load-modify-write 的进程内锁：防止并发 save 互相覆盖丢记录。
# 跨进程并发仍需外部协调（同一项目不要起多个 jenpy 进程同时写）。
_WRITE_LOCK = threading.Lock()


def new_build_id() -> str:
    """生成构建 ID：时间戳 + 4 位随机后缀，保证唯一且可读。

    第一性原理：秒级时间戳便于人读，但同秒触发的多次构建会冲突
    （日志目录互相覆盖）。加随机后缀以概率消除冲突。
    """
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def save(result: BuildResult) -> str:
    """把一次构建结果存入历史，返回 build_id。

    第一性原理：记录要能回答三个问题——何时、是什么流水线、成不成功。
    步骤明细 + 日志目录是附加信息，便于事后排查。
    """
    # 优先使用 executor 分配的 build_id，保证与日志目录一致
    build_id = result.build_id or new_build_id()

    record = {
        "build_id": build_id,
        "pipeline": result.pipeline_name,
        "status": "success" if result.success else "failed",
        "started_at": result.started_at,
        "duration": round(result.duration, 2),
        "log_dir": result.log_dir,
        "steps": [
            {
                "stage": s.stage_name,
                "step": s.step_name,
                "success": s.success,
                "duration": round(s.duration, 2),
                "log_file": s.log_file,
            }
            for s in result.steps
        ],
    }

    # 原子写：先写临时文件，再 os.replace 原子替换。
    # 加锁串行化 load-modify-write，避免并发 save 互相覆盖丢记录。
    with _WRITE_LOCK:
        records = _load_all()
        records.append(record)
        # 只保留最近 MAX_RECORDS 条
        records = records[-MAX_RECORDS:]

        os.makedirs(HISTORY_DIR, exist_ok=True)
        tmp_path = HISTORY_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        # os.replace 在同目录下是原子的（POSIX 保证；Windows NTFS 也是）
        os.replace(tmp_path, HISTORY_FILE)

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
