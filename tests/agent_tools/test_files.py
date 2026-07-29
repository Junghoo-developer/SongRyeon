"""Node1 파일 도구가 읽기 전용 경계 안에서만 동작하는지 검사한다."""

from pathlib import Path

import pytest

from agent_tools import (
    LIST_PYTHON_FILES,
    MAX_TOOL_ARGUMENT_CHARACTERS,
    MAX_TOOL_NAME_CHARACTERS,
    READ_PYTHON_FILE,
    FileToolbox,
)


def test_python_file_list_is_sorted_and_excludes_private_directories(
    tmp_path,
):
    project = tmp_path / "project"
    (project / "package").mkdir(parents=True)
    (project / "__pycache__").mkdir()
    (project / ".tmp").mkdir()
    (project / "build" / "lib").mkdir(parents=True)
    (project / "knowledge" / "documents").mkdir(parents=True)

    (project / "z.py").write_text("Z = 1\n", encoding="utf-8")
    (project / "package" / "a.py").write_text(
        "A = 1\n",
        encoding="utf-8",
    )
    (project / "__pycache__" / "hidden.py").write_text(
        "HIDDEN = True\n",
        encoding="utf-8",
    )
    (project / ".tmp" / "generated.py").write_text(
        "GENERATED = True\n",
        encoding="utf-8",
    )
    (project / "build" / "lib" / "copied.py").write_text(
        "COPIED = True\n",
        encoding="utf-8",
    )
    (project / "knowledge" / "documents" / "external.py").write_text(
        "EXTERNAL = True\n",
        encoding="utf-8",
    )
    (project / "notes.txt").write_text("메모", encoding="utf-8")

    toolbox = FileToolbox(project)
    result = toolbox.execute(LIST_PYTHON_FILES, {})

    assert result.success is True
    assert result.content.splitlines() == [
        "package/a.py",
        "z.py",
    ]
    assert str(project) not in result.content


def test_read_python_file_preserves_utf8_and_line_endings(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    raw_content = "print('안녕🙂')\r\nVALUE = 1\n".encode("utf-8")
    (project / "main.py").write_bytes(raw_content)
    toolbox = FileToolbox(project)

    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "main.py"},
    )

    assert result.success is True
    assert result.content == raw_content.decode("utf-8")
    assert result.error is None


@pytest.mark.parametrize(
    "requested_path",
    [
        "../outside.py",
        "bad\x00.py",
        "carrier:secret.py",
        "missing.py",
        "notes.txt",
        "folder",
    ],
)
def test_read_rejects_paths_outside_the_python_file_contract(
    tmp_path,
    requested_path,
):
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "outside.py").write_text(
        "OUTSIDE = True\n",
        encoding="utf-8",
    )
    (project / "notes.txt").write_text("메모", encoding="utf-8")
    (project / "folder").mkdir()
    toolbox = FileToolbox(project)

    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": requested_path},
    )

    assert result.success is False
    assert result.content == ""
    assert result.error
    assert str(tmp_path) not in result.error


def test_read_rejects_an_absolute_path(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    source = project / "main.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    toolbox = FileToolbox(project)

    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": str(source.resolve())},
    )

    assert result.success is False
    assert "절대경로" in result.error


def test_read_rejects_an_oversized_file(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "large.py").write_bytes(b"X" * 11)
    toolbox = FileToolbox(project, max_file_bytes=10)

    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "large.py"},
    )

    assert result.success is False
    assert "최대 열람 크기" in result.error


def test_read_accepts_exact_limit_and_rejects_invalid_utf8(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "exact.py").write_bytes(b"X" * 10)
    (project / "invalid.py").write_bytes(b"\xff\xfe")
    toolbox = FileToolbox(project, max_file_bytes=10)

    exact = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "exact.py"},
    )
    invalid = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "invalid.py"},
    )

    assert exact.success is True
    assert exact.content == "X" * 10
    assert invalid.success is False
    assert "UTF-8" in invalid.error


def test_unknown_tool_and_invalid_arguments_return_failures(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    toolbox = FileToolbox(project)

    unknown = toolbox.execute("delete_file", {})
    invalid_list = toolbox.execute(
        LIST_PYTHON_FILES,
        {"unexpected": True},
    )
    invalid_read = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": 123},
    )
    oversized_name = toolbox.execute(
        "x" * (MAX_TOOL_NAME_CHARACTERS + 1),
        {},
    )
    oversized_arguments = toolbox.execute(
        READ_PYTHON_FILE,
        {
            "path": "x" * (MAX_TOOL_ARGUMENT_CHARACTERS + 1),
        },
    )

    assert unknown.success is False
    assert invalid_list.success is False
    assert invalid_read.success is False
    assert oversized_name.success is False
    assert oversized_name.tool_name == "<invalid_tool_name>"
    assert oversized_arguments.success is False
    assert len(str(oversized_arguments.arguments)) < 200


def test_malformed_nested_arguments_are_bounded_failures(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    toolbox = FileToolbox(project)
    deeply_nested = {}
    cursor = deeply_nested

    for _ in range(1_100):
        child = {}
        cursor["child"] = child
        cursor = child

    deep_result = toolbox.execute(
        READ_PYTHON_FILE,
        deeply_nested,
    )
    mixed_key_result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "main.py", 1: "extra"},
    )

    assert deep_result.success is False
    assert mixed_key_result.success is False
    assert all(
        isinstance(key, str)
        for key in mixed_key_result.arguments
    )


def test_operating_system_error_does_not_expose_the_host_path(
    tmp_path,
    monkeypatch,
):
    project = tmp_path / "project"
    project.mkdir()
    toolbox = FileToolbox(project)

    def fail_with_host_path(relative_path):
        raise PermissionError(project / relative_path)

    monkeypatch.setattr(
        toolbox,
        "read_python_file",
        fail_with_host_path,
    )
    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "private.py"},
    )

    assert result.success is False
    assert str(project) not in result.error
    assert result.error == "파일 도구가 요청을 처리하지 못했습니다."


def test_direct_read_rejects_the_external_documents_directory(tmp_path):
    project = tmp_path / "project"
    document = project / "knowledge" / "documents" / "external.py"
    document.parent.mkdir(parents=True)
    document.write_text("EXTERNAL = True\n", encoding="utf-8")
    toolbox = FileToolbox(project)

    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "knowledge/documents/external.py"},
    )

    assert result.success is False


def test_link_to_an_outside_file_is_not_readable(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("SECRET = True\n", encoding="utf-8")
    link = project / "linked.py"

    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("현재 Windows 설정에서 심볼릭 링크 생성 권한이 없습니다.")

    toolbox = FileToolbox(project)

    assert "linked.py" not in toolbox.list_python_files()
    result = toolbox.execute(
        READ_PYTHON_FILE,
        {"path": "linked.py"},
    )
    assert result.success is False
