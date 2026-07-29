"""여러 평가 결과를 시스템별 비교 수치로 집계한다."""

from dataclasses import dataclass

from .schema import EvaluationResult


def _ratio(numerator, denominator, *, empty_value):
    if denominator:
        return numerator / denominator

    return empty_value


@dataclass(frozen=True)
class EvaluationSummary:
    """한 시스템의 미시 평균과 실행 비용 요약."""

    system_name: str
    run_count: int
    a_fact_exact_match_rate: float
    a_fact_precision: float
    a_fact_recall: float
    code_claim_count: int
    unsupported_code_claim_count: int
    unsupported_code_claim_rate: float
    completion_rate: float
    total_tool_call_count: int
    mean_tool_call_count: float
    total_latency_ms: float
    mean_latency_ms: float

    def to_dict(self):
        return {
            "system_name": self.system_name,
            "run_count": self.run_count,
            "a_fact_exact_match_rate": self.a_fact_exact_match_rate,
            "a_fact_precision": self.a_fact_precision,
            "a_fact_recall": self.a_fact_recall,
            "code_claim_count": self.code_claim_count,
            "unsupported_code_claim_count": (
                self.unsupported_code_claim_count
            ),
            "unsupported_code_claim_rate": (
                self.unsupported_code_claim_rate
            ),
            "completion_rate": self.completion_rate,
            "total_tool_call_count": self.total_tool_call_count,
            "mean_tool_call_count": self.mean_tool_call_count,
            "total_latency_ms": self.total_latency_ms,
            "mean_latency_ms": self.mean_latency_ms,
        }


def summarize_results(results):
    """같은 system_name을 가진 결과 하나 이상을 미시 평균으로 집계한다."""

    values = tuple(results)

    if not values:
        raise ValueError("요약할 평가 결과가 없습니다.")

    if not all(isinstance(value, EvaluationResult) for value in values):
        raise TypeError("results에는 EvaluationResult만 넣을 수 있습니다.")

    system_names = {value.system_name for value in values}

    if len(system_names) != 1:
        raise ValueError("한 요약에는 하나의 system_name만 사용할 수 있습니다.")

    run_count = len(values)
    expected_count = sum(
        value.a_execution_facts.expected_count
        for value in values
    )
    reported_count = sum(
        value.a_execution_facts.reported_count
        for value in values
    )
    matched_count = sum(
        value.a_execution_facts.matched_count
        for value in values
    )
    exact_matches = sum(
        value.a_execution_facts.exact_match
        for value in values
    )
    code_claim_count = sum(
        value.code_claim_count
        for value in values
    )
    unsupported_count = sum(
        value.unsupported_code_claim_count
        for value in values
    )
    completions = sum(value.completed for value in values)
    tool_calls = sum(value.tool_call_count for value in values)
    total_latency_ms = sum(value.latency_ms for value in values)

    return EvaluationSummary(
        system_name=next(iter(system_names)),
        run_count=run_count,
        a_fact_exact_match_rate=exact_matches / run_count,
        a_fact_precision=_ratio(
            matched_count,
            reported_count,
            empty_value=1.0 if expected_count == 0 else 0.0,
        ),
        a_fact_recall=_ratio(
            matched_count,
            expected_count,
            empty_value=1.0,
        ),
        code_claim_count=code_claim_count,
        unsupported_code_claim_count=unsupported_count,
        unsupported_code_claim_rate=_ratio(
            unsupported_count,
            code_claim_count,
            empty_value=0.0,
        ),
        completion_rate=completions / run_count,
        total_tool_call_count=tool_calls,
        mean_tool_call_count=tool_calls / run_count,
        total_latency_ms=total_latency_ms,
        mean_latency_ms=total_latency_ms / run_count,
    )


def compare_systems(results):
    """섞인 평가 결과를 system_name별 요약 딕셔너리로 반환한다."""

    grouped = {}

    for result in results:
        if not isinstance(result, EvaluationResult):
            raise TypeError("results에는 EvaluationResult만 넣을 수 있습니다.")

        grouped.setdefault(result.system_name, []).append(result)

    return {
        system_name: summarize_results(grouped[system_name])
        for system_name in sorted(grouped)
    }
