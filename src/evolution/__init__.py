"""
Evolution Module - 自进化闭环系统

包含：
- EvaluatorAgent: 质检员，评估回答和记忆质量
- AnalyzerAgent: 分析师，问题归因
- PromptOptimizer: 提示词优化器
- MemoryOptimizer: 记忆优化器
- SelfEvolutionLoop: 双闭环主控制器
"""

from .evaluator import EvaluatorAgent, EvaluationReport, ResponseScore, MemoryScore
from .analyzer import AnalyzerAgent, AnalysisReport, ProblemType
from .optimizers import PromptOptimizer, MemoryOptimizer, PromptOptimization, MemoryOptimization
from .self_evolution_loop import SelfEvolutionLoop, IterationResult, EvolutionSummary
from .demo_service import build_ui_report, load_test_cases, run_demo_evaluation

__all__ = [
    # Evaluator
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
    # Main Loop
    "SelfEvolutionLoop",
    "IterationResult",
    "EvolutionSummary",
    # Demo helpers
    "load_test_cases",
    "run_demo_evaluation",
    "build_ui_report",
]
