from __future__ import annotations

from dataclasses import asdict

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    NodeMovement,
    TaskFrame,
    TaskResultFrame,
    validate_task_frame,
    validate_task_result_frame,
)
from songryeon_core.core.trace_store import TraceStore


TASK_FRAME_DATA_TYPE = "task_ledger:task_frame"
TASK_RESULT_DATA_TYPE = "task_ledger:task_result_frame"


def record_task_ledger_from_movements(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    movements: list[NodeMovement],
    assigned_model_by_node: dict[str, str] | None = None,
) -> tuple[str, list[str]]:
    """현재 순차 노드 동선을 task 장부로 복사해 기록한다.

    Task Ledger v0은 실행 순서를 바꾸지 않는다. 이미 끝난 NodeMovement를
    task/task_result record로 남겨서 나중에 scheduler와 worker를 붙일 수
    있는 장부 표면을 만드는 단계다.
    """

    if not movements:
        event = trace_store.create_event(
            turn_id=turn_id,
            actor="scheduler",
            event_type="task_ledger_commit",
            schema_status="passed",
        )
        return event.event_id, []

    task_frames: list[TaskFrame] = []
    task_results: list[TaskResultFrame] = []
    output_refs: list[str] = []
    previous_task_id: str | None = None
    model_by_node = assigned_model_by_node or {}

    for index, movement in enumerate(movements, start=1):
        task_id = f"task:{turn_id}:{index:03d}"
        result_id = f"task_result:{turn_id}:{index:03d}"
        output_refs.extend([task_id, result_id])

        # v0에서는 실제 실행 순서를 바꾸지 않고, 직전 task에만 의존하는 순차 장부로 남긴다.
        frame = TaskFrame(
            task_id=task_id,
            turn_id=turn_id,
            step_index=index,
            node_id=movement.node_id,
            task_kind=movement.node_type,
            mode=movement.mode,
            depends_on_task_ids=[previous_task_id] if previous_task_id else [],
            input_trace_ids=list(movement.input_trace_ids),
            input_data_ids=list(movement.input_data_ids),
            expected_output_trace_ids=list(movement.output_trace_ids),
            expected_output_data_ids=list(movement.output_data_ids),
            assigned_model_id=_assigned_model_for_movement(movement, model_by_node),
            assigned_worker_id="local_sync_worker",
            scheduling_policy="sequential_v0",
            status=movement.status,
        )
        validate_task_frame(frame)
        task_frames.append(frame)

        result = TaskResultFrame(
            result_id=result_id,
            task_id=task_id,
            turn_id=turn_id,
            status=_result_status_from_movement(movement),
            output_trace_ids=list(movement.output_trace_ids),
            output_data_ids=list(movement.output_data_ids),
            failure_type=None if movement.status == "completed" else movement.status,
            failure_reason=None if movement.status == "completed" else "movement_status_not_completed",
        )
        validate_task_result_frame(result)
        task_results.append(result)

        previous_task_id = task_id

    input_refs = _unique_strings(
        [
            trace_id
            for movement in movements
            for trace_id in [*movement.input_trace_ids, *movement.output_trace_ids]
        ]
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="scheduler",
        event_type="task_ledger_commit",
        input_ref=input_refs,
        output_ref=output_refs,
        schema_status="passed",
    )

    for frame, result in zip(task_frames, task_results, strict=True):
        data_store.create_record(
            data_id=frame.task_id,
            data_type=TASK_FRAME_DATA_TYPE,
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
        data_store.create_record(
            data_id=result.result_id,
            data_type=TASK_RESULT_DATA_TYPE,
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(result),
        )

    return event.event_id, output_refs


def task_ledger_counts(data_store: DataStore) -> dict[str, int]:
    """DataStore 안의 task ledger record 수를 센다."""

    frame_count = 0
    result_count = 0
    for record in data_store.list_records():
        if record.data_type == TASK_FRAME_DATA_TYPE:
            frame_count += 1
        elif record.data_type == TASK_RESULT_DATA_TYPE:
            result_count += 1
    return {"task_frame_count": frame_count, "task_result_count": result_count}


def _assigned_model_for_movement(
    movement: NodeMovement,
    assigned_model_by_node: dict[str, str],
) -> str:
    if movement.node_id in assigned_model_by_node:
        return assigned_model_by_node[movement.node_id]
    if movement.node_id == "node_0":
        return "CODE:RULE_STUB"
    return "CODE/LOCAL_RUNTIME"


def _result_status_from_movement(movement: NodeMovement) -> str:
    if movement.status in {"completed", "failed", "skipped"}:
        return movement.status
    return "completed" if movement.status == "started" else "failed"


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
