"""로컬 Gemma와 Codex-account GPT의 탐색적 model-ceiling 비교.

기존 ``live_capture``의 로컬 대회 평가 경계는 그대로 둔다. 이 모듈은 공개
합성 fixture만 외부 서비스에 보내며, 결과를 구조 효과나 대회 공식 성능으로
주장하지 않는 별도 evidence pack을 만든다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import secrets
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_tools import FileToolbox
from llm import CodexAccountIntegrationClient, ModelCallError, OllamaClient
from llm.client import (
    DEFAULT_BASE_URL,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_NUM_CTX,
    DEFAULT_SEED,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)
from llm.codex_account import (
    CODEX_REASONING_EFFORTS,
    DEFAULT_CODEX_ACCOUNT_MODEL,
    DEFAULT_CODEX_REASONING_EFFORT,
)
from runtime import run_demo_turn

from .live_capture import (
    EVAL_MAX_PYTHON_FILE_BYTES,
    _capture_case,
    _prepare_output_directory,
    _project_fixture_identity,
    _safe_name,
    _write_json_atomic,
)
from .runner import PROJECT_DIRECTORY, SCHEMA_VERSION, load_manifest
from .variants import SONGRYEON_FULL


DEFAULT_MODEL_CEILING_MANIFEST = (
    Path(__file__).resolve().parent
    / "model_ceiling_cases"
    / "manifest.json"
)
DEFAULT_MODEL_SCALE_ROOT = Path(".tmp") / "evals" / "model_scale_captures"
DEFAULT_LOCAL_MODEL = "gemma4:26b"
PROTOCOL_FILENAME = "protocol.json"
BLIND_KEY_FILENAME = "blind_key.json"
CHECKPOINT_FILENAME = "checkpoint.json"
CAPTURE_FILENAME = "capture.json"
MECHANICAL_SUMMARY_FILENAME = "mechanical_summary.json"
BLIND_REVIEW_FILENAME = "blind_review.json"
REPORT_FILENAME = "REPORT.md"
ARTIFACT_MANIFEST_FILENAME = "artifact_manifest.json"
EXPERIMENT_KIND = "exploratory_external_model_ceiling"
PROTOCOL_VERSION = "model-scale-ceiling-v1"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

_RUNTIME_CONTRACT = {
    "system_wrapper": "songryeon-full",
    "maximum_tool_calls_per_case": 12,
    "maximum_tool_calls_per_node1_round": 3,
    "initial_memory_view_characters": 8000,
    "file_toolbox_max_python_file_bytes": EVAL_MAX_PYTHON_FILE_BYTES,
    "tool_evidence_policy": "SongRyeon retention, max 2000 chars each",
    "num_predict": {
        "node1": 1024,
        "node2": 768,
        "node3": 2048,
        "node4": 768,
    },
    "node2": "active review with max 3 rejections",
    "node4": "active review with max 3 rejections",
}

_SOURCE_SCOPES = (
    "agent_tools",
    "demo",
    "evals",
    "llm",
    "memory",
    "nodes",
    "prompts",
    "runtime",
    "tests",
)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_sha256(value) -> str:
    return _sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _relative_artifact(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _write_text_atomic(text: str, path: Path) -> Path:
    temporary_path = path.with_name(path.name + ".tmp")
    temporary_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary_path, path)
    return path


def _source_snapshot(project_directory=PROJECT_DIRECTORY):
    """실행 코드가 dirty여도 정확한 파일별 hash로 상태를 고정한다."""

    root = Path(project_directory).resolve()
    selected = set()
    for scope_name in _SOURCE_SCOPES:
        scope = root / scope_name
        if not scope.is_dir():
            continue
        for pattern in ("*.py", "*.json"):
            for path in scope.rglob(pattern):
                if "__pycache__" not in path.parts and path.is_file():
                    selected.add(path.resolve())
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        selected.add(pyproject.resolve())

    files = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path.read_bytes()),
            "byte_count": path.stat().st_size,
        }
        for path in sorted(selected, key=lambda value: value.as_posix())
    ]
    return {
        "algorithm": "sha256(raw-bytes)",
        "file_count": len(files),
        "tree_sha256": _canonical_sha256(files),
        "files": files,
    }


def _run_metadata_command(arguments):
    try:
        completed = subprocess.run(
            arguments,
            cwd=PROJECT_DIRECTORY,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _git_identity():
    commit = _run_metadata_command(["git", "rev-parse", "HEAD"])
    status = _run_metadata_command(
        [
            "git",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            *_SOURCE_SCOPES,
            "pyproject.toml",
        ]
    )
    status_lines = [] if status is None else status.splitlines()
    return {
        "commit": commit or "unavailable",
        "dirty": bool(status_lines),
        "status_paths": status_lines,
        "source_snapshot_is_authoritative": True,
    }


def _gpu_identity():
    output = _run_metadata_command(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    if output is None:
        return []
    devices = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        devices.append(
            {
                "name": parts[0],
                "driver_version": parts[1],
                "memory_total_mib": parts[2],
            }
        )
    return devices


def _environment_identity():
    return {
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable_name": Path(sys.executable).name,
        },
        "processor": platform.processor() or "unavailable",
        "gpus": _gpu_identity(),
    }


def _local_system_metadata(client, ready):
    digest = ready.get("model_digest")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError("Ollama model digest가 유효하지 않습니다.")
    if ready.get("model_name") != client.model_name:
        raise ValueError("Ollama 준비 응답의 모델 이름이 요청과 다릅니다.")
    return {
        "system_name": (
            f"songryeon-full-local-{_safe_name(client.model_name)}"
        ),
        "system_wrapper": SONGRYEON_FULL,
        "comparison_role": "contest_local_reference",
        "provider": client.provider,
        "execution_profile": client.execution_mode,
        "model_name": client.model_name,
        "model_digest": digest,
        "model_digest_available": True,
        "server_version": ready.get("server_version"),
        "uses_external_service": False,
        "authentication": "none",
        "configuration": {
            "base_url": client.base_url,
            "num_ctx": client.num_ctx,
            "timeout_seconds": client.timeout_seconds,
            "keep_alive": client.keep_alive,
            "temperature": client.temperature,
            "seed": client.seed,
        },
        "runtime_contract": _RUNTIME_CONTRACT,
    }


def _account_system_metadata(client, ready):
    if ready.get("model_name") != client.model_name:
        raise ValueError("Codex 계정 모델 이름이 요청과 다릅니다.")
    return {
        "system_name": (
            f"songryeon-full-account-{_safe_name(client.model_name)}"
        ),
        "system_wrapper": SONGRYEON_FULL,
        "comparison_role": "external_model_ceiling",
        "provider": client.provider,
        "execution_profile": client.execution_mode,
        "model_name": client.model_name,
        "model_digest": None,
        "model_digest_available": False,
        "sdk_version": ready.get("sdk_version"),
        "uses_external_service": True,
        "authentication": "chatgpt_account",
        "api_key_used": False,
        "contest_eligibility_claimed": False,
        "configuration": {
            "reasoning_effort": client.reasoning_effort,
            "ephemeral_thread": True,
            "sandbox": "read_only",
            "approval_mode": "deny_all",
            "codex_tools_allowed": False,
        },
        "runtime_contract": _RUNTIME_CONTRACT,
    }


def _build_schedule(manifest, repetitions, system_names):
    schedule = []
    sequence = 0
    for repetition in range(1, repetitions + 1):
        for case_index, case in enumerate(manifest.cases):
            order = list(system_names)
            if (repetition + case_index) % 2 == 0:
                order.reverse()
            for order_in_pair, system_name in enumerate(order, start=1):
                sequence += 1
                run_id = (
                    f"r{repetition:02d}-{_safe_name(case.case_id)}-"
                    f"{_safe_name(system_name)}"
                )
                schedule.append(
                    {
                        "sequence": sequence,
                        "run_id": run_id,
                        "repetition": repetition,
                        "case_id": case.case_id,
                        "system_name": system_name,
                        "order_in_case_pair": order_in_pair,
                    }
                )
    return schedule


def _build_blind_key(schedule, manifest_sha256, blind_seed):
    aliases = ["System A", "System B"]
    systems = sorted({item["system_name"] for item in schedule})
    selector = _sha256(
        f"{manifest_sha256}:{blind_seed}".encode("utf-8")
    )
    if int(selector[-1], 16) % 2:
        systems.reverse()
    system_aliases = dict(zip(systems, aliases, strict=True))
    items = []
    for item in schedule:
        review_id = _sha256(
            f"{blind_seed}:{item['run_id']}".encode("utf-8")
        )[:16]
        items.append(
            {
                "review_id": review_id,
                "run_id": item["run_id"],
                "system_name": item["system_name"],
                "blind_system_alias": system_aliases[item["system_name"]],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "warning": "블라인드 검토 완료 전에는 이 파일을 열지 마십시오.",
        "system_aliases": system_aliases,
        "items": items,
    }


def _protocol_document(
    *,
    created_at,
    manifest,
    repetitions,
    schedule,
    systems,
    blind_key_sha256,
    source_snapshot,
    case_wall_clock_limit_seconds,
):
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "experiment_kind": EXPERIMENT_KIND,
        "protocol_status": "frozen_before_first_inference",
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
        "publishable": False,
        "official_contest_score": False,
        "hypothesis": (
            "동일한 SongRyeon full wrapper와 합성 fixture에서 외부 상위 "
            "모델 통합 스택이 로컬 제출 모델보다 증거 경계 과제를 더 "
            "안정적으로 수행하는지 탐색한다."
        ),
        "primary_outcome": (
            "strict_task_success_pending_blinded_human_normalization"
        ),
        "secondary_outcomes": [
            "completion_rate",
            "transport_failure_count",
            "validation_limit_exhaustion_count",
            "tool_call_count",
            "model_call_count",
            "node2_rejection_count",
            "node4_rejection_count",
            "latency_descriptive_only",
        ],
        "allowed_claim": (
            "이 고정 합성 사례군에서 관찰된 full SongRyeon 통합 스택의 "
            "탐색적 model-ceiling 차이"
        ),
        "forbidden_claims": [
            "순수 기반 모델만의 인과 효과",
            "Node2 또는 Node4 구조 자체의 효과",
            "대회 제출 환경에서 gpt-5.6-sol 사용 가능",
            "로컬 GPU와 외부 서비스 latency의 동등 비교",
            "실제 모든 코딩 작업으로의 일반화",
        ],
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "case_set_status": manifest.case_set_status,
            "case_count": len(manifest.cases),
        },
        "project_fixture": _project_fixture_identity(manifest),
        "repetitions": repetitions,
        "planned_run_count": len(schedule),
        "schedule": schedule,
        "schedule_policy": (
            "manifest case order; each case pair alternates backend order by "
            "case index and repetition"
        ),
        "case_isolation": {
            "fresh_memory_jsonl": True,
            "fresh_file_toolbox": True,
            "actual_user_memory_used": False,
            "external_input_scope": "committed synthetic fixtures only",
        },
        "comparability": {
            "same_questions": True,
            "same_source_fixtures": True,
            "same_songryeon_wrapper": True,
            "same_runtime_contract": True,
            "backend_prompt_equivalent": False,
            "generation_parameters_equivalent": False,
            "tokenizers_equivalent": False,
            "num_predict_semantics_equivalent": False,
            "latency_comparable_as_model_quality": False,
            "codex_hidden_harness_present": True,
        },
        "case_wall_clock_limit_seconds": case_wall_clock_limit_seconds,
        "wall_clock_limitation": (
            "Codex SDK의 진행 중 단일 호출은 강제 중단하지 못하므로 한 호출이 "
            "한도를 넘긴 뒤 실패로 기록될 수 있다."
        ),
        "automatic_answer_grading": False,
        "heldout_claim_policy": (
            "이 held-out manifest의 supported_code_claims는 모두 필요한 핵심 "
            "주장으로 취급하며, 누락은 strict_task_success 실패다."
        ),
        "human_review": {
            "system_identity_blinded": True,
            "blind_key_file_sha256": blind_key_sha256,
            "minimum_recommended_reviewers": 2,
            "claim_to_source_spans_required_for_publication": True,
            "unreviewed_results_must_remain_non_publishable": True,
        },
        "systems": systems,
        "environment": _environment_identity(),
        "git": _git_identity(),
        "source_snapshot": source_snapshot,
    }


def _write_checkpoint(
    *, output_dir, protocol_sha256, schedule, captures, status
):
    document = {
        "schema_version": SCHEMA_VERSION,
        "experiment_kind": EXPERIMENT_KIND,
        "checkpoint_status": status,
        "publishable": False,
        "protocol_sha256": protocol_sha256,
        "planned_run_count": len(schedule),
        "captured_run_count": len(captures),
        "completed_run_ids": [capture["run_id"] for capture in captures],
        "captures": captures,
    }
    return _write_json_atomic(document, output_dir / CHECKPOINT_FILENAME)


def _nearest_rank(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(len(ordered) * percentile) - 1),
    )
    return ordered[index]


def _mechanical_summary(captures, systems):
    by_system = defaultdict(list)
    for capture in captures:
        by_system[capture["system_name"]].append(capture)

    summaries = {}
    for system in systems:
        name = system["system_name"]
        runs = by_system[name]
        latencies = [run["latency_ms"] for run in runs]
        completed = sum(run["completed"] for run in runs)
        summaries[name] = {
            "planned_runs": len(runs),
            "completed_runs": completed,
            "completion_rate": completed / len(runs) if runs else 0.0,
            "failed_runs": len(runs) - completed,
            "wall_clock_limit_exhaustions": sum(
                run["wall_clock_limit_exhausted"] for run in runs
            ),
            "node2_limit_exhaustions": sum(
                run["node2_limit_exhausted"] is True for run in runs
            ),
            "node4_limit_exhaustions": sum(
                run["node4_limit_exhausted"] is True for run in runs
            ),
            "total_tool_calls": sum(run["tool_call_count"] for run in runs),
            "mean_tool_calls": (
                statistics.fmean(run["tool_call_count"] for run in runs)
                if runs
                else 0.0
            ),
            "total_model_calls": sum(run["model_call_count"] for run in runs),
            "total_node2_rejections": sum(
                run["node2_rejections"] or 0 for run in runs
            ),
            "total_node4_rejections": sum(
                run["node4_rejections"] or 0 for run in runs
            ),
            "latency_ms": {
                "median": statistics.median(latencies) if latencies else None,
                "p95_nearest_rank": _nearest_rank(latencies, 0.95),
                "minimum": min(latencies) if latencies else None,
                "maximum": max(latencies) if latencies else None,
                "interpretation": "descriptive only; backends are not equivalent",
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_kind": EXPERIMENT_KIND,
        "score_status": "mechanical_metrics_only",
        "publishable": False,
        "correctness_status": "pending_blinded_human_normalization",
        "systems": summaries,
    }


def _transcript_artifact(
    *, output_dir, artifact_system_name, case_id, lines
):
    relative = (
        Path("transcripts")
        / _safe_name(artifact_system_name)
        / f"{_safe_name(case_id)}.txt"
    )
    destination = output_dir / relative
    content = "\n".join(lines).rstrip() + "\n"
    _write_text_atomic(content, destination)
    raw = destination.read_bytes()
    return {
        "path": relative.as_posix(),
        "sha256": _sha256(raw),
        "byte_count": len(raw),
        "format": "utf-8-text",
    }


def _blind_review_document(manifest, captures, blind_key, blind_key_sha256):
    key_by_run = {item["run_id"]: item for item in blind_key["items"]}
    case_by_id = {case.case_id: case for case in manifest.cases}
    items = []
    for capture in captures:
        key = key_by_run[capture["run_id"]]
        case = case_by_id[capture["case_id"]]
        items.append(
            {
                "review_id": key["review_id"],
                "blind_system_alias": key["blind_system_alias"],
                "case_id": capture["case_id"],
                "repetition": capture["repetition"],
                "question": capture["evaluated_question"],
                "expected_a_facts": [
                    fact.to_dict() for fact in case.expected_a_facts
                ],
                "supported_code_claims": list(case.supported_code_claims),
                "answer": capture["answer"],
                "completed": capture["completed"],
                "error": capture["error"],
                "raw_artifact_sha256": capture["raw_memory_artifact"][
                    "sha256"
                ],
                "review_fields": {
                    "required_a_facts_satisfied": None,
                    "required_claims_satisfied": None,
                    "unsupported_claim_count": None,
                    "forbidden_behavior_count": None,
                    "strict_task_success": None,
                    "claim_spans": [],
                    "reviewer_id": None,
                    "review_protocol_version": None,
                    "notes": None,
                },
            }
        )
    items.sort(key=lambda item: item["review_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "packet_status": "unscored_blind_review",
        "publishable": False,
        "manifest_id": manifest.manifest_id,
        "manifest_sha256": manifest.sha256,
        "blind_key_file_sha256": blind_key_sha256,
        "instructions": [
            "blind_key.json은 모든 검토를 잠근 뒤에만 연다.",
            "자유 답변의 각 코드 주장을 문자 span으로 분리한다.",
            "각 주장에 fixture 파일과 줄 근거 또는 unsupported를 기록한다.",
            "실패와 시간 초과도 strict_task_success=false로 분모에 포함한다.",
            "두 명 이상 독립 검토 후 불일치 해결 기록을 별도로 남긴다.",
        ],
        "strict_task_success_definition": (
            "completed AND required A facts satisfied AND required claims "
            "satisfied AND unsupported claims == 0 AND forbidden behaviors == 0 "
            "AND no validation limit exhausted"
        ),
        "items": items,
    }


def _report_markdown(capture_document, summary, output_dir):
    lines = [
        "# SongRyeon exploratory model-ceiling evidence pack",
        "",
        "> **NON-PUBLISHABLE EXPLORATORY RESULT.** 자유 답변의 블라인드 인간 "
        "검토가 끝나지 않았으며, 외부 Codex 계정 조건은 대회 공식 성능이 아니다.",
        "",
        "## 고정 조건",
        "",
        f"- Protocol: `{capture_document['protocol_sha256']}`",
        f"- Manifest: `{capture_document['manifest']['manifest_id']}` / "
        f"`{capture_document['manifest']['manifest_sha256']}`",
        f"- Cases: {capture_document['coverage']['case_count']}",
        f"- Repetitions: {capture_document['coverage']['repetitions']}",
        f"- Planned/completed captures: "
        f"{capture_document['coverage']['planned_run_count']}/"
        f"{capture_document['coverage']['captured_run_count']}",
        "- 입력: 저장소에 동결한 합성 Python·합성 기억만 사용",
        "- 실제 사용자 `memory.jsonl`: 사용하지 않음",
        "",
        "## 기계 관측값",
        "",
        "| System | Completed | Failed | Tool calls | Model calls | "
        "Node2 rejects | Node4 rejects | Median latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in summary["systems"].items():
        lines.append(
            f"| {name} | {values['completed_runs']}/{values['planned_runs']} | "
            f"{values['failed_runs']} | {values['total_tool_calls']} | "
            f"{values['total_model_calls']} | "
            f"{values['total_node2_rejections']} | "
            f"{values['total_node4_rejections']} | "
            f"{values['latency_ms']['median']:.1f} |"
        )
    lines.extend(
        [
            "",
            "Latency는 로컬 GPU와 외부 서비스 조건이 달라 우열 점수로 해석하지 않는다.",
            "정확도와 근거 없는 주장 수는 `blind_review.json`의 독립 검토가 "
            "완료되기 전에는 계산하지 않는다.",
            "",
            "## 실패 장부",
            "",
            "| Run | System | Case | Error | Raw SHA-256 |",
            "|---|---|---|---|---|",
        ]
    )
    failures = [
        capture for capture in capture_document["captures"]
        if not capture["completed"]
    ]
    if failures:
        for capture in failures:
            error = capture["error"] or {"type": "incomplete"}
            lines.append(
                f"| {capture['run_id']} | {capture['system_name']} | "
                f"{capture['case_id']} | {error['type']} | "
                f"`{capture['raw_memory_artifact']['sha256']}` |"
            )
    else:
        lines.append("| — | — | — | 실패 없음 | — |")
    lines.extend(
        [
            "",
            "## 해석 제한",
            "",
            "- GPT 조건은 순수 API 모델이 아니라 Codex SDK와 숨은 하네스를 포함한다.",
            "- 이 실험은 full SongRyeon의 model ceiling 탐색이며 구조 효과 실험이 아니다.",
            "- GPT 조건은 대회의 로컬 제출·시연 성능 집계에서 제외한다.",
            "- 사례 수가 작아 실제 모든 코딩 작업으로 일반화하지 않는다.",
            "- 모든 raw 로그·transcript·설정은 `artifact_manifest.json`으로 검증한다.",
            "",
            "## 검토 순서",
            "",
            "1. `blind_review.json`을 두 명 이상이 독립 검토한다.",
            "2. 검토 결과와 claim-to-source span을 잠근다.",
            "3. 그 뒤에만 `blind_key.json`을 열어 시스템 이름을 복원한다.",
            "4. `python -m evals.model_scale_verify <evidence-pack>`로 hash를 검증한다.",
        ]
    )
    return _write_text_atomic(
        "\n".join(lines).rstrip() + "\n",
        output_dir / REPORT_FILENAME,
    )


def _write_artifact_manifest(output_dir):
    entries = []
    for path in sorted(output_dir.rglob("*"), key=lambda value: value.as_posix()):
        if not path.is_file() or path.name == ARTIFACT_MANIFEST_FILENAME:
            continue
        if path.name.endswith(".tmp"):
            continue
        raw = path.read_bytes()
        entries.append(
            {
                "path": _relative_artifact(path, output_dir),
                "sha256": _sha256(raw),
                "byte_count": len(raw),
            }
        )
    document = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": "sha256(raw-bytes)",
        "artifact_count": len(entries),
        "artifacts": entries,
    }
    return _write_json_atomic(
        document,
        output_dir / ARTIFACT_MANIFEST_FILENAME,
    )


def capture_model_scale_comparison(
    *,
    manifest_path=DEFAULT_MODEL_CEILING_MANIFEST,
    local_model=DEFAULT_LOCAL_MODEL,
    account_model=DEFAULT_CODEX_ACCOUNT_MODEL,
    reasoning_effort=DEFAULT_CODEX_REASONING_EFFORT,
    repetitions=1,
    base_url=DEFAULT_BASE_URL,
    num_ctx=DEFAULT_NUM_CTX,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    keep_alive=DEFAULT_KEEP_ALIVE,
    temperature=DEFAULT_TEMPERATURE,
    seed=DEFAULT_SEED,
    case_wall_clock_limit_seconds=600,
    output_dir=None,
    local_client_factory=OllamaClient,
    account_client_factory=CodexAccountIntegrationClient,
    capture_case=_capture_case,
    perf_counter_ns=time.perf_counter_ns,
    budget_clock_ns=time.monotonic_ns,
    now_factory=lambda: datetime.now(timezone.utc),
    blind_seed=None,
    on_progress=None,
):
    """합성 held-out case를 두 full SongRyeon backend로 교차 실행한다."""

    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("repetitions는 1 이상의 정수여야 합니다.")
    if (
        type(case_wall_clock_limit_seconds) is not int
        or case_wall_clock_limit_seconds < 1
    ):
        raise ValueError("case wall-clock 한도는 1 이상의 정수여야 합니다.")
    if reasoning_effort not in CODEX_REASONING_EFFORTS:
        raise ValueError("지원하지 않는 Codex reasoning effort입니다.")

    manifest = load_manifest(manifest_path)
    created_at = now_factory()
    if not isinstance(created_at, datetime):
        raise TypeError("now_factory는 datetime을 반환해야 합니다.")
    if output_dir is None:
        timestamp = created_at.astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        output_dir = (
            DEFAULT_MODEL_SCALE_ROOT
            / f"{timestamp}-{uuid4().hex[:8]}"
        )
    capture_directory = _prepare_output_directory(output_dir, created_at)

    local_client = local_client_factory(
        base_url=base_url,
        model_name=local_model,
        timeout_seconds=timeout_seconds,
        num_ctx=num_ctx,
        keep_alive=keep_alive,
        temperature=temperature,
        seed=seed,
    )
    account_client = account_client_factory(
        model_name=account_model,
        reasoning_effort=reasoning_effort,
    )

    captures = []
    try:
        local_ready = local_client.check_ready()
        account_ready = account_client.check_configuration()
        systems = [
            _local_system_metadata(local_client, local_ready),
            _account_system_metadata(account_client, account_ready),
        ]
        system_names = [system["system_name"] for system in systems]
        schedule = _build_schedule(manifest, repetitions, system_names)
        blind_key = _build_blind_key(
            schedule,
            manifest.sha256,
            blind_seed or secrets.token_hex(32),
        )
        blind_key_path = _write_json_atomic(
            blind_key,
            capture_directory / BLIND_KEY_FILENAME,
        )
        blind_key_sha256 = _sha256(blind_key_path.read_bytes())
        source_snapshot = _source_snapshot()
        protocol = _protocol_document(
            created_at=created_at,
            manifest=manifest,
            repetitions=repetitions,
            schedule=schedule,
            systems=systems,
            blind_key_sha256=blind_key_sha256,
            source_snapshot=source_snapshot,
            case_wall_clock_limit_seconds=case_wall_clock_limit_seconds,
        )
        protocol_path = _write_json_atomic(
            protocol,
            capture_directory / PROTOCOL_FILENAME,
        )
        protocol_sha256 = _sha256(protocol_path.read_bytes())
        _write_checkpoint(
            output_dir=capture_directory,
            protocol_sha256=protocol_sha256,
            schedule=schedule,
            captures=captures,
            status="in_progress",
        )

        clients = {
            systems[0]["system_name"]: local_client,
            systems[1]["system_name"]: account_client,
        }
        case_by_id = {case.case_id: case for case in manifest.cases}
        for planned in schedule:
            system_name = planned["system_name"]
            case = case_by_id[planned["case_id"]]
            artifact_system_name = (
                f"{system_name}-r{planned['repetition']:02d}"
            )
            transcript_lines = [
                f"run_id={planned['run_id']}",
                f"system={system_name}",
                f"case={case.case_id}",
                f"repetition={planned['repetition']}",
                f"question={manifest.questions[case.case_id]}",
            ]

            def progress(message):
                transcript_lines.append(message)
                if on_progress is not None:
                    on_progress(message)

            toolbox = FileToolbox(
                allowed_root=manifest.project_fixture_root,
                max_file_bytes=EVAL_MAX_PYTHON_FILE_BYTES,
            )
            captured = capture_case(
                manifest=manifest,
                case=case,
                client=clients[system_name],
                toolbox=toolbox,
                output_dir=capture_directory,
                system_name=artifact_system_name,
                run_turn=run_demo_turn,
                case_wall_clock_limit_seconds=case_wall_clock_limit_seconds,
                budget_clock_ns=budget_clock_ns,
                perf_counter_ns=perf_counter_ns,
                on_progress=progress,
            )
            captured["run_id"] = planned["run_id"]
            captured["repetition"] = planned["repetition"]
            captured["schedule_sequence"] = planned["sequence"]
            captured["order_in_case_pair"] = planned["order_in_case_pair"]
            captured["artifact_system_name"] = artifact_system_name
            captured["system_name"] = system_name
            if captured["answer"] is not None:
                transcript_lines.extend(["", "[final_answer]", captured["answer"]])
            if captured["error"] is not None:
                transcript_lines.extend(
                    ["", "[error]", json.dumps(captured["error"], ensure_ascii=False)]
                )
            captured["transcript_artifact"] = _transcript_artifact(
                output_dir=capture_directory,
                artifact_system_name=artifact_system_name,
                case_id=case.case_id,
                lines=transcript_lines,
            )
            captures.append(captured)
            _write_checkpoint(
                output_dir=capture_directory,
                protocol_sha256=protocol_sha256,
                schedule=schedule,
                captures=captures,
                status="in_progress",
            )

        finished_at = datetime.now(timezone.utc)
        capture_document = {
            "schema_version": SCHEMA_VERSION,
            "experiment_kind": EXPERIMENT_KIND,
            "capture_status": "exploratory_raw_complete",
            "review_status": "unscored",
            "publishable": False,
            "official_contest_score": False,
            "uses_external_service": True,
            "warning": (
                "EXPLORATORY NON-PUBLISHABLE: 블라인드 인간 정규화 전 raw "
                "model-ceiling 통합 실험이며 대회 공식 성능이 아닙니다."
            ),
            "created_at": created_at.astimezone(timezone.utc).isoformat(),
            "finished_at": finished_at.isoformat(),
            "protocol_sha256": protocol_sha256,
            "blind_key_file_sha256": blind_key_sha256,
            "manifest": protocol["manifest"],
            "project_fixture": protocol["project_fixture"],
            "systems": systems,
            "comparability": protocol["comparability"],
            "schedule": schedule,
            "coverage": {
                "case_count": len(manifest.cases),
                "system_count": len(systems),
                "repetitions": repetitions,
                "planned_run_count": len(schedule),
                "captured_run_count": len(captures),
                "complete_case_system_repetition_matrix": (
                    len(captures) == len(schedule)
                ),
                "completed_run_count": sum(
                    capture["completed"] for capture in captures
                ),
                "failed_run_count": sum(
                    not capture["completed"] for capture in captures
                ),
            },
            "captures": captures,
        }
        capture_path = _write_json_atomic(
            capture_document,
            capture_directory / CAPTURE_FILENAME,
        )
        summary = _mechanical_summary(captures, systems)
        summary_path = _write_json_atomic(
            summary,
            capture_directory / MECHANICAL_SUMMARY_FILENAME,
        )
        blind_review = _blind_review_document(
            manifest,
            captures,
            blind_key,
            blind_key_sha256,
        )
        blind_review_path = _write_json_atomic(
            blind_review,
            capture_directory / BLIND_REVIEW_FILENAME,
        )
        report_path = _report_markdown(
            capture_document,
            summary,
            capture_directory,
        )
        _write_checkpoint(
            output_dir=capture_directory,
            protocol_sha256=protocol_sha256,
            schedule=schedule,
            captures=captures,
            status="complete",
        )
        artifact_manifest_path = _write_artifact_manifest(capture_directory)
    finally:
        close = getattr(account_client, "close", None)
        if callable(close):
            close()

    return {
        "output_directory": capture_directory,
        "protocol_path": protocol_path,
        "capture_path": capture_path,
        "summary_path": summary_path,
        "blind_review_path": blind_review_path,
        "blind_key_path": blind_key_path,
        "report_path": report_path,
        "artifact_manifest_path": artifact_manifest_path,
        "capture": capture_document,
        "summary": summary,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "공개 합성 held-out case로 full SongRyeon의 로컬 Gemma와 "
            "Codex-account GPT model ceiling을 별도 비교합니다."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MODEL_CEILING_MANIFEST,
    )
    parser.add_argument("--local-model", default=DEFAULT_LOCAL_MODEL)
    parser.add_argument(
        "--account-model",
        default=DEFAULT_CODEX_ACCOUNT_MODEL,
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=CODEX_REASONING_EFFORTS,
        default=DEFAULT_CODEX_REASONING_EFFORT,
    )
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument("--keep-alive", default=DEFAULT_KEEP_ALIVE)
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--case-wall-clock-limit-seconds",
        type=int,
        default=600,
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        result = capture_model_scale_comparison(
            manifest_path=args.manifest,
            local_model=args.local_model,
            account_model=args.account_model,
            reasoning_effort=args.reasoning_effort,
            repetitions=args.repetitions,
            base_url=args.base_url,
            num_ctx=args.num_ctx,
            timeout_seconds=args.timeout_seconds,
            keep_alive=args.keep_alive,
            temperature=args.temperature,
            seed=args.seed,
            case_wall_clock_limit_seconds=(
                args.case_wall_clock_limit_seconds
            ),
            output_dir=args.output_dir,
            on_progress=print,
        )
    except (ModelCallError, OSError, TypeError, ValueError) as error:
        print(f"model-scale capture 중단: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("model-scale capture를 사용자가 중단했습니다.", file=sys.stderr)
        return 130

    print(result["capture"]["warning"])
    print(f"evidence pack: {result['output_directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
