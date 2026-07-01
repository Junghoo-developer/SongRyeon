from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_inspect import (
    GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR,
    GRAPH_VESSEL_NEO4J_INSPECT_RESULT_DATA_TYPE,
    inspect_graph_vessel_from_neo4j,
    record_graph_vessel_neo4j_inspect_result,
)
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.runtime.graph_vessel_inspect import render_vessel_inspect_text


INSPECTED_AT = "2026-07-01T22:00:00"


def test_vessel_inspect_returns_manual_walk_tree() -> None:
    fake_driver_factory = FakeInspectDriverFactory()

    result = inspect_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_163_tree",
        created_at=INSPECTED_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.generated_by == GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR
    assert result.info_class == "absolute"
    assert result.semantic_judgement_status == "not_run"
    assert result.inspect_status == "passed"
    assert result.inspected_path_count == 1
    assert result.core_count == 1
    assert result.time_axis_count == 1
    assert result.time_bundle_count == 1
    assert result.raw_capsule_count == 1
    assert result.tree_lines == [
        "CoreEgo [graph:core_ego:root]",
        "  HAS_AXIS -> Time Axis [graph:axis:time]",
        "    HAS_BUNDLE -> Time Bundle [graph:time_bundle:manual_vessel_first_write:core]",
        "      CONTAINS_MEMORY -> Raw Capsule: turn_vessel_first_write_0001:previous [graph:raw_capsule:turn_vessel_first_write_0001:previous]",
    ]
    assert result.source_data_ids == [
        "graph:core_ego:root",
        "graph:axis:time",
        "graph:time_bundle:manual_vessel_first_write:core",
        "graph:raw_capsule:turn_vessel_first_write_0001:previous",
    ]
    assert result.source_trace_ids == ["trace:turn_vessel_first_write_0001:previous:final"]
    assert fake_driver_factory.last_driver is not None
    assert fake_driver_factory.last_driver.closed is True


def test_vessel_inspect_records_result_in_datastore() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_neo4j_inspect_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_163",
        batch_id="order_163_record",
        config=_config(),
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(),
    )

    record = data_store.require_record(recorded.result.result_id)
    assert record.data_type == GRAPH_VESSEL_NEO4J_INSPECT_RESULT_DATA_TYPE
    assert record.payload["inspect_status"] == "passed"
    assert record.payload["tree_lines"][0] == "CoreEgo [graph:core_ego:root]"
    assert recorded.created_data_ids == [recorded.result.result_id]
    assert trace_store.list_events()[0].actor == "graph_vessel_neo4j_inspector"


def test_vessel_inspect_empty_when_core_axis_path_missing() -> None:
    result = inspect_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_163_empty",
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(path_rows=[]),
    )

    assert result.inspect_status == "empty"
    assert result.failure_type == "no_inspectable_path"
    assert result.inspected_path_count == 0
    assert result.tree_lines == []


def test_vessel_inspect_missing_password_does_not_call_driver() -> None:
    fake_driver_factory = RaisingDriverFactory()

    result = inspect_graph_vessel_from_neo4j(
        config=_config(password=None),
        batch_id="order_163_missing_password",
        created_at=INSPECTED_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.inspect_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert result.path_items == []
    assert fake_driver_factory.called is False


def test_vessel_inspect_records_driver_exception() -> None:
    result = inspect_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_163_read_failed",
        created_at=INSPECTED_AT,
        driver_factory=FailingInspectDriverFactory(),
    )

    assert result.inspect_status == "read_failed"
    assert result.failure_type == "neo4j_read_failed"
    assert "simulated inspect failure" in (result.failure_reason or "")


def test_vessel_inspect_text_renderer_uses_tree_lines() -> None:
    result = {
        "status": "VESSEL_INSPECT_OK",
        "inspect_status": "passed",
        "failure_type": None,
        "failure_reason": None,
        "graph_namespace": "songryeon_core_graph_v0",
        "inspected_path_count": 1,
        "tree_text": "CoreEgo [graph:core_ego:root]",
    }

    rendered = render_vessel_inspect_text(result)

    assert "status: VESSEL_INSPECT_OK" in rendered
    assert "inspect_status: passed" in rendered
    assert "CoreEgo [graph:core_ego:root]" in rendered


def test_vessel_inspect_does_not_create_semantic_fields() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_neo4j_inspect_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_163",
        batch_id="order_163_no_semantic",
        config=_config(),
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(),
    )

    payload = data_store.require_record(recorded.result.result_id).payload
    for forbidden_field in (
        "summary",
        "semantic_topic",
        "topic_label",
        "importance_score",
        "relevance_reason",
        "meaning_cluster",
        "embedding_id",
    ):
        assert forbidden_field not in payload
    assert payload["generated_by"] == GRAPH_VESSEL_NEO4J_INSPECT_GENERATOR
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"


def test_vessel_inspect_result_is_idempotent_for_same_batch_and_timestamp() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    first = record_graph_vessel_neo4j_inspect_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_163",
        batch_id="order_163_idempotent",
        config=_config(),
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(),
    )
    second = record_graph_vessel_neo4j_inspect_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_163",
        batch_id="order_163_idempotent",
        config=_config(),
        created_at=INSPECTED_AT,
        driver_factory=FakeInspectDriverFactory(),
    )

    assert first.created_data_ids == [first.result.result_id]
    assert second.created_data_ids == []
    assert second.existing_data_ids == [first.result.result_id]
    assert asdict(first.result) == asdict(second.result)


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


def _default_path_rows() -> list[dict[str, object]]:
    return [
        {
            "core_data_id": "graph:core_ego:root",
            "core_display_name": "CoreEgo",
            "axis_data_id": "graph:axis:time",
            "axis_display_name": "Time Axis",
            "bundle_data_id": "graph:time_bundle:manual_vessel_first_write:core",
            "bundle_display_name": "Time Bundle",
            "bundle_created_at": "2026-07-01T18:39:54",
            "bundle_written_at": "2026-07-01T18:39:54",
            "raw_capsule_data_id": "graph:raw_capsule:turn_vessel_first_write_0001:previous",
            "raw_capsule_display_name": "Raw Capsule: turn_vessel_first_write_0001:previous",
            "raw_capsule_created_at": "2026-07-01T18:39:54",
            "raw_capsule_written_at": "2026-07-01T18:39:54",
            "raw_capsule_source_trace_id": "trace:turn_vessel_first_write_0001:previous:final",
        }
    ]


class FakeInspectDriverFactory:
    def __init__(
        self,
        *,
        counts: dict[str, int] | None = None,
        path_rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.counts = {
            "core_count": 1,
            "time_axis_count": 1,
            "time_bundle_count": 1,
            "raw_capsule_count": 1,
        }
        self.counts.update(counts or {})
        self.path_rows = _default_path_rows() if path_rows is None else list(path_rows)
        self.calls: list[dict[str, object]] = []
        self.last_driver: FakeInspectDriver | None = None

    def __call__(self, uri: str, *, auth: object) -> "FakeInspectDriver":
        self.calls.append({"uri": uri, "auth": auth})
        self.last_driver = FakeInspectDriver(
            counts=self.counts,
            path_rows=self.path_rows,
        )
        return self.last_driver


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FailingInspectDriverFactory:
    def __call__(self, uri: str, *, auth: object) -> "FailingInspectDriver":
        return FailingInspectDriver()


class FakeInspectDriver:
    def __init__(
        self,
        *,
        counts: dict[str, int],
        path_rows: list[dict[str, object]],
    ) -> None:
        self.counts = dict(counts)
        self.path_rows = list(path_rows)
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def session(self, *, database: str) -> "FakeInspectSession":
        return FakeInspectSession(self, database=database)

    def close(self) -> None:
        self.closed = True


class FailingInspectDriver:
    def session(self, *, database: str) -> "FailingInspectSession":
        return FailingInspectSession()

    def close(self) -> None:
        pass


class FakeInspectSession:
    def __init__(self, driver: FakeInspectDriver, *, database: str) -> None:
        self.driver = driver
        self.database = database

    def __enter__(self) -> "FakeInspectSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, fn, *args):
        return fn(FakeInspectTransaction(self.driver), *args)


class FailingInspectSession:
    def __enter__(self) -> "FailingInspectSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, _fn, *_args):
        raise RuntimeError("simulated inspect failure")


class FakeInspectTransaction:
    def __init__(self, driver: FakeInspectDriver) -> None:
        self.driver = driver

    def run(self, query: str, **kwargs):
        self.driver.queries.append((query, kwargs))
        compact = " ".join(query.split())
        if "RETURN core.data_id AS core_data_id" in compact:
            return FakePathResult(self.driver.path_rows)
        if "MATCH (n:CoreEgo" in compact:
            return FakeCountResult(self.driver.counts["core_count"])
        if "MATCH (n:TimeAxis" in compact:
            return FakeCountResult(self.driver.counts["time_axis_count"])
        if "MATCH (n:TimeBundle" in compact:
            return FakeCountResult(self.driver.counts["time_bundle_count"])
        if "MATCH (n:RawCapsule" in compact:
            return FakeCountResult(self.driver.counts["raw_capsule_count"])
        return FakeCountResult(0)


class FakeCountResult:
    def __init__(self, count: int) -> None:
        self.count = count

    def single(self):
        return {"count": self.count}


class FakePathResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)
