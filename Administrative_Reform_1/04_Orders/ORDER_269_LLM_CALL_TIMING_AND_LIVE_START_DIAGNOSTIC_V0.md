# ORDER 269: LLM Call Timing And Live Start Diagnostic v0

## 1. 배경

ORDER 268의 동일 live Qwen 재측정은 600초 제한을 넘겨 604초에 command timeout 됐다.
현재 `llm_call` record는 adapter가 반환한 뒤에만 만들어지므로 완료된 호출의 실패 원인은
볼 수 있지만, 현재 어느 노드 호출에서 기다리고 있는지와 각 호출이 실제로 몇 초를
사용했는지는 확인하기 어렵다.

## 2. 목표

LLM 호출 정책과 예산을 바꾸지 않고 모든 노드가 공통으로 지나는 실행기에서 호출 시작,
종료, 소요시간, 설정 timeout을 code-owned 절대정보로 측정한다. live trace에서는 현재
시작된 호출을 즉시 보여주고, 정상 종료 뒤 terminal에서는 호출별 시간과 누적 시간을
확인할 수 있게 한다.

## 3. 구현 범위

### 3.1 LLMCallFrame 시간 절대정보

- `timing_status`
- `started_at_utc`
- `finished_at_utc`
- `execution_duration_ms`
- `configured_timeout_seconds`

벽시계 시각은 UTC로 기록하고, 소요시간 계산은 시스템 시각 변경의 영향을 덜 받는
monotonic clock을 사용한다. 소요시간은 adapter 호출과 JSON parse/schema validation을
포함한 공통 executor 1회 실행 시간이다.

`configured_timeout_seconds`는 adapter에 전달된 설정값의 절대정보다. 해당 transport가
그 값을 실제로 강제하는지는 별도 사실이며, terminal은 이를 단순 `timeout`이라고
표시하지 않는다.

### 3.2 live 호출 시작/완료 표시

- `--live-trace`가 켜진 경우 adapter 호출 직전에 `llm_call_started`를 출력한다.
- 반환 뒤 기존 공식 `llm_call` trace를 같은 예정 event ID로 출력한다.
- 시작 표시는 아직 완료되지 않은 progress preview이며 TraceStore의 공식 event count에는
  추가하지 않는다.
- 프로세스가 강제 종료되어도 사용자는 마지막으로 시작된 node와 prompt를 화면에서
  확인할 수 있다.

### 3.3 terminal 시간 요약

- 기록된 순서대로 node, prompt, duration, timeout, failure type을 표시한다.
- 완료된 호출의 합계와 최장 호출을 code가 계산한다.
- raw LLM text와 입력 payload 전문은 이 진단판에 노출하지 않는다.
- 완료되지 않은 호출 시간을 code가 추정하지 않는다.

## 4. 호환성

- timing 필드가 없는 과거 `LLMCallFrame`은 `timing_status=not_recorded`로 유지한다.
- 새 frame schema version은 0.2로 올리되 0.1 frame 검증 호환을 유지한다.
- progress preview는 공식 TraceStore/DataStore record를 추가하지 않는다.

## 5. 금지

- LLM 호출 수, retry, L revision, same-turn L/R 횟수 변경
- timeout 자동 증가/감소
- 느린 노드를 code가 의미적으로 생략하거나 대체
- 모델 응답 속도에 대한 휴리스틱 판정
- raw prompt/input/response 전문의 추가 terminal 노출
- 외부 API, Neo4j, 심야정부 변경

## 6. 완료 조건

1. 성공·adapter 실패 호출 모두 timing 절대정보를 남긴다.
2. `--live-trace` sink는 시작과 완료를 같은 예정 event ID로 관측한다.
3. progress preview는 TraceStore count를 늘리지 않는다.
4. terminal에서 호출 순서, 개별 duration, 총합, 최장 호출이 보인다.
5. 과거 timing 미기록 frame 호환이 유지된다.
6. 표적 pytest, 전체 pytest, smoke-test, competition-demo를 통과한다.
7. live Qwen을 제한된 시간 동안 재실행해 마지막 시작 node를 관찰한다.

## 7. 후속 경계

ORDER 269 결과로 실제 병목 node와 호출 횟수가 확인된 뒤에만 호출 합치기, 선택적 노드
생략, timeout 정책 변경을 별도 발주로 논의한다.
