# TMP ORDER 002: Trace Event Format

**상태**: 임시 발주서  
**목표**: "일 돌아가는 꼬라지"를 저장할 trace 이벤트 형식을 정한다.  
**실행 권한**: 없음.

## 배경

trace는 state가 어떻게 생겼는지 설명하는 실행 흔적이다. 연습장에서는 trace를 일거수일투족 저장하되, 나중에 0이나 DB/그래프 지식화가 읽기 좋게 관리해야 한다.

## 만들 것

`TraceEvent`의 최소 형식을 정의한다.

```text
event_id: trace 조각의 고유 ID.
turn_id: 어떤 턴에서 생긴 trace인지.
timestamp: 언제 생겼는지.
actor: 누가 만들었는지.
event_type: 입력, 출력, 라우팅, 도구 호출, 스키마 검사 등.
input_ref: 입력 데이터의 ID 목록.
output_ref: 출력 데이터의 ID 목록.
raw_content_ref: 원문 위치. 원문이 길면 파일 경로 또는 저장소 ID.
summary: LLM이 보기 좋은 짧은 요약.
schema_status: 스키마 통과 여부.
```

## event_type 후보

- `user_input`
- `node_input`
- `node_output`
- `routing`
- `tool_call`
- `tool_result`
- `schema_check`
- `memory_packet`
- `failure_signal`
- `turn_outcome`

## 완료 기준

- trace가 state와 어떻게 다른지 설명되어 있다.
- 이벤트 타입 목록이 있다.
- 나중에 0.state와 2 메타정보 경계가 이 trace를 참조할 수 있다.

## 제외

- 실제 파일 저장 구현.
- DB 설계.
