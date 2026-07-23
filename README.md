# JenPy

JenPy: A minimal CI/CD tool combining Python's flexibility with Jenkins' automation prowess. Designed for Python developers, it simplifies building, testing, and deploying code.

## 简介

JenPy 是一个极简的 CI/CD 工具，用 Python 写成。它的设计遵循**第一性原理**：

> CI/CD 的本质，就是「按顺序执行一组命令，并记录结果」。

JenPy 不发明新的概念，只把这件事做好——用 YAML 描述流水线，用命令行执行它，把每次的结果存下来。

## 功能特点

- **YAML 流水线**：用简洁的 YAML 描述阶段与步骤，符合「配置即代码」理念
- **真实执行引擎**：实时输出、超时控制、环境变量、失败即停
- **构建历史**：每次执行的结果、耗时、步骤明细自动落盘，随时可查
- **条件执行**：用 `when` 表达式控制阶段是否执行（如仅 main 分支部署）
- **自动触发**：内置 webhook 服务和定时轮询，支持远程/自动触发构建
- **部署支持**：内置 rsync 部署和自定义脚本两种部署方式
- **零依赖核心**：除 PyYAML 外不依赖任何第三方库

## 安装

```bash
git clone https://github.com/tianhaishun/JenPy.git
cd JenPy
pip install -e .
```

安装后会得到 `jenpy` 命令。

## 快速开始

### 1. 生成示例配置

```bash
jenpy init              # 在当前目录生成 jenpy.yaml
```

### 2. 执行流水线

```bash
jenpy run               # 默认读取 jenpy.yaml 并执行
```

执行时你会看到实时输出和每一步的成败状态。

### 3. 查看历史

```bash
jenpy history           # 列出最近的构建记录
jenpy logs <build_id>   # 查看某次构建的步骤明细
```

## 流水线配置

配置文件是普通的 YAML。最小示例：

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
          method: rsync
          source: ./dist/
          target: user@server:/var/www/app/
```

### 字段说明

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

### 模板变量

命令中可用 `{{ var }}` 引用通过 `--var` 注入的变量：

```bash
jenpy run --var branch=main --var env=prod
```

配置中：`run: echo "部署到 {{ env }} 环境"`

## 命令参考

```
jenpy init [-o FILE]            生成示例配置
jenpy run [-f FILE] [--var K=V] 执行流水线
jenpy list [-f FILE]            查看流水线结构
jenpy history [-n N]            查看构建历史
jenpy logs <build_id>           查看某次构建明细
jenpy serve [-p PORT] [--token T]  启动 webhook 服务
jenpy watch [-i SECONDS]        定时轮询自动触发
```

### 自动触发

**Webhook 模式**（事件驱动）——启动一个 HTTP 服务，收到 POST 即触发：

```bash
jenpy serve --port 8080 --token your-secret
```

触发方式：
```bash
curl -X POST -H "X-JenPy-Token: your-secret" http://127.0.0.1:8080/
```

**轮询模式**（时间驱动）——定期检查 git 是否有新提交，有则自动构建：

```bash
jenpy watch --interval 60
```

## 项目结构

```
jenpy/
├── __init__.py     版本号
├── cli.py          命令行入口
├── config.py       YAML 加载与校验
├── pipeline.py     数据模型（Pipeline/Stage/Step）
├── executor.py     执行引擎（核心）
├── history.py      构建历史读写
├── trigger.py      webhook 与定时轮询
├── deploy.py       部署执行器
└── template.py     示例配置模板
```

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 如何贡献

欢迎提交 Issue 和 Pull Request。请确保 `pytest tests/` 通过。

## 许可证

[Apache License 2.0](LICENSE)
