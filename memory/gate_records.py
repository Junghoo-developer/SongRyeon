"""Node2·Node4 판단과 코드가 적용한 라우팅 결과를 기록한다."""

from .audit import (
    canonical_json,
    new_audit_record,
    validate_visible_batch,
)
from .settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)
from .store import append_information_records


def save_node1_route(
    *,
    requested_action,
    reason,
    tool_name,
    arguments,
    next_node,
    outcome,
    forced_by_tool_limit,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """Node1의 R 요청과 코드가 적용한 A 라우팅을 기록한다."""

    request = canonical_json(
        {
            "action": requested_action,
            "arguments": arguments,
            "tool_name": tool_name,
        }
    )
    applied_route = canonical_json(
        {
            "forced_by_tool_limit": forced_by_tool_limit,
            "next_node": next_node,
            "outcome": outcome,
        }
    )
    records = [
        new_audit_record("node1", "absolute", "source", turn_id),
        new_audit_record(
            request,
            "relative",
            "node1_next_action",
            turn_id,
        ),
        new_audit_record(reason, "relative", "reason", turn_id),
        new_audit_record(
            applied_route,
            "absolute",
            "runtime_route",
            turn_id,
        ),
    ]

    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)


def save_gate_review(
    *,
    reviewer,
    verdict,
    reason,
    rejection_count,
    maximum_rejections,
    outcome,
    next_node,
    rejection_ignored,
    turn_id,
    memory_path=DEFAULT_MEMORY_PATH,
):
    """Node2·Node4의 R 판단과 코드가 적용한 A 결과를 기록한다."""

    action = canonical_json(
        {
            "next_node": next_node,
            "outcome": outcome,
            "rejection_ignored": rejection_ignored,
        }
    )
    count = canonical_json(
        {
            "count": rejection_count,
            "maximum": maximum_rejections,
        }
    )
    records = [
        new_audit_record(reviewer, "absolute", "source", turn_id),
        new_audit_record(verdict, "relative", "decision", turn_id),
        new_audit_record(reason, "relative", "reason", turn_id),
        new_audit_record(
            count,
            "absolute",
            "rejection_count",
            turn_id,
        ),
        new_audit_record(action, "absolute", "action", turn_id),
    ]

    validate_visible_batch(
        records,
        DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    )
    return append_information_records(records, memory_path)
