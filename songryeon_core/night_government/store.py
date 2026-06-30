from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from songryeon_core.night_government.schemas import (
    MemoryRecord,
    NightGovernmentPacket,
    validate_memory_record,
    validate_night_government_packet,
)


class NightGovernmentStore:
    """Small file-backed external memory DB.

    The format is intentionally boring JSONL/JSON so the MVP can run overnight
    without a server. Later adapters can map the same records to SQLite or Neo4j.
    """

    def __init__(self, db_dir: str | Path) -> None:
        self.db_dir = Path(db_dir)
        self.records_path = self.db_dir / "memory_records.jsonl"
        self.packets_path = self.db_dir / "night_packets.jsonl"
        self.active_packet_path = self.db_dir / "active_memory_packet.json"

    def append_record(self, record: MemoryRecord) -> MemoryRecord:
        validate_memory_record(record)
        existing_ids = {item.record_id for item in self.list_records()}
        if record.record_id in existing_ids:
            raise ValueError(f"duplicate memory record id: {record.record_id}")
        self._append_jsonl(self.records_path, asdict(record))
        return record

    def list_records(self) -> list[MemoryRecord]:
        return [MemoryRecord(**item) for item in self._read_jsonl(self.records_path)]

    def append_packet(self, packet: NightGovernmentPacket) -> NightGovernmentPacket:
        validate_night_government_packet(packet)
        self._append_jsonl(self.packets_path, asdict(packet))
        return packet

    def list_packets(self) -> list[NightGovernmentPacket]:
        return [self._packet_from_dict(item) for item in self._read_jsonl(self.packets_path)]

    def save_active_packet(self, packet: NightGovernmentPacket) -> Path:
        validate_night_government_packet(packet)
        self.active_packet_path.parent.mkdir(parents=True, exist_ok=True)
        self.active_packet_path.write_text(
            json.dumps(asdict(packet), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.active_packet_path

    def load_active_packet(self) -> NightGovernmentPacket | None:
        if not self.active_packet_path.exists():
            return None
        payload = json.loads(self.active_packet_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("active packet json root must be an object")
        return self._packet_from_dict(payload)

    def _append_jsonl(self, path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, object]]:
        if not path.exists():
            return []
        rows: list[dict[str, object]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"{path} line {line_number} must be a JSON object")
            rows.append(payload)
        return rows

    def _packet_from_dict(self, payload: dict[str, object]) -> NightGovernmentPacket:
        from songryeon_core.night_government.schemas import MemoryActivationItem

        items_payload = payload.get("active_memory_items")
        if not isinstance(items_payload, list):
            raise ValueError("night packet active_memory_items must be a list")
        payload = dict(payload)
        payload["active_memory_items"] = [
            item if isinstance(item, MemoryActivationItem) else MemoryActivationItem(**item)
            for item in items_payload
            if isinstance(item, dict) or isinstance(item, MemoryActivationItem)
        ]
        packet = NightGovernmentPacket(**payload)
        validate_night_government_packet(packet)
        return packet


def load_memory_records(db_dir: str | Path) -> list[MemoryRecord]:
    return NightGovernmentStore(db_dir).list_records()


def append_memory_records(db_dir: str | Path, records: Iterable[MemoryRecord]) -> list[MemoryRecord]:
    store = NightGovernmentStore(db_dir)
    return [store.append_record(record) for record in records]
