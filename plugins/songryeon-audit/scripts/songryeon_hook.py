"""Silent, advisory Codex lifecycle hook for SongRyeon Audit.

The collector never returns a blocking, rewriting, approval, or denial decision.
It best-effort records the JSON object received on stdin and always exits zero.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from songryeon_store import SongRyeonStore  # noqa: E402


_JSON_OUTPUT_HOOKS = {"Stop", "SubagentStop"}
MAX_HOOK_INPUT_BYTES = 8 * 1024 * 1024


def main() -> int:
    hook_name: str | None = None
    try:
        raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
        if len(raw) > MAX_HOOK_INPUT_BYTES:
            return 0
        payload = json.loads(raw.decode("utf-8"))
        if isinstance(payload, dict):
            observed = payload.get("hook_event_name")
            hook_name = observed if isinstance(observed, str) else None
            SongRyeonStore().append_hook_event(payload)
    except Exception:
        # Audit collection is advisory in v0.  It must not alter the agent's
        # permissions, output, or external actions even when storage fails.
        pass

    # Current Codex Stop/SubagentStop contracts expect JSON for successful
    # exit.  An empty object is model-silent and does not request continuation.
    if hook_name in _JSON_OUTPUT_HOOKS:
        sys.stdout.write("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
