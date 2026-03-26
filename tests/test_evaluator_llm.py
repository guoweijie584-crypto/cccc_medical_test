"""
测试 Evaluator LLM 评估功能
"""

import sys
import os

# Import directly to avoid broken config/__init__.py chain (EVAL_DATA_DIR missing)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_root, 'src')
sys.path.insert(0, os.path.join(_src, 'evolution'))
sys.path.insert(0, _src)
sys.path.insert(0, _root)

from evaluator import EvaluatorAgent, ResponseScore, MemoryScore
from llm_client import LLMClient


def test_evaluator_with_llm():
    """测试 LLM 评估（需要 API key）"""
    print("\n=== 测试 LLM 评估 ===")

    # 初始化 Evaluator
    llm_client = LLMClient()
    evaluator = EvaluatorAgent(llm_client=llm_client)

    # 测试数据
    patient_id = "PAT_001"
    query = "我今天空腹血糖8.5，餐后2小时12.3，是不是控制得不好？"
    response = """根据您的血糖数据，空腹8.5 mmol/L略高于理想范围（4.4-7.0），餐后12.3 mmol/L也超过了目标值（<10.0）。

建议：
1. 饮食方面：减少精制碳水化合物，增加膳食纤维
2. 用药方面：建议咨询医生是否需要调整用药剂量
3. 监测：建议每天监测2-3次血糖，观察趋势

请注意：如血糖持续高于13.9或出现不适，请及时就医。"""

    expert_opinions = {
        "药剂师": "建议检查当前用药依从性，可能需要调整剂量",
        "营养师": "建议控制每餐碳水化合物摄入，选择低GI食物",
        "代谢病医生": "血糖控制欠佳，建议1个月内复查糖化血红蛋白"
    }

    patient_context = {
        "profile": "患者ID: PAT_001, 年龄: 55岁, 性别: 男, 糖尿病类型: 2型, 发现时间: 2020年"
    }

    # 测试回答评估
    print("\n[1] 测试回答质量评估")
    response_score = evaluator.evaluate_response(
        patient_id=patient_id,
        query=query,
        response=response,
        expert_opinions=expert_opinions,
        patient_context=patient_context,
        use_llm=True
    )

    print(f"  医学准确性: {response_score.medical_accuracy}/10")
    print(f"  安全性: {response_score.safety}/10")
    print(f"  完整性: {response_score.completeness}/10")
    print(f"  个性化: {response_score.personalization}/10")
    print(f"  一致性: {response_score.consistency}/10")
    print(f"  综合得分: {response_score.overall}/10")
    print(f"  评语: {response_score.comments}")
    if response_score.issues:
        print(f"  发现问题: {response_score.issues}")

    # 测试记忆评估
    print("\n[2] 测试记忆质量评估")
    memories = [
        {
            "category": "glucose",
            "content": {"value": 8.5, "type": "空腹", "timestamp": "2024-03-25 08:00"},
            "timestamp": "2024-03-25T08:00:00"
        },
        {
            "category": "medication",
            "content": {"drug": "二甲双胍", "dose": "500mg", "frequency": "每日2次"},
            "timestamp": "2024-03-20T10:00:00"
        },
        {
            "category": "diet",
            "content": {"meal": "早餐", "items": "燕麦粥+鸡蛋"},
            "timestamp": "2024-03-25T07:30:00"
        }
    ]

    patient_data = {
        "patient_id": "PAT_001",
        "age": 55,
        "diabetes_type": "2型",
        "diagnosis_date": "2020-01-15"
    }

    memory_score = evaluator.evaluate_memory(
        patient_id=patient_id,
        memories=memories,
        patient_data=patient_data,
        use_llm=True
    )

    print(f"  完整性: {memory_score.completeness}/10")
    print(f"  准确性: {memory_score.accuracy}/10")
    print(f"  时效性: {memory_score.timeliness}/10")
    print(f"  相关性: {memory_score.relevance}/10")
    print(f"  结构性: {memory_score.structure}/10")
    print(f"  综合得分: {memory_score.overall}/10")
    print(f"  评语: {memory_score.comments}")
    if memory_score.issues:
        print(f"  发现问题: {memory_score.issues}")

    print("\n[PASS] LLM 评估测试完成")


def test_evaluator_fallback():
    """测试无 API key 时的 fallback"""
    print("\n=== 测试 Fallback 机制 ===")

    # 创建无 API key 的客户端
    llm_client = LLMClient(api_key="")
    evaluator = EvaluatorAgent(llm_client=llm_client)

    # 测试数据
    query = "我今天血糖有点高"
    response = "建议控制饮食，定期监测血糖"
    expert_opinions = {"药剂师": "注意用药", "营养师": "控制碳水"}
    patient_context = {"profile": "患者基本信息"}

    print("\n[1] 测试回答评估 fallback")
    response_score = evaluator.evaluate_response(
        patient_id="PAT_001",
        query=query,
        response=response,
        expert_opinions=expert_opinions,
        patient_context=patient_context,
        use_llm=True  # 即使设置 use_llm=True，也会 fallback 到规则评估
    )

    print(f"  综合得分: {response_score.overall}/10")
    print(f"  评语: {response_score.comments}")

    print("\n[2] 测试记忆评估 fallback")
    memories = [{"category": "glucose", "content": "血糖记录"}]
    memory_score = evaluator.evaluate_memory(
        patient_id="PAT_001",
        memories=memories,
        patient_data={},
        use_llm=True
    )

    print(f"  综合得分: {memory_score.overall}/10")
    print(f"  评语: {memory_score.comments}")

    print("\n[PASS] Fallback 测试完成")


def test_score_range_validation():
    """测试评分范围验证"""
    print("\n=== 测试评分范围验证 ===")

    evaluator = EvaluatorAgent()

    # 模拟 LLM 返回超出范围的分数
    llm_result = """{
        "medical_accuracy": 15.0,
        "safety": -2.0,
        "completeness": 8.0,
        "personalization": 12.0,
        "consistency": 5.0,
        "comments": "测试超出范围的分数",
        "issues": []
    }"""

    score = evaluator._parse_llm_response_score(llm_result)

    print(f"  medical_accuracy (原15.0): {score.medical_accuracy}")
    print(f"  safety (原-2.0): {score.safety}")
    print(f"  personalization (原12.0): {score.personalization}")

    # 验证分数被限制在 0-10 范围内
    assert 0 <= score.medical_accuracy <= 10, "medical_accuracy 超出范围"
    assert 0 <= score.safety <= 10, "safety 超出范围"
    assert 0 <= score.personalization <= 10, "personalization 超出范围"

    print("\n[PASS] 评分范围验证通过")


if __name__ == "__main__":
    print("=" * 60)
    print("Evaluator LLM 功能测试")
    print("=" * 60)

    # 测试 1: Fallback 机制（不需要 API key）
    test_evaluator_fallback()

    # 测试 2: 评分范围验证
    test_score_range_validation()

    # 测试 3: LLM 评估（需要 API key）
    llm_client = LLMClient()
    if llm_client.api_key:
        print("\n检测到 API key，运行 LLM 评估测试...")
        test_evaluator_with_llm()
    else:
        print("\n未检测到 API key，跳过 LLM 评估测试")
        print("提示：设置环境变量 LLM_API_KEY 可启用 LLM 评估测试")

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)
