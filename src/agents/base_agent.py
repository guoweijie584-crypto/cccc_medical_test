"""
Base Agent - 所有专家 Agent 的基类
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from abc import ABC, abstractmethod

from config.settings import AGENT_CONFIG, PROJECT_ROOT
from ..llm_client import get_llm_client, LLMClient


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, agent_type: str, llm_client: Optional[LLMClient] = None):
        self.agent_type = agent_type
        self.config = AGENT_CONFIG.get(agent_type, {})
        self.name = self.config.get("name", agent_type)
        self.name_zh = self.config.get("name_zh", agent_type)
        self.role = self.config.get("role", "")
        self.system_prompt = self._load_system_prompt()
        self.llm_client = llm_client or get_llm_client()
    
    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """调用 LLM 获取回复"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return await self.llm_client.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=2000
        )
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = self.config.get("system_prompt_file", "")
        if not prompt_file:
            return ""
        
        prompt_path = PROJECT_ROOT / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return ""
    
    def build_full_prompt(self, context: str, query: str, expert_opinions: Optional[Dict[str, str]] = None) -> str:
        """构建完整提示词"""
        prompt_parts = [
            f"# {self.name_zh} ({self.name})",
            f"\n{self.system_prompt}",
            f"\n## 患者上下文",
            context,
            f"\n## 患者问题",
            query,
        ]
        
        if expert_opinions:
            prompt_parts.extend([
                "\n## 专家意见（供参考）",
            ])
            for expert, opinion in expert_opinions.items():
                prompt_parts.append(f"\n### {expert}")
                prompt_parts.append(opinion)
        
        prompt_parts.append("\n## 请基于以上信息给出专业建议")
        
        return "\n".join(prompt_parts)
    
    @abstractmethod
    async def process(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """异步处理请求（子类实现）"""
        pass
    
    @abstractmethod
    def process_sync(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """同步处理请求（子类实现）"""
        pass
    
    def format_response(self, raw_response: str) -> Dict[str, Any]:
        """格式化响应"""
        return {
            "agent_type": self.agent_type,
            "agent_name": self.name_zh,
            "response": raw_response,
            "success": True
        }


class MockAgent(BaseAgent):
    """Mock Agent - 用于测试（无需 LLM API）"""
    
    async def process(self, context: str, query: str, expert_opinions: Dict[str, str] = None, **kwargs) -> Dict[str, Any]:
        """异步处理 - 直接调用同步方法"""
        return self.process_sync(context, query, expert_opinions=expert_opinions, **kwargs)
    
    def process_sync(self, context: str, query: str, expert_opinions: Dict[str, str] = None, **kwargs) -> Dict[str, Any]:
        """同步处理"""
        # 根据 Agent 类型返回模拟响应
        mock_responses = {
            "primary": self._mock_primary_response(query, expert_opinions),
            "pharmacist": self._mock_pharmacist_response(query),
            "nutritionist": self._mock_nutritionist_response(query),
            "doctor": self._mock_doctor_response(query),
        }
        
        response = mock_responses.get(self.agent_type, f"[{self.name_zh}] 收到问题：{query}")
        return self.format_response(response)
    
    def _mock_primary_response(self, query: str, expert_opinions: Dict[str, str] = None) -> str:
        return f"""【综合建议】
- 核心建议：根据您的情况，建议继续当前治疗方案，同时注意饮食控制和规律监测。
- 详细说明：保持良好的用药依从性，定期监测血糖变化。如有异常波动请及时联系医生。
- 注意事项：避免空腹运动，随身携带糖果预防低血糖。

【专家意见摘要】
- 药剂师意见：当前用药方案合理，注意服药时间。
- 营养师意见：建议控制碳水化合物摄入，增加膳食纤维。
- 代谢病医生意见：血糖控制尚可，需定期复查。

【特别提醒】
如血糖持续高于13.9或低于3.9 mmol/L，请及时就医。"""
    
    def _mock_pharmacist_response(self, query: str) -> str:
        return f"""【用药建议】
1. 二甲双胍是2型糖尿病的一线用药，主要通过减少肝脏葡萄糖输出来降低血糖。
2. 常见副作用包括胃肠道反应，通常随用药时间延长会减轻。

【注意事项】
- 药物相互作用：与某些造影剂合用需停药
- 肾功能不全患者需调整剂量
- 常见副作用：恶心、腹泻、胃部不适

【用药指导】
- 服药时间：餐中或餐后服用可减少胃肠不适
- 与饮食的配合：规律进餐，避免漏餐
- 监测要点：定期监测血糖、肾功能

[⚠️] 具体剂量调整请咨询主治医生。"""
    
    def _mock_nutritionist_response(self, query: str) -> str:
        return f"""【饮食建议】
1. 控制每餐碳水化合物摄入量，建议选择低GI食物。
2. 推荐餐食：糙米饭 + 清蒸鱼 + 绿叶蔬菜 + 适量豆腐

【食物选择指导】
- 推荐食物：全谷物、豆类、绿叶蔬菜、瘦肉、鱼类
- 需限制的食物：精制糖、甜饮料、油炸食品、白面包
- 替代选择：用糙米替代白米，用水果替代甜点

【实用技巧】
- 进餐顺序：先吃蔬菜，再吃蛋白质，最后吃主食
- 分量控制：使用标准餐具，每餐主食约1拳头大小
- 外出就餐：选择清淡烹饪方式，避免酱汁过多的菜品

【教育要点】
- 碳水化合物是血糖的主要来源，但不是完全不能吃
- 蛋白质和纤维可以延缓血糖上升
- 规律进餐有助于血糖稳定"""
    
    def _mock_doctor_response(self, query: str) -> str:
        return f"""【病情评估】
- 当前控制状况：需改善
- 主要关注点：餐后血糖控制

【风险识别】
- 潜在风险：长期血糖控制不佳可能导致并发症
- 需要关注的筛查：眼底检查、尿微量白蛋白、神经病变筛查

【诊疗建议】
- 建议的监测项目：每周2-3次空腹及餐后2小时血糖
- 生活方式调整：饮食控制 + 适量运动
- 就医建议：建议1-3个月内复查糖化血红蛋白

【目标设定】
- 血糖控制目标：空腹 4.4-7.0 mmol/L，餐后<10 mmol/L
- 体重管理：保持BMI在18.5-24之间
- 监测频率：每天至少1次血糖监测

如出现酮症症状或血糖持续异常，请立即就医。"""
