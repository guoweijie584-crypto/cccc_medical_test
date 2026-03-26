"""Memory Palace client adapted to the current browse/observability HTTP API."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx


class MemoryPalaceClientSync:
    """Synchronous wrapper around the Memory Palace HTTP API."""

    DOMAIN_ALIAS = {
        "medical": "core",
    }
    SEARCH_MODE_ALIAS = {
        "legacy": "keyword",
    }

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("MCP_API_KEY", "local-dev-key-12345")
        self.session_id = session_id or f"cccc_medical_{os.urandom(4).hex()}"
        self.timeout = float(os.getenv("MEMORY_PALACE_TIMEOUT", "2.0") or "2.0")
        self.cooldown_seconds = float(os.getenv("MEMORY_PALACE_COOLDOWN", "60.0") or "60.0")
        self._disabled_until = 0.0

    def _run_sync(self, coro: Any) -> Any:
        """Run async code from sync call sites, including nested event loops."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        result = [None]
        error = [None]

        def run_in_thread() -> None:
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result[0] = new_loop.run_until_complete(coro)
                new_loop.close()
            except Exception as exc:  # pragma: no cover - defensive
                error[0] = exc

        thread = threading.Thread(target=run_in_thread, daemon=True)
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
        """Issue one HTTP request against Memory Palace."""
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
                    response = await client.get(url, headers=headers, params=params, timeout=self.timeout)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=json_data, timeout=self.timeout)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, params=params, json=json_data, timeout=self.timeout)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params, timeout=self.timeout)
                else:  # pragma: no cover - defensive
                    raise ValueError(f"Unsupported method: {method}")

                response.raise_for_status()
                return response.json() if response.content else {}
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                body: Any
                try:
                    body = exc.response.json()
                except Exception:
                    body = exc.response.text
                if status_code in {404, 409, 422}:
                    return {
                        "error": str(exc),
                        "status_code": status_code,
                        "body": body,
                    }
                self._disabled_until = time.time() + self.cooldown_seconds
                print(f"[MemoryPalace] {method} {path} error: {exc}")
                return {
                    "error": str(exc),
                    "status_code": status_code,
                    "body": body,
                }
            except Exception as exc:
                self._disabled_until = time.time() + self.cooldown_seconds
                print(f"[MemoryPalace] {method} {path} error: {exc}")
                return {"error": str(exc)}

    def _normalize_uri(self, uri: str, *, default_domain: str = "core") -> Tuple[str, str]:
        raw = str(uri or "").strip()
        if "://" in raw:
            raw_domain, raw_path = raw.split("://", 1)
        else:
            raw_domain, raw_path = default_domain, raw

        raw_domain = raw_domain.strip().lower() or default_domain
        raw_path = raw_path.strip("/")
        actual_domain = self.DOMAIN_ALIAS.get(raw_domain, raw_domain)

        if raw_domain == "medical" and raw_path:
            parts = [part for part in raw_path.split("/") if part]
            if len(parts) >= 3 and parts[0] == "patient":
                patient_id = parts[1]
                if parts[2] == "profile" and len(parts) == 3:
                    return actual_domain, f"medical/patient_profiles/{patient_id}"
                category = parts[2]
                suffix = "__".join(parts[3:]) if len(parts) > 3 else ""
                leaf = f"{patient_id}__{category}" + (f"__{suffix}" if suffix else "")
                return actual_domain, f"medical/patient_memories/{leaf}"
            prefix = f"{raw_domain}/"
            if raw_path != raw_domain and not raw_path.startswith(prefix):
                raw_path = f"{raw_domain}/{raw_path}"
        elif raw_domain != actual_domain and raw_path:
            prefix = f"{raw_domain}/"
            if raw_path != raw_domain and not raw_path.startswith(prefix):
                raw_path = f"{raw_domain}/{raw_path}"

        return actual_domain, raw_path

    def _split_path(self, path: str) -> Tuple[str, str]:
        clean = str(path or "").strip("/")
        if not clean:
            return "", ""
        if "/" not in clean:
            return "", clean
        parent, title = clean.rsplit("/", 1)
        return parent, title

    def _namespace_marker(self, path: str) -> str:
        digest = hashlib.sha1(str(path or "").encode("utf-8")).hexdigest()[:12]
        return f"ns:{digest}"

    def _build_search_filters(self, query: str, domain: str) -> Tuple[str, Dict[str, Any]]:
        clean_query = str(query or "").strip()
        raw_domain = str(domain or "core").strip().lower() or "core"
        actual_domain = self.DOMAIN_ALIAS.get(raw_domain, raw_domain)
        filters: Dict[str, Any] = {"domain": actual_domain}

        patient_match = re.search(r"(?:^|\s)patient:([^\s]+)", clean_query)
        patient_id = patient_match.group(1).strip() if patient_match else ""
        if patient_match:
            clean_query = re.sub(r"(?:^|\s)patient:[^\s]+", f" {patient_id}", clean_query).strip()

        if raw_domain != actual_domain:
            base_prefix = "medical/patient_memories" if raw_domain == "medical" else raw_domain
            filters["path_prefix"] = (
                base_prefix
            )
        elif patient_id:
            filters["path_prefix"] = f"patient/{patient_id}"

        return clean_query or "patient memory", filters

    async def _ensure_parent_path_exists(self, *, domain: str, parent_path: str) -> None:
        clean_parent = str(parent_path or "").strip("/")
        if not clean_parent:
            return

        current = ""
        for segment in clean_parent.split("/"):
            current = f"{current}/{segment}" if current else segment
            existing = await self._request(
                "GET",
                "/browse/node",
                params={"path": current, "domain": domain},
            )
            if "error" not in existing:
                continue
            grand_parent, title = self._split_path(current)
            created = await self._request(
                "POST",
                "/browse/node",
                json_data={
                    "parent_path": grand_parent,
                    "title": title,
                    "content": self._namespace_marker(current),
                    "domain": domain,
                },
            )
            if "error" in created:
                raise RuntimeError(created["error"])

    def search(
        self,
        query: str,
        domain: str = "medical",
        max_results: int = 10,
        mode: str = "keyword",
    ) -> List[Dict[str, Any]]:
        clean_query, filters = self._build_search_filters(query, domain)
        payload = {
            "query": clean_query,
            "max_results": max_results,
            "mode": self.SEARCH_MODE_ALIAS.get(str(mode or "").strip().lower(), str(mode or "keyword").strip().lower() or "keyword"),
            "include_session": True,
            "session_id": self.session_id,
            "filters": filters,
        }
        result = self._run_sync(self._request("POST", "/maintenance/observability/search", json_data=payload))
        if "error" in result:
            return []
        normalized_results: List[Dict[str, Any]] = []
        for item in list(result.get("results") or []):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            uri = str(normalized.get("uri") or "").strip()
            if "content" not in normalized:
                if uri:
                    node = self.read(uri)
                    if isinstance(node, dict) and node.get("content") is not None:
                        normalized["content"] = node.get("content")
                if "content" not in normalized:
                    normalized["content"] = normalized.get("snippet", "")
            if "score" not in normalized:
                scores = normalized.get("scores")
                if isinstance(scores, dict):
                    normalized["score"] = float(scores.get("final", 0) or 0)
                else:
                    normalized["score"] = 0.0
            normalized_results.append(normalized)
        return normalized_results

    def create(
        self,
        content: str,
        uri: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        del metadata
        domain, path = self._normalize_uri(uri)
        parent_path, title = self._split_path(path)
        if not title:
            return {"error": "missing target title"}

        async def _create() -> Dict[str, Any]:
            try:
                await self._ensure_parent_path_exists(domain=domain, parent_path=parent_path)
                result = await self._request(
                    "POST",
                    "/browse/node",
                    json_data={
                        "parent_path": parent_path,
                        "title": title,
                        "content": content,
                        "domain": domain,
                    },
                )
                if "error" in result:
                    return result
                return {
                    **result,
                    "uri": f"{domain}://{path}",
                    "path": path,
                    "domain": domain,
                }
            except Exception as exc:
                return {"error": str(exc)}

        return self._run_sync(_create())

    def read(self, uri: str) -> Optional[Dict[str, Any]]:
        domain, path = self._normalize_uri(uri)
        result = self._run_sync(
            self._request(
                "GET",
                "/browse/node",
                params={"path": path, "domain": domain},
            )
        )
        if "error" in result:
            return None
        node = result.get("node") if isinstance(result, dict) else None
        if not isinstance(node, dict):
            return None
        return {
            "uri": node.get("uri") or f"{domain}://{path}",
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
        uri: str,
        content: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        del reason
        domain, path = self._normalize_uri(uri)
        result = self._run_sync(
            self._request(
                "PUT",
                "/browse/node",
                params={"path": path, "domain": domain},
                json_data={"content": content},
            )
        )
        if "error" in result:
            return result
        return {
            **result,
            "uri": f"{domain}://{path}",
            "path": path,
            "domain": domain,
        }

    def delete(self, uri: str, reason: str = "") -> bool:
        del reason
        domain, path = self._normalize_uri(uri)
        result = self._run_sync(
            self._request(
                "DELETE",
                "/browse/node",
                params={"path": path, "domain": domain},
            )
        )
        return "error" not in result
