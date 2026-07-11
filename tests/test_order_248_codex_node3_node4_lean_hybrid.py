from __future__ import annotations

from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.runtime.user_turn import run_qwen_codex_hybrid_user_turn


class _QwenAdapter(SongRyeonAllNodesFakeLLMAdapter):
    model_id = "qwen3:14b"


class _CodexAdapter(SongRyeonAllNodesFakeLLMAdapter):
    model_id = "gpt-5.6-sol"
    codex_bin_source = "test"

    def __init__(self) -> None:
        self.request_count = 0

    def complete(self, request):  # type: ignore[no-untyped-def]
        self.request_count += 1
        return super().complete(request)

    def usage_snapshot(self) -> dict[str, object]:
        return {
            "auth_type": "chatgpt",
            "plan_type": "pro",
            "attempted_turn_count": self.request_count,
            "completed_turn_count": self.request_count,
            "accepted_response_count": self.request_count,
            "total_tokens": 100,
            "last_tool_activity_count": 0,
            "last_failure_type": None,
            "last_failure_reason": None,
        }

    def close(self) -> None:
        return None


def test_only_node3_and_node4_use_codex(monkeypatch) -> None:
    qwen = _QwenAdapter()
    codex = _CodexAdapter()
    monkeypatch.setattr(
        "songryeon_core.runtime.user_turn.build_llm_adapter",
        lambda *args, **kwargs: qwen,
    )
    monkeypatch.setattr(
        "songryeon_core.runtime.user_turn.CodexSDKAdapter",
        lambda **kwargs: codex,
    )

    result = run_qwen_codex_hybrid_user_turn(
        user_input="송련 Core가 무엇인지 설명해줘",
        include_data_records=True,
        force_l_route=True,
        max_tool_calls=2,
        max_query_attempts=1,
        max_read_doc_calls=1,
    )

    model_by_node: dict[str, set[str]] = {}
    for record in result["data_records"]:
        if record.get("data_type") != "llm_call":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        model_by_node.setdefault(str(payload.get("node_id")), set()).add(
            str(payload.get("model_id"))
        )

    assert model_by_node["L3"] == {"qwen3:14b"}
    assert model_by_node["node_2"] == {"qwen3:14b"}
    assert model_by_node["node_3"] == {"gpt-5.6-sol"}
    assert model_by_node["node_4"] == {"gpt-5.6-sol"}
    assert codex.request_count == 2
