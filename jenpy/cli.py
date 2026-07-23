"""JenPy 命令行入口。

第一性原理：CLI 是人和工具之间的文字接口。每个子命令对应一个最朴素的动作：
  init     —— 生成一份能跑的示例配置
  run      —— 执行一条流水线
  list     —— 看有哪些流水线配置
  history  —— 看过去跑过哪些、结果如何
  logs     —— 看某次构建的细节
  serve    —— 起一个 webhook 服务，让外部能触发构建
  watch    —— 定时检查代码更新并自动构建

参数解析用标准库 argparse，零外部依赖。
"""

from __future__ import annotations
import argparse
import sys

from . import __version__, history
from .config import load_pipeline, ConfigError
from .executor import Executor, _c
from . import template
from . import trigger


def main(argv=None) -> int:
    """CLI 主入口，返回退出码。"""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except ConfigError as e:
        print(_c(f"配置错误: {e}", "red"), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(_c("\n已中断", "yellow"))
        return 130


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="jenpy",
        description="JenPy —— 用 Python 写的极简 CI/CD 工具",
    )
    parser.add_argument("-V", "--version", action="version", version=f"jenpy {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="生成示例流水线配置 jenpy.yaml")
    p_init.add_argument("-o", "--output", default="jenpy.yaml", help="输出文件路径")
    p_init.set_defaults(func=cmd_init)

    # run
    p_run = sub.add_parser("run", help="执行一条流水线")
    p_run.add_argument("-f", "--file", default="jenpy.yaml", help="配置文件路径")
    p_run.add_argument("--var", action="append", default=[], metavar="KEY=VAL",
                       help="注入模板变量，可多次使用，如 --var branch=main")
    p_run.set_defaults(func=cmd_run)

    # list
    p_list = sub.add_parser("list", help="显示当前流水线的结构")
    p_list.add_argument("-f", "--file", default="jenpy.yaml", help="配置文件路径")
    p_list.set_defaults(func=cmd_list)

    # history
    p_hist = sub.add_parser("history", help="查看构建历史")
    p_hist.add_argument("-n", "--limit", type=int, default=20, help="显示条数")
    p_hist.set_defaults(func=cmd_history)

    # logs
    p_logs = sub.add_parser("logs", help="查看某次构建的步骤明细")
    p_logs.add_argument("build_id", help="构建 ID，如 20260723-160530")
    p_logs.set_defaults(func=cmd_logs)

    # serve
    p_serve = sub.add_parser("serve", help="启动 webhook 服务，接收远程触发")
    p_serve.add_argument("-f", "--file", default="jenpy.yaml", help="配置文件路径")
    p_serve.add_argument("-H", "--host", default="127.0.0.1", help="监听地址")
    p_serve.add_argument("-p", "--port", type=int, default=8080, help="监听端口")
    p_serve.add_argument("--token", default=None, help="校验 token（建议设置）")
    p_serve.set_defaults(func=cmd_serve)

    # watch
    p_watch = sub.add_parser("watch", help="定时轮询并自动触发构建")
    p_watch.add_argument("-f", "--file", default="jenpy.yaml", help="配置文件路径")
    p_watch.add_argument("-i", "--interval", type=int, default=60, help="轮询间隔（秒）")
    p_watch.set_defaults(func=cmd_watch)

    return parser


# ---------- 子命令实现 ----------

def cmd_init(args) -> int:
    """生成示例配置。"""
    import os
    if os.path.exists(args.output):
        print(_c(f"文件已存在，未覆盖: {args.output}", "yellow"))
        return 1
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(template.EXAMPLE_PIPELINE)
    print(_c(f"已生成示例配置: {args.output}", "green"))
    print(_c(f"编辑它，然后运行: jenpy run -f {args.output}", "cyan"))
    return 0


def cmd_run(args) -> int:
    """执行流水线。"""
    pipeline = load_pipeline(args.file)
    context = _parse_vars(args.var)
    executor = Executor()
    result = executor.run(pipeline, context)

    # 落盘到历史记录
    build_id = history.save(result)
    print(_c(f"  构建记录 ID: {build_id}", "gray"))
    print(_c(f"  查看: jenpy logs {build_id}", "gray"))

    return 0 if result.success else 1


def cmd_list(args) -> int:
    """展示流水线结构。"""
    pipeline = load_pipeline(args.file)
    print(_c(f"流水线: {pipeline.name}", "cyan"))
    print(_c(f"工作目录: {pipeline.workspace}", "gray"))
    if pipeline.env:
        print(_c(f"环境变量: {list(pipeline.env.keys())}", "gray"))
    for i, stage in enumerate(pipeline.stages, 1):
        when = f"  (when: {stage.when})" if stage.when else ""
        print(f"  [{i}] 阶段 {stage.name}{when}")
        for step in stage.steps:
            kind = "deploy" if step.deploy else (step.run or "?")
            print(f"        - {step.name}: {kind}")
    return 0


def cmd_history(args) -> int:
    """查看历史。"""
    records = history.list_records(limit=args.limit)
    if not records:
        print(_c("暂无构建记录", "yellow"))
        return 0
    print(_c(f"最近 {len(records)} 条构建记录:", "cyan"))
    print(f"  {'构建ID':<18} {'状态':<8} {'耗时':<8} {'流水线':<16} 开始时间")
    for r in records:
        status = _c(r["status"], "green" if r["status"] == "success" else "red")
        print(f"  {r['build_id']:<18} {status:<8} {r['duration']:<8} "
              f"{r['pipeline']:<16} {r['started_at']}")
    return 0


def cmd_logs(args) -> int:
    """查看某次构建的步骤明细。"""
    record = history.get_record(args.build_id)
    if not record:
        print(_c(f"找不到构建记录: {args.build_id}", "red"))
        return 1
    status = _c(record["status"], "green" if record["status"] == "success" else "red")
    print(_c(f"构建 {record['build_id']}", "cyan"))
    print(f"  流水线: {record['pipeline']}")
    print(f"  状态:   {status}")
    print(f"  开始:   {record['started_at']}")
    print(f"  耗时:   {record['duration']}s")
    print(_c("  步骤明细:", "yellow"))
    for s in record["steps"]:
        mark = _c("✓", "green") if s["success"] else _c("✗", "red")
        print(f"    {mark} [{s['stage']}] {s['step']} ({s['duration']}s)")
    return 0


def cmd_serve(args) -> int:
    """启动 webhook 服务。"""
    return trigger.serve(
        config_file=args.file,
        host=args.host,
        port=args.port,
        token=args.token,
    )


def cmd_watch(args) -> int:
    """定时轮询触发。"""
    return trigger.watch(
        config_file=args.file,
        interval=args.interval,
    )


def _parse_vars(pairs: list) -> dict:
    """把 ['branch=main', 'env=prod'] 解析成 {'branch': 'main', 'env': 'prod'}。"""
    context = {}
    for pair in pairs:
        if "=" not in pair:
            continue
        key, _, val = pair.partition("=")
        context[key.strip()] = val.strip()
    return context


if __name__ == "__main__":
    sys.exit(main())
