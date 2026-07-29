"""원본 기억에서 에이전트가 볼 JSONL 구간을 만든다.

``memory.jsonl`` 자체는 원본이다. 이 파일의 반환값만 에이전트 시야다.
턴 시작 전에는 최신 글자 예산을 적용하고, 턴 중에는 그때 선택된 가장
오래된 원자를 기준점으로 고정한다. 따라서 같은 턴의 뒤쪽 노드가 앞쪽
노드가 본 원자를 잃지 않는다.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from .settings import (
    AGENT_VIEW_FIELDS,
    AGENT_VISIBLE_FIELDS,
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
    HIDDEN_INFORMATION_TYPE_PREFIXES,
)


class AgentMemoryFloorError(RuntimeError):
    """고정한 에이전트 시야 기준점을 원본 로그에서 복원할 수 없다."""


class TurnMemoryContextError(RuntimeError):
    """현재 턴의 시작 원자를 원본 로그에서 정확히 찾을 수 없다."""


@dataclass(frozen=True)
class AgentMemoryFloor:
    """한 턴 동안 움직이지 않을 가장 오래된 공개 원자의 내부 ID."""

    anchor_information_id: str | None

    def __post_init__(self):
        anchor = self.anchor_information_id

        if anchor is not None and (
            not isinstance(anchor, str) or not anchor.strip()
        ):
            raise ValueError(
                "anchor_information_id는 비어 있지 않은 문자열 또는 None이어야 합니다."
            )


@dataclass(frozen=True)
class TurnMemoryContext:
    """모든 노드가 한 턴 동안 공유할 순서 경계와 직전 사용자 입력."""

    current_turn_start_index: int
    previous_user_input_index: int | None = None
    previous_user_input: str | None = None

    def __post_init__(self):
        start_index = self.current_turn_start_index

        if (
            not isinstance(start_index, int)
            or isinstance(start_index, bool)
            or start_index < 1
        ):
            raise ValueError(
                "current_turn_start_index는 1 이상의 정수여야 합니다."
            )

        previous_index = self.previous_user_input_index
        previous_input = self.previous_user_input

        if (previous_index is None) != (previous_input is None):
            raise ValueError(
                "직전 사용자 입력의 순번과 내용은 함께 있거나 함께 없어야 합니다."
            )

        if previous_index is not None and (
            not isinstance(previous_index, int)
            or isinstance(previous_index, bool)
            or previous_index < 1
            or previous_index >= start_index
        ):
            raise ValueError(
                "previous_user_input_index는 현재 턴 시작보다 작은 양의 정수여야 합니다."
            )

        if previous_input is not None and (
            not isinstance(previous_input, str)
            or not previous_input.strip()
        ):
            raise ValueError(
                "previous_user_input은 비어 있지 않은 문자열이어야 합니다."
            )


def format_agent_memory(agent_memory):
    """에이전트 시야 기록들을 실제 전달용 JSONL 문자열로 바꾼다."""

    return "\n".join(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for record in agent_memory
    )


def _is_hidden_record(record):
    """원본에는 남지만 평상시 시야에서 숨길 기록인지 확인한다."""

    information_type = record["information_type"]
    return information_type.startswith(HIDDEN_INFORMATION_TYPE_PREFIXES)


def _load_indexed_raw_records(path):
    """원본 JSONL의 물리 줄 번호와 7필드 원자를 순서대로 읽는다."""

    indexed_records = []

    with path.open("r", encoding="utf-8") as file:
        for memory_index, line in enumerate(file, start=1):
            if not line.strip():
                continue

            indexed_records.append(
                (memory_index, json.loads(line))
            )

    return indexed_records


def _load_visible_records(path, turn_id):
    """공개 원자의 내부 ID와 다섯 필드 시야를 원본 순서로 읽는다."""

    visible_records = []

    for memory_index, raw_record in _load_indexed_raw_records(path):
        if _is_hidden_record(raw_record):
            continue

        if turn_id is not None and raw_record["turn_id"] != turn_id:
            continue

        visible_record = {
            "memory_index": memory_index,
            **{
                field: raw_record[field]
                for field in AGENT_VISIBLE_FIELDS
            },
        }
        if tuple(visible_record) != AGENT_VIEW_FIELDS:
            raise RuntimeError("에이전트 시야 필드 순서가 설정과 다릅니다.")

        visible_records.append(
            (
                raw_record["information_id"],
                visible_record,
            )
        )

    return visible_records


def load_turn_memory_context(
    start_information_id,
    file_path=DEFAULT_MEMORY_PATH,
):
    """현재 턴 시작 순번과 그보다 앞선 마지막 사용자 입력을 찾는다.

    ``start_information_id``에는 ``save_user_input``이 저장한 첫
    ``source:user`` 원자의 내부 UUID를 사용한다. 원본 UUID는 안정적인
    조회 기준이고, 에이전트에게는 찾은 물리 줄 번호만 공개한다.
    """

    if (
        not isinstance(start_information_id, str)
        or not start_information_id.strip()
    ):
        raise ValueError(
            "start_information_id는 비어 있지 않은 문자열이어야 합니다."
        )

    path = Path(file_path)

    if not path.exists():
        raise TurnMemoryContextError(
            "현재 턴 시작점을 찾을 원본 기억 로그가 없습니다."
        )

    indexed_records = _load_indexed_raw_records(path)
    matching_positions = [
        position
        for position, (_, record) in enumerate(indexed_records)
        if record.get("information_id") == start_information_id
    ]

    if len(matching_positions) != 1:
        problem = (
            "찾을 수 없습니다"
            if not matching_positions
            else "중복됐습니다"
        )
        raise TurnMemoryContextError(
            "현재 턴 시작 원자가 원본 로그에서 "
            + problem
            + "."
        )

    start_position = matching_positions[0]
    current_turn_start_index, start_record = indexed_records[
        start_position
    ]

    if (
        start_record.get("information") != "user"
        or start_record.get("information_type") != "source"
        or start_record.get("information_class") != "absolute"
        or start_record.get("code_verifiable") is not True
    ):
        raise TurnMemoryContextError(
            "현재 턴 시작 원자는 사용자 출처 A여야 합니다."
        )

    previous_user_input_index = None
    previous_user_input = None

    for memory_index, record in indexed_records[:start_position]:
        if record.get("information_type") != "user_input":
            continue

        information = record.get("information")

        if (
            not isinstance(information, str)
            or not information.strip()
            or record.get("information_class") != "relative"
            or record.get("code_verifiable") is not False
        ):
            raise TurnMemoryContextError(
                "직전 사용자 입력 원자의 형식이 올바르지 않습니다."
            )

        previous_user_input_index = memory_index
        previous_user_input = information

    return TurnMemoryContext(
        current_turn_start_index=current_turn_start_index,
        previous_user_input_index=previous_user_input_index,
        previous_user_input=previous_user_input,
    )


def _select_latest_records(visible_records, max_characters):
    """최신 원자부터 완전한 기록 단위로 글자 예산을 채운다."""

    selected_records = []
    used_characters = 0

    # 원본은 오래된 순서로 저장되므로 뒤에서부터 최신 기록을 고른다.
    for visible_record in reversed(visible_records):
        record_characters = len(format_agent_memory([visible_record]))
        separator_characters = 1 if selected_records else 0
        required_characters = record_characters + separator_characters

        if required_characters > max_characters and not selected_records:
            raise ValueError(
                "원자 기록 하나가 에이전트 기억의 글자 수 제한보다 큽니다."
            )

        if used_characters + required_characters > max_characters:
            break

        selected_records.append(visible_record)
        used_characters += required_characters

    # LLM은 선택된 범위 안에서는 다시 시간 순서대로 읽는다.
    selected_records.reverse()
    return selected_records


def load_agent_memory(
    file_path=DEFAULT_MEMORY_PATH,
    turn_id=None,
    max_characters=DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
):
    """원본 로그에서 최신 글자 예산에 맞는 에이전트 시야를 반환한다."""

    if max_characters <= 0:
        raise ValueError("max_characters는 1 이상이어야 합니다.")

    path = Path(file_path)

    if not path.exists():
        return []

    visible_records = [
        record
        for _, record in _load_visible_records(path, turn_id)
    ]
    return _select_latest_records(visible_records, max_characters)


def freeze_agent_memory_floor(
    file_path=DEFAULT_MEMORY_PATH,
    max_characters=DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
):
    """현재 최신 시야에서 가장 오래된 공개 원자를 턴 기준점으로 고정한다."""

    if max_characters <= 0:
        raise ValueError("max_characters는 1 이상이어야 합니다.")

    path = Path(file_path)

    if not path.exists():
        return AgentMemoryFloor(anchor_information_id=None)

    indexed_records = _load_visible_records(path, turn_id=None)
    visible_records = [record for _, record in indexed_records]
    selected_records = _select_latest_records(
        visible_records,
        max_characters,
    )

    if not selected_records:
        return AgentMemoryFloor(anchor_information_id=None)

    oldest_selected_index = len(visible_records) - len(selected_records)
    anchor_information_id = indexed_records[
        oldest_selected_index
    ][0]
    return AgentMemoryFloor(
        anchor_information_id=anchor_information_id,
    )


def load_frozen_agent_memory(
    floor,
    file_path=DEFAULT_MEMORY_PATH,
):
    """고정 기준점부터 현재 끝까지의 모든 공개 원자를 반환한다.

    최초 8,000자 제한은 ``freeze_agent_memory_floor``에서만 적용한다.
    턴이 진행된 뒤에는 기준점을 앞으로 옮기거나 공개 원자를 잘라내지 않는다.
    """

    if not isinstance(floor, AgentMemoryFloor):
        raise TypeError("floor는 AgentMemoryFloor여야 합니다.")

    path = Path(file_path)
    anchor_information_id = floor.anchor_information_id

    if not path.exists():
        if anchor_information_id is None:
            return []
        raise AgentMemoryFloorError(
            "고정한 에이전트 시야의 원본 기억 로그가 사라졌습니다."
        )

    indexed_records = _load_visible_records(path, turn_id=None)

    # 공개 원자가 하나도 없던 시점에 고정했다면 이후 생긴 공개 원자 전부가
    # 이번 기준점 뒤의 기록이다.
    if anchor_information_id is None:
        return [record for _, record in indexed_records]

    matching_indices = [
        index
        for index, (information_id, _) in enumerate(indexed_records)
        if information_id == anchor_information_id
    ]

    if len(matching_indices) != 1:
        problem = (
            "찾을 수 없습니다"
            if not matching_indices
            else "중복됐습니다"
        )
        raise AgentMemoryFloorError(
            "고정한 에이전트 시야 기준점이 원본 로그에서 "
            + problem
            + "."
        )

    anchor_index = matching_indices[0]
    return [
        record
        for _, record in indexed_records[anchor_index:]
    ]
