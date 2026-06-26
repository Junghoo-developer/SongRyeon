# Order Batch LLM L Loop 2026-06-21 001

## 목적

사용자 요청에 따라 LLM 투입부터 L루프 자율 검색, 효율적 도구 사용, smoke/replay 검증까지 이어지는 정식 발주서 묶음을 만들었다.

## 추가한 발주서

- `ORDER_043_LLM_RUNTIME_ACTIVATION.md`: Qwen/Fake/off 런타임 선택과 Qwen ping.
- `ORDER_044_LLM_CALL_TRACE_AND_RETRY.md`: LLM 호출 trace/data 저장, JSON 파싱 실패, 스키마 실패, 재시도/fallback.
- `ORDER_045_L2_LLM_QUERY_PLANNER.md`: L2가 검색 query 후보를 LLM으로 계획.
- `ORDER_046_TOOL_CATALOG_AND_CHOICE_FRAME.md`: 도구 목록과 도구 선택을 스키마로 제공.
- `ORDER_047_AUTONOMOUS_L_LOOP_CONTROLLER.md`: L루프가 제한된 budget 안에서 검색/읽기/중단을 반복.
- `ORDER_048_TOOL_RESULT_DISTILLATION.md`: 도구 결과를 LLM이 읽기 좋은 작은 근거 프레임으로 압축.
- `ORDER_049_TOOL_EFFICIENCY_POLICY.md`: 중복 방지, budget, cache, 조기 중단 정책.
- `ORDER_050_LLM_L_LOOP_SMOKE_AND_REPLAY.md`: LLM L루프 smoke test와 replay 검증.

## 설계 판단

LLM은 도구를 직접 실행하지 않는다.  
LLM은 query plan, tool choice, loop control, distillation 같은 구조화 프레임을 만들고, 코드는 registry, schema, budget을 검증한 뒤 도구를 실행한다.

## 다음 실행 추천

1. ORDER 043으로 Qwen runtime gate를 먼저 만든다.
2. ORDER 044로 LLM call record와 retry/fallback을 만든다.
3. ORDER 045-047로 L2/L루프 자율 검색을 붙인다.
4. ORDER 048-050으로 효율과 검증을 다진다.
