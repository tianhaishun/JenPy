# JenPy 架构文档

本文档帮助贡献者理解 JenPy 的整体设计，找到合适的扩展点。

## 设计哲学

JenPy 遵循**第一性原理**：CI/CD 的本质就是「按顺序执行一组命令，并记录结果」。
所有功能都从这个本质派生，不引入不必要的复杂度。每个模块的职责单一，
用朴素的 Python 实现，优先标准库。

## 五层架构

```
┌─────────────────────────────────────────────────┐
│              用户入口层                          │
│   jenpy (CLI)          jenpy ui (浏览器)         │
├─────────────────────────────────────────────────┤
│              Web API 层  (jenpy/api/)            │
│   FastAPI · REST · SSE · WebSocket · 静态托管    │
├─────────────────────────────────────────────────┤
│           构建编排层  (jenpy/manager.py)         │
│   BuildManager · 串行队列 · 状态跟踪 · 订阅分发   │
├─────────────────────────────────────────────────┤
│             核心引擎层  (jenpy/)                 │
│   Executor · config · conditions · history      │
│   trigger · deploy · pipeline · template        │
├─────────────────────────────────────────────────┤
│             存储层  (.jenpy/)                    │
│   builds/<id>/*.log · history.json              │
└─────────────────────────────────────────────────┘
```

## 模块职责

| 模块 | 职责 | 扩展点 |
|------|------|--------|
| `pipeline.py` | 数据模型（Pipeline/Stage/Step dataclass） | 加新字段 |
| `config.py` | YAML ↔ Pipeline 对象互转 | `load_pipeline` / `dump_pipeline` |
| `conditions.py` | `when` 条件安全求值（自研递归下降，无 eval） | 加新运算符 |
| `executor.py` | 执行引擎：拉子进程、流式输出、超时、落盘 | `on_line`/`on_step` 回调 |
| `history.py` | 构建历史持久化（JSON，原子写 + 锁） | 换存储后端 |
| `manager.py` | 构建编排：队列、状态、订阅（Web 层的桥梁） | 加并发策略 |
| `trigger.py` | webhook + 定时轮询自动触发 | 加触发源 |
| `deploy.py` | 部署执行（copy/rsync/script） | **加部署插件** |
| `template.py` | 示例配置模板 | 改默认模板 |
| `cli.py` | 命令行入口（argparse） | 加子命令 |
| `api/` | FastAPI Web 层（REST + SSE + 静态托管） | 加端点 |

## 数据流：一次构建的生命周期

```
用户触发 (CLI run / API POST / webhook / watch)
        │
        ▼
  BuildManager.trigger(pipeline, context)
        │  分配 build_id，入队列，立即返回
        ▼
  [后台工作线程] Executor.run(pipeline, context)
        │
        │  逐阶段、逐步骤执行：
        │    ├─ _should_run(stage) → 评估 when 条件
        │    ├─ _run_command() → subprocess.Popen
        │    │     ├─ stdout 逐行 → 终端 + 日志文件 + on_line 回调
        │    │     └─ 超时 → 进程组 kill
        │    └─ on_step 回调 → 通知步骤完成
        │
        ▼
  BuildResult → history.save()  (原子写 history.json)
        │
        ▼
  Web 层：SSE 推送日志行 / WebSocket 推送步骤事件
```

## 如何扩展

### 加一个部署方式（最容易上手的贡献）

在 `deploy.py` 加一个 `_deploy_xxx` 函数并在 `run()` 注册：

```python
def _deploy_docker(config, workspace, env, log_path) -> bool:
    image = config.get("image")
    cmd = ["docker", "build", "-t", image, workspace]
    return _exec(cmd, workspace, env, log_path, shell=False, missing_msg="未安装 docker")

# 在 run() 的方法分发里加：
if method == "docker":
    return _deploy_docker(config, workspace, env, log_path)
```

YAML 里就能用：

```yaml
deploy:
  method: docker
  image: myapp:latest
```

### 加一个 API 端点

在 `jenpy/api/routes/` 建路由文件，在 `app.py` 的 `create_app()` 里 include。

### 加一个 CLI 子命令

在 `cli.py` 的 `_build_parser()` 加 `sub.add_parser(...)` 并 `set_defaults(func=cmd_xxx)`。

## 关键设计决策

1. **不用 eval**：`conditions.py` 手写递归下降解析器，只支持 `==`/`!=`/`and`/`or`/`()`，杜绝代码注入。
2. **零依赖核心**：核心 CLI 只依赖 PyYAML；FastAPI/uvicorn 是 `[web]` extra，按需安装。
3. **原子写 + 锁**：`history.save` 用临时文件 + `os.replace` + `threading.Lock`，保证并发安全。
4. **进程组清理**：超时杀进程用 `killpg`(POSIX) / `taskkill /T`(Windows)，避免子进程残留。
5. **同步执行 + 异步推送**：Executor 是同步阻塞的，跑在 BuildManager 的工作线程里；Web 层用 SSE 桥接同步回调到异步流。
