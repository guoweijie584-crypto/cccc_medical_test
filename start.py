"""
一键启动脚本

功能：
1. 检查环境
2. 启动 Memory Palace 服务
3. 初始化系统
4. 运行测试
"""

import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
MEMORY_PALACE_DIR = PROJECT_ROOT / "Memory-Palace-main"


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("[错误] 需要 Python 3.10+")
        return False
    print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_env():
    """检查环境变量"""
    required = ["LLM_API_KEY"]
    missing = []
    
    for var in required:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"[警告] 缺少环境变量: {', '.join(missing)}")
        print("  请在 .env 文件中设置或导出环境变量")
        return False
    
    print("[OK] 环境变量检查通过")
    return True


def start_memory_palace():
    """启动 Memory Palace 服务"""
    print("\n[1/3] 启动 Memory Palace 服务...")
    
    # 检查是否已经运行
    try:
        import httpx
        response = httpx.get("http://127.0.0.1:8000/health", timeout=2)
        if response.status_code == 200:
            print("  [OK] Memory Palace 已在运行")
            return True
    except:
        pass
    
    # 启动服务
    backend_dir = MEMORY_PALACE_DIR / "backend"
    if not backend_dir.exists():
        print(f"  [错误] 找不到 Memory Palace: {backend_dir}")
        return False
    
    print("  正在启动服务...")
    # 注意：这里只是演示，实际需要用 subprocess 启动并保持运行
    print(f"  请手动运行: cd {backend_dir} && python main.py")
    print("  或者: cd {backend_dir} && uvicorn main:app --host 127.0.0.1 --port 8000")
    
    return True


def init_system():
    """初始化系统"""
    print("\n[2/3] 初始化系统...")
    
    # 检查目录结构
    dirs = ["src", "config", "data", "logs", "prompts"]
    for d in dirs:
        dir_path = PROJECT_ROOT / d
        dir_path.mkdir(exist_ok=True)
    
    print("  [OK] 目录结构检查完成")
    return True


def run_tests():
    """运行测试"""
    print("\n[3/3] 运行功能测试...")
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--test"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            return False
        return True
    except Exception as e:
        print(f"  [错误] 测试运行失败: {e}")
        return False


def main():
    """主流程"""
    print("=" * 60)
    print("血糖管理 Agent 自进化系统 - 一键启动")
    print("=" * 60)
    
    # 检查环境
    if not check_python_version():
        return 1
    
    check_env()
    
    # 初始化
    if not init_system():
        return 1
    
    # 启动 Memory Palace
    if not start_memory_palace():
        return 1
    
    print("\n" + "=" * 60)
    print("启动完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 确保 Memory Palace 服务已启动")
    print("  2. 运行测试: python main.py --test")
    print("  3. 查看信息: python main.py --info")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
