from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DataRef,
    ToolCatalogFrame,
    ToolCatalogItem,
    ToolChoiceFrame,
    validate_tool_catalog_frame,
    validate_tool_choice_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.tools.document_tools import list_docs, read_artifact, read_doc, search_docs


ToolFunction = Callable[..., object]


@dataclass
class ToolSpec:
    """도구 하나의 등록 정보."""

    name: str
    description: str
    read_only: bool
    output_data_type: str
    function: ToolFunction
    input_fields: list[str] = field(default_factory=list)


@dataclass
class ToolRunResult:
    """도구 실행 결과와 trace 연결 정보."""

    tool_name: str
    trace_event_id: str
    data_ref: DataRef
    payload: object


class ToolRegistry:
    """사용 가능한 도구 목록을 관리한다."""

    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self._specs = {spec.name: spec for spec in specs or []}

    def register(self, spec: ToolSpec) -> None:
        if not spec.read_only:
            raise ValueError("only read-only tools are allowed at this stage")
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._specs:
            raise KeyError(f"unknown tool: {name}")
        return self._specs[name]

    def names(self) -> list[str]:
        return sorted(self._specs)

    def list_specs(self) -> list[ToolSpec]:
        return [self._specs[name] for name in self.names()]

    def to_catalog_items(self) -> list[ToolCatalogItem]:
        return [
            ToolCatalogItem(
                tool_name=spec.name,
                description=spec.description,
                read_only=spec.read_only,
                input_fields=list(spec.input_fields),
                output_data_type=spec.output_data_type,
            )
            for spec in self.list_specs()
        ]


class ToolRunner:
    """도구를 실행하고 trace 이름표와 payload 본체를 함께 남긴다."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def run(
        self,
        *,
        tool_name: str,
        trace_store: TraceStore,
        data_store: DataStore | None = None,
        turn_id: str,
        input_ref: list[str] | None = None,
        id_namespace: LRunIds | None = None,
        **kwargs: Any,
    ) -> ToolRunResult:
        spec = self.registry.get(tool_name)
        payload = spec.function(**kwargs)

        event_id = trace_store.next_event_id()
        data_id = tool_result_data_id(tool_name, event_id, id_namespace=id_namespace)
        event = trace_store.create_event(
            event_id=event_id,
            turn_id=turn_id,
            actor=f"tool:{tool_name}",
            event_type="tool_call",
            input_ref=input_ref or [],
            output_ref=[data_id],
            schema_status="passed",
        )
        data_ref = DataRef(
            data_id=data_id,
            data_type=spec.output_data_type,
            exists=True,
            created_at=event.timestamp,
            source_trace_id=event.event_id,
        )
        if data_store is not None:
            data_store.create_record(
                data_id=data_ref.data_id,
                data_type=data_ref.data_type,
                exists=data_ref.exists,
                created_at=data_ref.created_at,
                source_trace_id=data_ref.source_trace_id,
                payload=payload,
            )
        return ToolRunResult(
            tool_name=tool_name,
            trace_event_id=event.event_id,
            data_ref=data_ref,
            payload=payload,
        )


def build_document_tool_registry(document_root: str | Path) -> ToolRegistry:
    """Administrative_Reform_1 같은 문서 루트에 묶인 읽기 전용 도구 레지스트리."""

    root = Path(document_root)
    return ToolRegistry(
        [
            ToolSpec(
                name="list_docs",
                description="Markdown 문서 목록을 읽기 전용으로 가져온다.",
                read_only=True,
                output_data_type="tool_result:list_docs",
                function=lambda: list_docs(root=root),
                input_fields=[],
            ),
            ToolSpec(
                name="read_doc",
                description="Markdown 문서 하나를 읽기 전용으로 가져온다.",
                read_only=True,
                output_data_type="tool_result:read_doc",
                function=lambda doc_id: read_doc(root=root, doc_id=doc_id),
                input_fields=["doc_id"],
            ),
            ToolSpec(
                name="read_artifact",
                description="명시적인 Markdown 문서명, 파일명, 경로를 정확히 해석해 읽는다.",
                read_only=True,
                output_data_type="tool_result:read_artifact",
                function=lambda artifact_ref: read_artifact(root=root, artifact_ref=artifact_ref),
                input_fields=["artifact_ref"],
            ),
            ToolSpec(
                name="search_docs",
                description="Markdown 문서를 임베딩 검색한다.",
                read_only=True,
                output_data_type="tool_result:search_docs",
                function=lambda query, top_k=5: search_docs(root=root, query=query, top_k=top_k),
                input_fields=["query", "top_k"],
            ),
        ]
    )


def tool_result_data_id(
    tool_name: str,
    event_id: str,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    legacy_id = f"tool_result:{tool_name}:{event_id}"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def tool_catalog_data_id(turn_id: str, *, id_namespace: LRunIds | None = None) -> str:
    if id_namespace is None:
        return f"tool_catalog:{turn_id}"
    return id_namespace.tool_catalog_data_id(turn_id)


def tool_choice_data_id(
    chooser_node_id: str,
    tool_name: str,
    *,
    id_namespace: LRunIds | None = None,
) -> str:
    if id_namespace is None:
        return f"tool_choice:{chooser_node_id}:{tool_name}"
    return id_namespace.tool_choice_data_id(chooser_node_id, tool_name)


def record_tool_catalog(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    registry: ToolRegistry,
    input_ref: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    id_namespace: LRunIds | None = None,
) -> str:
    """ToolRegistry 내용을 ToolCatalogFrame으로 trace/data에 저장한다."""

    catalog_id = tool_catalog_data_id(turn_id, id_namespace=id_namespace)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="tool_registry",
        event_type="node_output",
        input_ref=input_ref or [],
        output_ref=[catalog_id],
        schema_status="passed",
    )
    frame = ToolCatalogFrame(
        catalog_id=catalog_id,
        turn_id=turn_id,
        tools=registry.to_catalog_items(),
        source_trace_ids=input_ref or [],
        source_data_ids=source_data_ids or [],
    )
    validate_tool_catalog_frame(frame)
    data_store.create_record(
        data_id=catalog_id,
        data_type="tool_catalog",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id


def record_tool_choice(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    registry: ToolRegistry,
    chooser_node_id: str,
    tool_name: str,
    catalog_id: str,
    reason: str,
    expected_use: str,
    tool_choice_policy_id: str | None = None,
    expected_effect_label: str | None = None,
    input_ref: list[str] | None = None,
    source_data_ids: list[str] | None = None,
    id_namespace: LRunIds | None = None,
) -> str:
    """검증된 tool choice를 trace/data에 저장한다."""

    registry.get(tool_name)
    choice_id = tool_choice_data_id(
        chooser_node_id,
        tool_name,
        id_namespace=id_namespace,
    )
    choice_source_data_ids = _unique_strings([catalog_id, *(source_data_ids or [])])
    frame = ToolChoiceFrame(
        choice_id=choice_id,
        turn_id=turn_id,
        chooser_node_id=chooser_node_id,
        tool_name=tool_name,
        reason=reason,
        expected_use=expected_use,
        catalog_id=catalog_id,
        tool_choice_policy_id=tool_choice_policy_id or f"{chooser_node_id}:{tool_name}:policy",
        expected_effect_label=expected_effect_label or f"CODE_STATUS:{tool_name}_selected",
        source_trace_ids=input_ref or [],
        source_data_ids=choice_source_data_ids,
    )
    validate_tool_choice_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor=chooser_node_id,
        event_type="node_output",
        input_ref=input_ref or [],
        output_ref=[choice_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=choice_id,
        data_type="tool_choice",
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
