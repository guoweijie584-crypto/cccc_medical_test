"""Memory Palace client — simplified for medical domain.

Talks to the Memory Palace HTTP API (browse + observability endpoints).
All URI handling follows the medical URI scheme defined in the design doc:
    medical://patients/{patient_id}/profile
    medical://patients/{patient_id}/consultations/{timestamp}
    medical://patients/{patient_id}/glucose/{timestamp}
    ...
"""

from __future__ import annotations

import asyncio
import os
import threading
import time
from typing import Any, Dict, List, Optional

import httpx


class MemoryPalaceClient:
    """Synchronous wrapper around the Memory Palace HTTP API.

    Key design changes from the old version:
    - No more complex URI normalization / domain aliasing
    - Direct support for priority and disclosure fields
    - Search uses standard observability endpoint
    - Simpler, more predictable behavior
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        domain: str = "core",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("MCP_API_KEY", "local-dev-key-12345")
        self.session_id = session_id or f"cccc_medical_{os.urandom(4).hex()}"
        self.domain = domain
        self.timeout = float(os.getenv("MEMORY_PALACE_TIMEOUT", "5.0") or "5.0")
        self.cooldown_seconds = float(os.getenv("MEMORY_PALACE_COOLDOWN", "60.0") or "60.0")
        self._disabled_until = 0.0

    # ── Async plumbing ──────────────────────────────────────────────

    def _run_sync(self, coro: Any) -> Any:
        """Run async code from sync call sites, including nested event loops."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        result: list = [None]
        error: list = [None]

        def _thread_target() -> None:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(coro)
                loop.close()
            except Exception as exc:
                error[0] = exc

        thread = threading.Thread(target=_thread_target, daemon=True)
        thread.start()
        thread.join()
        if error[0]:
            raise error[0]
        return result[0]

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if time.time() < self._disabled_until:
            return {"error": "memory palace temporarily unavailable"}

        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{path}"
            headers = {
                "X-MCP-API-Key": self.api_key,
                "Content-Type": "application/json",
            }
            try:
                if method == "GET":
                    resp = await client.get(url, headers=headers, params=params, timeout=self.timeout)
                elif method == "POST":
                    resp = await client.post(url, headers=headers, json=json_data, timeout=self.timeout)
                elif method == "PUT":
                    resp = await client.put(url, headers=headers, params=params, json=json_data, timeout=self.timeout)
                elif method == "DELETE":
                    resp = await client.delete(url, headers=headers, params=params, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                try:
                    body = exc.response.json()
                except Exception:
                    body = exc.response.text
                if status_code in {404, 409, 422}:
                    return {"error": str(exc), "status_code": status_code, "body": body}
                self._disabled_until = time.time() + self.cooldown_seconds
                print(f"[MemoryPalace] {method} {path} error: {exc}")
                return {"error": str(exc), "status_code": status_code, "body": body}
            except Exception as exc:
                self._disabled_until = time.time() + self.cooldown_seconds
                print(f"[MemoryPalace] {method} {path} error: {exc}")
                return {"error": str(exc)}

    # ── Helper: ensure parent path exists ───────────────────────────

    async def _ensure_parent_path(self, parent_path: str) -> None:
        """Create intermediate nodes if they don't exist yet."""
        if not parent_path:
            return
        current = ""
        for segment in parent_path.strip("/").split("/"):
            current = f"{current}/{segment}" if current else segment
            existing = await self._request(
                "GET", "/browse/node",
                params={"path": current, "domain": self.domain},
            )
            if "error" not in existing:
                continue
            grand_parent, title = self._split_path(current)
            created = await self._request(
                "POST", "/browse/node",
                json_data={
                    "parent_path": grand_parent,
                    "title": title,
                    "content": f"[container node: {current}]",
                    "domain": self.domain,
                },
            )
            if "error" in created:
                raise RuntimeError(f"Failed to create parent node {current}: {created['error']}")

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        clean = path.strip("/")
        if "/" not in clean:
            return "", clean
        parent, title = clean.rsplit("/", 1)
        return parent, title

    # ── Public API ──────────────────────────────────────────────────

    def create(
        self,
        path: str,
        content: str,
        *,
        priority: int = 3,
        disclosure: str = "",
    ) -> Dict[str, Any]:
        """Create a new memory node at the given path.

        Args:
            path: Node path within the domain (e.g. "patients/P001/profile")
            content: Memory content text
            priority: Retrieval priority (lower = higher priority, min 0)
            disclosure: Trigger condition — when should this memory be recalled
        """
        parent_path, title = self._split_path(path)

        async def _do_create() -> Dict[str, Any]:
            try:
                await self._ensure_parent_path(parent_path)
                result = await self._request(
                    "POST", "/browse/node",
                    json_data={
                        "parent_path": parent_path,
                        "title": title,
                        "content": content,
                        "domain": self.domain,
                        **({"priority": priority} if priority is not None else {}),
                        **({"disclosure": disclosure} if disclosure else {}),
                    },
                )
                if "error" in result:
                    return result
                return {
                    **result,
                    "path": path,
                    "domain": self.domain,
                    "uri": f"{self.domain}://{path}",
                }
            except Exception as exc:
                return {"error": str(exc)}

        return self._run_sync(_do_create())

    def read(self, path: str) -> Optional[Dict[str, Any]]:
        """Read a memory node by path."""
        result = self._run_sync(
            self._request("GET", "/browse/node", params={"path": path, "domain": self.domain})
        )
        if "error" in result:
            return None
        node = result.get("node") if isinstance(result, dict) else None
        if not isinstance(node, dict):
            return None
        return {
            "uri": node.get("uri") or f"{self.domain}://{path}",
            "content": node.get("content"),
            "metadata": {
                "domain": node.get("domain"),
                "path": node.get("path"),
                "priority": node.get("priority"),
                "disclosure": node.get("disclosure"),
                "created_at": node.get("created_at"),
            },
            "children": list(result.get("children") or []),
        }

    def update(
        self,
        path: str,
        content: str,
        *,
        priority: Optional[int] = None,
        disclosure: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing memory node's content and/or metadata.

        Supports partial metadata updates: if priority or disclosure are
        provided they are sent to Memory Palace for update; otherwise only
        content is replaced.  The Write Guard on the server side will
        validate the write before committing.
        """
        json_data: Dict[str, Any] = {"content": content}
        if priority is not None:
            json_data["priority"] = priority
        if disclosure is not None:
            json_data["disclosure"] = disclosure

        result = self._run_sync(
            self._request(
                "PUT", "/browse/node",
                params={"path": path, "domain": self.domain},
                json_data=json_data,
            )
        )
        if "error" in result:
            return result
        return {
            **result,
            "path": path,
            "domain": self.domain,
            "uri": f"{self.domain}://{path}",
        }

    def delete(self, path: str) -> bool:
        """Delete a memory node by path."""
        result = self._run_sync(
            self._request("DELETE", "/browse/node", params={"path": path, "domain": self.domain})
        )
        return "error" not in result

    def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        mode: str = "hybrid",
        path_prefix: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search memories using keyword/semantic/hybrid retrieval.

        Default mode is 'hybrid' to leverage Memory Palace's full
        retrieval capability (keyword + semantic matching).
        """
        filters: Dict[str, Any] = {"domain": self.domain}
        if path_prefix:
            filters["path_prefix"] = path_prefix

        payload = {
            "query": query,
            "max_results": max_results,
            "mode": mode,
            "include_session": True,
            "session_id": self.session_id,
            "filters": filters,
        }
        result = self._run_sync(
            self._request("POST", "/maintenance/observability/search", json_data=payload)
        )
        if "error" in result:
            return []

        normalized: List[Dict[str, Any]] = []
        for item in list(result.get("results") or []):
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            # Ensure content is present
            if "content" not in entry:
                uri = str(entry.get("uri") or "").strip()
                if uri:
                    node = self.read(uri.split("://", 1)[-1] if "://" in uri else uri)
                    if node and node.get("content") is not None:
                        entry["content"] = node["content"]
                if "content" not in entry:
                    entry["content"] = entry.get("snippet", "")
            # Normalize score
            if "score" not in entry:
                scores = entry.get("scores")
                if isinstance(scores, dict):
                    entry["score"] = float(scores.get("final", 0) or 0)
                else:
                    entry["score"] = 0.0
            normalized.append(entry)
        return normalized

    def health_check(self) -> bool:
        """Check if Memory Palace is reachable."""
        try:
            result = self._run_sync(self._request("GET", "/health"))
            return "error" not in result
        except Exception:
            return False


# Backward compatibility alias
MemoryPalaceClientSync = MemoryPalaceClient
