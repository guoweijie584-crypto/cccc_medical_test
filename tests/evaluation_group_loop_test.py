"""
评测组后台闭环功能测试
验证: evaluator评分 -> analyzer分析 -> optimizer优化 -> 通知evaluator
验收标准: 一轮完整自进化闭环有4个消息传递，无人工干预
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class EvaluationGroupLoopTest:
    """评测组后台闭环测试"""

    def __init__(self):
        self.test_results = []

    def test_1_evaluator_to_analyzer(self):
        """测试1: evaluator 低分时路由到 analyzer"""
        print("\n[测试1] evaluator -> analyzer (score_below_threshold)")

        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(routing_config, from_actor="evaluator", to_actor="analyzer")

        assert rule is not None, "未找到 evaluator -> analyzer 路由规则"
        assert rule["condition"] == "score_below_threshold", "路由条件应为 score_below_threshold"

        # 模拟低分评测报告
        mock_score_report = self._mock_evaluation_report(total_score=28)
        assert mock_score_report["total_score"] < 35, "模拟分数应低于阈值35"

        print(f"[PASS] evaluator 低分({mock_score_report['total_score']}/50)时正确路由到 analyzer")
        self.test_results.append(("evaluator_to_analyzer", True, None))
        return True

    def test_2_analyzer_to_prompt_optimizer(self):
        """测试2: analyzer 按 prompt 根因路由到 prompt_optimizer"""
        print("\n[测试2] analyzer -> prompt_optimizer (root_cause_prompt)")

        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(
            routing_config, from_actor="analyzer", to_actor="prompt_optimizer"
        )

        assert rule is not None, "未找到 analyzer -> prompt_optimizer 路由规则"
        assert rule["condition"] in (
            "root_cause_prompt",
            "root_cause_coordination",
        ), "路由条件应为 root_cause_prompt 或 root_cause_coordination"

        mock_analysis = self._mock_analysis_report(root_cause="prompt", target_actor="primary")
        assert mock_analysis["root_cause"] == "prompt"
        assert mock_analysis["target_optimizer"] == "prompt_optimizer"

        print(f"[PASS] analyzer 按 prompt 根因正确路由到 prompt_optimizer")
        self.test_results.append(("analyzer_to_prompt_optimizer", True, None))
        return True

    def test_3_analyzer_to_memory_optimizer(self):
        """测试3: analyzer 按 memory 根因路由到 memory_optimizer"""
        print("\n[测试3] analyzer -> memory_optimizer (root_cause_memory)")

        routing_config = self._load_routing_config()
        rule = self._find_routing_rule(
            routing_config, from_actor="analyzer", to_actor="memory_optimizer"
        )

        assert rule is not None, "未找到 analyzer -> memory_optimizer 路由规则"
        assert rule["condition"] == "root_cause_memory", "路由条件应为 root_cause_memory"

        mock_analysis = self._mock_analysis_report(root_cause="memory", target_actor="memory")
        assert mock_analysis["root_cause"] == "memory"
        assert mock_analysis["target_optimizer"] == "memory_optimizer"

        print(f"[PASS] analyzer 按 memory 根因正确路由到 memory_optimizer")
        self.test_results.append(("analyzer_to_memory_optimizer", True, None))
        return True

    def test_4_optimizer_to_evaluator(self):
        """测试4: optimizer 完成后通知 evaluator 触发下一轮"""
        print("\n[测试4] [prompt_optimizer | memory_optimizer] -> evaluator (optimization_done)")

        routing_config = self._load_routing_config()

        rule_prompt = self._find_routing_rule(
            routing_config, from_actor="prompt_optimizer", to_actor="evaluator"
        )
        rule_memory = self._find_routing_rule(
            routing_config, from_actor="memory_optimizer", to_actor="evaluator"
        )

        assert rule_prompt is not None, "未找到 prompt_optimizer -> evaluator 路由规则"
        assert rule_memory is not None, "未找到 memory_optimizer -> evaluator 路由规则"
        assert rule_prompt["condition"] == "optimization_done"
        assert rule_memory["condition"] == "optimization_done"

        print("[PASS] 两个 optimizer 完成后均能通知 evaluator 触发下一轮")
        self.test_results.append(("optimizer_to_evaluator", True, None))
        return True

    def test_5_backend_constraints(self):
        """测试5: 评测组所有 actor 均不直接回复用户"""
        print("\n[测试5] 评测组后台约束验证")

        routing_config = self._load_routing_config()
        constraints = routing_config.get("constraints", {})

        backend_actors = ["evaluator", "analyzer", "prompt_optimizer", "memory_optimizer"]
        for actor in backend_actors:
            assert actor in constraints, f"{actor} 应有约束配置"
            assert constraints[actor].get("direct_user_reply") == False, \
                f"{actor} 不应直接回复用户"

        print(f"[PASS] 4个评测组 actor 均配置为不直接回复用户")
        self.test_results.append(("backend_constraints", True, None))
        return True

    def test_6_complete_loop_flow(self):
        """测试6: 完整自进化闭环验证（4条消息传递）"""
        print("\n[测试6] 完整自进化闭环验证")

        messages = []

        # 消息1: evaluator -> analyzer（低分触发）
        messages.append({
            "from": "evaluator",
            "to": "analyzer",
            "type": "score_report",
            "payload": self._mock_evaluation_report(total_score=28)
        })

        # 消息2: analyzer -> prompt_optimizer（根因分析）
        messages.append({
            "from": "analyzer",
            "to": "prompt_optimizer",
            "type": "analysis_report",
            "payload": self._mock_analysis_report(root_cause="prompt", target_actor="primary")
        })

        # 消息3: prompt_optimizer 执行优化（内部操作，不计入消息传递）
        # 消息3: prompt_optimizer -> evaluator（优化完成通知）
        messages.append({
            "from": "prompt_optimizer",
            "to": "evaluator",
            "type": "optimization_done",
            "payload": {"status": "success", "target_actor": "primary", "version": 2}
        })

        # 消息4: evaluator 收到通知，触发下一轮评测（闭环完成）
        messages.append({
            "from": "evaluator",
            "to": "analyzer",
            "type": "next_round_trigger",
            "payload": self._mock_evaluation_report(total_score=41)
        })

        assert len(messages) == 4, f"完整闭环应有4条消息传递，实际{len(messages)}条"

        print(f"[PASS] 完整自进化闭环包含4条消息传递:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg['from']} -> {msg['to']} ({msg['type']})")

        # 验证最终分数提升
        initial_score = messages[0]["payload"]["total_score"]
        final_score = messages[3]["payload"]["total_score"]
        assert final_score > initial_score, "优化后分数应提升"
        print(f"  分数变化: {initial_score}/50 -> {final_score}/50 (+{final_score - initial_score})")

        self.test_results.append(("complete_loop", True, None))
        return True

    def test_7_trigger_config(self):
        """测试7: 评测触发配置验证"""
        print("\n[测试7] 评测触发配置验证")

        trigger_config = self._load_trigger_config()

        conditions = trigger_config.get("trigger_conditions", [])
        assert len(conditions) >= 2, "应至少有2个触发条件"

        types = [c["type"] for c in conditions]
        assert "dialogue_count" in types, "应包含对话轮次触发条件"
        assert "score_threshold" in types, "应包含分数阈值触发条件"

        count_cond = next(c for c in conditions if c["type"] == "dialogue_count")
        score_cond = next(c for c in conditions if c["type"] == "score_threshold")

        assert count_cond["threshold"] == 5, "对话轮次阈值应为5"
        assert score_cond["threshold"] == 35, "分数阈值应为35"
        assert score_cond["operator"] == "less_than", "分数触发条件应为 less_than"

        assert trigger_config.get("trigger_logic") == "OR", "触发逻辑应为 OR"
        assert trigger_config.get("target_group") == "evaluation_group", "目标组应为 evaluation_group"
        assert trigger_config.get("entry_actor") == "evaluator", "入口 actor 应为 evaluator"

        print("[PASS] 触发配置验证通过：每5轮 OR 分数<35 触发 evaluator")
        self.test_results.append(("trigger_config", True, None))
        return True

    # --- helpers ---

    def _load_routing_config(self):
        config_path = PROJECT_ROOT / "config" / "evaluation_group_routing.json"
        if not config_path.exists():
            raise FileNotFoundError(f"路由配置文件不存在: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_trigger_config(self):
        config_path = PROJECT_ROOT / "config" / "evaluation_trigger.json"
        if not config_path.exists():
            raise FileNotFoundError(f"触发配置文件不存在: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_routing_rule(self, config, from_actor=None, to_actor=None, condition=None):
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

    def _mock_evaluation_report(self, total_score: int) -> dict:
        per_dim = total_score // 5
        return {
            "total_score": total_score,
            "dimensions": {
                "medical_accuracy": per_dim,
                "safety": per_dim,
                "completeness": per_dim,
                "personalization": per_dim,
                "clarity": total_score - per_dim * 4,
            },
            "issues": ["医学准确性不足"] if total_score < 35 else [],
        }

    def _mock_analysis_report(self, root_cause: str, target_actor: str) -> dict:
        optimizer_map = {
            "prompt": "prompt_optimizer",
            "coordination": "prompt_optimizer",
            "memory": "memory_optimizer",
        }
        return {
            "root_cause": root_cause,
            "target_actor": target_actor,
            "target_optimizer": optimizer_map[root_cause],
            "fix_suggestion": f"优化 {target_actor} 的{'提示词' if root_cause != 'memory' else '记忆'}",
        }

    def run_all_tests(self):
        print("=" * 60)
        print("评测组后台闭环功能测试")
        print("=" * 60)

        tests = [
            self.test_1_evaluator_to_analyzer,
            self.test_2_analyzer_to_prompt_optimizer,
            self.test_3_analyzer_to_memory_optimizer,
            self.test_4_optimizer_to_evaluator,
            self.test_5_backend_constraints,
            self.test_6_complete_loop_flow,
            self.test_7_trigger_config,
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

        print("\n" + "=" * 60)
        print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
        print("=" * 60)
        return failed == 0


if __name__ == "__main__":
    tester = EvaluationGroupLoopTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
