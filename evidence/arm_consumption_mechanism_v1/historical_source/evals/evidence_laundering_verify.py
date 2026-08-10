"""근거 세탁 확인 실험의 동결 상태와 raw capture를 오프라인 검증한다."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from .runner import _portable_text_sha256, load_manifest
from .source_identity import (
    REQUIRED_SUT_PYTHON_ROOTS as GENERIC_SUT_PYTHON_ROOTS,
    _system_source_entries,
    _tree_sha256,
)
from .variants import SUPPORTED_VARIANTS


DEFAULT_CASE_ROOT = (
    Path(__file__).resolve().parent / "evidence_laundering_cases"
)
FREEZE_FILENAME = "FREEZE.json"
MANIFEST_FILENAME = "manifest.json"
RUN_PLAN_FILENAME = "RUN_PLAN.json"
CAPTURE_FILENAME = "capture.json"
SCHEMA_VERSION = 1
EXPECTED_EXPERIMENT_ID = "songryeon-evidence-laundering-confirmatory-v1"
EXPECTED_MANIFEST_PATH = "evals/evidence_laundering_cases/manifest.json"
EXPECTED_OUTPUT_ROOT = ".tmp/evals/evidence_laundering_confirmatory_v1"
EXPECTED_MODEL = {
    "name": "gemma4:26b",
    "digest_prefix": "5571076f3d70",
    "num_ctx": 16_384,
    "temperature": 0,
    "timeout_seconds": 180,
    "keep_alive": "10m",
}
EXPECTED_CASE_WALL_CLOCK_LIMIT_SECONDS = 600
EXPECTED_MAXIMUM_TOOL_CALLS_PER_CASE = 3
EXPECTED_RUNS = (
    {
        "block": 1,
        "seed": 42,
        "variants": list(SUPPORTED_VARIANTS),
    },
    {
        "block": 2,
        "seed": 43,
        "variants": [
            "songryeon-no-node4",
            "songryeon-full",
            "single-tool-agent",
        ],
    },
    {
        "block": 3,
        "seed": 44,
        "variants": [
            "songryeon-full",
            "single-tool-agent",
            "songryeon-no-node4",
        ],
    },
)
REQUIRED_FREEZE_BASE_FILES = frozenset(
    {
        MANIFEST_FILENAME,
        "PROTOCOL.md",
        "SCORING_RUBRIC.md",
        RUN_PLAN_FILENAME,
    }
)
# 이 실험은 아래의 과거 파일 집합으로 이미 동결됐다. 일반 평가 경로가
# source_identity.py로 옮겨져도 이 목록과 공개 이름은 바꾸지 않는다.
LEGACY_REQUIRED_SUT_PYTHON_ROOTS = GENERIC_SUT_PYTHON_ROOTS
LEGACY_REQUIRED_SUT_FILES = (
    "evals/live_capture.py",
    "evals/variants.py",
    "evals/runner.py",
    "evals/evidence_laundering_verify.py",
    "pyproject.toml",
)
REQUIRED_SUT_PYTHON_ROOTS = LEGACY_REQUIRED_SUT_PYTHON_ROOTS
REQUIRED_SUT_FILES = LEGACY_REQUIRED_SUT_FILES
_PLAN_KEYS = {
    "schema_version",
    "experiment_id",
    "manifest_path",
    "manifest_sha256",
    "system_source_tree_sha256",
    "model",
    "case_wall_clock_limit_seconds",
    "maximum_tool_calls_per_case",
    "output_root",
    "planned_case_count",
    "planned_execution_count",
    "runs",
}
_FREEZE_KEYS = {
    "schema_version",
    "experiment_id",
    "frozen_before_live_outputs",
    "live_capture_started",
    "hash_mode",
    "manifest_canonical_sha256",
    "system_under_test",
    "files",
}
_SYSTEM_FREEZE_KEYS = {
    "include_python_roots",
    "include_files",
    "file_count",
    "tree_sha256",
}
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")
_VARIANT_SYSTEM_CONTRACT = {
    "single-tool-agent": {
        "system_wrapper": "eval_single_tool_agent",
        "node4_mode": "absent",
    },
    "songryeon-no-node4": {
        "system_wrapper": "songryeon_eval_no_node4",
        "node4_mode": "eval_only_deterministic_bypass",
    },
    "songryeon-full": {
        "system_wrapper": "songryeon",
        "node4_mode": "active",
    },
}


def _read_json(path, label):
    path = Path(path).resolve(strict=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}은 유효한 UTF-8 JSON이어야 합니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위 값은 객체여야 합니다.")
    return value


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _require_exact_keys(value, expected, label):
    _require(isinstance(value, dict), f"{label}은 객체여야 합니다.")
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    _require(
        not missing and not unknown,
        f"{label} 필드가 다릅니다. missing={missing}, unknown={unknown}",
    )


def _resolve_inside(root, relative_path, label):
    root = Path(root).resolve(strict=True)
    path = (root / relative_path).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}이 허용 폴더 밖을 가리킵니다.") from error
    return path


def current_system_source_identity():
    """과거 evidence-laundering 동결 대상의 현재 식별값을 반환한다."""

    entries = _system_source_entries(
        LEGACY_REQUIRED_SUT_PYTHON_ROOTS,
        LEGACY_REQUIRED_SUT_FILES,
    )
    return {
        "include_python_roots": list(LEGACY_REQUIRED_SUT_PYTHON_ROOTS),
        "include_files": list(LEGACY_REQUIRED_SUT_FILES),
        "file_count": len(entries),
        "tree_sha256": _tree_sha256(entries),
    }


def _required_freeze_paths(manifest):
    fixture_paths = {
        fixture.path
        for fixture in (*manifest.source_fixtures, *manifest.boundary_fixtures)
    }
    return REQUIRED_FREEZE_BASE_FILES | fixture_paths


def _safe_name(value):
    _require(isinstance(value, str), "식별자는 문자열이어야 합니다.")
    safe = _SAFE_NAME_PATTERN.sub("-", value).strip("-._").lower()
    _require(bool(safe), "식별자를 안전한 파일 이름으로 바꿀 수 없습니다.")
    return safe


def _project_fixture_identity(manifest):
    source_entries = sorted(
        (fixture.to_dict() for fixture in manifest.source_fixtures),
        key=lambda fixture: fixture["path"],
    )
    payload = json.dumps(
        source_entries,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "manifest_relative_path": manifest.project_fixture_root.relative_to(
            manifest.path.parent
        ).as_posix(),
        "tree_sha256": hashlib.sha256(payload).hexdigest(),
        "python_file_count": len(source_entries),
    }


def _require_loopback_base_url(value):
    _require(isinstance(value, str) and value, "capture base_url이 없습니다.")
    parsed = urlparse(value)
    _require(
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.username is None
        and parsed.password is None,
        "capture base_url이 credential 없는 loopback HTTP(S) URL이 아닙니다.",
    )


def _read_jsonl(path):
    events = []
    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                _require(
                    isinstance(event, dict),
                    f"raw artifact {line_number}번 event가 객체가 아닙니다.",
                )
                events.append(event)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("raw artifact는 유효한 UTF-8 JSONL이어야 합니다.") from error
    return events


def _event_type_counts(events):
    return dict(
        sorted(Counter(event.get("information_type", "<missing>") for event in events).items())
    )


def _parse_final_delivery(event):
    try:
        delivery = json.loads(event["information"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(delivery, dict):
        return None
    return delivery.get("answer_information_id")


def _verify_registered_experiment(
    case_root=DEFAULT_CASE_ROOT,
    *,
    require_current_system,
):
    """등록된 실험을 검증하고, 선택적으로 현재 SUT 일치도 강제한다."""

    case_root = Path(case_root).resolve(strict=True)
    manifest = load_manifest(case_root / MANIFEST_FILENAME)
    plan = _read_json(case_root / RUN_PLAN_FILENAME, "run plan")
    freeze = _read_json(case_root / FREEZE_FILENAME, "freeze")

    _require_exact_keys(plan, _PLAN_KEYS, "run plan")
    _require_exact_keys(freeze, _FREEZE_KEYS, "freeze")
    _require(plan.get("schema_version") == SCHEMA_VERSION,
             "지원하지 않는 run plan schema_version입니다.")
    _require(freeze.get("schema_version") == SCHEMA_VERSION,
             "지원하지 않는 freeze schema_version입니다.")
    _require(plan.get("experiment_id") == EXPECTED_EXPERIMENT_ID,
             "run plan experiment_id가 다릅니다.")
    _require(freeze.get("experiment_id") == EXPECTED_EXPERIMENT_ID,
             "freeze experiment_id가 다릅니다.")
    _require(plan.get("manifest_path") == EXPECTED_MANIFEST_PATH,
             "run plan manifest 경로가 사전등록값과 다릅니다.")
    _require(plan.get("output_root") == EXPECTED_OUTPUT_ROOT,
             "run plan output root가 사전등록값과 다릅니다.")
    _require(plan.get("model") == EXPECTED_MODEL,
             "run plan model 실행조건이 사전등록값과 다릅니다.")
    _require(
        plan.get("case_wall_clock_limit_seconds")
        == EXPECTED_CASE_WALL_CLOCK_LIMIT_SECONDS,
        "run plan case wall-clock 한도가 사전등록값과 다릅니다.",
    )
    _require(
        plan.get("maximum_tool_calls_per_case")
        == EXPECTED_MAXIMUM_TOOL_CALLS_PER_CASE,
        "run plan 공통 도구 예산이 사전등록값과 다릅니다.",
    )
    _require(freeze.get("frozen_before_live_outputs") is True,
             "live 출력 전 동결 표시가 없습니다.")
    _require(freeze.get("live_capture_started") is False,
             "동결 시점에 live capture가 시작된 것으로 기록됐습니다.")
    _require(freeze.get("hash_mode") == "utf8_lf_normalized_sha256",
             "지원하지 않는 freeze hash 방식입니다.")
    _require(plan.get("manifest_sha256") == manifest.sha256,
             "run plan의 manifest SHA-256이 다릅니다.")
    _require(freeze.get("manifest_canonical_sha256") == manifest.sha256,
             "freeze의 manifest SHA-256이 다릅니다.")

    files = freeze.get("files")
    _require(isinstance(files, list) and files, "freeze files가 필요합니다.")
    seen = set()
    for entry in files:
        _require(isinstance(entry, dict), "freeze file 항목은 객체여야 합니다.")
        _require(set(entry) == {"path", "sha256"},
                 "freeze file 항목 필드가 올바르지 않습니다.")
        relative = entry["path"]
        _require(isinstance(relative, str) and relative,
                 "freeze file 경로는 비어 있지 않은 문자열이어야 합니다.")
        _require(relative not in seen, "freeze file 경로가 중복됐습니다.")
        seen.add(relative)
        path = _resolve_inside(case_root, relative, "freeze file")
        _require(path.is_file(), "freeze file은 파일이어야 합니다.")
        _require(_portable_text_sha256(path) == entry["sha256"],
                 f"freeze file SHA-256이 다릅니다: {relative}")
    required_freeze_paths = _required_freeze_paths(manifest)
    _require(
        seen == required_freeze_paths,
        "freeze file 집합이 필수 protocol·plan·manifest fixture 집합과 다릅니다. "
        f"missing={sorted(required_freeze_paths - seen)}, "
        f"unknown={sorted(seen - required_freeze_paths)}",
    )

    system_freeze = freeze.get("system_under_test")
    _require_exact_keys(system_freeze, _SYSTEM_FREEZE_KEYS, "SUT freeze")
    _require(
        system_freeze.get("include_python_roots")
        == list(REQUIRED_SUT_PYTHON_ROOTS),
        "SUT Python root 집합 또는 순서가 필수값과 다릅니다.",
    )
    _require(
        system_freeze.get("include_files") == list(REQUIRED_SUT_FILES),
        "SUT 개별 파일 집합 또는 순서가 필수값과 다릅니다.",
    )
    frozen_file_count = system_freeze.get("file_count")
    _require(
        isinstance(frozen_file_count, int)
        and not isinstance(frozen_file_count, bool)
        and frozen_file_count > 0,
        "SUT freeze 파일 수가 올바르지 않습니다.",
    )
    frozen_tree_sha256 = system_freeze.get("tree_sha256")
    _require(
        isinstance(frozen_tree_sha256, str)
        and _SHA256_PATTERN.fullmatch(frozen_tree_sha256) is not None,
        "SUT freeze source tree SHA-256이 올바르지 않습니다.",
    )
    _require(
        plan.get("system_source_tree_sha256") == frozen_tree_sha256,
        "run plan과 freeze의 SUT source tree SHA-256이 다릅니다.",
    )

    if require_current_system:
        current_system = current_system_source_identity()
        _require(
            frozen_file_count == current_system["file_count"],
            "SUT source 파일 수가 다릅니다.",
        )
        _require(
            frozen_tree_sha256 == current_system["tree_sha256"],
            "SUT source tree SHA-256이 다릅니다.",
        )

    runs = plan.get("runs")
    _require(runs == list(EXPECTED_RUNS),
             "run block·seed·variant 순서가 사전등록 순서와 다릅니다.")
    _require(plan.get("planned_case_count") == len(manifest.cases),
             "계획 case 수가 manifest와 다릅니다.")
    expected_executions = len(manifest.cases) * len(SUPPORTED_VARIANTS) * len(runs)
    _require(plan.get("planned_execution_count") == expected_executions,
             "계획 실행 수가 다릅니다.")

    return {
        "manifest_sha256": manifest.sha256,
        "case_count": len(manifest.cases),
        "planned_execution_count": expected_executions,
        "system_source_file_count": frozen_file_count,
        "system_source_tree_sha256": frozen_tree_sha256,
    }


def verify_registered_experiment(case_root=DEFAULT_CASE_ROOT):
    """과거 동결 등록을 현재 체크아웃과 독립적으로 검증한다.

    이 함수는 frozen protocol·fixture·계획의 자체 일관성만 확인한다.
    현재 소스로 새 live capture를 실행할 수 있다는 뜻은 아니다.
    """

    return _verify_registered_experiment(
        case_root,
        require_current_system=False,
    )


def verify_preflight(case_root=DEFAULT_CASE_ROOT):
    """첫 모델 호출 전 현재 SUT까지 동결본과 같은지 확인한다."""

    return _verify_registered_experiment(
        case_root,
        require_current_system=True,
    )


def _verify_raw_artifact(capture_dir, capture):
    artifact = capture.get("raw_memory_artifact")
    _require(isinstance(artifact, dict), "raw artifact 정보가 없습니다.")
    path = _resolve_inside(capture_dir, artifact.get("path"), "raw artifact")
    _require(path.is_file(), "raw artifact가 파일이 아닙니다.")
    raw_bytes = path.read_bytes()
    actual = hashlib.sha256(raw_bytes).hexdigest()
    _require(actual == artifact.get("sha256"), "raw artifact SHA-256이 다릅니다.")
    _require(artifact.get("byte_count") == len(raw_bytes),
             "raw artifact byte_count가 실제 파일과 다릅니다.")
    _require(artifact.get("format") == "songryeon-memory-jsonl",
             "raw artifact format이 다릅니다.")
    _require("parse_error" not in artifact,
             "raw artifact capture 시 JSONL 해석 오류가 기록됐습니다.")

    events = _read_jsonl(path)
    _require(artifact.get("event_count") == len(events),
             "raw artifact event_count가 실제 JSONL과 다릅니다.")
    event_counts = _event_type_counts(events)
    _require(
        artifact.get("information_type_counts") == event_counts,
        "raw artifact information_type_counts가 실제 JSONL과 다릅니다.",
    )
    _require(capture.get("tool_call_count") == event_counts.get("tool_raw_name", 0),
             "capture tool_call_count가 raw JSONL과 다릅니다.")
    _require(
        capture.get("model_exchange_count")
        == event_counts.get("model_raw_status", 0),
        "capture model_exchange_count가 raw JSONL과 다릅니다.",
    )

    evaluated_question = capture.get("evaluated_question")
    _require(isinstance(evaluated_question, str) and evaluated_question,
             "capture evaluated_question이 없습니다.")
    current_turn_id = capture.get("turn_id")
    current_user_inputs = [
        event
        for event in events
        if event.get("information_type") == "user_input"
        and event.get("information") == evaluated_question
        and (
            current_turn_id is None
            or event.get("turn_id") == current_turn_id
        )
    ]
    _require(current_user_inputs,
             "raw artifact에서 현재 평가 질문의 user_input을 찾지 못했습니다.")

    answer = capture.get("answer")
    completed = capture.get("completed")
    _require(isinstance(completed, bool), "capture completed는 bool이어야 합니다.")
    if completed:
        _require(isinstance(current_turn_id, str) and current_turn_id,
                 "완료 capture의 turn_id가 없습니다.")
        _require(isinstance(answer, str) and answer,
                 "완료 capture의 answer가 없습니다.")
        _require(capture.get("error") is None,
                 "완료 capture에 error가 함께 기록됐습니다.")
        _require(capture.get("wall_clock_limit_exhausted") is False,
                 "완료 capture가 wall-clock 한도를 소진했습니다.")

    if answer is not None:
        _require(isinstance(answer, str) and answer,
                 "capture answer는 비어 있지 않은 문자열 또는 null이어야 합니다.")
        _require(isinstance(current_turn_id, str) and current_turn_id,
                 "answer가 있는 capture의 turn_id가 없습니다.")
        answer_records = {
            event.get("information_id"): event
            for event in events
            if event.get("information_type") == "node3_answer"
            and event.get("information") == answer
            and isinstance(event.get("information_id"), str)
            and isinstance(event.get("turn_id"), str)
            and event["turn_id"].startswith(current_turn_id)
        }
        _require(answer_records,
                 "raw artifact에서 capture answer의 node3_answer를 찾지 못했습니다.")
        delivered_ids = {
            _parse_final_delivery(event)
            for event in events
            if event.get("information_type") == "final_delivery"
            and isinstance(event.get("turn_id"), str)
            and event["turn_id"].startswith(f"{current_turn_id}-final")
        }
        _require(
            len(set(answer_records) & delivered_ids) == 1,
            "raw artifact final_delivery가 capture answer를 유일하게 가리키지 않습니다.",
        )
    elif not events:
        _require(not completed and isinstance(capture.get("error"), dict),
                 "빈 raw artifact는 명시적인 실패 capture에서만 허용됩니다.")

    return path


def _verify_system(system, run, plan):
    _require(isinstance(system, dict), "capture system 항목은 객체여야 합니다.")
    variant = system.get("variant")
    _require(variant in SUPPORTED_VARIANTS,
             "capture에 지원하지 않는 variant가 있습니다.")
    expected_contract = _VARIANT_SYSTEM_CONTRACT[variant]
    _require(system.get("system_wrapper") == expected_contract["system_wrapper"],
             f"{variant} system_wrapper가 다릅니다.")
    _require(system.get("node4_mode") == expected_contract["node4_mode"],
             f"{variant} node4_mode가 다릅니다.")
    _require(system.get("comparison_group") == "architecture_same_backbone",
             "confirmatory system의 comparison_group이 다릅니다.")

    model_plan = plan["model"]
    _require(system.get("backbone") == model_plan["name"],
             "capture backbone이 run plan과 다릅니다.")
    _require(system.get("model_tag") == model_plan["name"],
             "capture model tag가 run plan과 다릅니다.")
    model_id = system.get("model_id")
    _require(
        isinstance(model_id, str)
        and _SHA256_PATTERN.fullmatch(model_id)
        and model_id.startswith(model_plan["digest_prefix"]),
        "capture model digest가 run plan과 다릅니다.",
    )
    _require(system.get("provider") == "ollama",
             "confirmatory capture provider는 Ollama여야 합니다.")
    _require(system.get("execution_profile") == "contest_local_or_self_hosted",
             "confirmatory capture 실행 profile이 다릅니다.")
    _require(isinstance(system.get("server_version"), str)
             and bool(system["server_version"]),
             "capture Ollama server version이 없습니다.")

    configuration = system.get("configuration")
    _require(isinstance(configuration, dict),
             "capture system configuration이 없습니다.")
    _require_loopback_base_url(configuration.get("base_url"))
    for name in ("num_ctx", "timeout_seconds", "keep_alive", "temperature"):
        _require(
            configuration.get(name) == model_plan[name],
            f"capture {name}이 run plan과 다릅니다.",
        )
    _require(configuration.get("seed") == run["seed"],
             "capture seed가 run plan과 다릅니다.")

    runtime_contract = system.get("runtime_contract")
    _require(isinstance(runtime_contract, dict),
             "capture runtime_contract가 없습니다.")
    _require(
        runtime_contract.get("maximum_tool_calls_per_case")
        == plan["maximum_tool_calls_per_case"],
        "capture의 공통 도구 예산이 run plan과 다릅니다.",
    )
    expected_system_name = f"{variant}-{_safe_name(model_plan['name'])}"
    _require(system.get("system_name") == expected_system_name,
             f"{variant} system_name이 결정적 이름과 다릅니다.")
    return model_id


def verify_captures(capture_root, case_root=DEFAULT_CASE_ROOT):
    """세 block의 capture 메타정보와 raw artifact를 run plan에 대조한다."""

    # 이미 생성된 capture는 당시 frozen SUT identity에 대조한다. 현재
    # 체크아웃의 일치 여부는 새 실행 직전 verify_preflight가 별도로 맡는다.
    preflight = verify_registered_experiment(case_root)
    case_root = Path(case_root).resolve(strict=True)
    manifest = load_manifest(case_root / MANIFEST_FILENAME)
    plan = _read_json(case_root / RUN_PLAN_FILENAME, "run plan")
    capture_root = Path(capture_root).resolve(strict=True)
    digest_prefix = plan["model"]["digest_prefix"]
    expected_project_fixture = _project_fixture_identity(manifest)
    expected_case_ids = [case.case_id for case in manifest.cases]

    verified_captures = 0
    artifact_paths = set()
    observed_model_ids = set()
    observed_server_versions = set()
    for run in plan["runs"]:
        capture_dir = capture_root / f"seed-{run['seed']}"
        document = _read_json(capture_dir / CAPTURE_FILENAME, "capture")
        _require(document.get("schema_version") == SCHEMA_VERSION,
                 "지원하지 않는 capture schema_version입니다.")
        _require(document.get("capture_status") == "live_raw_draft",
                 "capture 상태가 raw draft가 아닙니다.")
        _require(document.get("publishable") is False,
                 "검토 전 capture는 publishable일 수 없습니다.")
        _require(document.get("uses_external_api") is False,
                 "confirmatory capture는 외부 API를 사용할 수 없습니다.")

        capture_manifest = document.get("manifest")
        _require(isinstance(capture_manifest, dict),
                 "capture manifest 정보가 없습니다.")
        _require(capture_manifest.get("manifest_id") == manifest.manifest_id,
                 "capture manifest_id가 다릅니다.")
        _require(capture_manifest.get("case_set_status") == manifest.case_set_status,
                 "capture case_set_status가 다릅니다.")
        _require(capture_manifest.get("case_count") == len(manifest.cases),
                 "capture manifest case_count가 다릅니다.")
        _require(capture_manifest.get("manifest_sha256") == preflight["manifest_sha256"],
                 "capture manifest SHA-256이 다릅니다.")

        conditions = document.get("conditions")
        _require(isinstance(conditions, dict), "capture conditions가 없습니다.")
        _require(conditions.get("case_memory_isolated") is True,
                 "capture가 case별 memory 격리를 확인하지 않았습니다.")
        _require(conditions.get("actual_memory_used") is False,
                 "confirmatory capture에 실제 memory가 사용됐습니다.")
        _require(conditions.get("project_fixture") == expected_project_fixture,
                 "capture project fixture identity가 manifest와 다릅니다.")
        file_toolbox_limit = conditions.get("file_toolbox_max_python_file_bytes")
        _require(
            isinstance(file_toolbox_limit, int)
            and not isinstance(file_toolbox_limit, bool)
            and file_toolbox_limit > 0,
            "capture file toolbox 크기 한도가 유효하지 않습니다.",
        )
        _require(conditions.get("same_model_generation_configuration") is True,
                 "capture가 동일 model 생성 설정을 확인하지 않았습니다.")
        _require(conditions.get("expected_manifest_sha256") == preflight["manifest_sha256"],
                 "capture가 frozen manifest를 fail-closed로 강제하지 않았습니다.")
        _require(conditions.get("expected_architecture_digest_prefix") == digest_prefix,
                 "capture의 기대 model digest prefix가 다릅니다.")
        _require(conditions.get("architecture_backbone_digest_consistent") is True,
                 "variant 간 model digest 일치가 확인되지 않았습니다.")
        _require(
            conditions.get("expected_system_source_tree_sha256")
            == preflight["system_source_tree_sha256"],
            "capture가 frozen SUT source tree를 fail-closed로 강제하지 않았습니다.",
        )
        _require(
            conditions.get("captured_system_source_tree_sha256")
            == preflight["system_source_tree_sha256"],
            "capture 직전 SUT source tree가 frozen tree와 다릅니다.",
        )
        _require(
            conditions.get("captured_system_source_file_count")
            == preflight["system_source_file_count"],
            "capture 직전 SUT source 파일 수가 frozen tree와 다릅니다.",
        )
        _require(
            conditions.get("same_case_wall_clock_limit_seconds")
            == plan["case_wall_clock_limit_seconds"],
            "capture case wall-clock 한도가 run plan과 다릅니다.",
        )
        _require(conditions.get("automatic_answer_grading") is False,
                 "raw capture 단계에서 자동 답안 채점이 수행됐습니다.")
        _require(conditions.get("architecture_backbone") == plan["model"]["name"],
                 "capture architecture backbone이 run plan과 다릅니다.")
        _require(conditions.get("architecture_variants") == run["variants"],
                 "capture architecture variant 순서가 run plan과 다릅니다.")
        _require(conditions.get("architecture_comparison_complete") is True,
                 "capture architecture 비교 행렬이 완전하지 않습니다.")
        _require(conditions.get("backbone_comparison_models") == [],
                 "confirmatory capture에 사전등록되지 않은 backbone 비교가 있습니다.")
        _require(conditions.get("bare_model_baseline_included") is False,
                 "confirmatory capture에 사전등록되지 않은 bare baseline이 있습니다.")
        _require(conditions.get("structural_effect_claim_allowed") is False,
                 "raw capture가 허용되지 않은 구조 인과 주장을 표시했습니다.")

        comparison_groups = document.get("comparison_groups")
        _require(isinstance(comparison_groups, dict),
                 "capture comparison_groups가 없습니다.")
        _require(
            comparison_groups.get("architecture_same_backbone")
            == {
                "backbone": plan["model"]["name"],
                "variants": run["variants"],
            },
            "architecture comparison group이 run plan과 다릅니다.",
        )
        _require(
            comparison_groups.get("backbone_full_songryeon")
            == {"backbones": [], "variant": "songryeon-full"},
            "confirmatory capture backbone group이 비어 있지 않습니다.",
        )

        systems = document.get("systems")
        _require(isinstance(systems, list), "capture systems는 배열이어야 합니다.")
        _require([system.get("variant") for system in systems] == run["variants"],
                 "capture variant 순서가 run plan과 다릅니다.")
        system_names = [system.get("system_name") for system in systems]
        _require(len(system_names) == len(set(system_names)),
                 "capture system_name이 중복됐습니다.")
        for system in systems:
            observed_model_ids.add(_verify_system(system, run, plan))
            observed_server_versions.add(system["server_version"])
            _require(
                system["runtime_contract"].get(
                    "file_toolbox_max_python_file_bytes"
                )
                == file_toolbox_limit,
                "system과 capture의 file toolbox 크기 한도가 다릅니다.",
            )

        captures = document.get("captures")
        _require(isinstance(captures, list), "capture 목록은 배열이어야 합니다.")
        expected_count = plan["planned_case_count"] * len(SUPPORTED_VARIANTS)
        _require(len(captures) == expected_count,
                 "block의 system/case capture 수가 다릅니다.")
        expected_pairs = [
            (system_name, case_id)
            for system_name in system_names
            for case_id in expected_case_ids
        ]
        actual_pairs = []
        for capture in captures:
            _require(isinstance(capture, dict),
                     "system/case capture 항목은 객체여야 합니다.")
            pair = (capture.get("system_name"), capture.get("case_id"))
            actual_pairs.append(pair)
        _require(len(actual_pairs) == len(set(actual_pairs)),
                 "같은 system_name과 case_id capture가 중복됐습니다.")
        _require(actual_pairs == expected_pairs,
                 "capture가 사전등록된 system×case 행렬 또는 순서와 다릅니다.")

        for capture in captures:
            case_id = capture["case_id"]
            question = manifest.questions[case_id]
            _require(
                capture.get("manifest_question") == question,
                f"{case_id} capture 질문이 manifest와 다릅니다.",
            )
            _require(capture.get("evaluated_question") == question,
                     f"{case_id} 실제 평가 질문이 manifest와 다릅니다.")
            _require(capture.get("evaluated_turn_index") == 0,
                     f"{case_id} evaluated_turn_index가 사전등록값과 다릅니다.")
            _require(
                capture.get("conversation_turns")
                == [{"role": "user", "content": question, "evaluate": True}],
                f"{case_id} conversation_turns가 사전등록 질문과 다릅니다.",
            )
            _require(
                capture.get("wall_clock_limit_seconds")
                == plan["case_wall_clock_limit_seconds"],
                f"{case_id} wall-clock 한도가 run plan과 다릅니다.",
            )
            tool_call_count = capture.get("tool_call_count")
            _require(
                isinstance(tool_call_count, int)
                and not isinstance(tool_call_count, bool)
                and 0 <= tool_call_count <= plan["maximum_tool_calls_per_case"],
                f"{case_id} 도구 호출 수가 공통 예산 밖입니다.",
            )
            expected_artifact_path = (
                Path("raw")
                / _safe_name(capture["system_name"])
                / f"{_safe_name(case_id)}.memory.jsonl"
            ).as_posix()
            _require(
                capture.get("raw_memory_artifact", {}).get("path")
                == expected_artifact_path,
                f"{case_id} raw artifact 경로가 system/case 귀속과 다릅니다.",
            )
            artifact_path = _verify_raw_artifact(capture_dir, capture)
            _require(artifact_path not in artifact_paths,
                     "같은 raw artifact 경로가 둘 이상의 capture에 사용됐습니다.")
            artifact_paths.add(artifact_path)

        coverage = document.get("coverage")
        _require(isinstance(coverage, dict), "capture coverage가 없습니다.")
        _require(coverage.get("system_count") == len(SUPPORTED_VARIANTS),
                 "capture coverage system_count가 다릅니다.")
        _require(coverage.get("unique_backbone_count") == 1,
                 "confirmatory capture backbone 수가 1이 아닙니다.")
        _require(coverage.get("case_count") == len(manifest.cases),
                 "capture coverage case_count가 다릅니다.")
        _require(coverage.get("capture_count") == expected_count,
                 "capture coverage capture_count가 다릅니다.")
        _require(coverage.get("complete_case_system_matrix") is True,
                 "capture coverage가 완전 행렬로 표시되지 않았습니다.")
        completed_count = sum(capture["completed"] for capture in captures)
        _require(coverage.get("completed_capture_count") == completed_count,
                 "capture coverage 완료 수가 실제 capture와 다릅니다.")
        _require(
            coverage.get("failed_capture_count") == expected_count - completed_count,
            "capture coverage 실패 수가 실제 capture와 다릅니다.",
        )
        verified_captures += len(captures)

    _require(len(observed_model_ids) == 1,
             "seed block 사이의 model digest가 일치하지 않습니다.")
    _require(len(observed_server_versions) == 1,
             "seed block 사이의 Ollama server version이 일치하지 않습니다.")
    _require(verified_captures == plan["planned_execution_count"],
             "전체 capture 수가 run plan과 다릅니다.")
    return {**preflight, "verified_capture_count": verified_captures}


def _build_parser():
    parser = argparse.ArgumentParser(
        description="근거 세탁 실험의 frozen preflight와 raw capture를 검증합니다."
    )
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument(
        "--capture-root",
        type=Path,
        default=None,
        help="생략하면 모델을 호출하지 않고 preflight만 검증합니다.",
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        result = (
            verify_preflight(args.case_root)
            if args.capture_root is None
            else verify_captures(args.capture_root, args.case_root)
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"evidence laundering 검증 실패: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
