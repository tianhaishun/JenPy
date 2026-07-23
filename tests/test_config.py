"""config 模块测试。

第一性原理：测试要验证「YAML 能正确翻译成数据结构」这件本质之事。
用真实的 YAML 字符串作为输入，断言解析出的结构符合预期。
"""

import os
import tempfile
import pytest

from jenpy.config import load_pipeline, ConfigError


def _write_yaml(content: str) -> str:
    """把 YAML 内容写入临时文件，返回路径。"""
    fd, path = tempfile.mkstemp(suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_load_basic_pipeline():
    """基本结构：名称 + 一个阶段 + 一个步骤。"""
    path = _write_yaml("""
name: my-app
stages:
  - name: build
    steps:
      - run: echo hello
""")
    p = load_pipeline(path)
    assert p.name == "my-app"
    assert len(p.stages) == 1
    assert p.stages[0].name == "build"
    assert p.stages[0].steps[0].run == "echo hello"
    os.unlink(path)


def test_step_shorthand_string():
    """步骤的简写形式：直接写字符串。"""
    path = _write_yaml("""
name: app
stages:
  - name: s1
    steps:
      - echo done
""")
    p = load_pipeline(path)
    assert p.stages[0].steps[0].run == "echo done"


def test_step_full_fields():
    """步骤的完整字段：name/timeout/env/continue_on_error。"""
    path = _write_yaml("""
name: app
stages:
  - name: s1
    steps:
      - name: my step
        run: pytest
        timeout: 120
        env:
          DEBUG: "1"
        continue_on_error: true
""")
    p = load_pipeline(path)
    step = p.stages[0].steps[0]
    assert step.name == "my step"
    assert step.timeout == 120
    assert step.env == {"DEBUG": "1"}
    assert step.continue_on_error is True


def test_deploy_step():
    """部署步骤：含 deploy 字段而非 run。"""
    path = _write_yaml("""
name: app
stages:
  - name: deploy
    steps:
      - deploy:
          method: rsync
          source: ./dist/
          target: user@host:/path/
""")
    p = load_pipeline(path)
    step = p.stages[0].steps[0]
    assert step.deploy["method"] == "rsync"
    assert step.run is None


def test_when_condition():
    """阶段条件表达式。"""
    path = _write_yaml("""
name: app
stages:
  - name: prod
    when: branch == 'main'
    steps:
      - run: echo deploy
""")
    p = load_pipeline(path)
    assert p.stages[0].when == "branch == 'main'"


def test_global_env():
    """顶层环境变量。"""
    path = _write_yaml("""
name: app
env:
  FOO: bar
  NUM: "42"
stages:
  - name: s1
    steps:
      - run: echo $FOO
""")
    p = load_pipeline(path)
    assert p.env == {"FOO": "bar", "NUM": "42"}


def test_missing_file_raises():
    """文件不存在应报错。"""
    with pytest.raises(ConfigError):
        load_pipeline("/nonexistent/path/to/file.yaml")


def test_step_without_run_or_deploy_raises():
    """步骤既无 run 也无 deploy 应报错。"""
    path = _write_yaml("""
name: app
stages:
  - name: s1
    steps:
      - name: empty step
""")
    with pytest.raises(ConfigError):
        load_pipeline(path)
    os.unlink(path)
