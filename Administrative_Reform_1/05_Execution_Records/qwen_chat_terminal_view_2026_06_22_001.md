# Qwen Chat Terminal View 2026-06-22 001

## Goal

Make SongRyeon usable as a rough terminal conversation loop while still showing the internal runtime work the user should see.

## Result

New commands:

```powershell
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --pretty
python main.py qwen-turn "document memory index" --timeout 120 --pretty --force-l
python main.py qwen-chat --timeout 120
```

## Terminal Output Policy

`qwen-turn` still returns JSON by default for machine-readable checks.

`--pretty` renders:

- `[runtime]`: concise internal processing that the user should see.
  - model and transport
  - status
  - trace/data counts
  - selected L2 query plan
  - search result count
  - top document candidates
  - read document
  - L3 achievement/controller status
- `[answer]`: user-facing answer generated from DataStore records, search results, read document payloads, and L3 achievement records.

The pretty answer does not print the full `Dry Run Report` or full absolute-info list.

## Chat Behavior

`qwen-chat` loops over user input until `/exit` or `/quit`.

For the MVP, `qwen-chat` forces the first route to L so that normal conversation attempts still use the internal-document lookup loop. This is a temporary bridge until node 1 routing becomes LLM-based.

## Code Changes

- `main.py`
  - Added `qwen-chat`.
  - Added `--pretty`.
  - Added `--force-l`.
  - Reconfigured stdin/stdout as UTF-8 when available.
- `songryeon_core/runtime/terminal_view.py`
  - Added runtime summary rendering.
  - Added chat answer rendering.
- `songryeon_core/runtime/user_turn.py`
  - Added optional `include_data_records`.
  - Added optional `force_l_route`.
- `songryeon_core/runtime/dry_run.py`
  - Added `force_l_route` to route MVP chat turns through L.

## Verification

- `python -m py_compile main.py songryeon_core\runtime\dry_run.py songryeon_core\runtime\user_turn.py songryeon_core\runtime\terminal_view.py`
- `python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --pretty`
- `python main.py qwen-turn "document memory index" --timeout 120 --pretty --force-l`
- `python main.py qwen-chat --timeout 120`
- `python main.py smoke-test`

Smoke result:

- `status: SMOKE_TEST_OK`
- `fake_turn_status: ok`
- `l2_mixed_tool_plan_normalized: true`
- `document_memory_index_docs: 124`

## Known Limits

- The final answer is deterministic rendering, not yet a dedicated Qwen reporter node.
- Turn IDs still use the old `turn_dry_001` naming.
- `qwen-chat` does not yet persist previous chat turns into 0state across process iterations.
- Routing is forced to L in chat mode until node 1 becomes LLM-based.
