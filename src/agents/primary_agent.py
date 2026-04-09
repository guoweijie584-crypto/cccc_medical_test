"""
Primary Agent - 主治医生 Agent
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent, MockAgent, StructuredExpertOutput


class PrimaryAgent(BaseAgent):
    """主治医生 Agent - 综合决策者"""
    
    def __init__(self, llm_client=None):
        super().__init__("primary", llm_client)
    
    async def process(
        self, 
        context: str, 
        query: str, 
        expert_opinions: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """处理患者问题"""
        prompt = self.build_full_prompt(context, query, expert_opinions)
        response = await self._call_llm(prompt, temperature=0.7)
        return self.format_response(response)
    
    def process_sync(self, context: str, query: str, expert_opinions: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """同步处理"""
        prompt = self.build_full_prompt(context, query, expert_opinions)
        response = self._call_llm_sync(prompt, temperature=0.7)
        return self.format_response(response)


class MockPrimaryAgent(MockAgent):
    """Mock 主治医生 Agent"""
    
    def __init__(self):
        super().__init__("primary")
