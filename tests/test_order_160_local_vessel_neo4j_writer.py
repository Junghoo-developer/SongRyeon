from __future__ import annotations

from dataclasses import asdict

import pytest

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_memory import record_graph_memory_for_capsules
from songryeon_core.core.graph_memory_export import record_graph_memory_export_packet
from songryeon_core.core.graph_vessel_adapter import record_graph_vessel_write_plan
from songryeon_core.core.graph_vessel_neo4j import (
    GRAPH_VESSEL_NEO4J_WRITE_RESULT_DATA_TYPE,
    GRAPH_VESSEL_NEO4J_WRITER_GENERATOR,
    GraphVesselNeo4jConfig,
    record_graph_vessel_neo4j_write_result,
    write_graph_vessel_plan_to_neo4j,
)
from songryeon_core.core.schemas import NodeMovement, TurnStateCapsule
from songryeon_core.core.trace_store import TraceStore


EXPORTED_AT = "2026-07-01T20:00:00"
PLANNED_AT = "2026-07-01T20:00:01"
WRITTEN_AT = "2026-07-01T20:00:02"


def test_neo4j_writer_writes_ready_plan_with_fake_driver() -> None:
    trace_store, data_store, plan_id = _store_with_write_plan()
    fake_driver_factory = FakeNeo4jDriverFactory()

    result = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=fake_driver_factory,
    )

    frame = result.result
    plan_payload = data_store.require_record(plan_id).payload
    assert frame.generated_by == GRAPH_VESSEL_NEO4J_WRITER_GENERATOR
    assert frame.info_class == "absolute"
    assert frame.semantic_judgement_status == "not_run"
    assert frame.write_status == "written"
    assert frame.external_write_status == "written"
    assert frame.failure_type is None
    assert frame.attempted_operation_count == plan_payload["operation_count"]
    assert frame.written_operation_count == plan_payload["operation_count"]
    assert frame.neo4j_record_node_count is not None
    assert frame.neo4j_graph_edge_count is not None
    assert fake_driver_factory.last_driver is not None
    assert fake_driver_factory.last_driver.closed is True

    record = data_store.require_record(frame.result_id)
    assert record.data_type == GRAPH_VESSEL_NEO4J_WRITE_RESULT_DATA_TYPE
    assert record.payload["write_status"] == "written"
    assert result.created_data_ids == [frame.result_id]


def test_neo4j_writer_missing_password_is_adapter_unavailable_without_driver_call() -> None:
    _, data_store, plan_id = _store_with_write_plan()
    fake_driver_factory = RaisingDriverFactory()

    result = write_graph_vessel_plan_to_neo4j(
        data_store=data_store,
        plan_id=plan_id,
        config=_config(password=None),
        created_at=WRITTEN_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.write_status == "adapter_unavailable"
    assert result.failure_type == "neo4j_config_missing"
    assert result.external_write_status == "not_run"
    assert result.attempted_operation_count == 0
    assert fake_driver_factory.called is False


def test_neo4j_writer_allow_no_auth_passes_auth_none() -> None:
    _, data_store, plan_id = _store_with_write_plan()
    fake_driver_factory = FakeNeo4jDriverFactory()

    result = write_graph_vessel_plan_to_neo4j(
        data_store=data_store,
        plan_id=plan_id,
        config=_config(password=None, allow_no_auth=True),
        created_at=WRITTEN_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.write_status == "written"
    assert fake_driver_factory.calls[0]["auth"] is None


def test_neo4j_writer_blocks_not_ready_plan() -> None:
    trace_store = TraceStore()
    data_store = DataStore()
    data_store.create_record(
        data_id="graph:edge:contains:graph:missing_parent:graph:missing_child",
        data_type="graph_memory:edge:CONTAINS",
        payload={
            "edge_id": "graph:edge:contains:graph:missing_parent:graph:missing_child",
            "edge_kind": "CONTAINS",
            "from_node_id": "graph:missing_parent",
            "to_node_id": "graph:missing_child",
            "source_data_ids": ["graph:missing_parent", "graph:missing_child"],
        },
    )
    export = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        batch_id="batch_order_160_failed_integrity",
        created_at=EXPORTED_AT,
    )
    plan = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        export_packet_id=export.packet.packet_id,
        created_at=PLANNED_AT,
    )

    result = write_graph_vessel_plan_to_neo4j(
        data_store=data_store,
        plan_id=plan.plan.plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=RaisingDriverFactory(),
    )

    assert result.write_status == "blocked_plan_not_ready"
    assert result.failure_type == "plan_status_not_ready"
    assert result.attempted_operation_count == 0
    assert result.external_write_status == "not_run"


def test_neo4j_writer_records_write_failure() -> None:
    _, data_store, plan_id = _store_with_write_plan()

    result = write_graph_vessel_plan_to_neo4j(
        data_store=data_store,
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=FailingNeo4jDriverFactory(),
    )

    assert result.write_status == "write_failed"
    assert result.failure_type == "neo4j_write_failed"
    assert result.external_write_status == "not_run"
    assert result.attempted_operation_count > 0
    assert result.written_operation_count == 0


def test_neo4j_writer_does_not_create_semantic_fields() -> None:
    trace_store, data_store, plan_id = _store_with_write_plan()

    result = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=FakeNeo4jDriverFactory(),
    )

    payload = data_store.require_record(result.result.result_id).payload
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
    assert payload["generated_by"] == GRAPH_VESSEL_NEO4J_WRITER_GENERATOR
    assert payload["info_class"] == "absolute"
    assert payload["semantic_judgement_status"] == "not_run"


def test_neo4j_writer_uses_human_readable_display_vocabulary() -> None:
    trace_store, data_store, plan_id = _store_with_write_plan()
    fake_driver_factory = FakeNeo4jDriverFactory()

    result = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_161",
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=fake_driver_factory,
    )

    assert result.result.write_status == "written"
    assert fake_driver_factory.last_driver is not None
    queries = "\n".join(query for query, _kwargs in fake_driver_factory.last_driver.queries)
    assert "SET n:VesselRecord" in queries
    assert "REMOVE n:SongRyeonRecord" in queries
    assert ":CoreEgo" in queries
    assert ":TimeAxis" in queries
    assert ":TimeBundle" in queries
    assert ":RawCapsule" in queries
    assert "r:HAS_AXIS" in queries
    assert "r:HAS_BUNDLE" in queries
    assert "r:CONTAINS_MEMORY" in queries

    property_sets = [
        kwargs["properties"]
        for _query, kwargs in fake_driver_factory.last_driver.queries
        if isinstance(kwargs.get("properties"), dict)
    ]
    assert any(item.get("display_name") == "CoreEgo" for item in property_sets)
    assert any(item.get("display_label") == "RawCapsule" for item in property_sets)
    assert any(
        item.get("display_relationship_type") == "HAS_AXIS"
        for item in property_sets
    )


def test_neo4j_write_result_is_idempotent_for_same_plan_and_timestamp() -> None:
    trace_store, data_store, plan_id = _store_with_write_plan()

    first = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=FakeNeo4jDriverFactory(),
    )
    second = record_graph_vessel_neo4j_write_result(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160",
        plan_id=plan_id,
        config=_config(),
        created_at=WRITTEN_AT,
        driver_factory=FakeNeo4jDriverFactory(),
    )

    assert first.created_data_ids == [first.result.result_id]
    assert second.created_data_ids == []
    assert second.existing_data_ids == [first.result.result_id]
    assert asdict(first.result) == asdict(second.result)


def _store_with_write_plan() -> tuple[TraceStore, DataStore, str]:
    trace_store = TraceStore()
    data_store = DataStore()
    record_graph_memory_for_capsules(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160_core",
        batch_id="batch_order_160_core",
        capsules=[_sample_capsule("turn_order_160_previous")],
    )
    export = record_graph_memory_export_packet(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160_export",
        batch_id="batch_order_160_export",
        created_at=EXPORTED_AT,
    )
    plan = record_graph_vessel_write_plan(
        trace_store=trace_store,
        data_store=data_store,
        turn_id="turn_order_160_plan",
        export_packet_id=export.packet.packet_id,
        created_at=PLANNED_AT,
    )
    return trace_store, data_store, plan.plan.plan_id


def _sample_capsule(turn_id: str) -> TurnStateCapsule:
    return TurnStateCapsule(
        turn_id=turn_id,
        node_movements=[
            NodeMovement(
                movement_id=f"move:{turn_id}:001",
                turn_id=turn_id,
                step_index=1,
                node_id="node_0",
                mode="pre_route_report",
                input_trace_ids=[f"trace:{turn_id}:user"],
                output_trace_ids=[f"trace:{turn_id}:node0"],
                status="completed",
            )
        ],
        trace_event_ids=[
            f"trace:{turn_id}:user",
            f"trace:{turn_id}:node0",
            f"trace:{turn_id}:final",
        ],
        user_input_trace_id=f"trace:{turn_id}:user",
        final_response_trace_id=f"trace:{turn_id}:final",
    )


def _config(
    *,
    password: str | None = "test-password",
    allow_no_auth: bool = False,
) -> GraphVesselNeo4jConfig:
    return GraphVesselNeo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password=password,
        database="songryeon_vessel",
        allow_no_auth=allow_no_auth,
    )


class FakeNeo4jDriverFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.last_driver: FakeNeo4jDriver | None = None

    def __call__(self, uri: str, *, auth: object) -> "FakeNeo4jDriver":
        self.calls.append({"uri": uri, "auth": auth})
        self.last_driver = FakeNeo4jDriver()
        return self.last_driver


class RaisingDriverFactory:
    def __init__(self) -> None:
        self.called = False

    def __call__(self, *_args, **_kwargs) -> object:
        self.called = True
        raise AssertionError("driver factory should not be called")


class FailingNeo4jDriverFactory:
    def __call__(self, uri: str, *, auth: object) -> "FailingNeo4jDriver":
        return FailingNeo4jDriver()


class FakeNeo4jDriver:
    def __init__(self) -> None:
        self.record_node_ids: set[str] = set()
        self.edge_ids: set[str] = set()
        self.queries: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def session(self, *, database: str) -> "FakeNeo4jSession":
        return FakeNeo4jSession(self, database=database)

    def close(self) -> None:
        self.closed = True


class FailingNeo4jDriver:
    def session(self, *, database: str) -> "FailingNeo4jSession":
        return FailingNeo4jSession()

    def close(self) -> None:
        pass


class FakeNeo4jSession:
    def __init__(self, driver: FakeNeo4jDriver, *, database: str) -> None:
        self.driver = driver
        self.database = database

    def __enter__(self) -> "FakeNeo4jSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_write(self, fn, *args):
        return fn(FakeNeo4jTransaction(self.driver), *args)

    def execute_read(self, fn, *args):
        return fn(FakeNeo4jTransaction(self.driver), *args)


class FailingNeo4jSession:
    def __enter__(self) -> "FailingNeo4jSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        return None

    def execute_write(self, _fn, *_args):
        raise RuntimeError("simulated write failure")


class FakeNeo4jTransaction:
    def __init__(self, driver: FakeNeo4jDriver) -> None:
        self.driver = driver

    def run(self, query: str, **kwargs):
        self.driver.queries.append((query, kwargs))
        if "RETURN count(n) AS count" in query:
            return FakeNeo4jResult(len(self.driver.record_node_ids))
        if "RETURN count(r) AS count" in query:
            return FakeNeo4jResult(len(self.driver.edge_ids))
        data_id = kwargs.get("data_id")
        if isinstance(data_id, str):
            self.driver.record_node_ids.add(data_id)
        edge_id = kwargs.get("edge_id")
        if isinstance(edge_id, str) and "SONGRYEON_GRAPH_EDGE" in query:
            self.driver.edge_ids.add(edge_id)
        return FakeNeo4jResult(0)


class FakeNeo4jResult:
    def __init__(self, count: int) -> None:
        self.count = count

    def single(self):
        return {"count": self.count}
