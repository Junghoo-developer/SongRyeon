"""Confirmatory capture verifier의 fail-closed 경계를 검사한다."""

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from uuid import NAMESPACE_URL, uuid5

import pytest

from evals.evidence_laundering_verify import (
    DEFAULT_CASE_ROOT,
    EXPECTED_MODEL,
    verify_captures,
    verify_registered_experiment,
)
from evals.runner import load_manifest


MODEL_DIGEST = EXPECTED_MODEL["digest_prefix"] + (
    "0" * (64 - len(EXPECTED_MODEL["digest_prefix"]))
)
FILE_TOOLBOX_MAX_BYTES = 16_384
VARIANT_CONTRACTS = {
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


def _json_bytes(value):
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path, value):
    path.write_bytes(
        (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _record(*, information, information_type, turn_id, record_label):
    information_class = (
        "absolute" if information_type == "final_delivery" else "relative"
    )
    return {
        "information": information,
        "information_class": information_class,
        "code_verifiable": information_class == "absolute",
        "information_type": information_type,
        "turn_id": turn_id,
        "information_id": str(uuid5(NAMESPACE_URL, record_label)),
        "created_at": "2026-08-03T00:00:00+00:00",
    }


def _raw_events(*, seed, variant, case_id, question, answer, turn_id):
    label = f"{seed}:{variant}:{case_id}"
    answer_record = _record(
        information=answer,
        information_type="node3_answer",
        turn_id=(
            f"{turn_id}-answer"
            if variant == "single-tool-agent"
            else f"{turn_id}-node3-synthetic"
        ),
        record_label=f"{label}:answer",
    )
    return [
        _record(
            information=question,
            information_type="user_input",
            turn_id=turn_id,
            record_label=f"{label}:question",
        ),
        answer_record,
        _record(
            information=json.dumps(
                {"answer_information_id": answer_record["information_id"]},
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            information_type="final_delivery",
            turn_id=f"{turn_id}-final",
            record_label=f"{label}:delivery",
        ),
    ]


def _write_raw_artifact(capture_dir, relative_path, events):
    raw_path = capture_dir / relative_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    content = b"".join(_json_bytes(event) for event in events)
    raw_path.write_bytes(content)
    counts = Counter(event["information_type"] for event in events)
    return {
        "path": relative_path.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "byte_count": len(content),
        "format": "songryeon-memory-jsonl",
        "event_count": len(events),
        "information_type_counts": dict(sorted(counts.items())),
    }


def _project_fixture_identity(manifest):
    entries = sorted(
        (fixture.to_dict() for fixture in manifest.source_fixtures),
        key=lambda fixture: fixture["path"],
    )
    payload = json.dumps(
        entries,
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
        "python_file_count": len(entries),
    }


def _system_document(variant, seed):
    contract = VARIANT_CONTRACTS[variant]
    return {
        "system_name": f"{variant}-gemma4-26b",
        "variant": variant,
        "backbone": EXPECTED_MODEL["name"],
        "model_tag": EXPECTED_MODEL["name"],
        "model_id": MODEL_DIGEST,
        "provider": "ollama",
        "execution_profile": "contest_local_or_self_hosted",
        "server_version": "synthetic-1.0",
        "comparison_group": "architecture_same_backbone",
        "system_wrapper": contract["system_wrapper"],
        "node4_mode": contract["node4_mode"],
        "configuration": {
            "base_url": "http://127.0.0.1:11434",
            "num_ctx": EXPECTED_MODEL["num_ctx"],
            "timeout_seconds": EXPECTED_MODEL["timeout_seconds"],
            "keep_alive": EXPECTED_MODEL["keep_alive"],
            "temperature": EXPECTED_MODEL["temperature"],
            "seed": seed,
        },
        "runtime_contract": {
            "maximum_tool_calls_per_case": 3,
            "file_toolbox_max_python_file_bytes": (
                FILE_TOOLBOX_MAX_BYTES
            ),
        },
    }


def _build_capture_bundle(root):
    case_root = Path(DEFAULT_CASE_ROOT)
    preflight = verify_registered_experiment(case_root)
    manifest = load_manifest(case_root / "manifest.json")
    plan = _read_json(case_root / "RUN_PLAN.json")

    for run in plan["runs"]:
        seed = run["seed"]
        capture_dir = root / f"seed-{seed}"
        capture_dir.mkdir(parents=True)
        systems = [
            _system_document(variant, seed)
            for variant in run["variants"]
        ]
        captures = []
        for system in systems:
            variant = system["variant"]
            for case in manifest.cases:
                question = manifest.questions[case.case_id]
                answer = f"synthetic grounded answer for {case.case_id}"
                turn_id = f"turn-{seed}-{variant}-{case.case_id}"
                relative_path = (
                    Path("raw")
                    / system["system_name"]
                    / f"{case.case_id}.memory.jsonl"
                )
                artifact = _write_raw_artifact(
                    capture_dir,
                    relative_path,
                    _raw_events(
                        seed=seed,
                        variant=variant,
                        case_id=case.case_id,
                        question=question,
                        answer=answer,
                        turn_id=turn_id,
                    ),
                )
                captures.append(
                    {
                        "case_id": case.case_id,
                        "system_name": system["system_name"],
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
                        "answer": answer,
                        "completed": True,
                        "error": None,
                        "turn_id": turn_id,
                        "tool_call_count": 0,
                        "model_exchange_count": 0,
                        "wall_clock_limit_seconds": 600,
                        "wall_clock_limit_exhausted": False,
                        "raw_memory_artifact": artifact,
                    }
                )

        document = {
            "schema_version": 1,
            "capture_status": "live_raw_draft",
            "review_status": "draft",
            "publishable": False,
            "uses_external_api": False,
            "captured_at": "2026-08-03T00:00:00+00:00",
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
                    FILE_TOOLBOX_MAX_BYTES
                ),
                "same_model_generation_configuration": True,
                "architecture_backbone_digest_consistent": True,
                "expected_architecture_digest_prefix": (
                    EXPECTED_MODEL["digest_prefix"]
                ),
                "expected_manifest_sha256": manifest.sha256,
                "expected_system_source_tree_sha256": (
                    preflight["system_source_tree_sha256"]
                ),
                "captured_system_source_tree_sha256": (
                    preflight["system_source_tree_sha256"]
                ),
                "captured_system_source_file_count": (
                    preflight["system_source_file_count"]
                ),
                "same_case_wall_clock_limit_seconds": 600,
                "automatic_answer_grading": False,
                "architecture_backbone": EXPECTED_MODEL["name"],
                "architecture_variants": run["variants"],
                "architecture_comparison_complete": True,
                "backbone_comparison_models": [],
                "bare_model_baseline_included": False,
                "structural_effect_claim_allowed": False,
            },
            "comparison_groups": {
                "architecture_same_backbone": {
                    "backbone": EXPECTED_MODEL["name"],
                    "variants": run["variants"],
                },
                "backbone_full_songryeon": {
                    "backbones": [],
                    "variant": "songryeon-full",
                },
            },
            "systems": systems,
            "coverage": {
                "system_count": len(systems),
                "unique_backbone_count": 1,
                "case_count": len(manifest.cases),
                "capture_count": len(captures),
                "complete_case_system_matrix": True,
                "completed_capture_count": len(captures),
                "failed_capture_count": 0,
            },
            "captures": captures,
        }
        _write_json(capture_dir / "capture.json", document)

    return root


@pytest.fixture(scope="module")
def pristine_capture_bundle(tmp_path_factory):
    root = _build_capture_bundle(tmp_path_factory.mktemp("capture-baseline"))
    verify_captures(root, DEFAULT_CASE_ROOT)
    return root


@pytest.fixture
def capture_bundle(pristine_capture_bundle, tmp_path):
    root = tmp_path / "captures"
    shutil.copytree(pristine_capture_bundle, root)
    return root


def _capture_document(root, seed=42):
    path = root / f"seed-{seed}" / "capture.json"
    return path, _read_json(path)


def _rewrite_artifact(capture_dir, capture, events):
    artifact = capture["raw_memory_artifact"]
    updated = _write_raw_artifact(
        capture_dir,
        Path(artifact["path"]),
        events,
    )
    artifact.clear()
    artifact.update(updated)


def _artifact_events(capture_dir, capture):
    path = capture_dir / capture["raw_memory_artifact"]["path"]
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_valid_synthetic_capture_bundle_passes(pristine_capture_bundle):
    result = verify_captures(pristine_capture_bundle, DEFAULT_CASE_ROOT)

    assert result["verified_capture_count"] == 270


def test_duplicate_case_variant_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    document["captures"][1]["case_id"] = document["captures"][0]["case_id"]
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_missing_case_variant_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    document["captures"].pop()
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_duplicate_raw_artifact_path_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    document["captures"][1]["raw_memory_artifact"] = deepcopy(
        document["captures"][0]["raw_memory_artifact"]
    )
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


@pytest.mark.parametrize(
    ("configuration_key", "tampered_value"),
    (("num_ctx", 8_192), ("temperature", 0.25)),
)
def test_wrong_generation_configuration_is_rejected(
    capture_bundle,
    configuration_key,
    tampered_value,
):
    path, document = _capture_document(capture_bundle)
    document["systems"][0]["configuration"][configuration_key] = (
        tampered_value
    )
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_raw_jsonl_hash_tampering_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    capture = document["captures"][0]
    raw_path = path.parent / capture["raw_memory_artifact"]["path"]
    raw_path.write_bytes(raw_path.read_bytes() + b"\n")

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_raw_jsonl_event_count_tampering_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    document["captures"][0]["raw_memory_artifact"]["event_count"] += 1
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_raw_question_attribution_tampering_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    capture = document["captures"][0]
    events = _artifact_events(path.parent, capture)
    user_event = next(
        event
        for event in events
        if event["information_type"] == "user_input"
    )
    user_event["information"] = "tampered question"
    _rewrite_artifact(path.parent, capture, events)
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_raw_answer_attribution_tampering_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    capture = document["captures"][0]
    events = _artifact_events(path.parent, capture)
    answer_event = next(
        event
        for event in events
        if event["information_type"] == "node3_answer"
    )
    answer_event["information"] = "tampered answer"
    _rewrite_artifact(path.parent, capture, events)
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)


def test_captured_system_source_tree_mismatch_is_rejected(capture_bundle):
    path, document = _capture_document(capture_bundle)
    document["conditions"]["captured_system_source_tree_sha256"] = "0" * 64
    _write_json(path, document)

    with pytest.raises(ValueError):
        verify_captures(capture_bundle, DEFAULT_CASE_ROOT)
