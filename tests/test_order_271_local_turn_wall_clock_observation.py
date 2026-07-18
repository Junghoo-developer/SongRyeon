from __future__ import annotations

from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.runtime.user_turn import run_qwen_user_turn


def test_qwen_blocked_response_keeps_local_turn_wall_clock(tmp_path) -> None:
    result = run_qwen_user_turn(
        user_input="외부 업무 폴더를 읽어줘",
        endpoint="https://example.invalid/v1/chat/completions",
        timeout_seconds=1,
        workspace_root=tmp_path,
    )

    assert result["status"] == "blocked"
    timing = result["turn_timing"]
    assert isinstance(timing, dict)
    assert timing["timing_status"] == "recorded"
    assert timing["scope"] == "local_user_turn_entry_to_response"
    assert isinstance(timing["execution_duration_ms"], int)
    assert timing["execution_duration_ms"] >= 0
    assert timing["record_scope"] == "response_runtime_only"
    assert timing["generated_by"] == "CODE:LOCAL_USER_TURN_WALL_CLOCK"
    assert timing["info_class"] == "absolute"
    assert timing["semantic_judgement_status"] == "not_run"


def test_terminal_renders_turn_wall_clock_without_interpreting_difference() -> None:
    rendered = render_runtime_view(
        {
            "status": "ok",
            "runtime": {"model_id": "fake", "transport": "unit"},
            "turn_timing": {
                "timing_status": "recorded",
                "scope": "local_user_turn_entry_to_response",
                "execution_duration_ms": 4321,
                "record_scope": "response_runtime_only",
                "generated_by": "CODE:LOCAL_USER_TURN_WALL_CLOCK",
                "info_class": "absolute",
                "semantic_judgement_status": "not_run",
            },
            "data_records": [],
        },
        user_input="전체 턴 시간 확인",
    )

    assert "전체 턴 시간 [CODE/LOCAL_USER_TURN_WALL_CLOCK]" in rendered
    assert "duration=4321ms" in rendered
    assert "scope=local_user_turn_entry_to_response" in rendered
    assert "record=response_runtime_only" in rendered
