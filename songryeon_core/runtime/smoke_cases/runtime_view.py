from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MetainfoBoundary
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.nodes.node_2_handoff import record_node3_input_brief, record_route2_handoff
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.live_trace import format_live_trace_event


def run_live_trace_progress_stream_smoke() -> dict[str, object]:
    """live trace hook should emit progress lines without report body streaming."""

    lines: list[str] = []

    result = run_dry_turn(
        user_input="live trace progress smoke",
        live_trace_sink=lambda event: lines.append(format_live_trace_event(event)),
    )
    if len(lines) != result["trace_count"]:
        raise AssertionError("live trace line count must match trace_count")
    if not lines:
        raise AssertionError("live trace smoke must collect at least one line")
    first_line = lines[0]
    for token in ("[trace]", "trace_000001", "user", "user_input", "schema=not_checked", "out=[]"):
        if token not in first_line:
            raise AssertionError(f"live trace first line missing token: {token}")
    if not any("node_0 memory_packet" in line for line in lines):
        raise AssertionError("live trace must show node_0 memory_packet progress")
    joined = "\n".join(lines)
    forbidden_report_fragments = [
        "UNSUPPORTED_SECRET_CLAIM_SENTINEL",
        "근거 기준:",
        "FINAL_BLOCKED_BY_GATEKEEPER",
    ]
    for fragment in forbidden_report_fragments:
        if fragment in joined:
            raise AssertionError("live trace must not stream report body fragments")

    return {
        "line_count": len(lines),
        "matches_trace_count": len(lines) == result["trace_count"],
        "no_report_body": True,
    }


def run_runtime_count_consistency_smoke() -> dict[str, int]:
    """빈 extract record와 보고 가능한 문서를 같은 read_doc 숫자로 섞지 않는지 확인한다."""

    trace_store = TraceStore()
    data_store = DataStore()
    turn_id = "turn_runtime_count_consistency"
    seed_event = trace_store.create_event(
        turn_id=turn_id,
        actor="smoke",
        event_type="node_output",
        output_ref=["node2_input:runtime_count_consistency"],
        schema_status="passed",
    )
    data_store.create_record(
        data_id="node2_input:runtime_count_consistency",
        data_type="node_output:node2_input_frame",
        source_trace_id=seed_event.event_id,
        payload={"frame_id": "node2_input:runtime_count_consistency"},
    )
    data_store.create_record(
        data_id="memory_packet:node_2:final_trace_for_2",
        data_type="node_output:memory_packet",
        source_trace_id=seed_event.event_id,
        payload={"packet_id": "memory_packet:node_2:final_trace_for_2"},
    )
    data_store.create_record(
        data_id="turn_outcome:runtime_count_consistency",
        data_type="node_output:turn_outcome",
        source_trace_id=seed_event.event_id,
        payload={"outcome_id": "turn_outcome:runtime_count_consistency"},
    )
    data_store.create_record(
        data_id="route:2",
        data_type="node_output:routing_decision",
        source_trace_id=seed_event.event_id,
        payload={"frame_id": "route:2", "route": "2"},
    )
    for index in range(1, 3):
        text = f"보고 가능한 문서 {index} 본문"
        data_store.create_record(
            data_id=f"tool_result:read_doc:runtime_count:{index:04d}",
            data_type="tool_result:read_doc",
            source_trace_id=seed_event.event_id,
            payload={
                "doc_id": f"doc_{index}.md",
                "char_count": len(text),
                "text": text,
            },
        )
    data_store.create_record(
        data_id="tool_result:read_artifact:runtime_count:empty",
        data_type="tool_result:read_artifact",
        source_trace_id=seed_event.event_id,
        payload={
            "doc_id": "empty_artifact.md",
            "char_count": 0,
            "text": "",
        },
    )

    handoff_trace_id, handoff_id = record_route2_handoff(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question="runtime count consistency smoke",
        node2_input_frame_id="node2_input:runtime_count_consistency",
        node2_input_trace_id=seed_event.event_id,
        final_memory_packet_id="memory_packet:node_2:final_trace_for_2",
        turn_outcome_id="turn_outcome:runtime_count_consistency",
        route_ids=["route:2"],
        l_loop_output_ids=[],
    )
    handoff_payload = data_store.require_record(handoff_id).payload
    if not isinstance(handoff_payload, dict):
        raise AssertionError("runtime count smoke handoff payload must be dict")
    if handoff_payload.get("reportable_document_count") != 2:
        raise AssertionError("handoff must count two reportable document extracts")
    if handoff_payload.get("read_doc_count") != 2:
        raise AssertionError("handoff compatibility read_doc_count must mean reportable documents")
    if handoff_payload.get("raw_document_extract_record_count") != 3:
        raise AssertionError("handoff must keep raw extract record count separate")
    if handoff_payload.get("empty_document_extract_record_count") != 1:
        raise AssertionError("handoff must count empty extract records separately")

    _, _, brief_frame = record_node3_input_brief(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        user_question="runtime count consistency smoke",
        handoff_frame_id=handoff_id,
        boundary=MetainfoBoundary(),
        input_trace_ids=[handoff_trace_id],
        source_data_ids=[handoff_id],
    )
    if len(brief_frame.read_documents) != 2:
        raise AssertionError("node3 brief must expose only the two reportable documents")

    return {
        "reportable_document_count": handoff_payload["reportable_document_count"],
        "raw_document_extract_record_count": handoff_payload["raw_document_extract_record_count"],
        "empty_document_extract_record_count": handoff_payload["empty_document_extract_record_count"],
    }
