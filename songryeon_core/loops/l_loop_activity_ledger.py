from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import raw_capsule_graph_node_id
from songryeon_core.core.schemas import (
    L_LOOP_ACTIVITY_LEDGER_DATA_TYPE,
    LLoopActivityLedgerFrame,
    validate_l_loop_activity_ledger_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop import LLoopResult
from songryeon_core.loops.l_loop_namespace import LRunIds


def record_l_loop_activity_ledger(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    l_result: LLoopResult,
    return_summary_frame_id: str | None = None,
    document_material_packet_frame_id: str | None = None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, LLoopActivityLedgerFrame]:
    """Record one absolute ledger for the DataStore records touched by an L run."""

    return_summary_payload = _payload_for(data_store, return_summary_frame_id)
    document_material_payload = _payload_for(data_store, document_material_packet_frame_id)
    run_index = id_namespace.run_index if id_namespace is not None else _run_index_from_result(
        data_store,
        l_result,
    )
    frame_id = (
        id_namespace.activity_ledger_frame_id()
        if id_namespace is not None
        else "L:activity_ledger_frame"
    )
    output_data_ids = _unique_strings(
        [
            *l_result.output_data_ids,
            return_summary_frame_id,
            document_material_packet_frame_id,
        ]
    )
    source_trace_ids = _unique_strings(
        [
            *l_result.source_trace_ids,
            *_string_list(return_summary_payload.get("source_trace_ids")),
            *_string_list(document_material_payload.get("source_trace_ids")),
        ]
    )
    source_data_ids = _unique_strings(
        [
            *output_data_ids,
            *_string_list(return_summary_payload.get("source_data_ids")),
            *_string_list(document_material_payload.get("source_data_ids")),
        ]
    )
    read_doc_ids = _read_doc_ids(return_summary_payload, document_material_payload)
    search_candidate_doc_ids = _search_candidate_doc_ids(
        return_summary_payload,
        document_material_payload,
    )
    read_code_file_paths = _unique_strings(
        _string_list(return_summary_payload.get("read_code_file_paths"))
    )
    material_items = document_material_payload.get("items")
    document_material_item_count = len(material_items) if isinstance(material_items, list) else 0

    frame = LLoopActivityLedgerFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        run_index=run_index,
        turn_capsule_graph_node_id=raw_capsule_graph_node_id(turn_id),
        run_frame_data_ids=list(l_result.run_data_ids),
        goal_data_ids=list(l_result.goal_data_ids),
        budget_plan_data_ids=list(l_result.budget_plan_data_ids),
        tool_scope_data_ids=list(l_result.tool_scope_data_ids),
        tool_budget_partition_data_ids=list(l_result.tool_budget_partition_data_ids),
        tool_catalog_data_ids=list(l_result.tool_catalog_data_ids),
        tool_choice_data_ids=list(l_result.tool_choice_data_ids),
        query_plan_data_ids=list(l_result.query_plan_data_ids),
        query_data_ids=list(l_result.query_data_ids),
        control_data_ids=list(l_result.control_data_ids),
        tool_result_data_ids=list(l_result.tool_result_data_ids),
        tool_distillation_data_ids=list(l_result.tool_distillation_data_ids),
        tool_budget_data_ids=list(l_result.tool_budget_data_ids),
        continuation_data_ids=list(l_result.continuation_data_ids),
        revision_input_data_ids=list(l_result.revision_input_data_ids),
        revision_query_plan_data_ids=list(l_result.revision_query_plan_data_ids),
        revision_query_data_ids=list(l_result.revision_query_data_ids),
        failure_signal_data_ids=list(l_result.failure_signal_data_ids),
        explicit_artifact_reference_data_ids=list(l_result.explicit_artifact_reference_data_ids),
        document_context_pack_data_ids=list(l_result.document_context_pack_data_ids),
        preserved_data_ids=list(l_result.preserved_data_ids),
        achievement_data_ids=list(l_result.achievement_data_ids),
        return_summary_frame_id=return_summary_frame_id,
        document_material_packet_frame_id=document_material_packet_frame_id,
        output_data_ids=output_data_ids,
        search_candidate_doc_ids=search_candidate_doc_ids,
        read_doc_ids=read_doc_ids,
        read_code_file_paths=read_code_file_paths,
        output_data_id_count=len(output_data_ids),
        tool_result_count=len(l_result.tool_result_data_ids),
        search_candidate_doc_count=len(search_candidate_doc_ids),
        actual_read_doc_count=len(read_doc_ids),
        actual_read_code_file_count=len(read_code_file_paths),
        document_material_item_count=document_material_item_count,
        activity_records=_build_activity_records(
            l_result=l_result,
            return_summary_frame_id=return_summary_frame_id,
            document_material_packet_frame_id=document_material_packet_frame_id,
        ),
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_l_loop_activity_ledger_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type=L_LOOP_ACTIVITY_LEDGER_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def _build_activity_records(
    *,
    l_result: LLoopResult,
    return_summary_frame_id: str | None,
    document_material_packet_frame_id: str | None,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    field_map = {
        "run_frame": l_result.run_data_ids,
        "goal": l_result.goal_data_ids,
        "budget_plan": l_result.budget_plan_data_ids,
        "tool_scope": l_result.tool_scope_data_ids,
        "tool_budget_partition": l_result.tool_budget_partition_data_ids,
        "tool_catalog": l_result.tool_catalog_data_ids,
        "tool_choice": l_result.tool_choice_data_ids,
        "query_plan": l_result.query_plan_data_ids,
        "query": l_result.query_data_ids,
        "control": l_result.control_data_ids,
        "tool_result": l_result.tool_result_data_ids,
        "tool_distillation": l_result.tool_distillation_data_ids,
        "tool_budget": l_result.tool_budget_data_ids,
        "continuation": l_result.continuation_data_ids,
        "revision_input": l_result.revision_input_data_ids,
        "revision_query_plan": l_result.revision_query_plan_data_ids,
        "revision_query": l_result.revision_query_data_ids,
        "failure_signal": l_result.failure_signal_data_ids,
        "explicit_artifact_reference": l_result.explicit_artifact_reference_data_ids,
        "document_context_pack": l_result.document_context_pack_data_ids,
        "l3_preserved": l_result.preserved_data_ids,
        "l3_achievement": l_result.achievement_data_ids,
    }
    for stage, data_ids in field_map.items():
        for data_id in data_ids:
            records.append(
                {
                    "stage": stage,
                    "data_id": data_id,
                    "source_field": f"{stage}_data_ids",
                }
            )
    if return_summary_frame_id:
        records.append(
            {
                "stage": "return_summary",
                "data_id": return_summary_frame_id,
                "source_field": "return_summary_frame_id",
            }
        )
    if document_material_packet_frame_id:
        records.append(
            {
                "stage": "document_material_packet",
                "data_id": document_material_packet_frame_id,
                "source_field": "document_material_packet_frame_id",
            }
        )
    return records


def _payload_for(data_store: DataStore, data_id: str | None) -> dict[str, object]:
    if not data_id:
        return {}
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


def _run_index_from_result(data_store: DataStore, l_result: LLoopResult) -> int:
    for data_id in l_result.run_data_ids:
        payload = _payload_for(data_store, data_id)
        run_index = payload.get("run_index")
        if isinstance(run_index, int) and run_index > 0:
            return run_index
    return 1


def _read_doc_ids(
    return_summary_payload: dict[str, object],
    document_material_payload: dict[str, object],
) -> list[str]:
    read_doc_ids = _unique_strings(_string_list(return_summary_payload.get("read_doc_ids")))
    if read_doc_ids:
        return read_doc_ids
    return _doc_ids_from_material_items(document_material_payload, role="actual_tool_read_doc")


def _search_candidate_doc_ids(
    return_summary_payload: dict[str, object],
    document_material_payload: dict[str, object],
) -> list[str]:
    search_doc_ids = _unique_strings(
        _string_list(return_summary_payload.get("search_result_doc_ids"))
    )
    if search_doc_ids:
        return search_doc_ids
    return _doc_ids_from_material_items(document_material_payload, role="search_candidate")


def _doc_ids_from_material_items(payload: dict[str, object], *, role: str) -> list[str]:
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    doc_ids: list[str] = []
    role_flag = f"was_{role}"
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get(role_flag) is True:
            doc_ids.append(str(item.get("doc_id") or ""))
    return _unique_strings(doc_ids)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


__all__ = ["record_l_loop_activity_ledger"]
