"""Helpers for running and formatting the demo evolution pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import EVALUATION_DATASET_FILE, EVALUATION_OUTPUT_DIR, EVOLUTION_CONFIG
from src.agents import GlucoseManagementWorkflow
from src.llm_client import get_llm_client
from src.memory import get_memory_agent

from .self_evolution_loop import SelfEvolutionLoop


def load_test_cases(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not EVALUATION_DATASET_FILE.exists():
        return []
    payload = json.loads(EVALUATION_DATASET_FILE.read_text(encoding="utf-8"))
    cases = list(payload.get("test_cases") or [])
    if limit is not None:
        return cases[:limit]
    return cases


def run_demo_evaluation(
    *,
    iterations: Optional[int] = None,
    case_limit: Optional[int] = None,
    use_mock: Optional[bool] = None,
    export: bool = True,
) -> Dict[str, Any]:
    llm_client = get_llm_client()
    effective_use_mock = bool(use_mock) if use_mock is not None else (not llm_client.available)
    workflow = GlucoseManagementWorkflow(use_mock=effective_use_mock, llm_client=llm_client)
    memory_agent = get_memory_agent()
    loop = SelfEvolutionLoop(
        workflow=workflow,
        memory_agent=memory_agent,
        llm_client=llm_client if llm_client.available else None,
        max_iterations=iterations or EVOLUTION_CONFIG["max_iterations"],
        improvement_threshold=EVOLUTION_CONFIG["improvement_threshold"],
    )
    test_cases = load_test_cases(case_limit or EVOLUTION_CONFIG["default_eval_cases"])
    summary = loop.run(test_cases)
    export_dir = loop.export_results(str(EVALUATION_OUTPUT_DIR / "latest_demo")) if export else None
    return {
        "summary": summary,
        "iteration_results": loop.iteration_results,
        "export_dir": str(export_dir) if export_dir else None,
        "mode": "mock" if effective_use_mock else "llm",
    }


def build_ui_report(run_result: Dict[str, Any]) -> Dict[str, Any]:
    summary = run_result["summary"]
    iteration_results = list(run_result["iteration_results"] or [])
    grouped: Dict[int, Dict[str, Any]] = {}

    for item in iteration_results:
        bucket = grouped.setdefault(
            item.iteration,
            {
                "iteration": item.iteration,
                "scores": [],
                "medical": [],
                "safety": [],
                "completeness": [],
                "personalization": [],
                "consistency": [],
                "promptChanges": 0,
                "memoryChanges": 0,
                "timestamp": item.timestamp,
                "promptDetails": [],
                "memoryDetails": [],
            },
        )
        bucket["scores"].append(item.evaluation.response_score.overall)
        bucket["medical"].append(item.evaluation.response_score.medical_accuracy)
        bucket["safety"].append(item.evaluation.response_score.safety)
        bucket["completeness"].append(item.evaluation.response_score.completeness)
        bucket["personalization"].append(item.evaluation.response_score.personalization)
        bucket["consistency"].append(item.evaluation.response_score.consistency)
        bucket["promptChanges"] += len(item.prompt_optimizations)
        bucket["memoryChanges"] += len(item.memory_optimizations)
        bucket["promptDetails"].extend(item.prompt_optimizations)
        bucket["memoryDetails"].extend(item.memory_optimizations)

    iterations: List[Dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        bucket = grouped[key]
        count = max(len(bucket["scores"]), 1)
        iterations.append(
            {
                "iteration": key + 1,
                "timestamp": bucket["timestamp"],
                "avgScore": round(sum(bucket["scores"]) / count, 2),
                "medicalAccuracy": round(sum(bucket["medical"]) / count, 2),
                "safety": round(sum(bucket["safety"]) / count, 2),
                "completeness": round(sum(bucket["completeness"]) / count, 2),
                "personalization": round(sum(bucket["personalization"]) / count, 2),
                "consistency": round(sum(bucket["consistency"]) / count, 2),
                "promptChanges": int(bucket["promptChanges"]),
                "memoryChanges": int(bucket["memoryChanges"]),
                "promptDetails": list(bucket["promptDetails"]),
                "memoryDetails": list(bucket["memoryDetails"]),
            }
        )

    return {
        "summary": {
            "initialScore": summary.initial_score,
            "finalScore": summary.final_score,
            "improvement": summary.improvement,
            "bestIteration": summary.best_iteration + 1 if summary.total_iterations else 0,
            "promptVersions": summary.prompt_versions,
            "memoryOperations": summary.memory_operations,
            "mode": run_result.get("mode", "mock"),
        },
        "iterations": iterations,
        "exportDir": run_result.get("export_dir"),
    }
