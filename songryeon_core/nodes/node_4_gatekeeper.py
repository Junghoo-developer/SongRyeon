from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    Node3InputBriefFrame,
    Node4GatekeeperFrame,
    validate_node4_gatekeeper_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload


NODE4_GATEKEEPER_FRAME_DATA_ID = "node_4:gatekeeper_frame"


def run_node4_gatekeeper(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    report_id: str,
    boundary_id: str,
    brief_frame: Node3InputBriefFrame,
    rendered_markdown: str,
    adapter: LLMAdapter,
    input_ref: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None = None,
) -> str:
    """node_4가 node_3 브리프와 최종 보고문 사이의 근거 이탈을 검사한다."""

    gatekeeper_frame_id = (
        id_namespace.node4_gatekeeper_frame_id()
        if id_namespace is not None
        else NODE4_GATEKEEPER_FRAME_DATA_ID
    )
    prompt_ref = "songryeon_core/prompts/node_4_gatekeeper_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="node_4",
        prompt=prompt,
        input_payload={
            "rendered_markdown": rendered_markdown[:5000],
            "node3_input_brief": node3_brief_llm_payload(brief_frame),
            "checks": [
                "보고문이 node3_input_brief 밖의 사실을 단정했는지 확인한다.",
                "보고문이 '근거 기준:' 블록으로 시작하고 count가 brief와 맞는지 확인한다.",
                "검색 후보 문서를 읽은 문서처럼 말하는지 확인한다.",
                "문서 추출이 있는데 없다고 말하는 모순이 있는지 확인한다.",
                "내부 추적용 식별자나 장부용 필드명이 노출됐는지 확인한다.",
            ],
        },
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_ref,
        source_data_ids=source_data_ids,
        payload_validator=_validate_gatekeeper_payload,
    )
    if llm_result.failure_type == "none" and llm_result.validation.payload is not None:
        payload = llm_result.validation.payload
        gate_status = str(payload.get("gate_status") or "").strip()
        reason = str(payload.get("reason") or "").strip()
        checked_claims = _string_list(payload.get("checked_claims"))
        unsupported_claims = _string_list(payload.get("unsupported_claims"))
        contradictions = _string_list(payload.get("contradictions"))
        revision_targets = _string_list(payload.get("revision_targets"))
        llm_gate_status = "ran"
    else:
        gate_status = "failed"
        reason = f"node_4 LLM gatekeeper failed: {llm_result.failure_type}"
        checked_claims = []
        unsupported_claims = []
        contradictions = []
        revision_targets = [reason]
        llm_gate_status = "failed"

    # CODE 권한: 숫자 불일치 같은 절대 검사는 LLM 의미 판단을 기다리지 않고 차단한다.
    # 단, 이것은 의미 검사가 아니라 node3_input_brief와 보고문 첫 근거 블록의 산술 일치 검사다.
    code_count_violations = _grounding_count_violations(
        rendered_markdown=rendered_markdown,
        brief_frame=brief_frame,
    )
    gate_generation_source = f"LLM:{llm_result.model_id}"
    if code_count_violations:
        if gate_status == "pass":
            gate_status = "needs_revision"
        gate_generation_source = f"{gate_generation_source}+CODE:GROUNDING_COUNT_GUARD"
        reason = _append_reason(
            reason,
            "CODE_STATUS:grounding_count_mismatch",
        )
        checked_claims = _unique_strings([*checked_claims, "grounding_count_block"])
        contradictions = _unique_strings([*contradictions, *code_count_violations])
        revision_targets = _unique_strings(
            [
                *revision_targets,
                "근거 기준 블록의 count를 node3_input_brief와 일치시킨다.",
            ]
        )

    frame_source_trace_ids = list(input_ref)
    if llm_result.trace_event_id:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = _unique_strings(
        [*source_data_ids, report_id, brief_frame.frame_id, boundary_id, llm_result.call_data_id]
    )
    frame = Node4GatekeeperFrame(
        gate_id=gatekeeper_frame_id,
        turn_id=turn_id,
        report_id=report_id,
        boundary_id=boundary_id,
        gate_status=gate_status,
        reason=reason,
        gate_generation_source=gate_generation_source,
        llm_gate_status=llm_gate_status,
        checked_claims=checked_claims,
        unsupported_claims=unsupported_claims,
        contradictions=contradictions,
        revision_targets=revision_targets,
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=frame_source_data_ids,
    )
    validate_node4_gatekeeper_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_4",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[gatekeeper_frame_id],
        schema_status="passed" if gate_status == "pass" else "failed",
    )
    data_store.create_record(
        data_id=gatekeeper_frame_id,
        data_type="node_output:node4_gatekeeper_frame",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id


def _grounding_count_violations(
    *,
    rendered_markdown: str,
    brief_frame: Node3InputBriefFrame,
) -> list[str]:
    """node_3 보고문 첫 근거 블록의 숫자가 brief의 절대 count와 맞는지 검사한다."""

    # 장기 과제: 현재는 한국어 고정 문구를 정규식으로 읽는 v0 가드다.
    # 장기적으로는 node_3가 ReportGroundingFrame 같은 구조화 출력을 함께 만들고,
    # node_4는 렌더링된 문장 대신 그 frame을 검사하는 쪽이 더 건강하다.
    expected_counts = {
        "읽은 문서": len(brief_frame.read_documents),
        "검색 후보 문서": brief_frame.search_candidate_count,
        "현재 턴 실행 순서 자료": len(brief_frame.runtime_tasks),
    }
    if not rendered_markdown.startswith("근거 기준:"):
        return ["grounding_block_missing_or_not_first_line"]

    violations: list[str] = []
    for label, expected_count in expected_counts.items():
        actual_count = _grounding_count(rendered_markdown, label)
        if actual_count is None:
            violations.append(f"{label}:missing_expected_{expected_count}")
            continue
        if actual_count != expected_count:
            violations.append(
                f"{label}:actual_{actual_count}_expected_{expected_count}"
            )
    return violations


def _grounding_count(rendered_markdown: str, label: str) -> int | None:
    pattern = rf"^-\s*{re.escape(label)}\s*:\s*(\d+)\s*개\s*$"
    match = re.search(pattern, rendered_markdown, flags=re.MULTILINE)
    if match is None:
        return None
    return int(match.group(1))


def _append_reason(reason: str, addition: str) -> str:
    if not reason:
        return addition
    if addition in reason:
        return reason
    return f"{reason} | {addition}"


def _validate_gatekeeper_payload(payload: dict[str, object]) -> None:
    frame = Node4GatekeeperFrame(
        gate_id=NODE4_GATEKEEPER_FRAME_DATA_ID,
        turn_id="validation_turn",
        report_id="validation_report",
        boundary_id="validation_boundary",
        gate_status=str(payload.get("gate_status") or "").strip(),
        reason=str(payload.get("reason") or "").strip(),
        gate_generation_source="LLM:validation-model",
        llm_gate_status="ran",
        checked_claims=_string_list(payload.get("checked_claims")),
        unsupported_claims=_string_list(payload.get("unsupported_claims")),
        contradictions=_string_list(payload.get("contradictions")),
        revision_targets=_string_list(payload.get("revision_targets")),
        source_trace_ids=["validation_trace"],
        source_data_ids=["validation_data"],
    )
    validate_node4_gatekeeper_frame(frame)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
