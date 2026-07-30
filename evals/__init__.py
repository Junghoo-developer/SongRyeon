"""송련 실행 결과를 고정 fixture로 비교하는 순수 Python 평가 도구."""

from .evaluator import evaluate_run, evaluate_runs
from .schema import (
    EvaluationCase,
    EvaluationResult,
    ExecutionFact,
    FactMatchMetrics,
    RecordedRun,
)
from .runner import (
    BenchmarkManifest,
    RunArtifact,
    RunBundle,
    build_report,
    load_manifest,
    load_run_bundle,
    run_evaluation,
    write_report,
)
from .summary import (
    EvaluationSummary,
    compare_systems,
    summarize_results,
)

__all__ = [
    "BenchmarkManifest",
    "EvaluationCase",
    "EvaluationResult",
    "EvaluationSummary",
    "ExecutionFact",
    "FactMatchMetrics",
    "RecordedRun",
    "RunArtifact",
    "RunBundle",
    "build_report",
    "compare_systems",
    "evaluate_run",
    "evaluate_runs",
    "load_manifest",
    "load_run_bundle",
    "run_evaluation",
    "summarize_results",
    "write_report",
]
