"""JenPy Web API 包。

第一性原理：Web API 是「让浏览器和 HTTP 客户端能驱动 CI」的薄层。
它把 BuildManager 的能力暴露为 REST + SSE + WebSocket，不包含业务逻辑。
所有执行都经 BuildManager 单例，保证串行与数据安全。

依赖：fastapi、uvicorn（optional extra [web]，核心 CLI 不需要它们）。
"""
