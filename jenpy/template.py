"""流水线模板。

第一性原理：新用户最需要的是「一个能立刻跑通、看得懂的最小示例」。
"""

EXAMPLE_PIPELINE = """\
# JenPy 流水线配置示例
# 文档：https://github.com/tianhaishun/JenPy

name: my-project
workspace: .        # 命令执行的工作目录

# 全局环境变量，所有阶段共享
env:
  PYTHONUNBUFFERED: "1"

stages:
  - name: 安装依赖
    steps:
      - name: 安装 Python 包
        run: pip install -r requirements.txt
        timeout: 300          # 超时秒数，防止挂死

  - name: 测试
    steps:
      - name: 运行单元测试
        run: pytest -v
        continue_on_error: true   # 测试失败也继续后续阶段

  - name: 构建
    steps:
      - name: 打包
        run: python -m build

  - name: 部署
    when: branch == 'main'     # 仅 main 分支执行部署
    steps:
      - name: 同步到服务器
        deploy:
          method: rsync
          source: ./dist/
          target: user@your-server:/var/www/my-project/
"""
