from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import L3PreservedInfoFrame
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.loops.l_loop_continuation import (
    record_l_loop_continuation_decision,
)
from songryeon_core.nodes.l1_goal_setter import _validate_l1_goal_payload
from songryeon_core.nodes.l3_result_keeper import (
    _build_goal_match_context,
    l3_revision_achievement_frame_data_id,
    run_l3_revision_result_keeper,
)
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.tools.document_context_pack import (
    build_explicit_artifact_reference_frame,
)


class _SemanticMatchAdapter:
    model_id = "order-279-semantic-match-adapter"

    def complete(self, request: LLMRequest) -> LLMResponse:
        previews = request.input_payload.get("read_document_previews")
        first_preview = previews[0] if isinstance(previews, list) and previews else {}
        excerpts = (
            first_preview.get("evidence_excerpt_candidates")
            if isinstance(first_preview, dict)
            else []
        )
        first_excerpt = excerpts[0] if isinstance(excerpts, list) and excerpts else {}
        payload = {
            "semantic_goal_match_status": "matched",
            "semantic_goal_match_reason": "허용된 fallback 원문이 현재 요청을 직접 지원한다.",
            "semantic_evidence_bindings": [
                {
                    "material_ref": first_preview.get("material_ref"),
                    "evidence_excerpt_ref": first_excerpt.get("evidence_excerpt_ref"),
                }
            ],
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def test_l1_rejects_artifact_reference_index_outside_supplied_list() -> None:
    payload = _l1_payload(
        mode="exact_one",
        occurrence_indices=[2],
    )

    with pytest.raises(ValueError, match="must be in supplied references"):
        _validate_l1_goal_payload(
            payload,
            explicit_artifact_reference_count=1,
        )


def test_ordered_fallback_matches_second_reference_after_first_not_found(
    tmp_path: Path,
) -> None:
    frame, second_doc_id = _fallback_resolver_frame(tmp_path)
    data_store = _goal_match_store(frame=frame, read_doc_ids=[second_doc_id])

    result = _build_goal_match_context(
        user_query="ORDER_900_DOES_NOT_EXIST.md가 없으면 ORDER_901을 읽어줘",
        preserved_frame=L3PreservedInfoFrame(
            frame_id="L3:preserved",
            turn_id="turn_order_279",
        ),
        data_store=data_store,
        allowed_source_data_ids={frame.frame_id, "tool_result:read_doc:0001"},
        l1_goal=_l1_goal(
            mode="ordered_fallback",
            occurrence_indices=[1, 2],
        ),
    )

    assert result["artifact_requirement_status"] == "matched"
    assert result["goal_match_status"] == "matched"
    assert result["artifact_requirement_target_doc_ids"] == [second_doc_id]
    assert result["artifact_requirement_matched_doc_ids"] == [second_doc_id]


def test_ordered_fallback_does_not_skip_existing_primary(tmp_path: Path) -> None:
    frame, first_doc_id, second_doc_id = _two_existing_resolver_frame(tmp_path)
    data_store = _goal_match_store(frame=frame, read_doc_ids=[second_doc_id])

    result = _build_goal_match_context(
        user_query="ORDER_901이 없으면 ORDER_902를 읽어줘",
        preserved_frame=L3PreservedInfoFrame(
            frame_id="L3:preserved",
            turn_id="turn_order_279",
        ),
        data_store=data_store,
        allowed_source_data_ids={frame.frame_id, "tool_result:read_doc:0001"},
        l1_goal=_l1_goal(
            mode="ordered_fallback",
            occurrence_indices=[1, 2],
        ),
    )

    assert result["artifact_requirement_status"] == "partial"
    assert result["artifact_requirement_target_doc_ids"] == [first_doc_id]
    assert result["artifact_requirement_matched_doc_ids"] == []


def test_all_of_requires_every_selected_artifact(tmp_path: Path) -> None:
    frame, first_doc_id, second_doc_id = _two_existing_resolver_frame(tmp_path)
    data_store = _goal_match_store(frame=frame, read_doc_ids=[first_doc_id])

    result = _build_goal_match_context(
        user_query="ORDER_901과 ORDER_902를 모두 읽어줘",
        preserved_frame=L3PreservedInfoFrame(
            frame_id="L3:preserved",
            turn_id="turn_order_279",
        ),
        data_store=data_store,
        allowed_source_data_ids={frame.frame_id, "tool_result:read_doc:0001"},
        l1_goal=_l1_goal(mode="all_of", occurrence_indices=[1, 2]),
    )

    assert result["artifact_requirement_status"] == "partial"
    assert result["artifact_requirement_target_doc_ids"] == [
        first_doc_id,
        second_doc_id,
    ]
    assert result["artifact_requirement_matched_doc_ids"] == [first_doc_id]


def test_any_of_accepts_one_selected_artifact(tmp_path: Path) -> None:
    frame, first_doc_id, second_doc_id = _two_existing_resolver_frame(tmp_path)
    data_store = _goal_match_store(frame=frame, read_doc_ids=[second_doc_id])

    result = _build_goal_match_context(
        user_query="ORDER_901이나 ORDER_902 중 하나를 읽어줘",
        preserved_frame=L3PreservedInfoFrame(
            frame_id="L3:preserved",
            turn_id="turn_order_279",
        ),
        data_store=data_store,
        allowed_source_data_ids={frame.frame_id, "tool_result:read_doc:0001"},
        l1_goal=_l1_goal(mode="any_of", occurrence_indices=[1, 2]),
    )

    assert result["artifact_requirement_status"] == "matched"
    assert result["artifact_requirement_matched_doc_ids"] == [second_doc_id]
    assert first_doc_id in result["artifact_requirement_target_doc_ids"]


def test_revision_fallback_contract_promotes_and_stops_achieved(
    tmp_path: Path,
) -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    source_event = trace_store.create_event(
        turn_id="turn_order_279",
        actor="test",
        event_type="node_output",
        output_ref=["source:test"],
        schema_status="passed",
    )
    frame, second_doc_id = _fallback_resolver_frame(tmp_path)
    data_store.create_record(
        data_id="L1:goal_frame",
        data_type="node_output:L1_goal_frame",
        source_trace_id=source_event.event_id,
        payload={
            **_l1_goal(mode="ordered_fallback", occurrence_indices=[1, 2]),
            "macro_goal": "첫 문서가 없으면 대체 ORDER 원문을 읽는다.",
            "micro_goal": "허용된 대체 문서를 읽는다.",
            "minimum_read_documents": 1,
        },
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:explicit_artifact_reference_frame",
        source_trace_id=source_event.event_id,
        payload=asdict(frame),
    )
    data_store.create_record(
        data_id="L2:revision_query_frame:0001",
        data_type="node_output:L2_revision_query_frame",
        source_trace_id=source_event.event_id,
        payload={"query_text": second_doc_id},
    )
    data_store.create_record(
        data_id="tool_result:read_doc:0001",
        data_type="tool_result:read_doc",
        source_trace_id=source_event.event_id,
        payload={
            "doc_id": second_doc_id,
            "text": "ORDER 279 대체 문서 원문은 조건부 성공 계약을 설명한다.",
            "char_count": 34,
        },
    )

    run_l3_revision_result_keeper(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_279",
        attempt_index=1,
        revision_query_frame_data_id="L2:revision_query_frame:0001",
        revision_tool_source_trace_ids=[source_event.event_id],
        revision_tool_source_data_ids=[
            frame.frame_id,
            "tool_result:read_doc:0001",
        ],
        user_query="ORDER_900_DOES_NOT_EXIST.md가 없으면 ORDER_901을 읽어줘",
        adapter=_SemanticMatchAdapter(),
    )

    achievement_id = l3_revision_achievement_frame_data_id(1)
    achievement = data_store.require_record(achievement_id).payload
    assert isinstance(achievement, dict)
    assert achievement["artifact_requirement_mode"] == "ordered_fallback"
    assert achievement["artifact_requirement_status"] == "matched"
    assert achievement["achievement_status"] == "achieved"
    assert frame.frame_id in achievement["source_data_ids"]

    _, _, continuation = record_l_loop_continuation_decision(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_279",
        attempt_index=1,
        max_attempts=4,
        l3_achievement_data_id=achievement_id,
        l2_query_frame_data_id="L2:revision_query_frame:0001",
    )
    assert continuation.continuation_status == "stop_achieved"


def test_runtime_view_displays_artifact_requirement_contract() -> None:
    output = render_runtime_view(
        {
            "status": "ok",
            "trace_count": 2,
            "data_record_count": 2,
            "data_records": [
                {
                    "data_id": "L1:goal_frame",
                    "data_type": "node_output:L1_goal_frame",
                    "payload": {
                        "macro_goal": "대체 문서 원문을 확보한다.",
                        "micro_goal": "허용된 대체 문서를 읽는다.",
                        "goal_generation_source": "LLM:test",
                        "llm_goal_judgement_status": "ran",
                        "artifact_requirement_mode": "ordered_fallback",
                        "explicit_artifact_reference_count": 2,
                        "artifact_reference_occurrence_indices": [1, 2],
                        "artifact_requirement_reason": "첫 문서가 없으면 둘째 문서를 사용한다.",
                    },
                },
                {
                    "data_id": "L3:achievement_frame",
                    "data_type": "node_output:L3_achievement_frame",
                    "payload": {
                        "achievement_status": "achieved",
                        "controller_decision": "stop_success",
                        "goal_match_status": "matched",
                        "artifact_requirement_mode": "ordered_fallback",
                        "artifact_requirement_status": "matched",
                        "artifact_requirement_target_doc_ids": ["docs/SECOND.md"],
                        "artifact_requirement_matched_doc_ids": ["docs/SECOND.md"],
                    },
                },
            ],
        },
        user_input="첫 문서가 없으면 둘째 문서를 읽어줘",
    )

    assert "mode=ordered_fallback" in output
    assert "reference_count=2" in output
    assert "status=matched" in output
    assert "docs/SECOND.md" in output


def _fallback_resolver_frame(tmp_path: Path):
    second_path = _write_order(tmp_path, 901, "B")
    frame = build_explicit_artifact_reference_frame(
        turn_id="turn_order_279",
        user_text="ORDER_900_DOES_NOT_EXIST.md가 없으면 ORDER_901을 읽어줘",
        document_root=tmp_path,
        frame_id="L:explicit_artifact_reference_frame",
        source_trace_ids=["trace:user"],
        source_data_ids=["L1:goal_frame"],
    )
    second_doc_id = str(frame.resolved_references[1].selected_doc_id)
    assert second_path.name in second_doc_id
    return frame, second_doc_id


def _two_existing_resolver_frame(tmp_path: Path):
    _write_order(tmp_path, 901, "A")
    _write_order(tmp_path, 902, "B")
    frame = build_explicit_artifact_reference_frame(
        turn_id="turn_order_279",
        user_text="ORDER_901과 ORDER_902를 읽어줘",
        document_root=tmp_path,
        frame_id="L:explicit_artifact_reference_frame",
        source_trace_ids=["trace:user"],
        source_data_ids=["L1:goal_frame"],
    )
    return (
        frame,
        str(frame.resolved_references[0].selected_doc_id),
        str(frame.resolved_references[1].selected_doc_id),
    )


def _write_order(tmp_path: Path, number: int, suffix: str) -> Path:
    order_dir = tmp_path / "Administrative_Reform_1" / "04_Orders"
    order_dir.mkdir(parents=True, exist_ok=True)
    path = order_dir / f"ORDER_{number:03d}_{suffix}_V0.md"
    path.write_text(f"# ORDER {number:03d}\n\n테스트 원문 {suffix}", encoding="utf-8")
    return path


def _goal_match_store(*, frame, read_doc_ids: list[str]) -> DataStore:
    data_store = DataStore()
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:explicit_artifact_reference_frame",
        payload=asdict(frame),
    )
    for index, doc_id in enumerate(read_doc_ids, start=1):
        data_store.create_record(
            data_id=f"tool_result:read_doc:{index:04d}",
            data_type="tool_result:read_doc",
            payload={"doc_id": doc_id, "text": f"{doc_id} 원문"},
        )
    return data_store


def _l1_goal(*, mode: str, occurrence_indices: list[int]) -> dict[str, object]:
    return {
        "artifact_requirement_mode": mode,
        "artifact_reference_occurrence_indices": occurrence_indices,
        "artifact_requirement_reason": "테스트가 지정한 명시 요구 관계",
    }


def _l1_payload(*, mode: str, occurrence_indices: list[int]) -> dict[str, object]:
    return {
        "macro_goal": "명시 문서 원문을 확보한다.",
        "macro_goal_reason": "사용자가 명시 문서를 요구했다.",
        "micro_goal": "선택된 문서를 읽는다.",
        "micro_goal_reason": "원문 확보가 필요하다.",
        "evidence_requirement_kind": "exact_artifact_lookup",
        "minimum_read_documents": 1,
        "requires_cross_document_analysis": False,
        "randomness_mode": "not_random",
        "l_loop_success_condition": "허용된 원문을 읽는다.",
        "temporal_requirement_status": "not_required",
        "temporal_evidence_goal": "시간 근거는 별도 성공 조건이 아니다.",
        "temporal_requirement_reason": "현재 테스트 요청은 명시 문서 원문 확보를 요구한다.",
        "artifact_requirement_mode": mode,
        "artifact_reference_occurrence_indices": occurrence_indices,
        "artifact_requirement_reason": "사용자의 명시 요구 관계",
        "requested_search_top_k": 3,
        "requested_max_tool_calls": 3,
        "requested_max_read_doc_calls": 1,
        "requested_max_query_attempts": 1,
        "budget_request_reason": "명시 문서 확인 예산",
    }
