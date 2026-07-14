from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DataRef,
    MetainfoBoundary,
    MixedInfoRef,
    Node2AnswerBasisFrame,
    RelativeInfoRef,
    Node2BoundaryReviewFrame,
    Node2EvidenceRole,
    validate_node2_answer_basis_frame,
    validate_mixed_info_ref,
    validate_relative_info_ref,
    validate_node2_boundary_review_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds


NODE2_ANSWER_BASIS_FRAME_DATA_ID = "node_2:answer_basis_frame"
NODE2_ANSWER_BASIS_SCHEMA_REPAIR_MAX_ATTEMPTS = 1
ANSWER_MATERIAL_CATALOG_MAX_ITEMS = 48
ANSWER_MATERIAL_PREVIEW_MAX_CHARS = 700


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


def run_node2_answer_basis_selection(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_question: str,
    boundary_id: str,
    boundary: MetainfoBoundary,
    handoff_frame_id: str,
    adapter: LLMAdapter | None,
    input_ref: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None = None,
) -> tuple[str, str, Node2AnswerBasisFrame]:
    """node_2 LLM이 node_3 답변 근거 모드를 고르고 실패 시 안전 fallback을 기록한다."""

    frame_id = (
        id_namespace.scoped_data_id(NODE2_ANSWER_BASIS_FRAME_DATA_ID)
        if id_namespace is not None
        else NODE2_ANSWER_BASIS_FRAME_DATA_ID
    )
    base_source_data_ids = _unique_strings(
        [*source_data_ids, boundary_id, handoff_frame_id]
    )
    available_evidence_sources = _answer_basis_available_evidence_sources(
        boundary=boundary,
        base_source_data_ids=base_source_data_ids,
        data_store=data_store,
        turn_id=turn_id,
        handoff_frame_id=handoff_frame_id,
    )
    evidence_source_id_by_ref = {
        str(source["evidence_ref"]): str(source["source_data_id"])
        for source in available_evidence_sources
    }
    evidence_ref_by_source_id = {
        source_data_id: evidence_ref
        for evidence_ref, source_data_id in evidence_source_id_by_ref.items()
    }
    evidence_source_metadata_by_ref = {
        str(source["evidence_ref"]): source
        for source in available_evidence_sources
    }
    allowed_answer_basis_source_data_ids = _unique_strings(
        [
            str(source["source_data_id"])
            for source in available_evidence_sources
            if isinstance(source.get("source_data_id"), str)
        ]
    )
    prompt_ref = "songryeon_core/prompts/node_2_answer_basis_selector_v0.md"
    if adapter is None:
        frame = _fallback_answer_basis_frame(
            frame_id=frame_id,
            turn_id=turn_id,
            source_trace_ids=input_ref,
            source_data_ids=allowed_answer_basis_source_data_ids,
            failure_type="adapter_missing",
            llm_call_data_id=None,
            trace_event_id=None,
            validation_error="adapter_missing",
            raw_text_present=False,
            prompt_ref=prompt_ref,
            payload_parse_status="not_checked",
        )
        return _record_answer_basis_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
            schema_status="failed",
        )

    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    input_payload = {
        "user_question": user_question,
        "boundary_id": boundary_id,
        "handoff_frame_id": handoff_frame_id,
        "absolute_info_count": len(boundary.absolute_info),
        "relative_info_count": len(boundary.relative_info),
        "mixed_info_count": len(boundary.mixed_info),
        "absolute_info_samples": _answer_basis_absolute_samples(
            boundary=boundary,
            evidence_ref_by_source_id=evidence_ref_by_source_id,
        ),
        "relative_info_samples": _answer_basis_semantic_samples(
            info_refs=boundary.relative_info[:12],
            evidence_ref_by_source_id=evidence_ref_by_source_id,
            info_class="relative",
        ),
        "mixed_info_samples": _answer_basis_semantic_samples(
            info_refs=boundary.mixed_info[:12],
            evidence_ref_by_source_id=evidence_ref_by_source_id,
            info_class="mixed",
        ),
        "available_evidence_sources": [
            {
                "evidence_ref": source["evidence_ref"],
                "source_label": source["source_label"],
                "source_kind": source["source_kind"],
                "material_channel": source.get("material_channel", "generic"),
                "material_preview": source.get("material_preview", ""),
            }
            for source in available_evidence_sources
        ],
        "answer_material_catalog": [
            {
                "evidence_ref": source["evidence_ref"],
                "source_label": source["source_label"],
                "source_kind": source["source_kind"],
                "material_channel": source.get("material_channel", "generic"),
                "material_preview": source.get("material_preview", ""),
            }
            for source in available_evidence_sources
            if source.get("material_channel") != "generic"
        ],
        "answer_basis_modes": [
            "absolute_first",
            "relative_allowed",
            "mixed_or_uncertain",
        ],
        "basis_reason_codes": [
            "code_verified_fact_required",
            "user_asked_for_interpretation",
            "multi_source_bundle",
            "source_mapping_unclear",
            "insufficient_grounding",
            "partial_evidence_only",
            "recent_conversation_basis_present",
            "document_basis_present",
            "runtime_state_basis_present",
            "llm_mode_selection_failed",
        ],
        "evidence_role_values": [
            "primary_answer_basis",
            "supporting_context",
            "available_but_not_used",
            "candidate_not_read",
            "excluded_by_budget",
            "failed_or_empty",
            "not_supplied",
        ],
        "role_reason_info_class_values": ["relative", "mixed"],
        "evidence_requirement_values": [
            "not_required",
            "optional",
            "required",
        ],
    }
    executor = LLMNodeExecutor(adapter)
    first_result = executor.run(
        node_id="node_2",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_ref,
        source_data_ids=base_source_data_ids,
        payload_validator=lambda payload: _validate_answer_basis_payload(
            payload,
            evidence_source_id_by_ref=evidence_source_id_by_ref,
            evidence_source_metadata_by_ref=evidence_source_metadata_by_ref,
        ),
    )
    attempt_results = [first_result]
    llm_result = first_result
    if _should_repair_answer_basis_schema_failure(first_result):
        repair_input_payload = _answer_basis_schema_repair_input_payload(
            base_payload=input_payload,
            failed_payload=first_result.validation.payload,
            failure_reason=first_result.validation.error,
        )
        llm_result = executor.run(
            node_id="node_2",
            prompt=prompt,
            input_payload=repair_input_payload,
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            prompt_ref=prompt_ref,
            input_ref=_unique_strings([*input_ref, first_result.trace_event_id]),
            source_data_ids=_unique_strings(
                [*base_source_data_ids, first_result.call_data_id]
            ),
            payload_validator=lambda payload: _validate_answer_basis_payload(
                payload,
                evidence_source_id_by_ref=evidence_source_id_by_ref,
                evidence_source_metadata_by_ref=evidence_source_metadata_by_ref,
            ),
        )
        attempt_results.append(llm_result)

    frame_source_trace_ids = _unique_strings(
        [
            *input_ref,
            *(result.trace_event_id for result in attempt_results),
        ]
    )
    frame_source_data_ids = _unique_strings(
        [
            *allowed_answer_basis_source_data_ids,
            *(result.call_data_id for result in attempt_results),
        ]
    )
    if llm_result.failure_type == "none" and llm_result.validation.payload is not None:
        payload = llm_result.validation.payload
        (
            task_contract_status,
            user_task_summary,
            fulfillment_requirements,
            evidence_requirement,
        ) = _answer_task_contract_fields(payload)
        frame = Node2AnswerBasisFrame(
            frame_id=frame_id,
            turn_id=turn_id,
            answer_basis_mode=str(payload.get("answer_basis_mode") or "").strip(),
            basis_reason_codes=_string_list(payload.get("basis_reason_codes")),
            mode_selection_reason=str(payload.get("mode_selection_reason") or "").strip(),
            mode_selection_reason_info_class=str(
                payload.get("mode_selection_reason_info_class") or "mixed"
            ).strip(),
            task_contract_status=task_contract_status,
            user_task_summary=user_task_summary,
            fulfillment_requirements=fulfillment_requirements,
            evidence_requirement=evidence_requirement,
            evidence_roles=_evidence_roles_from_payload(
                payload.get("evidence_roles"),
                evidence_source_id_by_ref=evidence_source_id_by_ref,
                evidence_source_metadata_by_ref=evidence_source_metadata_by_ref,
            ),
            generated_by=f"LLM:{llm_result.model_id}",
            info_class=str(payload.get("mode_selection_reason_info_class") or "mixed").strip(),
            semantic_judgement_status="ran",
            answer_basis_failure_type="none",
            answer_basis_llm_call_data_id=llm_result.call_data_id,
            answer_basis_trace_event_id=llm_result.trace_event_id,
            answer_basis_validation_error="",
            answer_basis_raw_text_present=bool(llm_result.raw_text),
            answer_basis_prompt_ref=prompt_ref,
            answer_basis_payload_parse_status=_answer_basis_payload_parse_status(llm_result.failure_type),
            source_trace_ids=_unique_strings(frame_source_trace_ids),
            source_data_ids=frame_source_data_ids,
        )
        validate_node2_answer_basis_frame(frame)
        return _record_answer_basis_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
            schema_status="passed",
        )

    frame = _fallback_answer_basis_frame(
        frame_id=frame_id,
        turn_id=turn_id,
        source_trace_ids=frame_source_trace_ids,
        source_data_ids=frame_source_data_ids,
        failure_type=llm_result.failure_type,
        llm_call_data_id=llm_result.call_data_id,
        trace_event_id=llm_result.trace_event_id,
        validation_error=_short_diagnostic_text(llm_result.validation.error or ""),
        raw_text_present=bool(llm_result.raw_text),
        prompt_ref=prompt_ref,
        payload_parse_status=_answer_basis_payload_parse_status(llm_result.failure_type),
    )
    return _record_answer_basis_frame(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
        schema_status="failed",
    )


def _answer_basis_available_evidence_sources(
    *,
    boundary: MetainfoBoundary,
    base_source_data_ids: list[str],
    data_store: DataStore,
    turn_id: str,
    handoff_frame_id: str,
) -> list[dict[str, object]]:
    """answer-basis LLM이 evidence role로 고를 수 있는 source ID 표를 만든다."""

    catalog_metadata = _answer_material_catalog_metadata(
        data_store=data_store,
        turn_id=turn_id,
        handoff_frame_id=handoff_frame_id,
    )
    candidate_ids = _unique_strings(
        [
            *base_source_data_ids,
            *(ref.data_id for ref in boundary.absolute_info[:16]),
            *(ref.source_data_id for ref in boundary.relative_info[:12]),
            *(ref.source_data_id for ref in boundary.mixed_info[:12]),
            *(str(item["source_data_id"]) for item in catalog_metadata),
        ]
    )
    metadata_by_source_id = {
        str(item["source_data_id"]): item
        for item in catalog_metadata
    }
    return [
        _answer_basis_source_row(
            evidence_ref=f"E{index:03d}",
            source_data_id=source_data_id,
            metadata=metadata_by_source_id.get(source_data_id),
        )
        for index, source_data_id in enumerate(candidate_ids, start=1)
    ]


def _answer_material_catalog_metadata(
    *,
    data_store: DataStore,
    turn_id: str,
    handoff_frame_id: str,
) -> list[dict[str, object]]:
    """최종 답변 재료와 작업 과정 장부를 record type 기준으로 분리한다."""

    rows: list[dict[str, object]] = []
    for record in data_store.list_records():
        payload = record.payload if isinstance(record.payload, dict) else {}
        payload_turn_id = str(payload.get("turn_id") or "").strip()
        if payload_turn_id and payload_turn_id != turn_id:
            continue
        metadata = _answer_material_record_metadata(
            data_id=record.data_id,
            data_type=record.data_type,
            payload=payload,
        )
        if metadata is not None:
            rows.append(metadata)

    # runtime task sequence 자체는 node_3 brief 조립 시 만들어진다. 여기서는 이미 존재하는
    # handoff frame을 그 과정 장부의 source anchor로 사용하고 새 의미 record를 만들지 않는다.
    rows.append(
        {
            "source_data_id": handoff_frame_id,
            "source_label": "현재 턴 실행 과정 장부",
            "source_kind": "runtime_task_sequence",
            "material_channel": "process",
            "material_preview": (
                "node_3 brief 생성 시점까지의 node/mode/status 실행 순서 자료. "
                "사용자가 실행 과정 자체를 물을 때만 답변 재료로 고른다."
            ),
        }
    )
    channel_order = {"answer_ready": 0, "status": 1, "process": 2}
    rows.sort(key=lambda item: channel_order.get(str(item["material_channel"]), 9))
    return rows[:ANSWER_MATERIAL_CATALOG_MAX_ITEMS]


def _answer_material_record_metadata(
    *,
    data_id: str,
    data_type: str,
    payload: dict[str, object],
) -> dict[str, object] | None:
    if data_type == "node_output:L3_per_document_summary_frame":
        document_name = str(payload.get("source_document_name") or "문서").strip()
        preview = _catalog_preview(
            payload.get("task_relevant_summary"),
            payload.get("plain_document_summary"),
        )
        return _catalog_row(
            data_id=data_id,
            label=f"L3 문서 요약: {document_name}",
            kind="l3_document_summary",
            channel="answer_ready",
            preview=preview,
        )
    if data_type in {"tool_result:read_doc", "tool_result:read_artifact"}:
        document_name = str(
            payload.get("doc_id") or payload.get("document_name") or "읽은 문서"
        ).strip()
        return _catalog_row(
            data_id=data_id,
            label=f"읽은 문서 원문: {document_name}",
            kind="read_document",
            channel="answer_ready",
            preview=_catalog_preview(payload.get("text")),
        )
    if data_type == "tool_result:read_code_file":
        file_path = str(payload.get("file_path") or "읽은 코드 파일").strip()
        return _catalog_row(
            data_id=data_id,
            label=f"읽은 코드 원문: {file_path}",
            kind="read_code_file",
            channel="answer_ready",
            preview=_catalog_preview(payload.get("text")),
        )
    if data_type == "node_output:selected_recent_memory_context_frame":
        items = payload.get("items") if isinstance(payload.get("items"), list) else []
        if not items:
            return None
        copied_text: list[object] = []
        for item in items[:2]:
            if isinstance(item, dict):
                copied_text.extend(
                    [item.get("raw_user_text"), item.get("raw_assistant_text")]
                )
        return _catalog_row(
            data_id=data_id,
            label="선택된 최근 대화 원문",
            kind="selected_recent_memory_context",
            channel="answer_ready",
            preview=_catalog_preview(*copied_text),
        )
    if data_type == "r_loop:vessel_step_memory_packet":
        candidate_records = (
            payload.get("visible_child_candidate_records")
            if isinstance(payload.get("visible_child_candidate_records"), list)
            else []
        )
        summary_previews = [
            item.get("summary_text_preview")
            for item in candidate_records[:6]
            if isinstance(item, dict) and item.get("summary_text_preview")
        ]
        return _catalog_row(
            data_id=data_id,
            label=f"Vessel R 단계 재료 {payload.get('step_index', '')}".strip(),
            kind="vessel_r_material",
            channel="answer_ready",
            preview=_catalog_preview(
                payload.get("selected_node_kind"),
                payload.get("r3_sufficiency_status"),
                *summary_previews,
            ),
        )
    if data_type == "node_output:l_loop_return_summary_frame":
        return _catalog_row(
            data_id=data_id,
            label="L loop 최종 상태",
            kind="l_loop_return_summary",
            channel="status",
            preview=_catalog_preview(
                f"task={payload.get('l_loop_task_status')}",
                f"acquisition={payload.get('evidence_acquisition_status')}",
                f"originals={payload.get('original_material_count')}",
                f"semantic={payload.get('l3_semantic_goal_match_status')}",
            ),
        )
    if data_type == "node_output:R_loop_return_summary_frame":
        return _catalog_row(
            data_id=data_id,
            label="R loop 최종 상태",
            kind="r_loop_return_summary",
            channel="status",
            preview=_catalog_preview(
                f"task={payload.get('r_loop_task_status')}",
                f"continuation={payload.get('continuation_status')}",
                f"budget={payload.get('budget_status')}",
            ),
        )
    if data_type == "r_loop:vessel_return_packet":
        return _catalog_row(
            data_id=data_id,
            label="Vessel R 반환 상태",
            kind="vessel_r_return_packet",
            channel="status",
            preview=_catalog_preview(
                f"return={payload.get('return_status')}",
                f"task={payload.get('r_loop_task_status')}",
                f"summaries={payload.get('summary_material_count')}",
                f"raw_originals={payload.get('raw_original_material_count')}",
            ),
        )
    if data_type == "node_output:document_context_pack_frame":
        included = (
            payload.get("included_documents")
            if isinstance(payload.get("included_documents"), list)
            else []
        )
        document_names = [
            item.get("document_name")
            for item in included[:10]
            if isinstance(item, dict)
        ]
        return _catalog_row(
            data_id=data_id,
            label="node_3 공급 문서 context 묶음",
            kind="document_context_pack",
            channel="status",
            preview=_catalog_preview(*document_names),
        )
    if data_type == "node_output:node0_document_material_packet_frame":
        return _catalog_row(
            data_id=data_id,
            label="문서 후보/read/supplied/excluded 장부",
            kind="document_material_packet",
            channel="process",
            preview=_catalog_preview(
                f"candidates={payload.get('search_candidate_count')}",
                f"read={payload.get('actual_tool_read_doc_count')}",
                f"supplied={payload.get('supplied_document_context_count')}",
                f"unread={payload.get('unread_candidate_count')}",
            ),
        )
    if data_type in {
        "node_output:L2_query_plan_frame",
        "node_output:L2_revision_query_plan_frame",
    }:
        candidates = (
            payload.get("candidates")
            if isinstance(payload.get("candidates"), list)
            else []
        )
        purposes = [
            item.get("purpose")
            for item in candidates[:6]
            if isinstance(item, dict)
        ]
        return _catalog_row(
            data_id=data_id,
            label="L2 검색 계획",
            kind="l2_query_plan",
            channel="process",
            preview=_catalog_preview(*purposes),
        )
    return None


def _catalog_row(
    *,
    data_id: str,
    label: str,
    kind: str,
    channel: str,
    preview: str,
) -> dict[str, object]:
    return {
        "source_data_id": data_id,
        "source_label": label,
        "source_kind": kind,
        "material_channel": channel,
        "material_preview": preview,
    }


def _catalog_preview(*values: object) -> str:
    compact = " | ".join(
        " ".join(str(value).split())
        for value in values
        if value is not None and str(value).strip()
    )
    if len(compact) <= ANSWER_MATERIAL_PREVIEW_MAX_CHARS:
        return compact
    return f"{compact[: ANSWER_MATERIAL_PREVIEW_MAX_CHARS - 3]}..."


def _answer_basis_source_row(
    *,
    evidence_ref: str,
    source_data_id: str,
    metadata: dict[str, object] | None,
) -> dict[str, object]:
    if metadata is None:
        return {
            "evidence_ref": evidence_ref,
            "source_data_id": source_data_id,
            "source_label": _answer_basis_source_label(source_data_id),
            "source_kind": _answer_basis_source_kind(source_data_id),
            "material_channel": _answer_basis_material_channel(source_data_id),
            "material_preview": "",
        }
    return {
        "evidence_ref": evidence_ref,
        "source_data_id": source_data_id,
        "source_label": str(metadata.get("source_label") or "공급된 근거 자료"),
        "source_kind": str(metadata.get("source_kind") or "supplied_source"),
        "material_channel": str(metadata.get("material_channel") or "generic"),
        "material_preview": str(metadata.get("material_preview") or ""),
    }


def _answer_basis_absolute_samples(
    *,
    boundary: MetainfoBoundary,
    evidence_ref_by_source_id: dict[str, str],
) -> list[dict[str, object]]:
    """절대정보 sample에서 raw ID를 빼고 code evidence ref만 남긴다."""

    samples: list[dict[str, object]] = []
    for data_ref in boundary.absolute_info[:16]:
        evidence_ref = evidence_ref_by_source_id.get(data_ref.data_id)
        if evidence_ref is None:
            continue
        samples.append(
            {
                "evidence_ref": evidence_ref,
                "source_label": _answer_basis_source_label(data_ref.data_id),
                "source_kind": _answer_basis_source_kind(data_ref.data_id),
                "exists": data_ref.exists,
            }
        )
    return samples


def _answer_basis_semantic_samples(
    *,
    info_refs: list[object],
    evidence_ref_by_source_id: dict[str, str],
    info_class: str,
) -> list[dict[str, object]]:
    """상대/혼합 sample은 의미 text와 ref만 보여주고 내부 info ID는 숨긴다."""

    samples: list[dict[str, object]] = []
    for info_ref in info_refs:
        source_data_id = getattr(info_ref, "source_data_id", None)
        if not isinstance(source_data_id, str):
            continue
        evidence_ref = evidence_ref_by_source_id.get(source_data_id)
        if evidence_ref is None:
            continue
        samples.append(
            {
                "evidence_ref": evidence_ref,
                "source_label": _answer_basis_source_label(source_data_id),
                "info_class": info_class,
                "info_kind": str(getattr(info_ref, "info_kind", "")),
                "field_path": str(getattr(info_ref, "field_path", "")),
                "text": str(getattr(info_ref, "text", "")),
            }
        )
    return samples


def _answer_basis_source_label(source_data_id: str) -> str:
    if "selected_recent_memory_context" in source_data_id:
        return "선택된 최근 기억"
    if "memory_relevance" in source_data_id:
        return "최근 기억 선택 판단"
    if "l_loop_return_summary" in source_data_id or "L:return_summary_frame" in source_data_id:
        return "L loop 반환 요약"
    if "read_doc" in source_data_id or "read_artifact" in source_data_id:
        return "읽은 문서"
    if "document_material_packet" in source_data_id:
        return "0 문서 장부"
    if "document_context_pack" in source_data_id:
        return "문서 context pack"
    if "L3" in source_data_id or "achievement" in source_data_id or "preserved" in source_data_id:
        return "L3 검색 성패 판단"
    if "route" in source_data_id:
        return "라우팅 결과"
    if "boundary" in source_data_id:
        return "메타정보 경계"
    if "handoff" in source_data_id:
        return "node_2 handoff"
    if "node2_input" in source_data_id:
        return "node_2 입력 프레임"
    return "공급된 근거 자료"


def _answer_basis_source_kind(source_data_id: str) -> str:
    if "selected_recent_memory_context" in source_data_id:
        return "selected_recent_memory_context"
    if "memory_relevance" in source_data_id:
        return "memory_relevance_selection"
    if "l_loop_return_summary" in source_data_id or "L:return_summary_frame" in source_data_id:
        return "l_loop_return_summary"
    if "read_doc" in source_data_id or "read_artifact" in source_data_id:
        return "read_document"
    if "document_material_packet" in source_data_id:
        return "document_material_packet"
    if "document_context_pack" in source_data_id:
        return "document_context_pack"
    if source_data_id.startswith("L2:"):
        return "l2_query_plan"
    if "L3" in source_data_id or "achievement" in source_data_id or "preserved" in source_data_id:
        return "l3_result"
    if "vessel" in source_data_id or source_data_id.startswith("R:"):
        return "vessel_r_material"
    if "task_ledger" in source_data_id:
        return "runtime_task_sequence"
    if "route" in source_data_id:
        return "route"
    if "boundary" in source_data_id:
        return "metainfo_boundary"
    if "handoff" in source_data_id:
        return "node2_handoff"
    if "node2_input" in source_data_id:
        return "node2_input"
    return "supplied_source"


def _answer_basis_material_channel(source_data_id: str) -> str:
    source_kind = _answer_basis_source_kind(source_data_id)
    if source_kind in {
        "read_document",
        "read_code_file",
    }:
        return "answer_ready"
    if source_kind in {"l_loop_return_summary"}:
        return "status"
    if source_kind in {
        "l2_query_plan",
        "document_material_packet",
        "runtime_task_sequence",
        "route",
        "node2_handoff",
    }:
        return "process"
    return "generic"


def _fallback_answer_basis_frame(
    *,
    frame_id: str,
    turn_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    failure_type: str,
    llm_call_data_id: str | None,
    trace_event_id: str | None,
    validation_error: str,
    raw_text_present: bool,
    prompt_ref: str,
    payload_parse_status: str,
) -> Node2AnswerBasisFrame:
    frame = Node2AnswerBasisFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        answer_basis_mode="mixed_or_uncertain",
        basis_reason_codes=["llm_mode_selection_failed"],
        mode_selection_reason="CODE_STATUS:node2_answer_basis_mode_selection_failed",
        mode_selection_reason_info_class="absolute_status",
        task_contract_status="failed",
        user_task_summary="",
        fulfillment_requirements=[],
        evidence_requirement="not_recorded",
        evidence_roles=[],
        generated_by="CODE:FALLBACK",
        info_class="absolute_status",
        semantic_judgement_status="failed",
        answer_basis_failure_type=failure_type,
        answer_basis_llm_call_data_id=llm_call_data_id,
        answer_basis_trace_event_id=trace_event_id,
        answer_basis_validation_error=validation_error,
        answer_basis_raw_text_present=raw_text_present,
        answer_basis_prompt_ref=prompt_ref,
        answer_basis_payload_parse_status=payload_parse_status,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )
    validate_node2_answer_basis_frame(frame)
    return frame


def _answer_basis_payload_parse_status(failure_type: str) -> str:
    if failure_type in {"none", "schema_failed"}:
        return "passed"
    if failure_type == "parse_failed":
        return "failed"
    return "not_checked"


def _short_diagnostic_text(text: str, *, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _record_answer_basis_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: Node2AnswerBasisFrame,
    schema_status: str,
) -> tuple[str, str, Node2AnswerBasisFrame]:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_2",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status=schema_status,
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type="node_output:node2_answer_basis_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def _validate_answer_basis_payload(
    payload: dict[str, object],
    *,
    evidence_source_id_by_ref: dict[str, str],
    evidence_source_metadata_by_ref: dict[str, dict[str, object]] | None = None,
) -> None:
    resolved_roles = _evidence_roles_from_payload(
        payload.get("evidence_roles"),
        evidence_source_id_by_ref=evidence_source_id_by_ref,
        evidence_source_metadata_by_ref=evidence_source_metadata_by_ref,
    )
    (
        task_contract_status,
        user_task_summary,
        fulfillment_requirements,
        evidence_requirement,
    ) = _answer_task_contract_fields(payload)
    frame = Node2AnswerBasisFrame(
        frame_id="validation_answer_basis",
        turn_id="validation_turn",
        answer_basis_mode=str(payload.get("answer_basis_mode") or "").strip(),
        basis_reason_codes=_string_list(payload.get("basis_reason_codes")),
        mode_selection_reason=str(payload.get("mode_selection_reason") or "").strip(),
        mode_selection_reason_info_class=str(
            payload.get("mode_selection_reason_info_class") or "mixed"
        ).strip(),
        task_contract_status=task_contract_status,
        user_task_summary=user_task_summary,
        fulfillment_requirements=fulfillment_requirements,
        evidence_requirement=evidence_requirement,
        evidence_roles=resolved_roles,
        generated_by="LLM:validation-model",
        info_class=str(payload.get("mode_selection_reason_info_class") or "mixed").strip(),
        semantic_judgement_status="ran",
        source_trace_ids=["validation_trace"],
        source_data_ids=_unique_strings(list(evidence_source_id_by_ref.values())),
    )
    validate_node2_answer_basis_frame(frame)


def _should_repair_answer_basis_schema_failure(result: object) -> bool:
    """parse된 JSON의 schema 계약만 실패했을 때 repair를 한 번 허용한다."""

    validation = getattr(result, "validation", None)
    return (
        getattr(result, "failure_type", None) == "schema_failed"
        and isinstance(getattr(validation, "payload", None), dict)
    )


def _answer_basis_schema_repair_input_payload(
    *,
    base_payload: dict[str, object],
    failed_payload: dict[str, object] | None,
    failure_reason: str | None,
) -> dict[str, object]:
    """의미를 고치지 않고 실패한 JSON 계약을 LLM이 다시 맞추도록 입력을 만든다."""

    payload = dict(base_payload)
    payload["schema_repair_request"] = {
        "repair_status": "requested",
        "max_repair_attempts": NODE2_ANSWER_BASIS_SCHEMA_REPAIR_MAX_ATTEMPTS,
        "repair_attempt_index": 1,
        "validation_error": failure_reason or "schema_failed",
        "failed_payload": failed_payload or {},
        "required_evidence_role_fields": [
            "evidence_ref",
            "evidence_role",
            "role_reason",
            "role_reason_info_class",
        ],
        "boundary": (
            "Repair the complete JSON object using only official evidence refs. "
            "Code still validates every field and does not choose semantic roles."
        ),
    }
    return payload


def _evidence_roles_from_payload(
    value: object,
    *,
    evidence_source_id_by_ref: dict[str, str],
    evidence_source_metadata_by_ref: dict[str, dict[str, object]] | None = None,
) -> list[Node2EvidenceRole]:
    if not isinstance(value, list):
        return []
    roles: list[Node2EvidenceRole] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        evidence_ref = str(item.get("evidence_ref") or "").strip()
        evidence_role = str(item.get("evidence_role") or "").strip()
        if not evidence_ref or not evidence_role:
            raise ValueError("Node2 evidence role requires evidence_ref and evidence_role")
        source_data_id = evidence_source_id_by_ref.get(evidence_ref)
        if source_data_id is None:
            raise ValueError("Node2 evidence_ref must exist in available_evidence_sources")
        metadata = (evidence_source_metadata_by_ref or {}).get(evidence_ref, {})
        roles.append(
            Node2EvidenceRole(
                source_data_id=source_data_id,
                evidence_role=evidence_role,
                role_reason=str(item.get("role_reason") or "").strip(),
                role_reason_info_class=str(
                    item.get("role_reason_info_class") or "mixed"
                ).strip(),
                source_label=str(metadata.get("source_label") or ""),
                source_kind=str(metadata.get("source_kind") or ""),
                material_channel=str(metadata.get("material_channel") or ""),
            )
        )
    return roles


def _answer_task_contract_fields(
    payload: dict[str, object],
) -> tuple[str, str, list[str], str]:
    """새 task contract field가 전혀 없으면 구형 adapter 입력으로 투명하게 기록한다."""

    keys = {
        "user_task_summary",
        "fulfillment_requirements",
        "evidence_requirement",
    }
    if not any(key in payload for key in keys):
        return "not_recorded", "", [], "not_recorded"
    return (
        "recorded",
        str(payload.get("user_task_summary") or "").strip(),
        _string_list(payload.get("fulfillment_requirements")),
        str(payload.get("evidence_requirement") or "").strip(),
    )


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
