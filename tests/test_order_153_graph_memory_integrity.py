from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory_integrity import audit_graph_memory_integrity
from songryeon_core.core.schemas import R_ROUTE_EXPERIMENTAL_NEXT_0_MODE
from songryeon_core.llm.base import LLMRequest, LLMResponse
from songryeon_core.runtime.dry_run import run_dry_turn


def test_default_dry_turn_graph_memory_integrity_passes() -> None:
    result = run_dry_turn()
    report = audit_graph_memory_integrity(_data_store_from_result(result))

    assert report.passed, report.to_summary()


def test_r_experimental_route_records_graph_sources_before_handoff() -> None:
    result = run_dry_turn(
        user_input="그래프 기억을 R로 한 번만 실험해줘",
        node_1_router_adapter=RRouteFakeAdapter(),
        enable_r_route_experimental=True,
    )
    graph_data_ids = result["r_route_experimental_graph_data_ids"]
    report = audit_graph_memory_integrity(_data_store_from_result(result))

    assert result["r_route_experimental_status"] == "selected"
    assert "graph:snapshot:turn_dry_001:r_route_experimental" in graph_data_ids
    assert (
        "rloop:graph_guide:graph:snapshot:turn_dry_001:r_route_experimental"
        in graph_data_ids
    )
    assert "graph:time_bundle:turn_dry_001:r_route_experimental" in graph_data_ids
    assert report.passed, report.to_summary()


def test_graph_integrity_audit_reports_missing_source_ref() -> None:
    data_store = DataStore()
    data_store.create_record(
        data_id="node_output:bad_graph_ref",
        data_type="node_output:test",
        payload={"source_data_ids": ["graph:missing:node"]},
    )

    report = audit_graph_memory_integrity(data_store)

    assert not report.passed
    assert report.missing_source_refs[0].missing_ref == "graph:missing:node"
    assert report.missing_edge_endpoints == []


def test_graph_integrity_audit_reports_missing_edge_endpoint() -> None:
    data_store = DataStore()
    data_store.create_record(
        data_id="graph:edge:bad",
        data_type="graph_memory:edge:CONTAINS",
        payload={
            "edge_id": "graph:edge:bad",
            "edge_kind": "CONTAINS",
            "from_node_id": "graph:missing:from",
            "to_node_id": "graph:missing:to",
            "source_data_ids": [],
        },
    )

    report = audit_graph_memory_integrity(data_store)

    assert not report.passed
    assert {issue.missing_ref for issue in report.missing_edge_endpoints} == {
        "graph:missing:from",
        "graph:missing:to",
    }


class RRouteFakeAdapter:
    model_id = "r-route-fake"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if "node_1 Router" not in request.prompt:
            return LLMResponse(text="{}", model_id=self.model_id, raw={})
        payload = {
            "route": "R",
            "route_reason": "graph memory traversal looks useful",
            "expected_next_0_mode": R_ROUTE_EXPERIMENTAL_NEXT_0_MODE,
            "route_confidence": 0.71,
            "needs_more_memory": False,
        }
        return LLMResponse(
            text=json.dumps(payload, ensure_ascii=False),
            model_id=self.model_id,
            raw=payload,
        )


def _data_store_from_result(result: dict[str, object]) -> DataStore:
    records = result["data_records"]
    assert isinstance(records, list)
    return DataStore.from_records(records)
