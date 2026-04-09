"""Main workflow for the glucose-management multi-agent system."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from .doctor_agent import DoctorAgent, MockDoctorAgent
from .nutritionist_agent import NutritionistAgent, MockNutritionistAgent
from .pharmacist_agent import PharmacistAgent, MockPharmacistAgent
from .primary_agent import MockPrimaryAgent, PrimaryAgent
from .safety_reviewer import (
    MockSafetyReviewerAgent,
    SafetyReviewerAgent,
    SafetyReviewResult,
)
from .trace import ConsultationTrace, generate_trace_id, generate_request_id
from ..llm_client import get_llm_client
from ..memory import get_memory_agent

logger = logging.getLogger(__name__)


# 安全降级 fallback 回复
_DANGER_FALLBACK_RESPONSE = (
    "⚠️ 系统安全审查提示：您的问题涉及需要专业医生判断的情况。"
    "为了您的安全，请尽快联系您的主治医生或前往医院就诊。"
    "在等待就医期间，请勿自行调整药物或治疗方案。"
    "\n\n如遇紧急情况（严重低血糖、意识模糊、酮症酸中毒症状等），请立即拨打 120 急救电话。"
)

_SAFETY_CAUTION_TEMPLATE = (
    "\n\n---\n"
    "⚠️ **安全提醒**：{issues}\n"
    "如有任何疑问或不适，请及时咨询您的主治医生。"
)


class GlucoseManagementWorkflow:
    """Orchestrates memory retrieval, specialist reasoning, synthesis, and memory write-back."""

    # ── Query classification rules (mock mode) ────────────────────
    _CLASSIFICATION_RULES: List[Dict[str, Any]] = [
        {
            "keywords": ("低血糖", "急", "严重", "酮症", "酮症酸中毒", "DKA", "昏迷", "意识"),
            "query_type": "emergency",
            "needs_specialists": ["pharmacist", "nutritionist", "doctor"],
        },
        {
            "keywords": ("药", "胰岛素", "二甲双胍", "格列", "阿卡波糖", "用药", "剂量", "处方"),
            "query_type": "medication",
            "needs_specialists": ["pharmacist", "doctor"],
        },
        {
            "keywords": ("吃", "饮食", "水果", "碳水", "早餐", "午餐", "晚餐", "食物", "GI", "食谱"),
            "query_type": "diet",
            "needs_specialists": ["nutritionist"],
        },
        {
            "keywords": ("运动", "锻炼", "步行", "跑步", "健身", "有氧", "散步"),
            "query_type": "exercise",
            "needs_specialists": ["nutritionist", "doctor"],
        },
        {
            "keywords": ("血糖", "mmol", "监测", "空腹", "餐后"),
            "query_type": "glucose",
            "needs_specialists": ["doctor"],
        },
        {
            "keywords": ("并发症", "肾", "眼底", "足", "神经", "视网膜"),
            "query_type": "complication",
            "needs_specialists": ["doctor"],
        },
    ]

    def __init__(self, use_mock: bool = True, llm_client=None) -> None:
        self.use_mock = bool(use_mock)
        self.llm_client = llm_client or get_llm_client()
        self.memory_agent = get_memory_agent()
        self.executor = ThreadPoolExecutor(max_workers=4)

        if self.use_mock:
            self.primary = MockPrimaryAgent()
            self.pharmacist = MockPharmacistAgent()
            self.nutritionist = MockNutritionistAgent()
            self.doctor = MockDoctorAgent()
            self.safety_reviewer = MockSafetyReviewerAgent()
        else:
            self.primary = PrimaryAgent(self.llm_client)
            self.pharmacist = PharmacistAgent(self.llm_client)
            self.nutritionist = NutritionistAgent(self.llm_client)
            self.doctor = DoctorAgent(self.llm_client)
            self.safety_reviewer = SafetyReviewerAgent(self.llm_client)

    # ── Coordinator: query rewriting & classification ─────────────

    def _rewrite_query(self, original_query: str, patient_context: str) -> Dict[str, Any]:
        """Coordinator 重述问题：规范化、消歧、分类。

        Returns:
            {
                "rewritten_query": str,   # 规范化后的查询
                "query_type": str,        # medication/diet/exercise/glucose/complication/general/emergency
                "needs_specialists": list, # ["pharmacist","nutritionist","doctor"] 的子集
            }
        """
        if self.use_mock:
            return self._rewrite_query_mock(original_query)
        return self._rewrite_query_llm(original_query, patient_context)

    def _rewrite_query_mock(self, original_query: str) -> Dict[str, Any]:
        """Mock 模式：用关键词匹配做简单分类。"""
        # 按优先级匹配规则（emergency 最先）
        for rule in self._CLASSIFICATION_RULES:
            if any(kw in original_query for kw in rule["keywords"]):
                return {
                    "rewritten_query": original_query,
                    "query_type": rule["query_type"],
                    "needs_specialists": list(rule["needs_specialists"]),
                }
        # 无匹配 → general → 需要所有专家
        return {
            "rewritten_query": original_query,
            "query_type": "general",
            "needs_specialists": ["pharmacist", "nutritionist", "doctor"],
        }

    def _rewrite_query_llm(self, original_query: str, patient_context: str) -> Dict[str, Any]:
        """LLM 模式：使用 LLM 做问题重述和分类。"""
        prompt = (
            "你是一个糖尿病管理系统的 Coordinator。请对以下患者问题进行重述和分类。\n\n"
            f"## 患者上下文\n{patient_context}\n\n"
            f"## 原始问题\n{original_query}\n\n"
            "请返回严格的 JSON 格式（不要其他文字）：\n"
            "{\n"
            '  "rewritten_query": "规范化后的问题（消除歧义、补充上下文、简洁明确）",\n'
            '  "query_type": "medication|diet|exercise|glucose|complication|general|emergency 之一",\n'
            '  "needs_specialists": ["需要咨询的专家列表，可选 pharmacist/nutritionist/doctor"]\n'
            "}\n\n"
            "分类规则：\n"
            "- medication: 涉及药物、胰岛素、剂量调整\n"
            "- diet: 涉及饮食、食物选择、碳水控制\n"
            "- exercise: 涉及运动、锻炼\n"
            "- glucose: 涉及血糖监测、血糖数值解读\n"
            "- complication: 涉及并发症\n"
            "- emergency: 涉及低血糖急救、酮症酸中毒等紧急情况\n"
            "- general: 其他一般性咨询\n"
            "注意：emergency 类型必须路由到所有三个专家。"
        )

        try:
            result = self.llm_client.json_completion_sync(
                messages=[
                    {"role": "system", "content": "你是糖尿病管理系统的问题分类器。只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            # Validate and provide defaults
            rewritten = str(result.get("rewritten_query", "")).strip() or original_query
            query_type = str(result.get("query_type", "general")).strip()
            valid_types = {"medication", "diet", "exercise", "glucose", "complication", "general", "emergency"}
            if query_type not in valid_types:
                query_type = "general"
            needs = result.get("needs_specialists", [])
            valid_specialists = {"pharmacist", "nutritionist", "doctor"}
            needs = [s for s in needs if s in valid_specialists]
            if not needs or query_type == "emergency":
                needs = ["pharmacist", "nutritionist", "doctor"]
            return {
                "rewritten_query": rewritten,
                "query_type": query_type,
                "needs_specialists": needs,
            }
        except Exception as exc:
            logger.warning("LLM query rewriting failed, falling back to mock: %s", exc)
            return self._rewrite_query_mock(original_query)

    # ── Main query processing ────────────────────────────────────

    def process_patient_query(
        self,
        patient_id: str,
        query: str,
        *,
        enable_parallel: bool = True,
        patient_context: Optional[Dict[str, Any]] = None,
        session_id: str = "",
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        t0 = time.perf_counter()

        # ── Generate trace identifiers ─────────────────────────────
        trace_id = generate_trace_id()
        request_id = generate_request_id()

        trace = ConsultationTrace(
            trace_id=trace_id,
            request_id=request_id,
            session_id=session_id or f"session_{trace_id[:8]}",
            patient_id=patient_id,
            timestamp_start=start_time.isoformat(),
            timestamp_end="",
            original_query=query,
            mode="mock" if self.use_mock else "llm",
        )

        # ── Step 1: Memory retrieval ───────────────────────────────
        t_memory_start = time.perf_counter()
        context = self.memory_agent.build_agent_context(
            patient_id=patient_id,
            agent_type="primary",
            current_query=query,
        )
        t_memory_end = time.perf_counter()
        trace.latency_memory_ms = (t_memory_end - t_memory_start) * 1000.0

        # Capture retrieved memory keys from context
        for bucket in ("recent_memories", "session_history"):
            for entry in context.get(bucket, []):
                uri = entry.get("uri") if isinstance(entry, dict) else ""
                if uri:
                    trace.retrieved_memory_keys.append(uri)
        trace.memory_dossier_summary = str(context.get("summary", ""))

        # ── Step 1.5: Coordinator query rewrite & classification ──
        rewrite_result = self._rewrite_query(query, context)
        effective_query = rewrite_result["rewritten_query"]
        query_type = rewrite_result["query_type"]
        needs_specialists = rewrite_result["needs_specialists"]

        trace.rewritten_query = effective_query
        trace.query_type = query_type
        trace.routing_decision = {
            "query_type": query_type,
            "needs_specialists": needs_specialists,
            "original_query": query,
            "rewritten_query": effective_query,
        }

        # ── Step 2: Expert consultation (dynamic routing) ─────────
        t_experts_start = time.perf_counter()
        expert_outputs: Dict[str, Any] = {}
        all_expert_agents = {
            "pharmacist": self.pharmacist,
            "nutritionist": self.nutritionist,
            "doctor": self.doctor,
        }
        # Only route to needed specialists
        expert_agents = {
            name: agent
            for name, agent in all_expert_agents.items()
            if name in needs_specialists
        }

        if enable_parallel:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    name: executor.submit(agent.process_sync, context, effective_query)
                    for name, agent in expert_agents.items()
                }
                for name, future in futures.items():
                    try:
                        expert_outputs[name] = future.result(timeout=15)
                        trace.routed_agents.append(name)
                    except Exception as exc:
                        trace.errors.append({
                            "agent": name,
                            "error": str(exc),
                            "timestamp": datetime.now().isoformat(),
                        })
                        trace.partial_failure = True
        else:
            for name, agent in expert_agents.items():
                try:
                    expert_outputs[name] = agent.process_sync(context, effective_query)
                    trace.routed_agents.append(name)
                except Exception as exc:
                    trace.errors.append({
                        "agent": name,
                        "error": str(exc),
                        "timestamp": datetime.now().isoformat(),
                    })
                    trace.partial_failure = True

        t_experts_end = time.perf_counter()
        trace.latency_experts_ms = (t_experts_end - t_experts_start) * 1000.0
        trace.expert_outputs = expert_outputs

        expert_opinions = {
            key: str(payload.get("response") or "").strip()
            for key, payload in expert_outputs.items()
        }

        # ── Step 3: Synthesis ──────────────────────────────────────
        t_synthesis_start = time.perf_counter()
        primary_result = self.primary.process_sync(
            context=context,
            query=query,
            expert_opinions=expert_opinions,
        )
        primary_response = str(primary_result.get("response") or "").strip()
        t_synthesis_end = time.perf_counter()
        trace.latency_synthesis_ms = (t_synthesis_end - t_synthesis_start) * 1000.0
        trace.final_response = primary_response

        # ── Step 3.5: Safety review ───────────────────────────────
        t_safety_start = time.perf_counter()
        safety_result: SafetyReviewResult = self.safety_reviewer.review_sync(
            query=query,
            response=primary_response,
            expert_opinions=expert_opinions,
            patient_context=str(context) if context else None,
        )
        t_safety_end = time.perf_counter()
        trace.routed_agents.append("safety_reviewer")
        trace.latency_safety_ms = (t_safety_end - t_safety_start) * 1000.0
        trace.safety_review_passed = safety_result.passed
        trace.safety_risk_level = safety_result.risk_level
        trace.safety_issues = list(safety_result.issues or [])

        # Apply safety policy to primary_response
        if not safety_result.passed and safety_result.risk_level == "danger":
            # Danger: replace entire response with safe fallback
            primary_response = (
                safety_result.modified_response
                if safety_result.modified_response
                else _DANGER_FALLBACK_RESPONSE
            )
            trace.final_response = primary_response
        elif safety_result.risk_level in ("warning", "caution") and safety_result.issues:
            # Warning / Caution: append safety reminder to response
            issues_text = "；".join(safety_result.issues)
            if safety_result.modified_response:
                primary_response = primary_response + "\n\n" + safety_result.modified_response
            else:
                primary_response = primary_response + _SAFETY_CAUTION_TEMPLATE.format(
                    issues=issues_text
                )
            trace.final_response = primary_response

        # ── Step 4: Memory write-back ──────────────────────────────
        dialogue = {
            "speaker": "patient",
            "content": query,
            "assistant_response": primary_response,
            "timestamp": datetime.now().isoformat(),
        }
        extracted_facts = self.memory_agent.extract_facts_from_interaction(
            patient_id=patient_id,
            query=query,
            primary_response=primary_response,
            expert_opinions=expert_opinions,
        )
        trace.writeback_candidates = [
            f.to_content_dict() if hasattr(f, "to_content_dict")
            else ({"fact": f} if isinstance(f, str) else f)
            for f in (extracted_facts or [])
        ]

        stored_uris = self.memory_agent.extract_and_store(
            patient_id=patient_id,
            dialogue=dialogue,
            extracted_facts=extracted_facts,
        )
        trace.writeback_results = list(stored_uris or [])

        # Also store the full consultation record
        self.memory_agent.store_consultation_record(
            patient_id=patient_id,
            query=query,
            response=primary_response,
            expert_opinions=expert_opinions,
        )

        # ── Finalize trace ─────────────────────────────────────────
        end_time = datetime.now()
        trace.timestamp_end = end_time.isoformat()
        trace.latency_total_ms = (time.perf_counter() - t0) * 1000.0

        # Persist trace to Memory Palace
        self._persist_trace(trace)

        return {
            "patient_id": patient_id,
            "query": query,
            "patient_context": patient_context or {},
            "context": self.memory_agent.retrieve_patient_context(patient_id, query),
            "expert_opinions": expert_opinions,
            "primary_response": primary_response,
            "safety_review": safety_result.to_dict(),
            "stored_memory_uris": stored_uris,
            "extracted_facts": [
                f.to_legacy_dict() if hasattr(f, "to_legacy_dict") else f
                for f in (extracted_facts or [])
            ],
            "processing_time": (end_time - start_time).total_seconds(),
            "timestamp": end_time.isoformat(),
            "mode": "mock" if self.use_mock else "llm",
            "trace": trace.to_dict(),
        }

    def _persist_trace(self, trace: ConsultationTrace) -> None:
        """Persist a consultation trace to Memory Palace."""
        try:
            self.memory_agent.client.create(
                path=f"traces/{trace.trace_id}",
                content=trace.to_json(),
                priority=4,
                disclosure="当审查系统追踪记录时",
            )
        except Exception:
            # Trace persistence is non-critical; do not break the workflow
            pass

    def process_query(
        self,
        patient_id: str,
        query: str,
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        result = self.process_patient_query(
            patient_id=patient_id,
            query=query,
            patient_context=patient_context,
        )
        return str(result.get("primary_response") or "")

    def process_batch(
        self,
        queries: List[Dict[str, str]],
        *,
        enable_parallel: bool = True,
    ) -> List[Dict[str, Any]]:
        return [
            self.process_patient_query(
                patient_id=item["patient_id"],
                query=item["query"],
                enable_parallel=enable_parallel,
            )
            for item in queries
        ]


def process_glucose_query(
    patient_id: str,
    query: str,
    *,
    use_mock: bool = True,
    llm_client=None,
) -> Dict[str, Any]:
    workflow = GlucoseManagementWorkflow(use_mock=use_mock, llm_client=llm_client)
    return workflow.process_patient_query(patient_id, query)
