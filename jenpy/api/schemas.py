"""Pydantic 请求/响应模型。

第一性原理：API 契约要显式、可验证。这些模型同时是 OpenAPI 文档的来源
（FastAPI 自动生成 /docs），前端可据此生成客户端。
与 pipeline.py 的 dataclass 对应，但用 Pydantic 做校验。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DeploySchema(BaseModel):
    """部署配置。"""
    method: str = Field("script", description="copy | rsync | script")
    source: Optional[str] = None
    target: Optional[str] = None
    delete: bool = False
    run: Optional[str] = None

    model_config = {"extra": "allow"}


class StepSchema(BaseModel):
    """单个步骤。"""
    name: str = ""
    run: Optional[str] = None
    timeout: Optional[int] = None
    env: dict[str, str] = Field(default_factory=dict)
    continue_on_error: bool = False
    deploy: Optional[DeploySchema] = None


class StageSchema(BaseModel):
    """单个阶段。"""
    name: str
    when: Optional[str] = None
    steps: list[StepSchema] = Field(default_factory=list)


class PipelineSchema(BaseModel):
    """整条流水线。"""
    name: str
    workspace: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    stages: list[StageSchema] = Field(default_factory=list)


class TriggerRequest(BaseModel):
    """触发构建的请求体。"""
    file: str = Field("jenpy.yaml", description="流水线配置文件路径")
    context: dict[str, Any] = Field(default_factory=dict, description="模板/条件变量")


class TriggerResponse(BaseModel):
    """触发构建的响应。"""
    build_id: str
    status: str = "queued"


class StepRecordSchema(BaseModel):
    """历史记录中的单个步骤。"""
    stage: str
    step: str
    success: bool
    duration: float
    log_file: Optional[str] = None


class BuildRecordSchema(BaseModel):
    """单条构建记录。"""
    build_id: str
    pipeline: str = ""
    status: str
    started_at: str = ""
    duration: float = 0.0
    log_dir: Optional[str] = None
    steps: list[StepRecordSchema] = Field(default_factory=list)
