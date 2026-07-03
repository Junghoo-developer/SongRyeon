from __future__ import annotations

import json

from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.r_loop_vessel_one_step import run_r_loop_vessel_one_step

from tests.test_order_176_vessel_r_one_step_traversal import _record_packet


def test_r1_input_payload_supplies_user_question_anchor() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()
    adapter = AnchorCopyAdapter()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_192_anchor_payload",
        user_question="송련 그래프 기억을 한글 질문으로 확인해줘",
        read_packet=packet,
        adapter=adapter,
        frame_label="order_192_anchor_payload",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    anchor = adapter.r1_input_payload["user_question_anchor"]
    assert isinstance(anchor, dict)
    assert anchor["copy_required"] is True
    assert anchor["source_field"] == "user_question"
    assert str(anchor["anchor_id"]).startswith("r1_user_question_anchor:")
    assert result.r1_goal is not None
    assert result.r1_goal.user_question_anchor_id == anchor["anchor_id"]


def test_r1_korean_goal_passes_when_anchor_id_is_copied() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_192_korean_goal",
        user_question="소스 요약과 토큰 묶음 요약의 연결을 한글로 확인해줘",
        read_packet=packet,
        adapter=AnchorCopyAdapter(
            graph_search_goal="한글 목표문으로 그래프 요약 연결을 확인한다.",
        ),
        frame_label="order_192_korean_goal",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "completed"
    assert result.r1_goal is not None
    assert result.r1_goal.graph_search_goal == "한글 목표문으로 그래프 요약 연결을 확인한다."
    assert "source" not in result.r1_goal.graph_search_goal.lower()
    assert "token" not in result.r1_goal.graph_search_goal.lower()


def test_r1_missing_user_question_anchor_id_fails() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_192_missing_anchor",
        user_question="소스 요약과 토큰 묶음 요약의 연결을 확인해줘",
        read_packet=packet,
        adapter=AnchorCopyAdapter(anchor_mode="missing"),
        frame_label="order_192_missing_anchor",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R1"
    assert result.result_frame.failure_type == "schema_failed"
    assert "user_question_anchor_id" in (result.result_frame.failure_reason or "")


def test_r1_wrong_user_question_anchor_id_fails() -> None:
    trace_store, data_store, packet_event_id, packet = _record_packet()

    result = run_r_loop_vessel_one_step(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_192_wrong_anchor",
        user_question="소스 요약과 토큰 묶음 요약의 연결을 확인해줘",
        read_packet=packet,
        adapter=AnchorCopyAdapter(anchor_mode="wrong"),
        frame_label="order_192_wrong_anchor",
        input_ref=[packet_event_id],
    )

    assert result.result_frame.one_step_status == "failed"
    assert result.result_frame.failure_stage == "R1"
    assert result.result_frame.failure_type == "schema_failed"
    assert "user_question_anchor_id" in (result.result_frame.failure_reason or "")


class AnchorCopyAdapter:
    model_id = "order-192-anchor-copy-adapter"

    def __init__(
        self,
        *,
        anchor_mode: str = "copy",
        graph_search_goal: str = "한글 목표문으로 그래프 경로를 확인한다.",
    ) -> None:
        self.anchor_mode = anchor_mode
        self.graph_search_goal = graph_search_goal
        self.r1_input_payload: dict[str, object] = {}

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "R1 Vessel Goal Setter" in request.prompt:
            self.r1_input_payload = request.input_payload
            payload: dict[str, object] = {
                "graph_search_goal": self.graph_search_goal,
                "required_information_granularity": "low_summary",
                "allowed_summary_depth": 1,
                "stop_condition": "Stop after one selected candidate inspection.",
            }
            if self.anchor_mode == "copy":
                payload["user_question_anchor_id"] = request.input_payload[
                    "user_question_anchor"
                ]["anchor_id"]
            elif self.anchor_mode == "wrong":
                payload["user_question_anchor_id"] = "r1_user_question_anchor:wrong"
        elif "R2 Vessel Node Selector" in request.prompt:
            surface_ref, node_ref = _first_ref(request.input_payload)
            payload = {
                "selection_status": "selected" if node_ref else "none_selected",
                "selected_surface_ref": surface_ref if node_ref else None,
                "selected_node_ref": node_ref,
                "selection_reason": "Select the first official candidate for anchor copy test.",
                "expected_information_granularity": "low_summary",
                "expected_source_kind": "summary_or_entry_candidate",
            }
        elif "R3 Vessel Inspector" in request.prompt:
            payload = {
                "current_information_granularity": "low_summary",
                "sufficiency_status": "sufficient",
                "granularity_problem_status": "none",
                "branch_problem_status": "none",
                "recommended_next_action": "stop",
                "inspection_reason": "Anchor copy test supplied enough material.",
            }
        else:
            payload = {"error": "unknown prompt"}
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _first_ref(payload: dict[str, object]) -> tuple[str | None, str | None]:
    surface_refs = payload.get("available_surface_refs")
    records_by_surface = payload.get("candidate_records_by_surface_ref")
    if not isinstance(surface_refs, list) or not isinstance(records_by_surface, dict):
        return None, None
    for surface_ref in surface_refs:
        if not isinstance(surface_ref, str):
            continue
        records = records_by_surface.get(surface_ref)
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("node_ref"), str):
                return surface_ref, record["node_ref"]
    return None, None
