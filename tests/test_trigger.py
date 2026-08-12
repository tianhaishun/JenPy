"""trigger 模块测试 —— 自动触发的 context 注入。

第一性原理：自动触发（webhook/watch）最常用的条件就是分支与提交。
若不注入 context，when: branch == 'main' 在自动触发时永远为假，部署阶段会被跳过。
"""

import subprocess

from jenpy import trigger


def test_detect_git_context_in_repo():
    """在 git 仓库内，_detect_git_context 应返回当前 branch。"""
    ctx = trigger._detect_git_context()
    # 这个测试仓库在 main 分支
    assert "branch" in ctx
    assert ctx["branch"]
    assert ctx["git"]["ref"] == ctx["branch"]
    assert "commit" in ctx["git"]


def test_current_branch_returns_main():
    """_current_branch 应返回非空分支名。"""
    branch = trigger._current_branch()
    assert branch, "应在 git 仓库内得到分支名"
    assert branch != "HEAD"


def test_current_commit_returns_hash():
    """_current_commit 应返回短 commit hash。"""
    commit = trigger._current_commit()
    assert commit, "应在 git 仓库内得到 commit"
    # 短 hash 是 7+ 位十六进制
    assert all(c in "0123456789abcdef" for c in commit)


def test_run_once_with_explicit_context(monkeypatch, tmp_path):
    """_run_once 应把传入的 context 透传给 executor.run，使 when 条件生效。"""
    monkeypatch.chdir(tmp_path)

    captured = {}

    class FakeExecutor:
        def __init__(self, *a, **kw):
            pass

        def run(self, pipeline, context=None):
            captured["context"] = context
            # 返回一个最小 BuildResult 形状
            from jenpy.executor import BuildResult
            return BuildResult(pipeline_name=pipeline.name, success=True)

    monkeypatch.setattr(trigger, "Executor", FakeExecutor)
    monkeypatch.setattr(trigger.history, "save", lambda r: "fake-id")

    class FakePipeline:
        name = "t"

    trigger._run_once(FakePipeline(), context={"branch": "release"})
    assert captured["context"] == {"branch": "release"}
