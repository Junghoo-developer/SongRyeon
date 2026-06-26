from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MemoryPacketFrom0,
    RoutingDecision,
    RoutingDecisionFrame,
    validate_routing_decision_frame,
)
from songryeon_core.core.registry import SchemaRegistry
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds


L_ROUTE_KEYWORDS = {
    "문서",
    "검색",
    "기억",
    "장기",
    "내부",
    "너는",
    "누구",
    "정체",
    "소개",
    "송련",
    "L",
    "루프",
}

ROUTER_FALLBACK_POLICY_DEV_SMOKE = "dev_smoke_router_fallback_allowed"
ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED = "qwen_strict_router_fallback_blocked"


class Node1RouterLLMFailure(ValueError):
    """node_1 LLM router 실패의 절대 식별자를 보존하는 예외."""

    def __init__(
        self,
        *,
        failure_type: str,
        call_data_id: str | None,
        trace_event_id: str | None,
    ) -> None:
        super().__init__(f"node_1 LLM router failed: {failure_type}")
        self.failure_type = failure_type
        self.call_data_id = call_data_id
        self.trace_event_id = trace_event_id


def route_next(
    *,
    user_input: str,
    memory_packet: MemoryPacketFrom0,
    schema_registry: SchemaRegistry,
    force_l_route: bool = False,
) -> RoutingDecision:
    """1 상황판단 라우터의 규칙 기반 라우팅."""

    if force_l_route:
        route = "L"
        next_0_mode = "targeted_memory_supply"
        reason = "CODE_STATUS:force_l_route_policy"
        route_source = "CODE:POLICY_STUB"
        route_rule_id = "force_l_route_policy"
        matched_keywords: list[str] = []
        policy_flag = "force_l_route"
    elif _should_route_to_l(user_input):
        route = "L"
        next_0_mode = "targeted_memory_supply"
        reason = "CODE_STATUS:l_route_keyword_match"
        route_source = "CODE:RULE_STUB"
        route_rule_id = "l_route_keyword_match"
        matched_keywords = _matched_l_keywords(user_input)
        policy_flag = None
    else:
        route = "2"
        next_0_mode = "final_trace_for_2"
        reason = "CODE_STATUS:default_route_to_node_2"
        route_source = "CODE:RULE_STUB"
        route_rule_id = "default_route_to_node_2"
        matched_keywords = []
        policy_flag = None

    target_node = "node_2" if route == "2" else "L"
    return RoutingDecision(
        route=route,
        route_reason=reason,
        route_source=route_source,
        required_schema=schema_registry.binding_for(target_node),
        expected_next_0_mode=next_0_mode,
        route_rule_id=route_rule_id,
        matched_keywords=matched_keywords,
        policy_flag=policy_flag,
    )


def route_next_with_llm(
    *,
    user_input: str,
    memory_packet: MemoryPacketFrom0,
    schema_registry: SchemaRegistry,
    adapter: LLMAdapter,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_ref: list[str],
    source_data_ids: list[str],
    max_retries: int = 0,
) -> RoutingDecision:
    """LLM으로 1번 라우팅을 수행한다.

    실패하면 여기서 fallback을 위장하지 않고 예외를 던진다. 호출자는 기존
    코드 라우터로 떨어뜨리되 그 사실을 route_source로 남긴다.
    """

    prompt_ref = "songryeon_core/prompts/node_1_router_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    input_payload = {
        "user_input": user_input,
        "memory_packet": {
            "target": memory_packet.target,
            "trace_evidence_ids": memory_packet.trace_evidence_ids,
            "insufficient_signal_id": memory_packet.insufficient_signal_id,
        },
        "memory_packet_records": _memory_packet_records(
            data_store=data_store,
            source_data_ids=source_data_ids,
        ),
        "allowed_routes": ["L", "2"],
        "route_meanings": {
            "L": "내부 문서/장기기억 검색 루프",
            "2": "최종 메타정보 경계 및 보고 단계",
        },
        "source_data_ids": source_data_ids,
    }
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="node_1",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_ref,
        source_data_ids=source_data_ids,
        max_retries=max_retries,
        payload_validator=_validate_llm_routing_payload,
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise Node1RouterLLMFailure(
            failure_type=llm_result.failure_type,
            call_data_id=llm_result.call_data_id,
            trace_event_id=llm_result.trace_event_id,
        )

    return _routing_decision_from_llm_payload(
        payload=llm_result.validation.payload,
        schema_registry=schema_registry,
        model_id=llm_result.model_id,
        llm_trace_event_id=llm_result.trace_event_id,
        llm_call_data_id=llm_result.call_data_id,
    )


def route_next_with_llm_or_policy_fallback(
    *,
    user_input: str,
    memory_packet: MemoryPacketFrom0,
    schema_registry: SchemaRegistry,
    adapter: LLMAdapter,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_ref: list[str],
    source_data_ids: list[str],
    fallback_user_input: str | None = None,
    force_l_route: bool = False,
    fallback_policy: str = ROUTER_FALLBACK_POLICY_DEV_SMOKE,
    fallback_allowed_by_runtime_policy: bool = True,
    max_retries: int = 0,
) -> RoutingDecision:
    """LLM router 실패와 code fallback 결정을 분리해서 보존한다."""

    try:
        return route_next_with_llm(
            user_input=user_input,
            memory_packet=memory_packet,
            schema_registry=schema_registry,
            adapter=adapter,
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            input_ref=input_ref,
            source_data_ids=source_data_ids,
            max_retries=max_retries,
        )
    except Node1RouterLLMFailure as exc:
        if not fallback_allowed_by_runtime_policy:
            raise
        decision = route_next(
            user_input=fallback_user_input if fallback_user_input is not None else user_input,
            memory_packet=memory_packet,
            schema_registry=schema_registry,
            force_l_route=force_l_route,
        )
        return _mark_llm_failure_fallback(
            decision=decision,
            failure=exc,
            fallback_policy=fallback_policy,
            fallback_allowed_by_runtime_policy=fallback_allowed_by_runtime_policy,
        )


def record_routing(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    decision: RoutingDecision,
    input_ref: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    id_namespace: LRunIds | None = None,
    route_context: str = "entry",
) -> str:
    """RoutingDecision이 만들어졌다는 사실을 trace로 기록한다."""

    route_id = (
        id_namespace.return_route_decision_id(decision.route)
        if id_namespace is not None and route_context == "l_return"
        else id_namespace.route_decision_id(decision.route)
        if id_namespace is not None
        else f"route:{decision.route}"
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_1",
        event_type="routing",
        input_ref=input_ref or [],
        output_ref=[route_id],
        schema_status="passed",
    )
    if data_store is not None:
        frame = RoutingDecisionFrame(
            frame_id=route_id,
            turn_id=turn_id,
            route=decision.route,
            route_reason=decision.route_reason,
            expected_next_0_mode=decision.expected_next_0_mode,
            route_source=decision.route_source,
            llm_routing_status=decision.llm_routing_status,
            llm_call_data_id=decision.llm_call_data_id,
            llm_trace_event_id=decision.llm_trace_event_id,
            route_rule_id=decision.route_rule_id,
            matched_keywords=decision.matched_keywords,
            policy_flag=decision.policy_flag,
            route_confidence=decision.route_confidence,
            needs_more_memory=decision.needs_more_memory,
            fallback_after_llm_failure=decision.fallback_after_llm_failure,
            router_llm_failure_data_id=decision.router_llm_failure_data_id,
            router_llm_failure_trace_event_id=decision.router_llm_failure_trace_event_id,
            router_llm_failure_type=decision.router_llm_failure_type,
            fallback_policy=decision.fallback_policy,
            fallback_allowed_by_runtime_policy=decision.fallback_allowed_by_runtime_policy,
            fallback_source_route_rule_id=decision.fallback_source_route_rule_id,
            required_schema=asdict(decision.required_schema)
            if decision.required_schema is not None
            else None,
            source_trace_ids=input_ref or [],
            source_data_ids=source_data_ids or [],
        )
        validate_routing_decision_frame(frame)
        data_store.create_record(
            data_id=route_id,
            data_type="node_output:routing_decision",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
    return event.event_id


def _should_route_to_l(user_input: str) -> bool:
    return any(keyword in user_input for keyword in L_ROUTE_KEYWORDS)


def _memory_packet_records(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> list[dict[str, object]]:
    """node_1 LLM이 0의 구조화 memory_items를 실제 입력으로 볼 수 있게 복사한다."""

    records: list[dict[str, object]] = []
    for data_id in source_data_ids:
        record = data_store.get_record(data_id)
        if record is None or record.data_type != "node_output:memory_packet":
            continue
        if isinstance(record.payload, dict):
            records.append(record.payload)
    return records


def _matched_l_keywords(user_input: str) -> list[str]:
    return [keyword for keyword in sorted(L_ROUTE_KEYWORDS) if keyword in user_input]


def _mark_llm_failure_fallback(
    *,
    decision: RoutingDecision,
    failure: Node1RouterLLMFailure,
    fallback_policy: str,
    fallback_allowed_by_runtime_policy: bool,
) -> RoutingDecision:
    decision.llm_routing_status = "failed"
    decision.llm_call_data_id = failure.call_data_id
    decision.llm_trace_event_id = failure.trace_event_id
    decision.fallback_after_llm_failure = True
    decision.router_llm_failure_data_id = failure.call_data_id
    decision.router_llm_failure_trace_event_id = failure.trace_event_id
    decision.router_llm_failure_type = failure.failure_type
    decision.fallback_policy = fallback_policy
    decision.fallback_allowed_by_runtime_policy = fallback_allowed_by_runtime_policy
    decision.fallback_source_route_rule_id = decision.route_rule_id
    return decision


def _validate_llm_routing_payload(payload: dict[str, object]) -> None:
    _routing_decision_from_llm_payload(
        payload=payload,
        schema_registry=None,
        model_id="validation-model",
        llm_trace_event_id="validation_trace",
        llm_call_data_id="validation_call",
    )


def _routing_decision_from_llm_payload(
    *,
    payload: dict[str, object],
    schema_registry: SchemaRegistry | None,
    model_id: str,
    llm_trace_event_id: str | None,
    llm_call_data_id: str | None,
) -> RoutingDecision:
    route = str(payload.get("route") or "").strip()
    if route not in {"L", "2"}:
        raise ValueError("node_1 route must be L or 2")

    route_reason = str(payload.get("route_reason") or payload.get("reason") or "").strip()
    if not route_reason:
        raise ValueError("node_1 route_reason must not be empty")

    expected_next_0_mode = str(payload.get("expected_next_0_mode") or "").strip()
    expected_for_route = "targeted_memory_supply" if route == "L" else "final_trace_for_2"
    if not expected_next_0_mode or expected_next_0_mode != expected_for_route:
        expected_next_0_mode = expected_for_route

    route_confidence = _optional_float(payload.get("route_confidence"))
    if route_confidence is not None and (route_confidence < 0.0 or route_confidence > 1.0):
        raise ValueError("node_1 route_confidence must be between 0 and 1")

    target_node = "node_2" if route == "2" else "L"
    return RoutingDecision(
        route=route,
        route_reason=route_reason,
        route_source=f"LLM:{model_id}",
        required_schema=schema_registry.binding_for(target_node) if schema_registry is not None else None,
        expected_next_0_mode=expected_next_0_mode,
        route_rule_id="llm_router",
        matched_keywords=[],
        policy_flag=_optional_text(payload.get("policy_flag")),
        route_confidence=route_confidence,
        needs_more_memory=bool(payload.get("needs_more_memory") or False),
        llm_routing_status="ran",
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
    )


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
