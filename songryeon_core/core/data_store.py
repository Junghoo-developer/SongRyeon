from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class DataRecord:
    """trace가 가리키는 실제 데이터 본체 하나."""

    # TraceEvent.output_ref나 DataRef.data_id와 연결되는 고유 ID.
    data_id: str
    # 데이터 종류. 예: tool_result:search_docs, node_output:L3_preserved_frame.
    data_type: str
    # 실제 payload가 존재하는지.
    exists: bool
    # 이 데이터가 만들어진 시간. 보통 source trace의 timestamp를 그대로 쓴다.
    created_at: str | None
    # 이 데이터를 만들었다고 확인된 trace ID.
    source_trace_id: str | None
    # LLM이나 노드가 다시 읽어야 하는 실제 데이터 본체.
    payload: object


class DataStore:
    """DataRecord를 메모리에 쌓고 JSON으로 저장/복원하는 최소 저장소."""

    def __init__(self, records: Iterable[DataRecord] | None = None) -> None:
        # 실행 순서를 보존하기 위해 list를 원본 저장소로 둔다.
        self._records: list[DataRecord] = []
        # data_id 중복을 막고 빠르게 찾기 위해 index를 별도로 둔다.
        self._record_index: dict[str, DataRecord] = {}

        for record in records or []:
            self.add_record(record)

    def add_record(self, record: DataRecord) -> DataRecord:
        """이미 만들어진 DataRecord를 저장소에 추가한다."""

        if record.data_id in self._record_index:
            raise ValueError(f"duplicate data_id: {record.data_id}")
        self._validate_record(record)
        self._records.append(record)
        self._record_index[record.data_id] = record
        return record

    def create_record(
        self,
        *,
        data_id: str,
        data_type: str,
        payload: object,
        exists: bool = True,
        created_at: str | None = None,
        source_trace_id: str | None = None,
    ) -> DataRecord:
        """필수 정보와 payload를 받아 DataRecord를 만들고 바로 저장한다."""

        record = DataRecord(
            data_id=data_id,
            data_type=data_type,
            exists=exists,
            created_at=created_at,
            source_trace_id=source_trace_id,
            payload=payload,
        )
        return self.add_record(record)

    def get_record(self, data_id: str) -> DataRecord | None:
        """data_id로 데이터 본체 하나를 찾는다."""

        return self._record_index.get(data_id)

    def require_record(self, data_id: str) -> DataRecord:
        """data_id가 반드시 있어야 하는 상황에서 데이터 본체를 찾는다."""

        record = self.get_record(data_id)
        if record is None:
            raise KeyError(f"unknown data_id: {data_id}")
        return record

    def list_records(self) -> list[DataRecord]:
        """저장된 모든 데이터를 생성 순서대로 돌려준다."""

        return list(self._records)

    def to_records(self) -> list[dict[str, object]]:
        """DataRecord 목록을 JSON 저장 가능한 dict 목록으로 바꾼다."""

        return [asdict(record) for record in self._records]

    @classmethod
    def from_records(cls, records: Iterable[dict[str, object]]) -> DataStore:
        """dict 목록에서 DataStore를 복원한다."""

        data_records = [DataRecord(**record) for record in records]
        return cls(data_records)

    def save_json(self, path: str | Path) -> Path:
        """현재 데이터 목록을 JSON 파일로 저장한다."""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_records(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load_json(cls, path: str | Path) -> DataStore:
        """JSON 파일에서 DataStore를 복원한다."""

        source = Path(path)
        records = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("data json root must be a list")
        return cls.from_records(records)

    def _validate_record(self, record: DataRecord) -> None:
        """DataRecord가 최소 절대정보 규칙을 지키는지 확인한다."""

        if not record.data_id:
            raise ValueError("DataRecord.data_id must not be empty")
        if not record.data_type:
            raise ValueError("DataRecord.data_type must not be empty")

        # 지금 단계에서는 JSON 저장이 가능한 payload만 허용한다.
        try:
            json.dumps(record.payload, ensure_ascii=False)
        except TypeError as exc:
            raise TypeError(f"payload for {record.data_id} is not JSON serializable") from exc
