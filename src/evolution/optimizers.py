"""Prompt and memory optimizers."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import LOG_DIR, prompt_path_for
from .analyzer import AnalysisReport, ProblemType


@dataclass
class PromptOptimization:
    agent_id: str
    original_prompt: str
    optimized_prompt: str
    changes: List[str]
    version: int
    timestamp: str
    diff: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "original_prompt": self.original_prompt,
            "optimized_prompt": self.optimized_prompt,
            "changes": self.changes,
            "version": self.version,
            "timestamp": self.timestamp,
            "diff": self.diff,
        }


@dataclass
class MemoryOptimization:
    operation: str
    uri: str
    original_content: Optional[str]
    new_content: Optional[str]
    reason: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "uri": self.uri,
            "original_content": self.original_content,
            "new_content": self.new_content,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class PromptOptimizer:
    """Makes minimal prompt edits and records a version history."""

    def __init__(self, llm_client=None) -> None:
        self.llm_client = llm_client
        self.optimization_history: List[PromptOptimization] = []
        self.prompt_versions: Dict[str, int] = {}
        self.version_root = LOG_DIR / "prompt_versions"

    def optimize(
        self,
        agent_id: str,
        current_prompt: str,
        analysis_report: AnalysisReport,
        use_llm: bool = False,
    ) -> Optional[PromptOptimization]:
        relevant = [
            item
            for item in analysis_report.problems
            if item.problem_type == ProblemType.PROMPT and (item.agent_id in (None, "", agent_id))
        ]
        if not relevant:
            return None

        optimized_prompt, changes = self._optimize_with_rules(agent_id, current_prompt, relevant)
        if optimized_prompt.strip() == current_prompt.strip():
            return None

        version = self.prompt_versions.get(agent_id, 0) + 1
        self.prompt_versions[agent_id] = version
        diff = "\n".join(
            difflib.unified_diff(
                current_prompt.splitlines(),
                optimized_prompt.splitlines(),
                fromfile=f"{agent_id}_old",
                tofile=f"{agent_id}_new",
                lineterm="",
            )
        )

        result = PromptOptimization(
            agent_id=agent_id,
            original_prompt=current_prompt,
            optimized_prompt=optimized_prompt,
            changes=changes,
            version=version,
            timestamp=datetime.now().isoformat(),
            diff=diff,
        )
        self.optimization_history.append(result)
        self._persist_version(result)
        return result

    def rollback(self, agent_id: str, steps: int = 1) -> Optional[str]:
        history = [item for item in self.optimization_history if item.agent_id == agent_id]
        if len(history) <= steps:
            return None
        return history[-(steps + 1)].optimized_prompt

    def _optimize_with_rules(
        self,
        agent_id: str,
        current_prompt: str,
        relevant_problems: List[Any],
    ) -> tuple[str, List[str]]:
        prompt = current_prompt.strip()
        changes: List[str] = []

        def append_block(title: str, content: str, change_label: str) -> None:
            nonlocal prompt
            if title not in prompt:
                prompt = f"{prompt}\n\n{title}\n{content}".strip()
                changes.append(change_label)

        for problem in relevant_problems:
            desc = str(problem.description or "")
            suggestion = str(problem.suggestion or "")
            lower = f"{desc}\n{suggestion}".lower()

            if agent_id == "memory":
                append_block(
                    "[Memory extraction checklist]",
                    "- Capture short-term dialogue facts.\n"
                    "- Capture recent trend changes as mid-term memory.\n"
                    "- Preserve stable patient profile facts as long-term memory.\n"
                    "- Mark stale or uncertain information explicitly.\n"
                    "- Avoid storing noisy or speculative content.",
                    "Added structured memory extraction checklist",
                )
                if "stale" in lower or "结构" in desc:
                    append_block(
                        "[Memory hygiene]",
                        "- Remove outdated medication plans when new ones appear.\n"
                        "- Group memories by glucose, medication, diet, exercise, complication, and safety.",
                        "Added memory hygiene rules",
                    )
                continue

            if "safety" in lower or "风险" in desc:
                append_block(
                    "[Safety requirements]",
                    "- State clear escalation thresholds for severe hyperglycemia, hypoglycemia, and urgent symptoms.\n"
                    "- Do not give unsafe dosing changes without clinician confirmation.",
                    "Strengthened safety instructions",
                )
            if "personal" in lower or "患者" in desc:
                append_block(
                    "[Personalization requirements]",
                    "- Explicitly reference patient age, diabetes type, complications, current therapy, and recent trend before advice.",
                    "Strengthened personalization instructions",
                )
            if "accuracy" in lower or "医学" in desc:
                append_block(
                    "[Clinical grounding]",
                    "- Ground advice in diabetes-management guidelines and avoid unsupported claims.",
                    "Added clinical grounding instruction",
                )
            if "consistency" in lower:
                append_block(
                    "[Specialist synthesis]",
                    "- Reconcile specialist opinions and explain conflicts instead of ignoring them.",
                    "Added specialist synthesis instruction",
                )

        if not changes:
            append_block(
                "[Optimization note]",
                "- Keep recommendations concise, evidence-based, and action-oriented.",
                "Added general optimization note",
            )

        return prompt, changes

    def _persist_version(self, result: PromptOptimization) -> None:
        version_dir = self.version_root / result.agent_id
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / f"v{result.version}.txt").write_text(result.optimized_prompt, encoding="utf-8")
        (version_dir / f"v{result.version}.diff").write_text(result.diff, encoding="utf-8")
        (version_dir / f"v{result.version}.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class MemoryOptimizer:
    """Produces a list of concrete memory add/update/delete operations."""

    def __init__(self, memory_client=None, llm_client=None) -> None:
        self.memory_client = memory_client
        self.llm_client = llm_client
        self.optimization_history: List[MemoryOptimization] = []

    def optimize(
        self,
        patient_id: str,
        analysis_report: AnalysisReport,
        current_memories: List[Dict[str, Any]],
        dialogue_context: Optional[Dict[str, Any]] = None,
        use_llm: bool = False,
    ) -> List[MemoryOptimization]:
        operations: List[MemoryOptimization] = []
        if not analysis_report.should_optimize_memory():
            return operations

        for problem in analysis_report.problems:
            if problem.problem_type != ProblemType.MEMORY:
                continue
            desc = str(problem.description or "").lower()

            if "missing" in desc or "缺少" in problem.description:
                operations.extend(
                    self._extract_missing_memories(patient_id, dialogue_context or {}, current_memories)
                )
            if "stale" in desc or "过时" in problem.description:
                for mem in self._find_outdated_memories(current_memories):
                    operations.append(
                        MemoryOptimization(
                            operation="delete",
                            uri=str(mem.get("uri") or ""),
                            original_content=json.dumps(mem.get("content", {}), ensure_ascii=False),
                            new_content=None,
                            reason="Remove outdated memory entry",
                            timestamp=datetime.now().isoformat(),
                        )
                    )
            if "incorrect" in desc or "不准确" in problem.description:
                for mem in current_memories:
                    if self._is_suspicious_memory(mem):
                        operations.append(
                            MemoryOptimization(
                                operation="update",
                                uri=str(mem.get("uri") or ""),
                                original_content=json.dumps(mem.get("content", {}), ensure_ascii=False),
                                new_content=self._mark_uncertain(mem.get("content")),
                                reason="Mark low-confidence memory for review",
                                timestamp=datetime.now().isoformat(),
                            )
                        )

        self.optimization_history.extend(operations)
        return operations

    def apply_operations(self, operations: List[MemoryOptimization]) -> Dict[str, int]:
        if not self.memory_client:
            return {"added": 0, "updated": 0, "deleted": 0, "failed": len(operations)}

        stats = {"added": 0, "updated": 0, "deleted": 0, "failed": 0}
        for op in operations:
            try:
                if op.operation == "add":
                    result = self.memory_client.create(content=op.new_content or "", uri=op.uri, metadata={"optimized": True})
                    stats["added" if "error" not in result else "failed"] += 1
                elif op.operation == "update":
                    result = self.memory_client.update(uri=op.uri, content=op.new_content or "", reason=op.reason)
                    stats["updated" if "error" not in result else "failed"] += 1
                elif op.operation == "delete":
                    success = self.memory_client.delete(uri=op.uri, reason=op.reason)
                    stats["deleted" if success else "failed"] += 1
            except Exception:
                stats["failed"] += 1
        return stats

    def _extract_missing_memories(
        self,
        patient_id: str,
        dialogue_context: Dict[str, Any],
        current_memories: List[Dict[str, Any]],
    ) -> List[MemoryOptimization]:
        query = str(dialogue_context.get("query") or "")
        response = str(dialogue_context.get("response") or "")
        combined = f"{query}\n{response}"
        categories = {
            "glucose": ("血糖", "空腹", "餐后", "HbA1c"),
            "medication": ("药", "胰岛素", "剂量", "二甲双胍", "格列"),
            "diet": ("饮食", "早餐", "水果", "碳水"),
            "exercise": ("运动", "锻炼", "步行"),
            "safety": ("低血糖", "急诊", "风险", "DKA"),
        }
        existing_categories = {
            str((mem.get("content") or {}).get("category") or mem.get("category") or "").strip()
            for mem in current_memories
        }

        operations: List[MemoryOptimization] = []
        for category, keywords in categories.items():
            if category in existing_categories:
                continue
            if not any(keyword in combined for keyword in keywords):
                continue
            uri = f"medical://patient/{patient_id}/{category}/{datetime.now().strftime('%Y%m%d%H%M%S')}"
            payload = json.dumps(
                {
                    "patient_id": patient_id,
                    "category": category,
                    "content": f"Auto-extracted from consultation: {query[:120]}",
                    "timestamp": datetime.now().isoformat(),
                },
                ensure_ascii=False,
            )
            operations.append(
                MemoryOptimization(
                    operation="add",
                    uri=uri,
                    original_content=None,
                    new_content=payload,
                    reason="Add missing clinically relevant memory entry",
                    timestamp=datetime.now().isoformat(),
                )
            )
        return operations

    def _find_outdated_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = datetime.now()
        outdated: List[Dict[str, Any]] = []
        for mem in memories:
            timestamp_str = str(mem.get("timestamp") or (mem.get("content") or {}).get("timestamp") or "").strip()
            if not timestamp_str:
                continue
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                continue
            if (now - ts.replace(tzinfo=None)).days > 180:
                outdated.append(mem)
        return outdated

    def _is_suspicious_memory(self, memory: Dict[str, Any]) -> bool:
        raw = json.dumps(memory.get("content", {}), ensure_ascii=False)
        return any(token in raw for token in ("可能", "也许", "uncertain", "pending"))

    def _mark_uncertain(self, content: Any) -> str:
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except Exception:
                content = {"content": content}
        payload = dict(content or {})
        payload["confidence"] = "low"
        payload["needs_verification"] = True
        return json.dumps(payload, ensure_ascii=False)
