"""Silent, advisory Codex lifecycle hook for SongRyeon Audit.

The collector never returns a blocking, rewriting, approval, or denial decision.
It best-effort records the JSON object received on stdin and always exits zero.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from songryeon_store import SongRyeonStore  # noqa: E402


_JSON_OUTPUT_HOOKS = {"Stop", "SubagentStop"}
_KNOWN_HEALTH_HOOKS = {
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "SubagentStart",
    "SubagentStop",
    "Stop",
}
MAX_HOOK_INPUT_BYTES = 8 * 1024 * 1024
_HEALTH_SCHEMA_VERSION = "1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _health_directory() -> Path | None:
    plugin_data = os.environ.get("PLUGIN_DATA")
    if plugin_data:
        return Path(plugin_data).expanduser().resolve()
    return None


def _session_scope_digest(session_id: str | None) -> str | None:
    """Hash a JSON-escaped identifier without assuming valid UTF-8 scalars."""

    if not isinstance(session_id, str) or not session_id:
        return None
    canonical = json.dumps(
        session_id,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


def _write_health_marker(
    status: str,
    *,
    hook_name: str | None,
    input_bytes: int,
    error_type: str | None = None,
    session_id: str | None = None,
) -> None:
    """Best-effort, content-free collector health outside the SQLite path.

    The recorder may be unable to open SQLite, so diagnostics cannot depend on
    the database they are intended to diagnose.  Only envelope metadata is
    retained; exception messages and hook payload content are deliberately
    excluded.
    """

    temporary: Path | None = None
    try:
        directory = _health_directory()
        if directory is None:
            return
        marker_name = (
            "collector-last-success.json"
            if status == "ok"
            else "collector-last-error.json"
        )
        marker = {
            "schema_version": _HEALTH_SCHEMA_VERSION,
            "recorded_at": _utc_now(),
            "status": status,
            "hook_name": (
                hook_name if hook_name in _KNOWN_HEALTH_HOOKS else "Unknown"
                if hook_name is not None
                else None
            ),
            "input_bytes_observed": input_bytes,
            "error_type": error_type,
            "content_recorded": False,
            "session_scope_digest_sha256": _session_scope_digest(session_id),
        }
        path = directory / marker_name
        temporary = directory / f".{marker_name}.{os.getpid()}.{uuid4().hex}.tmp"
        directory.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(marker, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    except Exception:
        try:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        except Exception:
            pass


def main() -> int:
    hook_name: str | None = None
    session_id: str | None = None
    raw = b""
    try:
        raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
        if len(raw) > MAX_HOOK_INPUT_BYTES:
            _write_health_marker(
                "error",
                hook_name=None,
                input_bytes=len(raw),
                error_type="input_too_large",
            )
            return 0
        payload = json.loads(raw.decode("utf-8"))
        if isinstance(payload, dict):
            observed = payload.get("hook_event_name")
            hook_name = observed if isinstance(observed, str) else None
            observed_session = payload.get("session_id")
            session_id = (
                observed_session
                if isinstance(observed_session, str) and observed_session
                else None
            )
            SongRyeonStore().append_hook_event(payload)
            _write_health_marker(
                "ok",
                hook_name=hook_name,
                input_bytes=len(raw),
                session_id=session_id,
            )
        else:
            _write_health_marker(
                "error",
                hook_name=None,
                input_bytes=len(raw),
                error_type="payload_not_object",
            )
    except Exception as exc:
        # Audit collection is advisory in v0.  It must not alter the agent's
        # permissions, output, or external actions even when storage fails.
        _write_health_marker(
            "error",
            hook_name=hook_name,
            input_bytes=len(raw),
            error_type=type(exc).__name__,
            session_id=session_id,
        )

    # Current Codex Stop/SubagentStop contracts expect JSON for successful
    # exit.  An empty object is model-silent and does not request continuation.
    if hook_name in _JSON_OUTPUT_HOOKS:
        sys.stdout.write("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
