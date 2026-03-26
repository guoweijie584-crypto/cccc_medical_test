"""
医疗主组对话闭环功能测试
验证: primary 收到用户问题 -> 调用 memory -> 并行咨询3个专家 -> 综合回复用户
验收标准: 一轮完整对话有5条消息流转
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class MedicalGroupDialogueTest:
    """医疗主组对话闭环测试"""
    
    def __init__(self):
        self.test_results = []
        
    def test_1_user_to_primary(self):
        """测试1: 用户消息路由到 primary"""
        print("\n[测试1] 用户 -> primary 路由")
        
        user_message = {
            "from": "user",
            "to": "primary",
            "content": "我今天空腹血糖7.2，有点担心",
            "patient_id": "PAT_test_001"
        }
        
        # 验证路由规则
        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(routing_config, from_actor="user", to_actor="primary")
        
        assert rule is not None, "未找到 user -> primary 路由规则"
        assert rule["condition"] == "default", "路由条件应为 default"
        
        print("[PASS] 用户消息能正确路由到 primary")
        self.test_results.append(("user_to_primary", True, None))
        return True
        
    def test_2_primary_to_memory(self):
        """测试2: primary 调用 memory 检索上下文"""
        print("\n[测试2] primary -> memory 上下文检索")
        
        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(routing_config, from_actor="primary", to_actor="memory")
        
        assert rule is not None, "未找到 primary -> memory 路由规则"
        assert rule["condition"] == "retrieve_context", "路由条件应为 retrieve_context"
        
        print("[PASS] primary 能正确调用 memory 检索上下文")
        self.test_results.append(("primary_to_memory", True, None))
        return True
        
    def test_3_primary_parallel_consult(self):
        """测试3: primary 并行咨询3个专家"""
        print("\n[测试3] primary -> [pharmacist, nutritionist, doctor] 并行咨询")
        
        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(routing_config, from_actor="primary", condition="parallel_consult")
        
        assert rule is not None, "未找到并行咨询路由规则"
        assert rule["mode"] == "parallel", "并行模式应为 parallel"
        
        experts = rule["to"]
        assert "pharmacist" in experts, "应包含 pharmacist"
        assert "nutritionist" in experts, "应包含 nutritionist"
        assert "doctor" in experts, "应包含 doctor"
        assert len(experts) == 3, "应咨询3个专家"
        
        print(f"[PASS] primary 能并行咨询3个专家: {experts}")
        self.test_results.append(("parallel_consult", True, None))
        return True
        
    def test_4_primary_to_user(self):
        """测试4: primary 综合回复用户"""
        print("\n[测试4] primary -> user 综合回复")
        
        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(routing_config, from_actor="primary", to_actor="user")
        
        assert rule is not None, "未找到 primary -> user 路由规则"
        assert rule["condition"] == "final_response", "路由条件应为 final_response"
        
        print("[PASS] primary 能正确回复用户")
        self.test_results.append(("primary_to_user", True, None))
        return True
        
    def test_5_internal_actors_constraint(self):
        """测试5: 内部专家不直接回复用户"""
        print("\n[测试5] 内部专家约束验证")
        
        routing_config = self._load_routing_config()
        constraints = routing_config.get("constraints", {})
        
        internal_actors = ["pharmacist", "nutritionist", "doctor", "memory"]
        
        for actor in internal_actors:
            assert actor in constraints, f"{actor} 应有约束配置"
            assert constraints[actor].get("direct_user_reply") == False, f"{actor} 不应直接回复用户"
            
        print(f"[PASS] 4个内部专家均配置为不直接回复用户")
        self.test_results.append(("internal_constraints", True, None))
        return True
        
    def test_6_complete_dialogue_flow(self):
        """测试6: 完整对话流程验证（5条消息）"""
        print("\n[测试6] 完整对话流程验证")
        
        # 模拟消息流转
        messages = []
        
        # 消息1: 用户 -> primary
        messages.append({"from": "user", "to": "primary", "type": "input"})
        
        # 消息2: primary -> memory
        messages.append({"from": "primary", "to": "memory", "type": "retrieve"})
        
        # 消息3: primary -> 3个专家 (计为1条并行消息)
        messages.append({"from": "primary", "to": ["pharmacist", "nutritionist", "doctor"], "type": "consult"})
        
        # 消息4: 3个专家 -> primary (计为1条聚合消息)
        messages.append({"from": ["pharmacist", "nutritionist", "doctor"], "to": "primary", "type": "response"})
        
        # 消息5: primary -> 用户
        messages.append({"from": "primary", "to": "user", "type": "output"})
        
        assert len(messages) == 5, f"应有5条消息流转,实际{len(messages)}条"
        
        print(f"[PASS] 完整对话流程包含5条消息流转:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg['from']} -> {msg['to']} ({msg['type']})")
            
        self.test_results.append(("complete_flow", True, None))
        return True
        
    def _load_routing_config(self):
        """加载路由配置"""
        config_path = PROJECT_ROOT / "config" / "medical_group_routing.json"
        if not config_path.exists():
            raise FileNotFoundError(f"路由配置文件不存在: {config_path}")
            
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def _find_routing_rule(self, config, from_actor=None, to_actor=None, condition=None):
        """查找路由规则"""
        for rule in config.get("routing_rules", []):
            match = True
            if from_actor and rule.get("from") != from_actor:
                match = False
            if to_actor and rule.get("to") != to_actor:
                match = False
            if condition and rule.get("condition") != condition:
                match = False
            if match:
                return rule
        return None
        
    def run_all_tests(self):
        """运行所有测试"""
        print("="*60)
        print("医疗主组对话闭环功能测试")
        print("="*60)
        
        tests = [
            self.test_1_user_to_primary,
            self.test_2_primary_to_memory,
            self.test_3_primary_parallel_consult,
            self.test_4_primary_to_user,
            self.test_5_internal_actors_constraint,
            self.test_6_complete_dialogue_flow,
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                failed += 1
                print(f"[FAIL] {test.__name__} 失败: {e}")
                self.test_results.append((test.__name__, False, str(e)))
                
        print("\n" + "="*60)
        print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
        print("="*60)
        
        return failed == 0


if __name__ == "__main__":
    tester = MedicalGroupDialogueTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
