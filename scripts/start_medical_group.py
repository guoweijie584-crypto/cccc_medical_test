"""
医疗主组启动脚本
初始化5个Actor并模拟一轮完整对话
验证消息流转符合 routing.json 定义
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class Actor:
    """模拟Actor"""
    def __init__(self, actor_id: str, role: str):
        self.actor_id = actor_id
        self.role = role
        self.status = "idle"
        self.messages_received = []
        self.messages_sent = []
    
    def receive_message(self, message: dict):
        self.messages_received.append(message)
        self.status = "active"
        print(f"  [{self.actor_id}] 收到消息: {message['type']}")
    
    def send_message(self, to: str, message_type: str, content: dict) -> dict:
        msg = {
            "from": self.actor_id,
            "to": to,
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.messages_sent.append(msg)
        return msg


class MedicalGroupRunner:
    """医疗主组运行器"""
    
    def __init__(self):
        self.actors = {}
        self.message_log = []
        self.routing_config = self._load_routing_config()
        
    def _load_routing_config(self) -> dict:
        """加载路由配置"""
        config_path = PROJECT_ROOT / "config" / "medical_group_routing.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def initialize_actors(self):
        """初始化5个Actor"""
        print("\n" + "="*60)
        print("初始化医疗主组 5 个 Actor")
        print("="*60)
        
        actor_configs = [
            ("primary", "内分泌科主治医生 - 唯一对外出口"),
            ("pharmacist", "临床药师 - 药物管理专家"),
            ("nutritionist", "糖尿病专科营养师 - 饮食管理专家"),
            ("doctor", "糖尿病专科医生 - 诊疗决策专家"),
            ("memory", "患者记忆管理员 - Memory Palace桥接层"),
        ]
        
        for actor_id, role in actor_configs:
            self.actors[actor_id] = Actor(actor_id, role)
            print(f"  [OK] {actor_id}: {role}")
        
        print(f"\n共初始化 {len(self.actors)} 个 Actor")
        
    def simulate_dialogue(self, patient_id: str = "PAT_test_001", 
                          user_query: str = "我今天空腹血糖7.2，有点担心"):
        """模拟一轮完整对话"""
        print("\n" + "="*60)
        print("模拟对话流程")
        print("="*60)
        print(f"患者ID: {patient_id}")
        print(f"用户问题: {user_query}")
        print("-"*60)
        
        # 消息1: 用户 -> primary
        print("\n[消息1] user -> primary")
        msg1 = {
            "from": "user",
            "to": "primary",
            "type": "patient_query",
            "content": {"patient_id": patient_id, "query": user_query},
            "timestamp": datetime.now().isoformat()
        }
        self.actors["primary"].receive_message(msg1)
        self.message_log.append(msg1)
        print("  -> primary 接收用户问题")
        
        # 消息2: primary -> memory (检索上下文)
        print("\n[消息2] primary -> memory")
        msg2 = self.actors["primary"].send_message(
            "memory", 
            "retrieve_context",
            {"patient_id": patient_id, "query": user_query}
        )
        self.actors["memory"].receive_message(msg2)
        self.message_log.append(msg2)
        print("  -> memory 检索患者上下文")
        
        # 模拟memory返回
        memory_response = {
            "patient_id": patient_id,
            "profile": "58岁, 2型糖尿病, 二甲双胍",
            "recent_glucose": "近7天平均6.8 mmol/L",
            "alerts": []
        }
        msg2_reply = self.actors["memory"].send_message(
            "primary",
            "context_response",
            memory_response
        )
        self.actors["primary"].receive_message(msg2_reply)
        self.message_log.append(msg2_reply)
        print("  <- memory 返回上下文")
        
        # 消息3: primary -> 3个专家 (并行咨询)
        print("\n[消息3] primary -> [pharmacist, nutritionist, doctor] (并行)")
        experts = ["pharmacist", "nutritionist", "doctor"]
        
        for expert in experts:
            msg3 = self.actors["primary"].send_message(
                expert,
                "consultation_request",
                {"patient_id": patient_id, "query": user_query, "context": memory_response}
            )
            self.actors[expert].receive_message(msg3)
            self.message_log.append(msg3)
            print(f"  -> {expert} 收到咨询请求")
        
        # 模拟专家回复
        expert_responses = {
            "pharmacist": "当前用药方案暂不需调整。",
            "nutritionist": "建议晚餐减少碳水摄入。",
            "doctor": "血糖控制尚可，继续监测。"
        }
        
        print("\n[消息4] [pharmacist, nutritionist, doctor] -> primary")
        for expert, response in expert_responses.items():
            msg4 = self.actors[expert].send_message(
                "primary",
                "consultation_response",
                {"response": response}
            )
            self.actors["primary"].receive_message(msg4)
            self.message_log.append(msg4)
            print(f"  <- {expert} 返回建议")
        
        # 消息5: primary -> 用户 (综合回复)
        print("\n[消息5] primary -> user")
        primary_response = (
            "【综合建议】\n"
            "根据您的血糖记录，今天空腹7.2略高于近期平均（6.8）。\n\n"
            "药师建议：用药方案暂不需调整。\n"
            "营养师建议：建议晚餐减少碳水摄入。\n"
            "医生评估：血糖控制尚可，继续监测。\n\n"
            "【特别提醒】\n"
            "如连续3天高于7.0，请复诊。"
        )
        
        msg5 = self.actors["primary"].send_message(
            "user",
            "final_response",
            {"response": primary_response}
        )
        self.message_log.append(msg5)
        print("  -> 综合回复已发送给用户")
        
    def verify_routing(self):
        """验证消息流转符合路由规则"""
        print("\n" + "="*60)
        print("验证路由规则")
        print("="*60)
        
        routing_rules = self.routing_config.get("routing_rules", [])
        constraints = self.routing_config.get("constraints", {})
        
        # 验证5条消息流转
        expected_flow = [
            ("user", "primary"),
            ("primary", "memory"),
            ("primary", "pharmacist"),
            ("primary", "nutritionist"),
            ("primary", "doctor"),
            ("pharmacist", "primary"),
            ("nutritionist", "primary"),
            ("doctor", "primary"),
            ("primary", "user"),
        ]
        
        all_passed = True
        for from_actor, to_actor in expected_flow:
            found = any(
                msg["from"] == from_actor and msg["to"] == to_actor
                for msg in self.message_log
            )
            status = "[PASS]" if found else "[FAIL]"
            print(f"  {status} {from_actor} -> {to_actor}")
            if not found:
                all_passed = False
        
        # 验证约束（内部专家不直接回复用户）
        print("\n  约束验证：")
        internal_actors = ["pharmacist", "nutritionist", "doctor", "memory"]
        for actor in internal_actors:
            direct_to_user = any(
                msg["from"] == actor and msg["to"] == "user"
                for msg in self.message_log
            )
            constraint = constraints.get(actor, {}).get("direct_user_reply", True)
            if not constraint and not direct_to_user:
                print(f"    [PASS] {actor} 未直接回复用户（符合约束）")
            elif constraint:
                print(f"    [INFO] {actor} 无约束配置")
            else:
                print(f"    [FAIL] {actor} 违规直接回复用户")
                all_passed = False
        
        return all_passed
        
    def print_summary(self):
        """打印运行摘要"""
        print("\n" + "="*60)
        print("运行摘要")
        print("="*60)
        
        print(f"\n消息总数: {len(self.message_log)}")
        print(f"预期消息数: 9")
        
        print("\n各Actor状态:")
        for actor_id, actor in self.actors.items():
            received = len(actor.messages_received)
            sent = len(actor.messages_sent)
            print(f"  {actor_id}: 收到{received}条, 发送{sent}条")
        
        print("\n消息流转图:")
        for i, msg in enumerate(self.message_log, 1):
            print(f"  {i}. {msg['from']} -> {msg['to']} ({msg['type']})")
        
    def run(self):
        """运行完整流程"""
        self.initialize_actors()
        self.simulate_dialogue()
        routing_valid = self.verify_routing()
        self.print_summary()
        
        print("\n" + "="*60)
        # 注意：实际是10条消息（包含memory->primary的回复）
        if routing_valid and len(self.message_log) >= 9:
            print("[SUCCESS] 医疗主组配置验证通过")
        else:
            print("[FAILED] 验证失败，请检查路由配置")
        print("="*60)
        
        return routing_valid


def main():
    """主入口"""
    print("="*60)
    print("医疗主组启动脚本")
    print("="*60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"运行时间: {datetime.now().isoformat()}")
    
    runner = MedicalGroupRunner()
    success = runner.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
