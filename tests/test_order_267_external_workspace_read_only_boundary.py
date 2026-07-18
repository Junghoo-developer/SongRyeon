from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from songryeon_core.core.workspace_manifest import build_workspace_manifest
from songryeon_core.runtime.local_launcher import build_default_chat_cli_args
from songryeon_core.runtime.terminal_view import render_runtime_view
from songryeon_core.runtime.user_turn import run_fake_user_turn, run_qwen_user_turn
from songryeon_core.tools.code_tools import list_code_files, read_code_file
from songryeon_core.tools.document_tools import list_docs, read_doc
from songryeon_core.tools.workspace_policy import (
    workspace_file_rejection_reason,
    workspace_qwen_endpoint_is_local,
)


def _make_workspace(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "src").mkdir()
    (root / ".venv").mkdir()
    (root / "build").mkdir()
    (root / "tmp" / "ci-venv").mkdir(parents=True)
    (root / "docs" / "brief.md").write_text(
        "# 업무 브리프\n고객 요청은 안전한 읽기 전용 조사다.\n",
        encoding="utf-8",
    )
    (root / "notes.txt").write_text(
        "회의 메모: 실제 읽은 파일과 후보 파일을 구분한다.\n",
        encoding="utf-8",
    )
    (root / "src" / "app.py").write_text(
        "def answer():\n    return 'workspace evidence'\n",
        encoding="utf-8",
    )
    (root / ".env").write_text("SECRET=do-not-read\n", encoding="utf-8")
    (root / "credentials.json").write_text('{"token":"do-not-read"}', encoding="utf-8")
    (root / "private.pem").write_text("PRIVATE MATERIAL", encoding="utf-8")
    (root / ".venv" / "hidden.py").write_text("SECRET = True\n", encoding="utf-8")
    (root / "build" / "generated.py").write_text("GENERATED = True\n", encoding="utf-8")
    (root / "tmp" / "ci-venv" / "pyvenv.cfg").write_text(
        "home = C:/Python\n",
        encoding="utf-8",
    )
    (root / "tmp" / "ci-venv" / "hidden.py").write_text(
        "SECRET = True\n",
        encoding="utf-8",
    )
    (root / "image.png").write_bytes(b"not-a-supported-text-file")


def test_workspace_manifest_records_supported_files_and_explicit_exclusions(
    tmp_path: Path,
) -> None:
    _make_workspace(tmp_path)

    frame = build_workspace_manifest(
        root_path=tmp_path,
        turn_id="turn_workspace_manifest_test",
        observed_at="2026-07-18T00:00:00+00:00",
    )

    assert frame.manifest_status == "ready"
    assert frame.access_mode == "read_only"
    assert frame.local_model_only is True
    assert frame.automatic_graph_ingest_status == "not_run"
    assert frame.candidate_file_count == 3
    assert [item.relative_path for item in frame.files] == [
        "docs/brief.md",
        "notes.txt",
        "src/app.py",
    ]
    assert frame.source_kind_counts == {
        "workspace_code_or_config": 1,
        "workspace_document": 2,
    }
    assert all(len(item.content_hash) == 64 for item in frame.files)
    assert frame.excluded_directory_count == 3
    assert frame.exclusion_reason_counts["secret_filename_policy"] == 2
    assert frame.exclusion_reason_counts["secret_suffix_policy"] == 1
    assert frame.exclusion_reason_counts["unsupported_extension"] == 1


def test_workspace_document_and_code_tools_share_the_read_only_policy(
    tmp_path: Path,
) -> None:
    _make_workspace(tmp_path)

    document_ids = [item["doc_id"] for item in list_docs(root=tmp_path)]
    code_paths = [item["file_path"] for item in list_code_files(root=tmp_path)["files"]]

    assert document_ids == ["docs/brief.md", "notes.txt"]
    assert code_paths == ["src/app.py"]
    assert "회의 메모" in read_doc(root=tmp_path, doc_id="notes.txt")["text"]
    assert read_code_file(root=tmp_path, file_path="credentials.json")["read_status"] == (
        "secret_filename_policy"
    )
    assert read_code_file(
        root=tmp_path,
        file_path="tmp/ci-venv/hidden.py",
    )["read_status"] == "excluded_directory_policy"
    assert read_code_file(root=tmp_path, file_path="../outside.py")["read_status"] == (
        "path_outside_workspace_rejected"
    )


def test_workspace_symbolic_link_is_rejected_when_platform_allows_it(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}_outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        os.symlink(outside, link)
    except OSError:
        pytest.skip("symbolic link creation is unavailable on this Windows host")

    assert workspace_file_rejection_reason(root=tmp_path, path=link) == (
        "symbolic_link_rejected"
    )
    assert "linked.txt" not in [item["doc_id"] for item in list_docs(root=tmp_path)]


def test_workspace_qwen_rejects_remote_compatible_endpoint_before_llm_call(
    tmp_path: Path,
) -> None:
    _make_workspace(tmp_path)

    assert workspace_qwen_endpoint_is_local(None) is True
    assert workspace_qwen_endpoint_is_local("http://localhost:11434/v1/chat/completions") is True
    assert workspace_qwen_endpoint_is_local("http://127.0.0.1:11434/v1/chat/completions") is True
    assert workspace_qwen_endpoint_is_local("http://[::1]:11434/v1/chat/completions") is True
    assert workspace_qwen_endpoint_is_local("https://example.com/v1/chat/completions") is False

    result = run_qwen_user_turn(
        user_input="업무 폴더를 읽어줘",
        endpoint="https://example.com/v1/chat/completions",
        workspace_root=tmp_path,
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "workspace_requires_local_qwen_endpoint"
    assert result["workspace_policy_status"] == "blocked_remote_qwen_endpoint"


def test_fake_l_turn_reads_workspace_documents_and_preserves_manifest(
    tmp_path: Path,
) -> None:
    _make_workspace(tmp_path)

    result = run_fake_user_turn(
        user_input="업무 문서를 검색하고 실제 원문을 읽어서 정리해줘",
        workspace_root=tmp_path,
        include_data_records=True,
    )

    assert result["status"] == "ok"
    assert result["workspace_active"] is True
    assert result["workspace_candidate_file_count"] == 3
    assert result["workspace_automatic_graph_ingest_status"] == "not_run"
    records = result["data_records"]
    assert isinstance(records, list)
    manifests = [
        item
        for item in records
        if item.get("data_type") == "node_output:workspace_manifest_frame"
    ]
    assert len(manifests) == 1
    node1_calls = [
        item
        for item in records
        if item.get("data_type") == "llm_call"
        and isinstance(item.get("payload"), dict)
        and item["payload"].get("node_id") == "node_1"
    ]
    initial_node1_calls = [
        item
        for item in node1_calls
        if '"user_input":"업무 문서를 검색하고 실제 원문을 읽어서 정리해줘"'
        in item["payload"]["input_payload_preview_json"]
    ]
    assert len(initial_node1_calls) == 1
    node1_preview = initial_node1_calls[0]["payload"]["input_payload_preview_json"]
    node1_input = json.loads(node1_preview)
    workspace_context = node1_input["active_workspace_context"]
    assert workspace_context["workspace_status"] == "active"
    assert workspace_context["candidate_file_count"] == 3
    assert "root_path" not in workspace_context
    assert str(tmp_path) not in node1_preview
    read_records = [
        item
        for item in records
        if str(item.get("data_type") or "").startswith("tool_result:read_doc")
    ]
    assert read_records
    read_doc_ids = {
        str(item.get("payload", {}).get("doc_id") or "")
        for item in read_records
        if isinstance(item.get("payload"), dict)
    }
    assert read_doc_ids <= {"docs/brief.md", "notes.txt"}
    runtime_text = render_runtime_view(
        result,
        user_input="업무 문서를 검색하고 실제 원문을 읽어서 정리해줘",
    )
    assert "active workspace [CODE/READ_ONLY]" in runtime_text
    assert "graph_ingest=not_run" in runtime_text


def test_default_local_launcher_can_use_workspace_env_without_external_api(
    tmp_path: Path,
) -> None:
    args = build_default_chat_cli_args(
        environ={
            "SONGRYEON_DEFAULT_ENABLE_VESSEL_R": "false",
            "SONGRYEON_DEFAULT_LIVE_TRACE": "false",
            "SONGRYEON_WORKSPACE_ROOT": str(tmp_path),
        }
    )

    assert args[:3] == ["qwen-chat", "--timeout", "180"]
    workspace_index = args.index("--workspace")
    assert args[workspace_index + 1] == str(tmp_path)


def test_workspace_check_cli_reports_code_owned_boundary(tmp_path: Path) -> None:
    _make_workspace(tmp_path)
    repo_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "main.py", "workspace-check", str(tmp_path)],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "WORKSPACE_CHECK_OK"
    assert payload["candidate_file_count"] == 3
    assert payload["automatic_graph_ingest_status"] == "not_run"
    assert payload["generated_by"] == "CODE:WORKSPACE_MANIFEST_BUILDER"
    assert payload["semantic_judgement_status"] == "not_run"
    assert ".env" not in payload["candidate_relative_paths"]


def test_external_api_cli_does_not_accept_workspace_option(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "openai-turn",
            "test",
            "--workspace",
            str(tmp_path),
        ],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert "unrecognized arguments: --workspace" in completed.stderr
