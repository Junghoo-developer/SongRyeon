# TMP ORDER 003: ZeroState And Turn Capsule

**상태**: 임시 발주서  
**목표**: 0 기억공급관이 보는 특수 state와 이전 턴 캡슐 구조를 정한다.  
**실행 권한**: 없음.

## 배경

0은 최근 대화, 이전 턴 state, 이번 턴 trace를 합쳐 본다. 매 턴의 trace는 다음 턴에서 LLM이 읽기 좋게 정리되어 0.state의 재료가 된다.

## 만들 것

`ZeroState`와 `TurnStateCapsule`을 정의한다.

```text
ZeroState
- recent_raw_conversation
- older_conversation_summary
- previous_turn_capsules
- current_turn_trace_ids
- node_profiles
- memory_insufficient_count
```

```text
TurnStateCapsule
- turn_id
- user_input_summary
- final_response_summary
- routing_path
- important_trace_ids
- confirmed_facts
- relative_judgements
- unresolved_questions
- corrections_from_user
- memory_to_preserve
- next_turn_hints
```

## 한글 설명 예시

```text
previous_turn_capsules:
이전 턴 전체 로그를 통째로 넣는 대신, 다음 턴의 0이 읽기 좋게 압축한 상태 캡슐 목록.
```

## 완료 기준

- 0이 보는 정보와 일반 노드가 보는 정보의 차이가 설명되어 있다.
- 턴이 끝날 때 어떤 정보가 다음 턴으로 넘어가는지 정의되어 있다.
- "기억을 지어내지 않는다"는 규칙이 포함되어 있다.

## 제외

- 실제 요약 LLM 호출.
- 벡터 DB.
