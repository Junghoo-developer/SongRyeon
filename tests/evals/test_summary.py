"""평가 결과가 시스템별 비교 수치로 정확히 집계되는지 검사한다."""

import pytest

from evals import (
    EvaluationCase,
    ExecutionFact,
    RecordedRun,
    compare_systems,
    evaluate_runs,
    summarize_results,
)


def _fact(name, value):
    return ExecutionFact(name=name, value=value)


def _comparison_results():
    first_fact = _fact("tool_call.1.name", "read_python_file")
    second_tool = _fact("tool_call.1.name", "list_python_files")
    second_path = _fact("tool_call.2.path", "runtime/gates.py")
    cases = (
        EvaluationCase(
            case_id="case-1",
            expected_a_facts=(first_fact,),
            supported_code_claims=("supported-1",),
        ),
        EvaluationCase(
            case_id="case-2",
            expected_a_facts=(second_tool, second_path),
            supported_code_claims=("supported-2",),
        ),
    )
    runs = (
        RecordedRun(
            case_id="case-1",
            system_name="songryeon",
            reported_a_facts=(first_fact,),
            code_claims=("supported-1",),
            completed=True,
            tool_call_count=2,
            latency_ms=100,
        ),
        RecordedRun(
            case_id="case-2",
            system_name="songryeon",
            reported_a_facts=(second_tool,),
            code_claims=("supported-2", "invented-claim"),
            completed=False,
            tool_call_count=4,
            latency_ms=300,
        ),
        RecordedRun(
            case_id="case-1",
            system_name="single-agent",
            reported_a_facts=(),
            code_claims=("invented-claim",),
            completed=True,
            tool_call_count=1,
            latency_ms=50,
        ),
    )
    return evaluate_runs(cases, runs)


def test_summary_uses_micro_fact_scores_and_core_cost_metrics():
    results = _comparison_results()
    songryeon_results = tuple(
        result
        for result in results
        if result.system_name == "songryeon"
    )

    summary = summarize_results(songryeon_results)

    assert summary.system_name == "songryeon"
    assert summary.run_count == 2
    assert summary.a_fact_exact_match_rate == 0.5
    assert summary.a_fact_precision == 1.0
    assert summary.a_fact_recall == pytest.approx(2 / 3)
    assert summary.code_claim_count == 3
    assert summary.unsupported_code_claim_count == 1
    assert summary.unsupported_code_claim_rate == pytest.approx(1 / 3)
    assert summary.completion_rate == 0.5
    assert summary.total_tool_call_count == 6
    assert summary.mean_tool_call_count == 3.0
    assert summary.total_latency_ms == 400.0
    assert summary.mean_latency_ms == 200.0
    assert summary.to_dict()["run_count"] == 2


def test_compare_systems_groups_mixed_results_in_stable_name_order():
    comparison = compare_systems(_comparison_results())

    assert list(comparison) == ["single-agent", "songryeon"]
    assert comparison["single-agent"].run_count == 1
    assert comparison["single-agent"].a_fact_exact_match_rate == 0.0
    assert comparison["single-agent"].a_fact_precision == 0.0
    assert comparison["single-agent"].a_fact_recall == 0.0
    assert comparison["single-agent"].unsupported_code_claim_rate == 1.0
    assert comparison["songryeon"].run_count == 2


def test_empty_or_mixed_summary_inputs_are_rejected():
    results = _comparison_results()

    with pytest.raises(ValueError, match="평가 결과가 없습니다"):
        summarize_results(())

    with pytest.raises(ValueError, match="하나의 system_name"):
        summarize_results(results)

    with pytest.raises(TypeError, match="EvaluationResult"):
        compare_systems((object(),))


def test_empty_comparison_has_no_systems():
    assert compare_systems(()) == {}
