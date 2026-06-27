# ORDER 106: Live Trace Progress Stream v0

## 상태

구현 및 검증 완료.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_106_live_trace_progress_stream_2026_06_26_001.md`

이 발주서는 Qwen/fake 턴 실행 중 최종 답변이 나오기 전까지 사용자가 아무 진행 상황도 보지 못하는 문제를 줄이기 위한 좁은 UX/운영 MVP다.

## 배경

현재 `TraceStore.create_event()`는 각 노드/루프/도구 실행 중 trace event를 즉시 생성한다.

하지만 CLI 출력은 보통 턴이 끝난 뒤 `render_pretty_turn()` 또는 JSON summary로 한 번에 나온다.
따라서 긴 Qwen 실행 중에는 사용자가 다음을 알기 어렵다.

```text
송련이 멈췄는지
L 루프를 도는 중인지
문서를 읽는 중인지
node_4에서 검사 중인지
Qwen 응답을 기다리는 중인지
```

## 목표

trace event가 생성되는 순간 개발자용 진행 줄을 실시간으로 출력하는 `--live-trace` 옵션을 추가한다.

핵심 문장:

```text
trace는 이미 실시간으로 생성된다.
ORDER_106은 그 trace를 안전한 progress line으로 즉시 보여주는 작업이다.
```

## 구현 범위

### 1. TraceStore event hook

`TraceStore`에 optional event callback을 추가한다.

조건:

- 기본값은 off다.
- callback이 없으면 기존 동작이 바뀌지 않는다.
- event가 저장된 뒤 callback을 호출한다.
- 저장/복원된 과거 trace를 읽을 때 실시간 출력이 재생되면 안 된다.

### 2. live trace formatter

새 helper를 둔다.

출력 예:

```text
[trace] trace_000001 user user_input schema=not_checked out=[]
[trace] trace_000002 node_0 memory_packet schema=passed out=[memory_packet:node_1:pre_route_report]
```

표시 범위:

```text
event_id
actor
event_type
schema_status
output_ref
```

주의:

- LLM 답변 본문을 실시간 출력하지 않는다.
- node_4 통과 전 report 본문을 실시간 출력하지 않는다.
- raw user/assistant text를 live trace line에 싣지 않는다.

### 3. CLI 옵션

다음 명령에 `--live-trace`를 추가한다.

```text
dry-run
fake-turn
qwen-turn
qwen-chat
```

출력 대상은 stderr로 둔다.
기존 JSON/stdout 출력과 섞이지 않게 하기 위해서다.

### 4. smoke-test

최소 smoke를 추가한다.

검증:

```text
live_trace off 기본 실행은 기존처럼 동작한다.
live_trace sink를 넘기면 trace event 수만큼 line이 수집된다.
line에는 event_id, actor, event_type, schema_status, output_ref가 있다.
line에는 report 본문 sentinel이 새지 않는다.
```

## 비범위

이번 발주에서 하지 말 것:

```text
최종 답변 본문 streaming
node_3 report 본문 streaming
LLM token streaming
trace event schema 변경
DataStore record live streaming
웹 UI
TUI
장기기억/selector/route 정책 변경
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

가능하면 다음 수동 확인도 수행한다.

```powershell
python main.py fake-turn "진행상황 확인" --live-trace
```

완료 보고에는 다음을 적는다.

- live trace hook이 어디에 붙었는지
- 어떤 CLI에서 `--live-trace`를 쓸 수 있는지
- stdout/stderr를 어떻게 분리했는지
- node_4 전 report 본문을 streaming하지 않음을 어떻게 보장했는지
- smoke-test 결과
