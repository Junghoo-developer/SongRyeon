from __future__ import annotations

from pathlib import Path

from songryeon_core.llm.codex_sdk_adapter import resolve_codex_bin
from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.runtime.terminal_view import render_pretty_turn
from songryeon_core.runtime.user_turn import run_qwen_codex_hybrid_user_turn


class _TrackingQwenAdapter(SongRyeonAllNodesFakeLLMAdapter):
    model_id = "qwen3:14b"

    def __init__(self) -> None:
        self.request_count = 0

    def complete(self, request):  # type: ignore[no-untyped-def]
        self.request_count += 1
        return super().complete(request)


class _TrackingCodexAdapter(SongRyeonAllNodesFakeLLMAdapter):
    model_id = "gpt-5.6-sol"
    codex_bin_source = "workspace_cache"

    def __init__(self) -> None:
        self.request_count = 0
        self.closed = False

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
            "total_tokens": 12345,
            "last_tool_activity_count": 0,
            "last_failure_type": None,
            "last_failure_reason": None,
            "codex_bin_configured": True,
            "codex_bin_source": self.codex_bin_source,
        }

    def close(self) -> None:
        self.closed = True


def test_hybrid_turn_assigns_worker_and_final_nodes(monkeypatch) -> None:
    qwen = _TrackingQwenAdapter()
    codex = _TrackingCodexAdapter()
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

    assert result["status"] in {"ok", "needs_revision", "failed"}
    runtime = result["runtime"]
    assert runtime["mode"] == "qwen_codex_hybrid"
    assert runtime["worker_model_id"] == "qwen3:14b"
    assert runtime["judgement_model_id"] == "gpt-5.6-sol"
    assert runtime["final_report_gate_model_id"] == "gpt-5.6-sol"
    assert runtime["node_allocation_policy"] == "qwen_worker_codex_node3_node4_v1"
    assert "L2_query_planner" in runtime["qwen_nodes"]
    assert "L3_result_keeper" in runtime["qwen_nodes"]
    assert "node_2_metainfo_boundary" in runtime["qwen_nodes"]
    assert runtime["codex_nodes"] == ["node_3_reporter", "node_4_gatekeeper"]
    assert qwen.request_count > 0
    assert codex.request_count == 2
    assert codex.closed is True
    rendered = render_pretty_turn(result, user_input="테스트")
    assert "L2 계획 [LLM:qwen3:14b" in rendered
    assert "L2 계획 [LLM:qwen3:14b+gpt-5.6-sol" not in rendered


def test_hybrid_runtime_displays_models_and_codex_usage() -> None:
    result = {
        "status": "structure_failed",
        "trace_count": 0,
        "data_record_count": 0,
        "structure_failure_reason": "test failure",
        "runtime": {
            "mode": "qwen_codex_hybrid",
            "worker_model_id": "qwen3:14b",
            "judgement_model_id": "gpt-5.6-sol",
            "final_report_gate_model_id": "gpt-5.6-sol",
            "node_allocation_policy": "qwen_worker_codex_node3_node4_v1",
            "codex_nodes": ["node_3_reporter", "node_4_gatekeeper"],
            "api_usage": {
                "auth_type": "chatgpt",
                "plan_type": "pro",
                "attempted_turn_count": 2,
                "completed_turn_count": 2,
                "accepted_response_count": 2,
                "total_tokens": 12345,
                "last_tool_activity_count": 0,
                "last_failure_type": None,
                "last_failure_reason": None,
            },
        },
    }

    rendered = render_pretty_turn(result, user_input="테스트")

    assert "hybrid_models: worker=qwen3:14b / final_report_gate=gpt-5.6-sol" in rendered
    assert "hybrid_codex_nodes: node_3_reporter, node_4_gatekeeper" in rendered
    assert "codex_sdk: auth=chatgpt / plan=pro / turns=2/2/2" in rendered
    assert "tokens=12345" in rendered


def test_explicit_codex_bin_is_preserved(tmp_path: Path) -> None:
    executable = tmp_path / "codex.exe"
    executable.write_bytes(b"test")

    resolved, source = resolve_codex_bin(str(executable))

    assert resolved == str(executable.resolve())
    assert source == "explicit"
