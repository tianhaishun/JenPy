# 贡献指南

欢迎为 JenPy 贡献代码！本文档帮你快速上手。

## 开发环境

### 后端（Python）

```bash
git clone https://github.com/tianhaishun/JenPy.git
cd JenPy
pip install -e ".[dev,web]"   # 安装开发依赖 + Web 依赖
pytest tests/ -v              # 确认测试通过
```

### 前端（Vue 3）

```bash
cd web/frontend
npm install
npm run dev      # 启动 Vite dev server（端口 5173，自动代理 /api 到 8000）
```

开发时开两个终端：
1. `jenpy ui`（后端 FastAPI，端口 8000）
2. `cd web/frontend && npm run dev`（前端热更新，端口 5173）

浏览器访问 `http://localhost:5173`，改前端代码自动刷新。

### 构建前端

```bash
cd web/frontend
npm run build    # 产物输出到 jenpy/web/static/
```

之后 `jenpy ui` 会自动托管构建好的前端。

## 提交规范

- 消息格式：`<类型>: <描述>`，如 `feat: 加 docker 部署方式`、`fix: 修复 SSE 断连`
- 类型：`feat`（新功能）/ `fix`（修复）/ `docs`（文档）/ `test`（测试）/ `refactor`（重构）
- 一个 PR 只做一件事，保持改动聚焦
- **所有 PR 必须通过 `pytest tests/`**（CI 会自动检查）

## 测试要求

- 新功能必须配测试。测试风格：**用真实命令验证**，不 mock subprocess（参考 `tests/test_executor.py`）
- 用 `tmp_path` + `monkeypatch.chdir` 隔离文件系统副作用（参考 `tests/test_logging.py`）
- 跨平台：用 `python -c "..."` 代替 `sleep` 等平台相关命令

## 我能贡献什么？

### 🟢 适合新手（good first issue）

- **加一个部署方式**：在 `jenpy/deploy.py` 加 `_deploy_docker` / `_deploy_scp` 等（见 [ARCHITECTURE.md](ARCHITECTURE.md)）
- **加 API 端点**：如批量删除历史记录、按 pipeline 名筛选
- **改进前端组件**：日志搜索/过滤、构建对比视图、深色/浅色主题切换
- **完善文档**：更多示例、中英文双语

### 🟡 中等难度

- 并发构建支持（当前 BuildManager 串行执行）
- 构建产物 artifacts 打包下载
- 通知集成（钉钉/Slack/邮件 webhook）
- GitHub HMAC 签名校验（替代裸 token）

### 🔴 有挑战

- 插件机制（entry_points 注册自定义部署器/触发器）
- 分布式构建（多 worker）
- 流水线 DAG（阶段间依赖、并行 stage）

## 项目结构

详见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 行为准则

保持友善、尊重所有贡献者。技术讨论对事不对人。
