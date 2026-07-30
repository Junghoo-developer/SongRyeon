"""Versioned JSON fixtures를 기존 결정론적 평가기에 연결한다.

이 모듈은 모델, 네트워크, 실제 ``memory/memory.jsonl``을 전혀 호출하지
않는다. 라이브 실행은 별도 과정에서 ``RecordedRun`` JSON으로 정규화하고,
이 runner는 고정 manifest와 그 파일만 검증하고 채점한다.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

from agent_tools import FileToolbox

from .evaluator import evaluate_runs
from .schema import EvaluationCase, ExecutionFact, RecordedRun
from .summary import compare_systems


EVALS_DIRECTORY = Path(__file__).resolve().parent
PROJECT_DIRECTORY = EVALS_DIRECTORY.parent
DEFAULT_MANIFEST_PATH = EVALS_DIRECTORY / "cases" / "manifest.json"
DEFAULT_FIXTURE_RUNS_PATH = (
    EVALS_DIRECTORY / "cases" / "offline_fixture_runs.json"
)
DEFAULT_REPORT_PATH = Path(".tmp") / "evals" / "fixture_report.json"
SCHEMA_VERSION = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_SECRET_KEY_PARTS = (
    "api_key",
    "authorization",
    "password",
    "secret",
    "token",
)


def _sha256_bytes(content):
    return hashlib.sha256(content).hexdigest()


def _canonical_json_sha256(value):
    """JSON 공백·키 순서·줄바꿈과 무관한 내용 digest를 만든다."""

    canonical = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def _portable_text_sha256(path):
    """Git checkout의 LF/CRLF 차이를 제거한 UTF-8 source digest."""

    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("source fixture는 UTF-8 텍스트여야 합니다.") from error
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return _sha256_bytes(normalized.encode("utf-8"))


def _read_json(path, label):
    resolved = Path(path).resolve(strict=True)

    if not resolved.is_file():
        raise ValueError(f"{label}는 JSON 파일이어야 합니다.")

    raw_content = resolved.read_bytes()
    try:
        value = json.loads(
            raw_content.decode("utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {constant}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}는 유효한 UTF-8 JSON이어야 합니다.") from error

    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위 값은 JSON 객체여야 합니다.")

    return resolved, raw_content, value


def _require_keys(value, required, allowed, label):
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)

    if missing:
        raise ValueError(f"{label}에 필수 필드가 없습니다: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{label}에 알 수 없는 필드가 있습니다: {', '.join(unknown)}")


def _nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}는 비어 있지 않은 문자열이어야 합니다.")
    return value


def _sha256(value, label):
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{label}는 소문자 SHA-256 문자열이어야 합니다.")
    return value


def _fact_from_json(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}는 JSON 객체여야 합니다.")
    _require_keys(
        value,
        {"name", "value"},
        {"name", "value"},
        label,
    )
    return ExecutionFact(
        name=_nonempty_string(value["name"], f"{label}.name"),
        value=_nonempty_string(value["value"], f"{label}.value"),
    )


def _tuple_from_json(values, builder, label):
    if not isinstance(values, list):
        raise ValueError(f"{label}는 JSON 배열이어야 합니다.")
    return tuple(
        builder(value, f"{label}[{index}]")
        for index, value in enumerate(values)
    )


def _string_tuple(values, label):
    return _tuple_from_json(
        values,
        lambda value, item_label: _nonempty_string(value, item_label),
        label,
    )


def _resolve_portable_path(base_directory, relative_path, label):
    value = _nonempty_string(relative_path, label)
    portable = PurePosixPath(value)

    if (
        portable.is_absolute()
        or value != portable.as_posix()
        or any(part in {"", ".", ".."} for part in portable.parts)
    ):
        raise ValueError(f"{label}는 상위 이동 없는 POSIX 상대경로여야 합니다.")

    root = Path(base_directory).resolve(strict=True)
    candidate = (root / Path(*portable.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}가 fixture 폴더 밖을 가리킵니다.") from error
    return candidate


def _validate_no_secret_fields(value, label):
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in _SECRET_KEY_PARTS):
                raise ValueError(f"{label}에는 비밀정보 필드를 저장할 수 없습니다.")
            _validate_no_secret_fields(nested, f"{label}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_no_secret_fields(nested, f"{label}[{index}]")


@dataclass(frozen=True)
class SourceFixture:
    """Manifest에 고정된 합성 소스 파일과 검증된 digest."""

    path: str
    sha256: str

    def to_dict(self):
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class BenchmarkManifest:
    """평가 case와 합성 프로젝트를 하나의 digest로 식별한다."""

    path: Path
    manifest_id: str
    case_set_status: str
    title: str
    project_fixture_root: Path
    cases: tuple[EvaluationCase, ...]
    questions: MappingProxyType
    fixture_inputs: MappingProxyType
    source_fixtures: tuple[SourceFixture, ...]
    boundary_fixtures: tuple[SourceFixture, ...]
    sha256: str


@dataclass(frozen=True)
class RunArtifact:
    """라이브 RecordedRun의 근거가 된 보존 원문."""

    case_id: str
    system_name: str
    path: str
    sha256: str

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "system_name": self.system_name,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class RunBundle:
    """한 manifest에 대해 정규화된 시스템별 RecordedRun 묶음."""

    path: Path
    manifest_id: str
    manifest_sha256: str
    benchmark_status: str
    review_status: str
    normalization_method: str
    disclosure: str
    systems: MappingProxyType
    runs: tuple[RecordedRun, ...]
    raw_artifacts: tuple[RunArtifact, ...]
    sha256: str


def load_manifest(path=DEFAULT_MANIFEST_PATH):
    """고정 case manifest와 모든 합성 source digest를 검증한다."""

    resolved, raw_content, document = _read_json(path, "manifest")
    required = {
        "schema_version",
        "manifest_id",
        "case_set_status",
        "title",
        "project_fixture_root",
        "source_fixtures",
        "boundary_fixtures",
        "cases",
    }
    _require_keys(document, required, required, "manifest")

    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("지원하지 않는 manifest schema_version입니다.")

    manifest_id = _nonempty_string(document["manifest_id"], "manifest_id")
    case_set_status = _nonempty_string(
        document["case_set_status"],
        "case_set_status",
    )
    title = _nonempty_string(document["title"], "title")
    project_fixture_root = _resolve_portable_path(
        resolved.parent,
        document["project_fixture_root"],
        "project_fixture_root",
    )
    if not project_fixture_root.is_dir():
        raise ValueError("project_fixture_root는 폴더여야 합니다.")

    source_values = document["source_fixtures"]
    if not isinstance(source_values, list) or not source_values:
        raise ValueError("source_fixtures에는 한 개 이상의 파일이 필요합니다.")

    source_fixtures = []
    declared_project_paths = set()
    seen_source_paths = set()
    for index, source_value in enumerate(source_values):
        label = f"source_fixtures[{index}]"
        if not isinstance(source_value, dict):
            raise ValueError(f"{label}는 JSON 객체여야 합니다.")
        _require_keys(
            source_value,
            {"path", "sha256"},
            {"path", "sha256"},
            label,
        )
        relative_path = _nonempty_string(
            source_value["path"],
            f"{label}.path",
        )
        expected_sha256 = _sha256(
            source_value["sha256"],
            f"{label}.sha256",
        )
        if relative_path in seen_source_paths:
            raise ValueError(f"중복 source fixture 경로입니다: {relative_path}")
        seen_source_paths.add(relative_path)
        source_path = _resolve_portable_path(
            resolved.parent,
            relative_path,
            f"{label}.path",
        )
        try:
            source_path.relative_to(project_fixture_root)
        except ValueError as error:
            raise ValueError(
                f"source fixture가 project_fixture_root 밖에 있습니다: "
                f"{relative_path}"
            ) from error
        if not source_path.is_file():
            raise ValueError(f"source fixture가 파일이 아닙니다: {relative_path}")
        declared_project_paths.add(
            source_path.relative_to(project_fixture_root).as_posix()
        )
        actual_sha256 = _portable_text_sha256(source_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(f"source fixture SHA-256이 다릅니다: {relative_path}")
        source_fixtures.append(
            SourceFixture(path=relative_path, sha256=expected_sha256)
        )

    actual_project_paths = set(
        FileToolbox(
            allowed_root=project_fixture_root,
        ).list_python_files()
    )
    if actual_project_paths != declared_project_paths:
        missing_from_manifest = sorted(
            actual_project_paths - declared_project_paths
        )
        missing_from_project = sorted(
            declared_project_paths - actual_project_paths
        )
        raise ValueError(
            "project fixture Python 파일 집합이 manifest와 다릅니다. "
            f"manifest 누락={missing_from_manifest}, "
            f"project 누락={missing_from_project}"
        )

    boundary_values = document["boundary_fixtures"]
    if not isinstance(boundary_values, list) or not boundary_values:
        raise ValueError("boundary_fixtures에는 한 개 이상의 파일이 필요합니다.")

    boundary_fixtures = []
    seen_boundary_paths = set()
    for index, boundary_value in enumerate(boundary_values):
        label = f"boundary_fixtures[{index}]"
        if not isinstance(boundary_value, dict):
            raise ValueError(f"{label}는 JSON 객체여야 합니다.")
        _require_keys(
            boundary_value,
            {"path", "sha256"},
            {"path", "sha256"},
            label,
        )
        relative_path = _nonempty_string(
            boundary_value["path"],
            f"{label}.path",
        )
        expected_sha256 = _sha256(
            boundary_value["sha256"],
            f"{label}.sha256",
        )
        if relative_path in seen_boundary_paths:
            raise ValueError(f"중복 boundary fixture 경로입니다: {relative_path}")
        seen_boundary_paths.add(relative_path)
        boundary_path = _resolve_portable_path(
            resolved.parent,
            relative_path,
            f"{label}.path",
        )
        try:
            boundary_path.relative_to(project_fixture_root)
        except ValueError:
            pass
        else:
            raise ValueError(
                f"boundary fixture는 project_fixture_root 밖에 있어야 합니다: "
                f"{relative_path}"
            )
        if not boundary_path.is_file():
            raise ValueError(f"boundary fixture가 파일이 아닙니다: {relative_path}")
        actual_sha256 = _portable_text_sha256(boundary_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"boundary fixture SHA-256이 다릅니다: {relative_path}"
            )
        boundary_fixtures.append(
            SourceFixture(path=relative_path, sha256=expected_sha256)
        )

    case_values = document["cases"]
    if not isinstance(case_values, list) or not case_values:
        raise ValueError("cases에는 한 개 이상의 case가 필요합니다.")

    cases = []
    questions = {}
    fixture_inputs = {}
    for index, case_value in enumerate(case_values):
        label = f"cases[{index}]"
        if not isinstance(case_value, dict):
            raise ValueError(f"{label}는 JSON 객체여야 합니다.")
        case_keys = {
            "case_id",
            "question",
            "fixture_input",
            "expected_a_facts",
            "supported_code_claims",
            "tags",
        }
        _require_keys(case_value, case_keys, case_keys, label)
        if not isinstance(case_value["fixture_input"], dict):
            raise ValueError(f"{label}.fixture_input은 JSON 객체여야 합니다.")
        _validate_no_secret_fields(
            case_value["fixture_input"],
            f"{label}.fixture_input",
        )
        case_id = _nonempty_string(case_value["case_id"], f"{label}.case_id")
        if case_id in questions:
            raise ValueError(f"중복 case_id입니다: {case_id}")
        question = _nonempty_string(case_value["question"], f"{label}.question")
        questions[case_id] = question
        fixture_inputs[case_id] = json.loads(
            json.dumps(
                case_value["fixture_input"],
                allow_nan=False,
                ensure_ascii=False,
            )
        )
        cases.append(
            EvaluationCase(
                case_id=case_id,
                expected_a_facts=_tuple_from_json(
                    case_value["expected_a_facts"],
                    _fact_from_json,
                    f"{label}.expected_a_facts",
                ),
                supported_code_claims=_string_tuple(
                    case_value["supported_code_claims"],
                    f"{label}.supported_code_claims",
                ),
                tags=_string_tuple(case_value["tags"], f"{label}.tags"),
            )
        )

    return BenchmarkManifest(
        path=resolved,
        manifest_id=manifest_id,
        case_set_status=case_set_status,
        title=title,
        project_fixture_root=project_fixture_root,
        cases=tuple(cases),
        questions=MappingProxyType(questions),
        fixture_inputs=MappingProxyType(fixture_inputs),
        source_fixtures=tuple(source_fixtures),
        boundary_fixtures=tuple(boundary_fixtures),
        sha256=_canonical_json_sha256(document),
    )


def _validate_systems(value):
    if not isinstance(value, dict) or not value:
        raise ValueError("systems에는 한 개 이상의 시스템 메타정보가 필요합니다.")

    frozen = {}
    for name, metadata in value.items():
        system_name = _nonempty_string(name, "systems key")
        if not isinstance(metadata, dict):
            raise ValueError(f"systems.{system_name}은 JSON 객체여야 합니다.")
        required = {
            "execution_profile",
            "model_provider",
            "model_name",
            "model_id",
            "configuration",
        }
        _require_keys(
            metadata,
            required,
            required,
            f"systems.{system_name}",
        )
        for key in required - {"configuration"}:
            _nonempty_string(
                metadata[key],
                f"systems.{system_name}.{key}",
            )
        if not isinstance(metadata["configuration"], dict):
            raise ValueError(
                f"systems.{system_name}.configuration은 JSON 객체여야 합니다."
            )
        if "external_api" in metadata["execution_profile"].lower():
            raise ValueError("외부 API 실행 프로필은 이 benchmark에서 금지됩니다.")
        _validate_no_secret_fields(metadata, f"systems.{system_name}")
        # JSON 왕복으로 호출자가 나중에 원본 dict를 바꾸지 못하게 복사한다.
        frozen[system_name] = json.loads(
            json.dumps(metadata, allow_nan=False, ensure_ascii=False)
        )
    return frozen


def _artifact_from_json(value, *, bundle_path, case_id, system_name):
    label = f"runs[{system_name}/{case_id}].raw_artifact"
    if not isinstance(value, dict):
        raise ValueError(f"{label}는 JSON 객체여야 합니다.")
    _require_keys(value, {"path", "sha256"}, {"path", "sha256"}, label)
    relative_path = _nonempty_string(value["path"], f"{label}.path")
    expected_sha256 = _sha256(value["sha256"], f"{label}.sha256")
    artifact_path = _resolve_portable_path(
        bundle_path.parent,
        relative_path,
        f"{label}.path",
    )
    default_memory = (PROJECT_DIRECTORY / "memory" / "memory.jsonl").resolve()
    if artifact_path == default_memory:
        raise ValueError("실제 memory/memory.jsonl은 평가 원문으로 사용할 수 없습니다.")
    if not artifact_path.is_file():
        raise ValueError(f"{label}.path는 파일이어야 합니다.")
    if _sha256_bytes(artifact_path.read_bytes()) != expected_sha256:
        raise ValueError(f"{label} SHA-256이 다릅니다.")
    return RunArtifact(
        case_id=case_id,
        system_name=system_name,
        path=relative_path,
        sha256=expected_sha256,
    )


def load_run_bundle(path, manifest):
    """정규화된 fixture/live run 묶음을 읽고 provenance를 검증한다."""

    if not isinstance(manifest, BenchmarkManifest):
        raise TypeError("manifest는 BenchmarkManifest여야 합니다.")

    resolved, raw_content, document = _read_json(path, "run bundle")
    required = {
        "schema_version",
        "manifest_id",
        "manifest_sha256",
        "benchmark_status",
        "review_status",
        "normalization_method",
        "disclosure",
        "uses_external_api",
        "systems",
        "runs",
    }
    _require_keys(document, required, required, "run bundle")

    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("지원하지 않는 run bundle schema_version입니다.")
    if document["manifest_id"] != manifest.manifest_id:
        raise ValueError("run bundle의 manifest_id가 다릅니다.")
    manifest_sha256 = _sha256(
        document["manifest_sha256"],
        "manifest_sha256",
    )
    if manifest_sha256 != manifest.sha256:
        raise ValueError("run bundle의 manifest_sha256이 현재 manifest와 다릅니다.")

    benchmark_status = document["benchmark_status"]
    if benchmark_status not in {"fixture", "live"}:
        raise ValueError("benchmark_status는 fixture 또는 live여야 합니다.")
    review_status = document["review_status"]
    valid_review_status = (
        {"fixture"} if benchmark_status == "fixture" else {"draft", "reviewed"}
    )
    if review_status not in valid_review_status:
        raise ValueError("benchmark_status와 review_status 조합이 올바르지 않습니다.")
    normalization_method = _nonempty_string(
        document["normalization_method"],
        "normalization_method",
    )
    disclosure = _nonempty_string(document["disclosure"], "disclosure")
    if document["uses_external_api"] is not False:
        raise ValueError("외부 API 실행 결과는 이 benchmark에서 금지됩니다.")
    systems = _validate_systems(document["systems"])

    run_values = document["runs"]
    if not isinstance(run_values, list) or not run_values:
        raise ValueError("runs에는 한 개 이상의 실행 결과가 필요합니다.")
    runs = []
    artifacts = []
    for index, run_value in enumerate(run_values):
        label = f"runs[{index}]"
        if not isinstance(run_value, dict):
            raise ValueError(f"{label}는 JSON 객체여야 합니다.")
        required_run_keys = {
            "case_id",
            "system_name",
            "reported_a_facts",
            "code_claims",
            "completed",
            "tool_call_count",
            "latency_ms",
            "extra_metrics",
        }
        allowed_run_keys = required_run_keys | {"raw_artifact"}
        _require_keys(
            run_value,
            required_run_keys,
            allowed_run_keys,
            label,
        )
        case_id = _nonempty_string(run_value["case_id"], f"{label}.case_id")
        system_name = _nonempty_string(
            run_value["system_name"],
            f"{label}.system_name",
        )
        if system_name not in systems:
            raise ValueError(f"정의되지 않은 system_name입니다: {system_name}")
        if not isinstance(run_value["extra_metrics"], dict):
            raise ValueError(f"{label}.extra_metrics는 JSON 객체여야 합니다.")
        _validate_no_secret_fields(
            run_value["extra_metrics"],
            f"{label}.extra_metrics",
        )
        runs.append(
            RecordedRun(
                case_id=case_id,
                system_name=system_name,
                reported_a_facts=_tuple_from_json(
                    run_value["reported_a_facts"],
                    _fact_from_json,
                    f"{label}.reported_a_facts",
                ),
                code_claims=_string_tuple(
                    run_value["code_claims"],
                    f"{label}.code_claims",
                ),
                completed=run_value["completed"],
                tool_call_count=run_value["tool_call_count"],
                latency_ms=run_value["latency_ms"],
                extra_metrics=run_value["extra_metrics"],
            )
        )
        raw_artifact = run_value.get("raw_artifact")
        if benchmark_status == "live" and raw_artifact is None:
            raise ValueError("live run에는 raw_artifact가 반드시 필요합니다.")
        if benchmark_status == "fixture" and raw_artifact is not None:
            raise ValueError("fixture run에는 측정 원문 raw_artifact를 넣지 않습니다.")
        if raw_artifact is not None:
            artifacts.append(
                _artifact_from_json(
                    raw_artifact,
                    bundle_path=resolved,
                    case_id=case_id,
                    system_name=system_name,
                )
            )

    return RunBundle(
        path=resolved,
        manifest_id=manifest.manifest_id,
        manifest_sha256=manifest_sha256,
        benchmark_status=benchmark_status,
        review_status=review_status,
        normalization_method=normalization_method,
        disclosure=disclosure,
        systems=MappingProxyType(systems),
        runs=tuple(runs),
        raw_artifacts=tuple(artifacts),
        sha256=_canonical_json_sha256(document),
    )


def build_report(manifest, run_bundle):
    """완전한 case×system 행렬을 확인하고 안정적인 JSON 보고서를 만든다."""

    if not isinstance(manifest, BenchmarkManifest):
        raise TypeError("manifest는 BenchmarkManifest여야 합니다.")
    if not isinstance(run_bundle, RunBundle):
        raise TypeError("run_bundle은 RunBundle이어야 합니다.")
    if run_bundle.manifest_id != manifest.manifest_id:
        raise ValueError("manifest와 run bundle이 서로 다릅니다.")

    case_ids = {case.case_id for case in manifest.cases}
    system_names = set(run_bundle.systems)
    expected_pairs = {
        (system_name, case_id)
        for system_name in system_names
        for case_id in case_ids
    }
    actual_pairs = [
        (run.system_name, run.case_id)
        for run in run_bundle.runs
    ]
    if len(actual_pairs) != len(set(actual_pairs)):
        raise ValueError("같은 system_name과 case_id 실행이 중복됐습니다.")
    actual_pair_set = set(actual_pairs)
    unknown = sorted(actual_pair_set - expected_pairs)
    missing = sorted(expected_pairs - actual_pair_set)
    if unknown:
        raise ValueError(f"manifest에 없는 실행 조합이 있습니다: {unknown}")
    if missing:
        raise ValueError(f"누락된 실행 조합이 있습니다: {missing}")

    results = evaluate_runs(manifest.cases, run_bundle.runs)
    summaries = compare_systems(results)
    # reviewer identity/version, 정규화 coverage와 claim span 검증 계약이
    # 아직 없으므로 문자열 하나만으로 공개 가능 상태로 승격하지 않는다.
    publishable = False
    if run_bundle.benchmark_status == "fixture":
        warning = (
            "FIXTURE ONLY: 합성 계약 fixture의 결정론적 출력이며 "
            "측정된 모델 성능이 아닙니다."
        )
    elif run_bundle.review_status == "draft":
        warning = (
            "LIVE DRAFT: 원시 실행은 존재하지만 정규화 검토가 끝나지 않아 "
            "공개 성능 수치로 사용할 수 없습니다."
        )
    else:
        warning = (
            "REVIEWED NORMALIZATION, NON-PUBLISHABLE: reviewer/version, "
            "normalization coverage와 claim span의 기계 검증이 아직 없습니다."
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_status": run_bundle.benchmark_status,
        "review_status": run_bundle.review_status,
        "publishable": publishable,
        "publication_validation": {
            "raw_case_system_linkage_verified": (
                run_bundle.benchmark_status == "live"
            ),
            "reviewer_identity_and_version_verified": False,
            "normalization_coverage_verified": False,
            "claim_spans_verified": False,
        },
        "warning": warning,
        "disclosure": run_bundle.disclosure,
        "provenance": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "run_bundle_sha256": run_bundle.sha256,
            "case_set_status": manifest.case_set_status,
            "normalization_method": run_bundle.normalization_method,
            "uses_external_api": False,
            "source_fixtures": [
                source.to_dict()
                for source in manifest.source_fixtures
            ],
            "boundary_fixtures": [
                source.to_dict()
                for source in manifest.boundary_fixtures
            ],
            "raw_artifacts": [
                artifact.to_dict()
                for artifact in run_bundle.raw_artifacts
            ],
        },
        "coverage": {
            "case_count": len(manifest.cases),
            "system_count": len(run_bundle.systems),
            "recorded_run_count": len(run_bundle.runs),
            "complete_case_system_matrix": True,
        },
        "systems": dict(run_bundle.systems),
        "summaries": {
            name: summary.to_dict()
            for name, summary in summaries.items()
        },
        "results": [result.to_dict() for result in results],
    }


def write_report(report, output_path, *, forbidden_paths=()):
    """보고서를 안정적인 UTF-8 JSON으로 지정 경로에 기록한다."""

    path = Path(output_path)
    resolved = path.resolve()
    default_memory = (PROJECT_DIRECTORY / "memory" / "memory.jsonl").resolve()
    if resolved == default_memory:
        raise ValueError("실제 memory/memory.jsonl에는 평가 보고서를 쓸 수 없습니다.")
    forbidden = {
        Path(forbidden_path).resolve()
        for forbidden_path in forbidden_paths
    }
    if resolved in forbidden:
        raise ValueError(
            "평가 보고서는 manifest, run bundle 또는 raw artifact를 "
            "덮어쓸 수 없습니다."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        report,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(serialized + "\n", encoding="utf-8", newline="\n")
    return path


def run_evaluation(
    manifest_path=DEFAULT_MANIFEST_PATH,
    runs_path=DEFAULT_FIXTURE_RUNS_PATH,
    output_path=None,
):
    """파일 로드, provenance 검증, 평가, 선택적 저장을 한 번에 수행한다."""

    manifest = load_manifest(manifest_path)
    run_bundle = load_run_bundle(runs_path, manifest)
    report = build_report(manifest, run_bundle)
    if output_path is not None:
        forbidden_paths = [
            manifest.path,
            run_bundle.path,
            *(
                run_bundle.path.parent / artifact.path
                for artifact in run_bundle.raw_artifacts
            ),
        ]
        write_report(
            report,
            output_path,
            forbidden_paths=forbidden_paths,
        )
    return report
