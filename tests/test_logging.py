"""日志落盘测试。

第一性原理：日志的本质是「命令输出被完整保存，事后能查到」。
验证：构建后存在日志文件、内容包含命令的真实输出。
"""

import os

from jenpy.pipeline import Pipeline, Stage, Step
from jenpy.executor import Executor


def test_log_file_created(tmp_path, monkeypatch):
    """执行后应生成日志文件。"""
    monkeypatch.chdir(tmp_path)
    pipeline = Pipeline(name="t", stages=[
        Stage(name="s1", steps=[Step(name="hi", run="echo hello-world")]),
    ])
    result = Executor(build_id="test-123").run(pipeline)

    assert result.build_id == "test-123"
    assert result.log_dir is not None
    assert os.path.isdir(result.log_dir)

    step = result.steps[0]
    assert step.log_file is not None
    assert os.path.isfile(step.log_file)


def test_log_contains_real_output(tmp_path, monkeypatch):
    """日志文件应包含命令的真实输出文本。"""
    monkeypatch.chdir(tmp_path)
    pipeline = Pipeline(name="t", stages=[
        Stage(name="s1", steps=[Step(name="greet", run="echo UNIQUE_MARKER_42")]),
    ])
    result = Executor(build_id="test-456").run(pipeline)

    with open(result.steps[0].log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "UNIQUE_MARKER_42" in content


def test_failed_command_output_logged(tmp_path, monkeypatch):
    """失败命令的输出也应被记录。

    用 Python 以非零码退出并打印标记，避免依赖平台 shell 的命令分隔符语义。
    """
    monkeypatch.chdir(tmp_path)
    pipeline = Pipeline(name="t", stages=[
        Stage(name="s1", steps=[
            Step(name="bad",
                 run="python -c \"print('ERR_MARKER'); import sys; sys.exit(1)\""),
        ]),
    ])
    result = Executor(build_id="test-789").run(pipeline)

    assert result.steps[0].success is False
    with open(result.steps[0].log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "ERR_MARKER" in content


def test_multiple_steps_separate_logs(tmp_path, monkeypatch):
    """每个步骤应有独立的日志文件。"""
    monkeypatch.chdir(tmp_path)
    pipeline = Pipeline(name="t", stages=[
        Stage(name="s1", steps=[
            Step(name="first", run="echo one"),
            Step(name="second", run="echo two"),
        ]),
    ])
    result = Executor(build_id="test-mult").run(pipeline)

    log_files = [s.log_file for s in result.steps]
    assert len(set(log_files)) == 2  # 两个不同的文件
    for lf in log_files:
        assert os.path.isfile(lf)
