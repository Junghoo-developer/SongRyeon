"""기본 경로와 공통 시야 예산이 실행 위치에 흔들리지 않는지 검사한다."""

from memory.settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
)


def test_default_memory_path_does_not_follow_working_directory(
    tmp_path,
    monkeypatch,
):
    original_path = DEFAULT_MEMORY_PATH

    monkeypatch.chdir(tmp_path)

    assert DEFAULT_MEMORY_PATH == original_path
    assert DEFAULT_MEMORY_PATH.name == "memory.jsonl"
    assert DEFAULT_MEMORY_PATH.parent.name == "memory"


def test_all_nodes_share_an_8000_character_view_budget():
    assert DEFAULT_AGENT_VIEW_CHARACTER_LIMIT == 8_000
