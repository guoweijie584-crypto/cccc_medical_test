"""Extra API routes for trace listing and admin errors."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import Query

from src.memory import get_memory_agent


def register_extra_routes(app):
    """Register /api/traces and /api/admin/errors on the given FastAPI app."""

    @app.get("/api/traces")
    async def api_get_traces(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> Dict[str, Any]:
        memory_agent = get_memory_agent()
        client = memory_agent.client
        traces_root = client.read("traces")
        items: List[Dict[str, Any]] = []
        if traces_root:
            children = traces_root.get("children") or []
            for child in children[:limit]:
                child_path = child.get("path") if isinstance(child, dict) else str(child)
                if not child_path:
                    continue
                trace_id = child_path.rsplit("/", 1)[-1] if "/" in child_path else child_path
                record = client.read(child_path)
                if not record:
                    continue
                content = record.get("content")
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        content = {}
                elif not isinstance(content, dict):
                    content = {}
                items.append({
                    "trace_id": content.get("trace_id", trace_id),
                    "patient_id": content.get("patient_id", ""),
                    "query": content.get("original_query", ""),
                    "status": (
                        "partial_failure" if content.get("partial_failure")
                        else ("failure" if content.get("errors") else "success")
                    ),
                    "created_at": content.get("timestamp_start", ""),
                    "duration_ms": content.get("latency_total_ms", 0),
                    "expert_count": len(content.get("routed_agents", [])),
                    "has_safety_issues": not content.get("safety_review_passed", True),
                })
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"traces": items[:limit], "count": len(items)}

    @app.get("/api/admin/errors")
    async def api_get_admin_errors(
        limit: int = Query(default=20, ge=1, le=100),
    ) -> Dict[str, Any]:
        memory_agent = get_memory_agent()
        client = memory_agent.client
        traces_root = client.read("traces")
        errors: List[Dict[str, Any]] = []
        if traces_root:
            children = traces_root.get("children") or []
            for child in children[:200]:
                child_path = child.get("path") if isinstance(child, dict) else str(child)
                if not child_path:
                    continue
                record = client.read(child_path)
                if not record:
                    continue
                content = record.get("content")
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except (json.JSONDecodeError, TypeError):
                        continue
                elif not isinstance(content, dict):
                    continue
                trace_errors = content.get("errors") or []
                partial = content.get("partial_failure", False)
                safety_issues = content.get("safety_issues") or []
                tid = content.get("trace_id", child_path.rsplit("/", 1)[-1])
                pid = content.get("patient_id", "")
                ts = content.get("timestamp_start", "")
                for err_entry in trace_errors:
                    msg = err_entry.get("error", "") if isinstance(err_entry, dict) else str(err_entry)
                    errors.append({
                        "trace_id": tid,
                        "timestamp": err_entry.get("timestamp", ts) if isinstance(err_entry, dict) else ts,
                        "message": msg,
                        "severity": "error",
                        "patient_id": pid,
                    })
                if partial and not trace_errors:
                    errors.append({
                        "trace_id": tid, "timestamp": ts,
                        "message": "partial_failure",
                        "severity": "warning", "patient_id": pid,
                    })
                for issue in safety_issues:
                    errors.append({
                        "trace_id": tid, "timestamp": ts,
                        "message": issue,
                        "severity": "warning", "patient_id": pid,
                    })
        errors.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return {"errors": errors[:limit], "count": len(errors)}
