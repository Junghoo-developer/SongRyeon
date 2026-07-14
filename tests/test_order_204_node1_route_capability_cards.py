from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.registry import build_default_schema_registry
from songryeon_core.core.schemas import MemoryPacketFrom0
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.nodes.node_1_router import route_next_with_llm


def test_node1_receives_route_capability_cards_when_vessel_r_is_enabled() -> None:
    adapter = CaptureRoutePayloadAdapter(route="R")

    decision = route_next_with_llm(
        user_input="문서 검색보다 그래프 기억 탐색이 적합한지 판단해줘",
        memory_packet=MemoryPacketFrom0(target="node_1"),
        schema_registry=build_default_schema_registry(),
        adapter=adapter,
        trace_store=TraceStore(),
        data_store=DataStore(),
        turn_id="turn_order_204",
        input_ref=[],
        source_data_ids=[],
        allow_r_route_experimental=True,
        r_execution_mode="vessel_live",
    )

    assert decision.route == "R"
    payload = adapter.last_input_payload
    assert payload is not None
    cards = payload["route_capability_cards"]
    assert isinstance(cards, list)
    by_route = {card["route"]: card for card in cards if isinstance(card, dict)}
    assert set(by_route) == {"L", "2", "R"}
    assert by_route["R"]["r_execution_mode"] == "vessel_live"
    assert by_route["R"]["expected_next_0_mode"] == "vessel_r_read_packet"
    assert by_route["R"]["policy_flag"] == "enable_r_route_experimental"
    assert by_route["R"]["role_label"] == "vessel_graph_memory_traversal_loop"
    assert "Vessel read packet" in by_route["R"]["evidence_surface"]
    assert "read_doc" in by_route["L"]["evidence_surface"]

    selection_policy = payload["route_selection_policy"]
    assert selection_policy["not_a_keyword_rule"] is True
    assert selection_policy["code_semantic_routing_status"] == "not_run"


def test_node1_does_not_receive_r_card_when_vessel_r_is_disabled() -> None:
    adapter = CaptureRoutePayloadAdapter(route="2")

    decision = route_next_with_llm(
        user_input="현재 공급된 근거만으로 바로 답해줘",
        memory_packet=MemoryPacketFrom0(target="node_1"),
        schema_registry=build_default_schema_registry(),
        adapter=adapter,
        trace_store=TraceStore(),
        data_store=DataStore(),
        turn_id="turn_order_204_no_r",
        input_ref=[],
        source_data_ids=[],
        allow_r_route_experimental=False,
    )

    assert decision.route == "2"
    payload = adapter.last_input_payload
    assert payload is not None
    cards = payload["route_capability_cards"]
    by_route = {card["route"]: card for card in cards if isinstance(card, dict)}
    assert set(by_route) == {"L", "2"}
    assert "R" not in payload["allowed_routes"]


def test_node1_prompt_names_l_and_r_evidence_surface_difference() -> None:
    prompt = (
        "songryeon_core/prompts/node_1_router_v0.md"
    )
    text = __import__("pathlib").Path(prompt).read_text(encoding="utf-8")

    assert "route_capability_cards" in text
    assert "r_execution_mode=vessel_live" in text
    assert "Do not choose by keyword alone" in text
    assert "Still choose `L`" in text


class CaptureRoutePayloadAdapter:
    model_id = "capture-route-card-fake"

    def __init__(self, *, route: str) -> None:
        self.route = route
        self.last_input_payload: dict[str, object] | None = None

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.last_input_payload = request.input_payload
        payload = {
            "route": self.route,
            "route_reason": (
                "route_capability_cards를 보고 요청 근거 표면에 맞는 route를 선택했다."
            ),
            "expected_next_0_mode": (
                "r_loop_graph_guide_handoff"
                if self.route == "R"
                else "targeted_memory_supply"
                if self.route == "L"
                else "final_trace_for_2"
            ),
            "route_confidence": 0.8,
            "needs_more_memory": False,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )
