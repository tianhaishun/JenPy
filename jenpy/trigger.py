"""自动触发：webhook 服务与定时轮询。

第一性原理：自动触发只有两种本质模式：
  1. 事件驱动（webhook）——「别人喊我，我才跑」
  2. 时间驱动（轮询）    ——「我定期自己看看要不要跑」
本模块用标准库实现这两者，不引入额外服务或依赖。
"""

from __future__ import annotations
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import load_pipeline
from .executor import Executor, _c
from . import history


def serve(config_file: str, host: str, port: int, token=None) -> int:
    """启动 webhook HTTP 服务，收到 POST 即触发一次构建。

    兼容 GitHub Webhook：POST 到 /，可选校验 token。
    """
    pipeline = load_pipeline(config_file)
    server = _make_server(pipeline, config_file, host, port, token)
    print(_c(f"JenPy webhook 服务已启动", "cyan"))
    print(_c(f"  监听: http://{host}:{port}/", "gray"))
    print(_c(f"  触发: curl -X POST http://{host}:{port}/", "gray"))
    if token:
        print(_c(f"  带 token: curl -X POST -H 'X-JenPy-Token: {token}' http://{host}:{port}/", "gray"))
    print(_c("  Ctrl+C 停止", "gray"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(_c("\n停止服务", "yellow"))
        server.shutdown()
    return 0


def _make_server(pipeline, config_file, host, port, token):
    """构造 HTTP 服务器，闭包捕获 pipeline 等上下文。"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # 静默默认的请求日志，用我们自己的格式
            pass

        def do_POST(self):
            # token 校验
            if token and self.headers.get("X-JenPy-Token") != token:
                self._respond(403, "token 校验失败")
                return
            # 异步触发，避免 HTTP 超时
            threading.Thread(target=_run_once, args=(pipeline,), daemon=True).start()
            self._respond(200, "构建已触发")

        def do_GET(self):
            # 健康检查端点
            if self.path in ("/", "/health"):
                self._respond(200, f"JenPy 服务中: {pipeline.name}")
            else:
                self._respond(404, "not found")

        def _respond(self, code, msg):
            body = msg.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return HTTPServer((host, port), Handler)


def watch(config_file: str, interval: int) -> int:
    """定时轮询：每隔 interval 秒检查 git 远程是否有新提交，有则触发构建。

    第一性原理：用 git 是否有新提交作为「是否需要重新构建」的判据——
    这是 CI 最朴素也最可靠的触发依据。
    """
    pipeline = load_pipeline(config_file)
    last_commit = _current_remote_commit()
    print(_c(f"JenPy watch 已启动（每 {interval}s 检查一次）", "cyan"))
    print(_c(f"  当前远程 commit: {_short(last_commit)}", "gray"))
    print(_c("  Ctrl+C 停止", "gray"))

    try:
        while True:
            time.sleep(interval)
            latest = _current_remote_commit()
            if latest and latest != last_commit:
                print(_c(f"\n检测到新提交: {_short(latest)}", "yellow"))
                last_commit = latest
                _run_once(pipeline)
            else:
                print(_c(".", "gray"), end="", flush=True)
    except KeyboardInterrupt:
        print(_c("\n停止监听", "yellow"))
    return 0


def _run_once(pipeline) -> None:
    """执行一次流水线并记录结果（供 webhook/watch 复用）。"""
    executor = Executor()
    result = executor.run(pipeline)
    history.save(result)


def _current_remote_commit() -> str:
    """获取当前分支远程最新 commit hash。失败返回空串。"""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "origin/HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def _short(sha: str) -> str:
    return sha[:8] if sha else "(未知)"
