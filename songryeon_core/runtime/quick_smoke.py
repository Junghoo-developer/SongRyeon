from __future__ import annotations

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.registry import build_default_schema_registry
from songryeon_core.core.trace_store import TraceStore


def run_quick_smoke_tests() -> dict[str, object]:
    """Run the smallest local health check that avoids expensive retrieval.

    quick-smoke는 "송련이 켜질 수 있는가"만 본다.
    문서 검색, Qwen, Neo4j, L/R traversal은 일부러 호출하지 않는다.
    """

    trace_store = TraceStore()
    event = trace_store.create_event(
        turn_id="turn_quick_smoke_0001",
        actor="quick_smoke",
        event_type="schema_check",
        schema_status="passed",
    )
    data_store = DataStore()
    data_store.create_record(
        data_id="quick_smoke:record:0001",
        data_type="quick_smoke:payload",
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload={
            "status": "ok",
            "purpose": "minimal_runtime_health_check",
        },
    )

    schema_registry = build_default_schema_registry()
    required_schema_targets = [
        "node_0",
        "node_1",
        "node_2",
        "node_2_answer_basis",
        "node_2_input",
        "L3",
    ]
    missing_schema_targets = [
        target
        for target in required_schema_targets
        if schema_registry.binding_for(target) is None
    ]
    if missing_schema_targets:
        raise AssertionError(f"missing schema registry targets: {missing_schema_targets}")

    return {
        "status": "QUICK_SMOKE_OK",
        "trace_count": len(trace_store.list_events()),
        "data_record_count": len(data_store.list_records()),
        "schema_target_count": len(required_schema_targets),
        "missing_schema_targets": missing_schema_targets,
        "document_search_ran": False,
        "qwen_ran": False,
        "neo4j_ran": False,
        "full_smoke_included": False,
    }


__all__ = ["run_quick_smoke_tests"]
