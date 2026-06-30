from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    L2_REVISION_TARGET_TOOL_NAMES,
    L2_TARGET_TOOL_NAMES,
    L2QueryFrame,
    L2QueryPlanCandidate,
    L2QueryPlanFrame,
    TraceEvent,
    validate_l2_query_frame,
    validate_l2_query_plan_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds


L2_QUERY_FRAME_DATA_ID = "L2:query_frame"
L2_QUERY_PLAN_FRAME_DATA_ID = "L2:query_plan_frame"
L2_REVISION_QUERY_PLAN_FRAME_DATA_ID_PREFIX = "L2:revision_query_plan"
L2_REVISION_QUERY_FRAME_DATA_ID_PREFIX = "L2:revision_query_frame"


def l2_revision_query_plan_data_id(
    attempt_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    """L2 revision query plan frame의 DataStore ID를 만든다."""

    legacy_id = f"{L2_REVISION_QUERY_PLAN_FRAME_DATA_ID_PREFIX}:{attempt_index:04d}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def l2_revision_query_frame_data_id(
    attempt_index: int,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    """L2 revision query frame의 DataStore ID를 만든다."""

    legacy_id = f"{L2_REVISION_QUERY_FRAME_DATA_ID_PREFIX}:{attempt_index:04d}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def run_l2_query_setter(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    l1_event: TraceEvent,
    query_text: str,
    query_source: str = "user_input_fallback",
    target_tool_name: str = "search_docs",
    source_data_ids: list[str] | None = None,
    extra_input_trace_ids: list[str] | None = None,
    query_frame_data_id: str = L2_QUERY_FRAME_DATA_ID,
) -> TraceEvent:
    """선택된 검색어 하나를 L2QueryFrame으로 저장한다.

    query_frame_data_id는 L루프 실행 회차별 ID를 주입하기 위한 자리다.
    상위 L 재라우팅을 열면 2회차 L2 query가 기존 `L2:query_frame`을 덮지 않아야 한다.
    """

    input_ref = [l1_event.event_id]
    input_ref.extend(extra_input_trace_ids or [])
    frame = L2QueryFrame(
        frame_id=query_frame_data_id,
        turn_id=turn_id,
        query_text=query_text,
        query_source=query_source,
        query_mode=_query_mode_for_tool(target_tool_name),
        target_tool_name=target_tool_name,
        source_trace_ids=input_ref,
        source_data_ids=source_data_ids or [],
    )
    validate_l2_query_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L2",
        event_type="node_output",
        input_ref=input_ref,
        output_ref=[query_frame_data_id],
        schema_status="passed",
    )
    if data_store is not None:
        data_store.create_record(
            data_id=query_frame_data_id,
            data_type="node_output:L2_query_frame",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
    return event


def run_l2_query_planner(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    l1_event: TraceEvent,
    user_input: str,
    adapter: LLMAdapter,
    source_data_ids: list[str],
    available_tools: list[dict[str, object]] | None = None,
    l_tool_scope: dict[str, object] | None = None,
    budget_partition: dict[str, object] | None = None,
    max_retries: int = 0,
    query_plan_frame_data_id: str = L2_QUERY_PLAN_FRAME_DATA_ID,
) -> TraceEvent:
    """LLM으로 내부 문서 검색 query 후보를 만들고 L2QueryPlanFrame으로 저장한다.

    query_plan_frame_data_id를 외부에서 받는 이유는 query frame과 같다.
    L2 plan도 L루프 재실행마다 별도 record로 남아야 0과 1이 실패/재시도 흐름을 구분할 수 있다.
    """

    source_trace_ids = [l1_event.event_id]
    prompt_ref = "songryeon_core/prompts/l2_query_setter_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    l1_goal = _read_l1_goal_payload(data_store=data_store, source_data_ids=source_data_ids)
    attribution_source_data_ids = _l2_attribution_source_data_ids(source_data_ids)
    supplied_available_tools = available_tools or _default_l2_available_tools()
    allowed_target_tools = _allowed_l2_target_tools_from_available(supplied_available_tools)
    input_payload = {
        "user_input": user_input,
        "l1_goal": l1_goal,
        "l2_planning_contract": _l2_planning_contract(l1_goal),
        "l_tool_scope": l_tool_scope or {},
        "budget_partition": budget_partition or {},
        # LLM에게 모든 내부 record ID를 의미 입력으로 보여주면
        # L:budget_plan_frame 같은 추적용 ID를 "예산 문서"로 오해할 수 있다.
        # 그래서 L2에게는 의미 판단용 목표와 별도로, 후보가 복사할 출처 ID만 공급한다.
        "attribution_source_data_ids": attribution_source_data_ids,
        "available_tools": supplied_available_tools,
    }
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="L2",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=source_trace_ids,
        source_data_ids=source_data_ids,
        max_retries=max_retries,
        payload_validator=lambda payload: _validate_l2_query_plan_payload(
            payload,
            allowed_target_tools=allowed_target_tools,
        ),
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise ValueError(f"L2 query planner failed: {llm_result.failure_type}")

    frame_source_trace_ids = list(source_trace_ids)
    if llm_result.trace_event_id is not None:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = list(source_data_ids)
    if llm_result.call_data_id is not None:
        frame_source_data_ids.append(llm_result.call_data_id)

    frame = _build_query_plan_frame_from_payload(
        payload=llm_result.validation.payload,
        turn_id=turn_id,
        source_trace_ids=frame_source_trace_ids,
        source_data_ids=frame_source_data_ids,
        frame_id=query_plan_frame_data_id,
        allowed_target_tools=allowed_target_tools,
    )
    validate_l2_query_plan_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L2",
        event_type="node_output",
        input_ref=frame_source_trace_ids,
        output_ref=[query_plan_frame_data_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=query_plan_frame_data_id,
        data_type="node_output:L2_query_plan_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event


def run_l2_revision_query_planner(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    revision_input_data_id: str,
    adapter: LLMAdapter,
    available_tools: list[dict[str, object]] | None = None,
    l_tool_scope: dict[str, object] | None = None,
    budget_partition: dict[str, object] | None = None,
    max_retries: int = 0,
    id_namespace: LRunIds | None = None,
) -> TraceEvent:
    """L2RevisionInputFrame을 바탕으로 재검색 query 후보를 만든다.

    이 함수는 도구를 실행하지 않는다. L2가 다시 검색한다면 어떤 query/tool
    후보를 쓸지 LLM에게 계획시키고, 그 결과를 attempt별 query plan frame으로
    보존한다.
    """

    revision_record = data_store.require_record(revision_input_data_id)
    if not isinstance(revision_record.payload, dict):
        raise TypeError("L2 revision input payload must be a dict")
    revision_input = revision_record.payload
    attempt_index = revision_input.get("attempt_index")
    if not isinstance(attempt_index, int):
        raise ValueError("L2 revision input attempt_index must be an integer")

    source_trace_ids = _unique_strings(
        [
            revision_record.source_trace_id,
            *_string_list(revision_input.get("source_trace_ids")),
        ]
    )
    source_data_ids = _unique_strings(
        [
            revision_input_data_id,
            *_string_list(revision_input.get("source_data_ids")),
        ]
    )
    prompt_ref = "songryeon_core/prompts/l2_revision_query_setter_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    supplied_available_tools = available_tools or _default_l2_available_tools(revision=True)
    allowed_target_tools = _allowed_l2_target_tools_from_available(
        supplied_available_tools,
        revision=True,
    )
    input_payload = {
        "planner_mode": "revision_query_plan",
        "revision_input_data_id": revision_input_data_id,
        "revision_input": revision_input,
        "source_data_ids": source_data_ids,
        "l_tool_scope": l_tool_scope or {},
        "budget_partition": budget_partition or {},
        "available_tools": supplied_available_tools,
    }
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="L2",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=source_trace_ids,
        source_data_ids=source_data_ids,
        max_retries=max_retries,
        payload_validator=lambda payload: _validate_l2_revision_query_plan_payload(
            payload,
            revision_input=revision_input,
            allowed_target_tools=allowed_target_tools,
        ),
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise ValueError(f"L2 revision query planner failed: {llm_result.failure_type}")

    frame_source_trace_ids = list(source_trace_ids)
    if llm_result.trace_event_id is not None:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = list(source_data_ids)
    if llm_result.call_data_id is not None:
        frame_source_data_ids.append(llm_result.call_data_id)

    frame_id = l2_revision_query_plan_data_id(
        attempt_index,
        id_namespace=id_namespace,
    )
    frame = _build_query_plan_frame_from_payload(
        payload=llm_result.validation.payload,
        turn_id=turn_id,
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=_unique_strings(frame_source_data_ids),
        frame_id=frame_id,
        default_planner_mode="revision_llm",
        allowed_target_tools=allowed_target_tools,
    )
    _validate_l2_revision_query_plan_against_input(
        frame,
        revision_input=revision_input,
    )
    validate_l2_query_plan_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L2",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type="node_output:L2_revision_query_plan_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event


def run_l2_revision_query_setter(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    revision_query_plan_data_id: str,
    id_namespace: LRunIds | None = None,
) -> TraceEvent:
    """선택된 revision query plan 후보를 attempt별 L2QueryFrame으로 확정한다.

    이 함수는 도구를 실행하지 않는다. L2 revision planner가 만든 후보들 중
    selected_candidate_id가 가리키는 query/tool만 복사해서, 다음 단계의 도구
    실행이 읽을 수 있는 L2QueryFrame record를 만든다.
    """

    plan_record = data_store.require_record(revision_query_plan_data_id)
    if not isinstance(plan_record.payload, dict):
        raise TypeError("L2 revision query plan payload must be a dict")
    plan_payload = plan_record.payload
    attempt_index = _attempt_index_from_revision_plan_id(revision_query_plan_data_id)
    selected_query = selected_query_from_plan(plan_payload)
    selected_tool = selected_target_tool_from_plan(plan_payload)
    planner_mode = str(plan_payload.get("planner_mode") or "")
    query_source = (
        "revision_llm_query_plan"
        if planner_mode == "revision_llm"
        else "revision_fallback_query_plan"
    )
    source_trace_ids = _unique_strings(
        [
            plan_record.source_trace_id,
            *_string_list(plan_payload.get("source_trace_ids")),
        ]
    )
    source_data_ids = _unique_strings(
        [
            revision_query_plan_data_id,
            *_string_list(plan_payload.get("source_data_ids")),
        ]
    )
    frame_id = l2_revision_query_frame_data_id(
        attempt_index,
        id_namespace=id_namespace,
    )
    frame = L2QueryFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        query_text=selected_query,
        query_source=query_source,
        query_mode=_query_mode_for_tool(selected_tool),
        target_tool_name=selected_tool,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_l2_query_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="L2",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame_id,
        data_type="node_output:L2_revision_query_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event


def selected_query_from_plan(payload: object) -> str:
    """L2QueryPlanFrame payload에서 선택된 query_text를 꺼낸다."""

    if not isinstance(payload, dict):
        raise TypeError("L2 query plan payload must be a dict")
    selected_candidate_id = payload.get("selected_candidate_id")
    candidates = payload.get("candidates")
    if not isinstance(selected_candidate_id, str) or not isinstance(candidates, list):
        raise ValueError("L2 query plan payload is incomplete")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("candidate_id") == selected_candidate_id:
            query_text = candidate.get("query_text")
            if isinstance(query_text, str) and query_text.strip():
                return query_text
    raise ValueError("selected L2 query candidate was not found")


def selected_target_tool_from_plan(payload: object) -> str:
    """Return the selected target tool from an L2QueryPlanFrame payload."""

    if not isinstance(payload, dict):
        raise TypeError("L2 query plan payload must be a dict")
    selected_candidate_id = payload.get("selected_candidate_id")
    candidates = payload.get("candidates")
    if not isinstance(selected_candidate_id, str) or not isinstance(candidates, list):
        raise ValueError("L2 query plan payload is incomplete")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("candidate_id") == selected_candidate_id:
            target_tool_name = candidate.get("target_tool_name")
            if isinstance(target_tool_name, str) and target_tool_name.strip():
                return target_tool_name
    raise ValueError("selected L2 query candidate target tool was not found")


def _validate_l2_query_plan_payload(
    payload: dict[str, object],
    *,
    allowed_target_tools: set[str] | None = None,
) -> None:
    """LLM raw payload가 L2QueryPlanFrame으로 바뀔 수 있는지 확인한다."""

    frame = _build_query_plan_frame_from_payload(
        payload=payload,
        turn_id="validation_turn",
        source_trace_ids=["validation_trace"],
        source_data_ids=["validation_data"],
        allowed_target_tools=allowed_target_tools,
    )
    validate_l2_query_plan_frame(frame)


def _validate_l2_revision_query_plan_payload(
    payload: dict[str, object],
    *,
    revision_input: dict[str, object],
    allowed_target_tools: set[str] | None = None,
) -> None:
    """LLM raw payload가 revision query plan frame으로 바뀔 수 있는지 확인한다."""

    frame = _build_query_plan_frame_from_payload(
        payload=payload,
        turn_id="validation_turn",
        source_trace_ids=["validation_trace"],
        source_data_ids=["validation_data"],
        frame_id="L2:revision_query_plan:0001",
        default_planner_mode="revision_llm",
        allowed_target_tools=allowed_target_tools,
    )
    _validate_l2_revision_query_plan_against_input(
        frame,
        revision_input=revision_input,
    )
    validate_l2_query_plan_frame(frame)


def _build_query_plan_frame_from_payload(
    *,
    payload: dict[str, object],
    turn_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    frame_id: str = L2_QUERY_PLAN_FRAME_DATA_ID,
    default_planner_mode: str = "llm",
    allowed_target_tools: set[str] | None = None,
) -> L2QueryPlanFrame:
    candidates_payload = payload.get("candidates")
    if not isinstance(candidates_payload, list):
        raise ValueError("L2 query plan candidates must be a list")

    planner_mode = str(payload.get("planner_mode") or default_planner_mode)
    schema_allowed_target_tools = (
        L2_REVISION_TARGET_TOOL_NAMES
        if planner_mode in {"revision_llm", "revision_fallback"}
        else L2_TARGET_TOOL_NAMES
    )
    if allowed_target_tools is not None:
        effective_allowed_target_tools = set(allowed_target_tools) & set(schema_allowed_target_tools)
    else:
        effective_allowed_target_tools = set(schema_allowed_target_tools)
    candidates: list[L2QueryPlanCandidate] = []
    for raw_candidate in candidates_payload:
        if not isinstance(raw_candidate, dict):
            continue
        target_tool_name = str(raw_candidate.get("target_tool_name") or "search_docs")
        # 일반 L2는 검색/명시 문서 참조만 허용한다.
        # revision L2만 이미 확보된 unread candidate doc_id를 read_doc으로 고를 수 있다.
        if target_tool_name not in effective_allowed_target_tools:
            continue
        raw_source_data_ids = raw_candidate.get("source_data_ids")
        candidate_source_data_ids = (
            [str(item) for item in raw_source_data_ids]
            if isinstance(raw_source_data_ids, list) and raw_source_data_ids
            else list(source_data_ids)
        )
        candidates.append(
            L2QueryPlanCandidate(
                candidate_id=str(raw_candidate.get("candidate_id") or ""),
                query_text=str(raw_candidate.get("query_text") or ""),
                purpose=str(raw_candidate.get("purpose") or ""),
                expected_signal=str(raw_candidate.get("expected_signal") or ""),
                priority=int(raw_candidate.get("priority") or len(candidates) + 1),
                target_tool_name=target_tool_name,
                source_data_ids=candidate_source_data_ids,
            )
        )
    selected_candidate_id = str(payload.get("selected_candidate_id") or "")
    candidate_ids = {candidate.candidate_id for candidate in candidates}
    if selected_candidate_id not in candidate_ids and candidates:
        selected_candidate_id = candidates[0].candidate_id

    return L2QueryPlanFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        planner_mode=planner_mode,
        selected_candidate_id=selected_candidate_id,
        candidates=candidates,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )


def _query_mode_for_tool(target_tool_name: str) -> str:
    if target_tool_name == "read_doc":
        return "direct_doc_read"
    if target_tool_name == "read_artifact":
        return "exact_artifact_ref"
    if target_tool_name == "list_code_files":
        return "code_file_list"
    if target_tool_name == "search_code":
        return "code_search"
    if target_tool_name == "read_code_file":
        return "code_file_read"
    return "embedding_search"


def _allowed_l2_target_tools_from_available(
    available_tools: list[dict[str, object]],
    *,
    revision: bool = False,
) -> set[str]:
    schema_allowed = L2_REVISION_TARGET_TOOL_NAMES if revision else L2_TARGET_TOOL_NAMES
    result: set[str] = set()
    for item in available_tools:
        if not isinstance(item, dict):
            continue
        name = item.get("tool_name") or item.get("name")
        if isinstance(name, str) and name in schema_allowed:
            result.add(name)
    return result


def _default_l2_available_tools(*, revision: bool = False) -> list[dict[str, object]]:
    tools: list[dict[str, object]] = [{"tool_name": "search_docs", "read_only": True}]
    if revision:
        tools.append({"tool_name": "read_doc", "read_only": True})
    return tools


def _validate_l2_revision_query_plan_against_input(
    frame: L2QueryPlanFrame,
    *,
    revision_input: dict[str, object],
) -> None:
    """Revision plan이 L2RevisionInputFrame의 후보/예산 경계를 넘지 않는지 확인한다."""

    unread_doc_ids = _allowed_revision_read_doc_ids(revision_input)
    remaining_query_attempts = _int(revision_input.get("remaining_query_attempts"))
    remaining_read_doc_calls = _int(revision_input.get("remaining_read_doc_calls"))

    if remaining_query_attempts <= 0:
        for candidate in frame.candidates:
            if candidate.target_tool_name != "read_doc":
                raise ValueError(
                    "L2 revision plan must target read_doc when remaining_query_attempts is 0"
                )

    for candidate in frame.candidates:
        if candidate.target_tool_name == "read_doc":
            if remaining_read_doc_calls <= 0:
                raise ValueError("L2 revision read_doc candidate requires remaining read_doc budget")
            if candidate.query_text not in unread_doc_ids:
                raise ValueError("L2 revision read_doc candidate must use an unread candidate doc_id")
        elif candidate.target_tool_name == "search_docs" and remaining_query_attempts <= 0:
            raise ValueError("L2 revision search_docs candidate requires remaining query budget")
        elif candidate.target_tool_name == "read_artifact" and remaining_query_attempts <= 0:
            raise ValueError("L2 revision read_artifact candidate is not allowed after query budget exhaustion")


def _allowed_revision_read_doc_ids(revision_input: dict[str, object]) -> set[str]:
    doc_ids = set(_string_list(revision_input.get("unread_candidate_doc_ids")))
    if doc_ids:
        return doc_ids
    for summary in _string_list(revision_input.get("unread_candidate_summaries")):
        marker = "doc_id="
        if marker not in summary:
            continue
        doc_id = summary.split(marker, 1)[1].split(";", 1)[0].strip()
        if doc_id:
            doc_ids.add(doc_id)
    return doc_ids


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item and item not in result:
            result.append(item)
    return result


def _read_l1_goal_payload(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> dict[str, object]:
    for data_id in source_data_ids:
        record = data_store.get_record(data_id)
        if record is None or record.data_type != "node_output:L1_goal_frame":
            continue
        if isinstance(record.payload, dict):
            return record.payload
    return {}


def _l2_planning_contract(l1_goal: dict[str, object]) -> dict[str, object]:
    evidence_kind = str(l1_goal.get("evidence_requirement_kind") or "unspecified")
    minimum_read_documents = l1_goal.get("minimum_read_documents")
    if not isinstance(minimum_read_documents, int):
        minimum_read_documents = 0
    return {
        "evidence_requirement_kind": evidence_kind,
        "minimum_read_documents": minimum_read_documents,
        "requires_cross_document_analysis": bool(
            l1_goal.get("requires_cross_document_analysis")
        ),
        "randomness_mode": str(l1_goal.get("randomness_mode") or "not_random"),
        "l_loop_success_condition": str(
            l1_goal.get("l_loop_success_condition") or ""
        ),
        "query_scope_rule": (
            "For exploratory_multi_doc or multi_doc_relationship, keep the selected search_docs query broad "
            "enough to gather multiple different internal documents. Do not narrow the query to one incidental "
            "topic unless the user explicitly named that topic."
        ),
    }


def _l2_attribution_source_data_ids(source_data_ids: list[str]) -> list[str]:
    """L2 LLM 후보가 출처 표기로 복사할 수 있는 최소 DataStore ID만 고른다.

    이 함수는 의미 판단을 하지 않는다. 내부 추적 ID 전체를 LLM 입력에 넣으면
    모델이 `L:budget_plan_frame` 같은 시스템 record 이름을 검색 주제로 오해할 수
    있으므로, 후보 생성의 직접 기준인 L1 goal ID를 우선적으로 남긴다.
    """

    # run-scoped ID도 `...:L1:goal_frame`으로 끝난다.
    # exact match만 쓰면 2회차 L1 목표를 L2 attribution 후보에서 놓치게 된다.
    preferred = [data_id for data_id in source_data_ids if data_id.endswith("L1:goal_frame")]
    if preferred:
        return preferred
    return source_data_ids[:1]


def _attempt_index_from_revision_plan_id(data_id: str) -> int:
    marker = f"{L2_REVISION_QUERY_PLAN_FRAME_DATA_ID_PREFIX}:"
    if marker not in data_id:
        raise ValueError(f"not a revision query plan id: {data_id}")
    suffix = data_id.rsplit(marker, 1)[1]
    try:
        attempt_index = int(suffix)
    except ValueError as exc:
        raise ValueError(f"invalid revision query plan attempt suffix: {suffix}") from exc
    if attempt_index < 1:
        raise ValueError("revision query plan attempt index must be positive")
    return attempt_index


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
