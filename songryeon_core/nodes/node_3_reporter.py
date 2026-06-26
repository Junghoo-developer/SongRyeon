from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    MetainfoBoundary,
    Node3InputBriefFrame,
    ReportFrame,
    validate_report_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor
from songryeon_core.nodes.node_2_handoff import node3_brief_llm_payload


@dataclass
class ReportDraft:
    rendered_markdown: str
    generation_source: str
    llm_reporter_status: str
    source_trace_ids: list[str]
    source_data_ids: list[str]


def render_report(
    *,
    turn_id: str,
    boundary: MetainfoBoundary,
) -> str:
    """2번이 허용한 절대정보와 근거 달린 의미 정보만 사용해 보고서를 만든다."""

    lines = [
        "# Dry Run Report",
        "",
        f"- turn_id: `{turn_id}`",
        f"- absolute_info_count: `{len(boundary.absolute_info)}`",
        f"- relative_info_count: `{len(boundary.relative_info)}`",
        f"- mixed_info_count: `{len(boundary.mixed_info)}`",
        "",
        "## Absolute Info",
    ]

    for data_ref in boundary.absolute_info:
        lines.append(
            f"- `{data_ref.data_id}` / `{data_ref.data_type}` / exists={data_ref.exists}"
        )

    lines.extend(["", "## Relative Info"])
    if not boundary.relative_info:
        lines.append("- none")
    for info_ref in boundary.relative_info:
        lines.append(
            f"- `{info_ref.info_id}` / `{info_ref.info_kind}` / "
            f"source=`{info_ref.source_data_id}` / field=`{info_ref.field_path}` / "
            f"source_mode=`{info_ref.source_mode}`"
        )
        lines.append(f"  - text: {info_ref.text}")
        lines.append(
            f"  - evidence: traces={len(info_ref.source_trace_ids)}, "
            f"data={len(info_ref.source_data_ids)}"
        )

    lines.extend(["", "## Mixed Info"])
    if not boundary.mixed_info:
        lines.append("- none")
    for info_ref in boundary.mixed_info:
        lines.append(
            f"- `{info_ref.info_id}` / `{info_ref.info_kind}` / "
            f"source=`{info_ref.source_data_id}` / field=`{info_ref.field_path}` / "
            f"source_mode=`{info_ref.source_mode}`"
        )
        lines.append(f"  - text: {info_ref.text}")
        lines.append(
            f"  - evidence: traces={len(info_ref.source_trace_ids)}, "
            f"data={len(info_ref.source_data_ids)}"
        )

    lines.extend(
        [
            "",
            "## Note",
            "이 보고서는 2가 허용한 절대정보와 출처가 확인된 상대/혼합 정보만 출력한다. 출처 없는 판단문은 보고하지 않는다.",
        ]
    )
    return "\n".join(lines)


def render_report_with_llm(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    brief_frame: Node3InputBriefFrame,
    adapter: LLMAdapter,
    input_ref: list[str],
    source_data_ids: list[str],
) -> ReportDraft:
    """node_3 LLM reporter가 내부 ID를 제거한 브리프만 보고 최종 답변을 만든다."""

    prompt_ref = "songryeon_core/prompts/node_3_reporter_v0.md"
    prompt = Path(prompt_ref).read_text(encoding="utf-8")
    input_payload = node3_brief_llm_payload(brief_frame)
    input_payload["code_supplied_grounding_block"] = build_node3_grounding_block(brief_frame)
    input_payload["report_assembly_policy"] = (
        "CODE will prepend code_supplied_grounding_block. "
        "node_3 must return only body_markdown and must not write the grounding block or counts."
    )
    llm_result = LLMNodeExecutor(adapter).run(
        node_id="node_3",
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=prompt_ref,
        input_ref=input_ref,
        source_data_ids=source_data_ids,
        payload_validator=_validate_reporter_payload,
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        raise ValueError(f"node_3 LLM reporter failed: {llm_result.failure_type}")

    body_markdown = _report_body_from_payload(llm_result.validation.payload)
    rendered_markdown = assemble_node3_report_markdown(
        brief_frame=brief_frame,
        body_markdown=body_markdown,
    )
    frame_source_trace_ids = list(input_ref)
    if llm_result.trace_event_id:
        frame_source_trace_ids.append(llm_result.trace_event_id)
    frame_source_data_ids = _unique_strings([*source_data_ids, brief_frame.frame_id, llm_result.call_data_id])
    return ReportDraft(
        rendered_markdown=rendered_markdown,
        generation_source=f"LLM:{llm_result.model_id}",
        llm_reporter_status="ran",
        source_trace_ids=_unique_strings(frame_source_trace_ids),
        source_data_ids=frame_source_data_ids,
    )


def build_node3_grounding_block(brief_frame: Node3InputBriefFrame) -> str:
    """Node3InputBriefFrame의 절대 count로 사용자-facing grounding block을 만든다."""

    return "\n".join(
        [
            "근거 기준:",
            f"- 읽은 문서: {len(brief_frame.read_documents)}개",
            f"- 검색 후보 문서: {brief_frame.search_candidate_count}개",
            f"- 현재 턴 실행 순서 자료: {len(brief_frame.runtime_tasks)}개",
            f"- 답변 한계: {_grounding_limit_text(brief_frame)}",
        ]
    )


def assemble_node3_report_markdown(
    *,
    brief_frame: Node3InputBriefFrame,
    body_markdown: str,
) -> str:
    """CODE count block과 LLM 본문을 합쳐 최종 node_3 보고문을 만든다."""

    return f"{build_node3_grounding_block(brief_frame)}\n\n{body_markdown.strip()}"


def record_report(
    *,
    trace_store: TraceStore,
    data_store: DataStore | None = None,
    turn_id: str,
    report_id: str,
    rendered_markdown: str | None = None,
    allowed_info_ids: list[str] | None = None,
    allowed_relative_info_ids: list[str] | None = None,
    allowed_mixed_info_ids: list[str] | None = None,
    input_ref: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    report_generation_source: str = "CODE/RENDERER",
    llm_reporter_status: str = "not_run",
) -> str:
    """3번 보고관이 보고서를 만들었다는 사실을 trace로 기록한다."""

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_3",
        event_type="node_output",
        input_ref=input_ref or [],
        output_ref=[report_id],
        schema_status="not_checked",
    )
    if data_store is not None:
        frame = ReportFrame(
            report_id=report_id,
            turn_id=turn_id,
            rendered_markdown=rendered_markdown or "",
            allowed_info_ids=allowed_info_ids or [],
            allowed_relative_info_ids=allowed_relative_info_ids or [],
            allowed_mixed_info_ids=allowed_mixed_info_ids or [],
            source_trace_ids=input_ref or [],
            source_data_ids=source_data_ids or [],
            report_generation_source=report_generation_source,
            llm_reporter_status=llm_reporter_status,
        )
        validate_report_frame(frame)
        data_store.create_record(
            data_id=report_id,
            data_type="node_output:report",
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            payload=asdict(frame),
        )
    return event.event_id


def _validate_reporter_payload(payload: dict[str, object]) -> None:
    _report_body_from_payload(payload)


def _report_body_from_payload(payload: dict[str, object]) -> str:
    body = payload.get("body_markdown")
    if isinstance(body, str) and body.strip():
        return _strip_accidental_grounding_block(body)

    legacy_markdown = payload.get("rendered_markdown")
    if isinstance(legacy_markdown, str) and legacy_markdown.strip():
        stripped = _strip_accidental_grounding_block(legacy_markdown)
        if stripped:
            return stripped

    raise ValueError("node_3 body_markdown must not be empty")


def _strip_accidental_grounding_block(markdown: str) -> str:
    stripped = markdown.strip()
    if not stripped.startswith("근거 기준:"):
        return stripped

    lines = stripped.splitlines()
    index = 1
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            break
        if line.lstrip().startswith("-"):
            index += 1
            continue
        break
    return "\n".join(lines[index:]).strip()


def _grounding_limit_text(brief_frame: Node3InputBriefFrame) -> str:
    if brief_frame.insufficiency_reasons:
        return "자료 부족 신호가 있어 제공된 문서/허용 주장/현재 턴 실행 순서 자료 범위 안에서만 답한다."
    return "제공된 문서/허용 주장/현재 턴 실행 순서 자료 범위 안에서만 답한다. 검색 후보는 읽은 문서가 아니다."


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
