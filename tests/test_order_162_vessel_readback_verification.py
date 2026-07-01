from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_vessel_neo4j import GraphVesselNeo4jConfig
from songryeon_core.core.graph_vessel_readback import (
    GRAPH_VESSEL_NEO4J_READBACK_GENERATOR,
    GRAPH_VESSEL_NEO4J_READBACK_RESULT_DATA_TYPE,
    readback_graph_vessel_from_neo4j,
    record_graph_vessel_neo4j_readback_result,
)
from songryeon_core.core.trace_store import TraceStore


READ_AT = "2026-07-01T21:00:00"


def test_vessel_readback_passes_when_core_path_exists() -> None:
    fake_driver_factory = FakeNeo4jReadbackDriverFactory()

    result = readback_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_162_pass",
        created_at=READ_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.generated_by == GRAPH_VESSEL_NEO4J_READBACK_GENERATOR
    assert result.info_class == "absolute"
    assert result.semantic_judgement_status == "not_run"
    assert result.readback_status == "passed"
    assert result.failure_type is None
    assert result.core_path_exists is True
    assert result.core_path_count == 1
    assert result.vessel_record_count == 10
    assert result.vessel_relationship_count == 3
    assert result.core_ego_count == 1
    assert result.time_axis_count == 1
    assert result.time_bundle_count == 1
    assert result.raw_capsule_count == 1
    assert result.has_axis_count == 1
    assert result.has_bundle_count == 1
    assert result.contains_memory_count == 1
    assert result.required_property_missing_count == 0
    assert fake_driver_factory.last_driver is not None
    assert fake_driver_factory.last_driver.closed is True


def test_vessel_readback_records_result_in_datastore() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_neo4j_readback_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_162",
        batch_id="order_162_record",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeNeo4jReadbackDriverFactory(),
    )

    record = data_store.require_record(recorded.result.result_id)
    assert record.data_type == GRAPH_VESSEL_NEO4J_READBACK_RESULT_DATA_TYPE
    assert record.payload["readback_status"] == "passed"
    assert record.payload["core_path_exists"] is True
    assert recorded.created_data_ids == [recorded.result.result_id]
    assert trace_store.list_events()[0].actor == "graph_vessel_neo4j_readback"


def test_vessel_readback_missing_password_does_not_call_driver() -> None:
    fake_driver_factory = RaisingDriverFactory()

    result = readback_graph_vessel_from_neo4j(
        config=_config(password=None),
        batch_id="order_162_missing_password",
        created_at=READ_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.readback_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert result.core_path_count is None
    assert fake_driver_factory.called is False


def test_vessel_readback_fails_when_core_path_is_missing() -> None:
    fake_driver_factory = FakeNeo4jReadbackDriverFactory(
        counts={"core_path_count": 0}
    )

    result = readback_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_162_missing_path",
        created_at=READ_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.readback_status == "failed"
    assert result.failure_type == "readback_check_failed"
    assert result.core_path_exists is False
    assert "path was not found" in (result.failure_reason or "")


def test_vessel_readback_fails_when_required_properties_are_missing() -> None:
    fake_driver_factory = FakeNeo4jReadbackDriverFactory(
        counts={"required_property_missing_count": 2},
        missing_samples=["graph:bad:001", "<missing-data-id>"],
    )

    result = readback_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_162_missing_properties",
        created_at=READ_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.readback_status == "failed"
    assert result.failure_type == "readback_check_failed"
    assert result.required_property_missing_count == 2
    assert result.required_property_missing_samples == ["graph:bad:001", "<missing-data-id>"]


def test_vessel_readback_records_driver_exception() -> None:
    result = readback_graph_vessel_from_neo4j(
        config=_config(),
        batch_id="order_162_read_failed",
        created_at=READ_AT,
        driver_factory=FailingReadbackDriverFactory(),
    )

    assert result.readback_status == "read_failed"
    assert result.failure_type == "neo4j_read_failed"
    assert "simulated read failure" in (result.failure_reason or "")


def test_vessel_readback_does_not_create_semantic_fields() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    recorded = record_graph_vessel_neo4j_readback_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_162",
        batch_id="order_162_no_semantic",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeNeo4jReadbackDriverFactory(),
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
    assert payload["generated_by"] == GRAPH_VESSEL_NEO4J_READBACK_GENERATOR
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"


def test_vessel_readback_result_is_idempotent_for_same_batch_and_timestamp() -> None:
    trace_store = TraceStore()
    data_store = DataStore()

    first = record_graph_vessel_neo4j_readback_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_162",
        batch_id="order_162_idempotent",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeNeo4jReadbackDriverFactory(),
    )
    second = record_graph_vessel_neo4j_readback_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_162",
        batch_id="order_162_idempotent",
        config=_config(),
        created_at=READ_AT,
        driver_factory=FakeNeo4jReadbackDriverFactory(),
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


class FakeNeo4jReadbackDriverFactory:
    def __init__(
        self,
        *,
        counts: dict[str, int] | None = None,
        missing_samples: list[str] | None = None,
    ) -> None:
        self.counts = {
            "core_path_count": 1,
            "vessel_record_count": 10,
            "vessel_relationship_count": 3,
            "core_ego_count": 1,
            "time_axis_count": 1,
            "time_bundle_count": 1,
            "raw_capsule_count": 1,
            "has_axis_count": 1,
            "has_bundle_count": 1,
            "contains_memory_count": 1,
            "required_property_missing_count": 0,
        }
        self.counts.update(counts or {})
        self.missing_samples = list(missing_samples or [])
        self.calls: list[dict[str, object]] = []
        self.last_driver: FakeNeo4jReadbackDriver | None = None

    def __call__(self, uri: str, *, auth: object) -> "FakeNeo4jReadbackDriver":
        self.calls.append({"uri": uri, "auth": auth})
        self.last_driver = FakeNeo4jReadbackDriver(
            counts=self.counts,
            missing_samples=self.missing_samples,
        )
        return self.last_driver


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FailingReadbackDriverFactory:
    def __call__(self, uri: str, *, auth: object) -> "FailingReadbackDriver":
        return FailingReadbackDriver()


class FakeNeo4jReadbackDriver:
    def __init__(
        self,
        *,
        counts: dict[str, int],
        missing_samples: list[str],
    ) -> None:
        self.counts = dict(counts)
        self.missing_samples = list(missing_samples)
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def session(self, *, database: str) -> "FakeNeo4jReadbackSession":
        return FakeNeo4jReadbackSession(self, database=database)

    def close(self) -> None:
        self.closed = True


class FailingReadbackDriver:
    def session(self, *, database: str) -> "FailingReadbackSession":
        return FailingReadbackSession()

    def close(self) -> None:
        pass


class FakeNeo4jReadbackSession:
    def __init__(self, driver: FakeNeo4jReadbackDriver, *, database: str) -> None:
        self.driver = driver
        self.database = database

    def __enter__(self) -> "FakeNeo4jReadbackSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, fn, *args):
        return fn(FakeNeo4jReadbackTransaction(self.driver), *args)


class FailingReadbackSession:
    def __enter__(self) -> "FailingReadbackSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_read(self, _fn, *_args):
        raise RuntimeError("simulated read failure")


class FakeNeo4jReadbackTransaction:
    def __init__(self, driver: FakeNeo4jReadbackDriver) -> None:
        self.driver = driver

    def run(self, query: str, **kwargs):
        self.driver.queries.append((query, kwargs))
        compact = " ".join(query.split())
        if "collect(coalesce(n.data_id" in compact:
            return FakeNeo4jSamplesResult(self.driver.missing_samples)
        if "CoreEgo" in compact and "HAS_AXIS" in compact and "CONTAINS_MEMORY" in compact:
            return FakeNeo4jCountResult(self.driver.counts["core_path_count"])
        if "WHERE n.data_id IS NULL" in compact:
            return FakeNeo4jCountResult(self.driver.counts["required_property_missing_count"])
        if "MATCH (n:VesselRecord" in compact and "RETURN count(n) AS count" in compact:
            return FakeNeo4jCountResult(self.driver.counts["vessel_record_count"])
        if "MATCH (n:CoreEgo" in compact:
            return FakeNeo4jCountResult(self.driver.counts["core_ego_count"])
        if "MATCH (n:TimeAxis" in compact:
            return FakeNeo4jCountResult(self.driver.counts["time_axis_count"])
        if "MATCH (n:TimeBundle" in compact:
            return FakeNeo4jCountResult(self.driver.counts["time_bundle_count"])
        if "MATCH (n:RawCapsule" in compact:
            return FakeNeo4jCountResult(self.driver.counts["raw_capsule_count"])
        if "MATCH ()-[r:HAS_AXIS" in compact:
            return FakeNeo4jCountResult(self.driver.counts["has_axis_count"])
        if "MATCH ()-[r:HAS_BUNDLE" in compact:
            return FakeNeo4jCountResult(self.driver.counts["has_bundle_count"])
        if "MATCH ()-[r:CONTAINS_MEMORY" in compact:
            return FakeNeo4jCountResult(self.driver.counts["contains_memory_count"])
        if "WHERE r.display_relationship_type IS NOT NULL" in compact:
            return FakeNeo4jCountResult(self.driver.counts["vessel_relationship_count"])
        return FakeNeo4jCountResult(0)


class FakeNeo4jCountResult:
    def __init__(self, count: int) -> None:
        self.count = count

    def single(self):
        return {"count": self.count}


class FakeNeo4jSamplesResult:
    def __init__(self, samples: list[str]) -> None:
        self.samples = samples

    def single(self):
        return {"samples": list(self.samples)}
