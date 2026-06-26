# ORDER 044: LLM Call Trace And Retry

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "llm 넣고" 후속 구조화  
**목표**: LLM 호출 자체를 trace/data로 남기고, JSON 파싱/스키마 검증 실패 시 재시도와 fallback을 표준화한다.

## 배경

현재 `LLMNodeExecutor`는 prompt, adapter, JSON 파싱을 묶지만 DataStore record를 남기지 않는다.  
LLM이 실제 흐름에 들어오면 "무슨 prompt를 줬고, 어떤 raw text가 왔고, 왜 실패했는지"가 추적되어야 한다.

## 범위

1. `LLMCallFrame` 또는 동등한 DataStore payload를 만든다.
2. LLM request의 node_id, prompt_ref, input_data_ids, model_id, response_format을 저장한다.
3. LLM response의 raw_text, parse_status, validation_status, retry_count를 저장한다.
4. JSON 파싱 실패와 스키마 실패를 구분한다.
5. 재시도 횟수 초과 시 규칙 기반 fallback 또는 failure signal로 넘긴다.

## 원칙

1. LLM raw output은 그대로 저장하되, 3 보고관이 자동으로 말할 수 있는 정보는 아니다.
2. LLM의 판단은 반드시 source trace/data ID를 가져야 한다.
3. 재시도 prompt도 trace에 남긴다.

## 완료 기준

1. FakeLLM 기준으로 LLM call record가 DataStore에 저장된다.
2. 잘못된 JSON을 반환하는 FakeLLM 테스트에서 재시도 또는 fallback이 기록된다.
3. 실패 원인이 `parse_failed`, `schema_failed`, `adapter_failed` 중 하나로 구분된다.
4. 기존 dry run과 smoke test가 통과한다.
