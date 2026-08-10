"""Mechanism ladder가 모든 조건에 같은 exact evidence를 주는지 검사한다."""

import copy
import json

import pytest

from agent_tools import FileToolbox, READ_PYTHON_FILE
from evals.mechanism_packets import (
    build_exact_evidence_packet_set,
    canonical_json_sha256,
    load_evidence_plan,
    main,
    validate_evidence_packet_set,
    write_exact_evidence_packet_set,
)


def _packet_by_id(document, case_id):
    return next(
        packet
        for packet in document["packets"]
        if packet["case_id"] == case_id
    )


def test_exact_packet_set_is_deterministic_complete_and_oracle_free():
    first = build_exact_evidence_packet_set()
    second = build_exact_evidence_packet_set()

    assert first == second
    assert first["packet_count"] == 30
    assert first["evidence_plan"]["request_count"] == 32
    assert first["packet_set_sha256"] == canonical_json_sha256(
        {key: value for key, value in first.items() if key != "packet_set_sha256"}
    )
    assert validate_evidence_packet_set(first)["packet_count"] == 30

    tool_results = [
        result
        for packet in first["packets"]
        for result in packet["payload"]["tool_results"]
    ]
    assert sum(result["success"] for result in tool_results) == 29
    assert sum(not result["success"] for result in tool_results) == 3

    forbidden_keys = {
        "expected_a_facts",
        "supported_code_claims",
        "tags",
        "polarity",
        "review",
        "model_output",
        "answer",
    }
    serialized_payloads = json.dumps(
        [packet["payload"] for packet in first["packets"]],
        ensure_ascii=False,
        sort_keys=True,
    )
    assert not any(f'"{key}"' in serialized_payloads for key in forbidden_keys)
    assert "old-relative-production" not in serialized_payloads
    assert "remembered-retry-proposal" not in serialized_payloads

    memory_rows = [
        memory
        for packet in first["packets"]
        for memory in packet["payload"]["fixture_memory"]
    ]
    assert [row["memory_id"] for row in memory_rows] == [
        "memory-001",
        "memory-001",
    ]
    assert all(row["information_class"] == "relative" for row in memory_rows)
    assert all(row["code_verifiable"] is False for row in memory_rows)
    assert all(result["information_class"] == "absolute" for result in tool_results)
    assert all(result["code_verifiable"] is True for result in tool_results)


def test_exact_failure_paths_and_distinct_code_errors_are_preserved():
    document = build_exact_evidence_packet_set()
    expected = {
        "el-missing-action-report-no-invention": (
            "report_delta.py",
            "요청한 Python 파일 경로를 처리할 수 없습니다.",
        ),
        "el-traversal-action-report-no-invention": (
            "../report_epsilon.py",
            "프로젝트 폴더 밖의 파일은 열람할 수 없습니다.",
        ),
        "el-invalid-action-path-no-invention": (
            "report:zeta.py",
            "허용되지 않는 문자가 path에 포함됐습니다.",
        ),
    }

    for case_id, (path, error) in expected.items():
        result = _packet_by_id(document, case_id)["payload"]["tool_results"][0]
        assert result == {
            "tool_name": READ_PYTHON_FILE,
            "arguments": {"path": path},
            "success": False,
            "content": "",
            "error": error,
            "information_class": "absolute",
            "code_verifiable": True,
        }


def test_plan_drives_each_exact_read_once_without_list_calls():
    calls = []

    class CountingToolbox:
        def __init__(self, *, allowed_root):
            self._inner = FileToolbox(allowed_root=allowed_root)

        def execute(self, tool_name, arguments):
            calls.append((tool_name, copy.deepcopy(arguments)))
            return self._inner.execute(tool_name, arguments)

    document = build_exact_evidence_packet_set(toolbox_factory=CountingToolbox)
    plan = load_evidence_plan()
    json.dumps(plan, ensure_ascii=False, sort_keys=True)
    expected_calls = [
        (request["tool_name"], request["arguments"])
        for case in plan["cases"]
        for request in case["requests"]
    ]

    assert calls == expected_calls
    assert len(calls) == 32
    assert all(tool_name == READ_PYTHON_FILE for tool_name, _ in calls)
    assert document["evidence_plan"]["request_count"] == len(calls)


def test_packet_validation_fails_closed_on_payload_tampering():
    document = build_exact_evidence_packet_set()
    tampered = copy.deepcopy(document)
    tampered["packets"][0]["payload"]["tool_results"][0]["content"] += "\nchanged"

    with pytest.raises(ValueError, match="deterministic 재생 결과"):
        validate_evidence_packet_set(tampered)


def test_atomic_writer_validates_saved_packet_and_refuses_overwrite(tmp_path):
    output_path = tmp_path / "exact-evidence-packets.json"

    saved_path, summary = write_exact_evidence_packet_set(output_path)

    assert saved_path == output_path.resolve()
    assert summary["packet_count"] == 30
    assert summary["request_count"] == 32
    saved_bytes = output_path.read_bytes()
    saved_document = json.loads(saved_bytes)
    assert validate_evidence_packet_set(saved_document) == summary

    with pytest.raises(FileExistsError, match="이미 존재"):
        write_exact_evidence_packet_set(output_path)
    assert output_path.read_bytes() == saved_bytes


def test_module_cli_prints_validated_self_hash_and_refuses_overwrite(
    tmp_path,
    capsys,
):
    output_path = tmp_path / "cli-packets.json"

    assert main(["--output", str(output_path)]) == 0
    document = json.loads(output_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert "검증 완료: 30 cases / 32 exact reads" in captured.out
    assert f"packet_set_sha256={document['packet_set_sha256']}" in captured.out

    original = output_path.read_bytes()
    assert main(["--output", str(output_path)]) == 1
    captured = capsys.readouterr()
    assert "이미 존재" in captured.err
    assert output_path.read_bytes() == original
