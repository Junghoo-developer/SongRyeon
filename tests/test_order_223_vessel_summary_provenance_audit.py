from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.graph_vessel_summary_provenance_audit import (
    GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_DATA_TYPE,
    audit_graph_vessel_summary_provenance_from_neo4j,
    record_graph_vessel_summary_provenance_audit_result,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.runtime.graph_vessel_summary_provenance_audit import (
    render_vessel_summary_provenance_audit_text,
)


def test_vessel_summary_provenance_audit_classifies_existing_summaries() -> None:
    result = audit_graph_vessel_summary_provenance_from_neo4j(
        config=_config(),
        batch_id="order_223_audit",
        created_at="2026-07-09T12:00:00",
        driver_factory=FakeSummaryAuditDriverFactory(summary_rows=_summary_rows()),
    )

    assert result.audit_status == "passed"
    assert result.total_summary_count == 4
    assert result.recorded_provenance_count == 1
    assert result.legacy_not_recorded_count == 1
    assert result.incomplete_provenance_count == 1
    assert result.invalid_provenance_status_count == 1
    assert result.provenance_count_by_status == {
        "legacy_not_recorded": 1,
        "recorded": 2,
        "wrong_status": 1,
    }
    assert result.summary_count_by_data_kind == {
        "source_leaf_summary": 2,
        "token_budget_bundle_summary": 2,
    }
    assert result.legacy_sample_items[0]["summary_data_id"] == "summary:legacy"
    assert result.incomplete_sample_items[0]["summary_data_id"] == "summary:incomplete"


def test_vessel_summary_provenance_audit_records_absolute_result() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_summary_provenance_audit_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_223",
        config=_config(),
        batch_id="order_223_record",
        created_at="2026-07-09T12:00:00",
        driver_factory=FakeSummaryAuditDriverFactory(summary_rows=_summary_rows()),
    )

    record = data_store.require_record(recorded.result.result_id)
    assert record.data_type == GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDIT_DATA_TYPE
    assert record.payload["generated_by"] == "CODE:GRAPH_VESSEL_SUMMARY_PROVENANCE_AUDITOR"
    assert record.payload["info_class"] == "absolute"
    assert record.payload["semantic_judgement_status"] == "not_run"
    assert trace_store.list_events()[0].actor == "graph_vessel_summary_provenance_auditor"


def test_vessel_summary_provenance_audit_missing_password_does_not_call_driver() -> None:
    factory = RaisingDriverFactory()

    result = audit_graph_vessel_summary_provenance_from_neo4j(
        config=_config(password=None),
        driver_factory=factory,
    )

    assert result.audit_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert factory.called is False


def test_vessel_summary_provenance_text_renderer_mentions_legacy_samples() -> None:
    rendered = render_vessel_summary_provenance_audit_text(
        {
            "status": "VESSEL_SUMMARY_PROVENANCE_AUDIT_OK",
            "audit_status": "passed",
            "failure_type": None,
            "failure_reason": None,
            "graph_namespace": "songryeon_core_graph_v0",
            "total_summary_count": 2,
            "recorded_provenance_count": 1,
            "legacy_not_recorded_count": 1,
            "incomplete_provenance_count": 0,
            "invalid_provenance_status_count": 0,
            "provenance_count_by_status": {"recorded": 1, "legacy_not_recorded": 1},
            "summary_count_by_data_kind": {"source_leaf_summary": 2},
            "legacy_sample_items": [
                {
                    "data_kind": "source_leaf_summary",
                    "summary_data_id": "summary:legacy",
                    "missing_fields": [
                        "summary_run_id",
                        "night_turn_id",
                        "night_batch_id",
                        "summary_created_at",
                        "run_provenance_status",
                    ],
                }
            ],
            "incomplete_sample_items": [],
        }
    )

    assert "legacy_not_recorded_count: 1" in rendered
    assert "Legacy summary samples" in rendered
    assert "summary:legacy" in rendered


def _summary_rows() -> list[dict[str, object]]:
    return [
        _row(
            "summary:recorded",
            "source_leaf_summary",
            {
                "data_kind": "source_leaf_summary",
                "summary_depth": 1,
                "validity_status": "active",
                "summary_run_id": "batch_001",
                "night_turn_id": "turn_001",
                "night_batch_id": "batch_001",
                "summary_created_at": "2026-07-09T12:00:00",
                "run_provenance_status": "recorded",
            },
        ),
        _row(
            "summary:legacy",
            "source_leaf_summary",
            {
                "data_kind": "source_leaf_summary",
                "summary_depth": 1,
                "validity_status": "active",
            },
        ),
        _row(
            "summary:incomplete",
            "token_budget_bundle_summary",
            {
                "data_kind": "token_budget_bundle_summary",
                "summary_depth": 2,
                "validity_status": "active",
                "summary_run_id": "batch_002",
                "run_provenance_status": "recorded",
            },
        ),
        _row(
            "summary:invalid",
            "token_budget_bundle_summary",
            {
                "data_kind": "token_budget_bundle_summary",
                "summary_depth": 2,
                "validity_status": "active",
                "summary_run_id": "batch_003",
                "night_turn_id": "turn_003",
                "night_batch_id": "batch_003",
                "summary_created_at": "2026-07-09T12:00:00",
                "run_provenance_status": "wrong_status",
            },
        ),
    ]


def _row(data_id: str, data_kind: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "summary_data_id": data_id,
        "summary_display_name": data_id,
        "summary_data_kind": data_kind,
        "summary_info_class": "mixed",
        "summary_generated_by": "LLM:fake",
        "summary_payload_json": json.dumps(payload, ensure_ascii=False),
    }


def _config(password: str | None = "pw") -> GraphVesselNeo4jConfig:
    return GraphVesselNeo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password=password,
        database="neo4j",
    )


class FakeSummaryAuditDriverFactory:
    def __init__(self, *, summary_rows: list[dict[str, object]]) -> None:
        self.summary_rows = list(summary_rows)

    def __call__(self, uri: str, *, auth: object) -> "FakeSummaryAuditDriver":
        return FakeSummaryAuditDriver(summary_rows=self.summary_rows)


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FakeSummaryAuditDriver:
    def __init__(self, *, summary_rows: list[dict[str, object]]) -> None:
        self.summary_rows = list(summary_rows)

    def session(self, *, database: str) -> "FakeSummaryAuditSession":
        return FakeSummaryAuditSession(self)

    def close(self) -> None:
        pass


class FakeSummaryAuditSession:
    def __init__(self, driver: FakeSummaryAuditDriver) -> None:
        self.driver = driver

    def __enter__(self) -> "FakeSummaryAuditSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, fn, *args):
        return fn(FakeSummaryAuditTransaction(self.driver), *args)


class FakeSummaryAuditTransaction:
    def __init__(self, driver: FakeSummaryAuditDriver) -> None:
        self.driver = driver

    def run(self, _query: str, **_kwargs):
        return FakeSummaryAuditResult(self.driver.summary_rows)


class FakeSummaryAuditResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)

