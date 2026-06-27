from __future__ import annotations

from dataclasses import dataclass, field

from songryeon_core.core.schema_parts.base import _validate_string_list


TASK_FRAME_SCHEMA_NAME = "TaskFrame"
TASK_FRAME_SCHEMA_VERSION = "0.1"
TASK_RESULT_FRAME_SCHEMA_NAME = "TaskResultFrame"
TASK_RESULT_FRAME_SCHEMA_VERSION = "0.1"


@dataclass
class TaskFrame:
    """스케줄러/큐 구조로 가기 전에 남기는 작업 장부의 최소 task 선언."""

    # task 하나를 구분하는 ID.
    task_id: str
    # 이 task가 속한 턴 ID.
    turn_id: str
    # 현재 순차 런타임에서 몇 번째 task인지 나타내는 순서 번호.
    step_index: int
    # 이 task가 실행한 노드나 루프. 예: node_0, node_1, L.
    node_id: str
    # task의 종류. 예: node, loop, scheduler_stub.
    task_kind: str
    # 실제 실행 모드. 예: routing, report, gatekeeper.
    mode: str | None = None
    # v0에서는 직전 task에만 의존하는 순차 실행으로 기록한다.
    depends_on_task_ids: list[str] = field(default_factory=list)
    # task 입력 trace ID 목록.
    input_trace_ids: list[str] = field(default_factory=list)
    # task 입력 data ID 목록.
    input_data_ids: list[str] = field(default_factory=list)
    # task가 만들 것으로 기록된 trace ID 목록.
    expected_output_trace_ids: list[str] = field(default_factory=list)
    # task가 만들 것으로 기록된 data ID 목록.
    expected_output_data_ids: list[str] = field(default_factory=list)
    # 이 task에 배정된 모델이나 코드 실행자.
    assigned_model_id: str = "CODE"
    # 이 task에 배정된 worker. v0에서는 실제 worker가 아니라 장부용 이름이다.
    assigned_worker_id: str = "local_sync_worker"
    # 현재 task 실행 정책. v0에서는 기존 순차 실행을 task로 장부화한다.
    scheduling_policy: str = "sequential_v0"
    # task frame을 만든 주체.
    created_by: str = "CODE:TASK_LEDGER_V0"
    # task 상태. v0에서는 실행 후 장부화하므로 completed가 기본이다.
    status: str = "completed"
    schema_name: str = TASK_FRAME_SCHEMA_NAME
    schema_version: str = TASK_FRAME_SCHEMA_VERSION


@dataclass
class TaskResultFrame:
    """task 실행 결과를 장부에 남기는 최소 결과 프레임."""

    # result frame 하나를 구분하는 ID.
    result_id: str
    # 대응하는 task ID.
    task_id: str
    # 이 결과가 속한 턴 ID.
    turn_id: str
    # task 실행 결과 상태.
    status: str
    # task가 실제로 만든 trace ID 목록.
    output_trace_ids: list[str] = field(default_factory=list)
    # task가 실제로 만든 data ID 목록.
    output_data_ids: list[str] = field(default_factory=list)
    # 실패 종류. 성공이면 None.
    failure_type: str | None = None
    # 실패 이유. 성공이면 None.
    failure_reason: str | None = None
    # task result를 최종 장부에 반영한 주체.
    committed_by: str = "CODE:TASK_LEDGER_V0"
    schema_name: str = TASK_RESULT_FRAME_SCHEMA_NAME
    schema_version: str = TASK_RESULT_FRAME_SCHEMA_VERSION


def validate_task_frame(frame: TaskFrame) -> None:
    """TaskFrame이 최소 작업 장부 규칙을 지키는지 확인한다."""

    for field_name, value in {
        "task_id": frame.task_id,
        "turn_id": frame.turn_id,
        "node_id": frame.node_id,
        "task_kind": frame.task_kind,
        "assigned_model_id": frame.assigned_model_id,
        "assigned_worker_id": frame.assigned_worker_id,
        "scheduling_policy": frame.scheduling_policy,
        "created_by": frame.created_by,
        "status": frame.status,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"TaskFrame.{field_name} must not be empty")
    if frame.step_index < 1:
        raise ValueError("TaskFrame.step_index must be positive")
    if frame.schema_name != TASK_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown task frame schema_name: {frame.schema_name}")
    if frame.schema_version != TASK_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown task frame schema_version: {frame.schema_version}")
    if frame.status not in {"queued", "running", "completed", "failed", "skipped"}:
        raise ValueError(f"unknown TaskFrame.status: {frame.status}")
    _validate_string_list("TaskFrame.depends_on_task_ids", frame.depends_on_task_ids)
    _validate_string_list("TaskFrame.input_trace_ids", frame.input_trace_ids)
    _validate_string_list("TaskFrame.input_data_ids", frame.input_data_ids)
    _validate_string_list("TaskFrame.expected_output_trace_ids", frame.expected_output_trace_ids)
    _validate_string_list("TaskFrame.expected_output_data_ids", frame.expected_output_data_ids)


def validate_task_result_frame(frame: TaskResultFrame) -> None:
    """TaskResultFrame이 최소 결과 장부 규칙을 지키는지 확인한다."""

    for field_name, value in {
        "result_id": frame.result_id,
        "task_id": frame.task_id,
        "turn_id": frame.turn_id,
        "status": frame.status,
        "committed_by": frame.committed_by,
        "schema_name": frame.schema_name,
        "schema_version": frame.schema_version,
    }.items():
        if not value:
            raise ValueError(f"TaskResultFrame.{field_name} must not be empty")
    if frame.schema_name != TASK_RESULT_FRAME_SCHEMA_NAME:
        raise ValueError(f"unknown task result schema_name: {frame.schema_name}")
    if frame.schema_version != TASK_RESULT_FRAME_SCHEMA_VERSION:
        raise ValueError(f"unknown task result schema_version: {frame.schema_version}")
    if frame.status not in {"completed", "failed", "skipped"}:
        raise ValueError(f"unknown TaskResultFrame.status: {frame.status}")
    if frame.status == "failed" and not frame.failure_type:
        raise ValueError("failed TaskResultFrame must include failure_type")
    _validate_string_list("TaskResultFrame.output_trace_ids", frame.output_trace_ids)
    _validate_string_list("TaskResultFrame.output_data_ids", frame.output_data_ids)


__all__ = [
    "TASK_FRAME_SCHEMA_NAME",
    "TASK_FRAME_SCHEMA_VERSION",
    "TASK_RESULT_FRAME_SCHEMA_NAME",
    "TASK_RESULT_FRAME_SCHEMA_VERSION",
    "TaskFrame",
    "TaskResultFrame",
    "validate_task_frame",
    "validate_task_result_frame",
]
