# TMP ORDER 001: Schema Foundation

**상태**: 임시 발주서  
**목표**: 연습장 MVP의 기본 데이터 그릇을 먼저 정의한다.  
**실행 권한**: 없음. 정식 발주서로 승격 전에는 코딩하지 않는다.

## 배경

연습장의 핵심은 LLM의 즉흥 발화를 믿는 것이 아니라, trace, state, memory packet, metainfo boundary 같은 구조화된 데이터가 노드 사이를 지나가게 만드는 것이다.

## 만들 것

다음 스키마 초안을 정의한다.

- `TraceEvent`
- `UnifiedState`
- `ZeroState`
- `TurnStateCapsule`
- `MemoryPacketFrom0`
- `RoutingDecision`
- `MetainfoBoundary`
- `FailureSignal`

## 필드 예시

```text
TraceEvent
- event_id
- turn_id
- timestamp
- actor
- event_type
- input_ref
- output_ref
- raw_content_ref
- summary
- schema_status
```

## 한글 주석 원칙

각 필드에는 "이 필드가 왜 필요한지"를 한글로 짧게 설명한다.

예:

```text
event_id: trace 조각 하나를 나중에 다시 찾기 위한 고유 번호.
actor: 이 흔적을 만든 주체. 예: node_0, node_1, L2, tool_search.
```

## 완료 기준

- 각 스키마의 목적이 한 문장으로 설명되어 있다.
- 각 스키마의 필드와 한글 설명이 있다.
- 아직 구현 코드가 아니라 문서 또는 타입 초안 수준으로 끝난다.

## 제외

- Qwen 14B 연결.
- LangGraph 연결.
- 실제 노드 실행.
