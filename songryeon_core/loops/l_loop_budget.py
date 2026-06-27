from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    LLoopBudgetPlanFrame,
    validate_l_loop_budget_plan_frame,
)
from songryeon_core.core.trace_store import TraceEvent, TraceStore


L_LOOP_BUDGET_PLAN_FRAME_DATA_ID = "L:budget_plan_frame"

# 문서 추적 테스트용 하드 정책 한도다.
# L1은 이 값보다 큰 예산을 요청할 수 있지만, CODE:BUDGET_POLICY는 여기서 잘라낸다.
SEARCH_TOP_K_CEILING = 12
MAX_TOOL_CALLS_CEILING = 18
MAX_READ_DOC_CALLS_CEILING = 10
MAX_QUERY_ATTEMPTS_CEILING = 8

# search_docs 뒤에 read_doc을 여러 번 태우려면 도구 호출 수가 같이 늘어야 한다.
# 예: read_doc 2개 승인 => search_docs 1회 + read_doc 2회 = tool_calls 최소 3회.
SEARCH_TOOL_CALL_OVERHEAD = 1


def record_l_loop_budget_plan(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    l1_event: TraceEvent,
    goal_data_id: str,
    base_search_top_k: int,
    base_max_tool_calls: int,
    base_max_read_doc_calls: int,
    base_max_query_attempts: int,
    budget_plan_data_id: str = L_LOOP_BUDGET_PLAN_FRAME_DATA_ID,
) -> tuple[str, str, LLoopBudgetPlanFrame]:
    """L1의 예산 요청과 코드의 승인 예산을 분리해서 기록한다.

    L1이 "더 많이 검색/열람하고 싶다"고 말하는 것은 상대/혼합 정보에 가깝다.
    반면 실제로 몇 번까지 도구를 허용할지는 런타임 정책의 절대 정보다.
    이 함수는 그 둘을 한 프레임에 나란히 남겨서, 나중에 어느 쪽 판단인지
    헷갈리지 않게 만든다.

    budget_plan_data_id를 인자로 받는 이유:
    L루프 2회차 이상에서는 예산 계획도 run scope 안에 들어가야 한다.
    현재 상위 재라우팅을 막는 남은 축 중 하나가 budget/control/tool 계열 ID다.
    """

    goal_payload = _payload_dict(data_store.require_record(goal_data_id).payload)
    requested_search_top_k = _nonnegative_int(goal_payload.get("requested_search_top_k"))
    requested_max_tool_calls = _nonnegative_int(goal_payload.get("requested_max_tool_calls"))
    requested_max_read_doc_calls = _nonnegative_int(goal_payload.get("requested_max_read_doc_calls"))
    requested_max_query_attempts = _nonnegative_int(
        goal_payload.get("requested_max_query_attempts")
    )
    evidence_requirement_kind = str(goal_payload.get("evidence_requirement_kind") or "unspecified")
    minimum_read_documents = _nonnegative_int(goal_payload.get("minimum_read_documents"))
    requires_cross_document_analysis = _bool_value(
        goal_payload.get("requires_cross_document_analysis")
    )
    requirement_min_read_doc_calls = _requirement_min_read_doc_calls(
        evidence_requirement_kind=evidence_requirement_kind,
        minimum_read_documents=minimum_read_documents,
        requires_cross_document_analysis=requires_cross_document_analysis,
    )
    requirement_min_search_top_k = _requirement_min_search_top_k(
        evidence_requirement_kind=evidence_requirement_kind,
        requirement_min_read_doc_calls=requirement_min_read_doc_calls,
        requires_cross_document_analysis=requires_cross_document_analysis,
    )
    effective_requested_search_top_k = max(requested_search_top_k, requirement_min_search_top_k)
    effective_requested_max_read_doc_calls = max(
        requested_max_read_doc_calls,
        requirement_min_read_doc_calls,
    )

    approved_search_top_k = _approve_budget(
        base_value=base_search_top_k,
        requested_value=effective_requested_search_top_k,
        ceiling=SEARCH_TOP_K_CEILING,
    )
    approved_max_tool_calls_before_alignment = _approve_budget(
        base_value=base_max_tool_calls,
        requested_value=requested_max_tool_calls,
        ceiling=MAX_TOOL_CALLS_CEILING,
    )
    approved_max_read_doc_calls = _approve_budget(
        base_value=base_max_read_doc_calls,
        requested_value=effective_requested_max_read_doc_calls,
        ceiling=MAX_READ_DOC_CALLS_CEILING,
    )
    approved_max_query_attempts = _approve_budget(
        base_value=base_max_query_attempts,
        requested_value=requested_max_query_attempts,
        ceiling=MAX_QUERY_ATTEMPTS_CEILING,
    )
    read_doc_budget_expanded_by_l1 = (
        effective_requested_max_read_doc_calls > base_max_read_doc_calls
    )
    approved_max_tool_calls = (
        _align_tool_calls_with_read_doc_budget(
            approved_max_tool_calls=approved_max_tool_calls_before_alignment,
            approved_max_read_doc_calls=approved_max_read_doc_calls,
            ceiling=MAX_TOOL_CALLS_CEILING,
        )
        if read_doc_budget_expanded_by_l1
        else approved_max_tool_calls_before_alignment
    )
    tool_calls_aligned_for_read_docs = (
        approved_max_tool_calls > approved_max_tool_calls_before_alignment
    )
    expanded_from_evidence_requirement = (
        requirement_min_read_doc_calls > requested_max_read_doc_calls
        or requirement_min_search_top_k > requested_search_top_k
    )

    approval_reason = _approval_reason(
        tool_calls_aligned_for_read_docs=tool_calls_aligned_for_read_docs,
        expanded_from_evidence_requirement=expanded_from_evidence_requirement,
        requested_values=[
            effective_requested_search_top_k,
            requested_max_tool_calls,
            effective_requested_max_read_doc_calls,
            requested_max_query_attempts,
        ],
        base_values=[
            base_search_top_k,
            base_max_tool_calls,
            base_max_read_doc_calls,
            base_max_query_attempts,
        ],
        approved_values=[
            approved_search_top_k,
            approved_max_tool_calls,
            approved_max_read_doc_calls,
            approved_max_query_attempts,
        ],
        ceilings=[
            SEARCH_TOP_K_CEILING,
            MAX_TOOL_CALLS_CEILING,
            MAX_READ_DOC_CALLS_CEILING,
            MAX_QUERY_ATTEMPTS_CEILING,
        ],
    )

    frame = LLoopBudgetPlanFrame(
        frame_id=budget_plan_data_id,
        turn_id=turn_id,
        target_loop="L",
        requested_by="L1",
        approved_by="CODE:BUDGET_POLICY",
        goal_data_id=goal_data_id,
        requested_search_top_k=requested_search_top_k,
        requested_max_tool_calls=requested_max_tool_calls,
        requested_max_read_doc_calls=requested_max_read_doc_calls,
        requested_max_query_attempts=requested_max_query_attempts,
        approved_search_top_k=approved_search_top_k,
        approved_max_tool_calls=approved_max_tool_calls,
        approved_max_read_doc_calls=approved_max_read_doc_calls,
        approved_max_query_attempts=approved_max_query_attempts,
        search_top_k_ceiling=SEARCH_TOP_K_CEILING,
        max_tool_calls_ceiling=MAX_TOOL_CALLS_CEILING,
        max_read_doc_calls_ceiling=MAX_READ_DOC_CALLS_CEILING,
        max_query_attempts_ceiling=MAX_QUERY_ATTEMPTS_CEILING,
        budget_request_reason=str(goal_payload.get("budget_request_reason") or "").strip(),
        approval_reason=approval_reason,
        source_trace_ids=[l1_event.event_id],
        source_data_ids=[goal_data_id],
    )
    validate_l_loop_budget_plan_frame(frame)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="CODE:BUDGET_POLICY",
        event_type="node_output",
        input_ref=[l1_event.event_id],
        output_ref=[budget_plan_data_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=budget_plan_data_id,
        data_type="node_output:l_loop_budget_plan_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, budget_plan_data_id, frame


def _approve_budget(*, base_value: int, requested_value: int, ceiling: int) -> int:
    """기본 예산과 L1 요청 중 큰 값을 쓰되, 정책 한도는 넘기지 않는다."""

    requested_or_base = (
        max(base_value, requested_value) if requested_value > 0 else base_value
    )
    return min(requested_or_base, ceiling)


def _requirement_min_read_doc_calls(
    *,
    evidence_requirement_kind: str,
    minimum_read_documents: int,
    requires_cross_document_analysis: bool,
) -> int:
    """L1의 구조화된 근거 요구사항을 최소 read_doc 예산 후보로 바꾼다."""

    required = minimum_read_documents
    if evidence_requirement_kind in {"multi_doc_relationship", "exploratory_multi_doc"}:
        required = max(required, 2)
    if evidence_requirement_kind in {"single_doc_lookup", "exact_artifact_lookup"}:
        required = max(required, 1)
    if requires_cross_document_analysis:
        required = max(required, 2)
    return required


def _requirement_min_search_top_k(
    *,
    evidence_requirement_kind: str,
    requirement_min_read_doc_calls: int,
    requires_cross_document_analysis: bool,
) -> int:
    """다문서 열람 요구가 있을 때 검색 후보 수도 함께 넉넉하게 요청한다."""

    if (
        evidence_requirement_kind in {"multi_doc_relationship", "exploratory_multi_doc"}
        or requires_cross_document_analysis
    ):
        return max(3, requirement_min_read_doc_calls + 2)
    return 0


def _align_tool_calls_with_read_doc_budget(
    *,
    approved_max_tool_calls: int,
    approved_max_read_doc_calls: int,
    ceiling: int,
) -> int:
    """read_doc 승인 횟수와 총 tool call 승인 횟수가 서로 모순되지 않게 맞춘다."""

    # search_docs 한 번도 tool call을 소비하므로 read_doc N개를 허용하려면 최소 N+1회가 필요하다.
    # 장기 과제: 이 보정도 예산 정책의 절대 정보로 기록되지만, L1/L2가 도구 계획을 더 잘 쓰면
    # "검색 1회 + 열람 N회" 같은 계획을 별도 frame으로 노출하는 편이 더 깔끔하다.
    minimum_tool_calls = SEARCH_TOOL_CALL_OVERHEAD + approved_max_read_doc_calls
    return min(max(approved_max_tool_calls, minimum_tool_calls), ceiling)


def _approval_reason(
    *,
    tool_calls_aligned_for_read_docs: bool,
    expanded_from_evidence_requirement: bool,
    requested_values: list[int],
    base_values: list[int],
    approved_values: list[int],
    ceilings: list[int],
) -> str:
    """예산 승인 이유를 코드 상태 라벨로 만든다."""

    reasons: list[str] = []
    if any(
        base > ceiling or requested > ceiling
        for base, requested, ceiling in zip(base_values, requested_values, ceilings)
    ):
        reasons.append("CODE_STATUS:budget_reduced_by_policy_ceiling")
    if tool_calls_aligned_for_read_docs:
        reasons.append("CODE_STATUS:tool_calls_aligned_with_read_doc_budget")
    if expanded_from_evidence_requirement:
        reasons.append("CODE_STATUS:budget_expanded_from_l1_evidence_requirement")
    if any(approved > base for approved, base in zip(approved_values, base_values)):
        reasons.append("CODE_STATUS:budget_expanded_from_l1_request")
    if not reasons:
        reasons.append("CODE_STATUS:base_budget_retained")
    return " | ".join(reasons)


def _payload_dict(payload: object) -> dict[str, object]:
    return payload if isinstance(payload, dict) else {}


def _nonnegative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, str):
        try:
            return max(int(value.strip()), 0)
        except ValueError:
            return 0
    return 0


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return False
