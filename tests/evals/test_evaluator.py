"""고정 fixture 평가가 모델 없이 결정론적으로 동작하는지 검사한다."""

import json

import pytest

from evals import (
    EvaluationCase,
    ExecutionFact,
    RecordedRun,
    evaluate_run,
    evaluate_runs,
)


def _fact(name, value):
    return ExecutionFact(name=name, value=value)


def test_exact_fixture_run_scores_all_core_metrics_without_a_model():
    tool_fact = _fact("tool_call.1.name", "read_python_file")
    path_fact = _fact("tool_call.1.path", "nodes/review.py")
    case = EvaluationCase(
        case_id="read-review",
        expected_a_facts=(tool_fact, path_fact),
        supported_code_claims=(
            "ReviewDecision.verdict supports permit and reject",
        ),
        tags=("execution_fact", "code_claim"),
    )
    run = RecordedRun(
        case_id="read-review",
        system_name="songryeon",
        # 순서가 달라도 같은 사실 집합으로 판정한다.
        reported_a_facts=(path_fact, tool_fact),
        code_claims=(
            "ReviewDecision.verdict supports permit and reject",
        ),
        completed=True,
        tool_call_count=2,
        latency_ms=125.5,
        extra_metrics={"node4_rejections": 0, "profile": "fixture"},
    )

    result = evaluate_run(case, run)

    assert result.a_execution_facts.exact_match is True
    assert result.a_execution_facts.expected_count == 2
    assert result.a_execution_facts.reported_count == 2
    assert result.a_execution_facts.matched_count == 2
    assert result.a_execution_facts.precision == 1.0
    assert result.a_execution_facts.recall == 1.0
    assert result.a_execution_facts.missing_facts == ()
    assert result.a_execution_facts.unexpected_facts == ()
    assert result.unsupported_code_claim_count == 0
    assert result.completed is True
    assert result.tool_call_count == 2
    assert result.latency_ms == 125.5
    assert result.extra_metrics["profile"] == "fixture"

    # 결과 스키마는 별도 변환기 없이 JSON에 저장할 수 있다.
    serialized = json.dumps(
        result.to_dict(),
        allow_nan=False,
        ensure_ascii=False,
    )
    assert '"exact_match": true' in serialized
    assert '"unsupported_count": 0' in serialized


def test_partial_facts_and_unsupported_claims_keep_diagnostics():
    expected_tool = _fact("tool_call.1.name", "read_python_file")
    expected_path = _fact("tool_call.1.path", "runtime/gates.py")
    wrong_path = _fact("tool_call.1.path", "runtime/runner.py")
    case = EvaluationCase(
        case_id="wrong-path",
        expected_a_facts=(expected_tool, expected_path),
        supported_code_claims=("gate has a rejection limit",),
    )
    run = RecordedRun(
        case_id="wrong-path",
        system_name="single-agent",
        reported_a_facts=(expected_tool, wrong_path),
        code_claims=(
            "gate has a rejection limit",
            "missing_function exists",
        ),
        completed=False,
        tool_call_count=3,
        latency_ms=800,
    )

    result = evaluate_run(case, run)

    assert result.a_execution_facts.exact_match is False
    assert result.a_execution_facts.matched_count == 1
    assert result.a_execution_facts.precision == 0.5
    assert result.a_execution_facts.recall == 0.5
    assert result.a_execution_facts.missing_facts == (expected_path,)
    assert result.a_execution_facts.unexpected_facts == (wrong_path,)
    assert result.code_claim_count == 2
    assert result.unsupported_code_claims == ("missing_function exists",)
    assert result.completed is False


def test_empty_expected_facts_penalize_an_unexpected_report():
    invented = _fact("tool_call.1.name", "read_python_file")
    case = EvaluationCase(case_id="no-tool-expected")
    run = RecordedRun(
        case_id="no-tool-expected",
        system_name="single-agent",
        reported_a_facts=(invented,),
        completed=True,
    )

    result = evaluate_run(case, run)

    assert result.a_execution_facts.exact_match is False
    assert result.a_execution_facts.precision == 0.0
    assert result.a_execution_facts.recall == 1.0
    assert result.a_execution_facts.unexpected_facts == (invented,)


def test_evaluate_runs_matches_cases_by_id_and_keeps_run_order():
    cases = (
        EvaluationCase(case_id="first"),
        EvaluationCase(case_id="second"),
    )
    runs = (
        RecordedRun(
            case_id="second",
            system_name="songryeon",
            completed=True,
        ),
        RecordedRun(
            case_id="first",
            system_name="songryeon",
            completed=True,
        ),
    )

    results = evaluate_runs(cases, runs)

    assert [result.case_id for result in results] == [
        "second",
        "first",
    ]

    with pytest.raises(ValueError, match="정의되지 않은 case_id"):
        evaluate_runs(
            cases,
            (
                RecordedRun(
                    case_id="unknown",
                    system_name="songryeon",
                ),
            ),
        )

    with pytest.raises(ValueError, match="중복 case_id"):
        evaluate_runs(
            (
                EvaluationCase(case_id="same"),
                EvaluationCase(case_id="same"),
            ),
            (),
        )


def test_fixture_schema_rejects_ambiguous_or_invalid_metric_values():
    fact = _fact("tool_call.1.name", "read_python_file")

    with pytest.raises(ValueError, match="중복 사실"):
        EvaluationCase(
            case_id="duplicate-fact",
            expected_a_facts=(fact, fact),
        )

    with pytest.raises(ValueError, match="중복 값"):
        RecordedRun(
            case_id="duplicate-claim",
            system_name="songryeon",
            code_claims=("same", "same"),
        )

    with pytest.raises(ValueError, match="tool_call_count"):
        RecordedRun(
            case_id="negative-tool-count",
            system_name="songryeon",
            tool_call_count=-1,
        )

    with pytest.raises(ValueError, match="latency_ms"):
        RecordedRun(
            case_id="nan-latency",
            system_name="songryeon",
            latency_ms=float("nan"),
        )

    with pytest.raises(TypeError, match="extra_metrics 값"):
        RecordedRun(
            case_id="invalid-extra",
            system_name="songryeon",
            extra_metrics={"details": {"nested": "not allowed"}},
        )


def test_extra_metrics_are_copied_before_the_run_is_frozen():
    source = {"token_count": 12}
    run = RecordedRun(
        case_id="frozen-extra",
        system_name="songryeon",
        extra_metrics=source,
    )

    source["token_count"] = 999

    assert run.extra_metrics["token_count"] == 12

    with pytest.raises(TypeError):
        run.extra_metrics["token_count"] = 13


def test_case_and_run_ids_must_match():
    case = EvaluationCase(case_id="expected")
    run = RecordedRun(
        case_id="other",
        system_name="songryeon",
    )

    with pytest.raises(ValueError, match="case_id가 다릅니다"):
        evaluate_run(case, run)
