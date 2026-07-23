"""部署执行器。

第一性原理：部署的本质是「把构建产物搬运到目标位置」。
最可靠、最被广泛理解的搬运方式就是调用系统已有的工具（rsync / 自定义脚本）。
本模块不发明新的传输协议，只封装这些成熟工具的调用。
"""

from __future__ import annotations
import os
import subprocess
import sys
from typing import Optional


def run(config: dict, workspace: str, env: dict,
        log_path: Optional[str] = None) -> bool:
    """根据配置执行一次部署，返回是否成功。

    Args:
        config: 部署配置字典，必须含 method 字段
        workspace: 命令工作目录
        env: 环境变量
        log_path: 若提供，把部署命令的输出写到该文件
    """
    method = config.get("method", "script")

    if method == "rsync":
        return _deploy_rsync(config, workspace, env, log_path)
    if method == "copy":
        return _deploy_copy(config, workspace, env, log_path)
    if method == "script":
        return _deploy_script(config, workspace, env, log_path)

    _log(log_path, f"不支持的部署方式: {method}")
    print(f"  ✗ 不支持的部署方式: {method}", file=sys.stderr)
    return False


def _deploy_rsync(config, workspace, env, log_path) -> bool:
    """用 rsync 同步文件。第一性原理：rsync 是增量同步的事实标准。"""
    source = config.get("source")
    target = config.get("target")
    if not source or not target:
        _log(log_path, "rsync 部署缺少 source 或 target")
        print("  ✗ rsync 部署需要 source 和 target", file=sys.stderr)
        return False

    # -a 归档模式（保留权限/软链等），-v 详细输出，-z 压缩传输
    cmd = ["rsync", "-avz"]
    if config.get("delete", False):
        cmd.append("--delete")
    cmd += [source, target]
    print(f"  $ {' '.join(cmd)}")
    return _exec(cmd, workspace, env, log_path, shell=False,
                 missing_msg="系统未安装 rsync")


def _deploy_copy(config, workspace, env, log_path) -> bool:
    """用纯 Python 复制文件到目标目录。

    第一性原理：部署的本质是「搬运文件」。rsync 是优秀的搬运工具，但
    Windows 默认没有它。本地/同机部署用 Python 标准库 shutil 即可——
    零依赖、跨平台、行为可预测。适合本地测试、容器内部署、同机搬运。
    """
    import shutil

    source = config.get("source")
    target = config.get("target")
    if not source or not target:
        _log(log_path, "copy 部署缺少 source 或 target")
        print("  ✗ copy 部署需要 source 和 target", file=sys.stderr)
        return False

    src = os.path.join(workspace, source) if not os.path.isabs(source) else source
    tgt = os.path.join(workspace, target) if not os.path.isabs(target) else target

    print(f"  $ copy {source} -> {target}")
    try:
        os.makedirs(tgt, exist_ok=True)
        if config.get("delete", False):
            # 先清空目标，再复制（模拟 rsync --delete）
            for entry in os.listdir(tgt):
                full = os.path.join(tgt, entry)
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
        # 复制源内容到目标
        if os.path.isdir(src):
            for entry in os.listdir(src):
                s = os.path.join(src, entry)
                d = os.path.join(tgt, entry)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        else:
            shutil.copy2(src, tgt)
        msg = f"copy 完成: {source} -> {target}"
        _log(log_path, msg)
        print(f"  ✓ {msg}")
        return True
    except Exception as e:
        _log(log_path, f"copy 失败: {e}")
        print(f"  ✗ copy 失败: {e}", file=sys.stderr)
        return False


def _deploy_script(config, workspace, env, log_path) -> bool:
    """执行用户自定义的部署脚本。

    第一性原理：当内置方式不够用时，把控制权完全交给用户——他最清楚自己的部署逻辑。
    """
    script = config.get("run")
    if not script:
        _log(log_path, "script 部署缺少 run 字段")
        print("  ✗ script 部署需要 run 字段指定脚本", file=sys.stderr)
        return False

    print(f"  $ {script}")
    return _exec(script, workspace, env, log_path, shell=True,
                 missing_msg="执行异常")


def _exec(cmd, workspace, env, log_path, shell, missing_msg) -> bool:
    """统一执行：输出同时打终端和日志文件。"""
    try:
        proc = subprocess.Popen(
            cmd, shell=shell, cwd=workspace, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        lines = []
        for line in proc.stdout:
            print(line, end="")
            lines.append(line)
        proc.wait()
        _log(log_path, "".join(lines))
        return proc.returncode == 0
    except FileNotFoundError:
        _log(log_path, missing_msg)
        print(f"  ✗ {missing_msg}", file=sys.stderr)
        return False
    except Exception as e:
        _log(log_path, f"{missing_msg}: {e}")
        print(f"  ✗ {missing_msg}: {e}", file=sys.stderr)
        return False


def _log(log_path: Optional[str], text: str) -> None:
    """把文本追加到日志文件（若提供）。"""
    if not log_path:
        return
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass
