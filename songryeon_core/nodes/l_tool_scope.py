from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L_REQUIRED_MATERIALS,
    L_TOOL_GROUPS,
    L_TOOL_SCOPE_MODES,
    LToolBudgetPartitionFrame,
    LToolScopeFrame,
    TraceEvent,
    validate_l_tool_budget_partition_frame,
    validate_l_tool_scope_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds


L_TOOL_SCOPE_FRAME_DATA_ID = "L:tool_scope_frame"
L_TOOL_BUDGET_PARTITION_FRAME_DATA_ID = "L:tool_budget_partition_frame"
L_TOOL_SCOPE_PROMPT_REF = "songryeon_core/prompts/l_tool_scope_planner_v0.md"

DOCUMENT_TOOL_NAMES = {"list_docs", "search_docs", "read_doc", "read_artifact"}
CODE_INSPECTION_TOOL_NAMES = {"list_code_files", "search_code", "read_code_file"}
RUNTIME_RECORD_TOOL_NAMES: set[str] = set()


def run_l_tool_scope_planner(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    l1_event: TraceEvent,
    user_query: str,
    goal_data_id: str,
    budget_plan_data_id: str,
    tool_catalog_data_id: str,
    available_tools: list[dict[str, object]],
    adapter: LLMAdapter | None,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, LToolScopeFrame]:
    """L2 전에 이번 L루프의 허용 도구군을 명시 frame으로 기록한다."""

    frame_id = _scope_frame_data_id(id_namespace=id_namespace)
    source_trace_ids = [l1_event.event_id]
    source_data_ids = [goal_data_id, budget_plan_data_id, tool_catalog_data_id]
    llm_call_trace_id: str | None = None
    llm_call_data_id: str | None = None
    failure_type = "adapter_missing"

    if adapter is not None:
        prompt = Path(L_TOOL_SCOPE_PROMPT_REF).read_text(encoding="utf-8")
        llm_result = LLMNodeExecutor(adapter).run(
            node_id="L_tool_scope",
            prompt=prompt,
            input_payload={
                "user_query": user_query,
                "l1_goal": _payload(data_store, goal_data_id),
                "budget_plan": _payload(data_store, budget_plan_data_id),
                "available_tools": available_tools,
                "allowed_tool_scope_modes": sorted(L_TOOL_SCOPE_MODES),
                "allowed_tool_groups": sorted(L_TOOL_GROUPS),
                "allowed_required_materials": sorted(L_REQUIRED_MATERIALS),
            },
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            prompt_ref=L_TOOL_SCOPE_PROMPT_REF,
            input_ref=source_trace_ids,
            source_data_ids=source_data_ids,
            payload_validator=lambda payload: _validate_scope_payload(
                payload=payload,
                turn_id=turn_id,
                frame_id=frame_id,
                source_trace_ids=["validation_trace"],
                source_data_ids=["validation_data"],
            ),
        )
        llm_call_trace_id = llm_result.trace_event_id
        llm_call_data_id = llm_result.call_data_id
        failure_type = llm_result.failure_type
        if llm_result.failure_type == "none" and llm_result.validation.payload is not None:
            frame = _frame_from_payload(
                payload=llm_result.validation.payload,
                turn_id=turn_id,
                frame_id=frame_id,
                source_trace_ids=_unique_strings([*source_trace_ids, llm_call_trace_id]),
                source_data_ids=_unique_strings([*source_data_ids, llm_call_data_id]),
                generated_by=f"LLM:{llm_result.model_id}",
                llm_call_data_id=llm_call_data_id,
            )
            return _record_scope_frame(
                trace_store=trace_store,
                data_store=data_store,
                turn_id=turn_id,
                frame=frame,
            )

    frame = _fallback_scope_frame(
        turn_id=turn_id,
        frame_id=frame_id,
        source_trace_ids=_unique_strings([*source_trace_ids, llm_call_trace_id]),
        source_data_ids=_unique_strings([*source_data_ids, llm_call_data_id]),
        failure_type=failure_type,
        llm_call_data_id=llm_call_data_id,
    )
    return _record_scope_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )


def record_l_tool_budget_partition(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    tool_scope_frame: LToolScopeFrame,
    tool_scope_trace_id: str,
    budget_plan_data_id: str,
    budget_plan_trace_id: str,
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, LToolBudgetPartitionFrame]:
    """승인된 L 예산을 tool scope에 따라 도구군별로 나눠 기록한다."""

    budget_plan = _payload(data_store, budget_plan_data_id)
    frame_id = _budget_partition_frame_data_id(id_namespace=id_namespace)
    frame = _partition_frame(
        turn_id=turn_id,
        frame_id=frame_id,
        tool_scope_frame=tool_scope_frame,
        budget_plan_data_id=budget_plan_data_id,
        budget_plan=budget_plan,
        source_trace_ids=_unique_strings([tool_scope_trace_id, budget_plan_trace_id]),
        source_data_ids=_unique_strings([tool_scope_frame.frame_id, budget_plan_data_id]),
    )
    validate_l_tool_budget_partition_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="CODE:L_TOOL_BUDGET_PARTITION_POLICY",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type="node_output:L_tool_budget_partition_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame_id, frame


def filter_available_tools_for_scope(
    available_tools: list[dict[str, object]],
    tool_scope_frame: LToolScopeFrame,
) -> list[dict[str, object]]:
    """LToolScopeFrame이 허용한 tool group에 속한 도구만 L2에 노출한다."""

    allowed_names = allowed_tool_names_for_groups(tool_scope_frame.allowed_tool_groups)
    return [
        tool
        for tool in available_tools
        if isinstance(tool.get("tool_name") or tool.get("name"), str)
        and str(tool.get("tool_name") or tool.get("name")) in allowed_names
    ]


def allowed_tool_names_for_groups(groups: list[str]) -> set[str]:
    allowed: set[str] = set()
    if "document_tools" in groups:
        allowed.update(DOCUMENT_TOOL_NAMES)
    if "code_inspection_tools" in groups:
        allowed.update(CODE_INSPECTION_TOOL_NAMES)
    if "runtime_record_tools" in groups:
        allowed.update(RUNTIME_RECORD_TOOL_NAMES)
    return allowed


def _scope_frame_data_id(*, id_namespace: LRunIds | None) -> str:
    if id_namespace is None:
        return L_TOOL_SCOPE_FRAME_DATA_ID
    return id_namespace.scoped_data_id(L_TOOL_SCOPE_FRAME_DATA_ID)


def _budget_partition_frame_data_id(*, id_namespace: LRunIds | None) -> str:
    if id_namespace is None:
        return L_TOOL_BUDGET_PARTITION_FRAME_DATA_ID
    return id_namespace.scoped_data_id(L_TOOL_BUDGET_PARTITION_FRAME_DATA_ID)


def _validate_scope_payload(
    *,
    payload: dict[str, object],
    turn_id: str,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> None:
    frame = _frame_from_payload(
        payload=payload,
        turn_id=turn_id,
        frame_id=frame_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by="LLM:validation-model",
        llm_call_data_id=None,
    )
    validate_l_tool_scope_frame(frame)


def _frame_from_payload(
    *,
    payload: dict[str, object],
    turn_id: str,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    generated_by: str,
    llm_call_data_id: str | None,
) -> LToolScopeFrame:
    return LToolScopeFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        tool_scope_mode=str(payload.get("tool_scope_mode") or "").strip(),
        allowed_tool_groups=_string_list(payload.get("allowed_tool_groups")),
        required_materials=_string_list(payload.get("required_materials")),
        scope_reason=str(payload.get("scope_reason") or "").strip(),
        scope_reason_info_class=str(payload.get("scope_reason_info_class") or "mixed").strip(),
        generated_by=generated_by,
        info_class="mixed",
        semantic_judgement_status="ran",
        scope_failure_type="none",
        llm_call_data_id=llm_call_data_id,
        prompt_ref=L_TOOL_SCOPE_PROMPT_REF,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )


def _fallback_scope_frame(
    *,
    turn_id: str,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    failure_type: str,
    llm_call_data_id: str | None,
) -> LToolScopeFrame:
    return LToolScopeFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        tool_scope_mode="document_only",
        allowed_tool_groups=["document_tools"],
        required_materials=["project_document"],
        scope_reason="CODE_STATUS:l_tool_scope_selection_failed_compat_document_only",
        scope_reason_info_class="absolute_status",
        generated_by="CODE:FALLBACK",
        info_class="absolute_status",
        semantic_judgement_status="failed",
        scope_failure_type=failure_type,
        llm_call_data_id=llm_call_data_id,
        prompt_ref=L_TOOL_SCOPE_PROMPT_REF,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )


def _record_scope_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: LToolScopeFrame,
) -> tuple[str, str, LToolScopeFrame]:
    validate_l_tool_scope_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L_tool_scope",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed" if frame.semantic_judgement_status == "ran" else "failed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:L_tool_scope_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def _partition_frame(
    *,
    turn_id: str,
    frame_id: str,
    tool_scope_frame: LToolScopeFrame,
    budget_plan_data_id: str,
    budget_plan: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> LToolBudgetPartitionFrame:
    tool_calls = _int(budget_plan.get("approved_max_tool_calls"))
    query_attempts = _int(budget_plan.get("approved_max_query_attempts"))
    read_calls = _int(budget_plan.get("approved_max_read_doc_calls"))
    mode = tool_scope_frame.tool_scope_mode

    document_tool = document_query = document_read = 0
    code_tool = code_query = code_read = 0
    runtime_budget = 0

    if mode == "document_only":
        document_tool, document_query, document_read = tool_calls, query_attempts, read_calls
    elif mode == "code_only":
        code_tool, code_query, code_read = tool_calls, query_attempts, read_calls
    elif mode in {"document_and_code", "mixed_evidence"}:
        if "document_tools" in tool_scope_frame.allowed_tool_groups and "code_inspection_tools" in tool_scope_frame.allowed_tool_groups:
            document_tool, code_tool = _split_budget(tool_calls)
            document_query, code_query = _split_budget(query_attempts)
            document_read, code_read = _split_budget(read_calls)
        elif "document_tools" in tool_scope_frame.allowed_tool_groups:
            document_tool, document_query, document_read = tool_calls, query_attempts, read_calls
        elif "code_inspection_tools" in tool_scope_frame.allowed_tool_groups:
            code_tool, code_query, code_read = tool_calls, query_attempts, read_calls
        if "runtime_record_tools" in tool_scope_frame.allowed_tool_groups:
            runtime_budget = 1
    elif mode == "runtime_trace_only":
        runtime_budget = 1

    return LToolBudgetPartitionFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        tool_scope_frame_id=tool_scope_frame.frame_id,
        budget_plan_frame_id=budget_plan_data_id,
        tool_scope_mode=mode,
        allowed_tool_groups=list(tool_scope_frame.allowed_tool_groups),
        document_tool_call_budget=document_tool,
        document_query_budget=document_query,
        document_read_budget=document_read,
        code_tool_call_budget=code_tool,
        code_query_budget=code_query,
        code_read_budget=code_read,
        runtime_record_budget=runtime_budget,
        partition_reason=f"CODE_STATUS:partition_from_l_tool_scope_mode:{mode}",
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )


def _split_budget(total: int) -> tuple[int, int]:
    if total <= 0:
        return 0, 0
    if total == 1:
        return 1, 0
    document_budget = max(1, total // 2)
    code_budget = max(1, total - document_budget)
    return document_budget, code_budget


def _payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


def _int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return result


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
