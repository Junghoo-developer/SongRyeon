# ORDER 003: ZeroState And Turn Capsule

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: `TMP_Auto_Hunt_2026_06_21/TMP_ORDER_003_ZERO_STATE_AND_TURN_CAPSULE.md`  
**목표**: 저장된 trace를 다음 턴의 0번이 읽을 수 있는 `TurnStateCapsule`로 묶고, 이를 `ZeroState`에 추가하는 최소 기능을 만든다.

## 범위

1. `zero_state.py`를 만든다.
2. `TraceStore`에서 특정 `turn_id`의 trace를 읽어 `TurnStateCapsule`을 만든다.
3. 모든 trace ID를 캡슐에 보존한다.
4. 사용자 입력 trace ID를 자동으로 찾는다.
5. 최종 응답 trace ID는 명시 입력 또는 안전한 후보에서 찾는다.
6. `NodeMovement` 목록을 캡슐에 연결한다.
7. 캡슐을 `ZeroState.previous_turn_capsules`에 추가한다.

## 원칙

1. LLM 요약은 하지 않는다.
2. 상대 정보와 혼합 정보는 만들지 않는다.
3. 기억을 지어내지 않는다.
4. trace에 없는 정보는 캡슐에 확정값으로 넣지 않는다.
5. 이번 단계는 절대정보 색인과 연결만 다룬다.

## 완료 기준

1. `zero_state.py`가 존재한다.
2. `python -m py_compile schemas.py trace_store.py zero_state.py`가 통과한다.
3. 샘플 trace에서 `TurnStateCapsule`을 만들 수 있다.
4. 생성된 캡슐을 `ZeroState`에 추가할 수 있다.
