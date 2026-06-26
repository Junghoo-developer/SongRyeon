# LLM L Loop Smoke And Replay 2026-06-22 001

**대상 발주서**: `ORDER_050_LLM_L_LOOP_SMOKE_AND_REPLAY.md`  
**성격**: 코드 구현 기록  
**결과**: smoke-test, Qwen skipped 경로, FakeLLM export/replay 확인

## 구현 요약

LLM이 들어간 L루프를 FakeLLM으로 deterministic하게 검증하고, export된 runtime artifact를 replay로 다시 읽을 수 있게 했다.  
Qwen 통합 검사는 endpoint가 없으면 구조 실패가 아니라 `skipped`로 반환된다.

## 코드 변경

1. `replay.py`
   - replay 출력에 run summary를 추가했다.
   - LLM call, tool choice, search/read tool result, distillation, budget, controller decision, L2 query plan, L3 achievement를 사람이 읽기 좋게 표시한다.

2. `dry_run.py`
   - export summary에 `llm_call_count`, `tool_result_count`, `tool_distillation_count`, `tool_budget_frame_count`, `l_loop_final_decision`, `l2_query_source`를 추가했다.

3. `l_loop_smoke.py`
   - `run_fake_llm_l_loop_smoke()`를 추가했다.
   - 규칙 기반 L루프와 FakeLLM L루프의 `query_source`, data record count, LLM call 존재 여부를 비교한다.
   - export된 artifact를 replay로 읽고 LLM/tool/controller/budget 표시가 있는지 확인한다.
   - `run_qwen_l_loop_smoke()`를 추가했다.

4. `smoke_test.py`
   - 기본 smoke-test에 FakeLLM L루프 export/replay 검증을 포함했다.

5. `main.py`
   - `qwen-l-loop-smoke` 명령을 추가했다.
   - endpoint가 없으면 `status=skipped`, `reason=endpoint_missing`을 반환한다.

## 생성한 runtime artifact

```text
Administrative_Reform_1/05_Execution_Records/runtime_runs/llm_l_loop_order050_2026_06_22_001
```

이 폴더에는 `trace.json`, `data.json`, `summary.json`, `report.md`가 있다.  
`python main.py replay <run_dir>`로 LLM L루프 동선을 다시 볼 수 있다.

## 검증

```text
python -m py_compile main.py songryeon_core\runtime\dry_run.py songryeon_core\runtime\replay.py songryeon_core\runtime\l_loop_smoke.py songryeon_core\runtime\smoke_test.py
python main.py qwen-l-loop-smoke
python main.py smoke-test
python main.py replay Administrative_Reform_1\05_Execution_Records\runtime_runs\llm_l_loop_order050_2026_06_22_001
```

검증 결과:

```text
qwen-l-loop-smoke: status=skipped, reason=endpoint_missing
smoke-test: status=SMOKE_TEST_OK
fake_llm_l_loop_status=FAKE_LLM_L_LOOP_OK
fake_llm_l_loop_replay_checked=True
```

FakeLLM L루프 export 결과:

```text
rule_query_source=user_input_fallback
llm_query_source=llm_query_plan
rule_data_record_count=29
llm_data_record_count=31
llm_call_count=1
l2_query_plan_present=True
l_loop_final_decision=stop_success
```

## 현재 한계

Qwen endpoint가 실제로 연결된 상태의 품질은 아직 검증하지 않았다.  
다만 endpoint가 없을 때와 모델 출력이 L2 query plan schema를 통과하지 못할 때를 구조 실패와 분리해서 볼 수 있는 준비는 끝났다.
