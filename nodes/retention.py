"""Node1의 보존 결정과 정확한 원문 선택.

짧은 원문은 기존 ``full/excerpt/omit`` 계약을 유지한다. 긴 원문은 코드가
결정론적으로 만든 청크의 ID를 Node1이 고르게 한다. 따라서 모델은 Python
문자 위치를 계산하지 않고, 코드는 선택된 청크의 정확한 범위를 다시 계산해
원문을 복사한다.
"""

from dataclasses import dataclass

from .common import validate_short_reason


DEFAULT_CHUNK_CHARACTERS = 2_000
RETENTION_MODES = {"full", "excerpt", "chunk", "omit"}


def _is_plain_integer(value):
    """bool을 문자 위치로 잘못 받지 않도록 순수 int만 허용한다."""

    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class TextChunk:
    """코드가 원문 순서와 줄 경계로 만든 결정론적 청크."""

    chunk_id: str
    start: int
    end: int
    content: str


def _require_positive_integer(value, field_name):
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name}는 1 이상의 정수여야 합니다.")


def build_text_chunks(
    raw_text,
    max_characters=DEFAULT_CHUNK_CHARACTERS,
):
    """원문을 가능한 한 줄 경계에서 최대 길이 이하로 나눈다.

    한 줄 자체가 상한보다 길면 그 줄만 문자 경계로 나눈다. 모든 청크를
    순서대로 이어 붙이면 원문과 byte 변환 전 문자열이 정확히 같아야 한다.
    """

    if not isinstance(raw_text, str):
        raise TypeError("도구 원문은 문자열이어야 합니다.")

    _require_positive_integer(max_characters, "max_characters")

    if not raw_text:
        return []

    chunks = []
    current_start = 0
    current_length = 0
    position = 0

    for line in raw_text.splitlines(keepends=True):
        line_start = position
        line_end = line_start + len(line)
        position = line_end

        if current_length and current_length + len(line) > max_characters:
            chunks.append((current_start, line_start))
            current_start = line_start
            current_length = 0

        remaining_start = line_start
        remaining_length = len(line)

        while remaining_length > max_characters:
            split_end = remaining_start + max_characters
            chunks.append((remaining_start, split_end))
            remaining_start = split_end
            remaining_length -= max_characters
            current_start = remaining_start

        if remaining_length:
            if current_length == 0:
                current_start = remaining_start
            current_length += remaining_length

    if current_length:
        chunks.append((current_start, len(raw_text)))

    result = [
        TextChunk(
            chunk_id=f"chunk-{index:04d}",
            start=start,
            end=end,
            content=raw_text[start:end],
        )
        for index, (start, end) in enumerate(chunks, start=1)
    ]

    if "".join(chunk.content for chunk in result) != raw_text:
        raise RuntimeError("결정론적 청크가 원문을 정확히 보존하지 못했습니다.")

    return result


def resolve_text_chunk(
    raw_text,
    chunk_id,
    max_characters=DEFAULT_CHUNK_CHARACTERS,
):
    """현재 원문에서 ID가 정확히 일치하는 청크 하나를 반환한다."""

    if not isinstance(chunk_id, str) or not chunk_id:
        raise ValueError("chunk 선택에는 chunk_id가 필요합니다.")

    matches = [
        chunk
        for chunk in build_text_chunks(raw_text, max_characters)
        if chunk.chunk_id == chunk_id
    ]

    if len(matches) != 1:
        raise ValueError("chunk_id가 현재 원문의 청크 목록에 없습니다.")

    return matches[0]


@dataclass(frozen=True)
class RetentionDecision:
    """Node1이 도구 원문을 얼마나 공개할지 정한 상대정보."""

    mode: str
    review: str
    start: int | None = None
    end: int | None = None
    chunk_id: str | None = None

    def __post_init__(self):
        if self.mode not in RETENTION_MODES:
            raise ValueError(f"알 수 없는 본문 보존 방식입니다: {self.mode}")

        validate_short_reason(self.review, "review")

        if self.mode == "excerpt":
            if not (
                _is_plain_integer(self.start)
                and _is_plain_integer(self.end)
            ):
                raise ValueError(
                    "excerpt에는 정수 start와 end가 필요합니다."
                )
            if self.chunk_id is not None:
                raise ValueError("excerpt에는 chunk_id를 지정할 수 없습니다.")
            return

        if self.mode == "chunk":
            if not isinstance(self.chunk_id, str) or not self.chunk_id:
                raise ValueError("chunk에는 chunk_id가 필요합니다.")
            if self.start is not None or self.end is not None:
                raise ValueError(
                    "chunk에는 start 또는 end를 지정할 수 없습니다."
                )
            return

        if (
            self.start is not None
            or self.end is not None
            or self.chunk_id is not None
        ):
            raise ValueError(
                "full과 omit에는 선택 위치를 지정할 수 없습니다."
            )


def select_retained_content(
    raw_text,
    decision,
    max_chunk_characters=DEFAULT_CHUNK_CHARACTERS,
):
    """Node1이 고른 위치를 검증하고 코드를 통해 원문을 정확히 복사한다."""

    if not isinstance(raw_text, str):
        raise TypeError("도구 원문은 문자열이어야 합니다.")

    if not isinstance(decision, RetentionDecision):
        raise TypeError("decision은 RetentionDecision이어야 합니다.")

    if decision.mode == "full":
        return raw_text

    if decision.mode == "omit":
        return None

    if decision.mode == "chunk":
        return resolve_text_chunk(
            raw_text,
            decision.chunk_id,
            max_chunk_characters,
        ).content

    if not 0 <= decision.start < decision.end <= len(raw_text):
        raise ValueError(
            "excerpt 범위는 0 <= start < end <= 원문 길이여야 합니다."
        )

    # strip, 정규화, 줄번호 추가 없이 원문의 해당 위치만 그대로 복사한다.
    return raw_text[decision.start:decision.end]
