"""Self-evolution loop for prompt and memory optimization.

Contains two loop variants:
1. SelfEvolutionLoop — legacy numeric-score driven (EvaluatorAgent)
2. HumanEvalEvolutionLoop — human-evaluation driven (EvaluationService, Line 3)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import EVALUATION_OUTPUT_DIR, EVOLUTION_CONFIG, prompt_path_for

from .analyzer import AnalysisReport, AnalyzerAgent
from .evaluator import EvaluationReport, EvaluatorAgent
from .evaluation_service import EvaluationService, HumanEvaluation, get_evaluation_service
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


# ── Human-Evaluation-Driven Evolution Loop (Line 3) ──────────────────


@dataclass
class HumanEvalCycleResult:
    """Result of processing a single human evaluation."""
    evaluation_id: str
    label: str
    analysis: AnalysisReport
    prompt_optimizations: List[Dict[str, Any]] = field(default_factory=list)
    memory_optimizations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluation_id": self.evaluation_id,
            "label": self.label,
            "analysis": self.analysis.to_dict(),
            "prompt_optimizations": self.prompt_optimizations,
            "memory_optimizations": self.memory_optimizations,
            "timestamp": self.timestamp,
        }


@dataclass
class HumanEvalEvolutionSummary:
    """Summary of a full human-eval-driven evolution run."""
    evaluations_processed: int
    prompt_optimizations_total: int
    memory_optimizations_total: int
    problems_found: int
    results: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluations_processed": self.evaluations_processed,
            "prompt_optimizations_total": self.prompt_optimizations_total,
            "memory_optimizations_total": self.memory_optimizations_total,
            "problems_found": self.problems_found,
            "results": self.results,
            "timestamp": self.timestamp,
        }


class HumanEvalEvolutionLoop:
    """Reads BAD/ERROR human evaluations and drives prompt + memory optimization.

    Flow:
        EvaluationService.get_bad_evaluations()
        → AnalyzerAgent.analyze_human_evaluation(eval)
        → if should_optimize_prompt: PromptOptimizer.optimize()
        → if should_optimize_memory: MemoryOptimizer.optimize()

    This is the Line 3 bridge: human scoring → automatic optimization.
    """

    def __init__(
        self,
        evaluation_service: Optional[EvaluationService] = None,
        memory_agent=None,
        llm_client=None,
    ) -> None:
        self.eval_service = evaluation_service or get_evaluation_service()
        self.memory_agent = memory_agent
        self.llm_client = llm_client

        self.analyzer = AnalyzerAgent(llm_client)
        self.prompt_optimizer = PromptOptimizer(llm_client)
        self.memory_optimizer = MemoryOptimizer(
            memory_client=memory_agent.client if memory_agent else None,
            llm_client=llm_client,
        )

        self.current_prompts = self._load_current_prompts()
        self.cycle_history: List[HumanEvalCycleResult] = []

    def _load_current_prompts(self) -> Dict[str, str]:
        prompts: Dict[str, str] = {}
        for agent_id in ("primary", "pharmacist", "nutritionist", "doctor", "memory"):
            path = prompt_path_for(agent_id)
            prompts[agent_id] = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        return prompts

    def process_single_evaluation(
        self,
        evaluation: HumanEvaluation,
    ) -> HumanEvalCycleResult:
        """Process one BAD/ERROR evaluation through the optimization pipeline."""

        # 1. Analyze: convert human label → ProblemAnalysis list
        analysis = self.analyzer.analyze_human_evaluation(evaluation)

        # 2. Prompt optimization path
        prompt_opts: List[Dict[str, Any]] = []
        if analysis.should_optimize_prompt(threshold=6.0):
            for agent_id in analysis.prompt_target_agents():
                current_prompt = self.current_prompts.get(agent_id, "")
                if not current_prompt:
                    continue
                opt = self.prompt_optimizer.optimize(
                    agent_id=agent_id,
                    current_prompt=current_prompt,
                    analysis_report=analysis,
                )
                if opt:
                    prompt_opts.append(opt.to_dict())
                    self.current_prompts[agent_id] = opt.optimized_prompt

        # 3. Memory reinforcement path
        memory_opts: List[Dict[str, Any]] = []
        if analysis.should_optimize_memory(threshold=5.5):
            patient_id = str(evaluation.patient_id or "").strip()
            # Gather current memories for this patient if possible
            current_memories: List[Dict[str, Any]] = []
            if self.memory_agent and patient_id:
                try:
                    current_memories = self.memory_agent.search_memories(
                        query=evaluation.query or "",
                        patient_id=patient_id,
                        max_results=10,
                    )
                except Exception:
                    pass

            ops = self.memory_optimizer.optimize(
                patient_id=patient_id,
                analysis_report=analysis,
                current_memories=current_memories,
                dialogue_context={
                    "query": evaluation.query or "",
                    "response": evaluation.response or "",
                },
            )
            if ops:
                self.memory_optimizer.apply_operations(ops)
                memory_opts = [op.to_dict() for op in ops]

        result = HumanEvalCycleResult(
            evaluation_id=evaluation.evaluation_id,
            label=evaluation.label,
            analysis=analysis,
            prompt_optimizations=prompt_opts,
            memory_optimizations=memory_opts,
            timestamp=datetime.now().isoformat(),
        )
        self.cycle_history.append(result)
        return result

    def run(self, limit: int = 20) -> HumanEvalEvolutionSummary:
        """Fetch recent BAD/ERROR evaluations and process them all.

        Args:
            limit: Maximum number of BAD/ERROR evaluations to process.

        Returns:
            Summary with counts of optimizations performed.
        """
        bad_evals = self.eval_service.get_bad_evaluations(limit=limit)

        results: List[Dict[str, Any]] = []
        total_prompt_opts = 0
        total_memory_opts = 0
        total_problems = 0

        for evaluation in bad_evals:
            cycle_result = self.process_single_evaluation(evaluation)
            results.append(cycle_result.to_dict())
            total_prompt_opts += len(cycle_result.prompt_optimizations)
            total_memory_opts += len(cycle_result.memory_optimizations)
            total_problems += len(cycle_result.analysis.problems)

        return HumanEvalEvolutionSummary(
            evaluations_processed=len(bad_evals),
            prompt_optimizations_total=total_prompt_opts,
            memory_optimizations_total=total_memory_opts,
            problems_found=total_problems,
            results=results,
            timestamp=datetime.now().isoformat(),
        )

    def export_results(self, output_dir: Optional[str] = None) -> Path:
        """Export human-eval evolution results to disk."""
        target = Path(output_dir) if output_dir else EVALUATION_OUTPUT_DIR / "human_eval_evolution"
        target.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        (target / f"human_eval_cycles_{timestamp}.json").write_text(
            json.dumps([item.to_dict() for item in self.cycle_history], ensure_ascii=False, indent=2),
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
