"""history 模块测试。

第一性原理：历史记录的本质是「存得进、读得出、查得到」。
"""

import os
import tempfile
import threading

from jenpy.executor import BuildResult, StepResult
from jenpy import history


def _make_result(success=True) -> BuildResult:
    return BuildResult(
        pipeline_name="test-pipeline",
        success=success,
        steps=[
            StepResult(stage_name="s1", step_name="step1",
                       success=True, returncode=0, duration=0.1),
        ],
        duration=0.5,
        started_at="2026-07-23T12:00:00",
    )


def _isolated_history(monkeypatch, tmp_path):
    """把 history 的存储目录重定向到临时目录，避免污染真实数据。"""
    hist_dir = str(tmp_path / ".jenpy")
    hist_file = os.path.join(hist_dir, "history.json")
    monkeypatch.setattr(history, "HISTORY_DIR", hist_dir)
    monkeypatch.setattr(history, "HISTORY_FILE", hist_file)
    return hist_file


def test_save_and_list(tmp_path, monkeypatch):
    """存入后应能列出。"""
    _isolated_history(monkeypatch, tmp_path)
    history.save(_make_result())
    records = history.list_records()
    assert len(records) == 1
    assert records[0]["pipeline"] == "test-pipeline"
    assert records[0]["status"] == "success"


def test_get_by_build_id(tmp_path, monkeypatch):
    """按 build_id 应能查到对应记录。"""
    _isolated_history(monkeypatch, tmp_path)
    build_id = history.save(_make_result())
    record = history.get_record(build_id)
    assert record is not None
    assert record["build_id"] == build_id


def test_get_nonexistent_returns_none(tmp_path, monkeypatch):
    """查不存在的 build_id 应返回 None。"""
    _isolated_history(monkeypatch, tmp_path)
    assert history.get_record("no-such-id") is None


def test_status_reflects_failure(tmp_path, monkeypatch):
    """失败的构建应记录为 failed。"""
    _isolated_history(monkeypatch, tmp_path)
    history.save(_make_result(success=False))
    records = history.list_records()
    assert records[0]["status"] == "failed"


# ---------- P0 修复：并发安全 ----------

def test_build_id_has_random_suffix():
    """build_id 应带随机后缀，同一秒内多次调用应唯一。"""
    ids = {history.new_build_id() for _ in range(20)}
    assert len(ids) == 20  # 20 次调用得到 20 个不同 ID
    # 格式应为 YYYYMMDD-HHMMSS-xxxx
    import re
    for bid in ids:
        assert re.match(r"^\d{8}-\d{6}-[a-z0-9]{4}$", bid), bid


def test_concurrent_saves_no_data_loss(tmp_path, monkeypatch):
    """多个线程同时 save，不应丢失记录（原子写 + 锁的保护效果）。"""
    _isolated_history(monkeypatch, tmp_path)

    n_threads = 10
    per_thread = 5
    threads = []
    errors = []

    def writer():
        try:
            for _ in range(per_thread):
                history.save(_make_result())
        except Exception as e:
            errors.append(e)

    for _ in range(n_threads):
        threads.append(threading.Thread(target=writer))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"线程内异常: {errors}"
    # list_records 默认 limit=20，这里显式取全部（50 < MAX_RECORDS=100）
    records = history.list_records(limit=n_threads * per_thread)
    # 所有记录都应存在（不被覆盖）
    assert len(records) == n_threads * per_thread
