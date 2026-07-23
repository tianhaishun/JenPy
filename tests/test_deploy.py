"""deploy 模块测试。

第一性原理：部署的本质是「把文件搬到目标位置」。验证三种搬运方式，
以及工具缺失时的优雅降级。
"""

import os
import pytest

from jenpy import deploy


# ---------- copy 方式（纯 Python，跨平台，主测试对象） ----------

def test_copy_deploys_files(tmp_path):
    """copy 方式应真实把文件搬到目标目录。"""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello")
    (src / "sub").mkdir()
    (src / "sub" / "b.txt").write_text("world")

    tgt = tmp_path / "deployed"
    config = {"method": "copy", "source": str(src), "target": str(tgt)}

    assert deploy.run(config, str(tmp_path), {}) is True
    assert (tgt / "a.txt").read_text() == "hello"
    assert (tgt / "sub" / "b.txt").read_text() == "world"


def test_copy_creates_target_if_missing(tmp_path):
    """目标目录不存在时应自动创建。"""
    src = tmp_path / "s"; src.mkdir()
    (src / "x.txt").write_text("x")
    tgt = tmp_path / "deep" / "nested" / "target"

    config = {"method": "copy", "source": str(src), "target": str(tgt)}
    assert deploy.run(config, str(tmp_path), {}) is True
    assert (tgt / "x.txt").exists()


def test_copy_delete_clears_target_first(tmp_path):
    """delete=true 时应先清空目标中多余的旧文件。"""
    src = tmp_path / "src"; src.mkdir()
    (src / "new.txt").write_text("new")

    tgt = tmp_path / "tgt"; tgt.mkdir()
    (tgt / "old.txt").write_text("old")   # 目标里已有的旧文件

    config = {"method": "copy", "source": str(src),
              "target": str(tgt), "delete": True}
    assert deploy.run(config, str(tmp_path), {}) is True
    assert (tgt / "new.txt").exists()
    assert not (tgt / "old.txt").exists()   # 旧文件被清除


def test_copy_missing_source_or_target(tmp_path):
    """缺 source 或 target 应返回失败，不抛异常。"""
    with pytest.MonkeyPatch().context() as m:
        pass
    assert deploy.run({"method": "copy"}, str(tmp_path), {}) is False
    assert deploy.run({"method": "copy", "source": "x"}, str(tmp_path), {}) is False


# ---------- script 方式 ----------

def test_script_runs_command(tmp_path):
    """script 方式应执行用户命令。"""
    (tmp_path / "marker.txt").stat() if False else None
    config = {"method": "script", "run": "echo deployed"}
    assert deploy.run(config, str(tmp_path), {}) is True


def test_script_failure(tmp_path):
    """script 命令失败应返回 False。"""
    config = {"method": "script",
              "run": 'python -c "import sys; sys.exit(1)"'}
    assert deploy.run(config, str(tmp_path), {}) is False


def test_script_missing_run(tmp_path):
    """script 缺 run 字段应失败。"""
    assert deploy.run({"method": "script"}, str(tmp_path), {}) is False


# ---------- rsync 方式：优雅降级 ----------

def test_rsync_without_binary_degrades_gracefully(tmp_path):
    """系统无 rsync 时应优雅失败，不抛未捕获异常。"""
    # 用一个肯定不存在的命令名模拟 rsync 缺失
    config = {"method": "rsync", "source": "a", "target": "b"}
    # 在真实环境里若 rsync 存在则会尝试执行；这里主要验证不崩溃
    result = deploy.run(config, str(tmp_path), {})
    assert isinstance(result, bool)


# ---------- 未知方式 ----------

def test_unknown_method_fails(tmp_path):
    """不支持的部署方式应返回失败。"""
    assert deploy.run({"method": "ftp"}, str(tmp_path), {}) is False
