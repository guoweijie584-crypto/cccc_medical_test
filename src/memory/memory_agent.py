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
import logging
import re
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import PROJECT_ROOT, prompt_path_for
from .palace_client import MemoryPalaceClient

logger = logging.getLogger(__name__)


# ── URI helpers ─────────────────────────────────────────────────────

def _patient_path(patient_id: str, *segments: str) -> str:
    """Build a patient-scoped path."""
    parts = ["patients", patient_id] + list(segments)
    return "/".join(parts)


def _timestamp_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class MemoryRecord:
    """带完整元数据的记忆记录。

    包含 8 项必备元数据字段以满足记忆治理指南的要求。
    """
    content: str
    category: str  # glucose, medication, diet, exercise, consultation, safety, profile, etc.
    patient_id: str

    # 8 项必备元数据
    source: str = "system_extracted"  # user_reported / expert_inferred / doctor_confirmed / system_extracted
    timestamp: str = ""  # ISO 格式
    expiry: Optional[str] = None  # ISO 格式，None 表示永不过期
    confidence: float = 0.8  # 0.0-1.0
    verification_status: str = "unverified"  # unverified / verified / disputed / retracted
    sensitivity_level: str = "normal"  # normal / sensitive / highly_sensitive
    conflict_with: Optional[List[str]] = None  # 冲突的记忆 URI 列表
    supersedes: Optional[str] = None  # 如果替代某条旧记录，填旧记录的 URI

    # 附加
    importance: str = "normal"  # low / normal / high / critical
    disclosure: str = ""  # 触发条件描述

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_content_dict(self) -> Dict[str, Any]:
        """转换为可存入 Memory Palace 的 content dict。"""
        return {
            "patient_id": self.patient_id,
            "category": self.category,
            "content": self.content,
            # 8 项必备元数据
            "source": self.source,
            "timestamp": self.timestamp,
            "expiry": self.expiry,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "sensitivity_level": self.sensitivity_level,
            "conflict_with": self.conflict_with,
            "supersedes": self.supersedes,
            # 附加
            "importance": self.importance,
            "disclosure": self.disclosure,
        }

    def to_legacy_dict(self) -> Dict[str, str]:
        """转换为旧版 Dict[str, str] 格式，保持向后兼容。

        供 workflow.py 中 extracted_facts 序列化 / 日志记录使用。
        """
        return {
            "category": self.category,
            "content": self.content,
            "importance": self.importance,
            "disclosure": self.disclosure,
        }

    @classmethod
    def from_content_dict(cls, data: Dict[str, Any], patient_id: str = "") -> "MemoryRecord":
        """从 Memory Palace 读取的 content dict 解析。

        向后兼容：缺少新字段时使用默认值。
        """
        pid = data.get("patient_id", "") or patient_id
        return cls(
            content=data.get("content", ""),
            category=data.get("category", "general"),
            patient_id=pid,
            # 8 项必备元数据 — 旧格式缺失时用默认值
            source=data.get("source", "system_extracted"),
            timestamp=data.get("timestamp", ""),
            expiry=data.get("expiry", None),
            confidence=float(data.get("confidence", 0.8)),
            verification_status=data.get("verification_status", "unverified"),
            sensitivity_level=data.get("sensitivity_level", "normal"),
            conflict_with=data.get("conflict_with", None),
            supersedes=data.get("supersedes", None),
            # 附加
            importance=data.get("importance", "normal"),
            disclosure=data.get("disclosure", ""),
        )


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

        返回的每条记忆会标注 verification_status 和 confidence 元数据。
        """
        # 1. Read patient profile
        profile_path = _patient_path(patient_id, "profile")
        profile_record = self.client.read(profile_path)
        profile_content = self._parse_content(
            profile_record.get("content") if profile_record else None
        )

        # 2. Search relevant memories for this patient (hybrid = keyword + semantic)
        search_query = query or "血糖 用药 饮食 运动 并发症"
        relevant_memories = self.client.search(
            query=search_query,
            max_results=10,
            mode="hybrid",
            path_prefix=f"patients/{patient_id}",
        )

        # 3. Annotate memories with metadata (verification_status, confidence)
        annotated_memories = self._annotate_memories_with_metadata(relevant_memories)

        return {
            "patient_id": patient_id,
            "profile": profile_content,
            "profile_text": self._profile_to_text(profile_content),
            "relevant_memories": annotated_memories,
            "memory_count": len(annotated_memories),
        }

    def _annotate_memories_with_metadata(
        self, memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """为每条检索到的记忆标注 verification_status 和 confidence 元数据。

        解析记忆内容，提取元数据字段并附加到返回结果中，
        便于下游 agent 根据可信度进行决策。
        """
        annotated: List[Dict[str, Any]] = []
        for item in memories:
            enriched = dict(item)  # shallow copy

            # 尝试从 content 中解析元数据
            content = item.get("content")
            parsed = self._parse_content(content)

            # 提取元数据字段（向后兼容：旧记忆缺少这些字段时用默认值）
            enriched["_meta"] = {
                "verification_status": parsed.get("verification_status", "unverified"),
                "confidence": float(parsed.get("confidence", 0.8)),
                "source": parsed.get("source", "system_extracted"),
                "sensitivity_level": parsed.get("sensitivity_level", "normal"),
                "expiry": parsed.get("expiry"),
            }
            annotated.append(enriched)

        return annotated

    def build_agent_context(
        self,
        patient_id: str,
        agent_type: str,
        current_query: str,
    ) -> str:
        """Build context string for an agent.

        Unified context — no more three-layer organization.
        包含每条记忆的可信度和验证状态标注。
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
                meta = item.get("_meta", {})
                confidence = meta.get("confidence", 0.8)
                status = meta.get("verification_status", "unverified")
                brief = self._memory_brief(item)
                # 标注可信度和验证状态
                sections.append(
                    f"- {brief} [confidence={confidence:.1f}, status={status}]"
                )

        return "\n".join(sections)

    # ── Memory storage ──────────────────────────────────────────────

    def store_consultation_record(
        self,
        patient_id: str,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Store a consultation record in Memory Palace.

        使用 MemoryRecord 构建完整元数据。
        """
        ts = _timestamp_id()
        path = _patient_path(patient_id, "consultations", ts)

        record = MemoryRecord(
            content=json.dumps({
                "query": query,
                "response": response,
                "expert_opinions": expert_opinions or {},
            }, ensure_ascii=False),
            category="consultation",
            patient_id=patient_id,
            source="system_extracted",
            confidence=0.9,
            verification_status="unverified",
            sensitivity_level="normal",
            importance="normal",
            disclosure="当回顾患者历史咨询记录时",
        )
        content_dict = record.to_content_dict()

        result = self.client.create(
            path=path,
            content=json.dumps(content_dict, ensure_ascii=False),
            priority=Priority.CONSULTATION,
            disclosure=record.disclosure,
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
    ) -> List[MemoryRecord]:
        """Extract clinically relevant facts from an interaction.

        返回 List[MemoryRecord]，每条记录包含完整的 8 项必备元数据。
        向后兼容：MemoryRecord 可通过 .to_legacy_dict() 转为旧格式 Dict。
        """
        text = "\n".join(
            [query, primary_response] + list((expert_opinions or {}).values())
        )
        facts: list[MemoryRecord] = []
        now_iso = datetime.now().isoformat()

        # 判断来源：如果有专家意见，则为 expert_inferred；否则来自用户
        has_expert = bool(expert_opinions and any(expert_opinions.values()))

        def _add(
            category: str,
            content: str,
            importance: str = "normal",
            disclosure: str = "",
            confidence: float = 0.8,
            source: str = "",
            sensitivity_level: str = "normal",
        ) -> None:
            if not any(f.category == category and f.content == content for f in facts):
                # 智能推断 source
                effective_source = source
                if not effective_source:
                    effective_source = "expert_inferred" if has_expert else "user_reported"

                facts.append(MemoryRecord(
                    content=content,
                    category=category,
                    patient_id=patient_id,
                    source=effective_source,
                    timestamp=now_iso,
                    expiry=None,
                    confidence=confidence,
                    verification_status="unverified",
                    sensitivity_level=sensitivity_level,
                    conflict_with=None,
                    supersedes=None,
                    importance=importance,
                    disclosure=disclosure,
                ))

        # Glucose reading — 精确数值，高置信度
        glucose_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mmol/?L)?", text, flags=re.IGNORECASE)
        if glucose_match and "血糖" in text:
            _add(
                "glucose",
                f"血糖读数 {glucose_match.group(1)} mmol/L",
                disclosure="当评估血糖控制情况时",
                confidence=0.95,  # 精确数值读数，高置信度
                source="user_reported",
            )

        # Keyword-based extraction
        keyword_map = {
            "medication": (
                ("药", "剂量", "胰岛素", "二甲双胍", "格列", "阿卡波糖"),
                "当讨论用药方案时",
                0.75,  # 模糊关键词匹配，中等置信度
                "sensitive",  # 用药信息属于敏感
            ),
            "diet": (
                ("饮食", "水果", "早餐", "晚餐", "碳水", "GI"),
                "当给出饮食建议时",
                0.7,
                "normal",
            ),
            "exercise": (
                ("运动", "步行", "跑步", "锻炼"),
                "当讨论运动方案时",
                0.7,
                "normal",
            ),
            "complication": (
                ("并发症", "肾", "眼底", "足", "神经"),
                "当评估并发症风险时",
                0.7,
                "sensitive",  # 并发症信息属于敏感
            ),
            "safety": (
                ("低血糖", "急诊", "风险", "酮症酸中毒", "DKA"),
                "当评估安全风险时",
                0.85,  # 安全相关，较高置信度
                "sensitive",  # 安全信息属于敏感
            ),
        }
        for category, (keywords, disclosure, conf, sens) in keyword_map.items():
            if any(kw in text for kw in keywords):
                _add(
                    category,
                    f"咨询涉及{category}管理",
                    disclosure=disclosure,
                    confidence=conf,
                    sensitivity_level=sens,
                )

        if not facts:
            _add(
                "consultation",
                "常规糖尿病管理咨询",
                disclosure="当回顾患者咨询历史时",
                confidence=0.6,  # 兜底记录，较低置信度
            )

        return facts

    # ── Conflict detection ────────────────────────────────────────

    # Time window for considering two records as potential conflicts
    _CONFLICT_WINDOW_HOURS: int = 24

    def _check_conflict(
        self,
        patient_id: str,
        new_record: MemoryRecord,
    ) -> Optional[List[str]]:
        """检查新记忆是否与已有记忆冲突。

        搜索同 patient_id + 同 category 的近期记忆，
        比较内容是否矛盾（同类型、不同内容、时间间隔短）。

        Returns:
            冲突的记忆 URI 列表；None 表示无冲突。
        """
        try:
            # Search for recent memories of the same category for this patient
            path_prefix = f"patients/{patient_id}"
            existing_memories = self.client.search(
                query=new_record.content,
                max_results=5,
                mode="hybrid",
                path_prefix=path_prefix,
            )

            if not existing_memories:
                return None

            conflict_uris: List[str] = []

            for mem in existing_memories:
                parsed = self._parse_content(mem.get("content"))
                existing_category = parsed.get("category", "")
                existing_content = parsed.get("content", "")
                existing_timestamp_str = parsed.get("timestamp", "")

                # Only compare within the same category
                if existing_category != new_record.category:
                    continue

                # Skip if content is identical (not a conflict, just a duplicate)
                if existing_content == new_record.content:
                    continue

                # Skip if there's no existing content to compare
                if not existing_content:
                    continue

                # Check if within conflict time window
                if existing_timestamp_str and new_record.timestamp:
                    try:
                        existing_ts = datetime.fromisoformat(existing_timestamp_str)
                        new_ts = datetime.fromisoformat(new_record.timestamp)
                        time_diff = abs((new_ts - existing_ts).total_seconds())
                        if time_diff > self._CONFLICT_WINDOW_HOURS * 3600:
                            continue  # Too old — not a conflict, just an update
                    except (ValueError, TypeError):
                        pass  # If timestamps can't be parsed, still check content

                # Same category, different content, within time window → conflict
                mem_uri = mem.get("uri", "")
                if not mem_uri:
                    mem_path = parsed.get("path", "")
                    if mem_path:
                        mem_uri = f"{self.client.domain}://{mem_path}"
                if mem_uri:
                    conflict_uris.append(mem_uri)

            return conflict_uris if conflict_uris else None

        except Exception as exc:
            logger.warning("Conflict check failed (non-critical): %s", exc)
            return None  # Fail open: allow writes if conflict check fails

    def extract_and_store(
        self,
        patient_id: str,
        dialogue: Dict[str, Any],
        extracted_facts: Union[List[MemoryRecord], List[Dict[str, str]], List[str]],
    ) -> List[str]:
        """Store extracted facts as individual memories in Memory Palace.

        在写入前执行冲突检测：如果发现冲突，在新记录的 conflict_with
        字段中标注冲突 URI，而不是覆盖旧记录。

        向后兼容：extracted_facts 可以是：
          - List[MemoryRecord]  — 新格式（推荐）
          - List[Dict[str, str]] — 旧格式（自动转换）
          - List[str]            — 测试用纯字符串列表（自动转换）
        """
        stored_uris: List[str] = []
        ts = _timestamp_id()

        # 统一转换为 MemoryRecord 列表
        records = self._normalize_facts(extracted_facts, patient_id)

        for i, record in enumerate(records):
            category = record.category
            path = _patient_path(patient_id, category, f"{ts}_{i}")

            # ── Conflict detection before write ──
            conflict_uris = self._check_conflict(patient_id, record)
            if conflict_uris:
                # Annotate the new record with conflict references instead of overwriting
                record.conflict_with = conflict_uris
                logger.info(
                    "Memory conflict detected for patient %s, category=%s: "
                    "new record conflicts with %s",
                    patient_id, category, conflict_uris,
                )

            # Map importance to priority
            priority_map = {
                "critical": Priority.SAFETY_ALERT,
                "high": Priority.RECENT_KEY_EVENT,
                "normal": Priority.CONSULTATION,
                "low": Priority.LOW_PRIORITY,
            }
            priority = priority_map.get(record.importance, Priority.CONSULTATION)

            # Special: safety facts get highest priority
            if category == "safety":
                priority = Priority.SAFETY_ALERT

            # 使用 MemoryRecord.to_content_dict() 生成完整元数据
            memory_content = record.to_content_dict()
            # 附加对话来源信息
            memory_content["source_dialogue"] = dialogue

            result = self.client.create(
                path=path,
                content=json.dumps(memory_content, ensure_ascii=False),
                priority=priority,
                disclosure=record.disclosure,
            )
            if "error" not in result:
                uri = result.get("uri") or f"{self.client.domain}://{path}"
                stored_uris.append(uri)

        return stored_uris

    def _normalize_facts(
        self,
        extracted_facts: Union[List[MemoryRecord], List[Dict[str, str]], List[str]],
        patient_id: str,
    ) -> List[MemoryRecord]:
        """将各种格式的 extracted_facts 统一转换为 List[MemoryRecord]。

        支持三种输入格式以保持向后兼容：
          - List[MemoryRecord] — 直接使用
          - List[Dict] — 使用 MemoryRecord.from_content_dict() 解析
          - List[str] — 包装为最基本的 MemoryRecord
        """
        records: List[MemoryRecord] = []
        for item in extracted_facts:
            if isinstance(item, MemoryRecord):
                records.append(item)
            elif isinstance(item, dict):
                records.append(MemoryRecord.from_content_dict(item, patient_id=patient_id))
            elif isinstance(item, str):
                # 纯字符串 — 来自旧版测试
                records.append(MemoryRecord(
                    content=item,
                    category="general",
                    patient_id=patient_id,
                    source="system_extracted",
                    confidence=0.6,
                ))
            else:
                # 未知类型，尝试转为字符串
                records.append(MemoryRecord(
                    content=str(item),
                    category="general",
                    patient_id=patient_id,
                    source="system_extracted",
                    confidence=0.5,
                ))
        return records

    def update_patient_profile(
        self,
        patient_id: str,
        updates: Dict[str, Any],
    ) -> Union[bool, Dict[str, Any]]:
        """Update a patient's profile in Memory Palace.

        逐字段比较，记录哪些字段被更新、哪些被标记为冲突。
        向后兼容：仍然返回 bool（成功/失败），但内部会记录
        冲突信息到 profile 的 _field_conflicts 元数据中。

        对于全新的 profile（无已有记录），行为与旧版完全相同。

        Returns:
            True/False for backward compat.  Internally, field-level
            conflict details are persisted in the profile's
            ``_field_conflicts`` and ``_update_log`` keys.
        """
        path = _patient_path(patient_id, "profile")
        existing = self.client.read(path)

        if existing and existing.get("content") is not None:
            current = self._parse_content(existing["content"])
            now_iso = datetime.now().isoformat()

            # ── Field-level comparison ────────────────────────────
            updated_fields: List[str] = []
            conflict_fields: Dict[str, Dict[str, Any]] = {}  # field → {old, new}

            # Preserve existing conflict log
            field_conflicts = dict(current.get("_field_conflicts") or {})
            update_log: List[Dict[str, Any]] = list(current.get("_update_log") or [])

            for key, new_value in updates.items():
                if key.startswith("_"):
                    # Skip internal metadata keys
                    continue
                old_value = current.get(key)

                if old_value is None or old_value == "" or old_value == {} or old_value == []:
                    # Field was empty — safe to set
                    current[key] = new_value
                    updated_fields.append(key)
                elif old_value == new_value:
                    # No change — skip
                    continue
                else:
                    # Field has a different existing value → conflict
                    conflict_fields[key] = {
                        "old_value": old_value,
                        "new_value": new_value,
                        "detected_at": now_iso,
                    }
                    # Store conflict info but STILL apply the update
                    # (the new value is more recent, but we keep a record)
                    field_conflicts[key] = {
                        "old_value": old_value,
                        "new_value": new_value,
                        "detected_at": now_iso,
                        "status": "auto_updated",  # vs. "needs_review" for sensitive fields
                    }
                    current[key] = new_value
                    updated_fields.append(key)

            # For sensitive medical fields, mark conflicts as needing review
            _SENSITIVE_FIELDS = {
                "诊断", "糖尿病类型", "并发症", "药物过敏",
                "当前用药", "medications", "diagnosis", "type",
            }
            for fld in conflict_fields:
                if fld in _SENSITIVE_FIELDS and fld in field_conflicts:
                    field_conflicts[fld]["status"] = "needs_review"

            # Record this update in the log
            if updated_fields or conflict_fields:
                log_entry: Dict[str, Any] = {
                    "timestamp": now_iso,
                    "updated_fields": updated_fields,
                }
                if conflict_fields:
                    log_entry["conflicts"] = conflict_fields
                update_log.append(log_entry)
                # Keep only the last 20 log entries to avoid unbounded growth
                update_log = update_log[-20:]

            current["_field_conflicts"] = field_conflicts
            current["_update_log"] = update_log
            current["last_updated"] = now_iso

            if conflict_fields:
                logger.info(
                    "Profile update for patient %s: %d field(s) updated, "
                    "%d conflict(s) detected: %s",
                    patient_id, len(updated_fields),
                    len(conflict_fields), list(conflict_fields.keys()),
                )

            result = self.client.update(
                path=path,
                content=json.dumps(current, ensure_ascii=False),
            )
        else:
            # No existing profile — create fresh (no conflicts possible)
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
            mode="hybrid",
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
