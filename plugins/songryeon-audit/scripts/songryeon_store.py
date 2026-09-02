"""Local evidence store for the SongRyeon Codex audit prototype.

The store deliberately labels *atoms*, not whole events. Runtime envelope
observations are recorded as A; semantic content from people, models, documents,
and generic tool responses remains R. The SQLite transaction and SHA-256
record chain make interrupted or concurrent writes diagnosable.  They are not a
tamper-proof guarantee.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Mapping
from uuid import uuid4
from datetime import datetime, timezone


SCHEMA_VERSION = "songryeon.audit.v0"
CHAIN_ALGORITHM = "sha256-linked-recording-order-v0"
CHAIN_GUARANTEE = "diagnostic_only_not_tamper_proof"
DEFAULT_DB_NAME = "songryeon-audit.sqlite3"

STATUS_OBSERVED_FROM_START = "observed_from_session_start"
STATUS_OBSERVED_PARTIAL = "observed_partial_start_missing"
STATUS_NO_RECORD = "no_songryeon_record"
OBSERVED_COVERAGE_BOUNDARY = "hook_observation_only_not_complete_runtime_capture"
ABSENCE_COVERAGE_BOUNDARY = "absence_does_not_establish_plugin_was_absent"

MAX_STRING_CHARS = 16_384
MAX_COLLECTION_ITEMS = 200
MAX_DEPTH = 12
MAX_ATOM_BYTES = 65_536
MAX_QUERY_LIMIT = 500
DEFAULT_SCOPED_SEQUENCE_WINDOW = 5_000
MAX_SCOPED_SEQUENCE_WINDOW = 50_000
SQLITE_BUSY_TIMEOUT_MS = 1_000

_SENSITIVE_KEYS = re.compile(
    r"(?i)(?:password|passwd|passphrase|api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|auth(?:orization)?|bearer|secret|client[_-]?secret|"
    r"private[_-]?key|cookie|session[_-]?token|aws[_-]?(?:access[_-]?key[_-]?id|"
    r"secret[_-]?access[_-]?key|session[_-]?token))"
)
_PRIVACY_PATTERNS = (
    (
        re.compile(
            r"(?i)\b(?P<scheme>[a-z][a-z0-9+.-]{1,20}://)"
            r"[^/\s:@]+:[^@\s/]+@"
        ),
        r"\g<scheme>[REDACTED]@",
    ),
    (
        re.compile(r"(?i)\b[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s\"']+"),
        "[USER_HOME]",
    ),
    (
        re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s\"']+"),
        "[USER_HOME]",
    ),
    (
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        "[REDACTED:email]",
    ),
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]+=*"),
    re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/]{8,}={0,2}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(
        r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\."
        r"[A-Za-z0-9_-]{5,}\b"
    ),
    re.compile(
        r"(?is)-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?"
        r"-----END [^-\r\n]*PRIVATE KEY-----"
    ),
    re.compile(
        r"(?i)\b(?P<key>password|passwd|passphrase|token|api[_-]?key|secret|"
        r"aws[_-]?(?:access[_-]?key[_-]?id|secret[_-]?access[_-]?key|"
        r"session[_-]?token))(?P<sep>\s*[:=]\s*)(?P<value>[^\s;&,]+)"
    ),
)

_COMMON_A_FIELDS = {
    "session_id",
    "turn_id",
    "cwd",
    "hook_event_name",
    "model",
    "permission_mode",
    "transcript_path",
    "tool_name",
    "tool_use_id",
    "source",
    "reason",
    "trigger",
    "agent_id",
    "agent_type",
    "agent_transcript_path",
    "stop_hook_active",
}
_SEMANTIC_R_FIELDS = {
    "prompt",
    "tool_input",
    "last_assistant_message",
}
_TURN_SCOPED_HOOKS = {
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "Stop",
}
_TOOL_HOOKS = {"PreToolUse", "PostToolUse"}
_KNOWN_HOOKS = {
    "SessionStart",
    "SessionEnd",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "Stop",
}
_KNOWN_PAYLOAD_FIELDS = (
    _COMMON_A_FIELDS
    | _SEMANTIC_R_FIELDS
    | {"actor", "actor_id", "tool_response", "_collector_gap"}
)
_RECURSIVE_AUDIT_OMISSION = "[OMITTED:recursive-songryeon-audit-content]"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 64:
        return "[UNSERIALIZABLE:depth-limit]"
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, depth + 1) for item in value]
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _redact_string(value: str) -> tuple[str, int]:
    redacted = value
    count = 0
    for pattern, replacement in _PRIVACY_PATTERNS:
        redacted, matches = pattern.subn(replacement, redacted)
        count += matches
    for pattern in _SECRET_PATTERNS:
        if {"key", "sep", "value"}.issubset(pattern.groupindex):
            redacted, matches = pattern.subn(
                lambda match: (
                    f"{match.group('key')}{match.group('sep')}[REDACTED]"
                ),
                redacted,
            )
        else:
            redacted, matches = pattern.subn("[REDACTED]", redacted)
        count += matches
    return redacted, count


def _canonical_scope_cwd(
    value: Any, *, case_insensitive: bool | None = None
) -> str | None:
    """Normalize a raw or already-redacted cwd for exact scope comparison."""
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str):
        return None
    if case_insensitive is None:
        case_insensitive = bool(
            re.match(r"(?i)^[a-z]:[\\/]", value) or value.startswith("\\\\")
        )
    redacted, _ = _redact_string(value)
    normalized = re.sub(r"/+", "/", redacted.replace("\\", "/"))
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized.casefold() if case_insensitive else normalized


def _redact_value(
    value: Any,
    path: str = "$",
) -> tuple[Any, list[str]]:
    """Return a JSON-safe redacted copy and the redacted JSON paths."""
    value = _json_safe(value)
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        paths: list[str] = []
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if _SENSITIVE_KEYS.search(key):
                output[key] = "[REDACTED:sensitive-key]"
                paths.append(child_path)
                continue
            clean, child_paths = _redact_value(item, child_path)
            output[key] = clean
            paths.extend(child_paths)
        return output, paths
    if isinstance(value, list):
        output_list: list[Any] = []
        paths = []
        for index, item in enumerate(value):
            clean, child_paths = _redact_value(item, f"{path}[{index}]")
            output_list.append(clean)
            paths.extend(child_paths)
        return output_list, paths
    if isinstance(value, str):
        clean, count = _redact_string(value)
        return clean, [path] * count
    return value, []


def _truncate_value(value: Any, depth: int = 0) -> tuple[Any, bool]:
    """Bound stored previews without changing the separately recorded digest."""
    if depth >= MAX_DEPTH:
        return "[TRUNCATED:depth-limit]", True
    truncated = False
    if isinstance(value, str):
        if len(value) > MAX_STRING_CHARS:
            return value[:MAX_STRING_CHARS] + "…[TRUNCATED]", True
        return value, False
    if isinstance(value, list):
        items: list[Any] = []
        for item in value[:MAX_COLLECTION_ITEMS]:
            stored, child_truncated = _truncate_value(item, depth + 1)
            items.append(stored)
            truncated = truncated or child_truncated
        if len(value) > MAX_COLLECTION_ITEMS:
            items.append(
                {"_songryeon_omitted_items": len(value) - MAX_COLLECTION_ITEMS}
            )
            truncated = True
        candidate: Any = items
    elif isinstance(value, dict):
        candidate_dict: dict[str, Any] = {}
        entries = list(value.items())
        for key, item in entries[:MAX_COLLECTION_ITEMS]:
            stored, child_truncated = _truncate_value(item, depth + 1)
            candidate_dict[key] = stored
            truncated = truncated or child_truncated
        if len(entries) > MAX_COLLECTION_ITEMS:
            candidate_dict["_songryeon_omitted_fields"] = (
                len(entries) - MAX_COLLECTION_ITEMS
            )
            truncated = True
        candidate = candidate_dict
    else:
        return value, False

    serialized = _canonical_json(candidate)
    if len(serialized.encode("utf-8")) > MAX_ATOM_BYTES:
        preview = serialized.encode("utf-8")[: MAX_ATOM_BYTES - 256]
        preview_text = preview.decode("utf-8", errors="ignore")
        return {
            "_songryeon_json_preview": preview_text,
            "_songryeon_truncated": True,
        }, True
    return candidate, truncated


def _source_role(hook_name: str) -> str:
    if hook_name == "UserPromptSubmit":
        return "user_input"
    if hook_name in {"PreToolUse", "PermissionRequest"}:
        return "model_proposal_or_runtime_request"
    if hook_name == "PostToolUse":
        return "tool_result"
    if hook_name in {"Stop", "SubagentStop"}:
        return "model_output"
    return "runtime_lifecycle"


def _explicit_actor(payload: Mapping[str, Any]) -> tuple[str | None, str]:
    actor_id = payload.get("actor_id")
    if isinstance(actor_id, str) and actor_id.strip():
        return actor_id.strip(), "explicit"
    actor = payload.get("actor")
    if isinstance(actor, Mapping):
        nested_id = actor.get("id")
        if isinstance(nested_id, str) and nested_id.strip():
            return nested_id.strip(), "explicit"
    return None, "unknown"


def _is_songryeon_audit_tool(tool_name: str | None) -> bool:
    if not tool_name:
        return False
    normalized = tool_name.lower().replace("_", "-")
    return "songryeon" in normalized and any(
        operation in normalized
        for operation in (
            "search",
            "get-event",
            "trace",
            "list-sessions",
            "check-session",
            "find-gaps",
            "doctor",
        )
    )


def _omit_recursive_audit_content(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Avoid copying SongRyeon's own retrieved evidence back into the store."""
    output = dict(payload)
    tool_name = _string_or_none(output.get("tool_name"))
    omitted: list[str] = []
    if _is_songryeon_audit_tool(tool_name):
        for field in ("tool_input", "tool_response"):
            if field in output:
                output[field] = _RECURSIVE_AUDIT_OMISSION
                omitted.append(field)
    return output, omitted


def _installed_plugin_data_dir(module_path: Path | None = None) -> Path | None:
    """Map an installed plugin cache path to its plugin-scoped data directory."""
    resolved = (module_path or Path(__file__)).expanduser().resolve()
    for cache_dir in resolved.parents:
        if cache_dir.name != "cache" or cache_dir.parent.name != "plugins":
            continue
        relative_parts = resolved.relative_to(cache_dir).parts
        if len(relative_parts) < 5:
            return None
        marketplace_name, plugin_name = relative_parts[:2]
        if not marketplace_name or not plugin_name:
            return None
        return (
            cache_dir.parent
            / "data"
            / f"{plugin_name}-{marketplace_name}"
        ).resolve()
    return None


def resolve_db_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the local database path without creating it."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    plugin_data = os.environ.get("PLUGIN_DATA")
    if plugin_data:
        return (Path(plugin_data).expanduser() / DEFAULT_DB_NAME).resolve()
    installed_plugin_data = _installed_plugin_data_dir()
    if installed_plugin_data is not None:
        return (installed_plugin_data / DEFAULT_DB_NAME).resolve()
    local_data = os.environ.get("LOCALAPPDATA")
    if local_data:
        return (
            Path(local_data).expanduser()
            / "SongRyeon"
            / "Audit"
            / DEFAULT_DB_NAME
        ).resolve()
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return (
            Path(xdg_data).expanduser() / "songryeon-audit" / DEFAULT_DB_NAME
        ).resolve()
    return (
        Path.home() / ".local" / "share" / "songryeon-audit" / DEFAULT_DB_NAME
    ).resolve()


class SongRyeonStore:
    """Transactional local storage for captured Codex lifecycle events."""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = resolve_db_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000,
        )
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    schema_version TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    hook_name TEXT NOT NULL,
                    session_id TEXT,
                    turn_id TEXT,
                    source_role TEXT NOT NULL,
                    actor_id TEXT,
                    actor_status TEXT NOT NULL,
                    tool_name TEXT,
                    tool_use_id TEXT,
                    payload_bytes INTEGER NOT NULL,
                    payload_digest TEXT NOT NULL,
                    payload_digest_scope TEXT NOT NULL,
                    redaction_count INTEGER NOT NULL,
                    truncation_count INTEGER NOT NULL,
                    prev_chain_digest TEXT,
                    chain_digest TEXT,
                    chain_algorithm TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS atoms (
                    atom_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    authority TEXT NOT NULL CHECK(authority IN ('A', 'R')),
                    value_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    note TEXT NOT NULL,
                    redacted INTEGER NOT NULL,
                    truncated INTEGER NOT NULL,
                    original_bytes INTEGER NOT NULL,
                    stored_bytes INTEGER NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS event_links (
                    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    target_event_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    UNIQUE(event_id, target_event_id, relation),
                    FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS coverage_gaps (
                    gap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    gap_kind TEXT NOT NULL,
                    path TEXT,
                    detail TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(event_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_events_session_seq
                    ON events(session_id, seq);
                CREATE INDEX IF NOT EXISTS idx_events_turn_seq
                    ON events(session_id, turn_id, seq);
                CREATE INDEX IF NOT EXISTS idx_events_tool_use
                    ON events(session_id, tool_use_id, seq);
                CREATE INDEX IF NOT EXISTS idx_atoms_event
                    ON atoms(event_id, atom_id);
                CREATE INDEX IF NOT EXISTS idx_links_event
                    ON event_links(event_id);
                CREATE INDEX IF NOT EXISTS idx_links_target
                    ON event_links(target_event_id);
                CREATE INDEX IF NOT EXISTS idx_gaps_event
                    ON coverage_gaps(event_id);
                """
            )

    @staticmethod
    def _atom(
        path: str,
        authority: str,
        value: Any,
        source: str,
        note: str,
        redacted_paths: Iterable[str] = (),
    ) -> dict[str, Any]:
        original_json = _canonical_json(value)
        stored_value, truncated = _truncate_value(value)
        stored_json = _canonical_json(stored_value)
        atom_paths = {path, f"$.{path}"}
        redacted = any(
            redacted_path == atom_path
            or redacted_path.startswith(atom_path + ".")
            or redacted_path.startswith(atom_path + "[")
            for redacted_path in redacted_paths
            for atom_path in atom_paths
        )
        return {
            "path": path,
            "authority": authority,
            "value": stored_value,
            "value_json": stored_json,
            "source": source,
            "note": note,
            "redacted": redacted,
            "truncated": truncated,
            "original_bytes": len(original_json.encode("utf-8")),
            "stored_bytes": len(stored_json.encode("utf-8")),
        }

    def _build_atoms(
        self,
        payload: Mapping[str, Any],
        hook_name: str,
        occurred_at: str,
        payload_bytes: int,
        payload_digest: str,
        actor_id: str | None,
        actor_status: str,
        redacted_paths: list[str],
    ) -> list[dict[str, Any]]:
        atoms = [
            self._atom(
                "schema_version",
                "A",
                SCHEMA_VERSION,
                "songryeon_recorder",
                "Recorder schema observed at write time.",
            ),
            self._atom(
                "recorded_at",
                "A",
                occurred_at,
                "songryeon_recorder",
                "Recorder clock observation, not the semantic event's claimed time.",
            ),
            self._atom(
                "payload.present",
                "A",
                True,
                "songryeon_recorder",
                "A JSON object reached the collector.",
            ),
            self._atom(
                "payload.byte_count",
                "A",
                payload_bytes,
                "songryeon_recorder",
                "Canonical received JSON size before redaction.",
            ),
            self._atom(
                "payload.digest_sha256",
                "A",
                payload_digest,
                "songryeon_recorder",
                "Digest of the redacted, untruncated payload; not a truth claim about its content.",
            ),
            self._atom(
                "actor.identity_status",
                "A",
                actor_status,
                "songryeon_recorder",
                "Identity is explicit only when the hook payload supplies an actor id.",
            ),
        ]
        if actor_id is not None:
            atoms.append(
                self._atom(
                    "actor.id",
                    "R",
                    actor_id,
                    "explicit_actor_marker",
                    "Explicit marker content; the recorder does not verify the real-world identity.",
                    redacted_paths,
                )
            )

        for field in sorted(_COMMON_A_FIELDS):
            if field in payload:
                atoms.append(
                    self._atom(
                        field,
                        "A",
                        payload[field],
                        "hook_envelope",
                        "Runtime field observed in the Codex hook envelope.",
                        redacted_paths,
                    )
                )

        for field in sorted(_SEMANTIC_R_FIELDS):
            if field in payload:
                atoms.append(
                    self._atom(
                        field,
                        "R",
                        payload[field],
                        "semantic_payload",
                        "Semantic content is not made true by appearing in a runtime record.",
                        redacted_paths,
                    )
                )

        if "tool_response" in payload:
            response_omitted = (
                payload["tool_response"] == _RECURSIVE_AUDIT_OMISSION
            )
            response_json = _canonical_json(payload["tool_response"])
            atoms.append(
                self._atom(
                    "tool_response.present",
                    "A",
                    True,
                    "songryeon_recorder",
                    "A tool_response value reached the collector; its meaning remains R.",
                )
            )
            if not response_omitted:
                atoms.extend(
                    [
                    self._atom(
                        "tool_response.byte_count",
                        "A",
                        len(response_json.encode("utf-8")),
                        "songryeon_recorder",
                        "Size of the redacted response value observed by the recorder.",
                    ),
                    self._atom(
                        "tool_response.digest_sha256",
                        "A",
                        _sha256_text(response_json),
                        "songryeon_recorder",
                        "Digest of the redacted response value; not a truth claim about its fields.",
                    ),
                    ]
                )
            atoms.append(
                self._atom(
                    "tool_response.semantic_content",
                    "R",
                    payload["tool_response"],
                    "tool_output",
                    (
                        "SongRyeon's own retrieved content was omitted by capture policy."
                        if response_omitted
                        else "The complete tool output remains R, including status-like claims."
                    ),
                    redacted_paths,
                )
            )

        return atoms

    @staticmethod
    def _build_gaps(
        payload: Mapping[str, Any],
        hook_name: str,
        actor_status: str,
        redacted_paths: list[str],
        atoms: list[dict[str, Any]],
        hook_name_mismatch: str | None,
        recursive_omitted_fields: list[str],
    ) -> list[dict[str, str | None]]:
        gaps: list[dict[str, str | None]] = []

        def add(kind: str, detail: str, path: str | None = None) -> None:
            gaps.append({"gap_kind": kind, "path": path, "detail": detail})

        if actor_status == "unknown":
            add(
                "actor_identity_unknown",
                "The hook envelope did not explicitly identify the human actor; identity was not inferred.",
                "actor.id",
            )
        if not payload.get("session_id"):
            add("missing_session_id", "No session_id was observed.", "session_id")
        if hook_name in _TURN_SCOPED_HOOKS and not payload.get("turn_id"):
            add("missing_turn_id", "No turn_id was observed for a turn-scoped hook.", "turn_id")
        if hook_name in _TOOL_HOOKS and not payload.get("tool_use_id"):
            add(
                "missing_tool_use_id",
                "No tool_use_id was observed, so proposal/result pairing may be incomplete.",
                "tool_use_id",
            )
        if hook_name not in _KNOWN_HOOKS:
            add(
                "unknown_hook_event",
                "The recorder has no event-specific capture contract for this hook name.",
                "hook_event_name",
            )
        if hook_name == "SessionStart":
            add(
                "tool_hook_coverage_partial",
                "Codex hosted tools and specialized opt-out paths are not guaranteed to emit Pre/PostToolUse hooks.",
                None,
            )
        if redacted_paths:
            add(
                "redacted_content_not_stored",
                f"Basic secret redaction replaced {len(redacted_paths)} value occurrence(s); this is not complete DLP.",
                redacted_paths[0],
            )
        for atom in atoms:
            if atom["truncated"]:
                add(
                    "payload_truncated",
                    "The stored preview was bounded; the redacted untruncated digest was retained.",
                    atom["path"],
                )
        if hook_name_mismatch:
            add("hook_name_mismatch", hook_name_mismatch, "hook_event_name")
        unknown_field_count = sum(
            key not in _KNOWN_PAYLOAD_FIELDS for key in payload
        )
        if unknown_field_count:
            add(
                "unclassified_payload_omitted",
                f"{unknown_field_count} unknown hook field value(s) were omitted by the allowlist capture policy.",
                None,
            )
        if recursive_omitted_fields:
            add(
                "recursive_audit_content_omitted",
                "SongRyeon's own MCP input/output content was omitted to prevent recursive evidence duplication.",
                recursive_omitted_fields[0],
            )
        collector_gap = payload.get("_collector_gap")
        if collector_gap:
            add("collector_gap", str(collector_gap), "_collector_gap")
        return gaps

    @staticmethod
    def _find_link_targets(
        connection: sqlite3.Connection,
        *,
        seq: int,
        hook_name: str,
        session_id: str | None,
        turn_id: str | None,
        tool_use_id: str | None,
    ) -> list[tuple[str, str]]:
        targets: list[tuple[str, str]] = []

        def add_rows(rows: Iterable[sqlite3.Row], relation: str) -> None:
            known = {(event_id, existing_relation) for event_id, existing_relation in targets}
            for row in rows:
                pair = (row["event_id"], relation)
                if pair not in known:
                    targets.append(pair)
                    known.add(pair)

        if session_id and turn_id and hook_name == "PreToolUse":
            rows = connection.execute(
                """
                SELECT event_id FROM events
                WHERE seq < ? AND session_id = ? AND turn_id = ?
                  AND hook_name = 'UserPromptSubmit'
                ORDER BY seq DESC LIMIT 1
                """,
                (seq, session_id, turn_id),
            ).fetchall()
            add_rows(rows, "same_turn_follows_prompt")

        if session_id and tool_use_id and hook_name == "PostToolUse":
            rows = connection.execute(
                """
                SELECT event_id FROM events
                WHERE seq < ? AND session_id = ? AND tool_use_id = ?
                  AND hook_name = 'PreToolUse'
                ORDER BY seq DESC LIMIT 1
                """,
                (seq, session_id, tool_use_id),
            ).fetchall()
            add_rows(rows, "tool_result_matches_proposal_id")

        if session_id and turn_id and hook_name in {"Stop", "SubagentStop"}:
            rows = connection.execute(
                """
                SELECT event_id FROM events
                WHERE seq < ? AND session_id = ? AND turn_id = ?
                ORDER BY seq DESC LIMIT 200
                """,
                (seq, session_id, turn_id),
            ).fetchall()
            add_rows(rows, "same_turn_precedes_stop")

        if session_id and hook_name == "SessionEnd":
            rows = connection.execute(
                """
                SELECT event_id FROM events
                WHERE seq < ? AND session_id = ?
                ORDER BY seq DESC LIMIT 1
                """,
                (seq, session_id),
            ).fetchall()
            add_rows(rows, "same_session_precedes_end")

        if not targets and session_id:
            if turn_id:
                rows = connection.execute(
                    """
                    SELECT event_id FROM events
                    WHERE seq < ? AND session_id = ? AND turn_id = ?
                    ORDER BY seq DESC LIMIT 1
                    """,
                    (seq, session_id, turn_id),
                ).fetchall()
                add_rows(rows, "same_turn_previous_capture")
            else:
                rows = connection.execute(
                    """
                    SELECT event_id FROM events
                    WHERE seq < ? AND session_id = ?
                    ORDER BY seq DESC LIMIT 1
                    """,
                    (seq, session_id),
                ).fetchall()
                add_rows(rows, "same_session_previous_capture")
        return targets

    def append_hook_event(
        self,
        payload: Mapping[str, Any],
        hook_name: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a JSON object")

        safe_payload = _json_safe(payload)
        assert isinstance(safe_payload, dict)
        supplied_hook_name = hook_name
        observed_hook_name = safe_payload.get("hook_event_name")
        if supplied_hook_name:
            resolved_hook_name = str(supplied_hook_name)
        elif isinstance(observed_hook_name, str) and observed_hook_name:
            resolved_hook_name = observed_hook_name
        else:
            resolved_hook_name = "Unknown"
        mismatch = None
        if (
            supplied_hook_name
            and isinstance(observed_hook_name, str)
            and observed_hook_name
            and supplied_hook_name != observed_hook_name
        ):
            mismatch = (
                f"Configured hook name {supplied_hook_name!r} differed from envelope "
                f"value {observed_hook_name!r}; the configured value was used."
            )

        raw_json = _canonical_json(safe_payload)
        payload_bytes = len(raw_json.encode("utf-8"))
        redacted_payload, redacted_paths = _redact_value(safe_payload)
        assert isinstance(redacted_payload, dict)
        payload_digest = _sha256_text(_canonical_json(redacted_payload))
        occurred_at = _utc_now()
        event_id = f"sra_{uuid4().hex}"
        stored_payload, recursive_omitted_fields = _omit_recursive_audit_content(
            redacted_payload
        )
        actor_id, actor_status = _explicit_actor(stored_payload)
        session_id = _string_or_none(stored_payload.get("session_id"))
        turn_id = _string_or_none(stored_payload.get("turn_id"))
        tool_name_value = _string_or_none(stored_payload.get("tool_name"))
        tool_use_id = _string_or_none(stored_payload.get("tool_use_id"))
        atoms = self._build_atoms(
            stored_payload,
            resolved_hook_name,
            occurred_at,
            payload_bytes,
            payload_digest,
            actor_id,
            actor_status,
            redacted_paths,
        )
        gaps = self._build_gaps(
            stored_payload,
            resolved_hook_name,
            actor_status,
            redacted_paths,
            atoms,
            mismatch,
            recursive_omitted_fields,
        )
        truncation_count = sum(bool(atom["truncated"]) for atom in atoms)

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT chain_digest FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            previous_digest = previous["chain_digest"] if previous else None
            cursor = connection.execute(
                """
                INSERT INTO events (
                    event_id, schema_version, occurred_at, hook_name, session_id,
                    turn_id, source_role, actor_id, actor_status, tool_name,
                    tool_use_id, payload_bytes, payload_digest,
                    payload_digest_scope, redaction_count, truncation_count,
                    prev_chain_digest, chain_digest, chain_algorithm
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    event_id,
                    SCHEMA_VERSION,
                    occurred_at,
                    resolved_hook_name,
                    session_id,
                    turn_id,
                    _source_role(resolved_hook_name),
                    actor_id,
                    actor_status,
                    tool_name_value,
                    tool_use_id,
                    payload_bytes,
                    payload_digest,
                    "redacted_untruncated_payload",
                    len(redacted_paths),
                    truncation_count,
                    previous_digest,
                    CHAIN_ALGORITHM,
                ),
            )
            seq = int(cursor.lastrowid)
            link_targets = self._find_link_targets(
                connection,
                seq=seq,
                hook_name=resolved_hook_name,
                session_id=session_id,
                turn_id=turn_id,
                tool_use_id=tool_use_id,
            )
            chain_record = {
                "sequence": seq,
                "event_id": event_id,
                "schema_version": SCHEMA_VERSION,
                "occurred_at": occurred_at,
                "hook_name": resolved_hook_name,
                "session_id": session_id,
                "turn_id": turn_id,
                "source_role": _source_role(resolved_hook_name),
                "actor_id": actor_id,
                "actor_status": actor_status,
                "tool_name": tool_name_value,
                "tool_use_id": tool_use_id,
                "payload_bytes": payload_bytes,
                "payload_digest": payload_digest,
                "redaction_count": len(redacted_paths),
                "truncation_count": truncation_count,
                "previous_digest": previous_digest,
                "atoms": [
                    {
                        "path": atom["path"],
                        "authority": atom["authority"],
                        "value": atom["value"],
                        "source": atom["source"],
                        "note": atom["note"],
                        "redacted": atom["redacted"],
                        "truncated": atom["truncated"],
                    }
                    for atom in atoms
                ],
                "links": [
                    {"target_event_id": target, "relation": relation}
                    for target, relation in link_targets
                ],
                "coverage_gaps": gaps,
            }
            chain_digest = _sha256_text(_canonical_json(chain_record))
            connection.execute(
                "UPDATE events SET chain_digest = ? WHERE event_id = ?",
                (chain_digest, event_id),
            )
            connection.executemany(
                """
                INSERT INTO atoms (
                    event_id, path, authority, value_json, source, note,
                    redacted, truncated, original_bytes, stored_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event_id,
                        atom["path"],
                        atom["authority"],
                        atom["value_json"],
                        atom["source"],
                        atom["note"],
                        int(atom["redacted"]),
                        int(atom["truncated"]),
                        atom["original_bytes"],
                        atom["stored_bytes"],
                    )
                    for atom in atoms
                ],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO event_links
                    (event_id, target_event_id, relation)
                VALUES (?, ?, ?)
                """,
                [
                    (event_id, target_event_id, relation)
                    for target_event_id, relation in link_targets
                ],
            )
            connection.executemany(
                """
                INSERT INTO coverage_gaps (event_id, gap_kind, path, detail)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (event_id, gap["gap_kind"], gap["path"], gap["detail"])
                    for gap in gaps
                ],
            )
            connection.commit()
        event = self.get_event(event_id)
        assert event is not None
        return event

    def _materialize(
        self, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> dict[str, Any]:
        atom_rows = connection.execute(
            "SELECT * FROM atoms WHERE event_id = ? ORDER BY atom_id",
            (row["event_id"],),
        ).fetchall()
        link_rows = connection.execute(
            """
            SELECT target_event_id, relation FROM event_links
            WHERE event_id = ? ORDER BY link_id
            """,
            (row["event_id"],),
        ).fetchall()
        gap_rows = connection.execute(
            """
            SELECT gap_kind, path, detail FROM coverage_gaps
            WHERE event_id = ? ORDER BY gap_id
            """,
            (row["event_id"],),
        ).fetchall()
        gaps = [dict(gap) for gap in gap_rows]
        return {
            "schema_version": row["schema_version"],
            "event_id": row["event_id"],
            "sequence": row["seq"],
            "occurred_at": row["occurred_at"],
            "hook_name": row["hook_name"],
            "session_id": row["session_id"],
            "turn_id": row["turn_id"],
            "source_role": row["source_role"],
            "actor": {"id": row["actor_id"], "status": row["actor_status"]},
            "tool_name": row["tool_name"],
            "tool_use_id": row["tool_use_id"],
            "payload": {
                "byte_count": row["payload_bytes"],
                "digest_sha256": row["payload_digest"],
                "digest_scope": row["payload_digest_scope"],
                "redaction_count": row["redaction_count"],
                "truncation_count": row["truncation_count"],
            },
            "atoms": [
                {
                    "path": atom["path"],
                    "authority": atom["authority"],
                    "value": json.loads(atom["value_json"]),
                    "source": atom["source"],
                    "note": atom["note"],
                    "redacted": bool(atom["redacted"]),
                    "truncated": bool(atom["truncated"]),
                    "original_bytes": atom["original_bytes"],
                    "stored_bytes": atom["stored_bytes"],
                }
                for atom in atom_rows
            ],
            "links": [dict(link) for link in link_rows],
            "coverage": {
                "status": "partial" if gaps else "captured",
                "gaps": gaps,
            },
            "chain": {
                "algorithm": row["chain_algorithm"],
                "previous_digest": row["prev_chain_digest"],
                "digest": row["chain_digest"],
                "guarantee": CHAIN_GUARANTEE,
            },
        }

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
            return self._materialize(connection, row) if row else None

    def search(
        self,
        query: str = "",
        session_id: str | None = None,
        limit: int = 50,
        max_sequence: int | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        needle = f"%{query}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT e.* FROM events e
                WHERE (? IS NULL OR e.session_id = ?)
                  AND (? IS NULL OR e.seq <= ?)
                  AND (
                    ? = '' OR e.event_id LIKE ? OR e.hook_name LIKE ?
                    OR COALESCE(e.tool_name, '') LIKE ?
                    OR COALESCE(e.tool_use_id, '') LIKE ?
                    OR EXISTS (
                        SELECT 1 FROM atoms a
                        WHERE a.event_id = e.event_id AND a.value_json LIKE ?
                    )
                  )
                ORDER BY e.seq DESC
                LIMIT ?
                """,
                (
                    session_id,
                    session_id,
                    max_sequence,
                    max_sequence,
                    query,
                    needle,
                    needle,
                    needle,
                    needle,
                    needle,
                    safe_limit,
                ),
            ).fetchall()
            return [self._materialize(connection, row) for row in rows]

    def trace(
        self,
        event_id: str,
        direction: str = "both",
        depth: int = 2,
    ) -> dict[str, Any]:
        aliases = {"up": "ancestors", "down": "descendants"}
        resolved_direction = aliases.get(direction, direction)
        if resolved_direction not in {"ancestors", "descendants", "both"}:
            raise ValueError("direction must be ancestors, descendants, or both")
        safe_depth = max(0, min(int(depth), 20))
        with self._connect() as connection:
            root_row = connection.execute(
                "SELECT * FROM events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if root_row is None:
                return {
                    "event": None,
                    "ancestors": [],
                    "descendants": [],
                    "unresolved_links": [],
                    "direction": resolved_direction,
                    "depth": safe_depth,
                }

            unresolved: list[dict[str, str]] = []

            def walk(start: str, reverse: bool) -> list[sqlite3.Row]:
                frontier = [start]
                visited = {start}
                output: list[sqlite3.Row] = []
                for _ in range(safe_depth):
                    next_frontier: list[str] = []
                    for current in frontier:
                        if reverse:
                            link_rows = connection.execute(
                                """
                                SELECT event_id AS candidate, relation
                                FROM event_links WHERE target_event_id = ?
                                ORDER BY link_id
                                """,
                                (current,),
                            ).fetchall()
                        else:
                            link_rows = connection.execute(
                                """
                                SELECT target_event_id AS candidate, relation
                                FROM event_links WHERE event_id = ?
                                ORDER BY link_id
                                """,
                                (current,),
                            ).fetchall()
                        for link in link_rows:
                            candidate = link["candidate"]
                            if candidate in visited:
                                continue
                            visited.add(candidate)
                            row = connection.execute(
                                "SELECT * FROM events WHERE event_id = ?",
                                (candidate,),
                            ).fetchone()
                            if row is None:
                                unresolved.append(
                                    {
                                        "from_event_id": current,
                                        "target_event_id": candidate,
                                        "relation": link["relation"],
                                    }
                                )
                            else:
                                output.append(row)
                                next_frontier.append(candidate)
                    frontier = next_frontier
                    if not frontier:
                        break
                return output

            ancestor_rows = (
                walk(event_id, reverse=False)
                if resolved_direction in {"ancestors", "both"}
                else []
            )
            descendant_rows = (
                walk(event_id, reverse=True)
                if resolved_direction in {"descendants", "both"}
                else []
            )
            return {
                "event": self._materialize(connection, root_row),
                "ancestors": [
                    self._materialize(connection, row) for row in ancestor_rows
                ],
                "descendants": [
                    self._materialize(connection, row) for row in descendant_rows
                ],
                "unresolved_links": unresolved,
                "direction": resolved_direction,
                "depth": safe_depth,
            }

    def list_sessions(
        self,
        limit: int = 20,
        cwd: str | os.PathLike[str] | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        if cwd is not None:
            return self.list_sessions_scoped(
                cwd=cwd,
                limit=safe_limit,
            )["sessions"]
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    e.session_id,
                    COUNT(*) AS event_count,
                    MIN(e.occurred_at) AS first_recorded_at,
                    MAX(e.occurred_at) AS last_recorded_at,
                    SUM(CASE WHEN e.actor_status = 'unknown' THEN 1 ELSE 0 END)
                        AS unknown_actor_count,
                    SUM((SELECT COUNT(*) FROM coverage_gaps g
                         WHERE g.event_id = e.event_id)) AS gap_count,
                    SUM(CASE WHEN e.hook_name = 'SessionStart' THEN 1 ELSE 0 END)
                        AS session_start_count,
                    SUM(CASE WHEN e.hook_name = 'SessionEnd' THEN 1 ELSE 0 END)
                        AS session_end_count,
                    (SELECT e1.event_id FROM events e1
                     WHERE e1.session_id IS e.session_id
                     ORDER BY e1.seq ASC LIMIT 1) AS first_event_id,
                    (SELECT e1.hook_name FROM events e1
                     WHERE e1.session_id IS e.session_id
                     ORDER BY e1.seq ASC LIMIT 1) AS first_hook_name,
                    (SELECT a1.value_json
                     FROM events e1
                     JOIN atoms a1 ON a1.event_id = e1.event_id
                     WHERE e1.session_id IS e.session_id
                       AND e1.hook_name = 'SessionStart'
                       AND a1.path = 'source'
                       AND e1.seq = (
                           SELECT MIN(e0.seq) FROM events e0
                           WHERE e0.session_id IS e.session_id
                       )
                     ORDER BY e1.seq ASC, a1.atom_id DESC LIMIT 1)
                        AS first_session_start_source_json,
                    (SELECT e2.event_id FROM events e2
                     WHERE e2.session_id IS e.session_id
                     ORDER BY e2.seq DESC LIMIT 1) AS last_event_id,
                    (SELECT a3.value_json
                     FROM events e3
                     JOIN atoms a3 ON a3.event_id = e3.event_id
                     WHERE e3.session_id IS e.session_id AND a3.path = 'cwd'
                     ORDER BY e3.seq DESC, a3.atom_id DESC LIMIT 1) AS last_cwd_json,
                    MAX(e.seq) AS last_seq
                FROM events e
                GROUP BY e.session_id
                ORDER BY last_seq DESC
                LIMIT ?
                """,
                (safe_limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "session_id": row["session_id"],
                    "event_count": row["event_count"],
                    "first_recorded_at": row["first_recorded_at"],
                    "last_recorded_at": row["last_recorded_at"],
                    "unknown_actor_count": row["unknown_actor_count"],
                    "gap_count": row["gap_count"] or 0,
                    "songryeon_record_found": True,
                    "instrumentation_status": (
                        STATUS_OBSERVED_FROM_START
                        if (
                            row["first_hook_name"] == "SessionStart"
                            and row["first_session_start_source_json"]
                            == '"startup"'
                        )
                        else STATUS_OBSERVED_PARTIAL
                    ),
                    "session_start_seen": bool(row["session_start_count"]),
                    "session_end_seen": bool(row["session_end_count"]),
                    "coverage_boundary": OBSERVED_COVERAGE_BOUNDARY,
                    "first_event_id": row["first_event_id"],
                    "first_hook_name": row["first_hook_name"],
                    "first_session_start_source": (
                        json.loads(row["first_session_start_source_json"])
                        if row["first_session_start_source_json"] is not None
                        else None
                    ),
                    "last_event_id": row["last_event_id"],
                    "cwd": (
                        json.loads(row["last_cwd_json"])
                        if row["last_cwd_json"] is not None
                        else None
                    ),
                }
                for row in rows
            ]

    def list_sessions_scoped(
        self,
        cwd: str | os.PathLike[str],
        limit: int = 20,
        sequence_window: int = DEFAULT_SCOPED_SEQUENCE_WINDOW,
    ) -> dict[str, Any]:
        """Find recent exact-cwd sessions with an explicit bounded scan receipt."""

        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        safe_window = max(
            1,
            min(int(sequence_window), MAX_SCOPED_SEQUENCE_WINDOW),
        )
        raw_cwd = os.fspath(cwd) if isinstance(cwd, os.PathLike) else cwd
        case_insensitive = bool(
            re.match(r"(?i)^[a-z]:[\\/]", raw_cwd)
            or raw_cwd.startswith("\\\\")
        )
        scoped_cwd = _canonical_scope_cwd(
            raw_cwd,
            case_insensitive=case_insensitive,
        )

        with self._connect() as connection:
            bounds = connection.execute(
                "SELECT MIN(seq) AS min_seq, MAX(seq) AS max_seq FROM events"
            ).fetchone()
            maximum_sequence = int(bounds["max_seq"] or 0)
            minimum_recorded_sequence = (
                int(bounds["min_seq"]) if bounds["min_seq"] is not None else None
            )
            minimum_included_sequence = max(
                1,
                maximum_sequence - safe_window + 1,
            )
            candidate_rows = connection.execute(
                """
                WITH candidate_sessions AS (
                    SELECT session_id, MAX(seq) AS last_seq
                    FROM events
                    WHERE seq BETWEEN ? AND ?
                      AND session_id IS NOT NULL
                    GROUP BY session_id
                )
                SELECT
                    candidate_sessions.session_id,
                    candidate_sessions.last_seq,
                    (SELECT a.value_json
                     FROM events e2
                     JOIN atoms a ON a.event_id = e2.event_id
                     WHERE e2.session_id = candidate_sessions.session_id
                       AND a.path = 'cwd'
                     ORDER BY e2.seq DESC, a.atom_id DESC LIMIT 1)
                        AS last_cwd_json
                FROM candidate_sessions
                ORDER BY candidate_sessions.last_seq DESC
                """,
                (minimum_included_sequence, maximum_sequence),
            ).fetchall()

        matching_session_ids: list[str] = []
        for row in candidate_rows:
            if row["last_cwd_json"] is None:
                continue
            stored_cwd = json.loads(row["last_cwd_json"])
            if (
                _canonical_scope_cwd(
                    stored_cwd,
                    case_insensitive=case_insensitive,
                )
                != scoped_cwd
            ):
                continue
            matching_session_ids.append(row["session_id"])
            if len(matching_session_ids) == safe_limit:
                break

        older_events_excluded = bool(
            minimum_recorded_sequence is not None
            and minimum_recorded_sequence < minimum_included_sequence
        )
        return {
            "sessions": [
                self.get_session_status(session_id)
                for session_id in matching_session_ids
            ],
            "scope_scan": {
                "bounded": True,
                "sequence_window": safe_window,
                "latest_sequence": maximum_sequence or None,
                "minimum_sequence_included": (
                    minimum_included_sequence if maximum_sequence else None
                ),
                "candidate_sessions_examined": len(candidate_rows),
                "older_events_excluded": older_events_excluded,
                "coverage_boundary": (
                    "recent_sequence_window_only_older_sessions_may_be_omitted"
                    if older_events_excluded
                    else "all_recorded_sequences_examined"
                ),
            },
        }

    def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Return metadata-only evidence about SongRyeon observation coverage.

        A missing row means only that this store has no record for the supplied
        identifier. It cannot establish that the plugin was absent, because the
        session may predate installation, belong to another store or device, or
        have failed before a hook record was written.
        """

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS event_count,
                    MAX(e.seq) AS snapshot_max_sequence,
                    MIN(e.occurred_at) AS first_recorded_at,
                    MAX(e.occurred_at) AS last_recorded_at,
                    SUM(CASE WHEN e.hook_name = 'SessionStart' THEN 1 ELSE 0 END)
                        AS session_start_count,
                    SUM(CASE WHEN e.hook_name = 'SessionEnd' THEN 1 ELSE 0 END)
                        AS session_end_count,
                    SUM(CASE WHEN e.actor_status = 'unknown' THEN 1 ELSE 0 END)
                        AS unknown_actor_count,
                    SUM((SELECT COUNT(*) FROM coverage_gaps g
                         WHERE g.event_id = e.event_id)) AS gap_count,
                    (SELECT e1.event_id FROM events e1
                     WHERE e1.session_id = ?
                     ORDER BY e1.seq ASC LIMIT 1) AS first_event_id,
                    (SELECT e1.hook_name FROM events e1
                     WHERE e1.session_id = ?
                     ORDER BY e1.seq ASC LIMIT 1) AS first_hook_name,
                    (SELECT a1.value_json
                     FROM events e1
                     JOIN atoms a1 ON a1.event_id = e1.event_id
                     WHERE e1.session_id = ?
                       AND e1.hook_name = 'SessionStart'
                       AND a1.path = 'source'
                       AND e1.seq = (
                           SELECT MIN(e0.seq) FROM events e0
                           WHERE e0.session_id = ?
                       )
                     ORDER BY e1.seq ASC, a1.atom_id DESC LIMIT 1)
                        AS first_session_start_source_json,
                    (SELECT e2.event_id FROM events e2
                     WHERE e2.session_id = ?
                     ORDER BY e2.seq DESC LIMIT 1) AS last_event_id,
                    (SELECT a3.value_json
                     FROM events e3
                     JOIN atoms a3 ON a3.event_id = e3.event_id
                     WHERE e3.session_id = ? AND a3.path = 'cwd'
                     ORDER BY e3.seq DESC, a3.atom_id DESC LIMIT 1) AS last_cwd_json
                FROM events e
                WHERE e.session_id = ?
                """,
                (
                    session_id,
                    session_id,
                    session_id,
                    session_id,
                    session_id,
                    session_id,
                    session_id,
                ),
            ).fetchone()

        event_count = int(row["event_count"] or 0)
        if event_count == 0:
            return {
                "session_id": session_id,
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
                "instrumentation_status": STATUS_NO_RECORD,
                "session_start_seen": False,
                "session_end_seen": False,
                "coverage_boundary": ABSENCE_COVERAGE_BOUNDARY,
            }

        session_start_seen = bool(row["session_start_count"])
        first_session_start_source = (
            json.loads(row["first_session_start_source_json"])
            if row["first_session_start_source_json"] is not None
            else None
        )
        observed_from_start = (
            row["first_hook_name"] == "SessionStart"
            and first_session_start_source == "startup"
        )
        return {
            "session_id": session_id,
            "event_count": event_count,
            "first_recorded_at": row["first_recorded_at"],
            "last_recorded_at": row["last_recorded_at"],
            "unknown_actor_count": row["unknown_actor_count"] or 0,
            "gap_count": row["gap_count"] or 0,
            "first_event_id": row["first_event_id"],
            "first_hook_name": row["first_hook_name"],
            "first_session_start_source": first_session_start_source,
            "last_event_id": row["last_event_id"],
            "snapshot_last_event_id": row["last_event_id"],
            "snapshot_max_sequence": row["snapshot_max_sequence"],
            "cwd": (
                json.loads(row["last_cwd_json"])
                if row["last_cwd_json"] is not None
                else None
            ),
            "songryeon_record_found": True,
            "instrumentation_status": (
                STATUS_OBSERVED_FROM_START
                if observed_from_start
                else STATUS_OBSERVED_PARTIAL
            ),
            "session_start_seen": session_start_seen,
            "session_end_seen": bool(row["session_end_count"]),
            "coverage_boundary": OBSERVED_COVERAGE_BOUNDARY,
        }

    def find_gaps(
        self,
        session_id: str | None = None,
        limit: int = 50,
        max_sequence: int | None = None,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), MAX_QUERY_LIMIT))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    g.gap_kind, g.path, g.detail,
                    e.event_id, e.session_id, e.turn_id, e.hook_name,
                    e.occurred_at, e.seq
                FROM coverage_gaps g
                JOIN events e ON e.event_id = g.event_id
                WHERE (? IS NULL OR e.session_id = ?)
                  AND (? IS NULL OR e.seq <= ?)
                ORDER BY e.seq DESC, g.gap_id
                LIMIT ?
                """,
                (session_id, session_id, max_sequence, max_sequence, safe_limit),
            ).fetchall()
            return [
                {
                    "event_id": row["event_id"],
                    "session_id": row["session_id"],
                    "turn_id": row["turn_id"],
                    "hook_name": row["hook_name"],
                    "occurred_at": row["occurred_at"],
                    "sequence": row["seq"],
                    "gap_kind": row["gap_kind"],
                    "path": row["path"],
                    "detail": row["detail"],
                }
                for row in rows
            ]


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


__all__ = [
    "CHAIN_ALGORITHM",
    "CHAIN_GUARANTEE",
    "SCHEMA_VERSION",
    "SongRyeonStore",
    "resolve_db_path",
]
