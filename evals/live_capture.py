"""고정 평가 case를 로컬 Ollama로 실행하고 원시 증거만 보존한다.

이 모듈은 자연어 답변의 정답이나 코드 주장을 자동 판정하지 않는다.
출력은 언제나 ``live/draft/non-publishable`` 원시 capture이며, 이후 사람이
원문을 확인해 별도의 ``RecordedRun`` bundle로 정규화해야 한다.
"""

import argparse
import hashlib
import ipaddress
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from agent_tools import FileToolbox
from demo.cli import DEMO_MAX_PYTHON_FILE_BYTES
from llm import ModelCallError, OllamaClient
from llm.client import (
    DEFAULT_BASE_URL,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_NUM_CTX,
    DEFAULT_SEED,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
)
from memory import (
    append_information_records,
    save_final_delivery,
    save_node3_answer,
    save_user_input,
)
from runtime import run_demo_turn

from .runner import (
    DEFAULT_MANIFEST_PATH,
    PROJECT_DIRECTORY,
    SCHEMA_VERSION,
    load_manifest,
)
from .variants import (
    EVAL_NODE4_BYPASS_METRIC,
    SINGLE_TOOL_AGENT,
    SONGRYEON_FULL,
    SONGRYEON_NO_NODE4,
    SUPPORTED_VARIANTS,
    NoNode4EvalClient,
    run_single_tool_agent_turn,
)


DEFAULT_ARCHITECTURE_BACKBONE = "qwen3:14b"
DEFAULT_ARCHITECTURE_VARIANTS = SUPPORTED_VARIANTS
DEFAULT_CAPTURE_ROOT = Path(".tmp") / "evals" / "local_captures"
CAPTURE_FILENAME = "capture.json"
CHECKPOINT_FILENAME = "checkpoint.json"
EVAL_MAX_PYTHON_FILE_BYTES = DEMO_MAX_PYTHON_FILE_BYTES
_SAFE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9._-]+")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class EvalWallClockLimitError(TimeoutError):
    """한 case에 공통 적용한 eval wall-clock 예산을 소진했다."""


class _DeadlineClient:
    """모델 호출 사이에 공통 case deadline을 강제하는 얇은 adapter."""

    def __init__(self, client, *, deadline_ns, clock_ns):
        self._client = client
        self._deadline_ns = deadline_ns
        self._clock_ns = clock_ns
        for attribute in (
            "base_url",
            "model_name",
            "timeout_seconds",
            "num_ctx",
            "keep_alive",
            "temperature",
            "seed",
            "provider",
            "execution_mode",
        ):
            setattr(self, attribute, getattr(client, attribute))

    def _timeout_targets(self):
        targets = []
        current = self._client
        seen = set()
        while id(current) not in seen:
            seen.add(id(current))
            if hasattr(current, "timeout_seconds"):
                targets.append(current)
            current = getattr(current, "_client", None)
            if current is None:
                break
        return targets

    def complete(self, **kwargs):
        remaining_ns = self._deadline_ns - self._clock_ns()
        if remaining_ns <= 0:
            raise EvalWallClockLimitError(
                "eval case의 wall-clock 한도를 소진했습니다."
            )
        remaining_seconds = max(
            1,
            math.ceil(remaining_ns / 1_000_000_000),
        )
        originals = []
        for target in self._timeout_targets():
            original = target.timeout_seconds
            originals.append((target, original))
            target.timeout_seconds = min(original, remaining_seconds)
        try:
            return self._client.complete(**kwargs)
        finally:
            for target, original in originals:
                target.timeout_seconds = original


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _project_fixture_identity(manifest):
    payload = json.dumps(
        sorted(
            (
                source.to_dict()
                for source in manifest.source_fixtures
            ),
            key=lambda source: source["path"],
        ),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "manifest_relative_path": (
            manifest.project_fixture_root.relative_to(
                manifest.path.parent
            ).as_posix()
        ),
        "tree_sha256": _sha256(payload),
        "python_file_count": len(manifest.source_fixtures),
    }


def _json_copy(value):
    return json.loads(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
        )
    )


def _safe_name(value):
    safe = _SAFE_NAME_PATTERN.sub("-", value).strip("-._").lower()
    if not safe:
        raise ValueError("파일 이름으로 바꿀 수 없는 식별자입니다.")
    return safe


def _require_loopback_ollama_url(base_url):
    """대회 비교 capture가 외부 API 호스트로 향하지 않게 한다."""

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url은 비어 있지 않은 문자열이어야 합니다.")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("base_url은 유효한 HTTP(S) URL이어야 합니다.")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("base_url에는 계정정보, query 또는 fragment를 넣을 수 없습니다.")

    hostname = parsed.hostname.lower()
    if hostname == "localhost":
        return base_url.rstrip("/")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError as error:
        raise ValueError(
            "live capture는 로컬 loopback Ollama만 사용할 수 있습니다."
        ) from error
    if not address.is_loopback:
        raise ValueError(
            "live capture는 로컬 loopback Ollama만 사용할 수 있습니다."
        )
    return base_url.rstrip("/")


def _validate_model_names(model_names):
    names = tuple(model_names)
    if not names:
        raise ValueError("한 개 이상의 로컬 Ollama 모델이 필요합니다.")
    for name in names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("모델 이름은 비어 있지 않은 문자열이어야 합니다.")
    if len(set(names)) != len(names):
        raise ValueError("같은 모델을 비교 목록에 중복할 수 없습니다.")
    return names


def _validate_variants(variants):
    values = tuple(variants)
    if not values:
        raise ValueError("한 개 이상의 eval variant가 필요합니다.")
    unknown = sorted(set(values) - set(SUPPORTED_VARIANTS))
    if unknown:
        raise ValueError(f"지원하지 않는 eval variant입니다: {unknown}")
    if len(set(values)) != len(values):
        raise ValueError("eval variant를 중복할 수 없습니다.")
    return values


def _prepare_output_directory(output_dir, now):
    if output_dir is None:
        timestamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = (
            DEFAULT_CAPTURE_ROOT
            / f"{timestamp}-{uuid4().hex[:8]}"
        )

    path = Path(output_dir)
    resolved = path.resolve()
    actual_memory_directory = (PROJECT_DIRECTORY / "memory").resolve()
    if (
        resolved == actual_memory_directory
        or actual_memory_directory in resolved.parents
    ):
        raise ValueError("실제 memory 폴더에는 평가 capture를 쓸 수 없습니다.")
    if path.exists() and not path.is_dir():
        raise ValueError("capture 출력 경로는 폴더여야 합니다.")
    if path.exists() and any(path.iterdir()):
        raise ValueError("capture 출력 폴더는 없거나 비어 있어야 합니다.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fixture_record(
    *,
    information,
    information_class,
    information_type,
    turn_id,
    information_id,
    sequence,
):
    if information_class not in {"absolute", "relative"}:
        raise ValueError("fixture memory 분류는 absolute 또는 relative여야 합니다.")
    return {
        "information": information,
        "information_class": information_class,
        "code_verifiable": information_class == "absolute",
        "information_type": information_type,
        "turn_id": turn_id,
        "information_id": information_id,
        "created_at": (
            f"2000-01-01T00:00:{sequence:02d}+00:00"
        ),
    }


def _seed_memory_records(fixture_input, memory_path, case_id):
    records = fixture_input.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("memory_records fixture에는 records가 필요합니다.")

    completed = []
    seen_ids = set()
    for index, value in enumerate(records, start=1):
        if not isinstance(value, dict) or set(value) != {
            "record_id",
            "information_class",
            "information",
        }:
            raise ValueError("memory_records 항목 형식이 올바르지 않습니다.")
        record_id = value["record_id"]
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError("fixture record_id는 비어 있지 않아야 합니다.")
        if record_id in seen_ids:
            raise ValueError("fixture record_id가 중복됐습니다.")
        seen_ids.add(record_id)
        information = value["information"]
        if not isinstance(information, str) or not information.strip():
            raise ValueError("fixture information은 비어 있지 않아야 합니다.")
        completed.append(
            _fixture_record(
                information=information,
                information_class=value["information_class"],
                information_type="fixture_memory",
                turn_id=f"fixture-seed-{case_id}",
                information_id=record_id,
                sequence=index,
            )
        )
    append_information_records(completed, memory_path)


def _validate_conversation_turns(fixture_input):
    turns = fixture_input.get("turns")
    if not isinstance(turns, list) or not turns:
        raise ValueError("conversation fixture에는 turns가 필요합니다.")

    normalized = []
    evaluated_indices = []
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict) or set(turn) != {
            "role",
            "content",
            "evaluate",
        }:
            raise ValueError("conversation turn 형식이 올바르지 않습니다.")
        role = turn["role"]
        content = turn["content"]
        evaluate = turn["evaluate"]
        if role not in {"user", "assistant"}:
            raise ValueError("conversation role은 user 또는 assistant여야 합니다.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("conversation content는 비어 있지 않아야 합니다.")
        if not isinstance(evaluate, bool):
            raise ValueError("conversation evaluate는 bool이어야 합니다.")
        if evaluate:
            evaluated_indices.append(index)
        normalized.append(
            {
                "role": role,
                "content": content,
                "evaluate": evaluate,
            }
        )

    if evaluated_indices != [len(normalized) - 1]:
        raise ValueError(
            "conversation의 마지막 turn 하나만 평가 대상으로 표시해야 합니다."
        )
    if normalized[-1]["role"] != "user":
        raise ValueError("conversation 평가 대상은 마지막 사용자 요청이어야 합니다.")
    return normalized


def _replay_conversation_prefix(turns, memory_path, case_id):
    """평가 대상 직전까지의 고정 대화를 원본 기억 형식으로 재생한다."""

    for index, turn in enumerate(turns[:-1]):
        turn_id = f"fixture-conversation-{case_id}-{index + 1}"
        if turn["role"] == "user":
            save_user_input(
                turn["content"],
                turn_id,
                memory_path,
            )
            continue

        answer_records = save_node3_answer(
            turn["content"],
            f"{turn_id}-node3",
            memory_path,
        )
        answer_record = next(
            record
            for record in answer_records
            if record["information_type"] == "node3_answer"
        )
        save_final_delivery(
            answer_record["information_id"],
            f"{turn_id}-final",
            memory_path,
        )


def _prepare_case_input(manifest, case, memory_path):
    fixture_input = _json_copy(manifest.fixture_inputs[case.case_id])
    kind = fixture_input.get("kind")

    if kind in {"memory_records", "project_and_memory"}:
        _seed_memory_records(fixture_input, memory_path, case.case_id)
    elif kind == "conversation":
        turns = _validate_conversation_turns(fixture_input)
        _replay_conversation_prefix(
            turns,
            memory_path,
            case.case_id,
        )
        return {
            "manifest_question": manifest.questions[case.case_id],
            "evaluated_question": turns[-1]["content"],
            "evaluated_turn_index": len(turns) - 1,
            "conversation_turns": turns,
        }
    elif kind not in {"none", "project"}:
        raise ValueError(f"지원하지 않는 fixture_input kind입니다: {kind}")

    question = manifest.questions[case.case_id]
    return {
        "manifest_question": question,
        "evaluated_question": question,
        "evaluated_turn_index": 0,
        "conversation_turns": [
            {
                "role": "user",
                "content": question,
                "evaluate": True,
            }
        ],
    }


def _read_memory_events(memory_path):
    if not memory_path.exists():
        return [], None

    events = []
    try:
        with memory_path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError(
                        f"{line_number}번 memory event가 객체가 아닙니다."
                    )
                events.append(event)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        return events, {
            "type": type(error).__name__,
            "message": "raw memory JSONL을 끝까지 해석하지 못했습니다.",
        }
    return events, None


def _model_metric_totals(events):
    totals = Counter()
    for event in events:
        if event.get("information_type") != "model_raw_metrics":
            continue
        try:
            metrics = json.loads(event["information"])
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if not isinstance(metrics, dict):
            continue
        for name, value in metrics.items():
            if (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
            ):
                totals[name] += value
    return dict(sorted(totals.items()))


def _event_counts(events):
    counts = Counter(
        event.get("information_type", "<missing>")
        for event in events
    )
    return dict(sorted(counts.items()))


def _safe_error(error, hidden_paths):
    message = str(error).replace("\r", " ").replace("\n", " ").strip()
    for hidden_path in hidden_paths:
        message = message.replace(str(Path(hidden_path).resolve()), "<path>")
    return {
        "type": type(error).__name__,
        "message": message[:500] or "실행 오류",
    }


def _partial_counts(events):
    event_types = Counter(
        event.get("information_type")
        for event in events
    )
    model_status_turn_ids = {
        event.get("turn_id")
        for event in events
        if event.get("information_type") == "model_raw_status"
    }
    bypass_turn_ids = set()
    tool_limit_forced_count = 0
    for event in events:
        if event.get("information_type") == "eval_single_tool_limit":
            tool_limit_forced_count += 1
            continue
        if event.get("information_type") == "runtime_route":
            try:
                route = json.loads(event["information"])
            except (KeyError, TypeError, json.JSONDecodeError):
                route = None
            if (
                isinstance(route, dict)
                and route.get("forced_by_tool_limit") is True
            ):
                tool_limit_forced_count += 1
            continue
        if event.get("information_type") != "model_raw_metrics":
            continue
        try:
            metrics = json.loads(event["information"])
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
        if (
            isinstance(metrics, dict)
            and metrics.get(EVAL_NODE4_BYPASS_METRIC) == 1
        ):
            bypass_turn_ids.add(event.get("turn_id"))

    return {
        "model_exchange_count": event_types["model_raw_status"],
        "model_call_count": len(model_status_turn_ids - bypass_turn_ids),
        "eval_bypass_count": len(model_status_turn_ids & bypass_turn_ids),
        "tool_call_count": event_types["tool_raw_name"],
        "tool_limit_forced_count": tool_limit_forced_count,
    }


def _copy_raw_memory(memory_path, output_dir, system_name, case_id):
    relative_path = (
        Path("raw")
        / _safe_name(system_name)
        / f"{_safe_name(case_id)}.memory.jsonl"
    )
    destination = output_dir / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    if memory_path.exists():
        shutil.copyfile(memory_path, destination)
    else:
        destination.write_bytes(b"")
    raw_content = destination.read_bytes()
    return {
        "path": relative_path.as_posix(),
        "sha256": _sha256(raw_content),
        "byte_count": len(raw_content),
        "format": "songryeon-memory-jsonl",
    }


def _capture_case(
    *,
    manifest,
    case,
    client,
    toolbox,
    output_dir,
    system_name,
    run_turn,
    case_wall_clock_limit_seconds,
    budget_clock_ns,
    perf_counter_ns,
    on_progress,
):
    with tempfile.TemporaryDirectory(
        prefix=f"songryeon-eval-{_safe_name(case.case_id)}-",
        dir=output_dir,
    ) as temporary_directory:
        memory_path = Path(temporary_directory) / "memory.jsonl"
        prepared = _prepare_case_input(
            manifest,
            case,
            memory_path,
        )
        if on_progress is not None:
            on_progress(
                f"{system_name}/{case.case_id}: "
                f"{prepared['evaluated_question']}"
            )

        budget_started_ns = budget_clock_ns()
        deadline_ns = budget_started_ns + (
            case_wall_clock_limit_seconds * 1_000_000_000
        )
        deadline_client = _DeadlineClient(
            client,
            deadline_ns=deadline_ns,
            clock_ns=budget_clock_ns,
        )
        result = None
        error_value = None
        started = perf_counter_ns()
        try:
            result = run_turn(
                prepared["evaluated_question"],
                client=deadline_client,
                toolbox=toolbox,
                memory_path=memory_path,
                on_event=(
                    None
                    if on_progress is None
                    else lambda node, message: on_progress(
                        f"{system_name}/{case.case_id}/{node}: {message}"
                    )
                ),
            )
        except Exception as error:  # 실패 case도 raw capture에 반드시 남긴다.
            error_value = _safe_error(
                error,
                (temporary_directory, manifest.project_fixture_root),
            )
        elapsed_ns = perf_counter_ns() - started
        if elapsed_ns < 0:
            raise RuntimeError("perf_counter_ns가 역행했습니다.")
        wall_clock_limit_exhausted = (
            budget_clock_ns() >= deadline_ns
            or (
                error_value is not None
                and error_value["type"] == "EvalWallClockLimitError"
            )
        )
        if wall_clock_limit_exhausted and error_value is None:
            error_value = {
                "type": "EvalWallClockLimitError",
                "message": "eval case의 wall-clock 한도를 소진했습니다.",
            }

        events, memory_parse_error = _read_memory_events(memory_path)
        artifact = _copy_raw_memory(
            memory_path,
            output_dir,
            system_name,
            case.case_id,
        )
        artifact["event_count"] = len(events)
        artifact["information_type_counts"] = _event_counts(events)
        if memory_parse_error is not None:
            artifact["parse_error"] = memory_parse_error

        partial = _partial_counts(events)
        capture = {
            "case_id": case.case_id,
            "system_name": system_name,
            **prepared,
            "answer": None if result is None else result.answer,
            "completed": (
                result is not None
                and error_value is None
                and not wall_clock_limit_exhausted
            ),
            "latency_ms": elapsed_ns / 1_000_000,
            "wall_clock_limit_seconds": case_wall_clock_limit_seconds,
            "wall_clock_limit_exhausted": wall_clock_limit_exhausted,
            "error": error_value,
            "turn_id": None if result is None else result.turn_id,
            "tool_call_count": (
                partial["tool_call_count"]
                if result is None
                else result.total_tool_calls
            ),
            "model_call_count": partial["model_call_count"],
            "model_exchange_count": partial["model_exchange_count"],
            "eval_bypass_count": partial["eval_bypass_count"],
            "tool_call_limit_reached": (
                partial["tool_limit_forced_count"] > 0
            ),
            "tool_limit_forced_count": (
                partial["tool_limit_forced_count"]
            ),
            "node1_rounds": None if result is None else result.node1_rounds,
            "node2_rejections": (
                None if result is None else result.node2_rejections
            ),
            "node3_drafts": None if result is None else result.node3_drafts,
            "node4_rejections": (
                None if result is None else result.node4_rejections
            ),
            "node2_limit_exhausted": (
                None if result is None else result.node2_limit_exhausted
            ),
            "node4_limit_exhausted": (
                None if result is None else result.node4_limit_exhausted
            ),
            "final_outcome": (
                None if result is None else result.final_outcome
            ),
            "model_metric_totals": _model_metric_totals(events),
            "raw_memory_artifact": artifact,
        }
        return capture


def _client_metadata(
    client,
    ready,
    system_name,
    *,
    variant,
    backbone,
    comparison_group,
    system_wrapper,
    node4_mode,
    runtime_contract,
):
    provider = getattr(client, "provider", None)
    execution_mode = getattr(client, "execution_mode", None)
    if provider != "ollama":
        raise ValueError("live capture는 Ollama client만 허용합니다.")
    if (
        not isinstance(execution_mode, str)
        or "external_api" in execution_mode.lower()
    ):
        raise ValueError("외부 API 실행 모드는 live capture에서 금지됩니다.")
    digest = ready.get("model_digest")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise ValueError("Ollama model digest가 유효하지 않습니다.")
    if ready.get("model_name") != client.model_name:
        raise ValueError("Ollama 준비 응답의 모델 이름이 요청과 다릅니다.")
    server_version = ready.get("server_version")
    if not isinstance(server_version, str) or not server_version:
        raise ValueError("Ollama server version이 유효하지 않습니다.")

    return {
        "system_name": system_name,
        "system_wrapper": system_wrapper,
        "variant": variant,
        "backbone": backbone,
        "comparison_group": comparison_group,
        "node4_mode": node4_mode,
        "runtime_contract": _json_copy(runtime_contract),
        "provider": "ollama",
        "execution_profile": execution_mode,
        "model_tag": client.model_name,
        "model_id": digest,
        "server_version": server_version,
        "configuration": {
            "base_url": client.base_url,
            "num_ctx": client.num_ctx,
            "timeout_seconds": client.timeout_seconds,
            "keep_alive": client.keep_alive,
            "temperature": client.temperature,
            "seed": client.seed,
        },
    }


def _write_json_atomic(document, path):
    serialized = json.dumps(
        document,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    temporary_path = path.with_name(path.name + ".tmp")
    temporary_path.write_text(
        serialized + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary_path, path)
    return path


def _write_capture(document, output_dir):
    return _write_json_atomic(
        document,
        output_dir / CAPTURE_FILENAME,
    )


def _write_checkpoint(
    *,
    output_dir,
    checkpoint_status,
    captured_at,
    manifest,
    systems,
    captures,
):
    document = {
        "schema_version": SCHEMA_VERSION,
        "capture_status": "live_raw_draft",
        "checkpoint_status": checkpoint_status,
        "review_status": "draft",
        "publishable": False,
        "uses_external_api": False,
        "captured_at": captured_at.astimezone(timezone.utc).isoformat(),
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "case_set_status": manifest.case_set_status,
            "case_count": len(manifest.cases),
        },
        "project_fixture": _project_fixture_identity(manifest),
        "systems": systems,
        "planned_pair_count": len(systems) * len(manifest.cases),
        "captured_pair_count": len(captures),
        "captures": captures,
    }
    return _write_json_atomic(
        document,
        output_dir / CHECKPOINT_FILENAME,
    )


def capture_local_comparison(
    *,
    manifest_path=DEFAULT_MANIFEST_PATH,
    variants=DEFAULT_ARCHITECTURE_VARIANTS,
    architecture_backbone=DEFAULT_ARCHITECTURE_BACKBONE,
    backbone_compare_models=(),
    base_url=DEFAULT_BASE_URL,
    num_ctx=DEFAULT_NUM_CTX,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    keep_alive=DEFAULT_KEEP_ALIVE,
    temperature=DEFAULT_TEMPERATURE,
    seed=DEFAULT_SEED,
    case_wall_clock_limit_seconds=600,
    output_dir=None,
    client_factory=OllamaClient,
    perf_counter_ns=time.perf_counter_ns,
    budget_clock_ns=time.monotonic_ns,
    now_factory=lambda: datetime.now(timezone.utc),
    on_progress=None,
):
    """동일 조건으로 로컬 모델들을 실행하고 채점 전 raw capture를 만든다."""

    manifest = load_manifest(manifest_path)
    selected_variants = _validate_variants(variants)
    architecture_model = _validate_model_names(
        (architecture_backbone,)
    )[0]
    comparison_models = _validate_model_names(
        backbone_compare_models
    ) if backbone_compare_models else ()
    local_base_url = _require_loopback_ollama_url(base_url)
    if (
        not isinstance(case_wall_clock_limit_seconds, int)
        or isinstance(case_wall_clock_limit_seconds, bool)
        or case_wall_clock_limit_seconds < 1
    ):
        raise ValueError("case wall-clock 한도는 1 이상의 정수여야 합니다.")
    systems_to_run = []
    system_names = set()

    def prepare_system(
        *,
        variant,
        backbone,
        comparison_group,
        system_name,
        system_wrapper,
        node4_mode,
        run_turn,
        runtime_contract,
        bypass_node4=False,
    ):
        base_client = client_factory(
            base_url=local_base_url,
            model_name=backbone,
            timeout_seconds=timeout_seconds,
            num_ctx=num_ctx,
            keep_alive=keep_alive,
            temperature=temperature,
            seed=seed,
        )
        client = (
            NoNode4EvalClient(base_client)
            if bypass_node4
            else base_client
        )
        ready = client.check_ready()
        if system_name in system_names:
            raise ValueError("평가 system_name이 충돌했습니다.")
        system_names.add(system_name)
        systems_to_run.append(
            (
                client,
                system_name,
                _client_metadata(
                    client,
                    ready,
                    system_name,
                    variant=variant,
                    backbone=backbone,
                    comparison_group=comparison_group,
                    system_wrapper=system_wrapper,
                    node4_mode=node4_mode,
                    runtime_contract=runtime_contract,
                ),
                run_turn,
            )
        )

    variant_contracts = {
        SINGLE_TOOL_AGENT: {
            "system_wrapper": "eval_single_tool_agent",
            "node4_mode": "absent",
            "run_turn": run_single_tool_agent_turn,
            "bypass_node4": False,
            "runtime_contract": {
                "maximum_tool_calls_per_case": 3,
                "initial_memory_view_characters": 8000,
                "file_toolbox_max_python_file_bytes": (
                    EVAL_MAX_PYTHON_FILE_BYTES
                ),
                "tool_evidence_policy": "raw history in single-agent prompt",
                "num_predict": {
                    "action": 1024,
                    "answer": 2048,
                },
                "node2": "absent",
                "node4": "absent",
            },
        },
        SONGRYEON_NO_NODE4: {
            "system_wrapper": "songryeon_eval_no_node4",
            "node4_mode": "eval_only_deterministic_bypass",
            "run_turn": run_demo_turn,
            "bypass_node4": True,
            "runtime_contract": {
                "maximum_tool_calls_per_case": 12,
                "maximum_tool_calls_per_node1_round": 3,
                "initial_memory_view_characters": 8000,
                "file_toolbox_max_python_file_bytes": (
                    EVAL_MAX_PYTHON_FILE_BYTES
                ),
                "tool_evidence_policy": "SongRyeon retention, max 2000 chars each",
                "num_predict": {
                    "node1": 1024,
                    "node2": 256,
                    "node3": 2048,
                    "node4_bypass": 0,
                },
                "node2": "active, max 3 rejections",
                "node4": "eval-only deterministic pass-through",
            },
        },
        SONGRYEON_FULL: {
            "system_wrapper": "songryeon",
            "node4_mode": "active",
            "run_turn": run_demo_turn,
            "bypass_node4": False,
            "runtime_contract": {
                "maximum_tool_calls_per_case": 12,
                "maximum_tool_calls_per_node1_round": 3,
                "initial_memory_view_characters": 8000,
                "file_toolbox_max_python_file_bytes": (
                    EVAL_MAX_PYTHON_FILE_BYTES
                ),
                "tool_evidence_policy": "SongRyeon retention, max 2000 chars each",
                "num_predict": {
                    "node1": 1024,
                    "node2": 256,
                    "node3": 2048,
                    "node4": 256,
                },
                "node2": "active, max 3 rejections",
                "node4": "active, max 3 rejections",
            },
        },
    }
    for variant in selected_variants:
        contract = variant_contracts[variant]
        prepare_system(
            variant=variant,
            backbone=architecture_model,
            comparison_group="architecture_same_backbone",
            system_name=f"{variant}-{_safe_name(architecture_model)}",
            **contract,
        )

    for model_name in comparison_models:
        prepare_system(
            variant=SONGRYEON_FULL,
            backbone=model_name,
            comparison_group="backbone_full_songryeon",
            system_name=(
                f"backbone-{SONGRYEON_FULL}-{_safe_name(model_name)}"
            ),
            **variant_contracts[SONGRYEON_FULL],
        )

    captured_at = now_factory()
    if not isinstance(captured_at, datetime):
        raise TypeError("now_factory는 datetime을 반환해야 합니다.")
    capture_directory = _prepare_output_directory(output_dir, captured_at)
    captures = []
    systems = [
        metadata
        for _, _, metadata, _ in systems_to_run
    ]
    _write_checkpoint(
        output_dir=capture_directory,
        checkpoint_status="in_progress",
        captured_at=captured_at,
        manifest=manifest,
        systems=systems,
        captures=captures,
    )
    for client, system_name, metadata, run_turn in systems_to_run:
        for case in manifest.cases:
            # Toolbox 인스턴스도 case마다 새로 만들어 상태 공유를 제거한다.
            toolbox = FileToolbox(
                allowed_root=manifest.project_fixture_root,
                max_file_bytes=EVAL_MAX_PYTHON_FILE_BYTES,
            )
            captures.append(
                _capture_case(
                    manifest=manifest,
                    case=case,
                    client=client,
                    toolbox=toolbox,
                    output_dir=capture_directory,
                    system_name=system_name,
                    run_turn=run_turn,
                    case_wall_clock_limit_seconds=(
                        case_wall_clock_limit_seconds
                    ),
                    budget_clock_ns=budget_clock_ns,
                    perf_counter_ns=perf_counter_ns,
                    on_progress=on_progress,
                )
            )
            _write_checkpoint(
                output_dir=capture_directory,
                checkpoint_status="in_progress",
                captured_at=captured_at,
                manifest=manifest,
                systems=systems,
                captures=captures,
            )

    document = {
        "schema_version": SCHEMA_VERSION,
        "capture_status": "live_raw_draft",
        "review_status": "draft",
        "publishable": False,
        "warning": (
            "LIVE RAW DRAFT ONLY: 답변 정답과 코드 주장을 아직 "
            "정규화·검토하지 않았으므로 성능 수치로 공개할 수 없습니다."
        ),
        "uses_external_api": False,
        "captured_at": captured_at.astimezone(timezone.utc).isoformat(),
        "manifest": {
            "manifest_id": manifest.manifest_id,
            "manifest_sha256": manifest.sha256,
            "case_set_status": manifest.case_set_status,
            "case_count": len(manifest.cases),
        },
        "conditions": {
            "case_memory_isolated": True,
            "actual_memory_used": False,
            "project_fixture": _project_fixture_identity(manifest),
            "file_toolbox_max_python_file_bytes": (
                EVAL_MAX_PYTHON_FILE_BYTES
            ),
            "same_model_generation_configuration": True,
            "same_case_wall_clock_limit_seconds": (
                case_wall_clock_limit_seconds
            ),
            "automatic_answer_grading": False,
            "architecture_backbone": architecture_model,
            "architecture_variants": list(selected_variants),
            "architecture_comparison_complete": (
                set(selected_variants) == set(SUPPORTED_VARIANTS)
            ),
            "backbone_comparison_models": list(comparison_models),
            "bare_model_baseline_included": False,
            "structural_effect_claim_allowed": False,
        },
        "comparison_groups": {
            "architecture_same_backbone": {
                "backbone": architecture_model,
                "variants": list(selected_variants),
            },
            "backbone_full_songryeon": {
                "backbones": list(comparison_models),
                "variant": SONGRYEON_FULL,
            },
        },
        "systems": systems,
        "coverage": {
            "system_count": len(systems),
            "unique_backbone_count": len(
                {system["backbone"] for system in systems}
            ),
            "case_count": len(manifest.cases),
            "capture_count": len(captures),
            "complete_case_system_matrix": (
                len(captures) == len(systems) * len(manifest.cases)
            ),
            "completed_capture_count": sum(
                capture["completed"]
                for capture in captures
            ),
            "failed_capture_count": sum(
                not capture["completed"]
                for capture in captures
            ),
        },
        "captures": captures,
    }
    capture_path = _write_capture(document, capture_directory)
    _write_checkpoint(
        output_dir=capture_directory,
        checkpoint_status="complete",
        captured_at=captured_at,
        manifest=manifest,
        systems=systems,
        captures=captures,
    )

    return capture_path, document


def _build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "고정 10개 case를 같은 로컬 backbone의 eval variant들로 실행하고 "
            "선택적으로 full SongRyeon backbone 비교 raw capture를 보존합니다."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=SUPPORTED_VARIANTS,
        default=list(DEFAULT_ARCHITECTURE_VARIANTS),
        help="같은 backbone에서 비교할 eval variant",
    )
    parser.add_argument(
        "--architecture-backbone",
        default=DEFAULT_ARCHITECTURE_BACKBONE,
        help="구조 비교 세 variant가 공통으로 사용할 Ollama 모델",
    )
    parser.add_argument(
        "--backbone-compare-models",
        nargs="*",
        default=[],
        help=(
            "별도 그룹에서 full SongRyeon으로 비교할 모델들 "
            "(예: gemma4:26b qwen3:14b)"
        ),
    )
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
        help="모든 system/case에 같은 누적 wall-clock 한도",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "새 capture 폴더. 생략하면 "
            ".tmp/evals/local_captures/<UTC-ID>를 만듭니다."
        ),
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        capture_path, document = capture_local_comparison(
            manifest_path=args.manifest,
            variants=args.variants,
            architecture_backbone=args.architecture_backbone,
            backbone_compare_models=args.backbone_compare_models,
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
            client_factory=OllamaClient,
            on_progress=print,
        )
    except (ModelCallError, OSError, TypeError, ValueError) as error:
        print(f"live capture 중단: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("live capture를 사용자가 중단했습니다.", file=sys.stderr)
        return 130

    print(document["warning"])
    print(
        f"{document['coverage']['capture_count']}개 raw capture 저장: "
        f"{capture_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
