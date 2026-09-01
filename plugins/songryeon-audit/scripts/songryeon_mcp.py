"""Read-only stdio MCP server for the SongRyeon audit store.

The server deliberately exposes evidence, not a canned incident verdict.  A
Codex skill (or another MCP client) can use these primitives to reconstruct an
action for the user's actual question.  That reconstruction remains
model-generated relative information (R).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, TextIO


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


SERVER_NAME = "songryeon-audit"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"


class AuditStore(Protocol):
    """The read subset of ``SongRyeonStore`` used by this server."""

    def get_event(self, event_id: str) -> dict[str, Any] | None: ...

    def search(
        self,
        query: str = "",
        session_id: str = "",
        limit: int = 50,
        max_sequence: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def trace(
        self,
        event_id: str,
        direction: str = "both",
        depth: int = 2,
    ) -> dict[str, Any]: ...

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]: ...

    def get_session_status(self, session_id: str) -> dict[str, Any]: ...

    def find_gaps(
        self,
        session_id: str = "",
        limit: int = 50,
        max_sequence: int | None = None,
    ) -> list[dict[str, Any]]: ...


class InvalidToolArguments(ValueError):
    """The client supplied arguments outside the advertised input schema."""


class UnknownTool(LookupError):
    """The requested tool is not part of this server's fixed read surface."""


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "songryeon_search",
        "description": (
            "Search recorded SongRyeon events and atoms. Returns structured "
            "evidence only; it does not decide why the agent acted."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Free-text search term. Empty lists recent events only "
                        "inside the required session scope."
                    ),
                    "default": "",
                },
                "session_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Required exact session scope.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 50,
                },
                "max_sequence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9223372036854775807,
                    "description": (
                        "Optional immutable audit cutoff. Events recorded after "
                        "this sequence are excluded."
                    ),
                },
            },
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "songryeon_get_event",
        "description": (
            "Get one recorded event with its A/R atoms, links, and coverage "
            "metadata by event ID."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Exact SongRyeon event ID.",
                },
                "session_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Required exact session scope.",
                },
                "max_sequence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9223372036854775807,
                    "description": "Optional immutable audit cutoff.",
                },
            },
            "required": ["event_id", "session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "songryeon_trace",
        "description": (
            "Follow recorded links around an event. Returns ancestors, "
            "descendants, and unresolved links without inventing missing context."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "minLength": 1},
                "session_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Required exact session scope.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["ancestors", "descendants", "both"],
                    "default": "both",
                },
                "depth": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 20,
                    "default": 2,
                },
                "max_sequence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9223372036854775807,
                    "description": "Optional immutable audit cutoff.",
                },
            },
            "required": ["event_id", "session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "songryeon_list_sessions",
        "description": (
            "List metadata for recorded sessions whose working directory "
            "exactly matches the caller-supplied scope. Unfiltered local-session "
            "enumeration is intentionally unavailable."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 20,
                },
                "cwd": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Required exact working-directory scope.",
                },
            },
            "required": ["cwd"],
            "additionalProperties": False,
        },
    },
    {
        "name": "songryeon_check_session",
        "description": (
            "Check whether this local store contains SongRyeon records for one "
            "exact session ID, whether a startup SessionStart receipt was "
            "observed, and the current immutable snapshot cutoff. A missing "
            "record does not prove that the plugin was absent."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Exact session ID to check without reading event content.",
                }
            },
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "songryeon_find_gaps",
        "description": (
            "Find explicit capture, redaction, truncation, actor, and unresolved-"
            "link gaps. A gap is evidence of missing coverage, not evidence of "
            "what happened in the missing path."
        ),
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Required exact session scope.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 50,
                },
                "max_sequence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9223372036854775807,
                    "description": "Optional immutable audit cutoff.",
                },
            },
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
]


def _json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _tool_success(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": _json_text(payload)}],
        "structuredContent": payload,
        "isError": False,
    }


def _tool_error(message: str) -> dict[str, Any]:
    payload = {"error": message}
    return {
        "content": [{"type": "text", "text": _json_text(payload)}],
        "structuredContent": payload,
        "isError": True,
    }


def _require_object(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise InvalidToolArguments("arguments must be an object")
    return arguments


def _reject_extra(arguments: dict[str, Any], allowed: set[str]) -> None:
    extras = sorted(set(arguments) - allowed)
    if extras:
        raise InvalidToolArguments(f"unexpected argument(s): {', '.join(extras)}")


def _string(
    arguments: dict[str, Any],
    key: str,
    *,
    default: str | None = None,
    nullable: bool = False,
) -> str | None:
    if key not in arguments:
        return default
    value = arguments[key]
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise InvalidToolArguments(
            f"{key} must be a string" + (" or null" if nullable else "")
        )
    if default is None and not nullable and not value.strip():
        raise InvalidToolArguments(f"{key} must not be empty")
    return value


def _integer(
    arguments: dict[str, Any],
    key: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidToolArguments(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise InvalidToolArguments(f"{key} must be between {minimum} and {maximum}")
    return value


def _optional_integer(
    arguments: dict[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int | None:
    if key not in arguments:
        return None
    return _integer(
        arguments,
        key,
        default=minimum,
        minimum=minimum,
        maximum=maximum,
    )


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = _string(arguments, key)
    if value is None:
        raise InvalidToolArguments(f"{key} is required")
    return value


def _within_cutoff(value: Any, max_sequence: int | None) -> bool:
    if not isinstance(value, Mapping):
        return False
    if max_sequence is None:
        return True
    sequence = value.get("sequence")
    return (
        isinstance(sequence, int)
        and not isinstance(sequence, bool)
        and sequence <= max_sequence
    )


def _in_session(value: Any, session_id: str) -> bool:
    return isinstance(value, Mapping) and value.get("session_id") == session_id


def _empty_trace(
    *,
    event_id: str,
    session_id: str,
    direction: str,
    depth: int,
    max_sequence: int | None,
) -> dict[str, Any]:
    """Return a non-leaking not-found trace for the requested session scope."""

    payload = {
        "event": None,
        "ancestors": [],
        "descendants": [],
        "unresolved_links": [],
        "direction": direction,
        "depth": depth,
        "event_id": event_id,
        "session_id": session_id,
        "found": False,
    }
    if max_sequence is not None:
        payload["max_sequence"] = max_sequence
    return payload


SESSION_METADATA_KEYS = {
    "session_id",
    "event_count",
    "first_recorded_at",
    "last_recorded_at",
    "unknown_actor_count",
    "gap_count",
    "first_event_id",
    "first_hook_name",
    "first_session_start_source",
    "last_event_id",
    "cwd",
    "songryeon_record_found",
    "instrumentation_status",
    "session_start_seen",
    "session_end_seen",
    "coverage_boundary",
}

SESSION_STATUS_KEYS = {
    "session_id",
    "event_count",
    "first_recorded_at",
    "last_recorded_at",
    "gap_count",
    "first_hook_name",
    "first_session_start_source",
    "songryeon_record_found",
    "instrumentation_status",
    "session_start_seen",
    "session_end_seen",
    "coverage_boundary",
    "snapshot_last_event_id",
    "snapshot_max_sequence",
}


def _session_metadata(value: Any) -> dict[str, Any] | None:
    """Keep session discovery useful without returning event/atom content."""

    if not isinstance(value, Mapping):
        return None
    return {key: value[key] for key in SESSION_METADATA_KEYS if key in value}


def _session_status_metadata(value: Any) -> dict[str, Any] | None:
    """Return the narrow status receipt without paths or event content."""

    if not isinstance(value, Mapping):
        return None
    return {key: value[key] for key in SESSION_STATUS_KEYS if key in value}


class SongRyeonMCPServer:
    """Small JSON-RPC dispatcher around the read-only store API."""

    def __init__(self, store: AuditStore):
        self.store = store

    def call_tool(self, name: str, raw_arguments: Any) -> dict[str, Any]:
        try:
            arguments = _require_object(raw_arguments)

            if name == "songryeon_search":
                _reject_extra(
                    arguments, {"query", "session_id", "limit", "max_sequence"}
                )
                query = _string(arguments, "query", default="")
                session_id = _required_string(arguments, "session_id")
                limit = _integer(
                    arguments, "limit", default=50, minimum=1, maximum=200
                )
                max_sequence = _optional_integer(
                    arguments,
                    "max_sequence",
                    minimum=1,
                    maximum=9_223_372_036_854_775_807,
                )
                raw_events = self.store.search(
                    query=query or "",
                    session_id=session_id,
                    limit=limit,
                    max_sequence=max_sequence,
                )
                events = [
                    event
                    for event in raw_events
                    if _in_session(event, session_id)
                    and _within_cutoff(event, max_sequence)
                ]
                payload = {
                    "events": events,
                    "count": len(events),
                    "query": query or "",
                    "session_id": session_id,
                }
                if max_sequence is not None:
                    payload["max_sequence"] = max_sequence
                return _tool_success(payload)

            if name == "songryeon_get_event":
                _reject_extra(
                    arguments, {"event_id", "session_id", "max_sequence"}
                )
                event_id = _required_string(arguments, "event_id")
                session_id = _required_string(arguments, "session_id")
                max_sequence = _optional_integer(
                    arguments,
                    "max_sequence",
                    minimum=1,
                    maximum=9_223_372_036_854_775_807,
                )
                event = self.store.get_event(event_id)
                if not _in_session(event, session_id) or not _within_cutoff(
                    event, max_sequence
                ):
                    event = None
                payload = {
                    "event": event,
                    "event_id": event_id,
                    "session_id": session_id,
                    "found": event is not None,
                }
                if max_sequence is not None:
                    payload["max_sequence"] = max_sequence
                return _tool_success(payload)

            if name == "songryeon_trace":
                _reject_extra(
                    arguments,
                    {
                        "event_id",
                        "session_id",
                        "direction",
                        "depth",
                        "max_sequence",
                    },
                )
                event_id = _required_string(arguments, "event_id")
                session_id = _required_string(arguments, "session_id")
                direction = _string(arguments, "direction", default="both")
                if direction not in {"ancestors", "descendants", "both"}:
                    raise InvalidToolArguments(
                        "direction must be ancestors, descendants, or both"
                    )
                depth = _integer(
                    arguments, "depth", default=2, minimum=0, maximum=20
                )
                max_sequence = _optional_integer(
                    arguments,
                    "max_sequence",
                    minimum=1,
                    maximum=9_223_372_036_854_775_807,
                )
                scoped_root = self.store.get_event(event_id)
                if not _in_session(scoped_root, session_id) or not _within_cutoff(
                    scoped_root, max_sequence
                ):
                    return _tool_success(
                        _empty_trace(
                            event_id=event_id,
                            session_id=session_id,
                            direction=direction,
                            depth=depth,
                            max_sequence=max_sequence,
                        )
                    )

                raw_trace = self.store.trace(
                    event_id, direction=direction, depth=depth
                )
                root = raw_trace.get("event")
                if not _in_session(root, session_id) or not _within_cutoff(
                    root, max_sequence
                ):
                    return _tool_success(
                        _empty_trace(
                            event_id=event_id,
                            session_id=session_id,
                            direction=direction,
                            depth=depth,
                            max_sequence=max_sequence,
                        )
                    )

                ancestors = [
                    event
                    for event in raw_trace.get("ancestors", [])
                    if _in_session(event, session_id)
                    and _within_cutoff(event, max_sequence)
                ]
                descendants = [
                    event
                    for event in raw_trace.get("descendants", [])
                    if _in_session(event, session_id)
                    and _within_cutoff(event, max_sequence)
                ]
                scoped_events = [root, *ancestors, *descendants]
                scoped_ids = {
                    event.get("event_id")
                    for event in scoped_events
                    if isinstance(event.get("event_id"), str)
                }
                unresolved_links = [
                    link
                    for link in raw_trace.get("unresolved_links", [])
                    if isinstance(link, Mapping)
                    and link.get("from_event_id") in scoped_ids
                ]
                unresolved_targets = {
                    link.get("target_event_id")
                    for link in unresolved_links
                    if isinstance(link.get("target_event_id"), str)
                }

                def scoped_event(event: Mapping[str, Any]) -> dict[str, Any]:
                    materialized = dict(event)
                    links = event.get("links")
                    if isinstance(links, list):
                        materialized["links"] = [
                            dict(link)
                            for link in links
                            if isinstance(link, Mapping)
                            and link.get("target_event_id")
                            in (scoped_ids | unresolved_targets)
                        ]
                    return materialized

                trace = {
                    "event": scoped_event(root),
                    "ancestors": [scoped_event(event) for event in ancestors],
                    "descendants": [scoped_event(event) for event in descendants],
                    "unresolved_links": [dict(link) for link in unresolved_links],
                    "direction": direction,
                    "depth": depth,
                    "event_id": event_id,
                    "session_id": session_id,
                    "found": True,
                }
                if max_sequence is not None:
                    trace["max_sequence"] = max_sequence
                return _tool_success(trace)

            if name == "songryeon_list_sessions":
                _reject_extra(arguments, {"limit", "cwd"})
                limit = _integer(
                    arguments, "limit", default=20, minimum=1, maximum=200
                )
                cwd = _required_string(arguments, "cwd")
                raw_sessions = self.store.list_sessions(limit=200)
                sessions: list[dict[str, Any]] = []
                for raw_session in raw_sessions:
                    session = _session_metadata(raw_session)
                    if session is None:
                        continue
                    if session.get("cwd") != cwd:
                        continue
                    sessions.append(session)
                    if len(sessions) == limit:
                        break
                return _tool_success(
                    {"sessions": sessions, "count": len(sessions), "cwd": cwd}
                )

            if name == "songryeon_check_session":
                _reject_extra(arguments, {"session_id"})
                session_id = _required_string(arguments, "session_id")
                raw_status = self.store.get_session_status(session_id)
                status = _session_status_metadata(raw_status)
                if status is None or status.get("session_id") != session_id:
                    return _tool_error("store returned invalid session metadata")
                return _tool_success(status)

            if name == "songryeon_find_gaps":
                _reject_extra(
                    arguments, {"session_id", "limit", "max_sequence"}
                )
                session_id = _required_string(arguments, "session_id")
                limit = _integer(
                    arguments, "limit", default=50, minimum=1, maximum=200
                )
                max_sequence = _optional_integer(
                    arguments,
                    "max_sequence",
                    minimum=1,
                    maximum=9_223_372_036_854_775_807,
                )
                raw_gaps = self.store.find_gaps(
                    session_id=session_id,
                    limit=limit,
                    max_sequence=max_sequence,
                )
                gaps = [
                    gap
                    for gap in raw_gaps
                    if _in_session(gap, session_id)
                    and _within_cutoff(gap, max_sequence)
                ]
                payload = {
                    "gaps": gaps,
                    "count": len(gaps),
                    "session_id": session_id,
                }
                if max_sequence is not None:
                    payload["max_sequence"] = max_sequence
                return _tool_success(payload)

            raise UnknownTool(name)
        except (InvalidToolArguments, UnknownTool):
            raise
        except Exception as exc:  # keep the stdio server alive on store failures
            print(f"SongRyeon tool error ({name}): {exc}", file=sys.stderr)
            return _tool_error(f"store operation failed: {type(exc).__name__}")

    def handle_message(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "Invalid Request")

        request_id = message.get("id")
        method = message.get("method")
        is_notification = "id" not in message

        if not isinstance(method, str):
            if is_notification:
                return None
            return _rpc_error(request_id, -32600, "Invalid Request")

        if is_notification:
            # MCP lifecycle/cancellation notifications are acknowledgeless.  The
            # audit server has no mutable operation to cancel.
            return None

        params = message.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return _rpc_error(request_id, -32602, "Invalid params")

        if method == "initialize":
            requested = params.get("protocolVersion")
            protocol_version = (
                requested if isinstance(requested, str) and requested else DEFAULT_PROTOCOL_VERSION
            )
            return _rpc_result(
                request_id,
                {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": (
                        "These tools return recorded evidence, A/R atoms, links, and "
                        "coverage gaps. Content access requires an exact session_id; "
                        "use list_sessions and check_session only for metadata. A "
                        "missing record does not prove that SongRyeon was absent. Any causal "
                        "audit delegated after check_session must freeze its "
                        "snapshot_max_sequence and pass it as max_sequence. Any causal "
                        "reconstruction you generate is R; cite event IDs and state "
                        "unknowns."
                    ),
                },
            )

        if method == "ping":
            return _rpc_result(request_id, {})

        if method == "tools/list":
            return _rpc_result(request_id, {"tools": TOOL_DEFINITIONS})

        if method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str) or not name:
                return _rpc_error(request_id, -32602, "Invalid params: name is required")
            try:
                result = self.call_tool(name, params.get("arguments", {}))
            except UnknownTool:
                return _rpc_error(request_id, -32602, f"Unknown tool: {name}")
            except InvalidToolArguments as exc:
                return _rpc_error(request_id, -32602, f"Invalid arguments: {exc}")
            return _rpc_result(request_id, result)

        return _rpc_error(request_id, -32601, "Method not found")


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(
    request_id: Any,
    code: int,
    message: str,
    data: Any | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def serve(server: SongRyeonMCPServer, reader: TextIO, writer: TextIO) -> None:
    """Serve newline-delimited JSON-RPC until EOF."""

    for raw_line in reader:
        if not raw_line.strip():
            continue
        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            response = _rpc_error(
                None,
                -32700,
                "Parse error",
                {"line": exc.lineno, "column": exc.colno},
            )
        else:
            try:
                response = server.handle_message(message)
            except Exception as exc:  # defensive boundary: never corrupt stdout
                print(f"SongRyeon protocol error: {exc}", file=sys.stderr)
                response = _rpc_error(None, -32603, "Internal error")
        if response is not None:
            # JSON-RPC is Unicode, but Codex can launch this process with a
            # legacy Windows console encoding such as cp949. Keep the wire
            # representation ASCII-only so one emoji in a recorded payload
            # cannot terminate the MCP transport with UnicodeEncodeError.
            writer.write(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
            writer.write("\n")
            writer.flush()


def _load_store(explicit_path: str | os.PathLike[str] | None = None) -> AuditStore:
    # Import lazily so protocol tests can inject a fake without requiring a DB.
    from songryeon_store import SongRyeonStore

    if explicit_path is not None:
        return SongRyeonStore(Path(explicit_path))
    env_path = os.environ.get("SONGRYEON_AUDIT_DB")
    if env_path:
        return SongRyeonStore(Path(env_path))
    return SongRyeonStore()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SongRyeon read-only MCP server")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Explicit audit SQLite path (otherwise PLUGIN_DATA/default resolution is used).",
    )
    args = parser.parse_args(argv)
    # MCP stdio is UTF-8. Force that contract on Windows instead of inheriting
    # the active console code page. ``serve`` still emits ASCII-safe JSON so it
    # also remains robust when embedded with a caller-provided legacy writer.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")
    server = SongRyeonMCPServer(_load_store(args.db))
    serve(server, sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
