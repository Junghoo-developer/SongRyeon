# ORDER 269 LLM Call Timing And Live Start Diagnostic 실행 기록

## 1. 실행 일자

- 2026-07-18

## 2. 작업 배경

ORDER 268의 강제 L live Qwen 재측정은 604초 command timeout으로 끝났다. 기존 장부는
LLM adapter가 반환한 뒤에만 `llm_call`을 기록했기 때문에, 완료된 호출의 실패는 볼 수
있어도 현재 어느 노드에서 기다리는지는 확인하기 어려웠다.

## 3. 구현 내용

### 3.1 공통 LLM 시간 장부

모든 노드가 공통으로 지나는 `LLMNodeExecutor`에서 다음 절대정보를 기록한다.

- `timing_status`
- `started_at_utc`
- `finished_at_utc`
- `execution_duration_ms`
- `configured_timeout_seconds`

시작/종료 시각은 UTC, 경과시간은 monotonic clock을 사용한다. 성공뿐 아니라 parse,
schema, adapter 실패에도 완료된 호출의 시간이 남는다.

`LLMCallFrame` schema는 0.2로 올렸고, timing이 없던 0.1 frame은
`timing_status=not_recorded`로 검증 호환을 유지했다.

### 3.2 live 시작/완료 관측

`--live-trace`에서 adapter 호출 직전 `llm_call_started`를 출력하고, 반환 뒤 기존 공식
`llm_call`을 같은 예정 event ID로 출력한다. 시작 preview는 TraceStore에 저장하지 않기
때문에 trace count와 이후 event ID를 바꾸지 않는다.

### 3.3 terminal 시간표

완료된 호출을 실행 순서대로 표시하고 총 소요시간과 가장 느린 호출을 code가 계산한다.
화면에는 node, prompt reference, duration, configured timeout, failure type만 나오며 raw
LLM text와 입력 payload 전문은 추가 노출하지 않는다.

## 4. 검증 결과

```text
python -m compileall songryeon_core main.py
-> passed

python -m pytest tests/test_order_269_llm_call_timing_and_live_start_diagnostic.py -q
-> 4 passed

관련 호환 회귀
-> 10 passed, 2 deselected

python -m pytest
-> 492 passed, 1 skipped, 5 deselected in 142.04s

python main.py smoke-test
-> SMOKE_TEST_OK in 156.4s
-> trace_count=55, data_record_count=93

python main.py competition-demo
-> SONGRYEON_COMPETITION_DEMO_OK
-> LOCAL PASS / HONEST FALLBACK PASS / CODE GUARD PASS

git diff --check
-> passed
```

Windows symbolic-link 권한 때문에 ORDER 267의 해당 테스트 하나는 계속 skip됐다.

fake-turn `--live-trace`에서는 node_1, node_2 두 호출, node_3, node_4 각각에 대해 같은
event ID의 `llm_call_started`와 `llm_call` 쌍이 출력됐고, 공식 trace/data count는 기존
`25/52`를 유지했다.

## 5. Live Qwen 병목 관측

ORDER 268과 같은 workspace 강제 L 질문을 `--live-trace`로 실행하고 외부 관측 제한을
150초로 뒀다. 회수된 마지막 trace는 다음과 같았다.

```text
[trace] trace_000006 node_1 routing schema=passed out=[route:L]
[trace] trace_000007 node_0 memory_packet schema=passed out=[memory_packet:L:targeted_memory_supply]
[trace] trace_000008 L node_output schema=passed out=[L:run_frame:0001]
[trace] trace_000009 llm:L1 llm_call_started schema=not_checked
        out=[llm_call:L1:trace_000009]
        detail=prompt=songryeon_core/prompts/l1_goal_setter_v0.md
```

같은 `trace_000009`의 완료 `llm_call`은 150초 안에 나타나지 않았다. 따라서 이번 실행에서
확정 가능한 병목은 **L1 Qwen 호출이 최소 150초 동안 반환하지 않은 것**이다. L2/L3와
후속 node_2/node_3/node_4는 아직 시작되지 않았다.

추가 코드 감사 결과 `QwenLocalHTTPAdapter`의 `timeout_seconds`는 HTTP `urlopen` 경로에는
전달되지만, endpoint가 없을 때 사용하는 직접 `ollama.chat(...)` 호출에는 전달되지 않는다.
따라서 CLI의 `--timeout 180`은 현재 direct Ollama transport에서 실제 강제 timeout으로
작동한다고 볼 수 없다. terminal은 오해를 막기 위해 이를 `configured_timeout`으로 표시한다.

## 6. 일부러 하지 않은 것

- direct Ollama 호출 강제 timeout 구현
- L1 생략 또는 code 대체
- LLM 호출 수와 retry 변경
- L revision과 same-turn L/R 횟수 변경
- 느린 호출 자동 중단 휴리스틱
- 외부 API, Neo4j, 심야정부 변경

## 7. 판정

ORDER 269의 관측 목표는 완료됐다. 10분 전체 지연을 막연히 L 전체 문제라고 부르던 상태에서,
이번 재현에서는 L1 direct Ollama 호출이 150초 이상 반환하지 않았고 설정 timeout도 강제되지
않는다는 구체적인 절대정보를 확보했다. 다음 발주는 direct Ollama timeout/recovery 경계를
먼저 설계해야 한다.
