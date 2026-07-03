from __future__ import annotations

"""Night-government worker for one token-budget summary layer bundle."""

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    GRAPH_MEMORY_CODE_GENERATOR,
    GraphMemoryEdgeFrame,
    GraphMemoryNodeFrame,
    validate_graph_memory_edge_frame,
    validate_graph_memory_node_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.llm.base import LLMAdapter
from songryeon_core.llm.node_executor import LLMNodeExecutor


NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID = "night_summarize_token_budget_bundle"
NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_PROMPT_REF = (
    "songryeon_core/prompts/night_summarize_token_budget_bundle_v0.md"
)
NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_FRAME_DATA_TYPE = (
    "node_output:night_summarize_token_budget_bundle_frame"
)
TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_DATA_TYPE = (
    "graph_memory:node:token_budget_summary_bundle"
)
TOKEN_BUDGET_SUMMARY_BUNDLE_POLICY_ID = "TOKEN_BUDGET_SUMMARY_LAYER_V0"
TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND = "token_budget_summary_bundle"
TOKEN_BUDGET_SUMMARY_NODE_DATA_KIND = "token_budget_bundle_summary"
TOKEN_BUDGET_SUMMARY_BUNDLE_DATA_KIND = "token_budget_summary_bundle"


@dataclass(frozen=True)
class TokenBudgetSummaryBundleSpec:
    bundle_index: int
    bundle_graph_node_id: str
    source_summary_graph_node_ids: list[str]
    source_summary_char_count: int
    char_budget: int
    char_budget_status: str


@dataclass(frozen=True)
class NightTokenBudgetBundleSummaryFrame:
    frame_id: str
    summary_graph_node_id: str
    target_graph_node_id: str
    target_node_kind: str
    summary_text: str = ""
    summary_status: str = "ran"
    failure_type: str = "none"
    payload_parse_status: str = "passed"
    node_kind: str = "summary"
    data_kind: str = TOKEN_BUDGET_SUMMARY_NODE_DATA_KIND
    summary_depth: int = 2
    source_depth_min: int = 1
    source_depth_max: int = 1
    source_leaf_count: int = 0
    source_summary_count: int = 0
    source_bundle_kind: str = TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND
    char_budget: int = 0
    input_summary_char_count: int = 0
    validity_status: str = "active"
    review_status: str = "not_reviewed"
    llm_call_data_id: str | None = None
    llm_trace_event_id: str | None = None
    prompt_ref: str = NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_PROMPT_REF
    source_mode: str = "source_bundle"
    claim_alignment: str = "multi_source_bundle"
    source_graph_node_ids: list[str] | None = None
    source_trace_ids: list[str] | None = None
    source_data_ids: list[str] | None = None
    generated_by: str = "LLM:unknown:night_summarize_token_budget_bundle"
    info_class: str = "mixed"
    semantic_judgement_status: str = "ran"
    schema_name: str = "NightTokenBudgetBundleSummaryFrame"
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_graph_node_ids", self.source_graph_node_ids or [])
        object.__setattr__(self, "source_trace_ids", self.source_trace_ids or [])
        object.__setattr__(self, "source_data_ids", self.source_data_ids or [])


@dataclass(frozen=True)
class RecordedNightTokenBudgetBundleSummaryResult:
    frame: NightTokenBudgetBundleSummaryFrame
    trace_event_id: str
    frame_data_id: str
    target_bundle_graph_node_id: str
    summary_graph_node_data_id: str | None
    summary_edge_data_id: str | None
    bundle_edge_data_ids: list[str]
    created_data_ids: list[str]
    existing_data_ids: list[str]


def collect_active_source_leaf_summary_graph_node_ids(
    data_store: DataStore,
) -> list[str]:
    """Return active source leaf summary graph nodes in deterministic order."""

    items: list[tuple[str, str, str]] = []
    for record in data_store.list_records():
        if record.data_type != "graph_memory:node:summary":
            continue
        if not isinstance(record.payload, dict):
            continue
        payload = record.payload
        if payload.get("data_kind") != "source_leaf_summary":
            continue
        if payload.get("summary_status") != "ran":
            continue
        if payload.get("validity_status") != "active":
            continue
        path = _text(payload.get("source_path"))
        source_kind = _text(payload.get("source_kind"))
        items.append((source_kind, path, record.data_id))
    return [data_id for _, _, data_id in sorted(items)]


def build_token_budget_summary_bundle_specs(
    *,
    data_store: DataStore,
    summary_run_id: str,
    source_summary_graph_node_ids: list[str],
    max_bundle_chars: int,
) -> list[TokenBudgetSummaryBundleSpec]:
    """Group summary nodes without splitting any individual summary text."""

    if max_bundle_chars <= 0:
        raise ValueError("max_bundle_chars must be positive")
    specs: list[TokenBudgetSummaryBundleSpec] = []
    current_ids: list[str] = []
    current_chars = 0

    def flush(*, forced_status: str | None = None) -> None:
        nonlocal current_ids, current_chars
        if not current_ids:
            return
        bundle_index = len(specs) + 1
        status = forced_status or (
            "within_budget"
            if current_chars <= max_bundle_chars
            else "single_item_exceeds_budget"
        )
        specs.append(
            TokenBudgetSummaryBundleSpec(
                bundle_index=bundle_index,
                bundle_graph_node_id=token_budget_summary_bundle_graph_node_id(
                    summary_run_id,
                    bundle_index=bundle_index,
                ),
                source_summary_graph_node_ids=list(current_ids),
                source_summary_char_count=current_chars,
                char_budget=max_bundle_chars,
                char_budget_status=status,
            )
        )
        current_ids = []
        current_chars = 0

    for source_summary_graph_node_id in source_summary_graph_node_ids:
        payload = _require_summary_payload(
            data_store=data_store,
            summary_graph_node_id=source_summary_graph_node_id,
        )
        summary_chars = len(_text(payload.get("summary_text")))
        if summary_chars > max_bundle_chars:
            flush()
            current_ids = [source_summary_graph_node_id]
            current_chars = summary_chars
            flush(forced_status="single_item_exceeds_budget")
            continue
        if current_ids and current_chars + summary_chars > max_bundle_chars:
            flush()
        current_ids.append(source_summary_graph_node_id)
        current_chars += summary_chars
    flush()
    return specs


def token_budget_summary_bundle_graph_node_id(
    summary_run_id: str,
    *,
    bundle_index: int,
) -> str:
    _require_text("summary_run_id", summary_run_id)
    if bundle_index <= 0:
        raise ValueError("bundle_index must be positive")
    return (
        "graph:token_budget_summary_bundle:"
        f"{_safe_id_part(summary_run_id)}:{bundle_index:04d}"
    )


def night_summarize_token_budget_bundle_frame_id(
    target_bundle_graph_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("target_bundle_graph_node_id", target_bundle_graph_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "night_summary:token_budget_bundle:"
        f"{_stable_suffix(target_bundle_graph_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def night_summarize_token_budget_bundle_graph_node_id(
    target_bundle_graph_node_id: str,
    *,
    summary_run_id: str,
) -> str:
    _require_text("target_bundle_graph_node_id", target_bundle_graph_node_id)
    _require_text("summary_run_id", summary_run_id)
    return (
        "graph:summary:token_budget_bundle:"
        f"{_stable_suffix(target_bundle_graph_node_id)}:{_safe_id_part(summary_run_id)}"
    )


def record_token_budget_summary_bundle_node(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    spec: TokenBudgetSummaryBundleSpec,
) -> tuple[GraphMemoryNodeFrame, str, list[str], list[str], list[str]]:
    """Record one code-generated bundle node and its CONTAINS edges."""

    source_payloads = [
        _require_summary_payload(data_store=data_store, summary_graph_node_id=data_id)
        for data_id in spec.source_summary_graph_node_ids
    ]
    source_trace_ids = _unique_strings(
        [
            trace_id
            for payload in source_payloads
            for trace_id in _string_list(payload.get("source_trace_ids"))
        ]
    )
    source_data_ids = _unique_strings(
        [
            *spec.source_summary_graph_node_ids,
            *[
                data_id
                for payload in source_payloads
                for data_id in _string_list(payload.get("source_data_ids"))
            ],
        ]
    )
    node = GraphMemoryNodeFrame(
        node_id=spec.bundle_graph_node_id,
        node_kind=TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND,
        data_kind=TOKEN_BUDGET_SUMMARY_BUNDLE_DATA_KIND,
        summary_depth=max([_int(payload.get("summary_depth")) for payload in source_payloads] or [1]),
        source_depth_min=min(
            [_int(payload.get("source_depth_min")) for payload in source_payloads] or [0]
        ),
        source_depth_max=max(
            [_int(payload.get("summary_depth")) for payload in source_payloads] or [1]
        ),
        source_leaf_count=sum(_int(payload.get("source_leaf_count")) for payload in source_payloads),
        source_summary_count=sum(
            _int(payload.get("source_summary_count")) + 1 for payload in source_payloads
        ),
        source_bundle_kind=TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND,
        bundle_policy_id=TOKEN_BUDGET_SUMMARY_BUNDLE_POLICY_ID,
        char_budget=spec.char_budget,
        source_char_count=spec.source_summary_char_count,
        char_budget_status=spec.char_budget_status,
        source_graph_node_ids=list(spec.source_summary_graph_node_ids),
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=GRAPH_MEMORY_CODE_GENERATOR,
        info_class="absolute",
        semantic_judgement_status="not_run",
    )
    validate_graph_memory_node_frame(node)
    edges = [_contains_edge(node, child_id) for child_id in spec.source_summary_graph_node_ids]
    for edge in edges:
        validate_graph_memory_edge_frame(edge)

    event = trace_store.create_event(
        turn_id=turn_id,
        actor="night_token_budget_summary_bundle_builder",
        event_type="node_output",
        input_ref=source_trace_ids,
        output_ref=[node.node_id, *[edge.edge_id for edge in edges]],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=node.node_id,
        data_type=TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_DATA_TYPE,
        payload=asdict(node),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    for edge in edges:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=edge.edge_id,
            data_type=f"graph_memory:edge:{edge.edge_kind}",
            payload=asdict(edge),
            created_at=event.timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    return (
        node,
        event.event_id,
        [edge.edge_id for edge in edges],
        created_data_ids,
        existing_data_ids,
    )


def run_night_summarize_token_budget_bundle(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    spec: TokenBudgetSummaryBundleSpec,
    summary_run_id: str,
    adapter: LLMAdapter | None,
    max_retries: int = 0,
) -> RecordedNightTokenBudgetBundleSummaryResult:
    bundle_node, bundle_trace_id, bundle_edge_ids, created_ids, existing_ids = (
        record_token_budget_summary_bundle_node(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            spec=spec,
        )
    )
    frame_id = night_summarize_token_budget_bundle_frame_id(
        bundle_node.node_id,
        summary_run_id=summary_run_id,
    )
    summary_graph_node_id = night_summarize_token_budget_bundle_graph_node_id(
        bundle_node.node_id,
        summary_run_id=summary_run_id,
    )
    source_payloads = [
        _require_summary_payload(data_store=data_store, summary_graph_node_id=data_id)
        for data_id in spec.source_summary_graph_node_ids
    ]
    input_data_id = f"{frame_id}:input"
    input_payload = _input_payload(
        input_data_id=input_data_id,
        summary_run_id=summary_run_id,
        bundle_node_payload=asdict(bundle_node),
        source_summary_payloads=source_payloads,
    )
    input_trace_id = _record_input(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        input_data_id=input_data_id,
        input_payload=input_payload,
        source_trace_ids=_unique_strings([bundle_trace_id, *bundle_node.source_trace_ids]),
        source_data_ids=_unique_strings(
            [bundle_node.node_id, *bundle_node.source_graph_node_ids, *bundle_node.source_data_ids]
        ),
    )
    frame_source_trace_ids = _unique_strings(
        [bundle_trace_id, *bundle_node.source_trace_ids, input_trace_id]
    )
    frame_source_data_ids = _unique_strings(
        [
            bundle_node.node_id,
            *bundle_node.source_graph_node_ids,
            *bundle_node.source_data_ids,
            input_data_id,
        ]
    )
    if adapter is None:
        frame = _failed_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            bundle_node=bundle_node,
            model_id="adapter_missing",
            failure_type="adapter_missing",
            payload_parse_status="not_checked",
            source_trace_ids=frame_source_trace_ids,
            source_data_ids=frame_source_data_ids,
            llm_call_data_id=None,
            llm_trace_event_id=None,
        )
        result = _record_failed_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )
        return _with_bundle_ids(result, bundle_node.node_id, bundle_edge_ids, created_ids, existing_ids)

    prompt = Path(NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_PROMPT_REF).read_text(encoding="utf-8")
    llm_result = LLMNodeExecutor(adapter).run(
        node_id=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID,
        prompt=prompt,
        input_payload=input_payload,
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        prompt_ref=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_PROMPT_REF,
        input_ref=frame_source_trace_ids,
        source_data_ids=frame_source_data_ids,
        max_retries=max_retries,
        payload_validator=_validate_summary_payload,
    )
    source_trace_ids_after_llm = _unique_strings(
        [*frame_source_trace_ids, llm_result.trace_event_id]
    )
    source_data_ids_after_llm = _unique_strings(
        [*frame_source_data_ids, llm_result.call_data_id]
    )
    if llm_result.failure_type != "none" or llm_result.validation.payload is None:
        frame = _failed_frame(
            frame_id=frame_id,
            summary_graph_node_id=summary_graph_node_id,
            bundle_node=bundle_node,
            model_id=llm_result.model_id,
            failure_type=llm_result.failure_type,
            payload_parse_status=_payload_parse_status(llm_result.failure_type),
            source_trace_ids=source_trace_ids_after_llm,
            source_data_ids=source_data_ids_after_llm,
            llm_call_data_id=llm_result.call_data_id,
            llm_trace_event_id=llm_result.trace_event_id,
        )
        result = _record_failed_frame(
            trace_store=trace_store,
            data_store=data_store,
            turn_id=turn_id,
            frame=frame,
        )
        return _with_bundle_ids(result, bundle_node.node_id, bundle_edge_ids, created_ids, existing_ids)

    frame = _frame_from_payload(
        payload=llm_result.validation.payload,
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        bundle_node=bundle_node,
        model_id=llm_result.model_id,
        source_trace_ids=source_trace_ids_after_llm,
        source_data_ids=source_data_ids_after_llm,
        llm_call_data_id=llm_result.call_data_id,
        llm_trace_event_id=llm_result.trace_event_id,
    )
    result = _record_success_graph_summary(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        frame=frame,
    )
    return _with_bundle_ids(result, bundle_node.node_id, bundle_edge_ids, created_ids, existing_ids)


def _with_bundle_ids(
    result: RecordedNightTokenBudgetBundleSummaryResult,
    bundle_graph_node_id: str,
    bundle_edge_ids: list[str],
    created_ids: list[str],
    existing_ids: list[str],
) -> RecordedNightTokenBudgetBundleSummaryResult:
    return RecordedNightTokenBudgetBundleSummaryResult(
        frame=result.frame,
        trace_event_id=result.trace_event_id,
        frame_data_id=result.frame_data_id,
        target_bundle_graph_node_id=bundle_graph_node_id,
        summary_graph_node_data_id=result.summary_graph_node_data_id,
        summary_edge_data_id=result.summary_edge_data_id,
        bundle_edge_data_ids=bundle_edge_ids,
        created_data_ids=[*created_ids, *result.created_data_ids],
        existing_data_ids=[*existing_ids, *result.existing_data_ids],
    )


def _frame_from_payload(
    *,
    payload: dict[str, object],
    frame_id: str,
    summary_graph_node_id: str,
    bundle_node: GraphMemoryNodeFrame,
    model_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightTokenBudgetBundleSummaryFrame:
    frame = NightTokenBudgetBundleSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=bundle_node.node_id,
        target_node_kind=bundle_node.node_kind,
        summary_text=str(payload.get("summary_text") or "").strip(),
        summary_status="ran",
        failure_type="none",
        payload_parse_status="passed",
        summary_depth=bundle_node.summary_depth + 1,
        source_depth_min=bundle_node.source_depth_min,
        source_depth_max=bundle_node.source_depth_max,
        source_leaf_count=bundle_node.source_leaf_count,
        source_summary_count=bundle_node.source_summary_count,
        char_budget=bundle_node.char_budget or 0,
        input_summary_char_count=bundle_node.source_char_count,
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        source_graph_node_ids=[bundle_node.node_id, *bundle_node.source_graph_node_ids],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_token_budget_bundle",
        info_class="mixed",
        semantic_judgement_status="ran",
    )
    _validate_token_budget_summary_frame(frame)
    return frame


def _failed_frame(
    *,
    frame_id: str,
    summary_graph_node_id: str,
    bundle_node: GraphMemoryNodeFrame,
    model_id: str,
    failure_type: str,
    payload_parse_status: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    llm_call_data_id: str | None,
    llm_trace_event_id: str | None,
) -> NightTokenBudgetBundleSummaryFrame:
    frame = NightTokenBudgetBundleSummaryFrame(
        frame_id=frame_id,
        summary_graph_node_id=summary_graph_node_id,
        target_graph_node_id=bundle_node.node_id,
        target_node_kind=bundle_node.node_kind,
        summary_text="",
        summary_status="failed",
        failure_type=failure_type,
        payload_parse_status=payload_parse_status,
        summary_depth=bundle_node.summary_depth + 1,
        source_depth_min=bundle_node.source_depth_min,
        source_depth_max=bundle_node.source_depth_max,
        source_leaf_count=bundle_node.source_leaf_count,
        source_summary_count=bundle_node.source_summary_count,
        char_budget=bundle_node.char_budget or 0,
        input_summary_char_count=bundle_node.source_char_count,
        llm_call_data_id=llm_call_data_id,
        llm_trace_event_id=llm_trace_event_id,
        source_graph_node_ids=[bundle_node.node_id, *bundle_node.source_graph_node_ids],
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        generated_by=f"LLM:{model_id}:night_summarize_token_budget_bundle",
        info_class="mixed",
        semantic_judgement_status="failed",
    )
    _validate_token_budget_summary_frame(frame)
    return frame


def _record_success_graph_summary(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightTokenBudgetBundleSummaryFrame,
) -> RecordedNightTokenBudgetBundleSummaryResult:
    edge = _summary_of_edge(frame)
    validate_graph_memory_edge_frame(edge)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids or [],
        output_ref=[frame.summary_graph_node_id, edge.edge_id],
        schema_status="passed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.summary_graph_node_id,
        data_type="graph_memory:node:summary",
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=edge.edge_id,
        data_type="graph_memory:edge:SUMMARY_OF",
        payload=asdict(edge),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightTokenBudgetBundleSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.summary_graph_node_id,
        target_bundle_graph_node_id=frame.target_graph_node_id,
        summary_graph_node_data_id=frame.summary_graph_node_id,
        summary_edge_data_id=edge.edge_id,
        bundle_edge_data_ids=[],
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _record_failed_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    frame: NightTokenBudgetBundleSummaryFrame,
) -> RecordedNightTokenBudgetBundleSummaryResult:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID,
        event_type="node_output",
        input_ref=frame.source_trace_ids or [],
        output_ref=[frame.frame_id],
        schema_status="failed",
    )
    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    _record_payload_if_missing(
        data_store=data_store,
        data_id=frame.frame_id,
        data_type=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_FRAME_DATA_TYPE,
        payload=asdict(frame),
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    return RecordedNightTokenBudgetBundleSummaryResult(
        frame=frame,
        trace_event_id=event.event_id,
        frame_data_id=frame.frame_id,
        target_bundle_graph_node_id=frame.target_graph_node_id,
        summary_graph_node_data_id=None,
        summary_edge_data_id=None,
        bundle_edge_data_ids=[],
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _contains_edge(bundle_node: GraphMemoryNodeFrame, child_node_id: str) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=f"graph:edge:contains:{bundle_node.node_id}:{child_node_id}",
        edge_kind="CONTAINS",
        from_node_id=bundle_node.node_id,
        to_node_id=child_node_id,
        source_graph_node_ids=[bundle_node.node_id, child_node_id],
        source_trace_ids=list(bundle_node.source_trace_ids),
        source_data_ids=[bundle_node.node_id, child_node_id],
    )


def _summary_of_edge(frame: NightTokenBudgetBundleSummaryFrame) -> GraphMemoryEdgeFrame:
    return GraphMemoryEdgeFrame(
        edge_id=(
            "graph:edge:summary_of:"
            f"{frame.summary_graph_node_id}:{frame.target_graph_node_id}"
        ),
        edge_kind="SUMMARY_OF",
        from_node_id=frame.summary_graph_node_id,
        to_node_id=frame.target_graph_node_id,
        source_graph_node_ids=_unique_strings(
            [
                frame.summary_graph_node_id,
                frame.target_graph_node_id,
                *(frame.source_graph_node_ids or []),
            ]
        ),
        source_trace_ids=list(frame.source_trace_ids or []),
        source_data_ids=_unique_strings(
            [
                frame.summary_graph_node_id,
                frame.target_graph_node_id,
                *(frame.source_graph_node_ids or []),
            ]
        ),
    )


def _input_payload(
    *,
    input_data_id: str,
    summary_run_id: str,
    bundle_node_payload: dict[str, object],
    source_summary_payloads: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "input_data_id": input_data_id,
        "summary_run_id": summary_run_id,
        "target_token_budget_bundle_payload": dict(bundle_node_payload),
        "source_summary_payloads": [
            {
                "summary_graph_node_id": _text(payload.get("summary_graph_node_id"))
                or _text(payload.get("frame_id")),
                "source_kind": _text(payload.get("source_kind")),
                "source_path": _text(payload.get("source_path")),
                "summary_text": _text(payload.get("summary_text")),
                "summary_status": _text(payload.get("summary_status")),
                "info_class": _text(payload.get("info_class")),
            }
            for payload in source_summary_payloads
        ],
        "expected_info_class": "mixed",
        "budget_unit": "characters",
        "classification_rule": (
            "token-budget layer v0 uses code-counted summary_text characters; "
            "successful bundle summaries are mixed because they depend on multiple summaries"
        ),
        "generated_by": "CODE:NIGHT_TOKEN_BUDGET_BUNDLE_INPUT_BUILDER",
        "semantic_judgement_status": "not_run",
    }


def _record_input(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    input_data_id: str,
    input_payload: dict[str, object],
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> str:
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID,
        event_type="node_input",
        input_ref=source_trace_ids,
        output_ref=[input_data_id],
        schema_status="not_checked",
    )
    data_store.create_record(
        data_id=input_data_id,
        data_type="node_input:night_summarize_token_budget_bundle_input",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload={
            **input_payload,
            "source_trace_ids": source_trace_ids,
            "source_data_ids": source_data_ids,
        },
    )
    return event.event_id


def _validate_summary_payload(payload: dict[str, object]) -> None:
    summary_text = str(payload.get("summary_text") or "").strip()
    if not summary_text:
        raise ValueError("summary_text must not be empty")
    supplied_info_class = payload.get("info_class")
    if supplied_info_class is not None and supplied_info_class != "mixed":
        raise ValueError("token budget bundle summary info_class must be mixed")
    supplied_source_ids = payload.get("source_graph_node_ids")
    if supplied_source_ids:
        raise ValueError("LLM must not supply source_graph_node_ids")


def _validate_token_budget_summary_frame(frame: NightTokenBudgetBundleSummaryFrame) -> None:
    for field_name, value in {
        "frame_id": frame.frame_id,
        "summary_graph_node_id": frame.summary_graph_node_id,
        "target_graph_node_id": frame.target_graph_node_id,
        "target_node_kind": frame.target_node_kind,
        "summary_status": frame.summary_status,
        "failure_type": frame.failure_type,
        "payload_parse_status": frame.payload_parse_status,
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
    }.items():
        if not value:
            raise ValueError(f"NightTokenBudgetBundleSummaryFrame.{field_name} must not be empty")
    if frame.target_node_kind != TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND:
        raise ValueError("token budget bundle summary target must be token budget bundle")
    if frame.info_class != "mixed":
        raise ValueError("token budget bundle summary info_class must be mixed")
    if frame.semantic_judgement_status not in {"ran", "failed"}:
        raise ValueError("token budget bundle semantic status is invalid")
    if frame.summary_status not in {"ran", "failed"}:
        raise ValueError("token budget bundle summary_status is invalid")
    if frame.failure_type not in {
        "none",
        "adapter_missing",
        "adapter_failed",
        "parse_failed",
        "schema_failed",
    }:
        raise ValueError("token budget bundle failure_type is invalid")
    if frame.summary_status == "ran" and not frame.summary_text:
        raise ValueError("successful token budget bundle summary_text must not be empty")
    if frame.char_budget <= 0:
        raise ValueError("token budget bundle char_budget must be positive")
    if frame.input_summary_char_count < 0:
        raise ValueError("token budget bundle input_summary_char_count must be non-negative")
    if frame.target_graph_node_id not in (frame.source_data_ids or []):
        raise ValueError("token budget bundle summary source_data_ids must include target")
    for graph_node_id in frame.source_graph_node_ids or []:
        if graph_node_id not in (frame.source_data_ids or []):
            raise ValueError("token budget bundle summary source_data_ids must include graph ids")


def _require_summary_payload(
    *,
    data_store: DataStore,
    summary_graph_node_id: str,
) -> dict[str, object]:
    record = data_store.require_record(summary_graph_node_id)
    if record.data_type != "graph_memory:node:summary":
        raise ValueError(f"expected graph summary node: {summary_graph_node_id}")
    if not isinstance(record.payload, dict):
        raise TypeError(f"summary node payload must be dict: {summary_graph_node_id}")
    return dict(record.payload)


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
            raise ValueError(f"token budget summary data_id collision: {data_id}")
        if existing.payload != payload:
            raise ValueError(
                f"token budget summary data_id collision with different payload: {data_id}"
            )
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


def _payload_parse_status(failure_type: str) -> str:
    if failure_type == "parse_failed":
        return "failed"
    if failure_type in {"adapter_failed", "adapter_missing"}:
        return "not_checked"
    return "passed"


def _require_text(field_name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{field_name} must not be empty")


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


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
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _safe_id_part(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        raise ValueError("safe id part must not be empty")
    return cleaned


__all__ = [
    "NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_FRAME_DATA_TYPE",
    "NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_NODE_ID",
    "NIGHT_SUMMARIZE_TOKEN_BUDGET_BUNDLE_PROMPT_REF",
    "TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_DATA_TYPE",
    "TOKEN_BUDGET_SUMMARY_BUNDLE_NODE_KIND",
    "TOKEN_BUDGET_SUMMARY_BUNDLE_POLICY_ID",
    "NightTokenBudgetBundleSummaryFrame",
    "RecordedNightTokenBudgetBundleSummaryResult",
    "TokenBudgetSummaryBundleSpec",
    "build_token_budget_summary_bundle_specs",
    "collect_active_source_leaf_summary_graph_node_ids",
    "night_summarize_token_budget_bundle_frame_id",
    "night_summarize_token_budget_bundle_graph_node_id",
    "record_token_budget_summary_bundle_node",
    "run_night_summarize_token_budget_bundle",
    "token_budget_summary_bundle_graph_node_id",
]
