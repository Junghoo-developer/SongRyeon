from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.schemas import MemoryItem
from songryeon_core.core.trace_store import TraceStore
from songryeon_core.tools.workspace_policy import (
    WORKSPACE_EXCLUDED_DIR_NAMES,
    WORKSPACE_SUPPORTED_EXTENSIONS,
    workspace_directory_is_excluded,
    workspace_file_rejection_reason,
    workspace_source_kind,
)


WORKSPACE_MANIFEST_POLICY_ID = "EXTERNAL_WORKSPACE_READ_ONLY_BOUNDARY_V0"
WORKSPACE_MANIFEST_GENERATOR = "CODE:WORKSPACE_MANIFEST_BUILDER"
WORKSPACE_MANIFEST_DATA_TYPE = "node_output:workspace_manifest_frame"


@dataclass(frozen=True)
class WorkspaceManifestFile:
    relative_path: str
    source_kind: str
    extension: str
    size_bytes: int
    modified_at_utc: str
    content_hash: str


@dataclass(frozen=True)
class WorkspaceManifestFrame:
    frame_id: str
    workspace_label: str
    root_path: str
    observed_at: str
    manifest_status: str
    access_mode: str
    local_model_only: bool
    automatic_graph_ingest_status: str
    supported_extensions: list[str]
    candidate_file_count: int
    source_kind_counts: dict[str, int]
    extension_counts: dict[str, int]
    excluded_file_count: int
    excluded_directory_count: int
    exclusion_reason_counts: dict[str, int]
    files: list[WorkspaceManifestFile]
    policy_id: str = WORKSPACE_MANIFEST_POLICY_ID
    generated_by: str = WORKSPACE_MANIFEST_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"


@dataclass(frozen=True)
class RecordedWorkspaceManifest:
    frame: WorkspaceManifestFrame
    trace_event_id: str
    data_id: str


def build_workspace_manifest(
    *,
    root_path: str | Path,
    turn_id: str,
    observed_at: str | None = None,
) -> WorkspaceManifestFrame:
    """사용자가 고른 업무 폴더의 읽기 가능한 파일 좌표와 hash를 기록한다."""

    root = Path(root_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"workspace root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"workspace root is not a directory: {root}")

    files: list[WorkspaceManifestFile] = []
    exclusion_reason_counts: dict[str, int] = {}
    excluded_file_count = 0
    excluded_directory_count = 0

    for current_root, dir_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current_root)
        kept_dirs: list[str] = []
        for dir_name in sorted(dir_names):
            directory = current_path / dir_name
            reason = None
            if directory.is_symlink():
                reason = "symbolic_link_rejected"
            elif workspace_directory_is_excluded(directory):
                reason = "excluded_directory_policy"
            if reason is None:
                kept_dirs.append(dir_name)
                continue
            excluded_directory_count += 1
            _increment(exclusion_reason_counts, reason)
        dir_names[:] = kept_dirs

        for file_name in sorted(file_names):
            path = current_path / file_name
            reason = workspace_file_rejection_reason(root=root, path=path)
            if reason is not None:
                excluded_file_count += 1
                _increment(exclusion_reason_counts, reason)
                continue
            try:
                stat = path.stat()
                content = path.read_bytes()
            except OSError:
                excluded_file_count += 1
                _increment(exclusion_reason_counts, "unreadable_file")
                continue
            files.append(
                WorkspaceManifestFile(
                    relative_path=path.resolve().relative_to(root).as_posix(),
                    source_kind=workspace_source_kind(path),
                    extension=path.suffix.casefold(),
                    size_bytes=stat.st_size,
                    modified_at_utc=datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
                    content_hash=hashlib.sha256(content).hexdigest(),
                )
            )

    files.sort(key=lambda item: item.relative_path)
    source_kind_counts = _count_values(item.source_kind for item in files)
    extension_counts = _count_values(item.extension for item in files)
    root_digest = hashlib.sha256(root.as_posix().encode("utf-8")).hexdigest()[:12]
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    return WorkspaceManifestFrame(
        frame_id=f"workspace:manifest:{turn_id}:{root_digest}",
        workspace_label=root.name or root.drive or "workspace",
        root_path=root.as_posix(),
        observed_at=timestamp,
        manifest_status="ready" if files else "no_supported_files",
        access_mode="read_only",
        local_model_only=True,
        automatic_graph_ingest_status="not_run",
        supported_extensions=sorted(WORKSPACE_SUPPORTED_EXTENSIONS),
        candidate_file_count=len(files),
        source_kind_counts=source_kind_counts,
        extension_counts=extension_counts,
        excluded_file_count=excluded_file_count,
        excluded_directory_count=excluded_directory_count,
        exclusion_reason_counts=dict(sorted(exclusion_reason_counts.items())),
        files=files,
    )


def record_workspace_manifest(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    root_path: str | Path,
    input_ref: list[str],
) -> RecordedWorkspaceManifest:
    frame = build_workspace_manifest(root_path=root_path, turn_id=turn_id)
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="node_0",
        event_type="workspace_manifest",
        input_ref=input_ref,
        output_ref=[frame.frame_id],
        schema_status="passed",
    )
    data_store.create_record(
        data_id=frame.frame_id,
        data_type=WORKSPACE_MANIFEST_DATA_TYPE,
        exists=True,
        created_at=event.timestamp,
        source_trace_id=event.event_id,
        payload=asdict(frame),
    )
    return RecordedWorkspaceManifest(
        frame=frame,
        trace_event_id=event.event_id,
        data_id=frame.frame_id,
    )


def workspace_manifest_memory_item(frame: WorkspaceManifestFrame) -> MemoryItem:
    """node_0이 node_1에게 의미 판단 없이 복사할 workspace 상황판이다."""

    return MemoryItem(
        item_id=f"{frame.frame_id}:node_1_workspace_context",
        item_type="active_workspace_manifest",
        text=(
            "COPIED_FIELDS:"
            f"workspace_label={frame.workspace_label};"
            f"manifest_status={frame.manifest_status};"
            f"candidate_file_count={frame.candidate_file_count};"
            f"workspace_document_count={frame.source_kind_counts.get('workspace_document', 0)};"
            f"workspace_code_or_config_count={frame.source_kind_counts.get('workspace_code_or_config', 0)};"
            f"access_mode={frame.access_mode};"
            f"automatic_graph_ingest_status={frame.automatic_graph_ingest_status}"
        ),
        source_trace_ids=[],
        source_data_ids=[frame.frame_id],
    )


def workspace_manifest_cli_payload(frame: WorkspaceManifestFrame) -> dict[str, object]:
    """전체 hash 목록 대신 사람이 먼저 볼 안전 경계만 CLI에 표시한다."""

    return {
        "status": "WORKSPACE_CHECK_OK",
        "workspace_label": frame.workspace_label,
        "root_path": frame.root_path,
        "manifest_status": frame.manifest_status,
        "access_mode": frame.access_mode,
        "local_model_only": frame.local_model_only,
        "automatic_graph_ingest_status": frame.automatic_graph_ingest_status,
        "supported_extensions": frame.supported_extensions,
        "candidate_file_count": frame.candidate_file_count,
        "source_kind_counts": frame.source_kind_counts,
        "extension_counts": frame.extension_counts,
        "excluded_file_count": frame.excluded_file_count,
        "excluded_directory_count": frame.excluded_directory_count,
        "exclusion_reason_counts": frame.exclusion_reason_counts,
        "candidate_relative_paths": [item.relative_path for item in frame.files],
        "generated_by": frame.generated_by,
        "info_class": frame.info_class,
        "semantic_judgement_status": frame.semantic_judgement_status,
    }


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _count_values(values: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return dict(sorted(counts.items()))


__all__ = [
    "RecordedWorkspaceManifest",
    "WORKSPACE_MANIFEST_DATA_TYPE",
    "WORKSPACE_MANIFEST_GENERATOR",
    "WORKSPACE_MANIFEST_POLICY_ID",
    "WorkspaceManifestFile",
    "WorkspaceManifestFrame",
    "build_workspace_manifest",
    "record_workspace_manifest",
    "workspace_manifest_cli_payload",
    "workspace_manifest_memory_item",
]
