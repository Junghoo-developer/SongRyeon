from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from songryeon_core.core.data_store import DataStore
from songryeon_core.core.graph_source_ingest import (
    GraphSourceKindIngestResult,
    record_graph_source_kind_ingest,
)
from songryeon_core.core.trace_store import TraceStore


SONGRYEON_CORE_SOURCE_MANIFEST_POLICY_ID = "SONGRYEON_CORE_SOURCE_MANIFEST_V0"
SONGRYEON_CORE_SOURCE_MANIFEST_GENERATOR = "CODE:SONGRYEON_CORE_SOURCE_MANIFEST"
SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE = "graph_source:songryeon_core_source_manifest_frame"
SONGRYEON_CORE_SOURCE_MANIFEST_EXPLICIT_PATHS = {
    "internal_document": [
        "AGENTS.md",
        "README.md",
    ],
    "source_code_file": [
        "main.py",
    ],
}
SONGRYEON_CORE_SOURCE_MANIFEST_GLOBS = {
    "internal_document": [
        "Administrative_Reform_1/**/*.md",
    ],
    "source_code_file": [
        "songryeon_core/**/*.py",
        "tests/**/*.py",
    ],
}


@dataclass(frozen=True)
class SongRyeonCoreSourceManifest:
    frame_id: str
    root_path: str
    policy_id: str
    explicit_paths_by_kind: dict[str, list[str]]
    glob_patterns_by_kind: dict[str, list[str]]
    source_paths_by_kind: dict[str, list[str]]
    source_kind_counts: dict[str, int]
    generated_by: str = SONGRYEON_CORE_SOURCE_MANIFEST_GENERATOR
    info_class: str = "absolute"
    semantic_judgement_status: str = "not_run"


@dataclass(frozen=True)
class SongRyeonCoreSourceManifestIngestResult:
    manifest: SongRyeonCoreSourceManifest
    manifest_trace_event_id: str
    manifest_data_id: str
    ingest_result: GraphSourceKindIngestResult


def songryeon_core_source_manifest_frame_id(batch_id: str) -> str:
    return f"graph_source:songryeon_core_source_manifest:{batch_id}"


def resolve_songryeon_core_source_manifest(
    *,
    root_path: str | Path,
    batch_id: str,
) -> SongRyeonCoreSourceManifest:
    root = Path(root_path).resolve()
    if not root.exists():
        raise FileNotFoundError(root.as_posix())
    if not root.is_dir():
        raise ValueError(f"SongRyeon Core root must be a directory: {root.as_posix()}")

    source_paths_by_kind: dict[str, list[str]] = {}
    for source_kind in sorted(
        {
            *SONGRYEON_CORE_SOURCE_MANIFEST_EXPLICIT_PATHS.keys(),
            *SONGRYEON_CORE_SOURCE_MANIFEST_GLOBS.keys(),
        }
    ):
        resolved_paths: list[Path] = []
        for relative_path in SONGRYEON_CORE_SOURCE_MANIFEST_EXPLICIT_PATHS.get(
            source_kind,
            [],
        ):
            path = root / relative_path
            if not path.exists():
                raise FileNotFoundError(path.as_posix())
            if not path.is_file():
                raise ValueError(f"manifest explicit path must be a file: {path.as_posix()}")
            resolved_paths.append(path)

        for pattern in SONGRYEON_CORE_SOURCE_MANIFEST_GLOBS.get(source_kind, []):
            resolved_paths.extend(
                path
                for path in sorted(root.glob(pattern))
                if path.is_file()
            )
        source_paths_by_kind[source_kind] = _dedupe_paths(resolved_paths)

    return SongRyeonCoreSourceManifest(
        frame_id=songryeon_core_source_manifest_frame_id(batch_id),
        root_path=root.as_posix(),
        policy_id=SONGRYEON_CORE_SOURCE_MANIFEST_POLICY_ID,
        explicit_paths_by_kind={
            key: list(values)
            for key, values in SONGRYEON_CORE_SOURCE_MANIFEST_EXPLICIT_PATHS.items()
        },
        glob_patterns_by_kind={
            key: list(values)
            for key, values in SONGRYEON_CORE_SOURCE_MANIFEST_GLOBS.items()
        },
        source_paths_by_kind=source_paths_by_kind,
        source_kind_counts={
            source_kind: len(paths)
            for source_kind, paths in source_paths_by_kind.items()
        },
    )


def record_songryeon_core_source_manifest_ingest(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    root_path: str | Path,
    turn_id: str,
    batch_id: str,
    observed_at: str | None = None,
    ingested_at: str | None = None,
) -> SongRyeonCoreSourceManifestIngestResult:
    """Resolve the approved SongRyeon Core manifest and ingest raw source snapshots."""

    manifest = resolve_songryeon_core_source_manifest(
        root_path=root_path,
        batch_id=batch_id,
    )
    manifest_event = trace_store.create_event(
        turn_id=turn_id,
        actor="songryeon_core_source_manifest",
        event_type="node_output",
        output_ref=[manifest.frame_id],
        schema_status="passed",
    )
    _record_manifest_payload_if_missing(
        data_store=data_store,
        manifest=manifest,
        created_at=manifest_event.timestamp,
        source_trace_id=manifest_event.event_id,
    )
    ingest_result = record_graph_source_kind_ingest(
        trace_store=trace_store,
        data_store=data_store,
        turn_id=turn_id,
        batch_id=batch_id,
        source_paths_by_kind=manifest.source_paths_by_kind,
        input_ref=[manifest_event.event_id],
        observed_at=observed_at,
        ingested_at=ingested_at,
        store_text_snapshots=True,
    )
    return SongRyeonCoreSourceManifestIngestResult(
        manifest=manifest,
        manifest_trace_event_id=manifest_event.event_id,
        manifest_data_id=manifest.frame_id,
        ingest_result=ingest_result,
    )


def _record_manifest_payload_if_missing(
    *,
    data_store: DataStore,
    manifest: SongRyeonCoreSourceManifest,
    created_at: str,
    source_trace_id: str,
) -> None:
    payload = {
        "frame_id": manifest.frame_id,
        "root_path": manifest.root_path,
        "policy_id": manifest.policy_id,
        "explicit_paths_by_kind": manifest.explicit_paths_by_kind,
        "glob_patterns_by_kind": manifest.glob_patterns_by_kind,
        "source_paths_by_kind": manifest.source_paths_by_kind,
        "source_kind_counts": manifest.source_kind_counts,
        "generated_by": manifest.generated_by,
        "info_class": manifest.info_class,
        "semantic_judgement_status": manifest.semantic_judgement_status,
    }
    existing = data_store.get_record(manifest.frame_id)
    if existing is not None:
        if existing.data_type != SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE:
            raise ValueError(f"manifest data_id collision with different type: {manifest.frame_id}")
        if existing.payload != payload:
            raise ValueError(
                f"manifest data_id collision with different payload: {manifest.frame_id}"
            )
        return
    data_store.create_record(
        data_id=manifest.frame_id,
        data_type=SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE,
        exists=True,
        created_at=created_at,
        source_trace_id=source_trace_id,
        payload=payload,
    )


def _dedupe_paths(paths: list[Path]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        normalized = path.resolve().as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


__all__ = [
    "SONGRYEON_CORE_SOURCE_MANIFEST_DATA_TYPE",
    "SONGRYEON_CORE_SOURCE_MANIFEST_EXPLICIT_PATHS",
    "SONGRYEON_CORE_SOURCE_MANIFEST_GENERATOR",
    "SONGRYEON_CORE_SOURCE_MANIFEST_GLOBS",
    "SONGRYEON_CORE_SOURCE_MANIFEST_POLICY_ID",
    "SongRyeonCoreSourceManifest",
    "SongRyeonCoreSourceManifestIngestResult",
    "record_songryeon_core_source_manifest_ingest",
    "resolve_songryeon_core_source_manifest",
    "songryeon_core_source_manifest_frame_id",
]
