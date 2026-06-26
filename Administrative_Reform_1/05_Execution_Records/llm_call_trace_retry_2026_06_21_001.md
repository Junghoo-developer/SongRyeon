# LLM Call Trace And Retry 2026-06-21 001

## 목적

ORDER 044에 따라 LLM 호출 자체를 trace/data로 저장하고, JSON 파싱 실패 시 재시도 기록을 남기게 했다.

## 변경 내용

- `LLMCallFrame` 스키마와 검증 함수를 추가했다.
- `LLMNodeExecutor.run()`에 선택적 trace/data 저장 인자를 추가했다.
- LLM 호출 성공, JSON 파싱 실패, 스키마 실패, adapter 실패를 `failure_type`으로 구분한다.
- 깨진 JSON을 반환하는 `BrokenJSONFakeLLMAdapter`를 추가했다.
- smoke test가 FakeLLM 성공 1회와 깨진 JSON 재시도 2회를 확인한다.
- `LLMCallFrame`을 schema registry에 등록했다.

## 확인 결과

```text
python -m compileall -q songryeon_core
OK

python main.py smoke-test
SMOKE_TEST_OK
llm_call_records=3
llm_retry_failure_type=parse_failed
```

## 해석

이번 단계는 아직 특정 노드를 LLM으로 교체한 것이 아니다.

LLM이 호출될 때마다 어떤 노드가 어떤 prompt로 어떤 model을 불렀고, raw text가 무엇이었고, JSON 파싱/스키마 검증이 어떻게 되었는지를 DataStore에 남길 수 있게 한 단계다.

다음 단계부터 L2 query planner나 3 reporter 같은 실제 노드에 이 executor를 연결할 수 있다.
