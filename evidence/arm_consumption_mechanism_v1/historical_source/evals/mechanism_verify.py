"""ARM mechanism replay capture의 raw 완전성과 동일성을 검증한다.

자연어 정답은 이 모듈에서 채점하지 않는다. 이 모듈의 범위는
30 case × 3 seed raw unit, exact evidence packet, prompt 처치 외 동일성,
reviewer의 common consumer draft, model digest/config, raw SHA-256을 다시
계산하는 것이다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from .mechanism_capture import (
    ANSWER_CONDITIONS,
    ANSWER_CONDITION_BLOCKS,
    ANSWER_NUM_PREDICT,
    ANSWER_SCHEMA,
    AR_CONSUMER_RULE,
    EXPERIMENT_ID,
    MAX_INVALID_JSON_ATTEMPTS,
    MECHANISM_SEEDS,
    REVIEWERS,
    REVIEWER_CONDITION_BLOCKS,
    REVIEW_NUM_PREDICT,
    REVIEW_SCHEMA,
    SCHEMA_VERSION,
    _derive_outputs,
    _masked_prompt_hash,
    _prompt_hash,
    balanced_answer_order,
    balanced_reviewer_order,
    build_answer_prompts,
    build_reviewer_prompts,
    validate_condition_block_lengths,
)
from .mechanism_packets import (
    DEFAULT_EVIDENCE_PLAN_PATH,
    DEFAULT_SOURCE_MANIFEST_PATH,
    validate_evidence_packet_set,
)


DEFAULT_RUN_PLAN_PATH = (
    Path(__file__).resolve().parent / "arm_mechanism_cases" / "RUN_PLAN.json"
)
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_ORACLE_MARKERS = (
    "answer_key",
    "expected_a_facts",
    "ground_truth",
    "negative_control",
    "positive_control",
    "supported_code_claims",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read_json(path, label):
    resolved = Path(path).resolve(strict=True)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label}은 유효한 UTF-8 JSON이어야 합니다.") from error
    _require(isinstance(value, dict), f"{label} 최상위 값은 객체여야 합니다.")
    return resolved, value


def _sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value):
    _require(isinstance(value, str), "SHA-256 text 입력은 문자열이어야 합니다.")
    return _sha256_bytes(value.encode("utf-8"))


def _require_sha256(value, label):
    _require(
        isinstance(value, str) and _SHA256_PATTERN.fullmatch(value),
        f"{label}은 64자 소문자 SHA-256이어야 합니다.",
    )


def _resolve_artifact(root, relative, label):
    _require(isinstance(relative, str) and relative, f"{label} 경로가 비어 있습니다.")
    relative_path = Path(relative)
    _require(not relative_path.is_absolute(), f"{label} 경로는 상대경로여야 합니다.")
    path = (root / relative_path).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label}이 capture root 밖을 가리킵니다.") from error
    _require(path.is_file(), f"{label}이 파일이 아닙니다.")
    return path


def _oracle_terms(manifest_path):
    _, manifest = _read_json(manifest_path, "source manifest")
    terms = set(_ORACLE_MARKERS)
    for case in manifest.get("cases", []):
        for claim in case.get("supported_code_claims", []):
            if isinstance(claim, str) and len(claim) >= 8:
                terms.add(claim)
    return tuple(sorted(terms))


def _require_no_oracle_leakage(text, terms, label):
    _require(isinstance(text, str), f"{label}은 문자열이어야 합니다.")
    folded = text.casefold()
    leaked = [term for term in terms if term.casefold() in folded]
    _require(not leaked, f"{label}에 oracle 문자열이 노출됐습니다: {leaked}")


def _require_loopback(value):
    _require(isinstance(value, str) and value, "model base_url이 비어 있습니다.")
    parsed = urlparse(value)
    _require(
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and parsed.username is None
        and parsed.password is None,
        "model base_url은 credential 없는 loopback HTTP(S)여야 합니다.",
    )


def _verify_attempt(
    attempt,
    *,
    schema,
    num_predict,
    expected_model_name,
    oracle_terms,
    label,
):
    required = {
        "attempt",
        "system_prompt",
        "user_prompt",
        "prompt_sha256",
        "status",
        "raw_response",
        "raw_response_sha256",
    }
    _require(isinstance(attempt, dict), f"{label}은 객체여야 합니다.")
    _require(not (required - set(attempt)), f"{label}에 필수 필드가 없습니다.")
    _require(
        attempt["prompt_sha256"]
        == _prompt_hash(
            attempt["system_prompt"],
            attempt["user_prompt"],
            schema,
            num_predict,
        ),
        f"{label} prompt SHA-256이 다릅니다.",
    )
    _require(
        attempt["raw_response_sha256"] == _sha256_text(attempt["raw_response"]),
        f"{label} raw response SHA-256이 다릅니다.",
    )
    _require_no_oracle_leakage(attempt["system_prompt"], oracle_terms, f"{label} system prompt")
    _require_no_oracle_leakage(attempt["user_prompt"], oracle_terms, f"{label} user prompt")
    if attempt["status"] in {"valid", "invalid"}:
        _require(
            attempt.get("model") == expected_model_name,
            f"{label} 응답 model name이 동결과 다릅니다.",
        )
    else:
        _require(attempt["status"] == "transport_error", f"{label} status가 올바르지 않습니다.")


def _verify_call(
    call,
    *,
    expected_system_prompt,
    expected_user_prompt,
    schema,
    num_predict,
    expected_model_name,
    oracle_terms,
    label,
):
    _require(isinstance(call, dict), f"{label}은 객체여야 합니다.")
    required = {"status", "base_prompt_sha256", "masked_prompt_sha256", "attempts", "output"}
    _require(not (required - set(call)), f"{label}에 필수 필드가 없습니다.")
    _require(
        call["base_prompt_sha256"]
        == _prompt_hash(expected_system_prompt, expected_user_prompt, schema, num_predict),
        f"{label} base prompt SHA-256이 다릅니다.",
    )
    _require(
        call["masked_prompt_sha256"]
        == _masked_prompt_hash(expected_system_prompt, expected_user_prompt, schema, num_predict),
        f"{label} masked prompt SHA-256이 다릅니다.",
    )
    attempts = call["attempts"]
    _require(
        isinstance(attempts, list) and 1 <= len(attempts) <= MAX_INVALID_JSON_ATTEMPTS,
        f"{label} attempt 수가 올바르지 않습니다.",
    )
    for index, attempt in enumerate(attempts, start=1):
        _require(attempt.get("attempt") == index, f"{label} attempt 번호가 연속적이지 않습니다.")
        if index == 1:
            _require(attempt.get("system_prompt") == expected_system_prompt, f"{label} system prompt가 다릅니다.")
            _require(attempt.get("user_prompt") == expected_user_prompt, f"{label} user prompt가 다릅니다.")
        else:
            _require(attempt.get("system_prompt") == expected_system_prompt, f"{label} retry system prompt가 바뀌었습니다.")
            _require(
                isinstance(attempt.get("user_prompt"), str)
                and attempt["user_prompt"].startswith(expected_user_prompt),
                f"{label} retry user prompt가 기본 prompt를 보존하지 않았습니다.",
            )
        _verify_attempt(
            attempt,
            schema=schema,
            num_predict=num_predict,
            expected_model_name=expected_model_name,
            oracle_terms=oracle_terms,
            label=f"{label}.attempts[{index - 1}]",
        )
    statuses = [attempt["status"] for attempt in attempts]
    if call["status"] == "valid":
        _require(statuses[-1] == "valid", f"{label} valid call의 마지막 attempt가 valid가 아닙니다.")
        _require(isinstance(call["output"], dict), f"{label} valid output이 없습니다.")
    elif call["status"] == "invalid_exhausted":
        _require(len(attempts) == MAX_INVALID_JSON_ATTEMPTS, f"{label} invalid exhausted 횟수가 다릅니다.")
        _require(all(status == "invalid" for status in statuses), f"{label} invalid exhausted 상태가 다릅니다.")
        _require(call["output"] is None, f"{label} 실패 output은 null이어야 합니다.")
    else:
        _require(call["status"] == "transport_error", f"{label} call status가 올바르지 않습니다.")
        _require(statuses == ["transport_error"], f"{label} transport error attempt가 다릅니다.")
        _require(call["output"] is None, f"{label} transport error output은 null이어야 합니다.")


def _verify_answer_output(call, label):
    output = call.get("output")
    if output is None:
        return
    _require(set(output) == {"answer"}, f"{label} answer output 필드가 다릅니다.")
    _require(isinstance(output["answer"], str) and output["answer"].strip(), f"{label} answer가 비어 있습니다.")


def _verify_review_output(call, draft, label):
    output = call.get("output")
    if output is None:
        return
    _require(
        set(output) == {"verdict", "reason", "revised_answer"},
        f"{label} reviewer output 필드가 다릅니다.",
    )
    _require(output["verdict"] in {"permit", "reject"}, f"{label} verdict가 올바르지 않습니다.")
    _require(isinstance(output["reason"], str) and output["reason"].strip(), f"{label} reason이 비어 있습니다.")
    _require(
        isinstance(output["revised_answer"], str) and output["revised_answer"].strip(),
        f"{label} revised_answer가 비어 있습니다.",
    )
    if output["verdict"] == "permit":
        _require(output["revised_answer"] == draft, f"{label} permit이 원 draft를 바꾸었습니다.")


def _verify_model_configuration(capture, run_plan):
    configuration = capture.get("configuration")
    _require(isinstance(configuration, dict), "capture configuration이 없습니다.")
    _require(configuration.get("experiment_id") == EXPERIMENT_ID, "configuration experiment_id가 다릅니다.")
    _require(configuration.get("seeds") == list(MECHANISM_SEEDS), "configuration seed가 다릅니다.")
    _require(configuration.get("answer_conditions") == list(ANSWER_CONDITIONS), "answer condition 순서가 다릅니다.")
    _require(configuration.get("reviewers") == list(REVIEWERS), "reviewer 순서가 다릅니다.")
    _require(configuration.get("model_name") == run_plan["model"]["name"], "model name이 run plan과 다릅니다.")
    _require(configuration.get("answer_num_predict") == ANSWER_NUM_PREDICT == run_plan["answer_num_predict"], "answer num_predict가 다릅니다.")
    _require(configuration.get("review_num_predict") == REVIEW_NUM_PREDICT == run_plan["reviewer_num_predict"], "review num_predict가 다릅니다.")
    _require(configuration.get("maximum_invalid_json_attempts") == MAX_INVALID_JSON_ATTEMPTS == run_plan["maximum_attempts_per_call"], "maximum attempt가 다릅니다.")
    _require(
        configuration.get("answer_condition_block_lengths")
        == validate_condition_block_lengths(ANSWER_CONDITION_BLOCKS),
        "answer treatment 길이가 동결과 다릅니다.",
    )
    _require(
        configuration.get("reviewer_condition_block_lengths")
        == validate_condition_block_lengths(REVIEWER_CONDITION_BLOCKS),
        "reviewer treatment 길이가 동결과 다릅니다.",
    )

    runtime = configuration.get("model_runtime")
    _require(isinstance(runtime, dict), "model_runtime이 없습니다.")
    for key in ("num_ctx", "temperature", "timeout_seconds", "keep_alive"):
        _require(runtime.get(key) == run_plan["model"][key], f"model_runtime.{key}가 run plan과 다릅니다.")
    _require_loopback(runtime.get("base_url"))
    digest = runtime.get("model_digest")
    _require_sha256(digest, "model digest")
    _require(digest == run_plan["model"]["digest"], "model digest가 run plan과 다릅니다.")
    _require(
        runtime.get("server_version") == run_plan["model"]["server_version"],
        "Ollama server version이 run plan과 다릅니다.",
    )

    metadata = capture.get("model_metadata")
    _require(isinstance(metadata, dict) and set(metadata) == {str(seed) for seed in MECHANISM_SEEDS}, "model_metadata seed grid가 다릅니다.")
    for seed in MECHANISM_SEEDS:
        item = metadata[str(seed)]
        _require(item.get("seed") == seed, "model_metadata seed가 다릅니다.")
        _require(item.get("model_name") == configuration["model_name"], "model_metadata model name이 다릅니다.")
        _require(item.get("model_digest") == digest, "seed 사이 model digest가 다릅니다.")
        _require(item.get("server_version") == runtime["server_version"], "seed 사이 server version이 다릅니다.")
        _require(item.get("runtime") == {key: runtime[key] for key in ("base_url", "num_ctx", "temperature", "timeout_seconds", "keep_alive")}, "seed 사이 model runtime이 다릅니다.")
    return configuration


def verify_capture(
    capture_path,
    packet_path,
    *,
    run_plan_path=DEFAULT_RUN_PLAN_PATH,
    manifest_path=DEFAULT_SOURCE_MANIFEST_PATH,
    evidence_plan_path=DEFAULT_EVIDENCE_PLAN_PATH,
):
    """capture.json과 packet set을 실제 raw unit까지 오프라인 검증한다."""

    capture_file, capture = _read_json(capture_path, "mechanism capture")
    _packet_file, packet_set = _read_json(packet_path, "evidence packet set")
    _run_plan_file, run_plan = _read_json(run_plan_path, "mechanism run plan")

    _require(run_plan.get("schema_version") == SCHEMA_VERSION, "run plan schema_version이 다릅니다.")
    _require(run_plan.get("experiment_id") == EXPERIMENT_ID, "run plan experiment_id가 다릅니다.")
    _require(run_plan.get("study_status") == "exploratory-mechanism-replay", "run plan의 exploratory 상태가 다릅니다.")
    _require(run_plan.get("seeds") == list(MECHANISM_SEEDS), "run plan seed가 다릅니다.")
    _require(run_plan.get("answer_conditions") == list(ANSWER_CONDITIONS), "run plan answer conditions가 다릅니다.")
    _require(run_plan.get("reviewer_conditions") == list(REVIEWERS), "run plan reviewer conditions가 다릅니다.")
    _require(
        run_plan.get("answer_condition_character_count")
        == len(next(iter(ANSWER_CONDITION_BLOCKS.values()))),
        "run plan answer treatment 문자 수가 다릅니다.",
    )
    _require(
        run_plan.get("reviewer_condition_character_count")
        == len(next(iter(REVIEWER_CONDITION_BLOCKS.values()))),
        "run plan reviewer treatment 문자 수가 다릅니다.",
    )
    _require(
        run_plan.get("answer_condition_sha256")
        == {name: _sha256_text(block) for name, block in ANSWER_CONDITION_BLOCKS.items()},
        "run plan answer treatment SHA-256이 현재 동결 문구와 다릅니다.",
    )
    _require(
        run_plan.get("reviewer_condition_sha256")
        == {name: _sha256_text(block) for name, block in REVIEWER_CONDITION_BLOCKS.items()},
        "run plan reviewer treatment SHA-256이 현재 동결 문구와 다릅니다.",
    )

    packet_summary = validate_evidence_packet_set(
        packet_set,
        manifest_path=manifest_path,
        evidence_plan_path=evidence_plan_path,
    )
    _require(packet_summary["packet_count"] == 30, "packet은 30 case여야 합니다.")
    _require(packet_summary["request_count"] == 32, "evidence plan은 32 exact reads여야 합니다.")
    packet_file_sha256 = _sha256_bytes(Path(packet_path).resolve(strict=True).read_bytes())
    _require(
        packet_summary["source_manifest_sha256"] == run_plan["source_manifest_sha256"],
        "source manifest SHA-256이 run plan과 다릅니다.",
    )
    _require(
        packet_set["packet_set_sha256"] == run_plan["evidence_packet_set_sha256"],
        "evidence packet set SHA-256이 run plan과 다릅니다.",
    )
    _require(
        packet_file_sha256 == run_plan["evidence_packet_file_sha256"],
        "evidence packet file SHA-256이 run plan과 다릅니다.",
    )
    _require(run_plan.get("planned_case_count") == 30, "run plan case count가 다릅니다.")
    _require(run_plan.get("planned_answer_calls") == 360, "run plan answer call 수가 다릅니다.")
    _require(run_plan.get("planned_reviewer_calls") == 180, "run plan reviewer call 수가 다릅니다.")
    _require(run_plan.get("planned_model_calls") == 540, "run plan model call 수가 다릅니다.")
    _require(capture.get("schema_version") == SCHEMA_VERSION, "capture schema_version이 다릅니다.")
    _require(capture.get("capture_status") == "complete", "capture가 complete 상태가 아닙니다.")
    _require(capture.get("review_status") == "unscored_raw_capture", "capture review_status가 다릅니다.")
    _require(capture.get("publishable") is False, "raw capture는 publishable=false여야 합니다.")
    configuration = _verify_model_configuration(capture, run_plan)
    _require(
        configuration.get("packet_set_sha256") == packet_set["packet_set_sha256"],
        "capture와 evidence packet set hash가 다릅니다.",
    )

    packets = packet_set["packets"]
    packet_by_index = {index: packet for index, packet in enumerate(packets)}
    expected_keys = {
        (seed, packet_index)
        for seed in MECHANISM_SEEDS
        for packet_index in range(len(packets))
    }
    artifacts = capture.get("raw_artifacts")
    _require(isinstance(artifacts, list), "capture raw_artifacts는 배열이어야 합니다.")
    _require(capture.get("planned_unit_count") == len(expected_keys) == 90, "planned unit은 90개여야 합니다.")
    _require(capture.get("completed_unit_count") == len(expected_keys), "completed unit은 90개여야 합니다.")
    _require(len(artifacts) == len(expected_keys), "raw artifact는 90개여야 합니다.")

    root = capture_file.parent.resolve(strict=True)
    oracle_terms = _oracle_terms(manifest_path)
    seen_keys = set()
    seen_paths = set()
    answer_call_count = 0
    reviewer_call_count = 0
    model_attempt_count = 0

    for artifact_index, artifact in enumerate(artifacts):
        _require(isinstance(artifact, dict), "raw artifact entry는 객체여야 합니다.")
        key = (artifact.get("seed"), artifact.get("packet_index"))
        _require(key in expected_keys, f"예정에 없는 raw artifact key입니다: {key}")
        _require(key not in seen_keys, f"raw artifact key가 중복됐습니다: {key}")
        seen_keys.add(key)
        _require(artifact.get("path") not in seen_paths, "raw artifact path가 중복됐습니다.")
        seen_paths.add(artifact.get("path"))
        raw_path = _resolve_artifact(root, artifact.get("path"), f"raw_artifacts[{artifact_index}]")
        raw_bytes = raw_path.read_bytes()
        _require(artifact.get("byte_count") == len(raw_bytes), "raw artifact byte_count가 다릅니다.")
        _require_sha256(artifact.get("sha256"), "raw artifact sha256")
        _require(_sha256_bytes(raw_bytes) == artifact["sha256"], "raw artifact SHA-256이 다릅니다.")
        try:
            unit = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("raw unit은 유효한 UTF-8 JSON이어야 합니다.") from error
        _require(isinstance(unit, dict), "raw unit 최상위 값은 객체여야 합니다.")
        seed, packet_index = key
        packet = packet_by_index[packet_index]
        _require(unit.get("schema_version") == SCHEMA_VERSION, "raw unit schema_version이 다릅니다.")
        _require(unit.get("experiment_id") == EXPERIMENT_ID, "raw unit experiment_id가 다릅니다.")
        _require(unit.get("case_id") == artifact.get("case_id") == packet["case_id"], "raw unit case_id가 다릅니다.")
        _require(unit.get("packet_index") == packet_index, "raw unit packet_index가 다릅니다.")
        _require(unit.get("seed") == seed, "raw unit seed가 다릅니다.")
        _require(unit.get("packet_sha256") == packet["packet_sha256"], "raw unit packet hash가 다릅니다.")
        seed_index = list(MECHANISM_SEEDS).index(seed)
        _require(
            unit.get("answer_condition_order") == list(balanced_answer_order(packet_index, seed_index)),
            "answer condition order가 사전 배치와 다릅니다.",
        )
        _require(
            unit.get("reviewer_order") == list(balanced_reviewer_order(packet_index, seed_index)),
            "reviewer order가 사전 배치와 다릅니다.",
        )

        # mechanism_capture가 A/R 필드를 조건 불변 K/M token으로 바꾼는
        # payload를 포함한 정확 prompt를 다시 만들기 위해 같은 helper를 쓴다.
        from .mechanism_capture import _opaque_payload

        prompt_payload = _opaque_payload(packet["payload"])
        answer_calls = unit.get("answer_calls")
        _require(isinstance(answer_calls, dict) and set(answer_calls) == set(ANSWER_CONDITIONS), "raw unit은 4개 answer call을 가져야 합니다.")
        answer_masked_hashes = set()
        for condition in ANSWER_CONDITIONS:
            expected_system, expected_user = build_answer_prompts(prompt_payload, condition)
            call = answer_calls[condition]
            _verify_call(
                call,
                expected_system_prompt=expected_system,
                expected_user_prompt=expected_user,
                schema=ANSWER_SCHEMA,
                num_predict=ANSWER_NUM_PREDICT,
                expected_model_name=configuration["model_name"],
                oracle_terms=oracle_terms,
                label=f"{key} answer {condition}",
            )
            _verify_answer_output(call, f"{key} answer {condition}")
            answer_masked_hashes.add(call["masked_prompt_sha256"])
            answer_call_count += 1
            model_attempt_count += len(call["attempts"])
        _require(len(answer_masked_hashes) == 1, "같은 unit의 answer masked prompt hash가 다릅니다.")

        reviewer_calls = unit.get("reviewer_calls")
        _require(isinstance(reviewer_calls, dict) and set(reviewer_calls) == set(REVIEWERS), "raw unit은 2개 reviewer call을 가져야 합니다.")
        consumer_output = answer_calls[AR_CONSUMER_RULE].get("output")
        reviewer_masked_hashes = set()
        if isinstance(consumer_output, dict):
            draft = consumer_output["answer"]
            for reviewer in REVIEWERS:
                expected_system, expected_user = build_reviewer_prompts(prompt_payload, draft, reviewer)
                call = reviewer_calls[reviewer]
                _verify_call(
                    call,
                    expected_system_prompt=expected_system,
                    expected_user_prompt=expected_user,
                    schema=REVIEW_SCHEMA,
                    num_predict=REVIEW_NUM_PREDICT,
                    expected_model_name=configuration["model_name"],
                    oracle_terms=oracle_terms,
                    label=f"{key} reviewer {reviewer}",
                )
                _verify_review_output(call, draft, f"{key} reviewer {reviewer}")
                reviewer_masked_hashes.add(call["masked_prompt_sha256"])
                reviewer_call_count += 1
                model_attempt_count += len(call["attempts"])
            _require(len(reviewer_masked_hashes) == 1, "같은 unit의 reviewer masked prompt hash가 다릅니다.")
        else:
            for reviewer in REVIEWERS:
                call = reviewer_calls[reviewer]
                _require(
                    call
                    == {
                        "status": "skipped_no_consumer_draft",
                        "base_prompt_sha256": None,
                        "masked_prompt_sha256": None,
                        "attempts": [],
                        "output": None,
                    },
                    "consumer draft 실패 reviewer는 정확한 skipped 기록이어야 합니다.",
                )

        _require(
            unit.get("derived_outputs") == _derive_outputs(answer_calls[AR_CONSUMER_RULE], reviewer_calls),
            "shadow/enforced 파생 결과가 reviewer verdict와 원 draft에서 정확히 계산되지 않았습니다.",
        )

    _require(seen_keys == expected_keys, "30×3 raw unit grid가 완전하지 않습니다.")
    _require(answer_call_count == 360, "answer call은 360개여야 합니다.")
    # consumer draft 실패는 reviewer를 ITT 실패로 남기므로 실제 reviewer
    # 호출 수는 180보다 작을 수 있다. grid는 위에서 여전히 검증된다.
    _require(reviewer_call_count <= 180, "reviewer call이 180개를 초과했습니다.")

    return {
        "experiment_id": EXPERIMENT_ID,
        "exploratory": True,
        "independent_confirmatory": False,
        "case_count": 30,
        "seed_count": 3,
        "unit_count": 90,
        "evidence_request_count": packet_summary["request_count"],
        "packet_set_sha256": packet_set["packet_set_sha256"],
        "packet_file_sha256": packet_file_sha256,
        "capture_file_sha256": _sha256_bytes(capture_file.read_bytes()),
        "model_name": configuration["model_name"],
        "model_digest": configuration["model_runtime"]["model_digest"],
        "answer_call_count": answer_call_count,
        "reviewer_call_count": reviewer_call_count,
        "model_attempt_count": model_attempt_count,
    }


def _build_parser():
    parser = argparse.ArgumentParser(
        description="ARM mechanism replay capture의 packet·raw hash·prompt 동일성을 검증합니다."
    )
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--run-plan", type=Path, default=DEFAULT_RUN_PLAN_PATH)
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    try:
        result = verify_capture(
            args.capture,
            args.packets,
            run_plan_path=args.run_plan,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"mechanism capture 검증 실패: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "verify_capture"]
