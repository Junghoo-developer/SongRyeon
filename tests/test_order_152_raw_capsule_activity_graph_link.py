from __future__ import annotations

import pytest

from songryeon_core.core.schemas import (
    TurnActivityGraphLinkFrame,
    validate_turn_activity_graph_link_frame,
)
from songryeon_core.core.turn_activity_graph_links import (
    TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE,
    activity_ledger_graph_edge_id,
    activity_ledger_graph_node_id,
    turn_activity_graph_link_frame_id,
)
from songryeon_core.runtime.dry_run import run_dry_turn


def test_raw_capsule_links_to_l_activity_ledger() -> None:
    result = run_dry_turn()
    records = _records_by_id(result)
    link_record = records[turn_activity_graph_link_frame_id("turn_dry_001")]
    link = link_record["payload"]
    l_node_id = activity_ledger_graph_node_id("L:activity_ledger_frame")
    edge_id = activity_ledger_graph_edge_id(
        raw_capsule_node_id="graph:raw_capsule:turn_dry_001",
        activity_node_id=l_node_id,
    )

    assert link_record["data_type"] == TURN_ACTIVITY_GRAPH_LINK_DATA_TYPE
    assert link["generated_by"] == "CODE:TURN_ACTIVITY_GRAPH_LINK_BUILDER"
    assert link["info_class"] == "absolute"
    assert link["semantic_judgement_status"] == "not_run"
    assert link["turn_capsule_graph_node_id"] == "graph:raw_capsule:turn_dry_001"
    assert link["l_loop_activity_ledger_data_ids"] == ["L:activity_ledger_frame"]
    assert link["r_graph_access_ledger_data_ids"] == []
    assert link["activity_ledger_graph_node_ids"] == [l_node_id]
    assert link["activity_ledger_graph_edge_ids"] == [edge_id]
    assert link["link_records"] == [
        {
            "activity_kind": "l_loop_activity_ledger",
            "ledger_data_id": "L:activity_ledger_frame",
            "graph_node_id": l_node_id,
            "edge_id": edge_id,
            "source_field": "l_loop_activity_ledger_data_ids",
        }
    ]

    node = records[l_node_id]["payload"]
    assert node["node_kind"] == "activity_ledger"
    assert node["data_kind"] == "l_loop_activity_ledger"
    assert node["source_graph_node_ids"] == ["graph:raw_capsule:turn_dry_001"]
    assert node["source_data_ids"] == ["L:activity_ledger_frame"]

    edge = records[edge_id]["payload"]
    assert edge["edge_kind"] == "HAS_ACTIVITY_LEDGER"
    assert edge["from_node_id"] == "graph:raw_capsule:turn_dry_001"
    assert edge["to_node_id"] == l_node_id
    assert "L:activity_ledger_frame" in edge["source_data_ids"]


def test_raw_capsule_links_to_r_access_ledger_when_r_dry_run_runs() -> None:
    result = run_dry_turn(enable_r_route_dry_run=True)
    records = _records_by_id(result)
    link = records[turn_activity_graph_link_frame_id("turn_dry_001")]["payload"]
    r_ledger_id = "R:dry_run:turn_graph_access_ledger_frame"
    r_node_id = activity_ledger_graph_node_id(r_ledger_id)
    r_edge_id = activity_ledger_graph_edge_id(
        raw_capsule_node_id="graph:raw_capsule:turn_dry_001",
        activity_node_id=r_node_id,
    )

    assert link["l_loop_activity_ledger_data_ids"] == ["L:activity_ledger_frame"]
    assert link["r_graph_access_ledger_data_ids"] == [r_ledger_id]
    assert r_node_id in link["activity_ledger_graph_node_ids"]
    assert r_edge_id in link["activity_ledger_graph_edge_ids"]

    node = records[r_node_id]["payload"]
    assert node["node_kind"] == "activity_ledger"
    assert node["data_kind"] == "r_graph_access_ledger"
    assert node["source_data_ids"] == [r_ledger_id]

    edge = records[r_edge_id]["payload"]
    assert edge["edge_kind"] == "HAS_ACTIVITY_LEDGER"
    assert edge["from_node_id"] == "graph:raw_capsule:turn_dry_001"
    assert edge["to_node_id"] == r_node_id


def test_turn_activity_graph_link_validator_rejects_semantic_status() -> None:
    frame = TurnActivityGraphLinkFrame(
        frame_id="graph:turn_activity_graph_link:turn_test",
        turn_id="turn_test",
        turn_capsule_graph_node_id="graph:raw_capsule:turn_test",
        semantic_judgement_status="ran",
        source_data_ids=["graph:raw_capsule:turn_test"],
    )

    with pytest.raises(ValueError, match="semantic_judgement_status"):
        validate_turn_activity_graph_link_frame(frame)


def _records_by_id(result: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        item["data_id"]: item
        for item in result["data_records"]
        if isinstance(item, dict)
    }
