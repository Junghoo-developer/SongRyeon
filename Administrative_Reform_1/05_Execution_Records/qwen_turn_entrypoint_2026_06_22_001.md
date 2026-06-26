# Qwen Turn Entrypoint 2026-06-22 001

## Linked Orders

- `ORDER_043_LLM_RUNTIME_ACTIVATION.md`
- `ORDER_045_L2_LLM_QUERY_PLANNER.md`
- `ORDER_050_LLM_L_LOOP_SMOKE_AND_REPLAY.md`

## Result

Direct user-turn commands now exist.

```powershell
python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘"
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 60
```

`fake-turn` uses the deterministic fake L2 query planner so the command can be tested without a local model.

`qwen-turn` uses Qwen as the L2 query planner.

- If `QWEN_LOCAL_ENDPOINT` is configured, it uses an OpenAI-compatible HTTP endpoint.
- If no endpoint is configured, it follows the original `SongRyeon_Project` pattern and calls Ollama directly.
- The default local model is `qwen3:14b`.
- Adapter failures are returned as structured runtime results instead of crashing the whole turn.

## Code Changes

- `songryeon_core/runtime/user_turn.py`
  - Added `run_fake_user_turn`.
  - Added `run_qwen_user_turn`.
  - Added direct-turn JSON response with replay checks when `--export` is used.
- `main.py`
  - Added `fake-turn`.
  - Added `qwen-turn`.
  - Added turn budget options and `--include-report`.
- `songryeon_core/prompts/l2_query_setter_v0.md`
  - Strengthened the L2 JSON output instruction for Qwen-style local models.
- `songryeon_core/llm/qwen_adapter.py`
  - Added Ollama direct-call fallback when `QWEN_LOCAL_ENDPOINT` is not configured.
- `songryeon_core/llm/runtime.py`
  - Added `transport` reporting: `ollama` or `http`.
- `songryeon_core/nodes/l2_query_setter.py`
  - Normalizes Qwen L2 plans so only current-stage `search_docs` candidates remain.
- `songryeon_core/runtime/smoke_test.py`
  - Added fake-turn smoke coverage.
  - Added mixed-tool L2 plan normalization coverage.

## Verification

- `python -m py_compile main.py songryeon_core\runtime\user_turn.py songryeon_core\runtime\smoke_test.py`
- `python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘"`
- `python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 5`
- `python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --export Administrative_Reform_1/05_Execution_Records/runtime_runs/fake_turn_user_test_2026_06_22_001`
- `python main.py smoke-test`
- `python main.py qwen-ping --timeout 60`
- `python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --export Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_ollama_turn_test_2026_06_22_002`
- `python main.py replay Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_ollama_turn_test_2026_06_22_002`

Smoke result included:

- `fake_turn_status: ok`
- `fake_turn_query_source: llm_query_plan`
- `qwen_ping.status: ok`
- `qwen_ping.runtime.transport: ollama`
- `qwen_ping.model_id: qwen3:14b`
- `qwen_turn.status: ok`
- `qwen_turn.l2_query_source: llm_query_plan`
- `qwen_turn.l2_query_plan_present: true`
- `qwen_turn.l_loop_final_decision: stop_success`
- `qwen_turn.replay_has_llm_call: true`
- `qwen_turn.replay_has_controller: true`

## Qwen Test Sequence

Default Ollama path:

```powershell
python main.py qwen-ping --timeout 60
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --export Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_turn_user_test_001
python main.py replay Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_turn_user_test_001
```

Optional OpenAI-compatible HTTP endpoint path:

```powershell
$env:QWEN_LOCAL_ENDPOINT="http://localhost:8000/v1/chat/completions"
$env:QWEN_MODEL_ID="qwen3:14b"
```

Then test in this order:

```powershell
python main.py qwen-ping --timeout 20
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 60 --export Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_turn_user_test_001
python main.py replay Administrative_Reform_1/05_Execution_Records/runtime_runs/qwen_turn_user_test_001
```

## Notes

This is still not the final user-facing MVP report style. It is the direct test bridge needed before the success/failure review and cleanup phase.
