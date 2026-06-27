from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DataRef,
    MetainfoBoundary,
    MixedInfoRef,
    RelativeInfoRef,
    Node2BoundaryReviewFrame,
    validate_mixed_info_ref,
    validate_relative_info_ref,
    validate_node2_boundary_review_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


def build_metainfo_boundary(
    *,
    trace_store: TraceStore,
    turn_id: str,
    data_store: DataStore | None = None,
    node2_input_frame_id: str | None = None,
) -> MetainfoBoundary:
    """현재 턴 trace에서 확인 가능한 절대정보만 모아 MetainfoBoundary를 만든다."""

    if node2_input_frame_id is not None and data_store is not None:
        return _build_boundary_from_node2_input_frame(
            trace_store=trace_store,
            data_store=data_store,
            node2_input_frame_id=node2_input_frame_id,
        )

    return _build_boundary_from_turn_trace(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
    )


def _build_boundary_from_turn_trace(
    *,
    trace_store: TraceStore,
    turn_id: str,
    data_store: DataStore | None = None,
) -> MetainfoBoundary:
    """옛 방식: 한 턴의 전체 trace를 절대정보 후보로 훑는다."""

    absolute_info: list[DataRef] = []
    seen_data_ids: set[str] = set()
    for event in trace_store.events_for_turn(turn_id):
        _append_ref_once(
            absolute_info,
            seen_data_ids,
            DataRef(
                data_id=event.event_id,
                data_type=f"trace_event:{event.event_type}",
                exists=True,
                created_at=event.timestamp,
                source_trace_id=event.event_id,
            ),
        )
        for output_id in event.output_ref:
            _append_data_record_ref(
                absolute_info=absolute_info,
                seen_data_ids=seen_data_ids,
                data_store=data_store,
                data_id=output_id,
                fallback_created_at=event.timestamp,
                fallback_source_trace_id=event.event_id,
                fallback_data_type=f"trace_output_ref:{event.event_type}",
            )
    relative_info, mixed_info = (
        _build_semantic_info_refs(
            data_store=data_store,
            source_data_ids=[data_ref.data_id for data_ref in absolute_info],
        )
        if data_store is not None
        else ([], [])
    )
    return MetainfoBoundary(
        absolute_info=absolute_info,
        relative_info=relative_info,
        mixed_info=mixed_info,
    )


def _build_boundary_from_node2_input_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    node2_input_frame_id: str,
) -> MetainfoBoundary:
    """새 방식: 0이 정리한 Node2InputFrame에 적힌 source만 읽는다."""

    frame_record = data_store.require_record(node2_input_frame_id)
    if not isinstance(frame_record.payload, dict):
        raise TypeError("Node2InputFrame payload must be a dict")

    source_trace_ids = _read_string_list(frame_record.payload, "source_trace_ids")
    source_data_ids = _read_string_list(frame_record.payload, "source_data_ids")
    source_data_id_set = set(source_data_ids)

    absolute_info: list[DataRef] = []
    seen_data_ids: set[str] = set()
    _append_data_record_ref(
        absolute_info=absolute_info,
        seen_data_ids=seen_data_ids,
        data_store=data_store,
        data_id=node2_input_frame_id,
        fallback_data_type="data_record:node_output:node2_input_frame",
    )

    for trace_id in source_trace_ids:
        event = trace_store.get_event(trace_id)
        if event is None:
            _append_ref_once(
                absolute_info,
                seen_data_ids,
                DataRef(
                    data_id=trace_id,
                    data_type="trace_event:missing",
                    exists=False,
                ),
            )
            continue

        _append_ref_once(
            absolute_info,
            seen_data_ids,
            DataRef(
                data_id=event.event_id,
                data_type=f"trace_event:{event.event_type}",
                exists=True,
                created_at=event.timestamp,
                source_trace_id=event.event_id,
            ),
        )
        for output_id in event.output_ref:
            if output_id not in source_data_id_set:
                continue
            _append_data_record_ref(
                absolute_info=absolute_info,
                seen_data_ids=seen_data_ids,
                data_store=data_store,
                data_id=output_id,
                fallback_created_at=event.timestamp,
                fallback_source_trace_id=event.event_id,
                fallback_data_type=f"trace_output_ref:{event.event_type}",
            )

    for data_id in source_data_ids:
        _append_data_record_ref(
            absolute_info=absolute_info,
            seen_data_ids=seen_data_ids,
            data_store=data_store,
            data_id=data_id,
            fallback_data_type="data_record:missing",
        )

    relative_info, mixed_info = _build_semantic_info_refs(
        data_store=data_store,
        source_data_ids=source_data_ids,
    )
    return MetainfoBoundary(
        absolute_info=absolute_info,
        relative_info=relative_info,
        mixed_info=mixed_info,
    )


def record_boundary(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    boundary_id: str,
    boundary: MetainfoBoundary,
    input_ref: list[str] | None = None,
) -> str:
    """MetainfoBoundary가 만들어졌다는 사실을 trace로 기록한다."""

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="schema_check",
        input_ref=input_ref or [data_ref.data_id for data_ref in boundary.absolute_info],
        output_ref=[boundary_id],
        schema_status="passed",
    )
    if data_store is not None:
        data_store.create_record(
            data_id=boundary_id,
            data_type="node_output:metainfo_boundary",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(boundary),
        )
    return event.event_id


def run_node2_boundary_review(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    boundary_id: str,
    boundary: MetainfoBoundary,
    adapter: LLMAdapter,
    input_ref: list[str],
    source_data_ids: list[str],
) -> str:
    """LLM이 node_2 boundary를 검토한 결과를 별도 frame으로 저장한다."""

    review_id = "node_2:boundary_review"
    prompt_ref = "songryeon_core/prompts/node_2_metainfo_boundary_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="node_2",
        prompt=prompt,
        input_payload={
            "boundary_id": boundary_id,
            "absolute_info_count": len(boundary.absolute_info),
            "relative_info_count": len(boundary.relative_info),
            "mixed_info_count": len(boundary.mixed_info),
            "absolute_info_samples": [
                asdict(data_ref) for data_ref in boundary.absolute_info[:12]
            ],
            "relative_info": [asdict(info_ref) for info_ref in boundary.relative_info[:12]],
            "mixed_info": [asdict(info_ref) for info_ref in boundary.mixed_info[:12]],
            "source_data_ids": source_data_ids,
        },
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_ref,
        source_data_ids=source_data_ids,
        payload_validator=_validate_node2_review_payload,
    )
    if llm_result.failure_type == "none" and llm_result.validation.payload is not None:
        payload = llm_result.validation.payload
        review_status = "ran"
        ready_for_report = bool(payload.get("ready_for_report"))
        boundary_summary = str(payload.get("boundary_summary") or "").strip()
        warnings = _string_list(payload.get("warnings"))
        excluded_claims = _string_list(payload.get("excluded_claims"))
    else:
        review_status = "failed"
        ready_for_report = False
        boundary_summary = f"LLM boundary review failed: {llm_result.failure_type}"
        warnings = [boundary_summary]
        excluded_claims = []

    frame_source_trace_ids = list(input_ref)
    if llm_result.trace_event_id:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = _unique_strings(
        [*source_data_ids, boundary_id, llm_result.call_data_id]
    )
    frame = Node2BoundaryReviewFrame(
        review_id=review_id,
        turn_id=turn_id,
        boundary_id=boundary_id,
        review_status=review_status,
        ready_for_report=ready_for_report,
        boundary_summary=boundary_summary,
        review_generation_source=f"LLM:{llm_result.model_id}",
        warnings=warnings,
        excluded_claims=excluded_claims,
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=frame_source_data_ids,
    )
    validate_node2_boundary_review_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[review_id],
        schema_status="passed" if review_status == "ran" else "failed",
    )
    data_store.create_record(
        data_id=review_id,
        data_type="node_output:node2_boundary_review",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id


def _data_record_metadata_refs(
    *,
    data_id: str,
    source_trace_id: str,
    created_at: str,
    payload: dict[str, object],
) -> list[DataRef]:
    """DataStore payload 안의 스키마 metadata를 절대정보 후보로 분리한다."""

    refs: list[DataRef] = []
    for field_name in ("schema_name", "schema_version"):
        value = payload.get(field_name)
        if isinstance(value, str) and value:
            refs.append(
                DataRef(
                    data_id=f"{data_id}:{field_name}",
                    data_type=f"data_record_metadata:{field_name}:{value}",
                    exists=True,
                    created_at=created_at,
                    source_trace_id=source_trace_id,
                )
            )
    for field_name in ("source_trace_ids", "source_data_ids"):
        value = payload.get(field_name)
        if isinstance(value, list):
            refs.append(
                DataRef(
                    data_id=f"{data_id}:{field_name}",
                    data_type=f"data_record_metadata:{field_name}:count:{len(value)}",
                    exists=True,
                    created_at=created_at,
                    source_trace_id=source_trace_id,
                )
            )
    return refs


def _build_semantic_info_refs(
    *,
    data_store: DataStore,
    source_data_ids: list[str],
) -> tuple[list[RelativeInfoRef], list[MixedInfoRef]]:
    """2가 보고를 허용할 수 있는 근거 달린 의미 정보를 분류해서 골라낸다."""

    # 학습 메모: node_2는 여기서 문장 뜻을 새로 판정하지 않는다.
    # schema/status/source ID 같은 구조 신호를 보고, 이미 생긴 의미 텍스트의 운반 등급만 나눈다.
    relative_info: list[RelativeInfoRef] = []
    mixed_info: list[MixedInfoRef] = []
    seen_info_ids: set[str] = set()
    for data_id in _unique_strings(source_data_ids):
        record = data_store.get_record(data_id)
        if record is None or not isinstance(record.payload, dict):
            continue

        payload = record.payload
        schema_name = payload.get("schema_name")
        source_trace_ids = _record_source_trace_ids(record_source_trace_id=record.source_trace_id, payload=payload)
        source_data_ids_for_record = _record_source_data_ids(record_data_id=record.data_id, payload=payload)
        if not source_trace_ids or not source_data_ids_for_record:
            continue

        if schema_name == "L3AchievementFrame" and _is_llm_semantic_payload(payload):
            _append_semantic_text_field(
                relative_info=relative_info,
                mixed_info=mixed_info,
                seen_info_ids=seen_info_ids,
                source_data_id=record.data_id,
                field_path="reason",
                info_kind="l3_achievement_reason",
                text=payload.get("reason"),
                source_trace_ids=source_trace_ids,
                source_data_ids=source_data_ids_for_record,
            )
        elif schema_name == "ToolChoiceFrame" and _is_llm_tool_choice_payload(payload):
            _append_semantic_text_field(
                relative_info=relative_info,
                mixed_info=mixed_info,
                seen_info_ids=seen_info_ids,
                source_data_id=record.data_id,
                field_path="reason",
                info_kind="tool_choice_reason",
                text=payload.get("reason"),
                source_trace_ids=source_trace_ids,
                source_data_ids=source_data_ids_for_record,
            )
        elif schema_name == "L2QueryPlanFrame":
            _append_l2_query_plan_purposes(
                relative_info=relative_info,
                mixed_info=mixed_info,
                seen_info_ids=seen_info_ids,
                source_data_id=record.data_id,
                payload=payload,
                source_trace_ids=source_trace_ids,
                source_data_ids=source_data_ids_for_record,
            )
        elif schema_name == "MemoryRelevanceSelectionFrame":
            _append_memory_relevance_selection_reason(
                relative_info=relative_info,
                mixed_info=mixed_info,
                seen_info_ids=seen_info_ids,
                source_data_id=record.data_id,
                payload=payload,
                source_trace_ids=source_trace_ids,
                source_data_ids=source_data_ids_for_record,
            )

    return relative_info, mixed_info


def _append_memory_relevance_selection_reason(
    *,
    relative_info: list[RelativeInfoRef],
    mixed_info: list[MixedInfoRef],
    seen_info_ids: set[str],
    source_data_id: str,
    payload: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> None:
    """LLM selector의 selection_reason을 source bundle 혼합 정보로 보존한다."""

    if payload.get("info_class") != "mixed":
        return
    if payload.get("source_mode") != "source_bundle":
        return
    if payload.get("claim_alignment") != "multi_source_bundle":
        return
    if not str(payload.get("generated_by") or "").startswith("LLM:"):
        return

    _append_semantic_text_field(
        relative_info=relative_info,
        mixed_info=mixed_info,
        seen_info_ids=seen_info_ids,
        source_data_id=source_data_id,
        field_path="selection_reason",
        info_kind="memory_relevance_selection_reason",
        text=payload.get("selection_reason"),
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        force_mixed=True,
    )


def _append_l2_query_plan_purposes(
    *,
    relative_info: list[RelativeInfoRef],
    mixed_info: list[MixedInfoRef],
    seen_info_ids: set[str],
    source_data_id: str,
    payload: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> None:
    """LLM query plan 후보의 purpose를 출처 달린 혼합 정보로 승격한다."""

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            continue
        candidate_source_data_ids = _unique_strings(
            [
                *source_data_ids,
                *_optional_string_list(candidate, "source_data_ids"),
            ]
        )
        _append_semantic_text_field(
            relative_info=relative_info,
            mixed_info=mixed_info,
            seen_info_ids=seen_info_ids,
            source_data_id=source_data_id,
            field_path=f"candidates[{index}].purpose",
            info_kind="l2_query_candidate_purpose",
            text=candidate.get("purpose"),
            source_trace_ids=source_trace_ids,
            source_data_ids=candidate_source_data_ids,
            # L2 purpose는 candidate field 하나에 저장되어 있어도, planner가 여러 입력 묶음으로 만든 이유다.
            # 그래서 direct-field 모양처럼 보여도 source bundle 판단으로 고정한다.
            force_mixed=True,
        )


def _is_llm_semantic_payload(payload: dict[str, object]) -> bool:
    return (
        payload.get("llm_semantic_judgement_status") != "not_run"
        and not str(payload.get("achievement_generation_source") or "").startswith("CODE:")
    )


def _is_llm_tool_choice_payload(payload: dict[str, object]) -> bool:
    return (
        payload.get("llm_tool_choice_status") != "not_run"
        and not str(payload.get("choice_generation_source") or "").startswith("CODE:")
    )


def _append_semantic_text_field(
    *,
    relative_info: list[RelativeInfoRef],
    mixed_info: list[MixedInfoRef],
    seen_info_ids: set[str],
    source_data_id: str,
    field_path: str,
    info_kind: str,
    text: object,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    force_mixed: bool = False,
) -> None:
    """본문과 근거 ID가 모두 있을 때만 RelativeInfoRef 또는 MixedInfoRef를 추가한다."""

    if not isinstance(text, str) or not text.strip():
        return

    # 학습 메모: relative/mixed 분류는 text 내용을 읽어서 맞히는 휴리스틱이 아니다.
    # source_data_ids가 원본 record 하나뿐인지, source bundle인지라는 provenance 모양만 본다.
    normalized_source_data_ids = _unique_strings([source_data_id, *source_data_ids])
    if not force_mixed and _is_direct_field_claim(
        source_data_id=source_data_id,
        source_data_ids=normalized_source_data_ids,
    ):
        ref = RelativeInfoRef(
            info_id=_relative_info_id(source_data_id=source_data_id, field_path=field_path),
            source_data_id=source_data_id,
            field_path=field_path,
            info_kind=info_kind,
            text=text.strip(),
            source_trace_ids=source_trace_ids,
            source_data_ids=normalized_source_data_ids,
        )
        validate_relative_info_ref(ref)
        if ref.info_id in seen_info_ids:
            return
        relative_info.append(ref)
        seen_info_ids.add(ref.info_id)
        return

    ref = MixedInfoRef(
        info_id=_mixed_info_id(source_data_id=source_data_id, field_path=field_path),
        source_data_id=source_data_id,
        field_path=field_path,
        info_kind=info_kind,
        text=text.strip(),
        source_trace_ids=source_trace_ids,
        source_data_ids=normalized_source_data_ids,
    )
    validate_mixed_info_ref(ref)
    if ref.info_id in seen_info_ids:
        return
    mixed_info.append(ref)
    seen_info_ids.add(ref.info_id)


def _is_direct_field_claim(*, source_data_id: str, source_data_ids: list[str]) -> bool:
    """근거 data가 원본 record 하나뿐이면 one-to-one field 주장으로 분류한다."""

    # source_data_ids에 자기 record 외의 근거가 붙는 순간, claim은 한 field만으로 설명하기 어려워진다.
    return _unique_strings(source_data_ids) == [source_data_id]


def _record_source_trace_ids(
    *,
    record_source_trace_id: str | None,
    payload: dict[str, object],
) -> list[str]:
    """record 자체와 payload가 말하는 trace 근거를 합친다."""

    return _unique_strings(
        [
            record_source_trace_id,
            *_optional_string_list(payload, "source_trace_ids"),
            *_optional_string_list(payload, "evidence_trace_ids"),
        ]
    )


def _record_source_data_ids(
    *,
    record_data_id: str,
    payload: dict[str, object],
) -> list[str]:
    """record 자체와 payload가 말하는 data 근거를 합친다."""

    return _unique_strings(
        [
            record_data_id,
            *_optional_string_list(payload, "source_data_ids"),
            *_optional_string_list(payload, "evidence_data_ids"),
        ]
    )


def _mixed_info_id(*, source_data_id: str, field_path: str) -> str:
    """원본 위치가 같으면 같은 ID가 나오도록 boundary 내부 ID를 만든다."""

    return f"mixed:{_safe_identifier(source_data_id)}:{_safe_identifier(field_path)}"


def _relative_info_id(*, source_data_id: str, field_path: str) -> str:
    """원본 위치가 같으면 같은 ID가 나오도록 relative boundary 내부 ID를 만든다."""

    return f"relative:{_safe_identifier(source_data_id)}:{_safe_identifier(field_path)}"


def _safe_identifier(value: str) -> str:
    """data_id와 field_path를 사람이 읽을 수 있는 안전한 ID 조각으로 바꾼다."""

    safe = "".join(character if character.isalnum() else "_" for character in value)
    return safe.strip("_") or "empty"


def _append_data_record_ref(
    *,
    absolute_info: list[DataRef],
    seen_data_ids: set[str],
    data_store: DataStore | None,
    data_id: str,
    fallback_created_at: str | None = None,
    fallback_source_trace_id: str | None = None,
    fallback_data_type: str = "data_record:missing",
) -> None:
    """DataStore record와 그 metadata ref를 중복 없이 absolute_info에 추가한다."""

    data_record = data_store.get_record(data_id) if data_store is not None else None
    if data_record is None:
        _append_ref_once(
            absolute_info,
            seen_data_ids,
            DataRef(
                data_id=data_id,
                data_type=fallback_data_type,
                exists=data_store is None,
                created_at=fallback_created_at,
                source_trace_id=fallback_source_trace_id,
            ),
        )
        return

    created_at = data_record.created_at or fallback_created_at
    source_trace_id = data_record.source_trace_id or fallback_source_trace_id
    _append_ref_once(
        absolute_info,
        seen_data_ids,
        DataRef(
            data_id=data_id,
            data_type=f"data_record:{data_record.data_type}",
            exists=data_record.exists,
            created_at=created_at,
            source_trace_id=source_trace_id,
        ),
    )
    if isinstance(data_record.payload, dict):
        for metadata_ref in _data_record_metadata_refs(
            data_id=data_id,
            source_trace_id=source_trace_id or "",
            created_at=created_at or "",
            payload=data_record.payload,
        ):
            _append_ref_once(absolute_info, seen_data_ids, metadata_ref)


def _append_ref_once(
    absolute_info: list[DataRef],
    seen_data_ids: set[str],
    data_ref: DataRef,
) -> None:
    """같은 data_id가 boundary에 여러 번 들어가는 것을 막는다."""

    if data_ref.data_id in seen_data_ids:
        return
    absolute_info.append(data_ref)
    seen_data_ids.add(data_ref.data_id)


def _read_string_list(payload: dict[str, object], field_name: str) -> list[str]:
    """Node2InputFrame payload에서 문자열 리스트 필드를 읽는다."""

    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"Node2InputFrame.{field_name} must be a list")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"Node2InputFrame.{field_name} must contain non-empty strings")
    return list(value)


def _optional_string_list(payload: dict[str, object], field_name: str) -> list[str]:
    """임의 payload에서 문자열 리스트면 읽고, 아니면 빈 리스트로 둔다."""

    value = payload.get(field_name)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _validate_node2_review_payload(payload: dict[str, object]) -> None:
    frame = Node2BoundaryReviewFrame(
        review_id="validation_review",
        turn_id="validation_turn",
        boundary_id="validation_boundary",
        review_status="ran",
        ready_for_report=bool(payload.get("ready_for_report")),
        boundary_summary=str(payload.get("boundary_summary") or "").strip(),
        review_generation_source="LLM:validation-model",
        warnings=_string_list(payload.get("warnings")),
        excluded_claims=_string_list(payload.get("excluded_claims")),
        source_trace_ids=["validation_trace"],
        source_data_ids=["validation_data"],
    )
    validate_node2_boundary_review_frame(frame)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _unique_strings(values: list[object]) -> list[str]:
    """순서를 보존하면서 빈 값과 중복 문자열을 제거한다."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        result.append(stripped)
        seen.add(stripped)
    return result
