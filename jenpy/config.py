"""加载并解析流水线配置文件。

第一性原理：配置文件只是「人能方便编辑的、描述流水线结构的文本」。
本模块的唯一职责是把 YAML 文本翻译成 Pipeline 对象，并做最基本的校验。
不做任何执行逻辑——执行是 executor 的事。
"""

from __future__ import annotations
import os
from typing import Any

import yaml

from .pipeline import Pipeline, Stage, Step


class ConfigError(Exception):
    """配置文件格式错误。"""


def load_pipeline(path: str) -> Pipeline:
    """从 YAML 文件加载一条流水线。

    Args:
        path: YAML 配置文件路径

    Returns:
        解析后的 Pipeline 对象

    Raises:
        ConfigError: 文件不存在或格式不符合预期
    """
    if not os.path.isfile(path):
        raise ConfigError(f"配置文件不存在: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError("配置文件顶层必须是字典（mapping）")

    return _build_pipeline(raw)


def dump_pipeline(pipeline: Pipeline) -> str:
    """把 Pipeline 对象序列化回 YAML 文本。

    第一性原理：可视化编辑器改完结构后，需要写回 YAML 文件。
    dataclass -> dict -> yaml.safe_dump，与 load_pipeline 互为逆操作。
    仅输出非默认字段，保持输出简洁。
    """
    def step_to_dict(s: Step) -> dict:
        d = {}
        if s.name:
            d["name"] = s.name
        if s.run is not None:
            d["run"] = s.run
        if s.timeout is not None:
            d["timeout"] = s.timeout
        if s.env:
            d["env"] = s.env
        if s.continue_on_error:
            d["continue_on_error"] = True
        if s.deploy is not None:
            d["deploy"] = s.deploy
        return d

    def stage_to_dict(st: Stage) -> dict:
        d: dict = {"name": st.name}
        if st.when:
            d["when"] = st.when
        d["steps"] = [step_to_dict(s) for s in st.steps]
        return d

    doc: dict = {"name": pipeline.name}
    if pipeline.workspace and pipeline.workspace != ".":
        doc["workspace"] = pipeline.workspace
    if pipeline.env:
        doc["env"] = pipeline.env
    doc["stages"] = [stage_to_dict(st) for st in pipeline.stages]
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _build_pipeline(raw: dict) -> Pipeline:
    """把原始字典结构转成 Pipeline 对象。"""
    name = raw.get("name") or "unnamed-pipeline"

    # 顶层环境变量
    env = raw.get("env") or {}
    if not isinstance(env, dict):
        raise ConfigError("env 必须是字典")

    workspace = raw.get("workspace", ".")

    raw_stages = raw.get("stages") or []
    if not isinstance(raw_stages, list):
        raise ConfigError("stages 必须是列表")

    stages = [_build_stage(s, i) for i, s in enumerate(raw_stages)]

    return Pipeline(name=name, stages=stages, workspace=workspace, env=env)


def _build_stage(raw: Any, index: int) -> Stage:
    """把单个 stage 字典转成 Stage 对象。"""
    if not isinstance(raw, dict):
        raise ConfigError(f"第 {index + 1} 个 stage 必须是字典")

    name = raw.get("name") or f"stage-{index + 1}"
    raw_steps = raw.get("steps") or []
    if not isinstance(raw_steps, list):
        raise ConfigError(f"stage '{name}' 的 steps 必须是列表")

    steps = [_build_step(s, i, name) for i, s in enumerate(raw_steps)]

    return Stage(name=name, steps=steps, when=raw.get("when"))


def _build_step(raw: Any, index: int, stage_name: str) -> Step:
    """把单个 step 字典转成 Step 对象。

    第一性原理：一个 step 要么是「执行命令」(run)，要么是「部署」(deploy)。
    二者至少有一个，否则这个步骤没有意义。
    """
    if isinstance(raw, str):
        # 简写形式：直接写命令字符串
        return Step(name=f"step-{index + 1}", run=raw)

    if not isinstance(raw, dict):
        raise ConfigError(f"stage '{stage_name}' 的第 {index + 1} 个 step 格式无效")

    has_run = "run" in raw and raw["run"] is not None
    has_deploy = "deploy" in raw and raw["deploy"] is not None
    if not has_run and not has_deploy:
        raise ConfigError(
            f"stage '{stage_name}' 的第 {index + 1} 个 step 必须包含 run 或 deploy"
        )

    return Step(
        name=raw.get("name") or f"step-{index + 1}",
        run=raw.get("run"),
        timeout=raw.get("timeout"),
        env=raw.get("env") or {},
        continue_on_error=bool(raw.get("continue_on_error", False)),
        deploy=raw.get("deploy"),
    )
