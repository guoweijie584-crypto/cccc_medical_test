"""
Evolution Module — Self-Evolution System

Components:
- EvaluationService: Human doctor evaluation collection (replaces old EvaluatorAgent)
- AnalyzerAgent: Root-cause analysis (triggered by BAD/ERROR human evaluations)
- PromptOptimizer: Prompt optimization
- MemoryOptimizer: Memory optimization
- SelfEvolutionLoop: Dual-loop controller (legacy, numeric-score driven)
- HumanEvalEvolutionLoop: Human-evaluation-driven optimization (Line 3)

Legacy components (kept for backward compatibility):
- EvaluatorAgent: Old LLM self-evaluation (deprecated, use EvaluationService)
"""

# New: Human evaluation service
from .evaluation_service import (
    EvaluationService,
    HumanEvaluation,
    EvaluationStats,
    get_evaluation_service,
    VALID_LABELS,
)

# Legacy (kept for backward compat, but deprecated)
from .evaluator import EvaluatorAgent, EvaluationReport, ResponseScore, MemoryScore

# Still active
from .analyzer import AnalyzerAgent, AnalysisReport, ProblemType
from .optimizers import PromptOptimizer, MemoryOptimizer, PromptOptimization, MemoryOptimization
from .self_evolution_loop import (
    SelfEvolutionLoop, IterationResult, EvolutionSummary,
    HumanEvalEvolutionLoop, HumanEvalCycleResult, HumanEvalEvolutionSummary,
)
from .demo_service import build_ui_report, load_test_cases, run_demo_evaluation

__all__ = [
    # New evaluation service
    "EvaluationService",
    "HumanEvaluation",
    "EvaluationStats",
    "get_evaluation_service",
    "VALID_LABELS",
    # Legacy evaluator (deprecated)
    "EvaluatorAgent",
    "EvaluationReport",
    "ResponseScore",
    "MemoryScore",
    # Analyzer
    "AnalyzerAgent",
    "AnalysisReport",
    "ProblemType",
    # Optimizers
    "PromptOptimizer",
    "MemoryOptimizer",
    "PromptOptimization",
    "MemoryOptimization",
    # Legacy evolution loop
    "SelfEvolutionLoop",
    "IterationResult",
    "EvolutionSummary",
    # Human-eval-driven evolution loop (Line 3)
    "HumanEvalEvolutionLoop",
    "HumanEvalCycleResult",
    "HumanEvalEvolutionSummary",
    # Demo helpers
    "load_test_cases",
    "run_demo_evaluation",
    "build_ui_report",
]
