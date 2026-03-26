"""Self-evolution loop for prompt and memory optimization."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import EVALUATION_OUTPUT_DIR, EVOLUTION_CONFIG, prompt_path_for

from .analyzer import AnalysisReport, AnalyzerAgent
from .evaluator import EvaluationReport, EvaluatorAgent
from .optimizers import MemoryOptimization, MemoryOptimizer, PromptOptimization, PromptOptimizer


@dataclass
class IterationResult:
    iteration: int
    evaluation: EvaluationReport
    analysis: AnalysisReport
    prompt_optimizations: List[Dict[str, Any]] = field(default_factory=list)
    memory_optimizations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration": self.iteration,
            "evaluation": self.evaluation.to_dict(),
            "analysis": self.analysis.to_dict(),
            "prompt_optimizations": self.prompt_optimizations,
            "memory_optimizations": self.memory_optimizations,
            "timestamp": self.timestamp,
        }


@dataclass
class EvolutionSummary:
    total_iterations: int
    initial_score: float
    final_score: float
    improvement: float
    prompt_versions: Dict[str, int]
    memory_operations: Dict[str, int]
    best_iteration: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_iterations": self.total_iterations,
            "initial_score": self.initial_score,
            "final_score": self.final_score,
            "improvement": self.improvement,
            "prompt_versions": self.prompt_versions,
            "memory_operations": self.memory_operations,
            "best_iteration": self.best_iteration,
        }


class SelfEvolutionLoop:
    """Runs iterative evaluation -> analysis -> optimization cycles."""

    def __init__(
        self,
        workflow,
        memory_agent,
        llm_client=None,
        max_iterations: int = EVOLUTION_CONFIG["max_iterations"],
        improvement_threshold: float = EVOLUTION_CONFIG["improvement_threshold"],
    ) -> None:
        self.workflow = workflow
        self.memory_agent = memory_agent
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.regression_tolerance = EVOLUTION_CONFIG["regression_tolerance"]

        self.evaluator = EvaluatorAgent(llm_client)
        self.analyzer = AnalyzerAgent(llm_client)
        self.prompt_optimizer = PromptOptimizer(llm_client)
        self.memory_optimizer = MemoryOptimizer(
            memory_client=memory_agent.client if memory_agent else None,
            llm_client=llm_client,
        )

        self.iteration_results: List[IterationResult] = []
        self.current_prompts = self._load_current_prompts()
        self.best_prompts = dict(self.current_prompts)
        self.best_average_score = 0.0

    def _load_current_prompts(self) -> Dict[str, str]:
        prompts: Dict[str, str] = {}
        for agent_id in ("primary", "pharmacist", "nutritionist", "doctor", "memory"):
            path = prompt_path_for(agent_id)
            prompts[agent_id] = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        return prompts

    def _apply_prompt(self, agent_id: str, prompt: str) -> None:
        self.current_prompts[agent_id] = prompt
        if agent_id == "memory":
            self.memory_agent.set_prompt(prompt)
            return

        attr_map = {
            "primary": "primary",
            "pharmacist": "pharmacist",
            "nutritionist": "nutritionist",
            "doctor": "doctor",
        }
        attr_name = attr_map.get(agent_id)
        if not attr_name:
            return
        agent = getattr(self.workflow, attr_name, None)
        if agent is not None:
            agent.system_prompt = prompt

    def run_single_iteration(self, test_case: Dict[str, Any], iteration: int) -> IterationResult:
        patient_id = (
            str(test_case.get("patient_reference") or "").strip()
            or str(test_case.get("patient_id") or "").strip()
            or "PAT_DEMO"
        )
        query = str(test_case.get("question") or test_case.get("query") or "").strip()
        patient_profile = dict(test_case.get("patient_profile") or {})

        workflow_result = self.workflow.process_patient_query(
            patient_id=patient_id,
            query=query,
            patient_context=patient_profile,
        )
        memories = self.memory_agent.search_relevant_memories(
            query=query,
            patient_id=patient_id,
            max_results=10,
        )

        response_score = self.evaluator.evaluate_response(
            patient_id=patient_id,
            query=query,
            response=str(workflow_result.get("primary_response") or ""),
            expert_opinions=dict(workflow_result.get("expert_opinions") or {}),
            patient_context=self.memory_agent.retrieve_patient_context(patient_id, query),
            use_llm=bool(self.llm_client),
        )
        memory_score = self.evaluator.evaluate_memory(
            patient_id=patient_id,
            memories=memories,
            patient_data=patient_profile,
            use_llm=bool(self.llm_client),
        )
        evaluation = self.evaluator.generate_report(
            patient_id=patient_id,
            query=query,
            response_score=response_score,
            memory_score=memory_score,
            iteration=iteration,
        )

        analysis = self.analyzer.analyze(
            evaluation_report=evaluation.to_dict(),
            agent_outputs=dict(workflow_result.get("expert_opinions") or {}),
            memories=memories,
        )

        prompt_opts: List[Dict[str, Any]] = []
        if analysis.should_optimize_prompt():
            for agent_id in analysis.prompt_target_agents():
                current_prompt = self.current_prompts.get(agent_id, "")
                if not current_prompt:
                    continue
                opt = self.prompt_optimizer.optimize(
                    agent_id=agent_id,
                    current_prompt=current_prompt,
                    analysis_report=analysis,
                )
                if not opt:
                    continue
                prompt_opts.append(opt.to_dict())
                self._apply_prompt(agent_id, opt.optimized_prompt)

        memory_opts: List[Dict[str, Any]] = []
        if analysis.should_optimize_memory():
            ops = self.memory_optimizer.optimize(
                patient_id=patient_id,
                analysis_report=analysis,
                current_memories=memories,
                dialogue_context={
                    "query": query,
                    "response": workflow_result.get("primary_response", ""),
                },
            )
            if ops:
                self.memory_optimizer.apply_operations(ops)
                memory_opts = [op.to_dict() for op in ops]

        result = IterationResult(
            iteration=iteration,
            evaluation=evaluation,
            analysis=analysis,
            prompt_optimizations=prompt_opts,
            memory_optimizations=memory_opts,
            timestamp=datetime.now().isoformat(),
        )
        self.iteration_results.append(result)
        return result

    def run(self, test_cases: List[Dict[str, Any]]) -> EvolutionSummary:
        if not test_cases:
            return EvolutionSummary(0, 0.0, 0.0, 0.0, {}, {"add": 0, "update": 0, "delete": 0}, 0)

        iteration_averages: List[float] = []
        for iteration in range(self.max_iterations):
            scores: List[float] = []
            start_index = len(self.iteration_results)
            for case in test_cases:
                result = self.run_single_iteration(case, iteration)
                scores.append(result.evaluation.response_score.overall)
            average = round(sum(scores) / len(scores), 2) if scores else 0.0
            iteration_averages.append(average)

            if average > self.best_average_score:
                self.best_average_score = average
                self.best_prompts = dict(self.current_prompts)
            elif self.best_average_score and average < self.best_average_score - self.regression_tolerance:
                for agent_id, prompt in self.best_prompts.items():
                    self._apply_prompt(agent_id, prompt)

            if iteration > 0:
                improvement = average - iteration_averages[iteration - 1]
                if improvement < self.improvement_threshold:
                    break

        initial = iteration_averages[0] if iteration_averages else 0.0
        final = self.best_average_score or (iteration_averages[-1] if iteration_averages else 0.0)
        best_iteration = max(range(len(iteration_averages)), key=lambda idx: iteration_averages[idx]) if iteration_averages else 0
        return EvolutionSummary(
            total_iterations=len(iteration_averages),
            initial_score=initial,
            final_score=final,
            improvement=round(final - initial, 2),
            prompt_versions=dict(self.prompt_optimizer.prompt_versions),
            memory_operations=self._memory_operation_counts(),
            best_iteration=best_iteration,
        )

    def _memory_operation_counts(self) -> Dict[str, int]:
        counts = {"add": 0, "update": 0, "delete": 0}
        for item in self.memory_optimizer.optimization_history:
            if item.operation in counts:
                counts[item.operation] += 1
        return counts

    def export_results(self, output_dir: Optional[str] = None) -> Path:
        target = Path(output_dir) if output_dir else EVALUATION_OUTPUT_DIR / "latest_demo"
        target.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        (target / f"iterations_{timestamp}.json").write_text(
            json.dumps([item.to_dict() for item in self.iteration_results], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (target / "prompt_evolution_log.json").write_text(
            json.dumps([item.to_dict() for item in self.prompt_optimizer.optimization_history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (target / "memory_evolution_log.json").write_text(
            json.dumps([item.to_dict() for item in self.memory_optimizer.optimization_history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
