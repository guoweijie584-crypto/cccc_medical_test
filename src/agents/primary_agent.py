"""
Primary Agent - 主治医生 Agent
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent, MockAgent


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
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果在事件循环中，创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.process(context, query, expert_opinions))
                return future.result()
        except RuntimeError:
            # 没有事件循环，直接运行
            return asyncio.run(self.process(context, query, expert_opinions))


class MockPrimaryAgent(MockAgent):
    """Mock 主治医生 Agent"""
    
    def __init__(self):
        super().__init__("primary")
