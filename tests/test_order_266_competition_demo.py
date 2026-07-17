from __future__ import annotations

from songryeon_core.runtime.competition_demo import (
    render_competition_demo,
    run_competition_demo,
)


def test_competition_demo_proves_local_fallback_and_code_guard_boundaries() -> None:
    result = run_competition_demo()
    scenarios = result["scenarios"]

    assert result["status"] == "SONGRYEON_COMPETITION_DEMO_OK"
    assert result["passed"] is True
    assert result["external_api_calls"] == 0
    assert result["neo4j_connections"] == 0

    assert scenarios["local_path"]["passed"] is True
    assert scenarios["local_path"]["final_gate"] == "pass"

    assert scenarios["honest_fallback"]["passed"] is True
    assert scenarios["honest_fallback"]["generated_by"] == "CODE:FALLBACK"
    assert scenarios["honest_fallback"]["semantic_judgement_status"] == "failed"

    guard = scenarios["code_guard"]
    assert guard["passed"] is True
    assert guard["search_candidate_count"] == 5
    assert guard["actual_tool_read_doc_count"] == 2
    assert guard["unread_candidate_count"] == 3
    assert guard["controlled_llm_decision"] == "pass"
    assert guard["final_gate"] == "needs_revision"
    assert guard["public_answer"] == "blocked"
    assert guard["blocking_renderer_marker_present"] is True
    assert "CODE:DOCUMENT_EVIDENCE_ROLE_GUARD" in guard["generated_by"]
    assert guard["contradiction"].startswith(
        "read_doc_claim_without_actual_tool_read_doc:"
    )


def test_competition_demo_renderer_is_short_and_discloses_test_scope() -> None:
    rendered = render_competition_demo(run_competition_demo())

    assert "감사 가능한 로컬 조사 에이전트" in rendered
    assert "후보=5 · 실제 read_doc=2 · 미열람 후보=3" in rendered
    assert "[1/3 LOCAL] PASS" in rendered
    assert "[2/3 HONEST FALLBACK] PASS" in rendered
    assert "[3/3 CODE GUARD] PASS" in rendered
    assert "통제된 모델 판정=pass" in rendered
    assert "사용자 공개=blocked" in rendered
    assert "결정론적 테스트" in rendered
    assert rendered.rstrip().endswith("SONGRYEON_COMPETITION_DEMO_OK")
    assert len(rendered.splitlines()) <= 20
