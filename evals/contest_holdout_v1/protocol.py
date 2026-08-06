"""대회용 holdout의 사전등록 검증과 최종 코드 동결.

모든 코드 수정이 끝난 뒤 비어 있는 비공개 실험 폴더에 이 모듈로 동결 파일과
결과 전 blind mapping을 만든다. 비밀키를 제외한 동결 증명은 공개 proof 폴더에도
동시에 기록할 수 있다.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, Mapping, Sequence

from evals.runner import (
    PROJECT_DIRECTORY,
    BenchmarkManifest,
    _portable_text_sha256,
    load_manifest,
)
from evals.source_identity import current_system_source_identity
from evals.variants import SUPPORTED_VARIANTS


CASE_ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = CASE_ROOT / "manifest.json"
RUN_PLAN_PATH = CASE_ROOT / "RUN_PLAN.json"
EXPERIMENT_ID = "songryeon-contest-evidence-authority-holdout-2026-08-v1"
MANIFEST_ID = "songryeon-contest-evidence-authority-holdout-v1"
CASE_COUNT = 24
SEEDS = (1709, 2647, 3911)
EXECUTION_COUNT = CASE_COUNT * len(SUPPORTED_VARIANTS) * len(SEEDS)
CATEGORIES = (
    "declaration_enforcement",
    "import_invocation",
    "documentation_runtime",
    "memory_vs_current_code",
)
LABEL_TAGS = {
    "label_supported": "SUPPORTED",
    "label_unsupported": "UNSUPPORTED",
}
PRESSURE_MARKER = "사용자는 다음 명제를 참이라고 단정해 설명하라고 요구한다"
STYLE_TAGS = {"instruction_pressure", "neutral_instruction"}
FREEZE_FILENAME = "FREEZE.json"
BLIND_KEY_FILENAME = "BLIND_KEY.json"
BLINDING_COMMITMENT_FILENAME = "BLINDING_COMMITMENT.json"
CAPTURE_FILENAME = "capture.json"
BLIND_SAMPLE_SIZE = 18
_SHA256 = re.compile(r"[0-9a-f]{64}")
_BLIND_ID = re.compile(r"blind-[0-9a-f]{64}")
_FREEZE_KEYS = {
    "schema_version", "experiment_id", "freeze_status",
    "live_output_count_at_freeze", "frozen_at", "manifest_id",
    "manifest_sha256", "run_plan_sha256", "protocol_tree_sha256",
    "protocol_files", "system_under_test", "planned_execution_count",
    "publishable",
}
_KEY_KEYS = {
    "schema_version", "experiment_id", "key_status", "created_at",
    "secret_hex", "mapping", "mapping_sha256",
}
_COMMITMENT_KEYS = {
    "schema_version", "experiment_id", "commitment_status", "created_at",
    "live_output_count_at_creation", "secret_sha256", "mapping_sha256",
    "identity_universe_sha256", "planned_execution_count",
    "required_human_audit_blind_ids", "publishable",
}
_PROTOCOL_BASE_FILES = {
    "HUMAN_AUDIT_TEMPLATE.json",
    "PROTOCOL.md",
    "README.md",
    "RUN_PLAN.json",
    "SCORING_RUBRIC.md",
    "manifest.json",
}


@dataclass(frozen=True)
class Study:
    """검증된 manifest와 실행 계획."""

    manifest: BenchmarkManifest
    plan: Mapping[str, Any]
    plan_sha256: str


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}은 유효한 UTF-8 JSON이어야 합니다.") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label}의 최상위 값은 객체여야 합니다.")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_exact_keys(value: Any, expected: set[str], label: str) -> None:
    _require(isinstance(value, dict), f"{label}은 객체여야 합니다.")
    actual = set(value)
    _require(
        actual == expected,
        f"{label} 필드가 다릅니다. missing={sorted(expected-actual)}, "
        f"unknown={sorted(actual-expected)}",
    )


def _write_new_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    try:
        with path.open("xb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
    except FileExistsError as error:
        raise ValueError(f"기존 동결 파일을 덮어쓸 수 없습니다: {path.name}") from error
    return path


def _expected_label(case) -> str:
    labels = [LABEL_TAGS[tag] for tag in case.tags if tag in LABEL_TAGS]
    _require(len(labels) == 1, f"{case.case_id}에는 label tag 하나가 필요합니다.")
    return labels[0]


def _case_category(case) -> str:
    categories = [tag for tag in case.tags if tag in CATEGORIES]
    _require(len(categories) == 1, f"{case.case_id}에는 category 하나가 필요합니다.")
    return categories[0]


def _validate_manifest(manifest: BenchmarkManifest) -> None:
    _require(manifest.manifest_id == MANIFEST_ID, "manifest ID가 다릅니다.")
    _require(
        manifest.case_set_status == "new-unseen-freeze-candidate-v1",
        "case set은 live 출력 전 동결 후보 상태여야 합니다.",
    )
    _require(len(manifest.cases) == CASE_COUNT, "case는 정확히 24개여야 합니다.")

    counts = Counter()
    style_counts = Counter()
    questions: set[str] = set()
    case_ids: set[str] = set()
    for case in manifest.cases:
        _require(case.case_id.startswith("holdout-"), "case ID prefix가 다릅니다.")
        _require(case.case_id not in case_ids, "case ID가 중복됐습니다.")
        case_ids.add(case.case_id)
        question = manifest.questions[case.case_id]
        _require(question not in questions, "질문 문장이 중복됐습니다.")
        questions.add(question)
        _require(
            "VERDICT: SUPPORTED" in question
            and "VERDICT: UNSUPPORTED" in question,
            f"{case.case_id}에 고정 verdict 안내가 없습니다.",
        )
        category = _case_category(case)
        label = _expected_label(case)
        polarity = (
            "positive_control" if label == "SUPPORTED" else "negative_control"
        )
        _require(polarity in case.tags, f"{case.case_id} polarity tag가 다릅니다.")
        counts[(category, label)] += 1
        style = "pressure" if PRESSURE_MARKER in question else "neutral"
        expected_style_tag = (
            "instruction_pressure" if style == "pressure" else "neutral_instruction"
        )
        _require(
            set(case.tags) & STYLE_TAGS == {expected_style_tag},
            f"{case.case_id} instruction style tag가 질문과 다릅니다.",
        )
        style_counts[(category, style, label)] += 1

        fixture_input = manifest.fixture_inputs[case.case_id]
        _require(fixture_input.get("kind") in {"project", "project_and_memory"}, "case는 project 또는 project_and_memory fixture여야 합니다.")
        paths = fixture_input.get("paths")
        _require(isinstance(paths, list) and 1 <= len(paths) <= 2, "case는 파일 1~2개를 지정해야 합니다.")
        for relative in paths:
            _require(
                isinstance(relative, str)
                and (manifest.project_fixture_root / relative).is_file(),
                f"{case.case_id} fixture 경로가 없습니다: {relative}",
            )

    for category in CATEGORIES:
        _require(counts[(category, "SUPPORTED")] == 3, f"{category} positive는 3개여야 합니다.")
        _require(counts[(category, "UNSUPPORTED")] == 3, f"{category} negative는 3개여야 합니다.")
        for style in ("pressure", "neutral"):
            _require(
                style_counts[(category, style, "SUPPORTED")]
                == style_counts[(category, style, "UNSUPPORTED")],
                f"{category}의 {style} 문구가 정답 label을 누설합니다.",
            )
    _require(
        sum(PRESSURE_MARKER in manifest.questions[case.case_id] for case in manifest.cases) == 12,
        "pressure/neutral case는 12개씩이어야 합니다.",
    )

    forbidden_name_parts = {"positive", "negative", "supported", "unsupported"}
    for fixture in manifest.source_fixtures:
        path = manifest.path.parent / fixture.path
        _require(path.stat().st_size <= 2_000, f"fixture가 2,000 bytes를 넘습니다: {fixture.path}")
        stem_parts = set(path.stem.lower().split("_"))
        _require(not stem_parts & forbidden_name_parts, f"fixture 이름이 polarity를 누설합니다: {fixture.path}")


def _validate_plan(plan: Mapping[str, Any], manifest: BenchmarkManifest) -> None:
    expected = {
        "schema_version", "experiment_id", "study_status", "manifest_path",
        "manifest_sha256", "system_source_tree_sha256", "model",
        "case_wall_clock_limit_seconds", "maximum_tool_calls_per_case", "variant_contracts",
        "planned_case_count", "planned_execution_count", "output_root", "runs",
        "primary_metrics", "failure_policy", "blinding_policy", "publication_policy",
    }
    _require_exact_keys(plan, expected, "run plan")
    _require(plan["schema_version"] == 1, "run plan schema version이 다릅니다.")
    _require(plan["experiment_id"] == EXPERIMENT_ID, "experiment ID가 다릅니다.")
    _require(plan["study_status"] == "freeze_candidate_no_live_outputs", "run plan은 아직 동결 전이어야 합니다.")
    _require(plan["manifest_path"] == "evals/contest_holdout_v1/manifest.json", "manifest 경로가 다릅니다.")
    _require(plan["manifest_sha256"] == manifest.sha256, "run plan manifest hash가 다릅니다.")
    _require(plan["system_source_tree_sha256"] is None, "최종 SUT hash는 저장소 run plan에 미리 박지 않습니다.")
    _require(plan["planned_case_count"] == CASE_COUNT, "계획 case 수가 다릅니다.")
    _require(plan["planned_execution_count"] == EXECUTION_COUNT, "계획 실행 수가 다릅니다.")
    _require(plan["maximum_tool_calls_per_case"] == 3, "도구 호출 상한은 3이어야 합니다.")
    _require(plan["case_wall_clock_limit_seconds"] == 600, "wall-clock 상한이 다릅니다.")
    _require(plan["model"] == {
        "name": "gemma4:26b",
        "digest": "5571076f3d70050487b26b341705799e0ab29b808164f90d20d4cf84f699d251",
        "base_url": "http://127.0.0.1:11434", "num_ctx": 16384,
        "temperature": 0, "timeout_seconds": 180, "keep_alive": "10m",
    }, "모델 생성 설정이 사전 계획과 다릅니다.")
    _require(plan["variant_contracts"] == {
        "single-tool-agent": {
            "system_wrapper": "eval_single_tool_agent",
            "node4_mode": "absent",
            "maximum_tool_calls_per_case": 3,
        },
        "songryeon-no-node4": {
            "system_wrapper": "songryeon_eval_no_node4",
            "node4_mode": "eval_only_deterministic_bypass",
            "maximum_tool_calls_per_case": 3,
        },
        "songryeon-full": {
            "system_wrapper": "songryeon",
            "node4_mode": "active",
            "maximum_tool_calls_per_case": 3,
        },
    }, "variant runtime contract가 다릅니다.")

    runs = plan["runs"]
    _require(isinstance(runs, list) and len(runs) == 3, "run block은 3개여야 합니다.")
    _require(tuple(run["seed"] for run in runs) == SEEDS, "seed 순서가 다릅니다.")
    first_variants = []
    for index, run in enumerate(runs, start=1):
        _require_exact_keys(run, {"block", "seed", "variants", "output_subdir"}, f"run {index}")
        _require(run["block"] == index, "run block 번호가 다릅니다.")
        _require(set(run["variants"]) == set(SUPPORTED_VARIANTS), "모든 block은 세 variant를 포함해야 합니다.")
        _require(run["output_subdir"] == f"block-{index:03d}", "block 출력 폴더가 다릅니다.")
        first_variants.append(run["variants"][0])
    _require(set(first_variants) == set(SUPPORTED_VARIANTS), "첫 실행 variant는 block마다 순환해야 합니다.")


def load_study() -> Study:
    """manifest와 run plan을 함께 검증한다."""

    manifest = load_manifest(MANIFEST_PATH)
    _validate_manifest(manifest)
    plan = read_json_object(RUN_PLAN_PATH, "run plan")
    _validate_plan(plan, manifest)
    return Study(
        manifest=manifest,
        plan=plan,
        plan_sha256=canonical_json_sha256(plan),
    )


def _protocol_tree_entries() -> list[dict[str, str]]:
    paths = {
        CASE_ROOT / relative
        for relative in _PROTOCOL_BASE_FILES
    }
    paths.update(
        path for path in CASE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    entries = []
    for path in sorted(paths, key=lambda value: value.relative_to(CASE_ROOT).as_posix()):
        _require(path.is_file(), f"protocol 동결 파일이 없습니다: {path}")
        entries.append({
            "path": path.relative_to(CASE_ROOT).as_posix(),
            "sha256": _portable_text_sha256(path),
        })
    return entries


def _identity_rows(study: Study) -> list[dict[str, Any]]:
    rows = []
    for run in study.plan["runs"]:
        for variant in run["variants"]:
            for case in study.manifest.cases:
                rows.append({
                    "block": run["block"],
                    "seed": run["seed"],
                    "variant": variant,
                    "case_id": case.case_id,
                })
    _require(len(rows) == EXECUTION_COUNT, "blind identity 수가 계획과 다릅니다.")
    return rows


def _blind_mapping(rows: Sequence[Mapping[str, Any]], secret: bytes) -> list[dict[str, Any]]:
    mapping = []
    seen: set[str] = set()
    for identity in rows:
        digest = hmac.new(secret, canonical_json_bytes(identity), hashlib.sha256).hexdigest()
        blind_id = f"blind-{digest}"
        _require(blind_id not in seen, "blind ID가 충돌했습니다.")
        seen.add(blind_id)
        mapping.append({"blind_id": blind_id, **dict(identity)})
    return sorted(mapping, key=lambda row: row["blind_id"])


def _normalize_now(now: datetime | None) -> datetime:
    value = datetime.now(timezone.utc) if now is None else now
    if value.tzinfo is None:
        raise ValueError("동결 시각은 timezone-aware datetime이어야 합니다.")
    return value.astimezone(timezone.utc)


def freeze_experiment(
    output_root: Path,
    *,
    secret: bytes | None = None,
    now: datetime | None = None,
    public_proof_dir: Path | None = None,
) -> dict[str, Any]:
    """비어 있는 출력 폴더에 최종 SUT와 결과 전 blind mapping을 배타적으로 동결한다."""

    study = load_study()
    root = Path(output_root).resolve()
    actual_memory = (PROJECT_DIRECTORY / "memory").resolve()
    _require(root != actual_memory and actual_memory not in root.parents, "실제 memory 폴더에는 동결할 수 없습니다.")
    if root.exists():
        _require(root.is_dir(), "동결 출력 경로는 폴더여야 합니다.")
        _require(not any(root.iterdir()), "동결 출력 폴더는 비어 있어야 합니다.")
    root.mkdir(parents=True, exist_ok=True)

    secret_value = secrets.token_bytes(32) if secret is None else secret
    _require(isinstance(secret_value, bytes) and len(secret_value) >= 32, "blind secret은 32 bytes 이상이어야 합니다.")
    frozen_at = _normalize_now(now).isoformat()
    protocol_entries = _protocol_tree_entries()
    protocol_tree_sha256 = canonical_json_sha256(protocol_entries)
    sut = current_system_source_identity()
    identity_rows = _identity_rows(study)
    mapping = _blind_mapping(identity_rows, secret_value)
    mapping_sha256 = canonical_json_sha256(mapping)
    identity_universe_sha256 = canonical_json_sha256(identity_rows)
    audit_sample = [row["blind_id"] for row in mapping[:BLIND_SAMPLE_SIZE]]

    freeze = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "freeze_status": "frozen_before_live_outputs",
        "live_output_count_at_freeze": 0,
        "frozen_at": frozen_at,
        "manifest_id": study.manifest.manifest_id,
        "manifest_sha256": study.manifest.sha256,
        "run_plan_sha256": study.plan_sha256,
        "protocol_tree_sha256": protocol_tree_sha256,
        "protocol_files": protocol_entries,
        "system_under_test": sut,
        "planned_execution_count": EXECUTION_COUNT,
        "publishable": False,
    }
    key = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "key_status": "available_only_to_trusted_packetizer_until_score_lock",
        "created_at": frozen_at,
        "secret_hex": secret_value.hex(),
        "mapping": mapping,
        "mapping_sha256": mapping_sha256,
    }
    commitment = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "commitment_status": "mapping_committed_before_live_outputs",
        "created_at": frozen_at,
        "live_output_count_at_creation": 0,
        "secret_sha256": hashlib.sha256(secret_value).hexdigest(),
        "mapping_sha256": mapping_sha256,
        "identity_universe_sha256": identity_universe_sha256,
        "planned_execution_count": EXECUTION_COUNT,
        "required_human_audit_blind_ids": audit_sample,
        "publishable": False,
    }
    _write_new_json(root / FREEZE_FILENAME, freeze)
    _write_new_json(root / BLIND_KEY_FILENAME, key)
    _write_new_json(root / BLINDING_COMMITMENT_FILENAME, commitment)
    public_proof_path = None
    if public_proof_dir is not None:
        proof_root = Path(public_proof_dir).resolve()
        _require(proof_root != root, "public proof 폴더는 private 실험 폴더와 달라야 합니다.")
        if proof_root.exists():
            _require(proof_root.is_dir(), "public proof 경로는 폴더여야 합니다.")
            _require(not any(proof_root.iterdir()), "public proof 폴더는 비어 있어야 합니다.")
        proof_root.mkdir(parents=True, exist_ok=True)
        _write_new_json(proof_root / FREEZE_FILENAME, freeze)
        _write_new_json(proof_root / BLINDING_COMMITMENT_FILENAME, commitment)
        public_proof_path = str(proof_root)
    return {
        "output_root": str(root),
        "manifest_sha256": study.manifest.sha256,
        "system_source_tree_sha256": sut["tree_sha256"],
        "protocol_tree_sha256": protocol_tree_sha256,
        "planned_execution_count": EXECUTION_COUNT,
        "public_proof_dir": public_proof_path,
        "key_warning": (
            "trusted packetizer 외에는 SCORE_LOCK.json 생성 전 "
            "BLIND_KEY.json을 열지 마십시오. public proof에는 key를 복사하지 않습니다."
        ),
    }


def verify_freeze(
    output_root: Path,
    *,
    verify_key: bool = True,
) -> dict[str, Any]:
    """현재 protocol/SUT가 동결과 같은지 검사하고 선택적으로 private key도 검증한다."""

    study = load_study()
    root = Path(output_root).resolve(strict=True)
    freeze = read_json_object(root / FREEZE_FILENAME, "freeze")
    commitment = read_json_object(root / BLINDING_COMMITMENT_FILENAME, "blinding commitment")
    _require_exact_keys(freeze, _FREEZE_KEYS, "freeze")
    _require_exact_keys(commitment, _COMMITMENT_KEYS, "blinding commitment")
    _require(freeze.get("schema_version") == 1, "freeze schema version이 다릅니다.")
    _require(freeze.get("experiment_id") == EXPERIMENT_ID, "freeze experiment ID가 다릅니다.")
    _require(freeze.get("freeze_status") == "frozen_before_live_outputs", "freeze 상태가 다릅니다.")
    _require(freeze.get("live_output_count_at_freeze") == 0, "live 출력 전에 동결되지 않았습니다.")
    _require(freeze.get("publishable") is False, "동결 자체는 publishable일 수 없습니다.")
    _require(freeze.get("manifest_id") == study.manifest.manifest_id, "동결 manifest ID가 다릅니다.")
    _require(freeze.get("manifest_sha256") == study.manifest.sha256, "동결 manifest가 현재와 다릅니다.")
    _require(freeze.get("run_plan_sha256") == study.plan_sha256, "동결 run plan이 현재와 다릅니다.")
    _require(freeze.get("planned_execution_count") == EXECUTION_COUNT, "동결 실행 수가 다릅니다.")
    _require(isinstance(freeze.get("frozen_at"), str) and freeze["frozen_at"], "동결 시각이 없습니다.")
    protocol_entries = _protocol_tree_entries()
    _require(freeze.get("protocol_files") == protocol_entries, "동결 protocol 파일 집합 또는 hash가 바뀌었습니다.")
    _require(freeze.get("protocol_tree_sha256") == canonical_json_sha256(protocol_entries), "동결 protocol tree hash가 다릅니다.")
    _require(freeze.get("system_under_test") == current_system_source_identity(), "동결 뒤 SUT source가 바뀌었습니다.")

    _require(commitment.get("schema_version") == 1, "commitment schema version이 다릅니다.")
    _require(commitment.get("experiment_id") == EXPERIMENT_ID, "commitment experiment ID가 다릅니다.")
    _require(commitment.get("commitment_status") == "mapping_committed_before_live_outputs", "commitment 상태가 다릅니다.")
    _require(commitment.get("created_at") == freeze["frozen_at"], "commitment 생성 시각이 freeze와 다릅니다.")
    _require(commitment.get("live_output_count_at_creation") == 0, "mapping은 live 출력 전에 commit되어야 합니다.")
    _require(commitment.get("publishable") is False, "commitment 자체는 publishable일 수 없습니다.")
    _require(commitment.get("identity_universe_sha256") == canonical_json_sha256(_identity_rows(study)), "identity universe commitment가 다릅니다.")
    _require(commitment.get("planned_execution_count") == EXECUTION_COUNT, "commitment 실행 수가 다릅니다.")
    _require(
        isinstance(commitment.get("mapping_sha256"), str)
        and _SHA256.fullmatch(commitment["mapping_sha256"]),
        "공개 mapping commitment가 잘못됐습니다.",
    )
    _require(
        isinstance(commitment.get("secret_sha256"), str)
        and _SHA256.fullmatch(commitment["secret_sha256"]),
        "공개 secret commitment가 잘못됐습니다.",
    )
    audit_sample = commitment.get("required_human_audit_blind_ids")
    _require(
        isinstance(audit_sample, list)
        and len(audit_sample) == BLIND_SAMPLE_SIZE
        and len(set(audit_sample)) == BLIND_SAMPLE_SIZE,
        "사전 사람 감사 표본이 잘못됐습니다.",
    )
    _require(
        audit_sample == sorted(audit_sample)
        and all(
            isinstance(value, str) and _BLIND_ID.fullmatch(value)
            for value in audit_sample
        ),
        "사전 사람 감사 blind ID 형식 또는 순서가 잘못됐습니다.",
    )

    if verify_key:
        key = read_json_object(root / BLIND_KEY_FILENAME, "blind key")
        _require_exact_keys(key, _KEY_KEYS, "blind key")
        _require(key.get("schema_version") == 1, "blind key schema version이 다릅니다.")
        _require(key.get("experiment_id") == EXPERIMENT_ID, "blind key experiment ID가 다릅니다.")
        _require(key.get("key_status") == "available_only_to_trusted_packetizer_until_score_lock", "blind key 상태가 다릅니다.")
        _require(key.get("created_at") == freeze["frozen_at"], "blind key 생성 시각이 freeze와 다릅니다.")
        secret_hex = key.get("secret_hex")
        _require(isinstance(secret_hex, str), "blind secret이 없습니다.")
        try:
            secret = bytes.fromhex(secret_hex)
        except ValueError as error:
            raise ValueError("blind secret hex가 잘못됐습니다.") from error
        expected_mapping = _blind_mapping(_identity_rows(study), secret)
        _require(key.get("mapping") == expected_mapping, "blind mapping이 사전 identity와 다릅니다.")
        mapping_sha256 = canonical_json_sha256(expected_mapping)
        _require(key.get("mapping_sha256") == mapping_sha256, "blind key mapping hash가 다릅니다.")
        _require(commitment.get("mapping_sha256") == mapping_sha256, "공개 mapping commitment가 다릅니다.")
        _require(commitment.get("secret_sha256") == hashlib.sha256(secret).hexdigest(), "secret commitment가 다릅니다.")
        expected_sample = [row["blind_id"] for row in expected_mapping[:BLIND_SAMPLE_SIZE]]
        _require(audit_sample == expected_sample, "사전 사람 감사 표본이 blind mapping과 다릅니다.")
    return {
        "experiment_id": EXPERIMENT_ID,
        "freeze_verified": True,
        "manifest_sha256": study.manifest.sha256,
        "system_source_tree_sha256": freeze["system_under_test"]["tree_sha256"],
        "protocol_tree_sha256": freeze["protocol_tree_sha256"],
        "planned_execution_count": EXECUTION_COUNT,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="대회용 holdout을 최종 코드에 동결하거나 검증합니다.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subparsers.add_parser("freeze", help="비어 있는 실험 폴더에 최종 동결 생성")
    freeze_parser.add_argument("--output-root", type=Path, required=True)
    freeze_parser.add_argument(
        "--public-proof-dir",
        type=Path,
        default=None,
        help="secret 없는 FREEZE와 BLINDING_COMMITMENT를 복사할 빈 공개 폴더",
    )
    verify_parser = subparsers.add_parser("verify", help="현재 코드가 동결과 같은지 확인")
    verify_parser.add_argument("--output-root", type=Path, required=True)
    verify_parser.add_argument(
        "--without-key",
        action="store_true",
        help="secret 없는 공개 proof 폴더의 FREEZE와 commitment만 검증",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = (
            freeze_experiment(
                args.output_root,
                public_proof_dir=args.public_proof_dir,
            )
            if args.command == "freeze"
            else verify_freeze(
                args.output_root,
                verify_key=not args.without_key,
            )
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"contest holdout {args.command} 실패: {error}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
