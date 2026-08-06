"""로컬 모델 raw capture가 네트워크 없이 결정론적으로 조립되는지 검사한다."""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from agent_tools import FileToolbox
from demo.cli import DEMO_MAX_PYTHON_FILE_BYTES
from llm import ModelReply
from memory import DEFAULT_MEMORY_PATH

from evals.live_capture import (
    CHECKPOINT_FILENAME,
    capture_local_comparison,
    main,
)
from evals.runner import load_manifest
from evals.source_identity import current_system_source_identity
from evals.variants import (
    SINGLE_TOOL_AGENT,
    SONGRYEON_FULL,
    SONGRYEON_NO_NODE4,
    run_single_tool_agent_turn,
)


def _json(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    )


class FakeLocalOllama:
    """실제 runtime을 통과하지만 네트워크를 전혀 사용하지 않는 fake client."""

    provider = "ollama"
    execution_mode = "contest_local_or_self_hosted"
    instances = []

    def __init__(
        self,
        *,
        base_url,
        model_name,
        timeout_seconds,
        num_ctx,
        keep_alive,
        temperature,
        seed,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.temperature = temperature
        self.seed = seed
        self.calls = []
        type(self).instances.append(self)

    def check_ready(self):
        return {
            "server_version": "fake-1.0",
            "model_name": self.model_name,
            "model_digest": hashlib.sha256(
                self.model_name.encode("utf-8")
            ).hexdigest(),
        }

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        response_schema,
        num_predict,
    ):
        properties = set(response_schema["properties"])
        if properties == {
            "action",
            "reason",
            "tool_name",
            "arguments",
        }:
            payload = {
                "action": "route_node2",
                "reason": "fake client는 현재 기록으로 검토를 요청한다.",
                "tool_name": None,
                "arguments": None,
            }
        elif properties == {"verdict", "reason"}:
            payload = {
                "verdict": "permit",
                "reason": "fake client의 결정론적 검토 결과다.",
            }
        elif properties == {"answer"}:
            payload = {
                "answer": f"{self.model_name}의 결정론적 fake 답변",
            }
        else:
            raise AssertionError(f"예상하지 못한 schema: {properties}")

        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "num_predict": num_predict,
            }
        )
        return ModelReply(
            content=_json(payload),
            thinking="",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 1},
        )


class FailingFakeLocalOllama(FakeLocalOllama):
    instances = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        raise RuntimeError("synthetic local transport failure")


class StepTimer:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 1_000_000
        return self.value


class JumpBudgetClock:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 2_000_000_000
        return self.value


class ThreeToolFake(FakeLocalOllama):
    """매 행동에서 도구를 요구해 코드의 3회 상한을 시험한다."""

    instances = []

    def complete(
        self,
        *,
        system_prompt,
        user_prompt,
        response_schema,
        num_predict,
    ):
        properties = set(response_schema["properties"])
        if properties == {
            "action",
            "reason",
            "tool_name",
            "arguments",
        }:
            payload = {
                "action": "use_tool",
                "reason": "목록을 다시 확인한다.",
                "tool_name": "list_python_files",
                "arguments": {},
            }
        elif properties == {"answer"}:
            payload = {"answer": "도구 세 번 뒤 답한다."}
        else:
            raise AssertionError(properties)
        self.calls.append({"properties": properties})
        return ModelReply(
            content=_json(payload),
            thinking="",
            model=self.model_name,
            done_reason="stop",
            metrics={"eval_count": 1},
        )


def _raw_events(capture_root, capture):
    path = capture_root / capture["raw_memory_artifact"]["path"]
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_fake_local_models_capture_all_cases_without_real_memory(tmp_path):
    FakeLocalOllama.instances = []
    output_dir = tmp_path / "capture"
    default_existed = DEFAULT_MEMORY_PATH.exists()
    default_before = (
        DEFAULT_MEMORY_PATH.read_bytes()
        if default_existed
        else None
    )

    capture_path, document = capture_local_comparison(
        output_dir=output_dir,
        client_factory=FakeLocalOllama,
        perf_counter_ns=StepTimer(),
        now_factory=lambda: datetime(
            2026,
            7,
            30,
            0,
            0,
            tzinfo=timezone.utc,
        ),
    )
    source_identity = current_system_source_identity()

    assert capture_path == output_dir / "capture.json"
    assert document["capture_status"] == "live_raw_draft"
    assert document["review_status"] == "draft"
    assert document["publishable"] is False
    assert document["uses_external_api"] is False
    assert document["conditions"] == {
        "case_memory_isolated": True,
        "actual_memory_used": False,
        "project_fixture": {
            "manifest_relative_path": "project",
            "tree_sha256": (
                "35ae5c1b5ca667f4f00a60eb0b9d4307cbc215cba85d649b5b"
                "b2fb11bf14266c"
            ),
            "python_file_count": 4,
        },
        "file_toolbox_max_python_file_bytes": (
            DEMO_MAX_PYTHON_FILE_BYTES
        ),
        "same_model_generation_configuration": True,
        "architecture_backbone_digest_consistent": True,
        "expected_architecture_digest_prefix": None,
        "expected_manifest_sha256": None,
        "expected_system_source_tree_sha256": None,
        "captured_system_source_tree_sha256": (
            source_identity["tree_sha256"]
        ),
        "captured_system_source_file_count": source_identity["file_count"],
        "same_case_wall_clock_limit_seconds": 600,
        "automatic_answer_grading": False,
        "architecture_backbone": "qwen3:14b",
        "architecture_variants": [
            SINGLE_TOOL_AGENT,
            SONGRYEON_NO_NODE4,
            SONGRYEON_FULL,
        ],
        "architecture_comparison_complete": True,
        "backbone_comparison_models": [],
        "bare_model_baseline_included": False,
        "structural_effect_claim_allowed": False,
    }
    assert document["coverage"] == {
        "system_count": 3,
        "unique_backbone_count": 1,
        "case_count": 10,
        "capture_count": 30,
        "complete_case_system_matrix": True,
        "completed_capture_count": 30,
        "failed_capture_count": 0,
    }
    assert [system["system_name"] for system in document["systems"]] == [
        "single-tool-agent-qwen3-14b",
        "songryeon-no-node4-qwen3-14b",
        "songryeon-full-qwen3-14b",
    ]
    assert [system["variant"] for system in document["systems"]] == [
        SINGLE_TOOL_AGENT,
        SONGRYEON_NO_NODE4,
        SONGRYEON_FULL,
    ]
    assert [system["backbone"] for system in document["systems"]] == [
        "qwen3:14b",
        "qwen3:14b",
        "qwen3:14b",
    ]
    assert all(
        system["runtime_contract"]["maximum_tool_calls_per_case"] == 3
        for system in document["systems"]
    )
    assert all(
        system["runtime_contract"][
            "file_toolbox_max_python_file_bytes"
        ] == DEMO_MAX_PYTHON_FILE_BYTES
        for system in document["systems"]
    )
    assert document["systems"][1]["node4_mode"] == (
        "eval_only_deterministic_bypass"
    )
    assert {
        json.dumps(system["configuration"], sort_keys=True)
        for system in document["systems"]
    } == {
        json.dumps(
            {
                "base_url": "http://127.0.0.1:11434",
                "num_ctx": 16384,
                "timeout_seconds": 180,
                "keep_alive": "10m",
                "temperature": 0,
                "seed": 42,
            },
            sort_keys=True,
        )
    }

    for capture in document["captures"]:
        assert capture["completed"] is True
        assert capture["error"] is None
        assert capture["latency_ms"] == 1.0
        assert capture["wall_clock_limit_seconds"] == 600
        assert capture["wall_clock_limit_exhausted"] is False
        assert capture["tool_call_count"] == 0
        assert capture["tool_call_limit_reached"] is False
        assert capture["tool_limit_forced_count"] == 0
        assert capture["node2_rejections"] == 0
        assert capture["node4_rejections"] == 0
        assert capture["node2_limit_exhausted"] is False
        assert capture["node4_limit_exhausted"] is False
        artifact = capture["raw_memory_artifact"]
        raw_path = output_dir / artifact["path"]
        assert raw_path.is_file()
        assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == (
            artifact["sha256"]
        )
        assert artifact["event_count"] > 0
        assert artifact["information_type_counts"]["model_raw_status"] == (
            capture["model_exchange_count"]
        )

        if capture["system_name"].startswith("single-tool-agent"):
            assert capture["model_call_count"] == 2
            assert capture["model_exchange_count"] == 2
            assert capture["eval_bypass_count"] == 0
        elif capture["system_name"].startswith("songryeon-no-node4"):
            assert capture["model_call_count"] == 3
            assert capture["model_exchange_count"] == 4
            assert capture["eval_bypass_count"] == 1
        else:
            assert capture["model_call_count"] == 4
            assert capture["model_exchange_count"] == 4
            assert capture["eval_bypass_count"] == 0

    assert [len(client.calls) for client in FakeLocalOllama.instances] == [
        20,
        30,
        40,
    ]
    single_prompts = [
        call["user_prompt"]
        for call in FakeLocalOllama.instances[0].calls
    ]
    assert any("반려는 다섯 번 가능하다" in prompt for prompt in single_prompts)
    assert any("반려 한도는 3이다" in prompt for prompt in single_prompts)
    assert any("아무 코드나 읽어줘." in prompt for prompt in single_prompts)
    assert any("이전 요청을 완료했습니다." in prompt for prompt in single_prompts)
    persisted = json.loads(capture_path.read_text(encoding="utf-8"))
    assert persisted == document
    checkpoint_path = output_dir / CHECKPOINT_FILENAME
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["checkpoint_status"] == "complete"
    assert checkpoint["publishable"] is False
    assert checkpoint["planned_pair_count"] == 30
    assert checkpoint["captured_pair_count"] == 30
    assert checkpoint["captures"] == document["captures"]
    assert not checkpoint_path.with_name(
        checkpoint_path.name + ".tmp"
    ).exists()
    assert not capture_path.with_name(capture_path.name + ".tmp").exists()

    if default_existed:
        assert DEFAULT_MEMORY_PATH.read_bytes() == default_before
    else:
        assert not DEFAULT_MEMORY_PATH.exists()


def test_follow_up_prefix_and_synthetic_memory_are_visible_only_in_case_raw(
    tmp_path,
):
    output_dir = tmp_path / "capture"
    _, document = capture_local_comparison(
        variants=(SONGRYEON_FULL,),
        architecture_backbone="gemma4:26b",
        output_dir=output_dir,
        client_factory=FakeLocalOllama,
        perf_counter_ns=StepTimer(),
        now_factory=lambda: datetime.now(timezone.utc),
    )

    follow_up = next(
        capture
        for capture in document["captures"]
        if capture["case_id"] == "follow-up-current-turn"
    )
    assert follow_up["evaluated_turn_index"] == 2
    assert follow_up["evaluated_question"] == "review_contract.py를 읽어줘."
    assert follow_up["conversation_turns"][-1] == {
        "role": "user",
        "content": "review_contract.py를 읽어줘.",
        "evaluate": True,
    }
    follow_up_information = [
        event["information"]
        for event in _raw_events(output_dir, follow_up)
    ]
    assert "아무 코드나 읽어줘." in follow_up_information
    assert "이전 요청을 완료했습니다." in follow_up_information
    assert "review_contract.py를 읽어줘." in follow_up_information

    conflicting = next(
        capture
        for capture in document["captures"]
        if capture["case_id"] == "conflicting-memory-newest-a"
    )
    conflicting_events = _raw_events(output_dir, conflicting)
    seeded_ids = {
        event["information_id"]
        for event in conflicting_events
        if event["information_type"] == "fixture_memory"
    }
    assert seeded_ids == {"old-r", "latest-a"}

    unrelated = next(
        capture
        for capture in document["captures"]
        if capture["case_id"] == "subjective-request-no-tool"
    )
    assert not any(
        event.get("information_id") in {"old-r", "latest-a"}
        for event in _raw_events(output_dir, unrelated)
    )


def test_case_failures_are_preserved_as_draft_instead_of_discarded(tmp_path):
    FailingFakeLocalOllama.instances = []
    output_dir = tmp_path / "failed-capture"

    _, document = capture_local_comparison(
        variants=(SONGRYEON_FULL,),
        architecture_backbone="gemma4:26b",
        output_dir=output_dir,
        client_factory=FailingFakeLocalOllama,
        perf_counter_ns=StepTimer(),
        now_factory=lambda: datetime.now(timezone.utc),
    )

    assert document["coverage"]["capture_count"] == 10
    assert document["coverage"]["completed_capture_count"] == 0
    assert document["coverage"]["failed_capture_count"] == 10
    for capture in document["captures"]:
        assert capture["completed"] is False
        assert capture["answer"] is None
        assert capture["error"] == {
            "type": "RuntimeError",
            "message": "synthetic local transport failure",
        }
        assert capture["model_call_count"] == 1
        assert capture["raw_memory_artifact"]["event_count"] > 0


def test_checkpoint_preserves_completed_pairs_when_capture_is_interrupted(
    tmp_path,
):
    output_dir = tmp_path / "interrupted-capture"
    case_starts = []

    def interrupt_during_second_case(message):
        prefix = message.split(": ", 1)[0]
        if prefix.count("/") != 1:
            return
        case_starts.append(prefix)
        if len(case_starts) == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        capture_local_comparison(
            variants=(SONGRYEON_FULL,),
            output_dir=output_dir,
            client_factory=FakeLocalOllama,
            perf_counter_ns=StepTimer(),
            now_factory=lambda: datetime.now(timezone.utc),
            on_progress=interrupt_during_second_case,
        )

    checkpoint_path = output_dir / CHECKPOINT_FILENAME
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["checkpoint_status"] == "in_progress"
    assert checkpoint["publishable"] is False
    assert checkpoint["planned_pair_count"] == 10
    assert checkpoint["captured_pair_count"] == 1
    assert len(checkpoint["captures"]) == 1
    artifact = checkpoint["captures"][0]["raw_memory_artifact"]
    assert (output_dir / artifact["path"]).is_file()
    assert not (output_dir / "capture.json").exists()
    assert not checkpoint_path.with_name(
        checkpoint_path.name + ".tmp"
    ).exists()


def test_same_case_wall_clock_deadline_is_enforced_before_model_calls(
    tmp_path,
):
    FakeLocalOllama.instances = []

    _, document = capture_local_comparison(
        variants=(SONGRYEON_FULL,),
        architecture_backbone="qwen3:14b",
        case_wall_clock_limit_seconds=1,
        output_dir=tmp_path / "deadline-capture",
        client_factory=FakeLocalOllama,
        perf_counter_ns=StepTimer(),
        budget_clock_ns=JumpBudgetClock(),
        now_factory=lambda: datetime.now(timezone.utc),
    )

    assert document["coverage"]["failed_capture_count"] == 10
    assert len(FakeLocalOllama.instances[0].calls) == 0
    for capture in document["captures"]:
        assert capture["wall_clock_limit_exhausted"] is True
        assert capture["error"]["type"] == "EvalWallClockLimitError"
        # 실패도 structured audit에 transport_error 원자로 남는다.
        assert capture["model_exchange_count"] == 1


def test_live_capture_cli_rejects_non_loopback_before_any_model_call(
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "--base-url",
            "https://api.example.com/v1",
            "--output-dir",
            str(tmp_path / "must-not-exist"),
        ]
    )

    assert exit_code == 1
    assert "loopback" in capsys.readouterr().err
    assert not (tmp_path / "must-not-exist").exists()


def test_frozen_manifest_and_model_digest_can_be_enforced_before_capture(
    tmp_path,
):
    manifest = load_manifest()
    expected_model_digest = hashlib.sha256(
        b"qwen3:14b"
    ).hexdigest()
    source_identity = current_system_source_identity()

    _, document = capture_local_comparison(
        variants=(SONGRYEON_FULL,),
        expected_manifest_sha256=manifest.sha256,
        expected_architecture_digest_prefix=expected_model_digest[:12],
        expected_system_source_tree_sha256=(
            source_identity["tree_sha256"]
        ),
        output_dir=tmp_path / "accepted",
        client_factory=FakeLocalOllama,
        perf_counter_ns=StepTimer(),
        now_factory=lambda: datetime.now(timezone.utc),
    )
    assert document["conditions"]["expected_manifest_sha256"] == (
        manifest.sha256
    )
    assert document["conditions"][
        "expected_architecture_digest_prefix"
    ] == expected_model_digest[:12]
    assert document["conditions"][
        "captured_system_source_tree_sha256"
    ] == source_identity["tree_sha256"]

    with pytest.raises(ValueError, match="manifest SHA-256"):
        capture_local_comparison(
            variants=(SONGRYEON_FULL,),
            expected_manifest_sha256="0" * 64,
            output_dir=tmp_path / "wrong-manifest",
            client_factory=FakeLocalOllama,
        )
    assert not (tmp_path / "wrong-manifest").exists()

    with pytest.raises(ValueError, match="model digest"):
        capture_local_comparison(
            variants=(SONGRYEON_FULL,),
            expected_architecture_digest_prefix="0" * 12,
            output_dir=tmp_path / "wrong-model",
            client_factory=FakeLocalOllama,
        )
    assert not (tmp_path / "wrong-model").exists()

    with pytest.raises(ValueError, match="system source tree SHA-256"):
        capture_local_comparison(
            variants=(SONGRYEON_FULL,),
            expected_system_source_tree_sha256="0" * 64,
            output_dir=tmp_path / "wrong-system-source",
            client_factory=FakeLocalOllama,
        )
    assert not (tmp_path / "wrong-system-source").exists()


def test_single_agent_uses_same_toolbox_and_stops_after_three_calls(tmp_path):
    manifest = load_manifest()
    client = ThreeToolFake(
        base_url="http://127.0.0.1:11434",
        model_name="qwen3:14b",
        timeout_seconds=180,
        num_ctx=16384,
        keep_alive="10m",
        temperature=0,
        seed=42,
    )
    memory_path = tmp_path / "memory.jsonl"

    result = run_single_tool_agent_turn(
        "파일 목록을 반복해서 확인해줘.",
        client=client,
        toolbox=FileToolbox(
            allowed_root=manifest.project_fixture_root,
        ),
        memory_path=memory_path,
    )

    assert result.total_tool_calls == 3
    assert len(client.calls) == 4
    assert [
        call["properties"]
        for call in client.calls
    ].count(
        {"action", "reason", "tool_name", "arguments"}
    ) == 3
    raw = [
        json.loads(line)
        for line in memory_path.read_text(encoding="utf-8").splitlines()
    ]
    assert sum(
        event["information_type"] == "tool_raw_name"
        for event in raw
    ) == 3
    assert sum(
        event["information_type"] == "eval_single_tool_limit"
        for event in raw
    ) == 1


def test_optional_backbone_group_is_separate_from_architecture_group(tmp_path):
    _, document = capture_local_comparison(
        variants=(SONGRYEON_FULL,),
        architecture_backbone="qwen3:14b",
        backbone_compare_models=("gemma4:26b", "qwen3:14b"),
        output_dir=tmp_path / "capture",
        client_factory=FakeLocalOllama,
        perf_counter_ns=StepTimer(),
        now_factory=lambda: datetime.now(timezone.utc),
    )

    assert document["comparison_groups"] == {
        "architecture_same_backbone": {
            "backbone": "qwen3:14b",
            "variants": [SONGRYEON_FULL],
        },
        "backbone_full_songryeon": {
            "backbones": ["gemma4:26b", "qwen3:14b"],
            "variant": SONGRYEON_FULL,
        },
    }
    systems = {
        system["system_name"]: system
        for system in document["systems"]
    }
    assert systems["songryeon-full-qwen3-14b"]["comparison_group"] == (
        "architecture_same_backbone"
    )
    assert systems[
        "backbone-songryeon-full-gemma4-26b"
    ]["comparison_group"] == "backbone_full_songryeon"
    assert systems[
        "backbone-songryeon-full-qwen3-14b"
    ]["backbone"] == "qwen3:14b"
    assert document["conditions"]["structural_effect_claim_allowed"] is False
