"""송련 실행 결과를 고정 fixture로 비교하는 순수 Python 평가 도구."""

from .evaluator import evaluate_run, evaluate_runs
from .schema import (
    EvaluationCase,
    EvaluationResult,
    ExecutionFact,
    FactMatchMetrics,
    RecordedRun,
)
from .summary import (
    EvaluationSummary,
    compare_systems,
    summarize_results,
)

__all__ = [
    "EvaluationCase",
    "EvaluationResult",
    "EvaluationSummary",
    "ExecutionFact",
    "FactMatchMetrics",
    "RecordedRun",
    "compare_systems",
    "evaluate_run",
    "evaluate_runs",
    "summarize_results",
]
