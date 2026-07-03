from __future__ import annotations

import json

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.r_loop_vessel_read_packet import (
    R_LOOP_VESSEL_READ_PACKET_DATA_TYPE,
    R_LOOP_VESSEL_READ_PACKET_GENERATOR,
    build_r_loop_vessel_read_packet_from_neo4j,
    record_r_loop_vessel_read_packet,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.runtime.r_loop_vessel_read_packet import (
    render_r_loop_vessel_read_packet_text,
)


READ_AT = "2026-07-02T19:00:00"


def test_r_loop_vessel_read_packet_reads_entries_and_active_summaries_only() -> None:
    result = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_175_packet",
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    assert result.read_status == "passed"
    assert result.entry_candidate_count == 2
    assert result.summary_candidate_count == 1
    assert result.total_summary_scanned_count == 3
    assert result.active_summary_candidate_count == 1
    assert result.skipped_summary_count == 2
    assert result.summary_count_by_data_kind == {"source_leaf_summary": 1}
    assert result.summary_count_by_depth == {"1": 1}
    assert result.entry_candidate_records[0]["candidate_kind"] == "source_ingest_bundle"
    assert result.summary_candidate_records[0]["summary_node_id"] == (
        "graph:summary:source_leaf:code_tools"
    )
    assert result.summary_candidate_records[0]["summary_text"] == (
        "This source leaf summary is copied from an active LLM summary node."
    )
    assert "graph:summary:invalidated:old" not in result.source_data_ids
    assert "graph:raw_source:code_tools" in result.source_data_ids
    assert result.source_trace_ids == ["trace:source:manifest", "trace:summary:active"]


def test_r_loop_vessel_read_packet_marks_absolute_code_generated() -> None:
    result = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_175_boundary",
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    assert result.generated_by == R_LOOP_VESSEL_READ_PACKET_GENERATOR
    assert result.info_class == "absolute"
    assert result.semantic_judgement_status == "not_run"
    assert result.target_consumer == "R_LOOP"


def test_r_loop_vessel_read_packet_missing_password_does_not_call_driver() -> None:
    fake_driver_factory = RaisingDriverFactory()

    result = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(password=None),
        batch_id="order_175_missing_password",
        created_at=READ_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.read_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert result.entry_candidate_records == []
    assert fake_driver_factory.called is False


def test_r_loop_vessel_read_packet_records_payload_in_datastore() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_r_loop_vessel_read_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_175",
        batch_id="order_175_record",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeRLoopVesselDriverFactory(
            entry_rows=_entry_rows(),
            summary_rows=_summary_rows(),
        ),
    )

    record = data_store.require_record(recorded.packet.packet_id)
    assert record.data_type == R_LOOP_VESSEL_READ_PACKET_DATA_TYPE
    assert record.payload["read_status"] == "passed"
    assert record.payload["target_consumer"] == "R_LOOP"
    assert record.payload["summary_candidate_count"] == 1
    assert recorded.created_data_ids == [recorded.packet.packet_id]
    assert trace_store.list_events()[0].actor == "r_loop_vessel_read_packet_builder"


def test_r_loop_vessel_read_packet_text_renderer_prints_candidate_counts() -> None:
    result = {
        "status": "R_LOOP_VESSEL_READ_PACKET_OK",
        "read_status": "passed",
        "failure_type": None,
        "failure_reason": None,
        "graph_namespace": "songryeon_core_graph_v0",
        "target_consumer": "R_LOOP",
        "entry_candidate_count": 2,
        "summary_candidate_count": 1,
        "total_summary_scanned_count": 3,
        "skipped_summary_count": 2,
        "summary_count_by_data_kind": {"source_leaf_summary": 1},
        "summary_count_by_depth": {"1": 1},
        "packet_text": "\n".join(
            [
                "R loop Vessel entry candidates: 2",
                "Active summary candidates",
                "  source_leaf_summary(depth=1, info=relative) [graph:summary:source_leaf:code_tools]",
            ]
        ),
    }

    rendered = render_r_loop_vessel_read_packet_text(result)

    assert "status: R_LOOP_VESSEL_READ_PACKET_OK" in rendered
    assert "entry_candidate_count: 2" in rendered
    assert "summary_candidate_count: 1" in rendered
    assert "Active summary candidates" in rendered


def test_r_loop_vessel_read_packet_records_driver_exception() -> None:
    result = build_r_loop_vessel_read_packet_from_neo4j(
        config=_config(),
        batch_id="order_175_read_failed",
        created_at=READ_AT,
        driver_factory=FailingDriverFactory(),
    )

    assert result.read_status == "read_failed"
    assert result.failure_type == "neo4j_read_failed"
    assert "simulated R packet read failure" in (result.failure_reason or "")


def _config(
    *,
    password: str | None = "test-password",
    allow_no_auth: bool = False,
) -> GraphVesselNeo4jConfig:
    return GraphVesselNeo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password=password,
        database="neo4j",
        allow_no_auth=allow_no_auth,
    )


def _entry_rows() -> list[dict[str, object]]:
    return [
        {
            "candidate_node_id": "graph:source_ingest_time_bundle:night_changed_sources",
            "display_name": "Source Ingest Bundle",
            "node_kind": "source_ingest_time_bundle",
            "data_kind": "source_ingest_time_bundle",
            "created_at": "2026-07-02T14:02:36",
            "written_at": "2026-07-02T14:02:36",
            "source_trace_id": "trace:source:manifest",
            "payload_json": json.dumps(
                {
                    "node_kind": "source_ingest_time_bundle",
                    "data_kind": "source_ingest_time_bundle",
                    "summary_depth": 0,
                    "source_leaf_count": 552,
                    "source_summary_count": 0,
                },
                ensure_ascii=False,
            ),
            "labels": ["VesselRecord", "GraphMemoryNode", "SourceIngestBundle"],
        },
        {
            "candidate_node_id": "graph:time_bundle:manual_vessel_first_write:core",
            "display_name": "Time Bundle",
            "node_kind": "time_bundle",
            "data_kind": "time_bundle",
            "created_at": "2026-07-01T18:39:54",
            "written_at": "2026-07-01T18:39:54",
            "source_trace_id": None,
            "payload_json": json.dumps(
                {
                    "node_kind": "time_bundle",
                    "data_kind": "time_bundle",
                    "summary_depth": 0,
                    "source_leaf_count": 1,
                    "source_summary_count": 0,
                },
                ensure_ascii=False,
            ),
            "labels": ["VesselRecord", "GraphMemoryNode", "TimeBundle"],
        },
    ]


def _summary_rows() -> list[dict[str, object]]:
    return [
        {
            "summary_node_id": "graph:summary:source_leaf:code_tools",
            "summary_display_name": "Summary: graph:raw_source:code_tools",
            "data_kind": "source_leaf_summary",
            "info_class": "relative",
            "generated_by": "LLM:fake:night_summarize_source_leaf",
            "payload_json": json.dumps(
                {
                    "data_kind": "source_leaf_summary",
                    "summary_depth": 1,
                    "summary_status": "ran",
                    "validity_status": "active",
                    "review_status": "not_reviewed",
                    "target_graph_node_id": "graph:raw_source:code_tools",
                    "target_node_kind": "raw_source",
                    "source_leaf_count": 1,
                    "source_summary_count": 0,
                    "source_graph_node_ids": ["graph:raw_source:code_tools"],
                    "source_data_ids": [
                        "graph:raw_source:code_tools",
                        "source_manifest:file:code_tools.py",
                    ],
                    "source_trace_ids": ["trace:summary:active"],
                    "info_class": "relative",
                    "generated_by": "LLM:fake:night_summarize_source_leaf",
                    "summary_text": (
                        "This source leaf summary is copied from an active LLM summary node."
                    ),
                },
                ensure_ascii=False,
            ),
            "target_graph_node_id": "graph:raw_source:code_tools",
            "target_display_name": "Raw Source: code_tools.py",
            "target_node_kind": "raw_source",
        },
        {
            "summary_node_id": "graph:summary:invalidated:old",
            "summary_display_name": "Summary: old source",
            "data_kind": "source_leaf_summary",
            "info_class": "relative",
            "generated_by": "LLM:fake:night_summarize_source_leaf",
            "payload_json": json.dumps(
                {
                    "data_kind": "source_leaf_summary",
                    "summary_depth": 1,
                    "summary_status": "ran",
                    "validity_status": "invalidated_by_source_change",
                    "summary_text": "Old invalidated summary.",
                },
                ensure_ascii=False,
            ),
            "target_graph_node_id": "graph:raw_source:old",
            "target_display_name": "Raw Source: old",
            "target_node_kind": "raw_source",
        },
        {
            "summary_node_id": "graph:summary:failed:empty",
            "summary_display_name": "Summary: failed source",
            "data_kind": "source_leaf_summary",
            "info_class": "relative",
            "generated_by": "LLM:fake:night_summarize_source_leaf",
            "payload_json": json.dumps(
                {
                    "data_kind": "source_leaf_summary",
                    "summary_depth": 1,
                    "summary_status": "failed",
                    "validity_status": "active",
                    "summary_text": "",
                },
                ensure_ascii=False,
            ),
            "target_graph_node_id": "graph:raw_source:failed",
            "target_display_name": "Raw Source: failed",
            "target_node_kind": "raw_source",
        },
    ]


class FakeRLoopVesselDriverFactory:
    def __init__(
        self,
        *,
        entry_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
    ) -> None:
        self.entry_rows = list(entry_rows)
        self.summary_rows = list(summary_rows)
        self.last_driver: FakeRLoopVesselDriver | None = None

    def __call__(self, uri: str, *, auth: object) -> "FakeRLoopVesselDriver":
        self.last_driver = FakeRLoopVesselDriver(
            entry_rows=self.entry_rows,
            summary_rows=self.summary_rows,
        )
        return self.last_driver


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FailingDriverFactory:
    def __call__(self, uri: str, *, auth: object) -> "FailingDriver":
        return FailingDriver()


class FakeRLoopVesselDriver:
    def __init__(
        self,
        *,
        entry_rows: list[dict[str, object]],
        summary_rows: list[dict[str, object]],
    ) -> None:
        self.entry_rows = list(entry_rows)
        self.summary_rows = list(summary_rows)
        self.closed = False

    def session(self, *, database: str) -> "FakeRLoopVesselSession":
        return FakeRLoopVesselSession(self, database=database)

    def close(self) -> None:
        self.closed = True


class FailingDriver:
    def session(self, *, database: str) -> "FailingSession":
        return FailingSession()

    def close(self) -> None:
        pass


class FakeRLoopVesselSession:
    def __init__(self, driver: FakeRLoopVesselDriver, *, database: str) -> None:
        self.driver = driver
        self.database = database

    def __enter__(self) -> "FakeRLoopVesselSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, fn, *args):
        return fn(FakeRLoopVesselTransaction(self.driver), *args)


class FailingSession:
    def __enter__(self) -> "FailingSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, _fn, *_args):
        raise RuntimeError("simulated R packet read failure")


class FakeRLoopVesselTransaction:
    def __init__(self, driver: FakeRLoopVesselDriver) -> None:
        self.driver = driver

    def run(self, query: str, **kwargs):
        compact = " ".join(query.split())
        if "entry.data_id AS candidate_node_id" in compact:
            return FakeResult(self.driver.entry_rows)
        if "MATCH (summary:SummaryGraphNode" in compact:
            return FakeResult(self.driver.summary_rows)
        return FakeResult([])


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)
