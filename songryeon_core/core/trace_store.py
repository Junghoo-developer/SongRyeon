from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from songryeon_core.core.schemas import TraceEvent


# 현재 설계에서 공식 후보로 인정한 trace 사건 종류들.
# 이 목록은 "참고용 사전"이고, 새 event_type을 추가하는 일은 나중에 발주서로 다룬다.
KNOWN_EVENT_TYPES = {
    "user_input",
    "node_input",
    "node_output",
    "routing",
    "tool_call",
    "tool_result",
    "schema_check",
    "memory_packet",
    "failure_signal",
    "turn_outcome",
}


# 스키마 검사 상태는 trace의 절대정보에 가깝기 때문에 지금 단계에서 좁게 관리한다.
KNOWN_SCHEMA_STATUSES = {
    "passed",
    "failed",
    "not_checked",
}


class TraceStore:
    """TraceEvent를 메모리에 쌓고 JSON으로 저장/복원하는 최소 저장소."""

    def __init__(self, events: Iterable[TraceEvent] | None = None) -> None:
        # 실행 순서를 보존하기 위해 list를 원본 저장소로 둔다.
        self._events: list[TraceEvent] = []
        # event_id로 빠르게 찾고, 중복 ID를 막기 위해 index를 별도로 둔다.
        self._event_index: dict[str, TraceEvent] = {}

        # 이미 만들어진 TraceEvent 목록을 받아 초기화할 수 있게 한다.
        for event in events or []:
            self.add_event(event)

    def add_event(self, event: TraceEvent) -> TraceEvent:
        """이미 만들어진 TraceEvent를 저장소에 추가한다."""

        # event_id는 trace 조각의 신분증이므로 중복되면 전체 추적이 흔들린다.
        if event.event_id in self._event_index:
            raise ValueError(f"duplicate trace event_id: {event.event_id}")

        self._validate_event(event)
        self._events.append(event)
        self._event_index[event.event_id] = event
        return event

    def create_event(
        self,
        *,
        turn_id: str,
        actor: str,
        event_type: str,
        event_id: str | None = None,
        timestamp: str | None = None,
        input_ref: list[str] | None = None,
        output_ref: list[str] | None = None,
        raw_content_ref: str | None = None,
        schema_status: str = "not_checked",
    ) -> TraceEvent:
        """필수 정보만 받아 TraceEvent를 만들고 바로 저장한다."""

        # event_id를 넘기지 않으면 현재 저장소 길이를 기준으로 단순한 ID를 만든다.
        # 나중에 여러 프로세스가 동시에 쓰게 되면 더 강한 ID 생성기가 필요하다.
        generated_event_id = event_id or self.next_event_id()

        # timestamp를 넘기지 않으면 현재 시간을 초 단위 문자열로 기록한다.
        event_time = timestamp or datetime.now().isoformat(timespec="seconds")

        event = TraceEvent(
            event_id=generated_event_id,
            turn_id=turn_id,
            timestamp=event_time,
            actor=actor,
            event_type=event_type,
            input_ref=input_ref or [],
            output_ref=output_ref or [],
            raw_content_ref=raw_content_ref,
            schema_status=schema_status,
        )
        return self.add_event(event)

    def next_event_id(self, prefix: str = "trace") -> str:
        """현재 저장소 기준으로 다음 trace ID 후보를 만든다."""

        # 사람이 읽기 편하게 6자리 숫자를 붙인다. 예: trace_000001.
        return f"{prefix}_{len(self._events) + 1:06d}"

    def list_events(self) -> list[TraceEvent]:
        """저장된 모든 trace를 실행 순서대로 돌려준다."""

        # 내부 list를 그대로 넘기면 밖에서 실수로 조작할 수 있으니 복사본을 준다.
        return list(self._events)

    def get_event(self, event_id: str) -> TraceEvent | None:
        """event_id로 trace 하나를 찾는다."""

        return self._event_index.get(event_id)

    def events_for_turn(self, turn_id: str) -> list[TraceEvent]:
        """특정 턴에서 생긴 trace만 실행 순서대로 모아 돌려준다."""

        return [event for event in self._events if event.turn_id == turn_id]

    def to_records(self) -> list[dict[str, object]]:
        """TraceEvent 목록을 JSON으로 저장 가능한 dict 목록으로 바꾼다."""

        # TraceEvent는 dataclass라서 asdict로 안전하게 기본 자료형으로 바꿀 수 있다.
        return [asdict(event) for event in self._events]

    @classmethod
    def from_records(cls, records: Iterable[dict[str, object]]) -> TraceStore:
        """dict 목록에서 TraceStore를 복원한다."""

        events = [TraceEvent(**record) for record in records]
        return cls(events)

    def save_json(self, path: str | Path) -> Path:
        """현재 trace 목록을 JSON 파일로 저장한다."""

        target = Path(path)
        # 저장할 폴더가 없으면 만든다. trace 파일 저장은 이 함수의 책임으로 둔다.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_records(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> TraceStore:
        """JSON 파일에서 TraceStore를 복원한다."""

        source = Path(path)
        records = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("trace json root must be a list")
        return cls.from_records(records)

    def _validate_event(self, event: TraceEvent) -> None:
        """TraceEvent가 최소한의 절대정보 규칙을 지키는지 확인한다."""

        # 아래 필드들은 trace의 기본 뼈대라 비어 있으면 안 된다.
        required_text_fields = {
            "event_id": event.event_id,
            "turn_id": event.turn_id,
            "timestamp": event.timestamp,
            "actor": event.actor,
            "event_type": event.event_type,
        }
        for field_name, value in required_text_fields.items():
            if not value:
                raise ValueError(f"TraceEvent.{field_name} must not be empty")

        # event_type은 후보 목록 밖이어도 일단 허용한다.
        # 이유: 아직 노드 설계가 끝나지 않았고, 새로운 event_type이 생길 수 있다.
        # 단, 비어 있는 값은 위에서 막는다.

        # schema_status는 현재 확정 가능한 절대정보이므로 좁게 검증한다.
        if event.schema_status not in KNOWN_SCHEMA_STATUSES:
            raise ValueError(f"unknown schema_status: {event.schema_status}")
