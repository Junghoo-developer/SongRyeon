"""고정 실행 fixture를 기대값과 비교하는 결정론적 평가기."""

from .schema import (
    EvaluationCase,
    EvaluationResult,
    FactMatchMetrics,
    RecordedRun,
)


def _precision(matched_count, reported_count, expected_count):
    if reported_count:
        return matched_count / reported_count

    return 1.0 if expected_count == 0 else 0.0


def _recall(matched_count, expected_count):
    if expected_count:
        return matched_count / expected_count

    return 1.0


def evaluate_run(case, run):
    """한 실행을 A 사실·코드 주장·완료·비용 지표로 판정한다."""

    if not isinstance(case, EvaluationCase):
        raise TypeError("case는 EvaluationCase여야 합니다.")

    if not isinstance(run, RecordedRun):
        raise TypeError("run은 RecordedRun이어야 합니다.")

    if case.case_id != run.case_id:
        raise ValueError("case와 run의 case_id가 다릅니다.")

    expected = set(case.expected_a_facts)
    reported = set(run.reported_a_facts)
    matched = expected & reported
    missing = tuple(sorted(expected - reported))
    unexpected = tuple(sorted(reported - expected))
    expected_count = len(expected)
    reported_count = len(reported)
    matched_count = len(matched)
    fact_metrics = FactMatchMetrics(
        expected_count=expected_count,
        reported_count=reported_count,
        matched_count=matched_count,
        exact_match=not missing and not unexpected,
        precision=_precision(
            matched_count,
            reported_count,
            expected_count,
        ),
        recall=_recall(matched_count, expected_count),
        missing_facts=missing,
        unexpected_facts=unexpected,
    )
    supported_claims = set(case.supported_code_claims)
    unsupported_claims = tuple(
        sorted(set(run.code_claims) - supported_claims)
    )

    return EvaluationResult(
        case_id=case.case_id,
        system_name=run.system_name,
        a_execution_facts=fact_metrics,
        code_claim_count=len(run.code_claims),
        unsupported_code_claims=unsupported_claims,
        completed=run.completed,
        tool_call_count=run.tool_call_count,
        latency_ms=run.latency_ms,
        extra_metrics=run.extra_metrics,
    )


def evaluate_runs(cases, runs):
    """case_id로 여러 고정 실행을 찾아 입력 순서대로 평가한다."""

    case_by_id = {}

    for case in cases:
        if not isinstance(case, EvaluationCase):
            raise TypeError("cases에는 EvaluationCase만 넣을 수 있습니다.")

        if case.case_id in case_by_id:
            raise ValueError(f"중복 case_id입니다: {case.case_id}")

        case_by_id[case.case_id] = case

    results = []

    for run in runs:
        if not isinstance(run, RecordedRun):
            raise TypeError("runs에는 RecordedRun만 넣을 수 있습니다.")

        try:
            case = case_by_id[run.case_id]
        except KeyError as error:
            raise ValueError(
                f"정의되지 않은 case_id입니다: {run.case_id}"
            ) from error

        results.append(evaluate_run(case, run))

    return tuple(results)
