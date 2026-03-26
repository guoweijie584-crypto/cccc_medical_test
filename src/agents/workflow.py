"""Main workflow for the glucose-management multi-agent system."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from .doctor_agent import DoctorAgent, MockDoctorAgent
from .nutritionist_agent import NutritionistAgent, MockNutritionistAgent
from .pharmacist_agent import PharmacistAgent, MockPharmacistAgent
from .primary_agent import MockPrimaryAgent, PrimaryAgent
from ..llm_client import get_llm_client
from ..memory import get_memory_agent


class GlucoseManagementWorkflow:
    """Orchestrates memory retrieval, specialist reasoning, synthesis, and memory write-back."""

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
        else:
            self.primary = PrimaryAgent(self.llm_client)
            self.pharmacist = PharmacistAgent(self.llm_client)
            self.nutritionist = NutritionistAgent(self.llm_client)
            self.doctor = DoctorAgent(self.llm_client)

    def process_patient_query(
        self,
        patient_id: str,
        query: str,
        *,
        enable_parallel: bool = True,
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        context = self.memory_agent.build_agent_context(
            patient_id=patient_id,
            agent_type="primary",
            current_query=query,
        )

        if enable_parallel:
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    "pharmacist": executor.submit(self.pharmacist.process_sync, context, query),
                    "nutritionist": executor.submit(self.nutritionist.process_sync, context, query),
                    "doctor": executor.submit(self.doctor.process_sync, context, query),
                }
                expert_outputs = {
                    key: future.result(timeout=15)
                    for key, future in futures.items()
                }
        else:
            expert_outputs = {
                "pharmacist": self.pharmacist.process_sync(context, query),
                "nutritionist": self.nutritionist.process_sync(context, query),
                "doctor": self.doctor.process_sync(context, query),
            }

        expert_opinions = {
            key: str(payload.get("response") or "").strip()
            for key, payload in expert_outputs.items()
        }

        primary_result = self.primary.process_sync(
            context=context,
            query=query,
            expert_opinions=expert_opinions,
        )
        primary_response = str(primary_result.get("response") or "").strip()

        dialogue = {
            "turn": len(self.memory_agent.session_memories.get(patient_id, [])) + 1,
            "speaker": "patient",
            "content": query,
            "assistant_response": primary_response,
        }
        extracted_facts = self.memory_agent.extract_facts_from_interaction(
            patient_id=patient_id,
            query=query,
            primary_response=primary_response,
            expert_opinions=expert_opinions,
        )
        stored_uris = self.memory_agent.extract_and_store(
            patient_id=patient_id,
            dialogue=dialogue,
            extracted_facts=extracted_facts,
        )

        end_time = datetime.now()
        return {
            "patient_id": patient_id,
            "query": query,
            "patient_context": patient_context or {},
            "context": self.memory_agent.retrieve_patient_context(patient_id, query),
            "expert_opinions": expert_opinions,
            "primary_response": primary_response,
            "stored_memory_uris": stored_uris,
            "extracted_facts": extracted_facts,
            "processing_time": (end_time - start_time).total_seconds(),
            "timestamp": end_time.isoformat(),
            "mode": "mock" if self.use_mock else "llm",
        }

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
