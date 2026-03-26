"""
阶段二测试 - Agent 系统测试（同步版本）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import (
    GlucoseManagementWorkflow,
    process_glucose_query,
    MockPrimaryAgent,
    MockPharmacistAgent,
    MockNutritionistAgent,
    MockDoctorAgent,
)


def test_single_agent():
    """测试单个 Agent"""
    print("=" * 50)
    print("测试单个 Agent")
    print("=" * 50)
    
    context = """## 患者画像
患者ID: PAT_test_001
姓名: 张三
年龄: 45岁
糖尿病类型: 2型
发现时间: 2019年

## 相关历史记录
- 当前用药：二甲双胍 500mg bid
- 近期空腹血糖 7.2-8.5 mmol/L
"""
    
    query = "二甲双胍可以和格列美脲一起吃吗？"
    
    # 测试药剂师
    pharmacist = MockPharmacistAgent()
    result = pharmacist.process_sync(context, query)
    print(f"\n【药剂师】")
    print(result["response"][:200] + "...")
    
    # 测试营养师
    nutritionist = MockNutritionistAgent()
    query2 = "餐后血糖高，应该怎么调整饮食？"
    result = nutritionist.process_sync(context, query2)
    print(f"\n【营养师】")
    print(result["response"][:200] + "...")
    
    # 测试代谢病医生
    doctor = MockDoctorAgent()
    query3 = "最近空腹血糖一直8左右，需要调整治疗吗？"
    result = doctor.process_sync(context, query3)
    print(f"\n【代谢病医生】")
    print(result["response"][:200] + "...")
    
    # 测试主治医生
    primary = MockPrimaryAgent()
    expert_opinions = {
        "药剂师": "二甲双胍和格列美脲可以联用，但需注意低血糖风险。",
        "营养师": "建议控制碳水摄入，增加膳食纤维。",
        "代谢病医生": "血糖控制尚可，建议继续当前方案。"
    }
    result = primary.process_sync(context, query, expert_opinions=expert_opinions)
    print(f"\n【主治医生 - 综合】")
    print(result["response"][:200] + "...")
    
    print("\n[OK] 单个 Agent 测试通过")
    return True


def test_workflow():
    """测试完整工作流"""
    print("\n" + "=" * 50)
    print("测试完整工作流")
    print("=" * 50)
    
    workflow = GlucoseManagementWorkflow(use_mock=True)
    
    test_cases = [
        {
            "patient_id": "PAT_test_001",
            "query": "我最近空腹血糖一直在8左右，是不是控制得不好？需要调整药吗？"
        },
        {
            "patient_id": "PAT_test_002",
            "query": "吃二甲双胍总是胃不舒服，可以改成饭后吃吗？"
        },
        {
            "patient_id": "PAT_test_003",
            "query": "我早餐可以吃稀饭吗？听说升糖很快。"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i} ---")
        print(f"问题: {case['query']}")
        
        result = workflow.process_patient_query(
            patient_id=case["patient_id"],
            query=case["query"],
            enable_parallel=False  # 串行避免线程问题
        )
        
        print(f"\n【综合回答】")
        print(result["primary_response"][:300] + "...")
        print(f"\n处理时间: {result['processing_time']:.2f}s")
    
    print("\n[OK] 工作流测试通过")
    return True


def test_batch_processing():
    """测试批量处理"""
    print("\n" + "=" * 50)
    print("测试批量处理")
    print("=" * 50)
    
    workflow = GlucoseManagementWorkflow(use_mock=True)
    
    queries = [
        {"patient_id": "PAT_001", "query": "血糖控制目标是多少？"},
        {"patient_id": "PAT_002", "query": "胰岛素忘记打了怎么办？"},
        {"patient_id": "PAT_003", "query": "可以吃水果吗？"},
    ]
    
    results = workflow.process_batch(queries, enable_parallel=False)
    
    print(f"成功处理 {len(results)} 个查询")
    for i, result in enumerate(results):
        print(f"  查询{i+1}: {result['processing_time']:.2f}s")
    
    print("\n[OK] 批量处理测试通过")
    return True


def test_quick_function():
    """测试快捷函数"""
    print("\n" + "=" * 50)
    print("测试快捷函数")
    print("=" * 50)
    
    result = process_glucose_query(
        patient_id="PAT_quick_test",
        query="我最近血糖有点高，是不是吃太多了？",
        use_mock=True
    )
    
    print(f"查询: {result['query']}")
    print(f"处理时间: {result['processing_time']:.2f}s")
    print(f"\n【回答】")
    print(result["primary_response"][:300] + "...")
    
    print("\n[OK] 快捷函数测试通过")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("阶段二 Agent 系统测试（同步版本）")
    print("=" * 50)
    
    try:
        test_single_agent()
        test_workflow()
        test_batch_processing()
        test_quick_function()
        
        print("\n" + "=" * 50)
        print("[OK] 所有测试通过！")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
