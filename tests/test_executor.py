"""executor 模块测试。

第一性原理：执行器的本质是「跑命令、拿结果」。测试用真实命令验证：
成功/失败判定、超时、continue_on_error、条件执行。
"""

import pytest

from jenpy.pipeline import Pipeline, Stage, Step
from jenpy.executor import Executor


def _make_pipeline(stages, name="test") -> Pipeline:
    return Pipeline(name=name, stages=stages)


def test_successful_command():
    """成功的命令，整体结果应为成功。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[Step(name="ok", run="echo hello")]),
    ])
    result = Executor().run(pipeline)
    assert result.success is True
    assert result.steps[0].success is True
    assert result.steps[0].returncode == 0


def test_failed_command_stops_pipeline():
    """失败的命令（未设 continue_on_error）应中断流水线。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[
            Step(name="fail", run="exit 1"),
        ]),
        Stage(name="s2", steps=[
            Step(name="never", run="echo nope"),
        ]),
    ])
    result = Executor().run(pipeline)
    assert result.success is False
    assert len(result.steps) == 1  # 第二阶段未执行


def test_continue_on_error():
    """设了 continue_on_error 的失败步骤不阻断后续。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[
            Step(name="fail", run="exit 1", continue_on_error=True),
            Step(name="next", run="echo ok"),
        ]),
    ])
    result = Executor().run(pipeline)
    assert result.success is True  # 整体仍成功
    assert len(result.steps) == 2
    assert result.steps[0].success is False
    assert result.steps[1].success is True


def test_timeout():
    """超时应被捕获并标记失败。

    用 Python 触发长耗时，避免依赖平台相关的 sleep 命令。
    """
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[
            Step(name="slow", run="python -c \"import time; time.sleep(10)\"",
                 timeout=1),
        ]),
    ])
    result = Executor(build_id="test-timeout").run(pipeline)
    assert result.success is False
    assert result.steps[0].success is False


def test_when_condition_true():
    """when 条件为真时阶段执行。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[Step(run="echo first")]),
        Stage(name="s2", when="branch == 'main'",
              steps=[Step(run="echo second")]),
    ])
    result = Executor().run(pipeline, context={"branch": "main"})
    assert result.success is True
    assert len(result.steps) == 2


def test_when_condition_false():
    """when 条件为假时阶段被跳过。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[Step(run="echo first")]),
        Stage(name="s2", when="branch == 'main'",
              steps=[Step(run="echo second")]),
    ])
    result = Executor().run(pipeline, context={"branch": "dev"})
    assert result.success is True
    assert len(result.steps) == 1  # 第二阶段被跳过


def test_template_variable_substitution():
    """{{ var }} 模板变量应被替换。"""
    pipeline = _make_pipeline([
        Stage(name="s1", steps=[
            Step(name="greet", run="echo {{ who }}"),
        ]),
    ])
    result = Executor().run(pipeline, context={"who": "world"})
    assert result.success is True
