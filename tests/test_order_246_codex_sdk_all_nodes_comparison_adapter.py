from __future__ import annotations

from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.runtime.terminal_view import render_pretty_turn
from songryeon_core.runtime.user_turn import run_codex_sdk_user_turn


class _FakeCodexAllNodesAdapter(SongRyeonAllNodesFakeLLMAdapter):
    model_id = "gpt-5.4"

    def __init__(self) -> None:
        self.closed = False

    def usage_snapshot(self) -> dict[str, object]:
        return {
            "auth_type": "chatgpt",
            "plan_type": "pro",
            "attempted_turn_count": 4,
            "completed_turn_count": 4,
            "accepted_response_count": 4,
            "total_tokens": 4000,
            "last_tool_activity_count": 0,
            "last_failure_type": None,
            "last_failure_reason": None,
        }

    def close(self) -> None:
        self.closed = True


def test_codex_sdk_turn_uses_existing_all_node_path_and_closes(monkeypatch) -> None:
    adapter = _FakeCodexAllNodesAdapter()
    monkeypatch.setattr(
        "songryeon_core.runtime.user_turn.CodexSDKAdapter",
        lambda **kwargs: adapter,
    )

    result = run_codex_sdk_user_turn(
        user_input="송련이 무엇인지 짧게 설명해줘",
        max_tool_calls=2,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    assert result["status"] in {"ok", "needs_revision", "failed"}
    assert result["runtime"]["mode"] == "codex_sdk"
    assert result["runtime"]["api_key_forwarded"] is False
    assert result["runtime"]["api_usage"]["auth_type"] == "chatgpt"
    assert int(result["llm_call_count"] or 0) >= 3
    assert adapter.closed is True


def test_codex_sdk_runtime_usage_is_visible() -> None:
    result = {
        "status": "structure_failed",
        "trace_count": 0,
        "data_record_count": 0,
        "structure_failure_reason": "test failure",
        "runtime": {
            "mode": "codex_sdk",
            "model_id": "gpt-5.4",
            "transport": "codex_sdk_app_server",
            "api_usage": {
                "auth_type": "chatgpt",
                "plan_type": "pro",
                "attempted_turn_count": 1,
                "completed_turn_count": 1,
                "accepted_response_count": 0,
                "total_tokens": 12000,
                "last_tool_activity_count": 0,
                "last_failure_type": "schema_failed",
                "last_failure_reason": "payload mismatch",
            },
        },
    }

    rendered = render_pretty_turn(result, user_input="테스트")

    assert "codex_sdk: auth=chatgpt / plan=pro / turns=1/1/0" in rendered
    assert "tokens=12000" in rendered
    assert "codex_sdk_failure_type: schema_failed" in rendered
