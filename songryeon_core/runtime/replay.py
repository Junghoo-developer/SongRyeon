from __future__ import annotations

import json
from pathlib import Path


def replay_run(run_dir: str | Path) -> str:
    """export된 trace/data 산출물을 사람이 읽기 좋은 텍스트로 재생한다."""

    root = Path(run_dir)
    trace_path = root / "trace.json"
    data_path = root / "data.json"
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    data_records = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else []
    data_index = {record["data_id"]: record for record in data_records}

    summary = _summarize_records(data_records)
    lines = [
        "# Trace Replay",
        "",
        "## Run Summary",
        f"- trace_count: {len(traces)}",
        f"- data_record_count: {len(data_records)}",
        f"- llm_call_count: {summary['llm_call_count']}",
        f"- tool_choice_count: {summary['tool_choice_count']}",
        f"- tool_result_count: {summary['tool_result_count']}",
        f"- controller_decision_count: {summary['controller_decision_count']}",
        f"- final_controller_decision: {summary['final_controller_decision']}",
        "",
        "## Event Flow",
    ]

    for event in traces:
        lines.append("")
        lines.append(f"- {event['event_id']} | {event['actor']} | {event['event_type']}")
        if event.get("input_ref"):
            lines.append(f"  input: {', '.join(event['input_ref'])}")
        if event.get("output_ref"):
            lines.append(f"  output: {', '.join(event['output_ref'])}")
            for data_id in event["output_ref"]:
                record = data_index.get(data_id)
                if record is None:
                    continue
                lines.extend(_describe_record(record))
    return "\n".join(lines)


def _summarize_records(data_records: list[dict[str, object]]) -> dict[str, object]:
    llm_call_count = 0
    tool_choice_count = 0
    tool_result_count = 0
    controller_decisions: list[str] = []

    for record in data_records:
        data_type = str(record.get("data_type") or "")
        payload = record.get("payload")
        if data_type == "llm_call":
            llm_call_count += 1
        if data_type == "tool_choice":
            tool_choice_count += 1
        if data_type.startswith("tool_result:"):
            tool_result_count += 1
        if isinstance(payload, dict) and payload.get("schema_name") == "LLoopControlFrame":
            decision = payload.get("decision")
            if isinstance(decision, str):
                controller_decisions.append(decision)

    return {
        "llm_call_count": llm_call_count,
        "tool_choice_count": tool_choice_count,
        "tool_result_count": tool_result_count,
        "controller_decision_count": len(controller_decisions),
        "final_controller_decision": controller_decisions[-1] if controller_decisions else "none",
    }


def _describe_record(record: dict[str, object]) -> list[str]:
    data_type = str(record.get("data_type") or "")
    payload = record.get("payload")
    schema_name = payload.get("schema_name") if isinstance(payload, dict) else None
    lines = [f"  data: {record['data_type']} schema={schema_name}"]
    if not isinstance(payload, dict):
        return lines

    if data_type == "llm_call":
        lines.append(
            "  llm_call: "
            f"node={payload.get('node_id')} model={payload.get('model_id')} "
            f"failure={payload.get('failure_type')} retry={payload.get('retry_count')}"
        )
    elif data_type == "tool_choice":
        lines.append(
            "  tool_choice: "
            f"{payload.get('chooser_node_id')} -> {payload.get('tool_name')} "
            f"catalog={payload.get('catalog_id')}"
        )
    elif data_type.startswith("tool_result:search_docs"):
        lines.append(
            "  tool_result.search_docs: "
            f"query={_short(payload.get('query'))} "
            f"result_count={payload.get('result_count')} "
            f"cache_status={payload.get('cache_status')}"
        )
    elif data_type.startswith("tool_result:read_doc") or data_type.startswith("tool_result:read_artifact"):
        label = "read_artifact" if data_type.startswith("tool_result:read_artifact") else "read_doc"
        lines.append(
            f"  tool_result.{label}: "
            f"doc_id={payload.get('doc_id')} char_count={payload.get('char_count')}"
        )
    elif data_type.startswith("tool_result_distillation:"):
        lines.append(
            "  distillation: "
            f"tool={payload.get('tool_name')} items={len(payload.get('items') or [])} "
            f"bytes={payload.get('original_payload_bytes')}->{payload.get('distilled_content_bytes')}"
        )
    elif data_type == "tool_use_budget":
        lines.append(
            "  budget: "
            f"stop_reason={payload.get('stop_reason')} "
            f"tool_calls={payload.get('tool_call_count')}/{payload.get('max_tool_calls')} "
            f"query_attempts={payload.get('query_count')}/{payload.get('max_query_attempts')} "
            f"search_top_k={payload.get('search_top_k')} "
            f"read_docs={payload.get('read_doc_count')}/{payload.get('max_read_doc_calls')}"
        )
        cache_statuses = payload.get("cache_statuses")
        if isinstance(cache_statuses, list) and cache_statuses:
            last_cache = cache_statuses[-1]
            if isinstance(last_cache, dict):
                lines.append(
                    "  budget.cache: "
                    f"{last_cache.get('cache_status')} query={_short(last_cache.get('query_text'))}"
                )
    elif schema_name == "LLoopControlFrame":
        lines.append(
            "  controller: "
            f"decision={payload.get('decision')} tool={payload.get('selected_tool_name')} "
            f"query={_short(payload.get('query_text'))} doc_id={payload.get('doc_id')} "
            f"tool_calls={payload.get('tool_call_count')}/{payload.get('max_tool_calls')}"
        )
    elif schema_name == "L2QueryPlanFrame":
        lines.append(
            "  l2_query_plan: "
            f"selected={payload.get('selected_candidate_id')} "
            f"candidates={len(payload.get('candidates') or [])}"
        )
    elif schema_name == "L2QueryFrame":
        lines.append(
            "  l2_query: "
            f"source={payload.get('query_source')} query={_short(payload.get('query_text'))}"
        )
    elif schema_name == "L3AchievementFrame":
        lines.append(
            "  l3_achievement: "
            f"status={payload.get('achievement_status')} "
            f"controller={payload.get('controller_decision')} "
            f"candidates={payload.get('candidate_count')}"
        )
    return lines


def _short(value: object, max_chars: int = 60) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
