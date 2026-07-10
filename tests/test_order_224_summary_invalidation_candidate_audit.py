from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.graph_vessel_summary_invalidation_candidate_audit import (
    GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_DATA_TYPE,
    audit_graph_vessel_summary_invalidation_candidates_from_neo4j,
    record_graph_vessel_summary_invalidation_candidate_audit_result,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.runtime.graph_vessel_summary_invalidation_candidate_audit import (
    render_vessel_summary_invalidation_candidate_audit_text,
)


def test_summary_invalidation_candidate_audit_finds_changed_source_candidates() -> None:
    result = audit_graph_vessel_summary_invalidation_candidates_from_neo4j(
        config=_config(),
        batch_id="order_224_audit",
        created_at="2026-07-10T10:00:00",
        driver_factory=FakeInvalidationAuditDriverFactory(
            lineage_rows=_lineage_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    assert result.audit_status == "passed"
    assert result.source_lineage_count == 3
    assert result.changed_lineage_count == 2
    assert result.superseded_source_count == 1
    assert result.total_summary_count == 4
    assert result.invalidation_candidate_count == 1
    assert result.already_invalidated_candidate_count == 1
    assert result.manual_review_candidate_count == 1
    assert result.candidate_records[0]["summary_graph_node_id"] == "summary:old_active"
    assert result.candidate_records[0]["action_status"] == "candidate_only_not_applied"
    assert result.candidate_records[0]["proposed_validity_status"] == (
        "invalidated_by_source_change"
    )


def test_summary_invalidation_candidate_audit_records_absolute_result() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_summary_invalidation_candidate_audit_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_224",
        config=_config(),
        batch_id="order_224_record",
        created_at="2026-07-10T10:00:00",
        driver_factory=FakeInvalidationAuditDriverFactory(
            lineage_rows=_lineage_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    record = data_store.require_record(recorded.result.result_id)
    assert record.data_type == GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_DATA_TYPE
    assert record.payload["generated_by"] == (
        "CODE:GRAPH_VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDITOR"
    )
    assert record.payload["info_class"] == "absolute"
    assert record.payload["semantic_judgement_status"] == "not_run"
    assert trace_store.list_events()[0].actor == (
        "graph_vessel_summary_invalidation_candidate_auditor"
    )


def test_summary_invalidation_candidate_audit_missing_password_does_not_call_driver() -> None:
    factory = RaisingDriverFactory()

    result = audit_graph_vessel_summary_invalidation_candidates_from_neo4j(
        config=_config(password=None),
        driver_factory=factory,
    )

    assert result.audit_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert factory.called is False


def test_summary_invalidation_candidate_text_renderer_mentions_candidates() -> None:
    rendered = render_vessel_summary_invalidation_candidate_audit_text(
        {
            "status": "VESSEL_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_OK",
            "audit_status": "passed",
            "failure_type": None,
            "failure_reason": None,
            "graph_namespace": "songryeon_core_graph_v0",
            "total_summary_count": 1,
            "source_lineage_count": 1,
            "changed_lineage_count": 1,
            "superseded_source_count": 1,
            "invalidation_candidate_count": 1,
            "already_invalidated_candidate_count": 0,
            "manual_review_candidate_count": 0,
            "candidate_records": [
                {
                    "summary_graph_node_id": "summary:old_active",
                    "superseded_source_graph_node_id": "raw:old",
                    "superseding_source_graph_node_id": "raw:new",
                }
            ],
            "manual_review_records": [],
        }
    )

    assert "invalidation_candidate_count: 1" in rendered
    assert "Invalidation candidate samples" in rendered
    assert "summary:old_active" in rendered


def _lineage_rows() -> list[dict[str, object]]:
    return [
        _lineage_row(
            "lineage:changed",
            {
                "lineage_status": "content_changed",
                "active_source_graph_node_id": "raw:new",
                "superseded_source_graph_node_ids": ["raw:old"],
            },
        ),
        _lineage_row(
            "lineage:stable",
            {
                "lineage_status": "single_version",
                "active_source_graph_node_id": "raw:stable",
                "superseded_source_graph_node_ids": [],
            },
        ),
        _lineage_row(
            "lineage:manual",
            {
                "lineage_status": "content_changed",
                "active_source_graph_node_id": "raw:manual_new",
                "superseded_source_graph_node_ids": [],
            },
        ),
    ]


def _summary_rows() -> list[dict[str, object]]:
    return [
        _summary_row(
            "summary:old_active",
            {
                "validity_status": "active",
                "source_graph_node_ids": ["raw:old"],
            },
        ),
        _summary_row(
            "summary:already_invalidated",
            {
                "validity_status": "invalidated_by_source_change",
                "source_graph_node_ids": ["raw:old"],
            },
        ),
        _summary_row(
            "summary:new",
            {
                "validity_status": "active",
                "source_graph_node_ids": ["raw:new"],
            },
        ),
        _summary_row(
            "summary:stable",
            {
                "validity_status": "active",
                "source_graph_node_ids": ["raw:stable"],
            },
        ),
    ]


def _lineage_row(data_id: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "source_lineage_frame_id": data_id,
        "lineage_payload_json": json.dumps(payload, ensure_ascii=False),
    }


def _summary_row(data_id: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "summary_graph_node_id": data_id,
        "summary_payload_json": json.dumps(payload, ensure_ascii=False),
    }


def _config(password: str | None = "pw") -> GraphVesselNeo4jConfig:
    return GraphVesselNeo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password=password,
        database="neo4j",
    )


class FakeInvalidationAuditDriverFactory:
    def __init__(
        self,
        *,
        lineage_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
    ) -> None:
        self.lineage_rows = list(lineage_rows)
        self.summary_rows = list(summary_rows)

    def __call__(self, uri: str, *, auth: object) -> "FakeInvalidationAuditDriver":
        return FakeInvalidationAuditDriver(
            lineage_rows=self.lineage_rows,
            summary_rows=self.summary_rows,
        )


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FakeInvalidationAuditDriver:
    def __init__(
        self,
        *,
        lineage_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
    ) -> None:
        self.lineage_rows = list(lineage_rows)
        self.summary_rows = list(summary_rows)

    def session(self, *, database: str) -> "FakeInvalidationAuditSession":
        return FakeInvalidationAuditSession(self)

    def close(self) -> None:
        pass


class FakeInvalidationAuditSession:
    def __init__(self, driver: FakeInvalidationAuditDriver) -> None:
        self.driver = driver

    def __enter__(self) -> "FakeInvalidationAuditSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, fn, *args):
        return fn(FakeInvalidationAuditTransaction(self.driver), *args)


class FakeInvalidationAuditTransaction:
    def __init__(self, driver: FakeInvalidationAuditDriver) -> None:
        self.driver = driver
        self.call_index = 0

    def run(self, _query: str, **_kwargs):
        self.call_index += 1
        if self.call_index == 1:
            return FakeInvalidationAuditResult(self.driver.lineage_rows)
        return FakeInvalidationAuditResult(self.driver.summary_rows)


class FakeInvalidationAuditResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)

