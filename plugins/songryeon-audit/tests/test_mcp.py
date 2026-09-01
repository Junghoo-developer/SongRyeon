from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "songryeon_mcp.py"
STORE_PATH = SCRIPT_PATH.with_name("songryeon_store.py")
PLUGIN_ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("songryeon_mcp", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mcp)
STORE_SPEC = importlib.util.spec_from_file_location("songryeon_store", STORE_PATH)
assert STORE_SPEC is not None and STORE_SPEC.loader is not None
store_module = importlib.util.module_from_spec(STORE_SPEC)
STORE_SPEC.loader.exec_module(store_module)


def test_packaged_mcp_config_uses_current_plugin_schema_and_relative_paths() -> None:
    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert not (PLUGIN_ROOT / ".mcp.json").exists()
    server = manifest["mcpServers"]["songryeon-audit"]

    assert server["command"] == "python"
    assert server["args"] == ["-I", "-S", "-B", "scripts/songryeon_mcp.py"]
    assert server["cwd"] == "."
    assert "${PLUGIN_ROOT}" not in json.dumps(server)
    assert "${PLUGIN_DATA}" not in json.dumps(server)


def test_public_marketplace_points_to_packaged_plugin() -> None:
    repo_root = PLUGIN_ROOT.parents[1]
    marketplace = json.loads(
        (repo_root / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )

    assert marketplace["name"] == "songryeon"
    entry = next(
        plugin
        for plugin in marketplace["plugins"]
        if plugin["name"] == "songryeon-audit"
    )
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert entry["category"] == "Productivity"
    assert entry["source"]["source"] == "local"
    source_path = entry["source"]["path"]
    assert (repo_root / source_path).resolve() == PLUGIN_ROOT.resolve()


class FakeStore:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.event = {
            "event_id": "evt-1",
            "session_id": "session-1",
            "sequence": 10,
            "atoms": [
                {"classification": "A", "field": "hook_name", "value": "PostToolUse"},
                {"classification": "R", "field": "tool_content", "value": "claimed output"},
            ],
            "links": [
                {"target_event_id": "evt-parent", "relation": "same-session"},
                {"target_event_id": "evt-2", "relation": "cross-session"},
                {"target_event_id": "evt-missing", "relation": "unresolved"},
            ],
        }
        self.parent = {
            "event_id": "evt-parent",
            "session_id": "session-1",
            "sequence": 5,
            "atoms": [],
            "links": [],
        }
        self.other_event = {
            "event_id": "evt-2",
            "session_id": "session-2",
            "sequence": 11,
            "atoms": [{"authority": "R", "value": "other-session secret"}],
            "links": [],
        }

    def search(
        self,
        query: str = "",
        session_id: str | None = None,
        limit: int = 50,
        max_sequence: int | None = None,
    ):
        self.calls.append(("search", query, session_id, limit, max_sequence))
        # Deliberately ignore the requested scope so the MCP boundary is tested.
        return [self.event, self.other_event]

    def get_event(self, event_id: str):
        self.calls.append(("get_event", event_id))
        return {
            "evt-1": self.event,
            "evt-parent": self.parent,
            "evt-2": self.other_event,
        }.get(event_id)

    def trace(self, event_id: str, direction: str = "both", depth: int = 2):
        self.calls.append(("trace", event_id, direction, depth))
        return {
            "event": self.event if event_id == "evt-1" else None,
            "ancestors": [self.parent],
            "descendants": [self.other_event],
            "unresolved_links": [
                {
                    "from_event_id": "evt-1",
                    "target_event_id": "evt-missing",
                    "relation": "unresolved",
                },
                {
                    "from_event_id": "evt-2",
                    "target_event_id": "other-missing",
                    "relation": "other-session",
                },
            ],
            "direction": direction,
            "depth": depth,
        }

    def list_sessions(self, limit: int = 20):
        self.calls.append(("list_sessions", limit))
        return [
            {
                "session_id": "session-1",
                "event_count": 2,
                "cwd": "C:/work/one",
                "songryeon_record_found": True,
                "instrumentation_status": "observed_from_session_start",
                "session_start_seen": True,
                "session_end_seen": False,
                "coverage_boundary": "hook_observation_only_not_complete_runtime_capture",
                "events": [self.event],
            },
            {
                "session_id": "session-2",
                "event_count": 1,
                "cwd": "C:/work/two",
                "songryeon_record_found": True,
                "instrumentation_status": "observed_partial_start_missing",
                "session_start_seen": False,
                "session_end_seen": False,
                "coverage_boundary": "hook_observation_only_not_complete_runtime_capture",
                "events": [self.other_event],
            },
        ][:limit]

    def get_session_status(self, session_id: str):
        self.calls.append(("get_session_status", session_id))
        if session_id == "session-1":
            return {
                "session_id": "session-1",
                "event_count": 2,
                "first_recorded_at": "2026-08-31T00:00:00+00:00",
                "last_recorded_at": "2026-08-31T00:01:00+00:00",
                "gap_count": 1,
                "first_hook_name": "SessionStart",
                "first_session_start_source": "startup",
                "songryeon_record_found": True,
                "instrumentation_status": "observed_from_session_start",
                "session_start_seen": True,
                "session_end_seen": False,
                "coverage_boundary": "hook_observation_only_not_complete_runtime_capture",
                "snapshot_last_event_id": "evt-1",
                "snapshot_max_sequence": 10,
                "cwd": "C:/must-not-leak-from-check",
                "events": [self.event],
                "secret": "must-not-leak",
            }
        return {
            "session_id": session_id,
            "event_count": 0,
            "first_recorded_at": None,
            "last_recorded_at": None,
            "gap_count": 0,
            "first_hook_name": None,
            "first_session_start_source": None,
            "songryeon_record_found": False,
            "instrumentation_status": "no_songryeon_record",
            "session_start_seen": False,
            "session_end_seen": False,
            "coverage_boundary": "absence_does_not_establish_plugin_was_absent",
            "snapshot_last_event_id": None,
            "snapshot_max_sequence": None,
        }

    def find_gaps(
        self,
        session_id: str | None = None,
        limit: int = 50,
        max_sequence: int | None = None,
    ):
        self.calls.append(("find_gaps", session_id, limit, max_sequence))
        return [
            {
                "kind": "unresolved_link",
                "event_id": "evt-1",
                "session_id": "session-1",
                "sequence": 10,
            },
            {
                "kind": "redaction",
                "event_id": "evt-2",
                "session_id": "session-2",
                "sequence": 11,
                "detail": "other-session secret",
            },
        ][:limit]


def rpc(server, request_id: int, method: str, params: dict[str, Any] | None = None):
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return server.handle_message(message)


def test_lists_exact_read_only_tool_surface() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    response = rpc(server, 1, "tools/list")

    assert response["id"] == 1
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {
        "songryeon_search",
        "songryeon_get_event",
        "songryeon_trace",
        "songryeon_list_sessions",
        "songryeon_check_session",
        "songryeon_find_gaps",
    }
    assert not any(
        word in name for name in names for word in ("write", "delete", "verdict", "report")
    )
    assert all(
        tool["annotations"] == {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
        for tool in response["result"]["tools"]
    )


def test_tool_calls_return_structured_evidence_without_fixed_verdict() -> None:
    store = FakeStore()
    server = mcp.SongRyeonMCPServer(store)

    response = rpc(
        server,
        2,
        "tools/call",
        {
            "name": "songryeon_search",
            "arguments": {"query": "claimed", "session_id": "session-1", "limit": 7},
        },
    )

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["events"][0]["event_id"] == "evt-1"
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    assert store.calls == [("search", "claimed", "session-1", 7, None)]
    assert not ({"verdict", "root_cause", "explanation"} & result["structuredContent"].keys())


def test_content_tools_require_an_explicit_nonempty_session_scope() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    calls = [
        ("songryeon_search", {"query": "claimed"}),
        ("songryeon_get_event", {"event_id": "evt-1"}),
        ("songryeon_trace", {"event_id": "evt-1"}),
        ("songryeon_check_session", {}),
        ("songryeon_find_gaps", {}),
    ]

    for request_id, (name, arguments) in enumerate(calls, start=30):
        response = rpc(
            server,
            request_id,
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        assert response["error"]["code"] == -32602
        assert "session_id is required" in response["error"]["message"]

    empty = rpc(
        server,
        35,
        "tools/call",
        {
            "name": "songryeon_search",
            "arguments": {"session_id": ""},
        },
    )
    assert empty["error"]["code"] == -32602
    assert "session_id must not be empty" in empty["error"]["message"]


def test_mcp_boundary_filters_cross_session_search_get_trace_and_gaps() -> None:
    store = FakeStore()
    server = mcp.SongRyeonMCPServer(store)

    search = rpc(
        server,
        36,
        "tools/call",
        {
            "name": "songryeon_search",
            "arguments": {"query": "", "session_id": "session-1"},
        },
    )["result"]["structuredContent"]
    wrong_get = rpc(
        server,
        37,
        "tools/call",
        {
            "name": "songryeon_get_event",
            "arguments": {"event_id": "evt-2", "session_id": "session-1"},
        },
    )["result"]["structuredContent"]
    trace = rpc(
        server,
        38,
        "tools/call",
        {
            "name": "songryeon_trace",
            "arguments": {"event_id": "evt-1", "session_id": "session-1"},
        },
    )["result"]["structuredContent"]
    wrong_trace = rpc(
        server,
        39,
        "tools/call",
        {
            "name": "songryeon_trace",
            "arguments": {"event_id": "evt-2", "session_id": "session-1"},
        },
    )["result"]["structuredContent"]
    gaps = rpc(
        server,
        40,
        "tools/call",
        {
            "name": "songryeon_find_gaps",
            "arguments": {"session_id": "session-1"},
        },
    )["result"]["structuredContent"]

    assert [event["event_id"] for event in search["events"]] == ["evt-1"]
    assert wrong_get == {
        "event": None,
        "event_id": "evt-2",
        "session_id": "session-1",
        "found": False,
    }
    assert [event["event_id"] for event in trace["ancestors"]] == ["evt-parent"]
    assert trace["descendants"] == []
    assert {link["target_event_id"] for link in trace["event"]["links"]} == {
        "evt-parent",
        "evt-missing",
    }
    assert trace["unresolved_links"] == [
        {
            "from_event_id": "evt-1",
            "target_event_id": "evt-missing",
            "relation": "unresolved",
        }
    ]
    assert wrong_trace["found"] is False
    assert wrong_trace["event"] is None
    assert wrong_trace["ancestors"] == []
    assert wrong_trace["descendants"] == []
    assert gaps["gaps"] == [
        {
            "kind": "unresolved_link",
            "event_id": "evt-1",
            "session_id": "session-1",
            "sequence": 10,
        }
    ]
    assert "other-session secret" not in json.dumps(
        {"search": search, "get": wrong_get, "trace": trace, "gaps": gaps}
    )


def test_list_sessions_is_metadata_only_and_supports_exact_cwd_filter() -> None:
    store = FakeStore()
    server = mcp.SongRyeonMCPServer(store)

    definition = next(
        tool
        for tool in mcp.TOOL_DEFINITIONS
        if tool["name"] == "songryeon_list_sessions"
    )
    assert definition["inputSchema"]["required"] == ["cwd"]
    unscoped = rpc(
        server,
        40,
        "tools/call",
        {"name": "songryeon_list_sessions", "arguments": {"limit": 1}},
    )
    assert unscoped["error"]["code"] == -32602
    assert "cwd is required" in unscoped["error"]["message"]

    result = rpc(
        server,
        41,
        "tools/call",
        {
            "name": "songryeon_list_sessions",
            "arguments": {"cwd": "C:/work/two", "limit": 1},
        },
    )["result"]["structuredContent"]

    assert result == {
        "sessions": [
            {
                "session_id": "session-2",
                "event_count": 1,
                "cwd": "C:/work/two",
                "songryeon_record_found": True,
                "instrumentation_status": "observed_partial_start_missing",
                "session_start_seen": False,
                "session_end_seen": False,
                "coverage_boundary": "hook_observation_only_not_complete_runtime_capture",
            }
        ],
        "count": 1,
        "cwd": "C:/work/two",
    }
    assert store.calls == [("list_sessions", 200)]
    assert "events" not in result["sessions"][0]


def test_check_session_returns_a_narrow_receipt_and_an_epistemic_no_record() -> None:
    store = FakeStore()
    server = mcp.SongRyeonMCPServer(store)

    found = rpc(
        server,
        42,
        "tools/call",
        {
            "name": "songryeon_check_session",
            "arguments": {"session_id": "session-1"},
        },
    )["result"]["structuredContent"]
    missing = rpc(
        server,
        43,
        "tools/call",
        {
            "name": "songryeon_check_session",
            "arguments": {"session_id": "missing"},
        },
    )["result"]["structuredContent"]

    assert found == {
        "session_id": "session-1",
        "event_count": 2,
        "first_recorded_at": "2026-08-31T00:00:00+00:00",
        "last_recorded_at": "2026-08-31T00:01:00+00:00",
        "gap_count": 1,
        "first_hook_name": "SessionStart",
        "first_session_start_source": "startup",
        "songryeon_record_found": True,
        "instrumentation_status": "observed_from_session_start",
        "session_start_seen": True,
        "session_end_seen": False,
        "coverage_boundary": "hook_observation_only_not_complete_runtime_capture",
        "snapshot_last_event_id": "evt-1",
        "snapshot_max_sequence": 10,
    }
    assert missing["instrumentation_status"] == "no_songryeon_record"
    assert missing["songryeon_record_found"] is False
    assert missing["coverage_boundary"] == (
        "absence_does_not_establish_plugin_was_absent"
    )
    serialized = json.dumps({"found": found, "missing": missing})
    assert "must-not-leak" not in serialized
    assert "C:/must-not-leak-from-check" not in serialized
    assert store.calls == [
        ("get_session_status", "session-1"),
        ("get_session_status", "missing"),
    ]


def test_check_session_rejects_a_store_scope_mismatch_without_leaking_content() -> None:
    class MismatchedStore(FakeStore):
        def get_session_status(self, session_id: str):
            return {
                "session_id": "different-session",
                "songryeon_record_found": True,
                "instrumentation_status": "observed_from_session_start",
                "secret": "cross-session content",
            }

    server = mcp.SongRyeonMCPServer(MismatchedStore())
    response = rpc(
        server,
        44,
        "tools/call",
        {
            "name": "songryeon_check_session",
            "arguments": {"session_id": "session-1"},
        },
    )["result"]

    assert response["isError"] is True
    assert response["structuredContent"] == {
        "error": "store returned invalid session metadata"
    }
    assert "cross-session content" not in json.dumps(response)


def test_snapshot_cutoff_excludes_later_events_even_if_store_ignores_scope() -> None:
    class CutoffStore(FakeStore):
        def search(
            self,
            query: str = "",
            session_id: str | None = None,
            limit: int = 50,
            max_sequence: int | None = None,
        ):
            return [self.event, self.parent, self.other_event]

    server = mcp.SongRyeonMCPServer(CutoffStore())
    search = rpc(
        server,
        45,
        "tools/call",
        {
            "name": "songryeon_search",
            "arguments": {"session_id": "session-1", "max_sequence": 9},
        },
    )["result"]["structuredContent"]
    blocked_get = rpc(
        server,
        46,
        "tools/call",
        {
            "name": "songryeon_get_event",
            "arguments": {
                "event_id": "evt-1",
                "session_id": "session-1",
                "max_sequence": 9,
            },
        },
    )["result"]["structuredContent"]
    trace = rpc(
        server,
        47,
        "tools/call",
        {
            "name": "songryeon_trace",
            "arguments": {
                "event_id": "evt-1",
                "session_id": "session-1",
                "max_sequence": 10,
            },
        },
    )["result"]["structuredContent"]
    gaps = rpc(
        server,
        48,
        "tools/call",
        {
            "name": "songryeon_find_gaps",
            "arguments": {"session_id": "session-1", "max_sequence": 9},
        },
    )["result"]["structuredContent"]

    assert [event["event_id"] for event in search["events"]] == ["evt-parent"]
    assert search["max_sequence"] == 9
    assert blocked_get["found"] is False
    assert blocked_get["max_sequence"] == 9
    assert [event["event_id"] for event in trace["ancestors"]] == ["evt-parent"]
    assert trace["descendants"] == []
    assert trace["max_sequence"] == 10
    assert gaps["gaps"] == []
    assert gaps["max_sequence"] == 9


def test_event_not_found_is_evidence_not_protocol_failure() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    response = rpc(
        server,
        3,
        "tools/call",
        {
            "name": "songryeon_get_event",
            "arguments": {"event_id": "missing", "session_id": "session-1"},
        },
    )

    result = response["result"]
    assert result["isError"] is False
    assert result["structuredContent"] == {
        "event": None,
        "event_id": "missing",
        "session_id": "session-1",
        "found": False,
    }


def test_trace_and_gap_tools_preserve_unknowns() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    trace = rpc(
        server,
        4,
        "tools/call",
        {
            "name": "songryeon_trace",
            "arguments": {
                "event_id": "evt-1",
                "session_id": "session-1",
                "direction": "ancestors",
                "depth": 4,
            },
        },
    )["result"]["structuredContent"]
    gaps = rpc(
        server,
        5,
        "tools/call",
        {
            "name": "songryeon_find_gaps",
            "arguments": {"session_id": "session-1"},
        },
    )["result"]["structuredContent"]

    assert trace["unresolved_links"] == [
        {
            "from_event_id": "evt-1",
            "target_event_id": "evt-missing",
            "relation": "unresolved",
        }
    ]
    assert trace["direction"] == "ancestors"
    assert gaps["gaps"] == [
        {
            "kind": "unresolved_link",
            "event_id": "evt-1",
            "session_id": "session-1",
            "sequence": 10,
        }
    ]


def test_bad_tool_arguments_are_protocol_errors_and_server_stays_alive() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    bad = rpc(
        server,
        6,
        "tools/call",
        {
            "name": "songryeon_search",
            "arguments": {"session_id": "session-1", "limit": True},
        },
    )
    ping = rpc(server, 7, "ping")

    assert bad["error"]["code"] == -32602
    assert "integer" in bad["error"]["message"]
    assert ping == {"jsonrpc": "2.0", "id": 7, "result": {}}


def test_unknown_tool_is_a_protocol_error() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    response = rpc(
        server,
        8,
        "tools/call",
        {"name": "songryeon_fixed_verdict", "arguments": {}},
    )
    assert response["error"] == {
        "code": -32602,
        "message": "Unknown tool: songryeon_fixed_verdict",
    }


def test_stdio_initialize_notification_tools_and_parse_error() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    reader = io.StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 10,
                        "method": "initialize",
                        "params": {"protocolVersion": "2025-06-18"},
                    }
                ),
                json.dumps(
                    {"jsonrpc": "2.0", "method": "notifications/initialized"}
                ),
                json.dumps(
                    {"jsonrpc": "2.0", "id": 11, "method": "tools/list"}
                ),
                "{not-json",
                "",
            ]
        )
    )
    writer = io.StringIO()

    mcp.serve(server, reader, writer)
    responses = [json.loads(line) for line in writer.getvalue().splitlines()]

    assert len(responses) == 3  # notifications never receive a response
    assert responses[0]["result"]["protocolVersion"] == "2025-06-18"
    assert responses[0]["result"]["capabilities"] == {
        "tools": {"listChanged": False}
    }
    assert len(responses[1]["result"]["tools"]) == 6
    assert responses[2]["error"]["code"] == -32700


def test_stdio_unicode_response_survives_legacy_windows_writer() -> None:
    store = FakeStore()
    store.event["atoms"].append(
        {
            "classification": "R",
            "field": "tool_content",
            "value": "한국어 로그 🧪",
        }
    )
    server = mcp.SongRyeonMCPServer(store)
    reader = io.StringIO(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "songryeon_get_event",
                    "arguments": {
                        "session_id": "session-1",
                        "event_id": "evt-1",
                    },
                },
            }
        )
        + "\n"
    )
    output = io.BytesIO()
    writer = io.TextIOWrapper(output, encoding="cp949", errors="strict")

    mcp.serve(server, reader, writer)
    writer.flush()
    response = json.loads(output.getvalue().decode("cp949"))

    atoms = response["result"]["structuredContent"]["event"]["atoms"]
    assert atoms[-1]["value"] == "한국어 로그 🧪"


def test_unknown_method_uses_json_rpc_error() -> None:
    server = mcp.SongRyeonMCPServer(FakeStore())
    response = rpc(server, 12, "resources/list")
    assert response["error"]["code"] == -32601


def test_real_store_is_searchable_through_a_fresh_stdio_process(tmp_path: Path) -> None:
    db_path = tmp_path / "songryeon.sqlite3"
    store = store_module.SongRyeonStore(db_path)
    recorded = store.append_hook_event(
        {
            "session_id": "integration-session",
            "turn_id": "integration-turn",
            "prompt": "한국어 로그 🧪",
        },
        hook_name="UserPromptSubmit",
    )
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "songryeon_search",
                "arguments": {
                    "query": "한국어 로그 🧪",
                    "session_id": "integration-session",
                },
            },
        },
    ]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp949:strict"

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--db", str(db_path)],
        input="".join(json.dumps(item) + "\n" for item in requests),
        text=True,
        capture_output=True,
        env=environment,
        timeout=10,
        check=True,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]

    assert completed.stderr == ""
    assert len(responses) == 2
    result = responses[1]["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["count"] == 1
    assert result["structuredContent"]["events"][0]["event_id"] == recorded["event_id"]
