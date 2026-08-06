"""기본 경로와 공통 시야 예산이 실행 위치에 흔들리지 않는지 검사한다."""

from memory.settings import (
    DEFAULT_AGENT_VIEW_CHARACTER_LIMIT,
    DEFAULT_MEMORY_PATH,
    PROJECT_ROOT,
)
from knowledge.settings import (
    DEFAULT_DB_PATH,
    DEFAULT_DOCUMENTS_DIRECTORY,
)


def test_default_data_paths_use_process_starting_project_root(
    tmp_path,
    monkeypatch,
):
    starting_root = PROJECT_ROOT
    original_path = DEFAULT_MEMORY_PATH

    monkeypatch.chdir(tmp_path)

    assert starting_root != tmp_path
    assert PROJECT_ROOT == starting_root
    assert DEFAULT_MEMORY_PATH == original_path
    assert DEFAULT_MEMORY_PATH == starting_root / "memory" / "memory.jsonl"
    assert DEFAULT_DB_PATH == starting_root / "knowledge" / "knowledge.db"
    assert DEFAULT_DOCUMENTS_DIRECTORY == (
        starting_root / "knowledge" / "documents"
    )


def test_all_nodes_share_an_8000_character_view_budget():
    assert DEFAULT_AGENT_VIEW_CHARACTER_LIMIT == 8_000
