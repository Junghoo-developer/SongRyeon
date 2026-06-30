from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import (
    DocumentContextPackExcludedDocument,
    DocumentContextPackFrame,
    DocumentContextPackIncludedDocument,
    ExplicitArtifactReferenceFrame,
    ExplicitArtifactResolvedReference,
    validate_document_context_pack_frame,
    validate_explicit_artifact_reference_frame,
)
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.loops.l_loop_namespace import LRunIds
from songryeon_core.tools.document_tools import read_artifact, read_doc


EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE = "node_output:explicit_artifact_reference_frame"
DOCUMENT_CONTEXT_PACK_DATA_TYPE = "node_output:document_context_pack_frame"

_ARTIFACT_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_./\\-])"
    r"(?:Administrative_Reform_1[/\\])?"
    r"(?:[A-Za-z0-9_.-]+[/\\])*"
    r"ORDER_\d{3}(?:_[A-Za-z0-9]+)*(?:\.md)?"
    r"(?![A-Za-z0-9_./\\-])",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION = ".,;:!?)]}>'\"`"


@dataclass
class _DocumentCandidate:
    doc_id: str
    selection_basis: str
    source_data_id: str
    rank_index: int = 0


def explicit_artifact_reference_frame_id(
    *,
    id_namespace: LRunIds | None,
) -> str:
    legacy_id = "L:explicit_artifact_reference_frame"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def document_context_pack_frame_id(
    *,
    id_namespace: LRunIds | None,
) -> str:
    legacy_id = "L:document_context_pack_frame"
    if id_namespace is None:
        return legacy_id
    return id_namespace.scoped_data_id(legacy_id)


def extract_explicit_artifact_references(user_text: str) -> list[str]:
    """Return visible ORDER/artifact references in user-text order."""

    refs: list[str] = []
    seen_spans: set[tuple[int, int]] = set()
    for match in _ARTIFACT_REF_RE.finditer(user_text or ""):
        raw_ref = match.group(0).strip().strip(_TRAILING_PUNCTUATION)
        if not raw_ref:
            continue
        span = match.span()
        if span in seen_spans:
            continue
        seen_spans.add(span)
        refs.append(raw_ref)
    return refs


def record_explicit_artifact_reference_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    user_text: str,
    document_root: str | Path,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    frame_id: str,
) -> tuple[str, str, ExplicitArtifactReferenceFrame]:
    """Extract explicit artifact refs and resolve them before embedding candidates are packed."""

    frame = build_explicit_artifact_reference_frame(
        turn_id=turn_id,
        user_text=user_text,
        document_root=document_root,
        frame_id=frame_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
    )
    validate_explicit_artifact_reference_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="document_context_builder",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=EXPLICIT_ARTIFACT_REFERENCE_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def build_explicit_artifact_reference_frame(
    *,
    turn_id: str,
    user_text: str,
    document_root: str | Path,
    frame_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
) -> ExplicitArtifactReferenceFrame:
    refs = extract_explicit_artifact_references(user_text)
    resolved: list[ExplicitArtifactResolvedReference] = []
    for index, raw_ref in enumerate(refs, start=1):
        payload = read_artifact(root=document_root, artifact_ref=raw_ref)
        status = str(payload.get("match_status") or "not_found")
        if status == "invalid_ref":
            resolve_status = "invalid_ref"
        elif status == "ambiguous":
            resolve_status = "ambiguous"
        elif status == "unique":
            resolve_status = "unique"
        else:
            resolve_status = "not_found"
        candidates = payload.get("candidates")
        resolved.append(
            ExplicitArtifactResolvedReference(
                raw_ref=raw_ref,
                normalized_ref=_normalize_ref(raw_ref),
                occurrence_index=index,
                resolve_status=resolve_status,
                candidate_count=_int(payload.get("candidate_count")),
                selected_doc_id=_optional_text(payload.get("selected_doc_id"))
                if resolve_status == "unique"
                else None,
                match_type=_optional_text(payload.get("match_type"))
                if resolve_status == "unique"
                else None,
                char_count=_int(payload.get("char_count")) if resolve_status == "unique" else 0,
                candidates=[item for item in candidates if isinstance(item, dict)]
                if isinstance(candidates, list)
                else [],
            )
        )

    return ExplicitArtifactReferenceFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        source_user_text=user_text,
        extracted_reference_count=len(resolved),
        resolved_references=resolved,
        unique_count=sum(1 for item in resolved if item.resolve_status == "unique"),
        ambiguous_count=sum(1 for item in resolved if item.resolve_status == "ambiguous"),
        not_found_count=sum(1 for item in resolved if item.resolve_status == "not_found"),
        invalid_count=sum(1 for item in resolved if item.resolve_status == "invalid_ref"),
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=_unique_strings(source_data_ids),
    )


def record_document_context_pack_frame(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    document_root: str | Path,
    max_document_context_chars: int,
    frame_id: str,
    explicit_reference_data_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None,
) -> tuple[str, str, DocumentContextPackFrame]:
    """Build and store the whole-document context pack for node_3."""

    frame = build_document_context_pack_frame(
        data_store=data_store,
        turn_id=turn_id,
        document_root=document_root,
        max_document_context_chars=max_document_context_chars,
        frame_id=frame_id,
        explicit_reference_data_id=explicit_reference_data_id,
        source_trace_ids=source_trace_ids,
        source_data_ids=source_data_ids,
        id_namespace=id_namespace,
    )
    validate_document_context_pack_frame(frame)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="document_context_builder",
        event_type="node_output",
        input_ref=frame.source_trace_ids,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=DOCUMENT_CONTEXT_PACK_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return event.event_id, frame.frame_id, frame


def build_document_context_pack_frame(
    *,
    data_store: DataStore,
    turn_id: str,
    document_root: str | Path,
    max_document_context_chars: int,
    frame_id: str,
    explicit_reference_data_id: str,
    source_trace_ids: list[str],
    source_data_ids: list[str],
    id_namespace: LRunIds | None,
) -> DocumentContextPackFrame:
    candidates = _ranked_document_candidates(
        data_store=data_store,
        explicit_reference_data_id=explicit_reference_data_id,
        id_namespace=id_namespace,
    )
    source_query_frame_ids = _source_query_frame_ids(data_store, id_namespace=id_namespace)
    source_search_result_data_ids = _source_search_result_data_ids(candidates)
    included: list[DocumentContextPackIncludedDocument] = []
    excluded: list[DocumentContextPackExcludedDocument] = []
    included_total_chars = 0
    strict_cutoff_seen = False
    cutoff_reason = "none"

    for rank_index, candidate in enumerate(candidates, start=1):
        try:
            payload = read_doc(root=document_root, doc_id=candidate.doc_id)
        except (FileNotFoundError, ValueError):
            excluded.append(
                DocumentContextPackExcludedDocument(
                    doc_id=candidate.doc_id,
                    document_name=_document_name(candidate.doc_id),
                    char_count=0,
                    rank_index=rank_index,
                    selection_basis=candidate.selection_basis,
                    exclusion_reason="excluded_not_readable_markdown_document",
                    would_exceed_budget=False,
                    source_data_id=candidate.source_data_id,
                )
            )
            continue
        text = str(payload.get("text") or "")
        char_count = payload.get("char_count")
        if not isinstance(char_count, int):
            char_count = len(text)
        candidate.rank_index = rank_index
        if strict_cutoff_seen:
            excluded.append(
                DocumentContextPackExcludedDocument(
                    doc_id=candidate.doc_id,
                    document_name=_document_name(candidate.doc_id),
                    char_count=char_count,
                    rank_index=rank_index,
                    selection_basis=candidate.selection_basis,
                    exclusion_reason="excluded_after_strict_rank_cutoff",
                    would_exceed_budget=False,
                    source_data_id=candidate.source_data_id,
                )
            )
            continue
        if included_total_chars + char_count <= max_document_context_chars:
            included.append(
                DocumentContextPackIncludedDocument(
                    doc_id=candidate.doc_id,
                    document_name=_document_name(candidate.doc_id),
                    char_count=char_count,
                    rank_index=rank_index,
                    selection_basis=candidate.selection_basis,
                    text=text,
                    source_data_id=candidate.source_data_id,
                )
            )
            included_total_chars += char_count
            continue
        excluded.append(
            DocumentContextPackExcludedDocument(
                doc_id=candidate.doc_id,
                document_name=_document_name(candidate.doc_id),
                char_count=char_count,
                rank_index=rank_index,
                selection_basis=candidate.selection_basis,
                exclusion_reason="excluded_due_to_context_budget",
                would_exceed_budget=True,
                source_data_id=candidate.source_data_id,
            )
        )
        strict_cutoff_seen = True
        cutoff_reason = f"excluded_due_to_context_budget at {candidate.doc_id}"

    pack_source_data_ids = _unique_strings(
        [
            explicit_reference_data_id,
            *source_query_frame_ids,
            *source_search_result_data_ids,
            *source_data_ids,
        ]
    )
    return DocumentContextPackFrame(
        frame_id=frame_id,
        turn_id=turn_id,
        max_document_context_chars=max_document_context_chars,
        budget_unit="chars",
        whole_document_only=True,
        strict_rank_order=True,
        included_documents=included,
        excluded_documents=excluded,
        included_document_count=len(included),
        excluded_document_count=len(excluded),
        included_total_chars=included_total_chars,
        cutoff_reason=cutoff_reason,
        source_query_frame_ids=source_query_frame_ids,
        source_search_result_data_ids=source_search_result_data_ids,
        source_explicit_reference_data_id=explicit_reference_data_id,
        source_trace_ids=_unique_strings(source_trace_ids),
        source_data_ids=pack_source_data_ids,
    )


def latest_document_context_pack_payload(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> dict[str, object]:
    for record in reversed(data_store.list_records()):
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if record.data_type != DOCUMENT_CONTEXT_PACK_DATA_TYPE:
            continue
        return record.payload if isinstance(record.payload, dict) else {}
    return {}


def _ranked_document_candidates(
    *,
    data_store: DataStore,
    explicit_reference_data_id: str,
    id_namespace: LRunIds | None,
) -> list[_DocumentCandidate]:
    candidates: list[_DocumentCandidate] = []
    seen_doc_ids: set[str] = set()

    explicit_payload = _payload(data_store, explicit_reference_data_id)
    resolved = explicit_payload.get("resolved_references")
    if isinstance(resolved, list):
        for item in resolved:
            if not isinstance(item, dict) or item.get("resolve_status") != "unique":
                continue
            doc_id = item.get("selected_doc_id")
            raw_ref = item.get("raw_ref")
            if not isinstance(doc_id, str) or not doc_id or doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            candidates.append(
                _DocumentCandidate(
                    doc_id=doc_id,
                    selection_basis=f"explicit_artifact_reference_unique:{raw_ref or doc_id}",
                    source_data_id=explicit_reference_data_id,
                )
            )

    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if not record.data_type.startswith("node_output:L3") or "preserved_info_frame" not in record.data_type:
            continue
        if not isinstance(record.payload, dict):
            continue
        raw_candidates = record.payload.get("candidates")
        if not isinstance(raw_candidates, list):
            continue
        for item in raw_candidates:
            if not isinstance(item, dict):
                continue
            doc_id = item.get("doc_id")
            if not isinstance(doc_id, str) or not doc_id or doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            source_data_id = item.get("source_data_id")
            candidates.append(
                _DocumentCandidate(
                    doc_id=doc_id,
                    selection_basis="embedding_search_candidate",
                    source_data_id=source_data_id if isinstance(source_data_id, str) and source_data_id else record.data_id,
                )
            )
    return candidates


def _source_query_frame_ids(
    data_store: DataStore,
    *,
    id_namespace: LRunIds | None,
) -> list[str]:
    ids: list[str] = []
    for record in data_store.list_records():
        if not _record_in_namespace(record.data_id, id_namespace=id_namespace):
            continue
        if record.data_type in {
            "node_output:L2_query_frame",
            "node_output:L2_revision_query_frame",
        }:
            ids.append(record.data_id)
    return _unique_strings(ids)


def _source_search_result_data_ids(candidates: list[_DocumentCandidate]) -> list[str]:
    return _unique_strings(
        [
            candidate.source_data_id
            for candidate in candidates
            if candidate.selection_basis == "embedding_search_candidate"
        ]
    )


def _payload(data_store: DataStore, data_id: str) -> dict[str, object]:
    record = data_store.get_record(data_id)
    if record is None or not isinstance(record.payload, dict):
        return {}
    return record.payload


def _record_in_namespace(data_id: str, *, id_namespace: LRunIds | None) -> bool:
    if id_namespace is None:
        return True
    return id_namespace.owns_data_id(data_id)


def _normalize_ref(raw_ref: str) -> str:
    normalized = str(raw_ref or "").strip().strip("`'\"").replace("\\", "/")
    normalized = normalized.strip().strip("/")
    normalized = normalized.removeprefix("Administrative_Reform_1/")
    return normalized.lower()


def _document_name(doc_id: str) -> str:
    normalized = doc_id.replace("\\", "/").strip("/")
    return normalized.rsplit("/", 1)[-1] or doc_id


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _unique_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
