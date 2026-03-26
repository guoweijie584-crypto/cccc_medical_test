"""
Memory Palace 客户端 - 纯同步版本（避免 asyncio 冲突）

使用 threading 在后台运行异步代码，对外提供同步接口。
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional
import asyncio
import httpx


class MemoryPalaceClientSync:
    """Memory Palace 同步客户端"""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("MCP_API_KEY", "")
        self.session_id = session_id or f"cccc_medical_{os.urandom(4).hex()}"
        
    def _run_sync(self, coro) -> Any:
        """运行异步协程并返回结果（处理嵌套事件循环）"""
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建新线程运行
            result = [None]
            error = [None]
            
            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result[0] = new_loop.run_until_complete(coro)
                    new_loop.close()
                except Exception as e:
                    error[0] = e
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if error[0]:
                raise error[0]
            return result[0]
            
        except RuntimeError:
            # 没有运行的事件循环，直接运行
            return asyncio.run(coro)
    
    async def _search_async(
        self,
        query: str,
        domain: str = "medical",
        max_results: int = 10,
        mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """异步搜索实现"""
        async with httpx.AsyncClient() as client:
            payload = {
                "query": query,
                "domain": domain,
                "max_results": max_results,
                "mode": mode,
                "session_id": self.session_id
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/search",
                    json=payload,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                return result.get("memories", [])
            except Exception as e:
                print(f"[MemoryPalace] Search error: {e}")
                return []
    
    async def _create_async(
        self,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """异步创建实现"""
        async with httpx.AsyncClient() as client:
            payload = {
                "uri": uri,
                "content": content,
                "metadata": metadata or {},
                "session_id": self.session_id
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/create",
                    json=payload,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"[MemoryPalace] Create error: {e}")
                return {"error": str(e)}
    
    async def _read_async(self, uri: str) -> Optional[Dict[str, Any]]:
        """异步读取实现"""
        async with httpx.AsyncClient() as client:
            payload = {"uri": uri, "session_id": self.session_id}
            
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/read",
                    json=payload,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"[MemoryPalace] Read error: {e}")
                return None
    
    async def _update_async(
        self,
        uri: str,
        content: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """异步更新实现"""
        async with httpx.AsyncClient() as client:
            payload = {
                "uri": uri,
                "content": content,
                "reason": reason,
                "session_id": self.session_id
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/update",
                    json=payload,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"[MemoryPalace] Update error: {e}")
                return {"error": str(e)}
    
    async def _delete_async(self, uri: str, reason: str = "") -> bool:
        """异步删除实现"""
        async with httpx.AsyncClient() as client:
            payload = {
                "uri": uri,
                "reason": reason,
                "session_id": self.session_id
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/mcp/delete",
                    json=payload,
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return True
            except Exception as e:
                print(f"[MemoryPalace] Delete error: {e}")
                return False
    
    # 同步接口
    def search(
        self,
        query: str,
        domain: str = "medical",
        max_results: int = 10,
        mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """同步搜索记忆"""
        return self._run_sync(self._search_async(query, domain, max_results, mode))
    
    def create(
        self,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """同步创建记忆"""
        return self._run_sync(self._create_async(content, uri, metadata))
    
    def read(self, uri: str) -> Optional[Dict[str, Any]]:
        """同步读取记忆"""
        return self._run_sync(self._read_async(uri))
    
    def update(
        self,
        uri: str,
        content: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """同步更新记忆"""
        return self._run_sync(self._update_async(uri, content, reason))
    
    def delete(self, uri: str, reason: str = "") -> bool:
        """同步删除记忆"""
        return self._run_sync(self._delete_async(uri, reason))
