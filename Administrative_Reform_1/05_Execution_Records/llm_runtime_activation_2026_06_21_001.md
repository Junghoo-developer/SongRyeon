# LLM Runtime Activation 2026-06-21 001

## 목적

ORDER 043에 따라 LLM 런타임 선택지를 실제 코드에 연결했다.

## 변경 내용

- `songryeon_core/llm/runtime.py`를 추가했다.
- LLM 모드를 `off`, `fake`, `qwen`으로 명시했다.
- `SONGRYEON_LLM_MODE`, `QWEN_LOCAL_ENDPOINT`, `QWEN_MODEL_ID`, `QWEN_TIMEOUT_SECONDS`를 읽는 runtime config를 만들었다.
- Qwen adapter가 timeout 설정을 받도록 했다.
- `main.py qwen-ping` CLI를 추가했다.
- `llm_failed` failure type 후보를 추가했다.

## 확인 결과

```text
python main.py qwen-ping
ok=false
status=endpoint_missing
error='QWEN_LOCAL_ENDPOINT is not set'

python -m compileall -q songryeon_core
OK

python dry_run.py
DRY_RUN_OK
trace_count=15
data_record_count=15
movement_count=11

python main.py smoke-test
SMOKE_TEST_OK
trace_count=15
data_record_count=15
```

## 해석

이번 단계는 LLM이 노드 판단을 실제로 맡는 단계가 아니다.

Qwen/Fake/off 중 어떤 runtime을 쓸지 선택하고, Qwen endpoint가 없어도 구조 실행이 죽지 않도록 gate를 만든 단계다. 다음 단계인 ORDER 044에서 LLM call 자체를 trace/data로 남기고 retry/fallback을 표준화한다.
