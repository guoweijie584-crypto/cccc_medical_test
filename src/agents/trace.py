"""Consultation Trace — full tracing record for a single patient consultation."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConsultationTrace:
    """一轮咨询的完整追踪记录。"""

    trace_id: str  # UUID
    request_id: str  # 请求唯一标识
    session_id: str  # 会话标识
    patient_id: str
    timestamp_start: str  # ISO 格式
    timestamp_end: str

    # 输入
    original_query: str
    rewritten_query: Optional[str] = None  # Coordinator 重述后的问题
    query_type: Optional[str] = None  # 问题分类: medication/diet/exercise/glucose/complication/general/emergency
    routing_decision: Optional[Dict[str, Any]] = None  # 路由决策详情

    # 记忆上下文
    retrieved_memory_keys: List[str] = field(default_factory=list)  # 检索到的记忆 URI
    memory_dossier_summary: str = ""  # 上下文摘要

    # 路由与专家
    routed_agents: List[str] = field(default_factory=list)  # 调用了哪些专家
    expert_outputs: Dict[str, Any] = field(default_factory=dict)  # 各专家原始输出

    # 汇总
    synthesis_method: str = "coordinator_merge"  # 汇总方式
    final_response: str = ""

    # 安全审查
    safety_review_passed: bool = True
    safety_risk_level: str = "safe"
    safety_issues: List[str] = field(default_factory=list)

    # 记忆写回
    writeback_candidates: List[Dict[str, Any]] = field(default_factory=list)
    writeback_results: List[str] = field(default_factory=list)  # 写入的 URI

    # 评价
    evaluation_id: Optional[str] = None

    # 性能
    latency_total_ms: float = 0.0
    latency_memory_ms: float = 0.0
    latency_experts_ms: float = 0.0
    latency_synthesis_ms: float = 0.0
    latency_safety_ms: float = 0.0

    # 错误
    errors: List[Dict[str, str]] = field(default_factory=list)  # [{agent, error, timestamp}]
    partial_failure: bool = False

    # 模式
    mode: str = "mock"  # mock / llm

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConsultationTrace":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return uuid.uuid4().hex


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return uuid.uuid4().hex[:16]
