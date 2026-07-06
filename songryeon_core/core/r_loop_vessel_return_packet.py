from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.trace_store import TraceStore


R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE = "r_loop:vessel_return_packet"
R_LOOP_VESSEL_RETURN_PACKET_GENERATOR = "CODE:NODE_0_R_VESSEL_RETURN_PACKET"
R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME = "RLoopVesselReturnPacketFrame"
R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION = "0.1"
R_LOOP_VESSEL_RETURN_STATUSES = {"available", "failed"}

# 학습용 큰 그림:
# R 루프는 그래프를 탐색하고 많은 내부 frame을 남긴다.
# 하지만 node_2/node_3가 그 모든 내부 frame을 직접 이해하면 너무 위험하고 복잡하다.
# 그래서 node_0이 R 활동 장부를 읽고 "이번 R 탐색 결과를 downstream에 넘겨도 되는가"를
# 절대정보 봉투로 다시 포장한다. 그 봉투가 RLoopVesselReturnPacketFrame이다.


@dataclass(frozen=True)
class RLoopVesselReturnPacketFrame:
    """node_0 labels the finished Vessel R traversal for downstream nodes."""

    # packet_id/turn_id/target/mode는 이 봉투 자체의 좌표와 용도다.
    packet_id: str
    turn_id: str
    target: str
    mode: str

    # return_status는 R 결과를 downstream에 넘길 수 있는지에 대한 code 상태값이다.
    # 여기서 의미 판단을 하는 것이 아니라, traverse가 completed였는지 같은 절대 상태만 본다.
    return_status: str

    # source_* 필드는 이 return packet이 어떤 R 기록에서 나왔는지 알려주는 족보다.
    # 송련식으로 말하면 "이 봉투의 출처 장부"다.
    source_start_handoff_packet_id: str | None
    source_activity_ledger_frame_id: str
    source_traverse_result_frame_id: str
    source_return_summary_frame_id: str | None
    source_read_packet_id: str

    # R 루프가 자기 일을 얼마나 끝냈는지 나타내는 상태 요약.
    # node_3는 이 값을 보고 "R이 충분히 봤다/부분만 봤다/실패했다"를 구분할 수 있다.
    r_loop_task_status: str
    traverse_status: str
    failure_stage: str | None
    failure_type: str | None
    failure_reason: str | None

    # R이 실제로 고른 node 수, 검사한 node 수, summary/raw 재료 수.
    # count는 code가 확정 가능한 절대정보라서 LLM에게 맡기지 않는다.
    selected_graph_node_count: int
    inspected_graph_node_count: int
    summary_material_count: int
    raw_original_material_count: int

    # node3_material_ready=True는 "node_3에 넘길 R 재료 좌표가 있다"는 뜻이다.
    # "그 재료가 사용자 질문에 의미적으로 충분하다"는 뜻은 아니다.
    node3_material_ready: bool
    node3_material_source_data_ids: list[str]

    # trace/data 출처. 내부 ID는 사용자 답변에 그대로 새면 안 되지만,
    # 시스템 내부 감사와 재현에는 반드시 필요하다.
    source_trace_ids: list[str]
    source_data_ids: list[str]
    generated_by: str = R_LOOP_VESSEL_RETURN_PACKET_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"
    schema_name: str = R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME
    schema_version: str = R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION


@dataclass(frozen=True)
class RecordedRLoopVesselReturnPacket:
    packet: RLoopVesselReturnPacketFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


def r_loop_vessel_return_packet_id(frame_label: str) -> str:
    if not frame_label:
        raise ValueError("frame_label must not be empty")
    return f"r_loop:vessel_return_packet:{_stable_suffix(frame_label)}"


def build_r_loop_vessel_return_packet(
    *,
    data_store: DataStore,
    turn_id: str,
    activity_ledger_payload: dict[str, object],
    frame_label: str,
) -> RLoopVesselReturnPacketFrame:
    # activity ledger는 R 탐색이 끝난 뒤의 장부다.
    # 여기서 traverse result, read packet, return summary 같은 핵심 frame id를 꺼낸다.
    activity_ledger_id = _required_text(activity_ledger_payload, "frame_id")
    traverse_result_id = _required_text(activity_ledger_payload, "traverse_result_frame_id")
    read_packet_id = _required_text(activity_ledger_payload, "source_read_packet_id")
    traverse_payload = _payload_by_id(data_store, traverse_result_id)
    return_summary_id = _optional_text(
        activity_ledger_payload.get("return_summary_frame_id")
    )
    traverse_status = _text(
        traverse_payload,
        "traverse_status",
        fallback=_text(activity_ledger_payload, "traverse_status", fallback="failed"),
    )
    r_loop_task_status = _text(
        traverse_payload,
        "r_loop_task_status",
        fallback=_optional_text(activity_ledger_payload.get("r_loop_task_status"))
        or "failed",
    )

    # selected_ids: R2가 선택한 그래프 node들.
    # inspected_ids: R3가 실제로 검사한 그래프 node들.
    # 둘 다 나중에 node_3 재료 후보가 되지만, 사용자-facing 답변에는 안전한 label/요약으로 바꿔야 한다.
    selected_ids = _string_list(
        traverse_payload.get("selected_graph_node_ids")
        if traverse_payload
        else activity_ledger_payload.get("selected_graph_node_ids")
    )
    inspected_ids = _string_list(
        traverse_payload.get("inspected_graph_node_ids")
        if traverse_payload
        else activity_ledger_payload.get("inspected_graph_node_ids")
    )

    # completed만 available로 본다.
    # partial/failed를 억지로 available로 고치지 않는 것이 정직성 원칙이다.
    return_status = "available" if traverse_status == "completed" else "failed"

    # material_source_ids는 node_3가 R 자료를 찾아갈 수 있는 최소 좌표 묶음이다.
    # 여기에는 내부 graph id가 들어가므로, 최종 답변에서는 그대로 노출하면 안 된다.
    material_source_ids = _unique_strings(
        [
            traverse_result_id,
            read_packet_id,
            return_summary_id,
            *selected_ids,
            *inspected_ids,
        ]
    )
    frame = RLoopVesselReturnPacketFrame(
        packet_id=r_loop_vessel_return_packet_id(frame_label),
        turn_id=turn_id,
        target="node_1_or_node_2",
        mode="vessel_r_return_packet",
        return_status=return_status,
        source_start_handoff_packet_id=_optional_text(
            activity_ledger_payload.get("source_start_handoff_packet_id")
        ),
        source_activity_ledger_frame_id=activity_ledger_id,
        source_traverse_result_frame_id=traverse_result_id,
        source_return_summary_frame_id=return_summary_id,
        source_read_packet_id=read_packet_id,
        r_loop_task_status=r_loop_task_status,
        traverse_status=traverse_status,
        failure_stage=_optional_text(
            traverse_payload.get("failure_stage")
            if traverse_payload
            else activity_ledger_payload.get("failure_stage")
        ),
        failure_type=_optional_text(
            traverse_payload.get("failure_type")
            if traverse_payload
            else activity_ledger_payload.get("failure_type")
        ),
        failure_reason=_optional_text(
            traverse_payload.get("failure_reason")
            if traverse_payload
            else activity_ledger_payload.get("failure_reason")
        ),
        selected_graph_node_count=len(selected_ids),
        inspected_graph_node_count=len(inspected_ids),
        # graph:summary:* 로 시작하는 node는 R이 본 요약 재료로 센다.
        # 이것도 의미 판단이 아니라 id prefix와 record 구조에 근거한 절대 count다.
        summary_material_count=sum(
            1
            for value in _unique_strings([*selected_ids, *inspected_ids])
            if value.startswith("graph:summary:")
        ),
        raw_original_material_count=_int(
            traverse_payload,
            "raw_original_material_seen_count",
            fallback=_int(activity_ledger_payload, "raw_original_material_seen_count"),
        ),
        node3_material_ready=return_status == "available",
        node3_material_source_data_ids=material_source_ids,
        source_trace_ids=_unique_strings(
            [
                *_string_list(activity_ledger_payload.get("source_trace_ids")),
                *_string_list(traverse_payload.get("source_trace_ids")),
            ]
        ),
        source_data_ids=_unique_strings(
            [
                activity_ledger_id,
                traverse_result_id,
                read_packet_id,
                return_summary_id,
                _optional_text(activity_ledger_payload.get("source_start_handoff_packet_id")),
                *_string_list(activity_ledger_payload.get("source_data_ids")),
                *_string_list(traverse_payload.get("source_data_ids")),
                *material_source_ids,
            ]
        ),
    )
    validate_r_loop_vessel_return_packet_frame(frame)
    return frame


def record_r_loop_vessel_return_packet(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    activity_ledger_frame_id: str,
    frame_label: str = "manual_vessel_r_traverse",
) -> RecordedRLoopVesselReturnPacket:
    # record_* 함수는 build_*가 만든 frame을 TraceStore/DataStore에 실제로 기록한다.
    # build_*는 객체 생성과 검증, record_*는 사건/데이터 저장이라고 보면 된다.
    activity_record = data_store.require_record(activity_ledger_frame_id)
    if not isinstance(activity_record.payload, dict):
        raise ValueError("R Vessel return packet requires activity ledger payload")
    packet = build_r_loop_vessel_return_packet(
        data_store=data_store,
        turn_id=turn_id,
        activity_ledger_payload=activity_record.payload,
        frame_label=frame_label,
    )
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="memory_packet",
        timestamp=_now_iso(),
        input_ref=packet.source_trace_ids,
        output_ref=[packet.packet_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=packet.packet_id,
        data_type=R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE,
        payload=asdict(packet),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedRLoopVesselReturnPacket(
        packet=packet,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def validate_r_loop_vessel_return_packet_frame(
    frame: RLoopVesselReturnPacketFrame,
) -> None:
    _require_text_fields(
        "RLoopVesselReturnPacketFrame",
        {
            "packet_id": frame.packet_id,
            "turn_id": frame.turn_id,
            "target": frame.target,
            "mode": frame.mode,
            "return_status": frame.return_status,
            "source_activity_ledger_frame_id": frame.source_activity_ledger_frame_id,
            "source_traverse_result_frame_id": frame.source_traverse_result_frame_id,
            "source_read_packet_id": frame.source_read_packet_id,
            "r_loop_task_status": frame.r_loop_task_status,
            "traverse_status": frame.traverse_status,
            "generated_by": frame.generated_by,
            "info_class": frame.info_class,
            "semantic_judgement_status": frame.semantic_judgement_status,
            "schema_name": frame.schema_name,
            "schema_version": frame.schema_version,
        },
    )
    if frame.target != "node_1_or_node_2":
        raise ValueError("RLoopVesselReturnPacketFrame.target is invalid")
    if frame.mode != "vessel_r_return_packet":
        raise ValueError("RLoopVesselReturnPacketFrame.mode is invalid")
    if frame.return_status not in R_LOOP_VESSEL_RETURN_STATUSES:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.return_status: {frame.return_status}")
    if frame.traverse_status not in {"completed", "failed", "not_run"}:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.traverse_status: {frame.traverse_status}")
    if frame.r_loop_task_status not in {"not_run", "sufficient", "partial", "failed"}:
        raise ValueError(
            f"unknown RLoopVesselReturnPacketFrame.r_loop_task_status: {frame.r_loop_task_status}"
        )
    if frame.generated_by != R_LOOP_VESSEL_RETURN_PACKET_GENERATOR:
        raise ValueError("RLoopVesselReturnPacketFrame.generated_by must be node_0 code")
    if frame.info_class != "absolute":
        raise ValueError("RLoopVesselReturnPacketFrame.info_class must be absolute")
    if frame.semantic_judgement_status != "not_run":
        raise ValueError(
            "RLoopVesselReturnPacketFrame.semantic_judgement_status must be not_run"
        )
    if frame.schema_name != R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.schema_name: {frame.schema_name}")
    if frame.schema_version != R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION:
        raise ValueError(f"unknown RLoopVesselReturnPacketFrame.schema_version: {frame.schema_version}")
    _validate_non_negative_ints(
        "RLoopVesselReturnPacketFrame",
        {
            "selected_graph_node_count": frame.selected_graph_node_count,
            "inspected_graph_node_count": frame.inspected_graph_node_count,
            "summary_material_count": frame.summary_material_count,
            "raw_original_material_count": frame.raw_original_material_count,
        },
    )
    if not isinstance(frame.node3_material_ready, bool):
        raise TypeError("RLoopVesselReturnPacketFrame.node3_material_ready must be bool")
    if frame.return_status == "failed" and frame.node3_material_ready:
        raise ValueError("failed RLoopVesselReturnPacketFrame cannot be node3-ready")
    for field_name, values in {
        "node3_material_source_data_ids": frame.node3_material_source_data_ids,
        "source_trace_ids": frame.source_trace_ids,
        "source_data_ids": frame.source_data_ids,
    }.items():
        _validate_string_list(f"RLoopVesselReturnPacketFrame.{field_name}", values)
        _validate_no_duplicates(f"RLoopVesselReturnPacketFrame.{field_name}", values)
    required_source_ids = _unique_strings(
        [
            frame.source_start_handoff_packet_id,
            frame.source_activity_ledger_frame_id,
            frame.source_traverse_result_frame_id,
            frame.source_return_summary_frame_id,
            frame.source_read_packet_id,
            *frame.node3_material_source_data_ids,
        ]
    )
    missing = sorted(set(required_source_ids) - set(frame.source_data_ids))
    if missing:
        raise ValueError(
            "RLoopVesselReturnPacketFrame.source_data_ids missing required IDs: "
            f"{missing}"
        )


def _payload_by_id(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


def _record_payload_if_missing(
    *,
    data_store: DataStore,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
    created_at: str,
    source_trace_id: str,
    created_data_ids: list[str],
    existing_data_ids: list[str],
) -> None:
    existing = data_store.get_record(data_id)
    if existing is not None:
        if existing.data_type != data_type:
            raise ValueError(f"R Vessel return packet data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"R Vessel return packet payload collision: {data_id}")
        existing_data_ids.append(data_id)
        return
    data_store.create_record(
        data_id=data_id,
        data_type=data_type,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )
    created_data_ids.append(data_id)


def _required_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _text(payload: dict[str, object], field_name: str, *, fallback: str = "") -> str:
    value = payload.get(field_name)
    return value if isinstance(value, str) and value else fallback


def _int(payload: dict[str, object], field_name: str, *, fallback: int = 0) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    return fallback


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _validate_non_negative_ints(class_name: str, values: dict[str, int]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, int):
            raise TypeError(f"{class_name}.{field_name} must be an integer")
        if value < 0:
            raise ValueError(f"{class_name}.{field_name} must not be negative")


def _validate_string_list(field_name: str, values: list[str]) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name} must contain only non-empty strings")


def _validate_no_duplicates(field_name: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")


def _require_text_fields(class_name: str, values: dict[str, str]) -> None:
    for field_name, value in values.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{class_name}.{field_name} must not be empty")


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _stable_suffix(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace("\\", "_")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "R_LOOP_VESSEL_RETURN_PACKET_DATA_TYPE",
    "R_LOOP_VESSEL_RETURN_PACKET_GENERATOR",
    "R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_NAME",
    "R_LOOP_VESSEL_RETURN_PACKET_SCHEMA_VERSION",
    "R_LOOP_VESSEL_RETURN_STATUSES",
    "RLoopVesselReturnPacketFrame",
    "RecordedRLoopVesselReturnPacket",
    "build_r_loop_vessel_return_packet",
    "r_loop_vessel_return_packet_id",
    "record_r_loop_vessel_return_packet",
    "validate_r_loop_vessel_return_packet_frame",
]
