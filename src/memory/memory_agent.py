"""Memory agent for layered patient memory management."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import PROJECT_ROOT, prompt_path_for
from .palace_client import MemoryPalaceClientSync


@dataclass
class PatientMemory:
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


class MemoryAgent:
    """Maintains short-, mid-, and long-term memory for a patient."""

    def __init__(
        self,
        palace_client: Optional[MemoryPalaceClientSync] = None,
        domain: str = "medical",
        system_prompt: Optional[str] = None,
    ) -> None:
        self.client = palace_client or MemoryPalaceClientSync()
        self.domain = domain
        self.system_prompt = system_prompt or self._load_system_prompt()
        self.session_memories: Dict[str, List[Dict[str, Any]]] = {}

    def _load_system_prompt(self) -> str:
        path = prompt_path_for("memory")
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return (
            "You are the Memory Agent for a diabetes-management multi-agent system. "
            "Capture clinically relevant facts, separate short/mid/long-term memory, "
            "and avoid storing noisy or speculative content."
        )

    def get_prompt(self) -> str:
        return self.system_prompt

    def set_prompt(self, prompt: str) -> None:
        self.system_prompt = str(prompt or "").strip()

    def retrieve_patient_context(
        self,
        patient_id: str,
        query: str = "",
        context_type: str = "full",
    ) -> Dict[str, Any]:
        profile_uri = f"medical://patient/{patient_id}/profile"
        profile_record = self.client.read(profile_uri) or {}
        profile_content = self._parse_content(profile_record.get("content"))

        mid_term = self.search_relevant_memories(
            query=query or "血糖 用药 饮食 运动 并发症",
            patient_id=patient_id,
            max_results=8,
        )
        short_term = list(self.session_memories.get(patient_id, []))

        return {
            "patient_id": patient_id,
            "context_type": context_type,
            "long_term": profile_content,
            "mid_term": mid_term,
            "short_term": short_term,
            "profile": self._profile_to_text(profile_content),
            "recent_memories": mid_term,
            "session_history": short_term,
        }

    def build_agent_context(self, patient_id: str, agent_type: str, current_query: str) -> str:
        context = self.retrieve_patient_context(patient_id=patient_id, query=current_query)
        sections: list[str] = [f"Agent: {agent_type}", f"Current query: {current_query}"]

        if context["profile"]:
            sections.append("## Long-term patient profile")
            sections.append(context["profile"])

        if context["mid_term"]:
            sections.append("## Mid-term relevant memory")
            for item in context["mid_term"][:5]:
                sections.append(f"- {self._memory_brief(item)}")

        if context["short_term"]:
            sections.append("## Short-term session memory")
            for item in context["short_term"][-5:]:
                sections.append(f"- {self._memory_brief(item)}")

        return "\n".join(sections)

    def extract_facts_from_interaction(
        self,
        *,
        patient_id: str,
        query: str,
        primary_response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, str]]:
        text = "\n".join(
            [query, primary_response] + list((expert_opinions or {}).values())
        )
        facts: list[Dict[str, str]] = []

        def add_fact(category: str, content: str, importance: str = "normal") -> None:
            if not any(f["category"] == category and f["content"] == content for f in facts):
                facts.append(
                    {
                        "category": category,
                        "content": content,
                        "importance": importance,
                    }
                )

        glucose_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mmol/?L)?", text, flags=re.IGNORECASE)
        if glucose_match and "血糖" in text:
            add_fact("glucose", f"Patient discussed glucose reading {glucose_match.group(1)} mmol/L")

        keyword_map = {
            "medication": ("药", "剂量", "胰岛素", "二甲双胍", "格列", "阿卡波糖"),
            "diet": ("饮食", "水果", "早餐", "晚餐", "碳水", "GI"),
            "exercise": ("运动", "步行", "跑步", "锻炼"),
            "complication": ("并发症", "肾", "眼底", "足", "神经"),
            "safety": ("低血糖", "急诊", "风险", "酮症酸中毒", "DKA"),
        }
        for category, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                add_fact(category, f"Consultation touched on {category} management")

        if not facts:
            add_fact("consultation", "General diabetes management consultation")

        return facts

    def extract_and_store(
        self,
        patient_id: str,
        dialogue: Dict[str, Any],
        extracted_facts: List[Dict[str, str]],
    ) -> List[str]:
        stored_uris: List[str] = []
        timestamp = datetime.now().isoformat()
        session_bucket = self.session_memories.setdefault(patient_id, [])

        for fact in extracted_facts:
            category = str(fact.get("category") or "general").strip() or "general"
            uri = f"medical://patient/{patient_id}/{category}/{timestamp}"
            memory_content = {
                "patient_id": patient_id,
                "category": category,
                "content": str(fact.get("content") or "").strip(),
                "importance": str(fact.get("importance") or "normal").strip() or "normal",
                "source_dialogue": dialogue,
                "timestamp": timestamp,
            }

            result = self.client.create(
                content=json.dumps(memory_content, ensure_ascii=False),
                uri=uri,
                metadata={
                    "category": category,
                    "importance": memory_content["importance"],
                    "patient_id": patient_id,
                },
            )
            if "error" not in result:
                stored_uris.append(uri)

            session_bucket.append(memory_content)

        return stored_uris

    def update_patient_profile(self, patient_id: str, updates: Dict[str, Any]) -> bool:
        uri = f"medical://patient/{patient_id}/profile"
        existing = self.client.read(uri) or {}
        current = self._parse_content(existing.get("content"))
        current.update(dict(updates or {}))
        current["last_updated"] = datetime.now().isoformat()

        payload = json.dumps(current, ensure_ascii=False)
        if existing.get("content") is not None:
            result = self.client.update(uri=uri, content=payload, reason="profile update")
        else:
            result = self.client.create(
                content=payload,
                uri=uri,
                metadata={"type": "patient_profile", "patient_id": patient_id},
            )
        return "error" not in result

    def search_relevant_memories(
        self,
        query: str,
        patient_id: Optional[str] = None,
        time_range: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        search_query = str(query or "").strip() or "glucose medication diet exercise"
        if patient_id:
            search_query = f"{search_query} patient:{patient_id}"

        results = self.client.search(
            query=search_query,
            domain=self.domain,
            max_results=max_results,
            mode="keyword",
        )
        if patient_id and not results:
            results = self.client.search(
                query=patient_id,
                domain=self.domain,
                max_results=max_results,
                mode="keyword",
            )
        parsed_results: List[Dict[str, Any]] = []
        for mem in results:
            content = self._parse_content(mem.get("content"))
            if patient_id and content.get("patient_id") not in ("", patient_id):
                continue
            parsed_results.append(
                {
                    "uri": mem.get("uri", ""),
                    "content": content,
                    "metadata": dict(mem.get("metadata") or {}),
                    "score": float(mem.get("score", 0) or 0),
                    "timestamp": content.get("timestamp", ""),
                }
            )

        if patient_id and not parsed_results:
            parsed_results.extend(
                {
                    "uri": f"session://{patient_id}/{idx}",
                    "content": item,
                    "metadata": {"source": "session"},
                    "score": 0.0,
                    "timestamp": item.get("timestamp", ""),
                }
                for idx, item in enumerate(self.session_memories.get(patient_id, [])[-max_results:])
            )
        return parsed_results[:max_results]

    def list_patient_memories(self, patient_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        combined = self.search_relevant_memories(query=patient_id, patient_id=patient_id, max_results=limit)
        combined.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return combined[:limit]

    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        if not profile:
            return ""
        lines = []
        for key, value in profile.items():
            if value in (None, "", [], {}):
                continue
            if key == "patient_snapshot" and isinstance(value, dict):
                lines.append("patient_snapshot:")
                for sub_key, sub_value in value.items():
                    if sub_value in (None, "", [], {}):
                        continue
                    lines.append(f"  {sub_key}: {sub_value}")
                continue
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _memory_brief(self, item: Dict[str, Any]) -> str:
        content = item.get("content")
        if isinstance(item, dict) and not isinstance(content, dict):
            category = item.get("category", "memory")
            text = item.get("content", "")
            ts = item.get("timestamp", "")
            if text:
                return f"[{category}] {text} ({ts})"
        if isinstance(content, dict):
            category = content.get("category", "memory")
            text = content.get("content", "")
            ts = content.get("timestamp", "")
            return f"[{category}] {text} ({ts})"
        return str(item)

    def _parse_content(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not content:
            return {}
        try:
            return json.loads(str(content))
        except Exception:
            return {"raw": str(content)}


_memory_agent: Optional[MemoryAgent] = None


def get_memory_agent() -> MemoryAgent:
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent
