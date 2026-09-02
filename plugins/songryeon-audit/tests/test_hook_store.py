from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import sqlite3
import time

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from songryeon_store import (  # noqa: E402
    CHAIN_GUARANTEE,
    SongRyeonStore,
    _installed_plugin_data_dir,
    resolve_db_path,
)


def _atoms(event, authority=None):
    atoms = event["atoms"]
    if authority:
        atoms = [atom for atom in atoms if atom["authority"] == authority]
    return {atom["path"]: atom for atom in atoms}


def _prompt(session="session-1", turn="turn-1", **extra):
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": session,
        "turn_id": turn,
        "prompt": "Check the cooling controller before changing firmware.",
        "cwd": "C:/work",
        "model": "codex-test",
        "permission_mode": "default",
        **extra,
    }
    return payload


def _database_artifact_bytes(db_path: Path) -> bytes:
    artifacts = [db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")]
    return b"".join(path.read_bytes() for path in artifacts if path.exists())


def test_event_has_mixed_atoms_without_whole_event_label(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")

    event = store.append_hook_event(_prompt())

    assert "authority" not in event
    assert event["actor"] == {"id": None, "status": "unknown"}
    assert _atoms(event, "R")["prompt"]["value"].startswith("Check the cooling")
    assert _atoms(event, "A")["hook_event_name"]["value"] == "UserPromptSubmit"
    assert _atoms(event, "A")["payload.digest_sha256"]["value"]
    assert event["chain"]["guarantee"] == CHAIN_GUARANTEE
    assert "tamper_proof" not in event["chain"]
    assert any(
        gap["gap_kind"] == "actor_identity_unknown"
        for gap in event["coverage"]["gaps"]
    )


def test_tool_result_arrival_is_a_but_all_semantic_fields_remain_r_and_links(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    prompt = store.append_hook_event(_prompt())
    proposed = store.append_hook_event(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_use_id": "tool-1",
            "tool_input": {
                "command": "flash --board R3",
                "api_key": "not-a-real-test-secret",
            },
        }
    )
    result = store.append_hook_event(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_use_id": "tool-1",
            "tool_input": {"command": "flash --board R3"},
            "tool_response": {
                "exit_code": 0,
                "output": "Firmware command accepted; hardware effect unverified.",
                "details": {"status": "queued", "claim": "board is now safe"},
            },
        }
    )

    proposal_r = _atoms(proposed, "R")["tool_input"]
    assert proposal_r["authority"] == "R"
    assert proposal_r["value"]["api_key"] == "[REDACTED:sensitive-key]"
    assert "not-a-real-test-secret" not in json.dumps(proposed, ensure_ascii=False)

    result_a = _atoms(result, "A")
    result_r = _atoms(result, "R")
    assert result_a["tool_response.present"]["value"] is True
    assert result_a["tool_response.byte_count"]["value"] > 0
    assert result_a["tool_response.digest_sha256"]["value"]
    semantic = result_r["tool_response.semantic_content"]["value"]
    assert semantic["output"].startswith("Firmware command accepted")
    assert semantic["exit_code"] == 0
    assert semantic["details"]["status"] == "queued"
    assert semantic["details"]["claim"] == "board is now safe"
    assert "tool_response.exit_code" not in result_a
    assert "tool_response.details.status" not in result_a

    assert any(
        link["target_event_id"] == proposed["event_id"]
        and link["relation"] == "tool_result_matches_proposal_id"
        for link in result["links"]
    )
    trace = store.trace(result["event_id"], direction="ancestors", depth=2)
    ancestor_ids = {event["event_id"] for event in trace["ancestors"]}
    assert proposed["event_id"] in ancestor_ids
    assert prompt["event_id"] in ancestor_ids


def test_explicit_actor_is_used_but_shared_account_identity_is_not_inferred(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")

    explicit = store.append_hook_event(_prompt(actor_id="explicit-user-42"))
    unknown = store.append_hook_event(_prompt(turn="turn-2"))

    assert explicit["actor"] == {"id": "explicit-user-42", "status": "explicit"}
    assert unknown["actor"] == {"id": None, "status": "unknown"}


def test_redaction_truncation_and_coverage_gaps_are_queryable(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    huge_prompt = "Bearer abcdefghijklmnopqrstuvwxyz " + ("x" * 20_000)

    event = store.append_hook_event(_prompt(prompt=huge_prompt))

    prompt_atom = _atoms(event, "R")["prompt"]
    assert "abcdefghijklmnopqrstuvwxyz" not in prompt_atom["value"]
    assert "[REDACTED]" in prompt_atom["value"]
    assert prompt_atom["truncated"] is True
    gap_kinds = {gap["gap_kind"] for gap in store.find_gaps("session-1")}
    assert "redacted_content_not_stored" in gap_kinds
    assert "payload_truncated" in gap_kinds


def test_public_release_redacts_common_credentials_identity_and_home_paths(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    basic_token = "dXNlcjpwYXNz" + "d29yZA=="
    aws_access_key = "AKIA" + "1234567890ABCDEF"
    jwt_value = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "signature123"
    )
    sensitive_text = " ".join(
        [
            "contact=alice@example.invalid",
            "file=C:/Users/alice/work/private.txt",
            f"Authorization: Basic {basic_token}",
            f"AWS_ACCESS_KEY_ID={aws_access_key}",
            "AWS_SECRET_ACCESS_KEY=very-secret-value",
            "postgresql://dbuser:dbpass@example.invalid/private",
            jwt_value,
        ]
    )

    event = store.append_hook_event(_prompt(prompt=sensitive_text))
    stored = _atoms(event, "R")["prompt"]["value"]

    for forbidden in (
        "alice@example.invalid",
        "C:/Users/alice",
        basic_token,
        aws_access_key,
        "very-secret-value",
        "dbuser:dbpass",
        jwt_value.split(".")[0],
    ):
        assert forbidden not in stored
    assert "[REDACTED:email]" in stored
    assert "[USER_HOME]/work/private.txt" in stored
    assert stored.count("[REDACTED]") >= 4


def test_unknown_future_fields_are_omitted_instead_of_stored_wholesale(tmp_path):
    db_path = tmp_path / "audit.sqlite3"
    store = SongRyeonStore(db_path)
    secret = "future-private-value-that-must-not-be-stored"

    event = store.append_hook_event(_prompt(future_hook_payload={"secret": secret}))

    assert "unclassified_payload" not in _atoms(event)
    assert secret not in json.dumps(event, ensure_ascii=False)
    assert secret.encode("utf-8") not in _database_artifact_bytes(db_path)
    assert any(
        gap["gap_kind"] == "unclassified_payload_omitted"
        for gap in event["coverage"]["gaps"]
    )


@pytest.mark.parametrize(
    "tool_name",
    [
        "mcp__songryeon-audit__songryeon_get_event",
        "mcp__songryeon-audit__songryeon_doctor",
    ],
)
def test_songryeon_mcp_content_is_not_recursively_copied(tmp_path, tool_name):
    db_path = tmp_path / "audit.sqlite3"
    store = SongRyeonStore(db_path)
    secret = "retrieved-audit-content-must-not-be-duplicated"

    event = store.append_hook_event(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": tool_name,
            "tool_use_id": "tool-audit-1",
            "tool_input": {"event_id": "sra-old", "secret": secret},
            "tool_response": {"event": {"secret": secret}},
        }
    )

    atoms = _atoms(event)
    assert atoms["tool_input"]["value"] == (
        "[OMITTED:recursive-songryeon-audit-content]"
    )
    assert atoms["tool_response.semantic_content"]["value"] == (
        "[OMITTED:recursive-songryeon-audit-content]"
    )
    assert secret not in json.dumps(event, ensure_ascii=False)
    assert secret.encode("utf-8") not in _database_artifact_bytes(db_path)
    assert any(
        gap["gap_kind"] == "recursive_audit_content_omitted"
        for gap in event["coverage"]["gaps"]
    )


def test_search_sessions_descendants_and_chain_order(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    first = store.append_hook_event(_prompt(prompt="rare thermal phrase"))
    second = store.append_hook_event(
        {
            "hook_event_name": "Stop",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "last_assistant_message": "I changed the calibration assumption.",
            "stop_hook_active": False,
        }
    )

    assert store.search("rare thermal phrase")[0]["event_id"] == first["event_id"]
    descendants = store.trace(first["event_id"], "descendants", 1)
    assert second["event_id"] in {
        event["event_id"] for event in descendants["descendants"]
    }
    sessions = store.list_sessions()
    assert sessions[0]["session_id"] == "session-1"
    assert sessions[0]["event_count"] == 2
    assert sessions[0]["cwd"] == "C:/work"
    assert sessions[0]["instrumentation_status"] == "observed_partial_start_missing"
    assert sessions[0]["songryeon_record_found"] is True
    assert sessions[0]["session_start_seen"] is False
    assert sessions[0]["coverage_boundary"] == (
        "hook_observation_only_not_complete_runtime_capture"
    )
    assert second["chain"]["previous_digest"] == first["chain"]["digest"]
    assert store.trace("missing", "both", 2)["event"] is None
    with pytest.raises(ValueError):
        store.trace(first["event_id"], "sideways", 1)


def test_list_sessions_scopes_raw_windows_home_to_redacted_cwd(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    matching = store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "matching-project",
            "cwd": "C:\\Users\\Alice\\work\\Project-One\\",
            "source": "startup",
        }
    )
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "different-project",
            "cwd": "C:\\Users\\Alice\\work\\Project-Two",
            "source": "startup",
        }
    )

    assert _atoms(matching)["cwd"]["value"].startswith("[USER_HOME]")
    assert len(store.list_sessions()) == 2

    scoped = store.list_sessions(cwd="c:/users/alice/WORK/project-one")
    assert [item["session_id"] for item in scoped] == ["matching-project"]
    assert store.list_sessions(cwd="C:/Users/Alice/work/Project-Three") == []

    serialized = json.dumps(scoped, ensure_ascii=False).casefold()
    assert "alice" not in serialized
    assert "c:/users/" not in serialized
    assert "c:\\users\\" not in serialized


def test_list_sessions_preserves_posix_cwd_case_sensitivity(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "posix-project",
            "cwd": "/home/alice/Project",
            "source": "startup",
        }
    )

    assert [
        item["session_id"]
        for item in store.list_sessions(cwd="/home/alice/Project")
    ] == ["posix-project"]
    assert store.list_sessions(cwd="/home/alice/project") == []


def test_scoped_session_scan_is_bounded_and_reports_older_exclusion(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")
    for session_id, cwd in (
        ("old-match", "C:/work/target"),
        ("new-other-1", "C:/work/other-1"),
        ("new-other-2", "C:/work/other-2"),
    ):
        store.append_hook_event(
            {
                "hook_event_name": "SessionStart",
                "session_id": session_id,
                "cwd": cwd,
                "source": "startup",
            }
        )

    bounded = store.list_sessions_scoped(
        cwd="C:/work/target",
        sequence_window=2,
    )
    assert bounded["sessions"] == []
    assert bounded["scope_scan"] == {
        "bounded": True,
        "sequence_window": 2,
        "latest_sequence": 3,
        "minimum_sequence_included": 2,
        "candidate_sessions_examined": 2,
        "older_events_excluded": True,
        "coverage_boundary": (
            "recent_sequence_window_only_older_sessions_may_be_omitted"
        ),
    }

    complete = store.list_sessions_scoped(
        cwd="C:/work/target",
        sequence_window=3,
    )
    assert [item["session_id"] for item in complete["sessions"]] == [
        "old-match"
    ]
    assert complete["scope_scan"]["older_events_excluded"] is False


def test_session_status_distinguishes_start_partial_late_start_and_no_record(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")

    start = store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "from-start",
            "cwd": "C:/work/from-start",
            "source": "startup",
        }
    )
    store.append_hook_event(_prompt(session="from-start"))
    store.append_hook_event(
        {
            "hook_event_name": "SessionEnd",
            "session_id": "from-start",
            "reason": "closed",
        }
    )

    partial = store.append_hook_event(_prompt(session="partial"))
    late_first = store.append_hook_event(_prompt(session="late-start"))
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "late-start",
            "cwd": "C:/work/late-start",
            "source": "late-observation",
        }
    )
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "resumed",
            "cwd": "C:/work/resumed",
            "source": "resume",
        }
    )
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "missing-source",
            "cwd": "C:/work/missing-source",
        }
    )
    store.append_hook_event(
        {
            "hook_event_name": "SessionStart",
            "session_id": "missing-source",
            "cwd": "C:/work/missing-source",
            "source": "startup",
        }
    )

    from_start_status = store.get_session_status("from-start")
    partial_status = store.get_session_status("partial")
    late_status = store.get_session_status("late-start")
    resumed_status = store.get_session_status("resumed")
    missing_source_status = store.get_session_status("missing-source")
    missing_status = store.get_session_status("missing")
    listed = {item["session_id"]: item for item in store.list_sessions(limit=20)}

    assert from_start_status["instrumentation_status"] == "observed_from_session_start"
    assert from_start_status["first_event_id"] == start["event_id"]
    assert from_start_status["first_hook_name"] == "SessionStart"
    assert from_start_status["first_session_start_source"] == "startup"
    assert from_start_status["session_start_seen"] is True
    assert from_start_status["session_end_seen"] is True
    assert from_start_status["songryeon_record_found"] is True

    assert partial_status["instrumentation_status"] == "observed_partial_start_missing"
    assert partial_status["first_event_id"] == partial["event_id"]
    assert partial_status["session_start_seen"] is False
    assert partial_status["session_end_seen"] is False

    assert late_status["instrumentation_status"] == "observed_partial_start_missing"
    assert late_status["first_event_id"] == late_first["event_id"]
    assert late_status["first_hook_name"] == "UserPromptSubmit"
    assert late_status["session_start_seen"] is True

    assert resumed_status["first_hook_name"] == "SessionStart"
    assert resumed_status["first_session_start_source"] == "resume"
    assert resumed_status["instrumentation_status"] == (
        "observed_partial_start_missing"
    )
    assert missing_source_status["first_session_start_source"] is None
    assert missing_source_status["instrumentation_status"] == (
        "observed_partial_start_missing"
    )
    assert listed["from-start"]["instrumentation_status"] == (
        "observed_from_session_start"
    )
    assert listed["from-start"]["first_session_start_source"] == "startup"
    assert listed["resumed"]["instrumentation_status"] == (
        "observed_partial_start_missing"
    )
    assert listed["resumed"]["first_session_start_source"] == "resume"
    assert listed["missing-source"]["first_session_start_source"] is None
    assert listed["missing-source"]["instrumentation_status"] == (
        "observed_partial_start_missing"
    )

    assert missing_status == {
        "session_id": "missing",
        "event_count": 0,
        "first_recorded_at": None,
        "last_recorded_at": None,
        "unknown_actor_count": 0,
        "gap_count": 0,
        "first_event_id": None,
        "first_hook_name": None,
        "first_session_start_source": None,
        "last_event_id": None,
        "snapshot_last_event_id": None,
        "snapshot_max_sequence": None,
        "cwd": None,
        "songryeon_record_found": False,
        "instrumentation_status": "no_songryeon_record",
        "session_start_seen": False,
        "session_end_seen": False,
        "coverage_boundary": "absence_does_not_establish_plugin_was_absent",
    }

    cutoff = from_start_status["snapshot_max_sequence"]
    later = store.append_hook_event(_prompt(session="from-start", turn="later"))
    assert isinstance(cutoff, int)
    assert from_start_status["snapshot_last_event_id"] is not None
    assert later["sequence"] > cutoff
    assert store.search(session_id="from-start", max_sequence=cutoff)[0][
        "sequence"
    ] <= cutoff
    assert all(
        gap["sequence"] <= cutoff
        for gap in store.find_gaps("from-start", max_sequence=cutoff)
    )


def test_concurrent_writes_form_one_diagnosable_recording_chain(tmp_path):
    store = SongRyeonStore(tmp_path / "audit.sqlite3")

    def write(index):
        return store.append_hook_event(
            _prompt(turn=f"turn-{index}", prompt=f"concurrent prompt {index}")
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        events = list(executor.map(write, range(24)))

    assert len({event["event_id"] for event in events}) == 24
    ordered = sorted(store.search("concurrent prompt", limit=50), key=lambda item: item["sequence"])
    assert len(ordered) == 24
    assert ordered[0]["chain"]["previous_digest"] is None
    for previous, current in zip(ordered, ordered[1:]):
        assert current["chain"]["previous_digest"] == previous["chain"]["digest"]


def test_default_path_uses_plugin_data(monkeypatch, tmp_path):
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path))

    assert resolve_db_path().parent == tmp_path.resolve()


def test_installed_cache_path_maps_to_same_plugin_scoped_data_dir(tmp_path):
    module_path = (
        tmp_path
        / ".codex"
        / "plugins"
        / "cache"
        / "personal"
        / "songryeon-audit"
        / "0.1.0+codex.test"
        / "scripts"
        / "songryeon_store.py"
    )

    assert _installed_plugin_data_dir(module_path) == (
        tmp_path
        / ".codex"
        / "plugins"
        / "data"
        / "songryeon-audit-personal"
    ).resolve()


def test_noninstalled_source_path_has_no_derived_plugin_data_dir(tmp_path):
    module_path = tmp_path / "songryeon-audit" / "scripts" / "songryeon_store.py"

    assert _installed_plugin_data_dir(module_path) is None


def test_hook_process_is_silent_advisory_and_stop_returns_empty_json(tmp_path):
    hook = SCRIPTS / "songryeon_hook.py"
    environment = os.environ.copy()
    environment["PLUGIN_DATA"] = str(tmp_path)

    prompt_run = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(_prompt()),
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    stop_run = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(
            {
                "hook_event_name": "Stop",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "last_assistant_message": "Done",
                "stop_hook_active": False,
            }
        ),
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    bad_run = subprocess.run(
        [sys.executable, str(hook)],
        input="not-json",
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )

    assert prompt_run.returncode == 0
    assert prompt_run.stdout == ""
    assert prompt_run.stderr == ""
    assert stop_run.returncode == 0
    assert stop_run.stdout == "{}"
    assert stop_run.stderr == ""
    assert bad_run.returncode == 0
    assert bad_run.stdout == ""
    assert bad_run.stderr == ""
    stored = SongRyeonStore(tmp_path / "songryeon-audit.sqlite3").search(
        session_id="session-1"
    )
    assert len(stored) == 2
    success = json.loads(
        (tmp_path / "collector-last-success.json").read_text(encoding="utf-8")
    )
    error = json.loads(
        (tmp_path / "collector-last-error.json").read_text(encoding="utf-8")
    )
    assert success["status"] == "ok"
    assert success["hook_name"] == "Stop"
    assert success["content_recorded"] is False
    assert error["status"] == "error"
    assert error["error_type"] == "JSONDecodeError"
    assert error["content_recorded"] is False
    assert "not-json" not in json.dumps(error)


def test_health_marker_rejects_arbitrary_hook_name_content(tmp_path):
    hook = SCRIPTS / "songryeon_hook.py"
    environment = os.environ.copy()
    environment["PLUGIN_DATA"] = str(tmp_path)
    secret = "PROMPT_SECRET_must_not_enter_health_marker"
    payload = {
        "hook_event_name": secret,
        "session_id": "adversarial-session",
        "prompt": "ordinary stored R content",
    }

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=environment,
        timeout=4,
        check=False,
    )

    assert completed.returncode == 0
    marker_text = (tmp_path / "collector-last-success.json").read_text(
        encoding="utf-8"
    )
    marker = json.loads(marker_text)
    assert marker["hook_name"] == "Unknown"
    assert marker["content_recorded"] is False
    assert secret not in marker_text
    assert payload["prompt"] not in marker_text
    assert len(marker["session_scope_digest_sha256"]) == 64


def test_hook_with_lone_surrogate_session_id_stays_advisory(tmp_path):
    hook = SCRIPTS / "songryeon_hook.py"
    environment = os.environ.copy()
    environment["PLUGIN_DATA"] = str(tmp_path)
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "\ud800",
        "source": "startup",
    }

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(payload).encode("ascii"),
        capture_output=True,
        env=environment,
        timeout=4,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == b""
    assert completed.stderr == b""
    marker = json.loads(
        (tmp_path / "collector-last-error.json").read_text(encoding="utf-8")
    )
    assert marker["status"] == "error"
    assert marker["content_recorded"] is False
    assert marker["session_scope_digest_sha256"] is not None


def test_busy_store_does_not_outlive_the_three_second_hook_budget(tmp_path):
    hook = SCRIPTS / "songryeon_hook.py"
    db_path = tmp_path / "songryeon-audit.sqlite3"
    SongRyeonStore(db_path)
    environment = os.environ.copy()
    environment["PLUGIN_DATA"] = str(tmp_path)
    locker = sqlite3.connect(db_path, timeout=1.0)
    locker.execute("BEGIN IMMEDIATE")
    try:
        started = time.monotonic()
        completed = subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(_prompt(session="locked-session")),
            text=True,
            capture_output=True,
            env=environment,
            timeout=3.5,
            check=False,
        )
        elapsed = time.monotonic() - started
    finally:
        locker.rollback()
        locker.close()

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert elapsed < 3.0
    assert SongRyeonStore(db_path).get_session_status("locked-session")[
        "songryeon_record_found"
    ] is False
    error = json.loads(
        (tmp_path / "collector-last-error.json").read_text(encoding="utf-8")
    )
    assert error["status"] == "error"
    assert error["error_type"] == "OperationalError"
    assert error["content_recorded"] is False


def test_oversized_hook_input_records_content_free_health_error(tmp_path):
    hook = SCRIPTS / "songryeon_hook.py"
    environment = os.environ.copy()
    environment["PLUGIN_DATA"] = str(tmp_path)

    completed = subprocess.run(
        [sys.executable, str(hook)],
        input="x" * (8 * 1024 * 1024 + 1),
        text=True,
        capture_output=True,
        env=environment,
        timeout=4,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
    error = json.loads(
        (tmp_path / "collector-last-error.json").read_text(encoding="utf-8")
    )
    assert error == {
        "content_recorded": False,
        "error_type": "input_too_large",
        "hook_name": None,
        "input_bytes_observed": 8 * 1024 * 1024 + 1,
        "recorded_at": error["recorded_at"],
        "schema_version": "1",
        "session_scope_digest_sha256": None,
        "status": "error",
    }


def test_every_hook_launcher_is_isolated_and_disables_bytecode_writes():
    hook_config = json.loads(
        (PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
    )
    launchers = [
        command
        for groups in hook_config["hooks"].values()
        for group in groups
        for command in group["hooks"]
    ]

    assert launchers
    assert all("python3 -I -S -B " in item["command"] for item in launchers)
    assert all("python -I -S -B -c " in item["commandWindows"] for item in launchers)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows command regression")
def test_windows_hook_command_resolves_plugin_root_in_powershell(tmp_path):
    hook_config = json.loads(
        (PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
    )
    command = hook_config["hooks"]["SessionStart"][0]["hooks"][0][
        "commandWindows"
    ]
    environment = os.environ.copy()
    environment["PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    environment["PLUGIN_DATA"] = str(tmp_path)
    hostile_cwd = tmp_path / "hostile-cwd"
    hostile_cwd.mkdir()
    marker = tmp_path / "workspace-module-was-imported.txt"
    for module_name in ("runpy.py", "json.py", "sitecustomize.py"):
        (hostile_cwd / module_name).write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n",
            encoding="utf-8",
        )
    environment["PYTHONPATH"] = str(hostile_cwd)

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ],
        input=json.dumps(
            {
                "hook_event_name": "SessionStart",
                "session_id": "powershell-session",
                "source": "startup",
                "cwd": "C:/work",
                "model": "codex-test",
            }
        ),
        text=True,
        capture_output=True,
        env=environment,
        cwd=hostile_cwd,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert not marker.exists()
    status = SongRyeonStore(
        tmp_path / "songryeon-audit.sqlite3"
    ).get_session_status("powershell-session")
    assert status["instrumentation_status"] == "observed_from_session_start"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX command regression")
def test_posix_hook_command_ignores_hostile_cwd_and_pythonpath(tmp_path):
    hook_config = json.loads(
        (PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
    )
    command = hook_config["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    hostile_cwd = tmp_path / "hostile-cwd"
    hostile_cwd.mkdir()
    marker = tmp_path / "workspace-module-was-imported.txt"
    for module_name in ("json.py", "sitecustomize.py"):
        (hostile_cwd / module_name).write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe')\n",
            encoding="utf-8",
        )
    environment = os.environ.copy()
    environment["PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    environment["PLUGIN_DATA"] = str(tmp_path)
    environment["PYTHONPATH"] = str(hostile_cwd)

    completed = subprocess.run(
        ["/bin/sh", "-c", command],
        input=json.dumps(
            {
                "hook_event_name": "SessionStart",
                "session_id": "posix-session",
                "source": "startup",
                "cwd": "/work",
            }
        ),
        text=True,
        capture_output=True,
        env=environment,
        cwd=hostile_cwd,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert not marker.exists()
    status = SongRyeonStore(
        tmp_path / "songryeon-audit.sqlite3"
    ).get_session_status("posix-session")
    assert status["instrumentation_status"] == "observed_from_session_start"
