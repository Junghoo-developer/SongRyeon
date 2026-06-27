from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DataRef:
    """시스템이 확인할 수 있는 데이터 하나를 가리키는 절대정보 참조."""

    # 데이터 하나를 가리키는 고유 ID.
    data_id: str
    # 데이터 종류. 예: trace_event, user_message, node_output, schema_result.
    data_type: str
    # 시스템이 이 데이터의 존재를 확인했는지.
    exists: bool = True
    # 데이터가 만들어진 시간. 모르면 None으로 둔다.
    created_at: str | None = None
    # 이 데이터 존재를 확인하게 해준 trace ID.
    source_trace_id: str | None = None


@dataclass
class SchemaBinding:
    """어떤 스키마가 어디에 적용되고 검증됐는지 기록하는 절대정보."""

    # 적용할 스키마 이름.
    schema_name: str
    # 적용할 스키마 버전.
    schema_version: str
    # 이 스키마가 반드시 적용되어야 하는지.
    required: bool = True
    # 스키마 검증 결과. 예: passed, failed, not_checked.
    validation_status: str = "not_checked"
    # 스키마 검증 과정 자체를 기록한 trace ID.
    validation_trace_id: str | None = None


@dataclass
class NodeMovement:
    """한 턴 안에서 노드나 루프가 실제로 이동한 동선을 기록하는 절대정보."""

    # 노드 동선 하나를 구분하는 ID.
    movement_id: str
    # 이 동선이 속한 턴 ID.
    turn_id: str
    # 턴 안에서 몇 번째로 실행됐는지 나타내는 순서 번호.
    step_index: int
    # 실행된 노드나 루프의 ID. 예: node_0, node_1, L1.
    node_id: str
    # 실행 단위의 종류. 예: node, loop_node, tool.
    node_type: str = "node"
    # 실제 호출된 모드. 예: pre_route_report, final_trace_for_2.
    mode: str | None = None
    # 이 실행 단위가 입력으로 받은 trace ID 목록.
    input_trace_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 출력으로 만든 trace ID 목록.
    output_trace_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 입력으로 받은 데이터 ID 목록.
    input_data_ids: list[str] = field(default_factory=list)
    # 이 실행 단위가 출력으로 만든 데이터 ID 목록.
    output_data_ids: list[str] = field(default_factory=list)
    # 실행 시작 시간.
    started_at: str | None = None
    # 실행 종료 시간.
    finished_at: str | None = None
    # 실행 상태. 예: started, completed, failed.
    status: str = "started"


def _validate_string_list(field_name: str, values: list[str]) -> None:
    for value in values:
        if not value:
            raise ValueError(f"{field_name} must not contain empty values")


def _validate_no_duplicates(field_name: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicate values")


__all__ = [
    "DataRef",
    "NodeMovement",
    "SchemaBinding",
    "_validate_no_duplicates",
    "_validate_string_list",
]
