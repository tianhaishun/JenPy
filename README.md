# JenPy

> 用 Python 写的极简 CI/CD 工具 —— 既有命令行的简洁，又有可视化平台的直观。

[![CI](https://github.com/tianhaishun/JenPy/actions/workflows/ci.yml/badge.svg)](https://github.com/tianhaishun/JenPy/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

JenPy 将 Python 的灵活性与 Jenkins 的自动化能力结合，为 Python 开发者打造一款**轻量、可视、可扩展**的 CI/CD 工具。

## 为什么选择 JenPy？

| 特性 | JenPy | Jenkins | Drone/Woodpecker |
|------|-------|---------|------------------|
| 安装复杂度 | `pip install` 即用 | 需 Java + 容器 | 需 Docker + 数据库 |
| 配置方式 | 单个 YAML | XML / Jenkinsfile | YAML + 容器 |
| 可视化 UI | 内置（`jenpy ui`） | 内置 | 内置 |
| 核心依赖 | 仅 PyYAML | JRE | Docker |
| 扩展门槛 | 一个 Python 函数 | 写 Java 插件 | 写 Go 插件 |
| 适合场景 | Python 项目 / 个人 / 小团队 | 企业级 / 多语言 | 容器原生 |

## 两种使用方式

### 命令行（CLI）

```bash
jenpy run          # 执行流水线，实时输出
jenpy history      # 查看构建历史
jenpy logs <id>    # 查看某次构建的步骤明细
```

### 可视化 Web UI

```bash
jenpy ui           # 启动 Web 平台（http://127.0.0.1:8000）
```

界面参考 **Jenkins 经典风格**，融合现代前端技术栈（Vue 3 + Naive UI）：

- 🔵 **状态球图标** — Jenkins 最具辨识度的视觉符号：蓝球脉冲=构建中、绿球=成功、红球=失败
- 🎨 **Jenkins 配色** — 深蓝 header + 浅色主题，信息密度高，熟悉 Jenkins 的用户零学习成本
- 📊 **Dashboard**：构建概览统计（成功率/耗时）、紧凑行列表、构建队列 + 执行器状态 widget
- 📝 **可视化编辑器**：表单编辑阶段/步骤，右侧实时 YAML 预览，保存即生效
- 📡 **实时日志流**：构建进行中逐行推送输出（SSE），深色终端风格，自动滚动
- 🔄 **手动触发/重跑**：浏览器上一键触发或重跑失败的构建

```
┌──────────────────────────────────────────────────────────┐
│ 🛠 JenPy  CI/CD 平台                          API 文档    │  ← Jenkins 深蓝 header
├──────────┬───────────────────────────────────────────────┤
│ Dashboard│  Dashboard                    [刷新] [🚀 立即构建] │
│ 构建历史  │ ┌──────┬──────┬──────┬──────┐                  │
│ 流水线   │ │ 总构建│ 成功 │ 失败 │成功率│                  │
│ 管理     │ │  12  │  10  │   2  │ 83%  │                  │
│          │ └──────┴──────┴──────┴──────┘                  │
│ ───────  │ ┌─────────────────────────┬─────────────────┐  │
│ 构建执行器│ │ 构建历史                 │ 构建队列         │  │
│ ● 在线   │ │ 🟢 example-pipeline #... │ （队列为空）     │  │
│          │ │ 🔴 my-app #181744        │                 │  │
│          │ │ 🟢 deploy-test #181530   │ 执行器状态      │  │
│          │ └─────────────────────────┤ 🟢 executor-1   │  │
│          │                             │   空闲          │  │
└──────────┴─────────────────────────────┴─────────────────┘
```

## 快速开始

### 安装

```bash
git clone https://github.com/tianhaishun/JenPy.git
cd JenPy
pip install -e .           # 核心 CLI（零额外依赖）
pip install -e ".[web]"    # 加上可视化 UI（FastAPI + uvicorn）
```

### 核心 CLI

```bash
jenpy init              # 生成示例配置 jenpy.yaml
jenpy run               # 执行流水线
jenpy history           # 查看历史
```

### 可视化 UI

```bash
jenpy ui                # 启动 Web 平台
# 浏览器打开 http://127.0.0.1:8000
```

## 流水线配置

配置是普通的 YAML：

```yaml
name: my-project

stages:
  - name: 构建
    steps:
      - run: pip install -r requirements.txt
        timeout: 300

  - name: 测试
    steps:
      - run: pytest -v
        continue_on_error: true

  - name: 部署
    when: branch == 'main'
    steps:
      - deploy:
          method: copy             # 纯 Python 跨平台，无需 rsync
          source: ./dist/
          target: ./deployed/
          delete: true
```

完整字段说明见 [文档](#字段说明)。可视化编辑器可在浏览器中直接编辑并保存。

## 命令参考

```
jenpy init [-o FILE]               生成示例配置
jenpy run [-f FILE] [--var K=V]    执行流水线
jenpy list [-f FILE]               查看流水线结构
jenpy history [-n N]               查看构建历史
jenpy logs <build_id>              查看某次构建明细
jenpy ui [-p PORT]                 启动可视化 Web 界面
jenpy serve [-p PORT] [--token T]  启动 webhook 服务（兼容旧版）
jenpy watch [-i SECONDS]           定时轮询自动触发
```

## 字段说明

**顶层**

| 字段 | 说明 |
|---|---|
| `name` | 流水线名称 |
| `workspace` | 命令执行的工作目录（默认 `.`） |
| `env` | 全局环境变量，所有阶段共享 |
| `stages` | 阶段列表，按顺序执行 |

**Stage（阶段）**

| 字段 | 说明 |
|---|---|
| `name` | 阶段名称 |
| `steps` | 步骤列表 |
| `when` | 条件表达式，为假时跳过该阶段（如 `branch == 'main'`） |

**Step（步骤）**

| 字段 | 说明 |
|---|---|
| `name` | 步骤名称 |
| `run` | 要执行的 shell 命令（支持多行、`{{ var }}` 模板变量） |
| `timeout` | 超时秒数，防止命令挂死 |
| `env` | 该步骤专属的环境变量 |
| `continue_on_error` | 为 true 时，此步骤失败不阻断后续 |
| `deploy` | 部署配置（与 `run` 二选一） |

### 部署方式

| 方式 | 说明 | 适用场景 |
|---|---|---|
| `copy` | 纯 Python 复制（shutil），跨平台零依赖 | 本地/同机/Windows |
| `rsync` | 调用系统 rsync 增量同步 | 远程服务器（需 rsync） |
| `script` | 执行自定义脚本 | 复杂逻辑（docker/scp/helm） |

### 条件表达式（when）

`when` 采用自研安全解析器（**不使用 eval**），只支持 `==` `!=` `and` `or` `()`，杜绝代码注入：

```
branch == 'main'
branch == 'main' and env == 'prod'
(branch == 'main' or branch == 'release') and env == 'prod'
```

## 运行测试

```bash
pip install -e ".[dev,web]"
pytest tests/ -v          # 82+ 测试
```

## 项目结构

```
jenpy/
├── cli.py          命令行入口
├── config.py       YAML 加载与序列化
├── pipeline.py     数据模型（Pipeline/Stage/Step）
├── conditions.py   when 条件安全求值器（自研，无 eval）
├── executor.py     执行引擎（流式输出、超时、进程组清理）
├── manager.py      构建编排器（队列、状态、订阅分发）
├── history.py      构建历史（原子写 + 锁）
├── trigger.py      webhook 与定时轮询
├── deploy.py       部署执行器（copy/rsync/script）
├── template.py     示例配置模板
├── api/            FastAPI Web 层（REST + SSE + 静态托管）
└── web/static/     前端构建产物（由 web/frontend 构建）
web/frontend/       Vue 3 前端源码（Jenkins 风格 UI）
  ├── components/   StatusBall 状态球、LogViewer 日志终端
  ├── views/        Dashboard、BuildDetail、PipelineEditor 等
  └── theme.ts      Jenkins 配色与共享工具
```

## 如何贡献

欢迎提交 Issue 和 Pull Request！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

**适合新手的贡献方向**：
- 加一个部署方式（docker/scp/helm）—— 只需在 `deploy.py` 加一个函数
- 改进前端组件（日志搜索、主题切换、构建对比）
- 完善文档和示例

架构与扩展点说明见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## Roadmap

- [x] 核心 CLI（YAML 流水线、执行引擎、历史、条件、部署）
- [x] 可视化 Web UI（Dashboard、编辑器、实时日志、触发）
- [x] Jenkins 风格界面（状态球、深蓝 header、构建队列 widget）
- [x] 自举 CI（GitHub Actions）
- [x] 并发安全（history 原子写 + 锁、进程组清理）
- [ ] 插件机制（entry_points 注册自定义部署器）
- [ ] 并发构建支持（多 executor）
- [ ] 通知集成（钉钉/Slack/邮件）
- [ ] 构建产物 artifacts 打包
- [ ] 流水线 DAG（阶段间依赖、并行 stage）

## 许可证

[Apache License 2.0](LICENSE)
