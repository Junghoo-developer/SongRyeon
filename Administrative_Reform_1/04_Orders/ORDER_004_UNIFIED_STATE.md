# ORDER 004: UnifiedState

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: `TMP_Auto_Hunt_2026_06_21/TMP_ORDER_004_UNIFIED_STATE.md`  
**목표**: 0번을 제외한 일반 노드와 루프가 공유하는 `UnifiedState`를 안전하게 만들고 갱신하는 최소 helper를 만든다.

## 범위

1. `unified_state.py`를 만든다.
2. `UnifiedState`를 생성한다.
3. trace id 목록을 추가하거나 `TraceStore`에서 동기화한다.
4. 실제 라우팅 대상 `current_route`를 갱신한다.
5. 현재 루프 `current_loop`를 갱신한다.
6. 현재 스키마 `active_schema`를 갱신한다.
7. 메타정보 경계 id와 실패 신호 id를 연결한다.

## 원칙

1. 라우팅 이유는 아직 넣지 않는다. 라우팅 이유는 상대정보이므로 1번 노드 설계와 함께 다룬다.
2. 사용자 의도 판단, 요약, 성공/실패 판단은 넣지 않는다.
3. 이번 단계에서는 현재 턴의 절대정보 상태만 다룬다.
4. Qwen 14B, LangGraph, 실제 노드 실행은 붙이지 않는다.

## 완료 기준

1. `unified_state.py`가 존재한다.
2. `python -m py_compile schemas.py trace_store.py zero_state.py unified_state.py`가 통과한다.
3. 샘플 trace를 통해 `UnifiedState.trace_event_ids`를 동기화할 수 있다.
4. route, loop, schema, metainfo boundary, failure signal id를 갱신할 수 있다.
