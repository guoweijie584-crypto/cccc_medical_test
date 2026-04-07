"""Root-cause analysis for prompt and memory issues.

Supports two input modes:
1. Legacy: numeric-score evaluation reports (EvaluatorAgent)
2. Human-driven: discrete-label human evaluations (EvaluationService)
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .evaluation_service import HumanEvaluation


class ProblemType(Enum):
    PROMPT = "prompt"
    MEMORY = "memory"
    WORKFLOW = "workflow"
    UNKNOWN = "unknown"


@dataclass
class ProblemAnalysis:
    problem_type: ProblemType
    severity: float
    agent_id: Optional[str] = None
    memory_uri: Optional[str] = None
    description: str = ""
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_type": self.problem_type.value,
            "severity": self.severity,
            "agent_id": self.agent_id,
            "memory_uri": self.memory_uri,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class AnalysisReport:
    analysis_id: str
    evaluation_id: str
    problems: List[ProblemAnalysis] = field(default_factory=list)
    primary_problem: Optional[ProblemAnalysis] = None
    summary: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "evaluation_id": self.evaluation_id,
            "problems": [item.to_dict() for item in self.problems],
            "primary_problem": self.primary_problem.to_dict() if self.primary_problem else None,
            "summary": self.summary,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def should_optimize_prompt(self, threshold: float = 6.0) -> bool:
        prompt_problems = [p for p in self.problems if p.problem_type == ProblemType.PROMPT]
        return bool(prompt_problems) and max(p.severity for p in prompt_problems) >= threshold

    def should_optimize_memory(self, threshold: float = 5.5) -> bool:
        memory_problems = [p for p in self.problems if p.problem_type == ProblemType.MEMORY]
        return bool(memory_problems) and max(p.severity for p in memory_problems) >= threshold

    def prompt_target_agents(self) -> List[str]:
        ordered: list[str] = []
        for item in self.problems:
            if item.problem_type != ProblemType.PROMPT:
                continue
            agent_id = str(item.agent_id or "").strip()
            if agent_id and agent_id not in ordered:
                ordered.append(agent_id)
        return ordered


class AnalyzerAgent:
    """Analyzes evaluation results and points optimizers at the likely root cause."""

    def __init__(self, llm_client=None) -> None:
        self.llm_client = llm_client
        self.analysis_history: List[AnalysisReport] = []

    def analyze(
        self,
        evaluation_report: Dict[str, Any],
        agent_outputs: Optional[Dict[str, str]] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = False,
    ) -> AnalysisReport:
        from datetime import datetime
        import uuid

        response_score = dict(evaluation_report.get("response_score") or {})
        memory_score = dict(evaluation_report.get("memory_score") or {})

        problems: List[ProblemAnalysis] = []
        problems.extend(self._analyze_prompt_issues(response_score, agent_outputs or {}))
        problems.extend(self._analyze_memory_issues(memory_score, memories or []))

        if not problems:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.UNKNOWN,
                    severity=0.0,
                    description="No blocking issue detected.",
                    suggestion="Keep the current configuration.",
                )
            )

        primary_problem = max(problems, key=lambda item: item.severity)
        summary = self._generate_summary(problems, response_score, memory_score)

        report = AnalysisReport(
            analysis_id=f"anal_{uuid.uuid4().hex[:8]}",
            evaluation_id=str(evaluation_report.get("evaluation_id") or "").strip(),
            problems=problems,
            primary_problem=primary_problem,
            summary=summary,
            timestamp=datetime.now().isoformat(),
        )
        self.analysis_history.append(report)
        return report

    def should_optimize_prompt(self, report: AnalysisReport, threshold: float = 6.0) -> bool:
        return report.should_optimize_prompt(threshold)

    def should_optimize_memory(self, report: AnalysisReport, threshold: float = 5.5) -> bool:
        return report.should_optimize_memory(threshold)

    def _analyze_prompt_issues(
        self,
        response_score: Dict[str, Any],
        agent_outputs: Dict[str, str],
    ) -> List[ProblemAnalysis]:
        problems: List[ProblemAnalysis] = []
        if float(response_score.get("medical_accuracy", 10) or 0) < 7.0:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=8.0,
                    agent_id="primary",
                    description="Medical accuracy is below target.",
                    suggestion="Tighten evidence-based instructions and treatment-target guidance.",
                )
            )
        if float(response_score.get("safety", 10) or 0) < 7.5:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=9.0,
                    agent_id="primary",
                    description="Safety language is too weak for the case.",
                    suggestion="Add explicit escalation, low/high glucose thresholds, and emergency triggers.",
                )
            )
        if float(response_score.get("personalization", 10) or 0) < 6.5:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=6.5,
                    agent_id="primary",
                    description="The answer is not sufficiently tailored to the patient profile.",
                    suggestion="Force explicit use of patient profile and recent glucose trend before giving recommendations.",
                )
            )
        if float(response_score.get("consistency", 10) or 0) < 6.5 and agent_outputs:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=6.8,
                    agent_id="primary",
                    description="Expert outputs are not being reconciled clearly.",
                    suggestion="Strengthen synthesis instructions for conflicting specialist opinions.",
                )
            )
        return problems

    def _analyze_memory_issues(
        self,
        memory_score: Dict[str, Any],
        memories: List[Dict[str, Any]],
    ) -> List[ProblemAnalysis]:
        problems: List[ProblemAnalysis] = []
        if float(memory_score.get("completeness", 10) or 0) < 6.5:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.MEMORY,
                    severity=7.5,
                    memory_uri=None,
                    description="Key memory categories are missing.",
                    suggestion="Extract missing facts and improve memory capture coverage.",
                )
            )
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=7.2,
                    agent_id="memory",
                    description="Memory-agent extraction instructions are too weak.",
                    suggestion="Update the Memory Agent prompt to require short/mid/long-term memory extraction.",
                )
            )
        if float(memory_score.get("accuracy", 10) or 0) < 6.5:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.MEMORY,
                    severity=7.0,
                    description="Stored memory may contain stale or incorrect facts.",
                    suggestion="Mark uncertain memories and clean stale medication/history items.",
                )
            )
        if float(memory_score.get("structure", 10) or 0) < 6.5:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.PROMPT,
                    severity=6.6,
                    agent_id="memory",
                    description="Memory structure is weak or inconsistent.",
                    suggestion="Strengthen structured memory formatting and category rules in the Memory Agent prompt.",
                )
            )
        if not memories:
            problems.append(
                ProblemAnalysis(
                    problem_type=ProblemType.WORKFLOW,
                    severity=6.0,
                    description="No relevant memories were returned at all.",
                    suggestion="Verify Memory Palace availability and fallback session-memory behavior.",
                )
            )
        return problems

    def _generate_summary(
        self,
        problems: List[ProblemAnalysis],
        response_score: Dict[str, Any],
        memory_score: Dict[str, Any],
    ) -> str:
        prompt_count = sum(1 for item in problems if item.problem_type == ProblemType.PROMPT)
        memory_count = sum(1 for item in problems if item.problem_type == ProblemType.MEMORY)
        workflow_count = sum(1 for item in problems if item.problem_type == ProblemType.WORKFLOW)
        return (
            f"response={float(response_score.get('overall', 0) or 0):.2f}, "
            f"memory={float(memory_score.get('overall', 0) or 0):.2f}; "
            f"prompt_issues={prompt_count}, memory_issues={memory_count}, workflow_issues={workflow_count}"
        )

    # ── Human evaluation analysis (Line 3) ─────────────────────────

    def analyze_human_evaluation(
        self,
        evaluation: "HumanEvaluation",
        agent_outputs: Optional[Dict[str, str]] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
    ) -> AnalysisReport:
        """Analyze a single BAD/ERROR human evaluation and produce an AnalysisReport.

        Maps discrete labels (safety, advice_direction, reviewer_notes) to
        concrete ProblemAnalysis items that PromptOptimizer and MemoryOptimizer
        can act on.
        """
        problems: List[ProblemAnalysis] = []

        label = str(evaluation.label or "").upper()

        # ── Safety dimension ───────────────────────────────────────
        if evaluation.safety in ("risky", "dangerous"):
            severity = 9.5 if evaluation.safety == "dangerous" else 8.0
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=severity,
                agent_id="primary",
                description=f"Human reviewer flagged safety as '{evaluation.safety}'.",
                suggestion=(
                    "Add stricter safety guardrails: explicit escalation thresholds, "
                    "contraindication checks, and emergency-referral triggers."
                ),
            ))

        # ── Advice direction dimension ─────────────────────────────
        if evaluation.advice_direction == "wrong":
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=8.5,
                agent_id="primary",
                description="Human reviewer judged advice direction as 'wrong'.",
                suggestion=(
                    "Strengthen clinical grounding and evidence-based instruction "
                    "to prevent incorrect recommendations."
                ),
            ))
        elif evaluation.advice_direction == "partial":
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=6.5,
                agent_id="primary",
                description="Human reviewer judged advice direction as 'partial'.",
                suggestion=(
                    "Improve completeness: ensure all relevant aspects (medication, "
                    "diet, exercise, monitoring) are addressed."
                ),
            ))

        # ── Personalization dimension ──────────────────────────────
        if evaluation.personalized is False:
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=6.5,
                agent_id="primary",
                description="Response was not personalized to the patient.",
                suggestion=(
                    "Force explicit reference to patient profile (age, type, "
                    "complications, current therapy, recent glucose trend) before giving advice."
                ),
            ))
            # Memory issue: maybe the patient context was not recalled
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.MEMORY,
                severity=6.0,
                description="Personalization failure may indicate missing patient memory retrieval.",
                suggestion=(
                    "Verify that the patient profile and recent interaction memories "
                    "are being retrieved and injected into the agent context."
                ),
            ))

        # ── Reviewer notes mining ──────────────────────────────────
        notes = str(evaluation.reviewer_notes or "").strip()
        if notes:
            problems.extend(self._mine_reviewer_notes(notes))

        # ── ERROR label: high severity general problem ─────────────
        if label == "ERROR" and not problems:
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.WORKFLOW,
                severity=9.0,
                description="Human reviewer flagged as ERROR — requires detailed review.",
                suggestion="Inspect the full consultation log and memory state for this case.",
            ))

        # ── BAD label with no specific dimension flagged ───────────
        if label == "BAD" and not problems:
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=7.0,
                agent_id="primary",
                description="Human reviewer rated response as BAD without specific dimensions flagged.",
                suggestion=(
                    "Review primary agent prompt for general quality issues: "
                    "accuracy, completeness, safety language."
                ),
            ))

        # Ensure at least one problem
        if not problems:
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.UNKNOWN,
                severity=0.0,
                description="No actionable issue extracted from this evaluation.",
                suggestion="Monitor for recurring patterns.",
            ))

        primary_problem = max(problems, key=lambda p: p.severity)
        prompt_count = sum(1 for p in problems if p.problem_type == ProblemType.PROMPT)
        memory_count = sum(1 for p in problems if p.problem_type == ProblemType.MEMORY)
        summary = (
            f"human_eval={label}; "
            f"prompt_issues={prompt_count}, memory_issues={memory_count}, "
            f"total_problems={len(problems)}"
        )

        report = AnalysisReport(
            analysis_id=f"hanal_{uuid.uuid4().hex[:8]}",
            evaluation_id=str(evaluation.evaluation_id or ""),
            problems=problems,
            primary_problem=primary_problem,
            summary=summary,
            timestamp=datetime.now().isoformat(),
        )
        self.analysis_history.append(report)
        return report

    def _mine_reviewer_notes(self, notes: str) -> List[ProblemAnalysis]:
        """Extract problem signals from free-text reviewer notes."""
        problems: List[ProblemAnalysis] = []
        lower = notes.lower()

        # Safety keywords
        safety_kw = ("危险", "低血糖", "急诊", "过敏", "禁忌", "unsafe", "dangerous", "risk", "hypoglycemia")
        if any(kw in lower for kw in safety_kw):
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=8.5,
                agent_id="primary",
                description=f"Reviewer notes mention safety concern: '{notes[:120]}'",
                suggestion="Reinforce safety checks and contraindication awareness in prompts.",
            ))

        # Memory / context keywords
        memory_kw = ("记忆", "遗忘", "没考虑", "上次", "历史", "memory", "forgot", "context", "history")
        if any(kw in lower for kw in memory_kw):
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.MEMORY,
                severity=7.0,
                description=f"Reviewer notes suggest memory/context gap: '{notes[:120]}'",
                suggestion="Improve memory retrieval coverage and patient history recall.",
            ))

        # Accuracy keywords
        accuracy_kw = ("不准", "错误", "不对", "误导", "inaccurate", "wrong", "incorrect", "misleading")
        if any(kw in lower for kw in accuracy_kw):
            problems.append(ProblemAnalysis(
                problem_type=ProblemType.PROMPT,
                severity=8.0,
                agent_id="primary",
                description=f"Reviewer notes indicate accuracy issue: '{notes[:120]}'",
                suggestion="Strengthen evidence-based grounding and clinical guideline adherence.",
            ))

        return problems
