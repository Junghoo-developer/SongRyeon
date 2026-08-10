"""ARM/SongRyeon mechanism experiment용 동일 증거 packet을 만든다.

이 모듈은 모델에게 증거를 고르게 하지 않는다. 동결된 evidence plan의 정확한
``read_python_file`` 요청을 ``FileToolbox``로 한 번씩 실행하고, 모든 비교
조건이 재사용할 작은 canonical packet으로 바꾼다.

정답 fixture(``expected_a_facts``, ``supported_code_claims``)는 plan 검증에만
사용한다. 모델에게 전달할 ``payload``에는 활성 목표, 불투명 ID의 R 기억,
코드가 직접 실행한 A 도구 결과만 들어간다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from agent_tools import FileToolbox, READ_PYTHON_FILE, ToolResult

from .runner import PROJECT_DIRECTORY, load_manifest


SCHEMA_VERSION = 1
PACKET_SET_ID = "songryeon-arm-mechanism-exact-evidence-v1"
DEFAULT_SOURCE_MANIFEST_PATH = (
    Path(__file__).resolve().parent
    / "evidence_laundering_cases"
    / "manifest.json"
)
DEFAULT_EVIDENCE_PLAN_PATH = (
    Path(__file__).resolve().parent
    / "arm_mechanism_cases"
    / "EVIDENCE_PLAN.json"
)

_PLAN_KEYS = {
    "schema_version",
    "plan_id",
    "source_manifest_path",
    "source_manifest_sha256",
    "cases",
}
_PLAN_CASE_KEYS = {"case_id", "requests"}
_REQUEST_KEYS = {"tool_name", "arguments"}
_PACKET_SET_KEYS = {
    "schema_version",
    "packet_set_id",
    "source_manifest",
    "evidence_plan",
    "packet_count",
    "packets",
    "packet_set_sha256",
}
_PACKET_KEYS = {"case_id", "payload", "packet_sha256"}
_PAYLOAD_KEYS = {"active_goal", "fixture_memory", "tool_results"}
_MEMORY_KEYS = {
    "memory_id",
    "information",
    "information_class",
    "code_verifiable",
}
_TOOL_RESULT_KEYS = {
    "tool_name",
    "arguments",
    "success",
    "content",
    "error",
    "information_class",
    "code_verifiable",
}


def canonical_json_sha256(value):
    """JSON 값의 키 순서·공백과 무관한 SHA-256을 반환한다."""

    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json_object(path, label):
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{label}은 JSON 파일이어야 합니다.")

    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}은 유효한 UTF-8 JSON이어야 합니다.") from error

    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위 값은 객체여야 합니다.")
    return resolved, value


def _require_exact_keys(value, expected, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}은 객체여야 합니다.")

    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        raise ValueError(
            f"{label} 필드가 다릅니다. missing={missing}, unknown={unknown}"
        )


def _nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}는 비어 있지 않은 문자열이어야 합니다.")
    return value


def _manifest_relative_path(manifest_path):
    resolved = Path(manifest_path).resolve(strict=True)
    try:
        return resolved.relative_to(PROJECT_DIRECTORY.resolve()).as_posix()
    except ValueError as error:
        raise ValueError("source manifest는 프로젝트 폴더 안에 있어야 합니다.") from error


def _expected_read_paths(case):
    """정답을 packet에 넣지 않고 plan 경로의 완전성만 검증한다."""

    return [
        fact.value
        for fact in case.expected_a_facts
        if fact.name == "tool_call.any.path"
    ]


def _load_evidence_plan_for_manifest(path, manifest):
    resolved, document = _read_json_object(path, "evidence plan")
    _require_exact_keys(document, _PLAN_KEYS, "evidence plan")

    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("지원하지 않는 evidence plan schema_version입니다.")

    plan_id = _nonempty_string(document["plan_id"], "plan_id")
    declared_manifest_path = _nonempty_string(
        document["source_manifest_path"],
        "source_manifest_path",
    )
    if declared_manifest_path != _manifest_relative_path(manifest.path):
        raise ValueError("evidence plan의 source manifest 경로가 다릅니다.")
    if document["source_manifest_sha256"] != manifest.sha256:
        raise ValueError("evidence plan의 source manifest SHA-256이 다릅니다.")

    case_values = document["cases"]
    if not isinstance(case_values, list) or not case_values:
        raise ValueError("evidence plan cases에는 한 개 이상의 항목이 필요합니다.")
    if len(case_values) != len(manifest.cases):
        raise ValueError("evidence plan과 manifest의 case 수가 다릅니다.")

    normalized_cases = []
    request_count = 0
    for index, (case_value, manifest_case) in enumerate(
        zip(case_values, manifest.cases, strict=True)
    ):
        label = f"cases[{index}]"
        _require_exact_keys(case_value, _PLAN_CASE_KEYS, label)
        case_id = _nonempty_string(case_value["case_id"], f"{label}.case_id")
        if case_id != manifest_case.case_id:
            raise ValueError("evidence plan의 case 순서 또는 ID가 manifest와 다릅니다.")

        request_values = case_value["requests"]
        if not isinstance(request_values, list) or not request_values:
            raise ValueError(f"{label}.requests에는 요청이 하나 이상 필요합니다.")

        normalized_requests = []
        signatures = set()
        for request_index, request_value in enumerate(request_values):
            request_label = f"{label}.requests[{request_index}]"
            _require_exact_keys(request_value, _REQUEST_KEYS, request_label)
            if request_value["tool_name"] != READ_PYTHON_FILE:
                raise ValueError("evidence plan은 read_python_file만 허용합니다.")
            arguments = request_value["arguments"]
            _require_exact_keys(arguments, {"path"}, f"{request_label}.arguments")
            path_value = _nonempty_string(
                arguments["path"],
                f"{request_label}.arguments.path",
            )
            signature = (READ_PYTHON_FILE, path_value)
            if signature in signatures:
                raise ValueError(f"{label}에 중복 도구 요청이 있습니다.")
            signatures.add(signature)
            normalized_requests.append(
                {
                    "tool_name": READ_PYTHON_FILE,
                    "arguments": {"path": path_value},
                }
            )

        planned_paths = [
            request["arguments"]["path"]
            for request in normalized_requests
        ]
        if planned_paths != _expected_read_paths(manifest_case):
            raise ValueError(
                f"{case_id}의 정확한 read 경로가 frozen manifest와 다릅니다."
            )
        request_count += len(normalized_requests)
        normalized_cases.append(
            {
                "case_id": case_id,
                "requests": normalized_requests,
            }
        )

    normalized = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "source_manifest_path": declared_manifest_path,
        "source_manifest_sha256": manifest.sha256,
        "cases": normalized_cases,
        "plan_sha256": canonical_json_sha256(document),
        "request_count": request_count,
        "path": resolved.as_posix(),
    }
    return normalized


def load_evidence_plan(
    path=DEFAULT_EVIDENCE_PLAN_PATH,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
):
    """동결 plan과 source manifest의 경로·hash·case 행렬을 검증한다."""

    manifest = load_manifest(manifest_path)
    return _load_evidence_plan_for_manifest(path, manifest)


def _fixture_memory_payload(fixture_input):
    records = fixture_input.get("records", [])
    if not isinstance(records, list):
        raise ValueError("fixture_input.records는 배열이어야 합니다.")

    payload = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict) or set(record) != {
            "record_id",
            "information_class",
            "information",
        }:
            raise ValueError("fixture memory record 형식이 올바르지 않습니다.")
        if record["information_class"] != "relative":
            raise ValueError("mechanism packet의 fixture memory는 R만 허용합니다.")
        information = _nonempty_string(
            record["information"],
            "fixture memory information",
        )
        payload.append(
            {
                # 원래 record_id에는 역할을 암시하는 단어가 들어갈 수 있으므로
                # manifest 순서만 반영한 불투명 ID로 치환한다.
                "memory_id": f"memory-{index:03d}",
                "information": information,
                "information_class": "relative",
                "code_verifiable": False,
            }
        )
    return payload


def _tool_result_payload(result):
    if not isinstance(result, ToolResult):
        raise TypeError("toolbox.execute는 ToolResult를 반환해야 합니다.")
    return {
        "tool_name": result.tool_name,
        "arguments": result.arguments,
        "success": result.success,
        "content": result.content,
        "error": result.error,
        "information_class": "absolute",
        "code_verifiable": True,
    }


def _packet_set_core(manifest, plan, packets):
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_set_id": PACKET_SET_ID,
        "source_manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "case_count": len(manifest.cases),
        },
        "evidence_plan": {
            "plan_id": plan["plan_id"],
            "plan_sha256": plan["plan_sha256"],
            "request_count": plan["request_count"],
        },
        "packet_count": len(packets),
        "packets": packets,
    }


def build_exact_evidence_packet_set(
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    evidence_plan_path=DEFAULT_EVIDENCE_PLAN_PATH,
    toolbox_factory=FileToolbox,
):
    """30개 case의 모델 독립적 exact-read evidence packet을 만든다."""

    manifest = load_manifest(manifest_path)
    plan = _load_evidence_plan_for_manifest(evidence_plan_path, manifest)
    packets = []

    for manifest_case, plan_case in zip(
        manifest.cases,
        plan["cases"],
        strict=True,
    ):
        toolbox = toolbox_factory(allowed_root=manifest.project_fixture_root)
        tool_results = [
            _tool_result_payload(
                toolbox.execute(
                    request["tool_name"],
                    request["arguments"],
                )
            )
            for request in plan_case["requests"]
        ]
        payload = {
            "active_goal": manifest.questions[manifest_case.case_id],
            "fixture_memory": _fixture_memory_payload(
                manifest.fixture_inputs[manifest_case.case_id]
            ),
            "tool_results": tool_results,
        }
        packet_identity = {
            "case_id": manifest_case.case_id,
            "payload": payload,
        }
        packets.append(
            {
                **packet_identity,
                "packet_sha256": canonical_json_sha256(packet_identity),
            }
        )

    core = _packet_set_core(manifest, plan, packets)
    return {
        **core,
        "packet_set_sha256": canonical_json_sha256(core),
    }


def validate_evidence_packet_set(
    document,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    evidence_plan_path=DEFAULT_EVIDENCE_PLAN_PATH,
    toolbox_factory=FileToolbox,
):
    """packet의 구조·hash와 현재 frozen source에서의 재생 결과를 검증한다."""

    _require_exact_keys(document, _PACKET_SET_KEYS, "packet set")
    packets = document.get("packets")
    if not isinstance(packets, list):
        raise ValueError("packet set packets는 배열이어야 합니다.")

    for index, packet in enumerate(packets):
        _require_exact_keys(packet, _PACKET_KEYS, f"packets[{index}]")
        _require_exact_keys(
            packet["payload"],
            _PAYLOAD_KEYS,
            f"packets[{index}].payload",
        )
        for memory_index, memory in enumerate(packet["payload"]["fixture_memory"]):
            _require_exact_keys(
                memory,
                _MEMORY_KEYS,
                f"packets[{index}].fixture_memory[{memory_index}]",
            )
        for tool_index, result in enumerate(packet["payload"]["tool_results"]):
            _require_exact_keys(
                result,
                _TOOL_RESULT_KEYS,
                f"packets[{index}].tool_results[{tool_index}]",
            )

    expected = build_exact_evidence_packet_set(
        manifest_path=manifest_path,
        evidence_plan_path=evidence_plan_path,
        toolbox_factory=toolbox_factory,
    )
    if document != expected:
        raise ValueError("packet set이 frozen plan의 deterministic 재생 결과와 다릅니다.")

    return {
        "packet_set_id": document["packet_set_id"],
        "packet_count": document["packet_count"],
        "request_count": document["evidence_plan"]["request_count"],
        "source_manifest_sha256": document["source_manifest"][
            "manifest_sha256"
        ],
        "evidence_plan_sha256": document["evidence_plan"]["plan_sha256"],
        "packet_set_sha256": document["packet_set_sha256"],
    }


def write_exact_evidence_packet_set(
    output_path,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    evidence_plan_path=DEFAULT_EVIDENCE_PLAN_PATH,
    toolbox_factory=FileToolbox,
):
    """새 파일에 packet set을 원자적으로 저장하고 다시 읽어 검증한다.

    이미 존재하는 파일이나 디렉터리는 덮어쓰지 않는다. 임시 파일과 목적지는
    같은 디렉터리에 두고 hard link의 배타적 생성 성질을 이용해 경쟁 상황에서도
    기존 결과를 교체하지 않는다.
    """

    destination = Path(output_path).resolve()
    if destination.exists():
        raise FileExistsError(f"출력 경로가 이미 존재합니다: {destination}")
    if not destination.parent.is_dir():
        raise ValueError(f"출력 디렉터리가 존재하지 않습니다: {destination.parent}")

    document = build_exact_evidence_packet_set(
        manifest_path=manifest_path,
        evidence_plan_path=evidence_plan_path,
        toolbox_factory=toolbox_factory,
    )
    validate_evidence_packet_set(
        document,
        manifest_path=manifest_path,
        evidence_plan_path=evidence_plan_path,
        toolbox_factory=toolbox_factory,
    )
    serialized = json.dumps(
        document,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    _, saved = _read_json_object(destination, "저장된 packet set")
    summary = validate_evidence_packet_set(
        saved,
        manifest_path=manifest_path,
        evidence_plan_path=evidence_plan_path,
        toolbox_factory=toolbox_factory,
    )
    return destination, summary


def _build_parser():
    parser = argparse.ArgumentParser(
        description="동결 plan에서 deterministic exact evidence packet을 생성합니다."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_SOURCE_MANIFEST_PATH,
    )
    parser.add_argument(
        "--evidence-plan",
        type=Path,
        default=DEFAULT_EVIDENCE_PLAN_PATH,
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        output_path, summary = write_exact_evidence_packet_set(
            args.output,
            manifest_path=args.manifest,
            evidence_plan_path=args.evidence_plan,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"evidence packet 생성 중단: {error}", file=sys.stderr)
        return 1

    print(
        f"검증 완료: {summary['packet_count']} cases / "
        f"{summary['request_count']} exact reads"
    )
    print(f"packet_set_sha256={summary['packet_set_sha256']}")
    print(f"저장: {output_path}")
    return 0


__all__ = [
    "DEFAULT_EVIDENCE_PLAN_PATH",
    "DEFAULT_SOURCE_MANIFEST_PATH",
    "PACKET_SET_ID",
    "build_exact_evidence_packet_set",
    "canonical_json_sha256",
    "load_evidence_plan",
    "validate_evidence_packet_set",
    "write_exact_evidence_packet_set",
]


if __name__ == "__main__":
    raise SystemExit(main())
