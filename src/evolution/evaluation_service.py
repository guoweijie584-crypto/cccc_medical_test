"""
Evaluation Service — Human Doctor Evaluation System

Core principle: Agent self-evaluation is unreliable.
All quality judgments come from real human doctors.

Evaluation labels:
    GOOD    — Response is accurate, safe, and helpful
    BAD     — Response has clear problems
    NEUTRAL — Acceptable but unremarkable
    ERROR   — Safety risk or unable to judge, needs detailed review
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..memory.palace_client import MemoryPalaceClient


# ── Constants ───────────────────────────────────────────────────────

VALID_LABELS = {"GOOD", "BAD", "NEUTRAL", "ERROR"}
VALID_SAFETY = {"safe", "risky", "dangerous"}
VALID_ADVICE_DIRECTION = {"correct", "partial", "wrong"}


# ── Data structures ─────────────────────────────────────────────────

@dataclass
class HumanEvaluation:
    """A single human doctor evaluation record."""
    evaluation_id: str
    patient_id: str
    query: str
    response: str
    expert_opinions: Dict[str, str]

    # Core evaluation (required)
    label: str = ""  # GOOD / BAD / NEUTRAL / ERROR

    # Optional extensions
    safety: Optional[str] = None            # safe / risky / dangerous
    personalized: Optional[bool] = None     # True / False
    advice_direction: Optional[str] = None  # correct / partial / wrong

    # Notes
    reviewer_notes: str = ""
    reviewer_id: str = ""

    # Metadata
    timestamp: str = ""             # when evaluation was submitted
    consultation_timestamp: str = ""  # when original consultation happened
    status: str = "pending"         # pending / completed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HumanEvaluation":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


@dataclass
class EvaluationStats:
    """Aggregated evaluation statistics."""
    total: int = 0
    good: int = 0
    bad: int = 0
    neutral: int = 0
    error: int = 0
    pending: int = 0

    @property
    def good_rate(self) -> float:
        completed = self.total - self.pending
        if completed <= 0:
            return 0.0
        return round(self.good / completed, 3)

    @property
    def needs_attention(self) -> int:
        return self.bad + self.error

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["good_rate"] = self.good_rate
        d["needs_attention"] = self.needs_attention
        return d


# ── Service ─────────────────────────────────────────────────────────

class EvaluationService:
    """Human evaluation management service.

    Does NOT perform any automatic scoring.
    Manages the lifecycle of evaluation records:
    create pending → doctor submits label → data available for self-evolution.
    """

    def __init__(
        self,
        palace_client: Optional[MemoryPalaceClient] = None,
    ) -> None:
        self.client = palace_client or MemoryPalaceClient()
        self._local_cache: Dict[str, HumanEvaluation] = {}

    # ── Create pending evaluation ───────────────────────────────────

    def create_pending_evaluation(
        self,
        patient_id: str,
        query: str,
        response: str,
        expert_opinions: Optional[Dict[str, str]] = None,
    ) -> HumanEvaluation:
        """Create a pending evaluation record after a consultation.

        Called automatically by the workflow after each patient interaction.
        """
        eval_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        evaluation = HumanEvaluation(
            evaluation_id=eval_id,
            patient_id=patient_id,
            query=query,
            response=response,
            expert_opinions=expert_opinions or {},
            consultation_timestamp=now,
            status="pending",
        )

        # Store in Memory Palace
        path = f"evaluations/pending/{eval_id}"
        self.client.create(
            path=path,
            content=evaluation.to_json(),
            priority=3,
            disclosure="当医生进行质量评价时",
        )

        # Cache locally
        self._local_cache[eval_id] = evaluation
        return evaluation

    # ── Submit evaluation ───────────────────────────────────────────

    def submit_evaluation(
        self,
        evaluation_id: str,
        label: str,
        *,
        safety: Optional[str] = None,
        personalized: Optional[bool] = None,
        advice_direction: Optional[str] = None,
        reviewer_notes: str = "",
        reviewer_id: str = "",
    ) -> HumanEvaluation:
        """Doctor submits an evaluation for a pending record.

        Args:
            evaluation_id: The evaluation to complete
            label: Required. One of GOOD / BAD / NEUTRAL / ERROR
            safety: Optional. safe / risky / dangerous
            personalized: Optional. True / False
            advice_direction: Optional. correct / partial / wrong
            reviewer_notes: Optional. Free text from the doctor
            reviewer_id: Optional. Doctor identifier
        """
        label_upper = label.strip().upper()
        if label_upper not in VALID_LABELS:
            raise ValueError(
                f"Invalid label '{label}'. Must be one of: {', '.join(sorted(VALID_LABELS))}"
            )
        if safety and safety not in VALID_SAFETY:
            raise ValueError(
                f"Invalid safety '{safety}'. Must be one of: {', '.join(sorted(VALID_SAFETY))}"
            )
        if advice_direction and advice_direction not in VALID_ADVICE_DIRECTION:
            raise ValueError(
                f"Invalid advice_direction '{advice_direction}'. "
                f"Must be one of: {', '.join(sorted(VALID_ADVICE_DIRECTION))}"
            )

        # Load evaluation
        evaluation = self._load_evaluation(evaluation_id)
        if evaluation is None:
            raise ValueError(f"Evaluation {evaluation_id} not found")

        # Update fields
        evaluation.label = label_upper
        evaluation.safety = safety
        evaluation.personalized = personalized
        evaluation.advice_direction = advice_direction
        evaluation.reviewer_notes = reviewer_notes
        evaluation.reviewer_id = reviewer_id
        evaluation.timestamp = datetime.now().isoformat()
        evaluation.status = "completed"

        # Move from pending to completed in Memory Palace
        self.client.delete(f"evaluations/pending/{evaluation_id}")
        self.client.create(
            path=f"evaluations/completed/{evaluation_id}",
            content=evaluation.to_json(),
            priority=2 if label_upper in ("BAD", "ERROR") else 4,
            disclosure=(
                "当分析系统回答质量问题时"
                if label_upper in ("BAD", "ERROR")
                else "当统计评价数据时"
            ),
        )

        # Update cache
        self._local_cache[evaluation_id] = evaluation
        return evaluation

    # ── Query methods ───────────────────────────────────────────────

    def get_pending_evaluations(self, limit: int = 20) -> List[HumanEvaluation]:
        """Get pending evaluations for doctors to review."""
        results = self.client.search(
            query="evaluation pending",
            max_results=limit,
            path_prefix="evaluations/pending",
        )
        evaluations = []
        for item in results:
            content = item.get("content", "")
            data = self._parse_content(content)
            if data and data.get("evaluation_id"):
                evaluations.append(HumanEvaluation.from_dict(data))
        return evaluations

    def get_evaluation(self, evaluation_id: str) -> Optional[HumanEvaluation]:
        """Get a single evaluation by ID."""
        return self._load_evaluation(evaluation_id)

    def get_bad_evaluations(self, limit: int = 10) -> List[HumanEvaluation]:
        """Get recent BAD and ERROR evaluations for self-evolution analysis."""
        results = self.client.search(
            query="BAD ERROR evaluation",
            max_results=limit,
            path_prefix="evaluations/completed",
        )
        evaluations = []
        for item in results:
            content = item.get("content", "")
            data = self._parse_content(content)
            if data and data.get("label") in ("BAD", "ERROR"):
                evaluations.append(HumanEvaluation.from_dict(data))
        return evaluations

    def get_evaluation_stats(
        self,
        patient_id: Optional[str] = None,
    ) -> EvaluationStats:
        """Get aggregated evaluation statistics."""
        stats = EvaluationStats()

        # Count pending
        pending = self.client.search(
            query="evaluation pending",
            max_results=100,
            path_prefix="evaluations/pending",
        )
        stats.pending = len(pending)

        # Count completed by label
        completed = self.client.search(
            query="evaluation completed",
            max_results=100,
            path_prefix="evaluations/completed",
        )
        for item in completed:
            data = self._parse_content(item.get("content", ""))
            if not data:
                continue
            if patient_id and data.get("patient_id") != patient_id:
                continue
            label = str(data.get("label", "")).upper()
            if label == "GOOD":
                stats.good += 1
            elif label == "BAD":
                stats.bad += 1
            elif label == "NEUTRAL":
                stats.neutral += 1
            elif label == "ERROR":
                stats.error += 1

        stats.total = stats.pending + stats.good + stats.bad + stats.neutral + stats.error
        return stats

    # ── Helpers ─────────────────────────────────────────────────────

    def _load_evaluation(self, evaluation_id: str) -> Optional[HumanEvaluation]:
        """Load evaluation from cache or Memory Palace."""
        if evaluation_id in self._local_cache:
            return self._local_cache[evaluation_id]

        # Try completed first, then pending
        for prefix in ("evaluations/completed", "evaluations/pending"):
            path = f"{prefix}/{evaluation_id}"
            record = self.client.read(path)
            if record and record.get("content"):
                data = self._parse_content(record["content"])
                if data:
                    evaluation = HumanEvaluation.from_dict(data)
                    self._local_cache[evaluation_id] = evaluation
                    return evaluation
        return None

    @staticmethod
    def _parse_content(content: Any) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if not content:
            return {}
        try:
            return json.loads(str(content))
        except (json.JSONDecodeError, TypeError):
            return {}


# ── Module-level singleton ──────────────────────────────────────────

_evaluation_service: Optional[EvaluationService] = None


def get_evaluation_service() -> EvaluationService:
    global _evaluation_service
    if _evaluation_service is None:
        _evaluation_service = EvaluationService()
    return _evaluation_service
