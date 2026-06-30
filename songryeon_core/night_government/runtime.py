from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from songryeon_core.night_government.schemas import (
    MEMORY_ROLES,
    MemoryActivationItem,
    MemoryRecord,
    NightGovernmentPacket,
    validate_night_government_packet,
)
from songryeon_core.night_government.store import NightGovernmentStore


DEFAULT_NIGHT_DB_DIR = ".songryeon_core_cache/night_government"
NIGHT_GOVERNMENT_GENERATOR = "code:night_government_mvp_v0"

ROLE_PRIORITY = {
    "fact": 0,
    "failure": 1,
    "lesson": 2,
    "hypothesis": 3,
    "association": 4,
    "emotion": 5,
    "raw": 6,
}


def ingest_memory_record(
    *,
    db_dir: str | Path = DEFAULT_NIGHT_DB_DIR,
    text: str,
    record_type: str = "manual_note",
    memory_role: str = "raw",
    tags: list[str] | None = None,
    source_refs: list[str] | None = None,
    record_id: str | None = None,
    created_at: str | None = None,
    confidence_label: str = "unknown",
    human_review_status: str = "unreviewed",
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    now = created_at or _utc_now()
    record = MemoryRecord(
        record_id=record_id or _record_id(now, text),
        record_type=record_type,
        text=text,
        created_at=now,
        memory_role=memory_role,
        confidence_label=confidence_label,
        human_review_status=human_review_status,
        tags=tags or [],
        source_refs=source_refs or [],
        metadata=metadata or {},
    )
    store = NightGovernmentStore(db_dir)
    store.append_record(record)
    return {
        "status": "NIGHT_MEMORY_INGESTED",
        "db_dir": str(store.db_dir),
        "record": asdict(record),
        "record_count": len(store.list_records()),
    }


def run_night_government(
    *,
    db_dir: str | Path = DEFAULT_NIGHT_DB_DIR,
    day_id: str | None = None,
    active_goal: str = "",
    max_records: int = 24,
    created_at: str | None = None,
) -> dict[str, object]:
    if max_records <= 0:
        raise ValueError("max_records must be positive")
    store = NightGovernmentStore(db_dir)
    records = _candidate_records(store.list_records())
    selected = _select_records(records, max_records=max_records)
    now = created_at or _utc_now()
    packet = NightGovernmentPacket(
        packet_id=_packet_id(day_id or _day_id(now), now, selected),
        day_id=day_id or _day_id(now),
        created_at=now,
        generated_by=NIGHT_GOVERNMENT_GENERATOR,
        active_goal=active_goal,
        input_record_ids=[record.record_id for record in selected],
        active_memory_items=_activation_items(selected),
        role_counts=_role_counts(selected),
        current_limits=[
            "old or false memories are preserved but must not be promoted as current facts",
            "activation item use_as controls how the next turn may use the memory",
            "human_review_status is exposed because unreviewed memory needs caution",
        ],
    )
    validate_night_government_packet(packet)
    store.append_packet(packet)
    active_path = store.save_active_packet(packet)
    return {
        "status": "NIGHT_GOVERNMENT_OK",
        "db_dir": str(store.db_dir),
        "packet_id": packet.packet_id,
        "day_id": packet.day_id,
        "input_record_count": len(packet.input_record_ids),
        "active_memory_item_count": len(packet.active_memory_items),
        "role_counts": packet.role_counts,
        "active_packet_path": str(active_path),
        "active_packet": asdict(packet),
    }


def load_active_memory_packet(
    *,
    db_dir: str | Path = DEFAULT_NIGHT_DB_DIR,
) -> dict[str, object] | None:
    packet = NightGovernmentStore(db_dir).load_active_packet()
    if packet is None:
        return None
    return asdict(packet)


def render_active_memory_packet_markdown(packet: dict[str, object] | None) -> str:
    if packet is None:
        return "NO_ACTIVE_MEMORY_PACKET"
    lines = [
        f"# Active Memory Packet: {packet.get('packet_id')}",
        "",
        f"- day_id: {packet.get('day_id')}",
        f"- generated_by: {packet.get('generated_by')}",
        f"- active_goal: {packet.get('active_goal') or '(none)'}",
        f"- input_record_count: {len(packet.get('input_record_ids') or [])}",
        "",
        "## Items",
    ]
    for item in packet.get("active_memory_items") or []:
        if not isinstance(item, dict):
            continue
        lines.extend(
            [
                "",
                f"### {item.get('item_id')}",
                f"- source_record_id: {item.get('source_record_id')}",
                f"- role: {item.get('memory_role')}",
                f"- use_as: {item.get('use_as')}",
                f"- confidence: {item.get('confidence_label')}",
                f"- review: {item.get('human_review_status')}",
                f"- activation_reason: {item.get('activation_reason')}",
                "",
                str(item.get("text") or ""),
            ]
        )
    return "\n".join(lines)


def _candidate_records(records: list[MemoryRecord]) -> list[MemoryRecord]:
    return [record for record in records if record.record_type != "night_packet"]


def _select_records(records: list[MemoryRecord], *, max_records: int) -> list[MemoryRecord]:
    buckets: dict[str, list[MemoryRecord]] = {
        role: [] for role in sorted(MEMORY_ROLES, key=lambda role: ROLE_PRIORITY.get(role, 99))
    }
    for record in records:
        buckets.setdefault(record.memory_role, []).append(record)
    for bucket in buckets.values():
        bucket.sort(key=lambda record: (record.created_at, record.record_id), reverse=True)

    selected: list[MemoryRecord] = []
    while len(selected) < max_records:
        progressed = False
        for role in sorted(buckets, key=lambda item: ROLE_PRIORITY.get(item, 99)):
            bucket = buckets[role]
            if not bucket:
                continue
            selected.append(bucket.pop(0))
            progressed = True
            if len(selected) >= max_records:
                break
        if not progressed:
            break
    return selected


def _activation_items(records: list[MemoryRecord]) -> list[MemoryActivationItem]:
    return [
        MemoryActivationItem(
            item_id=f"active_memory:{index:04d}",
            source_record_id=record.record_id,
            text=record.text,
            memory_role=record.memory_role,
            use_as=_use_as(record.memory_role),
            activation_reason=_activation_reason(record.memory_role),
            confidence_label=record.confidence_label,
            human_review_status=record.human_review_status,
            tags=list(record.tags),
            source_refs=list(record.source_refs),
        )
        for index, record in enumerate(records, start=1)
    ]


def _use_as(memory_role: str) -> str:
    if memory_role == "fact":
        return "fact"
    if memory_role in {"failure", "lesson"}:
        return "warning"
    if memory_role == "hypothesis":
        return "hypothesis"
    if memory_role == "association":
        return "association"
    return "context"


def _activation_reason(memory_role: str) -> str:
    if memory_role == "fact":
        return "ROLE:fact:usable_only_with_source_and_review_status"
    if memory_role == "failure":
        return "ROLE:failure:preserve_as_warning_not_current_fact"
    if memory_role == "lesson":
        return "ROLE:lesson:preserve_as_human_or_runtime_learning"
    if memory_role == "hypothesis":
        return "ROLE:hypothesis:must_be_rechecked_before_use_as_fact"
    if memory_role == "association":
        return "ROLE:association:may_seed_creative_link_not_evidence"
    if memory_role == "emotion":
        return "ROLE:emotion:context_signal_not_evidence"
    return "ROLE:raw:context_only_until_reviewed_or_derived"


def _role_counts(records: list[MemoryRecord]) -> dict[str, int]:
    counts = {role: 0 for role in sorted(MEMORY_ROLES)}
    for record in records:
        counts[record.memory_role] += 1
    return counts


def _record_id(created_at: str, text: str) -> str:
    digest = hashlib.sha256(f"{created_at}\n{text}".encode("utf-8")).hexdigest()[:12]
    safe_ts = created_at.replace(":", "").replace("-", "").replace("+", "z")
    return f"mem_{safe_ts}_{digest}"


def _packet_id(day_id: str, created_at: str, records: list[MemoryRecord]) -> str:
    digest_source = "\n".join([created_at, *[record.record_id for record in records]])
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
    safe_day = day_id.replace(":", "").replace("/", "_")
    return f"night_packet_{safe_day}_{digest}"


def _day_id(created_at: str) -> str:
    return created_at[:10]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
