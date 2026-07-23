"""history 模块测试。

第一性原理：历史记录的本质是「存得进、读得出、查得到」。
"""

import os
import tempfile

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
