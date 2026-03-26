"""
血糖管理 Agent 自进化系统 - 主入口

启动命令:
    python main.py

环境要求:
    - Python 3.10+
    - Memory Palace 服务已启动
    - LLM API Key 已配置
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加 src 到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.memory import MemoryAgent, get_memory_agent
from config.settings import (
    MEMORY_PALACE_URL,
    PATIENT_DATA_FILE,
    AGENT_CONFIG
)


def load_patient_data(patient_id: Optional[str] = None) -> Dict:
    """加载患者数据"""
    if not PATIENT_DATA_FILE.exists():
        print(f"[Error] 患者数据文件不存在: {PATIENT_DATA_FILE}")
        return {}
    
    try:
        with open(PATIENT_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if patient_id:
            for patient in data:
                if patient.get("患者UUID") == patient_id:
                    return patient
            return {}
        return data
    except Exception as e:
        print(f"[Error] 加载患者数据失败: {e}")
        return {}


def test_memory_agent():
    """测试 Memory Agent 功能"""
    print("=" * 60)
    print("血糖管理 Agent 自进化系统 - 功能测试")
    print("=" * 60)
    
    # 1. 初始化 Memory Agent
    print("\n[1/4] 初始化 Memory Agent...")
    try:
        agent = get_memory_agent()
        print("[OK] Memory Agent 初始化成功")
    except Exception as e:
        print(f"[FAIL] Memory Agent 初始化失败: {e}")
        return False
    
    # 2. 加载患者数据
    print("\n[2/4] 加载患者数据...")
    patients = load_patient_data()
    if not patients:
        print("[FAIL] 患者数据加载失败")
        return False
    print(f"[OK] 加载了 {len(patients)} 位患者数据")
    
    # 3. 测试患者上下文检索
    print("\n[3/4] 测试患者上下文检索...")
    test_patient = patients[0]
    patient_id = test_patient.get("患者UUID", "unknown")
    
    try:
        context = agent.retrieve_patient_context(
            patient_id=patient_id,
            query="血糖控制"
        )
        print(f"[OK] 成功检索患者 {patient_id} 的上下文")
        print(f"  - 患者画像: {'有' if context.get('profile') else '无'}")
        print(f"  - 近期记忆: {len(context.get('recent_memories', []))} 条")
    except Exception as e:
        print(f"[FAIL] 上下文检索失败: {e}")
    
    # 4. 测试记忆存储
    print("\n[4/4] 测试记忆存储...")
    try:
        uris = agent.extract_and_store(
            patient_id=patient_id,
            dialogue={"turn": 1, "speaker": "patient", "content": "测试对话"},
            extracted_facts=[
                {
                    "category": "test",
                    "content": "系统测试记录",
                    "importance": "normal"
                }
            ]
        )
        print(f"[OK] 成功存储 {len(uris)} 条记忆")
    except Exception as e:
        print(f"[FAIL] 记忆存储失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    return True


def print_system_info():
    """打印系统信息"""
    print("\n系统配置:")
    print(f"  Memory Palace: {MEMORY_PALACE_URL}")
    print(f"  患者数据: {PATIENT_DATA_FILE}")
    print(f"  Agent 数量: {len(AGENT_CONFIG)}")
    
    print("\nAgent 列表:")
    for key, config in AGENT_CONFIG.items():
        print(f"  - {config['name_zh']} ({key}): {config['role']}")


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="血糖管理 Agent 自进化系统")
    parser.add_argument("--test", action="store_true", help="运行功能测试")
    parser.add_argument("--info", action="store_true", help="显示系统信息")
    
    args = parser.parse_args()
    
    if args.test:
        test_memory_agent()
    elif args.info:
        print_system_info()
    else:
        print("血糖管理 Agent 自进化系统")
        print("\n使用方法:")
        print("  python main.py --test    运行功能测试")
        print("  python main.py --info    显示系统信息")
        print("\n请确保:")
        print("  1. Memory Palace 服务已启动 (python -m backend.main)")
        print("  2. 环境变量 LLM_API_KEY 已设置")


if __name__ == "__main__":
    main()
