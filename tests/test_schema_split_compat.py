from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core import schemas
from songryeon_core.core.schema_parts import base, task_ledger, trace_data


def test_schema_parts_reexport_through_compat_layer() -> None:
    assert schemas.DataRef is base.DataRef
    assert schemas.SchemaBinding is base.SchemaBinding
    assert schemas.NodeMovement is base.NodeMovement
    assert schemas.TaskFrame is task_ledger.TaskFrame
    assert schemas.TaskResultFrame is task_ledger.TaskResultFrame
    assert schemas.TraceEvent is trace_data.TraceEvent
    assert schemas.UnifiedState is trace_data.UnifiedState
    assert schemas.TurnStateCapsule is trace_data.TurnStateCapsule
    assert schemas.ZeroState is trace_data.ZeroState
    assert schemas.MemoryPacketFrom0 is trace_data.MemoryPacketFrom0
    assert schemas.RoutingDecision is trace_data.RoutingDecision


def test_schema_parts_dataclass_payload_shape_matches_old_import_path() -> None:
    compat_task = schemas.TaskFrame(
        task_id="task_001",
        turn_id="turn_001",
        step_index=1,
        node_id="node_0",
        task_kind="node",
    )
    direct_task = task_ledger.TaskFrame(
        task_id="task_001",
        turn_id="turn_001",
        step_index=1,
        node_id="node_0",
        task_kind="node",
    )

    assert asdict(compat_task) == asdict(direct_task)
    schemas.validate_task_frame(compat_task)
    task_ledger.validate_task_frame(direct_task)

    compat_event = schemas.TraceEvent(
        event_id="trace_001",
        turn_id="turn_001",
        timestamp="2026-06-27T00:00:00+09:00",
        actor="node_0",
        event_type="node_output",
    )
    direct_event = trace_data.TraceEvent(
        event_id="trace_001",
        turn_id="turn_001",
        timestamp="2026-06-27T00:00:00+09:00",
        actor="node_0",
        event_type="node_output",
    )

    assert asdict(compat_event) == asdict(direct_event)
