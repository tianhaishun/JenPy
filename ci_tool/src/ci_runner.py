import subprocess
import sys

# 配置信息
git_repo_url = "https://github.com/your-username/your-repo.git"
build_command = "python setup.py install"  # 示例构建命令
test_command = "pytest"  # 示例测试命令

def run_command(command):
    """运行命令行指令并打印输出"""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print("错误输出:", stderr.decode())
        sys.exit(process.returncode)
    print(stdout.decode())

def main():
    print("拉取最新代码...")
    run_command(f"git clone {git_repo_url} repo")
    
    print("开始构建过程...")
    run_command(build_command)

    print("运行测试...")
    run_command(test_command)

    print("CI流程完成！")

if __name__ == "__main__":
    main()
