"""
阶段一验收测试 - Memory Palace 桥接 (同步版本)
使用实际的 Memory Agent API
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入 Memory Agent
try:
    from src.memory import MemoryAgent, get_memory_agent
    MEMORY_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"[警告] 无法导入 Memory Agent: {e}")
    MEMORY_AGENT_AVAILABLE = False


class Phase1AcceptanceTests:
    """阶段一验收测试套件"""
    
    def __init__(self):
        self.results = []
        self.agent: Optional[MemoryAgent] = None
    
    def setup(self):
        """测试前准备"""
        if MEMORY_AGENT_AVAILABLE:
            try:
                self.agent = get_memory_agent()
                print("[准备] Memory Agent 初始化成功")
            except Exception as e:
                print(f"[警告] Memory Agent 初始化失败: {e}")
                self.agent = None
    
    def test_memory_agent_initialization(self) -> Dict[str, Any]:
        """
        测试 1: Memory Agent 初始化
        """
        test_name = "Memory Agent 初始化"
        print(f"\n[测试] {test_name}...")
        
        if not MEMORY_AGENT_AVAILABLE:
            result = {
                "test": test_name,
                "status": "SKIP",
                "message": "Memory Agent 模块不可用",
                "details": {}
            }
        elif self.agent is None:
            result = {
                "test": test_name,
                "status": "FAIL",
                "message": "Memory Agent 初始化失败",
                "details": {}
            }
        else:
            result = {
                "test": test_name,
                "status": "PASS",
                "message": "Memory Agent 初始化成功",
                "details": {"agent_type": type(self.agent).__name__}
            }
        
        self.results.append(result)
        print(f"  [{result['status']}] {result['message']}")
        return result
    
    def test_retrieve_patient_context(self) -> Dict[str, Any]:
        """
        测试 2: 检索患者上下文
        - 使用 build_agent_context 获取患者信息
        """
        test_name = "检索患者上下文"
        print(f"\n[测试] {test_name}...")
        
        if not self.agent:
            result = {
                "test": test_name,
                "status": "SKIP",
                "message": "Memory Agent 未初始化",
                "details": {}
            }
        else:
            try:
                # 测试构建患者上下文
                context = self.agent.build_agent_context(
                    patient_id="PAT_test_001",
                    agent_type="pharmacist",
                    current_query="二甲双胍剂量"
                )
                
                result = {
                    "test": test_name,
                    "status": "PASS",
                    "message": "患者上下文检索成功",
                    "details": {
                        "context_length": len(context) if isinstance(context, str) else "N/A",
                        "context_preview": context[:200] if isinstance(context, str) else str(context)[:200]
                    }
                }
            except Exception as e:
                result = {
                    "test": test_name,
                    "status": "FAIL",
                    "message": f"检索失败: {e}",
                    "details": {}
                }
        
        self.results.append(result)
        print(f"  [{result['status']}] {result['message']}")
        return result
    
    def test_extract_and_store(self) -> Dict[str, Any]:
        """
        测试 3: 提取并存储记忆
        - 模拟对话后提取关键信息并存储
        """
        test_name = "提取并存储记忆"
        print(f"\n[测试] {test_name}...")
        
        if not self.agent:
            result = {
                "test": test_name,
                "status": "SKIP",
                "message": "Memory Agent 未初始化",
                "details": {}
            }
        else:
            try:
                # 模拟对话数据
                dialogue = {
                    "patient_id": "PAT_test_001",
                    "question": "我的血糖有点高，需要调整药物吗？",
                    "answer": "根据您最近的血糖记录，建议将二甲双胍从500mg增加到850mg。",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                
                extracted_facts = [
                    "患者目前服用二甲双胍500mg",
                    "建议增加到850mg",
                    "原因：近期血糖控制不佳"
                ]
                
                uris = self.agent.extract_and_store(
                    patient_id="PAT_test_001",
                    dialogue=dialogue,
                    extracted_facts=extracted_facts
                )
                
                result = {
                    "test": test_name,
                    "status": "PASS",
                    "message": "记忆提取和存储成功",
                    "details": {
                        "stored_uris_count": len(uris) if isinstance(uris, list) else 1,
                        "facts_extracted": len(extracted_facts)
                    }
                }
            except Exception as e:
                result = {
                    "test": test_name,
                    "status": "FAIL",
                    "message": f"存储失败: {e}",
                    "details": {}
                }
        
        self.results.append(result)
        print(f"  [{result['status']}] {result['message']}")
        return result
    
    def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """
        测试 4: 端到端工作流
        - 完整流程：检索 → 构建上下文 → 模拟回答 → 存储记忆
        """
        test_name = "端到端工作流"
        print(f"\n[测试] {test_name}...")
        
        if not self.agent:
            result = {
                "test": test_name,
                "status": "SKIP",
                "message": "Memory Agent 未初始化",
                "details": {}
            }
        else:
            try:
                start_time = time.time()
                
                # 1. 构建上下文
                context = self.agent.build_agent_context(
                    patient_id="PAT_test_002",
                    agent_type="primary",
                    current_query="我应该怎么调整饮食？"
                )
                
                # 2. 模拟对话
                dialogue = {
                    "patient_id": "PAT_test_002",
                    "question": "我应该怎么调整饮食？",
                    "answer": "建议减少碳水化合物摄入，增加膳食纤维。",
                    "context_used": context[:100] if isinstance(context, str) else "N/A"
                }
                
                # 3. 存储记忆
                uris = self.agent.extract_and_store(
                    patient_id="PAT_test_002",
                    dialogue=dialogue,
                    extracted_facts=["建议减少碳水化合物", "增加膳食纤维"]
                )
                
                elapsed = time.time() - start_time
                
                result = {
                    "test": test_name,
                    "status": "PASS",
                    "message": "端到端流程完成",
                    "details": {
                        "total_time_ms": round(elapsed * 1000, 2),
                        "flow_steps": ["build_context", "dialogue", "store_memory"]
                    }
                }
            except Exception as e:
                result = {
                    "test": test_name,
                    "status": "FAIL",
                    "message": f"流程失败: {e}",
                    "details": {}
                }
        
        self.results.append(result)
        print(f"  [{result['status']}] {result['message']}")
        return result
    
    def test_integration_with_evaluation_dataset(self) -> Dict[str, Any]:
        """
        测试 5: 与评测数据集集成
        - 使用真实测试用例验证上下文组装
        """
        test_name = "评测数据集集成"
        print(f"\n[测试] {test_name}...")
        
        try:
            # 加载评测数据集
            dataset_path = Path(__file__).parent / "evaluation_dataset_v2.json"
            if not dataset_path.exists():
                result = {
                    "test": test_name,
                    "status": "SKIP",
                    "message": "评测数据集文件不存在",
                    "details": {}
                }
            else:
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    dataset = json.load(f)
                
                test_cases = dataset.get('test_cases', [])
                sample_cases = test_cases[:3]  # 取前3条测试
                
                if self.agent:
                    for case in sample_cases:
                        patient_id = case.get('patient_reference', 'PAT_unknown')
                        question = case.get('question', '')
                        
                        # 尝试构建上下文
                        context = self.agent.build_agent_context(
                            patient_id=patient_id,
                            agent_type="primary",
                            current_query=question
                        )
                
                result = {
                    "test": test_name,
                    "status": "PASS",
                    "message": f"成功加载 {len(test_cases)} 条测试用例",
                    "details": {
                        "total_test_cases": len(test_cases),
                        "categories": list(set(c.get('category') for c in test_cases)),
                        "sample_tested": len(sample_cases)
                    }
                }
        except Exception as e:
            result = {
                "test": test_name,
                "status": "FAIL",
                "message": f"集成测试失败: {e}",
                "details": {}
            }
        
        self.results.append(result)
        print(f"  [{result['status']}] {result['message']}")
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有验收测试"""
        print("=" * 60)
        print("阶段一验收测试 - Memory Palace 桥接")
        print("=" * 60)
        
        # 准备
        self.setup()
        
        start_time = time.time()
        
        # 依次运行所有测试
        self.test_memory_agent_initialization()
        self.test_retrieve_patient_context()
        self.test_extract_and_store()
        self.test_end_to_end_workflow()
        self.test_integration_with_evaluation_dataset()
        
        elapsed_time = time.time() - start_time
        
        # 生成报告
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        skipped = sum(1 for r in self.results if r['status'] == 'SKIP')
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": len(self.results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": f"{passed/(len(self.results)-skipped)*100:.1f}%" if (len(self.results)-skipped) > 0 else "N/A",
                "elapsed_time_sec": round(elapsed_time, 2)
            },
            "details": self.results
        }
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("测试摘要")
        print("=" * 60)
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"通过: {report['summary']['passed']}")
        print(f"失败: {report['summary']['failed']}")
        print(f"跳过: {report['summary']['skipped']}")
        print(f"通过率: {report['summary']['pass_rate']}")
        print(f"耗时: {report['summary']['elapsed_time_sec']} 秒")
        
        # 保存报告
        report_path = Path(__file__).parent / "phase1_acceptance_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存到: {report_path}")
        
        return report


def main():
    """主函数"""
    tester = Phase1AcceptanceTests()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
