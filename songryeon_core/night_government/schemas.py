from __future__ import annotations

import json
from dataclasses import dataclass, field


MEMORY_RECORD_SCHEMA_NAME = "NightGovernmentMemoryRecord"
MEMORY_RECORD_SCHEMA_VERSION = "0.1"
MEMORY_ACTIVATION_ITEM_SCHEMA_NAME = "NightGovernmentMemoryActivationItem"
MEMORY_ACTIVATION_ITEM_SCHEMA_VERSION = "0.1"
NIGHT_PACKET_SCHEMA_NAME = "NightGovernmentPacket"
NIGHT_PACKET_SCHEMA_VERSION = "0.1"

MEMORY_ROLES = {
    "raw",
    "fact",
    "hypothesis",
    "failure",
    "lesson",
    "emotion",
    "association",
}
MEMORY_RECORD_TYPES = {
    "manual_note",
    "coding_event",
    "raw_turn",
    "runtime_export",
    "night_packet",
}
CONFIDENCE_LABELS = {"unknown", "low", "medium", "high", "verified"}
HUMAN_REVIEW_STATUSES = {"unreviewed", "human_approved", "human_rejected"}
MEMORY_USE_MODES = {"fact", "warning", "hypothesis", "association", "context"}


@dataclass
class MemoryRecord:
    """One durable external memory fragment.

    A record can be false, stale, or merely emotional. The role and review fields
    are part of the data because old memories are not deleted just because they
    are not current facts.
    """

    record_id: str
    record_type: str
    text: str
    created_at: str
    memory_role: str = "raw"
    confidence_label: str = "unknown"
    human_review_status: str = "unreviewed"
    tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    derived_from_record_ids: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    schema_name: str = MEMORY_RECORD_SCHEMA_NAME
    schema_version: str = MEMORY_RECORD_SCHEMA_VERSION


@dataclass
class MemoryActivationItem:
    """A record converted into current working material."""

    item_id: str
    source_record_id: str
    text: str
    memory_role: str
    use_as: str
    activation_reason: str
    confidence_label: str
    human_review_status: str
    tags: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    schema_name: str = MEMORY_ACTIVATION_ITEM_SCHEMA_NAME
    schema_version: str = MEMORY_ACTIVATION_ITEM_SCHEMA_VERSION


@dataclass
class NightGovernmentPacket:
    """Nightly packet that prepares external memories for the next active turn."""

    packet_id: str
    day_id: str
    created_at: str
    generated_by: str
    active_goal: str
    input_record_ids: list[str]
    active_memory_items: list[MemoryActivationItem]
    role_counts: dict[str, int]
    current_limits: list[str] = field(default_factory=list)
    schema_name: str = NIGHT_PACKET_SCHEMA_NAME
    schema_version: str = NIGHT_PACKET_SCHEMA_VERSION


def validate_memory_record(record: MemoryRecord) -> None:
    _require_text("MemoryRecord.record_id", record.record_id)
    _require_text("MemoryRecord.record_type", record.record_type)
    _require_text("MemoryRecord.text", record.text)
    _require_text("MemoryRecord.created_at", record.created_at)
    _require_member("MemoryRecord.record_type", record.record_type, MEMORY_RECORD_TYPES)
    _require_member("MemoryRecord.memory_role", record.memory_role, MEMORY_ROLES)
    _require_member("MemoryRecord.confidence_label", record.confidence_label, CONFIDENCE_LABELS)
    _require_member(
        "MemoryRecord.human_review_status",
        record.human_review_status,
        HUMAN_REVIEW_STATUSES,
    )
    if record.schema_name != MEMORY_RECORD_SCHEMA_NAME:
        raise ValueError(f"unknown memory record schema_name: {record.schema_name}")
    if record.schema_version != MEMORY_RECORD_SCHEMA_VERSION:
        raise ValueError(f"unknown memory record schema_version: {record.schema_version}")
    _validate_string_list("MemoryRecord.tags", record.tags)
    _validate_string_list("MemoryRecord.source_refs", record.source_refs)
    _validate_string_list("MemoryRecord.derived_from_record_ids", record.derived_from_record_ids)
    _validate_json_serializable("MemoryRecord.metadata", record.metadata)


def validate_memory_activation_item(item: MemoryActivationItem) -> None:
    _require_text("MemoryActivationItem.item_id", item.item_id)
    _require_text("MemoryActivationItem.source_record_id", item.source_record_id)
    _require_text("MemoryActivationItem.text", item.text)
    _require_member("MemoryActivationItem.memory_role", item.memory_role, MEMORY_ROLES)
    _require_member("MemoryActivationItem.use_as", item.use_as, MEMORY_USE_MODES)
    _require_text("MemoryActivationItem.activation_reason", item.activation_reason)
    _require_member(
        "MemoryActivationItem.confidence_label",
        item.confidence_label,
        CONFIDENCE_LABELS,
    )
    _require_member(
        "MemoryActivationItem.human_review_status",
        item.human_review_status,
        HUMAN_REVIEW_STATUSES,
    )
    if item.schema_name != MEMORY_ACTIVATION_ITEM_SCHEMA_NAME:
        raise ValueError(f"unknown activation item schema_name: {item.schema_name}")
    if item.schema_version != MEMORY_ACTIVATION_ITEM_SCHEMA_VERSION:
        raise ValueError(f"unknown activation item schema_version: {item.schema_version}")
    _validate_string_list("MemoryActivationItem.tags", item.tags)
    _validate_string_list("MemoryActivationItem.source_refs", item.source_refs)


def validate_night_government_packet(packet: NightGovernmentPacket) -> None:
    _require_text("NightGovernmentPacket.packet_id", packet.packet_id)
    _require_text("NightGovernmentPacket.day_id", packet.day_id)
    _require_text("NightGovernmentPacket.created_at", packet.created_at)
    _require_text("NightGovernmentPacket.generated_by", packet.generated_by)
    _validate_string_list("NightGovernmentPacket.input_record_ids", packet.input_record_ids)
    if packet.schema_name != NIGHT_PACKET_SCHEMA_NAME:
        raise ValueError(f"unknown night packet schema_name: {packet.schema_name}")
    if packet.schema_version != NIGHT_PACKET_SCHEMA_VERSION:
        raise ValueError(f"unknown night packet schema_version: {packet.schema_version}")
    seen_item_ids: set[str] = set()
    for item in packet.active_memory_items:
        validate_memory_activation_item(item)
        if item.item_id in seen_item_ids:
            raise ValueError(f"duplicate active memory item id: {item.item_id}")
        seen_item_ids.add(item.item_id)
        if item.source_record_id not in packet.input_record_ids:
            raise ValueError("activation item source must be included in packet input ids")
    for role, count in packet.role_counts.items():
        _require_member("NightGovernmentPacket.role_counts key", role, MEMORY_ROLES)
        if count < 0:
            raise ValueError("role_counts values must not be negative")
    _validate_string_list("NightGovernmentPacket.current_limits", packet.current_limits)


def _require_text(field_name: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must not be empty")


def _require_member(field_name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        raise ValueError(f"unknown {field_name}: {value}")


def _validate_string_list(field_name: str, value: list[str]) -> None:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{field_name} must contain only non-empty strings")


def _validate_json_serializable(field_name: str, value: object) -> None:
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be JSON serializable") from exc
