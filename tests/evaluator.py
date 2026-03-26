"""
血糖管理 Agent 评测脚本
- 运行测试集
- 评估回答质量
- 生成对比报告
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class EvaluationResult:
    """单个测试用例的评估结果"""
    test_id: str
    category: str
    question: str
    agent_response: str
    
    # 评分 (0-10)
    medical_accuracy: float = 0.0  # 医学准确性
    safety: float = 0.0  # 安全性
    completeness: float = 0.0  # 完整性
    personalization: float = 0.0  # 个性化
    consistency: float = 0.0  # 一致性
    
    # 评估详情
    matched_points: List[str] = field(default_factory=list)
    missed_points: List[str] = field(default_factory=list)
    hallucinations: List[str] = field(default_factory=list)
    safety_warnings: List[str] = field(default_factory=list)
    
    @property
    def total_score(self) -> float:
        """加权总分"""
        weights = {
            'medical_accuracy': 0.3,
            'safety': 0.25,
            'completeness': 0.2,
            'personalization': 0.15,
            'consistency': 0.1
        }
        return (
            self.medical_accuracy * weights['medical_accuracy'] +
            self.safety * weights['safety'] +
            self.completeness * weights['completeness'] +
            self.personalization * weights['personalization'] +
            self.consistency * weights['consistency']
        )


class AgentEvaluator:
    """Agent 回答质量评估器"""
    
    def __init__(self, test_data_path: str):
        self.test_data = self._load_test_data(test_data_path)
        
    def _load_test_data(self, path: str) -> List[Dict]:
        """加载测试数据集"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('test_cases', [])
    
    def evaluate_response(
        self,
        test_case: Dict,
        agent_response: str,
        memory_context: Optional[Dict] = None
    ) -> EvaluationResult:
        """
        评估 Agent 对单个测试用例的回答
        
        TODO: 实现 LLM-based 自动评估逻辑
        - 使用 Evaluator Agent 或规则匹配
        - 检查 expected_answer_points 覆盖度
        - 检测幻觉和安全问题
        """
        result = EvaluationResult(
            test_id=test_case['id'],
            category=test_case['category'],
            question=test_case['question'],
            agent_response=agent_response
        )
        
        # 占位符：实际实现需要调用 Evaluator Agent
        # 或使用规则匹配算法
        result.medical_accuracy = 0.0  # 待实现
        result.safety = 0.0
        result.completeness = 0.0
        result.personalization = 0.0
        result.consistency = 0.0
        
        return result
    
    def run_evaluation(
        self,
        agent_callable,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        运行完整评测
        
        Args:
            agent_callable: 接受 (patient_profile, question) 返回回答的可调用对象
            output_path: 结果输出路径
        """
        results = []
        
        for test_case in self.test_data:
            print(f"\n[评测] {test_case['id']}: {test_case['question'][:40]}...")
            
            # 调用 Agent 获取回答
            patient_profile = test_case.get('patient_profile', {})
            question = test_case['question']
            
            try:
                agent_response = agent_callable(patient_profile, question)
            except Exception as e:
                print(f"  [错误] Agent 调用失败: {e}")
                agent_response = f"[ERROR] {str(e)}"
            
            # 评估回答
            result = self.evaluate_response(test_case, agent_response)
            results.append(result)
            
            print(f"  [得分] {result.total_score:.2f}/10")
        
        # 生成报告
        report = self._generate_report(results)
        
        if output_path:
            self._save_report(report, output_path)
        
        return report
    
    def _generate_report(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """生成评测报告"""
        if not results:
            return {}
        
        # 总体统计
        total_score = sum(r.total_score for r in results) / len(results)
        
        # 按类别统计
        category_scores = {}
        for r in results:
            cat = r.category
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(r.total_score)
        
        category_avg = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_scores.items()
        }
        
        # 详细结果
        details = [
            {
                'test_id': r.test_id,
                'category': r.category,
                'question': r.question,
                'total_score': r.total_score,
                'medical_accuracy': r.medical_accuracy,
                'safety': r.safety,
                'completeness': r.completeness,
                'personalization': r.personalization,
                'consistency': r.consistency
            }
            for r in results
        ]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_cases': len(results),
                'average_score': round(total_score, 2),
                'category_scores': category_avg
            },
            'details': details
        }
    
    def _save_report(self, report: Dict, path: str):
        """保存报告到文件"""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n[报告] 已保存到: {path}")


class IterationComparator:
    """多轮迭代结果对比器"""
    
    @staticmethod
    def compare_iterations(
        baseline_report: Dict,
        current_report: Dict
    ) -> Dict[str, Any]:
        """
        对比两轮评测结果
        
        Returns:
            包含改进/退化指标的字典
        """
        baseline_avg = baseline_report['summary']['average_score']
        current_avg = current_report['summary']['average_score']
        
        improvement = current_avg - baseline_avg
        
        return {
            'baseline_score': baseline_avg,
            'current_score': current_avg,
            'improvement': round(improvement, 2),
            'improvement_pct': round(improvement / baseline_avg * 100, 1) if baseline_avg > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }


def mock_agent_call(patient_profile: Dict, question: str) -> str:
    """
    Mock Agent 调用（用于测试框架）
    
    TODO: 替换为实际 Agent 调用
    """
    return f"[MOCK] 这是模拟回答。患者年龄{patient_profile.get('age')}岁，问题：{question[:20]}..."


if __name__ == '__main__':
    # 示例用法
    print("=" * 50)
    print("血糖管理 Agent 评测脚本")
    print("=" * 50)
    
    # 初始化评估器
    evaluator = AgentEvaluator('evaluation_schema.json')
    
    # 运行评测（使用 mock）
    report = evaluator.run_evaluation(
        agent_callable=mock_agent_call,
        output_path='evaluation_report.json'
    )
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("评测摘要")
    print("=" * 50)
    print(f"测试用例数: {report['summary']['total_cases']}")
    print(f"平均得分: {report['summary']['average_score']:.2f}/10")
    print("\n按类别得分:")
    for cat, score in report['summary']['category_scores'].items():
        print(f"  {cat}: {score:.2f}")
