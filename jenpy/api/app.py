"""FastAPI 应用工厂。

第一性原理：组装各路由、挂载静态前端、提供健康检查。
create_app() 是唯入口，被 `jenpy ui` 命令和测试复用。
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .routes import pipelines, builds, logs


def create_app() -> FastAPI:
    """构造 FastAPI 应用实例。"""
    app = FastAPI(
        title="JenPy",
        description="用 Python 写的极简 CI/CD 工具 —— 可视化平台 API",
        version=_get_version(),
    )

    # 健康检查
    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "name": "JenPy", "version": _get_version()}

    # API 路由
    app.include_router(pipelines.router)
    app.include_router(builds.router)
    app.include_router(logs.router)

    # 静态前端：若已构建产物存在，挂载 SPA
    static_dir = _static_dir()
    if static_dir and os.path.isdir(static_dir):
        _mount_spa(app, static_dir)

    return app


def _get_version() -> str:
    from .. import __version__
    return __version__


def _static_dir() -> str:
    """前端构建产物的目录（jenpy/web/static）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    # jenpy/api/app.py -> jenpy/web/static
    return os.path.join(here, "..", "web", "static")


def _mount_spa(app: FastAPI, static_dir: str) -> None:
    """挂载 SPA：静态资源直接返回，其他路径 fallback 到 index.html。"""
    static_dir = os.path.abspath(static_dir)
    index_path = os.path.join(static_dir, "index.html")

    # /assets 等静态文件
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets"))
              if os.path.isdir(os.path.join(static_dir, "assets"))
              else StaticFiles(directory=static_dir), name="assets")

    # SPA fallback：未匹配 API 的路径返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # API 路径不应被 SPA fallback 捕获（未匹配的 API 返回 404 JSON）
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        # 优先尝试精确文件
        candidate = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return JSONResponse({"detail": "前端未构建，请运行 npm run build"}, status_code=404)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> int:
    """启动 uvicorn 服务（供 `jenpy ui` 调用）。"""
    import uvicorn
    app = create_app()
    print(f"JenPy Web UI 启动中: http://{host}:{port}/")
    print("  API 文档: /docs")
    print("  Ctrl+C 停止")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
