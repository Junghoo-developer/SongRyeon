from __future__ import annotations

from songryeon_core.llm.fake import SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.node_4_gatekeeper import (
    _claims_vessel_r_as_document_evidence,
)
from songryeon_core.runtime.user_turn import run_fake_user_turn


def test_release_intro_fake_turn_finishes_with_gatekeeper_pass() -> None:
    result = run_fake_user_turn(user_input="송련이 뭔지 짧게 설명해줘")

    assert result["status"] == "ok"
    assert result["l2_query_source"] is None
    assert result["tool_result_count"] == 0
    assert result["node4_gate_status"] == "pass"
    assert "FINAL_BLOCKED_BY_GATEKEEPER" not in str(result["report"])
    assert "로컬 우선 구조화 에이전트 런타임" in str(result["report"])


def test_release_intro_fake_router_keeps_document_lookup_on_l_route() -> None:
    adapter = SongRyeonAllNodesFakeLLMAdapter()

    response = adapter._node_1_payload(  # noqa: SLF001 - deterministic fake contract test.
        _Request({"user_input": "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘"})
    )

    assert response["route"] == "L"


def test_vessel_r_document_boundary_negation_is_not_blocked() -> None:
    rendered = (
        "이번 답변은 Vessel R graph-memory 재료를 사용했어. "
        "이 재료는 read_doc evidence가 아니고 read_code_file evidence도 아니야."
    )

    assert not _claims_vessel_r_as_document_evidence(rendered)


class _Request:
    prompt = "node_1 Router"

    def __init__(self, input_payload: dict[str, object]) -> None:
        self.input_payload = input_payload
