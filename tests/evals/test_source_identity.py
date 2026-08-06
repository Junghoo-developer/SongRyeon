"""평가 대상 source 동결 범위의 최소 계약을 검사한다."""

from evals.source_identity import REQUIRED_SUT_FILES


def test_source_identity_includes_transitively_executed_eval_modules():
    """live capture import 경로의 Python 파일도 SUT hash에 포함한다."""

    required = {
        "evals/__init__.py",
        "evals/evaluator.py",
        "evals/live_capture.py",
        "evals/runner.py",
        "evals/schema.py",
        "evals/source_identity.py",
        "evals/summary.py",
        "evals/variants.py",
    }

    assert required <= set(REQUIRED_SUT_FILES)
