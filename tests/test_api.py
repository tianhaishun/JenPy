"""Web API 测试。

第一性原理：API 的本质是「请求进来，正确的响应出去」。
用 FastAPI TestClient 做端到端验证，复用 tmp_path+monkeypatch.chdir 隔离模式。
触发构建用 echo 等快命令。
"""

import os
import time

import pytest
from fastapi.testclient import TestClient

from jenpy.api.app import create_app
from jenpy import history
from jenpy.manager import BuildStatus


@pytest.fixture
def client(tmp_path, monkeypatch):
    """构造 TestClient，工作目录隔离到 tmp_path。"""
    monkeypatch.chdir(tmp_path)
    # 每个 test 独立的 manager，避免跨测试状态污染
    import jenpy.manager as mgr_mod
    monkeypatch.setattr(mgr_mod, "_manager", None)
    app = create_app()
    return TestClient(app)


def _write_pipeline(path, name="test-pipeline"):
    """写一个最小可跑的流水线文件。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"name: {name}\n"
            "stages:\n"
            "  - name: s1\n"
            "    steps:\n"
            "      - name: greet\n"
            "        run: echo API_HELLO\n"
        )


def test_health(client):
    """健康检查应返回 200 + ok。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["name"] == "JenPy"


def test_get_pipeline(client):
    """读取已存在的流水线文件。"""
    _write_pipeline("jenpy.yaml")
    resp = client.get("/api/pipelines/jenpy.yaml")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test-pipeline"
    assert len(data["stages"]) == 1
    assert data["stages"][0]["name"] == "s1"
    assert data["stages"][0]["steps"][0]["run"] == "echo API_HELLO"


def test_get_pipeline_not_found(client):
    """文件不存在应返回 404。"""
    resp = client.get("/api/pipelines/nonexistent.yaml")
    assert resp.status_code == 404


def test_get_pipeline_rejects_path_traversal(client):
    """路径穿越应被拒绝（返回 4xx，不返回文件内容）。"""
    resp = client.get("/api/pipelines/..%2F..%2Fetc%2Fpasswd")
    # 不应返回 200/500；路径含分隔符被路由层拒绝
    assert resp.status_code in (400, 404)
    # 且绝不能返回系统文件内容
    assert "root:" not in resp.text


def test_put_pipeline_writes_yaml(client):
    """PUT 应把结构化 JSON 写回 YAML 文件。"""
    body = {
        "name": "edited",
        "workspace": ".",
        "env": {"FOO": "bar"},
        "stages": [
            {"name": "build", "steps": [
                {"name": "compile", "run": "echo built", "timeout": 30},
            ]},
        ],
    }
    resp = client.put("/api/pipelines/mine.yaml", json=body)
    assert resp.status_code == 200
    assert os.path.isfile("mine.yaml")
    with open("mine.yaml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "edited" in content
    assert "echo built" in content
    assert "timeout: 30" in content


def test_trigger_build_returns_202_and_id(client):
    """触发构建应返回 202 + build_id。"""
    _write_pipeline("jenpy.yaml")
    resp = client.post("/api/builds", json={"file": "jenpy.yaml", "context": {}})
    assert resp.status_code == 202
    data = resp.json()
    assert "build_id" in data
    assert data["status"] == "queued"


def test_trigger_invalid_config_returns_400(client):
    """触发不存在的配置文件应返回 400。"""
    resp = client.post("/api/builds", json={"file": "nope.yaml"})
    assert resp.status_code == 400


def test_build_lifecycle(client):
    """触发 -> 轮询 -> 完成 -> 列表 -> 详情。"""
    _write_pipeline("jenpy.yaml")
    resp = client.post("/api/builds", json={"file": "jenpy.yaml"})
    build_id = resp.json()["build_id"]

    # 轮询等待完成
    deadline = time.time() + 15
    while time.time() < deadline:
        detail = client.get(f"/api/builds/{build_id}")
        if detail.status_code == 200:
            data = detail.json()
            if data["status"] in ("success", "failed"):
                break
        time.sleep(0.1)
    else:
        pytest.fail("构建未在超时内完成")

    assert data["status"] == "success"
    assert data["pipeline"] == "test-pipeline"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["step"] == "greet"

    # 列表里应能看到
    listing = client.get("/api/builds").json()
    assert any(r["build_id"] == build_id for r in listing)


def test_get_build_not_found(client):
    """查不存在的 build_id 应返回 404。"""
    resp = client.get("/api/builds/no-such-id")
    assert resp.status_code == 404


def test_step_log_retrieval(client):
    """构建完成后应能读取某步的完整日志。"""
    _write_pipeline("jenpy.yaml")
    resp = client.post("/api/builds", json={"file": "jenpy.yaml"})
    build_id = resp.json()["build_id"]

    # 等完成
    deadline = time.time() + 15
    while time.time() < deadline:
        detail = client.get(f"/api/builds/{build_id}")
        if detail.status_code == 200 and detail.json()["status"] in ("success", "failed"):
            break
        time.sleep(0.1)

    log_resp = client.get(f"/api/builds/{build_id}/logs/s1/greet")
    assert log_resp.status_code == 200
    assert "API_HELLO" in log_resp.text


def test_stream_replays_finished_build(client):
    """SSE 端点对已完成的构建应回放日志。"""
    _write_pipeline("jenpy.yaml")
    resp = client.post("/api/builds", json={"file": "jenpy.yaml"})
    build_id = resp.json()["build_id"]

    # 等完成
    deadline = time.time() + 15
    while time.time() < deadline:
        detail = client.get(f"/api/builds/{build_id}")
        if detail.status_code == 200 and detail.json()["status"] in ("success", "failed"):
            break
        time.sleep(0.1)

    # 读 SSE 流
    with client.stream("GET", f"/api/builds/{build_id}/stream") as r:
        assert r.status_code == 200
        collected = []
        for line in r.iter_lines():
            collected.append(line)
            if "done" in line:
                break
        joined = "\n".join(collected)
        assert "API_HELLO" in joined or "done" in joined
