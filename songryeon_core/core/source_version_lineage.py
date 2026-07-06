from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime

from songryeon_core.core.data_store import DataRecord, DataStore
from songryeon_core.core.schemas import (
    SourceObservationLedgerFrame,
    SourceVersionLineageFrame,
    SummaryInvalidationLedgerFrame,
    validate_source_observation_ledger_frame,
    validate_source_version_lineage_frame,
    validate_summary_invalidation_ledger_frame,
)
from songryeon_core.core.trace_store import TraceStore


SOURCE_VERSION_LINEAGE_FRAME_DATA_TYPE = "graph_source:source_version_lineage_frame"
SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE = "graph_source:source_observation_ledger_frame"
SUMMARY_INVALIDATION_LEDGER_FRAME_DATA_TYPE = "graph_source:summary_invalidation_ledger_frame"
SOURCE_VERSION_LINEAGE_POLICY_ID = "SOURCE_VERSION_LINEAGE_V0"
SOURCE_OBSERVATION_LEDGER_POLICY_ID = "SOURCE_OBSERVATION_LEDGER_V0"
SUMMARY_INVALIDATION_LEDGER_POLICY_ID = "SUMMARY_INVALIDATION_LEDGER_V0"

# 학습용 큰 그림:
# 이 파일은 "이 자료가 동적이냐 정적이냐"를 직접 판정하는 곳이 아니다.
# 대신 같은 경로의 원본이 언제 어떤 내용 hash로 관측되었는지 줄 세우고,
# 그 줄에서 최신 원본과 밀려난 원본을 구분한다.
#
# 왜 이게 중요하냐면, LLM 요약은 원본 자체가 아니라 "특정 원본 버전"을 보고
# 만들어진 파생 정보이기 때문이다. 원본이 바뀌면 옛 요약을 지우는 대신
# "이 요약은 옛 버전에 붙은 요약이다"라고 추적 가능하게 무효화해야 한다.


@dataclass(frozen=True)
class RecordedSourceVersionLineageResult:
    # 한 번 lineage/invalidation 기록을 실행한 뒤의 결과 봉투.
    # 새로 만든 data id와 이미 있던 data id를 나눠 두면,
    # 같은 작업을 다시 돌렸을 때 중복 생성인지 실제 새 기록인지 구분할 수 있다.
    lineage_frames: list[SourceVersionLineageFrame]
    observation_ledger: SourceObservationLedgerFrame
    invalidation_ledger: SummaryInvalidationLedgerFrame
    trace_event_id: str
    created_data_ids: list[str]
    existing_data_ids: list[str]


@dataclass(frozen=True)
class _SourceVersion:
    # DataStore 안에 흩어진 raw_source record와 file_metadata record를
    # lineage 계산용으로 작게 다시 묶은 내부 전용 카드.
    # 외부 schema가 아니라 이 파일 안에서 정렬/비교하기 쉽게 만든 작업용 구조다.
    source_kind: str
    path: str
    source_graph_node_id: str
    source_file_data_id: str
    content_sha1: str
    observed_at: str
    ingested_at: str
    source_last_modified_at: str
    source_trace_id: str | None


def source_version_lineage_frame_id(
    *,
    source_kind: str,
    path: str,
    active_source_graph_node_id: str | None = None,
) -> str:
    identity_digest = _source_identity_digest(source_kind, path)
    if active_source_graph_node_id is None:
        return f"graph_source:source_version_lineage:{identity_digest}"
    active_digest = hashlib.sha1(
        active_source_graph_node_id.encode("utf-8")
    ).hexdigest()[:16]
    return f"graph_source:source_version_lineage:{identity_digest}:{active_digest}"


def source_identity_key(*, source_kind: str, path: str) -> str:
    return f"source_identity:{_source_identity_digest(source_kind, path)}"


def summary_invalidation_ledger_frame_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_source:summary_invalidation_ledger:{batch_id}"


def source_observation_ledger_frame_id(batch_id: str) -> str:
    if not batch_id:
        raise ValueError("batch_id must not be empty")
    return f"graph_source:source_observation_ledger:{batch_id}"


def build_source_version_lineage_frames(
    *,
    data_store: DataStore,
) -> list[SourceVersionLineageFrame]:
    """Build absolute source version lineages from existing raw_source records."""

    # 1단계: 같은 source_kind + path를 가진 관측본끼리 한 바구니에 모은다.
    # 예를 들어 같은 README.md가 두 번 관측되었다면 같은 바구니로 들어간다.
    versions_by_identity: dict[tuple[str, str], list[_SourceVersion]] = {}
    for version in _iter_source_versions(data_store):
        versions_by_identity.setdefault((version.source_kind, version.path), []).append(version)

    frames: list[SourceVersionLineageFrame] = []
    for (source_kind, path), versions in sorted(versions_by_identity.items()):
        # 2단계: 관측 시각과 graph node id 기준으로 순서를 정한다.
        # 이 순서의 마지막 항목이 현재 active source version이 된다.
        ordered_versions = sorted(
            versions,
            key=lambda item: (item.observed_at, item.source_graph_node_id),
        )
        frame = _build_lineage_frame(
            source_kind=source_kind,
            path=path,
            versions=ordered_versions,
        )
        validate_source_version_lineage_frame(frame)
        frames.append(frame)
    return frames


def build_summary_invalidation_ledger_frame(
    *,
    data_store: DataStore,
    batch_id: str,
    lineage_frames: list[SourceVersionLineageFrame],
    invalidated_at: str | None = None,
) -> SummaryInvalidationLedgerFrame:
    """Build an absolute ledger for summaries derived from superseded source versions."""

    timestamp = invalidated_at or _now_iso()
    # content_changed인 lineage만 요약 무효화 후보가 된다.
    # single_version이면 비교할 과거 버전이 없으므로 무효화할 요약도 없다.
    changed_lineages = [
        frame for frame in lineage_frames if frame.lineage_status == "content_changed"
    ]
    superseded_to_active: dict[str, tuple[SourceVersionLineageFrame, str]] = {}
    for frame in changed_lineages:
        for superseded_source_id in frame.superseded_source_graph_node_ids:
            superseded_to_active[superseded_source_id] = (
                frame,
                frame.active_source_graph_node_id,
            )

    invalidated_summary_node_ids: list[str] = []
    invalidation_records: list[dict[str, str]] = []
    for summary_record in _iter_summary_records(data_store):
        payload = summary_record.payload
        if not isinstance(payload, dict):
            continue
        summary_node_id = _payload_text(payload, "node_id") or summary_record.data_id
        source_graph_node_ids = _string_list(payload.get("source_graph_node_ids"))
        # 요약 node가 바라본 source_graph_node_ids 중 하나가 superseded라면,
        # 그 요약은 최신 원본에 대한 요약으로는 더 이상 쓰면 안 된다.
        # 여기서도 요약을 삭제하지 않고 invalidation ledger에만 기록한다.
        for source_graph_node_id in source_graph_node_ids:
            if source_graph_node_id not in superseded_to_active:
                continue
            lineage_frame, active_source_graph_node_id = superseded_to_active[
                source_graph_node_id
            ]
            invalidated_summary_node_ids.append(summary_node_id)
            invalidation_records.append(
                {
                    "summary_graph_node_id": summary_node_id,
                    "invalidated_reason_code": "source_content_changed",
                    "source_lineage_frame_id": lineage_frame.frame_id,
                    "superseded_source_graph_node_id": source_graph_node_id,
                    "superseding_source_graph_node_id": active_source_graph_node_id,
                    "invalidated_at": timestamp,
                    "validity_status": "invalidated_by_source_change",
                }
            )

    frame = SummaryInvalidationLedgerFrame(
        frame_id=summary_invalidation_ledger_frame_id(batch_id),
        batch_id=batch_id,
        ledger_status="invalidations_recorded"
        if invalidation_records
        else "no_invalidations",
        invalidated_summary_node_ids=_unique_strings(invalidated_summary_node_ids),
        invalidation_records=_dedupe_invalidation_records(invalidation_records),
        changed_source_lineage_frame_ids=_unique_strings(
            [frame.frame_id for frame in changed_lineages]
        ),
        changed_source_graph_node_ids=_unique_strings(
            [
                source_graph_node_id
                for frame in changed_lineages
                for source_graph_node_id in frame.superseded_source_graph_node_ids
            ]
        ),
        active_source_graph_node_ids=_unique_strings(
            [frame.active_source_graph_node_id for frame in changed_lineages]
        ),
        source_graph_node_ids=_unique_strings(
            [
                source_graph_node_id
                for frame in changed_lineages
                for source_graph_node_id in frame.version_source_graph_node_ids
            ]
        ),
        source_trace_ids=_unique_strings(
            [
                trace_id
                for frame in changed_lineages
                for trace_id in frame.source_trace_ids
            ]
        ),
        source_data_ids=_unique_strings(
            [
                *[frame.frame_id for frame in changed_lineages],
                *[
                    data_id
                    for frame in changed_lineages
                    for data_id in frame.source_data_ids
                ],
                *[record["summary_graph_node_id"] for record in invalidation_records],
            ]
        ),
    )
    validate_summary_invalidation_ledger_frame(frame)
    return frame


def build_source_observation_ledger_frame(
    *,
    data_store: DataStore,
    batch_id: str,
    observed_source_file_data_ids: list[str] | None = None,
) -> SourceObservationLedgerFrame:
    """Build a per-batch absolute ledger of source observations."""

    # observation ledger는 "이번 batch에서 무엇을 봤는가"를 적는 출석부에 가깝다.
    # lineage frame이 파일별 전체 버전 족보라면,
    # observation ledger는 이번 실행에서 새로 확인한 관측 사건 목록이다.
    metadata_records = _metadata_records_by_data_id(data_store)
    raw_source_by_identity_content = _raw_source_id_by_identity_content(data_store)
    metadata_by_identity = _metadata_records_by_identity(data_store)
    target_ids = (
        _unique_strings(observed_source_file_data_ids or [])
        if observed_source_file_data_ids is not None
        else sorted(metadata_records)
    )

    observation_records: list[dict[str, str]] = []
    for source_file_data_id in target_ids:
        metadata_record = metadata_records.get(source_file_data_id)
        if metadata_record is None or not isinstance(metadata_record.payload, dict):
            continue
        payload = metadata_record.payload
        source_kind = _payload_text(payload, "source_kind")
        path = _payload_text(payload, "path")
        content_sha1 = _payload_text(payload, "content_sha1")
        observed_at = _payload_text(payload, "observed_at")
        if not all([source_kind, path, content_sha1, observed_at]):
            continue

        active_source_graph_node_id = raw_source_by_identity_content.get(
            (source_kind, path, content_sha1),
            "",
        )
        previous_active_source_graph_node_id = ""
        observation_status = "new_source_version"
        previous_metadata = _previous_metadata_record(
            metadata_by_identity.get((source_kind, path), []),
            source_file_data_id=source_file_data_id,
            observed_at=observed_at,
        )
        if previous_metadata is not None and isinstance(previous_metadata.payload, dict):
            previous_content_sha1 = _payload_text(previous_metadata.payload, "content_sha1")
            previous_active_source_graph_node_id = raw_source_by_identity_content.get(
                (
                    source_kind,
                    path,
                    previous_content_sha1,
                ),
                "",
            )
            observation_status = (
                "unchanged"
                if previous_content_sha1 == content_sha1
                else "content_changed"
            )
        # 여기서 "동적 파일"이라고 추측하지 않는다.
        # 오직 이전 content_sha1과 지금 content_sha1이 같은지 다른지만 본다.
        # 이것이 송련식 절대정보 판정이다.

        if not active_source_graph_node_id:
            continue
        observation_records.append(
            {
                "source_file_data_id": source_file_data_id,
                "source_kind": source_kind,
                "path": path,
                "observed_at": observed_at,
                "content_sha1": content_sha1,
                "observation_status": observation_status,
                "active_source_graph_node_id": active_source_graph_node_id,
                "previous_active_source_graph_node_id": previous_active_source_graph_node_id,
            }
        )

    frame = SourceObservationLedgerFrame(
        frame_id=source_observation_ledger_frame_id(batch_id),
        batch_id=batch_id,
        ledger_status="recorded" if observation_records else "no_observations",
        observation_records=observation_records,
        observation_status_counts=_count_observation_statuses(observation_records),
        observed_source_file_data_ids=_unique_strings(
            [record["source_file_data_id"] for record in observation_records]
        ),
        active_source_graph_node_ids=_unique_strings(
            [record["active_source_graph_node_id"] for record in observation_records]
        ),
        source_graph_node_ids=_unique_strings(
            [record["active_source_graph_node_id"] for record in observation_records]
        ),
        source_trace_ids=_unique_strings(
            [
                metadata_records[record["source_file_data_id"]].source_trace_id
                for record in observation_records
                if record["source_file_data_id"] in metadata_records
            ]
        ),
        source_data_ids=_unique_strings(
            [
                *[record["source_file_data_id"] for record in observation_records],
                *[record["active_source_graph_node_id"] for record in observation_records],
            ]
        ),
    )
    validate_source_observation_ledger_frame(frame)
    return frame


def record_source_version_lineage_and_summary_invalidation(
    *,
    trace_store: TraceStore,
    data_store: DataStore,
    turn_id: str,
    batch_id: str,
    input_ref: list[str] | None = None,
    observed_source_file_data_ids: list[str] | None = None,
    created_at: str | None = None,
) -> RecordedSourceVersionLineageResult:
    """Record lineage and invalidation frames without mutating source or summary records."""

    if not turn_id:
        raise ValueError("turn_id must not be empty")
    if not batch_id:
        raise ValueError("batch_id must not be empty")

    timestamp = created_at or _now_iso()
    # 아래 세 frame은 서로 역할이 다르다.
    # lineage_frames: 같은 원본의 버전 족보.
    # observation_ledger: 이번 batch에서 실제로 관측한 source 목록.
    # invalidation_ledger: 바뀐 원본 때문에 최신 근거로 쓰면 안 되는 요약 목록.
    lineage_frames = build_source_version_lineage_frames(data_store=data_store)
    observation_ledger = build_source_observation_ledger_frame(
        data_store=data_store,
        batch_id=batch_id,
        observed_source_file_data_ids=observed_source_file_data_ids,
    )
    invalidation_ledger = build_summary_invalidation_ledger_frame(
        data_store=data_store,
        batch_id=batch_id,
        lineage_frames=lineage_frames,
        invalidated_at=timestamp,
    )
    output_ref = [
        *[frame.frame_id for frame in lineage_frames],
        observation_ledger.frame_id,
        invalidation_ledger.frame_id,
    ]
    event = trace_store.create_event(
        turn_id=turn_id,
        actor="source_version_lineage_builder",
        event_type="node_output",
        timestamp=timestamp,
        input_ref=input_ref or [],
        output_ref=output_ref,
        schema_status="passed",
    )

    created_data_ids: list[str] = []
    existing_data_ids: list[str] = []
    for frame in lineage_frames:
        _record_payload_if_missing(
            data_store=data_store,
            data_id=frame.frame_id,
            data_type=SOURCE_VERSION_LINEAGE_FRAME_DATA_TYPE,
            payload=asdict(frame),
            created_at=timestamp,
            source_trace_id=event.event_id,
            created_data_ids=created_data_ids,
            existing_data_ids=existing_data_ids,
        )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=observation_ledger.frame_id,
        data_type=SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE,
        payload=asdict(observation_ledger),
        created_at=timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )
    _record_payload_if_missing(
        data_store=data_store,
        data_id=invalidation_ledger.frame_id,
        data_type=SUMMARY_INVALIDATION_LEDGER_FRAME_DATA_TYPE,
        payload=asdict(invalidation_ledger),
        created_at=timestamp,
        source_trace_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )

    return RecordedSourceVersionLineageResult(
        lineage_frames=lineage_frames,
        observation_ledger=observation_ledger,
        invalidation_ledger=invalidation_ledger,
        trace_event_id=event.event_id,
        created_data_ids=created_data_ids,
        existing_data_ids=existing_data_ids,
    )


def _build_lineage_frame(
    *,
    source_kind: str,
    path: str,
    versions: list[_SourceVersion],
) -> SourceVersionLineageFrame:
    source_graph_node_ids = [version.source_graph_node_id for version in versions]
    source_file_data_ids = [version.source_file_data_id for version in versions]
    # 정렬된 versions의 마지막을 active로 본다.
    # 이전 것들은 삭제하지 않고 superseded로 남긴다.
    # 그래야 나중에 "옛 요약이 왜 무효화됐는지" 되짚을 수 있다.
    active_source_graph_node_id = source_graph_node_ids[-1]
    superseded_source_graph_node_ids = source_graph_node_ids[:-1]
    content_sha1_values = {version.content_sha1 for version in versions}
    if len(versions) == 1:
        lineage_status = "single_version"
    else:
        lineage_status = "content_changed"

    version_records: list[dict[str, str]] = []
    previous_source_graph_node_id = ""
    for index, version in enumerate(versions, start=1):
        version_records.append(
            {
                "version_index": str(index),
                "source_graph_node_id": version.source_graph_node_id,
                "source_file_data_id": version.source_file_data_id,
                "content_sha1": version.content_sha1,
                "observed_at": version.observed_at,
                "ingested_at": version.ingested_at,
                "source_last_modified_at": version.source_last_modified_at,
                "supersedes_source_graph_node_id": previous_source_graph_node_id,
            }
        )
        previous_source_graph_node_id = version.source_graph_node_id

    return SourceVersionLineageFrame(
        frame_id=source_version_lineage_frame_id(
            source_kind=source_kind,
            path=path,
            active_source_graph_node_id=active_source_graph_node_id,
        ),
        source_identity_key=source_identity_key(source_kind=source_kind, path=path),
        source_kind=source_kind,
        path=path,
        lineage_status=lineage_status,
        active_source_graph_node_id=active_source_graph_node_id,
        version_source_graph_node_ids=source_graph_node_ids,
        superseded_source_graph_node_ids=superseded_source_graph_node_ids,
        source_file_data_ids=source_file_data_ids,
        version_records=version_records,
        content_sha1_by_version={
            version.source_graph_node_id: version.content_sha1 for version in versions
        },
        observed_at_by_version={
            version.source_graph_node_id: version.observed_at for version in versions
        },
        source_graph_node_ids=source_graph_node_ids,
        source_trace_ids=_unique_strings([version.source_trace_id for version in versions]),
        source_data_ids=_unique_strings(
            [
                *source_file_data_ids,
                *source_graph_node_ids,
            ]
        ),
    )


def _iter_source_versions(data_store: DataStore) -> list[_SourceVersion]:
    # raw_source record는 그래프의 원본 node이고,
    # graph_source:file_metadata record는 그 원본의 path/hash/관측시각 같은 설명 카드다.
    # 이 함수는 둘을 DataStore에서 찾아 연결해 _SourceVersion으로 변환한다.
    metadata_by_data_id = _metadata_records_by_data_id(data_store)
    versions: list[_SourceVersion] = []
    for record in data_store.list_records():
        if record.data_type != "graph_memory:node:raw_source":
            continue
        if not isinstance(record.payload, dict):
            continue
        for source_file_data_id in _string_list(record.payload.get("source_data_ids")):
            metadata_record = metadata_by_data_id.get(source_file_data_id)
            if metadata_record is None or not isinstance(metadata_record.payload, dict):
                continue
            source_kind = _payload_text(metadata_record.payload, "source_kind")
            path = _payload_text(metadata_record.payload, "path")
            content_sha1 = _payload_text(metadata_record.payload, "content_sha1")
            observed_at = _payload_text(metadata_record.payload, "observed_at")
            ingested_at = _payload_text(metadata_record.payload, "ingested_at")
            source_last_modified_at = _payload_text(
                metadata_record.payload,
                "source_last_modified_at",
            )
            if not all(
                [
                    source_kind,
                    path,
                    content_sha1,
                    observed_at,
                    ingested_at,
                    source_last_modified_at,
                ]
            ):
                continue
            versions.append(
                _SourceVersion(
                    source_kind=source_kind,
                    path=path,
                    source_graph_node_id=record.data_id,
                    source_file_data_id=source_file_data_id,
                    content_sha1=content_sha1,
                    observed_at=observed_at,
                    ingested_at=ingested_at,
                    source_last_modified_at=source_last_modified_at,
                    source_trace_id=record.source_trace_id or metadata_record.source_trace_id,
                )
            )
    return versions


def _metadata_records_by_data_id(data_store: DataStore) -> dict[str, DataRecord]:
    return {
        record.data_id: record
        for record in data_store.list_records()
        if record.data_type == "graph_source:file_metadata"
    }


def _metadata_records_by_identity(data_store: DataStore) -> dict[tuple[str, str], list[DataRecord]]:
    records_by_identity: dict[tuple[str, str], list[DataRecord]] = {}
    for record in data_store.list_records():
        if record.data_type != "graph_source:file_metadata":
            continue
        if not isinstance(record.payload, dict):
            continue
        source_kind = _payload_text(record.payload, "source_kind")
        path = _payload_text(record.payload, "path")
        if not source_kind or not path:
            continue
        records_by_identity.setdefault((source_kind, path), []).append(record)
    for records in records_by_identity.values():
        records.sort(
            key=lambda item: (
                _payload_text(item.payload, "observed_at")
                if isinstance(item.payload, dict)
                else "",
                item.data_id,
            )
        )
    return records_by_identity


def _raw_source_id_by_identity_content(data_store: DataStore) -> dict[tuple[str, str, str], str]:
    metadata_by_data_id = _metadata_records_by_data_id(data_store)
    raw_source_ids: dict[tuple[str, str, str], str] = {}
    for record in data_store.list_records():
        if record.data_type != "graph_memory:node:raw_source":
            continue
        if not isinstance(record.payload, dict):
            continue
        for source_file_data_id in _string_list(record.payload.get("source_data_ids")):
            metadata_record = metadata_by_data_id.get(source_file_data_id)
            if metadata_record is None or not isinstance(metadata_record.payload, dict):
                continue
            source_kind = _payload_text(metadata_record.payload, "source_kind")
            path = _payload_text(metadata_record.payload, "path")
            content_sha1 = _payload_text(metadata_record.payload, "content_sha1")
            if not all([source_kind, path, content_sha1]):
                continue
            raw_source_ids.setdefault((source_kind, path, content_sha1), record.data_id)
    return raw_source_ids


def _previous_metadata_record(
    records: list[DataRecord],
    *,
    source_file_data_id: str,
    observed_at: str,
) -> DataRecord | None:
    previous: DataRecord | None = None
    for record in records:
        if record.data_id == source_file_data_id:
            return previous
        if not isinstance(record.payload, dict):
            continue
        record_observed_at = _payload_text(record.payload, "observed_at")
        if record_observed_at > observed_at:
            return previous
        previous = record
    return previous


def _iter_summary_records(data_store: DataStore) -> list[DataRecord]:
    records: list[DataRecord] = []
    for record in data_store.list_records():
        if record.data_type == "graph_memory:node:summary":
            records.append(record)
            continue
        if not isinstance(record.payload, dict):
            continue
        if record.payload.get("node_kind") == "summary":
            records.append(record)
    return records


def _dedupe_invalidation_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for record in records:
        key = (
            record["summary_graph_node_id"],
            record["source_lineage_frame_id"],
            record["superseded_source_graph_node_id"],
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


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
            raise ValueError(f"source lineage data_id collision with different type: {data_id}")
        if existing.payload != payload:
            raise ValueError(f"source lineage data_id collision with different payload: {data_id}")
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


def _payload_text(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    return value if isinstance(value, str) else ""


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


def _count_observation_statuses(records: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        status = record.get("observation_status", "")
        if not status:
            continue
        counts[status] = counts.get(status, 0) + 1
    return counts


def _source_identity_digest(source_kind: str, path: str) -> str:
    if not source_kind:
        raise ValueError("source_kind must not be empty")
    if not path:
        raise ValueError("path must not be empty")
    digest_source = f"{source_kind}:{path}"
    return hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


__all__ = [
    "SOURCE_VERSION_LINEAGE_FRAME_DATA_TYPE",
    "SOURCE_OBSERVATION_LEDGER_FRAME_DATA_TYPE",
    "SOURCE_VERSION_LINEAGE_POLICY_ID",
    "SOURCE_OBSERVATION_LEDGER_POLICY_ID",
    "SUMMARY_INVALIDATION_LEDGER_FRAME_DATA_TYPE",
    "SUMMARY_INVALIDATION_LEDGER_POLICY_ID",
    "RecordedSourceVersionLineageResult",
    "build_source_version_lineage_frames",
    "build_source_observation_ledger_frame",
    "build_summary_invalidation_ledger_frame",
    "record_source_version_lineage_and_summary_invalidation",
    "source_identity_key",
    "source_observation_ledger_frame_id",
    "source_version_lineage_frame_id",
    "summary_invalidation_ledger_frame_id",
]
