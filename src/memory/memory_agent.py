"""Medical Memory Palace adapter.

All memory storage, retrieval, and governance is delegated to Memory Palace.
No more three-layer memory (short/mid/long term).

URI scheme:
    patients/{patient_id}/profile          — patient profile
    patients/{patient_id}/consultations/*   — consultation records
    patients/{patient_id}/medications/*     — medication events
    patients/{patient_id}/glucose/*         — glucose readings
    patients/{patient_id}/diet/*            — diet records
    patients/{patient_id}/alerts/*          — safety alerts
    evaluations/pending/*                   — pending human evaluations
    evaluations/completed/*                 — completed evaluations
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import PROJECT_ROOT, prompt_path_for
from .palace_client import MemoryPalaceClient


# ── URI helpers ─────────────────────────────────────────────────────

def _patient_path(patient_id: str, *segments: str) -> str:
    """Build a patient-scoped path."""
    parts = ["patients", patient_id] + list(segments)
    return "/".join(parts)


def _timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class PatientMemory:
    """A patient memory retrieved from Memory Palace."""
    patient_id: str
    data: Dict[str, Any]

    @property
    def basic_info(self) -> Dict[str, Any]:
        return dict(self.data.get("基础信息") or {})

    def to_context_string(self) -> str:
        basic = self.basic_info
        snippets = []
        for key in ("年龄", "性别", "诊断", "糖尿病类型", "是否规律用药", "并发症"):
            value = basic.get(key)
            if value not in (None, "", [], {}):
                snippets.append(f"{key}: {value}")
        return "\n".join(snippets)


# ── Priority constants ──────────────────────────────────────────────

class Priority:
    """Memory retrieval priority (lower = higher priority)."""
    SAFETY_ALERT = 0
    CORE_PROFILE = 1
    RECENT_KEY_EVENT = 2
    CONSULTATION = 3
    AUXILIARY = 4
    LOW_PRIORITY = 5


# ── Main Agent ──────────────────────────────────────────────────────

class MemoryAgent:
    """Medical Memory Palace adapter.

    Delegates ALL memory operations to Memory Palace.
    No internal memory layers. No session_memories dict.
    """

    def __init__(
        self,
        palace_client: Optional[MemoryPalaceClient] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self.client = palace_client or MemoryPalaceClient()
        self.system_prompt = system_prompt or self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        path = prompt_path_for("memory")
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return (
            "You are the Memory Agent for a diabetes-management multi-agent system. "
            "You manage patient memories through Memory Palace — storing consultation "
            "records, medication changes, glucose readings, and safety alerts. "
            "Use appropriate priority levels and disclosure conditions."
        )

    def get_prompt(self) -> str:
        return self.system_prompt

    def set_prompt(self, prompt: str) -> None:
        self.system_prompt = str(prompt or "").strip()

    # ── Context retrieval ───────────────────────────────────────────

    def retrieve_patient_context(
        self,
        patient_id: str,
        query: str = "",
    ) -> Dict[str, Any]:
        """Retrieve patient context from Memory Palace.

        No more short/mid/long term layers.
        Uses Memory Palace search with patient path prefix,
        ordered by priority and relevance.
        """
        # 1. Read patient profile
        profile_path = _patient_path(patient_id, "profile")
        profile_record = self.client.read(profile_path)
        profile_content = self._parse_content(
            profile_record.get("content") if profile_record else None
        )

        # 2. Search relevant memories for this patient
        search_query = query or "血糖 用药 饮食 运动 并发症"
        relevant_memories = self.client.search(
            query=search_query,
            max_results=10,
            mode="keyword",
            path_prefix=f"patients/{patient_id}",
        )

        return {
            "patient_id": patient_id,
            "profile": profile_content,
            "profile_text": self._profile_to_text(profile_content),
            "relevant_memories": relevant_memories,
            "memory_count": len(relevant_memories),
        }

    def build_agent_context(
        self,
        patient_id: str,
        agent_type: str,
        current_query: str,
    ) -> str:
        """Build context string for an agent.

        Unified context — no more three-layer organization.
        """
        ctx = self.retrieve_patient_context(patient_id, current_query)
        sections: list[str] = [
            f"Agent: {agent_type}",
            f"Current query: {current_query}",
        ]

        if ctx["profile_text"]:
            sections.append("## Patient Profile")
            sections.append(ctx["profile_text"])

        if ctx["relevant_memories"]:
            sections.append("## Relevant Memories")
            for item in ctx["relevant_memories"][:8]:
                sections.append(f"- {self._memory_brief(item)}")

        return "\n".join(sections)

    # ── Memory storage ──────────────────────────────────────────────

    def store_consultation_record(
        self,
        patient_id: str,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Store a consultation record in Memory Palace."""
        ts = _timestamp_id()
        path = _patient_path(patient_id, "consultations", ts)
        record = {
            "patient_id": patient_id,
            "query": query,
            "response": response,
            "expert_opinions": expert_opinions or {},
            "timestamp": datetime.now().isoformat(),
        }
        result = self.client.create(
            path=path,
            content=json.dumps(record, ensure_ascii=False),
            priority=Priority.CONSULTATION,
            disclosure="当回顾患者历史咨询记录时",
        )
        if "error" not in result:
            return result.get("uri") or f"{self.client.domain}://{path}"
        return None

    def extract_facts_from_interaction(
        self,
        *,
        patient_id: str,
        query: str,
        primary_response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        """Extract clinically relevant facts from an interaction."""
        text = "\n".join(
            [query, primary_response] + list((expert_opinions or {}).values())
        )
        facts: list[Dict[str, str]] = []

        def _add(category: str, content: str, importance: str = "normal", disclosure: str = "") -> None:
            if not any(f["category"] == category and f["content"] == content for f in facts):
                facts.append({
                    "category": category,
                    "content": content,
                    "importance": importance,
                    "disclosure": disclosure,
                })

        # Glucose reading
        glucose_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mmol/?L)?", text, flags=re.IGNORECASE)
        if glucose_match and "血糖" in text:
            _add("glucose", f"血糖读数 {glucose_match.group(1)} mmol/L",
                 disclosure="当评估血糖控制情况时")

        # Keyword-based extraction
        keyword_map = {
            "medication": (("药", "剂量", "胰岛素", "二甲双胍", "格列", "阿卡波糖"), "当讨论用药方案时"),
            "diet": (("饮食", "水果", "早餐", "晚餐", "碳水", "GI"), "当给出饮食建议时"),
            "exercise": (("运动", "步行", "跑步", "锻炼"), "当讨论运动方案时"),
            "complication": (("并发症", "肾", "眼底", "足", "神经"), "当评估并发症风险时"),
            "safety": (("低血糖", "急诊", "风险", "酮症酸中毒", "DKA"), "当评估安全风险时"),
        }
        for category, (keywords, disclosure) in keyword_map.items():
            if any(kw in text for kw in keywords):
                _add(category, f"咨询涉及{category}管理", disclosure=disclosure)

        if not facts:
            _add("consultation", "常规糖尿病管理咨询", disclosure="当回顾患者咨询历史时")

        return facts

    def extract_and_store(
        self,
        patient_id: str,
        dialogue: Dict[str, Any],
        extracted_facts: List[Dict[str, str]],
    ) -> List[str]:
        """Store extracted facts as individual memories in Memory Palace."""
        stored_uris: List[str] = []
        ts = _timestamp_id()

        for i, fact in enumerate(extracted_facts):
            category = fact.get("category", "general")
            path = _patient_path(patient_id, category, f"{ts}_{i}")
            importance = fact.get("importance", "normal")
            disclosure = fact.get("disclosure", "")

            # Map importance to priority
            priority_map = {"high": Priority.RECENT_KEY_EVENT, "normal": Priority.CONSULTATION, "low": Priority.LOW_PRIORITY}
            priority = priority_map.get(importance, Priority.CONSULTATION)

            # Special: safety facts get highest priority
            if category == "safety":
                priority = Priority.SAFETY_ALERT

            memory_content = {
                "patient_id": patient_id,
                "category": category,
                "content": fact.get("content", ""),
                "importance": importance,
                "source_dialogue": dialogue,
                "timestamp": datetime.now().isoformat(),
            }

            result = self.client.create(
                path=path,
                content=json.dumps(memory_content, ensure_ascii=False),
                priority=priority,
                disclosure=disclosure,
            )
            if "error" not in result:
                uri = result.get("uri") or f"{self.client.domain}://{path}"
                stored_uris.append(uri)

        return stored_uris

    def update_patient_profile(self, patient_id: str, updates: Dict[str, Any]) -> bool:
        """Update a patient's profile in Memory Palace."""
        path = _patient_path(patient_id, "profile")
        existing = self.client.read(path)

        if existing and existing.get("content") is not None:
            current = self._parse_content(existing["content"])
            current.update(updates)
            current["last_updated"] = datetime.now().isoformat()
            result = self.client.update(
                path=path,
                content=json.dumps(current, ensure_ascii=False),
            )
        else:
            profile = {**updates, "last_updated": datetime.now().isoformat()}
            result = self.client.create(
                path=path,
                content=json.dumps(profile, ensure_ascii=False),
                priority=Priority.CORE_PROFILE,
                disclosure="当需要了解患者基本信息时",
            )
        return "error" not in result

    def search_memories(
        self,
        query: str,
        patient_id: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search memories, optionally scoped to a patient."""
        path_prefix = f"patients/{patient_id}" if patient_id else None
        return self.client.search(
            query=query,
            max_results=max_results,
            mode="keyword",
            path_prefix=path_prefix,
        )

    # ── Helpers ─────────────────────────────────────────────────────

    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        if not profile:
            return ""
        lines = []
        for key, value in profile.items():
            if value in (None, "", [], {}):
                continue
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    if sub_value not in (None, "", [], {}):
                        lines.append(f"  {sub_key}: {sub_value}")
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _memory_brief(self, item: Dict[str, Any]) -> str:
        content = item.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return content[:100] if content else str(item)
        if isinstance(content, dict):
            category = content.get("category", "memory")
            text = content.get("content", "")
            ts = content.get("timestamp", "")
            return f"[{category}] {text} ({ts})"
        return str(item)[:100]

    def _parse_content(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not content:
            return {}
        try:
            return json.loads(str(content))
        except Exception:
            return {"raw": str(content)}


# ── Module-level singleton ──────────────────────────────────────────

_memory_agent: Optional[MemoryAgent] = None


def get_memory_agent() -> MemoryAgent:
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent
