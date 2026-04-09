"""
Doctor Agent - 代谢病医生 Agent
"""

from typing import Dict, Any
from .base_agent import BaseAgent, MockAgent, StructuredExpertOutput


class DoctorAgent(BaseAgent):
    """代谢病医生 Agent - 诊疗专家"""

    def __init__(self, llm_client=None):
        super().__init__("doctor", llm_client)

    async def process(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """处理诊疗相关问题"""
        prompt = self.build_full_prompt(context, query)
        response = await self._call_llm(prompt, temperature=0.3)
        return self.format_response(response)

    def process_sync(self, context: str, query: str, **kwargs) -> Dict[str, Any]:
        """同步处理"""
        prompt = self.build_full_prompt(context, query)
        response = self._call_llm_sync(prompt, temperature=0.3)
        return self.format_response(response)


class MockDoctorAgent(MockAgent):
    """Mock 代谢病医生 Agent"""

    def __init__(self):
        super().__init__("doctor")
