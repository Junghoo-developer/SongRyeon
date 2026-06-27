# ORDER_106 Live Trace Progress Stream 실행 기록

## 작업 일시

2026-06-26

## 목표

턴이 끝날 때까지 기다리지 않아도 실행 진행 상황을 볼 수 있도록 `--live-trace` 옵션을 추가했다.

이번 작업의 경계는 다음이다.

```text
trace event progress line은 실시간으로 출력한다.
node_4 통과 전 report 본문은 출력하지 않는다.
LLM token streaming은 열지 않는다.
```

## 변경 파일

- `songryeon_core/core/trace_store.py`
- `songryeon_core/runtime/live_trace.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/user_turn.py`
- `songryeon_core/runtime/smoke_test.py`
- `main.py`
- `Administrative_Reform_1/04_Orders/ORDER_106_LIVE_TRACE_PROGRESS_STREAM_V0.md`

## 구현 내용

### 1. TraceStore event hook

`TraceStore`에 optional `on_event` callback을 추가했다.

기본값은 `None`이므로 기존 실행은 그대로 동작한다.
`TraceStore.add_event()`가 새 event를 저장한 뒤 callback을 호출한다.

과거 trace 복원 시에는 callback을 호출하지 않도록 `TraceStore.__init__()`에서 기존 event 추가는 `notify=False`로 처리했다.

### 2. live trace formatter

`songryeon_core/runtime/live_trace.py`를 추가했다.

출력 형식:

```text
[trace] trace_000001 user user_input schema=not_checked out=[]
[trace] trace_000002 node_0 memory_packet schema=passed out=[memory_packet:node_1:pre_route_report]
```

출력 필드:

```text
event_id
actor
event_type
schema_status
output_ref
```

raw user text, node_3 report 본문, node_4 전 최종 답변 후보 본문은 출력하지 않는다.

### 3. CLI 옵션

다음 명령에서 `--live-trace`를 사용할 수 있다.

```text
dry-run
fake-turn
qwen-turn
qwen-chat
```

live trace line은 stderr로 출력한다.
기존 JSON/pretty 최종 출력은 stdout에 남긴다.

### 4. smoke-test

`_run_live_trace_progress_stream_smoke()`를 추가했다.

검증 내용:

```text
live_trace_sink를 넘기면 trace_count와 같은 개수의 line이 수집된다.
첫 line에 event_id, actor, event_type, schema_status, output_ref가 들어간다.
node_0 memory_packet progress가 보인다.
report body sentinel 또는 grounding/report 본문 조각이 live trace에 새지 않는다.
```

## 검증

```powershell
python -m compileall .\songryeon_core .\main.py
```

통과.

```powershell
python .\main.py dry-run --live-trace
```

통과.

확인된 예시 출력:

```text
[trace] trace_000001 user user_input schema=not_checked out=[]
[trace] trace_000002 node_0 memory_packet schema=passed out=[memory_packet:node_1:pre_route_report]
[trace] trace_000003 memory_relevance_selector node_output schema=passed out=[memory_packet:node_1:pre_route_report:memory_relevance_selection]
```

```powershell
python .\main.py smoke-test
```

통과.

최종 상태:

```text
SMOKE_TEST_OK
```

새 smoke 확인값:

```text
live_trace_line_count=12
live_trace_matches_trace_count=true
live_trace_no_report_body=true
```

```powershell
python .\main.py fake-turn "진행상황 확인" --live-trace
```

통과.

확인된 사항:

```text
fake-turn 입구에서도 --live-trace가 전달된다.
llm:node_1, node_0 memory_packet, node_3, node_4 trace progress line이 출력된다.
최종 report 본문은 기존 최종 JSON/pretty 출력 경로로만 나온다.
```

## 비범위 유지

이번 작업에서 다음은 하지 않았다.

- 최종 답변 본문 streaming
- node_3 report 본문 streaming
- LLM token streaming
- trace event schema 변경
- DataStore record live streaming
- 웹 UI/TUI
- 기억 selector/route 정책 변경

## 남은 위험

stderr/stdout 분리는 실제 터미널에서는 진행 표시를 빠르게 보여주지만, 일부 테스트 harness나 캡처 도구에서는 stdout/stderr 병합 순서가 실제 시간순과 다르게 보일 수 있다.

또한 live trace는 event가 생성된 뒤에만 보인다.
긴 LLM 호출 중에는 호출 시작 event가 별도로 없으면 응답 대기 중 상태가 길게 보일 수 있다.
향후 필요하면 LLM call start event 또는 tool call start event를 별도 발주로 검토한다.
