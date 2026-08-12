"""流水线读写路由：GET/PUT /api/pipelines/{name}。

第一性原理：可视化编辑器需要「读出 YAML 结构 -> 表单编辑 -> 写回 YAML」。
这两个端点是编辑器的数据后端。
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from ...config import load_pipeline, dump_pipeline, ConfigError
from ..schemas import PipelineSchema

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("/{name}", response_model=PipelineSchema)
def get_pipeline(name: str):
    """读取一条流水线配置，返回结构化 JSON（供编辑器加载）。

    name 即文件名（如 jenpy.yaml 或 my-pipeline.yaml），相对当前工作目录。
    """
    # 防路径穿越：只取文件名部分
    safe_name = os.path.basename(name)
    if safe_name != name:
        raise HTTPException(status_code=400, detail="文件名不允许包含路径分隔符")
    if not os.path.isfile(safe_name):
        raise HTTPException(status_code=404, detail=f"配置文件不存在: {safe_name}")
    try:
        pipeline = load_pipeline(safe_name)
    except ConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _pipeline_to_schema(pipeline)


@router.put("/{name}", response_model=PipelineSchema)
def put_pipeline(name: str, body: PipelineSchema):
    """保存流水线配置（结构化 JSON -> dump_pipeline -> 写回 YAML）。"""
    safe_name = os.path.basename(name)
    if safe_name != name:
        raise HTTPException(status_code=400, detail="文件名不允许包含路径分隔符")

    pipeline = _schema_to_pipeline(body)
    yaml_text = dump_pipeline(pipeline)
    try:
        with open(safe_name, "w", encoding="utf-8") as f:
            f.write(yaml_text)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"写入失败: {e}")

    return _pipeline_to_schema(pipeline)


def _pipeline_to_schema(p) -> PipelineSchema:
    """config.Pipeline -> PipelineSchema。"""
    from ..schemas import StageSchema, StepSchema, DeploySchema
    stages = []
    for st in p.stages:
        steps = []
        for s in st.steps:
            deploy = None
            if s.deploy is not None:
                deploy = DeploySchema(**s.deploy)
            steps.append(StepSchema(
                name=s.name, run=s.run, timeout=s.timeout, env=s.env,
                continue_on_error=s.continue_on_error, deploy=deploy,
            ))
        stages.append(StageSchema(name=st.name, when=st.when, steps=steps))
    return PipelineSchema(name=p.name, workspace=p.workspace, env=p.env, stages=stages)


def _schema_to_pipeline(body: PipelineSchema):
    """PipelineSchema -> config.Pipeline。"""
    from ...pipeline import Pipeline, Stage, Step
    stages = []
    for st in body.stages:
        steps = []
        for s in st.steps:
            deploy = dict(s.deploy) if s.deploy is not None else None
            steps.append(Step(
                name=s.name, run=s.run, timeout=s.timeout, env=dict(s.env),
                continue_on_error=s.continue_on_error, deploy=deploy,
            ))
        stages.append(Stage(name=st.name, when=st.when, steps=steps))
    return Pipeline(name=body.name, workspace=body.workspace, env=dict(body.env), stages=stages)
