"""部署执行器。

第一性原理：部署的本质是「把构建产物搬运到目标位置」。
最可靠、最被广泛理解的搬运方式就是调用系统已有的工具（rsync / 自定义脚本）。
本模块不发明新的传输协议，只封装这些成熟工具的调用。
"""

from __future__ import annotations
import subprocess
import sys


def run(config: dict, workspace: str, env: dict) -> bool:
    """根据配置执行一次部署，返回是否成功。

    Args:
        config: 部署配置字典，必须含 method 字段
        workspace: 命令工作目录
        env: 环境变量
    """
    method = config.get("method", "script")

    if method == "rsync":
        return _deploy_rsync(config, workspace, env)
    if method == "script":
        return _deploy_script(config, workspace, env)

    print(f"  ✗ 不支持的部署方式: {method}", file=sys.stderr)
    return False


def _deploy_rsync(config: dict, workspace: str, env: dict) -> bool:
    """用 rsync 同步文件。第一性原理：rsync 是增量同步的事实标准。"""
    source = config.get("source")
    target = config.get("target")
    if not source or not target:
        print("  ✗ rsync 部署需要 source 和 target", file=sys.stderr)
        return False

    # -a 归档模式（保留权限/软链等），-v 详细输出，-z 压缩传输
    cmd = ["rsync", "-avz", "--delete", source, target]
    print(f"  $ {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=workspace, env=env)
        return result.returncode == 0
    except FileNotFoundError:
        print("  ✗ 系统未安装 rsync", file=sys.stderr)
        return False


def _deploy_script(config: dict, workspace: str, env: dict) -> bool:
    """执行用户自定义的部署脚本。

    第一性原理：当内置方式不够用时，把控制权完全交给用户——他最清楚自己的部署逻辑。
    """
    script = config.get("run")
    if not script:
        print("  ✗ script 部署需要 run 字段指定脚本", file=sys.stderr)
        return False

    print(f"  $ {script}")
    try:
        result = subprocess.run(script, shell=True, cwd=workspace, env=env)
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ 部署脚本执行异常: {e}", file=sys.stderr)
        return False
