from __future__ import annotations

from songryeon_core.llm.fake import BrokenJSONFakeLLMAdapter, SongRyeonAllNodesFakeLLMAdapter
from songryeon_core.nodes.node_1_router import (
    ROUTER_FALLBACK_POLICY_DEV_SMOKE,
    ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
    Node1RouterLLMFailure,
)
from songryeon_core.runtime.dry_run import run_dry_turn
from songryeon_core.runtime.terminal_view import render_pretty_turn


def run_router_fallback_honesty_smoke() -> dict[str, object]:
    """node_1 LLM 실패 뒤 code fallback이 정직하게 구분되는지 확인한다."""

    user_input = "그냥 보고해줘"
    success = run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=SongRyeonAllNodesFakeLLMAdapter(),
    )
    success_route = _first_routing_payload(success)
    if success_route.get("llm_routing_status") != "ran":
        raise AssertionError("node_1 LLM router success must record llm_routing_status=ran")
    if success_route.get("fallback_after_llm_failure") is not False:
        raise AssertionError("node_1 LLM router success must not look like fallback")

    fallback = run_dry_turn(
        user_input=user_input,
        node_1_router_adapter=BrokenJSONFakeLLMAdapter(),
    )
    fallback_route = _first_routing_payload(fallback)
    failure_data_id = fallback_route.get("router_llm_failure_data_id")
    failure_trace_id = fallback_route.get("router_llm_failure_trace_event_id")
    source_data_ids = fallback_route.get("source_data_ids")
    source_trace_ids = fallback_route.get("source_trace_ids")
    if fallback_route.get("llm_routing_status") != "failed":
        raise AssertionError("fallback route must record llm_routing_status=failed")
    if fallback_route.get("fallback_after_llm_failure") is not True:
        raise AssertionError("fallback route must record fallback_after_llm_failure=true")
    if fallback_route.get("fallback_policy") != ROUTER_FALLBACK_POLICY_DEV_SMOKE:
        raise AssertionError("fallback route must record the dev/smoke fallback policy")
    if fallback_route.get("fallback_allowed_by_runtime_policy") is not True:
        raise AssertionError("fallback route must record runtime policy allowance")
    if fallback_route.get("fallback_source_route_rule_id") != fallback_route.get("route_rule_id"):
        raise AssertionError("fallback route must preserve the code route rule id")
    if fallback_route.get("router_llm_failure_type") != "parse_failed":
        raise AssertionError("fallback route must preserve the LLM failure type")
    if not isinstance(failure_data_id, str) or not isinstance(source_data_ids, list):
        raise AssertionError("fallback route must cite the failed LLM call data id")
    if failure_data_id not in source_data_ids:
        raise AssertionError("fallback route source_data_ids must include failed LLM call id")
    if not isinstance(failure_trace_id, str) or not isinstance(source_trace_ids, list):
        raise AssertionError("fallback route must cite the failed LLM trace event id")
    if failure_trace_id not in source_trace_ids:
        raise AssertionError("fallback route source_trace_ids must include failed LLM trace id")

    code = run_dry_turn(user_input=user_input)
    code_terminal = render_pretty_turn(code, user_input=user_input)
    fallback_terminal = render_pretty_turn(fallback, user_input=user_input)
    if "node_1 router: CODE:RULE_STUB" not in code_terminal:
        raise AssertionError("terminal must show direct code router status")
    if "node_1 router: LLM failed -> CODE:RULE_STUB fallback" not in fallback_terminal:
        raise AssertionError("terminal must distinguish LLM failure fallback")

    strict_blocked = False
    try:
        run_dry_turn(
            user_input=user_input,
            node_1_router_adapter=BrokenJSONFakeLLMAdapter(),
            allow_node_1_router_fallback=False,
            node_1_router_fallback_policy=ROUTER_FALLBACK_POLICY_QWEN_STRICT_BLOCKED,
        )
    except Node1RouterLLMFailure:
        strict_blocked = True
    if not strict_blocked:
        raise AssertionError("strict router policy must not silently allow fallback")

    return {
        "fallback_policy": fallback_route["fallback_policy"],
        "failure_type": fallback_route["router_llm_failure_type"],
        "terminal_distinct": True,
        "strict_blocked": strict_blocked,
    }


def _first_routing_payload(result: dict[str, object]) -> dict[str, object]:
    records = result.get("data_records")
    if not isinstance(records, list):
        raise AssertionError("data_records must be a list")
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("data_type") != "node_output:routing_decision":
            continue
        payload = record.get("payload")
        if isinstance(payload, dict):
            return payload
    raise AssertionError("routing decision payload not found")
